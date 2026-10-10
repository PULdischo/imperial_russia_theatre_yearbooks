"""repertoire_1897-98_pair020 (printed pp. 20-21): five sessions carried the label «1 Воскресенье.», but the sheet has no such column.
Read blind on the scan (reader_reports/hdr_1897-98_p20.csv): the headers run «27 Пятница.» | «28 Суббота.» | «мартъ.» | «2 П…» [crease] | «3 Вторникъ.»,
and the page margin labels end the left page at «2 марта.»; the binding crease hides the rest of the weekday word. The day is Monday 2 March (old style).
The label is corrected to «2 Понедѣльникъ.» (the weekday word completed from the calendar; what is printed is «2 П…»).
uv run python docs/eval/title_check_2026-10-10/fix_date_label_1897_98_p20.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs" / "full_run" / "raw" / "repertoire_1897-98_pair020.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
n = 0
for i, s in enumerate(d["sessions"], 1):
    if s.get("date_text") == "1 Воскресенье.":
        s["date_text"] = "2 Понедѣльникъ."; n += 1; print("s%d" % i, s["theater"], "->", s["date_text"])
assert n == 5, n
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
