# Season Reviews — fields we capture

Working inventory, started 2026-10-07 at RG's request, ahead of building
mention detection. Part 1 is what the pipeline captures **today**, measured
against the live corpus (1,070 pages / 4,672 blocks / 4,760 spans /
203,361 words). Part 2 is the proposed mention layer.

---

## Part 1 — what exists now

### `review_page.csv` — one row per scanned page

| field | filled | notes |
|---|---|---|
| `page_id` | 1070/1070 | `review_<season>_<city>_<genre>_pNNN` |
| `season` `city` `genre` | 1070 | 19 seasons; SP/Moscow; Ballet/Opera/All |
| `printed_folio` | 994 | 76 blanks are correct — plates and tailpiece pages carry none |
| `tailpiece_present` | 1070 | |
| `no_text` | 1070 | |
| `copy_artifacts` | 217 | **free text, not evidence** — see below |
| `reading_order_uncertain` | 1070 | |
| `n_blocks` `n_chars` | 1070 | derived |

### `review_block.csv` — one row per printed block

| field | filled | notes |
|---|---|---|
| `block_id` `page_id` `block_index` | 4672 | |
| `block_type` | 4672 | paragraph 3073, figure 897, enumerated_list 446, heading 132, verse 38, cast_list 35, other 23, footnote 13, byline 9, personnel_news 6 |
| `enumerator` | 438 | the printed item marker |
| `figure_subtype` | 897 | plate / photograph / ornament |
| `caption_vertical` | 4672 | |
| `footnote_marker` | 13 | |
| `text` / `caption_text` | 3765 / 897 | the transcription itself |
| `manuscript` | **0 True** | dead |
| `column` | **0 filled** | dead |

### `review_span.csv` — typographic runs inside a block

| field | filled | notes |
|---|---|---|
| `span_id` `block_id` `span_role` `span_index` | 4760 | |
| `text` | 4760 | |
| `razryadka` | 4760 | letter-spacing; the one typographic flag that works |
| `italic` | 4760 | |
| `lang` | 125 | fr / ru |
| `bold` | **0 True** | dead |
| `uncertain` | **0 True** | dead |
| `damaged` | **0 True** | dead |
| `gap` / `gap_extent` | **0** | dead |

### Seven dead fields, and what that means

`column`, `gap_extent`, `manuscript`, `bold`, `uncertain`, `damaged`, `gap`
are never populated — not once in 4,760 spans. The uncertainty contract in
particular (`uncertain` / `damaged` / `gap`) is specified, prompted for, and
entirely ignored by the model; the `zero_uncertainty` quality check fires 33
times for exactly this reason. The gold transcriptions DO mark damaged type
with `<d>`, so the concept is real — the model just never reports it.

**Design consequence: a field the model is merely asked to fill is not a
field we have.** Anything in Part 2 should be derivable by code from the
text, or checkable, rather than trusted because the prompt requested it.

### `copy_artifacts` is not evidence

Two of two stamp entries checked were wrong, one wholly fabricated (a
Czechoslovak ministry library recorded as a Kiev one, with an invented date).
See `docs/eval/genuine_print_typos.md`. Useful as a pointer to *look* at a
page; never as a source.

---

## Part 2 — the proposed mention layer

RG's stated use (2026-09-26): connect a mention of a person, ballet, role or
musical number in a review to its entity, with the season as context. Nothing
here is built yet.

### What the text actually supports

Measured on the corpus, not assumed:

- **29.3% of tokens are capitalised**; 36% of those are sentence-initial
  noise, 42% match a known surname outright.
- **Case inflection is the main matcher failure**, not missing entities.
  `Сен-Леона` is the genitive of `Сенъ-Леонъ`, which IS in `research.person`.
  Same for Минкуса, Вагнера, Делиба, Павловой, Рославлевой, Сѣдовой.
- **3,918 guillemet spans `«…»`** — work titles are explicitly marked.
- Honorifics (`г.`, `г-жа`, `г-жи`, `гг.`, `восп-ца`, `уч-ца`, `в-ца`) govern
  **lists**, not single names: one honorific, then thirty surnames.
- Creator attributions carry their own markers and no honorific:
  `муз. соч.`, `сочин.`, `балетм.`, `художника`, `постановка`.

### `review_mention` — proposed

