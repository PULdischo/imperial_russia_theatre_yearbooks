"""1894-95, 29 Jan 1895, Маріинскій, «Лебединое озеро / Жертвы Амуру»: hundreds digit misread. Stored «3359 р.»; the scan
prints «3559 р.» (second digit a lightly inked 5, read at 5x on ForUpload_1894-95_Repertoire.pdf p. 10, checked by Claude,
2026-10-27). With it the 17 Маріинскій ballet figures sum to 44,984.11 р., the printed season-totals line (p. 19) exactly;
ledger 1894-95-03. Found on a second blind read of the column (RG: "is it worth doublechecking this again?").
uv run python docs/eval/reconciliation/fix_1894_95_mariinsky_swan_lake.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
NOTE = "scan 2026-10-27: receipts 3359 -> 3559 р. (print «3559 р.»)"
p = RAW / "repertoire_1894-95_pair010.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][16 - 1]
assert S["date_text"] == "29 Воскресенье." and S["theater"].startswith("Маріин") and S["receipts_text"] == "3359 р.", S
assert [w["work_title"] for w in S["works"]] == ["Лебединое озеро", "Жертвы Амуру"], S["works"]
S["receipts_text"] = "3559 р."
S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + NOTE
print(S["date_text"], S["theater"], S["receipts_text"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
