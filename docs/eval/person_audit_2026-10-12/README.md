# Audit of entities.person, end to end -- 2026-10-12

RG asked for a thorough audit of every person entity: unconnected records, mis-merges, anything suspicious.
Read-only. Nothing was merged, split or corrected by this audit. 3,059 live people were examined
(six known non-person rows excluded). `audit.py` computes the signals, `cluster.py` groups the main one;
both rerun in seconds. Every CSV here is a WORKLIST, not a verdict.

## 1. Unconnected records (one person held as two or more)

**1a. Same name, same printed start date, never joined -- 298 clusters.** `U_clusters_same_start_date.csv`.
- **Grade A, 263 clusters (280 records to absorb):** one consistent name, at most one patronymic, no season in
  which two members stand in the same list.
  - 153 involve a Graduates-only record. In 126 the company record starts the next season, in 25 the same
    season (the volume lists the class in both), in 2 later.
  - 110 are company records only. In 74 the short record fills gaps in, or adjoins, the long one; 33 are not
    adjacent and 3 are two posts in different lists -- those 36 deserve a look before any merge.
- **Grade B, 35 clusters (44 records):** a surname that differs (Левинсонъ/Левенсонъ, Кастровскій/Костровской,
  Трекова/Грекова), two patronymics inside one cluster (Хасперъ, Нестеровская, Чумакова, Чичелева, Аѳанасьева),
  or a same-list overlap (Грибенъ, Елинекъ, Стеличекъ, Никольскій Иванъ/Іоаннъ, Шефферъ/Шпейеръ).
- **Why the pipeline never proposed them:** Tier 1 needs the whole name to match; Tier 2 compares records that
  differ in ONE field (surname, or patronymic) and both its keys contain the first name and the ordinal. So it
  never compares (i) a first-name variant (Софія/Софья, Агриппина/Агрипина, Лидія/Лилія), (ii) two fields varying
  at once, or (iii) a graduate (no patronymic, no ordinal) against a company record that also has no ordinal.
  The 2026-10-12 ordinal-shift pass covered only pairs whose ordinals differ.
- Not scan-checked. A random sample of 8 company-only clusters read as obvious single people from the data.

**1b. Other shapes** (`U_unconnected_pairs.csv`, column `kind`):
- 58 pairs where a short record fills a gap in a longer one in the same list, without a shared date.
- 27 surname-only records beside a named person in the same list. 15 of them are one page: the Moscow ballet list
  of 1901-02 prints several people as a bare surname (scan-confirmed for Воронцовъ and Валининъ).
- 12 identical names with no shared date. Some are deliberate (Васильевъ, Тарасовъ: earlier splits; Жукова:
  uncertain-list entry 10).

**1c. What stays unexplained:** 170 single-entry company records have no partner by any signal (58 are 1890-91,
the first volume, where people leaving that year appear once; 18 each in 1907-08 and 1908-09). 213 graduates
have no company record; the Graduates lists also carry drama and opera pupils, so most of these are expected.
`X_single_entry_company_records.csv`, `G_graduate_only_records.csv`.

## 2. Mis-merges (two people held as one)

- **One confirmed regression: Никитинъ, Алексѣй Никитичъ (636532).** The Petersburg second violinist (съ 1
  сентября 1881, left 1 октября 1900) and the Moscow trombonist (съ 23 сентября 1898) were split on 2026-10-05
  and are one record again; they are both listed in 1898-99, 1899-00 and 1900-01, in two cities, on two
  instruments. Cause, read in `build_entities.merge_duplicate_persons`: its start-date gate is satisfied by ANY
  two members of a same-name group, its overlap gate is season+city, it does not consult the split log, and it
  writes no log row. A new 1910-11 Moscow row shared a date with the trombonist and pulled the violinist in.
- **13 logged splits checked:** 10 hold; Логиновъ and Николаевъ were rejoined on RG's own decision; Никитинъ is
  the regression above.
- `M10_two_start_dates_same_season.csv` (50): apart from Никитинъ and Логиновъ these read as one person with two
  posts, each with its own date (artist + teacher, artist + assistant regisseur).
