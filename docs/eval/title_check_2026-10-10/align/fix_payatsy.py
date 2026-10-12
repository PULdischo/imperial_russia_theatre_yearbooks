"""«Панцы» -> «Паяцы» (issue #151 follow-up 21): a misread я in three Repertoire cells, each checked on a full-resolution crop.

    uv run python docs/eval/title_check_2026-10-10/align/fix_payatsy.py [--write]

  1895-96 pair014 Маріинскій 1 Понед. (1 Jan 1896): «Рафаэль, оп. | Паяцы, оп.» 2941 р. 70 к.
  1895-96 p026 Большой 19 Воскресенье (19 May 1896): «Паяцы, оп. | Даита, бал.»
  1896-97 pair020 Маріинскій 20 Четвергъ, evening (20 Feb 1897): «1-е д. оп. Орлеанская дѣва. | Паяцы, оп.» 3535 р. 70 к.
The edit is made on the file text at the exact work_title; every other byte is untouched.
"""
import sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
OLD, NEW = '"work_title": "Панцы"', '"work_title": "Паяцы"'
for page in ("1895-96_pair014", "1895-96_p026", "1896-97_pair020"):
    path = RAW / f"repertoire_{page}.raw.json"
    t = path.read_text(encoding="utf-8")
    assert t.count(OLD) == 1 and "Панцы" not in t.replace(OLD, ""), page
    if WRITE:
        path.write_text(t.replace(OLD, NEW), encoding="utf-8")
    print(page, "ok")
print("WROTE" if WRITE else "DRY RUN")
