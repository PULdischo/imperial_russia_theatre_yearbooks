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

Coverage, 2026-10-27 (2,254 events, 47 corrected):

| Season  | Columns read in full                                                    |
|---------|-------------------------------------------------------------------------|
| 1893-94 | Маріинскій, Александринскій, Михайловскій; Moscow Большой + Малый pp. 2-5 only |
| 1894-95 | Большой, Малый, Маріинскій, Михайловскій (not the Александринскій)      |
| 1895-96 | Маріинскій, Большой, Малый; Михайловскій opera only                      |
| 1897-98 | Большой, Малый, Александринскій                                         |

Separate from this, the Binding Fold Log (RG's readings of the physical volumes) covers the gutter columns of 1892-93 to
1897-98; see `docs/eval/fold_log/`.
