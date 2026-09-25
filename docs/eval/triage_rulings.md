# Triage rulings — RG's readings on disagreement-flagged passages

Format: one row per disputed spot. "runs" is what the three pilot passes
returned. "ruling" is RG's, from the scan. Anything without a ruling is
still open.

## review_1896-97_SP_ballet_p018  (two-page spread, folios 248+249)

Montage layout — overlapping photographs with text threaded around them.
`docs/season_reviews.md` §8 names 1896-97 BalletSP idx 12–18 as the hardest
known cluster in the corpus; this is idx 18.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | женщицу / женщину / женщицу | **женщину** (RG) | 2-run majority was WRONG |
| 2 | Влали / Влали / Вдали | **Вдали** (RG) | 2-run majority was WRONG |
| 3 | бакалы / баклы / бакалы | **бокаловъ** (RG) | ALL THREE runs wrong — consensus is not correctness |
| 4 | цыгами / цыгами / щипами | **LOOK UP IN THE ORIGINAL VOLUME** (RG) | obscured by an overprinted photograph, not merely faint |

Cosmetic, not raised: em-dash spacing (`меня»,—ласково` vs `меня», — ласково`)
and apostrophe type (`L'argenterie` vs `L’argenterie`).


## review_1897-98_MSK_ballet_p004  (folio 376)

Clean, well-printed, single-column. All disputes are ordinary misreads.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | Шарпантье / Шарпантъе / Шарпантъе | **Шарпантье** (RG) | 2-run majority WRONG — the ъ/ь trap again |
| 2 | откланиваются / откланиваются / откликаются | **откланиваются** (RG) | |
| 3 | устроенному / устроенному / устроенномъ | **устроенному** (RG) | |
| 4 | тутъ / tутъ / тутъ | **тутъ** (RG) | run 2 used a LATIN t |

Structural, needs no ruling: run 2 lumped the page's `б) в) г) д)` items into one
paragraph where runs 1 and 3 split them. `segment_reviews.py` fixes this
downstream for free.

The three-line dancer list under the photograph was captured by all three runs,
in the figure's caption. The body-text comparison excludes captions by design
(RG, 2026-09-25: plates and captions set aside for separate handling).

## Needs checking against the physical volume

The scan cannot settle these — a photograph is printed over the text, so no
amount of magnification recovers it.

| page | passage | what is missing |
|---|---|---|
| `review_1896-97_SP_ballet_p018` (folio 248) | `влекайся играми, ?нцами…` | the word after `играми,`. Ends `-нцами`; sense suggests `танцами` ("amuse yourself with games and dances"), but the letters are covered by an overprinted photograph. Runs guessed цыгами / цыгами / щипами — all three unreliable. |


## review_1901-02_SP_ballet_p027  (folio 193)

A photograph with narrow text columns wrapping down BOTH sides — the same
text-around-figure layout as page 07 of the gold set. That accounts for the
structural disagreement between runs.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | Легатъ / Легать / Легать (x4) | **Легатъ** (RG) — hard sign | 2-run majority WRONG; ъ/ь again |
| 2 | Мартыновъ / Мартыновъ / Мартьяновъ | **Мартья-**\n**новъ** (RG) | 2-run majority WRONG. `Мартыновъ` is the far commoner surname, which is probably why two passes produced it. |
| 3 | Преображенская / Пребраженская / Пребраженская | **both, as printed** (RG) | The page prints Преображенская at full width and Пребраженская in the narrow column. Run 1 silently normalised. Added to `docs/eval/genuine_print_typos.md`. |

**Run 1 dropped text.** Runs 2 and 3 both carry `Сланцова, Павлова 1-я,
Конецкая, Леонова 2-я, Спрышинская, Георгіевская` from the narrow columns;
run 1 does not. This is the failure class that matters most, and no
consensus vote could have found it — only the disagreement signal did.

## review_1899-00_SP_ballet_p028  (folio 109)

