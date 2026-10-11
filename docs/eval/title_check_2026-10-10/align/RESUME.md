# Column-structure read: resume notes (paused 2026-10-11, issue #151 follow-up 15)

**What this is.** A blind, page-level read of the scans (is each theater's cell on each date row one undivided cell, or
divided?) of every Repertoire page that has at least one stored morning/evening split (524 pages), diffed against the stored
sessions. Purpose: find the rest of the date-shift cascades (follow-ups 13-14) that the weekday and receipts-order checks
cannot see. Method and brief: `BRIEF_ALIGN.md`; crops: `outputs/title_check_2026-10-10/align_crops/` (gitignored, regenerate with
`render_align_crops.py`); chunk lists: `chunks/align_NN.csv` (66 chunks: 01-03 are the 11 "deep" candidate pages with receipts and
first titles, 04-26 spreads then singles, 66 = 1890-91 pair008 re-read).

## State at the pause
* **Reports written** (`reports/align_NN.csv`): see `ls reports`. In flight at the last snapshot: 53 only (it writes its own
  reports when they finish; a report that is not on disk was not finished). **Never launched: 57-65.**
* Each reader costs ~100-140k tokens per chunk (10 single pages or 4 spreads). 57-65 is nine more chunks, ~1.2M tokens.
* `compare_structure.py` diffs all reports on disk against `raw.event_entry` -> `discrepancies.csv`, `discrepant_columns.csv`.
  Keyed on theater + day number (totals), a printed dash with no stored session is ignored (dark days are synthesised later).
  Later reports win for a page (`align_66` replaces the pair008 rows of `align_04`).

## To resume
1. `ls docs/eval/title_check_2026-10-10/align/reports` and list chunk numbers missing against `chunks/` (the 14 in flight may
   have finished or died with the session; re-launch any with no report). Launch format: a blind reader agent with
   "read BRIEF_ALIGN.md, chunk `align_NN.csv`, write `reports/align_NN.csv`, reply with one line".
2. Run `uv run python docs/eval/title_check_2026-10-10/align/compare_structure.py`; it prints pages / page-columns / differing rows.
3. **Triage `discrepant_columns.csv`.** Many are one-row differences in one column. For each, look at `discrepancies.csv`
   (read_subcells vs stored_sessions, stored event ids) and check the scan yourself: a stored split where the print is one cell,
   or the reverse, is the cascade origin; then read the whole column (receipts + first title) to see where the shift ends and
   fix with a script like `fix_shift_cascades.py` (before-state asserted, backup, rebuild, `check_person_link_alignment.py`).
   Whole-row differences common to all five theaters of one date (e.g. 1890-91 pair014 28 Dec-2 Jan, pair024 6-12 Apr)
   are not cascades: they mean the stored data has no session for printed rows (Christmas/Lent closures read as splits or
   dashes) or the reader labelled rows differently; check once, then dismiss.
4. Pages with no PDF image (not read): `repertoire_1890-91_p015`, `repertoire_1890-91_p023` (hand-photographed).
   `repertoire_1895-96_p026` also hand-photographed (14 cells unread). Stored banner/empty morning-evening sessions exist
   on 1890-91 p015, which was why the stored-data detector listed it.
5. Image-mapping trap: for 1890-91 the PDF has two scans of 1-20 Nov (idx 3 and 4) and no Oct 12-31 spread; pair008 uses
   the photograph `pdf/RepertoireTables/ForUpload_1890-91_Repertoire_002a.jpg`. Any page whose read matches NONE of its stored
   day numbers is a wrong-image page; check the header month printed above the first date.

## Already settled by this thread
* 1910-11 p009 Михайловскій 9/10 Nov: the scan itself prints 1006 р. 75 к. on both days (cleared, not a stored duplicate).
* Fixed and committed: 1899-00 p012 MIH, p018 ALX, 1891-92 pair012 ALX (follow-up 14, `fix_shift_cascades.py`).
* Still open from `shift_candidates.csv` after charts 01-03 are triaged (read `reports/align_01..03.csv` deep columns): the
  duplicate candidates 1892-93 pair012 MAR 9/10, 1893-94 pair006 ALX 15/16, 1893-94 pair016 BOL 23/24, 1910-11 p041 MAR
  10/11 and the six banner-only pages.
