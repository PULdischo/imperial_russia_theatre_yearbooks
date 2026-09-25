# Season Reviews — verbatim diplomatic transcription

Status: **design complete; pipeline stages 1-6 built, 2026-08-30.** Not yet
run beyond a one-page smoke test. Written 2026-08-28.

Implemented so far:

| Script | Does |
|---|---|
| `pipeline/render_reviews.py` | renders 1,024 pages + manifest (done: 1.3GB) |
| `pipeline/schemas/review.py` | the LLM-facing contract + flattener |
| `pipeline/prompts/review_system.txt` | extraction prompt (+ `_plain` ablation twin) |
| `pipeline/run_reviews.py` | batch driver, DashScope **and** Anthropic |
| `pipeline/parse_reviews.py` | validate, repair, flatten to CSV |
| `pipeline/quality_checks_reviews.py` | structural checks incl. missing pages |
| `pipeline/gold_reviews.py` | parser for the hand-typed gold files |
| `pipeline/eval_reviews.py` | alignment-based scorer |
| `pipeline/build_review_outputs.py` | TEI + Markdown + searchable text |

Findings from the smoke test are triaged in
`docs/eval/known_issues_reviews.md`.

The *Ежегодникъ Императорскихъ театровъ* carries, in each volume, narrative
reviews of the season for Russian drama, opera, ballet and French drama, in
both St. Petersburg and Moscow. This document specifies the pipeline that
turns the scanned reviews into a **verbatim diplomatic transcription**.

This is a **parallel track** to the tabular pipeline described in
`docs/pipeline.md`, not an extension of it. The `raw` schema's contract is
"one row per printed appearance"; continuous prose does not fit that shape
and should not be bent into it.

**Scope of this pass: transcription only.** Entity linking, cast-list
parsing, and section classification are deliberately deferred (§12).

---

## 1. Corpus

41 PDFs in `pdf/Reviews_Season/`, **1,024 pages**, 17 seasons.

Naming rule, uniform across all 41 files:

    <season>_SeasonReview_<Genre><City>.pdf

`Genre` ∈ {`Ballet`, `Opera`, `All`}; `City` ∈ {`SP`, `Moscow`}. The wider
set `RussianDrama` / `FrenchDrama` is reserved but unscanned (see below).

**`FrenchDrama` pairs only with `SP`.** The French troupe played the
Mikhailovsky in St. Petersburg and had no Moscow counterpart, so a
`FrenchDramaMoscow` file cannot exist. Russian drama, opera and ballet all
have both cities. A filename combining `FrenchDrama` with `Moscow` is an
error, not a gap, and the manifest builder should reject it.

Adding a season later is: drop a correctly-named file in the folder and
re-run. Discovery is by filename; rendering is idempotent.

Note this differs from the rest of the corpus, which uses a `ForUpload_`
prefix. That prefix is a meaningless upload-batch artifact; the reviews'
scheme is the better one and the parser accepts both.

### Coverage

| Genre | Files | Pages |
|---|---|---|
| Ballet | 32 | 674 |
| Opera | 7 | 240 |
| All (combined volumes) | 2 | 110 |

Ballet is complete for all 17 seasons × 2 cities, counting the two seasons
whose ballet coverage sits inside a combined volume.

### Known absences — permanent, not gaps to fill

- **1898-99 has no season reviews at all.** That issue was truncated for
  administrative reasons. This is a structural fact about the publication,
  not a scanning gap. Do not re-flag it.
- **No standalone Russian drama or French drama reviews are scanned**, and
  none are wanted — spoken drama is out of scope. Drama text that happens to
  fall inside the two combined volumes *is* transcribed, because those
  volumes are transcribed whole.

### The two combined volumes

`1890-91_SeasonReview_AllSP.pdf` (85 pp) and
`1899-00_SeasonReview_AllMoscow.pdf` (25 pp) are not organised by art form.

- **AllMoscow** runs drama → opera → ballet. Ballet begins mid-page and
  mid-paragraph on page index 20 (printed folio 204), immediately after
  `…Леонковалло (1 опера) по 2 представленія.`, and runs to the end.
- **AllSP** is chronological, production by production, with genres
  interleaved. Ballet appears in at least four separate stretches
  (approx. idx 13–29, 42–44, 70–75, 84), *plus* ballet material embedded
  inside opera sections — idx 67 credits Л. И. Ивановъ with the dances in
  Gounod's «Ромео и Джульетта».

Both are transcribed **whole**. No page-range filtering: a page-range filter
would have discarded the Ивановъ credit, and lossy filtering at extraction
time cannot be audited later.

