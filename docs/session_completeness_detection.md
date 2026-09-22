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

## Tier 1 -- row-height geometric screening (not built)

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

## Tier 2 -- cheap disambiguation of Tier 1's candidates (not built)

Two discriminator branches, both applied only to Tier 1's short
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
| 0 | Done | Free (SQL only) | 39-row candidate list (annotation-anchored), Monday ranking weight |
| 1 | Not started | Free (CPU, reuses `row_detect.py`) | Corpus-wide tall-row candidate list |
| 2A | Not started | Free-to-cheap (OCR, or small VLM crop-query as fallback) | Split confirmed/ruled out |
| 2B | Not started | Same as 2A | Content-drop confirmed/ruled out |
| 3 | N/A | Manual, same as rest of session | Data fixed and scan-verified |