| field | source | notes |
|---|---|---|
| `mention_id` | derived | |
| `block_id`, `char_start`, `char_end` | derived | anchor into the verbatim text |
| `surface` | verbatim | exactly as printed, inflected, pre-reform |
| `normalised` | derived | orthography-folded **and case-stripped** |
| `mention_type` | derived | person / work / role / theater / place / creator-role |
| `entity_id` | linked | `person_id`, `work_id` or `theater_id`; null if unresolved |
| `link_method` | derived | exact / folded / case-stripped / fuzzy / honorific-span |
| `link_confidence` | derived | |
| `candidates_n` | derived | how many entities the surname alone admits — 79% of surnames are ambiguous before context |
| `evidence` | derived | the honorific, ordinal, marker word or guillemets that found it |

### CORRECTION 2026-10-07: do not invent an assertion shape

The spiski ALREADY model the performer -> work -> role triple:
`raw.person_entry_credit`, `credit_type='named_work'`, **10,718 rows with a
`role_name`** and `label` holding the work (Эсмеральда/Эсмеральда,
Донъ-Кихотъ/Жуанна). Creator roles live separately in
`research.production_credit` (1,495 rows). Query logged 2026-10-07.

But the performer triple is **not exposed in `research`** — it exists only
in raw/analysis, and `research.person_appearance` carries no role or work.
That missing research table is a need BOTH tracks share; the Repertoire side
has 10,718 rows waiting for it today, independent of the reviews.

So the reviews should feed the existing shape. What they uniquely add is
**dates**: spiski credits are season-scoped with no performance date, and
the repertoire tables have dates but no roles. The reviews join the two.

### Mention detection is CLOSED-VOCABULARY matching, not NER

RG, 2026-10-07: *"there will be very few mentions of people who don't exist
elsewhere in the Yearbooks."* That retires the open-NER framing and the
hand-annotation recommendation with it — if the population is closed,
measuring against the dictionary IS measuring against nearly all mentions.

All four target types already have dictionaries:

| type | source | distinct |
|---|---|---|
| people | `research.person.canonical_family_name` | 1,852 |
| works | `research.work.canonical_title` | 3,152 |
| roles | `raw.person_entry_credit.role_name` | 2,621 |
| theatres | `research.theater` | 6 |

**Measured coverage** of 38,216 capitalised non-sentence-initial tokens,
using those dictionaries plus crude case-stripping: person 40.8%, work
12.1%, role 7.0%, initials 7.0%, **unmatched 33.0%**.

The unmatched third is mostly two fixable things:

- **Institutions in inflected/adjectival form** — Императорскихъ, Маріинскомъ,
  Московскаго, Его Величества. `research.theater` holds 6 canonical names
  and no adjectival forms. A theatre/institution dictionary is the single
  biggest remaining gain.
- **A threshold bug in the test, not the data** — the indexer required 4+
  characters, so Дочь->доч, Донъ->дон and Фея never matched, losing the
  first words of «Дочь фараона» and «Донъ-Кихотъ».

**Caution on roles.** The role vocabulary mixes proper names (Лиза, принцъ
Шарманъ) with generic nouns (королева 53, офицеръ 55, цыганка 71, герцогиня
50). Matched naively against running prose those will fire on ordinary
words. Role matching needs the cast-list context, not free text.

### `review_assertion` — superseded, see the correction above

A mention alone does not answer "Pavlova 2 danced this role in this ballet
this season". The cast-list grammar supplies a relation:

> `Царь-Дѣвицу—г-жа Джури` — role em-dash performer

| field | notes |
|---|---|
| `assertion_id` | |
| `block_id` | provenance |
| `person_mention_id` → `person_id` | the performer |
| `role_surface` / `role_id` | the role as printed |
| `work_mention_id` → `work_id` | from the governing title |
| `season`, `city`, `genre` | from the page |
| `date_text` | where the review gives one |
| `assertion_type` | performed-role / created / conducted / designed |

### Open questions, deliberately unanswered here

1. **Where does this live?** No table in the DuckDB has "review" in its
   name; the reviews are CSV-only. Deferred item §12.5, still open.
2. **Roles as entities?** `research` has no role table. Авроры, Китри,
   Одетты recur across seasons and would resolve, but that is a new
   population like composers were.
3. **Season must RANK, not gate.** A hard season+ordinal filter leaves 15.5%
   of mentions with zero candidates (guests, roster gaps, ordinal
   mismatches).
4. **Recall against ALL mentions is unmeasured.** Every figure above counts
   tokens that already match a database entity. A person with no entity is
   invisible to the measurement. A small hand-annotated sample is the only
   way to know the real denominator.


---

## Unknown names get flagged for investigation (RG, 2026-10-07)

> "If in the process we find names that aren't in the database, we flag them
> for investigation. They might be special guests, the tsar/family, or
> something else."

