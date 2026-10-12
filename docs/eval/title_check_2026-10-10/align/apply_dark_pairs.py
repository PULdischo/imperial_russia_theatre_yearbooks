"""Collapse a closed-day cell stored as a morning+evening pair of empty sessions into ONE session (issue #151 follow-up 20).

    uv run python docs/eval/title_check_2026-10-10/align/apply_dark_pairs.py            # dry run
    uv run python docs/eval/title_check_2026-10-10/align/apply_dark_pairs.py --write

The cells are the `C_dark` rows of align/triage.csv (regenerated against the current ids by compare_structure.py + triage_structure.py):
the blind structure read printed ONE undivided cell (a dash, or one occasion line with no work) where the data holds two sessions.
  * 53 cells: both sessions are `is_dark`, no works, no figure -> the first becomes the single `unspecified` dark session, the second is deleted.
  * 1 cell (1905-06 p035 Большой 2 Feb): the stored morning is empty and the evening holds the occasion line (a benefit for the families
    of officers fallen in the war, no work printed) -> the evening is kept as the single `unspecified` annotation-only session.
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parents[3] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
NOTE = "closed-day cell stored as a morning+evening pair collapsed to one session (issue #151 follow-up 20)"

cells = defaultdict(list)
for r in csv.DictReader(open(HERE / "triage.csv", encoding="utf-8")):
    if r["class"] != "C_dark":
        continue
    ids = [int(x.split(":")[0][1:]) for x in r["stored_events"].split(",") if x]
    assert len(ids) == 2, r
    cells[r["page_id"]].append(tuple(sorted(ids)))
n_cells = n_del = 0
for page, pairs in sorted(cells.items()):
    path = RAW / f"{page}.raw.json"
    t = path.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    fmt = (ind, ea, tr)
    assert fmt, page
    S = d["sessions"]; dele = set()
    for a, b in pairs:
        x, y = S[a - 1], S[b - 1]
        assert x["date_text"].split()[0] == y["date_text"].split()[0] and x["theater"] == y["theater"], (page, a, b)
        assert not x.get("works") and not y.get("works") and not x.get("receipts_text") and not y.get("receipts_text"), (page, a, b)
        if x.get("is_dark") and y.get("is_dark") and not x.get("annotation") and not y.get("annotation"):
            x["session"] = "unspecified"; x["_fix_note"] = NOTE; dele.add(b)
        else:
            # one empty half and one occasion-line half: keep the half that carries the annotation
            keep, drop = (y, a) if (y.get("annotation") and not x.get("annotation")) else (x, b)
            assert keep.get("annotation") and not S[drop - 1].get("annotation"), (page, a, b)
            keep["session"] = "unspecified"; keep["_fix_note"] = NOTE; dele.add(drop)
        n_cells += 1
    d["sessions"] = [s for i, s in enumerate(S, 1) if i not in dele]
    n_del += len(dele)
    print(f"{page}: {len(pairs)} cell(s), sessions {len(S)} -> {len(d['sessions'])}")
    if WRITE:
        path.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(f"{n_cells} cells collapsed, {n_del} sessions deleted;", "WROTE" if WRITE else "DRY RUN")
