"""Fixes from the TheaterSchoolStaff blind sample (issue #134, 2026-10-03). Dry run by default; --write to apply.
Every edit asserts the expected OLD value; any drift aborts without writing. Run: uv run python <this> [--write]"""
import json, re, sys
R = 'outputs/full_run/raw/theaterschoolstaff_%s.raw.json'
D = r'\d{1,2}\s+[а-яѣіѳ]+\s+\d{4}'
log, fails = [], []
cache = {}


def ent(pg, e):
    if pg not in cache: cache[pg] = json.load(open(R % pg))
    return cache[pg]['entries'][int(e[1:]) - 1]


def per(*ps): return [{'start_date_text': a, 'end_date_text': b, 'end_type': c} for a, b, c in ps]


def setf(pg, e, field, old, new):
    x = ent(pg, e)
    if x.get(field) != old: fails.append((pg, e, field, 'expected', old, 'found', x.get(field))); return
    x[field] = new; log.append((pg, e, field, old, new))


def setp(pg, e, old_periods, new_periods, expect_family):
    x = ent(pg, e)
    if x['family_name'] != expect_family: fails.append((pg, e, 'family', expect_family, x['family_name'])); return
    cur = x.get('service_periods') or []
    if cur != old_periods: fails.append((pg, e, 'periods', 'expected', old_periods, 'found', cur)); return
    x['service_periods'] = new_periods; log.append((pg, e, 'service_periods', old_periods, new_periods))


# ---- surnames, each confirmed on a zoomed crop of the scan ----
for pg, e in [('1903-04_p000', 'e002'), ('1906-07_p000', 'e002'), ('1909-10_p000', 'e002')]:
    setf(pg, e, 'family_name', 'Всеволожскій', 'Всеволожской')       # print: Всеволожской (the 1908-09 p003 Moscow row genuinely prints -скій, untouched)
for pg, e in [('1894-95_p001', 'e001'), ('1906-07_p001', 'e003')]:
    setf(pg, e, 'family_name', 'Молась', 'Моласъ')                      # print: Моласъ (16 other seasons already so)

# ---- Тернизьенъ 1895-96 p001: the "† 16 января 1896" printed after Степановъ leaked into the next row ----
setp('1895-96_p001', 'e033', per(('съ 1 декабря 1879 г.', '16 января 1896 г.', 'died')), per(('съ 1 декабря 1879 г.', None, None)), 'Тернизьенъ')

# ---- 1891-92 p002: only e019 (Васильева) and e026 (Сазоновъ) print a leaving note; the rows after each inherited its end ----
for e, fam, start, wrong_end in [('e020', 'Гердтъ', '1 сентября 1888 г.', '1 сентября 1892 г.'), ('e021', 'Давыдовъ', '1 сентября 1889 г.', '1 сентября 1892 г.'),
                                 ('e022', 'Далькевичъ', '1 сентября 1891 г.', '1 сентября 1892 г.'), ('e023', 'Морозовъ', '1 сентября 1889 г.', '1 сентября 1892 г.'),
                                 ('e024', 'Острогорскій', '1 сентября 1888 г.', '1 сентября 1892 г.'), ('e025', 'Писаревъ', '1 сентября 1888 г.', '1 сентября 1892 г.'),
                                 ('e027', 'Соколовъ', '1 сентября 1888 г.', '15 ноября 1891 г.'), ('e028', 'Цвѣтковскій', '1 сентября 1888 г.', '15 ноября 1891 г.')]:
    setp('1891-92_p002', e, per((start, wrong_end, 'left service')), per((start, None, None)), fam)

# ---- Морозовъ: note prints two stints, only the first start was stored (1903-04 p002 e022 already has both) ----
two = per(('1 сентября 1889 г.', '1 сентября 1892 г.', None), ('1 сентября 1893 г.', None, None))
for pg, e in [('1893-94_p002', 'e031'), ('1894-95_p002', 'e027'), ('1896-97_p002', 'e028')]:
    setp(pg, e, per(('съ 1 сентября 1889 г.', None, None)), two, 'Морозовъ')

# ---- notes with a leaving / death marker whose period lacks the end (found by the follow-up sweep) ----
setp('1890-91_p005', 'e016', per(('съ 1 сентября 1888 г.', None, None)), per(('съ 1 сентября 1888 г.', '1 іюля 1891 г.', 'left service')), 'Грековъ')
setp('1901-02_p002', 'e027', per(('1 апрѣля 1902 г.', None, None)), per((None, '1 апрѣля 1902 г.', 'died')), 'Острогорскій')   # "† 1 апрѣля 1902 г." only: death date was stored as a start (cf. Ѳедоровъ 1891-92 p003)
setp('1902-03_p002', 'e026', per(('1 сентября 1895 г.', None, None)), per(('1 сентября 1895 г.', None, 'died')), 'Шемаевъ')            # "† 1902 г." year only -> no end date, end_type died

# ---- 1891-92 p003 e009-e020: start date in the note but no service_periods at all ----
for i in range(9, 21):
    e = 'e%03d' % i; x = ent('1891-92_p003', e)
    ds = re.findall(D, x.get('tenure_note_text') or '')
    if len(ds) != 1 or x.get('service_periods'): fails.append(('1891-92_p003', e, 'unexpected', ds, x.get('service_periods'))); continue
    x['service_periods'] = per((re.search(D, x['tenure_note_text']).group(0) + ' г.', None, None)); log.append(('1891-92_p003', e, 'service_periods', [], x['service_periods']))

print(len(log), 'edits;', len(fails), 'fails')
for f in fails: print('FAIL', f)
for l in log: print(' ', l[0][-12:], l[1], l[2], '|', l[3], '->', l[4])
if '--write' in sys.argv and not fails:
    for pg, d in cache.items():
        json.dump(d, open((R % pg) + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        import os; os.replace((R % pg) + '.tmp', R % pg)
    json.dump(log, open(sys.argv[0].rsplit('/', 1)[0] + '/blind_fixes_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN', len(cache), 'pages')
