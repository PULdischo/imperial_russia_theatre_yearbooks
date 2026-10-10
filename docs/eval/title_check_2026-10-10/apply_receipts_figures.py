"""Add six receipts figures the extraction dropped (issue #151 follow-up 11). Each read blind on the scan by two readers whose digits agree
(reader_reports/rcpt_1xx.csv first pass, rcpt_138.csv / rcpt_139.csv second pass); every target session currently has receipts_text = null.
  Q011 repertoire_1892-93_pair010 s106, SP, 3 Dec 1892          1452 р. 57 к.   (La Femme à Papa ...)
  Q095 repertoire_1895-96_pair014 s063, Moscow Большой, 7 Jan 1896  2647 р. 62 к.   (Аида; foot of the digits clipped by the fold, both readers agree)
  Q136/137/138 repertoire_1904-05_p033 s033/s035/s037, Moscow Новый, утро 25/26/27 Feb 1905: 403 р. 01 к. each (the same figure under all three)
  Q153 repertoire_1906-07_p014 s019, SP Мариинскій, утро 19 Nov 1906    2032 р. 53 к.   (Садко)
NOT added: Q091 (the figure is stored on the neighbouring evening session: one undivided cell was split in two); Q016 (fold, 3 vs 8 unresolved).
uv run python docs/eval/title_check_2026-10-10/apply_receipts_figures.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs" / "full_run" / "raw"
FIG = [("repertoire_1892-93_pair010", 106, "1452 р. 57 к."), ("repertoire_1895-96_pair014", 63, "2647 р. 62 к."),
       ("repertoire_1904-05_p033", 33, "403 р. 01 к."), ("repertoire_1904-05_p033", 35, "403 р. 01 к."), ("repertoire_1904-05_p033", 37, "403 р. 01 к."),
       ("repertoire_1906-07_p014", 19, "2032 р. 53 к.")]
by = {}
for page, s, fig in FIG: by.setdefault(page, []).append((s, fig))
w = "--write" in sys.argv
for page, items in by.items():
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, fig in items:
        S = d["sessions"][s - 1]
        assert not S.get("receipts_text"), (page, s, S.get("receipts_text"))
        S["receipts_text"] = fig
        print(f"{page} s{s}: {S['theater']} {S['date_text']} {[x['work_title'] for x in S['works']][:2]} <- {fig}")
    if w: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if w else "DRY RUN")
