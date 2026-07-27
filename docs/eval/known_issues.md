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
