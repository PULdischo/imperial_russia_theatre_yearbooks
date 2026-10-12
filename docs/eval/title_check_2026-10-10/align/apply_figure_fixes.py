"""Receipts-figure corrections from the figure-level re-read of 1899-00 SP and 1903-04 SP (issue #151 follow-up 17).

    uv run python docs/eval/title_check_2026-10-10/align/apply_figure_fixes.py [--write]

Every St Petersburg page of the two seasons (38 pages, 1,199 stored figures) was read blind at 3000 px (reports_figures); the six
cells where the read and the stored figure differ were read again by two readers at native resolution (reports_detail detail_31/32).
Changed only where at least three reads agree against the stored value:
  1899-00 p008 МАР 27 Nov  «Князь Игорь»          3539 р. 50 к. -> 3599 р. 50 к.   (also the whole 60.00 of the opera line's residual)
  1903-04 p018 АЛЕК 21 Dec утро «Безъ вины виноватые» 225 р. 67 к. -> 235 р. 67 к. (faint hundreds-of-tens digit, three reads)
  1903-04 p018 АЛЕК 27 Dec вечеръ charity block     2602 р. 50 к. -> no figure   (two native readers + the 3000 px read: the block prints
                                                    none; 2602 р. 50 к. is the Михайловскій benefit's figure of the same date, s041)
  1903-04 p030 МИХ 11 Feb «Les affaires sont les affaires» 1066 р. 05 к. -> 1056 р. 05 к.
  1903-04 p034 МАР 23 Mar «Жизнь за Царя»        1502 р. 41 к. -> 1502 р. 40 к.   (damaged last digit; the kopeck sum of the printed total supports 40)
NOT changed: 1899-00 p024 МАР 2 Среда «Дочь Фараона» 2839 р. 70 к.: three reads see 2859 on a damaged glyph, but the printed ballet total
equals the stored figures to the kopeck only with 2839 (see known_issues.md follow-up 17).
"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
FIX = [
    ("1899-00_p008", 31, "3539 р. 50 к.", "3599 р. 50 к.", "Князь"),
    ("1903-04_p018", 21, "225 р. 67 к.", "235 р. 67 к.", "Безъ вины"),
    ("1903-04_p018", 27, "2602 р. 50 к.", None, "Дѣло"),
    ("1903-04_p030", 26, "1066 р. 05 к.", "1056 р. 05 к.", "Les affaires"),
    ("1903-04_p034", 12, "1502 р. 41 к.", "1502 р. 40 к.", "Жизнь за"),
]
NOTE = "figure corrected from the scan 2026-10-12 (figure-level re-read, issue #151 follow-up 17)"
for page, s, old, new, title in FIX:
    path = RAW / f"repertoire_{page}.raw.json"
    t = path.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    fmt = (ind, ea, tr)
    assert fmt, page
    x = d["sessions"][s - 1]
    assert x.get("receipts_text") == old, (page, s, x.get("receipts_text"), old)
    assert any((w.get("work_title") or "").startswith(title) for w in x.get("works") or []), (page, s, title)
    x["receipts_text"] = new
    x["_fix_note"] = NOTE
    print(f"{page} s{s:03d}: {old!r} -> {new!r}")
    if WRITE:
        path.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if WRITE else "DRY RUN")
