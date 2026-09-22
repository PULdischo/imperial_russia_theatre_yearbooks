# Detecting silently-dropped Repertoire content (scoping doc)

## The gap this addresses

`pipeline/quality_checks.py`'s `duplicate_event_key` check (see
`docs/eval/known_issues.md` issue #77's addenda) catches a session that
got mislabeled or duplicated -- but only because a collision is visible
in the data. It is structurally blind to the case where the model
captured only one of two genuinely-printed УТРО/ВЕЧ sessions, or dropped
an annotation/extra work line outright: nothing collides, so nothing
flags. This doc scopes a detector for that blind spot. Nothing here has
been built yet except Tier 0, which is pure SQL against data already on
disk.

Prompted by RG asking (2026-09-22) how confident the corpus's
morning/evening session labeling should be, beyond what the
`duplicate_event_key` backlog work already fixed.

## Why the obvious cheap option isn't available

CLAUDE.md's pipeline recipe runs three independent Repertoire
extractions (baseline, row-level, column-wise) specifically so they can
be cross-checked against each other. If the row-level/baseline copies
had survived on disk alongside the canonical column-wise output, a
missing-session check would be a free three-way diff. They don't --
`outputs/` is disposable and only the canonical `*.raw.json` + the
`.duckdb` are kept once column-wise is established as the source of
truth for a season. Re-running the other two extraction methods
corpus-wide to get that diff back would mean re-incurring real paid API
cost. Everything below is designed to avoid that.

## Tier 0 -- pure SQL, already run, zero build cost

Two independent signals, both queryable from `raw.event_entry` as it
stands today (no image work, no new extraction):

