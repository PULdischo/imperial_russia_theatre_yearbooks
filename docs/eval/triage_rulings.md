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

## Running tally

| | |
|---|---|
| pages triaged | 3 of 10 |
| rulings | 12 |
| RG agreed with Claude's reading | 12 of 12 |
| **2-run majority WRONG** | **6 of 12** (женщину, Вдали, Шарпантье, Легатъ, Мартьяновъ, Пребраженская) |
| **all three passes wrong together** | **1** (бокаловъ) |
| **a pass silently DROPPED text** | **1** (p027, six names from the narrow columns) |

The three passes find WHERE to look and cannot decide WHAT is right. Majority
vote would have corrupted three readings and could never have caught бокаловъ,
where all three agreed on the same wrong word. Every ruling needs the scan.

Half the majority failures are ъ/ь confusions (Шарпантье, Легатъ, and the
gold-set Карльсонъ before it) — the same trap that recurs in RG's own
transcription. Worth watching for specifically.

The other recurring pattern: **the model reaches for the commoner word.**
Мартыновъ for Мартьяновъ, женщицу for женщину, Преображенская for the
page's own misprint Пребраженская. Where two passes agree on a plausible
word and one dissents, the dissenter is worth a look.
