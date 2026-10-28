"""1892-93: four SP theater cells with no stored row (research shows them as not_captured placeholders) are printed dashes
on the scan (ForUpload_1892-93_Repertoire.pdf spreads 4-6, checked by Claude 2026-10-28):
21 Nov 1892 Маріинскій (pair010), 19 Dec 1892 Александринскій (pair012), 9 and 16 Jan 1893 Александринскій (pair014).
Each is a Saturday on which the other dark SP theater's cell is stored as is_dark. The rows are APPENDED at the end of each
page's sessions array, so no existing event_id shifts (issue #131 rule).
uv run python docs/eval/reconciliation/fix_1892_93_dash_cells.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
ADD = {  # page: [(date_text, theater as stored on the page)]
    "pair010": [("21 Суббота.", "Маріинскій.")],
    "pair012": [("19 Суббота.", "Александринскій.")],
    "pair014": [("9 Суббота.", "Александринскій."), ("16 Суббота.", "Александринскій.")],
}
NOTE = "scan 2026-10-28: printed dash, no stored row (was a not_captured placeholder); appended at the end of the array"
for page, cells in ADD.items():
    p = RAW / f"repertoire_1892-93_{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    S = d["sessions"]
    for date_text, theater in cells:
        assert not [s for s in S if s["date_text"] == date_text and s["theater"] == theater], (page, date_text, theater)
        assert [s for s in S if s["date_text"] == date_text], (page, date_text)  # the date itself is on the page
        S.append({"date_text": date_text, "month_text": None, "year_text": None, "session": "unspecified",
                  "theater": theater, "is_dark": True, "receipts_text": None, "annotation": None, "works": [],
                  "_fix_note": NOTE})
        print(page, f"s{len(S):03d}", date_text, theater)
    if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
