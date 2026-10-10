"""Two sessions where a banner line was fused into a work (issue #151 follow-up 3); both cells read by two blind readers
(cells_34.csv, cells_34b.csv, which agree).
  repertoire_1898-99_p029 s020 (Малый, 22 Понед. февраля 1899): printed «Бенефисъ г-жи Никулиной.» | «Ложь, ком.» | «Ноктюрнъ, др. эск.» |
      «Прелестная незнакомка, шут.»; stored the banner as a work whose «genre» was «Ложь», and «др. вск.» for «др. эск.».
  repertoire_1893-94_pair012 s103 (Большой, 21 Вторникъ декабря 1893): printed «Въ пользу инвалидовъ.» | «Евгеній Онѣгинъ, оп.»; the
      annotation already holds the banner, the work title had it prefixed.
uv run python docs/eval/title_check_2026-10-10/fix_fused.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs" / "full_run" / "raw"
def load(page):
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    return p, d, fmt
w = "--write" in sys.argv
p, d, f = load("repertoire_1898-99_p029"); S = d["sessions"][19]
assert S["works"][0] == {"work_title": "Бенефисъ г-жи Никулиной", "genre": "Ложь"} and S["annotation"] is None
S["annotation"] = "Бенефисъ г-жи Никулиной."
S["works"] = [{"work_title": "Ложь", "genre": "ком."}, {"work_title": "Ноктюрнъ", "genre": "др. эск."}, S["works"][2]]
assert S["works"][2]["work_title"] == "Прелестная незнакомка"
if w: p.write_text(json.dumps(d, indent=f[0], ensure_ascii=f[1]) + f[2], encoding="utf-8")
p, d, f = load("repertoire_1893-94_pair012"); S = d["sessions"][102]
assert S["works"] == [{"work_title": "Въ пользу инвалидовъ. Евгеній Онѣгинъ", "genre": "оп."}] and S["annotation"] == "Въ пользу инвалидовъ."
S["works"][0]["work_title"] = "Евгеній Онѣгинъ"
if w: p.write_text(json.dumps(d, indent=f[0], ensure_ascii=f[1]) + f[2], encoding="utf-8")
print("WROTE" if w else "DRY RUN OK")
