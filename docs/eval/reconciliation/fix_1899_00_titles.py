"""1899-00 Repertoire title audit. The blind read of every column (docs/eval/scan_audit/1899-00_scan_reads.csv) was compared
word by word with the stored works: 127 cells differed, 83 in punctuation only (no change). The other 44 were read again on
ForUpload_1899-00_Repertoire.pdf (image index = pNNN) by a second agent that saw neither version, and the doubtful ones by Claude;
readings and verdicts in docs/eval/scan_audit/1899-00_title_reads.csv (column n = the number used below). Two cells (20, 26,
«Ирэнъ») were already right; the first blind read was wrong there.

Kinds of fix:
- letters the extraction got wrong or modernised: «Свѣтитъ, да не грѣетъ» (×5), «Девятый валъ» (×3, stored «вальс»), «Вѣеръ» (×3,
  stored «Вѣрь»), «поставитъ» (×6), «Юдиѳь» (×2), «Звѣзды», «Гастролерша», «Ранцева», «Осенній», «Шато-Икемъ», «Мелентьева»,
  «Cyrano de Bergerac» (stored «Cyrano»), «Der Königslieutenant» (stored «Königsleutnant»); genre «сц.» (stored «сп.», 16 Jan);
- genres the print does not give: the Savina benefit excerpts (19 Jan) and 23 Jan «2-е д. бал. Золушка.» (the project's
  excerpt convention: no genre); a genre duplicated into the title («Тщетная предосторожность, бал», «Onkel Toni, Comödie.»);
- misprints stored as printed (genuine_print_typos.md; aliased for matching in work_title_aliases.csv): «Хоть тресни, а женнсь»,
  «Джентльмэиъ», «Agence dramatiqus», «Colinete», «Наванунѣ золотой свадьбы», «Книзь Игорь», «Weh dem der, Iügt», «Татьяна Рѣпипа»;
  and the genre «сп.» on 9 Jan (Малый, «Не отъ міра сего»; 16 Jan prints «сц.»), as 1908-09 «Черевички, эп,».
Also the weekday words and theater names the extraction modernised: «Четвергь.»/«Четверг.» (the print has «Четвергъ.» throughout)
and «… театр.» (the column headings print «театръ.»).
Rows keep their places; no event_id or performance order changes.

uv run python docs/eval/reconciliation/fix_1899_00_titles.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-30 (1899-00 title audit, scan_audit/1899-00_title_reads.csv"
P = "поставить на своемъ"; PT = "поставитъ на своемъ"
SV = ("Свѣтить, да не грѣть", "др."); SVT = ("Свѣтитъ, да не грѣетъ", "др.")

# (n, page, session index, work index, (old title, old genre), (new title, new genre))
FIX = [
    (1, 'p000', 17, 1, ('Гастролерка', 'шут.'), ('Гастролерша', 'шут.')),
    (2, 'p001', 2, 0, ('Звёзды', 'бал.'), ('Звѣзды', 'бал.')),
    (3, 'p001', 12, 1, (f'Если женщина рѣшила, такъ {P}!', 'ком.'), (f'Если женщина рѣшила, такъ {PT}!', 'ком.')),
    (4, 'p002', 30, 1, ('Хоть тресни, а женись', 'ком.'), ('Хоть тресни, а женнсь', 'ком.')),
    (5, 'p003', 17, 2, (f'Если женщина рѣшила, такъ {P}', 'ком.'), (f'Если женщина рѣшила, такъ {PT}!', 'ком.')),
    (6, 'p003', 24, 2, (f'Если женщина рѣшила, такъ {P}', 'ком.'), (f'Если женщина рѣшила, такъ {PT}!', 'ком.')),
    (7, 'p004', 27, 0, ('Девятый вальс', 'др.'), ('Девятый валъ', 'др.')),
    (8, 'p005', 12, 0, ('Джентльменъ', 'ком.'), ('Джентльмэнъ', 'ком.')),
    (9, 'p005', 21, 0, ('Джентльменъ', 'ком.'), ('Джентльмэиъ', 'ком.')),
    (10, 'p005', 33, 2, (f'Если женщина рѣшила, такъ {P}!', 'ком.'), (f'Если женщина рѣшила, такъ {PT}!', 'ком.')),
    (11, 'p006', 26, 0, ('Ольга Рапцева', 'др.'), ('Ольга Ранцева', 'др.')),
    (12, 'p006', 29, 0, ('Девятый вальс', 'др.'), ('Девятый валъ', 'др.')),
    (13, 'p006', 35, 0, ('Девятый вальс', 'др.'), ('Девятый валъ', 'др.')),
    (14, 'p007', 0, 0, ('Тщетная предосторожность, бал', 'бал.'), ('Тщетная предосторожность', 'бал')),
    (15, 'p008', 8, 0, SV, SVT),
    (16, 'p013', 31, 1, ('Осенний вечеръ въ деревнѣ', 'вод.'), ('Осенній вечеръ въ деревнѣ', 'вод.')),
    (17, 'p014', 14, 0, SV, SVT),
    (18, 'p014', 20, 0, SV, SVT),
    (19, 'p014', 23, 1, ('Agence dramatique', 'scène'), ('Agence dramatiqus', 'scène')),
    (21, 'p017', 17, 1, (f'Если женщина рѣшила, такъ {P}', 'ком.'), (f'Если женщина рѣшила, такъ {PT}', 'ком.')),
    (22, 'p017', 28, 0, ('Вѣрь', 'ком.'), ('Вѣеръ', 'ком.')),
    (23, 'p017', 31, 0, ('Вѣрь', 'ком.'), ('Вѣеръ', 'ком.')),
    (24, 'p017', 35, 0, ('Вѣрь', 'ком.'), ('Вѣеръ', 'ком.')),
    (25, 'p018', 19, 0, SV, SVT),
    (27, 'p019', 18, 1, (f'Если женщина рѣшила, такъ {P}!', 'ком.'), (f'Если женщина рѣшила, такъ {PT}!', 'ком.')),
    (28, 'p020', 13, 0, ('Юдифь', 'оп.'), ('Юдиѳь', 'оп.')),
    (29, 'p020', 17, 0, ('Юдифь', 'оп.'), ('Юдиѳь', 'оп.')),
    (30, 'p020', 22, 0, ('Colinette', 'pièce'), ('Colinete', 'pièce')),
    (31, 'p021', 24, 0, ('Не отъ міра сего', 'сц.'), ('Не отъ міра сего', 'сп.')),
    (32, 'p021', 26, 1, ('Шато-Инемъ', 'ком.'), ('Шато-Икемъ', 'ком.')),
    (33, 'p021', 38, 0, ('Василиса Мелентьевна', 'др.'), ('Василиса Мелентьева', 'др.')),
    (34, 'p022', 34, 0, SV, SVT),
    (35, 'p022', 9, 0, ('Сцена 4-го д. ком. Ревизоръ', 'ком.'), ('Сцена 4-го д. ком. Ревизоръ', None)),
    (35, 'p022', 9, 2, ('4-е д. ком. Послѣдняя жертва', 'ком.'), ('4-е д. ком. Послѣдняя жертва', None)),
    (35, 'p022', 9, 3, ('Сцены 3-го д. ком. Волки и овцы', 'ком.'), ('Сцены 3-го д. ком. Волки и овцы', None)),
    (36, 'p023', 17, 0, ('Не отъ міра сего', 'сп.'), ('Не отъ міра сего', 'сц.')),
    (37, 'p023', 19, 1, ('Наканунѣ золотой свадьбы', 'шут.'), ('Наванунѣ золотой свадьбы', 'шут.')),
    (38, 'p024', 1, 2, ('2-е д. бал. Золушка', 'бал.'), ('2-е д. бал. Золушка', None)),
    (38, 'p024', 0, 0, ('Князь Игорь', 'оп.'), ('Книзь Игорь', 'оп.')),
    (39, 'p028', 12, 0, ('Weh dem der, lügt', 'Lustspiel'), ('Weh dem der, Iügt', 'Lustspiel')),
    (40, 'p028', 13, 0, ('Onkel Toni, Comödie.', 'Comödie'), ('Onkel Toni', 'Comödie')),
    (41, 'p028', 14, 0, ('Onkel Toni, Comödie.', 'Comödie'), ('Onkel Toni', 'Comödie')),
    (42, 'p030', 14, 0, ('Cyrano', 'com.'), ('Cyrano de Bergerac', 'com.')),
    (43, 'p034', 15, 0, ('Der Königsleutnant', 'Lustspiel'), ('Der Königslieutenant', 'Lustspiel')),
    (44, 'p036', 15, 0, ('Татьяна Рѣпина', 'ком.'), ('Татьяна Рѣпипа', 'ком.')),
]
MISPRINT = {4, 9, 19, 30, 31, 37, 39, 44, 38}
WEEKDAYS = {'Четвергь.': 'Четвергъ.', 'Четверг.': 'Четвергъ.'}
THEATERS = {'Малый театр.': 'Малый театръ.', 'Новый театр.': 'Новый театръ.', 'Большой театр.': 'Большой театръ.'}


def load(pg):
    p = RAW / f"repertoire_1899-00_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}): {msg}"


pages = {}
def get(pg):
    if pg not in pages:
        pages[pg] = load(pg)
    return pages[pg][1]


n_works = 0
for n, pg, si, wi, old, new in FIX:
    S = get(pg)["sessions"][si]; W = S["works"][wi]
    assert (W["work_title"], W["genre"]) == old, (n, pg, si, wi, W, old)
    W["work_title"], W["genre"] = new
    kind = "misprint stored as printed" if (n in MISPRINT and not (n == 38 and wi == 2)) else "read on the scan"
    note(S, f"n{n}: «{old[0]}, {old[1]}» -> «{new[0]}{', ' + new[1] if new[1] else ''}» ({kind})")
    n_works += 1

n_days = n_th = 0
for pg in [f"p{i:03d}" for i in range(38)]:
    for S in get(pg)["sessions"]:
        parts = S["date_text"].split(" ", 1)
        if len(parts) == 2 and parts[1] in WEEKDAYS:
            old = S["date_text"]; S["date_text"] = parts[0] + " " + WEEKDAYS[parts[1]]
            note(S, f"weekday «{old}» -> «{S['date_text']}» (the print has «Четвергъ.»)"); n_days += 1
        if S["theater"] in THEATERS:
            old = S["theater"]; S["theater"] = THEATERS[old]
            note(S, f"theater «{old}» -> «{S['theater']}» (column heading)"); n_th += 1

print(f"works {n_works}, weekday words {n_days}, theater names {n_th}")
if "--write" in sys.argv:
    for pg, (p, d, fmt) in pages.items():
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
