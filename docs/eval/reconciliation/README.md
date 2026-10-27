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
г. Рыбакова.» on the same row (`fix_1890_91_bolshoi_benefit_leak.py`, ledger 1890-91-09, `corrected`; shows in the database
after the next rebuild).

**27 April 1891, time of day (RG: "note the discrepancy").** The review (p. 203) names two debuts that day, Медвѣдевъ and
Карелинъ in «Отелло» and Владимірова in «На бойкомъ мѣстѣ», without a time. The table (p. 25) prints both in the «утро»
half of a divided row (rule across the SP columns, «утро/веч.» labels beside the Большой only). Stored as printed, morning;
ledger 1890-91-10, `yearbook_own`.

**Outcome:** totals and lists: no gaps. Review dates: 8 `yearbook_own` rows. Benefits: 1 `corrected`. 27 April: 1
`yearbook_own`. Nothing open.

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

**Outcome:** 11 ledger rows: 1 `corrected` (29 Jan Маріинскій, `fix_1894_95_mariinsky_swan_lake.py`; shows in the
database after the next rebuild), 6 `yearbook_own` (5 receipts gaps, provisional until RG reads the source, plus the review's
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
