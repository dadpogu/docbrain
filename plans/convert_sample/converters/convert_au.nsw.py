#!/usr/bin/env python3
"""Convert NSW legislation exchange XML (the legislation.nsw.gov.au XML download) into Markdown.

Usage: convert_au.nsw.py INPUT.xml [-o OUTPUT.md]

Walks the NSW PCO exchange XML (exdoc: content/level/tier/block/list/note/table) and writes the same
Markdown conventions as convert_au.py, reusing its inline emitter, escaping and table renderer:
- levels: Chapter and Schedule h2, Part h3, Division h4, Subdivision h5, section/clause h6;
  historical notes h2 with their tables h3;
- subsections, paragraphs and list items keep their numbers at the start of their first paragraph;
- defined terms are bold italic and Act names italic, as marked in the XML;
- history notes ("s 4: Am 2009 No 56 ...") become blockquotes at the end of the provision they belong to;
- repealed provisions read "(Repealed)", as on the NSW legislation website.
"""
import argparse
import copy
import os
import re

from lxml import etree

import convert_au as au

LEVELS = {"chapter": 2, "part": 3, "division": 4, "subdivision": 5, "clause": 6, "schedule": 2,
          "historicalnotes": 2, "tableleg": 3, "tableamends": 3}
SKIP = {"parentattributes", "metadata", "head"}


def inline(el):
    return au.inline(el, {}) if el is not None else ""


def table(tbl):
    """CALS table -> the table tree convert_au.render_table renders (namest/nameend and morerows become spans)."""
    t = etree.Element("table")
    for tg in tbl.iter("tgroup"):
        cols = [c.get("colname") for c in tg.iter("colspec")]
        for row in tg.iter("row"):
            tr, cur = etree.SubElement(t, "tr"), 0
            for en in row.iterchildren("entry"):
                start, end = en.get("namest") or en.get("colname"), en.get("nameend")
                idx = cols.index(start) if start in cols else cur
                for _ in range(cur, idx):  # entries omitted for empty columns
                    etree.SubElement(tr, "td")
                span = cols.index(end) - idx + 1 if end in cols else 1
                td = etree.SubElement(tr, "td")
                if span > 1:
                    td.set("colspan", str(span))
                if en.get("morerows"):
                    td.set("rowspan", str(int(en.get("morerows")) + 1))
                for txt in en.iter("txt"):
                    p = copy.deepcopy(txt)
                    p.tag, p.tail = "p", None
                    li = next(txt.iterancestors("li"), None)
                    if li is not None and li.find("no") is not None and next(li.iter("txt")) is txt:
                        p.text = inline(li.find("no")) + " " + (p.text or "")
                    td.append(p)
                cur = idx + span
    return ("raw", au.render_table(t, {}))


def numbered(no, items):
    """Prefix the number of a subsection/paragraph to its first paragraph."""
    if no and items and items[0][0] == "p":
        return [("p", f"{no} {items[0][1]}")] + items[1:]
    return ([("p", no)] if no else []) + items


def blocks(el):
    """Markdown items of an element's children: ("p", inline text) paragraphs or ("raw", block) Markdown."""
    out = []
    for c in el:
        if not isinstance(c.tag, str) or c.tag in SKIP:
            continue
        if c.tag == "txt":
            t = inline(c)
            if t:
                out.append(("p", t))
        elif c.tag == "level":
            out += level(c)
        elif c.tag == "tier":
            out += numbered(inline(c.find("head/no")), blocks(c))
        elif c.tag == "li":
            out += numbered(inline(c.find("no")), blocks(c))
        elif c.tag == "note":
            out += numbered(inline(c.find("heading")), blocks(c))
        elif c.tag == "table":
            out.append(table(c))
        elif c.tag == "repealed":
            out.append(("p", inline(c.find("repealedtxt")) or "(Repealed)"))
        elif c.tag == "content" and c.get("type") == "historynote":
            out += [("raw", "> " + au.para(inline(t))) for t in c.iter("txt") if inline(t)]
        elif c.tag != "heading":  # block, list, deflist, pre, content: containers
            out += blocks(c)
    return out


def level(lv):
    head = lv.find("head")
    no = inline(head.find("no")) if head is not None else ""
    heading = inline(head.find("heading")) if head is not None else ""
    body = blocks(lv)
    if lv.find("repealed") is not None and not heading:  # "73, 74 (Repealed)" as on the NSW website
        heading, body = "(Repealed)", [b for b in body if b != ("p", "(Repealed)")]
    text = au.plain(" ".join(x for x in (no, heading) if x))
    lvl = LEVELS.get(lv.get("type"))
    return ([("raw", "#" * lvl + " " + text)] if lvl and text else ([("p", text)] if text else [])) + body


def convert(path):
    doc = etree.parse(path, etree.XMLParser(load_dtd=False, no_network=True, huge_tree=True)).getroot()
    title = " ".join((doc.get("title") or "").split()) or os.path.splitext(os.path.basename(path))[0]
    items = blocks(doc)
    text = f"# {title}\n\n" + "\n\n".join(au.para(t) if kind == "p" else t for kind, t in items) + "\n"
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="NSW exchange XML file")
    ap.add_argument("-o", "--output", help="Markdown file to write (default: INPUT with .md suffix)")
    a = ap.parse_args()
    if not a.input.lower().endswith(".xml"):
        raise SystemExit(f"unsupported input (expected .xml): {a.input}")
    out = a.output or os.path.splitext(a.input)[0] + ".md"
    text = convert(a.input)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(out)


if __name__ == "__main__":
    main()
