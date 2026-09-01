# Known issues — season reviews

Kept separate from `known_issues.md`, which tracks the tabular pipeline.
Same discipline: triage by cause, so nothing gets re-diagnosed later.

Causes are labelled: **model** (the VLM's behaviour), **prompt** (our
instructions), **schema/code** (ours), **inherent** (VLM non-determinism),
**convention** (an open question about what the right answer even is).

---

## 1. `personnel_news` is not being produced — model

*Found 2026-08-30, smoke test on `review_1894-95_SP_ballet_p000`.*

Blocks opening `Приняты на службу:` and `Оставили службу:` — the canonical
cases, and the exact trigger phrases named in the prompt — came back typed as
`paragraph`. The prompt was strengthened once (explicit trigger list, "do not
label them paragraph") with no effect on this page.

The model also merged the lead-in sentence (`Въ теченіе сезона въ составѣ
труппы произошли слѣдующія перемѣны:`) with the list that follows into a
single block, so the boundary is not being seen either.

Not yet diagnosed further: one page is not evidence about the corpus. Measure
against the gold set before tuning again — `personnel_news` appears on gold
pages #6 and (as a section boundary) elsewhere, so the eval will give a real
rate rather than an anecdote.

Note that this type is **provisional** (docs/season_reviews.md §4). If it
proves unreliable *and* RG drops it, the issue dissolves — the text is
captured verbatim either way. Worth knowing before investing in prompt work.

## 2. Bold not detected — model

*Found 2026-08-30, same page.*

`«Евгеній Онѣгинъ»` is set bold in the printed text; the model returned it
with no `bold` flag. Разрядка on the same page WAS detected correctly, so
typographic capture is partly working rather than absent.

Relevant to the §11 decision rule: if bold precision/recall is poor across
the gold set, bold is dropped from rendering and nothing is lost, since the
characters are captured regardless.

## 3. Decorative ornament double-recorded — prompt

*Found 2026-08-30, same page.*

The prompt says a purely decorative ornament with no text is recorded ONLY by
`tailpiece_present`, with no `figure` block. The model set the flag correctly
*and* emitted an empty `figure` block. Harmless (an empty block contributes
no text) but it inflates block counts, which matters because block structure
is compared separately in the eval (§11).

Cheap to repair deterministically at parse time — drop `figure` blocks that
have neither spans nor caption — rather than spending more prompt on it.

---

## Resolved

### R1. Model emitted `type`, not `block_type` — prompt *(fixed 2026-08-30)*

The first prompt described the block types but never gave the literal JSON
key names, so the model invented its own. Every page failed schema
validation. Fixed by adding an explicit output skeleton to the prompt, and
by accepting `type` as an alias in the schema so an already-paid-for run is
never wasted by key drift.

### R2. Разрядка written as literal letter-spacing — prompt *(fixed 2026-08-30)*

The heading came back as `"Б а л е т ъ."` with `razryadka: true` — the
corpus-poisoning failure mode docs/season_reviews.md §5 exists to prevent,
occurring on the very first page transcribed.

Two fixes: a worked WRONG/RIGHT example pair in the prompt, and a targeted
repair in the schema — when a span is flagged `razryadka` AND its text is
literally letter-spaced, the spacing is closed up. That repair is lossless
precisely because the flag tells us the spacing is typography rather than
characters. Unflagged spans are left alone, since there we cannot distinguish
letter-spacing from genuinely spaced initials.

### R3. Letter-spacing detector had a crippling false-positive rate — schema/code *(fixed 2026-08-30)*

The first detector, `(?:\w\s){2,}\w`, fired on almost every block of ordinary
Russian, because one-letter words are everywhere (`г. Ершовъ и г. Морской`).
Now requires four or more consecutive single letters separated by single
spaces, which does not occur naturally and matches `Б а л е т ъ` exactly.
