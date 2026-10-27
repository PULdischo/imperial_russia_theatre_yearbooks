"""1909-10, Маріинскій, two cells on p. 38 (repertoire_1909-10_p037) whose kopecks the extraction dropped:
23 Feb 1910 «Миранда (послѣдняя борьба)» stored «3358 р.», print «3358 р. 50 к.»; 24 Feb 1910 evening «Эсмеральда» stored
«3479 р.», print «3479 р. 55 к.» (both read at 4-5x on ForUpload_1909-10_Repertoire.pdf p. 38, checked by Claude, 2026-10-27).
The second closes SP ballet against the printed season totals (p. 58: 51 events, 167,180 р. 22 к.); ledger 1909-10.
uv run python docs/eval/reconciliation/fix_1909_10_mariinsky_kopecks.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1909-10_p037.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
FIXES = [  # (1-based session index, date_text, title, stored, print)
    (7, "23 Вторник.", "Миранда (послѣдняя борьба)", "3358 р.", "3358 р. 50 к."),
    (9, "24 Среда.", "Эсмеральда", "3479 р.", "3479 р. 55 к."),
]
for i, date_text, title, old, new in FIXES:
    S = d["sessions"][i - 1]
    assert S["date_text"] == date_text and S["theater"].startswith("Маріин") and S["receipts_text"] == old, S
    assert [w["work_title"] for w in S["works"]] == [title], S["works"]
    S["receipts_text"] = new
    note = f"scan 2026-10-27: receipts «{old}» -> «{new}» (kopecks dropped in extraction)"
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
    print(date_text, S["theater"], S["receipts_text"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