**The genre-named files are not cleanly bounded either.** 1897-98 BalletSP
opens mid-way through the previous section's personnel list and ends by
beginning `Французскій театръ.` Section membership is therefore a
paragraph-level annotation (§12), never a page range.

### No duplicate pages

All 1,024 pages were perceptually hashed and cross-compared. The high
correlations that surfaced were all false positives (dense text pages share
a texture). No page appears in two files.

---

## 2. Output model

**Unit of output:** one document per (season × city × genre).

**Layers**, each derived from the one above, mirroring the `raw` → `analysis`
discipline of the tabular pipeline:

1. **Per-page JSON** — the model's only contract. Verbatim, diplomatic.
2. **TEI XML** — the source of truth for the edition; citable, depositable,
   schema-validated.
3. **Markdown** — the daily reading and grepping copy.
4. **Searchable text** — line-rejoined (see §7), derived by rule.

Layers 2–4 are *renderers*. Any change to formatting, markup convention, or
output format is a re-render from JSON already on disk, never a
re-extraction. This is the same reasoning as the flatten boundary documented
in `CLAUDE.md`: extraction is paid and non-deterministic, so the model's
contract stays stable and every downstream decision remains revisable.

**This pass produces files only.** No `reviews` schema in the DuckDB file;
that can be built from the JSON later without re-extraction.

---

## 3. Page-level fields

| Field | Notes |
|---|---|
| `page_id` | `review_<season>_<city>_<genre>_p<NNN>` |
| `printed_folio` | The **printed** page number. See the hazard in §9. |
| `tailpiece_present` | Boolean. Tailpieces reliably mark section ends. |
| `no_text` | True only when the page carries nothing transcribable. |
| `copy_artifacts` | Library stamps, pencil foliation — see §9. |
| `reading_order_uncertain` | Flags the page for human review (§8). |

`no_text` is reserved for genuinely blank pages and plates with no caption.
A plate **with** a caption is not textless — it is a `figure` block whose
caption transcribes normally.

`no_text` is the highest-risk false positive in the whole design, because
many full-page plates carry their captions set **vertically**, and rotated
text is a common thing for a vision model to skip entirely. The ink-coverage
check (§10) must scrutinise `no_text` pages hardest.

---

## 4. Block taxonomy

Every block carries: type, text, position (§8), and a stable index within
the page.

| Type | Notes |
|---|---|
| `heading` | Includes lettered subsections (`в) Балетъ.`) and ornamental headpieces containing **printed** text. **NOT run-in introducers** — see below |
| `paragraph` | Running prose — the bulk |
| `verse` | Quoted poetry. **Exempt from line-rejoining**; indentation NOT preserved (§7) |
| `cast_list` | Role → performer runs, prose-set or block-set |
| `personnel_news` | `Приняты на службу:` / `Оставили службу:` / `Умерли:` / transfers. **Provisional** — see below |
| `enumerated_list` | See below |
| `figure` | Subtyped (plate, photograph, notated example, ornament-with-printed-text); caption transcribed verbatim |
| `footnote` | Kept with its page, in printed order, at the foot |
| `byline` | Rare; appears only in later seasons |
| `other` | **Catch-all. Never discard text.** |

### Headings are rare, and introducers are not headings

**RG, 2026-09-24, and this is the general rule, not a ruling on one phrase:
"If I tag them, it will be because of what they say, not their formatting."**

The vision pass records **form** — what the printer did. Meaning is assigned
**later, from the finished text**, where it can be revised for free. So
`Танцовали:`, `роли исполняли:` and `исполнено было:` are `paragraph`: in
form they are run-in sentence openings, set in the same type as the prose
they belong to. That they *function* as introducers to the list below is a
statement about content, and content is the later pass's job (deferred item 1
already splits `enumerated_list` the same way).

This is also the test for whether any future field belongs in the extraction
prompt at all. `lang` failed it — "which language is this" is a question
about meaning, and it turned out to be answerable from the characters
downstream at 100% rather than from the model at 10%. Разрядка, bold and
italic pass the test in principle, being purely typographic; разрядка fails
in practice for separate reasons (see below).

The model over-applies `heading` to exactly these introducers — across five
runs of the `seg2` prompt it called `Танцовали:` a heading every time, and
twice promoted a figure caption as well. Actual headings across the twelve
gold pages: **one** (`Балетъ.`, page 06), which the model finds 5 times in 5
without needing разрядка — short text alone on a line is cue enough.

**This will change.** Headings stay rare in the season reviews proper, but
jubilee and obituary material (not yet in the corpus) carries many more, so
the block type earns its place and the convention is worth fixing now rather
than after those volumes arrive (§13).

