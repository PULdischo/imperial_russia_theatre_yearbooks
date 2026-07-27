# Research questions and data organization (prep for PI conversation)

Companion to `schema.md` (what we capture) and `structural_survey.md` (what
varies in the source). This is about what the data is *for*: what questions
it can answer, which modeling choices serve which questions, and how to
organize it so it's actually usable for research rather than just faithfully
transcribed.

**Working assumption for everything below**: we keep a verbatim/raw layer for
reproducibility and transparency (the `roster_entry`/`performance_session`
tables as specified in `schema.md`, provenance-linked to source pages), but
the **derived analysis layer is the primary thing researchers touch day to
day**. The raw layer exists so any derived number can be traced back to the
printed page it came from — not as the main interface.

---

## What questions this data can answer

**Programming/repertoire analysis** (from `performance_session`/`performance_work`):
- Which works dominated the repertoire, and how did the genre mix shift over
  18 years (canonization of specific operas/ballets, decline of one-act
  vaudeville)?
- SP vs. Moscow programming divergence — same taste, or different audiences?
- The Mikhailovsky's French-language repertoire as a distinct marker of
  court/elite programming versus the Russian houses.
- Box-office patterns: receipts by work/genre/theater, and whether later-era
  programming reads as more revenue-driven than the earlier imperial-patronage
  era.
- Calendar patterns: dark days, holiday and benefit-performance programming,
  matinee/evening double-bill usage.

**Institutional/organizational history** (Administration, ProductionTeam,
TheaterSchoolStaff):
- Bureaucratic growth — headcount and rank-class distribution over time (the
  survey already shows role hierarchies deepening 1890→1907).
- Turnover and tenure-length patterns by department/role; professionalization
  of technical roles (decorators, machinists).

**Career/prosopographical research** (BalletArtists, Musicians — the most
exciting angle, and the one with the sharpest modeling tradeoff, below):
- Career longevity, workload evolution, genre crossover (dancers appearing in
  operas), honorific timing.
- Named-role casting history for specific ballets, aggregated at the season
  level.

**Economic history**: revenue trends, genre profitability, correlation
between receipts and repertoire choices over time.

---

## Where modeling choices cut against each other

**Entity resolution (people across years) is the central tradeoff.** We
deliberately did not deduplicate people across volumes — each roster
appearance is its own row, faithful to one printed year. Right call for
transcription accuracy, but it's a hard blocker for every career/biographical
question above: "how long did a dancer's career last" requires linking the
same person across up to 18 volumes, and pre-reform Russian name variants
(patronymic sometimes omitted, ordinal suffixes like "1-я"/"2-я"
disambiguating within one year but not necessarily stable across years) make
that real entity-resolution work, not a join.

**Recommendation for the PI**: scope this explicitly as its own workstream if
prosopography is a priority. Start conservative (exact name + overlapping or
adjacent tenure dates), attach a confidence score to every link, and never
silently auto-merge. This is exactly the kind of judgment call that belongs in
the derived layer — the raw layer stays untouched, one row per printed
appearance, and a `person_id` crosswalk table sits on top of it as a separate,
versioned, revisable artifact.

**The source itself limits date-level casting.** Printed Repertoire tables
never name performers — only work, genre, and receipts. BalletArtists
named-role credits are season-level aggregates ("Спящая красавица
(Аврора)—21"), not per-date. "Who danced Aurora on March 3, 1898" is not
recoverable from this source at all — a source limitation, not something the
schema can fix. Worth setting that expectation with the PI now.

**Verbatim-only fields make cross-year aggregation brittle.** Theater name,
genre abbreviation, department/position are all subject to spelling and
orthography drift across 18 years. "Count all ballet performances 1890–1907"
needs a normalization/controlled-vocabulary layer sitting *alongside* the
verbatim text in the derived tables, not replacing it in the raw ones.

---

## Data organization

### Two layers, one source of truth

- **Raw/verbatim layer** — exactly `schema.md`'s tables, immutable, one row
  per printed appearance, provenance-linked to `page_id`. This is the
  reproducibility/transparency guarantee: every number in the derived layer
  traces back to a specific page.
- **Derived/analysis layer** — built *from* the raw layer via versioned SQL
  transforms, not hand-edited. Normalized categorical columns (theater,
  genre, department, position — verbatim value kept alongside a
  `*_normalized` column, never overwritten), resolved entities where that
  work has been done (`person_id`, with confidence), computed fields (parsed
  receipts as numeric rubles+kopecks or a single kopeck-integer total, season
  as a sortable value, etc.).

### Storage: DuckDB

Single-file embedded database — no server to run, easy to hand someone a
`.duckdb` file and have them query it immediately (via the CLI, Python,
R, or a notebook), and fast enough for the aggregation-heavy queries this
research will mostly consist of (group-by-season, group-by-theater, joins
across a few thousand rows). Two schemas inside one file: `raw` and
`analysis` (or two attached databases if we want to distribute them
separately later). Keep the eval gold-set CSVs and the extraction scripts
outside the database — they're pipeline inputs/tooling, not the dataset
itself.

### Interface: a small Streamlit/Gradio app on top

Modeled on the HuggingFace Data Studio idea — not a data-entry tool, a
*browsing and querying* surface: pick an entity type, filter by season/city/
department, see results in a table, click through to the source page image
for verification, drop into a raw-SQL box for anything the filters don't
cover. Since DuckDB is a single file, this app can run anywhere once the
`.duckdb` file is downloaded — it doesn't need to stay connected to wherever
the extraction pipeline ran. Detailed in `pipeline.md`.

### Documentation

- `schema.md` should function as the living data dictionary for the raw
  layer; add a companion section (or file) documenting the derived layer's
  normalization rules and controlled vocabularies once those exist.
- Keep an explicit **known-limitations** note visible from the front door of
  the docs (no per-date casting, Julian dates only as printed, orthography
  variance, people not deduplicated by default) so a researcher doesn't
  mistake a source limitation for a data-quality bug.
- If this heads toward publication or shared reuse beyond the immediate
  group, raise versioning and a persistent identifier (e.g., a dated release
  on Zenodo) with the PI early — much easier to set up now than to retrofit
  after the fact.
