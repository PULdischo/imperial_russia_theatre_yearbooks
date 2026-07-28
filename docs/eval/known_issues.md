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

## 13. Completeness reconciliation: `session_status='not_captured'` (implemented)

**Status: implemented, in `analysis.performance_session`.** Renamed
`is_dark` to `session_status` (`performed` / `no_performance`) — "dark
cell" is theater jargon, not intuitive — and added a third,
analysis-layer-only value, `not_captured`, for (date, theater) cells the
page should have but extraction didn't return at all. Full rationale and
the two assumptions it rests on: `docs/schema.md`'s `session_status`
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
  `performance_session` from 89.0% to 99.8%.
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
