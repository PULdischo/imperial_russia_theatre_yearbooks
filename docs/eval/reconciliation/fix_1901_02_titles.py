"""1901-02 Repertoire title audit. The blind read of every column (docs/eval/scan_audit/1901-02_scan_reads.csv) was compared
word by word with the stored works: 76 cells differed, 11 in punctuation only (no change). The other 65 were read on
ForUpload_1901-02_Repertoire.pdf (page index = pNNN) by two agents and the uncertain ones by Claude; readings and verdicts in
docs/eval/scan_audit/1901-02_title_reads.csv (column n = the number used below). RG read three on the crops (2026-10-30):
#45 «Ирининская» (not a misprint), 20 Apr «Балетный» (faint е, stored right), 9 Feb «Принцесса Греза» (faint е).

Kinds of fix (61 cells, 67 works):
- letters the extraction got wrong or modernised: «Свѣтитъ, да не грѣетъ», «Въ отвѣтѣ», «Въ глуши», «Ирининская», «Валкирія»,
  «Евгеній», «Греза», «Бѣшеныя», «предпріятіе», «Флахсманъ», «Джентльмэнъ»; genres «эт.» (stored «вт.»), «сц.» («сп.»), «др.» («хр.»),
  «оперетка»;
- genre added where the print gives none: «Боярыня Вѣра Шелога, прологъ» (stored with «оп.»/«др.»), excerpts with «бал.»/«оперет.»;
- excerpt wording lost: 2 Dec Маріинскій «3-й актъ бал. Спящая красавица» (was the whole ballet, the wording in the annotation),
  12 Jan Маріинскій operetta acts, 20 Apr Большой benefit; printed phrase restored, genre none (the project's excerpt convention);
- garbage genres from the extraction: «L'énigme» «pièce nouvelle», «Sacré Léonce!» «pièce»;
- misprints stored as printed (genuine_print_typos.md): «M'amonr» (24 Jan), «Pour étre aimée» (28 Dec), «Дивертиссемемтъ» (30 Jan).
Also (RG 2026-10-30): 2 Feb Большой charity, five printed items moved from the annotation to works (STRUCT); weekday words
and theater names the extraction modernised («Четверг.», «Четвергь.», «Вторник.», «Воскресенье», «Мариинскій», «Новый театр.»),
read on the scan (DATES, THEATERS). 16 Feb Маріинскій «Концертъ-спектакль» stored as an item (STRUCT; RG: printed in the item face). 9 Mar Михайловскій «Intermède» appended as the third item
(APPEND; RG: "yes").
Rows keep their places; no event_id or performance order changes.

uv run python docs/eval/reconciliation/fix_1901_02_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-30 (1901-02 title audit, scan_audit/1901-02_title_reads.csv"

# (n, page, session index, work index, (old title, old genre), (new title, new genre))
FIX = [
    (1, 'p001', 15, 1, ('Волшебные звуки', 'вт.'), ('Волшебные звуки', 'эт.')),
    (2, 'p002', 23, 0, ('Джентльменъ', 'ком.'), ('Джентльмэнъ', 'ком.')),
    (3, 'p003', 28, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (4, 'p003', 32, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (5, 'p005', 3, 0, ('Евгений Онѣгинъ', 'оп.'), ('Евгеній Онѣгинъ', 'оп.')),
    (6, 'p006', 13, 0, ('Въ отвѣтъ', 'пьеса'), ('Въ отвѣтѣ', 'пьеса')),
    (7, 'p006', 15, 0, ('Въ отвѣтъ', 'пьеса'), ('Въ отвѣтѣ', 'пьеса')),
    (8, 'p006', 20, 0, ('Въ отвѣтъ', 'пьеса'), ('Въ отвѣтѣ', 'пьеса')),
    (9, 'p006', 24, 0, ('Въ отвѣтъ', 'пьеса'), ('Въ отвѣтѣ', 'пьеса')),
    (10, 'p006', 1, 1, ('1-е д. бал. Наяда и рыбакъ', 'бал.'), ('1-е д. бал. Наяда и рыбакъ', None)),
    (11, 'p007', 17, 0, ('Вѣшеныя деньги', 'ком.'), ('Бѣшеныя деньги', 'ком.')),
    (12, 'p007', 21, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (13, 'p008', 18, 0, ('Въ отвѣтъ', 'пьеса'), ('Въ отвѣтѣ', 'пьеса')),
    (15, 'p009', 1, 0, ('Боярыня Вѣра Шелога, прологъ', 'оп.'), ('Боярыня Вѣра Шелога', 'прологъ')),
    (16, 'p009', 4, 0, ('Боярыня Вѣра Шелога, прологъ', 'оп.'), ('Боярыня Вѣра Шелога', 'прологъ')),
    (17, 'p009', 14, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (18, 'p009', 16, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (19, 'p009', 19, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (20, 'p010', 25, 0, ('Въ отвѣтъ', 'пьеса'), ('Въ отвѣтѣ', 'пьеса')),
    (21, 'p011', 23, 0, ('Въ глупии, пьеса', None), ('Въ глуши', 'пьеса')),
    (22, 'p011', 28, 0, ('Въ глупии, пьеса', None), ('Въ глуши', 'пьеса')),
    (23, 'p012', 33, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (24, 'p012', 21, 1, ('Великая тайна', 'вт.'), ('Великая тайна', 'эт.')),
    (25, 'p013', 1, 0, ('Боярыня Вѣра Шелога, прологъ', 'др.'), ('Боярыня Вѣра Шелога', 'прологъ')),
    (26, 'p013', 11, 0, ('Боярыня Вѣра Шелога, прологъ', 'др.'), ('Боярыня Вѣра Шелога', 'прологъ')),
    (27, 'p013', 19, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (28, 'p014', 10, 1, ('Спящая красавица', 'бал.'), ('3-й актъ бал. Спящая красавица', None)),
    (28, 'p014', 10, 2, ('Оживленный садъ', 'бал.'), ('Оживленный садъ', None)),
    (30, 'p016', 12, 0, ('1-е д. оперет. Птички пѣвчія', 'оперет.'), ('1-е д. оперет. Птички пѣвчія', None)),
    (30, 'p016', 12, 1, ('2-е д. оперет. Прекрасная Елена', 'оперет.'), ('2-е д. оперет. Прекрасная Елена', None)),
    (32, 'p017', 10, 0, ('Боярыня Вѣра Шелога, прологъ', 'др.'), ('Боярыня Вѣра Шелога', 'прологъ')),
    (33, 'p017', 22, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (34, 'p017', 31, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (35, 'p018', 27, 2, ('На премію', 'сп.'), ('На премію', 'сц.')),
    (36, 'p018', 34, 1, ('Пожаръ', 'сп.'), ('Пожаръ', 'сц.')),
    (37, 'p018', 42, 0, ('Pour être aimée', 'com.'), ('Pour étre aimée', 'com.')),
    (38, 'p020', 34, 1, ('Великая тайна', 'вт.'), ('Великая тайна', 'эт.')),
    (40, 'p021', 11, 0, ('Боярыня Вѣра Шелога, прологъ', 'др.'), ('Боярыня Вѣра Шелога', 'прологъ')),
    (41, 'p022', 5, 0, ('Свѣтить, да не грѣть', 'др.'), ('Свѣтитъ, да не грѣетъ', 'др.')),
    (42, 'p022', 13, 0, ('Птички пѣвчія', 'оперет.'), ('1-е д. оперет. Птички пѣвчія', None)),
    (42, 'p022', 13, 1, ('Прекрасная Елена', 'оперет.'), ('2-е д. оперет. Прекрасная Елена', None)),
    (42, 'p022', 13, 2, ('Орфей въ аду', 'оперет.'), ('1-е и 2-е д. оперет. Орфей въ аду', None)),
    (43, 'p023', 12, 0, ('Выгодное предприятіе', 'ком.'), ('Выгодное предпріятіе', 'ком.')),
    (44, 'p023', 13, 0, ('Прининская община', 'ком.'), ('Ирининская община', 'ком.')),
    (45, 'p023', 17, 0, ('Прининская община', 'ком.'), ('Ирининская община', 'ком.')),
    (46, 'p023', 27, 0, ('Воспитатель Флаксманъ', 'ком.'), ('Воспитатель Флахсманъ', 'ком.')),
    (47, 'p024', 0, 0, ('Валкірія', 'оп.'), ('Валкирія', 'оп.')),
    (49, 'p024', 6, 0, ('Валкірія', 'оп.'), ('Валкирія', 'оп.')),
    (50, 'p024', 9, 0, ('Валкірія', 'оп.'), ('Валкирія', 'оп.')),
    (51, 'p024', 14, 1, ("M'amour", 'com.'), ("M'amonr", 'com.')),
    (53, 'p025', 30, 1, ('Дивертиссементъ', ''), ('Дивертиссемемтъ', None)),
    (54, 'p026', 5, 0, ('Принцесса Грэза', 'оп.'), ('Принцесса Греза', 'оп.')),
    (55, 'p027', 23, 0, ('Въ отвѣтъ', 'пьеса'), ('Въ отвѣтѣ', 'пьеса')),
    (62, 'p030', 26, 0, ('Гейша и рыцарь', 'хр.'), ('Гейша и рыцарь', 'др.')),
    (63, 'p030', 32, 0, ('Милашка', 'оперетта.'), ('Милашка', 'оперетка')),
    (65, 'p032', 23, 0, ("L'énigme, pièce nouvelle.", 'pièce'), ("L'énigme", 'pièce nouvelle')),
    (66, 'p032', 25, 0, ("L'énigme, pièce nouvelle.", 'pièce'), ("L'énigme", 'pièce nouvelle')),
    (67, 'p032', 26, 0, ("L'énigme, pièce nouvelle.", 'pièce'), ("L'énigme", 'pièce nouvelle')),
    (68, 'p032', 27, 1, ('Sacré Léonce! pièce.', 'pièce'), ('Sacré Léonce!', 'pièce')),
    (69, 'p032', 28, 1, ('Sacré Léonce! pièce.', 'pièce'), ('Sacré Léonce!', 'pièce')),
    (70, 'p032', 30, 1, ('Sacré Léonce! pièce.', 'pièce'), ('Sacré Léonce!', 'pièce')),
    (71, 'p032', 32, 1, ('Sacré Léonce! pièce.', 'pièce'), ('Sacré Léonce!', 'pièce')),
    (73, 'p035', 6, 0, ('Гугеноты', 'оп.'), ('3-е и 4-е д. оп. Гугеноты', None)),
    (73, 'p035', 6, 1, ('Макбетъ', 'траг.'), ('Сцена 5-го д. траг. Макбетъ', None)),
    (73, 'p035', 6, 2, ('Горе отъ ума', 'ком.'), ('3-е д. ком. Горе отъ ума', None)),
    (74, 'p035', 14, 0, ('Ирвиннская община', 'ком.'), ('Ирининская община', 'ком.')),
    (75, 'p035', 21, 0, ('Ирвиннская община', 'ком.'), ('Ирининская община', 'ком.')),
]
# (n, page, session index, (old annotation, new annotation))
ANN = [
    (28, 'p014', 10, ('Бенефисъ г-жи Преображенской. 3-й актъ бал.', 'Бенефисъ г-жи Преображенской.')),
]

# (n, page, session index, old annotation, new annotation, new session, works, note): items held only in the annotation
STRUCT = [
    (52, 'p025', 9,
     'Въ пользу фонда Комиссіи по сооруженію памятника А. С. Пушкину въ С.-Петербургѣ.\n3-я карт. 2-го дѣйств. и 3-е дѣйств. оп. Русланъ и Людмила.\n1-я сцена оп. Руслалки.\n3-я и 4-я сц. оп. Каменнаго гостя.\n2-я карт. 1-го дѣйств. Борисъ Годуновъ.\nЖивыя картины.',
     'Въ пользу фонда Комиссіи по сооруженію памятника А. С. Пушкину въ С.-Петербургѣ.', 'morning',
     [('3-я карт. 2-го дѣйств. и 3-е дѣйств. оп. Русланъ и Людмила', None), ('1-я сцена оп. Русалки', None),
      ('3-я и 4-я сц. оп. Каменнаго гостя', None), ('2-я карт. 1-го дѣйств. Борисъ Годуновъ', None), ('Живыя картины', None)],
     "5 printed items moved from the annotation to works (RG 2026-10-30: \"This sounds good\"), session -> morning (printed УТРО); "
     "the annotation's «Руслалки» was a misread of «Русалки»"),
    (58, 'p028', 0,
     'Въ пользу благотворительнаго Общества при Городской Калинкинской больницѣ. Концертъ-спектакль.',
     'Въ пользу благотворительнаго Общества при Городской Калинкинской больницѣ.', 'unspecified',
     [('Концертъ-спектакль', None)],
     "«Концертъ-спектакль.» is printed in the roman item face below the bold charity heading, so it is the item given "
     "(RG 2026-10-30: \"the typeface is that of a performance\", \"Store as item\"); as other generic items in that face are "
     "stored (Концертное отдѣленіе, Живыя картины, Дивертиссементъ, Intermède; RG: \"the strongest evidence\"); moved from the annotation to works"),
]
# (n, page, session index, old annotation, new annotation, works expected, item appended, note): a printed item left in the annotation
APPEND = [
    (64, 'p030', 15,
     "Représentation au bénéfice de l'Association de secours mutuel des artistes dramatiques russes et français. Intermède.",
     "Représentation au bénéfice de l'Association de secours mutuel des artistes dramatiques russes et français.",
     [("L'énigme", 'pièce'), ('La main', 'mimodrame')], ('Intermède', None),
     "«Intermède.» is the third line in the roman item face, after «La main, mimodrame»; stored as an item, as on the Михайловскій "
     "French benefit bills of 14 Dec 1892 and 7 Apr 1903 (RG 2026-10-30: \"yes\"); moved from the annotation to works"),
]
# (page, stored date_text, printed date_text, rows): weekday words modernised or misread by the extraction (read on the scan)
DATES = [
    ('p000', '30 Четверг.', '30 Четвергъ.', 1),
    ('p000', '6 Четверг.', '6 Четвергъ.', 1),
    ('p006', '11 Четверг.', '11 Четвергъ.', 3),
    ('p006', '18 Четверг.', '18 Четвергъ.', 3),
    ('p006', '9 Вторник.', '9 Вторникъ.', 3),
    ('p007', '11 Четверг.', '11 Четвергъ.', 3),
    ('p007', '18 Четверг.', '18 Четвергъ.', 3),
    ('p007', '9 Вторник.', '9 Вторникъ.', 3),
    ('p010', '11 Воскресенье', '11 Воскрес.', 2),
    ('p010', '4 Воскресенье', '4 Воскрес-', 1),
    ('p011', '1 Четверг.', '1 Четвергъ.', 2),
    ('p011', '8 Четверг.', '8 Четвергъ.', 2),
    ('p017', '13 Четверг.', '13 Четвергъ.', 2),
    ('p025', '24 Четверг.', '24 Четвергъ.', 3),
    ('p025', '31 Четверг.', '31 Четвергъ.', 3),
    ('p027', '14 Четвергь.', '14 Четвергъ.', 2),
    ('p027', '7 Четвергь.', '7 Четвергъ.', 2),
    ('p029', '21 Четвергь.', '21 Четвергъ.', 6),
    ('p034', '18 Четвергь.', '18 Четвергъ.', 3),
    ('p035', '18 Четверг.', '18 Четвергъ.', 3),
    ('p036', '2 Четверг.', '2 Четвергъ.', 3),
    ('p036', '25 Четверг.', '25 Четвергъ.', 3),
    ('p037', '2 Четверг.', '2 Четвергъ.', 2),
    ('p037', '25 Четверг.', '25 Четвергъ.', 2),
]
# (page, stored theater, printed theater, rows)
THEATERS = [
    ('p006', 'Мариинскій театръ.', 'Маріинскій театръ.', 13),
    ('p008', 'Мариинскій театръ.', 'Маріинскій театръ.', 13),
    ('p021', 'Новый театр.', 'Новый театръ.', 16),
    ('p027', 'Новый театр.', 'Новый театръ.', 13),
]


def load(pg):
    p = RAW / f"repertoire_1901-02_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + msg


pages = {}
for n, pg, i, j, old, new in FIX:
    if pg not in pages: pages[pg] = load(pg)
    S = pages[pg][1]["sessions"][i]; w = S["works"][j]
    assert (w["work_title"], w.get("genre")) == old, (n, pg, i, j, w, old)
    w["work_title"], w["genre"] = new
    note(S, f"{TAG} #{n}): work {j + 1} «{old[0]}» / {old[1]!r} -> «{new[0]}» / {new[1]!r}")
for n, pg, i, (old, new) in ANN:
    S = pages[pg][1]["sessions"][i]
    assert S.get("annotation") == old, (n, S.get("annotation"))
    S["annotation"] = new; note(S, f"{TAG} #{n}): annotation «{old}» -> «{new}» (excerpt wording moved back to the work)")
for n, pg, i, old_ann, new_ann, new_sess, works, why in STRUCT:
    if pg not in pages: pages[pg] = load(pg)
    S = pages[pg][1]["sessions"][i]
    assert S.get("annotation") == old_ann and S["works"] == [] and S["session"] == "unspecified", (n, S)
    S["annotation"], S["session"] = new_ann, new_sess
    S["works"] = [{"work_title": wt, "genre": g} for wt, g in works]
    note(S, f"{TAG} #{n}): {why}")
for n, pg, i, old_ann, new_ann, works, item, why in APPEND:
    if pg not in pages: pages[pg] = load(pg)
    S = pages[pg][1]["sessions"][i]
    assert S.get("annotation") == old_ann and [(w["work_title"], w.get("genre")) for w in S["works"]] == works, (n, S)
    S["annotation"] = new_ann; S["works"].append({"work_title": item[0], "genre": item[1]})
    note(S, f"{TAG} #{n}): {why}")
for pg, old, new, k in DATES:
    if pg not in pages: pages[pg] = load(pg)
    hits = [S for S in pages[pg][1]["sessions"] if S["date_text"] == old]
    assert len(hits) == k, (pg, old, len(hits), k)
    for S in hits:
        S["date_text"] = new; note(S, f"{TAG}): date_text «{old}» -> «{new}» (printed weekday)")
for pg, old, new, k in THEATERS:
    if pg not in pages: pages[pg] = load(pg)
    hits = [S for S in pages[pg][1]["sessions"] if S["theater"] == old]
    assert len(hits) == k, (pg, old, len(hits), k)
    for S in hits:
        S["theater"] = new; note(S, f"{TAG}): theater «{old}» -> «{new}» (as printed)")
if "--write" in sys.argv:
    for p, d, f in pages.values():
        p.write_text(json.dumps(d, indent=f[0], ensure_ascii=f[1]) + f[2], encoding="utf-8")
print(len(FIX), "works,", len(ANN), "annotation,", len(STRUCT) + len(APPEND), "structural,", sum(d[3] for d in DATES), "date words,", sum(x[3] for x in THEATERS), "theater names,", len(pages), "pages;", "WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
