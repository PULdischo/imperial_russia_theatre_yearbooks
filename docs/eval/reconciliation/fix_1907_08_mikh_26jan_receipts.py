"""1907-08, Михайловскій, p. 104 (repertoire_1907-08_p028): 26 Jan 1908, Andrieu benefit («Le commissaire est bon
enfant» / «Raffles»), stored «2237 р. 50 к.», print «2257 р. 50 к.». The third digit is a damaged sort (flat top bar and
lower bowl, upper-left stem missing); in this typeface «3» has a rounded top and «5» a flat bar (compared with «3598»
and «2300» on the same page). Found by the blind column read of 2026-10-28; checked by Claude at 4x on
ForUpload_1907-08_Repertoire.pdf p. 104 (index 28). Ledger 1907-08.
uv run python docs/eval/reconciliation/fix_1907_08_mikh_26jan_receipts.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1907-08_p028.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][23]  # 0-based; event_id repertoire_1907-08_p028__s024
old, new = "2237 р. 50 к.", "2257 р. 50 к."
assert S["date_text"] == "26 Суббота." and S["theater"].startswith("Михайлов") and S["receipts_text"] == old, S
assert S["annotation"] == "Au bénéfice de M-r Andrieu.", S["annotation"]
S["receipts_text"] = new
note = f"scan 2026-10-28: receipts «{old}» -> «{new}» (damaged 5 read as 3 in extraction; blind column read)"
S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
print(S["date_text"], S["theater"], S["receipts_text"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