- `M5_both_cities_one_season.csv` (19): guest appearances and transfers (Кшесинская, Павлова, Фокинъ, Горскій...),
  plus Никитинъ and Логиновъ.
- `M2`/`M3`/`M4` (conflicting patronymics, first names, surnames: 78/24/29): almost all are field-shift artefacts
  in the raw rows (first name in the patronymic field, ordinal in the first-name field, «И.» from «И. д.»), not
  two people. Real variation is already on the uncertain list (Зандинъ, Лебедевъ, Голяховскій, Тихомировъ,
  Сергѣевъ, Шредеръ). Not yet looked at: Кякштъ, Лидія (Георгіевна x5, Юрьевна x1), Петипа 2-я, Надежда
  (Маріусовна x14, Васильевна x1), Мендесъ, Джульетта (Іосифовна x2).
- `M11_two_instrument_families.csv` (12): the start date is constant in each, so these look like instrument-field
  errors in single seasons (Котроба: Вальдгорнъ every year, «Первая скрипка» once), not two players.
- `M9_listed_after_leaving_or_death.csv` (194) and `M8_first_start_date_varies.csv` (380) are broad and were NOT
  triaged row by row; the 2026-10-05 sweep covered the same ground with scan checks.
- `M1_two_rows_same_list_season.csv` (250 rows, 98 people): 195 are the Musicians «Музыканты» heading, where a
  player is listed in two orchestras, and 43 are honorary members of the school conference listed twice.

## 3. Suspicious name fields

- Display names are mostly sound (`S_display_name_signals.csv`): 37 surname-only people, 8 with brackets or
  quotes (5 are genuine double surnames; «Гельцеръ, (Китри)» and «Эрлеръ, "Александръ"» are not), 1 «Бурина 1 я».
- Raw rows (`S_suspicious_name_fields.csv`, 906 flags): 245 two-word first-name fields, 106 ordinals in the
  first-name or patronymic field, 105 patronymic fields that are not patronymics, 78 surnames with trailing
  punctuation, 43 brackets or quotes, 23 Latin letters inside Cyrillic names. The analysis layer's clean columns
  already repair most of these for display; the rows themselves are unrepaired.

## Not done
No scan reading beyond what is cited; no merges, splits or raw corrections; M8 and M9 not triaged.

## Follow-up, same day (RG: yes to all three recommendations)

**Applied.** `build_entities.py` gained `build_shared_start_candidates` and `_keep_apart_pairs`;
`merge_duplicate_persons` is now pairwise, logs its merges (`confirmed_duplicate`) and refuses a group that a hand
split keeps apart; `_repoint_all_superseded` also repoints production-credit links.
- Никитинъ, Алексѣй Никитичъ is two men again (`docs/eval/person_resplit_nikitin_2026-10-12.py`) and survives a rebuild.
- 296 pairs auto-confirmed, 295 records absorbed: entities.person 3060 -> 2765, research.person 2863.
  Listed in `auto_confirmed_shared_start_dryrun.csv`. In 57 the first names differ by a letter (Софія/Софья,
  Лидія/Лилія, Надежда/Належда); in none do two printed patronymics differ. Not scan-checked.
- Queue for RG: 176 pending pairs in 159 groups (`outputs/full_run/person_candidate_review.csv`): 90 with a shared
  start date that did not fit cleanly, 86 graduates matched by name and graduation year only.
- Backup `outputs/full_run/imperial_theaters.pre_sharedstart_pass_2026-10-12.duckdb`. Receipts, appearances and
  Wikidata links (176) unchanged; 0 orphan links, 0 shift blocks; review mentions resolved 21,307 -> 21,403.

**Corrections to the report above.**
- Section 1c said the unlinked graduates include "drama and opera pupils". Wrong (RG): every Graduates entry is a
  ballet pupil of the Petersburg or Moscow school. And 213 was inflated: this audit read RAW name fields, and
  three classes (1891-92, 1893-94, 1897-98) have «Surname, Name.» glued into the surname field. The pipeline pass
  reads the cleaned names. Now: 465 people have a Graduates entry, 293 are joined to a company record, 100 have a
  pending candidate, 72 have none (24 are the class of 1910-11, with no later volume; 19 are 1900-01; 9 are 1908-09).
