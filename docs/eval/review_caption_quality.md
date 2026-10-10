# Figure captions are the worst-transcribed layer of the Season Reviews

Found 2026-10-10, while scan-checking the 40 candidate title misreads
(`outputs/reviews/mentions/review_title_candidate_misreads.csv`). The
title errors turned out to be a symptom; this is the cause.

## The measurement

Captions are set in a small italic face, quite unlike the body. Counting
*impossible* honorific forms — a digit or a wrong letter where `г-жа` /
`г.` must stand, e.g. `1-жа`, `в-жа`, `і. Аистовъ` — against correct ones,
over `outputs/reviews/merged_full/review_block.csv`:

| block kind | bad | good | bad % | chars |
|---|---|---|---|---|
| **caption** | **68** | 226 | **23.1%** | 77,004 |
| paragraph | 15 | 8,455 | 0.2% | 1,321,677 |
| enumerated_list | 0 | 668 | 0.0% | 58,538 |
| cast_list | 0 | 160 | 0.0% | 9,070 |
| heading / footnote / personnel_news | 0 | 37 | 0.0% | — |

**A caption is ~100x more likely to carry a garbled honorific than a
paragraph.** Read that ratio carefully, though: 23.1% is the share of
*honorific tokens appearing in captions* that are malformed, which is **74
tokens spread over 61 of the 897 caption blocks (6.8%)** — not 23% of
captions. An earlier draft of this file blurred the two; the corrected
figures are here.

The honorific is only a proxy — it is the one error class that is
mechanically detectable, because `1-жа` cannot be a word. It is a lower
bound, not a total: the 34 title misreads fixed on 2026-10-10
(`Камаріо`/`Балдерка`) carried no honorific at all and would never show up
in this count. The true caption error rate is higher than 6.8% and is not
known.

## Why it matters more than the ratio suggests

Captions carry exactly the triple RG wants linked: performer, role and
ballet, in one line — `«Камарго», бал. Сенъ-Жоржа и М. Петипа. / Марія
Камарго (г-жа Леньяни).` Reach into the layers:

- **2,035 of 27,410 mentions (7.4%)** come from `figure` blocks, 1,321 of
  them resolved.
- only **27 of 1,952 assertions (1.4%)** — the assertion grammar needs a
  role—performer dash that captions mostly do not use.

So the damage is concentrated in the mention layer, and it is bounded.

## What was fixed, and what was not

Scan-checked every instance of the two title misreads across all 20 pages
(15 for Камарго, 5 for Баядерка) and applied them through
`pipeline/apply_review_text_corrections.py` — see
`docs/eval/review_text_corrections.csv` for the per-row evidence.

**Not fixed, and deliberately left for its own pass:** the rest of the
caption damage on these same 1900-01/1901-02 SP pages, all of it visible
in the page reads but none of it swept corpus-wide —

| transcribed | the scan reads | page |
|---|---|---|
| `в-жа Леньяни` | `г-жа Леньяни` | p018 |
| `1-жа Эрлеръ 2-я`, `і. Аистовъ` | `г-жа …`, `г. Аистовъ` | p019 |
| `М. Петина` | `М. Петипа` | p023 |
| `Сент-Жоржа` | `Сенъ-Жоржа` | p030 |
| `Донъ Германдресъ` | `Донъ Германдесъ` | p028 |
| `г-жа Вили` | `г-жа Виль` | p021 |
| `1-жа Рощъ` | `г-жа Рошъ` | p032 |
| `1-жа Сидова` | `г-жа Сѣдова` | p017 |
| `г. Бекефіи` | `г. Бекефи` | p013 |

Two cautions that came out of the same reads and are the reason this is a
separate pass rather than a regex:

1. **`Талорачва` (p005 caption) vs `Толорагва` (p020 body)** — the same
   Bayadère role, spelled two ways *in the print*. Both transcriptions are
   correct. Likewise `Мадгавая` (p017 body) against `Магдавая` (p020
   body). Normalising these would destroy real source variation; see
   [[never-assume-spelling-consistency]].
2. **`Модславая` (p013 caption)** — the scan reads something closer to
   `Мадгавая`, but the letterforms are genuinely hard at this size and I
   am not confident between `Мадгавая` and `Мадсгавая`. Left alone,
   flagged for RG.

## The option worth costing

The captions were extracted by the same single pass as the body. A
caption-specific re-extraction pass — cropping the caption band and
prompting for small-italic text — is the structural fix, and it is a
billed Vision run. Not started; needs RG's go and a cost estimate first.


## The re-extraction was tried, and it does not work (2026-10-10)

Hypothesis: `run_reviews.py` does no client-side resizing, but a page costs
~5,170 prompt tokens, so the service downscales it and the small italic
falls below legibility. Cropping the caption band should buy back ~10x the
effective resolution for the same tokens.

**Falsified.** `pipeline/caption_reextract.py` + `pipeline/platefind.py`
cropped the caption band from a located plate, upscaled 3-4x, and read it
with a caption-specific prompt in three different crops. 93 calls over the
20 pages hand-verified earlier that day, $0.06.

| | impossible honorific tokens, 29 captions |
|---|---|
| current corpus text | **17** |
| re-extracted, tight crop (4x) | 27 |
| re-extracted, wide crop (3x) | 25 |
| re-extracted, deep crop (3x) | 26 |

The crop is **worse than what we already have**. On the title word, across
63 readings of a caption whose print demonstrably says `Камарго`:
`Камаріо` 60, `Камарю` 2, `Камарго` 1. `Баядерка` did better — 15 right
against 6 `Балдерка` — but unreliably.

Two things worth recording:

1. The prompt explicitly said *"the honorific is NEVER a digit; if a mark
   looks like `1-жа` it is `г-жа`"*. The model emitted `1-жа` anyway, in
   every view. Instruction did not reach it.
2. The crop introduced **new** errors absent from the corpus: `Пѣтина` for
   Петипа, `Слѣдова`/`Спѣдова` for Сѣдова, `Бекефі`/`Бекефн` for Бекефи,
   `Летатъ`/`Лелятъ`/`Лєгатъ` for Легатъ. The wider crops also pulled body
   text from below the plate into the caption.

So this is not a resolution problem. At 4x zoom on a tight crop a human
reads these captions easily; the model cannot read this italic face at any
scale we can give it. **Do not buy the full 897-caption pass** — the $2.33
would make the corpus worse. The pilot cost 6 cents and settled it.

### What is left

- **A different model.** Untested. There is no `ANTHROPIC_API_KEY` in
  `.env`, so Claude would need a key added; `qwen3-vl-max` is reachable on
  the existing DashScope key and would cost ~$0.20 for the same 29
  captions.
- **Fix the matching, not the text** (free). RG's purpose is linking, not
  a verbatim caption. `1-жа` has exactly one possible reading, so the
  matcher can normalise it at match time — recovering the honorific path,
  and with it gender and list membership, for ~74 names — without editing
  a single character of the stored text. Caption mentions currently
  resolve poorly (`bare` 358/716, `honorific-list` 75/247) against 63.7%
  overall, so there is room here.
- **Hand transcription** of the 897 captions. Reliable, and the only route
  to a correct caption layer, but it is real time rather than money.
