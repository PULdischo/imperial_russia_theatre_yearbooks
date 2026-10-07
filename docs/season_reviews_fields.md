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

### `review_assertion` — the thing RG actually wants

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