- The Petersburg classes of 1897 and 1898 are printed «съ 1-го мая» in the Graduates list and «съ 1 іюня» in the
  company list (Фокинъ, Егорова, Обуховъ, Гордова), so they share no date and are matched by year, pending.
- The two splits RG reverted: Николаевъ, Иванъ Николаевичъ now holds only three ProductionTeam rows (1908-11).
  The 1909-10 Moscow ballet row that raised the question no longer exists as a Николаевъ entry (that page was
  re-read in a later audit; what replaced it was not traced), so uncertain-list entry 3 is stale. Логиновъ is
  unchanged: one record, listed in both cities in 1905-06, start «1894» in Petersburg and «1904» in Moscow.

**Scan checks (item 3).**
| Row | Print | Finding |
|---|---|---|
| Кякштъ, Лидія, SP 1902-03 no. 45 | «Кякштъ, Лидія Юрьевна (съ 1 іюня 1902 г.)» (reduced size) | print variant: Юрьевна for Георгіевна (Юрій = Георгій) |
| Петипа 2-я, Надежда, SP 1904-05 no. 80 | «Петипа 2-я, Надежда Васильевна (съ 1 сентября 1892 г.)» (full zoom) | genuine print error for Маріусовна; raw had dropped «2-я» (fixed) |
| Мендесъ, Джульетта, Moscow 1907-08 no. 53 | «Мендесъ, Джульетта Іосифовна (съ 1 октября 1896 г.)» (reduced size) | one woman; earlier rows carry her ordinal in the patronymic field |
| «Гельцеръ, (Китри)», SP 1909-10 | a section «Танцовала на Петербургской сценѣ Императорскаго театра: Гельцеръ. Донъ-Кихотъ (Китри—1)» (reduced size) | a guest listing; the role was in the patronymic field (fixed). Three such surname-only guest records stay separate people: Гельцеръ 1909-10, Гельцеръ and Балашова 1910-11 |
| Эрлеръ, "Александръ", SP 1904-05 no. 93 | «Эрлеръ, Александръ Александровичъ» with specks beside the name (reduced size) | quotation marks were specks (fixed) |
| Бурина 1 я, Moscow 1909-10 no. 9 | «Бурина 1 я, Клавдія Александровна» (full zoom) | printed without the hyphen; left verbatim |
| Исаева, Татьяна Михайловна, SP 1908-09 | nos. 31 AND 38 both print «Исаева, Татьяна Михайловна (съ 1 іюня 1894 г.)» (full zoom) | the volume lists her twice; no. 38 stands in the К's |
Raw fixes: `docs/eval/raw_fix_audit_rows_2026-10-12.py` (3 rows, backup `outputs/full_run_pre_promote_backup_2026-10-12_audit_rawfix/`).

## The Moscow class of 1901 (RG asked why 19 graduates of 1900-01 have no candidate)

They are one class: all 19 pupils of the Moscow school's ballet department who left in spring 1901
(`graduates_1900-01_p001`; the Petersburg class of 8 on p000 is linked, bar Гольде, Юліусъ).
The Moscow list prints no start date for the class, and the volume that should show them joining, the Moscow
ballet list of 1901-02, prints 23 people as a BARE SURNAME with their credits and nothing else (scan-confirmed
for «12. Валининъ,» and «14. Воронцовъ,»). 16 of the 23 are this class; the other seven are people who also carry
«съ 1 сентября 1901 г.» later or returned that month (Воронцовъ, Пановъ, Щегловъ, Гримальди, Иванова, Рѣпина,
Струкова). From 1902-03 the class is listed with full names and «съ 1 сентября 1901 г.».