**A. Annotation-anchored (strong signal).** 78 (page_id, date_text,
theater) slots carry a "Безплатные спектакли для воспитанниковъ"
free-matinee annotation (or a close variant -- "Безплатный спектакль
для...", "Всплатные..." OCR variant, etc.) directly on one of their
rows. Exactly 39 of those 78 already have a correct 2-session pair; the
other **39 have only one session recorded**. A clean 50/50 split on a
signal this specific is hard to explain as coincidence -- these are the
current highest-confidence candidates for a missed split.

```sql
with anno as (
    select distinct page_id, date_text, theater
    from raw.event_entry
    where annotation ilike '%воспитанник%'
),
counts as (
    select e.page_id, e.date_text, e.theater, count(*) as n
    from raw.event_entry e
    join anno a using (page_id, date_text, theater)
    group by 1,2,3
)
select n, count(*) from counts group by 1 order by 1
-- 39 groups with n=1, 39 with n=2 (2026-09-22)
```

Full 39-row candidate list logged in `docs/query_log.md`, 2026-09-22
entry. `repertoire_1899-00_p028` accounts for 15 of the 39, spanning
nearly every date on that page across three theaters -- worth checking
first, since a page this concentrated may have one systemic cause
rather than 15 independent misses. The rest are scattered singles
across `1898-99_p013/p017/p028/p038/p039`, `1900-01_p012/p022`,
`1901-02_p016`, `1902-03_p011`, `1903-04_p017`.

**B. Weekday split-rate (weak signal, ranking only).** Empirically,
Monday is the real high-split day for every theater (16-33% of Monday
date/theater slots have 2 sessions, vs 1-9% on every other weekday --
computed corpus-wide, not assumed). Too weak to flag anything on its
own, but useful as a secondary ranking weight once Tier 1 exists: a
single-session Monday is more worth checking than a single-session
Wednesday.

```sql
with per_group as (
    select page_id, date_text, theater_canonical, date_undate, count(*) as n
    from analysis.event_entry
    where date_undate is not null and date_undate != ''
    group by 1,2,3,4
)
select theater_canonical, dayname(try_cast(date_undate as date)) as wd,
       count(*) as n_groups,
       sum(case when n>1 then 1 else 0 end) as n_split,
       round(100.0*sum(case when n>1 then 1 else 0 end)/count(*), 1) as split_pct
from per_group
where try_cast(date_undate as date) is not null  -- Julian leap-year dates
                                                   -- (e.g. 1900-02-29) aren't
                                                   -- valid Gregorian dates;
                                                   -- try_cast skips them
group by 1,2 order by 1, split_pct desc
```

**Status**: query results in hand, not yet scan-verified against any
actual page image. Next step is working the 39-row list (page-by-page,
`1899-00_p028` first) the same way every other fix this session was
verified -- render the source PDF page, confirm against the actual
printed layout, only then touch data.

## Tier 1 -- row-height geometric screening: TRIED, ABANDONED 2026-09-22

**Do not restart this without reading this section first.** The
hypothesis below was tested directly against `repertoire_1898-99_p029`
-- a page with fully scan-verified ground truth from this session's
earlier `duplicate_event_key` work (confirmed compound rows: 21
Воскрес., 24 Среда., 25 Четвергъ., 26 Пятница.; confirmed single rows:
17/18/19/22/23; confirmed dark: 20 Суббота.) -- using
`row_detect.py`'s own `analyze_page`/`debug_visualize`, not a
hypothetical. The result contradicted the design below in an
informative way, not just "didn't work":

- **Synchronized splits work, sort of, but not via height.** On 21
  Воскрес. (all 3 theaters split together), the internal УТРО/ВЕЧ
  divider genuinely spans the full table width, so the existing
  detector picks it up as a real boundary and produces **two
  normal-height rows**, not one tall one. The signal that actually
  fires here is extra row *count*, not height -- the original
  hypothesis was wrong about the mechanism even in the case that works.
- **Partial splits (one theater splits, others don't -- confirmed the
  common case, e.g. 24 Среда. where only Большой splits) break it.**
  The internal divider has nothing to anchor to in the two unsplit
  columns, and the detector produced an anomalously *short* fragment
  (111px vs. a ~180px baseline) instead of a tall row.
- **Boundary tracking silently failed further down the same page.** By
  25-26 Четвергъ/Пятница (both also compound), the chain tracker lost
  the thread entirely -- one detected "row" spanned 565px, swallowing
  25 Четвергъ's evening half, all of 26 Пятница, and the page margin
  below it into a single blob.

This confirms the caveat this doc already flagged before testing:
`row_detect.py` was built and tuned against the two-page-spread format,
not the single-page column-wise corpus, and does not transfer cleanly.
RG's call (2026-09-22), given this: drop the CV approach rather than
sink more time debugging a detector fighting the wrong format; extend
Tier 0's SQL/text heuristics instead. If this is ever revisited, the
partial-split failure mode is the one to solve first -- it's the
common case, not the edge case, and the current detector actively
produces a misleading signal for it (short, not tall) rather than just
missing it.

**Also tried and ruled out** (2026-09-22, same session): searching
`annotation` for the literal marker text "утро"/"веч" as a proxy for
"the model saw a session label but didn't route it to `time_of_day`."
12 rows matched, all false positives -- every one is an ordinary
benefit-event title using the common Russian words "утро"
(morning)/"вечеръ" (evening, as in "an evening of...") as ordinary
nouns ("Музыкально-Литературный вечеръ" = "an evening of music and
literature"), not the structural УТРО./ВЕЧ. abbreviation. Not a viable
signal as stated; a stricter pattern (anchored, abbreviated form only:
`^УТРО\.?$`/`^ВЕЧ\.?$`) might avoid the false positives but wasn't
tried, since the underlying premise (session field failing to update
while the marker text leaks into annotation) has no confirmed real
example to test against yet.

## Tier 1 (superseded) -- original design, kept for reference only

`pipeline/row_detect.py` already does real per-row boundary detection
for this table format and already computes each detected row band's
height (`_adaptive_pads`'s `heights = row_boundaries[i+1] -
row_boundaries[i]`) as a byproduct of finding row boundaries at all. A
printed УТРО/ВЕЧ split cell is visibly taller than a single-session
cell -- two lines of content, an internal divider, and the vertical
label sub-column `detect_columns` already pads for explicitly (its own
docstring documents a past bug, #68, from clipping that sub-column).

Proposal: re-run row-boundary detection against each rendered page,
compute a per-page/per-season baseline single-row height (e.g. median),
flag any row exceeding roughly 1.5x that baseline as "structurally
looks compound." CPU-only, no paid calls, reuses code that already
exists and is already exercised elsewhere in this pipeline.

Deliberately biased toward recall over precision at this stage: a real
split will almost always be taller, so false negatives should be rare.
False positives (a single session with a long annotation, a benefit
notice, a 3-work bill) are expected and are Tier 2's job to filter, not
Tier 1's.

**Open caveat, not yet resolved**: `row_detect.py`'s row-splitting was
built and validated against the two-page-spread seasons (1890-91-
1897-98, ScanTailor-preprocessed). Whether it transfers cleanly to the
single-page (1898-99+) column-wise corpus's own image geometry is
unconfirmed -- needs a quick validation pass against a handful of
known-split pages before trusting its output corpus-wide. The project's
own history also has a paused "Repertoire row-boundary detection"
thread specifically about a utro/vecher false-split problem (see the
user memory `repertoire-row-boundary-detection-on-hold.md`,
`known_issues.md` #50/#51) -- read that before restarting this work; it
may already document why this is harder than it looks.

## Tier 2 -- cheap disambiguation of Tier 1's candidates: PAUSED (depends on abandoned Tier 1)

Kept below for reference and in case a future Tier 1 replacement
produces a similar candidate list to disambiguate -- but there is
currently no Tier 1 output feeding this, so nothing here is actionable
right now.

Two discriminator branches, both meant to apply only to a short
candidate list, never corpus-wide:

**Branch A -- session-split classification** (the original ask). For
each flagged tall row: does a second session already exist in the DB
for that (date, theater)? If not, crop the date-column sub-region
`detect_columns` already isolates and check for the literal
"УТРО."/"ВЕЧ." glyphs -- since neither word uses a pre-reform letter
(ѣ/і/ѳ), plain OCR (Tesseract) might work here even though it wouldn't
for the body text; worth testing before reaching for a paid VLM
crop-query as a fallback. Confirms or rules out a missing split.

**Branch B -- content-completeness classification** (RG, 2026-09-22:
"can we also use this to double check that all annotations have been
caught?"). A tall row doesn't have to be a missing split -- it can also
be a single session whose extra printed line (an annotation, a benefit
notice, a second work) never made it into the extracted record at all.
For each Tier-1-flagged row that Branch A does NOT resolve to a missing
split, check whether the existing record has *something* explaining
the height: a non-empty `annotation`, or more than one row in
`event_entry_performance` for that session. If neither is true -- a
structurally tall row holding nothing but a single bare title -- that's
a genuine content-drop, a different failure mode from a missed split
but caught by the same screening pass. This is the same bug class
already found by hand more than once this session without a systematic
check (`repertoire_1906-07_p035`'s scrambled benefit notice, issue #77
addendum; `repertoire_1904-05_p032`'s cascaded missing lines) -- Branch
B would have surfaced candidates for that class directly instead of
requiring someone to trip over it while fixing something else.

Honest tradeoff: broadening Tier 2 this way also broadens its own
false-positive rate somewhat -- a row can be tall for purely
typographic reasons (a long title, wrapped text) without anything
being missing. Branch A's split-or-not question is closer to binary;
Branch B's completeness question has more genuinely ambiguous middle
ground and will need more judgment calls per candidate, not just a
glyph check.

## Tier 3 -- the fix (not build work, just discipline)

Once Branch A or B confirms a genuine gap: same procedure as every
other fix this session -- render/locate the actual scan, read the
missing content directly, add or correct the session, re-verify the
specific row against the image before moving on. No different from the
manual work already done on the 1904-05_p032/1891-92_pair008/etc.
cases; Tier 0-2 exist only to generate a short, high-confidence
candidate list instead of relying on stumbling across problems while
doing something else.

## Status summary

| Tier | Built? | Cost | Output |
|---|---|---|---|
| 0 | Done, extendable | Free (SQL only) | 39-row candidate list (annotation-anchored), Monday ranking weight |
| 1 | **Abandoned 2026-09-22** | -- | Tried against `row_detect.py`, found unreliable on this format (see section above); "утро/веч in annotation" alternative also tried and ruled out |
| 2A | Paused (no Tier 1 feed) | -- | -- |
| 2B | Paused (no Tier 1 feed) | -- | -- |
| 3 | N/A | Manual, same as rest of session | Data fixed and scan-verified |

**Current direction (2026-09-22)**: stay within Tier 0 -- extend the
SQL/text-heuristic approach rather than pursue image-geometry
detection further. Next candidate ideas to evaluate, none built yet:
cross-theater/cross-week streak anomalies (a theater that splits on
every other occurrence of a weekday within a season, flagged where one
occurrence in the middle of a streak doesn't), and a tighter,
anchored-pattern version of the annotation-marker search that failed
above (`^УТРО\.?$`/`^ВЕЧ\.?$` rather than a loose substring match).
