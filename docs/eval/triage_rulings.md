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


## Running tally

| | |
|---|---|
| pages triaged | 2 of 10 |
| rulings | 8 |
| RG agreed with Claude's reading | 8 of 8 |
| **2-run majority WRONG** | **3 of 8** (женщину, Вдали, Шарпантье) |
| **all three passes wrong together** | **1** (бокаловъ) |

The three passes find WHERE to look and cannot decide WHAT is right. Majority
vote would have corrupted three readings and could never have caught бокаловъ,
where all three agreed on the same wrong word. Every ruling needs the scan.

Two of the three majority failures were ъ/ь confusions (Шарпантье, and the
gold-set Карльсонъ before it) — the same trap that recurs in RG's own
transcription. Worth watching for specifically.
