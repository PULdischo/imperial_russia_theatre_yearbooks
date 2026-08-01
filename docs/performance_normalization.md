# Performance normalization: strategy

Continuing from `docs/work_normalization.md` (title/genre cleanup) and
`docs/entity_centric_model.md` (the proposed `entities.performance` fact
table), this covers three things for the performance-level data
specifically: keeping the verbatim title/genre while relating each
performance to the *normalized* work identity once `work_normalization.md`
is built, the same question for genre, and a real standardized date
column. This is a plan only — nothing here is implemented.

## Title and genre: verbatim stays, plus a link to the normalized identity

Once `work_normalization.md`'s fixes land, `entities.work` will no longer
have the ~2,034 duplicate/phantom rows it does today, and `canonical_title`
will be a clean, deduplicated identity rather than a raw grouping key. The
right shape for a performance-level record is what this project already
does everywhere else (`docs/schema.md`'s raw/analysis split, Person's
`display_name` vs. printed spelling): **keep the exact printed text as its
own field, never overwritten, and add a separate FK to the resolved
identity** —

```
raw.performance_work.work_title    -- printed text, untouched (already exists)
raw.performance_work.genre         -- printed text, untouched (already exists)
entities.work_link.work_id         -- FK to the corrected entities.work row (already exists,
                                       just needs work_normalization.md's fixes applied to
                                       what it resolves to)
```

`entities.work_link` already does exactly this job structurally — nothing
new needs to be invented here, it just needs `entities.work` itself fixed
first. The one real gap: **genre currently has no equivalent lookup
table**. If `work_normalization.md`'s Problem #2 fix goes ahead (genre
demoted from identity key to a reconciled attribute), a small
`entities.genre` reference table — `genre_id`, canonical form, language —
would let a performance record carry a clean `genre_id` FK the same way
`work_id` does, rather than a repeated free-text string. Small table
(a few hundred rows at most, likely fewer once the 48 mechanical
duplicates from `work_normalization.md` are folded), same hand-seedable
spirit as `entities.theater`.

## A standardized date column

`raw.performance_session` already has more than `date_text` suggests at
first glance — `month_text`, `year_text`, and a combined `date_undate`
(ISO `YYYY-MM-DD`, e.g. `1890-08-16`) all exist and are populated for
23,670 of 23,726 rows (99.76%). **The "missing month" impression came from
`build_datasette.py`'s `WORK_PERFORMANCES_SQL`, which only selected
`date_text`** and dropped the other three columns from the exported join
view — already fixed as part of this conversation (not a data gap, an
export gap).

That said, checking whether the underlying `month_text`/`date_undate`
values are actually *correct* (not just present) turned up a real,
significant issue.

### Cross-validating with the day-of-week

`date_text` carries the day-of-week name alongside the day number (e.g.
`16 Понед.` — "16, Monday"). That's an independent, verifiable fact: given
a candidate (year, month, day), the Julian calendar (this corpus's dates
are Old Style, per `docs/schema.md`) determines exactly one correct
weekday. If the printed weekday doesn't match what the calendar says for
the stored `date_undate`, something's wrong with that row's date.

Checked against `convertdate`'s Julian calendar conversion (structurally
verified against the well-documented October Revolution date — 25 October
1917 Julian = 7 November 1917 Gregorian — before trusting any result from
it):

- **22,611 rows had a parseable day-of-week; 2,002 of them (8.9%) don't
  match** what the Julian calendar says for their stored date.
- **This is not evenly spread — it's heavily concentrated in one block of
  seasons**: 13–45% mismatch rates in 1891-92 through 1896-97, versus 0–4%
  in every other season (1890-91, 1897-98, and 1898-99 through 1907-08 all
  sit under 4%, most under 1%). This points to a systematic defect
  specific to how those years' volumes were extracted, not general OCR
  noise (which would be roughly uniform across seasons) or a source-wide
  printing convention issue.
- **3 rows have an outright invalid calendar date** (`1902-11-31` — November
  only has 30 days).

### What actually explains the mismatches

Tested whether a nearby correction resolves each mismatch — trying the
adjacent month (same day number) and the adjacent day (same month) before
giving up:

