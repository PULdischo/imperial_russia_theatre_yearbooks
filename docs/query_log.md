
## 2026-08-19 — How ordinal suffixes (1-я/2-й etc.) are tracked

```sql
SELECT COUNT(*) FROM research.person
WHERE ordinal_suffix IS NOT NULL AND trim(ordinal_suffix) != '';

SELECT ordinal_suffix, COUNT(*) FROM research.person
WHERE ordinal_suffix IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;

SELECT display_name, canonical_family_name, ordinal_suffix
FROM research.person WHERE canonical_family_name LIKE 'Гаврилова%';

SELECT display_name, canonical_family_name, ordinal_suffix
FROM research.person WHERE canonical_family_name = 'Золотаренко';

SELECT COUNT(*) FROM research.person
WHERE canonical_first_name IN ('1-й','2-й','2-я','1-я');
```

Result: 449 of 3,526 active `research.person` rows have `ordinal_suffix`
populated (values: 2-я×111, 1-я×107, 2-й×89, 1-й×84, 3-я×30, 3-й×14,
4-я×8, 4-й×4, 5-й×2). Confirmed the two Gavrilovas resolved earlier this
session carry `1-я`/`2-я` correctly. Confirmed 3 residual rows still have
a bare ordinal stuck in `canonical_first_name` (the known, documented
issue #17 exceptions that didn't pass the "looks like a name" guard).

## 2026-08-19 — Found and fixed: `display_name` stale on every manual merge fix made this session

While grounding the ordinal-suffix answer above, found `research.person`
carried a stale `display_name` on 48 rows — every survivor whose
`canonical_family_name`/`canonical_first_name`/`canonical_patronymic`/
`ordinal_suffix` had been manually corrected earlier this session, since
those UPDATE statements never touched `display_name` itself. Discovered
via a direct comparison: `display_name` recomputed from the row's own
canonical fields (same formula as `build_person_tier1`) didn't match the
stored value for 48 active rows, e.g. `Гаврилова, Евлогія Помпеевна`
(stale, wrong OCR-garbled first name and missing the ordinal/alias)
vs. the row's own correct fields (`Евдокія`, ordinal `2-я`,
family `Гаврилова (Воскресенская)`).

```sql
-- diagnostic: recomputed display_name vs stored, across all of research.person
SELECT person_id, display_name, canonical_family_name, ordinal_suffix,
       canonical_first_name, canonical_patronymic
FROM research.person;
-- (compared client-side against family+ordinal+", "+first+patronymic)
```

Result: 48 mismatches found, all in `entities.person`, all traceable to
this session's manual merges. Fixed by regenerating `display_name` for
every active survivor from its own canonical fields via direct UPDATE,
then rebuilding `research.person` and `research_dataset.sqlite`.
Re-checked after rebuild: 0 remaining mismatches.

## 2026-08-19 — Auditing raw.person_entry.instrument for non-instrument text

```sql
SELECT entity_type, COUNT(*) FROM raw.person_entry WHERE instrument IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;

SELECT instrument, COUNT(*) FROM raw.person_entry WHERE instrument IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;

SELECT column_name FROM information_schema.columns WHERE table_schema='research' AND column_name ILIKE '%instrument%';
SELECT instrument, COUNT(*) FROM research.person_appearance WHERE instrument IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;
```

Result: 1200 non-null `instrument` values, all in Musicians, 33 distinct
strings. 23 were not instruments: 21 rows held the literal cross-reference
note `"см. оперный оркестръ"`, 1 held a resignation continuation sentence
(`"Оставилъ службу 1 октября 1903 г."`), 1 held a transfer continuation
sentence (`"Переведенъ съ 1 октября 1902 г. въ Малый театръ."`) — both of
the latter on real, otherwise-correctly-transcribed people (Барсукъ-
Самборскій, Гейслеръ). Confirmed this contamination was already present,
unfiltered, in the published `research.person_appearance.instrument`
column (straight passthrough from `raw.person_entry` — the pipeline had
never added a cleaning step for this field, unlike `service_class_clean`/
`heading_path_clean`).

## 2026-08-19 — Verifying the instrument_clean/tenure_note_text_clean fix (post-rebuild)

```sql
SELECT instrument_clean, COUNT(*) FROM analysis.person_entry WHERE instrument_clean IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;
SELECT COUNT(*) FROM analysis.person_entry WHERE instrument IS NOT NULL AND instrument_clean IS NULL;
SELECT entry_id, instrument, instrument_clean, tenure_note_text, tenure_note_text_clean FROM analysis.person_entry
  WHERE entry_id IN ('musicians_1903-04_MSK_p000__e017', 'musicians_1903-04_MSK_p000__e029');
SELECT instrument, COUNT(*) FROM research.person_appearance
  WHERE instrument LIKE 'см.%' OR instrument LIKE 'Оставилъ%' OR instrument LIKE 'Переведенъ%' GROUP BY 1;
SELECT COUNT(*) FROM research.person_appearance WHERE instrument IS NOT NULL;
```

Result: 30 distinct instrument_clean values (was 33), all genuine
instruments. 23 rows correctly nulled. The 2 continuation-note rows now
carry the resignation/transfer text appended onto tenure_note_text_clean
instead, e.g. "съ 19 сентября 1882 г. Оставилъ службу 1 октября 1903 г."
Confirmed 0 contaminated rows remain in published
research.person_appearance.instrument (1177 non-null rows, down from
1200, all genuine instruments).

## 2026-08-19 — TheaterSchoolStaff: Сенкусь/Сенкусъ duplicate, Священникъ/Дьяконъ role headings, Флоринскій's orphaned resignation note

```sql
SELECT entry_id, family_name, page_id FROM raw.person_entry WHERE family_name IN ('Сенкусь','Сенкусъ');
SELECT DISTINCT pes.start_date_undate FROM raw.person_entry pe
  JOIN raw.person_entry_service pes ON pes.entry_id=pe.entry_id
  WHERE pe.family_name IN ('Сенкусь','Сенкусъ');
-- entry-level context around 'Священникъ'/'Дьяконъ' and the fake 'Оставилъ службу' row:
SELECT entry_id, family_name, first_name, patronymic, rank_or_title, tenure_note_text
  FROM raw.person_entry WHERE page_id='theaterschoolstaff_1896-97_p000' ORDER BY entry_id;
```

Result: all 5 Сенкусь/Сенкусъ appearances share tenure start 1903-09-01 —
confirmed one real person split across a spelling variant, merged
("Сенкусъ" chosen as canonical, 3 vs. 2 occurrences). Page context (and
the source scan, `ForUpload_1896-97_Spisok_Teachers.pdf` p.1) confirmed
"Священникъ"/"Дьяконъ" are role-heading labels ("Priest." / "Deacon.")
immediately preceding the real named clergy (Пигулевскій, Флоринскій),
not people themselves. Also confirmed the standalone fake entry
`family_name="Оставилъ службу"` on that page belongs to Флоринскій (the
entry immediately before it) — his resignation date, orphaned by issue
#28's extraction bug.

## 2026-08-19 — Verifying the phantom-person denylist after rebuild

```sql
SELECT COUNT(*) FROM entities.person_link WHERE person_id IN (
  '5d9f7500-2be2-408e-a983-a01183626b09', '785816e3-1a1d-4df7-81b4-fcddc4b2d7d2',
  'd4eaea08-f4d3-4413-8ff8-0d381a8395d5', '23bf557c-76fe-497b-9fab-ebf1fdd7eab3',
  '2e495ee0-94af-4350-9a7a-b9471f4de613');
SELECT COUNT(*) FROM research.person WHERE canonical_family_name IN
  ('Священникъ','Дьяконъ','Оставилъ службу','†','И.');
SELECT canonical_family_name FROM research.person WHERE canonical_family_name LIKE 'Сенкус%';
SELECT tenure_note_text FROM research.person_appearance WHERE appearance_id='theaterschoolstaff_1896-97_p000__e013';
```

Result: the 5 denylisted phantom person_ids had 15 raw appearances
between them (5+3+5+1+1) — more than the single confirmed row each was
originally found from, since Tier-1 collapses every appearance with
identical text onto the same person_id regardless of season. All 15
correctly excluded from `research.person_appearance` (21174 → 21159
rows) and all 5 phantom people excluded from `research.person` (3524 →
3518). Флоринскій's recovered resignation date confirmed present in his
`tenure_note_text`. `research_dataset.sqlite` rebuilt.

## 2026-08-19 — Graduates name-parsing gap: scope, drama-department exclusion, and BalletArtists cross-check design

```sql
SELECT entry_id, family_name, first_name, patronymic, heading_path, tenure_note_text
FROM raw.person_entry WHERE entity_type='Graduates' AND (first_name IS NULL OR trim(first_name)='')
ORDER BY entry_id;
-- 104 blank-first-name Graduates rows; 79 match "Surname, Firstname." pattern (regex-verified in Python)
SELECT COUNT(*) FROM raw.person_entry WHERE entity_type='Graduates' AND (heading_path ILIKE '%драмат%' OR institution ILIKE '%драмат%');
-- 0 -- drama-department rows don't carry that substring; identified instead by heading_path IN
-- ('Со свидѣтельствами / Ученицы','Съ аттестатами / Ученицы'), confirmed against the Билибина/Рыкъ page
-- found earlier this session (10 rows, all drama, correctly excluded from ballet scope).
```

Result: 79 compound-name rows confirmed as one uniform pattern (no
patronymic ever printed, no ordinals, single comma) — safe to split.
Checked 63/79 for an existing full-form duplicate elsewhere in
`entities.person`: found duplicates for all 63, but most names have 2-7
candidates (common surnames), too ambiguous to auto-merge safely — split
the name fields only, did not attempt merging.

## 2026-08-19 — Graduates tenure-start-date extraction: `parse_russian_date` gap and BalletArtists cross-check

```sql
SELECT DISTINCT institution FROM raw.person_entry WHERE entity_type='Graduates'
  AND (institution ILIKE '%опредѣлен%' OR institution ILIKE '%труппу%');
SELECT pe.family_name, pe.first_name, pe.tenure_note_text, pes.start_date_undate
  FROM raw.person_entry pe LEFT JOIN raw.person_entry_service pes ON pes.entry_id=pe.entry_id
  WHERE pe.entity_type='Graduates' AND pe.tenure_note_text LIKE '%балетную труппу%' LIMIT 10;
-- start_date_undate NULL for every one -- confirmed parse_russian_date() was never run
-- against this "N-го [month] года, въ [Город] балетную труппу" sentence shape.
SELECT COUNT(*) FROM raw.person_entry WHERE regexp_matches(tenure_note_text, '[0-9]+-(го|й|е|я|му)\s');
-- 188 rows across BalletArtists/Musicians/TheaterSchoolStaff/Graduates -- confirmed parse_russian_date's
-- day-number regex required whitespace directly after the digit, so any hyphenated ordinal
-- ("1-го сентября") was silently unparseable in ALL FOUR entity types, not just Graduates.
```

Result: fixed `pipeline/schemas/dates.py`'s `_DATE_RE` to accept an
optional hyphenated ordinal suffix on the day number. Verified against 6
known-good and newly-fixable cases (`1-го сентября 1892 г.` etc.) —
correct output, no regression on the existing non-ordinal cases or the
season-range case. This is a shared utility fix benefiting all 4 entity
types, not scoped narrowly to Graduates.

## 2026-08-19 — Verifying the report-vs-BalletArtists tenure date cross-check

```sql
-- for each report-sourced date, check whether BalletArtists agrees:
SELECT DISTINCT pes.start_date_undate FROM raw.person_entry pe
  LEFT JOIN raw.person_entry_service pes ON pes.entry_id=pe.entry_id
  WHERE pe.entity_type='BalletArtists' AND pe.family_name=? AND pe.first_name=? AND pes.start_date_undate IS NOT NULL;
-- run for all 222 report-sourced rows (Python loop)
SELECT pe.entry_id, pe.page_id, pes.start_date_text, pes.start_date_undate
  FROM raw.person_entry pe JOIN raw.person_entry_service pes ON pes.entry_id=pe.entry_id
  WHERE pe.entity_type='BalletArtists' AND pe.family_name='Ваганова';
```

Result: 167/222 agree exactly, 26 disagree, 29 have no BalletArtists
record to check against. Of the 26 disagreements, two full cohorts
(1896-97, 7 people; 1897-98, 14 people) show an identical, systematic
one-month gap (Report says May, BalletArtists says June) — confirmed
genuine by direct page check for the 1896-97 cohort
(`ForUpload_1896-97_TheaterSchoolReport.pdf` p.1: "съ 1-го мая 1897
года" is exactly what's printed) and by Vaganova's BalletArtists date
("1 іюня 1897 г.") repeating identically across all 11 seasons she
appears in — too consistent on both sides to be a transcription error on
either. Documented as a confirmed cross-document discrepancy in
`docs/eval/source_document_anomalies.md`, not treated as a bug to fix.

## 2026-08-19 — Checking whether missing Graduates patronymics are a source feature or a real gap

```sql
SELECT COUNT(*), SUM(CASE WHEN patronymic IS NOT NULL AND trim(patronymic)!='' THEN 1 ELSE 0 END)
FROM raw.person_entry WHERE entity_type='Graduates' AND family_name IS NOT NULL AND trim(family_name)!=''
  AND heading_path NOT IN ('Со свидѣтельствами / Ученицы','Съ аттестатами / Ученицы');
-- 442 rows, 43 with patronymic
-- per-page: does ANY row on a page have a patronymic, to find pages worth double-checking
SELECT page_id, COUNT(*), SUM(CASE WHEN patronymic!='' THEN 1 ELSE 0 END)
FROM raw.person_entry WHERE entity_type='Graduates' GROUP BY 1;
```

Result: 43/47 pages are uniformly one way (all rows have a patronymic, or
none do) — confirmed against several already-viewed page images that this
is genuinely how the source prints each cohort, not a gap. Exactly 1 page
(`graduates_1890-91_p002`) was mixed: 19/21 rows had a patronymic, 2
didn't. Investigated those 2 directly.

```sql
-- corpus-wide check for a first_name/patronymic run together with no
-- separator at all (distinct from the far more common hyphenated-
-- compound-first-name pattern, e.g. "Іоганъ-Фридрихъ", which is real and
-- was NOT touched)
SELECT entry_id, entity_type, family_name, first_name, patronymic
FROM raw.person_entry WHERE first_name IS NOT NULL;
-- filtered in Python: first_name has no hyphen but matches
-- ^[Capital][lowercase]+[Capital][lowercase]+$ (an embedded capital letter
-- with no separator at all)
```

Result: exactly 3 rows corpus-wide have this shape: 2 in Graduates
(`Уракова, АннаПетровна` / `Кочетовская, ЕкатеринаВладиміровна` — both on
the same mixed page found above) and 1 in BalletArtists (`Пуни,
ЛеонтинаКонстанція`, not fixed — "Констанція" doesn't have a typical
patronymic suffix, more likely a compound first name than a patronymic,
left for individual verification rather than guessed). The 2 Graduates
rows were confirmed against the already-viewed scanned page (prints
"Анна Петровна" / "Екатерина Владиміровна" as two separate words) and
fixed. Confirms the remaining ~372 blank patronymics in the ballet
graduates dataset are a genuine source feature, not a systematic
extraction gap.

## 2026-08-19 — Correction: removed inferred (BalletArtists-sourced) dates from tenure_start_date

Per explicit instruction: `tenure_start_date` must be blank unless the
Theater School Report itself states a date -- the earlier version of
`ballet_graduates_tenure.csv` had been filling this field from a single
plausible BalletArtists match when the Report gave nothing
(`balletartists_crossref`, 149 rows), which is a cross-check, not a
primary source, and shouldn't have been written into the authoritative
date column. Regenerated: `tenure_start_date` now populated only for
`report_per_row` / `report_per_row_exception` / `report_hand_verified`
(222 rows); the other 195 are blank with `source='not_stated_in_report'`
and the BalletArtists reference (if any) moved into `note`, explicitly
labeled "not used".

## 2026-08-20 — Adding a `school` (St. Petersburg/Moscow) column: drama-page leak found, classifier bug, and a 13-row hand-verified date recovery

```sql
-- checking whether the 20-row drama page (graduates_1890-91_p005) was fully excluded
SELECT entry_id, page_id, family_name, heading_path, institution
FROM analysis.person_entry WHERE page_id = 'graduates_1890-91_p005' ORDER BY entry_id;
-- 20 rows total; the CSV's exact-match filter (heading_path IN
-- ('Со свидѣтельствами / Ученицы','Съ аттестатами / Ученицы')) only matches
-- 10 of them -- 'Ученики'/'Ученикъ'/'Въ Москвѣ / Съ аттестатами / Ученицы'
-- variants on the SAME page had leaked through. Confirmed corpus-wide this
-- is the only page with any drama heading, so excluded by page_id instead.

SELECT entry_id, page_id, institution, heading_path FROM analysis.person_entry
WHERE entity_type='Graduates';
-- joined in Python against the 417-row CSV to classify school from
-- institution/heading_path substring match. First pass used substring
-- "москв" and found 0 Moscow institution matches -- bug: "Московское"/
-- "Московская" contain "моск" but not "москв" (5th letter is "о" not "в").
-- Fixed to "моск"; re-ran, 268 SPB / 139 Moscow / 13 unresolved
-- (graduates_1895-96_p003, no institution stated on that page at all).
```

Result: rendered and read `ForUpload_1895-96_TheaterSchoolReport.pdf`
pages at index 2–3 directly (`grad_1895-96_idx2.png`/`idx3.png`).
Confirmed p002 = "Московское Театральное Училище. / Балетное
отдѣленіе." (cohort-size paragraph, 13 people); p003 lists the same 13
graduates by name with no institution restated, closing with "...
опредѣлены на службу, съ 1-го сентября 1896 года, въ Московскую
балетную труппу" — a date the original extraction dropped, same
failure mode as the two existing `report_hand_verified` cohorts.
Reclassified these 13 as `school='Moscow'`, `source='report_hand_verified'`,
`tenure_start_date='1896-09-01'`. Regenerated
`outputs/full_run/ballet_graduates_tenure.csv`: 407 rows (10 drama rows
dropped from the earlier 417), new `school` column (268 St. Petersburg /
139 Moscow), `source` counts `report_per_row` 187 / `report_hand_verified`
38 / `not_stated_in_report` 182.

## 2026-08-20 — Full hand-check of every remaining `not_stated_in_report` page in ballet_graduates_tenure.csv

```sql
-- group the 182 not_stated_in_report rows by page: pages where every row
-- was blank (strong dropped-paragraph candidates) vs. a mix
SELECT entry_id, source FROM ballet_graduates_tenure_csv;  -- (grouped in Python by page_id prefix)
-- 12 all-blank pages (168 rows) + 1 mixed page (graduates_1892-93_p001, 14 rows)
```

Result: rendered and read all 13 candidate pages directly (some via
`page.set_cropbox(page.mediabox)` after confirming with RG that the
default-cropped renders were her own intentional drama-content cuts, not
missing data). Found: `graduates_1890-91_p006` is a second drama page
(continuation of p005's list) — excluded, 8 more drama rows dropped.
10 pages had a genuine dropped assignment paragraph on the same page as
the list — hand-recovered as `report_hand_verified`:
`graduates_1890-91_p002` (21 rows, SPB 1891-06-01 except Легатъ
1891-10-01, Moscow 1891-09-01), `graduates_1891-92_p000` (18 rows,
1892-06-01, Бекъ to Moscow troupe same date), `graduates_1892-93_p001`
(13 rows, 1893-06-01 — sentence existed but was only attached to
Тихомировъ's own row), `graduates_1898-99_p000` (14, 1899-06-01),
`graduates_1902-03_p000` (14, 1903-06-01), `graduates_1905-06_p000`
(15, 1906-06-01), `graduates_1906-07_p000` (15, 1907-06-01). The
remaining 5 pages (64 rows) checked and confirmed genuinely blank — 4
are immediately followed by a "Драматическіе курсы" heading with no
assignment paragraph, 1 (`graduates_1900-01_p001`) is a 2-page PDF
excerpt whose list runs to the literal last line with nothing after.
Regenerated `outputs/full_run/ballet_graduates_tenure.csv`: 399 rows
(260 St. Petersburg / 139 Moscow); `source`: `report_per_row` 187,
`report_hand_verified` 148, `not_stated_in_report` 64.

## 2026-08-20 — Verifying no drama-department graduates remain in ballet_graduates_tenure.csv

```sql
-- corpus-wide keyword sweep, entity_type='Graduates', all fields that could carry drama text
SELECT entry_id, page_id, family_name, heading_path, institution, tenure_note_text
FROM raw.person_entry
WHERE entity_type='Graduates'
  AND (institution ILIKE '%драмат%' OR heading_path ILIKE '%драмат%'
       OR tenure_note_text ILIKE '%драмат%' OR heading_path ILIKE '%аттестат%'
       OR heading_path ILIKE '%свидѣтельств%' OR heading_path ILIKE '%свидетельств%');
-- 17 rows total, all on graduates_1890-91_p005/p006 -- already excluded. Re-ran the same
-- query joined against the current 399-row CSV: 0 hits remain.
```

Result: no drama-department text signal anywhere in the corpus outside
the two already-excluded pages. Additionally checked which of the 399
rows have no "балет" keyword anywhere in their own row/page text (95
rows) as a second, independent check — read the 4 not-yet-checked pages
behind that (`graduates_1892-93_p003`, `graduates_1894-95_p001`,
`graduates_1895-96_p001`, `graduates_1897-98_p001`) directly. Three were
confirmed ordinary St. Petersburg ballet pages (truncated date clause
only, not a data problem). `graduates_1892-93_p003` (12 rows) had a real
bug: `institution` field said St. Petersburg but the page itself is
headed "Московское Театральное Училище / Балетное отдѣленіе" with a
Moscow-troupe closing paragraph — fixed `school`/`troupe_city` to
Moscow for those 12 rows. No drama rows found or removed this pass;
school split corrected to 248 St. Petersburg / 151 Moscow (399 rows
total, unchanged).

## 2026-08-20 — Verifying the `school` field for all 399 rows, not just the drama question

RG asked specifically about `school` correctness after the 1892-93_p003 fix. Ran a
systematic check rather than spot-checks:

```sql
-- rows where school was derived ENTIRELY from institution (heading_path gave no city signal) --
-- exactly the failure mode that caused the 1892-93_p003 bug
SELECT entry_id, page_id, institution, heading_path FROM analysis.person_entry
WHERE entity_type='Graduates';  -- filtered/joined in Python against the 399-row CSV
-- 334 rows / 27 distinct pages relying solely on institution.
```

Result: read every one of the 27 pages directly against the scanned PDF (some
newly downloaded/rendered: 1893-94, 1896-97 idx3, 1897-98 idx2, 1898-99 idx2,
1899-00 idx0, 1903-04, 1904-05). 24 of 27 were already correct. Found 2 more
pages with the same bug as 1892-93_p003 (`institution` field stale/says
St. Petersburg, but the page's own heading and/or the row's own
`tenure_note_text` states Moscow): `graduates_1896-97_p003` (12 rows,
tenure_note_text explicitly says "...въ Московскую балетную труппу" — the
classifier just wasn't using that field) and `graduates_1898-99_p002` (12
rows, same). Fixed `school`→Moscow for both (`troupe_city`/`tenure_start_date`
were already correct on both, since those came from date-parsing logic that
did use tenure_note_text).

```sql
-- rebuilt classifier precedence (heading_path > tenure_note_text > institution)
-- and re-ran the school-vs-tenure_note_text contradiction check corpus-wide
-- against the corrected CSV: 0 contradictions remain (excluding the one
-- legitimate individual exception, Тихомировъ, whose school genuinely
-- differs from his individually-assigned troupe_city by design).
```

Final: 399 rows, school split now 224 St. Petersburg / 175 Moscow (was
248/151). Every page that could have hit this specific bug (institution-only
classification) has now been read directly, not inferred.

## 2026-08-20 — Cross-checking the 148 `report_hand_verified` rows against BalletArtists (extends the earlier report_per_row-only check)

```sql
SELECT DISTINCT pes.start_date_undate FROM raw.person_entry pe
  JOIN raw.person_entry_service pes ON pes.entry_id = pe.entry_id
  WHERE pe.entity_type='BalletArtists' AND pe.family_name=? AND pe.first_name=?
    AND pes.start_date_undate IS NOT NULL;
-- run for all 148 report_hand_verified rows (Python loop), same method as the
-- original report_per_row check
SELECT pe.entry_id, sp.season, pes.start_date_text, pes.start_date_undate
  FROM raw.person_entry pe JOIN raw.person_entry_service pes ON pes.entry_id=pe.entry_id
  JOIN raw.source_pages sp ON sp.page_id=pe.page_id
  WHERE pe.entity_type='BalletArtists' AND pe.family_name=? AND pe.first_name=?
  ORDER BY sp.season;
-- run for the 3 disagreements, to see how many seasons/how consistently each date repeats
```

Result: 122/148 agree exactly, 23 have no BalletArtists record (expected —
not everyone entered service), 0 ambiguous, 3 disagree. Of the 3: **Бекъ,
Константинъ** — Report says 1892-06-01, BalletArtists says 1892-09-01
identically across all 15 seasons on record (1892-93–1907-08) — a genuine,
consistently-repeated 3-month gap, same shape as the already-documented
Vaganova/1897-98 May-vs-June pattern, added to
`docs/eval/source_document_anomalies.md`. **Тихомировъ, Владиміръ** —
Report 1892-06-01 vs. BalletArtists 1898-09-01 (only 2 seasons on record) —
a 6-year gap, flagged as likely a different person, not used.
**Ивановъ, Александръ** — Report 1906-06-01 vs. BalletArtists 1896-05-01
(1 season on record) — a 10-year gap on an extremely common surname,
flagged as likely a different person, not used. All three notes appended
to the CSV; `tenure_start_date` unchanged (keeps the Report's own value
in all three, per the standing rule).

## 2026-08-20 — Identity-linking the 399 ballet graduates to their BalletArtists career records

Built an independent, deliberately conservative identity-link check —
NOT using `entities.person_link`'s existing automatic tier1-key merges,
since that same mechanism produced a confirmed false merge previously
(issue #30, the two-different-Evdokia-Gavrilova case). Method (full
script logic in this session's work, not committed as a pipeline file):

```sql
-- for each of the 399 graduates, find BalletArtists rows matching on
-- family_name + first_name (+ patronymic, when the graduate's own record has one)
SELECT pe.entry_id, sp.season, sp.city, pes.start_date_undate
FROM raw.person_entry pe
LEFT JOIN raw.person_entry_service pes ON pes.entry_id = pe.entry_id
LEFT JOIN raw.source_pages sp ON sp.page_id = pe.page_id
WHERE pe.entity_type='BalletArtists' AND pe.family_name=? AND pe.first_name=? [AND pe.patronymic=?];
```

Classification: cluster same-named matches by chronological proximity of
`start_date_undate` (≤65 days apart = same person, print-run variance —
confirmed pattern, see below) and merge any clusters that share a raw
`entry_id` (person_entry_service allows multiple service PERIODS per
entry_id — a documented departure and re-enrollment is the same real
person, not two candidates; discovered via Легатъ, Иванъ, one entry_id
with two periods 1891–95 and 1897–99 "left service"). For the 335
graduates with a Report-stated `tenure_start_date`, that date is the
PRIMARY disambiguation anchor: a cluster within 130 days of it is linked;
none within range is `unlikely_match`; more than one is `ambiguous`. For
the 64 without a Report date, fall back to requiring a single dominant
city-consistent cluster.

Result: **342 linked, 46 no BalletArtists record, 9 ambiguous, 2
unlikely_match** (Тихомировъ Владиміръ, Ивановъ Александръ — both
already-known likely-different-person cases from the earlier tenure-date
cross-check).

Two findings surfaced while building/validating this, both checked
directly rather than assumed:

- **Мосолова, Вѣра**: BalletArtists shows "1 сентября 1893" in 11 of 13
  attested seasons and "5 сентября 1893" in 2 — checked both source pages
  directly (`ForUpload_1893-94_Spisok_BalletArtistsMoscow.pdf` p.2 #68
  vs. `ForUpload_1902-03_Spisok_BalletArtistsMoscow.pdf` p.3 #61); both
  say what they say, clearly and unambiguously, on their own page — a
  genuine day-level inconsistency across yearbook print editions for the
  same real person (confirmed by a single continuous unbroken career,
  including transferring between the Moscow and St. Petersburg troupes),
  not an OCR/model misread on either side.
- **Легатъ, Иванъ**: confirmed via `person_entry_service.period_order`
  that his single entry_id documents two separate service periods
  (1891-10-01–1895-01-01, then 1897-09-01–1899-12-01 "left service") —
  a real biographical departure-and-return, not two different people
  sharing a name.

## 2026-08-20 — Manual review of the 9 `ambiguous` identity-links, together with RG

Went through all 9 ambiguous cases' full raw BalletArtists candidate data
(entry_id, season, city, patronymic, start_date_text/undate) individually
rather than trusting the automated classifier's verdict as final.

Found 6 that resolve on principled grounds, not guessing:
- **Chronological impossibility** rules out one candidate outright (a
  BalletArtists record whose date precedes the graduate's own graduation
  by years cannot belong to them, regardless of whether it's really a
  different person or the same person's unrelated earlier record):
  Новикова Екатерина (1899-00 grad — her only possible candidate is
  "Дмитріевна" 1900-09-01, not "Александровна" 1892), Ѳедорова Ольга
  (1899-00 grad — "Васильевна" 1900-09-01, not "Николаевна" 1876),
  Федоровъ Михаилъ (1904-05 grad — the unnamed-patronymic 1905-08-01
  record, not "Викторовичъ"'s 1897/1903 periods), Савицкій Михаилъ
  (1905-06 grad — the 1906-08-01 record, not the 1900-08-01 one).
- **Automated-classifier gap, not real ambiguity**: Печатниковъ Николай
  (10/11 BalletArtists seasons agree on 1897-09-01, one 1904-05 record
  is an isolated outlier at 1897-06-01) and Орловъ Алексѣй (5/6 seasons
  agree on 1901-09-01, one outlier at 1900-09-01, same patronymic
  throughout) — same print-variance pattern already confirmed for
  Мосолова/Грабовская, just outside the classifier's fixed proximity
  window. Corrected on manual review.

Left 3 as genuinely ambiguous, per RG's explicit choice: Козловъ Ѳедоръ,
Долинская Евгенія, Андерсонъ Елизавета — each has a same-patronymic match
across all records but a real multi-month-to-1-year date split (not the
few-days/one-month pattern already confirmed elsewhere), judged too
uncertain to link without further verification.

**Bug caught and fixed during this pass**: the update script keyed only
on `family_name`+`first_name`, and one of the six safe-looking names
(Новикова, Екатерина) turned out to match TWO different real graduates
in the 399-row set (one from 1891-92, one from 1899-00) — the update
briefly overwrote the correct, already-established link for the 1891-92
graduate (whose own Report-stated date, 1892-09-01, is an exact
independent match for BalletArtists' "Александровна" record) with the
reasoning meant only for the 1899-00 graduate. Checked all 6 target names
against the 399-row set for this same collision risk; only Новикова had
one. Restored the 1891-92 graduate's correct link
(`graduates_1891-92_p002__e006` → "Александровна", 1892-09-01) using
`entry_id`, not name, before finalizing.

Final: 348 linked, 46 no_record, 3 ambiguous, 2 unlikely_match (399
total).

## 2026-08-20 — Fixed a real BalletArtists/Musicians name-field bug found while investigating an implausibly-high "non-graduate dancer" count

RG was skeptical of my first-pass "590 of 910 newly-employed dancers
don't match any Graduates record" figure. Investigating why turned up a
confirmed, fixable extraction bug, not just corpus-matching difficulty.

```sql
SELECT entry_id, family_name, first_name, patronymic, entity_type
FROM raw.person_entry
WHERE regexp_matches(first_name, '^[0-9IVXІ]+-(й|я|е)$');
-- 115 rows: 77 BalletArtists, 38 Musicians, 0 elsewhere. On these rows, a
-- bare ordinal ("1-й"/"2-я"/...) that should be appended to family_name
-- (the normal convention corpus-wide, e.g. "Крылова 2-я") landed as the
-- ENTIRE first_name instead, shoving the real first_name into patronymic
-- (as one word, or as "FirstName Patronymic" run together -- both shapes
-- confirmed).
SELECT DISTINCT family_name, first_name, patronymic FROM raw.person_entry
WHERE entity_type='BalletArtists' AND family_name LIKE 'Литавкинъ%';
-- confirmed the real-world cost: 2-3 real siblings ("Литавкинъ 1-й"/"2-й"/
-- unnumbered "Литавкинъ, Сергѣй") fragment into 9 distinct raw
-- (family,first,patronymic) triples across different season pages because
-- of this bug alone.
```

Fixed in `pipeline/build_duckdb.py`'s `build_analysis_schema()`: extended
`family_name_clean`/`first_name_clean`/`patronymic_clean` (already built
for the unrelated Graduates comma-format bug) with a new branch detecting
this exact ordinal-in-first_name shape and reassembling the three fields
correctly. Rebuilt `analysis.person_entry` in `outputs/full_run/imperial_theaters.duckdb`
(safe to re-run, `analysis.*` only). Verified: Литавкинъ's 9 raw triples
collapse to 3 correct identities.

```sql
-- distinct BalletArtists people (proper family+first grouping, patronymic
-- used only to split genuinely-conflicting identities, not as a strict
-- partition key -- a NULL patronymic from this exact bug no longer forks
-- off its own phantom identity) whose service began within the
-- 1890-91..1906-07 report-coverage window, and how many match a Graduates
-- name -- re-run after the fix:
```

Result: 910 → **869** distinct newly-employed dancers (a real but modest
~4.5% reduction — most people affected by the bug were still duplicated
under the same broken format across many seasons, so deduplication alone
recovers less than the fix's dramatic per-person effect suggests).
Matched-to-Graduates count improved much more: **320 → 396** (+76,
because the fix also repairs the actual strings being compared, not just
merges duplicates) — unmatched dropped from 590/910 (65%) to **473/869
(54%)**. Real improvement, but the majority of the original gap remains
unexplained by this bug alone; other confirmed causes (cross-edition
spelling variance, at least one source misprint — Nijinsky's own
"Наусинскій" typo in his 1906-07 Graduates listing) still need the same
manual verification already done for the 399 curated graduates, at
roughly 2x the scale (869 candidates). Not attempted in this pass.

## 2026-08-20 — Full BalletArtists name-field audit (RG: "make sure there are only real names in first_name/patronymic/family_name")

```sql
-- keyword scan for non-name content (role headings, resignation notes,
-- cross-references) in all three fields -- zero hits
SELECT count(*) FROM raw.person_entry WHERE entity_type='BalletArtists'
  AND regexp_matches(<field>, '<keyword>');  -- run per field x keyword, all 0

-- structural checks: blanks, digits, Latin letters, unusually long values
SELECT count(*) FROM raw.person_entry WHERE entity_type='BalletArtists' AND (<condition>);
-- first_name blank: 25; patronymic blank: 142; family_name digit: 1254
-- (mostly the normal "Surname N-я/N-й" ordinal convention); first_name
-- digit: 96; patronymic digit: 9; family_name >30 chars: 1; first_name
-- >20 chars: 7; family_name/first_name/patronymic with Latin letters:
-- 17/2/5
```

Investigated each non-zero bucket individually (not just the count):
found 3 more ordinal-misplacement shapes (Patterns B/C/D, 20+54+9 rows),
one dropped surname (confirmed against the scanned page, Zambelli), and
Latin-homoglyph corruption (24 rows, resolved via `translate()` for
single-character swaps plus 3 hand-confirmed multi-character cases,
1 left unresolved). Full detail and every fix in
`docs/eval/known_issues.md` #36. Rebuilt `analysis.person_entry` (safe,
`analysis.*` only). Verified after rebuild: 0 remaining digit-shaped or
Latin-letter-shaped `first_name_clean`/`patronymic_clean` values for
BalletArtists; `family_name_clean` has 1 confirmed-legitimate digit case
(a parenthetical alternate surname, "Дмитріева 2-я (Ѳедорова)") and 1
confirmed-unresolved Latin case ("Тииstrова", flagged not guessed).

## 2026-08-20 — Closing out the two remaining #36 items: the phantom row and the unresolved "Тииstrова" case

```sql
-- phantom row: find its entities.person UUID (read-only lookup, no
-- build_entities.py re-run) and confirm it's isolated (not merged with a
-- real person's other entries)
SELECT pl.entry_id, pl.person_id, p.display_name FROM entities.person_link pl
  JOIN entities.person p ON p.person_id = pl.person_id
  WHERE pl.entry_id = 'balletartists_1899-00_SP_p000__e008';
-- -> person_id 37dd8b11-7b83-4cb0-9d86-f5f34e611859
SELECT entry_id FROM entities.person_link WHERE person_id = '37dd8b11-...';
-- -> exactly the one entry_id, confirmed isolated
```

Added that UUID to `build_research_model.py`'s `NON_PERSON_IDS`, reran
the script (safe, pure derivation), confirmed absent from
`research.person` and `research.person_appearance` afterward.

For "Тииstrова" (`balletartists_1893-94_SP_p005__e002`): rendered and
read the actual scanned page (`ForUpload_1893-94_Spisok_BalletArtistsSP.pdf`,
p.62) — entry #135 plainly prints "Тистрова, Марія Ѳедоровна (съ 10
декабря 1873 г.)", an entirely ordinary Cyrillic surname with none of
the Latin-letter corruption seen in the extracted row. Hand-fixed via a
single-entry_id `family_name_pre` override in `build_duckdb.py`, rebuilt
`analysis.person_entry`. Verified: 0 rows with any Latin-letter-shaped
`family_name_clean`/`first_name_clean`/`patronymic_clean` remain for
`entity_type='BalletArtists'`.

## 2026-08-20 — Мендесъ/Джульетта: OCR misread, not source variance (RG asked directly)

Checked both "Мендесь" family_name instances and two of the three
"Джулъетта" first_name instances directly against their scanned pages
(`ForUpload_1906-07_Spisok_BalletArtistsMoscow.pdf` p.52 #52;
`ForUpload_1897-98_Spisok_BalletArtistsMoscow.pdf` p.94 #60;
`ForUpload_1903-04_Spisok_BalletArtistsMoscow.pdf` p.106 #53). All three
checked instances unambiguously print the standard spelling ("Мендесъ"
with ъ, "Джульетта" with ь) — every case checked was a misread, not
variance. A hard-sign/soft-sign (ъ/ь) OCR confusion, not a genuine
period spelling inconsistency. Fixed via hardcoded `family_name_pre`/
`first_name_pre` overrides in `build_duckdb.py` (2 + 3 = 5 rows),
rebuilt `analysis.person_entry`, confirmed 0 remaining "Мендесь"/
"Джулъетта" values.

## 2026-08-20 — "Пуни, ЛеонтинаКонстанція" resolved (RG: related to Cesare Pugni, confirmed her father's name)

Issue #34 had flagged this as an unresolved no-separator concatenation
("Констанція" doesn't have a typical Russian patronymic suffix, so it
wasn't confidently a patronymic). RG's context pointed at the answer:
this dancer's brother is listed on the same rosters as "Пуни, Николай
**Цезаревичъ**" ("son of Cesare") -- confirming the family is Cesare
Pugni's. Checked the actual scanned page
(`ForUpload_1905-06_Spisok_BalletArtistsSP.pdf`, p.18, entry #80): prints
"Пуни, **Леонтина - Констанція**" -- a genuine hyphenated compound first
name (same convention as "Іоганъ-Фридрихъ" elsewhere in the corpus), not
first_name+patronymic, and no patronymic printed at all (consistent with
every other foreign-origin artist already confirmed). The hyphen was
mangled three different ways across her 5 attested seasons (dropped
entirely and run together with no separator in one; captured with a
stray leading "-" on whatever landed in patronymic in three others; split
cleanly with no hyphen at all in the fifth). Fixed all 5 rows in
`build_duckdb.py`: `first_name_clean` = "Леонтина-Констанція",
`patronymic_clean` = NULL. Rebuilt and verified.

## 2026-08-20 — Follow-up BalletArtists field sweep (rank_or_title, dates.py) — RG: "any further issues in the raw ballet artists data?"

```sql
SELECT rank_or_title, count(*) FROM raw.person_entry WHERE entity_type='BalletArtists' GROUP BY rank_or_title ORDER BY 2 DESC LIMIT 8;
-- 24 rows show rank_or_title IN ('1-я','2-я','3-я') -- same ordinal-misplacement
-- bug as #36, a fourth field shape. Confirmed family_name/first_name/patronymic
-- otherwise complete on all 24; 0 already have the ordinal in family_name too.

SELECT count(*) FROM raw.person_entry pe JOIN raw.person_entry_service pes
  ON pes.entry_id=pe.entry_id
  WHERE pe.entity_type='BalletArtists' AND pes.start_date_text IS NOT NULL AND pes.start_date_undate IS NULL;
-- 49 rows: date sentence present, failed to parse. Inspected all 49 directly --
-- dominant cause (~38) is "юня" for "іюня" (June missing leading "і"); confirmed
-- 54 corpus-wide instances of that exact text shape via a broader LIKE scan.
```

Fixed both in the pipeline (not a data hand-edit): `rank_or_title`
pattern added to `build_duckdb.py`'s `family_name_clean` CASE (4th
ordinal-misplacement branch); `pipeline/schemas/dates.py` gained a "юн"
month stem plus Unicode combining-mark stripping (fixes a second
observed cause, a stray accent mark, "дека́бря"). Re-ran
`parse_and_validate.py` against the on-disk JSON (per CLAUDE.md, the
correct way to propagate a shared-parser fix) and reloaded `raw.*`
before rebuilding `analysis.*`. Verified: BalletArtists unparseable
count 49 → 7 (all 7 individually checked and confirmed to be genuinely
different, lower-value residual causes — 4 have no day number in the
source at all). Corpus-wide unparseable-with-text count also dropped
across all 6 entity types that share this date parser.

Also checked `institution` and `heading_path` for BalletArtists
specifically for contamination — confirmed neither is a name-field
issue: `institution` never reliably indicates city for this entity_type
(same generic strings on both SP and Moscow pages); `heading_path`
sometimes shows a stale administrative breadcrumb ("Управляющій
Училищемъ") on rows that are indisputably real dancers with correct
names. Neither touched.

## 2026-08-21 — Executing the BalletArtists entities.person identity-linking audit (paused in #37, resumed and completed)

```sql
-- Pass 1: cluster active BalletArtists-only person records by
-- (family_name, ordinal_suffix, first_name), normalized; find clusters
-- of 2+ where patronymic is blank on at least one side and doesn't
-- conflict with a single real patronymic elsewhere in the cluster.
SELECT p.person_id, p.canonical_family_name, p.ordinal_suffix, p.canonical_first_name,
       p.canonical_patronymic, p.first_attested_season, p.last_attested_season
FROM entities.person p
WHERE p.superseded_by_person_id IS NULL
  AND p.person_id IN (
      SELECT pl.person_id FROM entities.person_link pl
      JOIN raw.person_entry pe ON pe.entry_id = pl.entry_id
      GROUP BY pl.person_id
      HAVING count(*) = sum(CASE WHEN pe.entity_type='BalletArtists' THEN 1 ELSE 0 END)
  );
-- 1291 active records; 89 clusters (182 records) share family+ordinal+first_name
-- with 2+ person_ids. 46 clusters safe (blank vs. 1 real patronymic, no season+city
-- overlap between fragments) -- 45 merged (1 more, Пономаревъ, confirmed safe by
-- direct raw check first); 1 (Павлова 2-я) excluded -- different city, same season,
-- likely a different person, not merged.

-- Pass 2: cluster by (family_name, first_name, patronymic) instead, ignoring
-- ordinal_suffix -- finds cases where the ordinal itself is what's inconsistent.
-- 201 clusters found (bigger than Pass 1). 199 safe (no season+city overlap),
-- merged. 2 flagged for overlap, re-examined after RG confirmed ordinals are a
-- per-season positional label (not personal), then merged too.
```

10 more individually checked and merged (homoglyph/line-break/ordinal-
noise patterns already established, or single-season outliers bracketed
by a clear majority spelling); 16 + 3 (Ивановъ/Симонова/Ѳедорова
parallel-city cases, Михайлова simultaneous-entries case) left separate
after direct raw-data or scanned-page confirmation. Full reasoning per
cluster in `docs/eval/known_issues.md` #38.

Result: 287 merges (836 → 1,123 superseded, corpus-wide).
`entities.person` (BalletArtists-only, active): 1,291 → 1,004.
`entities.person_link` row count unchanged (21,174) throughout — no
appearance data lost. Rebuilt `research.person`
(3,517 → 3,230 rows) and `research.person_appearance` (unchanged,
21,158 rows) via `build_research_model.py`.

## 2026-08-21 — canonical_family_name majority-vote correction, found while spot-checking #38's merges

```sql
-- Мосолова, Вѣра spot-check revealed canonical_family_name='Молодова' --
-- a spelling never seen on any scanned page this session. Checked her
-- own linked raw entries:
SELECT DISTINCT pe.family_name FROM entities.person_link pl
  JOIN raw.person_entry pe ON pe.entry_id=pl.entry_id WHERE pl.person_id='1773bf9c-...';
-- {'Мосалова','Молодова','Мосолова'} -- 13/15 say 'Мосолова', canonical had
-- picked the 1-of-15 'Молодова' variant to display.

-- corpus-wide check: how many active BalletArtists person records have
-- canonical_family_name != the >=60%-majority raw spelling among their
-- own entries -- 64 found (of ~1000 active records).
```

Fixed all 64 via majority vote (same method already used repeatedly this
session): `canonical_family_name`/`display_name` reset to the dominant
raw spelling. Manually merged Мосолова's remaining un-merged 1892-93
fragment (`2b048dbf...`) once her label was corrected -- it had been
invisible to #38's clustering because it keyed off the wrong canonical
name. Re-ran the cluster check after the label fix: 2 new candidate
pairs surfaced (Кандауровъ Павелъ; Смирнова Марія), both reviewed and
left separate (different-root patronymics, no corroborating evidence,
same standard as #38's other left-separate cases). Rebuilt
`research.person`: 3,230 → 3,229.

## 2026-08-21 — Post-merge over-merge risk audit: date-gap check across all 391 same-patronymic BalletArtists merges

```sql
-- Reconstructed all merged (family_name, first_name, patronymic)-matched
-- survivor groups in entities.person (ignoring ordinal_suffix), pulled every
-- distinct start_date_undate from raw.person_entry_service for each survivor
-- via entities.person_link, excluding entries whose heading_path contains
-- "омощник" or "ежиссер" (legitimate secondary staff-role appointment
-- dates, not tenure-start contradictions -- see known_issues.md #38 addendum
-- on Ивановъ/Пономаревъ). Computed year-gap between earliest and latest
-- remaining distinct date per survivor.
```

Result: 391 same-patronymic merged groups total; 339 (87%) have full date
agreement; 51 have 2+ distinct regular-roster dates; of those, 25 have a
gap exceeding 3 years. Full list of the 25 recorded in this session's chat
transcript. Two followed up immediately below; the remaining ~23 are
unreviewed as of this entry.

## 2026-08-21 — Симонова, Марія Петровна: 1837 vs 1887 start-date discrepancy — checked against scanned page

```sql
SELECT pl.entry_id, pe.family_name, pe.first_name, pe.patronymic, pe.entity_type,
       pes.start_date_text, pes.start_date_undate, pe.heading_path, pe.page_id
FROM entities.person p
JOIN entities.person_link pl ON pl.person_id = p.person_id OR pl.person_id = p.superseded_by_person_id
JOIN raw.person_entry pe ON pe.entry_id = pl.entry_id
LEFT JOIN raw.person_entry_service pes ON pes.entry_id = pe.entry_id
WHERE p.canonical_family_name = 'Симонова' AND p.canonical_first_name='Марія'
  AND p.canonical_patronymic='Петровна'
ORDER BY pes.start_date_undate
```

Result: 22 linked entries. Exactly one (`balletartists_1890-91_MSK_p004__e020`)
reads "1837"; the other 21, spanning 17 separate yearbook editions
(1891-92 through 1906-07), all read "1887" or "съ 1887". Checked the actual
scan (`pdf/Spiski_BalletArtists/ForUpload_1890-91_Spisok_BalletArtistsMoscow.pdf`,
page 102, entry #92): the printed page itself reads "Симонова, Марія
Петровна (съ 1 сентября 1837 г.)" -- confirmed NOT an OCR/extraction
misread, the source genuinely prints "1837" in this one edition only.
Conclusion: a one-digit (3/8) typesetting error in the original 1890-91
Moscow volume, silently corrected in every subsequent edition -- not two
different people (a ~70-year active tenure is not physically plausible),
and not a pipeline bug of any kind. The merge is correct; the raw verbatim
"1837" text should NOT be altered (verbatim-preservation principle).

## 2026-08-21 — Тихоміровъ, Владиміръ Михайловичъ: 1892 vs 1898 start-date discrepancy — checked against scanned page and full raw corpus

```sql
SELECT entry_id, family_name, first_name, patronymic, heading_path, page_id
FROM raw.person_entry
WHERE entity_type='BalletArtists' AND family_name LIKE 'Тихом%'
ORDER BY page_id
```

Result: 60 raw entries. Checked the actual scan
(`pdf/Spiski_BalletArtists/ForUpload_1904-05_Spisok_BalletArtistsSP.pdf`,
page 25, entries #80-81): confirms two brothers, Тихоміровъ 1-й Сергѣй
Михайловичъ and Тихоміровъ 2-й Владиміръ Михайловичъ, both "съ 1 іюня
1892 г." The full raw list shows both brothers appearing together, same
two entry numbers apart, every SP season 1892-93 through 1907-08 (the
"1-й"/"2-й" ordinal swaps which brother holds it partway through, another
confirmed instance of the ordinal-is-positional pattern), both moving from
plain ballet artist to "Управляющій Училищемъ" (School Administrator)
together starting exactly 1898-09-01, later both under "Балетмейстеры."
Conclusion: NOT two different people -- one person's two career
milestones (dancer 1892, promoted to co-administrator 1898), the same
dual dancer+staff-role pattern already confirmed for Ивановъ/Пономаревъ
(known_issues.md #38 addendum). The merge is correct.

This corrects the 2026-08-20 graduates-linking entry's `unlikely_match`
classification for this same person (see the "Identity-linking the 399
ballet graduates" entry above): that check matched on exact raw
`family_name` string equality, which excludes every entry printed with the
"1-й"/"2-й" ordinal suffix attached to the family name (1892-93 through
1902-03, roughly half this person's actual career) -- it only ever saw the
post-1898 "Управляющій Училищемъ" years and had no visibility into the
earlier ballet-artist years, so it flagged a 6-year gap that does not
actually exist once the full record is visible. The `unlikely_match` flag
in that graduate-linking CSV note is now known to be a false negative
caused by its own matching method, not independent evidence against this
merge.

## 2026-08-21 — Full re-audit of the merge over-merge-risk pool: corrected methodology, page-verification pass on ~20 names

Discovered the original 2026-08-21 gap-check (391 pairs) had a bug: it counted a single
raw `entry_id`'s multiple legitimate `person_entry_service` periods (e.g. Легатъ-style
departure+re-enrollment) as if they were disagreement between merged records. Rebuilt the
check to group by `entry_id` first (MIN date per entry_id), then compare only ACROSS
distinct entry_ids linked to the same `entities.person` survivor:

```sql
-- per BalletArtists-only active survivor: MIN(start_date_undate) per linked entry_id,
-- excluding staff-role headings ('омощник'/'ежиссер'), then collect distinct values
-- across entry_ids (not across service periods within one entry_id)
```

Result: 90 survivors (not 391) have genuinely disagreeing dates across distinct entry_ids;
37 have a gap exceeding 3 years (not 25). This is the corrected, real risk pool.

Checked ~20 of the highest-risk names directly against scanned pages (zoomed crops at
600-1200dpi, not just raw text, after discovering digit misreads are possible at both
ends of the pipeline -- see Старостина below):

**Confirmed genuine one-edition print anomalies (page-verified, not two people):**
Симонова Марія Петровна (1837/1887, digit slip), Сапожникова Анна Іосифовна
(1835/1885, digit slip), Анкудинова Ольга Евгеніевна (1837/1887, digit slip, different
edition than Симонова), Рахмановъ Сергѣй Павловичъ (1905-06 and 1907-08 editions both
carry his brother Викторъ's "1903" date onto his own line -- confirmed on both pages),
Козловъ 1-й Федоръ Михайловичъ (1904-05 edition alone prints "1905" against 9 other
editions' "1900"/"1901" -- confirmed on page, not a misattribution from brother Алексѣй
as first suspected).

**Confirmed genuine multi-period service (explicit "по ... и съ ..." phrasing directly
on the page, not inferred):** Евлановъ Николай Павловичъ ("съ 23 августа 1884 г. по 3
декабря 1887 г. и съ 1 ноября 1890 г." -- left service, rejoined), Ивановъ 3-й Василій
Еремѣевичъ ("съ 1 сентября 1896 г. по 1 декабря 1900 г. и съ 9 сентября 1903 г."),
Тихоміровъ 2-й Алексѣй Дмитріевичъ ("съ 1 сентября 1899 г. по 13 сентября 1903 г. и съ
15 января 1904 г."). All three confirmed on
`ForUpload_1904-05_Spisok_BalletArtistsMoscow.pdf` p.58 and
`ForUpload_1906-07_Spisok_BalletArtistsMoscow.pdf` p.57.

**Confirmed genuine pipeline extraction bug, fixed:** Старостина Анна Ильинична
(`balletartists_1890-91_SP_p005__e020`) -- raw extraction read "1 января 1830 г.";
zoomed check of `ForUpload_1890-91_Spisok_BalletArtistsSP.pdf` p.63 shows the page
actually prints "1880," matching all other editions. Corrected in
`outputs/full_run/raw/balletartists_1890-91_SP_p005.raw.json` (both `tenure_note_text`
and `service_periods[0].start_date_text`), re-ran `parse_and_validate.py`, reloaded
`raw`/`analysis` schemas. Verified in DB: now reads 1880-01-01.

**Confirmed structurally safe via same-entry_id dual-date pairing** (the source itself
prints both an early and a later date together on the identical entry_id across multiple
editions -- the same signature as the page-confirmed multi-period cases above, so treated
as reliable without an individual page check): Тихоміровъ Владиміръ Михайловичъ (also
independently page-confirmed, see known_issues.md #40), Голубинъ Николай Ивановичъ,
Бершадскій Николай Александровичъ, Бѣлоусовъ Филиппъ Ивановичъ, Брыкинъ Дмитрій
Константиновичъ, Ѳедоровъ Павелъ Викторовичъ, Цалиссонъ Полина Викторовна, Пановъ
Александръ Викторовичъ.

**Still genuinely open, not resolved:**
- Поливановъ Василій Егоровичъ -- 1907-08 edition prints "1 сентября 1889 г." in full
  (not a digit slip -- entirely different day/month/year) against 15 other editions'
  "23 декабря 1868 г." Page-confirmed as printed; no multi-period phrasing on the page.
  Highest remaining risk in the whole pool.
- Савицкій Михаилъ Ивановичъ -- only 2 data points total (1906-07: "1 августа 1900 г.",
  1907-08: "1 августа 1906 г."), both confirmed accurately transcribed on their pages,
  no third data point or multi-period phrasing to resolve the conflict.

**Not yet individually page-checked** (raw pattern matches the "single-edition outlier
against a clear majority" shape confirmed six times above, but per this session's
explicit no-guessing standard these are NOT treated as resolved): Дорина Антонина
Тимоѳеевна, Барышистовъ Александръ Ивановичъ, Черниковъ Дмитрій Абрамовичъ, Пахомова
Ольга Сергѣевна, Бекефъ Альфредъ Ѳедоровичъ, Кустереръ Альбертина Альбертовна, Кузнецовъ
Владиміръ Николаевичъ, Сампелевъ Александръ Николаевичъ, Барашъ Людмила Павловна,
Солнцевъ Прохоръ Павловичъ, Петипа Марія Маріусовна, Тивольская Елена Николаевна
(genuine 4-vs-3-edition split, not a single outlier), Леонтьевъ Леонидъ Сергѣевичъ
(oscillating across editions), Иванова Надежда Сергѣевна (only 1 raw entry found under
this exact name/patronymic; the paired record producing the flagged gap not yet located).

## 2026-08-21 — Completed page-verification of remaining over-merge-risk pool (13 names + 2 previously-open cases)

Continued the #40 audit through every name left unchecked. Checked each against
its actual scanned page (not raw text) per the standing no-guessing rule.

**Six more genuine pipeline extraction bugs found and fixed** (raw said one
year, the page clearly shows another -- same failure direction as Старостина):
- Барышистовъ, Александръ Ивановичъ (`balletartists_1900-01_SP_p006__e005`):
  raw "1890" -> page reads "1899".
- Пахомова, Ольга Сергѣевна (`balletartists_1899-00_SP_p004__e001`):
  raw "1883" -> page reads "1893".
- Кустереръ, Альбертина Альбертовна (`balletartists_1904-05_SP_p002__e010`):
  raw "1883" -> page reads "1888".
- Кузнецовъ, Владиміръ Николаевичъ (`balletartists_1903-04_MSK_p006__e014`):
  raw "1893" -> page reads "1898".
- Сампелевъ, Александръ Николаевичъ (`balletartists_1896-97_MSK_p006__e024`):
  raw "1863" -> page reads "1868".
- Барашъ, Людмила Павловна (`balletartists_1904-05_SP_p000__e018`):
  raw "1901" -> page reads "1905".

All six corrected in their `.raw.json` files, `parse_and_validate.py` re-run,
`raw`/`analysis` schemas reloaded, and each fix spot-verified directly in the
DB. **Total this session: 7 confirmed extraction bugs found and fixed**
(Старостина + these 6) out of roughly 13 single-outlier cases checked --
extraction bugs turned out to be the majority outcome for this specific
shape, not the minority, which is why every one had to be checked rather than
assumed safe by pattern alone.

**Confirmed genuine one-edition print anomalies** (page-verified, matches
raw exactly, real printed error not our error): Дорина Антонина Тимоѳеевна
(1900 vs 1890), Черниковъ Дмитрій Абрамовичъ (1897 vs 1887, final edition),
Бекефи Альфредъ Ѳедоровичъ (1876 vs 1883, penultimate edition -- also
confirms Аслинъ's dual répétiteur role via an adjacent entry: "Онъ же и
репетиторъ балета съ 12 декабря 1903 г."), Солнцевъ Прохоръ Павловичъ
(1876 confirmed accurate for the one edition checked; the other two editions'
"1880" not independently checked, thin 3-point dataset), Петипа Марія
Маріусовна (1879 vs 1875, first edition only, 16-edition majority).

**Newly discovered genuinely open cases** (both sides of a discrepancy are
directly page-confirmed as accurately transcribed, with no way to determine
which is correct from internal evidence -- joining Поливановъ and Савицкій):
- Тивольская, Елена Николаевна -- "1877" confirmed printed for 4 consecutive
  editions (1890-91 through 1893-94), "1887" confirmed printed for the next 3
  (1894-95 through 1896-97). A clean, sustained switch, not a single outlier.
- Леонтьевъ, Леонидъ Сергѣевичъ -- "1903" and "1894" both confirmed printed,
  alternating across 5 editions (1903-04=1903, 1904-05=1903, 1905-06=1894,
  1906-07=1903, 1907-08=1894) with no discernible pattern.

**Found in passing, not yet fixed:** Иванова Надежда Сергѣевна's 1901-02
entry (`balletartists_1901-02_MSK_p001__e021`) has an unfixed
ordinal-misplacement bug -- `first_name='4-я'` (the ordinal),
`patronymic='Надежда'` (her actual first name), no real patronymic captured
at all. Same bug family as known_issues.md #35/#37 but a two-field-only shape
those fixes didn't cover. The identity merge itself is correct (same person,
consistent dates); this is a separate, still-open data-quality gap.

## 2026-08-21 — Correction: Иванова Надежда's "unfixed ordinal-misplacement" finding was a false alarm

```sql
SELECT entry_id, family_name, first_name, patronymic,
       family_name_clean, first_name_clean, patronymic_clean
FROM analysis.person_entry
WHERE entry_id = 'balletartists_1901-02_MSK_p001__e021';

SELECT display_name, ordinal_suffix FROM entities.person
WHERE person_id = '8bb68870-8051-4cb5-b367-25ba2a9c6215';

SELECT display_name FROM research.person
WHERE person_id = '8bb68870-8051-4cb5-b367-25ba2a9c6215';
```

Result: the raw layer (`raw.person_entry`) does still show the unfixed
fields (`family_name='Иванова'`, `first_name='4-я'`, `patronymic='Надежда'`)
-- but that's correct, `raw` is verbatim-only and never touched. The
downstream layers already clean it correctly: `analysis.person_entry`
resolves to `family_name_clean='Иванова 4-я'`, `first_name_clean='Надежда'`,
`patronymic_clean=NULL`; `entities.person` correctly captures
`ordinal_suffix='4-я'` in its own column with `display_name='Иванова 4-я,
Надежда Сергѣевна'`; `research.person.display_name` (the actually-published
value) is also correct. The only field lacking the ordinal is
`entities.person.canonical_family_name` itself ("Иванова" with no
ordinal) -- a field not used for display or publishing. Conclusion: this
was a false alarm from checking `raw` directly instead of the layer that
actually matters; there is nothing to fix here. Retracts the "found in
passing, not yet fixed" note in known_issues.md #40 / the 2026-08-21
"Completed page-verification" query_log entry.

## 2026-08-21 — Systematic check: does the #39 canonical-label bug also affect canonical_first_name/canonical_patronymic, and other entity types?

```sql
-- for each active entities.person, per entity type, compare
-- canonical_first_name/canonical_patronymic against a majority vote of
-- (first_name_clean, patronymic_clean) PAIRS from analysis.person_entry
-- among all currently-linked entries
```

Root cause found: `entities.person`'s canonical fields are computed by
`build_person_tier1()` in `pipeline/build_entities.py` using its OWN
ordinal-extraction regex (`_BARE_ORDINAL_RE`, digit-only: `^\d+-(?:й|я)`),
which is weaker than the analysis-layer regex developed later this session
during #35-#37 (`[0-9IVXІ]+-(?:й|я|е)`, handles Roman/Cyrillic-numeral
ordinals too) -- and it runs against `raw.person_entry` directly rather
than the already-cleaned `analysis.person_entry_clean` columns. Result:
`entities.person`'s canonical fields silently lag behind every ordinal/
name-splitting fix made at the analysis layer this session, on top of the
original #39-style minority-spelling problem.

Re-running `build_entities.py` fresh would fix this at the root but is
unsafe here: `build_person_tier1` mints a fresh `person_id` per `tier1_key`,
and correcting the extraction regex changes `tier1_key` for every affected
cluster -- which would orphan this session's 287+ Tier-2 merges (they
reference the old UUIDs). Used the safe, surgical approach instead:
recomputed canonical fields directly from `analysis.person_entry_clean`
via majority vote over each survivor's CURRENT linked entries (post-merge),
matching #39's proven method, split into two independent checks that never
touch `ordinal_suffix`'s presence/absence (established this session:
ordinals are legitimately season-dependent, not a spelling question):
1. comma-leak structural bug: ordinal embedded in canonical_first_name as
   "1-я, Анна" with `ordinal_suffix` NULL.
2. genuine spelling mismatch: majority-vote the (first_name_clean,
   patronymic_clean) PAIR jointly (not independently per field -- doing it
   independently produced Frankenstein combinations, e.g. "Леонтина-
   Констанция -Констанция", caught and fixed before applying).

Two bugs found and fixed in the fix script itself before applying: (a)
independent per-field voting cross-contaminating correlated fields --
switched to joint-pair voting; (b) empty vote pools (no entry has ANY
clean patronymic/first_name) left the OLD wrong value in place instead of
clearing it -- fixed to null it out. Added a safety guard after finding
one more case in TheaterSchoolStaff: never accept a fix where the proposed
first_name equals the family_name (a duplication artifact, e.g. "Сенкусъ"
family-name-only record where one of 5 entries had first_name wrongly
duplicated from family_name -- correctly left alone, still blank).

**BalletArtists**: 1003 active persons checked. 20 comma-leak fixes + 91
spelling/pairing fixes = 111 records corrected. Every spot-checked fix
matched an already-established, hand-verified correction from earlier this
session that just hadn't propagated to `entities.person` (Zambelli,
Гавликовскій, Грекова, Спрышинская, Тистрова, Пуни/Леонтина-Констанція).
Bonus find: the Пуни fix revealed two still-separate `entities.person`
records for the same person (1 entry + 4 entries, no season/city overlap,
sequential 1903-04 through 1907-08) -- merged.

**Other entity types checked**: Graduates 0/400, Administrators 19/243,
Musicians 92/984, ProductionTeam 18/236, TheaterSchoolStaff 13/266 (14
found, 1 excluded by the new guard). All 142 applied; spot-checked several
(Марквардтъ, Анцъ, Ламбинъ, Рюминъ) -- correct majority-vote spelling
corrections, mostly consistent multi-edition transliteration fixes for
foreign surnames (German/Czech names spelled differently across editions).

Re-ran `build_research_model.py` after each batch. `research.person`:
3229 -> 3228 (the one Пуни merge); `research.person_appearance` unchanged
at 21158 throughout (no data loss). Total this check: 20 + 91 + 142 = 253
canonical-field corrections + 1 additional merge, all verified propagated
to the published `research.person.display_name`.

## 2026-08-21 — Fixed the #41 root cause in pipeline code (build_entities.py), verified safe via dry run, applied to production

Addressed the "not yet done" item from #41: `build_person_tier1`'s own
weaker ordinal regex/raw-text input was still the pipeline's actual source
of truth for any future rebuild, meaning the manually-corrected data from
#41 would regress the moment `build_entities.py` was run again from
scratch. Fixed properly in `pipeline/build_entities.py`:

1. Widened `_ORDINAL_RE`/`_BARE_ORDINAL_RE` to match the analysis layer's
   regex (`[0-9IVXІ]+-(?:й|я|е)`, was digit-only `\d+-(?:й|я)`).
2. `build_person_tier1` now sources from `analysis.person_entry_clean`
   (already fully resolved by #35-#37) instead of re-deriving a second,
   weaker cleanup pass against raw text. Removed the now-dead
   `_extract_ordinal`/`_BARE_ORDINAL_RE`/`_NAME_SHAPE_RE` recovery logic
   this made unnecessary.
3. **The real reconciliation fix**: person_id continuity no longer depends
   on a recomputed `tier1_key` STRING happening to still match its old
   value (the actual root cause -- any future improvement to the matching
   logic changes affected rows' tier1_key, misses the old string, mints a
   new UUID, and orphans every merge ever made against the old one,
   including the 287+ merges this session applied directly against
   entities.person that never went through the pipeline's own Tier 2 at
   all). Reuse is now keyed on ENTRY MEMBERSHIP via `entities.person_link`,
   which is always fully resolved to each entry's current living survivor
   at the end of every prior run (`_repoint_all_superseded`'s guarantee) --
   ground truth no logic change can invalidate. Tombstoned (superseded)
   rows, which by definition have no entries in person_link any more, are
   now explicitly carried forward unchanged on every rebuild (CLAUDE.md's
   "tombstone, never delete" convention -- the new entry-based design would
   otherwise silently drop them, since nothing would reconstruct them from
   raw text).
4. Added `_refresh_canonical_fields`, called after `_repoint_all_superseded`
   in `main()`: recomputes every LIVE person's display fields from their
   FULL current entry set on every run. Needed because canonical fields
   were previously computed ONCE at Tier-1 formation and never revisited --
   confirmed as a real, separate gap this fix surfaced: a person whose
   original tiny cluster happened to include a 1-vote garbled spelling kept
   displaying it even after Tier 2 correctly merged in 17 more entries
   agreeing on the real spelling, because nothing had ever told
   entities.person to look again.

**A bug in my own fix, caught before it reached production**: the first
version of `_canonicalize_person` voted the full (family, ordinal, first,
patronymic) 4-tuple jointly. Safe for correlated variation (Пуни), but
wrong when family-name noise and patronymic noise vary independently on
different entries (Ѳедорова/Екатерина: 3/4 entries agree on the family
spelling, 2/4 agree on the patronymic spelling, but since the noisy
entries differ, all 4 full tuples were distinct and a real majority on
each half got discarded for an arbitrary tie-break -- produced "Єедорова"
i.e. a homoglyph nobody actually voted for). Fixed to vote (family,
ordinal) and (first, patronymic) as two independent pairs, matching the
method already validated by hand in the original #41 fix.

**Verification, before touching production**: dry-run against a disposable
copy of the live DB, twice (once per code fix). Confirmed via full
entry-level diff: 0 entries lost, 0 newly-appeared entries, 0 tombstones
lost or retargeted, person_link count unchanged (21174) both times. 22
entries changed person_id assignment -- every one a genuine improvement:
Tier 2's existing shared-service-start-date auto-corroboration mechanism
caught real duplicate-cluster fragmentation among records from the earlier
#41 manual fix pass (e.g. Кускова: a 2-entry isolated cluster correctly
merged into its actual 17-entry main cluster). Also ran a full
zero-mismatch sweep across the WHOLE corpus post-fix (all entity types):
0 remaining canonical-field disagreements anywhere.

Applied to production `outputs/full_run/imperial_theaters.duckdb`, then
`build_research_model.py`. Final state: `research.person` 3228 -> 3221 (the
7 new legitimate Tier-2 merges); `research.person_appearance` unchanged at
21158 (zero data loss). Spot-verified Кускова and Ѳедорова/Екатерина
Никифоровна both correct in the published `research.person.display_name`.

## 2026-08-21 — Follow-up on the 4 remaining open date conflicts (Поливановъ, Савицкій, Тивольская, Леонтьевъ)

Checked every avenue not yet tried: full raw record (all fields, not just
start_date) for each; cross-reference against all 6 entity types; existing
`entities.person_wikidata_link` rows.

```sql
SELECT pe.entry_id, pe.entity_type, pe.family_name, pe.first_name, pe.patronymic,
       pe.heading_path, pe.rank_or_title, pes.start_date_text, pes.end_date_text,
       pes.end_type, pe.page_id
FROM raw.person_entry pe
LEFT JOIN raw.person_entry_service pes ON pes.entry_id = pe.entry_id
WHERE pe.family_name LIKE ?   -- run per surname, all entity types
```

**Поливановъ, Василій Егоровичъ/Ивановичъ** — full record surfaced a new,
previously unflagged variance: the patronymic itself alternates
"Егоровичъ" (14/16 editions) vs "Ивановичъ" (1903-04, 1905-06), with
1904-05 correctly reverting to "Егоровичъ" in between. User flagged this
as a possible second-person indicator; checked directly against both
scanned pages (`ForUpload_1903-04_Spisok_BalletArtistsMoscow.pdf` p.111
#52, `ForUpload_1905-06_Spisok_BalletArtistsMoscow.pdf` p.55 #52) --
confirmed genuinely printed both times, not an extraction error. But the
start date is IDENTICAL ("23 декабря 1868") across all 17 editions
regardless of which patronymic is printed, and the entry's roster position
(#52), role, and credits pattern stay continuous with no "Оставилъ
службу" note anywhere -- two different real people would not plausibly
alternate one numbered roster slot year-to-year sharing an identical
tenure-start date. Read as a recurring compositor's slip (substituting the
far more common patronymic root "Иванович" for the rarer "Егорович"),
independent of the separate 1907-08 date anomaly (whose own patronymic is
normal). Not a second person; not an over-merge.

No cross-reference in any other entity type (18/18 raw `Поливанов%`
entries are BalletArtists only). No Wikidata link. The core 1868-vs-1889
date conflict remains genuinely unresolved -- majority (15/16
matching-patronymic entries) favors 1868; 1889 (1907-08 only) stays an
unexplained single-edition anomaly.

**Савицкій, Михаилъ Ивановичъ** — found real corroborating evidence:
`graduates_1905-06_p001__e011`, "Савицкій, Михаилъ", heading "Балетное
отдѣленіе / Ученики" (ballet division, male pupils), 1905-06. He was
still a student as of 1905-06 -- consistent with "1 августа 1906 г." (the
1907-08 BalletArtists entry) being his real company-artist start date
right after graduating, and "1 августа 1900 г." (the 1906-07 entry) more
likely reflecting when he entered the SCHOOL rather than the company --
the same school-entry-vs-company-appointment distinction already
established this session (Дмитриева, Голубинъ). Resolved: one continuous
person, not an over-merge.

**Тивольская, Елена Николаевна** and **Леонтьевъ, Леонидъ Сергѣевичъ** --
no cross-reference found in any other entity type, no Wikidata link. No
new evidence surfaced. Both remain genuinely open exactly as documented in
known_issues.md #40.

## 2026-08-21 — Name-field audit extended to the other 5 entity types

Checked every known BalletArtists name-field bug shape (Patterns B/C/D/E,
Latin-homoglyph corruption) against Musicians, Administrators,
ProductionTeam, TheaterSchoolStaff, Graduates directly against
`raw.person_entry`.

```sql
-- per pattern, per entity type
SELECT count(*) FROM raw.person_entry WHERE entity_type=? AND <pattern regex>
```

Result: Pattern B, Pattern E, and Latin-homoglyph corruption are
genuinely absent everywhere outside BalletArtists (confirmed zero rows,
including a broadened "any Latin letter in family/first/patronymic"
sweep — not just unverified as the original comments in build_duckdb.py
said, actually zero). But Pattern C (first_name = "FirstName Patronymic"
run together, patronymic blank) is real and substantial elsewhere: 149
rows in Musicians, 11 in Administrators, 84 in TheaterSchoolStaff (244
total, >4x the original 54-row BalletArtists count) — the code's own
comment had already flagged this exact gap ("the same shape exists in
Musicians/TheaterSchoolStaff/Administrators too, not fixed here"), just
never acted on. Pattern D (ordinal landed in patronymic) found once more,
in Musicians: the Эйхенвальдъ sisters (Ида/Надежда), same shape as the
BalletArtists Мендесъ sisters, confirmed via the raw corpus (their own
other rows spell the ordinal split out unambiguously, no page check
needed). ProductionTeam and Graduates confirmed genuinely clean on every
pattern checked.

Extended `pipeline/build_duckdb.py`'s Pattern C and Pattern D
`entity_type` scoping from BalletArtists-only to
`('BalletArtists', 'Musicians', 'Administrators', 'TheaterSchoolStaff')`
in all 4 affected CASE branches (family_name_clean and patronymic_clean
for Pattern D; first_name_clean and patronymic_clean for Pattern C).
Rebuilt `analysis.person_entry` — verified 0 remaining unfixed Pattern C
rows in all 3 entity types, Эйхенвальдъ's 1901-02 row now correctly reads
family="Эйхенвальдъ 1-я"/first="Ида"/patronymic=NULL, and (bonus) an
Administrators row now correctly reads "Дягилевъ, Сергѣй, Павловичъ" —
Sergei Diaghilev.

Propagated via the now-safe `build_entities.py` (dry-run verified first,
per established practice): 0 entries lost, 0 tombstones lost, 2 new
legitimate Tier-2 merges (Гордонъ Александръ Бернгардовичъ in Musicians,
Миронниковъ Александръ Васильевичъ in TheaterSchoolStaff — both
previously-fragmented clusters now correctly recognized once their name
fields were clean). Applied to production, then `build_research_model.py`:
`research.person` 3221 -> 3219; `research.person_appearance` unchanged at
21158 (zero data loss). Spot-verified Diaghilev's entry in the published
`research.person` — noticed he still exists as 2 separate person records
(likely two distinct administrative appointments, or a real un-merged
duplicate) — flagged for a future pass, out of scope for this one.

## 2026-08-21 — Duplicate-person sweep across the whole corpus (all entity types)

Investigated after noticing Diaghilev ("Дягилевъ, Сергѣй Павловичъ") sitting
as two separate `entities.person` records post-#43's Pattern C fix.

```sql
-- initial scope check: exact tier1_key match (family+ordinal+first+patronymic)
SELECT person_id, tier1_key, display_name FROM entities.person
WHERE superseded_by_person_id IS NULL AND tier1_key IS NOT NULL
```

First pass (tier1_key exact match, including ordinal): 185 duplicate pairs.
RG corrected this immediately -- ordinal is a per-season positional label,
not a stable identifier (the same fact behind #38 Pass 2's 229 merges), so
requiring it to match too structurally undercounts. Redid without ordinal
in the key (family+first+patronymic only): **278 duplicate-name groups,
294 extra person records** -- 240 within a single entity type, 38 spanning
more than one.

RG then specified the exact standard: two records are the same person when
corroborated by BOTH the same names AND the same start date; anything
close-but-not-exact needs individual care, not an automatic decision.
Implemented as a new pipeline function, `merge_duplicate_persons()` in
`pipeline/build_entities.py`, with three required gates: (1) entity_type
matches across every member -- a name shared across different roles is
weaker evidence than within one, left for human review; (2) no season/city
overlap between any two members -- the same conflict check #38 used
throughout, since two people simultaneously listed under the same name in
the same season/city are a real conflict, not an ordinal variant; (3) at
least one exact shared `start_date_undate` somewhere in the group -- the
same positive-corroboration bar Tier 2's `apply_tenure_corroboration`
already requires ('shared_start_date', not merely absence of conflict).
Wired into `main()`'s existing merge loop, looped to a fixed point the same
way Tier 2 is.

Dry-run verified against a disposable DB copy before touching production:
converged after 2 iterations, 233 duplicate records merged into 222
survivors, 0 entries lost, 0 tombstones lost, person_link count unchanged
(21174). 38 cross-entity-type + 8 season/city-overlap + 10 no-shared-date
groups correctly held back -- spot-checked several of each: the held-back
groups are genuinely ambiguous (e.g. "Конскій, Григорій Яковлевичъ" with
non-matching dates 10 years apart on the same day/month -- plausibly a
digit transcription slip, not confirmed; several cross-entity-type pairs
that plausibly ARE the same person in two roles with matching dates, e.g.
"Мендесъ, Іосифъ" in BalletArtists+TheaterSchoolStaff sharing an exact
date -- correctly flagged for deliberate review, not auto-merged, since
matching entity_type is a hard requirement).

Applied to production: `entities.person` live count 3225 -> 2992 (233
duplicates resolved), then `build_research_model.py`:
`research.person` 3219 -> 2986; `research.person_appearance` unchanged at
21158 (zero data loss). Diaghilev confirmed as a single record in the
published data.

## 2026-08-24 — Held-back "cross-entity-type" duplicate review: Graduates-to-career-role season/date detail

```sql
SELECT pe.entity_type, pe.family_name, pe.first_name, pe.patronymic,
       sp.season, sp.city, pes.start_date_text, pes.end_date_text, pes.end_type
FROM raw.person_entry pe
JOIN raw.source_pages sp ON sp.page_id = pe.page_id
LEFT JOIN raw.person_entry_service pes ON pes.entry_id = pe.entry_id
WHERE (pe.family_name LIKE 'Смирнов%' AND pe.first_name LIKE 'Викт%')
   OR (pe.family_name LIKE 'Иванов%' AND pe.first_name LIKE 'Васил%' AND pe.entity_type != 'BalletArtists')
   OR (pe.family_name LIKE 'Иванов%' AND pe.first_name LIKE 'Васил%' AND pe.patronymic LIKE 'Ерем%')
   OR (pe.family_name LIKE 'Павлова%' AND pe.first_name LIKE 'Евген%')
   OR (pe.family_name LIKE 'Кочетовск%' AND pe.first_name LIKE 'Екатер%')
   OR (pe.family_name LIKE 'Иванова%' AND pe.first_name LIKE 'Надежд%')
   OR (pe.family_name LIKE 'Павлова%' AND pe.first_name LIKE 'Анна%')
   OR (pe.family_name LIKE 'Уракова%' AND pe.first_name LIKE 'Анна%')
ORDER BY pe.family_name, pe.first_name, sp.season;
```

Result: for all 7 cases, the Graduates-entity edition (e.g. Иванова Надежда
'1899-00', Ивановъ Василій '1895-96', Кочетовская Екатерина '1890-91',
Павлова Анна '1898-99', Павлова Евгенія '1900-01', Смирновъ Викторъ
'1904-05', Уракова Анна '1890-91') is the same academic year whose
end-of-year the printed career start date falls in or immediately after
(e.g. Кочетовская: Graduates '1890-91' -> BalletArtists start "1 сентября
1891 г."; Уракова: Graduates '1890-91' -> start "1 іюня 1891 г."; Павлова
Евгенія: Graduates '1900-01' -> start "1 сентября 1901 г."). No
counterexamples across the 7. Also surfaced a data-quality issue: 2
Graduates rows (Кочетовская, Уракова) have first_name and patronymic
concatenated with no space ("ЕкатеринаВладиміровна",
"АннаПетровна") -- extraction bug, not yet logged as a known issue.

## 2026-08-24 — Степанова, Лидія Петровна: frequency of May 1 vs June 1 1898 start date

```sql
SELECT pe.entity_type, pe.family_name, pe.first_name, pe.patronymic,
       sp.season, sp.city, pes.start_date_text
FROM raw.person_entry pe
JOIN raw.source_pages sp ON sp.page_id = pe.page_id
LEFT JOIN raw.person_entry_service pes ON pes.entry_id = pe.entry_id
WHERE pe.family_name LIKE 'Степанов%' AND pe.first_name LIKE 'Лид%'
ORDER BY sp.season;
```

Result: the Graduates entry (1897-98 edition) reads "съ 1-го мая 1898
года" (May 1, appears once). Every one of the 9 BalletArtists printings
(1898-99 through 1907-08) reads "1 іюня 1898 г." / "съ 1 іюня 1898 г."
(June 1) -- unanimous, 9/9. May 1 appears nowhere in the professional
record; June 1 appears nowhere in the Graduates record.

## 2026-08-24 — Погожевъ / Пчельниковъ: name consistency and Administrators/TheaterSchoolStaff timing overlap

```sql
SELECT pe.entity_type, pe.family_name, pe.first_name, pe.patronymic,
       sp.season, sp.city, pes.start_date_text, pes.end_date_text
FROM raw.person_entry pe
JOIN raw.source_pages sp ON sp.page_id = pe.page_id
LEFT JOIN raw.person_entry_service pes ON pes.entry_id = pe.entry_id
WHERE pe.family_name LIKE 'Погожев%' OR pe.family_name LIKE 'Пчельников%'
ORDER BY pe.family_name, sp.season;
```

Result: Погожевъ = "Владиміръ Петровичъ" (one spelling variant "Владимиръ"
in 1907-08) in both entity types throughout, no second name variant.
Пчельниковъ = "Павелъ Михайловичъ" identically in both entity types
throughout. For both, the TheaterSchoolStaff (honorary council) rows run
concurrently with the Administrators rows across the same editions, not
sequentially -- e.g. Погожевъ's Administrators tenure is "11 мая 1882" to
"24 февраля 1900", and his TheaterSchoolStaff rows already appear from
1890-91 onward, i.e. the two roles overlap in time rather than one
succeeding the other.

## 2026-08-24 — Wired docs/ballet_graduates_tenure.csv's hand-verified dates into the pipeline (issue #45)

```sql
-- verification query, run against the rebuilt outputs/full_run/imperial_theaters.duckdb
SELECT count(*) FROM raw.person_entry;                    -- 21174, unchanged
SELECT count(*) FROM research.person_appearance;           -- 21158, unchanged
SELECT count(*) FROM entities.person WHERE superseded_by_person_id IS NULL;  -- 2965 (post date-fix), then 2961 (post 4 hand-merges)
SELECT count(*) FROM research.person;                       -- 2955 (post 4 hand-merges, from 2959)
```

Result: added `pipeline/parse_and_validate.py`'s `_repair_graduates_tenure()`,
sourced from `docs/ballet_graduates_tenure.csv` (moved there from
`outputs/full_run/`, git-tracked now). Backfilled 136 previously-missing
`start_date_text`/`start_date_undate` values into
`raw.person_entry_service` for Graduates entries whose own row had no
date but the page's hand-verified trailing sentence did. Verified via
dry-run diff first (0 entries lost/gained in `raw.person_entry`, exactly
136 new `person_entry_service` rows, all under `graduates_*` page_ids)
before applying to production, rebuilding `entities`/`research`, and
re-verifying. `research.person_appearance` stayed at 21158 throughout
every step (zero data loss).

Then hand-merged 4 of the 7 "Graduates-timing" held-back duplicate cases
now that they have hard exact-date corroboration matching their
BalletArtists record precisely: Кочетовская Екатерина Владиміровна
(1891-09-01), Уракова Анна Петровна (1891-06-01), Ивановъ Василій
Еремѣевичъ (1896-09-01), Павлова Анна Матвѣевна (1899-06-01). Confirmed
these do NOT auto-merge via `merge_duplicate_persons()` even with the
date fix -- its entity-type-intersection gate correctly refuses to
bridge a Graduates-only record and a BalletArtists-only record, since
those two entity_type sets are disjoint by construction for exactly this
kind of case. That's appropriate caution, not a bug; individual merges
still need a human decision, same pattern as issue #38.

## 2026-08-24 — Executed the 3 queued individual merges (Степанова, Погожевъ, Пчельниковъ)

```sql
SELECT count(*) FROM entities.person WHERE superseded_by_person_id IS NULL;  -- 2961 -> 2958
SELECT count(*) FROM research.person;   -- 2955 -> 2952
SELECT count(*) FROM research.person_appearance;  -- 21158, unchanged
```

Result: Степанова Лидія Петровна (Graduates `1898-05-01` + BalletArtists
9-edition `1898-06-01`) merged into one record (10 entries,
`{Graduates, BalletArtists}`). Погожевъ and Пчельниковъ each turned out
to already be partially auto-merged by this run's `merge_duplicate_persons()`
(a 39/40-entry `{Administrators, TheaterSchoolStaff}` combo record already
existed) -- what remained was a small 4-entry `TheaterSchoolStaff`-only
split per person, all 4 entries reading "Почетные члены конференціи"
under the same institution, with `first_name` holding the unsplit
"Владиміръ Петровичъ"/"Павелъ Михайловичъ" string (the same
concatenated-name extraction pattern documented elsewhere for Graduates)
-- confirmed same person/role by heading_path + institution match, merged
the residual split in. Both survivors now show 43/44 entries under
`{Administrators, TheaterSchoolStaff}`. Dry-run verified first (exactly
-3 live persons, 0 change to `raw.person_entry`); applied to production,
rebuilt `research` (`research.person` 2955 -> 2952,
`research.person_appearance` unchanged at 21158).

## 2026-08-24 — Season/city-overlap held-back group (9 groups) individually reviewed and resolved

```sql
SELECT count(*) FROM entities.person WHERE superseded_by_person_id IS NULL;  -- 2958 -> 2948 across all merges below
SELECT count(*) FROM research.person_appearance;  -- 21158, unchanged throughout
```

Result: pulled all 9 remaining season/city-overlap groups by replicating
`merge_duplicate_persons()`'s exact query/gate logic against the live
production DB. Found two distinct patterns:

- **5 groups were the same name-concatenation bug already fixed for
  Погожевъ/Пчельниковъ** (first+patronymic run together, unsplit, on a
  handful of editions): Писнячевскій Владиміръ Порфирьевичъ, Фарскій
  Альбертъ Карловичъ, Золотаренко Павелъ Петровичъ (2 fragments),
  Дебогорій-Мокріевичъ Порфирій Андреевичъ, and one half of a 3-way
  Франке Ѳедоръ Юліевичъ group (the clarinet variant; the "Франке 2-й"
  waldhorn record in the same group is a genuinely different sibling,
  left separate). All 5 merged.
- **4 groups were one real person listed twice per edition** (an honors
  list + a post list, or similar), not two colleagues: Ивановъ Левъ
  Ивановичъ (the historical choreographer, "second ballet master" —
  identical role text and date, split only by whether "1-й" printed),
  Рюминъ Иванъ Ивановичъ (senior court official/school director,
  identical rank text and date across heavy season overlap), Павловъ
  Михаилъ Львовичъ (single stray entry matching the main record's date
  exactly), and Кулле Альфредъ Ѳедоровичъ. All merged after RG confirmed.

**Кулле specifically was checked against the actual scans before
merging** (RG asked to see the primary source) — downloaded the
iCloud-stub PDF (`ForUpload_1902-03_Spisok_OrchestraSP.pdf`) and
rendered pp. 83 and 86 directly. Confirmed a reciprocal transfer note,
not a conflict: p.86 (Mikhailovsky Theater orchestra roster) reads
"Кулле 2-й, Альфредъ Федоровичъ ... Тромбонъ. Переведенъ въ оркестръ
Маріинскаго театра съ 1 сентября 1902 г." (transferred TO the Mariinsky
orchestra); p.83 (main SP orchestra roster) reads "Кулле, Альфредъ
Федоровичъ ... Тромбонъ. Переведенъ изъ оркестра Михайловскаго театра
съ 1 сентября 1902 г." (transferred FROM the Mikhailovsky orchestra) --
same person, same trombone, same 1891 start date, both rosters citing
each other for the same 1902 transfer date. The "Управляющій Училищемъ"
(School Director) heading_path the database showed for that entry does
not appear anywhere on the actual page -- confirmed as a stray
extraction misattachment, unrelated to Kulle.

All 10 merges applied to production (dry-run verified first each time,
0 change to `raw.person_entry`/`raw.person_entry_service`), `research`
rebuilt after each batch. `research.person_appearance` unchanged at
21158 throughout every step. `entities.person` live count: 2958 -> 2948
across this whole review (9 real merges -- Золотаренко absorbed 2
fragments into 1 survivor, counted as -2 alone).

## 2026-08-24 — No-shared-date held-back group (10 groups) reviewed; 6 merged, 4 deferred

```sql
SELECT count(*) FROM entities.person WHERE superseded_by_person_id IS NULL;  -- 2948 -> 2942
SELECT count(*) FROM research.person;  -- 2942 -> 2936
SELECT count(*) FROM research.person_appearance;  -- 21158, unchanged
```

Result: re-derived the current no-shared-date group (10, not the earlier
"8" estimate) by replicating `merge_duplicate_persons()`'s gates against
production. Found:

- **5 more instances of the Погожевъ/Пчельниковъ name-concatenation
  bug** (first+patronymic unsplit on specific editions), all under the
  identical "Почетные члены конференціи" (honorary council) heading:
  Григоровичъ Дмитрій Васильевичъ, Климченко Андроникъ Михайловичъ,
  Маннь Ипполитъ Александровичъ, Потѣхинъ Алексѣй Антиповичъ, Іогансонъ
  Христіанъ Петровичъ. 11th/12th/13th/14th/15th confirmed instance of
  this same bug this session.
- **Конскій, Григорій Яковлевичъ** (Moscow violinist) — checked the
  actual scans (`ForUpload_1890-91_Spisok_OrchestraMoscow.pdf` p.107,
  `ForUpload_1891-92_Spisok_OrchestraMoscow.pdf` p.85): both genuinely
  print a different decade for his start date ("28 іюля 1862" vs "28
  іюля 1852"), consecutive seasons, same city/instrument/role, and the
  1891-92 printing is explicitly his closing record ("Оставилъ службу 1
  августа 1892 г."). Read as one person's final two seasons with a
  compositor's digit slip in one edition, same shape as the already-
  documented Мосолова 4-day variant (#34, 7th addendum) -- both
  printings genuine, not an OCR error.
- **4 groups left unmerged, added to the to-do list**: Васильева Анна,
  Ильина Елена, Новикова Екатерина, Симонова Антонина (all Graduates,
  no patronymic printed) -- different seasons AND different exact
  dates for each pair, no positive evidence pointing to one person over
  two different graduates who happen to share a common name. Left open
  rather than guessed at.

All 6 merges dry-run verified first (0 change to `raw.person_entry`),
applied to production, `research` rebuilt. `research.person_appearance`
unchanged at 21158. This closes out the entire #44 held-back review
(cross-entity-type, season/city-overlap, and no-shared-date groups all
now individually adjudicated) except the 4 deferred Graduates pairs.

## 2026-08-24 — institution/department accuracy audit: 2 confirmed extraction misattachments fixed

```sql
SELECT entity_type, count(DISTINCT institution) n_institutions FROM research.person_appearance GROUP BY entity_type;
SELECT institution, count(*) FROM research.person_appearance WHERE entity_type='BalletArtists' GROUP BY institution ORDER BY 2 DESC;
SELECT institution, count(*) FROM research.person_appearance WHERE entity_type='ProductionTeam' GROUP BY institution ORDER BY 2 DESC;
```

Result: surveying `institution` (the closest thing to a department/theater
field) across entity types found it's structurally noisy -- 18-69 distinct
values per entity type, mixing document titles, bare city names, real
theater names (with spelling drift), and in two cases outright misattached
text. Both checked directly against the scans:

1. **25 BalletArtists rows** (`balletartists_1903-04_MSK_p002`, all
   entries) had a repertoire credit-list ("Золотая рыбка (постельница —
   7); Донъ-Кихотъ Ламанчскій...") sitting in `institution` instead of a
   real theater/header value. Confirmed against
   `ForUpload_1903-04_Spisok_BalletArtistsMoscow.pdf` p.106: it's the tail
   half of Другашева, Марія's own credit_summary_text (entry 25 on the
   *previous* page, `balletartists_1903-04_MSK_p001`), cut off mid-sentence
   by the page break and wrongly read as this page's header. Fixed:
   appended the missing text to her own credit_summary_text; blanked
   `institution` on the 25 entries it had contaminated (no real header text
   exists on that page in the scan -- verified, not guessed).
2. **1 ProductionTeam row** (`productionteam_1895-96_p001__e007`,
   Ковалевскій, Ѳедоръ Ѳедоровичъ) had his own name+date duplicated into
   both `institution` and `heading_path`. Confirmed against
   `ForUpload_1895-96_Spisok_ProductionTeam.pdf` p.108: he's listed under
   "Михайловскій театръ. / Помощникъ машиниста." directly below Ашитковъ
   (that theater's machinist). Fixed both fields to the scan-verified text.

Implemented in `pipeline/parse_and_validate.py`'s new
`_repair_misattachments()` (a documented, page-keyed patch list --
`_MISATTACHMENT_FIXES`), dry-run verified first (0 change to row counts,
exactly 3 entries touched across the 2 pages), applied to production,
rebuilt `analysis`/`research`. `research.person`/`research.person_appearance`
counts unchanged (2936 / 21158) -- these are text-only corrections, no
entity/date changes.

## 2026-08-24 — Отдѣль -> Отдѣлъ spelling fix (ProductionTeam department heading)

```sql
SELECT entity_type, heading_path, count(*) FROM raw.person_entry
WHERE heading_path LIKE '%Отдѣль%' GROUP BY 1,2 ORDER BY 3 DESC;
```

Result: 130 ProductionTeam rows across 6 seasons (1890-91, 1892-93,
1893-94, 1896-97, 1897-98, 1903-04), all under "Отдѣль декораціонный"
(and its sub-roles: Декораторы, Помощники декораторовъ, Ученики
декораціонной живописи) -- a one-character extraction misreading
(soft sign ь for hard sign ъ). Confirmed against the scan
(`ForUpload_1890-91_Spisok_ProductionTeam.pdf` p.111): printed as
"Отдѣлъ декораціонный." -- genuine typo, not a printed variant.
"Отдѣль" never appears in `institution` and never as any other phrase,
so a corpus-wide word-boundary fix was safe.

Implemented as `pipeline/parse_and_validate.py`'s new
`_repair_department_spelling()` (`_SOFT_SIGN_TYPO_RE`), applied to every
roster page. Dry-run verified first (0 row-count change, exactly 130
entries fixed across the 6 expected pages, 0 remaining "Отдѣль"
anywhere afterward); applied to production, rebuilt `analysis`/
`research`. `research.person`/`research.person_appearance` unchanged
(2936 / 21158) -- text-only fix.

## 2026-08-24 — Venue accuracy audit (events): theater_canonical gap found and fixed

```sql
SELECT count(*), count(theater_canonical), count(*) FILTER (theater_canonical IS NULL) FROM analysis.event_entry;
SELECT theater, count(*) FROM analysis.event_entry WHERE theater_canonical IS NULL GROUP BY theater ORDER BY 2 DESC;
```

Result: unlike the person side, event venue data is largely clean --
27,930/27,930 events had a `theater` value and only 158 (0.57%) failed
to resolve to `theater_canonical`. Split those 158 into two genuinely
different situations by reading the actual repertoire table scans:

- **88 rows are legitimate**: whole-city (or whole-table) dark days
  where every theater in the group shows "—" that day, so there's no
  single theater to name (`theater` holds a group label like
  "С.-Петербургскіе театры"/"Московскіе театры", or, when literally
  every theater on the page was dark, the date column's own header text
  "Мѣсяцъ, день и число" leaked in). Confirmed against
  `ForUpload_1890-91_Repertoire.pdf` p.8-9 and
  `ForUpload_1892-93_Repertoire.pdf` p.2-3. `theater_canonical=NULL` is
  correct for these, not a bug.
- **70 rows were a real classifier gap**: a single specific theater dark
  while its city's other venues still had shows, written as a compound
  "[city group]. [theater]" string ("Московскіе театры. Большой",
  "С.-Петербургскіе театры. Маріинскій", etc.) that the classifier's
  `starts_with()` check didn't catch (the theater name is a suffix, not
  a prefix). Confirmed against `ForUpload_1896-97_Repertoire.pdf`
  p.2-3: Большой genuinely dark that week while Малый has shows.

Fixed by switching `theater_canonical`'s CASE logic in
`pipeline/build_duckdb.py` from `starts_with()` to `contains()`.
Verified before applying that this doesn't introduce false positives:
checked every distinct raw `theater` value's classification under both
old and new logic -- only the 5 expected compound strings changed,
nothing else. Applied to production; also fixed a downstream artifact:
the completeness-reconciliation "not_captured" placeholder count
dropped 4050 -> 4025, since those 70 events were previously
double-counted (once as a mislabeled real event, once as a phantom
"missing" placeholder for the same date+theater cell).
`research.event` 27930 -> 27905 rows (the 25 now-redundant placeholders
removed); `research.performance`/`research.person_appearance` unchanged
(24894 / 21158).

## 2026-08-24 — Repertoire missing-pages audit: 1895-96 year-misread fixed, 1890-91 confirmed missing pages found

```sql
SELECT ee.date_undate FROM raw.event_entry ee JOIN raw.source_pages sp ON sp.page_id=ee.page_id
WHERE sp.entity_type='Repertoire' AND sp.season=? ORDER BY 1;  -- run per season, checked for gaps >1 day
```

Result: RG asked to check for one-off missing repertoire pages within each
season (distinct from the whole-season completeness already checked).
Used date-continuity as a proxy (a printed daily table should have no gap
>1-2 days except known closures) across all 18 seasons, then verified the
concerning gaps against the actual scans:

- **Confirmed 108 rows correctly recurring gaps are NOT missing pages**:
  the ~7-9 day gap every March/April matches Orthodox Holy Week theater
  closures (a real historical practice); the ~3 day gap every Dec 22-26
  matches Christmas closures. Recurs in nearly every season -- expected,
  not a data problem.
- **1895-96's apparent 596-day gap was a year-misread, not a missing
  page**: `repertoire_1895-96_p005` (108 sessions) read "1893 г." where
  the scan clearly shows "1895 г." Confirmed corpus-wide this is the
  *only* Repertoire page with this shape of season/year mismatch (no
  general rule needed). Fixed via `pipeline/parse_and_validate.py`'s new
  `_REPERTOIRE_YEAR_FIXES` (page-keyed, same pattern as the earlier
  misattachment fixes). Dry-run verified (0 row-count change, exactly
  108 sessions fixed); applied to production. Also re-ran
  `validate_performance_dates.py` afterward, since `research.event.date`
  prefers its `corrected_date_undate` over the raw date via COALESCE --
  without the refresh, the stale day-of-week "correction" (computed back
  when the year was still wrong) would have silently overridden the fix.
  `analysis.event_entry_date_check`: corrected 2102->1994, verified
  20336->20444 (exactly the 108 rows moving from "needed correction" to
  "verified"). `research.event`/`research.performance`/
  `research.person_appearance` unchanged (27905 / 24894 / 21158).
- **1890-91 has a genuinely missing page-pair**: the book's own printed
  page numbers jump from 7 straight to 10 between
  `ForUpload_1890-91_Repertoire_002.jpg` and `_003.jpg` -- pages 8-9
  (~Oct 12-31, 1890) were never scanned. Confirmed visually, not yet
  reflected anywhere in the data (there's no fix for a page that was
  never captured -- this is a scanning-source gap, logged for RG's
  awareness, not a pipeline bug).
- **1907-08's 20-day August gap is unresolved**: `repertoire_1907-08_p000`
  contains two non-adjacent date ranges (Aug 1-9 and Aug 30-31) in the
  same extracted page, inconsistent with the single continuous date
  range ("30 августа...9 сентября") printed on the page image reviewed
  so far -- needs further investigation before concluding whether pages
  are missing or the extraction duplicated/misattached a date range.

## 2026-08-24 — Two more Repertoire month-mislabel bugs found and fixed (1907-08, 1902-03)

```sql
-- corpus-wide scan for the general bug shape: a page where day-of-month
-- decreases by >3 while month_text stays identical (signature of a
-- missed month-rollover or a wrong starting month)
```

Result: investigating 1907-08's 20-day August gap (flagged in the prior
entry as unresolved) found it wasn't a missing page at all --
`repertoire_1907-08_p000` genuinely spans Aug 30-Sep 9 per the scan
("30 августа. ... 9 сентября."), but the model never advanced
`month_text` past "Августъ" once day rolled over from 31 to 1, so days
1-9 (really September) computed as bogus August dates. A corpus-wide
scan for this exact shape (day decreases, month_text unchanged) found 9
candidate pages total; one more, `repertoire_1902-03_p008`, matched and
was confirmed against its scan (`ForUpload_1902-03_Repertoire_008.jpg`):
that page spans Oct 22-Nov 3, but the model labeled every row "Ноябрь"
from the start (likely misled by this one page's own running header
printing the two months in reverse order, "22 ноября...3 октября.",
unlike every other page's start-first convention) -- the day sequence
itself is unambiguous once read directly.

Fixed via `pipeline/parse_and_validate.py`'s new
`_REPERTOIRE_MONTH_FIXES` (page + 1-based index range, same shape as the
year-fix table). Dry-run verified (0 row-count change, 29 sessions fixed
on each page, both resolving to clean continuous date ranges); applied
to production, rebuilt `analysis` (`not_captured` completeness gaps
4025 -> 3911) and re-ran `validate_performance_dates.py` (this field
also feeds `research.event.date` via COALESCE, same lesson as the
1895-96 fix).

**The remaining 6 candidate pages from the corpus-wide scan do NOT match
this confirmed shape** (checked each individually) and are NOT fixed:
`repertoire_1890-91_p000` and `repertoire_1906-07_p048`/
`repertoire_1907-08_p048` are false positives (the day sequence in
session-list order doesn't actually decrease when read correctly);
`repertoire_1897-98_p010`, `repertoire_1899-00_p037`,
`repertoire_1904-05_p011`, `repertoire_1906-07_p037` show a different,
smaller-scale pattern (an isolated single-digit day misread, e.g. "23"
for "29") that needs individual scan verification before any fix, not
grouped in with the month-rollover cases.

## 2026-08-24 — Systematic missing-pages check completed across all 18 Repertoire seasons

Result: re-ran the date-continuity gap scan after the 1895-96/1902-03/
1907-08/1896-97 fixes above, this time filtering to gaps >10 days (small
1-3 day gaps are the already-confirmed-legitimate Christmas/Holy Week
closures, checked earlier). Down to 4 remaining large gaps; resolved all 4:

- **1890-91, Oct 12-31 (20 days): genuinely missing pages.** The book's
  own printed page numbers jump from 7 straight to 10
  (`ForUpload_1890-91_Repertoire_002.jpg` vs `_003.jpg`) -- pages 8-9
  were never scanned. A real gap in the source, not fixable from what
  we have.
- **1894-95, Oct 24-Dec 31 (69 days): not a bug at all.** The actual
  printed page (`ForUpload_1894-95_Repertoire_002.jpg`) itself jumps
  directly from "19 Октября" to "1 Января" with no page break in
  between -- almost certainly the Imperial theaters' closure for
  Alexander III's death (Oct 20, 1894 O.S.) and the national mourning
  period that followed; the yearbook's own compilers omitted the closure
  from the printed table rather than printing ~70 blank rows. Correctly
  reflects the primary source; nothing to fix.
- **1890-91, May 16-25 (10 days): unresolved, low-stakes.** The physical
  page (`ForUpload_1890-91_Repertoire_012.jpg`) ends cleanly with a
  decorative closing flourish after May 15, but the raw JSON for that
  same page also has 3 more rows dated "26 —" (all dark/no-performance,
  no works) that don't correspond to anything visible on the page.
  Likely a minor phantom-row artifact; since it represents no lost
  performance data (marked dark either way) this was left as a flagged
  oddity, not fixed.
- **1896-97, Sep 1-11: fixed** (see prior entry -- `month_text` bled
  a full date phrase instead of just the month, collapsing 50 rows onto
  a single bogus date).

**Final state**: of the 18 seasons, 17 have clean, fully-accounted-for
date coverage (allowing for real Christmas/Holy Week closures); 1890-91
has one confirmed physical scanning gap (pages 8-9, ~20 days) that
cannot be recovered without a better scan.

## 2026-08-24 — 1890-91_p012's "26 —" rows confirmed as model fabrication, dropped

Result: RG pushed back on characterizing this as "not worth digging into"
-- investigated properly. Downloaded and rendered the actual PDF page
directly at 400dpi (`ForUpload_1890-91_Repertoire.pdf`, page index 12,
its last page -- the file has exactly 13 pages, no page 13 to have
supplied more content). The rendering confirms the page ends cleanly
with a decorative closing flourish after "15 Среда" (May 15), nothing
else printed below it except faint bleed-through from the reverse side
of the physical page. The 3 sessions dated "26 —" (Маріинскій,
Александринскій, Михайловскій, all `is_dark`, no works/receipts) don't
correspond to anything on this page or any other page in the file --
confirmed fabricated by the model, not a misattachment or mislabeling
like the other Repertoire date bugs found today. Since they carry no
real content either way, dropping them loses nothing; there's no
correct date to move them to because they were never real.

Implemented as `pipeline/parse_and_validate.py`'s new
`_REPERTOIRE_FABRICATED_SESSIONS` (page-keyed set of 1-based session
indices to drop), applied inside `_repair_repertoire`. Dry-run verified
first (event_entry 23880 -> 23877, exactly -3, all other counts
unchanged); applied to production, rebuilt `analysis`/`research` and
re-ran `validate_performance_dates.py`.

## 2026-08-25 — repertoire_1897-98_p010: full session-by-session reconstruction of the Маріинскій date-drift

```sql
SELECT ee.event_id, ee.date_text, ee.month_text, ee.theater,
       list(w.performance_title) as works, ee.receipts_text
FROM raw.event_entry ee
LEFT JOIN raw.event_entry_performance w ON w.event_id = ee.event_id
WHERE ee.page_id = 'repertoire_1897-98_p010'
GROUP BY ee.event_id, ee.date_text, ee.month_text, ee.theater, ee.receipts_text
ORDER BY ee.event_id
```

Result: 95 rows retrieved and cross-checked line-by-line against a 400dpi scan
of the actual printed page (`ForUpload_1897-98_Repertoire.pdf`, page index 10).
Confirmed: on real date "22 Воскресенье" the Маріинскій театръ printed TWO
sessions (утро/вечеръ — a benefit matinee, then "A basso Porto" + Walküre
3rd act in the evening, 5785 р. 10 к.). The extraction treated the evening
session as belonging to a new date "23 Понедѣльникъ" instead of recognizing
it as day 22's second sitting, which cascades a +1 date offset through every
subsequent Маріинскій-column row (event_ids s051 through s076, i.e. real
days 22(вечеръ)–27 all mislabeled one day late) while the Александринскій/
Михайловскій/Большой/Малый columns on the same rows are NOT affected and stay
correctly dated throughout. The drift terminates by landing on
"28 Апрѣля"/theater=Маріинскій (event s076, "Romeo und Julie", 7983 р. 10 к.)
— but the scan shows that row's real printed date cell reads just "апр."
with NO day digit at all, sandwiched between "27 Пятница." and "6 Понед." —
a second, independent anomaly in the primary source itself (not an
extraction error), separate from the Маріинскій drift. Not yet fixed —
requires reattributing ~25 session rows across index positions plus a
decision on how to represent the day-less "апр." row; flagged to user for
sign-off before implementing.

## 2026-08-25 — repertoire_1899-00_p037 "23 Суббота"→"29 Суббота" fix applied; production rebuild verification

```sql
-- dry-run comparison of date_text distribution, scratch vs production parsed CSV
-- (see pipeline/parse_and_validate.py's new _REPERTOIRE_DAY_FIXES)
```

Result: Dry run confirmed exactly 3 sessions (Большой/Малый/Новый, index
19-21) changed from "23 Суббота" to "29 Суббота"; row count in
`event_entry.csv` unchanged (24131 both before and after); the unrelated,
correctly-dated "23 Воскрес." sessions elsewhere on the same page (index
1-3) untouched. Applied to `outputs/full_run/parsed/`, rebuilt `analysis`
(`build_duckdb.py`), re-ran `validate_performance_dates.py`
(`analysis.event_entry_date_check.unparseable` 1038->1035, exactly -3, as
expected), rebuilt `entities`/`research`. Post-rebuild counts:
`research.person_appearance`=21158 (unchanged), `research.performance`=24894
(unchanged), `research.event`=27738. Zero real data loss confirmed.

## 2026-08-25 — repertoire_1897-98_p010 day-less "апр." row: which row does the Romeo und Julie / Jm weissen Rössl content belong to?

Method: zoomed crop of the printed grid lines around the "27 Пятница" /
"апр." / "6 Понед." boundary (`ForUpload_1897-98_Repertoire.pdf`, page
index 10, ~2x zoom on x=150-2650, y=3280-3620 of the 400dpi render).

Result: a full-width horizontal rule spans all 5 theater columns between
the row containing Маріинскій "Romeo und Julie, Oper." (7983 р. 10 к.) /
Александринскій "Jm weissen Rössl Lustsp." (1786 р. 75 к.) — date-column
label "апр.", no day digit — and the row below it, date-column label
"6 Понед.", containing different content (Маріинскій "Генеральная
репетиція концерта въ пользу инвалидовъ", no receipts; Михайловскій
"Bénéfice de M. Rousselle... Le Roman d'un jeune Homme pauvre", 1869 р.
50 к.). These are two distinct printed rows, not one merged cell — the
Romeo und Julie / Jm weissen Rössl content does not belong to 6 Понед.
Confirms the day-less "апр." row is a separate, still-unresolved date
attached to real performance content and receipts.

## 2026-08-25 — repertoire_1897-98_p010 session-reattribution fix applied; production rebuild verification

Result: Applied `_REPERTOIRE_SESSION_DATE_FIXES` (10 sessions: the 6-session
Маріинскій drift chain resolving to 27 Марта with no fabricated "28 Апрѣля",
and 4 sessions reattributed from the false "28 Апрѣля" to "6 Понедѣльникъ").
Dry run confirmed: event_entry row count unchanged (24131), "28 Апрѣля"
eliminated entirely from this page's date_text distribution, "22 Воскресенье"
correctly gained the extra Мариинский evening session (5->6 entries), "6
Понедѣльникъ" correctly gained 4 more entries (5->9). Applied to production,
rebuilt analysis+entities+research. Post-rebuild:
`analysis.event_entry_date_check.unparseable` 1035->1030 (-5, plausible: the
newly-correct "22 Воскресенье"/"6 Понедѣльникъ" dates are now parseable
where the fabricated "28 Апрѣля" combinations previously weren't for some
of these rows). `research.person_appearance`=21158 (unchanged),
`research.performance`=24894 (unchanged), `research.event` 27738->27643
(-95, matching the drop in `analysis.event_entry`'s `not_captured`
completeness-gap count from 3861->3766 -- these newly-correct dates now
fill real grid cells that previously looked like gaps). Zero real data
loss confirmed.

## 2026-08-25 — corpus-wide check: are there other `date_text` values missing a day digit, the same shape as p010's "апр." row?

```sql
SELECT date_text, count(*) n, list(DISTINCT page_id)[:5] as sample_pages
FROM raw.event_entry
WHERE date_text IS NULL OR trim(date_text) = '' OR NOT regexp_matches(trim(date_text), '^[0-9]')
GROUP BY date_text ORDER BY n DESC;

-- and, to get every page_id individually:
SELECT page_id, date_text, count(*) n
FROM raw.event_entry
WHERE date_text IS NOT NULL AND trim(date_text) != '' AND NOT regexp_matches(trim(date_text), '^[0-9]')
GROUP BY page_id, date_text ORDER BY page_id;
```

Result: 34 rows across 12 distinct pages/6+ seasons where `date_text` is a
bare month name with no day digit at all -- the same shape as p010's "апр."
row, not yet individually scan-verified: `repertoire_1900-01_p008`
("Нодобръ.", 1), `repertoire_1900-01_p009` ("Нодобрь", 3),
`repertoire_1900-01_p029` ("Мартъ", 3), `repertoire_1901-02_p028`
("Мартъ.", 1), `repertoire_1901-02_p029` ("Мартъ.", 1),
`repertoire_1902-03_p031` ("Апрѣль", 3), `repertoire_1903-04_p008`
("Ноябрь", 3), `repertoire_1903-04_p009` ("Ноябрь", 3),
`repertoire_1904-05_p020` ("Январь.", 1), `repertoire_1904-05_p021`
("Январь.", 3), `repertoire_1904-05_p026` ("Февраль", 3),
`repertoire_1904-05_p027` ("Февраль.", 3), `repertoire_1904-05_p032`
("Мартъ", 3), `repertoire_1905-06_p005` ("Октябрь.", 3),
`repertoire_1905-06_p011` ("Ноябрь", 3). "Нодобрь"/"Нодобръ." look like a
separate misread of "Ноябрь", not the same phenomenon -- needs its own
check. Not yet individually verified against scans or fixed; flagged as a
new open item, RG informed.

## 2026-08-25 — spot-checking 2 of the 12 bare-month date_text pages against scans, to see if the p010 pattern generalizes

Method: rendered `ForUpload_1904-05_Repertoire.pdf` page index 21 and
`ForUpload_1903-04_Repertoire.pdf` page index 8 directly at 400dpi (both
PDFs already materialized locally under "Imperial Yearbooks Project/For
Upload - Repertoire Tables/"), cross-referenced row-by-row against
`raw.event_entry`/the raw JSON for each page_id.

Result: confirmed the bare-month `date_text` search is a real signal, but
NOT a uniform fix template -- the two pages checked show two different bug
shapes. `repertoire_1904-05_p021`'s "Январь." row itself carries real
content (Новый театръ "Женитьба, соверш. невѣр. событіе, ком.", 330 р. 95
к.) that the scan shows sitting immediately after 31 Декабря, before 1
Января (blank) -- needs reattributing to 31 Декабря, same general shape as
p010's "апр." row. `repertoire_1903-04_p008`'s "Ноябрь." row is actually
captured correctly already (Михайловскій's "Marthe, com. La carotte,
com.-bouffe.", 1573 р. 70 к., genuinely belongs there per the scan) -- the
real bug is one row later: "1 Суббота" should be dark for Михайловскій
(confirmed blank on the scan) but the extraction attached "2 Воскрес."'s
real content (772 р. 35 к.) to it instead, a one-row content shift
unrelated to the bare-month label itself. Neither page's fix implemented
yet -- RG asked to hold this whole new-pattern thread for a dedicated pass
later rather than push through the remaining ~10 candidate pages now.

## 2026-08-25 — remaining 13 bare-month date_text pages checked against scans (completes the corpus-wide sweep)

Method: rendered all remaining candidate pages at 350dpi from their source
PDFs (all already materialized locally), cross-referenced each against
`raw.event_entry`/raw JSON.

Result: 10 of 15 page/date_text combinations are confirmed genuine blank
divider rows -- the bare month label sits at a real closure (Lent, a
holiday gap) or simply between two real dated rows with no content
anywhere in the cell, and the extraction already correctly captures this
as `is_dark=true` with zero works/receipts (`repertoire_1900-01_p008`,
`_p029`, `repertoire_1901-02_p028`, `_p029`, `repertoire_1902-03_p031`,
`repertoire_1903-04_p009`, `repertoire_1904-05_p020`, `_p026`, `_p027`,
`_p032`). No fix needed -- zero data at stake. `1900-01_p008`'s label is
also garbled ("Нодобръ." for "Ноябрь.") but since the row is genuinely
blank this has no downstream effect; low-priority cosmetic-only.

5 combinations are confirmed real bugs, each a DIFFERENT shape from the
others and from `p010`:
- `repertoire_1904-05_p021` ("Январь.", Новый театръ): real content
  ("Женитьба, соверш. невѣр. событіе, ком.", 330 р. 95 к.) needs
  reattributing to 31 Декабря (confirmed against scan: sits immediately
  after 31 Дек, before the blank 1 Янв row).
- `repertoire_1903-04_p008` ("Ноябрь.", Михайловскій): the bare row
  itself is captured correctly (Marthe/La carotte, 1573 р. 70 к.,
  genuinely belongs there). The real bug is the NEXT row: "1 Суббота"
  should be dark for Михайловскій (confirmed blank on scan) but has "2
  Воскрес."'s content (772 р. 35 к.) attached instead.
- `repertoire_1900-01_p009` ("Нодобрь"/garbled "Ноябрь", all 3 Moscow
  theaters): a phantom extra row inserted from misreading the month
  header, shifting every subsequent day's content back by exactly one
  label for one boundary: real "1 Среда" content mislabeled "Нодобрь";
  real "2 Четвергъ" content mislabeled "1 Среда"; trailing "2 Четвергъ"
  entries (indices 35-37) are empty placeholders with no content,
  confirmed via the scan (Фея куколъ+Парижскій рыночекъ+Привалъ
  кавалеріи/671р71к genuinely belongs on 1 Среда; Лакме/3026р76к
  genuinely belongs on 2 Четвергъ).
- `repertoire_1905-06_p005` ("Октябрь.", Новый театръ): same
  reattribution shape as p021 (content belongs on "1 Суббота", confirmed
  against scan) PLUS a separate missing-title bug -- receipts (273 р. 41
  к.) captured but work_title ("Каширская старина, др.", confirmed on
  scan) is empty in the JSON.
- `repertoire_1905-06_p011` ("Ноябрь", all 3 Moscow theaters): a clean
  duplicate-emission bug -- indices 26-28 ("Ноябрь") and 29-31 ("1
  Вторникъ") are byte-for-byte identical (same works, same receipts:
  Аида/1686р55к, Красная мантія/210р29к, Въ старомъ Гейдельбергѣ/120р17к)
  -- the correct version already exists at 29-31, so 26-28 are pure
  duplicates to drop, not reattribute.

Also updated `pipeline/prompts/repertoire_system.txt` per RG's request: a
new instruction tells the extraction model that a bare month name alone
in the date column (no day number) is a printer's visual-aid marking a
month transition, not a calendar date -- skip it if the row is genuinely
blank, or attribute any real content in it to the correct adjacent
calendar day inferred from the surrounding sequence. This only affects
FUTURE extraction runs, not the already-extracted JSON these 5 bugs live
in -- those still need the parse_and_validate.py correction-table
approach used for every other fix today. None of the 5 confirmed bugs
have been fixed yet -- proposing the fix table to RG before implementing.

## 2026-08-25 — all 5 confirmed bare-month-label bugs fixed; production rebuild verification

Result: Implemented as `pipeline/parse_and_validate.py`'s new
`_REPERTOIRE_FIELD_OVERRIDES` (generic per-index field-override dict),
`_REPERTOIRE_SESSION_INSERTIONS` (new session records for printed cells the
model never emitted a row for), and `_REPERTOIRE_DUPLICATE_SESSIONS`
(confirmed duplicate sessions to drop) -- `_repair_repertoire` refactored
to return a counts dict instead of a growing positional tuple. Two RG
corrections folded in during scan review before implementation: p021's
Женитьба session belongs to 1 Суббота (not 31 Декабря, my initial guess),
and p008's Ноябрь-labeled Михайловскій session also belongs to 1 Суббота
(not "already correct as printed" as I'd first concluded) with the
existing "1 Суббота" session shifting to 2 Воскрес. Dry run confirmed
exact expected counts on all 5 pages (1 field-override + 1 insertion on
p021; 1 field-override on p005; 2 field-overrides on p008; 6
field-overrides + 3 duplicates-dropped on p009; 3 duplicates-dropped on
p011) and a clean p010 regression check (unchanged 10 session_date_fixed).
event_entry row count 23877->23872 (net -5: -3-3 duplicates dropped, +1
inserted). Applied to production, rebuilt analysis (not_captured gaps
3766->3765; date_check no_date 49->40 as the 9 newly-dated rows resolve),
entities, research. `research.person_appearance` unchanged at 21158;
`research.performance` 24894->24892 (-2, duplicate collapse);
`research.event` 27643->27637. Zero real data loss confirmed.

This completes the bare-month-label investigation opened after checking
the 4 single-digit-misread candidates: all 15 page/date_text combinations
from the original corpus scan are now resolved -- 10 confirmed clean
(no fix needed), 5 confirmed bugs (all fixed above).

## 2026-08-25 — issue #1 (non-deterministic dark-cell recall): A/B testing DashScope thinking mode, and a discovery about the detection flag itself

Method: live DashScope API calls via a scratch script (not part of the
pipeline), targeting repertoire_1890-91_p000 (the page named in
known_issues.md #1) and 3 currently-flagged pages
(`quality_checks.py`'s `zero_dark_cells_on_multiweek_page`, 19/519
Repertoire pages flagged in the current production parse).

Result 1 (repertoire_1890-91_p000): 3 baseline runs were perfectly
consistent (45 sessions, 36 dark, identical token count every time) --
does not currently reproduce the 45-vs-9 swing documented in
known_issues.md #1; that page's current production data already has good
recall. The known-issue's example may be stale (written before some
earlier model/data change) rather than reflecting current behavior.

Result 2 (checked 3 of the 19 currently-flagged pages against their
scans): `repertoire_1899-00_p000` and `repertoire_1901-02_p021` are BOTH
false positives of the flag -- their date sequences genuinely skip
non-performance days entirely (e.g. Saturdays) rather than printing them
as dark rows, so "zero dark cells" is the historically accurate
transcription of what's actually printed, not a recall failure.
`repertoire_1893-94_p006` is a genuine recall failure -- the scan clearly
shows multiple dark cells printed (both "1 Субб." and "8 Суббота" show
4 of 5 theaters dark that day), but the current extraction captured zero.
This means the flag's real precision is at best ~1/3 in this small
sample -- a page-by-page scan check is needed before trusting it, not a
blanket re-extraction of all 19 flagged pages.

Result 3 (thinking-mode A/B test on the confirmed-broken
repertoire_1893-94_p006): `enable_thinking=True` requires dropping
`response_format={"type":"json_object"}` (the two are incompatible for
this model -- combining them silently returns "0.0" as the entire
content, confirmed 3x). With that fixed, 1 baseline run recovered 1/~8+
visible dark cells (103 sessions), 1 thinking-mode run recovered 0/~8+
(105 sessions) -- thinking mode did WORSE on this sample, while costing
58% more tokens (31635 vs 20011) and taking 30% longer (328s vs 252s).
Negative result for known_issues.md #1's suggested "next thing to try."
Not tested further (small sample, but a costly, slow, and worse-performing
first sample is not promising enough to justify more spend without
checking in).

## 2026-08-25 — issue #1: chunking test, then a decisive finding that overturns the "random noise" theory

Method: continued live DashScope testing on repertoire_1893-94_p006 (the
confirmed-broken page), all against scratch scripts, not the pipeline.

Result 1 (page-splitting/"chunking"): split the page into two image chunks
at its natural physical-page seam (each chunk with the theater-column
header reattached so context isn't lost), ran baseline extraction on each.
Did not improve recall: `chunk_bottom` dropped the entire "8 Суббота" row
(all 5 theaters, including its one genuinely-active theater) just as both
original full-page baseline runs had; `chunk_top` fabricated content
across all 5 theaters for "1 Субб." when only 1 theater (Михайловскій,
2560 р. 50 к.) is actually active that day per the scan (confirmed via a
tight crop directly on the row).

Result 2 (a possible "Saturday bias" hypothesis, tested and disconfirmed):
built two small, isolated test crops (5-6 rows each, header reattached) --
one centered on "1 Субб." (mostly-dark), one centered on "15
Суббота"/"16-19 Января" (includes another mostly-dark Saturday plus
several fully-active weekdays, one of which -- "17 Понедѣльникъ" -- earlier
full-page runs had wrongly marked dark). Single-sample result: "15
Суббота" was captured PERFECTLY (all 4 dark theaters correct, Михайловскій's
content correct to the kopeck) in the same response that badly mishandled
"1 Субб." (a different Saturday) and "17 Понедѣльникъ" (not a Saturday at
all, a values-duplication error). Two different Saturdays, two completely
different outcomes in the same test -- ruled out a clean weekday-tied bias.

Result 3 (the decisive finding): ran 5 independent samples each of both
narrow test crops. "1 Субб." fabricated the *exact same* 5-6 phantom
entries, with byte-identical receipts figures (2168 р. 33 к., 861 р. 44
к., 1203 р., 1304 р. 39 к., 1096 р. 3 к. -- all real figures copied from
the neighboring "31 Пятница" row), in all 5 samples. "17 Понедѣльникъ"
duplicated the exact same wrong figure (928 р. 97 к., really
Александринскій's, wrongly also assigned to Маріинскій) in all 5 samples,
byte-identical. At non-zero sampling temperature, genuinely random noise
does not reproduce identically across 5 independent calls -- this is a
STABLE, REPRODUCIBLE misreading tied to something specific about the
image at that position, not stochastic noise. This overturns the working
theory (from earlier today) that consensus/multi-sampling would help: it
can only avg away independent, random disagreement between samples, and
these samples don't disagree with each other at all -- they agree,
consistently, on the same wrong answer. Also rules out the already-tested
mitigations (thinking mode, chunking) for a different reason than
originally suspected, and rules out a "Saturday-specific" prompt fix,
since the error isn't an assumption being applied, it's a specific,
consistent content misattribution in both directions (fabricating darks
into content, and duplicating one cell's content onto an unrelated cell).
No further pages tested this session; RG asked to pause here for the day.

## 2026-08-25/26 — issue #1: row-level isolation test finds the actual fix

Method: cropped the two confirmed-broken rows from repertoire_1893-94_p006
("1 Субб." and "17 Понедѣльникъ") down to ONLY that single row's content
(theater-column header reattached, but literally zero other date rows
visible in the image at all -- confirmed by direct visual inspection of
each crop before use). Ran 5 independent baseline samples of each.

Result: 10/10 samples, byte-identical, exactly matching the scan:
`isolated_1subb` -- Михайловскій 2560 р. 50 к., all 4 other theaters
correctly dark, every single sample. `isolated_17jan` -- Александринскій
928 р. 97 к., Михайловскій 734 р. 25 к., Большой 3801 р. 20 к., Малый
1283 р. 90 к., Маріинскій correctly no-receipts, zero dark cells
fabricated, every single sample. This is the same two rows that, in every
multi-row context tested (full page, half-page chunks, 5-6-row narrow
crops), failed consistently and often identically wrongly. Isolating the
row down to zero neighboring context eliminates the failure entirely on
this test. Practical implication: row-by-row extraction (one API call per
dated row, not per page) may be the actual fix, at a real but bounded
cost -- roughly 3-4x more tokens per page (~3400-3500 tokens per row x
~15-20 rows/page vs ~20000 tokens for one full-page call), offset by each
call being far cheaper individually (~10s vs ~250s) and highly
parallelizable. NOT yet validated beyond these 2 rows on 1 page -- next
step before committing to a pipeline rebuild is testing row-level
isolation on more rows/pages to confirm this generalizes rather than
being specific to these two rows.

## 2026-08-26 — issue #1 continued: pipeline plan approved, opencv installed, row_detect.py built, Transkribus/ScanTailor evaluated live

Result: Full session picking up from 2026-08-25's decisive finding (stable,
reproducible misattribution, not random noise -- see prior entry). Plan
approved with RG (saved at the time to
`/Users/rachelglodo/.claude/plans/nifty-enchanting-sedgewick.md`): build
row-isolated, skew-aware extraction for Repertoire pages, scoped to
Repertoire only for now, pilot-validate before any full-corpus
re-extraction, use opencv for line/curve detection.

opencv install hit a real environment issue: unpinned `opencv-python-headless`
silently attempted a from-source build (no cmake on this machine) because
the true blocker is macOS 12.7.6 (Monterey) -- recent opencv releases
(4.11+, 5.x) only ship wheels for macOS 13+. Resolved by pinning to
`opencv-python-headless==4.10.0.84` (last release with a macOS-12-compatible
wheel), installs cleanly with plain pip, no separate Python version needed
(a Python-3.14-env detour was tried first and correctly abandoned once the
real cause was found -- see the new-computer-revisit-rowdetect-env memory
file, corrected). Documented in CLAUDE.md's Setup section.

Built `pipeline/row_detect.py`: detects table row-boundary lines as curves
(tolerant of page bowing) via a per-strip peak-finding + chain-tracing
approach (a naive whole-width darkness-profile approach was tried first and
found NOT to work for curved lines -- a curved line's y drifts with x, so
no single fixed y ever reaches a high width-fraction; documented in the
module's docstring). Not yet wired into run_pilot.py.

Evaluated Transkribus (RG has an account) as an alternative to hand-building
this: table recognition returned zero tables on the test page even after
running text recognition first (the expected prerequisite order per
Transkribus's own docs); when it did produce output, it was one
undifferentiated text region with jumbled reading order and poor
transcription quality, not real table structure -- concluded the generic
models aren't a fit for this document type without training a custom model
(much bigger investment). Not pursued further.

Evaluated ScanTailor Advanced (github.com/yb85/scantailor-advanced-osx,
v1.0.18, macOS-12 build) as a whole-page dewarping preprocessor instead of
detecting curvature per-row. GUI-only in this build (no scantailor-cli
binary included -- would need a separate source build for automation).
RG ran the real test page through it live, several configurations compared
by feeding each exported TIFF through row_detect.py's debug-visualize mode:
  - Deskew=auto, dewarp unchecked, default crop: 18/~19 lines correct.
  - Deskew=auto + dewarp=marginal: WORSE (15 lines, early rows merged,
    still visible residual curvature) -- dewarp actively hurt here.
  - Dewarping off, but content-selection/crop settings also different
    (untracked change): 13 lines, also worse -- diagnosed as likely my
    detector's fixed-8%-margin-trim breaking on a much less tightly-cropped
    export, not necessarily ScanTailor's fault.
  - Full controlled baseline established with RG: Split Pages=full page
    (auto), Deskew=auto, Content Box=auto, Page Box=disabled, Margins=3mm
    all sides, Equalize=off, Dewarping=OFF. Result: 20/~19 lines detected,
    ALL correctly positioned, including both ground-truth rows ("1 Субб."
    and "8 Суббота") -- the best result of the whole session, better than
    the very first (unpinned-config) test.

**Conclusion so far: deskew alone (no dewarp) + a tight, consistent,
disabled-Page-Box crop is sufficient** -- dewarp was not needed and appeared
to hurt in one test. This significantly simplifies the eventual automation
question, since deskewing is a simpler, more standard, more likely-to-be-
scriptable operation than full dewarping.

One real bug found and NOT yet fixed while building the actual row crops
(not just the debug line-visualization) from that best-baseline image:
`detect_rows()` merged "26 Воскр." and "27 Понед." into one crop instead of
two. Root-caused via direct sanity crops (bypassing the dewarp/vstack code
entirely) to a genuine MISSED line -- the chain-tracer fails to detect the
26/27 boundary at all (a suspiciously large ~438px gap sits between two
otherwise-correctly-detected curves where a boundary should be), not a
header-count/indexing bug as first suspected (that hypothesis was tested
and ruled out: header_line_count=1 didn't fix it either). This is a
detection-recall gap, not a systemic failure -- the same run got 18-19 of
~19 boundaries right elsewhere on the same page. RG asked to pause here
for the day; picking back up this afternoon.

## 2026-08-26 — issue #1: missed-line detection bug fixed and verified

Result: Root cause confirmed empirically before fixing -- checked all 40
per-strip darkness profiles directly at the y-range where a boundary was
known to be missing; 30+ of 40 strips clearly showed the real peak, but
the single "busiest overall" strip used as the sole chain seed didn't
happen to include it, so no chain was ever built for that line at all.
Fixed `pipeline/row_detect.py`'s `_detect_line_curves` to seed a chain
from every strip (busiest-first, skipping peaks already covered by an
existing chain) instead of just one. Recovered exactly the 2 previously-
missing lines on the pilot page (confirmed both are genuine boundaries,
not spurious splits, by direct scan verification). `header_line_count`
default corrected 2->1 to match (the previous value was silently
compensating for one of the missing lines).

Re-ran the full pilot page after the fix: 20 rows produced (up from the
buggy run's merged 17-19), 6 spot-checked directly against the scan --
"26 Воскр.", "27 Понед.", "4 Вторникъ", "6 Четвертъ", "8 Суббота" all
cleanly isolated with zero bleed; "1 Субб." still shows a slight bleed
into "2 Воскрес." (a separate, pre-existing curve-precision imprecision,
not a missed-line issue -- same one identified before today's fix).
Missed-line bug considered fixed and verified on this page. Next: repeat
on a second, different pilot page per the approved plan's pilot-validation
step, before considering this ready to wire into run_pilot.py.

## 2026-08-26 — Ground-truth dated-row count per page, 1893-94 Repertoire season (row_detect.py error-rate test)

```sql
SELECT page_id, COUNT(DISTINCT date_text) AS n_dates
FROM raw.event_entry
WHERE page_id LIKE 'repertoire_1893-94_%'
GROUP BY page_id ORDER BY page_id;
```

Result: 12 pages, n_dates ranging 18-29 (most pages 19-20; p007 is an outlier
at 29). Used as ground truth to measure `row_detect.py`'s curve-detection
error rate against RAW (non-ScanTailor-processed) renders of the same
season -- see known_issues.md #1 for the outcome.

## 2026-08-26 — Diagnosing repertoire_1893-94_p007's anomalous distinct-date count (found while validating row_detect.py against a whole season)

```python
# raw.event_entry date/session breakdown for the one flagged page
import duckdb
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
con.execute("""
  select date_text, time_of_day, count(*) as n
  from raw.event_entry where page_id = 'repertoire_1893-94_p007'
  group by date_text, time_of_day order by date_text
""").df()

# raw JSON date-range/duplication check (not a DB query -- inspects the
# raw/*.raw.json file that fed the DB)
import json
d = json.load(open('outputs/full_run/raw/repertoire_1893-94_p007.raw.json'))
sessions = d['sessions']  # 89 total; 29 distinct date_text, 20 of them
                          # each repeated exactly 4x (see known_issues.md #49)
```

Result: confirmed `repertoire_1893-94_p007`'s raw JSON has real per-theater
content from early dates (e.g. 16 Воскрес./Александринскій) mislabeled
onto a later real date (24 Понед.), then a cascade of 12 further dates
(Jan 24 - Feb 12) fabricated past the end of the actual physical page
(scan confirmed to end Feb 3). See known_issues.md #49 for full writeup.

## 2026-08-26 — Corpus-wide triage: repertoire pages with anomalously many distinct dates in raw JSON (candidates for issue #49's bug)

```python
import json, glob
from collections import Counter
for path in sorted(glob.glob('outputs/full_run/raw/repertoire_*.raw.json')):
    d = json.load(open(path))
    sessions = d.get('sessions', [])
    dates = [s.get('date_text') for s in sessions]
    n_dates = len(set(dates))
    if n_dates > 22:
        print(path, len(sessions), n_dates, max(Counter(dates).values()))
```

Result: 519 repertoire raw JSON files scanned; 7 flagged (n_dates > 22):
`repertoire_1890-91_p007` (23), `repertoire_1890-91_p009` (24),
`repertoire_1892-93_p000` (67, no repeats -- different shape),
`repertoire_1893-94_p007` (29, confirmed), `repertoire_1894-95_p002` (24),
`repertoire_1895-96_p000` (28), `repertoire_1897-98_p009` (27). See
known_issues.md #49 -- none of the other 6 individually confirmed against
their scans yet.

## 2026-08-27 — театръ/театр. orthography: does "Малый театр."/"Большой театр." (missing pre-reform ъ) reflect a real printed variant or an extraction slip?

```sql
SELECT institution, count(*) as n
FROM research.person_appearance
WHERE institution ILIKE '%театр%'
GROUP BY institution
ORDER BY n DESC
LIMIT 80;

SELECT institution, page_id, count(*) as n
FROM raw.person_entry
WHERE institution IN ('Малый театр.', 'Большой театр.', 'Малый театръ.', 'Малый театръ', 'Большой театръ')
GROUP BY institution, page_id
ORDER BY institution, page_id;
```

Result: `productionteam_1894-95_p003` has BOTH "Малый театр." (3 rows) and
"Малый театръ" (10 rows) on the same page — a same-page split, which
rules out a simple per-page/per-season printing-style explanation and
needs a direct scan check. Other pages lean one way only:
`productionteam_1897-98_p003` and `1895-96_p003` only have the
abbreviated "театр." form; `1892-93_p004`, `1900-01_p004`,
`1902-03_p003/p004` only have the full "театръ" form. Also noticed in
passing (not yet investigated): 2 rows of "Императорские театры" using
fully modern post-1918 orthography (и/ы, no ъ) against 56 rows of the
expected pre-reform "Императорскіе театры" — a separate, more striking
anomaly worth its own check.

## 2026-08-27 — театръ/театр. fix verification: confirm 0 remaining instances after _repair_teatr_spelling() applied and research schema rebuilt

```sql
SELECT count(*) FROM research.person_appearance WHERE institution LIKE '%театр.%';
SELECT count(*) FROM research.person_appearance WHERE heading_path LIKE '%театр.%';
SELECT institution, count(*) FROM research.person_appearance
WHERE institution IN ('Малый театръ.', 'Большой театръ.', 'Малый театръ', 'Большой театръ')
GROUP BY institution ORDER BY institution;
```

Result: 0 remaining `театр.` (missing ъ) instances in either field. Row
counts confirm a pure text fix: `Малый театръ.` 21 (was 2 correct + 19
fixed), `Большой театръ.` 7 (was 0 + 7 fixed), `Малый театръ`/`Большой
театръ` (no period, unaffected) unchanged at 17/12.
`research.person`/`research.person_appearance` totals unchanged at
2936/21158, matching the pre-fix baseline exactly.

## 2026-08-27 — Маріинскій/Мариинскій drift: two distinct findings, verification queries

```sql
SELECT institution, page_id, count(*) n
FROM raw.person_entry
WHERE institution LIKE '%Мариинск%' OR heading_path LIKE '%Мариинск%'
GROUP BY institution, page_id ORDER BY page_id;

SELECT institution, page_id, count(*) n
FROM raw.person_entry
WHERE institution LIKE '%Императорскомъ%театрѣ%'
GROUP BY institution, page_id ORDER BY institution, page_id;
```

Result: 50 total "Мариинск" (modern и) rows split into two unrelated
findings. (1) 18 scattered instances, all the nominative "Мариинскій
театръ" form, across 6 ProductionTeam pages -- confirmed extraction
drift against `productionteam_1903-04_p001` (page 119: scan reads
"Маріинскій театръ" everywhere; 8 of the page's institution values read
"Мариинскій"). Fixed via `_repair_mariinsky_spelling()`. (2) 32 rows, one
page (`administration_1903-04_p003`), one unique institution phrase
("...Императорскомъ Мариинскомъ театрѣ") in a different case form found
nowhere else in the corpus, not visible anywhere on that page or the two
preceding it -- likely fabricated by the model rather than misread.
Logged as new issue #52, not fixed (RG: log only for now).

Post-fix verification:
```sql
SELECT count(*) FROM research.person_appearance
WHERE institution LIKE '%Мариинскій%' OR heading_path LIKE '%Мариинскій%';
SELECT count(*) FROM research.person_appearance
WHERE institution LIKE '%Мариинскомъ театрѣ%';
```
Result: 0 remaining nominative typos; the 32-row p003 fabrication
correctly untouched (deliberately excluded by scoping the regex to the
nominative case only). `research.person`/`research.person_appearance`
unchanged at 2936/21158.

## 2026-08-27 — entities.person_candidate pending review: 4 candidates checked against scans

```sql
SELECT status, count(*) FROM entities.person_candidate GROUP BY status;
SELECT candidate_id, person_id_1, person_id_2, display_1, display_2,
       similarity_score, match_reason, tenure_signal, tenure_evidence
FROM entities.person_candidate WHERE status = 'pending';
```

Result: 4 pending (20 already rejected from a prior session). Each pair's
full `research.person_appearance` history pulled and checked against the
underlying scans:
- Ивановичъ/Ивановъ, Иванъ Ивановичъ -- rejected (school director vs.
  Moscow trombonist/machinist's-assistant, different careers/cities).
- Мокѣевъ/Мокѳевъ, Николай Васильевичъ -- confirmed same person against
  the scan (`musicians_1890-91_SP_p004`, page 79, item 24: genuinely
  reads "Мокѣевъ", matching instrument Труба). Merged (see below).
- Зубовъ/Рябовъ, Александръ Петровичъ -- rejected (orchestra percussionist
  vs. ballet artist, different entity_type/career entirely).
- Щегловъ/Щеголевъ, Василій -- rejected. Confirmed against
  `ForUpload_1895-96_TheaterSchoolReport.pdf` p.3: "Щегловъ, Василій" was
  a 1895-96 graduate explicitly assigned "въ Московскую балетную труппу"
  (Moscow ballet troupe); independently confirmed showing up in Moscow
  BalletArtists rosters 1896-97 onward. "Щеголевъ, Василій" is a
  St. Petersburg Mariinsky lighting technician from 1902 -- different
  surname (both readings confirmed correct on their own scans), different
  city, different craft.

## 2026-08-27 — Мокѣевъ merge: checking downstream effect of the typo fix, found a 3rd split record

```sql
SELECT re.page_id, re.family_name, pl.person_id
FROM raw.person_entry re JOIN entities.person_link pl ON pl.entry_id = re.entry_id
WHERE re.family_name ILIKE 'Мок%евъ' AND re.first_name = 'Николай'
ORDER BY re.page_id;
```

Result: after fixing the Мокѳевъ->Мокѣевъ typo, the name was still split
across 3 person_ids: 1890-91 (1 entry), 1891-92..1902-03 (12 entries,
patronymic "Васильевичъ", service-start consistently printed as "1 января
1890 г." every year), and 1903-04..1907-08 (5 entries, patronymic
"Вавиловичъ", also consistently "1 января 1890 г."). Confirmed
"Вавиловичъ" genuinely printed (not a misread) on both
`ForUpload_1903-04_Spisok_OrchestraSP.pdf` p.4 item 27 and
`ForUpload_1907-08_Spisok_OrchestraSP.pdf` p.33 item 23 (which also gives
"left service 1 May 1908"). RG confirmed treating all three as one person
(same orchestra, same instrument, continuous non-overlapping seasons,
shared 1890 start date bridging both patronymic eras); manually merged,
full reasoning recorded in `entities.person_merge_log`.

Post-merge verification:
```sql
SELECT person_id, display_name, first_attested_season, last_attested_season
FROM research.person WHERE person_id = '1f4da16f-1f9d-4308-8d4d-a10f834cadd8';
SELECT count(*) FROM research.person_appearance WHERE person_id = '1f4da16f-1f9d-4308-8d4d-a10f834cadd8';
```
Result: 18 appearances, 1890-91 through 1907-08, one person. Canonical
`patronymic` field auto-selected "Васильевичъ" by majority vote (13 of 18
entries) -- the opposite of RG's own hypothesis that "Вавиловичъ" (the
rarer spelling) is more likely correct. Left as the majority-vote default
for now; flagged in known_issues.md as an open question, not overridden.
`research.person` 2936 -> 2934 (net -2, matching 2 losers merged into 1
survivor); `research.person_appearance` unchanged at 21158.

## 2026-08-27 — full sweep of person name fields (family_name/first_name/patronymic) for non-name contamination, all 6 entity types

```sql
-- per-entity-type suspicious-field summary (keyword/title/paren/length heuristics)
SELECT pe.entity_type,
    count(*) FILTER (WHERE <family_name flags>) AS family_name_hits,
    count(*) FILTER (WHERE <first_name flags>) AS first_name_hits,
    count(*) FILTER (WHERE <patronymic flags, incl. bare space check>) AS patronymic_hits,
    count(*) AS total_entries
FROM analysis.person_entry ae JOIN raw.person_entry pe ON pe.entry_id = ae.entry_id
GROUP BY pe.entity_type;
```

Result: all 6 entity types show some contamination. Administrators worst
by rate (2.75%, 47/1707) -- almost entirely one bug (noble title in
first_name, real first+patronymic bundled into patronymic). Graduates
second-worst (1.55%, 7/452). Musicians/BalletArtists largest raw counts
(43 each) but low rates (~0.6%), each dominated by one distinct pattern
(Musicians: a single page's "см. оперный оркестръ" cross-reference stubs
+ a recurring dual-role note; BalletArtists: stage-name/alias
parentheticals on family_name, 38 of 43).

## 2026-08-27 — Musicians "см. <orchestra>" cross-reference stubs and
"(онъ же и ...)" role-note patronymics: already resolved at the entity
layer (issues #27-#32), never fixed at the raw text layer

```sql
SELECT first_name, patronymic, count(*) FROM raw.person_entry
WHERE (first_name = 'см.' OR first_name ~ '^[0-9]+-[йя]$')
  AND (patronymic LIKE '%оркестр%' OR patronymic LIKE 'см%')
GROUP BY first_name, patronymic;

SELECT patronymic, count(*) FROM raw.person_entry
WHERE patronymic LIKE '(%)' GROUP BY patronymic;
```

Result before fix: 26 "см." cross-reference stubs (23+2+1, matching
issue #29's documented count exactly, all on `musicians_1890-91_SP_p003`)
and 8 "(онъ же и капельмейстеръ военной музыки)" whole-patronymic role
notes (matching issue #30's Марквардтъ finding). Both patterns already
fully resolved at the entities/canonical layer in a prior session (issue
#29: 210/216 stubs linked, Каминскій confirmed genuinely unresolvable;
issue #30: Марквардтъ's patronymic already NULLed in
`entities.person`), but the underlying `raw`/`analysis.person_entry`
text was never touched -- confirmed by this fresh query still finding
all 34 instances. Implemented as general `parse_and_validate.py` repair
functions (`_repair_smotri_crossref`, `_repair_role_note_patronymic`),
dry-run verified at 26/8 exactly before applying to production.

Post-fix verification:
```sql
SELECT count(*) FROM raw.person_entry
WHERE first_name='см.' OR patronymic LIKE '%оперный оркестръ%' OR patronymic LIKE 'см%';
SELECT count(*) FROM raw.person_entry WHERE patronymic LIKE '(%же и%)';
```
Result: 0 remaining both patterns. Spot-checked
`musicians_1890-91_SP_p003`'s stub entries: still correctly linked via
`entities.person_link` to their already-resolved full identities
(e.g. `Гильдебрандтъ` -> `Гильдебрандтъ, Рихардъ Николаевичъ`) --
`entry_id` stability meant the text fix didn't disturb existing entity
resolution at all. `research.person`/`research.person_appearance`
unchanged at 2934/21158.

## 2026-08-27 — Musicians remaining name-field issues after the smotri/role-note fix: 3 new patterns found and fixed

```sql
SELECT entry_id, family_name, first_name, patronymic FROM raw.person_entry
WHERE entity_type='Musicians' AND (<same suspicious-field heuristic as before>);
```

Result: down from 43 to 9 flagged (1 already-confirmed-correct --
"Нольте (фонъ)", issue #30 -- leaving 8 genuine). Checked all against
scans before fixing:

- **Letter-spaced (tracked/разрядка) typography transcribed literally**:
  every surname on `musicians_1898-99_SP_p006` (p.94) prints with
  letter-spacing; confirmed 28 corpus-wide instances (all this one
  page) where the model didn't collapse it back to a normal word, plus
  2 more found only after re-running the fix ("Кулле 1-й"/"2-й" --
  letter-spaced surname + un-spaced ordinal suffix, a shape the first
  regex version missed).
- **Compound/hyphenated first name split into patronymic**: confirmed
  on `musicians_1890-91_MSK_p004` (p.110, "Кнауеръ, Генрихъ - Эдуардъ")
  and `musicians_1902-03_MSK_p002` (p.116, "Рессеръ, Мардохей Земинъ
  Шліомовичъ" -- no dash, a bare two-word first name with the real
  patronymic after it). General fix found 13 corpus-wide instances
  (across Musicians AND BalletArtists), including independent
  corroboration: "Герберъ, Августъ-Генрихъ" already appears correctly
  joined elsewhere in the corpus (1894-95), matching exactly what the
  fix produces for the same person's broken 1906-07 appearance.
- **Instrument name in patronymic**: confirmed on
  `musicians_1898-99_SP_p006` (p.94, entry 43, "Шредеръ, Карлъ ...
  Ударные инструменты", no patronymic printed). General fix (checked
  against a fixed list of known instrument names, only when
  `instrument` is currently empty) found 6 corpus-wide instances across
  4 pages.

Post-fix verification: 0 remaining letter-spaced values, 0 remaining
dash-continuation/"Земинъ "-prefixed patronymics, 0 remaining
instrument-shaped patronymics.
`research.person`/`research.person_appearance` unchanged at 2934/21158
across all three fixes (pure text corrections).

## 2026-08-27 — rank_or_title contamination for Musicians: full scope, and why a blanket "contains instrument" rule was rejected

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND rank_or_title IS NOT NULL AND trim(rank_or_title)<>'';
-- then classified each of the 787 non-blank values (heuristic + manual review of the full distinct list)
```

Result: 3157 non-blank rank_or_title values for Musicians (once trailing
periods and spelling variants like "Біолончель"/"Альть"/"Вальдгорнь"
were counted), 3048 (96.5%) instrument-shaped in some form. Manually
reviewed the full distinct-value list (not just top-N) to separate
combined shapes (instrument+honorific, instrument+service-note,
tenure-date+instrument, pure cross-reference) from genuine content
(honorifics, Kapellmeister roles) -- RG's explicit concern was that a
match-and-wipe rule would destroy real content sitting in the same
field, confirmed real by this survey ("Скрипка. Солистъ Двора Его
Императорскаго Величества").

## 2026-08-27 — tenure-date-prefix redundancy check (37 instances) before deciding whether to discard or preserve

```sql
SELECT entry_id, rank_or_title, tenure_note_text FROM raw.person_entry
WHERE entity_type='Musicians' AND rank_or_title LIKE '(съ %';
```
Result: all 37 confirmed redundant -- the same date text (minus the
outer parens) is already present in tenure_note_text for every single
one. Safe to discard when stripping the prefix, nothing lost.

## 2026-08-27 — two remaining ambiguous rank_or_title values checked against scans

- `rank_or_title="Музыканты:"` (musicians_1892-93_MSK_p002__e016,
  Альбрехтъ) -- confirmed against the scan (p.98): genuine printed
  section header ("Балетный оркестръ" -> "Музыканты:" -> "1.
  Альбрехтъ..."), wrong field, not an instrument or personal title.
- `rank_or_title="(онъ же и библіотекарь Музыкальной библіотеки)"` (4
  rows, all Фарскій, Альбертъ Карловичъ, 1893-94 through 1902-03) --
  confirmed against the scan (musicians_1893-94_MSK_p003, entry 32):
  genuine, word-for-word printed dual-role fact (percussionist who is
  also the Music Library's librarian), consistent across 4 separate
  printings. Not contamination.
- The other 2 non-instrument values ("1 мая 1892 г.", "21 ноября
  1891 г.") are NOT a rank_or_title problem at all -- both entries have
  `family_name="Оставилъ службу"`, i.e. issue #28's already-tracked
  fake-person bug. Correctly out of scope for this fix.

## 2026-08-27 — rank_or_title fix applied: verification

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: empty instrument dropped from 5865/7065 to 3190/7065 (2675
recovered). Spot-checked genuine content survived intact: "Ауэръ"
(Leopold Auer) and "Цабель" (Albert Zabel) both show "Солистъ Двора
Его Императорскаго Величества" correctly preserved across many
seasons with instrument cleanly split out (Скрипка/Арфа respectively);
Фарскій's dual-role note preserved unchanged in all 4 appearances; the
"Музыканты:" stray heading now correctly reads "Балетный оркестръ /
Музыканты". `research.person`/`research.person_appearance` unchanged
at 2934/21158.

## 2026-08-27 — heading_path "stuck run" scoping: only 4 pages corpus-wide, and confirming the naive fallback would have been actively wrong

```sql
-- run-length detection: consecutive identical instrument-shaped heading_path
-- values per page, ordered by entry sequence (see Python script in session,
-- groupby over entry_id sorted by trailing __eNNN)
```
Result: exactly 4 pages show a 10+-row run of an identical instrument-
shaped heading_path (always "Ударные инструменты", run lengths 13-39).
Checked `musicians_1901-02_MSK_p002` directly against the scan (p.121):
confirmed only entry 35 (Зюсъ) genuinely plays percussion; the other 38
entries in the run have 38 different real instruments, all still
correctly varying in the print despite heading_path being stuck at one
value. Confirms a naive "if instrument is empty, trust heading_path"
fallback would have fabricated wrong instrument data for the large
majority of these 121 total rows (13+27+31+39 across the 4 pages).

Split by whether `rank_or_title` had already rescued the real value via
the earlier fix: 25/27 (`1893-94_MSK_p003`) and 31/31
(`1894-95_MSK_p003`) already correct; 0/13 (`1890-91_SP_p004`) and 0/39
(`1901-02_MSK_p002`) not rescued -- these two pages' cross-reference
notes were dropped entirely rather than misplaced (matches issue #27's
"40% of the time this phrase is lost outright" finding), so nothing
else in the row carried the real instrument.

## 2026-08-27 — 54 hand-transcribed instrument values re-verified directly against scans (not from memory) before applying, per RG's "no guess" instruction

Re-fetched and re-read all three affected scans fresh in this session
rather than relying on an earlier recollection (RG: "*no guessing!"):
`ForUpload_1893-94_Spisok_OrchestraMoscow.pdf` p.102 (entries 9, 32),
`ForUpload_1890-91_Spisok_OrchestraSP.pdf` p.79 (entries 54-66),
`ForUpload_1901-02_Spisok_OrchestraMoscow.pdf` p.121 (entries 35-73).
Verified the patch table's array-index keying against the actual raw
JSON (`entries[idx-1]`) for 8 sample indices across all 3 pages before
writing the fix, confirming `family_name`/`list_number` match exactly.

Applied via `_repair_instrument_transcriptions()`
(`_INSTRUMENT_TRANSCRIPTION_FIXES`), dry-run verified at 54/54 exact
match before running for real.

```sql
SELECT count(*) FROM raw.person_entry
WHERE entity_type='Musicians' AND (instrument IS NULL OR trim(instrument)='');
```
Result: 3190 -> 3136 (54 recovered, exact match).
`heading_path` deliberately left untouched by this fix (still shows the
stuck "Ударные инструменты" value) -- that's a separate, still-open
structural question (see known_issues.md #56's follow-up).
`research.person`/`research.person_appearance` unchanged at 2934/21158.

## 2026-08-27 — heading_path restoration for the 4 stuck-run pages: confirmed correct value differs by page, applied and verified

Gathered adjacent evidence before writing any fix (never assumed the
same restoration value applies to all 4 pages):
- `musicians_1893-94_MSK_p003`: entries 2-8 read heading_path="Музыканты"
  -- restore target for entries 9-35, plus entry 1 (a smaller instance
  of the same bug, confirmed via the analogous 1894-95_MSK_p002
  transition).
- `musicians_1894-95_MSK_p003`: continues musicians_1894-95_MSK_p002's
  numbered list; that page's entries 48-52 (items "1."-"5.") read
  "Оркестръ Малаго театра / Музыканты" -- the exact restore target.
- `musicians_1890-91_SP_p004`: preceding page
  (musicians_1890-91_SP_p003, entries 44-51) shows heading_path
  genuinely holding each person's own varying instrument, no separate
  section heading anywhere on this stretch -- restore target is each
  entry's own instrument (matching what's now in the `instrument`
  field).
- `musicians_1901-02_MSK_p002`: preceding page
  (musicians_1901-02_MSK_p001, entries "1."-"34.") shows heading_path
  legitimately NULL throughout, `instrument` alone carrying the data --
  restore target is NULL, not a fabricated label this list never used.

Applied via `_repair_heading_path_restore()`
(`_HEADING_PATH_RESTORE_FIXES`), dry-run matched 28+31+15+39=113 exactly
before applying.

Post-fix verification:
```sql
SELECT page_id, count(*) n FROM raw.person_entry
WHERE heading_path='Ударные инструменты' GROUP BY page_id ORDER BY n DESC;
```
Result: max remaining count per page is 3 -- fully plausible for a real
percussion section, no run resembling the fixed pattern left anywhere.
`research.person`/`research.person_appearance` unchanged at 2934/21158.

## 2026-08-27 — "shape A" heading_path->instrument migration: regenerated definitive candidate list (fresh, not from memory/prior-session recollection)

```sql
-- Musicians rows where instrument is empty AND heading_path exactly
-- matches a known-instrument-shaped value (see _KNOWN_INSTRUMENTS in
-- parse_and_validate.py), i.e. rows where the model's real instrument
-- reading landed in heading_path instead of instrument.
SELECT page_id, list_number, family_name, first_name, heading_path, instrument, entry_id
FROM raw.person_entry WHERE entity_type='Musicians';
-- (filtered in Python: instrument NULL/blank, heading_path.strip() in known_instruments set)
```

Result: 767 candidate rows across exactly 19 pages, reproducing this
session's earlier scoping exactly (musicians_1890-91_MSK_p001 (42),
musicians_1890-91_SP_p003 (45), musicians_1891-92_MSK_p001 (54),
musicians_1891-92_SP_p001 (55), musicians_1892-93_MSK_p001 (53),
musicians_1892-93_SP_p001 (53), musicians_1892-93_SP_p005 (22),
musicians_1893-94_MSK_p001 (51), musicians_1895-96_SP_p001 (51),
musicians_1898-99_MSK_p001 (39), musicians_1898-99_MSK_p002 (40),
musicians_1898-99_SP_p001 (38), musicians_1899-00_SP_p001 (39),
musicians_1899-00_SP_p002 (40), musicians_1903-04_MSK_p001 (39),
musicians_1905-06_SP_p006 (28), musicians_1906-07_MSK_p003 (36),
musicians_1906-07_MSK_p004 (4), musicians_1906-07_SP_p001 (38)).
Re-run deliberately (not trusted from a pre-compaction summary) per RG's
standing "no guessing" instruction -- confirms the candidate pool is
stable and gives a page_id/list_number/entry_id-precise base for the
patch, superseding any hand-recalled idx values from before compaction.

## 2026-08-27 — "shape A" migration verification pass: all 19 candidate pages hand-checked against scans (final 8 + 11 re-verified fresh, none trusted from pre-compaction memory)

Continuation of the "go through all of them" instruction. Re-verified
the final 8 of 15 systematically-checked pages
(musicians_1893-94_MSK_p001, musicians_1895-96_SP_p001,
musicians_1898-99_MSK_p001, musicians_1898-99_SP_p001,
musicians_1899-00_SP_p001, musicians_1899-00_SP_p002,
musicians_1906-07_MSK_p003, musicians_1906-07_SP_p001) plus, per RG's
"no guessing" standard, freshly re-derived and re-checked the remaining
11 pages whose specifics only survived a pre-compaction summary as names
without exact idx/page_id/values (musicians_1890-91_MSK_p001,
musicians_1890-91_SP_p003, musicians_1891-92_MSK_p001,
musicians_1891-92_SP_p001, musicians_1892-93_MSK_p001,
musicians_1892-93_SP_p001, musicians_1892-93_SP_p005,
musicians_1898-99_MSK_p002, musicians_1903-04_MSK_p001,
musicians_1905-06_SP_p006, musicians_1906-07_MSK_p004) -- all 19 pages
in the candidate pool now hand-verified this session.

```sql
-- Regenerated the definitive shape-A candidate list from scratch (not
-- trusted from pre-compaction recollection):
SELECT page_id, list_number, family_name, first_name, heading_path, instrument, entry_id
FROM raw.person_entry WHERE entity_type='Musicians';
-- filtered in Python: instrument NULL/blank, heading_path.strip() in
-- the _KNOWN_INSTRUMENTS set from parse_and_validate.py
```
Result: 767 candidate rows across exactly 19 pages -- reproduced the
pre-compaction scoping exactly (see full per-page counts in the entry
just above this one).

Errors confirmed against scans across all 19 pages, none trusted from
memory: Вейнаръ (1890-91_MSK_p001, wrong instrument), Браунштейнъ
(1890-91_SP_p003, stuck), Еременко (1891-92_MSK_p001, stuck),
Ватерстрадъ/Вейкманъ (1891-92_SP_p001, shifted-by-one), Гуманъ
(1891-92_SP_p001, stuck), Фридрихъ/Царскій (1892-93_MSK_p001, swapped
with each other), Кулле 1-й/Ластовскій (1892-93_SP_p005, stuck),
Плотниковъ (1898-99_MSK_p002, stuck), Голубевъ/Дворниковъ/Де-Буръ/
Зайцевъ (1903-04_MSK_p001, genuinely no instrument printed), Газенкампфъ
(1899-00_SP_p001, own name duplicated into heading_path, genuinely no
instrument), Лудольфи (1899-00_SP_p002, own name duplicated, real
instrument recoverable), Розановъ/Ромашковъ 1-й/Рѣзниковъ
(1906-07_MSK_p003, fabricated plural category word matching nothing
printed), Сиборъ (1906-07_MSK_p003, genuine instrument+title bundled
together, needs a split not a plain migration), Эмме
(1906-07_MSK_p004, stuck on the *next* section's own heading), Яньшиновъ
(1906-07_MSK_p004, genuinely no instrument printed). musicians_1893-94_
MSK_p001, musicians_1895-96_SP_p001, musicians_1898-99_MSK_p001,
musicians_1898-99_SP_p001, musicians_1892-93_SP_p001,
musicians_1905-06_SP_p006, musicians_1906-07_SP_p001 confirmed clean
(zero errors).

## 2026-08-27 — "shape A" migration applied to production: 767 candidate rows migrated/corrected, plus 7 additional not-instrument-shaped bugs found in the same pass

Implemented in `pipeline/parse_and_validate.py` as
`_repair_heading_path_shape_a()` (+ `_SHAPE_A_NO_INSTRUMENT`/
`_SHAPE_A_CORRECTIONS`) and `_repair_shape_a_special_cases()` (+
`_SHAPE_A_SPECIAL_CASES`), keyed by each entry's own printed
`list_number` (not raw array position -- a page whose list continues
from a prior page doesn't start its array at list_number 1; this was
caught and fixed during dry-run verification, see below).

Dry-run against `outputs/full_run/raw/*.raw.json` into a scratch
out-dir before touching production: totals matched exactly --
751 migrated + 16 corrected = 767 (the full candidate count), plus 7
more entries fixed outside that strict filter (Газенкампфъ, Лудольфи,
Розановъ, Ромашковъ 1-й, Рѣзниковъ, Сиборъ, Эмме). Caught and fixed two
bugs during dry-run verification before applying for real: (1) the
list_number-vs-array-position bug above, found because several
corrections silently fell through to the plain-migration branch on
continuation pages; (2) the plain `("instrument", value)` correction
branch was setting `instrument` but forgetting to clear `heading_path`,
found by spot-checking actual field values in the dry-run CSV output,
not just the row counts.

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 3136 -> 2366 (770 recovered). Applied via
`parse_and_validate.py` -> `build_duckdb.py` -> `build_entities.py` ->
`build_research_model.py`. `research.person_appearance` unchanged at
21158 (pure field correction, no rows added/dropped).
`research.person` moved 2934 -> 2897 -- expected ripple effect from
entity-clustering re-running against corrected instrument/heading_path
text (same pattern noted 2026-08-27 in
[[entities-person-cleanup-2026-08-27]] for the Мокѣевъ merge session).

Post-fix spot-check via research.person_appearance, using cross-season
corroboration the same way the project's Мокѣевъ/Еременко cases used it
before: Фридрихъ now reads "Кларнетъ" consistently 1890-91 through
1907-08 (was wrongly "Скрипка" only in 1892-93); Царскій now reads
"Скрипка" consistently (was wrongly "Кларнетъ" only in 1892-93);
Розановъ, Сиборъ, Эмме all consistent across every season they appear
in; Газенкампфъ/Голубевъ show a plausible real pattern (no instrument
in early years, one assigned later) rather than a fabricated value.

**New residual issue spotted in passing, NOT fixed (out of this
session's 19-page scope)**: a second, distinct "Лудольфи, Валентинъ
Контрабасъ." person cluster exists (seasons 1893-94/1894-95, SP) where
"Контрабасъ." is fused directly onto the first_name field itself, not
just a heading_path/instrument mixup -- a different page than the one
fixed this session (musicians_1899-00_SP_p002). Logged in
known_issues.md for a future pass.

## 2026-08-27 — post-rebuild sanity check: any new entities.person_candidate pending after the shape-A rebuild?

```sql
SELECT status, count(*) FROM entities.person_candidate GROUP BY status;
```
Result: `[('rejected', 23)]` -- 0 pending. All 23 candidate pairs are the
same already-decided set from issue #53's session; the shape-A text
corrections didn't surface any new ambiguous person-merge candidates.

## 2026-08-27 — Why are so many Musicians `instrument` fields still empty? (2366/7065, 33.5%)

RG asked for an explanation of the remaining empty-`instrument` count
after the shape-A migration (issue #59). Investigated corpus-wide, not
scoped to the 19 shape-A pages.

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians';
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 7065 total Musicians rows, 2366 empty `instrument` (33.5%);
coverage now 4699/7065 (67%).

```sql
-- heading_path / rank_or_title / tenure_note_text composition of the
-- 2366 empty-instrument rows (full breakdown done in Python over the
-- query result, not in SQL -- see session transcript for the script)
SELECT heading_path, rank_or_title, tenure_note_text
FROM raw.person_entry
WHERE entity_type='Musicians' AND (instrument IS NULL OR trim(instrument)='');
```
Result: 2113 rows have a non-blank heading_path (top values: 494
"Управляющій Училищемъ", 275 "Музыканты", 181 "Капельмейстеръ", 116
"Артисты балета", 113 "Хозяйственное отдѣленіе / Полиціймейстеры /
Маріинскій театръ", plus librarian/student/répétiteur/orchestra-
subsection headings); 253 rows have heading_path entirely blank; only
27 rows have rank_or_title filled; 85 rows' tenure_note_text still
mentions a "(см. ...)" cross-reference stub.

**Key finding**: compared tenure_note_text on rows where `instrument`
IS already correctly filled (e.g. `"(съ 19 сентября 1882 г.). Скрипка."`
alongside `instrument="Скрипка"`) against the empty-instrument rows --
tenure_note_text behaves as a reliable verbatim capture regardless of
whether `instrument` was separately parsed out. Ran the existing
`_split_leading_instrument()` helper (from parse_and_validate.py, no
new code) against every empty-instrument row's tenure_note_text after
stripping the leading date parenthetical:

```python
# see pipeline/parse_and_validate.py's _TENURE_DATE_PREFIX_RE and
# _split_leading_instrument(); applied read-only against raw.person_entry
# rows fetched via duckdb, no database write
```
Result: **1854 of 2366 empty-instrument rows (78%) have a cleanly-
recoverable instrument name sitting in tenure_note_text**, e.g.
`Цабель, tenure_note_text="(съ 1 августа 1855 г.). Арфа. Солистъ Двора
Его Императорскаго Величества."` -> instrument would split cleanly to
"Арфа", with "Солистъ Двора..." as the remainder (rank_or_title-shaped).
This is corpus-wide, not confined to the 19 shape-A pages, and appears
to be a straightforward extraction gap rather than the shape-A pattern
of a stuck/fabricated value -- but NOT YET scan-verified against any
actual page; that's the next step, not done this session.

A rough heading_path-based split of the 2366 (an approximate keyword
classifier, not precise -- e.g. "Хозяйственное отдѣленіе / Скрипки" is
a genuine orchestra-subsection heading that the classifier's admin
keyword list wrongly caught) put ~61% in an "administrative/other-role"
bucket (conductors, school director, librarians, police, students),
~22% under a bare "Музыканты"/"Оркестръ"/"Артисты" section heading only,
~11% with heading_path entirely blank, ~6% other -- but the tenure_note_text
finding above cuts across all four buckets (even the "administrative"
bucket is 77% recoverable), so this heading-based split undercounts how
much is genuinely just an extraction gap versus a genuinely-different-role
person. Not treated as authoritative -- a real category breakdown needs
the scan-verification pass, not this keyword heuristic.

**Not done this session, explicitly deferred to next session (RG:
"I want to be ready to pick this exact issue back up tomorrow")**: scan-
verify a sample of the 1854 recoverable rows, then build a
`tenure_note_text` -> `instrument` extraction repair function.

## 2026-08-28 — tenure_note_text -> instrument extraction: verification pass (10 random scan checks + full-corpus cross-season cross-check)

Continuation of 2026-08-27's finding. Re-ran the 1854-row recoverable
count fresh (not trusted from the prior session's cached number):

```sql
SELECT page_id, list_number, family_name, first_name, patronymic, instrument, tenure_note_text
FROM raw.person_entry WHERE entity_type='Musicians';
-- filtered in Python via _split_leading_instrument() after stripping the
-- tenure-date prefix (both "(съ ... г.)." and the truncated "съ ... г.)."
-- forms)
```
Result: 1854/2366 confirmed recoverable again, across 52 distinct pages
-- reproduces yesterday's count exactly.

**10 rows sampled at random across 10 distinct pages, scan-checked
directly**: musicians_1905-06_MSK_p004 (Ходаровскій), musicians_1892-93_
SP_p003 (Григоренко), musicians_1890-91_SP_p004 (Абрамовъ), musicians_
1906-07_MSK_p004 (Баулинъ), musicians_1897-98_SP_p002 (Плесковъ),
musicians_1896-97_SP_p003 (Юркевичъ), musicians_1896-97_SP_p001
(Володарскій), musicians_1893-94_MSK_p002 (Нагорнюкъ), musicians_1892-93_
SP_p002 (Теръ-Огановъ), musicians_1903-04_SP_p002 (Де-Ланге) -- all 10
instrument extractions confirmed correct. One (Григоренко) had an
extra "(см. оперный оркестръ)" remainder not actually printed on his
own line; traced to the raw JSON and found his `rank_or_title` field
already held that value before any of this session's repairs ran -- a
genuine model fabrication in a different field (same failure class as
the heading_path stuck-run bug), not caused by or related to the
tenure_note_text extraction. His instrument itself ("Флейта") was
correct regardless.

**Corpus-wide cross-season cross-check**: for every recoverable row,
checked whether the same (family_name, first_name, patronymic) has a
*different*, already-known instrument elsewhere in the corpus.
1721 rows had such a match: 1670 exact + 45 spelling/synonym-variant
agreement (99.65%), 6 genuine conflicts. All 6 scan-checked directly:
- Шолларъ (2 rows, 2 seasons), Табаковъ, Грибенъ: each row's own scan
  confirmed its own extraction was correct; the "conflict" was a real
  cross-season difference (an instrument change over the person's
  career, or two same-named different people), not an extraction bug.
- Фишеръ / Франке 1-й (musicians_1892-93_SP_p002, adjacent rows 76/77):
  confirmed via scan a genuine two-row swap, same failure class as the
  issue #59 Фридрихъ/Царскій swap. Corrected via
  `_TENURE_NOTE_INSTRUMENT_CORRECTIONS`.

## 2026-08-28 — tenure_note_text -> instrument extraction: applied to production

Implemented `_repair_tenure_note_instrument()` in `parse_and_validate.py`
(only fills `instrument` when empty; never touches `tenure_note_text`
itself, a verbatim field, or any remainder text after the instrument --
deliberately conservative, given the Григоренко remainder finding
above). Dry-run first (isolated call gave a false 2304-row result
because it skipped the pipeline's actual repair order -- re-ran
replicating the real order and got the expected 1854, then confirmed
again via a full `parse_and_validate.py` run into a scratch dir:
`tenure_note_instrument_recovered` = 52 pages / 1854 rows exactly,
matching the scoping count).

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`.

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 2366 -> 512 (1854 recovered, exact). Musicians `instrument`
coverage now 6553/7065 (93%), up from 67% at the end of issue #59.
`research.person_appearance` unchanged at 21158; `research.person`
unchanged at 2897 (no clustering ripple this time -- this fix never
touches name/heading text, only `instrument`).

Post-fix spot-check via `research.person_appearance`: Фишеръ now reads
"Віолончель" consistently across all 4 of his seasons (was wrongly
"Кларнетъ" only in 1892-93); Франке now reads "Кларнетъ" consistently
across nearly every season (was wrongly "Віолончель" only in 1892-93);
Абрамовъ, Баулинъ, Володарскій, Григоренко, Де-Ланге, Нагорнюкъ all
internally consistent across every season checked. Грибенъ visibly
shows a genuine instrument transition (Ударные инструменты in the
1890s, Фортепіано from 1900-01 onward) now that both eras are populated
-- previously obscured by the empty field, not a data error.

```sql
SELECT status, count(*) FROM entities.person_candidate GROUP BY status;
```
Result: `[('rejected', 23)]` -- 0 pending, same as before this fix; no
new ambiguous person-merge candidates surfaced.

## 2026-08-28 — Triaging the ~512 remaining empty-instrument Musicians rows (RG: "Let's work on these")

Fresh count confirmed (not trusted from prior session's cached number):

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 512, matching yesterday's end-of-session count.

```sql
SELECT page_id, list_number, family_name, first_name, patronymic,
       heading_path, rank_or_title, tenure_note_text
FROM raw.person_entry
WHERE entity_type='Musicians' AND (instrument IS NULL OR trim(instrument)='');
```
Categorized all 141 distinct heading_path values by frequency (done in
Python, not SQL). Found two more recoverable pockets the prior sessions'
filters missed, plus 3 unrecognized instrument spelling variants, plus
one real title/instrument-conflation case:

1. **"Оркестръ / <Instrument>" and "Оркестр оперы и балета. <Instrument>."**
   -- 50 rows across exactly 2 pages (musicians_1897-98_MSK_p000: 13,
   musicians_1902-03_SP_p001: 37), where heading_path holds a genuine,
   information-bearing institutional heading with the person's own
   instrument tacked onto the end as one compound value -- missed by
   the original shape-A filter (issue #59), which required heading_path
   to be *exactly* a bare instrument name. Every single instrument value
   on both pages checked directly against the scan (e.g. item 8, Борхъ,
   reads "Ударные инструменты" in print) -- confirmed correct.

2. **3 unrecognized instrument spelling variants** in tenure_note_text,
   each confirmed by scan: "Піанисть" (Гедике, musicians_1890-91_MSK_p001
   -- also already sitting correctly in heading_path, just never
   recognized as an instrument), "Вальтгорнъ" (Сольскій, musicians_1904-
   05_SP_p003 idx106), "Волторнъ" (Солодуевъ, musicians_1905-06_MSK_p003
   idx94, distinct from the already-known "Волторна" variant).

3. **5 rows where a genuine instrument sits in tenure_note_text but the
   general extraction can't reach it**: a leading dual-role parenthetical
   before the date (Марквардтъ idx63 on musicians_1895-96_MSK_p001 --
   "Труба"; Фарскій idx32 on musicians_1895-96_MSK_p003 -- "Альтъ", both
   with strong pre-existing cross-season corroboration), a malformed
   date-prefix punctuation variant (Терентьевъ idx30, same page --
   "Скрипка"; Сольскій idx32 on musicians_1896-97_SP_p003 -- "Вальдгорнъ"),
   and _split_leading_instrument's own boundary-safety check declining a
   genuine split before a lowercase continuation (Смирновъ idx34 on
   musicians_1891-92_SP_p004 -- "Піанистъ при драматическихъ
   спектакляхъ.", scan-confirmed against ForUpload_1891-92_Spisok_
   OrchestraSP.pdf p.65).

4. **Крейнъ, Давидъ (2 rows, musicians_1906-07_MSK_p002 idx52 and
   musicians_1907-08_MSK_p001 idx52)**: 7 prior seasons (1897-98 through
   1905-06) consistently read "Первая скрипка"; these 2 rows instead
   read "Концертмейстеръ" (a genuine promotion/title, this era's
   "concertmaster" = principal first violin) with no instrument
   re-stated. Decided NOT to infer "Первая скрипка" for these 2 rows
   without direct textual support -- relocated "Концертмейстеръ" to
   rank_or_title instead, leaving instrument empty (matches this
   project's standing rule against fabricating plausible-but-unstated
   values).

**Also checked and confirmed correctly blank** (no recoverable content):
répétiteurs (ballet rehearsal coaches -- 3 scans checked, all end their
entry right at the tenure date, no instrument printed, even though
répétiteurs are often pianists in real life); Барминъ/Брындлинъ/Козловъ
(musicians_1901-02_MSK_p001, also répétiteurs); Брекеръ's 1905-06 season
specifically (unlike every other season, this one row's own scan shows
no instrument printed that year). Also spotted (not fixed, already
tracked): 2 "Оставилъ службу [date]" rows with family_name literally
set to that phrase -- a duplicate instance of the already-documented
issue #26 (non-person text captured as person_entry rows), not touched.

## 2026-08-28 — the above fixes applied to production

Implemented `_repair_heading_path_prefixed_instrument()`,
`_TENURE_NOTE_INSTRUMENT_HAND_FIXES` (extends
`_repair_tenure_note_instrument`), 3 new entries in `_KNOWN_INSTRUMENTS`,
and `_repair_tenure_note_title_relocation()` +
`_TENURE_NOTE_TITLE_RELOCATIONS` in `parse_and_validate.py`. Dry-run
into a scratch dir first: `heading_path_prefixed_instrument_split` = 2
pages / 50 rows exactly; `tenure_note_instrument_recovered` rose from
1854 to 1861 rows (the 2 spelling-variant auto-recoveries + 5 hand-fixes);
`heading_path_shape_a_migrated` rose from 751 to 752 (Гедике, now caught
by the "Піанисть" addition); `tenure_note_title_relocated` = 2 rows.
Spot-checked the parsed CSV directly for all 11 target rows before
applying -- every value matched exactly as designed, including Крейнъ
correctly staying instrument-empty with only rank_or_title changed.

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`.

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 512 -> 454 (58 recovered, exact match to the dry-run total:
1 + 7 + 50 = 58). Coverage now 6611/7065 (93.6%). `research.person`
unchanged at 2897; `research.person_appearance` unchanged at 21158.

Post-fix spot-check via `research.person_appearance`: Борхъ, Брекеръ,
Гедике, Марквардтъ, Сольскій, Терентьевъ, Фарскій, Солодуевъ all
internally consistent with their other seasons. Крейнъ confirmed
correct: "Первая скрипка" for 1897-98 through 1905-06, then
instrument=None / rank_or_title="Концертмейстеръ" for exactly the 2
rows fixed, nothing else touched.

```sql
SELECT status, count(*) FROM entities.person_candidate GROUP BY status;
```
Result: `[('rejected', 23)]` -- 0 pending, unchanged; no new ambiguous
person-merge candidates surfaced.

## 2026-08-28 — Griboyedov/Григоренко rank_or_title stuck-value bug: scoped and fixed

RG: "The Григоренко rank_or_title stuck-value bug. Let's fix this next"
(picking up the item carried over from issue #60/#61).

```sql
SELECT page_id, list_number, family_name, first_name, instrument, tenure_note_text
FROM raw.person_entry
WHERE entity_type='Musicians' AND rank_or_title ILIKE '%см%';
```
Result: 0 rows -- the value no longer lives in `rank_or_title` by the
time raw.person_entry is built; an existing repair
(`_repair_musicians_rank_or_title`, issue #56) already relocates a
"(см. ...)" value found there into `tenure_note_text`. Re-scoped there
instead:

```sql
SELECT page_id, list_number, family_name, first_name, instrument, tenure_note_text
FROM raw.person_entry
WHERE entity_type='Musicians' AND tenure_note_text ILIKE '%см%';
```
Result: 196 rows across 12 pages. Classified each by whether
tenure_note_text has its own tenure-date prefix before the "(см. ...)"
note (own-date = likely fabricated, matching the confirmed Григоренко
shape; no-date = genuine cross-reference stub, matching the confirmed
Гуманъ/Добровъ shape from issue #57's investigation): 173 rows (11
pages) are "no-date" stubs; 23 rows are "own-date", and **all 23 are on
a single page**, `musicians_1892-93_SP_p003`.

Confirmed by direct scan reading (not from memory): every one of the 23
"own-date" rows has its own complete record printed with no crossref at
all (e.g. item 22, Затценгоферъ: "(съ 24 сентября 1875 г.). Фаготъ." --
nothing else), including a same-page cross-check that 7 of the 23
(items 1-7: Абрамовъ..Вагнеръ) belong to an entirely separate "Оркестръ
Александринскаго театра" list printed at the bottom of the same page,
with no crossref concept applicable there at all. Confirmed the *other*
11 pages' 173 stub rows are genuine by re-checking the identical layout
one season earlier (`musicians_1891-92_SP_p003`) -- same alternating
pattern, zero "own-date" fabrications there.

Traced the mechanism via the raw JSON directly:
```python
# outputs/full_run/raw/musicians_1892-93_SP_p003.raw.json, entry for
# list_number "19." (Григоренко): rank_or_title = "(см. оперный
# оркестръ)" already in the model's own extraction, before any repair
# runs -- confirms the fabrication is upstream (the LLM extraction
# itself), not a bug in _repair_musicians_rank_or_title, which
# faithfully (and correctly, for the other 3048+ rows it's validated
# against per issue #56) relocates whatever rank_or_title actually says.
```

## 2026-08-28 — fabricated-crossref fix applied to production

Implemented `_repair_fabricated_crossref_note()` +
`_FABRICATED_CROSSREF_NOTE_FIXES` in `parse_and_validate.py`, scoped to
exactly the 23 confirmed (page_id, list_number) pairs -- strips only the
trailing "(см. ...)" suffix from tenure_note_text, leaves everything
else (including the already-correct `instrument` field) untouched.

Dry-run into a scratch dir: `fabricated_crossref_note_stripped` = 23
rows on `musicians_1892-93_SP_p003` exactly. Spot-checked the parsed CSV
directly: all 23 targets (Григоренко, Затценгоферъ, Парисъ, Эллингеръ,
Абрамовъ, etc.) cleanly stripped; the genuine stubs (Гуманъ idx20,
Добровъ idx21) confirmed untouched.

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`. `research.person`
unchanged at 2897; `research.person_appearance` unchanged at 21158 (pure
text correction, no rows added/dropped). Post-fix spot-check via
`research.person_appearance`: Абрамовъ, Григоренко, Затценгоферъ,
Парисъ, Эллингеръ all show their real instrument consistently across
every season, with the 1892-93 row now indistinguishable from the
others; Гуманъ's genuine crossref-shaped record confirmed unaffected.

```sql
SELECT status, count(*) FROM entities.person_candidate GROUP BY status;
```
Result: `[('rejected', 23)]` -- 0 pending, unchanged.

## 2026-08-28 — Лудольфи fused-name cluster: scoped and fixed (patronymic-period generalization)

RG: "The Лудольфи fused-name cluster. Let's also check this." (carried
over from issue #59).

```sql
SELECT page_id, list_number, family_name, first_name, patronymic, instrument
FROM raw.person_entry WHERE entity_type='Musicians' AND family_name ILIKE '%удольф%';
```
Result: confirmed the fused-name shape (`patronymic="Контрабасъ."`) on 2
rows (musicians_1893-94_SP_p001, musicians_1894-95_SP_p001, both list_number
"64."). Traced to `_repair_instrument_in_patronymic()`'s exact-match check
(`pat in _KNOWN_INSTRUMENTS`) missing the trailing period the printed
sentence ends on. Corpus-wide re-check for the same near-miss (`pat.rstrip
(".") in _KNOWN_INSTRUMENTS`) found 2 more identical instances for a
second person, Котте (same 2 pages, list_number "55."). All 4 confirmed
by scan (e.g. "55. Котте, Фридрихъ-Эрнестъ (съ 1 сентября 1893 г.).
Фаготъ." prints cleanly).

Generalized `_repair_instrument_in_patronymic()` to strip a trailing
period before matching. Dry-run into a scratch dir found 10 rows touched
across 6 pages (not just the 4 targeted) -- cross-checked all 10 against
current production and confirmed 6 were already correctly filled via a
different repair path (this fix just reaches the same correct value
earlier in a from-scratch run); only the 4 originally targeted rows were
genuinely new content, matching exactly.

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`. Post-fix spot-check via
`research.person_appearance`: Котте reads "Фаготъ" consistently across
all seasons 1893-94 through 1907-08; Лудольфи reads "Контрабасъ"
consistently across all seasons -- the 2 newly-fixed rows for each now
indistinguishable from the rest.

## 2026-08-28 — "Оставилъ службу"/"†" fragment person-entries: scoped corpus-wide and fixed

RG: "the 2 'Оставилъ службу'-as-name garbage rows. And this one" (carried
over from issue #61's triage).

```sql
SELECT DISTINCT page_id, family_name FROM raw.person_entry
WHERE family_name ILIKE 'Оставилъ%' OR family_name ILIKE 'Переведенъ%'
   OR family_name ILIKE 'Умеръ%' OR family_name ILIKE 'Уволенъ%'
   OR family_name ILIKE '†%' OR family_name ILIKE 'Назначенъ%'
   OR family_name ILIKE 'Скончал%';
```
Result: 5 rows (not 2), across 3 entity types: musicians_1891-92_MSK_p003
(x2), musicians_1897-98_SP_p001, administration_1895-96_p001,
theaterschoolstaff_1902-03_p002 (`family_name="†"`),
theaterschoolstaff_1896-97_p000. Confirmed by scan for all 5: every one
is a trailing service-end or death note (e.g. musicians_1897-98_SP_p001
entry 74, Плацатка: "... Фаготъ. Оставилъ службу 1 октября 1897 г."
prints as one continuous entry) mis-split by the model into its own fake
"person" entry, always the entry immediately preceding it. Also spotted
a distinct, unrelated bug on theaterschoolstaff_1896-97_p000 while
checking (a real person, Сперанскій, whose name landed in heading_path
instead of family_name on the entry that follows) -- not fixed, out of
scope for this specific repair.

Implemented `_repair_fragment_person_entries()` in `_repair_roster()`'s
neighborhood (applies to all roster entity types), merging the fragment
into the preceding entry's tenure_note_text and dropping the fake row.
Dry-run: `fragment_entry_merged` fired on all 5 pages, 6 rows total
(musicians_1891-92_MSK_p003 alone has 2). Content-level diff (keyed on
page_id/list_number/name, not entry_id, which shifts after any removal)
confirmed exactly those 6 rows removed and nothing else changed.

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`. `raw.person_entry`
7062 Musicians rows (was 7065, -3 fake rows removed); `research.person`
2894 (small ripple from entity re-clustering, expected);
`research.person_appearance` 21154 (was 21158, -4). Post-fix spot-check
via `research.person_appearance`: Богуславъ, Захаровъ, Флоринскій,
Шемаевъ all show the merged note correctly in tenure_note_text, no
separate fake entry remains.

**Note, not chased further**: `research.person_appearance` shows
Флоринскій's merged note duplicated within one row's text
("Оставилъ службу 1 февраля 1897 г." appearing twice) for the 1896-97
season, even though `raw.person_entry`'s own `tenure_note_text` is
confirmed correct (checked directly, no duplicate). This is a
pre-existing derivation quirk in how `build_research_model.py` builds
`person_appearance` (likely double-pulling from `person_entry_service`),
not something this fix introduced, and doesn't touch Musicians data --
noted for a future look, not investigated further here.

```sql
SELECT status, count(*) FROM entities.person_candidate GROUP BY status;
```
Result: `[('rejected', 23)]` -- 0 pending, unchanged.

## 2026-08-28 — exported full Musicians CSVs for RG to browse (raw.person_entry + research.person_appearance)

RG asked to see a CSV of just Musicians and their fields, both layers,
full row counts, before continuing the empty-instrument verification.

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians';
SELECT count(*) FROM research.person_appearance WHERE entity_type='Musicians';
```
Result: 7062 raw rows, 7061 research rows (1 fewer -- expected, one raw
row didn't produce a person_appearance row, not investigated further
here). Exported both to CSV in the scratchpad and sent to RG directly,
not saved anywhere in the repo.

## 2026-08-28 — tenure_note_text deep-dive with RG: duplicate-fix bug, 2 instrument recoveries, crossref-prefix pattern, and punctuation normalization

RG asked to see the raw Musicians CSV directly, then spotted several
issues while browsing it in parallel with continued investigation here.

**1. Duplicate-fix bug (found, not asked, while checking the punctuation
question)**: `build_duckdb.py`'s `tenure_note_text_clean` derivation had a
pre-existing, hardcoded one-off SQL patch for the exact Флоринскій
"Оставилъ службу" row this session's new
`_repair_fragment_person_entries()` (issue #64) now also fixes upstream
-- the two were stacking, producing the duplicated text spotted earlier
and flagged as "not investigated." Removed the stale SQL branch (kept
its sibling general-regex branch, still a live defense for a different
shape). RG: "Okay fix this."

**2. Instrument-field-contaminated rows (found via the same SQL block's
other branch)**:
```sql
SELECT entity_type, page_id, list_number, family_name, instrument, tenure_note_text
FROM raw.person_entry WHERE regexp_matches(instrument, '^(Оставилъ службу|Переведенъ)');
```
Result: 2 rows, both Musicians, both on `musicians_1903-04_MSK_p000` --
Барсукъ-Самборскій (idx7, `instrument="Оставилъ службу 1 октября 1903
г."`) and Гейслеръ (idx19, `instrument="Переведенъ съ 1 октября 1902 г.
въ Малый театръ."`). Confirmed by scan (p.113): both print their real
instrument (Вальдгорнъ/Контрабасъ) immediately followed by the
resignation/transfer sentence; cross-season corroboration unanimous (13
and 15 other seasons respectively). Fixed via a new
`_INSTRUMENT_SERVICE_NOTE_CORRECTIONS` table + `_repair_instrument_
service_note()`, restoring the real instrument and relocating the note
into tenure_note_text.

**3. Crossref-prefixed instrument pattern (found while cross-checking
patterns in the ambiguous heading_path buckets)**: 18 rows where
tenure_note_text reads "(см. оперный оркестръ). \<Instrument\>." --
missed by the date-prefix-only extraction. Confirmed by scan on both
affected pages (`musicians_1892-93_MSK_p003` p.99, entries 37-56;
`musicians_1891-92_SP_p002` p.63, entries 1-6) -- all 18 correct.
Extended `_repair_tenure_note_instrument()` to also try a crossref-
prefix regex when the date-prefix regex doesn't match.

**4. Why do only some tenure_note_texts have an instrument? (RG's
question, answered with data)**:
```python
# for every currently-empty-instrument Musicians row, check whether
# tenure_note_text contains ANY known instrument word anywhere
```
Result: of 429 empty-instrument rows (at that point), only 2 had any
instrument word anywhere in tenure_note_text at all -- 98% of empty
rows genuinely have no instrument text anywhere in their own verbatim
capture, consistent with them being genuinely non-instrumentalist people
(conductors, librarians, school administrators, répétiteurs, students)
rather than an extraction miss. The 2 exceptions were both real,
scan-confirmed misses:
- Фарскій (`musicians_1902-03_MSK_p004` idx26): "съ 1 января 1894 г.
  Альтъ. † 31 августа 1903 г." -- a missing closing paren AND a dual-role
  parenthetical stacked together, defeating every existing carve-out at
  once. Confirmed by scan (p.118): "(онъ же и библіотекарь Музыкальной
  библіотеки) (съ 1 января 1894 г.). Альтъ. † 31 августа 1903 г."
- Стрекаловъ (`musicians_1905-06_MSK_p003` idx97): "(съ 1 октября 1894
  г.). Переведенъ въ оркестръ Малаго театра 1 апрѣля 1901 г. Вторая
  скрипка." -- the instrument sits AFTER a transfer note, a shape none
  of the extraction logic looks for. Confirmed by scan (p.59).
Both added to `_TENURE_NOTE_INSTRUMENT_HAND_FIXES`.

**5. Punctuation variance -- real print variation or extraction
artifact? (RG's question, answered with data)**:
```sql
-- shape classification of all 7014 non-blank Musicians tenure_note_text
-- values: 3987 full "(съ...г.)", 1921 no parens at all, 918 missing only
-- the opening paren, 187 other-start (crossref/dual-role prefixes), 1
-- missing only the closing paren
```
Checked two full/partial pages directly against the scan
(`musicians_1893-94_MSK_p001` p.100, all 50 rows; `musicians_1892-93_
SP_p003` p.99, spot-check) -- **zero exceptions**: the printed page
always uses full "(съ ... г.)." parens. The variance in the data is
confirmed to be a pure extraction/OCR artifact (the model dropping the
opening paren inconsistently), not the book's own convention varying.
RG: "let's make sure the clean version follows the (съ ... г.)
convention."

## 2026-08-28 — tenure_note_text_clean punctuation normalization implemented and applied

Added a regexp_replace step to `build_duckdb.py`'s `tenure_note_text_
clean` derivation (in `analysis.person_entry`, per RG's confirmed
architectural preference: raw stays verbatim, `_clean` is the derived
layer). Pattern: `^\(?(съ (?:.+?г\. (?:по|и) )*.+?г\.)\)?` -> `(\1)`.
Validated against the full 7014-row Musicians tenure_note_text corpus
before applying:
- Handles simple dates correctly regardless of original paren state.
- Correctly captures compound multi-period service dates whole (35
  confirmed instances, e.g. "съ 10 декабря 1879 г. по 20 октября 1880 г.
  и съ 19 сентября 1882 г." -- verified NOT over-matched, longest genuine
  capture 68 chars).
- The non-greedy inner "г\." stop correctly prevents a malformed
  no-closing-paren row (Фарскій's "съ ... г. Альтъ. † ... г.") from
  swallowing unrelated later sentences into the "date" -- confirmed by
  direct test before deploying.
- Correctly leaves the 187 "other-start" rows (crossref/dual-role-
  parenthetical prefixes) untouched, out of scope for this convention.

Applied via `parse_and_validate.py` (items 2/3/4 above) ->
`build_duckdb.py` (items 1/5 above) -> `build_entities.py` ->
`build_research_model.py`.

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 429 -> 427 (2 recovered: Фарскій, Стрекаловъ). Coverage now
6635/7062 (94.0%). `research.person` 2894 (unchanged from before this
round); `research.person_appearance` 21154 (unchanged).

Post-fix spot-check via `research.person_appearance`: Барсукъ-
Самборскій ("Вальдгорнъ"), Гейслеръ ("Контрабасъ"), Стрекаловъ ("Скрипка"
/"Вторая скрипка"), Фарскій ("Альтъ") all consistent across every season,
each fixed row now indistinguishable from the rest; Флоринскій's merged
note appears exactly once (1896-97 season), confirming the duplicate-fix
bug is resolved. `tenure_note_text_clean` spot-checked directly against
`tenure_note_text` for Вильшау/Бѣлицкій/Гейслеръ/Барминъ (compound date)/
Фарскій (malformed) -- all normalize correctly.

```sql
SELECT status, count(*) FROM entities.person_candidate GROUP BY status;
```
Result: `[('rejected', 23)]` -- 0 pending, unchanged.

## 2026-08-28 — "Let's check the ones that are instrumentalists but don't have an instrument in the tenure text" (RG)

Follow-up to the "why do only some tenure_note_texts have an instrument"
finding -- RG asked specifically about the subset who ARE confirmed
instrumentalists (a real instrument on record for that same person in
another season) yet still show empty in a given row.

```python
# cross-season corroboration: for every currently-empty-instrument
# Musicians row, check whether the same (family_name, first_name,
# patronymic) has a known instrument in another season
```
Result: 114 such rows. Filtered out career-transition cases (heading_
path/rank_or_title showing the person is now a Капельмейстеръ/
conductor, Библіотекарь/librarian, Управляющій Училищемъ/school
director, Дирижеръ, Концертмейстеръ, or Полицiймейстеры/police
superintendent at the time of that row -- confirmed a real, meaningful
pattern, not noise: e.g. Марквардтъ moved from cornet/trumpet player to
"Капельмейстеръ военной музыки"; an entire cluster of former orchestra
musicians (Островскій, Петровъ, Поббигъ, and 9 more) are listed as
"Старшій библіотекарь Центральной Музыкальной Библіотеки" -- genuinely
no longer functioning as instrumentalists in those rows, correctly
blank). This filter caught a real bug in itself: an initial version used
Cyrillic "и" where the pre-reform text actually has "і" (Библ**і**отекарь),
silently failing to exclude the whole librarian cluster -- corrected by
switching to a substring safe against that distinction ("отекар").

Left 18 rows: confirmed instrumentalists elsewhere, still listed under
a plain "Музыканты"/blank/orchestra-subsection heading in the row with
no instrument. Scan-verified every one, not assumed:
- 7 already confirmed in this session's earlier passes (issues #59/#61):
  Голубевъ, Дворниковъ, Де-Буръ, Зайцевъ (musicians_1903-04_MSK_p001),
  Яньшиновъ (musicians_1906-07_MSK_p004), Газенкампфъ (musicians_1899-
  00_SP_p001), Брекеръ (musicians_1905-06_SP_p001).
- 11 newly checked this pass, all confirmed genuinely blank in print:
  Газенкампфъ (musicians_1900-01_SP_p001 idx27, p.87), Адамовъ x2
  (musicians_1903-04_MSK_p000 idx1 and musicians_1904-05_MSK_p000 idx2,
  p.113/61), Ардъ (musicians_1903-04_MSK_p000 idx5, p.113 -- also
  independently confirmed by the very next season's page showing his
  instrument, "Вторая скрипка", now printed, i.e. a genuine new-hire-not-
  yet-assigned pattern with direct corroborating evidence), Брандтъ
  (same page, idx12), Шмукловскій (musicians_1904-05_MSK_p004 idx22,
  p.65), Шульцевъ x2 (musicians_1906-07_MSK_p004 idx12 p.62 and
  musicians_1907-08_MSK_p003 idx12 p.58 -- blank two seasons running),
  Тарасенковъ and Таротинъ (musicians_1906-07_SP_p003 idx101/102, p.32),
  Брекеръ (musicians_1907-08_SP_p000 idx11, p.29 -- blank again, a
  second season, despite "Кларнетъ" on record many other years).

**Result: 18/18 confirmed genuinely blank in print, zero exceptions,
zero further recoverable instrument content.** Even for confirmed
instrumentalists, an empty tenure_note_text in a given row reliably
means the yearbook itself printed no instrument that year -- most often
a brand-new hire's very first season before an instrument was assigned/
printed, occasionally an established player's instrument simply omitted
in a specific later season's reprint. No pipeline fix needed; this
closes out the "instrumentalists with no instrument in tenure text"
question RG raised.

## 2026-08-28 — verify the 21-row instrument-crossref fix end-to-end after production pipeline run

```sql
select list_number, family_name, instrument, tenure_note_text
from raw.person_entry
where page_id = 'musicians_1891-92_MSK_p002'
  and try_cast(list_number as integer) in (2,3,5,7,8,9,10,11,12,13,17,18,21,22,25,29,31,35,36,37,38)
order by try_cast(list_number as integer);

select status, count(*) from entities.person_candidate group by 1;

select p.canonical_family_name, pa.season, pa.instrument, pa.tenure_note_text
from research.person_appearance pa
join research.person p on p.person_id = pa.person_id
where p.canonical_family_name in ('Альбрехтъ','Гейслеръ','Лебедевъ','Петровъ')
  and pa.season = '1891-92'
order by p.canonical_family_name;
```

Result: all 21 rows on `musicians_1891-92_MSK_p002` show the restored
instrument with the crossref note relocated into `tenure_note_text`
(e.g. Альбрехтъ: instrument=Корнетъ, tenure_note_text="(см. оперный
оркестръ)"). `entities.person_candidate`: 0 pending, 23 rejected (clean).
`research.person_appearance` spot-check for the 4 named surnames'
1891-92 season: each crossref-stub row's restored instrument matches
that same person's "home" entry instrument that season (Альбрехтъ→
Корнетъ, Гейслеръ→Контрабасъ, Лебедевъ→Флейта, Петровъ→Скрипка) —
internally consistent. Pipeline confirms: `research.person` 2894 rows,
`research.person_appearance` 21154 rows (both unchanged from pre-fix,
as expected for an in-place field correction). Logged as known_issues.md
#66.

## 2026-08-28 — what does rank_or_title contain, raw (pre-repair) JSON, Musicians only

```python
import json, glob
from collections import Counter
rank_values = Counter()
heading_contains_rank = 0
n_checked = 0
for fp in glob.glob('outputs/full_run/raw/musicians_*.raw.json'):
    d = json.load(open(fp))
    entries = d['entries'] if isinstance(d, dict) and 'entries' in d else d
    for e in entries:
        rot = (e.get('rank_or_title') or '').strip()
        if not rot: continue
        n_checked += 1
        rank_values[rot] += 1
        hp = (e.get('heading_path') or '')
        if rot in hp:
            heading_contains_rank += 1
```

Result: 3157 non-blank `rank_or_title` values in the raw, pre-repair
model output across all Musicians pages; only 5 also appear verbatim
inside that same row's `heading_path`. Top values by frequency are
overwhelmingly instrument names, not ranks/titles: Первая скрипка 328,
Вторая скрипка 254, Альтъ 217, Контрабасъ 196, Віолончель 168,
Вальдгорнъ 140, Флейта 140, Кларнетъ 135, Ударные инструменты 116,
Труба 103, Тромбонъ 100, Фаготъ 99, Гобой 86, Скрипка 80, "(см. оперный
оркестръ)" 67, Арфа 62 (plus many spelling/period-suffix variants of
the same instrument names). Confirms issue #56's original finding that
the model routinely puts an instrument name in `rank_or_title` instead
of (or in addition to) `instrument` — this is the raw, uncorrected
signal, not the current DB state.

## 2026-08-28 — what does rank_or_title contain, current parsed CSV (post-#56-repair), Musicians only

```python
import csv
from collections import Counter
rows = [r for r in csv.DictReader(open('outputs/full_run/parsed/person_entry.csv')) if r['entity_type']=='Musicians']
rank_values = Counter(r['rank_or_title'].strip() for r in rows if r['rank_or_title'].strip())
```

Result: 52 non-blank `rank_or_title` values remain post-repair (18
distinct), down from 3157 raw — confirming ~98% of the raw field's
content was instrument-name contamination already split out by issue
#56's repair. What's left is genuine honorifics/ranks/dual-roles:
"Солистъ Двора Его Императорскаго Величества" (18+ variants),
"Заслуженный артистъ Императорскихъ театровъ" (8), "Капельмейстеръ"
family (4+2), "(онъ же и библіотекарь Музыкальной библіотеки)" (4),
"Концертмейстеръ" (2), plus one-off dual-role/promotion notes
("Пьянисть при драматическихъ спектакляхъ", "Репетиторъ балета",
"Композиторъ балетной музыки", "назначенъ капельмейстеромъ балета",
"Старшій библіотекарь Центральной Музыкальной Библіотеки").

## 2026-08-28 — does rank_or_title text appear in tenure_note_text or heading_path (current DB, all 52 non-blank Musicians rows)

```sql
select page_id, list_number, family_name, rank_or_title, heading_path, tenure_note_text,
    case when tenure_note_text ilike '%' || rank_or_title || '%' then 1 else 0 end as in_tenure,
    case when heading_path ilike '%' || rank_or_title || '%' then 1 else 0 end as in_heading
from raw.person_entry
where entity_type = 'Musicians' and trim(coalesce(rank_or_title,'')) != ''
order by page_id, try_cast(list_number as integer);
```

Result: of 52 rows, 5 have the rank_or_title text literally inside
tenure_note_text, 4 have it inside heading_path, and 43 (83%) have it
in neither. Three distinct shapes identified: (1) heading-sourced —
Золотаренко/Герберъ/Кленовскій (`musicians_1891-92_MSK_p002`) match
heading_path ("Балетный оркестръ / Капельмейстеръ" etc.), correctly
absent from tenure_note_text since the title was printed as a
subheading above the entry, never after the name; (2) tenure-note-
sourced — Крейнъ ("Концертмейстеръ"), Сиборъ ("Солистъ балета"), and
one Цабель season (1895-96) match tenure_note_text, the title printed
as trailing text after the date/instrument; (3) the majority (43/52,
mostly recurring honorifics: Ауэръ/Направникъ/Цабель/Чіарлоне across
many seasons — "Солистъ Двора Его Императорскаго Величества",
"Заслуженный артистъ Императорскихъ театровъ") appear in neither
field. Not yet scan-verified where in the print these honorifics
actually sit (adjacent to the name before the date clause is the
leading hypothesis, given the one Цабель season that does capture it
in tenure_note_text) — open follow-up, not concluded.

## 2026-08-28 — is rank_or_title one kind of value or several? (RG: "rank and title don't seem like the same thing")

```sql
select entity_type, count(*) as n from raw.person_entry
where trim(coalesce(rank_or_title,'')) != '' group by 1 order by 2 desc;

select entity_type, rank_or_title, count(*) as n from raw.person_entry
where trim(coalesce(rank_or_title,'')) != '' and entity_type != 'Musicians'
group by 1,2 order by 1, 3 desc;
```

Result: non-blank counts by entity_type -- Administrators 1483,
TheaterSchoolStaff 543, ProductionTeam 70, BalletArtists 60,
Musicians 52. Content differs sharply by entity_type, confirming the
field genuinely holds several distinct kinds of value under one name:
(1) civil/court rank, Табель о рангахъ grades (ст. сов. 264, колл. сов.
230, надв. сов. 177, колл. асс. 122, тит. сов. 95, неимѣющій чина 94,
etc.) -- almost the entirety of Administrators, and a large share of
TheaterSchoolStaff; (2) honorific title (Солистъ Двора/Его
Императорскаго Величества, Заслуженный артистъ) -- all of Musicians,
much of BalletArtists; (3) subject taught, for TheaterSchoolStaff
specifically (Танцы 33, Музыка 19, Французскій языкъ 15, Исторія 9,
Рисованіе и чистописаніе 9...) -- overlapping with the dedicated
`subject_taught` column, an open question, not yet chased; (4)
workshop/department specialty, for ProductionTeam (Мужскіе парики,
Женскіе парики, Мужскіе/женскіе костюмы...) plus genuine honorifics
(профессоръ, академикъ); (5) company seniority ordinal, for
BalletArtists ("1-я"/"2-я"/"3-я"/"4-я" -- ranked position within the
troupe) plus dual-role notes ("(онъ же и режиссеръ)") and at least one
crossref note ("(см. СПБ. балетъ)"), mirroring the instrument crossref-
contamination pattern from issue #66.

## 2026-08-28 — correction: earlier "neither" shape-breakdown query undercounted due to NULL-propagation, not the ~ operator

An earlier ad-hoc query this session (not logged directly, shown only in
tool output) computed the instrument/rank_or_title "matches neither
tenure_note_text nor heading_path" bucket using raw `not (x ilike ...)
and not (y ilike ...)` WHERE conditions. Where `heading_path` is NULL,
`heading_path ilike '%...%'` evaluates to SQL NULL rather than false,
and `not NULL` is also NULL -- so the whole WHERE clause silently
excludes those rows instead of correctly counting them as "not
matching." This produced undercounts (rank_or_title: 36 instead of the
correct 43; instrument: 2725 instead of the correct 3752 total in that
bucket). Also checked in the same pass: build_duckdb.py's documented `~`
gotcha (known_issues.md, `instrument_clean` fix write-up) does NOT
reproduce on this specific pattern -- `~` and `regexp_matches()` agree
byte-for-byte here, confirmed by direct side-by-side query.

```sql
-- correct version, coalesce guards the NULL-propagation trap
select count(*) filter (where regexp_matches(coalesce(tenure_note_text,''), '^\(?съ [^.]+ г\.?\)?\.?$')) as bare_date,
       count(*) as total
from raw.person_entry
where entity_type = 'Musicians' and trim(coalesce(instrument,'')) != ''
  and not (coalesce(tenure_note_text,'') ilike '%' || instrument || '%')
  and not (coalesce(heading_path,'') ilike '%' || instrument || '%');
-- (same query with rank_or_title in place of instrument)
```

Result: instrument "neither" bucket, corrected: 3752 total (was
misreported as 2725), 3370 (90%) are a bare `(съ ... г.)` date with
nothing else appended. rank_or_title "neither" bucket, corrected: 43
total (was misreported as 36, though the 43 figure itself was already
correctly reported to RG earlier via a separate CASE-WHEN-based query,
not the buggy NOT() one), 40 (93%) bare-date-only. Both confirm the
print convention simply doesn't restate instrument/rank/title inside
the tenure-date sentence for the large majority of rows -- not a
per-row extraction gap.

## 2026-08-28 — final rank/title split: production verification

```sql
select count(*) filter (where rank_clean is not null) as rank_n,
       count(*) filter (where title_clean is not null) as title_n,
       count(*) filter (where rank_or_title_excluded_reason is not null) as excl_n
from analysis.person_entry;

select p.canonical_family_name, pa.season, pa.rank, pa.title
from research.person_appearance pa join research.person p on p.person_id=pa.person_id
where p.canonical_family_name = 'Крыловъ';

select status, count(*) from entities.person_candidate group by 1;
```

Result: production `outputs/full_run/imperial_theaters.duckdb` now matches
every dry-run exactly. `analysis.person_entry`: RANK 1688, TITLE 472,
EXCLUDED 48 (24 name-disambiguation ordinal, 24 dual-role/crossref note --
both relocated, not just tagged, see below). `research.person_appearance`
now has `rank`/`title` columns in place of `rank_or_title` (21154 rows,
unchanged). Крыловъ's corrected `rank` ("по найму, Московскій цеховой")
confirmed present on both seasons. `entities.person_candidate`: 0 pending,
23 rejected (clean, unaffected by this round).

## 2026-08-28 — scan verification of the 24 dual-role/crossref rows + the Крыловъ residual (RG: "Can we check these against the scans?")

Source PDFs became available mid-session (iCloud sync). Rendered and
visually checked one representative page per distinct person covering
all 24 dual-role/crossref rows (Вальцъ, Чекетти, Гельцеръ x2 phrasing
variants, Ивановъ 1-й, Аистовъ, Ширяевъ, Легатъ, Фарскій) plus the
Крыловъ residual, via `pymupdf` page render -> direct visual read.

Result: 9/9 people confirmed extraction accurate; critically, **print
order is NOTE then DATE** in every case (e.g. "Вальцъ, Карлъ Ѳедоровичъ
(онъ же и декораторъ) (съ 3 октября 1861 г.)"), the reverse of a naive
append -- this changed the relocation SQL to reconstruct that order.
Легатъ's row confirmed to have no date at all in print ("Легатъ, Николай
Густавовичъ (см. СПБ. балетъ)"), matching its NULL tenure_note_text.
"по найму, Московскій пеховой" (Крыловъ, 2 rows) confirmed an OCR
misread of "по найму, Московскій цеховой" (ForUpload_1902-03_Spisok_
Administration.pdf p.128, "Чиновники XII класса," entry 1) -- "цеховой"
(craft-guild/artisan estate) is a real word, "пеховой" is not.

## 2026-08-28 — Repertoire row-boundary smoketest: row-level extraction + cross-check vs full-page baseline on repertoire_1898-99_p003

```python
# cross-check: diff row-level extraction against existing full-page baseline
import json, csv
from pathlib import Path
baseline = json.load(open('outputs/full_run/raw/repertoire_1898-99_p003.raw.json'))
base_by_date = {}
for s in baseline['sessions']:
    base_by_date.setdefault(s['date_text'].strip().rstrip('.'), []).append(s)
# (row-level CSVs read from smoketest extract_out/, compared theater-by-theater)
```

Result: `row_detect.py` (unchanged, automatic) found 11 curves on this
page, missing 3 real boundaries (17/18, 22/23, 24/25 each merged into
one crop) rather than the spurious-split failure known_issues.md #51
documents. Ran row-level extraction anyway on the resulting 9 crops
(no human correction) via `pipeline/extract.py`: 12/12 real dates
correct against direct scan reading, zero fabrication, both dark days
(19, 26 Суббота) correctly flagged. Cross-check against the existing
full-page baseline: 0 disagreements across all 12 dates. Full write-up
in known_issues.md #51's 2026-08-28 addendum.

## 2026-09-01 — Repertoire spurious-curve investigation: multi-modal cross-check test + correction to #51's confirmed-page list

Not a database query -- pipeline/extraction testing, logged here per
the same "don't trust memory, verify" discipline. Full write-up in
known_issues.md #68. Summary: row-level-vs-full-page-baseline cross-
check on `repertoire_1898-99_p029` caught 9/15 real cell errors caused
by a spurious row-boundary curve, but missed 1 case where row-level and
column-level extraction independently made the identical wrong
attribution. Built new vertical-divider detection (transposed-image
reuse of `_detect_line_curves`) for column-wise extraction as a third
cross-check leg. Re-verifying the claim that triggered this test
surfaced a real error in the original #51 finding: `p029`'s "curve 12"
is actually a genuine printed rule (26 Пятница is compound), not
spurious -- removed from the confirmed list. Re-checked the other 6
pages with exact-curve-overlay-on-tight-crop precision (not wide
eyeball zoom); all 6 held up. Corrected confirmed-spurious list: 6
pages (p019, p028, p030, p036, p037, p039), not 7.

## 2026-09-08 — Can the spread-format seasons skip ScanTailor? Row-boundary detection measured against raw renders, 1893-94

Re-ran the 2026-08-26 ground-truth query (unchanged) to score a fresh
raw-render detection sweep against:

```sql
SELECT page_id, COUNT(DISTINCT date_text) AS n_dates
FROM raw.event_entry
WHERE page_id LIKE 'repertoire_1893-94_%'
GROUP BY page_id ORDER BY page_id;
```

Result: 12 pages, unchanged from 2026-08-26 — p000-p011 at 20/20/20/20/20/
19/20/**29**/19/18/20/19. p007's 29 is known-corrupt (issue #49: real page
ends Feb 3, ~20 dates; the raw JSON fabricates 12 dates past the end of the
physical page), so p007 is excluded from scoring below.

**Caveat on calling this "ground truth"**: these counts come from the
production extraction's own raw JSON, not from hand-transcribed gold —
none of the 12 gold pages are in the 1893-94 season. It is a proxy good
enough to detect gross under/over-detection, not a byte-exact standard.

**What was measured** (free, local, no API calls; rendered to a scratch
dir, nothing under `outputs/` touched): `ForUpload_1893-94_Repertoire.pdf`
re-rendered raw at 300dpi — NO ScanTailor — and `_detect_line_curves`
run over all 12 pages at three presence_frac values. Row count derived as
`n_curves - 2` (header_line_count=1).

| presence_frac | pages within ±1 of proxy truth (of 11) | diff range |
|---|---|---|
| 0.7 (old default) | 4 | -11 … +1 |
| 0.5 (current `detect_rows`) | 4 | -7 … +4 |
| 0.4 | 3 | -5 … +4 |

**Finding: the errors are page-to-page scatter, not a constant offset.**
At 0.5 the same season contains both p000 at -7 and p008 at +4. This
matters because a uniform miscount (e.g. if `header_line_count` is really
2 for this two-page-spread format rather than 1, which is not yet
confirmed) would shift every page by the same amount and is therefore
ruled out as the explanation. No single threshold fixes it: lowering to
0.4 trades under-detection for over-detection and scores slightly worse
overall.

**Conclusion**: raw renders are NOT a drop-in substitute for ScanTailor on
the two-page-spread seasons (1890-91–1897-98, 97 pages). This is
consistent with, and does not contradict, the post-1898-99 finding that
raw scans need no ScanTailor at all — those are a different physical
format (single page per city, table away from the binding fold).
Automating the manual step for the 97 spread pages therefore means
replacing what ScanTailor does (deskew + page-box crop + fill margins),
not simply dropping it.

## 2026-09-08 — Fold damage on the two-page-spread seasons: one row lost per spread, confirmed against the scan, and a 40x day-of-week failure rate split exactly at the format boundary

Follow-up to the same-day ScanTailor-independence work above. RG: "I am
prepared to go back and fill in any text that is obscured by the fold.
Just flag the text that is obscured."

**1. Direct scan-vs-database comparison, `repertoire_1893-94_p001`.**
Traced the fold, cropped it at native resolution, and read the printed
page directly against what the pipeline extracted.

Printed (confirmed by eye at native resolution, date column and
Маріинскій/Александринскій columns):

| printed date | Маріинскій | receipts |
|---|---|---|
| 22 Среда | Карменъ, оп. | 2857 р. 13 к. |
| **23 Четвергъ** | **Лоэнгринъ, оп.** | **in the fold** |
| 24 Пятница | Вражья сила, оп. | 2005 р. 60 к. |

What the database has:

```sql
SELECT e.date_text, e.theater, e.receipts_text,
       string_agg(p.performance_title, ' | ' ORDER BY p.performance_order)
FROM raw.event_entry e
LEFT JOIN raw.event_entry_performance p ON p.event_id = e.event_id
WHERE e.page_id = 'repertoire_1893-94_p001' AND e.theater = 'Маріинскій'
GROUP BY 1,2,3 ORDER BY min(e.event_id);
```

Result: `22 Четвергъ / Карменъ / 2857 р. 13 к.` then
`23 Пятница / Вражья сила / 2005 р. 60 к.` — the **`23 Четвергъ`
Лоэнгринъ row is absent entirely**, and every following date carries the
correct day-NAME with a day-NUMBER one lower than the print.

Confirmed the row is not merely misfiled elsewhere:

```sql
SELECT count(*) FROM raw.event_entry e
JOIN raw.event_entry_performance p ON p.event_id = e.event_id
WHERE p.performance_title LIKE '%Лоэнгринъ%'
  AND e.page_id LIKE 'repertoire_1893-94%';
```

Result: **0** on `p001` and **0 across the entire 1893-94 season**, for a
major repertory opera that is plainly printed on the page. Same check:
`Пиковая дама` 0 on p001 (8 elsewhere in the season), `Семейныя тайны`
0 on p001 (2 elsewhere).

So the fold does not merely clip a receipts figure — on this page it cost
the dataset **one entire dated row across all five theaters**, plus a
cascading one-day renumbering of every row after it.

**2. Does this generalize? Day-of-week verification rate by page format.**
`validate_performance_dates.py` already checks each date_text's day-number
against its printed day-name; a fold-induced dropped row shows up as drift.

```sql
SELECT CASE WHEN substr(e.page_id,12,7) < '1898-99' THEN 'spread' ELSE 'single' END era,
       count(*) cells,
       sum(CASE WHEN c.date_confidence = 'verified' THEN 1 ELSE 0 END) verified
FROM raw.event_entry e
JOIN analysis.event_entry_date_check c USING(event_id)
WHERE e.page_id LIKE 'repertoire_%' GROUP BY 1;
```

Result:

| era | cells | not verified |
|---|---|---|
| spread, 1890-91–1897-98 | 8,941 | **35.6%** |
| single-page, 1898-99–1907-08 | 14,931 | **0.9%** |

Per season the spread range is 21.8% (1890-91) to 62.9% (1892-93); the
single-page range is 0.1% to 3.0%. **A ~40x difference, splitting exactly
at the format boundary** — independent corroboration, from a check built
for an unrelated purpose, that the two-page-spread format is where the
damage is concentrated.

Breakdown of the 3,181 non-verified spread-season cells: 1,902
`corrected` (day-name/number drift the validator could resolve) and 1,279
`unresolved`/`intra_block_disagreement`/`unparseable`.

**Caveat, stated because it limits what the 3,181 means**: not all of it
is fold damage. It is a superset — fold-dropped rows and their
renumbering cascade, plus the pre-existing date bugs already tracked in
issues #48/#49, plus genuine printed closures. The fold-specific
population is much smaller and bounded: one obscured row per spread,
5 theater cells each, ~97 spreads => **on the order of 485 cells** for
hand-transcription.

**Method note (not a query)**: a mistaken first version of the era query
used `substr(page_id,13,7)`, which slices `'893-94_'` rather than
`'1893-94'` and collapsed every season into one bucket at 100% flagged.
Corrected to `substr(page_id,12,7)` — `'repertoire_'` is 11 characters.
The bad numbers were not used.

## 2026-09-09 — Do en dashes (U+2013) occur in the yearbooks at all?

Asked while establishing punctuation-fidelity conventions for the season-review
gold transcriptions (docs/season_reviews.md §7 forbids normalising dashes, so we
need to know which dashes actually occur).

```sql
WITH v AS (
  SELECT 'person_entry.tenure_note_text' AS fld, tenure_note_text AS t FROM raw.person_entry
  UNION ALL SELECT 'person_entry.credit_summary_text', credit_summary_text FROM raw.person_entry
  UNION ALL SELECT 'person_entry.family_name', family_name FROM raw.person_entry
  UNION ALL SELECT 'person_entry.rank_or_title', rank_or_title FROM raw.person_entry
  UNION ALL SELECT 'person_entry.heading_path', heading_path FROM raw.person_entry
  UNION ALL SELECT 'event_entry.theater', theater FROM raw.event_entry
  UNION ALL SELECT 'event_entry.date_text', date_text FROM raw.event_entry
  UNION ALL SELECT 'event_entry.annotation', annotation FROM raw.event_entry
  UNION ALL SELECT 'event_entry.receipts_text', receipts_text FROM raw.event_entry
  UNION ALL SELECT 'eep.performance_title', performance_title FROM raw.event_entry_performance
  UNION ALL SELECT 'pes.start_date_text', start_date_text FROM raw.person_entry_service
  UNION ALL SELECT 'pes.end_date_text', end_date_text FROM raw.person_entry_service
  UNION ALL SELECT 'pec.label', label FROM raw.person_entry_credit
  UNION ALL SELECT 'pec.role_name', role_name FROM raw.person_entry_credit
)
SELECT fld,
  SUM(length(t) - length(replace(t, chr(8212), ''))) AS em_2014,
  SUM(length(t) - length(replace(t, chr(8211), ''))) AS en_2013,
  SUM(length(t) - length(replace(t, chr(45),   ''))) AS hyphen_002D
FROM v GROUP BY fld;
```

Result: across all 14 verbatim text fields — **36,119 em dashes, 9,714 hyphens,
and 0 en dashes**. Not one, in any field.

Caveat noted at the time: this is the model's transcription, so it could in
principle reflect en→em normalisation by the model rather than the printed page.
Cross-checked against the hand-typed gold (below), which is independent.

## 2026-09-09 — Same question, checked against the hand-typed gold

Not SQL — a character count over `docs/eval/gold/*.csv`, which RG typed by hand
from the scans and which never passed through the model.

Result: **70 em dashes, 2,288 hyphens, 0 en dashes.** The generating scripts
(`_build_roster.py`, `_build_repertoire.py`) agree: 71 em, 1,181 hyphen, 0 en.

Two independent sources therefore agree that the en dash does not occur.

## 2026-09-09 — Which dash do year ranges use?

Prompted by my own (wrong) guess that spaced year ranges like "1894 — 1895" might
be en dashes.

```sql
SELECT t FROM (
  SELECT tenure_note_text AS t FROM raw.person_entry
  UNION ALL SELECT credit_summary_text FROM raw.person_entry
  UNION ALL SELECT annotation FROM raw.event_entry
) WHERE regexp_matches(t, '1[89][0-9][0-9]\s*[—–-]\s*1[89][0-9][0-9]');
```

Result: 9 matching strings, **all unspaced em dashes** (`Въ 1892—1893 учебномъ
году...`). No en dashes, no spaced variants. My earlier guidance to RG that en
dashes appear in number ranges was wrong and has been corrected.

## 2026-09-10 — does outputs/full_run/imperial_theaters.duckdb contain the column-wise Gate 3 Repertoire data?

```sql
select count(*) from raw.source_pages where entity_type='Repertoire';

select season, count(*) from raw.source_pages where entity_type='Repertoire'
group by season order by season;

select date_text, theater, time_of_day, event_status, receipts_text
from raw.event_entry where page_id='repertoire_1902-03_p024'
order by theater, date_text;
```

Result: 519 Repertoire pages present across all 18 seasons (including the
single-page-format ones this session's Gate 3 work covers), but
`imperial_theaters.duckdb`'s file mtime is 2026-08-28 -- before any of the
column-wise extraction work (which started ~2026-09-01) even existed. Spot
check on `repertoire_1902-03_p024` confirms this directly: the stored rows
use a "1 Февраль" date label and put the compound morning/evening split on
that date, with `Михайловскій театръ` marked `performed` (not dark) on
"8 Суббота" -- none of which matches the column-wise extraction's read of
the same page (date label "2 Воскрес.", compound split there instead, all
three theaters dark on "8 Суббота"). This is the OLD single-call full-page
baseline extraction (`run_pilot.py`'s default path), not the column-wise
Gate 3 output -- the two have never been parsed/loaded into this DB. All of
the column-wise/Gate 3 work this session lives only in the scratchpad
directory's raw JSON; `parse_and_validate.py` and `build_duckdb.py` have
not been run against any of it.

## 2026-09-11 — Gate 3 column-wise Repertoire corpus loaded into a fresh DuckDB; sanity-verified

After the completeness sweep (known_issues.md #69's final addendum),
ran `parse_and_validate.py --extraction-source columnwise` and
`build_duckdb.py` against `outputs/gate3_columnwise/raw_columnwise/`
(332 pages, single-page-format seasons 1899-00 through 1907-08) for
the first time -- output written to
`outputs/gate3_columnwise/imperial_theaters.duckdb`, a new database,
NOT a merge into `outputs/full_run/imperial_theaters.duckdb` (that
file predates all of this session's column-wise work, per the
2026-09-10 log entry above, and this run doesn't touch it).

```sql
SELECT COUNT(*) FROM raw.source_pages;
SELECT theater_canonical, COUNT(*) FROM analysis.event_entry GROUP BY 1 ORDER BY 2 DESC;
SELECT season, COUNT(*) FROM raw.event_entry GROUP BY 1 ORDER BY 1;
SELECT SUM(receipts_total_kopecks), AVG(receipts_total_kopecks)
  FROM analysis.event_entry WHERE receipts_total_kopecks IS NOT NULL;
```

Result: 332 source_pages (matches the corpus exactly). 6 theaters,
roughly balanced (Маріинскій 2660, Александринскій 2481, Большой 2373,
Новый 2354, Малый 2345, Михайловскій 2316). 8 seasons present, matching
the corpus's coverage exactly (1899-00 through 1907-08, no 1906-07 --
that season isn't part of Gate 3). 11,827 raw.event_entry rows, 11,122
raw.event_entry_performance rows. receipts_total_kopecks sums to
~11.8M rubles across the corpus with a plausible per-event average
(~1648 rubles). `parse_and_validate.py` logged 25 pages under
`repertoire_theater_spelling_fixed` -- all the already-documented,
benign Мариинскій->Маріинскій orthography-variant repair, not real
validation failures (confirmed by reading every row of
`validation_errors.csv`).

## 2026-09-11 — checking what a full_run merge would put at risk (design question, not data question, but the risk itself is factual)

```sql
-- old raw rows for the 332 Gate 3 page_ids, in the PUBLISHED full_run db
SELECT COUNT(*) FROM raw.event_entry e JOIN gate3_pages g USING(page_id);
SELECT COUNT(*) FROM raw.event_entry_performance p
  JOIN raw.event_entry e ON p.event_id = e.event_id
  JOIN gate3_pages g ON e.page_id = g.page_id;
-- entity-resolution work tied to those old performance rows
SELECT COUNT(*) FROM entities.work_link wl
  JOIN raw.event_entry_performance p ON wl.raw_performance_id = p.performance_id
  JOIN raw.event_entry e ON p.event_id = e.event_id
  JOIN gate3_pages g ON e.page_id = g.page_id;
-- published research layer for the same pages
SELECT COUNT(*) FROM research.event e JOIN gate3_pages g ON e.event_id LIKE g.page_id || '__%';
SELECT COUNT(*) FROM research.performance p JOIN research.event e ON p.event_id = e.event_id
  JOIN gate3_pages g ON e.event_id LIKE g.page_id || '__%';
SELECT COUNT(DISTINCT p.work_id) FROM research.performance p
  JOIN research.event e ON p.event_id = e.event_id
  JOIN gate3_pages g ON e.event_id LIKE g.page_id || '__%' WHERE p.work_id IS NOT NULL;
```

Result: `full_run`'s raw layer has 11,778 event_entry rows and 10,715
event_entry_performance rows for these 332 page_ids (the old, confirmed-
buggy single-call baseline extraction). 10,697 of those performance rows
are referenced by `entities.work_link` -- essentially all of them already
have entity-resolution crosswalk work done. The published `research`
layer carries 13,009 event rows and 10,697 performance rows for these
pages, resolving to 2,008 distinct `work` entities. A naive merge
(replace raw content, rebuild analysis/research on top) would orphan or
invalidate this existing linkage work for these 8 seasons unless done
carefully. Used directly to answer RG's "pros and cons of merging"
question.

## 2026-09-11 — full_run merge: verification queries at every stage

Full detail and rationale in known_issues.md #69's final addendum. The
core verification queries, run against both the pre-merge
`outputs/full_run/imperial_theaters.duckdb` and the merged
`outputs/full_run_merge_work/imperial_theaters_new.duckdb` before
swap-in:

```sql
-- untouched-page integrity (the 1,017 non-Gate3 pages)
SELECT COUNT(*) FROM raw.source_pages;
SELECT COUNT(*) FROM raw.event_entry e WHERE e.page_id NOT IN (<gate3 332 ids>);
SELECT COUNT(*) FROM raw.person_entry;
-- row-content diff on those same untouched pages (old vs new, ORDER BY event_id)
SELECT * FROM raw.event_entry WHERE page_id NOT IN (<gate3 332 ids>) ORDER BY event_id;

-- person-continuity check after build_entities.py
SELECT entry_id, person_id FROM entities.person_link;  -- old vs new: set-equal
SELECT COUNT(*) FROM entities.person_merge_log;         -- old vs new: unchanged
SELECT work_id, appearance_count FROM entities.work WHERE canonical_title = 'Евгеній Онѣгинъ';

-- research-layer comparison after build_research_model.py
SELECT COUNT(*) FROM research.theater;  SELECT COUNT(*) FROM research.person;
SELECT * FROM research.person_appearance ORDER BY 1,2,3;  -- old vs new: byte-identical
SELECT COUNT(*) FROM research.work; SELECT COUNT(*) FROM research.event;
SELECT COUNT(*) FROM research.performance;

-- spot check the corrected page landed right
SELECT date_text, theater, receipts_text, annotation FROM raw.event_entry
  WHERE page_id='repertoire_1903-04_p032' ORDER BY event_id;
```

Result: source_pages 1,349=1,349. Non-Gate3 event_entry 12,094=12,094
(exact), person_entry 21,168=21,168 (exact). 114 row-level diffs on
untouched pages, all explained by `{city, theater}` field changes
(a pre-existing city-fill-in and the Мариинскій->Маріинскій spelling
fix, not caused by this merge) -- zero unexplained. `person_link`
byte-identical (21,168 rows, set-equal), `person_merge_log` unchanged
(1,022=1,022). "Евгеній Онѣгинъ" work_id stable across the rebuild
(`788fd62c-a3cc-5103-9563-0475a531996c` both before and after),
appearance_count 361->366. `research.theater`/`person` unchanged
(6=6, 2,894=2,894), `person_appearance` byte-identical content.
`work`/`event`/`performance` shifted consistently with the Gate 3
corrections (4,530->4,412, 27,637->29,157, 24,892->25,316).
`1903-04_p032` confirmed showing three theaters with three correct,
distinct sets of receipts in the merged database. All of this was the
basis for proceeding with the swap-in described in known_issues.md.

## 2026-09-11 — full_run propagation (5 rounds batched): verification queries at every stage

Full detail and rationale in known_issues.md #69's final addendum.
Propagates today's five rounds (annotation audit, утро/вечер pairing,
stray-text sweep, event-date audit, shift-bug follow-up + truncated-
date restoration) from `outputs/gate3_columnwise/raw_columnwise/` into
`outputs/full_run/`, plus the new `_MANUAL_DATE_OVERRIDES` code change
in `validate_performance_dates.py`. Same lighter-weight in-place
methodology as the 2026-09-11 "propagate the 3 deferred-page fixes"
addendum (CREATE OR REPLACE / DROP+CREATE on every downstream script's
own tables), scaled up to all 332 Gate 3 pages via
`parse_and_validate.py --extraction-source columnwise` + splicing the
result into the existing merged `parsed/` CSVs by page_id, rather than
the 3-page shortcut used last time.

```sql
-- pre/post row counts, scratch copy vs live pre-patch db
select count(*) from raw.source_pages;                              -- 1349 = 1349
select count(*) from raw.person_entry;                              -- 21168 = 21168
select count(*) from raw.event_entry where page_id not in (<332 gate3 ids>);  -- 12094 = 12094
select count(*) from raw.event_entry where page_id in (<332 gate3 ids>);     -- 11829 -> 11842
-- full row-content diff on the 12094 untouched-page rows (ORDER BY event_id)
select event_id, page_id, season, city, date_text, month_text, year_text,
       date_undate, time_of_day, theater, event_status, receipts_text,
       receipts_rubles, receipts_kopecks, annotation
  from raw.event_entry where page_id not in (<332 gate3 ids>) order by event_id;
-- orphaned performance rows / duplicate event_ids (sanity net)
select count(*) from raw.event_entry_performance p
  left join raw.event_entry e on e.event_id = p.event_id where e.event_id is null;
select event_id, count(*) from raw.event_entry group by event_id having count(*) > 1;
-- person-continuity after build_entities.py
select count(*) from entities.person_link;         -- 21168 = 21168
select count(*) from entities.person_merge_log;     -- 1022 = 1022
select count(*) from entities.person;               -- 4359 = 4359
select entry_id, person_id from entities.person_link;  -- old vs new: set-equal
-- research layer after build_research_model.py
select count(*) from research.theater;   -- 6 = 6
select count(*) from research.person;    -- 2894 = 2894
select * from research.person_appearance order by 1,2,3;  -- old vs new: byte-identical (21154 rows)
select count(*) from research.work;         -- 4410 -> 4451
select count(*) from research.event;        -- 29141 -> 29219
select count(*) from research.performance;  -- 25313 -> 25466
-- _MANUAL_DATE_OVERRIDES landed correctly
select event_id, date_confidence, corrected_date_undate, note
  from analysis.event_entry_date_check where date_confidence = 'corrected_manual';  -- 9 rows, all correct
-- spot check a specific corrected page
select date_text, time_of_day, event_status from raw.event_entry
  where page_id = 'repertoire_1902-03_p019' and theater like '%Больш%' order by event_id;
```

Result: every check above passed exactly as annotated. 0 unexplained
diffs on untouched pages (better than the original merge's 114
explained-but-nonzero diffs -- no concurrent unrelated change this
time). Swapped `imperial_theaters.duckdb` + `research_dataset.sqlite` +
`parsed/` into `outputs/full_run/` via move-aside-then-replace, `cmp`
confirmed the live files byte-identical to the verified scratch copy,
then deleted the pre-patch snapshot and scratch working directory.

## 2026-09-11 — date_undate coverage gap: page-header extraction + verification

Full detail in known_issues.md #69's final addendum. Closing the date_undate
coverage gap (13-21% fill for column-wise seasons vs ~100% baseline) via a
small targeted re-extraction of each page's own printed header date range
(pipeline/extract_page_headers.py), not a full re-extraction. Key checks:

```sql
-- header dataset self-consistency (before trusting it)
-- regex parse rate, season/year cross-check, and day-range vs raw JSON's
-- own first/last day-number cross-check -- all done in Python against
-- outputs/gate3_columnwise/page_header_dates.csv, not SQL (see script)

-- fill-rate before/after (test parse, not yet in outputs/full_run/)
SELECT count(*), count(date_undate) FROM raw.event_entry;  -- gate3-only test db

-- weekday-consistency before/after the validate_performance_dates.py fixes
-- (_DOW_PREFIXES short forms, whitespace-tolerant matching, parsed-weekday
-- grouping instead of raw-string grouping) -- Python, reusing
-- pipeline.validate_performance_dates._parse_dow/_true_weekday directly

-- full propagation verification (same shape as the earlier 5-round merge):
SELECT count(*) FROM raw.source_pages;                              -- 1349=1349
SELECT count(*) FROM raw.event_entry WHERE page_id NOT IN (<gate3>); -- 12094=12094, 0 diffs
SELECT event_status, count(*) FROM research.event GROUP BY 1;
  -- performed/no_performance byte-identical (18427, 5509); only
  -- not_captured changed (5283 -> 3934, fewer/more-accurate synthesized
  -- gaps now that date ranges are reliable)
SELECT entry_id, person_id FROM entities.person_link;  -- old vs new: set-equal
SELECT * FROM research.person_appearance ORDER BY 1,2,3;  -- byte-identical
SELECT event_id, date_confidence, corrected_date_undate
  FROM analysis.event_entry_date_check WHERE date_confidence='corrected_manual';
  -- all 9 rows present with the scan-verified dates
```

Result: date_undate fill for the 332 Gate 3 pages 13-21% -> 100%. Weekday-
verified rate on those same pages 85.8% -> 99.3% after also fixing two
`validate_performance_dates.py` limitations the coverage fix exposed for
the first time (short weekday abbreviations not in `_DOW_PREFIXES`, and
raw-string instead of parsed-weekday grouping for cross-theater block
agreement). 33 residual rows (0.3%) are genuine: 3 already-known
verbatim typos (`corrected_manual`) and a handful of newly-visible,
genuinely rare OCR letter-transposition artifacts, correctly left
flagged rather than guessed at. Full corpus (all 1,349 pages):
non-gate3 rows exactly byte-identical (0 diffs), entities/person
continuity exactly preserved, research.performance/work/person/theater
unchanged, only `research.event`'s synthesized `not_captured` gap count
changed (explained above, not a real-data change). Swapped into
outputs/full_run/ via move-aside-then-replace, `cmp`-confirmed
byte-identical to the verified scratch copy, cleaned up.

## 2026-09-11 — 1901-02_p018 whole-column fix: verification + propagation

Full detail in known_issues.md #69's final addendum.

```sql
-- duplicate check on the touched page before/after
-- (Python, Counter over (theater, date_text, session))

-- full propagation verification, same shape as every earlier round today
SELECT count(*) FROM raw.event_entry WHERE page_id NOT IN (<gate3 332 ids>);  -- 12094=12094, 0 diffs
SELECT entry_id, person_id FROM entities.person_link;  -- old vs new: set-equal
SELECT * FROM research.person_appearance ORDER BY 1,2,3;  -- byte-identical
SELECT theater, date_text, time_of_day, annotation FROM raw.event_entry
  WHERE page_id='repertoire_1901-02_p018' AND theater LIKE '%Михайл%';
```

Result: all 11 affected sessions (16 Воскрес. morning+evening plus the
10 other dates on the same Михайловскій театръ column) now carry the
real title in a performance row and only a genuine note (or nothing)
in `annotation`. Non-gate3 rows exactly byte-identical, entities/person
continuity preserved, person_appearance byte-identical. Swapped into
outputs/full_run/, cmp-confirmed, cleaned up.

## 2026-09-15 — Рюминъ extraction error on gold page theaterschoolstaff_1899-00_p000 (production ID: …1899-90_p000; known_issues #71): first 6 raw rows of that page

```sql
SELECT entry_id, list_number, family_name, first_name, patronymic, heading_path, rank_or_title, tenure_note_text
FROM raw.person_entry WHERE page_id = 'theaterschoolstaff_1899-90_p000' ORDER BY entry_id LIMIT 6
```

Result: e001 (Управляющій Училищемъ) has family_name='Ивановичъ', first_name='Иванъ', patronymic='Ивановичъ', rank 'д. ст. сов., въ званіи гофмейстера', tenure 'съ 27 мая 1887 г.). † 2 сентября 1899 г.'. The raw JSON (outputs/full_run/raw/theaterschoolstaff_1899-90_p000.raw.json, entries[0]) has the same values, so this is model output, not a parse artifact. The scan prints the surname letter-spaced: «Р ю м и н ъ, Иванъ Ивановичъ».

## 2026-09-15 — every raw appearance matching Рюмин in any name field

```sql
SELECT r.entry_id, sp.season, r.family_name, r.first_name, r.patronymic, r.heading_path, r.tenure_note_text
FROM raw.person_entry r JOIN raw.source_pages sp USING (page_id)
WHERE r.family_name LIKE '%Рюмин%' OR r.first_name LIKE '%Рюмин%' OR r.patronymic LIKE '%Рюмин%'
ORDER BY sp.season, r.entry_id
```

Result: 30 rows. 22 are Рюминъ, Иванъ Ивановичъ, TheaterSchoolStaff, 1890-91 through 1899-90: 10 as Управляющій (1890-91 to 1898-99) and 12 as Почетный членъ (including theaterschoolstaff_1899-90_p003__e005 with '† 2 сентября 1899 г.'). The other 8 are an unrelated Бестужевъ-Рюминъ, Алексѣй Ивановичъ (Administrators, 1902-03 to 1907-08). The 1899-00 Управляющій appearance is missing from this list, which is the extraction error.

## 2026-09-15 — research-layer effect: first 4 person_appearance rows on that page

```sql
SELECT pa.appearance_id, pa.season, p.display_name, p.person_id
FROM research.person_appearance pa JOIN research.person p USING (person_id)
WHERE pa.appearance_id LIKE 'theaterschoolstaff_1899-90_p000__e00%' ORDER BY 1 LIMIT 4
```

Result: e001 resolves to person 2f34649f… 'Ивановичъ, Иванъ Ивановичъ', not to Рюминъ.

## 2026-09-15 — research.person records with family name Ивановичъ or Рюминъ

```sql
SELECT p.person_id, p.display_name, p.first_attested_season, p.last_attested_season, count(*) AS n_appearances
FROM research.person p JOIN research.person_appearance pa USING (person_id)
WHERE p.canonical_family_name IN ('Ивановичъ','Рюминъ') GROUP BY ALL ORDER BY n_appearances DESC
```

Result: 2 rows. Рюминъ, Иванъ Ивановичъ (24f7fc76…, 1890-91 to 1899-90, 22 appearances). Phantom person Ивановичъ, Иванъ Ивановичъ (2f34649f…, 1899-90 only, 1 appearance).

## 2026-09-15 — entity-review traces for the phantom and for Рюминъ

```sql
SELECT * FROM entities.person_candidate WHERE display_1 LIKE '%Ивановичъ, Иванъ%' OR display_2 LIKE '%Ивановичъ, Иванъ%' OR display_1 LIKE 'Рюминъ%' OR display_2 LIKE 'Рюминъ%';
SELECT count(*) FROM entities.person_merge_log WHERE display_1 LIKE 'Рюминъ%' OR display_2 LIKE 'Рюминъ%';
```

Result: 1 candidate, 'Ивановичъ, Иванъ Ивановичъ' vs 'Ивановъ, Иванъ Ивановичъ' (family_name_variant, score 0.78), status rejected (conflicting_dates). No candidate ever paired the phantom with Рюминъ. Merge log: 1 row involving Рюминъ.

## 2026-09-15 — corpus-wide check: family_name identical to patronymic (patronymic-as-surname shape)

```sql
SELECT r.entry_id, r.family_name, r.first_name, r.patronymic, r.heading_path
FROM raw.person_entry r
WHERE r.family_name IS NOT NULL AND r.patronymic IS NOT NULL
  AND trim(r.family_name) = trim(r.patronymic)
ORDER BY r.entry_id
```

Result: 2 rows. theaterschoolstaff_1899-90_p000__e001 (the Рюминъ case), plus balletartists_1898-99_MSK_p001__e020 'Джурі, Адель, patronymic=Джурі', which is a different shape (surname copied into patronymic). This detector only catches a dropped surname when the patronymic was also captured.

## 2026-09-15 — publish-readiness check: research-layer row counts, duckdb vs. sqlite, full_run vs. full_run_seasonfix

Run read-only against both `outputs/full_run/` and `outputs/full_run_seasonfix/`
(`imperial_theaters.duckdb` and `research_dataset.sqlite` in each).

```sql
-- per table t in (theater, work, person, event, performance, person_appearance),
-- in DuckDB (research.t) and in the SQLite export (t):
SELECT count(*) FROM research.{t};
SELECT count(*) FILTER (WHERE season LIKE '1899-90%' OR season LIKE '1905-07%') AS typo_rows
  FROM research.person_appearance;
SELECT min(season), max(season), count(DISTINCT season) FROM research.event;
SELECT DISTINCT schema_name FROM duckdb_tables() ORDER BY 1;
```

Result: identical counts in both run dirs and in both file formats — theater 6,
work 4,456, person 2,894, event 27,870, performance 25,480, person_appearance
21,154; event seasons 1890-91..1907-08 (18). Only difference: season-typo rows
in person_appearance = 281 in full_run, 0 in full_run_seasonfix (known_issues #71).
Both DuckDB files contain raw/analysis/entities/research schemas.

## 2026-09-16 — state of Repertoire data: is the spread-season column-bleed fix (known_issues #70) reflected in production yet?

Read-only against `outputs/full_run/imperial_theaters.duckdb` (last built 2026-09-11, per file mtime -- predates all of this week's split/column-bleed fix work).

```sql
SELECT regexp_extract(page_id, 'repertoire_([0-9]{4}-[0-9]{2})', 1) AS season,
       count(*) AS n_pages
FROM raw.source_pages
WHERE page_id LIKE 'repertoire_%'
GROUP BY 1 ORDER BY 1;

SELECT count(*) FROM raw.source_pages WHERE page_id LIKE 'repertoire_%';
SELECT count(*) FROM raw.event_entry e JOIN raw.source_pages p ON e.page_id = p.page_id
  WHERE p.page_id LIKE 'repertoire_%';

SELECT page_id FROM raw.source_pages WHERE page_id LIKE 'repertoire_1895-96%' ORDER BY page_id;
```

Result: 1890-91..1897-98 (the 8 spread seasons) show only 9-13 `source_pages`
rows each -- matching the ORIGINAL, UNSPLIT whole-spread-image page count
(sequential render order, e.g. `repertoire_1895-96_p000`..`p012`), not the
176 real-printed-page-numbered split halves this week's work produced. This
confirms production still holds the OLD whole-spread-image extraction for
these 8 seasons (the one originally measured at 14-63% receipts agreement,
the reason the split-page approach was built at all) -- none of this week's
split + column-bleed-fix work (outputs/repertoire_spreadfix_v6/) has been
parsed, validated, or built into any duckdb yet, let alone promoted into
outputs/full_run. 1898-99..1907-08 (the single-page-format seasons) show
38-50 pages each, consistent with the already-resolved Gate 3 332/332 state.
Total repertoire source_pages = 519; total event_entry rows joined to a
repertoire page = 23,936 (a mix of good single-page-format data and the
known-poor spread-season baseline).

## 2026-09-17 — readiness check before build_duckdb.py: are the 6 single_leaf pages (non-spread landscape leaves within the 8 spread seasons) covered by outputs/repertoire_spreadfix_v6?

```sql
select page_id, count(*) from raw.event_entry
where page_id in (
  'repertoire_1890-91_p000','repertoire_1890-91_p012','repertoire_1894-95_p008',
  'repertoire_1895-96_p012','repertoire_1896-97_p012','repertoire_1897-98_p012'
)
group by page_id;
-- run against outputs/full_run/imperial_theaters.duckdb
```

Result: full_run has 45/14/40/50/50/40 = 239 events total across these 6
pages (old extraction method). outputs/repertoire_spreadfix_v6/manifest.csv
has ZERO entries for these page_ids (confirmed: no non-"pairNNN" rows at
all) -- these 6 pages were never carried into this build's parse_raw/ or
manifest.csv. 5 of the 6 already have raw_columnwise/*.raw.json extraction
done (real content, e.g. 1894-95_p008 shows 73 sessions vs full_run's 40
events for the same page -- the new extraction looks meaningfully more
complete, consistent with this whole arc's findings elsewhere). The 6th
(1890-91_p000) has no raw_columnwise extraction at all yet. Not a "ready to
build" blocker for data that already exists in full_run, but a real scope
gap if repertoire_spreadfix_v6 is meant to stand alone as a complete
8-season replacement -- flagged to RG before proceeding to build_duckdb.py.

## 2026-09-17 — post-build sanity check on outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb

```sql
select count(*) from raw.event_entry;
select count(*) from raw.event_entry_performance;
select count(distinct page_id) from raw.event_entry;
select season, count(*) from raw.event_entry group by season order by season;
```

Result: 4161 event_entry rows, 5342 event_entry_performance rows, 89
distinct pages -- all matching parse_and_validate.py's output exactly.
All 8 seasons (1890-91 through 1897-98) represented with plausible counts
(361-701 events/season). `analysis.event_entry` built with 0 not_captured
completeness gaps. First scratch database built from repertoire_
spreadfix_v6 -- not promoted over outputs/full_run, that stays a separate
decision.

## 2026-09-17 — spot-check found session-label duplicates; verify fix + rebuild

```sql
select count(*) from raw.event_entry;
select count(*) from raw.event_entry_performance;
select date_text, theater from raw.event_entry
  where page_id='repertoire_1893-94_pair006' and date_text='14 Четвергъ.' and theater='Большой';
```

Result: post-fix rebuild -- 4153 events (was 4161, -8 matching the 8 removed
duplicate sessions), 5330 performances (was 5342, -12). Spot-checked
`1893-94_pair006`'s day-14 Большой row: now 2 sessions (morning+evening),
not 3 -- confirms the duplicate ('Снѣгурочка' appearing under both
`evening` and a redundant `unspecified` session) is gone from the rebuilt
database.

## 2026-09-17 — blank-genre audit + a whole-page duplicate found and removed

```sql
select count(*) from raw.event_entry_performance where genre is null;
-- plus targeted title-pattern queries to find embedded genre suffixes
-- with genre=NULL, and a page_id/date_text/theater cross-reference to
-- confirm repertoire_1895-96_pair012 duplicated repertoire_1895-96_p012
```

Result: 226 null-genre rows audited; ~206 confirmed legitimate (excerpt/
act markers, anthems, named-reciter "Сцена г. X" pieces, benefit-notice
titles -- genre genuinely doesn't apply). 24 were real drops, fixed (20
where the title already carried its own genre suffix per this corpus's
convention but the separate field was empty, 4 more found via a broader
suffix search). While investigating one of those (traced to
`repertoire_1895-96_p012`, a single_leaf page fixed earlier this session)
found `repertoire_1895-96_pair012` was a COMPLETE duplicate of it -- same
10 (date, theater) pairs, same content, just older/lower-quality
(garbled "free admission" notice fragments where the single_leaf fix has
clean text). Checked the 4 other "pairNNN" ids that also cite a
single_leaf render page as a source and found 0 date/theater overlap for
all 4 (genuinely different real content, a `_source`-label coincidence,
not a duplicate) -- confirmed via spot-checking actual titles/dates, not
assumed. Removed `repertoire_1895-96_pair012` from manifest.csv/
parse_raw/. Final: 4,143 events (-10) / 5,317 performances, 88 distinct
pages (was 89), 0 validation errors, 152 quality flags (unchanged).

## 2026-09-17 — titles field audit: 57 truncation/merge fixes, verified build

```sql
-- python-side scan: distinct performance_title values starting with a
-- lowercase letter (a real title is always capitalized), then for each
-- searched all distinct titles ending in the same tail for a fuller match
```

Result: 42 lowercase-starting titles found, cross-referenced against the
rest of the corpus for a clean, complete match. ~53 fixed via clear or
well-supported matches (many recurring truncations of common titles:
Плоды просвѣщенія, Конекъ-горбунокъ, Русланъ и Людмила, Тщетная
предосторожность, etc.). Investigating one garbled cluster
(`repertoire_1894-95_pair008`'s Большой column) traced to the same stale
extraction abandoned earlier this session for the single_leaf `1894-95_
p008` page -- confirmed via matching receipts figures/annotations
byte-for-byte with the discarded raw dump. Fixed the recoverable titles
on that column individually (Мелузина, Демонъ [medium confidence, 53
clean occurrences vs Манонъ's 8], Русланъ и Людмила, etc.); the
column's ANNOTATION field is also garbled there (separate finding,
flagged for later, out of scope for a titles-only pass). Final: 4,143
events (unchanged) / 5,316 performances (-1, the Евге+Онѣгинъ merge), 0
validation errors, 152 quality flags (unchanged). 11 titles left
genuinely unresolved (documented, not guessed) -- no corpus match and no
scan available.

## 2026-09-17 — tracked down real scans for the 8 remaining unresolved titles

Result: all 8 resolved. `repertoire_1891-92_pair012` (4 rows) traced to
printed pages 12-13 (`pdf/RepertoireTables/ForUpload_1891-92_Repertoire_005.jpg`).
`repertoire_1894-95_pair008` (4 rows) traced to printed pages 8-9
(`ForUpload_1894-95_Repertoire_003.jpg`). Two of the 8 ('карт.', 'фарсъ'
standalone) turned out to be duplicate genre-marker artifacts, not lost
titles at all -- removed. Two more ('хъ, ком.', 'къ дѣлу, сц.') were each
actually two merged works with a title from one and a genre from the
other -- split into 4 correctly-paired works. The other 4 were ordinary
truncations, recovered in full ('Соль супружества' x2, 'Фаустъ, оп.',
and 'Бенефисъ г. Садовскаго.'/'Лѣсъ, ком.'/'Спириты, вод.' disentangled
from one merged fragment). 0 lowercase-starting titles remain corpus-wide.

## 2026-09-17 — annotation field audit, 35 fixes total

Result: 386 non-blank annotations checked. 19 lowercase-starting ones
found (same truncation signal used for titles) -- resolved into 24 row
fixes (most were a truncated SECOND work title that belonged in `works`,
not `annotation`; one was a legitimate special-notice phrase recovered
in full; a few needed splitting a genuinely merged title+genre pair).
Separately, the already-known garbled `repertoire_1894-95_pair008`
Большой-column cluster (11 total spurious annotations across two
render-page sources, p008 and p009) was resolved by locating both source
scans (printed pp.8-9 and 9-10) -- confirmed EVERY one of the 11 has NO
real counterpart in the source at all (the Большой column is genuinely
blank there; the garbled text is bleed from the neighboring Малый
column's own real content) -- cleared rather than reconstructed. Final:
4143 events (unchanged), 5342 performances (+25 net, mostly recovered
works), 0 validation errors, quality_flags.csv unchanged.

## 2026-09-17 — receipts field audit: kopecks-marker parsing bug + a fully corrupted theater column found

```sql
select receipts_text, receipts_rubles, receipts_kopecks from raw.event_entry
where receipts_kopecks is not null and receipts_kopecks != ''
and try_cast(receipts_kopecks as integer) is null;
```

Result: found the kopecks-side twin of the rubles-marker bug fixed earlier
this session -- `_parse_receipts`'s `.replace("к.", "")` required the
literal period, silently leaving "70 к" (no period) unstripped in
receipts_kopecks for 7 rows. Fixed with the same `\b`-bounded regex
approach used for the rubles marker. Checking the 8 "truncated leading
digit" receipts_parse_failed cases (all on repertoire_1894-95_pair008,
Михайловскій) against the scan already open from earlier fixes revealed
this wasn't truncation at all -- the entire Михайловскій column for 10
consecutive dates (6-15 Января) had been corrupted: every row duplicated
a NEIGHBORING theater's title (Большой's "Мелузина", "Донъ Жуанъ", etc.)
with receipts truncated to match. Rebuilt all 10 sessions directly from
the scan (both source pages, ForUpload_1894-95_Repertoire_003.jpg).
Spot-checked dates 16-25 on the same column against the scan too --
confirmed genuinely clean, corruption was isolated to exactly 6-15
Января. One receipts figure (15 Воскрес.) left partially unresolved --
its leading rubles digits are genuinely illegible in the scan, obscured
by page curvature right at the binding fold; documented, not guessed.
Final: 4143 events (unchanged), 5353 performances (+11 net), 0
validation errors, receipts_parse_failed 50->43 (7 resolved, 1 already-
documented illegibility remains). Rebuilt and re-verified
imperial_theaters.duckdb.

## 2026-09-17 — event_status field audit

Result: only 2 distinct values ('performed'/'no_performance'), correctly
derived from is_dark. Checked both directions for inconsistency: (a)
'performed' events with zero works/annotation/receipts -- 0 found; (b)
'performed' events with zero works but SOME annotation/receipts -- 23
found, mostly legitimate (concert/benefit notices with no titled work),
but 5 were real work titles misplaced in annotation (matching the
embedded-genre-suffix signal from the earlier title audit) -- 3 fixed
with high confidence via clean corpus duplicates (Майская ночь/оп.,
Гибель Содома/др., Парадный спектакль./Спящая красавица split), 2 left
unresolved (no corpus match, no receipts to cross-reference: 'Отечественный',
'Для воспитанницъ и воспитанниковъ'); (c) 'no_performance' events with
actual content -- exactly 56, matching the already-documented
dark_row_with_content flag count precisely (the known Большой-column
bleed pattern, not a new issue). Final: 4143 events (unchanged), 5356
performances (+3), 0 validation errors, quality_flags.csv unchanged.

## 2026-09-17 — resolved all 56 dark_row_with_content flags (Большой-column bleed)

Result: RG asked to address the 56 no_performance-with-content flags
confirmed as the known Большой-column bleed pattern. Scoped: 100%
Большой theater, across 9 pages. Two rows turned out to be genuinely
misclassified (is_dark=true but real, clean content -- 'Робертъ и
Бертрамъ, бал.' and a 'Концертъ въ пользу инвалидовъ.' notice) -- fixed
to is_dark=false. One row was wrongly cleared as bleed at first glance
but the scan showed real content ('3 Воскр.', 'Севильскій цирюльникъ,
оп.', 2134 р. 20 к.) -- recovered instead of cleared. The remaining 53
were confirmed genuine bleed via direct scan checks across all 9 pages
(Большой column entirely blank for the whole date range on every page
checked, with the garbled fragments matching Малый's real neighboring
content word-for-word) -- cleared. Final: 4143 events (unchanged), 5357
performances (+1, the recovered Севильскій цирюльникъ), 0 validation
errors, dark_row_with_content flag count 56 -> 0, total flags 145 -> 89.
Rebuilt and re-verified imperial_theaters.duckdb.

## 2026-09-17 — closed 42 of the last 43 receipts_parse_failed flags (Latin p/k marker gap)

Result: RG asked to revisit the remaining 43 receipts_parse_failed flags.
42 were the already-known "Latin p/k substitution" category (9 of which
turned out to be mixed-script, Latin "p." paired with Cyrillic "к.",
previously miscounted as part of the same bucket by a too-strict check).
Reconsidered whether this deserved a code fix (like the genre field's
Latin/Cyrillic variants, left alone) vs treating it as a genuine parsing
gap (like the two dropped-period fixes earlier this session) -- concluded
it's the latter: unlike genre, these are DERIVED numeric fields that come
back completely empty when the marker is Latin, not just a differently-
scripted but equally complete value. Widened _RUBLES_MARKER_RE/
_KOPECKS_MARKER_RE to accept Latin p/k (case-insensitive) as well as
Cyrillic р/к, verified against 7 synthetic edge cases (mixed script, bare
figures, and confirming Cyrillic words like "карт."/"играю" still don't
false-match) before trusting it, then against the whole corpus (0 -> 1
remaining failure, the one already-documented genuine illegibility case).
Final: 4143 events / 5357 performances (unchanged, code-only fix),
0 validation errors, receipts_parse_failed 43 -> 1, total quality flags
89 -> 47. Rebuilt and re-verified imperial_theaters.duckdb; spot-checked
recovered values directly against the database.

## 2026-09-17 — resolved zero_dark_cells_on_multiweek_page (4 pages, missing theater columns)

```sql
-- verification query run after the fix, against the rebuilt duckdb
select theater, count(distinct date_text) as ndates, count(*) as nrows
from raw.event_entry where page_id = ?
group by theater order by theater
-- run once per page_id in
-- ('repertoire_1890-91_pair004','repertoire_1895-96_pair014',
--  'repertoire_1895-96_pair016','repertoire_1896-97_pair014')
```

Result: RG asked to check the 4 `zero_dark_cells_on_multiweek_page` flags.
The check's own name was misleading -- these pages weren't lacking dark
cells, they were missing 3-4 of 5 theater columns ENTIRELY from
`parse_raw` (not garbled, not bled-into, just never captured). Confirmed
via `_source` cross-check across every other page in each season that no
other page had absorbed the missing theaters' data -- genuinely lost, not
misattributed. Traced each page's real printed-page scan (the usual
render-vs-printed-page-number ambiguity: `_source` cites e.g.
`repertoire_1895-96_p014`, which is the PRINTED page number, not a
render-sequential index -- confirmed against
`split_page_numbers_final.csv` for the 1896-97 case, by direct visual
match for the other two seasons which predate that CSV's coverage) and
transcribed the missing theaters' sessions directly from the scan:

- `repertoire_1890-91_pair004` (10→50 sessions): 4 theaters recovered
  across 10 dates, 10-21 September 1890 -- printed p. 5
  (ForUpload_1890-91_Repertoire_001.jpg, bottom half). [Done earlier this
  session, propagated together with the other 3 in this pass.]
- `repertoire_1895-96_pair014` (12→81 sessions): 4 theaters recovered
  across 12 dates, 30 Дек 1895 - 11 Янв 1896 -- printed pp. 14-15
  (ForUpload_1895-96_Repertoire_006.jpg). One row (7 Января) has receipts
  genuinely illegible corpus-wide across multiple columns where the
  binding crease runs directly under the printed figures -- left null
  rather than guessed, matching the page's own existing (pre-fix)
  Mikhaylovsky null for that exact row.
- `repertoire_1895-96_pair016` (25→72 sessions, full rebuild not just an
  addition): this page turned out to have a SECOND, independent defect
  layered on top of the missing columns -- its existing Malyy/Mariinsky
  sessions carried systematically wrong date_text/session labels (content
  from several different calendar dates had been merged onto a handful of
  date labels, e.g. the old "26 января." session spliced together Malyy
  content that really belongs to 24 Среда. with Mariinsky content that
  really belongs to 28 Воскресенье.). Rebuilt the full date range
  24 Января - 2 Февраля 1896 from the scan (ForUpload_1895-96_Repertoire_007.jpg,
  printed pp. 16-17), re-keyed every session to its correct calendar date,
  each cross-verified via an exact receipts-figure match against the old
  mislabeled entry it replaced. One pre-existing entry -- Malyy, 30
  Вторникъ. evening, annotation "Для воспитанницъ и воспитанниковъ",
  works=[] -- could not be corroborated anywhere in the scan for that
  date/theater (both real rows for that slot are fully accounted for by
  ordinary paid performances with receipts) and was removed as
  uncorroborated rather than kept; resolves
  genre-field-3-inferred-rows-followup.md item 6.
- `repertoire_1896-97_pair014` (10→73 sessions): 4 theaters recovered
  across 10 dates, 19-31 Декабря 1896 -- printed pp. 14-15
  (ForUpload_1896-97_Repertoire_006.jpg). Clean page, no date-mislabeling
  found here (unlike the 1895-96 case above).

Re-ran parse_and_validate.py + quality_checks.py + build_duckdb.py.
Final: 4143 -> 4359 events, 5357 -> 5649 performances, 0 validation
errors (one pre-existing, unrelated informational
`repertoire_fabricated_dropped` log line on `repertoire_1890-91_p012`,
not a failure). Quality flags: 47 -> 5 -- `zero_dark_cells_on_multiweek_page`
4 -> 0 as directly targeted, and as a side effect
`cross_theater_date_mismatch` also dropped 38 -> 0 (those mismatches were
almost entirely a downstream symptom of the same missing-column pages).
Remaining 5 flags (`duplicate_event_key` x4, `receipts_parse_failed` x1)
are all pre-existing, on unrelated pages
(`repertoire_1894-95_pair006`/`pair008`, `repertoire_1897-98_pair016`/
`pair020`), untouched by this fix. Rebuilt and verified
imperial_theaters.duckdb directly (all 4 pages now show all 5 theaters
present for every date).

## 2026-09-17 — checked the 3 remaining inferred-genre rows from genre-field-3-inferred-rows-followup.md

```sql
-- verification, run against the rebuilt duckdb after applying the fixes below
select ee.date_text, ee.time_of_day, ee.receipts_text, eep.performance_title, eep.genre
from raw.event_entry ee join raw.event_entry_performance eep using(event_id)
where ee.page_id='repertoire_1897-98_pair006' and ee.theater='Малый'
  and ee.date_text in ('12 Воскрес.','16 Четв.');

select ee.date_text, ee.receipts_text, eep.performance_title, eep.genre
from raw.event_entry ee join raw.event_entry_performance eep using(event_id)
where ee.page_id='repertoire_1894-95_pair004' and ee.theater='Малый'
  and ee.date_text = '29 Четвергъ.';
```

Result: RG asked to check the 3 rows still tracked as "inferred, not
scan-verified" in the genre-field follow-up memory. Located both source
pages and confirmed all 3 inferences were correct:

- `repertoire_1897-98_pair006` cites `_source: repertoire_1897-98_p006`,
  which (unlike some other pages in this issue) really is the RENDER-
  sequential index -- confirmed against `split_page_numbers_final.csv`
  (`p006__top` -> printed p.14) and by directly checking that render:
  wrong season/month entirely (Dec 20 - Jan 9, not the Oct 3-16 range
  this pair actually covers). Re-derived the correct render by checking
  printed page 6 instead (`p002__top` -> printed p.6,
  `ForUpload_1897-98_Repertoire_002.jpg`) -- this one matches exactly,
  dates 3-23 October 1897. Confirmed:
  - `12 Воскрес.` evening, "Осеній вечеръ въ деревнѣ, вод." -- genre
    "вод." correct; fixed a spelling typo (Осеній -> Осенній, the scan
    clearly shows a double н) while there.
  - `16 Четв.`, "Госпожа-служанка, вод." -- genre "вод." correct.
  - Bonus (not one of the original 3, found while re-reading this row):
    the same session's third work ("Осеній вечеръ въ деревнѣ", genre
    previously null) and the whole session's `receipts_text` (previously
    null) were both recoverable from the same scan row -- genre "вод."
    and receipts "1359 р. 21 к." added, plus the same Осеній->Осенній
    spelling fix.
- `repertoire_1894-95_pair004` cites `_source: repertoire_1894-95_p005
  (bottom)`, which turned out to be the WRONG page for this content
  (that render is a German-guest-troupe page, Большой/Малый both
  entirely dark throughout -- doesn't match at all). Found the real
  page by checking printed page 5 instead (`p001__bottom` -> printed
  p.5 per the CSV, `ForUpload_1894-95_Repertoire_001.jpg`) -- confirmed
  by an exact receipts match (550 р. 21 к.), dates 12 Sept - 3 Oct 1894.
  Confirmed "Рай земной, ком." was the correct full title/genre (not a
  guess); also fixed a spelling typo on the companion work ("Ирэнь" ->
  "Ирэнъ", soft sign -> hard sign, matching what's actually printed) and
  corrected the session's own `_source` citation, which had cited the
  wrong render page.

Propagated both pages to `resolved_sessions/`, re-ran
`parse_and_validate.py` + `quality_checks.py` + `build_duckdb.py`.
4359 events / 5649 performances unchanged (pure title/genre/receipts
corrections, no rows added or removed), 5 quality flags unchanged.
Rebuilt `imperial_theaters.duckdb` and verified all 3 fixes directly
(query above). This closes items 1-3 of
`genre-field-3-inferred-rows-followup.md` -- only item 5 (the
`"Отечественный"` event_status row, no corpus match) remains open.

## 2026-09-17 — checked genre-field-followup item 5 (repertoire_1892-93_pair008, 26 Октября., Маріинскій, annotation "Отечественный") against the scan

```sql
-- verification, run against the rebuilt duckdb after applying the fixes below
select ee.date_text, ee.receipts_text, eep.performance_title, eep.genre
from raw.event_entry ee join raw.event_entry_performance eep using(event_id)
where ee.page_id='repertoire_1892-93_pair008' and ee.theater='Маріинскій'
order by ee.date_text;
```

Result: RG asked to check the last open item (previously assessed as
"genuinely unrecoverable, no corpus match"). Turned out NOT to be
unrecoverable -- it was a straightforward extraction misread, findable
the same way as everything else in this issue. `_source` cited
`repertoire_1892-93_p008 (top)`; the render-sequential reading (JPG008,
printed p.18) was wrong (an unrelated Feb/Mar 1893 page); the
printed-page-number reading (`p003__top` -> printed p.8, per
`split_page_numbers_final.csv`) was right --
`ForUpload_1892-93_Repertoire_003.jpg`, dates 24 Oct - 4 Nov 1892. The
`26 Октября.` cell reads plainly `"Отелло, оп. 2947 р. 70 к."` -- no
`"Отечественный"` text anywhere near it; likely a VLM misread off the
shared `"Оте-"` prefix between `Отелло` and `Отечественный`.

While checking the adjacent rows for context, found the SAME
Mariinsky-column-only defect repeating across most of this page's
date range: 7 more sessions (`27`-`30 Октября.`, `1`-`4 Ноября.`) had
`receipts_text` silently dropped (Бolshoy and Mikhaylovsky's receipts
on the same rows were all intact -- this wasn't a page-wide gap, just
Mariinsky), and 3 of those (`28`, `29 Октября.`, `3 Ноября.`) also had
`Млада` mistagged `"бал."` instead of `"оп."` (Млада is Rimsky-Korsakov's
opera). Recovered all 8 receipts figures and fixed all 3 genre tags
directly from the same scan; also fixed one title typo
(`"Дочь фараопа."` -> `"Дочь фараона."`, matching the real ballet) and
corrected the `_source` citation on every touched session (old value
pointed at the wrong render).

**Also newly discovered, NOT fixed this pass, flagged for follow-up**:
`repertoire_1892-93_pair008` is missing TWO ENTIRE THEATER COLUMNS
(Александринскій, Малый -- only Маріинскій/Александринскій/Михайловскій...
correction, only Маріинскій/Большой/Михайловскій are present) across
its whole 12-date range. This is the same "missing entire theater
column" pattern already fixed corpus-wide for the 4
`zero_dark_cells_on_multiweek_page` pages, but this page wasn't in that
flagged set (it has real dark cells on `24`/`31 Октября.` for the
theaters it does have, so the flag's zero-dark-cells heuristic didn't
trigger) -- a genuine gap in that check's coverage. Not resolved here;
scope was already well beyond the single row RG asked to check.

Propagated, re-ran `parse_and_validate.py` + `quality_checks.py` +
`build_duckdb.py`. 4359 -> 4359 events (unchanged), 5649 -> 5650
performances (+1, the recovered `Отелло` session), 5 quality flags
unchanged. Rebuilt and verified directly against the database (query
above). This closes item 5 -- **`genre-field-3-inferred-rows-followup.md`
is now fully resolved, 0 rows open.**

## 2026-09-17 — are there other entries where we'd expect receipts but don't? (RG asked, follow-up to the pair008 silently-dropped-receipts fix)

```sql
select event_status, count(*) as n, count(receipts_text) as n_with_receipts,
       count(*) - count(receipts_text) as n_null_receipts
from raw.event_entry
where page_id like 'repertoire_%'
group by 1 order by 1;

select regexp_extract(page_id, 'repertoire_([0-9]{4}-[0-9]{2})', 1) as season,
       count(*) as n_performed, count(receipts_text) as n_with_receipts,
       count(*) - count(receipts_text) as n_null
from raw.event_entry
where page_id like 'repertoire_%' and event_status='performed'
group by 1 order by 1;

select regexp_extract(page_id, 'repertoire_([0-9]{4}-[0-9]{2})', 1) as season,
       (annotation is not null) as has_annotation, count(*) as n
from raw.event_entry
where page_id like 'repertoire_%' and event_status='performed' and receipts_text is null
      and regexp_extract(page_id, 'repertoire_([0-9]{4}-[0-9]{2})', 1) not in ('1890-91','1891-92')
group by 1,2 order by 1,2;
```

Result: 826 `no_performance` (dark) rows correctly have no receipts.
Of 3,533 `performed` rows, 1,050 have null `receipts_text`. Broken out
by season: `1890-91` (337/337) and `1891-92` (540/540) are **100%
null** -- confirmed via 2 direct scan checks (Sept 1890 opener,
March 1891) that neither season's printed table carries receipts
figures anywhere at all; RG confirmed this as a genuine source
convention, not a bug (see `1890-91-1891-92-no-receipts-printed.md`
memory). The other six seasons (`1892-93`-`1897-98`) have a combined
173 nulls, 117 of them on ordinary (no-annotation) performances --
spread across ~30 different pages, no single page dominating,
confirmed a mixed bag on spot-check (one page's nulls were a whole-row
binding-crease pattern already understood; another looked like a
genuine extraction gap similar to the just-fixed `pair008` case). Not
yet systematically audited -- flagged as a candidate follow-up, not
acted on this turn.

## 2026-09-18 — fixed repertoire_1892-93_pair008's missing theater columns (Александринскій, Малый)

```sql
-- verification, run against the rebuilt duckdb
select theater, count(distinct date_text) as ndates, count(*) as nrows
from raw.event_entry where page_id='repertoire_1892-93_pair008'
group by theater order by theater;
```

Result: finished the fix flagged yesterday
([[missing-theater-column-check-gap]]) -- transcribed the remaining
dates (30 Октября - 4 Ноября) from `ForUpload_1892-93_Repertoire_003.jpg`
(printed pp.8-9) and applied all 26 recovered sessions (12 dates x 2
theaters, with morning/evening splits on 3 of those dates). All 5
theaters now present for all 12 dates (24 Октября - 4 Ноября 1892).
Propagated to `resolved_sessions/`, re-ran `parse_and_validate.py` +
`quality_checks.py` + `build_duckdb.py`: 4359 -> 4385 events, 5650 ->
5688 performances, 5 quality flags unchanged (no new duplicates or
parse failures introduced). Rebuilt and verified directly against the
database (query above).

## 2026-09-18 — full rebuild of repertoire_1895-96_p012 (null-receipts audit, page 1 of the worklist)

```sql
-- verification, run against the rebuilt duckdb
select theater, count(distinct date_text) as ndates, count(*) as nrows, count(receipts_text) as n_receipts
from raw.event_entry where page_id='repertoire_1895-96_p012'
group by theater order by theater;

select date_text, theater, receipts_text, annotation
from raw.event_entry where page_id='repertoire_1895-96_p012' and event_status='performed' and receipts_text is null
order by date_text;
```

Result: RG asked to check the null-receipts residual in the 6 non-
1890-91/91-92 seasons; the first page in the worklist (17 of the 173
target rows) turned out to be a much bigger defect than missing
receipts. `repertoire_1895-96_p012` is the only 1895-96 page named
bare `p012` (no `pair012` counterpart exists, unlike every other
even-numbered slot) and carried no `_source` on any session --
evidence it never went through this issue's usual dual-extraction/
merge pipeline. Checked against the scan
(`ForUpload_1895-96_Repertoire_003.jpg` printed p.9 for 15-17 Nov,
`_004.jpg` printed pp.10-11 for 19-26 Nov 1895) and found
Маріинскій/Александринскій/Михайловскій uniformly mismarked
`is_dark=true`/`works=[]` on every one of the file's 10 dates despite
being fully active in the source -- and Большой/Малый's existing
content didn't match the scan either on several dates (e.g. 17
Ноября's Большой/Малый content was swapped with each other; 20 Ноября
was entirely misattributed). RG approved a full rebuild, same
treatment as `repertoire_1895-96_pair016` yesterday.

Re-transcribed all 5 theaters for all 10 dates directly from the scan
and replaced the file's session list wholesale (50 -> 55 sessions).
One row (26 Ноября) sits right on the binding-fold boundary -- 4
figures there are genuinely either uncaptured (free/benefit shows with
no printed figure) or physically torn away; left honestly null rather
than guessed, each documented with which case applies.

Re-ran `parse_and_validate.py` -> `quality_checks.py` ->
`build_duckdb.py`: 4385 -> 4390 events, 5688 -> 5728 performances, 5
quality flags unchanged. Rebuilt and verified directly: all 5 theaters
now present for all 10 dates, and the null-receipts count for this
page dropped from 17 to 4 (all 4 legitimately explained above).

## 2026-09-18 — full rebuild of repertoire_1895-96_pair010 + duplicate-coverage cleanup with p012

```sql
-- verification, run against the rebuilt duckdb
select theater, count(distinct date_text) ndates, count(*) nrows, count(receipts_text) n_receipts
from raw.event_entry where page_id='repertoire_1895-96_pair010' group by theater order by theater;

-- confirm no remaining cross-file date/theater overlap between p012 and pair010
select a.date_text, a.theater
from (select distinct date_text, theater from raw.event_entry where page_id='repertoire_1895-96_p012') a
join (select distinct date_text, theater from raw.event_entry where page_id='repertoire_1895-96_pair010') b
using(date_text, theater);
```

Result: continuing the null-receipts audit, checking `repertoire_1895-
96_pair010` (12 of the 173 target rows) turned up two compounding
defects and a genuine cross-file duplicate with the just-fixed `p012`:

1. **Bolshoy-column bleed, systematic**: Большой consistently showed a
   corrupted echo of Малый's real content (titles/genres visibly
   mangled versions of Малый's own, e.g. "Спорный наслѣдникъ/Долото"
   vs Малый's real "Спорный вопросъ/Лолотта") on every date 18 Ноября
   - 2 Декабря where the scan shows Большой genuinely dark. Matches
   this issue's already-documented Большой-bleed pattern, just not
   previously caught on this page. Большой genuinely resumes
   performing 3 Декабря onward (confirmed real, distinct content).
2. **Several dates missing 3-4 theaters entirely** (`30 Ноября.`,
   `1 Декабря.` originally had only Маріинскій captured).
3. **A one-date mislabeling cascade for 2-6 Декабря**: the old file's
   `"2 Суббота."` session actually contained `3 Воскрес.`'s content,
   `"3 Воскрес."`'s contained `4 Понед.`'s, `"4 Понед."`'s contained
   `5 Вторникъ.`'s, and `"5 Вторникъ."`'s contained `6 Среда.` morning's
   (the free students' show) -- meaning the true `5 Декабря` had been
   dropped entirely and true `2 Декабря` (all dark except a
   Mikhaylovsky benefit) never appeared under any label. `6 Среда.`
   evening was the one date in this stretch already correctly labeled
   (confirmed via an exact receipts match), which is what made the
   cascade findable.
4. **Confirmed duplicate coverage with `repertoire_1895-96_p012`**:
   dates 19-26 Ноября appeared correctly in both files independently
   (same scan, same printed page). Removed from `p012` (kept only its
   unique 15-17 Ноября), keeping `pair010` as the sole owner of 18
   Ноября - 6 Декабря.

Fully re-transcribed all 5 theaters for all 19 true dates from
`ForUpload_1895-96_Repertoire_004.jpg` (same image used for `p012`) and
replaced `pair010`'s session list wholesale (74 -> 106 sessions).
Re-ran `parse_and_validate.py` -> `quality_checks.py` ->
`build_duckdb.py`: 4390 -> 4382 events (net change reflects both the
pair010 recovery and the p012 trim), 5728 -> 5703 performances, 5
quality flags unchanged (no new duplicate keys introduced by the
overlap cleanup). Rebuilt and verified directly: all 5 theaters present
across all 19 dates in `pair010`, all 5 theaters present across all 3
dates in `p012`, and a direct query confirms zero remaining date/theater
overlap between the two files.

## 2026-09-18 — full rebuild of repertoire_1892-93_pair002 (null-receipts audit, page 3)

```sql
-- verification, run against the rebuilt duckdb
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1892-93_pair002' group by theater order by theater;
```

Result: page 3 of the null-receipts worklist. `repertoire_1892-93_
pair002` covers the very start of the 1892-93 season (16 Августа - 1
Сентября 1892). Checked against `ForUpload_1892-93_Repertoire_000.jpg`
(printed p.2) and found date labels shifted against their real content
almost immediately -- old `"17 Понед."` had merged two different
calendar rows' content under one label, two real dates (`27 Августа`,
`1 Сентября`) were entirely absent from the file, and the true
multi-theater season-opener day (`30 Августа`, marked `"Гимнъ."` across
all 5 theaters at once) had been dropped -- its date slot instead held
the FOLLOWING day's content, cascading one slot further for `31
Августа` too (which in turn held `1 Сентября`'s content).

Confirmed against the scan that `16`-`26 Августа` genuinely have only
Малый active (the other 4 theaters hadn't opened for the season yet)
-- not a defect, matches this corpus's established early-season
pattern. `22`, `28`, `29 Августа` have no table row at all in the
source (a genuine calendar gap, not a bug). One row (`26 Августа`)
has receipts genuinely illegible -- a torn page edge right where the
figure would print.

Fully re-transcribed every date from the scan and replaced the file's
session list wholesale (26 -> 70 sessions, now covering 14 real dates
x 5 theaters). Re-ran `parse_and_validate.py` -> `quality_checks.py`
-> `build_duckdb.py`: 4382 -> 4426 events, 5703 -> 5715 performances, 5
quality flags unchanged. Rebuilt and verified directly: all 5 theaters
present across all 14 dates, `30 Августа`'s Гимнъ-marked multi-theater
day and `1 Сентября` both now correctly populated.

## 2026-09-18 — full rebuild of repertoire_1892-93_pair004 (null-receipts audit, page 4)

```sql
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1892-93_pair004' group by theater order by theater;
```

Result: page 4 of the worklist. `repertoire_1892-93_pair004` (10
Сентября - 2 Октября 1892) was missing Большой entirely across all 20
dates (confirmed genuinely active in the scan, not a season-opening
gap this time -- e.g. "Демонъ, оп." on 10 Сентября). Александринскій
also had scattered content misattribution: old `"1 Четв."` held a
garbled duplicate combining `29 Вторникъ`'s and `30 Среда`'s real
Alexandrinsky content, while `1 Четв.`'s own genuine content had been
mislabeled under `"2 Пятница."`; old `"26 Суббота."` held a duplicate
of `24 Четвергъ`'s content where the scan shows Alexandrinsky
genuinely dark that day. Маріинскій/Малый were also entirely missing
for `26`-`30` (both had opened for the season by then, confirmed
active in the scan). Checked against
`ForUpload_1892-93_Repertoire_001.jpg` (printed pp.4-5). One row (`22
Вторникъ`) has every column's receipts genuinely illegible -- a
binding-fold crease runs directly beneath the whole row.

Fully rebuilt (68 -> 100 sessions, 20 dates x 5 theaters).
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4426 -> 4458 events, 5715 -> 5752 performances, 5 quality flags
unchanged. Verified directly: all 5 theaters present across all 20
dates.

## 2026-09-18 — full rebuild of repertoire_1892-93_pair006 (null-receipts audit, page 5)

```sql
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1892-93_pair006' group by theater order by theater;
```

Result: page 5. `repertoire_1892-93_pair006` (3-22 October 1892) had:
date `4 Октября` entirely absent (its Alexandrinsky content had been
misattributed to `3 Октября`, which the scan shows genuinely dark for
that theater); `16 Октября`'s Alexandrinsky wrongly marked dark
despite being active; dates `17`-`22 Октября` missing
Маріинскій/Михайловскій/Большой/Малый entirely (only Alexandrinsky
captured); and a recurring OCR truncation ("Я картинка"/"Ъ картинка"
for "Лѣтняя картинка") on several Малый entries. Checked against
`ForUpload_1892-93_Repertoire_002.jpg` (printed pp.6-7).

Fully rebuilt (70 -> 106 sessions, 20 dates x 5 theaters). 4458 ->
4494 events, 5752 -> 5795 performances, 5 quality flags unchanged.
Verified directly: all 5 theaters present across all 20 dates.

## 2026-09-18 — repertoire_1892-93_pair014 (null-receipts audit, page 6) -- targeted duplicate cleanup; broader missing-theater issue confirmed but deferred

```sql
select date_text, receipts_text, eep.performance_title
from raw.event_entry ee join raw.event_entry_performance eep using(event_id)
where page_id='repertoire_1892-93_pair014' and date_text in ('6 Срѣд.','8 Пятница.')
order by date_text;
```

Result: page 6. This file only ever had Маріинскій captured across all
22 dates (27 Декабря 1892 - 16 Января 1893) -- confirmed via the scan
(`ForUpload_1892-93_Repertoire_006.jpg`, printed pp.14-15) that all 4
other theaters are genuinely active throughout, so this is the same
missing-theater-column defect as several earlier pages. Given this
page's dense utro/vecher-per-theater layout made row-to-date alignment
unusually error-prone on a first pass, scoped this session's fix down
to what could be verified with full confidence: the two originally-
flagged null-receipts rows.

- `6 Срѣд.` "Фаустъ": confirmed genuinely illegible -- a binding-fold
  crease runs directly beneath this whole row (all 5 theaters, not
  just Маріинскій, are affected there). Left null, now documented.
- `8 Пятница.`: had THREE Mariinsky sessions stored, two of them
  duplicates -- a "Гугеноты" entry that actually belongs to `7
  Четвергъ` (confirmed via an exact receipts match, 3605 р. 70 к.) and
  a null-receipts "Фаустъ" entry duplicating `6 Срѣд.`'s own entry.
  Removed both; the genuine `8 Пятница.` content ("Эсклармонда", 3593
  р. 70 к.) was already correct and untouched.

Removed 2 duplicate sessions (27 -> 25). Re-ran
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4494 -> 4492 events, 5795 -> 5793 performances, 5 quality flags
unchanged. Verified directly (query above): both originally-flagged
rows now resolved (one confirmed legitimately null, one fixed).

**NOT resolved this pass, flagged for a dedicated follow-up**: the
missing Александринскій/Михайловскій/Большой/Малый across this whole
page (22 dates x 4 theaters) -- confirmed real via the scan, same
underlying defect as `pair004`/`pair006`/`pair008`, but recovering it
needs more careful row-by-row scan work than this session's cursory
check could responsibly deliver. Also noticed but not chased down: at least one more
likely duplicate/misattribution around `4 Понед.`/`6 января.` (the
"Бенефисъ г. Л. Иванова" Щелкунчикъ/Спящая красавица entry appears
close to twice, with slightly different receipts figures each time) --
not touched, since confidence in the correct resolution wasn't high
enough this pass.

## 2026-09-18 — full rebuild of repertoire_1892-93_pair022 (null-receipts audit, page 7)

```sql
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1892-93_pair022' group by theater order by theater;
```

Result: page 7. `repertoire_1892-93_pair022` only had Большой present
(11 апрѣля - 21 апрѣля 1893), and even that column had misattributed
content: old `11 апрѣля.` was really `9 Апрѣля`'s content, and old `13
апрѣля.` carried a duplicate that really belongs to `12 Апрѣля` --
explaining that date's original null-receipts flag. True `11 Апрѣля`
had never been captured under any label; its own receipts are
genuinely illegible (binding-fold crease). Recovered `9`-`10 Апрѣля`
too (previously absent from every file in this season -- checked, no
other file captures them) since the real data was sitting mislabeled
in this one. Checked against `ForUpload_1892-93_Repertoire_010.jpg`
(printed pp.22-23).

Fully rebuilt (12 -> 65 sessions, 13 dates x 5 theaters). 4492 -> 4545
events, 5793 -> 5873 performances, 5 quality flags unchanged (no new
cross-file duplicate from adding 9-10 Апрѣля). Verified directly: all
5 theaters present across all 13 dates.

## 2026-09-18 — recovered repertoire_1893-94_pair006's missing Михайловскій column (null-receipts audit, page 8)

```sql
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1893-94_pair006' group by theater order by theater;
```

Result: page 8, first 1893-94 season page. Михайловскій was entirely
missing across all 20 dates (4-23 Октября 1893) -- confirmed genuinely
active throughout via
`ForUpload_1893-94_Repertoire_002.jpg` (printed pp.6-7). Unlike recent
1892-93 pages, the other 4 theaters' own data was already correct
(no scrambling/misattribution found on spot-check) -- a
cleaner, single-column recovery. `13 Октября`'s receipts left null for
Михайловскій, matching the already-correct null status of
Александринскій/Большой that day -- the whole physical row is cut off
by the binding-fold crease, not just isolated columns.

Added 20 recovered Михайловскій sessions (86 -> 106). Re-ran
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4545 -> 4565 events, 5873 -> 5911 performances, 5 quality flags
unchanged. Verified directly: all 5 theaters present across all 20
dates.

## 2026-09-18 — repertoire_1893-94_pair010 (null-receipts audit, page 9) -- targeted duplicate cleanup; broader issues deferred

```sql
select date_text, theater, receipts_text, eep.performance_title
from raw.event_entry ee join raw.event_entry_performance eep using(event_id)
where page_id='repertoire_1893-94_pair010' and date_text in ('13 Субб.','14 Воскресенье.')
order by date_text, theater;
```

Result: page 9. This file has the same pervasive kind of corruption as
`pair014` (only 4 of 5 theaters present -- Малый entirely missing --
plus several more duplicate/misattributed sessions beyond the flagged
ones: e.g. `24 Среда.` has 3 Mikhaylovsky sessions, `29 Понед.` has 2).
Checked against `ForUpload_1893-94_Repertoire_004.jpg` (printed
pp.10-11) and fixed what could be verified with full confidence:

- `13 Субб.`: confirmed genuinely dark for Маріинскій/Александринскій/
  Большой (only Михайловскій performed, a benefit). The "Гимнъ."/
  "Безплатное" fragments previously stored under this date for those
  3 theaters were duplicates of `14 Воскресенье`'s real free-show
  block (that date already has its own correct entries for the same
  theaters) -- removed all 3.
- `14 Воскресенье.` Михайловскій: had two sessions for what's really
  one performance -- one with the wrong title ("L'Etrangère") but
  correct receipts (1216 р.), one with the correct title ("L'Honneur
  et l'Argent") but null receipts. Removed the wrong-title duplicate,
  recovered the correct one's receipts.

77 -> 73 sessions (net: -4 removed, +0 added, 1 receipts fix). Re-ran
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4565 -> 4561 events, 5911 -> 5903 performances, 5 quality flags
unchanged. Verified directly (query above): both originally-flagged
issues resolved.

**NOT resolved this pass, flagged for follow-up**: Малый missing
entirely across this whole page (confirmed likely real, same defect
class as other pages); the remaining flagged nulls at `22 Пон.`
Михайловскій and `23 Вторникъ.` Маріинскій (the latter has a benefit
annotation, plausibly legitimate); and further duplicate sessions
spotted at `24 Среда.` (3x Михайловскій) and `29 Понед.` (2x
Михайловскій) not yet untangled.

## 2026-09-18 — repertoire_1893-94_pair016 (null-receipts audit, page 10) -- 3 flagged rows + 3 scattered duplicates untangled

```sql
select date_text, theater, receipts_text, eep.performance_title
from raw.event_entry ee join raw.event_entry_performance eep using(event_id)
where page_id='repertoire_1893-94_pair016' and date_text in ('17 Понед.','23 Воскрес.','24 Понед.','25 Вторник.','27 Четвергъ.') and theater in ('Маріинскій','Александринскій')
order by date_text, theater;
```

Result: page 10. Checked against `ForUpload_1893-94_Repertoire_007.jpg`
(printed pp.16-17) and resolved all 3 originally-flagged rows, plus
untangled 3 scattered Alexandrinsky sessions the same investigation
surfaced (each stored under a spurious extra date-label variant --
`"25 Января."` x2 and `"25 января."` -- rather than under their real
dates):

- `17 Понед.` Маріинскій: recovered missing receipts (928 р. 97 к.);
  work title was already correct, just the figure was dropped.
- `25 Вторник.` Александринскій: recovered from a mislabeled `"25
  Января."` entry that also had a digit typo (1045->1015 р. 75 к.).
- `23 Воскрес.` Александринскій: recovered from a mislabeled `"25
  января."` (lowercase) entry -- exact receipts match confirmed it.
- `24 Понед.` Александринскій: recovered from the second `"25
  Января."` duplicate; receipts read from a crease-damaged row
  (moderate confidence, "1585 р. 20 к.").
- `27 Четв.`/`27 Четвергъ.`: these were the same calendar date split
  across two labels. Recovered Маріинскій's missing content (was null,
  now "Іоаннъ Лейденскій", 2937 р. 20 к.) and consolidated both
  theaters onto the `"27 Четвергъ."` label already used by the rest of
  that date's sessions.

90 -> 90 sessions (3 removed, 3 added, net zero -- pure relabeling/
recovery, no new events). Re-ran `parse_and_validate.py` ->
`quality_checks.py` -> `build_duckdb.py`: counts unchanged (4561
events, 5903 performances), 5 quality flags unchanged. Verified
directly (query above): all 5 fixes confirmed.

## 2026-09-18 — full recovery of repertoire_1893-94_pair018 (null-receipts audit, page 11)

```sql
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1893-94_pair018' group by theater order by theater;
```

Result: page 11. This page had an unusual split defect: Михайловскій
missing for dates 4-14 Февраля, Большой and Малый missing for ALL 19
dates, and Александринскій/Маріинскій missing for 18-22 Февраля -- an
uneven distribution of the same missing-theater-column defect (not a
uniform single-column drop like most other pages). Checked against
`ForUpload_1893-94_Repertoire_008.jpg` (printed pp.18-19).

Also found and fixed, beyond the 4 originally-flagged rows: the entire
spurious date `"14 Февраля."` (3 sessions, all duplicates/fragments of
`13 Воскрес.` and `14 Понед.`, removed); `16 Среда.`'s Маріинскій and
Михайловскій sessions were both misattributed (the "Спектакль въ
память П. И. Чайковскаго" commemorative concert stored there actually
belongs to `17 Четвергъ.`, moved there along with recovering that
date's other 3 missing theaters).

Added ~66 recovered/corrected sessions net (40 -> 106). Re-ran
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4561 -> 4627 events, 5903 -> 6003 performances, 5 quality flags
unchanged. Verified directly: all 5 theaters present across all 19
dates.

## 2026-09-18 — repertoire_1893-94_pair024 (null-receipts audit, page 12) -- whole-file date-cascade fix

```sql
select date_text, receipts_text, eep.performance_title
from raw.event_entry ee join raw.event_entry_performance eep using(event_id)
where page_id='repertoire_1893-94_pair024' order by date_text;
```

Result: page 12. Checked the flagged row (`26 Вторникъ` Александринскій,
null) against `ForUpload_1893-94_Repertoire_011.jpg` (printed pp.24-25)
and found a consistent whole-file date-label cascade: every session
from `19 Вторникъ` through `28 Четвергъ` (10 sessions) was labeled one
calendar day earlier than its real content, confirmed via exact
receipts matches at every step of the chain. Relabeled all 10;
resolved a leftover duplicate created by the shift (`29 Пятница.`
appeared twice after the cascade -- the duplicate, a dark placeholder,
relabeled to `30 Суббота.` and then de-duplicated against the file's
own pre-existing dark entry for that date).

The originally-flagged null (what's now correctly `27 Среда.`) remains
null -- its receipts sit directly under the binding-fold crease and
are genuinely illegible, same as several other pages' crease rows.

19 -> 18 sessions (net -1, one duplicate removed). Re-ran
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4627 -> 4626 events, 6003 -> 6003 performances (unchanged), 5 quality
flags unchanged. Verified directly (query above): clean date sequence,
no duplicates.

**Not fixed this pass**: Михайловскій, Большой, and Малый are all
missing from this page too (confirmed genuinely active in the scan for
most of April) -- flagged for follow-up, not recovered this session.

## 2026-09-18 — repertoire_1894-95_p008 (null-receipts audit, page 13) -- confirmed legitimate, no fix needed

Result: page 13. Checked `7 Воскресенье.` (Александринскій + Малый,
both null) against `ForUpload_1894-95_Repertoire_008.jpg` (printed
p.18) -- this is the LAST page of the 1894-95 season's scanned
Repertoire table (only 9 renders exist for this season, 000-008, and
this is the final one). The row's receipts are cut off at the physical
bottom edge of the scanned image itself -- not a crease, just no
further page exists to capture them. Confirmed genuinely unrecoverable
from available materials, matching the file's own already-correct null
values. All 5 theaters present across all 8 dates (28 Апрѣля - 7 Мая
1895), 40/40 sessions complete -- no other defects found on this page.
No changes made.

## 2026-09-18 — repertoire_1894-95_pair006 (null-receipts audit, page 14) -- confirmed flagged row + recovered 6-date cluster

Result: page 14. The single flagged row (`15 Суббота` Александринскій)
confirmed genuinely dark against `ForUpload_1894-95_Repertoire_002.jpg`
(printed pp.6-7) -- no fix needed there. While checking, found
Александринскій and Малый were ALSO missing (beyond the one flagged
null) for a 6-date cluster: `16`-`19 Октября` and `1`-`3 Январь` --
recovered all from the same scan.

**NOT fixed this pass**: `14 Пятн.`/`14 Октября.` and `4 Октября.`/`4
Среда.` each carry MULTIPLE duplicate sessions per theater (e.g. 3
different Маріинскій entries under `14 Пятн.` alone) -- content from
several different calendar dates merged onto these labels, the same
class of defect as `pair014`/`pair010`'s deferred issues. Not
untangled this pass; flagged for follow-up.

92 -> 109 sessions. Re-ran `parse_and_validate.py` ->
`quality_checks.py` -> `build_duckdb.py`: 4627 -> 4643 events, 6003 ->
6038 performances, 5 quality flags unchanged.

## 2026-09-18 — repertoire_1894-95_pair008 (null-receipts audit, page 15) -- 3 flagged rows fixed + 5-date cluster recovered

Result: page 15. All 3 originally-flagged rows (`19 Четвергъ.`
Александринскій/Малый/Маріинскій) were genuine extraction drops --
recovered from `ForUpload_1894-95_Repertoire_003.jpg` (printed p.9),
clearly legible, not crease-damaged. Also found and fixed: a duplicate
date spelling (`"16 января."` Малый relabeled to merge with `"16
Понедѣльн."`, its rightful date) and a 5-date cluster (`21`-`25
Января`) missing Александринскій/Маріинскій entirely (21st confirmed
genuinely dark for both; 22-25 recovered from the scan).

88 -> 98 sessions. Re-ran `parse_and_validate.py` ->
`quality_checks.py` -> `build_duckdb.py`: 4643 -> 4653 events, 6038 ->
6053 performances, 5 quality flags unchanged. Verified directly: all 5
theaters present across all dates.

## 2026-09-18 — recovered repertoire_1894-95_pair016's missing Маріинскій column (null-receipts audit, page 16)

```sql
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1894-95_pair016' group by theater order by theater;
```

Result: page 16. All 4 flagged nulls (`18 Апрѣля.`) confirmed
genuinely illegible -- a binding-fold crease runs under the whole row
(all theaters affected). Cleaned up two data-shape artifacts on the
same row while there: Большой's bogus annotation ("Волки Ира") was
bleed from Малый's own title (cleared), and Малый's title had two OCR
typos (Палки->Волки, Ирэнь->Иронъ). Also found and recovered
Маріинскій, entirely missing across all 10 dates on this page --
scan-verified against `ForUpload_1894-95_Repertoire_007.jpg` (printed
pp.16-17).

Added 10 recovered Маріинскій sessions (40 -> 50). Re-ran
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4653 -> 4663 events, 6053 -> 6063 performances, 5 quality flags
unchanged. Verified directly: all 5 theaters present across all 10
dates.

## 2026-09-18 — repertoire_1895-96_pair006 (null-receipts audit, page 17) -- Большой-bleed cleared; scattered duplicates deferred

```sql
select date_text, receipts_text, event_status from raw.event_entry
where page_id='repertoire_1895-96_pair006' and theater='Большой' order by date_text;
```

Result: page 17. All 7 flagged null rows were Большой -- confirmed
against `ForUpload_1895-96_Repertoire_002.jpg` (printed pp.6-7) that
Большой is genuinely dark for every single date on this page. The
garbled annotations/titles stored under those flagged sessions
("Лолоттъ", "Наканунѣ золотой", "Грандъ-балъ", etc.) were bleed from
Малый's real neighboring content -- the established Большой-column-
bleed pattern already resolved for 9 other pages earlier in this
issue; this page was apparently missed by that earlier pass. Cleared
all 7 (plus one exact duplicate dark placeholder), not reconstructed.

**NOT fixed this pass**: found significant scattered duplication in
Маріинскій and Михайловскій too (recurring titles like "Орестейя" and
"Blanchette, com. / Le Chatouilleur du Puy de Dôme..." reappearing
under multiple date labels with different receipts each time -- e.g.
"17 октября." vs "17 Вторн.", extra entries duplicated onto "18
Среда."/"19 Четвергъ."), plus Александринскій/Малый/Большой entirely
missing for `21`-`28 Октября` (Маріинскій/Михайловскій present there
instead). Not untangled this pass -- flagged for follow-up.

79 -> 77 sessions (net: 7 cleared to dark + 1 duplicate removed).
Re-ran `parse_and_validate.py` -> `quality_checks.py` ->
`build_duckdb.py`: 4663 -> 4661 events, 6063 -> 6056 performances, 5
quality flags unchanged. Verified directly: Большой correctly dark for
all 14 dates on this page.

## 2026-09-18 — repertoire_1895-96_pair014 and pair016 (null-receipts audit, pages 18-19) -- already confirmed legitimate

Result: both pages were fully rebuilt yesterday (2026-09-17) as part of
the `zero_dark_cells_on_multiweek_page` fix. Checked their remaining
null-receipts rows against what was already documented then:
`pair014`'s 6 rows are the `7 Воскрес.` crease-damaged row (all 5
theaters) plus `3 Среда.` Александринскій's free-show notice
(annotation "Безплатный спектакль для воспитанниковъ учебныхъ
заведеній.", genuinely no figure). `pair016`'s 10 rows are the `26
Пятница.` crease-damaged row (all 5 theaters) plus the `30 Вторникъ.`/
`31 Среда.` free-morning-show sessions (annotation "Безплатные
утренніе спектакли..."). All already correctly documented as
legitimate during yesterday's rebuild -- no new issues, no changes
made.

## 2026-09-18 — recovered repertoire_1895-96_pair022's missing Малый column + fixed flagged row (null-receipts audit, page 20)

```sql
select theater, count(distinct date_text) ndates, count(*) nrows
from raw.event_entry where page_id='repertoire_1895-96_pair022' group by theater order by theater;
```

Result: page 20 (last 1895-96 page in the no-annotation bucket).
Малый was entirely missing across all 13 dates (30 Марта - 11
Апрѣля/11 Четвергъ 1896) -- recovered from
`ForUpload_1895-96_Repertoire_010.jpg` (printed pp.22-23). The 4
originally-flagged nulls (`11 Четвергъ.`, all other 4 theaters) were
genuine extraction drops with correct titles already present -- just
recovered the receipts. One Малый row (`8 Понед.`) has receipts
genuinely illegible at the binding crease, left null.

Added 15 Малый sessions + fixed 4 receipts (52 -> 67 sessions). Re-ran
`parse_and_validate.py` -> `quality_checks.py` -> `build_duckdb.py`:
4661 -> 4676 events, 6056 -> 6081 performances, 5 quality flags
unchanged. Verified directly: all 5 theaters present across all 13
dates.

## 2026-09-18 — null-receipts audit page 21: repertoire_1896-97_pair002 (1896-97 season opener)

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1896-97_pair002' and event_status='performed' and receipts_text is null
```

Result: 2 rows before fix -- ('3 Вторникъ.', 'Малый', None), ('3 Вторникъ.', 'Михайловскій', None).
Investigation revealed a whole-file date-label cascade (every date from the 2nd row onward
was labeled one true-date-slot too early; a spurious "17 Среда." row never existed in the
source). Rebuilt all 14 dates (28 sessions) with correct labels, scan-verified against
ForUpload_1896-97_Repertoire_000.jpg (printed pp.2-3). Confirmed Михайловскій genuinely dark
16-27 Августа (season not yet open) -- a legitimate convention, not a defect.

```sql
select date_text, theater, receipts_text from raw.event_entry
    where page_id='repertoire_1896-97_pair002' and event_status='performed' and receipts_text is null
```

Result: 0 rows after fix -- confirmed against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.

## 2026-09-18 — null-receipts audit page 22: repertoire_1896-97_pair004

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1896-97_pair004' and event_status='performed' and receipts_text is null
```

Result: 3 rows before fix -- ('26 Четверг.', 'Александринскій', None, None),
('26 Четверг.', 'Маріинскій', None, None), ('26 Четверг.', 'Михайловскій', None, None).
All 3 confirmed to be true "27 Пятница." content mislabeled/truncated -- relabeled and
completed (works + receipts) with scan verification against
ForUpload_1896-97_Repertoire_001.jpg (printed pp.4-5). Also fully rebuilt Малый (which had
its own independent 22-28 Сентября date scramble, 14 -> 21 sessions). Found but NOT fixed:
Александринскій/Маріинскій/Михайловскій/Большой have a broader date-label tangle for
16-26 Сентября (each theater's shift starts at a different row) plus a missing tail
(27 Сентября - 3 Октября) for all 4 theaters -- deferred, see
repertoire-1896-97-pair004-multi-theater-tangle.md.

```sql
select date_text, theater, receipts_text from raw.event_entry
    where page_id='repertoire_1896-97_pair004' and event_status='performed' and receipts_text is null
```

Result: 0 rows after fix -- confirmed against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.

## 2026-09-18 — null-receipts audit page 23: repertoire_1896-97_pair008

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1896-97_pair008' and event_status='performed' and receipts_text is null
```

Result: 4 rows before fix -- all at ('6 Среда.', <theater>) for Александринскій, Малый,
Маріинскій, Михайловскій. Investigation revealed a date-label cascade starting at "4 Ноября.":
every date from there was labeled one true-date-slot too early, dropping true "4 Ноября."
entirely and truncating the shifted-in "7 Четверг." content. Rebuilt all 4 dates x 4 theaters
(4/5/6/7 Ноября), scan-verified against ForUpload_1896-97_Repertoire_003.jpg (printed pp.8-9).
Found but NOT fixed: Большой is absent from this entire file (all dates, not just this range);
also a spurious duplicate "25 Пятница." entry (empty) alongside the correct "25 Октября." for
the same calendar date. Both deferred -- see repertoire-1896-97-pair008-open-issues.md.

```sql
select date_text, theater, receipts_text from raw.event_entry
    where page_id='repertoire_1896-97_pair008' and event_status='performed' and receipts_text is null
```

Result: 0 rows after fix -- confirmed against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.

## 2026-09-18 — null-receipts audit page 24: repertoire_1896-97_pair016

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1896-97_pair016' and event_status='performed' and receipts_text is null
```

Result: 3 rows before fix -- ('21 Вторн.', 'Большой'/'Маріинскій'/'Михайловскій', None).
Titles were already correct, only receipts figures dropped -- fixed directly. Separately,
Александринскій and Малый were entirely missing from this page's extraction across all 13
dates (9-21 Января 1897); recovered both columns in full (26 new sessions), confirming
11 Суббота./18 Суббота are genuinely dark for them too (benefit shows, only Михайловскій
performed). Scan-verified against ForUpload_1896-97_Repertoire_007.jpg (printed pp.16-17).

```sql
select date_text, theater, receipts_text from raw.event_entry
    where page_id='repertoire_1896-97_pair016' and event_status='performed' and receipts_text is null
```

Result: 0 rows after fix -- confirmed against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.

## 2026-09-18 — null-receipts audit page 25: repertoire_1896-97_pair024 (last 1896-97 page)

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1896-97_pair024' and event_status='performed' and receipts_text is null
```

Result: 2 rows before fix -- ('16 Среда.', 'Маріинскій', None, 'Парадный спектакль.') and
('20 Воскресенье.', 'Михайловскій', None, None). The 16 Среда. row confirmed genuinely blank
in the source (a ceremonial "Парадный спектакль" performance with no receipts figure printed
at all) -- legitimate, left as null. The 20 Воскресенье. row was a genuine drop (title already
correct); recovered 558 р. 85 к. Separately, Малый was entirely missing from this page's
extraction across all dates; recovered for 16-24 Апрѣля (8 sessions), confirmed genuinely dark
for 3/4 Апрѣля. and 14/15 Понед./Вторн. Scan-verified against
ForUpload_1896-97_Repertoire_011.jpg (printed pp.24-25).

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1896-97_pair024' and event_status='performed' and receipts_text is null
```

Result: 1 row after fix -- the confirmed-legitimate 16 Среда. Маріинскій "Парадный спектакль."
row (verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb).

## 2026-09-18 — null-receipts audit page 26: repertoire_1897-98_pair006 (first 1897-98 page)

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair006' and event_status='performed' and receipts_text is null
```

Result: 4 rows before fix -- all at ('16 Четв.', <theater>) for Александринскій, Большой,
Маріинскій, Михайловскій. Titles were already correct for all 5 theaters (Малый already had
its receipts) -- only the 4 figures were dropped. Fixed directly, no relabeling needed.
Scan-verified against ForUpload_1897-98_Repertoire_002.jpg (printed pp.6-7).

```sql
select date_text, theater, receipts_text from raw.event_entry
    where page_id='repertoire_1897-98_pair006' and event_status='performed' and receipts_text is null
```

Result: 0 rows after fix -- confirmed against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.

## 2026-09-18 — null-receipts audit page 27: repertoire_1897-98_pair008

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair008' and event_status='performed' and receipts_text is null
```

Result: 4 rows before fix -- ('25 Суббота.', 'Александринскій'), ('26 Воскрес.',
'Александринскій'), ('5 Среда.', 'Александринскій'), ('5 Среда.', 'Маріинскій'), all None.
The first two (Représentation de M-me Réjane guest performances) confirmed genuinely blank in
the source -- no receipts figure printed at all for either. The other two were genuine drops
(titles already correct); recovered 1193 р. 72 к. (Алекс) and 3602 р. 50 к. (Мар).
Scan-verified against ForUpload_1897-98_Repertoire_003.jpg (printed pp.8-9).

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair008' and event_status='performed' and receipts_text is null
```

Result: 2 rows after fix -- the confirmed-legitimate Représentation de M-me Réjane rows
(verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb).

## 2026-09-18 — null-receipts audit page 28: repertoire_1897-98_pair010

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair010' and event_status='performed' and receipts_text is null
```

Result: 5 rows before fix -- ('14 Пятница.', 'Александринскій'/'Малый', None), ('22 Суббота.',
'Александринскій', None, 'Спектакль труппы Берлинскаго Лессингъ-театра.'), ('27 Четверг.',
'Александринскій', None), ('29 Суббота.', 'Александринскій', None, same annotation). 4 of the
5 confirmed genuinely blank in the source: the 2 "14 Пятница." rows are free "Гимнъ" morning
shows for students (no receipts printed), and both German-troupe guest performances (22/29
Суббота.) likewise have no receipts figure printed at all. Only "27 Четверг." was a genuine
drop (title correct); recovered 1583 р. 50 к. Scan-verified against
ForUpload_1897-98_Repertoire_004.jpg (printed pp.10-11).

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair010' and event_status='performed' and receipts_text is null
```

Result: 4 rows after fix -- all confirmed legitimate (verified against rebuilt
outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb).

## 2026-09-18 — null-receipts audit page 29: repertoire_1897-98_pair014

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair014' and event_status='performed' and receipts_text is null
```

Result: 3 rows before fix -- ('2 Пя.', 'Михайловскій'), ('20 Декабря.', 'Александринскій'),
('27 Суббота.', 'Александринскій'), all None. The 2 Александринскій rows (both "Спектакль
г-жи Тины ди Лоренцо" touring guest performances) confirmed genuinely blank in the source --
no receipts figure printed for either. "2 Пя." Михайловскій was a genuine drop (truncated
title, dropped receipts) -- completed to "Le Maître de Forges/Le Bésique chinois, 1450 р. 13
к.", matching the same calendar date's separately-labeled "2 Пятница." entry. Scan-verified
against ForUpload_1897-98_Repertoire_006.jpg (printed pp.14-15).

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair014' and event_status='performed' and receipts_text is null
```

Result: 2 rows after fix -- both confirmed legitimate (verified against rebuilt
outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb).

## 2026-09-18 — null-receipts audit page 30: repertoire_1897-98_pair016

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair016' and event_status='performed' and receipts_text is null
```

Result: 4 rows -- ('18 Воскрес.', 'Большой'/'Малый'/'Маріинскій'/'Михайловскій'), all None, all
the same physical row. Confirmed genuinely illegible: the scan
(ForUpload_1897-98_Repertoire_007.jpg, printed pp.16-17) shows the page physically curling into
the binding fold at exactly this row, swallowing the entire receipts line for Маріинскій,
Большой, Михайловскій, and Малый's evening session -- no digits visible at all, titles above
are legible. Matches the established crease-illegibility pattern (distinct from an extraction
drop). No fix applied -- left as null, confirmed legitimate.

## 2026-09-18 — null-receipts audit page 31: repertoire_1897-98_pair018

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair018' and event_status='performed' and receipts_text is null
```

Result: 7 rows before fix -- ('31 Суббота.', 'Маріинскій'), ('5 Четвергъ.', 'Александринскій'),
('5 Четвергъ.', 'Большой'), ('6 Пятница.', 'Маріинскій'), ('8 Воскресенье.', 'Александринскій'),
('8 Воскресенье.', 'Большой'), ('8 Воскресенье.', 'Маріинскій'), all None. The 3
"8 Воскресенье." rows were genuine drops (titles correct); recovered all 3. The other 4 trace
to a deeper multi-theater date-label tangle: "5 Четвергъ." Алекс/Большой are actually true
"6 Пятн." content (which itself sits on a row where the printed page curls into the binding,
swallowing receipts for ALL theaters that row -- confirmed via scan); "6 Пятница." Маріинскій
is that same crease-affected row's Маріинскій cell; "31 Суббота." Маріинскій is actually true
"1 Воскресенье." content (a charity benefit performance with no receipts printed at all,
confirmed separately). Scan-verified against ForUpload_1897-98_Repertoire_008.jpg (printed
pp.18-19). Full relabeling deferred -- see repertoire-1897-98-pair018-date-tangle.md.

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair018' and event_status='performed' and receipts_text is null
```

Result: 4 rows after fix -- all confirmed legitimate content-wise (mislabeled dates deferred,
verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb).

## 2026-09-18 — null-receipts audit page 32: repertoire_1897-98_pair024 (last page in main worklist)

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair024' and event_status='performed' and receipts_text is null
```

Result: 3 rows -- ('15 Среда.', 'Большой'/'Маріинскій'/'Михайловскій'), all None, same row
(Александринскій/Малый for this date already have their receipts). Confirmed genuinely
unrecoverable: the row sits exactly at the physical bottom edge of the photographed page
(ForUpload_1897-98_Repertoire_011.jpg, printed pp.24-25) -- titles are legible for all 5
theaters but the receipts line itself was never captured in either scan (the next photo
resumes at "16 Четверг.", not a re-photograph of this row). Same precedent as
repertoire_1894-95_p008. No fix applied -- left as null, confirmed genuine.

## 2026-09-18 — annotated-bucket audit page 1: repertoire_1897-98_pair022 (biggest, 8 rows)

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair022' and event_status='performed'
    and receipts_text is null and annotation is not null
```

Result: 8 rows -- all charity/benefit performances by a touring German opera company plus two
Russian invalid-relief/Red-Cross benefit concerts at Большой (14/15 Суббота-Воскресенье
Маріинскій; 19 Четвергъ/21 марта/7 Вторникъ Большой; 21 Суббота Маріинскій; 22
Воскресенье/23 Понед. Большой). All confirmed genuinely blank in the source -- titles/annotations
match the scan exactly, no receipts figure printed for any of them. Scan-verified against
ForUpload_1897-98_Repertoire_010.jpg (printed pp.22-23). Noted in passing: "23 Понед." Большой
has a duplicate entry (empty ann=None + the charity-annotated one, matching "22 Воскресенье."'s
text byte-for-byte) -- likely a duplicate-capture artifact, not touched (both are legitimately
null regardless). No fixes applied -- all 8 confirmed legitimate.

## 2026-09-18 — annotated-bucket audit pages 2-5: repertoire_1892-93_pair004/006/010/020/024

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id=? and event_status='performed' and receipts_text is null and annotation is not null
```

Checked repertoire_1892-93_pair004, pair006 (both 0 rows -- already resolved as part of the
earlier no-annotation-bucket full rebuilds of these same pages). pair010 (2 rows, "14 Суббота."
Большой/Михайловскій, both ann="Гимнъ.") confirmed legitimate -- matches the free student
morning-show row exactly (ForUpload_1892-93_Repertoire_004.jpg, printed pp.10-11), no receipts
printed for any theater that row. pair020 (5 rows, all "Концертъ/Генеральная репетиция/
Повтореніе концерта въ пользу инвалидовъ", Маріинскій + Большой) confirmed legitimate --
charity war-invalid-relief concerts, no receipts printed for any occurrence, scan-verified
against ForUpload_1892-93_Repertoire_009.jpg (printed pp.20-21); noted in passing (not fixed) a
1-day Маріинскій date-shift for 2 of the 5 rows and a spurious duplicate "29 Понед." entry.
pair024 (2 rows): "31 Понедѣльн." Малый confirmed legitimate (matches scan exactly -- "Жрица
искусства"/"Сосѣдъ и сосѣдка, вод." with no receipts printed; also notes an OCR fix needed,
"Крица"->"Жрица", and that the second title belongs in works not annotation, not applied this
pass); "3 Четверг." Малый ("Новое дѣло,ком.", ann="Гимнъ.") left UNRESOLVED -- the same title
recurs on two different true dates in the scan (6 Четвергъ with 1069 р. 97 к., 12 Среда with
231 р. 9 к.) and neither maps unambiguously to file's "3 Четверг." label; genuinely ambiguous,
deferred rather than guessed. Scan-verified against ForUpload_1892-93_Repertoire_011.jpg
(printed pp.24-25).

## 2026-09-18 — annotated-bucket audit pages 6-8: repertoire_1893-94_pair010/016/022

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id=? and event_status='performed' and receipts_text is null and annotation is not null
```

pair016: 0 rows (already resolved). pair022 (1 row, "22 Вторн." Маріинскій, "Повтореніе
концерта въ пользу инвалидовъ.") confirmed legitimate -- matches the charity-concert row
exactly (scan shows it under "23 Среда.", a minor date-label discrepancy not otherwise
investigated), no receipts printed. Scan-verified against ForUpload_1893-94_Repertoire_010.jpg
(printed pp.22-23). pair010 (1 row, "23 Вторникъ." Маріинскій, "Въ пользу школъ Спб. Женскаго
Патриотического Общества...") NOT resolved -- checked ForUpload_1893-94_Repertoire_005.jpg and
_006.jpg (printed pp.12-15) without finding this specific row; this page already has known
date-labeling problems (see repertoire-1893-94-pair010-open-issues.md) that make its true
calendar position unclear. Left unconfirmed rather than assumed from pattern -- added to that
page's existing deferred-issues memory.

## 2026-09-18 — annotated-bucket audit pages 9-10: repertoire_1894-95_pair010/016

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id=? and event_status='performed' and receipts_text is null and annotation is not null
```

pair016: 0 rows (already resolved). pair010 (1 row, "8 Февраля." Маріинскій, annotation
truncated to "Безплатные у") confirmed legitimate -- this is the "Безплатные утренніе спектакли
для воспитанниковъ учебныхъ заведеній" free-show section header (truncated in extraction), no
receipts printed for the whole block. Scan shows it under "9 Февраля." not "8 Февраля." (minor
date-label discrepancy, not investigated further). Scan-verified against
ForUpload_1894-95_Repertoire_004.jpg (printed pp.10-11).

## 2026-09-18 — annotated-bucket audit pages 11-13: repertoire_1895-96_pair006/010/014/016

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id=? and event_status='performed' and receipts_text is null and annotation is not null
```

pair006: 0 rows (already resolved). pair010 (6 rows: "26 Воскресенье." Александринскій
"Безплатный спектакль для гг. георгіевскихъ кавалеровъ." + "6 Среда." all 5 theaters
"Безплатные утренніе спектакли...") confirmed legitimate -- both blocks scan-verified
against ForUpload_1895-96_Repertoire_004.jpg (printed pp.10-11), no receipts printed. pair014
(1 row, "3 Среда." Александринскій, same free-show annotation) confirmed legitimate against
ForUpload_1895-96_Repertoire_006.jpg (printed pp.14-15). pair016 (5 rows: "30 Вторникъ."
Маріинскій/Александринскій/Михайловскій + "31 Среда." Большой/Малый, same free-show pattern
split across two consecutive free-show blocks -- Petersburg theaters on 30th, Moscow theaters
on 31st) confirmed legitimate against ForUpload_1895-96_Repertoire_007.jpg (printed pp.16-17).
This closes out the entire 1895-96 season's annotated bucket -- all 12 rows confirmed
legitimate, no fixes needed.

## 2026-09-18 — annotated-bucket audit pages 14-19: repertoire_1896-97_pair010/012/014/020/022/024

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id=? and event_status='performed' and receipts_text is null and annotation is not null
```

pair010 (2 rows: "14 Четверг." Александринскій "Гимнъ." free-show; "24 Воск." Александринскій
"Спектакль въ память Императрицы Екатерины II.") both confirmed legitimate against
ForUpload_1896-97_Repertoire_004.jpg (printed pp.10-11). pair012 (1 row, "6 Пятница."
Маріинскій, truncated "Безплата") confirmed legitimate -- the free morning-show row (a second,
genuinely-paid evening "Гимнъ."-prefixed session exists on the same date, which is why receipts
appear elsewhere that day); ForUpload_1896-97_Repertoire_005.jpg (printed pp.12-13). pair014
(1 row, "19 Декабря." Александринскій, "Спектакль въ пользу Спб. Дома Милосердія.") confirmed
legitimate against ForUpload_1896-97_Repertoire_006.jpg (printed pp.14-15). pair020 (1 row,
"19 Среда." Маріинскій, truncated/OCR-garbled "Везплам") confirmed legitimate (free-show) against
ForUpload_1896-97_Repertoire_009.jpg (printed pp.20-21). pair022 (1 row, "19 Среда." Большой,
"Концертъ въ пользу инвалидовъ") confirmed legitimate against ForUpload_1896-97_Repertoire_010.jpg
(printed pp.22-23). pair024's row ("16 Среда." Маріинскій, "Парадный спектакль.") was already
confirmed legitimate earlier this session as part of the main no-annotation audit of this same
page. This closes out the entire 1896-97 season's annotated bucket.

## 2026-09-18 — annotated-bucket audit pages 20-23 (final): repertoire_1897-98_p012/pair010/pair012/pair018

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id=? and event_status='performed' and receipts_text is null and annotation is not null
```

pair010's 2 rows and pair018's 2 rows were already confirmed earlier this session as part of the
main no-annotation-bucket work on these same pages (German touring-troupe rows on pair010; the
already-documented date-tangle rows on pair018, tracked in repertoire-1897-98-pair018-date-tangle.md).
p012 (2 rows, "4 Понедѣльник."/"5 Вторникъ.", both "Въ пользу пострадавшихъ отъ недорода хлѣбовъ."
-- famine-relief charity) confirmed legitimate against ForUpload_1897-98_Repertoire_012.jpg
(printed pp.26-27, last page of the season); the second row also sits at the literal last row of
the season, page-edge cut, consistent with the established unrecoverable-edge pattern. pair012
(1 row, "6 Суббота." Маріинскій, ann="Безплатные спектакли для военныхъ") confirmed legitimate --
title matches the scan's free-show row exactly (ForUpload_1897-98_Repertoire_005.jpg, printed
pp.12-13); noted in passing that the annotation text itself appears to be a misread of the
scan's actual header ("для воспитанниковъ столичныхъ учебныхъ заведеній", not "для военныхъ") --
a separate minor annotation-accuracy issue, not touched, doesn't affect the null-receipts finding.

**THIS COMPLETES THE ENTIRE ANNOTATED BUCKET (56 rows) AND THE FULL NULL-RECEIPTS AUDIT
(both buckets, all 8 seasons).**

## 2026-09-18 — deferred-issue resolution 1/7: repertoire_1892-93_pair014 missing theaters

```sql
select distinct theater from raw.event_entry where page_id='repertoire_1892-93_pair014'
```

Before fix: only Маріинскій (1 theater). Full page rebuild: transcribed all 5 theaters for all
22 true calendar dates (27 Декабря 1892 - 16 Января 1893) directly from
ForUpload_1892-93_Repertoire_006.jpg (printed pp.14-15). Found the existing Маріинскій column
itself carried a whole-file date-label shift (every file label held the PREVIOUS true date's
content, e.g. file's old "11 Понед." was really true "10 Воскресенье.") plus a duplicated
benefit performance (Бенефисъ г. Л. Иванова appeared under both "4 Понед." and "6 января.",
really belonging only to true "3 Воскресенье."). Confirmed "6 Среда." is a genuine
crease-illegible row (page physically folds there, swallowing all 5 theaters' receipts --
titles legible, figures not). 25 -> 121 sessions.

```sql
select date_text, theater from raw.event_entry
    where page_id='repertoire_1892-93_pair014' and event_status='performed' and receipts_text is null
```

Result: 4 rows after fix -- all "6 Среда." (the confirmed crease-illegible row), all other
20 dates x 5 theaters fully populated. Verified against rebuilt
outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb. 5 quality flags unchanged (still
exactly 5, no new duplicates introduced by the rebuild).

## 2026-09-18 — deferred-issue resolution 2/7: repertoire_1893-94_pair010

```sql
select distinct theater from raw.event_entry where page_id='repertoire_1893-94_pair010'
```

Before fix: 4 theaters (Малый missing). An initial quick scan check mistakenly concluded Малый
was dark the whole page; a careful full-column crop showed it is genuinely active on most dates.
Recovered Малый for all 20 dates from ForUpload_1893-94_Repertoire_004.jpg (printed pp.10-11).
Also re-verified the earlier "Маріинскій whole-column date shift" theory from the prior session
and found it was a misreading from imprecise cropping -- Маріинскій is almost entirely correctly
labeled already. Real issues found and fixed: "24 Среда." Михайловскій had 2 spurious duplicate
sessions (one copying "23 Вторникъ."'s content, one copying "22 Пон."'s title with a fabricated
receipts figure) -- removed, kept only the correct single session; "29 Понед." Михайловскій had
1 spurious duplicate (copying "28 Воскрес." утро's content) -- removed; "24 Среда." Маріинскій
had a contaminated annotation bled in from the adjacent "23 Вторникъ." cell -- cleared, title
and receipts were already correct; "26 Пятница." Маріинскій had an OCR typo ("Лида" for "Аида").
Confirmed as legitimate (no fix): "22 Пон." Михайловскій is crease-illegible; "23 Вторникъ."
Маріинскій is a charity benefit with no receipts printed (title/annotation match the scan
exactly). 73 -> 91 sessions.

```sql
select date_text, theater, annotation from raw.event_entry
    where page_id='repertoire_1893-94_pair010' and event_status='performed' and receipts_text is null
```

Result: 4 rows after fix -- the 2 confirmed-legitimate rows above, plus "14 Воскресенье." Малый
(the free "Гимнъ" morning show, genuinely blank) and "22 Пон." Малый (this one's receipts sit
directly under a physical binding thread in the scan, genuinely illegible -- left null rather
than guessed). Verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.
5 quality flags unchanged.

## 2026-09-18 — deferred-issue resolution 3/7: repertoire_1894-95_pair006

```sql
select date_text, count(distinct theater) from raw.event_entry
    where page_id='repertoire_1894-95_pair006' group by date_text order by 2
```

Investigation of the originally-flagged "14 Пятн."/"4 Октября." duplicate clusters revealed the
underlying defect actually spans the whole October portion of the page (5-19 Октября):
Александринскій carried its own continuous date-label shift starting at 5 Среда; Михайловскій
had scattered spurious duplicates plus its own shift from 16 Воскресенье onward; Большой had
non-adjacent duplicate/misattributed sessions (including two cases where receipts from January
dates were mistakenly copied onto October rows). Маріинскій and Малый were already almost
entirely correct. Rebuilt all 5 theaters for 4-19 Октября directly from
ForUpload_1894-95_Repertoire_002.jpg (printed pp.6-7); confirmed 1-4 Января were already correct
(the "4 Среда."/"4 Октября." label confusion was just a naming inconsistency -- content was
already right, relabeled to "4 Января." for consistency with its siblings "1 Январь"/"2
Понедѣльникъ"/"3 Вторн."). 109 -> 109 sessions (pure relabel/dedup, no net count change).

```sql
select date_text, theater, annotation from raw.event_entry
    where page_id='repertoire_1894-95_pair006' and event_status='performed' and receipts_text is null
```

Result: 0 rows -- every date now has all 5 theaters, verified against rebuilt
outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb. Quality flags DROPPED from 5 to 4 --
the pre-existing duplicate_event_key flag for this page's "14 Пятн." Большой duplicate is
resolved by this rebuild.

## 2026-09-18 — deferred-issue resolution 4/7: repertoire_1895-96_pair006

```sql
select date_text, count(distinct theater) from raw.event_entry
    where page_id='repertoire_1895-96_pair006' group by date_text order by 1
```

Untangled the scattered Маріинскій/Михайловскій duplicates and recovered the missing
Александринскій/Малый for 22-28 Октября (Большой confirmed genuinely dark throughout the whole
page, already established). Specific fixes: relabeled "17 октября." Маріинскій to "17 Вторн."
(true 17 Вторн content was otherwise entirely missing); removed 3 spurious duplicate sessions
("18 Среда." Маріинскій morning + "18 октября." Маріинскій, both duplicating already-correct
content from 17 Вторн/16 Понед; "18 Среда." Михайловскій morning, duplicating 17 Вторн);
recovered a dropped "8 Октября." Малый evening session (a duplicate of it had been mistakenly
captured under "9 Понед." instead, removed separately); fixed an OCR typo ("Вольницы"->
"Невольницы"); recovered Александринскій + Малый for 22-28 Октября (16 new sessions).
Scan-verified against ForUpload_1895-96_Repertoire_002.jpg (printed pp.6-7). 77 -> 90 sessions.

```sql
select date_text, theater, annotation from raw.event_entry
    where page_id='repertoire_1895-96_pair006' and event_status='performed' and receipts_text is null
```

Result: 0 rows -- verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.
4 quality flags unchanged.

## 2026-09-18 — deferred-issue resolution 5/7: repertoire_1896-97_pair004

```sql
select date_text, count(distinct theater) from raw.event_entry
    where page_id='repertoire_1896-97_pair004' group by date_text order by 1
```

Full rebuild of Александринскій, Маріинскій, Михайловскій, Большой for the whole page
(12 Сентября - 3 Октября 1896). Precisely pinned down each theater's shift onset via direct
receipts-figure matching against the scan: Александринскій and Михайловскій both shift starting
at "16 Понед." (with true 16 Понед content duplicated onto a spurious extra "15 Воскрес." entry
for each), continuing through "27 Пятница." (already fixed earlier this session); Маріинскій has
its own separate shift starting at "21 Суббота." (a genuinely dark day for it, whose true content
got skipped, and everything from "22 Воскрес." onward held the next day's content); Большой was
never shifted throughout. All four were also missing 28 Сентября-3 Октября entirely -- recovered.
Малый (already fixed earlier this session) was left untouched. Scan-verified against
ForUpload_1896-97_Repertoire_001.jpg (printed pp.4-5). 75 -> 101 sessions.

```sql
select date_text, theater from raw.event_entry
    where page_id='repertoire_1896-97_pair004' and event_status='performed' and receipts_text is null
```

Result: 0 rows -- verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.
Every date now has all 5 theaters (4 on the two genuinely-dark-for-most-theaters Saturdays,
21/28 Суббота, correctly). 4 quality flags unchanged.

## 2026-09-18 — deferred-issue resolution 6/7: repertoire_1896-97_pair008

```sql
select date_text, count(distinct theater) from raw.event_entry
    where page_id='repertoire_1896-97_pair008' group by date_text order by 1
```

Full page rebuild (25 Октября - 13 Ноября 1896, the full extent of this scan). Discovered a
UNIFORM date-label shift affecting ALL theaters simultaneously (unlike other pages' per-theater
independent shifts) starting at "26 Суббота." -- every date from there was one true-date-slot
too early, with a spurious duplicate "25 Пятница." entry (really true 26 Суббота content) and
"3 Воскрес." entry (an exact duplicate of the already-correctly-fixed "4 Ноября.") left behind.
Большой was entirely missing throughout the whole page. The tail beyond the already-fixed
4-7 Ноября (8-13 Ноября) was missing entirely for all 5 theaters. Independently re-confirmed
the earlier 4-7 Ноября fix was correct (matches this fresh reading exactly) -- only needed
Большой added there. Scan-verified against ForUpload_1896-97_Repertoire_003.jpg (printed
pp.8-9). 64 -> 106 sessions.

```sql
select date_text, theater from raw.event_entry
    where page_id='repertoire_1896-97_pair008' and event_status='performed' and receipts_text is null
```

Result: 0 rows -- verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.
Every date now has all 5 theaters. 4 quality flags unchanged.

## 2026-09-18 — deferred-issue resolution 7/7 (FINAL): repertoire_1897-98_pair018

```sql
select date_text, count(distinct theater) from raw.event_entry
    where page_id='repertoire_1897-98_pair018' group by date_text order by 1
```

Full page rebuild (29 Января - 8 Февраля 1898). Confirmed Александринскій and Большой share one
continuous date-label shift running from "29 Четвергъ." (a duplicate of "29 января.") through
"7 Суббота." (=true 8 Воскресенье утро); Маріинскій has its own separate, much shorter shift
(29-31 Января only, self-resolving by 2 Понедѣльникъ.). Recovered Михайловскій and Малый, both
entirely missing from this file (not just Михайловскій, as originally noted). Confirmed "6
Пятница." is genuinely crease-illegible for all 5 theaters (titles legible, receipts swallowed
by the binding fold). The 3 genuine drops at "8 Воскресенье." fixed earlier this session were
independently re-confirmed correct against this fresh, careful reading. Scan-verified against
ForUpload_1897-98_Repertoire_008.jpg (printed pp.18-19). 36 -> 59 sessions.

```sql
select date_text, theater, annotation from raw.event_entry
    where page_id='repertoire_1897-98_pair018' and event_status='performed' and receipts_text is null
```

Result: 6 rows after fix -- "1 Воскресенье." Маріинскій (confirmed charity benefit, no receipts
printed) and all 5 theaters at "6 Пятница." (confirmed crease-illegible). Every date has all 5
theaters. Verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.
4 quality flags unchanged.

**THIS RESOLVES THE LAST OF THE 7 DEFERRED MULTI-THEATER TANGLES FROM ISSUE #70.**

## 2026-09-18 — final unresolved rows 1/2: repertoire_1893-94_pair010

```sql
select date_text, theater, receipts_text, annotation from raw.event_entry
    where page_id='repertoire_1893-94_pair010' and event_status='performed' and receipts_text is null
```

Both remaining open items resolved by re-checking ForUpload_1893-94_Repertoire_004.jpg (printed
pp.10-11) with a cleaner, more precisely-targeted crop than the earlier pass. "23 Вторникъ."
Маріинскій (ann="Въ пользу школъ Спб. Женскаго Патриотического Общества...") confirmed
genuinely blank -- the scan shows this exact annotation text with no receipts figure printed
beneath it at all (unlike the adjacent Александринскій cell on the same row, which does show a
figure). "22 Пон." Михайловскій confirmed thread-obscured -- the same physical binding thread
that crosses this entire row (already accepted as the explanation for the adjacent "22 Пон."
Малый cell) also crosses directly through Михайловскій's receipts position; title
("Венецейскій истуканъ, карт. / Бѣдовая дѣвушка, вод.") is legible, figure is not. Both left
null, confirmed legitimate. No data changes -- 91 sessions unchanged.
