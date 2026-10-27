"""Markdown/HTML parsing into canonical, source-addressed structures.

Covers DB-005 (metadata import and reconciliation), DB-007 (legislation structure), DB-009 (table
semantics). Nothing here fetches files or URLs: callers pass decoded text plus the immutable
artifact ID that every :class:`SourceSpan` refers to.

Design rules taken from the coding backlog:

* Legal numbering comes from the text (``(2)``, ``(a)``, ``65A``), never from Markdown heading depth
  or line starts. Inline subsection starts are accepted only when they continue the numbering.
* Page furniture (running headers, footers, separators) is kept as source metadata and excluded from
  provision text, but every provision keeps spans into the original artifact.
* Table rows are only produced from structural evidence (HTML rows, pipe rows). Detached columns and
  stray row text become :class:`TableFragment` objects on an unresolved table; nothing is zipped.
* Unresolved structure produces warnings instead of invented nodes.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from html.parser import HTMLParser
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator

from .models import (
    Block,
    BlockKind,
    ContentClass,
    FactClaim,
    FurnitureKind,
    LegalTime,
    PageBasis,
    ParsedLegislation,
    ParseWarning,
    ProvisionKind,
    ProvisionNode,
    Region,
    RepealEntry,
    SourceSpan,
    TableCell,
    TableColumn,
    TableFragment,
    TableRecord,
    TableRow,
    TableStatus,
    sha256_hex,
)

# --------------------------------------------------------------------------------------------
# Text normalization
# --------------------------------------------------------------------------------------------

_DASHES = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_WS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Faithful retrieval text: NFKC, unified dashes, no Markdown emphasis, collapsed whitespace.

    Used for lookup and normalized text only. Verbatim evidence always comes from source spans.
    """
    text = unicodedata.normalize("NFKC", text)
    text = _DASHES.sub("-", text)
    text = text.replace("*", "")
    return _WS.sub(" ", text).strip()


def lookup_key(text: str) -> str:
    return normalize_text(text).casefold()


# --------------------------------------------------------------------------------------------
# Lines and blocks
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Line:
    number: int  # 1-based
    start: int
    end: int  # exclusive, excluding the line terminator
    text: str


def _split_lines(text: str) -> list[_Line]:
    lines: list[_Line] = []
    pos = 0
    number = 1
    for match in re.finditer(r"\r\n|\n|\r", text):
        lines.append(_Line(number, pos, match.start(), text[pos : match.start()]))
        pos = match.end()
        number += 1
    if pos < len(text):
        lines.append(_Line(number, pos, len(text), text[pos:]))
    return lines