`other` is load-bearing: without a legal home, unclassifiable text is text a
model will quietly drop. Anything unrecognised goes into `other` verbatim and
is flagged for review.

### Engraved signatures inside ornaments are not transcribed

The rule that "an ornament containing text gets its text transcribed" means
**printed** text — a framed headpiece like `ИМПЕРАТОРСКІЕ МОСКОВСКІЕ ТЕАТРЫ`,
set in type inside a decorative border.

It does **not** cover an engraver's signature drawn into the plate itself
(1907-08 BalletMoscow p160 carries one reading approximately
`Грав: И. Гескій.`). Those are part of the artwork, in the way an artist's
signature on a painting is: cursive, drawn rather than set, and functioning
as authorship of the image rather than as text on the page.

Decided 2026-09-09 (RG). Three reasons: they are image, not typography;
transcribing engraved cursive would yield mostly `<unclear>`, which is
low-value uncertainty polluting a metric that matters; and engraver
attribution is peripheral to the research question. They remain recoverable
from the page images if ever wanted.

A vignette carrying only such a signature is therefore recorded by
`tailpiece_present` alone, with no `figure` block.

### `personnel_news` is provisional

The name describes one very particular kind of paragraph — the colon-led
blocks announcing who joined, left, transferred or died — and it may not
survive long-term. Its scope is deliberately **narrow**: benefits, jubilees
and honours are ordinary narrative sentences and stay in `paragraph`.
Widening it would pull arbitrary prose in and blur the boundary that makes
the type findable at all.

Retiring it later costs nothing. The type is a label on blocks whose text is
captured verbatim either way, so collapsing `personnel_news` into `paragraph`
— or renaming it again — is a data operation over JSON already on disk, not a
re-extraction. Nothing downstream should assume the label is permanent.

### `enumerated_list`

Three printed forms, one structure (*label → performers/creator*):

- **Numbered** — `1)`, `2)`, `3)` — most common
- **Cyrillic-lettered** — `б) Solo de Diane chasseresse`, `в) Scènes de chasse`
- **Bare-labelled, no enumerator** — `Solo de Vénus — …; Entrée de l'Étoile polaire — …`

Store the **enumerator verbatim as its own field** (possibly empty). Without
it, "was this numbered or bare?" is unrecoverable and reclassification means
returning to the scans.

Nesting occurs: `23) Variations: a) г. Н. Легатъ; b) г-жа Сѣдова; …`
(Latin sub-letters inside a numbered item).

Semantically these fall into at least two families — production credits
(scene → designer) and divertissement programmes (dance → performers) — but
**form and meaning do not align**: costume and property credits are the same
semantic family, printed as plain prose. Classify by *form* here; classify
semantics later in a text pass (§12).

### `footnote`

Capture the **anchor** as well as the note. A faithfully transcribed footnote
whose anchor is lost no longer records which sentence it belonged to. TEI
attaches the note at its anchor; Markdown keeps it at the page foot.

---

## 5. Inline spans

Span attributes, all **captured always, rendered conditionally**:

- `razryadka` — letter-spaced emphasis
- `bold`
- `italic`
- `lang` ∈ {`ru`, `fr`, `de`, `it`, `la`}
- `damaged` — **gold-only** (see below)

### `damaged` is not uncertainty

`damaged` marks type that is poorly printed — faint, smudged or broken — but
confidently read. `uncertain` marks a reading we are not sure of. These are different claims — one about
the page, one about our confidence — and conflating them would corrupt the
uncertainty metric, since the eval compares gold's uncertainty flags against
the model's.

The extraction prompt never asks the model for `damaged`, so **it is never
scored**. It exists to be diagnostic: with badly printed type labelled in gold,
we can ask afterwards whether the model's character errors cluster on poorly
inked passages, which is exactly the kind of question a raw error rate cannot
answer. Renders as TEI `<damage agent="inking">`.

**Span text is always the normal unspaced word.** Styling is metadata on top
of it, never expressed as literal spacing. A model emitting
`К ш е с и н с к а я` would poison the transcription and every search over
it; a validator flags any token matching a single-char-plus-space pattern.

### Разрядка vs. justification

Pre-reform typesetting widens **word** spacing to justify lines. Разрядка
widens **letter** spacing within a word and carries meaning. The rule: gaps
*between words* are justification and mean nothing; gaps *between letters
within a word* are разрядка.

1899-00 AllMoscow p20 is a narrow column beside a plate, heavily justified —
the canonical false-positive trap, and in the gold set for that reason.

