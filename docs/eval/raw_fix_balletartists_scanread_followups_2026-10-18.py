"""BalletArtists follow-ups from the 2026-10-18 ordinal scan read (after raw_fix_dropped_ordinals_balletartists_2026-10-18.py).

Every entry below was zoomed on the full-resolution scans (pdf/Spiski_BalletArtists, extract_image; single-line crops in
docs/eval/balletartists_spelling_crops_2026-10-18.html). RG decided each group on 2026-10-18:
  S  45 surnames misread by extraction, set to the printed spelling (Оголейть -> Оголейтъ etc.; «Алексадрова 2-я», 1901-02 SP
     no. 2, is a print typo stored as printed, like «Кщесинскій»). Rows not zoomed are left alone, whatever their spelling.
  H  5 ordinals printed without a hyphen, stored as printed («Смирновъ 2 й»), like «Никитина 2 я».
  B  1903-04 MSK p005 (printed p. 109): extraction dropped «10. Бѣлоусовъ 1-й, Геннадій Ивановичъ» and put «108. Ѳеоктистова,
     Лилія Васильевна» (last of the women's list, top of the page) in his slot as Артисты no. 10. Slot 10 is overwritten with
     Бѣлоусовъ's printed entry and Лилія is APPENDED at the end of the page as Артистки no. 108 (appending keeps every other
     entry_id; issue #131). person_link is pre-seeded: e010 -> Бѣлоусовъ 49135ed2, the new e022 -> Лилія's person 83685cf4.
  M  1893-94 SP p003: «Михайлова 2-я» printed no. 78 (stored 77.); «Михайлова 1-я» † 12 декабря 1893 г. recorded in her
     service period (end_type 'died', as for the other printed deaths).
  P  3 pages with «Имя Отчество» in first_name and no patronymic (1893-94 SP p002, 1905-06 SP p002, 1908-09 MSK p003):
     split into first_name / patronymic (79 rows; «Леньяни, Пьерина» has no patronymic printed and is left).
Field edits plus one appended entry; no entry removed or moved.
usage: uv run python docs/eval/raw_fix_balletartists_scanread_followups_2026-10-18.py [--write]
       then docs/eval/rebuild_after_raw_edit.sh (the --write run also pre-seeds entities.person_link for B)"""
import json, re, sys
from collections import Counter
from pathlib import Path

RAW = Path('outputs/full_run/raw')
DB = 'outputs/full_run/imperial_theaters.duckdb'
EXPECTED = Counter({'S': 45, 'H': 5, 'B': 2, 'M': 2, 'P': 79})
PATRONYMIC = re.compile(r'^[А-ЯЁѲІѢ]\w*(вна|чна|ична|ичъ|вичъ)$')

# (page_id, list_number) -> (stored surname base, printed base); the ordinal is kept as stored
S = {}
def s(page, lns, old, new):
    for ln in lns: S[(f'balletartists_{page}', f'{ln}.')] = (old, new)
s('1890-91_SP_p004', (83, 84, 85), 'Оголейть', 'Оголейтъ')
s('1891-92_SP_p002', (85,), 'Оголѣйть', 'Оголейтъ')
s('1891-92_SP_p003', (86, 87), 'Оголейть', 'Оголейтъ')
s('1892-93_SP_p003', (90, 91, 92), 'Оголейть', 'Оголейтъ')
s('1895-96_SP_p003', (87, 88), 'Оголейть', 'Оголейтъ')
s('1895-96_SP_p004', (89,), 'Оголейть', 'Оголейтъ')
s('1892-93_MSK_p001', (19, 20), 'Гейтень', 'Гейтенъ')
for pg in ('1893-94_MSK_p001', '1896-97_MSK_p001', '1897-98_MSK_p001'):
    s(pg, (20,), 'Гейтень', 'Гейтенъ')
s('1894-95_MSK_p001', (21,), 'Гейтень', 'Гейтенъ')
s('1895-96_MSK_p001', (23,), 'Гейтень', 'Гейтенъ')
s('1892-93_MSK_p001', (28, 29), 'Дантесь', 'Дантесъ')
s('1893-94_MSK_p001', (29, 30), 'Дантесь', 'Дантесъ')
s('1892-93_MSK_p003', (94,), 'Смирнина', 'Смирнова')
s('1895-96_SP_p006', (148, 149, 150, 151), 'Федорова', 'Ѳедорова')
s('1896-97_MSK_p004', (129, 130), 'Ѳектистова', 'Ѳеоктистова')
s('1896-97_MSK_p004', (1, 2), 'Бакинь', 'Бакинъ')
s('1897-98_SP_p004', (97, 98), 'Рыхлянова', 'Рыхлякова')
s('1900-01_SP_p008', (52, 53), 'Пашенко', 'Пащенко')
s('1901-02_SP_p000', (2,), 'Александрова', 'Алексадрова')
s('1904-05_SP_p009', (80, 81), 'Тихомировъ', 'Тихоміровъ')
s('1907-08_SP_p009', (72, 73), 'Тихомировъ', 'Тихоміровъ')
s('1907-08_MSK_p007', (58, 59), 'Симирновъ', 'Смирновъ')
s('1909-10_SP_p002', (46, 47), 'Леонтъева', 'Леонтьева')

