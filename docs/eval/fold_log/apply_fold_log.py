"""Apply RG's physical-volume readings from the Binding Fold Log (claude.ai/artifact/C5n3ckdTBn2JCn1AQCTN9Y) to the raw JSON.
Input: docs/eval/fold_log/readings_<season>.csv, one row per card cell (exported from the log's store, with the event_id each
cell maps to and the receipts stored at export time). A row is applied only where RG's reading differs from the stored figure;
the stored figure is asserted unchanged first. RG's "[?]" (digits hidden by the binding thread) becomes the dataset's "?",
as in «11?7 р. 08 к.», so receipts_total_kopecks stays null for it. WORKS holds whole-cell corrections RG gave in a note.
uv run python docs/eval/fold_log/apply_fold_log.py <season> [--write]"""
import csv, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "outputs" / "full_run" / "raw"
NOTE = "RG, physical volume, Binding Fold Log 2026-10-14"
# event_id -> (works [(title, genre)], receipts). Issue #153: 24 Понед. held a copy of 23 Воскрес.
WORKS = {"repertoire_1893-94_pair016__s046": ([("Жизнь за Царя", "оп.")], "2168 р. 23 к.")}
norm = lambda s: re.sub(r"\s+", " ", (s or "").strip()).rstrip(".")
season = sys.argv[1]; write = "--write" in sys.argv
changes = {}
for r in csv.DictReader(open(Path(__file__).parent / f"readings_{season}.csv", encoding="utf-8")):
    eid = r["event_id"]
    if eid in WORKS:
        changes[eid] = (r["stored"], WORKS[eid][1], WORKS[eid][0]); continue
    new = re.sub(r"\s+", " ", re.sub(r"\?к", "? к", r["reading"].replace("[?]", "?")).strip())
    if not new or norm(new) == norm(r["stored"]): continue
    changes[eid] = (r["stored"], new, None)
by = {}
for eid, ch in changes.items():
    page, s = eid.rsplit("__s", 1); by.setdefault(page, []).append((int(s), eid, ch))
for page, items in sorted(by.items()):
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, eid, (stored, new, works) in sorted(items):
        S = d["sessions"][s - 1]
        assert (S.get("receipts_text") or "") == stored, (eid, S.get("receipts_text"), stored)
        old_w = [w["work_title"] for w in S["works"]]
        S["receipts_text"] = new
        if works: S["works"] = [{"work_title": t_, "genre": g} for t_, g in works]
        S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + NOTE
        print(f"{eid}: {S['date_text']} {S['theater']} {S['session']}  {stored or '(blank)'} -> {new}"
              + (f"   works {old_w} -> {[w['work_title'] for w in S['works']]}" if works else ""))
    if write: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(len(changes), "cells,", len(by), "pages:", "WROTE" if write else "DRY RUN")