So each of them is held as up to THREE records: the graduate (1900-01), the bare surname (1901-02), the named
dancer (1902-03 on). The year-match rule missed them because the named record starts two seasons after the
graduation list, not one. By name, every one of the 19 has exactly one named Moscow record starting 1 Sept 1901
(Орловъ and Грекова from 1903-04); 17 have a bare 1901-02 row found by surname (Валининъ for Волининъ, Николаева
3-я, Царманъ 2-й among them); Бурина's and Грекова's bare rows were not found by this query. Жвирблисъ is the one
already queued. Nothing merged; from the extraction, not the scans, apart from the two rows named above.

**Correction, same day (RG: "so these are the only ones that go missing?").** Neither goes missing. All 19 of the
class are in the Moscow 1901-02 list.
- Грекова, Елена: «26. Грекова 2-я» is there; the earlier query missed it because the ordinal sits in the
  first-name field. She is then «Трекова, Елена Александровна» in the 1902-03 data (not read on the scan) and
  «Грекова 2-я, Елена Александровна» from 1903-04.
- Бурина, Марія: the print has «10. Бурина 2-я.», a bare surname (full zoom). The extraction had filled that row
  with the name, start date and credits of row 11, Бюхнеръ, Евгенія Фердинандовна, inventing a «Бурина, Евгенія
  Фердинандовна». Corrected from the scan (`docs/eval/raw_fix_burina_1901-02_2026-10-12.py`; row 9 also regains
  «1-я»). 2 entries changed, 0 links moved.
So the bare-surname rows of that list number 24 with this one, 17 of them the class of 1901; and each of the 19
graduates has a graduate record, a 1901-02 row and a named record from 1902-03 or 1903-04.

### The 1901-02 Moscow ballet list read on the scans (2026-10-12) -- proposal for RG, nothing merged

All nine pages read at reduced size (the bare rows are large type and legible); p000 rows 9-11 and p005 rows
12-14 at full zoom. 25 rows are printed as a bare surname, plus «39. Жвирблисъ, Марія (съ 1 сентября 1901 г.)»
with a first name and no patronymic. Machine-readable: `moscow_1901-02_bare_rows.json`.

| 1901-02 row | Graduate of 1901 | Named record (start 1 Sept 1901 unless noted) |
|---|---|---|
| 10. Бурина 2-я | Бурина, Марія | Бурина 2-я, Марія Александровна, 1902-03.. |
| 22. Грабовская | Грабовская, Ольга | Грабовская, Ольга Васильевна, 1902-03.. |
| 26. Грекова 2-я | Грекова, Елена | «Трекова 2-я, Елена Александровна» 1902-03 + Грекова 2-я, Елена Александровна 1903-04.. |
| 31. Домашева | Домашева, Евдокія | Домашева, Евдокія Петровна, 1902-03.. |
| 32. Дмитріева | Дмитріева, Надежда | Дмитріева, Надежда Николаевна, 1902-03.. |
| 35. Дьяченко-Краткая | Дьяченко-Краткая, Елизавета | Дьяченко-Краткая, Елизавета Яковлевна, 1902-03.. |
| 39. Жвирблисъ, Марія | (same record) | Жвирблицъ, Марія Ивановна, 1902-03 (queued pair) |
| 55. Ленская | Ленская, Лидія | Ленская, Лидія Ивановна, 1902-03 only |
| 71. Николаева 3-я | Николаева, Зинаида | Николаева, Зинаида Николаевна, 1902-03.. |
| 75. Павлова | Павлова, Евгенія | Павлова, Евгенія Ивановна, 1902-03.. |
| 98. Соколова | Соколова, Татьяна | Соколова, Татьяна Александровна, 1902-03.. |
| 114. Шаломытова | Шаломытова, Антонина | Шаломытова, Антонина Михайловна, 1902-03.. |
| 122. Ѳеоктистова | Ѳеоктистова, Лидія | Ѳеоктистова, Лидія Васильевна, 1902-03.. |
| 12. Валининъ | Волининъ, Александръ | Волининъ, Александръ Емельяновичъ, 1902-03.. |
| 31. Карцевъ | Карцевъ, Александръ | Карцевъ, Александръ Викторовичъ, 1902-03.. |
| 33. Коноваловъ | Коноваловъ, Владиміръ | Коноваловъ, Владиміръ Дмитріевичъ, 1902-03.. |
| 49. Орловъ | Орловъ, Алексѣй | Орловъ, Алексѣй Владиміровичъ, 1902-03.. |
| 70. Фроловъ | Фроловъ, Сергѣй | Фроловъ, Сергѣй Александровичъ, 1902-03.. |
| 75. Царманъ 2-й | Царманъ, Владиміръ | Царманъ 2-й, Владиміръ Александровичъ, 1902-03.. |

