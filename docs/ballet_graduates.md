# Ballet School Graduates — Names and Tenure Start Dates

What this document is: a guide to `docs/ballet_graduates_tenure.csv`
(moved here from `outputs/full_run/` on 2026-08-24 so it survives an
`outputs/` wipe -- `outputs/` is gitignored/disposable per `CLAUDE.md`,
and this file took real hand-verification effort to build; see
`docs/eval/known_issues.md` #34 and its addenda, and #45), the extracted
list of Imperial Theater School ballet graduates with their
service-start dates, built from the Theater School Reports
(`pdf/Spiski_Graduates/`).

**As of #45 (2026-08-24), the 136 `report_hand_verified`/`report_per_row_exception`
dates in this file that were missing from the database have been wired
into the actual pipeline** (`pipeline/parse_and_validate.py`'s
`_repair_graduates_tenure`, sourced from this CSV) -- `raw.person_entry_service`,
`entities.person`, and `research.person`/`research.person_appearance` all
reflect these dates now, not just this reference document. Re-running
the pipeline from raw JSON reproduces them automatically; this CSV no
longer needs to be consulted by hand for that purpose, though it remains
the fuller reference (including `not_stated_in_report` rows and the
BalletArtists identity-linking columns, neither of which the pipeline
fix touches).

## Scope

399 rows, one per ballet-department graduate, covering both the
St. Petersburg and Moscow schools across all seasons in the corpus.
**Drama-department graduates are excluded** — the Theater School Reports
cover both departments, and drama graduates are identified by page:
`graduates_1890-91_p005` and `graduates_1890-91_p006` are the two pages
in the corpus that carry a drama section (confirmed by their own closing
paragraphs, which name the Moscow/St. Petersburg *drama* troupes, not
the ballet ones), and both are left out entirely (see
`docs/eval/known_issues.md` #34, second and third addenda).

Checked directly, not just assumed: a corpus-wide keyword sweep of every
`Graduates`-entity row for drama-specific text ("драмат", "аттестат",
"свидѣтельств") turns up nothing outside those two pages, and every one
of the 399 rows here carries either an explicit "балетную" (ballet
troupe) mention or was individually confirmed against the scanned page
by hand (`docs/eval/known_issues.md` #34, fourth addendum).

`school` was also checked exhaustively, not just where drama might leak
in: every one of the 27 pages where `school` had no `heading_path` city
signal to rely on (334 rows) was read directly against the scan. Three
of those pages had a stale `institution` field (said St. Petersburg on
a page that's actually Moscow) — all three fixed; the other 24 were
already correct (`docs/eval/known_issues.md` #34, fifth addendum).

Columns:

| column | meaning |
|---|---|
| `family_name`, `first_name`, `patronymic` | as printed; patronymic is usually blank because most graduation lists genuinely don't print one (checked page by page — see `docs/eval/known_issues.md` #34) |
| `graduation_season` | the yearbook season the graduation list appears in |
| `school` | `St. Petersburg` or `Moscow` — which Imperial Theater School the graduate belongs to, from the Report's own institution/section heading on that page |
| `tenure_start_date` | when they entered Imperial service, in `YYYY-MM-DD` — **populated only when the Theater School Report itself states it; blank otherwise, see below** |
| `troupe_city` | Moscow or St. Petersburg, when the Report states it |
| `source` | `report_per_row`, `report_per_row_exception`, `report_hand_verified`, or `not_stated_in_report` — see below |
| `note` | why the field is blank, or a flagged disagreement with the BalletArtists roster — see below |
| `entry_id` | internal row identifier, for tracing back to `imperial_theaters.duckdb` |
| `balletartists_link_status`, `balletartists_seasons_attested`, `balletartists_link_note` | whether this graduate could be identified with a specific BalletArtists company-roster record, and why — see "Identity-linking" below |

## `tenure_start_date` comes from the Theater School Report only

If the Report doesn't state a date for a graduate, the field is **blank**
— nothing is inferred or filled in from any other source. This holds
even when a same-named person's BalletArtists record makes a plausible
date fairly obvious; that information is not reliable enough on its own
to state as this person's tenure date, since a common name can belong to
more than one real dancer.

| `source` value | count | what it means |
|---|---|---|
| `report_per_row` | 187 | The graduation list itself states this graduate's service-start date directly (e.g. "съ 1-го сентября 1897 года, въ Московскую балетную труппу"). |
| `report_per_row_exception` | included above | A named individual exception within a cohort note (e.g. "...кромѣ ученика Тихомирова, который зачисленъ съ ..."), applied only to the graduate the exception names. |
| `report_hand_verified` | 148 | The graduate's own row didn't state it, but the assignment paragraph on the same printed page does — the original computer-reading of the page missed that sentence entirely. Read directly off the scanned page by hand and entered here. Covers ten cohorts across 1891, 1892, 1893, 1896 (Moscow), 1899, 1902, 1903, 1906, and 1907 — see `docs/eval/known_issues.md` #34, third addendum for the full page-by-page list. |
| `not_stated_in_report` | 64 | No service-start date anywhere in the Report for this graduate — `tenure_start_date` is blank. Every page these 64 rows sit on was individually checked by hand (see below); none of them turned out to have a dropped assignment paragraph. See the `note` column: some of these rows still carry a BalletArtists date for reference, clearly labeled as *not used*. |

## Every `not_stated_in_report` page has been hand-checked

Earlier versions of this dataset left this as an open question — whether
some of the blank rows were really the extraction dropping an assignment
paragraph on the same page (the way `report_hand_verified` cases are
found), rather than the graduate genuinely having no stated date. As of
this pass, **every page with any `not_stated_in_report` row has been
opened and read directly**, not inferred. Two things came out of that:

- All 10 pages where *every* row on the page was blank turned out to
  have a real, recoverable assignment paragraph — these became the new
  `report_hand_verified` rows above.
- The remaining 5 pages (`graduates_1899-00_p001`, `graduates_1900-01_p001`,
  `graduates_1901-02_p001`, `graduates_1904-05_p001`,
  `graduates_1905-06_p001` — 64 rows, all Moscow) genuinely have no
  assignment paragraph to recover: on four of them, the ballet list is
  immediately followed by a new "Драматическіе курсы" section heading
  with nothing about ballet assignment dates in between; on the fifth
  (`graduates_1900-01_p001`) the source PDF excerpt itself ends right
  after the list, so if a paragraph exists at all it isn't in this scan.
  These are left as `not_stated_in_report`, not guessed at.

## Reading the `note` column on blank rows

For the 64 `not_stated_in_report` rows, `note` tells you why, and
sometimes what else is known but deliberately not used:

- *"For reference only (not used): BalletArtists roster shows service
  starting [date]."* — a single plausible BalletArtists match exists.
  This is **not** in `tenure_start_date` and shouldn't be treated as
  confirmed; it's there so you can decide for yourself whether to chase
  it further.
- *"BalletArtists shows multiple plausible dates... ambiguous."* — more
  than one same-named candidate exists; genuinely unclear which one (if
  either) is this graduate.
- *"BalletArtists has a same-named record but with a date far from
  graduation... likely a different person."*
- *"no BalletArtists record found — may not have entered Imperial
  service."* — the plainest case: graduating did not guarantee a place
  in a troupe, and this is probably a graduate who didn't take one.

## A confirmed disagreement between the two sources, for the rows that DO have a Report date

Every row with a Report-stated date — both `report_per_row` (187 rows)
and `report_hand_verified` (148 rows) — has now been cross-checked
against the BalletArtists roster. Where the two disagree,
`tenure_start_date` keeps the Report's own value (per the rule above)
and `note` flags the disagreement rather than hiding it. 29 rows are
flagged this way in total. Most of these (22) form one clean, striking
pattern across three cohorts:

- **1896-97, 7 graduates including Agrippina Vaganova** — the Report
  says service began **1 May 1897**; the BalletArtists roster says
  **1 June 1897**, and says so identically on every one of the 11
  seasons Vaganova's name appears in it.
- **1897-98, 14 graduates** — same pattern, one month apart (May vs.
  June 1898).
- **Бекъ, Константинъ (1892)** — an individual exception within an
  otherwise St. Petersburg cohort, sent to the Moscow troupe: the
  Report says **1 June 1892**, BalletArtists says **1 September 1892**,
  identically across all 15 seasons he appears in that roster.

Both readings were checked directly against their scanned pages. Neither
looks like a misreading of the other — the month words don't resemble
each other, and the BalletArtists date is far too consistently repeated,
year after year, to be a one-off transcription slip. This looks like a
genuine feature of the historical record — a gap between an official
appointment date and the date service actually began, perhaps — rather
than something to silently correct. Full detail, including the exact
page citations, is in `docs/eval/source_document_anomalies.md`.

The remaining 7 disagreements are individual cases. Most look like
common-surname mismatches rather than genuine disagreements about the
same person — e.g. a graduate whose only same-named BalletArtists match
has a service date 6–10 years off from their graduation — and are noted
as such rather than treated as confirmed.

## Identity-linking to the fuller BalletArtists company record

| column | meaning |
|---|---|
| `balletartists_link_status` | `linked`, `ambiguous`, `unlikely_match`, or `no_record` — see below |
| `balletartists_seasons_attested` | for `linked` rows, the season range this person is attested in the BalletArtists roster (blank otherwise) |
| `balletartists_link_note` | the reasoning behind the status — which date matched, how many other same-named candidates existed, why an ambiguous case couldn't be resolved |

Beyond just cross-checking dates, each graduate was checked for whether
they can be identified with a specific BalletArtists company-roster
record — their fuller career, not just a single confirmed or disputed
date. This was deliberately deferred earlier in this effort precisely
because guessing wrong here means silently merging two different real
dancers (`docs/eval/known_issues.md` #30 documents a case where this
went wrong the first time it was tried, two different women both named
Evdokia Gavrilova) — so it was built as its own careful pass rather than
assumed safe by default.

| status | count | what it means |
|---|---|---|
| `linked` | 342 | Exactly one BalletArtists person could plausibly be this graduate — for the 335 graduates with a Report-stated date, a same-named BalletArtists record within ~4 months of it; for the rest, a single dominant, city-consistent same-named record. |
| `no_record` | 46 | No BalletArtists record under this name at all. |
| `ambiguous` | 9 | Two or more distinct same-named people are on record with no way to tell which, if any, is this graduate — not linked. |
| `unlikely_match` | 2 | Exactly one same-named BalletArtists record exists, but its date is implausibly far (6+ years) from this graduate's own — almost certainly a different, same-named person, not linked. |

Two things worth knowing about how the "one candidate" determination was
made, since both came from real findings rather than assumptions:

- Same-named appearances a few days to about a month apart, in an
  otherwise unbroken run of seasons, are treated as **one person**, not
  two — a genuine yearbook-to-yearbook print inconsistency, not a second
  candidate. Confirmed directly against the scanned pages: Мосолова, Вѣра
  is printed as starting "1 сентября 1893" in 11 of her 13 attested
  seasons and "5 сентября 1893" in the other 2 — both readings are
  legible and correct on their own page, this is the historical record
  disagreeing with itself, not an extraction error.
- A single BalletArtists entry can document **more than one service
  period** for the same person (a departure and a later re-enrollment)
  — found via Легатъ, Иванъ, whose one entry records service from
  1891 to 1895 and again from 1897 to 1899 ("left service"). This isn't
  two candidates either.

For the 335 graduates who have their own Report-stated date, that date
is the primary evidence used to pick the right candidate when more than
one same-named person exists in BalletArtists — not an internal
popularity vote among the BalletArtists records themselves, which turned
out to be the wrong signal to trust alone (an early version of this
check nearly linked several graduates to a majority-vote candidate whose
date was years away from a lone outlier record, conflating two
unrelated phenomena).

## What's still open

- The 9 `ambiguous` and 46 `no_record` graduates are not pursued further
  — for `ambiguous`, guessing which candidate is correct is exactly the
  risk this whole exercise was built to avoid; for `no_record`, not
  every graduate necessarily entered a form of service this dataset
  captures.
