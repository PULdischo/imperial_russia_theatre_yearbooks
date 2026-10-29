"""1897-98, Маріинскій, p. 23 (repertoire_1897-98_pair022): 23 Mar 1898, the visiting German opera troupe's bill
«A basso Porto, Oper.» + «4-ter Akt aus der Oper Die Hugenotten.», 5806 р. 40 к. The act was stored only in the annotation,
and as «1-ter Akt». The print has the same line as on 26 Mar (stored there as a work): the numeral is the damaged 4 of
this typeface (stem plus a faint diagonal, cf. Barnay «3741», 1896-97), read the same on both days
(docs/eval/scan_audit/1897-98_hugenotten_act_23_26mar.jpeg). Found by the 2026-10-29 blind column read; RG 2026-10-29:
"Yes, both" (store the act as a work on 23 Mar; count both bills as German opera). Ledger 1897-98-01.
uv run python docs/eval/reconciliation/fix_1897_98_hugenotten_23mar.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1897-98_pair022.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][22]
assert S["date_text"] == "23 Понедѣльникъ." and S["theater"].startswith("Маріин") and S["receipts_text"] == "5806 р. 40 к.", S
assert S["annotation"] == "1-ter Akt aus der Oper Die Hugenotten.", S["annotation"]
assert S["works"] == [{"work_title": "A basso Porto", "genre": "Oper."}], S["works"]
twin = d["sessions"][88]   # 26 Mar: the same line, stored as a work
assert twin["date_text"] == "26 Четвергъ." and twin["works"][1] == {"work_title": "4-ter Akt aus der Oper Die Hugenotten.", "genre": None}
S["annotation"] = None
S["works"].append({"work_title": "4-ter Akt aus der Oper Die Hugenotten.", "genre": None})
note = ("scan 2026-10-29: «1-ter Akt aus der Oper Die Hugenotten.» moved from annotation to a work and read «4-ter» "
        "(damaged 4, as on 26 Mar; RG: yes)")
S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
print(S["date_text"], S["theater"], S["annotation"], S["works"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
