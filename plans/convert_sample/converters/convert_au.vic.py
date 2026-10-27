#!/usr/bin/env python3
"""Convert a Victorian legislation DOCX (OCPC Word templates) into Markdown.

Usage: convert_au.vic.py INPUT.docx [-o OUTPUT.md]

Reuses convert_au.py's DOCX reader and Markdown emitter and adds the Victorian style map:
- Chapter/Part/Division/Subdivision/Schedule/Endnotes headings take their level from their leading word
  (Chapter and Schedule h2, Part h3, Division h4, Subdivision h5), as convert_au.py levels Commonwealth Acts;
- section and schedule-clause headings (DraftHeading1, ScheduleHeading1) are h6, endnote headings h3;
- side notes (amendment history set in the margin) become blockquotes before the provision they annotate;
- the cover page and table of provisions are dropped: the first page of the Act repeats the cover.
"""
import argparse
import os
import re
import sys

import convert_au as au

GROUP_STYLES = {"ChapterHeading": 2, "Heading-SCHEDULE": 2, "Heading-PART": 3, "Schedule-PART": 3, "Schedule-Part0": 3,
                "Heading-DIVISION": 4, "Schedule-DIVISION": 4, "Schedule-Division0": 4}
GROUP_WORDS = {"chapter": 2, "schedule": 2, "endnotes": 2, "part": 3, "division": 4, "subdivision": 5}
HEADING_STYLES = {"DraftHeading1": 6, "ScheduleHeading1": 6, "Heading-ENDNOTES": 3}
SKIP = re.compile(r"^(TOC\d*|Lines)$")
ACT_TITLE = re.compile(r"\b(Act|Regulations|Rules)\s+\d{4}$")
# The cover counts as front matter only if the table of provisions starts within this many text paragraphs.
MAX_COVER_PARAGRAPHS = 20
# Styles rendered as ordinary paragraphs on purpose (checked on 17-51a023.docx); any other unmapped style is reported.
# On WARNING styles missing, add then either to BODY_STYLES or HEADING_STYLES and re-run.
BODY_STYLES = {
    "", "DraftHeading2", "DraftHeading3", "DraftHeading4", "DraftHeading5",  # subsections and paragraphs
    "BodySectionSub", "BodyParagraph", "BodyParagraphSub", "DraftDefinition2", "DraftPenalty2", "Stars",
    "DraftSectionNote", "DraftSub-sectionNote", "DraftParaNote", "AmndSub-sectionNote", "DraftParaEg",
    "Normal-Schedule", "EndnoteText", "ParaHead", "ParaText",  # endnotes
}


def heading_level(cls, text):
    if cls in GROUP_STYLES:
        word = text.split(maxsplit=1)[0].lower() if text else ""
        return GROUP_WORDS.get(word, GROUP_STYLES[cls])
    return HEADING_STYLES.get(cls)


def cover_end(blocks, styles):
    """Index of the first table-of-provisions paragraph if only a short cover precedes it, else 0."""
    first = next((i for i, e in enumerate(blocks) if re.match(r"TOC\d", e.get("class") or "")), None)
    if first is None or any(au.local(e) == "table" for e in blocks[:first]):
        return 0
    cover = sum(1 for e in blocks[:first] if au.inline(e, styles))
    return first if cover <= MAX_COVER_PARAGRAPHS else 0


def render(body, styles, title):
    """(title, Markdown blocks, {unmapped style: [count, example]}) of a VIC document body.

    title=None picks the first Act-title paragraph."""
    blocks = list(au.iter_blocks(body))
    styles = dict(styles, SideNote=(None, False))  # side notes keep only direct emphasis, not the style's bold
    out, title_done, unmapped = [], False, {}
    for e in blocks[cover_end(blocks, styles):]:
        cls = (e.get("class") or "").strip()
        if SKIP.match(cls):
            continue
        if au.local(e) == "table":
            t = au.render_table(e, styles)
            if t:
                out.append(t)
            continue
        t = au.inline(e, styles)
        if not t:
            continue
        text = au.plain(t)
        if not title_done and (text == title or (title is None and ACT_TITLE.search(text))):
            title, title_done = text, True
            continue
        lvl = heading_level(cls, text)
        if lvl:
            out.append("#" * lvl + " " + text)
        elif cls == "SideNote":
            out.append("\n".join("> " + ln for ln in au.para(t).split("\n")))
        else:
            out.append(au.para(t))
            if cls not in BODY_STYLES:
                unmapped.setdefault(cls, [0, text[:70]])[0] += 1
    return title, out, unmapped


def convert(path):
    bodies, styles, meta_title = au.read_docx(path)
    title, blocks, unmapped = render(bodies[0], styles, au.SPACES.sub(" ", meta_title).strip() if meta_title else None)
    if unmapped:
        print(f"warning: {path}: {len(unmapped)} paragraph style(s) not in the VIC style map, written as plain paragraphs:",
              file=sys.stderr)
        for cls, (n, example) in sorted(unmapped.items(), key=lambda kv: -kv[1][0]):
            print(f"  {cls}: {n} paragraph(s), e.g. {example!r}", file=sys.stderr)
    title = title or os.path.splitext(os.path.basename(path))[0]
    text = f"# {title}\n\n" + "\n\n".join(blocks) + "\n"
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="DOCX rendition of a Victorian Act or statutory rule")
    ap.add_argument("-o", "--output", help="Markdown file to write (default: INPUT with .md suffix)")
    a = ap.parse_args()
    if not a.input.lower().endswith(".docx"):
        raise SystemExit(f"unsupported input (expected .docx): {a.input}")
    out = a.output or os.path.splitext(a.input)[0] + ".md"
    text = convert(a.input)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(out)


if __name__ == "__main__":
    main()
