"""TheaterSchoolStaff single-season name outliers (issue #134, 2026-10-05): 48 entries whose spelling differed by a small edit from the
person's majority spelling in >=3 other seasons were read BLIND on the scan (3 readers; reader_results/). 38 print exactly as stored (genuine
print variants, left alone); the 9 below print the MAJORITY spelling, i.e. the stored value was a transcription misread. Every edit asserts the
expected old value. Dry run unless --write.  usage: uv run python <this> [--write]"""
import json, sys
R = 'outputs/full_run/raw/%s.raw.json'
FIXES = [  # (page_id, entry, field, old, new)
    ('theaterschoolstaff_1898-99_p001', 'e021', 'patronymic', 'Филотовичъ', 'Филотеровичъ'),
    ('theaterschoolstaff_1908-09_p002', 'e002', 'family_name', 'Зацімовскій', 'Зацимовскій'),
    ('theaterschoolstaff_1897-98_p003', 'e008', 'patronymic', 'Анемполистовичъ', 'Анемподистовичъ'),
    ('theaterschoolstaff_1893-94_p003', 'e016', 'family_name', 'Рофасть', 'Рофастъ'),
    ('theaterschoolstaff_1901-02_p000', 'e017', 'family_name', 'Мирониковъ', 'Миронниковъ'),
    ('theaterschoolstaff_1900-01_p001', 'e034', 'family_name', 'Семеничковъ', 'Семенчиковъ'),
    ('theaterschoolstaff_1902-03_p001', 'e024', 'family_name', 'Легать 1-й', 'Легатъ 1-й'),
    ('theaterschoolstaff_1902-03_p001', 'e025', 'family_name', 'Легать 2-й', 'Легатъ 2-й'),
    ('theaterschoolstaff_1902-03_p002', 'e025', 'family_name', 'Полієвктовъ', 'Поліевктовъ'),
]
EXTRA = json.load(open(sys.argv[sys.argv.index('--extra') + 1])) if '--extra' in sys.argv else []
cache, log, fails = {}, [], []
for pg, e, fld, old, new in FIXES + [tuple(x) for x in EXTRA]:
    cache.setdefault(pg, json.load(open(R % pg)))
    x = cache[pg]['entries'][int(e[1:]) - 1]
    if x.get(fld) != old: fails.append((pg, e, fld, 'expected', old, 'found', x.get(fld))); continue
    x[fld] = new; log.append((pg, e, fld, old, new, x.get('family_name')))
print(len(log), 'edits;', len(fails), 'fails')
for f in fails: print('FAIL', f)
for l in log: print(' ', l[0][-12:], l[1], l[2], '|', l[3], '->', l[4])
if '--write' in sys.argv and not fails:
    import os
    for pg, d in cache.items():
        json.dump(d, open((R % pg) + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace((R % pg) + '.tmp', R % pg)
    json.dump(log, open(sys.argv[0].rsplit('/', 1)[0] + '/name_fixes_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN', len(cache), 'pages')
