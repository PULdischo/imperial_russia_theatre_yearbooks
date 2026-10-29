# Scan audit: Repertoire cells read against the scans

RG, 2026-10-27: "Can we use these rereadings as a general audit, too?" — yes. When a season's receipts are checked against the
printed season totals, whole theater columns get read against the scan. This folder keeps a record of which cells were read
and what was found, so a cell read once is not read again and the coverage is visible.

`receipts_scan_reads_<date>.csv` — one row per Repertoire event read:
- `result`: `matches scan` (stored figure equals the print) or `corrected` (fixed from the scan; the fix script is named in
  `docs/eval/known_issues.md` and the raw cell carries a `_fix_note`).
- Reads are **checked by Claude**, on the full-resolution embedded scans (ForUpload_<season>_Repertoire.pdf), each suspected
  difference confirmed at 3-5x zoom before any change. Per RG's rule they are finding aids, not her own reading.

What a read covers, and what it doesn't:
- The **receipts figure** of every cell in the listed columns was compared digit by digit.
- **Titles, genres and annotations** were looked at but not compared word by word. Gross errors were caught and fixed
  (a missing second work, a shifted or copied cell, garbled titles), small letter-level slips would not be. A title audit
  of the same columns is still to do.

Coverage, 2026-10-27 (2,729 events, 47 corrected):