An easy page: one photograph, three short enumerated items, runs nearly
identical. The 0.800 stability score was almost entirely dash spacing.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | (nothing) / (nothing) / `„Лукья-` | **ignore — printing artefact** (RG) | Something IS printed before `Лукья-`: at 6x, a small filled square above a comma-shaped mark, between the comma after `2-й` and the `Л`. Does not look like `„` (which is two comma shapes side by side). RG: "it's a printing artifact. It doesn't have any semantic meaning." Runs 1 and 2 were right to omit it. Confirmed by the next line: the item runs on to `новъ; г-жи Петипа 1-я и Петипа 2-я.` with NO closing quote anywhere, and item 4 begins cleanly. A similar speck sits after `Леньяни.` in item 4 — debris on this part of the page, not type. |

Not raised, dash spacing only: `ambassadeurs — гг.` (runs 1,2) vs
`ambassadeurs— гг.` (run 3), three times over.

**Outside the body text, for when captions are picked up:** all three runs
read the photo caption as `Camargo (1-жа Леньяни)` — a `1` where the page
prints `Г-жа`. All three wrong, so no disagreement flags it. Captions are
set aside per RG, 2026-09-25.

## review_1897-98_SP_ballet_p003  (folio 239)

«Дочь микадо» — a Japanese-themed ballet, and the page that produced the
"do not normalise names you recognise" prompt rule (commit 19f5071).
Photograph with a narrow text column beside it.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | Сень-Нинъ / Сенъ-Нинъ / Сень-Нинъ | **Сенъ-Нинъ** (RG) — hard sign | 2-run majority WRONG. ъ/ь again. Both halves of the name end the same way, twice over. |
| 2 | Оёдоровъ / Оедоровъ / Ѳедоровъ | **Ѳедоровъ** — fita | settled from the scan; RG delegated |
| 3 | Юриtomo / Іориtomo / Иориtomo | **Іори-**/**томо** | settled from the scan; RG delegated. The page prints it in italic CYRILLIC across a line break. ALL THREE passes romanised it. |

Also on this page and NOT raised, now handled automatically: Миkado,
Каsatkina, Бакерkina, Новоbrачные, ввеsti, поdарками, подnоситъ — the same
romanising failure, caught by `repair_mixed_script` or flagged by it.

Structural, no ruling needed: run 1 put the figure's caption text into a
body block where runs 2 and 3 put it in the figure caption, which accounts
for most of run 1's apparent extra words.

## review_1895-96_SP_ballet_p014  (folio 246)

Montage of six overlapping photographs with the text in a column at right.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | Оомичевъ / Оомичевъ / Ꙋомичевъ | **Ѳомичевъ** (RG) — fita | **ALL THREE WRONG.** Run 3 produced Ꙋ (archaic "uk"), a letter not in this typeface. The model is NOT blind to fita — four lines down it reads `Ѳедуловъ` and `Ѳедоровъ 1-й` correctly in the same column. It failed on the rarer name. `Ѳомичевъ` appears nowhere else in the 200-page pilot. |

Structural, no ruling: run 2 classified the caption text as a `figure`
block where runs 1 and 3 used body paragraphs. Nothing was dropped — the
body-only comparison simply does not see caption text.

## review_1899-00_SP_ballet_p027  (folio 108)

Short page: one photograph, four lines of text beneath it.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | Пре-/ображевская / Пре-/ображенная / Пре-/ображанская | **Пре-**/**ображенская** (RG) | **ALL THREE WRONG, in three different ways.** The page prints the standard spelling plainly. |

Not raised: apostrophe type in `L’arrivée` (runs 1,3 curly) vs
`L'arrivée` (run 2 straight).

**This one complicates the rarity story.** Ѳомичевъ and Іоритомо were rare
names the model did not know. `Преображенская` is the opposite — one of the
commonest names in the corpus — and all three passes still corrupted it,
each differently, none matching the page or each other. The likely cause is
the letter shapes rather than the word: `-ображенская` is six rounded
characters in a row.

**Compare page p027 of 1901-02**, where the page genuinely printed
`Пребраженская` and one pass silently normalised it to the standard form.
Here the page prints it correctly and all three passes corrupted it. Same
name, opposite errors — and only the scan tells them apart.

