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