| Season  | Columns read in full                                                    |
|---------|-------------------------------------------------------------------------|
| 1891-92 | no receipts printed; targeted reads in `1891-92_scan_reads.csv` (2026-10-28): stats page, the three symphony concerts, the four invalids' concert cells (10, all as stored), and all 15 runs of not_captured dates in the date column (every one a print skip) |
| 1893-94 | every column, both cities (Moscow pp. 6-25 added later the same day: 329 cells, none corrected) |
| 1894-95 | every column (Александринскій added later the same day: 146 cells, none corrected, 4 in the fold) |
| 1895-96 | every column. Маріинскій, Большой, Малый and Михайловскій opera read 2026-10-27; Александринскій and Михайловскій read blind 2026-10-28 (409 events: every figure equals the read or, for 6 fold cells, RG's Fold Log); Большой and Малый re-read blind 2026-10-28 (2 agents, 536 rows): every stored figure equals the blind read or, for 5 fold cells, RG's Binding Fold Log; the 7 low-confidence cells in `1895-96_moscow_blind_reread.csv` |
| 1896-97 | every column, both cities, blind (2026-10-29, 10 agents): `1896-97_scan_reads.csv`, 1,310 rows (every date × session incl. dashes). Every session agrees; 1 misread corrected (Маріинскій 14 Dec 1896 Barnay 3711 -> 3741, `docs/eval/reconciliation/fix_1896_97_barnay_14dec.py`); 3 damaged glyphs kept as stored (Alex 26 Jan, Большой 26 Nov, Малый 6 Oct). The 60 Binding Fold Log cells were read from the scan only, not the volume |
| 1897-98 | every column, both cities, blind (2026-10-29, 7 agents): `1897-98_scan_reads.csv`, 1,264 rows (every date × session incl. dashes). Every session agrees; every legible figure as stored but 10 Sep Маріинскій (43 → 45 к., RG: "5"; `docs/eval/reconciliation/fix_1897_98_scan_reads.py`, applied 2026-10-29); the 18 gutter cells equal RG's Binding Fold Log. Works compared word for word: `1897-98_title_diffs.csv` (61 rows; 4 extraction errors in the fix script, 43 letter-level left for a title audit). Earlier (2026-10-27): Большой, Малый, Александринскій receipts. **Titles audited too** (2026-10-29): `1897-98_title_reads.csv`, 43 cells, all corrected (`fix_1897_98_titles.py`) |
| 1898-99 | every column, both cities, blind (2026-10-28, 4 agents): 1,198 events, 9 cells corrected (`fix_1898_99_scan_reads.py`; 8 receipts, 1 copied charity figure) plus the Новый 28 Dec works; the rest as stored |
| 1903-04 | three columns, blind (2026-10-29, 6 agents): Большой, Новый, Маріинскій (the opera and ballet theaters; Малый, Александринскій, Михайловскій not read): `1903-04_scan_reads.csv`, 730 rows (every printed date × session incl. dashes). Three extraction errors corrected (`docs/eval/reconciliation/fix_1903_04_scan_reads.py`): Маріинскій 19 Apr «Садко» 1520.60 -> 1530.60 (blotted 3), Большой 5 Feb matinée 1705.55 -> 1705.56 (damaged 6), Новый 18 Jan matinée stored on the blank 17 Jan. Every other figure as stored. Medium-confidence cells: none whose alternative reading would close a gap. Titles not audited |
| 1904-05 | every column, both cities, blind (2026-10-28, 6 agents): `1904-05_scan_reads.csv`, 1,558 rows (every date × session incl. dashes). Five extraction errors corrected (`docs/eval/reconciliation/fix_1904_05_scan_reads.py`): Малый 1 Oct (dropped cell), Большой 2 Feb (copied receipts), Новый 30/31 Oct + 6/7 Nov (matinées a day early), Новый 25-27 Feb evenings (copied receipts), Михайловскій 24 Apr (3 read as 8); plus the 19 Apr Большой evening banner. Every other figure as stored. 9 medium-confidence cells; no alternative reading of any of them would close a gap. **Titles too** (2026-10-29): the blind read's works compared word by word with the stored ones; the 57 cells that differed read on the scan (`1904-05_title_reads.csv`): 49 corrected (`docs/eval/reconciliation/fix_1904_05_titles.py`), 8 already right. So 1904-05 is the first season whose titles are audited, not only its receipts |
| 1906-07 | every column, both cities, blind (2026-10-29, 6 agents): `1906-07_scan_reads.csv`, 1,713 rows (every date × session incl. dashes). Малый exact to the kopeck. Two extraction errors corrected (`docs/eval/reconciliation/fix_1906_07_scan_reads.py`, applied 2026-10-29): Александринскій 19 Nov 1906 matinée 625.75 dropped; Большой 30 Dec 1906 «Аида» stored as evening (printed утро). Damaged digits: Большой 28 Jan evening «5?» kopecks (stored 05; RG reads 55, check on HathiTrust), Михайловскій 6 Feb «11?7» (stored none), plus 5 left as stored (none closes a gap). Titles not audited. See reconciliation README, 1906-07 |
| 1909-10 | every column, both cities, blind (2026-10-28): 1,097 events (Маріинскій 213 incl. every heading word for word), every figure as stored; one session label fixed (20 Feb Alex) |
| 1910-11 | every column, both cities, blind (agents read the scan before seeing the data): 1,134 cells with works, none misread; 14 kopeck losses in the parse restored via receipts_print_typos.csv |

`spelling_reads_beshenyya_lakme_2026-10-29.csv` -- every Repertoire cell stored «Бѣшеные деньги», «Лакме», «Лакма» or «Лакмѣ» (59, 1893-94..1907-08), read on the scans after the 1904-05 title audit found the first misreads: 41 misread (fixed), 18 «Лакме» as printed.

Separate from this, the Binding Fold Log (RG's readings of the physical volumes) covers the gutter columns of 1892-93 to
1897-98; see `docs/eval/fold_log/`.

`date_reads_<date>.csv` — dates and date gaps read on the scans (one row per read): Repertoire date columns where the
table skips days, rows checked against a dated statement elsewhere in the yearbook, and the season-review pages
themselves. `result`: `no printed row (source skip)`, `matches stored`, or `print slip in the review`.

- 2026-10-27, 1890-91: all 26 dates with no printed row (16 skips) read in the date column; the p. 21/22 break for
  4-9 March; six Repertoire rows and seven season-review dates behind the review-vs-Repertoire check. Every Repertoire
  row matched; all nine disagreements are slips in the review's own print (reconciliation ledger 1890-91-01..08).

- 2026-10-28, page-break sweep (known_issues.md #162): `pagebreak_missing_dates_2026-10-28.csv` lists every city-date with no
  row and no placeholder (107, all at page breaks); `pagebreak_date_reads_2026-10-28.csv` has the scan reads of the 12 runs not
  read before: 11 print skips, and 1905-06 SP p. 112, whose weekday words (not its day numbers) are misprinted.

`result` values added 2026-10-27 for cells in the binding fold: `fold: RG reading = stored` (the figure can't be read on
the scan; RG's Binding Fold Log reading equals the stored value) and `not visible` (hidden in the fold, no fold-log reading
yet). Cells in the fold are not covered by a scan read, whatever their column.
