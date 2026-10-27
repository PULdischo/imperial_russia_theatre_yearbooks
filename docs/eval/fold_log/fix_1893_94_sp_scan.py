"""1893-94 St Petersburg was 494 р. 14 к. under the printed totals (French −492.40, opera +32.03, drama+German+mixed −33.77).
Every Маріинскій, Александринскій and Михайловскій figure read against the scan (ForUpload_1893-94_Repertoire.pdf,
2026-10-27, checked by Claude; each difference below confirmed at full resolution).
- p. 11, Михайловскій 26-28 Nov 1893: a one-row shift. Stored 26 held a copy of 25 (La Paix du Ménage, 894 р. 10 к.), 27 held
  26, 28 held 27 with its benefit heading; 28's own cell was lost. Scan: 26 «У своихъ, ком. / Лѣтняя картинка, карт.»
  1280 р. 95 к.; 27 «Bénéfice de M-lle Balletta.» «Cendrillonnette, opérette. / Les Projets de ma Tante, com.» 2684 р. 50 к.;
  28 the same two plays, no heading, 1383 р. 50 к.
- p. 5, 3 Oct Михайловскій «Oscar ...» 455 р. -> 458 р.
- p. 19, 15 Feb 1894 Маріинскій held a copy of 16 Feb («Пиковая дама» 2943 р. 20); scan «Демонъ, оп.» 2776 р. 70 к.
- Маріинскій kopecks dropped in extraction (pp. 12-13, 18): 10 cells.
- p. 13, 13 Dec Маріинскій: «1-е и 2-е д.» + genre-less «Русланъ и Людмила» are one printed excerpt «1-е и 2-е д. оп.
  Русланъ и Людмила» (as stored for 16 Dec); merged, keeping the excerpt in position 2 (no later performance id shifts).
uv run python docs/eval/fold_log/fix_1893_94_sp_scan.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
W = lambda *ws: [{"work_title": a, "genre": b} for a, b in ws]
# page -> {session: (stored receipts, new receipts, new works or None, annotation: '' keep / None clear / str set)}
FIX = {
 "repertoire_1893-94_pair004": {98: ("455 р. — к.", "458 р.", None, "")},
 "repertoire_1893-94_pair010": {
   61: ("894 р. 10 к.", "1280 р. 95 к.", W(("У своихъ", "ком."), ("Лѣтняя картинка", "карт.")), ""),
   64: ("1280 р. 95 к.", "2684 р. 50 к.", W(("Cendrillonnette", "opérette."), ("Les Projets de ma Tante", "com.")), "Bénéfice de M-lle Balletta."),
   67: ("2684 р. 50 к.", "1383 р. 50 к.", W(("Cendrillonnette", "opérette."), ("Les Projets de ma Tante", "com.")), None)},
 "repertoire_1893-94_pair012": {
   11: ("2948 р.", "2948 р. 70 к.", W(("Сельская честь", "оп."), ("1-е и 2-е д. оп. Русланъ и Людмила", None)), ""),
   14: ("3540 р.", "3540 р. 50 к.", None, ""), 17: ("2952 р.", "2952 р. 20 к.", None, ""),
   36: ("4066 р.", "4066 р. 90 к.", None, ""), 42: ("1534 р.", "1534 р. 37 к.", None, "")},
 "repertoire_1893-94_pair018": {
   2: ("2934 р.", "2934 р. 20 к.", None, ""), 4: ("3445 р.", "3445 р. 50 к.", None, ""),
   13: ("2943 р. 20", "2776 р. 70 к.", W(("Демонъ", "оп.")), ""),
   31: ("2939 р.", "2939 р. 70 к.", None, ""), 33: ("2766 р.", "2766 р. 20 к.", None, ""), 35: ("2938 р.", "2938 р. 20 к.", None, "")}}
for page, cells in FIX.items():
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, (old, new, works, ann) in cells.items():
        S = d["sessions"][s - 1]
        assert S["receipts_text"] == old, (page, s, S["theater"], S["receipts_text"])
        S["receipts_text"] = new
        if works is not None: S["works"] = works
        if ann != "": S["annotation"] = ann
        S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-27: 1893-94 SP season-stats check"
        print(page[-7:], s, S["date_text"], S["theater"], old, "->", new, [w["work_title"] for w in S["works"]] if works else "", S.get("annotation") if ann != "" else "")
    if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN")