Bare rows that are not the class:
- 27. Гримальди -> Гримальди, Генріетта (1902-03..1905-06, съ 1 сентября 1901; 3 roles in common). Not a graduate of
  the school: she arrives that month.
- 51. Пановъ -> Пановъ, Александръ Викторовичъ (1895-96..1898-99, then 1902-03.. with a second start 1 сентября 1901).
- 83. Щегловъ -> Щегловъ, Василій Семеновичъ (1896-97..1898-99, then 1902-03.. with a second start 16 ноября 1901).
- 14. Воронцовъ and 100. Струкова are already on their people.
- 42. Иванова and 89. Рѣпина: no single candidate. Left alone.

Found on the way: (a) the 1902-03 list really prints «26. Трекова 2-я» (full zoom, a Т beside the Г of row 25) --
a print error; raw dropped its «2-я»; (b) rows 76-99 of 1901-02 p003 are stored with no start date although the
print gives one for each -- 20 rows to re-read; (c) the bare rows' named parts carry over in six cases only, so
the matches rest on surname, class and the «съ 1 сентября 1901 г.» date, not on roles.

### Applied 2026-10-12 (RG)
- **The class of 1901: 19 people merged** (38 records absorbed), `docs/eval/person_merge_moscow_class_1901_2026-10-12.py`,
  backup `outputs/full_run/imperial_theaters.pre_class1901_merge_2026-10-12.duckdb`. Live persons 2765 -> 2727.
- **Гримальди, Пановъ, Щегловъ merged** on RG's condition that only one later candidate exists; checked across the
  whole corpus (`person_merge_moscow_1901-02_bare_rows_2026-10-12.py`, backup `...pre_bare_rows_merge_2026-10-12.duckdb`).
  Live 2724. Not merged, seen in passing: «Гримальди, Генріэтта», Petersburg 1899-00 (съ 1 сентября 1899), probably the same woman.
- **21 start dates restored** on `balletartists_1901-02_MSK_p003` (nos. 76-99), each read at full zoom; «Поржицкая»
  (was Поржипкая); «Трекова 2-я» regains its ordinal (`raw_fix_msk_1901-02_p003_dates_2026-10-12.py`, backup
  `outputs/full_run_pre_promote_backup_2026-10-12_msk0102_dates/`). 22 entries and 22 service rows differ, 0 links.
  The four rows still undated on that page are the bare surnames, which print none.
- After all of it: 174 pairs pending (88 shared-start, 86 graduate year-match); 154 graduate-only records;
  receipts and Wikidata links unchanged; 0 orphans, 0 shift blocks; review mentions resolved 21,393.

