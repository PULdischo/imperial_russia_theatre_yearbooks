"""Raw fixes from the 2026-10-05 homonym sweep (issue #134 follow-up). Dry run unless --write. Every edit asserts the expected OLD value.
All three confirmed against the scan (zoomed crops) before being written here."""
import json, sys
R = 'outputs/full_run/raw/%s.raw.json'
cache, log, fails = {}, [], []
def ent(pg, e):
    cache.setdefault(pg, json.load(open(R % pg)))
    return cache[pg]['entries'][int(e[1:]) - 1]
def fix(pg, e, fam, old, new, why):
    x = ent(pg, e)
    cur = [(s.get('start_date_text'), s.get('end_date_text'), s.get('end_type')) for s in (x.get('service_periods') or [])]
    if x['family_name'] != fam or cur != old: fails.append((pg, e, fam, 'expected', old, 'found', x['family_name'], cur)); return
    x['service_periods'] = [{'start_date_text': a, 'end_date_text': b, 'end_type': c} for a, b, c in new]
    log.append((pg, e, fam, old, new, why))
# Бакина 2-я: the "Оставила службу 1 сентября 1901 г." printed under No.4 Бакина 1-я was also attached to No.5
fix('balletartists_1900-01_MSK_p001', 'e002', 'Бакина 2-я', [('съ 1 сентября 1886 г.', '1 сентября 1901 г.', 'left service')], [('съ 1 сентября 1886 г.', None, None)],
    'leaving line printed under No.4 only (scan-verified); she is listed again 1903-04..1905-06')
# Николаева 3-я Зинаида: no leaving/death note anywhere in the print; she is listed through 1909-10
fix('balletartists_1902-03_MSK_p003', 'e010', 'Николаева', [('1 сентября 1901 г.', '1 декабря 1902 г.', 'died')], [('1 сентября 1901 г.', None, None)],
    'No.69 prints no note at all (scan-verified); invented "died 1 декабря 1902"')
# Русецкій: "Съ 1 іюня 1898 г. назначенъ дѣлопроизводителемъ" is a post change, not leaving service
fix('administration_1897-98_p000', 'e013', 'Русецкій', [('съ 1 ноября 1893 г.', '1 іюня 1898 г.', 'left service')], [('съ 1 ноября 1893 г.', '1 іюня 1898 г.', 'other')],
    'print: appointed дѣлопроизводителемъ on 1 іюня 1898 (post change, scan-verified); end_type other like other transfers')
print(len(log), 'edits;', len(fails), 'fails')
for f in fails: print('FAIL', f)
for l in log: print(' ', l[0][-26:], l[1], l[2], l[3], '->', l[4])
if '--write' in sys.argv and not fails:
    for pg, d in cache.items():
        json.dump(d, open((R % pg) + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        import os; os.replace((R % pg) + '.tmp', R % pg)
    json.dump(log, open(sys.argv[0].rsplit('/', 1)[0] + '/period_fixes_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN', len(cache), 'pages')
