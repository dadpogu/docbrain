#!/usr/bin/env python3
"""Convert a Federal Register of Legislation EPUB or DOCX rendition into Markdown.

Usage: convert.py INPUT.epub|INPUT.docx [-o OUTPUT.md]

Both formats are reduced to the same HTML-like tree (Word paragraph and character styles
as classes, direct run formatting as inline CSS) and rendered by one Markdown emitter, so
the EPUB and DOCX renditions of a compilation produce the same Markdown.
"""
import argparse
import os
import re
import zipfile

from lxml import etree

XHTML = "{http://www.w3.org/1999/xhtml}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
DC = "{http://purl.org/dc/elements/1.1/}"

# Paragraph class -> heading level (H1 is the title of the instrument).
HEADINGS = {
    # current OPC drafting templates (Acts and instruments)
    "ActHead1": 2,   # Chapter
    "ActHead2": 3,   # Part
    "ActHead3": 4,   # Division
    "ActHead4": 5,   # Subdivision
    "ActHead5": 6,   # section / regulation / rule
    "ActHead6": 2,   # Schedule
    "ActHead7": 3,   # Part of a Schedule
    "ActHead8": 4,   # Division of a Schedule
    "ActHead9": 5,   # Act/instrument amended by a Schedule
    "ENotesHeading1": 2,
    "ENotesHeading2": 3,
    "ENotesHeading3": 4,
    # older templates
    "HC": 2, "HP": 3, "HD": 4, "HS": 5, "HR": 6,
    "Scheduletitle": 2, "ScheduleTitle": 2, "ScheduleHeading": 2,
    "EndNotes": 2, "ENotesHeading": 2,
}
SKIP_CLASSES = re.compile(r"^(TOC\d*|Header|Footer|ContentsHead|ContentsSectionBreak|NotesSectionBreak|"
                          r"SchedSectionBreak|ContentsPage)$")
BLOCK = {"p", "table", "h1", "h2", "h3", "h4", "h5", "h6", "li", "img", "hr"}
SPACES = re.compile(r"[ \t\r\n     ​]+")


def local(el):
    t = el.tag
    if not isinstance(t, str):
        return ""
    return t.split("}", 1)[-1].lower()


def style_of(el):
    return el.get("style") or ""


def is_tab_span(el):
    st = style_of(el)
    return "inline-block" in st and "width" in st


CSS_FONT = re.compile(r"font-(style|weight):([\w-]+)")


def css_emphasis(decls, it=None, bd=None):
    """Apply font-style/font-weight declarations to (italic, bold); None means unset."""
    for prop, val in CSS_FONT.findall(decls.replace(" ", "").lower()):
        if prop == "style":
            it = val in ("italic", "oblique")
        else:
            bd = val in ("bold", "bolder") or (val.isdigit() and int(val) >= 600)
    return it, bd


def emphasis(e, styles, it, bd):
    """(italic, bold) of element e: inherited, then its style classes, then inline CSS."""
    for c in (e.get("class") or "").split():
        cit, cbd = styles.get(c, (None, None))
        it = it if cit is None else cit
        bd = bd if cbd is None else cbd
    it, bd = css_emphasis(style_of(e), it, bd)
    name = local(e)
    return it or name in ("i", "em"), bd or name in ("b", "strong")


