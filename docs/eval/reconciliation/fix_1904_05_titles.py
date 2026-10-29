"""1904-05 Repertoire title audit (RG 2026-10-29: "Yes, apply"). The blind read of every column
(docs/eval/scan_audit/1904-05_scan_reads.csv) was compared word by word with the stored works; the 57 cells that
differed were read by Claude on ForUpload_1904-05_Repertoire.pdf (page index = pNNN). Readings and verdicts:
docs/eval/scan_audit/1904-05_title_reads.csv (column n = the number used below). 49 cells change here; 8 were
already right (Карѳагенѣ x3, Жаннина x4, the misprint «Ou n'oublie pas»).

Kinds of fix:
- letters the extraction got wrong or modernised (Бѣшеныя, событіе, Мертвыя, лѣтняя, Валкирія, Далила, Лакмэ,
  Безприданница, Потокъ, проказницы, соверш.); worn type read as the letter present (com., Bellaggio);
- excerpt wording lost on three charity bills (8 Apr, 6 Apr, 16 Feb): printed phrase restored, genre none
  (the project's excerpt convention);
- genre run into the title split off; «nouv.» restored to French genres; genres the print does not give removed;
- misprints stored as printed (genuine_print_typos.md): «Конскъ-Горбуновъ» (30 Dec), «Коневъ-Горбунокъ» (25 Feb),
  «соверш,» (1 Jan).
Rows keep their places; no event_id or performance order changes. Terminal punctuation is dropped, as elsewhere.

uv run python docs/eval/reconciliation/fix_1904_05_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-29 (1904-05 title audit, scan_audit/1904-05_title_reads.csv"
N = None  # placeholder for "no genre"

# n: (page, session index, date_text, [(work index, (old_title, old_genre), (new_title, new_genre))], annotation change)
FIX = {
 1: ("p000", 12, "30 Понед.", [(0, ("Въ 1-й разъ по возобновленіи Виндзорскія промазницы", "ком."),
                                  ("Виндзорскія проказницы", "ком."))], (None, "Въ 1-й разъ по возобновленіи")),
 2: ("p003", 5, None, [(0, ("Лакма", "оп."), ("Лакмэ", "оп."))], None),
 3: ("p003", 31, None, [(0, ("Мертвые души", "сц."), ("Мертвыя души", "сц."))], None),
 4: ("p003", 33, None, [(1, ("Ночное, лѣтния сцена", N), ("Ночное, лѣтняя сцена", N))], None),
 5: ("p006", 14, None, [(0, ("Le nuage", "c.m."), ("Le nuage", "com."))], None),
 6: ("p008", 26, None, [(0, ("L'ami de la maison, com. nouv.", "com."), ("L'ami de la maison", "com. nouv."))], None),
 7: ("p008", 28, None, [(0, ("L'ami de la maison, com. nouv.", "com."), ("L'ami de la maison", "com. nouv."))], None),
 8: ("p008", 30, None, [(0, ("L'ami de la maison, com. nouv.", "com."), ("L'ami de la maison", "com. nouv."))], None),
 9: ("p008", 36, None, [(1, ("Великая тайна, этюдъ.", "этюдъ"), ("Великая тайна", "этюдъ"))], None),
 13: ("p015", 33, None, [(0, ("Беаприданница", "др."), ("Безприданница", "др."))], None),
 15: ("p016", 33, None, [(0, ("Les roses de Bellagio", "com. nouv."), ("Les roses de Bellaggio", "com. nouv."))], None),
 16: ("p017", 12, None, [(0, ("Бѣшеные деньги", "ком."), ("Бѣшеныя деньги", "ком."))], None),
 17: ("p017", 13, None, [(2, ("Женитьба", "соверш. невѣр. событие"), ("Женитьба", "соверш. невѣр. событіе"))], None),
 18: ("p017", 18, None, [(0, ("Женитьба", "соверш. нев. событие"), ("Женитьба", "соверш. нев. событіе"))], None),
 19: ("p018", 1, None, [(1, ("2-я карт. бал. „Брама“", "бал."), ("2-я карт. бал. „Брама“", N))], None),
 20: ("p018", 6, None, [(0, ("Валкірія", "оп."), ("Валкирія", "оп."))], None),
 21: ("p018", 11, None, [(0, ("Валкірія", "оп."), ("Валкирія", "оп."))], None),
 25: ("p019", 11, None, [(0, ("Женитьба, совершенно невѣроятное событіе", "ком."),
                          ("Женитьба, совершенно невѣроятное событіе", N))], None),
 26: ("p019", 18, None, [(0, ("Бѣшеные деньги", "ком."), ("Бѣшеныя деньги", "ком."))], None),
 27: ("p019", 26, None, [(0, ("Потомъ", "др."), ("Потокъ", "др."))], None),
 28: ("p021", 10, None, [(0, ("Конекъ-Горбунокъ", "бал."), ("Конскъ-Горбуновъ", "бал."))], None),
 29: ("p021", 38, None, [(0, ("Бѣшеные деньги", "ком."), ("Бѣшеныя деньги", "ком."))], None),
 30: ("p021", 18, None, [(0, ("Снѣгурочка, весенн. сказка.", "др."), ("Снѣгурочка", "весенн. сказка"))], None),
 31: ("p021", 30, None, [(0, ("Женитьба, соверш. невѣр. событие", "ком."), ("Женитьба, соверш, невѣр. событіе", "ком."))], None),
 32: ("p022", 9, None, [(0, ("2-я карт. бал. Щелкунчикъ", "бал."), ("2-я карт. бал. Щелкунчикъ", N))], None),
 33: ("p022", 14, None, [(0, ("Крылья связаны, пьеса.", "пьеса"), ("Крылья связаны", "пьеса"))], None),
 34: ("p022", 17, None, [(0, ("Крылья связаны, пьеса.", "пьеса"), ("Крылья связаны", "пьеса"))], None),
 35: ("p023", 11, None, [(0, ("Бѣшеные деньги", "ком."), ("Бѣшеныя деньги", "ком."))], None),
 36: ("p023", 19, None, [(0, ("Бѣшеные деньги", "ком."), ("Бѣшеныя деньги", "ком."))], None),
 37: ("p023", 20, None, [(0, ("Снѣгурочка, весенн. сказка", "сказка"), ("Снѣгурочка", "весенн. сказка"))], None),
 38: ("p023", 26, None, [(0, ("Снѣгурочка, весен. сказка", "сказка"), ("Снѣгурочка", "весен. сказка"))], None),
 39: ("p024", 25, None, [(0, ("L'acquitté", "com."), ("L'acquitté", "com. nouv."))], None),
 40: ("p024", 26, None, [(0, ("Un bain qui chauffe", "com."), ("Un bain qui chauffe", "com. nouv."))], None),
 41: ("p024", 27, None, [(0, ("L'acquitté", "com."), ("L'acquitté", "com. nouv."))], None),
 42: ("p024", 28, None, [(0, ("Un bain qui chauffe", "com."), ("Un bain qui chauffe", "com. nouv."))], None),
 43: ("p024", 30, None, [(0, ("L'acquitté", "com."), ("L'acquitté", "com. nouv."))], None),
 44: ("p026", 1, None, [(1, ("2 карт. 1 д. бал. Лебединое озеро", "бал."), ("2 карт. 1 д. бал. Лебединое озеро", N)),
                        (2, ("3 д. бал. Пахита", "бал."), ("3 д. бал. Пахита", N))], None),
 45: ("p027", 8, None, [(0, ("Боярыня Вѣра Шелога, прологъ", "оп."), ("Боярыня Вѣра Шелога", "прологъ"))], None),
 46: ("p029", 11, None, [(1, ("1, 2 и 3 карт. оп. Евгеній Онѣгинъ", "оп."), ("1, 2 и 3 карт. оп. Евгеній Онѣгинъ", N)),
                        (2, ("2 карт. 1 д. Борисъ Годуновъ", "оп."), ("2 карт. 1 д. Борисъ Годуновъ", N))], None),
 47: ("p029", 22, None, [(0, ("Женитьба", "совершен. нев. событіе."), ("Женитьба", "соверш. нев. событіе."))], None),
 48: ("p031", 3, None, [(0, ("Макбетъ", "траг."), ("4 сц. 1 д. тр. Макбетъ", N)),
                       (1, ("Гамлетъ", "оп."), ("сц. 4 д. оп. Гамлетъ", N)),
                       (2, ("Фіаметта", "бал."), ("2 д. бал. Фіаметта", N))],
     ("Въ пользу убѣжища для престарѣлыхъ артистовъ и ихъ семействъ. 4 сц. 1 д. тр. Макбетъ. сц. 4 д. оп. Гамлетъ. "
      "2 д. бал. Фіаметта.", "Въ пользу убѣжища для престарѣлыхъ артистовъ и ихъ семействъ.")),
 50: ("p033", 5, None, [(1, ("11-я карт. бал. Конекъ-Горбунокъ", "бал."), ("11-я карт. бал. Коневъ-Горбунокъ", N))], None),
 51: ("p040", 1, None, [(1, ("Наяда и рыбакъ", "бал."), ("Двѣ карт. бал. Наяда и рыбакъ", N)),
                       (2, ("Брама", "бал."), ("Двѣ карт. бал. Брама", N))], None),
 52: ("p040", 3, None, [(0, ("Ромео и Джульетта", "оп."), ("2 актъ оп. Ромео и Джульетта", N)),
                       (1, ("Демонъ", "оп."), ("3 актъ оп. Демонъ", N)),
                       (2, ("Искатели жемчуга", "оп."), ("1 актъ оп. Искатели жемчуга", N)),
                       (3, ("Лакмё", "оп."), ("Сцена 2 акта оп. Лакме", N))], None),
 53: ("p040", 21, None, [(0, ("Le marché", "com."), ("Le marché", "com. nouv.")),
                        (1, ("Que Suzanne n'en sache rien", "com."), ("Que Suzanne n'en sache rien", "com. nouv."))], None),
 54: ("p040", 23, None, [(0, ("Le marché", "com."), ("Le marché", "com. nouv.")),
                        (1, ("Que Suzanne n'en sache rien", "com."), ("Que Suzanne n'en sache rien", "com. nouv."))], None),
 55: ("p041", 20, None, [(0, ("Поросль, пьеса.", "пьеса"), ("Поросль", "пьеса"))], None),
 56: ("p042", 13, None, [(0, ("Самсонъ и Даліла", "оп."), ("Самсонъ и Далила", "оп."))], None),
 57: ("p042", 15, None, [(2, ("3 д. бал. Пахита", "бал."), ("3 д. бал. Пахита", N))], None),
}


def load(pg):
    p = RAW / f"repertoire_1904-05_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


pages = {}
changed = 0
for n, (pg, i, dtext, works, ann) in sorted(FIX.items()):
    if pg not in pages:
        pages[pg] = load(pg)
    S = pages[pg][1]["sessions"][i]
    if dtext:
        assert S["date_text"] == dtext, (n, S["date_text"])
    msgs = []
    for wi, (ot, og), (nt, ng) in works:
        W = S["works"][wi]
        assert (W["work_title"], W.get("genre")) == (ot, og), (n, wi, W)
        W["work_title"], W["genre"] = nt, ng
        msgs.append(f"«{ot}» / {og!r} -> «{nt}» / {ng!r}")
        changed += 1
    if ann:
        old, new = ann
        assert S.get("annotation") == old, (n, S.get("annotation"))
        S["annotation"] = new
        msgs.append(f"annotation {old!r} -> {new!r}")
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG} n={n}): " + "; ".join(msgs)
    print(n, pg, i, "; ".join(msgs))

if "--write" in sys.argv:
    for pg, (p, d, fmt) in pages.items():
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(f"{len(FIX)} cells, {changed} works,", "WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