### What emphasis actually marks — and why it is not reliable

Empirically, across volumes:

- **bold** marks work titles at first mention (`«Евгеній Онѣгинъ»`, `«Сильфида»`)
- **italic** marks figure captions *and* French terms in running prose
  (`Pas de deux`, `Groupes et scène`)
- **разрядка** marks headings (`Б а л е т ъ.`) and, in some volumes, the
  French titles inside enumerated lists

But **the convention is not stable across the corpus.** The same job — marking
a dance title — is done by разрядка in 1899-00, by italic in 1897-98 Moscow,
and by *nothing at all* in 1902-03 BalletSP, where French titles sit in plain
roman. Typography alone therefore cannot find titles. **Script detection can**, on
every volume and regardless of how the printer set them — a Latin-script run
is a Latin-script run whether it is letter-spaced, italic, or plain roman.
This was originally the argument for the `lang` tag; it is now the argument
for not needing one (see "Language" below).

### Language — Russian vs non-Russian only, and not the model's job

**RG, 2026-09-24: the only distinction she needs is Russian vs
non-Russian.** French vs Italian vs German is not required, now or later.

That collapses the whole problem, because the distinction she wants is
**recoverable from the characters themselves**, with no model involvement:

| | |
|---|---|
| model asked to tag `lang` | **10%** recall (5 of 52 spans) |
| script detection over the gold text | **100%** (48/48) |
| script detection over the model's text | ~80%, and every miss is a place the model misread the characters, not a tagging failure |

All 52 lang-tagged spans in the gold contain Latin letters and **zero**
contain Cyrillic. The rule is exact, deterministic, free, and runs over text
already on disk, so it never costs a vision call and can be re-run whenever.

**Therefore `lang` is dropped from the extraction prompt** (`seg2_trim.txt`,
2026-09-24). Nothing is lost that RG wants. This supersedes the earlier
rationale on this page — that the `de` slot had to exist to "protect the
French set" from mislabelling, and that French-vs-Italian was the
distinction that mattered for ballet. Both were reasoning about a
requirement RG has since said she does not have.

The `Lang` enum stays in `schemas/review.py`: it costs nothing unused, gold
pages already typed carry `<l fr>` tags, and reinstating the field later
would otherwise mean a schema change. Nothing populates it from vision.

**A language-ID pass remains available and RG explicitly wants that door left
open** ("we can do one later if it's helpful"). It is cheap to add whenever:
it runs over finished text, needs no vision call, and can be iterated or
thrown away without re-extracting anything. The point of dropping `lang` from
the prompt is not that the distinction is worthless — it is that identifying
French vs Italian is a *text* problem that should not be paid for at vision
time, where it also measurably competes with transcription accuracy.

### What the gold set does and does not represent

Measured 2026-09-24 against 60 non-gold pages, stratified across all 41
season/city/genre groups and all 17 seasons:

| | gold (12 pages) | out of sample (60) |
|---|---|---|
| pages containing an enumerated list | 42% | **17%** |
| items carrying a printed enumerator | 85% | 81% |

The enumerator ratio generalises. **The prevalence of lists does not** — the
gold set over-represents list-heavy pages by roughly 2.5x, because those
pages were deliberately chosen to stress the hardest layouts. A day of
prompt work on segmentation was therefore work on about a sixth of the
corpus, and anyone reading the eval numbers should scale their sense of the
problem accordingly.

Worse, segmentation measured on the gold does not survive contact with
unseen pages. On the gold the model marked all 47 enumerators. Out of
sample it marked **29 while its own transcribed text contained 90** — it
reads the items correctly and files two thirds of them as ordinary prose.
That is the overfitting risk of tuning against twelve pages, measured
rather than feared.

Bold is a second, opposite case: the gold contains exactly **one** bold
mark, which is a sampling artefact and not a fact about the corpus (RG,
2026-09-24: bold is not uncommon). Bold recall therefore cannot be measured
from this gold set at all, in either direction.

### The governing rule

**Base text accuracy outranks every annotation.** If the annotation-heavy
prompt measurably degrades plain-text character accuracy, the annotations go
and the transcription stays. This is tested directly (§11), not assumed.

---

## 6. Alternate casting

Two printed conventions for the same fact:

- **Parentheses** — `бѣлая жемчужина — г-жа Леньяни (г-жа Сѣдова)`
- **`или`** — `г-жа Шишко или г-жа Дьякъ`

A parser that knows only one loses half the dancers. Both must survive
verbatim into the transcription; reconciling them is a later concern.

---

## 7. Fidelity rules

