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

**C — ruled and applied (RG 2026-11-03, "Yes, transcribe", then "Yes, store them").** Both pages read on the scans by Claude
(crops `docs/eval/scan_audit/1892-93_productionteam_*`). 61 sets, 11 decorators (SP 28: Андреевъ 8, Бочаровъ 1-й 9, Ивановъ 4,
Левотъ 2, Шишковъ 1, Яновъ 4; Moscow 33: Вальцъ 21, Лебедевъ 1, Савицкій 2, Смирновъ 1, Гельцеръ 8); every printed total and
per-work count matches. Raw: the 6 SP lines now carry the full printed list (they held only «Всего—N»); Moscow misreads fixed
(«Сиѣгурочка» x3 -> «Снѣгурочка», «Лакма» -> «Лакмэ», «поднямъ» -> «поляны»), `B12_1892-93_set_lists_2026-11-03.csv`. Research: new
`research.set_design` from `docs/season_sets/1892-93_new_sets.csv` (checked against the printed lines and totals at build time;
`source` column leaves room for the reviews' 230 «scenery» credits, RG asked about these for later). Includes the first
«Щелкунчикъ» (Dec. 1892): Бочаровъ 1-й «Лѣсъ зимой», Ивановъ the President's hall and «Конфектное царство».

Next in the walkthrough: Works.

## 2. Works

(Resumed in a new session, 2026-11-03 afternoon. Queries logged in `docs/query_log.md`, "Research-layer review: Works".)

### What one record holds

- **`work`** — 2,952 rows: `canonical_title`, `canonical_genre` (the printed genre word, as printed, in the language of
  the print: «ком.» 424, «com.» 568, «Lustsp.» 67 ...), `appearance_count`, `excerpt_of_work_id` + `excerpt_note`
  (342 excerpts), `genre_source` (`printed` 2,560, none 365, `review` 20, `research_rule` 7), `genre_note`,
  `title_note`, `work_source` (`repertoire` 2,932, `review` 20: works named only in the Season Reviews) and
  `source_note`.
- The art form is **not on the work**. It sits on each `performance` (`discipline`, `company`, `genre_family`,
  `includes_dance`). 2,915 works have performances.
- Other tables that point at a work: `production` (ballet productions lists, 627 of 628 linked), `review_assertion`
  (1,879 of 2,657), `review_credit` (2,358 of 2,410), `review_dance` (632 of 914), `review_solo` (37 of 96).
  The dancers' tally titles (`person_performance_tally`, ruling P1) are not linked to works yet.

### Things noticed (for RG)

1. **Three review cast lines linked to the wrong work.** 1904-05 SP review p.115 (4 Nov 1904), the cast of
   «Путешествующая танцовщица»: Альма is linked to that ballet, but Діасъ (Кшесинскій), «Кармена, подруга Альмы»
   (Радина) and слуга Альмы (Стуколкинъ) are linked to a ballet «Карменъ», because the role name «Кармена» was read as
   the title. Mechanical fix: point all four at «Путешествующая танцовщица».
2. **17 works with no performances.** 15 are parent works whose excerpts alone were played (Дмитрій Донской 5
   excerpts, Борисъ Годуновъ трагедія 4, ...): by design. The other two are leftovers of genre-slip rulings:
   «Карменъ, бал.» (its two 1906-07 / 1907-08 performances now count as the opera) and «Анжело, оп.» (its one
   1910-11 performance now counts as the drama). They hold nothing except the three slips in item 1.
3. **`appearance_count` is stale for 7 ballets**, short by 1-2 against the performances now linked (Коппелія 105 vs
   107, Лебединое озеро 125 vs 127, Эвника 8 vs 9, Шопеніана, Волшебная флейта, Дочь фараона, Золотая рыбка).
   Counting from `performance` is right; the column needs recomputing in the build.
4. **The same play in two languages is two works**: Гамлетъ (Russian drama 66) vs Hamlet (German/French 4), Тартюфъ
   25 vs Tartuffe 4, Фаустъ драм. поэма 14 vs Faust Schausp. 2, Фаустъ оп. 289 vs Faust op. 5. This follows the
   2026-10-05 rule (identity = title + art form + script). Noted in case RG wants them connected without merging.
5. **«Дивертиссементъ» is five works**: «Дивертиссементъ» with «бал.» (44 performances), with no genre (37, not
   counted as ballet; 2 more counted as ballet), «Дивертиссментъ» (as stored; 3 ballet + 2 not), and «Дивертиссементъ
   (Etudes)». These are programme labels, not titled works.
6. 338 performances have no `discipline`: «Гимнъ» 195, concerts 52, divertissements 41, tableaux 32, readings,
   lectures, cinema. By design (art forms = five companies + concert; anthem is ceremonial). Four performances have no
   `genre_family` either: «Концертъ-спектакль» 1901-02, «Обозрѣніе» 1902-03, «Балетоманъ» 1904-05, «Слава»! 1894-95.
7. 12 works span more than one `discipline`, mostly the opera repertory sung by both the Russian and the Italian
   company (Фаустъ, Травіата, Аида, Балъ-маскарадъ). Odd ones: «Гейша» (opera, Russian drama, German operetta) and
   «Званый вечеръ съ итальянцами» (opera, Russian drama).

### RG's questions and rulings

**W1 — the three «Кармена» cast lines (RG 2026-11-03, "Yes, relink them").** One row in
`docs/eval/review_work_mention_links.csv` links the «Кармена» mention in `review_1904-05_SP_ballet_p010__b004` to
«Путешествующая танцовщица»; assertions 1482, 2848, 2849 follow it. Tested on a copy first: 1 mention and 3 assertions
change; the other differences are candidate lists in a different order. «Карменъ, бал.» now holds nothing.

Found while checking W1 (for RG): this cast is not the 1904-05 revival. The review quotes the **1865 première** («Балетъ
этотъ былъ поставленъ въ первый разъ на сценѣ Большого театра въ бенефисъ М. С. Петипа 1865 г., 4-го ноября, при
слѣдующемъ распредѣленіи въ немъ ролей: ...»), which is the same case as the quoted 1875 «Голубая Георгина» cast. The
assertions are dated 1904-11-04 and their dancers (Радина, Стуколкинъ, Берра ...) are linked as if in 1904-05.

**W1b — the quoted 1865 cast (RG 2026-11-03, "Yes, same treatment").** Scan read by Claude (crops
`docs/eval/scan_audit/1904-05_review_SP_ballet_p115_1865_traveling_dancer_cast.png`, `..._p116_...png`). p.115 block
`review_1904-05_SP_ballet_p010__b004` is on `docs/eval/review_historical_passages.csv` dated 1865-11-04. The cast
runs on into p.116 (`..._p011__b001`) up to «При настоящемъ возобновленіи балета роли въ немъ распредѣлены такъ», where
the 1905 cast begins in the same block, so that block is not listed; its 1865 names are unlinked one by one instead.
27 rows in `docs/eval/review_mention_links.csv` (empty person_id). Code: `build_review_assertions.py` no longer
resolves a performer in a listed block through the spiski credits, which are the review season's: that is how «г-жа
М. С. Петипа» (Альма, 1865) had been linked to Петипа 1-я. Result: all 15 1865 cast lines are now unlinked (8 had a person
link: Альма, Кармена, слуга Альмы; Ole, La charrada, La Iota, El Cabarde, почтальонъ), the four on p.115 dated 1865-11-04
(the p.116 ones carry no date); the 1905 cast keeps its links. «Берра» in «Берра, слуга
Альмы» is the role's name and had been linked to a dancer; now unlinked with the rest.
Not fixed (small, noted): p.116 prints «Гердтъ, Легатъ 1-й и Волковъ» in La charrada, stored «Гердъ».

**W2, W3 (RG 2026-11-03, "fix these").** `build_research_model.py` now stages the performance rows, sets every
repertoire work's `appearance_count` to its performances as built, and drops a repertoire work left with none unless it
is an excerpt parent or in a ballet productions list. Dropped: «Анжело», оп. and «Карменъ», бал. (2,952 -> 2,950 works).
Recounted: Коппелія 105 -> 107, Лебединое озеро 125 -> 127. Correction to item 3 above: the other five (Эвника,
Шопеніана, Волшебная флейта, Дочь фараона, Золотая рыбка) were right. Each has one performance supplied from a review
or productions list, which `appearance_count` leaves out by design (docs/schema.md), so their counts stay. Applied to
production after a test on a copy, then the review chain; 0 person_link shifts, 0 work_ids left pointing at a dropped work.

**W4 — same piece in two scripts (RG 2026-11-03, "Link, don't merge. At least for now. I assume Hamlet could be performed
both in English and in Russian, and I'm not really sure if they're the same parent work or not.").** Evidence: the
split follows the printed script, not the company (Sandrock's German «Гамлетъ» 1901-02 sits with the Russian drama's;
the German and French «Hamlet» are apart; Угетти's Italian «Фаустъ» 1901-02 with the Russian opera, the Moscow Italian
and German «Faust» apart). Ruling: keep them as separate works and connect them; whether they share one parent work stays
open. Nothing built yet: a link needs a work-to-work relation (the research layer's only one today is
`excerpt_of_work_id`), the same need as RG's 2026-10-12 «Млада» / «Волшебное зеркало» case (connect without
equating). Candidate pairs among the 1,192 Latin-script works need a hand-checked list (translation, not spelling).

**W5 — «Дивертиссементъ» (RG 2026-11-03, "Keep as is. We don't know enough about them to categorize them as the 'same
work'").** The six work rows stay apart (бал. 44; no genre 37; no genre / ballet 2; «Дивертиссментъ» бал. 3 and no genre
2; «(Etudes)» 1).

**W6/W7 (RG 2026-11-03, "Check the scans").** Item 7 needs no ruling: «Гейша» and «Званый вечеръ съ итальянцами»
take their company by RG's rules (an operetta goes with the company that performs it; a visiting troupe by its
personnel). Item 6: the four items with no kind were already walked through with RG on 2026-10-13 and left without
one (`docs/eval/known_issues.md`, "The items with no kind"; «Балетоманъ» flagged to be looked for). Read again on the
scans by Claude today, crops in `docs/eval/scan_audit/`: each is printed as stored, with no genre, inside a banner
(«Спектакль въ память А. С. Грибоѣдова.» «Слава»! / Горе отъ ума, ком., Малый 4 Jan 1895, 1367 р. 37 к.;
«Въ пользу благотворительнаго Общества при Городской Калинкинской больницѣ. Концертъ-спектакль.», Маріинскій 16 Feb
1902; «Спектакль въ пользу Общества Покровительства животнымъ. Обозрѣніе.», Маріинскій 11 Jan 1903; «Балетоманъ»,
Маріинскій 23 Apr 1905, item 3 of 6 lines under «Спектакль въ пользу Общества попеченія о Гребловской школѣ имени Н. В.
Гоголя.»). The season totals carry no concert or revue line; no review mentions them. Nothing new: they stay blank.

### Held earlier but not carried into research (Works) — checked 2026-11-03 at RG's request

