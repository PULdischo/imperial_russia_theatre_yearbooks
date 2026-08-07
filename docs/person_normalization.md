# Person normalization: tenure-based merging and Wikidata linking

Two additive passes on top of the Tier 1/Tier 2 person resolution described
in `docs/research_dataset.md`, both done after a conversation with the
researcher about what independent evidence, beyond name spelling, could
help decide whether two similar names are the same real person. Neither
touches `raw`; both extend `entities` non-destructively, same rule as
everything else in this schema.

## Tenure-based auto-merging

**The insight:** `raw.person_entry_service.start_date_undate` is a real
historical fact ("in service since 3 September 1881") that gets reprinted
identically in every later yearbook the same person appears in. Two
near-identical spelling variants that *also* share an exact printed service
start date is much stronger evidence than name similarity alone — a
coincidence two different people sharing both a near-identical name and an
identical start date is highly unlikely.

**What changed in `pipeline/build_entities.py`:**

- Every Tier 2 candidate pair gets a `tenure_signal` (`shared_start_date`,
  `conflicting_dates`, or `no_date_data`) and `tenure_evidence` column,
  computed from `entities.person_link` joined to `raw.person_entry_service`.
- `apply_tenure_corroboration()` auto-confirms — without individual human
  sign-off — any pending pair whose `tenure_signal` is `shared_start_date`.
  This is a deliberate, explicit exception to the "never auto-merge Tier 2"
  rule in `docs/research_dataset.md`, made because the researcher judged
  this specific signal strong enough to trust directly.
- `reconcile_person_merges()` turns a confirmed decision into an actual
  merge: every `raw.person_entry` appearance that belonged to the absorbed
  person is repointed (`entities.person_link.person_id`) onto the survivor,
  and the survivor's attested season range is recomputed from the union of
  both clusters' real appearances. Previously, a "merge" only set
  `superseded_by_person_id` and left appearances split across records —
  fixed for both this new tenure path and the pre-existing human-review
  path, since neither had ever actually been exercised before (zero
  confirmed merges existed prior to this pass).
- Uses union-find, not pairwise resolution: a person can appear in more
  than one confirmed pair (three printed spelling variants of one
  patronymic cross-matching pairwise was observed in the real data — A-B,
  A-C, B-C), and naive pairwise merging would pick an inconsistent survivor
  depending on row order. Each connected component's survivor is always its
  lexicographically smallest `person_id`.
- The candidate-generation → tenure-check → merge cycle loops to a fixed
  point within one pipeline run (converges in 2 passes on this corpus).
  Without looping, a still-pending pair whose *other* member gets absorbed
  by an unrelated merge in the same run would silently disappear instead of
  being regenerated against its new survivor — confirmed against the real
  data (11 of the first pass's 51 remaining pairs pointed at an
  already-superseded person before this fix).
- A permanent, append-only `entities.person_merge_log` records every
  decided pair (evidence included) regardless of what later iterations do
  to the live `entities.person_candidate` working table — needed because
  that table only ever holds comparisons among *currently active* people,
  so a tenure-confirmed pair's evidence would otherwise become unrecoverable
  the moment its absorbed member drops out of the next rebuild.

**Results, run against the full corpus:**

| | Count |
|---|---|
| Tier 2 candidate pairs generated | 851 |
| Auto-confirmed via shared service-start date | **800 (94%)** |
| Person records merged | 672 |
| Surviving (post-merge) person records | 522 |
| Remaining for human review | **51 → 40** (11 were stale references to an already-merged person, corrected by the fixed-point loop above) |

Two artifacts for the researcher:

- `outputs/full_run/person_tenure_audit.csv` — all 800 auto-accepted pairs,
  with similarity score, name-match reason, and the shared date that
  justified each one. A spot-check list, not a decision queue.