For a diplomatic transcription, **the model's helpfulness is the enemy.**
Vision models are trained to produce clean, modern, sensible text, and every
rule below marks a place where "sensible" destroys evidence.

**Punctuation is preserved exactly, never normalised.** The corpus uses both
guillemets (`«…»`, U+00AB/U+00BB) and German-style quotes (`„…"`,
U+201E/U+201C) — sometimes in the same volume. Em dash (U+2014), en dash
(U+2013) and the line-end hyphen (U+002D) are typographically distinct here
and must not be flattened. Naming the codepoints makes this mechanically
checkable by character-frequency comparison against gold.

**Spacing around the em dash is a known limit of the source, not signal.**
The corpus shows all three forms — `Робертъ—г. Мордкинъ` (flush both sides),
`свита —воспитанники` (apparent gap before only), `Коломбина — г-жа Гордова`
(apparent gaps both sides). It is tempting to treat that variation as
meaningful. It probably is not reliably recoverable.

An em dash is cast on a full-em body and its stroke does not fill that body,
so the sort carries side bearing that looks like a space even where none is
set. Justification stretches whatever spaces exist, compounding it. At the
resolution of these scans the two causes cannot be told apart.

Measured impact, over the first three hand-typed gold pages: 16 em dashes in
2,618 characters, of which only **2** carry an adjacent space at all. Even
assuming every one of those two is transcribed wrongly, that is **0.08% CER**
— about a twentieth of the error rate ordinary transcription produces, and
0.61% in an implausible worst case where every dash is disputed.

Two consequences follow. Transcribe what looks right and do not agonise: the
flush cases, which are the large majority, are unambiguous anyway. And do
**not** build dash-spacing normalisation into the eval — it would be
machinery, and a place for a bug, in service of a distinction worth eight
hundredths of a percent. What deserves that attention instead is ъ/ь, which
is more frequent, invisible to the automated checks, and produces a genuinely
wrong character rather than an unresolvable ambiguity.

**Abbreviations are never expanded.** `г-жа`, `г.`, `всп-ца`, `б-тъ`. A model
that writes out `госпожа` has fabricated text that is not on the page.
Expansion belongs in a derived layer (§12) — and "cleaned" there means
expanding abbreviations, *not* modernising orthography. ъ/ѣ/і/ѳ/ѵ stay
everywhere, per the project's standing rule.

**Printer's errors stay.** If the typesetter misspelled a name, the
misspelling is data. 1897-98 BalletMoscow p381 prints
`Solo de Saturne et de ses 4 sattelites` — doubled *t*, for *satellites*. It
must survive.

This creates a distinction the prompt must draw explicitly: **"I cannot read
this" (legibility) is uncertainty; "this looks wrong" (implausibility) is
not.** Collapsing them turns a printer's error into an `<unclear>`, and from
there into a correction.

**Illegible text is flagged, never guessed.** Three states:

1. Confident → plain text
2. Partially legible → best reading **plus** an uncertainty flag
3. Unreadable → explicit gap marker with an extent estimate and **no invented
   characters**

Flags accumulate in a review queue carrying the printed folio, surrounding
text, **and a cropped image of the exact spot**, so a case can be settled from
the queue rather than by hunting through a 140 MB scan.

A suspiciously *low* flag rate is itself a warning: near-zero uncertainty
across 1,024 pages means confabulation, not success.

**Line breaks and hyphenation are preserved as printed** in the diplomatic
layer — including end-of-line hyphens (`возобновле-` / `ніемъ`). The
line-rejoined searchable text (§2, layer 4) is derived from it by rule.
Neither fidelity nor usability is sacrificed.

**`verse` is exempt from rejoining.** In prose a line break is a typographic
accident; in verse it is part of the text, and verse line breaks are kept.

**Indentation is NOT preserved. RG, 2026-09-25: "There is very little verse
across the corpus, so I think we can relax it. It's clear when something is
in verse without indentation."**

This reverses the earlier rule on this page, which required four spaces per
level. The measurement that prompted the change: reproducing indentation
cost **0.4pt of corpus CER on its own** — on 1894-95 OperaMoscow p299 it was
the *entire* 9% error for that page, every difference being a run of eight
spaces the model did not emit. That made it the single largest recoverable
chunk of error in the whole eval, and it was never a reading failure.

Concretely: extraction prompts ask for verse line breaks and tell the model
to start every line at the left margin; `eval_reviews.py` collapses leading
whitespace on both sides before scoring (`_relax_indent`). **The gold keeps
its indentation** — it is the verbatim record and costs nothing to retain —
so the decision is reversible without re-typing anything.

---

## 8. Reading order

