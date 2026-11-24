# RGIA Ф. 497 оп. 18 — received дела

How each дело that arrives from the archive gets logged, prepared, summarised
page by page, and added to the **RGIA Reading Room** artifact
(https://claude.ai/artifact/FEzfCSGR2uohoZr9kfeyZ2, private to RG).

## What lives where

| What | Where | Tracked? |
|---|---|---|
| Requested / received status of all 171 дела | `docs/rgia_request_log.csv` (edit only via `pipeline/rgia_request_tracker.py`) | yes |
| Page-by-page summary of each received дело | `docs/rgia/dela/<delo>.jsonl`, one line per PDF page | yes |
| Instructions for the page-summary agents | `docs/rgia/triage_instructions.md` | yes |
| Page images, enhanced copies, thumbnails | `outputs/rgia_dela/<delo>/` | no, rebuilt from the PDF |
| Reading Room page + seed data + thumbnail sheets | `outputs/rgia_reading_room/` | no, rebuilt from the two tracked files |
| RG's own marks (read / key / skip) and notes | the Reading Room's `marks` collection, one doc per дело (`d159`, …) | no: pull with ArtifactData `list marks` |
| Editorial timeline: dated acts and the spans built on them | `docs/rgia/editorial_acts.csv`, `docs/rgia/editorial_spans.csv` (design: `editorial_timeline_design.md`) | yes |
| RG's sorting of each received дело into piles (sorting tray / set-aside shelf) | the Reading Room's `sorting` collection, one doc per дело (`d159`, …); copied into the log's `rg_piles`, `rg_sort_note`, `rg_sort_date` | yes once copied |
| Claude's suggested pile(s) per дело, shown on the tray | `docs/rgia/sorting_suggestions.csv` → the `suggest` field of each `dela` doc | yes |
| RG's own readings of timeline acts (date + note) | the Reading Room's `rg_reads` collection, one doc per act (`A001`, …) | no: pull with ArtifactData `list rg_reads` |
| The PDFs themselves | wherever RG saves them (path in the log's `notes`) | no, too large |

## When a new дело arrives

```
uv run python pipeline/rgia_request_tracker.py received --dela 160 --date YYYY-MM-DD
uv run python pipeline/rgia_request_tracker.py note --dela 160 --text "<n> PDF pages; file at <path>"
uv run python pipeline/rgia_delo_intake.py --pdf <path>.pdf --delo 160 [--enhanced-pdf <path>_enhanced.pdf]
```

Then split the PDF pages across reading agents (~30 pages each) using
`docs/rgia/triage_instructions.md`; each writes
`outputs/rgia_dela/<delo>/triage/partK.jsonl`. Merge and check coverage:

```
uv run python pipeline/rgia_merge_triage.py --dela 160
```

Different agents apply tags and ratings unevenly, so follow with one text-only
consistency pass per дело (`docs/rgia/consistency_rules.md`), which writes
`outputs/rgia_dela/<delo>/consistency_patch.jsonl`, and apply it:

```
uv run python pipeline/rgia_apply_patch.py --dela 160
uv run python pipeline/rgia_reading_room.py
```

Publish `outputs/rgia_reading_room/index.html` (copied from the tracked
`docs/rgia/reading_room.html`) to the same artifact URL with the
new `sprites/<delo>.jpg` added to `files`, then write
`seed/dela/d<delo>.json` and every `seed/pages/d<delo>*.json` into the
artifact's `dela` and `pages` collections with ArtifactData. Changes to the request
log (new batches, received dates) need the `dela` docs rewritten too. Never write
to `marks`: that is RG's.

### Sorting step (after the page summaries)

RG sorts each received дело (via its runs, below) into one or more Keep piles — **Ballet**, **Editorial**, **Sales &
distribution**, **Design & production**, **Manuscripts & drafts** — or **Set aside**. Set-aside дела
leave the register and sit on the **Set-aside shelf** (`#shelf`); nothing is
deleted and the PDFs stay in `pdf/RGIA_F497_Op18/dela/` (RG, 2026-11-24: a
label, not a move). Several Keep piles per дело are allowed.

For each newly triaged дело, add one row to `docs/rgia/sorting_suggestions.csv`
(`delo`, `piles` `;`-joined from `ballet / editorial / manuscripts / sales / design /
set_aside`, `why` = one line from the page counts and summaries), rerun
`rgia_reading_room.py`, and write the дело's `suggest` field with ArtifactData.
**Manuscripts & drafts** (RG 2026-11-24): manuscripts and drafts that made their way
into the printed Yearbook — drafts of lists, season reviews, articles, and source
material supplied for them (e.g. staff lists sent for the Yearbook's lists). Part of
the editorial history, kept as its own pile; suggest it alongside Editorial.
Craftspeople's and designers' дела go to Design & production, not Set aside,
even with no ballet named. The suggestion is only shown; never write to
`sorting`: it is RG's.

To record her decisions in git, pull them and copy them into the log:

```
# ArtifactData list collection=sorting out_dir=<dir>
uv run python pipeline/rgia_request_tracker.py sorting --from <dir>
```

A дело with no `sorting` doc is cleared in the log (she sent it back to the tray).

### Runs: dividing a дело for the tray (RG 2026-11-24)

RG sorts **one дело at a time, run by run**. A run is a stretch of neighbouring
pages dealing with the same business (one correspondence, one ledger, one
manuscript article); RG chose "grouped runs" over one-document-each or the
archive's own divisions. Start a new run at a change of subject,
correspondents, document kind, a large date jump, or an archival divider;
covers, blanks and duplicate exposures join their neighbour or a wrapper run.

1. From the page summaries in `docs/rgia/dela/<delo>.jsonl`, write
   `docs/rgia/runs/<delo>.json` (format in `pipeline/rgia_runs.py`): each run's
   pages, title, dates, suggested piles, one-line why, and `unsure` where the
   boundary or the piles are doubtful. Craftspeople/design → Design & production.
2. `uv run python pipeline/rgia_runs.py --dela <delo>`. **Ballet safety** (RG:
   "careful not to miss ballet-related stuff"): any page tagged ballet, or whose
   summary mentions ballet/dance/the Theatre School, or names a ballet from
   `docs/rgia/ballet_titles.txt`, must sit in a run with the Ballet pile, or
   the script refuses. Each such page is listed on the run's card.
3. Write `outputs/rgia_reading_room/seed/runs/d<delo>.json` to the artifact's
   `runs` collection (ArtifactData `set`, doc `d<delo>`).

RG's run decisions and any split/merge live in the artifact's `run_sorting`
collection (hers; never write there). When every run of a дело is decided the
page writes the дело's own `sorting` doc (union of Keep piles, or Set aside),
which `rgia_request_tracker.py sorting --from` copies into the log as before.
To keep her run decisions in git, pull `run_sorting` with ArtifactData `list`
and an `out_dir`, and copy the files verbatim to `docs/rgia/run_decisions/`.

### Editorial timeline step (after the page summaries)

Every new дело adds to the record of who was doing what in the редакція
(`editorial_timeline_design.md`). Scope: editors, assistant editors, anyone
signing «за редактора», paid editorial staff.

1. Search the new дело's summaries for editorial people and roles (the
   `ed_editors` tag, «редакт», and the names already in `editorial_acts.csv`).
2. Read each candidate on a zoomed crop of the original scan. Add one row per
   dated act to `editorial_acts.csv` with the next `act_id`: person and role
   verbatim, date verbatim and normalised (`YYYY`, `YYYY-MM` or `YYYY-MM-DD`;
   blank if the page gives none), д./л./PDF p., source, and
   `claude_reading` = "checked by Claude" (or "uncertain", with what is
   uncertain in `uncertainty_note`). Leave `rg_read_date`/`rg_note` empty.
   Inferences never go in acts. To an act already in a span, add its id to that
   span's `act_ids` only if it is plainly the same person in the same role.
3. Recompute the spans' arithmetic and list what needs RG:
   ```
   uv run python pipeline/rgia_editorial_timeline.py
   ```
   It updates only earliest/latest act and date. Everything it prints under
   "For RG" (undated acts, acts in no span, brackets the acts contradict, new
   role readings, anything touching an RG ruling) goes to RG one question at a
   time, with evidence, and changes only on her yes.
4. Refresh the Reading Room's Timeline: write
   `outputs/rgia_reading_room/seed/timeline/acts.json` and `spans.json` (the
   script writes them) into the artifact's `timeline` collection (docs `acts`,
   `spans`) with ArtifactData. Before any edit, pull RG's readings with
   ArtifactData `list rg_reads` with an `out_dir` and run the script with
   `--rg-reads <out_dir>` to copy them verbatim into the CSVs. Never write to
   `rg_reads` (or `marks`): they are RG's.
5. End the intake with a short list for RG: the new acts to read, each with its
   дело, л., PDF p. and Reading Room link (`#timeline`).

## Things to know

- The summaries tell RG where to look. They are not transcriptions. Names
  marked "?" are doubtful, and readings get checked against the scan.
- The photos are of a monitor. The enhanced copy (greyscale, moiré softened)
  helps at normal zoom but drops colour (red ruling, blue pencil, inks). Read
  names and numbers from a zoomed crop of the original.
- "Editorial" is split into four sub-tags (contributors, illustrations, print
  runs & finances, editors & office); "editorial" = any of them. Д. 159's
  sub-tags were added afterwards from the summaries (pages checked against the
  image are flagged in outputs/rgia_dela/159/editorial_subtags.jsonl).
- Pages of source material supplied to the редакція for the contents (staff lists,
  committee data) fit none of the four editorial tags; in Д. 163 pp. 9-10, 15, 23-28
  were put back to high by hand after the consistency pass. A fifth tag is the fix.
- `docs/rgia/glossary.json` is the Reading Room's glossary (published with the page
  as `glossary.json`): English glosses shown after Russian terms, plus a Glossary
  panel. Add terms there and republish with `files: {"glossary.json": ...}`.
- Disk: an original runs ~110 MB and its enhanced copy ~150 MB. On 2026-10-09 the
  internal disk had 20 GB free, which is not enough for every дело twice over.
  Make enhanced PDFs only when needed, or keep PDFs on the backup drive.
- **The page's source lives in git: `docs/rgia/reading_room.html`.** Until
  2026-10-27 it existed only as an untracked file in `outputs/`, which fell behind
  the live page (it lacked the Editorial Timeline). `rgia_reading_room.py` now
  copies the tracked file to `outputs/rgia_reading_room/index.html` on every run.
  Make page changes in `docs/rgia/reading_room.html` and commit them; an edit made
  only on the live artifact is lost at the next publish. If the live page ever has
  a change the file lacks, fetch it with Artifact `read` + `path: "index.html"`,
  drop the publish wrapper (the first `<!doctype…><body>` line and the closing
  `</body></html>`), and save it over the file before publishing.
