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
  five theaters at once). Same pattern as 1890-91's print skips; with every count exact, they are presumptively the
  yearbook's own skips. Not read in the date column (1890-91 had that done, `date_reads_2026-10-27.csv`).
- `outputs/reviews/bilingual/1891-92_SP_Ballet.md` has transcription slips against the page images (checked by Claude):
  «П. Пуни» for «Ц. Пуни», «большого» for «большаго», «Шнейггеффера» for «Шнейцгеффера», «Крузетъ» for «Круазетъ»,
  «крестьянкина» for «крестьянина», «колдуны» for «колдуньи». None touches a date or count.

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
| SP | French | 100 | 101 | −69.90 | every figure as printed (receipts: the stats page's own); the 1-event count gap is open (1909-10-10) |
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
likeliest reading. SP French 101 vs 100 (still open): footnote 4 (8 benefits, 2 free) matches, «100» is clear.

**SP ballet benefits (footnote 3, «Въ томъ числѣ 2 бенефиса»): both unaccounted for** (RG 2026-10-28). The blind
Маріинскій read and a search of every raw field find no ballet cell headed «бенефисъ» (the column's only two are opera).
The 24 Jan Трефилова farewell is probably not one: it is printed «Прощальный спектакль», where benefit farewells print
«Прощальный бенефисъ» (Бекефи 1906, Петипа 1907, Гельцеръ 1907; Звягина on this same stats page), and it took 3,592.50 р.,
the ordinary full-house figure, while every ballet benefit 1904-05 to 1910-11 took 3,800-13,600 р. Every other season
1904-05 to 1910-11 has a Маріинскій corps-de-ballet benefit; 1909-10 has none in the Repertoire, a natural candidate for one
of the two. **Follow-up for later:** a source outside the Repertoire (RGIA Ф. 497, newspapers; the yearbook has no SP ballet
review this season) (1909-10-13, open).

**Still to do:** the SP French count gap (RG); «Миранда» (classed as opera) and the Art Theatre run (`VISITING_RUNS`, research layer rebuilt and promoted, backup `outputs/backups/mat_run_1909-10_2026-10-27/`) are settled. The 19 Apr «Утро памяти А. П. Чехова» (no works) is left without a company. The season reviews were not
checked (1909-10 has SP music reviews only).
**Half-kopecks FIXED the same day** (RG: whole kopecks, as #109): research-layer rule, 210 events, +105.98 р.; known_issues.md #161.
