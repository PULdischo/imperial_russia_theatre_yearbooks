"""1893-94, 4 Feb 1894 (p. 18) Маріинскій: the scan prints «Паяцы, оп. / 3-е и 4-е д. оп. Риголетто.» (3535 р. 50 к.); only
«Паяцы» was stored. Found while reading every SP figure against the scan, 2026-10-27 (checked by Claude). The excerpt is
appended after the stored work (no performance id shifts), in the form already stored once elsewhere.
uv run python docs/eval/fold_log/fix_1893_94_paiatsy_rigoletto.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs/full_run/raw/repertoire_1893-94_pair018.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][25 - 1]
assert S["date_text"].startswith("4 ") and S["theater"].startswith("Маріин") and [w["work_title"] for w in S["works"]] == ["Паяцы"], S
S["works"].append({"work_title": "3-е и 4-е д. оп. Риголетто", "genre": None})
S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-27: 2nd work restored"
print(S["date_text"], S["theater"], [w["work_title"] for w in S["works"]])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
