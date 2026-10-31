"""1900-01 Repertoire: Новый 5 and 6 Feb 1901 (p027, printed p. 29) print «Школьные товарищи, ком.» above «Лучъ, сц.»;
the extraction stored them the other way round. Print order read by Claude on the scan (5 Feb) and by both blind readers
(5 and 6 Feb; docs/eval/scan_audit/1900-01_title_reads.csv n13, n14). RG 2026-10-31: "Yes, reorder". Only the order of the
two works in each event changes.

uv run python docs/eval/reconciliation/fix_1900_01_order.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-31 (1900-01 title audit n13/n14; RG)"
OLD = [("Лучъ", "сц."), ("Школьные товарищи", "ком.")]

p = RAW / "repertoire_1900-01_p027.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
fmt = next((ind, ea, tr) for ind in (2, 4, 1, None) for ea in (False, True) for tr in ("", "\n")
           if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t)
for day in ("5", "6"):
    hits = [S for S in d["sessions"] if S["date_text"].split()[0] == day and S["theater"].startswith("Новый")]
    assert len(hits) == 1, (day, len(hits))
    S = hits[0]
    assert [(w["work_title"], w.get("genre")) for w in S["works"]] == OLD, (day, S["works"])
    S["works"].reverse()
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + \
        f"{TAG}: works reordered to the print («Школьные товарищи» first)"
    print(day, "Feb", [w["work_title"] for w in S["works"]])
if "--write" in sys.argv:
    p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