Reading order is **data, not the accident of array sequence.** Each block
stores its position on the page (at minimum column and vertical rank;
ideally a bounding box). Correcting a mis-ordered page is then a data edit,
not a re-run of a paid, non-deterministic extraction.

A page can score perfectly on characters while being scrambled — which is
invisible if only CER is measured. Reading-order accuracy is therefore its
own metric (§11).

Only genuinely ambiguous pages reach a human: multi-column, text wrapping
around inset figures, montage layouts. Most pages are single-column prose
with exactly one possible order. The review interface is a page thumbnail
with blocks outlined and numbered in the order the model read them —
confirm or renumber, seconds per page, no reading required.

Hardest known cluster: 1896-97 BalletSP idx 12–18, and 1895-96 BalletSP
idx 13–15 (colour photographic montages scattered diagonally).

---

## 9. Copy artifacts and the folio hazard

**Copy artifacts** — library stamps, pencilled archival foliation, any
manuscript addition — are evidence about *this copy*, not the edition.
Presence is noted; they are never transcribed into the reading text.

Observed: a red circular library stamp overprinted on 1900-01 OperaMoscow
idx 15; pencil foliation (`42`, `3`, `3/34`) in the top corners throughout
1893-94 BalletMoscow.

**The folio hazard.** Pencil foliation must never be captured as
`printed_folio`. The printed folio is what makes citation possible
(*Ежегодникъ 1895–96, с. 47*), and this is the one field where the tabular
pipeline had nothing to compare against — `printed_page_number` has been
empty in `manifest.csv` since the beginning because it was not derivable
without reading the page.

Detection cannot rely on typography: the printed folio appears as `— 194 —`
(centred, em-dashes), `151` / `303` (bare, centred), and `160` (bare, left).
The reliable rule is **position at the foot of the type block**, plus a
**sequence check** — folios run consecutively within a file, so any break in
the sequence is flagged. A pencilled `42` captured by mistake breaks the
sequence immediately.

Manuscript text inside a figure (e.g. the Tchaikovsky autograph on AllSP
idx 22) is marked as manuscript-and-uncertain rather than flowing into the
text as though printed. A diplomatic transcription should not silently blur
print and hand.

---

## 10. Known corpus characteristics

**Scan batches.** Five files are photographs of an open book with the
photographer's fingers visible at the fore-edge: 1892-93 OperaSP, 1893-94
BalletSP, 1893-94 BalletMoscow, 1894-95 OperaMoscow, 1895-96 BalletSP,
1896-97 BalletSP. **Verified at full resolution: no text is obscured** — the
fingers sit on margins and below the type block. The real (mild) issue in
these volumes is page curvature and lighting falloff toward the gutter, which
should show as a slightly elevated error rate on inner columns rather than as
missing text.

**Resolution range** spans 1277×1596 (1906-07 BalletMoscow) to 6057×6510
(1901-02 BalletSP). The low end was checked and is **comfortably legible** —
that volume is set in larger type with generous leading, so pixels-per-
character, not total pixel count, is the measure that matters. No rescanning
is needed.

**Layout hazards**, in rough order of risk:

- Vertical (90°-rotated) captions on full-page plates — corpus-wide, not a
  quirk of one volume; some whole plates are printed landscape
- Text wrapping around multiple inset figures
- Colour photographic montages scattered diagonally with a shared caption
- Narrow columns beside plates, heavily justified (the разрядка trap)
- Near-unbroken dense prose (1905-06 BalletSP, 1906-07 BalletSP)

**Structural checks that scale past the gold set** (the analogue of
`quality_checks.py`):

- Ink coverage vs. transcribed character count — catches silent drops,
  especially on `no_text` pages
- Folio sequence continuity within a file — see *Missing pages* below
- Literal letter-spacing leaking into span text
- Punctuation codepoint frequency vs. gold
- Token-length comparison (catches expanded abbreviations)

### Missing pages

The printed folios give the corpus a self-check the tabular pipeline never
had: they run consecutively within a file, so a break in the run means a page
of the printed volume is not in the scan.

The check has to allow for unpaginated pages — some plates carry no printed
folio at all — so the rule is not "folios must increment by one" but:

> Between two consecutive **paginated** scan pages whose folios are *m* and
> *n*, there must be exactly *n − m − 1* intervening **unpaginated** scan
> pages.

Any file where that fails yields a `missing_page_suspected` record naming the
file, the folios either side of the break, the size of the gap, and the two
scan pages that bracket it. A **repeated** folio is reported the same way —
that means a page was scanned twice, or a folio was misread.

