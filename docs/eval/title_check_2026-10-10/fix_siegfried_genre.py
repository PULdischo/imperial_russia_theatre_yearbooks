"""Fill the missing genre of «Зигфридъ» (repertoire_1893-94_pair016 s060, Большой, 27 Четвергъ января 1894, benefit of г. Барцалъ).
Printed «Зигфридъ, оп.»: three blind readers (cells_24-era first reading, cells_35, cells_35b) all read the genre «оп.»; stored genre was null.
uv run python docs/eval/title_check_2026-10-10/fix_siegfried_genre.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs" / "full_run" / "raw" / "repertoire_1893-94_pair016.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][59]
w = [x for x in S["works"] if x["work_title"] == "Зигфридъ"]
assert len(w) == 1 and w[0]["genre"] in (None, ""), S["works"]
w[0]["genre"] = "оп."
print("Зигфридъ ->", w[0])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
