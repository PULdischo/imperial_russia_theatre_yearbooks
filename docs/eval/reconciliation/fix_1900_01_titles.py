"""1900-01 Repertoire title audit. The blind read of every column (docs/eval/scan_audit/1900-01_scan_reads.csv) was compared
word by word with the stored works: 279 cells differed, 213 in punctuation only (no change). Of the other 66, 6 were pairing
artefacts of unlabelled split cells (6 Dec, 7 Feb); the remaining 60 were read again blind by a second agent that saw neither
version, and the doubtful ones by Claude (docs/eval/scan_audit/1900-01_title_reads.csv; n = the number used below).
Claude read n12, n36, n50, n53, n57 on the crops: n57 «Лебединое» and n50 «Фіамметта» are stored right (one reader wrong each).

Kinds of fix:
- letters the extraction got wrong or modernised: «Сорренто» (stored «Корренто»), «предпріятіе», «Лоэнгринъ» ×2 (stored «Ловнгринъ»),
  «Бѣдность» («Вѣдность»), «Свѣтитъ, да не грѣетъ» ×4, «За обѣдомъ» ×3 («объѣдомъ»), «Именины» («Именныя»), «Юдиѳь» ×3,
  «Девятый валъ» («вальс»), «Джентльмэнъ»; genres «эт.» ×2 («вт.»), «этюдъ» ×2 («втюдъ»), «карт.» («март.»), «ком.» («ном.»);
- genre the print does not give on an excerpt: 18 Oct «2-е д. оп. Севильскій цирюльникъ.» (stored with «оп.»);
- excerpt wording lost (ballet): the printed «2-е д. бал. …», «1-е д. бал. …», «4-я карт. бал. …», «2-я карт. 2-го дѣйств. бал. …»
  restored on 8 cells (11 works), genre none (the project's excerpt convention, as 1899-00 and 1901-02);
- misprints stored as printed (genuine_print_typos.md; titles aliased in work_title_aliases.csv): «Жизнь аз Царя», «Гамлстѣ»,
  «Le Misantrope», «Trois femmes ponr un mari», «Les éléves de Dupré», «Die Zwillingschwester» ×2; genres «весенная сказка»,
  «цьеса», «Schausptel», «piecè». n12 (Малый 30 Jan «Шутники, вартина.») is NOT changed: two readers saw «картина»/«еартина», but at full resolution
  Claude reads в (straight stem, two bowls), as the 2026-09-28 zoom did (genuine_print_typos.md); stored «вартина» is the print;
- printed items missing from the works (APPEND, at the end of the session so no performance order shifts): 17 Oct and 28 Nov
  Александринскій «Не бывать-бы счастью, да несчастье помогло, оперет.»; 9 Feb «Я играю большую роль!, шут.»; 6 Jan Малый
  «Концертное отдѣленіе.» + «Балетный дивертиссементъ.»; 28 Feb and 2 Mar Маріинскій «Концертное отдѣленіе.» (as 1901-02, RG: items
  printed in the item face are works);
- 28 Oct Маріинскій (Sonnenthal): «Der Hüttenbesitzer, Schauspiel.» moved from the annotation to works (STRUCT, as 1901-02 2 Feb).
Not changed: n13/n14 (Новый 5, 6 Feb) print «Школьные товарищи» first, stored second — order left for RG (no order changes here);
n19 (7 Apr) and n43 («Вѣнская оперетка.») are headings, already in the annotation.

uv run python docs/eval/reconciliation/fix_1900_01_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-30 (1900-01 title audit, scan_audit/1900-01_title_reads.csv"

SV_OLD = ("Свѣтить, да не грѣть", "др."); SV_NEW = ("Свѣтитъ, да не грѣетъ", "др.")
# (n, page, day, theater prefix, (old title, old genre), (new title, new genre))
FIX = [
    (1, "p007", "18", "Больш", ("2-е д. оп. Севильскій цирюльникъ", "оп."), ("2-е д. оп. Севильскій цирюльникъ", None)),
    (2, "p013", "16", "Малый", ("Вечеръ въ Корренто", "сц."), ("Вечеръ въ Сорренто", "сц.")),
    (3, "p017", "6", "Больш", ("Жизнь за Царя", "оп."), ("Жизнь аз Царя", "оп.")),
    (5, "p017", "8", "Малый", ("Выгодное предприятіе", "ком."), ("Выгодное предпріятіе", "ком.")),
    (6, "p017", "11", "Больш", ("Ловнгринъ", "оп."), ("Лоэнгринъ", "оп.")),
    (7, "p017", "14", "Больш", ("Ловнгринъ", "оп."), ("Лоэнгринъ", "оп.")),
    (8, "p019", "27", "Новый", ("Вѣдность не порокъ", "ком."), ("Бѣдность не порокъ", "ком.")),
    (9, "p021", "31", "Новый", ("Волшебные звуки", "вт."), ("Волшебные звуки", "эт.")),
    (11, "p021", "10", "Новый", ("Волшебные звуки", "вт."), ("Волшебные звуки", "эт.")),
    (17, "p027", "9", "Больш", ("Донъ-Кихотъ Ламанчскій", "бал."), ("1-е д. бал. Донъ-Кихотъ Ламанчскій", None)),
    (18, "p027", "10", "Новый", ("Снѣгурочка", "весенняя сказка"), ("Снѣгурочка", "весенная сказка")),
    (20, "p033", "8", "Больш", ("Звѣзды", "бал."), ("2-я карт. 2-го дѣйств. бал. Звѣзды", None)),
    (21, "p035", "22", "Больш", ("Звѣзды", "бал."), ("2-я карт. 2.го д. бал. Звѣзды", None)),
    (22, "p037", "26", "Малый", ("Джентльменъ", "ком."), ("Джентльмэнъ", "ком.")),
    (23, "p037", "29", "Больш", ("Корсаръ", "бал."), ("2-е д. бал. Корсаръ", None)),
    (23, "p037", "29", "Больш", ("Донъ-Кихотъ Ламанчскій", "бал."), ("1-е д. бал. Донъ-Кихотъ Ламанчскій", None)),
    (24, "p037", "3", "Малый", ("Шутники", "март."), ("Шутники", "карт.")),
    (25, "p000", "31", "Алекс", SV_OLD[:1] + ("драма.",), SV_NEW[:1] + ("драма.",)),
    (26, "p004", "1", "Алекс", SV_OLD, SV_NEW),
    (29, "p008", "31", "Алекс", ("За объѣдомъ", "шут."), ("За обѣдомъ", "шут.")),
    (30, "p008", "2", "Алекс", ("За объѣдомъ", "шут."), ("За обѣдомъ", "шут.")),
    (31, "p010", "9", "Алекс", ("Именныя въ углахъ", "карт."), ("Именины въ углахъ", "карт.")),
    (32, "p010", "12", "Михай", ("Trois femmes pour un mari", "com."), ("Trois femmes ponr un mari", "com.")),
    (33, "p012", "17", "Алекс", ("За объѣдомъ", "шут."), ("За обѣдомъ", "шут.")),
    (34, "p012", "22", "Алекс", SV_OLD, SV_NEW),
    (36, "p014", "30", "Алекс", ("Трагедія о Гамлетѣ, принцѣ Датскомъ", None), ("Трагедія о Гамлстѣ, принцѣ Датскомъ", None)),
    (38, "p014", "26", "Михай", ("Le Misantrophe", "com."), ("Le Misantrope", "com.")),
    (39, "p014", "27", "Михай", ("Буреломъ", "пьеса"), ("Буреломъ", "цьеса")),
    (40, "p016", "10", "Алекс", ("Честь", "ном."), ("Честь", "ком.")),
    (41, "p020", "3", "Маріи", ("Юдифь", "оп."), ("Юдиѳь", "оп.")),
    (42, "p022", "14", "Маріи", ("Юдифь", "оп."), ("Юдиѳь", "оп.")),
    (44, "p022", "15", "Михай", ("Девятый вальс", "др."), ("Девятый валъ", "др.")),
    (45, "p024", "31", "Мар", ("Юдифь", "оп."), ("Юдиѳь", "оп.")),
    (46, "p026", "4", "Маріи", ("Пахита", "бал."), ("2-е д. бал. Пахита", None)),
    (46, "p026", "4", "Маріи", ("Наяда и рыбакъ", "бал."), ("1-е д. бал. Наяда и рыбакъ", None)),
    (47, "p026", "8", "Маріи", ("Наяда и рыбакъ", "бал."), ("1-е д. бал. Наяда и рыбакъ", None)),
    (48, "p026", "9", "Алекс", SV_OLD, SV_NEW),
    (49, "p026", "10", "Алекс", ("Красный цвѣтокъ", "драм. втюдъ"), ("Красный цвѣтокъ", "драм. этюдъ")),
    (50, "p026", "11", "Маріи", ("Камарго", "бал."), ("4-я карт. бал. Камарго", None)),
    (50, "p026", "11", "Маріи", ("Фіамметта", "бал."), ("2-е д. бал. Фіамметта", None)),
    (50, "p026", "11", "Маріи", ("Щелкунчикъ", "бал."), ("2-е д. бал. Щелкунчикъ", None)),
    (53, "p028", "2", "Михай", ("Les élèves de Dupré", "ballet"), ("Les éléves de Dupré", "ballet")),
    (54, "p028", "11", "Алекс", ("Die Zwillingsschwester", "Lustspiel"), ("Die Zwillingschwester", "Lustspiel")),
    (55, "p028", "12", "Алекс", ("Die Zwillingsschwester", "Lustspiel"), ("Die Zwillingschwester", "Lustspiel")),
    (56, "p030", "17", "Алекс", ("Abschied vom Regiment", "Schauspiel"), ("Abschied vom Regiment", "Schausptel")),
    (58, "p034", "15", "Михай", ("Le député Leveau", "pièce"), ("Le député Leveau", "piecè")),
    (59, "p034", "20", "Михай", ("Красный цвѣтокъ", "драм. втюдъ"), ("Красный цвѣтокъ", "драм. этюдъ")),
    (60, "p036", "6", "Маріи", ("Наяда и рыбакъ", "бал."), ("1-е д. бал. Наяда и рыбакъ", None)),
    (60, "p036", "6", "Маріи", ("Щелкунчикъ", "бал."), ("1-е д. бал. Щелкунчикъ", None)),
]
NB = ("Не бывать-бы счастью, да несчастье помогло", "оперет.")
# (n, page, day, theater prefix, a title already in the session, works to append)
APPEND = [
    (27, "p006", "17", "Алекс", "Девятый валъ", [NB]),
    (35, "p014", "28", "Алекс", "Цѣна жизни", [NB]),
    (48, "p026", "9", "Алекс", "Свѣтитъ, да не грѣетъ", [("Я играю большую роль!", "шут.")]),
    (10, "p021", "6", "Малый", "Провинціалка", [("Концертное отдѣленіе", None), ("Балетный дивертиссементъ", None)]),
    (51, "p028", "28", "Маріи", "Месса Реквіемъ", [("Концертное отдѣленіе", None)]),
    (52, "p028", "2", "Маріи", "Месса-Реквіемъ", [("Концертное отдѣленіе", None)]),
]
STRUCT = (28, "p008", "28", "Маріи", "Der Hüttenbesitzer, Schauspiel.", ("Der Hüttenbesitzer", "Schauspiel"))
# (page, stored date_text, printed date_text, rows): weekday words modernised by the extraction; printed form from the blind read
DATES = [
    ("p000", "31 Четвергь.", "31 Четвергъ.", 3), ("p003", "21 Четвергь.", "21 Четвергъ.", 3),
    ("p004", "2 Понедѣльник.", "2 Понедѣльн.", 3), ("p004", "9 Понедѣльник.", "9 Понедѣльн.", 3),
    ("p005", "28 Четверг.", "28 Четвергъ.", 3), ("p005", "5 Четверг.", "5 Четвергъ.", 3),
    ("p008", "2 Четверг.", "2 Четвергъ.", 3), ("p008", "26 Четверг.", "26 Четвергъ.", 3),
    ("p010", "6 Понедѣльник.", "6 Понедѣльн.", 3), ("p011", "6 Понедѣльник.", "6 Понедѣльн.", 3),
    ("p014", "30 Четверг.", "30 Четвергъ.", 1), ("p014", "30 Четвергь.", "30 Четвергъ.", 2),
    ("p015", "30 Четвергь.", "30 Четвергъ.", 3), ("p017", "14 Четвергь.", "14 Четвергъ.", 1),
    ("p017", "7 Четвергь.", "7 Четвергъ.", 1), ("p019", "21 Четвергь.", "21 Четвергъ.", 1),
    ("p019", "28 Четвергь.", "28 Четвергъ.", 2), ("p023", "18 Четвергь.", "18 Четвергъ.", 3),
    ("p026", "4 Воскре.", "4 Воскре с.", 2), ("p027", "8 Четверг.", "8 Четвергъ.", 4),
    ("p034", "19 Четвергь.", "19 Четвергъ.", 3),
]
# (page, stored theater, printed theater, rows): the column headings print «… театръ.»
THEATERS = [
    ("p003", "Большой театр.", "Большой театръ.", 12), ("p007", "Большой театр.", "Большой театръ.", 12),
    ("p017", "Большой театр.", "Большой театръ.", 12), ("p017", "Новый театр.", "Новый театръ.", 13),
    ("p019", "Малый театр.", "Малый театръ.", 12), ("p019", "Новый театр.", "Новый театръ.", 15),
    ("p021", "Малый театр.", "Малый театръ.", 12), ("p021", "Новый театр.", "Новый театръ.", 14),
    ("p024", "Мариинскій театръ.", "Маріинскій театръ.", 13), ("p029", "Большой театр.", "Большой театръ.", 12),
    ("p033", "Малый театр.", "Малый театръ.", 11),
]

pages = {}


def load(pg):
    if pg in pages:
        return pages[pg]
    p = RAW / f"repertoire_1900-01_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    pages[pg] = (p, d, (ind, ea, tr)); return pages[pg]
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG} {msg})"


def sessions(pg, day, th):
    return [S for S in load(pg)[1]["sessions"] if S["date_text"].split()[0] == day and S["theater"].startswith(th)]


n_works = 0
for n, pg, day, th, old, new in FIX:
    hits = [(S, w) for S in sessions(pg, day, th) for w in S["works"]
            if (w["work_title"], w.get("genre")) == old]
    assert len(hits) == 1, (n, pg, day, th, old, len(hits))
    S, w = hits[0]
    w["work_title"], w["genre"] = new
    note(S, f"n{n}: «{old[0]}, {old[1]}» -> «{new[0]}{', ' + new[1] if new[1] else ''}»")
    n_works += 1
for n, pg, day, th, anchor, add in APPEND:
    hits = [S for S in sessions(pg, day, th) if any(w["work_title"] == anchor for w in S["works"])]
    assert len(hits) == 1, (n, pg, day, th, anchor, len(hits))
    S = hits[0]
    assert not any(w["work_title"] == a[0] for w in S["works"] for a in add), (n, "already there")
    for t, g in add:
        S["works"].append({"work_title": t, "genre": g})
    note(S, f"n{n}: appended " + " + ".join(f"«{t}{', ' + g if g else ''}»" for t, g in add) + " (printed, missing from works)")
    n_works += len(add)
n, pg, day, th, ann, work = STRUCT
hits = [S for S in sessions(pg, day, th) if ann in (S.get("annotation") or "") and not S["works"]]
assert len(hits) == 1, (n, len(hits))
S = hits[0]
S["annotation"] = " ".join(S["annotation"].replace(ann, "").split()) or None
S["works"].append({"work_title": work[0], "genre": work[1]})
note(S, f"n{n}: «{ann}» moved from the annotation to works")
n_works += 1
n_dates = n_th = 0
for pg, old, new, k in DATES:
    hits = [S for S in load(pg)[1]["sessions"] if S["date_text"] == old]
    assert len(hits) == k, (pg, old, len(hits), k)
    for S in hits:
        S["date_text"] = new; note(S, f"date_text «{old}» -> «{new}» (printed weekday)"); n_dates += 1
for pg, old, new, k in THEATERS:
    hits = [S for S in load(pg)[1]["sessions"] if S["theater"] == old]
    assert len(hits) == k, (pg, old, len(hits), k)
    for S in hits:
        S["theater"] = new; note(S, f"theater «{old}» -> «{new}» (as printed)"); n_th += 1

print(f"{n_works} works changed or added, {n_dates} weekday words, {n_th} theater names, on {len(pages)} pages")
if "--write" in sys.argv:
    for p, d, fmt in pages.values():
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
