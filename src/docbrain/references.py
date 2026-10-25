"""Clause references and scoped definitions (DB-010).

References are extracted from each provision's own source spans, so every reference keeps an exact
span. Resolution never corrects the source: unknown targets become ``unresolved`` warnings, other
Acts are ``external_unavailable`` unless supplied, and provisions recorded as repealed in the
amendment history are ``explicitly_repealed``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel

from .models import (
    DefinitionEntry,
    ParsedLegislation,
    ParseWarning,
    ProvisionKind,
    ProvisionNode,
    Reference,
    ReferenceKind,
    ReferenceStatus,
    SourceSpan,
    TableStatus,
)
from .parsing import lookup_key, normalize_text

_NUM = r"\d+[A-Z]*(?!\.\d|\d)"
_PARTS = r"(?:\([0-9A-Za-z]{1,5}\))+"
_ACT = r"\*?((?:[A-Z][\w'’()-]*\s+)+(?:Act(?:\s+\d{4})?|Code)|Constitution)\*?"
_LIST_SEP = r"\s*(?:,|and|or|to)\s*"

_EXTERNAL = re.compile(
    rf"\b((?:sections?|subsections?|paragraphs?)\s+[\d.A-Za-z()]+(?:{_LIST_SEP}[\d.A-Za-z()]+)*)\s+of\s+the\s+{_ACT}"
)
_SAME_MEANING = re.compile(rf"(?:same meaning as in|within the meaning of)\s+the\s+{_ACT}")
_TABLE_ITEMS = re.compile(
    rf"\bitems?\s+(\d+(?:{_LIST_SEP}\d+)*)\s+of\s+the\s+table\s+in\s+(?:sub)?section\s+({_NUM})(\(\d+[A-Z]*\))?"
)
_PARAGRAPH_ABS = re.compile(rf"\bparagraphs?\s+({_NUM})({_PARTS})((?:{_LIST_SEP}\([0-9A-Za-z]{{1,5}}\))*)")
_PARAGRAPH_REL = re.compile(rf"\bparagraphs?\s+({_PARTS})((?:{_LIST_SEP}\([0-9A-Za-z]{{1,5}}\))*)")
_SUBSECTION_ABS = re.compile(rf"\bsubsections?\s+({_NUM})(\(\d+[A-Z]*\))((?:{_LIST_SEP}\(\d+[A-Z]*\))*)")
_SUBSECTION_REL = re.compile(rf"\bsubsections?\s+(\(\d+[A-Z]*\)(?:{_LIST_SEP}\(\d+[A-Z]*\))*)")
_SECTION = re.compile(rf"\bsections?\s+({_NUM}(?:{_LIST_SEP}{_NUM})*)")


_STRUCTURAL_KINDS = frozenset(
    {
        ProvisionKind.CHAPTER,
        ProvisionKind.PART,
        ProvisionKind.DIVISION,
        ProvisionKind.SUBDIVISION,
        ProvisionKind.SCHEDULE,
    }
)


def _section_part(key: str) -> str:
    match = re.match(r"(s\d+[A-Z]*)", key)
    return match.group(1) if match else key


def _expand_numbers(text: str) -> list[int]:
    out: list[int] = []
    for start, end in re.findall(r"(\d+)(?:\s*to\s*(\d+))?", text):
        a = int(start)
        out.extend(range(a, int(end) + 1) if end else [a])
    return out


def _span_in(node_span: SourceSpan, text: str, start: int, end: int) -> SourceSpan:
    base = node_span.char_start
    prefix = text[base : base + start]
    line_start = node_span.line_start + prefix.count("\n")
    return node_span.model_copy(
        update={
            "char_start": base + start,
            "char_end": base + end,
            "line_start": line_start,
            "line_end": line_start + text[base + start : base + end].count("\n"),
        }
    )


class _Extractor:
    def __init__(self, parsed: ParsedLegislation, text: str, available_acts: frozenset[str]) -> None:
        self.parsed = parsed
        self.text = text
        self.available_acts = {lookup_key(a) for a in available_acts}
        self.repealed = {r.provision: r for r in parsed.repeals}
        self.sections = [n.number for n in parsed.nodes(ProvisionKind.SECTION) if n.number]
        self.this_act = lookup_key(str(parsed.cover_facts["title"].value)) if "title" in parsed.cover_facts else None

    def run(self) -> list[Reference]:
        refs: list[Reference] = []
        for key in self.parsed.order:
            node = self.parsed.provisions[key]
            if node.kind in _STRUCTURAL_KINDS:
                continue
            for i, span in enumerate(node.spans):
                if node.kind is ProvisionKind.SECTION and i == 0:
                    continue  # the section heading itself
                refs.extend(self._scan(node, span))
        return refs

    def _section_range(self, a: str, b: str) -> list[str]:
        if a in self.sections and b in self.sections:
            i, j = self.sections.index(a), self.sections.index(b)
            if i <= j:
                return self.sections[i : j + 1]
        return [a, b]

    def _status(self, targets: list[str]) -> tuple[ReferenceStatus, str | None]:
        missing = [t for t in targets if t not in self.parsed.provisions]
        if not missing:
            return ReferenceStatus.RESOLVED, None
        repealed = [self.repealed[s] for s in (_section_part(t) for t in missing) if s in self.repealed]
        if repealed and len(repealed) == len(missing):
            history = ", ".join(sorted({f"{r.provision} {r.how}" for r in repealed}))
            return ReferenceStatus.EXPLICITLY_REPEALED, f"amendment history records: {history}"
        return ReferenceStatus.UNRESOLVED, f"no provision {', '.join(missing)} in this rendering"

    def _scan(self, node: ProvisionNode, span: SourceSpan) -> list[Reference]:
        # Match on text without emphasis markers (parsers split italics mid-title), mapping positions back.
        source = self.text[span.char_start : span.char_end]
        keep = [i for i, ch in enumerate(source) if ch != "*"]
        raw = "".join(source[i] for i in keep)
        keep.append(len(source))
        section = self.parsed.section_of(node.key)
        sec_key = section.key if section else None
        sub_key = self._enclosing_subsection(node)
        taken: list[tuple[int, int]] = []
        refs: list[Reference] = []

        def free(m: re.Match[str]) -> bool:
            return all(m.end() <= a or m.start() >= b for a, b in taken)

        def add(m: re.Match[str], kind: ReferenceKind, targets: list[str], **extra: object) -> None:
            taken.append((m.start(), m.end()))
            start, end = keep[m.start()], keep[m.end() - 1] + 1
            ref = Reference(
                kind=kind,
                raw_text=normalize_text(m.group(0)),
                source_key=node.key,
                span=_span_in(span, self.text, start, end),
                targets=targets,
                **extra,
            )
            refs.append(ref)

        for m in _EXTERNAL.finditer(raw):
            act = normalize_text(m.group(2))
            if self.this_act and lookup_key(act) == self.this_act:
                continue
            add(
                m,
                ReferenceKind.EXTERNAL_ACT,
                [],
                target_act=act,
                status=self._act_status(act),
                note=f"{normalize_text(m.group(1))} of another Act",
            )
        for m in _SAME_MEANING.finditer(raw):
            if free(m):
                act = normalize_text(m.group(1))
                add(m, ReferenceKind.EXTERNAL_ACT, [], target_act=act, status=self._act_status(act))
        for m in _TABLE_ITEMS.finditer(raw):
            if not free(m):
                continue
            owner = f"s{m.group(2)}{m.group(3) or ''}"
            items = [str(n) for n in _expand_numbers(m.group(1))]
            status, note = self._table_status(owner, items)
            add(m, ReferenceKind.TABLE_ITEMS, [owner], table_items=items, status=status, note=note)
        for m in _PARAGRAPH_ABS.finditer(raw):
            if free(m):
                head = f"s{m.group(1)}{m.group(2)}"
                targets = [head] + [self._sibling(head, t) for t in re.findall(r"\(([0-9A-Za-z]+)\)", m.group(3))]
                add(m, ReferenceKind.PARAGRAPH, targets, status=self._status(targets)[0], note=self._status(targets)[1])
        for m in _SUBSECTION_ABS.finditer(raw):
            if free(m):
                targets = [f"s{m.group(1)}{m.group(2)}"] + [
                    f"s{m.group(1)}({t})" for t in re.findall(r"\((\d+[A-Z]*)\)", m.group(3))
                ]
                status, note = self._status(targets)
                add(m, ReferenceKind.SUBSECTION, targets, status=status, note=note)
        for m in _PARAGRAPH_REL.finditer(raw):
            if free(m) and sec_key:
                head_parts = m.group(1)
                if head_parts[1].isdigit():
                    base = sec_key
                else:
                    base = self._list_owner(node, head_parts[1:].split(")")[0]) or sub_key or sec_key
                head = f"{base}{head_parts}"
                targets = [head] + [self._sibling(head, t) for t in re.findall(r"\(([0-9A-Za-z]+)\)", m.group(2))]
                status, note = self._status(targets)
                add(m, ReferenceKind.PARAGRAPH, targets, status=status, note=note)
        for m in _SUBSECTION_REL.finditer(raw):
            if free(m) and sec_key:
                targets = [f"{sec_key}({t})" for t in re.findall(r"\((\d+[A-Z]*)\)", m.group(1))]
                status, note = self._status(targets)
                add(m, ReferenceKind.SUBSECTION, targets, status=status, note=note)
        for m in _SECTION.finditer(raw):
            if not free(m):
                continue
            tokens = re.findall(rf"({_NUM})|(\bto\b)", m.group(1))
            numbers: list[str] = []
            pending_range = False
            for number, is_to in tokens:
                if is_to:
                    pending_range = True
                elif pending_range and numbers:
                    numbers.extend(self._section_range(numbers.pop(), number))
                    pending_range = False
                else:
                    numbers.append(number)
            targets = [f"s{n}" for n in dict.fromkeys(numbers)]
            status, note = self._status(targets)
            add(m, ReferenceKind.SECTION, targets, status=status, note=note)
        return refs

    def _list_owner(self, node: ProvisionNode, token: str) -> str | None:
        """Nearest enclosing provision that has a child numbered ``token`` (e.g. a definition's list)."""
        current: ProvisionNode | None = node
        while current is not None:
            if f"{current.key}({token})" in self.parsed.provisions:
                return current.key
            current = self.parsed.provisions.get(current.parent_key) if current.parent_key else None
        return None

    def _sibling(self, head: str, token: str) -> str:
        return re.sub(r"\([0-9A-Za-z]+\)$", f"({token})", head)

    def _enclosing_subsection(self, node: ProvisionNode) -> str | None:
        current: ProvisionNode | None = node
        while current is not None:
            if current.kind is ProvisionKind.SUBSECTION:
                return current.key
            current = self.parsed.provisions.get(current.parent_key) if current.parent_key else None
        return None

    def _act_status(self, act: str) -> ReferenceStatus:
        return (
            ReferenceStatus.RESOLVED if lookup_key(act) in self.available_acts else ReferenceStatus.EXTERNAL_UNAVAILABLE
        )

    def _table_status(self, owner: str, items: list[str]) -> tuple[ReferenceStatus, str | None]:
        tables = [t for t in self.parsed.tables if t.owner_key == owner]
        if not tables:
            return ReferenceStatus.UNRESOLVED, f"no table owned by {owner}"
        if any(t.status is TableStatus.UNRESOLVED for t in tables):
            return ReferenceStatus.AMBIGUOUS, f"the table in {owner} has unresolved row associations"
        keys = {r.key for t in tables for r in t.rows}
        missing = [i for i in items if i not in keys]
        if missing:
            return ReferenceStatus.UNRESOLVED, f"items {', '.join(missing)} not found in {owner}"
        return ReferenceStatus.RESOLVED, None


def extract_references(parsed: ParsedLegislation, text: str, *, available_acts: Iterable[str] = ()) -> list[Reference]:
    refs = _Extractor(parsed, text, frozenset(available_acts)).run()
    for ref in refs:
        if ref.status in (ReferenceStatus.UNRESOLVED, ReferenceStatus.AMBIGUOUS):
            parsed.warnings.append(
                ParseWarning(
                    code=f"{ref.status.value}_reference",
                    message=f"{ref.raw_text!r} in {ref.source_key}: {ref.note}",
                    span=ref.span,
                    clause_key=ref.source_key,
                )
            )
    return refs


# --------------------------------------------------------------------------------------------
# Definitions
# --------------------------------------------------------------------------------------------

_INLINE_DEFINED = re.compile(
    r"\((?:a|an|the|each a|each an)\s+\*\*\*([^*]+)\*\*\*\)|\*\*\*([^*]+)\*\*\*\s+(?:means|includes|has the meaning)\b"
)
_SCOPE_PHRASE = re.compile(r"\bIn this (Act|Chapter|Part|Division|Subdivision|section|subsection)\b")
_QUALIFIER = re.compile(r"^,\s*((?:for|in relation to|in)\b[^,]*?),\s*(?:has|means|includes)\b")


def _scope_for(parsed: ParsedLegislation, node: ProvisionNode) -> tuple[str, str | None]:
    section = parsed.section_of(node.key)
    candidates: list[ProvisionNode] = []
    parent = parsed.provisions.get(node.parent_key) if node.parent_key else None
    if parent is not None:
        candidates.append(parent)
    if section is not None and section is not parent:
        candidates.append(section)
    for candidate in candidates:
        phrases = _SCOPE_PHRASE.findall(candidate.text)
        if phrases:
            word = phrases[-1].lower()
            if word == "act":
                return "act", None
            if word in ("section", "subsection"):
                return "section", section.key if section else None
            ancestor = next((a for a in parsed.ancestry(node.key) if a.kind.value == word), None)
            return word, ancestor.key if ancestor else None
    return "section", section.key if section else None


def extract_definitions(parsed: ParsedLegislation, text: str) -> list[DefinitionEntry]:
    entries: list[DefinitionEntry] = []
    for key in parsed.order:
        node = parsed.provisions[key]
        if node.kind is ProvisionKind.DEFINITION and node.title:
            scope_kind, scope_key = _scope_for(parsed, node)
            body = node.text[len(node.title) :] if node.text.startswith(node.title) else node.text
            qualifier = _QUALIFIER.match(body)
            external = _SAME_MEANING.search(" ".join(text[s.char_start : s.char_end] for s in node.spans))
            entries.append(
                DefinitionEntry(
                    term=node.title,
                    defined_in=node.key,
                    scope_kind=scope_kind,
                    scope_key=scope_key,
                    qualifier=qualifier.group(1) if qualifier else None,
                    external_act=normalize_text(external.group(1)) if external else None,
                    text=parsed.full_text(node.key),
                    spans=node.spans,
                )
            )
        elif node.kind is not ProvisionKind.DEFINITION:
            section = parsed.section_of(node.key)
            for span in node.spans:
                raw = text[span.char_start : span.char_end]
                for m in _INLINE_DEFINED.finditer(raw):
                    entries.append(
                        DefinitionEntry(
                            term=normalize_text(m.group(1) or m.group(2)),
                            defined_in=node.key,
                            scope_kind="section",
                            scope_key=section.key if section else None,
                            text=node.text,
                            spans=[_span_in(span, text, m.start(), m.end())],
                        )
                    )
    return entries


class TermResolution(BaseModel):
    term: str
    status: str  # resolved | external_unavailable | qualified_only | ambiguous | not_found
    definition: DefinitionEntry | None = None
    candidates: list[DefinitionEntry] = []
    notes: list[str] = []


def resolve_term(parsed: ParsedLegislation, term: str, at_key: str) -> TermResolution:
    """Resolve ``term`` as used in provision ``at_key``: local scope first, never a qualified definition."""
    wanted = lookup_key(term)
    candidates = [d for d in parsed.definitions if lookup_key(d.term) == wanted]
    section = parsed.section_of(at_key)
    ancestors = {a.key for a in parsed.ancestry(at_key)}

    def notes_for(entry: DefinitionEntry) -> list[str]:
        node = parsed.provisions.get(entry.defined_in)
        if node is None:
            return []
        return [parsed.provisions[c].text for c in node.children if parsed.provisions[c].kind is ProvisionKind.NOTE]

    def result(matches: list[DefinitionEntry]) -> TermResolution:
        if len(matches) > 1:
            return TermResolution(term=term, status="ambiguous", candidates=matches)
        entry = matches[0]
        status = "external_unavailable" if entry.external_act else "resolved"
        return TermResolution(term=term, status=status, definition=entry, candidates=candidates, notes=notes_for(entry))

    local = [d for d in candidates if d.scope_kind == "section" and section and d.scope_key == section.key]
    if local:
        return result(local)
    structural = [d for d in candidates if d.scope_kind not in ("act", "section") and d.scope_key in ancestors]
    if structural:
        return result(structural)
    act_wide = [d for d in candidates if d.scope_kind == "act" and d.qualifier is None]
    if act_wide:
        return result(act_wide)
    qualified = [d for d in candidates if d.qualifier is not None]
    if qualified:
        return TermResolution(
            term=term,
            status="qualified_only",
            candidates=qualified,
            notes=[f"defined only {d.qualifier}" for d in qualified],
        )
    return TermResolution(term=term, status="not_found", candidates=candidates)
