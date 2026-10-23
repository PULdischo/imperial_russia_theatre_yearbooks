# Research questions and data organization (prep for PI conversation)

Companion to `schema.md` (what we capture) and `structural_survey.md` (what
varies in the source). This is about what the data is *for*: what questions
it can answer, which modeling choices serve which questions, and how to
organize it so it's actually usable for research rather than just faithfully
transcribed.

**Working assumption for everything below**: we keep a verbatim/raw layer for
reproducibility and transparency (the `person_entry`/`event_entry`
tables as specified in `schema.md`, provenance-linked to source pages), but
the **derived analysis layer is the primary thing researchers touch day to
day**. The raw layer exists so any derived number can be traced back to the
printed page it came from — not as the main interface.

---

## What questions this data can answer

**Programming/repertoire analysis** (from `event_entry`/`event_entry_performance`):
- Which works dominated the repertoire, and how did the genre mix shift over
  18 years (canonization of specific operas/ballets, decline of one-act
  vaudeville)?
- SP vs. Moscow programming divergence — same taste, or different audiences?
- The Mikhailovsky's French-language repertoire as a distinct marker of
  court/elite programming versus the Russian houses.
- Box-office patterns: receipts by work/genre/theater, and whether later-era
  programming reads as more revenue-driven than the earlier imperial-patronage
  era.
- Calendar patterns: no-performance events, holiday and benefit-performance programming,
  matinee/evening double-bill usage.

**Institutional/organizational history** (Administrators, ProductionTeam,
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

---

## Future directions

Research strands RG has deliberately parked for later. Each entry says what
has already been done, what is left, and where the material is. This is a
list of ideas, not a work queue: data-quality backlog lives in the status
index at the top of `eval/known_issues.md`, and open decisions about how the
research layer models excerpts, mixed bills and supplied works are under its
"Waiting on RG's decision" heading. Re-check any figure below with a fresh
query before quoting it.

### 1. Dancers in operas and dramas; mixed-art-form evenings

RG (2026-09-29): "I will definitely want to follow up on any drama
performances that include ballet or dancers." Broadened 2026-09-30 to any
evening mixing ballet with drama, opera or something else; she called the
opera-ballet mixes "vitally important to my research" (2026-10-07).

- **Done so far:** a systematic sweep of the season reviews
  (`pipeline/find_opera_ballet_crossover.py`, write-up in
  `eval/ballet_in_opera_and_divertissement.md`: 32 passages, ten kinds).
  The reviews' own tallies of evenings shared with opera match the Repertoire
  exactly in 8 of the 9 seasons that give one. The events whose programme the
  Repertoire leaves unnamed (plain «Дивертиссементъ» and similar) were matched
  to review passages where possible (`eval/unnamed_programmes_itemised.md`).
  `research.performance.includes_dance` marks the works a source shows with
  dancers (`pipeline/entity_curation/works_with_dancers.csv`).
- **Parked:** RG plans "a whole investigation later of dramas/plays with
  dancers in them" (2026-10-13). Candidates are being flagged, not decided:
  see the entry «Dramas and plays with dancers: leads for the later
  investigation» in `eval/known_issues.md`.
- **Open threads:** whether ballet dancers appeared in «Мѣщанинъ во
  дворянствѣ» (Moscow, January 1900), which no source seen so far answers.
  The drama and opera reviews that would show more crossover are on the
  scanning and borrowing list in `yearbook_volume_requests.md`.

### 2. Connecting related productions without equating them

RG (2026-10-12): "We'll need to start figuring out ways of connecting
productions without equating them." Her examples: «Млада» (the
Rimsky-Korsakov opera-ballet of 1892 and the Minkus/Petipa ballet on the same
scenario) and «Волшебное зеркало» (Petipa, St Petersburg 1903; reworked by
Gorsky for Moscow, 1905).

- Merging such works hides the difference; leaving them unlinked hides the
  connection. RG's idea is a "parent work" or "canonic work" category that
  related works and stagings sit under.
- **Nothing built yet.** The only work-to-work link in the research layer is
  `excerpt_of_work_id`. One naming clash to settle first: "parent work" already
  means the whole work that an excerpt belongs to.
- Proposed but not agreed: two kinds of link, work-to-work ("same scenario")
  and staging-to-staging within one work ("reworked from"), starting as a
  hand-curated evidence file.

### 3. Checking the Yearbook against the Directorate's own records

Once enough RGIA files (Фонд 497, опись 18) are in hand, compare the
Directorate's internal records with what the Yearbook printed, using the
archive as an independent check on the publication's accuracy rather than
only for one-off name questions. RG flagged this as deliberately out of scope
for now. Request batches and reading notes are in `rgia/README.md` and
`rgia_request_log.csv`.

### 4. Opera season reviews

