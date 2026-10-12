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
