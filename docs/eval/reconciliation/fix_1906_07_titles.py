"""1906-07 Repertoire title audit. The blind read of every column (docs/eval/scan_audit/1906-07_scan_reads.csv) was
compared word by word with the stored works; the 39 cells that differed, plus 2 found by grouping (the «Le bonheur,
mesdames» split), were read again from ForUpload_1906-07_Repertoire.pdf (page index = pNNN) by a second reader that saw
neither version, and the disputed ones by Claude. Readings and verdicts: docs/eval/scan_audit/1906-07_title_reads.csv
(column n = the number used below). 39 cells change here; 2 were already right (n6 numbering only; n12 «bonhomme»).

Kinds of fix:
- letters the extraction got wrong or modernised: Факелъ (x7), Мелентьева (x4), Валкирія (x3), Димитрій (x2 cells),
  денщика, declarer, piéce, coeur;
- titles split or run together at a comma: «Le bonheur, mesdames» (x4), «Le coeur d'Angélique» [com.],
  «Боярыня Вѣра Шелога» [прологъ / прол.] (x3);
- genres the print does not give removed («Драма жизни» x2, «Le cultivateur de Chicago», two «Конекъ-Горбунокъ» acts),
  or given wrong («Miquette et sa mère» pièce, «Женитьба» соверш. невѣроятн. событіе);
- 22 Dec «Гугеноты»: the act prefix «1, 2, 3 и 4 д. оп.» restored (excerpt convention, genre none);
- 4 Mar: «J'attends Ernest, com.» was stored as the annotation; it is the bill's first work;
- misprints stored as printed (genuine_print_typos.md): «Пиковая дамя» (26 Dec), «Велшебное зеркало» (29 Apr).
Rows keep their places; only n19 adds a work (at the front, as printed: «Le marquis de Priola» moves to __w2).

uv run python docs/eval/reconciliation/fix_1906_07_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-30 (1906-07 title audit, scan_audit/1906-07_title_reads.csv"
N = None
F = "Факель въ тайникѣ", "тр."
FF = "Факелъ въ тайникѣ", "тр."
V = "Василиса Мелентьевна", "др."
VV = "Василиса Мелентьева", "др."
W = "Валкірія", "оп."
WW = "Валкирія", "оп."

# n: (page, session index, date_text, [(work index, (old_title, old_genre), (new_title, new_genre))])
FIX = {
 1: ("p020", 22, "22 Пятница.", [(0, ("«Гугеноты»", "оп."), ("1, 2, 3 и 4 д. оп. «Гугеноты»", N))]),
 2: ("p022", 1, "26 Вторн.", [(0, ("Пиковая дама", "оп."), ("Пиковая дамя", "оп."))]),
 3: ("p038", 0, "20 Вторн.", [(0, W, WW)]),
 4: ("p038", 3, "21 Среда", [(0, W, WW)]),
 5: ("p038", 9, "23 Пятница", [(0, W, WW)]),
 7: ("p004", 4, "21 Четвергъ.", [(0, ("5-е д. тр. Дмитрій Самозванецъ", N), ("5-е д. тр. Димитрій Самозванецъ", N)),
                                 (2, ("2 послѣднія дѣйствія трагедіи Дмитрій Донской", N),
                                     ("2 послѣднія дѣйствія трагедіи Димитрій Донской", N))]),
 8: ("p014", 20, "19 Воскрес.", [(0, ("5-е д. тр. Дмитрій Самозванецъ", N), ("5-е д. тр. Димитрій Самозванецъ", N))]),
 9: ("p034", 17, "3 Суббота", [(1, ("День денищика Душкина", "ком."), ("День денщика Душкина", "ком."))]),
 10: ("p006", 9, "3 Вторн.", [(1, ("Le bonheur", "mesdames"), ("Le bonheur, mesdames", "com."))]),
 11: ("p006", 15, "5 Четвергъ", [(1, ("Le bonheur", "mesdames"), ("Le bonheur, mesdames", "com."))]),
 13: ("p018", 8, "6 Среда.", [(0, ("Paraître", "pièce"), ("Paraître", "piéce"))]),
 14: ("p026", 25, "23 Вторн.", [(0, ("Le coeur d'Angélique com.", "com."), ("Le coeur d'Angélique", "com."))]),
 15: ("p026", 28, "24 Среда", [(1, ("Vous n'avez rien à déclarer", "vaud."), ("Vous n'avez rien à declarer", "vaud."))]),
 16: ("p030", 8, "8 Четвергъ", [(1, ("Miquette et sa mère", "com."), ("Miquette et sa mère", "pièce"))]),
 17: ("p032", 2, "17 Суббота", [(0, ("Le cultivateur de Chicago", "com."), ("Le cultivateur de Chicago", N))]),
 18: ("p034", 13, "2 Пятница", [(0, ("Le cœur d'Angélique", "com."), ("Le coeur d'Angélique", "com."))]),
 20: ("p048", 0, "13 Воскр.", [(0, ("Драма жизни", "др."), ("Драма жизни", N))]),
 21: ("p048", 2, "15 Вторн.", [(0, ("Драма жизни", "др."), ("Драма жизни", N))]),
 22: ("p001", 13, "3 Воскрес.", [(0, ("6-я карт. бал. Конекъ-Горбунокъ", "бал."), ("6-я карт. бал. Конекъ-Горбунокъ", N))]),
 23: ("p011", 22, "30 Понед.", [(0, ("Боярыня Вѣра Шелога, прологъ", "оп."), ("Боярыня Вѣра Шелога", "прологъ"))]),
 24: ("p013", 0, "3 Пятница.", [(0, ("Боярыня Вѣра Шелога, прол.", "оп."), ("Боярыня Вѣра Шелога", "прол."))]),
 25: ("p013", 22, "10 Пятница.", [(0, ("Боярыня Вѣра Шелога, прологъ", "оп."), ("Боярыня Вѣра Шелога", "прологъ"))]),
 26: ("p023", 3, "27 Среда.", [(0, ("3-е д. бал. Конекъ-Горбунокъ", "бал."), ("3-е д. бал. Конекъ-Горбунокъ", N))]),
 27: ("p045", 22, "29 Воскрес.", [(1, ("4-е д. бал. Волшебное зеркало", N), ("4-е д. бал. Велшебное зеркало", N))]),
 28: ("p015", 2, "14 Вторн.", [(0, ("Женитьба", "ком."), ("Женитьба", "соверш. невѣроятн. событіе"))]),
 29: ("p003", 24, "16 Суббота.", [(0, V, VV)]),
 30: ("p009", 15, "16 Понед.", [(0, V, VV)]),
 31: ("p017", 34, "4 Понед.", [(0, V, VV)]),
 32: ("p031", 11, "9 Пятница", [(0, F, FF)]),
 33: ("p031", 21, "12 Понед.", [(0, F, FF)]),
 34: ("p031", 30, "15 Четвергъ", [(0, F, FF)]),
 35: ("p033", 2, "17 Суббота.", [(0, F, FF)]),
 36: ("p033", 12, "20 Вторн.", [(0, F, FF)]),
 37: ("p033", 18, "22 Четвергъ.", [(0, F, FF)]),
 38: ("p033", 31, "26 Понед.", [(0, F, FF)]),
 39: ("p045", 21, "28 Суббота", [(0, V, VV)]),
 40: ("p004", 33, "30 Суббота.", [(1, ("Le bonheur", "mesdames."), ("Le bonheur, mesdames", N))]),
 41: ("p006", 3, "1 Воскрес.", [(1, ("Le bonheur", "mesdames."), ("Le bonheur, mesdames", N))]),
}


def load(pg):
    p = RAW / f"repertoire_1906-07_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + msg


pages, n_works = {}, 0
for n, (pg, i, dtext, works) in sorted(FIX.items()):
    if pg not in pages:
        pages[pg] = load(pg)
    S = pages[pg][1]["sessions"][i]
    assert S["date_text"] == dtext, (n, S["date_text"], dtext)
    for wi, (ot, og), (nt, ng) in works:
        w = S["works"][wi]
        assert (w["work_title"], w["genre"]) == (ot, og), (n, wi, w)
        w["work_title"], w["genre"] = nt, ng
        n_works += 1
    note(S, f"{TAG} n{n}): " + "; ".join(f"«{ot}» [{og}] -> «{nt}» [{ng}]" for _, (ot, og), (nt, ng) in works))

# n19: 4 Mar 1907 Михайловскій: «J'attends Ernest, com.» printed as the first work, stored as the annotation
pg = "p034"
if pg not in pages:
    pages[pg] = load(pg)
S = pages[pg][1]["sessions"][23]
assert S["date_text"] == "4 Воскрес." and S["annotation"] == "J'attends Ernest, com.", S
assert [(w["work_title"], w["genre"]) for w in S["works"]] == [("Le marquis de Priola", "com.")], S
S["works"].insert(0, {"work_title": "J'attends Ernest", "genre": "com."})
S["annotation"] = None
note(S, f"{TAG} n19): annotation «J'attends Ernest, com.» -> work 1 «J'attends Ernest» [com.]; annotation cleared")
n_works += 1

for pg, (p, d, fmt) in pages.items():
    if "--write" in sys.argv:
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(f"{len(FIX) + 1} cells, {n_works} works, {len(pages)} pages;", "WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
