# Musicians notes audit, 2026-10-02 (issue #130, batches 6-7)

Independent report-only scan audits of all 215 Musicians pages for printed service notes (left service / death / transfer / appointment / aliases).
- `batch6_candidates/` -- 30 pages with suspects from the sweep (group2..6 files named by agent group; originals reported by hand).
- `batch7_all_pages/group01..37.txt` -- the other 185 pages, 5 pages per agent, PAGE SUMMARY / DISCREPANCIES / OTHER FINDINGS. **OTHER FINDINGS is the working list for the still-open
  name / instrument misread batch** (~hundreds of one-line items: surnames, instrument words, homoglyph letters, stray list numbers).
- `spec_batch7_wave*.py` -- the exact edits applied (page, surname, list number, operations), reusable pattern for later batches.
- `AUDIT_PROMPT.md` -- the agent instructions. `month_spelling_check.txt` -- scan check of the modernized month words.
Every discrepancy was re-read by hand on the scan before being applied; agents' own transcriptions were NOT trusted for pre-reform letters (one wrote "июля" for printed "іюля").
