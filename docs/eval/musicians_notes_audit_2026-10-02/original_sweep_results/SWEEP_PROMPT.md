# Musicians sweep: verification instructions (REPORT ONLY)

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Historical Imperial Theater yearbook "Spiski" (Roster) pages, VLM-extracted into DuckDB (`outputs/full_run/imperial_theaters.duckdb`, table `raw.person_entry`). You are verifying the **Musicians** pages assigned to you. Run python only as `uv run python3` from the project directory (plain python3 has no PIL/duckdb).

## The bug class (confirmed on 60+ pages already)
On pages where a numbered list continues from an earlier page, the extraction often lost the real section heading and stamped an unrelated value on many/all rows: `heading_path` and/or `institution` (e.g. "Управляющій Училищемъ", "Хозяйственное отдѣленіе / Полиціймейстеры / Маріинскій театръ", "Артисты балета", "Императорское С.-Петербургское Театральное Училище", a bare sub-heading like "Музыканты:" copied into institution, a single theater name stuck page-wide). Other shapes seen: the page-top/real institution dropped at a page break; a wrong theater label shifted one row; fabricated labels borrowed from another list; non-standard spellings. Pages can also be **two-tiered** (only part wrong).

## For EACH assigned page
1. Read its bundle `/tmp/musicians_sweep/<page_id>.txt` (all rows with e-number, list_number, name, heading, institution, instrument). Read the scan `outputs/roster_images_full/images/<page_id>.png`. Zoom with PIL (crop, 3x LANCZOS resize, save under /tmp/musicians_sweep/crops/, then Read it) whenever a letterform or heading is small/ambiguous; normal-resolution reads are NOT reliable for о/ю, ь/ъ, н/и.
2. Determine what is actually PRINTED on this page: section headings (institution-level, e.g. "Оркестры.", "Оркестръ Малаго театра."; sub-headings, e.g. "Музыканты:", "Капельмейстеръ:", "Музыкальная библіотека.") and where each starts, in which column, between which list numbers.
3. For continuation pages (no heading printed, list_number does not start at 1): trace back through earlier pages of the same series (same page_id prefix, lower pNNN; scans + `raw.person_entry`) until you find the page that PRINTS the heading; confirm numbering runs unbroken (no restart at "1."). A numbered list restarting at 1 means a NEW section.
4. Compare to the DB. Verdict per row range: OK, FIX (give the correct values), or UNCERTAIN.

## Conventions you MUST respect (project rules, hard-won)
- Never modernize pre-reform orthography (ъ, ѣ, і, ѳ). Spelling variation between years is real; do not "correct" a variant to a norm unless the scan shows the DB differs from what is printed.
- Institution strings vary genuinely per volume: "Оркестры." (with period) vs "Оркестры" (none) are both real; take each season's own printed/established form (check that series' p000 via DB). "Оркестръ Малаго/Михайловскаго/Александринскаго театра." are real theater-specific institutions.
- In this corpus `institution` for plain orchestra rows is the section-level title (e.g. "Оркестры.") and `heading_path` the sub-heading ("Музыканты", or "Оркестръ оперы и балета / Музыканты" where that tier is printed). Follow the convention the series' own correctly-captured p000/neighbors use; state which you followed.
- Standalone librarian listings (e.g. Фарскій, Альбертъ Карловичъ, also an orchestra violist with "онъ же и библіотекарь") appear twice by design: the numbered orchestra entry AND a separate unnumbered "Музыкальная библіотека. / Библіотекарь." entry. Check each instance by scan; do not assume.
- A page may mix a continuation list AND a fresh section (e.g. a Малый театръ orchestra block, Балетный оркестръ block, library block). Report exact e-number ranges for each.
- If the heading IS correct but institution is wrong (or vice versa), say which field.
- Do not guess. Grade each fix: DIRECT (printed on this page, you read it), CONTINUITY (list_number lineage to a page where it is printed), ANALOGY (inferred from other seasons/pages). Anything ANALOGY-only is UNCERTAIN: report it, do not assert it.
- Expect many pages to be OK. Report OK when correct; do not force a bug verdict.

## HARD RULES
- REPORT ONLY. Do NOT edit, create or delete any project file (including docs/query_log.md). Crops go in /tmp/musicians_sweep/crops/ only.
- Do NOT call spawn_task or start background work. Do not message other agents.
- DB access is read-only: `duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)`.

## REPORT FORMAT (end your final message with exactly this machine-readable section)
```
RESULTS
<page_id> | OK | all rows correct (state convention followed)
<page_id> | FIX | e001-e034 | heading=<correct value or KEEP or NULL> | inst=<correct value or KEEP> | DIRECT/CONTINUITY | one-line basis
<page_id> | KEEP | e035 | already correct (reason)
<page_id> | UNCERTAIN | e0xx-e0yy | what is unclear / what you'd need
OTHER FINDINGS
- anything outside your assigned pages (adjacent pages that look buggy, name misreads you noticed, etc.), one line each
```
Use e-numbers exactly as in the bundle (e001 = first row). Cover every row of every assigned page in RESULTS (no gaps, no overlaps). Above RESULTS you may give short prose reasoning per page.
