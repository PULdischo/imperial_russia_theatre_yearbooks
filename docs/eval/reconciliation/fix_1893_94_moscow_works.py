"""1893-94 Moscow works corrected from the scan (ForUpload_1893-94_Repertoire.pdf, 2026-10-27, checked by Claude; found
in the Moscow pp. 6-25 receipts read; RG: "fix the 17 Feb 1894 Большой works (add the Мазепа entracte, store the three
excerpts as printed), «Кручина» ×2 and «Аида» (1893-94)"). Receipts unchanged in every cell.
- p. 19, 17 Feb 1894 Большой, «Спектакль въ память П. И. Чайковскаго»: the print reads
    Антрактъ къ 4-му д. оп. Мазепа. / Іоланта, оп. / 2-е д. оп. Пиковая дама. /
    2-я карт. 1-го д. и арія 2-й карт. 2-го д. изъ оп. Евгеній Онѣгинъ. / 1-я карт. 2-го д. оп. Черевички.
  Stored: Іоланта + three whole operas. The three excerpts are stored as printed (in place, positions 2-4), and the
  entracte is appended as position 5 so no performance id shifts (it is printed first).
- p. 16, 18 Jan 1894 Малый «Кручинина» and 26 Jan 1894 Малый «Кручиня»: the print reads «Кручина, др.» both times.
- p. 7, 22 Oct 1893 Большой «Лида, оп.»: the print reads «Аида, оп.».
uv run python docs/eval/reconciliation/fix_1893_94_moscow_works.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
NOTE = "scan 2026-10-27: works corrected (1893-94 Moscow read)"
# page -> session (1-based) -> (expected date_text prefix, theater prefix, stored works, new works)
FIX = {
 "repertoire_1893-94_pair018": {38: ("17 ", "Больш",
     [("Іоланта", "оп."), ("Пиковая дама", "оп."), ("Евгеній Онѣгинъ", "оп."), ("Черевички", "оп.")],
     [("Іоланта", "оп."), ("2-е д. оп. Пиковая дама", None),
      ("2-я карт. 1-го д. и арія 2-й карт. 2-го д. изъ оп. Евгеній Онѣгинъ", None),
      ("1-я карт. 2-го д. оп. Черевички", None), ("Антрактъ къ 4-му д. оп. Мазепа", None)])},
 "repertoire_1893-94_pair016": {
   18: ("18 ", "Малый", [("Кручинина", "др."), ("Наканунѣ золотой свадьбы", "ш.")],
        [("Кручина", "др."), ("Наканунѣ золотой свадьбы", "ш.")]),
   56: ("26 ", "Малый", [("Кручиня", "др."), ("Я играю большую роль!", "ш.")],
        [("Кручина", "др."), ("Я играю большую роль!", "ш.")])},
 "repertoire_1893-94_pair006": {50: ("22 ", "Больш", [("Лида", "оп.")], [("Аида", "оп.")])},
}
for page, cells in FIX.items():
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, (date, th, old, new) in cells.items():
        S = d["sessions"][s - 1]
        got = [(w["work_title"], w.get("genre")) for w in S["works"]]
        assert S["date_text"].startswith(date) and S["theater"].startswith(th) and got == old, (page, s, S["date_text"], S["theater"], got)
        S["works"] = [{"work_title": a, "genre": b} for a, b in new]
        S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + NOTE
        print(page[-7:], s, S["date_text"], S["theater"], [a for a, _ in old], "->", [a for a, _ in new])
    if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
