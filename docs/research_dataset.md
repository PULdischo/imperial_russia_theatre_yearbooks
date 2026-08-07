# Research dataset: entity resolution plan

The verbatim/`raw` layer (`docs/schema.md`) is deliberately one row per
*printed appearance* — the same person, theater, or work appears as a
separate, unlinked row every time it's printed across 18 seasons. That's
the right choice for transcription fidelity (`docs/research_questions.md`
flagged entity resolution as "a deliberately separate, later task" from
day one, precisely so guessing at identity never contaminated getting the
page right). This doc is that later task: what entities to resolve, how to
model them, and how a non-coder actually works with the result. Mirrors
`docs/verbatim_deliverables.md`'s planning-before-building approach.

Nothing here touches `raw`. This is a **third schema, `entities`**, sitting
alongside `raw` and `analysis` — additive, never overwriting, same rule
`build_duckdb.py` already follows for `analysis`.

## Entities identified

Four candidates, in order of how confidently they can be resolved
automatically. Real numbers from the full corpus below, to ground the
difficulty ranking rather than guess at it:

| Entity | Distinct raw values | Rows referencing it | Difficulty |
|---|---|---|---|
| Theater | 22 raw strings | 23,726 `event_entry` rows | **Easy** — already 90% solved |
| Work | 5,395 distinct (title, genre) pairs | 25,051 `event_entry_performance` rows | **Medium** |
| Person | 4,163 distinct (family, first, patronymic) triples | 20,716 `person_entry` rows | **Hard** — the centerpiece |
| Institution | 178 distinct `institution` strings | 20,716 `person_entry` rows | **Hard, and probably out of v1 scope** — see below |

### Theater — already effectively resolved

`analysis.event_entry.theater_canonical` (built in `build_duckdb.py`
for the completeness-reconciliation work) already collapses the 22 raw
spelling/suffix variants down to the real 6 venues. `entities.theater`
just needs to be the small, hand-seeded reference table this already joins
against — city, and the season a venue starts existing (Новый театръ from
1898-99 on) — not a resolution *pipeline*, since there's nothing left to
resolve.

### Work — title + genre, revivals are a feature, not a bug

A play or opera performed in 1891 and again in 1905 is *correctly* the
same Work — repertoire research explicitly wants "how often was this
revived, and when" as an answerable question. That means, unusually,
**a work's identity can be keyed directly on its canonicalized (title,
genre) text** rather than needing fuzzy human-reviewed matching: collision
on that key is exactly the right behavior, not a resolution error. The
real work here is just canonicalizing the text first (trimming genre
abbreviation punctuation, folding pre-reform letter variants the same way
`theater_canonical` does), then grouping.

### Person — the hard, valuable one

4,163 distinct name-triples across 20,716 appearances means the average
person here appears ~5 times — real evidence that the same people recur
across seasons, which is exactly what prosopography research needs
resolved. But unlike Work, two identical name-triples are **not**
automatically the same person — common surnames repeat across genuinely
different people, and this source already has its own way of flagging
that: printed ordinal suffixes (`Вальтеръ 1-й` / `Вальтеръ 2-й`) exist
*because* the original compilers needed to disambiguate two people with
the same name in the same volume. That signal should be preserved, not
discarded during normalization. Full approach below.

### Institution — real institutions are a minority of the `institution` column

Checked before designing this, rather than assuming: the 15 most frequent
`institution` values are dominated by things like `"Списокъ артистовъ
Императорскихъ театровъ"` ("List of artists of the Imperial Theatres,"
4,537 rows) and `"Ежегодникъ Императорскихъ театровъ"` (the yearbook's own
title, 1,139 rows) — **series/document titles, not organizational
affiliations**. This is the same institution/heading_path boundary
ambiguity already documented in `known_issues.md` #2, just visible here as
a modeling problem instead of an extraction one: naively resolving the
`institution` column as-is would produce a handful of "entities" that are
actually just section headers, not real institutions. A few genuine
institutions *do* show up in the same column (`"Императорское
С.-Петербургское Театральное Училище"`, 3,110 rows) — they're just mixed
in with boilerplate, not cleanly separated from it.

**Recommendation: descope for v1.** The real institutions in this corpus
form a small, closed, nameable set (the Directorate, the SP and Moscow
Offices, the two Theater Schools, and the six theaters as staffing units)
— small enough to hand-curate as a lookup, the same way `theater_canonical`
is hand-curated rather than inferred. Building that lookup is real,
worthwhile work, but it's a distinct task from Person/Work/Theater and
shouldn't block shipping those. Ship without it; add
`entities.institution` as a hand-curated reference table once someone's
willing to do the (fairly small, ~15-20 row) curation pass.

## Data model

```
entities.theater        theater_id (UUID, uuid5) | canonical_name | city | active_from_season
entities.work            work_id (UUID, uuid5)    | canonical_title | canonical_genre
entities.person           person_id (UUID, uuid4, persisted) | display_name | canonical_family_name
                          | canonical_first_name | canonical_patronymic | ordinal_suffix
                          | first_attested_season | last_attested_season | superseded_by_person_id

entities.person_link      entry_id (FK -> raw.person_entry) | person_id (FK) | match_method | match_confidence
entities.work_link        raw_performance_id (FK -> raw.event_entry_performance) | work_id (FK -> entities.work) | match_confidence
```

