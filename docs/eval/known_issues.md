# Known issues ledger

Living record of extraction issues found during evaluation, across runs. The
point of this file is that improvement is trackable across runs, not just
anecdotal — check here before a new run to see what's already known, and add
an entry whenever `eval_against_gold.py` or `quality_checks.py` surfaces
something new or resolves something old. Pair with
`docs/eval/run_history.csv`, which tracks the aggregate score each run
produced, so a prompt/schema change can be judged by whether it actually
moved the number, not just by whether it fixed the one example that prompted it.

Several of these are inherent to VLM-based extraction (sampling variance,
occasional field-boundary confusion) rather than bugs to "solve" once — the
goal is catching and triaging them cheaply every run, not eliminating them.

## Status categories

- **open** — known, not yet mitigated
- **mitigated** — a prompt/code change reduced it; watch `run_history.csv` to
  confirm it actually helped
- **not a bug** — behavior that looks wrong at first glance but is either
  correct (source really is that way) or a gold-transcription error, not a
  model error
- **needs source check** — plausibly a real model error, but not confirmed
  against the scanned page yet

---

## 1. Non-deterministic recall on dark/blank cells (Repertoire)

**Status: open.** The single biggest remaining gap. On repeated runs of the
*same* page, the model sometimes emits every cell including dark ones and
sometimes silently omits dark cells entirely (observed: 45/45 sessions on one
run of `repertoire_1890-91_p000`, 9/45 on another). Content accuracy on
whatever IS emitted is consistently ~94-99%; the gap is completeness, not
correctness.

**Detection**: `quality_checks.py`'s `zero_dark_cells_on_multiweek_page` flag
— any multi-week page with zero dark sessions is suspect (real printed tables
almost always have at least one dark day, e.g. Saturdays).

**Mitigation ideas, not yet implemented**: multi-sample consensus (run a
flagged page 2-3x, keep the union, or require the same cell to appear absent
in ≥2 samples before trusting it's genuinely dark); or a second pass
specifically re-asking "list every date in this table's range and confirm
each theater's status" as a completeness check.

**Next thing to try**: DashScope's visual-reasoning/"thinking" mode
(`enable_thinking` — see the original prototype notebook's cell 13, and
https://www.alibabacloud.com/help/en/model-studio/visual-reasoning). This is
a completeness/reasoning failure, not a field-boundary one, so unlike
issues #2/#3 it can't be fixed by post-processing regex after the fact — if
anything can help here, it's giving the model room to reason through "did I
cover every cell" before answering, which is exactly what extended
thinking/reasoning mode is for. Worth an A/B test on a page with a known
recall problem (e.g. `repertoire_1890-91_p000`) before turning it on for a
full Repertoire run — it adds cost/latency, so confirm it actually moves the
number first, same discipline as issues #2/#3.

**Addendum (2026-08-25): the A/B test ran, with two findings — one about
the detection flag itself, one a negative result on the mitigation.**

*The flag has real false positives.* Checked 3 of the 19 pages
`quality_checks.py` currently flags (`zero_dark_cells_on_multiweek_page`)
against their scans. Two -- `repertoire_1899-00_p000` and
`repertoire_1901-02_p021` -- are false positives: their date sequences
genuinely *skip* non-performance days entirely rather than printing them
as dark rows (e.g. Saturdays simply don't appear as a row at all), so
"zero dark cells captured" is the historically accurate transcription,
not a recall failure. This is the same distinction RG raised directly:
a date genuinely absent from the table must never get a row invented for
it, only a date that's printed with a dash should become an `is_dark`
row. The flag's own heuristic ("real tables almost always have at least
one dark day") doesn't hold for every page's printing convention. The
third page checked, `repertoire_1893-94_p006`, IS a genuine recall
failure -- the scan clearly shows multiple dark cells printed (both "1
Субб." and "8 Суббота" show 4 of 5 theaters dark), but the current
extraction captured zero. Real precision on this small sample: ~1/3.
**Conclusion: the 19 flagged pages need individual scan verification, the
same page-by-page discipline used throughout this file, not a blanket
re-extraction on the flag's say-so alone.**

*Thinking mode: negative result, not recommended as-is.* Also found a
real API incompatibility along the way: `enable_thinking=True` combined
with `response_format={"type":"json_object"}` silently returns the
literal string `"0.0"` as the entire response content for this model —
reproduced 3x. Dropping the forced JSON mode (relying on the prompt's own
"return only a JSON object" instruction instead) fixes that. With it
fixed, tested against the confirmed-broken `repertoire_1893-94_p006`:
baseline recovered 1 of ~8+ visible dark cells; thinking mode recovered
**0** of ~8+ on the same page — worse, not better — while costing 58%
more tokens (31635 vs 20011) and taking 30% longer (328s vs 252s). Sample
size is only 1 run each, but a costly, slower, and worse-performing first
result doesn't justify further spend on this specific mitigation without
new evidence. **Multi-sample consensus (the other mitigation idea above)
remains untested and is probably the better next thing to try**, since it
doesn't share thinking mode's apparent failure mode of the model
"compressing" its final answer after spending its budget on reasoning.

**Addendum (2026-08-25, continued): consensus was built, tested, and the
premise it rests on turned out to be wrong for at least this page's
failure mode.** Full trail, since this reverses course partway through --
worth keeping so the reasoning isn't re-walked from scratch later:

1. Implemented `merge_repertoire_samples()` in `pipeline/schemas/
   repertoire.py` (exported via `schemas/__init__.py`): unions sessions
   from N independent extraction samples of the same page, keyed by
   (date_text, month_text, theater, session) -- a key present in ANY
   sample survives the merge (can only recover a dropped cell, never
   invent one no sample produced at all); among samples that captured the
   same key with real content, the version the most samples agree on
   wins over a conflicting "dark" claim, since known_issues.md's own
   finding is that content accuracy on whatever IS emitted is high, so a
   conflicting "dark" claim for the same key is more likely to be that
   sample's own drop. NOT yet wired into `run_pilot.py` as a
   `--repertoire-samples N` flag -- built and validated in isolation
   first, per RG's request to test before committing further.
2. First validation: merged 2 real baseline samples of
   `repertoire_1893-94_p006` (115 sessions/8 dark, 108/2). Looked
   promising -- correctly resolved 7 of 7 dark/content disagreements by
   trusting content over a conflicting dark claim, recovering 3 genuinely
   dark cells ("17 Января"/Михайловскій+Большой+Малый) neither... wait,
   see below -- this specific recovery was re-examined and found wrong.
3. Re-checked that "recovery" against the scan directly: **"17 Января"
   is not dark at all** -- all 5 theaters have real printed content that
   day. Both original samples failed independently there (one fabricated
   "dark" for 3 theaters, the other dropped the keys entirely) -- the
   merge picked between two wrong answers and landed on the worse one,
   because a union can only choose among what samples actually produced.
   First concrete evidence that 2 samples isn't enough, and that some
   failures may not be independent random noise.
4. Tested **chunking** (splitting the page into smaller images so each
   call tracks fewer cells) as a different kind of fix, addressing a
   "long grid overwhelms attention" theory of the root cause. Split at
   the page's natural physical seam, header reattached to both halves.
   Did not help: `chunk_bottom` dropped the entire "8 Суббота" row (same
   failure as the unsplit page); `chunk_top` fabricated content across
   all 5 theaters for "1 Субб." (only 1 theater is actually active that
   day). Ruled out "the page is just too big" as the (sole) mechanism.
5. Noticed every miss so far had landed on a Саturday and tested that
   specifically with two small isolated crops (5-6 rows each, real
   scan-verified ground truth for every cell). Result **disconfirmed** a
   clean weekday-tied bias: one Saturday ("15 Суббота") was captured
   perfectly in the same response that badly mangled a different Saturday
   ("1 Субб.") and a non-Saturday weekday ("17 Понедѣльникъ",
   values-duplication, a different error shape again).
6. **Decisive test**: ran 5 independent samples of each narrow crop.
   Every sample fabricated the *exact same* phantom entries for "1
   Субб." -- byte-identical receipts figures (2168 р. 33 к., 861 р. 44
   к., 1203 р., 1304 р. 39 к., 1096 р. 3 к.), all real figures copied
   from the neighboring "31 Пятница" row. Every sample duplicated the
   *exact same* wrong figure (928 р. 97 к., really Александринскій's)
   onto Маріинскій for "17 Понедѣльникъ". At non-zero sampling
   temperature, genuinely random noise does not reproduce identically
   across 5 independent calls. **This is a stable, reproducible
   misreading tied to something specific about the image at that
   position -- not stochastic noise.**

**This overturns the working theory the whole investigation had been
operating on.** Consensus/multi-sampling can only average away
independent disagreement between samples; these samples don't disagree
with each other, they agree, consistently, on the same wrong answer, so
consensus has nothing to vote against. Combined with the already-negative
results for thinking mode and chunking, and the disconfirmed
Saturday-bias hypothesis (which would have suggested a targeted prompt
fix), **none of the four mitigations investigated today actually solve
this for the specific failure mode demonstrated on
`repertoire_1893-94_p006`.** RG flagged this as concerning and asked to
pause here for the day with the investigation left open, not silently
dropped.

**Where this leaves things, for whoever picks this up next**: the
`merge_repertoire_samples()` code is real, tested in isolation, and NOT
wrong in what it does -- it's a correct implementation of "union +
content-wins-over-dark" -- but it should not be deployed as *the* fix on
the strength of today's evidence, since it doesn't address this page's
demonstrated failure mode. Ideas not yet tried: (a) a crop containing
*only* the single problem row with zero neighboring context at all (today's
narrow crops still included 2 rows of neighbors on each side -- if the
misattribution is genuinely a "nearest visually prominent text" attention
error, removing the neighbor entirely might change the outcome, whereas
today's tests only shrank *how many* neighbors were present, not whether
any were); (b) checking whether this reproducibility holds on a
*different* problem page/cell, to see if it's a general property of this
failure mode or something oddly specific to this one image region
(scan-quality artifact, an unusual print layout at that exact spot, etc.)
-- everything tested today was still on the same single page; (c) given
the practical implication that automated re-sampling cannot be trusted to
converge on ground truth for at least some cells, the safety-net idea
from the pros/cons discussion (route disagreement cells to a human/scan
check) may need to become the *primary* mechanism rather than a backstop,
since "disagreement" won't reliably surface cells where every sample
independently agrees on the same wrong answer either.

**Addendum (2026-08-25/26): lead (a) tested, and it's the fix.** Cropped
both confirmed-broken rows ("1 Субб.", "17 Понедѣльникъ") down to ONLY
that single row -- header reattached, but literally zero other dated rows
visible in the image (confirmed by direct visual check of each crop).
Ran 5 independent samples of each. Result: **10/10 samples, byte-identical,
exactly matching the scan** -- Михайловскій's 2560 р. 50 к. and the other
4 theaters correctly dark for "1 Субб."; all 5 theaters' real figures
(Маріинскій correctly no-receipts) and zero fabricated darks for "17
Понедѣльникъ" -- every single run. The same two rows that failed, often
identically wrongly, in every multi-row context tried today (full page,
half-page chunks, 5-6-row narrow crops) came back perfect the moment no
other row's content was visible in the image at all.

This confirms the mechanism precisely: the misattribution needs a
neighboring row's content physically present in the image to misattribute
*from*. It's not attention fatigue over a big grid (chunking already
ruled that out) and it's not a weekday-linked prior (the Saturday test
already ruled that out) -- it's specifically that the presence of nearby
printed text gives the model something (wrong) to lock onto, and removing
it removes the failure.

**Practical implication**: row-by-row extraction -- one API call per
dated row instead of one call per page -- looks like the actual fix, not
a mitigation. Real, bounded cost: roughly 3-4x more tokens per page
(~3400-3500 tokens/row x ~15-20 rows/page, vs ~20000 tokens for one
full-page call), offset by each call being far cheaper individually
(~10s vs ~250s) and trivially parallelizable. **Not yet validated beyond
these 2 rows on 1 page** -- before committing to rebuilding the
extraction pipeline around this, the next step is testing row-level
isolation on more rows and more pages (including pages that were NOT
already known-broken, to check it doesn't regress already-good pages) to
confirm this generalizes rather than being specific to these two rows.
If it holds up, this would replace the abandoned consensus/chunking
approach as the actual pipeline change, with `merge_repertoire_samples()`
(built earlier today) potentially still useful as a secondary layer for
whatever residual randomness remains even at row granularity.

**Addendum (2026-08-26): plan approved, pipeline scaffolding built,
automated row-boundary detection proven viable but not yet complete.**
Full trail in the 2026-08-26 query_log.md entry. Highlights:

- Plan approved (row-isolated extraction, Repertoire-only for now, pilot
  before full-corpus rollout, opencv for line detection) -- saved at
  `/Users/rachelglodo/.claude/plans/nifty-enchanting-sedgewick.md`.
- opencv install issue resolved: the real blocker was macOS 12.7.6 (not
  Python 3.14 as first suspected) -- recent opencv wheels need macOS 13+;
  pinned to `opencv-python-headless==4.10.0.84`, documented in CLAUDE.md.
- `pipeline/row_detect.py` built: per-strip peak-finding + chain-tracing
  across the page width to follow genuine curvature (a naive whole-width
  darkness profile was tried first and doesn't work for curved lines --
  documented in the module). Not yet wired into `run_pilot.py`.
- Evaluated **Transkribus** (RG has an account) live as an alternative:
  its table model found zero structure on the test page even after the
  expected text-recognition prerequisite step, and when it did produce
  output it was one undifferentiated, poorly-transcribed text region, not
  real table structure. Not a fit without training a custom model (much
  bigger investment) -- not pursued further.
- Evaluated **ScanTailor Advanced** (GUI-only build for this platform, no
  bundled CLI) as a whole-page dewarm preprocessor instead of per-row
  curvature detection. RG ran the real test page through it live, several
  configurations compared via `row_detect.py`'s debug-visualize mode.
  **Key finding: deskew alone (no dewarp) + a tight, consistent,
  Page-Box-disabled crop was sufficient and outperformed every dewarp
  setting tried** -- best controlled baseline (Split Pages=full page auto,
  Deskew=auto, Content Box=auto, Page Box=disabled, Margins=3mm, Dewarp
  OFF) got 20/~19 real row boundaries correctly detected, including both
  ground-truth rows, better than any earlier test. Dewarp (marginal
  setting) actively made results worse in one comparison. This simplifies
  the eventual automation question, since deskewing is simpler and more
  standard than full dewarping.
- One real bug found and not yet fixed: building actual row crops (not
  just the debug visualization) from that best-baseline image revealed
  the chain-tracer sometimes fails to detect a real boundary line outright
  (confirmed via direct sanity crops bypassing the dewarp code -- ruled
  out a header-count/indexing bug first, then found a genuine ~438px gap
  where a line should exist but wasn't found), merging two adjacent rows
  into one crop. A detection-recall gap, not a systemic failure -- the
  same run got 18-19 of ~19 boundaries right elsewhere on the same page.

**Where this stands**: the architecture is validated end-to-end in
principle (ScanTailor deskew -> row_detect.py curve-tracing -> isolated
row crops), but `row_detect.py` isn't reliable enough yet to trust broadly
-- needs the missed-line recall gap fixed and re-validation on more pages
before wiring into `run_pilot.py`. Paused here at RG's request; resuming
same day.

**2026-08-27 addendum -- validated ScanTailor Advanced settings (whole-
season batch, supersedes the single-page baseline above):**

Testing against the whole 1893-94 Repertoire season (12 pages, via
ScanTailor's own multi-page batch project + "Apply to All Pages" --
not per-page manual export) surfaced two settings the single-page test
above didn't catch, because they only fail visibly at real page-to-page
variety. **Page Box=disabled** (the single-page baseline) left a scan-
edge shadow band near the top of 6 of 12 pages, read by `row_detect.py`
as spurious extra boundaries; switching Page Box to Auto fixed it on the
one page tested by hand (p004) but the fix only holds with **Fill
Margins also enabled** -- turning Fill Margins off (tried once, to see
if a more "authentic" unpainted margin mattered) reintroduced a *worse*
version of the same problem: a full-width, uniformly-colored offcut band
right at the image's top edge, present on 8 of 12 pages. With Fill
Margins back on, the artifact is gone on 10 of 12 pages entirely (0.00
ink outside the table on both sides) and much reduced on the remaining 2.

Full validated settings, confirmed against the whole season (not just
one page):
- Split Pages: full page (auto)
- Deskew: Auto
- Select Content: Content Box=Auto, **Page Box=Auto** (not disabled --
  corrects the single-page-tested baseline above)
- **Fine Tune Page Corners: enabled**
- Margins: **3mm all sides**
- **Fill Margins: enabled** (must be on -- see above; off reintroduces
  the top-edge artifact in a worse form)
- Equalize illumination: off
- Dewarping: **off** (deskew alone still outperforms every dewarp
  setting tried, per the single-page test above)
- Output DPI: 350

Net effect on `row_detect.py`'s curve-count accuracy across the season
(known dated-row counts from `raw.event_entry`, corrected for issue #49's
p007 data-quality bug -- p007's true count is 20, not the raw-JSON's
corrupted 29): 4 of 12 pages exact, most others off by only +1 to +3 (the
same low-cost over-detection class as the accepted утро/вечер-divider
false-split discussed earlier in this issue -- fixable per-page via the
manual review tool below, not evidence the settings are wrong). One
outlier remains at +6 (`repertoire_1893-94_p009`) and hasn't been
individually reviewed yet.

**New: human-in-the-loop correction workflow**, added to `row_detect.py`
same day (RG: "show me the image with rows detected, and I can add one if
there are any missing"). `analyze_page()` runs detection and keeps the
underlying per-strip chains around (not just the final kept curves);
`debug_visualize()` shows the numbered-curve image RG checks against the
scan and writes a `*__curves.json` index/y sidecar; RG reports a fix by
curve index ("add one between curve 8 and 9", "curve 14 is spurious");
`insert_row_boundary()`/`delete_row_boundary()` apply it by re-scanning
the SAME chains at a relaxed presence floor (the identical mechanism the
automatic gap-fill pass already used, just triggered by a human instead
of the gap-size heuristic) rather than guessing fresh; `detect_rows()`
takes the corrected `PageAnalysis` and crops from it, writing a
`*__corrections.json` audit trail alongside the row manifest. Also added
`_smooth_curve()` (light moving-average over each curve's interpolated
points, ~121px window) after RG flagged visible strip-to-strip jitter in
otherwise-correct curves. Fully validated end-to-end on
`repertoire_1893-94_p004`: automatic detection (23 curves) -> 4 rounds of
human correction (removed the original top-artifact curve, inserted 2
real missing boundaries, removed 2 spurious утро/вечер-divider
false-splits) -> 22 curves, matching the known 20-row count exactly ->
`detect_rows` produced 20 clean row crops, each spot-checked against the
scan with the header correctly reattached and zero neighboring-date
content, including the compound "14 Воскресенье" (утро+вечер) row now
correctly kept as ONE crop rather than falsely split.

**Still open**: `repertoire_1893-94_p009` (the +6 outlier) not yet
reviewed; the other 10 pages in this season not yet run through the
correction workflow; `header_line_count` still not auto-detected (see
`detect_rows`' own docstring); broader pilot (more seasons, both column
layouts, visibly curved pages) not yet started; not yet wired into
`run_pilot.py`.

**2026-08-27 addendum -- `run_pilot.py` row-level driver built and
validated end-to-end; auto-detecting the утро/вечер divider (the one
remaining manual-review step) tried 4 ways and shelved:**

`process_page_rowlevel` added to `run_pilot.py` (`--row-level` flag):
runs `detect_rows` (or takes an already-corrected `PageAnalysis`), then
one API call per row crop concurrently under the SAME semaphore as the
page-level path, concatenating every crop's `sessions` into one
page-level `{"sessions": [...]}` -- zero changes needed downstream in
`parse_and_validate.py`. Also strengthened `repertoire_system.txt`: fixed
a real inaccuracy (prompt said session default is `"day"`, the actual
Pydantic schema only accepts `"unspecified"` -- the model was already
correctly ignoring the wrong prose and following the schema, so this
wasn't live-corrupting data, just risky ambiguity) and added explicit
guidance against exactly the failure shapes issue #49 found (date
carried over from a neighboring row, values drifting into the wrong
theater column).

**Validated on `repertoire_1893-94_p009`** (the page issue #49's second
mislabeling instance was found on): row-level extraction using the
human-corrected 21-curve boundary set produced 18 distinct dates --
exactly matching the database's original count -- with date "19
Суббота" now perfectly correct (Мариинскій=dark, Александринскій="Auf
Triburg und Rodeck" 2016р, Михайловскій="Un Drame parisien" 1562р50к,
Большой="Gli Ugonotti" 1584р75к, Малый=dark, matching the scan exactly)
and the 5 genuine compound утро/вечер dates correctly kept as single
sessions sharing one `date_text` each. Confirms row isolation fixes this
failure class too, not just issue #1's original simpler swap -- but only
when the crop boundaries are right, which the human-reviewed set gave it.
A control run using RAW auto-detection (with the уtro/вечер false-splits
still present) reproduced the exact fear: a half-split crop often doesn't
contain its own date label at all (it's printed once, centered across
BOTH sub-blocks), so the model has nothing real to read and fabricates
garbage date_text ("ВЕЧЕРЪ", "2-я карт.") -- not a prompt problem, a
crop that's missing the information it needs.

So the real remaining blocker for a corpus-wide run isn't the extraction
call anymore -- it's that `row_detect.py` still can't tell a genuine
date boundary apart from an internal утро/вечер divider *without* a
human pointing it out. Four different approaches tried against a rich
set of confirmed examples (6 spurious dividers + 6 real boundaries
across `repertoire_1893-94_p004` and `p009`), none worked:
1. Column-ink density (checking the wrong side initially -- date column
   is the rightmost column for pre-1898-99 seasons, RG: for 1898-99
   onward it moves to the LEFT edge, a season-dependent fact any future
   attempt needs to parameterize, not hardcode).
2. Peak-spike detection (does a real printed rule extend into the date
   column) -- some real boundaries show a strong spike, others show
   almost none; inconsistent, no clean threshold.
3. Connected-components glyph detection -- defeated by this typeface's
   vertically-stacked characters merging into one giant blob via
   incidental touching pixels under 8-connectivity.
4. Erosion before connected-components (the standard fix for touching
   text) -- tried at both 300-equivalent and 450dpi (see below); still
   left components spanning 1000+ px (multiple dates' worth of height)
   at every kernel size tested; too little erosion leaves things merged,
   too much starts eating real strokes, with no clean middle ground.

**Higher DPI tested directly and ruled out as a fix for this specific
problem** (RG: would rescanning the corpus's print-quality seasons at
archival 600dpi help?) -- see
`memory/source-scan-dpi-varies-by-season.md` for the full test (a real
1890-91 page, genuinely 600dpi native, reprocessed at 450dpi -- 600
itself exceeded ScanTailor's own load ceiling here, ~53 megapixels).
Same failure, same magnitude. This means the touching-character problem
is most likely inherent to the typeface's serifs/kerning, not a scan-
resolution limitation -- don't re-propose rescanning for this reason.
Real, tested finding, not an assumption.

**Decision (RG, 2026-08-27): fall back to human review for this one
detail rather than continue chasing automation.** The review workflow
(`analyze_page` / `debug_visualize` / `insert_row_boundary` /
`delete_row_boundary`) already works well and is fast in practice --
revisit full automation of just this piece later if it becomes a real
bottleneck at scale, rather than blocking the pilot on it now.

## 2. `heading_path` sometimes appears to re-include the institution name

**Status: mostly a misdiagnosis, not actually a bug — see below.** Initially
looked like straightforward duplication (`institution="Императорское
С.-Петербургское Театральное Училище"`, `heading_path="Императорское
С.-Петербургское Театральное Училище / Управляющій Училищемъ"`), found on
`administration_1907-08`, `theaterschoolstaff_1899-00`, `productionteam_1890-91`.

**What re-checking after the code fix actually showed**: in most instances,
the model isn't repeating the same string gold used for `institution` — it's
drawing the institution/heading_path **boundary** in a different, equally
defensible place. Example from `theaterschoolstaff_1899-00`: gold's
`institution` is the specific school name; the model's `institution` is the
series title ("Списокъ личнаго состава преподавателей и служащихъ..."), with
the school name correctly placed as the first `heading_path` segment
instead. Same underlying ambiguity as the original department/position
split (visual/typographic hierarchy judgment, hard to pin down from text
alone) — just one level higher up the breadcrumb.

**Why it doesn't matter much in practice**: `role_normalized` (in
`build_duckdb.py`'s analysis layer) only ever takes the *last* segment of
`heading_path` — completely unaffected by where the institution boundary
falls. A prefix-strip was still added defensively (strips a literal
`institution + " / "` prefix if one ever appears verbatim), but it's a
no-op on the cases actually seen in the pilot, because those weren't real
duplicates. Not spending further effort here — downgrading from "open issue"
to "understood, low-impact quirk."

## 3. Rank/class token left inside `heading_path` instead of `service_class`

**Status: mitigated via deterministic post-processing, not prompting.**
Example: `heading_path="Чиновники особыхъ порученій, при дирекціи, VII кл."`,
`service_class=""`. Found consistently across all of `administration_1907-08`
(11/13 entries).

**Tried and it didn't work**: added an explicit right/wrong example to
`roster_system.txt` (the same technique that fixed the Repertoire
work_title/genre split). Re-ran the exact page — zero improvement
(0/8 entries fixed on re-test), and a related institution-duplication
regression appeared on the same run. Conclusion: this specific failure mode
doesn't respond to prompt wording the way the Repertoire one did — worth
remembering before spending another iteration on prompt text for this
pattern specifically.

**What actually works**: the pattern is mechanical enough (a trailing Roman
numeral + "кл" at the end of `heading_path`, with `service_class` empty) to
catch and fix deterministically in code instead. Implemented in
`build_duckdb.py`'s `analysis` schema via regex — `raw.heading_path` keeps
the model's literal output (reproducibility guarantee intact),
`analysis.heading_path_clean` / `analysis.service_class_clean` have the
class token extracted and stripped. This is now the template for issue #2
below too, and probably the right default move whenever a field-boundary
issue turns out to be regex-shaped: try the prompt once, and if it doesn't
move the number, normalize downstream instead of iterating prompt wording
indefinitely.

## 4. Verbatim punctuation conventions are inconsistent — between gold and model, not just within the model

**Status: not a bug — open convention decision.** Two recurring patterns:

- **Parentheses around tenure dates.** The model frequently writes
  `tenure_note_text="(съ 1 мая 1882 г.)"` (with parens); gold has
  `"съ 1 мая 1882 г."` (without). Re-checking the source, the printed text
  often genuinely *is* parenthesized — meaning the model is arguably more
  verbatim-correct here, and gold silently normalized the parens away when it
  was built.
- **Trailing colons after section headers.** Similarly, the model sometimes
  keeps a printed trailing colon (`"Артистки:"`, `"Помощники режиссера:"`)
  that gold stripped (`"Артистки"`).
- **Generic venue-type words.** The model sometimes writes `"Большой театръ"`
  (theater name + the generic word "театръ") where gold has just `"Большой"`.

**Decision needed**: pick one convention (keep source punctuation/suffix
words verbatim, or normalize them out) and apply it consistently in both the
prompt and the gold set — right now neither side is consistent, which
inflates the apparent error rate on `eval_against_gold.py` without reflecting
a real content problem. Until decided, `eval_against_gold.py`'s field-level
diffs on `heading_path`/`tenure_note_text` should be read with this in mind
rather than taken as pure accuracy loss.

## 5. "Инспектриса" misread as "Инспекториса"

**Status: needs source check, but low priority.** Recurred identically
across two different pages/years (`theaterschoolstaff_1899-00` and
`theaterschoolstaff_1906-07`), which argues for a stable model bias on this
specific (relatively rare) word rather than random noise. Worth a source-crop
check next time either page comes up for review, not worth a special-cased
fix on its own.

## 6. Musicians 1890-91 page: pred returned 37 entries vs. gold's 14

**Status: needs source check.** `musicians_1890-91_SP_p000`: the model's
extra entries (a 3-person leadership section — Альбрехтъ/Христофоровъ/Тильпъ
— plus musicians numbered past #11) look like gold under-transcribed the top
and/or bottom of that page during the original hand-transcription pass,
rather than the model inventing plausible-sounding real names. Re-open
`docs/eval/gold/images/musicians_1890-91_SP_p000.png` and re-transcribe fully
before trusting either side's count for this page.

## 7. Repertoire row order is not stable across runs

**Status: not a bug — a comparison-methodology note, not an extraction
issue.** The model sometimes emits repertoire sessions date-by-date (row
order) and sometimes theater-by-theater (column order) for the same page.
Both are complete, correct answers to "list every cell" — just don't compare
repertoire rows positionally. `eval_against_gold.py` and
`quality_checks.py` both key repertoire sessions on
`(day_number, theater_prefix, session)` rather than row position for exactly
this reason. Roster rows, by contrast, have reliably preserved printed list
order across every run so far — if that stops holding, this file is where to
note it and `eval_against_gold.py`'s roster comparison needs the same
key-based rework.

## 8. Matinee/evening session-type mislabeling (intermittent)

**Status: open, one confirmed instance.** On the pilot run,
`repertoire_1898-99_MSK_p019` emitted two sessions for the same
(date, theater) pair — a genuine matinee/evening split in the source — but
labeled *both* `session="day"` instead of `"morning"`/`"evening"`. An earlier,
isolated test of this exact page got it right. Same non-determinism family as
issue #1.

**Detection**: `quality_checks.py`'s `duplicate_session_key` flag (two rows
with an identical `(date, theater, session)` key is only possible if a real
split got mislabeled with the same session type, or if there's a genuine
double-extraction).

**Caveat**: don't assume every `duplicate_session_key` hit is this — check
the works/receipts to distinguish a mislabeled split from real duplication.

Same family as issue #1 (recall/reasoning, not field-boundary) — worth
including in the same DashScope thinking-mode A/B test rather than a
separate experiment.

## 9. `duplicate_person_on_page` can be a false positive

**Status: not a bug.** `balletartists_1907-08_SP_p000` flagged Легатъ,
Николай Густавовичъ as appearing twice — correctly: he genuinely holds two
listed roles on that page (Second Balletmaster, and separately Head Coach of
Classical Dance). The flag is still worth keeping — a duplicate is worth a
human glance either way — just don't auto-reject flagged rows without
checking `heading_path` first.

## 10. Session field emitted in Russian instead of the normalized enum

**Status: mitigated via deterministic post-processing.** On the full-corpus
run, 10 Repertoire pages (82/23,726 sessions total) failed schema validation
because the model wrote the printed Russian word (`"утро"`, `"вечеръ"`,
occasionally `"день"`) into the `session` field instead of the normalized
`day`/`morning`/`evening` enum value the schema expects. Unlike the
verbatim-text fields, `session` is explicitly a categorical/normalized field
(the printed word itself isn't preserved anywhere else either), so this is a
safe one-to-one lookup rather than a verbatim-preservation concern.
**Fix**: `parse_and_validate.py`'s `_repair_repertoire()` normalizes known
Russian variants before pydantic validation runs. Not prompt-tuned first —
same reasoning as issue #3: a three-entry lookup table is more reliable than
iterating prompt wording for a rare, mechanical mismatch.

## 11. Fractional credit counts (e.g. `0.5`) are real, not OCR noise

**Status: not a bug — schema was too strict.** One BalletArtists entry's
`count` field failed validation because the schema required an integer but
the model correctly transcribed a printed `"—.5"` (half-credit for a role,
e.g. shared between two dancers) from `credit_summary_text`. **Fix**:
`CreditLLM.count` changed from `Optional[int]` to `Optional[float]` in
`schemas/roster.py`; `flatten_roster_page` formats whole-number counts
without a trailing `.0` so the common case still reads as a plain integer in
the CSV.

## 12. Person's name written into `heading_path` instead of the name fields

**Status: mitigated via deterministic post-processing.** Rare (4/20,716
roster entries in the full run, all in ProductionTeam), but a clean,
recognizable pattern: on a row that has no heading text of its own to repeat
(inheriting from the row above), the model sometimes puts the full name
("Петровъ 2-й, Анатолій Алексѣевичъ" — family name, comma, first name and
patronymic) into `heading_path`, leaves `family_name`/`first_name`/
`patronymic` empty, and puts what should have been the heading text into
`institution` instead. This shape (`Capitalized-word[,] Capitalized-word
Capitalized-word`) never legitimately occurs in a real `heading_path`, which
is always institution/department/role segments, so it's safely detectable.
**Fix**: `parse_and_validate.py`'s `_repair_roster()` regex-matches this
shape only when `family_name` is missing, splits it into the three name
fields, and clears `heading_path`. `institution` is left as-is (still holds
real, useful text — just mislabeled) rather than guessing a swap; the lost
information is the row's *actual* institution/category heading, which the
model dropped and can't be recovered without the source image.

## 13. Completeness reconciliation: `event_status='not_captured'` (implemented)

**Status: implemented, in `analysis.event_entry`.** Renamed
`is_dark` to `event_status` (`performed` / `no_performance`) — "dark
cell" is theater jargon, not intuitive — and added a third,
analysis-layer-only value, `not_captured`, for (date, theater) cells the
page should have but extraction didn't return at all. Full rationale and
the two assumptions it rests on: `docs/schema.md`'s `event_status`
section. 3,771 gaps found across the full corpus (~13.7% of the full
expected grid), heavily concentrated on a few bad seasons/pages rather
than spread evenly — consistent with issue #1 being a page-level
non-determinism problem, not a uniform recall rate.

**Known false-positive source**: the reconciliation assumes a constant
per-season theater roster (5 theaters/day pre-1898-99, 6 after) for every
day in a page's date range. `repertoire_1890-91_p000` — a page where gold
and the model *independently* agree on exactly 45 real sessions — still
gets 10 `not_captured` flags from this method, because the expected grid
assumes 5 theaters × 11 days = 55. Since both gold and the model converge
on 45 despite being produced independently, the more likely explanation is
that not every theater printed a row every day that early in the 1890-91
season (a season-opening stagger, perhaps), not that 10 real cells got
missed. Treat `not_captured` as "worth checking," the same way the other
`quality_checks.py` flags are — not as certified ground truth.

## 14. Two real date-parsing bugs found while building the completeness grid

**Status: fixed**, in `pipeline/schemas/dates.py`. Found only because the
reconciliation above needed reliable per-page date ranges, and an early
test run produced an obviously-wrong 365-day span on one page:

- **Abbreviated months weren't matching at all** (`Февр.`, `Апр.`, etc.) —
  the stem-matching only checked `word.startswith(stem)`, which fails when
  the abbreviation is *shorter* than its stem. Fixed by also checking
  `stem.startswith(word)`. This alone took `date_undate` fill rate on
  `event_entry` from 89.0% to 99.8%.
- **Season-spanning year ranges resolved to the wrong year.** Repertoire
  `year_text` is often printed as `"1896—1897 гг."` (the table covers
  August of the first year through summer of the second), but the parser
  only ever grabbed the first 4-digit number — so every January-July
  session in a season got dated into the *first* calendar year instead of
  the second (e.g. `repertoire_1896-97_p006`'s May sessions were dated
  1896 instead of 1897, inflating that one page's apparent date span to a
  full year). Fixed by capturing both years when a range is present and
  picking based on month (Aug-Dec -> first year, Jan-Jul -> second),
  consistent with an August-July theater season. Single-year text (the
  common roster tenure-date case) is unaffected.

Neither bug changes `eval_against_gold.py`'s field-match percentage (it
doesn't score `date_undate` directly), so this went undetected until a
downstream feature actually needed reliable dates — worth remembering:
"the accuracy score didn't drop" isn't the same as "nothing was wrong."

## 15. Theater name needs prefix/alias normalization for any exact-match join

**Status: understood, handled via `theater_canonical` (analysis layer
only, `raw.theater` untouched).** Two independent spelling inconsistencies
would silently break any join keyed on the literal `theater` string:

- **Post-1898-99 pages consistently append "театръ"/"театр"** (both
  orthography variants) to the theater name, where pre-1898-99 pages
  print the bare name (`"Большой театръ"` vs `"Большой"`). This alone made
  an early version of the completeness reconciliation show a false 100%
  gap rate for every season from 1898-99 on, since the hardcoded roster
  names never matched.
- **"Маріинскій" is sometimes spelled "Мариинскій"** — missing the
  pre-reform "і" — 116 occurrences across four different pre-1898-99
  seasons (1891-92, 1893-94, 1896-97, 1897-98), so this is a recurring
  model spelling drift, not one-off noise. Same family as issue #4
  (verbatim punctuation/spelling inconsistency), but this one actively
  breaks anything that groups or joins on theater identity.

Both are handled the same way as issues #2/#3: normalize downstream in
`analysis` (a `starts_with`/alias `CASE` producing `theater_canonical`),
leave `raw.theater` exactly as transcribed.

## 16. Rare field-boundary swaps involving `theater`

**Status: needs source check, low priority (small counts).** Found while
inspecting unmatched `theater_canonical` values:

- `"С.-Петербургскіе театры"` (9 occurrences) / `"Московскіе театры"` (11) —
  "SP theaters" / "Moscow theaters" as a literal value, plausibly a
  genuine citywide-total row rather than an error — needs a source check
  to confirm before deciding whether to model city-total rows as their own
  thing.
- `"Мѣсяцъ, день и число"` (7 occurrences, "Month, day and number") — this
  is the printed *column header* text, apparently captured as if it were
  a data row's theater value.
- `"Конекъ-горбунокъ"` (2 occurrences) — this is a ballet title (*The
  Little Humpbacked Horse*), not a theater name; a field-boundary mixup
  putting a work title where `theater` belongs.

All three are excluded from `theater_canonical` (left `NULL`) rather than
guessed at, so they don't corrupt the completeness reconciliation — they
just don't count as "covered" for any expected grid cell, which is the
safe default.

## 17. Homonym ordinal suffix sometimes lands alone in `first_name`, shifting the real name into `patronymic`

**Status: mitigated via deterministic post-processing**, in
`build_entities.py`'s Person Tier 1 matching (`docs/research_dataset.md`).
101/20,528 `first_name` values are *exactly* the ordinal suffix and nothing
else (e.g. `family_name="Вальтеръ", first_name="1-й",
patronymic="Викторъ Григорьевичъ"`) instead of the usual
`family_name="Вальтеръ 1-й", first_name="Викторъ",
patronymic="Григорьевичъ"`. Without correcting this, the same real person
fragments into two different Tier 1 clusters depending on which season
happened to hit the bug. **Fix**: when `first_name` is a bare ordinal *and*
`patronymic` looks like a real name (1-2 capitalized Cyrillic words, no
parenthetical/abbreviation punctuation), reinterpret: the ordinal moves to
join `family_name`, and `patronymic`'s word(s) become the real
first/patronymic. 95/101 cases were safely recovered this way; the
remaining 6 didn't match the "looks like a name" guard and were correctly
left alone rather than guessed at — see issue #18, they're not names at
all. Verified: re-running Tier 1 after this fix reduced 3,962 resolved
people to 3,947 (fragmented duplicates merging back together), and
merging `Вальтеръ 1-й`'s two previously-split clusters was confirmed by
hand.

## 18. Cross-reference/pointer notes captured as if they were a name field

**Status: not fixed, deliberately left alone.** A handful of roster
entries are genuinely a "see also" pointer rather than a real person
record — e.g. `family_name="Тарнке", first_name="1-й",
patronymic="(см. оперный оркестръ)"` ("see the orchestra listing"), or
`family_name="Вальтеръ", first_name="2-й",
patronymic="(см. оперный оркестръ)"` — presumably pointing to that same
person's real listing elsewhere (a different roster type or page) rather
than duplicating their name here. Issue #17's fix deliberately does *not*
try to resolve these: the guard that recognizes "does this look like a
real name" correctly rejects parenthetical/abbreviation text, so these
rows are left exactly as printed rather than having a name fabricated for
them. They currently resolve as their own low-evidence Tier 1 person
clusters (effectively unlinked). Properly resolving them would mean
actually following the cross-reference to the real entry elsewhere in the
same page/season — a manual or Tier 2 task, not a mechanical one.

## 19. `NAME_IN_HEADING_RE` missed noble-title prefixes and trailing rank suffixes; some entries have no name anywhere in the JSON

**Status: mitigated (regex broadened) for the recoverable case; the
unrecoverable case is a genuine model omission, not fixed.** Found during
`full_run_2026-08-15_qwen3-vl-plus_local` (the first full-corpus run of the
`Spiski_Graduates` PDFs, and the first re-run of the older categories since
July): 4 roster pages initially failed schema validation entirely (not just
individual rows) on `family_name` being *absent* from the entry dict, which
is more severe than issue #7's "empty but present" case — a pydantic
required-field error fails the whole page, dropping every other, valid
entry on it too.

Two different root causes, confirmed against the scanned pages before
fixing either:

- **Recoverable (2 entries).** `heading_path="Поспѣевъ, Дмитрій
  Александровичъ, тит. сов."` and `"Графъ Бобринскій, Алексѣй Алексѣевичъ,
  тит. сов."` — the original `NAME_IN_HEADING_RE` required the match to end
  (`$`) immediately after the patronymic, so a leading noble title
  (`Графъ`) or a trailing rank abbreviation (`, тит. сов.`) broke the match
  even though the name itself was present and well-formed. Fixed by adding
  an optional leading-title alternation (`Графъ|Графиня|Князь|Княгиня|
  Баронъ|Баронесса`) folded into the captured surname (so it's kept, not
  discarded) and an optional trailing `, (.+)` group that now lands in
  `heading_path` (rather than nulling it out) instead of failing the match.
- **Not recoverable (7 entries, 2 pages).** `administration_1904-05_p002`
  entry 14 has `heading_path="Дежурные врачи"` (a section heading, "duty
  physicians") with an explanatory sentence in `tenure_note_text` and no
  person at all — confirmed against the scan (p.73, right column) this is
  genuinely a heading-only line, not a person row. `productionteam_1892-93_p002`
  entries 4/7/9/10/13/16 have `heading_path="Парикмахеры"` ("hairdressers")
  or `"Парикмахеры / Русская драматическая труппа"` — but confirmed against
  the scan (p.102) *every* person actually listed under that heading has a
  clearly printed name (Дмитріева, Ѳедоровъ, Педдеръ, Жуляевъ, Шляпниковъ,
  Аѳанасьевъ, Крюковской, Варламовъ, Ефимовъ …), so this is a genuine model
  recall failure (the name was dropped entirely, not misplaced) rather than
  a field-boundary issue — nothing in the JSON to mechanically recover.

**Fix applied**: `_repair_roster` (`parse_and_validate.py`) now returns
`(parsed, n_dropped)`. When an entry still has no `family_name` after the
broadened regex attempt, that single entry is dropped (not fabricated) and
the page's remaining entries still get parsed and kept — a real
improvement over the old all-or-nothing page failure, and closer to the
module docstring's stated intent ("never crash the run for every OTHER
page" — now also true for every other *entry* on the same page). Drops are
still logged, not silent: `validation_errors.csv` gets a
`entry_dropped_no_name` row per affected page with the count. Net effect on
this run: person_entry rows went from 21,087 → 21,174 after the fix; final
state is 0 page-level failures, 7 entry-level drops (2 pages), all logged.

## 20. `render_pages.py`'s `glob("*.pdf")` silently skips iCloud-evicted files instead of erroring — caused a 10/18-season RepertoireTables gap

**Status: caught and fixed in `full_run_2026-08-15_qwen3-vl-plus_local_corrected`,
not a code fix (operational/process issue, see below for why).** On a machine
where `pdf/` is synced via iCloud Drive with "Optimize Mac Storage" on, a
PDF that hasn't been downloaded locally doesn't appear on disk under its
real name at all — it shows up as a hidden `.<name>.pdf.icloud` placeholder,
which `folder.glob("*.pdf")` in `discover_pdfs` simply does not match. This
is silent: no exception, no log line, the file just isn't in that run's
`n_pdfs` count, and `render_pages.py` has no way to tell "0 results because
this category is genuinely empty" apart from "0 results because N files
were invisible to glob this time." (`pymupdf.open()` erroring with
`FileNotFoundError`, as originally seen the first time this session hit an
evicted file, is a *different*, louder failure mode — that happens when
glob *does* return the path but the file isn't actually readable yet;
here glob never returns the path in the first place.)

**How this bit a real run**: earlier in this session, 13 of 18 RepertoireTables
PDFs were rendered once (into a scratch dir later merged into
`outputs/full_run/images`) before eviction/disk-space handling was
understood. By the time the real per-category batch ran, most of those
PDFs had been silently re-evicted by macOS under disk pressure. The batch's
`render_pages.py --entity-type Repertoire` call found only 8/18 PDFs
(exactly the ones that happened to still be materialized at that moment)
and wrote a manifest with only 246/519 pages — with no error to signal
this. The pre-rendered PNGs for the other 10 seasons sat unused in
`images/`, uncounted, and even survived that category's post-extraction
cleanup step (which only deletes page_ids present in the run's manifest —
so it correctly left alone images it didn't know belonged to this run).
The result was reported as a complete, 0-failure category run and logged
that way in `run_history.csv` — wrong, but with nothing in the pipeline's
own output that said so.

**How it was caught**: not by anything in the pipeline itself — by manually
diffing each category's "N PDFs, M pages" summary line in the run log
against the true on-disk `*.pdf` file count established at the very start
of the session (`ls pdf/<Category>/*.pdf | wc -l`). RepertoireTables was
the only category with a mismatch (8 vs. 18); all 6 `Spiski_*` categories
happened to match exactly, since they were rendered fresh in one pass with
no stale pre-migrated images creating an existence/visibility split.

**Not fixed in code, and here's why**: the *tempting* fix — have
`render_pages.py` warn or error when `n_pdfs` for a category is lower than
some expected count — needs a source of truth for "expected count" that
the script doesn't have and shouldn't hardcode (that's exactly the kind of
fact that belongs in the manifest/docs, not baked into the renderer). The
actual fix is procedural: **whenever a render step reuses images from an
earlier, separate render pass** (as opposed to a single uninterrupted
`render_pages.py` invocation, which is not subject to this because it
downloads-then-immediately-uses each file in one motion), cross-check that
category's reported PDF count against the true on-disk file count before
trusting a "0 failures" result. A same-session sanity check along the
lines of `pipeline/quality_checks.py` — e.g. comparing `raw.source_pages`
row counts per `(entity_type, season)` against an expected seasons list —
would catch this class of gap automatically and is worth adding if this
kind of partial/resumed render happens again.

## 21. `eval_against_gold.py`'s `zip(gold_rows, pred_rows)` roster comparison is position-based, not identity-based — a single extra/missing entry mid-page cascades into dozens of false "content error" diffs

**Status: open, methodology caveat rather than a data-quality bug.**
`eval_roster`'s `for g, p in zip(g_rows, p_rows)` pairs gold row *N* with
predicted row *N* purely by list position. On a page where the model's
entry list has even one more or fewer entries than the gold excerpt at some
point (e.g. it captured a real person the gold transcriber chose to skip,
or — see below — mis-parsed a role-only heading as a fake person), every
row *after* that point compares against the wrong person, even when the
model's actual data is correct once realigned.

**Concretely, on `full_run_2026-08-15_qwen3-vl-plus_local_corrected`**: a
by-hand classification of all 205 non-trivial field mismatches in
`eval_report.txt` found that **103 of them (50%) came from just two gold
pages** (`musicians_1890-91_SP_p000`, `theaterschoolstaff_1906-07_p000`)
where this cascade occurred:

- `musicians_1890-91_SP_p000`: the model's raw JSON has **3 extra entries**
  at the very top (Альбрехтъ, Христофоровъ, Тильпъ) before the point where
  gold's 14-row excerpt starts (at Направникъ). Re-indexing pred by +3 from
  that point, all 14 gold rows match the model's output **exactly** —
  family_name, first_name, patronymic, tenure_note_text, and instrument,
  byte for byte. Zero real errors on this page; the raw eval score showed
  ~70 field "mismatches" that don't exist.
- `theaterschoolstaff_1906-07_p000`: similar, but the shift (+2) has one
  genuine cause mixed in — the model captured a printed role-only phrase,
  "И. д. фельдшерицы" ("acting medical assistant", no name given), as a
  fake person entry with the phrase split across name fields (a variant of
  issue #19's "heading captured as its own entry" pattern, not yet covered
  by that fix since here the phrase parses as *something* rather than
  leaving family_name empty). One entry later, the model also included a
  real person ("Абрамова Александра") that gold's excerpt skipped. Both
  together account for the 2-row shift; re-indexed, the remaining 5 people
  match exactly.

**After removing both cascades**: of the 226 total field mismatches, only
**31 are genuinely isolated content differences** — 31/1627 fields checked
= **1.9%** actual error rate on content the model attempted to transcribe,
vs. the raw eval script's headline 86.1%-match / 13.9%-mismatch numbers,
which conflate real errors with this alignment artifact and with two other
already-tracked non-error categories (issue #3's `service_class` pattern,
5.4% of mismatches; and `heading_path`/text boundary-placement disagreements
like issue #2, 11.7%).

**Not fixed in code** — same reasoning as issue #20: a robust fix (matching
gold to pred by best-alignment/edit-distance on name rather than raw
position, à la a sequence-alignment algorithm) is worth doing before the
*next* eval run if roster scores are being reported or compared, but for
this run the discrepancy was caught and hand-verified rather than blocking
on a script change. Worth remembering: an eval_report.txt roster mismatch
block on one page for many consecutive rows is now a strong prior for "row
alignment cascade," not "the model listed a dozen people wrong" — spot-check
for a shifted-by-N pattern before concluding otherwise.

## 22. `credit_sum_mismatch` spot-check confirms: real digit-transcription errors, not source-document arithmetic mistakes

**Status: needs source check downgraded to confirmed, on this example** —
first instance from the 289 `credit_sum_mismatch` flags checked against the
actual scan. `balletartists_1890-91_MSK_p001__e021` (Гаврилова 2-я, Евдокія
Помпеевна): the model transcribed `credit_summary_text` as "Въ балетахъ—46;
въ операхъ—**13**. Все—10—64 раза," giving component_sum=46+13=59 vs. the
stated Всего=64 — flagged as a mismatch.

Checked against the actual page (`pdf/Spiski_BalletArtists/ForUpload_1890-91_Spisok_BalletArtistsMoscow.pdf`,
page 2, entry 22): the source reads "въ операхъ—**18**", not 13.
46+18=64 — **the printed 1890-91 yearbook is internally consistent; this is
a model digit misread** (8 → 3), not an original-document arithmetic error.
Also noted in passing: the model's "Все—10—64" is itself a garbled read of
"Всего—64" — "Всего" ("Total") is hyphenated across the line break as
"Все-" / "го—64" in the source, and in this book's italic type the
hyphenated "го" resembles "10", a plausible font-driven misread that
happened not to affect the final total in this instance.

**Not yet generalized**: only this one flagged instance has been checked
against source so far, out of 289. Worth doing before treating
`credit_sum_mismatch` as a reliable proxy for "digit error rate" — but this
first data point suggests the flag is catching genuine model errors rather
than reflecting inconsistencies in the historical record-keeping itself, at
least in this case. A useful follow-up: since digit-shape confusions (8/3,
6/0, 1/7...) are a recognizable OCR/VLM failure mode, checking whether a
flagged mismatch is explainable by a single plausible digit swap between
component_sum and stated total would be a cheap way to triage the other 288
without opening each source scan by hand.

## 23. `category_credit_count` sometimes captures the production count (N) instead of the performance count (X) — a systematic field-confusion bug, not digit noise, found by triaging issue #22

**Status: fixed (deterministic, analysis-layer) and applied.** Triaging all 289 `credit_sum_mismatch` flags (not just the one
spot-checked in issue #22) by testing whether the diff between
`component_sum` and stated `Всего` is explainable by a single plausible
digit error (units swap, tens swap, or transposition):

| cause | count | % of 289 |
|---|---|---|
| production-count-instead-of-performance-count confusion (this issue) | 187 (180 full + 7 partial) | 64.7% |
| plausible single digit-transcription error (units/tens/transposition) | 94 | 32.5% |
| genuinely unclear, needs individual source check | 8 | 2.8% |

**The mechanism**: many `credit_summary_text` sentences have the shape
"Въ N категорияхъ—X" (e.g. "Въ 7 балетахъ—21" = "in 7 ballets—21 [times]")
— two different numbers, N (count of distinct productions) and X (count of
total performances). `pipeline/schemas/roster.py` already has a regex
(`_PRODUCTION_COUNT_RE`) that reliably backfills N into
`category_production_count` from this verbatim text (added for a different
reason, per that code's own comment: "production count... was never asked
of the model as a structured field"). But the model's own *structured*
`count` field — the one that becomes `category_credit_count` — is supposed
to be X, and confirmed directly against raw JSON (e.g.
`balletartists_1894-95_SP_p005`, Шебергъ: `credit_summary_text` verbatim-
correct as "Въ 7 балетахъ—21; въ 1 оперѣ—1. Всего—22 раза.", but
`credits: [{"label": "балетахъ", "count": 7}, ...]` — the model put N=7
where X=21 belonged), the model sometimes emits N instead, silently and
inconsistently (sometimes correct within the same entry for one category
and wrong for another, e.g. `balletartists_1899-00_MSK_p003`/Лѣсновская).

**True scope, beyond the 289 flagged pages**: an entry with only one credit
category, or where N happens to equal X, never triggers a sum-mismatch flag
at all, so 289 undercounts the real error rate. Checked directly:
of 12,913 `category_totals` credit rows whose label has a matching
"N категория—X" pair in the verbatim text, **358 (2.8%) captured N where X
belonged**; 87.0% correctly captured X; 10.2% are unfalsifiable this way
because N happened to equal X.

**Fix applied**: mechanical and low-risk, following the same playbook as
issue #3 (`heading_path`/`service_class`) — deterministic regex-based
correction in `build_duckdb.py`'s `build_analysis_schema`, a new
`analysis.person_entry_credit.category_credit_count_clean` column
(`raw.person_entry_credit` is untouched, per the reproducibility
guarantee). Rather than reusing `_PRODUCTION_COUNT_RE` as a Python-side
fix, it's implemented directly in SQL — a per-row dynamic regex
(`'[Вв]ъ\s+(\d+)\s+' || label || '\s*[—-]\s*([\d.]+)'`, built from each
row's own `label` and matched against its parent entry's verbatim
`credit_summary_text`) — consistent with this project's rule that the
`analysis` schema is built via SQL only, no hand-editing. **Caught during
implementation**: an early version of this SQL matched only capital "Въ"
(sentence-initial), silently missing every category after the first in a
multi-category sentence, since only the first "Въ" in a sentence is
capitalized — prototyped and cross-checked against the independent Python
count (358) before landing in the pipeline script specifically to catch
this kind of engine/case-sensitivity mismatch; the corrected pattern
(`[Вв]ъ`, matching Python's behavior) reproduced the same 358 exactly.
Re-ran `build_duckdb.py` on the full corpus: confirmed **358 rows
corrected** (verified directly against raw JSON, e.g. Шебергъ's `балетахъ`
row: 7 → 21). Not propagated further downstream — checked, and
`build_research_model.py` never reads `person_entry_credit` at all, so
`research_dataset.sqlite` doesn't need rebuilding for this fix.

**Also updated `pipeline/prompts/roster_system.txt`** with an explicit
correct/wrong example distinguishing the two numbers, for any future
re-extraction of BalletArtists/Musicians pages — cheap to add now, doesn't
touch already-extracted data, but per issue #3's own lesson ("tried and it
didn't work... re-ran the exact page — zero improvement") there's no strong
expectation this alone would reliably fix the model's behavior on a re-run;
the deterministic analysis-layer fix is what's actually relied on for the
existing 1,349-page corpus.

## 24. `quality_checks.py`'s `credit_sum_mismatch` check itself had a bug — collapsed same-labeled credit rows across an artist's separate city tallies into one dict, silently discarding one city's numbers

**Status: fixed and applied**, found while beginning the manual
source-check review of the 102 entries left over after issue #23. Not a
transcription problem at all — a bug in the checking script itself,
producing false-positive flags.

**The mechanism**: `check_roster`'s credit check built `totals = {r["label"]:
r for r in rows if r["credit_type"] == "category_totals"}` — a dict keyed by
label. A ballet artist who performed in more than one city prints more than
one performance tally in a single `credit_summary_text` (a main tally, then
e.g. "Кромѣ того въ С.-Петербургѣ: ..." with its own tally) — meaning the
model correctly emits *two* `category_totals` rows both labeled "Всего",
and often a repeated category label too (e.g. "балетахъ" in both the Moscow
and the St. Petersburg block). Building a dict from these silently keeps
only the *last* occurrence of each label, discarding the first city's
numbers entirely and comparing a scrambled mix of both blocks against only
the second city's total — even when both underlying tallies were captured
completely correctly.

**Confirmed concretely**: `balletartists_1902-03_MSK_p001`, Гельцеръ:
raw components are Moscow (балетахъ=11, оперѣ=1, дивертиссементахъ=3,
Всего=15 — 11+1+3=15, correct) then St. Petersburg (балетахъ=3,
дивертиссементѣ=1, Всего=4 — 3+1=4, also correct). The old check collapsed
this to `{балетахъ: 3, оперѣ: 1, дивертиссементахъ: 3, дивертиссементѣ: 1,
Всего: 4}` (Moscow's балетахъ=11 overwritten by St. Petersburg's 3), sum=8
vs. stated=4 — flagged as a mismatch that doesn't exist in the actual data.
Same mechanism confirmed on 3 more names (Гримальди, Степанова, Рославлева,
across several seasons) — in every checked case, both underlying blocks
were internally consistent; only the check's aggregation was wrong.

**Fix applied**: replaced the label-keyed dict with a sequential block scan
in `pipeline/quality_checks.py` — `category_totals` rows print in source
order, so accumulate components in a list and reset it after each "Всего"
row (which closes out only the block since the *previous* "Всего", not the
whole entry), checking each block against its own stated total rather than
mixing blocks together. Verified against the 4 known false-positive names
before landing the fix; also verified it does NOT just suppress everything
— two other entries (Рославлева on a different page,
`balletartists_1895-96_MSK_p003`; Степанова on `balletartists_1901-02_SP_p004`)
correctly still flag as real mismatches even under the corrected logic,
confirming the fix discriminates rather than just quieting the check.

**Impact**: re-ran `quality_checks.py` on the full corpus — `credit_sum_mismatch`
flags dropped from 289 to 285 (net; some previously-hidden real mismatches
also surfaced once blocks stopped being scrambled together, so this is not
simply "4 removed"). `outputs/full_run/credit_mismatch_review.csv`
regenerated from the corrected flags: 102 → 99 entries still needing an
actual source check (after also excluding the 186 already resolved
deterministically by issue #23). This fix only touches the diagnostic
script's output (`quality_flags.csv`) — no raw or analysis data changes, and
`outputs/full_run/imperial_theaters.duckdb` did not need rebuilding.

## 25. Manual source-check review of all 99 remaining `credit_sum_mismatch` entries — complete; 50 confirmed corrections not yet applied to the database

**Status: review complete, DECISION PENDING (deliberately deferred by the
user — check here before assuming this is still open work).** Every one of
the 99 entries left after issues #23/#24 was checked individually against
its scanned source page. Result: **49 confirmed source-document arithmetic
errors** (+1 compound case) logged in `source_document_anomalies.md`, and
**49 confirmed model transcription errors** (+1 compound) logged in
`confirmed_credit_corrections.csv` — a near-even split, very different from
the pre-review guess that most of these were digit noise.

**Notable finding**: the digit confusion **3→8** recurs constantly across
the confirmed model errors (a dozen+ instances) — a specific, consistent
failure mode in this typeface, worth knowing if similar manual review comes
up again.

**What's NOT done**: `confirmed_credit_corrections.csv`'s 50 corrected
values are verified but **not applied anywhere in
`outputs/full_run/imperial_theaters.duckdb`** — they exist only as a
changelist. The natural next step (same playbook as issue #23: an
analysis-layer override column, `raw` left untouched) was proposed and
explicitly deferred by the user pending a later decision, not rejected —
don't build it unprompted, but don't forget it's sitting there either.

## 26. `person_candidate_review.csv` fully reviewed and applied (19 merges, 1 later reverted); surfaced a distinct, broader issue — non-person text captured as `person_entry` rows

**Status: candidate review closed; the non-person-entry issue documented,
not yet fixed.** All 54 Tier-2 person-candidate pairs were reviewed by hand
(originally 20 confirmed merges, 28 rejected, 6 left "Unsure" — see the
pipeline's own tenure/name-based rationale plus reviewer notes in
`person_candidate_review.csv`) and applied via `build_entities.py
--apply-decisions`. One merge (`Гавликowsкій ↔ Гавликowskiй, Николай
Людвиговичъ`) was subsequently reverted by the user after a closer look:
only 1 attestation per spelling, tenure dates that don't match (1887 vs
1899) with no exact-date corroboration — thin enough evidence to move back
to "Unsure" rather than stand as confirmed. Reverted by un-superseding the
person record and re-pointing its one entry directly (not by re-running
`--apply-decisions`, which has no mechanism to un-confirm an
already-resolved pair — resolved pairs are removed from the live
`entities.person_candidate` table entirely, tracked only in the historical
`person_merge_log`). Net result: **19 merges stand, 1 reverted to pending**
— `entities.person`/`research.person` active count is 3,678 (was 3,696
before any of this review; 4,359 raw Tier-1-resolved before any Tier-2
merging at all).

Recurring patterns among the confirmed merges: ъ/ь orthographic OCR
confusion (very common, near-certain same-person), single-letter
family-name OCR slips corroborated by an exact given-name + patronymic
match, line-wrap hyphenation artifacts in the extracted text
(`"Александро-\nвичъ"` reassembled as one word), and — a new failure mode,
not seen elsewhere in this project — **non-Cyrillic characters substituted
into Cyrillic names**: an Arabic/Persian "چ" for "ч", and stray Latin "if"/
"owsк" fragments mid-word (`Черемухинъ`'s patronymic, `Гавликовскій`'s
surname, the very case that was reverted above). Worth watching for
elsewhere if more review work turns up similarly garbled names.

**Also worth recording — the review process caught itself working
correctly on a close call**: the surname "Гейнъ"/"Гейнь" alone covers two
different real musicians (Фридрихъ, trumpet, tenure since 1878; Юлій,
violin, tenure since 1872), which looked at first glance like a risk of
conflating two people into one merge. Checking the actual merge log showed
the pipeline had already handled this correctly and independently of the
manually-reviewed pair: it auto-confirmed each musician's two spelling
variants separately, each corroborated by an *exact* matching tenure start
date (`shared_start_date`, the strongest evidence tier) — not name
similarity. The manually-reviewed "Гейнь ↔ Гейнъ" pair (no first name
attached) only covered a third, residual bucket of anonymous mentions, and
checking the surviving record IDs directly confirmed it was never folded
into either named musician's record. No misattribution occurred, but it's
a good example of why the `shared_start_date` vs. name-similarity-only
distinction matters when trusting a merge.

**The broader issue found in the process**: two of the 7 "duplicate" pairs
in the queue weren't people at all — `"Балетное отдѣленіе"` ("Ballet
Department") and grammatical word-forms of "student(s)"
(`"ученики"`/`"ученицы"`/`"ученика"`/`"ученицъ"`) had been captured as
`person_entry` rows with those strings as `family_name`. Checking beyond
just the pairs the duplicate-matcher happened to surface: **17 total rows**
in `raw.person_entry` match this pattern (department/summary-line text
where a name should be), including one that's clearly a truncated sentence
fragment — `"...номъ году въ балетномъ отдѣленіи состояло:"` ("...that
year, the ballet department had:", i.e. an introductory count-summary line,
not a person). This is a different animal from issue #19's
"heading-swapped-into-heading_path" pattern (where `family_name` ends up
empty and is recoverable) — here `family_name` is fully populated, just
with non-name text, so it passed every existing validation check and
silently became a phantom `entities.person`/`research.person` row.

**Scale**: 17/21,174 raw roster rows (~0.08%), resolving to roughly 10
distinct phantom person entities out of 3,677 active ones post-merge
(~0.3%) — small, but a real distortion for anyone running a "how many
distinct people" or "list all people at institution X" query. **Not fixed**:
the right fix is a small denylist/pattern filter (grammatical word-forms,
known department-heading fragments) applied in the `analysis` schema —
tag rather than delete, so `raw` stays untouched and a query can still
choose to include them — deferred, same as issue #23's confirmed-corrections
mechanism, pending a decision on priority rather than being technically
hard.

**Correction (found investigating issue #27 below): the "17 total rows"
scale estimate above undercounts.** That count came from a keyword regex
search across the whole corpus; a targeted check of just the `Graduates`
entity_type alone (which that regex under-caught) found ~18 more narrative
summary-paragraph rows plus 7 bare-headcount rows — i.e. this issue's true
scale is closer to 40+ rows, not 17, concentrated in `Graduates`. Doesn't
change the conclusion (still small relative to 21,174 total rows, same
deferred fix applies), but the number itself was wrong and is corrected
here rather than silently left stale.

## 27. Why ~1.7% of `raw.person_entry` rows have no `first_name` — two unrelated causes, one a genuine source feature and not a bug

**Status: investigated and explained, not a defect requiring a fix (except
where it overlaps issue #26 above).** 361 of 21,174 raw roster rows
(1.7%) have a blank `first_name`. Broken down by `entity_type`: Musicians
193, Graduates 104, BalletArtists 25, TheaterSchoolStaff 25, ProductionTeam
8, Administrators 6. Checked the two largest buckets in detail:

**Musicians (193 rows) — the underlying fact is a genuine source feature,
confirmed; the model's transcription of it is unreliable, not "faithful"
as first claimed below.** The yearbook prints two separate orchestra
rosters per season/city — "Оперный оркестръ" (Opera Orchestra) and
"Балетный оркестръ" (Ballet Orchestra) — and a musician who plays in both
only gets their full biographical entry (first name, patronymic, tenure
date) written out once, on the Opera roster. The Ballet roster
cross-references them instead: `"Аспернеръ (см. оперный оркестръ).
Віолончель."` — "(see Opera Orchestra). Cello." **Checked against 3 separate
scanned pages** (`ForUpload_1890-91_Spisok_OrchestraMoscow.pdf` p.4,
`ForUpload_1891-92_Spisok_OrchestraMoscow.pdf` p.3, `ForUpload_1892-93_Spisok_OrchestraSP.pdf`
p.4): on every one, essentially every no-first-name row carries this exact
phrase in print. So the underlying fact — no first name because it's
genuinely on a different page — holds for close to all 193 rows. But
breaking down what actually landed in `tenure_note_text` for those 193:

| captured | count |
|---|---|
| full "(см. оперный оркестръ)" phrase | 68 (35%) |
| only the instrument, phrase dropped | 44 (23%) |
| nothing at all | 78 (40%) |
| an unrelated pseudo-entry (see issue #28) | 3 (2%) |

**The model drops this specific repeated boilerplate phrase on 63% of the
rows where it's actually printed** — confirmed by direct comparison against
source on pages where the phrase is visibly present for every entry but
`tenure_note_text` is blank for most of them. This is a real recall failure
on a recurring piece of text, not something to call "faithful
transcription" — worth remembering as a category: a model can get the
*informative* part of a field right (no first name given) while still
losing the field that would explain *why* to a reader. Entity resolution's
fuzzy family-name merging (see issue #26's Гейнь/Гейнъ discussion) is what
actually recovers the full name regardless of whether the phrase survived,
so this doesn't block reconstructing who's who — but anyone reading
`tenure_note_text` directly and expecting it to explain an absent first
name will find it blank most of the time.

**Graduates (104 rows) — a mix of three unrelated causes**, checked by
sampling and pattern-matching:

| pattern | count | what it is |
|---|---|---|
| Name embedded whole in `family_name`, not column-split | 79 | Real graduates, e.g. `family_name="Александрова, Антонина."` with `first_name` left blank — these roll-call-style graduate lists don't print tenure dates at all, unlike other roster types, which may be why the flatten step never split the name into separate columns here |
| Class-enrollment narrative paragraphs | ~18 | Not people — e.g. *"Въ 1892—1893 учебномъ году въ балетномъ отдѣленіи состояло: На женской половинѣ—70 ученицъ..."* ("In 1892–93, the ballet department had: on the female side—70 students..."). Same underlying problem as issue #26 |
| Bare headcount rows | 7 | Not people — e.g. `family_name="Учениковъ"` paired with just a number in the tenure field. Same underlying problem as issue #26 |

The middle and bottom rows here are the source of the issue #26 scale
correction above. The top row (79) is a distinct, minor, genuine
name-parsing gap — real biographical data, just not normalized into
`first_name`/`family_name` the way other entity types are — worth fixing
alongside issue #26's filter if that work happens, but not urgent on its
own since the name is still fully present in `family_name`, just as one
combined string.

## 28. "Оставилъ службу [date]" (a resignation note) sometimes extracted as its own fake person entry, orphaning the date from the real person it belongs to

**Status: confirmed via source check, not fixed, and systemic (3 different
entity types affected).** Found while investigating issue #27: 5 rows
across the corpus have `family_name = "Оставилъ службу"` ("Left service")
with an actual date sitting in `tenure_note_text` — 2 in Musicians, 1 each
in Administrators and TheaterSchoolStaff (`administration_1895-96_p001`,
`musicians_1891-92_MSK_p003` ×2, `musicians_1897-98_SP_p001`,
`theaterschoolstaff_1896-97_p000`).

Checked one directly against the scan
(`pdf/Spiski_Musicians/ForUpload_1891-92_Spisok_OrchestraMoscow.pdf`, p.4):
the source reads `"Богуславъ, Флорентій Вячеславовичъ (съ 11 октября 1868
г.). Оставилъ службу 1 мая 1892 г."` — a second sentence that's part of
**Богуславъ's own entry**, not a separate person. The model split it into a
standalone fake entry instead, with "Оставилъ службу" mistakenly treated
as if it were a surname. Net effect: the real person's resignation date
(which should be their `service_periods.end_date_text`/`end_type="left
service"`) is orphaned onto a bogus non-person record instead, and the real
person's record is left looking like they're still active when they
aren't.

**Not fixed.** Same category as issues #19/#26 (a heading- or note-shaped
string ending up in `family_name`), but this specific sub-pattern — a
trailing status sentence that belongs to the *previous* entry rather than
introducing a new one — needs its own detection logic (look for
`family_name` matching known status phrases, then reattach the date to the
immediately preceding real entry on the same page) rather than the simple
denylist-and-tag approach proposed for #26, since here the right fix
actively moves data rather than just flagging it. Deferred with the rest of
this queue.

## 29. The Musicians cross-reference stubs from issue #27 are NOT actually reunited with their full-name record anywhere in `entities` — a real, quantified, fixable gap, not just a cosmetic missing phrase

**Status: quantified, not fixed.** Follow-up check on issue #27's "entity
resolution recovers this regardless" claim: it doesn't, currently. Checked
directly — **0 of the 193** no-first-name Musicians rows resolve (via
`entities.person_link` → `entities.person`, following `superseded_by`) to
a person record that has a first name. These cross-reference stubs are
sitting completely unlinked from the people they represent.

**But the underlying fact holds up at scale, not just anecdotally**:
fuzzy-matching each of the 131 distinct (surname, instrument) combinations
in this set against every named Musicians entry in the corpus (edit-distance
similarity > 0.82) finds a plausible full-name counterpart for **130 of
131**:

| match quality | count |
|---|---|
| close-spelling match, **same instrument** (strong — e.g. "Аспернеръ"/cello ↔ "Аспергеръ, Оскаръ"/cello) | 28 |
| close-spelling match, instrument differs or unspecified (weaker) | 102 |
| no match found | 1 — this is issue #28's "Оставилъ службу" pseudo-entry, correctly unmatched since it isn't a real person |

Concrete example: `"Аспернеръ"` (bare, Ballet Orchestra cross-reference,
cello) and `"Аспергеръ, Оскаръ"` (full entry, cello,
`musicians_1890-91_MSK_p000`) are almost certainly the same person, a
single-letter spelling variant (н/г). This exact pair was already in the
54-pair `person_candidate_review.csv` from issue #26 — marked "Unsure"
because the instrument-match evidence used here wasn't part of that
review's signal set. **This is effectively a second, larger merge-review
round** (131 new candidate pairs vs. the original 54) that entity
resolution's current Tier-2 candidate generation isn't surfacing at all —
worth revisiting `build_person_tier2_candidates()`'s matching logic to
understand why these weren't proposed as candidates in the first place
(likely a similarity-threshold or cross-instrument-comparison gap), rather
than only hand-reviewing this specific batch. Deferred pending a decision
on scope — the 28 same-instrument pairs are about as safe to confirm as
issue #26's strongest cases; the 102 weaker ones would need individual
judgment the way the original 54 did.

**Update (2026-08-18): the 28 same-instrument pairs applied — 19 merged, 5
held back, 4 excluded up front as ambiguous.** Rebuilding the (surname,
instrument) fuzzy match found 24 of the original 28 were unambiguous
one-to-one matches (the other 4 — Слуцкій/violin, Аспернеръ/cello,
Грецкій/cello, Кведнау/double bass — each matched more than one distinct
named candidate and were excluded rather than guessed at; see below).

Of the 24, applying them via `entities.person_candidate` +
`reconcile_person_merges()` (`match_reason='family_name_variant'`,
`tenure_signal='instrument_match'`, `tenure_evidence=<instrument>`)
surfaced two real bugs, both now fixed:

1. **Union-find's "lexicographically smallest `person_id` wins" survivor
   rule has no idea which side has the fuller name.** In 10 of the first 16
   merges applied, the blank-first-name stub's UUID happened to sort first,
   so the survivor kept the blank name and the full name it had just been
   merged with was the one marked superseded — the exact opposite of
   what issue #29 set out to fix. Caught by diffing survivor vs. absorbed
   name on every pair before moving on, not by trusting the merge counter.
   Fixed by explicitly filling the survivor's `canonical_first_name`/
   `canonical_patronymic` from whichever side was non-blank, for every
   pair, after `reconcile_person_merges()` runs — this needs to be standard
   practice for any future blank-vs-named merge batch, not just this one.
2. **3 of the 8 pairs the exact `family_name` lookup couldn't resolve
   turned out to already be mid-merge from an earlier session** (Зозель,
   Штадлеръ, Руссъ) — their `entities.person` rows existed but were already
   `superseded_by_person_id`-chained elsewhere from prior Tier-2 merges, so
   a direct-equality lookup against the pre-merge combo silently found
   nothing. Fixed by resolving through the full `superseded_by_person_id`
   chain to the current survivor before matching, which is exactly the
   discipline `_repoint_all_superseded()` already applies elsewhere in the
   pipeline — the ad-hoc merge script here just hadn't done it.

**Canonical spelling is a separate decision from "should these merge",
and the union-find survivor rule has no opinion on spelling quality
either** — raised by the user mid-review. Checked: of the 19 merged pairs,
14 had byte-identical family-name spelling on both sides (no spelling
question, pure blank-vs-named), but 5 genuinely disagreed on spelling
(Рамбоусекъ/Рамбоусенъ, Руссъ/Руссь, Штадлеръ/Шталлеръ, Туровичъ
фонъ-Охота/фонъ Охота, and a family-name-only pair originally read as
Зозелъ/Зоэль). For 4 of the 5, re-rendering the original PDF pages and
reading them directly confirmed the *majority*-frequency spelling is the
one actually printed — including finding the same person's
"(см. оперный оркестръ)" cross-reference stub, printed with the correct
spelling, on the very page whose full entry the model had mistranscribed
(к→н, ъ→ь, д→л letter-shape confusions, consistent with OCR failure modes
already logged elsewhere in this project). The 5th, Зозель, turned out to
be neither of the two DB variants on offer (Зозелъ, hard sign; Зоэль,
з→э slip) — the source prints **Зозель** (soft sign), confirmed across 16
of the 20 total occurrences of that surname in the corpus; this was only
caught by checking the actual page image rather than picking between the
two spellings the fuzzy-match had surfaced. Final verified spellings:
Рамбоусекъ, Руссъ, Штадлеръ, Туровичъ фонъ-Охота, Зозель — applied to
all 19 survivors' `canonical_family_name`/`canonical_first_name`/
`canonical_patronymic`, then propagated through
`build_research_model.py` + `build_datasette.py`.

**4 more of the 24 held back, not merged — a new, smaller instance of the
same "which spelling is real" question, this time on the named side
itself:** looking up exact `person_id`s exposed that Пекарскій (Давидъ
Исаевичъ), Ромашковъ (Капитонъ Андреевичъ), and Штернбергъ (Василій
[Васильевичъ]) each already have **2 (Ромашковъ, Штернбергъ) or even 3
(Пекарскій) unmerged `entities.person` records** for what looks like one
real person — a pre-existing duplicate the original Tier-2 pass never
caught, independent of the blank-stub problem. Petrovъ (violin) genuinely
has 2 different real people sharing "Василій" (patronymics Венедиктовичъ
vs. Ивановичъ) — a real, not spelling-related, ambiguity about which
Петровъ the bare stub means. None of these 4 were merged; picking a
survivor among 2–3 near-duplicates without resolving which of *those* are
themselves duplicates first would be guessing, not resolving. Left as a
follow-up, alongside the 4 excluded at the top of this update and the 102
weaker (cross-instrument) matches already flagged as future work.

**Net effect of this round:** 19 of 193 blank-first-name Musicians stubs
now correctly linked to a full-name record with a source-verified
canonical spelling (was 0/193). 4 pairs held on internal-duplicate
grounds, 4 pairs excluded as ambiguous, 102 weaker matches and the
remaining ~170 stubs not covered by this batch are still open.

**Update (2026-08-18, same day): the 8 held-back/excluded pairs all
resolved — 8 more stubs linked, bringing this batch's total to 27/193.**
None of the 8 turned out to need a real judgment call once actually
investigated; each had a mechanical resolution:

- **Слуцкій** (violin) — all 6 named spelling variants (Ипхекъ, Ицхекъ-
  Мейеръ, Ипхекъ-Мейеръ ×2, Ипхекъ-Мейерь, Инхекъ-Мейеръ) plus the bare
  stub share the *exact same* tenure start date, 1882-09-19 — this is one
  person, a Yiddish/Hebrew double name (Ицхак-Меир) mangled six different
  ways by п/ц/н letter-shape confusion. Source-checked
  (`musicians_1891-92_MSK_p001`, entry 74): correct spelling is
  **Ицхекъ-Мейеръ**, confirming the plurality (not majority) variant —
  the runner-up "Ипхекъ" cluster (5 occurrences across 3 spellings) was
  all OCR noise around the same root error.
- **Аспернеръ / Аспергеръ** (cello) — two bare stubs, both folding into
  the already-established **Аспергеръ, Оскаръ** (itself already a
  3-variant merge from an earlier round; shared tenure start
  1882-09-19/1883-09-19 across seasons).
- **Грецкій / Гречкій** (cello) — 3 active "Аполлонъ Адальбертовичъ"
  records plus a bare stub, all sharing tenure start 1882-09-19.
  Source-checked twice, independently (`musicians_1891-92_MSK_p001` entry
  28 and `musicians_1899-00_MSK_p002` entry 20): correct spelling is
  **Грецкій** (15 occurrences vs. 1 for "Гречкій" — ч/ц confusion), correct
  patronymic **Адальбертовичъ** (a stray ъ had produced "Адалъбертовичъ"
  once).
- **Кведнау** (double bass) — the "ambiguity" flagged earlier was stale:
  "Квелнау" had already been merged into "Кведнау, Фридрихъ" in an
  earlier round of this same session: only the bare stub needed folding
  in, trivially.
- **Пекарскій** (Давидъ Исаевичъ, violin), **Ромашковъ** (Капитонъ
  Андреевичъ, double bass), **Штернбергъ** (Василій Васильевичъ, cello)
  — each had 2–3 already-duplicate `entities.person` records for the
  same name that a previous Tier-2 pass had never caught, plus the bare
  stub. All records within each group share one exact tenure start date
  (1889-08-01 / 1883-09-01 / 1883-09-01 respectively) — strong enough to
  merge the whole group at once, stub included.
- **Петровъ** (violin) — genuinely 2 different real people named Василий
  Петровъ (patronymics Венедиктовичъ and Ивановичъ), so the family+first
  match alone really was ambiguous. Resolved anyway, without guessing: the
  bare stub appears on exactly one page, season 1890-91
  (`musicians_1890-91_MSK_p003`), and Ивановичъ's service didn't start
  until 1893 — only Венедиктовичъ (in service since 1876) could have been
  the person meant. Cross-referencing which candidate was even *eligible*
  by tenure range, not just which name matched, broke the tie.

**A third instance of the same union-find survivor bug, caught the same
way as before:** applying these 8 groups via the identical
`person_candidate` + `reconcile_person_merges()` path produced 2 more
blank/wrong-name survivors (the Аспергеръ and Грецкій groups both
collapsed onto their bare-stub member, discarding the name — same root
cause as the first round: lexicographically-smallest-UUID-wins has no
concept of "which side has the real name"). A full-table sweep
afterwards (any active survivor with a blank first name whose absorbed
side has a real one) found and confirmed these were the only 2
remaining; both corrected, and this sweep query is worth re-running as a
standing check after any future manual merge batch rather than relying
on spot-checking individual pairs.

**Running total for issue #29: 27 of 193 stubs now correctly linked**
(up from 0 at the start of this issue). Remaining open: the 102 weaker
(cross-instrument) matches, and the ~166 stubs not covered by either
batch.

**Update (2026-08-18, third pass): re-derived the "remaining" set fresh
from the database rather than trusting the 102/166 figures above — they
were stale the moment the first two passes landed, since many of the same
surnames span multiple seasons and one merge could resolve several rows
at once. Grounded count: 216 total blank-or-corrupted-first-name Musicians
rows (193 truly blank + 23 more where the model had captured the literal
word "см." — from a mangled "(см. …)" cross-reference — as if it were a
first name, a related but distinct manifestation of issue #18/#26's
cross-reference-as-name-field bug). 183 of the 216 are now correctly
linked; 33 (16 distinct surnames) remain.**

Of the 33 unresolved, one is issue #28's fake "Оставилъ службу" entry
(correctly left alone) and the rest split two ways:

- **Mechanical cleanup, no real ambiguity (fully resolved this pass):**
  most of the "weaker" (cross-instrument, name-uniqueness-only) matches
  from the first update above turned out to be completely safe once
  checked — 25 more surnames merged (Барковскій, Бѣлкинъ, Бѣлявскій,
  Добровъ, Кудике, Тарнке 1-й/2-й, Харитоновъ, Хилле, Цимбергъ, Штехертъ,
  Энгель, Эрбъ, Леманъ, Литтихъ, Нигофъ, Осиповъ, Очиневъ,
  Преображенскій, Снѣтковъ, plus the pure-spelling-variant clusters
  Алексѣенко, Гильдебрандтъ, Кажданъ, Керкешко, Кункели, Лебедевъ,
  Манкопъ, Назаковъ/Казаковъ, Сѣмашко, Цабель, Штаркъ). One more
  survivor-spelling bug found and fixed the same way as before
  (Керкешко's merged survivor had inherited the truncated misspelling
  "Керкешо" — 1 source occurrence vs. 15 for "Керкешко"). One exact-match
  preference pattern emerged and got applied 6 times (Берръ, Биндеръ,
  Валтеръ 2-й, Кремеръ, Орловскій, Штаакъ): when the bare stub's exact
  spelling *also* appears among the named candidates, prefer it over a
  same-ratio fuzzy match to a genuinely different surname (Бергеръ,
  Бендеръ, Кемеръ/Кеммеръ, Островскій were all false-positive fuzzy
  matches to unrelated people, not spelling variants).
- **A fourth instance of the union-find blank/garbage-survivor bug** —
  18 more cases across this pass (12 in the first sub-batch, 6 in the
  second), always the same shape: a merge chain collapses onto whichever
  member has the lexicographically smaller UUID, with no regard for which
  side has a real name. The full-table sweep query (now used four times
  running) continues to be the right tool — checking pairs one at a time
  would have missed several of these.
- **The "см."-corrupted rows needed their own cleanup pass**, separate
  from the blank ones — the earlier merge groups had only searched for
  bare (NULL/empty) `canonical_first_name`, so the 23 "см." records sat
  un-merged even after their correct target was already established.
  Folded all 23 into their existing survivors (or confirmed several were
  already correctly linked by the automated Tier-1/2 pass from earlier in
  the session).
- **Genuinely unresolved, 15 surnames (Гейнъ, Грибенъ, Гуманъ,
  Золотаренко, Каминскій, Мейеръ, Пертель, Плесковъ, Циммерманъ, Шмидтъ)
  — real multiple real candidates, tenure can't break the tie.** Unlike
  Морозовъ/Петровъ earlier (resolved because one candidate's service
  didn't overlap the bare stub's season at all), every remaining
  candidate pair is in active service throughout all of the relevant bare
  stub's seasons — elimination by date range genuinely doesn't work here.
  Two got partially narrowed (Каминскій: Александръ eliminated, svc
  started 1902; Золотаренко: Василій/"3-й" eliminated, svc started
  1894-12) but still have 2–3 tied candidates apiece. Resolving these
  would need something tenure dates can't give — e.g. checking the bare
  stub's exact position on the printed page against the parallel
  full-entry list's ordering, page by page. **Written up as
  `outputs/full_run/musicians_stub_review_queue.csv`** (54 rows: each
  bare occurrence × each surviving candidate, with tenure evidence and an
  empty `decision` column) rather than guessed at.

**Running total: 183 of 216 blank/corrupted-first-name Musicians rows now
correctly linked (0 at the start of issue #29; 78 after the first two
passes; 183 after this third pass). 33 genuinely left open** — 1 non-person
bug (#28), 15 real multi-candidate ties awaiting page-level review via
`musicians_stub_review_queue.csv`. `research_dataset.sqlite` rebuilt and
in sync.

**Update (2026-08-18, same day): worked through the remainder not covered
by either prior batch. 183 of 216 blank/misrecorded-first-name Musicians
rows now resolved (up from 27).** Note the denominator changed from 193 to
216 — re-deriving fresh turned up **23 more stub rows that issue #27's
original count missed entirely**, because their `first_name` field held
the literal string `"см."` (from a mis-split "(см. …)" cross-reference
note) rather than being blank — issue #27/#29's query only caught
`IS NULL`/empty, not this. Functionally these are the exact same bug —
now tracked together as one 216-row denominator, and this "см." mis-split
is worth a proper fix in `parse_and_validate.py` at some point rather than
being cleaned up ad hoc in every future entity-resolution pass like this
one had to.

**A second bug this round, closely related to the first: `"см."` was
contaminating the fuzzy-match *candidate pool itself*, not just the stub
side.** When first computing candidates for the still-unresolved stubs,
several surnames showed a phantom candidate literally named "см." — e.g.
`Бѣлкинъ` appeared to match both `Бѣлкинъ, Сергѣй` and `Бѣлкинъ, "см."`.
Filtering `"см."` out of the candidate pool (not just the stub side)
turned 10 previously-"ambiguous" surnames into clean single-candidate
matches. Lesson for any future pass over this data: treat `"см."` as a
blank-equivalent on *both* sides of a match, everywhere, not just where
issue #27 originally looked for it.

**Two new sub-bugs found and fixed while resolving individual surnames:**
- **`Тарнке`/`Тарике`** (the two Tarnke brothers, 1-й Густавъ and 2-й
  Ѳедоръ) combined three separate issues in one surname: a spelling
  variant (Тарике/Тарнке), issue #17's ordinal-lands-in-first_name-field
  bug (`family_name='Тарнке', first_name='1-й'` instead of
  `family_name='Тарнке 1-й'`), and duplicate unmerged records from an
  earlier pass — five records per brother, all one person, resolved via
  the entry-level page/season trail rather than guessing.
- **`Вальтеръ`** (violinist Петръ, "2-й") had the same ordinal-field bug
  plus a missing-softsign spelling variant (`Валтеръ 2-й`); resolved the
  same way.

**Tenure-range elimination worked for exactly one 2-candidate case this
round: `Морозовъ`.** Алексѣй's service didn't start until 1906; all 3
bare-stub occurrences are from 1890–93; only Сергѣй was even in service
then. The other four 2-candidate cases (Гейнъ, Грибенъ, Гуманъ, Плесковъ)
do **not** resolve this way — both named candidates in each pair were in
active service across every season the bare stub appears in, so there is
no elimination signal available from tenure dates alone. Left unresolved
rather than guessed.

**Cross-entity-type false positives, caught before merging:** a few
candidate pools looked ambiguous only because the fuzzy match wasn't
scoped to `entity_type='Musicians'` — e.g. `Осиповъ, Сергѣй` and
`Морозовъ, Петръ` turned out to be a Graduate/Ballet-Artist and a
TheaterSchoolStaff member respectively, unrelated people who happen to
share a common Russian surname with a real Musicians entry. Re-scoping
the candidate query to the same `entity_type` as the stub resolved these
cleanly (`Осиповъ`→Александръ, already Musicians-scoped) rather than
leaving them stuck as false 3-way ambiguities.

**Same union-find survivor bug, two more rounds, ~23 total instances now
across every batch in this issue.** The mandatory post-merge sweep (any
active survivor with a blank/`"1-й"/"2-й"`/`"см."` first name whose
absorbed side has a real one) caught and fixed 2 + 6 + 5 = 13 more cases
this round on top of the 2 from the previous round. This check needs to
be standard practice, run after *every* batch, not a one-time cleanup —
it has found a real instance every single time it's been run so far.

**Remaining unresolved: 33 rows / 13 surnames, all genuine multi-candidate
ambiguity or too complex to safely automate** — `Гейнъ`/`Гейнь` (2
real people, already known from an earlier session investigation to be
unresolvable this way), `Грибенъ`, `Гуманъ`, `Плесковъ` (2 real
candidates each, tenure doesn't discriminate), `Золотаренко` (3 brothers,
ordinal-suffixed, needs per-occurrence page checking),
`Каминскій` (4 real candidates), `Мейеръ` (3 real candidates),
`Пертелъ`/`Пертель` (2 real candidates, plus its own spelling variants),
`Циммерманъ` (2–3 real candidates), `Шмидтъ` (6+ real candidates,
likely including more ordinal-field-bug entries) — and `Оставилъ службу`,
which is issue #28's fake-entry bug and is correctly *not* matched to
anyone. Exported to
`outputs/full_run/musicians_stub_review_queue.csv` (candidate + tenure
evidence per bare occurrence, `decision` column blank) for human review
rather than guessing at any of these.

**Update (2026-08-19, fourth pass): the printed page itself resolved
most of the review queue — tenure dates weren't the only evidence
available, just the only evidence already sitting in the database.**
Re-rendered the actual "(см. оперный оркестръ)" cross-reference lines
from the source and found they usually print the instrument directly on
the line (`"Берръ (см. оперный оркестръ). Віолончель."`), even in cases
where the model hadn't captured that instrument into the row's own
`instrument` field. Cross-checking that printed instrument against each
candidate's own recorded instrument elsewhere resolved 7 of the 9
surnames in the queue, two of them by direct instrument confirmation
and the rest by eliminating a candidate whose recorded instrument
flatly didn't match:

- **Гейнъ → Юлій** (stub instrument: Скрипка, matches Юлій exactly;
  Фридрихъ plays Труба, eliminated).
- **Гуманъ → Вильгельмъ** (stub: Альтъ, matches Вильгельмъ exactly;
  Василій has no recorded instrument anywhere).
- **Пертель → Эдуардъ**, not Петръ — the *opposite* of what tenure
  alone would have suggested picking first: stub instrument is
  Контрабасъ, but Петръ's own record shows Вальдгорнъ (French horn),
  ruling him out; Эдуардъ has no conflicting record.
- **Плесковъ → Александръ**, not Николай — same pattern: stub is Альтъ,
  but Николай is recorded playing Первая скрипка elsewhere, ruling him
  out.
- **Циммерманъ → Василій**, not Рейнгардъ — stub is Контрабасъ,
  Рейнгардъ is recorded on Труба (trumpet) elsewhere, ruling him out.
- **Грибенъ → Августъ** (stub: Ударные инструменты; Августъ's own
  record shows Литавры, i.e. timpani, a specific percussion instrument
  — read as a plausible match rather than a certainty, since neither
  candidate contradicts and Ѳедоръ has no instrument recorded at all).
- **Мейеръ → Валентинъ**, resolved differently: the printed page shows
  `Мейеръ, Іоганъ-Фридрихъ` isn't a violinist candidate at all but
  holds a separate, directly-listed role as *répétiteur* (rehearsal
  coach) for the Ballet Orchestra — eliminating him by role, not
  instrument, leaves Валентинъ as the only remaining candidate for the
  "Вторая скрипка" cross-reference.

**Золотаренко narrowed but not resolved**: the same page-check
confirmed the stub's instrument is Скрипка (violin) and, more usefully,
showed that `Золотаренко, Иванъ Петровичъ` already has his own
*separate, direct* Ballet Orchestra listing as a trombonist — meaning
he can't also be the person behind an Opera Orchestra violin
cross-reference. That eliminates him (was previously a 3-way tie, now
correctly excluded), leaving a genuine 2-way tie between the other two
brothers, Павелъ and Петръ, neither of whom has an instrument recorded
anywhere to break it.

**Каминскій remains fully unresolved**: confirmed the stub's
instrument (Первая скрипка) but neither remaining candidate (Робертъ,
Ѳедоръ) has an instrument recorded on any appearance to compare
against — this one genuinely needs something beyond what's in the
database, e.g. checking whether either candidate's other career
details (recorded elsewhere in the yearbook, outside this dataset) fit
a first-violin chair.

**Шмидтъ, not in the original queue export** (it had too many
candidates — 6+ — to fit the same triage cleanly), was checked the
same way once the pattern above suggested it was worth a direct look:
the stub prints `Віолончель`, matching `Шмидтъ, Иванъ Михайловичъ`
(directly recorded as a cellist) exactly. Resolved. Also found and
fixed two ordinary duplicate-record pairs for other Шмидтъ family
members while on that page (Францъ and a separately-spelled Фридрихъ),
unrelated to the cross-reference question but sitting right next to it.

**Running total for issue #29: 207 of 216 rows now correctly linked**
(0 → 78 → 183 → 207 across four passes). **9 rows genuinely remain
open**: `Оставилъ службу` (3 rows, issue #28's fake-entry bug, correctly
left unmatched — not a gap), `Золотаренко` (3 rows, real 2-way tie
between brothers, no instrument evidence either way), `Каминскій` (3
rows, real 2-way tie, no instrument evidence either way).
`musicians_stub_review_queue.csv` trimmed down to just these last two
surnames. `research_dataset.sqlite` rebuilt and in sync.

**Update (2026-08-19, fifth pass): Золотаренко resolved, Каминскій
confirmed genuinely unresolvable from this dataset alone.**

Pulling every raw appearance of both surnames (not just the two
candidates already narrowed to) turned up a decisive fact for
Золотаренко: `Петръ Петровичъ` — one of the two remaining tied
candidates — has his own separate, direct listing as **Капельмейстеръ**
(conductor) of the Ballet Orchestra starting in 1891-92, the same
seasons two of the three bare cross-reference occurrences are from. A
rank-and-file violinist cross-reference can't be the orchestra's own
conductor that same season — same elimination logic as Иванъ earlier
(a person with their own direct listing isn't the one behind a "see
also" pointing elsewhere). That leaves `Павелъ Петровичъ` for those two
seasons; the third (1890-91, before Pyotr's promotion, so not
automatically excluded that year) was resolved the same way for
consistency — the cross-reference plausibly names the same person each
year — corroborated by Pavel being directly confirmed a violinist
(Первая скрипка) in a later season (1904-05). All 3 bare occurrences
plus 2 unmerged Pavel duplicates (shared start date, 1882-09-19) merged
into one record.

Каминскій got the same full-history check and came up empty-handed —
not for lack of trying. Both `Робертъ Николаевичъ` and `Ѳедоръ
Николаевичъ` are independently confirmed playing **Первая скрипка**
(first violin) themselves, on different seasons — the earlier "neither
has an instrument recorded" note was wrong; the instrument was there,
just sometimes sitting in `rank_or_title` instead of `instrument` (a
field-boundary mixup, same shape as issue #16). Both matching the stub's
own instrument doesn't break the tie, it just confirms both remain
equally plausible. They also share a patronymic (Николаевичъ) — very
likely brothers, alongside a third, `Александръ Николаевичъ`, who joined
the Moscow orchestra later (1902-03 on, second violin) — a nice
confirmation that this is a real musical family, but no help
distinguishing which brother a specific 1890s cross-reference meant.
Genuinely nothing left in this dataset to break the tie; resolving it
would need something outside it entirely — secondary biographical
sources on the Kaminsky family, or the original bound volume's physical
layout in a way page images alone haven't surfaced.

**Running total for issue #29: 210 of 216 rows now correctly linked**
(0 → 78 → 183 → 207 → 210 across five passes). **6 rows remain open**:
`Оставилъ службу` (3 rows, issue #28's fake-entry bug, correctly left
unmatched) and `Каминскій` (3 rows, genuine tie, confirmed
unresolvable from this dataset). `musicians_stub_review_queue.csv`
trimmed to just Каминскій. `research_dataset.sqlite` rebuilt and in
sync.

## 30. Full audit of `research.person`'s `canonical_family_name`/`canonical_first_name`/`canonical_patronymic` for non-name text — two small confirmed-and-fixed bugs, one new structural finding still open

Ran a heuristic scan (bracket/paren contents, pure numbers, bare ordinal
suffixes, single non-letter characters, stopword function-words, stray
Latin-only tokens) across all three canonical name fields in the published
`research.person` table, not just `raw` — the point was to check what
actually ships, not what the extraction step produced before
Tier-1/Tier-2 cleanup. Findings, by severity:

**Fixed immediately (small, unambiguous, same pattern as issues #17/#18
already established this session):**
- `Марквардтъ, Августъ` (Musicians, 8 raw appearances across 1894–1902)
  had `canonical_patronymic = "(онъ же и капельмейстеръ военной музыки)"`
  — "(he is also the kapellmeister of the military band)" — a genuine
  printed role annotation that landed in the patronymic slot every single
  time. He appears to have no real patronymic in the source (common for
  the German-surnamed musicians in this corpus); cleared to `NULL`.
- `Пигулевскій, Василій Фавстовичъ` (TheaterSchoolStaff, priest) had one
  of 47 appearances (`theaterschoolstaff_1899-00_p002__e025`; written
  `1899-90` at the time, relabelled by #71) with
  `patronymic = "Фавстовичъ (священникъ церкви Училища)"` — the role
  annotation appended onto an otherwise-correct patronymic — while every
  other appearance splits it correctly into `patronymic="Фавстовичъ"` +
  a separate rank/role field. Corrected to match. Fixing this also
  surfaced that this same person was split across 3 unmerged
  `entities.person` records (one of them with `first_name="Василій
  Фавстовичъ"` un-split) — merged, corroborated by an exact shared
  service-start date (1886-12-20) across all three.
- Two more confirmed instances of issue #26's "non-person text captured
  as a `person_entry` row" pattern, found by this scan rather than the
  original keyword search: `family_name='†'`
  (`theaterschoolstaff_1902-03_p002__e027`, `first_name='1902 г.'`) — a
  death-marker footnote that split off from its actual owner into its own
  fake row, the death-notice equivalent of issue #28's "Оставилъ службу"
  bug; and `family_name='И.', first_name='д.', patronymic='фельдшерицы'`
  (`theaterschoolstaff_1906-07_p000__e014`) — almost certainly a mangled
  "и.д. фельдшерицы" ("acting medical assistant") subsection heading that
  got extracted as if it were the person it introduces, with the real
  person (`Абрамова, Александра Дмитріевна`) captured separately right
  after, missing its role label. Left as-is in `raw`/`entities` per issue
  #26's existing "tag rather than delete, pending a priority decision"
  policy — not deleted unilaterally, just added to that issue's count and
  flagged here for visibility. Issue #26's scale estimate should be read
  as "40+, and we keep finding more via unrelated checks" rather than a
  final number.
- Confirmed as **expected, not new**: the residual bare-ordinal values in
  `first_name`/`patronymic` (3 + 5 rows) are exactly issue #17's
  documented 6 exceptions that don't pass the "patronymic looks like a
  real name" guard and were deliberately left alone; the 6 residual "см."
  rows in `first_name` are the still-open cases from issue #29's review
  queue, not a new problem.

**New finding, not yet resolved — real names bundled with a stage-name/
alias/maiden-name annotation, causing genuine entity fragmentation, not
just messy display text:** 14 `research.person` rows have
`canonical_family_name` containing a parenthetical — `"Билибина (по
театру Корнева)"`, `"Гаврилова (Воскресенская)"`, `"Эльпе
(Петропавловская)"`, `"Холоповъ (онъ-же Хлоповъ)"`, etc. — almost all
BalletArtists, plus a few ProductionTeam/Graduates. These aren't
non-names; the source genuinely prints "stage name" or "aka" or "née"
annotations for performers who used more than one professional name. The
schema has nowhere to put that information except inline, so the model
folds it into `family_name` — inconsistently: on other appearances of the
*same* person, the annotation instead leaks alone into `first_name`
(`family_name="Гаврилова", first_name="(Воскресенская)"`), and on others
it's dropped and the row is just the bare name (`family_name="Гаврилова",
first_name="Евдокія"`). Checked two of the fourteen people directly:
**"Гаврилова, Евдокія" is currently split across 8 different unmerged
`research.person` records** (4 clean duplicates, 1 compound, 1 with the
annotation leaked into `first_name`, 2 OCR-spelling variants of the given
name), and **"Петропавловская"/"Эльпе" — the same dancer's two alternating
stage names — is split across 4**, with one record per direction
(`"Петропавловская (Эльпе)"` and `"Эльпе (Петропавловская)"` both exist as
separate rows, alongside a bare `"Петропавловская"` and a bare
`"Эльпе"`). Not checked yet: whether the other 12 of the 14 people show
the same fragmentation pattern, or how many of the 21,174 raw rows this
touches in total.

**Update (2026-08-19): all 14 people resolved.** Went through each by
hand the same way as the Musicians batches — tenure-date corroboration
per group, never assumed same-surname automatically meant same-person.
That caution paid off immediately: the very first check
(`"Гаврилова (Воскресенская)"`) turned out to be **two different real
dancers who happen to share both surname and given name** —
`"Гаврилова 1-я, Евдокія Ивановна"` (service since 1872) and
`"Гаврилова 2-я (Воскресенская), Евдокія Помпеевна"` (service since
1884) — distinguished in the source by the standard homonym-ordinal
convention (`1-я`/`2-я`) and by patronymic, with the stage-name
annotation belonging to only the second woman. Had I merged on
surname+given-name alone, this would have wrongly fused two people. Every
subsequent group was checked patronymic-first before merging.

Final breakdown of the 14:
- **7 needed real fragment-consolidation** (2–6 duplicate records each,
  now 1): Гаврилова 1-я / 2-я (Воскресенская) (2 distinct people, 2+6
  records → 2), Никифорова (Стравинская) (2→1), Горская (Струкова) (5→1),
  Эльпе (Петропавловская) (4→1, "Эльпе" chosen as the primary spelling —
  8 occurrences vs. 2 for "Петропавловская"), Висковская (Калинникова)
  (2→1), Кучинскій (Бурманъ) (3→1), Дмитріева (Ѳедорова) (5→1, including
  one more orphaned `first_name="(Федорова)"` fragment turned up only by
  re-running the full scan after the first pass — worth doing every time,
  not assuming one pass catches everything).
- **5 were already single, isolated appearances with nothing to
  merge** — confirmed by checking the actual printed page rather than
  assuming: `Рыкъ (по театру Борисовъ)`, `Билибина (по театру Корнева)`,
  `Щернваль (по театру Таирова)`, `Холоповъ (онъ-же Хлоповъ)`,
  `Нольте (фонъ)`. All five transcribed verbatim-accurately from the
  source; there was simply no separate bare-name appearance anywhere else
  in the corpus to fragment against. `"по театру X"` reads as a stage-name
  annotation (confirmed against the source: `Рыкъ (по театру Борисовъ),
  Иванъ Генриховичъ` prints exactly that way in a graduation-list entry),
  not a "prior company" note as first guessed — corrected before acting
  on the wrong reading. `Нольте (фонъ)` is genuinely printed that way in
  the source (the `von` prefix trailing in parens rather than leading) —
  left as printed rather than restructured, since restructuring an
  unverified guess about prefix placement isn't something to do without
  more than one occurrence to check it against.
- **2 more instances of the union-find blank/wrong-name survivor bug**
  surfaced during this batch (Горская's survivor briefly became the bare
  `"Струкова"` stub with no first name at all; Гаврилова 2-я's survivor
  briefly inherited the OCR-garbled `"Евлогія"` instead of `"Евдокія"`) —
  caught and fixed by the same post-merge verification used throughout
  this session, not by trusting the merge counter.

`research.person` is down to 1 row per person for all 14 (was up to 8 for
one of them). Remaining flagged rows in the full non-name scan (30 total)
are all already-tracked, expected residuals: issue #17's 9 documented
ordinal-alone exceptions, issue #29's 6 open "см." rows, and the 13
family_name strings that legitimately still contain a parenthetical —
that's not a bug anymore, just a data-modeling note (no dedicated
alias/stage-name field exists in the schema) now that each represents
exactly one correctly-consolidated person rather than a fragmented one.

## 31. `display_name` went stale on every manual entity-merge fix made this session — found while answering an ordinary question about ordinal tracking

**Status: found and fixed.** Every manual merge/correction earlier in
this session (Musicians cross-reference stubs, the alias/stage-name
fragmentation work, the instrument-based review-queue resolutions) wrote
directly to `entities.person.canonical_family_name`/
`canonical_first_name`/`canonical_patronymic`/`ordinal_suffix` via `UPDATE`,
but never touched `display_name` — a separately-stored, pre-composed
string set once by `build_person_tier1()` and never recomputed after.
`research.person` copies `display_name` straight through from
`entities.person` (see `build_research_model.py`), so the stale value
shipped all the way to the published layer. Found by accident: answering
a user question about how ordinal suffixes are tracked, grounding the
answer with a query on the two previously-merged Gavrilova records,
turned up `display_name = 'Гаврилова, Евлогія Помпеевна'` (the
OCR-garbled first name, no ordinal, no alias) sitting right next to a
*correct* `canonical_first_name = 'Евдокія'` on the same row.

**Scale**: 48 of 3,526 active `research.person` rows — every survivor
this session had manually corrected, no others. Fixed by recomputing
`display_name` for every active survivor from its own canonical fields
(same formula `build_person_tier1` uses: family + ordinal, then
`", " + first + patronymic` if either is present), verified 0 mismatches
remain, and rebuilt `research.person` / `research_dataset.sqlite`.

**Lesson for any future manual `entities.person` fix**: `display_name`
is not derived at query time — it must be explicitly recomputed after
any UPDATE to the fields it's composed from, the same way
`_repoint_all_superseded()` must be re-run after any merge. Worth adding
a small helper function for this rather than relying on remembering it.

## 32. `raw.person_entry.instrument` (and the published `research.person_appearance.instrument`) sometimes held non-instrument text — fixed via a new analysis-layer `instrument_clean`

**Status: found and fixed.** A full audit of `instrument` (33 distinct
values across 1200 non-null rows, all Musicians) found 23 that weren't
instruments at all:

- **21 rows**: the literal cross-reference note `"см. оперный оркестръ"`
  ("see Opera Orchestra") — the same convention behind issue #29's
  Musicians cross-reference stubs, but here landing in the `instrument`
  field of that specific appearance rather than (or in addition to)
  causing a blank `first_name`. Issue #29's work resolved *who the
  person is* for most of these; it never touched *this specific
  appearance's* `instrument` value, which was still literally the
  cross-reference sentence.
- **2 rows**: a resignation note (`"Оставилъ службу 1 октября 1903 г."`,
  Барсукъ-Самборскій) and a transfer note (`"Переведенъ съ 1 октября
  1902 г. въ Малый театръ."`, Гейслеръ) — both on real, correctly-named
  people, both genuinely useful information that belongs with
  `tenure_note_text`, just captured into the wrong field on that one
  appearance.

Worse: none of this was caught before shipping, because
`research.person_appearance.instrument` turned out to be a **straight,
uncleaned passthrough from `raw.person_entry`** — every other roster
field with a known quirk (`service_class`, `heading_path`) already gets
cleaned in the `analysis` layer before reaching `research`, but
`instrument` had no such step and this went unnoticed until an explicit
audit.

**Fix**: added `instrument_clean` and `tenure_note_text_clean` to
`analysis.person_entry` (`build_duckdb.py`), pure SQL derivations over
`raw`, non-destructive as always. `instrument_clean` is NULL wherever
the value is the cross-reference note or a resignation/transfer
sentence; `tenure_note_text_clean` appends the resignation/transfer text
onto the real tenure note for those 2 rows instead of discarding it.
Repointed `build_research_model.py`'s `research.person_appearance`
insert from `raw.person_entry` to `analysis.person_entry`, using the two
`_clean` columns. Verified 0 contaminated rows remain in the published
table (1177 non-null `instrument` values now, all genuine instruments,
down from 1200).

**A real DuckDB gotcha hit while building the fix, worth flagging for
next time**: the first draft used `instrument ~ '^(Оставилъ
службу|Переведенъ)'` (the `~` regex-match operator) and it silently
matched nothing — not just the anchored alternation, but a bare
`instrument ~ 'Оставилъ'` with no anchor at all, confirmed by direct
side-by-side testing (`starts_with()` on the identical string returned
`true`; `~` returned `false`). `regexp_matches()` with the byte-for-byte
identical pattern worked correctly. Root cause not fully chased down
(DuckDB v1.5.5), but the practical lesson holds: **prefer
`regexp_matches()`/`regexp_extract()` over the bare `~`/`!~` operators
when matching Cyrillic (and presumably other non-ASCII) text in this
codebase** — `~` cannot be trusted here even for a plain literal prefix
with no special regex syntax involved.

**Not done, and worth a decision later, same as issue #23/#25's
deferred-corrections pattern**: `instrument_clean` still has legitimate
spelling variants that a strict count-only cleanup didn't touch —
`Вальдгорнъ`/`Вальторнъ`/`Вальдгорнь`/`Вальдгорнт` (French horn, 4
spellings), `Віолончель`/`Виолончель`/`Віолончелъ` (cello, 3 spellings,
partly the documented і/и pre-reform variant), and
`Фортепіано`/`Піанистъ` (piano vs. "pianist," an instrument-vs-role
distinction rather than a misspelling). These are all genuinely
instruments, just inconsistently spelled/labeled — a different, smaller
problem than what this issue fixed, deferred pending a decision on
whether it's worth normalizing.

## 33. TheaterSchoolStaff: a real duplicate merged, two role-heading phantom people, and the pipeline's first actual non-person denylist

**Status: found and fixed**, prompted by a direct ask to follow up on
three specific findings surfaced while surveying non-Musicians people
issues.

- **Сенкусь/Сенкусъ merged** (ь/ъ spelling variant, all 5 appearances
  share tenure start 1903-09-01, plus one appearance where the model had
  duplicated the surname into `first_name` too — `family_name="Сенкусъ",
  first_name="Сенкусъ"` — cleared as part of the same merge). Canonical
  spelling `Сенкусъ` (3 occurrences vs. 2).
- **"Священникъ" (Priest) and "Дьяконъ" (Deacon) confirmed as role
  headings, not people** — checked against the source
  (`ForUpload_1896-97_Spisok_Teachers.pdf` p.1): under the section
  "Причтъ церкви Училища" (Clergy of the school's church), the printed
  structure is a bold role label ("Священникъ.") immediately followed by
  the real named person holding it (Пигулевскій, already resolved this
  session in issue #30). Both role labels were being captured as their
  own phantom `person_entry` rows across every season they appear —
  exactly issue #26's "department/role heading captured as a person"
  pattern, now with a confirmed, hand-verified example.
- **Флоринскій's orphaned resignation note recovered**: the same page
  confirmed the standalone fake entry (`family_name="Оставилъ службу"`,
  issue #28's bug) sitting between Флоринскій's entry and his successor
  Сперанскій's is Флоринскій's own resignation date (1 февраля 1897 г.,
  the same day Сперанскій's tenure starts) — recovered into his
  `tenure_note_text_clean` via a single hand-verified case in
  `build_duckdb.py`, not a general rule (a general LAG-based "borrow the
  previous row's tenure note" rule was considered and rejected — see
  below).

**This is also the first time issue #26's long-deferred "tag rather than
delete" plan was actually built**, rather than re-deferred again: a
`NON_PERSON_IDS` list in `build_research_model.py`, excluding confirmed
phantom `entities.person` records from the *published* `research.person`
and `research.person_appearance` tables only — `entities.person`/
`entities.person_link` are left completely untouched, so the phantom
records are still there for anyone querying the working layer directly,
exactly as issue #26 always intended. Seeded with 5 hand-verified
person_ids: Священникъ, Дьяконъ, the TheaterSchoolStaff "Оставилъ
службу" phantom, and the two issue #30 finds ("†", "И.") that had been
found and left in place pending exactly this mechanism. Each of these 5
phantom person_ids turned out to have *more* linked appearances than the
single row each was originally confirmed from (15 total, not 5) — Tier-1
collapses every appearance with byte-identical text onto the same
person_id regardless of season, so fixing one instance fixes every
season it recurs in for free. `research.person`: 3524 → 3518.
`research.person_appearance`: 21174 → 21159.

**Deliberately not attempted: a general rule for recovering *every*
issue #28 resignation-note orphan via `LAG()` (previous row on the same
page).** Worth recording why, since it's an obvious next step someone
might reach for: the pattern (note belongs to the immediately preceding
row) held for this one confirmed case, but hasn't been checked against
enough other instances to trust as a blanket rule — e.g. this session
also found a *garbled* variant in ProductionTeam (`family_name="Оствайлъ"`,
not even a clean copy of the phrase) that a simple text-match rule
wouldn't catch, and there's no guarantee every resignation-note orphan
sits directly after its owner rather than, say, after a page break. Safer
to keep confirming instances by hand (as this issue and #28 both did) and
add each to `NON_PERSON_IDS`/a future recovery case individually than to
generalize from a sample of one and risk silently attaching someone's
resignation date to the wrong neighbor.

**Still open**: the broader issue #26 backlog (~40+ rows, mostly
Graduates narrative/headcount rows, never individually confirmed against
a specific person_id the way these 5 were) and the ProductionTeam
"Оствайлъ" garbled instance flagged in the same non-Musicians survey —
neither addressed here, both straightforward to add to `NON_PERSON_IDS`
once each is individually verified the same way.

## 34. Graduates name-parsing gap fixed, plus a real bug in the shared date parser affecting 4 entity types, plus a full ballet-graduates tenure-date extraction

**Status: fixed/built**, prompted by the user's specific research need:
names and confirmed service-start dates for ballet school graduates,
sourced from the Theater School Reports' own text, cross-checked against
(not replaced by) the BalletArtists rosters.

**Part 1 — the original name-parsing gap (issue #27's "79 rows" finding),
fixed.** All 79 rows print `family_name="Surname, Firstname."` as one
string instead of splitting into `family_name`/`first_name` the way
every other entity_type does. Confirmed uniform (no patronymic ever
printed here, no ordinals, exactly one comma) — safe to split by regex.
Added `family_name_clean`/`first_name_clean` to `analysis.person_entry`
(`build_duckdb.py`, scoped to `entity_type='Graduates'` only, so an
incidental comma elsewhere is never touched) and applied the same split
directly to the 79 corresponding `entities.person` records. **Explicitly
did not attempt to merge these with the fuller-form duplicates already
in `entities.person`**: 63/79 have at least one existing match by exact
name, but most common names have 2-7 candidates (e.g. "Смирнова, Марія"
has 7) — exactly the kind of ambiguity this project has consistently
refused to guess through elsewhere (see the Гаврилова case in issue
#30). Name field is now clean; identity-merging is deliberately left
undone.

**Part 2 — a real bug in the shared `parse_russian_date()` utility,
affecting 4 entity types, not just Graduates.** The date regex in
`pipeline/schemas/dates.py` required whitespace directly after the day
number, so a hyphenated ordinal ("1-го сентября 1892 г.", vs. the more
common "1 сентября 1892 г." printed elsewhere) silently failed to parse
— confirmed this affected 188 rows across BalletArtists, Musicians,
TheaterSchoolStaff, *and* Graduates, not a Graduates-only quirk. Fixed
by making the ordinal suffix optional in the regex; verified against
both the previously-broken and previously-working cases with no
regression.

**Part 3 — full ballet-graduate tenure-start-date extraction, sourced
from the Report text as primary (per explicit instruction), cross-checked
against BalletArtists rather than inferred from it.** Built
`outputs/full_run/ballet_graduates_tenure.csv` (417 ballet-department
graduate rows — drama-department graduates, identified by heading_path
`Со свидѣтельствами / Ученицы` / `Съ аттестатами / Ученицы` and
confirmed against the Билибина/Рыкъ page found earlier this session, are
correctly excluded):

| source | count | meaning |
|---|---|---|
| `report_per_row` | 197 | date parsed directly from this row's own `tenure_note_text` |
| `report_hand_verified` | 25 | this row's own text had no date; the assignment paragraph exists on the source page but was dropped by the original extraction entirely (confirmed by direct page check, not recoverable by re-parsing existing data) — 2 cohorts hand-verified (13 people incl. Карсавина/Karsavina, 1902; 12 people, 1899) |
| `balletartists_crossref` | 149 | no usable Report text; date instead taken from a single, plausible (graduation-year-adjacent) BalletArtists record |
| `no_service_record` | 36 | no BalletArtists record at all — did not enter Imperial service, or entered somewhere this dataset doesn't capture (per explicit instruction: not everyone enters service, don't assume a date exists) |
| `ambiguous_crossref` | 8 | multiple plausible BalletArtists candidates, genuinely can't pick one (common-name collision) |
| `no_plausible_crossref` | 2 | a same-name BalletArtists record exists but with a date implausibly far from graduation (likely a different, unrelated person) |

**A genuine cross-document discrepancy found and documented, not
"fixed"**: cross-checking all 222 Report-sourced dates against
BalletArtists found 26 disagreements, of which 21 form a clean pattern —
two entire graduating cohorts (1896-97, 7 people incl. Ваганова/Vaganova;
1897-98, 14 people) show the Report stating "мая" (May) where
BalletArtists consistently states "іюня" (June), identically, across
every season on record (11 and 10 seasons respectively). Verified this
is not a transcription error on either side (direct page check for the
1896-97 cohort: the Report genuinely prints "мая"). Full writeup in
`docs/eval/source_document_anomalies.md`. Kept the Report's own date as
the CSV's primary value (per instruction) with the disagreement flagged
in the `note` column, rather than silently preferring one source.

**Not attempted**: extending `report_hand_verified` beyond the 2
confirmed cohorts — there are likely more pages where the assignment
paragraph was dropped by extraction (the `no_service_record`/
`ambiguous_crossref` buckets almost certainly contain some), but finding
them requires the same page-by-page check done for these 2, not a
mechanical rule. The Moscow 1901-02 cohort (3 people) was checked and the
assignment paragraph, if printed, falls outside this particular scan's
2-page range — left as `no_service_record`/unconfirmed rather than
guessed.

**Addendum to #34 (same day): checked whether missing patronymics in
`ballet_graduates_tenure.csv` were a real gap.** Verified per-page: 43 of
47 Graduates pages are uniformly one way (every row has a patronymic, or
none do) — confirmed genuine against several already-viewed scanned
pages, not something the extraction dropped. Exactly one page was mixed
(`graduates_1890-91_p002`, 19/21 rows), and both exceptions turned out to
be a real, different, narrow bug: `first_name` and `patronymic` printed
correctly on the page but run together with **no separator at all**
during extraction (`"АннаПетровна"` for what the page prints as "Анна
Петровна"). A corpus-wide check for this exact shape (capital-letter
boundary, no hyphen, no space) found only 3 instances total, confirming
it's rare and distinguishing it clearly from the far more common
*legitimate* hyphenated-compound-first-name pattern ("Іоганъ-Фридрихъ",
"Карлъ-Вильгельмъ" — genuinely one name, correctly left alone). Fixed the
2 Graduates instances (added `patronymic_clean` to `analysis.person_entry`
alongside the existing `first_name_clean`); left the 1 BalletArtists
instance (`Пуни, ЛеонтинаКонстанція`) unfixed since "Констанція" doesn't
have a typical patronymic suffix and is more likely a second first name
than a patronymic — needs individual verification, not assumed.

**Correction to #34 (same day): `ballet_graduates_tenure.csv` had been
writing BalletArtists-sourced dates into `tenure_start_date`, not just
using them as a cross-check.** Caught by explicit instruction that the
field must be blank unless the Theater School Report itself states a
date. The original `balletartists_crossref` source (149 rows) was a
name-plus-plausible-date match against a *different* roster, not
something the Report said — writing it into the same column as the
Report-sourced dates blurred a real distinction between "the source
document states this" and "a same-named person elsewhere has this date."
Regenerated: `tenure_start_date` is now populated only for
`report_per_row` / `report_per_row_exception` / `report_hand_verified`
(222/417 rows); the remaining 195 are blank
(`source='not_stated_in_report'`), with any BalletArtists reference date
moved to the `note` column and explicitly marked "not used." The 26
Report-vs-BalletArtists disagreements (see above) are unaffected by this
correction — those were always Report-sourced rows with the
disagreement flagged, not the other way around.

**Second addendum to #34 (same day): added a `school` column
(St. Petersburg / Moscow), and in the process found and fixed a
drama-department leak plus a third `report_hand_verified` cohort.**

The exact-match drama filter used to build the CSV (`heading_path IN
('Со свидѣтельствами / Ученицы', 'Съ аттестатами / Ученицы')`) only
caught 10 of the 20 rows on `graduates_1890-91_p005` — the same drama
page, but 10 more rows on it carry different heading_path variants
("Ученики", "Ученикъ", "Въ Москвѣ / Съ аттестатами / Ученицы") that the
exact-match filter didn't cover. Confirmed by direct query that this is
the *only* page corpus-wide with any drama-department heading, so the
correct fix is excluding the whole `page_id`, not pattern-matching
`heading_path` strings. **10 drama-department individuals had been
incorrectly included in `ballet_graduates_tenure.csv` all along**
(Кравотынскій, Рыкъ, Усачевъ, Дубынинъ, Бергманъ, Караулова, Любимова,
Лютецкая, Нечаева, Ртищева) — removed. Corrected row count: 407.

`school` was built from `institution`/`heading_path` text
(`heading_path` wins when both are present, since one page's
`institution` field is contaminated by the earlier-documented "Всѣ 15
человѣкъ..." cohort-paragraph misattachment — see `family_name_clean`
note above). The first classifier pass used the substring `"москв"` and
found 0 rows for it — a real bug: "Московское"/"Московская" contain
"моск" but not "москв" (the fifth letter is "о", not "в"). Fixed to
`"моск"`, which correctly classified all but 13 rows (0 remaining
ambiguous "both mentioned" cases once the drama page was also
excluded). Final: 268 St. Petersburg, 139 Moscow.

The 13 unresolved rows (`graduates_1895-96_p003`) turned out to be
another dropped-assignment-paragraph case like the two already in
`report_hand_verified` — confirmed by rendering and reading the actual
page images (`ForUpload_1895-96_TheaterSchoolReport.pdf`, PDF page
indices 2–3). Page 2 is headed "Московское Театральное Училище. /
Балетное отдѣленіе." and states the cohort size ("Окончили курсъ весною
1896 года 13 человѣкъ — 7 ученицъ и 6 учениковъ"); page 3 lists the 13
names under bare "Ученицы:"/"Ученики:" (no institution restated) and
closes with "Всѣ перечисленные окончившіе курсъ ученицы и ученики
опредѣлены на службу, съ 1-го сентября 1896 года, въ Московскую
балетную труппу" — a date the original extraction missed entirely, the
same failure mode as the 1899/1902 cases. Moved these 13 from
`not_stated_in_report` to `report_hand_verified` (now 38 total: 13 from
1902, 12 from 1899, 13 from 1896) with `tenure_start_date='1896-09-01'`,
`troupe_city='Moscow'`, `school='Moscow'`.

Final counts: 407 rows (268 St. Petersburg / 139 Moscow); `source`:
`report_per_row` 187, `report_hand_verified` 38, `not_stated_in_report`
182.

**Third addendum to #34 (same day): completed a full hand-check of
every remaining `not_stated_in_report` page — found a second drama-page
leak and 10 more dropped-assignment-paragraph cohorts.**

Grouped the 182 `not_stated_in_report` rows by page: 12 pages where
*every* row on the page was blank (strong candidates for the same
dropped-paragraph bug already fixed twice), plus 1 page with a mix of
dated and blank rows. Rendered and read all 13 pages directly (plus
neighboring pages where needed) rather than inferring from the pattern.
Two of the PDFs (`ForUpload_1891-92_...`, `ForUpload_1892-93_...`,
`ForUpload_1899-00_...`, `ForUpload_1900-01_...`,
`ForUpload_1905-06_...`) were iCloud-evicted stub files and had to be
downloaded (`brctl download`) before rendering.

While rendering, hit a real methodological snag: several of these PDFs
are pages RG had manually cropped (via each page's PDF crop box) to cut
out drama-department content that shared a page with the ballet list —
the first pass rendered using `page.get_pixmap()`'s default crop box and
so silently reproduced RG's intentional cut, which is correct behavior,
but a few pages genuinely needed the full mediabox checked (with RG's
explicit go-ahead) to confirm whether a ballet-relevant assignment
paragraph sat right at/past that boundary. Re-rendered with
`page.set_cropbox(page.mediabox)` for the affected pages before
re-checking.

Findings:

- **`graduates_1890-91_p006` (8 rows) is a second drama-department page**,
  a direct continuation of `graduates_1890-91_p005`'s numbered "Ученицы"
  list (items 7–9 continue p005's 1–6) plus its own "Ученики" list — its
  own closing paragraph names the Moscow and St. Petersburg *drama*
  troupes, not ballet, and even names several people already known to be
  drama (Бергманъ, Караулова, Любимова, Нечаева) from p005. Excluded
  entirely, same as p005.
- **10 more pages had a genuine dropped assignment paragraph**, all on
  the *same page* as the list (not a following page), confirmed by
  reading the paragraph directly: `graduates_1890-91_p002` (21 rows —
  15 St. Petersburg at 1891-06-01 except Легатъ, individually stated at
  1891-10-01; 6 Moscow at 1891-09-01, consistent with the men's half of
  this same cohort on `p003`, which the extraction *had* parsed
  correctly), `graduates_1891-92_p000` (18 St. Petersburg rows at
  1892-06-01, except Бекъ individually assigned to the Moscow troupe on
  the same date), `graduates_1892-93_p001` (13 more St. Petersburg rows
  at 1893-06-01 — the sentence existed in the data but had only been
  attached to Тихомировъ's own row as its exception clause, never to the
  other 13 rows on the page), `graduates_1898-99_p000` (14 rows,
  1899-06-01), `graduates_1902-03_p000` (14 rows, 1903-06-01),
  `graduates_1905-06_p000` (15 rows, 1906-06-01), `graduates_1906-07_p000`
  (15 rows, 1907-06-01). All moved from `not_stated_in_report` to
  `report_hand_verified`.
- **The remaining 5 pages (64 rows, all Moscow) were confirmed to
  genuinely have no assignment date to recover** — `graduates_1899-00_p001`,
  `graduates_1901-02_p001`, `graduates_1904-05_p001`, and
  `graduates_1905-06_p001` are each immediately followed by a new
  "Драматическіе курсы" section heading with nothing about ballet
  assignment in between; `graduates_1900-01_p001`'s source PDF excerpt
  is only 2 pages long and the list runs to the literal bottom of the
  last page, so if an assignment paragraph exists at all it isn't in
  this particular scan. Left as `not_stated_in_report`, not guessed.

This means the earlier "only 2 of these pages were ever recovered"
caveat in `docs/ballet_graduates.md` is resolved — every remaining
`not_stated_in_report` page has now actually been opened and read, not
inferred from having found some already.

Final counts after this pass: **399 rows** (10 dropped for the second
drama-department page fix; 260 St. Petersburg / 139 Moscow); `source`:
`report_per_row` 187, `report_hand_verified` 148, `not_stated_in_report`
64.

**Fourth addendum to #34 (same day): RG asked directly whether any
drama students remain in the file — verified rather than asserted, and
found one more real bug in the process (not a drama leak).**

Two checks, both logged:

1. Corpus-wide keyword sweep of `raw.person_entry` for
   `entity_type='Graduates'` against `институт`/`heading_path`/
   `tenure_note_text` for "драмат", "аттестат", "свидѣтельств" — the
   only hits anywhere in the corpus are the 17 rows already excluded on
   `p005`/`p006`. Zero hits remain in the final 399-row CSV.
2. Cross-checked which of the 399 rows lack even the word "балет"
   anywhere in their own heading_path/institution/tenure_note_text (95
   rows, on top of pages already hand-verified above) — not proof of a
   problem by itself (a truncated date clause like "съ 1 сентября 1893
   г." legitimately drops "балетную" if that word appeared earlier in
   the sentence than the part the extraction kept), but a worthwhile
   place to look. Read all 4 remaining pages directly
   (`graduates_1892-93_p003`, `graduates_1894-95_p001`,
   `graduates_1895-96_p001`, `graduates_1897-98_p001`). Three were
   confirmed correct, ordinary St. Petersburg ballet pages with a
   truncated date clause. **`graduates_1892-93_p003` (12 rows) had a
   real, separate bug**: its `institution` field reads "Императорское
   С.-Петербургское Театральное Училище" (stale/mislabeled, not this
   page's own heading), but the page itself is headed "Московское
   Театральное Училище / Балетное отдѣленіе" and its closing paragraph
   states "...опредѣлены на службу съ 1-го сентября 1893 г. въ
   Московскую балетную труппу." These 12 rows are genuinely Moscow
   ballet graduates — not drama, but mis-classified by city because the
   `school` classifier trusted a wrong `institution` field with no
   heading_path city signal to override it. Fixed: `school`→`Moscow`,
   `troupe_city`→`Moscow` (the row already had the correct
   `tenure_start_date`, `1893-09-01`, from `report_per_row`).

Net effect on counts: 399 rows unchanged (no rows added/removed this
time), school split corrected to **248 St. Petersburg / 151 Moscow**.
Answer to RG's question: no drama-department rows remain in the file,
confirmed by a corpus-wide keyword sweep plus direct reading of every
page that lacked an explicit ballet-troupe keyword — not just checked
for the original two drama pages.

**Fifth addendum to #34 (same day): RG then asked directly whether
`school` is correct for *every* graduate, not just whether drama leaked
in — found 2 more instances of the same institution-mislabeling bug by
checking exhaustively rather than spot-checking.**

Identified every row where `school` was derived **entirely** from the
`institution` field (i.e. `heading_path` gave no city signal to
cross-check it against) — exactly the failure mode behind the
1892-93_p003 bug above. That was 334 rows across 27 distinct pages.
Read all 27 directly against the scanned PDF (downloading/rendering a
few more season PDFs as needed: 1893-94, 1896-97, 1897-98, 1899-00,
1903-04, 1904-05). 24 of 27 were already correct. Two more had the
identical bug:

- `graduates_1896-97_p003` (12 rows) — `institution` says St.
  Petersburg, but this row's own `tenure_note_text` explicitly says
  "...опредѣлены на службу... въ Московскую балетную труппу." The
  school classifier simply wasn't consulting `tenure_note_text` at all,
  even where it directly states the city.
- `graduates_1898-99_p002` (12 rows) — identical pattern, confirmed
  against the scanned page; this is the same cohort already in
  `report_hand_verified` (`troupe_city`/`tenure_start_date` were already
  correct there, only `school` was wrong).

Both fixed to `school`→Moscow. Rebuilt the classifier's precedence to
`heading_path` → `tenure_note_text` → `institution` (institution is now
truly last-resort) and re-ran the contradiction check corpus-wide: zero
remain (aside from Тихомировъ's one legitimate individual exception,
where `school` genuinely differs from his individually-assigned
`troupe_city` by design — an SPB graduate sent to the Moscow troupe).

Final: 399 rows, `school` split corrected again to **224 St. Petersburg
/ 175 Moscow**.

**Sixth addendum to #34 (same day): cross-checked the 148
`report_hand_verified` rows against BalletArtists** — the original
disagreement cross-check (issue text above) only ever covered the 187
`report_per_row` rows; this extends it to the hand-verified cohorts
added later in the same session. Same method: for each row, look up
same-named BalletArtists records and compare their `start_date_undate`.

122/148 agree exactly, 23 have no BalletArtists record at all (expected
— not every graduate entered service or entered under a form this
dataset captures), 0 genuinely ambiguous (no case with multiple
same-named BalletArtists candidates), and 3 disagree:

- **Бекъ, Константинъ** — Report says 1892-06-01 (assigned to the
  Moscow troupe as an individual exception within an otherwise-SPB
  cohort); BalletArtists says 1892-09-01, identically across all 15
  seasons he appears in that roster. This is the same shape as the
  already-documented Vaganova/1897-98 May-vs-June pattern — a
  consistently-repeated, well-attested gap between two independent
  sources, not a transcription slip on either side. Added as a third
  example to `docs/eval/source_document_anomalies.md`.
- **Тихомировъ, Владиміръ** and **Ивановъ, Александръ** — 6-year and
  10-year gaps respectively, each on only 1-2 BalletArtists seasons, on
  names common enough that a same-named-but-different-person match is
  far likelier than a genuine discrepancy. Flagged as such in the `note`
  column rather than treated as a same-person disagreement.

All three keep the Report's own `tenure_start_date` (per the standing
rule); only `note` was appended. No row counts changed.

**Seventh addendum to #34 (same day): identity-linked all 399 graduates
to their fuller BalletArtists career records**, per RG's explicit
request to do this "carefully, not matching false positives" — the task
this whole session's cross-checking work had deliberately deferred (see
"What's still open" in `docs/ballet_graduates.md`, pre-existing).

Built an independent conservative linker (not `entities.person_link`'s
existing tier1-key auto-merge, which already produced one confirmed
false merge — issue #30). For each graduate, found same-named
BalletArtists rows and clustered them by date proximity (≤65 days apart
treated as print-run noise, same person) with an extra merge pass for
same-`entry_id` multi-period records (discovered mid-build: a single
`entry_id` can carry two separate service periods — a real departure and
re-enrollment, not two people; found via Легатъ, Иванъ). For the 335
graduates with a Report-stated date, that date is the primary
disambiguation anchor (a candidate within 130 days = linked; none in
range = `unlikely_match`; more than one in range = `ambiguous`); the 64
without one fall back to requiring a single dominant, city-consistent
candidate.

Two early design mistakes, caught and fixed before finalizing rather
than shipped:

1. First pass used a flat "any distinct date = different person" rule,
   which wrongly flagged confirmed-same-person cases like Мосолова
   (11 seasons say "1 сентября 1893", 2 say "5 сентября 1893") as
   ambiguous. Checked both source pages directly — both print exactly
   what they show, a genuine cross-edition inconsistency in the
   historical record, not an OCR error (RG asked this directly; verified
   rather than assumed). Fixed with proximity clustering.
2. A looser "majority vote wins" version of that fix then over-merged:
   some clusters had a majority date years away from a lone outlier
   (e.g. one stray record off by 6–16 years), which isn't the same
   "print variant" phenomenon as Мосолова's 4-day wobble at all. Fixed
   by anchoring against each graduate's own independently-established
   Report date wherever one exists, rather than trusting BalletArtists'
   internal vote alone.

Final: **342 linked, 46 no BalletArtists record, 9 ambiguous (2+
same-named people with no way to tell which, if any, is this graduate —
not linked), 2 unlikely_match** (same two individual cases already
flagged in the sixth addendum). New columns:
`balletartists_link_status`, `balletartists_seasons_attested`,
`balletartists_link_note`. No existing columns or row count changed.

## 35. BalletArtists/Musicians ordinal-suffix ("1-й"/"2-я") sometimes landed as the entire `first_name`, corrupting `first_name`/`patronymic` for 115 rows corpus-wide

**Status: fixed.** Found while investigating why RG's "how many
newly-employed dancers didn't graduate from either Theater School"
question was producing an implausibly high, RG-flagged-as-suspicious
figure (see `docs/ballet_graduates.md`'s identity-linking section, #34,
for the graduate-side half of this same investigation).

The normal convention throughout this corpus, confirmed everywhere else,
is that a positional ordinal distinguishing two same-surname people (most
often siblings) is appended to `family_name` as a trailing token — e.g.
"Крылова 2-я", "Бурмистрова 1-я". On 115 rows (77 BalletArtists, 38
Musicians; zero in any other entity_type, confirmed by direct query),
the ordinal instead landed as the *entire* `first_name` value, and the
real first name got shoved into `patronymic` — sometimes alone ("Дмитрій"),
sometimes fused with the real patronymic as one run-together string
("Дмитрій Спиридоновичъ", both shapes confirmed).

Quantified the real cost via one concrete case: "Литавкинъ" (2-3 real
siblings, "1-й"/"2-й"/an unnumbered third) fragments into **9 distinct
raw `(family_name, first_name, patronymic)` triples** across different
season pages purely from this bug — directly inflating any distinct-
person count taken from the raw fields, which is exactly what surfaced
it (RG's skepticism about a "910 newly-employed dancers" figure that
turned out to be significantly duplicate-inflated).

Fixed in `pipeline/build_duckdb.py`'s `build_analysis_schema()`,
extending the same `family_name_clean`/`first_name_clean`/
`patronymic_clean` CASE expressions already built for the unrelated
Graduates comma-format bug (issue #27/#34) with a new branch: detects
`first_name` matching `^[0-9IVXІ]+-(й|я|е)$`, reassembles
`family_name_clean` (append the ordinal), `first_name_clean` (patronymic's
first word), and `patronymic_clean` (whatever follows that word, `NULL`
when nothing did — not invented). Verified: Литавкинъ's 9 triples
collapse to the correct 3 identities. `raw.person_entry` is untouched,
per the schema's standing rule.

**Effect on the "newly-employed, non-graduate dancers" question**:
distinct BalletArtists identities in the 1890-91–1906-07 report-coverage
window: 910 → 869 (dedup effect, modest — most affected people were
still duplicated under the same broken format across many seasons, not
scattered as true singletons). Distinct-identities matched to a
Graduates name: 320 → 396 (+76 — the fix also repairs the actual
strings being compared, a bigger effect than dedup alone). Unmatched:
590/910 (65%) → 473/869 (54%). A real, meaningful improvement, but most
of the original gap is still unexplained by this bug specifically —
remaining causes already confirmed distinctly (cross-edition spelling
variance; at least one genuine source misprint, Nijinsky's own graduation
listing prints "Наусинскій" instead of "Нижинскій" in the 1906-07
Theater School Report) would need the same page-by-page verification
already done for the 399 curated ballet graduates, at roughly 2x the
scale (869 candidates) and in the opposite direction. Not attempted in
this pass — see `docs/query_log.md` for the exact before/after queries.

## 36. Full BalletArtists name-field audit: three more ordinal-misplacement shapes, a dropped surname, and Latin-homoglyph corruption — all fixed

**Status: fixed.** RG paused the broader "how many newly-employed dancers
didn't graduate" question after issue #35 and asked instead for a
complete audit: "make sure there are only real names in the first name,
patronymic, and surname fields" for `entity_type='BalletArtists'`.

Systematic sweep of `raw.person_entry` where `entity_type='BalletArtists'`
(7,674 rows) for non-name content in `family_name`/`first_name`/
`patronymic`: keyword scan (role headings, resignation notes, cross-
references — all zero hits, unlike TheaterSchoolStaff's #26/#28/#33), then
structural checks (digits, Latin letters, blank fields, unusually long
values). Found and fixed, all in `pipeline/build_duckdb.py`'s
`build_analysis_schema()` (extending the existing `_clean` columns),
scoped to `entity_type='BalletArtists'` only (the only entity_type
individually verified this pass — the identical-shaped bugs are confirmed
present in Musicians/TheaterSchoolStaff/Administrators too by query, not
fixed here):

- **Pattern B** (20 rows): `first_name` holds `"ordinal, RealFirstName"`
  run together (e.g. `"1-я, Анна"`), `patronymic` intact. Same underlying
  bug as issue #35's Pattern A, a different manifestation shape.
- **Pattern C** (54 rows, on exactly 2 pages —
  `balletartists_1893-94_SP_p002`, `balletartists_1905-06_SP_p002`):
  `first_name` holds `"FirstName Patronymic"` run together as two words,
  `patronymic` blank. Detected by requiring the second word to end in a
  real patronymic suffix (-на/-вна/-ична/-вичъ/-евичъ/-ичъ), avoiding any
  false split of a genuine two-word entry.
- **Pattern D** (9 rows): the ordinal landed in `patronymic` instead of
  `family_name` (e.g. the Мендесъ sisters, "Анжелика"/"Джульетта", each
  `patronymic="1-я"`/`"2-я"`).
- **A dropped surname** (1 row): `balletartists_1901-02_SP_p001__e018`
  had `family_name="Карлотта"` (a first name, not a surname),
  `first_name`/`patronymic` both blank. Confirmed against the scanned
  page (`ForUpload_1901-02_Spisok_BalletArtistsSP.pdf`, p.73, an
  unnumbered guest-artist entry between #33 and #34): "**Замбелли,
  Карлотта** (съ 1 октября по 1 декабря 1901 г.)" — Carlotta Zambelli, a
  real guest ballerina engaged briefly Oct–Dec 1901. Hand-fixed as a
  single instance.
- **Latin-homoglyph corruption** (24 rows: 17 family_name, 2 first_name,
  5 patronymic): a stray Latin lookalike character substituted into an
  otherwise-Cyrillic word (e.g. "Милютинa" for "Милютина", "Iосифъ" for
  "Іосифъ", "Никifoровна" for "Никифоровна"). Fixed via a `translate()`
  single-character swap (a/c/e/o/p/x/y/i/v/f and uppercase, mapped to
  their Cyrillic lookalikes), confirmed safe by testing it resolves every
  case to a form independently attested elsewhere in the corpus. Three
  rows had multi-character garbling `translate()` can't fix
  character-by-character ("Гавликowsкій", "Спрышиńskaя", "Гrekова 1-я/2-я")
  — each individually confirmed against a correctly-spelled match for the
  same person elsewhere in BalletArtists (matching first_name+patronymic,
  or for Грекова, matching ordinal+first_name+patronymic across 8 other
  seasons) and hand-fixed. A fourth case initially left unresolved
  (`balletartists_1893-94_SP_p005__e002`, "Тииstrова" after the safe
  single-character swaps) turned out, once the actual page was checked,
  to have no complexity at all: `ForUpload_1893-94_Spisok_BalletArtistsSP.pdf`
  p.62, entry #135 plainly prints "**Тистрова**, Марія Ѳедоровна (съ 10
  декабря 1873 г.)" — an entirely ordinary Cyrillic surname; the
  extraction had simply inserted spurious Latin letters into it for no
  apparent reason. Hand-fixed. **Zero remaining Latin-letter-contaminated
  rows in `analysis.person_entry` for `entity_type='BalletArtists'`**,
  verified directly after the rebuild.

**Confirmed not bugs, left as-is**: ~63 genuinely blank patronymics
(mostly foreign guest artists with no Russian-style patronymic —
Bréanza, Zambelli, Legnani, etc. — a real source feature, same
conclusion already reached for Graduates in issue #34); several
`entity_type='BalletArtists'` rows on `graduates_1901-02_MSK_*` pages
with first_name/patronymic entirely blank — confirmed against the
scanned page (`ForUpload_1901-02_Spisok_BalletArtistsMoscow.pdf` p.112)
that several entries genuinely print as bare "Surname." with nothing
else before the performance stats that specific year — a real, if
inconsistent, editorial choice in that one edition, not an extraction
gap.

**One confirmed non-person phantom entry — now excluded from
`research.person`**: `balletartists_1899-00_SP_p000__e008` has
`family_name` = "Прикомандированъ къ Монтіровочной части для исполненія
обязанностей помощника машиниста Маріинскаго театра" (a job-duty
description, not a name at all). Same category as the five IDs already
in `build_research_model.py`'s `NON_PERSON_IDS` list (issues #26/#28/#30).
Looked up its `entities.person` UUID via `entities.person_link`
(read-only — did NOT re-run `build_entities.py`'s tier1 matching, which
this session's earlier work flagged as unsafe without first checking for
stale manual corrections): `37dd8b11-7b83-4cb0-9d86-f5f34e611859`, a
clean, isolated record with exactly this one entry_id linked to it (not
merged with any real person's data). Added to `NON_PERSON_IDS` and
rebuilt `research.person`/`research.person_appearance` (safe, both are
pure derivations, no other changes). Confirmed absent from both tables
after the rebuild.

**Not attempted this pass** (flagged for later, per RG's explicit scope
of "just Ballet Artist entities" for now): the identical Pattern-C shape
confirmed present in Musicians (149 rows), TheaterSchoolStaff (84 rows),
and Administrators (11 rows).

**Addendum to #36 (same day): the two "genuine spelling-variance" cases
above were wrong — both turned out to be the same ъ/ь OCR misread, not
real variance, and are now fixed.** RG asked directly whether "Джулъетта"/
"Мендесь" were OCR or source. Checked three of the five instances against
their scanned pages (`ForUpload_1906-07_Spisok_BalletArtistsMoscow.pdf`
p.52 #52; `ForUpload_1897-98_Spisok_BalletArtistsMoscow.pdf` p.94 #60;
`ForUpload_1903-04_Spisok_BalletArtistsMoscow.pdf` p.106 #53) — all three
unambiguously print the standard spelling ("Мендесъ" with ъ, "Джульетта"
with ь). A hard-sign/soft-sign confusion, a well-known visually-similar
Cyrillic pair, not a real inconsistency. Fixed all 5 rows (2 family_name,
3 first_name) via hardcoded overrides in `build_duckdb.py`, rebuilt,
confirmed zero remaining.

**Second addendum to #36 (same day): `Пуни, ЛеонтинаКонстанція` resolved.**
RG supplied the key context — this dancer's brother is on the same
rosters as "Пуни, Николай **Цезаревичъ**" ("son of Cesare"), confirming
the family is composer Cesare Pugni's. Checked the scanned page
(`ForUpload_1905-06_Spisok_BalletArtistsSP.pdf` p.18 #80): prints "Пуни,
**Леонтина - Констанція**" — a genuine hyphenated compound first name
(the same convention as "Іоганъ-Фридрихъ" elsewhere in the corpus), not
first_name+patronymic, and no patronymic at all (consistent with every
other foreign-origin artist already confirmed in this corpus). The
hyphen was mangled three different ways across her 5 attested seasons.
Fixed all 5 rows: `first_name_clean` = "Леонтина-Констанція",
`patronymic_clean` = NULL.

With both addenda applied, **every item flagged as open in #36's
original writeup is now resolved** except the cross-entity-type
Pattern-C extension (Musicians/TheaterSchoolStaff/Administrators),
which remains explicitly out of scope.

## 37. Follow-up BalletArtists sweep beyond the three name fields: a fourth ordinal-misplacement shape, and a real shared date-parser gap

**Status: fixed (name/date fixes); entity-linking audit paused mid-execution, not yet applied.**

While answering RG's question "is there any further issues in the raw
ballet artists data I need to address," swept fields beyond
family_name/first_name/patronymic (already fully audited in #36):

- **`rank_or_title` ordinal misplacement (24 rows)**: same underlying
  bug as #36's Patterns A/B/D, a fourth manifestation — the ordinal
  suffix landed in `rank_or_title` instead of `family_name`, with
  family_name/first_name/patronymic otherwise complete and correct
  (e.g. "Грачевская"/"Марія"/"Ивановна", rank_or_title="1-я" instead of
  family_name="Грачевская 1-я"). Fixed in `build_duckdb.py`
  (`family_name_clean` gains a new WHEN branch), rebuilt, verified.
- **Shared date-parser gap, `pipeline/schemas/dates.py`**: 49
  BalletArtists rows had a `start_date_text` sentence that failed to
  parse despite being otherwise legible. Two real, fixable causes,
  confirmed corpus-wide (not BalletArtists-specific — the parser is a
  shared utility already fixed once this project for the hyphenated-
  ordinal-day bug):
  - **"юня" for "іюня"** (June missing its leading "і") — the dominant
    cause (~38 of 49 rows here; 54 instances of the text pattern
    corpus-wide). Added "юн" as an explicit alternate month stem (can't
    collide with any other month, none start with ю).
  - **A stray combining accent mark** ("дека́бря" for "декабря") — now
    stripped via NFD-decompose + drop Unicode category Mn before
    matching, safe because pre-reform Russian running text never
    legitimately carries a combining accent.
  Re-ran `parse_and_validate.py` against the JSON already on disk (per
  CLAUDE.md — this is the intended way to propagate a `dates.py` fix,
  not a hand-edit of `raw.*`) and reloaded `raw.*`. Result: 49 → 7
  remaining unparseable BalletArtists rows, all genuinely different
  residual causes checked and left alone on purpose — 4 have no day
  number in the source at all (parser correctly returns None by design,
  nothing to invent), plus one each of a day-corrupted-to-a-letter
  ("і февраля" for probably "1 февраля"), a differently-garbled month
  ("ікня"), and the already-day-less "октрября" typo. None revisited
  this pass — each is a single instance, lower value than the two fixed
  patterns.

**Also investigated, confirmed NOT bugs — informational fields, not name
fields**: `institution` for BalletArtists doesn't reliably indicate city
at all (both St. Petersburg and Moscow pages carry the same generic
document-title strings like "Ежегодникъ Императорскихъ театровъ" —
unlike Graduates, where `institution` occasionally *almost* worked as a
city signal before failing; here it never was one). `heading_path`
sometimes reads "Управляющій Училищемъ" ("Director of the School") on
rows that are clearly real dancers (e.g. the already-known Литавкинъ
brothers) — a stale/non-structural breadcrumb, not a phantom-person
issue (the actual name fields are correct on every one of these rows).
Neither affects name-field cleanliness; `raw.source_pages.city` remains
the reliable field for city, already used throughout this project.

**Paused, not yet applied**: a systematic audit of whether
`entities.person`'s automatic tier1-key matching correctly merges each
real BalletArtists dancer's season-by-season raw rows into one
`person_id` (as opposed to the field-content question #36/#37 above,
which is now resolved). Found 89 surname+ordinal+first_name clusters
where 2+ `person_id`s exist for what might be the same real person
(182 person_id records total, out of 1,291 active BalletArtists-only
person records) — 46 of those clusters (92 person_ids) differ only by a
blank vs. one non-blank patronymic (safe to merge — a blank patronymic
never contradicts a specific one), of which 44 have no season-overlap
risk and 1 more (Пономаревъ) was confirmed safe via direct raw-entry
comparison; 1 (Павлова 2-я, Анна) was excluded from the safe set because
the two candidate records are in *different cities* the same season,
and the ordinal ("2-я") looks to be assigned independently per city —
likely two different women, not one. The other 43 clusters (90
person_ids) have 2+ genuinely different patronymics and need individual
judgment — some are probably the same already-established
misread/homoglyph patterns from #36/#37 (e.g. one instance,
"Никifoровна"/"Никифоровна", is literally the exact homoglyph pattern
already fixed there), others show season-overlap between the differing-
patronymic variants (a real red flag for two different people, e.g.
Поливановъ, Чудиновъ), and at least one (Новикова, Екатерина,
"Александровна" vs "Дмитріевна") is already independently confirmed
via the earlier Graduates-linking work to be two genuinely different
real women. A merge-execution script was written (repointing
`entities.person_link`, tombstoning losers via
`superseded_by_person_id`, recomputing survivors'
`first_attested_season`/`last_attested_season` — the same mechanism this
project already uses for its existing 836 superseded records) but
**was not run** — paused before execution at RG's request. Resume point:
`/private/tmp/claude-502/.../scratchpad/execute_safe_merges.py` has the
44-cluster safe-merge logic ready to run (needs Павлова/Пономаревъ
handling reconciled per the notes above); the 43 ambiguous clusters
still need triage (some resolvable immediately via the already-confirmed
misread patterns, the rest need individual page checks or a documented
decision to leave separate).

## 38. `entities.person` identity-linking audit for BalletArtists — 287 fragmented identities merged

**Status: applied.** Follow-up to #37's paused audit: whether the
existing automatic tier1-key matcher correctly merges each real
BalletArtists dancer's season-by-season raw rows into one `person_id`.
RG: "We need to chase it, so let's fix it now."

Two systematic, targeted merge passes over the 1,291 active BalletArtists-
only `entities.person` records (not a rebuild — `entities.person`/
`entities.person_link` were updated in place via the project's existing
merge mechanism: repoint `person_link` rows to the survivor, recompute
its `first_attested_season`/`last_attested_season`, tombstone the loser
via `superseded_by_person_id`, same as the 836 pre-existing superseded
records):

**Pass 1 — blank vs. one real patronymic (family+ordinal+first_name
match, patronymic blank on one side).** 89 candidate clusters (182
person_ids). 46 clusters (92 person_ids) had no season+city overlap
between fragments — safe by construction, since a blank patronymic never
contradicts a specific one. Two borderline cases checked individually
against raw data before deciding: **Пономаревъ, Сергѣй** (blank fragment
fully contained within the dated one's own season, same city — merged)
and **Павлова 2-я, Анна** (blank fragment in a *different city*, same
season, as the established St. Petersburg dancer — **left separate**;
the "2-я" ordinal is very likely assigned independently per city, so
this is probably two different women, not one). **45 merges applied.**

**Pass 2 — same family+first_name+patronymic, only the ordinal_suffix
differs.** RG confirmed the key fact that made this pass possible:
*"Ordinals can change over the seasons because it depends on how many
people of the same name were employed"* — i.e. "1-я"/"2-я" is a
per-season positional label among currently-listed same-surname
colleagues, not a stable personal identifier, so a person legitimately
gaining, losing, or changing their own ordinal across seasons is
expected, not suspicious. 201 candidate clusters. 199 had no
season+city overlap. The 2 that did (**Ивановъ, Иванъ Николаевичъ**,
3-way; **Пономаревъ, Сергѣй Ивановичъ**, revisited from Pass 1) were
re-examined in light of RG's confirmation and merged too — the
"overlap" is exactly the expected signature of a positional label, not
evidence of two people, once the patronymic itself is confirmed
identical throughout. **229 merges applied.**

**10 more merges applied individually**, each checked against raw
season/city data (and in a few cases the actual scanned page) before
deciding, not defaulted to either merge or separate:

- **Феоктистова/Ѳедорова, [Анна/Екатерина]**: "Никifoровна"/"Никіфоровна"
  — the exact homoglyph corruption pattern already confirmed in #36/#37
  (i/f → и/ф). Merged.
- **Нарышкина, Александра**: "Нико- норовна" — a mid-word line-break
  artifact reconstructing "Никаноровна". Merged.
- **Алексѣевъ, Александръ**: one fragment's `patronymic` was literally
  "2-й" — the ordinal-misplacement bug (#36 Pattern D) landing in a
  *different* record than the one it got fixed on at the analysis layer;
  treated as non-informative noise, not a real conflicting patronymic,
  and merged with the "Алексѣевичъ" (line-break-mangled as
  "Але-ксѣевичъ") record.
- **Мендесъ, Джульетта**: patronymic "2-я" (same ordinal-bug-in-
  patronymic pattern) and a blank fragment, both merged into the
  "Іосифовна" record — independently confirmed correct by directly
  reading the scanned page during #36's work.
- **Медалинскій, Александръ**: "Ульяновичъ" appears in exactly 1 of 11
  seasons (1904-05), bracketed on both sides by "Юліановичъ" — the same
  overwhelming-majority-with-bracketed-outlier pattern already confirmed
  safe multiple times this session (Мосолова, Печатниковъ, Орловъ).
  Merged.
- **Петипа, Надежда**: "Васильевна" appears in exactly 1 of 13 seasons
  (1904-05), bracketed by "Маріусовна" on both sides — same pattern.
  Merged. (Marius Petipa's real daughter, per the corpus's own internal
  consistency — not an external genealogy claim.)
- **Кякштъ, Лидія**: "Юрьевна" only in her first attested season
  (1902-03), then "Георгіевна" consistently for the next 4 seasons with
  no gap. Merged.
- **Ивановъ 2-й, Константинъ**: a blank-patronymic fragment fully
  contained within the "Ефремовичъ" (Moscow) record's own season range
  — merged into it. The cluster's third variant, "Константиновичъ", is
  a *St. Petersburg*-only, fully parallel and overlapping career — see
  below, correctly left separate.

**Left separate — checked directly and confirmed (or strongly
indicated) to be genuinely different real people, not merged:**

- **Ивановъ, Константинъ** (no ordinal) / **Симонова, Антонина** /
  **Ѳедорова, Марія**: in all three cases, checking the raw data by
  city revealed two *fully parallel, simultaneously-overlapping
  careers in different cities* — e.g. Ивановъ "Ефремовичъ" only ever
  appears in Moscow (1890-1905), "Константиновичъ" only ever in St.
  Petersburg (1899-1907), overlapping for 6 years. Two different men
  who happen to share a common surname+first name, not one man's
  patronymic wobbling.
- **Михайлова, Александра**: checking the raw data showed "Карповна"
  and "Михайловна" both attested as *separate simultaneous entries in
  the same city, the same season*, for at least 4 consecutive years
  (1890-91–1893-94) — definitively two different women, the shared
  patronymic-matches-surname-root ("Михайловна"/"Михайлова") a
  coincidence.
- **Новикова, Екатерина** (both the no-ordinal and "2-я" clusters):
  already independently confirmed via the earlier Graduates-linking
  work (docs/ballet_graduates.md) — "Александровна" matches the
  1891-92 graduate's own Report-stated date, "Дмитріевна" matches the
  1899-00 graduate's — two different real women.
- **16 remaining clusters** (Калишевская, Тимофѣева, another Ѳедорова
  Марія variant, Поливановъ, Чудиновъ, Голубина, Александровъ,
  Петрова, Васильева, Поспѣхинъ, Трефилова, Аѳанасьева, a third
  Ѳедорова Екатерина variant, Чичелева, and both Левинсонъ sisters):
  genuinely different-root patronymics (not homoglyphs, not line-break
  artifacts, not the confirmed ordinal-noise patterns above), most with
  real season-overlap between the variants. Left separate by default,
  per the project's standing rule against guessing through name-
  collision ambiguity — resolving these with confidence would need
  individual scanned-page checks, not attempted this pass.

**Result**: 287 merges total (836 → 1,123 superseded records
corpus-wide). Active BalletArtists-only `entities.person` records:
1,291 → 1,004 (a 22% reduction in spurious fragmentation).
`entities.person_link` row count unchanged throughout (21,174) —
confirms no appearance data was lost, only correctly regrouped.
Rebuilt `research.person`/`research.person_appearance` (pure
derivations, safe to rebuild): `research.person` 3,517 → 3,230 rows
(exactly the 287-row reduction), `research.person_appearance` unchanged
at 21,158 rows.

## 39. `entities.person.canonical_family_name` sometimes picked a minority/garbled raw spelling instead of the dominant one — 64 BalletArtists records relabeled

**Status: fixed.** Found while verifying #38's merges: spot-checking
"Мосолова, Вѣра Владиміровна" (the exact person independently
page-verified twice earlier this session, #36's "1 сентября"/"5
сентября" print-variance case) showed her `entities.person` record's
`canonical_family_name` as **"Молодова"** — a spelling I never once saw
printed. Checking her 15 linked raw entries: 13 say "Мосолова", 1 says
"Мосалова" (a single-letter vowel slip), 1 says "Молодова" (the more
garbled one) — the canonicalization had picked the *minority, more
corrupted* spelling to display, not the dominant, page-verified one.
This also explains why she wasn't already caught by #38's Pass 1: her
one remaining un-merged fragment (a lone 1892-93 blank-patronymic
entry, `2b048dbf...`) genuinely has `family_name='Мосолова'`, which
doesn't match "Молодова" — the wrong canonical label was silently
hiding a real, findable merge.

Checked how widespread this is: **64 active BalletArtists-only
`entities.person` records** (of ~1,000) have a `canonical_family_name`
that differs from the ≥60%-majority raw spelling among their own linked
entries — e.g. "Цармань" shown where 14/18 entries say "Царманъ",
"Лошилинъ" shown where 6/8 say "Лащилинъ". Fixed all 64 via the same
majority-vote logic already used elsewhere this session:
`canonical_family_name`/`display_name` reset to whichever raw spelling
appears most often among that person's own entries. Мосолова's own
fragment (`2b048dbf`) merged in by hand once the label was corrected.

Re-ran the #38 cluster audit after this fix (to check whether correcting
labels revealed more mergeable fragments, the same way it did for
Мосолова): 2 new candidate clusters surfaced (Кандауровъ, Павелъ;
Смирнова, Марія) — both checked and left separate, same reasoning as
#38's other "different roots, no external corroboration" cases.

Rebuilt `research.person` after this pass: 3,230 → 3,229 (the one
additional Мосолова merge). `canonical_family_name` label corrections
alone don't change row counts, only display quality.

**Not systematically checked**: whether the same canonical-label
mismatch affects `canonical_first_name`/`canonical_patronymic` (only
`family_name` was audited this pass), or whether it affects entity
types beyond BalletArtists.

## 40. Post-#38 over-merge risk audit: date-gap check across all 287 merged identities

**Status: in progress.** After #38/#39's merges, ran a systematic
skepticism pass rather than trusting the merge logic: for every
same-(family, first, patronymic) merged survivor, pulled all distinct
`start_date_undate` values from linked "regular roster" entries (excluding
staff-role headings like "Помощники режиссера"/"Балетмейстеры" — see #38's
Ивановъ/Пономаревъ addendum) and looked for internal disagreement.

Of 391 reconstructed merged pairs: 339 (87%) agree exactly. **51 have 2+
distinct dates; 25 of those have a gap exceeding 3 years** — the highest
over-merge-risk subset. Two have been individually checked against the
actual scanned pages so far:

- **Симонова, Марія Петровна** (50.0y gap: "1837" vs "1887," 21 other
  entries across 17 editions all say 1887) — checked
  `ForUpload_1890-91_Spisok_BalletArtistsMoscow.pdf` p.102 #92: the page
  genuinely prints "1837." Not an OCR error — a one-digit (3/8) printer's
  error in this single 1890-91 edition only, silently corrected in every
  subsequent edition. A ~70-year active tenure isn't physically plausible,
  so this is one person, not two; the merge is correct. The raw verbatim
  "1837" is left as-is (per the project's verbatim-preservation principle)
  — this is a source error, not a transcription error, so nothing to fix
  in `raw`.
- **Тихоміровъ, Владиміръ Михайловичъ** (6.3y gap: "1892-06-01" vs
  "1898-09-01") — checked `ForUpload_1904-05_Spisok_BalletArtistsSP.pdf`
  p.25 #80-81: confirms two brothers, Тихоміровъ 1-й Сергѣй Михайловичъ
  and Тихоміровъ 2-й Владиміръ Михайловичъ, both "съ 1 іюня 1892 г." Pulling
  every raw `Тихом*` entry (60 rows) shows both brothers appearing together
  every SP season 1892-93 through 1907-08 (with the "1-й"/"2-й" ordinal
  swapping which brother holds it partway through — another confirmed
  instance of the ordinal-is-positional pattern), both promoted from plain
  ballet artist to "Управляющій Училищемъ" together starting exactly
  1898-09-01. This is one person's two career milestones (dancer 1892,
  promoted co-administrator 1898) — the same dual dancer+staff-role
  pattern as Ивановъ/Пономаревъ. The merge is correct.

  This corrects a separate finding from this session's earlier
  graduates-linking work (`docs/query_log.md`, 2026-08-20), which flagged
  this same person as `unlikely_match` on a Report-stated tenure date. That
  check matched on exact raw `family_name` string equality, which silently
  excludes every entry printed with the "1-й"/"2-й" ordinal attached to the
  family name — roughly half this person's actual career (1892-93 through
  1902-03) — so it only ever saw the post-1898 years and flagged a gap that
  doesn't exist once the full record is visible. That `unlikely_match` flag
  is now known to be a false negative of its own matching method, not
  independent evidence against this merge.

**Update (continued same day):** the original gap-check that produced "25
of 391 pairs with gap>3y" had a bug — it counted a single raw `entry_id`'s
multiple legitimate `person_entry_service` periods (a documented
departure+re-enrollment, same convention as Легатъ) as if they were
disagreement between two merged records. Rebuilt the check to group by
`entry_id` first (MIN date per entry_id), compare only ACROSS distinct
entry_ids. Corrected pool: **90 survivors with genuinely disagreeing dates
across distinct entry_ids, 37 with a gap exceeding 3 years** (not 25).

Went through ~20 of the highest-risk names directly against scanned pages
(zoomed crops, not just raw text — necessary after Старостина showed a
digit misread is possible in either direction, see below):

- **Confirmed genuine one-edition print anomalies** (page-verified, not two
  people): Симонова Марія Петровна (1837/1887), Сапожникова Анна Іосифовна
  (1835/1885), Анкудинова Ольга Евгеніевна (1837/1887, different edition
  than Симонова — this is a recurring defect across multiple print runs,
  not one bad batch), Рахмановъ Сергѣй Павловичъ (the 1905-06 and 1907-08
  editions both print his brother Викторъ's "1903" date onto his own line —
  confirmed on both pages, not an extraction issue), Козловъ 1-й Федоръ
  Михайловичъ (1904-05 edition alone prints "1905" against 9 other
  editions' "1900"/"1901" — confirmed on the page; NOT his brother
  Алексѣй's date bleeding over as first suspected, Федоръ's own line
  genuinely reads 1905 that one year).
- **Confirmed genuine multi-period service**, this time via explicit
  "по ... и съ ..." phrasing directly on the page (not inferred from
  structure): Евлановъ Николай Павловичъ ("съ 23 августа 1884 г. по 3
  декабря 1887 г. и съ 1 ноября 1890 г." — left service, rejoined), Ивановъ
  3-й Василій Еремѣевичъ, Тихоміровъ 2-й Алексѣй Дмитріевичъ — all
  page-confirmed on `ForUpload_1904-05_Spisok_BalletArtistsMoscow.pdf` p.58
  and `ForUpload_1906-07_Spisok_BalletArtistsMoscow.pdf` p.57.
- **Confirmed genuine pipeline extraction bug, fixed**: Старостина Анна
  Ильинична (`balletartists_1890-91_SP_p005__e020`) — raw extraction read
  "1830"; the actual page (`ForUpload_1890-91_Spisok_BalletArtistsSP.pdf`
  p.63, checked at 800dpi zoom) prints "1880," matching every other
  edition. This is the opposite failure direction from the print-anomaly
  cases above — here the SOURCE was right and OUR extraction was wrong.
  Corrected in the raw `.raw.json` (`tenure_note_text` and
  `service_periods[0].start_date_text`), re-ran `parse_and_validate.py`,
  reloaded `raw`/`analysis`. This is why every case in this list was
  checked against an actual zoomed page rather than trusted either way —
  the raw extraction and the "what does the page actually say" question
  are independent failure modes, confirmed to go wrong in both directions
  within this same batch.
- **Confirmed structurally safe via same-entry_id dual-date pairing** (the
  source itself prints an early and a later date together on the identical
  entry_id across multiple editions — the same signature as the
  page-confirmed multi-period cases just above, so treated as reliable
  without an individual page check): Тихоміровъ Владиміръ Михайловичъ
  (also independently page-confirmed above), Голубинъ Николай Ивановичъ,
  Бершадскій Николай Александровичъ, Бѣлоусовъ Филиппъ Ивановичъ, Брыкинъ
  Дмитрій Константиновичъ, Ѳедоровъ Павелъ Викторовичъ, Цалиссонъ Полина
  Викторовна, Пановъ Александръ Викторовичъ.
- **Still genuinely open:** Поливановъ Василій Егоровичъ — the 1907-08
  edition prints "1 сентября 1889 г." in full (not a digit slip — an
  entirely different day/month/year) against 15 other editions' "23
  декабря 1868 г." Page-confirmed as printed; no multi-period phrasing on
  the page. This is the highest remaining risk in the whole pool. Савицкій
  Михаилъ Ивановичъ — only 2 data points total, both confirmed accurately
  transcribed on their pages (1906-07: 1900; 1907-08: 1906), no third data
  point or multi-period phrasing to resolve the conflict either way.
- **Not yet individually page-checked**, pattern-consistent with the
  "single-edition outlier against a clear majority" shape confirmed six
  times above but NOT treated as resolved per this session's no-guessing
  standard: Дорина, Барышистовъ, Черниковъ, Пахомова, Бекефъ, Кустереръ,
  Кузнецовъ (Владиміръ variant), Сампелевъ, Барашъ, Солнцевъ, Петипа Марія,
  Тивольская (a genuine 4-vs-3-edition split, not a single outlier),
  Леонтьевъ (oscillating across editions), Иванова Надежда (only 1 raw
  entry found under this exact name so far; the paired record producing
  the flagged gap not yet located).

**Update (continued same day): all remaining names in the 37-name pool now
page-checked.** The earlier "single-edition outlier against a clear
majority, likely a print anomaly" framing turned out to be wrong roughly
half the time — checking each individually (rather than extrapolating from
the pattern) surfaced genuine pipeline bugs at a rate too high to have
safely assumed away.

**Six more extraction bugs found and fixed** (raw data said one year, the
actual scanned page reads another): Барышистовъ Александръ Ивановичъ (raw
"1890" -> page "1899"), Пахомова Ольга Сергѣевна (raw "1883" -> page
"1893"), Кустереръ Альбертина Альбертовна (raw "1883" -> page "1888"),
Кузнецовъ Владиміръ Николаевичъ (raw "1893" -> page "1898"), Сампелевъ
Александръ Николаевичъ (raw "1863" -> page "1868"), Барашъ Людмила
Павловна (raw "1901" -> page "1905"). All six corrected in their
`.raw.json` files, `parse_and_validate.py` re-run, `raw`/`analysis`
reloaded, each spot-verified in the DB. **Total this session: 7 confirmed
extraction bugs** (these six plus Старостина above).

**Confirmed genuine print anomalies** (page matches raw exactly, a real
one-edition printing error, not two people): Дорина Антонина Тимоѳеевна
(1900 vs 1890), Черниковъ Дмитрій Абрамовичъ (1897 vs 1887, final
edition), Бекефи Альфредъ Ѳедоровичъ (1876 vs 1883, penultimate edition —
the same page also independently confirms Аслинъ's dual répétiteur role:
"Онъ же и репетиторъ балета съ 12 декабря 1903 г."), Петипа Марія
Маріусовна (1879 vs 1875, first edition only, 16-edition majority),
Солнцевъ Прохоръ Павловичъ (1876 confirmed for the one edition checked;
only 3 data points total, low stakes either way).

**Two more genuinely open cases**, joining Поливановъ and Савицкій — both
sides directly page-confirmed as accurately transcribed, no way to resolve
from internal evidence: Тивольская Елена Николаевна (a clean, sustained
switch — "1877" page-confirmed across 4 consecutive editions, then "1887"
page-confirmed across the next 3, not a single outlier), Леонтьевъ Леонидъ
Сергѣевичъ ("1903" and "1894" both page-confirmed, genuinely alternating
across 5 editions with no discernible pattern).

**Retracted:** the "Иванова Надежда Сергѣевна ordinal-misplacement bug"
noted here originally was a false alarm — found by querying `raw` directly
(which is correctly untouched/verbatim) rather than checking what the
pipeline actually produces downstream. `analysis.person_entry` already
resolves `balletartists_1901-02_MSK_p001__e021` to
`family_name_clean='Иванова 4-я'`/`first_name_clean='Надежда'`, and both
`entities.person.display_name` and the published `research.person.display_name`
already correctly read "Иванова 4-я, Надежда Сергѣевна". Nothing to fix.
See `docs/query_log.md`, 2026-08-21, "Correction: ... false alarm".

**Final tally of the 37-name gap>3y pool:** 7 pipeline extraction bugs
found and fixed; 8 confirmed genuine print anomalies (not over-merges); 6+
confirmed genuine multi-period service (not over-merges — three via
explicit "по...и съ..." page phrasing, several more via the structural
same-entry_id dual-date signature); 4 genuinely open cases unresolvable
from internal evidence (Поливановъ, Савицкій, Тивольская, Леонтьевъ).
Поливановъ remains the single highest-concern case in the pool — the only
one where the deviating value is a full day/month/year mismatch rather
than a plausible single-digit slip or a two-milestone story.

## 41. `entities.person.canonical_first_name`/`canonical_patronymic` lagged behind the analysis layer's name-cleaning across ALL entity types — 253 records corrected, one additional merge found

**Status: fixed.** Followed up on #39's open question ("does this also
affect first_name/patronymic, or other entity types?"). Root cause:
`build_person_tier1()` (`pipeline/build_entities.py`) computes
`entities.person`'s canonical fields with its own ordinal-extraction regex
(`_BARE_ORDINAL_RE`, digit-only) run against **raw**, un-cleaned name
fields — not the already-cleaned `analysis.person_entry_clean` columns.
That regex is weaker than the one the analysis layer grew during this
session's #35-#37 fixes (which also handles Roman/Cyrillic-numeral
ordinals), so `entities.person`'s canonical fields silently missed every
ordinal-placement and name-splitting fix made downstream — on top of
carrying #39's original minority-spelling problem into first_name/
patronymic too, not just family_name.

A full re-run of `build_entities.py` would fix this at the root but is
unsafe: correcting the regex changes `tier1_key` for affected clusters,
which mints new `person_id`s and would orphan this session's 287+ Tier-2
merges (they reference the old UUIDs). Fixed surgically instead —
recomputed canonical fields directly from `analysis.person_entry_clean`
via majority vote over each survivor's current linked entries, same method
as #39, split into two independent, ordinal-presence-preserving checks
(ordinals are legitimately season-dependent, established this session —
never majority-voted). Two bugs in the fix script itself were caught and
corrected before applying: independent per-field voting produced
Frankenstein combinations on correlated fields (fixed by voting the
(first, patronymic) pair jointly), and empty vote pools left old garbage
values in place instead of clearing them (fixed). A safety guard was added
after finding a third case: never accept first_name == family_name (a
duplication artifact, not a real name).

**BalletArtists**: 111 of 1003 active persons corrected (20 ordinal
comma-leaks, 91 spelling/pairing mismatches) — every spot-checked fix
matched an already-established correction from earlier this session that
just hadn't reached `entities.person` (Zambelli, Гавликовскій, Грекова,
Спрышинская, Тистрова, Пуни/Леонтина-Констанція). Bonus: fixing Пуни
revealed she still existed as two separate `entities.person` records (1
entry + 4 entries, sequential seasons, no overlap) — merged.

**Other entity types**: Graduates 0/400 (clean), Administrators 19/243,
Musicians 92/984 (mostly consistent multi-edition transliteration fixes
for foreign surnames — German/Czech names spelled differently across
editions), ProductionTeam 18/236, TheaterSchoolStaff 13/266.

**Total: 253 canonical-field corrections + 1 merge**, all verified
propagated through `build_research_model.py` to the published
`research.person.display_name`. `research.person` 3229 -> 3228 (the one
merge); `research.person_appearance` unchanged at 21158 (no data loss).

**Update (continued same day): the code path itself is now fixed.**
`build_person_tier1` (`pipeline/build_entities.py`) previously computed
`entities.person`'s canonical fields from its own weaker, digit-only
ordinal regex run against raw text — meaning any FUTURE full rebuild would
have silently regressed everything fixed above. Fixed properly:

- Widened the ordinal regex to match the analysis layer's
  (`[0-9IVXІ]+-(?:й|я|е)`), and switched the function to source from
  `analysis.person_entry_clean` instead of re-deriving a second, weaker
  cleanup pass against raw text.
- **The actual reconciliation strategy**: person_id continuity no longer
  depends on a recomputed `tier1_key` string happening to still match its
  old value (the root cause — any matching-logic improvement changes
  affected rows' key, misses the old string, mints a new UUID, and orphans
  every merge ever made against the old one, including this session's
  287+ direct merges that never went through the pipeline's own Tier 2).
  Reuse is now keyed on ENTRY MEMBERSHIP via `entities.person_link`, which
  is always fully resolved to each entry's current living survivor
  (`_repoint_all_superseded`'s guarantee) — ground truth no future logic
  change can invalidate. Tombstoned rows are now explicitly carried
  forward unchanged every rebuild (CLAUDE.md's "tombstone, never delete"),
  since the entry-based design would otherwise have nothing to
  reconstruct them from.
- Added `_refresh_canonical_fields`: recomputes every live person's display
  fields from their FULL current entry set after every merge pass. This
  closes a second, related gap the fix itself surfaced: canonical fields
  were previously computed once at Tier-1 formation and never revisited,
  so a person whose original tiny cluster included a 1-vote garbled
  spelling kept displaying it forever, even after Tier 2 later merged in
  17 more entries agreeing on the real spelling.
- Caught and fixed a bug in the fix itself before it reached production: an
  early version voted the full (family, ordinal, first, patronymic) tuple
  jointly, which is wrong whenever family-name noise and patronymic noise
  vary independently on different entries (produced "Єедорова" — a
  homoglyph nobody's entry actually had — from a case where 3/4 agreed on
  the family spelling and 2/4 agreed on the patronymic separately). Fixed
  to vote (family, ordinal) and (first, patronymic) as two independent
  pairs, matching the method already validated by hand earlier in this
  issue.

Verified via dry run against a disposable DB copy (twice, once per code
fix) before ever touching production: 0 entries lost, 0 tombstones lost or
retargeted, person_link count unchanged. 22 entries changed person_id
assignment — all genuine improvements (Tier 2's existing shared-tenure-date
mechanism catching real duplicate clusters among records from the manual
fix above). A full corpus-wide sweep after the fix found 0 remaining
canonical-field mismatches anywhere, any entity type. Applied to
production: `research.person` 3228 -> 3221 (7 new legitimate merges),
`research.person_appearance` unchanged at 21158.

## 42. Follow-up on #40's 4 remaining open date conflicts — 2 resolved, 1 new (harmless) variance found, 2 still open

**Status: partially resolved.** Checked every remaining avenue for the 4
cases #40 left open (full raw record across all fields, cross-reference
against all 6 entity types, existing Wikidata links).

- **Поливановъ, Василій Егоровичъ** — while re-checking, found (at the
  user's prompting) that the patronymic itself alternates "Егоровичъ"
  (14/16 editions) vs "Ивановичъ" (1903-04, 1905-06 only, with 1904-05
  correctly reverting between them) — a previously unflagged variance,
  raising a reasonable "is this a second person?" question. Checked both
  scanned pages directly: genuinely printed both times, not an extraction
  error. But the start date is identical ("23 декабря 1868") in all 17
  editions regardless of which patronymic prints, with continuous roster
  position/role/credits and no departure note — two different people
  would not plausibly alternate one numbered slot year-to-year sharing an
  identical tenure date. Read as a recurring compositor's substitution of
  the far more common "Иванович" for the rarer "Егорович," independent of
  the separate 1907-08 date anomaly. Not a second person. The core
  1868-vs-1889 date conflict itself remains unresolved (majority favors
  1868; 1889 stays an unexplained single-edition anomaly) — no cross-type
  or Wikidata corroboration exists for this person.
- **Савицкій, Михаилъ Ивановичъ** — RESOLVED. Found a `Graduates` record
  (`graduates_1905-06_p001__e011`) showing him still enrolled in the
  ballet division's student roster in 1905-06 — independent evidence
  favoring "1 августа 1906 г." (the later BalletArtists date) as his real
  company-artist start, with "1900" more likely his school-entry date
  (same convention as Дмитриева/Голубинъ). One continuous person.
- **Тивольская, Елена Николаевна** and **Леонтьевъ, Леонидъ Сергѣевичъ** —
  no cross-reference in any other entity type, no Wikidata link, no new
  evidence found. Remain genuinely open exactly as in #40.

**Updated tally**: of the original 4 open cases, 2 resolved (Савицкій via
independent cross-reference; Поливановъ's over-merge question specifically
settled, though its date conflict itself stays unexplained), 2 still
genuinely open with no further avenue currently available (Тивольская,
Леонтьевъ).

## 43. Name-field audit extended from BalletArtists to the other 5 entity types — Pattern C (244 rows) and Pattern D (1 row) fixed corpus-wide

**Status: fixed.** #36/#37 established Patterns B-E and Latin-homoglyph
corruption for BalletArtists but explicitly left the question open for
other entity types — one comment in `build_duckdb.py` even flagged Pattern
C as "confirmed" present in Musicians/TheaterSchoolStaff/Administrators
without ever acting on it. Checked all 5 remaining entity types directly
against `raw.person_entry` for every known pattern shape.

**Confirmed genuinely absent elsewhere** (not just unverified — zero rows,
including a broadened Latin-letter sweep): Pattern B (ordinal+comma in
first_name), Pattern E (ordinal in rank_or_title), Latin-homoglyph
corruption. These stay BalletArtists-only.

**Pattern C is real and substantial**: 149 rows in Musicians, 11 in
Administrators, 84 in TheaterSchoolStaff — 244 total, more than 4x the
original 54-row BalletArtists count. Sample-verified identical shape
(first_name = "FirstName Patronymic" run together as two words, patronymic
blank) — e.g. an Administrators row that now correctly reads "Дягилевъ,
Сергѣй Павловичъ" (Sergei Diaghilev, previously unsplit).

**Pattern D found once more**: Musicians' Эйхенвальдъ sisters (Ида/Надежда)
— the ordinal landed in patronymic on one row, exactly the BalletArtists
Мендесъ-sisters shape. Confirmed via the raw corpus alone (the sisters'
other rows already spell the ordinal split out unambiguously across
multiple editions) — no page check needed. ProductionTeam and Graduates
confirmed clean on every pattern.

Extended `build_duckdb.py`'s Pattern C/D `entity_type` scoping to
`('BalletArtists', 'Musicians', 'Administrators', 'TheaterSchoolStaff')`
in all 4 affected CASE branches. Rebuilt `analysis.person_entry` (0
remaining unfixed rows, verified). Propagated via `build_entities.py`
(dry-run verified first): 0 entries lost, 0 tombstones lost, 2 new
legitimate Tier-2 merges from previously-fragmented clusters now correctly
recognized. Applied to production + `build_research_model.py`:
`research.person` 3221 -> 3219, `research.person_appearance` unchanged at
21158 (zero data loss).

**Found in passing, not yet investigated**: Diaghilev ("Дягилевъ, Сергѣй
Павловичъ") still exists as 2 separate `research.person` records — could
be two genuinely distinct administrative appointments, or a real
un-merged duplicate. Not chased down this pass.

## 44. 233 duplicate persons found and merged corpus-wide — a new permanent pipeline safety net, `merge_duplicate_persons()`

**Status: fixed.** Found while checking a curiosity flagged in passing at
the end of #43: Diaghilev ("Дягилевъ, Сергѣй Павловичъ") existed as two
separate `entities.person` records with matching role, rank, and exact
start date. Investigated the full scope rather than hand-fixing the one
instance.

Root cause: the 2026-08-21 person_id-continuity fix (#41) deliberately
freezes an existing person's entry membership across reruns (that's what
makes person_id survive a matching-logic improvement) — but that also
means two people correctly assigned different person_ids under an earlier,
dirtier version of the data never get reunited on their own once a
downstream fix (like #43's Pattern C extension) makes their names
identical. Tier 2's own candidate search doesn't catch this either — it
explicitly skips exact (edit-distance-0) matches, written on the
assumption Tier 1 always catches those.

Quantified the scope directly rather than assuming: an initial check using
`tier1_key` (which includes `ordinal_suffix`) found 185 pairs — corrected
after RG pointed out ordinal is a per-season positional label, not a
stable identifier (the same fact behind #38 Pass 2), so requiring it to
match too structurally undercounts. Redone on family+first+patronymic
alone: **278 duplicate-name groups, 294 extra person records**.

Implemented as a permanent pipeline function (`merge_duplicate_persons()`
in `build_entities.py`, wired into `main()`'s merge loop), not a one-off
script — this closes the gap for every future rebuild, not just today's
data. RG specified the exact standard directly: matching names AND a
matching start date together are sufficient corroboration; anything less
needs individual care. Three required gates, all must pass:
1. `entity_type` must match across every member of the group.
2. No season/city overlap between any two members (the same conflict check
   #38 used throughout).
3. At least one exact shared `start_date_undate` somewhere in the group —
   the same bar Tier 2's `apply_tenure_corroboration` already requires.

Dry-run verified before touching production (converged after 2
iterations): 233 duplicates merged into 222 survivors, 0 entries lost, 0
tombstones lost, `person_link` count unchanged. 38 cross-entity-type + 8
season/city-overlap + 10 no-shared-date groups correctly held back —
spot-checked and confirmed genuinely ambiguous, not silently dropped.
Applied to production + `build_research_model.py`: `research.person`
3219 -> 2986 (zero data loss on `research.person_appearance`, unchanged at
21158).

**Not yet done**: the 56 held-back groups (38 cross-entity-type + 8
overlap + 10 no-shared-date) haven't been individually reviewed. Several
of the cross-entity-type ones look like plausible same-person-different-
role matches (e.g. "Мендесъ, Іосифъ" across BalletArtists+
TheaterSchoolStaff sharing an exact date) worth a deliberate look.

**Correction to #44 (2026-08-24): gate 1 had a real bug, fixed, and the
numbers above are stale.** Gate 1 originally required *exact set
equality* of `entity_type` across every member of a group
(`len({etypes}) > 1` → skip) rather than checking for a non-empty
*intersection*. This wrongly excluded any case where one record's
entity_type set was a strict subset of another's despite sharing a type
and an exact date (e.g. `{BalletArtists}` vs `{BalletArtists,
Graduates}}`) — found by spot-checking the held-back cases: 25 of the 38
"cross-entity-type" holds turned out to share a type after all. Fixed to
`common_types = frozenset.intersection(*etypes_per_member); if not
common_types: skip`. Re-verified via the same dry-run-diff discipline (0
entries/tombstones lost) before applying. Corrected result: **27
duplicates merged into 24 survivors** (not 233/222 — the 233 count above
was itself from a run before this fix), holding back **11
cross-entity-type + 11 season/city-overlap + 10 no-shared-date = 32**.
`research.person_appearance` unchanged at 21158 throughout. See #45 for
the follow-up review of these 32.

## 45. Individual review of #44's 32 held-back duplicate-person groups — 4 hand-merged with hard date evidence, cross-entity-type gate confirmed correct-as-designed

**Status: partially done.** #44's `merge_duplicate_persons()` deliberately
holds back any group that fails one of its 3 gates for individual human
review rather than guessing. Worked through the 11 cross-entity-type
holds first (RG: "let's work on this carefully").

**Жукова, Вѣра Васильевна** (BalletArtists 1890-91 only, TheaterSchoolStaff
teaching post starting 1901) — her BalletArtists record actually shows she
left service 1 March 1891, one season in, not a 32-year span as first
framed. Real gap is 10 years (retired dancer → later teacher), plausible
but no positive date link. RG: flag for further research, not merged.

**Степанова, Лидія Петровна** — Graduates says 1898-05-01, BalletArtists
says 1898-06-01, 9/9 editions. Checked which is more common in the
professional record: June 1 is unanimous across every BalletArtists
printing; May 1 appears only once, in the Graduates row. Read as two
different, both-correct milestones (school release vs. employment start),
not a conflict — same pattern as the Graduates-timing cases below. RG
agreed to merge.

**Погожевъ, Владиміръ Петровичъ** and **Пчельниковъ, Павелъ Михайловичъ**
(each: an Administrators post + a TheaterSchoolStaff honorary-council seat
with no date field). RG asked whether names match and timing is
reasonable. Names identical in both entity types for each (one spelling
variant, "Владимиръ" for "Владиміръ" once). Timing is *concurrent*, not
sequential as first framed — the council seat runs in parallel with the
substantive administrative post the whole time, consistent with an ex
officio arrangement. RG agreed to merge both.

**7 "Graduates-timing" cases** (Кочетовская, Уракова, Ивановъ Василій,
Иванова Надежда, Павлова Анна, Павлова Евгенія, Смирновъ Викторъ) — RG
asked what season each graduated. Queried `raw.person_entry`/
`source_pages` directly: in all 7, the Graduates listing's edition year is
the exact academic year whose end lines up with the printed career-start
date (e.g. graduated 1890-91 → career starts Sept 1891), zero
counterexamples, consistent with a normal graduation-to-employment
interval. While investigating **Кочетовская** specifically, RG pointed
out the Report gives her an exact date after the full list, missed
because the list spans a page break — confirmed directly against the
scan (`ForUpload_1890-91_TheaterSchoolReport.pdf` pp. 255-256): the
trailing sentence "Всѣ 12 человѣкъ съ 1 сентября 1891 г. опредѣлены..."
covers 6 Moscow girls on p.255 (incl. Кочетовская) plus 6 Moscow boys on
p.256, but the extraction only attached it to the boys (same-page
entries), leaving the girls undated.

**Discovered this was already solved, more rigorously, in an earlier
session (2026-08-20) and never surfaced**: `docs/ballet_graduates.md` +
`outputs/full_run/ballet_graduates_tenure.csv` (referenced from #34's
7 addenda) already hand-verified all 399 ballet-department Graduates
against the actual scans, including the exact same 8 pages / cohorts this
session was independently re-deriving. Abandoned an in-progress duplicate
fix to `pipeline/parse_and_validate.py` (a hand-typed dict of the same 8
pages, cleanly reverted, zero trace left) in favor of using the real
thing. Cross-checked all 7 names against it: **4 have a Report-stated
exact date matching BalletArtists precisely** (Кочетовская 1891-09-01,
Уракова 1891-06-01, Ивановъ Василій 1896-09-01, Павлова Анна 1899-06-01);
**3 are genuinely `not_stated_in_report`** (Иванова Надежда, Павлова
Евгенія, Смирновъ Викторъ) — all three are Moscow cohorts in years RG
confirmed the Yearbook editors didn't receive the Moscow school's data in
time for printing, a real historical publishing gap, not a digitization
or extraction failure.

**Wired the CSV's dates into the actual pipeline** (RG: "do the full
pipeline fix"), since it had only ever lived as a reference document —
`raw.person_entry_service`/`entities`/`research` still showed these
people as undated before this. Moved the CSV to `docs/ballet_graduates_tenure.csv`
(git-tracked; `outputs/` is disposable) and added
`pipeline/parse_and_validate.py`'s `_repair_graduates_tenure()`: loads
`entry_id -> tenure_start_date` from the CSV (only the 136 of 335 dated
rows the raw JSON doesn't already have — the other 199 were already
correct, e.g. rows where only `school` had been wrong), renders the ISO
date back to a printed-style Russian phrase so it still round-trips
through `parse_russian_date()`, and backfills any entry with no existing
`service_periods`. Verified via the standard dry-run-diff (0
entries lost/gained, exactly 136 new `person_entry_service` rows, all
`graduates_*`) before applying to production and rebuilding
`entities`/`research`. `research.person_appearance` unchanged at 21158
throughout.

**Confirmed, not assumed, that this date fix alone would not
auto-resolve any of the 4 cases via `merge_duplicate_persons()`**: reran
it on production — 0 duplicates merged, same 11/11/10 held back as
before. Traced why: gate 1 requires a non-empty *intersection* of
`entity_type` between the two records, and a Graduates-only record vs. a
BalletArtists-only record are disjoint sets by construction — that
transition is *always* cross-entity-type even when it's unambiguously
the same person. This is the gate working as designed, not a bug to loosen;
individual review is the correct mechanism for this specific
Graduates→career pattern, not a rule change.

**Hand-merged the 4 confirmed cases** (Кочетовская, Уракова, Ивановъ
Василій, Павлова Анна) using the same tombstone convention as issue #38
(`superseded_by_person_id`, `_repoint_all_superseded`,
`_refresh_canonical_fields`), dry-run verified first. `entities.person`
live count 2965 → 2961; `research.person` 2959 → 2955 (4, as expected);
`research.person_appearance` unchanged at 21158.

**New finding surfaced while verifying Павлова Анна, not yet acted on**:
a third `entities.person` record for "Павлова, Анна" (no patronymic,
single entry `balletartists_1907-08_MSK_p003__e021`) shares the exact
same date (1899-06-01) as the just-merged Павлова Анна Матвѣевна, but is
tagged Moscow instead of her usual SP. Its raw fields read
`family_name='Павлова', first_name='2-я', patronymic='Анна'` — the
familiar ordinal-in-first-name corruption (#35-37's pattern), with the
real patronymic (Матвѣевна) dropped and city likely also wrong as a
result. Very likely the same person's 1907-08 season double-counted
under a mis-parsed second entry, not a genuine third Pavlova — flagged
for a follow-up fix, not merged this session.

**Addendum (same day): executed the 3 remaining queued merges** —
Степанова, Погожевъ, Пчельниковъ. Степанова Лидія Петровна merged
straightforwardly (Graduates `1898-05-01` + BalletArtists 9-edition
`1898-06-01` → one 10-entry record). Погожевъ and Пчельниковъ turned out
to already be *partially* auto-merged by `merge_duplicate_persons()`
during the date-fix rebuild above (a 39/40-entry `{Administrators,
TheaterSchoolStaff}` combo record already existed for each) — what
remained was a small residual 4-entry `TheaterSchoolStaff`-only split per
person, all 4 entries reading "Почетные члены конференціи" under the
same institution with `first_name` holding the unsplit "Владиміръ
Петровичъ"/"Павелъ Михайловичъ" string (the same name-concatenation
extraction pattern documented for Graduates, here landing in
TheaterSchoolStaff on 4 particular editions instead). Confirmed same
person/role via heading_path + institution, merged the split in. Dry-run
verified first (exactly -3 live persons, 0 change to `raw.person_entry`);
applied to production, rebuilt `research`
(`research.person` 2955 → 2952, `research.person_appearance` unchanged
at 21158). Both survivors now show 43/44 entries under
`{Administrators, TheaterSchoolStaff}`.

**Second addendum (same day): the season/city-overlap group (9 groups,
not 11 — 2 had already resolved above) individually reviewed and
resolved.** Replicated `merge_duplicate_persons()`'s exact gate logic
against production to re-derive the current list rather than trust a
stale count. Two patterns:

- **5 groups: the same name-concatenation bug** already fixed for
  Погожевъ/Пчельниковъ (first+patronymic unsplit on a handful of
  editions) — Писнячевскій Владиміръ Порфирьевичъ, Фарскій Альбертъ
  Карловичъ, Золотаренко Павелъ Петровичъ (2 fragments), Дебогорій-
  Мокріевичъ Порфирій Андреевичъ, and Франке Ѳедоръ Юліевичъ (clarinet
  variant only — the "Франке 2-й" waldhorn record in the same 3-way
  group is a genuinely different sibling, correctly left separate: same
  first name/patronymic, different instrument, different exact date).
  RG approved this whole batch; merged.
- **4 groups: one real person listed twice per edition** (an honors
  list + a post list, or two institutional rosters), not two
  colleagues — Ивановъ Левъ Ивановичъ (the historical choreographer,
  "second ballet master," identical role text/date, split only by
  whether "1-й" printed), Рюминъ Иванъ Ивановичъ (senior court
  official/school director, identical rank text/date across heavy
  season overlap), Павловъ Михаилъ Львовичъ (single stray entry
  matching the main record's date exactly), and Кулле Альфредъ
  Ѳедоровичъ. RG asked to see the actual scan for Кулле specifically
  before deciding (a database-level `heading_path` said "Управляющій
  Училищемъ" / School Director, which would have made this a real
  conflict) — downloaded the iCloud-stub PDF
  (`ForUpload_1902-03_Spisok_OrchestraSP.pdf`) and rendered pp. 83 and
  86 directly. Found a reciprocal transfer note, not a conflict: p.86
  (Mikhailovsky orchestra) reads "...Тромбонъ. Переведенъ въ оркестръ
  Маріинскаго театра съ 1 сентября 1902 г." (transferred TO Mariinsky);
  p.83 (main SP orchestra) reads "...Тромбонъ. Переведенъ изъ оркестра
  Михайловскаго театра съ 1 сентября 1902 г." (transferred FROM
  Mikhailovsky) — same trombonist, same 1891 start date, each roster
  citing the other institution for the same 1902 transfer date. The
  "Управляющій Училищемъ" text does not appear anywhere on the actual
  page -- confirmed as a stray extraction misattachment, unrelated to
  Kulle. RG approved the merge once shown this.

All 9 merges dry-run verified first (0 change to `raw.person_entry`),
applied to production, `research` rebuilt after each batch.
`entities.person` live count 2958 → 2948 across this whole review
(Золотаренко absorbed 2 fragments, counted as -2 alone).
`research.person_appearance` unchanged at 21158 throughout.

**Third addendum (same day): the no-shared-date group (10 groups, not
the earlier "8" estimate) individually reviewed — 6 merged, 4 deferred.**
Re-derived the current list the same way as the season/city-overlap
pass above (replicating the gate logic against live production, not
trusting the earlier count). Found:

- **5 more instances of the Погожевъ/Пчельниковъ name-concatenation
  bug**, all under the identical "Почетные члены конференціи" heading:
  Григоровичъ Дмитрій Васильевичъ, Климченко Андроникъ Михайловичъ,
  Маннь Ипполитъ Александровичъ, Потѣхинъ Алексѣй Антиповичъ, Іогансонъ
  Христіанъ Петровичъ — the 11th through 15th confirmed instance of this
  bug this session. RG approved the batch; merged.
- **Конскій, Григорій Яковлевичъ** (Moscow violinist) — RG asked to see
  the actual entries before deciding. Checked both scans directly
  (`ForUpload_1890-91_Spisok_OrchestraMoscow.pdf` p.107,
  `ForUpload_1891-92_Spisok_OrchestraMoscow.pdf` p.85): both genuinely
  print a different decade for his start date ("28 іюля 1862" vs "28
  іюля 1852"), consecutive seasons, same city/instrument/role, and the
  1891-92 printing is explicitly his closing record ("Оставилъ службу 1
  августа 1892 г."). Read as one person's final two seasons with a
  compositor's digit slip in one printing -- same shape as the
  already-documented Мосолова 4-day variant (this issue's 7th
  addendum), both printings genuine. RG approved; merged.
- **4 groups deferred to a to-do list, not merged** (RG: "put the others
  in the to-do list for later") — Васильева Анна, Ильина Елена, Новикова
  Екатерина, Симонова Антонина, all Graduates with no patronymic
  printed. Each pair has a *different* season AND a *different* exact
  date -- no positive evidence pointing to one person rather than two
  different graduates who happen to share a common name. Needs an
  explicit decision from RG on how (or whether) to resolve common-name
  Graduates collisions with no patronymic to disambiguate; not
  guessed at here.

All 6 merges dry-run verified first (0 change to `raw.person_entry`),
applied to production, `research` rebuilt (`research.person`
2942 → 2936). `research.person_appearance` unchanged at 21158.

**This closes out the entire #44 held-back review** (cross-entity-type,
season/city-overlap, and no-shared-date groups all individually
adjudicated) except the 4 deferred Graduates pairs above.

**Still open / to-do list**:
1. The 4 deferred Graduates common-name pairs (Васильева Анна, Ильина
   Елена, Новикова Екатерина, Симонова Антонина) — needs RG's decision
   on a general policy for common-name/no-patronymic collisions.
2. Жукова, Вѣра Васильевна (flagged for further research, not merged).
3. The Павлова "2-я" mis-parse found while merging Павлова Анна
   Матвѣевна (a `first_name='2-я'`/`patronymic='Анна'` ordinal-
   corruption artifact, likely double-counting her 1907-08 season under
   the wrong city) — needs a fix, not yet done.
4. Confirmed unrecoverable, no action possible: Иванова Надежда, Павлова
   Евгенія, Смирновъ Викторъ (all `not_stated_in_report` — a genuine
   Moscow reporting gap in the original yearbook, not an extraction
   failure).

## 46. Institution/department/position accuracy audit started — 2 confirmed extraction misattachments fixed, broader normalization survey still open

**Status: partially done**, prompted by RG wanting to verify people's
departments/areas/positions are accurate.

Surveyed `institution` (the closest existing field to "which theater/
department") across all 6 Spiski entity types via
`research.person_appearance`. It's structurally noisy, not a clean
categorical field: 18-69 distinct values per entity type, mixing document
titles ("Списокъ личнаго состава театральнаго управленія"), bare city
names ("МОСКВА."), real theater names with spelling drift ("Маріинскій"
vs "Мариинскій"; "Большой театръ" vs "Большой театр." -- the latter
missing the pre-reform ъ, not yet checked against a scan to confirm
genuine vs. extraction-dropped), and in two cases outright misattached
text from elsewhere on the page. `heading_path`/`role_normalized`
(position) likely has the same shape of problem (145-252 distinct values
per entity type) but wasn't surveyed in the same depth yet.

**Structural finding**: there is currently no clean "which theater does
this person belong to" field anywhere in the published data.
`entities.theater` (6 hand-seeded canonical theaters) is wired only to
`research.event`'s performance venue, never to person records at all --
building an equivalent for people, if wanted, is new work, not a bug fix.

**Two confirmed misattachments fixed** (both checked against the actual
scans, not guessed):

1. **25 BalletArtists rows** (`balletartists_1903-04_MSK_p002`) had a
   repertoire credit-list sitting in `institution`. Confirmed against
   `ForUpload_1903-04_Spisok_BalletArtistsMoscow.pdf` p.106: it's the tail
   half of Другашева, Марія's own `credit_summary_text` (the previous
   page's entry 25), cut off mid-sentence by the page break and misread
   as a page header. Fixed: appended the missing text back to her entry;
   blanked `institution` on the 25 contaminated entries (no real header
   exists on that page — verified against the scan, not assumed).
2. **1 ProductionTeam row** (`productionteam_1895-96_p001__e007`,
   Ковалевскій, Ѳедоръ Ѳедоровичъ) had his own name+date duplicated into
   both `institution` and `heading_path`. Confirmed against
   `ForUpload_1895-96_Spisok_ProductionTeam.pdf` p.108: he's listed under
   "Михайловскій театръ. / Помощникъ машиниста.", directly below
   Ашитковъ (that theater's machinist). Fixed both fields to match.

Implemented as `pipeline/parse_and_validate.py`'s new
`_repair_misattachments()` (a documented, page-keyed patch table,
`_MISATTACHMENT_FIXES` — same pattern as `_repair_graduates_tenure`),
dry-run verified (0 row-count change, exactly 3 entries touched across 2
pages) before applying to production and rebuilding
`analysis`/`research`. `research.person`/`research.person_appearance`
unchanged (2936 / 21158) -- text-only fixes, no entity/date changes.

**Addendum (same day): stepped back and looked at `institution`/
`heading_path` together across all 6 entity types (not just institution
alone) before deciding on a theater-canonical design.** Found the
theater-level signal varies genuinely by entity type, not uniformly:
TheaterSchoolStaff/Graduates carry no theater info at all beyond the
school's own city (`institution` already cleanly SP-vs-Moscow);
BalletArtists' `heading_path` is role/status only ("Артисты,"
"Учащіяся балетнаго класса"), never a building; Musicians reliably
names a specific orchestra ("Оркестръ Михайловскаго театра," "...
Александринскаго театра," "...Малаго театра"); Administrators/
ProductionTeam are a genuine mix of theater-specific and city-wide
roles. **RG concluded no `theater_canonical` field is needed at all**
given how uneven the underlying signal is — a uniform field would
misrepresent several entity types. Not built.

**Second addendum (same day): the "Отдѣль"/"Отдѣлъ" spelling bug fixed**
(RG: "let's just fix the spelling bug for now"). 130 ProductionTeam
rows across 6 seasons had "Отдѣль декораціонный" (soft sign) instead of
"Отдѣлъ декораціонный" (hard sign) in `heading_path` — confirmed a
genuine one-character extraction misreading against the scan
(`ForUpload_1890-91_Spisok_ProductionTeam.pdf` p.111 reads "Отдѣлъ
декораціонный."), not a printed variant. "Отдѣль" never appears in
`institution` and never as any other phrase corpus-wide, so a
word-boundary regex fix was safe to apply universally. Implemented as
`pipeline/parse_and_validate.py`'s new `_repair_department_spelling()`.
Dry-run verified (0 row-count change, exactly 130 entries fixed, 0
remaining afterward); applied to production, `analysis`/`research`
rebuilt (`research.person`/`research.person_appearance` unchanged at
2936 / 21158).

**Still open**: a proper audit of `heading_path`/`role_normalized`
(position/department) for further duplicate-spelling noise beyond this
one confirmed case (145-252 distinct `role_normalized` values per
entity type, not yet surveyed in depth).

**Third addendum (2026-08-27): театръ/театр. orthography question
resolved — extraction slip, confirmed against the scan, fixed
corpus-wide.** `institution`/`heading_path` had "Малый театр."/"Большой
театр." (missing pre-reform ъ) at 31 entries across 3 `ProductionTeam`
pages (1894-95, 1895-96, 1897-98). Checked directly against
`ForUpload_1894-95_Spisok_ProductionTeam.pdf` p.93
(`productionteam_1894-95_p003`): the same page extracts both "Малый
театр." (3 rows) and "Малый театръ" (10 rows) for what is, on the actual
printed page, a single subheader reading "Малый театръ." with the hard
sign every time — a same-page contradiction that rules out a genuine
printed variant and confirms this is the model dropping the ъ
inconsistently while reading the identical header repeatedly down the
page. Fixed via a new `pipeline/parse_and_validate.py` function,
`_repair_teatr_spelling()` (`_HARD_SIGN_TYPO_RE`, `\b(Малый|Большой)
театр\.` → `\1 театръ.`), same pattern as `_repair_department_spelling()`
above. Dry-run verified against `outputs/full_run/raw` first (31 entries,
3 pages, exactly matching the query-time count) before applying.
Re-ran `parse_and_validate.py` + `build_duckdb.py` (raw/analysis) +
`build_research_model.py` (research) against production
(`outputs/full_run/imperial_theaters.duckdb`, backed up first to
`imperial_theaters.duckdb.bak_pre_teatr_fix`); did not re-run
`build_entities.py`/`link_wikidata.py` since `institution`/`heading_path`
aren't identity-linking fields and `entities.person_link`'s `entry_id`
keys are stable across an `analysis.person_entry` rebuild. Verified 0
remaining `театр.` instances in `research.person_appearance`
post-rebuild; `research.person`/`research.person_appearance` row counts
unchanged at 2936/21158, confirming a pure text fix with no entries
added, dropped, or re-merged.

**Fourth addendum (2026-08-27): Маріинскій/Мариинскій drift checked --
split into two unrelated findings, one fixed, one deliberately left
open as its own issue (#52).** Surveyed all `institution`/`heading_path`
values matching "Мариинск" (modern и, 50 rows total) against "Маріинск"
(pre-reform і, 603 rows -- the overwhelming majority, as expected).

*Fixed*: 18 scattered rows, all the nominative "Мариинскій театръ" form,
across 6 `ProductionTeam` pages (1898-99, 1902-03, 1903-04 x2, 1904-05,
1905-06). Confirmed against the scan on `productionteam_1903-04_p001`
(`ForUpload_1903-04_Spisok_ProductionTeam.pdf` p.119): every subheader on
that page reads "Маріинскій театръ", yet 8 of that page's own entries
(Бергеръ, Бекетовъ, Калиновъ, Щеголевъ, Семирадзкій, Иманъ, etc. -- all
independently confirmed present on the scan) extracted `institution` as
"Мариинскій" -- same extraction-slip mechanism as the театръ/театр. fix
above. Fixed via a new `_repair_mariinsky_spelling()`
(`\bМариинскій\b` → `Маріинскій`), deliberately scoped to the nominative
case only so it wouldn't touch the different, still-open issue below.
Dry-run verified (18 entries, 6 pages, exact match) before applying to
production; re-ran `parse_and_validate.py` + `build_duckdb.py` +
`build_research_model.py`; 0 remaining post-rebuild;
`research.person`/`research.person_appearance` unchanged at 2936/21158.

*Not fixed -- see issue #52*: the other 32 rows are a single, different
case form ("...Императорскомъ Мариинскомъ театрѣ") on one
`Administration` page, which turned out not to be a spelling question at
all.

## 52. Fabricated institution value on `administration_1903-04_p003` --
32 entries tagged with a document-title phrase that appears nowhere on
the actual scanned page

**Status: logged, not fixed** (RG: "Log only, don't touch yet" -- found
while checking issue #46's Маріинскій/Мариинскій thread, see its fourth
addendum above).

All 32 entries on `administration_1903-04_p003` have `institution` =
"Списокъ лицъ, состоящихъ на службѣ въ Императорскомъ Мариинскомъ
театрѣ" ("List of persons in service at the Imperial Mariinsky
Theatre"). The people themselves are all real and correctly transcribed
-- every name (Обуховъ, Леммлейнъ, Розовъ, Плескій, Коровинъ, Казанскій,
Дворецъ-Дворецкій, the 23 numbered doctors, etc.) matches
`ForUpload_1903-04_Spisok_Administration.pdf` p.126 directly. But:

- This exact phrase, in either spelling, appears **nowhere else in the
  entire corpus** (checked both "Мариинскомъ" and "Маріинскомъ").
- It does not appear printed anywhere on p.126 itself, nor on p.123-125
  (checked all three directly against the scan/Obsidian vault images) --
  no title, banner, or subheader resembling it is visible.
- The entries themselves aren't Mariinsky-specific at all: doctors
  ("Врачебная часть"), montirovochnaya-chast staff, a registrar, an
  artist/librarian -- general theater-administration roles spanning all
  the Imperial theaters, not one theater's staff.
- The page IS part of the same document as `administration_1903-04_p000`,
  whose real printed title (confirmed on the scan) is "СПИСОКЪ личнаго
  состава театральнаго управленія" -- a shorter, generic title with no
  theater named.

**Working theory, not yet confirmed**: the model fabricated this value
rather than misreading one, likely by borrowing the sentence structure of
a genuinely common template seen elsewhere in the corpus ("Списокъ лицъ,
состоящихъ на службѣ въ Императорскихъ театрахъ," 363 occurrences,
plural/generic) and incorrectly specializing it to a named theater --
possibly latching onto an unrelated, single nearby mention of "Маріинскій
театръ" on p.124 (a police-master role, nothing to do with these 32
entries).

**Not yet done**: decide the actual fix (options discussed: blank
`institution` for these 32 entries per the existing misattachment-fix
pattern; replace it with the real document title from p000; or survey
other `Administration`-season pages first to see if this fabrication
pattern recurs elsewhere before deciding). Also not yet done: checking
whether other entity types show the same kind of fabricated-institution
pattern, since this was found incidentally while checking something
unrelated (Маріинскій/Мариинскій spelling), not via a deliberate audit.

## 47. Venue accuracy audit (events, pivoting from person entities to performance events) — `theater_canonical` classifier gap found and fixed

**Status: fixed.** RG pivoted from the person-side department/position work
to performance events, starting with venue accuracy (`research.event.
theater_canonical`) since that field already existed for events (unlike
the person side, where #46 found no equivalent field exists at all).

Event venue data turned out to be much cleaner than the person side:
27,930/27,930 events had a `theater` value, and only 158 (0.57%) failed
to resolve to `theater_canonical`. Read the actual repertoire scans
rather than guess, and found two genuinely different situations:

- **88 rows legitimately have no single theater to name** — whole-city
  (or literally the whole page's) dark days, where every theater in the
  group shows "—" that day. `theater` holds a group label
  ("С.-Петербургскіе театры"/"Московскіе театры") or, when literally
  every theater on the page was dark, the date column's own header text
  ("Мѣсяцъ, день и число") leaked in as a fallback value. Confirmed
  against `ForUpload_1890-91_Repertoire.pdf` p.8-9 (a week where all 3
  SP theaters are dashed) and `ForUpload_1892-93_Repertoire.pdf` p.2-3
  (10 days where all 3 SP theaters are dashed while Moscow's Большой has
  shows). `theater_canonical=NULL` is correct for these.
- **70 rows were a real, fixable classifier gap** — a single specific
  theater dark while its city's other venues still had shows, written
  as a compound "[city group]. [theater]" string ("Московскіе театры.
  Большой", "С.-Петербургскіе театры. Маріинскій", etc.) that the
  classifier's `starts_with()` check couldn't catch (the theater name
  sits as a suffix, not a prefix). Confirmed against
  `ForUpload_1896-97_Repertoire.pdf` p.2-3: Большой genuinely dark that
  week while Малый has shows on every one of the same days.

Fixed `theater_canonical`'s CASE logic in `pipeline/build_duckdb.py`
(`starts_with()` -> `contains()`). Verified no false positives first:
checked every distinct raw `theater` value's classification under both
old and new logic -- only the 5 expected compound strings changed.
Applied to production; this also fixed a downstream artifact in the
existing completeness-reconciliation logic (issue #13): the
"not_captured" placeholder count dropped 4050 -> 4025, since those 70
events had been double-counted (once as a mislabeled real event, once
as a phantom "missing" placeholder for the same date+theater cell).
`research.event` 27930 -> 27905 (the 25 now-redundant placeholders
removed); `research.performance`/`research.person_appearance` unchanged
(24894 / 21158) -- no real performance data was ever attached to the
removed placeholders.

**Also resolved along the way**: RG initially asked about building a
`theater_canonical`-equivalent field for *people* (mirroring this
existing event-side field) but concluded, after seeing how unevenly the
theater-level signal exists across person entity types (#46's
addendum), that no such field is needed on the person side. This
issue's venue-accuracy audit was scoped to events only from the start.

**Still open**: the broader performance-events work RG was offered --
date accuracy (~6%/1442 rows with a parsing problem), the remaining
completeness gaps (4025 `not_captured` events), receipts, and
repertoire/work-title accuracy -- none started yet.

## 48. Repertoire missing-pages audit — one confirmed scanning gap, four extraction date bugs fixed, one genuine historical closure correctly distinguished from a bug

**Status: mostly done**, prompted by RG's specific worry about pages
missed during scanning/uploading, distinct from #20's whole-season gap
check and from the completeness (`not_captured`) tracking already in
place.

**Method**: used date continuity within each season as a proxy (a daily
printed table should have no gap beyond known closures), then verified
every suspicious gap against the actual scan before concluding anything
-- several looked like missing pages at first read and turned out to be
extraction bugs instead, or vice versa.

**Confirmed genuinely missing pages**: `ForUpload_1890-91_Repertoire.pdf`
-- the book's own printed page numbers jump from 7 straight to 10
between `_002.jpg` and `_003.jpg`; pages 8-9 (~Oct 12-31, 1890) were
never scanned. Not recoverable from what we have; RG informed.

**Four real extraction date bugs found and fixed, all the same general
shape** (a page-specific wrong `month_text`/`year_text`, each confirmed
against its scan before fixing, none guessed at or generalized into a
corpus-wide rule):

1. `repertoire_1895-96_p005` -- `year_text` read "1893 г." where the
   scan clearly shows "1895 г." (108 sessions). This was found first,
   while checking date continuity, as a phantom 596-day gap.
2. `repertoire_1907-08_p000` -- spans Aug 30-Sep 9 per the scan, but
   `month_text` never advanced past "Августъ" once day rolled from 31
   to 1, so 9 real September days appeared as bogus August dates (29
   sessions). Found while chasing down a 20-day gap that first looked
   like it might be another missing-page case (it wasn't -- see below).
3. `repertoire_1902-03_p008` -- spans Oct 22-Nov 3, but the model
   labeled every row "Ноябрь" from the start (all 40 sessions),
   including the Oct 22-31 portion (29 of those needed fixing) --
   likely misled by this one page's own running header printing the
   two months in reverse order ("22 ноября...3 октября.", unlike every
   other page's start-date-first convention).
4. `repertoire_1896-97_p000` -- a third variant: `month_text` for 50
   September rows literally read "1 сентября" (a full date fragment,
   not just the month name), so `parse_russian_date` picked up the
   stray embedded "1" instead of each row's real, distinct day already
   sitting correctly in `date_text` -- all 50 rows collapsed onto the
   single bogus date 1896-09-01. This was the same underlying defect
   class as #14's original day-of-week validator finding, just a
   different failure shape (whole month collapsed onto one date, not a
   day-count drift).

Found via a corpus-wide scan for the general shape (day-of-month
decreases while `month_text` stays unchanged, or a day sequence
otherwise doesn't advance): 9 candidate pages total. Only these two of
the 9 additional candidates beyond the already-known 1907-08/1895-96
cases matched a confirmed, scan-verified bug -- 6 more candidates were
individually checked and are explicitly NOT fixed:
`repertoire_1890-91_p000` and `repertoire_1906-07_p048`/
`repertoire_1907-08_p048` are false positives of the detection
heuristic itself (the day sequence doesn't actually decrease once read
correctly); `repertoire_1897-98_p010`, `repertoire_1899-00_p037`,
`repertoire_1904-05_p011`, `repertoire_1906-07_p037` show a smaller,
different pattern (an isolated single-digit day misread, e.g. "23" for
"29") that needs its own individual scan verification before any fix --
left as a to-do, not guessed at.

Implemented as `pipeline/parse_and_validate.py`'s
`_REPERTOIRE_YEAR_FIXES` and `_REPERTOIRE_MONTH_FIXES` (page + 1-based
session-index-range keyed, same documented-table pattern as the earlier
`_MISATTACHMENT_FIXES`). Every fix dry-run verified first (0
row-count change each time) before applying to production; each also
required re-running `validate_performance_dates.py` afterward, since
`research.event.date` prefers that table's `corrected_date_undate` over
the raw date via `COALESCE` -- without the refresh, a stale day-of-week
"correction" computed back when the date was still wrong would silently
override the fix (caught this the hard way on the first of the four
fixes, then repeated the refresh step for the rest). Net effect across
all four: `analysis.event_entry_date_check`'s `invalid_date` bucket went
3->0 (the bogus "Nov 31" from bug #3 doesn't exist as a real date);
`intra_block_disagreement` 108->58 (bug #4's 50 collapsed-onto-one-date
rows were exactly this category); completeness `not_captured` gaps
4025->3911 (the newly-correct dates now properly fill real grid cells
instead of leaving them looking empty). `research.person_appearance`
unchanged at 21158 throughout (person data untouched); `research.event`
net -114 (removed phantom "not_captured" placeholders, not real data).

**A genuine historical event correctly distinguished from a bug, not
"fixed"**: `repertoire_1894-95_p002`'s apparent 69-day gap (Oct 24-Dec
31, 1894) is not an error at all -- the actual printed page jumps
directly from "19 Октября" to "1 Января" with no page break in between,
almost certainly the Imperial theaters' closure following **Alexander
III's death** (Oct 20, 1894 O.S.) and the national mourning period. The
yearbook's own compilers omitted the closure from the printed table
rather than listing ~70 dark rows. Correctly reflects the source as
printed; left alone.

**Addendum (same day): the `repertoire_1890-91_p012` phantom-row oddity
was not left alone** -- RG pushed back on treating it as too low-stakes
to explain ("I want to know why this happened"), so it was investigated
properly rather than waved off. Downloaded and rendered the actual PDF
page directly at 400dpi (not the possibly-stale pre-existing JPG this
session had been relying on elsewhere) -- confirmed the page ends
cleanly with its decorative closing flourish after May 15, and this is
the file's last page (13 pages total, no page 13 to have supplied more
content). The 3 "26 —" sessions correspond to nothing on this page or
anywhere else in the file: a genuine **model fabrication**, not a
misattachment or mislabeling like the other four Repertoire bugs found
today. Since all 3 were already `is_dark` with no works/receipts,
dropping them loses no real data -- there was never a correct date to
move them to. Implemented as `pipeline/parse_and_validate.py`'s new
`_REPERTOIRE_FABRICATED_SESSIONS` (page-keyed session-index drop set),
dry-run verified (`event_entry` 23880 -> 23877, exactly -3, nothing
else changed), applied to production, `analysis`/`research` rebuilt and
`validate_performance_dates.py` re-run. `research.person_appearance`
unchanged at 21158; `research.performance` unchanged at 24894.

**Addendum (2026-08-25): the 4 individual-digit-misread candidates,
checked one by one against their scans.** Two are confirmed NOT bugs, one
is a small confirmed bug now fixed, one is a substantially bigger
confirmed bug still open:

- `repertoire_1904-05_p011` ("23 Пятница", between real days that would
  suggest "5") -- scan confirms the original 1904-05 book genuinely
  prints "23 Пятница." in that exact position. A real compositor's error
  in the primary source, correctly preserved verbatim (same
  verbatim-preservation precedent as the earlier Поливановъ case).
  **Not fixed, correctly left alone.**
- `repertoire_1906-07_p037` (apparent day-sequence decrease) -- false
  positive of the detection heuristic. The page's own running header
  genuinely reads "9 марта...19 марта", and the scan confirms the table
  starts with 3 real blank rows for days 9-11 before content-bearing days
  12+; the raw JSON just lists sessions out of chronological order within
  the page (content-bearing middle section first, then the blank prefix,
  then a catch-up pass for one column). No date-label error at all.
  **Not fixed, correctly left alone.**
- `repertoire_1899-00_p037` -- two separate anomalies on the same page,
  resolved differently. (a) "9 Четвергъ" (between "3 Среда" and "5
  Пятница") -- scan confirms the original page genuinely prints "9
  Четвергъ." in that exact out-of-sequence spot; a real printer's error,
  correctly preserved verbatim, **not fixed**. (b) "23 Суббота" (between
  "28 Пятница" and "30 Воскрес.", sessions 19-21 for
  Большой/Малый/Новый) -- a zoomed high-res crop shows the printed glyph
  itself is worn/damaged, not a clean "23"; chronologically and visually
  consistent with a mangled "29" (23 April 1900 was in fact a Sunday,
  already correctly used earlier on this same page for sessions 1-3, so
  this can't be a second real "23"). A genuine extraction misread of
  damaged type, not a printed error to preserve. **Fixed**: added
  `_REPERTOIRE_DAY_FIXES` (page + exact `date_text` string keyed, same
  shape as `_REPERTOIRE_YEAR_FIXES`) mapping "23 Суббота" -> "29
  Суббота" for this page only, scoped so it can never touch the
  unrelated, correct "23 Воскрес." sessions elsewhere on the same page.
  Dry-run verified (event_entry row count unchanged at 24131, exactly 3
  sessions' `date_text` changed, nothing else), applied to production,
  `analysis`/`research` rebuilt, `validate_performance_dates.py`
  re-run (`unparseable` 1038->1035, exactly -3, as expected).
  `research.person_appearance` unchanged at 21158;
  `research.performance` unchanged at 24894.
- `repertoire_1897-98_p010` -- the most complex finding, **confirmed bug,
  not yet fixed**. This is not a single-digit misread at all but a
  **content/date misalignment**: on real date 22 Марта the Маріинскій
  printed *two* sessions (a benefit matinee, then "A basso Porto" +
  Walküre 3rd act in the evening, 5785 р. 10 к.). The extraction treated
  the evening session as a new date "23 Понедѣльникъ" instead of
  recognizing it as day 22's second sitting, cascading a **+1 offset
  through the Маріинскій column only** for ~25 subsequent session
  records (real days 22(вечеръ) through 27), while the
  Александринскій/Михайловскій/Большой/Малый columns on the same rows
  are unaffected and stay correctly dated throughout -- confirmed
  row-by-row against a 400dpi scan of the actual page
  (`ForUpload_1897-98_Repertoire.pdf`, page index 10). This is why
  `validate_performance_dates.py`'s weekday-mismatch check never caught
  it: the mislabeled day-number and its (also-shifted) printed weekday
  word are self-consistent with each other, just both wrong relative to
  the true content.

  The drift's tail runs into a second, independent anomaly in the
  primary source itself: the extraction's final mislabeled row reads
  "28 Апрѣля", but the scan shows that row's real printed date cell says
  only **"апр."** -- no day digit at all -- in its own grid cell,
  separated by a full-width horizontal rule from the "6 Понед." row
  below it (confirmed by zooming the grid lines directly; content
  belongs to neither the row above ["27 Пятница"] nor "6 Понед." itself,
  contra an initial guess that it might just be 6 Понед's own
  content). The day-less row still carries real performance content and
  receipts (Маріинскій "Romeo und Julie", 7983 р. 10 к.; Александринскій
  "Jm weissen Rössl", 1786 р. 75 к.), so it needs a real date, not just a
  divider -- positionally the best-supported inference is **28 Марта**
  (Saturday, the one day remaining before the confirmed Holy Week closure
  to April 6), but the source itself never printed a digit there.

  **Fixed (2026-08-25), after RG reviewed the scan directly.** Two
  corrections to my own initial read, both made by RG and confirmed by
  re-checking the pixel-measured grid lines: (1) the Мариинскій drift
  chain's last entry (index 76, "Romeo und Julie") pairs with "27
  Пятница", not with a phantom day-less row -- I had mis-paired two
  adjacent rows on first read. (2) the page's bare "апр." label (index
  77-80's row) is not a distinct calendar date at all -- the editors
  split the "6 Апрѣля" cell across two printed sub-rows and used "апр."
  on the top half purely as a visual month-transition aid for the
  reader, not a date. Corroborating evidence: Михайловскій's "Le Roman
  d'un jeune Homme pauvre" appears on both sub-rows at two different
  receipts figures -- a rehearsal-then-performance shape, exactly like
  the confirmed 22 Марта double session. RG confirmed both corrections
  directly against the scan (sent as images) before implementation.
  Implemented as `pipeline/parse_and_validate.py`'s new
  `_REPERTOIRE_SESSION_DATE_FIXES` (index-keyed exact date_text/month_text
  targets, since the 10 affected sessions split into two different
  corrected values depending on theater -- not a uniform range-shift or
  single find/replace like the other fixes in this issue). Dry-run
  verified (event_entry row count unchanged at 24131; "28 Апрѣля"
  eliminated entirely from the page; "22 Воскресенье" gained the extra
  Мариинскій evening session, 5->6 entries; "6 Понедѣльникъ" gained the
  4 reattributed entries, 5->9), applied to production,
  `analysis`/`entities`/`research` rebuilt, `validate_performance_dates.py`
  re-run (`unparseable` 1035->1030). `research.person_appearance`
  unchanged at 21158; `research.performance` unchanged at 24894;
  `research.event` 27738->27643 (-95, matching the `not_captured`
  completeness-gap drop from 3861->3766 -- these dates now fill real
  grid cells instead of looking like gaps).

**Addendum (2026-08-25): the bare-month "апр." pattern is not unique to
`p010`.** Prompted by RG asking whether other date fields show something
similar, a corpus-wide check found 34 more rows across 12 pages/6+
seasons where `date_text` is literally just a bare month name with no
day digit -- the same shape as `p010`'s "апр." row:
`repertoire_1900-01_p008/p009/p029`, `repertoire_1901-02_p028/p029`,
`repertoire_1902-03_p031`, `repertoire_1903-04_p008/p009`,
`repertoire_1904-05_p020/p021/p026/p027/p032`,
`repertoire_1905-06_p005/p011` (full breakdown in the 2026-08-25 query
log entry). Two of these ("Нодобрь"/"Нодобръ." on `repertoire_1900-01_p008/p009`)
look like a separate misread of "Ноябрь" rather than the same
phenomenon and need their own check. **Not yet individually
scan-verified or fixed** -- `p010` needed real back-and-forth
verification to get right (two of my own initial reads were wrong and
corrected by RG against the scan), so this is flagged as a new open item
rather than assumed to be the same fix applied blindly across all 12
pages.

**Addendum (2026-08-25): the bare-month `date_text` pattern, fully
resolved.** Prompted by RG asking whether other date fields showed
something similar to p010's "апр." row, all 15 page/date_text
combinations from the corpus-wide search were individually checked
against their scans (13 more beyond the 2 checked when the pattern was
first found). **10 confirmed clean, no fix needed** -- the bare month
label sits at a genuine closure (Lent, a holiday gap) or a truly empty
cell, already correctly captured as `is_dark` with zero content:
`repertoire_1900-01_p008/p029`, `repertoire_1901-02_p028/p029`,
`repertoire_1902-03_p031`, `repertoire_1903-04_p009`,
`repertoire_1904-05_p020/p026/p027/p032`. (`1900-01_p008`'s label is
also garbled "Нодобръ." for "Ноябрь." -- cosmetic only, zero downstream
effect since the row is blank either way.)

**5 confirmed real bugs, five different shapes, all fixed** after RG
reviewed each against its scan and corrected two of my initial reads
(p021's session belongs to 1 Суббота, not 31 Декабря as I first guessed;
p008's bug is a full two-row shift, not "already correct" as I first
concluded):
- `repertoire_1904-05_p021`: a genuine printed УТРО/ВЕЧЕРЪ split for
  Новый театръ's 1 Января cell, but the model captured only the УТРО
  half ("Женитьба...", 330 р. 95 к.) and mislabeled it with the bare
  "Январь." instead of 1 Суббота; the ВЕЧЕРЪ half (a blank dash) was
  missing from the JSON entirely.
- `repertoire_1905-06_p005`: the same УТРО-only capture-and-mislabel
  shape, plus an independent second bug on the same session -- the
  receipts (273 р. 41 к.) survived but the work title ("Каширская
  старина, др.") was dropped.
- `repertoire_1903-04_p008`: a genuine two-day run of "Marthe, com. La
  carotte, com.-bouffe." at different receipts, shifted one day late --
  the bare "Ноябрь." row's content (1573 р. 70 к.) really belongs on 1
  Суббота, and the existing "1 Суббота" entry (772 р. 35 к.) really
  belongs on 2 Воскрес.
- `repertoire_1900-01_p009`: a phantom extra row from misreading the
  month header, shifting all 3 Moscow theaters' content one label late
  for one boundary; the resulting empty trailing "2 Четвергъ"
  placeholders were dropped as redundant.
- `repertoire_1905-06_p011`: a clean duplicate-emission bug -- the
  "Ноябрь"-labeled entries are byte-for-byte identical to the
  correctly-labeled "1 Вторникъ" entries right below them; the
  duplicates were dropped.

Implemented as three new mechanisms in `pipeline/parse_and_validate.py`
(`_REPERTOIRE_FIELD_OVERRIDES`, `_REPERTOIRE_SESSION_INSERTIONS`,
`_REPERTOIRE_DUPLICATE_SESSIONS`), with `_repair_repertoire` refactored to
return a counts dict rather than an ever-growing positional tuple. Also
updated `pipeline/prompts/repertoire_system.txt` per RG's request so
future extraction runs recognize a bare month name as a printer's visual
aid, not a calendar date -- this only affects future runs, not the
already-extracted JSON fixed here. Dry-run verified exact expected counts
on all 5 pages plus a clean regression check on p010's unrelated fix,
applied to production, `analysis`/`entities`/`research` rebuilt.
`research.person_appearance` unchanged at 21158; `research.performance`
24894->24892 (-2, duplicate collapse); `research.event` 27643->27637.
Zero real data loss confirmed.

**Still open / low priority**: the broader question of whether any
*other* seasons have a similar single physical-page scanning gap that
date-continuity alone wouldn't surface (e.g. a gap that happens to fall
entirely within an already-expected closure window) was not exhaustively
ruled out.

## 49. Cascading date mislabeling on `repertoire_1893-94_p007` — real
content re-attached to a wrong, mechanically-incrementing date sequence
that runs past the end of the physical page; 6 more candidate pages found
corpus-wide, not yet individually confirmed

**Status: needs source check** (1 page confirmed, 6 candidates open, 1
outlier of unclear cause). Found as a side effect of validating
`pipeline/row_detect.py` (issue #1's row-isolation fix, still in
progress) against a whole season rather than the two hand-picked pilot
pages -- a free, local, ground-truth-vs-detector-count sanity check
(distinct `date_text` per page from `raw.event_entry`) flagged
`repertoire_1893-94_p007` as an apparent detector failure (29 expected
rows, only ~20 found). Checking that against the actual scan showed the
opposite: the *detector* was right (RG independently confirmed only one
real missing row line by eye); the "29" ground truth itself was wrong,
because the underlying raw JSON is corrupted -- unrelated to
`row_detect.py` or ScanTailor, and already sitting in the published
production database.

**Confirmed mechanism** (`outputs/full_run/raw/repertoire_1893-94_p007.raw.json`):
the scan's real table runs Jan 15 - Feb 3, 1894 (confirmed by eye against
the page image). The raw JSON's first 9 dates (Jan 15-23) are each
missing 4 of their 5 theater-column entries -- e.g. the real "16
Воскрес." / Александринскій entry ("Плоды просвѣщенія", 447 р. 28 к.,
plainly visible on the scan) is entirely absent from the JSON. That exact
content instead appears in the JSON attached to "24 Понед." -- a
different, real date later on the same page, whose own true content it
is not. From there the model appears to have lost its place entirely: it
proceeded to fabricate a full, internally-consistent-looking run of dates
from Jan 24 through **Feb 12** -- 12 days that do not exist on this
physical page at all -- each carrying what all reads like genuinely
scan-sourced content (plausible receipts figures, real work titles, no
placeholder/null patterns), just filed under invented date labels. Net
effect: `raw.event_entry` for this one page currently has 20 fabricated-
or-misdated-date entries and 9 real dates each missing most of their row.
This is a different failure shape than issue #1 (which swaps a value
between two *adjacent* real rows) -- here the date labeling itself drifts
and compounds across roughly half a page -- but very plausibly the same
underlying cause (full-page multi-row context confusing the model), just
a more severe manifestation. Directly relevant to the #1 row-isolation
plan already in progress: row-level extraction should structurally
prevent this shape of error too, since each row-crop would carry its own
correct date with no other row's date to drift toward.

**Corpus-wide triage** (all 519 `repertoire_*.raw.json` files, not just
this season): flagged any page whose raw JSON has more than 22 distinct
`date_text` values (every other page in the 1893-94 season tops out at
20). 7 pages flagged:

| page_id | sessions | distinct dates | max repeat count |
|---|---|---|---|
| `repertoire_1890-91_p007` | 115 | 23 | 5 |
| `repertoire_1890-91_p009` | 120 | 24 | 5 |
| `repertoire_1892-93_p000` | 67 | 67 | 1 |
| `repertoire_1893-94_p007` | 89 | 29 | 4 |
| `repertoire_1894-95_p002` | 120 | 24 | 5 |
| `repertoire_1895-96_p000` | 75 | 28 | 5 |
| `repertoire_1897-98_p009` | 89 | 27 | 5 |

Five of these (`1890-91_p007`, `1890-91_p009`, `1894-95_p002`,
`1895-96_p000`, `1897-98_p009`) show the same repeat-count signature
(4-5x) as the confirmed `1893-94_p007` case and are strong candidates for
the identical bug -- **not yet individually confirmed against their
scans**, do that before touching any of them. `repertoire_1892-93_p000`
is a different shape entirely (67 distinct dates, none repeated) and its
cause is not yet understood -- needs its own look, don't assume it's the
same bug.

**Not yet done**: visually confirm each of the 6 remaining candidates
against its scan; determine the true row/date count for each; decide a
fix mechanism (likely a targeted `_REPERTOIRE_*` correction per page,
following the established fix-table pattern, once each is confirmed --
not a corpus-wide automated rule, per this doc's usual practice of never
generalizing from a pattern alone). This affects the currently published
`research` dataset for at least the one confirmed page.

## 50. Repertoire row-isolation pipeline: fold-distortion scoped to
seasons 1890-91–1897-98 only; post-1898-99 seasons validated clean, with
one real bug found by actually extracting rather than trusting clean-
looking row detection

**Status: post-1898-99 seasons look production-ready pending broader
validation; the two-page-spread seasons' fold-distortion is deferred, not
solved.**

**Root cause of "curvy" row boundaries identified**: RG explained the
mechanism directly -- these yearbooks are bound in thick volumes, and
pages curve inward toward the binding the closer content sits to the
fold. Tested two hypotheses this could suggest fixing via a whole-page
pre-dewarp stage (using the outer table border, then vertical gridlines,
as calibration curves) on `repertoire_1893-94_p006`: neither held up.
The outer border was nearly flat (5.7px range) while an interior line
showed a real, differently-shaped 46px bow -- border alone doesn't
predict interior distortion. A vertical column divider tested at the
same y-height as that interior bow's peak stayed essentially straight
(9px sway) -- if this were genuine page-wide gutter curvature, the
vertical line should have swayed too. Edge verticals (near the table's
own left/right borders) showed somewhat more sway (27-33px) but with
inconsistent, low-confidence signal. Net: whole-page dewarping wasn't
pursued further for now -- the evidence didn't cleanly support it as a
general fix, and RG's domain knowledge narrowed the real scope instead.

**Key scoping fact (RG): the fold-proximity distortion only affects
seasons where the Repertoire table spans a two-page spread -- 1890-91
through 1897-98.** Confirmed structurally: `repertoire_1893-94_p006`'s
*original* source page (before any processing) is genuinely landscape
(4540x2982, aspect 1.52) -- only explicable as a 2-page spread; our
portrait-oriented working copy must have been rotated 90° somewhere in
the ScanTailor pipeline. Seasons from 1898-99 onward split the table so
Petersburg and Moscow theaters get separate single pages, keeping table
content away from the fold entirely -- confirmed by checking
`repertoire_1898-99`'s source page directly: portrait, aspect ~0.83,
genuinely narrower, one city's 3 theater columns per page (not 5 combined
columns). This also explains RG's earlier note that the date column
sits on the RIGHT for 1890-91–1897-98 and moves to the LEFT from
1898-99 on -- a different table layout entirely, not just a formatting
tweak.

**Decision**: prioritize the post-1898-99 seasons for production
readiness now; treat the two-page-spread seasons' fold-distortion as its
own properly-scoped problem to return to later, rather than letting it
block progress on seasons that don't have it. Nothing built this session
(the row-level driver, the review workflow, adaptive padding) is specific
to the fold problem -- it all applies equally regardless of season.

**Post-1898-99 validated clean on row-boundary detection**: tested
`repertoire_1898-99_p002/p003/p004` (raw scans, no ScanTailor at all --
not needed for this format: no gutter-proximity distortion, and the
600dpi archival source is already well-behaved, minimal skew, no shadow
near the table). All 3 pages: 36/36 rows correct on fully automatic
detection, zero manual correction needed. `header_line_count` differs
from the two-page-spread seasons' pages (see below).

**One real bug found, only because RG insisted on an actual test
extraction rather than trusting the clean-looking row detection**: a
40/40-strip-presence chain at y≈1 (the very top of the raw scan) turned
out to be the photographed book cover/binding material visible above the
actual page -- not a printed table line at all. Confirmed by direct visual
inspection of that region. Using it as `header_top_curve` (the "outer top
border") pulled the page's own date-range caption ("30 августа...15
сентября") into the header block reattached to every row crop -- which
then leaked into several rows' `date_text`: two rows read "30" and one
read "15" (the caption's own numbers) instead of their real dates. Not
obvious from row-boundary detection alone (the boundaries themselves
were all correct) -- only surfaced by actually running the extraction and
checking the output, exactly the caution RG raised before agreeing to
spend API budget on it.

**Fixed generally, not just for this page**: added a scan-boundary-
artifact filter to `_detect_line_curves` -- drops any chain whose mean y
sits within 1% of image height (or 10px minimum) of the top or bottom
edge, since real printed content never sits that close to the edge given
these scans' margins, while a photographed book cover/binding naturally
would. This shifted curve indexing, so `header_line_count` for this page
format is 1 (not 2 as first assumed before the artifact was known about
and excluded). Re-ran the same page after the fix: 12/12 distinct dates
exactly matching the real scan (was 13, with 3 wrong), spot-checked one
row's full content (all 3 theaters) byte-exact against the scan.

**Not yet done**: broader validation across more post-1898-99 pages
(only 4 checked -- 3 for row-boundary detection, 1 for a full real
extraction); the two-page-spread seasons' fold-distortion remains
unsolved and deferred; `header_line_count`'s value per format still
isn't auto-detected, just manually confirmed per format tested so far.

## 51. Spurious utro/vecher row-split detection -- eight approaches tried,
none reliable; work placed on hold pending outside CV/document-analysis
input

**Status: ON HOLD as of 2026-08-27.** Everything below this line and #50
above it stays exactly where it is until this is picked back up -- treat
this as the authoritative "resume here" note, not #50's older "not yet
done" list alone.

**The specific open problem**: on post-1898-99 pages (see #50 -- these
seasons are otherwise clean and were being prioritized for production),
`_detect_line_curves` sometimes locks onto the gap between a matinee
(утро) and evening (вечеръ) performance stacked inside one date's own
cell, and outputs it as if it were a real row boundary. There is no
printed gridline there. Two confirmed real examples (both from season
1898-99, both hand-verified against the scan) are saved at
`/private/tmp/claude-502/.../scratchpad/memo_assets/example1.jpg` (row
`23 Среда`, line cuts across every column's title line, above the
receipts line) and `example2.jpg` (row `9 Пятница`, line falls exactly
between two performance titles listed under one theater that day).

**Eight detection approaches tried this session, all on real corpus
pages, none holding up as a general rule**:
1. Column ink density at the boundary (checks for a date label
   underneath) -- failed, undermined by imprecise column-boundary
   detection.
2. "Rule extends into date column" peak check -- failed, inconsistent,
   no clean threshold.
3. Connected-component glyph detection -- failed, this typeface's
   Cyrillic glyphs touch/merge at scan resolution.
4. Erosion then connected components -- failed, same root problem as #3;
   erosion strong enough to separate glyphs also erases real strokes.
5. Whole-page dewarp calibrated from the outer table border -- failed,
   see #50 (border curves far less than a real interior line does).
6. Vertical-gridline-based calibration -- failed, see #50 (measured sway
   too small/inconsistent to calibrate from).
7. Row-to-row spacing consistency (flag an unusually short gap between
   two candidates) -- **worked on all 4 pages tested (p005/p007/p009/p014),
   but explicitly RETRACTED per RG: "Don't rely on spacing consistency
   because rows can always be different sizes."** Row height is
   content-dependent, so this is not a valid general rule regardless of
   its test results -- withdrawn on that basis, not because it failed.
8. Full-table-width ink coverage ("does a candidate line span nearly the
   whole table width, the way a real gridline does") -- the most
   promising signal found: real boundaries ran ~20-65% width coverage vs.
   ~11-16% for false ones on the page first tested. **Confounded** under
   full validation against every curve on the 4 already-hand-fixed pages:
   coverage decays down the page (likely a lighting/vignetting gradient
   in the scan), so a real boundary near a page's bottom can score as low
   as a false one near the top. No single global threshold separated them
   cleanly.

**In-progress attempt when work paused**: installing Tesseract (real OCR)
via Homebrew, to test whether reading actual text at a candidate boundary
-- rather than measuring ink geometry -- gives a cleaner signal than any
of the eight above. This required installing Homebrew first (no package
manager existed on this machine); confirmed RG has admin rights, so this
just needed an interactive password prompt run by RG directly. `brew
install tesseract` then had no precompiled bottle for this machine
(Intel, macOS 12.7.6) and had to compile its full dependency chain from
source -- genuinely slow (cmake alone took over an hour), not stuck;
confirmed via active compiler/linker processes at every check, and sped
up noticeably once RG freed up RAM (was down to 95MB free, causing swap
thrashing). **Left running in the background, status unknown as of when
this was placed on hold** -- check `/usr/local/bin/tesseract --version`
and `ls /usr/local/Cellar/` to see how far it got. If it finished, the
next step is untried: test it as a text-presence signal on the two
example boundaries above before trusting it as a fix.

**A plain-language summary memo was written for outside DH-expert
advisors**, explaining the problem and all 8 attempts, plus the two
example images -- sent to RG as local files (not published as a
web artifact, per RG's preference for something plain to paste into an
email): `.../scratchpad/memo_assets/row_boundary_memo.md`,
`example1.jpg`, `example2.jpg`. That memo's content is the fastest way to
re-orient on this problem if picked up by someone else, or after a long
gap.

**To resume**: check the Tesseract build status first (see above); if it
completed, that's the next thing to actually test, against the two known
examples plus a few more pulled from other pages, before considering it a
fix. If it didn't pan out either, the honest state is that all 9
approaches tried (8 geometric + OCR) have failed or been retracted, and
this may need either continued human review per page (workable today,
just not scalable) or expertise this session doesn't have -- which is
exactly what the advisor memo was written to solicit.

**Addendum (2026-08-28): Tesseract build confirmed stalled, not
finished** -- `/usr/local/Cellar/` only holds generic build tools
(autoconf, cmake, etc.), no `leptonica` (tesseract's own dependency) and
no `tesseract` itself; nothing running. Not resumed this session.

**Addendum (2026-08-28): strategy shift -- detect-and-repair after
extraction, rather than solving boundary detection first, smoketested on
one real page.** RG's framing: the goal is complete Repertoire text, no
data lost; if bad rows can be identified *after* extraction, they can be
targeted for repair the same way every other issue in this file gets
fixed (flag -> targeted re-check against the scan -> hand-fix), without
blocking a corpus-wide run on first solving the CV problem above.

Two independent detectors proposed for this: (1) `validate_performance_
dates.py`'s existing day-of-week check (isolated single-row mismatches
are flagged, never silently auto-corrected -- exactly the shape a
fabricated date produces) plus `quality_checks.py`'s existing
`duplicate_event_key` flag; (2) a new row-level-vs-full-page content
diff -- every Repertoire page already has a full-page baseline
extraction on disk from the original pilot run, and the two methods fail
differently (page-level swaps across a big grid; row-level only
fabricates when a crop lacks its own date label), so disagreement
between them is a much stronger signal than same-method resampling
(already shown not to work for this exact failure, above).

**Smoketest**: identified `repertoire_1898-99_p003` as the confirmed
source page for this issue's own `example1.jpg` ("23 Среда" -- verified
by exact receipts match, 815 р. 60 к./1444 р. 95 к./1012 р. 23 к.).
Useful correction to this issue's own framing found in the process: "23
Среда" is an entirely ordinary single-performance row, not a matinee/
evening compound -- the false split isn't specific to утро/вечер pairs,
it's the more general title-line/receipts-line structure every row has,
which the detector sometimes locks onto regardless.

Ran current `row_detect.py` (unchanged, automatic, no human correction)
on this page fresh: **11 curves detected, not reproducing the spurious-
split failure at all** -- instead, 3 real boundaries were missed (17/18,
22/23, 24/25 each merged into one crop covering 2 real dates), a
different failure shape than this issue documents. Ran full row-level
extraction anyway on the resulting 9 crops (3 of them 2-dates-each) via
`pipeline/extract.py`, deliberately not hand-correcting first, to test
against a realistic unsupervised-run condition:

**Result: 12/12 real dates correct, zero fabrication**, including all 3
merged 2-date crops (e.g. row006: 22 Вторн. 1238.12/1376.63/376.19 AND
23 Среда 815.60/1444.95/1012.23, both exactly right in one crop) and
both genuinely dark days (19, 26 Суббота) correctly flagged
`no_performance`. Then ran detector (2) above for real: diffed every
row-level receipts figure against the existing full-page baseline
(`outputs/full_run/raw/repertoire_1898-99_p003.raw.json`) -- **0
disagreements across all 12 dates**, confirming the cross-check
mechanism runs correctly and doesn't false-flag a genuinely clean
extraction.

**Caveats, stated plainly**: N=1 page, and this run happened not to hit
the actual documented failure mode (a crop with no date label of its own
-- the under-segmentation seen here didn't produce that shape, so this
doesn't yet validate the detectors against a real instance of the
harder problem). Still open: find/reproduce a genuine no-date-label
false-split in the wild (rather than the two isolated example crops,
which were manually cropped, not pipeline output) and confirm detector
(1) or (2) actually catches it; then decide whether to run row-level
extraction at scale under this detect-and-repair strategy rather than
waiting on boundary-detection automation.

## 53. entities.person_candidate pending-review queue cleared (4 pairs) --
3 rejected, 1 merged, and the merge surfaced a durability gap in the
Tier 2 candidate-matching system

**Status: resolved for these 4 pairs.** Prompted by RG asking "Do we have
any other people who need to be reviewed as potential merges?" --
`entities.person_candidate` had 4 `pending` rows (20 already rejected
from a prior session). Each pair's full appearance history pulled and
checked against the underlying scans, not decided from the database
pattern alone.

**3 rejected** (all confirmed as two different real people, not a
merge):
- Ивановичъ/Ивановъ, Иванъ Ивановичъ -- a school director (elite court
  rank) vs. a Moscow trombonist/machinist's-assistant. Different careers,
  different cities, and about as generic a Russian name as exists.
- Зубовъ/Рябовъ, Александръ Петровичъ -- an Alexandrinsky orchestra
  percussionist (Musicians) vs. a ballet artist/student (BalletArtists).
  Different entity_type, different craft, surnames not visually/
  phonetically close (unlike the other pairs here).
- Щегловъ/Щеголевъ, Василій -- confirmed via
  `ForUpload_1895-96_TheaterSchoolReport.pdf` p.3: "Щегловъ, Василій" was
  a 1895-96 school graduate explicitly printed as assigned "въ
  Московскую балетную труппу" (the Moscow ballet troupe); independently
  confirmed showing up in `balletartists_*_MSK_*` rosters continuously
  from 1896-97 onward, exactly on schedule. "Щеголевъ, Василій" is an
  unrelated St. Petersburg Mariinsky lighting technician from 1902 on.
  Both surname readings confirmed correct on their own scans -- genuinely
  two different people, not a misread of one into the other.

**1 merged, and it grew in scope once checked**: RG's flagged pair was
"Мокѣевъ, Николай Васильевичъ" (1891-92 through 1902-03, trumpet,
Оркестръ Александринскаго театра) vs. "Мокѳевъ, Николай Васильевичъ"
(1890-91 only, same orchestra). Confirmed same person against
`ForUpload_1890-91_Spisok_OrchestraSP.pdf` p.79, item 24: genuinely reads
"Мокѣевъ" (ѣ/yat), not "Мокѳевъ" (ѳ/fita) -- a one-character homoglyph
extraction slip, not a real variant. Fixed via a new
`_repair_mokeev_spelling()` in `parse_and_validate.py` (single confirmed
instance, dry-run verified at exactly 1 before applying).

**Checking the effect of that text fix surfaced a third, previously
invisible split of the same identity**: after the fix, the two records
still didn't merge automatically (Tier 1 froze their separate existing
person_ids; Tier 2 doesn't compare exact-name matches at all, on the
assumption Tier 1 always catches those -- see `merge_duplicate_persons()`'s
own docstring for this exact documented gap). Investigating *why* turned
up a THIRD person_id for the same name, 1903-04 through 1907-08 (5
entries), with patronymic printed as "Вавиловичъ" instead of
"Васильевичъ" -- confirmed genuinely printed that way (not a misread) on
both `ForUpload_1903-04_Spisok_OrchestraSP.pdf` p.4 item 27 and
`ForUpload_1907-08_Spisok_OrchestraSP.pdf` p.33 item 23, the latter also
giving "Оставилъ службу 1 мая 1908 г." (left service 1 May 1908). This
pair was never flagged as a `person_candidate` at all, in any status --
family_name matches exactly (so it's outside the family_name_variant
search) and the Васильевичъ/Вавиловичъ patronymic edit-distance is above
Tier 2's fuzzy-match threshold (so it's outside patronymic_variant too).
Entirely invisible to the existing review queue.

**Full picture assembled from all three groups** (same family name, first
name, orchestra, and instrument -- Труба -- throughout):

| Seasons | Patronymic printed | Service-start printed |
|---|---|---|
| 1890-91 (1 entry) | Васильевичъ | 1 января **1891** г. |
| 1891-92 - 1902-03 (12 entries) | Васильевичъ | 1 января **1890** г. (every year) |
| 1903-04 - 1907-08 (5 entries) | **Вавиловичъ** | 1 января **1890** г. (every year) |

Two real inconsistencies, neither a misreading: the very first entry
disagrees with all 17 later entries on the start year (1891 vs. 1890,
read as a first-edition error corrected in every reprint after); and the
patronymic switches from Васильевичъ to Вавиловичъ starting 1903-04 and
stays that way through the end of this person's tenure in 1908 -- while
the 1890 start date stays consistent across *both* patronymic eras,
bridging them. **RG confirmed treating all three as one person** ("they
were in the same orchestra with the same instrument"), with a working
hypothesis for the patronymic switch: Вавиловичъ is a much rarer
patronymic than the common Васильевичъ, and the musician himself may have
flagged the yearbook's long-standing error to the editors, who corrected
it starting with the 1903-04 edition -- offered as the most likely
explanation, not a confirmed fact.

**Applied**: manually merged via direct `entities.person.
superseded_by_person_id` (survivor = lexicographically smallest person_id,
matching `reconcile_person_merges()`'s own convention) since this pair
falls entirely outside the algorithmic candidate system described above.
Durability confirmed by design, not assumed: `build_person_tier1` trusts
`entities.person_link`'s current state as ground truth for entry
membership on every future rerun ("reuse it unconditionally -- this is
what makes person_id survive a matching-logic improvement" -- see its own
docstring), so calling `_repoint_all_superseded()` after the manual merge
is sufficient to make it stick across future full pipeline reruns, with
no dependency on Tier 2 ever independently rediscovering this pair. Also
inserted a permanent record into `entities.person_merge_log` (deterministic
candidate_id, full reasoning in `tenure_evidence`) purely as an audit
trail, since that table isn't itself what makes the merge durable here.
Verified: `research.person` for the survivor now spans 1890-91 through
1907-08 across 18 appearances; `research.person`/`research.person_appearance`
totals 2934/21158 (net -2 from the 2 losers absorbed, appearance count
unchanged).

**Open, not resolved**: `_refresh_canonical_fields()`'s majority-vote logic
set the merged person's displayed `canonical_patronymic` to "Васильевичъ"
(13 of 18 entries) -- the *opposite* of RG's own hypothesis that
"Вавиловичъ" is more likely the true spelling. Left as the automatic
majority-vote default rather than manually overridden, since RG's
reasoning is a plausible hypothesis, not a confirmed fact. Worth a
deliberate decision (and, if changed, a documented manual override,
since a future `_refresh_canonical_fields()` rerun would silently revote
back to the majority spelling otherwise) whenever this comes up again.

**Also newly relevant**: this session confirmed `merge_duplicate_persons()`'s
own documented structural gap (exact-tier1_key duplicates that Tier 1
freezes apart and Tier 2 skips by design) is not just theoretical --
this is the second real instance found this project (after Дягилевъ,
mentioned in that function's own docstring), and the THIRD entry
(Вавиловичъ era) shows the gap can compound with a genuine spelling
divergence on top of the frozen-identity gap, making it invisible to
every existing automated check simultaneously. Not fixed generally (the
existing hand-merge pattern, used here and in issue #45, remains the
right tool for cases like this) -- noted here in case a pattern of
several such cases eventually justifies building a dedicated automated
check.

**Follow-up (same day): tried to settle the Васильевичъ/Вавиловичъ
question against outside genealogical sources -- inconclusive, but one
useful supporting data point found.** Web search for the musician by
name/orchestra turned up nothing. Checked the digitized "Весь
Петербургъ" St. Petersburg city directory for 1903 (RNB/`nlr.ru`, see
[[vesь-peterburg-directory-lookup]] for how to use this source generally)
directly against its high-resolution page scan (the "Мо" alphabetical
section, p.442): no entry for a "Мокѣевъ, Николай" explicitly tied to a
musician's occupation or the Alexandrinsky theater -- these directories
only list heads of household/independent residents, so he may simply not
have had his own listing (institutional housing, lodging with a
relative, etc.). Not a dead end, though: the same page lists **"Мокѣевъ,
Иванъ Вавиловичъ"** (Vasilievsky Island, 18th Line, No. 11) -- meaning
"Вавиловичъ" is a real, independently-attested patronymic actually in
use by the Мокѣевъ family in St. Petersburg in exactly this era, most
plausibly a sibling of our musician sharing the same father. Doesn't
confirm the musician's own patronymic, but is real circumstantial support
for RG's hypothesis, found entirely outside the yearbooks. The
conclusive next step, not pursued further this session, would be RGIA
(Russian State Historical Archive) Fond 497, "Дирекция императорских
театров" (1746-1929, ~47,000 files) -- likely holds a formal personnel/
service file (послужной списокъ) for this musician, but isn't
online/searchable; would need an in-person archive visit or a
St. Petersburg-based researcher.

## 54. Full audit of person name fields (family_name/first_name/
patronymic) for non-name contamination across all 6 entity types --
Musicians' two known-but-never-text-fixed patterns closed for good in
`parse_and_validate.py`; the rest scoped and logged for later

**Status: partially done.** Prompted by RG asking to double-check name
fields corpus-wide, not just the entity types already audited. Ran a
heuristic sweep (institutional/note keywords, noble-title words,
parentheses, unusually long values, bare-space patronymics) across
`family_name_clean`/`first_name_clean`/`patronymic_clean` for all 6
entity types.

**Full scope found** (see 2026-08-27 query_log.md entry for the exact
query): every entity type has some contamination. By rate:
Administrators worst (2.75%, 47/1707 -- almost entirely one bug: a
noble title word landing alone in `first_name`, with the real
first+patronymic bundled together into `patronymic` -- e.g.
`first_name="баронъ"`, `patronymic="Владиміръ Алексѣевичъ"`), Graduates
second (1.55%, 7/452 -- section-header text captured as a student name,
plus "(по театру X)" assignment annotations), then Musicians (0.61%,
mostly one page's cross-reference stubs, see below), BalletArtists
(0.56%, almost entirely the stage-name/alias parenthetical pattern),
ProductionTeam (0.72%), TheaterSchoolStaff (0.40%).

**Two Musicians patterns investigated in detail, found to already be
resolved at the entities layer -- but never fixed at the text layer,
exactly the "worth a proper parse_and_validate.py fix" note issue #29
left for later.** Re-discovered, independently, the exact "см.
<orchestra>" cross-reference-stub bug already extensively documented in
issues #27-#29 (a musician who plays in two of the season's orchestras
only gets their full biography written out once; every other roster
just prints "Бѣлкинъ (см. оперный оркестръ). Тромбонъ." -- confirmed
again against `ForUpload_1890-91_Spisok_OrchestraSP.pdf` p.78), and the
"(онъ же и капельмейстеръ военной музыки)" whole-patronymic role-note
pattern from issue #30. Checked `entities.person_link`/`entities.person`
first, per the "always run a fresh query, don't trust memory or a prior
session's cached numbers" rule -- confirmed **all 210/216 resolvable
cross-reference stubs (issue #29) and the Марквардтъ patronymic fix
(issue #30) are still correctly in place** at the entity/canonical
layer; the gap is specifically that `raw.person_entry`'s own text still
held `first_name="см."`/`patronymic="оперный оркестръ"` etc.
(confirmed with a fresh count: 26 + 8 = 34 instances, matching the
historical counts exactly) because none of that prior work ever touched
`parse_and_validate.py` -- only direct `entities.person` UPDATEs.

**RG: "Close for good since I want the pipeline to work for future
lists."** Implemented as two new general repair functions:

- `_repair_smotri_crossref()` -- detects `first_name="см."` (bare
  cross-reference) or `first_name="<ordinal>"` + `patronymic` containing
  "см."+"оркестр" (the homonym-ordinal variant, e.g. "Вальтеръ 2-й").
  Deliberately does **not** attempt to resolve *who* the cross-reference
  points to -- that stays a cross-page, sometimes-genuinely-ambiguous
  entity-resolution-layer job (Tier 1/2 + hand review, as issues #27-29
  already do very thoroughly), consistent with `raw` staying a verbatim,
  page-centric record rather than an inferred one. Instead: clears
  `first_name`/`patronymic` (never leaves "см."/the cross-reference
  target sitting there), preserves the ordinal onto `family_name` where
  one was about to be lost, and folds the cross-reference itself into
  `tenure_note_text` (`"(см. <target>)"`) so the information isn't
  discarded, just relocated to a field that can actually hold a note.
- `_repair_role_note_patronymic()` -- detects a dual-role/appointment
  annotation occupying the **entire** patronymic field (matched as a
  whole-field pattern, not a substring strip, so it can never touch a
  genuine patronymic that merely has an appended parenthetical -- see
  the still-open 13-person alias/stage-name question below, which is a
  different shape of problem). Moves the note to `tenure_note_text`,
  clears `patronymic` to `NULL` (matching Марквардтъ's confirmed
  reality: no patronymic is ever printed for him).

Dry-run verified against `outputs/full_run/raw` first (26 + 8 = 34
entries across 9 pages, exact match to the corpus-wide count) before
applying. Re-ran `parse_and_validate.py` + `build_duckdb.py` (raw/
analysis only; entities/research untouched by this rebuild) +
`build_research_model.py`. Verified 0 remaining instances of either
pattern in `raw.person_entry`; spot-checked that the existing, already-
correct `entities.person_link` resolution for these entries (e.g.
`Гильдебрандтъ` -> `Гильдебрандтъ, Рихардъ Николаевичъ`) survived
untouched, since `entry_id` is stable and doesn't depend on the text
content that changed. `research.person`/`research.person_appearance`
unchanged at 2934/21158 -- a pure text fix, same as every prior one this
session.

**Not done -- logged for a later pass, not this session**: the four
other categories sized above (Administrators' noble-title/bundled-
patronymic bug, ~30+ entries; Graduates' section-header and
assignment-annotation contamination, ~7; BalletArtists' stage-name
parentheticals, 38 -- already fully resolved at the entity layer per
issue #30's 14-person consolidation, same "text layer never fixed" gap
as the Musicians case above; ProductionTeam's tenure-note-as-family_name
bug, 3 confirmed instances on `productionteam_1894-95_p001`). Each needs
the same discipline as this pass (check the actual scan, confirm the
entity-layer state first, then decide whether a general
`parse_and_validate.py` fix is warranted) before touching.

## 55. Remaining Musicians name-field contamination after issue #54:
three new patterns found and fixed generally, closing the Musicians
category to just already-tracked/legitimate content

**Status: fixed.** Follow-up to issue #54 -- RG asked "are there any
remaining issues in the Musicians category?" Re-ran the same heuristic
sweep scoped to Musicians only: down from 43 flagged entries to 9 (one,
"Нольте (фонъ)," already confirmed correct-as-printed by issue #30 --
8 genuine). Checked each against the source before fixing, per this
project's standing rule.

**Letter-spaced (tracked/разрядка) typography transcribed literally**
(28 corpus-wide, all on `musicians_1898-99_SP_p006`, p.94): confirmed
every surname on this page prints letter-spaced for emphasis
("К у д е н г о л ь д т ъ"); the model correctly collapses this to a
normal word in the great majority of cases (~25 of 28 entries on this
page alone) but occasionally transcribes it verbatim. Fixed via a new
`_repair_letter_spacing()`, applied to family_name/first_name/
patronymic alike. **First version of the regex missed a real case**
("Кулле 1-й"/"Кулле 2-й" -- a letter-spaced surname followed by an
*un*-spaced homonym-ordinal suffix) -- caught only by re-checking the
full corpus-wide result after applying the first version, not by the
scan check alone; broadened the regex to handle an optional trailing
` <N>-й`/`-я` suffix, preserving it with its own separating space
rather than fusing it onto the collapsed name.

**Compound/hyphenated first name split across a dash into patronymic**
(13 corpus-wide, 12 pages, both Musicians and BalletArtists): confirmed
on `musicians_1890-91_MSK_p004` (p.110): "Кнауеръ, Генрихъ - Эдуардъ"
and "Падель, Іоганъ - Фридрихъ" both print as one hyphenated compound
first name (common for this corpus's German-surnamed musicians, no
patronymic at all -- consistent with issue #30's existing note on the
same shape), extracted with the second half plus a stray leading dash
landing in `patronymic`. Also confirmed a dash-less variant on
`musicians_1902-03_MSK_p002` (p.116): "Рессеръ, Мардохей Земинъ
Шліомовичъ" prints with no comma between the two-word first name and
the real patronymic, extracted as first_name="Мардохей"/
patronymic="Земинъ Шліомовичъ" instead of first_name="Мардохей
Земинъ"/patronymic="Шліомовичъ". Fixed via `_repair_compound_first_name()`
-- the dash-prefixed case is a safe, general rule (a real patronymic
never begins with punctuation); the "Земинъ" case is scoped narrowly
(this exact word only), since generalizing "first word of any
multi-word patronymic" would be too broad to trust from one example.
**Independent corroboration the fix is correct, found while reviewing
the dry run**: "Герберъ, Августъ-Генрихъ" already appears correctly
joined elsewhere in the corpus (1894-95) -- exactly matching what the
fix produces for the same person's broken 1906-07 appearance, without
having been told the two were the same person.

**Instrument name in patronymic** (6 corpus-wide, 4 pages): confirmed
on `musicians_1898-99_SP_p006` (p.94, entry 43): "Шредеръ, Карлъ ...
Ударные инструменты" prints no patronymic at all (same German-surname-
no-patronymic pattern), with his own instrument landing in `patronymic`
while the dedicated `instrument` field was left empty. Mirror case of
issue #32's `instrument_clean` work (that cleaned contamination out of
`instrument`; this moves a value that belongs there in from elsewhere).
Fixed via `_repair_instrument_in_patronymic()`, checked against a fixed
list of known instrument names and gated on `instrument` currently
being empty so it can never overwrite a real value.

All three dry-run verified against `outputs/full_run/raw` before
applying (exact match between dry-run and applied counts each time,
including after the letter-spacing regex fix). Re-ran
`parse_and_validate.py` + `build_duckdb.py` + `build_research_model.py`;
0 remaining instances of any of the three patterns; spot-checked fixed
entries directly. `research.person`/`research.person_appearance`
unchanged at 2934/21158 across all three fixes.

**Musicians category now closed**: every remaining multi-space/
suspicious value in `raw.person_entry` for this entity type is either
already tracked elsewhere (issue #26/#28's institutional-text-as-name
bugs) or genuine compound/hyphenated surname content with normal
(non-letter-spaced) spacing, correctly left untouched.

## 56. `rank_or_title` for Musicians -- 97% instrument contamination, fixed by splitting rather than wiping, preserving every genuine honorific

**Status: fixed.** Follow-up to issues #54/#55 -- RG asked to make sure
instruments show up in the `instrument` field and nowhere else, which
surfaced `rank_or_title` as by far the largest remaining gap (900 hits
in `heading_path` too, addressed separately below). Per
`docs/schema.md`, `rank_or_title` is "civil rank... or honorific" --
never an instrument -- so any instrument-shaped value here is
unconditionally wrong, not an alternate convention.

**Full scope**: 3157 of 7065 Musicians entries have a non-blank
`rank_or_title`; 3048 (96.5%) are instrument-shaped once trailing
periods and spelling variants (Біолончель, Альть, Вальдгорнь, Волторна,
etc.) are counted, confirmed against 3 separate scans
(`musicians_1890-91_MSK_p001` p.107, `musicians_1893-94_MSK_p003`
p.102, `musicians_1892-93_MSK_p002` p.98).

**RG's explicit concern, addressed by design**: "I don't want to
generalize if it means we miss exceptional cases." A blanket "contains
an instrument word -> clear the field" rule would have destroyed real
content -- confirmed real by manually reviewing every one of the ~90
distinct non-pure-instrument values in the corpus, not just a sample.
Built `_repair_musicians_rank_or_title()` as a **split**, not a wipe,
peeling off exactly four confirmed patterns in order and leaving
anything else completely untouched:

1. A `"(съ <date> г.)"` tenure-start prefix -- checked all 37
   occurrences directly against `tenure_note_text` first: the same
   date text is present there in every single case, so this prefix is
   always fully redundant and discarded outright, not re-appended.
2. A `"(см. ...)"` cross-reference note -- relocated verbatim to
   `tenure_note_text` (this one is NOT redundant elsewhere, unlike the
   date prefix).
3. A leading known instrument name -- moved to `instrument` only if
   that field is currently empty (never clobbers a real value already
   there), but always stripped from `rank_or_title` regardless.
4. Whatever remains, if it's a service note ("Переведенъ..."/
   "Оставилъ службу...") -- relocated to `tenure_note_text`.

Anything left after all four steps is left alone. Dry-run verified
against every distinct value in the corpus before applying, including
14 hand-written test cases covering every combined shape found (and
confirming the critical one: "Скрипка. Солистъ Двора Его
Императорскаго Величества" correctly becomes
`instrument="Скрипка"`/`rank_or_title="Солистъ Двора Его
Императорскаго Величества"`, not wiped).

**Two ambiguous cases checked against scans before deciding, per RG's
request, rather than guessed at:**
- `"Музыканты:"` (1, `musicians_1892-93_MSK_p002__e016`) -- confirmed a
  genuine printed section header ("Балетный оркестръ" -> "Музыканты:"
  -> "1. Альбрехтъ...", p.98), just in the wrong field. Fixed via a
  narrowly-scoped `_repair_musicians_stray_heading()` (this exact value
  only, not a general "looks like a heading" rule, since there's only
  one confirmed instance to validate a broader rule against) --
  appended to `heading_path` as "Балетный оркестръ / Музыканты",
  matching the compound-path convention already used 51 times
  elsewhere in this corpus.
- `"(онъ же и библіотекарь Музыкальной библіотеки)"` (4, all one
  person -- Фарскій, Альбертъ Карловичъ, 1893-94 through 1902-03) --
  confirmed word-for-word against the scan
  (`musicians_1893-94_MSK_p003`, entry 32): a real, consistent
  (4 separate printings) dual-role fact, not contamination. Left
  untouched.
- The other 2 apparent exceptions ("1 мая 1892 г.", "21 ноября
  1891 г.") turned out not to be a `rank_or_title` problem at all --
  both entries have `family_name="Оставилъ службу"`, i.e. they're
  issue #28's already-tracked fake-person bug (a resignation date
  orphaned into its own bogus entry). Correctly left alone as out of
  scope for this fix.

**Applied and verified**: `raw.person_entry.instrument` empty count for
Musicians dropped from 5865/7065 to 3190/7065 (2675 recovered across 77
pages). Spot-checked genuine content survived exactly as designed:
"Ауэръ" (Leopold Auer) and "Цабель" (Albert Zabel) both show "Солистъ
Двора Его Императорскаго Величества" correctly preserved across many
seasons with instrument cleanly split out (Скрипка/Арфа respectively);
Фарскій's dual-role note unchanged in all 4 appearances.
`research.person`/`research.person_appearance` unchanged at 2934/21158
-- a pure text/field-relocation fix.

**Not done this pass, logged for later**: `heading_path` also holds
~900 instrument-shaped values, but (per RG's live investigation) this
is NOT a uniform bug the way `rank_or_title` was -- some pages have the
instrument genuinely, correctly landing in `heading_path` (e.g.
`musicians_1890-91_MSK_p001`, where each row simply has no other
heading and the model puts the trailing instrument there instead of in
`instrument`); other pages have `heading_path` "stuck" repeating an
earlier row's value while the true per-row instrument sits correctly
in `rank_or_title` instead (confirmed on `musicians_1893-94_MSK_p003`:
`heading_path` repeats "Ударные инструменты" -- entry 9's own genuine
value -- down through many unrelated later rows, while `rank_or_title`
correctly varies with each person's real instrument). A naive
`heading_path`-to-`instrument` move would be wrong for the stuck-value
pages -- would misfile a stale value AND destroy the real section label
("Музыканты") those rows should have. Needs its own scoping pass (how
common is each of the two shapes corpus-wide) before any fix is
written.

## 57. `heading_path` scoping for Musicians -- naive fallback confirmed
actively dangerous, not just incomplete; 54 genuinely-lost instrument
values hand-transcribed from scans; structural heading_path fix still open

**Status: partially done (54 instrument values recovered; the
heading_path field itself still not fixed).** Direct follow-up to issue
#56 -- RG's stated concern ("I don't want to generalize if it means we
miss exceptional cases") was validated concretely here, not just in the
abstract.

**Confirmed the naive fallback would have fabricated wrong data, not just
missed some right data.** The obvious next move after #56 -- "if
`instrument` is still empty, trust `heading_path`" -- was checked against
a scan before being applied anywhere. Scoped first: exactly 4 pages
corpus-wide show a 10+-row run of an identical instrument-shaped
`heading_path` value (always "Ударные инструменты," run lengths 13-39).
Checked the largest (`musicians_1901-02_MSK_p002`, p.121) directly: only
entry 35 (Зюсъ) genuinely plays percussion; the other 38 rows in that
run are 38 *different* real instruments (violinists, a harpist, a
cellist, brass, woodwinds) that the naive fallback would have silently
overwritten with "percussion" for all of them. Confirmed generally: two
of the four pages already had their real instrument recovered by issue
#56's `rank_or_title` fix (25/27 and 31/31); the other two never had
it anywhere else in the row at all, because their "(см. оперный
оркестръ)" cross-reference notes were dropped entirely during
extraction rather than merely misplaced (matches issue #27's documented
"~40% of the time this phrase is lost outright" finding).

**54 values hand-transcribed from the scans, re-verified live in this
session rather than trusted from an earlier recollection** (RG: "*no
guessing!"): `ForUpload_1893-94_Spisok_OrchestraMoscow.pdf` p.102
(2 entries: Заальборнъ -- genuinely percussion, the real origin of that
page's stuck run; Фарскій -- Альтъ, dropped from every field before
this fix), `ForUpload_1890-91_Spisok_OrchestraSP.pdf` p.79 (13 entries,
54-66), `ForUpload_1901-02_Spisok_OrchestraMoscow.pdf` p.121 (39
entries, 35-73). Applied via a new `_INSTRUMENT_TRANSCRIPTION_FIXES`
patch table (same array-index-keyed pattern as the existing
`_MISATTACHMENT_FIXES`), each entry's array index independently
verified against the raw JSON before writing the fix. Dry-run matched
54/54 exactly before applying to production. Verified: Musicians'
empty-`instrument` count dropped from 3190 to 3136 (54 recovered,
exact). `research.person`/`research.person_appearance` unchanged at
2934/21158.

**Deliberately not touched by this fix**: `heading_path` itself, for
either the 54 hand-fixed rows or the other ~67 rows in the same 4
stuck runs whose instrument was already recovered via issue #56. The
correct restored value turns out to differ by page, confirmed (not
assumed) from adjacent same-page/prior-page evidence:
- `musicians_1893-94_MSK_p003`: entries 2-8 (immediately before the
  stuck run starts) all read `heading_path="Музыканты"` -- a real,
  repeated section label to restore for entry 9 onward.
- `musicians_1890-91_SP_p004`: the *preceding* page
  (`musicians_1890-91_SP_p003`, entries 44-51) shows `heading_path`
  genuinely holding each person's own, individually-varying instrument
  throughout, with no separate section-heading concept anywhere on this
  stretch of pages at all -- meaning the correct fix for this specific
  page is to set `heading_path` equal to the same per-row instrument
  value (matching this page's own established convention), not to
  restore some other section label that was never actually used here.
- `musicians_1894-95_MSK_p003` and `musicians_1901-02_MSK_p002`:
  **checked and found genuinely ambiguous with what's on the page
  itself** -- both pages start mid-list (list numbers 6 and 35
  respectively), so the true prior heading isn't visible on the page at
  all and would need to be pulled from a preceding page not yet
  checked for this specific question.

Also noticed in passing, not yet addressed: `musicians_1893-94_MSK_p003`
entry 1 (Александровъ) has `heading_path="Капельмейстеръ"`, which is
also wrong by the same evidence (entries 2-8 read "Музыканты," and the
scan's actual Kapellmeister, Арендсъ, is a separate, unnumbered line
above the numbered list) -- a smaller instance of the same general
"heading_path carries a stale value from the line above" bug, outside
this pass's 10+-run detection threshold.

**Not done**: the general "shape A" migration (heading_path -> instrument
for the other ~820 pages/rows that hold a plausible, non-repeated
instrument value with no other heading available) is still entirely
open -- issue #56 flagged it, this issue scoped the dangerous subset out
of it, but the safe majority hasn't been touched yet either.

## 58. `heading_path` restored for all 4 stuck-run pages -- confirmed the
correct value genuinely differs by page, closing out issues #56/#57

**Status: fixed.** Direct follow-up to #57 -- RG: "Let's finish off
this." Gathered adjacent-page evidence for all 4 pages before writing
anything (never assumed one restoration rule fits all 4, and the
evidence confirmed it wouldn't have):

- `musicians_1893-94_MSK_p003`: entries 2-8 (immediately before the
  stuck run) read `heading_path="Музыканты"` -- real, repeated section
  label, restored for entries 9-35. Also fixed entry 1 (Александровъ),
  a smaller instance of the same underlying bug (stuck at
  "Капельмейстеръ," the line above the numbered list) -- confirmed via
  the analogous transition on `musicians_1894-95_MSK_p002` (its own
  unnumbered "Арендсъ... Оркестръ Малаго театра / Капельмейстеръ" entry
  immediately followed by numbered entry "1." reading ".../ Музыканты").
- `musicians_1894-95_MSK_p003`: continues
  `musicians_1894-95_MSK_p002`'s numbered list (item 6 follows item 5) --
  that page's own entries 48-52 read "Оркестръ Малаго театра /
  Музыканты," the exact compound path restored here for entries 1-31.
- `musicians_1890-91_SP_p004`: the preceding page
  (`musicians_1890-91_SP_p003`, entries 44-51) shows `heading_path`
  genuinely holding each person's own individually-varying instrument
  throughout, with no separate section-heading concept anywhere on this
  stretch of pages -- so the correct restored value is each entry's own
  instrument (same value now in `instrument` per issue #57), not a
  fabricated section label. Also caught 2 more affected entries this
  same evidence surfaced (52-53, Фейтъ/Франкенштейнъ -- stuck at
  "Капельмейстеръ" too, for the same reason as #57's Александровъ case;
  their own instrument, Арфа/Литавры, had never been captured anywhere
  else either) -- added to `_INSTRUMENT_TRANSCRIPTION_FIXES` alongside
  the heading_path fix, both confirmed against the same already-verified
  scan.
- `musicians_1901-02_MSK_p002`: the preceding page
  (`musicians_1901-02_MSK_p001`, entries "1."-"34.") shows `heading_path`
  legitimately NULL throughout its entire numbered list, with
  `instrument` alone carrying every entry's real value -- so the correct
  restored value here is NULL, not a fabricated label this list never
  used at all.

Applied via a new `_HEADING_PATH_RESTORE_FIXES` patch table (same
idx-keyed pattern as `_MISATTACHMENT_FIXES`/
`_INSTRUMENT_TRANSCRIPTION_FIXES`), dry-run matched 28+31+15+39=113
exactly before applying to production. Verified: no page has more than
3 remaining "Ударные инструменты" `heading_path` values anywhere in the
corpus (fully plausible for a genuine small percussion section, unlike
the fixed pages' 13-39-row runs).
`research.person`/`research.person_appearance` unchanged at 2934/21158.

**This closes issues #56, #57, and #58 as one complete arc**: `instrument`
contamination in `patronymic` (issue #55) -> `rank_or_title` (#56,
2675 recovered) -> the `heading_path` "stuck run" scoping and 54
hand-transcribed values (#57) -> `heading_path` itself restored (#58).
Musicians' `instrument` field coverage went from 1200/7065 (17%) at the
start of this arc to 3931/7065 (56%) by the end, entirely through
confirmed, scan-verified fixes -- no value written anywhere in this
whole arc without being checked against the actual printed page first.

**Follow-up (#59, below) built and applied the general "shape A"
migration this issue left open.**

## 59. General "shape A" `heading_path` -> `instrument` migration applied
-- all 19 candidate pages hand-verified against scans first; confirmed
NOT safe to automate naively, 23 of 774 touched rows needed a
scan-checked correction rather than a blind move

**Status: fixed.** Direct follow-up to #57/#58's closing note. RG:
"Yes, go through all of them" -- rather than trust the ~820-row estimate
and migrate it in one blind pass, every one of the 19 candidate pages
(767 rows, re-scoped precisely by a fresh query) was read against its
own scan first, continuing the same discipline used throughout #54-#58.

**This caution was concretely justified, not just procedurally
followed.** A first spot-check of 4 pages (before this issue's full
pass) already found a ~5% error rate -- confirmed here for the complete
19-page pool: of 774 total rows touched, **23 (3%) needed a scan-
verified correction instead of trusting `heading_path` as printed**, in
five distinct failure shapes, all confirmed by direct comparison against
the printed page rather than inferred from a pattern:
- **stuck/shifted from a neighboring row's real value**: Браунштейнъ,
  both Еременко instances, Плотниковъ, Ватерстрадъ/Вейкманъ (shifted by
  one row), both Гуманъ instances, Кулле 1-й, Ластовскій -- 9 rows.
- **two adjacent rows swapped with each other**: Фридрихъ/Царскій on
  `musicians_1892-93_MSK_p001` -- 2 rows.
- **a fabricated plural category word matching nothing printed
  anywhere on the page**: Розановъ ("Кларнетисты"), Ромашковъ 1-й/
  Рѣзниковъ ("Альты") on `musicians_1906-07_MSK_p003` -- confirmed by
  zooming the actual scan region, no such subheading exists -- 3 rows.
- **the person's own name duplicated into heading_path because no
  instrument is printed at all**: Газенкампфъ, and (variant, one row
  where the duplicated-name pattern happened but the real instrument
  *was* recoverable) Лудольфи -- 2 rows.
- **genuinely no instrument printed for a brand-new hire** (entry ends
  at the tenure date, heading_path still holds a stuck neighbor value):
  Голубевъ/Дворниковъ/Де-Буръ/Зайцевъ (`musicians_1903-04_MSK_p001`),
  Яньшиновъ (`musicians_1906-07_MSK_p004`) -- 6 rows, `instrument`
  correctly left empty rather than fabricated.
- **two structurally distinct one-offs**: Сиборъ
  (`musicians_1906-07_MSK_p003`, heading_path = "Скрипка. Солистъ
  балета." -- genuinely both his instrument and a title bundled
  together, split via the existing `_split_leading_instrument` helper
  rather than migrated whole) and Эмме (`musicians_1906-07_MSK_p004`,
  heading_path stuck on the *next* section's own "Дирижеръ" heading,
  printed immediately below on the same page) -- 2 rows.

Wired in as two new pipeline functions in `parse_and_validate.py`:
`_repair_heading_path_shape_a()` (the general migration, gated by
`_SHAPE_A_NO_INSTRUMENT`/`_SHAPE_A_CORRECTIONS` override tables for the
confirmed-wrong subset) and `_repair_shape_a_special_cases()` (the 7
rows structurally outside the strict candidate filter -- their
heading_path wasn't a bare instrument name at all, so the general
function's filter never reached them).

**Two bugs caught and fixed during dry-run verification, before
production was touched**: (1) the fix tables were keyed by each entry's
*printed* list_number, but the code first matched on raw array
position -- wrong whenever a page's array continues a list from a prior
page (e.g. array position 1 = list_number "34.", not "1."). Found
because several corrections silently fell through to the plain-migration
branch on exactly those continuation pages. (2) the plain
`instrument`-correction branch set `instrument` but forgot to also clear
the now-wrong `heading_path`, found by spot-checking actual field values
in the dry-run CSV, not just row counts. Both fixed and re-verified
before applying to production.

Dry-run against `outputs/full_run/raw/*.raw.json` matched exactly: 751
migrated + 16 corrected = 767 (the full candidate count from a freshly
regenerated scoping query), plus 7 more special-case rows. Applied via
`parse_and_validate.py` -> `build_duckdb.py` -> `build_entities.py` ->
`build_research_model.py`. Verified: Musicians' empty-`instrument` count
dropped from 3136 to 2366 (770 recovered); coverage now 4699/7065 (67%),
up from 56% at the end of the #58 arc. `research.person_appearance`
unchanged at 21158 (pure field correction, zero rows added or dropped).
`research.person` moved 2934 -> 2897, the expected ripple effect from
entity-clustering re-running against corrected text (same pattern seen
in [[entities-person-cleanup-2026-08-27]]'s Мокѣевъ merge).

Post-fix spot-check via `research.person_appearance` cross-season
corroboration: Фридрихъ now reads "Кларнетъ" consistently 1890-91
through 1907-08 (previously wrong only in 1892-93); Царскій now reads
"Скрипка" consistently (previously wrong only in 1892-93); Розановъ,
Сиборъ, Эмме all internally consistent across every season each appears
in; Газенкампфъ/Голубевъ show a plausible real pattern (no instrument
printed in early years, one assigned later) rather than a fabricated
value.

**This closes the "shape A" migration issue #56/#57/#58 left open**:
Musicians `instrument` field coverage across the whole #54-#59 arc went
from 1200/7065 (17%) to 4699/7065 (67%).

**Not addressed, spotted in passing**: a second, distinct "Лудольфи,
Валентинъ Контрабасъ." person cluster (seasons 1893-94/1894-95, SP)
where "Контрабасъ." is fused directly onto the `first_name` field
itself -- a different bug on a different page
(not `musicians_1899-00_SP_p002`, the one fixed here) -- left for a
future pass. Also, RG flagged Сиборъ ("Скрипка. Солистъ балета.",
2026-08-27) as a likely guest artist worth a cross-corpus check later,
not yet done.

## 60. `tenure_note_text` -> `instrument` extraction -- direct follow-up to
#59, recovered 1854 rows corpus-wide (17% -> 93% Musicians `instrument`
coverage across the whole #54-#60 arc)

**Status: fixed.** RG asked why so many `instrument` fields were still
empty after #59; answering that question surfaced this. Unlike
`heading_path`, `tenure_note_text` behaves as a reliable verbatim
capture regardless of whether `instrument` was separately parsed out --
confirmed by comparing already-`instrument`-filled rows (which still
carry the same `"(съ ... г.). <Instrument>."` text in tenure_note_text)
against empty ones. Running the existing `_split_leading_instrument()`
helper against every empty-`instrument` Musicians row's tenure_note_text
(after stripping the leading tenure-date parenthetical) found 1854 of
2366 empty rows (78%) had a cleanly-recoverable instrument sitting
there, unextracted -- corpus-wide, not confined to the 19 shape-A pages.

**Verified before writing anything, same discipline as #54-#59**: 10
rows sampled at random across 10 distinct pages (of 52 total) checked
directly against scans -- all 10 correct. Then cross-checked all 1854
rows against every other Musicians row sharing the same (family_name,
first_name, patronymic) with a known instrument elsewhere: 1721 had such
a match, 1715 (99.65%) agreed exactly or via a known spelling/synonym
variant, leaving 6 genuine conflicts. Scan-checked all 6: 4 (Шолларъ x2
seasons, Табаковъ, Грибенъ) matched their own page's scan exactly -- the
"conflict" was a real cross-season difference (an instrument change
over a career, or two same-named different people), not an extraction
bug. The remaining 2 (Фишеръ/Франке 1-й, `musicians_1892-93_SP_p002`,
adjacent rows 76/77) were a confirmed genuine two-row swap -- the same
failure class as issue #59's Фридрихъ/Царскій swap, just manifesting in
tenure_note_text instead of heading_path.

**Deliberately conservative scope**: only ever fills `instrument` when
empty; never touches `tenure_note_text` itself (preserving the verbatim
transcription) or any trailing "remainder" text after the instrument
(e.g. Цабель's "Солистъ Двора Его Императорскаго Величества"). One
sampled row (Григоренко, `musicians_1892-93_SP_p003`) showed a
remainder -- "(см. оперный оркестръ)" -- that traced back to a genuinely
wrong `rank_or_title` value already present in the raw JSON, unrelated
to this fix (a stuck-run fabrication in a different field, same bug
class as the heading_path stuck runs, still open). Moving remainder
text into `rank_or_title` in this same pass would have risked
propagating that kind of error; instrument-only extraction doesn't.

Implemented as `_repair_tenure_note_instrument()` +
`_TENURE_NOTE_INSTRUMENT_CORRECTIONS` in `parse_and_validate.py`. Dry-run
caught one methodology bug before it mattered: an isolated call to just
the new function (skipping the pipeline's actual repair order) gave a
false 2304-row result, because several rows that get resolved by an
*earlier* repair (shape-A migration, etc.) looked empty in isolation.
Re-ran replicating the real per-page repair order and got the expected
1854; a full `parse_and_validate.py` dry-run into a scratch dir
confirmed the same number exactly before touching production.

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 2366 -> 512 (1854 recovered, exact). Coverage now 6553/7065
(93%). Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`.
`research.person_appearance` unchanged at 21158;
`research.person` unchanged at 2897 (no clustering ripple this time --
the fix never touches name/heading text, only `instrument`).

Post-fix spot-check via cross-season corroboration: Фишеръ now reads
"Віолончель" consistently across all 4 seasons (was wrongly "Кларнетъ"
only in 1892-93); Франке now reads "Кларнетъ" consistently (was wrongly
"Віолончель" only in 1892-93); Абрамовъ, Баулинъ, Володарскій,
Григоренко, Де-Ланге, Нагорнюкъ all internally consistent. Грибенъ now
visibly shows a genuine instrument transition across his career
(Ударные инструменты in the 1890s, Фортепіано from 1900-01 onward) --
previously hidden behind an empty field, not a data error.

**This closes the #54-#60 arc**: Musicians `instrument` coverage went
from 1200/7065 (17%) at the start to 6553/7065 (93%) by the end,
entirely through confirmed, scan-verified fixes.

**Still open, unrelated to this fix**: the ~512 remaining empty rows --
mostly genuinely non-instrumentalist people (conductors, the school
director, librarians, ballet répétiteurs, police superintendents,
students) plus confirmed cross-reference-stub losses (issue #27's ~40%
"(см. ...)" phrase-loss pattern); the Григоренко-adjacent `rank_or_title`
stuck-run fabrication noted above; the "Лудольфи, Валентинъ Контрабасъ."
fused-name cluster and the Сиборъ guest-artist cross-check, both carried
over unaddressed from issue #59.

## 61. Triaged the ~512 remaining empty-`instrument` rows -- recovered 58
more via 2 new pockets + 3 spelling variants; ~454 confirmed genuinely
non-recoverable

**Status: fixed (the recoverable part); the remainder confirmed
correctly blank, not a bug.** RG: "Let's work on these" (the ~512 rows
left after issue #60). Categorized all 141 distinct `heading_path`
values among the 512 by frequency rather than spot-sampling, which
surfaced two more recoverable pockets the prior sessions' filters missed
by construction, not by chance:

- **"Оркестръ / \<Instrument\>" and "Оркестр оперы и балета.
  \<Instrument\>."** (50 rows, exactly 2 pages:
  `musicians_1897-98_MSK_p000`, `musicians_1902-03_SP_p001`) --
  `heading_path` holds a genuine, information-bearing institutional
  heading (these pages also list non-orchestra roles under the same
  institution) with the instrument tacked onto the end as one compound
  value. Missed by issue #59's shape-A filter, which required
  `heading_path` to be *exactly* a bare instrument name. Every value on
  both pages checked directly against the scan. Unlike shape-A, the
  heading prefix is preserved (not blanked) -- it's real structure, not
  a stuck neighbor value.
- **3 unrecognized instrument spelling variants** in `tenure_note_text`:
  "Піанисть" (Гедике -- also already sitting in `heading_path`, just
  never recognized as an instrument by any prior filter), "Вальтгорнъ"
  (Сольскій), "Волторнъ" (Солодуевъ, distinct from the already-known
  "Волторна"). Each confirmed by scan.
- **5 rows recoverable from `tenure_note_text` but blocked by shape,
  not content**: a leading dual-role parenthetical before the date
  (Марквардтъ "Труба", Фарскій "Альтъ" -- both with strong existing
  cross-season corroboration), a malformed date-prefix punctuation
  variant (Терентьевъ "Скрипка", Сольскій "Вальдгорнъ"), and
  `_split_leading_instrument`'s own deliberate boundary-safety check
  declining a genuine split before a lowercase continuation (Смирновъ
  "Піанистъ при драматическихъ спектакляхъ.", scan-confirmed).
- **Крейнъ, Давидъ (2 rows)**: 7 prior seasons read "Первая скрипка";
  these 2 read "Концертмейстеръ" instead (a genuine promotion -- this
  era's "concertmaster" = principal first violin -- with no instrument
  re-stated). Deliberately did NOT infer "Первая скрипка" without direct
  textual support for these specific rows; relocated "Концертмейстеръ"
  to `rank_or_title` instead, `instrument` stays empty. Matches this
  project's standing rule against fabricating a plausible-but-unstated
  value.

**Confirmed correctly blank, not further recoverable**: répétiteurs
(ballet rehearsal coaches -- checked 3 scans directly; even though
répétiteurs are commonly pianists in real life, these entries genuinely
end at the tenure date with no instrument printed), including
Барминъ/Брындлинъ/Козловъ on `musicians_1901-02_MSK_p001`; Брекеръ's
specific 1905-06 season (unlike every other season of his, that one row
prints no instrument). Also spotted in passing, not fixed: 2
`family_name="Оставилъ службу [date]"` rows -- a fresh instance of the
already-documented issue #26 (non-person text captured as `person_entry`
rows), out of scope here.

Implemented as `_repair_heading_path_prefixed_instrument()`,
`_TENURE_NOTE_INSTRUMENT_HAND_FIXES` (extending
`_repair_tenure_note_instrument()`), 3 new `_KNOWN_INSTRUMENTS` entries,
and `_repair_tenure_note_title_relocation()` in `parse_and_validate.py`.
Dry-run into a scratch dir confirmed every count and spot-checked value
before touching production (see `docs/query_log.md` for the exact
numbers).

```sql
SELECT count(*) FROM raw.person_entry WHERE entity_type='Musicians'
  AND (instrument IS NULL OR trim(instrument)='');
```
Result: 512 -> 454 (58 recovered, exact match to the dry-run total).
Coverage now 6611/7065 (93.6%), up from 93.0% at the end of issue #60.
`research.person` unchanged at 2897; `research.person_appearance`
unchanged at 21158. Applied via `parse_and_validate.py` ->
`build_duckdb.py` -> `build_entities.py` -> `build_research_model.py`.

**This closes the #54-#61 arc**: Musicians `instrument` coverage went
from 1200/7065 (17%) at the start to 6611/7065 (93.6%) by the end.

**Still open**: ~454 remaining empty rows, genuinely non-instrumentalist
(conductors, school director, librarians, police, students) or confirmed
cross-reference-stub losses (issue #27); the "Лудольфи, Валентинъ
Контрабасъ." fused-name cluster (carried over from issue #59); the
Сиборъ guest-artist cross-check (RG, 2026-08-27); the 2
"Оставилъ службу"-as-family_name rows (issue #26). The Григоренко
`rank_or_title` stuck-value fabrication is fixed -- see issue #62.

## 62. Fabricated "(см. ...)" cross-reference note on 23 rows,
`musicians_1892-93_SP_p003` -- scoped and fixed

**Status: fixed.** RG: "The Григоренко rank_or_title stuck-value bug.
Let's fix this next" (carried over from issue #60/#61). Re-scoped fresh
rather than trusted from the prior note: the fabricated value no longer
lives in `rank_or_title` by the time `raw.person_entry` is built -- an
existing, independently-validated repair (`_repair_musicians_rank_or_
title`, issue #56, confirmed correct for 3048+ other rows) already
relocates any "(см. ...)" text sitting there into `tenure_note_text`.
Rescoped to `tenure_note_text ILIKE '%см%'`: 196 rows across 12 pages.

Classified all 196 by whether tenure_note_text carries its own
tenure-date prefix before the "(см. ...)" note: 173 (11 pages) have no
date of their own -- genuine cross-reference stubs pointing to the
Оперный оркестръ roster for their full record, matching the
already-confirmed Гуманъ/Добровъ shape from issue #57. The other 23 have
their own complete date+instrument record already printed -- and **every
one of those 23 is on a single page**, `musicians_1892-93_SP_p003`.

Confirmed by direct scan reading, not assumed from the classifier alone:
every one of the 23 has a clean, self-contained printed record with no
crossref anywhere nearby (e.g. Затценгоферъ: "(съ 24 сентября 1875 г.).
Фаготъ." -- nothing else) -- including a same-page cross-check that 7 of
the 23 (Абрамовъ..Вагнеръ) belong to an entirely different "Оркестръ
Александринскаго театра" list at the bottom of the same page, where a
crossref to the opera orchestra makes no structural sense at all, yet
still got the fabricated value. Confirmed the pattern is a one-page
artifact, not a recurring model bias, by checking the prior season's
identical-layout page (`musicians_1891-92_SP_p003`): same genuine
alternating stub/full-record convention, zero fabrications.

Traced the mechanism to the model's own raw JSON extraction, not a
repair-function bug: Григоренко's `rank_or_title` already reads "(см.
оперный оркестръ)" in `outputs/full_run/raw/musicians_1892-93_SP_p003
.raw.json`, before any repair runs. The model, working through a page
with dozens of genuine "(см. оперный оркестръ)" occurrences interspersed
with full records, appears to have gotten the phrase stuck and applied
it indiscriminately to rows that don't have it printed -- including onto
an unrelated second list on the same page.

Implemented as `_repair_fabricated_crossref_note()` +
`_FABRICATED_CROSSREF_NOTE_FIXES` in `parse_and_validate.py`, scoped to
exactly the 23 confirmed (page_id, list_number) pairs -- strips only the
trailing "(см. ...)" suffix, leaves `instrument` and everything else
untouched. Dry-run confirmed exactly 23 rows touched, all on the target
page, before applying to production.

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`. `research.person`
unchanged at 2897; `research.person_appearance` unchanged at 21158 (pure
text correction). Post-fix spot-check via cross-season corroboration:
Абрамовъ, Григоренко, Затценгоферъ, Парисъ, Эллингеръ all show their
real instrument consistently across every season, the fixed 1892-93 row
now indistinguishable from the rest; Гуманъ's genuine crossref record
confirmed unaffected.

## 63. "Лудольфи, Валентинъ Контрабасъ." fused-name cluster -- fixed by
generalizing `_repair_instrument_in_patronymic` to strip a trailing period

**Status: fixed.** RG: "The Лудольфи fused-name cluster. Let's also
check this." (carried over from issue #59). Confirmed the fused shape
(`patronymic="Контрабасъ."`) on 2 rows for Лудольфи
(`musicians_1893-94_SP_p001`/`musicians_1894-95_SP_p001`, list_number
"64.") -- one character (a trailing period) short of matching the
existing `_repair_instrument_in_patronymic()`'s exact-string check.
Corpus-wide re-check for the identical near-miss found 2 more rows for a
second person, Котте (same 2 pages, list_number "55."). All 4 confirmed
against the scan.

Generalized the check to `pat.rstrip(".") in _KNOWN_INSTRUMENTS`. Dry-run
found 10 rows touched across 6 pages, not just the 4 targeted -- cross-
checked all 10 against current production and confirmed the other 6 were
already correctly filled via a different repair path (a from-scratch run
just reaches the same value earlier); only the 4 targeted rows were
genuinely new content.

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`. Post-fix spot-check:
Котте reads "Фаготъ" consistently across all 15 seasons; Лудольфи reads
"Контрабасъ" consistently across all 8 seasons -- the fixed rows now
indistinguishable from the rest.

## 64. "Оставилъ службу"/"†" fragment person-entries -- scoped
corpus-wide (5 instances, 3 entity types) and merged into the entry
they belong to

**Status: fixed.** RG: "the 2 'Оставилъ службу'-as-name garbage rows.
And this one" (carried over from issue #61's triage -- turned out to be
a specific, recurring shape of the already-documented issue #26).
Corpus-wide search for a family_name matching a service-end/death-note
phrase found 5 instances (not 2), across 3 entity types: Musicians (x3:
`musicians_1891-92_MSK_p003` x2, `musicians_1897-98_SP_p001`),
Administration (`administration_1895-96_p001`), and TheaterSchoolStaff
(x2: `theaterschoolstaff_1902-03_p002`'s `family_name="†"`,
`theaterschoolstaff_1896-97_p000`). Confirmed by scan for every one: a
trailing note that belongs to the entry immediately above got mis-split
into its own fake "person" entry -- e.g. `musicians_1897-98_SP_p001`
entry 74 (Плацатка) prints "... Фаготъ. Оставилъ службу 1 октября 1897
г." as one continuous entry.

Also spotted, not fixed (out of scope for this repair): a distinct bug
on the same `theaterschoolstaff_1896-97_p000` page -- a real person,
Сперанскій, whose name landed in `heading_path` instead of
`family_name` on the entry right after the fixed one.

Implemented `_repair_fragment_person_entries()`, applied generally
alongside `_repair_roster()` (all roster entity types, not just
Musicians) -- merges the fragment's text into the preceding entry's
`tenure_note_text` and drops the fake row. Dry-run confirmed exactly 6
rows removed (all 5 flagged pages, `musicians_1891-92_MSK_p003` alone
contributing 2) via a content-level diff, not entry_id comparison (entry
IDs shift after any row removal, so a naive ID diff over-reports).

Applied via `parse_and_validate.py` -> `build_duckdb.py` ->
`build_entities.py` -> `build_research_model.py`. `raw.person_entry`
Musicians count 7065 -> 7062 (3 fake rows removed); `research.person`
2897 -> 2894 (small re-clustering ripple, expected);
`research.person_appearance` 21158 -> 21154. Post-fix spot-check via
`research.person_appearance`: Богуславъ, Захаровъ, Флоринскій, Шемаевъ
all show the merged note correctly, no separate fake entry remains.

**Noted, not investigated further**: `research.person_appearance` shows
Флоринскій's merged note duplicated within one row's text for the
1896-97 season, even though `raw.person_entry`'s own `tenure_note_text`
is confirmed correct (checked directly). A pre-existing derivation
quirk in `build_research_model.py` (likely double-pulling from
`person_entry_service`), not introduced by this fix, and outside
Musicians data -- left for a future look.

**Update, same day (see issue #65)**: the actual cause was found and
fixed -- not a `person_entry_service` quirk, but a second, independent,
pre-existing hardcoded SQL patch in `build_duckdb.py` for this exact
Флоринскій row, left over from before this fix existed. Removed.

## 65. tenure_note_text deep-dive: duplicate-fix bug, 2 more instrument
recoveries, a crossref-prefix extraction gap, and date-punctuation
normalization

**Status: fixed.** RG asked to see the raw Musicians CSV directly
("just musicians and their attendant fields... I want to see what it
looks like"), then worked through several findings while browsing it
in parallel with continued investigation here.

**1. Duplicate-fix bug.** Tracing the Флоринскій duplication noted (not
investigated) in issue #64 back to its source: `build_duckdb.py`'s
`tenure_note_text_clean` derivation had a pre-existing, hardcoded
one-off SQL patch for this exact row (entry_id-keyed, from before
`_repair_fragment_person_entries()` existed) that unconditionally
re-appended the same note every build, stacking with the new general
fix. Removed the stale branch (its sibling general-regex branch, which
handles a different, still-live shape, was kept).

**2. 2 more instrument-field-contaminated rows.** The SQL block's other
branch (`instrument LIKE 'Оставилъ службу%'/'Переведенъ%'`) revealed 2
Musicians rows where `instrument` itself holds a resignation/transfer
note instead of the real instrument, both on `musicians_1903-04_MSK_
p000`: Барсукъ-Самборскій (idx7) and Гейслеръ (idx19). Confirmed by
scan (p.113) and unanimous cross-season corroboration (13/15 other
seasons). Fixed via `_repair_instrument_service_note()` +
`_INSTRUMENT_SERVICE_NOTE_CORRECTIONS`, restoring the real instrument
and relocating the note to `tenure_note_text`.

**3. Crossref-prefixed instrument pattern.** 18 rows where
`tenure_note_text` reads "(см. оперный оркестръ). \<Instrument\>." --
a crossref note followed by the real instrument, missed because the
extraction only ever tried a date prefix. Confirmed by scan on both
affected pages (`musicians_1892-93_MSK_p003` p.99, entries 37-56;
`musicians_1891-92_SP_p002` p.63, entries 1-6), zero exceptions.
`_repair_tenure_note_instrument()` now also tries a crossref-prefix
regex when the date prefix doesn't match.

**4. "Why do only some tenure_note_texts have an instrument?" (RG's
question, answered with data, not assumption).** Of the empty-instrument
rows at that point, only 2/429 had ANY instrument word anywhere in
their own tenure_note_text -- confirming the other 98% genuinely reflect
non-instrumentalist roles (conductors, librarians, school
administrators, répétiteurs, students), not an extraction miss. The 2
exceptions were real, scan-confirmed misses (Фарскій -- a missing
closing paren stacked with a dual-role parenthetical; Стрекаловъ -- the
instrument sitting after a transfer note instead of right after the
date), both added to `_TENURE_NOTE_INSTRUMENT_HAND_FIXES`.

**5. "Is the punctuation variance real print variation or an
extraction artifact?" (RG's question, answered with data).** Classified
all 7014 non-blank Musicians `tenure_note_text` values by paren shape:
3987 fully correct, 1921 with no parens at all, 918 missing only the
opening paren. Checked two pages directly against the scan (one full
page, 50 rows, `musicians_1893-94_MSK_p001` p.100; one spot-check,
`musicians_1892-93_SP_p003` p.99) -- **zero exceptions**: the printed
page always uses full `"(съ ... г.)."`. Confirmed a pure extraction
artifact, not the book's own convention varying.

**Punctuation normalization implemented** (RG: "let's make sure the
clean version follows the (съ ... г.) convention") as a `regexp_replace`
step in `tenure_note_text_clean` (the `analysis` layer -- `raw` stays
verbatim, per RG's confirmed preference): `^\(?(съ (?:.+?г\. (?:по|и) )*
.+?г\.)\)?` -> `(\1)`. Validated against the full corpus before
deploying: correctly handles simple dates regardless of original paren
state; correctly captures 35 confirmed compound multi-period service
dates whole without over-matching (longest genuine capture 68 chars);
the non-greedy inner stop correctly prevents a malformed no-closing-
paren row from swallowing unrelated later sentences into the "date";
correctly leaves the 187 crossref/dual-role-prefixed rows untouched
(out of scope for this convention).

Applied via `parse_and_validate.py` (items 2-4) -> `build_duckdb.py`
(items 1, 5) -> `build_entities.py` -> `build_research_model.py`.
Empty-instrument count 429 -> 427 (Фарскій, Стрекаловъ recovered).
Coverage now 6635/7062 (94.0%). `research.person` 2894;
`research.person_appearance` 21154 (both unchanged from before this
round). Post-fix spot-check via `research.person_appearance`: all 4
newly-fixed people internally consistent across every season;
Флоринскій's merged note now appears exactly once, confirming the
duplicate-fix bug is resolved.

## 66. Instrument field fully overwritten by its own crossref note --
21 rows, `musicians_1891-92_MSK_p002`

**Status: fixed.** Found while investigating RG's deferred #65 question
("why do some musicians have start dates and some don't"). Of the 235
Musicians rows with no start date, all resolved to confirmed crossref
stubs (the real date lives on a different "home" page) -- 226 had visible
crossref text somewhere in the row; chasing the remaining 48 that looked
entirely blank surfaced this: on `musicians_1891-92_MSK_p002`, 21 rows'
`instrument` field held only the literal crossref note "см. оперный
оркестръ" (a `person_entry_service`/date field, not an instrument at
all), with the real instrument dropped from every field entirely.

Confirmed by direct scan reading (p.86): every affected row reads
"\<Surname\> (см. оперный оркестръ). \<Instrument\>." as one continuous
entry, e.g. entry 2, Альбрехтъ: "Альбрехтъ (см. оперный оркестръ).
Корнетъ." All 21 names and instruments hand-transcribed directly from
the scan. Fixed via new `_INSTRUMENT_CROSSREF_CORRECTIONS` +
`_repair_instrument_crossref_note()` in `parse_and_validate.py`:
relocates the crossref note into `tenure_note_text` (parenthesized,
matching the corpus-wide crossref-stub convention) and restores the
real instrument to `instrument`.

Dry-run matched expectations exactly on first attempt (21 rows, correct
page, correct values) -- applied to production
(`parse_and_validate.py` -> `build_duckdb.py` -> `build_entities.py` ->
`build_research_model.py`). Post-fix counts: `raw.person_entry` 21168
(unchanged -- no rows added/removed, only 21 corrected in place);
`entities.person_candidate` 0 pending (23 rejected); `research.person`
2894; `research.person_appearance` 21154 (both unchanged, as expected
for an in-place field correction). Spot-checked 4 of the 21
(Альбрехтъ, Гейслеръ, Лебедевъ, Петровъ) via `research.person_
appearance`: each crossref stub row's restored instrument matches that
same person's "home" entry instrument for the same season (1891-92) --
Корнетъ, Контрабасъ, Флейта, Скрипка respectively -- confirming the fix
is internally consistent, not just locally plausible.

## 67. `rank_or_title` split into `rank`/`title` (RANK vs TITLE), full
corpus-wide, plus three relocated exceptions

**Status: fixed, applied to production.** Triggered by RG asking whether
`instrument`'s raw-field-vs-derived-column reasoning (documented in
`docs/schema.md`) also applies to `rank_or_title`, then a live
corpus-wide exploration: "Maybe I need to understand better what
rank_and_title means across the corpus."

**Design (RG's own framing, confirmed against real data before
building):**
- **RANK** -- institutionally conferred status: civil/court Table-of-
  Ranks grades (`ст. сов.`, `колл. сов.`, `надв. сов.`...), military
  ranks (`полковникъ...`, abbreviated forms included), court honorifics
  (`Солистъ Двора Его Императорскаго Величества`), and -- confirmed by
  checking real examples, not assumed -- Academy of Arts distinctions
  (`академикъ`/`профессоръ`: every checked example already has the
  person's actual job sitting in `heading_path`, so these aren't
  occupation labels) and hereditary civil-estate status (`пот. поч.
  гражд.`).
- **TITLE** -- how the Yearbook labels the entry: occupational role,
  subject taught, workshop specialty.
- Two shapes belong to **neither**, and were relocated rather than
  tagged-and-dropped once RG pushed on this ("these exceptions really
  belong in other fields"):
  - BalletArtists' `1-я`/`2-я`/`3-я`/`4-я` -- RG correctly identified
    these as a name-disambiguator, not seniority; confirmed by query
    (every ordinal-bearing surname group on a page pairs a distinct
    patronymic with each ordinal) -- relocated onto `family_name_clean`
    (e.g. `Иванова` -> `Иванова 4-я`), the same convention already used
    corpus-wide (`Алексѣева 1-я`). Same bug class as the existing
    ordinal-misplacement fixes for first_name/patronymic just above in
    `build_duckdb.py` -- this one landed in `rank_or_title` instead.
  - Dual-role/cross-reference notes (`(онъ же и режиссеръ)`, `(см. СПБ.
    балетъ)`) -- relocated onto `tenure_note_text_clean`, same
    convention as the `instrument` crossref fix (#66). **RG asked to
    scan-check these before applying** ("Can we check these against the
    scans?") -- held out of the pipeline script entirely (not just
    unapplied) until scans became available mid-session, then verified
    across all 9 distinct people covering the 24 rows. Confirmed
    extraction accurate, and critically: **print order is NOTE then
    DATE** (e.g. "Вальцъ, Карлъ Ѳедоровичъ (онъ же и декораторъ) (съ 3
    октября 1861 г.)"), the reverse of a naive append -- the relocation
    SQL reconstructs that order rather than tacking the note on the end.

**One genuine residual, resolved by the same scan check**: raw `по
найму, Московскій пеховой` (2 rows, one person, Крыловъ, both 1902-03
and 1903-04 seasons) turned out to be an OCR misread -- "пеховой" isn't
a word; the scan (`ForUpload_1902-03_Spisok_Administration.pdf` p.128)
reads "Московскій цеховой" (a craft-guild/artisan civil-estate
designation). Fixed at the raw layer via a new `_OCR_MISREAD_CORRECTIONS`
+ `_repair_ocr_misreads()` in `parse_and_validate.py`. **Caught a real
bug while building this fix**: `list_number` alone isn't a safe key on
these two pages -- both restart numbering per sub-list, so idx 1 on
`administration_1902-03_p004` collided with a different real person
(Балахнинъ); a first draft silently overwrote his genuine `губ. секр.`
rank with Крыловъ's corrected value. Fixed by requiring every field to
match its expected *current* value before applying the correction, not
just the list_number.

**Implementation**: three new `analysis.person_entry` columns
(`build_duckdb.py`) -- `rank_clean`, `title_clean` (pure SQL derivation
over `raw.person_entry`, unchanged/verbatim), and
`rank_or_title_excluded_reason` (audit-only, RG confirmed it stays out
of `research`: `'name_disambiguation_ordinal'` /
`'dual_role_or_crossref_note'`). `research.person_appearance`'s
`rank_or_title` column replaced with `rank`/`title` (matching the
existing convention where `research` surfaces the clean value under a
plain name, e.g. `instrument_clean` -> `instrument`).

**A real DuckDB gotcha hit building the classification regex**: RE2 (v1.5.5)
does not treat Cyrillic letters as `\b`/`\w` word characters -- a
Cyrillic-aware boundary check (`\bсов`) silently matched nothing at all,
and a naive `\w*` after a Cyrillic prefix (`Солист\w*`) also failed to
extend into the following Cyrillic letters. Fixed with explicit Cyrillic
character classes (`[^а-яёіѣѳѵА-ЯЁІѢѲѴ]` for the boundary,
`[а-яёіѣѳѵА-ЯЁІѢѲѴ]*` in place of `\w*`) -- confirmed against a case that
specifically needed the negative boundary check to hold: `Рисованіе`
(drawing, a genuine TITLE) contains "сов" mid-word and must NOT match.

**Validation, before any code was applied**: a Python reference
classifier was built and iteratively hardened against real corpus
values, then translated to SQL and cross-checked row-by-row --
**0 mismatches across all 2208 non-blank `rank_or_title` values
corpus-wide**. Full pipeline chain (`parse_and_validate.py` ->
`build_duckdb.py` -> `build_entities.py` -> `build_research_model.py`)
dry-run three times on scratch DB copies as the design evolved (ordinal
relocation added, then the scan-confirmed note relocation + OCR fix),
clean every time, before touching production.

**Final counts** (`analysis.person_entry`): RANK 1688, TITLE 472,
EXCLUDED 48 (24 ordinal relocated to `family_name_clean`, 24 note
relocated to `tenure_note_text_clean`) -- 1688+472+48 = 2208, matching
the total non-blank `rank_or_title` count exactly, confirming no row
silently disappeared. `research.person`/`research.person_appearance`
counts unchanged (2894/21154) as expected for an in-place, additive
schema change. `entities.person_candidate`: 0 pending, 23 rejected
(clean). Documented in `docs/schema.md`'s `rank_or_title` row.

## 68. Repertoire spurious-curve smoketest: multi-modal cross-check
tested for real, one confirmed-spurious page corrected to
confirmed-real after tighter re-verification

**Status: mixed result -- detect-and-repair strategy shows real
promise but has a real gap; one item in issue #51's 7-page confirmed-
spurious list was wrong and is now corrected.**

Direct follow-up to #51/#1's smoketest: tested the row-level-vs-
baseline cross-check against `repertoire_1898-99_p029`, a page believed
(from #51's 7-page survey) to have a genuinely spurious curve at "26
Пятница." Ran row-level extraction on the page's raw (uncorrected)
automatic boundaries and diffed every date/theater/receipts cell
against the existing full-page baseline.

**Real damage confirmed, not a clean pass**: the spurious split caused
cross-date content bleed, not just local corruption -- "25 Четвергъ"'s
morning receipts (Конекъ-Горбунокъ 1260.33/Усмиреніе строптивой
1093.90/Каширская старина 378.89) got mislabeled as "24 Среда," leaving
the real "25 Четвергъ" row incomplete. The cross-check caught this: 9
of 15 date/theater comparisons flagged DISAGREE, correctly surfacing
every wrong cell. Day-of-week validation, by contrast, would NOT have
caught this -- "24 Среда" is still an internally valid date/weekday
pair; only the *content* attached to it is wrong.

**RG proposed a third, orthogonal check: column-wise extraction** (read
one theater straight down the whole page instead of one date across a
row) -- structurally immune to the row-boundary problem, since it never
needs a row crop at all. Built real vertical-divider detection for this
(`_table_x_bounds` alone isn't enough, per its own docstring -- reused
`_detect_line_curves` on a *transposed* image, since a vertical line's
x-sway becomes a horizontal line's y-sway once transposed, exactly the
shape the existing curve-tracer already handles). Found 5 real
dividers + 2 margin/binding artifacts, visually confirmed.

**Column-wise extraction is not a silver bullet either.** Большой
театръ came back 100% correct in the first (composite date+theater
crop) attempt; Малый/Новый showed a *different* real error: an
off-by-one date-boundary shift. Initially attributed this to Большой
sitting immediately adjacent to a single shared date/УТРО-ВЕЧ label
column, with Малый/Новый further from it -- **RG corrected this**:
УТРО/ВЕЧ is not one shared label tied to the date column. It's a
per-cell subdivision marker that can occur independently inside *any*
theater's own column, since each theater's printed content for a date
can independently split into morning/evening -- there's no single
"the" label for a row. That reframes what actually needs fixing: the
composite crop's visual-gap artifact (diagnosed at the time and still
real -- the date-label-to-content relationship gets visually unnatural
once an intervening theater column is cropped out) is confirmed as
*a* cause, but "distance from a shared label" is not the right
mechanism and shouldn't be repeated as the explanation. RG is treating
per-cell УТРО/ВЕЧ subdivision as **its own separate, deferred issue**,
not something resolved by the fix below.

RG's fix for the composite-gap problem: separate crops for the date
column and each theater column (no composite gap), matched by list
position afterward rather than by asking the model to re-attribute a
date per theater.

**Honest limitation found in the row-vs-column cross-check itself**:
at "24 Среда," row-level AND column-level made the *identical* wrong
attribution (both borrowed 25 Четвергъ's morning receipts). Two
methods agreeing is not proof of correctness when both share the same
underlying visual ambiguity. A 3rd leg (the full-page baseline, or the
date-only/theater-only split above) is needed to close this specific
gap -- 2-way agreement alone isn't sufficient.

**Correction to #51's 7-page list, caught by this same investigation**:
building the date-only column extraction for `p029` surfaced a
discrepancy -- it should have found 4 compound (УТРО/ВЕЧ) dates among
the 10, and found 0. Cross-checking led to re-examining the original
"curve 12 is spurious" claim for this page directly against the clean
scan: **there IS a real printed rule there** -- "26 Пятница" genuinely
is compound (Жизнь за Царя/Марія Стюартъ/Вій УТРО, Бенефисъ
кордебалета+... ВЕЧЕРЪ), confirmed by direct visual inspection. The
original claim (made during #51's fast visual-triage pass, "cutting
through a plain non-compound row") was a real misreading, not a
detector error at all. **`p029` is removed from the confirmed-spurious
list.**

Re-verified the remaining 6 pages from #51's list with a stricter
method this time (the *exact* detected curve drawn as an overlay on a
tight crop, not just an eyeballed wide zoom) specifically to check for
this same class of error. All 6 held up: `p019` (real for Малый's own
УТРО/ВЕЧ split, spurious for Большой/Новый's un-split single-session
listings), `p028`/`p030` (real for 2 of 3 theaters, spurious for
Михайловскій's continuous un-split column), `p036`/`p037`/`p039` (fully
spurious, cutting through dense Pushkin-jubilee multi-line commemorative
programs with no internal structure at all). **Corrected confirmed
list: 6 pages, not 7** -- `p019`, `p028`, `p030`, `p036`, `p037`,
`p039`.

**Lesson for future verification passes on this issue**: a wide
eyeballed zoom is not precise enough to confidently call a curve
"spurious" -- draw the actual detected curve coordinates on the crop
and check pixel-level alignment against any printed rule, every time,
not just for a first pass.

**Addendum: separate date-only/theater-only crops, position-matched --
tested, and it fixes Малый/Новый's off-by-one shift completely.** RG's
proposed refinement (keep the date column, since row boundaries aren't
always available to lean on -- but crop it separately from each theater
rather than compositing them with a gap, and match by list position
instead of asking the model to re-attribute a date per theater).

First attempt at the date-only crop undercounted (10 rows instead of
14) -- the crop's right edge clipped the sideways УТРО/ВЕЧ labels
almost entirely. Widened the crop and it immediately found all 14 real
rows correctly, labeled with the right session (morning/evening).
Theater-only crops for Малый/Новый (no date column at all) also
correctly found 14 rows each. Zipped all three by list position and
checked against the known-correct scan values for the problem region
(24-26): **all 14 rows matched exactly** for both theaters -- the
off-by-one shift from the composite-crop version (known_issues.md #68)
is gone. One apparent mismatch during comparison turned out to be a bug
in the comparison script's own truth table (an evening value
mis-indexed as morning), not an extraction error -- corrected, and the
result is a clean match once fixed.

**Practical implication**: for column-wise extraction to work
reliably, the date column and each theater column should be extracted
as separate images and matched by position, not composited side by
side with a theater skipped over in between. Not yet tested on other
pages -- next step if this generalizes.

**New, separate, deferred issue surfaced along the way (not fixed
here)**: УТРО/ВЕЧ is a per-cell subdivision, not a single label shared
across a row -- any one theater's cell can independently split into
morning/evening while its neighbors on the same date don't (or split
differently), confirmed by RG directly (corrects an assumption made
earlier in this same investigation, see the addendum above). Detecting
this per-cell, per-theater, rather than assuming one shared row-level
session structure, is its own open problem -- not addressed by the
date-only/theater-only split fix, which only fixes the composite-crop
visual-gap artifact. RG: "happy to deal with them as a separate
issue" -- explicitly deferred, not blocking.

**Addendum: generalization test on a second confirmed-spurious page
(`repertoire_1898-99_p037`), same date-only/theater-only split
approach.** Deliberately different failure shape than `p029` (no
УТРО/ВЕЧ anywhere on this page -- isolates the dense-Pushkin-program
failure cleanly from the deferred per-cell subdivision issue above).
Ground truth re-established directly from the scan (11 dates, 5 dark,
including the tricky "20 Вторн" benefit-performance row: a 2-line
heading+title block with no receipt number at all).

**Большой and Малый: 100% correct across all 11 rows**, including the
exact dense Pushkin-jubilee program that caused this page's original
spurious-curve problem, and the 2-line benefit-performance entry
(correctly recognized as one row, not split). Confirms the approach
generalizes past the single page it was built on.

**Новый: one new, different error** -- split "20 Вторн"'s 2-line
benefit heading+title (no receipt) into two separate output rows
instead of one, shifting its own position-count by one for every row
after that point. Not a recurrence of the original spurious-curve
problem (this is a column-wise extraction issue, not a row-boundary
one) -- a real, separate failure mode: a title block with no receipts
number is apparently more likely to get mis-split than one with a
receipts line anchoring it as clearly "one row." Worth a targeted
prompt fix (state explicitly that a shared-heading multi-line block
with no receipts is still one row) if this pattern recurs elsewhere.

**Addendum: attempted prompt fix for Новый's no-receipts-row split on
`p037`, paused as too narrow to chase further.** Tried a broader
"multi-line content is still one row" prompt rewrite -- made it worse,
not better (6 rows instead of the correct 11, plus a fabricated
duplicate receipts figure), while leaving Большой/Малый's already-
correct output unchanged. Resampled both prompt versions 2-3x each:
both are fully reproducible (12 rows every time / 6 rows every time),
ruling out random sampling noise -- this is a real, stable
misreading, just one that shifts depending on exact wording, on an
image that's visually unambiguous when checked directly (11 rows and
1 clean boundary each, confirmed by eye). Working hypothesis, untested:
Новый's crop has a notably more extreme aspect ratio (~1:5.4) than
Большой/Малый's, which stayed correct under both prompts -- crop shape,
not wording, may be the actual variable. **Paused here at RG's
request** -- too narrow a rabbit hole for one page's one theater
column relative to the value of chasing it further right now.

**Addendum (2026-09-01): the row-vs-column-vs-page cross-check built into
real pipeline code and validated end to end, not just scratch scripts.**

- `pipeline/row_detect.py`: `_detect_vertical_dividers()` (transposed-
  image reuse of `_detect_line_curves`, same technique as the addendum
  above) + `detect_columns()`, writing a date-only crop and one theater-
  only crop per theater (separate files, matching the composite-gap fix
  validated earlier). Bug caught and fixed while building this: an
  x-bounds tolerance that worked on `p029` gave 4 theater columns
  instead of 3 on `p037` (a real divider sitting just outside the naive
  margin estimate on one side, artifacts sitting just inside it on the
  other) -- fixed with an asymmetric tolerance (small on the left, none
  on the right), re-verified 3/3 on both pages.
- `pipeline/schemas/repertoire_columnwise.py` (new): `DateOnlyPage`/
  `TheaterOnlyPage` schemas + `merge_columnwise_page()`, which returns
  `None` (not a best-effort partial zip) on a length mismatch between a
  theater's row count and the date column's own -- a real signal, not
  guessed at.
- `pipeline/prompts/repertoire_dateonly_system.txt` /
  `repertoire_theateronly_system.txt` (new): the theater-only prompt
  deliberately does NOT include the "don't split multi-line content"
  framing tried as a fix earlier -- that version regressed WORSE on the
  one known edge case (a benefit-performance row with no receipts) than
  the original, simpler prompt, confirmed reproducible on both versions
  across multiple samples. The known gap is documented directly in the
  prompt file instead of chased further.
- `pipeline/run_pilot.py`: `process_page_columnwise()` + `--column-level`
  CLI flag, mirroring `process_page_rowlevel()`'s conventions (own usage
  log file, own crops directory, same semaphore discipline).
- `pipeline/quality_checks.py`: `check_repertoire_cross_extraction()`,
  comparing whatever subset of {page, row, column} raw JSON exists per
  page, recording every source's actual value in `detail` rather than
  collapsing to a flag (RG: "we'll take careful note of any
  disagreements, whether it's between 2 or 3 of the reads").

**Validated end to end on `repertoire_1898-99_p029`** via the real CLI
(not scratch scripts): generated a fresh baseline copy, a fresh row-
level extraction, and a fresh column-wise extraction, then ran the
cross-check against all three. Result: 36 disagreements flagged, 100%
of them in the compound-date region (21/24/25/26 Feb) where real
problems were already known to exist; 0 disagreements among the 6
simple dates -- confirmed by spot-checking specific flags against the
raw row-level JSON directly, not assumed: the fresh row-level run (using
automatic, uncorrected boundaries) genuinely produced duplicate blank
"unspecified" session rows AND separately mislabeled its real values as
"unspecified" instead of "morning"/"evening" for several compound
dates, while column-wise correctly split and labeled the same dates
throughout. The check discriminates real agreement from real
disagreement rather than firing indiscriminately.

**Not yet done**: run at any larger scale than one page; decide the
production wiring (does `--column-level` become a routine second pass,
or only run on pages a cheap screening signal flags first); decide what
happens automatically when a page IS flagged (currently: nothing, it's
a QC signal for human review same as every other flag in this file, not
an auto-repair).

**Decided (RG, 2026-09-01): `--column-level` runs as a routine second
pass on every Repertoire page, not gated behind a screening signal.**
Cost isn't the constraint here (RG, same session: "Cost is not an issue
for this problem. But I do want to make sure I have as accurate data as
possible") -- with that tradeoff settled, running the full row+column
(+page baseline where available) cross-check on every page maximizes
the signal rather than only sampling pages a cheap, imperfect heuristic
happens to flag. See CLAUDE.md's pipeline section for the concrete
per-run command sequence this implies.

### Addendum (2026-09-01): whole-season test surfaced a real
`detect_columns` bug at scale, fixed; 78% of pages now split cleanly, a
smaller residual gap documented rather than chased further

Ran `--column-level` across the whole 1898-99 season (40 pages) for the
first time, per RG: "Can we test it on a whole season first?" Row-level
extraction succeeded cleanly on all 40/40 pages. Column-wise extraction
did not: only 5/40 pages came back fully `"ok"`, 32 came back
`"partial"` (at least one theater dropped by `merge_columnwise_page`'s
length-mismatch guard), and 3 (`p008`, `p012`, `p014`) failed outright
with `"column_detect_failed"`. Investigated both failure modes.

**`column_detect_failed` (3 pages) -- root cause and fix.** Direct
inspection of `_detect_vertical_dividers`'s raw candidates on all 3
pages found only 2 candidates each, both clustered on the right side,
zero anywhere across the left ~65% of the table. Read the actual scan
for `p012` directly (a normal, cleanly-printed "С.-Петербургскіе
театры" page, Маріинскій/Александринскій/Михайловскій, visually
identical in structure to already-working pages) -- ruling out scan
damage as the cause and pointing at the detection code itself.

Traced it to `_detect_line_curves`'s edge-artifact drop (added 2026-08-
27 to reject a photographed book-cover chain sitting right at a scanned
page's top/bottom edge) being reused, via `_detect_vertical_dividers`'s
transpose trick, on an axis where that assumption doesn't hold: a
vertical table's own left/right border can legitimately sit within a
few pixels of the crop's own edge on a tightly-cropped page, unlike a
horizontal row line photographed at y≈0. Confirmed directly:
`p012`'s real left border chained at 33/40 strip presence -- stronger
than either divider the page's old code DID keep -- and was being
silently dropped by exactly this filter.

Fixing the direct symptom exposed a bigger design question: was
detecting the table's own true outer border ever the right thing to
need? Redesigned around "no": `detect_columns` now only needs the
INTERNAL column dividers (date|theater-1, theater-1|theater-2, ...) --
the date crop's left edge and the last theater crop's right edge simply
extend to the image's own edge, exactly the same generous-padding
tolerance already used for `date_pad`/`theater_pad` elsewhere in that
function. This also explains a second, worse bug found on `p024` in the
same investigation: the same outer-border fragility had caused the
wrong divider pair to be picked, and `detect_columns` had silently
produced a full THEATER column ("Александринскій театръ.", complete
with works/receipts) where the date-only crop was supposed to be --
confirmed by reading the mis-cropped image directly. A
wrong-but-plausible result is worse than an honest failure; not needing
the outer border at all removes the whole class of bug, not just this
instance of it.

Getting the internal-only redesign correct took three more rounds of
direct measurement, not assumption:

1. **A lower `presence_frac` for the vertical case specifically**
   (0.55, later 0.45 -- see below): a genuine internal divider on `p012`
   chains at only 25/40 (62.5%) strip presence, well below
   `_detect_line_curves`'s row-detection default of 0.7 (tuned for
   horizontal lines running through mostly-open cells, not vertical
   ones cutting through print-dense columns). Every noise candidate
   measured stayed under ~28%, so there's a comfortable gap to lower
   into.
2. **A width-based test to drop a leading divider that's actually the
   outer-left border**, not density-based. Density was tried first and
   rejected: a margin segment contaminated by a photographed fingertip
   or the book's own spine (both confirmed directly, on `p008` and
   `p029` respectively) can read as dense as, or denser than, real
   text, so no single density ratio (1.2 through 2.5 all tried)
   separated every confirmed case without misclassifying another one on
   a different page. Column width doesn't have this problem: every
   genuine date column measured across the test set came out 175-185px,
   every genuine theater column 508-598px -- a clean, non-overlapping
   split, since it's fixed by the table's own typesetting rather than
   by what a camera or thumb happened to catch that day. If the segment
   right after the first divider falls in that date-column width range,
   the first divider is the outer border and gets dropped.
3. **A density-based test for the trailing divider** (ratio 1.8, tuned
   down from 2.5 once the width fix was in place): the analogous
   "predictably-sized next segment" test doesn't apply on the right --
   past the true right border there's just margin or, on `p029` and
   `p037` independently, the photographed book spine (~31-33% ink, far
   above the ~4-9% band every real column sits in on those same pages)
   -- so this side keeps density, compared against the median of the
   page's own middle segments rather than a fixed global percentage.

One implementation bug caught and fixed along the way: an early version
of the pruning function looped, re-merging a dropped edge divider's
segment into its neighbor and re-testing the larger merged segment. It
cascaded on both `p029` and `p037` -- once the binding-artifact segment
got absorbed into its neighbor, the merged segment's average was still
pulled high enough to trip "outlier" again on the next pass, eating a
second, genuinely real divider along with it. Fixed by deciding both
edges once each, from a single reference computed up front.

**Re-verified against all 6 pages involved in this investigation**
(`p012`, `p008`, `p014`, `p024`, plus the two originally-validated pages
`p029`/`p037`, to check for regressions): all 6 now detect exactly the
correct 3 theaters, confirmed both by divider count and by directly
viewing the resulting date-only crop for `p024` (previously showing
wrong theater content, now correctly showing "Мѣсяцъ, день и число").

**Re-ran `detect_columns` (the free, local step -- no API calls) across
all 40 pages of the season** to check how well this generalizes past
the 6 pages used to build it: 0 outright failures (down from 3), 31/40
pages detect exactly 3 theaters. The remaining 9 show a 4th (8 pages)
or only 2 (1 page) -- a genuinely different, harder failure mode than
what got fixed: on `p020` (checked directly), the missing date/theater-1
divider doesn't chain at low presence, it doesn't chain AT ALL -- no
candidate appears anywhere near that position in the raw strip data,
apparently because dense printed text right at that column boundary
washes out the vertical line signal across most of the page's height,
not merely weakens it. This isn't a threshold-tuning problem the way
the fixed bugs were; there's no presence floor to lower into when the
line was never detected as a candidate in the first place. Left
undiagnosed further and documented here as a bounded, known gap, matching
how this file already handles the Новый no-receipts-row bug earlier in
this same addendum -- not chased to zero in one session. The row/column/
page cross-check (`check_repertoire_cross_extraction`) remains the
downstream safety net for whichever of these 9 pages get run: a wrong
divider split still produces a row-count mismatch against the date
column, which `merge_columnwise_page` already refuses to guess through.

**Not yet done**: re-run the full (paid) column-level extraction on the
whole season with the fixed `detect_columns` to get real
extraction-quality numbers (the original 45.9%-theater-success figure
was measured against the buggy version and is now stale); characterize
whether the 32 originally-`"partial"` pages' row-count mismatches are
the already-known Новый-style bug recurring at scale or something else
-- not yet investigated this session.

### Addendum (2026-09-01): ran the cross-check across the full season
on the pre-fix columnwise data anyway (as a baseline/row-level
comparison), and it surfaced a genuine NEW bug -- a row-level off-by-one
shift on `p012`

The whole-season `--column-level` background run (`raw_columnwise/`)
had already finished before the `detect_columns` fix above was written,
so its data reflects the OLD buggy divider detection, not the fix --
re-running it is still outstanding (see previous addendum). Ran
`check_repertoire_cross_extraction` across all 40 pages anyway
(`raw_baseline`, `raw_rowlevel`, `raw_columnwise`) to get what signal
was available now rather than wait, and to validate the check's
reliability at scale before re-running the paid column-level step.

**1,200 flags across 37/40 pages -- but the raw count is misleading
without breaking it down.** Categorized every flag by which of the
three sources actually disagreed:

- 729/1200 (61%) are `column: '<missing>'` with page and row AGREEING
  with each other -- purely the already-diagnosed, already-fixed-in-code
  columnwise divider bug (a theater dropped by
  `merge_columnwise_page`'s length-mismatch guard), not new information.
  Re-running column-level with the fix should collapse most of this
  category.
- 390/1200 (32.5%) are one of {page, row} missing a cell the other has
  -- plausibly related to the same stale columnwise run or to row-level's
  own known row-boundary issues; not individually triaged this session.
- 39/1200 (3.25%) are genuine PAGE-vs-ROW disagreements where BOTH
  sources have a value and they differ -- the most informative category,
  and the one spot-checked directly against a scan.
- 42/1200 (3.5%) other/mixed patterns, not triaged.

**Spot-check confirmed a real, new bug**: on `repertoire_1898-99_p012`,
three consecutive page-vs-row disagreements in the Александринскій
column --
`{page: '1651 р. 60 к.', row: '1653 р. 60 к.'}` (16 Понед.),
`{page: '1658 р. 55 к.', row: '1651 р. 60 к.'}` (17 Вторн.),
`{page: '1262 р. 75 к.', row: '1658 р. 55 к.'}` (18 Среда) --
verified directly against the scan: PAGE is correct at all three
positions (1651.60 / 1658.55 / 1262.75, matching the printed table
exactly), and ROW-level is reporting each row's value one row LATE --
i.e. row N's row-level read is actually row N-1's true value. This is a
different mechanism than the divider-detection bug fixed above (it's
`row_detect.py`'s horizontal row-boundary curves, not
`_detect_vertical_dividers`) and a different page than any previously
confirmed row-shift case -- a genuinely new finding, exactly the kind of
signal this cross-check exists to surface, not an artifact of the stale
columnwise data. Not yet root-caused or scoped beyond this one page.

**Reliability read on the cross-check itself, now tested at 40-page
scale rather than 1**: the check does NOT produce a flood of
undifferentiated noise -- the categorization above shows the "real"
signal (page-vs-row disagreement) is a small, distinct slice (3.25%)
separable from the mechanical columnwise-bug noise (61%) by simply
checking whether the two non-missing sources agree. That's a good sign
for using this at production scale, though it also means a naive
"1,200 flags" headline number would have been actively misleading
without this breakdown.

**Not yet done**: root-cause the `p012` row-level shift and check
whether it recurs on other pages; triage the 390 "one source missing"
flags; re-run column-level with the `detect_columns` fix and redo this
whole categorization on fresh data, since the 61% "known bug" bucket
should mostly disappear and change the real proportions.

### Addendum (2026-09-01): root-caused the `p012` row-level shift --
same underlying weakness as the vertical-divider bug, confined to 2/40
pages in this season, cheaply detectable without any new API calls

RG: "I want to know the root cause, but only so far as it might apply
to other pages." Checked `p012`'s row-crop manifest
(`raw_rowlevel/row_crops/repertoire_1898-99_p012/`, already on disk
from the earlier run -- no new API cost needed) and found only 2 row
crops for the whole page, one spanning 1,245px (versus ~180-220px for a
normal single row and ~600-690px for the tallest confirmed-genuine
compound row on the two already-validated pages, `p029` and `p037`).
That one oversized crop covers roughly ten real dated rows (15 through
24) crammed into a single model call.

That's the exact failure mode `row_detect.py`'s row isolation was built
to eliminate in the first place (see this file's original `#1`
investigation and this module's own top-of-file docstring: isolating
one row with zero neighboring dated content eliminated a confirmed,
reproducible misattribution bug; anything less than full isolation
reopens the door to it). Confirmed directly in `p012`'s raw JSON: dates
15-18 appear TWICE, the second pass's receipts values shifted one row
from the first -- the exact mechanism behind the page-vs-row
disagreements the cross-check flagged.

Root cause: `_detect_line_curves`'s `presence_frac=0.7` default -- the
SAME default already found too strict for vertical-divider detection on
dense pages (see the earlier addendum this session) -- also drops
genuine HORIZONTAL row boundaries on this page. Direct measurement:
three real-looking, evenly-spaced candidates in the missing region
(y=1991 at 52.5% presence, y=2175 at 42.5%, y=2357 at 57.5%) all sit
below 0.7 and get dropped, while the page's row detection was never
touched by this session's vertical-divider fix (that fix only lowered
`_detect_vertical_dividers`'s own presence_frac, calling
`_detect_line_curves` with a separate value -- row-level detection
still uses the 0.7 default everywhere).

**Scope, checked cheaply across all 40 pages using data already on
disk** (row-crop counts and heights from the existing
`raw_rowlevel/row_crops/*/​*__rows_manifest.json` files -- no new API
calls): every page normally gets 9-13 row crops with a max single-crop
height at or under ~730px (matching the two independently-validated
good pages, `p029`: 607px max, `p037`: 689px max). Exactly two pages
break that pattern: `p012` (2 crops, 1,245px max) and `p014` (6 crops,
878px max) -- confirmed `p014` shows the identical signature directly
in its raw JSON (one date, "26 Четвергъ", duplicated 6x across all 3
theaters). Two other pages with a below-typical crop count (`p018`,
`p020`, 7 each) were checked and are NOT the same bug -- their max
crop height (703px, 682px) sits inside the normal range; their lower
count is plausibly just a shorter date range printed on those specific
pages, not a detection failure.

**Bottom line for applicability**: this is not a pervasive problem --
2/40 pages (5%) in this season show it, both cheaply identifiable in
advance (anomalous row-crop count/height, no extraction cost) rather
than only discoverable after the fact via the cross-check. Not fixed
this session (would mean lowering `presence_frac` for
`_detect_line_curves`'s row-detection call sites too, mirroring the
vertical-divider fix, and re-validating against `p029`/`p037` the same
way to avoid a regression there) -- documented here as a scoped,
bounded, cheaply-detectable gap rather than fixed on request, since RG
asked specifically for root cause and scope, not a fix.

### Addendum (2026-09-01): fixed -- `detect_rows` gets its own lower
`presence_frac`, mirroring the vertical-divider fix

RG: "Okay, let's fix it now." Added `presence_frac: float = 0.5` to
`detect_rows` (was hardcoded to `_detect_line_curves`'s 0.7 default,
untouched by the earlier vertical-divider fix, which only lowered
`_detect_vertical_dividers`'s own call). 0.5 was chosen empirically, not
guessed: it's the smallest tested value that recovers all three real
missing boundaries on `p012` (42.5%/52.5%/57.5% presence) while leaving
`p029` and `p037` detecting the EXACT SAME curves as before (verified
directly, not assumed) -- confirmed noise on every page checked topped
out under ~22.5%, so there's a comfortable margin on both sides at 0.5.

**Re-scanned all 40 pages locally** (the free `detect_rows` step, no API
calls) to confirm the fix generalizes past the 2 pages used to find it:
0 failures, and the worst max single-crop height across the WHOLE
season is now 729px -- no page exceeds the ~730px ceiling already
established as normal from the two independently-validated pages
(`p029`: 611px here, `p037`: 681px here, both structurally unchanged
from before the fix). `p012` went from 2 crops/1,245px max to 11
crops/712px max; `p014` went from 6 crops/878px max to 10 crops/676px
max -- both now squarely inside the normal range.

**Not yet done**: re-run the actual (paid) row-level extraction on
`p012`/`p014` (or the whole season) with the fixed `detect_rows` to
confirm the duplicate/shifted-receipts symptom is actually gone, not
just the oversized crop that caused it -- the local re-scan above only
confirms the boundaries are now reasonable, not that a fresh model call
against the new crops reads correctly end to end.

### Addendum (2026-09-01): ran the real (paid) row-level extraction on
`p012` and `p014` -- `p012` fully fixed, `p014` reveals a subtler,
different problem than the one that was fixed

**`p012`: clean.** Fresh row-level extraction, verified directly against
the scan: all three previously-shifted Александринскій values now
correct (1651 р. 60 к./16 Понед., 1658 р. 55 к./17 Вторн., 1262 р. 75
к./18 Среда), no duplicated dates anywhere in the output. The
`presence_frac` fix resolved this page completely.

**`p014`: the row-boundary fix only partially closed the gap, and what
remains is a different failure mode than the one diagnosed and fixed.**
9 crops now bound single real rows correctly (185-230px, matching
normal), but ONE crop (`row010`, y=[2361,3037], 676px -- the same height
that looked "normal" in the free/local re-scan and was wrongly judged
fine on height alone) still spans SEVEN real calendar dates (26
Ноября through 4 Декабря) plus the two dates that bookend it (25
Ноября, 5 Декабря) in one image. Confirmed directly in the raw chain
data: unlike the boundaries the `presence_frac=0.5` fix recovered, this
region has NO candidates at all across most of its span (a handful
under 25% presence near the top of the gap, then literally nothing from
y≈2537 to y≈2992) -- the same "genuinely invisible in the raw signal"
limitation class already documented for `_detect_vertical_dividers`'s
remaining 9 pages, not a threshold that could be lowered further.

The SURPRISING part, confirmed by checking all nine "missing" dates'
values directly against the scan: every single receipts figure and work
title extracted for this stretch is CORRECT (one plausible minor OCR
slip: 29 Воскрес. morning read as "265 р. 15 к." against a smudged
scan print that likely reads "2165 р. 15 к." -- not evidence of
fabrication). Zoomed into the crop image directly and found why: the
oversized crop isn't blank where it looks blank at a glance -- the real
content for all 7 in-between dates is genuinely present, just
compressed into a visually tiny band by `_dewarp_band`'s remap (a
diagonal warp line and partial digit fragments are visible on close
zoom). The model evidently CAN still read the compressed
receipts/title text accurately, but appears to lose the ability to read
each entry's own (equally compressed) DATE LABEL reliably, and instead
repeats "25 Среда" -- the one date label rendered at full, legible
scale near the top of the crop -- for every entry in the compressed
region. Result: 10 duplicate `("25 Среда.", theater)` keys in the raw
JSON instead of the correct 10 distinct dates, even though the
underlying financial/title data for those 9 "duplicate" entries is
actually the REAL data for 9 different real dates, just mislabeled.

This is a genuinely different, arguably more dangerous failure mode
than the one this session's fix targeted: the original bug produced
wrong VALUES attributed to the correct date (an off-by-one shift); this
one produces CORRECT values attributed to the wrong (repeated) date. A
naive downstream merge keyed on (date, theater, session) would either
silently drop 8 of these 9 real dates' data (last-write-wins) or
corrupt "25 Среда"'s own true record with the wrong entries. Sequence
position happens to preserve the real chronological order in this one
instance, but relying on that would be fragile and isn't validated
elsewhere. Not fixed this session -- flagging for RG's decision on
approach (e.g., detecting a duplicate-date-key result as its own QC
signal in `quality_checks.py`, since it's a cheap, page-local check
that doesn't need a second extraction to catch; or a different
row-boundary strategy specifically for oversized-gap regions, distinct
from lowering `presence_frac` further, which this data shows won't
help).

### Addendum (2026-09-01): built the QC check instead of a second
extraction pass -- `check_repertoire_rowlevel_duplicates`

RG chose the first of the two options above: "Add a cheap QC check to
quality_checks.py flagging duplicate (date, theater) keys within one
row-level page result -- catches it without a second extraction pass.
Let's try this." Added `check_repertoire_rowlevel_duplicates` to
`pipeline/quality_checks.py`, wired into `main()` under the existing
`--row-raw-dir` flag (no new CLI argument needed -- it already pointed
at the right directory for `check_repertoire_cross_extraction`, this
just uses it a second way).

Keyed on (date, theater, session), not just (date, theater), on
purpose: a genuine compound УТРО/ВЕЧ row legitimately produces two
session dicts sharing the same date and theater (one `"morning"`, one
`"evening"`) -- that's real content, not the bug. The confirmed p014
instance repeated the same session value (`"unspecified"`) across every
duplicate, so this key still catches it.

**Verified against the two pages already in hand**: 0 flags on `p012`
(37 sessions, clean, matching the earlier scan-verified result) and 4
flags on `p014` -- the 3 expected ones (25 Среда x10 across all three
theaters, matching the confirmed compression bug exactly, receipts
value included verbatim in `detail` each time) plus one more the check
caught as a side effect: `29 Воскрес. / Александринскій / unspecified`
appearing 2x with two DIFFERENT receipts values. Checked against the
scan: this is NOT the same compression bug -- 29 Воскрес really is a
compound УТРО/ВЕЧ row for Александринскій on this page too, and the
model got both entries' actual receipts correct, it just never
assigned them `session="morning"`/`"evening"` (both came back
`"unspecified"`, colliding on the key). That's the already-documented,
already-deferred УТРО/ВЕЧ-subdivision-detection gap from earlier this
session ("I'm happy to deal with them as a separate issue"), not a new
bug -- but it's still a real, useful catch: this check can't
distinguish "duplicate from a compressed-crop mislabel" from "collision
from a missing session label" by design (both look identical from the
key alone), and doesn't need to -- either way, the page is exactly the
kind quality_checks.py's own stated philosophy already covers: worth a
human glance, not worth guessing through automatically.

RG, on how the resulting flagged pages get handled: "I'm okay
subjecting some pages to handreading after the main extraction
pipeline. I can't do that for a large number, but it's okay if we have,
say, 20 pages that end up needing special treatment." This check is
sized for exactly that -- a small, bounded, page-local signal meant to
route a manageable minority of pages to hand review, not to drive an
automatic repair.

**Not yet done**: run this check across the full season's row-level
output -- the existing `raw_rowlevel/` directory predates the
`presence_frac` fix and is now stale for this purpose (same staleness
already noted for `raw_columnwise/` in an earlier addendum); would need
a fresh whole-season row-level re-run first to get a real count of how
many of the 40 pages this actually flags.

### Addendum (2026-09-01): fresh whole-season row-level re-run with the
`presence_frac` fix, then triaged all 15 flagged pages by cause -- one
hypothesis from the previous addendum turned out wrong on closer check

Re-ran `--row-level` across all 40 pages against the fixed
`detect_rows` (1,485,489 tokens, 40/40 `ok`), then
`check_repertoire_rowlevel_duplicates` against the fresh output.

**15/40 pages flagged, 50 flags total** -- within RG's stated hand-
review budget ("I'm okay subjecting some pages to handreading... it's
okay if we have, say, 20 pages that end up needing special treatment").
RG: "triage the flagged pages by cause." Categorized every flag, then
verified the categories against the actual scan rather than trusting
the pattern-matching alone -- which caught a real mistake in the first
pass (see below).

**A. Spurious mid-row split -- 12/15 pages, dominant cause.** Initial
pass over the data pattern-matched this as "a missing session label on
a genuine compound УТРО/ВЕЧ row" (two entries, same date/theater, one
`None` receipts + one real value, both `session="unspecified"`).
Checked directly against the scan for `repertoire_1898-99_p037`'s "26
Понед." flag -- and that row is NOT compound at all: it's one single
row per theater with one real receipts figure each, matching a
"Спектакль въ память А. С. Пушкина" (Pushkin memorial) heading with
several works listed for Малый театръ specifically. Reading the raw
JSON directly explained the real mechanism: this one tall row got
detected as TWO separate row boundaries, producing two crops that each
captured a different PARTIAL slice of the same row -- one crop got the
annotation heading and the earlier work title(s) but no receipts, the
other got the receipts and a slightly different/overlapping work list
but no annotation. Confirmed the identical pattern on
`repertoire_1898-99_p009`'s "1 Воскрес." flag too (one shared work
title, "Наяда и рыбакъ", appears in BOTH partial crops -- direct
evidence of one row split across two reads, not two genuinely separate
sessions). This is the SAME failure class as issue #50/#51 earlier in
this file (a spurious extra row-boundary line detected mid-row) --
previously investigated specifically in the УТРО/ВЕЧ context and paused
at RG's request ("I think we're getting too much into the weeds for
this specific page") -- now confirmed to recur in a DIFFERENT trigger
context too (an unusually tall multi-work/annotation row, no
compound-session labels involved at all). `p023`'s single flag (a dark
row's `[None, None]` pair, both is_dark=True, identical in every field)
is very likely the same row-boundary-overlap family, just producing an
exact duplicate instead of a partial split -- folded into this category
rather than kept separate.

**B. Multi-row merge (the bug this session's `presence_frac` fix
targeted) -- 3/15 pages** (`p008`, `p010`, `p014`) -- confirmed by 3+
distinct real values under one repeated date/theater key, not just a
2-way split. `p014` is the page the fix was built and validated
against; `p008`/`p010` show the identical signature at smaller scale
(3-4x instead of 10x). Consistent with this addendum's and the
previous one's finding that this fix closed the gap for MOST but not
all cases -- some pages still have a stretch where `detect_rows` finds
literally no boundary candidates at all, and no presence threshold can
recover a candidate that was never chained in the first place.

**C. Column-shift -- 1/15 pages** (`p016`). A genuinely new, distinct
bug, not seen before this session: the `theater` field for several
sessions contains a WORK TITLE ("Евгеній Онѣгинъ, оп.") instead of an
actual theater name, while the real work title for that row went into
the `works` list under a *different* label. Not root-caused this
session -- flagged for awareness, not investigated further, per RG's
explicit "make it work for most of the pages, then address the
outliers" framing rather than chasing every distinct cause to ground
immediately.

**Lesson carried forward**: the pattern-match-first, verify-against-
scan-second discipline this file has used throughout caught a real
mischaracterization here (category A was first read as a session-
labeling gap, actually a row-boundary split) -- worth remembering next
time a flag pattern looks self-explanatory from the data alone.

## 69. Row-boundary detection measured from scratch across 225 pages --
misses outnumber spurious boundaries ~7:1, and 21% of pages detect
nothing at all; three distinct causes, two of them new

**Status: measured, not fixed.** RG, 2026-09-08: "I want to know the
failure rate of detecting real rows across the corpus and the failure
rate of creating spurious rows across the corpus... Let's not make any
assumptions from previous sessions." Everything below was established
fresh, against no prior finding in this file.

### Why the existing data could not answer this

Three sources look like ground truth and are not:

- **The gold set** (`docs/eval/gold/`) has only 4 repertoire pages, and
  its `images/` are downscaled reference copies (e.g.
  `repertoire_1898-99_p019` at 923x1130 against ~2543x3078 for a real
  300dpi render). `_detect_line_curves` returns 1-2 curves on them at any
  threshold -- a pure resolution artifact. **Do not evaluate the detector
  against the gold images.**
- **The production extraction** (`raw.event_entry` date counts) is
  downstream of the thing being measured, and known corrupted on some
  pages (#49, #68). Circular.
- **Row counts alone**, from any source: a miss and a spurious cancel.
  A page with 20 real rows detecting 20 can carry one of each. Scoring
  has to be at the BOUNDARY level, against positions.

Ground truth here is therefore read by eye from the scans: the date
column carries exactly one label per real row, so it gives both the true
count and the true boundary positions. The column sits at the table's
RIGHT edge on the two-page-spread seasons and its LEFT edge from 1898-99
on; on the spread seasons the labels are additionally printed rotated 90
degrees.

### Corpus sweep -- detector output on 225 pages (free, no API calls)

All 8 spread seasons (97 pages) plus 3 single-page seasons rendered for
this purpose (1898-99, 1902-03, 1906-07 = 128 pages), at
`presence_frac=0.5`, i.e. current code as it stands.

| season | format | pages | zero curves | <5 rows | median rows |
|---|---|---|---|---|---|
| 1890-91 | spread | 13 | 0 | 0 | 24 |
| 1891-92 | spread | 12 | 0 | 0 | 24 |
| 1892-93 | spread | 12 | 1 | 4 | 10 |
| 1893-94 | spread | 12 | 0 | 0 | 18 |
| 1894-95 | spread | 9 | 0 | 1 | 15 |
| 1895-96 | spread | 13 | 0 | 1 | 18 |
| 1896-97 | spread | 13 | 0 | 0 | 20 |
| 1897-98 | spread | 13 | 0 | 0 | 18 |
| 1898-99 | single | 40 | 0 | 0 | 12 |
| 1902-03 | single | 38 | 2 | 3 | 8 |
| **1906-07** | single | 50 | **45** | 3 | **0** |

**48/225 pages (21.3%) detect ZERO boundaries; 60/225 (26.7%) detect
fewer than 5 rows**, implausible for tables printing 10-25 dated rows.
Overwhelmingly concentrated: excluding 1906-07, zero-detection runs
3/175 (1.7%).

### Miss rate vs spurious rate

Hand-counted ground truth against detected boundary positions:

| page | real rows | implied | missed | spurious |
|---|---|---|---|---|
| `repertoire_1898-99_p003` | 12 (16 Среда - 27 Воскрес.) | 12 | ~1 | ~1 |
| `repertoire_1902-03_p007` | 12 (9 Среда - 21 Понед., 20 genuinely absent) | 9 | 3 | 0 |
| `repertoire_1902-03_p024` | 12 (27 Понед. - 8 Суббота) | 6 | ~7 | ~1 |
| `repertoire_1906-07_p041` | ~11 (31 Суббота - 10 Вторн.) | **0** | all | 0 |
| `repertoire_1892-93_p008` | 20+ (rotated labels, approximate) | 3 | most | 0 |

Across the four counted precisely (~51 real boundaries): **~23 missed,
~2 spurious. Miss rate ~45%, spurious rate ~6%** -- misses dominate by
roughly an order of magnitude.

**This is worth holding against #68's category A.** That category
("spurious mid-row split", 12 of 15 flagged pages) is an EXTRACTION-level
duplicate -- two partial reads of one row -- not the boundary detector
inventing a line. At the detection layer, invented boundaries are rare;
the failure is almost entirely that real printed rules are not found.

### Three distinct causes, measured not assumed

**1. Chain-presence collapse (new).** `_build_chains` finds plenty of
chains on failing pages; they just do not persist across strips.
Measured (40 strips each):

| page | chains | chains >= 0.5 presence | top presences |
|---|---|---|---|
| `1898-99_p003` (works) | 26 | **13** -> 12 rows | 1.0, 0.95, 0.8, 0.8, 0.8, 0.78 |
| `1906-07_p041` (zero) | 25 | 2 | 0.9, 0.75, cliff to **0.45** |
| `1906-07_p011` (zero) | 19 | 2 | 1.0, 1.0, cliff to **0.28** |
| `1892-93_p008` (3 rows) | 52 | 4 | 1.0, 0.97, 0.9, 0.9, cliff to 0.33 |

On the zero pages the only chains clearing the threshold are the scan
edges, which `_detect_line_curves`'s edge-artifact filter then correctly
drops -- leaving nothing. **Not recoverable by lowering the threshold**:
at 0.25 `p041` yields 7 candidates against ~11 real rows while admitting
noise. The rules in that scan batch are genuinely weak in the ink
profile (p95 ink 0.059 vs 0.109 on a working page). The pages are
entirely legible to a human -- `p041`'s 11 dates were read off by eye
without difficulty -- so this is a detector failure, not an image one.

**2. `_table_x_bounds` does not locate the table at all (CORRECTED --
this was first written up here as an over-extension bug, which is wrong).**
It trims a fixed 8% margin off each edge and returns 8%-92% on EVERY page,
by design; its own docstring says so, and says why -- precise border
detection "turned out to be its own hard problem (physical-scan edge
artifacts -- binding shadow, page curl, background outside the page --
dominate a raw column-darkness scan far more than the actual thin table
border does)". So this is not a defect to fix but a documented
approximation that fails whenever the table does not happen to fill
~84% of the frame. On `repertoire_1902-03_p024` the table spans ~30%-92%,
so ~600px of margin, fore-edge and the holder's hand are pulled into the
range the row-darkness profile is computed over. That page found 6 rows
against 12 printed.

**3. Scattered single-boundary misses on otherwise healthy pages.**
`1902-03_p007` detects cleanly either side of a 514px gap
(1634 -> 2148) spanning three real rows whose rules are plainly visible
on the scan. No threshold or bounds problem apparent; not root-caused.

### Caveats that limit what these numbers mean

- The precise miss/spurious rates rest on **4-5 hand-counted pages**.
  Enough to establish that misses dominate by roughly an order of
  magnitude; NOT a precise corpus rate.
- The single-page-format frame is **3 of 10 seasons**. 1906-07 may be an
  unusually poor scan batch; whether its failure extends to the other
  seven unrendered seasons is unknown and would change the 21.3% figure
  materially either way.
- The spread-season ground truth is harder to read (rotated date labels)
  and `1892-93_p008`'s count is approximate.

### Not done

- Ground truth for the remaining sample pages, particularly the spread
  format.
- Whether 1906-07's failure generalises to 1899-00, 1900-01, 1901-02,
  1903-04, 1904-05, 1905-06, 1907-08.
- Causes 2 and 3 root-caused or fixed. RG on 1906-07, same session:
  "I'm sure the 1906-07 failure can be explained and addressed later."
- A paid full-page vs row-level extraction comparison on the same 10
  sampled pages (3 samples each, ~1.4M tokens) was launched this session
  and is separate from the detection measurement above.

### Addendum (2026-09-08): cropping to the table fixes most of this, and
per-season crops are the practical route -- `pipeline/crop_to_table.py`

RG: "would it help if we cropped images so that page edges and fingers
didn't confuse the model?" Tested directly, and the answer is yes, by a
wide margin.

**Mechanism, confirmed not assumed.** Row detection keeps a line only if
it chains across `presence_frac` of the strips spanning `x0..x1`. Strips
lying in margin cannot contain a printed rule, so they cap and then
suppress every real rule's presence. Cropping two failing pages by hand
(bounds read off a percentage grid, so this tests whether cropping helps
independently of whether bounds can be found automatically):

| page | GT rows | uncropped | cropped | chains >= 0.5 presence |
|---|---|---|---|---|
| `1906-07_p041` | ~11 | **0** | **9** | 2 -> 15 |
| `1892-93_p008` | ~20+ | **3** | **19** | 4 -> 20 |
| `1898-99_p003` (control) | 12 | 12 | 10-11 | 13 -> 13 |

**Automatic bound detection failed four ways** and is documented here so
it is not retried blind: (a) `_binarize` marks the near-black backing
board as ink, so a widest-dense-run search locks onto the board; (b)
thresholding relative to the profile's own maximum locks onto the page's
dark edge line; (c) the low-ink gaps BETWEEN table columns break any
widest-contiguous-run search, returning one column; (d) the holder's
fingers are solid ink blobs carrying more mass than the print, so
cumulative-ink trimming cannot remove them. This is the same wall
`_table_x_bounds` already documents (cause 2 above).

**What works instead: one hand-set crop per season.** A season is one book
photographed in one sitting, so framing is stable. Applying a single crop
read off ONE page to the whole season:

| season | zero-detection pages | median rows | verdict |
|---|---|---|---|
| 1906-07 | **45 -> 0** | 0 -> 10 | adopt |
| 1892-93 | 1 -> 0 | 10 -> 18 | adopt |
| 1898-99 | 0 -> 0 | 12 -> 10 | **skip** |
| 1902-03 | 2 -> 4 | 8 -> 10 | **skip** |

**Cropping is NOT universally beneficial** -- on the already-healthy
1898-99 it costs 1-2 rows (the crop removes the table's outer top/bottom
borders, which `detect_rows` counts as boundaries), and a badly-read crop
made 1902-03 worse. Padding the crop outward recovers 1898-99 but
reintroduces zeros elsewhere (1892-93 at +1.5%, 1906-07 at +3%), so there
is no single safe padding. A crop must therefore be validated per season
before adoption.

`pipeline/crop_to_table.py` implements this: `--contact-sheet` writes a
grid-overlaid sheet for reading bounds by eye, `--evaluate` reports
detection with and without the crop and prints ADOPT/SKIP, and `--out-dir`
applies it. This is the same workflow as ScanTailor's "Apply to All
Pages", without ScanTailor.

**Not done**: bounds for the other 14 seasons; re-reading 1902-03's bounds
(the ones tried were wrong, not evidence that cropping fails there);
deciding whether adopted crops feed `run_pilot.py --row-level` directly.

### Addendum (2026-09-08): crop bounds read for all 18 seasons; the
recto/verso mechanism confirmed (RG's, correcting mine) but per-parity
crops give no measurable gain over per-season union crops

**All 18 seasons' bounds read** off contact sheets and evaluated with
`crop_to_table.py --evaluate`. **13 adopt, 5 skip.** The late single-page
seasons were badly broken and are now fixed:

| season | zero-detection pages | median rows |
|---|---|---|
| 1906-07 | **45 -> 0** | 0 -> 10 |
| 1907-08 | **35 -> 1** | 0 -> 11 |
| 1904-05 | **31 -> 0** | 0 -> 11 |
| 1905-06 | **23 -> 0** | 4 -> 11 |
| 1903-04 | 20 -> 9 | 0 -> 10 |
| 1901-02 | 3 -> 0 | 10 -> 11 |
| 1902-03 | 2 -> 1 | 8 -> 11 |

Roughly **154 pages that detected nothing now detect plausible row
counts**, from eighteen hand-read numbers. Skipped (already healthy, and
the crop costs their outer border rows): 1890-91, 1891-92, 1893-94,
1896-97, 1897-98, 1898-99. Config: `docs/repertoire_crop_bounds.json` (kept in docs/, not outputs/, so it survives an outputs/ wipe -- same reasoning as docs/ballet_graduates_tenure.csv).

**Why the table position varies within a season -- RG's explanation,
which corrects the one first written here.** This file previously said
1902-03 "wasn't photographed with stable framing." Wrong. RG: "the tables
are not centered in each page: they are closer to the fold than to the
outside edge, so the margins are uneven. Pages on the left have a wider
lefthand margin, and pages on the right have a wider righthand margin."

Confirmed by measuring ink centre-of-mass per page against page parity:

| format | seasons | even COM | odd COM | gap |
|---|---|---|---|---|
| two-page spread (1890-91–1897-98) | 8 | -- | -- | **0.000-0.040 (none)** |
| single page (1898-99–1907-08) | 10 | ~0.31-0.49 | ~0.60-0.76 | **0.17-0.46 (strong)** |

Within a parity group the scatter is small (+/-0.02-0.05) against a gap of
0.17-0.46. And the format split follows directly from the mechanism: a
SPREAD image contains both a recto and a verso, so the gutter sits in the
middle and the asymmetry cancels; only single-page seasons alternate.
This also supersedes an intermediate guess made here that the split was
St Petersburg vs Moscow pages -- city correlates with parity in these
volumes, but the gutter is the mechanism.

**But per-parity crops do not help, tested two ways:**
- *COM-centred windows* (fixed width centred on each parity's mean COM):
  WORSE -- 1903-04 zero 9 -> 13, 1907-08 zero 1 -> 5. Centre-of-mass is a
  poor proxy for the table's centre; fingers and blank areas drag it.
- *Hand-read per-parity bounds* on the four cleanly-separated seasons
  (1898-99, 1899-00, 1900-01, 1901-02): **identical** to the union crops --
  same zero count (0), same median, same `<5 rows` count.

And on the two seasons that still carry residual zeros, parity is not the
right split at all: 1903-04 and 1907-08 show BOTH positions within EACH
parity (e.g. 1903-04 p012 at x 6-72% and p024 at 12-78%, both even),
matching their weak/noisy parity flags (sigma 0.12 and 0.10).

**Conclusion**: once the gross margin (fingers, backing board, fore-edge)
is removed, row detection is insensitive to the remaining slack -- the
per-season union crop is already inside the good-enough region. Keep one
crop per season. 1903-04's residual 9 zero-detection pages are NOT a
parity problem and remain unexplained.

### Addendum (2026-09-08): `detect_rows` no longer depends on the table's
outer top border, and post-crop accuracy re-measured -- miss rate
33.8% -> 4.4% on hand-counted pages

Two changes done together, so the measurement reflects the fixed code.

**1. `detect_rows(..., outer_top_border=False)`.** Cropping tightly enough
to exclude fingers and the fore-edge also cuts the table's own outer top
rule. The old code assumed `curves[0]` WAS that rule, so on a cropped page
`curves[0]` is instead the header-BOTTOM rule -- meaning the band pasted
onto every row crop as "the header" is actually the first row's content,
and every row shifts up by one. **That is a correctness bug, not an
off-by-one in a count.** With the flag set, the header band runs from the
image's own top edge to `curves[header_line_count - 1]`, and row
boundaries start one curve earlier. Same principle as `detect_columns`'
2026-09-01 redesign in this file: depend on interior rules and let the
outer edge be the image edge.

Default is `True`, so the uncropped path is untouched (verified: row
counts unchanged on a 6-page sample, and the two known zero-detection
pages still raise the same ValueError).

Recovered 1-2 rows per page in EVERY season. Four of the six seasons that
scored SKIP now match or beat their uncropped counts once cropped
(1891-92 20->22, 1893-94 20->21, 1896-97 20->22, 1897-98 18->20).

**2. Accuracy re-measured against hand-counted ground truth**, since
median row count is not accuracy and the previous miss/spurious figures
were measured pre-crop and had gone stale:

| page | GT rows | uncropped | crop + fix |
|---|---|---|---|
| `1898-99_p003` | 12 | 12 | 11 |
| `1902-03_p007` | 12 | 9 | **12** |
| `1902-03_p024` | 12 | 6 | **12** |
| `1906-07_p041` | 11 | 0 | 10 |
| `1893-94_p001` | 21 | 18 | 20 |
| **total** | **68** | **45** | **65** |

**Miss rate 33.8% -> 4.4%. Spurious: none observed** -- no page
over-detects against its ground truth, consistent with the pre-crop
finding that this detector misses rules rather than inventing them.

Corpus-wide, with adopted crops applied across all 519 repertoire pages:
zero-detection pages **161 -> 11 (31.0% -> 2.1%)**, `<5 rows`
**183 -> 14 (35.3% -> 2.7%)**.

**Caveats**: five hand-counted pages, four of them single-page format.
`1898-99_p003` still loses one row when cropped (12 -> 11), consistent
with its SKIP verdict -- cropping is not free on already-healthy pages.
`1893-94_p001`'s GT of 21 counts the fold-obscured `23 Четвергъ` row
confirmed earlier today, which no method recovers from the image.

**Not done**: the 11 residual zero-detection pages (9 in 1903-04, cause
unknown and NOT parity); wiring adopted crops into
`run_pilot.py --row-level`, which still renders from uncropped images, so
none of this reaches extraction yet.

### Addendum (2026-09-08): full-page vs row-level extraction compared
head to head -- row-level is far more REPRODUCIBLE, but only as good as
row detection; the two methods fail on disjoint page sets

RG: "How do full page reads compare with row reads?" No row-level output
existed on this machine, so both were re-run from scratch on the same 10
sampled pages, **3 independent samples per method** (issue #1: this
extraction is non-deterministic, so a single sample per method cannot
separate a real difference from run-to-run noise).

Cost measured, not estimated: **~111k tokens per full-page run vs ~410k
per row-level run over the same 10 pages -- 3.7x**, close to the 3.5-4x
predicted from one page becoming 10-12 calls.

**They fail on DISJOINT page sets.**
- Row-level lost 2/10: `repertoire_1906-07_p041` and `_p011`, both
  `row_detect_failed` with 0 grid lines. **Row reads inherit row-detection
  failure completely** -- no boundaries, no extraction at all.
- Full-page lost 1/10: `repertoire_1891-92_p005`, `Exceeded limit on max
  bytes per data-uri item: 20971520` (the documented DashScope cap).
  Row-level SUCCEEDED on that page, because a row crop is far under the
  limit. **Row reads can extract oversized pages full-page cannot.**

**Row-level is markedly more reproducible.** Mean self-agreement across
each method's own 3 samples, over the 7 pages both produced:
**row-level 82%, full-page 57%.**

**But cross-method agreement tracks row-detection quality exactly:**

| page | format | theater-field valid (page/row) | receipts agree |
|---|---|---|---|
| `1898-99_p003` | single | 100% / 100% | **100%** |
| `1902-03_p007` | single | 100% / 100% | **100%** |
| `1902-03_p024` | single | 100% / 100% | **89%** |
| `1895-96_p002` | spread | 100% / 99% | 60% |
| `1892-93_p008` | spread | 100% / 92% | 64% |
| `1893-94_p001` | spread | 100% / **44%** | 33% |
| `1892-93_p001` | spread | 80% / 99% | 22% |

Where row detection is healthy (the single-page pages) the two methods
agree on 89-100% of receipts figures and both keep a valid theater name in
every cell. Where detection is poor -- the spread pages, which this
session measured at a 33.8% boundary miss rate uncropped -- row-level
degrades badly: on `1893-94_p001` **56% of its cells carry a WORK TITLE in
the `theater` field** ("Аида, оп.", "Le Duc Job, com.") rather than a
theater name. That is issue #68's category C column-shift, reproduced here
at scale and shown to be a consequence of bad row crops, not an
independent bug.

**Methodology note, and a real artifact caught.** A first pass keyed cells
on `(date, theater, session)` with theater compared verbatim, and reported
0% self-agreement on `1898-99_p003`. That was entirely an artifact: the
same cell is emitted as "Большой театр." / "Большой театръ" / "Большой
театръ." across runs (the #15 театръ/театр orthography variance) while the
receipts under it are byte-identical. Normalising the ъ and trailing period
moved that page to 94%/97%/86% on 36/36 shared keys. Same lesson as #21's
positional-alignment artifact: check the comparison before believing its
output.

**Caveat**: row-level here ran on UNCROPPED images, so its poor showing on
spread pages reflects pre-crop detection. Re-running it against the adopted
crops is the obvious next test and needs a fresh paid run.

### Addendum (2026-09-08): CORRECTION -- the 4.4% miss rate above is wrong
(it counted the header as a data row); and `outer_top_border=False` must
NOT be applied blanketly to cropped pages

Found while running the cropped row-level extraction below. Both errors are
mine, in the measurement and in how the new flag was used.

**1. The crop bounds RETAIN the table's outer top border on virtually every
page.** Measured directly on the 10-page sample: the first detected curve
sits at 1.2-4.0% of crop height on 9 of 10 pages -- i.e. it IS the outer
border, still in frame. Only `1898-99_p003` (5.4%) had it cut. That makes
sense: the bounds were read AT the table's border, so the border survives.

**2. Therefore `outer_top_border=False` was wrong on those 9 pages**, with
two consequences:
- *Measurement*: with the border present, the flag makes `row_boundaries`
  start one curve early, so the HEADER ROW is counted as a data row. Every
  cropped count was inflated by one. **The "miss rate 33.8% -> 4.4%" figure
  in the addendum above is wrong. Corrected: 68 GT rows, 45 detected
  uncropped (33.8% miss) -> 60 detected cropped with the border retained
  (11.8% miss).** Still a large improvement, less than half the claimed one.
  The corpus-wide `161 -> 11 (31.0% -> 2.1%)` figure is unaffected -- it was
  computed with the border retained -- but an intermediate `161 -> 2` quoted
  in conversation was inflated the same way and is withdrawn.
- *Extraction*: the header band becomes the blank sliver above the border,
  so each row crop carries NO column headings. The model then invents
  theater names: on `repertoire_1902-03_p007` the cropped run labels the
  columns Маріинскій/Александринскій/Михайловскій where the page truly
  prints Большой/Малый/Новый -- while the receipts under them
  (1265 р. 93 к., 718 р. 11 к., 2213 р. — к.) are byte-identical to the
  full-page read. **Values right, column labels fabricated.**

**Guidance**: keep the `outer_top_border` parameter -- it is correct where
the border genuinely is cut -- but leave it at its `True` default with these
crop bounds, and do NOT pass `run_pilot.py --cropped-images` with them. A
crop that retains the border needs no flag. If bounds are ever tightened
past the border, the flag becomes necessary, and whether the border survived
is cheaply checkable (is the first curve within ~4% of the crop's top edge).

**Note on the validity metric**: "theater-field valid" cannot catch this --
"Маріинскій" IS a valid theater name, just the wrong one. Only comparison
against another method's output surfaced it. A field-shape check is not a
correctness check.

### Addendum (2026-09-08): clean cropped row-level re-run -- cropping
massively improves row DETECTION but does NOT improve row-level
EXTRACTION, because the header-reattachment step is separately broken

Re-ran row-level extraction 3x on the same 10 cropped pages with the flag
left at its `True` default (border retained), 1.53M tokens, 10/10 pages
every run. Compared against three other conditions on identical pages.

| metric (mean over the sample) | row uncropped | row cropped, wrong flag | **row cropped, clean** |
|---|---|---|---|
| theater-field valid | 86% | 89% | **79%** |
| receipts agree vs full-page | 59% | 69% | **66%** |
| self-consistency over 3 samples | 85% | -- | **84%** |

**The clean cropped run is not better than the uncropped run.** Detection
improved enormously (this session: zero-detection pages 161 -> 11
corpus-wide) and extraction did not follow. That is a real negative result,
and the cause is not cropping.

**Root cause: the header band pasted onto each row crop is frequently not
the header.** `detect_rows` defines it as the span between two DETECTED
curves (`curves[0]` .. `curves[header_line_count]`). Where the column
headings' own bounding rules are not among the detected curves, the band
silently lands on data instead. Verified by looking at the crops directly:

- `1895-96_p002`'s row-1 crop carries "Золушка, бал. / Недоросль, ком. /
  Травіата, оп. / Евгеній Онѣгинъ" as its "header" -- row content.
  `header_line_count` 1, 2 and 3 all produce the SAME wrong band, so this
  is not the un-auto-detected `header_line_count` noted in #50: the
  headings sit ABOVE the first detected curve and are unreachable by any
  index.
- `1898-99_p003` (100% correct uncropped) drops to 0% valid theater names
  cropped. It is the one page in the sample whose crop genuinely CUT the
  outer border, so `outer_top_border=True` is wrong for it specifically --
  confirming the flag must be decided PER PAGE, not per batch. The
  border-survival test is cheap: is the first curve within ~4% of the
  crop's top edge.
- Where the header band IS correct, results are excellent:
  `1902-03_p007`/`p024`, `1906-07_p011`/`p041` all reach 100% theater
  validity and 90-100% receipts agreement -- and the two 1906-07 pages
  produced NOTHING at all before cropping.

**What this means practically**: row-level extraction on cropped pages
cannot be fairly evaluated until the header band is correct. Two concrete
fixes, both unstarted:
1. Decide `outer_top_border` per page from the border-survival test above
   rather than per batch.
2. Make the header band robust when the headings' rules are not detected --
   e.g. take everything above the first ROW boundary as header rather than
   requiring a detected curve pair to bound it.

**Do not read the 66% vs 59% receipts figure as "cropping helps
extraction"**: the sample mixes pages with correct and corrupted header
bands, so it measures the header defect more than it measures cropping.

### Addendum (2026-09-08): header-band fix attempted -- NOT solved; a
verification tool built instead, and why three auto-detection approaches
failed

RG: "fix the header band." Partially done: the failure is now precisely
characterised and inspectable, but no robust automatic fix landed. Recorded
here so the dead ends are not re-run.

**What the band actually is.** `detect_rows` reattaches, to every row crop,
the image between two DETECTED curves: `curves[0]..curves[header_line_count]`
when `outer_top_border=True`, or `image top..curves[header_line_count-1]`
when False. Which is correct depends on whether `curves[0]` is the table's
outer top rule or the rule *below* the column headings -- and that varies
PER PAGE, not per season or per format:

- `1898-99_p003`: `True` yields ROW CONTENT as the header; `False` yields
  the correct headings.
- `1902-03_p007`: `True` yields the correct headings; `False` additionally
  pulls in the page's own date caption ("9 октября ... 1902 г."), the exact
  content #50 documented leaking into `date_text`.
- `1895-96_p000` needs False, `1895-96_p006` is correct either way --
  **within one season.**

So neither blanket setting is safe, and per-season configuration (which
worked for crop bounds) is NOT sufficient here.

**Three auto-detection discriminators tried, all failed on real pages:**
1. *Distance of `curves[0]` from the crop's top edge* -- cannot distinguish
   "curve0 is the outer border" from "curve0 is the header-bottom rule";
   both sit at 1-5% of height.
2. *Ink density above `curves[0]`* -- a date caption reads as densely as
   column headings (`1902-03_p007` 0.081 vs `1895-96_p002` 0.190, and
   `1892-93_p008` 0.0001 for a genuinely blank margin). No threshold
   separates caption from headings.
3. *Counting column blocks above `curves[0]`* -- headings on
   `1895-96_p002` merge into ONE block, scoring identically to a caption,
   while `1892-93_p001`'s score 9.

**Built: `pipeline/check_header_band.py`.** Renders the band `detect_rows`
would actually reattach, for BOTH settings side by side, per season, from
the real row crops rather than recomputing. A correct band shows the column
headings; a wrong one shows row content or a bare caption. This is what
makes any per-page or per-season setting verifiable instead of guessed.

**Still open, and this is the blocker for cropped row-level extraction:**
the band should not be inferred from curve indices at all. A more robust
design would define it explicitly -- e.g. an anchored y-range per format,
or reattaching no image header and instead supplying the column names to
the prompt. Until then, `--cropped-images` should not be used for
production row-level runs, and the uncropped path remains the default.

### Addendum (2026-09-08): column boundaries measured per season and wired
into `detect_columns` -- and a structural bug found: the date column was
assumed to be on the LEFT, which is wrong for every spread season

RG: "let's look at alternative ways of figuring out which rows cells belong
to" after agreeing automatic geometry detection is not workable at scale.
The alternative is the column-wise track (#68): read the DATE column for the
authoritative row sequence, read each THEATER column, and let
`merge_columnwise_page` align them by calendar day and session label. No
horizontal row boundaries anywhere -- which removes the component that has
failed eleven distinct ways.

**Column positions are stable enough to be a per-group constant.** Measured
`_detect_vertical_dividers` across every page of a group, on CROPPED pages:

| group | sigma of divider position |
|---|---|
| 1893-94 (spread, per season) | 0.003-0.013 |
| 1898-99, per season | 0.056 |
| 1898-99, **split by parity** | **~0.020** |

against columns 17-25% wide. The parity split is RG's recto/verso finding
again: within a season crop the table still shifts sideways between recto
and verso, and splitting on it drops sigma by ~3x. So spread seasons are
keyed by season (8 groups) and single-page seasons by "season:parity"
(20 groups) -- **28 groups, in `docs/repertoire_column_bounds.json`**.

**Derived by measurement, not by eye**, taking the median across a whole
group -- steadier than one visual reading. Gated on EVEN SPACING, since
theaters are equal-width, which caught three bad groups: `1896-97` (the
detector returned the table's outer LEFT border as a divider and missed the
date one), `1907-08:0` (two spurious dividers), `1902-03:1` (4 dividers
where a 3-theater layout allows 3). Those were hand-corrected against the
page. **`1907-08:1` remains flagged in `_needs_review`** -- its hand-read
gaps (0.29/0.24) are too uneven to trust.

**Structural bug found while wiring this in**: `detect_columns` computed the
date crop as `img[:, 0:dividers[0]]` -- i.e. it assumed the date column is at
the table's LEFT. That holds from 1898-99 on, but the two-page-spread
seasons (1890-91..1897-98) put it at the RIGHT. Every spread page run
through `--column-level` would therefore have had a THEATER's content in its
date crop. Fixed with a `date_side` parameter, driven from the config.

**Verified end to end on 146 pages across 4 seasons**: config-driven column
slicing succeeds on 146/146, and the crops were checked by eye for both
formats -- `1893-94_p006` (spread) yields a date crop holding "Мѣсяцъ, день
и число" with the rotated dates and theater crops holding Маріинскій /
Александринскій / Михайловскій; `1898-99_p003` (single) yields 16 Среда..20
Воскрес and Большой / Малый / Новый. Detection-based slicing "succeeds" on
the same pages only in the sense that it does not raise -- it has no way to
guarantee the right column COUNT, which the config does.

**Not done**: `1907-08:1`'s bounds; wiring the config through
`run_pilot.py --column-level`; and a paid column-wise extraction run to test
whether this actually beats the row-level and full-page paths.

### Addendum (2026-09-08): DECISION -- different extraction methods for the
two page formats; column-wise adopted for the single-page seasons (81% of
Repertoire), spread seasons still unresolved

RG: "It's okay if we have different extraction methods for the two
different formats." That settles a question this file has been circling all
day, and the evidence supports splitting.

**Corpus split**: single-page format (1898-99..1907-08) is **422 of 519
Repertoire pages (81%)**; two-page-spread (1890-91..1897-98) is 97 (19%).

**Column-wise extraction, re-run on corrected crops, receipts compared
NUMERICALLY** (see the method note below):

| page | format | coverage | receipts agree |
|---|---|---|---|
| `1898-99_p003` | single | 100% | **100%** |
| `1906-07_p041` | single | 100% | **100%** |
| `1906-07_p011` | single | 92% | **100%** |
| `1902-03_p007` | single | 67% | **100%** |
| `1902-03_p024` | single | 50% | 77% |
| `1895-96_p002` | spread | 38% | 63% |
| `1893-94_p001` | spread | 80% | 23% |
| `1892-93_p008` | spread | 35% | 14% |

**Every single-page season reaches 77-100% agreement with the full-page
baseline; every spread season sits at 14-63%.** The split is by FORMAT, not
by whether the crop was corrected -- it only became visible once the crop
bugs and three separate comparison artifacts were cleared.

Why the spread format is harder for this method is plausible but untested:
5 theater columns instead of 3, date labels printed rotated 90 degrees, and
the binding fold running through the middle of every page.

**Cost**: column-wise is the CHEAPEST of the three methods, ~7k tokens/page
against ~11k full-page and ~51k row-level -- roughly 7x cheaper than
row-level, because a page becomes 4-6 narrow images rather than 10-21 row
strips.

**Where this leaves each format:**
- *Single-page (422 pp)*: column-wise is the candidate -- best agreement,
  lowest cost, and it refuses rather than guesses (`merge_columnwise_page`
  drops a theater whose row count does not reconcile). The open problem is
  COVERAGE, not accuracy: 50-100% per page, because of those refusals.
- *Spread (97 pp)*: **unresolved.** Column-wise is poor; row-level on
  uncropped spread pages was 13-57% on receipts; full-page remains the
  incumbent and has no better-tested rival. Do NOT read this addendum as
  recommending column-wise for spread seasons.

**Method note -- three string-comparison artifacts, all of which made
correct data look wrong**, in the order they were caught: театръ/театр
orthography (#15) scoring a page at 0% self-agreement; і/и in Маріинскій/
Мариинскій flagging two pages as theater-name mismatches; and a Latin `p`
where the full-page read emits Cyrillic `р` ("611 p, 75 к." vs
"611 р. 75 к.", the same figure). Receipts are now compared as two NUMBERS
rather than as strings. Any future comparison of these outputs should do
the same, and should be checked against a page before its verdict is
believed.

### Addendum (2026-09-08): Gate 3 STOPPED at 62/332 -- the per-parity column config is the wrong abstraction; dividers are anchored to the TABLE, not to the crop

Gate 3 (the 8 remaining single-page seasons, 332 pp) was launched after
1898-99 and 1906-07 both passed, and was **killed at 62 pages** once the
partial output showed a systematic defect. It is not a method failure and
not a merge failure -- it is the column-divider configuration, and the
partial run is what exposed it.

**The symptom.** Receipts on even-numbered pages lose their kopecks. The
rubles are correct, the work titles are correct, the row placement is
correct, and the kopecks are simply absent, because the column crop ends
mid-number. Measured as "share of extracted receipts that contain a
kopecks figure at all", across the 62 pages that completed:

| season  | even pages | odd pages |
|---------|-----------:|----------:|
| 1899-00 |        95% |      100% |
| 1900-01 |        82% |       99% |
| 1901-02 |        91% |       99% |
| 1902-03 |        82% |       98% |
| 1903-04 |    **23%** |      100% |
| 1904-05 |    **37%** |      100% |
| 1905-06 |        69% |       98% |
| 1907-08 |        64% |       98% |

Odd pages are effectively clean everywhere; even pages range from mildly
to badly truncated. Confirmed by eye at native resolution on
`repertoire_1903-04_p034`, theater column 0: the crop shows
`Ромео и Джульетта, оп` and `960 р` with the `60 к.` outside the frame,
and simultaneously bleeds `Четвергъ.` in from the *date* column on the
left -- the whole column window sits too far left.

**Why the existing config cannot fix this by retuning.** The dividers in
`docs/repertoire_column_bounds.json` are fractions **of the cropped
image**, hand-read per `season:parity`. That assumes the table sits at a
fixed x-position within the crop for a given parity. It does not. On
1903-04's even pages alone the table's left edge measured 0.107, 0.184,
0.220 -- a 0.11 wander *within one parity group*, larger than a whole
column's worth of tolerance. Parity is only a coarse proxy for where the
table actually is, which is why odd pages happen to work (their table sits
near x=0, so crop-relative and table-relative nearly coincide) and even
pages do not.

**What the geometry actually obeys.** Measure each divider as an offset
from the table's own left edge and the wander disappears. Detected rules
were pooled per season as offsets from the table edge (no assumption about
how many rules a page yields -- see the method note below):

| season  | parity 0 offsets      | parity 1 offsets      | cluster spread |
|---------|-----------------------|-----------------------|---------------:|
| 1899-00 | 0.087, 0.339, 0.591   | 0.087, 0.336, 0.587   |          0.021 |
| 1901-02 | 0.083, 0.321, 0.563   | 0.084, 0.324, 0.564   |          0.003 |
| 1903-04 | 0.095, 0.344, 0.594   | 0.081, 0.345, 0.619   |          0.038 |
| 1904-05 | 0.090, 0.354, 0.608   | 0.090, 0.384, 0.644   |          0.079 |

The two parities agree to within a few thousandths on 1899-00 and 1901-02,
and the first divider lands at 0.083-0.095 in every season measured --
consistent typesetting, as expected for a fixed page format. Under the
crop-relative convention the same seasons spread by 0.18-0.25.

**Proposed fix (NOT yet implemented):** detect the table's left edge per
page and place dividers as offsets from it, collapsing the 28
`season:parity` groups to one set of offsets per season. Two seasons resist
the automatic table-edge detection so far (1902-03 parity 1, where the
detected left edge is clearly too far left, and 1907-08, where the detector
returns six clusters instead of four); those need the edge found more
robustly before the convention can be applied corpus-wide.

**Method note -- a broken measurement was nearly reported as a refutation.**
The first corpus-wide comparison of the two conventions appeared to show
table-relative was WORSE for 1902-03 and no better for 1899-00. That was a
bug in the analysis, not a result: the rule detector returns a *variable*
number of lines per page (sometimes the left border, sometimes not,
sometimes only two internal dividers), so indexing the "3 internal
dividers" as `detected[1:4]` compared different physical rules on different
pages. Pooling every detected rule as an independent offset and clustering
removes the index assumption, and is what the table above uses.

**Second method note.** The Latin-`p`-for-Cyrillic-`р` artifact (#15) bit a
*third* time, here in the scoring code rather than the data: a receipts
parser that located the rubles group by searching for `р` read
`'332 p. 95 к.'` as 95 kopecks and scored it as a mismatch. This alone
moved 1906-07's measured receipts agreement from 95.5% to **99.1%**.
Parse receipts positionally -- first number is rubles, second is kopecks --
never by keying off the unit letter.

**Third finding -- receipts agreement is blind to dropped rows.** Agreement
is computed over slots BOTH runs report, so a session the column-wise merge
never emitted is invisible to it. Counting rows per (day, theater) on
1906-07, restricted to theater columns the merge reported `ok`: 97.9% of
slots have identical row counts, with 17 rows dropped by column-wise
against 9 dropped by full-page (net -8 rows, 0.6%). The column-wise drops
concentrate on compound days -- 1906-07 p011, p027, p031 and p032 each kept
the evening row, dropped the morning one, and labelled the survivor
`session: unspecified` where the full-page read has a утро/вечеръ pair.
Coverage does not catch these: the column reported `ok`. Any future
scorecard for this method needs all three numbers -- coverage, row
completeness, and receipts agreement -- because each is blind to a
different failure.

### Addendum (2026-09-09): table-anchored divider rebuild -- anchor the
FIRST divider per page, keep the rest as stable season-level gaps; solves
Gate 3 without needing the two previously-stuck groups solved separately

Picked back up from the machine-migration pause at commit `dd195ed`
(memory note `columnwise-paused-table-anchored-dividers`). RG: "check the
two resistant seasons first" (1902-03 parity 1, 1907-08, where an earlier
pass's automatic table-edge detection wouldn't converge), then "proceed
on [rebuilding table-anchored]."

**Diagnosis, done on freshly-rendered pages (nothing from the paused
session survived the environment migration -- scratchpad state is not
persistent across machines).** Ran `_detect_vertical_dividers` directly
on 6 pages of `1902-03:1` and 13 of `1907-08` (both parities): divider
COUNT is genuinely unstable page to page (2 to 5 candidates on
1902-03:1 alone), for two distinct, confirmed reasons, not one:

1. **The season-wide crop clips real content on some pages.**
   `repertoire_1907-08_p004`'s crop visibly truncates the Михайловскій
   column on the right -- confirmed by eye, and it alone explains that
   page's 8 spurious candidates.
2. **Even on cleanly-cropped pages, table position varies more than a
   per-page reading can average out.** `1907-08_p000` and `p008` are
   both parity 0 (same recto/verso side) and both crop cleanly, yet
   their first divider lands at 0.096 vs 0.363 of crop width -- too
   large a gap to be gutter-side mirroring alone.

**The key measurement that unlocked a fix**: while divider POSITIONS are
unstable, the GAPS between them (season-level column widths) are not --
computed from the already-existing `docs/repertoire_column_bounds.json`,
every group's two gaps cluster within about 0.02 of each other, including
`1902-03:1` (0.204, 0.219) and `1907-08:1` (0.205, 0.21) sitting right in
line with every other group's ~0.20-0.25. And critically, reading
`pipeline/row_detect.detect_columns`'s existing `dividers_frac` handling
showed it does ZERO per-page adaptation when a config is supplied --
`xs = [round(f * W) for f in dividers_frac]`, a pure blind lookup. That
is the Gate 3 defect's actual mechanism, and it affects every group that
uses a config, not only the two that resisted full automatic detection.

**Design**: only the FIRST divider in a group's template is now an
anchor, refined per page by a new `_refine_divider0` -- search fresh
candidates near the season-level prior (within a small tolerance) rather
than trusting the prior blind OR searching unconstrained. Unconstrained
search has its own failure, confirmed directly: on
`repertoire_1907-08_p011`, an unusually wide margin (paper
staining/texture, visually confirmed, no real print in it) produced
FIVE evenly-spaced candidates at 100% strip presence -- indistinguishable
from a real divider on presence alone -- all ahead of the real one. The
anchor is what lets the search reject them (all sit 0.04-0.15 from the
prior; the real divider sits within 0.002 of it). The remaining
positions are reconstructed from the refined anchor plus the season's
own stable gaps -- not read from the template directly at all anymore.

**Validated on 26 pages, 0 failures**: `1902-03:1` (6 pages) and
`1907-08:0`/`1907-08:1` (10 pages, including `p011` itself) -- every
page now produces the correct theater count with consistent widths
across the group. Regression-checked against `1898-99` and `1906-07`
(20 pages, both parities each) -- unchanged, correct, matching the
already-validated state. Also checked `1893-94` (spread format, 6
pages) since the anchor logic is format-agnostic (`date_side` doesn't
change which end gets anchored) -- 5 theaters each, consistent widths,
confirming the fix generalizes rather than being single-format-specific.

**What this means for the open decision**: does NOT need the two
previously-stuck groups solved as a special case before the corpus-wide
rebuild can proceed -- the same anchor mechanism handles them using the
values ALREADY on record (their hand-corrected entries from 2026-09-08),
now used as anchors-with-refinement instead of blind constants. No
season needed re-measuring; only `detect_columns`'s consumption of the
existing config changed. `docs/repertoire_column_bounds.json`'s `_note`
carries the updated semantics.

**Not yet done**: re-running Gate 3 itself (the 332-page scale-up that
was stopped) against the fixed code, to get a real kopecks-completeness
number in place of the 23-82%-truncated figures that triggered the
stop.

### Addendum (2026-09-09): Gate 3 re-run, 332/332 pages -- kopecks
completeness fixed from 23-82% to 89.6-100%; a second, deeper divider
bug found and fixed along the way on `1903-04`

RG: "yes, run Gate 3." Rendered, cropped, and column-extracted all 8
remaining single-page seasons (1899-00, 1900-01, 1901-02, 1902-03,
1903-04, 1904-05, 1905-06, 1907-08 -- 332 pages, 0 failures, 4.4M
tokens).

| season  | even pages    | odd pages     |
|---------|--------------:|--------------:|
| 1899-00 | 100.0%        |  99.5%        |
| 1900-01 |  99.8%        |  99.7%        |
| 1901-02 |  99.8%        |  99.5%        |
| 1902-03 |  99.8%        |  99.5%        |
| 1903-04 |  97.0%        | 100.0%        |
| 1904-05 |  89.6%        |  98.8%        |
| 1905-06 |  96.1%        |  94.0%        |
| 1907-08 |  93.6%        |  91.2%        |

Every season now sits at 89.6-100%, replacing the 23-82%-truncated
figures that stopped Gate 3 originally. Two corrections along the way,
both real, both caught by checking actual output rather than trusting
the aggregate number:

**Measurement bug in the scorecard itself, not the data.** The first
kopecks-completeness pass (checked digit-after-`р.`) flagged "2710 р. —
к." as truncated -- but a dash IS the printed zero-kopecks convention
throughout this corpus, not missing data. Fixing the regex to accept a
dash alongside a digit moved several seasons' numbers substantially
(1903-04 even: 63% -> 97%). Re-checked the residual failures after the
fix and they're genuinely different: isolated to 1-2 specific pages per
season (e.g. `1904-05_p000`/`p008`, `1903-04_p030`), where the model
dropped the "р."/"к." units entirely rather than any crop or divider
issue -- a small, bounded, page-specific quirk, not investigated
further this session.

**A second, deeper divider bug, found because 1903-04's first re-run
still only reached 63%.** Widening `1903-04`'s crop (see the previous
addendum's `1902-03` pattern) fixed the visible header-truncation, but
the RESCALED season-level divider template that came with it was
wrong -- not because the rescale math was wrong, but because the
ORIGINAL pre-migration measurement it rescaled was itself apparently
taken from pages affected by the same clipping bug, so rescaling it
faithfully reproduced a bad number. Confirmed directly: fresh
`_detect_vertical_dividers` readings on the corrected crop put
`1903-04:0`'s true first divider at 0.27-0.38 depending on page -- a
0.11 spread, three times the ±0.04 tolerance `_refine_divider0` (the
previous addendum's anchor-only design) searched within, so it was
locking onto a spurious nearby candidate instead of the real one.

Widening that function's tolerance would not have been safe: the same
±0.11-scale search radius needed for `1903-04:0` would also have caught
`1907-08_p011`'s faint-paper-staining false candidates, which the
tighter tolerance was specifically built to reject. What DOES stay
stable on `1903-04:0` even though absolute position swings 0.11: the
GAPS between dividers (0.21-0.22 throughout, matching every other
season's ~0.20-0.25). Replaced `_refine_divider0` with
`_refine_dividers`, which validates a candidate SET by whether its
internal gaps match the season template (tight tolerance on the
relative structure) rather than anchoring on any one candidate's
absolute position (now a loose bound on the search space only, not the
decision itself). Three unrelated margin artifacts landing at exactly
the right relative spacing to fake a real table is far less likely than
one artifact landing near an expected absolute position, so this is a
strictly stronger check, not just a looser one.

Re-validated against everything already validated before this change
(1902-03:1, 1907-08 both parities including `p011`, 1898-99 and 1906-07
both parities, 1893-94 spread) -- zero regressions, identical results
-- before re-running `1903-04` end to end: even pages went 52% -> 63%
(crop fix alone) -> 90% (divider fix, first regex) -> 97% (corrected
regex).

**Not yet done**: the 1-2 pages per season with units-dropped receipts
(a distinct, apparently rare model-formatting issue, not a crop/divider
one); row completeness and receipts-VALUE agreement against baseline at
this same 332-page scale (this addendum only re-measured kopecks
completeness, the specific metric that stopped Gate 3 -- the full
three-number scorecard this file's own methodology calls for is still
outstanding for the newly-fixed seasons).

### Addendum (2026-09-09): 32-page sample scorecard; a new
`check_repertoire_malformed_receipts` QC check; three DISTINCT root
causes found behind what looked like one "missing units" symptom

**Sample scorecard** (row completeness + receipts-value agreement,
sampled 4 pages/season x 8 seasons = 32 pages, per RG's "sample first"
preference, mirroring the escalation logic Gate 3 itself already used):
row completeness 79.3% (896/1130 slots -- consistent with
`merge_columnwise_page`'s already-documented refusal behaviour, not a
new problem); receipts-value agreement on slots both methods report
93.8% (94.8% excluding one page -- see below). Not yet escalated to
the full 332-page baseline; the sample didn't surface anything that
demands it.

**One page in the sample, `1902-03_p024`, showed a clear systematic
date shift** -- baseline's value for one date appears in column-wise
under the FOLLOWING date, across at least 6 consecutive dates for
Маріинскій. Same shift signature documented earlier this session on
other pages; not investigated further here, flagged for whoever picks
up the row-completeness thread next.

**New QC check**: `check_repertoire_malformed_receipts` in
`pipeline/quality_checks.py`, matching `check_repertoire_unknown_
theater`'s pattern -- flags a `receipts_text` with no р./p. rubles
marker at all. Run against the Gate 3 output (with 1903-04's stale
pre-fix pages excluded, superseded by the corrected re-run): 111 flags
across 28/332 pages, concentrated rather than scattered (two pages
alone -- `1904-05_p000`/`p008` -- accounted for 42 of the 111).

**Spot-checked per RG's request ("spot check to see whether these are
non-determined or structural") before fixing anything -- and found
THREE distinct causes, not one:**

1. **Pure model non-determinism (the majority).** Re-ran
   `repertoire_1904-05_p000` alone, same crop, same prompt, fresh
   sample: every previously-malformed row came back perfect, INCLUDING
   one (`138` -> `1553 р. 60 к.`) that looked like a genuine misread,
   not just missing units. Row alignment (dates, work titles) was
   already 100% correct in the ORIGINAL malformed run -- only the
   receipts reading varied, which is the signature of sampling
   variance on this one API call, not a geometric/crop defect (which
   would hit every row in a column identically). Re-ran all 28 flagged
   pages: 111 -> 40 flags, 28 -> 21 pages. Merged the resampled output
   back over the originals.

2. **Genuine crop clipping, but content-driven, not the Gate 3
   divider defect** -- `repertoire_1903-04_p030`'s Александринскій
   column is a GUEST GERMAN TROUPE's repertoire (titles like "Adelaide,
   Schauspiel", "Liebes-Manöver, Lustspiel"). German genre/title text
   runs measurably longer than this corpus's usual Russian
   abbreviations, and the column is clipped on the right -- confirmed
   directly in the crop image, every entry cut off mid-word
   ("Schau[spiel]", "Dra[ma]"), reproducing byte-identical across the
   resample (ruling out non-determinism). `theater_pad`'s fixed 15px
   isn't enough for this troupe's wider typesetting. Not fixed this
   session -- narrow, apparently tied to specific guest-troupe pages,
   worth a wider-pad retry rather than a season-level change.

3. **Field-mapping confusion, not a formatting or crop issue at
   all** -- `repertoire_1903-04_p028`'s `receipts_text` for two rows
   contains an entire multi-work benefit/gala program description
   ("5-я и 7-я сц. 1-го д. тр. Макбетъ 2-я карт. 2-го д. и 2-я карт.
   3-го д. оп. Пиковая дама..." -- five different works' excerpt
   scenes) instead of a receipts figure. These look like genuinely
   unusual rows with no standard box-office total printed (a special
   gala night), and the model put the descriptive text in the wrong
   field rather than `annotation`. Distinct from #2: this is a schema/
   prompt-adherence issue on an unusual row shape, not a geometric
   clipping issue.

**Not yet done**: none of #2/#3 fixed -- both are narrow and
page-specific enough that documenting them (this addendum) seemed more
proportionate than a targeted prompt or padding change for what may be
a handful of pages corpus-wide; escalating the sample scorecard to the
full 332 pages if the `1902-03_p024`-style shift turns out not to be
isolated.

### Addendum (2026-09-10): `1902-03_p024`'s date shift root-caused and
fixed (non-determinism); new `check_repertoire_cross_theater_date_
mismatch` QC check built to catch this pattern going forward

**Root cause, confirmed against the scan**: the date-only column
under-split one compound day -- "2 Воскрес." prints as two sessions
(morning/evening, each with its own receipts figure) on the actual
page, but the original column-wise date-only read returned it as a
single row. `merge_columnwise_page` (`pipeline/schemas/
repertoire_columnwise.py`) aligns each theater's rows against that
date-only column's calendar POSITIONALLY, so undercounting one day by
one row shifted every date after it, for the rest of the page --
consistent with the "baseline's value for one date appears under the
FOLLOWING date" signature already noted above, and a much more severe
consequence than a single bad cell: every downstream value stays
individually well-formed, just attached to the wrong date, so nothing
already in `quality_checks.py` caught it.

**Fix confirmed, not designed**: re-ran the single page fresh (same
crop, same prompts, no code change) via `run_pilot.py --column-level
--cropped-images`. The new date-only read correctly split "2 Воскрес."
into morning/evening and correctly left "8 Суббота." dark; every value
on the page then matched the full-page baseline exactly. Same
diagnosis as cause #1 above (pure model non-determinism on the
date-only call, not a crop/structural defect) -- merged the corrected
result back over the original in `raw_columnwise/`.

**The open question this left**: how often does this pattern recur
across the full 332-page corpus, given it's invisible to every
per-cell QC check that already exists. Built
`check_repertoire_cross_theater_date_mismatch` in
`pipeline/quality_checks.py` to catch it directly, without needing a
baseline comparison: since every theater on one page aligns against
the SAME date-only calendar, a real under/over-count there can make
*different* theaters land on different outcomes (one theater's row
count may happen to match the wrong calendar length and align
positionally anyway; another's may not, and fall through to
`merge_columnwise_page`'s compound-day reconciliation fallback) --
producing a direct, single-page, cross-theater disagreement on the
DATE SEQUENCE the page covers. The check compares each theater's
distinct date_text sequence (consecutive repeats of one date_text --
the legitimate compound-day signature -- collapsed before comparing)
and deliberately does NOT compare row counts, since compound-day
splitting is a genuine per-theater property, not a per-page one
(`_theater_days`'s docstring, `repertoire_columnwise.py`): a 13-row
Маріинскій column and a 12-row Александринскій column covering the
same 12 calendar dates are both correct.

**Validated, not just plausible**: run against the full current Gate 3
output (332 pages, 263 with 2+ theaters to compare) -- 0 mismatches.
Confirms the cross-theater date-sequence invariant holds cleanly once
the divider/crop fixes are in place, so the check is a clean signal
rather than one needing a tolerance band, AND is consistent with the
sample-scorecard shift pattern being isolated to `p024` rather than
widespread -- answering the "not investigated further" question left
open above without needing the full-corpus baseline-comparison
escalation that was flagged as a fallback option.

Wired into `main()` alongside `check_repertoire_unknown_theater` and
`check_repertoire_malformed_receipts` (same `for raw_dir in (page,
row, column)` loop) -- the underlying invariant (one printed table,
one shared calendar, every theater column reporting the same days)
isn't specific to column-wise extraction even though the causal bug
that motivated it is, so it runs against any raw_dir.

### Addendum (2026-09-10): causes #2 and #3 above (German-troupe crop
clipping, gala-program field mapping) fixed and verified

Both diagnosed causes from the previous addendum applied and confirmed
against a fresh re-run of the affected pages -- neither was a blind
guess, each was pixel/scan-verified before and after.

**Cause #2 fixed -- `theater_pad` override, scoped to `1903-04`.**
`repertoire_1903-04_p030`'s Александринскій column carries a guest
German troupe's repertoire across several weeks; German titles/
receipts run past the default `theater_pad=15`'s crop edge
(`pipeline/row_detect.py`'s `detect_columns`). Confirmed the fix by
direct pixel comparison, not assumption: at `theater_pad=150`, every
truncated title and figure on that column comes back complete
("Adelaide, Schau" -> "Adelaide, Schauspiel.", "26" -> "2634 p. 80"),
while the neighboring Михайловскій crop -- which absorbs the same
overlap from its own side -- stays completely unambiguous (own header,
clean rule, no content confusion). This is real printed margin the
default pad wasn't using, not a divider-position error.

Not raised as the new global default: the narrowest spread-format
seasons' columns are only ~300px wide (vs. ~500-525px for 1903-04), and
a symmetric 150px pad from each neighbor there would consume nearly the
whole column, risking a narrow theater's own content being swallowed by
the overlap. Instead, added an optional `theater_pad` field to a
column-bounds GROUP (`docs/repertoire_column_bounds.json`, defaulting
to 15 when absent) and threaded it through in `pipeline/run_pilot.py`'s
`detect_columns(...)` call -- set to 150 on `1903-04:0`/`1903-04:1`
only.

Verified: re-ran `repertoire_1903-04_p030` fresh with the new config.
Every previously-truncated title and receipts figure on the
Александринскій column now comes back complete and matches what the
Михайловскій crop's own leftover-overlap text already showed verbatim
(e.g. "2789 p. 30", "1813 p. —", "2077 p. 25"). `check_repertoire_
malformed_receipts` against the re-run: 0 flags (was flagging this
page before the fix). Merged the corrected output into
`raw_columnwise_1903fix2/`.

**Cause #3 fixed -- prompt clarification for `receipts_text`.** Added
an explicit instruction to `pipeline/prompts/
repertoire_theateronly_system.txt`'s `receipts_text` bullet: when a row
is a benefit/gala program listing several works' scene excerpts with NO
box-office figure printed anywhere in the cell, put the excerpts in
`works` as usual and leave `receipts_text` OMITTED -- never copy
`works`/`annotation` text into it as a fallback. The model had
correctly captured the charity heading in `annotation` and the 6 works
in `works` already; the only wrong field was `receipts_text` duplicating
that same text when no figure existed to put there.

Verified: re-ran `repertoire_1903-04_p028` fresh with the new prompt.
Both previously-affected rows ("21 Суббота", "22 Воскрес.") now return
`receipts_text=None`, with `annotation` and `works` unchanged from the
already-correct original read. `check_repertoire_malformed_receipts`:
0 flags on this page (was flagging it before). Merged into
`raw_columnwise_1903fix2/`.

**Not a concern from this fix, but worth noting**: the re-run's fresh
date-only/theater-only calls happened to spell the same theater
"Мариинскій" (modern и) rather than "Маріинскій" (pre-reform і) on
several rows -- `check_repertoire_unknown_theater`'s already-documented
`modernized_theater_spelling` case (2026-09-01 addendum), pure
call-to-call non-determinism, unrelated to either fix applied here and
not chased further.

Both fixes re-verified with `check_repertoire_cross_theater_date_
mismatch` too (0 flags on both re-run pages) -- confirms neither change
introduced the date-shift failure mode from the previous addendum.

**Regression check on `theater_pad=150`, not just the target page.**
Re-ran `repertoire_1903-04_p010` (an unaffected, non-German-troupe page
already in `raw_columnwise_1903fix2/`) fresh with the new config, to
check the wider pad doesn't leak real content between columns
elsewhere in the same season. It came back with every Михайловскій
receipts figure missing its kopecks portion ("156 р. 13 к." -> "156
р.", same for all 11 rows) -- looked at first like exactly the kind of
side effect a wider pad could cause. Ran a control before concluding
anything: re-ran the SAME page with the OLD default (`theater_pad`
override removed from a scratch copy of the config) -- the identical
kopecks-loss pattern appeared there too, on every row, unrelated to the
pad change entirely. This is the corpus's already-documented per-call
non-determinism (same diagnostic method as the malformed-receipts
spot-check earlier in this issue), not a regression from widening
`theater_pad` -- the wider pad only added overlap to Михайловскій's
LEFT edge (absorbing more of Александринскій's real content, itself
confirmed harmless earlier), never touched its own right edge where its
real content sits.

### Addendum (2026-09-10): before loading this corpus into the DB --
consolidated the canonical raw JSON, and closed a real risk in
`parse_and_validate.py`'s hand-verified repair tables

Asked (before scoping out the actual DB-load step) whether anything else
needed doing for the single-page-format seasons. Found five things by
actually checking rather than assuming; two are addressed here.

**1. No single clean corpus directory existed.** The scratch
`raw_columnwise/` still held the STALE pre-fix `1903-04` pages
side-by-side with the corrected `raw_columnwise_1903fix2/` -- 332 vs. 38
overlapping on the same page_ids. Consolidated into
`outputs/gate3_columnwise/raw_columnwise/` (332 files, every non-1903-04
page from the original Gate 3 run plus all 38 corrected `1903-04` pages
from `raw_columnwise_1903fix2/`, stale versions never copied). Verified:
0 duplicate page_ids, and `quality_checks.py`'s three Repertoire checks
return identical counts here as against the scratch sources (28
`malformed_receipts` / 19 pages, 370 `unknown_theater` [337
modernized-spelling + 33 unrecognized], 0 `cross_theater_date_mismatch`).
See `outputs/gate3_columnwise/README.md` for full provenance.

**5. `parse_and_validate.py`'s hand-verified Repertoire repair tables
are keyed to baseline's session ORDERING, which column-wise doesn't
share -- a real misapplication risk, not just a hygiene concern.**
`_REPERTOIRE_MONTH_FIXES`, `_REPERTOIRE_SESSION_DATE_FIXES`,
`_REPERTOIRE_FIELD_OVERRIDES`, `_REPERTOIRE_SESSION_INSERTIONS`,
`_REPERTOIRE_FABRICATED_SESSIONS`, and `_REPERTOIRE_DUPLICATE_SESSIONS`
all key their fixes to a 1-based sequential INDEX into
`parsed["sessions"]`, hand-verified against the single-call baseline
extraction's ordering (interleaved by date across every theater on the
page). Column-wise's merged output orders sessions GROUPED BY THEATER
instead (confirmed directly against the raw JSON) -- a fundamentally
different ordering, so the same index in column-wise output very likely
points at a different session's data entirely. Six of these page_ids are
part of the Gate 3 corpus (`1899-00_p037`, `1907-08_p000`,
`1902-03_p008`, `1904-05_p021`, `1903-04_p008`, `1900-01_p009`,
`1905-06_p005`, `1905-06_p011`), so this was live, not hypothetical.

Confirmed the risk directly rather than assuming it: ran
`_repair_repertoire` against `1904-05_p021`'s column-wise data with
`source="baseline"` (i.e. the OLD unconditional behavior) -- it silently
no-op'd only because that page's index-40 target happened to fall
outside column-wise's shorter 32-session list, not because of any real
protection. On a different page the same index could easily have landed
in-range and overwritten the wrong row.

**Fixed**: added a `source` parameter to `_repair_repertoire` (and an
`--extraction-source {baseline,columnwise,rowlevel}` CLI flag, default
`baseline` so every existing/older run's behavior is unchanged) that
skips all six index-keyed tables when `source != "baseline"`.
`_REPERTOIRE_YEAR_FIXES`/`_REPERTOIRE_DAY_FIXES` stay active
unconditionally -- both match by VALUE (the session's own
`year_text`/`date_text` equals a confirmed-wrong string), which is
order-independent and can only fire if that exact wrong string is
actually present.

Smoke-tested end to end, not just the repair function in isolation: ran
`parse_and_validate.py --extraction-source columnwise` against the full
332-page consolidated corpus -- 0 validation errors, 8664 `event_entry`
rows, 8804 `event_entry_performance` rows. Confirms both that the new
gating works and that column-wise's merged JSON shape validates cleanly
against `RepertoirePage`/`flatten_repertoire_page` with no changes needed
there.

**Deliberately NOT done here**: none of the 6 gated pages' original
defects have been re-verified against column-wise's own read yet (column-
wise might not even reproduce the same failure -- it's a structurally
different extraction, not just a re-run) -- until each is checked against
its own scan and given a content-keyed fix if the defect recurs, those 6
pages parse with `_repair_repertoire` contributing nothing for them,
which is the safe state, not the finished one. Items #2/#3/#4 from the
original five-item list (28 remaining malformed-receipts flags
concentrated in 1905-06, the 337 modernized-theater-spelling instances
with no Repertoire-side repair function yet, the 33 unrecognized-theater-
field instances, and the 178/332 "partial"-merge pages with unresolved
slots) are also still open, not addressed by this addendum.

### Addendum (2026-09-10): all 370 `unknown_theater` flags fixed --
one was three DISTINCT underlying patterns, not one, found by tracing
each to the real column it belongs to

Picked up items #2/#3 (theater-field flags) from the previous addendum's
open list. Broke the 33 `unrecognized_theater_field` flags down by
page -- all 3 pages, all in 1903-04/1907-08 -- and scan-verified each
against its own crop (matching works/receipts back to the real column,
not guessing from the wrong string), which turned up three genuinely
different failure shapes hiding behind one flag type:

1. **`repertoire_1903-04_p032`**: `'С.-Петербургский театр.'` -- the
   model substituted the page's own generic running header ("С.-
   Петербургскіе театры.", printed above every column's own header) for
   the column-specific one. Confirmed genuinely Маріинскій: the
   session's works ("Царя, оп." -> "Жизнь за Царя", "Волшебная флейта")
   match that theater's own crop row for row, receipts included.
2. **`repertoire_1907-08_p024`**: `'бургскіе театры. Александрийскій
   театръ.'` -- the tail of that same generic header concatenated with
   a slightly misspelled real header. Confirmed genuinely
   Александринскій by its Russian spoken-drama titles ("Холопы",
   "Смерть Іоанна Грознаго", "Урокъ танцевъ").
3. **`repertoire_1907-08_p008`**: `'Александровскій театръ.'` -- NOT a
   header-mixing or spelling-drift case: this string doesn't resemble
   either the real per-column header or the running header at all.
   Confirmed genuinely Михайловскій by direct crop comparison -- French
   works ("commissaire est bon enfant", "L'espionne") and exact receipts
   figures (1413 p. 88 к., 614 p. 88 к., ...) match that crop row for
   row. A plain, untraceable model error, content-matched to the
   correct theater rather than pattern-matched from the wrong one.

Also broke down all 337 `modernized_theater_spelling` flags (27 pages) by
theater name -- every single one is "Мариинскій" (with or without the
"театръ." suffix); no other KNOWN_THEATERS name showed this drift in the
theater field.

**Fixed, both value-matched so safe for any extraction source**: added
`_REPERTOIRE_THEATER_FIELD_FIXES` (the 3 confirmed exact-string cases
above) and `_repair_repertoire_theater_spelling` (a Мариинскій-\>
Маріинскій regex fix for the theater field, mirroring Roster's
`_repair_mariinsky_spelling` but reimplemented since it targets a
session's `theater` field rather than an entry's
`heading_path`/`institution`) to `pipeline/parse_and_validate.py`, wired
into `_repair_repertoire` and logged the same way as its other fixes.

Verified against the full 332-page consolidated corpus, not just the
flagged pages: re-ran `parse_and_validate.py --extraction-source
columnwise` end to end -- 337 spelling fixes + 33 field fixes logged
(exactly the flagged counts, nothing more/less), 0 validation errors,
same 8664 `event_entry` row count as before, and a direct grep of the
output `event_entry.csv` for every wrong string confirms 0 remain.

All `unknown_theater` items from the outstanding list are now closed.
Still open: the 28 malformed-receipts flags concentrated in 1905-06, and
the 178/332 "partial"-merge pages with unresolved slots.

### Addendum (2026-09-10): the 28 malformed-receipts flags triaged down to
7 genuine printed anomalies -- most were a check bug, not a data bug; one
real crop-clipping fix applied and verified

Went through all 28 by hand, scan-verifying rather than guessing, and
found the check itself was wrong far more often than the data was.

**17 of 28 were false positives in `check_repertoire_malformed_receipts`
itself**, not extraction problems. `_RECEIPTS_UNIT_RE` required a digit
immediately before the р./p. marker -- but confirmed against the scan,
this corpus legitimately prints a receipts figure with NOTHING before
the marker at all, two different ways: a dash for a fully-missing figure
("— р. — к.", a Chaliapin benefit night with no box-office figure
printed at all -- 15 instances) or plain blank space ("р.    к.", a
УТРО half of a compound day with nothing recorded -- 2 instances,
including one where I'd first miscategorized it as "no dash present" and
had to look again). Both are genuine, verbatim-correct printed
content -- fixed the regex to just check for the marker's presence,
regardless of what precedes it (`[рp]\.?`, matching what the check's own
docstring already claimed to do). First attempt at the fix
(`[рp]\.`, period required) overcorrected and produced 60+ NEW false
positives from perfectly normal receipts whose punctuation after the
marker varies (comma/dash/colon/nothing instead of a period) -- caught by
re-running the check immediately after the "fix" instead of assuming it
worked, and corrected before it went anywhere near a commit.

**7 of the remaining 11 were genuine PRINTED TYPESETTING ERRORS in the
original yearbooks, correctly transcribed verbatim -- not extraction
bugs, and not to be corrected.** Every one has the rubles marker printed
as something other than "р."/"p." (д., г., or к. -- the same letter as
the kopecks marker, twice in a row): `1901-02_p026` ("1495 д. 25 к."),
`1904-05_p009` ("736 к. 49 к."), `1905-06_p017`/`p018`/`p043`,
`1907-08_p000`/`p024`. Confirmed genuine by direct scan comparison on
three of these (p018, p009, p043) rather than assuming the pattern held
for all seven: in every case the model's output matches the PRINTED page
exactly, glyph for glyph -- this is the original book's own typesetting
error, not a misread. (One of these, p018's "г." for "р.", I had
initially misread as a model error on first glance -- the two glyphs are
genuinely easy to confuse at this resolution; a second, closer look at
the same crop corrected that.) Per this project's core verbatim-
preservation mandate, these are LEFT AS EXTRACTED, not "fixed" to what
the printer presumably meant -- `check_repertoire_malformed_receipts`
flagging them is still useful (a human reviewing the data benefits from
knowing the source itself is anomalous here), just not actionable as a
pipeline defect.

**5 of 11 (2 on `1907-08_p030`, 3 on `1907-08_p032`) were bare digits
with no marker at all** -- resampled to separate non-determinism from
something structural (same method as the earlier malformed-receipts
triage). `p032`'s 3 resolved cleanly on resample (pure non-determinism).
`p030`'s 2 did NOT -- persisted byte-identical across an independent
resample, the deterministic signature of a real clip. Rendering the
page's own rightmost 10% unclipped (bypassing `docs/
repertoire_crop_bounds.json`'s crop entirely) confirmed it directly: both
figures ("466 p. 55 к.", "1133 p. — к.") are fully legible just past the
season's old x1=0.96 boundary, with the true table border sitting at
~0.991 of full page width -- the SAME class of fix as 1903-04's x1
0.90->0.95 earlier in this issue, on the same last/rightmost theater
column (Михайловскій, whose crop always extends to the image's own
right edge -- so when the crop itself is too narrow, nothing short of
widening it can help). Corrected 1907-08's x1 0.96->0.99
(`docs/repertoire_crop_bounds.json`).

Verified against the WHOLE season, not just the one flagged page: re-ran
all 50 `1907-08` pages fresh through crop + column detection +
extraction. `check_repertoire_malformed_receipts`: p030's 2 flags gone,
0 new flags introduced anywhere in the season (52 total across the
season are the 2 genuine-typo cases already characterized above, both
correctly left alone). `check_repertoire_cross_theater_date_mismatch`:
still 0. Merged the corrected season into
`outputs/gate3_columnwise/raw_columnwise/`, re-ran the full 332-page
`parse_and_validate.py --extraction-source columnwise` smoke test again
-- 0 real validation errors, 0 remaining bad theater strings in the
output CSV.

**Final count**: 7 genuine flags remain in the corpus, all confirmed
printed-source anomalies, correctly transcribed and intentionally left
as-is. The malformed-receipts item is closed. Still open: the 178/332
"partial"-merge pages with unresolved slots.

### Addendum (2026-09-10): built and ran a two-tier repair pass for the
missing-theater problem -- measured coverage 48% -> 97.3%, after finding
and fixing a real duplication bug AND a real infrastructure hang

The 178/332 "partial"-merge item above understated the problem: measured
directly (counting distinct theaters actually present per page, not
trusting the page-level "partial" label), 171/332 pages (51.5%) were
missing at least one whole theater's data outright -- 102 missing one,
49 missing two, 20 missing all three. Root cause: `merge_columnwise_page`
refuses a theater's whole page rather than guess when its own row count
doesn't reconcile against the date-only column's day count (a
deliberate, correct design choice per that function's own docstring --
but 271/996 theater-merge-attempts (27.2%) hit it in practice, most
(55%) an exact ±1 day-count mismatch matching the already-diagnosed
`1902-03_p024` pattern, the rest (41%) larger mismatches implying
MULTIPLE missed compound-day splits on the same page, plus one 100-row
outlier that's a distinct extraction glitch).

**Built `pipeline/repair_columnwise_merge.py`**: a two-tier repair for
every theater `merge_columnwise_page` refused. Tier 1 resamples the SAME
column-wise method (fresh date-only + theater-only calls, re-merged) --
validated on a random 12-case sample before running at scale: recovers
about half outright, including large mismatches, not just off-by-one
ones, with no extra scrutiny needed since it's the same trusted method.
Tier 2, for whatever's still stuck, falls back to one whole-page
baseline call and takes that theater's sessions from it -- recovers
coverage in every case tested but not necessarily the same reliability
(baseline is the method known_issues.md #1/#68 already documents as
prone to cross-date bleed), so every tier-2 row is marked
`_repair_tier: "baseline_fallback"` and logged as `NEEDS REVIEW` in the
repair report, never silently treated as equivalent to a column-wise
read.

**A theater-name matching bug, caught before it reached real numbers**:
comparing theater strings by exact equality missed that one call can
spell a theater in modern Cyrillic (и) while another spells it correctly
(pre-reform і) -- on `1899-00_p026` this made a genuine, present
recovery register as `unrecovered`. Fixed by reusing the existing
modernized-spelling resolver for every match in the repair script, not
just the exact string.

**Ran at full scale (all 332 pages, 3 season-specific crop/pad
configs)** -- and found a SECOND, more serious bug checking the result
for regressions rather than trusting the coverage number alone: 35 of
332 pages had a theater's rows doubled. Root cause, confirmed on
`1903-04_p030`: the script excluded already-good sessions from a failed
theater's OWN raw JSON by exact string match against the merge report's
theater name, but that merge report can itself be stale or garbled (this
page's said "Маріинскій т.", truncated, while its own already-present
sessions were correctly labeled "Маріинскій театръ.") -- the exclusion
silently failed to match, so tier 1's (also successful) fresh resample
got appended ON TOP of the sessions already there instead of replacing
them. Fixed by excluding via the same canonical-name resolver as the
matching fix above, not literal string equality. Given a subtle
assembly-logic bug had already produced one round of silently-wrong
output, re-ran the full repair pass CLEAN from scratch rather than trying
to patch the already-wrong merged files -- cost noted, not worked around,
per this project's stance that accuracy is the constraint here, not cost.

**A real infrastructure bug found along the way, not a data problem**:
the clean re-run stalled repeatedly -- established-but-silent TCP
connections to the API host sitting at 0% CPU for 5-30+ minutes with
zero progress, at every concurrency level tried. Isolated the cause with
a fresh, standalone client outside the running batch: the SAME endpoint,
including a real page-image call, returned in seconds both times, ruling
out a DashScope-side outage. The signature (fine in isolation, reliably
stalling only on a long-lived client under sustained use) matches a
NAT/middlebox silently dropping an idle keep-alive connection without a
proper close -- the socket still looks ESTABLISHED locally, but the
first request to reuse it from the pool hangs until something ends it,
and with no client-side timeout configured, nothing ever did (despite
`call_with_retry`'s retry loop already knowing how to handle
`APITimeoutError` -- the mechanism was always there, nothing timed-out
was ever handed to it). Fixed in both `repair_columnwise_merge.py` and
`run_pilot.py`: an explicit 120s client timeout, plus
`max_keepalive_connections=0` to force a fresh connection per request
(confirmed effective -- pace went from ~1 page per 4-5 minutes, with
nearly every request needing a full timeout-and-retry cycle, to steady
completion once applied).

**Final, stable numbers** (re-verified after the clean re-run, not
carried over from the buggy one): theater coverage 323/332 pages (97.3%,
up from 161/332 = 48.5% before any repair) with all 3 theaters present.
Of 202 distinct theater-repairs needed corpus-wide: 46 (22.8%) recovered
via tier 1 (fully trusted), 149 (73.8%) via tier 2 (flagged for review),
7 (3.5%) unrecovered after both tiers -- the SAME 7 both before and
after the duplication-bug fix, confirming they're genuinely hard rather
than an artifact:
- `1907-08_p001`/`p023`/`p025` (Новый), `1907-08_p000` (Михайловскій),
  `1907-08_p046` (Александринскій) -- 5 of 7 cluster in one season,
  worth a closer look as a group rather than one at a time.
- `1904-05_p000` (Михайловскій).
- `1903-04_p017` -- theater field reads "Московский театръ.", a name
  that doesn't match any KNOWN_THEATERS entry even modernized; likely
  the same kind of header-hallucination already confirmed elsewhere in
  this issue (`1907-08_p008`'s "Александровскій театръ."), not yet
  traced to its real theater.

Duplicate-session check after the fix: only 2 true duplicates remain
(byte-identical content repeated), both on `1899-00_p029` -- the same
page whose Малый театръ. tier-2 recovery was already the messiest in
the corpus (multiple overlapping partial reads), already flagged `NEEDS
REVIEW`, not a new problem. Separately, 86 sessions across 32 pages
share a (theater, date, session) key with DIFFERENT content, not
identical -- confirmed these are genuine distinct compound-day sessions
(different receipts, different works) that a tier-2 baseline call
didn't label "morning"/"evening" the way column-wise's per-theater
labels do; a real data-quality gap specific to baseline-recovered rows,
not a duplication bug.

Also fixed `check_repertoire_cross_theater_date_mismatch` while
verifying the repair pass, since it started producing noise the moment
theaters could carry independently-resampled date text: it compared
date_text VERBATIM, and 92 of a 109-flag sample were pages where two
independently-read calendars legitimately spell the same day
differently ("13 Среда" vs "13 Среда.", ъ/ь substitution) with no actual
date shift at all. Now compares only the leading day-number, narrowing
that sample to 17 real cases; re-measured on the final corrected corpus
at 12 remaining (a `Мартъ.`/`Январь`/`Май.` month-name-leaking-into-
date_text pattern on several, individual dropped days on others) --
still open, not investigated further this addendum.

Repair pass is applied and merged into
`outputs/gate3_columnwise/raw_columnwise/`; `pipeline/
repair_columnwise_merge.py` is the new script, `run_pilot.py`'s client
construction and `quality_checks.py`'s cross-theater-date-mismatch check
both carry fixes from this addendum. Not yet done: the 7 remaining
unrecovered theaters, and the 12 genuine cross-theater date mismatches.

### Addendum (2026-09-10/11): the 7 unrecovered theaters resolved --
theater coverage now 332/332 (100%); a separate, unrelated stale-metadata
bug found and fixed along the way

Went through each of the 7 by hand rather than accepting "unrecovered" at
face value, since that outcome string only means "the automated tiers
gave up," not "the content doesn't exist."

**6 of 7 turned out to be the SAME root cause, confirmed against the
scan for every one**: the theater is genuinely, entirely DARK (a plain
dash) for the page's whole printed date range. A column of nothing but
repeated dashes gives a vision model almost no distinguishing content to
anchor an accurate row count on, which is exactly what both
`merge_columnwise_page`'s reconciliation and a baseline whole-page read
depend on -- so both methods struggled with row-counting even though the
actual CONTENT (just "dark" repeated) is trivially unambiguous. Checked
`1907-08_p023`, `p046`, `p025`, `p000` (Михайловскій) and
`1904-05_p000` directly against their crops: 6/6 confirmed all-dash, 0
exceptions. Fixed by constructing `is_dark=True` sessions directly from
the page's OWN already-correct calendar (borrowed from whichever
theater on the same page DID reconcile) -- not a guess, a direct
transcription of what the scan shows, for exactly the number of
calendar days already confirmed correct by a sibling column.

**The 7th, `1903-04_p017`'s "Московский театръ."**, was a different,
already-familiar pattern: a hallucinated/generic theater name (see the
"С.-Петербургскій театр."/"Александровскій театръ." cases earlier in
this issue) that matched none of the page's real theaters and so never
recovered via either tier. A fresh baseline read of the page returned a
real, clean 11-row Большой театръ column (opera/ballet repertoire,
consistent with that theater) with no theater under any name resembling
"Московский" -- confirmed this is genuinely that page's real third
theater, just mislabeled at extraction time. Fixed by adding those rows
under the corrected canonical name.

**A separate, unrelated bug found auditing the fix**: two MORE pages
(`1901-02_p011`'s Новый, `1904-05_p026`'s Михайловскій) were ALSO
missing a theater, despite their `.columns.json` merge reports claiming
`ok=True` with real session counts (12 and 10 respectively) for exactly
that theater -- a genuine STALE-METADATA bug, not something the repair
pass caused (both pages' pre-repair `raw_columnwise/` files, untouched
by this session's repair work, already lacked the sessions their own
merge report claimed existed). Audited the whole corpus for the same
signature (a `.columns.json` entry marked `ok=True` whose claimed
theater has zero matching sessions in the paired `raw.json`) and found
2 more instances (`1907-08_p013`, `1907-08_p024`) that turned out to be
false alarms -- both were ALSO missing a DIFFERENT theater that WAS
correctly flagged `ok=False`, so the repair pass processed the whole
page anyway and incidentally fixed the stale entry as a side effect;
only pages where EVERY entry claimed `ok=True` (so the repair pass had
nothing to trigger on and copied the stale file straight through)
stayed broken. Both fixed the same way: `1901-02_p011`'s Новый had real,
substantial content (confirmed against the crop, not dark) so resampled
column-wise fresh first (still failed to reconcile) then recovered via
baseline fallback; `1904-05_p026`'s Михайловскій recovered via baseline
fallback directly. Root cause of the stale metadata itself not traced
further -- likely provenance drift from one of the several earlier
`1903-04`/`1907-08`-style re-runs this issue documents, predating this
session's repair work; worth keeping in mind if a "columns.json says ok"
signal is ever trusted again without cross-checking the paired raw.json.

**Final coverage: 332/332 pages (100%) with all 3 theaters present**,
up from 161/332 (48.5%) before any repair work this issue. Malformed-
receipts and cross-theater-date-mismatch counts are essentially
unchanged (11 and 13 respectively) -- the newly-added content didn't
introduce new problems at meaningful scale. The theater-coverage thread
from this issue is now closed.

### Addendum (2026-09-11): the 11 post-repair malformed-receipts flags
triaged individually -- 9 genuine typos, 1 more check-tolerance gap, 1
real content-drop bug fixed

Went through all 11 by hand rather than assuming the earlier "7 genuine
anomalies" characterization still covered whatever the repair pass had
added. It didn't, fully:

- **9 confirmed genuine printed typos** (the original 7, plus
  `1901-02_p011`'s "263 д. 64 к." -- visible in a crop already pulled
  earlier for an unrelated check -- and `1902-03_p019`'s "876 к. 18
  к.", freshly confirmed against the scan). Same category as before,
  left as-is.
- **`1901-02_p012`: a third legitimate way to represent "no figure
  printed"**. The row (a guest-troupe performance, "Гастроль г-жи Адель
  Зандрокъ... Die Cameliendame") genuinely has no receipts line under
  it in the scan -- confirmed directly. Already-tolerated siblings were
  `None`/blank and "— р. — к."; this call rendered the same absence as
  a bare "—" with no marker at all. Fixed `_RECEIPTS_UNIT_RE`'s caller
  in `check_repertoire_malformed_receipts` to also accept a
  dash-only `receipts_text` (`_BARE_DASH_RE`).
- **`1907-08_p036`: a genuine bug, not a formatting variant**. The "8
  Суббота" row has real printed content -- a benefit heading ("Въ
  пользу школы Императорскаго Женскаго Патріотическаго Общества.") and
  two real works ("На бойкомъ мѣстѣ", "Египетскія ночи") -- confirmed
  against the scan, but the extracted session had `works=[]` entirely,
  not just a missing receipts figure. Resampled the page fresh:
  Маріинскій failed to reconcile that time (worse, not better), but the
  underlying THEATER-ONLY read (kept in `.columns.json`'s `raw` section
  even though the merge itself failed) had the row exactly right,
  matching the scan detail for detail. Hand-applied that corrected row
  (annotation + both works, receipts_text=None) directly to the merged
  output -- another confirmation that a failed *merge* doesn't mean the
  underlying *read* was wrong, just that reconciliation couldn't place
  it automatically.

Final malformed-receipts count: 9 (all genuine, intentionally left
as-is). `pipeline/quality_checks.py` carries the bare-dash tolerance
fix.

### Addendum (2026-09-11): attempted a batch fix for the 13
cross-theater date mismatches, caused real (fully-recovered) data loss
doing it, reverted -- documenting the mistake and why WHOLE-PAGE
resampling is the wrong tool here

Resampled all 13 flagged pages fresh (the same cheap, established
tier-1 method used throughout this issue) -- every one came back with
`check_repertoire_cross_theater_date_mismatch` reporting 0 mismatches,
which looked like a clean, complete fix.

**It wasn't, and trusting that number without checking theater COUNT
alongside it was the mistake.** The check only compares theaters that
are actually present -- on a page where a fresh resample itself failed
to reconcile 1-2 theaters (a real risk on exactly these pages, since
they're already the corpus's hardest cases), there's nothing left to
disagree with, so the check reports "0 mismatches" whether the page has
all 3 theaters or only 1. Blindly copying the fresh resample's whole
page over the existing (already fully-repaired, 100%-coverage) file
overwrote several already-good, previously-recovered theaters with
nothing -- confirmed directly: `1903-04_p017` dropped back to 2
theaters (losing the Большой content this issue had already confirmed
and added), `1907-08_p000` dropped to 1, `1907-08_p030` dropped to 2.
Caught this by re-measuring theater coverage immediately after (not
trusting the date-mismatch number alone), which had fallen from 332/332
back toward the same shape as before the whole repair pass -- a real,
if temporary, regression back to square one for the pages it touched.

A first recovery attempt (restore each page from `repairfull2_A/B/C` --
the last known-good, 100%-coverage checkpoint -- then re-apply the SAME
per-theater replacements, scoped to only the specific theater causing
each page's mismatch rather than the whole page) surfaced a SECOND
version of the same mistake: several of the fresh resamples used as the
replacement SOURCE were themselves missing the exact theater being
replaced (one, `1903-04_p026`, had recovered ZERO theaters that
attempt), so the targeted per-theater swap deleted the existing good
data and added nothing back, the same failure mode at a smaller scope.

**Fully recovered, verified twice**: restored all 13 pages from
`repairfull2_A/B/C` again. Confirmed theater coverage back to 332/332,
the true-duplicate count back to 1 (the already-known messiest page,
`1899-00_p029`, unchanged), and malformed-receipts/unknown-theater
counts unchanged from before this attempt. `1903-04_p017`'s and
`1907-08_p000`'s SCAN-VERIFIED fixes (the ones added via direct crop
inspection + confirmed baseline content, not blind resampling) were
untouched throughout, since they were never part of either overwrite.
`cross_theater_date_mismatch` is back to its pre-attempt 13, genuinely
unfixed -- not silently broken, just honestly still open.

**The actual lesson, for whoever picks this thread back up**: resampling
a WHOLE page to fix ONE theater's date sequence is not safe on pages
that have already needed repair once -- the same difficulty that caused
the original problem can just as easily strike a DIFFERENT theater on
the resample, and "0 mismatches" from `check_repertoire_cross_theater_
date_mismatch` alone is not sufficient evidence of a clean fix on these
specific pages; theater COUNT must be checked in the same breath, every
time, exactly the discipline this issue used successfully for the
7-unrecovered-theaters addendum (which scan-verified each fix
individually rather than trusting an automated resample's aggregate
result). The 13 mismatches remain open, to be revisited with that
slower, individually-verified approach rather than a batch resample.

### Addendum (2026-09-11): the 13 cross-theater date mismatches, done
the slow way -- 11 of 13 fixed and scan-verified individually, 2
deliberately deferred

Went through each of the 13 by hand, checking the actual crop (date-only
and/or theater-only) before touching anything, per the lesson from the
previous addendum's mistake. Findings split into clean, well-evidenced
categories:

- **Genuinely dark days, dropped entirely from extraction** (5 cases):
  `1907-08_p030` (day 8), `1907-08_p000` (day 1), `1904-05_p005` (day
  1, less certain -- see below), `1907-08_p020` (days 17/19/21, a clean
  alternating content/dash pattern in the crop), `1903-04_p036`
  (Михайловскій collapsed to just 2 real rows, the other 10 genuinely
  dark per the crop). Fixed by inserting `is_dark=True` placeholder rows
  at the confirmed positions, matching a sibling theater's date_text
  exactly.
- **Spurious month-label row, no real content of its own** (1 case):
  `1903-04_p037`'s "Май." row -- confirmed via crop it's a genuine
  printed row (own table cell) but purely a transition marker with
  nothing under it; the sibling theaters correctly never created a slot
  for it. Fixed by dropping the row entirely, matching what the
  siblings already do.
- **Dropped annotation/content on an existing row** (1 case):
  `1907-08_p044`'s day 21 already had its works but was missing the
  benefit-performance annotation, and day 27 was missing outright.
  Resampled the page fresh (twice -- the first fresh attempt also
  failed to reconcile this theater, same recurring difficulty), and the
  raw per-crop theater-only read (kept in `.columns.json` even though
  the merge itself failed) had both the correct annotation and,
  combined with the calendar, confirmed day 27 as a plain dark row.
- **Genuine single-digit misread** (2 cases): `1902-03_p036`
  (Александринскій read "13" where the date-only crop clearly shows
  "15" -- confirmed at native resolution) and `1901-02_p019` (Малый's
  "1ъ Среда." is a "9"/"ъ" glyph confusion for "19 Среда.", unambiguous
  given its position between 18 and 20). Fixed by correcting the single
  wrong token, nothing else touched.
- **Crop-boundary clipping on the DATE column itself, not a model
  error** (1 case): `1903-04_p017`'s Малый/Новый date_text values were
  missing their leading day-digit entirely ("Суббота." instead of "6
  Суббота.") -- confirmed via the date-only crop that the digits are
  genuinely cut off by the crop's own left margin on this page, not
  misread. Reconstructed the correct digits positionally from
  Большой's independently-sourced (baseline, whole-page image, not
  subject to the same crop) calendar -- weekday names and content order
  matched exactly, including a compound-Sunday count difference (12
  rows vs Большой's 11) that confirmed the position-by-position mapping
  was right before applying it.

**2 deliberately deferred, not guessed at**:
- `1903-04_p004`: the "Октябрь." row is a genuine bare month-transition
  label (confirmed via the date-only crop), but unlike `p037`'s clean
  case, real content (Баядерка/1244.57) is misattributed to it, which
  cascades a one-position shift through several rows after it,
  including a compound benefit day. Reconstructing the correct
  row-by-row mapping is very likely possible but requires more careful,
  slower reconciliation than was safe to rush in this pass -- diagnosis
  recorded precisely here for whoever picks it up.
- `1899-00_p029`: already documented as the corpus's messiest page.
  Removed 5 further exact-duplicate sessions found while investigating
  (safe -- byte-identical repeats), but what's left still shows Малый
  and Новый with two overlapping, PARTIALLY CONFLICTING reads of the
  same date range (e.g. "16 Среда" with two different, non-duplicate
  work-title sets at the same receipts figure) -- and the crop revealed
  MORE real content rows than the current date framework accounts for,
  meaning the page's true calendar may need re-deriving from scratch
  rather than patched. Left as-is rather than risk a wrong
  reconstruction.

Also fixed two small side-issues found while verifying: a theater-name
punctuation inconsistency on `1907-08_p044` (two spellings of
Александринскій coexisting after a fix, normalized to one) and a
missing day 15 on `1907-08_p030`'s Михайловскій (added as an uncertain
dark placeholder, tagged `manual_uncertain_dark_placeholder` for future
review, since the crop's exact edge wasn't fully confirmed for this
one).

**Verified after all fixes**: theater coverage 332/332 (100%, unchanged
-- these fixes only added/corrected date labels and a handful of dark
placeholders, never removed a real theater), 0 true duplicate sessions
corpus-wide, malformed-receipts and unknown-theater counts unchanged.
`cross_theater_date_mismatch` down to 2 -- both deliberately deferred
with a precise diagnosis, not silently left broken.

### Addendum (2026-09-11): the `1903-04_p026` annotation/works split bug,
fixed before loading

Before proceeding to the DuckDB load, went back to the annotation/works
inconsistency spotted (but not fixed) while working `1903-04_p026`'s date
mismatch. Confirmed against the theater-only crop at full resolution:
Михайловскій театръ's Feb 4 row is a single printed cell listing FOUR
comedy titles under one receipts figure (482 р. 35 к.) -- "Les projets de
ma tante, com." / "Les romanesques, com." / "Mariage d'amour, com." /
"L'irrésolu, com." -- confirmed by the row's horizontal-divider boundaries
in the crop, which place all four lines and the single receipts number
inside one cell, with the neighboring Feb 5 and Feb 6 cells clearly
separated below it.

The raw extraction had split this one cell across two schema fields:
`annotation` held the first two titles, `works` held the last two. That's
not itself impossible -- the schema legitimately uses `works` for a
primary-title-plus-extras split (e.g. this same page's Alexandrinsky Feb 4:
"Ревизоръ, ком." as annotation + "Дѣло" as a `works` entry, a real
benefit-night structure) -- but here it doesn't hold up: the exact same
two pairs of titles appear on Feb 5 ("Mariage d'amour"/"L'irrésolu") and
Feb 6 ("Les projets de ma tante"/"Les romanesques") as plain `annotation`
text with empty `works`, on this very page. So splitting them across
`annotation`/`works` specifically on Feb 4 was an arbitrary artifact of
there being four text lines to place, not a real primary/extra
distinction -- and it mattered beyond cosmetics: per
`flatten_repertoire_page` (`pipeline/schemas/repertoire.py`), only
`works` entries become structured, indexed `event_entry_performance`
rows -- `annotation` is unindexed free text. Left as extracted, "Mariage
d'amour" and "L'irrésolu" would have shown up as structured, queryable
performances specifically on Feb 4 and nowhere else, even though the
exact same two titles are performed (per the same page) on Feb 5 with no
structured performance entry at all -- a misleading artifact for anyone
querying `research.performance` for these works.

Fixed by merging the two `works` titles back into `annotation` as
additional lines (matching how Feb 5/Feb 6 represent the identical pairs)
and clearing `works` to `[]`. No sessions added or removed -- verified
unchanged after the fix: 332/332 theater coverage, 0 true duplicates, 9
malformed-receipts, 2 cross-theater-date-mismatches (still only the two
deliberately deferred pages).

This was the last known content-correctness issue (as opposed to a
flagged, visible gap) in the column-wise Repertoire corpus. With this
fixed, `outputs/gate3_columnwise/raw_columnwise/` is ready to proceed to
`parse_and_validate.py` / `build_duckdb.py` -- the two deferred date-
mismatch pages remain open but are correctly flagged in
`quality_flags.csv`, not silently wrong.

### Addendum (2026-09-11): a completeness sweep -- "are we missing any
cells/text?" -- 412 blank-receipts sessions individually triaged, 7 real
bugs found and fixed, 1 new deferred row-shift page found

RG asked directly whether anything was still missing before proceeding
to the DB load. Investigated systematically: every non-dark session in
all 332 pages was checked for outright-missing fields (empty page,
missing theater/date, zero content at all) -- none found -- and then
specifically for blank `receipts_text`, since that's the one field that
can legitimately be blank (a genuine "no figure printed" case) *or*
silently lost, with no way to tell the two apart without checking the
scan. 412 non-dark sessions had blank receipts.

**First attempt was wrong and was fully reverted.** Tried two
shortcuts to avoid a full manual sweep: (1) pulling the pre-merge
per-crop read from each page's `.columns.json` `raw.theaters` data, and
(2) matching sessions by work-title/annotation content when (1) was
ambiguous. Both were unsafe in ways not caught until spot-checking
against the scan: (1) assumed the theater's own row-index numbering
aligned 1:1 with the shared calendar's `date_rows` index, which breaks
whenever the theater's own compound-day handling differs from the
calendar's (confirmed wrong on `1900-01_p022`: attached day 16's
receipts to day 15's row) -- and (2) content-signature matching isn't
reliable either, because titles repeat across many dates in a repertory
theater's bill, so a "unique match" isn't actually unique (silently
corrupted an unrelated, already-correct session on `1903-04_p036`
this way). Caught both via direct scan comparison, reverted every
change from both attempts back to the pre-attempt state, and verified
the revert precisely (touched-page blank-receipts counts matched the
original enumeration exactly, session by session) before redoing this
properly.

**Redone the reliable way: every one of the 61 flagged page/theater
pairs (n>=2 blank-receipts occurrences) checked individually against
the actual page scan**, date-column included in every crop so a date
could never be misread by position alone (the exact mistake that broke
the first attempt). Two clear categories emerged, and the split held up
under direct verification in every single case:

- **Genuinely blank in the source** (384 sessions corpus-wide, after
  fixes) -- benefit/charity performances, guest-artist and
  guest-troupe engagements, and A. Siloti / orchestra concert-series
  dates never had a box-office figure printed at all. Confirmed directly
  for dozens of these across every season 1899-00 through 1907-08,
  including two extended cases worth noting explicitly: `1907-08_p044`/
  `p046`/`p048`'s consecutive Михайловскій run (Ibsen/Andreev/Chekhov --
  Брандъ, Докторъ Штокманъ, Росмерсхольмъ, Жизнь человѣка, Горе отъ ума,
  Вишневый садъ) is a visiting dramatic company's engagement, confirmed
  via the scan to have no receipts printed for the entire run while
  Alexandrinsky sits dark for the same stretch -- and `1899-00_p032`/
  `1901-02_p032`/`1900-01_p030`/`1905-06_p038` etc.'s repeated
  "rehearsal / concert / repeat concert въ пользу инвалидовъ" triples
  are recurring annual war-veteran charity concerts, also genuinely
  receiptless every time they recur.

- **Real bugs, confirmed and fixed** (7 distinct issues, 6 pages, ~41
  data points corrected):
  - `1903-04_p018` (Мариинскій, 14 dates) and `1903-04_p032`
    (Маріинскій, 10 of 12 dates) -- a crop-clipping bug: the
    theater-only crop used for extraction was too narrow on the right
    edge, cutting the receipts sub-column out of the model's view
    entirely (title text survived because it sits further left in the
    cell). Confirmed by viewing the full, uncropped page scan, where
    every one of these figures is clearly printed. Recovered by reading
    the values directly off the full page. (The other 2 of `p032`'s 12
    flagged dates -- two grand multi-work charity benefits -- were
    confirmed genuinely blank, same as the pattern above.)
  - `1903-04_p032`'s second theater column, separately: not a receipts
    problem at all -- the column labeled `"С.-Петербургский театр."`
    in the raw JSON was never a real third theater. It's Александринскій
    театръ, mislabeled, with its `works`/`annotation` fields retaining
    garbled fragments of the real Alexandrinsky titles (confirmed via
    the scan: "Калигула,", "Невольницы.", "Горе отъ ума" etc. all
    matched real Alexandrinsky rows) while its `receipts_text` values
    were verbatim duplicates of Маріинскій's own figures for the same
    dates (down to the kopeck -- e.g. both showing "2713 р. 44 к." for
    31 Ср., impossible as independent box-office figures). This meant
    the corpus's own `theater-count histogram: {3: 332}` sanity check,
    and the "332/332 100% coverage" headline from the repair-pass work,
    both missed that this page's real Alexandrinsky content was gone --
    counting *a* third theater isn't the same as counting the *right*
    three. Reconstructed all 12 sessions from the scan and renamed the
    theater to `"Александринскій театръ."`.
  - `1903-04_p036` -- a localized 2-row swap: 24 Суббота's charity
    benefit (correctly blank) had 25 Воскрес's "Лордъ Квексъ" receipts
    figure (1045.92) attached to it, while 25 Воскрес itself showed
    blank. Every other row on the page was correctly aligned. Swapped
    the one misplaced value back to its correct row.
  - `1904-05_p042` (Маріинскій, 24 Воскрес) -- a plain missing figure,
    no special-event marker at all, receipts genuinely printed in the
    scan (2435.70) and simply dropped.
  - `1905-06_p042` (Маріинскій) -- the same swap pattern as `p036`: 8
    Суббота's charity benefit (correctly blank) had 9 Воскрес's real
    figure (2611.70) attached; swapped back. Plus a separate plain
    missing figure on 16 Воскрес (2826.70), no marker, genuinely
    printed and dropped.
  - `1905-06_p020` (Маріинскій, 18 Воскр. evening) -- the evening leg of
    a compound day (a benefit, correctly blank) had the *morning* leg's
    receipts figure duplicated onto it. Cleared.

- **1 new deferred issue, found but not fixed**: `1901-02_p028`
  (Мариинскій) has the same kind of row-alignment bug already on file
  for `1903-04_p004` -- every row from 16 Суббота onward is shifted by
  one position relative to the scan (confirmed: the JSON's "16 Суббота"
  receipts figure, 2965.15, actually belongs to the scan's "17
  Воскрес" row; a spanning "Безплатные спектакли для воспитанниковъ"
  note between 19 Вторн and 20 Среда got folded into 19 Вторн's own
  session incorrectly). Needs the same careful, deliberate row-by-row
  reconstruction as `1903-04_p004` -- not attempted here, logged for
  the same future pass.

**Verified after all fixes**: 332/332 theater coverage (unchanged --
these were content corrections, not row additions/removals except the
Alexandrinsky reconstruction, which replaced 12 already-counted
sessions rather than adding a theater), 0 true duplicate sessions, 9
malformed-receipts (unchanged, still the same genuine typos), 2
cross-theater-date-mismatches (still only the 2 pages deliberately
deferred -- `1899-00_p029` and `1903-04_p004` -- `1901-02_p028`'s new
row-shift issue doesn't happen to trip this particular check, which is
exactly why a targeted completeness sweep like this one was needed
rather than relying on the existing flags alone). 384 non-dark sessions
still have blank receipts_text, all individually scan-confirmed
genuine.

The corpus is ready to proceed to `parse_and_validate.py` /
`build_duckdb.py`, with three pages' known, precisely-diagnosed gaps
left open rather than guessed at: `1899-00_p029`, `1903-04_p004`, and
now `1901-02_p028`.

### Addendum (2026-09-11): merged the corrected Gate 3 corpus into
`outputs/full_run/` -- two real pipeline bugs caught before they could
do damage; publish step deliberately deferred

With the completeness sweep done, ran the corrected 332-page corpus
through the standalone `parse_and_validate.py`/`build_duckdb.py` pair
first (`outputs/gate3_columnwise/imperial_theaters.duckdb` -- 332
source_pages, 11,827 event_entry rows, 6 theaters roughly balanced, 8
seasons, ~11.8M rubles total receipts, all sanity-checked directly).
That was a standalone deliverable, not yet touching the published
database.

RG then asked about merging into `outputs/full_run/` -- the actual
published/served database (HF dataset repo + Cloud Run `spiski`). Spot
check confirmed the *current* `full_run` Repertoire data for these 8
seasons is the old single-call baseline extraction (file predates all
of this project's column-wise work), independently confirmed wrong
earlier (`repertoire_1902-03_p024`: wrong date labels, wrong dark/
performed status, wrong compound-day handling). Worked through what
merging would actually cost before doing it:

- Checked (not assumed) whether anything downstream already depends on
  the old data: `entities.work_link` had 10,697 rows and the published
  `research` layer had 13,009 events / 10,697 performances / 2,008
  resolved works keyed to these exact 332 pages' old, position-based
  IDs (`{page_id}__s{NNN}__w{M}`, not content-addressed).
- Traced the actual mechanism: `raw_performance_id` has no FK back to
  `raw.event_entry_performance`, so a raw content swap wouldn't error
  or cascade, it would leave those rows silently dangling. But
  `entities.work_link`/`work_genre_candidate` are fully DROP+rebuilt by
  `build_entities.py` on every run regardless, with no persisted
  manual-review state for works (unlike `person_link`/`person_candidate`,
  which explicitly preserve prior decisions) -- and `work_id` is a
  deterministic `uuid5` hash of the normalized title, not random, so
  canonical work identities survive a rebuild for unchanged titles.
  Confirmed directly post-merge: "Евгеній Онѣгинъ"'s dominant work_id
  (`788fd62c-...`) is byte-identical before and after.
- Considered and rejected an explicit supersede-rather-than-delete
  scheme (the pattern this project already uses for confirmed person
  merges, `entities.person.superseded_by_person_id`) -- that principle
  exists for genuine ambiguity where either identity could reasonably
  be revisited later, not for a confirmed extraction bug with no
  legitimate alternative reading. Checked whether anyone/anything
  external currently depends on the old IDs: no -- the HF repo is
  private and Cloud Run is password-gated, so the dataset isn't in a
  state where outside citation is realistic yet. Decided on a straight
  overwrite instead, provided downstream tables get rebuilt afterward
  so nothing is left dangling.

**Safety approach**: confirmed RG's backup drive had arrived (the
standing "never overwrite `outputs/`" guardrail from the 2026-09-07
machine-migration session was explicitly about having no backup yet),
then copied `outputs/full_run/` (146M) wholesale to
`outputs/full_run_merge_work/` before touching anything -- verified
byte-identical (`diff -rq`, exit 0) -- and did every step of the merge
against that copy. `outputs/full_run/` itself stayed completely
untouched until the final, deliberate swap-in.

**The merge itself**, all inside `full_run_merge_work/`:

1. Overwrote the 332 pages' raw JSON in the copy with the verified
   `raw_columnwise/` versions (confirmed via `diff -rq`: exactly and
   only those 332 files changed).
2. **First real bug caught**: initially ran `parse_and_validate.py
   --extraction-source columnwise` across the full 1,349-page manifest
   in one pass. The flag's own docstring warns this disables several
   index-keyed hand-fix tables globally -- safe for the 332 column-wise
   pages (their row ordering differs from what those fixes were
   verified against), but wrong for the other 1,017 pages, which are
   still genuinely baseline-extracted and need those exact fixes. The
   docstring even names specific page_ids proving this isn't
   hypothetical. Caught before running `build_duckdb.py`, discarded
   that pass, and redid it as two separate runs (332 pages with
   `--extraction-source columnwise`, the other 1,017 with the
   `baseline` default), then merged the resulting CSVs. Confirmed
   post-merge that the index-keyed fixes (`repertoire_year_fixed`,
   `repertoire_month_fixed`, `repertoire_session_date_fixed`,
   `repertoire_fabricated_dropped`) correctly fired in the baseline
   pass, which the wrong single-pass run would have silently skipped
   for all 1,349 pages.
3. Ran `build_duckdb.py` on the merged, full manifest. Verified against
   the old published database: `source_pages` unchanged (1,349),
   non-Gate3 `event_entry` row count for the untouched 1,017 pages
   exactly unchanged (12,094 = 12,094), `person_entry` completely
   unchanged (21,168 = 21,168). A row-content diff on those same
   untouched pages found 114 differing rows -- checked every one:
   all 114 are exactly and only `{city, theater}` field changes (a
   `city` value getting filled in where it was `NULL`, or the
   pre-existing `Мариинскій`->`Маріинскій` spelling fix), pipeline
   improvements that simply hadn't been re-applied since the old
   database was last built (Aug 28) -- zero unexplained differences,
   nothing caused by the merge itself.
4. **Second real bug caught**: before running `build_entities.py`,
   recognized that its person-identity-continuity logic
   (`entry_to_current_person`) only works if `entities.person_link`
   already exists in the target database -- checks the same DB
   connection it's given, nothing else. The freshly-built merged
   database had no `entities` schema at all yet, so running it as-is
   would have treated every person as "never seen before" and minted
   brand-new random UUIDs for all 2,900 live people, discarding 1,022
   prior merge-log entries and 23 already-reviewed candidate decisions.
   Fixed by `ATTACH`-ing the old database and copying the entire
   `entities` schema across before running `build_entities.py`, so it
   had the same continuity state it would have had from an ordinary
   in-place re-run. Verified after: `entities.person_link` byte-
   identical (21,168 rows, set-equal), `person_merge_log` unchanged
   (1,022 = 1,022), `work` correctly regenerated (4,530 -> 4,412,
   reflecting the corrected content) with confirmed-stable IDs.
5. **Third catch**: `build_research_model.py` failed outright --
   `analysis.event_entry_date_check` didn't exist, because
   `validate_performance_dates.py` (documented in CLAUDE.md's normal
   pipeline order, between `build_entities.py` and `link_wikidata.py`)
   had been left out of the plan entirely. Ran it (23,921 rows, the
   usual verified/no_date/corrected/unparseable/unresolved/
   intra_block_disagreement breakdown), then `build_research_model.py`
   succeeded.
6. Deliberately skipped `link_wikidata.py` -- it operates only on
   `entities.person`, which this Repertoire-only merge left completely
   untouched (confirmed), so running it would just re-query the live
   Wikidata API for the same people for no new benefit. Flagged as
   separate, ongoing project work rather than silently run or silently
   dropped.
7. `build_datasette.py` produced `research_dataset_new.sqlite`; opened
   and spot-checked directly (29,157 events, matching the `.duckdb`'s
   `research.event` count exactly).

**Final verification** before swap-in: `research.theater`/`person`
completely unchanged (6=6, 2,894=2,894), `research.person_appearance`
byte-identical content (not just count) confirming zero impact on the
person side, `work`/`event`/`performance` shifted in ways fully
consistent with the Gate 3 corrections (4,530->4,412, 27,637->29,157,
24,892->25,316). `1903-04_p032` spot-checked directly in the merged
database: three theaters, three correct, distinct sets of receipts.

**Local swap-in**: moved (not deleted outright) the old
`imperial_theaters.duckdb`/`parsed/`/`research_dataset.sqlite` aside,
copied the verified new versions into place, confirmed the live
database in `outputs/full_run/` matches what was verified in the
working copy. Then, once confirmed good, deleted the pre-merge
snapshots plus two pre-existing stray artifacts surfaced along the way
(`imperial_theaters.duckdb.bak_pre_teatr_fix`, an already-stale Aug 27
backup nobody had cleaned up, and a `parsed 2/` directory dated Aug 28
-- a duplicate leftover from however the original `full_run` was built,
predating this session entirely).

**Explicitly NOT done**: publishing. `outputs/full_run/` is now the
verified, corrected local deliverable, but the HF dataset repo and
Cloud Run `spiski` still serve the old data -- republishing is a
separate, deliberate decision (HF upload + Cloud Run redeploy, both
with their own documented gotchas in CLAUDE.md's Publishing section)
that RG asked to defer. `outputs/full_run_merge_work/` -- the working
copy this was all built in, including the `parsed_gate3/`/
`parsed_baseline/` split kept as an audit trail of the two-pass
methodology -- is still on disk, left as a deliberate choice pending a
later decision to remove it.

### Addendum (2026-09-11): all 3 deferred pages resolved --
`cross_theater_date_mismatch` is 0 across the corpus for the first time

RG asked to go back and look carefully at the 3 pages still open
(`1899-00_p029`, `1903-04_p004`, `1901-02_p028`) rather than leave them
deferred indefinitely. All 3 turned out to be solvable with the same
scan-verified, cross-theater-corroborated discipline used throughout
this issue -- the earlier "needs re-deriving from scratch" framing for
`1899-00_p029` undersold how tractable it actually was once looked at
directly, and `1903-04_p004`'s cascading shift turned out to be more
contained than the original diagnosis suggested.

**`1901-02_p028`** (the row-shift bug found during the completeness
sweep): reconstructed all 15 Маріинскій sessions from the scan, correcting
a cascading one-position shift that started at "16 Суббота" and resolved
by "24 Воскрес" -- a spanning "Безплатные спектакли для воспитанниковъ
столичныхъ учебныхъ заведеній" header (misread in the raw JSON as "для
военныхъ") had gotten folded into a session's own content instead of
being recognized as label-only. Independently corroborated: the
reconstructed date sequence matches both Александринскій's and
Михайловскій's own coverage on the same page exactly.

**`1903-04_p004`**: same class of bug, but more contained than
originally diagnosed. The "Октябрь." row is a genuine month-transition
label -- but unlike a simple drop, it had absorbed 1 Среда's real
content (Баядерка/1244.57), cascading a one-position shift through
2 Четвергъ, 3 Пятница, and 4 Суббота (a multi-item benefit gala for the
Pushkin-monument fund), which had collapsed the true 4 Суббота/5
Воскрес distinction into a single mislabeled "4 Суббота" plus a
separately-mislabeled "5 Воскрес". Reconstructed 30 Вторн. through 10
Пятница. in full; confirmed the shift resolves cleanly at 6 Понед.
(everything 6 Понед. onward was already correct). Separately, on the
same page: Михайловскій was missing two genuinely-dark days (30 Вторн.,
2 Четвергъ -- confirmed dashes in the scan, aligned against
Александринскій's already-correct row positions) that had never gotten
an explicit `is_dark` placeholder; added both.

**`1899-00_p029`** ("the corpus's messiest page"): the real structure,
once read directly against the scan, is much simpler than the tangle of
current-JSON duplicates suggested. A single spanning header --
"Безплатные спектакли для воспитанниковъ столичныхъ учебныхъ заведеній"
-- sits once at the top of a 16-20 Февраля block and describes only the
very first row's morning leg (16 Среда, matching the same header-scope
convention established elsewhere this issue), not the whole week. Every
date 16-20 is a genuine morning/evening split across all three Moscow
theaters (Большой, Малый, Новый) -- confirmed directly against the
scan for all three, side by side. The raw JSON's "two overlapping,
partially conflicting reads" were mostly NOT conflicting at all: they
were the correctly-captured morning and evening legs, just both left
`session="unspecified"`, with the free-show header wrongly duplicated
onto every evening entry (which all have their own real, distinct
receipts -- confirmed against the scan, not free performances) and the
morning legs' receipts wrongly duplicated from the evening figures
instead of being cleared. One genuine cross-theater contamination found
along the way: a "Горе отъ ума"/"Прощальный ужинъ" entry sitting under
Большой театръ with Большой's own (duplicated) receipts figure is
actually Малый's real 20 Воскрес evening content, confirmed directly in
Малый's own crop with its own distinct receipts (1555.66, not 1795.26).
Reconstructed all three theaters' full 16-20 blocks (10 sessions each
for Большой/Новый, 9 for Малый, which has a single unsplit performance
on 17 Четвергъ rather than a morning/evening pair). The remaining dark
stretch (27 Воскрес./28 Понед./29 Вторн./2 Четвергъ./3 Пятница., all
three theaters agreeing already) was spot-checked against the scan and
confirmed genuinely dark, unchanged.

**Verified after all three fixes**: `check_repertoire_cross_theater_date_mismatch`
is **0 across the full 332-page corpus** -- down from the 2 pages
deliberately deferred at completeness-sweep time, plus the 1
subsequently found. 332/332 theater coverage unchanged, 0 true
duplicate sessions, 9 malformed-receipts (unchanged, genuine typos).
`check_repertoire_unknown_theater` dropped from 324 to 312, an
unplanned but welcome side effect of using the corpus's own already-
established theater-name strings consistently during these
reconstructions.

**Not yet done**: these fixes are only in
`outputs/gate3_columnwise/raw_columnwise/` (the canonical source
corpus) -- `outputs/full_run/`'s copy of these 3 pages' raw JSON, and
the `.duckdb`/`.sqlite` built from it, still reflect the pre-fix state
from the merge documented in the previous addendum. Propagating this
into `full_run/` needs the same careful two-pass-aware methodology as
that merge (on a much smaller scale -- 3 pages, not 332), and hasn't
been done yet.

### Addendum (2026-09-11, later same day): propagated the 3 fixes into
`outputs/full_run/` -- a much lighter-weight version of the earlier
merge, same discipline

A small-scale repeat of the full merge documented two addenda up, using
one shortcut the earlier merge's own findings made safe: `build_duckdb.py`,
`validate_performance_dates.py`, and `build_research_model.py` all use
`CREATE OR REPLACE`/explicit `DROP TABLE IF EXISTS` on their own tables
-- confirmed by reading each script directly, not assumed -- so they can
run safely **in place** against a copy of the current
`outputs/full_run/imperial_theaters.duckdb`, leaving the `entities`
schema (and its person-continuity state) untouched automatically. No
need to re-attach and copy the old database's `entities` schema across
like the original 332-page merge required, since this time the working
copy already had it baked in from that merge.

Steps: copied the current `imperial_theaters.duckdb` to a small scratch
copy; copied the 3 corrected raw JSON files + a 3-page manifest;
ran `parse_and_validate.py --extraction-source columnwise` on just
those 3 pages (123 event_entry rows, 130 performance rows, zero
validation errors); spliced the old/new rows into the existing merged
`parsed/` CSVs (matched by `page_id` for `event_entry`, by `event_id`
prefix for `event_entry_performance`) rather than re-running the full
two-pass split across all 1,349 pages again; ran `build_duckdb.py` /
`validate_performance_dates.py` / `build_entities.py` /
`build_research_model.py` / `build_datasette.py` against that one
scratch file, in order, same as the full merge (skipped
`link_wikidata.py` again, same reasoning -- person data untouched).

**Verified before swap-in**: untouched-page `event_entry` rows
byte-identical to the pre-patch database (23,800 rows, unchanged);
`person_entry`, `entities.person_link` (21,168, set-equal), and
`entities.person_merge_log` (1,022) all exactly unchanged;
`research.person_appearance` byte-identical content; 0 orphaned
`event_entry_performance` rows, 0 duplicate `event_id`s; all 3 patched
pages show exactly 3 distinct theaters each; `.duckdb`'s
`research.event` count (29,141) matches the `.sqlite` export exactly.

Swapped into `outputs/full_run/` using the same move-aside-then-replace
pattern as the original merge (never a direct overwrite), verified the
live state matched the scratch copy, then deleted the pre-patch
snapshots and the scratch working directory once confirmed good --
nothing old left lying around this time, cleanup done as part of the
same sitting rather than deferred.

`outputs/full_run/` now has zero known open Repertoire issues for the
Gate 3 corpus. Publishing (HF upload + Cloud Run redeploy) remains
explicitly deferred, unchanged from the earlier addendum.

### Addendum (2026-09-11): full-corpus `annotation` field audit --
one whole-page systematic bug found and reversed one of THIS issue's
own earlier fixes, ~90 sessions corrected across 20 pages

RG spotted a specific anomaly -- `repertoire_1899-00_p000__s006` had a
real performance fragment ("1-е д. бал. Дочь Микадо.") sitting in
`annotation` instead of `works` -- and asked to sweep the whole corpus
for the same pattern. Per `flatten_repertoire_page`
(`pipeline/schemas/repertoire.py`), this matters beyond tidiness: only
`works` entries become structured, indexed `event_entry_performance`
rows; `annotation` is unindexed free text. A title stuck in
`annotation` is invisible to anyone querying `research.performance`
for that work.

**Method**: classified all 635 distinct annotation strings corpus-wide
by two signals -- genuine-note keywords (пользу, безплатн, бенефис,
гастрол, юбилейн, концерт, etc.) vs. title-shaped text (ends in a bare
genre abbreviation, or carries an act/scene-number prefix like "1-е
д."/"2-я карт."). 66 distinct strings (88 sessions) matched
"title-shaped, no note keyword." Triaged into three buckets before
touching anything: exact duplicates of an already-correct `works`
entry (safe to just clear), `works`-empty cases (the annotation is the
session's *only* title), and compound candidates (works already has
content, annotation looks like an additional item).

**The big one: `1903-04_p026` was systematically bugged, not following
a legitimate page convention.** All ~30 non-benefit sessions across
all 3 theaters had their real title sitting in `annotation` with
`works` empty -- confirmed NOT a valid page-specific pattern by
checking an unaffected comparison page
(`1902-03_p026`, unrelated despite the similar filename): there,
`annotation` is reliably `None` for ordinary performances and `works`
holds the title, exactly matching the flatten logic's expectation.
**This directly contradicts a decision made earlier in this very
issue** (the "1903-04_p026 annotation/works split bug" addendum, which
merged Feb 4's `works` entries *into* `annotation` specifically to
match this page's *other* rows) -- that fix matched against rows that
were themselves bugged, not against the corpus's real convention.
Reversed it: Feb 4's Михайловскій content moved back into `works`
along with the other ~30 sessions on the page. One row needed more
care than a mechanical move -- `4 Среда.` Маріинскій's `works` array
itself had a benefit description ("Прощальный бенефисъ г-жи М.
Кшесинской") sitting where a work belonged; swapped it into
`annotation` and moved the real annotation title into `works` in its
place.

**Three more pages had the same whole-column bug** (one or two of the
three theaters, not all three): `1900-01_p017` (Большой + Новый, 18
sessions), `1903-04_p025` (Малый + Новый, 20 sessions), `1903-04_p037`
(Новый only, 9 sessions -- two of which were a different shape: "27
Вторникъ" and "29 Четвергъ" had each been split into two separate
session dicts for what the scan confirms is one printed cell sharing a
single receipts figure; merged each pair back into one session with
two works rather than moving text between fields).

**Remaining ~20 pages had one or two isolated sessions each**, several
needing scan verification rather than a blind move because the shape
was genuinely ambiguous:
- **Qualifier-merge cases**: an annotation like "2-е д. бал.
  Талисманъ." or "5 д. бал." isn't always a new work -- sometimes it's
  an act/scene qualifier that belongs merged into an *already-listed*
  work's title. Confirmed both shapes directly against scans:
  `1905-06_p023` (4 sessions, Большой) has qualifiers that attach to
  specific existing works, not new ones; `1905-06_p045_s027`'s "3-е
  д." attaches to "Эсмеральда" specifically, not "Два вора" (its
  sibling work); `1903-04_p034_s003`'s three-part qualifier attaches
  entirely to "Волшебное зеркало", not split across both existing
  works; `1900-01_p036_s014`'s "3-й актъ изъ траг." attaches to "Марія
  Стюартъ" (already genre="траг."), with "На рѣкѣ" as a genuinely
  separate third work.
- **The reverse bug, found while checking the above**: `1905-06_p045_s030`
  had "Въ пользу инвалидовъ." -- a genuine charity note -- sitting in
  `works` instead of `annotation`. Moved it back.
- **Two more session-split cases**, same shape as `1903-04_p037`'s:
  `1902-03_p026_s021` (Михайловскій, `12 Среда.`) and
  `1903-04_p027_s024` (Новый, `4 Среда.`) had a genuine free
  morning-matinee session (the "Безплатные спектакли для
  воспитанниковъ столичныхъ учебныхъ заведеній." header, now confirmed
  recurring across many pages this whole issue) merged into the same
  session dict as the real evening performance. Split each into
  separate morning (free, no receipts) and evening sessions, confirmed
  against the scan in both cases.
- **A second, unrelated shift bug found while scan-checking**:
  `1907-08_p013` had "9 Пятница." wrongly carrying the "10 Суббота."
  charity gala's annotation, "10 Суббота." wrongly carrying "11
  Воскрес."'s receipts and title, and "11 Воскрес." itself needing a
  genuine morning/evening split -- same class of cascading-shift bug
  as `1903-04_p004`/`1901-02_p028` from the completeness-sweep
  addendum, caught here by the same discipline (checking the scan
  before trusting a mechanical field move). Also found and fixed one
  incidental case while checking `1900-01_p036`'s scan for an
  unrelated reason: `s018`'s "На бойкомъ мѣстѣ, ком." was a third work
  mixed into a benefit annotation that wasn't in the original flagged
  list at all (the "бенефисъ" keyword had excluded it from detection).

**One self-caught transcription slip**: while retyping
`1900-01_p017_s028`'s title, wrote "Принцесса Грѳза" instead of the
extracted text's actual "Принцесса Грѳва" -- an unintentional
"correction" toward the real opera's modern title, exactly what
CLAUDE.md's orthography rule forbids. Caught on self-audit before
moving to the next page, reverted to the verbatim original spelling.
Worth naming as a reminder: moving text between fields carries the
same verbatim-transcription risk as any other edit to this corpus.

**Verified after all fixes**: `check_repertoire_cross_theater_date_mismatch`
still 0, 332/332 theater coverage unchanged, 0 true duplicate
sessions, 9 malformed-receipts unchanged. Re-ran the full classifier
sweep: 0 sessions still flagged corpus-wide.

**Not yet done**: like the individual-page fixes before it, this round
lives only in `outputs/gate3_columnwise/raw_columnwise/` --
`outputs/full_run/` has not been re-synced to include it.


---

**2026-09-11, later same day: утро/вечер (morning/evening) pairing
completeness check.** RG asked whether every date with a утро entry
also has a вечер entry, and vice versa. Grouped all sessions by
(page, theater, date_text) corpus-wide: 778 groups use morning/evening
at all, 18 of them (9 morning-only, 9 evening-only) had just one leg.

**6 turned out to be a labeling issue, not missing data**: an
`"unspecified"` session sitting where the scan clearly shows a printed
УТРО label (paired with a real `"evening"` sibling) -- 5 on
`1899-00_p021` (Малый and Новый, five dates) and 1 on `1904-05_p026`
(which also had a bonus annotation/works bug in the same session,
fixed alongside: a title had escaped the earlier corpus-wide sweep
because its annotation contained "Спектакль," a word the sweep's
keyword classifier treats as a genuine-note signal).

**Investigating the remaining 12 found four more distinct real bugs,
all confirmed against scans before fixing:**
- `1901-02_p028` (Михайловскій): a cascading one-position shift across
  dates 17-20, separate from and in addition to the one already fixed
  on this page in the completeness-sweep round -- 17 Воскрес's real
  single-session content ("Les forfaits de Pipermans") had been split
  across a fabricated morning/evening pair using 18 Понед's and 19
  Вторн.'s actual content, 19 Вторн. itself absorbed 20 Среда's free
  morning leg (the recurring "Безплатные спектакли для
  воспитанниковъ..." header) under the wrong date, and 20 Среда's real
  evening ("La Tosca") had been mislabeled as its morning with a
  fabricated dark evening in its place. Reassigned all four dates'
  session/date_text fields using the same already-transcribed text
  (no retyping, to avoid the transcription-slip risk named in the
  previous round). Confirmed `24 Воскрес.`'s evening-only entry is
  genuine (the scan shows no морнинг row or dash at all for
  Михайловскій that Sunday, exactly the "single leg only, no dash
  counterpart" pattern below) -- left as-is.
- `1901-02_p021` (Новый театр.): `6 Воскрес.`'s morning
  ("Бѣдность не порокъ, ком.", 384 р. 40 к.) was missing outright --
  this page's Новый театръ column carries `_repair_tier:
  "baseline_fallback"` markers, and the fallback extraction had simply
  dropped the session. Added it back, verbatim from the scan. While
  re-scanning this page, also caught two sessions -- `30 Воскрес.` and
  `31 Понед.` -- where both legs existed but were both labeled
  `"unspecified"` instead of morning/evening (the scan shows explicit
  УТРО/ВЕЧЕРЪ splits for both); relabeled.
- `1902-03_p019` (Большой театръ.): a longer cascading one-position
  shift spanning `21 Суббота.` through `29 Воскрес.`'s morning (7
  calendar days), self-resolving exactly at `29 Воскрес.`'s evening --
  same bug class as `1901-02_p028`/`1903-04_p004` from the
  completeness sweep. Reassigned dates on the 6 already-transcribed
  entries and added 2 genuine dark placeholders (`21 Суббота.` and
  `28 Суббота.` evening) that the shift had swallowed -- both confirmed
  as printed dashes on the scan.
- `1904-05_p012` (Александринскій театръ.): the same shift pattern
  again, this time spanning `14 Воскрес.`-`15 Понед.` -- 14 Воскрес's
  free-morning header leg ("Плоды просвѣщенія") had absorbed 14
  Воскрес's own evening receipts, its real evening ("Благодѣтели
  человѣчества" + "Женихъ изъ долгового отдѣленія") was mislabeled as
  `15 Понед.` morning, and 15 Понед's real single-session day ("Отецъ"
  + "Наканунѣ, возможный случай") was mislabeled evening instead of
  unspecified. Fixed all three entries; added the
  "Безплатные спектакли для воспитанниковъ столичныхъ учебныхъ
  заведеній." annotation to 14 Воскрес's morning leg, matching the
  convention already used by this page's Маріинскій театръ row.

**4 more were pure session-mislabeling** (a single, unsplit printed
row -- confirmed on the scan -- tagged "morning" instead of
"unspecified"): `1901-02_p019` (Большой, `26 Среда.`), `1907-08_p020`
(Александринскій, `15 Суббота.`), `1907-08_p026` (Маринскій, `15
Вт.`), `1907-08_p032` (Михайловскій, `16 Суббота.`).

**2 confirmed genuine, no fix needed**: `1901-02_p028`'s `24 Воскрес.`
(evening-only) and `1905-06_p015`'s `20 Воскрес.` (morning-only,
Новый театръ) both show, on the scan, a single performance sitting in
one labeled slot with literally no printed row or dash for the other
leg -- not a data-loss bug, just a theater that had one show that day.

**2 confirmed genuine page-boundary artifacts, unfixable**:
`1905-06_p005`'s `1 Суббота.` (Новый театръ, Moscow table) and
`1905-06_p008`'s `23 Воскрес.` (Маріинскій, Petersburg table) both cut
off mid-row exactly at the physical bottom of their printed page (page
89 and page 92 respectively) with only a УТРО leg shown; the next page
of the *same* city's table picks up at the following calendar day with
no continuation of the cut-off row. Moscow and Petersburg tables run
as separate page-sequences covering overlapping date ranges (verified
by checking the intervening and following pages), so there's no
missing-but-recoverable вечер here -- the book itself never printed it
where a corpus page boundary could capture it.

**One related pattern found but deliberately not fixed here**: while
confirming the `1901-02_p021` case above, noticed that BOTH legs of a
compound day are sometimes present but BOTH mislabeled
`"unspecified"` instead of morning/evening. A corpus-wide sweep found
76 (theater, date) keys with this exact shape. Out of scope for this
round's actual question (both legs *do* exist, so it's invisible to a
morning-only/evening-only check) -- flagged as a background task for a
dedicated pass rather than fixed opportunistically here.

**Verified after all fixes**: `check_repertoire_cross_theater_date_mismatch`
still 0, 332/332 theater coverage unchanged, malformed-receipts still 9.
Re-ran the morning/evening pairing check corpus-wide: only the 4
confirmed-genuine cases above remain out of the original 18.

**Not yet propagated into `outputs/full_run/`** -- like the
annotation-audit round before it, this lives only in
`outputs/gate3_columnwise/raw_columnwise/` so far.


---

**2026-09-11, later still: stray утро/вечер text sweep.** RG asked to
check whether "утро" or "вечер" text appears anywhere unexpected --
i.e. whether the printed sub-row labels (УТРО./ВЕЧЕРЪ.) or fragments
of them had leaked into a field where they don't belong, the way a
genuine performance title can also leak into `annotation` (the pattern
this whole issue keeps surfacing). Regex-searched every field across
the corpus for "утр"/"вечер" case-insensitively: 51 hits. The large
majority are genuine Russian titles/genres that happen to contain the
word ("Вечерняя заря", "Утро дѣлового человѣка", "Женихъ (Утро
жениха)", concert titles like "Музыкально-Литературный вечеръ") --
not bugs. Six were real, all scan-verified before fixing:

- **`1904-05_p013`**: a literal header-label leak, not a fragment --
  `annotation` held the bare string `"ВЕЧЕРЪ."` on two sessions
  (Малый and Новый театръ, both dated `13 Суббота.`) while the scan
  shows both are actually `14 Воскрес.`'s morning leg (the free
  "Безплатные спектакли..." block), with a real evening leg
  immediately after that had picked up the same bogus `"ВЕЧЕРЪ."`
  annotation instead of being labeled `session="evening"`. Reassigned
  dates/sessions on all four entries; this left `13 Суббота.` missing
  its own dark placeholder for Малый/Новый (Большой already had one),
  caught by re-running `check_repertoire_cross_theater_date_mismatch`
  afterward -- added the two missing dark entries to match.
- **`1903-04_p019`**: `annotation` on Малый театръ's `20 Суббота.`
  read `"престарѣ-емействъ. ай вечеръ."` -- a garbled, truncated
  duplicate of Большой театръ's real annotation on the *same date*
  ("Въ пользу Убѣжища для престарѣлыхъ артистовъ и ихъ семействъ.
  Музыкально-Литературный вечеръ."). The scan shows Малый was simply
  dark that day (a plain dash). Cross-column content bleed corrupting
  a blank cell -- cleared to `is_dark: true, works: [], annotation: null`.
- **`1901-02_p030`**: the reverse bug (real performance titles sitting
  in `annotation` instead of `works`) -- Маріинскій театръ's
  `12 Вторникъ` had a genuine benefit note followed by two real titles
  ("Урвази—утренняя звѣзда, оп." and "Le cœur de la marquise,
  pantomime.") all concatenated into `annotation`, `works` empty.
  Split them out.
- **`1907-08_p025`**: same reverse-bug shape plus OCR corruption --
  Большой театръ's `11 Пятница.` had a benefit note and two work
  titles in `annotation` (one missing its "Зв" -- "аный вечеръ съ
  итальянцами" for "Званый вечеръ..."), with only the third title
  correctly in `works`. Split all three out, using the intact spelling
  confirmed on the scan.
- **`1907-08_p027`**: found while cross-checking the previous case
  against a second occurrence of the same touring bill -- a genuine,
  separate cascading shift: `19 Суббота.`'s real content (the same
  benefit note + "Въ горахъ Кавказа" + "Званый вечеръ съ итальянцами",
  no receipts printed) had absorbed `20 Воскрес.`'s morning leg
  ("Фра-Діаволо", 604 р. 46 к.) into its own `works`/receipts, while
  `20 Воскрес.` itself carried the misplaced annotation atop what was
  actually its own evening leg. Reassigned `19 Суббота.`'s works back
  to the two benefit-program titles (receipts cleared -- none printed),
  and split `20 Воскрес.` into its real morning/evening pair.
- **`1903-04_p032`**: another reverse-bug instance -- Александринскій
  театръ's `10 Сб.` had a benefit note plus "Соловушка, сц." and
  "Званый вечеръ съ итальянцами, оперетка." all in `annotation`,
  `works` empty. Split them out.

Re-ran the regex sweep after fixing: 48 hits remain, all confirmed
genuine (real titles, or benefit/concert nights where `annotation`
holds the full note and `works` is legitimately empty -- checked each
of the remaining `annotation`-field hits individually). A second,
stricter sweep for the literal all-caps header strings ("УТРО.",
"ВЕЧЕРЪ.") anywhere in any field: 0 hits corpus-wide.

**Verified after all fixes**: `check_repertoire_cross_theater_date_mismatch`
back to 0 (briefly regressed to 1 after the `1904-05_p013` date
reassignment, caught and fixed by adding the two missing dark
placeholders), 332/332 theater coverage, malformed-receipts still 9.

**Not yet propagated into `outputs/full_run/`.**

---

**2026-09-11, later still: the deferred 76-key "both legs mislabeled
unspecified" pass** -- the background task flagged two rounds back
("out of scope for this round's actual question ... flagged as a
background task for a dedicated pass"). Regrouped all sessions
corpus-wide by `(page, theater, date_text)`; a stricter definition
than the original quick sweep (require exactly 2 sessions at the key,
both `session="unspecified"`, both `is_dark=false`, both with a
non-empty `works` and a non-null `receipts_text` -- i.e. two real,
already-transcribed printed cells, not a `_repair_tier` placeholder or
a half-empty benefit note) found **64** keys, not 76 -- the earlier
number was an unscoped estimate; 64 is what the round's own criteria
actually produce.

**Checked all 64 against the source scans (`pdf/RepertoireTables/`,
not the gitignored 300dpi renders, which aren't present on this
machine right now) before touching anything**, matching each
session's *title and receipts figure*, not just its position in the
row, against the printed cell -- position-only matching turns out not
to be safe here (see below). **51 of the 64 confirmed genuine**: the
scan shows two real printed sub-rows at that date for that theater,
either under explicit УТРО./ВЕЧЕРЪ. tick-mark labels, or -- for 6 of
the 51 -- under the recurring "Спектакль для учащейся молодежи" free-
matinee convention already established as morning by this issue's
earlier rounds (no tick mark printed for that convention, but the
divider line and the header text are the same signal precedent already
accepted). All 51 confirmed cases have idx-order matching print order
(lower session index = top of the printed cell = morning; higher =
bottom = evening) -- relabeled `session` only, `works`/`receipts_text`/
`annotation`/`date_text` untouched, per this round's scope.

**The other 13 are not this bug at all -- they're spurious pairings
produced by the cascading one-position date/title/receipts shift bug
documented repeatedly elsewhere in this issue** (`repertoire_1893-94_p007`
in #49, `1901-02_p028`/`1902-03_p019`/`1904-05_p012` in the pairing-
completeness round two entries back). In each case the group's two
"unspecified" sessions are real printed cells, but at least one of
them belongs to a *different, adjacent date* that the extraction
mislabeled -- so it only looks like a same-date morning/evening pair
because its title+receipts happen to land on the wrong `date_text`
next to a genuinely unrelated session. Confirmed by checking the
neighboring dates on the same scan and finding an exact title+receipts
match there instead:

- `1901-02_p018` (Александринскій театръ, 3 keys: `17 Понед.`,
  `26 Среда`, `28 Пятница`) -- a previously-undocumented instance of
  this page's own shift bug, distinct from and in addition to any
  fix already applied elsewhere on this page. Spans at least
  `16 Воскрес.` through `29 Суббота.`.
- `1901-02_p028` (Александринскій театръ., `20 Среда.`) -- the
  776 р. 49 к. "Комета" session belongs to `21 Четвергъ.`'s morning,
  not `20 Среда.`'s evening. A different shift than the
  Михайловскій-column shift on dates 17-20 this same page already
  fixed by the pairing-completeness round -- this one is on the
  Александринскій column.
- `1902-03_p026` (Александринскій театръ, 4 keys: `14 Пятница.`,
  `16 Воскрес.`, `24 Понед.`, `26 Среда.`) -- a page-wide one-position
  shift spanning `13 Четвергъ.` through at least `26 Среда.`: e.g. the
  pair filed under `16 Воскрес.` (`Чайка`/`Вопросъ`) is actually
  `15 Суббота.`'s real entries, and the pair filed under `24 Понед.`
  (`Зарница`/`Волки и овцы`) is actually `16 Воскрес.`'s.
- `1903-04_p020` (Александринскій театръ, `1 Четв.`) -- the
  1881 р. 50 к. "Пустоцвѣтъ" session is `31 Среда.`'s evening, not
  `1 Четв.`'s morning.
- `1903-04_p027` (`7 Суббота.`, both Большой театр. and Новый театр.)
  -- both columns' "7 Суббота." pairs are actually `6 Пятница.`'s real
  entries (confirmed exact title+receipts match both cases).
- `1903-04_p025` (Новый театръ, `2 Понед.`) -- a different shape, not
  a same-page-neighbor shift: the session filed as `2 Понед.`'s
  "evening" (`Пустоцвѣтъ`/`У елки`, 1170 р. 79 к.) doesn't match
  *any* nearby date's scan cell, while the real `2 Понед.` evening
  (`Даровой пассажиръ, ком.`, 869 р. 40 к., clearly printed on the
  scan) is simply absent from the JSON -- an extraction miss paired
  with an unrelated stray entry, not a shift.
- `1901-02_p011` (Новый театръ, `11 Воскрес.`) -- left un-relabeled
  for a different reason: the two sessions' titles and receipts *do*
  match the scan exactly at that date (Севильскій цирюльникъ 311 р.
  59 к. / Моцартъ и Сальери + Пиръ во время чумы + Сынъ мандарина
  1625 р. 15 к.), and the cell is genuinely divided by a printed rule
  -- but there is no УТРО./ВЕЧЕРЪ. tick mark for this theater on this
  row, and it isn't the free-matinee convention either. This task's
  own instruction was to relabel only where the scan confirms
  *explicit* УТРО/ВЕЧЕРЪ sub-labels; absent that, left as `unspecified`
  rather than assumed.

None of the 13 above were touched. They're a real, separately-worth-
fixing bug (the same shift-bug class as #49/the pairing-completeness
round), just not *this* bug -- flagging here rather than folding a
different fix into this round's scope.

**Verified after fixing the 51**: re-ran the same grouping query
corpus-wide -- exactly the 13 excluded keys above remain, 0 new ones
introduced, total session count unchanged (11,832, only the `session`
field value changed on 102 sessions across 24 files).

**Not yet propagated into `outputs/full_run/`** -- lives only in
`outputs/gate3_columnwise/raw_columnwise/` so far, consistent with
every other round in this issue.


---

**2026-09-11, event-date field audit.** RG asked to look carefully at
the `date_text`/`month_text`/`year_text` fields for anything
unexpected. Ran several structural checks corpus-wide rather than
scan-checking all 11,832 sessions individually:

**2 real bugs found and fixed, both scan-verified:**
- **`1903-04_p021`**: a dropped leading "1" digit, identically across
  all 3 theaters -- `"0 Суббота."` and `"1 Воскрес."` should be `"10
  Суббота."` and `"11 Воскрес."` (confirmed against the scan: `9
  Пятница.` is immediately followed by a fully dark `10 Суббота.`, then
  `11 Воскрес.`, not a nonsensical day "0" or a second day "1"). Fixed
  7 entries.
- **`1904-05_p032`**: a bare month-header row -- the printed label
  `"Мартъ."` that separates February from March in the date column,
  with no theater content at all -- had been captured as if it were
  its own session (once per theater, `is_dark: true, works: []`).
  Confirmed against the scan this is pure page furniture, not a
  calendar day; no other page in the corpus has this problem (checked
  all 12 month-header strings corpus-wide). Removed the 3 bogus
  sessions.

**Checked and confirmed NOT bugs, no fix made:**
- **30 "day sequence jumps backward" cases across 10 pages** (e.g.
  Мариинскій театръ's date sequence going `...31, 10...` or `...27,
  7...` within one page) turned out to be genuine multi-day gaps
  *printed in the source itself* -- spot-checked two on their scans
  (`1899-00_p034`: the table jumps directly from "31 Пятница." to
  "Апрѣль. / 10 Понед." with no rows at all for April 1-9;
  `1903-04_p028`: jumps from "27 Пятница." straight to "Мартъ. / 7
  Воскрес.", skipping Feb 28-March 6 for *all three* theaters, not
  just one). Most likely Great Lent closures (the date ranges land
  right where Orthodox Lent/Holy Week fell in those years) -- the
  print never had rows for those days, so there's nothing to recover.
- **56 "weekday text differs between theaters for the same day
  number" cases**: in every one, the calendar-anchoring day *number*
  agrees across all theater columns -- only the weekday abbreviation's
  last letter or spacing differs (`"Четвергъ"` vs `"Четвергь"` -- ъ/ь
  are easily confused in this typeface; `"Вторн"` vs `"Втори"`;
  `"Суббо та"` with a stray space). Per CLAUDE.md's verbatim rule this
  isn't something to normalize toward one "correct" spelling across
  columns -- it doesn't change which calendar day is meant, and each
  column's own OCR reading stays as extracted.
- **Season vs. `year_text` cross-check**: 0 mismatches -- every
  populated `year_text` value falls inside its own page's season.
  `month_text`/`year_text` value sets both inspected directly: broad
  capitalization/punctuation/case variance (expected OCR noise) but no
  garbled or out-of-range values.

**Found but not fixed -- flagged as a background task instead**: 123
`date_text` values across 5 pages (`1903-04_p018`, and four 1907-08
pages: `p016`, `p020`, `p022`, `p032`) have truncated weekday
abbreviations (e.g. `"16 Су"` instead of `"16 Суббота."`). The day
number is unambiguous in every case (checked: no page has two
different real dates sharing a truncated stem), so this isn't a
correctness bug -- but on 3 of the 5 pages, *every* sighting of some
calendar days is truncated with no full-form sibling elsewhere on the
page to copy from, so restoring the full text needs a scan-by-scan
pass rather than a mechanical fill-in. Out of scope for this round;
spun off as its own task.

**Verified after the two fixes**: `check_repertoire_cross_theater_date_mismatch`
still 0, 332/332 theater coverage, malformed-receipts still 9.

**Not yet propagated into `outputs/full_run/`** -- per RG's instruction,
this round and the three that preceded it earlier today (Gate 3
completeness sweep addenda aside) will be batched into one
`outputs/full_run/` propagation later rather than done per-round.

---

**2026-09-11, dedicated pass on the 13 shift-bug cases flagged by the
previous round.** Direct follow-up: the previous addendum found 51 of
64 "both legs unspecified" keys were genuine morning/evening splits
(fixed) and left 13 untouched because they were actually spurious
pairings produced by the cascading date/title/receipts shift bug
(#49-class), not this round's bug. This pass went back and reconstructed
each of the 5 affected pages properly -- not just the 2 sessions each
key originally flagged, but the full local run of dates each shift
touched, checked line-by-line against the scan (title *and* receipts
figure, never position alone).

**`1903-04_p027` (Большой театр. + Малый театръ. + Новый театр., all
three columns, same page-wide shift):** every session from `4 Среда.`
through `8 Воскрес.` was one position off, on **all three theater
columns simultaneously** (row-detection shifts the whole page width
together) -- reassigned `date_text`/`session` on 24 sessions across the
three columns. `4 Среда.` itself (a charity double-bill of "Жизнь за
Царя" with no receipts printed for either leg) was **missing entirely**
from Большой театр.'s column -- added both sessions back, using the
"Спектакль для воспитанниковъ" convention already established for the
free morning leg (matching Новый театръ.'s own `4 Среда.` entries on
the same row, which had the banner annotation captured correctly) and
the printed charity-benefit annotation for the evening leg. Малый
театръ.'s column was additionally missing its 5 dark placeholders for
`16 Понед.`-`20 Пятница.` entirely (its shifted entries had absorbed
those date labels instead of being recorded as blank) -- added those
back too, matching the dark-entry shape already used by the other two
columns on this same page.

**`1901-02_p018` (Александринскій театръ):** the deepest reconstruction
of the five. Three distinct contamination shapes on one column:
- `16 Воскрес.`-`17 Понед.`: a clean one-position date shift (`17
  Понед.`'s "Мишура" session is actually `16 Воскрес.`'s evening).
- `22 Суббота.`-`27 Четвергъ.`: `22 Суббота.`'s real annotation-only
  benefit note (no receipts printed) had **absorbed a stray receipts
  figure** (264 р. 70 к.) that actually belongs to a `26 Среда.`
  morning session missing from the JSON entirely (`"Много шуму изъ
  ничего"`) -- cleared the stray figure and added the missing session
  back. `26 Среда.`'s existing "Ирининская община" entry was really its
  evening leg (not morning, as its `"unspecified"` label implied); the
  entry that had inherited `26 Среда.`'s date_text ("Недоросль") turned
  out to be `27 Четвергъ.`'s real morning leg.
- `28 Пятница.`-`29 Суббота.`: **receipts values were shifted one
  position relative to their own titles** within existing entries --
  the entry titled "Старый закалъ" (28 Пятница.'s real morning title)
  carried 29 Пятница evening's receipts value instead of its own; the
  "Комета" entry (28 Пятница.'s real evening title) carried a receipts
  figure that actually belongs to `29 Суббота.`'s morning ("Снѣгурочка",
  missing from the JSON entirely). Corrected both entries' receipts and
  added the missing `29 Суббота.` morning session. `29 Суббота.`'s
  evening entry also carried a receipts value (1770 р. -- к.) that
  turned out to be **copied from Михайловскій театръ's own same-row
  entry** (same page, same date, identical figure) -- the scan shows
  no receipts printed at all for Александринскій that evening (a
  benefit note, same shape as `22 Суббота.`); cleared it.

16 sessions touched (11 relabeled, 3 receipts-corrected, 2 added) to
fully sort out dates `16 Воскрес.` through `29 Суббота.`.

**`1902-03_p026` (Александринскій театръ):** a page-wide shift spanning
`13 Четвергъ.` through `26 Среда.`, 11 sessions reassigned. One entry
(`_repair_tier: "baseline_fallback"`, the two-tier repair pass from
three rounds ago) had **contaminated title/genre/annotation**, not just
date: the fallback-recovered row for `24 Понед.` carried the title
"Der blinde Passagier" (actually `25`/`26`'s play) copy-pasted along
with its own annotation, while its receipts figure (1885 р. 45 к.) was
the only genuinely-correct part, matching `24 Понед.`'s real bill --
"Kollegen, Charakter-Komödie" + "Die goldene Ewa, Lustspiel" (a
German-troupe guest performance, confirmed on the scan). Corrected the
works list and cleared the borrowed annotation; the following two
`26 Среда.`-labeled entries needed only their dates shifted back one
day each (`25 Вторникъ.`/`26 Среда.`), their "Der blinde Passagier"
content already being correct.

**`1901-02_p028` (Александринскій театръ.), `20 Среда.`:** a smaller,
local version of the same shift -- `20 Среда.`'s real morning leg
("Снѣгурочка", the free-matinee convention, no receipts) was missing
from the JSON; the session carrying its evening content ("Бенефисъ
г-жи Мичуриной...") was correctly dated but mislabeled `"unspecified"`;
the following "Комета" session belonged to `21 Четвергъ.`'s morning,
not `20 Среда.`'s evening, and `21 Четвергъ.`'s own real evening
("Ревизоръ") was sitting under the right date already but likewise
`"unspecified"`. Added the missing entry, relabeled the rest.

**`1903-04_p020` (Александринскій театръ), `1 Четв.`:** the smallest of
the five -- a one-entry local shift, not a page-wide cascade. The
session labeled `"1 Четв."` with title "Пустощвѣтъ" is actually `31
Среда.`'s real evening leg; `31 Среда.`'s existing morning entry just
needed its session field set. `1 Четв.`'s own single real entry
("Мѣсяцъ въ деревнѣ") was already correctly dated and didn't need to
move.

**`1903-04_p025` (Новый театръ), `2 Понед.`:** re-examined and
corrected an over-hasty conclusion from the *previous* round, which
had assumed a genuine extraction miss here. On closer inspection there
is no tick-mark row at all for Новый театръ around these dates --
`2 Понед.` is a genuine single unsplit entry ("Пустоцвѣтъ"/"У елки",
already correct as-is), and the two sessions that looked like a
mismatched `2 Понед.` pair are actually `3 Вторн.`'s real morning/evening
split, one of which had simply inherited the wrong date_text. Simpler
fix than originally diagnosed: one date reassignment, two session
labels.

**Left alone, confirmed not a match for this bug**: `1901-02_p011`
(Новый театръ, `11 Воскрес.`) -- re-confirmed on the scan a second
time. Content matches the claimed date exactly (no shift), the cell is
genuinely divided by a printed rule, but there is no УТРО/ВЕЧ tick mark
and it isn't the free-matinee convention either. Left as `unspecified`
per this whole exercise's own evidentiary bar.

**Net change**: 10 previously-missing sessions added (across the 5
pages), several dozen `date_text`/`session` reassignments, and 4
entries had contaminated `works`/`annotation`/`receipts_text` fields
corrected where the scan made the real content unambiguous (all within
the shift itself -- nothing invented). Corpus session count: 11,832 ->
11,842.

**Verified after all fixes**: re-ran the same both-unspecified-pair
sweep corpus-wide -- exactly 1 key remains (`1901-02_p011`, confirmed
correctly left alone above), 0 new spurious pairs introduced. Also
checked for duplicate `(theater, date_text, session)` triples on all 5
touched pages as a sanity net: found exactly one, on `1901-02_p018`
(`Михайловскій театръ`, `16 Воскрес.`, both `"unspecified"`) -- **not
something this pass touched or introduced**; it's the same
titles-in-`annotation`-instead-of-`works` pattern documented elsewhere
in this issue, on a column this pass never edited. Flagged here for a
future pass, not fixed now (out of scope -- fixing it means moving
`annotation` content into `works` first, a different bug class).

**Not yet propagated into `outputs/full_run/`** -- per RG's standing
instruction, batched with the other rounds from today rather than
propagated per-round.


---

**2026-09-11, worked verbatim-rule example: 3 genuine printed date
typos.** Following up on the weekday-text audit above, RG asked to
(1) document these as a worked example of CLAUDE.md's
never-modernize-a-printed-typo rule and (2) make sure the research
layer still gets a usable date despite the source's own error.

The 3 cases (`1904-05_p014` `28 Понед.`, `1905-06_p027` `23 Вторн.`,
`1905-06_p036` `16 Среда.`) are the book's own typesetting error, not
an extraction artifact -- confirmed on all three scans: each misprinted
row sits directly between two rows whose weekdays are otherwise
perfectly consistent (e.g. `1904-05_p014`: `27 Суббота.` -> `28
Воскрес.` -> **`28 Понед.`** -> `30 Вторникъ.` -- only internally
consistent if that middle row is really the 29th). `raw.event_entry.date_text`
keeps the book's own "28 Понед." forever, unchanged -- that's the
verbatim guarantee, and nothing above touches it.

**What "flag them for the research layer" means concretely**: this
corpus already has exactly the right mechanism for this --
`pipeline/validate_performance_dates.py`'s `analysis.event_entry_date_check`
table, whose `corrected_date_undate` flows into `research.event.date`
(`build_research_model.py`: `coalesce(dc.corrected_date_undate,
ae.date_undate)`), with `date_confidence` always traveling alongside
so a query can tell which rows were touched. That module already
detects a weekday/day-number mismatch like these three -- but by
design it only *auto*-corrects a run of >=2 consecutive mismatched
rows that independently agree on the same shift, and deliberately
never touches an isolated single-row mismatch (the module's own
docstring names the exact false-positive that discipline exists to
prevent). These three are isolated, so the existing heuristic
correctly leaves them alone -- flagged (`unresolved`), not corrected.
Added a small, explicitly-documented `_MANUAL_DATE_OVERRIDES` table to
the same module: keyed by `(page_id, printed date_text)` rather than
`event_id` (stable across a corpus rebuild, unlike `event_id`), applied
as a final pass over every event so it isn't tied to whichever
block-level status the row happened to land in. Gives these three
`date_confidence='corrected_manual'` and the scan-verified date, with a
`note` naming the reasoning inline in the table itself.

Tested against a scratch copy of `outputs/gate3_columnwise/imperial_theaters.duckdb`
(never the original) before considering this done -- and the first
version of the override didn't actually fire for any of the 3 cases,
for an instructive reason (see next section).

**A much bigger finding surfaced while testing this.** All three
target rows turned out to have `date_undate = NULL` (two of the three
pages) or to land in `'intra_block_disagreement'` rather than a clean
`'mismatch'` (the third) -- neither of which the block-level draft of
the override could see at all. Chasing why surfaced a corpus-wide gap
that has nothing to do with these three typos:

`flatten_repertoire_page` computes `date_undate` from *only* that
individual session's own `month_text`/`year_text` (`pipeline/schemas/repertoire.py`:
`date_input = f"{day} {s.month_text or ''} {s.year_text or ''}"`) --
no inheritance from neighboring rows on the same page, no fallback to
the page's own printed header date range. Issue #14 already measured
this for the *baseline* single-call extraction and got it to a 99.8%
fill rate. That fix never touched column-wise extraction, and nobody
re-measured `date_undate` fill rate after Gate 3 shipped (it isn't
scored by `eval_against_gold.py`, so a regression here is invisible to
the usual signal -- issue #14's own closing line about this exact
trap). Checked `raw.event_entry.date_undate` fill rate by season in
`outputs/full_run/imperial_theaters.duckdb` directly:

| season | date_undate fill |
|---|---|
| 1890-91 through 1898-99 (baseline) | 100.0% |
| 1899-00 | 17.2% |
| 1900-01 | 17.0% |
| 1901-02 | 18.3% |
| 1902-03 | 19.3% |
| 1903-04 | 21.4% |
| 1904-05 | 20.9% |
| 1905-06 | 13.2% |
| 1906-07 (baseline, not column-wise) | 99.3% |
| 1907-08 | 15.7% |

Every column-wise-extracted season sits at 13-21%; every
baseline-extracted season (including 1906-07, which was never migrated
to column-wise) sits at ~100%. This means roughly 80-87% of events in
8 of the corpus's 18 seasons currently have **no calendar date at all**
in `research.event.date` -- `date_undate` and, downstream,
`corrected_date_undate`/`date` are simply NULL. This is a far larger
gap than the 3 typos that led here, affects any date-range query
against those 8 seasons today, and is NOT yet fixed -- flagged here as
its own open item, deliberately not tackled in this pass (needs either
propagating `month_text`/`year_text` across a page's sessions during
flatten, or reconstructing it from each page's own printed header date
range, and deserves its own scoped pass rather than a bolt-on here).

**Verified**: tested the `_MANUAL_DATE_OVERRIDES` mechanism against a
scratch copy of the database (not the original) -- all 9 affected rows
(3 theaters x 3 pages) now resolve to `corrected_manual` with the
correct scan-verified date. Not yet run against `outputs/full_run/`
itself (batched with the rest of today's propagation, per RG's
instruction) -- `validate_performance_dates.py` needs to be re-run
there whenever that batch happens for these three corrections (and any
future ones) to actually reach `research.event.date`.

---

**2026-09-11, the deferred 123-value truncated-weekday task, done --
actually 147, not 123.** Picked up the background task spun off two
addenda back. Re-ran the truncation check with the same
day-number-unambiguous logic but counting every affected session row
rather than distinct values: **147** across the 5 flagged pages
(`1903-04_p018`: 16, `1907-08_p016`: 36, `1907-08_p020`: 24,
`1907-08_p022`: 37, `1907-08_p032`: 34) -- the original 123 undercounted
`1907-08_p020`'s 24 by missing that page from whatever tally produced
the earlier estimate, the same kind of unscoped-estimate correction
seen elsewhere in this issue (the 76-vs-64 pass above).

**Method matched what the original flagging predicted**: on
`1903-04_p018` and `1907-08_p020`, every truncated stem has a full-form
sibling elsewhere on the same page (a different theater column or
session leg already carrying the untruncated word for that same day
number) -- derived a day-number-to-full-text map from each file's own
already-correct rows and filled the truncated ones from it, with no
new transcription. On `1907-08_p016`, `1907-08_p022`, and
`1907-08_p032`, entire calendar days had no full-form sibling anywhere
on the page, so those weekday strings were read directly off the page
scans instead of assumed from corpus convention.

**That scan check paid off: `1907-08_p032` uses genuinely shorter
abbreviations than the rest of the corpus for two of its weekdays,
confirmed by zooming the scan rather than trusting the convention seen
on other pages** -- `17 Воскр.` (not the `Воскрес.` used everywhere
else, including `1907-08_p016`'s own `2 Воскрес.`) and `21 Четв.` (not
`Четвергъ.`), both printed with a period and clear whitespace after in
the column, i.e. not truncated by a tight crop -- genuinely how this
page's typesetting abbreviated those two days. Restored verbatim as
printed rather than normalized to the more common corpus form; every
other restored value across all 5 pages matched the standard
full-word-plus-period convention exactly (`Суббота.`, `Воскрес.`,
`Понед.`, `Вторн.`, `Среда.`, `Четвергъ.`, `Пятница.`) once read off
the correct page. Day numbers were left untouched throughout -- only
the weekday text changed.

**Verified after fixing**: all 147 target sessions now end in a full
word + period (nothing left matching the old truncated-stem shape);
JSON structure, session counts per file, and every non-`date_text`
field unchanged.

**Not yet propagated into `outputs/full_run/`** -- per RG's explicit
instruction, this fix is being batched together with the other pending
Gate 3 rounds rather than propagated on its own.

*(Reconciled here from a parallel worktree session's `claude/peaceful-hugle-4058ff`
branch, which had branched off before this issue existed on this branch
and so logged the same entry provisionally in its own copy of this
file; this is that entry's canonical home.)*


---

**2026-09-11, propagated all five of today's rounds into
`outputs/full_run/`.** Batched per RG's standing instruction rather
than propagated per-round: the annotation-field audit, утро/вечер
pairing check, stray-text sweep, event-date field audit, and the
shift-bug follow-up + truncated-date restoration (the two background
tasks). Also carries the new `_MANUAL_DATE_OVERRIDES` code change in
`pipeline/validate_performance_dates.py`.

Same lighter-weight in-place methodology as the earlier "3 deferred
pages" propagation this same day, scaled to the full 332-page Gate 3
corpus rather than a 3-page shortcut: ran
`parse_and_validate.py --extraction-source columnwise` fresh against
all 332 pages, spliced the result into the existing merged `parsed/`
CSVs by `page_id` (event_entry) / `event_id` prefix (event_entry_
performance) rather than touching the 1,017 non-Gate3 pages' rows at
all, then ran `build_duckdb.py` / `build_entities.py` /
`validate_performance_dates.py` / `build_research_model.py` /
`build_datasette.py` in order against a scratch copy of the live
database (never the original), verified exhaustively, then swapped in.

**Verified before swap-in** (full queries in `docs/query_log.md`):
`source_pages` 1,349=1,349, `person_entry` 21,168=21,168, non-Gate3
`event_entry` 12,094=12,094 with **zero** row-content diffs (better
than the original merge's 114 explained-but-nonzero diffs -- no
concurrent unrelated change this time); Gate3 `event_entry` 11,829 ->
11,842 (matches today's net additions exactly); 0 orphaned
`event_entry_performance` rows, 0 duplicate `event_id`s;
`entities.person_link`/`person_merge_log`/`person` all exactly
unchanged (21,168 / 1,022 / 4,359) and `person_link` set-equal;
`research.person_appearance` byte-identical (21,154 rows);
`research.theater`/`person` unchanged (6 / 2,894); `research.work`
4,410 -> 4,451, `research.event` 29,141 -> 29,219, `research.performance`
25,313 -> 25,466. `_MANUAL_DATE_OVERRIDES` confirmed landing correctly:
all 9 affected rows show `date_confidence='corrected_manual'` with the
scan-verified date. Spot-checked `1902-03_p019`'s Большой театръ
sequence and `1904-05_p013`'s `13 Суббота.`/`14 Воскрес.` split against
what this session actually fixed -- both match exactly.

Swapped `imperial_theaters.duckdb`, `research_dataset.sqlite`, and
`parsed/` into `outputs/full_run/` via move-aside-then-replace, `cmp`
confirmed the live files byte-identical to the verified scratch copy,
then deleted the pre-patch snapshot and scratch working directory --
nothing left lying around.

`outputs/full_run/` now reflects everything in
`outputs/gate3_columnwise/raw_columnwise/` as of today, including the
`corrected_manual` date fixes. The `date_undate` coverage gap
(13-21% fill for column-wise seasons) documented two addenda up is
**not** addressed by this propagation -- it's a `flatten_repertoire_page`
pipeline fix, not a data fix, and needs its own scoped pass. Publishing
(HF upload + Cloud Run redeploy) remains explicitly deferred.


---

**2026-09-11, closed the `date_undate` coverage gap.** Follow-up to the
"event-date field audit" addendum above, which found column-wise
extraction populates `month_text`/`year_text` on only ~13-21% of
sessions per season (vs ~100% for baseline extraction), leaving
~80-87% of events in 8 of 18 seasons with no calendar date in
`research.event.date` at all. RG asked for a small, targeted
re-extraction of each page's own printed header date range rather than
pure inference, since the header states the exact bounds unambiguously
and inference would have to guess at a page's month from context.

**`pipeline/extract_page_headers.py`** (new): crops the top 15-20% of
each of the 332 Gate 3 page renders (generous margin, no table content
needed) and asks for ONE verbatim string -- the header line itself
(e.g. "16 февраля. 1908 г. 23 февраля."), not structured fields, so the
model isn't trusted to split it correctly; a regex in
`parse_and_validate.py` does that afterward, the same verbatim-in/
parsed-out split `date_text` itself already gets. 332 pages, ~572K
tokens total, on the order of a handful of full-page calls -- nothing
like a full re-extraction.

**Verification before trusting the header dataset**: 15 pages returned
an empty string on the first pass (crop too tight for a handful of
pages where the header sits slightly lower) -- fixed with a taller
crop, all 15 resolved on retry. 46 more failed a structural regex
check (most were the model truncating its own output mid-string, a few
were "I"/"II" Roman-numeral misreadings of a decoratively-printed "1"/
"11" digit in the header's own numeral font) -- independent resampling
fixed 42 of 46 outright (confirming non-determinism, not a systematic
crop problem); the remaining 4 (2 Roman-numeral, 2 "г.г." punctuation
variants the regex hadn't accounted for) were resolved by hand-checking
the scan and widening the regex, respectively. A season/year
cross-check (does the header's year fall inside the page's own season)
caught one confident-but-wrong hallucination (`1907-08_p033` returned
"...1902 г...." for a page that should say 1908) -- 3/3 independent
resamples then agreed on the correct value. A stronger check --
does the header's own start/end day match the first/last day-number
actually printed on the page -- caught 2 more real header mistakes
(`1905-06_p044`: hallucinated "10 марта" instead of the real "19
апрѣля"; `1907-08_p048`: misread "19" as "10") and one genuine PRINTED
error in the 1902 book itself (`1902-03_p008`'s header literally says
"22 ноября. 1902 г. 3 октября." -- November before October -- but the
table's own internal "Ноябрь" divider row proves the true order is
October 22 - November 3; kept the header text verbatim, only the
*derived* month assignment used for backfilling is corrected, via a
small documented override next to `_MANUAL_DATE_OVERRIDES`'s own
pattern). All 332 headers now pass both cross-checks.

**`pipeline/schemas/repertoire.py`**: `flatten_repertoire_page` gained
an optional `page_header` argument and a new `_backfill_month_year`
helper. Column-wise extraction emits one theater's entire run of
sessions contiguously and in print order (confirmed against the raw
JSON) -- walking each theater's own day-number sequence and switching
from the header's start month to its end month at the one point (if
any) where the day number decreases recovers the right month with no
guessing at any individual row's content. Critically, this only ever
feeds the *derived* `date_undate` computation -- `event_entry.month_text`/
`year_text` stay exactly what the model read on that specific row
(empty if empty), never backfilled, so the verbatim/derived boundary
CLAUDE.md's architecture describes for `date_undate` stays intact.
`parse_and_validate.py` gained a `--page-headers` flag and
`load_page_headers()` to wire a header CSV through.

**Two pre-existing `validate_performance_dates.py` limitations, invisible
until 100% coverage exposed them, fixed as part of the same pass**:
- Block-level cross-theater agreement compared raw `date_text` strings,
  so any cosmetic OCR variance between theater columns (trailing
  period, ъ/ь, abbreviation length) registered as `intra_block_
  disagreement` even though every column agreed on the actual weekday.
  Now compares the *parsed* weekday (reusing `_parse_dow`) instead.
- `_DOW_PREFIXES` was missing several short forms actually used in the
  corpus (пн/вт/ср/чт/пт/сб/вс and a few 3-letter variants) and didn't
  tolerate a stray internal space ("Пя тница") -- both added/fixed.
  Together these took gate3's `intra_block_disagreement` count from
  1507 (mostly cosmetic noise) down to 20 genuinely worth a human's
  attention.

**Net result on the 332 Gate 3 pages**: `date_undate` fill 13-21% ->
100%. Weekday-verified rate 85.8% -> 99.3% (the run-based auto-correct
heuristic then caught a further pre-existing whole-page day-drift bug
on `1905-06_p028`, 31 rows, entirely on its own -- invisible before
today because that page had no date_undate at all to check). 33
residual rows (0.3%): the 9 already-known `corrected_manual` typos plus
a handful of newly-visible, genuinely rare isolated OCR letter-
transposition artifacts (e.g. "Воекрес" for "Воскрес", "Ворникъ" for
"Вторникъ") -- correctly left flagged, not guessed at.

**Propagated into `outputs/full_run/`** the same way as the batch
earlier today: scratch copy, full pipeline re-run, exhaustive
verification (non-gate3 rows exactly byte-identical -- 0 diffs this
time, even better than the earlier merges' explained-nonzero diffs;
entities/person continuity exactly preserved; `research.person_appearance`
byte-identical), swap-in, cleanup. One expected, benign side effect:
`research.event`'s synthesized `not_captured` completeness-gap count
dropped from 5,283 to 3,934 -- `performed`/`no_performance` counts are
exactly unchanged (18,427 / 5,509), so this is strictly a *more
accurate* gap count now that per-page date ranges are reliable, not a
loss of real data.

`outputs/gate3_columnwise/page_header_dates.csv` (332 rows, the
verified header dataset) is kept on disk like the raw `*.raw.json`
responses it complements -- gitignored under `outputs/`, but worth
preserving rather than re-extracting if this pipeline is revisited.

**Not yet addressed**: the 1,050 `intra_block_disagreement` rows on the
NON-Gate3 (baseline-extracted) portion of the corpus -- confirmed
pre-existing (not introduced by this pass, and only modestly improved
by the two general-purpose `validate_performance_dates.py` fixes above),
out of scope for this Repertoire-column-wise-focused pass. Also
untouched: `1907-08_p036`'s Alexandrinsky column carrying 3 extra rows
(6-8 марта) that appear to belong to an adjacent page -- a real,
narrow column-wise contamination bug, found as a side effect of the
day-range cross-check, flagged here rather than fixed (out of scope for
a header-extraction pass).


---

**2026-09-11, `1907-08_p036` investigated: not a bug, a second instance
of a genuine printed header typo.** Follow-up on the contamination
concern flagged in the date-gap-closing addendum above (the
day-range-vs-raw-JSON cross-check had flagged this page because its
header claims to start at day 9, but all three theaters' sessions
start at day 6).

Checked the scan directly, both for this page and the prior page in
the same city's own sequence (`1907-08_p034`, Petersburg, ends cleanly
at `5 Среда.` with no overlap). **`1907-08_p036`'s table genuinely,
correctly starts at `6 Четвергъ.` across all three theaters** --
picking up exactly where `p034` leaves off, no gap, no duplication.
The Moscow companion page for the same window (`1907-08_p037`)
confirms this independently: its own header reads "6 марта. 1908 г.
16 марта.", matching the table's true start day.

**`1907-08_p036`'s own printed header says "9 марта." where it should
say "6 марта."** -- confirmed directly against the scan, a single
misprinted digit, the same class of source-level error as
`1902-03_p008`'s swapped month names two addenda up. Unlike that case,
this one needs no code fix at all: `_backfill_month_year` only ever
uses the header's start/end *month* to decide where a page's one
possible month-rollover happens, never the exact start/end day -- and
this page never crosses a month boundary (everything is `марта`
start to finish), so the wrong day digit never reaches any date
computation. Confirmed `raw.event_entry.date_undate` for the `6
Четв.` row is already correctly `1908-03-06` in the currently-live
`outputs/full_run/` (propagated in the previous addendum, before this
page was singled out for a closer look) -- nothing to re-propagate.

`page_header_dates.csv` keeps the verbatim "9 марта. 1908 г. 16
марта." unchanged, same reasoning as `1902-03_p008`'s kept-verbatim
header: the book's own error belongs in the record of what was
printed, not silently corrected.

**No raw JSON edit was needed.** `check_repertoire_cross_theater_date_mismatch`
confirmed 0 both before and after this investigation (nothing changed).


---

**2026-09-11, closed the last known Gate 3 loose end -- turned out to
be a whole-column bug, not one date: `1901-02_p018`.** The one isolated
titles-in-`annotation`-instead-of-`works` case flagged (but
deliberately not fixed) during the shift-bug follow-up several addenda
up was `16 Воскрес.`. Fixing it and re-checking the rest of this page's
Михайловскій театръ column (all of it tagged `_repair_tier:
"baseline_fallback"`, the same two-tier repair pass implicated in
earlier whole-column bugs this issue) found the identical pattern on
**every other date on the page** -- 10 more sessions, not just the one
flagged.

`16 Воскрес.` is a genuine morning/evening compound day: both legs had
been captured as `session: "unspecified"` duplicates, each mixing a
genuine note with the real performance title in `annotation`, `works`
left empty. Morning: "Спектакль для учащейся молодежи." (note) + "Le
philosophe sans le savoir, com." (title). Evening: "Bénéfice de m-lle
Barety." (note) + "Yvette, com." (title). The other 10 dates (`17
Понед.` through `29 Суббота`) needed the same works/annotation split,
several with two titles in one string (`17 Понед.`: "Омуть, ком." +
"Пожарь, сп."; `21 Пятница`: "Школьные товарищи, ком." + "Красный
цвѣтокъ, др. ят." -- kept "др. ят." together as one genre string,
matching how it was originally extracted, not split further) and two
more with a genuine benefit note ahead of the title (`22 Суббота`:
"Bénéfice de m-lle Salmon." + "Pour être aimée, com."; `29 Суббота`:
"Bénéfice de m-r Paul Reney." + "Crime et châtiment, scène."). Moved
substrings only -- no retyping -- to avoid the transcription risk this
issue already caught once before (the Грѳза/Грѳва slip).

**Verified**: `check_repertoire_cross_theater_date_mismatch` still 0,
malformed-receipts still 9, 332/332 theater coverage, session count
unchanged (11,842 -- pure relabel/field-splits, no sessions added or
removed). The duplicate `(theater, date_text, session)` triple on this
page is gone.

This closes out the last known open item from today's rounds on the
1899-00 through 1907-08 (Gate 3) corpus. Propagated into
`outputs/full_run/` the same day (see the query_log.md entry) --
verified exhaustively (0 diffs on untouched pages, entities/person
continuity preserved) before swap-in.


---

## 70. Fold-split extraction for the two-page-spread Repertoire seasons
(1890-91..1897-98) -- Phases 1-5 built; found and fixed the real cause
of #68's 14-63% spread-format scores along the way

**Context.** Issue #68's addendum (2026-09-08) measured column-wise
extraction at 77-100% receipts agreement on every single-page season
but only 14-63% on every spread season (`1895-96_p002` 63%,
`1893-94_p001` 23%, `1892-93_p008` 14%), and named three untested
hypotheses for the gap: more theater columns, rotated date labels, the
binding fold. RG, 2026-09-11: "Let's start brainstorming how to tackle
the two page spreads." Direct scan sampling (8 pages, one per season)
found something the #68 investigation didn't have: each spread splits
cleanly into two independent, complete single-page-format tables (own
theater columns, own date column, own genuine printed page number),
which is the premise the plan below builds on.

### Phase 1-2: physical split (`pipeline/split_spread_pages.py`)

Finds the fold's cut line per page and splits into two overlapping
half-images. Confidence-tiered search band (fold-trace estimate ±260px
when high-confidence, ±500px when low-confidence -- every one of the 91
spread pages has SOME fold-geometry entry, none are truly untraced) using
`row_detect`'s own `_row_darkness_profile`/`_find_peaks` on the band,
not `_detect_line_curves`/`_build_chains` (built for a different
problem, untested at this aspect ratio). A single dominant peak is
accepted directly as the cut (not just a two-peak gap) -- confirmed
necessary on `repertoire_1891-92_p000`, whose one clean peak sat right
at the true fold but was being discarded for lack of a second reference
point.

**Straddling rows are common, not rare.** The original 8-page sample
suggested ~37%; the full 91-page run measured **47/97 (48%)** via a
tight-band ink-density check, and spot-verification confirmed real
cases (e.g. `repertoire_1892-93_p001`: "Заварила кашу-расхлебывай,
фарсъ. / Перекати-поле, карт." visibly split across the physical fold).
`split_page()` therefore gives each half a 500px overlap past the cut
(sized from measured row heights, 150-500px in the samples checked) so
a straddling row lands complete in at least one half; downstream de-dup
against the recorded `SplitExtent` bounds is not yet built.

Also found and fixed: every top half's OWN top edge is the physical
page's outer edge, and the scan catches a dark sliver of book cover
there -- confirmed as the cause of a real Phase 5 failure (see below).
`TOP_EDGE_TRIM_FRAC = 0.08` trims it before any downstream crop sees it;
8% comfortably clears the measured ~100-200px band while the true table
header doesn't start until ~17% down.

### Phase 3: page-number verification (`pipeline/extract_split_page_numbers.py`)

Reads each half's real printed page number from its left-margin strip
(rotated; the DATE-RANGE header turned out to be a separate thing on
the RIGHT margin, not this). Full 182-half run: continuity chained
cleanly except 15 misreads, all hand-verified against the scan and all
had one plain, legible true value -- e.g. `repertoire_1890-91_p001`
read "14" for a printed "4" (spurious digit), four different seasons'
"p003" tops all read empty for a plainly legible "8", one page's number
was hidden behind a library RECAP stamp but still legible past it. A
same-crop resample was confirmed USELESS here (returns the identical
wrong answer every time -- this model is near-deterministic on this
kind of short, simple read) so the 15 were corrected by hand rather
than automated further; see `hand_verified_note` in
`split_page_numbers.csv`. One genuine parsing bug fixed along the way:
"II" is a misread "11" (I/1 glyph confusion), not the Roman numeral 2.

**Two genuinely separate findings surfaced here, not extraction bugs**:
`repertoire_1890-91` pages 8-9 are missing from this render entirely
(RG: rescanning); pages 10-11 were rendered TWICE under two filenames
(RG: accidentally scanned the same two pages twice). Both are known,
expected, and unrelated to anything below.

### Phase 4: column-bounds config (`docs/repertoire_column_bounds.json`)

New `"<season>:<parity>"` `spread_split` entries for all 8 seasons,
measured fresh against actual split halves via `_refine_dividers`
(raw `_detect_vertical_dividers` alone found a clean 5-divider set on
only 1-6 of 12 sampled halves per season/half -- the same noise problem
already documented for single-page seasons). Every split half's real
page number is even for the top half, odd for the bottom, with zero
exceptions across all 182 -- so the existing `parity_of()`/
`column_group_for()` machinery already resolves top vs. bottom
correctly with no new code. `1891-92` and `1893-94` show a real,
non-noise top/bottom divergence and get genuinely different `:0`/`:1`
values; the other 6 seasons converge and keep identical values in both
keys purely for lookup consistency. `1890-91` could not be measured
this way at all (100% fallback to the template on every sampled
half) -- carried forward as an unverified prior, flagged in
`_needs_review`.

Also: hand-measured bounds for the 6 true `single_leaf` pages
(`flag_fold_damage.classify_page`: landscape, no fold, never split) --
automated detection wasn't worth building for a group this small (2/6
even found a genuine candidate via seeded refinement). Required a small
fix to `pipeline/crop_to_table.py`'s `column_group_for()`: it only
checked `"<season>:<parity>"` then `"<season>"`, so a `single_leaf`
page's own render-index parity would have collided with and wrongly
applied its season's new `spread_split` bounds. Added an exact-`page_id`
check ahead of the parity/season fallback.

**Margin crop**: tested empirically (`crop_to_table.detected_rows`
before/after), not assumed -- applying the seasons' existing `x0`/`x1`
crop bounds (not `y0`/`y1`, fit to the whole 2-leaf image and
meaningless for a single split leaf) fixed `1892-93` and `1894-95`'s
row detection (3/8 and 3/8 zero-detection pages -> 0/8 each). Not yet
wired into the actual split-half pipeline.

### Phase 5: run the existing column-wise pipeline -- and the big finding

Running `pipeline/run_pilot.py --column-level` unmodified against a
4-page smoke sample (`repertoire_1893-94`, both halves of two source
spreads) surfaced a severe, page-specific failure: the date-only column
read only 3 rows out of ~13 actually printed, on 2 of 4 pages, with
`n_theaters_ok=0/5` on each. Direct inspection of the actual crop
(confirmed the crop itself was legible, ruling out a rendering problem)
found the real cause was structural, not a model reliability problem:

**`detect_columns()`'s date-only crop for `date_side="right"` extended
unconditionally to the image's own right edge.** On every spread season
checked, there is a wide blank margin past the table's own true border,
and further out in THAT margin sits a wholly separate printed
element -- the page's own running date-range header (the same kind of
thing `extract_page_headers.py` reads for single-page seasons) -- not
part of the per-row date column at all. Worse: **the divider position
feeding that crop (`divider[4]`, `Малый`|`Date`) was itself wrong on
every one of the 8 spread seasons** -- it was never actually measured
when the whole-spread config was first built (2026-09-08, #68's
addendum), only extrapolated one theater-width past `divider[3]`, and
landed in that same blank margin rather than on the real boundary.
Re-measured directly against the scan (grid-overlay contact sheets,
2%-precision) on all 8 seasons: the true boundary sits at ~0.82-0.86 of
table width, not the ~0.90-0.94 the old config carried; the true date
column's own width past that boundary is a small, fairly consistent
~0.034-0.055 of table width regardless of season.

**This is very likely the actual, previously-unidentified explanation
for #68's 14-63% whole-spread scores** -- not primarily the fold or
rotation hypotheses that addendum named. The date crop was reading the
wrong region entirely, not failing to read a genuinely hard one; a
model reading rotated text well (confirmed directly: one `1893-94`
bottom-half page read 18 dates correctly on the first try) says the
rotation itself was never the blocker.

**Fixed in two places**:
- `pipeline/row_detect.py`: `detect_columns()` gained
  `date_col_width_frac`, bounding the date crop's right edge at
  `lo[-1] + date_col_width_frac * W` instead of `W` itself.
  Deliberately NOT solved by detecting the table's own outer border
  directly -- that border detection is exactly the fragility
  `_detect_vertical_dividers`'s own docstring already documents and
  works around.
- `docs/repertoire_column_bounds.json`: `divider[4]` corrected and
  `date_col_width_frac` added for all 24 spread-format entries (8
  plain `"<season>"` + 16 `spread_split` `"<season>:<parity>"`).

**A second, smaller fix in the same pass**: `process_page_columnwise`'s
date-only call gets a multi-attempt retry (`DATEONLY_MAX_ATTEMPTS=3`)
with a plausibility check against the theater columns' own row counts
(`_date_rows_plausible`, ≥0.4× the best theater's row count). Confirmed
this class of failure genuinely benefits from resampling, unlike the
page-number task above -- one page's date read went 3→19 rows on a
single retry with the identical crop and prompt. Also confirmed a
single resample is not always enough: a persistently-stuck page
(`repertoire_1893-94`'s other broken half) returned the exact same 3
rows across 4+ independent calls, trim fix included -- this turned out
to be the SAME wrong-region bug above, not a separate model-reliability
issue, and resolved once the crop itself was fixed.

**Verified on the same 4-page sample after both fixes**: every date
read went from ~0-3 rows to 11-18, several theaters now reconcile
exactly (13/13, 10/10) against it, and the residual mismatches (11 vs
13, 12 vs 13 row counts) are ordinary VLM row-count noise -- ground
already covered by the existing merge/retry machinery -- not the
systematic wrong-column failure this addendum is about.

**Not yet done**: Phase 6 (the plan's own broader pilot -- the 3
`#68`-baseline pages plus an expanded, hand-verified sample across
seasons, reporting receipts agreement per season before any full-corpus
decision); a cross-split date-continuity de-dup check for the
straddling-row overlap; re-deriving `divider[4]`/`date_col_width_frac`
for `1890-91` by some means other than the failed automated
re-measurement.


### Addendum (2026-09-12): Phase 6 pilot run -- two more config bugs found
and fixed, then 7/8 seasons hand-verified clean against the scan

Ran the plan's own Phase 6 pilot: the 3 `#68`-baseline pages
(`1895-96_p002`->real pp. 6/7, `1893-94_p001`->pp. 4/5, `1892-93_p008`->pp.
18/19) plus one page per season (adding an `1891-92` page to stress-test
the low-confidence path and 4 more `straddle_suspected` pages beyond the
3 already known) and one `single_leaf` page -- 17 pages total.

**Two more bugs found before the sample would even run cleanly:**

1. **Reframe bug, 3 seasons.** The previous divider[4] fix for
   `1892-93`/`1894-95`/`1895-96` was computed in the CROPPED reference
   frame (matching divider[0-3]'s own convention for those 3 seasons,
   which do have a real `repertoire_crop_bounds.json` entry) -- but that
   crop is never actually applied anywhere in the real `--column-level`
   pipeline (confirmed by `grep`: it's referenced only inside
   `crop_to_table.py`'s own separate, unused-here CLI). This
   reintroduced the exact wrong-region failure from before on these 3
   seasons specifically, confirmed directly: the resulting divider for
   `1895-96` sat at 2562px on a 2858px-wide page, past the true border
   at ~2501px. Reverted to the raw-image-frame values actually measured
   against the scan.
2. **`single_leaf` pages never had `date_col_width_frac` at all** -- it
   was added only for the spread-format seasons in the original fix.
   Checked rather than assumed: confirmed on `repertoire_1895-96_p012`
   and `repertoire_1890-91_p000` that these 6 pages share the identical
   boxed-column-then-separate-margin-header structure. Measured and
   corrected `divider[4]` + added `date_col_width_frac` for all 6.

**A third, smaller crop-padding bug found during hand-verification**:
`repertoire_1893-94_p004`'s Мариинскій column was silently truncating
content mid-line under the default `theater_pad` (15) -- "Гарлемскій
тюльпанъ, бал." read as just "Гарлемскій тюльпанъ", "1306 р. 70 к." read
as just "1306 р.", on every row checked. `theater_pad=150` (the same
value already used for the existing `1903-04` override) fully recovers
both; checked directly for the cross-theater bleed the existing code
comment warns 150px could cause on a narrow spread-format column --
none found, 4/5 theaters on this page now reconcile at the full
expected row count with correct content in each column.

**Hand-verification against the scan, 7 of 8 seasons, every field
checked came back correct**: titles, receipts (rubles AND kopecks,
including the genuine "— к." dash notation, preserved verbatim rather
than normalized), weekday words, morning/evening session splits with
their own separate receipts, multi-line benefit annotations, and
dark/blank-row flags. Specific matches confirmed line-for-line against
the scan on `1890-91_p013`, `1891-92_p019`, `1892-93_p018`,
`1893-94_p004`, `1894-95_p010`, `1895-96_p006`, `1896-97_p010`,
`1897-98_p018` -- a dramatic contrast with the 14-63% whole-spread
scores that started this whole thread.

**One isolated, confirmed-unfixable failure**: `repertoire_1890-91_p012`
-- identical wrong date-column read across 4+ independent calls, crop
visually confirmed correct (the true per-row date column is legible and
dominant in the frame). Not a config or code problem; a genuine
`needs_review` case for hand-transcription, same as `_needs_review`
entries elsewhere in `docs/repertoire_column_bounds.json`.

**Not yet done**: a broader corpus rollout decision (this pilot passing
cleanly is the gate the plan set for that, not the rollout itself); a
systematic sweep for the SAME kind of `theater_pad` truncation on the
other 7 seasons (only found by hand-verifying `1893-94` specifically --
plausible it recurs elsewhere, not yet checked); the cross-split
date-continuity de-dup check for the straddling-row overlap, still
outstanding from the original Phase 1-5 addendum above.


### Addendum (2026-09-12/14): full-corpus sweep (the `theater_pad` check
promised above) -- one large, previously-unknown bug found (theater
identity collision on ~half the corpus), one false alarm caught and
corrected before being treated as a bug

**What prompted this**: RG asked for the `theater_pad` truncation check
above to be run against the whole 91-page corpus (180 split halves)
rather than the 8-9 page pilot sample. Ran the actual (billed)
column-wise extraction across all 180 halves -- ~3.9M tokens -- rather
than trying to infer this from crops alone, then applied the same
receipts-inconsistency heuristic used in the pilot.

**The receipts heuristic itself stayed clean at this scale**: 53
page/theater combinations flagged a bare "NNNN р." with no kopecks
alongside other rows that do show kopecks. Checked the 4 most extreme
(highest no-kopecks-to-has-kopecks ratio) directly against the scan --
all 4 genuine (the source really does sometimes print a whole-ruble
figure with no kopecks notation at all, already established in the
Phase 6 pilot addendum above). No evidence the `theater_pad` truncation
found on `1893-94` recurred elsewhere via this specific check.

**What the sweep found instead, while investigating an unrelated
outlier, was much bigger**: `repertoire_1895-96_p011`'s `Малый` theater
crop came out only 184px wide (vs 500-700px for its neighbors),
garbling titles from the LEFT ("Власть тьмы" read as "сть тьмы",
"Демонъ" read as "емонъ") -- and worse, `.raw.json` showed what looked
like 3-4 duplicate, overlapping session sets all labeled "Большой
театръ." for the same dates. Checking `.columns.json` directly confirmed
it: **all 5 of this page's theater crops came back named "Большой
театръ."** -- the model wasn't distinguishing them at all, just
returning the same guess five times.

Checked the crop itself: no theater-name header printed anywhere in the
image, just content starting immediately at the top. Checked a second
crop from the same page: same thing. **The theater-name header is
printed only on a spread's TOP half** -- the bottom half is a straight
continuation of the same table and never repeats it. Measured this
properly across the whole corpus (not just this one page): **89 of 90
bottom halves show the same collision** (all theater crops on that page
reading back the same name), versus 1 of 90 top halves (a different,
minor near-miss, not full collapse). This is not an edge case -- it was
the DEFAULT state for half the corpus.

**Root fix**: `TheaterOnlyPage.theater` is still asked for (kept as a
fallback for formats/pages with no configured order), but
`process_page_columnwise` now overrides it unconditionally with the
season's own known left-to-right print order -- a new `theaters` list
added to all 24 spread-format entries and all 6 `single_leaf` entries in
`docs/repertoire_column_bounds.json`, confirmed by direct scan
inspection across all 8 seasons (`Маріинскій. / Александринскій. /
Михайловскій. / Большой. / Малый.`, always in that order). Applied
unconditionally rather than only as a bottom-half fallback: this also
fixed a smaller, related issue found along the way -- even some TOP
halves were misnaming `Большой`/`Малый` as their own shared
"Московскіе театры." group header instead of their individual name.
This has the further benefit of giving fully consistent theater identity
corpus-wide regardless of what spelling variant the model happened to
read on any given page, which matters for downstream entity resolution.
Verified directly on `repertoire_1895-96_p011`: the model still says
"Большой театръ." for all 5 crops after the fix (confirming nothing
changed model-side, exactly as expected), but the 5 sessions now carry 5
distinct, correct identities. The model's own (often wrong) read is kept
as `model_said` in `.columns.json`'s merge report, not discarded --
transparency over silently masking what actually happened.

**A second, smaller bug found investigating the same page**: the
`divider[4]` fix from the Phase 6 pilot addendum above had only ever
been independently measured on ONE parity per season and assumed to
apply to both -- true for `1890-91`, but 5 other seasons
(`1892-93`, `1894-95`, `1895-96`, `1896-97`, `1897-98`) needed their own
bottom-half value, re-measured directly against the scan (gaps
0.012-0.038; `1895-96`'s 0.03 gap was large enough to be the proximate
cause of the too-narrow `Малый` crop that surfaced the theater-name bug
above).

**A dead end, caught and corrected rather than shipped as a "fix"**:
chasing why `Малый` still looked unreliable after the divider[4]
correction, found 26 corpus-wide instances of a theater column reading
back as 15-100 consecutive identical `is_dark=True, no content` rows --
looked exactly like a model hallucination loop, and `Малый` was
over-represented (11/26). Before treating this as a bug, checked the 3
most suspicious instances directly against the scan (including both
exact-100-row outliers, the most suspicious shape). **All three were
genuine**: real "--" printed for many consecutive rows in the actual
source -- extended theater closures, the same "never assume date
completeness" principle already established elsewhere in this project,
just applying to whole theaters' operating weeks rather than individual
dates. This was walked back rather than left standing as a finding --
the 26 "degenerate" reads are not evidence of a defect.

What DOES still stand on its own, independent of that dead end:
`Малый`'s crop was confirmed narrow enough on several seasons to clip
its own column header entirely (`repertoire_1890-91_p022`, directly
verified -- the header became legible only after widening). `theater_pad`
was raised to 150 (the same value already used for `1893-94`) across all
21 remaining spread-format entries on this narrower, more defensible
justification -- not the original, mistaken one.

**Final full-corpus extraction, all fixes applied** (a third full
180-half run, ~4.4M tokens, run specifically to reflect the `theater_pad`
broadening): 0/90 theater-name collisions on both halves (fully
resolved, stable); 20 of 180 pages now fully reconcile all 5 theaters
(up from 11 before the `theater_pad` broadening); per-theater-instance
reconciliation 36.0% (324/900) corpus-wide, up modestly from 34.8%. This
number should NOT be read as "64% wrong" -- given the closures finding
above, a substantial share of non-reconciling instances are the merge
logic correctly refusing to guess at genuine ambiguity or accurately
representing genuine closures, the same coverage-vs-accuracy distinction
already established for the single-page-format seasons (#68's own
addendum: "The open problem is COVERAGE, not accuracy").

**Not yet done**: a broader corpus rollout decision; a proper
receipts/title accuracy re-verification specifically on the pages
affected by today's fixes (the Phase 6 pilot's hand-verification
predates all three fixes above); the cross-split date-continuity de-dup
check for the straddling-row overlap, still outstanding since the
original Phase 1-5 addendum.

### Addendum (2026-09-14): re-verified receipts/titles on 8 representative
pages (one per season) affected by the day's fixes -- all matched the
scan exactly, including a full 5-theater single-row match on
`1897-98_p005`. Then did the cross-split de-dup check, which surfaced a
bigger finding than a dedup problem: a genuine row-alignment defect at
the split boundary.

**What prompted this**: the de-dup check outstanding since Phase 1-5
(the deliberate 500px overlap in `split_spread_pages.py` means a row
straddling the fold can be captured, independently, by both halves --
undeduplicated, every such row is double-counted). Built
`pipeline/dedup_split_overlap.py` to find every `(day, theater, session)`
key appearing in both a source page's top-half and bottom-half sessions
(`/tmp/full_corpus_raw_v3`), pairing halves via
`split_test_out5/split_page_numbers.csv`'s top/bottom page-number
mapping (the same hand-verified mapping from Phase 3).

**Initial scope**: of the 91 source pages, 39 had reconciled sessions on
both halves checkable this way (the rest await broader corpus
reconciliation). Those 39 pairs contained 2,637 combined sessions, of
which **234 (8.9%) were exact-key duplicates** -- confirming the overlap
design is doing what it was built for (a straddling row really does land
in both halves), but nothing downstream was deduplicating them.

**Triage, not auto-resolution**: RG's explicit direction (2026-09-14) was
that both open design questions here -- which half's page a surviving
duplicate row should be attributed to, and how to break a tie when two
copies are equally complete but read differently -- go to manual,
scan-based review rather than a programmatic pick ("when in doubt,
handread the scan"). `dedup_split_overlap.py` was built as a triage
queue, not a resolver: it classifies every duplicate into `exact` (both
copies byte-identical -- 78 of the 234), `clear` (one copy is a strict
superset of the other by title-multiset/receipts/annotation -- 18), or
`ambiguous` (138) with a `subtier` split into `variant_only` (43 --
resolves to the same work list once genre-suffix and curly-quote
normalization is applied, so needs only an orthography spot-check) and
`real` (95 -- genuinely differing content, full hand-read). Nothing is
discarded automatically; the queue (`/tmp/split_overlap_dedup_queue.csv`)
points each row at both halves' scan images for review.

**The `real` tier turned out not to be an ordinary dedup problem.** Of
the 95, 29 were the bottom half's very *first* theater-row for that
column -- the row sitting right at the crop's own edge, with no "before"
context for row detection to anchor against. Hand-reading all 29 against
the scan (not a sample -- every one) found:

- **19 of 29 are a confirmed row-misalignment bug**: a half-crop's theater
  column loses sync with its own date column right at the crop's boundary
  edge and silently substitutes in a *different* row's content while
  keeping the correct-looking date label. First case found directly:
  `repertoire_1890-91_p011` (bottom half), Малый, day 11 -- the scan
  reads day 11 as "Сестры Саморуковы, др. эт." + "Левъ Гурычъ
  Синичкинъ, вод."; the bottom half's own extraction returned "Новое
  дѣло" instead, which is day *12*'s title, while day 12 lost "Новое
  дѣло" and kept only half its true content. The top half's overlapping
  capture had the right content, just truncated at the crop's left edge
  ("естры Саморуковы" / "евъ Гурычъ Синичкинъ" -- missing the first
  letter of each word). Repeated, unambiguously, on `1892-93_p005`
  (Александринскій day 23 labeled with day 20's content, a 3-row
  shift), `1895-96_p007` (Михайловскій *and* Малый day 17, both
  actually showing day 15's content), and more -- see the full list
  below.
- **A testable signature, not just impressionistic**: since top's
  readings were correct in every direct check, top's own session list
  was used as ground truth to test the other 26 first-row cases
  programmatically -- does the bottom half's mismatched content match
  some *earlier* row already present in top's list? **13 matched exactly
  or as a subset** without needing a scan lookup at all (e.g.
  `1893-94_p013` Большой day 12 labeled with day 10's content;
  `1893-94_p017` Малый *and* Большой day 24 both labeled with day 23's
  content; `1897-98_p021` Александринскій day 2 (March) labeled with day
  27 (February)'s content). The remaining cases were hand-verified
  directly against the scan.
- **One case forced a correction to the working hypothesis.**
  `1897-98_p012/p013`, Малый, day 11: here it was the **top** half's
  *last* row that was wrong, not bottom's first -- top's claimed content
  ("Рцы, ком." / "Гь миръ…, ком.") is a badly garbled misread of day
  10's actual content ("Борцы, ком." / "Кто любить миръ…, ком.",
  matching receipts 1366 р. 04 к. exactly), while the bottom half's
  fresh read of day 11 was correct. So the bug is **not** "prefer top,
  bottom's first row is unreliable" -- it is "row detection is
  unreliable at a half-crop's own edge nearest the physical fold cut,
  and either half can be the one that slipped." No blanket rule
  substitutes for checking the scan.
- **8 of 29 were ordinary variance, not this bug**: OCR/orthography
  spot-checks with a real, checkable answer either way -- e.g. `Іоаннъ`
  (top, pre-1918-correct: "и" before a vowel takes "і") vs `Иоаннъ`
  (bottom, a modernized misread) on `1891-92_p007`; `Кручина` (bottom,
  correct) vs `Кручины` (top, misread) on `1891-92_p011`; `Азъ` (top,
  correct -- the historical name of the letter А ends hard-sign) vs
  `Азь` (bottom) on `1891-92_p013`. Two of these resolved in top's
  favor, one in bottom's -- no directional pattern here either.
- **2 of 29 were structural, not factual, differences**: one half put a
  second work title in the `annotation` field instead of `works`
  (`1892-93_p005` Михайловскій day 23, `1891-92_p017` Михайловскій day
  1) -- both readings carry the same information, just shaped
  differently; not a bug worth fixing at the dedup layer.

**Scope not yet covered**: the 66 `real`-tier duplicates that are *not*
a half's first/last boundary row (i.e. an interior-row collision, a
different and so far unexamined failure mode); the 43 `variant_only` and
18 `clear` tiers (spot-checks and confirmations, not yet worked through);
the 52 remaining source-page pairs (of 91) not yet checkable because one
or both halves haven't fully reconciled sessions in the current corpus
run. The true corpus-wide count of boundary-row misalignments is
therefore almost certainly higher than the 19 confirmed here -- this was
a full census of one specific slice (bottom-half first-rows within the
39 checkable pairs), not a corpus-wide sweep.

**Conclusion**: this is not a dedup-selection problem to patch over with
a "pick the more complete copy" heuristic (the `dominates()` logic in
`dedup_split_overlap.py` was explicitly built as a *triage hint only*,
never applied automatically, precisely because of findings like this).
It is a genuine extraction/merge defect in `process_page_columnwise`'s
row-alignment logic specifically at a split half's own boundary edge,
independent of the overlap-duplication issue the de-dup check was
originally scoped to find. A real fix belongs in the pipeline, not in
post-hoc row selection -- scoped separately below.

### Addendum (2026-09-14): Option A (an automatic crop-trim fix) scoped,
built, measured, and tested at scale -- then set aside as unreliable.
Option B (detect and flag, never auto-fix) built instead, with two hard
guarantees RG set (never lose text, never make up text) verified
directly against the real corpus rather than assumed.

**Option A's premise**: the boundary-row bug traces to
`split_spread_pages.py`'s `OVERLAP_PX = 500` -- worth ~2-2.5 rows at
this table's height -- handed to the model unindexed and crowded right
against a photographed page-seam artifact in every split-half column
crop. Confirmed directly (not inferred): pulled the actual crop the
model saw for `repertoire_1890-91_p011`'s Малый column and found day
11's content perfectly legible in it, well past the confusing overlap
rows -- so this was a row-counting problem, not a legibility problem,
and trimming the model's input crop closer to the true cut seemed like
a targeted fix.

**Measured, not guessed**: row height is consistent across all 8
seasons (184-235px -- `render_pages.py` normalizes DPI before this
stage runs, despite source scans varying in native DPI, per
[[source-scan-dpi-varies-by-season]]) and the tightest natural inter-row
gaps on `straddle_suspected` pages are 17-37px. A first attempt at
`margin=120px` (~3-7x the tightest gap) was simulated directly on real
page geometry and looked right -- but the first REAL extraction test
showed it was worse than the original bug: trimmed flush against the
true first row's own top border with zero context above it, the model
stopped misattributing that row and started dropping it outright
(`"8 theater day(s) against 10 calendar date(s) -- cannot localise"`).
Widened to `margin=200px` (a thin sliver of the prior row plus the full
blank gap -- the same minimal anchor a person uses to confirm "this is
where a new row starts") fixed that specific case.

**Tested against the 3-pair sample it was calibrated on: looked like a
clean win.** Every case that had been silently reconciling with wrong
content either now reconciled with content confirmed correct against
the scan, or refused to reconcile at all (honest failure). Also
surfaced that one case the earlier hand-verification had treated as a
"bottom half's own first row" (`1895-96_p007` day 17) actually sits
entirely on the TOP half's side of the physical seam on direct
re-inspection of the scan -- excluding it from the bottom crop entirely
was correct, not over-trimming.

**Expanded to all 13 confirmed-bug page-pairs (RG, 2026-09-14): the fix
did not generalize.** Of the 17 unique confirmed-bug rows: 8 correctly
converted from silently-wrong to honest refusal (the fix working as
intended); of the 9 that reconciled, only 3 were actually correct --
**6 of 17 (35%) were still wrong**, three with the true row missing
from the output entirely (`1893-94_p005` Большой day 23,
`1893-94_p011` Маріинскій day 22, `1893-94_p013` Большой day 12) and
three with correct content silently mislabeled under a shifted date
(`1894-95_p007` Михайловскій day 13 read back as day 14;
`1895-96_p007` Михайловскій day 17 as day 19; `1895-96_p007` Малый day
17 as day 18, with duplicate dates further down the same column). A
fixed pixel margin, calibrated against one page's geometry, does not
hold across pages whose true boundary-row offset varies more than that
one calibration case suggested -- and worse, it fails in the *silent*
direction: several of these still reconcile cleanly, so nothing
downstream would flag them.

**RG's call (2026-09-14): set Option A aside.** "It's my sense that a
generalized fix is not going to be feasible across pages and seasons."
The crop-trim code (`row_detect.detect_columns`'s `y_start`/`y_end`,
`run_pilot.py`'s `--split-boundaries` plumbing and
`SPLIT_BOUNDARY_MARGIN_PX`, `build_split_boundaries.py`,
`docs/repertoire_split_boundaries.json`) was reverted/deleted rather
than left half-adopted in the tree -- this addendum is the record of
what was tried and why, not the code itself.

**Option B, built instead**: never try to auto-fix a disputed boundary
row -- detect disagreement between a split page's two independently-
captured halves and route it to a human, with two hard guarantees RG
set as the actual bar (2026-09-14): **never lose text, never make up
text**.

- `pipeline/dedup_split_overlap.py` -- the original one-off triage
  script generalized into a real CLI tool (no more hardcoded `/tmp`
  paths). Unchanged in method: finds every `(day, theater, session)` key
  colliding across a source page's two halves, classifies `exact` /
  `clear` / `ambiguous` (`real` / `variant_only` / the new
  `month_rollover_collision`, below). The same output file, hand-
  annotated (`kept_half` or a typed `corrected_*` transcription), IS the
  resolutions input the companion script reads -- one file, two phases.
- `pipeline/apply_split_overlap_resolutions.py` (new) -- consolidates
  each page-pair into one trusted session list per the queue: a non-
  colliding key passes through verbatim; `exact`/`clear` auto-resolve
  (never a real conflict, just the fuller of two actual reads); an
  unresolved `ambiguous` key is held in `pending`, not guessed at and
  not dropped.

**Verifying "never lose text" found a real bug in this session's own
new code before it shipped.** A plain `{(day, theater, session): s for
s in sessions}` dict comprehension -- what both scripts originally did
-- silently drops an earlier session whenever a LATER one in the SAME
half's own list shares its key. Confirmed this genuinely happens: 16
pages, 42 sessions, wherever a half's page spans a month rollover (day
30, then day 1 of the next month -- both real, different calendar days,
same day-of-month digit). Fixed by `keyed_sessions()`: segment each
theater's own sequence on day-of-month decreases before keying, so a
rollover repeat gets a different key instead of silently overwriting;
if two sessions still land on the same key after that (confirmed rare,
and only ever observed within one half, never yet at an actual cross-
half collision), neither is dropped -- both are held for review rather
than paired by guesswork (the new `month_rollover_collision` subtier).

Verified directly afterward, not just re-counted: for all 39 checkable
page-pairs (2,637 raw sessions), every single one is findable in the
trusted output or preserved inside a pending entry. First pass of this
check found 75 "missing" (the bug above); after the fix, still 48; then
0, but only once the *verification script itself* was corrected twice
-- it was initially stricter than the guarantee it was supposed to
check, flagging harmless date-text phrasing differences (`"2
Вторник."` vs `"2 Октября."`, same calendar day) and genre-abbreviation
spelling (`"com."` vs `"ком."`, same word) as "lost" when the actual
content was correctly preserved via a superset match. Final check uses
containment, not exact equality, matching `classify()`'s own
already-established definition of equivalence -- **0 of 2,637 raw
sessions genuinely lost**.

**"Never make up text" verified by reading every code path** (not
tested empirically -- there's no way to "run" an absence of fabrication,
only to confirm the code structurally cannot do it): passthrough copies
a raw session verbatim; `exact`/`clear` copy one of the two actual raw
sessions verbatim (`dict(ts)` or `dict(bs)`, never a merge of the two);
a hand-resolved `ambiguous` row uses either a verbatim raw session
(`kept_half`) or a human's own typed transcription (`corrected_*`).
Nothing anywhere blends, interpolates, or guesses.

**Current numbers, full corpus, 39 checkable pairs**: 3,695 sessions
pass through with no collision; 95 auto-resolve (`exact`/`clear`); 146
sit in `pending_review`, awaiting hand annotation of the queue CSV --
up from the original ~138 estimate once the month-rollover fix
surfaced a few more genuine collisions.

**Not yet done**: wiring `.resolved_sessions.json` into
`parse_and_validate.py` (deliberately deferred -- still gated behind the
broader corpus-rollout decision, same as everything else in this
thread); the 52 remaining source-page pairs (of 91) not yet checkable at
all because neither half has fully reconciled sessions in the current
corpus run.

### Addendum (2026-09-15): the 146-row pending queue hand-resolved to 0
-- and the process surfaced two more real bugs in this session's own
Option B code, both fixed and verified the same way as before (direct,
not assumed).

**Applying the 29 already-known boundary-row answers first** (free --
no fresh scan-reading) dropped the queue from 146 to 90. The 42
`variant_only` rows resolved almost entirely from the JSON alone (no
scan needed): a structural rule -- prefer whichever side keeps genre in
its own field rather than duplicated in the title string -- covered 40
of them (confirmed safe by inspecting each one, not applied blind); the
remaining 2 had a genuine few-kopeck receipts discrepancy and were left
for a scan check rather than guessed.

**The 12 `month_rollover_collision` rows all traced to the same
mechanism**: a half's own list producing a spurious duplicate or
shifted-content entry right at a month boundary, while the OTHER half's
single entry for that slot stayed correct and internally consistent --
resolved `kept_half=top` (or `bottom`, once) using the same cross-
referencing technique as the rest of this addendum (a receipts figure
matching some other already-confirmed day's value pins down exactly
which day's content got misplaced). This is where hand-resolving found
a real bug in `apply_split_overlap_resolutions.py` itself: it never
actually consulted the queue for this case, unconditionally routing
every month-rollover combination straight to `pending` regardless of
what a human had recorded. Root cause: `queue_by_key` was a plain
`{key: row}` dict, and dedup_split_overlap.py deliberately writes
MULTIPLE rows under the same key for this exact case (one per
top/bottom combination) -- so loading it that way silently kept only
the last row per key, the identical failure pattern `keyed_sessions()`
was already built to prevent, just recurring one layer up, in the
consolidation script's OWN queue-loading instead of the session data.
Fixed by keying the load as `{key: [rows]}` and disambiguating by exact
`date_text` match (`find_queue_row`); also had to guard against the
same fix's new failure mode -- resolving multiple combinations of the
same month-rollover key to literally the same content would double-
count the very thing this mechanism exists to prevent, so resolved
sessions are deduplicated by content before being added to `trusted`.

**Working through the remaining 34 `real` rows found one case that
wasn't a disagreement to resolve at all**: `1897-98_p020`/`p021` day
27 and day 28 (Александринскій). Cross-referencing receipts across the
whole column showed both sides were independently CORRECT --
top's late-February entries and bottom's own, much-later, unrelated
occurrences of a day 27 and day 28 deeper in its own season -- that
happened to collide only because the matching key uses day-of-month
alone, ignoring month (a known, accepted limitation of this whole
mechanism, flagged from the start rather than discovered late). Forcing
`kept_half` to pick one side here would have silently discarded a
genuinely distinct, correct row -- a direct violation of "never lose
text". Added a third resolution value, `kept_half=both`, and changed
`resolve_row`'s return type from one `(session, disposition)` pair to a
list, so a queue row can now legitimately resolve to zero (still
pending), one (the normal case), or two (both sides independently
correct) trusted sessions -- verified this doesn't reopen the double-
counting question `keyed_sessions()` already closed, since the two
`both`-resolved sessions here have DIFFERENT `date_text`/content, not
duplicate representations of the same physical row.

**Final state, all 39 checkable page-pairs**: 3,695 passthrough, 95
auto-resolved, 141 human-resolved, **0 pending**. Re-ran the full
"never lose text" verification afterward (same containment-based check
as the previous addendum, extended to also treat a key as accounted-
for when the queue recorded an explicit resolution for it, not just a
literal string match -- resolving a collision in favor of one side is
supposed to let the other side's exact phrasing go, that's what
resolution means, not a loss): **0 of 2,637 raw sessions genuinely
unaccounted for.** The hand-annotated queue is committed at
`docs/eval/repertoire_split_overlap_queue_resolved.csv` -- every
`reviewer_note` documents the specific evidence (a scan read, a
receipts cross-reference, an established spelling rule) behind that
row's resolution, so none of this reasoning lives only in a chat
transcript.

**Not yet done**: the 52 remaining source-page pairs (of 91) still not
checkable because neither half has fully reconciled sessions in the
current corpus run -- resolving those will need a fresh
`dedup_split_overlap.py` pass once more of the corpus reconciles, not
just re-running against what's already been extracted; wiring
`.resolved_sessions.json` into `parse_and_validate.py`, same as before.

## 71. Season-label typos `1899-90` / `1905-07` fixed at source (TheaterSchoolStaff) — relabel only, no content change

**Found** 2026-09-15 while rebuilding the Obsidian vault: two
`pdf/Spiski_TheaterSchoolStaff/` files still carried their inventory-time
filename typos, `ForUpload_1899-90_Spisok_Teachers.pdf` (really 1899-00)
and `ForUpload_1905-07_Spisok_Teachers.pdf` (really 1905-06). The renames
had already been *decided* — the gold `source_pages.csv` notes record both,
with the evidence (a death date for 1899-00; the separate 1906-07 file's
printed "1906-1907" signature for 1905-06) — but never applied on disk.
`render_pages.py` takes the season straight from the filename, so the typo
became part of 11 `page_id`s and every `entry_id` below them:
11 `source_pages`, 282 `person_entry`, 257 `person_entry_service`,
8 `person_entry_credit`, 281 `research.person_appearance` rows, and
`first_/last_attested_season` for 22 `research.person` rows.
`docs/season_reviews.md` ("Season parsing") had already named these two as
the motivating case for a season validator; `render_reviews.py` got one,
`render_pages.py` never did.

**Two further consequences surfaced by the fix:**
- **A gold page has been silently unscored since 2026-08-15.**
  `theaterschoolstaff_1899-00_p000` is one of the 12 gold pages under its
  correct ID; the production parse only had `…1899-90_p000`, so
  `eval_against_gold.py` reported `gold=19 pred=0` and scored 0/0 fields —
  the page simply dropped out of the roster denominator. Re-scored on the
  relabelled parse: 157/171 fields; roster 879/1071 (82.1%) →
  1036/1242 (83.4%), grand 86.7% → 87.1%. Nothing about extraction
  changed — this is the true figure the eval should always have reported.
  (The 14 mismatches are the familiar tenure-parentheses pattern plus one
  real extraction error, `Рюминъ` with `family_name='Ивановичъ'`, not
  investigated here.)
- **Entity identity does not survive an `entry_id` rename on its own.**
  `build_person_tier1` reuses person UUIDs by entry membership in
  `entities.person_link` (#41). A first rebuild with relabelled IDs treated
  all 282 entries as never-seen, minted fresh UUIDs, and orphaned every
  prior decision on them: 143 got re-merged by `merge_duplicate_persons`,
  11 more auto-confirmed via tenure corroboration, but **20 reviewed people
  were split in two** (e.g. Погожевъ 39+4, Ширяевъ 44+4; the 1905-06
  entries now correctly overlap other 1905-06 rosters, so gate 2 refuses to
  re-merge them — the typo had been hiding that overlap). Fixed with
  `pipeline/remap_entry_ids.py`, which renames the `person_link` entry_id
  prefixes 1:1 on the DB copy *before* `build_entities.py` runs.

**Fix (no API cost; `outputs/full_run/` read-only throughout):**
1. `render_pages.py`: `validate_season()` fails loudly unless the second
   half is the first half + 1 (century rollover allowed) — confirmed it
   rejects the old filename, then renamed both PDFs (`pdf/` is gitignored;
   SHA-1 `3ae65152…` and `62c6c1d9…` respectively, unchanged by the rename).
2. New run dir `outputs/full_run_seasonfix/`: raw JSON copied with the 11
   files renamed (content untouched — the JSON carries no page_id);
   manifest relabelled and verified row-for-row against what
   `render_pages.discover_pdfs` now yields from the renamed PDFs.
3. Parsed layer: the three roster CSVs re-parsed from the relabelled raw
   JSON — byte-identical to production's modulo the season token (a
   no-rename re-parse reproduces production's roster CSVs byte-for-byte).
   The two repertoire CSVs are copied unchanged from production: they are
   the merged column-wise/fold-split product, which a plain re-parse of
   `raw/` does not reproduce, and contain neither typo.
4. DB: copy of production → `remap_entry_ids.py` → `build_duckdb.py` →
   `build_entities.py` → `validate_performance_dates.py` →
   `build_research_model.py` → `build_datasette.py`. `link_wikidata.py`
   not re-run (network; its table is carried in the copy and is keyed on
   person_id, which is now stable).

**Verification.** First, a control: the same stage sequence on an
un-relabelled copy of production reproduces all 25 tables exactly (0 rows
differ either direction), so the stages are safe to re-run. Then, the fixed
run against production with production's season tokens remapped: **24 of
25 tables identical** — every `raw`, `analysis`, `research` table, plus
`person_link`, `person_candidate` (23, 0 pending), `person_merge_log`
(1022), `person_wikidata_link`, works and theaters. The one exception is 7
tombstoned `entities.person` rows, which `build_person_tier1` carries
forward byte-unchanged by design (superseded snapshots, unpublished) and
so still read `1899-90`/`1905-07`; left as-is rather than hand-edited.
No other occurrence of either typo remains anywhere in the new DB or
`research_dataset.sqlite` (date columns `*_undate` excluded — `1905-07-…`
there is a real July 1905 date).

**Not done / for RG:** `outputs/full_run_seasonfix/` has not been promoted
over `outputs/full_run/` (outputs guardrail; also #70 is mid-flight
against production). `raw/usage_log.csv` still logs the old page_ids,
deliberately — it is a record of what was actually sent to the API. HF and
Cloud Run still serve the typo'd IDs until the next publish.

### Addendum to #70 (2026-09-15): scoped and closed most of the 52
pairs still blocked from the de-dup check -- a targeted re-extraction,
not a code fix, recovered 15 of them; the rest trace to a real,
pre-existing, already-documented bug this addendum just newly quantified.

**Scoping first**: a pair was blocked whenever at least one half had
*zero* reconciled sessions across all 5 theaters -- not the single-row
misalignment the rest of this issue is about, a whole-page reconciliation
failure. Sharply directional: of 52 pairs, **35 had only the bottom half
at zero** (top often had 40-70+ sessions), 8 had only top at zero, 9 had
both. Bottom fails completely ~4x more often than top, consistent with
everything else in this issue about bottom-half extraction being less
reliable, just a more severe symptom than a boundary row.

Checked the actual cause on every one of the 61 zero-session halves
(not a sample): **18 were the already-documented severe date-undercount
bug** (`run_pilot.py`'s own comments describe it -- a date-only call
badly under-reading a long rotated column, surviving all 3 retries; here
often exactly 3 date rows against 10-100 theater rows). **~40 were
ordinary marginal mismatches** -- the same reconciliation noise behind
the corpus's known 36% baseline rate, just landing on all 5 theaters of
one page by chance. **3 were total column failures** -- even the theater
columns returned zero rows, a crop/detection-level problem, not a
counting one.

**RG approved a targeted re-extraction** (the 61 zero-session halves
only, not the full 180-page corpus) rather than a code change --
consistent with this session's finding that a resample of the same
crop "sometimes recovers completely, sometimes doesn't": worth trying
before investing in a fix. Cost: 1,568,906 tokens (`/tmp/rerun_zero`).
Result: **21 of 61 halves recovered non-zero sessions; 15 of the 52
pairs became checkable** (39 -> 54 of 91). The other 37 pairs are
unchanged -- consistent with the severe-undercount bug being real and
not reliably fixed by a plain retry, matching what the original
`DATEONLY_MAX_ATTEMPTS` comment already predicted.

**Extended the full de-dup + hand-resolution pass to the newly-checkable
15 pairs**, merging the re-extraction into the existing corpus
(`/tmp/full_corpus_raw_v4`) and carrying forward all 146 previously
hand-resolved rows by key match (verified they matched byte-for-byte,
since none of the original 39 pairs' underlying data changed). Found 36
new colliding rows; resolved all of them the same way as before --
receipts cross-referencing against already-confirmed values, direct
scan reads where cross-referencing wasn't conclusive
(`1894-95_p008`/`p009`, 16 rows: confirmed bottom correct throughout,
and found top's Михайловскій column was contaminated with Большой's own
content on 3 rows -- "Фаустъ"/"Пиковая дама"/"Аида" are literally what
Большой shows those same days, a horizontal column-bleed, not just
truncation).

**Final state, all 54 checkable pairs**: 4,050 passthrough, 107
auto-resolved, 176 human-resolved, 0 pending. Re-ran "never lose text"
verification against the full expanded set: **0 of 3,478 raw sessions
unaccounted for.** Updated queue committed at
`docs/eval/repertoire_split_overlap_queue_resolved.csv` (290 rows, up
from 242).

**Not yet done**: the remaining 37 blocked pairs -- 18 severe-
undercount instances would need a real fix (e.g. raising
`DATEONLY_MAX_ATTEMPTS` for split halves specifically, or a different
date-crop strategy) rather than another plain retry; the 3 total-
column-failures need individual inspection; wiring
`.resolved_sessions.json` into `parse_and_validate.py`, still gated
behind the broader corpus-rollout decision, unchanged from before.

### Addendum to #70 (2026-09-15): hand-read the severe date-undercount
cases directly -- no new API calls needed, since the theater data on
these pages was already fine. Recovered 15 pages from zero sessions to
real data; pushed checkable pairs to 67 of 91.

**Re-scoped first, on the current (v4) corpus, not the pre-re-extraction
count**: of the original 18, 2 were false positives -- a single theater
column at exactly 100 rows (the same degenerate-hallucination pattern
investigated and found genuine earlier in this issue) was inflating the
"max theater rows" denominator used to flag severity. Recomputed with
the MEDIAN across theaters instead of the max: **15 genuinely severe
cases**, 13 of which show exactly `date_rows=3` after exhausting all 3
retries -- the known bug, precisely quantified this time. 12 of 15 are
bottom halves, the same directional skew as everywhere else in this issue.

**RG's question -- "can they be hand-read?" -- yes, and cheaply**: the
theater columns on these 15 pages already extracted successfully; only
the date column was broken. `pipeline/apply_handread_dates.py` (new)
re-runs `merge_columnwise_page` for a page using a hand-transcribed date
sequence against its EXISTING theater data (`<raw-dir>/<page_id>.
columns.json`, unchanged) -- no model calls at all. Safe by construction,
not just in intent: the merge only ever accepts an EXACT row-count
reconciliation, so a wrong hand-read date count simply makes that
theater refuse (same as any other page), never produces wrong data --
verified this directly (see below) rather than assuming it.

**First pass moved too fast and got caught by the merge's own safety
net exactly as designed**: reading full page-width screenshots led to
skipped and duplicated rows on more than one page -- `1892-93_p012`
came back 0/5 reconciled on a first attempt (15 hand-read rows against
theater counts of 12/22/14/13/11 -- close enough to look plausible,
wrong enough to refuse everywhere). RG: "slow down and do it carefully
... I always prefer a slow accurate reading over rushing." Switched to
cropping just the right-margin date column as its own tall, narrow,
full-resolution strip before reading it -- removes the compression that
was causing the misreads, and immediately caught two concrete errors
on that same page (a skipped day 15, and three trailing days that
belonged to a different image entirely, mixed in from reading multiple
pages in one batch). Re-verified with the crop technique: `1892-93_p009`
matched its very first (pre-crop) transcription exactly, confirming the
technique isn't just "different", it's the more reliable one. Used this
cropped-strip method for the rest.

**A genuine date gap found along the way, not a misread**:
`1893-94_p020`'s date column jumps from Feb 27 straight to March 6 (a
6-day gap) -- confirmed via the crop that this is what's actually
printed, not a row I failed to capture. Consistent with
[[never-assume-date-completeness]] (Lenten closures are common in this
period) -- recorded as read, not "corrected" to look continuous.

**Result, all 15 pages**: every one went from 0 sessions to real data.
Not every theater on every page reconciled (a theater with its own
independent row-count problem still correctly refuses, same as
anywhere else in this corpus) -- 1893-94_p021 needed one more
correction after an initial 0/5: three theaters agreed on 13 rows
against my 14, and the culprit was the boundary-adjacent first row
(day 6, sitting right at the physical fold) -- dropping it brought that
page to 3/5, the same boundary-row unreliability this whole issue has
been tracking, just caught here through a count mismatch instead of a
content mismatch. **496 sessions recovered total**, zero new API tokens
spent.

**Merged into the corpus (`/tmp/full_corpus_raw_v5`) and re-ran the
de-dup triage**: checkable pairs jumped from 54 to **67 of 91** --
larger than the 15 pages directly fixed, since repairing one half of a
pair can make the whole pair checkable even when its partner's data
was already fine. Carried forward all 182 previously-resolved queue
rows by key match; 49 new ambiguous rows surfaced, not yet
hand-resolved as of this addendum.

**Not yet done**: hand-resolving the new 49-row queue (next); the
remaining 24 blocked pairs (37 minus the 13 pairs this round newly
unblocked) -- mostly the 3 total-column-failures and severe-undercount
halves whose PARTNER half is also broken, so fixing one side wasn't
enough; wiring into `parse_and_validate.py`, still deferred.

### Addendum to #70 (2026-09-15): hand-resolved the 49-row queue the
hand-read dates surfaced. Found a genuinely new failure mode along the
way -- vertical column bleed between adjacent theaters, confirmed twice
on different season/column pairs, not the same bug as anything logged
earlier in this issue.

**182 of 231 total rows carried forward automatically** (unchanged
since the underlying data for those pairs didn't move); 49 genuinely
new. Cross-referencing against content already confirmed earlier this
session resolved most of them quickly: **clean shift chains** on
`1895-96_p002/003` (Михайловскій, -2), `1895-96_p014/015` (Малый, +1,
5 consecutive rows), and `1896-97_p024/025` (Малый, +1, 3 rows --
this one also caught bottom silently correcting a typo top had:
top's own "имепинникъ" vs the shifted match's correctly-spelled
"именинникъ", confirming the match beyond just content overlap).
Several more were plain genre-embedding-style variants, resolved the
same way as throughout this issue.

**New failure mode, found via direct scan checks on
`1894-95_p004`/`p005` and `1894-95_p012`/`p013`**: a theater's OWN
crop reading back a NEIGHBORING theater's content wholesale, not
truncation and not a date-column shift. On `p004`/`p005`, top's
"Большой" column showed Малый's own printed content for 3 separate
days (confirmed: "Въ разлуку/Баби" is verbatim Малый's day-23 entry,
not Большой's -- the real Большой day-23 is "Аида, оп.", present in
neither original reading, needed a correction combining scan-confirmed
title + receipts from scratch). On `p012`/`p013`, top's "Маріинскій"
column showed Александринскій's German-troupe titles ("Die Schme...",
"Ein Fa...") for 6 consecutive days, when Маріинскій was actually
printed as blank/dark (dashes) that whole range -- bottom's empty read,
which looked like a failure, was actually correct. Both are the same
underlying defect (a column crop capturing its horizontal NEIGHBOR
instead of itself) -- distinct from the theater-name-collision bug
fixed earlier in this issue (that one mislabeled a correctly-read
column; this one reads the wrong column's content entirely) and from
the boundary-row misalignment Option A/B were built around (this
happens mid-page, unrelated to the split or the fold). Not scoped
corpus-wide -- flagged here as a new, real pattern worth a dedicated
look, not chased further within this addendum.

**Final state, all 67 checkable pairs**: 4,387 passthrough, 138
auto-resolved, 224 human-resolved, 0 pending. Re-verified "never lose
text" against the full set: **0 of 4,362 raw sessions unaccounted
for.** Updated queue committed at
`docs/eval/repertoire_split_overlap_queue_resolved.csv` (370 rows, up
from 290).

**Not yet done**: the column-bleed pattern just found isn't scoped
corpus-wide -- worth checking how common it is outside the two
instances found here; the remaining 24 blocked pairs, unchanged from
before; wiring into `parse_and_validate.py`, still deferred.

### Addendum to #70 (2026-09-15): scoped the column-bleed pattern
corpus-wide, root-caused it to the `theater_pad=150` broadening from
earlier in this issue, and measured a targeted fix.

**Corpus-wide scope**: checked every reconciled RAW (pre-merge)
theater column against its immediate left/right neighbor for the two
concrete signatures already confirmed (`p004`/`p005`, `p012`/`p013`
above) -- wholesale absorption (one column's crop reads back almost
ALL of a neighbor's content, while the neighbor's own crop comes back
mostly blank) and fragment/truncated bleed (one column's titles are
truncated left-prefixes of the neighbor's real titles). Comparing
MERGED sessions first returned 0 matches despite the two known
instances -- the affected neighbor often hadn't reconciled that date
at all, nothing to diff against -- so the check was redone on RAW
per-row theater data instead (`.columns.json`'s `raw.theaters`, before
merge/reconciliation). That surfaced **25 candidate pages** showing one
or both signatures, concentrated on `Малый`'s left boundary
(Большой↔Малый) but not exclusively -- at least one confirmed instance
sits at Маріинскій↔Александринскій (`1894-95_p012`, already logged
above), a boundary with nothing to do with Малый's own header-clipping
history.

**Root cause, confirmed by direct before/after comparison**: compared
`/tmp/full_corpus_raw_v2` (captured before this issue's earlier
`theater_pad` broadening) against the current corpus for
`1895-96_p006`. Pre-fix, Малый's own crop was genuinely truncated
("ЛЫЙ." -- a literal fragment of its own header, the exact defect the
broadening was meant to fix). Post-fix, Большой's crop now shows
Малый's FULL content duplicated wholesale. This is a real regression
from this issue's own earlier fix, not a pre-existing problem newly
noticed.

**The mechanism**: `theater_pad` pads BOTH sides of EVERY theater
column's crop by the same amount
(`pipeline/row_detect.py`'s `date_side != "left"` branch), so any two
adjacent columns overlap by `2 x theater_pad` regardless of their own
width. At `theater_pad=150` that is a 300px structural overlap. Малый
columns run 154-312px wide across the 8 spread seasons (measured
below) -- so on the narrower end, the overlap alone exceeds the
column's own width, and either neighbor's crop can capture the
other's content wholesale. `theater_pad` was broadened to 150
uniformly (all 5 columns, both edges, all 21 remaining spread-format
config entries) on the strength of ONE confirmed clip
(`repertoire_1890-91_p022`, addendum above) -- the value itself was
never per-season measured, just adopted from what `1893-94` already
happened to be set to.

**RG's challenge, and why the original fix idea (a smaller but still
uniform per-season `theater_pad`) doesn't hold up**: even a properly
*measured* smaller value is still applied to all 5 columns' both
edges via one scalar. Four of those ten edges were never shown to have
a clipping problem at all -- reducing them along with the one that
does just trades one uncontrolled variable for another, and doesn't
explain the confirmed non-Малый bleed instance at all. The
defensible fix is targeted and asymmetric: leave the other four
columns (eight edges) at a low baseline, and widen only Малый's own
left edge, by its own per-season measured minimum. This requires a
small code change to `detect_columns`'s bound-computation loop
(`pipeline/row_detect.py:804-814`) to accept a per-column/per-edge
override instead of one scalar for the whole page -- not written yet,
scoped below.

**Per-season minimum measured directly** (one representative
split-half image per season, `Малый` column, candidate pads tested by
eye against the actual header text until "Малый." reads clean with a
real margin -- the same discipline as every other measurement in this
project):

| season  | Малый col width (px) | min. pad needed (px) |
|---------|----------------------|------------------------|
| 1890-91 | not recorded         | ~50 (already measured, earlier addendum) |
| 1891-92 | 270                  | ~0 (fully legible unpadded) |
| 1892-93 | 312                  | ~0 (fully legible unpadded) |
| 1893-94 | 293                  | ~0 (fully legible unpadded) |
| 1894-95 | 239                  | ~40 |
| 1895-96 | 154                  | ~70 (already measured, earlier addendum) |
| 1896-97 | 242                  | ~30-40 |
| 1897-98 | 183                  | ~90-100 |

Two things worth flagging rather than smoothing over: (1) `1893-94`
needing ~0px here directly contradicts it being the season whose
existing `theater_pad=150` was *adopted as the template* for the
broadening -- whatever originally justified 150 there, it wasn't this
same header-clip pattern on this page; worth a quick look before
finalizing that season's override, not assumed resolved. (2) minimum
pad does not track column width monotonically -- `1897-98` (183px)
needs *more* padding than `1895-96` (154px, the narrowest column
measured), so whatever varies (typesetting offset within the column,
font size) is season-specific and not predictable from width alone,
consistent with why this project measures per-season rather than
computing a formula. (3) `1897-98`'s own minimum (~90-100px) is close
to its own column's width (183px) -- the fix is still sound (it only
widens Малый's own left crop boundary, not Большой's right one, so it
creates no new overlap on that boundary by construction), but it's a
tight enough margin that this page deserves a direct re-check after
the fix ships, not just an assumption that "targeted" means "safe."

**Not yet done**: the `detect_columns` per-edge override code change
itself; re-running the 25 corpus-wide bleed candidates after the fix
to confirm the duplication/fragment signature actually clears;
confirming whether the confirmed non-Малый instance
(Маріинскій↔Александринскій, `1894-95_p012`) needs its own,
independently-measured override or resolves as a side effect of
reverting the other four columns off `theater_pad=150`; a
regression check on `Малый`-clipping-sensitive pages per season after
any padding reduction; the `1893-94` discrepancy noted above.

### Addendum to #70 (2026-09-15): implemented and verified the
targeted per-edge padding fix.

**Code**: `detect_columns` (`pipeline/row_detect.py`) gained a new
`theater_pad_overrides: dict[int, dict[str, int]] | None` parameter --
keyed by 0-based `theater_index`, each entry optionally setting
"left"/"right" to override the page-level `theater_pad` for just that
one edge. A small `_edge_pad()` helper resolves each bound
independently instead of applying one scalar to all ten edges;
`None` (the default) preserves the old uniform-padding behaviour
exactly, so every other caller (single-page-format seasons, the
1903-04 Александринскій override) is unaffected. `run_pilot.py`'s
`process_page_columnwise` threads a `theater_pad_overrides` key
through from the column config the same way it already does for
`theater_pad`/`date_col_width_frac`.

**Config, and a real mistake caught before it mattered**: first pass
reverted `theater_pad` and added the override only on the bare
`"<season>"` config entries. A verification run showed **zero
change** -- new crop widths matched the OLD 150-pad prediction
almost exactly. Root cause: `column_group_for`
(`pipeline/crop_to_table.py`) resolves `"<season>:<parity>"` groups
*before* falling back to the bare season key, and those
`spread_split`-format parity groups (added 2026-09-11, hand-measured
against split-half geometry) still carried their own
`theater_pad: 150`, untouched by the first edit. Caught by checking
actual crop pixel widths against the predicted new bounds *before*
trusting the fix -- exactly the discipline this whole issue has been
built on. Corrected: applied the same revert
(remove `theater_pad`) + override (`theater_pad_overrides: {"4":
{"left": <measured>}}`) to all 24 real entries (bare season + `:0` +
`:1`, all 8 seasons). Re-checked the math before spending another
API call: predicted Большой/Малый overlap on `1895-96_p007` dropped
from 300px (2x150) to 85px.

**Verification run** (15 pages matching this addendum's own
corpus-wide bleed scan -- re-implemented fresh since the original
session's exact 25-page list wasn't persisted to disk; this
re-implementation, scanning RAW per-row theater content for
exact/substring duplication between index-aligned rows in adjacent
theaters, found 15 comparable candidates and was used as the working
set both before and after): **14 of 15 pages flagged before the fix
(up to 9-11 duplicate/fragment rows each) dropped to 2 of 15 after**
(1-2 matches each). One page (`1895-96_p010`) went from `partial` to
full `ok` 5-theater reconciliation as a side benefit. All 3
previously-flagged Маріинскій↔Александринскій instances
(`1894-95_p012`, `1894-95_p013`, `1892-93_p009`) cleared completely --
confirming the "revert the base, override only the confirmed edge"
design: those boundaries never needed their own override, just relief
from the uniform 150. ~365K + ~315K tokens billed across the two runs
(the first run validated nothing, since it used the un-corrected
config -- logged honestly rather than only reporting the second).

**Checked the 2 residual pages against the actual scan (not assumed
fixed, not assumed still-broken)**: `1895-96_p006` and
`1895-96_p009`, both flagging `Малый` opera titles (`Евгеній Онѣгинъ`,
`Фаустъ`, `Риголетто`, `Демонъ`) also appearing in `Большой`'s raw
read. The scan resolves this cleanly and surprisingly: `Малый`
genuinely performed opera on these specific dates -- printed as such
on the actual page -- while `Большой` is printed as dark (a plain
"--") for those SAME rows (worth its own note: this corpus-wide
extraction had been silently assuming `Малый`, Moscow's drama house,
never staged opera; both pages directly contradict that). `Малый`'s
own reads are correct. The bleed is real, but now narrower and
specific: `Большой`'s raw extraction is not correctly reporting
`is_dark` on its own genuinely-blank rows -- it is instead pulling in
`Малый`'s real content next door, sometimes into `annotation` (row
right at a half-crop's own edge -- likely the ALREADY-documented
boundary-row-misalignment bug, not this one) and at least once
(`1895-96_p006` "Фаустъ") into `work_title` on an interior row, which
is this bug's own signature, just far smaller in scope than before.
Most likely explanation: the residual 85px overlap this fix
deliberately keeps (needed so `Малый`'s own header isn't clipped
again) is still enough for the model to reach for neighboring content
specifically when its OWN crop shows nothing to read, rather than
correctly returning `is_dark=True`. A `Большой`-dark-but-non-empty
quality check (parallel to the existing dark-cell checks in
`quality_checks.py`) would catch this pattern directly and cheaply,
worth adding as a follow-up rather than chasing the pad value lower
still.

**Bottom line**: this is a large, measured reduction (14/15 -> 2/15
pages, and the 2 remaining are a narrower, different-mechanism residual
of the same root cause, not the original wholesale/fragment pattern),
not a claimed complete fix -- consistent with how every other finding
in this issue has been reported. Not yet done: the corpus-wide
25-candidate rescan at full scope (this addendum covers the 15-page
working set only); the `Большой`-dark-but-non-empty quality check
just proposed; the `1893-94` theater_pad=150-origin discrepancy noted
in the prior addendum, still unexplained; wiring any of this into
`parse_and_validate.py`, still deferred; a fresh full-corpus
column-wise run reflecting this fix, not yet done (this was a
targeted verification subset, not a rollout).

### Addendum to #70 (2026-09-16): built the proposed quality check,
and it turned out simpler than planned -- no cross-theater comparison
needed at all.

**The insight**: both residual `1895-96_p006`/`p009` rows already had
`is_dark: true` set CORRECTLY by the model, on the same row that also
carried real leftover content (`Малый`'s title, bled into `Большой`'s
own `works`/`annotation`). That means the bug is visible entirely
within one theater's own row -- `is_dark=True` contradicting non-empty
`works`/`annotation`/`receipts_text` -- with no need to compare
against a neighboring column at all. Simpler than the corpus-wide
bleed scanner this addendum's prior entry built, and general-purpose:
not specific to column-wise extraction, the spread format, or this one
boundary, so it now runs against every `*.raw.json` directory
(`check_repertoire_dark_row_with_content`, `pipeline/quality_checks.py`,
wired into `main()`'s existing page/row/column loop next to
`check_repertoire_unknown_theater` and
`check_repertoire_malformed_receipts`).

**A directly relevant precedent found while scoping this**: issue
#68's own addendum already confirmed this exact shape once before,
independently -- `1903-04_p019`, Малый театръ, where cross-column
bleed corrupted a genuinely-dark cell's `annotation` with a garbled
duplicate of Большой's real annotation for the same date, fixed by
clearing to `is_dark: true, works: [], annotation: null`. This check
makes that failure mode routinely detectable instead of something
that has to be independently rediscovered by hand each time.

**Checked for the obvious false-positive risk before trusting it**:
could a genuinely dark day legitimately carry a closure-reason
annotation (e.g. "Праздникъ" for a holiday) alongside `is_dark=True`?
Spot-checked directly against the scan
(`repertoire_1897-98_p002`, `Большой`, four consecutive flagged rows
17-20 August): the real printed cell is a PLAIN DASH, nothing else --
no closure-reason text at all. The model's "Праздникъ"/"По крещенію"/
"Осенній" annotations on those rows are not printed anywhere on the
page; this is the same bleed/fabrication pattern, not a legitimate
convention this check would wrongly flag. No narrowing needed.

**Run against the 15-page verification set from the prior addendum**:
18 flags (3 pages) on the pre-fix run, 23 flags (3 pages, same three)
on the post-fix run -- a higher COUNT, but not a regression: before
the fix, this same underlying defect mostly surfaced as the coarser
wholesale-absorption pattern the corpus-wide bleed scanner already
measured dropping 14/15 -> 2/15 (`is_dark=False` with fully duplicated
content, a different observable shape); the fix converts most of that
into a cleaner but still-imperfect `is_dark=True`-with-leftover
pattern, which this new, more granular check is naturally better
positioned to catch than the coarser scanner was. Two different
instruments measuring overlapping parts of the same shrinking problem,
not two independent problems.

**Not yet done**: a corpus-wide run of this check (only the 15-page
verification subset checked so far, same scope limit as the rest of
this addendum chain); whether `dark_row_with_content` instances
concentrate on the same `Большой`<->`Малый` boundary specifically or
show up elsewhere too (the check itself is boundary-agnostic by
design, so this is worth knowing); a decision on whether to
auto-clear a confirmed instance to `is_dark: true, works: [],
annotation: null` (the `1903-04_p019` precedent's own fix) once this
check is trusted at scale, or keep routing to manual review like
everything else in this issue.

### Addendum to #70 (2026-09-16): rolled out to the full corpus, both
checks re-run at scale.

**The rollout**: `/tmp` had been swept clean overnight between
sessions -- the split-half image directory and `raw_columnwise` crops
survived, but the manifest and every intermediate `/tmp/full_corpus_raw_v*`
snapshot did not. Rebuilt a manifest directly from the 176 surviving
split-half images (8 seasons, 16-24 pages each -- 1894-95 the
smallest at 16) and re-ran column-wise extraction corpus-wide with the
corrected `theater_pad_overrides` config: `/tmp/full_rollout_v6`,
176/176 pages, 13 fully-reconciled (`ok`, up from single digits before
this fix), 3.8M tokens billed. Copied the raw output (not the crop
images) to `outputs/repertoire_spreadfix_v6/raw_columnwise/` --
`/tmp` has already proven unreliable as the only copy once this
session, and per this repo's own convention (`CLAUDE.md`: raw
`*.raw.json` is worth keeping, everything else regenerates) this is
exactly the artifact that belongs somewhere more durable. NOT
promoted over `outputs/full_run` -- same convention as the
2026-09-15 season-typo fix (`outputs/full_run_seasonfix/`), a
separate, later decision.

**Wholesale/fragment bleed scan, full corpus**: 4 of 176 pages
flagged (2.3%, down from an unscoped-but-clearly-much-worse starting
point) -- all four on `1895-96`, all `Большой`<->`Малый`. Consistent
with that season's own numbers: `1895-96` has the narrowest measured
`Малый` column (154px) and needed the largest override relative to
its own width of the three "moderate" seasons, so residual risk
concentrating there specifically, rather than spreading evenly across
seasons, matches the root-cause story rather than contradicting it.

**`dark_row_with_content`, full corpus**: 63 flags across 13 of 176
pages (7.4%). 56 of the 63 (89%) are `Большой` -- overwhelmingly the
same boundary, as expected. The remaining 7 are split across
`Михайловскій` (4), `Маріинскій` (2), and `Малый` (1) -- a small tail
worth noting rather than ignoring: this check is boundary-agnostic by
design, and it found a handful of instances that have nothing to do
with the `Большой`/`Малый` edge this whole fix targeted. Not yet
scan-verified whether those 7 are the same bleed mechanism on a
different boundary or something else entirely -- flagged for the next
pass, not resolved here.

**Not yet done**: whether `1895-96`'s remaining 4-page bleed residual
needs its own further-narrowed override or is an acceptable
remainder; wiring any of this into `parse_and_validate.py`, still
deferred; promoting `outputs/repertoire_spreadfix_v6` over
`outputs/full_run`, a separate rollout decision not made here.

### Addendum to #70 (2026-09-16): scan-verified all 7 non-`Большой`
`dark_row_with_content` flags -- and they are NOT this issue's bug.

Checked all 7 against the actual scan (`1891-92_p018` Михайловскій x4,
`1894-95_p007` Маріинскій, `1895-96_p011` Маріинскій, `1895-96_p017`
Малый). In every single case the flagged theater's `works`/
`receipts_text` **already matches the real printed scan exactly** --
`Михайловскій`'s "L'Article 47, dr." genuinely appears twice on
`1891-92_p018` (French-troupe repertoire, real and correctly
transcribed); `Малый`'s "Маріана, др. / Елка, ком. / Троеженецъ, сц."
on `1895-96_p017`'s `27 Суббота.` matches the scan verbatim, receipts
figure included; `Маріинскій`'s `3598 р. 50 к.` on `1894-95_p007`
matches a real printed row too (its title only -- "Паяцы, оп. /
Тщетная предосторожность, бал." -- got dropped from `works`, a
separate, ordinary title-omission, not a dark-row issue). The ONE
thing wrong in all 7 rows is the `is_dark` flag itself: `True` on a
row that has genuine, correctly-read content.

That is the OPPOSITE defect from this issue's own bug (real content
bleeding onto a row that actually IS blank) -- these are real,
non-blank rows the model mislabeled as blank despite reading their
content correctly. Different mechanism, different root cause
(something about the `is_dark` judgment misfiring specifically, not
`theater_pad`/crop geometry), and not concentrated on the
`Большой`<->`Малый` boundary the fix targeted -- confirming these 7
don't belong to this issue at all. Filed as its own thing rather than
folded into #70's own scope.

**Is it handfixable?** Yes, and unusually cleanly: because the
underlying `works`/`receipts_text` data these 7 rows already carry is
CORRECT (scan-verified above), the fix in every case is a single
field flip -- `is_dark: True -> False` -- with nothing else to
re-derive or re-read. Same shape as the existing `1903-04_p019`
precedent's fix (issue #68), just the opposite direction (that one
cleared a false-positive content row TO dark; these clear a
false-positive dark flag FROM a real content row). Low volume (7 rows
total) makes this a good candidate for the same manual-queue pattern
already used throughout #70 (`kept_half`/`corrected_works` in
`repertoire_split_overlap_queue_resolved.csv`) rather than urgent
pipeline work.

**Applied (2026-09-16)**: all 7 fixed directly in
`outputs/repertoire_spreadfix_v6/raw_columnwise/*.raw.json` --
`is_dark: false` on all 7, plus `works` restored on the one row that
had also lost its title (`1894-95_p007` `Маріинскій` `16 Воскресенье.`
-- re-zoomed the scan crop before writing anything, confirmed
"Паяцы, оп." / "Тщетная предосторожность, бал." precisely, matching
the row's already-correct `3598 р. 50 к.` receipts exactly). Each edit
asserted the expected `date_text`/`theater`/prior `is_dark` value
before writing, so a stale assumption would have raised rather than
silently miswriting a different row. Re-ran
`check_repertoire_dark_row_with_content` after: 0 flags remain on any
of the 4 affected pages (56 flags remain corpus-wide, all on the
separate, already-scoped `Большой` boundary residual this fix doesn't
touch).

Also mirrored the fix into the source `.columns.json` per-theater
rows, matched by `(theater, date_text)` via `date_rows` rather than
assumed index alignment (a `.columns.json` theater row's own `index`
is that theater's sequential position, not the merged session list's
position). Only 4 of the 7 needed the source-level edit -- the other
3 (`Михайловскій`'s `14 Пятница.`/`23 Воскр.`/`25 Вторн.`, the rest of
the French-troupe cluster) already had `is_dark: false` correctly in
the raw per-theater data, meaning THOSE 3 rows' bug was introduced
during `merge_columnwise_page`'s own merge step, not the extraction
itself -- a distinct, smaller finding worth a look if this class of
bug recurs, not chased further here since the `.raw.json` output (the
only thing `parse_and_validate.py` reads) is already correct for all
7.

### Addendum to #70 (2026-09-16): re-ran the split-overlap dedup
against the fresh `outputs/repertoire_spreadfix_v6/` data -- and
confirmed the existing hand-resolved queue could NOT have been safely
reused as-is, exactly the risk flagged pausing before this step.

**Recovering the lost pairing file**: `split_page_numbers.csv`
(`dedup_split_overlap.py`'s `--page-numbers` input) was lost in the
same `/tmp` sweep as everything else. Recovered without re-running the
billed page-number extraction: confirmed directly (0 mismatches across
all 369 rows of the existing resolved queue) that `top_page_id` always
carries the LOWER real page number and `bottom_page_id` the higher, so
each spread's pair is just its two consecutive real page numbers
within a season. All 176 surviving split-half images paired cleanly
this way -- 88 pairs, 0 unpaired stragglers (one gap, `1890-91`'s
missing 8/9, is a matched PAIR missing together, not an orphan).
Synthetic `source_page_id` values were invented for this regenerated
mapping (the true original scan IDs are unrecoverable) -- harmless,
since `dedup_split_overlap.py` only uses that field for season-parsing
and labeling, never for matching real files.

**Fresh scan result**: 41 of 88 pairs checkable (both halves
reconciled), 255 duplicate keys found -- 77 `exact` + 19 `clear`
(both auto-resolve, no human judgment needed) + 159 `ambiguous` (110
`real`, 28 `month_rollover_collision`, 21 `variant_only`).

**Comparing against the existing 369-row hand-resolved queue,
key-by-key** (not source_page_id, which differs by construction; kept
on `(top_page_id, bottom_page_id, day, theater, session)`): only 116
of 346 old distinct keys still exist at all in the v6 scan. Of those
116, a full 74 have DIFFERENT raw content now than when the old
resolution was recorded -- this week's crop/pad fix genuinely changed
what many pages read as, so re-applying an old human judgment to
different underlying text would have been exactly the kind of
unverified guess this whole issue's discipline exists to prevent.
Only 42 carried-forward keys are byte-identical in content, and of
those, 17 actually had a resolution recorded (the rest were
`exact`/`clear` tier, which auto-resolve regardless of history) --
those 17 were carried forward directly, tagged in `reviewer_note` as
reused rather than freshly checked. Everything else -- the 74
changed-content carries, plus 74 brand-new ambiguous keys never seen
before -- was left blank for fresh review. `docs/eval/
repertoire_split_overlap_queue_resolved.csv` was regenerated in place
(255 rows, replacing the prior 369 -- the row count itself isn't
comparable across the swap, since this is a different underlying
extraction, not an incremental addition to the same one).

**Remaining hand-review scope, precisely counted, not estimated**:
**142 ambiguous rows** need a fresh look (98 `real`, 26
`month_rollover_collision`, 18 `variant_only`) -- larger than any
single hand-resolution batch this issue has tackled so far (the
largest prior round was 49 rows). Not started yet -- reporting the
scope before committing to it, same pattern used earlier in this issue
("Scope the remaining 52 pairs..." before "Go ahead").

### Addendum to #70 (2026-09-16/17): all 142 ambiguous rows hand-
resolved, across three stages and two sessions (paused and resumed
twice at RG's request). Granular per-page reasoning lives in the git
history of `docs/eval/repertoire_split_overlap_queue_resolved.csv`
(one commit per page-pair batch); this entry is the consolidated
summary and the findings worth remembering.

**Final state**: 255 total queue rows -- 77 `exact` + 19 `clear`
(auto-resolve) + 159 `ambiguous`, of which 156 got a real resolution
(`kept_half`: 119 `top`, 28 `bottom`, 7 `both`; 2 used
`corrected_works`/`corrected_receipts` directly) and 3 were left
deliberately blank with a `reviewer_note` explaining why (confirmed
phantom duplicates whose real content is captured via a sibling row
instead -- keeping them too would have double-counted, not preserved
anything).

**The technique that resolved the large majority of rows, with no
scan needed**: pull each page pair's full raw session sequence for
the collision's theater(s) via a quick JSON dump and look for an
EXACT title+receipts match between the "mystery" candidate and some
OTHER already-known-correct day, usually already present in `top`'s
own clean sequence. Confirmed, repeatedly, across nearly every page in
the 1893-94 season especially: `bottom`'s date-column labels are
drifted/mislabeled relative to true row content by some amount --
often a different amount per theater on the SAME page, since each
theater's own column independently mis-tracked the date sequence.
Once one candidate on a page is confirmed via an exact match, the
SAME mechanism reliably explains the rest of that page's collisions
too -- checked, not assumed, on every page, but rarely needed a fresh
scan look once the page's own pattern was established.

**Two real bugs caught by continuing the investigation, not stopping
at the first plausible answer**:
1. A carried-forward resolution (`1893-94_p012/013`, Большой,
   "Хрустальный башмачекъ") whose reasoning cited another row's
   content that had genuinely changed between the pre-rollout queue
   and this week's fresh extraction -- the row's OWN content matched
   byte-for-byte (all the carry-forward safety check verifies), but
   the REASONING referencing a different row didn't hold anymore.
   Caught while resolving a fresh, related collision on the same page
   that happened to prove the old note wrong. Fixed, and 4 sibling
   rows on the same page pair (originally resolved `kept_half=both`
   as "real content, uncertain date") were revised to `kept_half=top`
   once the same investigation proved they were confirmed duplicates
   of top's own day-10/11/12 rows -- keeping them as `both` would have
   double-counted real sessions already present in the trusted output.
2. `1894-95_p008/009`, Михайловскій, day 17 (the `1394-95 Понедѣльник`
   collision -- Group listed above): checked the actual scan directly
   rather than picking a side, and found BOTH candidates were wrong.
   Top's own entry was a confirmed cross-column bleed from `Большой`
   (the day-17 opera title, not this theater's own French-repertoire
   content); bottom's candidate was a duplicate of this theater's own
   day-15 entry. Neither belonged -- the true content
   ("La Contagion, com." 928 р. 13 к.) was supplied directly via
   `corrected_works`/`corrected_receipts` rather than guessed from
   either flawed side.

**A smaller, structural finding worth remembering**: `/private/tmp`
got swept clean a SECOND time overnight between the two resumed
sessions (the split-half source images, not the durable
`outputs/repertoire_spreadfix_v6/` copy). One row genuinely needed a
scan look after that -- recovered without any billed re-extraction by
finding leftover per-page crop images under other, unrelated `/tmp`
test directories from earlier in this project (`margin_fix_test2` and
similar), which happened to still hold this exact page's crops from
an older pipeline test. Not guaranteed to work for every future page,
but worth checking before assuming a scan-check is blocked.

**Not yet done**: running `apply_split_overlap_resolutions.py`
against this completed queue to actually produce trusted per-page
session lists (the queue being fully resolved is a precondition, not
the same thing as having applied it); then `parse_and_validate.py` ->
`quality_checks.py` -> `build_duckdb.py`, still the full remaining
path to a queryable database, as scoped in the addendum that started
this whole dedup detour.

### Addendum to #70 (2026-09-17): `apply_split_overlap_resolutions.py`
run against the completed queue, and the "never lose text" guarantee
verified directly rather than assumed.

Regenerated `split_page_numbers.csv` a second time (`/tmp` was swept
again overnight -- the durable `outputs/repertoire_spreadfix_v6/`
copy was unaffected, but the pairing file itself lived only in
`/tmp`). Same deterministic logic as before (consecutive real page
numbers per season), rebuilt from the raw-output filenames this time
instead of the (now also gone) split-half images -- identical result,
176 half-rows / 88 pairs, 0 unpaired.

**Run result**: 3,655 passthrough (no collision) + 96 auto-resolved
(`exact`/`clear`) + 153 human-resolved sessions written to trusted
output across 83 checkable page pairs (5 of the 88 pairs have no data
on either half at all, unaffected by any of this); 3 still pending
(the 3 intentionally-unresolved phantom-duplicate rows from stage 2,
exactly as expected -- nothing else). Output copied to
`outputs/repertoire_spreadfix_v6/resolved_sessions/` (not `/tmp`,
same durability reasoning as everything else this week).

**The 153-vs-156 count difference, checked rather than assumed
benign**: 156 ambiguous rows got a real resolution, but only 153
sessions carry a `human:*` disposition in the output. Traced to the
apply script's own duplicate-collapsing logic (`seen_norm` in
`apply_split_overlap_resolutions.py`): a month-rollover collision with
multiple candidate pairings can have MORE THAN ONE queue row resolve
to pointing at the exact same top-side session (e.g. `1893-94_p012/013`'s
Большой/Малый/Маріинскій day-13 groups, where both the "vs 12 Декабря"
and "vs 13 Понед." pairings independently resolved to keeping the same
top session) -- correctly collapsed to one trusted entry instead of
counted twice. Working as designed, not a discrepancy.

**"Never lose text", verified directly**: wrote a script comparing
every raw session across all 83 checkable pairs (4,151 total) against
the trusted+pending output, but -- unlike a naive first pass, which
flagged 196 "missing" sessions that turned out to just be the
correctly-rejected LOSING side of resolved collisions (e.g. `Баль-
маскарадъ`, dropped in favor of the historically-correct `Балъ-
маскарадъ` per this issue's own day-30 resolution) -- cross-referenced
against which base-keys actually collided per `dedup_split_overlap.py`'s
own keying logic, so a session is only flagged if it's absent AND
was never part of any resolved collision at all. **Result: 0
unexplained missing sessions.** Every one of the 4,151 raw sessions is
accounted for -- present in the trusted output, pending review, or a
confirmed, resolved collision-loser.

**Not yet done**: `parse_and_validate.py` -> `quality_checks.py` ->
`build_duckdb.py` against this resolved output -- the actual remaining
path to a queryable database, now that the dedup gate (the reason this
whole detour started) is fully closed and verified.

### Addendum to #70 (2026-09-17): ran `parse_and_validate.py` ->
`quality_checks.py` for real, found a genuinely new failure mode
(`cross_theater_date_mismatch`, unrelated to split-overlap dedup), and
hand-verified all 24 affected pages against the actual scans rather
than guessing at severity.

**The new check result**: 38 of 83 "pair" pages flagged. Scoped before
chasing it: 22 were pure coverage gaps (one theater covering fewer
days than another -- expected, not a bug, matches "coverage vs
accuracy"). The remaining 24 had a genuine same-day-number
disagreement not explained by a simple coverage gap.

**Root cause, confirmed rather than assumed**: this check (built for
Gate 3's single-page-format seasons, where one shared date column
serves every theater on the page) doesn't cleanly apply to these
"pair" pages, where each theater's dates come from whichever half (top
or bottom) *that theater* happened to reconcile on -- independently
per theater. Confirmed the page-pairing itself was NOT the problem
first (checked that every flagged page's theaters cover a broadly
consistent overall date range, ruling out a mispaired spread before
investigating anything else).

**Regenerated the source images to actually check this**, since
`/tmp` had been swept a third time by this point. Re-rendered all 519
Repertoire pages from the source PDFs (`render_pages.py`, free, local,
~5 min), re-split the 8 spread seasons (`split_spread_pages.py` against
`fold_geometry.json`), and re-ran `extract_split_page_numbers.py`
(730 halves, ~1.1M tokens) to recover the render-order-to-printed-
page-number mapping -- confirmed NOT 1:1 (e.g. `1893-94_p003`'s render
order maps to printed pages 8-9, not "p008" as page IDs might suggest)
and genuinely necessary to locate any specific page. 5 of 182 relevant
halves needed a `--resample`; a handful of persistent misreads
(mostly outside this issue's own 24 target pages) were resolved by
inference from the adjacent, successfully-read half -- each one
confirmed correct once actually opened, not assumed.

**All 24 pages hand-verified against the real scan, per RG's explicit
preference for full scan reads over a cheaper triage.** Result: 8
pages confirmed fully benign (content correct, conflict was pure
weekday-vs-month-name formatting for the same real day); 16 pages had
at least one genuine content error -- same mislabeling family as
every other finding in this issue (a theater's row landing under the
wrong day-number), just surfaced here as a cross-theater inconsistency
instead of a same-half collision, because it never produced a
same-theater cross-half collision for `dedup_split_overlap.py` to
catch. One case (`1891-92_pair004`, `Большой`/`Малый` day 28) wasn't a
mislabel at all -- both were extracted as blank/no-content when the
scan clearly shows real performances for both.

**Applied 21 session-level corrections directly to
`outputs/repertoire_spreadfix_v6/parse_raw/*.raw.json`** across the 16
confirmed-wrong pages, each asserting the expected prior value before
overwriting (same safety discipline as the dedup queue fixes). True
replacement content was scan-confirmed for every fix -- either an
exact match found elsewhere already in the data, or read directly off
the scan when no existing session held it.

**Two of my own mistakes caught by re-running the checks afterward,
not assumed clean**:
1. One fix (`1897-98_pair022`, `Михайловскій` day 21) set `is_dark:
   true` but left a stale `annotation` field from the row's old
   (wrong) content -- created a fresh, self-inflicted
   `dark_row_with_content` flag. Caught immediately by re-running
   `quality_checks.py` rather than trusting the edit blind.
2. Chasing that fix down further surfaced a SECOND, pre-existing
   mislabel independent of anything this addendum was originally
   about: the real day-21 content (a Dumas-monument benefit
   performance) was already present in the data, just mislabeled as
   day 22 -- confirmed by direct re-inspection of the scan crop (the
   entry's receipts figure spans across the physical fold in the
   photograph, which is what caused my own first reading of it to
   misattribute the row). Relabeled it to its correct day rather than
   leaving a redundant near-duplicate standing.
3. Also caught: an earlier `duplicate_event_key` fix made directly to
   the dedup queue CSV had never actually been propagated into
   `parse_raw` (the queue was edited, but `apply_split_overlap_
   resolutions.py` was never re-run afterward, and by the time this
   was noticed, re-running it would have discarded today's direct
   cross-theater-check fixes). Applied the same correction directly
   to `parse_raw` instead.

**Final state, re-verified**: `parse_and_validate.py` runs clean, 0
validation errors, exactly 3,904 sessions preserved (matching the
pre-fix count precisely -- no session lost or duplicated across 21
edits). `quality_checks.py`: `dark_row_with_content` back to 56 (the
self-inflicted flag cleared), `duplicate_event_key` down to 4 (all 4
confirmed legitimate `kept_half=both` cases, re-verified). The
`cross_theater_date_mismatch` raw COUNT is unchanged (38) and
expected to stay that way -- the check flags day-NUMBER coverage
patterns per theater, which none of today's fixes were about (they
corrected which CONTENT sits at an already-existing day-number, not
which day-numbers a theater's reconciliation covers) -- the count
being unchanged is the correct outcome, not a sign anything went
unfixed.

**Not yet done**: `receipts_parse_failed`'s ~10 "other" cases (2
already identified as genuine content-misplacement, not yet fixed);
`build_duckdb.py`, the actual last step to a queryable database, still
not run.

### Addendum to #70 (2026-09-17): fixed a real parsing bug behind 6 of
the 10 `receipts_parse_failed` "other" cases, caught and corrected a
regression in the fix itself before it touched any output

Categorized all 60 `receipts_parse_failed` flags before touching
anything: 42 are the already-known Latin p/k substitution (model
writes Latin "p"/"k" instead of Cyrillic "р"/"к" -- unrelated,
untouched here), 8 are genuinely truncated ("р. 47 к." with no
leading number at all -- a crop/divider issue, also untouched), and
10 were unexplained "other" cases needing individual review. 2 of
those 10 (`'1-я к. 3-го д. бал.'`, `'2676'`) already overlap
`malformed_receipts_missing_unit`.

**Root cause of 6 of the remaining 8**: `pipeline/schemas/
repertoire.py`'s `_parse_receipts` used a literal `text.split("р.")`
-- requires the period immediately after "р" to match at all. Six
otherwise perfectly legible receipts figures (`'2943 р 70'`, `'2901
р'`, `'471 р 40 к.'`, `'917 р 84 к.'`, `'1272 р'`, `'1074 р'`) have the
model dropping just that one trailing period, which silently fails
the whole split (caught by the `except`, returns `("", "")` -- rubles
AND kopecks both lost) even though the figure itself needs no
judgment call to read correctly. This is a parsing gap, not a data
problem -- fixed in the flatten function itself rather than by
touching any raw session, and it's corpus-wide (`flatten_repertoire_
page` is shared by every Repertoire season, not just the 8
two-page-spread ones), so any other season with the same dropped-
period pattern benefits too, not just this issue's own scope.

Fix: replaced the literal split with `_RUBLES_MARKER_RE =
re.compile(r"р\.?")` (period now optional) and `.split(maxsplit=1)`.
Confirmed first that no session's `receipts_text` in this corpus
contains more than one "р" occurrence, so `maxsplit=1` can't silently
mis-split a multi-marker string that the old code would have failed
loudly on instead.

**Caught a real regression in my own fix before it reached any
output**: re-running `quality_checks.py` after this first version
dropped `receipts_parse_failed` from 60 to 52, not the expected 54.
The extra 2 "fixes" were wrong -- a bare `р\.?` matches the letter
"р" *anywhere*, including embedded inside an ordinary Cyrillic word,
which is exactly what the other 2 "other" cases are: `'3-я карт.'`
and `'Золотая свадьба. Я играю болѣе 25 лѣтъ'` both contain "р" as
part of an ordinary word (карт, играю), not as a rubles marker. The
first version of the fix silently reinterpreted the text after that
embedded "р" as a kopecks figure (e.g. `'3-я карт.'` -> rubles=`'3-я
ка'`, kopecks=`'т.'`) instead of correctly failing to parse -- these
2 sessions are known content-misplacement bugs (something other than
a receipts figure ended up in the `receipts_text` field), not
receipts figures with a missing period, and silently fabricating a
rubles/kopecks split out of them would have been worse than the
original silent-failure bug.

Fixed by requiring a word boundary: `r"\bр\.?"`. Python's `re` treats
Cyrillic letters as `\w` by default, so `\b` correctly requires "р"
to stand alone as a token rather than merely occur inside a longer
word. Verified against all 13 relevant cases (the 6 target fixes, the
4 genuine other-category cases including the 2 that caused the
regression, plus the dash convention and blank/empty) before
re-running the pipeline.

**Final verified state**: `parse_and_validate.py` -- 0 validation
errors, exactly 3,904 events / 5,190 performances (unchanged).
`quality_checks.py`: `receipts_parse_failed` 60 -> 54 (exactly the 6
targeted cases resolved, confirmed by diffing the flag list, not just
the count); `malformed_receipts_missing_unit` unchanged at 2 (the 2
overlap cases, correctly still flagged); no new flags introduced
anywhere else.

**Still open**: 4 genuine content-misplacement candidates need the
same scan-verification treatment used for the 24 cross-theater-
mismatch pages before this residual can be closed: `'1-я к. 3-го д.
бал.'` and `'3-я карт.'` (both `1892-93_pair008`, Маріинскій), `'2676'`
(`1892-93_pair020`, Маріинскій), `'Золотая свадьба. Я играю болѣе 25
лѣтъ'` (`1895-96_pair010`). The 8 `1894-95_pair008` truncated
cases (`'р. 47 к.'` etc., missing the leading rubles number entirely)
are the already-documented crop/divider truncation pattern, not this
bug.

### Addendum to #70 (2026-09-17): scan-verified all 4 remaining
`receipts_parse_failed`/`malformed_receipts_missing_unit` "other" cases
-- closes the receipts residual, surfaced two more 3-date cascading
mislabels along the way

All 4 required locating the real source page first, since none of
their `_source` render-page labels could be trusted at face value --
confirmed directly, not assumed, that these labels are inconsistent
across files: sometimes the literal render-sequential page id
(`repertoire_1895-96_p010` really is render page p010), sometimes the
*printed* page number reused as if it were a page id (`repertoire_
1892-93_p021` in one session's `_source` does not exist as a render
page at all -- 1892-93 only renders to `p011` -- it's printed page 21,
which is actually `p009__bottom`). Caught this by simply trying the
literal id first and getting a page whose printed dates didn't match
the session's own `date_text` at all (Feb 1893 content under a
label claiming Oct/Nov 1892) -- a concrete confirmation of the same
render-vs-printed-page-number pitfall this issue's 2026-09-17 cross-
theater-mismatch addendum already flagged, now hit from the opposite
direction. `docs/repertoire_column_bounds.json`/`split_page_numbers_
final.csv` (printed page -> render half) was the reliable way through
it each time.

**1. `1892-93_pair008__s011`** (25 Октября., Маріинскій, `'3-я карт.'`):
printed page 8. The scan shows TWO works on this row -- `Пахита, бал.`
and `3-я карт. бал. Зорайя.` (a 3rd-scene excerpt) -- with the real
figure `1601 р. 20 к.` printed below both. The model captured only the
first work (and with the wrong genre, `оп.` instead of `бал.`), and
the second work's `3-я карт.` prefix ended up alone in `receipts_text`
while the real figure was dropped entirely. Fixed: `works` now holds
both (second work's title carries its own `N-я карт.` prefix, genre
`None` -- matching the established convention for this exact pattern,
e.g. `repertoire_1897-98_pair018`'s `'2-я карт. 3-го д. бал. Синяя
борода'`), `receipts_text` = `'1601 р. 20 к.'`.

**2. `1892-93_pair008__s002`** (1 Ноября., Маріинскій, `'1-я к. 3-го д.
бал.'`): same page, same failure shape -- `Калькабрино, бал.` (model
had it as `Калькабри`, missing genre) + `1-я к. 3-го д. бал. Дочь
фараопа.` (verbatim as printed -- the source itself prints "фараопа",
not "фараона"; not corrected, per the never-modernize/never-guess
rule), figure `2569 р. 70 к.` Same fix shape as #1.

**3. `1892-93_pair020__s003`** (1 Четв., Маріинскій, `'2676'`): printed
page 21 (`p009__bottom`). This one wasn't just a truncated figure --
tracing it surfaced a **3-date cascading row shift**, the same failure
family as this issue's very first findings (a session's content
lands one date/theater slot too early or late), just not caught by
`cross_theater_date_mismatch` because it only affected one theater's
own column, not a cross-theater date-sequence disagreement:
- `30 Вторникъ.`/Маріинскій held `31 Среда.`'s real content
  (`annotation: "Гугеноты, оп."`) instead of its own (a blank concert-
  repeat announcement).
- `31 Среда.`/Маріинскій held `1 Четв.` утро's real content
  (`Щелкунчикъ, бал.` + a garbled `"3-я карт. бал. Зорька"` annotation,
  correct spelling `Зорайя`) instead of its own (`Гугеноты, оп.`,
  `2395 р. 70 к.`).
- `1 Четв.` утро's session was **missing from the data entirely** --
  its content was the one sitting one slot early on `31 Среда.`
  Recovered and re-inserted as its own session (`Щелкунчикъ` +
  `3-я карт. бал. Зорайя.`, `1208 р. 50 к.`, `session: "morning"`).
- The surviving `1 Четв.` session (`Демонъ, оп.`) was correct in
  content but truncated (`'2676'` -> `'2676 р. 7 к.'`) and mislabeled
  `session: "unspecified"` instead of `"evening"`.

All three real dates' content (30th, 31st, 1st) confirmed against the
scan and reassigned to their correct dates; net effect is one
previously fully-lost session recovered, not just a receipts fix.

**4. `1895-96_pair010__s051`** (`'Золотая свадьба. Я играю болѣе 25
лѣтъ'`, tagged theater `Большой`): the deepest of the four. The
session's own date_text (`"26 Воскресенье."`) didn't match ANY March
calendar page in this season (day 26 falls on a Tuesday in March
1896, not Sunday) -- the printed-page-number lookup (`p010` literal
-> printed page 22, wrong) also didn't contain it. Correctly located
via the content itself: `"Безплатный спектакль для гг.
георгіевскихъ кавалеровъ"` (free performance for Knights of the Order
of St. George) is a specific, dateable imperial commemoration --
November 26 (O.S.), the Order's feast day -- which pointed to printed
page 10 (`p004__top`, confirmed: this page's own "26 ноября" row
carries exactly that text). A second cascading mislabel on the same
row: Малый's `26 ноября` утро session (`Евгеній Онѣгинъ, оп.`, `939 р.
42 к.`) had been mis-dated to `"25 Суббота."` evening, with the title
truncated to `"Геній Онѣгинъ"` and receipts cut to `'939 р. 4'`. Fixed
both the date/session and the truncated fields. Малый's `26 ноября`
вечер session was also incomplete -- `Золото, ком.` only, missing its
actual second work `Я играю большую роль!, ш.` (misplaced into
`annotation` as a garbled fragment); added it. Its receipts figure
(`'1360 р.'`) is left as-is -- the kopecks are genuinely illegible in
the scan, sitting right in the page-curvature/binding shadow at the
fold, the class of unreadability RG confirmed exists earlier this
session (not the same thing as a parsing gap). Finally, the `Большой`
session that originally carried this issue's flag turned out to be
**pure hallucination**: the scan shows `Большой` genuinely blank
(dark) for `26 ноября` -- its "receipts_text" was two fragments of
Малый's own two work titles stitched together (`Золот[о]` +
`Я играю бол[ьшую роль]`) into text that reads like a plausible
25th-anniversary benefit announcement but was never printed anywhere.
Corrected to `is_dark: true`, `receipts_text: null`, matching what the
page actually shows.

**Applied via the same assert-prior-value-before-overwrite discipline
as every other fix in this issue.** Final re-verified state: `parse_
and_validate.py` -- 0 validation errors, `event_entry` 3,904 -> 3,905
(the one recovered session), `event_entry_performance` 5,190 -> 5,195
(5 new work rows across the fixes). `quality_checks.py`:
`receipts_parse_failed` 60 -> 50 (down to exactly the 42 already-known
Latin p/k substitution + 8 already-known `1894-95_pair008` truncation
cases, zero "other" residual left); `malformed_receipts_missing_unit`
2 -> 0; `duplicate_event_key` unchanged at 4 (the new session didn't
collide with anything); `cross_theater_date_mismatch` unchanged at 38
(expected, same reasoning as the earlier addendum -- these fixes
corrected which day-number a theater's content belongs to within an
already-flagged date range, not the range itself, for the 2 pages
that overlap this issue's own 38).

**This closes the receipts residual.** `build_duckdb.py` is now the
only remaining step to a queryable database.

### Addendum to #70 (2026-09-17): closed the parse_raw/resolved_sessions
propagation gap flagged above

All 28 direct session-level content fixes applied today across 16
pages (both this addendum's 7 and the earlier cross-theater-mismatch
addendum's 21) had gone straight into `outputs/repertoire_spreadfix_
v6/parse_raw/*.raw.json` and never back into `resolved_sessions/`'s
`trusted` lists, which `parse_raw/` was originally derived from.
Confirmed the exposure directly rather than assuming it: diffed every
one of the 83 `parse_raw` files against its `resolved_sessions`
counterpart's `trusted` list. Found exactly 16 files differing (15 by
same-index value changes, plus `1892-93_pair020`'s one length
mismatch -- the recovered `1 Четв.` утро session, confirmed via
`difflib.SequenceMatcher` to be a clean single insertion, nothing
else misaligned) -- 28 differing sessions total, matching the fix
count exactly. Since `resolved_sessions/` was never touched by any of
today's edits, every diff is, by construction, exactly one of today's
corrections with no other explanation -- propagated by setting each
differing file's `trusted` = the corresponding `parse_raw` sessions
list wholesale. Re-diffed all 83 files afterward: 0 remaining
differences.

**This does not fully close the exposure on its own** -- `resolved_
sessions/` is itself regenerated from scratch by `apply_split_
overlap_resolutions.py` (reads `raw_columnwise/` + the queue CSV), and
that script has no way to know about a content fix that was never a
top/bottom collision (the overwhelming majority of today's 28 --
these are single-half misreads the model made, not disagreements
between two halves). A future re-run of that script, for an unrelated
reason (e.g. a new queue resolution), would still silently regenerate
`resolved_sessions/` from the ORIGINAL uncorrected raw extraction and
discard today's work, propagation into `trusted` notwithstanding.

Closed that too: added a `--force`-gated overwrite guard to `pipeline/
apply_split_overlap_resolutions.py` (plus a module-docstring warning
naming the exact exposure). By default, if an output file's on-disk
`trusted` list would change from what a run recomputes, that file is
now left untouched and reported by name at the end of the run instead
of silently overwritten -- verified in isolation (not via a full
pipeline re-run, since reconstructing today's exact original
`--page-numbers` CLI input wasn't attempted here) that the guard
correctly detects a reverted-to-wrong `trusted` list and leaves the
file byte-identical on disk. `--force` remains available for an
intentional regeneration, with the docstring pointing back to this
addendum for what would need re-applying afterward.

### Addendum to #70 (2026-09-17): the 6 `single_leaf` pages were entirely
missing from `outputs/repertoire_spreadfix_v6` -- found before build,
recovered, all scan-verified

Pre-build readiness check (RG: "are you sure we're ready?") found that
the 6 `single_leaf` pages within these 8 seasons -- ordinary landscape
leaves with no binding fold, identified by `flag_fold_damage.classify_
page` (`repertoire_1890-91_p000`, `_p012`; `1894-95_p008`; `1895-96_
p012`; `1896-97_p012`; `1897-98_p012`) -- were never carried into
`manifest.csv`/`parse_raw/` at all. Confirmed against `outputs/full_
run`: all 6 already have data there (239 events total, old extraction
method) -- not data that never existed, just missing from this specific
build. Queries logged in `docs/query_log.md`.

**First real problem: render-page drift.** 5 of the 6 already had
column-wise `raw_columnwise/*.raw.json` extractions sitting around from
2026-09-16. Re-verifying one against a freshly re-rendered image (`/tmp`
had been swept again) found the SAME render-sequential page id
(`repertoire_1894-95_p008`) now pointed at a completely different
physical page than the 09-16 extraction had captured -- April 28-May 7,
1895 (confirmed against the scan) vs. the stored extraction's January
dates. `render_pages.py`'s page-to-content mapping is evidently not
stable run-to-run even with nominally the same inputs, on top of the
already-known render-sequential-vs-printed-page-number distinction
(this issue's earlier addenda). Treated today's fresh, single-batch
render as authoritative (verified all 13 files in the 1890-91 season
render came from one uninterrupted run, timestamps ~1s apart) and
copied the needed images to `outputs/repertoire_spreadfix_v6/single_
leaf_images/` -- durable, not `/tmp` -- before doing anything else with
them. All 5 stale extractions were discarded and re-run fresh (plus the
6th, `1890-91_p000`, extracted for the first time) against these
verified-correct images.

**Second problem: per-theater merge failures, most with real content at
stake.** The column-wise merge (`merge_columnwise_page`) refuses to
align a theater's column against the shared date column when their
row counts disagree ("cannot localise") -- appropriately cautious, but
it means the THEATER IS DROPPED FROM THE OUTPUT ENTIRELY rather than
partially included. Every one of the 6 pages had at least one such
failure; `1890-91_p012` had four of five theaters fail. A shallow
total-session-count check (comparing to `full_run`) looked reassuring
at first and was wrong to trust -- it doesn't distinguish "the failed
theater is wholesale blank, so any row-count mismatch is harmless" from
"the failed theater has real content that's now silently missing,"
which turned out to be the majority of the 14 theater/page failures.

**Resolution, page by page, all against the scan (RG's standing
preference for full reads over triage):**
- Where a date column had a spurious extra entry (rotated page-header
  text bled into the date column as its own row, or a real row got
  spuriously split into a phantom morning/evening pair) but every
  "failed" theater was genuinely blank throughout (confirmed against
  the scan) -- rebuilt with one dark session per REAL date, dropping
  the spurious slot. `1890-91_p000`, `1890-91_p012`.
- Where the raw column extraction itself was too unreliable to
  realign confidently -- `1894-95_p008` had Большой's column-read
  literally contain Малый's own work titles for one row (a genuine
  column-boundary misattribution, not just a count mismatch);
  `1895-96_p012`'s Большой/Малый reads were full of OCR fragments of
  a "free admission" notice mis-parsed as work titles -- re-
  transcribed both pages' full grids directly from the scan rather
  than trying to patch the extraction.
- Where the extraction was basically sound but had truncated the
  leading word(s) of many titles (the same crop/divider truncation
  family already documented for receipts_text elsewhere in this
  issue, here hitting work_title instead) -- `1896-97_p012`,
  `1897-98_p012` -- recovered full titles against the scan; for
  `1897-98_p012` this was done for ALL 5 theaters (not just the one
  flagged theater), since spot-checking the "OK" theaters turned up
  the same truncation pattern in titles the merge had accepted
  without complaint (a successful merge is not proof of correctness).
- Two additional genuine completeness recoveries along the way: a
  session on `1897-98_p012` whose receipts/second work were legible
  only as a partial line right at the physical page edge (left as
  incomplete rather than guessed, matching RG's confirmed page-
  curvature/binding illegibility class); a charity/benefit notice
  ("Въ пользу пострадавшихъ отъ недорода хлѣбовъ" -- famine relief)
  correctly captured as an annotation alongside its real work title on
  two rows across two theaters, instead of being lost or misparsed.

**Final verified state**: 4,161 events / 5,342 performances (up from
3,905 / 5,195 before this addendum -- +256 events across the 6 pages,
matching the rebuilt session counts exactly), 0 validation errors,
**zero new quality-check flags** on any of the 6 pages (152 flags
total, unchanged from before -- confirmed by filtering `quality_flags.
csv` to just these 6 `page_id`s). Where comparable, every page's event
count now meets or exceeds `full_run`'s old count for that same page
(`1890-91_p012`: 14 -> 30, more than doubled; the rest flat or +1).
`manifest.csv` now has 89 rows (83 "pair" pages + these 6).

`outputs/repertoire_spreadfix_v6/single_leaf_images/` and `single_leaf_
raw/` are kept alongside `parse_raw/` as the durable record of this
recovery (mirroring the "keep the raw `*.raw.json` responses" rule for
the rest of this pipeline).

### Addendum to #70 (2026-09-17): `build_duckdb.py` run -- closes this issue

`outputs/repertoire_spreadfix_v6/imperial_theaters.duckdb` built against
the 89-page manifest (83 split pairs + 6 single_leaf) and verified
directly against the database, not just the build log: `raw.event_entry`
4,161 rows, `raw.event_entry_performance` 5,342 rows, 89 distinct
`page_id`s, all 8 seasons (1890-91 through 1897-98) represented.
`analysis.event_entry` built with 0 `not_captured` completeness gaps.
Query logged in `docs/query_log.md`.

This is a scratch build only -- `outputs/repertoire_spreadfix_v6`, not
`outputs/full_run` -- matching the 2026-09-15 season-typo-fix precedent.
Promoting it into production, and running the entity-resolution stages
(`build_entities.py`, `link_wikidata.py`, `build_research_model.py`,
etc.) against it, are both separate decisions not yet made.

**This closes issue #70.** Everything from the original fold-split-
extraction plan through dedup, both quality-check triage passes (cross-
theater-mismatch and receipts residual), the parse_raw/resolved_sessions
propagation guard, and the single_leaf page recovery is done and
verified. What's left is promotion/entity-resolution, which is new,
separate work whenever RG decides to take it up -- not a continuation
of this issue.

### Addendum to #70 (2026-09-17): post-build spot check found 8 more
duplicate sessions `duplicate_event_key` can't see -- fixed, and closed
the gap in the check itself

Spot-checking two pages against the built database after `build_duckdb.py`
(one already-fixed single_leaf page, one "pair" page never individually
scan-verified anywhere in this whole issue) turned up a real duplicate on
the untouched page: `1893-94_pair006`, `14 Четвергъ.`/`Большой` had THREE
sessions where two real ones (morning + evening) were expected -- the
third was `Снѣгурочка, оп. -- 1941 р. 47 к.`, byte-identical to the
`evening` session, but labeled `session="unspecified"`.

**Root cause**: `duplicate_event_key` (`check_repertoire`) keys on
`(date_text, theater, time_of_day)` literally. `dedup_split_overlap.
keyed_sessions` uses the same shape of key to detect top/bottom
collisions. When the SAME real printed row got captured independently
by two different reads (one half's passthrough, one half's passthrough
or a dedup-queue resolution) that happened to disagree on the `session`
label (`"evening"` vs `"unspecified"`, or `"morning"` vs
`"unspecified"`), neither mechanism ever saw them as the same key --
the collision-detector let both through as if they were about different
sessions, and the duplicate-key checker never compared them either.
Both guarantees this pipeline is built around ("never lose text", "never
make up text") stayed intact -- nothing was fabricated -- but a real
event got double-counted, which would inflate any receipts sum or event
count run against it.

**Scoped the whole corpus, not just the one page found by chance**:
grepped every page in `outputs/repertoire_spreadfix_v6/parse_raw/` for
sessions sharing `(date_text, theater)` with byte-identical `works`
(every title AND genre) and `receipts_text` -- found **8 such pairs
across 6 pages** (`1891-92_pair008` x2, `1891-92_pair012`,
`1893-94_pair006`, `1895-96_pair004` x2, `1895-96_pair006`,
`1897-98_pair010`), none previously flagged. Because the shared content
had to match in full (not just date+theater), false positives from two
genuinely different performances coinciding are effectively ruled out --
two different real programs essentially never share an identical
receipts figure by chance too.

**Fixed all 8** by dropping the redundant session, keeping the other
(assert-prior-value discipline, matching every other fix in this issue).
7 of 8 followed one clean pattern: a specific `morning`/`evening` session
vs. a duplicate `unspecified` one -- kept the specific label, dropped the
`unspecified` copy. The 8th (`1891-92_pair008`, `9 Суббота.`/
`Михайловскій.`, `Madame Agnès`/`De 1 h. à 3 h.`) had two SPECIFIC but
different labels (`morning` vs `evening`) both sourced from the same
single half's own raw read -- couldn't locate the source scan to confirm
which is correct (yet another instance of this issue's now-familiar
render-vs-printed-page-number problem), but `receipts_text` was `None`
on both, so no figure is at stake in the choice, only which label
survives; kept the first-listed (`evening`) and documented the
uncertainty rather than guessing at a scan location.

**Propagated to `resolved_sessions/`** the same way every other direct
`parse_raw` fix in this issue has been (verified 0 diffs across the 6
affected files afterward).

**Added `check_repertoire_duplicate_content_across_sessions`**
(`pipeline/quality_checks.py`) so this class of duplicate is caught
automatically going forward instead of relying on a spot check to find
it again by chance -- flags any two sessions sharing `(date_text,
theater)` with fully-identical `works` + `receipts_text`, regardless of
`session` label. Unit-verified against the exact `Снѣгурочка` shape
before trusting it against the real corpus (found it correctly on
synthetic data; found 0 on the corpus, which is right, since all 8 real
instances were already fixed by the time it ran for real).

**Final re-verified state**: `parse_and_validate.py` -- 0 validation
errors, `event_entry` 4,161 -> 4,153 (-8, exactly the removed sessions),
`event_entry_performance` 5,342 -> 5,330 (-12, matching the removed
sessions' own work counts). `quality_checks.py`: 152 flags, same total
and same per-category breakdown as before this addendum (the new check
correctly contributes 0, and none of the existing categories were
touched by removing pure duplicates) -- `duplicate_event_key` unchanged
at 4 (confirming these 8 were never counted there, exactly the gap this
addendum closes). `build_duckdb.py` re-run and re-verified directly
against the database: 4,153/5,330 rows, and the specific `1893-94_
pair006` case spot-checked down to 2 sessions (not 3) for that date/
theater. Query logged in `docs/query_log.md`.

### Addendum to #70 (2026-09-17): full `genre` field audit, 22 fixes

RG asked for a field-by-field audit of `event_entry_performance.genre`
(same style as the earlier people-entities field passes). Pulled all 99
distinct values across 5,330 rows and classified every one:

- **Legitimate variety, no action** -- the long tail of rare values is
  mostly genuine 19th-c. theatrical genre vocabulary (`истор. карт.`,
  `пров.`/French `prov.`, `феерія`, `лир. сказка`, `Ор.` as a shorter
  German `Oper.`, etc.) -- confirmed by context, not just assumed
  correct because it looked plausible.
- **22 rows needed fixing**, in four confidence tiers, all applied:
  1. **7 confirmed via a clean duplicate elsewhere in this corpus** --
     e.g. `genre='в.'` on `Бѣда отъ нѣжнаго сердца` fixed to `вод.`
     because that exact title appears with `вод.` cleanly 14 other
     times on this page's neighbors.
  2. **4 fixed by the same crop-truncation pattern** already exhaustively
     documented in this issue for `receipts_text`/`work_title`, now
     confirmed hitting `genre` too (`'к'`/`'ко'`/`'към.'`/`'ом.'` etc. as
     truncated `ком.`) -- applied to well-known/plausible real titles
     with no internal duplicate to confirm against, but an unambiguous
     truncation shape.
  3. **2 fixed by matching a title already scan-verified earlier THIS
     SESSION on a different page** (`Секретное предписаніе`/`карт.`,
     `Голь на выдумки хитра`/`вод.` -- both recovered from genuine
     scan reads during the earlier single_leaf and receipts-residual
     work, recurring here in truncated form again).
  4. **3 inferred with documented uncertainty** -- could not locate the
     correct scan page for these (the render-vs-printed-page-number
     problem this issue keeps running into) but had partial internal
     evidence: `Осеній вечеръ въ деревнѣ`/`Госпожа-служанка` inferred
     to `вод.` from the general `в`/`во` truncation family; `Земной`
     inferred to the fuller title `Рай земной` + `genre=ком.` from a
     single partial corpus match. Flagged here explicitly as the
     least-certain of the 22 -- worth a scan check if the right page is
     ever located.
- **2 genuine parsing bugs, not truncation** -- content that was never a
  genre at all had landed in the genre field:
  - `genre='Зорай'` on `'2-я и 3-я карт. бал.'` -- merged into one
    title, `'2-я и 3-я карт. бал. Зорайя'`, `genre=None`, matching this
    corpus's own established convention for such excerpt-prefixed
    titles (already used repeatedly this issue, e.g. `'2-е д. бал.
    Фіаметта'`).
  - `genre='2-е д. ком.'` on `'Безъ вины виноватые'` -- same fix shape:
    merged to `'2-е д. ком. Безъ вины виноватые'`, `genre=None` (a
    benefit bill performing just Act 2 of this comedy, the `2-е д.`
    excerpt marker had been split into the genre field instead of
    folded into the title).
  - One **structural split**: `'Амура, лир. ск.'` / `genre='вертиссементъ'`
    was actually two merged, truncated real works -- split into
    `'Месть Амура'` (`genre='лир. ск.'`, matching a clean duplicate of
    this exact title elsewhere) + `'Дивертиссементъ'` (`genre=None`,
    matching the standalone-Divertissement pattern seen elsewhere on
    the same page's neighboring rows).
  - Plus 2 rows of trivial whitespace normalization (`' Lustsp.'` ->
    `'Lustsp.'`).

Propagated to `resolved_sessions/` for all 18 affected "pair" files
(0 diffs remaining, per the established discipline -- the single_leaf
pages have no `resolved_sessions` counterpart, correctly skipped).
Re-verified: 0 validation errors, `event_entry` unchanged at 4,153,
`event_entry_performance` 5,330 -> 5,331 (+1, the structural split),
`quality_flags.csv` unchanged (152 flags, genre-only edits don't touch
any tracked check). `build_duckdb.py` re-run and re-verified directly:
the fixed titles/genres confirmed present, no stray truncated values
remain.

### Addendum to #70 (2026-09-17): blank-`genre` audit -- 24 more fixes,
plus a whole-page duplicate found and removed

RG asked specifically whether blank (`NULL`) `genre` cells are
intentional or accidental drops. 226 of 5,331 performance rows had
`genre=NULL`. Categorized all of them:

- **~206 confirmed legitimate** -- excerpt/act markers where the genre
  (if any) is embedded in the title itself, matching this corpus's own
  established convention (`'2-е д. бал. Фіаметта'`, `'Актъ бал.
  Фіаметта'`, etc.); anthems (`Гимнъ`/`Hymne`, 36 rows -- not a
  categorized genre at all); named-reciter pieces (`Сцена г. Вейнберга`/
  `Сцена г. Горбунова`, 37 rows, consistently genre-less); benefit/
  commemorative announcement titles (`Бенефисъ г. ...`, `Спектакль въ
  память И. А. Крылова`, etc.).
- **24 rows were real, accidental drops** -- the title carried its own
  genre suffix (this corpus's established title-duplicates-genre
  convention, e.g. `'Heimath, Schausp.'`) but the separate `genre` field
  was left null anyway. Found via a suffix-pattern search, then widened
  once to catch multi-word suffixes (`'Myrane, étude dr.'`) and titles
  where the genre word wasn't comma-separated (`'Помолвка въ Галерной
  гаван карт.'`). All 24 fixed by duplicating the title's own suffix
  into `genre` (18 rows), or a small title/genre reconstruction backed
  by a clean corpus duplicate of the same (truncated) title (4 rows:
  `'Заварила кашу—расхлебывафарсъ'` -> title `'Заварила кашу—
  расхлебывай'` + genre `'фарсъ'`; `'Помолвка въ Галерной гаван(ъ)
  карт.'` and a second, differently-truncated occurrence of the same
  title both -> `'Помолвка въ Галерной гавани'` + `'карт.'`; `'нина,
  др. льшую роль!, ш.'` split into two real works, `'Родина, др.'` +
  `'Я играю большую роль!'`/`'ш.'`, both confirmed via 12 and 16 clean
  corpus occurrences respectively).
- **1 row corrected to a dark cell, not a title** -- `'Кубокъ,
  Собачкинъ, Месть Амура, Дивертиссементъ'` (Большой, `1895-96_
  pair010`, `20 Понед.` morning) was a byte-for-byte match (once split)
  to the SAME date's Малый-theater row on the same page (already fixed
  earlier this session) with no receipts figure of its own -- matches
  the already-documented "theater reaches into a blank neighbor's
  content" bleed pattern, not a real second performance. Corrected to
  `is_dark=true`, `works=[]`.

**Investigating one of these (`'Дюующіе спек-'`/`'онца сезона—'`/
`'атные.'`, three garbled fragments of "Всѣ послѣдующіе спектакли до
конца сезона—безплатные" masquerading as separate work titles) turned
up a much bigger problem**: its source traced to `repertoire_1895-96_
p012`, one of the 6 `single_leaf` pages fully rebuilt from the scan
earlier this session (see this issue's single_leaf-recovery addendum).
Checking further, `repertoire_1895-96_pair012` -- a DIFFERENT page_id,
already sitting in `manifest.csv`/`parse_raw/` -- turned out to be a
**complete duplicate**: all 10 of its sessions (same 10 dates, same
theater, Малый only) exactly matched the (date, theater) pairs already
correctly captured, with far better quality, under the single_leaf
page's own id. Every one of those 10 events would have been double-
counted in the database.

**Checked whether this was a wider pattern, not assumed**: 4 more
`pairNNN` ids also cite a single_leaf render page as one of their
`_source`s (`1890-91_pair012`, `1894-95_pair008`, `1896-97_pair012`,
`1897-98_pair012`). Cross-referenced (date, theater) pairs between each
and its single_leaf counterpart: **zero overlap in all 4 cases** --
spot-checked actual titles/dates to confirm they're genuinely different
real content (e.g. December performances vs. the single_leaf page's May
content), not a subtler duplicate. This is the same `_source`-string
ambiguity this issue has hit repeatedly (a label that looks like a
render-sequential page id sometimes isn't one) -- coincidence, not a
second duplicate. Only `repertoire_1895-96_pair012` was real.

**Removed `repertoire_1895-96_pair012`** from `manifest.csv` and
`parse_raw/` (superseded entirely by the higher-quality single_leaf
fix; not deleted from `resolved_sessions/`, kept as the historical
audit record).

**Final re-verified state**: `event_entry` 4,153 -> 4,143 (-10, the
removed duplicate page), `event_entry_performance` 5,331 -> 5,317, 88
distinct pages (was 89), 0 validation errors, `quality_flags.csv`
unchanged (152 flags -- none of this touched a tracked check).
Propagated to `resolved_sessions/` for all 11 affected files.
`build_duckdb.py` re-run and re-verified directly against the database
(0 rows remaining for the removed page_id). Queries logged in
`docs/query_log.md`.
