"""1893-94 Маріинскій receipts stored without their kopecks (RG, 2026-10-15: apply the ballet ones and the opera ones
already read). The Маріинскій ballet receipts were 2 р. 96 к. under the printed season total (Балетныхъ, Маріинскій)
with the count equal; on the scan (outputs/title_check_2026-10-10/align_crops, 2026-10-15) four ballet cells print kopecks
that were dropped: together exactly 2 р. 96 к. Four opera cells on the same crops are truncated the same way.
Not touched: 16 Nov «2901 р.» is printed without kopecks. The other ~90 kopeck-less figures of 1892-93/1893-94 are unread.
uv run python docs/eval/fold_log/fix_1893_94_dropped_kopecks.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
# page, day, stored, printed, works (first title, for the assert)
FIX = [("repertoire_1893-94_pair008", "24", "2147 р. 9", "2147 р. 95 к.", "Пахита"),
       ("repertoire_1893-94_pair010", "17", "2239 р.", "2239 р. 45 к.", "Спящая красавица"),
       ("repertoire_1893-94_pair012", "5", "3473 р.", "3473 р. 70 к.", "Золушка"),
       ("repertoire_1893-94_pair018", "6", "2783 р.", "2783 р. 95 к.", "Спящая красавица"),
       ("repertoire_1893-94_pair010", "18", "2946 р. 2", "2946 р. 20 к.", "Мефистофель"),
       ("repertoire_1893-94_pair012", "3", "2879 р.", "2879 р. 20 к.", "Тангейзеръ"),
       ("repertoire_1893-94_pair012", "6", "2939 р.", "2939 р. 70 к.", "Паяцы"),
       ("repertoire_1893-94_pair018", "4", "3535 р.", "3535 р. 50 к.", "Паяцы")]
docs = {}
for page, day, old, new, first in FIX:
    if page not in docs:
        t = (RAW / f"{page}.raw.json").read_text(encoding="utf-8"); fmt = None
        d = json.loads(t)
        for ind in (2, 4, 1, None):
            for ea in (False, True):
                for tr in ("", "\n"):
                    if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
        assert fmt, page
        docs[page] = (d, fmt)
    d = docs[page][0]
    hits = [s for s in d["sessions"] if s["date_text"].split()[0] == day and "Маріин" in (s.get("theater") or "")
            and s.get("receipts_text") == old]
    assert len(hits) == 1 and hits[0]["works"][0]["work_title"] == first, (page, day, len(hits))
    s = hits[0]; s["receipts_text"] = new
    s["_fix_note"] = (s["_fix_note"] + "; " if s.get("_fix_note") else "") + f"scan 2026-10-15: kopecks printed ({new}), stored {old!r}"
    print(page, s["date_text"], first, old, "->", new)
if "--write" in sys.argv:
    for page, (d, fmt) in docs.items():
        (RAW / f"{page}.raw.json").write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
    print("WROTE")