| Resolution | Count | Share |
|---|---|---|
| Adjacent month fixes it | 573 | 29% |
| Adjacent day fixes it | 557 | 28% |
| Unresolved by either | 872 | 44% |

Both failure modes are real and roughly equally common — some rows
genuinely have the wrong month attributed (consistent with a header/
month-block being misattributed during extraction), others have a
single-digit day-number error (OCR or a transcription slip) — and neither
one dominates. The unresolved 44% cluster in the *same* problem seasons
as the resolved ones (1891-92 through 1896-97 account for the vast
majority of both resolved and unresolved cases alike), confirming this is
one unified phenomenon tied to that specific stretch of source volumes,
not two unrelated causes layered on top of each other.

### Spot-checked against the actual source page — root cause confirmed, and the ±1 heuristic confirmed unsafe

Pulled the page image for `repertoire_1890-91_p001` (one of the flagged
mismatches, in a season otherwise mostly clean) and read the date column
directly, row by row, rather than trust either the database or a first
low-resolution look at the page. **The printed source is internally
perfectly consistent with the true Julian calendar** — every row's day
number and weekday name agree with each other and with `convertdate`,
including a legitimate 2-day gap (13th–14th) where the theaters were
simply dark. This rules out a source-document error for this page: the
defect is in extraction, not the original printing.

Mapping the actual stored values against the true calendar for this run
of rows (page 001, September 1890) shows exactly what kind of extraction
error it is:

| DB day | DB weekday | True weekday for DB's day | Day whose *true* weekday matches DB's word |
|---|---|---|---|
| 12 | Среда | Среда | 12 (correct) |
| 13 | Суббота | Четвергъ | **15** |
| 16 | Понед. | Воскр. | **17** |
| 17 | Вторн. | Понед. | **18** |
| 18 | Среда | Вторн. | **19** |
| 19 | Четвергъ | Среда | **20** |
| 20 | Пятница | Четвергъ | **21** |
| 21 | Суббота | Пятница | **22** |

The weekday *word* is reliably correct on every single row — it's the day
*number* that's under-counted, by +2 starting at the first affected row
and then a steady +1 for every row after it. This is a clean, well-defined
failure mode (day-number drift within a run of otherwise-correct rows),
and it confirms the core methodology (weekday-as-anchor) is sound.