@dataclass(slots=True)
class _Block:
    index: int
    kind: BlockKind
    lines: list[_Line]
    level: int | None = None
    region: Region = Region.BODY
    furniture: FurnitureKind | None = None
    page_label: str | None = None

    @property
    def start(self) -> int:
        return self.lines[0].start

    @property
    def end(self) -> int:
        return self.lines[-1].end

    @property
    def joined(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def content(self) -> str:
        """Heading text without ``#`` markers, otherwise the joined lines."""
        if self.kind is BlockKind.HEADING:
            match = _HEADING.match(self.lines[0].text)
            return match.group(2) if match else self.lines[0].text
        return self.joined


_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_PAGE_BREAK = re.compile(r"^\s*-{5,}\s*$")
_SEPARATOR = re.compile(r"^\s*(?:-{3,4}|\*{3,}|_{3,})\s*$")
_IMAGE = re.compile(r"^\s*!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_YAMLISH = re.compile(r"^(?:[A-Za-z_][\w-]*\s*:.*|\s+.*|-\s.*|#.*|)$")


def _starts_block(line: str) -> bool:
    stripped = line.lstrip()
    return bool(
        stripped.lower().startswith("<table")
        or stripped.startswith("|")
        or _FENCE.match(line)
        or _HEADING.match(line)
        or _PAGE_BREAK.match(line)
        or _SEPARATOR.match(line)
        or _IMAGE.match(line)
    )


def _segment(lines: list[_Line]) -> list[_Block]:
    blocks: list[_Block] = []

    def add(kind: BlockKind, chunk: list[_Line], level: int | None = None) -> None:
        blocks.append(_Block(len(blocks), kind, chunk, level))

    i = 0
    n = len(lines)
    if n and lines[0].text.strip() == "---":
        for j in range(1, min(n, 400)):
            if lines[j].text.strip() == "---":
                if j > 1 and all(_YAMLISH.match(line.text) for line in lines[1:j]):
                    add(BlockKind.FRONT_MATTER, lines[0 : j + 1])
                    i = j + 1
                break
    while i < n:
        text = lines[i].text
        stripped = text.lstrip()
        if not text.strip():
            i += 1
            continue
        if stripped.lower().startswith("<table"):
            j = i
            while j < n and "</table>" not in lines[j].text.lower():
                j += 1
            j = min(j, n - 1)
            add(BlockKind.HTML_TABLE, lines[i : j + 1])
            i = j + 1
        elif stripped.startswith("|"):
            j = i
            while j + 1 < n and lines[j + 1].text.lstrip().startswith("|"):
                j += 1
            add(BlockKind.PIPE_TABLE, lines[i : j + 1])
            i = j + 1
        elif fence := _FENCE.match(text):
            j = i + 1
            while j < n and not lines[j].text.lstrip().startswith(fence.group(1)):
                j += 1
            j = min(j, n - 1)
            add(BlockKind.CODE, lines[i : j + 1])
            i = j + 1
        elif heading := _HEADING.match(text):
            add(BlockKind.HEADING, [lines[i]], len(heading.group(1)))
            i += 1
        elif _PAGE_BREAK.match(text):
            add(BlockKind.PAGE_BREAK, [lines[i]])
            i += 1
        elif _SEPARATOR.match(text):
            add(BlockKind.SEPARATOR, [lines[i]])
            i += 1
        elif _IMAGE.match(text):
            add(BlockKind.IMAGE, [lines[i]])
            i += 1
        else:
            j = i
            while j + 1 < n and lines[j + 1].text.strip() and not _starts_block(lines[j + 1].text):
                j += 1
            add(BlockKind.PARAGRAPH, lines[i : j + 1])
            i = j + 1
    return blocks


# --------------------------------------------------------------------------------------------
# Spans
# --------------------------------------------------------------------------------------------


class _SpanFactory:
    def __init__(self, text: str, lines: list[_Line], artifact_id: str) -> None:
        self.text = text
        self.artifact_id = artifact_id
        self._line_starts = [line.start for line in lines]

    def line_of(self, offset: int) -> int:
        lo, hi = 0, len(self._line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def make(self, start: int, end: int, page_label: str | None = None) -> SourceSpan:
        # Trim surrounding whitespace so spans cover source characters only.
        while start < end and self.text[start].isspace():
            start += 1
        while end > start and self.text[end - 1].isspace():
            end -= 1
        return SourceSpan(
            artifact_id=self.artifact_id,
            char_start=start,
            char_end=end,
            line_start=self.line_of(start),
            line_end=self.line_of(max(start, end - 1)),
            printed_page_label=page_label,
            page_label_basis=PageBasis.FOOTER_TEXT if page_label else None,
        )

    def for_block(self, block: _Block) -> SourceSpan:
        return self.make(block.start, block.end, block.page_label)


def _append_span(node_spans: list[SourceSpan], span: SourceSpan, text: str, *, merge: bool = True) -> None:
    if span.char_end <= span.char_start:
        return
    if node_spans and merge:
        last = node_spans[-1]
        gap = text[last.char_end : span.char_start]
        if last.char_end <= span.char_start and not gap.strip() and last.printed_page_label == span.printed_page_label:
            node_spans[-1] = last.model_copy(update={"char_end": span.char_end, "line_end": span.line_end})
            return
    node_spans.append(span)


# --------------------------------------------------------------------------------------------
# Tables (DB-009)
# --------------------------------------------------------------------------------------------


@dataclass(slots=True)
class _RawCell:
    text: str
    start: int
    end: int
    colspan: int = 1


class _HtmlTableParser(HTMLParser):
    def __init__(self, block_text: str) -> None:
        super().__init__(convert_charrefs=True)
        self._line_offsets = [0]
        for match in re.finditer(r"\n", block_text):
            self._line_offsets.append(match.end())
        self.rows: list[list[_RawCell]] = []
        self._row: list[_RawCell] | None = None
        self._cell: dict[str, Any] | None = None

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_offsets[line - 1] + col

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            colspan = int(dict(attrs).get("colspan") or 1)
            start_tag = self.get_starttag_text() or ""
            self._cell = {"parts": [], "start": self._offset() + len(start_tag), "colspan": colspan}
        elif tag == "br" and self._cell is not None:
            self._cell["parts"].append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            raw = "".join(self._cell["parts"])
            self._row.append(_RawCell(_cell_text(raw), self._cell["start"], self._offset(), self._cell["colspan"]))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["parts"].append(data)


def _cell_text(raw: str) -> str:
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", "", raw)
    return "\n".join(t for t in (normalize_text(part) for part in raw.split("\n")) if t)


def _parse_html_rows(block: _Block, text: str) -> list[list[_RawCell]]:
    block_text = text[block.start : block.end]
    parser = _HtmlTableParser(block_text)
    parser.feed(block_text)
    parser.close()
    for row in parser.rows:
        for cell in row:
            cell.start += block.start
            cell.end += block.start
    return parser.rows


def _parse_pipe_rows(block: _Block) -> tuple[list[list[_RawCell]], bool]:
    rows: list[list[_RawCell]] = []
    has_header = False
    for line in block.lines:
        content = line.text
        if re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", content):
            has_header = len(rows) == 1
            continue
        pipes = [m.start() for m in re.finditer(r"(?<!\\)\|", content)]
        bounds = [-1, *pipes, len(content)]
        segments = [(bounds[i] + 1, bounds[i + 1]) for i in range(len(bounds) - 1)]
        if content.lstrip().startswith("|"):
            segments = segments[1:]  # nothing before the leading pipe
        if pipes and not content[pipes[-1] + 1 :].strip():
            segments = segments[:-1]  # nothing after the trailing pipe
        cells = [_RawCell(_cell_text(content[a:b]), line.start + a, line.start + b) for a, b in segments]
        rows.append(cells)
    return rows, has_header


_ITEM_KEY = re.compile(r"^(\d+[A-Z]?)\.?(?:\s|$)")


def _is_data_row(row: list[_RawCell]) -> bool:
    return bool(row) and bool(_ITEM_KEY.match(row[0].text))


def _build_table(
    raw_rows: list[list[_RawCell]],
    spans: _SpanFactory,
    page_label: str | None,
    *,
    table_id: str,
    region: Region,
    content_class: ContentClass,
    header_rows: int | None,
) -> TableRecord:
    table = TableRecord(table_id=table_id, region=region, content_class=content_class)
    if not raw_rows:
        table.status = TableStatus.UNRESOLVED
        table.issues.append("table has no rows")
        return table
    ncols = max(sum(c.colspan for c in row) for row in raw_rows)
    r = 0
    first = raw_rows[0]
    if header_rows is None and len(first) == 1 and first[0].colspan == ncols and ncols > 1:
        table.title = first[0].text
        r = 1
    headers: list[list[_RawCell]] = []
    if header_rows is not None:
        headers = raw_rows[r : r + header_rows]
        r += header_rows
    else:
        data_start = next((i for i in range(r, len(raw_rows)) if _is_data_row(raw_rows[i])), None)
        if data_start is None:
            data_start = min(r + 1, len(raw_rows))
        headers = raw_rows[r:data_start]
        r = data_start

    header_texts: list[list[str]] = [[] for _ in range(ncols)]
    for row in headers:
        col = 0
        for cell in row:
            for k in range(cell.colspan):
                if col + k < ncols and cell.text:
                    header_texts[col + k].append(cell.text.replace("\n", " "))
            col += cell.colspan
    for index, parts in enumerate(header_texts):
        header = " ".join(parts)
        number = re.search(r"\bColumn\s+(\d+)\b", header, re.IGNORECASE)
        table.columns.append(
            TableColumn(index=index, header=header, column_number=int(number.group(1)) if number else None)
        )

    keyed_by_item = bool(table.columns) and table.columns[0].header.casefold().startswith("item")
    seen: set[str] = set()
    for ordinal, row in enumerate(raw_rows[r:], start=1):
        cells: list[TableCell] = []
        col = 0
        for cell in row:
            cells.append(
                TableCell(
                    column_index=col,
                    text=cell.text,
                    span=spans.make(cell.start, cell.end, page_label),
                    colspan=cell.colspan,
                )
            )
            col += cell.colspan
        first_text = row[0].text if row else ""
        match = _ITEM_KEY.match(first_text)
        if keyed_by_item and first_text:
            key = first_text.split()[0].rstrip(".")
        elif match:
            key = match.group(1)
        else:
            key = str(ordinal)
        if keyed_by_item and not re.fullmatch(r"\d+[A-Z]?", key or ""):
            table.issues.append(f"row key {first_text!r} is not a single item number")
        elif keyed_by_item and not re.fullmatch(r"\d+[A-Z]?", first_text):
            table.issues.append(f"row {key} key cell {first_text!r} holds more than an item number")
        if any(re.match(r"^Column\s+\d+", c.text) for c in cells[1:]) or (first_text.casefold() == "item"):
            table.issues.append(f"row {key} repeats header text")
        if key in seen:
            table.issues.append(f"duplicate row key {key}")
        seen.add(key)
        if col < ncols:
            table.issues.append(f"row {key} has {col} of {ncols} cells")
        empty = [c.column_index for c in cells if not c.text]
        if empty and region is Region.BODY:
            table.issues.append(f"row {key} has empty cells in columns {empty}")
        table.rows.append(TableRow(key=key, cells=cells))
    if table.issues:
        table.status = TableStatus.UNRESOLVED
    return table


# --------------------------------------------------------------------------------------------
# Legislation structure (DB-007)
# --------------------------------------------------------------------------------------------

_STRUCTURAL = re.compile(r"^(Chapter|Part|Division|Subdivision)\s+([0-9]+[A-Z]*|[A-Z]{1,3})\s*-\s*(\S.*)$")
_SCHEDULE = re.compile(r"^Schedule\s+(\d+[A-Z]*)\b\s*-?\s*(.*)$")
_SECTION = re.compile(r"^(\d+[A-Z]*)\s+(\S.*)$")
_RANK = {
    ProvisionKind.CHAPTER: 1,
    ProvisionKind.SCHEDULE: 1,
    ProvisionKind.PART: 2,
    ProvisionKind.DIVISION: 3,
    ProvisionKind.SUBDIVISION: 4,
}
_KEY_PREFIX = {
    ProvisionKind.CHAPTER: "ch",
    ProvisionKind.SCHEDULE: "sch",
    ProvisionKind.PART: "pt",
    ProvisionKind.DIVISION: "div",
    ProvisionKind.SUBDIVISION: "sdiv",
}
_HEADED_KINDS = frozenset({*_RANK, ProvisionKind.SECTION})
_COLUMN_FRAGMENT = re.compile(r"^Column\s+\d+\b(?!\s+of\b)", re.IGNORECASE)
_ROW_FRAGMENT = re.compile(r"^\d+[A-Z]?\.?\s+\S")
_MARKER = re.compile(r"\((\d+[A-Z]*|[a-z]{1,4}|[A-Z]{1,2})\)(?=\s)")
_INLINE_BEFORE = re.compile(r"(?:[.;:]|;\s+(?:and|or))\s+$")
_ITALIC_LABEL = re.compile(r"((?:\*[^*\n]{1,80}?\*[ \t]+){1,4})(?=\((\d+[A-Z]*)\)\s)")
_PENALTY = re.compile(r"(?:Civil penalty|Penalty)(?: for [^:]{1,80})?:\s")
_NOTE = re.compile(r"(Note|Example)(?:\s+(\d+))?:\s")
_DEFINITION = re.compile(r"^\s*\*\*\*([\w\s'’-]+)\*\*\*(?=\s*(?:[:,]|[a-z]))")
_INLINE_DEF = re.compile(r"\*\*\*([^*]+)\*\*\*")
_ROMAN = re.compile(r"^(?=[ivxl])(x{0,3})(ix|iv|v?i{0,3})$")
_SENTENCE_START = re.compile(r"\s*[\"'(*]*[A-Z]")


def _num_key(token: str) -> tuple[int, str]:
    match = re.match(r"(\d+)([A-Z]*)", token)
    return (int(match.group(1)), match.group(2)) if match else (0, token)


def _roman_value(token: str) -> int:
    values = {"i": 1, "v": 5, "x": 10, "l": 50}
    total = 0
    for i, ch in enumerate(token):
        v = values[ch]
        total += -v if i + 1 < len(token) and values[token[i + 1]] > v else v
    return total


def _letter_successors(token: str) -> set[str]:
    if len(token) == 1:
        return {chr(ord(token) + 1), token + token}
    if len(token) == 2 and token[0] == token[1]:
        return {token + token[0], chr(ord(token[0]) + 1), token[0] + chr(ord(token[1]) + 1)}
    return {token[:-1] + chr(ord(token[-1]) + 1), chr(ord(token[0]) + 1)}


def _classify_heading(text: str) -> tuple[ProvisionKind, str, str] | None:
    norm = normalize_text(text)
    if match := _STRUCTURAL.match(norm):
        return ProvisionKind(match.group(1).lower()), match.group(2), match.group(3).strip()
    if match := _SCHEDULE.match(norm):
        return ProvisionKind.SCHEDULE, match.group(1), match.group(2).strip()
    if match := _SECTION.match(norm):
        return ProvisionKind.SECTION, match.group(1), match.group(2).strip()
    return None


@dataclass(slots=True)
class _Segment:
    kind: str  # text | marker | label | penalty | note | definition
    start: int
    end: int
    token: str | None = None
    inline: bool = False


class _SectionBuilder:
    """Turns one section's blocks into subsection/paragraph/definition/note/penalty nodes."""

    def __init__(self, parser: _LegislationParser, section: ProvisionNode) -> None:
        self.p = parser
        self.section = section
        self.blocks: list[_Block] = []

    # -- state used while processing --
    def _reset(self) -> None:
        self.levels: dict[int, ProvisionNode] = {}
        self.current: ProvisionNode = self.section
        self.label: str | None = None
        self.pending_label: SourceSpan | None = None
        self.def_ctx: ProvisionNode | None = None
        self.note_ctx: ProvisionNode | None = None
        self.levels_before_note: dict[int, ProvisionNode] = {}
        self.last_sub: tuple[int, str] | None = None
        self.fragment_mode = False
        self.post_table: TableRecord | None = None
        self.pending_title: _Block | None = None
        self.tables: list[TableRecord] = []
        self.counters: dict[str, int] = {}
        self.outline = (self.section.title or "").casefold().startswith("simplified outline")

    def finish(self) -> None:
        self._reset()
        blocks = [b for b in self.blocks if b.furniture is None]
        for i, block in enumerate(blocks):
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            self._block(block, nxt)
        self._finalize_tables()

    # -- block dispatch --
    def _block(self, b: _Block, nxt: _Block | None) -> None:
        p = self.p
        if b.kind is BlockKind.IMAGE:
            return  # reported once for the whole document in _LegislationParser.parse
        if b.kind in (BlockKind.HTML_TABLE, BlockKind.PIPE_TABLE):
            table = p.table_from_block(b, self._content_class(), self.section.key)
            if self.fragment_mode or (self.post_table is not None and self.post_table.status is TableStatus.UNRESOLVED):
                table.issues.append("continues an unresolved table; stitching needs structural evidence")
            if self.pending_title is not None:
                table.title = table.title or normalize_text(self.pending_title.content)
                self.pending_title = None
            owner = self.levels.get(1) or self.section
            table.owner_key = owner.key
            owner.table_ids.append(table.table_id)
            self.tables.append(table)
            self.post_table = table if b.kind is BlockKind.PIPE_TABLE else None
            self.fragment_mode = False
            return
        content = normalize_text(b.content)
        is_heading = b.kind is BlockKind.HEADING
        if (is_heading or b.kind is BlockKind.PARAGRAPH) and _COLUMN_FRAGMENT.match(content):
            self._fragment(b, "detached column header")
            return
        if self._is_table_title(b, nxt, content):
            self.pending_title = b
            return
        if self.fragment_mode or self.post_table is not None:
            if self._starts_provision(b):
                self.fragment_mode = False
                self.post_table = None
            elif (
                self.fragment_mode
                or _ROW_FRAGMENT.match(content)
                or (self.post_table is not None and content[:1].islower())
            ):
                self._fragment(b, "table text outside a structured row")
                return
            else:
                self.post_table = None
        if is_heading:
            p.warn("demoted_heading", f"heading inside section {self.section.key} kept as text", b)
        if b.kind is BlockKind.PARAGRAPH and self._is_standalone_label(b, nxt, content):
            self.label = content
            self.pending_label = p.spans.for_block(b)
            return
        self._paragraph(b)

    def _is_table_title(self, b: _Block, nxt: _Block | None, content: str) -> bool:
        if nxt is None or len(content) > 120 or len(b.lines) != 1:
            return False
        bold = bool(re.fullmatch(r"\*\*[^*]+\*\*", b.content.strip()))
        if not (b.kind is BlockKind.HEADING or bold):
            return False
        nxt_text = normalize_text(nxt.content)
        return nxt.kind in (BlockKind.HTML_TABLE, BlockKind.PIPE_TABLE) or bool(_COLUMN_FRAGMENT.match(nxt_text))

    def _is_standalone_label(self, b: _Block, nxt: _Block | None, content: str) -> bool:
        if len(b.lines) != 1 or len(content) > 80 or not content or content[-1] in ".;:,":
            return False
        if _MARKER.match(content + " ") or _NOTE.match(content + " ") or _PENALTY.match(content + " "):
            return False
        if nxt is None or nxt.kind is not BlockKind.PARAGRAPH:
            return False
        return bool(re.match(r"^\s*\(\d+[A-Z]*\)\s", normalize_text(nxt.content)))

    def _starts_provision(self, b: _Block) -> bool:
        first = b.lines[0].text
        stripped = re.sub(r"^\s*(?:\*[^*]{1,80}\*\s+){1,4}", "", first)
        match = re.match(r"^\s*\((\d+[A-Z]*)\)\s", stripped)
        if match is None:
            return False
        return self.last_sub is None or _num_key(match.group(1)) > self.last_sub

    def _content_class(self) -> ContentClass:
        return ContentClass.SIMPLIFIED_OUTLINE if self.outline else ContentClass.BODY_PROVISION

    # -- table fragments --
    def _fragment(self, b: _Block, reason: str) -> None:
        p = self.p
        self.fragment_mode = True
        table = self.post_table or (self.tables[-1] if self.tables and self.tables[-1].fragments else None)
        if table is None:
            table = TableRecord(
                table_id=p.next_table_id(),
                region=Region.BODY,
                content_class=self._content_class(),
                section_key=self.section.key,
                owner_key=(self.levels.get(1) or self.section).key,
                status=TableStatus.UNRESOLVED,
            )
            if self.pending_title is not None:
                table.title = normalize_text(self.pending_title.content)
                table.fragments.append(
                    TableFragment(text=table.title, span=p.spans.for_block(self.pending_title), reason="table title")
                )
                self.pending_title = None
            p.tables.append(table)
            self.tables.append(table)
            (self.levels.get(1) or self.section).table_ids.append(table.table_id)
        self.post_table = table
        table.fragments.append(TableFragment(text=normalize_text(b.content), span=p.spans.for_block(b), reason=reason))

    def _finalize_tables(self) -> None:
        section_text = self.p.section_text(self.section.key)
        referenced = {int(n) for n in re.findall(r"\bcolumn\s+(\d+)\s+of\s+the\s+table", section_text, re.I)}
        non_act = {
            int(n)
            for n in re.findall(
                r"information in column\s+(\d+)\s+of the table is not part of this Act", section_text, re.I
            )
        }
        for table in self.tables:
            present = {c.column_number for c in table.columns if c.column_number is not None}
            if present and referenced - present:
                missing = ", ".join(str(n) for n in sorted(referenced - present))
                table.issues.append(f"section text refers to column(s) {missing} absent from the table")
            if table.fragments:
                table.issues.append(f"{len(table.fragments)} detached fragment(s) could not be associated with rows")
            if not table.rows and not table.fragments:
                table.issues.append("table has no data rows")
            for column in table.columns:
                if column.column_number in non_act:
                    column.classification = "non_operative_information"
            if table.issues:
                table.status = TableStatus.UNRESOLVED
            if table.status is TableStatus.UNRESOLVED:
                self.p.warn(
                    "unresolved_table",
                    f"table {table.table_id} in {self.section.key}: " + "; ".join(table.issues),
                    None,
                    clause_key=self.section.key,
                    span=table.span or (table.fragments[0].span if table.fragments else None),
                )

    # -- paragraphs --
    def _paragraph(self, b: _Block) -> None:
        for line in b.lines:
            for seg in self._split(line.text, line.start):
                self._apply(seg, b)

    def _split(self, line: str, base: int) -> list[_Segment]:
        cands: list[_Segment] = []
        taken: set[int] = set()
        for m in _ITALIC_LABEL.finditer(line):
            before = line[: m.start()]
            if not before.strip() or _INLINE_BEFORE.search(before):
                cands.append(_Segment("label", base + m.start(), 0, normalize_text(m.group(1)), bool(before.strip())))
                taken.add(m.end())
        for m in _MARKER.finditer(line):
            before = line[: m.start()]
            line_start = not before.strip() or bool(re.fullmatch(r"\s*\*\*?", before))
            if m.start() in taken:
                cands.append(_Segment("marker", base + m.start(), 0, m.group(1), True))
            elif line_start:
                cands.append(_Segment("marker", base + m.start(), 0, m.group(1), False))
            elif _INLINE_BEFORE.search(before):
                if m.group(1)[0].isdigit() and not _SENTENCE_START.match(line[m.end() :]):
                    continue
                cands.append(_Segment("marker", base + m.start(), 0, m.group(1), True))
        for regex, kind in ((_PENALTY, "penalty"), (_NOTE, "note")):
            for m in regex.finditer(line):
                before = line[: m.start()]
                if not before.strip() or re.search(r"[.;]\*?\s+$", before):
                    token = f"{m.group(1).lower()}{m.group(2) or ''}" if kind == "note" else None
                    cands.append(_Segment(kind, base + m.start(), 0, token, bool(before.strip())))
        if definition := _DEFINITION.match(line):
            term = re.split(r"\s+(?:means|has|includes)\b|[:,]", normalize_text(definition.group(1)))[0].strip()
            if term:
                cands.append(_Segment("definition", base + definition.start(1) - 3, 0, term))
        cands.sort(key=lambda s: s.start)
        segments: list[_Segment] = []
        first = cands[0].start if cands else base + len(line)
        if line[: first - base].strip():
            segments.append(_Segment("text", base, first))
        for i, cand in enumerate(cands):
            cand.end = cands[i + 1].start if i + 1 < len(cands) else base + len(line)
            segments.append(cand)
        return segments

    def _apply(self, seg: _Segment, b: _Block) -> None:
        p = self.p
        span = p.spans.make(seg.start, seg.end, b.page_label)
        if seg.kind == "label":
            self.label = seg.token
            self.pending_label = span
            return
        if seg.kind == "marker" and seg.token is not None:
            level = self._accept_marker(seg.token, seg.inline)
            if level is not None:
                self._open(level, seg.token, span)
                return
            if not seg.inline:
                p.warn("non_sequential_marker", f"({seg.token}) does not continue numbering", b, span=span)
        elif seg.kind == "penalty":
            self._leave_note()
            parent = self.levels.get(1) or self.section
            self.current = self._child(parent, ProvisionKind.PENALTY, "penalty", ContentClass.PENALTY)
        elif seg.kind == "note":
            self._leave_note()
            parent = self.def_ctx or self.levels.get(1) or self.section
            self.current = self._child(parent, ProvisionKind.NOTE, seg.token or "note", ContentClass.NOTE)
            # Lists inside a note belong to the note, not to the provision's own list.
            self.levels_before_note = {k: v for k, v in self.levels.items() if k > 1}
            for lvl in (2, 3, 4):
                self.levels.pop(lvl, None)
            self.note_ctx = self.current
        elif seg.kind == "definition" and seg.token is not None:
            self._leave_note()
            parent = self.levels.get(1) or self.section
            node = self._child(parent, ProvisionKind.DEFINITION, f"def:{seg.token}", ContentClass.DEFINITION)
            node.title = seg.token
            for lvl in (2, 3, 4):
                self.levels.pop(lvl, None)
            self.def_ctx = node
            self.current = node
        self._add_text(self.current, span)

    def _leave_note(self) -> None:
        if self.note_ctx is not None:
            for lvl in (2, 3, 4):
                self.levels.pop(lvl, None)
            self.levels.update(self.levels_before_note)
            self.note_ctx = None
            self.levels_before_note = {}

    def _accept_marker(self, token: str, inline: bool) -> int | None:
        if self.note_ctx is not None and not token[0].isdigit():
            level = self._fit_marker(token, True)
            if level is not None:
                return level
            self._leave_note()  # the marker continues the list that preceded the note
        return self._fit_marker(token, inline)

    def _fit_marker(self, token: str, inline: bool) -> int | None:
        if token[0].isdigit():
            key = _num_key(token)
            if self.last_sub is None or key > self.last_sub:
                return 1
            return None
        par, sub, subsub = self.levels.get(2), self.levels.get(3), self.levels.get(4)
        if token.isupper():
            if subsub is not None and subsub.number and token in _letter_successors(subsub.number.lower().upper()):
                return 4
            if sub is not None and token == "A":
                return 4
            return None if inline or sub is None else 4
        roman = bool(_ROMAN.match(token))
        if sub is not None and sub.number and roman and _roman_value(token) == _roman_value(sub.number) + 1:
            return 3
        if par is not None and par.number and token in _letter_successors(par.number):
            return 2
        if par is not None and token == "i":
            return 3
        if token == "a":
            return 2
        if inline:
            return None
        return 3 if roman and par is not None else 2

    def _open(self, level: int, token: str, span: SourceSpan) -> None:
        kinds = {
            1: ProvisionKind.SUBSECTION,
            2: ProvisionKind.PARAGRAPH,
            3: ProvisionKind.SUBPARAGRAPH,
            4: ProvisionKind.SUBSUBPARAGRAPH,
        }
        container = self.note_ctx or self.def_ctx
        if level == 1:
            self._leave_note()
            parent = self.section
            self.def_ctx = None
            self.last_sub = _num_key(token)
            container = None
        elif level == 2:
            parent = container or self.levels.get(1) or self.section
        else:
            parent = next((self.levels[k] for k in range(level - 1, 1, -1) if k in self.levels), None) or (
                container or self.levels.get(1) or self.section
            )
        if container is self.note_ctx and container is not None:
            content_class = ContentClass.NOTE
        elif container is not None:
            content_class = ContentClass.DEFINITION
        else:
            content_class = self._content_class()
        node = self.p.add_node(
            ProvisionNode(
                key=f"{parent.key}({token})",
                kind=kinds[level],
                number=token,
                parent_key=parent.key,
                content_class=content_class,
            )
        )
        if level == 1:
            node.label = self.label
            if self.pending_label is not None:
                self._add_text(node, self.pending_label)
        self.pending_label = None
        for lvl in range(level, 5):
            self.levels.pop(lvl, None)
        self.levels[level] = node
        self.current = node
        self._add_text(node, span)

    def _child(self, parent: ProvisionNode, kind: ProvisionKind, stem: str, cls: ContentClass) -> ProvisionNode:
        counter_key = f"{parent.key}/{stem}"
        self.counters[counter_key] = self.counters.get(counter_key, 0) + 1
        count = self.counters[counter_key]
        if kind is ProvisionKind.DEFINITION or stem[-1].isdigit():
            key = counter_key if count == 1 else f"{counter_key}#{count}"
        else:
            key = f"{counter_key}{count}"
        if kind is ProvisionKind.DEFINITION and count > 1:
            self.p.warn("duplicate_definition", f"{stem} defined more than once in {parent.key}", None, clause_key=key)
        if self.pending_label is not None and kind is not ProvisionKind.DEFINITION:
            self._add_text(self.current, self.pending_label)
            self.pending_label = None
        return self.p.add_node(ProvisionNode(key=key, kind=kind, parent_key=parent.key, content_class=cls))

    def _add_text(self, node: ProvisionNode, span: SourceSpan) -> None:
        self.p.add_span(node, span)


class _LegislationParser:
    def __init__(self, text: str, artifact_id: str, available_assets: frozenset[str]) -> None:
        self.text = text
        self.artifact_id = artifact_id
        self.available_assets = available_assets
        self.lines = _split_lines(text)
        self.spans = _SpanFactory(text, self.lines, artifact_id)
        self.blocks = _segment(self.lines)
        self.provisions: dict[str, ProvisionNode] = {}
        self.order: list[str] = []
        self.raw_parts: dict[str, list[SourceSpan]] = {}
        self.tables: list[TableRecord] = []
        self.warnings: list[ParseWarning] = []
        self.title: str | None = None
        self._table_seq = 0

    # -- shared helpers used by the section builder --
    def warn(
        self,
        code: str,
        message: str,
        block: _Block | None,
        *,
        clause_key: str | None = None,
        span: SourceSpan | None = None,
    ) -> None:
        if span is None and block is not None:
            span = self.spans.for_block(block)
        self.warnings.append(ParseWarning(code=code, message=message, span=span, clause_key=clause_key))

    def image_warning(self, block: _Block) -> None:
        match = _IMAGE.match(block.lines[0].text)
        target = match.group(1) if match else block.joined
        if target not in self.available_assets:
            self.warn("image_unavailable", f"image {target!r} is referenced but not supplied; not fetched", block)

    def next_table_id(self) -> str:
        self._table_seq += 1
        return f"t{self._table_seq:03d}"

    def add_node(self, node: ProvisionNode) -> ProvisionNode:
        if node.key in self.provisions:
            base = node.key
            n = 2
            while f"{base}#dup{n}" in self.provisions:
                n += 1
            node.key = f"{base}#dup{n}"
            self.warn("duplicate_provision", f"{base} occurs more than once", None, clause_key=node.key)
        self.provisions[node.key] = node
        self.order.append(node.key)
        if node.parent_key:
            self.provisions[node.parent_key].children.append(node.key)
        return node

    def add_span(self, node: ProvisionNode, span: SourceSpan) -> None:
        # Keep a heading's own span separate so node text can exclude it.
        heading_only = node.kind in _HEADED_KINDS and len(node.spans) == 1
        _append_span(node.spans, span, self.text, merge=not heading_only)

    def section_text(self, section_key: str) -> str:
        keys = [section_key]
        out: list[str] = []
        while keys:
            node = self.provisions[keys.pop(0)]
            out.extend(self.text[s.char_start : s.char_end] for s in node.spans)
            keys = node.children + keys
        return normalize_text(" ".join(out))

    def table_from_block(self, block: _Block, content_class: ContentClass, section_key: str | None) -> TableRecord:
        if block.kind is BlockKind.HTML_TABLE:
            rows = _parse_html_rows(block, self.text)
            header_rows = None
        else:
            rows, has_header = _parse_pipe_rows(block)
            header_rows = 1 if has_header else 0
        table = _build_table(
            rows,
            self.spans,
            block.page_label,
            table_id=self.next_table_id(),
            region=block.region,
            content_class=content_class,
            header_rows=header_rows,
        )
        table.section_key = section_key
        table.span = self.spans.for_block(block)
        self.tables.append(table)
        return table

    # -- passes --
    def parse(self) -> ParsedLegislation:
        front_matter = self._front_matter()
        self._classify_furniture()
        self._assign_regions()
        self._assign_page_labels()
        cover = self._cover_facts()
        for block in self.blocks:
            if block.kind is BlockKind.IMAGE:
                self.image_warning(block)
        self._body()
        repeals = self._endnotes()
        for key in self.order:
            node = self.provisions[key]
            own = node.spans[1:] if node.kind in _HEADED_KINDS else node.spans
            node.text = normalize_text(" ".join(self.text[s.char_start : s.char_end] for s in own))
            if node.kind in (ProvisionKind.PARAGRAPH, ProvisionKind.SUBPARAGRAPH, ProvisionKind.SUBSUBPARAGRAPH):
                if m := re.search(r";\s*(and|or)$", node.text):
                    node.list_connective = m.group(1)
        parsed = ParsedLegislation(
            artifact_id=self.artifact_id,
            text_sha256=sha256_hex(self.text.encode("utf-8")),
            front_matter=front_matter,
            cover_facts=cover,
            blocks=[
                Block(
                    index=b.index,
                    kind=b.kind,
                    region=b.region,
                    span=self.spans.for_block(b),
                    level=b.level,
                    furniture=b.furniture,
                )
                for b in self.blocks
            ],
            provisions=self.provisions,
            order=self.order,
            tables=self.tables,
            repeals=repeals,
            warnings=self.warnings,
        )
        from .references import extract_definitions, extract_references

        parsed.definitions = extract_definitions(parsed, self.text)
        parsed.references = extract_references(parsed, self.text)
        return parsed

    def _front_matter(self) -> dict[str, Any] | None:
        for block in self.blocks:
            if block.kind is BlockKind.FRONT_MATTER:
                block.region = Region.FRONT_MATTER
                body = "\n".join(line.text for line in block.lines[1:-1])
                loaded = yaml.safe_load(body)
                return loaded if isinstance(loaded, dict) else None
        return None

    def _classify_furniture(self) -> None:
        blocks = self.blocks
        for b in blocks:
            if b.kind is BlockKind.PAGE_BREAK:
                b.furniture = FurnitureKind.PAGE_BREAK
            elif b.kind is BlockKind.SEPARATOR:
                b.furniture = FurnitureKind.LAYOUT_SEPARATOR
        for i, b in enumerate(blocks):
            if b.kind not in (BlockKind.HEADING, BlockKind.PARAGRAPH) or len(b.lines) != 1:
                continue
            prev = blocks[i - 1] if i > 0 else None
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            if prev and prev.kind is BlockKind.PAGE_BREAK and nxt and nxt.kind is BlockKind.SEPARATOR:
                b.furniture = FurnitureKind.RUNNING_HEADER
            elif prev and prev.kind is BlockKind.SEPARATOR and (nxt is None or nxt.kind is BlockKind.PAGE_BREAK):
                b.furniture = FurnitureKind.PAGE_FOOTER

    def _assign_regions(self) -> None:
        blocks = self.blocks
        texts = [lookup_key(b.content) if b.kind in (BlockKind.HEADING, BlockKind.PARAGRAPH) else "" for b in blocks]

        def first(pred: Callable[[int], bool], start: int = 0) -> int | None:
            return next((i for i in range(start, len(blocks)) if blocks[i].furniture is None and pred(i)), None)

        for b in blocks:
            if b.kind is BlockKind.HEADING and b.level == 1 and b.furniture is None:
                self.title = normalize_text(b.content)
                break
        contents = first(lambda i: texts[i] == "contents")
        about = first(lambda i: texts[i] == "about this compilation")
        body = first(
            lambda i: (
                blocks[i].kind is BlockKind.HEADING
                and _classify_heading(blocks[i].content) is not None
                and not texts[i].startswith("an act")
            ),
            contents if contents is not None else 0,
        )
        body = body if body is not None else len(blocks)
        endnotes = first(lambda i: blocks[i].kind is BlockKind.HEADING and texts[i] == "endnotes", body)
        endnotes = endnotes if endnotes is not None else len(blocks)
        for i, b in enumerate(blocks):
            if b.kind is BlockKind.FRONT_MATTER:
                continue
            if i >= endnotes:
                b.region = Region.ENDNOTES
            elif i >= body:
                b.region = Region.BODY
            elif texts[i].startswith("an act ") and b.furniture is None:
                b.region = Region.LONG_TITLE
            elif contents is not None and i >= contents:
                b.region = Region.CONTENTS
            elif about is not None and i >= about:
                b.region = Region.COMPILATION_NOTES
            else:
                b.region = Region.COVER

    def _assign_page_labels(self) -> None:
        pending: list[_Block] = []
        title = lookup_key(self.title) if self.title else None
        for b in self.blocks:
            if b.kind is BlockKind.PAGE_BREAK:
                pending = []
                continue
            pending.append(b)
            if b.furniture is FurnitureKind.PAGE_FOOTER:
                label = self._footer_label(b.joined, title)
                if label is not None:
                    for item in pending:
                        item.page_label = label
                pending = []

    @staticmethod
    def _footer_label(footer: str, title: str | None) -> str | None:
        match = re.match(r"^\s*\*([^*]+)\*", footer)
        if not match or not title:
            return None
        inner = lookup_key(match.group(1))
        if title not in inner:
            return None
        rest = inner.replace(title, " ").strip()
        return rest if re.fullmatch(r"\d+|[ivxlc]+", rest) else None

    def _cover_facts(self) -> dict[str, FactClaim]:
        facts: dict[str, FactClaim] = {}
        months = {
            m: i
            for i, m in enumerate(
                [
                    "january",
                    "february",
                    "march",
                    "april",
                    "may",
                    "june",
                    "july",
                    "august",
                    "september",
                    "october",
                    "november",
                    "december",
                ],
                start=1,
            )
        }

        def put(name: str, value: Any, block: _Block) -> None:
            if name not in facts:
                facts[name] = FactClaim(value=value, span=self.spans.for_block(block))

        for b in self.blocks:
            if b.region is not Region.COVER or b.furniture is not None:
                continue
            text = normalize_text(b.content)
            if b.kind is BlockKind.HEADING and b.level == 1:
                put("title", text, b)
            if m := re.fullmatch(r"(?:Act\s+)?No\.\s*(\d+),\s*(\d{4})", text):
                put("act_number", f"{int(m.group(1))}/{m.group(2)}", b)
            if m := re.fullmatch(r"Compilation No\.\s*(\d+)", text):
                put("compilation_number", int(m.group(1)), b)
            if m := re.fullmatch(r"Compilation date:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text):
                month = months.get(m.group(2).lower())
                if month:
                    put("compilation_date", date(int(m.group(3)), month, int(m.group(1))), b)
            if m := re.fullmatch(r"Includes amendments:\s*(.+)", text):
                put("includes_amendments", m.group(1), b)
        footer_dates: dict[date, _Block] = {}
        for b in self.blocks:
            if b.furniture is FurnitureKind.PAGE_FOOTER:
                if m := re.search(r"Compilation date:\s*(\d{2})/(\d{2})/(\d{4})", b.joined):
                    footer_dates.setdefault(date(int(m.group(3)), int(m.group(2)), int(m.group(1))), b)
        if len(footer_dates) == 1:
            ((value, block),) = footer_dates.items()
            put("footer_compilation_date", value, block)
        elif len(footer_dates) > 1:
            self.warn("inconsistent_footer", f"page footers state {len(footer_dates)} compilation dates", None)
        return facts

    def _body(self) -> None:
        stack: list[ProvisionNode] = []
        builder: _SectionBuilder | None = None
        sections: list[tuple[int, tuple[int, str]]] = []
        for b in self.blocks:
            if b.region is Region.BODY and b.kind is BlockKind.HEADING and b.furniture is None:
                cls = _classify_heading(b.content)
                if cls and cls[0] is ProvisionKind.SECTION:
                    sections.append((b.index, _num_key(cls[1])))
        next_section_of = {
            idx: (sections[i + 1][1] if i + 1 < len(sections) else None) for i, (idx, _) in enumerate(sections)
        }
        current_bounds: tuple[tuple[int, str], tuple[int, str] | None] | None = None

        for b in self.blocks:
            if b.region is not Region.BODY:
                continue
            if b.kind is BlockKind.HEADING and b.furniture is None:
                cls = _classify_heading(b.content)
                if cls is not None:
                    kind, number, title = cls
                    if builder is not None:
                        builder.finish()
                        builder = None
                    if kind is ProvisionKind.SECTION:
                        schedule = next((n for n in stack if n.kind is ProvisionKind.SCHEDULE), None)
                        prefix = f"{schedule.key}/" if schedule else ""
                        node = self.add_node(
                            ProvisionNode(
                                key=f"{prefix}s{number}",
                                kind=kind,
                                number=number,
                                title=title,
                                parent_key=stack[-1].key if stack else None,
                            )
                        )
                        if title.casefold().startswith("simplified outline"):
                            node.content_class = ContentClass.SIMPLIFIED_OUTLINE
                        self.add_span(node, self.spans.for_block(b))
                        builder = _SectionBuilder(self, node)
                        current_bounds = (_num_key(number), next_section_of.get(b.index))
                    else:
                        while stack and _RANK[stack[-1].kind] >= _RANK[kind]:
                            stack.pop()
                        parent = stack[-1] if stack else None
                        key = f"{parent.key}/" if parent else ""
                        node = self.add_node(
                            ProvisionNode(
                                key=f"{key}{_KEY_PREFIX[kind]}{number}",
                                kind=kind,
                                number=number,
                                title=title,
                                parent_key=parent.key if parent else None,
                            )
                        )
                        self.add_span(node, self.spans.for_block(b))
                        stack.append(node)
                        current_bounds = None
                    continue
            if builder is not None:
                if b.kind is BlockKind.PARAGRAPH and b.furniture is None and current_bounds is not None:
                    self._check_unmarked_section(b, current_bounds)
                builder.blocks.append(b)
            elif b.furniture is None and b.kind not in (BlockKind.SEPARATOR, BlockKind.PAGE_BREAK):
                if b.kind is not BlockKind.IMAGE and stack:
                    self.add_span(stack[-1], self.spans.for_block(b))
        if builder is not None:
            builder.finish()

    def _check_unmarked_section(self, b: _Block, bounds: tuple[tuple[int, str], tuple[int, str] | None]) -> None:
        match = re.match(r"^(\d+[A-Z]*)\s+[A-Z][a-z]", normalize_text(b.lines[0].text))
        if not match:
            return
        key = _num_key(match.group(1))
        low, high = bounds
        if key > low and (high is None or key < high):
            self.warn(
                "possible_unmarked_section_heading",
                f"text looks like the heading of section {match.group(1)} but is not marked as a heading; "
                "no section node was created",
                b,
            )

    def _endnotes(self) -> list[RepealEntry]:
        repeals: list[RepealEntry] = []
        content_class = ContentClass.COMPILATION_INFORMATION
        pattern = re.compile(
            r"(?:^|(?<=\s)|(?<=\|))s\s+(\d+[A-Z]*)\s*(?:\|\s*|\.{3,}\s*)(rep\b[^|.]*?)(?=\s*\||\s+s\s+\d|\s*$)"
        )
        for b in self.blocks:
            if b.region is not Region.ENDNOTES or b.furniture is not None:
                continue
            if b.kind is BlockKind.HEADING and lookup_key(b.content).startswith("endnote"):
                content_class = (
                    ContentClass.AMENDMENT_HISTORY
                    if "amendment history" in lookup_key(b.content)
                    else ContentClass.COMPILATION_INFORMATION
                )
                continue
            if b.kind in (BlockKind.HTML_TABLE, BlockKind.PIPE_TABLE):
                self.table_from_block(b, content_class, None)
            if content_class is ContentClass.AMENDMENT_HISTORY:
                for line in b.lines:
                    for m in pattern.finditer(line.text):
                        repeals.append(
                            RepealEntry(
                                provision=f"s{m.group(1)}",
                                how=normalize_text(m.group(2)),
                                span=self.spans.make(line.start + m.start(), line.start + m.end(), b.page_label),
                            )
                        )
        return repeals


def read_front_matter(text: str) -> dict[str, Any] | None:
    """Return the YAML front matter mapping (safe loader), or ``None`` when there is none."""
    lines = _split_lines(text)
    for block in _segment(lines[:400]):
        if block.kind is BlockKind.FRONT_MATTER:
            loaded = yaml.safe_load("\n".join(line.text for line in block.lines[1:-1]))
            return loaded if isinstance(loaded, dict) else None
        return None
    return None


def parse_legislation_markdown(
    text: str, artifact_id: str, *, available_assets: Iterable[str] = ()
) -> ParsedLegislation:
    """Parse a legislation rendering (structured Markdown with HTML tables, or a LiteParse export).

    ``available_assets`` lists image paths supplied alongside the artifact; anything else is reported
    as unavailable and never fetched.
    """
    return _LegislationParser(text, artifact_id, frozenset(available_assets)).parse()


# --------------------------------------------------------------------------------------------
# Comparison against independently reviewed expectations (DB-007 / DB-008 offline step)
# --------------------------------------------------------------------------------------------


class InventoryComparison(BaseModel):
    missing: list[str]
    duplicates: list[str]
    unexpected: list[str]
    out_of_order: list[str]

    @property
    def matches(self) -> bool:
        return not (self.missing or self.duplicates or self.unexpected or self.out_of_order)


def compare_section_inventory(parsed: ParsedLegislation, expected: Sequence[str]) -> InventoryComparison:
    found = parsed.section_numbers()
    found_set, expected_set = set(found), set(expected)
    duplicates = sorted(n for n, count in Counter(found).items() if count > 1)
    common_found = [n for n in dict.fromkeys(found) if n in expected_set]
    common_expected = [n for n in expected if n in found_set]
    out_of_order = [a for a, b in zip(common_found, common_expected, strict=False) if a != b]
    return InventoryComparison(
        missing=[n for n in expected if n not in found_set],
        duplicates=duplicates,
        unexpected=[n for n in dict.fromkeys(found) if n not in expected_set],
        out_of_order=out_of_order,
    )


# --------------------------------------------------------------------------------------------
# Metadata import and reconciliation (DB-005)
# --------------------------------------------------------------------------------------------


def _no_containers(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        raise ValueError("metadata fields must be scalars")
    return value


def _iso_date(value: Any) -> Any:
    _no_containers(value)
    if isinstance(value, date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value)
    raise ValueError(f"expected an ISO date (YYYY-MM-DD), got {value!r}")


_Str = Annotated[str, BeforeValidator(_no_containers)]
_Date = Annotated[date, BeforeValidator(_iso_date)]


class LegislationMetadata(BaseModel):
    """Provider-supplied metadata (JSON sidecar or YAML front matter). Claims, not verified facts."""

    model_config = ConfigDict(strict=True, extra="allow", frozen=True)

    title: _Str
    identifier: _Str
    register_id: _Str | None = None
    type: _Str | None = None
    principal: bool | None = None
    number: _Str | None = None
    jurisdiction: _Str | None = None
    language: _Str | None = None
    date: _Date | None = None
    compilation_number: int | None = None
    last_amended: _Date | None = None
    version_start: _Date | None = None
    status: _Str | None = None
    source: _Str | None = None
    retrieved: _Date | None = None

    @field_validator("identifier", "register_id")
    @classmethod
    def _identifier(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
            raise ValueError(f"invalid identifier {value!r}")
        return value


def load_sidecar_json(data: bytes) -> LegislationMetadata:
    return LegislationMetadata.model_validate(json.loads(data.decode("utf-8")))


def front_matter_metadata(parsed: ParsedLegislation) -> LegislationMetadata | None:
    return LegislationMetadata.model_validate(parsed.front_matter) if parsed.front_matter else None


class MetadataBasis(StrEnum):
    PROVIDER_SIDECAR = "provider_sidecar"
    PROVIDER_FRONT_MATTER = "provider_front_matter"
    IMPORT_MANIFEST = "import_manifest"
    COVER_TEXT = "cover_text"
    PAGE_FOOTER = "page_footer"
    REVIEWED_SOURCE_FACT = "reviewed_source_fact"


#: Bases whose values were read from the legal text itself (or reviewed against it).
VERIFIED_BASES = frozenset({MetadataBasis.COVER_TEXT, MetadataBasis.PAGE_FOOTER, MetadataBasis.REVIEWED_SOURCE_FACT})


class MetadataClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    value: str | int | bool | date
    basis: MetadataBasis
    artifact_id: str
    span: SourceSpan | None = None


class FieldReconciliation(BaseModel):
    field: str
    status: str  # agreed | single_source | conflict
    value: str | int | bool | date | None
    claims: list[MetadataClaim]


class MetadataReconciliation(BaseModel):
    fields: dict[str, FieldReconciliation]

    @property
    def conflicts(self) -> list[FieldReconciliation]:
        return [f for f in self.fields.values() if f.status == "conflict"]

    def value(self, name: str) -> Any:
        entry = self.fields.get(name)
        return entry.value if entry and entry.status != "conflict" else None

    def provider_claims(self) -> list[MetadataClaim]:
        return [c for f in self.fields.values() for c in f.claims if c.basis not in VERIFIED_BASES]

    def verified_claims(self) -> list[MetadataClaim]:
        return [c for f in self.fields.values() for c in f.claims if c.basis in VERIFIED_BASES]


def legal_time_from(reconciliation: MetadataReconciliation, *, observed_at: datetime | None = None) -> LegalTime:
    """Build legal time from agreed claims only; conflicting or missing dates stay unknown."""

    def as_date(name: str) -> date | None:
        value = reconciliation.value(name)
        if isinstance(value, str):
            return date.fromisoformat(value)
        return value if isinstance(value, date) else None

    version_start = as_date("version_start")
    return LegalTime(
        original_enactment_date=as_date("original_enactment_date"),
        compilation_date=as_date("compilation_date"),
        version_start=version_start,
        last_amended=as_date("last_amended"),
        registration_date=as_date("registration_date"),
        retrieved_on=as_date("retrieved_on"),
        effective_from=version_start,
        observed_at=observed_at,
    )


def _act_number(value: str) -> str | None:
    match = re.search(r"No\.?\s*(\d+)\s*,\s*(\d{4})", value)
    return f"{int(match.group(1))}/{match.group(2)}" if match else None


def claims_from_metadata(meta: LegislationMetadata, basis: MetadataBasis, artifact_id: str) -> list[MetadataClaim]:
    """Map provider fields onto claim names that keep their distinct legal meanings."""
    mapping: dict[str, Any] = {
        "title": meta.title,
        "principal_identifier": meta.identifier,
        "register_id": meta.register_id,
        "act_number": _act_number(meta.number) if meta.number else None,
        "original_enactment_date": meta.date,
        "compilation_number": meta.compilation_number,
        "last_amended": meta.last_amended,
        "version_start": meta.version_start,
        "retrieved_on": meta.retrieved,
        "jurisdiction": meta.jurisdiction,
        "language": meta.language,
        "status": meta.status,
    }
    return [
        MetadataClaim(field=name, value=value, basis=basis, artifact_id=artifact_id)
        for name, value in mapping.items()
        if value is not None
    ]


def claims_from_cover(parsed: ParsedLegislation) -> list[MetadataClaim]:
    claims = []
    for name, fact in parsed.cover_facts.items():
        basis = MetadataBasis.PAGE_FOOTER if name.startswith("footer_") else MetadataBasis.COVER_TEXT
        field_name = name.removeprefix("footer_")
        claims.append(
            MetadataClaim(
                field=field_name, value=fact.value, basis=basis, artifact_id=parsed.artifact_id, span=fact.span
            )
        )
    return claims


def _comparable(field_name: str, value: Any) -> Any:
    if isinstance(value, str):
        return lookup_key(value)
    return value


def reconcile_claims(claims: Iterable[MetadataClaim]) -> MetadataReconciliation:
    """Agreement is recorded per field; disagreement is a reviewable conflict, never silent precedence."""
    grouped: dict[str, list[MetadataClaim]] = {}
    for claim in claims:
        grouped.setdefault(claim.field, []).append(claim)
    fields: dict[str, FieldReconciliation] = {}
    for name, items in grouped.items():
        distinct = {_comparable(name, c.value) for c in items}
        if len(distinct) > 1:
            fields[name] = FieldReconciliation(field=name, status="conflict", value=None, claims=items)
        else:
            sources = {(c.basis, c.artifact_id) for c in items}
            status = "agreed" if len(sources) > 1 else "single_source"
            fields[name] = FieldReconciliation(field=name, status=status, value=items[0].value, claims=items)
    return MetadataReconciliation(fields=fields)
