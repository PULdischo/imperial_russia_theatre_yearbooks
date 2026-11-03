# Research-layer review with RG — 2026-11-03

A walk through what `research.*` in `outputs/full_run/imperial_theaters.duckdb` holds for each entity type, so RG can
judge it piece by piece. Every count below comes from a query logged in `docs/query_log.md` (2026-11-03,
"Research-layer review"). Nothing here changes data or code; RG's questions and rulings are recorded per section.

## Inventory (22 tables, 2 views at the start; 23 tables after ruling P1)

| entity type | tables (rows) |
|---|---|
| People | `person` 2,619 · `person_appearance` 23,980 · `person_tenure` 3,034 · `service_period` 23,629 · `person_assignment` 16 · `person_tenure_note` 27 · `person_performance_tally` 36,050 (new, ruling P1) |
| Works | `work` 2,952 |
| Theaters | `theater` 6 |
| Events and performances | `event` 32,813 · `performance` 30,835 · views `events_with_dancers` 2,222, `events_with_dancers_performance` 3,085 |
| Ballet productions lists | `production` 628 · `production_work` 628 · `production_credit` 1,587 |
| Season Reviews | `review_assertion` 2,657 · `review_credit` 2,410 · `review_dance` 914 · `review_dance_performer` 2,982 · `review_dance_composer` 67 · `review_solo` 96 |
| Season stats | `season_stat_line` 303 · `season_stat_check` 38 · `season_stat_footnote` 125 |

## 1. People

### What one record holds

