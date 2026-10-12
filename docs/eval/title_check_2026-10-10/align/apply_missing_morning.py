"""Add the one morning performance that the half-dash cells turned up as missing (issue #151 follow-up 20).

1892-93 pair010, Малый, 21 Суббота (21 Nov 1892): the print has утро «Графъ де Ризоръ, др.» 827 р. 42 к. and a dash вечеръ. The stored
data held only the empty dark evening (s085). Two blind readers (detail_34, detail_37 at 3200 px) agree on title, genre and figure; neither
the title nor the figure occurs anywhere else in 1892-93. The performance is inserted before s085 as `morning`; s085 stays as the dark evening.
"""
import copy, json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
path = RAW / "repertoire_1892-93_pair010.raw.json"
t = path.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                fmt = (ind, ea, tr)
assert fmt
S = d["sessions"]
i = next(k for k, s in enumerate(S) if s["date_text"].startswith("21 Суббота") and s["theater"].startswith("Малый") and s.get("session") == "evening")
x = S[i]
assert x["is_dark"] and not x.get("works") and not x.get("receipts_text")
new = copy.deepcopy(x)
new.update({"session": "morning", "is_dark": False, "receipts_text": "827 р. 42 к.", "annotation": None,
            "works": [{"work_title": "Графъ де Ризоръ", "genre": "др."}], "_source": None,
            "_fix_note": "morning performance read from the scan 2026-10-12 (half-dash cell, issue #151 follow-up 20)"})
S.insert(i, new)
print("inserted before s%03d; sessions %d -> %d" % (i + 1, len(S) - 1, len(S)))
if WRITE:
    path.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if WRITE else "DRY RUN")
