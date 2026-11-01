"""1902-03 Repertoire title audit. The blind read of every column (docs/eval/scan_audit/1902-03_scan_reads.csv) was compared
word by word with the stored works: 194 cells differed, 154 in punctuation only (no change). The other 40 were read on
ForUpload_1902-03_Repertoire.pdf (page index = pNNN) by two readers, the second blind to the stored text; readings and verdicts
in docs/eval/scan_audit/1902-03_title_reads.csv (column n = the number used below). RG 2026-10-31: "Yes, apply all 34".

Kinds of fix (34 cells):
- a printed item lost: 15 Nov Малый «Да здравствуетъ жизнь! др. / Разводъ, ком.-шут.» (stored as one work with «др.» in the
  title and «Разводъ»'s genre); «Разводъ» appended as the second work (APPEND);
- excerpt wording lost or the excerpt given the parent's genre: 2 Oct, 9 Oct, 23 Oct Новый; 8 Apr Большой; 14 Dec, 29 Jan, 7 Mar
  Маріинскій. Printed phrase restored, genre none (the project's excerpt convention), unless a genre is printed after the excerpt
  (14 Dec «1-е д. бал. Дочь Микадо, бал.»); excerpt wording removed from the annotations that held it (ANN);
- genre doubled into the title by the extraction: «Сильные и слабые, пьеса.» ×2, «Не въ свои сани не садись, ком», «Закатъ, очерки.»;
- letters misread: «Лишеннный», «Le bougeois»/«Le bourgeois» (printed «Le bougeoir» ×4), «Флаксманъ» where the Moscow column
  prints «Флахсманъ» (×4; the SP columns print «Флаксманъ»); genres «вт.» (printed «эт.»), «этюдь» («этюдъ»), «возм. случаи.»
  («возм. случай.»);
- misprints the extraction had silently corrected, stored as printed (genuine_print_typos.md): «Мнссъ», «Сильные п слабыс»,
  «Бѣдность пе порокъ», «Морякъ Скпталецъ», «Конекъ-Горбунокч», «Воспитателъ», «Дивертиссемемтъ», «ccm.», «Les deux écolés»,
  «Don Juan d'Antriche», «Le depit amoureux», «Les précieuses riducules».
Not changed: «ист.-был.», «Deutsche», «vand.», 23 Nov heading-only event (stored right); 2 Jan «Ловнгринъ» (third letter
blotted); 2 Dec «Джентльмэнъ» (separate RG question). Rows keep their places; no event_id or performance order changes
(the 15 Nov item is appended at the end of its event).

uv run python docs/eval/reconciliation/fix_1902_03_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-31 (1902-03 title audit, scan_audit/1902-03_title_reads.csv"

# (n, page, session index, work index, (old title, old genre), (new title, new genre))
FIX = [
    (1, 'p005', 24, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (2, 'p005', 29, 0, ('1-е и 2-е д. Коппелія', 'бал.'), ('1-е и 2-е д., бал. Коппелія', None)),
    (3, 'p007', 24, 0, ('2-я карт. 2-го д. оп. Евгеній Онѣгинъ', 'оп.'), ('2-я карт. 2-го д. оп. Евгеній Онѣгинъ', None)),
    (3, 'p007', 24, 2, ('4-е д. оп. Ромео и Джульетта', 'оп.'), ('4-е д. оп. Ромео и Джульетта', None)),
    (4, 'p009', 25, 1, ('5-я карт. бал. Дочь Фараона', 'бал.'), ('5-я карт. бал. Дочь Фараона', None)),
    (4, 'p009', 25, 2, ('Дивертиссементъ', None), ('Дивертиссемемтъ', None)),
    (5, 'p009', 14, 0, ('Женская логика (Миссъ Гоббсъ)', 'ком.'), ('Женская логика (Мнссъ Гоббсъ)', 'ком.')),
    (6, 'p009', 15, 0, ('Сильные и слабые', 'пьеса'), ('Сильные п слабыс', 'пьеса')),
    (7, 'p013', 11, 0, ('Да здравствуетъ жизнь! др.', 'ком.-шут.'), ('Да здравствуетъ жизнь!', 'др.')),
    (9, 'p017', 35, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (10, 'p019', 20, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (11, 'p019', 28, 1, ('Волшебные звуки', 'этюдь'), ('Волшебные звуки', 'этюдъ')),
    (12, 'p019', 32, 0, ('Бѣдность не порокъ', 'ком.'), ('Бѣдность пе порокъ', 'ком.')),
    (13, 'p021', 22, 0, ('Сильные и слабые, пьеса.', 'пьеса'), ('Сильные и слабые', 'пьеса')),
    (14, 'p031', 9, 0, ('Евгеній Онѣгинъ', 'оп.'), ('2-я карт. 2-го д. оп. Евгеній Онѣгинъ', None)),
    (14, 'p031', 9, 1, ('Конекъ-горбунокъ', 'бал.'), ('7-я и 11-я карт. бал. Конекъ-горбунокъ', None)),
    (15, 'p033', 0, 0, ('Не въ свои сани не садись, ком', 'ком.'), ('Не въ свои сани не садись', 'ком.')),
    (16, 'p033', 21, 0, ('Морякъ Скиталецъ', 'оп.'), ('Морякъ Скпталецъ', 'оп.')),
    (17, 'p035', 11, 0, ('Сильные и слабые, пьеса.', 'пьеса'), ('Сильные и слабые', 'пьеса')),
    (18, 'p035', 7, 2, ('1-е д. бал. Конекъ-Горбунокъ', None), ('1-е д. бал. Конекъ-Горбунокч', None)),
    (19, 'p035', 17, 0, ('Закатъ, очерки.', 'очерки'), ('Закатъ', 'очерки')),
    (20, 'p000', 23, 0, ('Лишеннный правъ', 'пьеса'), ('Лишенный правъ', 'пьеса')),
    (21, 'p008', 38, 0, ('Le bougeois', 'com.'), ('Le bougeoir', 'com.')),
    (22, 'p008', 39, 0, ('Le bougeois', 'com.'), ('Le bougeoir', 'com.')),
    (23, 'p010', 27, 0, ('Le bourgeois', 'com.'), ('Le bougeoir', 'com.')),
    (24, 'p010', 29, 0, ('Le bourgeois', 'com.'), ('Le bougeoir', 'com.')),
    (25, 'p010', 38, 0, ('De 1 h. à 3 h.', 'com.'), ('De 1 h. à 3 h.', 'ccm.')),
    (27, 'p016', 7, 0, ('Жизнь за Царя', 'оп.'), ('1-е д. оп. Жизнь за Царя', None)),
    (27, 'p016', 7, 1, ('Дочь Микадо', 'бал.'), ('1-е д. бал. Дочь Микадо', 'бал.')),
    (28, 'p016', 22, 1, ('Великая тайна', 'вт.'), ('Великая тайна', 'эт.')),
    (29, 'p018', 39, 0, ("Don Juan d'Autriche", 'com.'), ("Don Juan d'Antriche", 'com.')),
    (30, 'p018', 30, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитателъ Флаксманъ', 'ком.')),
    (33, 'p022', 24, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (34, 'p022', 26, 0, ('Les deux écoles', 'com.'), ('Les deux écolés', 'com.')),
    (35, 'p022', 35, 2, ('Le dépit amoureux', 'com.'), ('Le depit amoureux', 'com.')),
    (35, 'p022', 35, 3, ('Fragments de: «Gil Blas de Santillane», «Bavardes du Mercure galant», «Les précieuses ridicules»', 'com.'),
                        ('Fragments de: «Gil Blas de Santillane», «Bavardes du Mercure galant», «Les précieuses riducules»', 'com.')),
    (36, 'p024', 2, 0, ('Карменъ', 'оп.'), ('1-е д. оп. Карменъ', None)),
    (36, 'p024', 2, 1, ('Пиковая дама', 'оп.'), ('2-я карт. 2-го д. оп. Пиковая дама', None)),
    (36, 'p024', 2, 2, ('Самсонъ и Далила', 'оп.'), ('2-е д. оп. Самсонъ и Далила', None)),
    (36, 'p024', 2, 3, ('Аида', 'оп.'), ('1-я карт. 4-го д. оп. Аида', None)),
    (37, 'p028', 7, 0, ('Горе отъ ума', None), ('1-е, 2-е и 4-е д. ком. Горе отъ ума', None)),
    (40, 'p034', 14, 1, ('Наканунѣ', 'возм. случаи.'), ('Наканунѣ', 'возм. случай.')),
]
# Same slip as #7 on the next three Малый events of the play (18, 22, 25 Nov; blind read «Да здравствуетъ жизнь! др.», as on its
# 30 other dates): the extraction put the genre in the title and left the genre empty. Split out when #7 was applied, because
# the shared work had taken its genre (and so its discipline) from #7 alone. Text unchanged.
EXTRA = [
    ('7a', 'p013', 14, 0, ('Да здравствуетъ жизнь! др.', None), ('Да здравствуетъ жизнь!', 'др.')),
    ('7b', 'p013', 17, 0, ('Да здравствуетъ жизнь! др.', None), ('Да здравствуетъ жизнь!', 'др.')),
    ('7c', 'p013', 20, 0, ('Да здравствуетъ жизнь! др.', None), ('Да здравствуетъ жизнь!', 'др.')),
]
# (n, page, session index, (old annotation, new annotation)): excerpt wording moved back to the works
ANN = [
    (14, 'p031', 9, ('Спектакль въ пользу Иверской Общины Краснаго Креста. 2-я карт. 2-го д. оп. Евгеній Онѣгинъ. 7-я и 11-я карт. бал. Конекъ-горбунокъ.',
                     'Спектакль въ пользу Иверской Общины Краснаго Креста.')),
    (27, 'p016', 7, ('Спектакль по случаю 100-лѣтняго юбилея Пажескаго Его Императорскаго Величества корпуса. 1-е д. оп. Жизнь за Царя. 1-е д. бал. Дочь Микадо, бал.',
                     'Спектакль по случаю 100-лѣтняго юбилея Пажескаго Его Императорскаго Величества корпуса.')),
    (36, 'p024', 2, ('Бенефисъ г-жи Славиной (за 25-ти-лѣтнюю службу). 1-е д. оп. Карменъ. 2-я карт. 2-го д. оп. Пиковая дама. 2-е д. оп. Самсонъ и Далила. 1-я карт. 4-го д. оп. Аида.',
                     'Бенефисъ г-жи Славиной (за 25-ти-лѣтнюю службу).')),
    (37, 'p028', 7, ('Спектакль въ пользу Отдѣла защиты дѣтей отъ жестокаго обращенія. 1-е, 2-е и 4-е д. ком.',
                     'Спектакль въ пользу Отдѣла защиты дѣтей отъ жестокаго обращенія.')),
]
# (n, page, session index, works expected after FIX, item appended, note)
APPEND = [
    (7, 'p013', 11, [('Да здравствуетъ жизнь!', 'др.')], ('Разводъ', 'ком.-шут.'),
     "«Разводъ, ком.-шут.» is the second printed line; the extraction had dropped the title and given its genre to the first play"),
]


def load(pg):
    p = RAW / f"repertoire_1902-03_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + msg


pages = {}
for n, pg, i, j, old, new in FIX + EXTRA:
    if pg not in pages: pages[pg] = load(pg)
    S = pages[pg][1]["sessions"][i]; w = S["works"][j]
    assert (w["work_title"], w.get("genre")) == old, (n, pg, i, j, w, old)
    w["work_title"], w["genre"] = new
    note(S, f"{TAG} #{n}): work {j + 1} «{old[0]}» / {old[1]!r} -> «{new[0]}» / {new[1]!r}")
for n, pg, i, (old, new) in ANN:
    S = pages[pg][1]["sessions"][i]
    assert S.get("annotation") == old, (n, S.get("annotation"))
    S["annotation"] = new; note(S, f"{TAG} #{n}): annotation «{old}» -> «{new}» (excerpt wording moved back to the works)")
for n, pg, i, works, item, why in APPEND:
    S = pages[pg][1]["sessions"][i]
    assert [(w["work_title"], w.get("genre")) for w in S["works"]] == works, (n, S["works"])
    S["works"].append({"work_title": item[0], "genre": item[1]})
    note(S, f"{TAG} #{n}): {why}; appended")
assert len({x[0] for x in FIX}) == 34, sorted({x[0] for x in FIX})
if "--write" in sys.argv:
    for p, d, f in pages.values():
        p.write_text(json.dumps(d, indent=f[0], ensure_ascii=f[1]) + f[2], encoding="utf-8")
print(len({x[0] for x in FIX}), "cells,", len(FIX), "works,", len(EXTRA), "extra,", len(ANN), "annotations,", len(APPEND), "appended,", len(pages), "pages;",
      "WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