- **`person`** — one row per resolved person. Name parts (`canonical_family_name`, `_first_name`, `_patronymic`,
  `ordinal_suffix`), `display_name`, `first_/last_attested_season`, Wikidata (`wikidata_qid`, `_label`, `_description`,
  `wikidata_source`), and `person_source`: `roster` 2,521 (the staff lists), `production_list` 86 (creators named only
  in the ballet productions lists, #133), `review` 12 (dancers named only in the reviews). The 98 non-roster people have
  no appearance rows. 174 people have a QID (6.6%): 88 by `link_wikidata`, 86 by RG's review.
- **`person_appearance`** — one row per printed list entry (person × season × list). `entity_type` (the list:
  BalletArtists 8,760 rows / 956 people; Musicians 7,896; TheaterSchoolStaff 2,855; ProductionTeam 2,101; Administrators
  1,902; Graduates 466), `institution`, `heading_path`, `rank`, `title`, `service_class`, `instrument`,
  `subject_taught`, `tenure_note_text` (verbatim), and the printed start (`printed_start_date/_text`,
  `printed_service_periods`).
- **`person_tenure`** — one row per run (person × list × city): the chosen start date and how it was chosen (`basis`),
  every printed date, slips left out, RG's rulings.
- **`service_period`** — one row per printed service period, with start/end at the precision printed and `end_type`
  (`left service` 1,095, `died` 217, `other` 211).
- **`person_assignment`** — 16 secondments/attachments («командирована къ Московскимъ театрамъ»).
- **`person_tenure_note`** — 27 printed leavings contradicted by later lists, with RG's reading.

### Things noticed (for RG)

1. `city` is blank for every Administrators, Graduates, ProductionTeam and TheaterSchoolStaff appearance (7,324 rows);
   only BalletArtists and Musicians carry SP/Moscow.
2. «Заслуженная артистка Императорскихъ театровъ» lands in `rank` only from 1908-09 on; earlier volumes leave it inside
   `tenure_note_text` (e.g. Кшесинская 2-я 1904-05, 1906-07).
3. Кшесинская 2-я has no 1905-06 entry (raw has none either; not scan-checked), and has a Moscow 1906-07 entry as well
   as the Petersburg one.
4. Ballet headings are only «Артистки» / «Артисты» plus staff posts; the lists print no soloist/coryphée grade.

### Held earlier but not carried into research

- **Role-by-role tallies**: `analysis.person_entry_credit`, 36,037 rows for 7,955 BalletArtists entries (e.g.
  Кшесинская 2-я 1904-05: Одетта 1, Падмана 1, царь-дѣвица 1, Лиза 2, Пахита 1, Фіаметта 2, Аспиччія 1; балетахъ 7/9;
  Всего 9). No research table reads them; `credit_summary_text` (the verbatim tally line) is not in research either.
- **`list_number`** — the entry's printed number on the list (8,596 of 8,760 BalletArtists entries).

### RG's questions and rulings

**P1 — role-by-role tallies: carry them into research (RG 2026-11-03, "Yes, add them").** Applied the same day:
new `research.person_performance_tally` (36,050 items: 17,146 category, 7,781 total, 11,123 role) and
`research.person_appearance.credit_summary_text` (the verbatim line; 7,991 of 8,760 BalletArtists entries). Labels and
role names stay as printed, with no link to `research.work` yet. Built on a copy first: every other table was
identical before and after; promoted to `outputs/full_run`, 0 differences from the tested copy, 0 person_link shifts.
Code: `build_research_model.build_person_performance_tallies`; export added to `build_datasette.py` (the sqlite
itself is Andy's to rebuild). Docs: `docs/schema.md`.

Left open by P1 (extraction slips found while building, not fixed):
- 11 tally items have no count: a truncated line (1898-99 MSK p006 e025 «въ 2 дра»); a category row with no matching
  text (1893-94 MSK p007 e001); «ком. Батюшкина дочка—въ бал. Своенравная жена (горничная—3)» stored as a role-less
  `ком. Батюшкина дочка` (4 entries, 1893-94 SP); and three printed «—» with no number («Франческа — )», «добрая фея—,
  нотаріусъ—3», «Одетта—, Одиллія—4»; the last two may mean one count shared by two parts).
- 42 entries print a tally line but have no parsed items (36 BalletArtists, 6 ProductionTeam).
- Possible next step: link tally titles to `research.work` (not done; needs RG's word).

**P1 follow-up — the gaps, checked on the scans by Claude 2026-11-03 (RG: "let's address these").** Correction to the
list above: 36 of the "42 entries with no items" are not tallies. Their line is a leaving, death or transfer note
(«Оставила службу 5 февраля 1892 г.», «† 19 декабря 1896 г.»), so no items is right. What remains:

A. Mechanical fixes, scan-confirmed (proposed):
1. Ивановъ 5-й, 1898-99 MSK p.119 no. 34: the line runs onto p.120, whose top was never stored: «...въ 2 дра-|махъ—3.
   Всего — 115 разъ. Въ томъ числѣ: Корсаръ (4-й корсаръ—4).» (53 + 59 + 3 = 115). Restore the text; драмахъ 3,
   Всего 115, role Корсаръ / 4-й корсаръ 4.
2. Смоликовъ, 1893-94 MSK p.98 no. 61: prints «Въ 2 операхъ—4; въ 1 драмѣ—8. Всего—12 разъ.», no ballets. The stored
   «балетахъ» item is invented; remove it.
3. «ком. Батюшкина дочка—въ бал. Своенравная жена» (1893-94 SP: Засѣдателева p.58 no. 39 горничная—3; Маржецкій p.64
   no. 37 поваръ—3; Солянниковъ 1-й no. 57 графъ—1; Татариновъ no. 62 кастелянъ—3): store the part and count, with the
   label used by the other 4 entries that parsed («ком. Батюшкина дочка—въ бал. Своенравная жена»).
4. Letter misreads in the same lines: «Своеправная» -> «Своенравная» (Маржецкій, Солянниковъ 1-й, Татариновъ; the print
   reads н in all four); Макарова 1901-02 SP p.74 no. 58: «дивертисементѣ» -> «дивертиссементѣ» (print «дивер-|
   тиссементѣ»), «Сваннильды» -> «Сванильды».

B. Print leaves a count blank (needs RG):
- «— ,» before a second part of the same work: Каралли 1906-07 MSK p.52 no. 44 «Дочь фараона (оживленная мумія— ,
  Бинтъ-Анта—3)» and «Лебединое озеро (Одетта— , Одиллія—4)»; Домашева no. 33 «Арлекинада (добрая фея— ,
  нотаріусъ—3)». For Каралли the parts add up to her printed ballet total (13 = 3 + 5 + 4 + 1) only if each pair shares one
  count: «both parts, the same N performances».
- Макарова «Граціелла (Франческа —  )»: a single part with no number printed. Nothing to restore.

C. 1892-93 ProductionTeam p.100, decorators (6 entries): under each name the print lists the new sets painted for
1892-93 (footnote: «перечень новыхъ декорацій, написанныхъ имъ къ сезону 1892—1893 гг.»), e.g. Бочаровъ 1-й:
«Щелкунчикъ, бал.—1 (2-я к. 1-го д.—Лѣсъ зимой)». Only the closing «Всего—N декорацій» was stored; the lists themselves
were dropped. They are set-design credits, not performance tallies (needs RG).

**Ruling B (RG 2026-11-03, "Yes. Odette-Odile is a good example of this, two roles that are typically taken by the same
dancer in the same performance").** «Part— , Part—N» = both parts in the same N performances. Research layer only (raw keeps the
blank): the blank part takes the next part's count and `count_shared_with` names that part, so role sums skip it. Lone
blanks (Макарова «Франческа —  ») stay empty. Rows: Каралли «оживленная мумія» (3, with Бинтъ-Анта), «Одетта» (4, with
Одиллія); Домашева «добрая фея» (3, with нотаріусъ).

**Group A approved (RG 2026-11-03, "yes to these").** Correction while preparing it: the four «Батюшкина дочка» parts were
not lost; each line had been split into two items (a count-less «ком. Батюшкина дочка» and «Своеправная жена (part—N)»).
The fix joins them under the one label. 28 entries print this line and store it in five different shapes (open question
below). Fix script: `docs/eval/tally_fixes_2026-11-03/raw_fix_tallies.py`.

**Chased (RG "chase these").** 1893-94 SP p.63: all five remaining «Своеправная» print «Своенравная» (Гавликовскій 18,
Горскій 21, Левинсонъ 31, Легатъ 1-й 32, Литавкинъ 34); the same lines print «Тангейзеръ» (stored «Тангейзерь»,
Горскій, Легатъ 1-й) and «скороходъ» (stored «сворождъ», Горскій). Added to the fix script. «Жизель (Верта—N)» in 8
entries plus «Ватюшкина» (2) and «Яйзель» (1): see below.

**C — how the 1892-93 set lists could be captured (RG asked for options).** What the print gives, per decorator, both
cities (SP p.100: 6 decorators; MSK p.103: Вальцъ 21 sets, Гельцеръ 8, and three assistants with 1-2 each): one item per
work, «Title, genre—N (act/scene—set name; ...)», e.g. «Щелкунчикъ, бал.—1 (2-я к. 1-го д.—Лѣсъ зимой)», sometimes
«вмѣстѣ съ К. Ѳ. Вальцемъ» (painted jointly). Checked: 1891-92 and 1893-94 SP print no lists, so this looks like one
season's feature.

**Applied 2026-11-03 (group A + B + the chased misreads).** `docs/eval/tally_fixes_2026-11-03/raw_fix_tallies.py`, 22 entries on 16
pages. Chased results: all 8 «Жизель (Верта—N)» print «Берта»; both «Ватюшкина» print «Батюшкина»; «Яйзель» is «Жизель»; the same lines
gave «Уранія», «Жертвы Амуру», «Флеръ-де-фаринъ» (scan check by a Claude helper, two crops re-read by Claude). Tally items 36,050 -> 36,046;
one count-less item left (Макарова «Франческа», a printed blank).

**Incident.** The first promotion copied a tested DB over production while the person audit session was rebuilding it (Больмъ edits);
production would not open. Repaired the same day (RG "Yes, put it in") with one combined rebuild from the raw files on the clean pre-clash
DB: only these tally fixes and the 3 Больмъ entries differ from it. Lesson: never copy a DB over production; rebuild from raw, and message
the other session first.

**Ruling (RG 2026-11-03, "Yes, full label").** All 28 entries printing «ком. Батюшкина дочка—въ бал. Своенравная жена (part—N)»
(SP 1893-94, 1894-95) get that one item label; 20 change (13 ballet-only, 5 comedy-only, Куличевская 1894-95 with the ballet in her part,
Маржецкій 1894-95 spaced dash). Part names scan-checked by Claude: «коранщикъ» -> «корзинщикъ» (Кшесинскій 2-й 1894-95), «поварь» ->
«поваръ» (Сергѣевъ 1894-95). Ширяевъ 1893-94 p.65 no.71, smudged page, read by RG: «въ бал.» is a full stop (stored «бал:», fixed) and
«драмѣ—3.» a full stop (as stored). Script: `docs/eval/tally_fixes_2026-11-03/raw_fix_batyushkina_labels.py`.
Applied 2026-11-03 (rebuilt from raw on production, checked equal to the tested copy). 1895-96 prints «Своенравная жена (part—N)» alone,
so its 12 items keep that label.

Still open (for RG, one at a time): C, how to capture the 1892-93 set lists.

Earlier note (superseded): 4 more entries print «Своеправная» (сторожъ, геній, танцмейстеръ ×2, графъ; not scan-checked);
«Ватюшкина», «Верта» look like Б->В misreads.

**Яковлева 1-я 1904-05 (RG 2026-11-03, "Yes, correct all 7").** SP p.21 no.130, read on the scan by Claude: Копсъ-Горбунокъ -> Конекъ-Горбунокъ,
Нахита -> Пахита, Корсарь -> Корсаръ, перпитянка -> негритянка, Фея куколь -> Фея куколъ, Граніелла -> Граціелла, Голубая георгиня ->
Голубая георгина; counts all as printed. Script `docs/eval/tally_fixes_2026-11-03/raw_fix_yakovleva_1904-05.py`; applied by a rebuild from
raw, production equal to the tested copy.