Columns: every work-level field the transcription captures (title, genre) reaches `research.performance`
(`verbatim_title`, `verbatim_genre`); every `entities.work` column is in `research.work`. Rows:
- **Ballet productions lists' printed dates**: `raw.production_entry_performance`, 2,374 dates (110 with a note such as
  «3-е дѣйствіе», «1-е и 2-е д.», «прологъ», «танцы изъ 2-го д. балета»; 30 marked outside the printed total; 5 whose
  printed year does not match the season). Research keeps only `production.n_dates` (sum 2,344) and
  `production_work.n_matched_dates`; the dates, their notes and which `research.event` each one is are not queryable.
- **One Repertoire line**, Малый 24 Nov 1905 («, ком.», 1218 р. 36 к.): the print omits the title (scan-confirmed
  2026-10-09, `docs/eval/genuine_print_typos.md`). Raw keeps it; research has the event (performed, receipts) with no
  performance. Already known.
- **Retired work ids**: `entities.work_id_crosswalk`, 836 old -> new ids from merges. Not published; matters only to
  someone holding an id from an earlier export.
- Pipeline-internal, by design: `entities.work_genre_candidate` (62, review queue), `entities.work_link` (the
  crosswalk the research FKs replace). `entities.review_work` (20) is carried as `work_source = 'review'`.
- `entities.work` rows not in research (4): «Карменъ» бал. and «Анжело» оп. (W2), «Шоиеніана» (title correction merged
  into «Шопеніана»), «Дивертиссементъ (Etudes)» (its research row is the research-rule split).

**W8 — ballet-list dates carried into research (RG 2026-11-03, "Yes, add them").** New `research.production_date`,
2,374 rows (one per printed date): printed day/month/year, note, `outside_total`, `year_printed_matches_season`, the
misprint correction where there is one, and the Repertoire `event_id` / `performance_id` it names. 2,357 match one
performance; 5 match two performances of one event (event set: Коппелія and Лебединое озеро 1895-96 with «2-я и 3-я
карт. бал.» on the same bill, Корсаръ 16 Nov 1908 «2-е дѣйствіе балета» beside «Оживленный садъ»); 1 matches two events
(«Золотая рыбка» 14 Nov 1904, «2 раза: утромъ и вечеромъ»); 11 match nothing. The list's «утро» / «вечеръ» note now
separates a day's two events (4 dates); a second pass on research's titles recovered «Шопеніана» 8 Apr 1910 (printed
«Шоиеніана»), «Волшебная флейта» 30 Nov 1903 and «Дочь Фараона» 13 Feb 1905 (performances supplied from the list).
Code: `build_research_model._list_date_matches` (ballet_list_matches is now a view of it, output checked identical:
2,370 pairs), `build_production_dates`; `build_datasette.py` schema; `docs/schema.md`.

Left for RG (not chased): the 11 list dates with no Repertoire performance naming the ballet. None is in the
reconciliation ledger under its date:
| season | city | list title | date | ballet on the Repertoire that day |
|---|---|---|---|---|
| 1895-96 | Moscow | Катарина (Дочь разбойника) | 1896-01-17 | Большой: Эсмеральда |
| 1895-96 | Moscow | Пробужденіе Флоры | 1896-05-02 | Большой: Паяцы + Даита |
| 1897-98 | SP | Волшебная флейта | 1897-10-25 | none |
| 1898-99 | SP | Очарованный лѣсъ | 1898-09-21 | none |
| 1900-01 | SP | Маркитантка | 1901-02-11 | Маріинскій: excerpts of Камарго, Фіамметта, Щелкунчикъ |
| 1901-02 | SP | Волшебная флейта | 1901-12-19 | Маріинскій: Сильвія |
| 1904-05 | SP | На перепутьи | 1904-12-17 | none |
| 1908-09 | Moscow | Спящая красавица | 1908-10-18 | none |
| 1910-11 | SP | Конекъ-горбунокъ или Царь-дѣвица | 1911-02-18 | none |
| 1910-11 | SP | Спящая красавица | 1911-02-19 | none |
| 1910-11 | SP | Шопеніана | 1911-03-09 | Маріинскій: Эвника + Карнавалъ |

**W8 follow-up — the 11 unmatched list dates (RG 2026-11-03, "Look at the 11").** Ten were already worked out in the
season reconciliations; one («Шопеніана» 9 Mar 1911) was new and was read on both scans by Claude today (crops
`docs/eval/scan_audit/1910-11_list_SP_p65_Chopiniana.png`, `1910-11_repertoire_1911-03-07_09_Mariinsky.png`).

A. A slip in the list, intended date known (could go in `LIST_DATE_PRINT_TYPOS` so `production_date` links them):
- «Пробужденіе Флоры», Moscow, «мая 2» -> 3 May 1896 (ledger 1895-96-09; the Repertoire and the Moscow review have 3 May).
- «На перепутьи», SP, «декабря 17» -> 27 Dec 1904 (RG 2026-10-29, ledger 1904-05-17; the list's own «Пробужденіе Флоры»
  entry has 27 Dec).
- «Спящая красавица», Moscow, «октября 18» -> 8 Oct 1908 (ledger 1908-09-03, scan read by Claude 2026-11-02; the Большой
  is dark on 18 Oct; count 7 = 7).
B. A slip in the list, no date to correct to: «Волшебная флейта» 25 Oct 1897 (Маріинскій dark; RG 2026-10-29 "It's likely
  a list error", ledger 1897-98-12); «Маркитантка» 11 Feb 1901 (corps-de-ballet benefit, no «Маркитантка»; list,
  Repertoire and review read).
C. The yearbook disagrees with itself (both transcriptions match their scans; open):
- «Катарина», Moscow, 17 Jan 1896 (the Repertoire has «Эсмеральда»).
- «Очарованный лѣсъ», SP, 21 Sep 1898 (the Repertoire has «Фераморсъ» only).
- «Волшебная флейта», SP, 19 Dec 1901 (the Repertoire has «Сильвія»; the list implies a double bill).
- «Конекъ-горбунокъ» 18 Feb and «Спящая красавица» 19 Feb 1911, SP (the Repertoire: «Китежъ»; «Кантата. Жизнь за
  царя»; ledger 1910-11-12). Moscow gave «Спящая красавица» at the 19 Feb matinée.
- «Шопеніана», SP, 9 Mar 1911: the list prints «1911 г.—марта 7, 9. Всего—4 раза», and its «Эвника» and «Карнавалъ»
  entries agree on 9 Mar; the Repertoire's 9 Mar bill is «Эвника, бал.» / «Карнавалъ, пантомима-бал.», 4653 р. 50 к.
  (7 Mar adds «Шопеніана, сюита»). The SP review says «Карнавалъ» was repeated «7-го и 9-го марта» and does not name
  «Шопеніана» for either.

**W8 follow-up A applied (RG 2026-11-03, "Yes, add the three").** The three list slips with a known date are in
`LIST_DATE_PRINT_TYPOS`: «Пробужденіе Флоры» -> 3 May 1896, «На перепутьи» -> 27 Dec 1904 (matinée), Moscow «Спящая
красавица» -> 8 Oct 1908. `production_date` keeps the printed day and says why in `date_correction_note`; matched 2,357 ->
2,360, unmatched 11 -> 8; `production_work.n_matched_dates` +1 for the three entries. Nothing else changed.

## 3. Theaters

(Queries logged in `docs/query_log.md`, "Research-layer review: Theaters".)

### What one record holds

- **`theater`** — 6 rows: `theater_id`, `canonical_name`, `city`, `active_from_season` (set only for «Новый», 1898-99).
  No end season, address, English name or Wikidata link. Same as `entities.theater`.
- Pointed at by `event.theater_id` (every one of 32,813 events has one) and the dancer views. `set_design` keeps the
  theater only as printed (`theater_printed`: Большой театръ 25, Малый театръ 8, blank 28), not as an id. No review
  table carries a theater.

| theater | city | events | performed | seasons | receipts (р.) |
|---|---|---|---|---|---|
| Маріинскій | SP | 5,953 | 4,040 | 1890-91 – 1910-11 | 10,974,212.58 |
| Александринскій | SP | 6,024 | 4,598 | 1890-91 – 1910-11 | 5,555,054.14 |
| Михайловскій | SP | 5,588 | 4,025 | 1890-91 – 1910-11 | 3,494,747.45 |
| Большой | Moscow | 5,844 | 3,808 | 1890-91 – 1910-11 | 7,597,011.23 |
| Малый | Moscow | 5,821 | 4,009 | 1890-91 – 1910-11 | 3,723,520.56 |
| Новый | Moscow | 3,583 | 1,685 | 1898-99 – 1910-11 | 886,339.85 |

Event counts include `no_performance` and `not_captured` rows (all theaters: performed 22,165, no_performance 7,771,
not_captured 2,877).

### Held earlier but not carried into research

- Raw prints 16 spellings of the six names («Большой театръ», «Большой», «Большой театр», «Большой театръ,» ...); every one
  maps to one of the six (`analysis.event_entry.theater_canonical`). Nothing unmapped.
- 30 events on `repertoire_1910-11_p056` are left out on purpose (`RESEARCH_EXCLUDED_PAGES`: Moscow's blank 10-19 May
  1911 page printed from the SP form; RG 2026-10-06).
- The Season Reviews' theater mentions (632 in `entities.review_mention`) reach no research table. Two venues outside the
  six occur there only: the Эрмитажный (3) and the Красносельскій (1).

### Things noticed (for RG)

1. **«Новый» after it stopped playing.** Its last performance is 29 Apr 1907. From 1907-08 to 1910-11 the Repertoire still
   prints a «Новый театръ» column of dashes (checked on the 1908-09 p. 3 scan), so research holds 1,037 `no_performance`
   events there (264, 255, 264, 254 a season). As printed; they swell Moscow's count of days without a performance.
2. **Review theater mentions are linked unevenly.** Moscow names link to a theater id (Новый 45, Большой 9, Малый 3), but 32
   of the 45 «Новый» links are the adjective («Новыя декораціи», «Новыхъ балетовъ»). Petersburg names («Маріинскомъ» 57,
   «Маріинскаго» 20, «Михайловскомъ» 11 ...; 105 in all) are not linked. The rest are institution tags (INST:imperial 208,
   INST:moscow 140, INST:petersburg 118, Эрмитажный, Красносельскій). Belongs with the reviews section; nothing uses it yet.
3. `active_from_season` exists only for «Новый»; there is no closing season for it.

### RG's questions and rulings

**T1 — «Новый» after 1906-07 (RG 2026-11-03, "keep as is").** The 1,037 dash-only rows of 1907-08 – 1910-11 stay
`no_performance` as printed; no closing season is added to `research.theater`.

**T2 — review theater mentions (RG 2026-11-03, "Leave for Reviews").** The 32 adjective links to «Новый» and the 105
unlinked Petersburg theater names wait for the Season Reviews section.

## 7. Season stats

