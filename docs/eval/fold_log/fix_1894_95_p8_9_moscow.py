"""1894-95, spread pp. 8-9 (repertoire_1894-95_pair008): Moscow cells misread or shifted, found while reading every Большой and
Малый figure against the scan (ForUpload_1894-95_Repertoire.pdf, 2026-10-27, checked by Claude). Each cell below is set to
what the scan prints; the stored values are asserted first.
- 17/18 Jan 1895 Малый: stored 17 held 18's bill and figure, stored 18 held a garbled copy of 19 («Дерево отъ ума / Забава
  струна»). Scan: 17 «Лѣсъ, ком. / Спириты, вод.» 1381 р. 39 к.; 18 «Непогрѣшимый, ком. / На тотъ свѣтъ, ш.» 1373 р. 67 к.
- Garbled titles: 22 Jan morning «Ворогъ къ дѣлу / Вѣрь» -> «На порогѣ къ дѣлу / Вѣеръ»; 22 Jan evening «Рись г. Максеева» is
  the annotation «Бенефисъ г. Макшеева.», works «Горькая судьбина, др. / Повѣтріе, ком.-ш.»; 23 Jan «Коля мужей» -> «Школа
  мужей»; 25 Jan «Кая судьбина / Вовѣтріе» -> «Горькая судьбина / Повѣтріе»; 16 Jan «Подъ столомъ» -> «Стряпчій подъ
  столомъ»; 8 Jan morning «Вѣрь» -> «Вѣеръ».
- Missing/fused works: 9 Jan «Золото» + «Школа мужей, ком.»; 10 Jan «Волки и овцы, ком.|сц.» -> «Волки и овцы, ком. / Утро съ
  сюрпризами, сц.».
- 12 Jan Большой «Куанъ, оп.» -> «Донъ Жуанъ, оп.».
uv run python docs/eval/fold_log/fix_1894_95_p8_9_moscow.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs/full_run/raw/repertoire_1894-95_pair008.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
W = lambda *ws: [{"work_title": a, "genre": b} for a, b in ws]
# session -> (stored works, stored receipts, new works, new receipts, new annotation or None to keep)
FIX = {
 3:  ([("Волки и овцы, ком.", "сц.")], "1370 р. 73 к.", W(("Волки и овцы", "ком."), ("Утро съ сюрпризами", "сц.")), None, None),
 12: ([("Куанъ", "оп.")], "2638 р. 56 к.", W(("Донъ Жуанъ", "оп.")), None, None),
 34: ([("Золото", "ком."), ("Подъ столомъ", "вод.")], "1395 р. 49 к.", W(("Золото", "ком."), ("Стряпчій подъ столомъ", "вод.")), None, None),
 39: ([("Погрѣшимый", "ком."), ("Тотъ свѣтъ", "ш.")], "1373 р. 67 к.", W(("Лѣсъ", "ком."), ("Спириты", "вод.")), "1381 р. 39 к.", None),
 44: ([("Дерево отъ ума", "ком."), ("Забава струна", "вод.")], "1375 р. 39 к.", W(("Непогрѣшимый", "ком."), ("На тотъ свѣтъ", "ш.")), "1373 р. 67 к.", None),
 53: ([("Ворогъ къ дѣлу", "сц."), ("Вѣрь", "ком.")], "334 р. 20 к.", W(("На порогѣ къ дѣлу", "сц."), ("Вѣеръ", "ком.")), None, None),
 56: ([("Рись г. Максеева", "др."), ("Кая судьбина", "др."), ("Вѣтріе", "ком.-ш.")], "3353 р. 80 к.",
      W(("Горькая судьбина", "др."), ("Повѣтріе", "ком.-ш.")), None, "Бенефисъ г. Макшеева."),
 59: ([("Золото", "ком."), ("Коля мужей", "ком.")], "1389 р. 82 к.", W(("Золото", "ком."), ("Школа мужей", "ком.")), None, None),
 65: ([("Кая судьбина", "др."), ("Вовѣтріе", "ком.-ш.")], "1353 р. 36 к.", W(("Горькая судьбина", "др."), ("Повѣтріе", "ком.-ш.")), None, None),
 81: ([("На порогѣ къ дѣлу", "сц."), ("Вѣрь", "ком.")], "414 р. 60 к.", W(("На порогѣ къ дѣлу", "сц."), ("Вѣеръ", "ком.")), None, None),
 86: ([("Золото", "ком.")], "1375 р. 60 к.", W(("Золото", "ком."), ("Школа мужей", "ком.")), None, None)}
for s, (ow, orc, nw, nrc, ann) in FIX.items():
    S = d["sessions"][s - 1]
    assert [(w["work_title"], w.get("genre")) for w in S["works"]] == ow and S["receipts_text"] == orc, (s, S)
    S["works"] = nw
    if nrc: S["receipts_text"] = nrc
    if ann: S["annotation"] = ann
    S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + "scan 2026-10-27: 1894-95 pp. 8-9 Moscow read"
    print(s, S["date_text"], S["session"], S["theater"], [w["work_title"] for w in nw], S["receipts_text"], S.get("annotation") or "")
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