The opera season reviews are kept and transcribed although opera casts are
not needed now. RG (2026-10-05): "I'll use it someday for future research."
Only 6 seasons have opera reviews (as of 2026-10-09). Opera-history articles
and opera plates in the supplements are not wanted.

### 5. The printing of the Yearbook: compositors and typefaces

Two related strands about the people and materials of the printing house
(Типографія Императорскихъ Спб. театровъ).

**Genuine print typos.** A running collection of confirmed original-print
errors in `eval/genuine_print_typos.md`, kept because RG finds that the
typos "reveal the real human hands/brains that were working on typesetting
more than 100 years ago". Entries are added when a scan check happens to
confirm one; no backfilling.

**A typeface register (RG, 2026-10-21; parked 2026-10-23).** The idea is to
catalogue every typeface used across the corpus and track which ones the
press reused, when it brought in new ones, and when designs changed.

- *Pilot finding:* the 1891-92 title page (page 4 of
  `1891-92_Frontpages.pdf`) uses at least 7 typefaces, possibly 8:
  - A: narrow decorative capitals with curled Ж and К (ЕЖЕГОДНИКЪ)
  - B: wide, light classical capitals (ИМПЕРАТОРСКИХЪ, ТЕАТРОВЪ, probably
    С.‑ПЕТЕРБУРГЪ)
  - C: a sans-serif (Сезонъ 1891—92 гг.)
  - D: a light slab-serif with strokes of even thickness ((ВТОРОЙ ГОДЪ),
    По порученію Дирекціи, ИЗДАНІЕ)
  - E: an ornamental face with a swash И (the Императорскихъ театровъ under
    По порученію)
  - F: the ordinary book typeface (РЕДАКТИРОВАЛЪ, Дирекціи Императорскихъ
    театровъ, the printer's line; also the censor's notice on page 5)
  - G: a bold slab-serif (А. Е. Молчановъ., the only bold line in the main
    block)

  The bold 1893. may be G or a bold sans-serif; the scan is too blurry to
  tell. Families are probably 6 or 7, but a family is defined by the
  foundry's catalogue, not by resemblance. The cover and half-title use
  further faces (the cover is all narrow sans-serif capitals, the title in a
  drop-shadow version).
- *Terminology:* "typeface" for the design; "font" for one size and style of
  it (in metal type, each size was a separate font). Russian *шрифт* covers
  both; *кегль* is the size, *начертание* the style.
- *Scope (counted 2026-10-21):* 4,067 scanned pages in 447 PDFs across 22
  seasons (the 1911-12 folder has none yet), but most pages repeat one design
  per section per season, so the real unit is about 500 designs (about 20
  recurring sections × 22 seasons, about 60 one-off features, 34 front-matter
  files), or roughly 2,000–4,000 lines to log. The number of distinct
  typefaces is unknown; 30–80 is a guess.
- *Plan, if resumed:* (1) the 34 front-matter PDFs first, which builds the
  core list and shows how long each decision takes; (2) one sample page per
  section per season; (3) an automated pass over every page that flags lines
  not matching their section's design; (4) matching against specimen books,
  alongside the rest. Each typeface gets one descriptive entry; each line
  that uses it gets a row with season, page, verbatim text, role on the page,
  bold/italic/small capitals/letterspacing, cap height in mm (measurable from
  the scan's dpi) and a crop image as evidence. Ornaments (rules, vignettes)
  could go in as a separate category. Cropping, measuring and grouping run
  locally at no cost; the matching itself is a human decision made by zooming
  in on distinctive letters, because vision models are unreliable at it.
- *Constraint:* the scan resolution varies by season (600 dpi for 1890-91 and
  1891-92, 300 dpi for some others). At 300 dpi small list type is enough for
  size and weight but marginal for telling similar book typefaces apart; use
  the full-resolution images embedded in the PDFs.
- *Specimen books to look for (leads from memory, not yet checked):* the
  St Petersburg foundry of О. И. Леманъ, «Образцы шрифтовъ словолитни
  О. И. Лемана» (sometimes «…и политипажей», which would also cover the
  ornaments), and Lehmann's journal «Обзоръ графическихъ искусствъ»; the
  rival Revillon foundry (словолитня Ревильона); and А. Г. Шицгал, «Русский
  типографский шрифт», as the standard history. Ask Princeton's Graphic Arts
  Collection first; then РНБ, РГБ, НЭБ, HathiTrust, WorldCat and the
  type-specimen collections at St Bride (London), the Newberry (Chicago) and
  RIT. Search terms: Образцы шрифтов(ъ); словолитня / шрифтолитейня Лемана;
  Леман, Осип Иванович; Schriftproben Lehmann Petersburg; subject heading
  "Type and type-founding -- Russia -- Specimens". The press may not have
  bought from Lehmann; check Revillon if a face isn't there.
