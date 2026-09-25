# Work normalization: strategy and implementation

`entities.work` groups `raw.event_entry_performance` rows by canonicalized
`(title, genre)` text (`docs/research_dataset.md`), on the premise that a
revival across seasons should correctly collapse to one row. Checked
against the real data before writing anything down, prompted by a concrete
example: **"Жизнь за Царя" (A Life for the Tsar) currently exists as 5
separate `entities.work` rows**, not one, with 195/39/4/2/1 appearances
respectively. That split is real data noise, not 5 different pieces — and
it turns out to be one instance of four distinct, quantifiable problems
across the whole corpus. **Implemented** in `build_work()`
(`pipeline/build_entities.py`) — real results below the strategy section.

## The five "Жизнь за Царя" rows, and what's actually wrong with each

| canonical_title | canonical_genre | appearances | problem |
|---|---|---|---|
| `Жизнь за Царя` | `оп.` | 195 | none — this is the correct, clean row |
| `Жизнь за Царя, оп.` | `оп.` | 39 | genre abbreviation duplicated into the title text |
| `Жизнь за Царя, оп.` | *(blank)* | 4 | same title-duplication, and genre wasn't separately captured at all |
| `1-е и 2-е д. оп. Жизнь за Царя` | *(blank)* | 2 | this is Acts 1–2 only, not the full opera — a partial performance, not a different work |
| `1-я карт. 4-го д. оп. Жизнь за Царя` | `Пари.` | 1 | Act 4, Scene 1 only, and the genre field holds something unrelated |

## Four problems, sized against the full corpus

**1. Genre abbreviation duplicated into the title text.** 787 of 5,248
`entities.work` rows (15%) have a canonical_title ending in `, <genre
abbreviation>.` — e.g. `Жизнь за Царя, оп.`, `Спящая красавица, бал.`. Of
those, **504 have an exact bare-title + matching-genre counterpart
elsewhere** in the table already — meaning stripping the suffix and
re-keying would directly collapse over 500 phantom duplicates on its own,
no judgment calls needed.

**2. Genre-field spelling/OCR variance splits an identical title into
multiple work rows.** 517 distinct title texts are currently split across
2+ `work_id`s purely because their genre field values differ (typo
variants, OCR noise, or blank vs. filled) — **699 "phantom" extra work
rows** (13% of the total 5,248) that shouldn't exist as separate rows at
all. Real examples pulled from the data:
   - `Фаустъ`: split 6 ways across `оп.` / `драмат. новма.` / `драм. новма.`
     / `драмат. поэма` / `др. поэма` / `драм. поэма` — all "dramatic poem,"
     spelled/abbreviated differently.
   - `Великая тайна`: split 8 ways across `эт.` / `втюдь` / `этюдъ` /
     `этоидь` / `этюль` / `вт.` / `ком.` / `этюдь` — visibly OCR noise on
     a single genre word, "этюдъ" (etude/study).
   - `Спящая красавица`: split across genre `бал.` vs. **blank** — the
     single most common variance shape (a title repeated with genre simply
     missing one of the times it was captured).

   This is the highest-volume problem by far, and the fix is different
   in kind from #1: it's not text cleanup on `canonical_title`, it's a
   question of whether genre should be part of the *identity key* at all,
   or a separate descriptive attribute reconciled after the fact (see
   Open questions).

**3. Genre/title field cross-contamination on multi-work bills.** A
smaller, structurally different problem: on a bill with more than one
piece that night (6,158 of 17,345 sessions list more than one work —
already documented in `docs/entity_centric_model.md`), the extraction
sometimes puts a *different work's title* into the `genre` column of an
adjacent row, rather than a real genre. Worst case found: `Гимнъ` (the
anthem, typically a short curtain-raiser before a main piece) has **11
distinct "genre" values**, several of which are unmistakably real work
titles from the same bill — `Евгеній Онѣгинъ`, `Ревизоръ`, `Жизнь за
Царя`, `Паяцы`, `Старый закалъ`, `Новое дѣло`. This is an extraction-layer
confusion, not a canonicalization problem — checked a few other
high-genre-variance titles (`Великая тайна`, `Волшебные звуки`, `Красный
цвѣтокъ`) specifically to make sure this wasn't the dominant pattern
everywhere, and it isn't: those turned out to be ordinary OCR noise (#2),
not cross-contamination. `Гимнъ` looks like a genuine, specific edge case
tied to how curtain-raisers get printed alongside a main work, worth its
own hand-curated fix rather than a general rule.

