# Reconciling the Repertoire, the season totals and the lists

Three parts of each Yearbook count the same season's events independently:

- **the Repertoire tables**: one cell per event, with works and receipts (`research.event`, `research.performance`);
- **the season totals page ("production stats")**: printed event counts and receipts by category, sometimes by theater
  (`research.season_stat_line`, transcribed in `docs/season_stats/`);
- **the productions lists** (ballet): each production's printed number of performances and its dates
  (`research.production`).

This document sets out how to follow up every disagreement between them so that each one ends with a recorded
outcome. Scan readings made along the way are finding aids, "checked by Claude"; RG reads the source before any claim.

## Tools

```
uv run python pipeline/compare_season_stats.py --db outputs/full_run/imperial_theaters.duckdb --out-dir <scratch>
uv run python pipeline/season_stats_receipt_candidates.py --family-totals <scratch>/family_totals.csv --out <scratch>/candidates.csv
```

`compare_season_stats.py` writes:

| File | One row per | Use |
|---|---|---|
| `city_totals.csv` | season × city | step 1 |
| `family_totals.csv` | season × city × category (× theater where printed) | step 2 |
| `ballet_counts.csv` | season × city: stats, lists, Repertoire ballet counts, verdict | step 4 |
| `ballet_count_dates.csv` | each date where the lists and the Repertoire disagree | step 4 |

`research.season_stat_check` holds the city-level check in the database. Scan reading uses the full-res images in
`pdf/RepertoireTables/ForUpload_<season>_Repertoire.pdf` (spread index = pairNNN/2 − 1, rotate −90); every suspected
digit is confirmed at 3–5× zoom.

## The method: coarse to fine

**1. City totals.** Compare event counts and receipts per city. This only says whether a gap exists. Explain the
event surplus first: the Repertoire includes events with no works (`no_works` in `family_totals.csv`) and events
the stats page may not count (charity, free performances, closures).

**2. Category lines.** Look for gaps that cancel: one category short by roughly what another is over, with the same
number of events. That means the yearbook classed some events differently (usually a mixed bill counted under one
art form, or the reverse). Nothing is misread, so nothing is corrected. Name the specific events behind each offset
and record them.

**3. The residual.** A gap that does not cancel needs the source, in this order:
1. the single-digit-slip candidate finder (`season_stats_receipt_candidates.py`);
2. a read of that theater column on the scan, every figure, logged in the scan-audit ledger
   (`docs/eval/scan_audit/`);
