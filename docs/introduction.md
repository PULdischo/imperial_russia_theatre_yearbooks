# From scanned pages to two datasets: an introduction

A walkthrough of how 144 scanned volumes become a diplomatic transcription
and a linked research dataset, without the implementation detail in
`docs/schema.md` and `docs/pipeline.md`. Written for a reader who knows the
scholarly stakes of transcription and record linkage but hasn't been
tracking the engineering.

## The source

The *Ежегодникъ Императорскихъ театровъ* — Yearbook of the Imperial
Theatres — ran annually from 1890 to 1908, covering the state opera,
ballet, and drama companies in St. Petersburg and Moscow. Each year's
volume is a scanned PDF containing two distinct table families: a
day-by-day performance calendar (work, venue, box-office receipts) and
staff rosters (dancers, musicians, administrators, rank, tenure). ~1,300
pages total, set in pre-1918 orthography — ъ, ѣ, і, ѳ are original
spelling, not scanning artifacts, and are preserved rather than
modernized, for the same reason a diplomatic edition doesn't silently
regularize its source.

## Two layers, decided up front

The project commits early to a two-layer output, and the whole pipeline
exists to fill both honestly rather than conflating them:

- **A diplomatic transcription** — one row per printed appearance,
  verbatim, no silent normalization, no deduplication of the same person
  across years. This is the layer that answers "what does the source
  actually say," and it's the one everything else is checked against.
- **A linked research dataset**, built on top, where record linkage has
  actually been done: the same real person, work, or venue recognized
  across its many separate printed appearances. This is the layer that
  answers repertoire- and prosopography-shaped questions — how often was
  a work revived, what was a given dancer's full attested career — which
  the diplomatic layer deliberately doesn't attempt on its own.

Every step below is in service of one or the other.

## Stage 1 — Rendering

Each PDF is rasterized to one image per page. Resolution turned out to
matter more than expected: an early pass at 150dpi produced recurring
character-level misreads (digit transpositions, confusable Cyrillic
letterforms); re-rendering at 300dpi eliminated nearly all of them. Worth
noting because it's the first of several points where "just run the OCR"
undersells how much the capture step itself affects downstream accuracy.

## Stage 2 — Transcription by a vision-language model

Each page image goes to a vision-language model — a system trained
jointly on images and text — prompted per table family to return a
transcription in a fixed structured shape (the fields in `docs/schema.md`)
rather than free text. This is closer to structured OCR with a schema
constraint than to captioning: the model is asked for `family_name`,
`rank_or_title`, `tenure_note_text`, and so on, not a paragraph
description of the page.

Treat this stage the way you'd treat any single-pass transcription by a
fast, tireless, occasionally-wrong reader: useful, necessary, and not
trustworthy on its own. Its known failure modes are catalogued rather than
assumed away — sampling non-determinism on dense tables (the same page
transcribed twice can yield different completeness), and field-boundary
confusion on ambiguous visual hierarchy (deciding where a heading ends and
a person's specific role begins is a typographic judgment call the model
doesn't reproduce reliably). Both are documented in `docs/eval/known_issues.md`
rather than silently patched over.

## Stage 3 — Validation and normalization into tables

Each page's transcription is validated against the schema and flattened
into corpus-wide tables — a roster family and a repertoire family, since
their information shapes differ. Anything that fails validation is logged
to its own record rather than dropped, so a schema mismatch on one page
never silently loses data or takes down the batch.

## Stage 4 — Quality assessment, two registers

No single-pass transcription is assessed as correct by assumption. Two
complementary checks run:

- **Gold-standard evaluation.** A 12-page hand-transcribed ground truth
  set — deliberately including the structurally hardest cases in the
  corpus, not a convenience sample of easy pages — gives a real accuracy
  score per run (currently 86.7% field-level match on the full corpus,
  with the gap concentrated in recall on the performance calendar, not
  content accuracy on what's transcribed).
- **Gold-free structural self-consistency checks**, which scale past the
  12 pages an answer key exists for: does a heading recur where the schema
  says it shouldn't, do tallied credit counts sum correctly, does a
  multi-week calendar page implausibly show zero closed dates (real
  theaters had dark nights; a page with none is a completeness flag, not
  a fact).

Findings from both are kept in a running ledger
(`docs/eval/known_issues.md`) triaged by cause — genuine model error,
inherent model non-determinism, or a gold-transcription inconsistency —
so a fix can be judged by whether it moved the aggregate score, not by
whether it resolved the one example that prompted it.

## Stage 5 — The diplomatic transcription, packaged

Once validated, everything assembles into the verbatim dataset proper —
one row per printed appearance, citable back to its source page and image.
It's shipped in parallel formats rather than one: a portable analytical
database, a workbook for pivot-table-style exploration, and a
one-note-per-page reading vault for close reading and annotation. Same
underlying rows throughout; the choice of format tracks the tool a given
collaborator already works in, not a difference in the data.

## Stage 6 — Record linkage into the research dataset

The diplomatic layer treats every printed appearance as its own row on
purpose — collapsing them prematurely would mean guessing at identity
before the transcription was even verified. Record linkage happens as a
separate, later pass, staged by confidence rather than run as one
undifferentiated matching pass:

- **Exact, normalized matches auto-resolve.** Orthographic variants are
  folded (ѣ→е, і→и) and matched as one unit *together with* the source's
  own homonym-disambiguating ordinal ("Ивановъ 2-й") — preserved rather
  than normalized away, specifically so two different attested people
  sharing a surname are never collapsed into one just because a later
  appearance dropped the ordinal.
- **Near matches go to human adjudication, never auto-merged.** A
  Levenshtein-bounded candidate pool (spelling drift the exact-fold pass
  wouldn't catch) is exported as a reviewable pairlist with a similarity
  score and the two source contexts side by side — the actual review
  happens in an ordinary spreadsheet, not a bespoke interface, and nothing
  merges without an explicit yes. A confirmed merge is recorded
  non-destructively: both identifiers remain valid, one is marked
  superseded rather than deleted, so nothing that already cited a given
  identifier breaks.

Repertoire works and venues go through an analogous resolution: a revived
work correctly collapses to one canonical identity across seasons (that's
a feature of the record-linkage design, not a bug — a researcher studying
repertoire wants revivals recognized as the same work), while genre
metadata is deliberately *not* folded across languages, since the
Mikhailovsky's French-language troupe genuinely printed French genre
abbreviations, and collapsing those into their Russian equivalents would
erase a real distinction, not just noise.

## Where this stands

The diplomatic transcription is complete across the full corpus. Record
linkage is live for venues (essentially solved, six known venues) and
works (canonicalization-based, low ambiguity); the person-linkage
candidate pool has been generated and is awaiting the human adjudication
pass described above. `docs/research_dataset.md` has the full entity-
resolution design; `docs/entity_centric_model.md` sketches a proposed next
iteration of the research dataset's table structure, not yet built.

Nothing here is being treated as a closed, one-shot process — the known-
issues ledger and the run-history log both exist specifically so accuracy
is tracked and improved across iterations, not asserted once and left
unexamined.
