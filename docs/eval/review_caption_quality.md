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
paragraph.** The honorific is only a proxy — it is simply the one error
class that is mechanically detectable, because `1-жа` cannot be a word.
The surrounding names fail at a similar rate.

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
