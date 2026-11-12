# New-season checklist -- the same treatment for every season

RG, 2026-11-12: "i want to make sure each season gets the same treatment." This is the list of every check a Repertoire
season (and its lists) has received so far, compiled from `docs/eval/known_issues.md` (#93, #119, #135, #138-#162 and the
2026-10-10..11-10 sweeps), `docs/eval/reconciliation/README.md` and `docs/query_log.md`. Corpus-wide sweeps run after a
season was promoted have to be re-run for each later season -- they are listed here as season steps for that reason.
Status columns: done / partial / not done / n.a. Keep the table current when a season is onboarded.

## A. Extraction and transcription

| # | Step | Source of the precedent | 1910-11 | 1911-12 |
|---|---|---|---|---|
| A1 | Scans checked for cut-off text and blur on arrival, re-shoot list to RG | RG 2026-11-11 | n.a. | late (found pp. 130/132/134 mid-read; re-shoot pending) |
| A2 | Per-season crop + column calibration, every crop checked for clipping | #93, #119 | done | done (per-page keys) |
| A3 | Four paid passes (headers, baseline, row-level, column-wise) + column repair | #119, #135 | done | done |
| A4 | Printed page numbers and page headers wired into the parse | CLAUDE.md, #76, #83 | done | done |
| A5 | Full scan-verified sweep, every cell (6 batches) | #79/#82/#93/#119/#135 | done | done |
| A6 | Consistency pass across batches (printed periods in genres/titles) | #135 | done | done (62 titles) |
| A7 | Blind audit: 6 random pages read before seeing the transcription | #135 post-sweep audit 1 | done | done 2026-11-12: 1,458 fields, 0 errors |
| A8 | Quality flags to zero or explained; date check (weekday vs date, overrides) | #142, #138, #148 | done | done (1 flag = print typo) |
| A9 | not_captured / page-break date sweep | #143, #162 | done | done (0) |
| A10 | Genuine print typos logged | genuine_print_typos.md | done | done |

## B. Corpus sweeps run after earlier promotions (re-run per season)

| # | Step | Precedent | 1911-12 |
|---|---|---|---|
| B1 | Final ь/ъ in titles read on the scan | #151 | checked 2026-11-12: only real ь words (Грань, Израиль, Медвѣдь) |
| B2 | Genre repeated at the end of titles | 2026-10-12 | checked: 0 |
| B3 | Benefit / season headings stored as works (Михайловскій) | 2026-10-12 | covered by the sweep brief; not re-queried |
| B4 | Half-kopeck receipts | #161 | checked: 0 |
| B5 | Receipt print typos to research corrections | #109, #142 | done (16 rows) |
| B6 | Free-performance banners on the right sessions | 2026-10-13 | done in sweep (14 Nov, 6 Dec, 1 Feb) |

## C. Research-layer curation (per season)

| # | Step | Precedent | 1911-12 |
|---|---|---|---|
| C1 | Performances with no discipline: classify (title rules, art_form_by_title, overrides) | "Titles with no art form", #158 | done 2026-11-12: 20 -> 8; left blank as in earlier seasons (galas items, concert sections, cantata, apotheosis, 2 divertissements by rule) |
| C2 | Plain «Дивертиссементъ» -> ballet genre | 2026-10-12 ruling | done 2026-11-12: 4 ballet, 2 left blank by the rule |
| C3 | Act/scene excerpts linked to their parent work | 2026-10-13 excerpt links | done 2026-11-12: 5 curated links + curated parent «Призракъ»; the rest automatic |
| C4 | Performed events with no work: decided (annotation-only) | #141 | done 2026-11-12: 5, scan-read, none on the opera/drama/ballet lists' dates; stay annotation-only; Literary Fund evening flagged charity (RG) |
| C5 | Visiting troupe runs labelled | VISITING_RUNS | done (MXT, RG) |
| C6 | Dancers in operas/dramas (`includes_dance`) for new works | 2026-10-12 | done 2026-11-12: nothing to mark. Both 1911-12 BalletArtists lists name only ballets in «Въ томъ числѣ» (364 entries; operas/dramas appear only as category totals, e.g. «въ 1 оперѣ—4»); no «ком.-бал.» and no title naming a dance. The four works with dancer evidence from other seasons (Демонъ, Жизнь за Царя, Князь Игорь, Фаустъ) stay unmarked here by the season-and-city rule. Re-check when the 1911-12 Season Reviews arrive (D6) |
| C7 | New work titles: art-form overrides, title aliases, work merges by majority | #156, work-identity folding | done 2026-11-12: 104 new works checked; 13 folded (1 raw fix, 10 typo aliases, 2 variant aliases, Снѣгурочка subtitle) with RG cell by cell; checked against the opera/drama production lists; «Tanzpoeme.» / «Variete.» left as stored, added to the dancers leads (RG) |
| C8 | Jubilee / benefit / obituary annotations catalogued | docs/jubilees_obituaries | **not done** for 1911-12 |

## D. Reconciliation (per season)

| # | Step | Precedent | 1911-12 |
|---|---|---|---|
| D1 | Season totals transcribed | #147 | done |
| D2 | compare_season_stats, every gap to a ledger outcome (`outcome_ledger.csv`) | reconciliation README | done 2026-11-12: 13 rows (1911-12-01..13); fixed on the way: Wagner's Ring «музык. драма» -> opera (RG), «Judith, eine Tragödie.» -> German, Гамлетъ «датскомъ» alias |
| D3 | Blind column reads, every theater (receipts + titles) | scan_audit README (1896-97..1910-11) | done 2026-11-12: 1,673 sessions, every receipt as stored, 3 title cells re-read (all as stored or ambiguous) |
| D4 | Ballet lists vs Repertoire, every lead read in both sources | #135, #146 | done (SP 12 explained); **not yet in ballet_list_repertoire_disagreements.md** |
| D5 | Opera productions lists vs Repertoire | 1910-11 ledger 14-15 | n.a. by RG's rule (opera lists archive only) unless RG reopens |
| D6 | Season Reviews vs Repertoire (dates, casts) | #141 notes, review checks | n.a. until the 1911-12 reviews are scanned |

## E. Lists and people

| # | Step | Precedent | 1911-12 |
|---|---|---|---|
| E1 | Full scan-read of every list entry, neighbouring-list leaks removed | #135 follow-up 3 | done (cut-off columns pending re-shoot) |
| E2 | Ballet productions lists verified + creators linked | #133 | done |
| E3 | Staff-list folios | 2026-11-03 | done |
| E4 | Person merges for the new season | merge batches | partly (A, B applied; C, D, E open) |
| E5 | Wikidata for new persons / creators | #133, link_wikidata | **not done** |
| E6 | Display names | RG 2026-11-12 | deferred to one audit when all seasons are in |
