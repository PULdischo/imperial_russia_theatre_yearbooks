# Administrators 1910-11 audit (issue #144), 2026-10-09

The 1910-11 Administration list (4 pages, 69 stored rows) was onboarded in #135 and was the one season left out of the #137 audit. Same method, scaled down: one blind reader transcribed all four pages (`reader_reports/bundle_01.txt`, 68 ROW lines; images extracted from the PDF at full resolution into `outputs/roster_images_full/images/`), `parse_reports.py` + `compare.py` (copies of the #137 scripts pointed at this folder) compared them with the stored rows, and the few differences were settled on the scan.

## Result: 68 of 69 rows were right
- **Wrong (fixed):** `administration_1910-11_p002__e018` "Дежурные врачи" was a **note stored as a person**: the page prints the heading «Дежурные врачи:» followed by the note «Находятся въ вѣдѣніи придворной медицинской части съ 6 декабря 1902 г.» (the same bug as the 7 rows removed in #137). Row removed from the raw page, its person_link deleted, the later entry renumbered (#131 rule), `apply_fixes.py`. Entries 23,981 -> 23,980; the phantom person is gone (live persons 3,135 -> 3,134); tombstones unchanged.
- **Looked different, but right:** «Принцъ, Борисъ Владиміровичъ» (surname «Принцъ», the #137 rule: false TITLE_IN_NAME alarm); «Фонъ-Бооль, Николай Константиновичъ» (the reader's report formats the particle separately, so the fuzzy pairing missed it; text identical to the stored row); **Коровинъ's rank «над. сов.»**: the reader read «надв. сов.», but the zoom (full resolution) shows «над. сов.» printed, so the stored value is correct (a print variant, listed in `genuine_print_typos.md`).
- Dates, numbers, name tokens, ranks and notes agreed on every other row; no Latin homoglyphs.

## Structure (RG's option 1, as in #137)
`structure_fix.py` (copy of the #137 script restricted to this season; one unmatched row paired by elimination): `institution` = «СПИСОКЪ личнаго состава театральнаго управленія.», `heading_path` = office / department / position: 5 Directorate rows, 35 St Petersburg, 28 Moscow (reader headings carried across the page breaks; the grade tokens such as "VII кл" are moved to `service_class` by the parser). All 21 Administrators seasons now have a single `institution` value.

## Verification after the rebuild
23,980 entries; live persons 3,134; tombstones 3,217; 0 orphans; 0 shift blocks; receipts identical; research.event 32,826. Backups: `outputs/full_run_pre_promote_backup_2026-10-09_adm1011` (before) and `.../after_removal` (before the structure write).
