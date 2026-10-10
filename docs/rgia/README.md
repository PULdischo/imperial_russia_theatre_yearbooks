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

Publish `outputs/rgia_reading_room/index.html` to the same artifact URL with the
new `sprites/<delo>.jpg` added to `files`, then write
`seed/dela/d<delo>.json` and every `seed/pages/d<delo>*.json` into the
artifact's `dela` and `pages` collections with ArtifactData. Changes to the request
log (new batches, received dates) need the `dela` docs rewritten too. Never write
to `marks`: that is RG's.

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
- Disk: an original runs ~110 MB and its enhanced copy ~150 MB. On 2026-10-09 the
  internal disk had 20 GB free, which is not enough for every дело twice over.
  Make enhanced PDFs only when needed, or keep PDFs on the backup drive.
