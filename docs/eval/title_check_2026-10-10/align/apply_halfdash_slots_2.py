"""Set `morning` on the two half-dash cells left in the `D_other` class (issue #151 follow-up 21).

    uv run python docs/eval/title_check_2026-10-10/align/apply_halfdash_slots_2.py [--write]

Both cells were looked at on the scan (align_crops, 2026-10-12): the upper half prints the performance, the lower half a dash; the
утро/веч labels are printed once at the row's edge. Same treatment as apply_halfdash_slots.py: the stored session takes the slot,
the dash half is NOT added as a session.
  1896-97 pair014 Большой 28 Суббота (28 Dec 1896): «Аида, оп.» 1186 р. 41 к. in the upper half, dash below.
  1903-04 p017 Большой 6 Суббота (6 Dec 1903): «1-е, 2-е и 3-е д. бал. Корсаръ | Привалъ кавалеріи» beside УТРО, dash beside ВЕЧ.
"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
NOTE = "morning/evening slot read from the scan 2026-10-12 (half-dash cell, issue #151 follow-up 21)"
# (page, day, session number, first-title prefix, stored slot, new slot)
SPEC = [["1896-97_pair014", "28", 47, "Аида", "unspecified", "morning"],
        ["1903-04_p017", "6", 24, "1-е, 2-е и 3-е д.", "unspecified", "morning"]]
n = 0
for page, day, s, title, cur, slot in SPEC:
    path = RAW / f"repertoire_{page}.raw.json"
    t = path.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    fmt = (ind, ea, tr)
    assert fmt, page
    x = d["sessions"][s - 1]
    first = (x.get("works") or [{}])[0]
    assert x["date_text"].split()[0] == day and x.get("session") == cur and "Больш" in x["theater"], (page, s, x["date_text"], x.get("session"), x["theater"])
    assert any(str(v).startswith(title) for v in first.values()), (page, first)
    x["session"] = slot
    x["_fix_note"] = (x["_fix_note"] + " | " if x.get("_fix_note") else "") + NOTE
    n += 1
    if WRITE:
        path.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(f"{n} sessions set;", "WROTE" if WRITE else "DRY RUN")