**4. Excerpt / partial-performance titles modeled as unrelated works.**
**178 `entities.work` rows, 246 appearances**, whose title is an act/scene
marker prefix followed by a genre and the real base title — e.g. `2-е д.
бал. Фіаметта` (Act 2 of the ballet *Fiametta*), `4-е д. оп. Гугеноты`
(Act 4 of *Les Huguenots*), `1-я карт. 2-го д. оп. Пиковая дама` (Act 1,
Scene 2 of *The Queen of Spades*). These are genuine excerpts of famous,
separately-cataloged repertory pieces (Swan Lake, Coppélia, Ruslan and
Lyudmila, Sleeping Beauty, The Nutcracker all appear in this list) — a
real, common 19th-century Imperial Ballet/Opera programming practice
(pairing a single act with other pieces on a mixed bill), not noise to
discard. A meaningful minority of these rows (roughly a dozen spot-checked)
have the title/genre split so garbled that neither field holds a coherent
base title at all (e.g. `canonical_title = "1-го д."`, `canonical_genre =
"2-я карт."`) — these will need hand review, a regex alone won't
reconstruct them confidently.

Note: `картина` ("tableau/vignette") is a **real, legitimate genre** for
short standalone pieces (`Лѣтняя картинка, карт.`), not always an excerpt
marker — the excerpt pattern is specifically an *ordinal number* at the
very start of the title (`2-е д.`, `1-я карт.`, `3-й актъ`), not the
presence of "карт." anywhere in the string. Conflating the two in a first
pass produced false positives; the numbers above are from the corrected,
prefix-anchored check.

## `canonical_genre` itself: same problem, viewed from the other column

424 distinct `canonical_genre` values exist across the 5,248 works. Most of
that variety is real and should stay — `_genre_key()` deliberately never
folds across language or case, because a French work's genre is printed in
French (`com.`, `pièce`, `vaud.`) and a German work's in German (`Lustsp.`,
`Schausp.`), and collapsing those would blur a genuine fact about the
performance, not fix noise. `ком.` (923 works) and `com.` (630 works) are
almost certainly "comedy" in Russian vs. French respectively — correctly
kept apart.

