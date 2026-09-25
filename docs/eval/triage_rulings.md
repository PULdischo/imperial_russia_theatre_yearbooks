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

## review_1895-96_SP_ballet_p025  (folio 257)

One illustration with a caption, then solid prose. Five character disputes.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | Аслинь / Аслинъ / Аслинъ | **Аслинъ** (RG) — hard sign | ъ/ь again |
| 2 | Легать / Легать / Легатъ (x3) | **Легатъ** | applying RG's ruling from 1901-02_SP_ballet_p027; 2-run majority WRONG |
| 3 | Леньяни / Леньяни / Леняни | **Леньяни** (RG) | Pierina Legnani; run 3 dropped the soft sign |
| 4 | каре / карэ / каре | **карэ** (RG) | 2-run majority WRONG — gave the MODERN spelling where the page has э |
| 5 | шіеся / шіесъ / шіесъ | **шіеся** (RG) | 2-run majority WRONG; run 1 alone right |
| 6 | running head transcribed / omitted / omitted | **omit** (RG) | runs 2 and 3 right. Convention for the whole corpus — see below |

### Running heads — DECIDED: not transcribed

RG, 2026-09-26: **"We do not need to include the running head in the seasons
that include them."** This settles the design note that had been left open
("Return to this if you see it in one of the Yearbooks and we'll decide").

The head on this page sits at the foot in small caps:
`ЕЖЕГОДНИКЪ ИМП. Т. 1895–1896 ГГ.`, beside the folio `— 257 —` and a
signature mark `17`. Run 1 transcribed it; runs 2 and 3 omitted it, and
were right.

It is page furniture: identical on every page of a volume, and carrying
nothing the manifest does not already record. Note the phrasing — only SOME
seasons print one, so this is not a rule that fires everywhere.

Applies to all 1,024 pages. The folio itself is still captured, in
`printed_folio`, which is a separate thing.


## review_1906-07_MSK_ballet_p008  (folio 240)

