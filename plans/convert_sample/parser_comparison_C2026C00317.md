# Parser output comparison: Recycling and Waste Reduction Act 2020 (C2026C00317)

Date: 2026-10-26. Compares the five Markdown files in [`assets/parsed/Sample`](../assets/parsed/Sample/) against [`C2026C00317.pdf`](../assets/parsed/Sample/C2026C00317.pdf), the authorised PDF of compilation No. 3 (213 pages, SHA-256 `998e9f4e…`, the same file as the raw asset).

## Bottom line

- **Text content:** every file contains essentially all of the Act's body text, with 99.9–100% of body word sequences present. The files differ in structure, formatting, and table fidelity.
- **Best overall: LawCodex.** It is the only file with a correct heading hierarchy (Chapter → Part → Division → Subdivision → Section). It has metadata front matter, intact tables, and defined terms. It is missing the table of contents, the "Prepared by" cover line, the registration date, page references, and italics on offence labels.
- **Mammoth and MarkItDown (EPUB):** their content and tables are as complete as LawCodex, but neither has any heading markup.
  - Mammoth keeps bold and italics, and adds 15 run-together words such as `enforceableunder`.
  - MarkItDown (EPUB) loses all emphasis and wraps the Act in EPUB/CSS noise.
- **LiteParse and MarkItDown (PDF):** both read the PDF layout and inherit its problems: page furniture and broken tables.
  - LiteParse has usable section headings, but cannot be trusted for tables or clause boundaries.
  - MarkItDown (PDF) is plain, hard-wrapped text with no Markdown structure.

## Inputs

| File | SHA-256 (prefix) | Likely source rendition (inferred) |
| --- | --- | --- |
| `C2020A00119_LawCodex.md` | `ee0aa90b` | Register text (front matter matches the JSON sidecar); same bytes as `assets/parsed/GLOBAL.AU/C2020A00119-…md` |
| `C2020A00119_Liteparse.md` | `b2700d01` | PDF (keeps page footers and page separators) |
| `C2020A00119_Mammoth.md` | `810c19c2` | DOCX (Mammoth converts Word files; embedded WMF image) |
| `C2020A00119_MarkItDown.md` | `ad547fa5` | PDF (keeps footers and PDF line wraps) |
| `C2020A00119_MarkItDown_EPUB.md` | `49ee221f` | EPUB (opens with "Content from the zip file `C2026C00317.epub`") |

DOCX and EPUB are different renditions of the same compilation. They have no PDF pages, so page-level provenance can't be expected from Mammoth or MarkItDown (EPUB).

## Scorecard

PDF reference values are in brackets. "Associated" means the item number, column 1 cell, and column 2 cell appear together in order.

| Check | LawCodex | LiteParse | Mammoth | MarkItDown (PDF) | MarkItDown (EPUB) |
| --- | --- | --- | --- | --- | --- |
| Body text coverage (5-word sequences) | 99.96% | 99.93% | 99.95% | 99.86% | 99.96% |
| Endnotes coverage | 98.6% | 84.8% | 98.6% | 93.7% | 98.6% |
| Section headings found [188] | 188, all `h6` | 188: 187 `h5`, 1 plain (s120) | 188, plain text | 188, plain text | 188, plain text |
| Chapter/Part/Division/Subdivision [5/26/22/8] | All, `h2`/`h3`/`h4`/`h5` | All, `h1`/`h2`/`h3`/`h4` (one Division `h6`) | All, plain text | All, plain text | All, plain text |
| Subsection starts at line start [591] | 591 | 215 | 591 | 591 | 591 |
| Paragraph starts at line start [1,144] | 1,140 | 1,036 | 1,140 | 1,135 | 1,140 |
| `Penalty:` / `Civil penalty:` lines [30/36] | 30/36 | 0/3 (inline) | 30/36 | 30/36 | 30/36 |
| Offence labels on own line / italic [177 labels] | All / no | 1 / yes | All / no | All / no | All / no |
| Defined terms as bold-italic [159] | 137 | 5 | 137 | 0 | 0 |
| s2 commencement row associated | Yes | No (columns interleaved) | Yes | Yes | Yes |
| s106 rows associated [8] | 8 | 0 | 8 | 0 | 8 |
| s151 rows associated [28] | 28 | 6 | 28 | 0 | 28 |
| Table representation | HTML (s2, s106, s151) + pipe (endnotes) | Partial pipe fragments | Pipe | None (flattened text) | Pipe |
| Table of contents | None | Present, lines merged | Present, with page numbers | Present, numbers split from titles | Present, no page numbers |
| Page furniture lines kept | 0 | 210 footers, 210 page labels, 107 running headers, 212 `-----` | 0 | 213 + 210 footers, 191 + 96 running headers | 0 |
| Non-Act text added | None | Furniture | None | Furniture | EPUB file listing, XML, CSS (about 4,500 words) |
| Prose lines broken mid-sentence | 0 | 548 | 0 | 2,293 | 0 |
| Run-together words | 0 | 2 | 15 | 0 | 0 |
| Cover: "Prepared by OPC" / registration date | No / no | Yes / no | No / no | Yes / yes (×213) | No / no |
| Metadata front matter | YAML (IDs, dates, source URL) | None | None | None | None |

