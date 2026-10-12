"""«Проступка и воспитанная» -> «Простушка и воспитанная» in 13 cells, and one missing first title (issue #151 follow-up 22).

    uv run python docs/eval/title_check_2026-10-10/align/fix_prostushka.py [--write]

Every one of the 13 cells was read on a full-resolution crop of its scan (2026-10-12) and prints «Простушка»; the stored form was
a misread, not a print variant. On 1892-93 pair024 Александринскій 30 Пятн. (30 Apr 1893, 430 р. 95 к.) the print has
«Всякому свое, ком.» above it, which the stored session lacked; it is added as the first work.
The edits are made on the file text; every other byte is untouched.
"""
import sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
OLD, NEW = '"work_title": "Проступка и воспитанная"', '"work_title": "Простушка и воспитанная"'
PAGES = {"1890-91_p015": 1, "1891-92_p003": 1, "1891-92_pair014": 2, "1891-92_pair022": 1, "1892-93_pair024": 1, "1894-95_pair006": 2,
         "1894-95_pair010": 1, "1896-97_pair004": 1, "1896-97_pair010": 1, "1896-97_pair020": 1, "1896-97_p012": 1}
ADD_OLD = '''      "works": [
        {
          "work_title": "Проступка и воспитанная",
          "genre": "вод."
        }
      ],'''
ADD_NEW = '''      "works": [
        {
          "work_title": "Всякому свое",
          "genre": "ком."
        },
        {
          "work_title": "Простушка и воспитанная",
          "genre": "вод."
        }
      ],'''
n = 0
for page, k in PAGES.items():
    path = RAW / f"repertoire_{page}.raw.json"
    t = path.read_text(encoding="utf-8")
    assert t.count(OLD) == k and t.count("Проступка") == k, (page, t.count(OLD), t.count("Проступка"))
    if page == "1892-93_pair024":
        assert t.count(ADD_OLD) == 1 and '"receipts_text": "430 р. 95 к."' in t[t.index(ADD_OLD) - 200:t.index(ADD_OLD)], page
        t = t.replace(ADD_OLD, ADD_NEW)
    t = t.replace(OLD, NEW); n += k
    if WRITE:
        path.write_text(t, encoding="utf-8")
print(f"{n} titles in {len(PAGES)} pages;", "WROTE" if WRITE else "DRY RUN")
