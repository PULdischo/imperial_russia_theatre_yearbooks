"""1890-91 benefit-heading check (2026-10-27, checked by Claude on ForUpload_1890-91_Repertoire.pdf, p. 14):
11 Вторн. (Dec 1890) Большой prints only «Фенелла, оп.». The stored annotation «Бенефисъ г. Р.» is a truncated copy of
the Малый heading on the same row («Бенефисъ г. Рыбакова.», session 66, kept). Clear it.
uv run python docs/eval/reconciliation/fix_1890_91_bolshoi_benefit_leak.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
page, s = "repertoire_1890-91_pair014", 2
p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt, page
S = d["sessions"][s - 1]
assert S["date_text"] == "11 Вторн." and S["theater"].startswith("Больш"), S
assert S["annotation"] == "Бенефисъ г. Р." and [w["work_title"] for w in S["works"]] == ["Фенелла"], S
assert d["sessions"][65]["annotation"] == "Бенефисъ г. Рыбакова.", d["sessions"][65]
S["annotation"] = None
S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + \
    "scan 2026-10-27: «Бенефисъ г. Р.» leaked from the Малый cell; Большой prints only «Фенелла, оп.» (benefit check)"
print(page, s, S["date_text"], S["theater"], "annotation cleared")
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN")
