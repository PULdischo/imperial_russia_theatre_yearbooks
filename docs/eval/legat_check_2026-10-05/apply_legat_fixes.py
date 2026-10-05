"""Apply the blind-read corrections for the Легат* surnames (2026-10-05): ь->ъ (41 of 42 rows; the 1890-91 SP p003 no. 64 ь is the genuine print and stays),
missing printed ordinals added to family_name (ordinal is part of family_name corpus-wide), Сергій->Сергѣй (1903-04 no. 42), and the merged first_name+patronymic
split on 1893-94 SP p002. Every edit asserts the old value. Dry run unless --write. Run from the repo root."""
import sys, json, os
sys.path.insert(0, 'docs/eval/legat_check_2026-10-05')
from reader_headings import R
RAW = 'outputs/full_run/raw/'
WRITE = '--write' in sys.argv
pages = {}; log = []; fails = []
for (pid, ln), (fam, fn, pat) in R.items():
    if pid not in pages: pages[pid] = json.load(open(RAW + pid + '.raw.json'))
    es = [(i, e) for i, e in enumerate(pages[pid]['entries']) if (e.get('list_number') or '') == ln and (e.get('family_name') or '').startswith('Легать')]
    if len(es) != 1: fails.append((pid, ln, 'expected 1 stored Легать row, found', len(es))); continue
    i, e = es[0]
    def setf(k, old, new):
        if e.get(k) != old: fails.append((pid, ln, k, 'stored', e.get(k), 'expected', old)); return
        if old != new: log.append((pid, f'e{i+1:03d}', k, old, new)); e[k] = new
    setf('family_name', e['family_name'], fam)
    if (pid, ln) == ('balletartists_1903-04_SP_p007', '42.'): setf('first_name', 'Сергій', 'Сергѣй')
    if pid == 'balletartists_1893-94_SP_p002' and ln in ('66.', '67.'):
        if e.get('first_name') in ('Вѣра Густавовна', 'Евгенія Густавовна') and not e.get('patronymic'):
            f0 = e['first_name']; setf('first_name', f0, fn); log.append((pid, f'e{i+1:03d}', 'patronymic', None, pat)); e['patronymic'] = pat
        else: fails.append((pid, ln, 'unexpected first/patronymic', e.get('first_name'), e.get('patronymic')))
print(len(log), 'edits,', len(fails), 'fails')
for l in log: print(' ', l)
for f in fails: print('FAIL', f)
if WRITE and not fails:
    for pid, d in pages.items():
        tmp = RAW + pid + '.raw.json.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, RAW + pid + '.raw.json')
    json.dump(log, open('docs/eval/legat_check_2026-10-05/apply_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN', len(pages), 'pages')