A by-product of matching, not a separate effort. The high-precision rule is
**a token carrying an honorific or following an initial that matches no
dictionary** — a person by grammar, unknown by lookup.

First run of that rule: **1,585 distinct forms, 3,119 occurrences.** It
needs two kinds of cleaning before it is a worklist, and the cleaning is
more informative than the queue:

**1. Stemmer failures, not absences.** Adjectival surnames in -скій/-ская
decline differently (-аго, -ому, -имъ, -ой, -ую) and my noun-ending list
missed all of them. Чайковск**аго** 126x, Горск**имъ** 73x, Кшесинск**ой**
39x, Преображенск**ой** 24x — every one of them already in
`research.person`. Adding the adjectival endings moves unmatched 30.4% ->
28.9% (~950 tokens). Any production matcher needs both declension classes.

**2. Hyphenation fragments.** пе-, ле-, кше-, пре-, чай-, гри-, преобра-,
кшесин- — line-break splits that must be rejoined before matching. The
bilingual builder already rejoins them for reading; the matcher does not.

**What survives as genuinely absent** — and it is a coherent population:
**Гуно, Бородинъ, Римскій-Корсаковъ, Верди, Мейерберъ, Бизе** (opera
composers) and **Фигнеръ** (the tenor). The ballet-lists thread (#133)
supplied BALLET creators — Минкусъ, Сенъ-Леонъ, Делибъ, Пуни, Дриго — but
opera composers were never in scope, so the reviews are the first place they
surface. Exactly the discovery RG described.

Note Глинка is absent too; `research.person` holds only `Глинкинъ`, an
unrelated surname.


---

## SCOPE, RG 2026-10-07: opera reviews are out for now

> "Let's not work with opera reviews at this time. We will look at them
> separately and for ballet mentions specifically."

This followed directly from the discovery-queue finding: the seven
"genuinely absent" people are an **opera artifact**, 293 occurrences in
opera reviews against 10 in ballet ones. The entity database was built from
ballet-priority sources, so opera composers were never in scope and their
absence is expected, not a gap.

| genre | pages | blocks | words |
|---|---|---|---|
| Ballet | 698 | 3,122 | 137,516 |
| Opera | 262 | 1,059 | 50,621 |
| All (combined) | 110 | 491 | 15,224 |

**Dropping Opera leaves 152,740 words (75%) across 808 pages.**

**But the two combined "All" volumes cannot be split by section.** They
carry only 10 headings between them, none of which is a `балетъ` / `опера` /
`драма` section marker — they use document titles instead (`ОБОЗРѢНІЕ`,
`С.-Петербургъ.`, `ИМПЕРАТОРСКІЕ МОСКОВСКІЕ ТЕАТРЫ.`). So the
heading-based filter that cleans the single-genre files has nothing to work
with here, and those 15,224 words remain a ballet/opera/drama mixture.

Three options when this matters, none chosen yet:
1. treat Ballet-only as the working set (137,516 words, 698 pages) and
   handle the combined volumes with the opera pass;
2. keep the combined volumes in and accept the mixture;
3. segment them by content rather than by heading.

**When opera is picked up separately**, the useful filter is not "unknown
name" but **"unknown name appearing in a ballet context"** — that is a short
list and every entry is on topic. The 10 ballet-review occurrences of the
opera composers (Глинка x4, Гуно x2, Римскій-Корсаковъ x2, Верди,
Мейерберъ) are presumably mixed bills or divertissement music, and connect
to the open "drama with ballet/dancers" thread.

---

## BUILT 2026-10-07 — `pipeline/match_review_mentions.py`

Mention matching is no longer unbuilt. RG chose the whole ballet corpus over a
dense-slice first pass, with a smoke test ahead of it to surface problems early.

```
uv run python pipeline/match_review_mentions.py \
    --reviews-dir outputs/reviews/merged_full \
    --db outputs/full_run/imperial_theaters.duckdb \
    --out-dir outputs/reviews/mentions
```

Runs in 0.6 s over 698 pages — no API cost, so it can be re-run freely after any
correction to the review text or any growth in the entity tables.

### What it produced

**698 pages / 3,118 blocks -> 27,085 mentions**, 15,117 (55.8%) resolved to a
single entity.

| type | n |
|---|---|
| person | 21,503 |
| work | 3,695 |
| role | 1,119 |
| theater / institution | 632 |
| dance_number | 136 |

Three side outputs:

- `review_mention_unknown.csv` — **855 distinct forms, 1,368 occurrences**, 564
  of them in ballet context. RG's flag-for-investigation ask.
- `review_title_candidate_misreads.csv` — **40 forms, 85 occurrences**: an
  unresolved title within edit distance of a real work. Reported, never applied.
- `mixed_script_word`, now a permanent check in `quality_checks_reviews.py`.

### Forms are generated from the dictionary, not stemmed from the text

Every canonical surname and title is expanded into its declined forms, folded,
and indexed; matching is an exact lookup. Stemming arbitrary tokens failed in
both directions in the exploratory pass. Generation makes each declension class
an explicit, reviewable rule, and a missed form is then a missing rule rather
than a silent threshold.

Classes that had to be added, each found by the smoke test:

| class | example | was failing |
|---|---|---|
| adjectival masc/fem | Чайковск**аго**, Кшесинск**ой** | the original known gap |
| soft stem (ь) | Гертель -> Гертел**я** | 10x |
| sibilant instrumental | Вальцъ -> Вальц**емъ** (not -омъ) | 19x |
| declining `-и` | Гримальди -> Гримальд**ы** | 22x |
| feminine `-я` | Фея -> Фе**и** | 15x |
| declining titles | Жизель -> Жизел**и** | — |
| both words declining | Лебедино**е** озер**о** -> Лебедина**го** озер**а** | — |

### Three traps, all paid for once

1. **Line breaks.** 7,173 words (3.7% of the corpus) are split across a printed
   break, and ~3,000 of those are capitalised — exactly the mentions being
   sought. Reflow first. A pattern failing across a break fails *silently*.
2. **ь/ъ is unstable.** The corpus prints `Легать`/`Легатъ`,
   `Сень-Леонъ`/`Сенъ-Леонъ`, `Мендесь`/`Мендесъ`. The lookup key treats a
   component-final soft sign as a hard one, symmetrically on both sides. Worth
   40+ mentions. Per the standing rule, this is a variant to absorb, not an
   error to flag.
3. **Gender cannot be read from a final hard sign.** An early ranker scored
   `-ъ` as masculine and so penalised the correct candidate by 5 points. The
   smoke test showed 128 gender mismatches, nearly all the *rule's* fault:
   `Ваземъ`, `Гейтенъ`, `Борхардтъ`, `Эрлеръ`, `Бастманъ`, `Мендесъ` are
   indeclinable and belong overwhelmingly to women here — Екатерина Ваземъ and
   Лидія Гейтенъ were leading ballerinas. Gender is now inferred only from the
   Slavic families that actually mark it (-овъ/-ова, -скій/-ская), and from the
   honorific, which is unambiguous. **After the fix: 0 mismatches in 6,945
   checkable resolutions.**

### Season ranks, it does not gate

As the design required. Candidates score on honorific gender (+4/-5), ordinal
(+6/-4), and season coverage (+5/-2); a margin of 4 or more resolves, a tie
leaves the full candidate list standing. This moved resolution from 20.9% to
55.8% on the smoke-test seasons without excluding anything.

### A new finding: gender contradiction marks a missing person

A resolution whose gender contradicts the honorific is not a match — it is
evidence that the family's *other* member is absent from `research.person`.
`Г-жа Галактіонова` resolving to `Галактіоновъ, Павелъ Георгіевичъ` is a roster
gap. **34 flagged.** Verified by hand on six: in every case the database held
only the opposite-gender counterpart. This is a higher-quality signal than the
raw unknown list, because the surname is known and only one family member is
missing.

### The unknown queue is coherent, not noise

RG expected special guests and the imperial family. The largest group is
neither: **pre-1890 historical ballerinas named in retrospectives** —
Прихунова, Амосова 1-я/2-я, Андреянова, Мадаева, Гранцева. They predate the
yearbook's own rosters, so no amount of roster coverage would reach them.
`Гримальди` (a guest) and `Пожицкая`/`Рябцевъ`/`Кошева` (Moscow dancers) are
the other groups.

### Still open

1. **20,172 mentions remain ambiguous** (>1 candidate, no decisive margin).
   The margin rule is deliberately conservative; city is not yet a signal, and
   `research.person` carries no city column.
2. **767 quoted titles unresolved.** Some are genuinely absent works, some are
   misreads (see the side file), some are French dance numbers now typed
   separately.
3. **Recall is still unmeasured** against *all* mentions. Every figure here
   counts tokens that match a dictionary; a person with no entity is invisible
   to the measurement. A hand-annotated sample remains the only way to know the
   real denominator — unchanged from the original design note.
4. **No table.** Output is CSV; the reviews still have no home in the DuckDB,
   deferred item §12.5.
