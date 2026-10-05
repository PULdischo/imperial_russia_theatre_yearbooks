"""TheaterSchoolStaff surname misreads found by the two-pass section re-read (issue #134, 2026-10-05): both independent passes read a spelling that
differs from stored; a high-zoom blind read (hardsign_check/) confirmed the word-final HARD sign. Old-value assertions; dry run unless --write."""
import json, sys, os
R = 'outputs/full_run/raw/%s.raw.json'
FIXES = [('theaterschoolstaff_1890-91_p000', 'e004', 'Маннь', 'Маннъ'), ('theaterschoolstaff_1892-93_p000', 'e004', 'Маннь', 'Маннъ'),
         ('theaterschoolstaff_1894-95_p000', 'e004', 'Маннь', 'Маннъ'), ('theaterschoolstaff_1891-92_p002', 'e010', 'Тернизьень', 'Тернизьенъ'),
         ('theaterschoolstaff_1893-94_p001', 'e028', 'Тернизьень', 'Тернизьенъ'), ('theaterschoolstaff_1894-95_p001', 'e031', 'Тернизьень', 'Тернизьенъ')]
cache, log, fails = {}, [], []
for pg, e, old, new in FIXES:
    cache.setdefault(pg, json.load(open(R % pg))); x = cache[pg]['entries'][int(e[1:]) - 1]
    if x.get('family_name') != old: fails.append((pg, e, 'expected', old, 'found', x.get('family_name'))); continue
    x['family_name'] = new; log.append((pg, e, old, new))
print(len(log), 'edits;', len(fails), 'fails'); [print('FAIL', f) for f in fails]; [print(' ', l) for l in log]
if '--write' in sys.argv and not fails:
    for pg, d in cache.items():
        json.dump(d, open((R % pg) + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace((R % pg) + '.tmp', R % pg)
    json.dump(log, open(sys.argv[0].rsplit('/', 1)[0] + '/surname_fixes_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN', len(cache), 'pages')
