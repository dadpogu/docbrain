#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["inscriptis>=2.3,<2.6", "lxml", "mammoth", "ftfy", "pypdfium2", "pillow", "tesserocr"]
# ///
"""Convert a local legislation file to plain text the way the Open Australian Legal Corpus creator does.

Usage: oalc_convert.py INPUT.epub|.docx|.html|.pdf [-o OUTPUT.txt] [--source frl|nsw] [--tessdata DIR]

Standalone version of the creator's text extraction, without its scraping stack (aiohttp, msgspec,
orjson, rich, click, ...):
  .epub  FRL HTML rendition: each spine page through Inscriptis with the FRL profile (the creator
         scrapes the same HTML pages from the Register's epubFrame)
  .docx  mammoth -> HTML -> Inscriptis with the FRL profile (the creator's Word fallback)
  .html  Inscriptis with the FRL profile, or the NSW profile and #frag-col cleanup with --source nsw
  .pdf   OCR every page with Tesseract (pypdfium2 render at scale 3), as the creator's PDF fallback
The text is then cleaned with the creator's clean_text (ftfy, NBSP -> space, whitespace trimming).
Run with `uv run oalc_convert.py ...` to get the dependencies; OCR needs eng.traineddata in --tessdata
or $TESSDATA_PREFIX.
"""
import argparse
import os
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

import lxml.html
from inscriptis.css_profiles import CSS_PROFILES
from inscriptis.html_properties import Display, WhiteSpace
from inscriptis.model.html_element import HtmlElement

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from custom_inscriptis import CustomInscriptis, CustomParserConfig  # noqa: E402  (no package imports)


# --- Inscriptis profiles, as set up in scrapers/federal_register_of_legislation.py and nsw_legislation.py

def frl_config():
    profile = CSS_PROFILES["strict"].copy()
    profile["p"] = HtmlElement(display=Display.block)
    profile["span"] = HtmlElement(whitespace=WhiteSpace.pre)
    profile |= dict.fromkeys(("h1", "h2", "h3", "h4", "h5"), HtmlElement(display=Display.block, margin_before=1))
    return CustomParserConfig(profile)


def nsw_config():
    profile = CSS_PROFILES["strict"].copy()
    profile["blockquote"] = HtmlElement(display=Display.block, padding_inline=4)
    return CustomParserConfig(profile)


# --- extraction ---------------------------------------------------------------------------------

def epub_pages(path):
    """HTML pages of an EPUB in spine order."""
    with zipfile.ZipFile(path) as z:
        opf = next(n for n in z.namelist() if n.endswith(".opf"))
        root = lxml.etree.fromstring(z.read(opf))
        ns = {"o": "http://www.idpf.org/2007/opf"}
        items = {i.get("id"): i.get("href") for i in root.iterfind(".//o:manifest/o:item", ns)}
        base = os.path.dirname(opf)
        names = [os.path.normpath(os.path.join(base, items[r.get("idref")])).replace("\\", "/")
                 for r in root.iterfind(".//o:spine/o:itemref", ns)]
        return [z.read(n) for n in names if n.lower().endswith((".html", ".xhtml", ".htm"))]


def from_epub(path):
    config = frl_config()
    return "\n".join(CustomInscriptis(lxml.html.document_fromstring(page), config).get_text()
                     for page in epub_pages(path))


def from_docx(path):
    import mammoth
    with open(path, "rb") as f:
        html = mammoth.convert_to_html(f, convert_image=lambda _: {})  # custom_mammoth.docx2html
    return CustomInscriptis(lxml.html.fromstring(html.value), frl_config()).get_text()


def from_html(path, source):
    with open(path, "rb") as f:
        tree = lxml.html.fromstring(f.read())
    if source == "frl":
        return CustomInscriptis(tree, frl_config()).get_text()
    # NSW whole-document view: keep #frag-col, drop the toolbar, hidden search results and history notes
    col = (tree.xpath('//div[@id="frag-col"]') or [tree])[0]
    for xp in ('//div[@id="fragToolbar"]', '//div[@class="nav-result display-none"]',
               "//*[contains(concat(' ', normalize-space(@class), ' '), ' view-history-note ')]"):
        for el in col.xpath(xp):
            el.drop_tree()
    return CustomInscriptis(col, nsw_config()).get_text()


def from_pdf(path, tessdata, threads):
    import pypdfium2
    import tesserocr
    pdf = pypdfium2.PdfDocument(path)
    ocr = (lambda img: tesserocr.image_to_text(img, path=tessdata)) if tessdata else tesserocr.image_to_text
    text = []
    with ThreadPoolExecutor(threads) as pool:
        for start in range(0, len(pdf), threads):  # batch pages to bound memory, as ocr.pdf2txt does
            imgs = [pdf[i].render(scale=3).to_pil() for i in range(start, min(start + threads, len(pdf)))]
            text.extend(pool.map(ocr, imgs))
    text = "\n".join(text)
    return re.sub(r"(^|\n)\d{1,4}[^\S\n]*\n", "", text)  # drop paragraph numbers, as ocr.pdf2txt does


# --- helpers.clean_text ---------------------------------------------------------------------------

def clean_text(text):
    import ftfy
    text = ftfy.fix_text(text).replace("\xa0", " ")
    text = re.sub("[\a\b\f\r\v]", "", text)
    text = "\n".join(re.sub(r"\s+$", "", line) for line in text.split("\n"))
    text = re.sub(r"^\s*\n", "", text)
    return re.sub(r"\n\s*$", "", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("-o", "--output", help="text file to write (default: INPUT with .txt suffix)")
    ap.add_argument("--source", choices=("frl", "nsw"), default="frl", help="Inscriptis profile for .html input")
    ap.add_argument("--tessdata", default=os.environ.get("TESSDATA_PREFIX"), help="directory with eng.traineddata")
    ap.add_argument("--threads", type=int, default=os.cpu_count() - 1 or 1, help="OCR threads")
    a = ap.parse_args()
    ext = os.path.splitext(a.input)[1].lower()
    if ext == ".epub":
        text = from_epub(a.input)
    elif ext == ".docx":
        text = from_docx(a.input)
    elif ext in (".html", ".htm"):
        text = from_html(a.input, a.source)
    elif ext == ".pdf":
        text = from_pdf(a.input, a.tessdata, a.threads)
    else:
        raise SystemExit(f"unsupported input (expected .epub, .docx, .html or .pdf): {a.input}")
    out = a.output or os.path.splitext(a.input)[0] + ".txt"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(clean_text(text) + "\n")
    print(out)


if __name__ == "__main__":
    main()
