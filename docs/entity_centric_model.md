# The entity-centric model (v2) — implemented

`docs/schema.md` (verbatim/`raw`) and `docs/research_dataset.md` (`entities`)
describe the model as it existed before this plan. Prompted by looking at
the schema diagram and noticing its hub was `source_pages` — correct for
how the data was *captured*, wrong for how a researcher actually wants to
*query* it. Every interesting question ("this person's whole career," "how
often was this work revived") meant traversing a crosswalk table back
through a page-centric table. This plan inverted that: **Person,
Performance, Session, Work, and Theater are now the primary,
directly-queryable entities**, in a new `research` schema
(`pipeline/build_research_model.py`); the verbatim page-centric tables
stay exactly as they were, underneath, as the immutable citation layer
everything else points back to.

**Implemented** — real results in the Implementation section below. The
two open questions this doc originally left unresolved (fold roster data
into `person` or keep it separate; accept the receipts double-counting
risk or keep `session` distinct) were both settled in favor of the more
conservative option: `person_appearance` stayed its own table, and
`session` stayed distinct from `performance`.

## The core move: bake foreign keys in, stop crosswalking at query time

Today, getting from a resolved `person` to their actual career facts means:
`person` → `person_link` (crosswalk) → `roster_entry` (the facts, on the
raw/page-centric table). Two hops, and the crosswalk table exists purely
to hold a `person_id` column that — in this proposal — just lives directly
on the fact row instead.

Concretely: `entities.person_link` and `entities.work_link` disappear as
separate crosswalk tables. Their one job (mapping a raw row to a resolved
entity) becomes a plain `person_id` / `work_id` column baked directly onto
new primary fact tables, resolved once when the entity-resolution pipeline
runs, not re-joined at every query.

## Proposed tables

| Table | Grain | Replaces / absorbs |
|---|---|---|
| `entities.person` | one resolved real person | unchanged |
| `entities.appearance` | one person's presence in one printed roster listing | `raw.roster_entry` + `entities.person_link`, merged |
| `entities.theater` | one venue | unchanged |
| `entities.session` | one printed box-office record (date, theater, receipts) | `raw.performance_session`, with `theater_id` resolved and inlined instead of joined by `theater_canonical` text at query time |
| `entities.performance` | one work performed within one session | `raw.performance_work` + `entities.work_link`, merged |
| `entities.work` | one resolved work (title + genre) | unchanged |

A query for "everything this person did" becomes one join
(`person ⋈ appearance`) instead of two. A query for "every performance of
this work, with venue and receipts" becomes
`work ⋈ performance ⋈ session ⋈ theater` — four real foreign keys, no text
matching, no crosswalk hop.

**`raw.*` does not change at all.** Every table in `docs/schema.md` stays
exactly as-is — untouched, immutable, still the reproducibility guarantee.
These new tables are an additional layer built on top, the same way
`entities` itself was additive to `raw` and `analysis`.

## Why `entities.session` has to stay a distinct entity from `entities.performance`

The obvious-looking simplification — one flat "Performance" row per (work,
date, theater) — is a real trap, checked against the actual corpus before
writing this plan: **6,158 of 17,345 sessions (35%) list more than one
work** (a night with two one-act plays, a ballet plus a curtain-raiser,
etc.), and receipts are recorded once **per session**, not once per work.
Flattening to one row per (work, session) would silently duplicate the
receipts value across every work on a multi-work bill — a `SUM(receipts)`
over that flat table would overcount by roughly a third of the corpus,
silently, with no error to catch it.

Keeping `session` (the box-office fact: date, theater, receipts, one row)
and `performance` (the bill-item fact: which work, within which session)
as two separate tables is what avoids this. It also happens to be the same
shape `raw.performance_session`/`raw.performance_work` already have —
this plan doesn't invent a new shape, it resolves real foreign keys onto
the existing one and promotes it to primary.

## Reusing existing keys — a smaller migration than it looks

Both new tables can reuse identifiers that already exist today rather than
minting new synthetic keys:

- `entities.appearance.appearance_id` = `raw.roster_entry.entry_id`
  (same value, reused as the PK). This is a genuine simplification, not
  just a rename: `raw.service_period` and `raw.roster_entry_credit` already
  key on `entry_id`, so they become valid children of `entities.appearance`
  with **zero changes to either table** — the join just already works.
- `entities.session.session_id` = `raw.performance_session.session_id`,
  reused directly.
- `entities.performance` needs a fresh PK, though — reusing
  `raw.performance_work.work_id` directly would collide with
  `entities.work.work_id`'s different meaning (a name collision this
  project already had to work around once, aliasing it to `raw_work_id` in
  `build_datasette.py`'s joined views). Worth fixing properly here instead
  of aliasing around it again: rename `raw.performance_work`'s own PK to
  `work_appearance_id` in this new layer (raw's actual column can stay
  `work_id` for backward compatibility, or get renamed too — open
  question below).

## What this made redundant

`build_datasette.py`'s old `person_appearances` and `work_performances`
tables — built as SQL joins purely for Datasette's browsing/faceting UI —
turned out to already be a preview of this exact shape. `build_datasette.py`
is now a straight per-table copy of `research.*` with no joins at all,
exactly as predicted: it got simpler, not more complex.

## Implementation

`pipeline/build_research_model.py` builds a new `research` schema
(`entities`, `raw`, and `analysis` are all untouched underneath). Real
row counts against the full corpus:

| Table | Rows | Grain |
|---|---|---|
| `research.theater` | 6 | one venue |
| `research.work` | 4,509 | one resolved work — post `docs/work_normalization.md` |
| `research.person` | 3,271 | one *currently-active* resolved person — the 676 superseded/merged records from `docs/person_normalization.md` are excluded, not shown as rows with a dead-end pointer |
| `research.session` | 27,497 | one printed box-office record (date, theater, receipts), including the 3,771 `not_captured` completeness placeholders, now labeled `date_confidence = 'synthesized_gap'` rather than lumped in with genuine date-parsing failures |
| `research.performance` | 25,013 | one work performed within one session |
| `research.person_appearance` | 20,715 | one roster listing, resolved to its person |

**Person**: no `superseded_by_person_id`, no `tier1_key`, no separate
`person_merge_log`/`person_wikidata_link` tables — `wikidata_qid`,
`wikidata_label`, and `wikidata_description` are inlined directly onto
`person` (a clean 1:1 today). The merge decisions themselves stay fully
recorded in `entities.person_merge_log`, just not in the published table —
a researcher wanting that audit trail queries the DuckDB file directly,
same as `docs/eval`'s per-run history is available but not bundled into
the browsable dataset.

**Session vs. performance**: kept distinct, resolving Open Question
(receipts). Receipts live *only* on `session` — `research.performance` has
no receipts column at all — so `SUM(receipts_total_kopecks)` over
`research.session` is always safe and summing `research.performance` can
never even be attempted. Verified directly: a real multi-work session
(`repertoire_1890-91_p000__s005`, 2 works) produces exactly 2
`performance` rows and exactly 1 `session` row.

**`session.date`** is the best-available date: the run-corroborated
correction from `docs/performance_normalization.md` when there is one,
otherwise the original computed date, with `date_confidence` always
alongside it — never silently hidden.

**`person_appearance`** stayed a separate table rather than folding into
`person` or `performance` (resolving Open Question 1 differently than a
nested-column alternative that was also considered): a roster listing is
a season-level employment fact with no tie to a specific work performance,
and a many-to-many relationship (one person, many listings) is what a
real table is for.

One real bug found and fixed while building this: `entities.person_link`
was found still pointing 3,024 rows at already-superseded people, from an
*earlier, unrelated* rerun of `build_entities.py` (for Work
normalization) silently resetting repointing that a previous run had
already applied correctly. `build_person_tier1` rebuilds `person_link`
from scratch every run using only each row's own exact-match cluster, with
no knowledge of any later Tier 2/tenure/Wikidata merge — and once a person
is absorbed, they drop out of Tier 2's candidate pool entirely, so the
specific pair that ever justified merging them can never be regenerated to
re-trigger a per-decision repoint on a later run. Fixed with
`_repoint_all_superseded()`: a full-chain resolution over the *entire*
current `superseded_by_person_id` state in `entities.person`, run once at
the end of every `build_entities.py` invocation, independent of which
candidate pairs happen to still be regenerable. Caught only because
`research.person_appearance`'s foreign key into `research.person` (which
excludes superseded rows) failed loudly at build time — a real,
concrete case for keeping real FK constraints even in a project that
mostly works in plain DuckDB/SQL.

## Resolved decisions (open questions from the original plan)

1. **Scope of `service_period`/`roster_entry_credit`**: kept scoped to
   `raw`, joined via `entry_id` = `person_appearance.appearance_id` when
   needed, not flattened into `person_appearance` itself — a person can
   have more than one service period per listing, and flattening would
   have meant guessing which one "belongs" on the row.
2. **`raw.performance_work.work_id` was not renamed** — `raw` stays
   completely untouched, per this project's standing rule. The new layer
   uses its own name (`performance_id`) instead.
3. **Versioning**: not yet decided which HF/Datasette artifacts get
   replaced in place versus versioned — still open, now that the schema
   itself is real and this becomes an actual publishing decision rather
   than a hypothetical one.
