# HathiTrust 1904-05 — quality test (step 2), 2026-10-30

**Question:** how far can a reading taken from the HathiTrust copy be trusted?

**Method.** 44 Repertoire cells on 13 pages (pp. 91–132): the 9 cells our blind scan read
(`docs/eval/scan_audit/1904-05_scan_reads.csv`) marked only medium confidence, the 15 cells behind the
audit's fixes (`docs/eval/reconciliation/fix_1904_05_scan_reads.py`), and 20 random high-confidence cells
as a baseline. A fresh agent read the HathiTrust crops (images = printed page + 670) with no access to
our readings or the database, then Claude compared. Cells: `1904-05_quality_test_cells.csv` (our readings);
blind HathiTrust reads: `1904-05_quality_test_hathi_reads.csv`. Checked by Claude, not by RG.

**Results.**

| Set | Receipts agree |
|---|---|
| Baseline (easy) | 20 / 20 |
| Audit fixes | 14 / 15 |
| Medium-confidence (hard) | 7 / 9 |
| **All** | **41 / 44** |

- Titles, genres and banners: 44 / 44 (differences only in a final full stop or comma).
- Dashes and the no-receipts Шаляпинъ cell (Большой, 2 Feb 1905) read correctly.
- **Every one of the 3 disagreements was one the blind reader itself marked low confidence.** No high- or
  medium-confidence HathiTrust reading was wrong (19 high, 20 medium all agree).
  - p. 96 Александринскій 8 Oct 1904: ours 483.87; HathiTrust «483 р. ?7 к.» (digit lost).
  - p. 132 Михайловскій 24 Apr 1905: ours 430.50 (audit fix); HathiTrust «480 р. 50 к.», digit a filled blot,
    i.e. the same misreading the extraction made.
  - p. 91 Новый 31 Aug 1904: ours 149.99; HathiTrust «149 р. 89 к.», kopecks blotted.

**What this means.**
1. A HathiTrust reading the reader rates high or medium can serve as a provisional reading (still labelled
   "HathiTrust copy, checked by Claude" until RG reads it). Low-confidence readings are not evidence.
2. HathiTrust is a poor tiebreaker for **damaged type**: broken type prints the same in every copy, and the
   copy's bitonal (black/white only) scan makes thin strokes break and bold digits fill in. It can help
   where the damage is in *our* copy (fold, stain, stamp, scan blur), not where it is in the type.
3. Words are reliable; digits carry the risk (mostly the middle rouble digit and first kopeck digit).

Note: the Moscow-page crops cut off the date column (a cropping choice, not a defect of the copy); the reader
located those rows by counting, and every location matched.