def inline(el, styles):
    """Return Markdown inline text of an element (recursively)."""
    segs = []  # (text, italic, bold) ; text "\x00BR\x00" = line break

    def add(t, it, bd):
        if t:
            segs.append((t, it, bd))

    def walk(e, it=False, bd=False):
        name = local(e)
        if name in ("script", "style"):
            pass
        elif name == "br":
            add("\x00BR\x00", False, False)
        elif name == "img":
            alt = (e.get("alt") or "").strip()
            add(f"[image{': ' + alt if alt else ''}]", False, False)
        else:
            nit, nbd = emphasis(e, styles, it, bd)
            if name == "span" and is_tab_span(e):
                add(" ", nit, nbd)
            else:
                add(e.text, nit, nbd)
                for c in e:
                    if not isinstance(c.tag, str):
                        add(c.tail, nit, nbd)
                    else:
                        walk(c, nit, nbd)
        if e is not el:
            add(e.tail, it, bd)

    walk(el)
    # merge runs with identical formatting; whitespace-only runs join neighbours
    runs = []
    for t, it, bd in segs:
        if t == "\x00BR\x00":
            runs.append([t, False, False])
            continue
        if runs and runs[-1][0] != "\x00BR\x00" and (
                (runs[-1][1], runs[-1][2]) == (it, bd) or not SPACES.sub("", t)):
            runs[-1][0] += t
        else:
            runs.append([t, it, bd])
    out = []
    for t, it, bd in runs:
        t = SPACES.sub(" ", t)
        if t == "\x00BR\x00":
            out.append(t)
            continue
        e = esc(t)
        core = e.strip()
        if core and (it or bd):
            lead = " " if e[:1] == " " else ""
            trail = " " if e[-1:] == " " else ""
            if bd:
                core = f"**{core}**"
            if it:
                core = f"*{core}*"
            e = lead + core + trail
        out.append(e)
    s = SPACES.sub(" ", "".join(out))
    s = re.sub(r" ?\x00BR\x00 ?", "\x00BR\x00", s)
    s = re.sub(r"^(\x00BR\x00)+|(\x00BR\x00)+$", "", s.strip()).strip()
    return s


def esc(t):
    t = t.replace("\\", "\\\\").replace("*", "\\*").replace("`", "\\`")
    t = t.replace("<", "&lt;").replace(">", "&gt;") if ("<" in t or ">" in t) else t
    return t


LEADING = re.compile(r"^(#{1,6}\s|[-+]\s|>|\d+[.)](\s|$)|={3,}|-{3,}|_{3,})")


def para(text):
    if LEADING.match(text):
        if text[0].isdigit():
            m = re.match(r"^(\d+)([.)])", text)
            text = m.group(1) + "\\" + m.group(2) + text[m.end():]
        else:
            text = "\\" + text
    return text.replace("\x00BR\x00", "\\\n")


def plain(text):
    """Strip Markdown emphasis for headings."""
    t = text.replace("\x00BR\x00", " ")
    t = re.sub(r"(?<!\\)\*+", "", t)
    return SPACES.sub(" ", t).strip()


def cell_text(td, styles):
    parts = []
    blocks = [c for c in td.iter() if local(c) in ("p", "li", "h1", "h2", "h3", "h4", "h5", "h6")]
    if blocks:
        for b in blocks:
            if any(local(a) in ("p", "li") for a in b.iterancestors() if a is not td and td in a.iterancestors()):
                continue
            t = inline(b, styles)
            if t:
                parts.append(t)
    else:
        t = inline(td, styles)
        if t:
            parts.append(t)
    return "<br>".join(p.replace("\x00BR\x00", "<br>") for p in parts)


def render_table(tbl, styles):
    rows = []
    complex_ = False
    for tr in tbl.iter(XHTML + "tr", "tr"):
        # skip rows of nested tables (handled as complex)
        if next((a for a in tr.iterancestors() if local(a) == "table"), None) is not tbl:
            complex_ = True
            continue
        cells = []
        for td in tr:
            if local(td) not in ("td", "th"):
                continue
            cs, rs = int(td.get("colspan", "1") or 1), int(td.get("rowspan", "1") or 1)
            if cs > 1 or rs > 1:
                complex_ = True
            cells.append((cell_text(td, styles), cs, rs, local(td) == "th"))
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    ncols = max(sum(c[1] for c in r) for r in rows)
    if ncols == 1 and not complex_:
        # single-column box: render as paragraphs
        return "\n\n".join(para(r[0][0].replace("<br>", "\x00BR\x00")) for r in rows if r[0][0])
    if not complex_:
        width = max(len(r) for r in rows)
        lines = []
        for i, r in enumerate(rows):
            vals = [c[0].replace("|", "\\|") for c in r] + [""] * (width - len(r))
            lines.append("| " + " | ".join(vals) + " |")
            if i == 0:
                lines.append("|" + "---|" * width)
        return "\n".join(lines)
    # complex table: minimal HTML
    out = ["<table>"]
    for r in rows:
        out.append("<tr>")
        for txt, cs, rs, th in r:
            tag = "th" if th else "td"
            attrs = (f' colspan="{cs}"' if cs > 1 else "") + (f' rowspan="{rs}"' if rs > 1 else "")
            out.append(f"<{tag}{attrs}>{md_inline_to_html(txt)}</{tag}>")
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def md_inline_to_html(t):
    # cell text is Markdown-escaped; convert emphasis to HTML inside HTML blocks
    t = re.sub(r"(?<!\\)\*\*(.+?)(?<!\\)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\\)\*(.+?)(?<!\\)\*", r"<i>\1</i>", t)
    return t.replace("\\*", "*").replace("\\\\", "\\").replace("\\`", "`")