Illustration at left with text wrapping round it, then full width below.
14 disputes.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | открытіи занавѣсъ / открытіи занавѣсъ / открытомъ занавѣсѣ | **открытомъ зана-**/**вѣсѣ,** (RG) | 2-run majority WRONG; run 3 alone right |
| 2 | юбилияръ / юбиляръ / юбилияръ | **юбиляръ** (RG) | 2-run majority WRONG; run 2 alone right. Claude first read the scan as "юбилярь" with a SOFT sign and was corrected by RG at 9x. |
| 3 | капельмейстеръ / капелмейстеръ / капельмейстеръ | settled by rule | run 2 dropped the ь |
| 4 | театралъ / театраль / театралъ | settled by rule | |

### What the юбиляръ misread cost, and what it taught

Claude read the scan as `юбилярь`, declared all three passes wrong, and
"fixed" `orthography.py` to treat -арь/-ярь as a soft-sign class. RG read it
at 9x as `юбиляръ` — a hard sign — which was right.

Everything that followed from the misread was therefore wrong, and is
reverted:

- It is a 2-run-majority failure, not a consensus failure. Run 2 was right.
- The orthography rule's ORIGINAL answer (hard consonant takes ъ) was
  correct all along.
- The suffix "fix" was doubly wrong. `арь`/`ярь` cannot decide anything:
  январь and словарь take ь, but пожаръ and самоваръ do not. It also broke
  `пожаръ`, which had passed only because of a separate bug — the test ran
  on the stem, so `пожар` never met `арь`.
- A first attempt at the same fix added bare `нь`/`ль`/`рь`, which flipped
  `Аслинъ` and `театралъ`, both already ruled the other way by RG.

`orthography.py` now carries a 12-case self-test built from RG's actual
rulings, which is what should have gated the change in the first place.

## review_1901-02_MSK_ballet_p024  (folio 309)

Plate mid-page; body text in two blocks above and below it. 3 disputes.

| # | runs 1 / 2 / 3 | ruling | note |
|---|---|---|---|
| 1 | Конекъ-Горбункѣ / Конекъ-Горбункѣ / Конькѣ-Горбункѣ | **Конькѣ-Горбункѣ** (RG) | 2-run majority WRONG; run 3 alone right |
| 2 | Федорова / Фёдорова / Фёдорова | **Ѳедорова** (RG) | **ALL THREE WRONG.** Fita, no ё. All three passes wrote Ф; they disputed only the ё. |
| 3 | Открытие / Открытіе / Открытие | **Открытіе** (RG) | 2-run majority WRONG; run 2 alone right, and the і-before-vowel rule agreed independently |

The title case is the sharper of the three: four lines below the disputed
word the same page prints the genitive `Конька-Горбунка`, which all three
passes transcribed correctly. Having the right stem elsewhere on the page
did not help any of them at the top.

`Ѳедорова` is the fifth consensus failure and the second fita one after
`Ѳомичевъ`. Nothing in the machinery could have caught it: the passes did
not disagree about the first letter, so the disagreement signal was silent
there, and no orthographic rule distinguishes Ѳ from Ф — that is lexical,
not phonological. It was found only by reading the scan. Note also that the
"never normalise a name because you recognise it" instruction was already
in the production prompt when these passes ran.

## Running tally

| | |
|---|---|
| pages triaged one at a time | 10 of 10 — calibration set COMPLETE |
| rulings | 29 |
| RG agreed with Claude's reading | 29 of 30 — one disagreement: юбиляръ |
| **2-run majority WRONG** | **13 of 27** (женщину, Вдали, Шарпантье, Легатъ x2, Мартьяновъ, Пребраженская, Сенъ-Нинъ, Аслинъ, шіеся, Леньяни, карэ, Конькѣ-Горбункѣ, Открытіе) |
| **all three passes wrong together** | **5** (бокаловъ, Іоритомо, Ѳомичевъ, Преображенская, Ѳедорова) |
| **a pass silently DROPPED text** | **1** (p027, six names from the narrow columns) |

The batched pass over the remaining 8 queue pages adds 66 more rulings —
18 further majority failures and 12 further all-three-wrong readings, 3 of
which were never flagged as disputes at all. See "Batched triage" below.

The three passes find WHERE to look and cannot decide WHAT is right. Majority
vote would have corrupted three readings and could never have caught бокаловъ,
where all three agreed on the same wrong word. Every ruling needs the scan.

Half the majority failures are ъ/ь confusions (Шарпантье, Легатъ, and the
gold-set Карльсонъ before it) — the same trap that recurs in RG's own
transcription. Worth watching for specifically.

**Five of the seven majority failures are ъ/ь** (Шарпантье, Легатъ,
Сенъ-Нинъ, plus the gold-set Карльсонъ). This is the corpus's single most
reliable trap, for the model and for RG alike.

The other recurring pattern: **the model reaches for the commoner or more
MODERN form.** Мартыновъ for Мартьяновъ, женщицу for женщину,
Преображенская for the page's own misprint Пребраженская, and каре for the
printed карэ — that last one is a pre-reform spelling the model quietly
modernised, which is the exact failure the verbatim rule exists to prevent. Where two passes agree on a plausible
word and one dissents, the dissenter is worth a look.



## Batched triage — the remaining 10 queue pages

RG, 2026-09-25: "switch to the batched form now", after the ten
one-at-a-time calibration pages agreed 29 of 30. Batched = every dispute on
a page read against the scan and brought as one consolidated list per page,
instead of one crop at a time. RG still rules; crops go with anything
consequential or surprising.

Two queue pages — `review_1897-98_SP_ballet_p015` and
`review_1902-03_SP_opera_p034` — carried nothing but spacing/punctuation
differences and produced no rulings.

**63 flagged disputes across 8 pages, plus 3 errors found only by reading
the scan that the disagreement signal never saw.** 66 rulings.

### review_1902-03_SP_opera_p010  (folio 117, Rimsky-Korsakov's «Сервилія»)

| runs 1 / 2 / 3 | ruling | note |
|---|---|---|
| Сервиліи, / Сервилии, / Сервилии, (x3 places) | **Сервиліи,** | 2-run majority WRONG each time |
| Сервилія, / Сервиля, / Сервилія, (x3 places) | **Сервилія,** | run 2 dropped the і |
| Сервиліей. / Сервилей. / Сервилией. | **Сервиліей.** | all three differ; run 1 right |
| палъ / паль / паль | **палъ** | 2-run majority WRONG; ъ/ь |
| силою / силой / силой | **силой** | majority right |
| Сервилія тушитъ / Сервиля тушить / … | **Сервилія тушитъ** | run 2 wrong twice in one token |
| Неволя / Неволея / Неволея | **Неволея** | majority right |
| запертум / запертыймъ / запертыймъ | **запертымъ** | **ALL THREE WRONG** |

### review_1901-02_MSK_ballet_p020  (folio 305)

| runs 1 / 2 / 3 | ruling | note |
|---|---|---|
| хвостѣ / хвость / хвостѣ | **хвостѣ** | |
| подводнаго / подводного / подводного | **подводнаго** | 2-run majority WRONG — the genitive modernised from -аго to -ого, the same "reach for the modern form" pattern as карэ/каре |

### review_1900-01_MSK_opera_p015  (folio 251, Cui's «Анджело»)

| runs 1 / 2 / 3 | ruling | note |
|---|---|---|
| Анджело (x6 places) | **Анджело** | runs 1+2 wrote Андржело at 3 of the 6; majority WRONG there |
| говоритъ / … / говорить | **говоритъ** | |
| сообщаетъ / … / сообщается | **сообщаетъ** | |
| женщицу / женщицу / женщину | **женщину** | 2-run majority WRONG — same word RG ruled on before |
| слышать / слышать / слышатъ | **слышатъ** | 2-run majority WRONG; ъ/ь |
| просить / просить / проситъ | **проситъ** | 2-run majority WRONG; ъ/ь |
| напасть / напасть / нарасть | **напасть** | |
| Анджело объщаетъ / Андржело обѣщаетъ / Анджело объщаетъ | **Анджело обѣщаетъ** | **ALL THREE WRONG as tokens** — each half was gettable, no pass got both |
| офѣпенѣніи / офпенійніи / офѣпенѣніи | **оцѣпенѣніи** | **ALL THREE WRONG** — ц read as ф |

### review_1906-07_MSK_ballet_p001  (folio 233)

| runs 1 / 2 / 3 | ruling | note |
|---|---|---|
| Волиничь. / Волининъ. / Волиничь. | **Волининъ.** | 2-run majority WRONG; run 2 alone right |
| Арендсъ. (x2 places) | **Арендсъ.** | |
| ІЕдоро вой / Єедоровой / Єедоровой | **Ѳедоровой 2-й** | **ALL THREE WRONG** |
| ІЕдоро ва / Єедорова / Єедорова | **Ѳедорова 2-я** | **ALL THREE WRONG** |
| ІЕдорова / Єедорова / Єедорова | **Ѳедорова 2-я** | **ALL THREE WRONG** |
| (not flagged — all three agreed) | **Аѳонасьева** | **ALL THREE WRONG, SILENT.** All wrote Аво-/насьева. Found only by reading. |
| Дирижировалъ / Дирижеровалъ / Дирижеровалъ | **Дирижеровалъ** | runs 2+3 right. The page prints Дирижеровалъ here and Дирижировалъ twice elsewhere — a print inconsistency, candidate for genuine_print_typos.md |

### review_1900-01_MSK_opera_p023  (folio 219)

| runs 1 / 2 / 3 | ruling | note |
|---|---|---|
| Ксеніи—г-жѣ / Ксениі—г-жѣ / Ксеніи—г-жѣ | **Ксеніи—г-жѣ** | |
| (not flagged — all three agreed) | **Ѳеодора** | **ALL THREE WRONG, SILENT.** All wrote Феодора; the page prints Ѳео-/дора. |

### review_1894-95_MSK_opera_p023  (folio 303)

| runs 1 / 2 / 3 | ruling | note |
|---|---|---|
| ударять / ударяетъ / ударяетъ | **ударяетъ** | |
| пожарь / пожаръ / пожаръ | **пожаръ** | the orthography rule's original answer, re-confirmed |
| tushinцы / тушинцы / тушинцы | **тушинцы** | Latin intrusion, run 1 |
| Украйнцевъ(г. / Украинцевъ(г. / Украинцевъ (г. | **Украинцевъ(г.** | run 2 exactly right; the print sets the paren tight, with no space |
| хоромы) Спасеные / хоромы)Спасены / хоромы)Спасены | **Спасенье тамъ!** on its own verse line | **ALL THREE WRONG** — wrong word AND all three ran it onto the stage-direction line |

### review_1893-94_SP_ballet_p021  (folio 251)

All ten flagged disputes go to runs 1+2. Run 3 carried a systematic `ІѲ`
corruption on every fita name on the page (Ѳедорова x3, Ѳедуловъ,
Ѳедоровъ x2) and Latin `kova` twice (Горшенкова, Потайкова). Also
`сатурнъ—г.` (not гг.) and Cyrillic `гг.`

| (not flagged — all three agreed) | **Мартьяновъ** | **ALL THREE WRONG, SILENT.** All wrote Мартъяновъ with a hard sign; the page prints ь. The same name RG ruled on earlier from a different page. |

### review_1901-02_MSK_ballet_p002  (folio 287)

| runs 1 / 2 / 3 | ruling | note |
|---|---|---|
| Мендесь / Мендесь / Мендесъ (x5 places) | **Мендесъ** | 2-run majority WRONG all five times; ъ/ь. The final letter matches the ъ of `старикъ` two words later on the first instance. |
| Валиничь. / Валиничь. / Валиниъ. (x2 places) | **Валининъ.** | **ALL THREE WRONG**, twice |
| бабочкъ / бабочкъ / бабочекъ | **бабочекъ** | 2-run majority WRONG |
| представленся / представляется / представляется | **представляется** | |
| ing / нимъ / нимъ | **нимъ** | Latin intrusion, run 1 |
| друг.; / друг.; / др.; | **друг.;** | |
| Галатъ, / Галать, / Галатъ, | **Галатъ,** | |

Note on the first row of p002: run 3 alone had the letters of
`Мендесъ; старикъ-` right but dropped the end-of-line hyphen, so no pass
reproduced the token exactly.

**`Валининъ` (1901-02 Moscow) vs `Волининъ` (1906-07 Moscow)** — same
dancer, different vowel, two volumes. Both stay verbatim; this is recorded,
not reconciled.

### Batch tally

| | |
|---|---|
| pages with rulings | 8 (2 more had spacing differences only) |
| rulings | 66 — 63 flagged disputes + 3 found only by reading |
| **2-run majority WRONG** | **18** |
| **all three passes wrong** | **9 flagged + 3 silent = 12** |

## Fita: a worklist, NOT a rule — RG, 2026-09-25

I counted, across the 200-page pilot, how often each pass wrote Ф or В on
stems I had listed as "fita-taking" (Ѳедор-, Ѳедул-, Ѳом-, Аѳон-, Ѳеодор-,
Ѳеофан-, Ѳекл-, Ѳадде-), and reported 42–45% per pass as an error rate.

**That figure is withdrawn.** RG: *"I don't think we can make a fita
assumption, because the point of pre-reformed orthography is that it's
unstable."* The count assumed those stems always print with Ѳ, so any Ф on
them must be a transcription error. The print itself is not consistent, so
the count measures what the passes wrote, not how often they were wrong.

This is the same mistake as the reverted -арь/-ярь suffix rule: inferring a
norm from a handful of cases and then treating deviation from it as error.

**What survives is scan-verified instances only — 7 of them**, each read
individually: Ѳедорова (1901-02_MSK_ballet_p024), Ѳедоровой + Ѳедорова x2 +
Аѳонасьева (1906-07_MSK_ballet_p001), Ѳомичевъ (1901-02_SP_ballet_p027),
Ѳеодора (1900-01_MSK_opera_p023). Three of the seven were silent — every
pass agreed on the wrong letter, so the disagreement signal never saw them.

**What the 19 pages are:** a worklist — pages where all three passes wrote
Ф on a stem that *sometimes* takes Ѳ. Each instance must be read against
its own scan. Nothing goes into `orthography.py`: fita is lexical, not
phonological, and a gazetteer of "fita-taking names" would encode exactly
the stability assumption being rejected here.

Pages in the worklist:

- `review_1897-98_MSK_ballet_p012`
- `review_1899-00_MSK_all_p004`
- `review_1899-00_MSK_all_p016`
- `review_1900-01_MSK_ballet_p005`
- `review_1900-01_MSK_opera_p023`
- `review_1901-02_SP_ballet_p027`
- `review_1901-02_SP_ballet_p029`
- `review_1901-02_SP_ballet_p030`
- `review_1902-03_MSK_ballet_p003`
- `review_1903-04_SP_ballet_p010`
- `review_1903-04_SP_ballet_p012`
- `review_1903-04_SP_ballet_p013`
- `review_1904-05_MSK_ballet_p001`
- `review_1904-05_MSK_ballet_p022`
- `review_1904-05_SP_ballet_p013`
- `review_1905-06_MSK_ballet_p015`
- `review_1905-06_MSK_ballet_p020`
- `review_1905-06_SP_ballet_p010`
- `review_1906-07_MSK_ballet_p001`

(`p027`, `1900-01_MSK_opera_p023` and `1906-07_MSK_ballet_p001` are already
read; the other 16 are open.)

## Resuming

**Next:** the 16 unread pages of the fita worklist above, each instance
read against its own scan. The 20-page disagreement queue is now fully
triaged.

(Historical note: the queue was described mid-session as "12 remaining
pages"; it was 10, and 2 of those had no real disputes.)

**Superseded:** the remaining flagged pages from
`outputs/reviews/triage_queue.txt`, in BATCHED form — RG, 2026-09-25:
"switch to the batched form now", after the ten one-at-a-time calibration
pages agreed 29 of 30. Batched means Claude reads every dispute on a page
against the scan and brings RG one consolidated list per page rather than
one crop at a time; RG still rules on every character, and any case Claude
cannot read confidently still gets its own crop.

The queue is 20 body-text pages below 0.95 in the 200-page pilot; ~103 are
expected across the full 1,024.

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
