"""«Джентльманъ» -> «Джентльмэнъ» in five Repertoire cells (1898-99, 1899-00, 1902-03). Every cell stored «Джентльманъ» was read on
the full-resolution scans by Claude (docs/eval/scan_audit/spelling_reads_dzhentlmen_2026-10-29.csv): all five print «Джентльмэнъ,
ком.», as do the other 92 performances; э read as а in extraction (the same misread found in the 1897-98 title audit, 12 Jan 1898
Малый). Title only. RG 2026-10-29: "Yes, fix them".
uv run python docs/eval/reconciliation/fix_dzhentlmen_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
WRITE = "--write" in sys.argv
EVENTS = ["repertoire_1898-99_p024__s026", "repertoire_1899-00_p006__s034", "repertoire_1899-00_p019__s010",
          "repertoire_1902-03_p012__s027", "repertoire_1902-03_p012__s033"]
docs, n = {}, 0
for eid in EVENTS:
    page, s = eid.rsplit("__s", 1)
    if page not in docs:
        p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
        for ind in (2, 4, 1, None):
            for ea in (False, True):
                for tr in ("", "\n"):
                    if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
        assert fmt, p
        docs[page] = (p, d, fmt)
    S = docs[page][1]["sessions"][int(s) - 1]
    hits = [w for w in S["works"] if w["work_title"] == "Джентльманъ"]
    assert len(hits) == 1, (eid, S["works"])
    hits[0]["work_title"] = "Джентльмэнъ"; n += 1
    note = "scan 2026-10-29: «Джентльманъ» -> «Джентльмэнъ» (э read as а)"
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
    print(eid, S["date_text"], S["theater"], [w["work_title"] for w in S["works"]])
if WRITE:
    for p, d, fmt in docs.values():
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(n, "cells;", "WROTE" if WRITE else "DRY RUN", RAW)
