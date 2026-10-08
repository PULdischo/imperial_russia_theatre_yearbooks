
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

## 2026-09-18 — final unresolved row 2/2: repertoire_1892-93_pair024

```sql
select date_text, theater, receipts_text from raw.event_entry
    where page_id='repertoire_1892-93_pair024' and theater='Малый' order by date_text
```

Resolved the ambiguity: "3 Четверг." Малый (title "Новое дѣло, ком.", ann="Гимнъ.") relabeled
to true "6 Четвергъ." -- confirmed via weekday-name matching. The title recurs twice in the
scan (true 6 Четвергъ. at 1069 р. 97 к., true 12 Среда. at 231 р. 9 к.), but only the 6
Четвергъ. occurrence shares the file label's weekday name ("Четвергъ"); separately confirmed
the file's own nearby date labels for this stretch (1 Вторник./2 Среда./3 Четверг.) do NOT
match the true calendar (true 3-4 Мая 1893 were Понедельникъ/Вторникъ per the scan's own date
column, not Среда/Четвергъ), establishing that weekday-name matching is the reliable
disambiguator for this page. Scan-verified against ForUpload_1892-93_Repertoire_011.jpg
(printed pp.24-25).

```sql
select date_text, theater, receipts_text from raw.event_entry
    where page_id='repertoire_1892-93_pair024' and event_status='performed' and receipts_text is null
```

Result: 1 row -- "31 Понедѣльн." Малый, already confirmed legitimate earlier this session
(genuinely obscured by the physical page fold, visible as a diagonal crease line in the scan
right through that row). Verified against rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.
4 quality flags unchanged.

**THIS RESOLVES THE LAST OF THE TWO INDIVIDUALLY-UNRESOLVED ROWS FROM THE ENTIRE #70 NULL-RECEIPTS AUDIT.**

## 2026-09-18 — date_undate fill rate and correctness check after the two-page-spread header backfill (issue #72)

```sql
-- fill rate
SELECT count(*), count(date_undate) FROM raw.event_entry;
```

Result: 4937/4939 = 99.96% filled (the 2 nulls are genuine -- `repertoire_1894-95_pair010`'s
two "Февр." sessions carry no day number at all).

```python
# programmatic cross-check: every date_undate against its own page's scan-verified
# (start_date, end_date) window, from the 88-row page_header_dates.csv
```

Result: 0 invalid calendar dates, 0 wrong-month/year assignments; 3 rows fall slightly outside
a page's window because that page's own `end_day` estimate undersold its true extent within the
same end_month (harmless, not a correctness issue).

```bash
uv run python pipeline/validate_performance_dates.py --db outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb
```

Result: verified 3924 (79.4%), intra_block_disagreement 767 (15.5%), corrected 204 (4.1%),
unresolved 42 (0.9%), no_date 2 (0.0%) -- independent Julian-calendar weekday corroboration
that the backfilled dates are correct, not just internally consistent with their own headers.
Prior baseline (unheadered spread dates, outputs/fold_review/README.md): 35.6% weekday mismatch.

## 2026-09-18 — characterizing the 42 'unresolved' rows from validate_performance_dates.py (follow-up to issue #72)

```sql
SELECT e.page_id, e.event_id, e.date_text, e.theater, e.date_undate, d.date_confidence
FROM analysis.event_entry_date_check d JOIN raw.event_entry e USING (event_id)
WHERE d.date_confidence = 'unresolved' ORDER BY e.page_id, e.date_undate;
```

Result: 42 rows across 9 pages. Largest cluster: repertoire_1891-92_pair004, 21 rows (3
consecutive dates, 1/2/3 Сентября 1891, ~5-6 theaters each). Computed true weekday (Julian,
convertdate.julian.jwday) vs. parsed printed weekday for all 42: every row shows a small,
consistent offset (1-2 days) between what the day-number implies and what the printed weekday
word says -- matching validate_performance_dates.py's own documented "day number drift" defect
(module docstring: concentrated in the 1891-92 through 1896-97 seasons), not something
introduced by today's date_undate backfill.

Debug-traced why the 1891-92_pair004 3-day run didn't auto-correct despite sharing the same
+2-day offset: the script's run-detection walks blocks in `event_id` order (raw file/session
print order), not calendar order. Confirmed directly -- block_order for this page shows
1891-09-01, then 1891-09-11, then 1891-09-19, then 1891-09-02 -- i.e. Sep2's block is NOT
adjacent to Sep1's in file order, because (same root cause as issue #72's pipeline fix) this
page's session lists aren't stored chronologically. The Sep11/19 blocks in between are
'verified' (no mismatch), breaking the run and leaving Sep1/2/3 each as an isolated
single-block run, which can't meet _MIN_RUN_AGREEMENT=2 alone. This is a real, separate
follow-on consequence of the non-chronological-session-order root cause, but in a different
script (validate_performance_dates.py) that issue #72 did not touch -- noted for a possible
future fix, not addressed today.

## 2026-09-18 — scan-checked all 9 pages behind the 42 'unresolved' rows (follow-up to issue #72)

Read the actual render image for at least one representative flagged date on each of the 9
pages. Findings:

1. `repertoire_1890-91_pair018` and `repertoire_1891-92_pair002`/`pair004` had never been
   individually re-scanned this session -- they were still using the original, already-proven-
   unreliable "single anchor month, trusted for whole page" guess. Checked directly:
   - `1890-91_pair018`: guess was "1-31 Января 1891"; scan (`ForUpload_1890-91_Repertoire_008.jpg`)
     shows the true range is 25 Января - 13(+) Февраля 1891, with the day-1/2 stragglers at the
     front of the file's own session order actually being Feb 1-2 (weekday-confirmed: true
     Feb1,1891=Пятн., Feb2=Субб., matching the printed labels exactly). A real, previously-missed
     header error -- FIXED, see known_issues.md.
   - `1891-92_pair002`/`pair004`: the "1-30 Августа"/"1-30 Сентября" guesses turned out to be
     directionally correct (confirmed against `ForUpload_1891-92_Repertoire_000.jpg`, which shows
     Aug16-Sep10 continuously) -- NOT a header bug. But the 3 flagged September 1/2/3 rows
     revealed something else: the scan clearly shows "1 Восир.(Sun)/2 Понед.(Mon)/3 Вторникъ(Tue)"
     while raw `date_text` for all 5 theaters says "1 Вторн./2 Среда/3 Четверг" (each 2 weekdays
     later) -- a pre-existing raw-extraction weekday-word misread, confirmed on the page itself,
     NOT a date_undate error (date_undate for these 3 rows is already correct -- matches both the
     scan's day column and true Julian weekday).

2. Found and fixed a real bug in today's own `_backfill_month_year` patch: the `_MONTH_LENGTH`
   sanity check hardcoded февраля=28, not accounting for Julian leap years (1892, 1896 in this
   corpus). This wrongly reassigned genuine "29 Суббота."/"29 Четвергъ." February 29th sessions to
   March 29th instead. Confirmed directly: `repertoire_1891-92_pair018`'s "29 Суббота." scan
   (`ForUpload_1891-92_Repertoire_008.jpg`) shows Feb29,1892 as Суббота -- true weekday (Julian)
   for 1892-02-29 is also Суббота; but 1892-03-29 (where the old bug sent it) is a Sunday, hence
   the mismatch. Same root cause hit `repertoire_1895-96_pair020`'s "29 Четвергъ." (1896 also a
   leap year). FIXED -- see known_issues.md.

3. The remaining pages checked (`1890-91_pair024`, `1892-93_pair024`, `1894-95_pair008`,
   `1895-96_pair002`) all show the SAME kind of pre-existing, isolated date_text weekday/day-number
   drift already documented in `validate_performance_dates.py`'s own module docstring (concentrated
   in 1891-92 through 1896-97) -- e.g. `1892-93_pair024`'s flagged "3 Четверг." Большой is a blank
   dark-day placeholder (no real content) whose weekday word is simply wrong; the true row for that
   date on the scan is blank too, just correctly labeled "3 Понедѣльн." One page
   (`1894-95_pair008`, "25 Суббота.") appears to be a genuine PRINTING error in the original 1895
   volume itself (real content, weekday label doesn't match the true calendar, but the scan itself
   prints "25 Суббота." right where the raw JSON has it) -- correctly left as-is per the project's
   verbatim-transcription rule, nothing to fix.

Reran the full pipeline after the two fixes: unresolved dropped 42 -> 34 (exactly the 8 rows the
two bugs affected); verified rose 79.4% -> 79.9%; corrected 204 -> 190; quality_flags.csv
unchanged at 4. Remaining 34 unresolved rows are all the pre-existing date_text extraction defect
described in point 3 above -- confirmed not a date_undate/header problem, a separate, already-
documented issue outside this task's scope.

## 2026-09-18 — fixed the remaining unresolved rows individually (follow-up to issue #72)

Full row-by-row content verification (titles, and receipts where the season has them) against
the actual scans for each of the 6 pages behind the 42 originally-unresolved rows. Result:

- `repertoire_1890-91_pair024` (3 rows): pure weekday-word fix, "22 Пятница." -> "22 Понед."
  (day/month/receipts all already correct).
- `repertoire_1892-93_pair024` (1 row): pure weekday-word fix on a blank dark placeholder,
  "3 Четверг." -> "3 Понедѣльн." (Большой).
- `repertoire_1891-92_pair002` (3 rows): the two sessions both labeled "17 Среда." (Малый)
  actually belong to two different true dates -- title-matched against
  `ForUpload_1891-92_Repertoire_000.jpg` and split into "18 Воскрес." (morning) and
  "19 Понед." (evening). The third row, a blank/dark "1 Воскр." Малый placeholder with zero
  content (no works, no receipts, no annotation) and no plausible true-August-1 position
  (the season doesn't open before Aug16 per the render, and this entry's own content is
  empty), was removed as a spurious duplicate artifact.
- `repertoire_1891-92_pair004` (16 rows) -- the big one. Full row-by-row cross-check against
  BOTH `ForUpload_1891-92_Repertoire_000.jpg` (Aug16-Sep10) and `_001.jpg` (Sep11-Oct7) found
  this page's header was fundamentally wrong (old single-anchor guess: "1-30 Сентября"). The
  raw JSON's day-1/2/3 sessions for every theater already correctly match OCTOBER 1/2/3
  content verbatim (title AND weekday both match October, not September) -- they only needed
  the right month assigned, not any date_text edit. Corrected header to
  `start_day=11, start_month=сентября, end_day=7, end_month=октября` (matches
  `repertoire_1891-92_pair006`'s already-confirmed Oct8-27 start with zero overlap -- strong
  corroboration). Also found and removed one genuine duplicate: Малый's "28 Сентября."
  session was an exact content duplicate of the real "29 Воскрес." session (true Sept28 is
  blank for Малый per the scan). Residual, NOT fixed: one stray Александринскій "1 Вторн."
  (evening) session (Василиса Мелентьева/Фотографъ-любитель) whose true date wasn't found in
  the Aug16-Oct7 range read this pass -- left as-is, low priority (doesn't block anything,
  single row).
- `repertoire_1895-96_pair002` (6 rows): receipts-figure matching against
  `ForUpload_1895-96_Repertoire_000.jpg` found a 3-way date scramble -- raw's "26 Воскрес."
  and "27 Четверг." labels actually cover THREE different true dates (27 Воскр., 31 Четвергъ.,
  and 1 Пятн. of the following month). Fixed all 4 non-blank rows via receipts-figure exact
  match (1356 р./808 р./1347 р./404 р.25 к.). Fixing the last one (Михайловскій -> "1 Пятн.")
  collided with an ALREADY-mislabeled pre-existing session at that same key (2134 р.20 к.,
  Севильскій цирюльникъ) -- title/receipts-matched that one too, to true "3 Воскр." (Sept3).
  That reassignment collided with YET ANOTHER pre-existing session already sitting at
  "3 Воскр." (675 р.63 к., Первая муха/Угасшая искра/Изъ-за мышенка) whose true date wasn't
  found in a search through Sep1-15 this pass -- stopped chasing this specific sub-thread
  (out of the original 42-row scope) and left it as an honestly-flagged
  `duplicate_event_key` for a future pass, rather than silently guessing. The 2 blank/dark
  "Большой" rows at "26"/"27" (zero content either way) were left unfixed -- no data impact.
- `repertoire_1894-95_pair008` (5 rows): re-confirmed as a genuine printing error in the
  original 1895 volume itself (the scan literally prints "25 Суббота." at that row; true
  Jan25,1895 was a Среда) -- correctly left verbatim per project convention, no fix.

Reran the full pipeline (parse_and_validate -> build_duckdb -> quality_checks ->
validate_performance_dates) after all fixes: unresolved 42 -> 6 (all 6 fully explained: the 5
genuine-printing-error rows above, plus the 1 remaining blank Большой row). verified rose to
80.8%. `quality_checks.py` went from 4 to 6 flags -- both NEW flags are honest surfacing of
pre-existing problems, not new breakage: `zero_dark_cells_on_multiweek_page` on
`1891-92_pair002` (removing the spurious "1 Воскр." dark placeholder unmasked that this page
has no other captured dark day at all -- likely a genuinely missing Aug24/Суббота row, not
something introduced here) and the `duplicate_event_key` on `1895-96_pair002`'s "3 Воскр."
Михайловскій described above.

## 2026-09-18 — found the 1895-96_pair002 missing date; audited all 8 remaining unscanned page headers (follow-up to issue #72)

**Missing date found**: Михайловскій's session at 675 р.63 к. ("Первая муха"/"Угасшая искра"/
"Изъ-за мышенка"), left unresolved in the prior pass, is confirmed as true **"4 Понедѣльн."**
(Sept 4, 1895) -- exact match on all 3 titles and the receipts figure, found in
`ForUpload_1895-96_Repertoire_000.jpg`. Fixed with no collision. `duplicate_event_key` flags
dropped from 4 to 3 (the 3 remaining are pre-existing, unrelated to #72, on 1897-98 pages).

**Header re-audit**: checked the pickle for any page still carrying the original unverified
"single anchor month, trusted for whole page" note (never individually re-scanned this
session, as opposed to "CONFIRMED"/"CORRECTED" notes from actual scan checks). Found 8:
`1890-91_p000`, `1890-91_pair004`, `1890-91_pair006`, `1890-91_pair016`, `1890-91_pair020`,
`1891-92_pair002`, `1891-92_pair006`, `1891-92_pair012`. Scan-checked all 8 against their
renders:

- `1890-91_p000`: CONFIRMED correct (16-26 Августа).
- `1890-91_pair004`: CORRECTED -- true range is 27 Августа-21 Сентября (was guessed as
  10-21 Сентября only). Scan-verified `ForUpload_1890-91_Repertoire_001.jpg`.
- `1890-91_pair006`: CORRECTED -- true range is 22 Сентября-11 Октября (was guessed as
  2-11 Октября only). Scan-verified `ForUpload_1890-91_Repertoire_002.jpg`. Neither correction
  changed any date_undate values -- the raw JSON simply has no session data in the
  newly-added day range, so this is a header-accuracy fix for future extraction work, not a
  regression fix.
- `1890-91_pair016`: no header fix needed for date_undate correctness -- it's a genuine
  single-month January page (confirmed via explicit "14 Января."/"15 Января." inline anchors),
  so the threshold logic never triggers regardless of exact day bounds. BUT found a real,
  separate data question: pair016's own day-10-18 entries appear to duplicate/overlap with
  the already-confirmed-correct `1890-91_pair022` (also Jan 10-23, German-language touring-
  troupe content, scan-verified as genuinely distinct from pair016's Russian repertoire) --
  deliberately NOT chased further, out of scope, documented as a new deferred item (see memory).
- `1890-91_pair020`: no cross-month evidence in the raw day sequence (14-26, single Михайловскій
  theater only, explicit "14 Февраля." anchor) -- left as-is, low risk.
- `1891-92_pair002`, `1891-92_pair006`, `1891-92_pair012`: no cross-month evidence (clean day
  sequences, no stray low-day entries after this session's earlier `pair002` cleanup) --
  `1891-92_pair006`'s Oct8 start also lines up with zero overlap against the newly-corrected
  `1891-92_pair004`'s Oct7 end, corroborating both.

Reran the full pipeline after all fixes. Full 88-page cross-check against scan-verified
windows: 2 violations remain, both the same already-understood harmless case
(`1892-93_pair024`'s header end_day being a conservative underestimate within the correct
end_month, not a real error). `quality_checks.py`: 5 flags (duplicate_event_key 3 -- back to
baseline; zero_dark_cells_on_multiweek_page 1; receipts_parse_failed 1).
`validate_performance_dates.py`: unresolved unchanged at 6 (both header fixes didn't touch any
existing date_undate values, as noted above), verified 80.8%.

## 2026-09-18 — resolved the repertoire_1890-91_pair016/pair022 question: pair022 was mislabeled as January all along, true content is March

Re-read `ForUpload_1890-91_Repertoire_007.jpg` (the render supposedly shared by both pages)
row by row for all 5 theater columns, days 10-18. Every single one of `pair016`'s own entries
for that range matched the scan exactly (title-for-title: "10 Четвергъ."=Цѣпи/Сцена г.Горбунова,
"11 Пятница."=Раздѣлъ/Гость/Первое декабря..., "14 Понед."=Симфонія/Дочь русскаго актера,
"15 Вторникъ."=Цѣпи/Азъ и Фертъ, "16 Среда."=Озимь/Старое старится.../Сцена г.Горбунова). My
first read of this row (in the prior session segment) had mismatched day8's Alexandrinsky
title with day10's row -- a misreading on my own part, not a data problem. Conclusion:
pair016 is genuine, correct January 3-18 content, not a duplicate of anything.

That meant pair022's own German/French-titled content (Das zweite Gesicht, Die Haubenlerche,
Thermidor, etc., all under a suspiciously perfect no-gaps day10-23 sequence with an odd
"10 Март." label) had to belong somewhere else. Read `ForUpload_1890-91_Repertoire_009.jpg`
(14 Февраля - 3 Марта 1891, showing "Thermidor, dr." recurring for Михайловскій) and
`ForUpload_1890-91_Repertoire_010.jpg` (10 Марта - 29 Марта 1891) -- exact match: render010's
"10 Воскр." row shows Александринскій="Das zweite Gesicht, Lustsp." and
Михайловскій="Thermidor, dr.", and "11 Понед." shows Александринскій="Die Haubenlerche,
Schausp." -- identical to pair022's own "10 Март."/"11 Понед." entries. Weekday cross-check
(Julian): true 1891-03-10 = Воскресенье, true 1891-03-23 = Суббота -- both match the file's
own labels exactly.

**Conclusion: `repertoire_1890-91_pair022` was never January at all.** Its true content is
10-23 Марта 1891 (a German/French touring-troupe schedule for the Alexandrinsky/Mikhailovsky/
Bolshoy/Maly columns). Corrected the header (`10 марта. 1891 г. 23 марта.`). Reran the full
pipeline: `date_undate` for every one of this page's ~52 sessions is now correctly March
instead of January. `validate_performance_dates.py`: verified rose 80.8% -> 81.9%, corrected
dropped 170 -> 118 (these 52 rows no longer need a weekday-based shift-correction, they're
directly right). unresolved unchanged at 6. Full 88-page window cross-check: still only the
2 same already-understood harmless cases (1892-93_pair024's end_day underestimate).

Noted but not chased further: render010 continues with distinct content through 29 Марта
(Das letzte Wort, Der Unterstaatssecretair, etc.) beyond pair022's day23 end -- this
March24-29 stretch doesn't appear to be captured under any existing page_id, consistent with
the missing-page pattern already documented elsewhere in this corpus.

## 2026-09-19 — pursued whether any other page shares pair022's wrong-month bug

RG asked to pursue the residual risk flagged after fixing `1890-91_pair022` (mislabeled
January, real content was March): could another "confident" page have the same undetected
wrong-month mislabeling? Ran three computational checks against all 88 pages:

1. **Date-range overlap** (using confident_headers_v3.pkl's per-page windows): 3 overlapping
   pairs found (`1895-96_pair008`/`p012`, `1895-96_p012`/`pair010`, `1897-98_pair020`/
   `pair022`). Checked each against actual raw session day-numbers: all 3 trace to an
   imprecise `end_day` upper-bound estimate in the header (e.g. `p012`'s real content only
   reaches day 17, header guessed 26) -- not genuine duplicate content. None are a repeat of
   pair022's problem.
2. **Inline month-name conflict**: scanned every session's own `date_text` across all 88 pages
   for a month name that disagrees with its page's assigned header month (exactly pair022's
   original signature: "10 Март." inside a page then-labeled January). 0 matches.
3. **Zero-Cyrillic-content pages**: 5 pages have works entirely in Latin script across every
   session -- `1890-91_pair022` (already fixed), `1891-92_pair018`, `1892-93_pair018`,
   `1895-96_pair020`, `1896-97_pair022`. Investigated the latter 4:
   - `1896-97_pair022` (Александринскій=German, Михайловскій=French, Большой=Italian opera,
     simultaneously, mid-Lent 1897): scan-verified against `ForUpload_1896-97_Repertoire_
     010.jpg` -- exact title+receipts match on every row checked (Gräfin Fritzi/Abu Seid
     1943р.11к; Rigoletto 2000р.10к; Gli Ugonotti 3152р.30к, etc.). Genuine: multiple foreign
     touring companies performing simultaneously during Great Lent, when Russian-language
     dramatic performance was restricted, is real documented historical practice, not a data
     error.
   - `1895-96_pair020` (Александринскій=German, Михайловскій=French, Feb28-Mar29 1896, also
     Lenten): scan-verified against `ForUpload_1895-96_Repertoire_009.jpg` -- exact match
     (Cardillac/Untreu 2479р.10к; Feu Toupinel/Camille 661р.5к), and the scan shows normal
     Russian repertoire resuming right at the end of the window (Lent's end), consistent with
     the pattern. Genuine.
   - `1891-92_pair018`, `1892-93_pair018`: both single-theater (Михайловскій only, its
     regular resident French troupe -- an extremely common, already-repeatedly-confirmed
     pattern throughout this whole corpus), both already date-range-verified this session.
     Lower priority, not individually re-verified further.

**Conclusion: no second pair022 found.** The two checks that would have caught it (overlap,
inline-month-conflict) come back clean corpus-wide, and the one class of page that superficially
resembled it (all-foreign-language content) turned out on direct verification to be genuine
historical Lenten programming, not mislabeling.

## 2026-09-19 — consolidated every date-coverage gap in the two-page-spread corpus into one inventory

RG asked to pull the many individually-noted missing-page mentions from this session (and the
2026-08-24 audit) into one consolidated list. Computed gaps between consecutive scan-verified
page date-ranges per season using confident_headers_v3.pkl (the same data issue #72 built and
fully verified this session):

```python
# per season: sort pages by (start_date, end_date), flag any gap of >1 day between
# one page's end and the next page's start
```

Result: 12 gaps found across the 8 seasons (after filtering out three 1-day boundary artifacts
from header end_day imprecision, not real gaps). Classified each against what was actually
directly confirmed by reading the render this session or in the 2026-08-24 audit: 9 confirmed
"extraction gaps" (real printed content exists on a render, no page_id captures it -- recoverable
in principle), 1 confirmed "scan gap" (1890-91 Oct12-31, book's own page numbers skip 7->10, never
photographed, not recoverable), 1 plausible Holy Week/Easter closure (1893-94 Apr9-17, no render
covers either side of the gap at all), and 1 genuinely unconfirmed (1890-91 Mar4-9, not yet checked
against any render). Full table written to docs/eval/known_issues.md issue #73.

## 2026-09-19 — recovered 1893-94's season-opener extraction gap (17 Августа - 3 Октября 1893)

RG asked to recover the largest confirmed extraction gap from issue #73's inventory. Manually
transcribed both renders in full (no paid API call, same methodology as the rest of this
session): `ForUpload_1893-94_Repertoire_000.jpg` (17-27 Августа + 30 Августа-10 Сентября,
100 sessions -> new page `repertoire_1893-94_pair002`) and `_001.jpg` (12 Сентября-3 Октября,
100 sessions -> new page `repertoire_1893-94_pair004`). All 5 theaters transcribed per date
where printed; blank-dash cells recorded as explicit `is_dark: true` (not omitted), matching
project convention. Two rows left honestly incomplete: `pair002`'s "27 Пятница." Малый receipts
and `pair004`'s entire "23 Четвергъ." row (all 5 theaters) are swallowed by the physical binding
fold in the scan -- titles legible, receipts not, confirmed by direct close-up re-check.

Added both to `manifest.csv` and `page_header_dates.csv` (`pair002`: 17 августа-10 сентября 1893;
`pair004`: 12 сентября-3 октября 1893). Reran the full pipeline: `event_entry` 4937 -> 5137
(+200, exactly the transcribed sessions), 0 new validation errors (the 1 pre-existing flag is
unrelated), `quality_checks.py` unchanged at 5 flags, full 90-page date-window cross-check clean
(same 2 pre-existing harmless cases only). `validate_performance_dates.py`: verified rose
81.9% -> 82.5%. One new genuinely-flagged row found and confirmed as a real source-printing
inconsistency (not a transcription error): `pair004`'s "13 Среда." (all 5 theaters) -- re-zoomed
the scan to confirm the digit is definitely "13" not "15", but 13 Сентября 1893 was actually a
Monday, not Wednesday -- same class of verbatim-preserved printing quirk as `1894-95_pair008`'s
"25 Суббота.", left as printed.

## 2026-09-19 — recovered the remaining 7 confirmed extraction gaps (issue #73, "all of them, one at a time")

Manually transcribed all 7 remaining confirmed extraction gaps from the issue #73 inventory --
no paid API calls, same discipline as the rest of this project. Summary (full detail in
known_issues.md's addenda):

- `repertoire_1891-92_p003` (31 Августа-10 Сентября 1891, 45 sessions) -- Aug31 (a Saturday) has
  no printed row at all; real content starts Sep1. From `ForUpload_1891-92_Repertoire_000.jpg`,
  already read during issue #72's pair004 investigation.
- `repertoire_1893-94_pair014` (26 Декабря 1893-14 Января 1894, 120 sessions) -- a dense page
  with frequent morning/evening splits and a free "Гимнъ" (Hymn) student-matinee day (26 Дек).
  From `ForUpload_1893-94_Repertoire_006.jpg`.
- `repertoire_1893-94_pair020` (23 Февраля-19 Марта 1894, 116 sessions) -- confirmed the
  now-familiar Lenten pattern (German troupe/Alexandrinsky, French/Mikhailovsky, blank
  Маріинскій+Малый) starting 6 Марта; Feb28-Mar5 has no printed rows (first week of Great
  Lent). From `ForUpload_1893-94_Repertoire_009.jpg`.
- `repertoire_1894-95_pair012` (19 Февраля-14 Марта 1895, 100 sessions) -- same Lenten pattern
  (only Александринскій/Михайловскій active, German/French). Found Feb13-18 has no available
  render at all (neither the prior nor this render covers it) -- reclassified from "extraction
  gap" to a probable first-week-of-Lent closure, not recoverable. From
  `ForUpload_1894-95_Repertoire_005.jpg`.
- `repertoire_1895-96_pair012` (7-29 Декабря 1895, 111 sessions) -- ordinary full 5-theater
  programming, no Lenten pattern (December, not Lent). From
  `ForUpload_1895-96_Repertoire_005.jpg`.
- `repertoire_1890-91_p015` (28 Декабря 1890-2 Января 1891, 55 sessions) -- from
  `ForUpload_1890-91_Repertoire_006.jpg` (the same render already used for the adjacent
  `pair014`/`pair016` boundary work in issue #72).
- `repertoire_1890-91_p023` (24 Марта-12 Апрѣля 1891, 77 sessions) -- Lenten pattern again
  (Александринскій=German, Михайловскій=French, others blank). Found Apr13-21 has no printed
  rows at all -- matches the established recurring Holy Week/Easter closure pattern (Easter
  1891 O.S. fell Apr21) exactly, reclassified as not recoverable, not a gap. Confirmed Apr22
  onward is already captured in the existing `pair024`. From `ForUpload_1890-91_Repertoire_
  010.jpg` (Mar24-29 tail) + `_011.jpg` (Mar30-Apr12).

Reran the full pipeline after all 7: `event_entry` 5418 -> 5761, 0 new validation errors,
`quality_checks.py` unchanged at 5 pre-existing flags, full 97-page date-window cross-check
clean (same 2 pre-existing harmless cases only). `validate_performance_dates.py`: verified rose
82.5% -> **84.3%**; all 11 remaining unresolved rows are the same already-explained cases from
before (5 rows: `1893-94_pair004`'s "13 Среда." genuine printing inconsistency; 5 rows:
`1894-95_pair008`'s "25 Суббота." genuine printing inconsistency; 1 row: a blank placeholder) --
nothing new introduced by any of the 7 recoveries.

Every one of the 9 originally-confirmed extraction gaps is now either recovered (7) or
reclassified as a genuine, non-recoverable closure after closer inspection (2: 1894-95's
Feb13-18, 1890-91's Apr13-21, both matching the established Lenten/Holy-Week closure pattern).

## 2026-09-19 — resolved the last loose thread from issue #72: 1891-92_pair004's stray Alexandrinsky session

RG asked to address the stray session (date_text "1 Вторн." evening, Александринскій, "Василиса
Мелентьева"/"Фотографъ-любитель") left unresolved when issue #72 fixed this page's header.
Searched every other page in the 1891-92 season's raw JSON for either title -- both titles
individually recur elsewhere as genuine Alexandrinsky repertoire, but never paired together, and
no match was found anywhere in the season.

Went back to the actual render (`ForUpload_1891-92_Repertoire_001.jpg`) and found the real row:
"20 Пятница." (Sept 20, 1891) Александринскій = "Василиса Мелентьева, др./Дочь русскаго актера,
вод." -- the correct title, a DIFFERENT correct companion piece ("Дочь русскаго актера", not
"Фотографъ-любитель"), and a different date entirely. Confirmed `pair004` had no existing entry
at all for day 20 Alexandrinsky -- so this was a garbled version of a genuinely missing row, not
a duplicate. Julian weekday check: true 1891-09-20 = Пятница, matching exactly.

Fixed: relabeled to "20 Пятница.", corrected the second work title to "Дочь русскаго актера",
changed session from "evening" to "unspecified" (no real утро/веч split exists for this date).
Reran the full pipeline: row count unchanged (5761, a relabel not an addition), 0 new validation
errors, quality_checks.py unchanged at 5 flags, validate_performance_dates.py unchanged at 84.3%
verified / 11 unresolved. No regressions.

This closes the last open item from issue #72's investigation.

## 2026-09-19 — investigated and resolved all three pre-existing quality_checks.py flags (receipts_parse_failed, duplicate_event_key x2, zero_dark_cells_on_multiweek_page)

RG's instruction, quoting their own earlier survey: "Three pre-existing quality flags, never
investigated, predating today's work entirely: zero_dark_cells_on_multiweek_page on
1891-92_pair002, receipts_parse_failed on 1894-95_pair008, duplicate_event_key x2 on
1897-98_pair016/pair020" -- then "investigate."

**receipts_parse_failed (1894-95_pair008)**: one-line fix, `receipts_text` had lost its leading
`1599` (was `'р. 75 к.'`), scan-verified and restored to `'1599 р. 75 к.'`.

**duplicate_event_key (1897-98_pair016)**: scan-verified against `ForUpload_1897-98_Repertoire_007.jpg`.
A 3-day cascading mislabel, not a simple duplicate: day21's second Малый session -> "22 Четвергъ.",
the pre-existing "22 Четвергъ." entry (itself one day off) -> "23 Пятница.", and a spurious dark
placeholder already sitting at "23 Пятница." removed.

**duplicate_event_key x2 (1897-98_pair020)**: much larger than it looked. Both flagged collisions
were `human:kept_both` markers from an earlier dedup pass. Cross-checked every receipts figure
(effectively a unique fingerprint per session on a page) against `ForUpload_1897-98_Repertoire_009.jpg`
and found the corruption was a page-wide cascading date-label shift spanning BOTH the
Александринскій and Маріинскій columns, 1-12 Марта 1898 -- not just the 2 flagged rows. Fixed 12
Александринскій sessions + 8 Маріинскій sessions (relabels, 2 genuinely-missing sessions recovered,
2 pure duplicates deleted, 1 receipts figure cleared back to null to match what's actually printed).
Two of three "empty is_dark placeholder" entries deleted in a first pass turned out on closer scan
inspection to be genuine dark-day markers (real printed dashes) mislabeled with page-corner-stamp
bleed-through dates -- restored rather than left deleted; a third had no verifiable true date and
was left deleted. Noted but NOT chased: a similar corner-stamp-bleed artifact ~25 Февраля on this
same page, and the open question of whether this failure mode recurs on other two-page-spread pages.

**zero_dark_cells_on_multiweek_page (1891-92_pair002)**: the biggest of the four. Confirmed the
flag's own suspicion exactly -- Мариинскій/Александринскій/Михайловскій/Большой had been dropped
entirely from this page (16-30 Августа 1891, season opener) despite clear printed dashes on
`ForUpload_1891-92_Repertoire_000.jpg`; only Малый was captured, and even that had a systematic
2-row date shift plus several OCR title garbles. Rebuilt the full 16-30 Августа window from the
scan: fixed/relabeled 11 Малый sessions, added 41 dark-day markers across the other 4 theaters,
added 3 missing "30 Пятница." season-opening Гимнъ sessions (Мариинскій/Михайловскій/Большой).

```sql
-- verification after all four fixes, run against the rebuilt outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb
-- (via pipeline/quality_checks.py and pipeline/validate_performance_dates.py, not raw SQL)
```

Result: `event_entry` 5761 -> 5802 rows. `quality_checks.py`: **5 flags -> 0** -- every flag in
the corpus resolved. `validate_performance_dates.py`: verified 84.3% -> 84.4%, unresolved
unchanged at 11, no regressions. 0 new validation errors. Full detail: `docs/eval/known_issues.md`
issue #74.

## 2026-09-19 — promoted repertoire_spreadfix_v6 over outputs/full_run (the published production database)

RG asked to "promote this build over outputs/full_run" after issue #74 closed with quality_flags.csv
at 0. This is the first promotion of the two-page-spread Repertoire rework (issues #69-#74, ~2 months
of work) into the actual production deliverable already published to HF/Cloud Run.

Confirmed with RG first: backup drive has arrived (guardrail from cost-and-outputs-guardrails.md no
longer applies at full strength), and to skip re-running link_wikidata.py this round (external API,
unaffected by this change -- Repertoire pages never produce person_entry rows, so wikidata person
links are structurally untouched by any of this).

**Scope**: swapped the 97 old single-page-scheme `repertoire_<season>_p###.raw.json` files (1890-91
through 1897-98) for repertoire_spreadfix_v6's 97 new two-page-spread `pair###`/`p###`-scheme files,
combined manifest.csv accordingly (removed 97 old rows, added 97 new), left the 422 single-page-season
(1898-99+) Repertoire files and all 831 Musicians/Roster/TheaterSchoolStaff/Administration files
completely untouched.

**Verified safe before running anything**: traced build_entities.py's source queries -- entities.person/
person_candidate/person_link/person_merge_log are built exclusively from raw.person_entry, which
Repertoire pages never populate, so none of the Musicians/Roster entity-resolution work (2900 live
people, 23 already-reviewed candidate decisions, person_merge_log) was at risk. entities.work is a
full CREATE OR REPLACE every run regardless (deterministic from raw.event_entry_performance, no
manual state to lose). entities.person_wikidata_link belongs solely to link_wikidata.py, untouched by
build_entities.py.

**Safety backup made first** (outputs/full_run_pre_promote_backup_2026-09-19/): imperial_theaters.duckdb,
research_dataset.sqlite, manifest.csv, and the 97 old raw JSON files being replaced.

**Pipeline rerun, full corpus**: parse_and_validate.py (with --page-headers for date_undate backfill)
-> build_duckdb.py -> quality_checks.py -> validate_performance_dates.py -> build_entities.py ->
build_research_model.py -> build_datasette.py. link_wikidata.py deliberately skipped.

```sql
-- verification: person_entry (Musicians/Roster) byte-identical old vs new
-- select count(*) from raw.person_entry  -> 21168 both before and after
-- select count(*) from entities.person_wikidata_link -> 43 both before and after
-- select count(*) from entities.person_candidate where status != 'pending' -> 23, "already-reviewed
--   decisions preserved from a previous run" (build_entities.py's own log line)
```

Result: raw.event_entry for the 8 promoted seasons dropped 8941 -> 5802 rows (expected -- old data
was the pre-dedup baseline extraction; new data is the fully hand-verified result of this session's
whole Repertoire two-page-spread arc). quality_flags.csv: 0 flags for all 97 promoted pages (1059
flags remain, all pre-existing and unrelated -- Musicians/Roster checks + single-page-season
Repertoire, both untouched). validate_performance_dates.py for the promoted seasons: verified 84.4%,
matching repertoire_spreadfix_v6 exactly (4898/5802). Musicians/Roster entity counts (person_entry,
person_wikidata_link, 23 preserved candidate decisions) all byte-identical old vs new -- confirmed no
collateral effect on unrelated entity-resolution work. outputs/full_run/imperial_theaters.duckdb and
research_dataset.sqlite rebuilt in place. Full detail in docs/eval/known_issues.md's promotion note.

## 2026-09-22 — fixed pair020's remaining corner-stamp-bleed entries, and swept the whole corpus for the same failure mode

RG asked to fix the two things deferred when issue #74 closed: the '2 марта.'/'3 марта.' garbled
entries still on 1897-98_pair020 near 25 Февраля, and whether that failure mode recurs elsewhere.

Completed pair020: relabeled 2 garbled entries (Александринскій, Маріинскій) with corrected titles
via receipts-figure fingerprint against render_009, deleted 1 pure duplicate, recovered 7 new
Маріинскій sessions that had never been captured (14 Суббота - 24 Вторн. block), and found + fixed
a parallel Михайловскій instance of the exact same bug that was missed the first time ('2 Бродник.'
-> '3 Вторникъ.').

Wrote a corpus-wide sweep classifying every session's date_text second token as weekday/month/other;
43 candidates after tuning out false positives against page_header_dates.csv's start_day. Scan-checked
each:

```
-- detection script (not SQL): pipeline/parse_raw/*.raw.json date_text classification,
-- see docs/eval/known_issues.md's 2026-09-22 addendum for the full script logic and results
```

Result: 5 pages had real bugs (1890-91_pair014, 1893-94_pair016, 1894-95_pair010 [the big one --
nearly the whole Александринскій+Большой columns cascading-shifted], 1895-96_pair018,
1891-92_pair018), all scan-verified and fixed. 8 more candidates checked and confirmed legitimate
(page-boundary/month-transition labels or cosmetic Unicode marks), no fix needed.

Final verification: event_entry 5802 -> 5810, quality_flags.csv stayed at 0 throughout, verified
84.4% -> 84.9%, unresolved unchanged at 11, no regressions. outputs/full_run NOT re-promoted this
pass -- still reflects the 2026-09-19 promotion's data; that's a separate next step.

## 2026-09-22 — RG asked what the 84.9% "verified" figure actually means; re-ran the check fresh to answer accurately

```sql
select date_confidence, count(*) from analysis.event_entry_date_check group by 1 order by 2 desc
```

Result (outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb, the two-page-spread seasons only):
verified 4930 (84.9%), intra_block_disagreement 751 (12.9%), corrected 118 (2.0%), unresolved 11
(0.2%), total 5810. Explained to RG what each status means per pipeline/validate_performance_dates.py's
actual logic (weekday cross-check against date_undate, not a general correctness score).

## 2026-09-22 — broke down and fixed the 751 intra_block_disagreement rows

RG asked how to verify/fix the intra_block_disagreement bucket after the 84.9% explanation. Imported
validate_performance_dates.py's own _parse_dow() and re-classified all 751 events by re-parsing each
block's distinct date_text values directly, rather than trusting the note string alone.

```python
# classification: for each (page_id, note) group, parse every distinct date_text with _parse_dow()
# all_unparseable: every text fails to parse as a weekday -> legitimate month-name-only labels
# mixed: some parse, some don't -> same date, inconsistent format across theater columns (still correct)
# genuine_conflict: 2+ DIFFERENT real parsed weekdays -> actual signal something's mislabeled
```

Result: 519 events (69%) all-unparseable -- confirmed via sampling these are the established
"first row of a date range gets the full month name" convention, not errors. 201 events (27%) mixed
-- confirmed via sampling these are the SAME correct date recorded in two valid formats across
columns (e.g. "1 Декабря." vs "1 Суббота", both true), not factual errors. 31 events (4%) genuine
weekday-vs-weekday conflict, concentrated in exactly 3 pages/9 note-groups.

Scan-verified all 9 genuine-conflict blocks:
- repertoire_1891-92_pair016 (Feb 2-4, 1892): Александринскій ran 1 day behind Мариинский/
  Михайловский; titles were already correct (Ревизоръ, Лѣтнія грѣзы, Въ такую ночь!.. all matched
  the true date exactly), only date_text was wrong. Fixed via ForUpload_1891-92_Repertoire_007.jpg.
- repertoire_1891-92_pair020 (Mar 21-25, 1892): Большой ran 1 day behind Малый/Мариинский; all
  entries were pure is_dark placeholders (Большой genuinely dark this whole range per the scan), no
  real content at risk. Fixed via ForUpload_1891-92_Repertoire_009.jpg; 1 redundant duplicate dark
  marker deleted.
- repertoire_1895-96_pair002 (Aug 27, 1895): Большой's dark placeholder mislabeled "27 Четверг."
  instead of "27 Воскрес." (matching Малый, which already had the correct label and real content).
  Fixed via ForUpload_1895-96_Repertoire_000.jpg.

Verification: event_entry 5810 -> 5809 (net -1, one duplicate removed). quality_flags.csv stayed at
0. validate_performance_dates.py: verified 84.9% -> 85.4%, intra_block_disagreement 751 -> 720
(exactly -31, matching the 31 events fixed), unresolved unchanged at 11, no regressions.

## 2026-09-22 — investigated all 11 remaining "unresolved" date-check rows

RG asked to turn to the 11 unresolved rows next. Queried them directly (not from memory):

```sql
select dc.event_id, e.page_id, e.theater, e.date_text, e.date_undate, e.season, dc.note
from analysis.event_entry_date_check dc join raw.event_entry e on e.event_id = dc.event_id
where dc.date_confidence = 'unresolved' order by e.page_id, e.date_undate
```

Result: 3 blocks. (1) repertoire_1893-94_pair004, "13 Среда." (1893-09-13), all 5 theaters --
true Julian weekday is Понедѣльникъ (Monday). (2) repertoire_1894-95_pair008, "25 Суббота."
(1895-01-25), all 5 theaters -- true weekday is Среда (Wednesday). (3) repertoire_1895-96_pair002,
"26 Воскрес." (1895-08-26), Большой only, is_dark placeholder, no content.

Re-verified all 3 against source, not trusting old memory notes:
- (1) ForUpload_1893-94_Repertoire_001.jpg: all 5 theaters' titles/receipts match exactly; "13
  Среда." is genuinely printed that way. Confirmed real 1893-volume printing error, correctly
  verbatim.
- (2) ForUpload_1894-95_Repertoire_003.jpg: all 5 theaters' titles/receipts match exactly; "25
  Суббота." genuinely printed. Also noticed the printed sequence itself jumps oddly from "24
  Вторникъ" straight to "25 Суббота." -- an internal inconsistency in the source itself, not just
  this row. Confirmed real 1895-volume printing error, correctly verbatim.
- (3) ForUpload_1895-96_Repertoire_000.jpg: checked the full row sequence across all 5 theater
  columns -- day 26 has NO printed row at all anywhere on the page (24 Четвергъ -> 25 Пятница ->
  27 Воскрес, a genuine gap). The "26 Воскрес." Большой entry (empty, is_dark placeholder) has no
  corresponding source content whatsoever -- confirmed fabricated, not a mislabeled real row.
  Deleted, matching the established fabricated-session-drop precedent (repertoire_1890-91_p012).

Reran full pipeline: event_entry 5809 -> 5808 (the deleted fabrication). quality_flags.csv stayed
at 0. validate_performance_dates.py: verified unchanged 85.4%, unresolved 11 -> 10 (the two
genuine-printing-error blocks remain, correctly, since they're accurate transcriptions of a real
source inconsistency -- nothing left to "fix" there without falsifying the primary source).

## 2026-09-22 — re-promoted repertoire_spreadfix_v6 over outputs/full_run with today's date-accuracy fixes

RG: "the printers' errors can be addressed in the research layer later. go ahead and promote today's
fixes to outputs/full_run." Same procedure as the 2026-09-19 promotion (see that entry): manifest
page_id set was already identical (no manifest changes needed, today's fixes only edited content
within existing pages, never added/removed page_ids), so this run only needed to re-copy raw JSON
for the 9 pages actually touched today (plus the two verified-but-unmodified pages) -- done as a
full re-copy of all 97 files for simplicity/consistency with Friday's approach.

Safety backup made first (outputs/full_run_pre_promote_backup_2026-09-22/).

**Found and cleaned up unrelated debris while doing this**: every one of the 97 raw files from
Friday's promotion had an orphaned "<page_id>.raw 2.json" duplicate sitting in outputs/full_run/raw/
(93 total, plus a " 3.json" variant for one page) -- leftover artifacts from whatever `cp` operation
created the Friday promotion, never cleaned up. Confirmed each was a harmless orphan (malformed
filename means parse_and_validate.py's exact page_id.raw.json lookup can never read it) before
deleting all 93. Checked the rest of outputs/full_run/raw/ for the same " N.json" pattern -- none
found elsewhere, confirmed isolated to this one prior operation.

Reran full pipeline: parse_and_validate.py -> build_duckdb.py -> quality_checks.py ->
validate_performance_dates.py -> build_entities.py -> build_research_model.py -> build_datasette.py.
link_wikidata.py again not run (still unaffected, per the same reasoning as 2026-09-19).

```sql
-- verification: person_entry, entities.person_wikidata_link, and reviewed person_candidate count
-- all byte-identical between the pre-promote backup and the new build (21168 / 43 / 23)
```

Result: event_entry 20782 -> 20788 (+6, matching the net change in repertoire_spreadfix_v6 across
today's fixes exactly). quality_flags.csv: 0 for all 97 promoted pages (1059 total, unchanged --
same pre-existing/unrelated flags as before). validate_performance_dates.py for the promoted
seasons: verified 85.4%, unresolved 10, matching repertoire_spreadfix_v6 exactly. Musicians/Roster
entity resolution and Wikidata links confirmed byte-identical (second promotion, second
confirmation the isolation holds). outputs/full_run/imperial_theaters.duckdb and
research_dataset.sqlite rebuilt in place.

## 2026-09-22 — printed_page_number build-out, Phase 1, season 1 of 8 (1890-91)

RG asked to build out printed_page_number for every entry, to cite when writing about specific
database rows. Scan-verified all 13 renders for 1890-91 (11 two-page-spread + 2 single-leaf)
directly against ForUpload_1890-91_Repertoire_000.jpg through _012.jpg, cross-checking each
against the existing outputs/repertoire_spreadfix_v6/page_numbers/split_page_numbers_final.csv
extraction rather than trusting it blindly.

Found and fixed one real misread: p003's top-half page number was recorded as "1" (a truncated/
misread "10") -- confirmed against the scan directly, corrected to 10. Also found p003 and p004
are literally duplicate scans of the same two physical pages (10/11, "1-20 ноября") -- checked
the live database and confirmed this did NOT create duplicate event rows (only 4 expected
morning/evening-split duplicates in that range, out of 60 events), so no data bug, just a
redundant source scan.

**New finding, not previously documented**: two genuine content gaps, ~24 days total, that the
2026-08-24 missing-pages audit (issue #48) and the 2026-09-19 gap inventory (issue #73) both
missed -- repertoire_1890-91_pair004 (header range 27 Августа-21 Сентября per page_header_dates.csv,
scan-verified correct) has ZERO captured events before Sep10, even though the render
(ForUpload_1890-91_Repertoire_001.jpg) clearly shows real printed content for Aug27-Sep9 (page 4).
Same pattern for pair006 (header 22 Сентября-11 Октября) -- zero events before Oct2, though
render_002 shows real content for Sep22-Oct1 (page 6). Confirmed via direct DB query (0 rows in
both ranges, corpus-wide, not just under the expected page_id). Not recovered as part of this
task -- flagged for separate transcription work.

Built the render-level reference table (12 renders' verified top/bottom page numbers + cutover
dates), cross-matched against every 1890-91 event's actual date_undate: 601/601 events (100%)
resolved to exactly one page with clean, non-overlapping boundaries at every page_id transition
(including pages shared across two page_ids, e.g. page 15 spans pair014's tail and p015's
manually-recovered content). Saved to
outputs/repertoire_spreadfix_v6/printed_page_numbers/1890-91.csv.

Ran through pipeline/parse_and_validate.py --printed-page-numbers end-to-end: 601/601 events
backfilled correctly, 0 new quality_checks.py flags (including the new sequence-consistency
check), no regression to the existing 5808-row/0-flag baseline.

## 2026-09-22 — printed_page_number build-out, Phase 1 seasons 2-8 (1891-92 through 1897-98), completing Phase 1

Continued from 1890-91 per RG's go-ahead ("keep going through the rest of phase 1"). Same method
per season: scan-verify every render directly (including every single-leaf page), cross-check
split_page_numbers_final.csv's prior extraction rather than trust it, build a render-level
(start_date, end_date, page_number) table, cross-match every one of that season's raw.event_entry
rows against it via direct DuckDB query against outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb.

Query pattern used for every season (example, 1897-98):
```sql
SELECT event_id, date_undate FROM raw.event_entry WHERE season = '1897-98'
```
(cross-matched in Python against the render-level page_for() lookup, not as a single SQL query,
since the lookup logic is date-range containment across 13 renders per season)

Results per season: 1891-92 741/741 (100%, 2 misreads fixed: p008 bottom "61"->19, p009
top/bottom 21/21->20/21); 1892-93 644/646 matched + 2 deliberately unmatched (May31,1893 stray
events, unrecoverable citation) + p000 bottom genuinely illegible (not guessed) + new Dec17-26,1892
content gap found (zero events, corpus-wide query confirmed); 1893-94 1022/1022 (100%, clean, no
corrections); 1894-95 556/556 (100%, clean); 1895-96 801/801 (100%, 1 correction: p003 top blank->8);
1896-97 711/713 matched + 2 unassigned (pair010's 2Ноября1896 events duplicate pair008's own
same-date "Disparu!!!"/"Marthe" event -- confirmed via direct query, a pre-existing raw-data
duplicate/misfiling, not a printed_page_number bug); 1897-98 728/728 (100%, 2 corrections: p001
top garbled "1 4 1"->4, p010 bottom "123"->23).

**Bug found during final combined rebuild**: reference CSVs for 1895-96/1896-97/1897-98 were
initially keyed by render-sequential page_id (repertoire_1895-96_p002) instead of the manifest's
actual pairNNN id (repertoire_1895-96_pair006) that raw.event_entry.page_id uses for two-page-
spread seasons. Confirmed the correct convention against manifest.csv and 1891-92's
already-correct CSV: pairNNN's numeric suffix = printed page number of that render's top half.
First pipeline run under wrong ids silently left 2,139/5,808 events with blank printed_page_number
(parse_and_validate.py doesn't error on an unmatched page_id). Caught via fill-rate check, not
"did it run" -- rewrote all three CSVs, reran, fill rate recovered immediately.

Combined all 8 seasons' reference CSVs (outputs/repertoire_spreadfix_v6/printed_page_numbers/combined_phase1.csv,
186 rows) and ran the full pipeline end-to-end: parse_and_validate.py --page-headers
--printed-page-numbers -> quality_checks.py -> build_duckdb.py. Final result: 5804/5808 events
(99.93%) resolved to exactly one printed page across all 8 seasons; 4 residual rows are genuinely
unassignable (2 unmatched May31,1893 stray events + 2 duplicate 2Ноября1896 events), none guessed.
quality_checks.py: 0 flags (including the new printed_page_number_out_of_sequence check across the
whole corpus). No regression to the 5808-row baseline; 0 not_captured completeness gaps (all
previously-recovered content stayed recovered).

Phase 1 (all 8 two-page-spread seasons) is now complete. Phase 2 (10 single-page seasons,
1898-99-1907-08) not yet started.

## 2026-09-22 — printed_page_number build-out, Phase 2 (all 10 single-page seasons, 1898-99 through 1907-08)

Continued directly from Phase 1's completion, per RG's "continue straight into Phase 2." Followed the
approved plan's spot-check-then-formula approach: read first/middle/last render (by source_page_index)
per season directly off the scan, checked whether printed_page = source_page_index + constant_offset
holds across those 3 points before trusting it for the rest of that season.

Offsets found: 1898-99 through 1903-04 all +2; 1904-05 jumps to +90; 1905-06/1906-07 both +84;
1907-08 +76 (matches docs/eval/gold/source_pages.csv's known +76 for this season). Every season's 3
checkpoints agreed, so all 10 resolved at the plan's best-case cost (30 reads, no season needed the
render-by-render fallback). Extra 4th check on 1904-05 p010 (page 100 predicted, page 100 confirmed)
ruled out the +90 jump being a checkpoint-local misread.

Built outputs/repertoire_singlepage_pagenumbers/{season}.csv (one row per page_id, single-page-season
shape) plus combined_phase2.csv (422 rows, all 10 seasons). Verification query pattern:

```sql
SELECT event_id, printed_page_number FROM event_entry WHERE season IN (10 single-page seasons)
```
(checked programmatically in Python against the parsed CSV output, not a live duckdb query this time --
this run never touched outputs/full_run/imperial_theaters.duckdb, only its read-only manifest/raw dirs)

Ran pipeline/parse_and_validate.py --printed-page-numbers against outputs/full_run/manifest.csv +
outputs/full_run/raw (read-only), writing all output to a new scratch dir
(outputs/repertoire_singlepage_pagenumbers/parsed_test/) rather than outputs/full_run itself. Result:
14,980/14,980 single-page-season events (100%) filled; the 8 already-completed spread-season events
(5,808) correctly stayed empty (no cross-season leakage). quality_checks.py: 1,059 flags, verified
byte-identical (diffed page_id/table/row_id/flag) to outputs/full_run/quality_flags.csv's existing
baseline -- 0 regression, 0 new printed_page_number_out_of_sequence flags across all 422 pages.

Phase 2 complete. Both phases of the printed_page_number plan are now done: 5,804/5,808 (99.93%)
two-page-spread events + 14,980/14,980 (100%) single-page events. Phase 3 (promoting into
outputs/full_run) remains a separate, later decision, not done here.

## 2026-09-22 — printed_page_number fold-boundary confidence check (prompted by RG's question)

RG asked whether we're confident about an entry's page number at a page fold. Ran a systematic
overlap check across all 91 two-page-spread fold boundaries (187 reference rows in
outputs/repertoire_spreadfix_v6/printed_page_numbers/*.csv):

```python
# for each page_id with 2 reference rows, check if end_date of the earlier range >= start_date
# of the later range (an overlap, meaning the same date is claimed by both halves)
```

Result: exactly 1 overlap found, repertoire_1897-98_pair018 (top ending 1898-02-07, bottom also
starting 1898-02-07).

```sql
SELECT event_id, date_undate, printed_page_number FROM raw.event_entry
WHERE page_id = 'repertoire_1897-98_pair018' AND date_undate = '1898-02-07'
```
Result: 5 real events (pair018__s046 through __s050), all showing page 18.

Re-examined ForUpload_1897-98_Repertoire_008.jpg directly (cropped for a close look at the fold
region): confirmed the true fold falls between 6 Февраля (last row on top, page 18) and 7 Февраля
(first row on bottom, page 19, Михайловскій only). Fixed 1897-98.csv (top range end_date
1898-02-07 -> 1898-02-06), rebuilt combined_phase1.csv, reran parse_and_validate.py ->
quality_checks.py -> build_duckdb.py: 5,808/5,808 events unchanged, 0 quality flags, the 5
corrected events verified to now read page 19.

Also ran a non-adjacency check (any fold boundary where the two ranges aren't exactly 1 day
apart, which would catch an off-by-one-in-the-other-direction misreading that wouldn't produce a
literal overlap): found 7 gaps, all either small (2-4 day) plausible season-opening dark-day gaps
or the already-documented 11-day 1892-93_pair014 gap (Dec17-26,1892, known_issues.md #75's first
addendum) -- nothing newly concerning.

Documented the honest limit of this check in known_issues.md: it catches boundary dates that
disturb the date-range arithmetic, not a misreading that still happens to produce a tidy
one-day-apart split. Full re-verification of all 91 folds against the scan was not done.

## 2026-09-22 — full manual re-verification of all 91 two-page-spread fold boundaries

RG asked for a full re-verification pass on all 91 folds after the earlier automated-check-only
pass found and fixed one bug (1897-98_pair018). Read every one of the 91 fold-bearing renders
directly (all 8 seasons, season by season: 1890-91 11 renders, 1891-92 12, 1892-93 12, 1893-94 12,
1894-95 8, 1895-96 12, 1896-97 12, 1897-98 12), confirming the last date on top and first date on
bottom against printed_page_numbers/{season}.csv by eye.

Result: 91/91 checked, only the one already-fixed bug found -- no new fold-boundary errors.
Re-confirmed the fix itself sits at the true fold:

```sql
SELECT event_id, date_undate, printed_page_number FROM raw.event_entry
WHERE page_id = 'repertoire_1897-98_pair018' AND date_undate = '1898-02-07'
```
Result: all 5 rows correctly read page 19 (post-fix).

Byproduct of reading every render in full (not just fold-adjacent rows): found the 1892-93
"Dec17-26,1892" gap documented in issue #75's first addendum was a significant undercount --
reading _Repertoire_005.jpg through _007.jpg in full showed real content continuing well past
Dec16. Queried to confirm:

```sql
SELECT event_id, page_id, date_undate, printed_page_number FROM raw.event_entry
WHERE season = '1892-93' AND date_undate BETWEEN '1892-12-17' AND '1893-02-06'
ORDER BY date_undate, event_id
```
Result: 42 rows, all dated Dec27-31,1892 (page14) -- zero events Jan1-Feb5,1893. True gap is
Dec31,1892-Feb5,1893 (~37 days), not ~10 days as originally reported.

Also found two further undocumented gaps in 1890-91 (Feb8-13 and Feb27-Mar3,1891), confirmed via
direct query each showed zero events despite real printed content on the scan; and confirmed the
already-catalogued Jan19-24,1891 gap (issue #73) was never actually recovered despite that issue's
"recovered all 7 remaining" framing.

Final state: 5804/5808 events (99.93%) filled, unchanged from before this pass -- this
re-verification found and fixed 0 new fold-boundary bugs (the corpus was already correct after
the earlier fix), only corrected the documented SIZE of one already-known content gap.

## 2026-09-22 — content gap recovery, 1890-91 (all 5 gaps in this season)

RG asked to tackle the content gaps found during the fold-reverification pass. Recovered all 5
gaps in 1890-91 by reading each render directly and manually transcribing every theater's cell
(including explicit dark-cell rows) into the existing page_id's raw JSON.

Verification query used repeatedly during this work (check whether a new session's date actually
resolved to a page number):
```sql
SELECT season, page_id, date_undate, count(*) FROM raw.event_entry
WHERE printed_page_number='' OR printed_page_number IS NULL
GROUP BY season, page_id, date_undate ORDER BY season, date_undate
```
First run after adding pair020's Feb27-Mar3 recovery surfaced a real bug: 19 events under
pair020 with date_undate 1891-03-02/03 had empty printed_page_number, tracing to
page_header_dates.csv's stale header entry ("14 февраля...26 февраля") causing the
month-backfill threshold logic to resolve "2 Суббота"/"3 Воскресенье" as February instead of
March. Fixed by extending pair020's and pair016's header entries to their true recovered end
dates (3 марта and 24 января respectively); reran and confirmed 0 empty rows remained for
1890-91.

Weekday sanity check on the fix:
```sql
SELECT dc.date_confidence, count(*) FROM analysis.event_entry_date_check dc
JOIN analysis.event_entry ae ON ae.event_id=dc.event_id
WHERE ae.date_undate IN ('1891-03-02','1891-03-03')
GROUP BY dc.date_confidence
```
Result: all 19 events verified (weekday matches calendar) after the fix.

Final state: event_entry 5808 -> 6015 (+207, exactly the transcribed session count),
quality_checks.py 0 flags, 1890-91 printed_page_number now 808/808 (100%, up from 601/601).
validate_performance_dates.py: 10 pre-existing unresolved rows unchanged (both in seasons
untouched by this pass, already documented), 0 new disagreements among the 207 new sessions.

1892-93's larger gaps (Dec31,1892-Feb5,1893 ~37 days; Feb24-Mar12,1893 ~17 days; partial
Mar4-12,1893) not yet started.

## 2026-09-22 — content gap recovery, 1892-93's large Dec31-Feb5 gap (233 sessions)

Continued gap recovery into 1892-93's biggest gap. Transcribed page13's tail (17-26 Дек, into
existing pair014), page14's tail (1-6 Янв, into pair014) and all of page15 (7-16 Янв, into
pair014), plus a brand-new page_id pair016 covering pages 16 and 17 in full (17 Янв - 5 Февр).
This season prints real receipts, transcribed alongside every title; a few cells sit on the
scan's binding crease and were left with annotation="receipts illegible" rather than guessed.

First pipeline run surfaced a structural bug: extending pair014 across the Dec/Jan boundary hit
day-number collisions the header-based month-threshold backfill can't resolve (day 4 and day 11
both occur in December's existing content and January's new content). Fixed by setting
month_text/year_text explicitly on every new session (confirmed via code read that
_backfill_month_year honors an explicit month/year over its own header guess). Verification
query used to confirm the fix:
```sql
SELECT event_id, date_undate, printed_page_number FROM raw.event_entry
WHERE page_id='repertoire_1892-93_pair014' AND date_undate IN ('1892-12-04','1893-01-04')
```
Result: both resolved to their own correct page (12 and 14 respectively), no collision.

quality_checks.py surfaced 12 duplicate_event_key flags -- investigated and confirmed harmless:
pre-existing December sessions on the same page_id have an OCR-mismatched weekday label already
auto-corrected by validate_performance_dates.py (status 'corrected'), coincidentally colliding
in raw date_text with my accurately-transcribed ('verified') January sessions. Confirmed via:
```sql
SELECT dc.event_id, ae.date_undate, dc.date_confidence FROM analysis.event_entry_date_check dc
JOIN analysis.event_entry ae ON ae.event_id=dc.event_id
WHERE dc.event_id IN ('repertoire_1892-93_pair014__s060','repertoire_1892-93_pair014__s182', ...)
```

Final state: event_entry 6015 -> 6248 (+233), quality_checks.py 12 flags (all the one confirmed
coincidence above), printed_page_number 1892-93 now 879/879 filled except the 4 already-known
unassignable rows. validate_performance_dates.py: all 233 new sessions verified (weekday matches
calendar), 0 new unresolved rows.

Remaining in 1892-93: Feb24-Mar12,1893 (~17 days) and a partial Mar4-12,1893 window, not yet
started.

## 2026-09-22 — content gap recovery, 1892-93's final two gaps (Feb24-Mar12,1893, 80 sessions)

Completed 1892-93's remaining gaps: page19 tail (24 Feb-3 Mar, into existing pair018) and all of
page20 (4-12 Mar, into existing pair020). Both fall in Great Lent 1893 -- confirmed the recurring
pattern (Маріинскій/Малый dark, only the German/French guest troupes at Александринскій/
Михайловскій, plus 2 Большой symphonic concerts). Checked the existing pair020 raw JSON before
transcribing to confirm 13 Марта onward was already captured (avoided duplicating).

Final verification:
```sql
SELECT dc.date_confidence, count(*) FROM analysis.event_entry_date_check dc
JOIN analysis.event_entry ae ON ae.event_id=dc.event_id
WHERE (ae.page_id='repertoire_1892-93_pair018' AND ae.date_undate BETWEEN '1893-02-24' AND '1893-03-03')
   OR (ae.page_id='repertoire_1892-93_pair020' AND ae.date_undate BETWEEN '1893-03-04' AND '1893-03-12')
GROUP BY dc.date_confidence
```
Result: all 80 verified.

Ran a final full-corpus gap scan (all 8 two-page-spread seasons' printed_page_numbers CSVs) to
confirm completeness -- every gap this session's fold-reverification pass found is now closed;
remaining gaps in the scan are exactly issue #73's pre-existing, already-triaged inventory.

Whole content-gap-recovery effort, final tally: event_entry 5808 -> 6328 (+520 sessions across
8 renders, 2 seasons), 0 new quality-check categories beyond the one confirmed-harmless
coincidence, 0 new weekday-validation problems, 3 real pipeline bugs found and fixed (two
month-threshold collisions, one combined_phase1.csv staleness trap -- must rebuild that
generated file after every edit to its 8 source CSVs).

## 2026-09-22 — promoted printed_page_number build-out (Phases 1+2, all gap recoveries) to outputs/full_run

RG asked to promote. Backed up first (full_run_pre_promote_backup_2026-09-22_printedpage/).
Copied all 98 repertoire_spreadfix_v6 raw JSON files into full_run/raw/, added the one new
pair016 manifest row (confirmed via direct manifest diff this was the only difference), built a
combined 614-row printed_page_numbers_all.csv (Phase 1 + Phase 2), reran the full pipeline chain.

Verification queries:
```sql
-- two-page-spread seasons date-check breakdown, compared against repertoire_spreadfix_v6's own numbers
SELECT dc.date_confidence, count(*) FROM analysis.event_entry_date_check dc
JOIN analysis.event_entry ae ON ae.event_id = dc.event_id
WHERE ae.season IN ('1890-91','1891-92','1892-93','1893-94','1894-95','1895-96','1896-97','1897-98')
GROUP BY dc.date_confidence
```
Result: verified 5480, corrected 118, intra_block_disagreement 720, unresolved 10 -- exact match.

```sql
SELECT season, count(*) FROM analysis.event_entry WHERE event_status = 'not_captured' GROUP BY season ORDER BY season
```
Result: spread across all 18 seasons (not concentrated in touched seasons) -- confirmed pre-existing
analysis-layer completeness-gap synthesis, not a regression.

raw.person_entry (21168 rows) and entities.person_wikidata_link (43 rows) confirmed byte-identical
against the backup via direct row comparison in Python/duckdb.

Final state: event_entry 20788 -> 21308 (+520), quality_flags.csv 1059 -> 1071 (+12, the
already-investigated duplicate_event_key coincidence, same 12 event_ids), Musicians/Roster
isolation confirmed byte-identical. outputs/full_run/imperial_theaters.duckdb and
research_dataset.sqlite rebuilt in place. Not done: link_wikidata.py, HF/Cloud Run republish.

Noted for follow-up (RG's next request): the single-page seasons show 9729 event_entry_date_check
rows with date_confidence='no_date' -- pre-existing, untouched by this session, next to investigate.

## 2026-09-22 — investigated and fixed single-page-season date_undate gap (issue #76)

RG asked to look at empty date_undate entries right after the printed_page_number promotion.

```sql
SELECT season, count(*) FROM raw.event_entry
WHERE date_undate IS NULL OR date_undate = ''
GROUP BY season ORDER BY count(*) DESC
```
Result: 9737/21308 (45.7%) empty, concentrated in 8 single-page seasons (1899-00 through 1907-08
except 1906-07); 1898-99 had 0, 1906-07 had 12.

Traced root cause: outputs/gate3_columnwise/page_header_dates.csv (332 rows, all status=ok)
already had the header data needed for _backfill_month_year, just never passed via
--page-headers for these seasons. Tested combining it with repertoire_spreadfix_v6's own header
file in a scratch parse_and_validate.py run: no_date dropped to 15, then found a second bug (a
trailing comma in some sessions' own month_text breaking pipeline/schemas/dates.py's _DATE_RE)
affecting the remaining 12 (all in 1906-07). Fixed the regex (widened \.? to [.,]?), verified:

```python
parse_russian_date('1 января, 1906—1907 гг.')  # now '1907-01-01', was None
parse_russian_date('1 мая 1882 г.')  # unchanged, '1882-05-01'
```

Reran: no_date collapsed to 3 (confirmed non-events -- "Мартъ." month-divider rows with no day
number and 0 attached performances). Weekday-verified rate 50.3% -> 95.3% corpus-wide.
quality_checks.py unchanged (1071 flags, 0 new).

Promoted to outputs/full_run (backup: full_run_pre_promote_backup_2026-09-22_dateundate/).
Verified: raw.event_entry row count unchanged (21308), raw.person_entry and
entities.person_wikidata_link byte-identical, entities.person still 2900 live/23 preserved
candidates. research.event 28096 -> 26618 (fewer not_captured synthetic rows now that real dates
are known). Combined header file saved permanently at
outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv for reuse.

## 2026-09-22 — single-page-season quality-flag backlog, part 1: fabricated/misplaced performance data (issue #77)

Started triaging the 172-row single-page-season quality-flag backlog RG asked about. Investigating
the 20 receipts_parse_failed rows found a much larger pattern. Corpus-wide query:
```sql
SELECT ee.page_id, ee.theater, count(*) FROM raw.event_entry ee
LEFT JOIN raw.event_entry_performance eep ON eep.event_id = ee.event_id
WHERE ee.season IN (10 single-page seasons)
  AND ee.event_status = 'performed' AND eep.event_id IS NULL
  AND (ee.receipts_text IS NOT NULL AND ee.receipts_text != '')
GROUP BY ee.page_id, ee.theater ORDER BY count(*) DESC
```
Result: 254 rows, 64 page/theater combinations. Traced to two causes: (1) rare fabricated tiny
receipts for genuinely dark cells (12 rows, one page), (2) the overwhelming majority: real
performances with the title sitting in annotation instead of works. Discovered outputs/full_run/raw/
was stale relative to outputs/gate3_columnwise/raw_columnwise/ (65 of 332 pages differed) --
re-syncing alone dropped the count from 254 to 139.

Built an annotation-to-works parser with a safety check (lines with >1 comma held back from
auto-fix). Manually scan-verified every ambiguous case individually (~40), catching two more
cascading date-mislabeling bugs (1900-01_p027, 1904-05_p032) along the way, verified via receipts-
figure matching:
```sql
-- pattern used repeatedly: match a session by its unique receipts_text rather than trusting
-- its own date_text label, since the labels themselves were sometimes wrong
```

Caught and corrected a serious process error before promoting: had copied a freshly-built scratch
.duckdb (with no entities history) directly over the live outputs/full_run/imperial_theaters.duckdb,
causing build_entities.py to lose all tombstone/merge history (2900 live people -> 4063, 23 preserved
candidates -> 853). Caught from the build_entities.py log output itself, restored from the
pre-promotion backup, redid the rebuild in place on the real file instead of copying in a scratch
copy, reverified entities.person/person_candidate matched the established baseline exactly.

Final verification: 254-row query -> 0 remaining. event_entry unchanged (21321), event_entry_performance
22424 -> 22809 (+385). quality_checks.py 1071 -> 986. validate_performance_dates.py verified 95.3% ->
95.6%, invalid_date 4 -> 1. raw.person_entry and entities.person_wikidata_link byte-identical against
backup; entities.person/person_candidate match baseline exactly (2900 live, 23 preserved). Promoted to
outputs/full_run.

Remaining from the original 172-row ask: duplicate_event_key (57), zero_dark_cells_on_multiweek_page
(16), receipts_parse_failed (14) -- not yet triaged, a distinct continuation.

## 2026-09-22 — receipts_parse_failed backlog (14 rows): investigation and resolution

```sql
select se.page_id, se.event_id, se.date_text, se.theater, se.receipts_text
from raw.event_entry se
where se.event_id in (
    select event_id from raw.event_entry
    where page_id like '%1901-02_p012%' or page_id like '%1905-06_p004%' or page_id like '%1905-06_p010%'
)
```

Result: pulled full session lists for the 3 pages whose exact receipts_text values hadn't been
captured yet (the other 11 flagged rows' pages were already known from quality_checks.py's detail
strings). Found the two genuinely-blank cases (`1905-06_p004__s034` = 'р. — к.', `1905-06_p010__s007`
= 'р. к.') and confirmed `1901-02_p012__s030` still showed receipts_text='—'.

```sql
select count(*) from raw.event_entry;         -- 21321, unchanged (pre-rebuild live DB)
select count(*) from raw.event_entry_performance;  -- 22809 (pre-rebuild)
```

Result: baseline row counts confirmed before starting fixes, to detect any accidental row
add/drop from the upcoming edits.

After all 14 rows resolved (10 fixed as genuine OCR/field-scrambling bugs, 4 scan-verified as
correct-as-is and excluded from the check going forward — see known_issues.md addendum), rebuilt
raw/analysis/entities/research in place:

```sql
select count(*) from raw.event_entry;               -- 21321 (unchanged)
select count(*) from raw.event_entry_performance;    -- 22810 (+1, the 1906-07_p035 fix)
select count(*) from raw.person_entry;               -- 21168 (byte-identical, Musicians/Roster untouched)
select count(*) from entities.person_wikidata_link;  -- 43 (byte-identical)
```

Result: all baselines held. `build_entities.py` log confirmed 2900 live people / 1459 tombstoned
carried forward unchanged, 23 preserved candidate decisions. `validate_performance_dates.py`: 95.6%
verified, unchanged. `quality_checks.py`: receipts_parse_failed 14 -> 0, total flags 986 -> 972.
Promoted to outputs/full_run (backup: outputs/full_run_pre_promote_backup_2026-09-22_receiptsfix/).

Remaining from the original 172-row ask: duplicate_event_key (69, includes the 12 already-confirmed-
harmless from earlier this session), zero_dark_cells_on_multiweek_page (16) -- next up.

## 2026-09-22 — zero_dark_cells_on_multiweek_page backlog (16 rows): investigation and resolution

```sql
select distinct page_id, count(*) as sessions, sum(case when event_status='no_performance' then 1 else 0 end) as dark
from raw.event_entry group by page_id having page_id in (
  'repertoire_1898-99_p000','repertoire_1899-00_p000','repertoire_1899-00_p001','repertoire_1899-00_p018',
  'repertoire_1901-02_p020','repertoire_1901-02_p021','repertoire_1901-02_p026',
  'repertoire_1900-01_p000','repertoire_1900-01_p001','repertoire_1900-01_p008',
  'repertoire_1902-03_p001','repertoire_1902-03_p016','repertoire_1903-04_p001','repertoire_1903-04_p003',
  'repertoire_1906-07_p022','repertoire_1907-08_p032'
)
```

Result: confirmed the 16 flagged pages' session counts and zero dark-day counts, cross-checked against
quality_flags.csv detail strings.

Structural cross-check (theater cardinality, to rule out a silently-dropped theater column as an
alternative explanation for the zero-dark-day pattern):

```python
# for each of the 16 raw JSON files: len({s['theater'].strip() for s in sessions})
```

Result: all 16 pages show exactly 3 distinct theaters, consistent with full column coverage (no
evidence of a dropped theater column).

Rendered all 8 seasons' source PDFs (render_pages.py, free/local, no paid API calls) and individually
scan-verified all 16 pages against their page images -- every one confirmed genuinely zero dark days,
matching the raw JSON exactly (including receipts figures). See known_issues.md addendum for the full
page list and narrative.

```sql
-- after refining quality_checks.py's check_repertoire to scope the flag to "pair" (two-page-spread) page_ids:
```

Result: quality_checks.py rerun -- zero_dark_cells_on_multiweek_page 16 -> 0, total flags 972 -> 956.
No data changed (detection-precision fix only); no pipeline rebuild needed.

Remaining from the original 172-row ask: duplicate_event_key (69, includes 12 already-confirmed-
harmless from earlier this session) -- last category, next up.

## 2026-09-22 — duplicate_event_key backlog (69 rows): investigation and resolution

```sql
select page_id, count(*) from (
  select distinct row_id, page_id, detail from raw.event_entry  -- via quality_flags.csv, not a live SQL source
) group by page_id
```

Result: (queried via quality_flags.csv grep, not SQL) confirmed the 69 rows spanned 21 distinct pages,
heavily concentrated in 1898-99 (13 pages).

```sql
select event_id, date_text, theater, time_of_day, receipts_text
from raw.event_entry where page_id = 'repertoire_1892-93_pair014' order by event_id
```

Result: found the page had grown to 244 sessions; cross-referenced against 4 backup copies to find a
121-session pre-duplication baseline, then diffed to isolate the genuine 244-session file's first-162
vs. duplicated-tail structure.

```python
# per-page raw JSON dumps (uv run python, not SQL) for all 20 remaining flagged pages after pair014,
# grouping sessions by (date_text, theater, session) to find every colliding group's exact content
```

Result: classified all 57 remaining rows into the pipeline-bug shape (1900-01_p009/1903-04_p008/
1904-05_p021, 5 rows), the УТРО/ВЕЧ session-missing shape (43 rows, 14 pages), and the content-bleed
shape (1904-05_p032, 6 rows) -- see known_issues.md addendum for full detail.

```sql
select count(*) from raw.event_entry;               -- 21235 (final, post-fix)
select count(*) from raw.event_entry_performance;    -- 22677 (final, post-fix)
select count(*) from raw.person_entry;               -- 21168 (byte-identical)
select count(*) from entities.person_wikidata_link;  -- 43 (byte-identical)
```

Result: `quality_checks.py`: duplicate_event_key 57 -> 0, total flags 944 -> 887 (887 is entirely
pre-existing out-of-scope categories). `build_entities.py` baseline confirmed exactly (2900 live/1459
tombstoned/23 preserved). `validate_performance_dates.py` unchanged at 95.6%. Promoted to outputs/full_run
(backup: outputs/full_run_pre_promote_backup_2026-09-22_dupeventkey/).

**This closes the entire original 172-row single-page-season quality-flag backlog.**

## 2026-09-22 — confidence check on morning/evening (УТРО/ВЕЧЕРЪ) session labeling

```sql
select time_of_day, count(*) from raw.event_entry group by 1 order by 2 desc
```
Result: unspecified 18120, evening 1569, morning 1546.

```sql
select count(*) from (
    select page_id, date_text, theater, count(*) as n
    from raw.event_entry group by 1,2,3 having count(*) > 1
)
```
Result: 1537 (page_id, date_text, theater) groups have more than one printed session -- these are the
only rows where morning/evening actually matters.

```sql
select count(*) from (
    select page_id, date_text, theater, count(*) as n,
           sum(case when time_of_day='unspecified' then 1 else 0 end) as n_unspec
    from raw.event_entry group by 1,2,3 having count(*) > 1
) t where n = n_unspec
```
Result: 0 -- confirms this session's duplicate_event_key fixes left no group with BOTH sessions still
unlabeled.

```sql
select n, count(*) from (
    select page_id, date_text, theater, count(*) as n
    from raw.event_entry group by 1,2,3 having count(*) > 1
) group by 1 order by 1
```
Result: 1531 groups of size 2 (clean morning/evening pairs), 6 groups of size 3.

```sql
select count(*) from (
    select page_id, date_text, theater, count(*) as n,
           sum(case when time_of_day='unspecified' then 1 else 0 end) as n_unspec
    from raw.event_entry group by 1,2,3 having count(*) > 1
) t where n_unspec > 0 and n_unspec < n
```
Result: 14 two-row groups have exactly one row still labeled 'unspecified' instead of morning/evening
(the other row IS labeled) -- session distinction incomplete for these, not investigated this session.

Direct row dump of all 6 three-row groups (page_id/date_text/theater, event_id/time_of_day/
receipts_text): 4 of the 6 (repertoire_1893-94_pair006 x2, repertoire_1895-96_pair018,
repertoire_1895-96_pair004) show evening+morning+a THIRD 'unspecified' row whose receipts_text nearly
exactly duplicates the evening row's (e.g. '2946 р. 20 к.' vs '2946 р. 20', '617 р. 29 к.' vs
'617 р. 29') -- the same duplication signature found and fixed this session on
repertoire_1892-93_pair014 and repertoire_1904-05_p032, but NOT caught by quality_checks.py's
duplicate_event_key check because the extra row's session value ('unspecified') doesn't collide with
either real label. repertoire_1897-98_pair010's triple group does not fit this pattern (morning has no
receipts, unspecified has an unrelated, much larger figure). repertoire_1891-92_pair008's triple group
has no receipts on any of the 3 rows, so duplication can't be confirmed/ruled out by this same method.
None of these 6 investigated further or fixed this session -- flagged as a genuine, unresolved,
previously-uncaught bug class, distinct from and not covered by this session's duplicate_event_key
backlog work (which was scoped to single-page seasons only; all 6 of these are two-page-spread pages).

## 2026-09-22 — morning/evening triples + unspecified-pair fixes: verification

```sql
select count(*) from (
    select page_id, date_text, theater, count(*) as n from event_entry group by 1,2,3 having count(*) > 2
)
```
Result: 0 (all 6 three-row groups resolved -- 4 confirmed duplicates dropped, 2 individually
scan-verified and corrected).

```sql
select count(*) from (
    select page_id, date_text, theater, count(*) as n,
           sum(case when time_of_day='unspecified' then 1 else 0 end) as n_unspec
    from event_entry group by 1,2,3 having count(*) > 1
) t where n_unspec > 0 and n_unspec < n
```
Result: 0 (all 8 partial-unspecified pairs resolved -- complementary morning/evening label assigned
to each, after confirming distinct content on both sides).

```sql
select count(*) from raw.event_entry;               -- 21226 (final)
select count(*) from raw.event_entry_performance;    -- 22659 (final)
select count(*) from raw.person_entry;               -- 21168 (byte-identical)
select count(*) from entities.person_wikidata_link;  -- 43 (byte-identical)
```
Result: build_entities.py baseline confirmed exactly (2900 live/1459 tombstoned/23 preserved).
validate_performance_dates.py unchanged at 95.6%. Promoted to outputs/full_run (backup:
outputs/full_run_pre_promote_backup_2026-09-22_utrovecher/).

## 2026-09-22 — session-completeness detection, Tier 0 (docs/session_completeness_detection.md)

```sql
with anno as (
    select distinct page_id, date_text, theater
    from raw.event_entry
    where annotation ilike '%воспитанник%'
),
counts as (
    select e.page_id, e.date_text, e.theater, count(*) as n
    from raw.event_entry e
    join anno a using (page_id, date_text, theater)
    group by 1,2,3
)
select n, count(*) from counts group by 1 order by 1
```
Result: 39 groups with n=1 (only one session despite carrying a "Безплатные спектакли для
воспитанниковъ" free-matinee annotation), 39 with n=2 (already correct). The n=1 39-row list:

```
repertoire_1898-99_p013__s001/s002/s003 (14 Суббота., Большой/Малый/Новый)
repertoire_1898-99_p017__s001/s002/s003 (6 Воскрес., Большой/Малый/Новый)
repertoire_1898-99_p028__s025/s026 (24 Среда., Александринскій/Михайловскій)
repertoire_1898-99_p028__s029/s030 (25 Четвергъ., Александринскій/Михайловскій)
repertoire_1898-99_p028__s033/s034 (26 Пятница., Александринскій/Михайловскій)
repertoire_1898-99_p038__s025 (6 Четвергъ, Александринскій)
repertoire_1898-99_p039__s026 (6 Четвергъ, Малый)
repertoire_1899-00_p028__s001/s002/.../s034 (16 Среда. - 3 Пятница., Александринскій/
  Михайловскій/Маріинскій -- 15 rows, this page alone)
repertoire_1900-01_p012__s028 (14 Вторн., Михайловскій)
repertoire_1900-01_p022__s003 (14 Воскрес., Александринскій)
repertoire_1901-02_p016__s028 (6 Четвергъ., Михайловскій)
repertoire_1902-03_p011__s036 (14 Четвергъ, Новый)
repertoire_1903-04_p017__s025 (6 Суббота., Большой)
```
Full per-row detail (event_id/receipts/annotation) captured in session transcript, not re-pasted
here -- re-run the query above for a fresh authoritative list before acting on it.

```sql
with per_group as (
    select page_id, date_text, theater_canonical, date_undate, count(*) as n
    from analysis.event_entry
    where date_undate is not null and date_undate != ''
    group by 1,2,3,4
)
select theater_canonical, dayname(try_cast(date_undate as date)) as wd,
       count(*) as n_groups,
       sum(case when n>1 then 1 else 0 end) as n_split,
       round(100.0*sum(case when n>1 then 1 else 0 end)/count(*), 1) as split_pct
from per_group
where try_cast(date_undate as date) is not null
group by 1,2 order by 1, split_pct desc
```
Result: Monday is the real high-split weekday for every theater (16-33%), all other weekdays
1-9%. Too weak alone to flag anything but usable as a secondary ranking signal. Full per-theater/
weekday table in session transcript.

Neither query mutated any data. Full scoping (Tiers 0-3, caveats, status) in
docs/session_completeness_detection.md.

## 2026-09-22 — Tier 1 CV validation (row_detect.py on single-page format): abandoned

Ran `row_detect.py`'s `analyze_page`/`debug_visualize` against the rendered image for
`repertoire_1898-99_p029` (scan-verified ground truth already established earlier this session:
compound rows 21 Воскрес./24 Среда./25 Четвергъ./26 Пятница., single rows 17-23, dark 20 Суббота.).
Not a SQL query -- a direct test of the proposed Tier 1 detector against known-correct answers.

Result: hypothesis ("compound rows are taller") did not hold as designed. Synchronized splits (all
3 theaters split together, e.g. 21 Воскрес.) produced two normal-height rows via the internal divider
being picked up as a real full-width boundary, not one tall row. Partial splits (one theater splits,
others don't -- the common case, e.g. 24 Среда.) produced an anomalously SHORT fragment (111px vs
~180px baseline), not a tall one. Boundary tracking failed entirely further down the page (one
"row" spanned 565px, swallowing 25 Четвергъ's evening half, all of 26 Пятница, and the page margin).
Full detail in docs/session_completeness_detection.md's Tier 1 section. RG's decision: abandon the
CV approach, extend Tier 0 (SQL/text heuristics) instead.

```sql
select time_of_day, count(*) from raw.event_entry
where annotation ilike '%утро%' or annotation ilike '%веч%' group by 1 order by 2 desc
```
Result: (unspecified, 12), (evening, 8), (morning, 8). Checked the 12 unspecified rows individually --
all false positives, ordinary benefit-event titles using "утро"/"вечеръ" as common nouns ("Музыкально-
Литературный вечеръ" = "an evening of music and literature"), not the structural УТРО./ВЕЧ. session
marker. Heuristic ruled out as stated; a stricter anchored pattern might avoid this but wasn't tried
since there's no confirmed real example of the underlying premise (marker text leaking into
annotation while time_of_day fails to update) to test against.

No data mutated by either investigation.

## 2026-09-22 — two new suspected phantom-session bugs found while testing label convention (DEFERRED, not fixed)

While testing whether the УТРО/ВЕЧ label-per-row convention (see session-completeness doc) holds across
seasons, picked two-page-spread multi-theater-split candidates via:
```sql
select page_id, date_text, count(distinct theater) from (
    select page_id, date_text, theater, count(*) n from raw.event_entry group by 1,2,3 having count(*)>1
) group by 1,2 having count(distinct theater)>=2
```
Both candidates checked against their actual scans turned out NOT to be genuine splits:
- `repertoire_1893-94_pair008`, "11 Четвергъ.": scan shows a single undivided row for every theater
  (ForUpload_1893-94_Repertoire.pdf page index 3, printed pp.14-15 area). DB's "morning" session for
  Большой (459 р. 19 к.) is actually "10 Среда."'s real content (visually confirmed matching receipts),
  mislabeled onto the wrong date. Малый/Маріинскій/Михайловскій's "morning" sessions for this date not
  yet traced to their true source.
- `repertoire_1892-93_pair014`, "3 Воскресенье.": scan confirms Александринскій genuinely splits
  (УТРО 280 р. 90 к./ВЕЧЕРЪ 1670 р. 91 к., matches DB exactly) but Большой and Малый are single lines
  in print (2053 р. 70 к. and 1379 р. 48 к. only). DB's "morning" sessions for those two (1099 р. 29 к.,
  694 р. 71 к.) don't match anything visible on this row -- not yet traced to their true source. Notable:
  this is a page already extensively fixed earlier this session (issue #77 addendum, the 244->162
  session truncation) -- this is a separate, still-open residual issue on the same page, not something
  that fix should have caught.

RG's call: defer fixing both, keep working the label-convention question. Flagging here so neither is
lost -- next step when revisited is tracing where each phantom "morning" receipts figure actually
belongs (same technique used throughout issue #77: match by exact receipts figure against nearby real
dates on the same page).

## 2026-09-22 — third suspected phantom-session bug found (same session, DEFERRED)

- `repertoire_1891-92_pair020`, "23 Понед." (ForUpload_1891-92_Repertoire.pdf page index 9, printed
  pp.20-21): scan shows Маріинскій/Михайловскій/Большой/Малый all completely dark ("—") for this date
  -- a Lenten closure stretch (surrounding dates 9 Марта-6 Апреля 1892 show almost the whole table dark
  except a German/French touring troupe at Александринскій). DB currently shows Большой, Малый, and
  Маріинскій each with a full 2-session (morning+evening, both receipts NULL) performance for this date
  -- doesn't match the scan at all. Third instance of this general bug shape found today (see the two
  logged above), each on a different page/season (1893-94_pair008, 1892-93_pair014, 1891-92_pair020) --
  possibly systemic rather than three isolated incidents, worth keeping in mind when this is picked back
  up. Deferred per RG, not investigated further or fixed.

## 2026-09-22 — fourth instance + a discriminating signal found

- `repertoire_1890-91_pair004`, "8 Суббота" (ForUpload_1890-91_Repertoire.pdf page index 1, printed
  pp.4-5): scan shows Маріинскій/Александринскій/Михайловскій completely blank and Большой/Малый each
  with a single УТРО-only entry, not the 5-theater full 2-session set the DB shows. Fourth instance of
  the same bug shape today, across four different seasons (1890-91, 1891-92, 1892-93, 1893-94).

Noticed a pattern across all 4 bad instances: every single one has NULL receipts_text on BOTH sessions.
The one genuine split scan-confirmed today (repertoire_1892-93_pair014's Александринскій, "3 Воскресенье.")
has real, distinct receipts on both sides (280 р. 90 к. / 1670 р. 91 к.). Filtering multi-theater-split
candidates to require non-NULL receipts on both sessions as a cheap way to avoid re-picking another
instance of this bug class.

## 2026-09-22 — CRITICAL: earlier fix today (repertoire_1893-94_pair006, 14 Четвергъ.) confirmed wrong

Scan (ForUpload_1893-94_Repertoire.pdf page index 2, printed pp.6-7) shows "14 Четвергъ." as a SINGLE
undivided row for all 5 theaters -- no УТРО/ВЕЧ split anywhere. Маріинскій=2946 р. 20 к. only,
Малый=617 р. 29 к. only, Большой=1941 р. 47 к. only (all matching the "evening" values kept earlier
today). The "morning" sessions kept as genuine in this session's earlier duplicate_event_key work
(2999 р. 20 к. Маріинскій, 1158 р. 27 к. Малый, 1099 р. 91 к. Большой) do not appear anywhere on this
row. That earlier fix correctly identified and dropped ONE phantom row (the "unspecified" duplicate,
_source human:kept_top) but incorrectly kept the "morning" row as genuine -- it is ALSO phantom, just
with different-looking numbers that didn't trip the identical-receipts duplicate check used at the time.
This fix is currently live in outputs/full_run (promoted earlier today).

This is now 5 of 5 two-page-spread multi-theater-split candidates checked today that turned out to be
this same bug shape, including this one already "fixed" and promoted. No longer looks like isolated bad
pages -- looks like a systemic reliability problem with two-page-spread season morning/evening session
pairs generally. Not fixed -- reporting to RG before continuing, per instruction to defer fixes but this
crosses into "something already promoted is wrong," which is different from the other 4 deferred items.

## 2026-09-22 — repertoire_1892-93_pair014 Маріинскій reconstruction: verification queries

```sql
select date_text, theater, time_of_day, receipts_text from raw.event_entry
where page_id='repertoire_1892-93_pair014' and theater='Маріинскій' order by date_undate
```
Result: used before/after to confirm the RG-verified 27 Дек-3 Янв sequence landed correctly post-rebuild.

```sql
select count(*) from raw.event_entry;               -- 21228 (final)
select count(*) from raw.person_entry;               -- 21168 (byte-identical)
select count(*) from entities.person_wikidata_link;  -- 43 (byte-identical)
```
Result: build_entities.py baseline confirmed exactly (2900 live/1459 tombstoned/23 preserved).
validate_performance_dates.py unchanged at 95.6%. Promoted to outputs/full_run (backup:
outputs/full_run_pre_promote_backup_2026-09-22_cascadeaudit/).

## 2026-09-22 — repertoire_1892-93_pair014 full 5-theater reconstruction via RG markup: verification

```sql
select date_text, theater, time_of_day, receipts_text from raw.event_entry
where page_id='repertoire_1892-93_pair014' and date_text in
  ('27 Декабря.','28 Понед.','29 Вторн.','30 Среда.','31 Четвергъ.','1 Пятн.','2 Суббота.','3 Воскресенье.','4 Понед.')
order by date_undate, theater, time_of_day
```
Result: used to compare current DB state against the RG-markup-verified reference table for
Александринскій/Михайловскій/Большой before writing the fix (Малый/Маріинскій already fixed earlier
the same day).

```sql
select count(*) from raw.event_entry;               -- 21230 (final)
select count(*) from raw.person_entry;               -- 21168 (byte-identical)
select count(*) from entities.person_wikidata_link;  -- 43 (byte-identical)
```
Result: build_entities.py baseline confirmed exactly (2900 live/1459 tombstoned/23 preserved).
validate_performance_dates.py unchanged at 95.6%. Promoted to outputs/full_run.

All 5 theaters now fully corrected for 27 Декабря-4 Января on this page. Remaining: 5 Января-16 Января
on this same page, and all 33 other flagged pages from the Tier-0 audit -- untouched.

## 2026-09-22 — repertoire_1892-93_pair014 full resolution: 6 Января fold row + page-header bug

```sql
select date_text, date_undate, theater, time_of_day, receipts_text
from raw.event_entry where page_id='repertoire_1892-93_pair014' order by event_id limit 20
```
Result: found date_undate wrongly resolving January dates to December (e.g. "1 Пятн." -> 1892-12-01).
Traced to a wrong page_header_dates.csv entry for this page_id ("4 декабря. 1892 г. 26 декабря." --
same start/end month, hitting _backfill_month_year's fast-path default). Compared against sibling
"pair014" pages in other seasons (correct season-crossing format confirmed) before fixing.

```python
# outputs/repertoire_spreadfix_v6/page_header_dates.csv and
# outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv:
# repertoire_1892-93_pair014 header corrected to "27 декабря. 1892-1893 гг. 16 января."
```
Result: re-ran parse_and_validate.py, confirmed date_undate now correct across the whole page
(27 Дек->1892-12-27, 1 Пятн->1893-01-01, 16 Суббота->1893-01-16).

```sql
select theater, session, receipts_text, [work titles] from raw.event_entry (via raw JSON)
where page_id='repertoire_1892-93_pair014' and date_text='6 Среда.'
```
Result: 4 of 5 theaters already correctly captured (titles present, receipts null -- genuine
page-fold illegibility, not a gap); Александринскій missing outright, added with the same
null-receipts convention, title read directly from RG's markup.

```sql
select theater, ... from raw.event_entry
where page_id='repertoire_1892-93_pair014' and date_text in ('7 Четвергъ.'...'16 Суббота.')
```
Result: entire 7 Января-16 Января range already correct in the DB, no fixes needed -- the cascade
corruption was confined to 27 Декабря-6 Января.

```sql
select count(*) from raw.event_entry;               -- 21231 (final)
select count(*) from raw.person_entry;               -- 21168 (byte-identical)
select count(*) from entities.person_wikidata_link;  -- 43 (byte-identical)
```
Result: build_entities.py baseline confirmed exactly. validate_performance_dates.py improved
95.6% -> 95.8% (header fix alone removed false date-mismatch noise page-wide). Promoted.

**repertoire_1892-93_pair014 is now fully resolved, every date, every theater.**

## 2026-09-22 — Broadened audit: weekday-disagreement % by page_id, two-page-spread corpus

```sql
-- (via validate_performance_dates.py's analysis.event_entry_date_check output,
--  aggregated by page_id, sorted by pct intra_block_disagreement/unresolved)
```

Result: top 4 "100%-flagged" pages (1892-93_pair022, 1892-93_pair008,
1894-95_pair016, 1895-96_pair008) all use pure "day + month" date_text
(no weekday word) -- confirmed via direct code read of
validate_performance_dates.py (~line 200-201) that this date format is
automatically flagged regardless of correctness. Signal is not a valid
proxy for the cascade bug on these pages; false positive.

## 2026-09-22 — repertoire_1892-93_pair022: printed page-number range and current DB state

```sql
-- grep repertoire_1892-93_pair022 outputs/repertoire_singlepage_pagenumbers/printed_page_numbers/1892-93.csv (or equivalent)
```

Result: pair022 spans 1893-04-09 to 1893-04-21 (printed pages 22-23).

```python
data = json.load(open('outputs/full_run/raw/repertoire_1892-93_pair022.raw.json'))
for s in data['sessions']: print(s['date_text'], s['theater'], s['session'], s['is_dark'], s['receipts_text'], [w['work_title'] for w in s['works']])
```

Result: 65 sessions, 9-21 апрѣля, all 5 theaters present every date
except is_dark=True blocks on 10th (4 of 5 theaters) and 17th (4 of 5
theaters). No morning/evening splits present anywhere on the page.

## 2026-09-22 — repertoire_1892-93_pair022 direct scan verification, 9-12 апрѣля

Rendered ForUpload_1892-93_Repertoire.pdf at 300dpi
(pipeline/render_pages.py), read page index 10 (repertoire_1892-93_p010.png),
compared 9/10/11/12 апрѣля (incl. page-fold boundary at 11th) against
current DB raw JSON directly (visual read, no SQL).

Result: exact match on all 5 theaters' works and receipts for all 4
dates checked, including dark-cell pattern on the 10th. No evidence of
the pair014-style dropped-session cascade. Page confirmed clean.

## 2026-09-22 — repertoire_1895-96_pair008: theater count check

```python
data = json.load(open('outputs/full_run/raw/repertoire_1895-96_pair008.raw.json'))
print(sorted(set(s['theater'] for s in data['sessions'])), len(data['sessions']))
```

Result: only ['Малый.'], 15 sessions total. Маріинскій/Александринскій/
Михайловскій/Большой entirely absent from this page's raw JSON.

## 2026-09-22 — repertoire_1895-96_pair008: "31 Ноября." date_undate check

```sql
SELECT date_text, date_undate FROM raw.event_entry
WHERE page_id = 'repertoire_1895-96_pair008' AND date_text LIKE '%Ноября%';
```

Result: date_undate correctly resolved to 1895-10-31 despite the
verbatim OCR-quirky date_text "31 Ноября." -- not a bug, matches
verbatim-raw/corrected-analysis-layer convention. No fix needed.

## 2026-09-22 — Corpus-wide sweep: distinct theaters per two-page-spread page_id

```python
import json, glob
for f in sorted(glob.glob('outputs/full_run/raw/repertoire_*_pair*.raw.json')):
    data = json.load(open(f))
    theaters = set(s['theater'] for s in data['sessions'])
    if len(theaters) <= 3:
        print(f, len(theaters), sorted(theaters))
```

Result: 28 of the two-page-spread pages show <=3 distinct theaters
(expected 5); 7 of those show only 1 theater for their entire date
range (1891-92_pair018, 1891-92_pair024, 1893-94_pair022,
1893-94_pair024, 1894-95_pair004, 1895-96_pair008, 1896-97_pair020) --
logged as new issue #78 in known_issues.md. The remaining 21 pages
show varying 2-3-theater subsets, more consistent with genuine partial
closures than a uniform bug; not yet individually verified.

## 2026-09-22 — Single-page-season (1898-99+) morning/evening split status

```sql
SELECT sp.season, ee.time_of_day, count(*) n
FROM raw.event_entry ee JOIN raw.source_pages sp ON ee.page_id = sp.page_id
WHERE sp.season >= '1898-99'
GROUP BY sp.season, ee.time_of_day ORDER BY sp.season, ee.time_of_day;

-- remaining unconverted duplicate (page_id, date_text, theater) groups still 'unspecified'
SELECT ee.page_id, ee.date_text, ee.theater, count(*) n
FROM raw.event_entry ee JOIN raw.source_pages sp ON ee.page_id = sp.page_id
WHERE sp.season >= '1898-99' AND ee.time_of_day = 'unspecified'
GROUP BY ee.page_id, ee.date_text, ee.theater HAVING count(*) >= 2;

-- 1906-07 morning/evening count imbalance by page/theater
SELECT ee.page_id, ee.theater,
       count(*) FILTER (WHERE ee.time_of_day='morning') m,
       count(*) FILTER (WHERE ee.time_of_day='evening') e
FROM raw.event_entry ee JOIN raw.source_pages sp ON ee.page_id=sp.page_id
WHERE sp.season = '1906-07'
GROUP BY ee.page_id, ee.theater HAVING m != e;
```

Result: each single-page season (1898-99 through 1907-08) has 87-168
morning/evening pairs (11-18% of sessions split), roughly balanced.
Zero remaining unconverted duplicate-key groups corpus-wide -- the
issue #77 duplicate_event_key fix (69 rows) fully closed that specific
pattern, confirmed fresh. One apparent imbalance found
(repertoire_1906-07_p015, 3 theaters showing evening>>morning) --
inspected directly: this page tags most single (non-split) sessions
explicitly as time_of_day='evening' rather than 'unspecified', which
is a legitimate page-level printed-convention difference, not a bug;
only 14 Вторн. (all 3 theaters) and 19 Воскрес. (Большой) are genuine
splits, both correctly captured. No fix needed.

## 2026-09-22 — Does the missing-theater-column bug (issue #78) extend into the single-page format?

```python
import json, glob, collections
rows = []
for f in sorted(glob.glob('outputs/full_run/raw/repertoire_*.raw.json')):
    name = f.split('/')[-1].replace('repertoire_','').replace('.raw.json','')
    if 'pair' in name: continue
    data = json.load(open(f))
    theaters = set(s['theater'] for s in data['sessions'])
    rows.append((name, len(theaters)))
print(collections.Counter(n for _, n in rows))
```

Result: 421/431 single-page-format pages have exactly 3 theaters
(the normal structure for this format -- pages alternate Petersburg
{Александринскій/Маріинскій/Михайловскій} vs Moscow {Большой/Малый/
Новый} groups). 9 pages show 5 (leftover un-split two-page-spread
season renders, not part of this format). 1 page,
`1906-07_p046`, shows only 1 theater.

```python
data = json.load(open('outputs/full_run/raw/repertoire_1906-07_p046.raw.json'))
# and neighbors p044/p045/p047/p048 for date range + city-group comparison
```

Result: `1906-07_p046` (dates 2-12 Февраля, same range/city-group as
`p044`) has only Михайловскій; Александринскій and Маріинскій are
completely absent from the page's raw JSON -- confirmed instance of
the issue #78 missing-column bug in the later single-page format, not
just the two-page-spread seasons. Scope not yet swept beyond this one
page for this format.

## 2026-09-23 — repertoire_1891-92_pair018: page-range and gap check before reconstruction

```sql
-- grep repertoire_1891-92_pair018/pair016 in page_header_dates.csv
```

Result: pair016 = 22 января-10 февраля 1892; pair018 = 11 февраля-8
марта 1892 -- contiguous, no overlap. Confirms the 17-22 Февраля gap
found on pair018's scan is not a page-boundary artifact (neither
neighboring page covers it either).

## 2026-09-23 — repertoire_1891-92_pair018: full rebuild verification post-fix

```bash
uv run python pipeline/parse_and_validate.py --manifest outputs/full_run/manifest.csv --raw-dir outputs/full_run/raw --out-dir outputs/full_run/parsed --page-headers outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv
uv run python pipeline/quality_checks.py --parsed-dir outputs/full_run/parsed --out outputs/full_run/quality_flags.csv
uv run python pipeline/build_duckdb.py --parsed-dir outputs/full_run/parsed --manifest outputs/full_run/manifest.csv --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/validate_performance_dates.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_entities.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_datasette.py --db outputs/full_run/imperial_theaters.duckdb --out outputs/full_run/research_dataset.sqlite
```

Result: raw.person_entry 21168 (byte-identical), entities.person 2900
live/1459 tombstoned/23 candidate-pairs preserved (all baselines
unchanged), entities.person_wikidata_link 43 (byte-identical).
quality_flags.csv: 887 flags, all pre-existing Musicians/staff-record
categories (institution_duplicated_in_heading_path, credit_sum_mismatch,
duplicate_person_on_page, rank_class_left_in_heading_path) -- zero
Repertoire-page flags, confirmed by filtering page_id LIKE
'repertoire%'. validate_performance_dates.py: 95.8% verified corpus-
wide, unchanged from pre-fix baseline. repertoire_1891-92_pair018 now
shows 127 raw.event_entry rows across all 5 theaters (confirmed via
`SELECT DISTINCT theater ... WHERE page_id='repertoire_1891-92_pair018'`).
Backed up pre-fix DB to outputs/full_run_pre_promote_backup_2026-09-23_pair018/
before rebuilding in place. Not yet promoted further (HF/Cloud Run
republish still deferred per established convention).

## 2026-09-23 — detect_columns / merge_columnwise_page root-cause investigation for issue #78

Read pipeline/row_detect.py's detect_columns (crop generation) and
pipeline/schemas/repertoire_columnwise.py's merge_columnwise_page (date
alignment) directly, plus outputs/repertoire_spreadfix_v6/raw_columnwise/
repertoire_1891-92_p018.columns.json.

Result: NOT a column-crop-detection failure -- the model successfully
extracted real content for all 5 theaters on pair018. The failure is in
merge_columnwise_page: when a theater's own row count doesn't reconcile
against the calendar date count (exactly, or via the compound-day
arithmetic fallback), it deliberately emits nothing for that theater
rather than guess (a reasoned tradeoff, see pipeline/schemas/
repertoire_columnwise.py's docstring, issue #69). The refusal itself is
recorded (`"ok": false`, with a `reason`) but nothing downstream turns
these into a corpus-wide flag -- that's the actual gap issue #78
describes.

```python
import json, glob
# count pages/theaters with ok:false across all raw_columnwise .columns.json
```

Result: 164 of 177 two-page-spread half-pages (92.7%) have >=1 failed
theater; 558 total failed theater-columns corpus-wide. This is a finer
grain than the 28-page/7-severe scope found 2026-09-22 -- most
half-page failures get rescued by the other half or a later repair
step; only when BOTH halves fail for the same theater does it surface
as a fully-missing column in the final promoted DB.

## 2026-09-23 — repair_columnwise_merge.py pilot, 6 severe pages (12 half-pages)

Regenerated split top/bottom half images (render_pages.py -> 
split_spread_pages.py against outputs/fold_review/fold_geometry.json,
5 seasons: 1891-92/1893-94/1894-95/1895-96/1896-97) since the original
split images are not retained on disk (outputs/ disposable by
convention). Verified true printed page numbers directly against scans
(not the pre-existing split_page_numbers_final.csv, which has at least
one confirmed error -- 1891-92_p008__bottom read "61" instead of "19")
-- all 6 confirmed via exact date-range match against page_header_dates.csv.

Ran pipeline/repair_columnwise_merge.py against the 12 renamed half-pages,
--raw-dir outputs/repertoire_spreadfix_v6/raw_columnwise, --column-config
docs/repertoire_column_bounds.json.

Result: 95 theater-repair attempts -- 8 recovered_tier1_resample (clean),
35 recovered_tier2_baseline (tool's own "NEEDS REVIEW" flag), 42
tier1_still_unresolved, 10 unrecovered. 2 of 12 half-pages
(1891-92_p025, 1896-97_p021) got zero recovery on every theater. Several
pages' fresh date-only re-read returned far fewer calendar dates than
the original attempt (e.g. 1893-94_p022: 16 -> 3), which directly
contradicts direct scan reads done the same session -- indicates the
regenerated split crops are not geometrically identical to whatever
produced the original raw_columnwise data. Decision: use this repaired
output only as a secondary cross-check alongside the original raw
columnwise data during manual scan reconstruction, not as a
promotable source on its own.

## 2026-09-23 — repertoire_1891-92_pair024, 1893-94_pair022, 1893-94_pair024: full rebuild verification

```bash
uv run python pipeline/parse_and_validate.py --manifest outputs/full_run/manifest.csv --raw-dir outputs/full_run/raw --out-dir outputs/full_run/parsed --page-headers outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv
uv run python pipeline/quality_checks.py --parsed-dir outputs/full_run/parsed --out outputs/full_run/quality_flags.csv
uv run python pipeline/build_duckdb.py --parsed-dir outputs/full_run/parsed --manifest outputs/full_run/manifest.csv --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/validate_performance_dates.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_entities.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_datasette.py --db outputs/full_run/imperial_theaters.duckdb --out outputs/full_run/research_dataset.sqlite
SELECT DISTINCT theater FROM raw.event_entry WHERE page_id='...';
```

Result: no validation errors on any of the 3 pages, zero Repertoire
quality flags, all baselines unchanged (person_entry 21168, entities
2900/1459/23), validate_performance_dates.py improved 95.9% -> 96.0%.
All 3 pages confirmed showing all 5 theaters (75/100/90 rows
respectively). Backed up pre-fix DB to
outputs/full_run_pre_promote_backup_2026-09-23_severepage3/ before
rebuilding in place.

## 2026-09-23 — repertoire_1896-97_pair020: RG-markup-verified reconstruction and rebuild

Extracted single source PDF page (ForUpload_1896-97_Repertoire.pdf,
index 9) to outputs/repertoire_markup/pair020_page_for_markup.pdf for
RG to mark up (red=date boundaries, blue=morning/evening splits).
Read back the marked-up PDF, rendered at 3x zoom, cropped section by
section. Markup resolved the key ambiguity: Михайловскій never splits
on this page even on dates where the other 4 theaters do -- it runs a
single nightly production across several consecutive dates, with the
title printed once and each night's own receipts figure positioned
below it, which had looked like an ambiguous multi-day merged cell
without the markup.

```bash
uv run python pipeline/parse_and_validate.py --manifest outputs/full_run/manifest.csv --raw-dir outputs/full_run/raw --out-dir outputs/full_run/parsed --page-headers outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv
uv run python pipeline/quality_checks.py --parsed-dir outputs/full_run/parsed --out outputs/full_run/quality_flags.csv
uv run python pipeline/build_duckdb.py --parsed-dir outputs/full_run/parsed --manifest outputs/full_run/manifest.csv --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/validate_performance_dates.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_entities.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_datasette.py --db outputs/full_run/imperial_theaters.duckdb --out outputs/full_run/research_dataset.sqlite
SELECT DISTINCT theater FROM raw.event_entry WHERE page_id='repertoire_1896-97_pair020';
```

Result: no validation errors, zero Repertoire quality flags, baselines
unchanged (person_entry 21168, entities 2900/1459/23),
validate_performance_dates.py unchanged at 96.0%. Page confirmed
showing all 5 theaters (113 rows). This closes out all 7 of the
original issue #78 severe (single-theater) pages. Backed up pre-fix
DB to outputs/full_run_pre_promote_backup_2026-09-23_pair020/ before
rebuilding in place.

## 2026-09-23 — Correction: are the 21 partial-subset pages genuine closures or the same bug?

```python
import json, glob
# For each of the 21 pages, map pairNNN -> p{NNN}/p{NNN+1}, check the
# "missing" theaters' n_theater_rows and ok status in each half's
# .columns.json merge report.
```

Result: ALL 21 pages, every missing theater, both halves: n_theater_rows
is substantial and nonzero (range 7-20 rows), ok:False throughout. Zero
instances of n_theater_rows near 0 (which would indicate a genuinely
dark/closed theater). This directly contradicts yesterday's hypothesis
that these pages reflect real partial theater closures -- every one is
the same merge_columnwise_page alignment-refusal bug as the 7 severe
pages, just less complete data loss (2-3 of 5 theaters vs 4-5 of 5).
Corrects known_issues.md's prior characterization of this bucket as
"more likely genuine closures, lower priority."

## 2026-09-23 — All 21 partial-subset pages: final rebuild verification

```bash
uv run python pipeline/parse_and_validate.py --manifest outputs/full_run/manifest.csv --raw-dir outputs/full_run/raw --out-dir outputs/full_run/parsed --page-headers outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv
uv run python pipeline/quality_checks.py --parsed-dir outputs/full_run/parsed --out outputs/full_run/quality_flags.csv
uv run python pipeline/build_duckdb.py --parsed-dir outputs/full_run/parsed --manifest outputs/full_run/manifest.csv --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/validate_performance_dates.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_entities.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_datasette.py --db outputs/full_run/imperial_theaters.duckdb --out outputs/full_run/research_dataset.sqlite
-- + a loop over all 21 page_ids: SELECT DISTINCT theater FROM raw.event_entry WHERE page_id=...
```

Result: zero validation errors, zero Repertoire quality flags across all 21
pages, baselines unchanged (person_entry 21168, entities 2900/1459/23,
Wikidata links unchanged), validate_performance_dates.py improved
95.6% (session start) -> 96.4% corpus-wide. All 21 pages confirmed
showing all 5 theaters via direct query. This closes issue #78's full
28-page scope (7 severe + 21 partial-subset).

## 2026-09-23 — Second-pass verification, issue #78: pair014 (1897-98) cascade + Михайловскій gap

```sql
-- verification was via direct raw JSON dump (dump_page.py) + scan re-read, not SQL;
-- post-fix structural check:
SELECT theater, date_text, session, COUNT(*) FROM raw.event_entry
WHERE page_id = 'repertoire_1897-98_pair014' GROUP BY 1,2,3 HAVING COUNT(*) > 1;
```

Result: Re-verifying `1897-98_pair014` (the page with the already-known 6-9
Января Маріинскій cascade, fixed last session) turned up two MORE real
errors on the same page, both missed in the first pass:

1. **Михайловскій was missing its entire 1-9 Января tail** (8 dates) —
   present on the scan, absent from the DB. Added via direct scan read.
2. **Малый had its own one-row cascade**: 29 Понедѣльник's evening session
   was dropped during the first-pass transcription, which pushed every
   subsequent date's content back by one slot — 30 Вторникъ showed 29's
   true evening content, 31 Среда showed 30's true content (both
   sessions), and 31 Среда's OWN true content (Полоцкое разоренье /
   Питомка) was lost entirely, never captured under any date. 2 Пятница
   was separately missing its own evening session. Also fixed a smaller
   error on 27 Суббота: two works that are one combined morning session
   ("На бойкомъ мѣстѣ" + "Женитьба", 522 р.) had been wrongly split into
   two separate sessions, with the evening one inventing a false
   dark=False no-receipts entry where the scan clearly shows evening is
   dark.

All fixes made directly against `outputs/full_run/raw/repertoire_1897-98_pair014.raw.json`.
Verified zero duplicate (theater, date_text, session) keys after the fix.
Re-ran `parse_and_validate.py` + `quality_checks.py`: 0 Repertoire quality
flags (887 total flags, all pre-existing Musicians/Roster baseline,
confirmed unrelated). 280 validation-failed pages is the pre-existing
baseline, none newly introduced (grepped — no `1897-98_pair014` entries in
`validation_errors.csv`).

This is exactly the failure class RG asked the second pass to specifically
guard against ("right performances end up associated with the correct
dates and times") — a shifted-by-one read that's internally self-
consistent and invisible to every automated check, only catchable by
re-reading the scan row-by-row.

## 2026-09-23 — Second-pass verification, issue #78: pair002 gap + pair006 field-categorization bug

Continuing the second pass (13 of 21 pages checked so far: 9 confirmed clean
with zero changes, 4 had real errors caught and fixed — see the pair014
entry above for the first two).

**`1896-97_pair002`**: Малый was missing its entire 5 Четвергъ - 11 Среда
tail (6 dates) — present on the scan, absent from the DB (same failure
class as every other issue #78 gap this session). Added directly from the
scan.

**`1896-97_pair006`**: Михайловскій "6 Воскресенье" had "Безчестные, др."
wrongly stored in the `annotation` field instead of as the first work in
the session's `works` list — the scan shows it printed identically to the
other two works on that date (no bénéfice/special-event formatting), so
this was a field-categorization error, not a date/performance
misattribution. Fixed by moving it into `works` and clearing the
annotation. Also corrected an OCR typo on the same session found in the
process: "Двѣ страницки любви" -> "Двѣ странички любви" (confirmed against
the same session's own re-read and against the correctly-spelled instance
of this same title elsewhere on the page, 23 Среда).

Verified zero duplicate (theater, date_text, session) keys on all 3 pages
touched this round. Re-ran `parse_and_validate.py` + `quality_checks.py`:
0 Repertoire quality flags (887 total, unchanged pre-existing Musicians/
Roster baseline); grepped `validation_errors.csv` for all 3 page_ids —
zero validation errors introduced.

Session paused here at RG's request (mid-second-pass). Remaining pages not
yet re-verified: 1894-95_pair010 (RG-markup, highest first-pass confidence
already), 1895-96_pair018, 1895-96_pair020, 1896-97_pair010, 1897-98_pair002,
1897-98_pair010, 1897-98_pair020, 1897-98_pair022, 1897-98_pair024 (8 of 21).

## 2026-09-23 — Second-pass verification, issue #78: pair018 (1895-96) major rebuild

Continuing the second pass. `1894-95_pair010` (RG's own hand-markup page,
highest first-pass confidence) re-verified clean: all 27 dates across 5
theaters matched perfectly, only one tiny OCR typo fixed ("Странчій подъ
столомъ" -> "Стряпчій подъ столомъ", confirmed against the correctly-
spelled instance of the same title elsewhere on the same page).

`1895-96_pair018` needed a much bigger rebuild than the first pass caught:

1. **3-4 Февраля**: the first-pass fix hardcoded `receipts_text=None` for
   every Маріинскій/Александринскій/Малый session added that day, despite
   all figures being clearly printed on the scan (8 receipts added). Also,
   Маріинскій genuinely splits into two sessions on 3 Суббота
   (Конекъ-горбунокъ 2892р70к morning / Вертеръ 2939р30к evening) but only
   one was captured. Separately, Большой's PRE-EXISTING data for these two
   dates (never touched by the first-pass fix, since Большой wasn't
   flagged as missing) had real column-bleed corruption: annotation fields
   contained garbled fragments of Малый's neighboring cell text
   ("Темная Анна Кер Гуверна" instead of blank; "Золот На тотъ" instead of
   "Бенефисъ кордебалета."), and work-title lists were mangled/truncated.
   Rebuilt both Большой sessions from a fresh scan read.
2. **11-27 Февраля**: the first pass assumed (based on a pattern confirmed
   on two OTHER pages, 1891-92 pair018/pair020) that Александринскій and
   Маріинскій were genuinely dark for this whole guest-troupe stretch,
   with only Михайловскій active. That assumption was wrong on THIS page:
   Александринскій ran its own separate German Schauspiel troupe on every
   single date (Die Venus von Milo, Der Dornenweg, Die Mütter, Das Glück
   im Winkel, Die Haubenlerche, Comtesse Guckerl -- 16 dates, all added),
   and Маріинскій ran its own guest opera ("Гибель Фауста") on 4 of those
   dates (odd Mon/Wed/Fri pattern: 19, 21, 23, 25 Февраля). Also caught and
   fixed a first-pass labeling bug: the row between 11 Воскрес. and
   13 Вторникъ had been mislabeled "13 Понед." instead of "12 Понед."
   (confirmed against Михайловскій's own untouched, correctly-labeled
   data for the same row).
3. **Большой, 20-27 Февраля**: missing entirely (not even a dark marker).
   20-24 and 27 are genuinely dark; 25 Воскрес has a real charity-concert
   entry ("Въ пользу фонда на учрежденіе... Музыкально-литературный вечеръ
   съ живыми картинами.", 4933 р.) that had never been captured at all.

This is the largest single-page correction of the second pass so far --
16 of 21 pages checked, this being the only one needing a rebuild this
size. Verified zero duplicate keys after each edit (caught and fixed one
duplicate-key mistake of my own mid-fix: forgot to remove the pre-existing
dark Маріинскій entries before adding the 4 real Гибель Фауста sessions).
Re-ran `parse_and_validate.py` + `quality_checks.py`: 0 Repertoire quality
flags, 887 total (unchanged pre-existing Musicians/Roster baseline), zero
new validation errors on either touched page.

## 2026-09-23 — Second-pass verification, issue #78: pair020 (1895-96) clean, pair010 (1896-97) three bugs

`1895-96_pair020` re-verified clean across all 22 dates/5 theaters -- zero
changes. Notably this page uses the SAME "guest troupe, other 4 theaters
dark" pattern that turned out wrong on its sibling page `pair018`; here
the pattern held (confirms per-page verification is still necessary even
when a neighboring page's assumption was wrong -- neither "trust the
pattern" nor "distrust the pattern" is a shortcut for reading the scan).

`1896-97_pair010`: three distinct bugs found, none of them a shifted-date
misattribution but all real:
1. A phantom duplicate Михайловскій entry under a nonexistent date label
   "2 Ноября." -- an exact duplicate (same works, same receipts) of the
   real "20 Среда." entry. No such row exists on the scan; deleted.
2. Михайловскій "14 Четвергъ." genuinely splits into a free morning
   student matinee and a paid evening show, but had been captured as ONE
   unspecified session pairing the morning's works with the evening's
   receipts and silently dropping the evening's own works entirely. Split
   into two correct sessions.
3. Малый was missing its entire 22 Пятница - 30 Суббота tail (9 dates),
   same failure class as elsewhere in this issue.

Self-caught a bug in my own fix script immediately after applying it: used
`None` instead of `False` for `is_dark` on 6 sessions, causing 6 pydantic
validation errors on `parse_and_validate.py` (a real, useful catch by that
automated check). Fixed by setting `is_dark=False` wherever it was `None`.
Re-ran validate + quality_checks: 0 errors, 0 Repertoire quality flags
(887 total, unchanged baseline). Zero duplicate keys confirmed.

16 of 21 pages now checked in the second pass; 5 remain:
`1897-98_pair002`, `1897-98_pair010`, `1897-98_pair020`, `1897-98_pair022`,
`1897-98_pair024`.

## 2026-09-23 — Second-pass verification, issue #78: pair002 (1897-98) duplicate-date-spelling bug

`1897-98_pair002`: found and fixed a duplicate-key bug invisible to the
`duplicate_event_key` structural check because it hides behind two
different spellings of the same date. The original whole-page
reconstruction added Александринскій sessions for "31 Воскресенье." and
"2 Вторникъ." without checking whether that date already existed under a
different date_text spelling -- it did, as "31 Воскрес." and "2 Вторник"
(no trailing "ъ."/"ъ"), both with byte-identical works and receipts. Since
the two spellings are different strings, the exact-match duplicate check
never caught it. Removed the two newer duplicates (kept the pre-existing
short-form entries, matching the spelling convention Большой/Малый
already used for the same two dates on this page). Rest of the page
(20 dates, 5 theaters) verified clean against the scan.

Zero duplicate keys confirmed after the fix. Re-ran validate + quality_checks:
0 errors, 0 Repertoire flags (887 total, unchanged baseline).

17 of 21 pages now checked in the second pass; 4 remain: `1897-98_pair010`,
`1897-98_pair020`, `1897-98_pair022`, `1897-98_pair024`.

## 2026-09-23 — Second-pass verification, issue #78: pair010 (1897-98) multiple cross-column bugs

`1897-98_pair010` had the highest bug density of any page in the second
pass -- five distinct issues, none of them simple gaps:

1. Two page-margin month-header artifacts ("21 ноября."/"22 ноября.")
   misread as real date rows during extraction (same failure class as
   pair010 1896-97's "2 Ноября." and pair018 1895-96's "13 Понед."). "21
   ноября." held real Маріинскій content that actually belongs under
   "21 Пятница." (renamed, not deleted -- Маріинскій had no other entry
   for that date). "22 ноября." entries (Маріинскій/Александринскій/
   Малый) were pure phantom dark duplicates of "22 Суббота." (deleted).
2. Александринскій "22 Суббота."/"23 Воскресенье." had cross-wired
   content: 22 Суббота is genuinely a single unsplit session ("Die
   versunkene Glocke", no receipts), but the DB had 23 Воскресенье
   утро's real content (Горе отъ ума, 276 р. 55 к.) wrongly attached to
   it as an "evening" session, while 23 Воскресенье утро itself wrongly
   showed "Die versunkene Glocke" instead of its own content. Untangled
   both.
3. Михайловскій had phantom duplicate entries on TWO dates (16
   Воскресенье, 30 Воскрес.) that were exact copies of Александринскій's
   split sessions rather than its own real, unsplit content.
4. On 30 Воскрес. specifically, this compounded into a second swap:
   Большой showed Михайловскій's real content (Севильскій цирюльникъ) in
   its own slot, while Большой's own true content (Сатанилла, бал.,
   1164 р. 54 к.) was missing from the DB entirely. Untangled: Мих ->
   Севильскій цирюльникъ, Бол -> Сатанилла.
5. One OCR title typo: "Воробьишкъ" -> "Воробышекъ" (confirmed against a
   clean crop; the source is legible, this was a straightforward misread).

None of these were shifted-date attributions in the pair014 sense (no
performance moved to a genuinely wrong day), but several put a
performance under the wrong THEATER, which matters just as much for "the
right performances end up associated with the correct dates" -- the date
was right, the venue was wrong. All five would have been invisible to
`quality_checks.py`'s duplicate/structural checks (each pairing that
created a duplicate did so under content, not under a literal
(theater, date, session) key clash for that pass -- the checks fired
correctly where they applied, but couldn't detect a same-key swap or a
different-date-string duplicate on their own).

Zero duplicate keys confirmed after all fixes. Re-ran validate +
quality_checks: 0 errors, 0 Repertoire flags (887 total, unchanged
baseline).

18 of 21 pages now checked in the second pass; 3 remain: `1897-98_pair020`,
`1897-98_pair022`, `1897-98_pair024`.

## 2026-09-23 — Second-pass verification, issue #78: pair020 (1897-98) clean, pair022 (1897-98) Михайловскій rebuild

`1897-98_pair020` re-verified clean across all 20 dates -- zero changes.

`1897-98_pair022`: Михайловскій was missing its entire 13-20 Марта stretch
(8 dates) entirely, plus a separate error around the 21-22 Марта boundary
-- the real content and receipts for 22 Воскресенье had been wrongly
merged into 21 Суббота's entry (which on the scan has no receipts and a
different annotation, a Dumas-monument benefit announcement), while two
phantom page-margin-header artifacts ("21 марта."/"22 марта.") sat in the
DB in place of real data. Also fixed two smaller mislabelings: "13 Мартъ."
was a mislabeled "13 Пятница." for both Маріинскій (real content) and
Большой (dark), and Большой's "23 Понед." wrongly carried 22
Воскресенье's charity-concert annotation (the scan shows that
announcement belongs only to 22 Воскресенье; 23 Понед. is genuinely dark,
already correctly captured separately as "23 Понедѣльникъ.").

Zero duplicate keys confirmed after all fixes. Re-ran validate +
quality_checks: 0 errors, 0 Repertoire flags (887 total, unchanged
baseline).

20 of 21 pages now checked in the second pass; 1 remains: `1897-98_pair024`.

## 2026-09-24 — Second-pass verification, issue #78: pair024 (1897-98) COMPLETE — all 21 pages checked

`1897-98_pair024`, the last of the 21 partial-subset pages: two real
errors found.

1. Малый was missing its entire "12 Воскресенье." split (present on the
   scan -- morning "Джентльмэнъ" 1369 р. 80 к., evening "И въ рукахъ было,
   да сплыло"/"За чѣмъ пойдешь, то и найдешь" 681 р. 13 к. -- absent from
   the DB, which had it as a single dark=True entry).
2. Александринскій "11 Суббота." was missing a third work ("Музыкальное
   отдѣленіе.") and its own charity-benefit annotation ("Спектакль въ
   пользу Общества попеченія о слабосильныхъ и выздоравливающихъ."). That
   exact annotation text had instead been misattached to "18 Суббота.",
   which is genuinely dark on the scan with no such announcement --
   removed the phantom copy there and restored it to its real home on
   11 Суббота., where the scan shows an explicit "УТРО." label confirming
   the session type too (fixed from unspecified to morning).

Zero duplicate keys confirmed after the fix. Re-ran validate +
quality_checks: 0 errors, 0 Repertoire flags (887 total, unchanged
baseline).

**This closes the second-pass verification pass in full: all 21 of the
21 partial-subset pages have now been independently re-checked against
the scans, distinct from and in addition to the first pass's own read.**
Summary across the whole second pass:
- 12 pages confirmed clean on first re-check, zero changes.
- 9 pages had real errors caught and fixed, none of them visible to any
  automated structural check (all internally self-consistent -- no
  duplicate keys, no validation failures) until the scan was re-read
  line by line: `1894-95_pair014`, `1896-97_pair002`, `1896-97_pair006`,
  `1896-97_pair010`, `1897-98_pair002`, `1897-98_pair010`,
  `1897-98_pair014` (already partially fixed once and STILL had two more
  bugs), `1897-98_pair022`, `1897-98_pair024`, plus the major
  `1895-96_pair018` rebuild.
- Failure classes found this pass, beyond the simple "missing date range"
  gap already characteristic of issue #78's first pass: phantom
  duplicate entries under a second spelling of the same date (invisible
  to exact-string duplicate checks), page-margin month-header text
  misread as a real date row, cross-column content bleed (one theater's
  annotation or works appearing in a neighboring theater's cell),
  theater-to-theater content swaps on a single date, and a wrong
  "genuinely dark" assumption carried over from a different page's
  confirmed pattern.

Next step: a consolidated full-chain rebuild (`build_duckdb.py` ->
`validate_performance_dates.py` -> `build_entities.py`), baseline
verification (Musicians/Roster untouched, quality_flags.csv still 0),
and a `known_issues.md` closing summary -- not yet done this session.

## 2026-09-24 — Sample scan-read of single-page-format Repertoire renders (1898-99 through 1907-08)

Following the completed issue #78 second pass (two-page-spread seasons,
1890-91-1897-98), RG asked whether the single-page-format seasons
(1898-99-1907-08, column-wise extraction, ~422 renders, per known_issues.md
only 1 previously checked) need the same treatment. Sampled 6 renders, one
per season, spread across the decade and across page position (early/mid/
late), scan-read in full against `pdf/RepertoireTables/ForUpload_<season>_
Repertoire_<NNN>.jpg` (these are the original per-page source images --
column-wise render used the same JPGs 1:1, `p{NNN}` = `_{NNN}.jpg`):

- `repertoire_1898-99_p005` -- 3 OCR title typos fixed ("Лѣсь"->"Лѣсъ",
  "Поэдная любовь"->"Поздная любовь", "Ночной пикинкъ"->"Ночной пикникъ").
  No structural/date errors.
- `repertoire_1899-00_p020` -- clean, zero changes.
- `repertoire_1901-02_p010` -- 3 issues: 2 instances of a mixed-script
  typo ("Мишурa" with a Latin "a" -> "Мишура"), 1 OCR typo repeated twice
  ("Беаприданница"->"Безприданница"), and one bénéfice line wrongly filed
  as a work title instead of an annotation ("Bénéfice de M-r Brouette").
- `repertoire_1903-04_p030` -- 5 issues, the most of any sample: a
  cross-column bleed bug (three of Маріинскій's charity-concert
  announcements had phantom truncated fragments leaking into
  Александринскій's annotation field on 17/19/29, one of which should
  have been genuinely dark and wasn't); a missing word in a German
  benefit-announcement title ("im" dropped from "für die Krieger im
  fernen Osten") that had also been wrongly filed as a work instead of
  an annotation; and one OCR digit error in a fractional-kopeck receipt
  ("15¹/₉" -> "15½", confirmed against the half-kopeck fraction notation
  used consistently elsewhere on the same page).
- `repertoire_1905-06_p015` -- 1 OCR typo repeated twice ("Неводь"->
  "Неводъ"). Also found and correctly left alone: Малый "24 Четвергъ."
  has a genuinely blank work title in the source print itself (just
  ", ком." with nothing before the comma, confirmed by direct zoom) --
  not an extraction error.
- `repertoire_1907-08_p045` -- clean, zero changes. The page's large
  21-27 Апрѣля dark stretch (all 3 theaters, all 7 dates) is genuine --
  confirmed against the scan, and consistent with Orthodox Holy Week/
  Easter 1908 (April 13/26 O.S./N.S.) -- not a bug.

**Summary: 2 of 6 pages completely clean, 4 had minor issues, 14 total
fixes -- but the error PROFILE is qualitatively different from the
two-page-spread pages just closed out in issue #78.** Every single error
found in this sample was an OCR misread or a field-categorization slip
(work title vs. annotation); NONE were a date/performance misattribution,
a missing theater column, or a cross-date cascade -- the failure classes
that dominated issue #78. This is consistent with the column-wise
extraction method for these seasons already being validated clean at Gate
3 (332/332, see `columnwise-paused-table-anchored-dividers` memory) for
its own structural correctness; this sample suggests genuine transcription
typos still exist at a low, steady rate (roughly 2-3 per page) but the
severe bugs this whole session has been chasing (missing columns, swapped
theaters, phantom duplicate dates) are much rarer here, though not zero --
the `1903-04_p030` cross-column bleed shows the same failure class CAN
occur in this format too, just less often.

Duplicate-key-checked (0 on all 6 pages), `parse_and_validate.py` +
`quality_checks.py` re-run: 0 new validation errors, 0 Repertoire quality
flags (887 total, unchanged baseline).

**Recommendation, not yet acted on**: given a ~67% per-page hit rate on a
tiny sample, a fuller sweep of the single-page-format seasons is probably
worth doing at some point, but not urgently -- unlike issue #78, nothing
found here misattributes a performance to the wrong date or theater,
which was RG's stated top concern. This is lower-stakes cleanup work.

## 2026-09-24 — Morning/evening split distribution, single-page-format seasons (1898-99–1907-08)

RG asked how single-page-format seasons handle morning/evening session
splits, after an initial 6-page sample suggested (wrongly) that splits
cluster on Sundays.

```sql
-- total split events, all 10 single-page seasons
SELECT COUNT(*) FROM raw.event_entry
WHERE time_of_day IN ('morning','evening')
  AND season IN ('1898-99','1899-00','1900-01','1901-02','1902-03',
                  '1903-04','1904-05','1905-06','1906-07','1907-08');

-- weekday distribution, corpus-wide
SELECT strftime(CAST(COALESCE(c.corrected_date_undate, e.date_undate) AS DATE), '%A') AS weekday,
       COUNT(*) AS n_split_events
FROM raw.event_entry e
JOIN analysis.event_entry_date_check c USING (event_id)
WHERE e.time_of_day IN ('morning','evening')
  AND e.season IN ('1898-99','1899-00','1900-01','1901-02','1902-03',
                    '1903-04','1904-05','1905-06','1906-07','1907-08')
GROUP BY 1 ORDER BY n_split_events DESC;

-- weekday distribution, broken out by season
SELECT e.season,
       strftime(CAST(COALESCE(c.corrected_date_undate, e.date_undate) AS DATE), '%A') AS weekday,
       COUNT(*) n
FROM raw.event_entry e
JOIN analysis.event_entry_date_check c USING (event_id)
WHERE e.time_of_day IN ('morning','evening')
  AND e.season IN ('1898-99','1899-00','1900-01','1901-02','1902-03',
                    '1903-04','1904-05','1905-06','1906-07','1907-08')
GROUP BY 1,2 ORDER BY 1, n DESC;

-- annotation breakdown on Monday-morning splits specifically
SELECT e.annotation, COUNT(*) n
FROM raw.event_entry e
JOIN analysis.event_entry_date_check c USING (event_id)
WHERE e.time_of_day = 'morning'
  AND e.season IN ('1898-99','1899-00','1900-01','1901-02','1902-03',
                    '1903-04','1904-05','1905-06','1906-07','1907-08')
  AND strftime(CAST(COALESCE(c.corrected_date_undate, e.date_undate) AS DATE), '%A') = 'Monday'
GROUP BY 1 ORDER BY n DESC;
```

Result: 2,230 total morning/evening split events across the 10 single-page
seasons. Corpus-wide weekday counts: Monday 992, Tuesday 306, Friday 218,
Thursday 205, Saturday 198, Sunday 184, Wednesday 127 -- every day of the
week appears, none at zero.

Broken out by season, the corpus-wide Monday total is not representative
of any individual season on its own -- it's an average over two distinct
patterns: 1898-99 and 1899-00 each have Tuesday as the top day (115, 116
events) with every other weekday, including Monday, in single or
low-double digits; 1900-01 through 1907-08 (all 8 remaining seasons) each
have Monday as the top day (84-164 events per season), with the
second-place day varying season to season (Friday, Saturday, or
Thursday) and no other single day close behind. In no season does one
weekday account for all or nearly all splits -- every season has splits
on every day of the week it was queried for, at varying counts.

Of 496 Monday-morning split events specifically, 433 (87%) carry no
`annotation` value at all -- the Monday concentration (in the 8 seasons
where it's the top day) is not primarily attributable to a specific named
event type (e.g. "free student matinee") captured in the annotation
field; only a minority (~63 rows) have any annotation, and those are a
mix of several different phrasings, not one dominant convention.

## 2026-09-24 — Do the single-page seasons have problems capturing split days?

RG asked directly whether there are real problems capturing morning/
evening splits in the single-page-format seasons (1898-99-1907-08),
following the weekday-distribution query above.

```sql
-- (page,theater,date) groups with more than 2 sessions -- structurally impossible
SELECT page_id, theater, date_text, COUNT(*) n, string_agg(time_of_day, ',') sessions
FROM raw.event_entry
WHERE season IN (<10 single-page seasons>)
GROUP BY 1,2,3 HAVING COUNT(*) > 2;
-- Result: 0 rows.

-- (page,theater,date) groups with exactly 2 sessions -- do they always pair morning+evening?
WITH g AS (
  SELECT page_id, theater, date_text,
         string_agg(time_of_day, ',' ORDER BY time_of_day) AS combo, COUNT(*) n
  FROM raw.event_entry
  WHERE season IN (<10 single-page seasons>)
  GROUP BY 1,2,3 HAVING COUNT(*) = 2
)
SELECT combo, COUNT(*) FROM g GROUP BY 1;
-- Result: ('evening,morning', 1098) -- all 1098 two-row groups are a clean pair, no mismatched pairs.

-- (page,theater,date) groups with exactly 1 session tagged morning or evening (no counterpart row at all)
WITH g AS (
  SELECT page_id, theater, date_text, COUNT(*) n,
         string_agg(time_of_day, ',' ORDER BY time_of_day) combo
  FROM raw.event_entry
  WHERE season IN (<10 single-page seasons>)
  GROUP BY 1,2,3
)
SELECT page_id, theater, date_text, n, combo FROM g WHERE combo IN ('morning','evening')
ORDER BY page_id, theater, date_text;
-- Result: 34 rows, on 7 distinct pages.
```

All 34 lone entries scan-verified page by page (source images in
`pdf/RepertoireTables/ForUpload_<season>_Repertoire_<NNN>.jpg`):

- **`repertoire_1906-07_p015`, 27 entries** (all 3 Moscow theaters,
  dates 15-23 Ноября minus the 20 Понед. dark day): scan shows these
  rows have no УТРО./ВЕЧЕРЪ. split structure printed at all -- each is a
  single, ordinary performance. The `time_of_day='evening'` tag on all
  27 is a mislabeling: the correct value is `unspecified`. The
  performance, date, and receipts themselves are correctly captured in
  every one of the 27; nothing is missing.
- **`repertoire_1906-07_p034`, 3 entries** (Михайловскій, 2/3/4 Пятница-
  Воскрес.): scan-confirmed same pattern -- no split printed for
  Михайловскій on these 3 dates (Маріинскій/Александринскій do split
  that day, Михайловскій doesn't), `time_of_day='morning'` should be
  `unspecified`. No missing content.
- **`repertoire_1901-02_p028`, 1 entry** (Михайловскій, 24 Воскрес.):
  same pattern, scan-confirmed no split printed, should be
  `unspecified`, no missing content.
- **`repertoire_1898-99_p030`, 1 entry** (Михайловскій, 28 Воскрес.):
  same pattern, scan-confirmed no split printed, should be
  `unspecified`, no missing content.
- **`repertoire_1905-06_p008`, 1 entry** (Маріинскій, 23 Воскрес.,
  morning): DIFFERENT signature -- the scan explicitly prints a "УТРО."
  label for this row (unlike the 32 above, which print no split label
  at all), meaning a real ВЕЧЕРЪ. entry existed in the source. That
  entry is genuinely absent from the DB: it is not on this render, not
  on the next Petersburg render (`p010`, which resumes at "24 Понед."
  with no continuation of "23 Воскрес."), and not on the intervening
  Moscow render (`p009`, a different city's tables for the same date
  range). **This is a confirmed real content gap, not a labeling
  artifact** -- one evening performance's data (title, receipts) is
  missing from the corpus entirely.
- **`repertoire_1905-06_p005`, 1 entry** (Новый театръ, 1 Суббота.,
  morning): AMBIGUOUS, not resolved. The scan shows a "УТРО." label (so,
  like the p008 case above, a split may genuinely exist) but the row
  sits at the very last line of the photographed page, cut off by the
  physical page edge; the next render (`p006`) resumes at "2 Воскрес."
  with no continuation. Could be a second genuine gap of the same kind
  as `p008`, or could be a page genuinely printed with only a morning
  show that day whose ВЕЧЕРЪ. label (if any) fell in unphotographed
  space. Not distinguishable from the scan alone without the physical
  volume.

**Answer to RG's question: yes, there are two distinct real problems**,
of very different severity:
1. **A session-mislabeling bug, 32 of 34 cases** (all except the last
   two above): a theater's single, unsplit performance on a date where
   at least one OTHER theater on the same row genuinely splits gets
   tagged `morning` or `evening` instead of `unspecified`. No
   performance/receipts data is lost in any of these 32 -- this is a
   metadata-correctness issue (a query filtering by `time_of_day` would
   misclassify these), not a missing-content issue.
2. **A genuine missing-evening-entry gap, at least 1 confirmed case (
   `1905-06_p008`, Маріинскій 23 Воскрес.) and 1 unresolved candidate
   (`1905-06_p005`, Новый театръ 1 Суббота.)**: real printed content
   that the extraction never captured, both located at a page-image
   boundary.

Not yet fixed. This was a corpus-wide structural query across all 10
single-page seasons (not limited to the earlier 6-page manual sample) --
it is a full accounting of every lone morning/evening entry in the
single-page-format corpus, not a further sample.

## 2026-09-24 — Fixed the 32 session-mislabeled entries (single-page seasons)

RG asked to fix the 32 confirmed session-mislabeling cases from the prior
query (excluding the 2 genuine-gap cases, `1905-06_p005` and
`1905-06_p008`, left untouched). Changed `session` from `morning`/
`evening` to `unspecified` in place on the affected `outputs/full_run/
raw/*.raw.json` files:

- `repertoire_1898-99_p030`: 1 entry
- `repertoire_1901-02_p028`: 1 entry
- `repertoire_1905-06_p015`: 1 entry
- `repertoire_1906-07_p015`: 27 entries
- `repertoire_1906-07_p034`: 3 entries

Total: 32. Two entries needed a direct fix pass after the first attempt
under-matched (theater name field has an inconsistent trailing period
within the same file in a couple of cases -- 'Новый театръ' vs 'Новый
театръ.' -- so an exact-string match missed them on the first pass;
matched by stripping the trailing period on retry).

Verified via a full corpus-wide re-scan (all 10 single-page seasons):
exactly 2 lone morning/evening entries remain, and they are precisely
the 2 genuine-gap cases that were deliberately excluded -- confirms no
over- or under-fixing. Zero duplicate (theater, date_text, session) keys
on all 5 touched pages. Re-ran `parse_and_validate.py` + `quality_checks.py`:
0 new validation errors, 0 Repertoire quality flags (887 total, unchanged
baseline).

The 2 genuine-gap cases (`1905-06_p005` Новый театръ 1 Суббота., 
`1905-06_p008` Маріинскій театръ 23 Воскрес.) remain open -- real,
scan-confirmed printed content (a ВЕЧЕРЪ. entry) that was never captured,
not a labeling issue. Not investigated further this round.

## 2026-09-24 — Extended sample scan-read to the remaining 4 single-page seasons

Extended the general-accuracy manual sample to the 4 single-page seasons
not covered by the original 6-page sample: 1900-01, 1902-03, 1904-05,
1906-07 (one render each). All scan-verified against
`pdf/RepertoireTables/ForUpload_<season>_Repertoire_<NNN>.jpg`.

- **`repertoire_1900-01_p012`** -- 7 fixes: a misfiled operetta title
  ("Не бывать-бы счастью, да несчастье помогло" was in `annotation`,
  moved to `works`); a truncated section-header annotation on
  Маріинскій's free-matinee morning session ("Безплатные спектакли для"
  cut off mid-sentence, completed to match the full header used
  elsewhere on the same page); a misfiled bénéfice line on Михайловскій
  18 Суббота ("Bénéfice de M-r Brouette" was in `works`, moved to
  `annotation`); 3 instances of a date_text OCR typo ("Четвергь" ->
  "Четвергъ", ь/ъ confusion); 1 instance of a work-title OCR typo
  ("Лѣсь" -> "Лѣсъ", same ь/ъ confusion, confirmed via zoom against a
  clean crop). Two suspicious-looking items checked and left alone as
  genuine print defects, confirmed by zoom: "Закать" (should grammatically
  be "Закатъ" but the print itself shows ь) and "994 р- 75 к." (a broken
  period rendered as a dash in the original type).
- **`repertoire_1902-03_p022`** -- the most substantial fix of this
  batch: Александринскій and Михайловскій both had a real, uncaptured
  morning/evening split on 26 Воскрес. -- the scan shows two distinct
  receipts figures stacked in one cell for each theater (no УТРО./
  ВЕЧЕРЪ. tick-mark column, but the visual grouping and figure count
  make the split unambiguous), which had been merged into one entry
  with only the evening receipts kept and the morning's own receipts
  entirely dropped. Also recovered one work title that had been dropped
  outright in the merge (Михайловскій's "Démocrite", printed as its own
  line between two other titles), and moved "Спектакль для учащейся
  молодежи" out of the merged works list into a proper `annotation` on
  the new morning sessions for both theaters. Plus 2 more OCR typos
  fixed: "Тріестанъ и Изольда" -> "Тристанъ и Изольда" (Wagner's
  Tristan und Isolde), "Воспитатель Фахсманъ" -> "Воспитатель
  Флаксманъ" (this character's name recurs across several 1900s-era
  pages and has now been seen misspelled three different ways --
  Фахсманъ, Флаксмансъ -- always confirmed against a clean crop before
  fixing). "Le deux écoles" (missing the plural -s on "Les") checked and
  left alone -- confirmed via zoom as the print's own typo, appearing
  consistently for this one specific occurrence while every other
  instance of the same title on the page correctly prints "Les deux
  écoles".
- **`repertoire_1904-05_p028`** -- 1 fix: "Жаннна" (extra н)
  -> "Жанина", confirmed against a clean crop and against the correct
  spelling used for the same title elsewhere on the page. The page's
  large 4-10 Февраля dark stretch (all 3 theaters, 7 consecutive dates)
  confirmed genuine against the scan -- no fix needed.
- **`repertoire_1906-07_p040`** -- 3 fixes, one of them a correction in
  the opposite direction from usual: "Воспитатель Флаксмансъ" (extra с)
  -> "Флаксманъ" (matches the confirmed-correct spelling); a spurious
  annotation that verbatim-duplicated the same session's own `works`
  content, removed; and -- confirmed by zoom -- the print genuinely
  reads "Съ повымъ годомъ" (not the grammatically-sensible "Съ новымъ
  годомъ", "Happy New Year"), which the DB had silently normalized to
  the sensible reading. Per this project's verbatim-transcription
  convention, restored the DB to match what the source actually prints,
  nonsensical as it is. Two more items checked and left alone as
  genuine print defects: "Husarenlieber" (grammatically should be
  "Husarenliebe", print shows the extra r) and "Das aite Heim"
  (grammatically "alte", print shows "aite" -- a broken/worn "l"
  glyph, confirmed by zoom).

Zero duplicate (theater, date_text, session) keys on all 4 pages.
Re-ran `parse_and_validate.py` + `quality_checks.py`: 0 new validation
errors, 0 Repertoire quality flags (887 total, unchanged baseline).

**All 10 single-page seasons now have at least one manually scan-read
sample page** (10 total pages checked across the two sampling rounds:
6 pages 2026-09-24 morning, 4 pages 2026-09-24 afternoon). Combined
error count: 2 of 10 sample pages completely clean
(`1899-00_p020`, `1907-08_p045`); 8 of 10 had fixes, ranging from a
single typo to the `1902-03_p022`
missed-split reconstruction. No date/performance misattribution of the
issue #78 kind found in this second batch either -- the errors remain
OCR typos, work/annotation field mixups, and (once, on `1902-03_p022`)
a missed split, not a shifted date or swapped theater.

## 2026-09-24 — Full sweep of remaining single-page-season Repertoire renders (post-sweep verification queries)

```sql
-- duplicate-key check across all 422 single-page-season raw JSON files (via Python, not SQL)
-- corpus-wide theater-column-count check (any page_id with <3 distinct theaters)
SELECT page_id, COUNT(DISTINCT theater) AS n_theaters
FROM raw.event_entry
WHERE page_id LIKE 'repertoire_18%' OR page_id LIKE 'repertoire_19%'
GROUP BY page_id
HAVING COUNT(DISTINCT theater) < 3;
```

Result: 0 duplicate-key files (422/422 clean); 0 pages with fewer than 3
theaters after the `repertoire_1906-07_p046` fix (was 1 before). Full
sweep covered all ~412 remaining single-page renders across 24 parallel
agent batches; see `docs/eval/known_issues.md` issue #79's final
addendum and `docs/eval/run_history.csv` row
`full_sweep_singlepage_2026-09-24` for the complete summary
(event_entry 21308->23181, Repertoire gold-eval 94.9%->96.1%,
validate_performance_dates.py verified rate 96.4% corpus-wide, 0
genuine Repertoire quality flags, Musicians/Roster isolation confirmed
byte-identical).

```sql
SELECT SUM(receipts_total_kopecks) FROM analysis.event_entry WHERE 0=1; -- not run; spot query only
```

Also ran, to confirm the 7 `receipts_parse_failed` flags: pulled
`date_text`/`theater`/`receipts_text`/`printed_page_number` for each of
the 7 flagged `event_id`s from `event_entry.csv` directly (not SQL --
parsed CSV read), then manually compared each against its source scan
image in `pdf/RepertoireTables/`. All 7 confirmed as genuine period
typesetting defects (rubles unit "р." misprinted as "к."/"и."/"г." in
the original print), left verbatim, no fix applied.

## 2026-09-24 — Sort out the 17 single-page-season `intra_block_disagreement` rows

```sql
SELECT e.page_id, e.event_id, e.date_text, e.theater, e.event_status, c.note
FROM analysis.event_entry_date_check c
JOIN raw.event_entry e ON e.event_id = c.event_id
WHERE c.date_confidence = 'intra_block_disagreement'
  AND e.season NOT IN ('1890-91','1891-92','1892-93','1893-94','1894-95','1895-96',
                        '1896-97','1897-98')
ORDER BY e.page_id, e.date_text;
```

Result: 17 rows across 5 pages. Scan-verified all 5 pages directly. Broke
down into three categories:

- **10 rows (1904-05_p014, 1905-06_p027, 1905-06_p036)**: NOT a data
  problem. These are the correctly-printed sibling rows of a day-number
  misprint already fixed via `_MANUAL_DATE_OVERRIDES` (e.g.
  `1904-05_p014`'s "28 Понед." should be "29 Понед." -- the book itself
  skips printing a "29" row). The override correctly resolves the
  misprinted row to `corrected_manual`; its sibling row (the OTHER,
  correctly-printed date sharing the same raw day-number) still shows
  `intra_block_disagreement` purely because the script groups rows by
  day-number-derived `date_undate`, and that block genuinely contains two
  different real calendar dates due to the source's own printing error.
  No further fix possible or needed -- confirmed both overrides and their
  sibling rows are already at their correct final state.
- **3 rows (1903-04_p010, "4 Ворникъ.")**: confirmed genuine period print
  typo (missing "т" in "Вторникъ") via scan -- all 3 theaters correctly
  transcribed the verbatim (wrong) printed text. Left as-is; will always
  show as `intra_block_disagreement` since "Ворникъ" doesn't parse as any
  weekday, which is expected/correct.
- **4 rows (1905-06_p014, "20 Воекрес.")**: confirmed a genuine
  EXTRACTION typo -- the scan clearly prints "20 Воскрес.". Fixed all 4
  sessions on that page, rebuilt the full chain. `verified` 22353->22357,
  `intra_block_disagreement` 666->662 in `analysis.event_entry_date_check`
  (exact match to the 4-row fix). No other numbers changed (Musicians/
  Roster untouched, quality_flags.csv unchanged at 894/7 receipts flags).

All 17 single-page-season `intra_block_disagreement` rows are now
accounted for -- 0 remaining open questions in this group.

## 2026-09-24 — What are the 22 `no_date` rows?

```sql
SELECT e.page_id, e.event_id, e.date_text, e.theater, e.date_undate, e.event_status
FROM analysis.event_entry_date_check c
JOIN raw.event_entry e ON e.event_id = c.event_id
WHERE c.date_confidence = 'no_date'
ORDER BY e.page_id;
```

Result: all 22 were on a single page, `repertoire_1906-07_p046` -- exactly
the 22 dark placeholder sessions (Маріинскій + Александринскій, 11 dates
each) added earlier this session to fix that page's dropped-theater-
column bug (see issue #79's final addendum). Root cause: those placeholder
sessions were created without `month_text`/`year_text`, and `1906-07`
is deliberately absent from `all_page_headers.csv` (per CLAUDE.md, that
season's baseline extraction normally populates month/year directly per
session, so it was never expected to need header backfill) -- so nothing
filled the gap in for these two synthetic rows. Fixed by copying the
`month_text: 'мая'` / `year_text: '1907 г.'` already present on every
real (Михайловскій) session on the same page onto the 22 placeholders.
Rebuilt the full chain: `no_date` 22 -> 0, `verified` 22357 -> 22379
(96.5%), exact +22 match. Musicians/Roster numbers unchanged.

## 2026-09-24 — Check the remaining `unresolved` and `corrected` date-check rows

```sql
SELECT e.page_id, COUNT(*), MIN(e.date_text), MAX(e.date_text)
FROM analysis.event_entry_date_check c
JOIN raw.event_entry e ON e.event_id = c.event_id
WHERE c.date_confidence = 'corrected'
GROUP BY e.page_id ORDER BY 2 DESC;

SELECT e.page_id, COUNT(*)
FROM analysis.event_entry_date_check c
JOIN raw.event_entry e ON e.event_id = c.event_id
WHERE c.date_confidence = 'unresolved'
GROUP BY e.page_id ORDER BY 2 DESC;
```

**`unresolved` (40 rows, 10 pages)**: scan-verified every page.

- **Two genuine extraction bugs found and fixed** (not print defects):
  `repertoire_1898-99_p020` (8 rows) had the Alexandrinsky column's
  `month_text` wrongly captured as "декабря" for 5 January dates (1, 2,
  3, 10, 11), while Маріинскій/Михайловскій correctly say "января" for
  the same dates -- scan confirms all are genuinely January performances.
  `repertoire_1903-04_p020` (1 row) had one Alexandrinsky evening
  session's `month_text` say "Январь" instead of "декабря", inconsistent
  with its own morning sibling on the same printed date. Fixed both
  (`month_text` corrected to match the sibling sessions/scan), rebuilt:
  `unresolved` 40->31, `verified` 22379->22388 (96.6%), exact +9 match.
- **The remaining 31 unresolved rows are all confirmed genuine period
  print defects**, left verbatim: `repertoire_1899-00_p037` (3, already
  documented, out-of-sequence "9 Четвергъ"), `repertoire_1898-99_p017`
  (3, "28 Среда." printed after a 12-day gap), `repertoire_1904-05_p011`
  (3, "23 Пятница." should be "5 Пятница."), `repertoire_1905-06_p023`
  (4, New Year's Day mislabeled "1 Вторникъ" instead of Sunday),
  `repertoire_1906-07_p041` (3, "6 Понед." should be "6 Пятница."), plus
  the two-page-spread residuals `repertoire_1892-93_pair024` (5, "2
  Вторн." should be Sunday), `repertoire_1893-94_pair004` (5) and
  `repertoire_1894-95_pair008` (5) -- both already investigated in
  earlier sessions, re-confirmed genuine. All added to
  `docs/eval/genuine_print_typos.md`.

**`corrected` (91 rows, 4 pages)**: this bucket is the pipeline's own
conservative auto-correction (only fires on a run of >=2 consecutive
rows agreeing on the same day-shift, per `validate_performance_dates.py`'s
module docstring). Spot-verified `repertoire_1905-06_p028` (31 rows, the
largest single-page-season instance) directly: confirmed it's not a
fresh bug but the same defect as the already-fixed
`repertoire_1905-06_p027` (`23 Вторн.` -> really day 24) rippling
forward -- computed true weekdays directly (Jan 24 1906 = Tuesday,
matching `p027`'s existing fix; Jan 25 = Wednesday, but `p028` prints
"25 Четвергъ." = Thursday, one day ahead) and confirmed the whole
10-row run is internally consistent under a uniform +1 shift. Every row
within each of the 4 `corrected` pages shares one identical drift value
across every theater column (`repertoire_1890-91_pair020`: -1,
`repertoire_1892-93_pair014`: +4, `repertoire_1899-00_p027`: +3,
`repertoire_1905-06_p028`: +1) -- the self-consistency plus the
`p027`/`p028` cross-page corroboration gives high confidence in the
existing correction; not exhaustively scan-verified row by row.

Rebuilt full chain after the two `month_text` fixes: Musicians/Roster
byte-identical, `quality_flags.csv` unchanged (894/7 receipts flags).

## 2026-09-24 — Issue #80: dropped weekday word in date_text, two-page-spread seasons

```sql
-- sizing (via Python, not SQL): scanned every outputs/full_run/raw/repertoire_*_pair*.raw.json
-- and single-leaf two-page-spread p0NN file for a weekday-word stem in date_text
```

Result: 629 of 8092 two-page-spread sessions (7.8%) had no weekday word,
across 63 of 98 pages (3 fully affected, 60 partial), concentrated in
1892-93 (25.6%). Scan-verified on 5 pages first (all 5 confirmed: weekday
genuinely printed, not a format quirk -- corrected a wrong conclusion
from an earlier session, see known_issues.md issue #80's correction to
issue #78's addendum). Fixed via 4 parallel scan-verification batches;
629 -> 70 residual flags, 69 of which are the sizing script's own regex
missing valid short abbreviations, 1 genuinely illegible (binding
gutter, left as printed). Full write-up: known_issues.md issue #80.

```sql
SELECT date_confidence, COUNT(*) FROM analysis.event_entry_date_check GROUP BY 1 ORDER BY 2 DESC;
```

Result after rebuild: verified 22659 (97.7%, up from 96.6%),
intra_block_disagreement 391 (down from 662), corrected 91, unresolved
31, corrected_manual 9. Also fixed one pre-existing duplicate-key
collision surfaced along the way (repertoire_1891-92_pair012, two
Александринскій "29 Воскрес." sessions both `session: "unspecified"`
instead of morning/evening -- assigned from content). Musicians/Roster
byte-identical throughout.

## 2026-09-25 — Issue #81: truncated weekday word in date_text, single-page seasons

```sql
-- sizing (via Python, not SQL): scanned every outputs/full_run/raw/repertoire_*_p*.raw.json
-- for the 10 single-page seasons, checking date_text for a weekday-word stem
```

Result: 237 of 15092 single-page sessions (1.6%) had a truncated (not
fully dropped) weekday word, across 20 pages, concentrated in 1907-08
(14 of 20 pages). Scan-verified 2 pages first (`1903-04_p032`,
`1907-08_p006`), both confirmed genuine truncation. Fixed via 2
parallel batches; 237 -> 6 residual, both confirmed genuine period
print typos (not bugs) -- `1903-04_p010` (already documented) and
`1901-02_p002` (newly confirmed, added to genuine_print_typos.md).
Full write-up: known_issues.md issue #81.

```sql
SELECT date_confidence, COUNT(*) FROM analysis.event_entry_date_check GROUP BY 1 ORDER BY 2 DESC;
```

Result after rebuild: unchanged at verified 22659 (97.7%) -- this fix
didn't move date-correctness confidence (the existing short-form
weekday parser already handled truncated forms like "Вт." correctly),
it's a verbatim-completeness fix, not a correctness one. 0
duplicate-key collisions corpus-wide. Musicians/Roster byte-identical.

## 2026-09-25 — Checked issue #80's five follow-ups

Re-verified each against its scan directly. 4 of 5 resolved:
`1890-91_pair016` and `1893-94_pair016` both had the same phantom-
duplicate pattern (a prior date's content spuriously echoed onto the
next date, plus exact-duplicate redundant rows) -- 8 stray sessions
removed total. `1894-95_pair016` day 18 and `1892-93_pair002` days
26/27 reconfirmed correct as already applied (permanent photo-frame
scan limitations). `1897-98_pair016` turned out to be a session-field
labeling gap (morning/evening both stored as "unspecified"), not a
content mismatch -- fixed, 4 sessions. `1893-94_pair012` confirmed as
a real, much bigger cascading date shift (8+ consecutive dates) than
originally flagged -- NOT fixed, needs its own reconstruction pass.
Full detail: known_issues.md's addendum to issue #80.

```sql
SELECT date_confidence, COUNT(*) FROM analysis.event_entry_date_check GROUP BY 1 ORDER BY 2 DESC;
```

Result after rebuild: verified 22659 (97.8%), intra_block_disagreement
383 (down from 391), event_entry 23181->23173 (-8, exactly the removed
phantom sessions). 0 duplicate-key collisions corpus-wide.
Musicians/Roster byte-identical.

## 2026-09-25 — Reconstructed repertoire_1893-94_pair012 (issue #80 follow-up #4)

Full page reconstruction. Root cause turned out to be four independent
bugs, not one cascade: Александринскій entirely absent (all 20 dates);
Малый missing d3-11 and shifted -1 for d12-21; Большой/Маріинскій/
Михайловскій each independently duplicated d15 onto d16, cascading a
-1 shift through d21; all four present theaters' "22 Среда." was a
redundant wrong duplicate of true d21 (the odd "22 Декабря. Среда."
entry was the correct d22 all along). Rebuilt all 5 theaters' sessions
for the full 3-22 Декабря 1893 range from the scan, verified
column-by-column (title + receipts cross-checked against the scan for
every date), preserving 3 genuine morning/evening splits and 3
genuinely dark days. One OCR digit typo fixed (Большой's "210 р. 2
к." -> "310 р. 2 к.", confirmed via the clean duplicate that existed
before cleanup). Full detail: known_issues.md's addendum to issue #80.

```sql
SELECT date_confidence, COUNT(*) FROM analysis.event_entry_date_check GROUP BY 1 ORDER BY 2 DESC;
```

Result after rebuild: verified 22701 (97.8%, +42), intra_block_disagreement
368 (down from 383). event_entry 23173->23200 (+27). 0 duplicate-key
collisions corpus-wide. Musicians/Roster byte-identical.

## 2026-09-25 — Re-examined the two "unresolved content gap" pages more precisely

RG pushed back twice on the standing conclusion for `1905-06_p005`/
`p008` ("do a better scan"): first asking whether neighboring renders
were really checked (re-verified directly, yes -- both continuation
pages open cleanly at their own next date with no orphaned content),
then pointing out there's genuine blank margin with the folio number
fully visible below both flagged rows, meaning the photograph isn't
truncated at all. Re-examined each row's printed border structure and
compared against a confirmed genuine УТРО./ВЕЧЕРЪ. split elsewhere on
`p005` (day 25's taller two-part box). Both flagged rows' column
lines run down past the receipts figure and simply stop -- no closing
border, no second sub-cell ever drawn. Conclusion revised: this is a
genuine period PRINTING limitation (the compositor ran out of page
space mid-row), not a scanning gap -- a better scan would recover
nothing, since the original book itself never typeset the evening
entry. No data change (the existing "morning"-labeled capture is
already verbatim-correct); known_issues.md's write-up corrected to
stop suggesting re-scanning as a path forward.

## 2026-09-25 — Two-page-spread full sweep: rebuild + gold-eval + quality-flag delta

```
pipeline/parse_and_validate.py --manifest outputs/full_run/manifest.csv --raw-dir outputs/full_run/raw --out-dir outputs/full_run/parsed --page-headers outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv
pipeline/quality_checks.py --parsed-dir outputs/full_run/parsed --out outputs/full_run/quality_flags.csv
pipeline/build_duckdb.py --parsed-dir outputs/full_run/parsed --manifest outputs/full_run/manifest.csv --db outputs/full_run/imperial_theaters.duckdb
pipeline/validate_performance_dates.py --db outputs/full_run/imperial_theaters.duckdb
pipeline/build_entities.py --db outputs/full_run/imperial_theaters.duckdb
pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb
pipeline/build_datasette.py --db outputs/full_run/imperial_theaters.duckdb --out outputs/full_run/research_dataset.sqlite
pipeline/eval_against_gold.py --parsed-dir outputs/full_run/parsed --gold-dir docs/eval/gold --out outputs/full_run/eval_report_spreadsweep_2026-09-25.txt --run-id spreadsweep_2026-09-25
```

Result: event_entry 23200 -> 24078 (+878). validate_performance_dates verified 97.8% -> 98.1%.
quality_flags.csv: 896 immediately post-sweep (894 pre-existing Musicians/Roster baseline + 2 new
`duplicate_event_key` on repertoire_1892-93_pair018) -> fixed the 2 flags by splitting a combined
"20 Субб. Воскрес." date label into its two real calendar days per the page's own scan -> re-ran
quality_checks.py, back to 894 (0 genuine Repertoire flags). Gold-eval: roster 82.1%, repertoire
96.1% (unchanged -- no gold Repertoire page is two-page-spread format), grand 87.2%. entities
layer confirmed stable (2900 live people, 0 new merges) -- Musicians/Roster isolation held. Full
narrative: docs/eval/run_history.csv row `full_sweep_twopagespread_2026-09-25`.

## 2026-09-25 — Filled the second dark-day placeholder gap on repertoire_1892-93_pair018

Fixed the small follow-up flagged during the pair018 duplicate_event_key fix earlier today:
Маріинскій/Большой/Малый each had only one `is_dark` entry for the combined "20 Субб./21
Воскрес." date, though the scan shows dash placeholders on both days for all three. Added
the missing "21 Воскрес." dark entry for each theater (+3 sessions). Rebuilt full chain:
event_entry 24078->24081, verified 98.1%->98.1% (unchanged), quality_flags.csv unchanged
(894/7, 0 genuine Repertoire flags).

## 2026-09-25 — printed_page_number build-out: assembly and backfill

```
pipeline/parse_and_validate.py ... --printed-page-numbers outputs/full_run/printed_page_numbers/printed_page_numbers.csv
pipeline/quality_checks.py --parsed-dir outputs/full_run/parsed --out outputs/full_run/quality_flags.csv
pipeline/build_duckdb.py ... (full rebuild)
```

Result: 23422/24081 Repertoire event_entry rows (97.3%) now carry a scan-verified
printed_page_number. Two-page-spread seasons: 90 of 98 page_ids backfilled from 97
manually-read render folios (dispatched as 6 parallel batches, cross-checked against
existing `split_page_numbers_final.csv`/`split_extents.csv` candidates rather than
trusting them blindly -- several VLM misreads caught and corrected). All 85 split-page
top/bottom pairs came out perfectly consecutive (n, n+1), a strong internal-consistency
signal. New `printed_page_number_out_of_sequence` quality check: 0 flags corpus-wide.
4/4 available gold cross-checks (docs/eval/gold/source_pages.csv) matched exactly.
8 spread page_ids deferred, not guessed: repertoire_1892-93_pair014 and
repertoire_1890-91_pair010 (multi-render, need one more targeted render read each);
repertoire_1890-91_p015/_p023, repertoire_1891-92_p003, repertoire_1892-93_pair024,
repertoire_1895-96_p012, repertoire_1897-98_pair020 (cutover date's day-of-month not
found in that page's actual date_undate list -- needs individual resolution, not a
formula fallback).

Single-page seasons: all 422 page_ids backfilled by formula after a 30-read spot-check
(3 per season) found every one of the 10 seasons holds a constant
printed_page = source_page_index + offset (offsets: 1898-99 through 1903-04 = +2,
1904-05 = +90, 1905-06 = +84, 1906-07 = +84, 1907-08 = +76). No escalation to full
per-season reads was needed -- all 10 seasons passed the 3-point consistency check.
validate_performance_dates.py unchanged (98.1%, expected -- pure additive column).
Full narrative: docs/eval/known_issues.md issue #83.

## 2026-09-25 — printed_page_number: closed the last 8 gaps, 100% fill

Followed up on RG's "take a closer look" request. 6 of 8 resolved by cross-referencing
a sibling page_id drawing from the same render (already successfully backfilled) --
no additional reads needed, just correct date-boundary logic:
repertoire_1890-91_p015 (=15, entirely after render p006's cutover),
repertoire_1890-91_p023 (=23, entirely after render p010's cutover),
repertoire_1891-92_p003 (=3, entirely after render p000's cutover),
repertoire_1895-96_p012 (=9, entirely after render p003's cutover),
repertoire_1892-93_pair024 (split 24/25 at the actual date-boundary around a dark/
uncaptured May 1st), repertoire_1897-98_pair020 (split 20/21 at the actual date-
boundary around a dark/uncaptured March 2nd).

The last 2 needed a dispatched agent to re-verify the render mapping directly against
scan content (not trust prior claims): repertoire_1892-93_pair014 turned out to span
THREE printed pages, not two (14: Dec27-Jan6, 15: Jan7-16, 16: Jan17-26 -- the render
_006.jpg is itself a normal two-page-spread render, on top of already needing _007.jpg
for the Jan17-26 tail). repertoire_1890-91_pair010's "multi-render" status was itself
wrong -- turned out to be a normal single-render page (_004.jpg, folios 10/11); the
earlier "two renders" read was based on stale leftover `_source` tags from before a
2026-09-25 correction, not a real second physical source.

Result: 24081/24081 Repertoire event_entry rows (100.00%) now carry a printed_page_number.
0 sequence-consistency flags. validate_performance_dates unchanged (98.1%). Full chain
rebuilt clean through research.event/research_dataset.sqlite.

## 2026-09-25 — Auditing the not_captured completeness gap, starting with 1894-95

```sql
select event_status, count(*) from analysis.event_entry group by 1 order by 2 desc;
select season, count(*) from analysis.event_entry where event_status='not_captured' group by 1 order by 2 desc;
select page_id, count(*) from analysis.event_entry where event_status='not_captured' and season='1894-95' group by 1 order by 2 desc;
select theater, count(*) from analysis.event_entry where event_status='not_captured' and season='1894-95' group by 1 order by 2 desc;
select distinct date_undate, date_text from raw.event_entry where page_id='repertoire_1894-95_pair006' order by date_undate;
select page_id, min(date_undate), max(date_undate), count(distinct date_undate) from raw.event_entry where season='1894-95' and page_id like 'repertoire_%' group by 1 order by 2;
```

Result: not_captured totals 3032 corpus-wide; 1894-95 is an outlier at 520 (vs.
under-270 everywhere else, 1905-06/1906-07 near-zero, 1907-08 zero). 365 of the
520 concentrated on repertoire_1894-95_pair006 alone, evenly split across all 5
theaters (~100 each) -- the signature of "no theater has anything for these
dates" rather than a missing-column bug. That page's actual content jumps from
19 Окт 1894 to 1 Янв 1895 (73-day gap). Confirmed via direct PDF page-count check
(pymupdf) that ForUpload_1894-95_Repertoire.pdf has exactly 9 pages against every
comparable season's 12-13 -- a genuine source-material shortfall, not an
extraction bug; searched the repo for any alternate/misfiled 1894-95 source,
found none. Documented as docs/eval/known_issues.md issue #84. Remaining ~155
scattered not_captured rows in 1894-95's other 8 pages, and the rest of the
corpus's not_captured totals, not triaged this pass.

## 2026-09-25 — Correcting the 1894-95 gap: printed page numbers, not scan pages

RG pushed back on the issue #84 conclusion: "do the page numbers show a gap?
It's possible that the theaters were literally closed during that period."

```sql
select page_id, min(date_undate), max(date_undate),
       min(printed_page_number::int), max(printed_page_number::int)
from raw.event_entry
where season='1894-95' and page_id like 'repertoire_%'
group by 1 order by min(date_undate);
```

Result: printed page numbers run perfectly consecutively, 2-3, 4-5, 6-7, 8-9, ...
18, with zero gap -- pair006 (pages 6-7) just covers an unusually wide 91-day
span instead of the normal ~20 days. Confirmed directly against the scan
(ForUpload_1894-95_Repertoire_002.jpg): the printed date column runs day-by-day
to "19 Среда." (19 Октября), then the very next row is the "ЯНВАРЬ" header and
"1 Воскр." -- no separator, no annotation, just a direct jump in the original
print. Coincides exactly with Tsar Alexander III's death (20 Октября 1894,
Julian) and the Imperial theaters' traditional mourning closure. This reverses
issue #84's original conclusion (PDF-page-count comparison, which only checks
whether rendering skipped a page, not whether the print itself is continuous) --
see that issue's own correction addendum in known_issues.md.

## 2026-09-25 — Corpus-wide printed_page_number continuity sweep (issue #85)

```sql
-- adjacent page-pair continuity check, per season
with pages as (
  select season, page_id, min(printed_page_number::int) lo, max(printed_page_number::int) hi
  from raw.event_entry where page_id like 'repertoire_%' and printed_page_number != ''
  group by 1,2
),
ordered as (select *, lag(hi) over (partition by season order by lo) as prev_hi from pages)
select season, page_id, lo, hi, prev_hi, lo - prev_hi as gap
from ordered where prev_hi is not null and lo - prev_hi != 1
order by season, lo;
```

Result: found 1 already-explained gap (1890-91), 1 new real gap (1892-93 pages 12-13),
and several false positives from single-render-final-page_ids sharing a page number
with a sibling (expected, not a bug). Cross-referenced against a corpus-wide render-file
usage check (every render file on disk vs. every render actually cited by a final
page_id) to find 1892-93's render_005.jpg and 1895-96's render_012.jpg sitting
completely unused -- both fully transcribed as new pages (repertoire_1892-93_pair012,
108 sessions; repertoire_1895-96_p026, 50 sessions). Also found, as a side effect,
35 duplicate sessions shared between repertoire_1892-93_pair014 and _pair016 (verified
by direct content match, not just date/theater) -- removed from pair014. event_entry
24081->24204 net. printed_page_number fill stayed 100.00%. quality_flags.csv unchanged
(894/7). validate_performance_dates.py unchanged (98.1%). Full narrative:
docs/eval/known_issues.md issue #85.

## 2026-09-25 — Added and ran the new cross_page_duplicate_event check

New pipeline/quality_checks.py check (check_repertoire_cross_page_duplicate),
flag cross_page_duplicate_event: flags any (theater, date_undate, time_of_day)
claimed by more than one page_id. First run found 18 flags: repertoire_1895-96_p012
was a pure 100%-redundant duplicate of part of pair008 (deleted outright, verified
byte-identical field-by-field first); repertoire_1904-05_p011 had 3 sessions
misdated to 23 Ноября 1904, entirely outside that page's own declared date range,
duplicating (with disagreeing content) what p015 already correctly owns (deleted
the 3 stray sessions). Re-ran after both fixes: 0 cross_page_duplicate_event flags.
event_entry 24204->24186. Full narrative: docs/eval/known_issues.md issue #86.

## 2026-09-25 — pair012 verification: found+fixed one wrongly-normalized figure

Checked the 5 low-confidence spots flagged by the pair012 reconstruction agent
directly against the scan. 4 of 5 (3 fold-blurred receipts figures near the
page-13 binding gutter, 1 ink blot correctly not treated as a footnote marker)
confirmed as genuinely at the edge of scan legibility -- added to the Binding
Fold Log candidates rather than resolved further. 1 of 5 was a real, confirmable
finding: Михайловскій, 8 Вторн., receipts printed "1225 q. 27 к." -- the
reconstruction agent had normalized this to "р." Zoomed to max resolution,
shared the crop directly with RG, who confirmed the glyph is genuinely a "q" --
a real compositor typo, not a misread, understood as the rubles marker by
context (position + corpus-wide figure shape) rather than visual resemblance.
Restored receipts_text to the verbatim "1225 q. 27 к." and widened
_RUBLES_MARKER_RE (pipeline/schemas/repertoire.py) to parse "q"/"Q" as a
rubles marker so receipts_rubles/receipts_kopecks still compute correctly --
RG's explicit choice, the one exception to this corpus's genuine-print-typo
receipts figures staying permanently unparsed by design. Documented in
docs/eval/genuine_print_typos.md.

## 2026-09-25 — Correction: "q" stays unparsed at the raw layer, not widened into _RUBLES_MARKER_RE

Supersedes the previous entry's regex-widening approach. RG's actual instruction:
leave "q." unparsed at this layer, same treatment as this corpus's other genuine
rubles-marker typos (к./и./г.) -- receipts_rubles/receipts_kopecks stay empty,
joins receipts_parse_failed (7->8). A corrected numeric value belongs in the
research layer (SQL-derived), not baked into raw-tier parsing -- not built yet.
Reverted _RUBLES_MARKER_RE, updated the raw JSON's _fix_note and
docs/eval/genuine_print_typos.md to match. Committed 9034f55.

## 2026-09-25 — Full not_captured audit (issue #87)

```sql
-- contiguous per-theater block extraction + Easter/Clean-Monday/mid-Lent/Christmas
-- calendar matching (see known_issues.md issue #87 for the Python logic)
select page_id, theater, date_undate from analysis.event_entry where event_status='not_captured';

-- disproportionate-theater check
select page_id, theater, count(*) n from analysis.event_entry where event_status='not_captured' group by 1,2;
```

Result: every contiguous block >=3 days matched Julian Easter, Clean Monday, mid-Lent,
or Christmas/New Year, or sat at a genuine page-boundary edge -- 5 independent Easter-year
matches landed exactly on the computed date. Spot-verified one Clean-Monday match directly
against the scan (repertoire_1900-01_p026: print jumps straight from 11 Февраля to 19
Февраля with zero rows between, Clean Monday 1901 = 12 Февраля). Disproportionate-theater
check found 8 real missing-column bugs (2 already found via other means this session, 6 new);
dispatched fixes for the 7 outstanding -- 5 confirmed and fixed (+66 sessions total), 2 were
NOT bugs after scan verification (1906-07_p037 is structurally Moscow-only, Petersburg
theaters live on sibling page p036 which is already correct; 1890-91_p012's "missing" theater
is genuinely dark, matching its siblings). Re-ran the disproportionate check after fixes: 0
pages flagged. event_entry 24186->24266. not_captured 3000->2935. Full narrative:
docs/eval/known_issues.md issue #87.

## 2026-09-25 — excerpt-linking triage: "2-я и 3-я карт. бал." source rows

```sql
select p.event_id, e.page_id, e.date_text, e.theater
from raw.event_entry_performance p join raw.event_entry e on p.event_id=e.event_id
where p.performance_title = '2-я и 3-я карт. бал.'
```

Result: 4 rows, all Маріинскій, 1895-96 season (`pair004` x2, `pair008`,
`pair010`) — led to inspecting the raw JSON directly and finding this is
always the 2nd item of a 3-work bill, a different bug class than
excerpt-linking (see known_issues.md issue #88).

## 2026-09-25 — "Люcія ди Ламермуръ" homoglyph check

```sql
select work_id, canonical_title, canonical_genre, appearance_count
from entities.work where canonical_title ilike '%амермур%'
```

Result: 7 works, confirming a real standalone "Лючія ди Ламермуръ" (10
appearances) exists; the unlinked excerpt used Latin "c" (U+0063) where
Cyrillic "ч" (U+0447) belonged — confirmed via `ord()` comparison, then
via the source event:

```sql
select p.event_id, e.page_id, e.date_text, e.theater
from raw.event_entry_performance p join raw.event_entry e on p.event_id=e.event_id
where p.performance_title = '1-я карт. 3-го д. оп. Люcія ди Ламермуръ'
```

Result: 1 row, `repertoire_1895-96_p026__s039` — my own manual-transcription
typo (page reconstructed earlier this session, issue #85). Verified against
`ForUpload_1895-96_Repertoire_012.jpg` directly, fixed the raw JSON, re-ran
`parse_and_validate.py` + `build_duckdb.py` + `build_entities.py`.

## 2026-09-25 — excerpt-linking final diagnostic (post-fixes)

Standalone Python script importing `_EXCERPT_PREFIX_RE`, `_title_key`,
`_fold_genre`, `_GENITIVE_GENRE_TO_ABBREV` from `pipeline/build_entities.py`,
replaying the matching logic against a fresh `select work_id, canonical_title,
canonical_genre, appearance_count from entities.work` pull.

Result: 21 unmatched (34 appearances) of 159 excerpt-shaped titles, up from
138 matched (was 96/47 at session start, 137/22 before the Люcія fix). Full
categorization in known_issues.md issue #88 and docs/work_normalization.md.

## 2026-09-25 — printed_page_number fill check (confirming plan file staleness)

```sql
select count(*) total, count(printed_page_number) filled from raw.event_entry
```

Result: (24266, 0) — column entirely null. Revealed a real regression: an
earlier parse_and_validate.py re-run today (for issue #88's typo fix)
omitted --printed-page-numbers, silently wiping the whole column. Fixed
by re-running with the flag restored; re-checked:

```sql
select count(*) total, count(printed_page_number) filled from raw.event_entry
```

Result: (24266, 23861) — 98.3%, matching pre-regression state (confirmed
the wipe-and-restore was a round trip, not new data loss).

```sql
select page_id, count(*) from raw.event_entry where printed_page_number is null group by page_id order by count(*) desc
```

Result: 11 page_ids, 405 rows — 2 are brand-new pages (issue #85,
never covered by the reference CSV), 9 are pre-existing pages that grew
new sessions after issue #87's missing-column fixes, outside the
originally-recorded date range. See known_issues.md issue #83 addendum.

```sql
select count(*) total, count(printed_page_number) filled from raw.event_entry where page_id='repertoire_1894-95_pair004'
```

Result: (100, 55) — confirms partial fill (pre-existing rows still
resolve; only newly-added rows are null), not a page-level wipe.

## 2026-09-26 — printed_page_number residual gap closure (issue #83 addendum)

```sql
select page_id, count(*), min(date_undate), max(date_undate)
from raw.event_entry where printed_page_number is null group by page_id
```

Result: 11 page_ids, 405 rows -- for each of the 9 pre-existing pages,
confirmed the null-date min/max sat strictly outside the existing
reference-CSV range on one side (safe outer-boundary extension, no
scan re-read needed). Full detail in known_issues.md issue #83 addendum.

```sql
select distinct date_undate from raw.event_entry
where page_id='repertoire_1892-93_pair018' and printed_page_number is null
```

Result: single day, 1893-02-21 -- matched an already-existing source
note explicitly citing "bottom=21 Февраля margin header", confirming
which side of the page split it belongs on without guessing.

```sql
select distinct date_undate from raw.event_entry
where page_id='repertoire_1892-93_pair014' order by date_undate
```

Result: 1892-12-27 through 1893-01-16 only -- confirmed 3 stale rows in
printed_page_numbers_all.csv (folios 11-13, dated 1892-12-01 to
1892-12-26) were dead cruft from before repertoire_1892-93_pair012 was
discovered as a genuinely missing page; removed.

```sql
select distinct date_undate from raw.event_entry
where page_id='repertoire_1895-96_p026' order by date_undate
```

Result: 1896-05-15 to 1896-05-26 (10 rows) -- matched an existing
reference row filed under the stale page_id 'repertoire_1895-96_p012'
exactly (same date range, folio 26); re-verified folio 26 directly
against ForUpload_1895-96_Repertoire_012.jpg before renaming the row.

```sql
select count(*) total, count(printed_page_number) filled from raw.event_entry
```

Result: (24266, 24266) -- 100% fill restored after all fixes applied
and the full raw/analysis chain rebuilt.

## 2026-09-26 — receipts_total_kopecks NULL-propagation finding, verified against RG's caution

RG: "check this, but realize that some seasons don't report box office
receipts and some performances are free" -- verified the finding doesn't
conflate those cases with the actual bug.

```sql
select count(*) from raw.event_entry
where receipts_rubles is not null and receipts_kopecks is null
```
Result: 735.

```sql
select count(*) from raw.event_entry
where receipts_rubles is not null and receipts_kopecks is null and receipts_rubles != '-'
```
Result: 720 -- the other 15 are the separately-found dash-placeholder
bug ("— р. — к.", both sides blank), already correctly excluded from any
total since TRY_CAST('-') is NULL regardless of the kopecks-side fix.

```sql
select count(*) from raw.event_entry
where receipts_rubles is not null and receipts_kopecks is null and receipts_rubles != '-'
and try_cast(receipts_rubles as integer) is null
```
Result: 0 -- confirms all 720 have a genuinely valid numeric rubles figure.

```sql
select season, count(*) total, count(receipts_text) has_text,
       round(100.0*count(receipts_text)/count(*),1) pct
from raw.event_entry group by 1 order by 1
```
Result: 1890-91 and 1891-92 both 0.0% (confirmed, matches the
already-documented issue #70 finding -- a genuine season-wide absence,
not a parsing gap) -- these rows have receipts_rubles NULL too, so
they're structurally outside the 720-row population; unaffected by
the proposed fix.

```sql
select event_id, annotation, receipts_rubles from raw.event_entry
where (annotation ilike '%безплатн%' or annotation ilike '%гратис%' or annotation ilike '%даров%')
and receipts_rubles is not null
```
Result: 59 rows -- all "free performance for [audience group]" cases
(e.g. free tickets for students) that still carry a real recorded
receipts figure (presumably subsidized/institutional accounting, not a
contradiction) -- none are placeholder values, confirms the 720-row
population is genuinely clean.

Conclusion: fix is safe -- COALESCE only ever changes a total for a row
that already has a real, valid rubles figure; a genuinely-blank or
free-with-no-receipts row's rubles stays NULL/non-numeric regardless,
so TRY_CAST(...)*100 stays NULL and the COALESCE on the kopecks side
never fires for it.

## 2026-09-26 — receipts_total_kopecks fix applied, verified

```sql
select count(receipts_total_kopecks) from analysis.event_entry
```
Result: 15784 (up from 15064 pre-fix, +720 -- exactly the population
verified above). Spot-checked repertoire_1898-99_p000__s006 ("239 р. —
к.") now correctly totals 23900; a dash-placeholder row
(repertoire_1905-06_p018__s031, "— p. — к.") correctly stays NULL;
quality_flags.csv unchanged at 895; entities.person/work unchanged
(4359/3498).

## 2026-09-26 — Михайловскій French genre corruption sweep (issue #90)

RG: "Mikhailovsky usually has french titles and genre markings. so if
there's non-French letters there, we should check those."

```sql
select p.event_id, e.page_id, e.date_text, e.theater, p.performance_title, p.genre
from raw.event_entry_performance p join raw.event_entry e on p.event_id=e.event_id
where e.theater like '%Михайлов%'
```
Result: 6088 rows total, of which 2128 contain any Cyrillic character in
title or genre -- too broad (Михайловскій also hosted genuine Russian
productions). Narrowed to: title has ZERO Cyrillic characters (a real
French title) AND genre has at least one Cyrillic character -- 332 rows,
27 distinct corrupted genre strings, 49 pages. Every distinct value
checked against its scan (8+ pages directly verified at zoom, several
more confirmed via title-inline text already spelling out the genre in
French) before building the fix mapping -- full detail and mapping table
in known_issues.md issue #90.

Post-fix re-query (same query, after applying the fix and rebuilding):
0 remaining rows. `entities.work`: 3498 -> 3435 (-63, spurious
genre-split collapse). `entities.work_genre_candidate`: 354 -> 304
groups. `quality_flags.csv` unchanged (895). Musicians/Roster isolation
and issue #88's excerpt-linking (138/21) both confirmed unchanged.

## 2026-09-26 — do entities.person surnames corroborate Season Reviews name spellings?

RG's idea: reviews and the tabular roster describe the same people, so
`entities.person` is an independent check on review spellings.

```sql
SELECT count(*), count(DISTINCT canonical_family_name) FROM research.person;
SELECT DISTINCT canonical_family_name FROM research.person
 WHERE canonical_family_name IS NOT NULL;
```

Result: 2,894 people, 1,692 distinct family names.

Cross-checked against the 16 spellings flagged by `pipeline/name_variants.py`
on the 200-page review pilot: 10 had the dominant spelling present in
entities and the minority absent (variant suspect); 1 (`Тихоміровъ` /
`Тихомировъ`) had BOTH present, correctly identifying the case gold shows is
genuine print variation; 5 were not personal names at all.

```sql
SELECT canonical_family_name, count(*) n, min(first_attested_season),
       max(last_attested_season)
  FROM research.person WHERE canonical_family_name = ? GROUP BY 1;
```

Result, for the near-1:1 pairs frequency alone cannot resolve:

| spelling | people in entities | seasons |
|---|---|---|
| Легатъ / Легать | 4 / **8** | both 1890-91..1907-08 |
| Ѳедоровъ / Федоровъ | **11** / 3 | 1890-91..1907-08 / **1904-05..1905-06 only** |
| Мендесъ / Мендесь | 3 / **absent** | |
| Галатъ / Галать | **absent** / 2 | |
| Аслинъ / Аслинь | 3 / **absent** | |
| Кустереръ / Кустерерь | 1 / **absent** | |
| Валининъ / Волининъ | 1 / 2 | **1901-02 only** / 1900-01..1907-08 |
| Корсаръ / Корсарь | absent / absent | (a work, not a person) |

**Key negative finding: entities is NOT a clean authority on ъ/ь.** It holds
`Легать` for 8 people against `Легатъ` for 4, and `Галать` but not `Галатъ`
— yet RG ruled `Легатъ` and `Галатъ` from the scans. The roster layer was
extracted by the same kind of model and carries the same systematic ъ->ь
slip, so agreement between the two sources is not independent on that axis.

Where entities holds one spelling and not the other it is good
corroboration (`Мендесъ`, `Аслинъ`, `Кустереръ` — all matching RG's or
Claude's scan readings). The season range is a useful extra signal:
`Валининъ` appears only in 1901-02 and `Волининъ` from 1900-01 onward,
exactly matching what the scans show — independent confirmation from a
different extraction path.

## 2026-09-26 — closing all 3 field-audit follow-ups (issue #91)

```sql
select receipts_rubles, count(*) from raw.event_entry
where receipts_rubles = '-'
```
Result: 15 rows before the _parse_receipts fix, 0 after.

```sql
select performance_title from raw.event_entry_performance
-- Latin-i/Cyrillic-і mixed-script scan, same method as issue #89
```
Result: 49 instances confirmed still present (48 title + 1 genre) --
deliberately left as a worklist, not fixed, per the pre-reform
orthography rule.

```sql
select p.event_id, e.page_id, e.date_text, e.theater, p.performance_title, p.genre
from raw.event_entry_performance p join raw.event_entry e on p.event_id=e.event_id
where e.theater not like '%Михайлов%'
```
Result (filtered to pure-Latin-title + Cyrillic-genre, same isolation
method as issue #90 minus the theater filter): 65 candidates, 49 pages.
Each distinct (title, genre) pair individually scan-verified (13 page
reads) before deciding fix vs. leave-alone -- full detail and per-page
citations in known_issues.md issue #91. 10 confirmed genuinely Cyrillic
(left alone), 55 confirmed corrupted (fixed), plus 1 genuine
cross-theater content swap found and fixed separately
(repertoire_1903-04_p026, "17 Вторн.").

Post-fix re-query: 10 remaining rows, all 10 the confirmed-legitimate
set. `entities.work`: 3435 -> 3426 (-9). `event_entry_performance`:
26154 -> 26155 (+1, the p026 fix). `quality_flags.csv` unchanged (895).

## 2026-09-26 — closing the last 2 field-audit items (issue #92)

```sql
select performance_order, performance_title from raw.event_entry_performance
where event_id = ?
```
Used to resolve each of the 4 "2-я и 3-я карт. бал." rows to whichever
performance immediately precedes it in the same event (performance_order
- 1), matching by title then disambiguating by genre when the preceding
title itself splits into >1 real genre. All 4 confirmed correct against
entities.work_link (2 -> Коппелія/бал., 2 -> Лебединое озеро/бал.).

```sql
-- same mixed-script detection query used throughout issues #89-91,
-- performance_title and genre, corpus-wide
```
Result: 49 -> 0 after applying the targeted per-string codepoint fix.
One self-inflicted regression caught by re-running this same query
post-fix (49 -> 1, not 0): "Царь Іоаннъ IV"'s Roman numeral "IV" had
been partially converted to "ІV" -- fixed by hand, confirmed against
the same title's other 2 untouched occurrences in the same file.

Final re-verification: 0 remaining mixed-script instances,
quality_flags.csv unchanged (895), entities.work 3398->3397, Musicians/
Roster isolation and excerpt-linking counts unchanged.

## 2026-09-26 — new season 1908-09 Repertoire: extraction, sweep, integration test (issue #93)

All against scratch databases under `outputs/repertoire_1908-09/`
(`scratch.duckdb` = 1908-09 alone; `integration/` = 18 existing seasons
+ 1908-09; `control/` = the 18 existing seasons rebuilt with the same
current code). `outputs/full_run` was only read, never written.

```sql
-- non-verified dates, 1908-09 alone
select e.page_id, e.theater, e.date_text, e.month_text, e.year_text, e.date_undate,
       d.date_confidence, d.corrected_date_undate, d.note
from analysis.event_entry_date_check d join raw.event_entry e using(event_id)
where d.date_confidence <> 'verified';
```
26 rows: 20 `no_date` on `p003` (unparsed "8 сен тября." header) and 6
`intra_block_disagreement` on `p022` ("4 Пятница." print typo). After the
`_MANUAL_DATE_OVERRIDES` entry: 3 `corrected_manual`, 3 residual.
Verified 1642/1668 (98.4%).

```sql
-- per table, pre-existing rows changed by adding 1908-09 (control vs integration)
select count(*) from (select * from control.<t> where <not 1908-09>
                      except select * from integration.<t> where <not 1908-09>);
```
0 for raw.event_entry, analysis.event_entry, research.event,
research.person, research.person_appearance, entities.person.
research.work: 122 rows differ (appearance_count), 2 canonical-genre
flips (pièce. -> pièce), 0 work_ids lost, 119 new works.

```sql
select count(*), sum(receipts_total_kopecks)/100 from analysis.event_entry
where season = '1908-09' and event_status = 'performed';
select event_status, count(*) from analysis.event_entry where season = '1908-09' group by 1;
```
1053 performed events, 1,784,570.90 rubles summed receipts; 615
no_performance, 23 not_captured (20 = `p003` phantoms, 3 = `p022`).

```sql
select count(*) from entities.work; select count(*) from research.work;
select count(*) from research.performance; select sum(receipts_total_kopecks) from research.event;
```
Production full_run: 3397 / 3498 / 26153 / 2,399,535,656. Control
(same parsed/, current code): 3397 / 3397 / 26154 / 2,555,499,136 --
production's research layer is stale relative to issues #89-92.

## 2026-09-26 — p003 research-layer date fix + phantom-gap rule (issue #93)

```sql
-- per scratch db, research.event before vs after build_research_model.py's new rule
select season, count(*) from before.research.event
where event_id not in (select event_id from after.research.event) group by 1;
select b.season, b.date_confidence, a.date_confidence, count(*)
from before.research.event b join after.research.event a using(event_id)
where b.date is distinct from a.date or b.date_confidence is distinct from a.date_confidence
group by all;
```
Control (18 seasons): 6 placeholders dropped (1904-05 x3, 1905-06 x3),
0 other rows changed. Integration: those 6 + 23 in 1908-09 dropped; 20
1908-09 rows no_date -> corrected_manual; research.performance 27449
unchanged. The 6 older ones checked individually: each sits beside a
real row dated by an existing `_MANUAL_DATE_OVERRIDES` entry
(1904-05_p014 "28 Понед." -> 1904-11-29; 1905-06_p036 "16 Среда." ->
1906-03-15).

## 2026-09-26 — excerpt-linker extension (issue #93)

```sql
-- integration build, entities.work before vs after the new prefix/suffix patterns
select a.canonical_title, p.canonical_title as parent, a.excerpt_note
from after.entities.work a left join before.entities.work b using(work_id)
left join after.entities.work p on p.work_id = a.excerpt_of_work_id
where a.excerpt_of_work_id is distinct from b.excerpt_of_work_id;
```
4 new links, 0 lost; entities.work 3515 -> 3515; entities.work_link 0 rows
changed. Linked total 139 -> 143.

```sql
select p.event_id, p.performance_order, p.performance_title, p.genre from raw.event_entry_performance p
where p.performance_title ilike 'Отрывок%';
```
24 rows: every bare "Отрывокъ" is Gogol's scene, billed with his other
scenes or after "Бѣдность—не порокъ" -- not an excerpt/continuation.

## 2026-09-26 — how much does the season narrow a surname to one person, and are composers in the database?

Both for scoping the Season Reviews mention-linking work (RG: link review
mentions to entities; match the review's season to the entry's year; and
begin tracking people not in the database, especially composers).

```sql
SELECT person_id, canonical_family_name, ordinal_suffix,
       first_attested_season, last_attested_season
  FROM research.person WHERE canonical_family_name IS NOT NULL;
```

Result: on 406 surname mentions across the 11 gold review pages that hit a
known entity, candidates narrow as follows.

| filter | ambiguous (>1 person) | resolved to exactly 1 |
|---|---|---|
| surname only | 322 (79.3%) | 84 (20.7%) |
| + season overlap | 172 (42.4%) | 234 (57.6%) |
| + season + ordinal | 93 (22.9%) | 313 (77.1%) |

**But 63 mentions (15.5%) have ZERO candidates left after season+ordinal.**
A person named in a review need not be on that season's roster (guests,
roster gaps), and the review's ordinal need not match the one recorded in
entities. So season and ordinal must RANK candidates, not gate them — a hard
filter silently discards one mention in six.

```sql
DESCRIBE research.work;
SELECT count(*) FROM research.person WHERE canonical_family_name ILIKE '%<name>%';
```

Result: `research.work` has **no composer column at all** (work_id,
canonical_title, canonical_genre, appearance_count, excerpt_of_work_id,
excerpt_note). And composers are almost absent from `research.person` —
Чайковск 0, Минкус 0, Бларамберг 0; Глазунов 1, Дриго 1, Вальц 1, Пуни 3,
and those are people who appear on a ROSTER (as conductors/staff), not
composer records.

**Tracking composers is therefore new construction, not linking.** There is
no composer entity population to link to.

## 2026-09-26 — genre-field-excerpt bug found and fixed (issue #94)

```sql
-- genre field itself matching an act/scene/tableau marker pattern
select p.event_id, e.page_id, e.date_text, e.theater, p.performance_title, p.genre
from raw.event_entry_performance p join raw.event_entry e on p.event_id=e.event_id
where p.genre is not null
```
Result (filtered in Python against a marker regex): 7 instances across
4 pages, all confirmed against scans -- see known_issues.md issue #94
for the full table and per-page citations.

Corpus-wide regression check on the `_ORDINAL_MARKER_UNIT` bare-ordinal
regex extension (every distinct `performance_title`, old regex vs. new):
0 new false positives, 11 genuinely correct excerpt titles newly caught
(bonus fix, unrelated to this issue's own field-splitting bug but the
same underlying regex gap).

Post-fix: `entities.work` excerpt links 138 -> 159. Musicians/Roster
isolation (2900/23) and quality_flags.csv (895) both unchanged.

## 2026-09-26 — Русалка "drama" excerpts: which theaters?

```sql
select p.event_id, e.page_id, e.date_text, e.season, e.city, e.theater, p.performance_title, p.genre
from raw.event_entry_performance p join raw.event_entry e on p.event_id=e.event_id
where p.performance_title in ('1-й актъ драмы Русалка.', '1-е д. др. Русалка', 'Русалка')
   or (p.performance_title = 'Русалка' and p.genre = '1-я сцена')
order by e.season, e.date_text
```

Result: the two "drama"-genre excerpts are BOTH at Михайловскій театръ
(1890-91 and 1893-94), not Малый where the Pushkin-gala "1-я сцена" row
sits (Moscow, 1898-99, a different theater and season entirely). All
other ~140 rows are the standard Dargomyzhsky opera at Большой/
Маріинскій. This complicates the "Pushkin's own drama, cited at a
literary gala" theory floated earlier -- Михайловскій mostly hosted the
French repertoire, so a "drama" excerpt there is at least as plausibly a
foreign-language dramatic adaptation as it is Pushkin's Russian text.

## 2026-09-26 — triaging the last 21 unlinked excerpts (issue #95)

```sql
select canonical_title, canonical_genre, appearance_count
from entities.work where canonical_title ilike ?
```
Checked each of: Цыганскій баронъ, Эрнани, Папоротникъ, Свои семьи (all
0 standalone rows, confirmed genuinely no parent exists); Прекрасная
Елена (2 tiny candidates, оперет./оперетка, genuine genre-merge
question deferred to the review queue); Конекъ-Горбунокъ/Пахита/
Фіаметто (first two have solid parents, Фіаметто has none, and the
compound bill can't express 3 parents in one FK regardless).

Scan-confirmed one genuine content bug: repertoire_1900-01_p007, "18
Среда.", Большой театр -- one raw performance entry actually represents
two separate billed works ("2-е д. оп. Севильскій цирюльникъ." and
"Паяцы, оп."). Split into two `works` entries; both resolved correctly
after rebuild (Паяцы -> existing 61-appearance parent, Севильскій
цирюльникъ excerpt -> existing 50-appearance parent).

Result: 21 -> 20 unlinked. quality_flags.csv and Musicians/Roster
isolation (2900/23) both unchanged.

## 2026-09-27 — Genre review queue: which season used "лир. сц." (lyric scenes) as a genre marker?

```sql
select e.season, e.date_verbatim, t.canonical_name, perf.verbatim_title, perf.verbatim_genre
from research.performance perf
join research.event e on perf.event_id = e.event_id
join research.theater t on e.theater_id = t.theater_id
where perf.verbatim_genre = 'лир. сц.'
```

Result: single row — season 1904-05, "21 Вторникъ", Маріинскій театръ, "Евгеній Онѣгинъ" billed as "лир. сц." (lyric scenes) — Tchaikovsky's own subtitle for the opera ("лирическія сцены"), a one-off genre label rather than the usual "оп." for this title elsewhere in the corpus.

## 2026-09-27 — Genre review queue: Ромео и Джульетта single "бал." outlier among ~130 "оп." appearances

```sql
select e.season, e.date_verbatim, t.canonical_name, perf.verbatim_title, perf.verbatim_genre
from research.performance perf
join research.event e on perf.event_id = e.event_id
join research.theater t on e.theater_id = t.theater_id
where perf.verbatim_title = 'Ромео и Джульетта'
order by perf.verbatim_genre
```

Result: ~130 rows genre "оп.", one row genre "бал." — season 1903-04, "29 Понед.", Маріинскій театръ, evening session. Scan-verified against ForUpload_1903-04_Repertoire_018.jpg: reads clearly "Ромео и Джульетта, оп." — a genuine extraction misread (о→а), fixed in raw JSON. See known_issues.md issue #96.

## 2026-09-27 — Genre review queue: Конекъ-Горбунокъ single "оп." outlier among 198 "бал." appearances

```sql
select e.season, e.date_verbatim, t.canonical_name, perf.verbatim_title, perf.verbatim_genre
from research.performance perf
join research.event e on perf.event_id = e.event_id
join research.theater t on e.theater_id = t.theater_id
where perf.verbatim_title = 'Конекъ-Горбунокъ' and perf.verbatim_genre = 'оп.'
```

Result: single row — season 1907-08, "10 Воскрес.", Большой театръ. Scan-verified against ForUpload_1907-08_Repertoire_031.jpg: reads clearly "Конекъ-Горбунокъ, оп.", clean print, no ambiguity — a genuine period print anomaly, not an extraction error. Left unchanged. See known_issues.md issue #96.

## 2026-09-28 — Genre review queue: all title groups with a majority genre (>=10) and a singleton-outlier genre

```sql
with grp as (
  select title_key, max(appearance_count) as max_n, count(*) as n_variants
  from entities.work_genre_candidate
  group by title_key
)
select c.title_key, c.canonical_title, c.canonical_genre, c.appearance_count, g.max_n
from entities.work_genre_candidate c
join grp g on c.title_key = g.title_key
where c.appearance_count = 1 and g.max_n >= 10
order by g.max_n desc
```

Result: 130 singleton-outlier rows across the queue. Worked through the structurally-odd subset (near-miss spellings, single letters, excerpt markers, a placeholder ellipsis); found page/date/theater for 19 of them via entities.work_link -> raw.event_entry_performance -> raw.event_entry -> raw.source_pages joins, scan-verified 15, confirmed 6 genuine extraction bugs and fixed them (issue #98), confirmed ~9 genuine (left as-is). 4 more (on two-page-spread-season pages) deferred — page_id-to-scan mapping didn't hold for that format, needs proper re-establishing rather than reuse of the single-page mapping.

## 2026-09-28 — Post-fix verification: work_genre_candidate state for the 4 fixed title groups plus Дивертиссементъ

```sql
select canonical_title, canonical_genre, appearance_count from entities.work_genre_candidate
where title_key in ('волшебные звуки','эсмеральда','конекъ-горбунокъ','коппелия','соломенная шляпка','дивертиссементъ')
order by title_key, canonical_genre
```

Result: confirmed all 6 fixes landed correctly post-rebuild (no orphaned "атюдь"/"втюдъ"/"сц." on Конекъ-Горбунокъ/"Дивертиссементъ" on Коппелія/"ком.-вол." remaining), Эсмеральда dropped out of the queue entirely (single genre left), "Дивертиссементъ" as its own title unaffected (pre-existing, unrelated candidate entry). See known_issues.md issue #98.

## 2026-09-28 — Confirming no clobbering between this session's genre fixes and the concurrent session's issue #97 (1890-91 pp.8-9) promotion

```sql
select canonical_title, canonical_genre, appearance_count from entities.work_genre_candidate
where title_key in ('волшебные звуки','конекъ-горбунокъ','коппелия','соломенная шляпка') order by title_key, canonical_genre;
select count(*) from raw.event_entry where page_id='repertoire_1890-91_pair008';
```

Result: both sessions' changes present together in the final rebuilt outputs/full_run/imperial_theaters.duckdb — 12 genre-candidate rows reflecting this session's fixes, and 103 rows for the recovered 1890-91_pair008 page. No file-write race, checked directly rather than assumed.

## 2026-09-28 — 1891-92 St. Petersburg ballet performances by work (spot-check vs. printed "Балетъ" productions list, p. 31)

```sql
select w.canonical_title, count(*) n, string_agg(coalesce(cast(e.date as varchar),e.date_verbatim)||' '||t.canonical_name, '; ' order by e.date) dates
from research.performance p join research.event e using(event_id) join research.work w using(work_id) join research.theater t on t.theater_id=e.theater_id
where e.season='1891-92' and e.city='SP' and (w.canonical_genre ilike '%бал%' or p.verbatim_genre ilike '%бал%')
group by 1 order by 1
```

Result: 13 works. (A first attempt with `e.city ilike '%петерб%'` returned 0 rows — city is coded 'SP'/'Moscow'.) Dates match the printed list exactly for 10 of 13 ballets. Царь Кандавлъ split across two work entities (Царь Кандавлъ 6 + Царь Кандавъ 4 = printed 10). Зорайя shows 2 vs printed 3 and Фиаметта absent — both because the excerpt rows have NULL genre (checked in next query).

## 2026-09-28 — Фиаметта / Зорайя excerpt rows, 1891-92 SP

```sql
select e.date, t.canonical_name, p.performance_order, p.verbatim_title, p.verbatim_genre, w.canonical_title, w.canonical_genre, w.excerpt_of_work_id
from research.performance p join research.event e using(event_id) join research.work w using(work_id) join research.theater t on t.theater_id=e.theater_id
where e.season='1891-92' and e.city='SP' and (p.verbatim_title ilike '%Фiамет%' or p.verbatim_title ilike '%Фіамет%' or p.verbatim_title ilike '%Зора%'
 or e.date in ('1892-04-26','1891-10-13','1891-11-14','1891-12-28','1892-02-14'))
order by e.date, t.canonical_name, p.performance_order
```

Result: "2-е д. бал. Фіаметта" present on 1891-10-13, 11-14, 12-28, 1892-02-14 (Маріинскій) = printed 4; "2-я и 3-я карт. бал. Зорайя" on 1892-04-26 = printed 3rd Зорайя. Both are excerpt works (excerpt_of_work_id set) with NULL genre. So all 13 printed ballets fully reconcile with the Repertoire data.

## 2026-09-28 — Establishing the pairNNN -> printed-page -> scan-render mapping for spread-season pages

```sql
-- (not a DB query; reconstructed from source: pipeline/split_spread_pages.py,
-- pipeline/extract_split_page_numbers.py, outputs/full_run/printed_page_numbers_all.csv,
-- and resolved_sessions/*.resolved_sessions.json's own _source provenance field)
```

Result: confirmed `raw_columnwise/{season}_pNNN.raw.json`'s `NNN` is the real printed page number (read off the scan's rotated left-margin stamp), not source-render order; `outputs/repertoire_spreadfix_v6/single_leaf_images/*.png` is a stale 5-file debug leftover sharing filenames by coincidence — do not reuse. `ForUpload_{season}_Repertoire_{(pair_number-2)/2:03d}.jpg` (0-indexed, pairs increment by 2 from pair002) gives the correct render; verified against 4 independent pair/season combos by reading each render's own date header before trusting the arithmetic. See known_issues.md issue #98 follow-up for the full writeup.

## 2026-09-28 — Post-fix verification: Золото / Левъ Гурычъ Синичкинъ / Шашки genre-candidate state

```sql
select canonical_title, canonical_genre, appearance_count from entities.work_genre_candidate
where title_key in ('золото','левъ гурычъ синичкинъ','шашки') order by title_key, canonical_genre
```

Result: Золото ком.(37)/к.-м.(1, genuine); Левъ Гурычъ Синичкинъ вод.(37)/ком-вод.(1, genuine spelling variant); Шашки ш.(59)/шут.(40)/шутка(10)/ком.(1, genuine)/…(1, genuine — stain-obscured, honest transcription). Confirms both fixes (Золото/Шашки split, Левъ Гурычъ Синичкинъ р.->вод.) landed cleanly and the 2 confirmed-genuine rows are untouched. See known_issues.md issue #98 follow-up.

## 2026-09-28 — (subagent, logged retroactively) 1890-91 Repertoire lookups used while scan-checking the ballet productions list — readings since reverted to scan-only

A verification subagent for the BalletProductions lists consulted the Repertoire data to settle blurred digits, contrary to the audit design (the lists must be read from the scan alone). All affected readings were reset to scan-only and logged kind=uncertain in outputs/ballet_productions_pilot/verify_logs/. Queries as reported by the subagent:

```sql
-- failed: Binder Error, no column title_text
select e.season, e.date_undate, e.theater_text, p.title_text from raw.event_entry e join raw.event_entry_performance p using(event_id)
where e.season='1890-91' and (p.title_text ilike '%башмач%' or p.title_text ilike '%Сатанил%' or p.title_text ilike '%Флик%') order by 3,4,2;
describe raw.event_entry_performance;
describe raw.event_entry;
select p.performance_title, e.city, e.theater, e.date_undate from raw.event_entry e join raw.event_entry_performance p using(event_id)
where e.season='1890-91' and (p.performance_title ilike '%башмач%' or p.performance_title ilike '%Сатанил%') order by 1,2,4;
-- looped over {t} in Шалость, Эсмеральд, Талисман, Фіаметт, Фиаметт, Катарин, Капризы:
select e.city, e.theater, list(e.date_undate order by e.date_undate) from raw.event_entry e join raw.event_entry_performance p using(event_id)
where e.season='1890-91' and p.performance_title ilike '%{t}%' group by 1,2;
```

Result: Сатанилла Большой 1890-09-23, 11-14, 12-12, 1891-02-06, 02-17; Хрустальный башмачекъ 1890-09-30, 12-09, 1891-01-30; "Рустикальный башмачекъ" 1890-11-11 (likely a Repertoire misread of Хрустальный башмачекъ — list prints ноября 11); Шалость SP 1890-11-11, 11-14, 11-18, 12-30, 1891-02-24, 02-28; Фіаметт SP 1890-11-11, 11-18, 12-30, 1891-01-20, 03-03; Фиаметт none; Эсмеральд SP 11-25, 11-28 + Moscow 9 dates; Талисман SP 09-02, 09-16; Катарин SP 09-19; Капризы SP 09-19.

## 2026-09-28 — Genre review queue, scaled up: all title groups with a majority genre (>=10) and a singleton-outlier genre, corpus-wide

```sql
select title_key, canonical_title, canonical_genre, appearance_count from entities.work_genre_candidate
```

Result: 130 singleton-outlier rows corpus-wide (87 unique title groups not yet checked this session). RG chose "singleton-outliers only, lighter touch on rest" — worked through all 58 single-page-season groups in this batch (the 25 spread-season groups are next). Found page/date/theater for each via entities.work_link -> raw.event_entry_performance -> raw.event_entry -> raw.source_pages joins, scan-verified all 58 against ForUpload_{season}_Repertoire_{NNN}.jpg, confirmed 22 genuine bugs (fixed, issue #99) and 36 genuine (left as-is). See known_issues.md issue #99 for the full breakdown.

## 2026-09-28 — Post-fix verification: work_genre_candidate queue size after issue #99's fixes

```sql
select count(*) as n_groups from (select title_key from entities.work_genre_candidate group by title_key)
```

Result: 302 title groups (down from 316 before this round's fixes), 716 rows (down from 752). Matches expectation — roughly 19 distinct titles resolved or partially resolved this round. See known_issues.md issue #99.

## 2026-09-28 — Genre review queue: two-page-spread-season singleton-outlier groups, mapped via pairNNN->printed-page->render

```sql
-- located via entities.work_link -> raw.event_entry_performance -> raw.event_entry -> raw.source_pages joins,
-- plus the pairNNN->render mapping from issue #98's follow-up, re-verified against 3 more seasons
-- (1890-91, 1892-93, 1893-94) before trusting it for all 25 targets
```

Result: all 25 two-page-spread-season singleton-outlier groups scan-verified against ForUpload_{season}_Repertoire_{(pair-2)/2:03d}.jpg. 5 genuine bugs found and fixed (Каширская старина, Цѣна жизни, Гроза, Гибель Содома, Sapho — all misreads matching an established shape), 20 confirmed genuine. This closes the entire 83-group singleton-outlier tier. See known_issues.md issue #99 follow-up.

## 2026-09-28 — Post-fix verification: work_genre_candidate queue size after the full singleton-outlier tier

```sql
select count(distinct title_key), count(*) from entities.work_genre_candidate
```

Result: 299 title groups (down from 302), 708 rows (down from 716). Matches expectation for the 5 fixes just applied. See known_issues.md issue #99 follow-up.

## 2026-09-28 — Does the choreographer "Бернаделли" (Волшебная флейта) appear in any spiski or Repertoire title? (cross-check of an uncertain 1896-97 ballet-list reading)

```sql
select p.page_id, p.family_name, p.first_name, p.heading_path, p.credit_summary_text from raw.person_entry p
where regexp_matches(coalesce(p.family_name,'')||' '||coalesce(p.credit_summary_text,'')||' '||coalesce(p.tenure_note_text,''), 'Бер[н]?а[р]?д[еѣьe]л|Бернадел|Бернардел');
select e.season, e.date_undate, p.performance_title from raw.event_entry e join raw.event_entry_performance p using(event_id)
where regexp_matches(p.performance_title, 'Бер[н]?а[р]?д[еѣьe]л|Бернадел|Бернардел');
```

Result: 0 rows for both. He is not on any staff/artist roster (he was a visiting/historical figure, not Imperial Theaters personnel). Outside the DB: the season reviews (1892-93 SP ballet p018: "соч. Бернаделли"; 1894-95 SP ballet p002: "г-жи Бернаделли … г. Бернаделли", visiting artists from Vienna) and the ballet lists 1892-93–1895-96 ("соч. Бернаделли") all spell it Бернаделли; only 1897-98 prints "Бернарделли".

## 2026-09-28 — Genre review queue: balanced-tier full scan-check, one representative check per group

```sql
-- located via entities.work_link -> raw.event_entry_performance -> raw.event_entry -> raw.source_pages joins,
-- one target per group (smallest-count non-blank variant), for 102 of 111 balanced-tier groups
```

Result: 102 of 111 balanced-tier groups scan-verified (70 single-page-season + 32 two-page-spread-season). 10 genuine bugs found and fixed (a genre-field-excerpt bug with 2 recovered missing works on Волки и овцы, a сц./ком. misread, an этюдъ/этюдь misread, 2 more genre-fabrication bugs, a truncation bug affecting 3 rows on one page, and a genre-contamination bug). ~90 confirmed genuine. 2 spread groups (Не все коту масляница, Sodom's Ende) not reached — session paused. See known_issues.md issue #100.

## 2026-09-28 — Genre review queue: re-deriving the true count of unchecked balanced-tier groups

```sql
-- (not a DB query; cross-checked own session tracking (/tmp/oc_single.json, /tmp/oc_spread.json)
-- against the original 111-group balanced_tier.json list)
```

Result: found and corrected a counting error in the prior turn's status report — only 2 groups (Не все коту масляница, Sodom's Ende) were actually unchecked, not ~9. The "102 of 111" figure had conflated the one-check target-list size with total groups checked, without crediting the 9 groups already fully checked earlier the same session. See known_issues.md issue #100 correction.

## 2026-09-28 — Genre review queue: final 2 balanced-tier groups

```sql
select ee.date_text, ee.theater, p.page_id, p.season
from entities.work_genre_candidate wg
join entities.work_link wl on wg.work_id = wl.work_id
join raw.event_entry_performance ep on wl.raw_performance_id = ep.performance_id
join raw.event_entry ee on ep.event_id = ee.event_id
join raw.source_pages p on ee.page_id = p.page_id
where wg.canonical_title in ('Не все коту масляница','Sodom''s Ende') and wg.appearance_count = 1
```

Result: both located and scan-verified genuine (Не все коту масляница, ком. on repertoire_1891-92_pair012; Sodom's Ende, Schausp. on repertoire_1891-92_pair020). This closes the entire 111-group balanced tier at 111/111. See known_issues.md issue #100.

## 2026-09-28 — Ballet productions lists loaded into DuckDB; list-vs-Repertoire comparison (issue #101)

pipeline/load_productions.py created raw.production_entry (480 rows) and raw.production_entry_performance (1881 rows, 0 orphans, 1880 with a valid date) in outputs/full_run/imperial_theaters.duckdb (backup first: imperial_theaters.pre_productions_2026-09-28.duckdb). Sanity queries:

```sql
select season, city, count(*), sum(total_count), sum(n_dates) from raw.production_entry group by all order by 1,2;
select count(*), count(date), min(date), max(date) from raw.production_entry_performance;
select count(*) from raw.event_entry;
select season, city, count(*), count(date), count(date_undate), min(date), max(date) from research.event where season in ('1890-91','1899-00','1904-05') group by all order by 1,2;
select date_confidence, count(*) from research.event group by 1;
select distinct t.canonical_name, t.city from research.theater t order by 2,1;
select event_status, count(*) from research.event group by 1;
```

pipeline/compare_productions_repertoire.py (read-only; its two SELECTs join raw.production_entry/_performance, and research.performance/event/theater/work incl. excerpt_of_work_id parent). Result: 1881 list dates → exact 1573, excerpt 134, fuzzy 75, nearby_date 23, other_titles 29, no_event 46, impossible_date 1; 61 Repertoire performances not accounted for (31 ballet_not_in_list, 30 title_in_list_other_date). CSVs in outputs/ballet_productions_pilot/compare/.

## 2026-09-28 — Дочь микадо 1897-98 SP: Repertoire dates vs the list's "ноября 9, 24, 16, 19; декабря 14, 38"

```sql
select e.date, e.date_verbatim, t.canonical_name, p.verbatim_title, e.printed_page_number from research.performance p join research.event e using(event_id) join research.theater t on t.theater_id=e.theater_id
where e.season='1897-98' and e.city='SP' and p.verbatim_title ilike '%микадо%' order by e.date;
select e.date, e.date_verbatim, t.canonical_name, string_agg(p.verbatim_title, ' | ') from research.event e join research.theater t on t.theater_id=e.theater_id left join research.performance p using(event_id)
where e.season='1897-98' and e.city='SP' and t.canonical_name='Маріинскій' and e.date between '1897-11-05' and '1897-12-31' group by all order by 1;
```

Result: Repertoire has Дочь микадо 1897-11-14, 11-16, 11-19, 12-14, 12-29, 1898-01-04, 04-19 and 04-22 (1-е д.) = 8. Suggests list "24" = 14 and "38" = 29 (12-28 was Жизнь за Царя). The Repertoire has NO Маріинскій events 1897-11-06..11-12, so the list's 9 Nov is unverifiable there — a possible Repertoire gap to check.

## 2026-09-28 — Which Repertoire pages bound the list-vs-Repertoire date gaps, and are printed pages truncated? (issue #101)

```sql
select date_undate, city, page_id, printed_page_number from raw.event_entry where season=? and date_undate in (?,?) group by all order by 1,2;  -- once per gap, 12 gaps
select page_id, printed_page_number, min(date_undate), max(date_undate), count(*) from raw.event_entry where season='1896-97' group by 1,2 order by 3;
select season, page_id, printed_page_number, count(*) n, min(date_undate) a, max(date_undate) b from raw.event_entry
where season between '1890-91' and '1897-98' group by all having count(*) < 35 order by season, a;
select count(distinct season||page_id||printed_page_number) from raw.event_entry where season between '1890-91' and '1897-98';
```

Result: every gap falls at the join between consecutive spreads, with consecutive printed page numbers, so no pages are missing. 1896-97 p. 15 has 18 rows (30–31 Dec) but the scan prints 30 Dec – 8 Jan; p. 17 has 17 rows (19–21 Jan) but the scan prints 19–28 Jan. 19 of 192 printed pages in the spread seasons have <35 rows. Some are genuinely short (season start/end, Lent); the rest match the list gaps: 1892-93 p3, 1894-95 p17, 1895-96 p16/p23, 1896-97 p15/17/19/23/25, 1897-98 p7/9/19.

## 2026-09-28 — Красный цвѣтокъ: all remaining "этюдъ"-family genre spellings, located and scan-checked

```sql
select wg.canonical_genre, ee.date_text, ee.theater, p.page_id, p.season
from entities.work_genre_candidate wg
join entities.work_link wl on wg.work_id = wl.work_id
join raw.event_entry_performance ep on wl.raw_performance_id = ep.performance_id
join raw.event_entry ee on ep.event_id = ee.event_id
join raw.source_pages p on ee.page_id = p.page_id
where wg.canonical_title = 'Красный цвѣтокъ'
order by wg.canonical_genre, ee.date_text
```

Result: 8 distinct genre spellings, 17 total occurrences across 14 pages, all individually scan-verified. 1 genuine misread found and fixed (`др. ят.`->`др. эт.`), 2 real date/session bugs found and fixed as a side effect (a mis-dated session on repertoire_1900-01_p016 that also exposed a missing session once corrected; a 3-way date/content tangle on repertoire_1903-04_p012 that exposed another missing session). 14 more confirmed genuine, including "драм. втюдъ" (2 occurrences) confirmed as a genuine period spelling, not the misread it was expected to be. See known_issues.md issue #102.

## 2026-09-28 — Post-fix verification: Красный цвѣтокъ genre-candidate state

```sql
select canonical_title, canonical_genre, appearance_count from entities.work_genre_candidate where title_key='красный цветокъ' order by appearance_count desc
```

Result: 7 distinct genre spellings (down from 8), 17 total appearances unchanged. Confirms both fixes landed cleanly (др. ят. merged into др. эт.; the recovered/untangled sessions kept the same genre values they already had). See known_issues.md issue #102.

## 2026-09-28 — Final survey of the genre-review queue: what's genuinely left, and closing the last 3 unverified titles

```sql
-- classified all 297 current title groups into "same-family spelling noise" (Problem #5, correctly
-- never merged) vs "genuinely distinct genre families" via a prefix-relation union-find over normalized
-- genre values, then cross-referenced against every title checked this session
```

Result: 297 title groups / 701 rows total in `entities.work_genre_candidate`. 109 groups are correctly-noise (spelling variants, not a task). Of 188 groups with genuinely distinct genre families, 179 were individually scan-checked this session (today, issues #98-102); the remaining 9 had documented resolutions from earlier sessions (Борисъ Годуновъ, Русалка, Севильскій цирюльникъ, Раймонда, Карменъ — all cited in known_issues.md from issues #89-99) except 3 (Я играю большую роль, Гамлетъ, Фаустъ) which had never been individually scan-verified. Checked all 3 fresh: all confirmed genuine (Я играю большую роль, ком. on repertoire_1899-00_p019; Гамлетъ, оп. as part of a benefit-gala excerpt listing on repertoire_1904-05_p031; Фаустъ, др. поэма on repertoire_1905-06_p022, Goethe's poem distinct from Gounod's opera). No fixes needed.

This closes 100% of the genre-review queue's "genuinely distinct genre family" tier (188/188 groups), on top of the already-closed singleton-outlier and balanced tiers. The 109 noise groups remain permanently in the queue by design (Problem #5).

## 2026-09-28 — Annotation audit: banner-style vs per-cell annotations (RG's request)

RG asked to audit `raw.event_entry.annotation`: some annotations sit in one
cell alongside that session's own production info, others print as a
banner heading spanning several theater columns for one date/session.
Ran a sequence of queries; exact SQL for the first few reconstructed from
session notes after a context-window boundary (not preserved verbatim),
noted below where approximate.

**Query 1 (approximate) — overall annotation value distribution:**
```sql
select annotation, count(*) from raw.event_entry
where annotation is not null group by annotation order by count(*) desc
```
Result: 738 distinct non-null annotation values across the corpus.

**Query 2 (approximate) — debug/fix-note leakage search:**
```sql
select annotation, count(*) from raw.event_entry
where annotation is not null
  and (annotation ilike '%corrected%' or annotation ilike '%scan%'
       or annotation ilike '%model%' or annotation ilike '%fixed%'
       or annotation ilike '%confirmed%' or annotation ilike '%verified%'
       or annotation ilike '%issue%' or annotation ilike '%bug%'
       or annotation ilike '%mislabel%')
group by annotation
```
Result: exactly 2 matches, both genuine developer debug-notes leaked into
the content field instead of being left null: (1) 12 rows on
`repertoire_1903-04_p000` (all `Михайловскій театръ.`, dates 31 Воскрес.
through 15 Понед.) carrying the literal text "corrected 2026-09-22: model
fabricated a spurious sub-6-ruble receipts figure for this cell; scan
(ForUpload_1903-04_Repertoire_000.jpg) shows a literal dash, no
performance, issue #77"; (2) 1 row carrying "date_text corrected from
mislabeled \"14 Понед.\" to \"13 Воскрес.\" (scan-verified,
ForUpload_1898-99_Repertoire_016.jpg): this row is the 13th evening
session, not the 14th" (page not yet independently re-confirmed by page_id
this segment, filename in the leaked text points to
`repertoire_1898-99_p016`). 13 rows total, contained, not widespread
(next largest match count after these two is 0).

**Query 3 (approximate, self-corrected mid-investigation) — banner-gap
detection, first pass (flawed — joined only on page_id+date_text, no
session):**
```sql
select e1.page_id, e1.date_text, e1.annotation, e2.theater
from raw.event_entry e1
join raw.event_entry e2
  on e1.page_id = e2.page_id and e1.date_text = e2.date_text
  and e2.annotation is null and e2.event_status != 'no_performance'
where e1.annotation in (<4 known banner strings>)
```
Result: 419 apparent "gaps" — later found to be an artifact of not
constraining on `time_of_day`/session, conflating a date's morning and
evening sessions. Spot-check against raw JSON for
`repertoire_1899-00_p012` ("14 Воскрес.") showed all 3 theaters' morning
sessions already correctly carried the banner, directly contradicting this
query's face-value output. Superseded by Query 4.

**Query 4 — corrected banner-gap detection, joined on
(page_id, date_text, time_of_day):**
```sql
select e1.page_id, e1.date_text, e1.time_of_day, e1.annotation, e2.theater, e2.event_status
from raw.event_entry e1
join raw.event_entry e2
  on e1.page_id = e2.page_id and e1.date_text = e2.date_text
  and e1.time_of_day = e2.time_of_day
  and e2.annotation is null
where e1.annotation in (<4 known institutional banner strings>)
```
Result: 84 real sibling comparisons for the 4 known banner strings; 77
confirmed true gaps (sibling theater performed in the identical
page/date/session slot but is missing the banner), 5 legitimately dark
(no gap expected), 2 legitimately carry the theater's own distinct
benefit program instead. Cross-verified directly against scans for 2
independent examples (`repertoire_1899-00_p012` "14 Воскрес." morning;
`repertoire_1902-03_p010`/`p011` "14 Четвергъ." morning) — both confirm
the banner prints once, centered across the full table width, above one
specific date's specific session, and both confirm the raw data currently
under-captures it to a single theater.

**Query 5 — corpus-wide coverage-ratio scan across all annotation values
(≥3 occurrences), to look for banner candidates beyond the 4 manually
identified:**
```sql
with occ as (
  select annotation, page_id, date_text, time_of_day, count(distinct theater) as n_theaters_with_it,
         (select count(distinct theater) from raw.event_entry e2
          where e2.page_id = e1.page_id and e2.date_text = e1.date_text and e2.time_of_day = e1.time_of_day
            and e2.event_status != 'no_performance') as n_theaters_performed_that_slot
  from raw.event_entry e1
  where annotation is not null
  group by annotation, page_id, date_text, time_of_day
)
select annotation, count(*) as n_occurrences_page_date,
       sum(n_theaters_with_it) as total_theater_rows,
       sum(n_theaters_performed_that_slot) as total_theater_rows_performed,
       round(sum(n_theaters_with_it)*1.0/sum(n_theaters_performed_that_slot), 2) as coverage_ratio
from occ group by annotation having count(*) >= 3
order by coverage_ratio asc, n_occurrences_page_date desc limit 40
```
Result: lowest-ratio entries were dominated by personal benefit-performance
annotations ("Бенефисъ г. Садовскаго.", "Бенефисъ г-жи Савиной.", etc.) —
a naturally low, CORRECT coverage ratio for a genuinely per-theater note
(only the theater hosting that named artist's benefit should ever carry
it), so raw coverage ratio alone cannot distinguish a true under-captured
banner from a correctly-narrow personal note. Superseded by Query 6, which
adds the distinguishing test.

**Query 6 — refined: only flag annotation values already confirmed to
co-occur across 2+ theaters in the same slot at least once (a personal
benefit for one named artist cannot legitimately do this; only an
institutional/page-wide banner can), then check remaining coverage gap:**
```sql
with occ as (
  select annotation, page_id, date_text, time_of_day, count(distinct theater) as n_theaters_with_it,
         (select count(distinct theater) from raw.event_entry e2
          where e2.page_id = e1.page_id and e2.date_text = e1.date_text and e2.time_of_day = e1.time_of_day
            and e2.event_status != 'no_performance') as n_theaters_performed_that_slot
  from raw.event_entry e1
  where annotation is not null
  group by annotation, page_id, date_text, time_of_day
),
confirmed_banner as (
  select distinct annotation from occ where n_theaters_with_it >= 2
)
select o.annotation, count(*) as n_occurrences,
       sum(o.n_theaters_with_it) as total_rows_with_it,
       sum(o.n_theaters_performed_that_slot) as total_rows_performed,
       sum(o.n_theaters_performed_that_slot) - sum(o.n_theaters_with_it) as missing_rows
from occ o
where o.annotation in (select annotation from confirmed_banner)
group by o.annotation having missing_rows > 0
order by missing_rows desc
```
Result: 10 distinct confirmed-banner annotation strings with a real,
quantified undercapture gap, 151 missing theater-rows total:
Спектакль для учащейся молодежи. (68 missing), Концертъ въ пользу
инвалидовъ. (37), Гимнъ. (16), Безплатные спектакли для воспитанниковъ
столичныхъ учебныхъ заведеній. (11), Безплатные утренніе спектакли для
воспитанниковъ учебныхъ заведеній. (7), Спектакль въ память Н. В. Гоголя.
(5), Спектакль въ память А. С. Пушкина. (3), Въ пользу Иверской Общины
сестеръ милосердія Краснаго Креста. (2), Спектакль въ пользу Иверской
Общины Краснаго Креста. (1), Юбилейный спектакль въ память столѣтія со
дня рожденія А. С. Пушкина. (1). This is the working confirmed-bug list
for the banner-undercapture class; the long tail of low-coverage-ratio
"Бенефисъ г./г-жи [Name]." entries from Query 5 is NOT part of this list
and should not be treated as buggy — their low ratio is the correct,
expected shape of a genuinely per-theater note. No fix applied yet;
investigation only, per RG's request ("take a look and see if there's
anything unexpected").

## 2026-09-28 — Truncated spread pages: integration vs control vs production, and list comparison after the fix (issue #103)

Read-only counts on three DBs (outputs/full_run, recovery .../control, .../integration):

```sql
select count(*) from raw.event_entry;  select count(*) from raw.event_entry_performance;
select count(*) from research.event;  select count(*) from research.performance;  select count(*) from research.work;
select count(*) from entities.person where superseded_by_person_id is null;
select count(*) from research.event where event_status='not_captured';
select count(*) from research.event where date_confidence in ('verified','intra_block_disagreement');
select count(*) from research.event where season between '1890-91' and '1897-98';  -- and season > '1897-98'
select sum(receipts_total_kopecks) from research.event;
select w.canonical_title, w.canonical_genre, w.appearance_count from research.work w where w.canonical_title not in (select canonical_title from ctl.research.work);
select e.date_text, e.date_undate, d.corrected_date_undate, d.date_confidence, count(*) from raw.event_entry e left join analysis.event_entry_date_check d using(event_id)
 where e.page_id='repertoire_1895-96_pair020' and e.date_undate in ('1896-02-28','1896-02-29','1896-03-28','1896-03-29') group by all;
select e.page_id, e.date_undate, string_agg(distinct e.date_text, ' / '), count(*) from raw.event_entry e join analysis.event_entry_date_check d using(event_id)
 where d.date_confidence='intra_block_disagreement' group by 1,2;
```

Result: control == production everywhere. Integration (and production after promotion) has raw.event_entry 26039 -> 26485, research.event 28968 -> 29439, research.performance 27591 -> 28221, research.work 3482 -> 3511, verified 25550 -> 26016, intra_block 397 -> 377, persons 2900 unchanged, non-spread seasons unchanged. The pair020 March rows sat on 1896-02-28/29 (intra_block, not corrected); 73 intra_block page/date groups, and only pair020 and 1894-95 pair006 (4 Oct) show two weekdays on one date. compare_productions_repertoire.py on production afterwards: no_event 46 -> 0, exact 1624, excerpt 140, fuzzy 77, other_titles 24, nearby_date 15.

## 2026-09-28 — Annotation audit: applying and verifying issue #104's fixes

**Debug-note-leak fix**: nulled `annotation` on 12 rows in
`repertoire_1903-04_p000.raw.json` and 1 row in
`repertoire_1898-99_p016.raw.json` (exact rows identified via the query
below), matching the 13 rows found in the investigation phase.
```sql
select page_id, date_text, time_of_day, theater, annotation
from raw.event_entry
where annotation ilike '%corrected%' or annotation ilike '%mislabel%'
order by page_id, date_text
```
Result (pre-fix): 13 rows, exact text confirmed matching the leaked
debug comments. Post-fix same query returns 0 rows.

**Banner-backfill full scan-verified sweep**: rather than trust the
138-row mechanical gap query, dispatched 8 parallel agents to
individually scan-verify every one of the 138 candidate rows across 84
pages against the actual printed scan (resolved via
`ForUpload_{season}_Repertoire_{idx:03d}.jpg`, with pair-numbered
spread-season ids resolved via the `(pairnum-2)/2` formula documented
in known_issues.md issue #98's follow-up, and 1908-09's 11 missing
renders freshly rendered from its PDF at 200dpi with PyMuPDF).

Result: **28 of 138 (20%) confirmed genuine, 110 (80%) confirmed false
positives** — the naive query would have been wrong 4 times out of 5.
Confirmed genuine banner strings: "Гимнъ." (20 rows/5 pages) and
"Безплатные [утренніе] спектакли для воспитанниковъ [столичныхъ]
учебныхъ заведеній." (8 rows/6 pages) — both visually confirmed as an
actual merged/italic/bold header row spanning the relevant theaters'
columns. All other candidates (dominated by "Спектакль для учащейся
молодежи." and "Концертъ въ пользу инвалидовъ.") were per-theater or
per-city notes incorrectly flagged by the same-slot join; see issue
#104 in known_issues.md for the full breakdown and the specific
false-positive classes now documented for future queries.

Applied the 28 confirmed rows directly to their raw JSON files (theater/
date_text/time_of_day matched against each verdict, annotation set only
where previously null — 0 write failures). Verification query
post-rebuild:
```sql
select count(*) from raw.event_entry where annotation in (<10 banner strings>)
```
Result: 321 total rows now carry one of these 10 strings corpus-wide
(up from the pre-fix count), consistent with 28 new + prior existing
occurrences.

Rebuilt full chain (`parse_and_validate.py` with both mandatory flags →
`quality_checks.py` → `build_duckdb.py` → `build_entities.py` →
`validate_performance_dates.py` → `build_research_model.py`). Confirmed
stable: quality_flags.csv 895 (baseline), validation_errors.csv 268
(baseline), dates verified 98.2%, Musicians/Roster entity isolation
2900/23 (unchanged), work_genre_candidate 297 groups/702 rows
(unchanged from concurrent session's own state). event_entry 26485
(reflects concurrent issue #103 work already in outputs/full_run, not a
regression from this session's changes — no session/work rows were
added or removed by this fix, only `annotation` values on existing
rows).

## 2026-09-28 — Fuzzy-title round (issue #105): worklist, integration/control diff, restore check

```sql
-- worklist: one Repertoire cell per fuzzy list date
select e.page_id, e.printed_page_number, e.date_text, e.theater, e.time_of_day, p.performance_title, p.genre
from raw.event_entry e join raw.event_entry_performance p using(event_id) where e.city=? and e.date_undate=? and p.performance_title=?;
-- builds: counts of raw.event_entry, research.performance, research.work, research.event, verified, receipts sum, persons, entities.work_genre_candidate, raw.production_entry
select canonical_title, appearance_count from ctl.research.work where canonical_title not in (select canonical_title from research.work);
select canonical_title, appearance_count from research.work where canonical_title not in (select canonical_title from ctl.research.work);
select count(*) from raw.event_entry where annotation is not null;
select count(*) from research.work where canonical_title in ('Данта','Бандерка','Царь Кандавъ','Царь Кандавль','Рустикальный башмачекъ','Ненюфарь');
```

Result: 77 cells on 59 pages. Integration vs control: works 3511 -> 3499 (13 misread works gone, +Фея-куколъ); everything else identical. Final production: works 3499, annotated raw rows 1458 (the parallel session's edits kept), misread works 0; comparison fuzzy 12, exact 1689, excerpt 140.

## 2026-09-28 — Follow-up to issue #104: headings miscaptured as spurious `works` entries

RG asked "what else do we need to look at carefully around annotations
(both banners and benefits)". Checked whether banner/occasion headings
were ever landing in `raw.event_entry_performance.performance_title`
instead of `annotation` (a structural-split bug, same class as issue
#98's Коппелія/Дивертиссементъ finding), rather than only auditing the
`annotation` field itself as issue #104 did.

```sql
select ep.performance_title, count(*)
from raw.event_entry_performance ep
where ep.performance_title ilike '%Гимнъ%' or ep.performance_title ilike '%безплатн%'
   or ep.performance_title ilike '%спектакль для учащ%' or ep.performance_title ilike '%въ память%'
   or ep.performance_title ilike '%юбилейн%' or ep.performance_title ilike '%концертъ въ пользу%'
group by ep.performance_title order by count(*) desc
```
Result: "Гимнъ"/"Гимнъ." as a work_title, 145 occurrences total (genre
always NULL, consistent with a genuinely performed wordless anthem
opener -- NOT flagged as a bug). Plus 9 occurrences of 8 entirely new
occasion headings never covered by issue #104's 10-string banner list:
Спектакль въ память А. С. Грибоѣдова (x2), Спектакль въ память И. А.
Крылова (x2), Концертъ въ пользу фонда на сооруженіе... М. И. Глинкѣ
(x1), Спектакль въ память Н. И. Хмельницкаго (x1), Спектакль въ память
Вольфганга Гёте (x1), Спектакль въ память Императрицы Екатерины II
(x1), Спектакль для учащейся молодежи with no trailing period (x1) --
all 9 with `annotation` NULL.

```sql
select case when annotation ilike '%Гимнъ%' or annotation ilike '%Hymne%' then 'has_gimn_annotation'
            when annotation is null then 'annotation_null' else 'other_annotation' end as bucket, count(*)
from raw.event_entry_performance ep join raw.event_entry ee on ep.event_id = ee.event_id
where ep.performance_title ilike '%Гимнъ%' group by bucket
```
Result: of the 145 "Гимнъ" sessions, only 16 also carry a matching
"Гимнъ."/"Hymne." annotation; 118 have annotation=NULL entirely, 11
have some other annotation. Left uninvestigated this round (out of
scope for the 7-page follow-up RG asked to start with) -- flagged as
the largest remaining open thread.

Individually scan-verified all 9 new-heading rows across their 7 pages
(resolved via the same season/pairnum scan-mapping as issue #104).
Result: **all 9 confirmed genuine** (no false positives this round,
unlike the earlier banner-gap sweep) -- each heading is a real printed
occasion notice that the extractor correctly transcribed but placed in
`works` instead of `annotation` (structurally identical to issue #98's
Коппелія/Дивертиссементъ bug). 3 pairs (Грибоѣдовъ, Крыловъ, Екатерина
II) independently confirmed shared across exactly 2 theaters each on
the same date/session via direct scan comparison; the other 3
(Глинка-concert, Гёте, Хмельницкій, student-matinee) confirmed
single-theater and self-contained, matching the already-established
"literary/historical memorial -> drama-focused theaters only, verify
per instance, never assume corpus-wide" rule from issue #104.

**2 additional genuinely missing sessions found as a side effect** of
scan-checking the Ekaterina II page in full: Большой театръ and
Маріинскій театръ both had their entire `24 Воскресенье.` session
missing from raw JSON for `repertoire_1896-97_pair010` (page's own
`_source` note already flagged "Маріинскій/Большой entirely missing
from extraction" as a known limitation from issue #78's 2023 -- er,
2026-09-23 reconstruction, but this specific date had fallen outside
what that pass covered). Recovered both directly from the scan
(`ForUpload_1896-97_Repertoire_004.jpg`): Большой = "О время!, ком. /
Ѳедулъ съ дѣтьми, оп. / Апоѳеозъ" under the shared Ekaterina II
heading, receipts 2643 р. 52 к.; Маріинскій = "Конекъ-горбунокъ, бал.",
receipts 2893 р. 32 к., no annotation (Маріинскій's own regular ballet
that night, unrelated to the memorial).

Applied: moved all 9 headings from `works` to `annotation` (removing
the spurious no-genre `works` entry in each case, keeping any genuinely
distinct co-listed items -- e.g. Хмельницкій's commemorative LECTURE by
И. А. Шляпкинъ was kept as its own work, since a lecture is a real
distinct program item, not a duplicate of the heading). Added the 2
recovered sessions.

Rebuilt full chain. Confirmed stable: quality_flags.csv 895 (baseline),
validation_errors.csv 268 (baseline), dates 98.2% (26016->26018
verified, +2 matching the 2 recovered sessions), work_genre_candidate
297 groups/702 rows (unchanged), Musicians/Roster 2900/23 (unchanged).
event_entry 26485->26487 (+2, the recovered sessions);
event_entry_performance 28222->28217 (-5, net of -9 removed spurious
heading-works +4 added real works for the 2 recovered sessions).

**Still open, not investigated this round**: the 118-row "Гимнъ
present as work, annotation NULL" population -- likely the largest
remaining thread in this area, but out of today's scope (RG asked to
start with just the 7-page/9-row new-heading set). See known_issues.md
issue #104 follow-up entry.

## 2026-09-28 — (subagent, logged retroactively) read-only checks during the other-title round, item 8 (issue #101 follow-up)

A checker ran two read-only queries on outputs/full_run to understand item 8 (1895-96 Moscow Катарина "января 17"). The exact SQL was not reported. What it looked up: (1) Moscow events on the list's Катарина dates (13 Dec 1895, 17 and 28 Jan 1896); (2) Большой events 14–21 Jan 1896. Result: Катарина appears on 13 Dec and 28 Jan, and on 17 Jan the Большой has Эсмеральда (500 р. 50 к.), matching the scan, so item 8 is a genuine list/Repertoire disagreement (category E). Not used to decide any reading.

## 2026-09-28 — Ballet-list dates re-derived from the season, not the printed year (RG): what changed

```sql
select production_performance_id, date from raw.production_entry_performance;  -- compared with the re-parsed CSV before reloading
```

Result: 1881 dates, 4 changed (1897-02-12 -> 1898-02-12 Пери; 1899-04-19 -> 1900-04-19 Дочь Микадо; 1903-11-06 -> 1902-11-06 Коппелія; 1904-04-27 -> 1903-04-27 Тщетная). All 4 now match the Repertoire; comparison exact 1691, excerpt 142 (was 1689/140), other_titles 24 -> 21, nearby_date 15 -> 14.

## 2026-09-28 — Other-title round (issue #106): worklist and integration/control diff

```sql
select e.page_id, e.printed_page_number, e.date_text, e.theater, e.time_of_day, string_agg(p.performance_title||coalesce(' ['||p.genre||']',''), ' + ' order by p.performance_order)
from raw.event_entry e left join raw.event_entry_performance p using(event_id) where e.city=? and e.date_undate=? group by all order by 4,5;
-- builds: counts of raw.event_entry, research.performance, research.work, research.event, verified, intra_block, receipts sum, persons, annotated raw rows
```

Result: 24 items (21 after the season-date change). Integration vs control: raw.event_entry +12, research.performance +31, research.work -3, research.event +7, verified +12, receipts +72,747 kopecks, persons unchanged, annotated rows -4. Production == integration after promotion. Comparison: other_titles 12, exact 1694, excerpt 148.

## 2026-09-29 — Near-date round: worklist of list dates where the Repertoire has the ballet 1–3 days away

```sql
select e.page_id, e.date_text, e.theater, e.time_of_day, string_agg(p.performance_title, ' + ' order by p.performance_order)
from raw.event_entry e left join raw.event_entry_performance p using(event_id) where e.city=? and e.date_undate=? group by all order by 3,4;
-- run for both the list date and the matched Repertoire date of each of the 13 nearby_date items
```

Result: comparison on current production is unchanged overnight (exact 1694, excerpt 148, nearby_date 13, fuzzy 13, other_titles 12). The 13 cluster as: 5 Большой cases on 1897-98 pair014 around New Year 1898 (likely column shift), plus Золушка on the same page; 2 on 1894-02-02, where the Repertoire has no Маріинскій session at all (likely column shift); 2 Moscow dates with no Repertoire rows at all (1893-09-15, 1895-01-04); 3 single offsets.

## 2026-09-29 — Near-date round (issue #107): builds, promotion check, and the confirmed-disagreements list

```sql
-- integration vs control vs production: counts of raw.event_entry, research.performance, research.work, research.event,
-- verified, intra_block_disagreement, sum(receipts_total_kopecks), live persons, annotated raw rows
select e.date, e.date_verbatim, t.canonical_name, p.verbatim_title from research.performance p join research.event e using(event_id) join research.theater t on t.theater_id=e.theater_id
 where e.season='1897-98' and e.city='SP' and p.verbatim_title ilike '%микадо%' order by e.date;
select distinct e.page_id, e.printed_page_number from raw.event_entry e where e.city=? and e.date_undate=?;  -- page refs for each remaining mismatch
```

Result: integration vs control raw.event_entry +17, performances +7, receipts +1,066,463 kopecks, verified +35, intra_block -13; production == integration after promotion. Дочь микадо 1897-98 SP now on 9, 14, 16, 19 Nov; 14, 28 Dec; 4 Jan; 19, 22 Apr (9 dates, 1:1 with the list's 9; "24" pairs with 14, "38" with 28, not 29 as reported 2026-09-28 from the then-shifted column). Comparison after the list fix (Кандавлъ): exact 1706, excerpt 148, fuzzy 12, other_titles 12, nearby_date 2.

## 2026-09-29 — Latin letters / quarter fractions in receipts (issue #108)

```sql
select regexp_matches(receipts_text,'[pk]') latin, count(*) n,
 sum(case when regexp_matches(receipts_text,'\d\s*[pр]') and receipts_rubles is null then 1 else 0 end) rub_missing,
 sum(case when regexp_matches(receipts_text,'\d\s*[kк]') and receipts_kopecks is null then 1 else 0 end) kop_missing
from raw.event_entry where receipts_text is not null group by 1;
-- builds: counts of raw.event_entry, research.performance, research.work, sum(receipts_total_kopecks), receipts with Latin letters, receipts containing '¼', verified, persons
```

Result: Latin-letter receipts parse fine (0 missing rubles/kopecks among 737); 8 non-Latin receipts have an unparsed kopeck figure. Integration == control except text; after promotion: Latin-letter receipts 738 -> 1 (the genuine "q."), '¼' 24 -> 0, receipts total unchanged (2800248320).

## 2026-09-29 — The 8 receipts with an unparsed figure (follow-up to issue #108)

```sql
select page_id, date_text, theater, time_of_day, receipts_text, receipts_rubles, receipts_kopecks
from raw.event_entry where receipts_text is not null and regexp_matches(receipts_text,'\d\s*[kк]') and receipts_kopecks is null order by page_id;
```

Result: 8 rows, all documented genuine print typos in the ruble/kopeck marker (1225 q. 27 к.; 876 к. 18 к.; 736 к. 49 н.; 1041 и. 53 к.; 701 г. 06 к.; 433 к. 45 к.; 1055 к. 04 к.; 1107 к. 62 к.). They are deliberately unparsed per RG's rule, so they are excluded from receipts totals until a research-layer correction exists.

## 2026-09-29 — Receipts that fail to parse, or parse only partly (research-layer correction, issue #109)

```sql
-- fully unparsed
select e.page_id, e.date_text, e.theater, e.time_of_day, e.receipts_text, e.receipts_rubles, e.receipts_kopecks, a.receipts_total_kopecks
from raw.event_entry e join analysis.event_entry a using(event_id)
where e.receipts_text is not null and regexp_matches(e.receipts_text,'\d') and a.receipts_total_kopecks is null order by e.page_id;
-- malformed rubles/kopecks parts (partial parses)
select e.page_id, e.date_text, e.theater, e.time_of_day, e.receipts_text, e.receipts_rubles, e.receipts_kopecks, a.receipts_total_kopecks
from raw.event_entry e join analysis.event_entry a using(event_id)
where e.receipts_text is not null and (
   (e.receipts_kopecks is not null and not regexp_matches(e.receipts_kopecks, '^\s*(\d+([½¼¾]|¹/₂)?|[—–-]+)?\s*$'))
or (e.receipts_rubles is not null and not regexp_matches(e.receipts_rubles, '^\s*(\d+|[—–-]+)\s*$'))) order by 1;
-- plus a lookup of the other documented receipts typos by their printed figures (1495, 263, 7166, 3049 р. 78, 366 р. 54, 777 р. 33, 3977 р. 50, and the 1905-06 p017/p018/p043 pages)
```

Result: 11 fully unparsed (the 8 documented typos plus "(3058 р. 08 к.)", "1с31 р. 35 к.", "19 22 р. 34 к."); 53 malformed-part receipts, most silently undercounted (e.g. "13.472 р. 22 к." counted as 1322 kopecks; "292 р. 04 р." loses its kopecks). Documented typos "1495 д.", "263 д." and the 1905-06 cases are transcribed with р. in raw, i.e. normalised away from the print. A scan check confirmed the print has the typo for 5 of them, so they are to be restored.

## 2026-09-29 — Receipts correction applied (issue #109): intended values and effect

```sql
select page_id,date_text,theater,time_of_day,receipts_text,receipts_total_kopecks from analysis.event_entry where receipts_text in (<60 scan-confirmed figures>);
select receipts_source, count(*) from research.event group by 1;
-- before/after: counts of raw.event_entry, research.event, research.performance, research.work, persons, sum(receipts_total_kopecks), raw.production_entry, annotated rows
```

Result: 60 confirmed figures found, each exactly once; 4 already parse correctly, 56 corrected. receipts_source: parsed 17110, corrected_print_typo 56, NULL 12297. sum(receipts_total_kopecks) 2800248320 -> 2802505260 (+2,256,940 = 22,569 р. 40 к.); every other count unchanged.

## 2026-09-29 — Issue #110: effect of rebuilding 1899-00 p028 and re-splitting 1902-03 p011

```sql
select e.page_id, e.date_text, e.theater, e.time_of_day, e.annotation from raw.event_entry e where e.date_undate=? and e.theater like ?;  -- 1900-02-20 Маріинскій, 1902-11-13 Новый
-- before/after: counts of raw.event_entry, research.event, research.performance, research.work, persons, sum(receipts_total_kopecks), annotated rows, verified, raw.production_entry
```

Result: raw.event_entry 26516 -> 26524, research.event 29463 -> 29471, research.performance 28254 -> 28259, research.work 3489 -> 3484, persons 2900, receipts 2802505260 -> 2803164121, annotated 1464 -> 1442, verified 26065 -> 26073. List comparison: exact 1705, excerpt 149; Repertoire-side not-accounted 52.

## 2026-09-29 — Repertoire-side leads: why "list leaves out a date" rows were really matcher artifacts

```sql
select e.page_id, e.date_text, e.theater, e.time_of_day, p.performance_title, e.receipts_text, e.event_id
from raw.event_entry e join raw.event_entry_performance p using(event_id) where e.city=? and e.date_undate=? and p.performance_title ilike ?;  -- per lead
select production_entry_id,season,city,list_number,title,page_id,printed_page_number,performed_text,total_text,total_count,n_dates from raw.production_entry;
```

Result: of 31 "title_in_list_other_date" rows, 13 were comparison-script artifacts (6 operas Робертъ/Балъ-маскарадъ prefix-matched to ballets; 4 same-cell "2-я и 3-я карт. бал." continuations that took the list date's claim; 3 matinee+evening pairs where one list date claimed both, incl. Золотая рыбка "ноября 14 (2 раза: утромъ и вечеромъ)"). After the matcher fixes: 18 remain = 3 halves of confirmed disagreements (A1, A4, A5) + 15 to scan-check (11 dates, 1 suspected Repertoire duplicate, 3 likely paired with A3/A7/A12). In all 15, the list's printed Всего equals its printed date count. The list-side match counts are unchanged (exact 1705, excerpt 149).

## 2026-09-29 — Issue #111 effect, and the copied-"morning"-row detector

```sql
-- before/after: counts of raw.event_entry, research.event, research.performance, research.work, persons, sum(receipts_total_kopecks), annotated rows, verified, raw.production_entry
```

Result: raw.event_entry 26524 -> 26516, research.event 29471 -> 29463, research.performance 28259 -> 28245, research.work 3484 -> 3483, receipts 2803164121 -> 2801769194, annotated 1442 -> 1440, verified 26073 -> 26065; comparison exact 1705 / excerpt 149; Repertoire-side leads 34. Detector (a JSON scan of outputs/full_run/raw, not SQL): 55 "morning" sessions whose works equal the same theater's adjacent day, on 35 pages.

## 2026-09-29 — Correction: the "2 missing sessions" from issue #104's follow-up were never missing

The concurrent Ballet-productions session (issue #111) caught that the
2 sessions I added to `repertoire_1896-97_pair010` yesterday (Большой
and Маріинскій, `24 Воскресенье.`) already existed under `date_text`
`24 Воскрес.` -- a shorter spelling variant used elsewhere on the same
page, which my own lookup never searched for before concluding
"missing." Verification query, post their fix:
```sql
select theater, date_text, session, annotation, receipts_text
from raw.event_entry
where page_id = 'repertoire_1896-97_pair010' and date_text = '24 Воскресенье.'
```
Result: exactly 7 rows (one per theater; Александринскій/Малый split
morning/evening as expected), no duplicates. My `annotation` content
(the Ekaterina II heading on Большой's real row) and `works` content
were both preserved by their fix -- only the duplicate-row mistake and
the date_text spelling were corrected. See known_issues.md issue #104
follow-up's correction addendum for the full writeup and the lesson
(never conclude "missing" without checking for a spelling/abbreviation
variant of the date string first, especially on a page that already
mixes conventions).

## 2026-09-29 — Issue #112: integration vs control counts (missing ballets + copied-morning sweep)

```sql
select (select count(*) from raw.event_entry), (select count(*) from raw.event_entry_performance),
       (select count(*) from research.event), (select sum(receipts_total_kopecks) from research.event),
       (select count(*) from research.work)
-- run on outputs/recovery_2026-09-28_spread_truncation/r0929_ctl and r0929_int, and on full_run after promotion
```

Result: control (26516, 28246, 29463, 2801769194, 3483); integration = production after promotion
(26520, 28246, 29467, 2801057477, 3481). quality_flags.csv identical (900 rows).

## 2026-09-29 — Issue #112: event-level diff, control vs integration, on the 40 staged pages

```sql
select e.page_id, e.date_text, e.theater, e.time_of_day, e.event_status, e.receipts_total_kopecks,
       string_agg(p.performance_title, ' / ' order by p.performance_order)
from {a|b}.analysis.event_entry e left join {a|b}.raw.event_entry_performance p using (event_id)
where e.page_id in (<40 staged page_ids>) group by all
-- set difference control minus integration and vice versa
```

Result: 48 rows removed / 55 added, every one a documented agent or scan fix (listed in known_issues.md #112);
receipts delta −711717 kopecks, fully accounted for (−499320, −162600, −20555, −187825, +158583).

## 2026-09-29 — Issue #112: printed page numbers of the five "no list entry" ballet cells + 21 Oct 1901

```sql
select e.page_id, e.date_text, e.theater, e.time_of_day, e.printed_page_number, e.receipts_text, e.annotation
from raw.event_entry e
where (e.page_id, e.date_text) in (('repertoire_1902-03_p016','14 Суббота.'), ('repertoire_1903-04_p036','24 Суббота.'),
  ('repertoire_1904-05_p038','29 Вторн.'), ('repertoire_1904-05_p042','23 Суббота.'), ('repertoire_1901-02_p009','21 Воскрес.'))
  and (e.theater ilike '%аріин%' or e.theater ilike '%Больш%') order by 1
```

Result: printed pp. 11 (1901-02 Большой, 2421 р. 58 к.), 18, 38, 128, 132; the four charity/jubilee cells have no receipts.

## 2026-09-29 — Issue #112: compare_productions_repertoire.py on production after promotion

pipeline/compare_productions_repertoire.py (read-only; same two SELECTs as before). Result: unchanged —
1881 list dates → exact 1705, excerpt 149, fuzzy 12, other_titles 12, nearby_date 2, impossible_date 1;
34 Repertoire-side not accounted for (19 ballet_not_in_list, 15 title_in_list_other_date). After #112 all 34 are
in the disagreements list's A/D/E sections, except 12 comedy-ballets (research need) and 2 "Балетный
дивертиссементъ" rows, not yet checked.

## 2026-09-29 — Issue #113: every "Балетный дивертиссементъ" performance in the Repertoire

```sql
select e.event_id, e.page_id, e.date_text, e.theater, e.time_of_day, e.printed_page_number, e.receipts_text, e.annotation,
       string_agg(p.performance_title||' | '||coalesce(p.genre,''), ' // ' order by p.performance_order)
from raw.event_entry e join raw.event_entry_performance p using (event_id)
where e.event_id in (select event_id from raw.event_entry_performance where performance_title ilike 'Балетный дивертис%')
group by all
```

Result: 11 rows; only 1901-02 p023 (16 Среда, Новый) and 1903-04 p034 (17 Суббота, Маріинскій) had genre "бал." (the two leads); the other 9 had no genre.

## 2026-09-29 — Issue #113: ballet lists mentioning a divertissement, or the two dates

```sql
select season, city, list_number, title, performed_text, post_total_text from raw.production_entry
where concat_ws(' ', title, description_text, performed_text, post_total_text) ilike '%дивертис%';
select list_number, title, performed_text from raw.production_entry
where season = ? and city ilike ? and (performed_text ilike ? or post_total_text ilike ?)  -- ('1901-02','Moscow%','%января%'), ('1903-04','SP%','%апрѣля%')
```

Result: only 1891-92 Moscow #7 and 1892-93 Moscow #1 mention a divertissement (descriptions, unrelated). No 1901-02 Moscow entry gives января 16; no 1903-04 SP entry gives апрѣля 17.

## 2026-09-29 — Issue #113: production after the fix

```sql
select (select count(*) from raw.event_entry), (select count(*) from raw.event_entry_performance), (select count(*) from research.event),
       (select sum(receipts_total_kopecks) from research.event), (select count(*) from research.work);
select performance_title, genre, count(*) from raw.event_entry_performance where performance_title ilike 'Балетный дивертис%' group by all
```

Result: (26520, 28246, 29467, 2801057477, 3481), unchanged; all 11 divertissement rows now genre NULL.
compare_productions_repertoire.py: list side unchanged; Repertoire-side not accounted for 34 → 32 (17 ballet_not_in_list, 15 title_in_list_other_date).

## 2026-09-29 — Issue #114: divertissement works in research.work before the genre rule

```sql
select w.work_id, w.canonical_title, w.canonical_genre, w.appearance_count, count(p.performance_id),
       string_agg(distinct coalesce(p.verbatim_genre,'∅'), ', '), string_agg(distinct p.verbatim_title, ' ; ')
from research.work w left join research.performance p using (work_id)
where w.canonical_title ilike '%дивертис%' or w.canonical_title ilike '%дивертисм%' group by all order by 5 desc
```

Result: Дивертиссементъ 81 (∅, др.); Балетный дивертиссементъ 9 (∅); Дивертиссментъ 5; Большой дивертиссементъ 2 (др.);
Балетный дивертиссментъ 2 (∅); Концертный и балетный дивертиссемент 1. All genre NULL except Большой (др.).

## 2026-09-29 — Issue #114: research.work after RESEARCH_GENRE_RULES

```sql
select genre_source, count(*) from research.work group by 1 order by 1;
select canonical_title, canonical_genre, appearance_count from research.work where genre_source = 'research_rule';
select count(*) from research.performance p join research.work w using (work_id) where w.genre_source = 'research_rule';
select genre, count(*) from raw.event_entry_performance where performance_title ilike 'Балетный дивертис%' group by 1;
select canonical_title, canonical_genre from research.work where canonical_title ilike '%дивертис%' and genre_source is distinct from 'research_rule'
```

Result: first run (regex without е?) matched 1 work only; after the fix printed 3074, research_rule 2, NULL 405;
Балетный дивертиссементъ бал. 9 + Балетный дивертиссментъ бал. 2 = 11 performances; raw genre NULL for all 11;
the other 4 divertissement works untouched. compare_productions_repertoire.py: Repertoire-side leads 32 → 40
(ballet_not_in_list 17 → 25; 8 divertissements in list seasons).

## 2026-09-29 — What is still outstanding between the ballet lists and the Repertoire (status review)

Read outputs/ballet_productions_pilot/compare/list_dates_vs_repertoire.csv (non-exact/excerpt rows) and
repertoire_not_in_lists.csv, then mapped each against docs/eval/ballet_list_repertoire_disagreements.md.
Result: list side, 27 non-matched dates. Each is in A1–A12, B1 or C1–C7, is one of the 4 waiting for RG's physical
check (Паяда/Наяда, Ваядерка/Баядерка, Пригалъ/Привалъ, Пахита fold cell), or is Ученики Дюпрэ (not a disagreement).
Repertoire side, 40 = 5 E + 15 in A/D + 8 ballet divertissements (RG's call) + 12 comedy-ballets (research need).

```sql
select e.page_id, e.date_text, e.theater, e.time_of_day, p.performance_title, p.genre, e.receipts_text
from raw.event_entry e join raw.event_entry_performance p using (event_id)
where p.performance_title in ('Анда','Анда.') or p.performance_title ilike 'Анда,%'
```

Result: 5 "Анда, оп." rows at the Маріинскій (1896-97 pair004 24 Вт.; 1898-99 p030 7 Вс.; 1904-05 p030 13 Вс. утро;
1905-06 p006 9 Вс. утро; 1905-06 p022 28 Ср. веч.). Not scan-checked: could be a misread of "Аида" or genuine print.

## 2026-09-29 — Issue #114 (2nd addendum): list pages for the three seasons with ballet divertissements

```sql
select season, city, page_id, printed_page_number, source_file, source_page_index, count(*), min(list_number), max(list_number)
from raw.production_entry
where (season, city) in (('1901-02','Moscow'), ('1902-03','Moscow'), ('1903-04','SP')) group by all order by 1, 2, 4
```

Result: 1901-02 MSK p. 54 (15 entries); 1902-03 MSK p. 51 (10); 1903-04 SP pp. 44 (2), 45 (22), 46 (4). Used only to
locate the scans; the lists themselves were then read on the scans, not from the transcription.

## 2026-09-29 — Is the 1902-03 Moscow ballet list (p. 51) missing a continuation? Repertoire-side test

```sql
select coalesce(pw.canonical_title, w.canonical_title) t, w.canonical_genre, count(*) n, string_agg(distinct th.canonical_name, ', ')
from research.performance p join research.event e using (event_id) join research.work w using (work_id)
left join research.work pw on pw.work_id = w.excerpt_of_work_id join research.theater th on th.theater_id = e.theater_id
where e.season = '1902-03' and e.city ilike 'Mos%'
  and (w.canonical_genre ilike '%бал%' or pw.canonical_genre ilike '%бал%' or p.verbatim_genre ilike '%бал%' or p.verbatim_title ilike '%бал.%')
group by all order by n desc;
select list_number, title, total_count from raw.production_entry where season = '1902-03' and city ilike 'Mos%' order by try_cast(list_number as int);
select w.canonical_title, count(*), string_agg(distinct th.canonical_name, ', ')
from research.performance p join research.event e using (event_id) join research.work w using (work_id) join research.theater th on th.theater_id = e.theater_id
where e.season = '1902-03' and e.city ilike 'Mos%' and w.canonical_genre is null and p.verbatim_genre is null group by all order by 1
```

Result: ballet-genre works = the list's 10 (Конекъ-Горбунокъ 13+1, Эсмеральда 7+1, Лебединое озеро 5, Спящая красавица 4,
Дочь фараона 3, Волшебный башмачекъ 3, Донъ Кихотъ 2+1, Коппелія 2+1, Корсаръ 2+1, Клоринда 2) plus Балетный
дивертиссементъ 2. Genre-less: 5 excerpts of listed ballets, Да здравствуетъ жизнь! др. 3, Снѣгурочка 2, Дивертиссементъ 5.
No unlisted ballet → no missing p. 52 entries.

## 2026-09-29 — Пахита fold cell (1897-98 p012, 5 May 1898): П-ballets in the 1897-98 Petersburg Repertoire

```sql
select coalesce(pw.canonical_title, w.canonical_title) t, count(*) n, min(e.date), max(e.date)
from research.performance p join research.event e using (event_id) join research.work w using (work_id)
left join research.work pw on pw.work_id = w.excerpt_of_work_id
where e.season = '1897-98' and e.city not ilike 'Mos%'
  and (w.canonical_genre ilike '%бал%' or pw.canonical_genre ilike '%бал%' or p.verbatim_title ilike '%бал.%')
group by all order by 1
```

Result: 15 ballets; П-titles are Пахита (3, last 1898-04-26) and Привалъ кавалеріи (2). Only Пахита fits the fragment's ~6-letter word.

## 2026-09-29 — Is "?" or "[" already used inside titles? (transcription marker for an unreadable digit)

```sql
select p.performance_title, e.page_id, e.date_text from raw.event_entry_performance p join raw.event_entry e using (event_id)
where p.performance_title like '%?%' limit 20;
select count(*) from raw.event_entry where receipts_text like '%?%';
select count(*) from raw.event_entry_performance where performance_title like '%[%' or performance_title like '%]%';
select count(*) from raw.event_entry where annotation like '%[%'
```

Result: "?" is real punctuation in several titles (Гдѣ мой зять?, Которая изъ двухъ?, Что такое любовь?, Qui?); 2 receipts
use "?" as an uncertainty marker; brackets occur in 0 titles and 0 annotations.

## 2026-09-29 — Issue #115: production before/after promoting "[?]-е д. бал. Пахита"

```sql
select (select count(*) from raw.event_entry), (select count(*) from raw.event_entry_performance), (select count(*) from research.event),
       (select count(*) from research.work), (select count(*) from research.work where excerpt_of_work_id is not null);
select p.verbatim_title, w.canonical_title, w.excerpt_note, pw.canonical_title
from research.performance p join research.work w using (work_id) left join research.work pw on pw.work_id = w.excerpt_of_work_id
where p.verbatim_title like '[?]%'
```

Result: before (backup db) (26520, 28246, 29467, 3481, 169); after (26520, 28247, 29467, 3482, 170).
"[?]-е д. бал. Пахита" → excerpt_note "[?]-е д.", parent Пахита. compare_productions_repertoire.py: exact 1705, excerpt 150,
fuzzy 12, other_titles 11, nearby_date 2, impossible_date 1; Repertoire-side 40 (unchanged).

## 2026-09-29 — Production-stats scoping pilot, 1896-97: events and receipts per theater

```sql
select t.canonical_name, e.event_status, count(*) n, count(e.receipts_total_kopecks) n_rec, round(sum(e.receipts_total_kopecks)/100.0, 2) rub
from research.event e join research.theater t using (theater_id) where e.season = '1896-97' group by all order by 1, 2
```

Result (performed): Александринскій 231 (322,673.29), Большой 203 (365,675.65), Малый 217 (218,125.13),
Маріинскій 182 (541,846.23), Михайловскій 217 (258,763.16). The stats page (p. 27) gives Moscow Russian drama 217 (219,255.13).

## 2026-09-29 — Production-stats pilot, 1896-97: performed events split by Latin-script titles (foreign troupes)

```sql
with ev as (select e.event_id, t.canonical_name th, e.receipts_total_kopecks k,
  bool_or(regexp_matches(p.verbatim_title, '^[A-Za-zÀ-ÿ]')) latin
  from research.event e join research.theater t using (theater_id) join research.performance p using (event_id)
  where e.season = '1896-97' and e.event_status = 'performed' group by all)
select th, latin, count(*), round(sum(k)/100.0, 2) from ev group by all order by 1, 2
```

Result: Александринскій Russian 193 (249,583.89) / Latin 38 (73,089.40); Большой 177 (299,895.45) / 25 (65,780.20);
Малый 217 (218,125.13); Маріинскій 178 (538,135.23) / 1 (3,711.00); Михайловскій 72 (78,846.09) / 145 (179,917.07).
Against the stats page: Михайловскій French 145 = 145; Михайловскій drama + opera + ballet 55 + 14 + 3 = 72 = 72;
Большой Italian opera 25 = 25; Малый 217 = 217; German 34 vs 38 Latin at the Александринскій.

## 2026-09-30 — Season stats vs Repertoire, level 1: city totals per season (pipeline/compare_season_stats.py)

```sql
with ev as (
  select e.season, e.city, e.event_id, e.theater_id, coalesce(e.date, e.event_id) as day_key,
         e.receipts_total_kopecks as k,
         coalesce(regexp_matches(lower(a.annotation), 'въ пользу'), false) as charity_text
  from research.event e left join analysis.event_entry a using (event_id)
  where e.event_status = 'performed')
select season, city, count(*) sessions, count(distinct (theater_id, day_key)) days, count(k) sessions_with_receipts,
       coalesce(sum(k), 0), coalesce(sum(k) filter (where charity_text), 0), count(*) filter (where charity_text)
from ev group by all
```

Result (34 city-seasons vs docs/season_stats/lines.csv, subtotals excluded): counting sessions (утро/веч. separately)
is within −3..+11 of the stats count in 1891-92 to 1900-01; counting distinct theater-days is short by 19–63 in every
season, so the yearbook counted morning and evening performances separately. From 1901-02 the Repertoire exceeds the
stats (SP +33 1901-02, +34 1906-07, +70 1907-08, +55 1908-09; Moscow +38 1907-08). Counting only sessions with receipts
doesn't match either (mostly −5..−30). Exact count matches: 2 (1892-93 and 1899-00 Moscow). 1908-09 Moscow receipts
differ by +10,775.35 while charity-text sessions carry 10,775.55.

## 2026-09-30 — Later-season excess: performed sessions per theater, with receipts and mornings

```sql
select e.season, e.city, t.canonical_name, count(*), count(e.receipts_total_kopecks),
       count(*) filter (where a.time_of_day = 'morning'),
       count(*) filter (where e.receipts_total_kopecks is null and a.time_of_day = 'morning')
from research.event e join research.theater t using (theater_id) join analysis.event_entry a using (event_id)
where e.event_status = 'performed' and e.season in ('1900-01','1901-02','1907-08','1908-09') group by all order by 1, 2, 3
```

Result: 1907-08 Михайловскій 173 sessions, 124 with receipts (stats French 103 + German 24 = 127). 1908-09 Михайловскій
178 / 127 (stats 103 + 25 = 128).

## 2026-09-30 — 1907-08 Михайловскій sessions without receipts

```sql
select a.page_id, a.date_text, a.time_of_day, a.receipts_text, left(coalesce(a.annotation, ''), 70), string_agg(p.performance_title, ' / ')
from research.event e join research.theater t using (theater_id) join analysis.event_entry a using (event_id)
left join raw.event_entry_performance p using (event_id)
where e.event_status = 'performed' and e.season = '1907-08' and t.canonical_name = 'Михайловскій' and e.receipts_total_kopecks is null
group by all order by 1, 2
```

Result: 49 sessions. 12 are charity or free student performances; about 37 (p042–p048, 14 Apr to 13 May 1908) are a
continuous run of Брандъ, Росмерсхольмъ, Жизнь человѣка, Докторъ Штокманъ, Вишневый садъ, Горе отъ ума with no receipts.
Scan p042 (checked at 300 dpi) prints no company heading for the run, so the performer is not stated there.

## 2026-09-30 — Season stats level 2: genre labels and Latin-title samples (to derive family rules)

```sql
select lower(coalesce(w.canonical_genre, p.verbatim_genre, '∅')) g, count(*) from research.performance p join research.work w using (work_id)
join research.event e using (event_id) where e.event_status = 'performed' and e.season >= '1891-92' group by 1 order by 2 desc limit 70;
select e.city, t.canonical_name, count(*) from research.performance p join research.event e using (event_id) join research.theater t using (theater_id)
where e.event_status = 'performed' and regexp_matches(p.verbatim_title, '^[A-Za-zÀ-ÿ]') group by all;
-- per ambiguous genre g in ('опер.','oper.','op.','dr.','p.','∅'): top 10 titles with theater and season
```

Result: "опер." = operetta by the drama company (Александринскій/Малый: Не бывать бы счастью, Парики); "oper." = German
opera at the Маріинскій 1897-98 (Lohengrin, Siegfried); "op." = Italian opera at the Большой (Otello, La Traviata);
"dr."/"p." with Latin titles = French troupe at the Михайловскій. Latin-titled performances: Михайловскій 4639,
Александринскій 711, Большой 52, Маріинскій 35, Малый 3.

## 2026-09-30 — Season stats level 2: family comparison (pipeline/compare_season_stats.py, LEVEL2_SQL)

```sql
select e.event_id, e.season, e.city, t.canonical_name, e.receipts_total_kopecks, p.verbatim_title, coalesce(w.canonical_genre, p.verbatim_genre)
from research.event e join research.theater t using (theater_id)
left join research.performance p using (event_id) left join research.work w using (work_id)
where e.event_status = 'performed'
```

Result: classified in Python (rules in the script). Exact family matches: 20 (strict "mixed") → 48 (drama + opera/ballet
counted under opera/ballet) → 55 after the Latin-title rules; total |Δ| 1236 → 748 → 642. Venue rows: 45/99 exact.
Leads: 63 rows with exact count but differing receipts; later SP drama excess (+37, +58, +50 in 1906-09); 85 sessions with no works.

## 2026-09-30 — Examples of "drama + opera/ballet" bills (RG asked what the convention covered)

Same join as LEVEL2_SQL plus analysis.event_entry (page_id, date_text, printed_page_number), ordered by performance_order,
seasons 1891-92–1908-09 except 1905-06; classified with pipeline/compare_season_stats.py.

Result: 299 such bills (180 ballet, 119 opera), and the "drama" item was usually genre-less: benefit headings stored as works,
"Гимнъ", excerpts ("3-е д. бал. Пахита", "1-е д. оп. Невѣста-лунатикъ"), "Дивертиссементъ". After classifying genre-less works
by title marker or as neutral: 78 remain (48 ballet, 30 opera), mostly still misreads (the Псковитянка prologue printed
"Боярыня Вѣра Шелога, прологъ, др.", "Мѣщанинъ во дворянствѣ, ком.-бал.", "Соломенная шляпка, оп.-вод."). Re-test with the
script's own functions: 57 exact / |Δ| 710 without the convention, 55 / 662 with it. The convention was dropped.

## 2026-09-30 — First look: events where ballet appears with another art form (RG's research interest)

LEVEL2_SQL (pipeline/compare_season_stats.py) ordered by event_id, performance_order; works classified with classify_work;
events containing a ballet-family work, grouped by the other families present (neutral genre-less items ignored).

Result: 1,847 performed events include a ballet work; 122 also include another art form. Ballet + opera 60 (Большой 32,
Маріинскій 26, Михайловскій 2); ballet + drama 46 (spread over all six theaters); ballet + drama + opera 7; small groups
with concerts and French plays. Known classifier limits: "ком.-бал." counts as ballet (Батюшкина дочка, Мѣщанинъ во
дворянствѣ), "Grand pas изъ балета Корсаръ" is misread as French, and 85 events have no works at all.

## 2026-09-30 — Are comedy-ballets in the ballet productions lists? (RG side question)

```sql
select season, city, list_number, title, left(description_text, 90) from raw.production_entry
where regexp_matches(lower(concat_ws(' ', title, description_text)), 'батюшкин|мѣщанинъ|комеді[яи][- ]балет|ком\.-бал|съ балетомъ|comédie-ballet');
select e.season, t.canonical_name, p.verbatim_title, p.verbatim_genre, count(*) from research.performance p join research.event e using (event_id)
join research.theater t using (theater_id) where e.event_status = 'performed' and regexp_matches(lower(p.verbatim_genre), 'ком.*бал') group by all order by 1
```

Result: 0 list entries. Repertoire "ком.-бал.": Батюшкина дочка at the Александринскій 3+3+1 (1893-94, 1894-95, 1895-96);
Мѣщанинъ во дворянствѣ Новый 4 + Большой 1 (1899-00).

## 2026-09-30 — Stats receipt leads: single-digit-slip candidates (pipeline/season_stats_receipt_candidates.py)

Same event join as the script's EVENT_SQL (research.event + analysis.event_entry + performance/work), classified with
compare_season_stats.py. For each of the 64 leads (count exact, receipts differ), every event whose receipts would account
for the difference by one digit change or one adjacent swap.

Result: only 8 of 64 leads have any candidate, and all but one have many (e.g. Δ30.00: 81 candidates), so the slip
hypothesis explains little. Most differences are hundreds to thousands of rubles.

## 2026-09-30 — Stats receipt leads: sessions without receipts and charity receipts per lead

Result: most positive leads (stats higher) have 1–7 performed sessions with NULL receipts in the category (none with
unparsed receipts_text except 2). This gives a worklist of 79 receipt-less sessions on 44 pages
(outputs/recovery_2026-09-30_stats_receipts/worklist.csv), sent for scan checks.

## 2026-09-30 — Issue #117: control vs integration vs production after the receipt-less-session round

```sql
select (select count(*) from raw.event_entry), (select count(*) from raw.event_entry_performance), (select count(*) from research.event),
       (select sum(receipts_total_kopecks) from research.event), (select count(*) from research.work),
       (select count(*) from raw.event_entry where annotation is not null)
```

Result: control (26520, 28247, 29467, 2801057477, 3482, 1440); integration = production after promotion
(26523, 28249, 29470, 2801057472, 3482, 1485). compare_season_stats.py afterwards: family rows 57/223 exact, venue rows 52/99.

## 2026-09-30 — When does the stats page's ballet count match the ballet productions lists?

```sql
-- per season/city: sum of printed "Всего" totals, list date rows, distinct list dates, distinct dates without a note
select e.season, e.city, sum(e.total_count) ...;   -- over raw.production_entry
select e.season, e.city, count(distinct p.date) from raw.production_entry_performance p join raw.production_entry e using (production_entry_id)
where not p.outside_total group by all
```

Compared with docs/season_stats/lines.csv, "Балетныхъ" (non-subtotal lines) and "Смѣшанныхъ" lines whose qualifier mentions балет.
Result (28 overlapping season-cities, 1891-92–1904-05):
- Σ "Всего" never matches; it is always higher, because double bills are counted per work.
- Distinct list dates = the stats ballet line in 8 (1891-92 MSK, 1896-97 SP, 1899-00 SP, 1900-01 MSK, 1901-02 SP,
  1902-03 MSK, 1902-03 SP, 1903-04 SP).
- Distinct list dates = ballet + mixed-with-ballet in 5 more (1891-92 SP, 1892-93 SP, 1894-95 MSK, 1896-97 MSK, 1897-98 MSK).
- 13/28 in all. The largest gap is 1892-93 MSK (+11 after mixed). Lists are lower than stats in 1898-99 MSK (−5), 1899-00 MSK (−3)
  and 1901-02 MSK (−3). Distinct dates merge same-day утро + веч. ballet, so they can undercount.

## 2026-09-30 — 1892-93 Moscow: ballet-list dates (54) vs stats ballet 41 + mixed 2; and what "Феерій" covers

```sql
select try_cast(e.list_number as int), e.title, left(e.description_text, 110), e.total_count, count(p.*) filter (where not p.outside_total),
       string_agg(strftime(p.date, '%m-%d') || coalesce('(' || p.note || ')', ''), ' ' order by p.date)
from raw.production_entry e join raw.production_entry_performance p using (production_entry_id)
where e.season = '1892-93' and e.city = 'Moscow' group by all order by 1;
select e.date, t.canonical_name, string_agg(p.verbatim_title || ' | ' || coalesce(p.verbatim_genre, ''), ' / ')
from research.event e join research.theater t using (theater_id) join research.performance p using (event_id)
where e.season = '1892-93' and e.city = 'Moscow' and e.event_status = 'performed'
  and e.event_id in (select event_id from research.performance where lower(coalesce(verbatim_genre, '')) like '%феер%') group by all order by 1;
-- then: every list entry whose title/description mentions кольцо любви / феері / волшебная сказка, every season;
-- every Repertoire performance with a "феер" genre; full description of Кольцо любви
```

Result: list #5 Кольцо любви, "Волшебная сказка въ 3 д. и 10 карт., составлена по нѣмецкимъ народнымъ сказкамъ и повѣрьямъ
В. А. Крыловымъ, музыка частью П. П. Золотаренко, частью заимствована". 11 dates, identical to the 11 Repertoire sessions
(Большой, genre "феерія"), = stats "Феерій 11". 41 + 2 + 11 = 54 = list dates. 1893-94 Moscow: Кольцо любви 5 = stats
"Феерій 5"; 43 + 2 + 5 = 50 vs 49 list dates. The stats pages have a "Феерій" line only in these two Moscow seasons.
Works the lists call "Балетъ-феерія" (Спящая красавица, Щелкунчикъ, Синяя борода) never get a separate stats line; they
fall under "Балетныхъ". In the Repertoire, "феер" genres occur only for Кольцо любви (1892-94) and three single later sessions.

## 2026-09-30 — Кольцо любви in the ballet season reviews (does RG's parent-genre rule's second condition hold?)

Text search (not SQL) of outputs/reviews/view_full_parsed/text/*.txt for "Кольцо любви".
Result: review_1892-93_MSK_ballet_p004 (caption "Сцена 1-й картины 2-го дѣйствія фееріи В. А. Крылова—«Кольцо любви»");
review_1893-94_MSK_ballet_p000 ("43 балетныхъ спектакля, 2 смѣшанныхъ (балетъ и опера вмѣстѣ) и 5 спектаклей, въ которыхъ
была дана феерія («Кольцо любви»)", the same figures as the 1893-94 stats page); review_1893-94_MSK_ballet_p012
(the season's last performance, 25 Apr, was the féerie).

## 2026-09-30 — Issue #118: parent_genre = ballet (scratch copy, then production)

```sql
select count(*), count(*) filter (where excerpt_of_work_id is not null) from research.work where parent_genre = 'ballet';
select coalesce(canonical_genre, '∅'), count(*) from research.work where parent_genre = 'ballet' group by 1 order by 2 desc;
select w.canonical_title, w.canonical_genre, count(*) from research.work w join research.performance p using (work_id)
join research.event e using (event_id) where w.canonical_genre ilike '%бал%' and w.parent_genre is null and e.season <= '1904-05'
group by all order by 3 desc;
select count(*) from research.performance p join research.work w using (work_id) where w.parent_genre = 'ballet'
```

Result: first run (exact/excerpt only) 175 works; "Раймонда, оп." (1901-02 p026, scan-confirmed genuine print) and
Кольцо любви "феерія." correctly included. 8 ballet works were missed only by spelling. After the curated aliases:
184 works, 2,267 performances. The ballet-genre works left NULL are exactly Балетный дивертиссементъ, the two
comedy-ballets, Сонъ въ лѣтнюю ночь and Мнимыя дріады (none is in a list).

## 2026-09-30 — Is "Балъ-маскарадъ въ Венеціи" (printed "див.") in the ballet productions list?

```sql
select e.season, e.city, e.list_number, e.printed_page_number, e.title, e.description_text, e.performed_text, e.total_text
from raw.production_entry e where e.title ilike 'Балъ-маскарад%';
-- plus every Repertoire event with a work titled 'Балъ-маскарад%', and research.work rows with that title and their parent_genre
```

Result: yes. 1892-93 Moscow list #1 (p. 38): "Балъ-маскарадъ въ Венеціи. Большой дивертиссементъ, составленъ Н. Ѳ.
Манохинымъ. Исполненъ: 1893 г.—февраля 5. Всего—1 разъ." Repertoire 5 Feb 1893 Большой (1892-93 pair016, p. 17): the
Гейтенъ 1-я benefit, 1-е д. оп. Фенелла / 2-е д. бал. Корсаръ / 2-е д. и 1-я карт. 3-го д. бал. Дочь фараона /
"Балъ-маскарадъ въ Венеціи, див.". The Verdi opera "Балъ-маскарадъ, оп." is a separate work and is not given the ballet
parent genre.

## 2026-09-30 — Three-way ballet count per season-city: stats page, ballet list, Repertoire (parent_genre)

```sql
select e.season, e.city, p.date, p.note from raw.production_entry_performance p join raw.production_entry e using (production_entry_id)
where not p.outside_total and p.date is not null;   -- list: distinct dates, "2 раза" counted twice
select e.season, e.city, count(distinct e.event_id) from research.event e join research.performance p using (event_id)
join research.work w using (work_id) where e.event_status = 'performed' and w.parent_genre = 'ballet' group by all;
-- per mismatching season-city: Repertoire parent-ballet sessions per date (theater, time_of_day, titles) vs list dates
```

Result: all three agree 11/28, two agree 14, all differ 3. Differences mapped to dates: a matinée/evening counting
artifact (1893-94 MSK+SP, 1898-99 MSK ×5, 1899-00 MSK ×5); recorded disagreements A2–A12, B1, D3–D8, E1, E2, E4;
new leads 1899-01-23 Маріинскій (Балъ изъ бал. Пахита), 1901-12-12 and 1901-12-19 Новый (Коппелія), 1902-02-21
Большой утро (Жизель / Корсаръ). Added the alias Ученики Дюпрэ → Les élèves de Dupré; research.work parent_genre ballet
184 → 185.

## 2026-09-30 — 1899-00 Moscow and the other unqualified "Смѣшанныхъ" lines: which Repertoire sessions are they?

```sql
-- 1899-00 Moscow sessions whose annotation mentions the 75th anniversary or the Иверская Община, with works and parent_genre
select e.date, t.canonical_name, a.time_of_day, a.page_id, a.printed_page_number, left(a.annotation, 120), e.receipts_total_kopecks,
       string_agg(p.verbatim_title || ' | ' || coalesce(p.verbatim_genre, '') || ' | ' || coalesce(w.parent_genre, ''), ' / ')
from research.event e join research.theater t using (theater_id) join analysis.event_entry a using (event_id)
join research.performance p using (event_id) join research.work w using (work_id)
where e.season = '1899-00' and e.city = 'Moscow' and e.event_status = 'performed'
  and (a.annotation ilike '%75%' or a.annotation ilike '%Иверск%') group by all;
-- list rows on 1900-01-06 and 1900-04-12 (1899-00 Moscow); РТО / Литературный фондъ sessions 1898-99 SP; РТО 1900-01 SP;
-- 1903-04 Moscow sessions mixing a parent-ballet work with other genres
```

Result:
- 1899-00 MSK: 6 Jan 1900 Большой (75th anniversary, includes Танцовщики по неволѣ, бал.) and 12 Apr 1900 Большой
  (Иверская, Лакме / Фея куколъ). The list prints both dates, so 62 + 2 = 64 in all three sources.
- 1898-99 SP: РТО 23 Jan 1899 gala (… Балъ изъ бал. Пахита); no session found for the Литературный фондъ.
- 1900-01 SP: РТО 30 Dec 1900 (… 2-е д. бал. Фіаметта).
- 1903-04 MSK: 18 Oct 1903 benefit (1-е д. Донъ-Кихотъ) and 24 Oct 1903 Tchaikovsky memorial (3-е д. Лебединое озеро).
- ballet_counts.csv: all three agree 14/28.

## 2026-09-30 — 1894-95 SP ballet count: which performances make the stats page's "русская драма и балетъ 4"?

```sql
-- every performed 1894-95 SP session with a ballet element (parent_genre ballet, a бал genre, "бал."/"балет"/"дивертис" in a title)
select e.date, t.canonical_name, a.time_of_day, a.page_id, left(a.annotation, 70), e.receipts_total_kopecks is not null,
       max(case when w.parent_genre = 'ballet' then 1 else 0 end), string_agg(p.verbatim_title || ' | ' || coalesce(p.verbatim_genre, ''), ' / ')
from research.event e join research.theater t using (theater_id) join analysis.event_entry a using (event_id)
join research.performance p using (event_id) join research.work w using (work_id)
where e.season = '1894-95' and e.city = 'SP' and e.event_status = 'performed' and e.event_id in (...) group by all order by 1, 2;
-- receipts of the 7 Александринскій candidates; every pair tested against the printed 9,015 р. 98 к.
```

Result: Маріинскій ballet 17, Михайловскій 3, opera + ballet 4, all as printed. Drama + ballet: 2 listed-ballet bills + the two
"Дивертиссементъ" bills (21 and 29 Sep 1894) = 9,015.98 р. exactly (the only pair). The three Батюшкина дочка bills are not
counted there. Маріинскій pure-ballet receipts 44,784.11 vs stats 44,984.11 (Δ 200.00, not pursued; receipts paused).

## 2026-09-30 — 1895-96 SP ballet count: stats 51 vs list = Repertoire 52

Same session query as for 1894-95 (season '1895-96'), grouped by theater and family with compare_season_stats.classify_work;
plus the list entry for Очарованный лѣсъ 1895-96 SP and footnote 2.
Result: Маріинскій ballet 46; Михайловскій ballet 1 (1,195.60 = stats); Михайловскій drama + ballet 4 (2,457.95 = stats).
The extra performance is 3 Jan 1896 Александринскій утро, a free student performance (Старый закалъ + Очарованный лѣсъ); the
list prints "января 3". Not counted as mixed: 29 Mar 1896 (Друзья-пріятели + Дивертиссементъ) and 22 Jan 1896 (Батюшкина дочка).

## 2026-09-30 — 1904-05 Moscow ballet count: stats 39 vs list = Repertoire 41

```sql
select e.event_id, e.date, t.canonical_name, a.time_of_day, left(a.annotation, 70), e.receipts_total_kopecks, string_agg(...)
from research.event e join research.theater t using (theater_id) join analysis.event_entry a using (event_id)
join research.performance p using (event_id) join research.work w using (work_id)
where e.season = '1904-05' and e.city = 'Moscow' and e.event_status = 'performed'
  and e.event_id in (select p2.event_id from research.performance p2 join research.work w2 using (work_id) where w2.parent_genre = 'ballet')
group by all order by 2;
-- list rows for 1904-11-14, 1904-12-06, 1905-02-16, 1905-02-24, 1905-04-19
```

Result: 41 sessions, receipts 82,893.95 (stats 82,893.92); 5 without receipts: 3 free student matinées and 2 charity performances
(16 Feb retirement-home benefit Макбетъ/Гамлетъ/Фіаметта; 19 Apr Иверская, Волшебное зеркало). The list prints all 5. The 2 the
stats page omits are among these 5, most likely the charity pair (unproven).

## 2026-09-30 — 1904-05 SP ballet count: stats 46 vs list 48 vs Repertoire 47

Parent-ballet sessions 1904-05 SP (research.event/performance/work, as for Moscow), receipts per session; the 13 Feb 1905
Маріинскій sessions; brute-force search over dropping sessions (± adding the 13 Feb evening, 8,750.70) for count 46 and
receipts 130,012.64.
Result: 47 sessions, 135,020.94 р.; no exact solution. Closest solutions involve the 28 Dec 1904 morning Корсаръ, 15,291.95
(already flagged as a likely print typo). Count reading: stats = Repertoire − 2 charity performances (29 Mar, 6 Apr) + B1 (13 Feb).
Unproven; receipts paused.

## 2026-09-30 — 1900-01 SP ballet count: stats 54 (+1 mixed) vs list 55 vs Repertoire 56

Parent-ballet sessions 1900-01 SP with receipts; D3 (1900-12-30) separated; single-session drop tested against the stats
ballet receipts 147,227.86.
Result: the other 55 total 149,818.37 (Δ 2,590.51). 2 Mar 1901 Михайловскій Bénéfice de M-lle Barety (Rosalie / Nos alliées /
Les élèves de Dupré) = 2,590.50, counted under "Французскихъ" by the stats page. D3 has no Repertoire receipts, but the stats
prints 5,043.90 for the РТО mixed performance.

## 2026-09-30 — Ballet completeness, 1906-07 to 1908-09 (stats pages without ballet lists)

Performed sessions 1906-09 per season-city, works classified with compare_season_stats.classify_work; pure ballet vs mixed
with ballet, receipts, receipt-less count; compared with docs/season_stats/lines.csv "Балетныхъ" (+ 1908-09 MSK "Смѣшанныхъ 1").
Then 1907-08 Moscow: sessions with receipts = 758171 (none) and the "Коппелія | оп." session.
Result: 1907-08 SP, 1908-09 SP (41 + 7 Шопеніана bills) and 1908-09 MSK (48 + Нуръ и Анитра/Раймонда) match count and receipts
exactly. 1906-07 SP receipts exact (count 55 vs 53). 1906-07 MSK Repertoire 51 vs 49. 1907-08 MSK 47 vs 48, resolved by 11 Nov 1907
Большой Коппелія "оп." (2,578.77); receipts still 5,002.94 short.

## 2026-09-30 — Issue #119: 1909-10 onboarding, integration-test verification queries

**Confirming zero regression to pre-existing corpus data after merging
1909-10 into a scratch integration DB:**
```sql
-- quality_flags delta
-- current full_run: 900 flags (receipts_parse_failed=13)
-- integration (full_run + 1909-10): 902 flags (receipts_parse_failed=15)
```
Result: +2, exactly the 2 confirmed genuine print typos in 1909-10
(`p016`, `p050`). All other flag categories identical counts.

```sql
select * from (
  select * from research.event where event_id not in
    (select event_id from raw.event_entry where page_id like 'repertoire_1909-10%')
  except select * from prod.research.event
)
```
Result: 0 rows — every pre-existing `research.event` row byte-identical
between current production and the integration build.

```sql
select * from (
  select p.* from research.performance p join research.event e using(event_id)
  where e.event_id not in (select event_id from raw.event_entry where page_id like 'repertoire_1909-10%')
  except select * from prod.research.performance
)
```
Result: 3 differing rows (`repertoire_1895-96_pair024__s024__w2`,
`repertoire_1898-99_p000__s019__w4`, `repertoire_1906-07_p004__s021__w1`)
— each a pre-existing null-genre raw row (confirmed via direct
`raw.event_entry_performance` lookup by `event_id`, not touched by
1909-10) whose canonicalized `work_id`/`canonical_genre` shifted once
1909-10's own correctly-genred appearances of the same 3 titles joined
the corpus-wide majority vote. Traced to completion; not a 1909-10 data
defect. See known_issues.md issue #119 for the full writeup.

Entity counts cross-checked directly (`entities.person`/`research.
person`/`research.person_appearance`: 4359/2894/21154, identical to
current production — Roster untouched since 1909-10 is Repertoire-only;
`entities.work_genre_candidate`: 323 groups unchanged, +74 rows from
new appearances of already-ambiguous titles; `not_captured` gap count:
2976, identical).

## 2026-09-30 — 1906-07 SP drama excess, by theater

```sql
select e.event_id, e.date, t.canonical_name, a.time_of_day, left(a.annotation, 75), e.receipts_total_kopecks,
       list(p.verbatim_title order by p.performance_order), list(coalesce(w.canonical_genre, p.verbatim_genre) order by p.performance_order)
from research.event e join research.theater t using (theater_id) join analysis.event_entry a using (event_id)
left join research.performance p using (event_id) left join research.work w using (work_id)
where e.season = '1906-07' and e.city = 'SP' and e.event_status = 'performed' group by all order by 2
-- classified with compare_season_stats; then Александринскій singles and pairs tested against 2,307.23
```

Result: Михайловскій receipted drama 24 = 10,353.15 (stats exact); extras: Moscow Art Theatre 24 sessions (23 Apr–17 May 1907), 14 Feb
charity, 6 Dec morning. Маріинскій: Стрѣльская benefit 7,262.50 (stats exact); extras: 2 charity operettas + 4 Китежъ (genre-less
opera). Александринскій 198 → 197 after the classifier fix; receipts +2,307.23, no single/pair match. After the fix: 1906-07 SP
drama Alex 197/197, opera 155 + 4 unknown (Китежъ). 1909-10 is now in research.event (added by the other chat); SP drama +60.

## 2026-09-30 — 1907-08 SP drama excess, by theater

Same session query as for 1906-07 (season '1907-08'); drama sessions per theater with receipts; the Александринскій tested
for a single session of 1,575.72. Also read (scan, no SQL): the 1907-08 "Списокъ пьесъ" p. 127 (Petersburg Russian drama,
entries 1–14).
Result: Александринскій 218 (214 receipted, 265,164.75; 4 free/benefit), Маріинскій 6 and Михайловскій 6 charity (no receipts),
Михайловскій spring run 38 (14 Apr–13 May 1908, no receipts). No single Александринскій session = 1,575.72. The list of plays has
none of the run's plays; the company is not named in the materials checked.

## 2026-09-30 — 1908-09 SP drama excess, by theater

Same session query as for 1906-07/1907-08 (season '1908-09'); plus the raw sessions for repertoire_1908-09_p035 "6 Пятница."
(scan checked at 600 dpi).
Result: Александринскій 223 = stats (219 receipted, 281,648.62; 4 free). Михайловскій: Moscow Art Theatre 46 (30 Mar–3 May 1909, no
receipts, named on the scan) + 2 receipted charity benefits (3,225.75; 749.25). Маріинскій: charity operetta + "Черевички, эп,"
(genuine print misprint of "оп."). 273 = 223 + 46 + 2 + 1 + 1.

## 2026-10-01 — Issue #120: re-querying the stale "118-row Гимнъ" figure fresh

Per the mandatory rule (never trust a cached number from a prior turn),
re-ran the population query from issue #104's follow-up before acting
on it -- 4 days and a full season promotion had passed since it was
cached.

```sql
select genre, count(*) from raw.event_entry_performance
where performance_title ilike 'Гимнъ%' group by genre
```
Result: `(NULL, 149)` -- up from the cached 145 (all genre-null,
confirming it's still a genuine performed opener corpus-wide, not a bug
itself).

```sql
select case when ee.annotation ilike '%Гимнъ%' or ee.annotation ilike '%Hymne%' then 'has_gimn_annotation'
            when ee.annotation is null then 'annotation_null' else 'other_annotation' end as bucket, count(*)
from raw.event_entry_performance ep join raw.event_entry ee on ep.event_id = ee.event_id
where ep.performance_title ilike 'Гимнъ%' group by bucket
```
Result: `has_gimn_annotation` 16 (unchanged), `annotation_null` 105
(down from 118 -- some already fixed by concurrent work since), a
previously-unreported `other_annotation` bucket of 28 (sessions with
Гимнъ plus some unrelated annotation, e.g. a personal benefit --
correctly excluded from the sweep's scope, not gaps).

```sql
select ee.page_id, ee.date_text, ee.time_of_day, count(distinct ee.theater), ee.annotation
from raw.event_entry_performance ep join raw.event_entry ee on ep.event_id = ee.event_id
where ep.performance_title ilike 'Гимнъ%'
group by ee.page_id, ee.date_text, ee.time_of_day
```
Result: 48 distinct occasions (not 149 individual rows to check), all
within the 1890-91-1897-98 two-page-spread era, spanning 29 distinct
pages -- this reframing (occasions, not raw rows) is what made a full
scan-verified sweep tractable rather than a shortcut. Dispatched 5
parallel agents, one per ~6-page batch, each checking every theater
performing in every occasion's slot (not only the ones the query
flagged) directly against the scan. Full results and the 1
self-correction found (a wrong annotation from issue #104's own
original sweep) are in known_issues.md issue #120.

Post-fix verification:
```sql
select count(*) from raw.event_entry_performance where performance_title ilike 'Гимнъ%'
```
Result: 160 (149 + 11 genuine missing-work additions found by the
sweep), matching `research.work`'s "Гимнъ" appearance_count exactly
after rebuild.

## 2026-09-30 — 1909-10 SP: stats vs Repertoire, and Latin-titled works with Cyrillic genres

```sql
select e.season, count(*), count(distinct a.page_id) from raw.event_entry_performance p join analysis.event_entry a using (event_id)
join research.event e using (event_id)
where regexp_matches(p.performance_title, '^[\W\d]*[A-Za-zÀ-ÿ]') and regexp_matches(coalesce(p.genre, ''), '[а-яё]') group by 1 order by 1
```

Result: 1909-10 has 46 entries on 6 pages ("ком." 32, "пьеса" 12); other seasons 1–15. The p023 15 Dec 1909 scan shows no Cyrillic genre, so
these were added by the transcription. Recount with Latin titles as foreign: the Art Theatre 35 = stats 35 exactly; French 107/107,172.60 vs
100/107,243.10; ballet 50 vs 51; German 22 vs 25; Russian drama 269 vs 258.

## 2026-10-01 — Issue #121: 1909-10 fabricated Cyrillic genres on Latin-script titles

Relayed by the concurrent Ballet-productions session (their own query,
reproduced here since it's what identified the population):
```sql
select a.page_id, count(*)
from raw.event_entry_performance p join analysis.event_entry a using (event_id)
where a.season = '1909-10'
  and regexp_matches(p.performance_title, '^[\W\d]*[A-Za-zÀ-ÿ]')
  and regexp_matches(coalesce(p.genre, ''), '[а-яё]')
group by 1
```
Result: 46 rows across 6 pages (p013 x1, p023 x10, p025 x8, p027 x10,
p031 x10, p033 x7).

Full detail pulled before fixing:
```sql
select a.page_id, a.date_text, a.time_of_day, a.theater, p.performance_title, p.genre
from raw.event_entry_performance p join analysis.event_entry a using (event_id)
where a.season = '1909-10'
  and regexp_matches(p.performance_title, '^[\W\d]*[A-Za-zÀ-ÿ]')
  and regexp_matches(coalesce(p.genre, ''), '[а-яё]')
order by a.page_id, a.date_text
```
Result: 46 rows, collapsing to 28 distinct (page_id, title, genre)
groups -- all 46 at Михайловскій except 1 at Маріинскій. Personally
scan-verified all 6 pages (not delegated) before fixing -- 100%
consistent, no exceptions found. See known_issues.md issue #121.

Post-fix verification:
```sql
select count(*) from raw.event_entry_performance p join analysis.event_entry a using (event_id)
where a.season = '1909-10'
  and regexp_matches(p.performance_title, '^[\W\d]*[A-Za-zÀ-ÿ]')
  and regexp_matches(coalesce(p.genre, ''), '[а-яё]')
```
Result: 0.

## 2026-09-30 — Issue #121 fixes: production before/after; 1909-10 SP rerun

```sql
select (select count(*) from raw.event_entry), (select count(*) from raw.event_entry_performance),
       (select count(*) from research.work), (select sum(receipts_total_kopecks) from research.event)
```

Result: before (28256, 29565, 3659, 2999154050); after (28256, 29569, 3657, 2999096975); Δ receipts −57,075 kopecks =
−600.75 + 30.00. compare_season_stats.py 1909-10 SP: drama 294 (incl. the Art Theatre 35; 259 vs 258 without it), French 101 vs 100,
German 22 vs 25, ballet 47 vs 51, opera 158 vs 157.

(Note 2026-09-30: the entry above headed "Issue #121 fixes" is issue #122. The Main session had already used #121 for the 1909-10 genre fix.)

## 2026-10-01 — Issue #123 Roster 1908-10: production baseline for the new batch's quality flags

```python
# compared outputs/full_run/quality_flags.csv's flag-type breakdown against the new batch's 3 flag categories
```

Result: production (full_run, pre-this-session) already carries these exact 3 categories at similar proportional
rates: credit_sum_mismatch 285, rank_class_left_in_heading_path 134, duplicate_person_on_page 178,
institution_duplicated_in_heading_path 290 -- known_issues.md documents all 4 as a standing "pre-existing,
out-of-scope" backlog, confirming the new batch's 107 flags aren't a new defect class from onboarding.

## 2026-10-01 — Issue #123: is credit_sum_mismatch's false-positive shape (single-category phrasing) corpus-wide?

```python
# for each production credit_sum_mismatch-flagged entry_id, checked whether its credit_summary_text contains ';'
# (multi-category "N1 cat1—M1; N2 cat2—M2" shape) vs not (single-category "Всего—всѣ N cat—M" shape)
```

Result: of 285 production flags, 265 are multi-category shape (';' present), only 20 single-category. The
single-category false-positive pattern found in this session's batch is NOT simply "most of the corpus's 285" --
needs its own dedicated investigation before touching production; deferred per RG ("just log it for later").

## 2026-10-01 — Issue #123: does production's rank_class_left_in_heading_path backlog use the same 'кл.' shape as the new batch's 40?

```python
# regex-matched the tail of every production-flagged entry's heading_path against r"([IVXLCХ]+\s*кл\.?):?\s*$"
```

Result: all 134 production instances match cleanly (0 non-matches), all using plain "VII кл."-style suffixes with
Latin-letter roman numerals -- confirms the new general repair (_repair_heading_path_rank_class) will clear all 134
on the next full-corpus parse_and_validate.py run, not just the new batch's 40.

## 2026-10-01 — Holistic status summary for RG (morning check-in)

```sql
select count(distinct season) from raw.source_pages;
select count(*) from raw.event_entry; select count(*) from raw.event_entry_performance;
select date_confidence, count(*) from analysis.event_entry_date_check group by 1 order by 2 desc;
select entity_type, count(*) from raw.person_entry group by 1 order by 2 desc;
select count(*) from entities.person where superseded_by_person_id is null; -- live
select count(*) from entities.person where superseded_by_person_id is not null; -- tombstoned
select count(*) from entities.work; select count(*) from entities.person_wikidata_link;
select status, count(*) from entities.person_candidate group by 1;
select count(*) from entities.work_genre_candidate;
select count(*) from research.event; select count(*) from research.performance;
select count(*) from research.person; select count(*) from research.person_appearance;
```

Result: 22 Repertoire seasons, 28256 events / 29569 performances, dates 98.4% verified (27805/28256). Roster:
8523 BalletArtists + 7606 Musicians + 2700 TheaterSchoolStaff + 2003 ProductionTeam + 1841 Administrators + 504
Graduates = 23177 person_entry rows. entities.person 3351 live / 2180 tombstoned; 3657 works; 43 Wikidata links;
person_candidate queue 25 pending / 23 rejected; work_genre_candidate queue 768 rows. research.event 31203,
research.performance 29568, research.person 3345, research.person_appearance 23163. quality_flags.csv 829 rows
(all 4 categories pre-existing/known, see known_issues.md issue #123).

## 2026-10-01 — Issue #124: duplicate_person_on_page corpus-wide sweep setup and verification

```python
# grouped all duplicate_person_on_page flags by page_id/entity_type from quality_flags.csv for sweep planning
# post-fix: re-ran parse_and_validate.py + quality_checks.py, compared flag-type counts before/after
```

Result: 183 flags / 98 pages pre-sweep (TheaterSchoolStaff 122, ProductionTeam 33, Administration 10, Musicians
10, BalletArtists 4, Graduates 4). Post-fix: 179 (4 genuine extraction bugs fixed: Нелидовъ+Бриліантовъ
split-entry merges on administration_1894-95_p002, Бенда death-note reattribution + Гордонъ merge on
musicians_1894-95_MSK_p000). person_entry 23177->23173. All other flag categories and Repertoire-side numbers
unchanged -- see known_issues.md issue #124 for full writeup.

## 2026-10-01 — "What's next for the people entity?" status check

```sql
select status, count(*) from entities.person_candidate group by 1;
select match_reason, count(*) from entities.person_candidate where status='pending' group by 1 order by 2 desc;
select count(*) from entities.person where superseded_by_person_id is null;
select count(*) from entities.person where superseded_by_person_id is not null;
select count(*) from entities.person_wikidata_link;
```

Result: person_candidate 21 pending (18 family_name_variant, 3 patronymic_variant) / 23 rejected. entities.person
3350 live / 2181 tombstoned. entities.person_wikidata_link 43 (a pilot-scale run, not full-corpus).

## 2026-10-01 — Issue #71 promotion: before/after verification

```python
# compared control (no-rename rebuild of current production) vs fixed (remap+rename+rebuild) duckdb copies
# across research.theater/work/event/performance, entities.person live/tombstoned (as sets, not just counts),
# entities.person_link entry_id prefixes, research.person season-field leftover typo tokens
```

Result: control and fixed identical throughout (research.event 31203, research.work 3657, entities.person
3350 live/2181 tombstoned with IDENTICAL tombstoned-id sets). entities.person_link: 0 old-prefix (theaterschool
staff_1899-90_/1905-07_) remaining, 282 new-prefix present. research.person: 0 leftover typo season tokens.
quality_checks.py: 825 flags, same breakdown as pre-fix production. Promoted clean.

## 2026-10-01 — Issue #52 re-verification before deciding a fix

```sql
select page_id, institution, count(*) from raw.person_entry where page_id='administration_1903-04_p003' group by 1,2;
select count(*) from raw.person_entry where institution like '%состоящихъ на службѣ въ Императорскомъ%';
```

Result: unchanged from the original finding — exactly 32 rows on administration_1903-04_p003, all carrying
"Списокъ лицъ, состоящихъ на службѣ въ Императорскомъ Мариинскомъ театрѣ", and this exact phrase occurs nowhere
else in the corpus. Confirms the issue is still live and unchanged before deciding a fix.

## 2026-10-01 — Issue #52 fix survey and verification

```sql
select institution, entity_type, count(*) n, count(distinct page_id) np from raw.person_entry
  where institution is not null and length(institution) > 60 group by 1,2 order by length(institution) desc;
select institution, entity_type, count(*) n, count(distinct page_id) np from raw.person_entry
  where institution like '%(%' and institution not like 'Списокъ%' and institution not like '%Контор%'
  group by 1,2 having count(*) >= 5 order by n desc;
-- post-fix verification:
select count(*) from raw.person_entry where institution like '%Мариинскомъ театрѣ%';
select count(*) from raw.person_entry where institution like '%Завѣдывающій центральною библіотекою%';
```

Result: survey of long/sentence-shaped institution values found one more real bug beyond #52's original 32
(administration_1900-01_p001, 24 entries, a stuck single-person position note instead of the page's real
multi-department structure) -- fixed both. Broader structural heuristic for "fabricated title" pages was too
noisy (matched legitimate document-title pages too, e.g. administration_1890-91_p000) -- not pursued further
this session, logged as a worklist item. Post-fix: 0 instances of either fabricated/stuck phrase remain anywhere
in raw.person_entry.

## 2026-10-01 — person_candidate pending queue, full detail for review

```sql
select candidate_id, display_1, display_2, similarity_score, match_reason, tenure_signal, tenure_evidence
from entities.person_candidate where status='pending' order by match_reason, similarity_score desc;
```

Result: 21 pending pairs (18 family_name_variant, 3 patronymic_variant), all tenure_signal in
(conflicting_dates, no_date_data) -- no matching_dates corroboration available for any of them, so each needs
individual review. Full list pulled for RG's review session; see known_issues.md for decisions as they're made.

## 2026-10-01 — Issue #125: person_candidate review queue, verification queries

```python
# pulled all 21 pending pairs with display names/dates; pulled full raw.person_entry history for each
# surname across all seasons to check corroborating role/date/graduation evidence; post-decision verification
# comparing production against pre-decision backup
```

Result: 7 of 21 resolved as transcription errors (not entity decisions) after zoom-level scan checks; 13
confirmed MERGE, 7 confirmed REJECT, 1 left deliberately pending (Давильеръ/Девильеръ). entities.person
3350->3342 live, all 2181 pre-existing tombstones preserved, 0 orphaned person_link rows, all Repertoire-side
research numbers unchanged. Full writeup: known_issues.md issue #125.

## 2026-10-01 — Issue #46 resumed: heading_path/role_normalized survey scope

```sql
select entity_type, count(distinct role_normalized) n_distinct, count(*) n_total
from analysis.person_entry where role_normalized is not null and role_normalized <> ''
group by 1 order by 1
```

Result: Administrators 262 distinct (1651 rows), BalletArtists 165 (3226), Graduates 14 (485), Musicians 169
(5472), ProductionTeam 219 (1967), TheaterSchoolStaff 179 (2536) -- 1008 distinct role_normalized values total
across 6 entity types. Starting a programmatic near-duplicate-spelling survey (normalized-key clustering) before
hand-reviewing clusters, same approach as the institution field audit (issue #46/#52).

## 2026-10-01 — Stuck heading_path sweep: real heading/institution for 5 pages (musicians_1903-04_SP_p002, musicians_1906-07_MSK_p002, musicians_1906-07_SP_p002, balletartists_1893-94_SP_p006, balletartists_1898-99_SP_p008)

```sql
-- per-season/city: group by page_id, heading_path, institution to find section boundaries
SELECT page_id, heading_path, institution, COUNT(*) AS n
FROM raw.person_entry WHERE page_id LIKE '<prefix>%'
GROUP BY page_id, heading_path, institution ORDER BY page_id;

-- then per page: list_number continuity check
SELECT list_number, family_name, first_name, heading_path, institution
FROM raw.person_entry WHERE page_id = '<page_id>' ORDER BY list_number;

-- exact institution string check (period vs no period)
SELECT DISTINCT institution FROM raw.person_entry WHERE page_id = '<p000 page_id>';
```

Result: confirmed all 5 target pages are mid-list continuation pages (no heading reprinted on the
page itself) whose heading_path/institution are stuck on "Управляющій Училищемъ" /
"Императорское С.-Петербургское Театральное Училище". list_number sequences run unbroken from
each section's genuine start page (p000 for the 3 Musicians pages, p005 for both BalletArtists
pages) through the target page and beyond, with no restart at "1." on the target page, confirming
each target page belongs entirely to one real section, not a mix. Real values (see full report
to RG): musicians_1903-04_SP_p002 = "Оркестръ оперы и балета / Музыканты" / "Оркестры.";
musicians_1906-07_MSK_p002 = "Музыканты" / "Оркестры."; musicians_1906-07_SP_p002 = "Музыканты" /
"Оркестры" (no period, verbatim difference from the other two — confirmed via DISTINCT, not a
display artifact); balletartists_1893-94_SP_p006 and balletartists_1898-99_SP_p008 both =
"Артисты:" / "Балетная труппа." (heading text confirmed directly on the scan of each section's
start page — balletartists_1893-94_SP_p005 and balletartists_1898-99_SP_p005 — institution value
inferred by analogy with the genuine "Артисты:"/"Балетная труппа." pairing on each season's own
p000, since no institution banner is visible on the continuation or start pages themselves).

## 2026-10-01 — Broadened stuck-heading_path scope check (entity-type/content mismatch, not just the 3 original substrings)

```sql
-- Musicians: heading_path containing admin-department language that cannot belong on a Musicians page
SELECT COUNT(*) n, COUNT(DISTINCT page_id) pages FROM raw.person_entry
WHERE entity_type='Musicians' AND (heading_path ILIKE '%полиц%' OR heading_path ILIKE '%артисты балета%'
  OR heading_path ILIKE '%управляющій училищемъ%' OR heading_path ILIKE '%хозяйствен%'
  OR heading_path ILIKE '%врачебн%' OR heading_path ILIKE '%счетн%');

-- BalletArtists: heading_path containing musician/admin language that cannot belong on a BalletArtists page
SELECT COUNT(*) n, COUNT(DISTINCT page_id) pages FROM raw.person_entry
WHERE entity_type='BalletArtists' AND (heading_path ILIKE '%полиц%' OR heading_path ILIKE '%музыкант%'
  OR heading_path ILIKE '%оркестр%' OR heading_path ILIKE '%управляющій училищемъ%'
  OR heading_path ILIKE '%хозяйствен%' OR heading_path ILIKE '%врачебн%' OR heading_path ILIKE '%счетн%');

-- TheaterSchoolStaff: heading_path containing musician/ballet language
SELECT COUNT(*) n, COUNT(DISTINCT page_id) pages FROM raw.person_entry
WHERE entity_type='TheaterSchoolStaff' AND (heading_path ILIKE '%музыкант%' OR heading_path ILIKE '%оркестр%'
  OR heading_path ILIKE '%артисты балета%');

-- Administrators: same check
SELECT COUNT(*) n, COUNT(DISTINCT page_id) pages FROM raw.person_entry
WHERE entity_type='Administrators' AND (heading_path ILIKE '%музыкант%' OR heading_path ILIKE '%оркестр%'
  OR heading_path ILIKE '%артисты балета%');
```

Result: Musicians 1357 rows/39 pages, BalletArtists 283 rows/12 pages, TheaterSchoolStaff 7 rows/2
pages, Administrators 0. Grand total (de-duplicated page_ids): **1647 rows across 53 pages** —
substantially larger than the original narrow-substring detection (954 rows/34 pages, issue #46
follow-up item #1). 36 of the 53 pages are outside the page list already dispatched for scan
verification this session; 5 of those 36 (musicians_1903-04_SP_p002, musicians_1906-07_MSK_p002,
musicians_1906-07_SP_p002, balletartists_1893-94_SP_p006, balletartists_1898-99_SP_p008) already
have confirmed real values logged above from an earlier pass this session. ~31 pages remain
genuinely unverified. A looser version of this query (adding generic "%музыкант%"/"%оркестр%" as
wrong-value indicators for the Musicians entity_type itself) produces 5170 rows/268 pages — mostly
noise, since those words are the CORRECT heading content on most Musicians pages, not a mismatch
signal. Reported to RG for a scope/cost decision before dispatching further verification agents.

## 2026-10-01 — Attempted structural detection of remaining stuck-heading pages (singleton heading/institution pairs)

```sql
with pair_pages as (
    select entity_type, heading_path, institution, page_id, count(*) n
    from raw.person_entry
    where entity_type in ('Musicians','BalletArtists','TheaterSchoolStaff','Administrators')
    group by 1,2,3,4
),
pair_totals as (
    select entity_type, heading_path, institution, count(distinct page_id) n_pages, sum(n) n_rows
    from pair_pages group by 1,2,3
)
select entity_type, heading_path, institution, n_rows
from pair_totals
where n_pages = 1 and n_rows > 8
order by entity_type, n_rows desc
```

Result: 114 (heading_path, institution) pairs that occur on exactly one page_id corpus-wide with
>8 rows. Inspected the list: this signal is too noisy to use directly — most of the 114 are
genuine, legitimate section headers/institution-name spellings that are simply rare (unique per
season/city, or a real one-off subsection), not stuck-value bugs. Distinguishing the two
requires the same scan-verification as the 60 pages already confirmed this session, not a cheap
DB-only heuristic. Concluded that chasing this further converges with the previously-discussed
"full Roster sweep" (see memory) rather than being a quick addition to the current stuck-heading
item; deferred to that future effort rather than expanding the current fix scope again. Current
confirmed scope for this item stands at 60 pages (34 original + 26 broadened-detection
follow-up), all scan-verified with real heading_path/institution values and two-tier exceptions
identified.

## 2026-10-01 — Stuck heading_path fix applied (issue #126), post-fix verification

```sql
-- confirm no remaining stuck-value rows among the 60 touched pages
SELECT COUNT(*) FROM raw.person_entry WHERE page_id IN (<60 page_ids>)
  AND (heading_path ILIKE '%полиц%' OR heading_path ILIKE '%артисты балета%'
       OR heading_path ILIKE '%управляющій училищемъ%' OR heading_path ILIKE '%хозяйствен%'
       OR heading_path ILIKE '%врачебн%' OR heading_path ILIKE '%счетн%');

-- check corpus precedent before applying a tentative institution guess
SELECT heading_path, institution, COUNT(*), COUNT(DISTINCT page_id)
FROM raw.person_entry WHERE heading_path ILIKE '%Александринскаго театра%' GROUP BY 1,2;

-- post-fix identity/tombstone verification (old vs new duckdb)
SELECT person_id FROM entities.person WHERE superseded_by_person_id IS NOT NULL;  -- set-compared
SELECT COUNT(*) FROM entities.person_link pl LEFT JOIN entities.person p ON pl.person_id=p.person_id
  WHERE p.person_id IS NULL;  -- orphan check
```

Result: 0 remaining stuck-value rows across the 60 fixed pages. The Alexandrinsky institution
guess had zero corpus precedent (all 14 other existing instances of that heading paired with
generic placeholders, never with the proposed value) -- reverted before promoting. Post-rebuild:
person_entry 23173 (unchanged), quality_flags 825 (matches pre-sweep baseline exactly), entities
.person 3342 live/2189 tombstoned, tombstone person_id set identical to backup, 0 orphaned
person_link rows, Repertoire-side raw/research counts and receipts_total_kopecks sum byte-
identical. Full writeup: known_issues.md issue #126.

## 2026-10-01 — institution_duplicated_in_heading_path review, 4 assigned pages (musicians_1897-98_SP_p003, productionteam_1896-97_p001, productionteam_1900-01_p002, productionteam_1907-08_p002)

```sql
-- flagged-page row dumps (repeated per page_id)
SELECT entry_id, list_number, family_name, heading_path, institution
FROM raw.person_entry WHERE page_id='musicians_1897-98_SP_p003' ORDER BY entry_id;

-- sibling-series cross-check (p000-p004 of same file, each series)
SELECT DISTINCT page_id FROM raw.person_entry WHERE page_id LIKE 'musicians_1897-98_SP%' ORDER BY page_id;
SELECT entry_id, list_number, family_name, heading_path, institution
FROM raw.person_entry WHERE page_id IN ('musicians_1897-98_SP_p000','musicians_1897-98_SP_p001','musicians_1897-98_SP_p002') ORDER BY entry_id;

SELECT DISTINCT page_id FROM raw.person_entry WHERE page_id LIKE 'productionteam_1896-97%' ORDER BY page_id;
SELECT entry_id, list_number, family_name, heading_path, institution
FROM raw.person_entry WHERE page_id IN ('productionteam_1896-97_p000','productionteam_1896-97_p001') ORDER BY entry_id;

SELECT DISTINCT page_id FROM raw.person_entry WHERE page_id LIKE 'productionteam_1900-01%' ORDER BY page_id;
SELECT entry_id, list_number, family_name, heading_path, institution
FROM raw.person_entry WHERE page_id IN ('productionteam_1900-01_p000','productionteam_1900-01_p001','productionteam_1900-01_p002') ORDER BY entry_id;

SELECT DISTINCT page_id FROM raw.person_entry WHERE page_id LIKE 'productionteam_1907-08%' ORDER BY page_id;
SELECT entry_id, list_number, family_name, heading_path, institution
FROM raw.person_entry WHERE page_id IN ('productionteam_1907-08_p000','productionteam_1907-08_p001','productionteam_1907-08_p002') ORDER BY entry_id;
```

Result: cross-checked against full-res scans (outputs/roster_images_full/images/*.png) page by
page. musicians_1897-98_SP_p003: the 42 bare "Музыканты:"=="Музыканты:" rows (e001-e042) are a
genuine bug — scan shows the preceding page (p002/printed p.73) ends with the heading "Оркестръ
Александринскаго театра." followed by "Капельмейстеръ"/Галкинъ, and p003 opens directly with the
repeated running sub-head "Музыканты:" for that same orchestra's continuing roster — the real
institution ("Оркестръ Александринскаго театра.") was dropped on page-break. The other 9 rows on
that page (Оркестръ Михайловскаго театра. / Капельмейстеръ and /Музыканты:) are fine as-is,
confirmed by direct parallel structure on the same page. productionteam_1896-97_p001: 12 of 27
flagged rows (mechanist/lighting/props sections, bare duplicates) are a bug — p000 of the same
document establishes institution="С.-ПЕТЕРБУРГЪ." (the document title) uniformly across every
department, and p001 is a page-break continuation of that same document with no new title;
institution should be "С.-ПЕТЕРБУРГЪ." The remaining 15 rows (Отдѣлъ гардеробный sub-sections)
are fine as-is — department-level truncation, consistent with the issue #52 convention.
productionteam_1900-01_p002: all 21 flagged rows are fine as-is, including the 2 bare
"Французская труппа"=="Французская труппа" rows — scan confirms no deeper venue subdivision was
ever printed for the French troupe's hairdressers (unlike the opera/ballet/Russian-drama troupes
on the same page, which do subdivide by theater), so the troupe name is genuinely the full,
correct institution value there. productionteam_1907-08_p002: both flagged rows are a bug, but
not in isolation — institution='Михайловскій театръ' is stuck/constant across all 20 rows on this
page (confirmed directly: rows e014/e015/e017/e018 explicitly describe Маріинскій and
Александринскій театръ staff yet still carry institution='Михайловскій театръ', an internal
contradiction), carried over incorrectly from the page's first entry. The 2 flagged rows only
coincidentally textually match their own heading's trailing venue segment. By cross-page
convention (productionteam_1900-01_p002 pairs the identical "Мѣстные гардеробы / Гардеробмейстеры
(-рши) / <theater>" heading with institution="Мѣстные гардеробы"), the real institution for both
flagged rows, and for the other 18 unflagged-but-equally-wrong rows on this page, should be
"Мѣстные гардеробы" / "Отдѣлъ гардеробный" / "Главный гардеробъ" per sub-section (not any single
theater name) — flagged as a broader page-wide data-quality issue beyond the 2 rows originally
in scope.

## 2026-10-01 — Item #2: institution_duplicated_in_heading_path review (issue #127), fix applied + verified

Result: all 290 flags across the 12 flagged pages reviewed (3 parallel agents, same scan +
same-file-convention discipline as issue #126). 219 rows were genuine bugs (overarching
institution/document title dropped at a page break, replaced by the narrow sub-heading in both
fields); 71 were confirmed fine-as-is (a genuine, accepted department-level truncation, same
shape as issue #52's precedent). Applied the 219 fixes directly to `outputs/full_run/raw/*.raw.json`.
One apparent residual-flag anomaly investigated and resolved: `productionteam_1895-96_p001__e007`
is governed by a pre-existing hard-coded `_MISATTACHMENT_FIXES` entry in `parse_and_validate.py`
(from an earlier session) that unconditionally restores its correct, scan-verified values every
parse — my raw-JSON edit to that one row was harmless but moot; confirmed via a full scan of both
`_MISATTACHMENT_FIXES` and `_HEADING_PATH_RESTORE_FIXES` for any other overlap with either this
item's or issue #126's touched pages (one overlap found, this one, already resolved correctly).
Post-rebuild: person_entry 23173 unchanged, entities.person 3342 live/2189 tombstoned (tombstone
SET identical to backup), 0 orphaned person_link, Repertoire-side counts and receipts sum byte-
identical. Backup at `outputs/full_run_pre_promote_backup_2026-10-01_institutiondup/`. Full
writeup: known_issues.md issue #127.

## 2026-10-01 — Item #3: Alexandrinsky theater naming, fresh full-corpus spelling survey

```sql
SELECT page_id, entry_id, heading_path, institution FROM raw.person_entry
WHERE heading_path ILIKE '%александр%театр%' OR institution ILIKE '%александр%театр%'
   OR heading_path ILIKE '%александр%скаго%' OR institution ILIKE '%александр%скаго%';
```
(then regex-extracted every `Александр...ск...` token from heading_path/institution and tallied)

Result: 919 total rows reference the theater. Dominant/correct forms: "Александринскаго" (674),
"Александринскій" (155) = 829 (90.2%). Four non-standard variants found, more than the "7 vs 3
instances" the original item framing described: "Александрийскаго" (79), "Александрийскій" (17),
"Александриискій" (14), "Александрійскій" (7), "Александри́нскій" (5, with a stray Unicode
combining-acute-accent mark), "Александриискаго" (3) -- 125 total non-standard instances, spread
across many distinct pages/seasons (not isolated to one volume), suggesting OCR/transcription
noise rather than genuine period variation for a single well-known theater's name. Scan-sampling
each variant class next before concluding anything is a real bug vs. genuine print variation.

## 2026-10-01 — Item #3: Alexandrinsky naming fix applied + verified (issue #128)

Result: scan-confirmed (3 independent samples across Musicians/ProductionTeam, 3 different years)
that "Александрийскій/-аго", "Александриискій/-аго", and "Александри́нскій" (stray combining
accent) are all pure transcription noise -- the scans plainly and consistently print the standard
"Александринскій/Александринскаго". Applied a corpus-wide string-normalization across all 4
non-standard spelling patterns: 121 replacements across 18 raw JSON files. Separately, chasing the
"Александрійскій" (і-variant, 7 instances, all on administration_1902-03_p004) led to a deeper
discovery: that page's heading_path for e001-e026 (both the "Маріинскій театръ" AND
"Александрійскій театръ" labeled rows) is entirely fabricated -- cross-year exact-name match
against administration_1904-05_p004 (same 24 names in the same order under heading_path =
"Чиновники X класса") proves e001-e026 is really one uniform "Чиновники X класса" (Class-X civil
officials) list with no theater-level subdivision at all. Fixed heading_path for all 26 entries.
Found but NOT fixed (logged as a worklist item): productionteam_1892-93_p001__e001-e009 shows the
same stuck/fabricated-heading bug (names exactly matching productionteam_1891-92_p000's "Помощники
декораторовъ" continuation, mislabeled "Хозяйственное отдѣленіе / Полиціймейстеры / Маріинскій
театръ") -- same bug class as issue #126, outside this item's narrower scope, needs its own
list_number-continuity verification pass.

Post-rebuild: person_entry 23173 unchanged, quality_flags institution_duplicated_in_heading_path
74->75 (+1, a harmless newly-coincidental truncation match, same accepted pattern as issue #127),
entities.person 3342 live/2189 tombstoned identical, 0 orphaned person_link, Repertoire-side counts
and receipts_total_kopecks sum byte-identical. 0 non-standard Alexandrinsky spellings remain
corpus-wide. Backup at `outputs/full_run_pre_promote_backup_2026-10-01_alexandrinsky/`. Full
writeup: known_issues.md issue #128.

## 2026-10-01 — Worklist cleanup: 4 items from issues #126-128 resolved (issue #129)

Result: all 4 logged-but-not-acted-on items from today's earlier passes resolved:
(1) `productionteam_1892-93_p001__e001`-`e009`: scan+list_number continuity confirmed these are
the direct continuation of `p000`'s "Отдѣлъ декораціонный / Помощники декораторовъ" list (#7
Ламбинъ -> #8 Ланге, no restart) -- heading_path fixed, institution already correct/unchanged.
(2) `productionteam_1907-08_p002` (18 more rows beyond the 2 already fixed) and
`productionteam_1899-00_p002` (same pattern): scan-read both pages directly, confirmed the
institution should be the printed department header ("Отдѣлъ бутафорскій."/"Отдѣлъ гардеробный."/
"Главный гардеробъ."/"Мѣстные гардеробы.") rather than a single stuck theater name -- fixed per-
subsection on both pages (1 row deliberately left untouched on 1899-00_p002, ambiguous evidence).
(3) `musicians_1907-08_SP_p003__e024`-`e037`: the institution value reverted during issue #126 is
now resolved using direct scan evidence already in hand from issue #128's investigation (the same
theater's orchestra roster, scanned 3 years earlier, shows institution = "Оркестръ
Александринскаго театра." for this exact heading) -- applied.

Post-rebuild: person_entry 23173 unchanged, quality_flags 608 (institution_duplicated_in_heading_
path 75->73), entities.person 3342 live/2189 tombstoned identical, 0 orphaned person_link,
Repertoire-side counts and receipts_total_kopecks sum byte-identical. Backup at
`outputs/full_run_pre_promote_backup_2026-10-01_worklist/`. Full writeup: known_issues.md issue
#129.

## 2026-10-02 — productionteam_1907-08_p002 e007/e008 heading_path shift fixed (addendum to issue #129)

```sql
SELECT entry_id, family_name, heading_path FROM raw.person_entry
WHERE page_id='productionteam_1907-08_p002' AND entry_id LIKE '%e00_' ORDER BY 1;
```

Result: scan (p.61) prints, under Парикмахеры -> "Русская драматическая труппа.", Педдеръ under
"Александринскій театръ." and Шляпниковъ under "Михайловскій театръ.". The DB had e007 with no
theater segment and e008 labeled Александринскій (shifted one row). Fixed both to the four-level
form used on sibling pages (e.g. productionteam_1904-05_p002). Post-rebuild: person_entry 23173,
quality_flags 608 (unchanged), entities.person 3342 live/2189 tombstoned (tombstone set identical),
0 orphaned person_link, receipts_total_kopecks sum identical.

## 2026-10-02 — Musicians sweep: opera-orchestra heading forms by season/city (RG: "across seasons or one season?")

```sql
SELECT regexp_extract(page_id,'musicians_([0-9]{4}-[0-9]{2})',1) s, regexp_extract(page_id,'_(MSK|SP)_',1) c,
       heading_path, count(*) FROM raw.person_entry
WHERE entity_type='Musicians' AND (heading_path ILIKE '%оперн%' OR heading_path ILIKE '%оркестр% оперы%' OR heading_path ILIKE '%оркестр оперы%')
GROUP BY 1,2,3 ORDER BY 1,2,4 DESC;
```

Result: spans many seasons, not one. 1890-91 to 1892-93 print "Оперный оркестръ" (MSK rows store
"Оперный оркестр." x87 / "Оперный оркестръ." x35; 1890-91 MSK has both forms; SP stores "Оперный
оркестръ" x65; 1892-93 SP also "Списокъ артистовъ опернаго оркестра" x47, a stuck-heading case).
From 1893-94 the printed wording becomes "Оркестръ оперы и балета": SP stores it with ъ
throughout (379 rows, 1893-94..1909-10); MSK 1894-95, 1896-97, 1897-98 store "Оркестр оперы и
балета." without the ъ (114 rows) plus 13 without the trailing period. The dropped ъ occurs only in
the Moscow series (216 rows, 1890-98).

## 2026-10-02 — Musicians full sweep (issue #130), setup + wave 1 applied

```sql
-- scope
SELECT count(*), count(distinct page_id) FROM raw.person_entry WHERE entity_type='Musicians';
-- opera-orchestra heading forms by season/city (see entry above)
-- post-fix check on the 30 wave-1 pages
SELECT institution, count(*) FROM raw.person_entry WHERE page_id IN (<30 pages>) GROUP BY 1;
SELECT count(*) FROM raw.person_entry WHERE page_id IN (<30 pages>) AND (institution ILIKE '%Ежегодникъ%'
  OR institution ILIKE '%theatры%' OR institution ILIKE 'Списокъ%' OR institution ILIKE '%Училище%'
  OR heading_path ILIKE '%Артисты%' OR heading_path ILIKE '%Ударные инструменты%');
```

Result: Musicians = 7,604 rows / 215 pages; 43 already verified (#126), 172 swept in tiered order
(A 109, B 12, C 51 pages) by 6-page report-only agents in waves of 5. Wave 1 (30 pages, Tier A,
1890-91 through 1895-96): all 30 pages needed fixes; 1,228 entries edited (heading_path and/or
institution), 5 junk list_number values nulled. Post-fix: 0 bad tokens on the 30 pages; institutions
are now Оркестры. (1061), Михайловскаго (142), Александринскаго (131), Малаго (58) театра., library (1).
Parser side effects handled: 257 instruments that had been recovered from the old (instrument-shaped)
heading_path were written into the raw `instrument` field so they survive; the hard-coded
_HEADING_PATH_RESTORE_FIXES entry for musicians_1890-91_SP_p004 removed (it would have re-stamped
instrument names as headings). Column diff old vs new parsed person_entry: only heading_path,
institution, list_number changed.

## 2026-10-02 — Musicians sweep wave 2 applied (issue #130)

Result: 30 more Tier A pages (1895-96 to 1900-01) fixed, 1,025 entries edited, 2 junk list_numbers
nulled; 39 instruments preserved via the raw instrument field (musicians_1898-99_MSK_p001). Column
diff of parsed person_entry: only heading_path (943), institution (983), list_number (2) changed.
Post-fix bad-token check on the 30 pages: 2 rows, both the deliberately deferred librarian rows
(musicians_1899-00_SP_p006 e014 "Ежегодникъ...", musicians_1898-99_SP_p006 e030 "Училище"); the
third librarian row (musicians_1897-98_SP_p004 e035) still holds "Центральная Музыкальная
Библиотека". Flags 608, entities.person 3342 live/2189 tombstoned (set identical), 0 orphans,
Repertoire receipts sum identical. Backup: outputs/full_run_pre_promote_backup_2026-10-02_musicians_wave2/.

## 2026-10-02 — Musicians sweep wave 3 applied + musicians_1897-98_MSK_p002 recovered (issue #130)

Result: wave 3 (30 Tier A pages, 1901-02 to 1905-06): 30/30 needed fixes, 879 entries edited, 3 junk
list_numbers nulled, 26 missing instruments set from the scans (musicians_1901-02_SP_p006 e001-e014,
musicians_1903-04_SP_p006 e001-e012), 72 instruments preserved via the raw instrument field. Column diff
of parsed person_entry: only heading_path (737), institution (879), list_number (4), instrument (26, intended)
changed. musicians_1897-98_MSK_p002: re-ran the vision extraction (pipeline/extract.py, qwen3-vl-plus; the
original run had returned 197 output tokens = one row), checked by an agent line-by-line against the scan
at 3-8x zoom (9 corrections: Путкамеръ, Рамбоусекъ, Гешеліовичъ, Ицхекъ-Мейеръ, Цыбинъ, Чіарлоне, tenure day),
heading Оркестр оперы и балета. Музыканты: / Оркестры. set per list-continuity (73-123 continue p001's 20-72),
Арендсъ kept at index 1 so its entity link keeps its entry_id. person_entry 23173 -> 23224 (+51). The 51 new
entries link to 52 live persons; 50 new person records were auto-merged into existing same-name persons
(tombstones 2189 -> 2239, all 2189 old tombstones preserved), live persons 3342 -> 3343. Receipts sum and
Repertoire counts identical, orphans 0, flags 608. Deferred library rows left untouched (4 more). Backup:
outputs/full_run_pre_promote_backup_2026-10-02_musicians_wave3/.

## 2026-10-02 — Musicians sweep wave 4 applied (issue #130)

Result: wave 4 (31 pages: 24 Tier A + 7 Tier B; 30 edited, 1 deferred) fixed: 972 entries edited, 101 instruments
preserved via the raw instrument field. Column diff of parsed person_entry: only heading_path (941) and institution
(560) changed after two parser interactions were handled: (a) musicians_1906-07_MSK_p003 e018 Сиборъ -- the old raw heading
"Скрипка. Солистъ балета." had been split by the parser into instrument + rank_or_title title; the new heading dropped the
title, so rank_or_title "Солистъ балета." was written into the raw entry (RG flagged this person for a later cross-corpus
check); (b) _HEADING_PATH_RESTORE_FIXES entry for musicians_1894-95_MSK_p003 removed (it pinned the Малый block to
"Оркестръ Малаго театра / Музыканты" instead of rule-3 "Музыканты" + institution "Оркестръ Малаго театра."). 1908-10 pages:
heading-only fixes, institutions left as stored per RG's "keep verbatim institutions" (series-level question logged).
Post-fix: flags 608, entities.person 3343 live / 2239 tombstoned (set identical to pre-wave), orphans 0, Repertoire receipts
sum identical; 3 bad-token rows remain = deferred librarian rows. Backup: outputs/full_run_pre_promote_backup_2026-10-02_musicians_wave4/.

## 2026-10-02 — Musicians sweep wave 5 applied (issue #130)

Result: wave 5 (30 Tier C pages, mostly p000 list-start pages, 1890-91 to 1900-01): 11 pages needed changes,
215 entries edited, 3 junk list_numbers nulled, 13 instruments preserved via the raw instrument field. Column diff of
parsed person_entry: only heading_path (185), institution (112), list_number (3) changed. Real errors found: the
Малый/Александринскій labels stamped on the wrong rows (1892-93 MSK p003, SP p004), a sub-heading copied into
institution (1897-98 MSK p003), an instrument word as heading (1893-94/1894-95 MSK p000 Бенда), 1898-99 SP p000 Репетиторы
rows under the military-band heading, and the "Завѣдывающій ..." tier carried onto every row of three Moscow p000s
(1893-94, 1895-96, 1896-97). The other 19 pages were correct as stored. Post-fix: flags 608 -> 599
(institution_duplicated_in_heading_path 73 -> 64, theater names no longer repeated in headings), entities.person 3343
live / 2239 tombstoned (set identical), orphans 0, receipts sum identical, 2 bad-token rows = deferred library rows.
Backup: outputs/full_run_pre_promote_backup_2026-10-02_musicians_wave5/.

## 2026-10-02 — Musicians sweep wave 6 applied; sweep complete (issue #130)

Result: wave 6 (21 last Tier C pages): 5 pages changed, 63 entries edited, 2 junk list_numbers nulled; column diff only
heading_path (4), institution (59), list_number (2). Fixes: Александринскаго rows stamped Михайловскаго (1905-06 SP p005), missing
institution period on the Александринскаго block (1904-05 SP p004), "Настройщики" heading (1904-05 MSK p000), the ballet-men tail
headed "Оркестры" (1909-10 MSK p000 e027-e028 -> "Артисты"), 1909-10 SP p000 Малько under Капельмейстеры балета. Post-fix: flags 599,
entities.person 3343 live / 2239 tombstoned (set identical), orphans 0, receipts sum identical. Backup:
outputs/full_run_pre_promote_backup_2026-10-02_musicians_wave6/.
SWEEP TOTALS: all 172 unverified Musicians pages scan-verified by report-only agents (29 agents, 6 waves); 136 pages edited
(~4,380 entries across heading_path/institution/list_number plus 26 missing instruments), plus musicians_1897-98_MSK_p002
re-extracted (+51 rows). The other 36 pages were correct as stored (modulo deferred cosmetic/secondary items).

## 2026-10-02 — Library-row institution survey (for RG's decision)

```sql
SELECT season, city, page_id, entry_id, family_name, heading_path, institution FROM raw.person_entry
WHERE entity_type='Musicians' AND (heading_path ILIKE '%библіот%' OR heading_path ILIKE '%библиот%'
   OR institution ILIKE '%библіот%' OR institution ILIKE '%библиот%') ORDER BY 1,2,3,4;
```

Result: 53 library-related rows (Moscow: Фарскій, Орловъ, Львовъ, Миролюбовъ, Адельгеймъ; St. Petersburg: Тильпъ, Новоселовъ,
Христофоровъ, Альбрехтъ/Кучера as inspectors; one Moscow drama "Библіотекарша"). Institution values: "Музыкальная библіотека." 14,
"Оркестры." 11, "Императорское С.-Петербургское Театральное Училище" 11, "Списокъ лицъ, состоявшихъ на службѣ въ Императорскихъ театрахъ" 5,
"Оркестръ Малаго театра." 3, "Центральная Музыкальная Библиотека" 3 (+1 with і), "Ежегодникъ Императорскихъ театровъ" 2,
"Музыканты:" 1, "Списокъ музыкантовъ" 1, "МОСКВА. Русская драматическая труппа." 1 (drama librarian, unrelated).

## 2026-10-02 — Missing conductor rows inserted (issue #130 secondary batch 1)

Result: 14 printed, unnumbered theater-orchestra conductor rows were absent from the data (Богуславъ MSK 1890-91 p004; Рамзе SP 1890-91
p005; Арендсъ MSK 1893-94 p003 and 1898-99 p003; Галкинъ SP 1898-99 p004 and 1903-04 p003; Келеръ SP 1899-00/1900-01/1901-02 p005; Шульцъ MSK 1900-01
p004, 1901-02 p004, 1903-04 p003, 1904-05 p003, 1906-07 p004). An agent re-read each conductor line on the scan at 2.5-4x
(findings: /tmp/conductors/findings.json, ephemeral) and confirmed none existed in the DB and none carries a list number. Rows were appended at the end of
each page's raw entries (not in print position) so no existing entry_id shifts -- person_link is keyed by entry_id. person_entry 23224 -> 23238
(+14, no existing row changed). All 14 link to existing live persons (no new person records survive: 6 Tier-1 records were auto-merged,
tombstones 2239 -> 2245, all prior tombstones preserved; live persons 3343 unchanged); flags 599, receipts sum identical.
Backup: outputs/full_run_pre_promote_backup_2026-10-02_conductors/.

## 2026-10-02 — Library-row institution decision applied (issue #130 secondary batch 2)

Decision (RG): institution comes from the section title ("Оркестры."); heading_path reflects the subsection, e.g. "Музыкальная библіотека / Библіотекарь".
Result: 41 institution values and 18 heading_path values changed on 52 Musicians library rows (Moscow Фарскій/Орловъ/Львовъ/Миролюбовъ/Адельгеймъ 1890-91..1907-08;
St. Petersburg Новоселовъ/Тильпъ 1896-97..1907-08) -- every row now has institution "Оркестры." (43) or the series' own no-period form "Оркестры" (9; 1896-97 SP,
1898-99 MSK, 1903-04 and 1904-05 MSK, 1906-07 SP); Moscow headings are role-only rows prefixed with "Музыкальная библіотека / " and the two period variants ("Музыкальная
библіотека. /") normalized to the no-period form; truncated St. Petersburg headings ("Старшій библіотекарь") extended to the printed phrase "Старшій библіотекарь Центральной Музыкальной
Библіотеки." No other column changed (person_entry 23238 rows, flags 599, tombstone set identical, orphans 0, Repertoire receipts sum identical). The first pass missed two rows whose
heading lacked the keyword (Орловъ "Помощникъ его" 1900-01/1901-02) and one with "Бібліотеки" (1898-99 SP p006 e030); all three fixed. Backup:
outputs/full_run_pre_promote_backup_2026-10-02_library/.

## 2026-10-02 — 1908-10 running-head institutions normalized (issue #130 secondary batch 3)

Decision (RG, following the library rule): institution = the section title "Оркестры."; the printed page-top running head ("ПЕТЕРБУРГСКІЕ/МОСКОВСКІЕ ОРКЕСТРЫ.", also stored
lowercase in places) is a page header, not a section title -- city is already in page_id / source_pages.
Result: 464 orchestra rows on musicians_1908-09_* and musicians_1909-10_* changed from the running head to "Оркестры." (1908-09 MSK p001-p003 103, SP p001-p003 105;
1909-10 MSK p000-p003 119, SP p000-p004 ... ); 16 non-orchestra rows keep the stored value (1908-09 MSK p000 e001-e007 ballet tail, 1908-09 SP p000 e001-e003 and 1909-10 SP p000 e012-e015
French-troupe actors, 1909-10 MSK p000 e027-e028 ballet tail) pending the row-removal decision; the Moscow drama rows ("МОСКВА...") untouched. Side effect handled: 1909-10 headings began with the
section title ("Оркестры. / Музыканты:", "Оркестры / Музыканты"), which now duplicated the institution (131 new institution_duplicated_in_heading_path flags); that redundant prefix was stripped
from 250 heading_path values (1909-10 only), returning flags to 599. Column diffs: batch 3a institution only (464), 3b heading_path only (250). Remaining cosmetic: trailing colons split
role_normalized ("Музыканты:" 127 vs "Музыканты" 119). Tombstone set identical, orphans 0, receipts sum identical. Backup: outputs/full_run_pre_promote_backup_2026-10-02_runninghead/.

## 2026-10-02 -- Issue #130 row removals: are the Moscow ballet/orchestra page pairs true duplicates, and did person identity survive?

```sql
-- pair overlap + person_link agreement (1908-09 and 1909-10), then post-rebuild identity check
select m.entry_id, m.list_number, m.family_name, b.entry_id, lm.person_id=lb.person_id
from raw.person_entry m join raw.person_entry b on b.page_id=? and b.list_number=m.list_number and b.family_name=m.family_name
left join entities.person_link lm on lm.entry_id=m.entry_id left join entities.person_link lb on lb.entry_id=b.entry_id where m.page_id=?;
select family_name from raw.person_entry where family_name in ('Terrier','Valbel','Violette','Perret') and entry_id like '%190%';
```

Result: all 26 (1908-09) and 28 (1909-10) rows on each Musicians page matched a BalletArtists row on the same person; French-troupe rows appear only on the Musicians pages. After removing 54 rows
and remapping person_link: live persons 3343, tombstone set identical (2245), orphan links 0, 19/19 renumbered links unchanged, receipts sum 2999096975 unchanged, quality flags 599.

## 2026-10-02 -- Issue #130: French-troupe rows on Musicians SP pages -- do the persons appear anywhere else; verify e035 note on scan

```sql
select e.entry_id,e.family_name,e.first_name,pl.person_id from raw.person_entry e left join entities.person_link pl using(entry_id)
where e.family_name in ('Terrier','Valbel','Violette','Perret') order by 1;
select entry_id,family_name,tenure_note_text from raw.person_entry where tenure_note_text ilike '%Переведен%' or family_name ilike 'Переведен%';
```

Result: the four persons appear only on musicians_1908-09_SP_p000 / musicians_1909-10_SP_p000 (7 entries, 4 person_ids). 118 entries carry "переведен" in tenure_note_text (convention: note folded
into the person's own tenure note); 1 row had it as family_name (the stray 1908-09 SP p002 e035). Scan check: note is printed under no. 70 Мнацагановъ. After rebuild: 23176 entries, live persons 3338,
tombstones identical (2245), orphans 0, flags 599, receipts sum 2999096975 unchanged.

## 2026-10-02 -- Issue #130 dropped identity notes: which Musicians rows carry a printed left-service/death note without a service end?

```sql
select e.entry_id,e.list_number,e.family_name,e.tenure_note_text,s.end_date_text,s.end_type
from raw.person_entry e left join raw.person_entry_service s using(entry_id)
where e.page_id like 'musicians_%' and (e.tenure_note_text like '%Оставил%' or e.tenure_note_text like '%†%')
  and not exists (select 1 from raw.person_entry_service s2 where s2.entry_id=e.entry_id and s2.end_date_text is not null and s2.end_date_text<>'');
```

Result: 3 rows after the batch (Плацатка 1897-98, Барсукъ-Самборскій 1903-04, Новоселовъ 1906-07). Two fixed (end dates set from the scan); Новоселовъ's lone "†" left (see known_issues #130 batch 6).
Final state: musicians end_type counts None 7083 / left service 329 / died 72 / other 41; 23176 entries; live persons 3338; tombstones identical (2245); orphan links 0; flags 599; receipts sum 2999096975.

## 2026-10-02 -- Issue #130 batch 7: global entity-link name-consistency check; month-spelling modernization census

```sql
-- links whose entry family name disagrees with the linked person's canonical family name (first 4 letters, normalized)
select l.entry_id,e.family_name,p.canonical_family_name from entities.person_link l join raw.person_entry e using(entry_id) join entities.person p on p.person_id=l.person_id;
-- month words modernized in Musicians dates (regexp_matches, NOT the ~ operator which is a full match in DuckDB)
select count(*) from raw.person_entry where entry_id like 'musicians_%' and regexp_matches(tenure_note_text,'(^|[^і])ию[нл]');
```

Result: 526 of 23176 links name-mismatched (many legitimate spelling variants; real shifted blocks on musicians_1891-92_MSK_p003 28, administration_1895-96_p001 27, administration_1894-95_p002 19, musicians_1894-95_MSK_p000 15,
theaterschoolstaff_1896-97_p000 11 -- predating 2026-10-01). Month census before fixes: 2 note texts + 3 service dates with "июл/июн", 8 with dropped-і "юня", 6 with "апреля": all corrected against the scans.
Final: person_entry 23178, live persons 3338, tombstones 2245 identical, orphans 0, flags 599, receipts sum 2999096975.

## 2026-10-02 -- Issue #130 batch 8: classify Musicians transfer/appointment notes by direction and what end data they carry

```sql
select e.entry_id,e.tenure_note_text,list({'e':s.end_date_text,'t':s.end_type} order by s.period_order)
from raw.person_entry e left join raw.person_entry_service s using(entry_id)
where e.entry_id like 'musicians_%' and regexp_matches(e.tenure_note_text,'(?i)переведен|назначен') group by 1,2;
```

Result: 114 entries (65 transfer-out-looking, 30 in, 12 change, 7 appointment by the first-pass regexes; hand-corrected). Before: out = 24 other / 19-22 left service / 7+ none; in/change/appointment: 17 carried a spurious end. After applying
RG's rule: all transfer-out rows with a printed date are end_type "other"; in/change/appointment rows have no end. Final: person_entry 23176, live persons 3336, tombstones 2245, orphans 0, flags 599, receipts sum 2999096975.

## 2026-10-02 -- Issue #130: structure of the remaining Moscow drama-troupe block on Musicians SP p004 pages

```sql
-- raw JSON scan of musicians_1908-09_SP_p004 and musicians_1909-10_SP_p004: first index whose institution contains МОСКВ, and whether every later row is drama-troupe
select count(*) from raw.person_entry where family_name=? and first_name=?;   -- per removed row, other corpus entries with the same name
```

Result: both blocks were entirely trailing (1908-09: 8 rows from e017; 1909-10: 5 rows from e022), all "МОСКВА. Русская драматическая труппа". After removal: person_entry 23163, live persons 3327, tombstones 2245, flags 598.

## 2026-10-02 -- Issue #131: shifted person_link blocks; tenure-start consistency of affected persons

```sql
-- name-consistency of every link (done in pipeline/check_person_link_alignment.py)
select l.entry_id,e.family_name,p.canonical_family_name from entities.person_link l join raw.person_entry e using(entry_id) join entities.person p on p.person_id=l.person_id;
-- start-date agreement across a person's entries
select e.entry_id,s.start_date_text from raw.person_entry e join raw.person_entry_service s using(entry_id) where s.period_order=1;
```

Result: 230 name-mismatched links on 71 pages; 6 shift blocks (5 pages) found by the new check. After relinking 92 entries on 4 pages: those pages 0 mismatches; affected persons with inconsistent first-period start dates 90 -> 21; shift blocks left: 1 (theaterschoolstaff_1896-97_p000, out of scope).
Final: live persons 3326, tombstones 2246, orphans 0, receipts sum 2999096975, flags 598.

## 2026-10-02 — Конскій Григорій: tenure start across years (issue #130 date digit check, 1891-92 MSK p001 e011)

```sql
select page_id,entry_id,family_name,first_name,tenure_note_text from raw.person_entry where family_name like 'Конск%' and first_name like 'Григор%' order by page_id
```

Result: see below in the issue #130 date-check entry.
Result (completing the entry above): `musicians_1890-91_MSK_p001__e027` "(съ 28 іюля 1862 г.)" and `musicians_1891-92_MSK_p001__e011` "(съ 28 іюля 1852 г.)" -- the 1891-92 print's third digit is physically damaged, the 1890-91 print is clearly 1862; stored start corrected to 1862 (known_issues #130 batch 9).

## 2026-10-02 -- Лиръ / Шмукловскій / Пащеевъ: tenure start and patronymic across years (issue #130 batch 9 date checks)

```sql
select page_id,entry_id,family_name,first_name,patronymic,tenure_note_text from raw.person_entry where family_name like 'Шмукловск%' order by page_id;
select page_id,entry_id,family_name,first_name,tenure_note_text from raw.person_entry where family_name='Лиръ' order by page_id;
select page_id,family_name,first_name,patronymic,tenure_note_text from raw.person_entry where family_name like 'Пащее%' order by page_id;
```

Result: Лиръ prints "съ 1 октября 1898 г." in 10 of 11 seasons (1904-05 stored "2" from a damaged glyph); Шмукловскій prints 16/26 августа 1904 in six seasons (1905-06 stored 1901 from a damaged last digit); Пащеевъ Борисъ, same start 16 декабря 1893 in all 15 seasons, patronymic alternates Ѳедоровичъ (8) / Ѳедотовичъ (7) -- both verified as printed.

## 2026-10-02 -- Musicians instrument values after the name audit (issue #130 batch 9)

```sql
select instrument,count(*) n from raw.person_entry where page_id like 'musicians_%' group by 1 order by n desc;
select family_name,count(*) from raw.person_entry where page_id like 'musicians_%' and (regexp_matches(family_name,'[a-zA-Z]') or regexp_matches(family_name,'[^а-яА-ЯѣѢіІѳѲёЁ ,\-0-9.()йЙ]')) group by 1;
```

Result: no 'Виолончель'/'Біолончель'/'Вальдгорнь'/'Альть' left (Віолончель 591, Вальдгорнъ 432, Альтъ 644); remaining odd instruments (Вальтгорнъ 4, Валторнъ 3, Волторна 2, Тромбомъ 1, ...) were each read at zoom and match the print. One non-Cyrillic character left in any Musicians surname: "Валеніўсъ" (ў printed). 

## 2026-10-02 -- the 46 persons newly merged by the Musicians name fixes (issue #130 batch 9)

```sql
select p.display_name,p.first_attested_season,p.last_attested_season,s.display_name,s.first_attested_season,s.last_attested_season
from entities.person p join entities.person s on s.person_id=p.superseded_by_person_id
where p.superseded_by_person_id is not null  -- minus the 2246 tombstones present in the pre-edit backup
```

Result: 46 new tombstones (2246 -> 2292), live persons 3326 -> 3280; every pair is the same normalized name in the same or adjacent seasons (list in known_issues #130 batch 9); 157 person_link rows repointed, all explained by those tombstones; 0 orphans; receipts sum identical.

## 2026-10-02 -- court-soloist / ballet-soloist titles in Musicians (issue #130 batch 9 addendum)

```sql
select family_name,count(*) filter (where rank_or_title is not null),count(*) from raw.person_entry where page_id like 'musicians_%' and family_name in ('Ауэръ','Цабель','Сиборъ') group by 1;
select entry_id,family_name,tenure_note_text from raw.person_entry where page_id like 'musicians_%' and rank_or_title is null and regexp_matches(tenure_note_text,'(Солист|Двора|Концертмейст|Капельмейст|Дирижеръ|Органист|Піанист|библіотекар|Репетитор|Аккомпан)');
```

Result: before, 18 rows (Цабель 8, Чіарлоне Виргинія 5, Ауэръ 4, Сиборъ 1) had the title only inside tenure_note_text; after the fix every Ауэръ (17/17) and Сиборъ (4/4) row has it, Цабель 14/17 (3 cross-reference rows, none printed), Чіарлоне 8 (the SP rows where it is printed).

## 2026-10-02 -- Musicians heading_path trailing colons (issue #130 batch 9 addendum 2)

```sql
select count(*) filter (where heading_path like '%:'), count(*), count(distinct heading_path) filter (where heading_path like '%:'), count(distinct heading_path) from raw.person_entry where page_id like 'musicians_%';
select heading_path,count(*) n from raw.person_entry where page_id like 'musicians_%' and heading_path like '%:' group by 1 order by n desc limit 8;
select count(*) from raw.person_entry where page_id like 'musicians_%' and heading_path like '%:' and rtrim(heading_path,':') in (select heading_path from raw.person_entry where page_id like 'musicians_%' and heading_path not like '%:');
select count(*) from raw.person_entry where page_id like 'musicians_%' and rank_or_title like '%онъ же%';
```

Result: 759 of 7639 rows end in a colon (9 distinct headings; "Музыканты:" 415, "Оркестр оперы и балета. Музыканты:" 147, "Оркестръ оперы и балета. Музыканты:" 123); 705 of them have a colon-free twin; 0 rows still hold the Фарскій alias in rank_or_title.

## 2026-10-02 -- hard-sign-less "оркестр" in Musicians headings (issue #130 batch 9 addendum 3)

```sql
select page_id,count(*) from raw.person_entry where page_id like 'musicians_%' and (regexp_matches(heading_path,'Оркестр[^ъаыуо]') or regexp_matches(heading_path,'Оркестр$')) group by 1 order by 1;
select heading_path,count(*) from raw.person_entry where page_id like 'musicians_%' group by 1 order by 1;   -- scanned all 104 distinct values by eye
select count(*) from raw.person_entry where page_id like 'musicians_%' and regexp_matches(heading_path,'(Оркестр|оркестр)([^ъыовауи]|$)');
```

Result: 7 pages (1894-95/1896-97/1897-98 MSK p000-p002) had "Оркестр оперы и балета", and by the full heading listing 8 more (1890-93 MSK p000-p002) had "Оперный оркестр" -- 544 rows in all; scans of all six p000 pages print the hard sign. After the fix: 0 rows left.

## 2026-10-02 -- research_dataset.sqlite rebuilt from the current full_run DuckDB

```sql
-- sqlite (new) vs sqlite (28 Sep backup) vs duckdb research.*: select count(*) from <table> for theater/work/person/event/performance/person_appearance;
select count(*) from person_appearance where instrument in ('Виолончель','Біолончель','Вальдгорнь','Альть');
select sum(receipts_total_kopecks) from event;  pragma integrity_check;  pragma foreign_key_check;
```

Result: new sqlite row counts equal duckdb research.* exactly (theater 6, work 3657, person 3274, event 31203, performance 29568, person_appearance 23151; the 28 Sep file had work 3518, person 2894, event 28966, performance 27587, person_appearance 21154); misread instrument spellings 112 -> 0; receipts sum 2999096975 in both; integrity ok, 0 foreign-key violations. Old file kept as outputs/full_run/research_dataset.sqlite.bak_2026-10-02.

## 2026-10-02 -- ProductionTeam profile before the audit (issue #132)

```sql
select entity_type,count(*),count(distinct page_id) from raw.person_entry group by 1 order by 2 desc;
select count(*),count(distinct page_id) from raw.person_entry e where e.entity_type='ProductionTeam' and regexp_matches(lower(coalesce(e.heading_path,'')||' '||coalesce(e.institution,'')),'декор');
select count(distinct l.person_id) from raw.person_entry e join entities.person_link l using(entry_id) where e.entity_type='ProductionTeam' and regexp_matches(lower(coalesce(e.heading_path,'')||' '||coalesce(e.institution,'')),'декор');
```

Result: ProductionTeam 2003 rows on 94 pages; the decor department ("Отдѣлъ декораціонный") 605 rows on 42 pages, 98 live persons; flags on decor rows: institution_duplicated_in_heading_path 4, duplicate_person_on_page 1.

## 2026-10-02 -- ProductionTeam after stage 1 (issue #132)

```sql
-- old (backup _pt_stage1) vs new: count(*) raw.person_entry; tombstones/live persons in entities.person; orphan / unlinked / tombstoned links; sum(receipts_total_kopecks) research.event
```

Result: person_entry 23163 -> 23158, tombstones 2292 -> 2297 (5 same-person merges), live persons 3280 -> 3269, 0 orphans / 0 unlinked entries / 0 links to tombstones, receipts sum identical, flags 598 -> 600.

## 2026-10-02 — Do all person entities come from the spiski (roster) pages?

```sql
-- schema check: raw.event_entry / raw.event_entry_performance columns
select table_name, column_name from information_schema.columns
where table_schema='raw' and table_name like 'event%';

select sp.entity_type, count(*) links, count(distinct pl.person_id) persons
from entities.person_link pl
join raw.person_entry pe on pe.entry_id = pl.entry_id
join raw.source_pages sp on sp.page_id = pe.page_id
group by 1 order by 1;

select count(*), count(*) filter (where entry_id not in (select entry_id from raw.person_entry))
from entities.person_link;

select count(*), count(*) filter (where person_id not in (select person_id from research.person_appearance))
from research.person;

select entity_type, count(*) from research.person_appearance group by 1 order by 1;
```

Result: Yes. Repertoire tables carry no person columns at all (title/genre/date/theater/receipts only). All 23,158 person_link rows resolve to raw.person_entry (0 unmatched); every link's page is a roster entity_type: Administrators 1839 links/269 persons, BalletArtists 8478/1149, Graduates 504/490, Musicians 7639/856, ProductionTeam 1998/300, TheaterSchoolStaff 2700/318. All 3,262 research.person rows have ≥1 person_appearance (0 orphans); appearances by type: Admin 1839, Ballet 8477, Grad 504, Musicians 7639, ProdTeam 1998, SchoolStaff 2689.

## 2026-10-02 -- ProductionTeam stage 2 (issue #132): distinct section values before/after (backup DB vs rebuilt DB)

```sql
select count(distinct heading_path), count(distinct institution), count(*)
from raw.person_entry where entry_id like 'productionteam%';
select count(distinct role_normalized) from analysis.person_entry where entry_id like 'productionteam%';
```

Result: before (pt_stage2 backup) 558 distinct heading_path / 68 institution / 1998 rows, 220 distinct role_normalized; after 201 / 2 (С.-ПЕТЕРБУРГЪ 1255, МОСКВА 742, plus 1 stale row since fixed) / 1998, 95 role_normalized.

## 2026-10-02 -- ProductionTeam stage 2: how many rows end with a theatre/troupe name as role_normalized

```sql
select count(*) from analysis.person_entry where entry_id like 'productionteam%' and role_normalized like '%театръ';
select count(*) from analysis.person_entry where entry_id like 'productionteam%' and (role_normalized like '%театръ' or role_normalized like '%труппа');
```

Result: 389 and 484 of 1998 -- role_normalized (= last chain segment) is a theatre/troupe for these rows (open item in known_issues #132 stage 2).

## 2026-10-02 -- ProductionTeam stage 2: surname spelling-variant sweep (ъ/ь/ѣ/і-normalised key groups)

```sql
select family_name, first_name, count(*) from raw.person_entry
where page_id like 'productionteam%' group by 1, 2;   -- then grouped in Python by a normalised key
select entry_id, family_name, first_name, patronymic, heading_path from raw.person_entry
where entry_id like 'productionteam%' and family_name = any([<variant list>]) order by family_name, entry_id;
```

Result: 10 same-person groups with >1 spelling (Пипарь 4/Пипаръ 9, Педдерь 1/Педдеръ 34, Вивьень 1/Вивьенъ 6, Зыбінь 1/Зыбинъ 9, Аллегрі 1/Аллегри 17, Хмѣлевскій/Хмелевскій runs, Кунъ 1-й/2-й etc.) and ~25 near-miss pairs; 74 rows
listed for a zoom re-read (worklist; result in the stage-1 residue note).

## 2026-10-02 -- ProductionTeam stage 2: link alignment + institution flag after rebuild

```sql
-- pipeline/check_person_link_alignment.py --db outputs/full_run/imperial_theaters.duckdb  (read-only)
select entry_id, family_name, institution, heading_path from raw.person_entry where institution like 'Михайловскій%';
```

Result: 23158 links checked, 1 shift block (theaterschoolstaff_1896-97_p000 e015..e024, the known #131 phase 2 item), none on ProductionTeam; the second query found the one stale ProductionTeam row (1895-96 p001 e007, from the
hard-coded override in parse_and_validate.py) that is now retired.


## 2026-10-02 — Where do the ballet production lists store their author/composer names?

```sql
select table_schema, table_name, column_name from information_schema.columns
where table_name like 'production%' order by 1,2;

select count(*), count(description_text), count(distinct description_text) from raw.production_entry;

select season, city, title, description_text
from raw.production_entry using sample 8 (reservoir, 42) order by season;
```

Result: raw.production_entry (+ _performance) exist only in the raw tier, with no person/author columns. The names are embedded in free-text description_text: 480 rows, all non-null, 291 distinct strings. Examples: "соч. Сенъ-Жоржа и М. И. Петипа, музыка Ц. Пуни."; "сюжетъ и. Асрейтера и Г. Гауль, музыка І. Байеръ." Names are printed in the genitive after соч./музыка/сюжетъ, with roles marked by these keywords. Nothing from these lists is in entities.person / research.person yet.

## 2026-10-02 — Has raw.production_entry.description_text drifted from the scan-verified CSV?

```sql
select season, city, list_number, title, description_text from raw.production_entry;
-- compared in pandas against outputs/ballet_productions_pilot/parsed_verified/production_entry.csv
-- (set of distinct description_text values both ways), plus group by season, city for 1899-00
```

Result: 480 DB rows vs 480 CSV rows. 0 description_text values are in the DB but not the CSV, and 0 the other way round, so there's no drift since the load. 1899-00: Moscow has 13 entries (the interim Google Books stand-in) and SP has 26. Also, outside the DB, the verify_logs tally for description_text is: 216 misread, 11 structure, 7 genuine_print, 1 extra, 11 uncertain (10 resolved by RG, 1 still open: Бернаделли, 1896-97 SP #2).

## 2026-10-02 -- ProductionTeam stage 2b: institution/heading_path after restoring the list title and city-first chain

```sql
select institution, count(*) from raw.person_entry where entry_id like 'productionteam%' group by 1 order by 1;
select heading_path from raw.person_entry where entry_id in ('productionteam_1895-96_p001__e007','productionteam_1905-06_p003__e010','productionteam_1909-10_p004__e019');
select family_name, count(*) from raw.person_entry where entry_id like 'productionteam%'
  and family_name in ('Пипарь','Пипаръ','Педдерь','Зыбінь','Аллегрі','Вивьень де-Шатобріанъ','Семирадскій') group by 1;
```

Result: two institution values, "Списокъ личнаго состава служащихъ по монтировочной части." 1605 rows and "... по постановочной части." 393; the three chains start "С.-ПЕТЕРБУРГЪ / ..." or "МОСКВА / ..."; only Пипаръ (13) remains
of the variant set (Пипарь, Педдерь, Зыбінь, Аллегрі, Вивьень, Семирадскій all 0).


## 2026-10-02 -- role_normalized: where it is used, and which ProductionTeam chains end in a theatre/troupe

```sql
describe research.person_appearance;   -- is role_normalized carried into the research layer?
select table_schema, table_name from information_schema.columns
where column_name ilike '%role%' and table_schema in ('research','analysis');
select heading_path_clean from analysis.person_entry where entry_id like 'productionteam%';  -- grouped in Python: last non-theatre/troupe segment vs final segment
select split_part(entry_id,'_',1) t, count(*) n,
  count(*) filter (where regexp_matches(role_normalized,'(театръ|театра|труппа)[.]?$')) th
from analysis.person_entry group by 1 order by 1;
```

Result: role_normalized exists only in analysis.person_entry (analysis.person_entry_credit has an unrelated role column); research.person_appearance has no role column (it carries the full heading_path). ProductionTeam: 484 of 1998 chains end in a theatre/troupe segment (Парикмахеры 156, Гардеробмейстеры 110, Гардеробмейстерши 107, Бутафоры 62, Помощники декораторовъ 19, Завѣдывающіе освѣщеніемъ 14, Помощники парикмахера 7, 7 others); by the broader regex ProductionTeam 493, Administrators 56 of 1839, BalletArtists 8, TheaterSchoolStaff 1, Musicians 0, Graduates 0.

## 2026-10-02 -- ProductionTeam consistency checks after stage 2 (list-number contiguity, person city, leaving notes)

```sql
select entry_id, family_name, list_number, heading_path from raw.person_entry where entry_id like 'productionteam%' order by entry_id;   -- grouped by (season, heading_path) in Python; numbers vs 1..n
select e.entry_id, l.person_id, split_part(e.heading_path,' / ',1) city, e.family_name, e.heading_path
from raw.person_entry e join entities.person_link l using(entry_id) where e.entry_id like 'productionteam%';   -- persons whose city differs from their majority city
select l.person_id, split_part(e.entry_id,'_',2), e.family_name, e.tenure_note_text, e.entry_id
from raw.person_entry e join entities.person_link l using(entry_id) where e.entry_id like 'productionteam%';   -- leaving (Оставилъ службу) / † notes vs later appearances
select e.entry_id, e.first_name, e.patronymic, substr(e.tenure_note_text,1,75), split_part(e.heading_path,' / ',1), right(e.heading_path,40), l.person_id
from raw.person_entry e join entities.person_link l using(entry_id) where e.entry_id like 'productionteam%' and e.family_name = ?;   -- Иващенко, Васильевъ, Каменскій, Неменскій, Павловъ, Ковалевскій, Лупановъ
```

Result: 1223 (season, chain) groups, 283 numbered, 9 not 1..n (8-row city bug + genuine gaps); 21 rows with a non-majority city (8 = the 1898-99 p002 city bug, now fixed); 9 leaving-note and 3 † rows with later appearances, explained except Васильевъ (two men merged: SPb decorator † 1892 and Moscow costumer from 1904).

## 2026-10-02 — Ballet-list creator-name second read: pre-promotion check and post-load verification

```sql
-- pre: row counts + snapshot (parquet backup) of raw.production_entry / _performance vs parsed_verified CSVs
select * from raw.production_entry;  select * from raw.production_entry_performance;
select description_text from raw.production_entry;  -- count 'Бурімюллера' / 'нѣкоторые номера'
-- post (after load_productions.py):
select count(*) from raw.production_entry; select count(*) from raw.production_entry_performance;
select season, city, list_number, description_text from raw.production_entry
 where description_text like '%Бургмюллера%' or description_text like '%нѣкоторые нумера%';
select count(*) from raw.production_entry
 where description_text like '%Бурімюллера%' or description_text like '%нѣкоторые номера%';
```

Result: pre: 480/1881 rows, the DB matched the CSVs, and each target was present once. Post: 480/1881 rows and 0 orphans. Бургмюллера is now in 1897-98 MSK #9, and "нѣкоторые нумера" is in all 5 Пахита entries (1900-01 through 1904-05). 0 old forms remain.

## 2026-10-03 -- ProductionTeam: persons whose entries disagree on first start date (homonym-merge / date-misread lead); Васильевъ split check

```sql
with first_start as (
  select e.entry_id, l.person_id, e.family_name, split_part(e.entry_id,'_',2) season, min(s.start_date_undate) fs
  from raw.person_entry e join entities.person_link l using(entry_id)
  left join raw.person_entry_service s on s.entry_id=e.entry_id
  where e.entry_id like 'productionteam%' group by all)
select person_id, any_value(family_name), count(*), count(distinct fs), list(distinct fs order by fs), min(season), max(season)
from first_start where fs is not null group by person_id having count(distinct fs)>1 order by 2;
select person_id::varchar, display_name, first_attested_season, last_attested_season, superseded_by_person_id is null
from entities.person where canonical_family_name='Васильевъ' and canonical_first_name='Василій' and canonical_patronymic='Васильевичъ';
select e.entry_id,e.first_name,e.patronymic,e.tenure_note_text,l.match_method from raw.person_entry e join entities.person_link l using(entry_id)
where l.person_id::varchar like 'cef4a3%' order by 1;   -- before the split
```

Result: 43 PT persons with >1 distinct first start date (about half day-level, ~16 year-level, list in known_issues #132 addendum 3); the Васильевъ query returned one merged person linking SPb 1890-91/1891-92 and Moscow 1903-04..1907-08 before the split, two live persons after (cef4a353 1890-91..1891-92, e97dc496 1903-04..1907-08); a name-keyed Tier 1 cluster, no merge-log entry.

## 2026-10-03 -- ProductionTeam start-date audit: follow-up queries (unparsed starts, Кунъ and patronymic-variant persons)

```sql
select s.entry_id, s.start_date_text, s.start_date_undate, s.end_date_text, substr(e.tenure_note_text,1,70)
from raw.person_entry_service s join raw.person_entry e using(entry_id)
where s.entry_id like 'productionteam%' and s.start_date_text is not null and s.start_date_undate is null;
select e.entry_id, e.family_name, e.first_name, e.patronymic, substr(e.tenure_note_text,1,50), substr(cast(l.person_id as varchar),1,6), right(e.heading_path,40)
from raw.person_entry e join entities.person_link l using(entry_id) where e.entry_id like 'productionteam%' and e.family_name like 'Кунъ%' order by 1;
select e.entry_id, e.first_name, e.patronymic, substr(e.tenure_note_text,1,45), substr(cast(l.person_id as varchar),1,6), right(e.heading_path,35)
from raw.person_entry e join entities.person_link l using(entry_id) where e.entry_id like 'productionteam_190%' and e.family_name in ('Бардюкъ','Бордюгъ','Зандинъ','Лебедевъ','Холодовъ') order by 1;
```

Result: 5 PT service rows with a start text but no parsed date, 1 fixable (Жуляевъ 1898-99, stray period -> fixed) and 4 genuine partial dates; the Кунъ list showed 1890-91 p003 e013 under the Кунъ 1-й person while its two sister entries (Карловичъ) sat under another (moved); Зандинъ and Лебедевъ each sit under two person_ids split by a patronymic variant (Ивановичъ/Павловичъ; Васильевичъ/Афанасьевичъ), Бардюкъ/Бордюгъ already share one person_id.

## 2026-10-03 -- ProductionTeam: where the workshop specialty text sits (tenure_note_text vs rank_or_title)

```sql
select count(*) filter (where regexp_matches(coalesce(tenure_note_text,''),'(парики|костюмы|Парики|Костюмы)')) in_tenure,
 count(*) filter (where regexp_matches(coalesce(rank_or_title,''),'(парики|костюмы|Парики|Костюмы)')) in_title,
 count(*) filter (where regexp_matches(coalesce(tenure_note_text,''),'(парики|костюмы|Парики|Костюмы)') and regexp_matches(coalesce(rank_or_title,''),'(парики|костюмы|Парики|Костюмы)')) both_
from raw.person_entry where entry_id like 'productionteam%';
select count(*) from raw.person_entry where entry_id like 'productionteam%' and rank_or_title is not null;
select l.person_id, any_value(e.family_name), count(*) filter (where regexp_matches(coalesce(e.tenure_note_text,''),'(парики|костюмы)')) t, count(*) filter (where regexp_matches(coalesce(e.rank_or_title,''),'(парики|костюмы)')) r
from raw.person_entry e join entities.person_link l using(entry_id) where e.entry_id like 'productionteam%' group by 1 having t>0 and r>0;
```

Result: specialty text in tenure_note_text on 204 rows, in rank_or_title on 43 (1 row both); 75 PT rows have any rank_or_title; 15 persons have it in tenure_note_text in some seasons and rank_or_title in others (Пипаръ 11/2, Жуляевъ 11/4, Ефимовъ 14/4, Варламовъ 14/4, Иванова 18/2 ...).

## 2026-10-03 -- ProductionTeam: specialty derivation + wardrobe-nesting change, verification queries

```sql
select count(*) filter (where title_clean is not null), count(*) filter (where regexp_matches(coalesce(tenure_note_text_clean,''),'(Мужскіе|Женскіе|Парики)')) from analysis.person_entry where entity_type='ProductionTeam';
select title_clean, count(*) from analysis.person_entry where entity_type='ProductionTeam' and title_clean is not null group by 1 order by 2 desc;
select md5(string_agg(x,'|' order by x)) from (select concat_ws('~', <every analysis column>) x from analysis.person_entry where entity_type<>'ProductionTeam');   -- backup DB vs rebuilt DB
select split_part(heading_path,' / ',2), count(*) from raw.person_entry where entry_id like 'productionteam%' group by 1 order by 2 desc;
select count(*) from raw.person_entry where entry_id like 'productionteam%' and (heading_path like '%/ Главный гардеробъ%' or heading_path like '%/ Мѣстные гардеробы%') and heading_path not like '% / Отдѣлъ гардеробный / %';
select entry_id, family_name, heading_path from raw.person_entry where entry_id like 'productionteam%' and split_part(heading_path,' / ',2) in ('Большой театръ','Мастерская по раскраскѣ тканей');
```

Result: title_clean on 261 ProductionTeam rows (75 before), 0 specialties left in tenure_note_text_clean; non-ProductionTeam analysis rows hash-identical to the backup; second path segment tally: Отдѣлъ декораціонный 917, гардеробный 739, освѣтительный 174, бутафорскій 134, Парикмахерскій отдѣлъ 18, декораціонно-машинный 7, Мастерская по раскраскѣ тканей 3, "Отдѣлъ бугафорскій" (print typo) 2; 0 Главный гардеробъ/Мѣстные гардеробы chains without the Отдѣлъ гардеробный parent; the 4 stray "Большой театръ" second segments (1900-01 p003 e015-e018) were fixed.

## 2026-10-03 — Issue #133: building and verifying analysis.production_entry_credit

```sql
select description_text, count(*) n from raw.production_entry group by 1 order by 1;   -- 290 distinct strings, read in full
-- after pipeline/build_production_credits.py:
select count(*), count(distinct production_entry_id), count(distinct name_printed) from analysis.production_entry_credit;
select count(*) from analysis.production_entry_credit c left join raw.production_entry e using (production_entry_id) where e.production_entry_id is null;
select e.description_text from raw.production_entry e where not exists
  (select 1 from analysis.production_entry_credit c where c.production_entry_id = e.production_entry_id);
select is_pseudonym, is_collective, count(*) from analysis.production_entry_credit group by all order by all;
select name_printed, role_category, count(*) from analysis.production_entry_credit where name_printed like '%Перро%' group by all order by all;
```

Result: 1215 rows, 478 entries, 167 distinct printed names, 0 orphans. The 2 entries with no credits print none ("Балетъ въ 1 д.", "(Les élèves de Dupré)."). There are 4 pseudonym rows and 5 group rows. Перро: source 25 (Perrault), author 4, plus Ж. Перро 13 and Ю. Перро 13 (both author, Perrot).

## 2026-10-03 -- ProductionTeam blind sample: corpus-wide sweeps for the error classes found (list_number leaks, heading text in rank_or_title, verb gender) + check of the added row

```sql
select entry_id, family_name, list_number, right(heading_path,45) from raw.person_entry where entry_id like 'productionteam%' and list_number is not null and not regexp_matches(list_number,'^[0-9]+[.]?$') order by 1;
select entry_id, family_name, rank_or_title, right(heading_path,40) from raw.person_entry where entry_id like 'productionteam%' and rank_or_title is not null and not regexp_matches(rank_or_title,'^(Мужскіе|Женскіе|Парики|князь|профессоръ|академикъ|баронесса|[(]онъ)') order by 1;
select entry_id, family_name, first_name, substr(tenure_note_text,1,90) from raw.person_entry where entry_id like 'productionteam%'
 and ((tenure_note_text like '%Оставила службу%' and regexp_matches(family_name,'(ъ|й|ь)( [0-9]-й)?$')) or (tenure_note_text like '%Оставилъ службу%' and regexp_matches(family_name,'(а|я)$'))) order by 1;
select l.person_id::varchar like '0995a2%', e.heading_path, e.rank_or_title from raw.person_entry e join entities.person_link l using(entry_id) where e.entry_id='productionteam_1898-99_p002__e025';
```

Result: 7 non-numeric list_number rows (all 1901-02 p003 e003-e009), 5 rank_or_title rows that are heading text, 3 verb-gender hits of which 1 wrong (Романовъ), and the added Педдеръ row linked to the existing Педдеръ person (0995a2).

## 2026-10-03 — Issue #133 step 2: creator → roster matching and link verification

```sql
-- surname-stem grouping of printed forms (read in full)
select c.name_printed, c.role_category, e.season, e.city, e.title, c.honorific_printed
from analysis.production_entry_credit c join raw.production_entry e using (production_entry_id) where not c.is_collective;
-- roster candidates, one query per nominative surname stem (~80 stems)
select p.person_id, p.display_name, p.first_attested_season, p.last_attested_season,
       string_agg(distinct a.entity_type, '/'), string_agg(distinct coalesce(a.title, a.rank, ''), ' / ')
from research.person p join research.person_appearance a using (person_id)
where p.canonical_family_name ilike ? group by all order by 2;
-- contexts for ambiguous forms (Тальони, Петипа, Иванова, Гершеля, Мюльдорфера, К. В., М. И. Чайковскаго, Щимана, …)
select distinct e.season, e.city, e.title from analysis.production_entry_credit x join raw.production_entry e using (production_entry_id) where name_printed = ?;
-- after link_production_creators.py
select count(*) from entities.production_credit_link where link_source = 'roster' and person_id not in (select person_id from research.person);
select count(*) from entities.production_credit_link where link_source = 'creator' and person_id not in (select person_id from entities.creator_person);
select count(*) from entities.creator_person where person_id in (select person_id from entities.person);
select count(*) from analysis.production_entry_credit c where not is_collective and credit_id not in (select credit_id from entities.production_credit_link);
select p.display_name, count(*), string_agg(distinct x.role_category, ',') from entities.production_credit_link l
  join research.person p using (person_id) join analysis.production_entry_credit x using (credit_id)
  where l.link_source = 'roster' group by 1 order by 2 desc;
select distinct p.display_name, p.wikidata_qid from entities.production_credit_link l join research.person p using (person_id) where l.link_source = 'roster';
```

Result: bare "Тальони" appears only on Флика и Флока (MSK 1890-94); "Тальони (отца)" only on Сильфида (SP 1891-93); bare "Петипа" on Дочь Фараона and others; "Иванова" once (Пробужденіе Флоры 1901-02). 1210 links, 330 to 18 roster persons, 75 creator_person rows; all four integrity checks are 0. 5 of the 18 roster creators already had QIDs (Петипа, Л. Ивановъ, Фокинъ, Хлюстинъ, Всеволожскій). The Wikidata candidate searches (public API, read-only) went to docs/eval/production_creators_wikidata_review.csv, not to the DB.

## 2026-10-03 -- TheaterSchoolStaff audit: scoping, apply verification and cross-checks

```sql
select split_part(page_id,'_',2) s, count(distinct page_id) p, count(*) n from raw.person_entry where entry_id like 'theaterschoolstaff%' group by 1 order by 1;
select institution, count(*) from raw.person_entry where entry_id like 'theaterschoolstaff%' group by 1 order by 2 desc;
select heading_path, count(*) from raw.person_entry where entry_id like 'theaterschoolstaff%' group by 1 order by 2 desc;
select e.entry_id, e.family_name, e.first_name, e.patronymic, substr(cast(l.person_id as varchar),1,6), p.display_name from raw.person_entry e join entities.person_link l using(entry_id)
  join entities.person p on p.person_id = l.person_id where e.page_id = 'theaterschoolstaff_1896-97_p000' order by e.entry_id;   -- the #131 phase 2 block
select count(*) from raw.person_entry where entry_id like 'theaterschoolstaff%' and patronymic is null and first_name like '% %';   -- 85 glued first+patronymic rows
select subject_taught, count(*) from raw.person_entry where entry_id like 'theaterschoolstaff%' and subject_taught is not null group by 1 order by 2 desc limit 15;
select rank_or_title, count(*) from raw.person_entry where entry_id like 'theaterschoolstaff%' and rank_or_title is not null group by 1 order by 2 desc limit 12;
```

Result: 99 pages / 2700 rows before the audit (2745 after stage 1), 22 distinct institution values and 193 distinct heading_path values before (2 institution titles + 128 heading paths for the 19 applied seasons after); the 1896-97 p000 block e014..e024 each carried the previous entry's person (fixed first); 85 rows had first name and patronymic glued; 627 rows had a rank_or_title that was often a subject (subjects: Танцы 38, Музыка 23 ...).

## 2026-10-03 -- TheaterSchoolStaff blind read: stored-value check on disputed name fields (issue #134)

```python
# raw JSON, not SQL: for each disputed (page, entry) print the stored family/first/patronymic and any non-Cyrillic code points
json.load(open(f'outputs/full_run/raw/{pg}.raw.json'))['entries'][i-1]   # 4 entries: 1893-94 p001 e005, 1891-92 p004 e003, 1897-98 p002 e024, 1905-06 p003 e002
```

Result: stored values Дебогорій-Мокріевичъ / Дмитріевичъ / Дмитріевичъ / Веселовскій; the only non-Cyrillic character is the hyphen-minus in the double surname. The scan crops (1891-92 p004, 1893-94 p001) show і+е, not є. Blind-read tally over 117 corrected fields: 108 agree, 1 uncertain-but-equal, 8 flagged and all explained (4 ordinal rows, 3 є misreadings, 1 previously reverted).

## 2026-10-03 -- TheaterSchoolStaff blind sample follow-ups: stored values after the 32 fixes (issue #134)

```sql
select entry_id, family_name from raw.person_entry where entry_id like 'theaterschoolstaff%' and (family_name='Молась' or family_name='Всеволожскій') order by 1;
select entry_id, family_name, start_date_text, end_date_text, end_type
from raw.person_entry_service s join raw.person_entry using(entry_id)
where entry_id in ('theaterschoolstaff_1895-96_p001__e033','theaterschoolstaff_1891-92_p002__e020','theaterschoolstaff_1894-95_p002__e027','theaterschoolstaff_1901-02_p002__e027') order by 1;
select family_name, count(*), min(substr(entry_id,1,22)) from raw.person_entry where family_name ilike 'Легат%' group by 1 order by 2 desc;
select family_name, count(*) from raw.person_entry where entry_id like 'theaterschoolstaff%' and family_name ilike 'Всеволож%' group by 1;
```

Result: after the fixes Молась has 0 rows and Всеволожскій only theaterschoolstaff_1908-09_p003__e002 (genuinely printed -скій). Before the fixes: Всеволожскій 4 rows / Всеволожской 16 rows in TheaterSchoolStaff; Легатъ ordinals ("Легатъ 1-й" etc.) are stored inside family_name in every table (26 bare Легатъ, 25 Легать, 11 Легатъ 1-й, 10 Легатъ 2-й ...). The raw-JSON sweeps (note dates vs service_periods; leaving/death markers vs period ends; Мола* spellings across all 99 TSS pages) were run with python over outputs/full_run/raw and found the 32 edits listed in docs/eval/theaterschoolstaff_audit_2026-10-03/blind_sample/blind_fixes_log.json.

## 2026-10-05 -- Merge batch review, candidate 1: Зандинъ Михаилъ (issue #134 follow-up)

```sql
select p.person_id, l.entry_id, e.family_name, e.first_name, e.patronymic, e.rank_or_title, e.heading_path, e.tenure_note_text
from entities.person_link l join entities.person p using(person_id) join raw.person_entry e using(entry_id)
where p.superseded_by_person_id is null and p.canonical_family_name='Зандинъ' order by e.entry_id;
```

Result: 4 rows, 2 live persons -- a9d821 "Зандинъ, Михаилъ Ивановичъ" (productionteam 1906-07 p000 e009, 1907-08 p000 e007; Помощники декораторовъ; "съ 1 мая 1907 г.") and 831b71 "Зандинъ, Михаилъ Павловичъ" (1908-09 p000 e004 "съ 1 мая 1887 г.) (у Головина)"; 1909-10 p000 e003 "съ 1 мая 1907 г."; Исп. об. главнаго Декоратора). No season overlap.

## 2026-10-05 -- Merge batch review, candidate 2: Лебедевъ Иванъ; discovery that person 1dd355 is three men

```sql
-- ProductionTeam Лебедевъ Иванъ rows and their persons
select p.person_id, l.entry_id, e.first_name, e.patronymic, e.heading_path, e.tenure_note_text from entities.person_link l join entities.person p using(person_id) join raw.person_entry e using(entry_id) where p.superseded_by_person_id is null and p.canonical_family_name='Лебедевъ' and e.first_name='Иванъ' and e.entry_id like 'productionteam%' order by e.entry_id;
-- everything attached to 1dd355
select l.entry_id, e.first_name, e.patronymic, e.heading_path, e.tenure_note_text from entities.person_link l join entities.person p using(person_id) join raw.person_entry e using(entry_id) where cast(p.person_id as varchar) like '1dd355%' order by e.entry_id;
-- persons tombstoned into 1dd355, and their merge-log rows
select person_id, display_name, first_attested_season, last_attested_season from entities.person where cast(superseded_by_person_id as varchar) like '1dd355%';
select * from entities.person_merge_log where person_id_1 or person_id_2 in the chain (652c2d, 7f0f33, ccfe76, e8c8d0);
-- patronymic-conflict count over live persons (python wrapper around: count(distinct patronymic-or-second-word-of-first_name) >= 2 per person)
```

Result: 1dd355 held 22 entries: 10 MSK musicians (Григорьевичъ flautist + 2 ballet-orchestra cross-reference lines per year), 11 SP musicians (Константиновичъ clarinetist, since 1868, left 1900-09-01) and 1 ProductionTeam row (Васильевичъ, Бутафоръ, "съ 3 іюня 1889"). Four tombstoned persons point at it; the merge log has 4 confirmed `family_name_variant` rows (similarity 0.85, tenure_signal `unique_name_in_corpus`) chaining them. Patronymic-conflict count: 245 live persons with >= 2 distinct printed patronymics (mostly spelling variants). After the two splits: 4 live Лебедевъ Иванъ persons (1dd355 Константиновичъ 11 entries; 7ca78604 Григорьевичъ 10; 1134bfb0 Васильевичъ 1; ea76e8 Афанасьевичъ 2); live persons 3257, tombstones 2313, orphans 0.

## 2026-10-05 -- Merge batch review, candidates 3-7 and application (issue #134 follow-up)

```sql
-- Петипа / Чекетти / Ширяевъ / Голяховскій: live persons and every appearance (entities.person_link x raw.person_entry), by canonical_family_name
select cast(person_id as varchar), display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where canonical_family_name in ('Петипа','Чекетти','Ширяевъ') and superseded_by_person_id is null;
select substr(cast(p.person_id as varchar),1,6), l.entry_id, e.first_name, e.patronymic, e.heading_path, e.tenure_note_text from entities.person_link l join entities.person p using(person_id) join raw.person_entry e using(entry_id) where p.superseded_by_person_id is null and p.canonical_family_name in ('Петипа','Чекетти','Ширяевъ','Голяховскій') order by 1, l.entry_id;
-- downstream references to the persons being merged
select 'person_wikidata_link', person_id from entities.person_wikidata_link; select 'production_credit_link', person_id, count(*) from entities.production_credit_link group by 1,2;
-- post-apply checks
select count(*) from entities.person where superseded_by_person_id is null;  select count(*) from entities.person_merge_log where status='confirmed_manual' and tenure_evidence like 'merge batch review 2026-10-05%';
select person_id, display_name, canonical_first_name, wikidata_qid from research.person where canonical_family_name in ('Чекетти','Петипа','Ширяевъ','Зандинъ','Голяховскій');
```

Result: Петипа Маріусъ Ивановичъ had 3 live persons (e04344 20 entries 1890-91..1907-08 incl. school rows to 1891-92; 0f4adf 2 entries 1908-09..1909-10 with "† 1 іюля 1910 г."; 6310e8 1 school row 1892-93 "съ 1 сентября 1855"); Чекетти 2 persons (09350c Энрико, 8 school entries 1893-94..1900-01, left 1 апрѣля 1901; bfe3f9 Генрихъ, 19 company entries 1890-91..1902-03, left 1 ноября 1902) plus his wife Жозефина (separate); Ширяевъ Александръ Викторовичъ had 6b54e5 (51 entries) plus 0c0f54 (the 1890-91 school row printing Васильевичъ -- scan-verified, p. 263); Голяховскій 7fd62c (17 entries) + dd0ff7 (5 entries 1901-06, Васильевичъ). Referenced downstream: Wikidata link on e04344 (Q312320) and 6b54e5 (Q4524496); production_credit_link 142 rows on e04344, 1 on 09350c. After applying: live persons 3250, 7 `confirmed_manual` log rows, research.person: Чекетти displayed "Чекетти, Энрико Цезаревичъ", Петипа 1890-91..1909-10 with Q312320, Ширяевъ 1890-91..1909-10 with Q4524496.

## 2026-10-05 -- Homonym sweep (issue #134 follow-up)

```sql
-- per live person: all linked entries with season/city/type/first/patronymic/instrument/heading/note/start-end dates (docs/eval/homonym_sweep_2026-10-05/signal_scan.py, timeline.py)
select l.person_id, l.entry_id, e.entity_type, sp.season, sp.city, a.family_name_clean, a.first_name_clean, a.patronymic_clean, ...
from entities.person_link l join entities.person p on p.person_id=l.person_id and p.superseded_by_person_id is null join raw.person_entry e using(entry_id) join analysis.person_entry a using(entry_id) join raw.source_pages sp on sp.page_id=e.page_id;
select entry_id, period_order, start_date_undate, end_date_undate, end_type from raw.person_entry_service;
-- note vs period sweep: tenure_note_text / credit_summary_text dates vs raw.person_entry_service dates (all roster types)
-- unmerged duplicates: live persons grouped by (canonical_family_name, canonical_first_name, canonical_patronymic, ordinal_suffix) with count > 1
-- post-fix: entities.person live count; entities.person_link vs superseded persons; raw.person_entry_service for the 3 corrected entries
```

Result: 273 -> 264 flagged persons (after the relink repair: patronymic conflicts 30 -> 22, first-name 15 -> 5, start-date 209 -> 200, after-end 85, two-cities 13); 47 persons with a recorded end followed by later entries and no new start date, 42 with the end printed in an entry text, 5 not printed (Мосолова: transfer, date printed with a Cyrillic І; Ѳедорова: leaving line genuinely printed; Русецкій: promotion; Бакина 2-я and Николаева 3-я: spurious ends, scan-verified); 8 entries repeating the previous entry's end date (1 real: Бакина 2-я); 7 persons spanning Musicians with BalletArtists/ProductionTeam (6 genuine dual listings, 1 wrong merge Ивановъ); 94 live pairs with identical canonical name+patronymic+ordinal (59 likely same, 8 probable, 13 overlap, 14 check). After the repairs: live persons 3256, tombstones 2320, orphans 0, shift blocks 0 (person_link alignment), 119 informational name mismatches (was 129).

## 2026-10-05 -- TheaterSchoolStaff school headings: per-page school sequence and 1898-99 verification (issue #134)

```sql
-- stored school per page (python over outputs/full_run/raw: first segment of heading_path, counts per page and sequence in array order), all 99 TSS pages
-- which school(s) is each person on 1898-99 p003/p004 listed under in OTHER seasons?
select split_part(e.heading_path,' / ',1), count(*) from entities.person_link l join raw.person_entry e using(entry_id) join raw.source_pages sp on sp.page_id=e.page_id
where cast(l.person_id as varchar)=? and e.entity_type='TheaterSchoolStaff' and sp.season<>'1898-99' group by 1;
-- after the fix
select split_part(heading_path,' / ',1), count(*) from raw.person_entry where entry_id like 'theaterschoolstaff_1898-99%' group by 1;
```

Result: stored Moscow/Petersburg row counts per season were ~59-66 Moscow / 75-86 Petersburg everywhere except 1898-99 (11 / 123); all 48 persons on 1898-99 p003+p004 are listed only under the Moscow school in other seasons (48 of 48 "M-only"); after the fix 1898-99 has 59 Moscow and 75 Petersburg rows (raw and analysis.heading_path_clean agree).

## 2026-10-05 -- TheaterSchoolStaff name outliers and Легатъ/Головань spellings (issue #134)

```sql
-- per TSS person with >= 4 entries: entries whose family/first/patronymic occurs in <= 2 entries and is >= 70% similar to a spelling shared by >= 3 others
select cast(l.person_id as varchar), l.entry_id, e.page_id, e.family_name, e.first_name, e.patronymic, sp.season, p.display_name from entities.person_link l join entities.person p on p.person_id=l.person_id and p.superseded_by_person_id is null join raw.person_entry e using(entry_id) join raw.source_pages sp on sp.page_id=e.page_id where e.entity_type='TheaterSchoolStaff';
select e.entity_type, regexp_replace(e.family_name,' [0-9]-[йя]$','') f, count(*) from raw.person_entry e where e.family_name ilike 'Легат%' group by 1,2 order by 1,2;
select sp.season, e.family_name, count(*) from raw.person_entry e join raw.source_pages sp on sp.page_id=e.page_id where e.entity_type='TheaterSchoolStaff' and e.family_name ilike 'Голован%' group by 1,2 order by 1;
```

Result: 53 candidates (patronymic 22, family 23, first 8), 48 read on the scan, 9 corrected. Легатъ/Легать after the fixes: BalletArtists 33 Легатъ / 41 Легать; Graduates 2 / 1; TheaterSchoolStaff 15 / 2 (the two remaining are 1896-97 p001 e016 and 1905-06 p001 e019, sent to a blind read). Головань (ь): 1906-07, 1907-08, 1909-10; Голованъ (ъ): 1908-09.

## 2026-10-05 -- TheaterSchoolStaff section structure: stored rows vs two blind page maps (issue #134)

```sql
-- stored section path per row (python over outputs/full_run/raw: heading_path minus the school segment, list_number, family_name, array position), all 99 TSS pages;
-- compared with 198 reader page maps (/tmp/ss, archived in blind_sections/reader_results)
select entry_id, heading_path, list_number, family_name from raw.person_entry where entity_type='TheaterSchoolStaff';
select family_name, count(*) from raw.person_entry where entity_type='TheaterSchoolStaff' and family_name in ('Маннь','Маннъ','Тернизьень','Тернизьенъ') group by 1;
```

Result: 2,742 / 2,739 printed rows matched to stored rows by pass C / D; 2,734 rows agree across both passes and the stored section; 0 rows wrong in both passes; 7 surname rows read identically by both passes but differing from stored (Маннь x3, Тернизьень x3, Головань/Потѣхннъ already settled); after the six hard-sign corrections the TSS family_name values Маннь and Тернизьень no longer occur.

## 2026-10-05 — Issue #133: locating the spelling-question instances for a scan check

```sql
select e.page_id, e.list_number, e.season, e.title, x.name_printed, e.description_text
from analysis.production_entry_credit x join raw.production_entry e using (production_entry_id)
where x.name_printed like '%Мюль%' order by e.season;
select e.page_id, e.list_number, e.title, x.name_printed
from analysis.production_entry_credit x join raw.production_entry e using (production_entry_id)
where x.name_printed in ('Гершеля','К. В.','М. И. Чайковскаго','Мод. И. Чайковскаго','А. Фридмана','П. П. Шенка','П. П. Золотаренко') order by 4, 1;
```

Result: Мюльендорфера ×6 (Хрустальный башмачекъ, MSK 1890-97) and Мюльдорфера ×4 (Волшебный башмачекъ, MSK 1899-1903); Гершеля ×6; К. В. ×4; М. И. Чайковскаго ×1 and Мод. И. ×3 (Калькабрино). Every instance was then zoomed on the full-resolution scan, and the transcription matches the print in every case (details in known_issues.md #133, 2026-10-05).

## 2026-10-05 — Черемухинъ merge: verify result (3 persons -> 1)

```sql
SELECT family_name||', '||first_name||' '||patronymic, min(season), max(season), count(*)
FROM entities.person_link pl JOIN raw.person_entry pe USING (entry_id)  -- via verify_pt.py / apply_duplicate_merges.py
WHERE person_id LIKE '0c1633%' GROUP BY 1;
```

Result: one person, 'Черемухинъ, Михаилъ Никифоровичъ', 1890-91..1909-10, 40 entries; live persons 3250 -> 3248, tombstones 2326 -> 2328, 0 orphans, 0 shift blocks, quality flags 546 (unchanged), receipts identical.

## 2026-10-05 — Петровъ Василій Ивановичъ (TSS): subjects/headings of the three persons, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), right(e.heading_path,24), e.subject_taught, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('c11d62','e1cac8','50a743') ORDER BY 1,2;
```

Result: 20 entries. 1894-95..1905-06 'Выразительное чтеніе' (ballet dept), 1902-03..1909-10 'Практика драматическаго искусства' (drama courses, "съ 1 сентября 1902"). After merge: one person, 1894-95..1909-10, 20 entries; live 3248 -> 3246, tombstones 2328 -> 2330, 0 orphans, 0 shift blocks, flags 546, receipts identical.

## 2026-10-05 — Потѣхинъ Алексѣй Антиповичъ (TSS): three persons' entries, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), right(e.heading_path,30), e.subject_taught, e.rank_or_title, e.tenure_note_text, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('b53a76','8872b8','0fd64e') ORDER BY 1,2;
```

Result: 18 entries, all 'Почетные члены конференціи', one per season 1890-91..1907-08. After merge: one person, 18 entries; live 3246 -> 3244, tombstones 2330 -> 2332, 0 orphans, 0 shift blocks, flags 546, receipts identical.

## 2026-10-05 — Issue #133: is the roster Шиманъ the ballet composer "Г. Шиманъ"?

```sql
select p.display_name, a.season, a.city, a.entity_type, a.institution, a.heading_path, a.instrument, a.rank, a.title, a.tenure_note_text
from research.person p join research.person_appearance a using (person_id)
where p.canonical_family_name ilike 'Шиман%' or p.canonical_family_name ilike 'Щиман%' or p.canonical_family_name ilike 'Шимон%'
order by 1, 2;
```

Result: one roster person, Шиманъ, Михаилъ Викторовичъ: Moscow opera/ballet orchestra, violin (second violin from 1897-98), "съ 10 марта 1882 г.", 1890-91..1900-01, the last listing "† 7 декабря 1900 г.". The ballet credits are "Г. Шимана" ×5 and "Шимана" ×1 (Хрустальный башмачекъ, MSK 1890-97) and "Щимана" ×1 (Волшебный башмачекъ, MSK 1900-01). The initial Г. ≠ М., so they are not linked; it is open for RG.

## 2026-10-05 — Рюминъ Иванъ Ивановичъ (TSS): entries of 24f7fc and 2f3464, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), right(e.heading_path,34), e.rank_or_title, e.tenure_note_text, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('24f7fc','2f3464') ORDER BY 1,2;
```

Result: 24 entries, 1890-91..1899-00: 'Управляющій Училищемъ' (съ 27 мая 1887) + 'Почетные члены конференціи' lines; 2f3464 = only the 1899-00 manager line with '† 2 сентября 1899 г.'. After merge: live 3244 -> 3243, 0 orphans, 0 shift blocks, flags 546.

Correction to the entry above: the merged Рюминъ person has 23 entries (the "24" was a miscount; the listing printed 23 rows).

## 2026-10-05 — Добрынина Елена Андреевна (TSS): entries of 0ef17f and d42d9e, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), right(e.heading_path,34), e.tenure_note_text, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('0ef17f','d42d9e') ORDER BY 1,2;
```

Result: 10 entries, 'Классныя дамы', one per season 1890-91..1899-00, start 'съ 1 апрѣля 1884' (1896-97 prints 'съ апрѣля 1884', on d42d9e), '† 27 октября 1899' in 1899-00. After merge: live 3243 -> 3242, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Issue #133: "Волшебный башмачекъ" title, as transcribed (for a scan check)

```sql
select page_id, list_number, season, city, title, left(description_text, 40) from raw.production_entry where title ilike '%башмач%' order by season;
select distinct performance_title, count(*) from raw.event_entry_performance where performance_title ilike '%башмач%' group by 1 order by 2 desc;
```

Result: Хрустальный башмачекъ ×6 (MSK 1890-97). Волшебный башмачекъ ×4 (MSK 1899-1903): 1899-00 has the title "Волшебный башмачекъ (Сандрильона)", while 1900-03 put "(Сандрильона)." at the start of description_text. Repertoire: Хрустальный башмачекъ 21 (+2 excerpt rows), Волшебный башмачекъ 12. All 4 Волшебный titles were zoomed on the scans: "Волшебный башмачекъ" (letter-spaced, ъ ending) every time. "(Сандрильона)" is in regular type on all 4 pages.

## 2026-10-05 — Петровъ Иванъ Степановичъ (TSS): the two persons' entries and the 1906-10 Петровъ lines, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), right(e.heading_path,34), e.rank_or_title, e.tenure_note_text, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('527973','0aeaf9') ORDER BY 1,2;
SELECT sp.season, right(e.page_id,5), right(e.heading_path,40), e.subject_taught, e.family_name, e.first_name, e.tenure_note_text
FROM raw.person_entry e JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE e.entity_type='TheaterSchoolStaff' AND e.family_name LIKE 'Петров%' AND sp.season IN ('1906-07','1907-08','1908-09','1909-10');
```

Result: 19 tutor entries 1890-91..1907-08 (Воспитатели, since 1 сентября 1891) and 2 'Учителя приготовительныхъ классовъ' entries 1908-09, 1909-10 (since 15 ноября 1907); no Петровъ Иванъ among 1908-10 Воспитатели. After merge: live 3242 -> 3241, 0 orphans, 0 shift blocks, flags 546.

Correction to the Петровъ Иванъ Степановичъ entry above: 18 tutor entries (1890-91..1907-08), 20 in total after the merge; "19" was a miscount.

## 2026-10-05 — Боборыкинъ Петръ Дмитріевичъ (TSS): entries of c58d24 and 232905, school of the 1899-1903 lines, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), substr(e.heading_path,1,60), e.tenure_note_text, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('c58d24','232905') ORDER BY 1,2;
```

Result: 23 entries, all 'Почетные члены конференціи', 1890-91..1909-10; 1899-00 to 1901-02 listed under both the Moscow and the Petersburg school, the Moscow lines of 1900-01 and 1901-02 carrying 'Переведенъ тѣмъ же званіемъ въ С.-Петербургское училище.'. After merge: live 3241 -> 3240, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Казанскій Левъ Ивановичъ (TSS + doctors' lists): entries of 0b9603 and d0ad53, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), substr(e.heading_path,1,12)||'..'||right(e.heading_path,30), e.rank_or_title, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('0b9603','d0ad53') ORDER BY 1,2;
```

Result: 37 entries: Moscow doctor lists (Дежурные врачи / Штатный врачъ / Старшій врачъ, 'съ 20 апрѣля 1885', later 'съ 20 февраля 1885') and 'Врачъ при Училищѣ' lines (1891-92..1909-10, '(старшій врачъ при Дирекціи Императорскихъ театровъ въ Москвѣ)'); d0ad53 = the 1908-09 and 1909-10 school-doctor lines. After merge: live 3240 -> 3239, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Issue #133: is А. Н. Богдановъ (co-author of Хрустальный башмачекъ) anywhere on the roster, incl. the Moscow Theatre School staff?

```sql
select sp.season, sp.city, sp.entity_type, pe.page_id, pe.family_name, pe.first_name, pe.patronymic, pe.heading_path
from raw.person_entry pe join raw.source_pages sp using (page_id) where pe.family_name ilike '%огдан%' order by 1, 3;
select sp.season, count(*) filter (where pe.institution ilike '%моск%' or pe.heading_path ilike '%моск%') msk, count(*) tot
from raw.person_entry pe join raw.source_pages sp using (page_id) where sp.entity_type = 'TheaterSchoolStaff' group by 1 order by 1;
select ... from raw.person_entry pe join raw.source_pages sp using (page_id)
where concat_ws(' ', pe.institution, pe.heading_path, pe.rank_or_title, pe.subject_taught, pe.tenure_note_text, pe.credit_summary_text, pe.first_name) ilike '%огдан%';
select distinct sp.season, pe.family_name, pe.first_name, pe.patronymic, pe.subject_taught, pe.heading_path ... -- Moscow school dance teachers, 1890-92
```

Result: no Алексѣй / А. Н. Богдановъ anywhere. Every Богдановъ is SP: Александра Александровна (BalletArtists 1890-97), Михаилъ Михайловичъ (BalletArtists 1890-94), Георгій Поликарповичъ (Graduates 1904-05, BalletArtists 1904-10). The Moscow school IS covered every season (41-70 Moscow rows out of 111-152 school-staff rows a year, 1890-1910). Its dance teachers in 1890-92 were Мендесъ Іосифъ, Ермоловъ Иванъ Алексѣевичъ, Никитинъ Иванъ Дмитріевичъ (Танцы) and Гельцеръ Василій Ѳедоровичъ (Пластика и танцы, drama courses). No other text field mentions Богданов except Михаилъ's own heading. NB: another session is working on the theater-school staff today; this reflects full_run at query time.

## 2026-10-05 — Пчельниковъ Павелъ Михайловичъ (TSS + Administrators): entries of 4af6a7 and d54352, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), e.entity_type, substr(e.heading_path,1,12)||'..'||right(e.heading_path,30), e.rank_or_title, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('4af6a7','d54352') ORDER BY 1,2;
```

Result: 44 entries on 4af6a7 (Administrators 'Управляющій Конторою' since 16 июня 1882, 1890-91..1897-98; school 'Управляющій Училищемъ' to 1897-98; 'Почетные члены конференціи' every season) + 2 on d54352 (1908-09 p003 e004, 1909-10 p003 e003: 'Почетные члены конференціи'). My question text said d54352 held a Petersburg and a Moscow line; in fact it holds one line per season (both on p003). After merge: live 3239 -> 3238, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Габріель (TSS): the two single-entry persons, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), e.family_name, e.first_name, e.patronymic, right(e.heading_path,34), e.subject_taught, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('750b99','a550ac') ORDER BY 1,2;
```

Result: 2 entries — 1890-91 p001 e018 and 1891-92 p001 e017, 'Габріель', Французскій языкъ, Балетное отдѣленіе, 'съ 1 сентября 1890 г.'. After merge: live 3238 -> 3237, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Гавронскій (TSS): entries of 7029d5 and 6f5c3c, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), e.family_name, right(e.heading_path,34), e.subject_taught, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('7029d5','6f5c3c') ORDER BY 1,2;
```

Result: 9 entries (1894-95..1902-03), all 'Законъ Божій для учащихся Римско-Католическаго вѣроисповѣданія', ballet dept, 'съ 1 февраля 1895', 'Оставилъ службу 1 сентября 1902' in 1902-03. After merge: live 3237 -> 3236, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Жукова Вѣра Васильевна: entries of c03d21, 3e22b9, 3732cd, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), e.entity_type, e.family_name, e.first_name, e.patronymic, right(e.heading_path,34), e.subject_taught, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('c03d21','3732cd','3e22b9') ORDER BY 1,2;
```

Result: c03d21 = 1 BalletArtists entry (1890-91 SP p001 e023, 'Жукова 1-я', 'съ 22 іюля 1869', 'Оставила службу 1 марта 1891'); 3e22b9 = 7 TSS entries 1901-02..1907-08 (Танцы), 3732cd = 2 TSS entries 1908-09, 1909-10 (Танцы / Классическіе танцы), all 'съ 1 сентября 1901'. After merging 3732cd into 3e22b9: live 3236 -> 3235, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Преображенская Ольга Іосифовна: entries of 76d1b9 and de05ca, scan check of the 1908-09 start date, then merge verification

```sql
SELECT sp.season, sp.city, right(l.entry_id,10), e.entity_type, e.family_name, e.first_name, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('76d1b9','de05ca') ORDER BY 1,2;
```

Result: 76d1b9 = 20 entries (BalletArtists 1890-91..1907-08 and 1909-10, start 'съ 1 іюня 1889'; plus a 1900-01 TSS 'Танцы' line, 'съ 1 мая 1901') with no 1908-09 entry; de05ca = 1 entry, balletartists_1908-09_SP_p003 e006, 'съ 1 іюня 1899'. The scan (printed p. 91, no. 74, 2x enlargement of a full-resolution crop) prints 1899 -- a genuine print typo. After merge: 21 entries, live 3235 -> 3234, 0 orphans, 0 shift blocks, flags 546. (My question text said the start date reads 1889 "in 18 volumes"; it is 19 BalletArtists volumes.)

## 2026-10-05 — Піотровичъ (TSS): entries of 088ec9 and 224c50, then merge verification

```sql
SELECT sp.season, right(l.entry_id,10), e.family_name, right(e.heading_path,34), e.subject_taught, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('088ec9','224c50') ORDER BY 1,2;
```

Result: 4 entries 1890-91..1893-94, all 'Законъ Божій для учащихся Римско-Католическаго (вѣро)исповѣданія', ballet dept, 'съ 1 ноября 1888', 'Оставилъ преподаваніе 1 сентября 1894' in 1893-94. After merge: live 3234 -> 3233, 0 orphans, 0 shift blocks, flags 546. Note: research.person reads 3306 since the ballet-creator thread's uncommitted build_research_model.py edits (production_list persons, 73) are now part of every rebuild.

## 2026-10-05 — Issue #133 step 3: building and verifying the production research tables

```sql
-- list entries -> matched works (via build_research_model.ballet_list_matches), excerpts collapsed to parents
-- => 443 one work, 35 several, 2 none
select person_source, count(*), count(wikidata_qid) from research.person group by 1;
select wikidata_source, count(*) from research.person group by 1;
select count(*) - count(distinct person_id) from research.person;
select season, city, list_title from research.production where work_id is null;
select count(*) from research.production_credit pc left join research.person p using (person_id) where p.person_id is null;
select count(*) from research.production pr left join research.work w using (work_id) where pr.work_id is not null and w.work_id is null;
select identification_status, count(*) from research.production_credit group by 1;
select p.display_name, pc.role_category, count(*), count(distinct pr.work_id) from research.production_credit pc
  join research.person p using (person_id) join research.production pr using (production_id) group by 1, 2 order by 3 desc limit 8;
-- sqlite export: Спящая красавица credits; Фокинъ's credits
```

Result: persons roster 3233 (32 with a QID) + production_list 73 (24 with a QID); wikidata_source link_wikidata 28 / rg_review 28; 0 duplicate ids, 0 orphan credits, 0 orphan works. 2 productions have no work (1902-03 SP Донъ-Кихотъ Ламанчскій, 1904-05 SP Дочь Фараона). identification_status: confirmed 1209, proposed 1 (Щимана). Top: Петипа author 115 credits / 30 works; Пуни music 103 / 13; Сенъ-Леонъ 68; Минкусъ 60; Дриго 49. Спящая красавица = Перро (source, Q128460), Чайковскій (music, Q7315), Петипа (author + staging, Q312320). person_appearance unchanged at 23203.

## 2026-10-05 — Рыхлякова cluster (ballet artists + TSS + Graduates): all entries of 8 persons, scan check of the 1904-05 start date, then Варвара-dancer merge verification

```sql
SELECT sp.season, sp.city, right(l.entry_id,10), e.entity_type, e.family_name, e.first_name, e.patronymic, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('1150d3','87c046','023b1e','5d6d24','33e281','af49d5','760668','7bc39e') ORDER BY 1,2;
```

Result: Варвара (1-я): 87c046 17 entries 1890-91..1907-08 (no 1904-05), 023b1e 1904-05 (misparsed fields; scan no. 95 prints 'съ 1 сентября 1890'), 1150d3 1908-09/1909-10 ('съ 1 сентября 1890'), 5d6d24 TheaterSchoolStaff 1909-10 ('съ 1 ноября 1907'). Наталья (2-я): 33e281 12 entries, 760668 5, af49d5 1 (1904-05, misparsed), 7bc39e Graduates 1891-92. After merging 023b1e + 1150d3 into 87c046: live 3233 -> 3231, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Рыхлякова 2-я Наталья: merge verification (evidence in the cluster query above)

Result: 760668 (5 entries), af49d5 (1904-05, misparsed fields) and 7bc39e (Graduates 1891-92) merged into 33e281 (12 entries) -> one person, 1891-92..1909-10. Counts in the verify output; 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Sizing duplicate works in research.work (all genres, not just ballet)

```sql
select work_id, canonical_title, canonical_genre, appearance_count, excerpt_of_work_id from research.work;
-- clustered in Python on a letters-only key: build_entities._title_key(_strip_genre_suffix(title)),
-- ё->е, then every non-letter/digit removed (spaces, hyphens, dashes, commas, apostrophes)
```

Result: 3657 works; 408 clusters with more than 1 work_id under the letters-only key. 84 have the same (or blank) genre: pure punctuation/spacing variants (Изъ-за / Изъ за мышенка; Правда—хорошо / Правда хорошо; Донъ-Кихотъ / Донъ Кихотъ; Звѣзды / Звёзды; Chez l'Avocat / l’Avocat). 324 have differing genres: about 74 are only abbreviation variants (rough family match: оп./опера, бал./бал.-феерія), and about 250 involve genuinely different genre words. Most of those 250 are the same work with the genre printed differently (Шашки шут./ш./шутка/ком.; Коппелія бал. ×103 / оп. ×1); a minority are genuinely different works (Фаустъ оп. vs драм. поэма; Ромео и Джульетта оп. vs траг.; Карменъ оп. vs бал.; Снѣгурочка оп. vs весенняя сказка). Separately, 107 excerpt-looking works (276 appearances) are not linked to a parent (excerpt_of_work_id null).

## 2026-10-05 — Рыхлякова Варвара (TSS 1909-10) merge verification, and the 1909-10 ballet-department teacher list

```sql
SELECT sp.season, right(l.entry_id,10), e.heading_path, e.subject_taught, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6)='5d6d24';
SELECT sp.season, right(e.page_id,5), e.family_name, e.first_name, e.heading_path, e.subject_taught
FROM raw.person_entry e JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE e.entity_type='TheaterSchoolStaff' AND sp.season='1909-10' AND e.subject_taught LIKE '%анц%';
```

Result: 5d6d24 = 1 entry (1909-10 p001 e024, SPb ballet department teachers, 'съ 1 ноября 1907', subject None); the other 1909-10 dance-subject lines are Андріановъ, Гавликовскій, Жукова, Куличевская, Обуховъ, Фокинъ etc. After merge: live 3228 -> 3227, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — Рыхлякова TSS 1909-10: is the missing subject an extraction drop? (RG's question)

```sql
-- raw JSON, theaterschoolstaff_1909-10_p001 entries 19-30 (subject_taught per entry), plus the scan p. 146 zoomed
```

Result: entry 18 (e024) has subject_taught null; every neighbouring teacher has one. The scan (printed p. 146, no. 18) prints "Рыхлякова, Варвара Трофимовна (съ 1 ноября 1907 г.)." with nothing after the date, so the null is faithful to the print, not an extraction miss. The uncertain-list entry 11 text was corrected accordingly.

## 2026-10-05 — Тихоміровъ Василій Дмитріевичъ: entries of 6d97a1 and ed66b3, then merge verification (also: Рыхлякова TSS merge actually applied)

```sql
SELECT sp.season, sp.city, right(l.entry_id,10), e.entity_type, left(e.heading_path,50), e.subject_taught, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('6d97a1','ed66b3') ORDER BY 1,2;
```

Result: 6d97a1 = 19 entries 1897-98..1907-08 (Moscow school dance teacher 'съ 1 октября 1896' + Moscow ballet artist 'съ 1 сентября 1893'), ed66b3 = 5 entries 1908-09, 1909-10 (same two lines). Correction to the 5d6d24 entry above: its run printed "3228 -> 3228" -- the merge had been silently skipped by the script's survivor-based "applied" filter (87c046 was already a survivor). The script now skips by loser; the next run applied 5d6d24 -> 87c046 and ed66b3 -> 6d97a1 together: live 3228 -> 3226, Рыхлякова Варвара person now 21 entries, Тихоміровъ 24 entries.

## 2026-10-05 — Work consolidation step 1 (punctuation/spacing): preview on a copy of full_run

```sql
-- build_entities.build_work() with the new _match_key grouping, run on a COPY of full_run
select count(*), count(excerpt_of_work_id) from entities.work;   -- before / after
select count(distinct title_key), count(*), count(distinct title_key) filter (where likely_cross_language) from entities.work_genre_candidate;  -- full_run vs preview
select x.old_canonical_title, x.n_performances, w.canonical_title, w.canonical_genre, w.appearance_count, x.old_work_id, x.new_work_id
from entities.work_id_crosswalk x join entities.work w on w.work_id = x.new_work_id order by w.appearance_count desc;
```

Result: works go 3657 → 3550; 107 work_ids retire into 3550 surviving ones (0 new ids, so every non-merged work keeps its id); 340 performances move; excerpt links unchanged at 179. Genre-split titles go 321 → 324 (variants that now group together); cross-language stays 2 (unchanged). Every merge is within one genre fold. Full list: docs/eval/work_consolidation_step1_merges.csv.

## 2026-10-05 — Легат* surname spellings by list/season/person (BalletArtists "Легать" check)

```sql
SELECT e.entity_type, e.family_name, e.first_name, count(*), min(sp.season), max(sp.season)
FROM raw.person_entry e JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE e.family_name LIKE 'Легат%' OR e.family_name LIKE 'Легать%' GROUP BY 1,2,3 ORDER BY 1,2,3;
-- then per-row listing (season, page_id, entry_id, list_number, family_name, first_name) for the 42 'Легать%' rows,
-- the persons holding Легат* entries (entities.person_link JOIN raw.person_entry), and after the fix:
SELECT entity_type, family_name, count(*) FROM raw.person_entry WHERE family_name LIKE 'Легат%' OR family_name LIKE 'Легать%' GROUP BY 1,2 ORDER BY 1,2;
```

Result: before: 42 rows 'Легать*' (41 BalletArtists, 1 Graduates) vs 40 'Легатъ*'. After the 47-edit correction: only one 'Легать 2-я' (1890-91 SP p003 no. 64, genuine print) remains; BalletArtists 'Легатъ' 33, 'Легатъ 1-й' 11, '1-я' 7, '2-й' 9, '2-я' 6, '3-й' 6, '3-я' 1; Graduates 3; TheaterSchoolStaff 3+7+7. Live persons 3226, tombstones 2350 (unchanged).

## 2026-10-05 — Work consolidation step 3 found already live in full_run (applied by a parallel session's rebuild)

```sql
select recorded_on, count(*), sum(n_performances) from entities.work_id_crosswalk group by 1;
select count(*) from research.work; select count(*) from research.performance; select count(*) from entities.person;
-- work_ids now in full_run that were not in the step-1 state (copy taken right after step 1)
select x.old_work_id, x.new_work_id, x.old_canonical_title, x.n_performances, w.canonical_title, w.canonical_genre, w.appearance_count
from entities.work_id_crosswalk x join entities.work w on w.work_id = x.new_work_id;  -- minus the step-1 pairs
```

Result: full_run has 3383 works (step 3 applied). The crosswalk has 276 rows / 927 performances: 107 from step 1 + 169 from step 3, recorded 2026-10-05. research.work is 3383 and research.performance is still 29568. 2 work_ids are new rather than inherited: Птички пѣвчія [оперет.] and Заварила кашу — расхлебывай [ф.]. The parallel session's ~12:21 rebuild ran build_entities.py while the step-3 code (before the id-inheritance fix) was on disk. Merge list (169 merges into 125 works): docs/eval/work_consolidation_step3_merges.csv.

## 2026-10-05 — Legat family person records: timelines of the Сергѣй, Иванъ and Александра persons; Иванъ merge-log check

```sql
SELECT sp.season, sp.city, right(l.entry_id,10), e.entity_type, e.family_name, e.first_name, e.patronymic, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('714fca','2cdfb1','b21c8b','651c58','437e79','495cd4','4f0350','c26b2e') ORDER BY 1,2;
SELECT left(cast(person_id_1 as varchar),6), left(cast(person_id_2 as varchar),6), status, match_reason FROM entities.person_merge_log
WHERE left(cast(person_id_1 as varchar),6) IN ('437e79','495cd4','d54949') OR left(cast(person_id_2 as varchar),6) IN ('437e79','495cd4','d54949');
```

Result: Сергѣй Густавовичъ 21 entries over 4 persons (all 'съ 1 іюня 1894', TSS 'съ 1 сентября 1898', '† 18 октября 1905'); Иванъ 8 entries over 2 persons (explicit break/re-engagement printed 1897-00); Александра: Graduates 1906-07 (joined 1 іюня 1907) + BalletArtists 1907-08 (съ 1 іюня 1907). The Иванъ check found 495cd4 tombstoned into 437e79 with no log row of its own (backups: 495cd4 live); a manual row was inserted after RG confirmed. After the three merges: live 3226 -> 3221, tombstones 2350 -> 2355, 0 orphans, 0 shift blocks, flags 546, receipts identical.

## 2026-10-05 — Work consolidation step 2 (unlinked excerpts): survey and preview on a copy

```sql
select canonical_title, canonical_genre, appearance_count from research.work where excerpt_of_work_id is null order by canonical_title;
-- filtered in Python for excerpt vocabulary => 118 excerpt-looking unlinked works / 379 performances
-- preview: worktree build_work() with the step-2 fallback matcher on a copy of full_run
select w.work_id, w.canonical_title, w.canonical_genre, w.appearance_count, w.excerpt_note, p.canonical_title, p.canonical_genre
from entities.work w left join entities.work p on p.work_id = w.excerpt_of_work_id;
```

Result: 118 candidates split into ~75 real excerpts the regexes missed; non-excerpts (Дивертиссементъ 81, Сцена г. Горбунова 49, Изъ огня да въ полымя…); and titles with no usable base or only a genitive base. Preview: 56 new excerpt links (87 performances), 0 links lost, all work_ids unchanged; excerpt links 179 → 237. Two wrong links in the first preview were fixed before showing RG: "Сц. 4-го д. оп. Балъ маскарадъ" (now → Балъ-маскарадъ оп.), and "Прологъ драмы Псковитянка" (now left unlinked: drama vs opera). List: docs/eval/work_consolidation_step2_excerpt_links.csv.

## 2026-10-05 — Step 2 curated excerpt links: performance context for genitive / art-form-ambiguous excerpts

```sql
-- for each excerpt title: season, city, theater, and the whole billing of its event
select e.season, e.city, e.theater_canonical, eep.performance_title,
       (select string_agg(p2.performance_title || coalesce(' [' || p2.genre || ']', ''), ' | ' order by p2.performance_order)
          from raw.event_entry_performance p2 where p2.event_id = eep.event_id)
from raw.event_entry_performance eep join analysis.event_entry e using (event_id)
join entities.work_link wl on wl.raw_performance_id = eep.performance_id join entities.work w using (work_id)
where w.canonical_title = ?;
select canonical_title, canonical_genre, appearance_count from research.work where canonical_title ilike ? || '%' and excerpt_of_work_id is null;
```

Result: "2 сцены изъ Бориса Годунова" and "Сцена изъ Каменнаго гостя" are from the 1898-99 Александринскій Pushkin-centenary gala (Моцартъ и Сальери, Скупой рыцарь, Пиръ во время чумы), so they are Pushkin's dramas, not the operas. The Русалка gala scenes (1898-99 Малый) are left alone per RG's 2026-09-26 and #94 rulings. Preview with 13 curated links: 69 new excerpt links in total (104 performances), 0 lost, ids unchanged.

## 2026-10-05 — Ѳедорова Марія Дмитріевна, Марквардтъ Августъ, Шнейдеръ/Шредеръ Карлъ (uncertain-list items 5, 6, 7): timelines and verification

```sql
SELECT sp.season, sp.city, right(l.entry_id,10), e.family_name, e.first_name, e.patronymic, e.instrument, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('2475a6','230477','8acb78','019ed1','ce6489','4396b9','cd67fa') ORDER BY 1,2;
SELECT sp.season, right(e.entry_id,10), e.list_number, e.family_name, e.first_name, e.instrument, left(cast(l.person_id as varchar),6), e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE e.entity_type='Musicians' AND sp.city='SP' AND (e.family_name LIKE 'Шнейдер%' OR e.family_name LIKE 'Шредер%' OR e.family_name LIKE 'Шрейдер%') ORDER BY 1,2;
SELECT sp.season, right(l.entry_id,10), e.list_number, e.family_name, e.first_name, e.patronymic, e.tenure_note_text, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE e.entity_type='BalletArtists' AND sp.city='SP' AND (e.family_name LIKE 'Щедрина%' OR e.family_name LIKE 'Ѳедорова%' OR e.family_name LIKE 'Федорова%') AND sp.season>='1903-04';
```

Result: Ѳедорова — 19 entries 1890-91..1907-08 on one person; 1904-05 no. 114 prints start 1 іюня 1885 and "Оставила службу 1 іюня 1905" (scan zoom), no. 125 Щедрина prints the same note (start 12 мая 1885, absent after 1904-05); 1905-06, 1906-07, 1907-08 list her again with 12 мая 1885. Марквардтъ — 230477 (bandmaster line every season 1890-91..1905-06 + orchestra line in 1890-94, 1895-96, 1904-05) and 8acb78 (orchestra line 1894-95, 1896-97..1902-03): complementary seasons; merged, 30 entries. Шнейдеръ/Шредеръ — blind read of 11 scan lines confirmed all stored values: percussionist Шредеръ Августовичъ (since 1 декабря 1894) to 1906-07; trombonist Шнейдеръ Ѳедоровичъ (since 1902, Mikhailovsky; Mariinsky list from 1908-09 'съ 1 сентября 1907'); 1907-10 percussion lines print Шредеръ Ѳедоровичъ, 1902 and were linked to the trombonist 019ed1 -> moved to cd67fa (RG). After both operations: live persons 3220, tombstones 2356, 0 orphans, 0 shift blocks, flags 546, receipts identical.

## 2026-10-05 — Шредеръ Карлъ (percussion): start-date year per season (1884 vs 1894), then merge verification

```sql
SELECT e.page_id, e.list_number, sp.season, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6)='cd67fa' AND sp.season<='1903-04' ORDER BY sp.season;
```

Result: stored start 'съ 1 декабря 1894' in 1894-95, 1895-96, 1903-04 and 'съ 1 декабря 1884' in 1896-97..1902-03; blind reader and my own view of three pages (1898-99, 1899-00, 1900-01) confirm 1884 is printed (декабря present; the reader's "missing декабря" claim was wrong). After merging 4396b9 into cd67fa: one percussionist, 16 entries 1894-95..1909-10; live 3219 -> 3218, tombstones 2357 -> 2358, 0 orphans, 0 shift blocks, flags 546.

## 2026-10-05 — are the Season Reviews in the database, and what would mentions link to?

RG asked what the process is for identifying people, works and events in the
season reviews.

```sql
SELECT table_schema, table_name FROM information_schema.tables ORDER BY 1,2;
SELECT count(*) FROM research.person;   -- and research.work, research.event
DESCRIBE research.work;
```

Result: **no table in any schema has "review" in its name.** The season
reviews are not in the DuckDB file at all — they exist only as
`outputs/reviews/merged_full/review_block.csv` and the 41 Markdown reading
files. There is therefore nowhere for a review mention to be stored, which
is deferred item §12.5 of docs/season_reviews.md ("whether reviews enter the
DuckDB file, and what those tables look like") and still undecided.

Link targets that DO exist: research.person 3,290 rows, research.work 3,386,
research.event 31,203. research.work carries canonical_title,
canonical_genre, parent_genre, excerpt_of_work_id — but no composer column
(see §12.11, composers deferred).

## 2026-10-05 — Work consolidation step 4 (art forms): B/C performance context and preview on a copy

```sql
-- every performance behind the B slips and C titles: date, city, theater, printed title/genre, full bill
select coalesce(dc.corrected_date_undate, e.date_undate), e.city, e.theater_canonical, eep.performance_title, eep.genre,
       (select string_agg(p2.performance_title || coalesce(' [' || p2.genre || ']', ''), ' | ' order by p2.performance_order)
          from raw.event_entry_performance p2 where p2.event_id = e.event_id)
from raw.event_entry_performance eep join analysis.event_entry e using (event_id) left join analysis.event_entry_date_check dc using (event_id)
join entities.work_link wl on wl.raw_performance_id = eep.performance_id join entities.work w using (work_id)
where w.canonical_title = ? [and w.canonical_genre = ?] order by 1;
-- preview: worktree build_work() (art-form identity + work_artform_overrides.csv) on a copy of full_run
```

Result:
- B: Коппелія / Конекъ-Горбунокъ / Баядерка "оп." are each the sole item at the Большой (1907-08); Раймонда "оп." ×2 is the Маріинскій (1902, 1909); Черевички "эп," is the Маріинскій (1909); Евгеній Онѣгинъ "лир. сц." is the Маріинскій (1904). Сельская честь "бал." is on a Маріинскій 1906 mixed charity bill, not scan-checked, so it is held. Очарованный лѣсъ "изъ бал." (1907) is an excerpt.
- C: every title is a drama-theatre curtain-raiser. Не бывать-бы счастью (SP Михайловскій/Александринскій 1891-93), Макаръ Алексѣевичъ Губкинъ (SP Александринскій 1892-93), Русскія пѣсни въ лицахъ (SP Александринскій 1894-95) and Парики (Moscow Малый 1895-99) each alternate "опер." and "оперетта". Угнетенная невинность (1890-93) is mostly ш./вод. Званый вечеръ съ итальянцами: 1904 Маріинскій gala and Александринскій, Moscow Большой 1908 (опер. / оперетта). Соломенная шляпка "оп.-вод." is the Moscow Новый, 1905.
- Preview: works 3386 → 3149 (237 merges into 203 works; 0 new ids); excerpt links 257 → 261, 0 lost; titles split by genre 238 → 44. The ballet record lists 6 titles (Волшебная флейта, Карменъ, Млада, Сонъ въ лѣтнюю ночь, Сельская честь, Цыганка).

## 2026-10-05 — Карменъ printed "бал." / "др." at the Большой: scan check and stats-page cross-check

```sql
-- the non-opera Карменъ performances
select coalesce(dc.corrected_date_undate, e.date_undate), e.city, e.theater_canonical, e.page_id, e.date_text, eep.performance_title, eep.genre
from raw.event_entry_performance eep join analysis.event_entry e using (event_id) left join analysis.event_entry_date_check dc using (event_id)
where eep.performance_title ilike 'Карменъ%' and coalesce(eep.genre, '') not in ('оп.', 'оп');
-- Moscow sessions with a бал.-genre work, 1906-07 and 1907-08, and how many are Карменъ
select count(distinct e.event_id), count(distinct e.event_id) filter (where exists (... performance_title ilike 'Карменъ%'))
from analysis.event_entry e where e.season = ? and e.city = 'Moscow' and e.event_status = 'performed' and exists (... genre ilike '%бал%');
```

Result: 3 performances, all Большой, all sole items, and all scan-confirmed as printed. "Карменъ, бал." on 28 Jan 1907, matinee, 971.01 р. (1906-07 p029); "Карменъ, бал." on 16 Sep 1907, matinee, 736.51 р. (1907-08 p003); "Карменъ, др." on 23 Sep 1908, evening, 3013.43 р. (1908-09 p006). Stats-page cross-check: see the counts printed alongside; season_stats_comparison.md has 1906-07 Moscow Repertoire 51 vs stats 49 ballet (Repertoire has more), and 1907-08 Moscow 47 vs 48 (= stats once Коппелія "оп." counts as ballet).
Counts printed: 1906-07 Moscow 51 sessions with a бал.-genre work (1 is Карменъ); 1907-08 Moscow 46 (1 is Карменъ). The 1907-08 total here (46) does not reproduce season_stats_comparison.md's 47 (its counting rule differs), so the stats-page evidence on Карменъ is inconclusive.

## 2026-10-05 — Карменъ "бал." at the Большой vs the Season Reviews (RG: is there a review that helps?)

```sql
select coalesce(dc.corrected_date_undate, e.date_undate), e.time_of_day, e.theater_canonical,
       (select string_agg(p.performance_title || coalesce(', ' || p.genre, ''), ' | ' order by p.performance_order)
          from raw.event_entry_performance p where p.event_id = e.event_id)
from analysis.event_entry e left join analysis.event_entry_date_check dc using (event_id)
where coalesce(dc.corrected_date_undate, e.date_undate) = ? and e.theater_canonical = 'Большой';
-- for 1907-09-16, 1907-09-30, 1907-10-24, 1908-01-06, 1907-01-28
```

Result: "Карменъ" appears in neither the 1906-07 nor the 1907-08 Moscow ballet review. The 1907-08 review (scan-checked, folio 154) gives «Жизель» on "1907 г. сентября 16-го, 30-го, октября 24-го; 1908 г. января 6-го", with an Études divertissement. The Repertoire has "Жизель, бал. | Дивертиссементъ" on 30 Sep, 24 Oct and 6 Jan (evening), but on 16 Sep it has matinee "Карменъ, бал." and evening "Конекъ-Горбунокъ, бал." (no Жизель). 1907-01-28: matinee "Карменъ, бал.", evening "Тщетная предосторожность | Арлекинада". The 1906-07 review doesn't mention 28 Jan, and its Жизель revival was 18 Feb 1907, after that date.

## 2026-10-05 — Итцигсонъ, Цыбинъ, Завѣтновскій (check/overlap class of the duplicate pairs): timelines and verification

```sql
SELECT sp.season, sp.city, right(l.entry_id,10), e.entity_type, e.family_name, e.first_name, e.patronymic, e.instrument, e.list_number, e.heading_path, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE left(cast(l.person_id as varchar),6) IN ('08a1a5','4dcddd','58db32','00c2fa','1c7f9e','33ecbf','2658b3') ORDER BY 1,2,3;
SELECT sp.season, sp.city, e.page_id, e.list_number, e.first_name, e.patronymic, e.instrument, e.tenure_note_text
FROM raw.person_entry e JOIN raw.source_pages sp ON sp.page_id=e.page_id WHERE e.family_name LIKE 'Завѣтнов%' OR e.family_name LIKE 'Заветнов%' ORDER BY 1;
```

Result: Итцигсонъ — 19 entries over two persons (Репетиторы, since 1 августа 1882, 1890-91..1907-08; 1906-07 in both the orchestra and ballet-troupe lists); merged. Цыбинъ — Moscow flute since 1 апрѣля 1897 (1900-01..1907-08) and Petersburg flute since 1 сентября 1907 (1908-09, 1909-10); merged, uncertain. Завѣтновскій — Викторъ 1901-02/1902-03 (left 1 Sept 1902), Николай 1904-05..1907-08 (since 15 октября 1904), Викторъ 1908-09/1909-10 (since 15 октября 1904; both scan-confirmed); parked. After the two merges: live persons 3218 -> 3216, tombstones 2358 -> 2360, 0 orphans, 0 shift blocks, flags 546, receipts identical.

## 2026-10-05 — Новикова Екатерина: two Moscow graduate records vs the two Moscow dancers, then merge verification

```sql
SELECT sp.season, sp.city, right(l.entry_id,10), e.entity_type, e.family_name, e.first_name, e.patronymic, e.list_number, e.heading_path, e.tenure_note_text, left(cast(l.person_id as varchar),6)
FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) JOIN raw.source_pages sp ON sp.page_id=e.page_id
WHERE e.family_name LIKE 'Новикова%' ORDER BY 1,2,3;
SELECT e.page_id, e.entry_id, e.institution, e.heading_path, e.list_number, e.family_name, e.first_name, e.tenure_note_text
FROM raw.person_entry e WHERE e.entry_id IN ('graduates_1899-00_p001__e008','graduates_1891-92_p002__e006');
```

Result: two Moscow-school graduate lines (1891-92 no. 6, note 'съ 1-го сентября 1892 г. въ Московскую балетную труппу'; 1899-00 no. 8, no note) and two Moscow dancers (Екатерина Александровна since 1 сентября 1892; Екатерина Дмитріевна since 1 сентября 1900). Both graduate lines attached (RG): live persons 3216 -> 3214, tombstones 2360 -> 2362, 0 orphans, 0 shift blocks, flags 546, receipts identical.

## 2026-10-06 — 1908-11 ballet lists: is the combined CSV identical to production for the 480 earlier entries?

```sql
SELECT * FROM raw.production_entry;  SELECT * FROM raw.production_entry_performance;
-- compared field by field (NULL = '') in Python against outputs/ballet_productions_all_2026-10-06/*.csv
```

Result: 0 differing fields over 480 entries / 1,881 dates.

## 2026-10-06 — after loading: did any pre-1908 credit or credit link change?

```sql
SELECT count(*) FROM (SELECT * FROM bk.analysis.production_entry_credit EXCEPT SELECT * FROM analysis.production_entry_credit);
SELECT count(*) FROM (SELECT * FROM bk.entities.production_credit_link EXCEPT SELECT * FROM entities.production_credit_link);
```

Result: 0 and 0. Totals are now 1,500 credits and 1,495 links (1,215 and 1,210 before).

## 2026-10-06 — research-layer diff against the pre-load backup

```sql
SELECT count(*) FROM (SELECT * FROM bk.research.<t> EXCEPT SELECT * FROM research.<t>);  -- and the reverse, per table
```

Result: event, performance, person_appearance and theater are unchanged. production
gained 111 rows and production_credit 285. In work, 36 rows changed: parent_genre
became ballet for 11 genuine ballets, and the parent_genre_note season lists grew. In
person, 12 rows were added and 30 changed last_attested_season.

## 2026-10-06 — which 1908-11 productions match no Repertoire work?

```sql
SELECT season, city, list_title FROM research.production WHERE season >= '1908-09' AND work_id IS NULL;
```

Result before the aliases: Донъ-Кихотъ Ламанчскій SP 1908-09 and 1909-10, Ѳетида и Пелей
SP 1908-09, and all 37 entries for 1910-11, whose Repertoire is not yet in production.
After the aliases, every 1908-10 production matches.

## 2026-10-06 — Issue #135: 1910-11 onboarding checks (all against scratch/integration DBs, then production)

- Ballet-genre performances 1908-11 not on any Ballet Production list (integration DB, lists from
  outputs/ballet_productions_all_2026-10-06): 358 performances, 6 not on a list -- Донъ Кихотъ Ломанчскій (1908-09 MSK),
  Ѳемида и Пелей (1908-09 SP; list prints Ѳетида), two Конекъ-горбунокъ act excerpts (1909-10), Балетный
  дивертиссментъ x2. CSV: outputs/integration_1910-11/ballets_not_on_lists_1908-11.csv.
- Every «Кихот/Quichotte» performance 1890-1911: all «бал.» (Большой, Маріинскій) except 1910-11 Большой «героич. ком.» x12
  (Massenet's opera). No play of that name.
- pipeline/compare_season_stats.py on the integration DB (outputs/integration_1910-11/season_stats_compare/): 1910-11
  Moscow ballet 51 vs 52 sessions, receipts 126,983.90 both; Moscow opera 180 vs 160 (Донъ-Кихотъ героич. ком. 12,
  Гугеноты excerpts 5, Валкирія/Карменъ 2); SP opera 167 vs 156.
- pipeline/compare_productions_repertoire.py, 1908-11 lists vs Repertoire (outputs/ballet_list_check_1908-11/):
  1908-09 MSK 53/55, SP 72/73; 1909-10 MSK 50/50, SP 64/65; 1910-11 MSK 52/52, SP 74/80 exact+excerpt.
- Control vs production and integration vs control, table by table (EXCEPT queries): 0 changed rows except the 5
  1909-10 performances fixed above. Production vs pre-promotion backup: research.person QIDs 56 -> 66, none lost.

## 2026-10-06 — Келеръ Морицъ: how many live records, and what does each cover?

```sql
SELECT person_id, display_name, superseded_by_person_id FROM entities.person WHERE display_name ILIKE 'Кел%ръ%';
SELECT e.page_id, e.family_name, e.first_name, e.patronymic, e.heading_path, e.instrument, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING (entry_id) WHERE l.person_id IN (<2884550f>, <ab138e8b>, <ad393322>);
```

Result: three live records for one man, with the same start date (1 сентября 1881) and
a continuous career. After the merge there is one person (2884550f) with 20 entries,
1890-91..1907-08. The entities diff against the pre-merge backup is 2 person rows and
6 person_link rows.

## 2026-10-06 — 1910-11 ballet-list productions after #135

```sql
SELECT season, count(*) FILTER (WHERE work_id IS NULL), count(*) FROM research.production GROUP BY 1;
```

Result for 1910-11: 1 of 37 unmatched (Фіаметта, SP). 1908-09 and 1909-10: 0 unmatched.

## 2026-10-06 — Келеръ Эрнестъ Іосифовичъ: two live records?

```sql
SELECT e.page_id, e.family_name, e.first_name, e.patronymic, e.instrument, e.tenure_note_text
FROM entities.person_link l JOIN raw.person_entry e USING (entry_id) WHERE l.person_id IN (<3df85e8e>, <c5677456>);
```

Result: one flautist, start 1 декабря 1871, 1890-91..1906-07 with no overlap. After the
merge there is one person (c5677456) with 17 entries; the diff is 1 person row and 5 links.

## 2026-10-06 — coverage: pages per season per section, plus ballet-list entries

```sql
SELECT season, entity_type, count(*) FROM raw.source_pages GROUP BY ALL
UNION ALL SELECT season, 'BalletProductionList', count(*) FROM raw.production_entry GROUP BY ALL;
```

Result: 21 seasons, 1890-91..1910-11. Administrators, BalletArtists, Musicians,
ProductionTeam, Repertoire and TheaterSchoolStaff are present every season. Graduates
has no pages in 1907-08. The ballet production lists have 0 entries for 1905-06,
1906-07 and 1907-08, and there are no scans for those seasons in
pdf/Spiski_BalletProductions.

## 2026-10-06 — ballet-list creators with a Wikidata ID, after RG's 41 new accepts

```sql
SELECT count(DISTINCT pc.person_id), count(DISTINCT pc.person_id) FILTER (WHERE p.wikidata_qid IS NOT NULL)
FROM research.production_credit pc JOIN research.person p USING (person_id);
```

Result: 108 creators, of whom 74 have a QID. That is 72 decided on the review page,
plus roster-linked people whose QID came from person_wikidata_link.
entities.creator_wikidata_link has 72 rows (31 before).

## 2026-10-06 — Where were comic operas (комич. оп. / opéra-comique) performed? (RG, re: Корневильскіе колокола)

```sql
select p.verbatim_title, p.verbatim_genre, t.canonical_name, min(e.season), max(e.season), count(*)
from research.performance p join research.event e using(event_id) join research.theater t using(theater_id)
where regexp_matches(lower(coalesce(p.verbatim_genre,'')||' '||p.verbatim_title),
      '(комич\.?\s*оп|ком\.\s*оп|opéra.comique|opera.comique|opéra-com)') group by all;
```
Result: one Russian "комич. оп." in the whole Repertoire -- «Корневильскіе колокола, комич. оп.», Маріинскій, 1903-04
(1 night). French "opéra-comique": La chanson de Fortunio, Михайловскій 1904-05 (3). (Two «Опавшіе листья, ком.» rows at
the Малый were false matches.) The same work's only other appearance is printed «Корневильскіе колокола, оперетка» --
Маріинскій 21 Feb 1906, charity bill (p. 116). Operetta printings overall: Александринскій, Михайловскій, Маріинскій,
Малый (опер./оперетта/оперет.).

## 2026-10-06 — Graduates audit (issue #136): scope, non-person rows, school labels, person counts

```sql
SELECT e.entity_type, count(*), count(distinct sp.season), max(sp.season) FROM raw.person_entry e JOIN raw.source_pages sp ON sp.page_id=e.page_id GROUP BY 1;
SELECT sp.season, count(*), count(distinct e.page_id), sum((e.first_name IS NULL)::int), sum((e.tenure_note_text IS NOT NULL)::int), string_agg(distinct e.institution,' | ')
FROM raw.person_entry e JOIN raw.source_pages sp ON sp.page_id=e.page_id WHERE e.entity_type='Graduates' GROUP BY 1 ORDER BY 1;
-- suspect rows: lowercase/noun surname, numeric or >160-char note, no list number (Python filter over raw.person_entry JOIN entities.person_link)
SELECT count(*), count(distinct l.person_id) FROM entities.person_link l JOIN raw.person_entry e USING(entry_id) WHERE e.entity_type='Graduates';
```

Result: Graduates = 519 entries (20 seasons incl. 1910-11); 50 suspect rows of which 25 non-person (+3 stage-name rows the filter flags wrongly, 11 + 13 real 1910-11 rows without list numbers). Persons: before 505 on 519 entries (backup), after the audit 492 on 494 entries (-13 phantom persons). School labels: 36 rows of three Moscow continuation pages were stored under St Petersburg, 13 had none; 168 `institution` repairs in all. Raw entries 24,039 -> 24,014; live persons 3,199 -> 3,186; tombstones 3,197 unchanged; 0 orphan links; 0 shift blocks; quality flags 572 (none on Graduates).

## 2026-10-06 — Drama-course graduates still stored in Graduates (removal check)

```sql
SELECT sp.season, e.page_id, right(e.entry_id,4), e.family_name, e.institution, e.heading_path, e.tenure_note_text, cast(l.person_id as varchar)
FROM raw.person_entry e JOIN raw.source_pages sp ON sp.page_id=e.page_id JOIN entities.person_link l USING(entry_id)
WHERE e.entity_type='Graduates' AND (lower(coalesce(e.heading_path,'')||' '||coalesce(e.institution,'')||' '||coalesce(e.tenure_note_text,'')) LIKE '%драмат%' OR e.page_id IN ('graduates_1890-91_p005','graduates_1890-91_p006'));
-- then, for the 28 persons: links elsewhere; rows in entities.person_wikidata_link / production_credit_link / creator_person / person_merge_log
```

Result: 28 rows, all on graduates_1890-91 p005 (20) and p006 (8); 27 persons only on these rows (no Wikidata / credit / merge-log references), 1 (Носовъ Сергѣй Владиміровичъ, 794bb7) also on 4 Moscow-school staff lines. After the removal: entries 24,014 -> 23,986; live persons 3,186 -> 3,159; tombstones 3,197 unchanged; 0 orphan links; 0 shift blocks.

## 2026-10-07 — how are roles handled in the artist spiski?

RG asked this while designing the Season Reviews mention layer, to avoid
inventing a parallel scheme.

```sql
SELECT table_schema, table_name, column_name FROM information_schema.columns
 WHERE column_name ILIKE '%role%';
SELECT credit_type, count(*) FROM raw.person_entry_credit GROUP BY 1;
SELECT credit_type, label, role_name FROM raw.person_entry_credit
 WHERE role_name IS NOT NULL AND role_name <> '' LIMIT 12;
SELECT role_category, count(*) FROM research.production_credit GROUP BY 1;
```

Result: **the spiski already capture the performer -> work -> role triple.**
`raw.person_entry_credit` has 35,603 rows in two kinds: `category_totals`
(24,862) and `named_work` (10,741). Of these, **10,718 carry a `role_name`**,
with `label` holding the work:

| label (work) | role_name |
|---|---|
| Эсмеральда | Эсмеральда |
| Донъ-Кихотъ | Жуанна |
| Кипрская статуя | Галатея |
| Эсмеральда | подруга Флеръ-де-Лисъ |

Creator roles are modelled separately in `research.production_credit`
(1,495 rows: music 648, author 607, source 113, libretto 90, staging 31,
instrumentation 6), from the ballet production lists.

**But the performer triple is NOT exposed in the research layer.** It lives
only in `raw`/`analysis`. `research.person_appearance` (23,985 rows) carries
rank, title, service_class, instrument, subject_taught — no role, no work.
The only role columns in `research` are `production_credit.role_text` and
`role_category`, i.e. creators.

Consequence for the reviews: do not invent a `review_assertion` shape. The
relation already has a model (`person_entry_credit`), and the missing
research-layer table for it is a need the two tracks share.

---

## 2026-10-07 — opera-ballet crossover: do the reviews' mixed-bill tallies hold?

RG: *"Confirming that these types of opera-ballet mixes are vitally important
to my research!"* The ballet reviews state, per season, how many performances
were `смѣшанные спектакли` shared with opera. That number is independently
derivable from the Repertoire tables, so it is a real cross-check rather than
a restatement.

```sql
-- events whose programme holds both a ballet work and an opera work
WITH pw AS (
  SELECT e.season, e.city, e.event_id,
    (w.parent_genre = 'ballet'
       OR regexp_matches(lower(coalesce(w.canonical_genre,'')), '^(бал|ballet)')) AS is_bal,
    (coalesce(w.parent_genre,'') <> 'ballet'
       AND regexp_matches(lower(coalesce(p.verbatim_genre, w.canonical_genre, '')),
                          '^(оп\.|опера|опер|op\.|opera|opéra|оп$)')) AS is_op
  FROM research.event e
  JOIN research.performance p ON p.event_id = e.event_id
  JOIN research.work w ON w.work_id = p.work_id),
ev AS (SELECT season, city, event_id, bool_or(is_bal) b, bool_or(is_op) o
       FROM pw GROUP BY 1,2,3)
SELECT season, city, count(*) FROM ev WHERE b AND o GROUP BY 1,2 ORDER BY 1,2;
```

Result: **26 season/city rows, 1891-92 to 1910-11.** Nine seasons have a review
that states a ballet+opera count, and **eight match exactly**: 1891-92 SP 4,
1892-93 SP 11, 1893-94 Moscow 2, 1894-95 Moscow 2, 1894-95 SP 4, 1895-96 Moscow
13, 1896-97 Moscow 4, 1897-98 Moscow 3. Different source PDFs, different
extraction method, different schema.

The 1892-93 SP eleven, dated (all Маріинскій, `Іоланта + Щелкунчикъ`):
6, 8, 11, 13, 14, 16, 17, 26 Dec 1892; 1, 12, 15 Jan 1893.

**The ninth, 1893-94 SP, is short by one and that is the finding.** The review
reports `балетъ и опера—2` plus a four-way bill including opera; the db finds 2.
The missing bill is the Greek earthquake benefit, Михайловскій, 29 Apr 1894:
`Жены [этюдъ] + Le petit Hôtel [com.] + Концертное отдѣленіе + 1-е и 2-е д.
бал. Коппелія`. The opera troupe is inside `Концертное отдѣленіе`, which names
no works, so no genre test can see it.

```sql
-- how often does the Repertoire decline to itemize a programme entry?
SELECT lower(verbatim_title), count(*), count(DISTINCT e.season)
FROM research.performance p JOIN research.event e ON e.event_id = p.event_id
WHERE regexp_matches(lower(verbatim_title),
      '(концертн|дивертиссемент|дивертисмент|divertissement|концерт)')
GROUP BY 1 ORDER BY 2 DESC;
```

Result: **128 events.** `Дивертиссементъ` 82 (19 of the 21 seasons), `Балетный
дивертиссементъ` 9, `Концертное отдѣленіе` 9, `Концертъ въ пользу инвалидовъ` 7,
`Симфоническій концертъ` 5, plus singletons. The reviews itemize many of these.
Verified on two 1901-02 SP cases — the Repertoire gives
`1901-11-21 Маріинскій · 673,163 kop. · Пахита + Дивертиссементъ`, and the
review names Bekefi's 25-year benefit, Замбелли's first Пахита, and item
1) `Танцы изъ оперы „Жизнь за Царя“, муз. Глинки`. Join: season + city + date
+ theatre.

Write-up: `docs/eval/ballet_in_opera_and_divertissement.md`.
Re-runnable: `pipeline/find_opera_ballet_crossover.py`.

---

## 2026-10-07 — mention matching over the ballet reviews

Built `pipeline/match_review_mentions.py` and ran it over all 698 Ballet-review
pages. Dictionaries came from the live database, so the counts are queries:

```sql
SELECT person_id, canonical_family_name, display_name, ordinal_suffix,
       first_attested_season, last_attested_season
FROM research.person WHERE canonical_family_name IS NOT NULL;      -- 3,243 rows
SELECT work_id, canonical_title, canonical_genre, parent_genre
FROM research.work WHERE canonical_title IS NOT NULL;              -- 3,190 rows
SELECT DISTINCT role_name FROM raw.person_entry_credit
WHERE role_name IS NOT NULL AND role_name <> '';                   -- 2,621 rows
SELECT theater_id, canonical_name FROM research.theater;            -- 6 rows
```

Expanded by form generation into 14,734 person forms, 17,781 work forms and
12,416 role forms.

Result: **27,085 mentions, 15,117 (55.8%) resolved to one entity** — person
21,503, work 3,695, role 1,119, theater 632, dance_number 136.

Validation query, run against the output rather than assumed:

```sql
-- for every resolved person mention, does the entity's gender agree with the
-- honorific that introduced it?
```
**6,945 resolutions checkable on both sides, 0 mismatches** after correcting the
gender rule (an earlier version read a final `ъ` as masculine and produced 128,
nearly all of them the rule's fault — `Ваземъ`, `Гейтенъ`, `Борхардтъ` are
indeclinable and female here).

Two by-products, each needing a scan check and neither applied:

- **34 gender contradictions** — `Г-жа Галактіонова` where the database holds
  only `Галактіоновъ`. Six checked by hand; all six were genuine roster gaps.
- **40 candidate title misreads**, incl. `Камаріо`->`Камарго` (20x) and
  `Балдерка`->`Баядерка` (7x).

This also closed an item logged earlier the same day: `Гаарлемскій тюльпанъ`
(1903-04 SP) is **not** missing from `research.work` — it is there as
`Гарлемскій тюльпанъ`, one «а», similarity 0.973.

---

## 2026-10-07 — the credit join, and validating its dates against the Repertoire

```sql
-- the disambiguating signal: which same-surname person was credited with this
-- role, in this season, in the spiski?
SELECT pl.person_id, c.label, c.role_name, sp.season
FROM raw.person_entry_credit c
JOIN raw.person_entry pe ON pe.entry_id = c.entry_id
JOIN entities.person_link pl ON pl.entry_id = pe.entry_id
JOIN raw.source_pages sp ON sp.page_id = pe.page_id
WHERE c.role_name IS NOT NULL AND c.role_name <> '';
```
Indexed to **5,826 (person, role) pairs and 4,190 (person, work) pairs**.
Resolved **178** review performers that gender/season/ordinal ranking could not.

Result: **1,939 assertions**, 334 distinct performers, 1,449 distinct roles;
1,482 with a performer entity, 362 with a work entity, 420 with a date.

The validation that matters — the dates are extracted from prose, so they have
to be checked against the tabular layer, not trusted:

```sql
WITH d AS (SELECT DISTINCT date_undate dt, city
           FROM research.review_assertion WHERE date_undate IS NOT NULL)
SELECT count(*) AS review_dates,
       sum(CASE WHEN EXISTS (SELECT 1 FROM research.event e
                             WHERE e.date_undate = d.dt AND e.city = d.city)
                THEN 1 ELSE 0 END) AS land_on_a_real_event
FROM d;
```
**141 of 142 (99.3%).** The works agree on the night too: the 1890-11-21 Moscow
«Эсмеральда» cast sits on a Repertoire programme of `Эсмеральда / Воевода`, and
the 1891-01-20 «Кипрская статуя» cast on one including `Бенефисъ г-жи Бессонэ`,
the benefit the review is describing. The one miss, `1896-08-01` SP, is an
August roster-appointment date rather than a performance.

Incidental but important:

```sql
SELECT date_undate, city, count(*) FROM research.event
WHERE date_undate LIKE '%-02-29' GROUP BY 1,2;
```
**6 events on 1900-02-29** (3 SP, 3 Moscow) — plus 1892, 1896, 1904 and 1908.
1900 is a leap year in the **Julian** calendar, which imperial Russia used until
1918, and not in the Gregorian. `datetime.date()` rejects it. This is why
`research.event.date_undate` is VARCHAR, and why
`research.review_assertion.date_undate` is too.

## 2026-10-07 -- Administrators structure stage: what do institution/heading_path look like after the rebuild?

```sql
select count(*), count(distinct institution), count(distinct heading_path), count(distinct split_part(heading_path,' / ',1))
from raw.person_entry where page_id like 'administration_%' and page_id not like '%1910-11%';
select split_part(heading_path,' / ',1) o, count(*) from raw.person_entry where page_id like 'administration_%' and page_id not like '%1910-11%' group by 1 order by 2 desc;
select count(*) from raw.person_entry where heading_path like '% /';
```

Result: 1,834 rows; 1 distinct institution; 186 distinct heading_path; 3 offices (St Petersburg 943, Moscow 758, Directorate 133). Dangling " /" paths: 67 before the parser fix, 0 after.

## 2026-10-07 -- Administrators rebuild integrity vs the pre-structure backup

```sql
select count(*) from raw.person_entry e left join entities.person_link l on l.entry_id=e.entry_id where l.entry_id is null;
select count(*) from entities.person where superseded_by_person_id is not null;
select count(*) from entities.person where superseded_by_person_id is null;
select sum(receipts_total_kopecks) from research.event;   -- compared with the backup file
```

Result: 0 unlinked entries; 3,217 tombstones and 3,135 live persons (both identical to the backup); receipts sum identical; 0 orphan links.

## 2026-10-08 -- Pipeline coverage by season: which scanned material is not yet processed?

```sql
select season, entity_type, count(*) from raw.source_pages group by all order by 1,2;
select season, string_agg(distinct city, ','), count(distinct page_id) from raw.production_entry group by 1 order by 1;
select season, string_agg(distinct city||':'||genre, ', '), count(*) from raw.review_page group by 1 order by 1;
```

Compared with the files in `pdf/` (Reviews_Season, Spiski_BalletProductions, Spiski_Graduates, Spiski_ProductionStats) and `docs/season_stats/pages.csv`.

Result: Repertoire and all six Roster list types are loaded for every season 1890-91..1910-11 (Graduates 0 pages for 1907-08: no graduates PDF exists for that season). Ballet production lists loaded for 1890-91..1904-05 and 1908-09..1910-11 (none for 1905-06..1907-08, matching the PDFs). Production stats transcribed 1891-92..1904-05, 1906-07..1910-11 (matching the PDFs; none for 1890-91, 1905-06). Season reviews loaded for every season except 1898-99 and 1909-10 (no PDFs). Season-review PDFs present but not loaded: 1908-09 OperaSP, OperaMoscow, MusicSP_Autumn1909; 1912-13 BalletSP, OperaSP. Nothing scanned yet for 1911-12, 1913-14 or 1914-15, and the 1912-13 Repertoire and spiski are not scanned.
