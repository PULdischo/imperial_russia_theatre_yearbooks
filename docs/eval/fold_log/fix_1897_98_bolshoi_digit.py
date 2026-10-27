"""1897-98 Moscow: every Большой receipts figure (167 events) read against the scan (ForUpload_1897-98_Repertoire.pdf, all
13 spreads, 2026-10-27) after the fold-log apply left Moscow ballet +2,743.80 and opera +935.91 over the printed totals.
One figure was misread: 28 Пятница (Nov 1897, p. 11) Большой «Рогнѣда, оп.» prints 1880 р. 98 к., stored 1880 р. 38 к.
uv run python docs/eval/fold_log/fix_1897_98_bolshoi_digit.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs/full_run/raw/repertoire_1897-98_pair010.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][98 - 1]
assert S["receipts_text"] == "1880 р. 38 к." and S["date_text"].startswith("28 ") and "Больш" in S["theater"], S
S["receipts_text"] = "1880 р. 98 к."
S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-27: kopecks 98, not 38 (Moscow season-stats check)"
print(S["date_text"], S["theater"], [w["work_title"] for w in S["works"]], "-> 1880 р. 98 к.")
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