The check reports; it does not diagnose. Three causes are mechanically
indistinguishable and only a human with the volume can separate them:

1. the page was never scanned,
2. the page is absent from the physical copy,
3. the folio was misread by the model (the pencil-foliation hazard in §9 is
   the most likely way this happens).

Cause 3 is worth eliminating first, since it is checkable from the scan we
already have rather than from the book.

This runs per file after transcription and writes a review queue alongside
the uncertainty queue from §7. It is cheap, it covers all 1,024 pages, and it
is the only mechanism that can detect a page that was never scanned — no
amount of care during extraction will find something that is not there.

---

## 11. Eval

### There was never an accuracy bar, and there should not be one now

`eval_against_gold.py` has no threshold, target, or pass/fail logic. The
scores in `docs/eval/run_history.csv` functioned as a **regression tripwire**
— interpreted against the previous run, not against a standard. The bar for
the reviews is set the same way: from real numbers, after the first gold
scores, not guessed in advance.

### The alignment lesson — the most important thing carried over

Known issue #21: `eval_against_gold.py` compares gold and predicted rows **by
list position** (`zip()`). On pages where the model correctly found people the
gold excerpt had skipped, every subsequent row compared against the wrong
person. Roughly half of 226 field mismatches were this artifact; hand-
realigning one page made all 14 gold rows match byte for byte. Genuine
isolated content errors were **31/1627 fields = ~1.9%**, not ~14%.

**Prose has an exact analogue, and it would bite harder.** Aligning gold to
prediction by paragraph index means one extra or missing block — a page break
stitched differently, a caption counted as a block — shifts everything after
it and collapses the score while the transcription is perfect.

The fix is to remove the failure mode rather than manage it: compute
character error rate over a **sequence alignment** of the full page text,
which is alignment-free by construction, and compare block structure
**separately** so a structural disagreement is reported as a structural
finding instead of silently poisoning the text score.

### Metrics

1. **CER** over aligned full-page text — the headline number
2. **Block structure** — types, count, order (reported separately)
3. **Reading order** accuracy
4. **Folio** exact match
5. **Span precision/recall** per attribute (разрядка, bold, italic, lang)
6. **Punctuation fidelity** by codepoint frequency

Разрядка is dropped from rendering if span precision falls below ~85%. That
threshold is movable; the point is deciding from a measurement.

### Two experiments before the full run