3. RG in the physical volume (or another library's copy), one question at a time, when the scan is unclear.

**4. The lists.** The ballet lists give a third, dated count independent of receipts. A disagreement points to a
specific date (`ballet_count_dates.csv`), so it is the quickest gap to resolve.

**5. Outcome.** Every gap ends with one of:

| Outcome | Meaning |
|---|---|
| `corrected` | a misread in the dataset, fixed by a raw edit (fix script + `_fix_note`) |
| `classification` | the yearbook counts these events under another category; events named |
| `yearbook_own` | figures match the scan; the yearbook disagrees with itself |
| `excluded_by_yearbook` | the stats page leaves out events the Repertoire prints (e.g. 1895-96 SP opening night, 3 Sept) |
| `open` | waiting on RG or another copy |
| `comparison_rule` | not a yearbook gap: the comparison tool classed events differently from the research layer (added 2026-10-27) |

Outcomes go in the ledger `docs/eval/reconciliation/outcome_ledger.csv`, one row per gap: `gap_id` (season-NN),
season, city, category, theater, `events_gap`, `receipts_gap_before_rub` (Repertoire minus printed when the gap was
found), `receipts_gap_now_rub`, outcome, `event_ids` (semicolon-separated), evidence (fix scripts, scan-audit file),
note, checked_by, date. A `corrected` row keeps what is left after the fix; if anything is, that remainder gets its own
row. `yearbook_own` stays provisional until RG reads the source. `docs/eval/known_issues.md` keeps the narrative; the summary table artifact
(claude.ai/artifact/ArLKsN6AHotfFGKQKcd634) can colour by outcome as well as size.

## Worked example: 1893-94 (state 2026-10-27, after the fold-log apply and scan reads)

**Step 1, city totals** (Repertoire minus printed):

| City | Events (Repertoire / printed) | Receipts |
|---|---|---|
| Moscow | 393 / 392 | −0.10 р. |
| SP | 600 / 597 | −163.77 р. |

The Repertoire includes 1 Moscow and 3 SP events with no works.

**Step 2, category lines:**

| City | Category | Events gap | Receipts gap | Reading |
|---|---|---|---|---|
| Moscow | Italian opera | −2 | −9,852.00 | cancels against mixed |
| Moscow | mixed | +2 | +9,851.90 | (ballet+opera 2; Italian opera+French 2 in the Repertoire) |
| SP | Russian drama, Александринскій | −3 | −7,028.37 | cancels against mixed |
| SP | German | −1 | −2,481.75 | cancels against mixed |
| SP | mixed | +4 | +9,476.35 | |
| SP | opera | 0 (119 = 119) | −130.00 | residual |
| all others | | 0 | 0.00 | exact |

Moscow residual after classification: −0.10. SP residual: opera −130.00 plus −33.77 across drama, German and mixed.

**Step 3, residual:** already done for SP: every Маріинскій, Александринскій and Михайловскій figure read on the scan
(15 cells corrected, `fix_1893_94_sp_scan.py`); Moscow tens digits fixed (`fix_1893_94_moscow_tens.py`). The opera
−130.00 survives with every Маріинскій figure matching the scan and no single-slip candidate: provisionally
`yearbook_own`.

**Step 4, lists:** ballet agrees three ways (Moscow 50, SP 47, including mixed bills with ballet and féeries), and all
26 productions' printed totals equal their dated performances.

**Step 2 done, 2026-10-27: the mixed-bill events named.** The stats footnotes date the printed SP mixed bills
(fn. 6-8), so the Repertoire's mixed events split into the yearbook's own mixed bills and the rest:

| City | Date | Theater | Works | Receipts | Reading |
|---|---|---|---|---|---|
| Moscow | 18 Jan 1894 | Большой | Паяцы + Коппелія | 1,659.05 | printed mixed (опера и балетъ) |
| Moscow | 25 Feb 1894 | Большой | Жизель + Паяцы, «Бенефисъ кордебалета» (fn. 13) | 4,367.50 | printed mixed |
| Moscow | 6 Mar 1894 | Большой | Hymne + Otello | 5,152.70 | Italian opera |
| Moscow | 25 Mar 1894 | Большой | Pagliacci + «4-o atto di op. Gli Ugonotti» | 4,699.20 | Italian opera |
| SP | 17 Feb 1894 | Маріинскій | Чайковскій memorial (fn. 7) | 5,702.00 | printed mixed (опера и балетъ) |
| SP | 22 Feb 1894 | Маріинскій | Чайковскій memorial (fn. 7) | 2,663.00 | printed mixed (опера и балетъ) |
| SP | 20 Apr 1894 | Александринскій | Нищіе духомъ + Очарованный лѣсъ, бенефисъ вторыхъ артистовъ (fn. 6) | 4,173.60 | printed mixed (драма и балетъ) |
| SP | 29 Apr 1894 | Михайловскій | Женя + Le petit Hôtel + concert + Коппелія acts 1-2, for Greece (fn. 8) | 2,886.90 | printed mixed (four art forms) |
| SP | 27 Jan 1894 | Александринскій | Дворянское гнѣздо + «Батюшкина дочка, ком.-бал.», Савина benefit | 5,021.55 | Russian drama |
| SP | 10 Feb 1894 | Александринскій | Угасшая искра + «Батюшкина дочка» + Не пойманъ—не воръ + Горбуновъ | 1,577.80 | Russian drama |
| SP | 21 Feb 1894 (morning) | Александринскій | «Батюшкина дочка» + Ворона въ павлиныхъ перьяхъ | 395.70 | Russian drama |
| SP | 6 Mar 1894 | Александринскій | Hymne + Sodom's Ende | 2,481.30 | German |

The six printed mixed bills match the stats exactly (Moscow 6,026.55; SP 15,425.50). The other six are not the yearbook
classing anything differently: `compare_season_stats.py`'s own regex classifier calls them mixed, because it reads «Hymne»
as a French work, a genre-less Latin excerpt («4-o atto di op. …») as French, and «ком.-бал.» as ballet. RG's rulings
(anthem is ceremonial; comedy-ballets are Russian drama with dancers; 2026-10-12) put all six in a single art form, and
`research.performance.discipline` already does. So the yearbook's 1893-94 stats page agrees with those rulings. Moving them
leaves the residuals: Moscow Italian opera −0.10; SP Russian drama −33.32, German −0.45 (−33.77 in all).

**Lesson for the method:** before reading a cancelling step-2 offset as the yearbook's classification, check whether the
comparison tool's classifier is out of step with `research.performance.discipline`.

**Still to do for 1893-94:**
1. ~~name the mixed-bill events~~ (done above);
2. decide whether the −0.10 (Moscow) and −33.77 (SP) are worth one more pass (Moscow pp. 6+ have not had a full scan
   read; see `docs/eval/scan_audit/README.md` for coverage);
3. ~~start the outcome ledger~~: 12 rows, `outcome_ledger.csv` (2026-10-27). Corrected 4 (Moscow tens digits ×2, SP
   Михайловскій shift, Маріинскій kopecks + copied cell); excluded_by_yearbook 2 (the 4 invalids' concert events,
   no concert line that season); yearbook_own 3, provisional (SP opera −130.00, Александринскій drama −33.32, German
   −0.45); open 1 (Moscow Italian opera −0.10, Большой pp. 6+ unread); comparison_rule 2 (the six regex-mixed bills).
   Every event-count gap is explained. Footnote checks: fn. 2 and 10 invalids' performances are separate events already
   counted; fn. 3's two charity operas print no receipts in the Repertoire either.

## 1890-91 (2026-10-27): nothing to reconcile but the ballet lists, and they agree

1890-91 has no season-totals page (the page type starts in 1891-92) and its Repertoire prints no receipts, so steps 1-3
have nothing to compare. No opera or drama productions lists exist for the season either. That leaves step 4.

**Step 4, lists:** `compare_season_stats.py` now also checks seasons that have lists but no stats page (stats columns
blank, verdict "no stats page; list = / ≠ Repertoire"). 1890-91:

| City | List performances (dated) | Repertoire events with ballet | Dates that differ |
|---|---|---|---|
| Moscow | 51 | 51 | 0 |
| SP | 45 | 45 | 0 |

All 22 productions' printed totals equal their dated performances (Moscow 9 productions, 51 = 51; SP 13 productions,
61 = 61; SP's 61 list dates fall on 45 events because some events carried two ballets). No list date is marked
"2 раза" or outside the total.

**Completeness side check.** The season has 133 `not_captured` placeholders (Moscow 52, SP 81). They are 26 whole dates
missing in all five theaters, plus Александринскій 12-14 May 1891, which #87 scan-verified as dark. Every one of the
26 dates falls mid-page, and the printed weekday words run straight across each skip (e.g. «31 Воскр.» then «6 Субб.»
over 1-5 April, the Lenten weekdays), so the yearbook did not print a row for those days: no content is missing.
Five of them (28-29 Aug, 1 and 7 Sept 1890, 1 Mar 1891) were already confirmed on the scan in the 2026-09-22 gap
recovery (#73 addendum). The rest are inferred from the weekday sequence and page position, not each read on the scan.

**Completeness, read on the scan (2026-10-27):** all 26 dates were then read in the date column
(`docs/eval/scan_audit/date_reads_2026-10-27.csv`); each is a skip in the print. So is 4-9 March 1891 (first week of
Lent), which falls at the p. 21/22 break: p. 21's table closes after 3 March and p. 22 opens on 10 March.

**A third source: the season reviews.** With no totals page, the review chapters (SP «All», Moscow ballet) are the only
other dated count. 71 dated statements were matched to the Repertoire: 62 agree, 9 do not. All 9 were read on both
scans; every Repertoire row matches its scan, and every disagreement is a slip in the review's own print, mostly the
wrong month: «30 сентября» for 30 Aug, «11 февраля» for 11 Jan (twice), «7 и 9 марта» for 7 and 9 April («Гибель
Фауста», which the Repertoire prints), plus «3 сентября» for 2 Sept, «12 октября» for 13 Oct, «21 октября» for a first
night on 20 Oct, and «27 декабря» for 26 Dec. Ledger rows 1890-91-01..08, outcome `yearbook_own` (the review disagrees
with the Repertoire; nothing in the dataset changes).

**Lesson for the method:** a review date that disagrees with the Repertoire is more often the review's slip than a
Repertoire misread; read both before treating either as wrong.

**Benefit headings (2026-10-27).** Every benefit the reviews date (29) falls on a Repertoire event carrying that
benefit's heading, and every printed «Бенефисъ / Bénéfice» heading on the 24 table pages (36) is in the database, page by
page. One stored heading is not printed: 11 Dec 1890 Большой «Бенефисъ г. Р.», a truncated copy of the Малый's «Бенефисъ
г. Рыбакова.» on the same row (`fix_1890_91_bolshoi_benefit_leak.py`, ledger 1890-91-09, `corrected`; in the database
since the 2026-10-27 rebuild).

**27 April 1891, time of day (RG: "note the discrepancy").** The review (p. 203) names two debuts that day, Медвѣдевъ and
Карелинъ in «Отелло» and Владимірова in «На бойкомъ мѣстѣ», without a time. The table (p. 25) prints both in the «утро»
half of a divided row (rule across the SP columns, «утро/веч.» labels beside the Большой only). Stored as printed, morning;
ledger 1890-91-10, `yearbook_own`.

**Outcome:** totals and lists: no gaps. Review dates: 8 `yearbook_own` rows. Benefits: 1 `corrected`. 27 April: 1
`yearbook_own`. Nothing open.

## 1891-92 (2026-10-28): every count explained; no receipts anywhere; the lists and both reviews agree

1891-92 is the first season with a totals page (p. 26, `1891-92_ProductionStats.pdf`): counts only, twelve lines, no
receipts, no footnotes. The Repertoire prints no receipts either: the spreads have a date column and five theater
columns and nothing else, and none of the season's 1,438 stored events has a receipts value or receipts text. So
step 3 (receipts residuals) has nothing to compare, and the season reconciles on counts alone.

**Step 1, city totals** (Repertoire / printed): Moscow 364 / 363, SP 575 / 572. The surplus is the four events with no
works, all of them the invalids' concert: Moscow 19 Mar 1892 (Большой); SP dress rehearsal 17 Mar, concert 19 Mar,
repeat 22 Mar (Маріинскій).

**Step 2, category lines.** Every line is exact except one pair:

| City | Line | Printed | Repertoire | Reading |
|---|---|---|---|---|
| SP | drama, Александринскій / Михайловскій | 169 / 64 | 169 / 64 | exact (after the «Псковитянка» ruling, 2026-10-27) |
| SP | opera | 120 | 123 | +3: the three symphony concerts (below) |
| SP | ballet / mixed (opera and ballet) | 41 / 4 | 41 / 4 | exact |
| SP | concerts | 3 | 0 | −3: the three symphony concerts |
| SP | French / German | 138 / 33 | 138 / 33 | exact |
| Moscow | drama / opera / ballet | 191 / 124 / 48 | 191 / 124 / 48 | exact |

The +3 / −3 is three Маріинскій bills headed «Симфоническій концертъ», on 2, 4 and 5 Mar 1892: «Донъ-Жуанъ, музыка къ
драм. поэмѣ», «Финалъ оп. Лорелей», «3-е д. оп. Млада» (2 Mar also opens with «Гимнъ»). The yearbook counts them as its
three concerts; with them moved, opera is 120 = 120. The tool counts them as opera because the research layer makes
the two opera excerpts `item_kind` opera: the «Симфоническій концертъ» heading only decides an event that has no titled
work (`CONCERT_EVENT_RE`), and «Донъ-Жуанъ» is a concert item that doesn't decide the event. All three cells read on
the scan, as stored (ledger 1891-92-01, `classification`).

**Why the symphony concerts and not the invalids' concert.** The SP invalids' events are also three, so they could fill
the «Концертовъ» 3 instead. But then opera would still be +3 with nothing to explain it, and the next season settles the
pattern: in 1892-93 both cities' «Концертовъ» lines (2 and 2) are the symphony concerts, and the invalids' concert (SP 17,
19, 30 Mar 1893; Moscow 19 Mar 1893) is left out of every line. 1893-94 and 1894-95 also leave it out. So the four 1891-92
invalids' events are outside the printed totals (ledger 1891-92-02 SP, 1891-92-03 Moscow, `excluded_by_yearbook`).
Moscow has no «Концертовъ» line at all in 1891-92.

**Stats transcription.** The «Концертовъ» digit noted as smudged reads «3» at 4× (the smudge is a stain beside it).

**Step 4, lists.** Ballet agrees three ways: Moscow stats 48 = lists 48 = Repertoire 48; SP stats 41 + 4 mixed = lists 45
= Repertoire 45. All 24 productions' printed totals equal their dated performances (Moscow 11 productions, 49 = 49, on 48
events; SP 13, 55 = 55, on 45 events). No opera or drama lists exist for the season.

**A third source: the ballet reviews** (Moscow folios 235-241, SP folios 163-179). Every dated performance statement
matches the Repertoire by date, theater and work. (Checked by Claude, by two agents, against the review images; neither
needed a Repertoire scan read, as nothing disagreed.)

| Review | Dated statements | Agree | Counts checked |
|---|---|---|---|
| Moscow | 9 (opening 1 Sept «Кипрская статуя»; 24 Nov «Тщетная предосторожность» revival; Джури 1 and 4 Dec; Мендесъ benefit 29 Dec with «Послѣ свадьбы»; Шашкинъ 2 Jan; Гейтенъ 14 Feb «Дочь фараона»; corps de ballet 15 Feb; closing 29 Apr «Сатанилла») | 9 | 48 ballet events, 11 ballets, «Тщетная предосторожность» 9, «Индія» 8: all agree |
| SP | 8 (opening 1 Sept «Приказъ короля»; Горшенкова 4 Sept; Бріанца 22 Sept; «Царь Кандавлъ» 24 Nov, 1 Dec (Бріанца benefit), 8 Dec (Іогансонъ benefit); «Сильфида» 19 Jan; closing 26 Apr) | 8 | 13 ballets, «Спящая красавица» 12, «Царь Кандавлъ» 10, «Сильфида» with «Поэтъ» 4: all agree; the ballerina split (Бріанца 6, Никитина 4…) can't be checked, the Repertoire prints no casts |

Benefit headings named by the reviews (Мендесъ, Шашкинъ, Гейтенъ, corps de ballet, Бріанца, Іогансонъ) are all on the
matching Repertoire events.

**Outcome** (scan reads: `docs/eval/scan_audit/1891-92_scan_reads.csv`): 3 ledger rows, nothing misread, nothing corrected: 1 `classification` (the symphony concerts), 2
`excluded_by_yearbook` (the invalids' concert, SP 3 and Moscow 1). Lists and reviews: no gaps.

**Symphony concerts as concert items: APPLIED and promoted 2026-10-28** (RG, 2026-10-28: "make items played in
an event headed «Симфоническій концертъ» concert items, like «Гибель Фауста»"; promotion: "merge, apply, commit and push").
`pipeline/build_research_model.py` now has `SYMPHONY_CONCERT_EVENT_RE` and one item_kind rule, placed after the anthem and heading rules: every titled item of an
event whose annotation contains «симфоническій концертъ» is item_kind concert; its art form (discipline, company) is kept,
as with «Гибель Фауста». In the database only the three 1891-92 bills match.

Test: `build_research_model.py` run on two copies of production, one with the patched script and one with the unpatched
script (same research_corrections), and every research table diffed. Changes: research.performance 9 rows, research.event
3 rows, nothing else. The six opera excerpts («Финалъ оп. Лорелей», «3-е д. оп. Млада» × 3) go genre_family opera → concert
(discipline stays opera); the three «Донъ-Жуанъ» items were concert already, only their basis text now names the new rule;
the three events' genre_families lose «opera». `compare_season_stats.py` on the test copy: SP opera 120 = 120, concerts
3 = 3; category lines exact 109 → 111 of 257; city totals and ballet counts unchanged. Promotion: research layer rebuilt on a
copy of production (after the 1909-10 20 Feb fix), every table diffed (research.performance 9, research.event 3, 54 tables
identical), SP 1891-92 opera 120 = 120 and concerts 3 = 3 confirmed on the copy; backup
`outputs/backups/symphony_concerts_1891-92_2026-10-28/`; sqlite rebuilt.

**Found along the way (not chased):**
- 200 `not_captured` placeholders on 40 whole dates (Moscow 80 = 2 × 40, SP 120 = 3 × 40: every date is missing in all
  five theaters at once). **Read on the scan, 2026-10-28** (RG: "do this just in case"): all 15 runs checked in the date
  column (`docs/eval/scan_audit/1891-92_scan_reads.csv`). Each is a skip in the print: the dates on either side sit in
  adjacent cells (e.g. «11 Среда.» → «19 Четвергъ.» over 12-18 Sept 1891; «16 Воскрес.» → «23 Воскр.» over 17-22 Feb 1892;
  «27 Пятница.» → «апрѣль 6 Понед.» over 28 Mar - 5 Apr 1892). 28-29 Aug 1891 fall at the p. 2/3 break (p. 2 closes on
  27 Aug, p. 3 opens on 30 Aug). No content is missing.
- `outputs/reviews/bilingual/1891-92_SP_Ballet.md` has transcription slips against the page images (checked by Claude):
  «П. Пуни» for «Ц. Пуни», «большого» for «большаго», «Шнейггеффера» for «Шнейцгеффера», «Крузетъ» for «Круазетъ»,
  «крестьянкина» for «крестьянина», «колдуны» for «колдуньи». None touches a date or count.

## 1892-93 (2026-10-28): every line exact; four dash cells restored; the lists and all three reviews agree

The stats page (p. 26, `1892-93_ProductionStats.pdf`, left-hand page of the pp. 26-27 spread) prints counts only, 18 lines, no
receipts and no footnotes. The Repertoire prints receipts (967 of 982 performed events), but with no printed totals there is
nothing to compare them with, so the season reconciles on counts.

**Step 1, city totals** (Repertoire / printed): Moscow 376 / 375, SP 606 / 603. The surplus is the invalids' concert, the only
four events with no works: SP Маріинскій dress rehearsal 17 Mar, concert 19 Mar, repeat 30 Mar 1893; Moscow Большой 19 Mar
1893. As in 1891-92, the stats leave it out of every line (ledger 1892-93-01 SP, -02 Moscow, `excluded_by_yearbook`).

**Step 2, category lines:** all 17 exact, venue lines included (SP drama Александринскій 188, Михайловскій 67; opera 120;
ballet 41; mixed opera-and-ballet 11; concerts 2, the two «Гибель Фауста» bills of 15 and 17 Feb; French 141; German 33.
Moscow drama Малый 197, Большой 1; opera 121; ballet 41; mixed drama-and-ballet 1, opera-and-ballet 1; féeries 11; concerts 2,
the two symphony concerts of 7 and 9 Mar).

**Step 4, lists.** Ballet agrees three ways (Moscow stats 41 + 2 mixed + 11 féeries = 54 = lists = Repertoire; SP 41 + 11 mixed
= 52 = lists = Repertoire). All 31 productions' printed totals equal their dated performances (Moscow 16 productions, 57 = 57;
SP 15, 77 = 77).

**Completeness.** 169 `not_captured` placeholders: 15 runs of whole dates missing in every theater (read in the date column
2026-10-28: every one a skip in the print, matching closures: the Воздвиженіе eve, Christmas, Крещенскій сочельникъ, the
first week of Lent, 1 March, Holy Week to Easter, and single Saturdays or Mondays) and four single SP cells that turned out to be printed
dashes, all Saturdays: Маріинскій 21 Nov 1892, Александринскій 19 Dec 1892, 9 and 16 Jan 1893 (read on the scan; the dark
theater beside each is stored as a dash). Appended to raw by `fix_1892_93_dash_cells.py` (at the end of each page's array, no
event_id shifts); rebuilt on a copy, every table diffed (raw/analysis event_entry and research.event: the four placeholders
become no_performance rows; 52 tables identical; 0 person_link shift blocks), promoted 2026-10-28 with backup
`outputs/backups/dash_cells_1892-93_2026-10-28/`; sqlite rebuilt. Ledger 1892-93-03, `corrected`. Also: 23 Oct 1892 (Friday) has no row and no placeholder in any theater;
the scan shows the print skips it at the p. 7/8 break (p. 7 ends on 22 Oct, p. 8 opens on 24 Oct). The placeholder
synthesis doesn't see a skipped date that falls exactly at a page break (noted, not chased).
Scan reads: `docs/eval/scan_audit/1892-93_scan_reads.csv`.

**A third source: the season reviews** (SP opera, 58 pp.; SP ballet, 20 pp.; Moscow ballet, 12 pp.), checked by two agents
against the Repertoire, reading the review images wherever the transcription was unclear (checked by Claude):

| Review | Dated statements | Counts | Disagreements |
|---|---|---|---|
| SP opera | 30 / 30 agree | 10 / 10 (120 opera events; 11 mixed; 2 «Гибель Фауста» concerts; 23 operas; «Русланъ» 15 and «Демонъ» 12 incl. excerpts; «Риголетто» 12, «Онѣгинъ» 11, «Іоланта» 11) | none |
| SP ballet | 14 / 14 | 4 / 4 (41 ballet events, 11 mixed, 15 ballets, 1 new / 3 revived / 11 kept) | none |
| Moscow ballet | 13 / 13 | 18 / 18 (54 events incl. «Кольцо любви»; all 16 per-ballet counts) | none |

Tables: `1892-93_review_sp_opera.csv`, `1892-93_review_ballet.csv`. Print slips found on the way (in
`docs/eval/genuine_print_typos.md`): the Repertoire's «Паяда и рыбакъ» (20 Sept, for «Наяда»), and the SP ballet review's
«съ 1 ноября 1893 г.» for Дель-Эра's hiring (1892). The opera review's «Сезонъ закончился 30-го апрѣля» is the opera season (two
Маріинскій ballet nights follow, 2 and 6 May), and its «возобновлена» for «Карменъ» on 9 Apr 1893 is the new production (six
autumn performances precede it).

**Outcome:** 3 ledger rows: 2 `excluded_by_yearbook` (the invalids' concert), 1 `corrected` (the four dash cells). Nothing
misread; every line, list and review statement agrees.

## Step-2 classifier now uses the research layer (2026-10-27)

RG: "make compare_season_stats.py use research.performance.discipline / is_ceremonial instead of its own regexes."
Each work's family now comes from `discipline` (Russian drama, opera, French drama, ballet, German drama/operetta,
Italian/German opera). The anthem (`is_ceremonial`) and items with no art form are neutral, so they don't make a bill
mixed. Concert items stay concert, «Кольцо любви, феерія» stays féerie, and the guest companies the stats print on their
own line (Режанъ, Тина ди Лоренцо, Лессингъ-театръ, Художественный театръ) count as "other". The old regex classifier is
kept in the script as `classify_work_regex`, for reference. `season_stats_receipt_candidates.py` uses the new one.

All seasons, category lines (venue rows apart):

| | Regex classifier | Research layer |
|---|---|---|
| exact event counts | 73 of 259 | 100 of 257 |
| total event-count gap | 1,069 | 793 |
| total receipts gap | 727,484 р. | 261,075 р. |

City totals and ballet counts don't depend on the classifier and are unchanged. A few lines got worse, and each one
points to a question for the research layer, not a fault in the switch:

- **«Гибель Фауста, драм. легенда» (Berlioz) is counted under concerts.** The research layer calls it opera, but the
  stats page counts it on its «Концертовъ» line. SP 1895-96: 4 events, 8,474.80 р., exactly the printed concerts;
  SP 1896-97: 3 events, 4,850.90 р., exact. SP 1892-93 «Концертовъ» 2 = the two «Симфоническій концертъ + Гибель Фауста»
  bills (15 and 17 Feb 1893). It is also given in 1890-91 and 1906-07. **APPLIED 2026-10-27** (RG: "make «Гибель
  Фауста» item_kind concert"): `CONCERT_KIND_TITLES` in `build_research_model.py`; item_kind concert, company still the
  opera's (14 performances). Now exact: SP 1892-93, 1895-96 and 1896-97 concerts and opera counts. **Exception, Moscow
  1906-07** (3 performances, 6, 9 and 12 Apr 1907): that stats page has no «Концертовъ» line, so the yearbook counted them
  elsewhere, probably as opera (opera now −1 event, −1,308.65 р.; with them +2, +2,338.90). Open, `classification`
  once the line is found.
- **«1-е д. др. Псковитянка» (Александринскій, 30 Sept, 4, 7 and 11 Oct 1891) was labelled opera.** The print says «др.»
  and the bill is a drama-company one (Не все коту масленица, Предложеніе…): Мей's play, not Rimsky-Korsakov's opera.
  **APPLIED 2026-10-27** (RG: "fix … to Russian drama"; "fix both"), with 1890-91's «1-й актъ др. Псковитянка» (5
  events): both linked to «Псковитянка» [др.] in `work_excerpt_links.csv`. 1891-92 SP drama and mixed are now exact.

After both: category lines exact 100 → 108 of 258; summed event gap 793 → 769; summed receipts gap 261,075 → 233,433 р.
Rebuild diff: 23 performances, 23 events, 2 works (excerpt parents), nothing else. Backup
`outputs/backups/faust_pskovityanka_2026-10-27/`; production = tested copy; sqlite rebuilt.
- **Guest companies with no line of their own** (Vienna operetta troupe 1900-02, the German guest seasons, Duse
  1896-97, Sandrock 1901-02, Угетти's Italian opera 1899-02): the stats pages don't say where they counted them. With
  `discipline` they land in German / foreign opera and push those lines over (1900-01 SP German +3, 1901-02 SP German +6).
  Not yet worked out; take it season by season.

Then the same steps season by season. Current gaps per season: the summary table artifact, or `city_totals.csv`.

## 1894-95 (2026-10-27): every count explained; one receipts misread fixed, five small gaps are the yearbook's own

The season runs 30 Aug 1894 - 7 May 1895 with the mourning closure for Alexander III (20 Oct - 31 Dec 1894) printed as a
straight jump in the date column (#84). The stats page is p. 19, on the last spread of the Repertoire scan.

**Step 1, city totals** (Repertoire minus printed):

| City | Events (Repertoire / printed) | Receipts |
|---|---|---|
| Moscow | 238 / 237 | +1,354.50 |
| SP | 365 / 362 | −1,593.60 |

The event surplus is the invalids' concert (Moscow 19 Mar 1895; SP rehearsal 17, concert 19, repeat 21 Mar): no works, no
receipts, and the stats have no «Концертовъ» line (ledger 1894-95-07, -08, `excluded_by_yearbook`).

**Step 2, category lines.** With the research-layer classifier every line has equal counts. Both mixed lines match to the
kopeck: SP «опера и балетъ» 4 = 11,719.75, «русская драма и балетъ» 4 = 9,015.98; Moscow 1 = 578.05 and 2 = 3,061.33. The old
regex classifier's offsets («Grand pas изъ балета Корсаръ» read as French, «Батюшкина дочка, ком.-бал.» as ballet) were the
tool's, not the yearbook's (1894-95-10, `comparison_rule`).

**Footnotes.** Every footnoted count is in the Repertoire: the five «1 безплатный спектакль» are the 9 Feb 1895 free student
matinées (Большой opera, Малый, Маріинскій ballet, Александринскій, Михайловскій French), which print no receipts and are
the season's only events with works but no receipts; 4 Александринскій, 5 Малый, 2 Маріинскій ballet, 2 Moscow ballet and 16
French benefits; the Щепкинъ-fund performances (Большой drama 7 Jan, Александринскій 11 Apr), the Ostrovsky reading room
(Малый 25 Apr), the Stukolkin widow (Маріинскій 5 Feb), the Чайковскій monument (Большой 7 Apr), the German charity
performance (19 Feb) and the second artists' benefit (5 Apr, mixed).

**Step 3, residual.** Every Repertoire figure of the season has now been read on the scan (Александринскій 146 cells added
2026-10-27, none corrected; 4 in the binding fold rest on RG's Binding Fold Log), and the printed lines with gaps were
re-read on p. 19, all as transcribed. What is left is the yearbook disagreeing with itself, provisionally:

| Ledger | Line | Gap (Repertoire − printed) |
|---|---|---|
| 1894-95-01 | Moscow opera | −1,000.00; a second blind read of the Большой column agrees (all 110 legible figures; the 18 Apr fold cell shows three digit tops, so no hidden thousands digit) |
| 1894-95-02 | Moscow Малый drama | +2,354.50; deferred (RG: one day, not needed for her research) |
| 1894-95-03 | SP Маріинскій ballet | ~~−200.00~~ **corrected**: 29 Jan 1895 «Лебединое озеро» prints «3559 р.», stored 3359; found on a second blind read, the first had passed it. Now 0.00 |
| 1894-95-04 | SP French | −1,392.50; deferred (RG: one day, not needed for her research) |
| 1894-95-05 | SP German (Александринскій) | −1.00; two German cells are fold readings, a 1-rouble slip in either would close it (RG: not worth following) |
| 1894-95-06 | SP Александринскій drama | −0.10 |

**Step 4, lists.** Moscow agrees three ways (30). SP: lists = Repertoire 26, stats 28; the two extra are the Александринскій
drama + «Дивертиссементъ» bills of 21 and 29 Sept 1894, which the stats count as drama + ballet and the lists do not list
(1894-95-09, `classification`; found 2026-09-30).

**Outcome:** 11 ledger rows: 1 `corrected` (29 Jan Маріинскій, `fix_1894_95_mariinsky_swan_lake.py`; database
rebuilt 2026-10-27), 6 `yearbook_own` (5 receipts gaps, provisional until RG reads the source, plus the review's
6 Feb slip), 2 `excluded_by_yearbook`, 1 `classification`, 1 `comparison_rule`.

**Lesson for the method:** a single read of a column can pass a misread; when a round gap survives one read, a second blind
read of the column is cheap and found this one. The Маріинскій −200.00 looked like a stats-page slip and was not.

**A third source: the season reviews (2026-10-27).** The four 1894-95 reviews (opera and ballet, both cities; 94 pages)
give 173 dated phrases. Most are staff changes («съ 1-го марта 1895 г.»), deaths, closure-period or other-season dates
(1850 «Катарина», 1859 «Парижскій рынокъ», 1882 «Севильскій цирюльникъ», the 1893-94 Чайковскій memorial). The rest,
about 58 dated performance statements (each date counted once per statement), were matched to the Repertoire by date,
city, theater and work: openings and closings, revivals, first nights, debuts, the Czech guest Флоріанскій's six
nights, the April cast changes. 57 agree. One does not: the Moscow review (p. 315) dates Калмыкова's benefit with the
«Катарина» revival to 6 Feb 1895; the Repertoire (p. 11) prints it in the 5 Feb evening row, read on both scans
(ledger 1894-95-11, `yearbook_own`, the review's slip).

The reviews' counts also agree with the Repertoire: Moscow 27 ballet events plus 3 mixed (2 with opera, 1 with drama); most
performed, Moscow ballet «Конекъ-горбунокъ» 9, «Кипрская статуя» 6, «Катарина» 5; Moscow opera «Жизнь за Царя» and «Фаустъ»
8 each, «Демонъ» 7, «Русалка» and «Донъ Жуанъ» 6 each; SP opera «Дубровскій» 10, «Евгеній Онѣгинъ» 9, «Майская ночь» 8. The
SP opera review's note that operas played only at the Михайловскій until 4 Oct (Маріинскій under repair) matches too.

## 1895-96 (2026-10-28): the opera and ballet company's first week is outside the printed receipts; Moscow re-read blind, no misreads

The stats page is p. 27 (`1895-96_ProductionStats.pdf`): counts and receipts per line, venue lines for drama, opera and SP ballet,
13 footnotes. Coronation season: Moscow's last fortnight (15-26 May 1896) is free performances and a gala.

**Step 1, city totals** (Repertoire / printed): Moscow 336 / 335, −1,230.50 р.; SP 605 / 602, +19,440.08 р.

**Step 2, counts: every line is explained.**
- SP +3 = the invalids' concert (dress rehearsal 12 Mar, concert 14 Mar, repeat 15 Mar 1896, Маріинскій), no works, outside every
  line (1895-96-04, `excluded_by_yearbook`), as in 1891-92 to 1894-95.
- SP Александринскій drama 186 / 187 and mixed 5 / 4: the free pupils' matinée of 3 Jan 1896 at the Александринскій (drama and a
  ballet) is on the drama line; footnote 2 counts four free pupils' performances there and with it the Repertoire has four
  (14 Nov, 6 Dec, 3 Jan, 30 Jan). The four Михайловскій drama-with-ballet events are the mixed line exactly, 2,457.95 р.
  (1895-96-03, `classification`).
- Moscow +1 = the invalids' concert of 10 Mar 1896 (Большой), no works, outside every line (1895-96-06, `excluded_by_yearbook`);
  the invalids' performance footnote 9 counts is the 21 Dec «Спектакль въ пользу инвалидовъ» (opera, 576.85 р.).
- Moscow concerts 1 / 2: footnote 13 «Оба въ пользу фонда … престарѣлыхъ артистовъ» = 25 Feb (4,933.00) and 5 Mar (4,364.80),
  9,297.80 р. = the printed line exactly. The 5 Mar «Музыкально-литературный вечеръ съ живыми картинами» has no works, so the
  comparison tool puts it under no-works; the research layer already calls it a concert (1895-96-05, `comparison_rule`).

**Step 3, receipts.**
- **SP: the opera and ballet company's first week is outside the printed receipts** (1895-96-01, `excluded_by_yearbook`).
  The Маріинскій opera line is +15,535.42 р.; the Маріинскій's six opera events of 31 Aug - 8 Sept 1895 sum to 15,535.32. The
  Маріинскій ballet line is +1,770.45 = 3 Sept «Гарлемскій тюльпанъ» exactly; the Михайловскій opera line is +2,134.20 = 3 Sept
  «Севильскій цирюльникъ» exactly. The stats count all eight events (every count is exact) but leave out their receipts.
  The drama company's receipts for the same days are in (Александринскій +0.01; the Михайловскій drama and mixed lines exact).
  From 10 Sept on, every opera and ballet figure is in. The page doesn't say why.
- SP Маріинскій opera remainder +0.10 (1895-96-02, `yearbook_own`, provisional; the column was read on the scan 2026-10-27).
- Moscow Большой opera +900.00 and Малый drama −2,130.50 (1895-96-07, -08, `yearbook_own`). Both columns were read again
  **blind** (two agents, the scans first, 536 rows): every stored figure equals the blind read, or, for five cells lost in the
  binding fold, RG's reading in the Binding Fold Log. The slip-candidate finder's five +900 candidates (9→0 or a digit swap)
  all read as stored. Two damaged digits checked at 4x: 18 Dec Малый «969» (hooked 6, not 0), 28 Jan Малый kopecks «82»
  (malformed 2). Cells: `docs/eval/scan_audit/1895-96_moscow_blind_reread.csv`.

**Step 4, lists.** SP: list 52 = Repertoire 52, stats 51: the list includes the 3 Jan Александринскій matinée the stats count as
drama (above). Moscow: stats 44 = Repertoire 44, list 43: the list prints «Пробужденіе Флоры» «мая 2, 22», the Repertoire has it
on 3 and 22 May (2 May is «Паяцы» + «Даита», which the list also gives to 2 May; both cells read blind). A date slip in the list
(1895-96-09, `yearbook_own`).

**A third source: the season reviews** (SP ballet, 28 pp.; Moscow ballet, 15 pp.; the season has no opera reviews), checked by
two agents against the Repertoire, reading the review images and Repertoire scan where needed (checked by Claude):

| Review | Dated statements | Counts | Disagreements |
|---|---|---|---|
| SP ballet | 9 / 9 agree (opening 3 Sept «Гарлемскій тюльпанъ»; Рославлева's debut 17 Sept; «Капризы бабочки» 27 Sept; «Талисманъ» 22 Oct; Леньяни's and Ефимовъ's benefits 6 and 10 Dec; Петипа 1-я's benefit 21 Jan; closing 14 Apr) | 7 / 9 (Маріинскій 46 + Михайловскій 1; 16 ballets; 2 new / 3 revived / 11 kept) | «4 смѣшанныхъ» and «51 спектакля»: the review leaves out the 3 Jan Александринскій matinée, as the stats do (1895-96-03); not a slip |
| Moscow ballet | 13 / 15 | 9 / 9 (31 ballet + 13 mixed = 44; 14 ballets; 2 new) | «Пробужденіе Флоры» «3-го и 23-го мая»: 3 May agrees with the Repertoire (so the list's «2» is its slip, 1895-96-09); «23» is the review's slip for 22 (1895-96-10). The other «no» is loose wording («въ маѣ» for a ballet first given 26 Apr) |

Tables: `1895-96_review_sp_ballet.csv`, `1895-96_review_msk_ballet.csv`.

**Drama and French columns** (RG asked for them as a general audit, though their lines are exact): the Александринскій and
Михайловскій were read blind 2026-10-28 (two agents, 515 rows): every legible figure equals the stored value (412), and the 8
cells lost in the binding fold equal RG's Fold Log readings. Every 1895-96 column has now been read.

**Outcome:** 10 ledger rows; nothing misread, nothing corrected.

## 1898-99 (2026-10-28): every column read blind; nine cells corrected; Moscow counts exact; French +6 open

The stats page is p. 42 (`1898-99_ProductionStats.pdf`). From this season footnote 1 says the printed receipts EXCLUDE charity
performances. SP opera is printed on two lines: «Русскихъ оперныхъ» 139 (453,383 р. 28 к.) and «Оперныхъ въ Великомъ посту»
23 (68,905 р. — к.). No season reviews for this season are in the dataset. Productions lists: all 28 printed totals equal their
dated performances (Moscow 11, 75 = 75; SP 17, 67 = 67); ballet stats = lists = Repertoire in Moscow (58); SP list = Repertoire 54.

**Column reads (2026-10-28).** All six columns read blind (four agents, the scans first; 1,198 performed events added to
`docs/eval/scan_audit/receipts_scan_reads_2026-10-27.csv`), every difference checked by Claude at full resolution. Fixed in raw by
`fix_1898_99_scan_reads.py` (rebuilt on a copy twice, every table diffed, promoted; backups
`outputs/backups/scan_reads_1898-99_2026-10-28/`, `outputs/backups/novyi_28dec_1898-99_2026-10-28/`):
- Маріинскій 12 Nov and 7 Jan «3602 р. 50 к.» stored 3502.50 (a damaged 6); 15 Feb «3475 р. 30 к.» stored 2475.30.
- Александринскій 16 Jan, Соловьевъ family charity: no figure printed; the stored 2778.50 was copied from the Михайловскій cell.
- Михайловскій 29 Sep 1010.55 (stored .85), 4 Feb 723.80 (stored .60).
- Новый 6 Dec «Трубадуръ» 1243.13 (stored 1743.13, a damaged 2), 27 Feb 668.31 (stored 663.31).
- Новый 28 Dec morning: «Василиса Мелентьева, др.», stored as «Риголетто, оп.» (works shifted down a row); and «Вій» (stored «Вѣй»)
  on 17, 28, 30 Dec. Found when the Новый drama line came out exactly 272.18 р. short.
Left as stored: Новый 15 Oct «326 р. 24 к.» (second kopeck digit damaged, 1 or 4).

**Lines after the fixes:**

| City | Line | Printed | Repertoire | Receipts gap | Reading |
|---|---|---|---|---|---|
| Moscow | drama Большой / Малый / Новый | 5 / 176 / 134 | 5 / 176 / 134 | 0.00 / −902.78 / 0.00 | Малый: the yearbook's own (1898-99-10) |
| Moscow | opera Большой / Новый | 107 / 52 | 107 / 52 | −30.00 / −794.42 | the yearbook's own (1898-99-09, -11); the Новый prints 2275.26 on both 25 Nov and 2 Dec |
| Moscow | ballet | 58 | 58 | −0.10 | (1898-99-11) |
| SP | drama Alex / Михайловскій | 196 / 70 | 196 / 70 | −27.00 / −146.00 | the yearbook's own (1898-99-03, -04) |
| SP | opera, Lent | 23 | 23 | 0.00 | exact (1 Mar-17 Apr 1899) |
| SP | opera, rest of season | 139 | 139 | −240.05 | the yearbook's own (1898-99-02) |
| SP | ballet | 53 | 53 | 0.00 | exact |
| SP | French | 141 | 147 | +0.45 | count open (1898-99-05) |
| SP | German | 34 | 34 | +100.00 | the yearbook's own (1898-99-06) |
| SP | mixed / concerts | 2 / 2 | (charity) | none printed | 23 Jan РТО bill + 3 Apr Литературный фондъ; the invalids' concert and dress rehearsal (1898-99-07) |

**SP French, 147 events vs 141 printed:** their receipts equal the printed French total within 0.45 р., footnote 7's 20 benefits all
match, there are no French matinées, no Lenten French line, and no other company at the Михайловскій. A count slip in the print
(«141» for 147) is the likeliest reading; for RG (1898-99-05).

**Outcome:** 11 ledger rows: 3 `corrected` (Маріинскій opera; Александринскій charity cell; Новый works and figures), 6
`yearbook_own` (provisional), 1 `classification` (charity mixed and concert lines), 1 `open` (French count).

## 1910-11 (2026-10-27): every figure read, kopeck losses restored; the large gaps are the yearbook's own, the counts are classification

The stats page (p. 58) has no footnotes and prints no receipts for the German (23) and Moscow Art Theatre (45) lines.
Transcription checked against the scan: all nine lines as printed.

**Step 1, city totals** (Repertoire minus printed, after the corrections below):

| City | Events (Repertoire / printed) | Receipts |
|---|---|---|
| Moscow | 474 / 471 | +13,948.31 |
| SP | 660 / 655 | +19,416.40 |

Concerts and notes-only events, which have no line here: Moscow 30 Oct 1910 «Симфоническій концертъ» for the aged artists' refuge
(5,812.33) and the 20 Mar 1911 invalids' concert; SP 11 Sep 1910 free gala for the obstetric congress and the 20 Mar invalids'
concert (ledger 1910-11-10, `excluded_by_yearbook`).

**Step 3 first, because the gaps were large.** Every cell of the Малый, Маріинскій and Александринскій columns (703 cells with
works, pp. 3-56) was read blind by six agents from the scan alone and compared afterwards; I read 13 more cells myself
(scan audit, `receipts_scan_reads_2026-10-27.csv`). **No figure is misread.** The only differences were kopecks the raw parse
loses when the print has a comma or a wrong letter next to the marker: «1542 р, 59 к.», «764 р. 60 к,», «1915 р. 77 р.»,
«1102 р. 69 р.», «616 р. 90 и.». A corpus check of every stored figure against its own printed text found 17 such cells
(14 in 1910-11, 2 in 1909-10, and 1907-08 4 Dec Малый «.575 р. 40 к.», stored as 1 р. 40 к.). All read on the scan and added to
`pipeline/research_corrections/receipts_print_typos.csv` (raw verbatim, #109's rule); research layer rebuilt and promoted
2026-10-27 (17 event values change, nothing else; backup `outputs/backups/receipts_typos_1910-11_2026-10-27/`). Ledger 1910-11-09.
Later the same day the other two columns were read blind too (Михайловскій and Большой, every cell; 431 cells): every figure matches. **All six theater columns of the 1910-11 Repertoire have now been read on the scan** (Новый is dark all season).

**Step 2, category lines:**

| City | Line | Printed | Repertoire | Receipts gap | Reading |
|---|---|---|---|---|---|
| SP | Moscow Art Theatre | 45 | 45 | n/a | the troupe's run, 11 Apr-15 May 1911 at the Михайловскій, is exactly 45 events; the heading is printed once (11 Apr morning). RG 2026-10-27: label all 45 (VISITING_RUNS row); applied, now exact (1910-11-05, `classification`) |
| SP | Russian drama | 272 | 273 | +690.61 | after the Art Theatre run and the two «оп.» cells; both drama columns read in full, every figure as printed; the extra event may be the 11 Feb charity «Поле брани» (no receipts) (1910-11-07, `yearbook_own`, provisional) |
| SP | opera | 167 | 168 | +13,474.09 | two Михайловскій cells print «оп.» inside the drama company's student run (21 Jan «Анжело», 4 Feb «Ромео и Джульетта»); the SP opera list has neither date. RG 2026-10-27: Russian drama (performance_work_overrides.csv); no drama-list check needed (RG) (1910-11-06). Маріинскій alone: 168, every figure as printed (1910-11-03, `yearbook_own`) |
| SP | ballet | 49 | 50 | +5,250.70 | every figure as printed. The ballet line includes the free students' matinée (1908-10 footnotes say so), so one paying event is missing from the printed 49. Probably 9 Jan 1911 «Капризы бабочки» + «Щелкунчикъ» (5,321.75), which leaves −71.05; the next candidates leave 530-670 р. RG: "It's probably Jan 9, but we have no way of confirming this now." (1910-11-04, `yearbook_own`, provisional) |
| SP | French | 99 | 99 | +1.00 | after two kopeck restorations; column read in full, every figure as printed (1910-11-08, `yearbook_own`) |
| Moscow | Russian drama | 240 | 240 | +8,136.00 | every Малый figure as printed. 23 Jan 1911 matinée prints «5092 р. 56 к.»; the same play's matinées on 12 Dec and 9 Jan print 509 р. 56 к., so probably a print slip; with 509.56 the gap is +3,553.00 (1910-11-01, `yearbook_own`) |
| Moscow | opera / ballet / mixed | 180 / 51 / 0 | 178 / 52 / 2 | −0.02 / 0.00 | explained by the opera list (step 4): the opera line counts every event with an opera item, both mixed bills included (180 = 180); the ballet line is the 51 paying evenings; the free 6 Dec ballet matinée is the event left out of 471. RG: keep both bills mixed in the research layer (1910-11-11, `classification`) |

**Step 4, lists.** Moscow: list = Repertoire 52, stats 51 (the free matinée). SP: list 52, Repertoire 50, stats 49. The lists print
«Конекъ-горбунокъ» «февраля 18, 20» and «Спящая красавица» «февраля 17, 19» (totals 4 and 5 count them); the Repertoire prints
18 Feb «Сказаніе о невидимомъ градѣ Китежѣ» and 19 Feb «Кантата. Жизнь за царя» at the Маріинскій. Both read on the scans
(1910-11-12, `yearbook_own`).

**Opera lists (2026-10-27, transcribed blind from the scans).** Moscow (pp. 69-71, 25 entries, 174 dates): every date is a Repertoire opera item; the list prints «Валкирія» with no dates (the Repertoire has it 14, 24, 27 Jan, 8 Feb). Events with an opera item = 180 = the printed line (1910-11-11, -15). SP (pp. 62-64, 28 entries, 165 dates): every date matches; the list prints «Карменъ» with no dates (16, 25, 29 Nov in the Repertoire); list + «Карменъ» = 168 = the Repertoire, stats 167: one fewer, +13,474.09 р., no clean candidate (1910-11-14). List slips: «Демонъ» 7 dates vs «Всего—6 разъ», «Лакмэ» 10 vs 9, «1909 г.» for 1910 twice. The list has neither Михайловскій «оп.» cell (1910-11-06).

**Moscow ballet review (2026-10-27).** Folios 95-98 agree with the Repertoire throughout: monthly counts (6, 7, 5, 11 with 5 matinées, 7, 8, 4, 4 = 52), all ten per-ballet totals, all 12 dated statements. Review = list = Repertoire 52; stats 51 leave out the free 6 Dec matinée, the only candidate: the printed ballet receipts equal the 51 paying evenings to the kopeck, and the opera and drama lines are fully accounted for. RG agreed, 2026-10-27 (1910-11-13).

**Outcome:** 15 ledger rows, nothing open: 2 `corrected` (17 kopeck restorations; Moscow opera now −0.02), 3 `classification` (the Art
Theatre run and the two «оп.» cells, applied on RG's rulings; the Moscow mixed bills, counted as opera by the stats), 9 `yearbook_own`
(provisional until RG reads the source), 1 `excluded_by_yearbook`. RG on SP ballet: probably 9 Jan 1911 (1910-11-04).

**Lesson for the method:** before reading a large residual as a misread, check the stored value against its own printed text
across the corpus. The parse can lose kopecks silently.

**Found along the way:** 211 receipts printed with half-kopecks («82½ к.», 1899-1910, most in 1899-1902; 106.76 р. in all)
are stored with no kopecks at all (TRY_CAST of «82½» fails, and the coalesce turns it into 0), up to 99 kopecks each. #109's note says
the total "stores whole kopecks", which was the intent but is not what happens. Also unparsed: 1909-10 p037 «2841 р. 60 р.»
(the 1909-10 session has it), 1902-03 p021 «218 р. 42 е.».

## 1909-10 (2026-10-27, columns read 2026-10-28): charity events are outside the printed lines; four kopeck losses fixed; every receipts gap explained, two count gaps open

The stats page is p. 58 of the 1909-10 issue (`pdf/Spiski_ProductionStats/1909-10_ProductionStats.pdf`): no venue breakdown,
footnotes per line, and a dated list of jubilees and benefits after each city. German and Art Theatre lines print no receipts.

**Step 1, city totals** (before fixes): Moscow 458 / 351 (+31,747.61 р.), SP 644 / 626 (+16,582.78 р.). Most of both is
**charity**: the twelve «въ пользу» events (Moscow 6, 30,464.75 р.; SP 6, 5,942.75 р.) are in no printed line, neither the
counts nor the receipts (1909-10-05, `excluded_by_yearbook`). With them out Moscow opera is 168 = 168 and Moscow ballet
exact, which settles the rule for this page.

**Step 2, category lines** (charity out, after the fixes below):

| City | Line | Printed | Repertoire | Receipts gap | Reading |
|---|---|---|---|---|---|
| Moscow | ballet | 49 | 49 | 0.00 | exact |
| Moscow | opera | 168 | 168 | −6.00 | every Большой figure as printed (column read 2026-10-28): the stats page's own (1909-10-11) |
| Moscow | drama | **134** | 235 | +1,289.64 | printed count is a slip (clear «134» on the scan); every Малый figure as printed, so the receipts gap is the stats page's own (1909-10-08) |
| SP | ballet | 51 | 51 | 0.00 | exact after 24 Feb fix |
| SP | opera | 157 | 154 + «Миранда» 2 + 18 Dec jubilee bill | +10,000.28 | stats ten-thousands slip, provisional (1909-10-07) |
| SP | drama | 258 | 268 | +712.11 | every figure as printed (receipts: the stats page's own); the 10-event count gap: print slip, «258» for 268 (RG 2026-10-28, provisional) (1909-10-09, `yearbook_own`) |
| SP | French | 100 | 101 | −69.90 | every figure as printed (receipts: the stats page's own); the 1-event count gap: the yearbook's own (RG 2026-10-28, pending further information) (1909-10-10, `yearbook_own`) |
| SP | German | 25 | 25 | (none printed) | exact |
| SP | Moscow Art Theatre | 35 | 35 | (none printed) | exact: Михайловскій 19 Apr - 14 May 1910, printed with no troupe heading; given to the Art Theatre by `VISITING_RUNS` (1909-10-06) |

**«Миранда (послѣдняя борьба)»** (Маріинскій, 23 and 26 Feb 1910, no genre printed) is still without an art form by RG's
ruling of 2026-10-13. The stats page is new evidence: SP opera reaches the printed 157 only if both nights are opera, and
the receipts then differ from the print by 10,000.28 р., a single-digit slip in the printed «531,215 р. 89 к.»
(541,215?). The other reading (charity left in, «Миранда» out) also gives 157, but leaves +8,548.78 р. with no pattern
and contradicts the Moscow lines on the same page. RG, 2026-10-27, after weighing the evidence: classify «Миранда» as opera (`art_form_by_title.csv`; research layer rebuilt and promoted, backup `outputs/backups/miranda_opera_2026-10-27/`); the evidence is recorded in `docs/review_scan_priorities.md` §6, with RGIA Ф. 497 оп. 18 д. 168 л. 62 (10 Sept [1910]), the editor asking for photographs of the scenery of «оперы „Миранда“ Казанли» (the д. 168 summary misreads the name as «Казаченко»).

**Fixes (2026-10-27).** Kopecks lost in four cells, all read on the scan: two extraction misreads in raw
(`fix_1909_10_mariinsky_kopecks.py`: 23 Feb «Миранда» 3358 -> 3358 р. 50 к.; 24 Feb «Эсмеральда» 3479 -> 3479 р. 55 к.)
and two print irregularities in `receipts_print_typos.csv` (12 Oct Большой «3049 р. 78⅞ к.», print damage per RG;
20 Feb Михайловскій «2841 р. 60 р.»). The 1910-11 session's corpus check fixed two more 1909-10 cells the same day
(19 Nov «840 р, 14 к.», 3 Jan «1867 р- 67 к.»). Rebuilt on a copy and diffed every table: only raw.event_entry 2,
analysis.event_entry 2, research.event 4, season_stat_check 2 rows changed. Promoted with backup
`outputs/backups/receipts_1909-10_2026-10-27/`; sqlite rebuilt.

**Footnotes and dated notes.** Every free students' matinée (14 Nov, 6 Dec, 24 Feb) and every footnoted benefit is in the
Repertoire except footnote 3 (SP ballet, 2 benefits) and 5 (Moscow drama, 1), which have no benefit heading there
(1909-10-13, open). Three dated notes disagree with the Repertoire: the second artists' benefit is 19 Dec, not 18
(Repertoire p. 24, scan); Cui's jubilee and the Moscow corps-de-ballet benefit say «января 1909 г.» for 1910
(1909-10-12, `yearbook_own`).

**Step 4, lists.** Moscow list = stats = 49 (the Repertoire's 50th is the 10 Feb charity bill). SP list = stats = 51 with
one date swapped: the stats count the 28 Feb ballet-excerpts evening and give the 18 Dec jubilee bill to opera; the list
has 18 Dec and not 28 Feb (1909-10-14, `classification`).

**Column reads (2026-10-28).** The Малый, Большой, Александринскій and Михайловскій columns were read blind: four agents
transcribed the scans (pp. 2-57, every row, dashes included) before anything was compared with the database. 884 events;
every receipts figure equals the stored value, including the misprints already handled («2466 о. 88 к.», «1425 к. 60 к.»,
«727 р. 70 р.», «603 р· 89 к.»). Two low-confidence digits were checked at zoom and are as printed: 12 Mar Малый «563 р.
72 к.» (stray mark above the 5, no room for a fourth digit) and 17 Mar Alex «1708 р. 88 к.» (broken 0, not 6). So the
receipts gaps on the drama, French and Moscow opera lines are the stats page's own (1909-10-08, -09, -10, -11). The
Маріинскій column was read blind the same day (296 rows, every heading word for word): every figure as stored, so **every
1909-10 column has now been read on the scan**. One extraction
error turned up that is not a figure: 20 Feb Alex «Передъ зарею» is one unsplit cell, stored as a morning
(`fix_1909_10_alex_20feb_session.py`; now unspecified. Rebuilt on a copy, every table diffed, promoted 2026-10-28 with
backup `outputs/backups/alex_20feb_session_2026-10-28/`; sqlite rebuilt). The German line checks out: the
visiting German drama troupe 23 + operetta 1 + German guest 1 = 25.

The two count gaps. SP drama 268 vs 258 (RG 2026-10-28: take it as a print slip in the count, provisional, to be
reconsidered on new evidence): footnote 1 («1 бенефисъ и 4 безплатныхъ спектакля») matches the
Repertoire (free 14 Nov, 6 Dec and 24 Feb at the Alex, 6 Dec «Не въ свои сани» at the Михайловскій), «258» is clear on p. 58,
and no set of 10 events fits +712.11 р. (the smallest SP drama figures are about 660 р.), so a count slip for 268 is the
likeliest reading. SP French 101 vs 100 (RG 2026-10-28: the yearbook's own error, pending any further information): footnote 4 (8 benefits, 2 free) matches, «100» is clear.

**SP ballet benefits (footnote 3, «Въ томъ числѣ 2 бенефиса»): both unaccounted for** (RG 2026-10-28). The blind
Маріинскій read and a search of every raw field find no ballet cell headed «бенефисъ» (the column's only two are opera).
The 24 Jan Трефилова farewell is probably not one: it is printed «Прощальный спектакль», where benefit farewells print
«Прощальный бенефисъ» (Бекефи 1906, Петипа 1907, Гельцеръ 1907; Звягина on this same stats page), and it took 3,592.50 р.,
the ordinary full-house figure, while every ballet benefit 1904-05 to 1910-11 took 3,800-13,600 р. Every other season
1904-05 to 1910-11 has a Маріинскій corps-de-ballet benefit; 1909-10 has none in the Repertoire, a natural candidate for one
of the two. **Follow-up for later:** a source outside the Repertoire (RGIA Ф. 497, newspapers; the yearbook has no SP ballet
review this season) (1909-10-13, open).

**Still to do:** the two SP ballet benefits (above), outside the Repertoire. Settled: «Миранда» (classed as opera) and the Art Theatre run (`VISITING_RUNS`, research layer rebuilt and promoted, backup `outputs/backups/mat_run_1909-10_2026-10-27/`) are settled. The 19 Apr «Утро памяти А. П. Чехова» (no works) is left without a company. The season reviews were not
checked (1909-10 has SP music reviews only).
**Half-kopecks FIXED the same day** (RG: whole kopecks, as #109): research-layer rule, 210 events, +105.98 р.; known_issues.md #161.

## 1907-08 (2026-10-28): every count explained; the season's own play list confirms the Repertoire; two misreads fixed, «Карменъ» back to opera

The stats page (p. 126 of `1907-08_ProductionStats.pdf`) prints eight category lines with receipts, no venue breakdown, and
footnotes counting each line's benefits and free performances. Transcription checked against the scan: all eight lines as
printed. **A new third source:** the same PDF's pp. 127-136 are the yearbook's «Списокъ пьесъ, исполненныхъ на сценахъ
Императорскихъ театровъ въ сезонѣ 1907—1908 гг.»: every play, opera and ballet given, by city and company, with its dates
and «Всего—N разъ». Four agents transcribed it blind (`1907-08_play_list.csv`, 210 entries; every entry's dates equal its
printed total except one). It lets each printed line be checked date by date.

**Step 1, city totals** (Repertoire / printed, after the fixes below): Moscow 434 / 396 events, +96.00 р.; SP 624 / 554,
−4,736.49 р.

**What the stats (and the play list) leave out.** The play list and the stats agree on what they don't count: every charity
bill, the concerts and rentals at the Маріинскій (the Зилоти concerts, the invalids' concert), the 15 Apr fund performance
for the opera's busts and portraits, the unreceipted 22 Oct Moscow staff benefit, and the spring run at the Михайловскій
(38 events, 14 Apr-13 May 1908, no heading, no receipts: Росмерсхольмъ, Брандъ, Вишневый садъ…, probably the Moscow Art
Theatre, not named). None of their dates is in the list. That is Moscow 6 events and SP 71 (ledger 1907-08-05, -07, -08,
`excluded_by_yearbook`). The one charity bill with receipts (Alex 3 Jan, 1,595.75 р.) is out of the receipts too.

**Step 2, category lines** (those events out):

| City | Line | Printed | Repertoire | Receipts gap | Reading |
|---|---|---|---|---|---|
| Moscow | drama | **181** | 213 | +10.00 | «181» is clear on the scan, but the page's own receipts cover all 213 Малый events (10 р. off), fn. 5 matches the full season, and the play list has all 213 (193 days); no subset gives 181. Not a print slip (RG): the count disagrees with the page's own receipts and play list, cause unknown (1907-08-04) |
| Moscow | opera | 167 | 167 | +36.00 | after 16 Sep «Карменъ» (below); 165 paying + 2 free (1907-08-03) |
| Moscow | ballet | 48 | 48 | +50.00 | 47 paying + the free 6 Dec matinée (1907-08-02) |
| SP | drama (Alex) | 217 | 216 | −20.03 | fn. 1 counts 3 free student performances; the Alex has 2. On 14 Nov the free banner spans the Alex column but its cell is undivided, three plays and 726.04 р.: perhaps a free matinée and an evening printed together; stays as printed (1907-08-09, -10) |
| SP | opera | 158 | 158 | −7,112.00 | 156 paying + 2 free; every Маріинскій figure as printed (1907-08-11) |
| SP | ballet / German | 52 / 24 | 52 / 24 | 0.00 / 0.00 | exact |
| SP | French | 103 | 103 | +799.78 | includes 3 free matinées where fn. 4 says 2 (1907-08-12, -13) |

**16 Sep 1907, Большой matinée: «Карменъ, бал.» is the opera (RG 2026-10-28).** #157 (2026-10-22) had followed the Moscow
ballet review, which gives «Жизель» that day. The play list puts the opera «Карменъ» on 16 Sep and has no ballet that day,
and the stats only fit with it as opera: ballet +786.51 → +50.00 р., opera −700.51 → +36.00 р. RG: "Carmen the opera was
performed, and бал. was the slip." `performance_work_overrides.csv` now points the matinée at «Карменъ» [оп.]. Rebuilt on a
copy (1 event, 1 performance, 2 work counts changed), promoted, backup `outputs/backups/carmen_opera_1907_2026-10-28/`
(1907-08-01, `classification`).

**Step 3, every column read blind (2026-10-28).** Five agents transcribed all five theater columns from the full-resolution
scans before anything was compared (`docs/eval/scan_audit/1907-08_scan_reads.csv`, 1,443 rows; Новый is dark all season).
Большой (221 events), Маріинскій (233) and Малый (213): every figure equals the stored value. Two extraction errors, both
fixed in raw, rebuilt on a copy (only these 3 events changed; person_link 0 shift blocks), promoted, backup
`outputs/backups/maly_mikh_1907-08_2026-10-28/`:
- Малый 24 Feb 1908: утро/вечеръ labels swapped (`fix_1907_08_maly_24feb_sessions.py`, 1907-08-06);
- Михайловскій 26 Jan 1908 Andrieu benefit: 2237.50 → «2257 р. 50 к.», a damaged 5 read as 3 (`fix_1907_08_mikh_26jan_receipts.py`, 1907-08-12).

Two digits the scan can't settle, left as stored: Alex 17 Oct «6?7 р. 06 к.» (stored 677; 627 or 647 would widen the
gap) and Михайловскій 12 Jan «1826/1825 р.» (stored 1825). So every receipts gap that remains is the stats page's own,
provisional until RG reads the source.

**Step 4, the lists.** The play list's ballet sections agree with the stats (Moscow 48 dates, SP 52) and with the
Repertoire. The separate ballet productions lists (#145): SP 52 = stats 52 (the Repertoire's other 4 are charity bills);
Moscow 47, which with the 20 Apr evening of single acts (2,469.30 р.; acts are outside the list's totals) is 48 = stats; the
Repertoire's other two are the 10 Nov and 15 Apr charity bills. Its own slips (Repertoire read on the scan): «Китежъ» «февраля 5, 18, 18, 21» where the Repertoire has the
Салина farewell benefit on 15 Feb; Moscow «Дѣльцы» on 18 Jan and «Молодежь» missing 13 Jan; SP «Склепъ» «18» for 28 Dec; four
wrong years (1907-08-14; RG 2026-10-29: all the list's slips).

**A fourth source: the ballet season reviews** (SP ff. 92-105, Moscow ff. 153-160), checked by two agents against the
Repertoire, reading the review images and the Repertoire scans for every disagreement; the main session then re-checked each
disagreement against the blind column read and the play list (`1907-08_review_ballet.csv`, checked by Claude):

| Review | Dated statements | Counts | Disagreements |
|---|---|---|---|
| SP ballet | 20 / 22 agree (1 partial: 18 Nov, one scene of «Тщетная») | 8 / 9 (52 ballet events = stats = both lists; «Раймонда» 38th, «Эсмеральда» 20th since the revival, 3 new ballets, 2 benefits) | 14 Nov «Донъ Кихотъ» called a matinée (it was the evening); «22 балета» = 23 titles less one of two excerpts |
| Moscow ballet | 42 / 51 (1 partial: «6-го декабря 1908 г.» for 1907) | 3 / 3 (47 paying «сверхъ того» the free matinée = 48 = stats; 14 ballets; 2 benefits) | 8 dates, all the review's slips: 27 Sep for 23 Sep; 9 Mar «Дочь фараона», 7 Nov «Спящая», 13 Feb «Волшебное зеркало» for what was given; the corps-de-ballet benefit dated 13 Jan for 2 Dec; 16 Sep «Жизель» (RG: «Карменъ»). Its «Дочь Фараона» with Павлова 2-я «сверхъ того» (f. 160) is probably the 15 Apr charity bill, the only «Дочь фараона» outside the 47; her Moscow roster line is «Въ 1 балетѣ—1» |

Every disputed Repertoire cell matches the blind column read, and the play list agrees with the Repertoire each time.
Three slips in the review transcription, «Аленкій» ×2 (SP f. 104, print «Аленькій»), «Заёль—г-жа Заёль» doubled (f. 94) and
«исполняла была» (Moscow f. 158, print «исполнена была»), were FIXED 2026-10-29 (RG: "fix"; `docs/eval/review_text_corrections.csv`,
commit 0ad4c98). The fix also yields one new review assertion, «Заёль — г-жа Сѣдова» in «Ручей» (30 Sep 1907).

**Outcome:** 16 ledger rows. Corrected 2 (24 Feb sessions, 26 Jan receipts), classification 1 («Карменъ», RG), excluded_by_yearbook
3, yearbook_own 10 (provisional; 2 of them the reviews' slips). Nothing open. The Михайловскій spring run is now labelled a visiting troupe, unnamed (RG 2026-10-28: "We don't need to
name the company"): a `VISITING_RUNS` row, company «visiting Russian drama troupe, St. Petersburg», discipline Russian drama;
38 events, nothing else changed; promoted, backup `outputs/backups/mikh_run_1907-08_2026-10-28/` (ledger 1907-08-08).

**Lesson for the method:** a season's «Списокъ пьесъ» is the best third source when one exists. It is dated, it covers
every company, and it leaves out exactly what the stats leave out.

## 1904-05 (2026-10-28): charity outside the stats, free matinées inside; five misreads fixed; one five-digit «Корсаръ» cell for RG

The stats page (`1904-05_ProductionStats.pdf`, p. 134) prints eight lines with receipts, venue lines for Russian drama
(SP and Moscow) and Moscow opera, and **no footnotes**. The stats PDF has no play list, but the scanned ballet-list pages
show the volume has one: p. 138 opens with the end of the SP opera list (nos. 13-24, dated) and p. 139 runs into
«Французская драма». Only the ballet pages were scanned. The rest would be the best third source for this season, as
it was for 1907-08.

**Step 1, city totals** (Repertoire / printed, after the fixes below): Moscow 528 / 516 events, +1,120.80 р.; SP 565 / 550,
+17,826.28 р.

**What the stats leave out, and what they keep.** Every charity bill is outside the stats: Moscow 10 events, SP 16, none
with printed receipts (1904-05-01, -11). The free school matinées (14 Nov, 6 Dec, 24/23 Feb, every theater) and the free
26 Nov performance for the Георгіевскіе кавалеры are counted. The Александринскій «Спектакль для учащейся молодежи»
matinées print receipts and are counted.

**Step 2, category lines** (charity out):

| City | Line | Printed | Repertoire | Receipts gap | Reading |
|---|---|---|---|---|---|
| Moscow | drama, Малый | 159 | 160 | +1,252.54 | after restoring the dropped 1 Oct cell; unresolved (1904-05-05) |
| Moscow | drama, Новый | 158 | 158 | −132.12 | after the 25-27 Feb fixes (1904-05-08) |
| Moscow | opera, Большой | 123 | 123 | +0.35 | after the 19 Apr banner (1904-05-03, -10) |
| Moscow | opera, Новый | 37 | 38 | 0.00 | one of the 3 free matinées not counted? (1904-05-09) |
| Moscow | ballet | 39 | 39 | +0.03 | |
| SP | drama, Александринскій | 175 | 174 | +2,709.50 | 1904-05-14 |
| SP | drama, Михайловскій | 55 | 55 | 0.00 | after 24 Apr fix (1904-05-12) |
| SP | opera | 134 | 134 | +1,357.41 | 1904-05-15 |
| SP | ballet | 46 | 46 | +13,759.00 | the 28 Dec «Корсаръ» cell (1904-05-13, open) |
| SP | French / German | 115 / 25 | 115 / 25 | −0.12 / +0.48 | half kopecks |

No cancelling offsets: every count gap is charity, free performances or a single unexplained event.

**Step 3, every column read blind (2026-10-28).** Six agents transcribed all six theater columns from the full-resolution
scans before anything was compared (`docs/eval/scan_audit/1904-05_scan_reads.csv`, 1,558 rows). Маріинскій (270 rows) and
Александринскій (264) match the dataset in every figure, Михайловскій (245) in all but one. Five extraction errors,
all checked by Claude on the scan, fixed in raw (`fix_1904_05_scan_reads.py`), rebuilt on a copy (11 events changed, 2 dark
rows added, 1 performance added, nothing else), promoted, backup `outputs/backups/scan_reads_1904-05_2026-10-28/`:
- Малый 1 Oct 1904: «Сенъ-Марсъ, тр.» 651 р. 56 к. had been stored as a dark placeholder (1904-05-04);
- Большой 2 Feb 1905: the Шаляпинъ charity cell prints no receipts; 3028 р. 21 к. was copied from 3 Feb (1904-05-02);
- Новый 30/31 Oct and 6/7 Nov 1904: the 31 Oct and 7 Nov matinées were stored on the dark day before (1904-05-06);
- Новый 25-27 Feb 1905: the three evenings carried the matinées' «403 р. 01 к.»; print 1183.94, 1187.12, 1041.57 (1904-05-07);
- Михайловскій 24 Apr 1905: 480 р. 50 к. → 430 р. 50 к. (1904-05-12).
Also the 19 Apr 1905 Иверская Община banner, which spans the Большой and Малый for the whole day, now covers the Большой
evening «Травіата» (1904-05-03).

**28 Dec 1904, Маріинскій matinée «Корсаръ»: «15291 р. 95 к.»** The print is clear (blind read and 3x zoom agree), but
no other ballet matinée takes more than 2,725 р. With this cell at 1,532.95 р. the SP ballet line would be exact to
the kopeck, but that is not a print slip (RG 2026-10-28): it is several digits away from «15291». No single-digit change
to the printed figure closes the gap either (nearest: 1529.95, −3.00 р.), and the ballet count (46) includes the event.
The +13,759.00 р. stays unexplained, the cell stays as printed. RG read the scan (2026-10-28) as
«15291 р. 95 к.» too. Closed as the yearbook's own (RG 2026-10-28: another copy won't help) (1904-05-13).

**Step 4, the lists.** Moscow: list 41 = Repertoire 41, which includes the 16 Feb and 19 Apr charity bills; the stats' 39
leaves them out. SP: the list prints «На перепутьи» «декабря 12, 17», but 17 Dec is «Валкірія» and the ballet was at the
27 Dec matinée (the list's own «Пробужденіе Флоры» entry says 27). That's a slip in the list (1904-05-17). The SP list
also leaves out two charity bills, «Эсмеральда» (29 Mar) and «Сонъ въ лѣтнюю ночь» (23 Apr), but includes the 6 Apr
one.

**A third source: the ballet season reviews** (SP ff. 105-121, Moscow ff. 193-214), checked 2026-10-28 by two agents reading
the review images and the Repertoire scans; every disagreement then re-read by Claude on both scans
(`1904-05_review_ballet.csv`, 112 statements):

| Review | Dated statements | Counts | Disagreements |
|---|---|---|---|
| SP ballet | 29 / 29 match date and ballet (3 partial: the review or the cell names more works) | 9 of 18 checkable agree | all counts: the review's own («Пахита» 23rd twice; «Конекъ» 55/56/57 skips two Repertoire dates; «Корсаръ» 13th/14th; «Фея куколъ» 3rd/5th) |
| Moscow ballet | 34 / 36 | 15 of 19 checkable agree, incl. «41 балетное представленіе, изъ коихъ одинъ спектакль былъ смѣшанный» = the Repertoire with charity | «24-го апрѣля» Иверская «Волшебное Зеркало» was 19 Apr; «27-го апрѣля» closing «Тщетная» + «Привалъ» was 24 Apr (27 Apr: «Карменъ, оп.»). Both the review's slips; list and Repertoire agree. Counts: «Баядерка» «всего 3» (1 + 1), Гримальди «16» (its breakdown sums to 17), «Эсмеральда» «19-е» |

Every disputed Repertoire cell matches the blind column read. Review transcription slips found here (the flat-topped 3 of
this typeface read as 5) were CORRECTED 2026-10-28 (RG: "Fix the five review-text transcription slips"), each read on the
image first, six rows in `docs/eval/review_text_corrections.csv`: SP p011 «25-го» -> «23-го января», p017 «3) 5-е» ->
«3) 3-е дѣйствіе», p013 «512-го» -> «12-го» (the «5» was an inked spacing slug, not a digit); Moscow p021 «всего 5» and
«Горбункѣ“ 5 раза» -> 3, p017 «Гримальды» -> «Гримальди»; then (RG, same day) p021 «Конекъ-Горбункѣ» -> the printed
«Конькѣ-Горбункѣ».

**Outcome:** 19 ledger rows. Corrected 6 (counting the banner), excluded_by_yearbook 2, yearbook_own 11 (the «Корсаръ» cell
closed by RG; the two reviews, 1904-05-18, -19). Nothing open.

**RG's reading of the provisional rows, 2026-10-29** (one at a time, evidence first): closed as the yearbook's own -- 05 Малый
(1,252.54 = 651.56 for 1 Oct + 600.98; RG reads the damaged 5 Oct digit as 0), 08 Новый drama (−132.12), 10 Большой (+35 к.
opera, +3 к. ballet), 15 SP opera (+1,357.41), 16 French −11 к. / German +50 к. (the earlier "half-kopeck rounding" note was wrong:
the five «½» cells explain only ½ к. and 2 к.; corrected); 17 the SP ballet list's «декабря 17» is its slip for 27. **Held:** 09
Новый opera (+1 event) and 14 Александринскій (−1 event, +2,709.50) wait for the season's drama and opera productions lists
(«Списокъ пьесъ»), which are dated and would show the counted dates; only the ballet pages are scanned so far. Crops for RG:
`docs/eval/scan_audit/1904-05_rg_row05_maly.png`, `1904-05_rg_row17_ballet_list.png`.

## 1896-97 (2026-10-29): ballet agrees four ways; every column read blind; one misread fixed; Михайловскій drama −19,709 is the stats page's

The stats page is p. 27 (`1896-97_ProductionStats.pdf`): venue lines for SP drama, opera and ballet, 10 footnotes, receipts on every
line. Productions lists (ballet) for both cities; ballet reviews for both cities; no opera or drama reviews.

**Ballet: stats, lists, Repertoire and both reviews agree.** Moscow 57 (53 ballet + 4 «опера и балетъ», incl. the 14 Nov free
matinée), SP 53 (Маріинскій 50, Михайловскій 3, incl. the 14 Nov and 6 Dec free matinées and the 16 Apr парадный спектакль). The
ballet lines are exact to the kopeck in both cities (Moscow 60,908.90 and mixed 6,253.23; SP 116,504.29 + 2,255.95). All 29
productions' printed totals equal their dated performances (Moscow 15, 77 dates; SP 14, 65 dates); no list date differs from the
Repertoire. Reviews (`1896-97_review_sp_ballet.csv`, `1896-97_review_msk_ballet.csv`): SP 12 / 12 statements agree (opening 1 Sept,
Михайловскій 4 Sept, «Млада» 25 Sept, Petipa's benefit and the first «Синяя борода» 8 Dec, Леньяни 15 Dec, «Царь Кандавлъ» 9 Feb,
closing 4 May; 50 + 3 = 53, 14 ballets, 1 new, 1 revived); Moscow 15 / 15 (opening 4 Sept, first «Цыганка» 15 Dec, Мендесъ 9 Feb,
Рославлева 16 Feb, Джури and the first «Фея куколъ» 20 Feb, corps de ballet 22 Feb, closing 30 Apr; 53 + 4 = 57, 15 ballets, 2 new,
1 revived), 4 n/a (casts, history).

**Step 1, city totals** (Repertoire / printed): Moscow 420 / 423, +469.80 р.; SP 630 / 621, −10,397.21 р. (after the fix below).
SP +9 = 3 invalids' concert + 2 Barnay + 1 Duse (none on any line) + 3 Александринскій drama (open). Moscow −3 = −4 opera +1 invalids'
concert.

**Step 3, every column read blind** (10 agents, the scans first; `docs/eval/scan_audit/1896-97_scan_reads.csv`, 1,310 rows incl.
dashes): every date and session agrees with the database; 4 figures differ, all damaged glyphs. One misread: 14 Dec 1896 Маріинскій
Barnay «3741 р. — к.», stored 3711 (RG: "It's a 4"; `fix_1896_97_barnay_14dec.py`, rebuilt, diff: that event only, promoted, backup
`outputs/backups/barnay_14dec_1896-97_2026-10-29/`). The other three stay as stored: Александринскій 26 Jan «646 р. 61 к.» (same
damaged 4); Большой 26 Nov «884 р. 46 к.» (the «опера и драма» line is exact with it: 2,643.52 + 884.46 = 3,527.98); Малый 6 Oct
«1238 р. 58 к.» (1208 would widen the Малый gap).

**What is left** (ledger 1896-97-01..13):

| Line | Gap | Reading |
|---|---|---|
| SP Михайловскій drama | 55 = 55, −19,709.00 | yearbook_own (provisional): every cell matches; the kopecks agree (.29), so the roubles of the printed «67,893» look mis-added |
| SP Александринскій drama | +3, −847.15 | **open**: 17 Nov (school fund) and 19 Dec (Дом Милосердія) charity are not in footnote 2; that still leaves +1 |
| Moscow opera | −4, +1,000.00 | yearbook_own (provisional): no missing session on the scan; 121 = 117 + the 4 opera-ballet bills the mixed line also counts |
| Moscow Малый −1,130.00; Italian +599.80; SP French −120.00; Маріинскій opera −19.56; German +1.00 | | yearbook_own (provisional) |

**Fold.** The Binding Fold Log has 13 Repertoire cards (60 cells, the gutter column of each left-hand page) and one review card for
1896-97, none read in the volume (returned loan). The blind read agreed with every stored figure in those cells; two had part of the
figure in the gutter: 29 Dec Большой evening «2628 р.» (kopecks not visible, stored without kopecks) and 18 Jan Михайловскій «2740 р.
50 к.» (first digit cut). Two readings of the same scan are not a reading of the page.

## 1897-98 (2026-10-29): every column read blind; ballet agrees four ways once one kopeck is fixed; four labels for RG

The stats page is p. 27 (`1897-98_ProductionStats.pdf`; it shares the scan with Repertoire p. 26): venue lines for SP drama
and opera, own lines for Réjane, Tina di Lorenzo, the Lessing-Theater and the drama-course students' performance, 16 footnotes.
Productions list (ballet) for SP and Moscow; ballet reviews for both cities. The SP list page (pp. 32-33) also prints the opera
and French drama lists, which are not transcribed: a possible third source for those lines.

**Ballet.** Moscow 51 (48 + 3 opera-ballet bills): stats = list = Repertoire = review. SP 50 (48 Маріинскій + 2 mixed): stats =
Repertoire = review (48 + 2, both mixed bills named); the list has 52 dates: two list dates have no ballet in the Repertoire (25 Oct
«Волшебная флейта», the Маріинскій dark; 3 Nov «Коппелія», which the Repertoire has on 2 Nov), ledger 1897-98-12/13.
`compare_season_stats.py` now applies `LIST_DATE_PRINT_TYPOS` (RG 2026-10-15, the two «Дочь микадо» slips), which it skipped
before. The ballet lines are exact to the kopeck in both cities once 10 Sep 1897 is read «2158 р. 45 к.» (stored 43; SP −0.02),
except Moscow ballet receipts (+2,743.80, already open). Review statements checked: SP opening 3 Sep, «Дочь микадо» first 9 Nov,
Куличевская benefit 16 Nov, «Раймонда» 7 Jan, Кшесинскій benefit 8 Feb, «Капризы бабочки» 19 Apr, «Пахита» 26 Apr, closing 3 May,
mixed 5 May; Moscow opening 3 Sep, «Катарина» 31 Dec, «Звѣзды» 25 Jan, benefits 12-15 Feb (13 Feb with act 2 of «Звѣзды»),
closing 15 Apr: all agree.

**Step 1, city totals** (Repertoire / printed, before the fixes below): Moscow 373 / 374, +3,590.91 р.; SP 649 / 650, −587.97 р.

**Step 2, classification** (no misreads): SP German opera 31 = 28 + the two charity matinées of 15 and 22 Mar (RG #141, event
labels; `compare_season_stats.py` now reads event-level labels for works-less events) + 26 Mar, whose «4-ter Akt aus der Oper Die
Hugenotten» is tagged German drama in the research layer: with it German opera is exact, 152,203.10. French +4 / German −2 (±2,881.52):
the two «Galeotto, dr.» nights (25-26 Mar, inside the German troupe's run) are tagged French, and Réjane's two nights (25 Oct, 26 Oct
morning) sit under the house French company although the stats page gives them their own line. Moved, French (146 / 177,587.01) and
German drama (32 / 58,892.95) are exact. 14 Dec morning (drama-course fund) is the students' line, so Александринскій drama is 187 = 187.
Every no-receipts line is matched (ledger 1897-98-11). Moscow opera +936.51 is the 22 Dec invalids' «Демонъ», counted but its takings
left out of the printed total (`excluded_by_yearbook`).

**Step 3, every column read blind** (7 agents, scans first; `docs/eval/scan_audit/1897-98_scan_reads.csv`, 1,264 rows incl.
dashes): every date and session agrees with the database; every legible receipts figure but one matches; the 18 gutter cells
equal RG's Binding Fold Log readings. The works compared word for word (`docs/eval/scan_audit/1897-98_title_diffs.csv`, 61 rows):
four extraction errors in the 2026-09 hand reconstructions (13 Nov Михайловскій second work dropped; 21 Nov «Германи» for «Гернани»;
26 and 27 Jan Михайловскій bill copied from the days before, print «Margot / Une Innocente»), the 16 Nov «Бенефисъ г-жи
Куличевской.» heading dropped (with it every benefit count matches its footnote: Михайловскій 20, Александринскій 9, Большой 5,
Малый 4, Маріинскій 3 ballet + 1 German opera), five German opera acts held only in the annotation (12, 19, 20, 22, 23 Mar), and
43 letter-level differences for a later title audit. Fixes in `fix_1897_98_scan_reads.py` (six cells); RG read the 10 Sep
digit as 5 (2026-10-29). Applied: rebuilt on a copy (only those cells' rows changed; «Германи» folds into the existing «Гернани»
work through the id crosswalk), production = tested copy, sqlite rebuilt, not republished; backup
`outputs/backups/scan_reads_1897-98_2026-10-29/`. SP ballet is now 48 / 120,913.66 exact; SP city receipts −587.95 (all Александринскій).

**What is left** (ledger 1897-98-01..13):

| Line | Gap | Reading |
|---|---|---|
| Moscow ballet | 48 = 48, +2,743.80 | **open** (RG, since 2026-10-27): every cell read twice, lists and reviews agree; every yearbook-internal test exhausted 2026-10-29 (ledger 1897-98-09); next: the volume, RGIA |
| SP Александринскій drama | 187 = 187, −587.95 | yearbook_own (provisional) |
| SP Маріинскій opera | 122 / 123, receipts exact | yearbook_own (provisional): no missing session on the scan |
| Moscow Малый | 206 / 207, −89.40 | yearbook_own (provisional): no missing session on the scan |
| SP German opera | 31 = 31, 152,203.10 | corrected 2026-10-29 (RG: "Yes, both"): 23 Mar act stored as a work and read «4-ter»; «aus der Oper» titles are opera items (1897-98-01) |
| SP German drama | 32 = 32, 58,892.95 | corrected 2026-10-29 (RG: "Yes, relabel"): «Galeotto» 25-26 Mar = German troupe, research layer (1897-98-02) |
| SP French | 146 = 146, 177,587.01 | corrected 2026-10-29 (RG: "Yes, relabel"): Réjane's 25-26 Oct nights = her troupe, own stats line (1897-98-03) |
| SP ballet list 3 Nov «Коппелія» | | list slip for 2 Nov (RG 2026-10-29), in `LIST_DATE_PRINT_TYPOS` (1897-98-13) |
| SP ballet list 25 Oct «Волшебная флейта» | list 51 vs 50 | list's own: likely a list error (RG 2026-10-29); left as printed (1897-98-12) |

## 1903-04 (2026-10-29): ballet explained in both cities; opera added (RG: dancers appear in operas too); three misreads fixed; two Moscow opera receipts gaps are the stats page's

The stats page is p. 40 (`1903-04_ProductionStats.pdf`): SP drama by venue, opera, ballet, French, German; Moscow drama and
opera by venue, ballet, and an unqualified «Смѣшанныхъ» 1. **No footnotes.** Transcription checked against the scan, and the
page's sums add up. Ballet productions lists for both cities (`raw.production_entry`: Moscow 10 productions, SP 28; every
printed «Всего» equals its dated entries). Ballet reviews for both cities. RG (2026-10-29): every volume also has dated opera
and drama productions lists; only the ballet ones are scanned.

**Step 3 first: three columns read blind (2026-10-29).** Six agents transcribed the Большой, Новый and Маріинскій columns from
the full-resolution scans before anything was compared (`docs/eval/scan_audit/1903-04_scan_reads.csv`, 730 rows). Sums read v.
stored: Большой 417,146.72 v. 417,146.71; Новый 116,799.43 = 116,799.43; Маріинскій 547,272.76 v. 547,262.76. Three extraction
errors, all checked by Claude on the scan, fixed in raw (`fix_1903_04_scan_reads.py`), rebuilt on a copy (4 events changed,
1 dark row added, nothing else in event, performance, work, person or person_appearance), promoted, backup
`outputs/backups/scan_reads_1903-04_2026-10-29/`:
- Маріинскій 19 Apr 1904 «Садко»: 1520.60 -> «1530 р. 60 к.» (blotted 3) (1903-04-06);
- Большой 5 Feb 1904 matinée «Золотая рыбка»: 1705.55 -> «1705 р. 56 к.» (damaged 6) (1903-04-05);
- Новый 17/18 Jan 1904: the 18 Jan matinée «Дѣвичій переполохъ» had been stored on the blank 17 Jan (1903-04-13).
The 32 Большой opera events at exactly 3,028.21 р. (and 3,954.93, 3,037.21) are printed so: subscription houses.

**What the stats leave out, and what they keep.** Out: every charity bill without receipts (SP ballet 5, SP opera 8 Mar;
Moscow 30 Mar at the Большой and the Новый, 4 Feb evening at the Большой), the concerts with no works, and the Moscow
18 Oct benefit mixed bill (6,118.14 р., the only excluded event with receipts). In: the free school matinées (14 Nov, 6 Dec,
4 Feb), and the charity events that print receipts (SP 18 Nov «Мефистофель» 3,600 р.; Moscow 30 Nov «Евгеній Онѣгинъ»
4,993.20 р.).

**Ballet** (stats / list / Repertoire, after the fixes):

| City | Counts | Reading |
|---|---|---|
| SP | 49 / 49 / 54 | the 5 extra are the charity bills of 24 Jan, 21 Feb, 3 Apr, 10 Apr, 24 Apr (no receipts; the 2026-10-09 review check found ballet in each, and the 17 Apr «Балетный дивертиссементъ» was the 4th act of «Конекъ-Горбунокъ» with Гельцеръ). Ballet line exact to the kopeck, 124,010.04 (1903-04-01) |
| Moscow | 34 + 1 / 36 / 37 | the Repertoire's extra over the list is the 30 Mar Иверская charity (1903-04-02); the list's extra over the stats is the 18 Oct benefit (1903-04-03); «Смѣшанныхъ» 1 = the 24 Oct Tchaikovsky memorial to the kopeck (1903-04-04). Ballet line exact, 78,160.80 (1903-04-05) |

Title by title, list and Repertoire agree except 30 Nov SP: the list and the review give «Волшебная флейта», the Repertoire cell
only «Фея куколъ» + Act 2 of «Фіаметта» (1903-04-14). RG (2026-10-29): two sources agree, so «Волшебная флейта» [бал.] is now supplied
in the research layer (`supplied_performances.csv`, which gained `adds_to_bill` and `work_genre`); raw keeps the printed cell. Moscow «Пригалъ кавалеріи» (14 Nov) and «Ваядерка» (25 Jan)
are print slips, stored as printed, and now aliased to «Привалъ кавалеріи» and «Баядерка» (RG 2026-10-29; 1903-04-17). The alias also caught SP 4 Sep 1905 «Ваядерка», printed «Баядерка»: a misread, fixed in raw (`fix_1905_06_bayaderka_title.py`).

**Opera** (stats / Repertoire, charity without receipts out):

| City | Line | Counts | Receipts gap | Reading |
|---|---|---|---|---|
| SP | opera | 139 / 140 | 0.00 | after «Садко»; one event without receipts not counted: a free matinée (6 Dec, 4 Feb) or the 18 Nov charity. **Open, held for the SP opera productions list** (1903-04-07, -08) |
| Moscow | Большой | 135 / 135 | −11,700.00 | every Большой figure as printed; kopecks agree; the stats page's own, provisional (1903-04-09, -10) |
| Moscow | Новый | 41 / 41 | +825.81 | exactly 26 Oct «Галька, оп.» «825 р. 81 к.»: the printed total seems to leave out one cell, provisional (1903-04-11, -12) |

**Dancers in operas.** The research layer marks no 1903-04 opera as including dance (only SP 22 Feb «чтеніе, пляска»). The
2026-10-09 opera-review checks (`docs/eval/review_check_1903-04_sp/`, `_moscow/`) name dancers in «Ромео и Джульетта», «Пиковая
дама», «Фераморсъ», «Русалка» and others at the Маріинскій, and «Добрыня Никитичъ», «Наль и Дамаянти», «Искатели жемчуга» in
Moscow. Not applied: RG (2026-10-29) wants these from a high-quality scan of the Princeton hard copy, not the HathiTrust
download; the pages to read are listed in `docs/yearbook_volume_requests.md` (1903-04, Vol. 14). The rosters only count operas
(«въ 11 операхъ»), never name them, and the 1903-04 ballet reviews say nothing about operas.

**The ballet season reviews** (two agents, the review images and the Repertoire scans for every disagreement;
`1903-04_review_sp_ballet.csv`, `1903-04_review_msk_ballet.csv`, checked by Claude):

| Review | Statements | Disagreements |
|---|---|---|
| SP (ff. 107-121) | 64: 41 agree, 4 partial, 3 no, 16 n/a | season total «35 (одинъ изъ нихъ смѣшанный)» fits no count; «25-го ноября» for 23 Nov; «Волшебное зеркало» «три раза» (2); closing 2 May (6 May). All the review's (1903-04-15) |
| Moscow (ff. 179-204) | 30: 24 agree, 2 partial, 4 no | «34 … изъ нихъ 1 смѣшанный» (stats 34 + 1); 21 Sep, 25 Sep, 14 Jan, 17 Jan misdated. All the review's (1903-04-16) |

Review transcription slip, CORRECTED 2026-10-29 (RG: "Yes, correct it"): SP f. 107 «5-го сентября» is «3-го» on the image
(`docs/eval/review_text_corrections.csv`); its three cast assertions moved from 5 to 3 Sep. The review rebuild also re-linked
414 `research.review_credit` rows that pointed at a mention in another block (production's credits were stale, off by one
from mention 13425) and brought the 1907-08 «Аленькій цвѣточекъ» credits in line with the corrected text. Backup
`outputs/backups/review_3sep_1903-04_2026-10-29/`.

**Noticed, not chased** (drama): SP Александринскій +6 events / −10.40 р., Михайловскій +1 / +329.00; Moscow Малый +1 / −2.03,
Новый drama +18.00. The Малый, Александринскій and Михайловскій columns were not read.

**Outcome:** 17 ledger rows. Corrected 3, classification 1, comparison_rule 1 (the two aliases), excluded_by_yearbook 6, yearbook_own 5,
open 1 (SP opera +1, held for the opera list).

**RG's reading, 2026-10-29** (one at a time, evidence first): 10 Большой opera «135 (341,255 р. 05 к.)» and 12 Новый opera «41 (41,889 р.
32 к.)» / «Галька» «825 р. 81 к.» read as transcribed, closed as the stats page's own (crops `docs/eval/scan_audit/1903-04_rg_row10_moscow_opera.png`,
`1903-04_rg_row12_novy_26oct.png`); 14 «Волшебная флейта» on 30 Nov supplied in the research layer (two sources agree; crops
`1903-04_rg_row14_*.png`); 15, 16 the reviews' own slips, "they can be considered review slips", noted in `docs/eval/genuine_print_typos.md`.
Nothing provisional is left; only 08 (SP opera +1) is open.

## 1906-07 (2026-10-29): every column read blind; the Михайловскій surplus is the Moscow Art Theatre; «Карменъ» is the opera (RG), Moscow counts exact; two misreads fixed

The stats page (`1906-07_ProductionStats.pdf`, page number too faint) prints SP drama by venue, opera, ballet, French, German;
Moscow drama by venue, opera, ballet. Counts and receipts, **no footnotes**, no concert or mixed line. Transcription checked
against the scan (2026-10-29): all 13 lines as printed. The SP drama subtotal prints 81.00 р. more than its lines (1906-07-16).
No ballet productions list for the season. Ballet reviews exist for both cities (not yet checked).

**Step 1, city totals** (Repertoire / printed): Moscow 619 / 610, +7,872.31 р.; SP 609 / 575, +710.92 р.

**What the stats leave out** (`excluded_by_yearbook`): the Moscow Art Theatre's visit to the Михайловскій, 23 Apr-17 May
1907, 24 events with no receipts, headed «Спектакли Московскаго Художественнаго Театра» on its first day only (1906-07-09);
every charity bill with no receipts (Moscow 7, SP 9) and the Moscow 24 Feb staff benefit, which prints none (-04, -10). The
free school matinées (14 Nov, 6 Dec, 28 Feb) are counted in Moscow; in SP all but two fit (-13). The one charity bill with
receipts, the German 10 Apr (2,809.80), is in the German line.

**Step 2, category lines** (those events out):

| City | Line | Printed | Repertoire | Receipts gap | Reading |
|---|---|---|---|---|---|
| Moscow | ballet | 49 | 49 (46 paying + 3 free) | +3,839.50 | after 28 Jan «Карменъ, бал.» = the opera (-01, RG) |
| Moscow | opera | 164 | 164 | +3,309.91 | with «Карменъ»; includes the 3 «Гибель Фауста» concerts (no concert line, -03) |
| Moscow | Большой together | 213 | 213 | +7,149.41 | every figure as printed; the stats page's own, provisional (-02) |
| Moscow | Малый | 217 | 217 | +594.90 | every figure as printed (-05) |
| Moscow | Новый | 180 | 181 | +128.00 | every figure as printed (-06) |
| SP | Александринскій | 197 | 196 | +2,332.23 | after restoring 19 Nov 625.75, dropped in extraction (-11) |
| SP | Михайловскій drama | 25 | 25 | 0.00 | exact once the MXAT run is out |
| SP | Маріинскій drama | 1 | 1 | 0.00 | Стрѣльская benefit, 27 Jan |
| SP | opera | 159 | 159 | +133.10 | (-12) |
| SP | ballet | 53 | 54 | 0.00 | 52 paying exact; one of the two free matinées not counted (-13) |
| SP | French | 115 | 115 | −1,128.60 | 6 Feb «11?7 р. 08 к.» stored with none; 1127.08 → −1.52 (-14, RG) |
| SP | German | 25 | 25 | −0.06 | 12 half-kopecks (#161) (-15) |

**Step 3, every column read blind (2026-10-29).** Six agents transcribed all six theater columns from the full-resolution
images in the Repertoire PDF before anything was compared (`docs/eval/scan_audit/1906-07_scan_reads.csv`, 1,713 rows,
every date × session incl. dashes). Малый (278) matches to the kopeck; Новый, Маріинскій, Большой, Михайловскій and
Александринскій match except these, each read again by Claude on the scan:
- Александринскій 19 Nov 1906 matinée «625 р. 75 к.» stored with no receipts: **extraction error, fixed**;
- Большой 30 Dec 1906 «Аида» printed in the утро half (вечеръ is a dash), stored as evening: **extraction error, fixed**;
- Большой 28 Jan 1907 evening «2321 р. 5? к.»: the 5 is the tens digit, stored 2321.05; RG reads «55» from the crop, to check on a HathiTrust copy before changing it (-08);
- Михайловскій 6 Feb «11?7 р. 08 к.» (-14; RG: left unstored, to read on a HathiTrust copy with 28 Jan); damaged digits left as stored: Новый 9 Feb «36? р.», Маріинскій 4 Dec «35?5 р.»,
  Александринскій 2 Mar «180? р.», Михайловскій 4 Mar «128? р.» and 22 Mar «2? к.». None of these closes a gap.

**Applied 2026-10-29** (RG: "Yes, apply both"; «Карменъ»: "a genre misprint just like the other one"): `fix_1906_07_scan_reads.py` (raw: 19 Nov receipts; 30 Dec session labels swapped, ids unchanged) and a `performance_work_overrides.csv` row (28 Jan «Карменъ» -> the opera; raw keeps «бал.»). Rebuilt on a copy (`outputs/rebuild_1906-07_2026-10-29/`): raw/analysis event_entry 3 rows, research.event 4, performance 1, work 2 (the two «Карменъ» counts; the ballet one now 0), season_stat_check 1; nothing else; validation errors the same 265 pages; person_link 0 shift blocks. Promoted (DB, parsed, the two raw files), sqlite rebuilt, not republished; backup `outputs/backups/scan_reads_1906-07_2026-10-29/`. The scans p000, p002 and p004 have duplicated strips (a scanner artefact) on dark days in the
Михайловскій; no content is affected. A stray copy `outputs/full_run/raw/repertoire_1906-07_p014.raw 2.json` sits beside the
real raw file (a sync duplicate?), left untouched.

**Outcome so far:** 16 ledger rows. corrected 1 (30 Dec; the 19 Nov fix is inside -11), excluded_by_yearbook 3, classification 2 («Карменъ», «Гибель Фауста»),
comparison_rule 1, yearbook_own 6 (provisional), open 3 (6 Feb French figure, 28 Jan kopecks for HathiTrust, the SP free-matinée count). Not yet done: ballet reviews,
the MXAT company label in the research layer, titles audit.

## 1901-02 (2026-10-29): eight copied charity figures; every count explained once they go; four damaged digits for RG

The stats page is p. 40 (`1901-02_ProductionStats.pdf`): SP drama by venue, opera, ballet, French, German; Moscow drama, opera
and ballet by venue, «Смѣшанныхъ» 1 (Большой). No footnotes. Ballet productions lists for both cities.

**Step 1, city totals** (before any fix): SP 638 / 604, +11,990.79 р.; Moscow 539 / 534, −1,869.41 р.

**Copied figures (the bulk of the SP gap).** Eight charity cells that print no receipts hold the figure of the neighbouring
column on the same row: Александринскій 26 Jan 1902 has the Михайловскій's 2006 р. (Rousselle benefit), and the Маріинскій
7, 8, 10, 11, 12, 13 and 14 Mar 1902 (Vienna operetta, Japanese troupe, Glinka concert, Любимовъ's opera) have the
Александринскій German troupe's. 12,373.14 р.; it is exactly the SP total of "charity with receipts" in the data. Checked by
Claude on the scan and by the blind read. **Applied 2026-10-29** (RG: "Yes, apply them"): `fix_1901_02_scan_reads.py` (receipts -> none; Новый 6 Nov below), rebuilt on a copy (`outputs/rebuild_1901-02_2026-10-29/`): raw/analysis event_entry 9, research.event 9, season_stat_check 2, nothing else in 56 tables; validation errors the same; person_link 0 shift blocks. Promoted (DB, parsed, the three raw pages), sqlite rebuilt, not republished; backup `outputs/backups/scan_reads_1901-02_2026-10-29/`. City totals now SP −382.35 р., Moscow −1,869.36 р. (ledger 1901-02-01).

**Every column read blind** (8 agents, scans first; `docs/eval/scan_audit/1901-02_scan_reads.csv`, 1,404 rows incl. dashes).
Every printed session matches a stored event. Every legible figure equals the stored one except the 8 copies and Новый 6 Nov
«400 р. 88 к.» (stored 83; fixed by the same script). Four damaged digits, each of which closes a gap (crops `1901-02_rg_*.png`):

| Cell | Print | Stored | Read | Closes |
|---|---|---|---|---|
| Большой 30 Dec matinée «Князь Игорь» | «1?31 р. 35 к.» | none | 1831.35 (low) | Большой opera −1,839.36 → −8.01 |
| Малый 24 Jan «Волки и овцы» | «9?5 р. 81 к.» | 955.81 | 985.81 (low) | Малый −30.00 → 0 |
| Маріинскій 14 Dec «Царская невѣста» | «3?33 р. 50 к.» | 3133.50 | 3433.50 (medium) | with the next, SP opera −299.91 → 0 |
| Маріинскій 24 Jan «Евгеній Онѣгинъ» | «35?0 р. 5? к.» | 3590.59 | 3590.50 (medium) | |

**What the stats count.** In: paying events and the free school matinées (14 Nov, 6 Dec, 20 Feb), and the 26 Nov free
performance for the Георгиевские кавалеры. Out: charity without receipts (the Малый 29 Sep figure is printed in parentheses,
«(3058 р. 08 к.)», and stored verbatim with no figure), and the guest companies, none of which print receipts here (Réjane,
Sandrock in both cities, Угетти's Italian opera, the Vienna operetta and Japanese troupes, the Moscow Art Theatre).
14 Nov at the Александринскій and Михайловскій (two works, one figure, no rule or labels) stays one event each (RG
2026-10-12); the stats count each as a free matinée plus a paid evening, which makes the Михайловскій drama 68 and French
130 lines match (1901-02-08).

**Lines, with the fix script and the four readings above:**

| Line | Counts | Receipts | Reading |
|---|---|---|---|
| SP ballet | 51 = 51 = list 51 | exact | |
| SP opera | 138 = 138 | exact | with 14 Dec + 24 Jan readings (open, RG) |
| SP German | 24 = 24 | exact | with the four ½-kopeck cells (#161 rule; 1901-02-12) |
| SP Александринскій drama | 192 / 193 | exact | one charity event without receipts seems counted (open, 1901-02-09) |
| SP Михайловскій drama | 68 = 68 | +45.00 | yearbook_own, provisional (every figure as stored) |
| SP French | 130 = 130 | −127.27 | yearbook_own, provisional (−127.42 less 30 half-kopecks) |
| Moscow ballet | 49 = 49, list 46 | exact | list prints 12 + 19 Dec «Коппелія» and 21 Feb acts below «Всего» (1901-02-15) |
| Moscow Большой opera | 132 / 133 | −8.01 | 30 Dec reading; one event short (2 Feb Pushkin charity opera acts?), open |
| Moscow Малый | 171 = 171 | exact | with 24 Jan reading |
| Moscow Новый drama | 147 = 147 | exact | 144 + the three drama/ballet bills (classification) + 6 Nov fix |
| Moscow Новый opera, Большой drama, «Смѣшанныхъ» | exact | exact | «Смѣшанныхъ» = 20 Apr benefit |

**Moscow ballet list, one date.** «Лебединое озеро … сентября 16, 21»: the Repertoire has «Русланъ и Людмила» on 21 Sep and
the ballet on 21 Oct, and the list has no October date for it. Probably a list slip (1901-02-14, for RG). The list page (p. 54)
also prints the end of the Moscow **opera** productions list («Фаустъ», «Фра-Діаволо»): the opera list exists.

**The ballet season reviews** (RG: "then cross check with the season reviews"; two agents, the review images and the Repertoire scans
for every disagreement; `1901-02_review_sp_ballet.csv` (41 statements: 31 agree, 2 partial, 4 no, 4 n/a) and `1901-02_review_msk_ballet.csv`
(27: 17, 2, 1, 7); checked by Claude). **No Repertoire error.** Three transcription slips in `raw.review_block`, read on the images:
SP p002 and Moscow p008 «25-го сентября» are «23-го» (the old-style 3), Moscow p029 «также балерина» is «таже» (1901-02-16). **Corrected 2026-10-29** (RG: "Yes, correct them"):
`docs/eval/review_text_corrections.csv`, review chain rebuilt on a copy (mentions, reviews, assertions, credits) and promoted: the SP
23 Sep «Корсаръ» paragraph's 9 cast assertions and 5 credits moved from 25 to 23 Sep; two Moscow p029 work mentions shifted one character;
nothing else apart from mention-id renumbering and candidate-list order. Backup `outputs/backups/review_text_1901-02_2026-10-29/`.
The review's own slips (1901-02-17): SP «во второй разъ» for third performances (4 and 11 Nov), «2-го января 1903», Сѣдова's Медора
«18-го февраля» (23 Feb), 24 Feb «Очарованный Лѣсъ» for «Оживленный садъ»; Moscow 24 Feb «2 дѣйствія» v. «2-е д.» in the Repertoire and
list. Neither review mentions «Лебединое озеро» on 21 Sep or 21 Oct.

**Outcome:** 17 ledger rows. Corrected 3 (the fix script, the review transcription slips), open 6 (the four damaged digits in three rows, the
list date, the two count gaps), classification 3, yearbook_own 3 (2 provisional), comparison_rule 1, excluded_by_yearbook 1. Not yet done: titles audit.