## Per-file findings

### LawCodex

**Parsed:**
- **Formatting:**
  - YAML front matter with identifier, register ID, compilation number, dates, source URL, and retrieval date.
  - One paragraph per line, with no hard wraps or page furniture.
  - 138 `***defined terms***` (137 of the PDF's 159 bold-italic terms match), and italic Act names: 83 of the 102 italic runs that are not offence labels.
  - Typographic characters kept (em dashes, curly apostrophes). CRLF line endings.
- **Structure:**
  - Full hierarchy: title `h1`, Chapter `h2`, Part `h3`, Division `h4`, Subdivision `h5`, section `h6`. Levels are skipped where the Act has no Division.
  - All 188 sections in order; 65A and 65B kept; repealed s122 and s187 correctly absent.
  - Every subsection, paragraph, `Note:`, `Penalty:` and `Civil penalty:` line starts its own line.
  - s2, s106, and s151 are HTML tables with correct cell associations (28/28 and 8/8).
  - Endnote 2 (abbreviation key), Endnote 3 (legislation history), and Endnote 4 (159-row amendment history) are pipe tables.
- **Content:** body 99.96% and endnotes 98.6%. The few unmatched sequences are PDF furniture (running "Section 76" headers on pages 93–100) and repeated table headers on endnote continuation pages, not missing Act text.

**Missed:**
- **Formatting:**
  - Offence labels ("Fault-based offence", "Civil penalty provision", "Strict liability offence") are plain text; the PDF sets them in italics.
  - No coat-of-arms image.
  - 128 non-breaking hyphens (U+2011), such as `non‑compliance`, where the PDF text layer has ASCII hyphens. Search needs to normalise them.
- **Structure:**
  - No table of contents.
  - No page numbers, page breaks, or printed page labels, so a citation can't point to a PDF page.
- **Content:**
  - The cover line "Prepared by the Office of Parliamentary Counsel, Canberra" is missing.
  - The registration line "Authorised Version C2026C00317 registered 21/07/2026" is missing, and the front matter has no registration date.

### LiteParse

**Parsed:**
- **Formatting:**
  - Italics are kept: 183 of 184 label lines and many Act names.
  - Bold on cover lines and on table and heading fragments.
  - An image reference for the cover (`img_p1_1.png`, a file that isn't supplied).
- **Structure:**
  - Chapter `h1`, Part `h2`, Division `h3`, Subdivision `h4`, section `h5` for 187 sections, all in order.
  - A table of contents (127 of 188 entries recognisable).
  - All four endnote headings.
  - Page boundaries are recoverable from 212 `-----` separators and page labels.
- **Content:**
  - Body 99.93%.
  - The only file besides MarkItDown (PDF) that keeps "Prepared by the Office of Parliamentary Counsel".

**Missed:**
- **Formatting:**
  - Em dashes and curly apostrophes are converted to ASCII; "Chapter 2—Regulating" becomes "Chapter 2-Regulating", so quotes and headings no longer match the source exactly.
  - 548 prose lines are broken mid-sentence.
  - Only 54 bold-italic spans; 5 of 159 defined terms match.
- **Structure:**
  - The s120 heading is plain text, with half its title in bold.
  - 107 running headers ("Chapter 1 Introduction Part 1 Preliminary provisions") and 7 lines of definition text (for example "Australian law means a law of …") are mis-tagged as `h6` headings.
  - 376 subsection starts, all 30 `Penalty:` and 33 of 36 `Civil penalty:` lines, and all but one offence label run inline inside paragraphs: `… not complied with. *Fault-based offence* (2) A person commits …`.
  - 12 statutory notes are rendered as two-column pipe tables.
- **Tables:**
  - s2: the columns are interleaved with the surrounding prose, so the commencement row isn't associated.
  - s106: 0 of 8 rows associated.
  - s151: 6 of 28 rows associated; rows 1–22 have detached person and decision columns, and items 7, 14, and 22 are split by page furniture.
  - Endnotes are reordered: the two-column abbreviation key is read across columns, and the amendment history separates the provision list from the "am No 68, 2025" list (endnotes coverage 84.8%).
- **Content:**
  - 210 compilation footers, 210 page labels, and 10 running "Section N" lines are mixed into the text.
  - 2 run-together words (`declarationinclude`, `exemptionthe`).
  - No registration date.

### Mammoth (DOCX)

**Parsed:**
- **Formatting:**
  - One paragraph per line.
  - Bold front-matter labels.
  - 138 `***defined terms***` (137 of 159 match, the same as LawCodex) and 111 italic spans.
  - Typographic characters kept.
- **Structure:**
  - All 188 sections and 61 Chapter/Part/Division/Subdivision headings, in order.
  - Every subsection, paragraph, note, and penalty on its own line.
  - Full table of contents with page numbers (100% of contents text matched).
  - s2, s106, s151, and the endnote tables are pipe tables with correct associations (28/28 and 8/8).
- **Content:** the most complete overall: body 99.95%, contents 100%, endnotes 98.6%, and no non-Act text.

**Missed:**
- **Formatting:**
  - No heading markup at all: every heading is a plain paragraph, so the hierarchy has to be rebuilt from the text patterns "Chapter N—", "Part N—", and "N Title".
  - Table captions sit in the header row (`| Persons affected by reviewable decisions | | |`), with the real column headers as the first body row.
  - The abbreviation-key table has an empty header row.
  - The cover image is a truncated placeholder (`data:image/x-wmf;base64...`).
  - 1,005 non-breaking spaces and 151 non-breaking hyphens.
- **Structure:** no page numbers or page breaks, because the DOCX rendition has none.
- **Content:**
  - 15 run-together words where a space was dropped, for example s103(1) and s104(1) "enforceableunder Part 6/7", plus `tothe` ×4, `partyauthorised` ×3, and `extentthat` ×2. Exact-phrase search and quoting fail on these.
  - The "Prepared by" line and the registration date are missing.

### MarkItDown (PDF)

**Parsed:**
- **Structure:**
  - All 188 section headings and 61 Chapter/Part/Division/Subdivision headings, each on its own (plain) line, in order.
  - Subsections, paragraphs, notes, penalties, and all 177 offence labels each start a line.
  - All four endnote headings.
  - Page boundaries are recoverable from the 213 footers.
- **Content:**
  - Body 99.86%.
  - The only file that keeps every cover fact, including "Prepared by" and the registration date (21/07/2026).
  - Typographic characters kept; no run-together words.

**Missed:**
- **Formatting:**
  - No Markdown at all: no headings, bold, italics, defined-term emphasis, tables, or images.
  - Lines are hard-wrapped at PDF line breaks (average 40 characters; 2,293 prose lines broken mid-sentence), and multi-line section titles are split across lines.
- **Structure:**
  - Tables are flattened: column 1 cells, then column 2 cells, in page blocks. s106 has 0 of 8 rows associated and s151 0 of 28; items 7, 14, and 22 are also split by page furniture.
  - The s2 row stays in order only because its cells are short.
  - In the table of contents, the section numbers form one block and the titles another (17 of 188 entries recognisable).
- **Content:**
  - 213 "Authorised Version" footers, 210 "Compilation No. 3 Compilation date" footers, 191 running "Section N" headers, 96 running Chapter/Part headers, and 104 page labels are mixed into the text (about 3,200 extra words).
  - Endnotes coverage is 93.7%, because the abbreviation key's two columns are read across.

### MarkItDown (EPUB)

**Parsed:**
- **Structure:**
  - All 188 sections and 61 Chapter/Part/Division/Subdivision headings, in order.
  - Every subsection, paragraph, note, and penalty on its own line.
  - A table of contents.
  - s2, s106, s151, and the endnote tables as pipe tables with correct associations (28/28 and 8/8).
- **Content:**
  - Body 99.96% and endnotes 98.6%.
  - No hard wraps, no page furniture, no run-together words.

**Missed:**
- **Formatting:**
  - All emphasis is lost: 0 defined terms, 0 bold, and 1 italic span. Offence labels and Act names are plain text.
  - Headings are plain text; the only Markdown headings are the four `## File:` container headings.
  - Every pipe table has an empty header row followed by the caption as a body row.
  - 5,127 non-breaking spaces and 151 non-breaking hyphens.
- **Structure:**
  - The table of contents has no page numbers.
  - No page boundaries.
- **Content:**
  - The EPUB package is dumped as text: the zip listing, `META-INF/container.xml`, a reference to `image.001.png`, and the full `styles.css` (about 4,500 words that aren't part of the Act).
  - The "Prepared by" line and the registration date are missing.

## Implications for the parser decision

- No file is usable as-is for clause-aware chunking. LawCodex needs the least work. Mammoth or MarkItDown (EPUB) would each need heading recovery from text patterns, plus character normalisation; Mammoth also needs its run-together words repaired.
- Do not use PDF-layout outputs (LiteParse, MarkItDown PDF) for table evidence. s106 and s151 associations fail in both, matching the earlier DB-008 finding for LiteParse.
- The PDF-layout outputs are the only source of page numbers. To cite PDF pages, pair a structure-rich file (LawCodex) with page anchors from the PDF itself rather than taking text from a PDF-layout parser.
- Whatever is chosen, normalise U+2011, U+00A0, and dash/quote variants consistently for indexing and exact-match lookups, and keep the original bytes for quotation.

## Method and limits

- **Reference:** words and font styles extracted from the PDF text layer with pdfplumber 0.11. Footers, page labels, and running headers were removed by position. Regions: cover (p1), about (p2), contents (p3–12), body (p13–203), endnotes (p204–213). The derived section list (188 sections) matches `tests/fixtures/recycling_act/expected_structure.json`.
- **Coverage:** the share of PDF words inside a 5-word sequence that also occurs in the Markdown, after removing Markdown/HTML markup and normalising case, dashes, and quotes. The check is order-insensitive beyond 5 words, so interleaved table columns can still count as "covered". Table fidelity is therefore measured separately, using the reviewed s151 tuples from the fixture and s106 rows read from PDF pages 131–132.
- **What a small remaining gap means:** the coverage gaps under 0.2% in LawCodex, Mammoth, and MarkItDown (EPUB) were inspected. They are PDF furniture that position filtering missed (four-level running headers on pages 93–100) and table headers repeated on continuation pages, not missing Act text.
- **Not checked:** OCR (the PDF has a text layer), visual layout, the full wording of every section against a human-reviewed source, or legal correctness. The LiteParse and MarkItDown engine versions and options are unknown.
- The comparison scripts are in `.amp/in/pdfcmp/` (`extract_pdf.py`, `compare.py`). That folder is excluded from Git; rerun them when new parser outputs are added.
