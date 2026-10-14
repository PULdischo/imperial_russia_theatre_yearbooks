"""1893-94 Moscow ballet receipts were 300 р. under the printed season total (Балетныхъ 43, 43,731 р. 41 к.) with the count
equal. pipeline/season_stats_receipt_candidates.py listed 30 single-digit candidates; on the scan (ForUpload_1893-94_Repertoire.pdf,
spread 4-5, read at 5x) 3 Воскрес. 1893 Большой «Хрустальный башмачекъ, бал.» prints 1431 р. 83 к., stored 1131 р. 83 к.
uv run python docs/eval/fold_log/fix_1893_94_ballet_digit.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs/full_run/raw/repertoire_1893-94_pair004.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][99 - 1]
assert S["receipts_text"] == "1131 р. 83 к." and S["date_text"].startswith("3 ") and "Больш" in S["theater"], S
S["receipts_text"] = "1431 р. 83 к."
S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-14: hundreds digit 4, not 1 (season-stats ballet check)"
print(S["date_text"], S["theater"], [w["work_title"] for w in S["works"]], "-> 1431 р. 83 к.")
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
