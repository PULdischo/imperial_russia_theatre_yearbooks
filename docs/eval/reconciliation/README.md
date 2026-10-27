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

**Step 2, category lines:**

| City | Line | Printed | Repertoire | Receipts gap | Reading |
|---|---|---|---|---|---|
| SP | Moscow Art Theatre | 45 | 1 | n/a | the troupe's run, 11 Apr-15 May 1911 at the Михайловскій, is exactly 45 events; the heading is printed once (11 Apr morning), so the research layer gives the other 44 to Petersburg drama (1910-11-05, open: RG to decide a label for the run) |
| SP | Russian drama | 272 | 315 | −336.69 | minus the 44 above, plus the two «оп.» cells below: 273, +690.61; Михайловскій drama not read in full (1910-11-07, open) |
| SP | opera | 167 | 170 | +14,501.39 | two Михайловскій cells print «оп.» inside the drama company's student run (21 Jan «Анжело», 4 Feb «Ромео и Джульетта», 616.90 = that run's usual figure): probably the yearbook's slip (1910-11-06, open). Маріинскій alone: 168 / +13,474.09, every figure as printed (1910-11-03, `yearbook_own`) |
| SP | ballet | 49 | 50 | +5,250.70 | every figure as printed; no 1-3 events sum to it (1910-11-04, `yearbook_own`) |
| SP | French | 99 | 99 | +1.00 | after two kopeck restorations; column not read (1910-11-08) |
| Moscow | Russian drama | 240 | 240 | +8,136.00 | every Малый figure as printed. 23 Jan 1911 matinée prints «5092 р. 56 к.»; the same play's matinées on 12 Dec and 9 Jan print 509 р. 56 к., so probably a print slip; with 509.56 the gap is +3,553.00 (1910-11-01, `yearbook_own`) |
| Moscow | opera / ballet / mixed | 180 / 51 / 0 | 178 / 52 / 2 | −0.02 / 0.00 | printed ballet 51 = the 51 receipted ballet events to the kopeck; the 52nd is the 6 Dec free matinée. Repertoire mixed: 30 Dec «Риголетто» + «Балетный дивертиссментъ» (charity) and 19 Feb Малый emancipation-jubilee programme. 472 vs 471 events; no footnotes to say how they were counted (1910-11-11, open) |

**Step 4, lists.** Moscow: list = Repertoire 52, stats 51 (the free matinée). SP: list 52, Repertoire 50, stats 49. The lists print
«Конекъ-горбунокъ» «февраля 18, 20» and «Спящая красавица» «февраля 17, 19» (totals 4 and 5 count them); the Repertoire prints
18 Feb «Сказаніе о невидимомъ градѣ Китежѣ» and 19 Feb «Кантата. Жизнь за царя» at the Маріинскій. Both read on the scans
(1910-11-12, `yearbook_own`).

**Outcome:** 12 ledger rows: 2 `corrected` (17 kopeck restorations; Moscow opera now −0.02), 4 `yearbook_own` (provisional until
RG reads the source), 1 `excluded_by_yearbook`, 5 `open` (3 wait on RG's decisions: the Art Theatre run, the two «оп.» cells,
and how the Moscow mixed bills were counted).

**Lesson for the method:** before reading a large residual as a misread, check the stored value against its own printed text
across the corpus. The parse can lose kopecks silently.

**Found along the way:** 211 receipts printed with half-kopecks («82½ к.», 1899-1910, most in 1899-1902; 106.76 р. in all)
are stored with no kopecks at all (TRY_CAST of «82½» fails, and the coalesce turns it into 0), up to 99 kopecks each. #109's note says
the total "stores whole kopecks", which was the intent but is not what happens. Also unparsed: 1909-10 p037 «2841 р. 60 р.»
(the 1909-10 session has it), 1902-03 p021 «218 р. 42 е.».

## 1909-10 (2026-10-27): charity events are outside the printed lines; four kopeck losses fixed; three drama/French gaps open

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
| Moscow | opera | 168 | 168 | −6.00 | open (1909-10-11) |
| Moscow | drama | **134** | 235 | +1,289.64 | printed count is a slip (clear «134» on the scan); receipts open (1909-10-08) |
| SP | ballet | 51 | 51 | 0.00 | exact after 24 Feb fix |
| SP | opera | 157 | 154 + «Миранда» 2 + 18 Dec jubilee bill | +10,000.28 | stats ten-thousands slip, provisional (1909-10-07) |
| SP | drama | 258 | 268 | +712.11 | open (1909-10-09) |
| SP | French | 100 | 101 | −69.90 | open (1909-10-10) |
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

**Still to do:** column reads for the four open receipts gaps (Малый, Александринскій + Михайловскій drama, Михайловскій
French, Большой opera; about 600 cells); «Миранда» (classed as opera) and the Art Theatre run (`VISITING_RUNS`, research layer rebuilt and promoted, backup `outputs/backups/mat_run_1909-10_2026-10-27/`) are settled. The 19 Apr «Утро памяти А. П. Чехова» (no works) is left without a company. The season reviews were not
checked (1909-10 has SP music reviews only).
**Half-kopecks FIXED the same day** (RG: whole kopecks, as #109): research-layer rule, 210 events, +105.98 р.; known_issues.md #161.
