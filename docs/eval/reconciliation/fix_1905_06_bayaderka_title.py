"""1905-06 Repertoire, Маріинскій 4 Sep 1905 evening (p000, idx 6, printed p. 84): stored «Ваядерка», print «Баядерка, бал.»
(a Б with its flag top, read by Claude at 2x on ForUpload_1905-06_Repertoire.pdf, 2026-10-29). Found when the 1903-04
alias «Ваядерка» -> «Баядерка» (a genuine print slip on 25 Jan 1904, ledger 1903-04-17) also caught this cell.

uv run python docs/eval/reconciliation/fix_1905_06_bayaderka_title.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-29 (1903-04 reconciliation, alias check)"

p = RAW / "repertoire_1905-06_p000.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
fmt = next((ind, ea, tr) for ind in (2, 4, 1, None) for ea in (False, True) for tr in ("", "\n")
           if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t)
S = d["sessions"][6]
assert S["date_text"] == "4 Воскрес." and S["session"] == "evening" and S["receipts_text"] == "2857 р. 95 к.", S
assert S["works"] == [{"work_title": "Ваядерка", "genre": "бал."}], S
S["works"][0]["work_title"] = "Баядерка"
S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}: title «Ваядерка» -> «Баядерка» (Б read as В)"
if "--write" in sys.argv:
    p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(S["date_text"], S["works"], "WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