### The graduate queue (86 pairs), decided 2026-10-12
`Q_graduate_year_match.csv` holds the evidence table. RG: merge the 80 clean pairs
(`person_merge_graduates_year_match_2026-10-12.py`); Семеновъ, Николай -> Николай Прокопьевичъ, the Petersburg
musician rejected; Мосолова, Зинаида + «Зинаида Алексѣевна» -> Мосолова 2-я, Зинаида Александровна
(`person_merge_semenov_mosolova_2026-10-12.py`); Бекъ (transfer printed) and Сергѣева (likely transfer, uncertain
list #31) (`person_merge_bek_sergeeva_2026-10-12.py`). Live persons 2724 -> 2639. Graduate-only records 154 -> 70.
- Scans read: the Petersburg class pages of 1897 and 1898 really print «съ 1-го мая»; the company lists have
  «съ 1 іюня» (extraction). 1891-92 p001 carries Бекъ's transfer; 1908-09 p000 has no transfer for anyone.
- Queue now: 88 name_variant_shared_start pairs. The graduate queue is empty.
- Seen, not done: «Ѳокинъ, Михаилъ Федоровичъ» 1908-09..1910-11 is a separate record from Фокинъ, Михаилъ
  Михайловичъ; «Семеновъ, Николай Прохоровичъ» (Moscow 1908-09) fills the one gap in Николай Прокопьевичъ's run;
  9 of the 16 Petersburg graduates of 1909 have no company record by any rule; a production database write by
  another session happened mid-afternoon (lock at 14:00), backups retaken after it.

### The notes on the Theatre School graduation pages (RG, 2026-10-12: "make sure we've carefully examined them")

Sources: the complete blind transcription of all 51 pages of 1890-91..1909-10 (`docs/eval/graduates_audit_2026-10-06/reader_reports/`),
the hand-verified table `docs/ballet_graduates_tenure.csv` (399 rows), the 1910-11 pages (read in issue #135), and
the scans re-read today for 1891-92 p000/p001, 1896-97 p001, 1897-98 p001, 1899-00 p001, 1900-01 p001, 1908-09 p000.

Every posting sentence in print, and the individual exceptions inside them:
| Class | Print | In the data |
|---|---|---|
| SP 1891 | all 15 from 1 June 1891, «а г. Легатъ—съ 1-го октября того же года» | Легатъ 2-й, Иванъ: 1 Oct 1891. Correct |
| SP 1892 | all from 1 June 1892 to the Petersburg troupe «кромѣ ученика Бека, который зачисленъ въ Московскую балетную труппу» | Бекъ carries 1 June 1892. The sentence gives NO date for him; the Moscow list has 1 Sept 1892. OPEN, see below |
| SP 1893 | all from 1 June 1893 «кромѣ ученика Тихомирова, который зачисленъ съ 1-го сентября 1893 года въ Московскую балетную труппу» | Тихомировъ, Василій: 1 Sept 1893, Moscow. Correct |
| SP 1896, 1897, 1898 | «съ 1-го мая» | 1 May; the company lists print 1 June (already documented in docs/ballet_graduates.md) |
| Moscow 1899 | «опредѣлены на службу съ 1 сентября 1899 года» | was unparsed for all 12 (a period "from spring 1899 to 1 Sept"). FIXED today |
| Moscow 1909 | «1. Жуковъ, Леонидъ (при услов. сдачи одного экзам.)» | note kept on his row. Correct |
| SP 1911 | all from 1 June 1911 «за исключеніемъ больной г-жи Безкоровайной» | she carried the class date. FIXED today: no start date, note kept |
| Moscow 1900, 1901, 1902, 1905, 1906, 1910, 1911 | no posting sentence printed | no date. Correct -- with one doubt: the 1899-00 Moscow page (`graduates_1899-00_p001`) is a CROPPED scan that ends under the men's list, so a sentence below it cannot be ruled out. The 1900-01 page is whole (folio 142) and has none |

- The table and the database agreed on every date except those 12 rows. The table does not cover the 67 rows of 1908-09..1910-11.
- Fix: `docs/eval/raw_fix_graduates_notes_2026-10-12.py` (backup `outputs/full_run_pre_promote_backup_2026-10-12_graduates_notes/`): 12 service rows changed.
- **Бекъ, open for RG:** `docs/ballet_graduates.md` records "the Report says 1 June 1892, BalletArtists says 1 September 1892" as a discrepancy. Read
  strictly, the Report dates the Petersburg posting and excepts him from it without giving his date, so there may be no discrepancy at all.
- Also done: «Семеновъ, Николай Прохоровичъ» merged into Николай Прокопьевичъ (`person_merge_semenov_prokhorovich_2026-10-12.py`).
  NOT merged: «Ѳокинъ, Михаилъ Федоровичъ» is an assistant hairdresser at the Bolshoi (ProductionTeam 1908-11, съ 16 августа 1901), not the dancer.
- Queue: 89 shared-start pairs and 1 ordinal_shift pair, new since the 1899 class dates began to parse.
