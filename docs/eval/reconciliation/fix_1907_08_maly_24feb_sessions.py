"""1907-08, Малый, p. 111 (repertoire_1907-08_p035): 24 Feb 1908 (Sunday) is a divided cell. The scan prints
УТРО «Джентльменъ, ком.» 644 р. 09 к. above ВЕЧЕРЪ «Горе отъ ума, ком.» 844 р. 95 к.; the extraction stored the
labels the other way round (works and receipts paired correctly). Found by the blind column read of 2026-10-28;
checked by Claude on ForUpload_1907-08_Repertoire.pdf p. 111 (index 35). Receipts unaffected. Only the two labels
change; the array order (and so every event_id / entry position) stays as it is.
uv run python docs/eval/reconciliation/fix_1907_08_maly_24feb_sessions.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1907-08_p035.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
A, B = d["sessions"][23], d["sessions"][24]  # 0-based; event_ids repertoire_1907-08_p035__s024 / __s025
for S, title, rec, old in ((A, "Джентльменъ", "644 р. 09 к.", "evening"), (B, "Горе отъ ума", "844 р. 95 к.", "morning")):
    assert S["date_text"] == "24 Воскр." and S["theater"].startswith("Малый"), S
    assert S["receipts_text"] == rec and S["works"][0]["work_title"] == title, S
    assert S["session"] == old, S["session"]
for S, new in ((A, "morning"), (B, "evening")):
    note = f"scan 2026-10-28: session «{S['session']}» -> «{new}» (утро/вечеръ labels swapped in extraction; blind column read)"
    S["session"] = new
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
    print(S["date_text"], S["theater"], S["works"][0]["work_title"], S["session"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
