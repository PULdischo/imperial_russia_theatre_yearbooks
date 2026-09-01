# Gold set — season reviews (prose)

Twelve hand-transcribed pages, the reference against which season-review
transcription runs are scored. Design and rationale: `docs/season_reviews.md`
(§11 for the eval, §7 for the fidelity rules the transcription must follow).

This is the prose counterpart to `docs/eval/gold/`, which covers the tabular
pipeline. It is **not** built by a script — unlike the roster and repertoire
gold, which is generated from hand-coded Python data structures, these are
typed directly from the scans.

## How to use

One `.txt` template per page, each with the page image beside it in
`images/`. Each template carries the transcription rules in its own header,
so you do not need to consult the spec while typing.

Fill in the `[FIELDS]` block, then transcribe the page under `[BLOCKS]`.

## Two rules that matter more than the rest

**Type from the scan, never from model output.** These templates are
deliberately blank. Pre-filling them from an extraction run would turn
transcription into correction, and you would unconsciously ratify the
model's readings — at which point the gold stops measuring anything.

**Reproduce errors exactly.** If the 1897 typesetter misspelled a French
word, type the misspelling. Silently fixing it while making the gold means
the eval will later mark the model *wrong* for being right, and the prompt
would be tuned against a corrupted reference.

## Full pages only

Never excerpts. A partial page makes "where does the gold end" ambiguous and
reintroduces the row-alignment failure documented as known issue #21 — which
made the tabular pipeline's reported accuracy look like ~14% error when the
real figure was ~1.9%.

## Coverage

The twelve are chosen to span scan setups, resolution extremes, layout
hazards and typographic conventions — not sampled at random. A deliberately
hard set measures worst case; corpus-wide behaviour comes from the structural
checks in `docs/season_reviews.md` §10, not from extrapolating these scores.
