# Multi-view merge — how close to a diplomatic transcription without human hours?

2026-09-26. 253 billed calls total (44 + 209), 1,208,467 tokens, ~20% of a
single 1,024-page pass. 11 gold pages (`1891-92_SP_ballet_p002` excluded
throughout — full-page plate with a sideways caption). Body text only
(`[figure …]` blocks dropped), dash spacing normalised on both sides.

**RG's goal, stated 2026-09-26:** *"What I would LIKE is a diplomatic
transcription, but I don't want to have to put in too many human hours to
get there."* This reframes the metric. Error EXPOSURE (what the disagreement
signal shows you) treats review time as free. The right metric is errors
removed **without** human involvement, and then the size of whatever queue
is left.

Metric below: gold body words misread (wrong or dropped). 2,209 words.

## A. Single views — the full page is still the best single view

| view | misread | accuracy |
|---|---|---|
| **full page** | **56** | **97.46%** |
| 6 bands | 63 | 97.15% |
| 2 bands | 70 | 96.83% |
| 3 bands | 74 | 96.65% |
| 4 bands | 85 | 96.15% |
| 8 bands | 104 | 95.29% |

Finer decomposition does NOT improve reading. 8 bands is markedly worse.
Chunking earns its place only as a second opinion, never as a replacement.

## B. Automatic merge — accuracy gained for zero human time

Majority vote across views, full page preferred on ties.

| | misread | accuracy | disagreement sites |
|---|---|---|---|
| one full-page pass | 56 | 97.46% | 0 |
| **vote of 3 RESAMPLES (production today)** | **57** | **97.42%** | 42 |
| vote of 3 views (full + 2band + 4band) | 49 | 97.78% | 193 |
| vote of 5 views | 47 | 97.87% | 232 |
| **vote of 6 views** | **42** | **98.10%** | 180 |

**Voting three resamples of the same view is worth exactly nothing** — 57
errors against a 56-error baseline, i.e. marginally worse than doing
nothing. This is the strongest single result here: today's 3-pass setup
buys no automatic accuracy at all. Its only product is a review queue.

Six distinct views cut errors by 25% for free.

## C. Oracle ceiling — what a better SELECTOR could win

Of the 56 errors in a single full-page pass, how many are read correctly by
at least one other view?

| | recoverable |
|---|---|
| 3 resamples | 12 of 56 (21.4%) |
| 3 views | 29 of 56 (51.8%) |
| **6 views** | **40 of 56 (71.4%)** |

Majority vote captures only 14 of those 40. **The gap between 98.10%
(majority) and ~99.3% (oracle) is the largest available win that costs no
human hours at all** — it is a selection problem, not a data problem. The
right answer is already sitting in the outputs.

`pipeline/orthography.py` already has the correct safety property for this
("a rule may only choose among readings a pass actually produced"), and now
has six candidate readings to choose among instead of three.

## D. The human queue that remains

Merged text leaves 42 misread words. Where must RG look?

| queue rule | sites | residual errors inside | errors per site |
|---|---|---|---|
| every site where views disagree | 180 | 34/42 | 0.19 |
| no outright majority | 38 | 17/42 | 0.45 |
| **3 or more distinct readings** | **32** | **17/42** | **0.53** |

Scaled to the full 1,024 pages (~206,000 body words, factor 93):

| | corpus estimate |
|---|---|
| errors, one full-page pass | ~5,200 |
| errors after 6-view merge | ~3,900 |
| errors at the 6-view oracle ceiling | ~1,500 |
| high-yield queue ("3+ readings") | ~3,000 sites, catching ~1,600 errors |
| exhaustive queue (every disagreement) | ~16,700 sites, catching ~3,200 errors |
| errors NO view ever flags | ~750 |

## The honest bottom line

None of this reaches a diplomatic transcription on its own. 98.10% word
accuracy is roughly 3,900 wrong words across the corpus, and even a perfect
selector over these six views leaves ~1,500. Reviewing every disagreement
site is ~16,700 decisions and still misses ~750 errors that no view flags.

The ordering that serves the stated goal:

1. **Merge multiple views.** Free, no human time, ~1,300 errors removed.
2. **Invest in the selector, not in review.** The oracle gap is ~2,400 more
   errors, also at zero human cost. Biggest remaining win.
3. **A second model** would raise the ceiling itself rather than just
   closing the gap to it — still the highest-value unblock.
4. **Human review last**, on the "3+ distinct readings" queue only.

## Caveats

- 11 pages, 56 baseline errors. Small.
- All views reused the unmodified full-page prompt, which asks bands for
  page-level fields they cannot see. Chunked accuracy is a floor.
- Every view "invents" words (141 for full page, 194–260 for chunked). Much
  of that is caption text the runs transcribe and this scoring excludes from
  gold; some of the chunked excess is my stitcher duplicating across seams.
  The invented-word counts are NOT a clean signal and were not used above.
- Projection onto gold is used for alignment, which is slightly generous to
  every view equally.
- Seam damage is real: text straddling a cut (`Импера-/торскаго`) and plate
  captions are where chunking loses words — the same class as the Repertoire
  `--cropped-images` header-band bug in CLAUDE.md.
