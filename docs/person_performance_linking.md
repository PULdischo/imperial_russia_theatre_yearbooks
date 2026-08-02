# Linking person_appearance to performance: what's possible, what isn't

`research.person_appearance` (a season-level roster listing) and
`research.performance` (a specific work performed in a specific session)
are currently disconnected — a person's employment record and the
specific performances that season have no foreign key between them. This
was a deliberate choice in `docs/entity_centric_model.md` (a roster
listing isn't tied to a specific work performance at all), but it's worth
asking directly whether the *data* has anything in it that could bridge
them anyway, rather than assuming the split is absolute. Checked before
writing anything down. This is a plan only — nothing here is implemented.

## The source of a possible link: `roster_entry_credit`

`raw.roster_entry_credit` (31,781 rows, "performance-count tallies for
Ballet/Musicians entries") has two shapes:

- `category_total` (22,833 rows) — "danced in 32 ballets, 15 operas, 47
  total" — a season-wide count, no specific work named.
- `named_work` (8,948 rows) — "Кипрская статуя (Амуръ — 5)": a specific
  work title, the role danced, and how many times that season. **This is
  the one real bridge available.**

**Scope limit, checked directly**: `named_work` credits exist only for
`BalletArtists` roster entries. `Musicians` only ever get
`category_total`; `Administration`, `ProductionTeam`, and
`TheaterSchoolStaff` roster entries have no credit rows naming a specific
work at all (`ProductionTeam` has 5 stray `category_total` rows and
nothing else). Whatever this doc proposes can only ever link **ballet
dancers**, never administrators, musicians, or teachers, to a specific
performance — the source material simply doesn't record that level of
detail for anyone else.

## What matching actually gets you

Matched each `named_work` credit's title against `entities.work` (same
title-key folding as `docs/work_normalization.md`), then compared the
credit's printed count against how many times that work was actually
performed in that dancer's own city and season:

| Title match | Count |
|---|---|
| Matches exactly one `entities.work` row | 6,715 (75%) |
| No match at all | 531 (6%) |
| Ambiguous (title splits across >1 genre, e.g. a `work_genre_candidate`) | 1,702 (19%) |

Of the 6,707 cleanly-matched credits with a parseable count, compared
against the real session count for that (work, city, season):

| Outcome | Count | Share | What it means |
|---|---|---|---|
| **Fully resolvable** — credit count equals total sessions performed | 2,431 | 36% | The dancer can be confidently linked to *every* `performance` row for that work that season — a real, non-fabricated connection |
| **Partial** — credit count is less than total sessions | 1,525 | 23% | Danced *some but not all* performances of that work; narrows the candidate pool, can't pin exact dates |
| **Contradiction** — credit count is *more* than sessions extracted | 1,666 | 25% | Almost certainly this project's own known completeness gap (`docs/schema.md`'s `not_captured` issue), not a printing error — see below |
| No performance data for that (work, city, season) at all | 1,085 | 16% | Extraction gap or a genuine mismatch not caught by title-key folding |

Concrete examples: Бармина danced Эсмеральда exactly 9 times in 1890-91,
Moscow — and Эсмеральда was performed exactly 9 times that season in
Moscow. That's not a coincidence worth ignoring; it's the same kind of
independent-signal corroboration `docs/person_normalization.md`'s tenure
merging already relies on, just for a different pair of facts.

## A useful side-effect: a second completeness-gap signal

The 25% "contradiction" bucket is interesting beyond the linking question
itself. A dancer's own printed season credit being *higher* than the
number of performances this pipeline actually extracted is an
independent, corpus-wide check on the exact same completeness problem
`analysis.performance_session.session_status = 'not_captured'` already
tracks (3,771 synthesized placeholder cells, per `docs/performance_normalization.md`).
Worth checking directly whether the contradiction cases cluster on the
same seasons/pages the `not_captured` gaps already cluster on — if they
do, this becomes a second, corroborating measurement of the same known
gap rather than a new problem; if they don't, it's a real new lead on
where extraction is silently missing sessions.

## Possible ways forward

1. **Build a `person_performance_credit` (or similar) linking table**,
   scoped honestly to what the data supports — a `resolution` column per
   credit row: `fully_resolved` (linked directly to its N `performance`
   rows), `candidate_pool` (linked to the *set* of possible sessions,
   without claiming which specific ones), `unresolved` (no usable
   performance data), `no_title_match`. Never claim more precision than
   the source has — the "partial" 23% should never collapse into a false
   specific date.
2. **For the ambiguous 19% (genre-split titles)**: the credit's own
   `role_name` might disambiguate which genre-variant work is meant (a
   dancer's named *role*, e.g. "Эсмеральда," is far more likely to belong
   to the ballet-genre `entities.work` row than an opera-genre one sharing
   the same title) — worth checking whether role_name reliably predicts
   the right genre variant before trusting it as an automatic
   disambiguator, same "verify before automating" discipline as everywhere
   else in this pipeline.
3. **Feed the "contradiction" bucket into the completeness-gap ledger**
   (`docs/eval/known_issues.md`) rather than treating it as a
   person-performance modeling problem — it's evidence about extraction
   completeness, not about whether the link works.
4. **Leave "no performance data" and "no title match" unresolved**,
   flagged for a human to spot-check a sample rather than guess at a fix
   — consistent with how `work_genre_candidate` and the Tier 2 person
   review queue are already handled.

## Open questions

- Does the "contradiction" bucket actually cluster with known
  `not_captured` gaps, or is it a different, new completeness problem?
  Needs checking before claiming it's "just" the known issue.
- Is `role_name`-based genre disambiguation (option 2) reliable enough to
  automate, or does it need its own review queue the way
  `work_genre_candidate` does?
- Worth extending `category_total` (Musicians' season-wide counts, no
  named work) into a coarser completeness cross-check too, even though it
  can never produce a person↔performance link the way `named_work` can?