def iter_blocks(body):
    """Yield block-level elements in document order, not descending into tables."""
    stack = [iter(body)]
    while stack:
        try:
            e = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        n = local(e)
        if not n:
            continue
        if n in BLOCK:
            yield e
            continue
        if n in ("ul", "ol", "div", "blockquote", "section", "tbody", "thead", "center", "a", "span", "font"):
            # inline-ish container holding text directly (rare): treat as paragraph
            if n in ("a", "span", "font"):
                yield e
                continue
            stack.append(iter(e))
            continue
        yield e


def epub_spine(z):
    """(HTML files in spine order, dc:title or None) of an EPUB package."""
    names = [n for n in z.namelist() if n.lower().endswith((".html", ".xhtml", ".htm"))]
    opf = next((n for n in z.namelist() if n.endswith(".opf")), None)
    if opf:
        try:
            root = etree.fromstring(z.read(opf))
            ns = {"o": "http://www.idpf.org/2007/opf"}
            items = {i.get("id"): i.get("href") for i in root.iterfind(".//o:manifest/o:item", ns)}
            base = os.path.dirname(opf)
            order = [os.path.normpath(os.path.join(base, items[r.get("idref")])).replace("\\", "/")
                     for r in root.iterfind(".//o:spine/o:itemref", ns) if r.get("idref") in items]
            order = [n for n in order if n in names]
            title = (root.findtext(f".//{DC}title") or "").strip() or None
            return order or sorted(names), title
        except etree.XMLSyntaxError:
            pass
    return sorted(names), None


def parse_html(data):
    parser = etree.HTMLParser(encoding="utf-8", remove_comments=True)
    try:
        root = etree.fromstring(data, etree.XMLParser(recover=True, huge_tree=True, remove_comments=True))
        if root is None or root.find(".//" + XHTML + "body") is None:
            raise etree.XMLSyntaxError("no body", None, 0, 0)
        return root.find(".//" + XHTML + "body")
    except etree.XMLSyntaxError:
        root = etree.fromstring(data, parser)
        return root.find(".//body")


def css_classes(css):
    """Class name -> (italic, bold) from the font rules of a stylesheet (None = unset)."""
    out = {}
    for sels, decls in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        fmt = css_emphasis(decls)
        if fmt == (None, None):
            continue
        for sel in sels.split(","):
            m = re.fullmatch(r"\s*[a-z0-9]*\.([\w-]+)\s*", sel)
            if m:
                out[m.group(1)] = fmt
    return out


def read_epub(path):
    with zipfile.ZipFile(path) as z:
        names, title = epub_spine(z)
        styles = {}
        for n in z.namelist():
            if n.lower().endswith(".css"):
                styles.update(css_classes(z.read(n).decode("utf-8", "replace")))
        bodies = [b for b in (parse_html(z.read(n)) for n in names) if b is not None]
    return bodies, styles, title


# --- DOCX: translate WordprocessingML into the tree the EPUB renditions use -----------------

# inline containers whose runs are part of the text (deleted/moved-from text and mc:Fallback are not)
DOCX_INLINE_WRAPPERS = {W + "hyperlink", W + "ins", W + "moveTo", W + "smartTag", W + "customXml",
                        W + "fldSimple", W + "sdt", W + "sdtContent", MC + "AlternateContent", MC + "Choice"}
