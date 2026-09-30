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

**Transcribed:** 18 pages (2026-09-30): every season 1891-92 to 1909-10 except
1905-06. 1909-10 was added from RG's new scan; the Repertoire doesn't cover 1909-10 yet, so the
comparison skips it. That comes to 285 lines and 118 footnotes. The data lives in `_build.py`: edit it
there, then run `uv run python docs/season_stats/_build.py` to regenerate the CSVs and rerun
every check.

**Format by season (observed on the scans):**
- 1891-92, 1892-93: counts only.
- 1893-94 to 1900-01: counts + receipts + footnotes. From 1898-99, footnote 1 says the
  receipts EXCLUDE charity performances.
- 1901-02 to 1904-05, and 1906-07: counts + receipts, no footnotes.
- 1907-08, 1908-09: category totals only, with no per-theater breakdown, and footnotes again.
- Lines with a count but no receipts occur in 1897-98, 1898-99 (charity) and 1891-92/1892-93
  (counts-only seasons).

## Files

- `pages.csv`: one row per page (season, source file, printed page, verbatim
  heading, heading footnote, format, note).
- `lines.csv`: one row per printed line that carries a number.
  - `line_kind`: `venue` (an indented "въ … театрѣ" line under a category), `part` (an
    indented sub-line of a category that is not a venue, e.g. the kinds of Смѣшанныхъ),
    `subtotal` (the ruled total under venue/part lines), or `category` (a single line).
  - `category_verbatim`: exactly as printed, including a ditto mark `»` or a
    trailing colon.
  - `category`: the same with the ditto resolved and the colon dropped, for
    querying.
  - `qualifier_verbatim`: printed parentheticals such as "(опера и балетъ)".
  - `receipts_verbatim`: the italic figure inside the parentheses, as printed
    (a missing period after "к" is kept).
  - `receipts_kopecks`: that figure parsed. A printed half-kopeck ("18½ к.") is kept as
    .5. A misprinted marker ("л." for "к.") is read explicitly in `KOPECKS_READ`, never by
    widening the parser.
  - `footnote_refs`: the superscript number(s) on the line.
- `footnotes.csv`: one row per footnote, verbatim.
- `dated_notes.csv`: from 1909-10, the page lists jubilees and benefits by date after each city's totals.
  These are verbatim, one row per printed line.

## Conventions

- Pre-reform orthography verbatim (ъ, ѣ, і), including variants such as
  "теченіи" (1891-92) vs "теченіе".
- Line-break hyphens in footnotes are joined ("воспи-танниковъ" → "воспитанниковъ").
- Damaged type is transcribed as the intended letter, with a note (as with
  "Балстный", #114). A true wrong letter would be kept as printed.
- A number the print gets wrong stays as printed, and `note` says so. See
  `docs/eval/genuine_print_typos.md`. There are three subtotal slips: 1896-97 SP ballet
  count 52 (lines 50 + 3); 1900-01 Moscow opera receipts 1 р. under its lines; 1906-07 SP
  drama receipts 81 р. over its lines. There are also several letter slips.
- Every row was read from the scan at 250–600 dpi. Doubtful characters were magnified
  further.
- `_build.py` fails if:
  - a subtotal doesn't equal its lines, unless the note starts "PRINT:";
  - a footnote reference has no footnote;
  - any field mixes Latin and Cyrillic letters.
