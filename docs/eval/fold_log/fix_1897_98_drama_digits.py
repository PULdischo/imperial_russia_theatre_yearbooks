"""1897-98: every Малый (206) and Александринскій (228) receipts figure read against the scan (ForUpload_1897-98_Repertoire.pdf,
2026-10-27, checked by Claude) after the fold-log apply left Moscow Малый drama −89.58 and SP Александринскій drama −617.95
against the printed season totals. Four misreads, each confirmed at 4x zoom:
  9 Четверг  (p. 6)  Малый            1391 р. 80 к. -> 1391 р. 86 к.
  30 Четв.   (p. 8)  Малый            1268 р. 00 к. -> 1268 р. 06 к.
  31 Пятн.   (p. 8)  Малый            1331 р. 20 к. -> 1331 р. 26 к.
  26 Пятница (p. 5)  Александринскій  1617 р. 45 к. -> 1647 р. 45 к.
uv run python docs/eval/fold_log/fix_1897_98_drama_digits.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
FIX = [("repertoire_1897-98_pair006", 70, "Малый", "1391 р. 80 к.", "1391 р. 86 к."),
       ("repertoire_1897-98_pair008", 52, "Малый", "1268 р. 00 к.", "1268 р. 06 к."),
       ("repertoire_1897-98_pair008", 57, "Малый", "1331 р. 20 к.", "1331 р. 26 к."),
       ("repertoire_1897-98_pair004", 74, "Александр", "1617 р. 45 к.", "1647 р. 45 к.")]
by = {}
for page, s, th, old, new in FIX: by.setdefault(page, []).append((s, th, old, new))
for page, items in by.items():
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, th, old, new in items:
        S = d["sessions"][s - 1]
        assert S["receipts_text"] == old and S["theater"].startswith(th), (page, s, S["theater"], S["receipts_text"])
        S["receipts_text"] = new
        S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-27: season-stats drama check"
        print(page, s, S["date_text"], S["theater"], old, "->", new)
    if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN")