DOCX_IMAGES = {W + "drawing", W + "pict", W + "object"}


def on_off(rpr, tag):
    """Value of a WordprocessingML toggle property (w:b, w:i, w:vanish): True, False or None if unset."""
    el = rpr.find(W + tag) if rpr is not None else None
    if el is None:
        return None
    return el.get(W + "val", "true").lower() not in ("0", "false", "off")


def docx_styles(xml):
    """Style id -> (italic, bold), following basedOn chains (nearest definition wins)."""
    raw = {}
    for s in etree.fromstring(xml).iter(W + "style"):
        based = s.find(W + "basedOn")
        rpr = s.find(W + "rPr")
        raw[s.get(W + "styleId")] = (based.get(W + "val") if based is not None else None,
                                     on_off(rpr, "i"), on_off(rpr, "b"))

    def resolve(sid, seen):
        based, it, bd = raw[sid]
        if based in raw and based not in seen and (it is None or bd is None):
            bit, bbd = resolve(based, seen | {sid})
            it, bd = (bit if it is None else it), (bbd if bd is None else bd)
        return it, bd

    return {sid: resolve(sid, {sid}) for sid in raw}


def append_text(e, s):
    if len(e):
        e[-1].tail = (e[-1].tail or "") + s
    else:
        e.text = (e.text or "") + s


def docx_run(r, out):
    rpr = r.find(W + "rPr")
    if on_off(rpr, "vanish"):
        return
    span = etree.SubElement(out, "span")
    if rpr is not None:
        rstyle = rpr.find(W + "rStyle")
        if rstyle is not None:
            span.set("class", rstyle.get(W + "val"))
        css = []
        it, bd = on_off(rpr, "i"), on_off(rpr, "b")
        if it is not None:
            css.append("font-style:" + ("italic" if it else "normal"))
        if bd is not None:
            css.append("font-weight:" + ("bold" if bd else "normal"))
        if css:
            span.set("style", "; ".join(css))
    for c in r:
        if c.tag == W + "t":
            append_text(span, c.text or "")
        elif c.tag == W + "tab":
            append_text(span, "\t")
        elif c.tag == W + "noBreakHyphen":
            append_text(span, "\u2011")
        elif c.tag == W + "cr" or (c.tag == W + "br" and c.get(W + "type", "textWrapping") == "textWrapping"):
            etree.SubElement(span, "br")
        elif c.tag in DOCX_IMAGES or (c.tag == MC + "AlternateContent" and c.find(f".//{W}drawing") is not None):
            pr = next(c.iterfind(".//{*}docPr"), None)
            etree.SubElement(span, "img", alt=(pr.get("descr") or pr.get("title") or "") if pr is not None else "")
        # w:softHyphen is an optional break point: no text


def docx_inline(el, out):
    for c in el:
        if c.tag == W + "r":
            docx_run(c, out)
        elif c.tag in DOCX_INLINE_WRAPPERS:
            docx_inline(c, out)


def docx_table(tbl):
    """w:tbl -> table; gridSpan becomes colspan and vMerge runs become rowspan."""
    rows = []
    for tr in tbl.iterchildren(W + "tr"):
        before = tr.find(f"{W}trPr/{W}gridBefore")
        col, cells = int(before.get(W + "val")) if before is not None else 0, []
        for tc in tr.iterchildren(W + "tc"):
            span = tc.find(f"{W}tcPr/{W}gridSpan")
            span = int(span.get(W + "val")) if span is not None else 1
            vm = tc.find(f"{W}tcPr/{W}vMerge")
            vm = None if vm is None else vm.get(W + "val", "continue")
            cells.append((col, tc, span, vm))
            col += span
        rows.append(cells)
    table = etree.Element("table")
    for i, cells in enumerate(rows):
        tr = etree.SubElement(table, "tr")
        if cells and cells[0][0]:  # gridBefore: keep later cells in their grid columns
            pad = etree.SubElement(tr, "td")
            if cells[0][0] > 1:
                pad.set("colspan", str(cells[0][0]))
        for col, tc, span, vm in cells:
            if vm == "continue":
                continue
            rowspan = 1
            if vm == "restart":
                while i + rowspan < len(rows) and any(
                        c[0] == col and c[3] == "continue" for c in rows[i + rowspan]):
                    rowspan += 1
            td = etree.SubElement(tr, "td")
            if span > 1:
                td.set("colspan", str(span))
            if rowspan > 1:
                td.set("rowspan", str(rowspan))
            docx_blocks(tc, td)
    return table


