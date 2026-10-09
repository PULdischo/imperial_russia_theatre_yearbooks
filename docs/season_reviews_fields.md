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

---

## BUILT 2026-10-07 (same day) — the credit join and dated assertions

`pipeline/build_reviews_duckdb.py`, then `pipeline/build_review_assertions.py`.
RG picked this over the data-quality queues because it is the actual goal.

```
uv run python pipeline/build_reviews_duckdb.py \
    --reviews-dir outputs/reviews/merged_full \
    --mentions-dir outputs/reviews/mentions \
    --db outputs/reviews/db/imperial_theaters_reviews.duckdb
uv run python pipeline/build_review_assertions.py \
    --reviews-dir outputs/reviews/merged_full \
    --db outputs/reviews/db/imperial_theaters_reviews.duckdb \
    --out outputs/reviews/mentions/review_assertion.csv
```

Built against a **scratch copy** of the production database, not
`outputs/full_run/`, because a parallel session is active. Promoting it is a
separate, deliberate step.

### Closes §12.5 — the reviews are now queryable

| table | layer | rows |
|---|---|---|
| `raw.review_page` | verbatim, page-centric | 1,070 |
| `raw.review_block` | verbatim, one row per printed block | 4,672 |
| `entities.review_mention` | linkage state, with candidate lists | 27,085 |
| `research.review_assertion` | the research fact | 1,939 |

A mention is linkage state, so it lives in `entities` beside `person_link`; an
assertion is a research fact, so it lives in `research`. Nothing was
hand-edited and every script is re-runnable.

### The result

**1,939 assertions**, 334 distinct performers, 1,449 distinct roles. 1,482
carry a performer entity, 362 a work entity, **420 a date**. The spiski credit
join newly resolved **178** performers that no amount of gender/season/ordinal
ranking could separate.

The payoff query — a performer's roles across the reviews, which neither source
could answer alone:

| performer | assertions | dated | distinct roles | span |
|---|---|---|---|---|
| Преображенская, Ольга Іосифовна | 83 | 29 | 73 | 1892-93 – 1907-08 |
| Леньяни, Пьерина | 67 | 3 | 62 | 1893-94 – 1900-01 |
| Трефилова, Вѣра Ивановна | 65 | 16 | 59 | 1894-95 – 1907-08 |
| Петипа 1-я, Марія Маріусовна | 45 | 1 | 42 | 1892-93 – 1904-05 |
| Карсавина, Тамара Платоновна | 23 | 7 | 22 | 1902-03 – 1910-11 |

### Validated against the Repertoire, which is the real test

**141 of 142 distinct extracted dates land on an actual `research.event` in the
same city — 99.3%.** The works agree too: the review's 1890-11-21 Moscow
«Эсмеральда» cast sits on a Repertoire night of `Эсмеральда / Воевода`, and the
1891-01-20 «Кипрская статуя» cast on `… / Бенефисъ г-жи Бессонэ / Кипрская
статуя / …` — which is precisely the benefit the review is describing. The one
unmatched date, `1896-08-01` SP, is an August roster-appointment date, not a
performance.

### The cast-list grammar prints both orders, and the role is often lowercase

Decided by surname membership rather than position, because the corpus does both:

- `роль—performer` — `Клодъ Фроло—Гельцеръ`, `судья—Бондыревъ` (1,795)
- `performer—роль` — `Составъ исполнителей былъ слѣдующій: Бессонэ — Галатея;
  Гельцеръ — Пигмаліонъ` (168)

Requiring a capital on the left, as the first version did, dropped **every
descriptive common-noun role**: `бабушка—Матвѣева`, `нотаріусъ—г. Жуляевъ`,
`его жена—г-жа Матвѣева`, `владѣлецъ деревни — Гельцеръ`. Loosening the role
side is only safe because the performer side is pinned to the surname
dictionary. Fixing this took the yield from 1,357 to 1,939 (+45%).

### Three bugs worth remembering

1. **Julian dates are not Gregorian dates.** `datetime.date()` rejects
   29 February 1900 — a date this corpus genuinely contains, because imperial
   Russia used the Julian calendar and 1900 is a Julian leap year.
   `research.event` already holds 6 events on `1900-02-29`, which is also why
   its `date_undate` is VARCHAR. The first version built dates through
   `datetime` inside a try/except and dropped those **silently**.
   `review_assertion.date_undate` is VARCHAR and named to match, so it joins
   straight to `research.event.date_undate`.
