"""1895-96, 26 Воскресенье (Nov 1895, p. 10) Александринскій evening, the free performance for the St George cavaliers:
a 2nd work lies in the binding fold below «Бояринъ Нечай-Ногаевъ, др.». RG, in the Princeton volume (2026-10-27): initial Д,
three words, genre perhaps «вод.»; matched against the company's 1895-96 vaudevilles -> «Дочь русскаго актера, вод.».
Appended after the stored work (no performance id shifts).
uv run python docs/eval/fold_log/fix_1895_96_alex_26nov_work.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs/full_run/raw/repertoire_1895-96_pair010.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][46 - 1]
assert S["date_text"].startswith("26 ") and S["theater"].startswith("Александр") and S["session"] == "evening", S
assert [w["work_title"] for w in S["works"]] == ["Бояринъ Нечай-Ногаевъ"], S["works"]
S["works"].append({"work_title": "Дочь русскаго актера", "genre": "вод."})
S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "RG, physical volume, Binding Fold Log 2026-10-27: 2nd work in the fold"
print(S["date_text"], S["theater"], S["session"], [w["work_title"] for w in S["works"]])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
