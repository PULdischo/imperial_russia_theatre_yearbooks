"""1893-94 Moscow was 60 р. 10 к. under the printed season totals after the fold-log apply: Малый drama −30.00 and opera
−30.00 (counts equal). Read on the scan (ForUpload_1893-94_Repertoire.pdf, 2026-10-27, checked by Claude), a tens digit
misread in each:
  5 Воскрес. (Sept 1893, p. 3)  Большой «Жизнь за Царя, оп.»     2618 р. 53 к. -> 2648 р. 53 к.
  15 Среда.  (Sept 1893, p. 4)  Малый «Въ такую ночь... / Не надо / Шашки»  818 р. 16 к. -> 848 р. 16 к.
uv run python docs/eval/fold_log/fix_1893_94_moscow_tens.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
FIX = [("repertoire_1893-94_pair002", 79, "Больш", "2618 р. 53 к.", "2648 р. 53 к."),
       ("repertoire_1893-94_pair004", 10, "Малый", "818 р. 16 к.", "848 р. 16 к.")]
for page, s, th, old, new in FIX:
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    S = d["sessions"][s - 1]
    assert S["receipts_text"] == old and S["theater"].startswith(th), (page, s, S["theater"], S["receipts_text"])
    S["receipts_text"] = new
    S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-27: tens digit (Moscow season-stats check)"
    print(page, s, S["date_text"], S["theater"], old, "->", new)
    if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN")
