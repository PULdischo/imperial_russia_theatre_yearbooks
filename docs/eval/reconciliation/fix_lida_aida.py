"""«Лида, оп.» is a misread of «Аида, оп.» (in this typeface the capital А has a pointed top and looks like Л). The last
three stored readings, each read on the scan 2026-10-27 (checked by Claude; RG: "check/fix the three remaining «Лида»
readings on the scans"); the fourth, 1893-94, is in fix_1893_94_moscow_works.py. Receipts unchanged.
  1892-93 p. 6, 9 Oct 1892 Большой (1978 р. 43 к.); 1892-93 p. 23, 12 Apr 1893 Большой (979 р. 41 к.);
  1899-00 p. 26, 27 Jan 1900 Маріинскій (2960 р. 85 к.).
uv run python docs/eval/reconciliation/fix_lida_aida.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
NOTE = "scan 2026-10-27: «Лида» -> «Аида» (print «Аида, оп.»)"
FIX = {"repertoire_1892-93_pair006": {35: ("9 ", "Больш", "1978 р. 43 к.")},
       "repertoire_1892-93_pair022": {19: ("12 ", "Больш", "979 р. 41 к.")},
       "repertoire_1899-00_p024": {6: ("27 ", "Маріин", "2960 р. 85 к.")}}
for page, cells in FIX.items():
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, (date, th, rec) in cells.items():
        S = d["sessions"][s - 1]
        assert S["date_text"].startswith(date) and S["theater"].startswith(th) and S["receipts_text"] == rec, (page, s, S)
        assert [(w["work_title"], w.get("genre")) for w in S["works"]] == [("Лида", "оп.")], (page, s, S["works"])
        S["works"][0]["work_title"] = "Аида"
        S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + NOTE
        print(page, s, S["date_text"], S["theater"], "Лида -> Аида")
    if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
