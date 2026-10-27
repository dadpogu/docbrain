"""Moved from src/docbrain/parsing.py (process application). Relies on parsing.py imports and helpers."""

# --------------------------------------------------------------------------------------------
# Operational documents: processes, work instructions, templates, site facts (DB-031)
# --------------------------------------------------------------------------------------------


class DocumentFinding(BaseModel):
    code: str
    message: str
    text: str
    span: SourceSpan | None = None


class DocSection(BaseModel):
    title: str
    level: int
    anchor: str
    span: SourceSpan


class StatedValue(BaseModel):
    """A numeric value with a unit as written in the source. Not a verified limit."""

    text: str
    normalized: str
    span: SourceSpan


class OperationalDocument(BaseModel):
    artifact_id: str
    text_sha256: str
    title: str | None = None
    doc_kind: str | None = None
    declared_id: str | None = None
    revision: str | None = None
    claimed_status: str | None = None
    owner: str | None = None
    approver: str | None = None
    fields: dict[str, str] = {}
    sections: list[DocSection] = []
    tables: list[TableRecord] = []
    stated_values: list[StatedValue] = []
    findings: list[DocumentFinding] = []

    def findings_of(self, code: str) -> list[DocumentFinding]:
        return [f for f in self.findings if f.code == code]


_FIELD = re.compile(r"^\s*\*\*([^*:]{1,60}):\*\*\s*(.*?)\s*$")
_ID_FIELD = re.compile(r"^(?:(?:process|wi|work instruction|document|form|policy|procedure|manual)\s+)?id$", re.I)
_TBC = re.compile(r"\[TBC[^\]]*\]")
_VARIABLE = re.compile(r"\b(torque|pressure|temperature|rate|limit|setting|speed|value)\s+([xX]|X{2,})\b", re.I)
_BRACKET = re.compile(r"(?<!!)\[(?!TBC)(?!!)([^\]\n]{1,120})\](?!\()")
_TEMPLATE_ID = re.compile(r"\b[A-Z]{1,4}-X{2,}\b|\bY{4}-M{2}-D{2}\b")
_LINK = re.compile(r"(?<!!)\[([^\]\n]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_QUANTITY = re.compile(
    r"(?<![\w.])(?:[<>≤≥]\s*)?\d+(?:\.\d+)?(?:\s*[–-]\s*\d+(?:\.\d+)?)?\s*"
    r"(?:°C/min|°C|%|PSI|psi|kPa|bar|kg/hour|kg/h|kg|h|min|L)(?![\w/])"
)


def heading_anchor(title: str) -> str:
    """GitHub-style heading anchor."""
    anchor = unicodedata.normalize("NFKC", title).strip().lower()
    anchor = re.sub(r"[^\w\- ]", "", anchor)
    return anchor.replace(" ", "-")


def parse_operational_markdown(
    text: str, artifact_id: str, *, link_exists: Callable[[str], bool] | None = None
) -> OperationalDocument:
    """Parse a process/work-instruction/policy/template document without asserting it is approved.

    ``link_exists`` resolves relative link targets; when omitted, path links are not checked.
    Placeholders, unresolved variables, and broken links become findings, not repaired content.
    """
    lines = _split_lines(text)
    spans = _SpanFactory(text, lines, artifact_id)
    blocks = _segment(lines)
    doc = OperationalDocument(artifact_id=artifact_id, text_sha256=sha256_hex(text.encode("utf-8")))
    if not text.strip():
        doc.findings.append(DocumentFinding(code="empty_document", message="document has no content", text=""))
        return doc

    for block in blocks:
        if block.kind is BlockKind.HEADING:
            title = normalize_text(block.content)
            doc.sections.append(
                DocSection(
                    title=title,
                    level=block.level or 1,
                    anchor=heading_anchor(block.content.replace("*", "")),
                    span=spans.for_block(block),
                )
            )
            if block.level == 1 and doc.title is None:
                doc.title = title
                if ":" in title:
                    doc.doc_kind = title.split(":", 1)[0].strip()
        elif block.kind is BlockKind.PIPE_TABLE:
            rows, has_header = _parse_pipe_rows(block)
            table = _build_table(
                rows,
                spans,
                None,
                table_id=f"t{len(doc.tables) + 1:03d}",
                region=Region.BODY,
                content_class=ContentClass.BODY_PROVISION,
                header_rows=1 if has_header else 0,
            )
            table.span = spans.for_block(block)
            doc.tables.append(table)
    for line in lines:
        if m := _FIELD.match(line.text):
            doc.fields.setdefault(m.group(1).strip(), normalize_text(m.group(2)))

    for name, value in doc.fields.items():
        if _ID_FIELD.match(name) and doc.declared_id is None:
            doc.declared_id = value.split()[0] if value else None
    for name in ("Version", "Revision"):
        if name in doc.fields and doc.revision is None:
            doc.revision = doc.fields[name].split()[0] if doc.fields[name] else None
            if m := re.search(r"\(([^)]*\b(?:draft|approved|superseded|obsolete)\b[^)]*)\)", doc.fields[name], re.I):
                doc.claimed_status = m.group(1)
    doc.claimed_status = doc.fields.get("Status", doc.claimed_status)
    doc.owner = doc.fields.get("Owner") or doc.fields.get("Document Owner")
    doc.approver = doc.fields.get("Approver")

    anchors = {s.anchor for s in doc.sections}
    in_code = False
    for line in lines:
        if _FENCE.match(line.text):
            in_code = not in_code
            continue
        if in_code:
            continue

        def find(code: str, message: str, m: re.Match[str], base: int = line.start) -> None:
            doc.findings.append(
                DocumentFinding(
                    code=code, message=message, text=m.group(0), span=spans.make(base + m.start(), base + m.end())
                )
            )

        for m in _TBC.finditer(line.text):
            find("placeholder_tbc", "value marked to be confirmed", m)
        for m in _VARIABLE.finditer(line.text):
            find("unresolved_variable", "parameter given as an unresolved variable", m)
        for m in _TEMPLATE_ID.finditer(line.text):
            find("template_placeholder", "template identifier/date placeholder", m)
        for m in _BRACKET.finditer(line.text):
            if not m.group(1).startswith("!"):
                find("template_placeholder", "bracketed placeholder text", m)
        for m in _LINK.finditer(line.text):
            target = m.group(2)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            path, _, fragment = target.partition("#")
            if not path:
                if fragment not in anchors:
                    find("missing_reference", f"in-document anchor #{fragment} does not exist", m)
            elif link_exists is not None and not link_exists(unquote(path)):
                find("missing_reference", f"linked document {path!r} is not available", m)
        for m in _QUANTITY.finditer(line.text):
            doc.stated_values.append(
                StatedValue(
                    text=m.group(0),
                    normalized=re.sub(r"\s+", "", m.group(0)).lower(),
                    span=spans.make(line.start + m.start(), line.start + m.end()),
                )
            )
    return doc
