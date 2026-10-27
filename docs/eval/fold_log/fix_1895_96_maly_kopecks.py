"""1895-96: every Большой and Малый receipts figure read against the scan (ForUpload_1895-96_Repertoire.pdf, 2026-10-27,
checked by Claude) while chasing the Moscow residuals against the printed totals. 13 Малый cells on pp. 4-7 had lost their
kopecks (or a kopeck digit) in extraction; each is restored here as printed. Nothing else in either column differs.
uv run python docs/eval/fold_log/fix_1895_96_maly_kopecks.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
FIX = [("repertoire_1895-96_pair004", 6, "1390 р. 3", "1390 р. 36 к."), ("repertoire_1895-96_pair004", 11, "981 р. 7", "981 р. 73 к."),
       ("repertoire_1895-96_pair004", 19, "1251 р.", "1251 р. 1 к."), ("repertoire_1895-96_pair004", 24, "959 р.", "959 р. 73 к."),
       ("repertoire_1895-96_pair004", 29, "1375 р.", "1375 р. 20 к."), ("repertoire_1895-96_pair004", 39, "1073 р.", "1073 р. 77 к."),
       ("repertoire_1895-96_pair004", 44, "1201 р.", "1201 р. 77 к."), ("repertoire_1895-96_pair004", 49, "1272 р", "1272 р. 66 к."),
       ("repertoire_1895-96_pair004", 59, "1143 р.", "1143 р. 40 к."), ("repertoire_1895-96_pair004", 64, "1366 р.", "1366 р. 53 к."),
       ("repertoire_1895-96_pair006", 7, "782 р. 4 к.", "782 р. 44 к."), ("repertoire_1895-96_pair006", 38, "1385 р.", "1385 р. 31 к."),
       ("repertoire_1895-96_pair006", 43, "1585 р.", "1585 р. 12 к.")]
by = {}
for page, s, old, new in FIX: by.setdefault(page, []).append((s, old, new))
for page, items in by.items():
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, old, new in items:
        S = d["sessions"][s - 1]
        assert S["receipts_text"] == old and S["theater"].startswith("Малый"), (page, s, S["theater"], S["receipts_text"])
        S["receipts_text"] = new
        S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-27: kopecks restored (Moscow season-stats check)"
        print(page, s, S["date_text"], old, "->", new)
    if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN")