H = {('balletartists_1892-93_MSK_p006', '58.'): ('Смирновъ 2-й', 'Смирновъ 2 й'),
     ('balletartists_1902-03_SP_p002', '30.'): ('Ильина 1-я', 'Ильина 1 я'),
     ('balletartists_1903-04_MSK_p004', '103.'): ('Ячменева 2-я', 'Ячменева 2 я'),
     ('balletartists_1904-05_SP_p000', '8.'): ('Бакеркина 2-я', 'Бакеркина 2 я'),
     ('balletartists_1906-07_SP_p007', '24.'): ('Ивановъ 2-й', 'Ивановъ 2 й')}

B_PAGE, B_INDEX = 'balletartists_1903-04_MSK_p005', 9
BELOUSOV = {'institution': 'Балетная труппа.', 'heading_path': 'Артисты:', 'list_number': '10.', 'family_name': 'Бѣлоусовъ 1-й',
            'first_name': 'Геннадій', 'patronymic': 'Ивановичъ', 'tenure_note_text': '(съ 23 августа 1884 г.)',
            'credit_summary_text': 'Въ 8 балетахъ—35; въ 8 операхъ—29. Всего—64 раза.',
            'service_periods': [{'start_date_text': '23 августа 1884 г.', 'end_date_text': None, 'end_type': None}],
            'credits': [{'credit_type': 'category_totals', 'label': 'балетахъ', 'count': 35},
                        {'credit_type': 'category_totals', 'label': 'операхъ', 'count': 29},
                        {'credit_type': 'category_totals', 'label': 'Всего', 'count': 64}]}
BELOUSOV_PERSON = '49135ed2-05a5-4fca-9825-638b1792cd11'
LILIYA_PERSON = '83685cf4-26e3-4691-a08b-f55b80a82064'

M_PAGE = 'balletartists_1893-94_SP_p003'
P_PAGES = ('balletartists_1893-94_SP_p002', 'balletartists_1905-06_SP_p002', 'balletartists_1908-09_MSK_p003')

done, log, pages = Counter(), [], {}
def load(pid):
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    return pages[pid]['entries']

for (pid, ln), (old, new) in S.items():
    [e] = [e for e in load(pid) if e.get('list_number') == ln and e['family_name'].split(' ')[0] == old]
    before = e['family_name']; e['family_name'] = new + before[len(old):]
    done['S'] += 1; log.append((pid, ln, 'S', before, e['family_name']))
for (pid, ln), (old, new) in H.items():
    [e] = [e for e in load(pid) if e.get('list_number') == ln and e['family_name'] == old]
    e['family_name'] = new; done['H'] += 1; log.append((pid, ln, 'H', old, new))

es = load(B_PAGE)
assert len(es) == 21 and es[B_INDEX]['family_name'] == 'Ѳеоктистова' and es[B_INDEX]['first_name'] == 'Лилія' \
    and es[B_INDEX]['list_number'] == '10.', es[B_INDEX]
liliya = dict(es[B_INDEX], heading_path='Артистки:', list_number='108.')
es[B_INDEX] = dict(BELOUSOV); es.append(liliya)
done['B'] += 2; log += [(B_PAGE, '10.', 'B', 'Ѳеоктистова, Лилія (slot 10)', 'Бѣлоусовъ 1-й, Геннадій Ивановичъ'),
                        (B_PAGE, '108.', 'B', '(missing)', 'Ѳеоктистова, Лилія Васильевна, appended as e022')]

es = load(M_PAGE)
assert es[2]['family_name'] == 'Михайлова 1-я' and es[2]['service_periods'][0]['end_date_text'] is None
assert es[3]['family_name'] == 'Михайлова 2-я' and es[3]['list_number'] == '77.'
es[2]['service_periods'][0].update(end_date_text='12 декабря 1893 г.', end_type='died')
es[3]['list_number'] = '78.'
done['M'] += 2; log += [(M_PAGE, '77.', 'M', 'no end', '† 12 декабря 1893 г. (died)'), (M_PAGE, '77.', 'M', '77.', '78.')]

for pid in P_PAGES:
    for e in load(pid):
        if e.get('patronymic') or ' ' not in (e.get('first_name') or ''):
            continue
        given, patr = e['first_name'].split(' ')
        assert PATRONYMIC.match(patr), (pid, e['first_name'])
        e['first_name'], e['patronymic'] = given, patr
        done['P'] += 1

for r in log:
    print(f'{r[0][14:]:<17} {r[1]:<5} {r[2]}  {r[3]}  ->  {r[4]}')
print(dict(done), 'on', len(pages), 'pages; plus P split on', len(P_PAGES), 'pages')
assert done == EXPECTED, done

if '--write' in sys.argv:
    import duckdb
    con = duckdb.connect(DB)
    e010, e022 = f'{B_PAGE}__e010', f'{B_PAGE}__e022'
    assert str(con.execute('SELECT person_id FROM entities.person_link WHERE entry_id=?', [e010]).fetchone()[0]) == LILIYA_PERSON
    assert con.execute('SELECT count(*) FROM entities.person_link WHERE entry_id=?', [e022]).fetchone()[0] == 0
    con.execute("UPDATE entities.person_link SET person_id=?, match_method='manual_seed' WHERE entry_id=?", [BELOUSOV_PERSON, e010])
    con.execute("INSERT INTO entities.person_link VALUES (?, ?, 'manual_seed', 1.0)", [e022, LILIYA_PERSON])
    con.close()
    for pid, d in pages.items():
        (RAW / f'{pid}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WRITTEN (raw pages + person_link seed)')
