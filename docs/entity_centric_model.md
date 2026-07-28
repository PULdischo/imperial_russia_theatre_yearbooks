# Plan: an entity-centric model (v2) — not yet built

`docs/schema.md` (verbatim/`raw`) and `docs/research_dataset.md` (`entities`)
describe the model as it exists today. This doc is a plan for a proposed
**next evolution**, prompted by looking at the schema diagram and noticing
its hub is `source_pages` — correct for how the data was *captured*, wrong
for how a researcher actually wants to *query* it. Every interesting
question ("this person's whole career," "how often was this work revived")
currently means traversing a crosswalk table back through a page-centric
table. This plan proposes to invert that: **Person, Performance, Work, and
Theater become the primary, directly-queryable entities**; the verbatim
page-centric tables stay exactly as they are today, underneath, as the
immutable citation layer everything else points back to.

Not implementing this yet — this is the design to react to first.

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

## What this makes redundant

`build_datasette.py`'s `person_appearances` and `work_performances`
tables — built as SQL joins purely for Datasette's browsing/faceting UI —
turn out to have already been a preview of this exact shape. Under this
plan they stop being query-time joins and just *are*
`entities.appearance` and `entities.performance` (joined to `session` and
`work`) directly. The Datasette export script gets simpler, not more
complex, once this lands.

## Open questions — worth deciding before building, not during

1. **Scope of `service_period`/`roster_entry_credit`: per-appearance or
   per-person?** They're printed per listing today (a person's tenure note
   gets reprinted, sometimes identically, every season they appear), so
   this plan defaults to keeping them scoped to `appearance` (faithful to
   what's actually printed) rather than consolidating into one
   career-spanning record per `person` — but a consolidated "this person's
   full service history" table is a reasonable thing to want later, and
   would be a separate, further-derived table on top of this one, not a
   replacement for it.
2. **Does `raw.performance_work.work_id` get renamed**, or does the
   rename only happen in the new layer? Renaming raw's own column is a
   breaking change to an otherwise-immutable table; not renaming it keeps
   the `raw_work_id`-style alias trick alive in a second place.
3. **Versioning the deliverables.** The HF dataset and the running
   Datasette site both currently reflect the v1 shape. Does v2 replace
   them in place, or ship as a clearly-labeled second version so anything
   already citing today's `person_id`/`work_id` values keeps working?
   (Those specific UUIDs don't change under this plan — only the tables
   built on top of them do — but worth being explicit about which URLs/
   files represent which version.)

## Rough shape of the build, when it happens

Not scheduling this, just sketching where the work would land: `person`
and `work`'s Tier 1/Tier 2 resolution logic in `build_entities.py` is
unaffected (the matching algorithm doesn't change) — what changes is the
output shape, writing an enriched `appearance`/`session`/`performance`
directly instead of a thin crosswalk table beside the untouched raw ones.
`build_datasette.py` gets simpler. `docs/schema.md` and
`docs/research_dataset.md` both need a "v2" companion section once this is
real, not a rewrite — the raw layer's documentation doesn't change at all.