- `outputs/full_run/person_review_queue.csv` — the remaining 40 pairs
  still needing an explicit Yes/No/Unsure, now also showing
  `tenure_signal`/`tenure_evidence` so the researcher can see *why* each
  one is hard (conflicting dates vs. no service-period data at all are very
  different situations to review).

## Wikidata linking

**The idea:** where a resolved person is independently identifiable —
someone historically notable enough to have a Wikidata entry — link
`entities.person` directly to a Wikidata QID, so the dataset connects
outward into the broader knowledge graph (birth/death dates, other
biographical sources, VIAF/other authority IDs Wikidata itself links to)
rather than staying a closed island.

**Scope:** the roster spans thousands of administrative and rank-and-file
staff who will almost never have a Wikidata entry — querying everyone would
mostly waste API calls on empty results. `pipeline/link_wikidata.py --pilot`
restricts to people whose printed role suggests real historical notability
(ballet masters, kapellmeisters/conductors, ballerinas, directors,
designers, composers, soloists) — confirmed against the real data before
committing to it: 964 of ~3,275 active person records match at least one of
these role keywords.

**Matching method:** Wikidata's public `wbsearchentities` API (no
authentication needed — the Wikidata MCP connector wasn't authorized in
this session, so this hits the same underlying public data directly
instead), searched on a name modernized from pre-1918 to standard
orthography for search purposes only (`entities.person`'s own printed
spelling is never altered).

**Confidence policy — deliberately conservative**, since a wrong Wikidata
link is a visible, citable error for a researcher: auto-accept only when
there is exactly one search result, its label/alias exactly matches the
modernized search name, its description names a theater/music/dance-related
occupation, and any birth/death years given don't contradict the person's
own attested season range. Anything else — zero results, multiple
candidates, or a single candidate missing or contradicting that evidence —
goes to a review CSV rather than into `entities.person_wikidata_link`.

**Results, pilot run against the full corpus:**

| | Count |
|---|---|
| Pilot pool (notable-role people) | 964 |
| Auto-accepted (written to `entities.person_wikidata_link`) | **45** |
| Distinct real Wikidata people represented | 41 |
| Flagged for human review | 127 |

The auto-accepted list includes genuinely significant historical figures —
Marius Petipa, Mathilde Kschessinska, Eduard Nápravník, Leopold Auer, the
Legat brothers, Olga Preobrajenska — confirming the matcher is finding real
identities, not name-collision noise. `outputs/full_run/wikidata_review_queue.csv`
holds the 127 people needing a human look (multiple same-name candidates,
a description that doesn't confirm occupation, or one that outright
contradicts the person's attested dates).

**An emergent finding, merged after an explicit decision:** 4 of the 45
links shared their Wikidata QID with a *different* `entities.person`
record — `Ивановъ 1-й, Левъ Ивановичъ` and `Ивановъ, Левъ Ивановичъ` both
resolved to Lev Ivanov (Q282950), and the same pattern showed up for
Feliks Kschessinsky, Sergei Legat, and Nadezhda Petipa. This happens
because the printed ordinal suffix ("1-й") only appears in years there was
an actual homonym in print to disambiguate from — the same real person can
appear with and without it across different yearbooks, which Tier 1 (by
design) never folds together, since the ordinal is exactly the signal that
protects two *different* same-named people from being merged. An
independent external identifier agreeing across both split records is real
evidence they're one person after all, but it crosses a boundary Tier 1
was explicitly built never to cross on its own — so unlike the tenure rule
above, this wasn't applied automatically alongside the linking pass; the
researcher confirmed it explicitly first.

`pipeline/link_wikidata.py --merge-shared-qids` records each such pair as
its own `entities.person_candidate` status (`confirmed_wikidata`) and
merges it through the same `reconcile_person_merges()` machinery as the
tenure merges — same non-destructive guarantee, same union-find handling
if a QID is ever claimed by more than two records. All 4 pairs were
confirmed and merged, bringing the running total to **676 person records
merged into 526 survivors** across both signals combined.
