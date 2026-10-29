"""1897-98 title audit: 45 works in 43 Repertoire cells corrected to the print. The 2026-10-29 blind column read
(docs/eval/scan_audit/1897-98_scan_reads.csv) differed from the stored works in 43 cells beyond the extraction errors already
fixed; each was read again on the scan by three readers given both versions unlabelled (crops checked by Claude), and in all 43
the print agrees with the blind read (docs/eval/scan_audit/1897-98_title_reads.csv). RG 2026-10-29: "yes".
Kinds: misread letters (Золотой телецъ, Консулъ Берникъ x5, Теща / За обѣдомъ, Villégiature x3, Воробышекъ, Джентльмэнъ,
Кто любитъ x10, Осенній, случившійся, этюдъ); wrong genre (21 Sep «др.», 9 Jan «Приличія, ш.», 16 Jan «др. очеркъ.»); genre
run into the title or added where none is printed (Пашенька x2, Маруся x3, «Случайно случившійся случай» x2, «2-е д. оп.
Севильскій цирюльникъ.» x4); print oddities stored as printed: 18 Nov «Воробышекъ   ом.» (the «, к» of «ком.» not inked: title
«Воробышекъ», genre «ом.»), 27 Mar «Jm weissen Rössl Lustsp.» (J, no comma; work_title_aliases.csv keeps it with «Im weissen
Rössl»), 11 Feb «Le Bésigue chinois» (the print's spelling from 31 Jan 1898 on). Not changed: 11 Apr «Музыкальное отдѣленіе»
(the print adds only a final full stop). Each change asserts the old title and genre.
uv run python docs/eval/reconciliation/fix_1897_98_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
WRITE = "--write" in sys.argv
# (page, session index, date_text, theater, work index, old title, old genre, new title, new genre)
CHANGES = [
    ('repertoire_1897-98_pair002', 77, '5 Пятница.', 'Михайловскій.', 1, 'Золотой теленокъ', 'ком.', 'Золотой телецъ', 'ком.'),
    ('repertoire_1897-98_pair004', 49, '21 Воскрес.', 'Малый.', 0, 'Въ сѣверной глуши', 'хр.', 'Въ сѣверной глуши', 'др.'),
    ('repertoire_1897-98_pair004', 67, '24 Среда.', 'Михайловскій.', 0, 'Консуль Берникъ', 'др.', 'Консулъ Берникъ', 'др.'),
    ('repertoire_1897-98_pair004', 77, '26 Пятница.', 'Михайловскій.', 0, 'Консуль Берникъ', 'др.', 'Консулъ Берникъ', 'др.'),
    ('repertoire_1897-98_pair004', 100, '1 Среда.', 'Михайловскій.', 0, 'Консуль Берникъ', 'др.', 'Консулъ Берникъ', 'др.'),
    ('repertoire_1897-98_pair006', 40, '3 Пятница.', 'Михайловскій.', 0, 'Консуль Берникъ', 'др.', 'Консулъ Берникъ', 'др.'),
    ('repertoire_1897-98_pair006', 53, '6 Понед.', 'Малый.', 1, 'Маруся, др. этюдь.', 'др.', 'Маруся', 'др. этюдъ.'),
    ('repertoire_1897-98_pair006', 64, '8 Среда.', 'Малый.', 1, 'Маруся, др. этюдь.', 'др.', 'Маруся', 'др. этюдъ.'),
    ('repertoire_1897-98_pair006', 2, '10 Пятн.', 'Малый.', 1, 'Волшебные звуки', 'этюдь', 'Волшебные звуки', 'этюдъ.'),
    ('repertoire_1897-98_pair006', 2, '10 Пятн.', 'Малый.', 2, 'Случайно случившійся случай, фарсъ.', 'фарсъ', 'Случайно случившійся случай', 'фарсъ.'),
    ('repertoire_1897-98_pair006', 4, '10 Пятн.', 'Михайловскій.', 0, 'Консуль Берникъ', 'др.', 'Консулъ Берникъ', 'др.'),
    ('repertoire_1897-98_pair006', 12, '12 Воскрес.', 'Малый.', 0, 'Пашенька, пьеса.', 'пьеса', 'Пашенька', 'пьеса.'),
    ('repertoire_1897-98_pair006', 28, '15 Среда.', 'Малый.', 1, 'Маруся, др. этюдь.', 'др.', 'Маруся', 'др. этюдъ.'),
    ('repertoire_1897-98_pair008', 15, '24 Пятн.', 'Маріинскій.', 1, '2-е д. оп. Севильскій цирюльникъ.', 'оп.', '2-е д. оп. Севильскій цирюльникъ.', None),
    ('repertoire_1897-98_pair008', 32, '27 Понед.', 'Маріинскій.', 1, '2-е д. оп. Севильскій цирюльникъ.', 'оп.', '2-е д. оп. Севильскій цирюльникъ.', None),
    ('repertoire_1897-98_pair008', 51, '30 Четв.', 'Малый.', 1, 'Не надо', 'др. этюд.', 'Не надо', 'др. этюдъ.'),
    ('repertoire_1897-98_pair008', 52, '30 Четв.', 'Маріинскій.', 1, '2-е д. оп. Севильскій цирюльникъ.', 'оп.', '2-е д. оп. Севильскій цирюльникъ.', None),
    ('repertoire_1897-98_pair008', 62, '4 Вторник.', 'Маріинскій.', 1, '2-е д. оп. Севильскій цирюльникъ.', 'оп.', '2-е д. оп. Севильскій цирюльникъ.', None),
    ('repertoire_1897-98_pair010', 16, '17 Понед.', 'Малый.', 1, 'Осенний вечеръ въ деревнѣ', 'вод.', 'Осенній вечеръ въ деревнѣ', 'вод.'),
    ('repertoire_1897-98_pair010', 17, '18 Вторн.', 'Александринскій.', 1, 'Воробышекъ', 'ком.', 'Воробышекъ', 'ом.'),
    ('repertoire_1897-98_pair010', 24, '21 Пятница.', 'Малый.', 1, 'Кто любить миръ... Кто любить ссору!', 'ком.', 'Кто любитъ миръ... Кто любитъ ссору!', 'ком.'),
    ('repertoire_1897-98_pair010', 28, '23 Воскресенье.', 'Малый.', 0, 'Пашенька, пьеса.', 'пьеса', 'Пашенька', 'пьеса.'),
    ('repertoire_1897-98_pair010', 32, '24 Понед.', 'Малый.', 1, 'Кто любить миръ....', 'ком.', 'Кто любитъ миръ....', 'ком.'),
    ('repertoire_1897-98_pair010', 51, '30 Воскрес.', 'Малый.', 1, 'Случайно случившійся случай, фарсъ.', 'фарсъ', 'Случайно случившійся случай', 'фарсъ.'),
    ('repertoire_1897-98_pair010', 1, '1 Понед.', 'Малый.', 1, 'Кто любить ссору!', 'ком.', 'Кто любитъ ссору!', 'ком.'),
    ('repertoire_1897-98_pair012', 4, '2 Вторникъ.', 'Малый.', 1, 'Кто любить миръ...', 'ком.', 'Кто любитъ миръ....', 'ком.'),
    ('repertoire_1897-98_pair012', 49, '10 Среда.', 'Малый.', 1, 'Кто любить миръ...', 'ком.', 'Кто любитъ миръ....', 'ком.'),
    ('repertoire_1897-98_pair012', 59, '12 Пятница.', 'Малый.', 1, 'Кто любить миръ...', 'ком.', 'Кто любитъ миръ....', 'ком.'),
    ('repertoire_1897-98_pair014', 15, '26 Пятница.', 'Александринскій.', 1, 'Воробьишекъ', 'ком.', 'Воробышекъ', 'ком.'),
    ('repertoire_1897-98_pair014', 97, '29 Понедѣльник.', 'Малый.', 1, 'Кто любить миръ....', 'ком.', 'Кто любитъ миръ....', 'ком.'),
    ('repertoire_1897-98_pair014', 102, '2 Пятница.', 'Малый.', 1, 'Случайно случившийся случай', 'фарсъ.', 'Случайно случившійся случай', 'фарсъ.'),
    ('repertoire_1897-98_pair014', 78, '7 Среда.', 'Малый.', 1, 'Кто любить миръ....', 'ком.', 'Кто любитъ миръ....', 'ком.'),
    ('repertoire_1897-98_pair014', 111, '9 Пятница.', 'Александринскій.', 1, 'Приличія', 'ком.', 'Приличія', 'ш.'),
    ('repertoire_1897-98_pair016', 14, '12 Понед.', 'Малый.', 0, 'Джентльманъ', 'ком.', 'Джентльмэнъ', 'ком.'),
    ('repertoire_1897-98_pair016', 34, '16 Пятница.', 'Малый.', 1, 'Разрушенный домъ', 'др.', 'Разрушенный домъ', 'др. очеркъ.'),
    ('repertoire_1897-98_pair016', 41, '17 Суббота.', 'Михайловскій.', 1, 'Villégiateure', 'com.', 'Villégiature', 'com.'),
    ('repertoire_1897-98_pair016', 53, '19 Понед.', 'Михайловскій.', 1, 'Villégiateure', 'com.', 'Villégiature', 'com.'),
    ('repertoire_1897-98_pair016', 58, '20 Вторн.', 'Михайловскій.', 1, 'Villégiateure', 'com.', 'Villégiature', 'com.'),
    ('repertoire_1897-98_pair016', 70, '28 Среда.', 'Малый.', 0, 'Теша', 'др.', 'Теща', 'др.'),
    ('repertoire_1897-98_pair016', 70, '28 Среда.', 'Малый.', 1, 'За объѣдомъ', 'ш.', 'За обѣдомъ', 'ш.'),
    ('repertoire_1897-98_pair018', 4, '29 Четвергъ.', 'Малый.', 1, 'Кто любить миръ....', 'ком.', 'Кто любитъ миръ....', 'ком.'),
    ('repertoire_1897-98_pair018', 82, '11 Среда.', 'Михайловскій.', 1, 'Le Bésique chinois', 'com.', 'Le Bésigue chinois', 'com.'),
    ('repertoire_1897-98_pair022', 52, '27 Пятница.', 'Александринскій.', 0, 'Im weissen Rössl', 'Lustsp.', 'Jm weissen Rössl', 'Lustsp.'),
    ('repertoire_1897-98_pair024', 33, '11 Суббота.', 'Александринскій.', 1, 'Собачкинъ', 'отрывъ.', 'Собачкинъ', 'отрыв.'),
    ('repertoire_1897-98_pair024', 62, '24 Пятница.', 'Малый.', 1, 'Кто любить миръ...', 'ком.', 'Кто любитъ миръ....', 'ком.'),
]
docs = {}
for page, idx, dt, th, wi, ot, og, nt, ng in CHANGES:
    if page not in docs:
        p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
        for ind in (2, 4, 1, None):
            for ea in (False, True):
                for tr in ("", "\n"):
                    if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
        assert fmt, p
        docs[page] = (p, d, fmt)
    S = docs[page][1]["sessions"][idx]
    assert S["date_text"] == dt and S["theater"] == th, (page, idx, S["date_text"], S["theater"])
    W = S["works"][wi]
    assert W["work_title"] == ot and W["genre"] == og, (page, idx, wi, W)
    W["work_title"], W["genre"] = nt, ng
    note = f"title audit 2026-10-29: «{ot}, {og}» -> «{nt}, {ng}» (scan)"
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
    print(dt, th, wi + 1, ot, "->", nt, ng)
if WRITE:
    for p, d, fmt in docs.values():
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(len(CHANGES), "changes in", len(docs), "pages;", "WROTE" if WRITE else "DRY RUN", RAW)