## Running tally

| | |
|---|---|
| pages triaged | 7 of 10 |
| rulings | 18 |
| RG agreed with Claude's reading | 18 of 18 |
| **2-run majority WRONG** | **7 of 16** (женщину, Вдали, Шарпантье, Легатъ, Мартьяновъ, Пребраженская, Сенъ-Нинъ) |
| **all three passes wrong together** | **4** (бокаловъ, Іоритомо, Ѳомичевъ, Преображенская) |
| **a pass silently DROPPED text** | **1** (p027, six names from the narrow columns) |

The three passes find WHERE to look and cannot decide WHAT is right. Majority
vote would have corrupted three readings and could never have caught бокаловъ,
where all three agreed on the same wrong word. Every ruling needs the scan.

Half the majority failures are ъ/ь confusions (Шарпантье, Легатъ, and the
gold-set Карльсонъ before it) — the same trap that recurs in RG's own
transcription. Worth watching for specifically.

**Five of the seven majority failures are ъ/ь** (Шарпантье, Легатъ,
Сенъ-Нинъ, plus the gold-set Карльсонъ). This is the corpus's single most
reliable trap, for the model and for RG alike.

The other recurring pattern: **the model reaches for the commoner word.**
Мартыновъ for Мартьяновъ, женщицу for женщину, Преображенская for the
page's own misprint Пребраженская. Where two passes agree on a plausible
word and one dissents, the dissenter is worth a look.


## Resuming

**Next:** pages 5–10 of the first ten, from `outputs/reviews/triage_queue.txt`
(20 body-text pages below 0.95 in the 200-page pilot; ~103 expected across
the full 1,024).

**How this runs** (agreed 2026-09-25): Claude compares the three passes,
resolves what is unambiguous, and brings RG only genuine character
disagreements, with image crops. RG rules. Claude does NOT get the last
word on pre-reform orthography.

**Already handled automatically, do not re-surface:**
- Latin letters stranded in Cyrillic words — `parse_reviews.py` repairs the
  certain ones and flags the rest; every case is listed in
  `outputs/reviews/mixed_script_review.csv`.
- Numbered/lettered item boundaries — `segment_reviews.py`, downstream.
- Dash spacing and line-break placement — known unstable, not chased.
- **Printing artefacts** — stray ink, specks, foul type. RG, 2026-09-26:
  ignore them, they carry no semantic meaning. Distinct from `<d>` damaged
  type, which is a real character poorly inked.

**Set aside for separate handling:** plate pages and figure captions.


## Rarity predicts the consensus failures

RG, 2026-09-26, on the all-three-wrong cases: "notice these are unusual
words/names." Measured against word frequencies across the 200-page pilot:

| word | times in 200 pages | failure |
|---|---|---|
| Іоритомо | 0 | all three wrong |
| Ѳомичевъ | 0 | all three wrong |
| бокаловъ | 1 | all three wrong |
| откланиваются | 1 | majority wrong |
| женщину | 2 | majority wrong |
| Мартьяновъ | 3 | majority wrong |
| Вдали | 4 | majority wrong |
| Шарпантье | 8 | majority wrong |
| Ѳедоровъ | 10 | majority wrong |
| Легатъ | 33 | majority wrong |

**All three consensus failures sit at the very bottom.** That matters
because the disagreement signal is structurally blind to them — it can only
find passages where the passes differ.

**But rarity alone is not a usable filter.** 64% of the pilot's distinct
vocabulary appears exactly once, and the median word frequency is 1,
because the corpus is mostly dancers' surnames. Flagging every rare word
would flag most of the text.

**A fourth consensus failure complicates this.** `Преображенская` is one of
the commonest names in the corpus, and all three passes still corrupted it,
each differently. Rarity did not predict that one; the letter shapes
probably did — `-ображенская` is six rounded characters in a row. So rarity
catches some consensus failures, not all.

The useful reading is that there are **two complementary signals for two
different failures**:

- **rarity** predicts the consensus failures, which nothing else detects;
- **ъ/ь** predicts the majority failures (5 of 7), which disagreement does
  detect.
