# ProductionTeam audit, 2026-10-02 (stage 1 APPLIED; stage 2 = section structure still to do)

All 94 ProductionTeam pages (2009 raw rows) were read entry by entry at zoom by report-only agents (19 groups of <=5 pages; PROMPT.md is the brief,
bundles/ the stored rows each agent was given, results/ their reports). Group 2 (1891-92 p001-p003, 1892-93 p000-p001) was cut off by a usage limit and is being
re-run; its results file will be added when it finishes. NOTHING in the data has been changed yet: next steps are (1) field-level fixes (names, tenure text,
field shifts, rows that are not people, missing rows) with a blind second read, then (2) a per-page section map to rebuild institution/heading_path.
Tally so far (18 groups): 278 field-level discrepancy lines (surnames 105, tenure text 79, list numbers 23, title 21, patronymic 18, first name 16,
ordinals 9, date 7), 296 section/heading lines, 16 missing/extra-row lines, 131 date checks (5 differ).

## Update: stage 1 applied (see docs/eval/known_issues.md, issue #132)
All 19 groups reported (group 2 re-run). Blind second reads: verification/ (36 singleton name misreads: 36/36 agree; 36 free-form entries all confirmed).
apply/: engine_pt.py + phase1..5 (strict expected-old assertions), run_all.py, relink_apply.py (person_link remap for removed rows), removed_rows.json (the 14 rows
removed from raw, kept here verbatim), all_log.json (every edit). Section structure (institution/heading_path) is NOT touched yet -- stage 2.
