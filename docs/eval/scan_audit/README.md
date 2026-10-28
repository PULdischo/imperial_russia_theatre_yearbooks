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
| 1895-96 | Маріинскій, Большой, Малый; Михайловскій opera only. Большой and Малый re-read blind 2026-10-28 (2 agents, 536 rows): every stored figure equals the blind read or, for 5 fold cells, RG's Binding Fold Log; the 7 low-confidence cells in `1895-96_moscow_blind_reread.csv` |
| 1897-98 | Большой, Малый, Александринскій                                         |
| 1909-10 | every column, both cities, blind (2026-10-28): 1,097 events (Маріинскій 213 incl. every heading word for word), every figure as stored; one session label fixed (20 Feb Alex) |
| 1910-11 | every column, both cities, blind (agents read the scan before seeing the data): 1,134 cells with works, none misread; 14 kopeck losses in the parse restored via receipts_print_typos.csv |

Separate from this, the Binding Fold Log (RG's readings of the physical volumes) covers the gutter columns of 1892-93 to
1897-98; see `docs/eval/fold_log/`.

`date_reads_<date>.csv` — dates and date gaps read on the scans (one row per read): Repertoire date columns where the
table skips days, rows checked against a dated statement elsewhere in the yearbook, and the season-review pages
themselves. `result`: `no printed row (source skip)`, `matches stored`, or `print slip in the review`.

- 2026-10-27, 1890-91: all 26 dates with no printed row (16 skips) read in the date column; the p. 21/22 break for
  4-9 March; six Repertoire rows and seven season-review dates behind the review-vs-Repertoire check. Every Repertoire
  row matched; all nine disagreements are slips in the review's own print (reconciliation ledger 1890-91-01..08).

`result` values added 2026-10-27 for cells in the binding fold: `fold: RG reading = stored` (the figure can't be read on
the scan; RG's Binding Fold Log reading equals the stored value) and `not visible` (hidden in the fold, no fold-log reading
yet). Cells in the fold are not covered by a scan read, whatever their column.
