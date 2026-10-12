"""Set morning/evening on the 25 sessions whose printed cell has one performing half and one dash half (issue #151 follow-up 20).

    uv run python docs/eval/title_check_2026-10-10/align/apply_halfdash_slots.py [--write]

Each cell was read twice (structure read + detail read, align/reports + align/reports_detail 33-36); the performing half is the one with
works. Slot = the printed label (утро/вечеръ) where the cell prints one, else the position (upper = morning, lower = evening; the
labels are then printed once at the row's left edge). The dash half is NOT added as a session. Two cells were already set or are
handled elsewhere (1903-04 p025 Новый 1: already `morning`; 1892-93 pair010 Малый 21: the performance itself was missing, see
apply_missing_morning.py).
"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
NOTE = "morning/evening slot read from the scan 2026-10-12 (half-dash cell, issue #151 follow-up 20)"
# (page, theater key, day, session number, stored slot, new slot)
SPEC = [["1890-91_pair024","Алекс","27",22,"unspecified","morning"],["1890-91_pair024","Марии","27",21,"unspecified","morning"],["1890-91_pair024","Михай","27",23,"unspecified","evening"],["1891-92_pair012","Больш","28",98,"unspecified","morning"],["1891-92_pair012","Малый","28",105,"unspecified","morning"],["1891-92_pair012","Марии","28",92,"unspecified","morning"],["1891-92_pair014","Больш","4",39,"unspecified","morning"],["1892-93_pair010","Больш","14",5,"unspecified","morning"],["1892-93_pair010","Больш","21",20,"unspecified","morning"],["1892-93_pair010","Малый","21",85,"evening","morning"],["1892-93_pair014","Больш","2",119,"unspecified","morning"],["1892-93_pair014","Малый","2",8,"unspecified","morning"],["1894-95_pair008","Больш","7",73,"unspecified","morning"],["1895-96_pair006","Малый","21",48,"unspecified","morning"],["1898-99_p013","Малый","21",25,"unspecified","morning"],["1898-99_p013","Новый","21",26,"unspecified","morning"],["1898-99_p018","Алекс","26",24,"unspecified","morning"],["1898-99_p019","Новый","29",38,"unspecified","evening"],["1898-99_p021","Больш","2",10,"unspecified","morning"],["1898-99_p021","Малый","2",11,"unspecified","morning"],["1900-01_p019","Малый","30",27,"unspecified","morning"],["1900-01_p019","Новый","30",42,"unspecified","morning"],["1902-03_p019","Малый","28",40,"unspecified","morning"],["1903-04_p017","Малый","6",1,"unspecified","morning"],["1903-04_p017","Новый","6",12,"unspecified","morning"],["1903-04_p025","Новый","1",32,"morning","morning"]]
by_page = {}
for page, th, day, s, cur, slot in SPEC:
    by_page.setdefault(page, []).append((th, day, s, cur, slot))
n = 0
for page, items in sorted(by_page.items()):
    path = RAW / f"repertoire_{page}.raw.json"
    t = path.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    fmt = (ind, ea, tr)
    assert fmt, page
    for th, day, s, cur, slot in items:
        x = d["sessions"][s - 1]
        assert x["date_text"].split()[0] == day and x.get("session") == cur, (page, s, x["date_text"], x.get("session"), day, cur)
        if cur == slot:
            continue
        if not x.get("works"):
            continue   # handled separately (empty stored session)
        x["session"] = slot
        x["_fix_note"] = NOTE
        n += 1
    print(f"{page}: {len(items)} cells")
    if WRITE:
        path.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(f"{n} sessions set;", "WROTE" if WRITE else "DRY RUN")