`theater` and `work` need no link table — `theater_canonical` /
`canonical_title+canonical_genre` already double as the join key directly
against `raw`. Only `person` needs a separate crosswalk, because person
matching is uncertain and reviewed, not a deterministic text transform.

### Two different UUID strategies, deliberately

- **Theater and Work: `uuid5`, deterministic, seeded from the canonical
  text.** Re-running the resolution pipeline from scratch always produces
  the same IDs for the same canonical name — a stateless, rebuildable
  transform, exactly like everything in `analysis` already is.
- **Person: `uuid4`, random, generated once and permanently persisted in
  `entities.person`.** This is the one place this project's "always
  rebuildable from scratch" pattern *cannot* apply: a person's identity
  can't be deterministically derived from their name (two different real
  Ивановыs would collide), and worse, deriving it from *which appearance
  happened to come first* would make a person's ID silently change if
  earlier pages are added to the corpus later. So `entities.person` is a
  **living reference table, not a view** — new extraction runs get matched
  *against* the existing registry (new people get new UUIDs appended;
  existing people's UUIDs never change), the same relationship a
  cumulative census or authority file has to new records, not the
  stateless SQL-over-`raw` pattern `analysis` uses everywhere else. Worth
  flagging clearly since it's a real architectural exception in this
  project.

### Person matching: staged, confidence-scored, never silently automatic

Given what's actually at stake (a wrong merge fabricates a person's career
that never happened; a wrong non-merge just under-counts, less damaging),
matching should escalate rather than guess:

1. **Tier 1 — exact normalized match, auto-accepted.** Fold pre-reform
   letter variants (ѣ->е, і->и) and case the same way `theater_canonical`
   already does, and match on (folded family name, ordinal suffix, first
   name, patronymic) as one unit — the ordinal suffix is *kept*, specifically
   so `Петровъ 2-й` never silently merges with a different `Петровъ`.
2. **Tier 2 — fuzzy candidates, human-reviewed, never auto-merged.**
   DuckDB has `jaro_winkler_similarity`/`levenshtein` built in already, so
   this needs no new dependency: surface near-matches Tier 1's exact fold
   misses (a spelling drift Tier 1's fixed fold list doesn't cover) as
   candidate pairs with a similarity score, and stop there — a human
   confirms or rejects, per the review-queue design below.
3. **Merges are additive, never destructive.** A confirmed Tier 2 merge
   sets `superseded_by_person_id` on the absorbed record rather than
   deleting it — every `person_id` ever issued keeps working as a
   citation-stable reference, and a merge decision can be revisited later
   without losing which rows were affected.

This is the same discipline this project has used since the extraction
pilots: cheap deterministic method first, escalate to a human only for
what's genuinely ambiguous, and never treat "the algorithm didn't flag it"
as proof of correctness.

## Interface for a non-coder

Two distinct jobs, two different tools — reusing what this researcher
already uses rather than introducing something new for its own sake:

**Reviewing Tier 2 candidate merges — Google Sheets, not a custom app.**
Export candidate pairs (two person_entry rows side by side, similarity
score, a blank decision column) as a Sheet; the researcher fills in
Yes/No/Unsure per row using ordinary Sheets filtering, no new tool to
learn. A small script reads confirmed rows back and applies them to
`entities.person`. OpenRefine remains the right tool for the *earlier*
step this feeds from (surfacing spelling-variant clusters in the verbatim
text in the first place, per `docs/verbatim_deliverables.md`'s OpenRefine
section) — the two aren't competing, Refine cleans, Sheets decides.

**Browsing resolved entities — extend the Obsidian vault, don't build a
new interface.** One note per `person_id`, containing a table of every
appearance (season, role, theater, link back to that page's existing
note) — the vault already exists and the researcher already likes it, so
a person's whole career becomes one note away from any page they're
reading. Same idea for Work (every `performed` session across every
season) and Theater. This is a genuinely small addition on top of
`build_obsidian_vault.py`, not a new system.

**Deliberately not recommending yet: the Stage 6 Streamlit app.**
`docs/pipeline.md` has held it as "not yet built" the whole project, and
that's still the right call — Sheets (review + pivot analysis), Obsidian
(browsing), and OpenRefine (cleaning) cover every actual need above using
tools already in hand. Build the interactive app only if a real gap shows
up that static exports can't cover (e.g., live cross-filtering across
thousands of person records at once) — same "don't build infrastructure
before a real gap justifies it" call this project already made once,
choosing DashScope over standing up local GPU serving on Adroit.

## Open questions

- How aggressive should Tier 1's exact-fold match be about *role*
  continuity? Two identical name-triples in wildly different roles
  (a dancer and an administrator) in overlapping years are more likely two
  different people who share a name than one person changing careers —
  worth a plausibility flag even on "exact" matches, not just fuzzy ones.
- `entities.institution` needs someone to actually do the ~15-20-row
  curation pass described above before it can exist at all — not a
  pipeline task, a one-time judgment-call task.
- Should `entities.person`'s registry live in the same `.duckdb` file as
  `raw`/`analysis`, or separately, given it's the one piece of this
  project that isn't safely regenerable from scratch and needs its own
  backup discipline?