def docx_blocks(el, out):
    for c in el:
        if c.tag == W + "p":
            p = etree.SubElement(out, "p")
            style = c.find(f"{W}pPr/{W}pStyle")
            if style is not None:
                p.set("class", style.get(W + "val"))
            docx_inline(c, p)
        elif c.tag == W + "tbl":
            out.append(docx_table(c))
        elif c.tag in (W + "sdt", W + "sdtContent", W + "customXml"):
            docx_blocks(c, out)


def read_docx(path):
    xml_parser = etree.XMLParser(huge_tree=True)
    with zipfile.ZipFile(path) as z:
        doc = etree.fromstring(z.read("word/document.xml"), xml_parser)
        names = set(z.namelist())
        styles = docx_styles(z.read("word/styles.xml")) if "word/styles.xml" in names else {}
        core = etree.fromstring(z.read("docProps/core.xml")) if "docProps/core.xml" in names else None
    body = etree.Element("body")
    docx_blocks(doc.find(W + "body"), body)
    title = (core.findtext(f"{DC}title") or "").strip() if core is not None else ""
    return [body], styles, title or None


# --- Markdown -----------------------------------------------------------------------------------

def render(bodies, styles):
    """(title from the ShortT paragraph or None, Markdown blocks) of the document bodies."""
    out = []
    title = None
    first_img = True
    for body in bodies:
        for e in iter_blocks(body):
            n = local(e)
            cls = (e.get("class") or "").strip()
            if SKIP_CLASSES.match(cls):
                continue
            if n == "table":
                t = render_table(e, styles)
                if t:
                    out.append(t)
                continue
            if n == "hr":
                continue
            if n == "img":
                if first_img:
                    first_img = False
                    continue
                alt = (e.get("alt") or "").strip()
                out.append(f"[image{': ' + alt if alt else ''}]")
                continue
            # paragraph-like
            imgs = e.findall(".//" + XHTML + "img") + e.findall(".//img")
            if imgs and first_img and not "".join(e.itertext()).strip():
                first_img = False
                continue
            if imgs:
                first_img = False
            t = inline(e, styles)
            if not t:
                continue
            if title is None and cls in ("ShortT", "Title", "ShortTP1"):
                title = plain(t)
                continue
            lvl = HEADINGS.get(cls)
            if lvl is None and n[0] == "h" and n[1:].isdigit():
                lvl = min(int(n[1:]) + 1, 6)
            if lvl:
                h = plain(t)
                if h:
                    out.append("#" * lvl + " " + h)
                continue
            if cls in ("ItemHead", "ItemHeadNoNum"):
                out.append("**" + plain(t).replace("*", "\\*") + "**")
                continue
            out.append(para(t))
    return title, out


def convert(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".epub":
        bodies, styles, meta_title = read_epub(path)
    elif ext == ".docx":
        bodies, styles, meta_title = read_docx(path)
    else:
        raise SystemExit(f"unsupported input (expected .epub or .docx): {path}")
    title, blocks = render(bodies, styles)
    title = title or meta_title or os.path.splitext(os.path.basename(path))[0]
    text = f"# {title}\n\n" + "\n\n".join(blocks) + "\n"
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="EPUB or DOCX rendition")
    ap.add_argument("-o", "--output", help="Markdown file to write (default: INPUT with .md suffix)")
    a = ap.parse_args()
    out = a.output or os.path.splitext(a.input)[0] + ".md"
    text = convert(a.input)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(out)


if __name__ == "__main__":
    main()
