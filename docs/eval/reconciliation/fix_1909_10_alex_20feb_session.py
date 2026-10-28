"""1909-10, Александринскій, p. 38 (repertoire_1909-10_p037): 20 Feb 1910 (Saturday) «Передъ зарею», 1869 р. 53 к., is one
unsplit cell on the scan, with no «утро» label, but the extraction stored it as session "morning" (the split
утро/вечеръ cell for 21 Feb sits just below it). Found by the blind column read of 2026-10-28; checked by Claude on
ForUpload_1909-10_Repertoire.pdf p. 38. Receipts unaffected.
uv run python docs/eval/reconciliation/fix_1909_10_alex_20feb_session.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1909-10_p037.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][11]  # 0-based; event_id repertoire_1909-10_p037__s012
assert S["date_text"] == "20 Суббота." and S["theater"].startswith("Александрин"), S
assert S["receipts_text"] == "1869 р. 53 к." and S["works"][0]["work_title"] == "Передъ зарею", S
assert S["session"] == "morning", S["session"]
S["session"] = "unspecified"
note = "scan 2026-10-28: session «morning» -> «unspecified» (one unsplit cell, no утро label; blind column read)"
S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
print(S["date_text"], S["theater"], S["session"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