But a purely mechanical check — lowercase + strip a trailing period only,
nothing language-aware — still collapses 424 raw genre strings down to 376
(**48 values were pure formatting noise**, not real distinctions):
`ком` vs `ком.`, `com.` vs `com` vs `Com.`, `Lustsp.` vs `Lustsp`, `Траг.`
vs `траг.`, and so on, together covering thousands of appearances (the
`ком`/`ком.` pair alone spans 5,581). This is a strict subset of Problem
#2 above (the same OCR/spelling variance that splits `entities.work` rows
also makes `canonical_genre` itself inconsistent for anyone trying to
facet/filter by genre directly, e.g. in Datasette), but it's worth naming
separately because the *safe, no-judgment-call* portion of it (case +
trailing-period folding) can be done as a small, independent, low-risk
first step regardless of how the harder genre-vs-identity-key question
(Problem #2, Open questions) eventually gets resolved.

## `appearance_count`: the mechanism is correct, the input isn't

Sanity-checked directly: every `entities.work.appearance_count` value
matches a fresh `COUNT(*)` over `entities.work_link` for that `work_id` —
**zero disagreements** across all 5,248 rows. The computation itself has
no bug. The problem is entirely upstream: `appearance_count` is only as
trustworthy as the grouping that produced the row it's attached to, and
Problems #1/#2/#4 mean a lot of rows are undercounting a more-performed
piece rather than correctly counting a rare one.

Concretely, for the motivating example: the visible `Жизнь за Царя` row
shows **195**, but the true combined total across all 5 split rows is
**241** — a 19% undercount, for one of the best-known operas in the
repertoire. This generalizes: of the **2,312 works with
`appearance_count = 1`** (44% of all works), **977 (42% of the singletons)**
are flagged by at least one of Problems #1/#2/#4 — meaning a large chunk of
what looks like "performed exactly once" is actually a noise-fragment of a
work performed more often, not a genuine one-off. Across the whole table,
**2,034 of 5,248 works (39%) are touched by at least one of the three
problems** — so `appearance_count` shouldn't be trusted for "how often was
this performed" research questions until the underlying grouping is fixed;
no separate fix to the column itself is needed once that happens, since the
computation already does the right thing with whatever rows it's given.

One more thing surfaced while checking this, worth a quick manual look
rather than a pipeline fix: **6 sessions have an exact duplicate raw row**
(same session, same work title, same genre, printed twice) — 4 of them
`Гимнъ`. Could be genuine (the anthem performed at both the start and end
of an evening is a plausible real practice) or an extraction duplicate.
Six is few enough to check directly against the source page image rather
than guess.

## Proposed strategy, by problem

1. **Strip the genre-duplication suffix before computing the title key**,
   the same way `_title_key()` already vowel-folds and trims punctuation —
   `canonical_title` itself (the display value) can keep the fuller printed
   form if that's judged more faithful, but the *grouping key* should not
   see `, оп.` as different from no suffix at all. Mechanical, low-risk,
   directly resolves the 504 confirmed-identical cases from problem #1.

2. **Demote genre from co-equal identity key to a reconciled descriptive
   attribute.** Concretely: group `entities.work` on title alone (folded
   the same way as today), and pick canonical_genre as the most common
   *non-blank* genre variant seen across all members of that title
   cluster — the same "most common variant wins" rule `build_work()`
   already uses for `canonical_title` itself, just applied to genre
   independently instead of as part of the grouping tuple. This is the
   single highest-leverage fix (699 of the ~5,248 rows) but it's a real
   modeling change worth confirming before building, not just a cleanup
   pass — see Open questions.

3. **Hand-curate the small number of cross-contamination cases** (`Гимнъ`
   and any others surfaced by a full audit of "titles with an unusually
   high count of distinct genre values that don't reduce to spelling
   variance") rather than trying to write a general rule — the failure
   mode is specific enough (adjacent-bill-item bleed) that a general regex
   risks corrupting genuinely-fine rows elsewhere.

4. **Link excerpt rows to their parent work rather than merging or
   discarding them.** A performance of "Act 2 only" is a real, different
   fact from a full performance — box-office and reception research may
   care about that distinction — so this shouldn't collapse into the same
   row the way problems #1/#2 should. Proposed shape: an
   `excerpt_of_work_id` (nullable FK to `entities.work`) plus a plain-text
   `excerpt_note` (e.g. "Act 2", "Act 4, Scene 1") on the excerpt's own
   row, extracted via the same ordinal-prefix pattern used to size this
   problem above. The ~dozen garbled title/genre rows should be flagged
   for manual review rather than auto-parsed, same "don't guess" discipline
   as the Person pipeline's ordinal-suffix handling.

5. **Fold `canonical_genre` on case + trailing period, independent of and
   before the harder question in #2.** Safe regardless of how the
   identity-key question resolves, since it never merges across the
   language boundary `_genre_key()` protects — just removes the 48 purely
   mechanical duplicate spellings. Cheap, no open question attached, worth
   doing first.

6. **No fix needed for `appearance_count` itself** — verified its
   computation is already correct (zero mismatches against a fresh count).
   It will self-correct once Problems #1/#2/#4 are fixed, since it's a
   straight count over whatever rows `entities.work_link` resolves to.
   Separately, manually check the 6 exact-duplicate-raw-row sessions
   (`Гимнъ` ×4 and two others) against their source page images — cheap to
   verify, and not something a general rule should guess at.

## Implementation

`build_work()` (`pipeline/build_entities.py`) now implements strategy
items #1, #2 (safe portion only), #3, #4, and #5 together. Real results
against the full corpus:

| | Before | After |
|---|---|---|
| `entities.work` rows | 5,248 | **4,509** (-739) |

- **593 works** now collapse more than one raw spelling variant into a
  single canonical row (strategy #1 + #5 combined — the genre-suffix
  strip and case/period fold both feed the same title-grouping step).
- **137 title groups** merged a blank-genre printing into an existing
  non-blank-genre work — the safe portion of strategy #2, applied whenever
  a title has at most one distinct real genre after folding.
- **355 titles (898 work rows) flagged in the new
  `entities.work_genre_candidate` table** — every title where 2+
  genuinely distinct genre folds remain (Карменъ's `оп.`/`бал.` and
  Фаустъ's OCR-noise cluster both land here). **Resolves the Open Question
  below**: rather than build an edit-distance heuristic to guess which
  splits are real adaptations versus noise (tested directly on
  `оп.`/`бал.` and `com.`/`ком.` — both sit at the same small edit
  distance as genuine OCR noise, so distance alone can't tell adaptation
  from typo), the implementation never auto-decides this case at all —
  every one of the 898 rows stays a separate, valid `entities.work` row
  exactly as before, just now flagged for a human to actually merge by
  hand if they choose to (no apply-side tooling built yet, since no
  review has happened; see Person's
  `apply_person_merges`/`reconcile_person_merges` for the pattern to reuse
  once this queue has been through review).
- **Of those 355, 49 are `likely_cross_language`** — every distinct genre
  fold on the title is written in a different script (Cyrillic vs. Latin),
  which means the title was already correctly split by language and
  needs no human decision at all; excluded from the exported review
  queue. That leaves **306 titles (775 work rows)** in
  `outputs/full_run/work_genre_review_queue.csv` genuinely needing a
  human call. (An earlier, throwaway analysis script put this at 98
  cross-language / 257 needing review — it was counting a blank/missing
  genre as its own "script," which wrongly flagged same-script titles
  like a bare `com.`/`pièce` pairing plus a blank member as
  cross-language. The in-pipeline `_genre_script()` classification
  excludes blanks and is the correct number.)
- **`Гимнъ`'s cross-contamination genres** (strategy #3) are now excluded
  via the small, hand-curated set found during investigation (`Новое
  дѣло`, `Евгеній Онѣгинъ`, `Паяцы`, `Сверхъ комплекта`, `Ревизоръ`,
  `Старый закалъ`, `Жизнь за Царя`) — treated as missing genre data for
  `Гимнъ` specifically, not folded into any general rule.
- **138 excerpt/partial-performance titles linked** to their parent work via
  `excerpt_of_work_id`/`excerpt_note` (strategy #4), up from 96 as of
  2026-09-25 (issue #88); **21 left unlinked**, down from 49. The regex
  needed several real fixes beyond the design in this doc:
  - A first version only handled a single ordinal+marker or an
    "и"-joined pair ("1-е и 2-е д."), missing the equally common
    "scene-of-an-act" shape with two independent markers back to back
    ("1-я карт. 4-го д.", "Scene 1 of Act 4") — caught by checking the
    motivating example end-to-end (all 3 remaining "Жизнь за Царя" rows,
    including both excerpts) rather than trusting the regex from the design
    alone.
  - A 1-or-2-unit cap on the marker group left a mangled leftover fragment
    (not the bare base title) as the extracted "base" for any title citing
    3+ separate act/scene references (e.g. "1-е д., 1-я карт. 2-го д. и
    1-я карт. 4-го д. Аида") — 11 titles were silently unlinkable for this
    reason alone; fixed by letting the marker group itself repeat up to 4
    times.
  - The genre word between the marker and the base title is sometimes
    spelled out in full, genitive case, with no trailing period ("балета",
    "оперы", "драмы" vs. the abbreviated "бал.", "оп.", "др.") — missed by
    the abbreviation-only pattern, leaving the genre word stuck onto the
    front of `base` (e.g. "1-е д. балета Калькабрино" → base wrongly
    "балета Калькабрино"). Fixed by adding a genitive-word alternation,
    plus (separately) a small `_GENITIVE_GENRE_TO_ABBREV` map used *only* at
    the excerpt-linking tiebreak, never touching the shared `_fold_genre()`
    function's deliberate no-abbreviation-normalization contract.
  - The ambiguous-candidate tiebreak now also falls back to the excerpt
    row's own `canonical_genre` database field when the title has no
    inline genre word at all (e.g. "3-е д. Аида", genre "оп." on the row
    itself but nothing inline) — several otherwise-resolvable cases were
    previously left unlinked purely for lack of this fallback.

  **Of the 21 still unlinked** (issue #88's final categorization):
  - **14 have no standalone parent anywhere in the corpus at all** — a
    correct, final state, not a bug (these excerpts were apparently never
    billed as a full stand-alone performance in any of the 18 seasons).
    Notably "1-е д. ком. Нахлѣбникъ" / "1-е д. изъ ком. Нахлѣбникъ" (10
    combined appearances) and "2-я и 3-я карт. бал." (4 appearances,
    always the *second* item in a 3-work bill — see below, this is a
    different bug class, not an unlinked excerpt at all).
  - **4 are genuine cross-work ambiguity needing a human call**, not a
    mechanical fix: two different "Русалка" candidates (opera vs. a
    "1-я сцена"-genre work, possibly the same drama mislabeled); two
    different "Пахита" candidates (one with a contaminated "3 д. бал."
    genre field); two different "Царь Борисъ" candidates (траг./др.); and
    "Прекрасная Елена" whose own genre field ("оп.") doesn't match any of
    its 3 real operetta-genre candidates, suggesting the excerpt row's
    genre may itself be a period mislabeling.
  - **2 are structurally not a single-parent excerpt at all**: one compound
    bill citing 3 different ballets in one title ("Конекъ-Горбунокъ, бал.
    Пахита и 2-е д. бал. Фіаметто"), and one where the printed title text
    genuinely didn't survive extraction ("2-я карт. 2-го акта и 1-я
    карт." — no base title follows the markers at all).

  **A separate bug found during this triage, not an excerpt-linking
  problem**: "2-я и 3-я карт. бал." (4 appearances, all Маріинскій,
  1895-96) is not an independent excerpt-of-another-work at all — checking
  the raw JSON shows it's always the *second* work in a 3-item list
  (`["<a real ballet>", "2-я и 3-я карт. бал.", "Своенравная жена"]`),
  meaning the printed billing is literally "[Ballet], 2nd & 3rd tableaux"
  as one continuous entry, split by extraction into two separate `works`
  array items instead of one. `_EXCERPT_PREFIX_RE`'s corpus-wide
  title-matching mechanism can't resolve this (there's no title text to
  match against), because the real fix is same-session adjacency ("this
  performance continues the immediately preceding work in this same
  billing"), a different mechanism than Problem #4 as designed. Not fixed
  this round — flagged here rather than force-linked, since it needs new
  logic (session-scoped, not corpus-wide) that would need its own design
  pass.

The motivating example now resolves cleanly: **1 main work (238
appearances, correctly summing the 195+39+4 safely-merged rows) + 2
properly-linked excerpts**, down from 5 disconnected rows.

## Open questions

- ~~Does demoting genre out of the identity key ever lose something
  real?~~ **Resolved by not automating it**: `Карменъ` (`оп.`/`бал.`) and
  `Конекъ-горбунокъ` (`бал.`/`траг.`/`оп.`) are exactly the kind of case
  this was worried about, and both now sit in
  `entities.work_genre_candidate` for human review rather than being
  merged (or not) by an edit-distance guess. Revisit only if the review
  queue turns out too large to work through by hand and a corroborating
  signal (mirroring Person's tenure/Wikidata approach) becomes worth
  building.
- **Should `excerpt_of_work_id` count toward `appearance_count`?** If a
  researcher asks "how many times was Swan Lake performed," should that
  include the excerpt-only nights? Probably yes for a combined count, but
  the raw distinction (full vs. excerpt) needs to stay queryable
  separately — this needs the researcher's judgment on what "a
  performance" means for this kind of question before building the field.
- **Is `Гимнъ`'s cross-contamination pattern worth a general "adjacent
  bill item" heuristic**, or is a dozen or so hand-fixed rows genuinely
  the whole problem? Needs a fuller audit (this doc checked 4 candidates,
  not all high-genre-variance titles) before deciding.