- **Model bake-off** — `qwen3-vl-plus` (the tabular pipeline's model) vs.
  `claude-opus-5`, 12 pages each. The decisive quality here is not OCR but
  disciplined adherence to negative instructions under a complex schema.
- **Annotation ablation** — the same pages with the annotation-heavy prompt
  and with a plain-transcription-only prompt, compared on plain-text CER. If
  the extras hurt the words, the extras go.

Operational notes: the Batch API halves cost and nothing here is
latency-sensitive; the system prompt is byte-identical across all 1,024 calls
and should be cached.

### Gold set — twelve pages, all verified at full resolution

Hand-transcribed by the researcher, **from the scans, never by correcting
model output.** Pre-filling a template from an extraction run turns
transcription into ratification and stops the gold measuring anything.

**Full pages, never excerpts** — a partial page makes "where does the gold
end" ambiguous and reintroduces the issue-#21 class of bug.

| # | Page | Tests |
|---|---|---|
| 1 | 1897-98 BalletMoscow p9 (folio 381) | Bare-labelled enumeration; italic French; alternates via `или`; `всп-ца`; the `sattelites` printer's error |
| 2 | 1902-03 BalletSP p9 (151) | ~33-item enumeration; nested `a) b) c)`; French **and** Italian; titles in plain roman (unmarked convention) |
| 3 | 1899-00 BalletSP p25 | Разрядка on French titles; parenthetical alternates |
| 4 | 1907-08 BalletMoscow p7 (160) | Footnote with anchor; tailpiece; left-set folio |
| 5 | 1901-02 BalletMoscow p18 (303) | Verse; `„…"` quotes; text wrap around inset photo |
| 6 | 1894-95 BalletSP p0 (194) | Personnel lists with dates; tailpiece; разрядка heading; bold title; section boundary |
| 7 | 1896-97 BalletSP p17 (247) | Reading order — three figures, threaded text; italic French; quoted dialogue |
| 8 | 1906-07 BalletMoscow p6 | Resolution floor |
| 9 | 1905-06 BalletSP p5 (131) | Density ceiling; `Danse „Grossvater"`; 40+ names per item |
| 10 | 1891-92 BalletSP p2 (165) | Full-page plate, **vertical** caption, horizontal folio |
| 11 | 1899-00 AllMoscow p20 (204) | Mid-page genre boundary; heavy justification (разрядка trap) |
| 12 | 1894-95 OperaMoscow p19 (299) | Verse — 11 lines, variable indentation; opera; figure caption |

Deliberately excluded: a German/Wagner page (low research value), and any
occlusion test (nothing in the corpus is occluded).

Effort is balanced deliberately — two long pages, three short, one nearly
free — so typing budget lands on failure modes rather than on repetitive
walls of text.

---

## 12. Deferred until after transcription

1. Semantic classification of `enumerated_list` (production credits vs.
   divertissement programme) — text pass
1b. **Detecting BARE-LABELLED items** — a dance title followed by its
   performers with no printed enumerator. RG, 2026-09-25: "we can later
   identify these lists from the meaning of their content." A pattern rule
   (Latin-script title + em dash) scored 7/8 with no false positives on the
   gold and was rejected anyway: script is a correlate of these titles, not
   the thing itself, and a volume with bare Russian titles would defeat it
   silently. `segment_reviews.py` handles only printed enumerators, which
   ARE the label. See that module's docstring.
2. Cast-list parsing into role → performer pairs, including both alternate
   conventions (§6)
3. Mention detection and entity linking (people, works, events, dates) —
   **a separate pass over finished text, not part of vision extraction**, so
   it can be iterated without re-paying for vision
4. Mention anchoring strategy — deferred safely because stable per-page block
   indices keep both offset-based and surface-form-based anchoring available
5. Whether reviews enter the DuckDB file, and what those tables look like
6. Paragraph-level section tagging — which paragraphs are ballet — reviewed
   against readable text, stored in a derived layer so it stays revisable
7. Abbreviation expansion in a derived "cleaned" layer
8. Whether разрядка / bold / italic / lang are rendered — decided by §11
9. Running heads — none observed; revisit if any turn up

---

## 13. Adding volumes later

**More season reviews will be scanned and added.** This pipeline is designed
to be re-run against a growing corpus indefinitely, not executed once. That
is a standing requirement, not a convenience.

### What must hold

- **Discovery is by filename, never by a list.** No hardcoded file
  enumeration, no hardcoded set of seasons. A new volume is added by
  dropping a correctly-named PDF into `pdf/Reviews_Season/` (§1).
- **Rendering is idempotent** — pages whose image already exists are skipped.
- **Extraction is incremental** — pages that already have raw JSON are
  skipped. Adding one volume costs one volume's worth of API calls, never
  the corpus's.
- **Derivation is total.** TEI, Markdown and the searchable text regenerate
  from *all* JSON on disk, so a new volume integrates without anyone
  hand-merging anything.
- **A re-run must never silently alter existing output.** Transcriptions that
  have been reviewed or corrected are not to be overwritten by a later run
  touching a different file. New work is additive, in the same spirit as the
  `raw` → `analysis` → `entities` → `research` layering.
- **Per-file checks stay per-file.** Folio continuity and missing-page
  detection (§10) are scoped to a single file, so a newly added volume is
  checked on its own terms and cannot be masked by the rest of the corpus.

### Season parsing

The season token is a generic `\d{4}-\d{2}`, so seasons after 1907-08 parse
without change. The validator must accept century rollover — `1899-00` is
well-formed — and should reject a second half that is not the first half plus
one, which is how `1899-90` and `1905-07` reached the tabular manifest.

### Genre vocabulary is closed on purpose

`Ballet`, `Opera`, `All`, plus the reserved `RussianDrama` and `FrenchDrama`
(SP only, §1). A filename carrying an unrecognised genre token should
**fail loudly** rather than be accepted as a new category — otherwise a typo
silently becomes a genre, and the error surfaces much later as a review that
nothing can find.

### Expect the later volumes to differ

The corpus already drifts: combined all-arts volumes in 1890-91 and 1899-00
but nowhere else, photograph-heavy layouts from 1907-08, and bylines that
appear only in the later seasons (§4). The safe posture for any newly added
volume is that it may not look like what came before.

Practically: run the structural checks of §10 on a new volume before trusting
its output, and if it introduces a layout or typographic convention the gold
set does not cover, add a gold page for it rather than assuming the existing
twelve still characterise the corpus. **The gold set is meant to grow with the
corpus, not to be frozen at twelve.**

---

## 14. Open questions

- The accuracy bar (deliberately deferred to first gold scores)
- Whether a genuine table exists anywhere in the corpus. None found so far;
  statistical summaries are set as prose. Enumerated material the model is
  unsure about is flagged into a review queue rather than guessed at.