2. **The credit join needs the gender constraint too.** Without it `г-жа
   Смирнова` resolved to `Смирновъ, Александръ Митрофановичъ`: the credit table
   is keyed by person, so a same-surname relative of the other gender is a
   perfectly good index hit and a wrong answer.
3. **Role spans must not cross a sentence boundary**, and must be trimmed of a
   preceding pair's performer. Before that, role values included
   `Яковлевъ. Партію Германа пѣлъ г. Клементьевъ, графа Томскаго`,
   `Московскихъ театровъ` (a fragment of "артистъ Императорскихъ Московскихъ
   театровъ") and `Гельцеръ, Коленъ, молодой крестьянинъ…`.

Also: **DuckDB refuses a foreign key across schemas** ("Creating foreign keys
across different schemas or catalogs is not supported"), so
`entities.review_mention.block_id` is a plain column with an explicit
post-load referential check. One more entry for the DuckDB-constraint list in
CLAUDE.md beside the missing `ALTER TABLE ADD FOREIGN KEY` and the `UPDATE`
restriction.

### Still open

- **457 assertions have no performer entity**, mostly irreducibly: `Петипа`
  admits 9 genuine family members and `Иванова` 52, and a prose mention with no
  role has nothing to join on.
- **Only 362 of 1,939 carry a work entity.** The governing title is taken as
  the nearest preceding work mention in the block, which often is not there.
  Carrying the title down from the page's heading would help.
- **Not promoted** to `outputs/full_run/`.

---

## The work side, 2026-10-07 — 362 -> 1,136 work entities

I had attributed the work-side gap to missing page headings. **That was wrong,
and the measurement says so.** Breaking the 1,939 assertions down first:

| bucket | n (before) |
|---|---|
| work_id resolved | 362 |
| work_surface found but **unresolved** | 675 |
| no work_surface at all | 902 |

The larger half was not a missing-title problem at all. It was 675 titles that
the matcher *had* found and failed to resolve, and they were famous ballets --
`Донъ-Кихота` 46x, `Золушка` 40x, `Спящая красавица` 29x, `Коппелія` 23x --
which certainly exist in `research.work`.

### Cause: a title was ambiguous against its own excerpt records

`«Коппелія»` came back with 5 candidates: the work (106 appearances) and **four
of its own act records** (`2-е д. бал. Коппелія`, `1-е и 2-е д., бал.
Коппелія`, …). Self-inflicted: `title_forms()` strips a leading genre
abbreviation to catch `«бал. Щелкунчикъ»`, and that same strip reduces an
excerpt title to its parent's title.

Three fixes, in order of how much they returned:

1. **Index an excerpt row under its literal title only**, never its stripped
   reduction. The parent already carries the bare title.
2. **Detect excerpt shape from the title**, not only from
   `excerpt_of_work_id` -- issue #88 linked most excerpts but left some
   unlinked, and those unflagged rows (`6 и 7 март. бал. Конекъ-Горбунокъ`,
   `2-е х. бал. Лебединое озеро`, `3-е и4-е д. бал. Конекъ-горбунокъ`) kept
   their parents ambiguous. The robust test is an **inline genre abbreviation
   with text before it**; enumerating act patterns missed `и4-е`, which has no
   space after the conjunction.
3. **Inside a ballet review, prefer the ballet candidate.** Different art forms
   are deliberately different works here, so `Донъ-Кихотъ [бал.]` and
   `Донъ-Кихотъ [героич. ком.]` are two rows, and `Волшебная флейта` is both
   `бал.` and `оп.` A ballet review means the ballet.

Work mentions resolved went **1,012 -> 2,802 of 3,692 (75.9%)**, still-ambiguous
work mentions **1,505 -> 114**, and overall mention resolution 55.8% -> 62.4%.

### Page inheritance helps, but much less than I claimed

For the 902 assertions whose block names no title:

| situation | n |
|---|---|
| no work mention earlier on the page at all | 464 |
| exactly ONE resolved work earlier -> safe to inherit | 255 |
| earlier mentions, none resolved | 72 |
| **two or more** different resolved works earlier -> unsafe | 111 |

So inheritance reaches about a quarter of the gap, not most of it. It is applied
only when the page has settled on one work, and `work_source` records the
provenance (`block` 991, `page-earlier-block` 301, `ambiguous-on-page` 111,
none 536) so it can be filtered.

**Validated rather than assumed**, by asking whether the spiski independently
credit that performer on that work:

| work_source | confirmed by spiski |
|---|---|
| `block` | 422/648 = **65.1%** |
| `page-earlier-block` | 138/245 = **56.3%** |

Inheritance is ~9 points less reliable. Neither figure is a ceiling: the spiski
carry role rows for only some performers, so non-confirmation is not
necessarily error.

### Result

**1,136 assertions carry a work entity, up from 362** (3.1x). The credit join
also improved as a side effect (178 -> 196 resolutions), because
`spiski-credit-work` needs a work to key on.

### New side output: work-consolidation candidates

`review_work_consolidation_candidates.csv`, 15 collision sets, split by verdict
so the list is actionable:

- **7 `spelling-variant?`** -- genuine duplicate work rows differing only in
  orthography, same genre: `Аленькій / Аленъкій / Аленкій цвѣточекъ` (3 rows),
  `Привалъ кавалеріи / Привалъ кавалерія` (59 appearances vs 1),
  `Фея куколъ / Фея куколь` (54 vs 3), `Тангейзерь / Тангейзеръ`,
  `Лѣсъ / Лѣсь`, `Конекъ-горбунокъ / Конекъ-Горбуночкъ`. For the
  work-consolidation thread.
- **8 `art-form split (deliberate)`** -- `Карменъ` as `оп.` (241) and `бал.`
  (2), `Волшебная флейта` as `бал.` (40) and `оп.` (10). **Not** to be merged;
  they are the policy. There are 36 such identical-title groups in
  `research.work` overall.

---

## PROMOTED to `outputs/full_run/` — 2026-10-07

The reviews are in production. **Not by copying a file** — that is the mistake
`promotion-race-with-parallel-sessions` records, where a whole-file copy
clobbered a concurrent session. Promotion here means re-running the builders
against the live database, so they pick up whatever the other sessions have
changed:

```
uv run python pipeline/match_review_mentions.py \
    --reviews-dir outputs/reviews/merged_full \
    --db outputs/full_run/imperial_theaters.duckdb \
    --out-dir outputs/reviews/mentions
uv run python pipeline/build_reviews_duckdb.py \
    --reviews-dir outputs/reviews/merged_full \
    --mentions-dir outputs/reviews/mentions \
    --db outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_review_assertions.py \
    --reviews-dir outputs/reviews/merged_full \
    --db outputs/full_run/imperial_theaters.duckdb \
    --out outputs/reviews/mentions/review_assertion.csv
```

**Why now rather than after the data-quality queues:** production drifted
*during this session* — `research.person` went from 3,243 to 3,219 while the
work sat in a scratch copy. Issue #71 is the precedent: a fix built on
2026-09-15 went unpromoted for three weeks, went stale, and had to be rebuilt
from scratch. The re-run approach makes promotion cheap enough that there is no
reason to let that happen again.

### Verified, not assumed

Snapshotted all 35 pre-existing tables before and after:

- **0 pre-existing tables changed**, none removed, 4 added
- `raw.review_page` 1,070 · `raw.review_block` 4,672 ·
  `entities.review_mention` 27,082 · `research.review_assertion` 1,939
- **0 dangling references** on all five integrity checks (mention -> block,
  person mention -> research.person, work mention -> research.work, assertion
  performer -> person, assertion work -> work)
- dates still 141/142 against `research.event`; gender audit still 0 mismatches
  in 6,945 checkable

A pre-promotion backup is at
`outputs/reviews/db/backup/imperial_theaters_pre_review_promotion_<ts>.duckdb`.
The scratch copy was deleted: it is reproducible in seconds, and a second
database carrying review tables is exactly the staleness hazard above.

### Publishing consequence, not yet acted on

`research` is the published layer, so **`research.review_assertion` will flow to
Datasette and the HF dataset on the next publish**. `entities.review_mention`
will not — CLAUDE.md marks `entities` as pipeline-internal and unpublished. If
the assertions should stay private for now, `build_datasette.py`'s SCHEMAS list
is where to exclude them. Worth a decision before the next publish; the table
carries `link_method`, `link_confidence`, `work_source` and the full candidate
list, so a consumer can filter rather than take everything at face value.

---

## New season 1912-13 SP Ballet — added 2026-10-09

RG approved the run. The corpus is now **1,074 pages / 20 seasons**, extending
past its previous 1910-11 endpoint.

4 pages, 3 views, **28 vision calls, 167K tokens, 0 errors**. Scoped manifests
were used throughout so only the new pages were billed; the four other
unprocessed PDFs (1908-09 Opera SP/Moscow, 1912-13 Opera SP, 1908-09 Music SP)
were left alone, opera being deferred.

```
render_reviews.py --pdf-dir <one-pdf dir> --out-dir outputs/reviews  # then merge the manifest
make_bands.py --bands 2 / --bands 4                                   # then merge those manifests
run_reviews.py x3  (full / bands2 / bands4)   -> 4 + 8 + 16 calls
stitch_bands.py x2 ; parse_reviews.py x3 ; merge_views.py             # all free
```

**Quality: 0 flags on all 4 pages.** Folios 140-143, consecutive. Selector
changed 4 of 1,008 words (0.40%), the corpus norm. Text spot-checked against
the scan and exact: Karsavina as Nikiya in «Баядерка», 49 performances, 20
ballets, the per-work date lists, Направникъ and Коутсъ conducting.

### The later reviews are a different genre, and the assertion layer feels it

This is **А. Левинсонъ**'s criticism, not a cast list. It gives statistics and
dates in prose — `«Баядерка» 4 раза (2-го, 5-го и 9-го сентября съ участіемъ
г-жи Карсавиной…)` — work, date and performer, but **no role**, so the
`Role—Performer` grammar finds nothing. 1912-13 contributes **0 assertions** and
that is correct, not a miss. Worth knowing before extending into the
1910s: the performer→role→work extractor is tuned to the 1890s cast-list
convention and will return progressively less as the reviews become essays.

It still yields mentions: 65 person, 58 work, 6 theatre. Only 16 of the 65
person mentions resolve (25%, against 62% corpus-wide) because the
Diaghilev-era names are simply not in `research.person`, which is built from
rosters ending at 1910-11. The unknown queue for this season is exactly that
cohort — **Бакстъ, Анисфельдъ, Коутсъ, Бронская, Ланская, Карали,
Рождественская, Зеестъ** — and `Дягилевъ` himself DID resolve.

### Two bugs the new season exposed, both fixed

1. **A work title generated feminine forms and swallowed a surname.**
   `Дубровская` (a dancer absent from `research.person`) matched the opera
   `Дубровскій`, because `title_forms` declines a title's final word through
   `surname_forms`, which adds BOTH genders. Right for a person — the same
   family name occurs as Горскій and Горская — and wrong for a work, which
   appears as `Дубровскаго`, never `Дубровская`. Titles now index with
   `both_genders=False`.
2. **The assertion builder mined the previous review's tail.** An issue packs
   two reviews onto one printed page, so a review's first page often opens with
   the end of the last one; `build_bilingual` drops those paragraphs, and the
   assertion builder did not. The only "assertion" 1912-13 produced was
   `представленій, посвященныхъ отечественнымъ авторамъ, и 16 %` — `Вагнеру`,
   parsed out of an opera statistics sentence. Now skipped, 48 blocks
   corpus-wide.

   Note the off-by-one that hid it at first: `first_page_skip` returned the
   list position where it had to return the stored `block_index`, which is
   1-based.

**Side effect worth recording:** removing that bleed took the date validation
from 141/142 to **139/139, 100%**. The one date that had never landed on a real
`research.event` — `1896-08-01` — was a roster-appointment date from exactly
this kind of bled-in paragraph. The anomaly was a symptom of the bug.

Corpus after: `raw.review_page` 1,074 · `raw.review_block` 4,697 ·
`entities.review_mention` 27,211 · `research.review_assertion` 1,936. Gender
audit 0 mismatches in 6,947; all referential checks 0.

**Not done:** the new pages have no English. `translate_reviews.py` would be a
separate billed run (~1,008 words), and the bilingual files are stale until it
runs — they carry a `source-hash` that no longer matches.

---

## Mixed-script queue CLOSED — 2026-10-09

**77 `mixed_script_word` flags -> 0.** Total review quality flags 233 -> 156.
The 25 scan decisions are in `docs/eval/mixed_script_scan_decisions.md`; the
machine-readable table is `docs/eval/mixed_script_corrections.csv`.

### Applied POST-MERGE, deliberately, and why

The obvious route — re-parse the three views and re-merge — **was tried and
rejected on evidence.** A control merge of the unchanged views reproduces
`merged_full` byte-identically, so the selector itself is stable. But once the
views' text changes, the selector sees different candidate pools and picks
differently in unrelated places. The re-merge produced **16 collateral changes
that have nothing to do with mixed script**, several plainly wrong:

| was | became |
|---|---|
| `Фредерикъ;` | `дерикъ;` |
| `Кшесинская` | `синская` |
| `3-я.` | `5-я.` |
| `«Galop»` | `«Галор»` |
| `Crimée` | `Сримéе` |

So the repair is applied directly to `merged_full` instead. The diff is then
exactly **81 word changes, 68 distinct, every one intended** — no collateral
movement at all.

**Consequence to know:** `merged_full` now carries a post-merge repair, so
re-merging from the view directories will NOT reproduce it. Those directories
are stale anyway — they hold 1,018 pages against the corpus's 1,074, predating
the issue-era additions. Re-running the merge needs the re-parse
(`view_*_parsed_new`) AND a fresh diff, not a blind rebuild.

### OPEN: the selector can prefer a truncated token

`Фредерикъ;` -> `дерикъ;` and `Кшесинская` -> `синская` are a full word losing
to a fragment of itself, which contradicts `select_reading`'s own first rule
("a dropped word never beats a read one"). `«Galop»` -> `«Галор»` and
`Crimée` -> `Сримéе` are pure-Latin titles being Cyrillicised, which the
mixed-script filter is explicitly supposed to leave alone. **Not investigated.**
These surfaced only because the re-merge was diffed rather than trusted, and
they are latent in any future re-merge.

### What the corrections changed

19 toward Cyrillic, 3 toward **Latin**, 3 separators — plus a Roman-numeral
normalisation rule (`XIІІ` -> `XIII`; glyph-identical, so Latin by RG's ruling
rather than by inspection).

Four could not have come from any character mapping, which is the whole
argument for checking scans one at a time rather than extending the heuristics:

- `Aprilя` -> **Апрѣля** — the Latin `i` stands for **ѣ**
- `tancovaли` -> **танцовали** — the Latin `c` stands for **ц**
- `Парtii` -> **Партіи** takes `і`, while **Чекетти** and **Гримальди** take
  `и`. Position decides; only the page can say.
- `Рапаderos` -> **Panaderos**, the Raymonda dance. The model read Latin `Pana`
  as Cyrillic `Рапа`, so the natural-looking repair would have invented
  `Рападерос`.

### A false positive of my own check, now fixed

`XLVлѣтнюю` was never an error. The print reads `за XLV-` / `лѣтнюю службу`,
and that is a **compound** hyphen, not a soft one. The reflow joined it and
manufactured the flag. Every reflow in the pipeline now keeps a hyphen that
follows a digit or a Roman numeral (`parse_reviews`, `quality_checks_reviews`,
`match_review_mentions`, `build_bilingual`, `find_opera_ballet_crossover`).

### Downstream

Mentions **27,211 -> 27,237** — the repaired words are matchable now, which was
the point. Person mentions joining `research.person` 12,819 -> 12,829; work
2,836 -> 2,839; assertions with a work entity 1,136 -> 1,138. Gender audit 0
mismatches in 6,955, dates 139/139, all referential checks 0. Bilingual files
rebuilt (47 files, 1,074 pages); the 1912-13 pages remain untranslated.

---

## Gender contradictions worked — 2026-10-09

**76 occurrences -> 55**, and the two largest causes turned out to be **my own
matcher**, not missing people. The remaining 33 forms are in
`docs/eval/review_people_not_in_rosters.csv`.

### Cause 1: the matcher indexed only canonical names (20 of the 76)

`Балашева` was flagged 20 times as an absent woman. She is not absent. Entity
resolution had already merged her correctly: `Балашева` and `Балашова` are both
**Александра Михайловна Балашова**, printed both ways across the years, and all
27 raw `Балаш*` entries ARE linked. But `research.person` keeps one canonical
spelling, so the review's variant matched nobody — and the form generator then
reached the MALE `Балашевъ` through its cross-gender forms, which is what the
gender check was catching.

**949 roster spellings across 594 people were invisible this way** —
`Югансонъ` for `Іогансонъ`, `Иосафовъ` for `Іосафовъ`, `Алольфи` for
`Адольфи`. The matcher now indexes every spelling `entities.person_link`
attaches to a person, with any ordinal stripped (the ranker scores those
separately). `Балашева` -> Балашова and `Балашовъ` -> Балашевъ both resolve.

### Cause 2: an honorific span running past the gender it governs

`Медалинскій` resolves correctly about 60 times under `гг.`/`г.` and was
flagged exactly once, under `г-жи`. The print writes `г-жи A, B, Медалинскій`
and simply lets the honorific lapse when the list reaches a man; the scanner
kept carrying it.

A contradiction inside an honorific list is now read as the list moving on
rather than as an absent person — **but only when the surface's own morphology
agrees with the entity**. That distinction is the whole safety of the rule:

- `Медалинскій` is masculine by its ending and matches a masculine entity, so
  only `г-жи` is out of step -> the honorific lapsed, keep the match.
- `Ефремова` is feminine by its ending AND by `г-жа`, and matches a masculine
  entity -> a real contradiction, and a genuinely absent woman.

Without that test the rule silently linked Ефремова to Ефремовъ. It was caught
by checking, and the first version is not what shipped.

The audit that reads honorific against entity therefore now reports **2
mismatches rather than 0, by design** — `Бочкина` under a `Г.` that is an
initial, and the one `Медалинскій`. Both carry
`rank_reason = 'honorific lapsed in list'`, so they are distinguishable from a
real mismatch.

### What remains: 33 forms, 55 occurrences

Genuinely absent from the rosters, which cover only certain companies and
years. Each row names the same-family member who IS present, so the question is
usually "is this his sister / her husband, and should they be a person?" —
RG's call, not the pipeline's. Three look instead like spelling variants of
someone already in the database and are flagged as such in the CSV:

| printed | the database has | |
|---|---|---|
| `Соляниковъ` | `Солянниковъ` | single vs double н |
| `Голейзовскій` | `Галейзовскій, Кассіанъ Карловичъ` | о vs а — this is Kasyan Goleizovsky |
| `Балащева` | `Балашева`/`Балашова` | щ looks like a misread of ш |

The Goleizovsky one is worth a decision rather than a guess: the roster spells
him `Галейзовскій`, the review `Голейзовскій`, and the historical form is
Голейзовский. That is a question about the ROSTER's spelling, so it wants the
roster page, not the review page.

### Effect

Mentions 27,237 -> **27,409**; resolved 16,979 -> **17,135**; person mentions
joining `research.person` 12,829 -> **12,985** (+156). Dates still 139/139, all
referential checks 0.

---

## Selector churn investigated — 2026-10-09

I said the 16 re-merge changes "contradict `select_reading`'s own first rule."
**That was wrong, and reading the code settles it:** rule 1 covers *dropped*
(empty) candidates, not truncations, so these fall through to rule 7, majority
vote. Three distinct things were happening, and one of them was mine.

### `«Galop»` was my bug, not the selector's

No view reads `Галор`. It came from the mixed-script repair: the model wrote
`«Gалor` for `«Galop`, the `л` satisfied the new `CYRILLIC_ONLY` test, and the
word was "repaired" into Cyrillic — on a page printing `«Scène dansante»`,
`«Pas des cerises»` and `«Galop»` in Latin all around it. **Scan-confirmed:
the print reads `«Galop comique»`.**

The premise `a Cyrillic-only letter proves the word is Russian` fails in one
direction: a LATIN word the model partly Cyrillicised also contains Cyrillic
letters. The rule now declines any word opening with a Latin capital, which is
the shape of a foreign proper noun or title. Lowercase-initial romanisations
(`dekoraцій`, `teатрѣ`, `tenоръ`) are unaffected. `Gалor` -> `Galop` is in the
corrections table, and the corpus instance is fixed.

### I had `Фредерикъ` backwards

`merged_full` contains **`Фре- Фредерикъ;`** — the head duplicated. The
re-merge producing `Фре-` + `дерикъ;` was therefore **correct**, and what I
logged as a regression was a fix. The cause is a view reading a line-split word
WHOLE and the whole reading landing at the tail position, so the head appears
twice.

Acting on the misdiagnosis, I added a selector rule preferring the longer of
two readings at a position, and applied it to the corpus. **It created 396 of
these duplications** — `повѣ-` + `ряетъ` became `повѣ-` + `повѣряетъ`. Caught
by diffing before trusting, fully reverted, and the rule is gone from
`select_reading.py` (self-test back to 13/13). The corpus was restored from the
pre-change copy and verified clean.

**Five genuine duplications that predate all of this were then fixed** —
`Фре- Фредерикъ`, `Кше- Кшесинская`, `слиш- слиш- комъ`, and two more — and
`duplicated_head_after_hyphen` is now a standing check. It requires a 3+
character head, because a two-letter one gives false positives where the tail
legitimately begins with it (`по-` + `пойка` is `попойка`).

### What the churn actually is

Correlated errors across views. On `review_1893-94_MSK_ballet_p010` the
full-page and 4-band views agreed on a reading the 2-band view got right, so
majority voting returned the wrong answer 2/3. The three views were measured at
54% error overlap and assumed to decorrelate enough for a vote; where they do
not, rule 7 has no defence. **Not fixed** — the obvious fix was tried above and
was worse than the disease. Any future re-merge still carries roughly two dozen
such differences, which is why `merged_full` is maintained by targeted repair
and why a rebuild must be diffed rather than trusted.

---

## Curated review-person variants, and a Wikidata finding — 2026-10-09

`docs/eval/review_person_variants.csv` maps a spelling the REVIEWS use that no
roster carries, onto the roster's canonical surname. Two entries so far, both
scan-verified. Keyed on the **surname**, not a person_id, because the review
often gives no ordinal: `Соляниковъ` maps to `Солянниковъ`, where the rosters
hold two men, and the ranker chooses between them.

Curated rather than inferred: spreading variants across a family
automatically was tried and reverted, since it fixed two cases and cost 70
resolutions by admitting every family member as a candidate everywhere.

### Голейзовскій = Галейзовскій, settled

**Wikidata Q19974678**, Kasyan Goleizovsky (1892–1970). The patronymic
objection dissolves: his Czech father **Ярославъ Матвеевичъ** was baptised
**Карлъ-Ярославъ**, so the yearbook's `Карловичъ` and the usual `Ярославич`
are both correct. The biography matches our records exactly — graduated the
Petersburg school **1909** (our 1908-09 SP review lists him among the
graduating `воспитанники`) and transferred to the Bolshoi **1 August 1909**
(the Moscow roster picks him up in **1909-10**).

The о/а split tracks the **city**, not two families: Petersburg sources (the
1905-06 Graduates list, this review) print `Голейзовск-`, the Moscow rosters
`Галейзовск-`.

### The Wikidata scan is overdue, and its filter has a blind spot

Two separate problems, found while checking the above.

**1. The roster-side scan has not run since 15 August 2026.** Of 350
pilot-eligible people, 334 are unlinked; 48 of those are in the August review
queue (queried, no confident match) and **286 were never queried at all**.
Among them: Николай Малько, Феликсъ Блуменфельдъ, Вѣра Фокина, Василій
Тихомировъ, Николай фонъ Бооль.

**2. More seriously, the notability filter cannot see the most famous
dancers.** `NOTABLE_ROLE_KEYWORDS` matches the rank the yearbook printed **at
the time** — Солистъ, Балерина, Балетмейстеръ — so anyone still in the corps
or coryphée during the corpus window is never eligible, however famous they
became. Confirmed not eligible, and unlinked:

| | review mentions | Wikidata |
|---|---|---|
| **Павлова 2-я, Анна** | 99 | none |
| **Кшесинская, Матильда Феликсовна** | 98 | none |
| Карсавина, Тамара Платоновна | — | none |
| Нижинскій, Вацлавъ Ѳомичъ | — | none |
| Галейзовскій, Кассіанъ Карловичъ | 1 | none (Q19974678 identified by hand here) |

**The review mention layer is a better notability signal than printed rank,**
and it is now available. Ranked by mentions, the unlinked list reads:
Трефилова 171, **Леньяни 150** (Pierina Legnani), Рославлева 134, Конецкая
123, Гиллертъ 114, Сѣдова 105, **Павлова 99**, **Кшесинская 98**, Сланцова 95,
Бекефи 93 — against linked ones like Гердтъ 332 and Преображенская 281, so the
signal clearly separates. Proposed: add "appears N+ times in the reviews" as a
second eligibility rule beside the rank keywords, then re-run. The Wikidata
read API is public and unbilled; the only cost is time.