**But it also disproves the ±1 auto-correction heuristic proposed in the
first draft of this doc.** For the first affected row (DB's "13"), a naive
±1 search finds no valid same-month day fix — but it *does* find a
coincidental match by shifting the **month** backward (September 13 →
October 13 both land on a Saturday). That "fix" is confidently wrong: the
real answer, confirmed against the page image, is September 15, not
October 13. Auto-applying the month-shift heuristic here would have
silently replaced one wrong date with a *different* wrong date. This is
exactly the risk flagged (but not yet demonstrated) in the first draft's
open questions — now confirmed with a concrete example, not just a
theoretical concern.

### Revised proposed approach

1. **Add the standardized date as its own field**, sourced from the
   already-existing `date_undate` — most of the work is already done; it
   just needs surfacing (done for the Datasette export) and a confidence
   signal before being treated as reliable.
2. **Never auto-apply a month-shift correction.** The spot-check above
   shows it can produce a confident, wrong answer by coincidence. A
   month-header misattribution is a real failure mode elsewhere in this
   corpus (`docs/work_normalization.md`'s Problem #3 documents a related
   but different field-crossing issue), but "the weekday happens to also
   match in an adjacent month" is not strong enough evidence on its own to
   rewrite a date.
3. **Treat day-number drift as a run-level phenomenon, not an isolated
   per-row fix.** The example above shows the error propagating across six
   consecutive rows with a consistent (mostly +1) offset once introduced.
   Rather than searching ±1 around each mismatched row independently, scan
   for the drift amount that makes an entire consecutive run agree with
   its weekday words, and apply that single correction to the whole run at
   once — far less prone to a coincidental false match than evaluating one
   isolated row.
4. **`date_confidence` should have at least four states**, not three:
   `verified` (matches, or nothing to check against), `corrected`
   (run-level day-drift correction applied, original value kept
   alongside non-destructively — same principle as
   `person.superseded_by_person_id`), `flagged_month_ambiguous` (a
   month-shift would resolve it, but per the finding above this must go to
   human review, never auto-applied), and `unresolved` (nothing above
   explains it — needs a source-image check before touching).
5. **Scope the first pass to the 1891-92 through 1896-97 seasons**, where
   nearly all of both the resolved and unresolved cases live — same
   pilot-first pattern already used for Wikidata linking, since the other
   12 seasons are already at or near 0% and don't need this pass at all.
6. **Spot-check a handful of pages per affected season against source
   images before building any automated correction**, the same way this
   one page was checked here — one page was enough to overturn a
   plausible-looking heuristic; a strategy built on database patterns
   alone, without ever looking at the actual page, would have shipped a
   confident wrong answer.

### Does this generalize into a broader OCR-error detector? Tested directly, and the answer is specific, not general

Worth asking explicitly: since the calendar mismatch is a free,
reference-free signal that a row's extraction went wrong somewhere, does a
mismatched row also predict *other* extraction defects on the same row
(garbled title, missing genre, missing receipts) — turning this into a
general page/row quality flag, not just a date-correctness check?

Tested directly rather than assumed, comparing blank-field rates between
mismatched and clean rows **within the same affected seasons** (not the
whole corpus, since the affected seasons could differ from the rest for
unrelated reasons):

| | n | blank receipts | blank genre | blank title |
|---|---|---|---|---|
| Date mismatch | 2,711 | 29.1% | 18.9% | 15.2% |
| Date OK | 5,932 | 30.1% | 22.3% | 16.2% |

No meaningful difference — **the signal does not generalize to other
columns.** This makes sense given the root cause found above: the date
column is printed **rotated 90°** on the page, a fundamentally different
visual/OCR problem from the horizontal-text title/genre/receipts columns.
A defect reading rotated digits doesn't imply anything about the same
row's horizontal text. Worth stating plainly since it would have been an
appealing but wrong conclusion to reach without checking.

**But looking for a broader signal surfaced a better one for the date
fields specifically**, calendar-independent this time: all 5 theaters
sharing one printed date-block should carry the **identical** `date_text`
string — it's one shared label, not 5 independently-read ones. Any
disagreement is a pure textual contradiction, no calendar interpretation
needed at all. Only 14 such blocks exist corpus-wide, but they're a
100%-certain error signal rather than a probabilistic one, and — useful
for correction, not just detection — a disagreement hands you two already-
extracted candidate readings to choose between (via the calendar check)
rather than an open-ended search. **9 of the 14 cluster on a single page**
(`repertoire_1895-96_p000`), a concrete, cheap next spot-check target.

The general lesson for this corpus: a self-consistency check built from
data the extraction already produces is valuable and worth deliberately
looking for elsewhere, but it should be expected to catch errors in the
*specific* field(s) that redundantly encode the same fact, not treated as
a stand-in for a general quality score across unrelated columns — confirmed
here rather than assumed.

## Open questions

- **How far can a day-number drift run before it self-corrects, and how
  do we find the run boundaries reliably?** The spot-checked example drifts
  by +1 for at least six consecutive rows — is that typical, or do some
  runs drift further, or reset mid-page? Needs more spot-checked pages
  (per season, not just the one checked here) before the "correct the
  whole run at once" approach in the revised strategy can be automated
  with confidence rather than done by hand per page.
- **Should `unresolved` rows keep their original (possibly wrong)
  `date_undate`, or should the field go `NULL` until verified?** Keeping
  it preserves ordering/filtering usability at the cost of occasionally
  showing a wrong date; nulling it is more honest but breaks any
  chronological query over the affected seasons entirely. Leans toward
  "keep it, but always show `date_confidence` alongside it" so a
  researcher can decide per-query whether to trust it.
- **What actually went wrong in 1891-92 through 1896-97 specifically?**
  This doc found *that* there's a defect and roughly *how much* one ±1
  search step can fix, but not *why* those six seasons specifically — that
  likely needs a look at the actual source page images for a few of the
  worst-affected pages (`docs/eval` already has the pattern for this kind
  of spot-check) before writing an extraction-side fix rather than only a
  post-hoc correction.
