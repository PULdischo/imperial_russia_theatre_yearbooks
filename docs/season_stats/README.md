# Season production-stats pages: hand transcription

Verbatim transcriptions of each volume's season totals page ("Всего въ теченіе
сезона … было спектаклей"). Scans: `pdf/Spiski_ProductionStats/<season>_ProductionStats.pdf`
(gitignored).

**Purpose:** the page's counts and receipts, per genre and theater, are a
checksum on the Repertoire tables. Its footnotes (from 1893-94) count benefits,
free student performances and charity performances. Plan and pilot: RG approved,
2026-09-29/30.

**Coverage:**
- Seasons 1891-92 to 1908-09.
- 1890-91 has no such page (the page type starts in 1891-92).
- No page has been found for 1905-06; that needs the physical volume.
- Format stages (RG's observation, confirmed on the scans):
  - counts only in 1891-92 and 1892-93;
  - counts + receipts + footnotes from 1893-94;
  - 1906-07 has counts + receipts and no footnotes;
  - 1908-09 has footnotes again.

**Transcribed so far:** 1891-92, 1896-97, 1906-07 (the three format pilots).

## Files

- `pages.csv`: one row per page (season, source file, printed page, verbatim
  heading, heading footnote, format, note).
- `lines.csv`: one row per printed line that carries a number.
  - `line_kind`: `venue` (an indented "въ … театрѣ" line under a category),
    `subtotal` (the ruled total under venue lines), or `category` (a single line).
  - `category_verbatim`: exactly as printed, including a ditto mark `»` or a
    trailing colon.
  - `category`: the same with the ditto resolved and the colon dropped, for
    querying.
  - `qualifier_verbatim`: printed parentheticals such as "(опера и балетъ)".
  - `receipts_verbatim`: the italic figure inside the parentheses, as printed
    (a missing period after "к" is kept).
  - `receipts_kopecks`: that figure parsed.
  - `footnote_refs`: the superscript number(s) on the line.
- `footnotes.csv`: one row per footnote, verbatim.

## Conventions

- Pre-reform orthography verbatim (ъ, ѣ, і), including variants such as
  "теченіи" (1891-92) vs "теченіе".
- Line-break hyphens in footnotes are joined ("воспи-танниковъ" → "воспитанниковъ").
- Damaged type is transcribed as the intended letter, with a note (as with
  "Балстный", #114). A true wrong letter would be kept as printed.
- A number the print gets wrong stays as printed, and `note` says so. See
  `docs/eval/genuine_print_typos.md`. So far there are two: 1896-97 SP ballet
  count subtotal 52 (lines 50 + 3), and 1906-07 SP drama receipts subtotal
  81 р. over its lines.
- Every row was read from the scan at 300–600 dpi.
- Each subtotal was checked against its lines by script, and every text field
  was checked for mixed Latin/Cyrillic letters.