(Taken before 4-6 at RG's request. Queries logged in `docs/query_log.md`, "Research-layer review: Season stats".)

### What one record holds

- **`season_stat_line`** — 303 rows, one per printed line with a number, from the season totals page («Всего въ
  теченіе сезона … было спектаклей»): `category_verbatim` / `category` (ditto resolved), `venue_verbatim`,
  `qualifier_verbatim` («(опера и балетъ)»), `count`, `receipts_verbatim` / `receipts_kopecks`, `footnote_refs`,
  `line_kind` (category 147, venue 99, subtotal 48, part 9). Categories: Русскихъ драматическихъ 99, Балетныхъ 50,
  Русскихъ оперныхъ 38, Смѣшанныхъ 29, Оперныхъ 24, Французскихъ 19, Нѣмецкихъ 18, Концертовъ 12, and one-offs for
  visiting troupes (Режанъ, Лессингъ-театръ, Тина ди Лоренцо, Московскій художественный театръ ...).
- **`season_stat_check`** — 38 rows (season × city): the page's totals beside the Repertoire's (performed events,
  distinct theater-days, receipts, charity-worded events) and the differences.
- **`season_stat_footnote`** — 125 footnotes, verbatim, 11 seasons (benefits, free student performances, charity
  exclusions).
- Seasons: 19 pages, 1891-92 to 1910-11. 1890-91 has no such page; 1905-06's has not been found (needs the volume).

### Held earlier but not carried into research

- **The reconciliation outcomes.** `docs/eval/reconciliation/outcome_ledger.csv`, 271 rows covering every season
  1890-91 – 1910-11, explains the differences between the stats, the Repertoire, the ballet lists and the reviews, one gap
  at a time, with the events involved and the evidence. Outcomes: yearbook_own 120, corrected 53, excluded_by_yearbook 48,
  classification 23, open 16, comparison_rule 11. Not in the database, so `season_stat_check` shows each difference
  (e.g. Moscow 1909-10 +107 events / +31,748 р., SP 1907-08 +70) without its explanation.
- `raw.season_stat_page` (19): the page heading verbatim, its footnote mark and the source file. Research keeps only the
  format and printed page (in `season_stat_check`).
- `raw.season_stat_dated_note` (10): the jubilees and farewell performances printed after each city's totals in 1909-10
  (correction 2026-11-03: 1909-10 only, not 1910-11) («24 января—прощальный спектакль балерины Трефиловой.», «24 февраля—35-ти лѣтіе службы М. Г. Савиной.» ...).

### Things noticed (for RG)

1. 1891-92 `repertoire_receipts_kopecks` is 0 for both cities: the Repertoire prints no receipts that season, so this
   should read "none", not 0 р.
2. `season_stat_footnote` has no city column (raw has none either); a footnote's city is only implied by its number.
3. A stats line does not link to the events it counts; that link exists only in the ledger's `event_ids`.

### RG's questions and rulings

**S1 — the reconciliation ledger in research (RG 2026-11-03, "Yes, load it").** New `research.season_stat_gap` (271
rows) and `season_stat_gap_event` (569 links to `research.event`), loaded from
`docs/eval/reconciliation/outcome_ledger.csv` by `build_research_model.build_season_stat_gaps`; export schema in
`build_datasette.py`; `docs/schema.md`. Links by outcome: excluded_by_yearbook 314, corrected 96, yearbook_own 74,
classification 46, comparison_rule 23, open 16. Seven gaps name their events in words or by page (1892-93-03, 1896-97-01,
-02, -05, -08, 1903-04-10, 1910-11-09) and have no links. Six ledger lines had unescaped quotes inside their note, which
split them into extra columns (1894-95-05, 1899-00-08, -12, 1903-04-14, 1904-05-15, 1909-10-06): quoting repaired, text
unchanged (1894-95-05 keeps its printed «30 (53","181 р. 53 к.)» as written).

**S2 — 1891-92 receipts (RG 2026-11-03, "agreed").** `season_stat_check.repertoire_receipts_kopecks`, the charity-worded
receipts and the receipts difference are NULL, not 0, when no event of the season and city prints receipts (1891-92,
both cities). No other row changed.

**S3 — page headings and dated notes (RG 2026-11-03, "Yes, add them").** New `research.season_stat_page` (19: source
file, printed page, heading and its footnote mark verbatim, format, note) and `research.season_stat_dated_note` (10, all
1909-10: SP 6, Moscow 4; city as SP/Moscow beside the printed form). Built from the raw tables in
`build_season_stats`; export schema in `build_datasette.py`; `docs/schema.md`. Every other table unchanged.

**S4 — footnote city (RG 2026-11-03, "Yes, add it").** `season_stat_footnote.city`: SP 63, Moscow 54, page 8 (the
heading's note on the italic receipts, 1893-94 – 1900-01). Taken from the lines that carry each mark; the build stops if a
footnote is carried by both cities or by nothing. Every other column and table unchanged; export schema in
`build_datasette.py`; `docs/schema.md`.

## 4. Events and performances

(Queries logged in `docs/query_log.md`, "Research-layer review: Events". The performance → work side is in section 2.)

### What one record holds

- **`event`** — 32,813 rows, one per theater × date × session: `event_status` (performed 22,165, no_performance 7,771,
  not_captured 2,877), `date_verbatim`, `date_undate` (as printed) and `date` (after the weekday check),
  `date_confidence` (verified 29,850, synthesized_gap 2,877, corrected_manual 76, no_weekday 10), `time_of_day`
  (unspecified 28,078, morning 2,378, evening 2,357), receipts (`receipts_verbatim`, `receipts_total_kopecks` on 19,329;
  `receipts_source`: parsed 19,041, half-kopeck dropped 209, corrected print typo 79; `receipts_correction_note` on 288),
  `printed_page_number` (29,936; the rest are the synthesized gaps), `annotation` (1,807), flags (`is_benefit` 729,
  `is_charity` 378, `is_free` 328, `is_student_performance` 143, `is_reduced_price` 26, `has_anthem` 195), and the bill's
  summary (`n_works`, `disciplines`, `companies`, `genre_families`).
- **`performance`** — 30,835 rows (section 2), plus `company` (St. Petersburg Russian drama 7,845, Moscow Russian drama
  7,629, St. Petersburg French drama 4,876, Moscow opera 3,198, St. Petersburg opera 3,116, St. Petersburg ballet 1,493,
  Moscow ballet 1,205, visiting German drama 812, Moscow Art Theatre 152, and 15 smaller visiting troupes; none for the 338
  anthems, concerts and the like), `includes_dance` (158, each with its basis), `is_ceremonial` (195).
- **Views** `events_with_dancers` 2,222 events, `events_with_dancers_performance` 3,085 rows.

### Held earlier but not carried into research

- **Date-correction notes.** `analysis.event_entry_date_check.note` explains each of the 86 corrected or doubtful dates
  («scan-verified: book prints day as "9" (should be "4"; between 3 Среда and 5 Пятница)», «the page misprints every
  weekday word one day ahead …»). Research has the corrected `date` and `date_confidence`, not the reason (receipts have
  `receipts_correction_note`; dates have nothing like it).
- `month_text`, `year_text` (the printed month and year headings) are not in research; `date_verbatim` is the day cell only.

### Things noticed (for RG)

1. **Julian dates.** `event.date` is text, not a date type, because six events fall on 29 Feb 1900, a Julian leap day that
   the Gregorian calendar (and DuckDB's DATE) does not have. There is no Gregorian date beside it, so a match with a
   foreign newspaper or any Gregorian-dated source needs the +12 / +13 day shift done by hand.
2. **117 performed events with no performance row**: concerts and similar evenings whose cell prints only a heading
   («Концертъ въ пользу инвалидовъ.», «Генеральная репетиція концерта …», «Баль-маскарадъ», «3-й концертъ А. Зилоти.»),
   no work line. They have `n_works` 0 and no performance row. **Correction (2026-11-03, later):** most are already
   labelled at event level: `event.genre_families` = concert on 93 (RG's 2026-10-13 rule, `CONCERT_EVENT_RE`, which
   also covers «музыкально-литературный вечеръ» headings); the two Siamese court troupe evenings and the two German
   charity bills of March 1898 (RG 2026-10-23, #141, `event_labels.csv`) carry a discipline and company. 20 have none.
3. Receipts are missing for 2,836 performed events: 1890-91 (965) and 1891-92 (939) print none; the rest are free and
   charity evenings.

### RG's questions and rulings

**E1 — date-correction notes (RG 2026-11-03, "Yes, add them").** New `research.event.date_correction_note`, from
`analysis.event_entry_date_check.note` (or the page-month override's reason): all 86 corrected_manual / no_weekday dates
have one; verified and synthesized dates have none. Every other column and table unchanged; export schema in
`build_datasette.py`; `docs/schema.md`.

**E2 — Gregorian date (RG 2026-11-03, "we can always add that later, so lets skip for now").** Not added; `date` stays
Julian, as printed.

**Step back (RG 2026-11-03): what belongs in research.** Test agreed: a table or column earns its place if it answers a
research question, carries the evidence needed to trust or cite an answer, or saves a hard or error-prone lookup. Not if it
restates another field, touches a handful of rows already findable by their text, records pipeline bookkeeping, or needs
ongoing judgment calls for little gain. Kept on review: `season_stat_page` (source file + printed page = the citation for
every stats figure), `season_stat_footnote.city`. Rolled back: `season_stat_dated_note` (11 of its 12 dated items are the
event's own Repertoire heading, e.g. «Прощальный спектакль балерины В. Трефиловой.» 24 Jan 1910; its two «1909 г.» year
slips and the 18 Dec second-artists' benefit are already in the 1909-10 reconciliation; raw keeps the notes).

**E3 — heading-only evenings (RG 2026-11-03).** No `event_kind` column. 97 of the 117 already carry an event-level label
(concert 93 under RG's 2026-10-13 rule; Siamese court troupe 2; German opera 2, #141); the other 20 keep their heading in
`annotation`, and the 17 dress rehearsals are found by «Генеральная репетиція». The 1899 and 1903 Pushkin evenings print
works inside their heading that were never made performance rows: noted, not chased.

## 5. Ballet productions lists (2026-11-04)

(Queries logged in `docs/query_log.md`, "Research-layer review: Ballet productions lists".)

### What one record holds

- **`production`** — 628 rows, one per printed list entry (a ballet as listed in one season and city; not RG's
  multi-season production, which stays her call): `list_title`, `list_number`, `is_premiere` (51), `description_text`
  (the printed description, verbatim), `printed_total` («Всего—N»), `n_dates`, `work_id` (the best single match, 627),
  `n_matched_works`, `printed_page_number`, `source_file`. Seasons 1890-91 – 1904-05 and 1907-08 – 1910-11, SP and Moscow:
  1905-06 and 1906-07 print no «Списокъ пьесъ» (both tables of contents checked, 2026-10-09).
- **`production_work`** — 628: every work an entry's dates matched, with the count. 626 entries match one work.
- **`production_credit`** — 1,587 printed creator credits, every one linked to a person (110 people: 86 known only from the
  lists, 24 also in the staff lists): music 688, author 641, source 123, libretto 98, staging 31, instrumentation 6;
  `name_printed`, `honorific_printed`, `qualifier_printed`, `is_pseudonym` (7), `identification_status` (confirmed 1,586,
  proposed 1).
- **`production_date`** — 2,374 printed dates (built 2026-11-03, W8).

### Held earlier but not carried into research

- The printed «Исполненъ: …» and «Всего—N» lines verbatim (`raw.production_entry.performed_text`, `total_text`) and the
  `section_heading` («Балетъ» on 518). Their content is carried as `production_date` rows and `printed_total`.
- 5 group credits («друг.», «др.», «разныхъ авторовъ» for the music) are left out on purpose: they name no person.
- The acts given on their own and printed after «Всего» (25 entries, e.g. «3-е дѣйствіе исполнено: 1899 г.—января 23»)
  ARE carried: the 30 `production_date` rows with `outside_total`, the act in `note`.
- The lists print no set or costume designers; design credits come from the reviews (`review_credit`) and
  `set_design` (1892-93).

### Things noticed (for RG)

1. **«Паяда и рыбакъ» is still its own work** (one performance, Маріинскій 20 Sep 1892), beside «Наяда и рыбакъ» (15).
   The П is a scan-confirmed print typo (`genuine_print_typos.md`), and the 1892-93 list entry matches both works. The two
   sister cases, «Ваядерка» and «Пригалъ кавалеріи», were folded into their works by `work_title_aliases.csv` (RG
   2026-10-29, "Yes, alias them"); «Паяда» was never added there.
2. **«Дочь Фараона», SP 1904-05, has no work** (`production.work_id` blank), although its one date (13 Feb 1905) now matches
   a «Дочь фараона» performance supplied from the list and the review (`production_date`). The entry match runs only on the
   Repertoire's printed titles and misses supplied performances.
3. The one proposed credit is «Щимана» (music, «Волшебный башмачекъ», 1900-01): it waits on the Шиманъ identity held in
   the person audit.
4. «Золотая рыбка», Moscow 1904-05, prints «Всего—7» over 6 dates: «ноября 14 (2 раза: утромъ и вечеромъ)». As printed;
   the Repertoire has all 7.

### RG's questions and rulings

**L1 — «Паяда и рыбакъ» folded (RG 2026-11-04, "Yes, fold it").** One row in `pipeline/entity_curation/work_title_aliases.csv`
(matching only; the 20 Sep 1892 performance keeps «Паяда и рыбакъ» as its printed title). «Наяда и рыбакъ» 15 -> 16
performances; the 1892-93 SP list entry now matches one work; the retired work id is in `entities.work_id_crosswalk`.
Rebuilt `build_entities` -> `validate_performance_dates` -> `build_research_model` on a copy, then production: nothing else
changed, 0 person_link shifts.

**L2 — «Дочь Фараона», SP 1904-05 (RG 2026-11-04, "okay, go ahead").** `build_productions`: an entry whose dates match no
work the Repertoire prints now falls back to performances supplied from another part of the yearbook, same city and date,
under the list's title (or its parent's). The entry now has work «Дочь фараона» (from the 13 Feb 1905 corps de ballet
benefit, supplied from the list and the review on RG's 2026-10-12 ruling); every list entry has a work. Nothing else changed.

**L3 — traceable to the printed page (RG 2026-11-04: "As long as someone looking at the data can trace its source. In the
case of this Pharaoh's Daughter performance, I'd want to make sure it could be traced back to the page number of the season
review.").** The supplied «Дочь фараона» row (13 Feb 1905) cited the list and the review only by internal id. Its
`supplied_performances.csv` basis now gives the list's printed page (p. 138, ForUpload_1904-05_Spisok_BalletProductionsSP.pdf)
and the review's folio (SP ballet review f. 117, with the sentence quoted), ids kept. The other four supplied performances
already cite review folios. Rebuilt on a copy, then production: one `research.performance` note changed.

**Provenance goal (RG 2026-11-04): "I want the researcher to be able to trace how something appeared in the research layer
(its source) and any attendant decisions."** Checked every research table for a path to the printed page and a column for the
decision. Planned as a provenance pass AFTER section 6 (RG "After reviews"): (1) one shared source-page table (page id, source
file, scan page, printed page) that events, list entries and review pages join to; (2) a note on works that absorbed a printed
variant through `work_title_aliases.csv` (Паяда, Ваядерка, Пригалъ …) and a basis for each list entry's chosen work;
(3) say in the dataset README that transcription fixes are traced in git and `docs/eval/`; (4) a short "how to trace a value"
guide in the published README / Datasette description (note columns; `known_issues.md`; this review doc).

## 6. Season reviews (2026-11-04)

(Queries logged in `docs/query_log.md`, "Research-layer review: Season reviews". Ballet reviews only: RG 2026-10-09, opera
reviews carry no cast data she wants.)

### What one record holds

- **`review_assertion`** — 2,655 cast statements ("this performer danced this role"): `role_surface`, `performer_surface`
  as printed, `performer_person_id` (2,426; `link_method` already-linked 2,317, spiski-credit 109, unresolved 229), `work_id`
  (1,877; `work_source`: the block 1,523, an earlier block on the page 407, the previous page 138, ambiguous 138, none 449),
  `date_undate` (683), `page_id`, `block_id`, `printed_folio`. 356 pages, 19 seasons.
- **`review_credit`** — 2,410 creator and craft credits: ballet_by 809, music 573, author 273, scenery 230, staging 190,
  choreography 80, source 72, libretto 54, staging-revival 39, costume_design 28, machinery 15, costume_making 14, props 13,
  instrumentation 8, costumes 5, footwear 3, headwear 2, wigs 2; 2,226 linked to a person, 2,358 to a work; `printed_phrase`,
  `context_flag`, `curator_note`.
- **`review_dance`** — 914 dance numbers (`dance_surface`, `printed_text`, work 632, dated 56), with
  **`review_dance_performer`** 2,982 (2,881 linked) and **`review_dance_composer`** 67 (34 linked).
- **`review_solo`** — 96 instrument solos (69 players linked, 37 works).

Cast statements by season: SP from 1891-92, Moscow from 1890-91, mostly 20-250 a season; then 1907-08 142, 1908-09 5,
1909-10 none, 1910-11 2. Raw has review pages 1890-91 – 1910-11 (no 1898-99 review exists; no 1909-10 pages) plus 4 pages
of 1912-13.

### Held earlier but not carried into research

- **The review text.** `raw.review_block`: 4,697 passages, 1.4 million characters, 1,074 pages (Ballet 702, Opera 262,
  All 110). Research rows cite `page_id`, `block_id` and `printed_folio`, but the passage itself is not in research or the
  sqlite export: a reader can find the folio but not read the sentence the row came from.
- **Mentions in the prose.** `entities.review_mention`: 27,327 (22,102 linked to a person, work or institution). Research keeps
  only the structured statements built from them, so "every passage that names Кшесинская" is not a research query.
- `entities.review_person` / `review_work`: the review-only people and works, carried into `research.person` and
  `research.work` (person_source / work_source = review).

### Things noticed (for RG)

1. **No link from a review statement to a Repertoire event or performance.** Only 683 of 2,655 cast statements carry a date,
   and none carries an `event_id`. "Who danced this role on this night" needs a hand join on season, city, work and date.
2. **The review text is not in research** (above): this is also the provenance goal's main review gap.
3. **Theater mentions (held over from section 3, T2):** 32 adjective «Новыя / Новая / Новыхъ» linked to the «Новый» theater,
   105 Petersburg theater names unlinked. No research table uses them.
4. Coverage after 1907-08 is thin (1908-09 5 statements from 12 pages; 1909-10 no pages; 1910-11 2): the later reviews are
   narrative, without cast lists. The 1912-13 pages are outside the Repertoire's seasons.
5. Craft credits with no person: footwear 3, headwear 2 (of 5); costume_design 7 of 28; scenery 45 of 230.

### RG's questions and rulings

**R1 — the review text in research (RG 2026-11-04, "Yes, add the text").** New `research.review_page` (1,074: season, city,
genre, printed folio, reading-order flag, number of passages) and `research.review_passage` (4,697: page, position, kind of
passage, text, caption), built by `build_reviews_duckdb.py` from `raw.review_page` / `raw.review_block` (the text after
`review_text_corrections.csv`), so they refresh with every review-chain run. Every `review_assertion` and `review_credit`
row's `block_id` resolves to a passage. Opera and «All» review pages are included (the text, not cast data). Export schema
in `build_datasette.py`; `docs/schema.md`. Nothing else changed; 0 person_link shifts.

**R2 — cast statements linked to Repertoire events (RG 2026-11-04, "Yes, link them").** `review_assertion.event_id` +
`event_match_note`, set in `build_review_assertions.py`: a dated statement links only when its city and date name exactly one
performed event whose bill carries the statement's work (or an excerpt of it). Linked 543. Not linked, each with its note:
no date 1,972; no work on the statement 69; events that day, none with the work 40; no performed event that day 30 (mostly
the quoted historical casts, 1844-1875); two events with the work 1. Export schema; `docs/schema.md`. Nothing else changed.

**R3 — review theater mentions (RG 2026-11-04, "Yes, fix them"; T2 from section 3).** Two faults in
`match_review_mentions.py`: (1) the Маріинскій, Александринскій and Михайловскій were indexed twice, as the research
theater and as an INST: tag, so every such mention had two candidates and stayed unlinked; the INST: tags for those three
are dropped. (2) «Большой», «Малый», «Новый» are also plain adjectives («Большой маршъ», «Новыя декораціи»): those three
theaters now link only when «театръ» follows (a line-break hyphen allowed). Theater mentions before -> after: unlinked 105
-> 0 (Маріинскій 83, Михайловскій 20, Александринскій 2); «Новый» 45 -> 9; «Большой» 9 -> 0; «Малый» 3 kept; the 45
adjective mentions dropped. No person or work link changed anywhere; `mention_id` renumbers after the dropped rows
(`review_credit.mention_id` follows). «въ Большомъ и 5 въ Новомъ театрѣ» leaves the Большой unlinked, as before.

**R4 — the review prose mentions in research (RG 2026-11-04, "Yes, add them").** New `research.review_mention` (27,282),
built by `build_reviews_duckdb.py` from `entities.review_mention`: passage, page, season, city, type, position in the passage
text, surface as printed, and typed links — `person_id` 17,703, `work_id` 3,097, `theater_id` 117, `institution` 470
(imperial, moscow, petersburg, hermitage, krasnoe_selo), `role_name` 775 — with `candidates_n` / `candidate_ids`,
`link_method`, `link_confidence`, `unlinked_reason`. The matcher's scoring notes stay in entities. No FK to person / work /
theater (the research build drops and recreates them). Export schema; `docs/schema.md`. Nothing else changed.

RG asked (2026-11-04) whether the matching catches declined forms and pre-reform spellings. Checked: declined forms yes
(«Кшесинской», «Преображенскою», «Гердтомъ», «Легатомъ» all link); pre-reform letters folded for lookup (ъ, ѣ, і, ѳ, ѵ;
a final ь set for ъ, «Легать» 84 links). Of 4,000 unlinked person mentions, 3,906 are ambiguous (several people share the
surname: «Петипа» 377, «Егорова», «Павлова», «Ѳедорова»), 93 have one candidate not accepted, 1 none. But 727 name-like
surfaces (1,116 occurrences) match no person: mostly dancers outside the staff lists (Андреянова, Санковская, Прихунова,
Мадаева — the quoted old casts), and some spellings the fold cannot absorb («Ленъяни» medial ъ, «Гердъ» dropped т,
«Леватъ» probable misread, «Іѳедорова» stray letter). Fixing those needs scan-checked rows in `review_person_variants.csv`
(4 so far): next question for RG.

**R5 — the 727 unmatched review names (RG 2026-11-04): "Not now since I'm up against usage limits, but i will want to do
so."** Pending: scan-check `outputs/reviews/mentions/review_mention_unknown.csv` (727 surfaces, 1,116 occurrences) and add
the genuine spelling variants to `docs/eval/review_person_variants.csv`; the dancers outside the staff lists stay unlinked.

## Additions by the other sessions, checked 2026-11-04

- **`work.entry_kind`, `art_form`, `art_form_basis`** (work-art-form session, merged 3276325): drama 2,257, opera 319,
  ballet 251, operetta 42, concert 11; 57 without (programme items 47, ceremonial 4, others 6). Every value has its basis.
  33 works' art form differs from a performing company's discipline: operettas played by the drama companies («Парики»,
  «Не бывать-бы счастью», French «opérette»), as RG's rule intends.
- **`person_death`** (307): roster «†» 193 (trace via `source_ref` = appearance -> folio), obituaries 108 and death notices 6
  (printed page on the row); all linked to a person.
- **`set_design`** (61, 1892-93 decorators' lists, SP 28 / Moscow 33): all linked to the decorator, printed page on every
  row. No `work_id`: the work is text only (`work_printed`); every title matches a research.work, three match two
  (Млада, Сельская честь, Снѣгурочка).
- **`person_appearance` source_file / scan_page / printed_folio / city**: filled on all 23,980.

**D1 — set designs linked to works (RG 2026-11-04, "Yes, link them").** `set_design.work_id`: the whole work with the printed
title; where two works share it, the one whose printed genre is the set's (Млада, Сельская честь, Снѣгурочка: all «оп.»,
so the operas); a set printed without a genre takes the genre printed for that title on the same page (two Снѣгурочка, one
Кольцо любви, assistants' credits at the Большой). All 61 linked. Export schema; nothing else changed; 0 person_link shifts.

## Provenance pass (2026-11-04, RG: "let's take care of this")

1. **`research.source_page`** (2,810 pages: Season Review 1,074, Repertoire 688, BalletArtists 392, Musicians 224,
   TheaterSchoolStaff 104, ProductionTeam 100, Administrators 90, BalletProductions 63, Graduates 56, SeasonStats 19), with
   source file, scan page (1-based) and printed page or folio; every file exists under `pdf/`. The 100 two-page spreads
   (1890-91 – 1897-98) get the season's Repertoire PDF and the printed pages, no scan page: their jpg numbering does not
   follow the page ids (49 of 100 differ), so none is guessed. Review file names are derived from the page id (checked
   against the review manifest: 1,074 of 1,074). Every event, staff-list appearance, list entry, review passage and review
   page finds its source page. `event.page_id` added.
2. **`work.title_note`** records each printed variant a work absorbed through `work_title_aliases.csv` (54 works, 76 notes;
   e.g. «Наяда и рыбакъ»: «printed «Паяда и рыбакъ» on 1 performance(s), read as this work …»).
3. **`production.work_basis`** says how each list entry's work was chosen (628 of 628: list title = work title 609; most
   matched dates, title differs 18; via a supplied performance 1).
4. **README "Tracing a value to its source"**: where each table's page is, the note columns, and where the decisions are
   written up (including that transcription fixes live in the raw JSON, `docs/eval/` and git).
Tested on a copy, then production: no existing column changed except the new title notes; 0 person_link shifts.

**R5 in progress — the unmatched review names, scan check (2026-11-04, RG "Yes, check the 209").** The 727 unmatched surfaces
were sorted by distance from a research surname: one letter 209 (318 occ.), two letters 218, none close 277, too short 23.
The 209 gave 418 occurrences still unmatched on 241 pages; five helper agents read them on the review images (crops at 2-6×)
and Claude checked every misread crop on contact sheets (agreeing on all but «Прѣспяковъ», which the print really has with
п). Result, 404 distinct occurrences, in `docs/eval/review_name_scan_check_2026-11-04/results.csv` (checked by Claude; scan
reads are finding aids, RG reads the source):
- text correction 92 (+7 stray line-break hyphens kept in the stored text, «Чере-пова» …);
- line-join rule 11: hyphenated names split across a line («Сенъ-|Леона», «Вальтеръ-|Кюне», «Дель-|Эра») lose the hyphen in
  the matcher's reflow;
- printed as stored 193: misprints of known people (~35: «Петина», «Гердъ», «Кемереръ», «Стуколькинъ», «Прѣспяковъ» …, need
  RG's identity call), names that are probably other people (the other gender of a roster surname: «Ефремова», «Воронина» …),
  names whose form matches research but the matcher's other rules declined;
- not a person name 98 («Вальсъ», composers, role names); page-end fragments 8; unclear 2 («Шсбергъ/Шебергъ», «Ваильевъ»).
Proposed order: (1) the mechanical text corrections and the line-join rule; (2) the misprint list with a person for each, for
RG; (3) the rest stay unlinked.

**R5 step 1 applied (RG 2026-11-04, "Yes, apply them").** 96 scan-checked rows added to `docs/eval/review_text_corrections.csv`
(92 misreads, 7 stray line-break hyphens, «Гердъ» on 1904-05 SP p011 split into three context-specific rows because the page
prints one genuine «Гердъ»), each scoped to its page with its count; 103 replacements. Line-join rule in
`match_review_mentions.reflow` (shared with `build_review_assertions`): a lowercase letter + hyphen + line break + capital keeps
the hyphen (`COMPOUND_BREAK`), so «Сенъ-|Леона», «Вальтеръ-|Кюне», «Донъ-|Кихотъ», «Царь-|Дѣвица», «Римскаго-|Корсакова» are
no longer joined (86 places; one doubtful, «гер-|Г.»). Follow-ups: four curated work links and one unlinked-reason row keyed on
the old joined «ЦарьДѣвица/-ы» updated; «Роль «Царь-Дѣвицы»» kept unlinked by a curated row (RG's earlier role-name ruling);
a drop-order bug from R4 fixed in `build_reviews_duckdb.py` (review_mention before review_passage).
Effect: person mentions linked 17,703 -> 17,802; cast statements 2,655 -> 2,671 (2,442 linked, 547 linked to an event); dance
performers 2,982 -> 3,045 (all 63 new ones linked); no linked mention lost or changed its person; 10 cast statements got new
assertion ids because their role text gained its hyphen («Флеръ-де-Лись», «Хейдеръ-Али»), same dancers. Unmatched name surfaces
727 -> 666. Production equal to the tested copy; 0 person_link shifts.
Next for RG (step 2): ~35 printed misprints of known people need a person each.

**R5 step 2, group A applied (RG 2026-11-04, "Yes, link group A").** 33 rows in `docs/eval/review_person_variants.csv` (printed
misprint -> the staff lists' family name, each the only person of that surname in the season's lists: «Гердъ» -> Гердтъ,
«Гиллердтъ»/«Гиллеръ» -> Гиллертъ, «Лабойко» -> Лобойко, «Алекснэ» -> Алексне, «Давидова» -> Давыдова, «Прѣспяковъ» ->
Прѣсняковъ …). RG asked how many fall in old cast lists outside the Yearbooks' seasons: 3 of the 54 new links, all wrong and
undone before production — «Гердъ» in the quoted 1865 cast on 1904-05 p.116 (unlinked again by a curated row; the print has
«Гердъ» there), and two «Кемереръ» in lists of earlier dancers (1906-07 Moscow «Лизы послѣдовательно …», 1894-95 SP «Кемереръ,
Канцыревой, Цукки»), women linked to Владиміръ Кеммереръ. The «Кемереръ» variant was Claude's error (gender judged from the bare
surname; the reviews print «Кемереръ 1-я / 2-я») and is dropped. Net: person mentions linked 17,802 -> 17,853; cast statements
linked 2,442 -> 2,452; dance performers linked 2,944 -> 2,965; no existing link lost or changed. Unmatched surfaces 666 -> 634.
Open for RG: group B (5 doubtful: Горина/Дорина, Салинъ/Силинъ, Сировъ/Сизовъ, Клейнъ/Крейнъ, Беккъ-Бекль/Бекъ) and group C (9 with
several candidates); groups D-E stay unlinked.

**R5 group B — «Горина» (RG 2026-11-04, "keep separate pending further information").** Unlinked; recorded in
`docs/eval/uncertain_person_identities.md` with the evidence sheet `docs/eval/scan_audit/R5_groupB_Gorina_Dorina_evidence.png`.
Correction to an earlier remark: «Андреянова» also appears in a current 1903-04 corps list (f. 112), so not only in quoted old casts.

**R5 group B — «Клейнъ» (RG 2026-11-04, "Yes, link to Крейнъ").** The 1901-02 Moscow review's «Соло на скрипкѣ исполнилъ г. Клейнъ»
(f. 290) is Крейнъ, Давидъ Сергѣевичъ (first violin, Moscow orchestra 1897-; the same reviews print «на скрипкѣ—г. Крейнъ» in 1900-01
f. 270, 1901-02 f. 313, 1902-03 f. 243). Evidence `docs/eval/scan_audit/R5_groupB_Klein_Krein_evidence.png`. To apply with the rest
of group B.

**R5 group B — «Беккъ», «Бекль» (RG 2026-11-04, "Yes, link both").** «Беккъ» (1906-07 Moscow f. 232) and «Бекль» (1905-06 Moscow
f. 231) are Бекъ, Константинъ Александровичъ (Moscow ballet troupe 1892-93–1910-11; «Бекъ» already linked in 1905-06 f. 210, 224,
225). Evidence `docs/eval/scan_audit/R5_groupB_Bekk_Bek_evidence.png`. Variant rows for «Клейнъ», «Беккъ», «Бекль» added to
docs/eval/review_person_variants.csv; the rebuild follows the last group B ruling.

**R5 group B — «Салинъ» (RG 2026-11-04, "Yes, leave unlinked").** 1905-06 Moscow f. 213, «Нилъ—г. Салинъ» in the «Дочь фараона»
revival. No single fit: Силинъ is a Moscow administration clerk (since 1867), Санинъ is SPb school staff 1902-04, and the dancers two
letters off are five people (Бакинъ 1-3, Гулинъ 1-2). Left unlinked. Evidence `docs/eval/scan_audit/R5_groupB_Salin_evidence.png`.
Noted, not applied: the stored text on that line reads «Ниль … и др.» where the scan prints «Нилъ … и друг.».

**R5 group B — «Сировъ» (RG 2026-11-04, "Yes, link to Сидоровъ").** 1902-03 Moscow f. 233, «Робертъ Пуспенъ, клеркъ,— г. Сировъ»:
the 1902-03 Moscow ballet list credits Сидоровъ, Иванъ Емельяновичъ with «Эсмеральда (Робертъ Пуспенъ—7)», the only Пуспенъ credit
in the lists. Linked. Evidence `docs/eval/scan_audit/R5_groupB_Sirov_evidence.png`. Noted, not applied: raw stores that credit as
«Пуспень» (scan «Пуспенъ»).

**R5 group B applied (2026-11-04).** Review chain rebuilt on a copy, then production. Exactly 4 new person links, none lost or
changed: «Клейнъ», «Сировъ», «Бекль», «Беккъ». Assertions +2; credits, dance performers and solos unchanged. Person mentions
linked 17,857 of 21,863; unknown surfaces 634 → 630. «Горина» and «Салинъ» stay unlinked. Next: group C (names with several
candidates).

**R5 group C — «Гавлова 2-я» (RG 2026-11-04, "Yes, link to Anna").** 1904-05 SP f. 114, «Danse Espagnole—г-жа Гавлова 2-я»: the
printed «2-я» selects Павлова 2-я, Анна Матвѣевна (list p. 19 no. 77). Variant row added; to apply with the rest of group C, checking
in the test rebuild that the ordinal lands on Анна. Evidence `docs/eval/scan_audit/R5_groupC_Gavlova_Pavlova_evidence.png`. Logged,
not chased: this block's stored text repeats some names («Матвѣева,Рѣпина, Матвѣева,Рѣпина»); the repeats predate R5.

**R5 group C — «Пашенко 1-й» (RG 2026-11-04, "Yes, link to Сергѣй").** 1895-96 SP f. 246, «Па-|шенко 1-й» (ш, or a worn щ, at the
available resolution): the «1-й» selects Пащенко 1-й, Сергѣй Назаровичъ (list p. 67 no. 47). Recorded as a printed variant with the
uncertainty noted. Evidence `docs/eval/scan_audit/R5_groupC_Pashenko_Pashchenko_evidence.png`.
Revised the same day: RG read the letter as щ ("I think it's a щ"), so this is a stored-text misread, not a printed variant. The
variant row was replaced by a text correction in docs/eval/review_text_corrections.csv («шенко 1-й» → «щенко 1-й», scoped to
review_1895-96_SP_ballet_p014).

**R5 group C — «Чекети» (RG 2026-11-04, "Yes, link to Enrico").** 1900-01 SP f. 187, «гг. Бекефи, Чекети и Кшесинскій 2-й»: the
men's «гг.» selects Чекетти, Энрико Цезаревичъ over Жозефина. Variant row added; the test rebuild must confirm the honorific
resolves it (otherwise a curated mention link). Evidence `docs/eval/scan_audit/R5_groupC_Cheketi_Cecchetti_evidence.png`.

**R5 group C — «Элеръ 1-я» (RG 2026-11-04, "Yes, link to Anna").** 1903-04 SP f. 109: the «1-я» selects Эрлеръ 1-я, Анна
Александровна (list p. 73 no. 116). Evidence `docs/eval/scan_audit/R5_groupC_Eler_Erler_evidence.png`. Logged, not chased: p004
prints «Эрлеръ 1-я» twice but only one mention is linked.

**R5 group C — «Ѳеодорова 2-я» (RG 2026-11-04, "Yes, link to Sofia").** 1905-06 Moscow f. 217, Хита in «Дочь фараона»: the list
credits Ѳедорова 2-я, Софія Васильевна with «Хита — 3». Printed variant (fuller spelling), not an error. Evidence
`docs/eval/scan_audit/R5_groupC_Feodorova_Fedorova_evidence.png`.

**R5 group C — «Гуля и Бера» (RG 2026-11-04, "Yes, link both").** 1906-07 SP f. 148, «балетъ Гг. Гуля и Бера «Фея Куколъ»»: the
ballet's creators. Linked for this mention only (docs/eval/review_mention_links.csv): «Гуля» → Гауль, Ф. (Q50307954), «Бера» →
Байеръ, Іосифъ (Q668930); no surname rule. Evidence `docs/eval/scan_audit/R5_groupC_Gul_Ber_Gaul_Bayer_evidence.png`. Logged, not
chased: «Петипа», «Егорова» and the work «Голубая Георгина» are unlinked in the same block.

**R5 group C — «Брантъ» (RG 2026-11-04, "Keep unlinked").** 1905-06 Moscow f. 225, cornet-à-pistons solo: Карлъ-Вильгельмъ (Труба)
or Владиміръ (Валторнъ) Брандтъ, with two listed cornetists besides. Left unlinked; entry added to uncertain_person_identities.md.
Evidence `docs/eval/scan_audit/R5_groupC_Brant_Brandt_evidence.png`.

**R5 group C — «Кусковъ» (RG 2026-11-04, "Yes, link to Ivan").** 1901-02 SP f. 193: the same folio prints the same group with
«Кусовъ». Linked to Кусовъ, Иванъ Николаевичъ for this mention only (review_mention_links.csv), since a surname rule would also catch
«Кускова» (Елизавета). Evidence `docs/eval/scan_audit/R5_groupC_Kuskov_Kusov_evidence.png`. Logged: stored «Аслинь», scan «Аслинъ».

**R5 group C — «Пономаревъ 2-я» (RG 2026-11-04, "Yes, link to Sergei").** 1904-05 SP f. 111: a print slip in the ordinal (feminine
«2-я» on a man under «Гг.»). Linked for this mention to Пономаревъ 2-й, Сергѣй Ивановичъ (list p. 25 no. 66). Evidence
`docs/eval/scan_audit/R5_groupC_Ponomarev2_evidence.png`.

**R5 group C applied (2026-11-04).** Text correction («Па-шенко» → «Па-щенко», RG's reading), then the review chain on a copy and on
production. 9 new person links, none lost or changed (the five ordinal/honorific cases each landed on the ruled person). «Гуля» and
«Бера» needed two variant rows («Гуль» → Гауль, «Беръ» → Байеръ) to be seen as mentions at all; the test showed no other effect.
Side effects: the Danse Espagnole (1904-05 SP f. 114) now has its two performers; one new assertion (Хита). Person mentions linked
17,866 of 21,870; unknown surfaces 630 → 623. «Брантъ» stays unlinked. Logged, not chased: the «Гуля/Бера» credit rows carry the right
work_id («Фея куколъ») but a stale work_surface «Голубая Георгина».

**R5 follow-up — four noticed slips fixed (RG 2026-11-04, "Yes, fix 1–4").** (1) 1905-06 MSK f. 213 «Ниль … и др.» → «Нилъ … и друг.»;
(2) 1901-02 SP f. 193 «Аслинь» → «Аслинъ» (both passages); (3) 1904-05 SP f. 114: six repeats at line breaks removed and the lost «8)»
restored — a corpus check found no other block with this pattern; the block's other misreads («артисты и артисты … трупьи» for
«артистки и артисты … труппы», «Воронковъ 1) Баклановъ») are left for a separate ruling; (4) raw: Сидоровъ's 1902-03 Moscow credit
«Пуспень» → «Пуспенъ» (outputs/full_run/raw/balletartists_1902-03_MSK_p007.raw.json, two fields; rebuilt with
rebuild_after_raw_edit.sh, one row changed per table). Items 1-3 are rows in docs/eval/review_text_corrections.csv. The 1903-04 and
1905-06 Сидоровъ credits carry the same misread (scans print «Пуспенъ»): evidence `docs/eval/scan_audit/Sidorov_Puspen_credits_evidence.png`,
not yet fixed. Noticed: a stray `balletartists_1902-03_MSK_p007.raw 2.json` sits beside the raw page (sync copy?), left untouched.
Follow-up (RG 2026-11-04, "Yes, fix both"): the same «Пуспень» → «Пуспенъ» fix applied to Сидоровъ's 1903-04 and 1905-06 Moscow credits
(raw JSON, two fields each; rebuilt; two rows changed per table; review layer unchanged). Not chased: outputs/full_run/raw holds 1,552
«*.raw 2.json» copies (from 2026-10-01 on), ignored by the pipeline.

## People items left from section 1 (2026-11-04)

**Item 1 — blank `city` (closed, no change).** Already resolved by the other sessions' "staff-list city/folio" addition: `city` is filled
on all 23,980 appearances from each list's printed heading (Directorate staff «both»; Свенторжецкій, «Техникъ при С.-Петербургской
Конторѣ», SP).

**Item 2 — «Заслуженн… артист…» (RG 2026-11-04, "Yes, fix the 8").** `rank` already carried the honour from 1900-01; 6 entries had it
only in the tenure note and 2 had it in print but nowhere in the data. Scan check by Claude of the gap seasons: the print omits it for
Петипа 1-я 1903-04, 1905-06, 1907-08, 1908-09, 1910-11, Гельцеръ 1906-07 and Кшесинская 1903-04 (left as stored). Fixed in raw
(`rank_or_title` on all 8; the printed sentence added to the note for Гельцеръ 1904-05 Moscow p. 57 and Кшесинская 1907-08 SP p. 17);
rebuilt with rebuild_after_raw_edit.sh; exactly 8 rows changed per table. Evidence `docs/eval/scan_audit/Zasluzhennaya_honour_evidence.png`.
Only these seven holders were checked; a corpus sweep for other missed honours was not done.

**Item 3 — Кшесинская 2-я 1905-06 / Moscow 1906-07 (closed, no change).** Both are the yearbook's own: the 1905-06 Petersburg list has
no entry for her (43. Кускова is followed by 44. Кякштъ; no Кшесинская on any page), and the 1906-07 Moscow list prints her as no. 50 with
the honour and «Тщетная предосторожность (Лиза—1)» (p. 52). Read on the scans by Claude.

**Correction to item 2 (2026-11-04).** The two entries reported as "missed" (Гельцеръ 1904-05, Кшесинская 1907-08) had the honour stored,
misfiled at the start of `credit_summary_text`; I had looked only at `rank` and the note. Adding it to their notes left it there twice. A
third entry, Преображенская 1908-09, has the same misfiling and a blank `rank`. Cleanup awaits RG.

**Item 2 cleanup (RG 2026-11-04, "Yes, clean up the 3").** The misfiled honour was removed from `credit_summary_text` for Гельцеръ
1904-05 and Кшесинская 1907-08 (it stays in `rank` and the note), and moved into `rank` and the note for Преображенская 1908-09 (SP p. 91,
printed after her date). Rebuilt; exactly 3 rows changed per table. No entry now has the honour in its credits line or only in its note;
`rank` carries it 30 times. Noted, not changed: Преображенская 1908-09 «Фея куколь» (scan «куколъ»).

## W8 C — the four list dates where the yearbook disagrees with itself (2026-11-04, RG "go ahead")

**«Катарина», Moscow, 17 Jan 1896 (RG 2026-11-04, "Yes, count Катарина").** The Repertoire prints «Эсмеральда, бал. 500 р. 50 к.»;
the ballet list puts «Катарина» on 17 Jan (Всего 3) and leaves it out of «Эсмеральда» (Всего 5); the staff list's role counts agree with
the list (16 dancers «Катарина» ×3; «Эсмеральда» principals ×5). One row in `pipeline/research_corrections/performance_work_overrides.csv`:
the performance keeps «Эсмеральда» as its verbatim title and counts under «Катарина». To apply with the rest of this group. Evidence
`docs/eval/scan_audit/1895-96_MSK_1896-01-17_Katarina_evidence.png`.

**«Очарованный лѣсъ», SP, 21 Sep 1898 (RG 2026-11-04, "Yes, link to 2 Sep").** The list prints «сентября 21, 27 … мая 2. Всего—3 раза»;
21 Sep is «Фераморсъ, оп.» alone; the Repertoire has the ballet on 2 Sep beside «Капризы бабочки» and «Волшебная флейта», which the list
itself dates 2 Sep; three performances in both; staff credits 3. No 1898-99 review. Added to `LIST_DATE_PRINT_TYPOS` as 2 Sep 1898 (the
printed «21» stays in `production_date`, with the reason in `date_correction_note`). Evidence
`docs/eval/scan_audit/1898-99_SP_1898-09-21_Ocharovanny_les_evidence.png`.

**«Волшебная флейта», SP, 19 Dec 1901 (RG 2026-11-04, "Yes, supply it").** The Repertoire prints «Сильвія, бал. 1743 р. 45 к.» alone; the list
dates both «Волшебная флейта» (Всего 4) and «Сильвія» (Всего 5) to 19 Dec; the Repertoire has «Волшебная флейта» only 3 times; the staff
list credits eight dancers with it 4 times. A row in `pipeline/research_corrections/supplied_performances.csv` (adds_to_bill = yes, as for
30 Nov 1903) adds it to the 19 Dec bill; the Repertoire's cell stays as printed. Evidence
`docs/eval/scan_audit/1901-02_SP_1901-12-19_Volshebnaya_fleyta_evidence.png`.

**«Шопеніана», SP, 9 Mar 1911 (RG 2026-11-04, "Keep as printed").** The list prints «марта 7, 9. Всего—4 раза»; the Repertoire's 9 Mar bill
is «Эвника» + «Карнавалъ» (3 «Шопеніана» in all); no staff-list role credits exist for it, and the review is silent for both March nights.
Kept as printed; `production_date` keeps the unmatched list date. Evidence `docs/eval/scan_audit/1910-11_SP_1911-03-09_Chopiniana_evidence.png`.

All four are in `docs/eval/reconciliation/outcome_ledger.csv` (1895-96-11, 1898-99-12, 1901-02-19, 1910-11-16), so they reach
`research.season_stat_gap` with links to their events.

**W8 C applied (2026-11-04).** `build_research_model` and the review chain rebuilt on a copy, then production. Changes: the 17 Jan 1896
performance counts as «Катарина» (verbatim «Эсмеральда» kept); «Волшебная флейта» supplied on 19 Dec 1901; three list dates now match
(Катарина 17 Jan, Волшебная флейта 19 Dec, Очарованный лѣсъ → 2 Sep); four ledger rows in `research.season_stat_gap`. One side effect found
and fixed in `match_review_mentions.py`: the overridden performance's printed «Эсмеральда» had been indexed as a quoted title of «Катарина»,
making a 1910-11 review's «Эсмеральдой» ambiguous; a printed title that is another work's canonical title is now skipped. After the fix no
review link changed.

## Small slips (RG 2026-11-04, "Yes, apply them")

Scan-checked by Claude (`docs/eval/scan_audit/small_slips_2026-11-04_evidence.png`). Fixed: (A) 1904-05 SP review f. 114 «артисты и артисты
балетной трупьи» → «артистки и артисты балетной труппы» (`review_text_corrections.csv`); (B) Преображенская 1908-09 «Фея куколь» → «Фея
куколъ» (raw, rebuilt, one row per table); (C) 1903-04 SP review p004 «…Пишо, Эрлеръ 1-я» linked to Эрлеръ 1-я, Анна (`review_mention_links.csv`;
the ordinal had been lost); (D) the «Гуля/Бера» credits' label «Голубая Георгина» → «Фея Куколъ» (`review_credit_overrides.csv`, work_surface).
Left as printed: «Воронковъ 1) Баклановъ» (the print's own «1)»), and the 3 Apr 1899 and 4 Oct 1903 Pushkin evenings (programme in the
heading only; no ballet; inclusion test). Nothing else changed.

## Raw-to-research check, second pass (2026-11-04)

Every raw / analysis / entities table and column compared with research (query log). Row gaps all deliberate (the excluded 1910-11 p056
page, 5 group music credits, 6 supplied performances). **Added (RG "Yes, add it"):** `person_appearance.printed_family_name`,
`printed_first_name`, `printed_patronymic` — the name as each season's list prints it (differs from the canonical name on 4,057
appearances: ordinal 2,873, spelling 647, first name 537). Still not carried: `list_number` (printed on 16,380 entries; RG 2026-11-06: not needed, see Outstanding item 3),
event month/year heading text, the lists' «Исполненъ»/«Всего» lines verbatim and section heading, review layout fields,
`season_stat_line.city_verbatim`; pipeline-internal by design: merge history, Wikidata decisions, matcher evidence, retired ids.

## Pre-publish check (2026-11-04)

Fresh export from production builds cleanly (35 tables, row counts = research, 0 FK violations, integrity ok). Gold set: repertoire 97.8%,
roster 76.4% (gold predates later convention rulings; `run_history.csv`). **«Сцепа» (RG "Yes, restore it"):** work 5080f6ba's only printing
is the misprint, so it had taken «Сцепа изъ бал. Корсаръ» as its title; `WORK_TITLE_FROM_ALIAS` in build_research_model now titles it
«Сцена изъ бал. Корсаръ» (verbatim kept on the performance, reason in title_note). Not changed, for RG one at a time: the same applies to
«Agence dramatiqus» and «Бокаччіо» (misprints, titled by them), and 11 works titled by a printing with its genre/subtitle attached. For Andy:
the local research_dataset.sqlite (3 Nov) is stale — rebuild; the Cloud Run metadata describes 6 of 35 tables.

## Site and table descriptions for the published dataset (2026-11-04, RG "okay go for it", "Commit as is")

`docs/datasette_metadata.json` (tracked; no plugins block, so no password hash in git): the site title and description (now 1890-91 –
1910-11, all five sources, traceability) and a description for each of the 35 exported tables. The old publish file
(`outputs/full_run/datasette_metadata_cloudrun.json`, 2026-08-21) described 6 and sorted `event` by `event_date`, a column that does not
exist; in Datasette 1.0a37 that makes the `event` table return an error (400). The draft sorts by `date`. Checked in Datasette 1.0a37:
every table page opens and shows its description. `pipeline/merge_datasette_metadata.py` copies title, description and tables into the
publish file and keeps its plugins block (tested on a copy; the real file untouched). For Andy at the next publish.

## OUTSTANDING — resume after Friday 2026-11-06 (noted 2026-11-04)

Everything above is applied, committed and pushed (main at 2f60354). Still open, in the order to take them:

1. **Ambiguous review names (the one large item).** 3,909 person mentions in `research.review_mention` have several candidates (Петипа
   377, Егорова 117, Павлова 109, Ширяевъ 92, Ѳедорова 86, Николаева 80, Ивановъ 68, Смирновъ 67); 94 more have one candidate not accepted.
   Approach: rule by rule (season, city, ordinal, honorific, that season's staff-list role credits), each rule brought to RG with evidence.
   **IN PROGRESS 2026-11-06, pilot «Петипа»** (378 tied mentions; the matcher offers all six Petipas for every mention, with no
   season or city filter). RG's guidance: Marius can be named anywhere as a creator (choreographer, not only ballet master in SP);
   dancers sometimes guested in the other city, so season and city are evidence, never a filter; a role named in the review can be
   checked against that season's staff-list entry (`raw.person_entry_credit` named_work role_name) — not foolproof, helps in ties.
   Rulings so far (nothing applied yet; applied together once the Petipa rules are all ruled):
   - **R5 creator wording → Маріусъ Ивановичъ** (RG "Yes, link to Marius"): «балетъ / бал. / въ постановкѣ / соч. / танцы и
     постановка … М. Петипа», «… М. Петипа, музыка …», «Программа его составлена М. Петипа»; both cities. 199 mentions (158 SP /
     40 Moscow at ruling, +1 «Испытаніе Дамиса» М. Петипа и А. Глазунова moved in after). Scan sample 10/10.
   - **R4 «г-жа М. Петипа» (honorific directly before the initial, 50) and «М. Петипа» inside a «г-жи …» list of ladies (9) →
     Марія Маріусовна (1-я)** (RG: "these are definitely Maria"; old-cast risk "highly unlikely"). Only Marius and Марія carry «М.»
     on any staff list; none of the 59 falls in 1906-07 or 1909-10, when she is unlisted. Scan sample 7/7; 8 roles match her
     staff-list entry and no sister's.
   - **6 more → Марія** (RG 2026-11-07 "Yes, link to Марія"): «М. Петипа, заслуженная артистка» (5, incl. 3 «Малороссійскій танецъ»
     in «Конекъ-Горбунокъ», where the same sentence names «Постановка и танцы Маріуса Петипа») and «балерины М. Кшесинской (Аспичія)
     и М. Петипа (Néva)». The 7th, «исполнили pas de trois, М. Петипа, и … pas de deux, того же балетмейстера» (1901-02 p.205), is
     the choreographer → R5. Totals: Marius 200 (R5), Марія 65.
   - **First names / full initials** (RG "Yes, link as named"): 27 «Маріуса / Маріусомъ Петипа» + «М. И. Петипа» → Marius;
     «бенефисъ г-жи Маріи Петипа, за 25-лѣтнюю службу» (4 Feb 1901) → Марія.
   - **Ordinals + season** (RG "Yes, link by ordinal"): «Петипа 1» → Марія (13), «2» → Надежда (6), «3» → Вѣра (8; all 1903-04 /
     1905-06, Любовь has none). 6 role matches, none against. Held out: the pupil «воспитанницы Петипа 1-я» (1897-98 caption,
     probably Любовь, the elder pupil sister).
   - **Old casts / quoted chronicles → unlinked and listed** (RG "Yes, unlink and list"; RG: every historical block must be findable
     later). `review_historical_passages.csv` gains a `scope` column: 'whole' (the build re-dates the block) or 'part' (a block that is
     only partly a quoted cast, recorded so it can be found; its rows are dated in review_assertion_overrides.csv, its names unlinked
     in review_mention_links.csv). +9 rows: the 1886 «Жертвы Амуру» cast (1893-94 p.231), the 1859 «Парижскій рынокъ» cast (1894-95
     p.204), the c. 1856 Прихунова review quoted in 1900-01 (5 blocks, undated), and 'part' rows for 1904-05 p.116 (1865 cast before
     «При настоящемъ возобновленіи») and p.118 (1860 «Голубая Георгина» chronicle). 30 explicit unlinks (15 had been linked to
     present-day dancers: the 1886 cast, Л. Ивановъ, Гердтъ); creator credits inside the quotes keep Marius. 7 cast rows dated
     1865-11-04. Review chain on a copy then production (backup `outputs/full_run/db_backup_historical_blocks_2026-11-07/`): exactly
     those 30 mentions and 7 rows changed; 0 person_link shifts. Lesson: the `occurrence` in review_mention_links.csv counts in the
     matcher's own row order (outputs/reviews/mentions/review_mention.csv), not text order.
   - **Role in only one staff-list entry → that person** (RG 2026-11-07: "if only one Petipa has that role listed, we know it was
     her"; general rule for the review-name work): «Маріи—г-жа Петипа» (Привалъ кавалеріи) and «Пахита—г-жа Петипа» (1900-01) →
     Марія. **Люсинда** (1905-06 p.128, «графини Люсинды—г-жа Петипа 1», scan-confirmed): the staff lists credit Надежда (2-я) with
     Люсинда in 1904-05 and 1905-06 and Марія never → Надежда, the «1» a probable print slip (RG "Надежда (print slip)";
     genuine_print_typos.md, unconfirmed). The only role conflict among all ruled Petipa links.
   Noticed, not chased: roles parsed as persons («Графа» → Граффъ, 1904-05 p.118; «Парисъ» → Парисъ, 1893-94 p.231); «1-жа» for
   «г-жа» in captions; «Имераторскихъ» (1905-06 p.14) a likely print typo.
   - **Last rulings (RG 2026-11-07):** «Малороссіянъ: г-жа Петипа» (Конекъ-Горбунокъ 1905-06) → Марія (same dance, same production named
     «М. Петипа, заслуженная артистка» in three other reviews); «Королева—г. М. Петипа» (1902-03) → Марія by the role rule (RG: men
     played character women's roles, so the «г.» is not called a slip); «г. И. Петипа» (1905-06 p.134) → Marius, «И.» logged as a
     slip; pupil «Петипа» 1901-02 → Вѣра (only Petipa still at the school), pupil «Петипа 1-я» 1897-98 unlinked; past events: 1884
     staging → Marius, 1875 «дебюта г-жи М. Петипа» → Марія, «Петипа-отца» beside «М. И. Петипа» as Гердтъ's teachers → Jean-Antoine
     (Q3163722); 1855 «бенефисъ М. Петипа» unlinked (uncertain_person_identities.md), «двумя Петипа, отцомъ и сыномъ» unlinked (two
     people in one name); the divertissement «panaderos» (1900-01) and 6 other plain «г-жа Петипа» left unlinked (no deciding evidence).
     RG's priority: people of the Yearbook period; historical passages flagged and listed, not adjudicated.
   - **APPLIED 2026-11-07:** 332 links in review_mention_links.csv (Marius 231, Марія 84, Вѣра 9, Надежда 7, Jean-Antoine 1), occurrence
     counted in the matcher's order. Review chain on a copy then production (backup `outputs/full_run/db_backup_petipa_links_2026-11-07/`):
     exactly the 332 mentions as ruled, 14 cast statements (13 gained a performer; «Танцы и постановка — М. Петипа» 1904-05 moved from
     Марія to Marius), 3 credits gained Marius, 15 dance performers; 0 person_link shifts. Tied person mentions corpus-wide 3,908 → 3,588;
     «Петипа» left unlinked 46 (historical + the cases above).
   **General rules (RG 2026-11-07: "will we have to do these all case-by-case?" → no; rules ruled once, applied to every surname).**
   Files: `docs/eval/review_names_general_rules_2026-11-07/`. Safeguards common to the rules: the candidate must agree with the gender of the
   honorific, the printed surname ending and the ordinal ending («-я/-й»); a printed ordinal (incl. bare digits after the name, «Эрлеръ 2»,
   which the matcher ignored) must match the person's number in that season's list; mentions in a pupils' list need a pupil/graduate
   candidate; quoted old casts (oldcast_check.py: «При первомъ … представленіи», «первыми исполнителями», «въ первый разъ поставленъ» …,
   looking back up to 3 blocks, stopped by a dated current performance) and pre-1890 years nearby are excluded.
   - **G1 — only one possible person on that season's list in that city → that person** (RG "Yes, apply G1"): 535 mentions (SP 313,
     Moscow 222; ballet artists 489, musicians 23, graduates 10 …); 183 set aside by the safeguards. Scan sample 11/12 (the 12th, a reprinted
     1890 premiere cast, led to the old-cast safeguard). Side finding: three person records for «Спрышинская» (Целина / Целія / Цецилія
     Владиславовна) — merge candidate.
   - **G2 — several on the list; the printed number, gender (honorific / surname ending / number ending), initial or pupils' list leaves
     one → that person** (RG "Yes, after one more check"): 1,297 mentions (SP 732, Moscow 565; number 1,046, gender 232, pupils 15,
     initial 4). Scan sample: the deciding detail printed as transcribed 12/12; 2 were quoted old casts («первыми сюжетами тогдашней
     труппы», «Составъ первыхъ исполнителей»), so oldcast_check.py was widened (24 caught; G1 now 531). A third sample (12, from the cleaned
     sets) is checked before applying.
   - **G3 — the role in only one candidate's staff-list entry → that person** (RG "Yes, apply G3", generalising the Petipa ruling):
     32 mentions; never used against a printed number or gender («Вестрисъ—г. Легать 5-й» set aside). Cross-check: confirms 84 G1/G2
     choices, contradicts none. Third scan sample (12 from the cleaned sets): all current-season, all support the link.
   - **APPLIED 2026-11-07:** 1,859 links (G1 531, G2 1,297, G3 32 less one: an existing old-cast unlink for «Лебедева», Moscow 1901-02,
     kept). Review chain on a copy then production (backup `outputs/full_run/db_backup_general_rules_2026-11-07/`): exactly those 1,859
     mentions; cast statements +61 performers, credits +3, dance performers 250 rows, dance composers +2 («музыка А. Гербера»), solos +4;
     nothing switched or lost; 0 person_link shifts. **Tied person mentions 3,588 → 1,729**; linked 20,033.
   Next: the surname-by-season groups (plain surname among namesakes); historical leftovers flagged; the ~150 pupil mentions linked to an
   older namesake (see below).
   **School pupils in the reviews (RG 2026-11-07: "we should definitely collect a list of school pupil mentions"):**
   `docs/eval/review_pupil_mentions.csv` (script `docs/eval/review_names_general_rules_2026-11-07/pupil_mentions.py`): 1,027 person
   mentions standing in a pupils' list (воспитанницы, в-цы, восп., уч-цы …), 17 seasons, SP 737 / Moscow 290; columns include the marker
   as printed, the current link, and graduates of the same surname that season or later (843 have one). A finding aid: a few rows are
   false hits («еще будучи воспитанницей» mid-sentence). **Follow-up found on the way, not yet chased:** ~150 of the 681 already-linked
   pupil mentions point to an older namesake first listed 3+ seasons earlier, often a man («воспитанница Шишко» → Николай Шишко,
   «Домашева» → Николай Домашевъ, «Рѣпина» → Василій Рѣпинъ) — existing matcher links, to be reviewed after the general rules.
   Next: the other surnames (Егорова 117, Павлова 109, Ширяевъ 92, Ѳедорова 86 …), same method: season/city/ordinal/honorific/role
   evidence, staff-list role check, historical passages listed quickly.
2. ~~**Titles printed with a misprint or with their genre/subtitle attached**~~ — **RULED and APPLIED 2026-11-06.** Every printing
   scan-checked by Claude first (full-res images in the ForUpload PDFs). Rulings (RG, one at a time): «Agence dramatiqus» → work
   «Agence dramatique» (its only printing, a logged misprint; "«Agence dramatique»"); «Бокаччіо» (1901) / «Боккаччіо» (1907), a 1-1 tie
   → work «Боккаччіо», the single к not ruled an error; the 11 subtitle titles → "Bare title, subtitle as genre" (work «Наканунѣ» genre
   «возможный случай», «Chéri!» «vaud.», «Der Star» «ein Wiener Stück» ...); «Colombine»: «Basazzade» (1905, ×4) ruled a print slip for
   «Bajazzade» (1910, ×3), genre «Bajazzade» (RG asked what it is: German clown-play/harlequinade, from «Bajazzo»); «Und Pippa tanzt!»:
   the print's «Glassetten-märchen» ruled a slip for Hauptmann's «Glashüttenmärchen», genre «ein Glashüttenmärchen». Our own slip found
   on the way: raw had «Glasettenmärchen» (one s) where the print has two; raw corrected
   (`docs/eval/raw_fix_pippa_glassetten_2026-11-06.py`, alias row re-keyed). Applied through `WORK_TITLE_FROM_ALIAS` (now title + genre +
   note per printed title); every performance keeps its verbatim title; each work's title_note gives the ruling. The two slips are in
   genuine_print_typos.md. Full rebuild + review chain on a copy, then production (backup `outputs/full_run/db_backup_work_titles_2026-11-06/`):
   research.work 14 rows (these 13 + the «Балетное отдѣленіе» divertissement ruling from a parallel session, carried by the same build),
   research.performance 4 (Pippa ×2, two divertissement items), research.event 1, entities.work 1, raw 2; review tables identical apart
   from the order of spelling variants inside candidate lists; person_link 0 shifts.
3. ~~**`list_number`**~~ — **RULED 2026-11-06: not needed** (RG: "I am ruling that I do not need this, as long as we have the correct
   volume and page number to cite"). Checked the same day: all 23,980 `research.person_appearance` rows carry `season`, `source_file`,
   `scan_page` and `printed_folio` (none null). The number stays in raw only.
4. **Corpus sweep for missed «Заслуженн… артист…» honours** — only seven holders were checked 2026-11-04.
5. **«Щимана»** music credit (1900-01, «Волшебный башмачекъ») — waits on the Шиманъ identity in the person audit.
6. **Gold set out of step** — roster 76.4% because the gold predates later convention rulings (headings with Directorate/Contora prefix,
   tenure notes with the printed brackets, service_class without its stop). Updating `docs/eval/gold/_build_roster.py` would restore it as a
   regression check.

Probably nothing to fix: 1,992 undated cast statements (as printed); craft credits with no person (scenery 45/230, costume 7/28, footwear 3,
headwear 2 — names in no staff list). Parked by RG: Gregorian dates; «Горина», «Брантъ» (uncertain_person_identities.md); ~620 old-cast names.
Housekeeping: 1,552 «*.raw 2.json» sync copies in outputs/full_run/raw (ignored by the pipeline). For Andy at the next publish: rebuild
research_dataset.sqlite (local copy 3 Nov), run `pipeline/merge_datasette_metadata.py` (fixes the event table's broken sort), publish.
