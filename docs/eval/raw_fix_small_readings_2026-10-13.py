"""Small scan readings (RG, 2026-10-13: "and get these fixed"). Every change below was read on the scan (PDF pages, or the
spread bands in outputs/title_check_2026-10-10/align_crops) on 2026-10-13. Run AFTER raw_fix_free_matinee_banner_sweep_2026-10-13.py.

A. Genre repeated from the title, not printed as a separate label -> genre None (the print gives the label inside the title only):
   «Наканунѣ, возможный случай» x5, «Снѣгурочка, весенняя сказка» x4 (Новый, 1901-02), «1, 2, 3 и 4 д. оп. Гугеноты» x2,
   «1-е и 2-е д. опер. Орфей въ аду» x1. «Разрывъ-трава, фант. сказка.» x2 (1901-02 p015) -> title/genre as on the other 30 rows.
B. 1901-02 p015, Новый: «Снѣгурочка» is the Sunday УТРО (25 Nov, 2 Dec 1901), not the Saturday; the Saturdays (24 Nov, 1 Dec)
   print a dash. The Sunday bills are the ВЕЧЕРЪ. Dark Saturdays are appended at the END (session ids are positional).
C. Георгіевскіе кавалеры free performances: 26 Nov 1896 banner is on the evening («Старый закалъ»), was stored on 25 Nov;
   26 Nov 1892 and 26 Nov 1897 (Александринскій) print NO receipts: the stored figures were the neighbouring cell's
   (Михайловскій 761 р. 7 к.; 27 Nov 1583 р. 50 к.).
D. 1898-99 p028: the banner is printed above 24 Feb 1899 only; it had been copied onto every session of 24-26 Feb. Kept on the
   three 24 Feb mornings (no receipts). Also «Девятый валъ, др.» / «Ночное сц.» as printed.
E. Banner stored on a paid, labelled evening of a free-matinee day (the print sets one banner across the day's row; 202 of 227
   such evenings in the corpus carry none): removed.
F. 23 Nov 1893, Александринскій: two works were inside the annotation. 15 Jan 1895, Малый: «Сіятельный зять, ком.» +
   «Парики, опер.» (stored as one work «Большой зять, ком.»); morning «Трудовой хлѣбъ» (stored «Новой хлѣбъ»).
G. Titles: «3-е и 4-е д. бал. Конекъ-горбунокъ» (9 Dec 1892), «2-е д. ком. Своя семья» and «5-е д. траг. Димитрій Донской»
   (30 Aug 1893), «2-я и 3-я карт. пьесы Зачѣмъ пойдешь, то и найдешь» (17 Apr 1897).
usage: uv run python docs/eval/raw_fix_small_readings_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
NOTE = 'scan-checked 2026-10-13 (small readings): '
docs = {}
def page(p):
    if p not in docs:
        docs[p] = json.loads((RAW / f'repertoire_{p}.raw.json').read_text(encoding='utf-8'))
    return docs[p]
def one(p, day, theater, session=None):
    hits = [s for s in page(p)['sessions'] if s['date_text'].split()[0] == day and (s.get('theater') or '').startswith(theater)
            and (session is None or s['session'] == session)]
    assert len(hits) == 1, (p, day, theater, session, len(hits))
    return hits[0]
def note(s, text):
    s['_fix_note'] = (s['_fix_note'] + ' | ' if s.get('_fix_note') else '') + NOTE + text
n = 0
# A
A = [('1903-04_p008', '27', 'Михайл', 'Наканунѣ, возможный случай', 'др.'), ('1903-04_p036', '27', 'Алекс', 'Наканунѣ, возможный случай', 'др.'),
     ('1903-04_p036', '2', 'Алекс', 'Наканунѣ, возможный случай', 'др.'), ('1904-05_p008', '18', 'Михайл', 'Наканунѣ, возможный случай.', 'драм.'),
     ('1904-05_p008', '22', 'Михайл', 'Наканунѣ, возможный случай', 'драм.'),
     ('1901-02_p001', '30', 'Нов', 'Снѣгурочка, весенняя сказка.', 'сказка'), ('1901-02_p009', '21', 'Нов', 'Снѣгурочка, весенняя сказка', 'сказка'),
     ('1901-02_p015', '24', 'Нов', 'Снѣгурочка, весенняя сказка.', 'сказка'), ('1901-02_p015', '1', 'Нов', 'Снѣгурочка, весенняя сказка.', 'сказка'),
     ('1906-07_p026', '18', 'Маріин', '1, 2, 3 и 4 д. оп. Гугеноты', 'оп.'), ('1907-08_p008', '18', 'Маріин', '1, 2, 3 и 4 д. оп. Гугеноты.', 'оп.'),
     ('1901-02_p016', '15', 'Маріин', '1-е и 2-е д. опер. Орфей въ аду', 'опер.')]
for p, day, th, title, genre in A:
    ss = [s for s in page(p)['sessions'] if s['date_text'].split()[0] == day and s['theater'].startswith(th)
          and any(w['work_title'] == title and w['genre'] == genre for w in s['works'])]
    assert len(ss) == 1, (p, day, title, len(ss))
    for w in ss[0]['works']:
        if w['work_title'] == title:
            w['genre'] = None; w['work_title'] = title.rstrip('.')
    note(ss[0], f'no separate genre label printed after «{title.rstrip(".")}» (was {genre!r})'); n += 1
for day in ('26', '29'):
    s = one('1901-02_p015', day, 'Нов'); w = s['works']
    assert len(w) == 1 and w[0] == {'work_title': 'Разрывъ-трава, фант. сказка.', 'genre': 'сказка'}, w
    w[0]['work_title'], w[0]['genre'] = 'Разрывъ-трава', 'фант. сказка'; note(s, 'printed «Разрывъ-трава, фант. сказка.»'); n += 1
# B
d = page('1901-02_p015')
for sat, sun in (('24 Суббота.', '25 Воскрес.'), ('1 Суббота.', '2 Воскрес.')):
    m = one('1901-02_p015', sat.split()[0], 'Нов'); e = one('1901-02_p015', sun.split()[0], 'Нов')
    assert m['works'][0]['work_title'] == 'Снѣгурочка, весенняя сказка' and m['session'] == e['session'] == 'unspecified'
    m['date_text'], m['session'] = sun, 'morning'; e['session'] = 'evening'
    note(m, f'printed as the Sunday УТРО; was on {sat}'); note(e, 'printed as the Sunday ВЕЧЕРЪ')
    d['sessions'].append({'date_text': sat, 'month_text': None, 'year_text': None, 'session': 'unspecified', 'theater': m['theater'],
                          'is_dark': True, 'receipts_text': None, 'annotation': None, 'works': [],
                          '_fix_note': NOTE + 'the Saturday cell prints a dash; appended at the end'}); n += 3
# C
GEO = 'Безплатный спектакль для гг. георгіевскихъ кавалеровъ.'
a = one('1896-97_pair010', '25', 'Алекс'); b = one('1896-97_pair010', '26', 'Алекс', 'evening')
assert a['annotation'] == GEO and not b['annotation'] and not b['receipts_text'] and b['works'][0]['work_title'] == 'Старый закалъ'
a['annotation'], b['annotation'] = None, GEO
note(a, 'the Georgievsky banner belongs to 26 Nov evening'); note(b, 'banner printed in this cell; was stored on 25 Nov'); n += 2
for p, rec, why in (('1892-93_pair010', '761 р. 7 к.', 'Михайловскій 26 Nov'), ('1897-98_pair010', '1583 р. 50 к.', 'Александринскій 27 Nov')):
    s = one(p, '26', 'Алекс'); assert s['receipts_text'] == rec and 'еоргіевскихъ' in s['annotation'], s
    s['receipts_text'] = None; note(s, f'no receipts printed for the free performance; {rec} is the figure of {why}'); n += 1
# D
B = 'Безплатные спектакли для воспитанниковъ столичныхъ учебныхъ заведеній.'
for s in page('1898-99_p028')['sessions']:
    day = s['date_text'].split()[0]
    if s.get('annotation') == B and (day in ('25', '26') or (day == '24' and s['receipts_text'])):
        s['annotation'] = None; note(s, 'banner is printed above 24 Feb only and belongs to the three mornings without receipts'); n += 1
assert sum(1 for s in page('1898-99_p028')['sessions'] if s.get('annotation') == B) == 3
s = one('1898-99_p028', '24', 'Алекс', 'evening')
assert [w['work_title'] for w in s['works']] == ['Девятый вальс', 'Ночное сц.']
s['works'] = [{'work_title': 'Девятый валъ', 'genre': 'др.'}, {'work_title': 'Ночное', 'genre': 'сц.'}]; n += 1
# E
E = [('1896-97_pair010', '14', ['Алекс', 'Больш', 'Малый', 'Маріин', 'Михайл']), ('1896-97_pair012', '6', ['Алекс', 'Больш', 'Малый', 'Маріин', 'Михайл']),
     ('1901-02_p012', '14', ['Маріин']), ('1904-05_p033', '24', ['Больш', 'Малый', 'Нов']), ('1906-07_p015', '14', ['Больш', 'Малый', 'Нов'])]
for p, day, ths in E:
    for th in ths:
        s = one(p, day, th, 'evening'); assert (s['annotation'] or '').startswith('Безплатные спектакли') and s['receipts_text'], (p, th, s)
        rest = s['annotation'].split('заведеній.', 1)[1].strip() or None
        s['annotation'] = rest; note(s, 'free-matinee banner removed from the paid evening'); n += 1
# F
s = one('1893-94_pair010', '23', 'Алекс')
assert s['annotation'] == 'Бенефисъ г-жи Дюжиковой 1-й. У своихъ, ком. Не пойманъ—не воръ, посл.' and len(s['works']) == 1
s['annotation'] = 'Бенефисъ г-жи Дюжиковой 1-й.'
s['works'] = [{'work_title': 'У своихъ', 'genre': 'ком.'}, {'work_title': 'Не пойманъ—не воръ', 'genre': 'посл.'},
              {'work_title': 'Дядя Беккеръ подшутилъ', 'genre': 'опер.'}]
note(s, 'two works were inside the annotation; «подшутилъ»'); n += 1
s = one('1894-95_pair008', '15', 'Малый', 'evening'); assert s['works'] == [{'work_title': 'Большой зять, ком.', 'genre': 'опер.'}], s['works']
s['works'] = [{'work_title': 'Сіятельный зять', 'genre': 'ком.'}, {'work_title': 'Парики', 'genre': 'опер.'}]; note(s, 'two works printed'); n += 1
s = one('1894-95_pair008', '15', 'Малый', 'morning'); assert s['works'][0]['work_title'] == 'Новой хлѣбъ'
s['works'][0]['work_title'] = 'Трудовой хлѣбъ'; note(s, 'printed «Трудовой хлѣбъ, сц.»'); n += 1
# G
G = [('1892-93_pair012', '9', 'Больш', '3-е и4-е д. бал. Конекъ-горбунокъ', '3-е и 4-е д. бал. Конекъ-горбунокъ'),
     ('1893-94_pair002', '30', 'Михайл', '2-е д. ком. Свои семьи', '2-е д. ком. Своя семья'),
     ('1893-94_pair002', '30', 'Алекс', '5-е д. траг. Дмитрій Донской', '5-е д. траг. Димитрій Донской'),
     ('1896-97_pair024', '17', 'Алекс', '2-я и 3-я карт. пьесы Затѣмъ пойдешь, то и найдешь', '2-я и 3-я карт. пьесы Зачѣмъ пойдешь, то и найдешь')]
for p, day, th, old, new in G:
    s = one(p, day, th); ws = [w for w in s['works'] if w['work_title'] == old]; assert len(ws) == 1, (p, old)
    ws[0]['work_title'] = new; note(s, f'title printed «{new}»'); n += 1
print(n, 'changes on', len(docs), 'pages', '(written)' if '--write' in sys.argv else '(dry run)')
if '--write' in sys.argv:
    for p, d in docs.items():
        (RAW / f'repertoire_{p}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
