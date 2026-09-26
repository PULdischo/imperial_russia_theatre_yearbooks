# Chunking test — does a different VIEW of the page decorrelate errors?

2026-09-26. Run at RG's request, after establishing that adding passes
does not help (see below). 44 billed calls, 220,699 tokens — about 4% of a
single 1,024-page pass.

## The question

Three passes of the production prompt expose only about a third of the
errors actually present in pass 1. The rest are **systematic**: the model
makes the same mistake every time, so resampling cannot find them. Does
changing what the model SEES — rather than how often it looks — break that
correlation?

## Method

- 11 of the 12 gold pages. `review_1891-92_SP_ballet_p002` was excluded:
  it is a full-page plate whose only text is a caption printed sideways, so
  horizontal bands would slice it lengthwise. Excluded from BOTH sides of
  every comparison.
- Each page cut into **4 horizontal bands**, with cuts placed at the
  quietest ink row within ±6% of each quarter mark (a gutter between printed
  lines, not a blind fraction), plus 4% page-height overlap each side of a
  seam.
- Production prompt `review_system_lines.txt`, temperature 0, unchanged.
- Bands stitched back by longest-match overlap dedup.
- Scored against gold at word level. **Body text only** — `[figure …]`
  blocks dropped, matching RG's standing decision to handle plates and
  captions separately. Dash spacing normalised on both sides (known
  unstable, not chased).

## Results

2,209 gold body words across 11 pages.

| single pass | word errors | accuracy |
|---|---|---|
| full page, sample 1 | 56 | 97.46% |
| full page, sample 2 | 60 | 97.28% |
| full page, sample 3 | 59 | 97.33% |
| **4-band chunked** | **85** | **96.15%** |

Chunking alone is **worse** than a full-page pass. But the errors are
different ones:

| error overlap | shared | as % of the smaller set |
|---|---|---|
| full page vs full page (resampled) | 53 | **95%** |
| full page vs chunked | 30 | **54%** |

**Resampling the same view reproduces 95% of the same errors.** Changing the
view reproduces 54%. That is the finding.

What that buys, measured as the share of pass 1's 56 real errors that the
combination exposes as a disagreement:

| combination | errors exposed | sites to review | tokens/page | vs today |
|---|---|---|---|---|
| 2x full page | 5/56 (8.9%) | 12 | 11,842 | 0.67x |
| **3x full page — production today** | **22/56 (39.3%)** | **40** | **17,763** | **1.00x** |
| 1x full + 1x chunked (4 bands) | 36/56 (64.3%) | 91 | 25,985 | 1.46x |
| 2x full + 1x chunked (4 bands) | 36/56 (64.3%) | 98 | 31,906 | 1.80x |

Note how little a second sample of the same view adds: **8.9%**.

## Cost: the system prompt dominates, so bands are not cheap

A band call costs 5,016 tokens against a full page's 5,921 — **85% of a full
page for a quarter of the image** — because the system prompt is re-sent with
every band and dwarfs the image. Chunking therefore multiplies cost almost
linearly in band count, not by area.

This makes band count the main cost lever:

| | tokens/page | vs today |
|---|---|---|
| 1x full + 1x chunked at 4 bands (measured) | 25,985 | 1.46x |
| 1x full + 1x chunked at **2 bands** (estimated) | 15,953 | **0.90x** |

**2 bands is the configuration worth testing next** — projected at slightly
BELOW today's cost, while still supplying a decorrelated second view. Its
exposure is unmeasured.

## Caveats — do not over-read this

- **11 pages, 56 errors.** The 39% vs 64% gap is large, but this is a small
  sample and should be confirmed before committing a 1,024-page run.
- **The chunked run used the full-page prompt unchanged**, which asks for
  page-level fields (`printed_folio`, `tailpiece_present`) a band cannot
  supply. 96.15% is therefore a FLOOR for chunking, not its ceiling; a
  band-aware prompt should narrow the 85-vs-56 gap.
- **Chunking has its own failure mode**, visible here: of 68 chunk-only
  errors before the body-text filter, 23 were dropped words in just 4
  contiguous runs, and all 4 were plate captions or text straddling a seam
  (`Импера-/торскаго` split across a cut). This is the same class as the
  Repertoire thread's `--cropped-images` header-band reattachment bug —
  see CLAUDE.md. Seam handling is where a production design would need care.
- Exposure of 64.3% still leaves **36% of errors silent**. Chunking improves
  the ceiling; it does not remove it.

## Relation to the pass-count measurement

Measured the same day on the same gold pages, production prompt: 3 passes
expose 35%, 5 passes 44%, and a 10-replicate config plateaus at ~35% by
pass 7 and is still 35% at pass 10. Adding passes costs linearly and buys
almost nothing past 5. **Chunking is the better lever**, and at 2 bands it
may be free.
