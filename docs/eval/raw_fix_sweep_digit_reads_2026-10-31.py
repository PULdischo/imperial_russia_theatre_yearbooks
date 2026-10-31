"""BalletArtists: number disputes from the unread-pages sweep, read by Claude on the scans (RG, 2026-10-31: "yes, apply A, B and C").
Evidence: docs/eval/copied_tallies_2026-10-30/sweep/digit_reads_2026-10-31.csv (group D, 4 unsure italic digits, held for RG).
  A  12 misreads (print clear, parts add up). Фонарева 1901-02 and Масловъ 1903-04 run over the page break; the extraction guessed
     the end of the line and dropped the role that ends it at the top of the next page. Парикова's credit rows also held the work
     counts (11, 5, 1) instead of the performance counts. Бессонэ: the print has «Всего—10», not «Все—10».
  B  4 role lists printed but not stored (3 of them at the top of the next page, a line the extraction lost entirely).
  C  5 print slips the extraction had silently corrected, restored as printed (credit_totals_scan_verified.csv, genuine_print_typos.md):
     Куршинская 80 (parts 86), Масловъ 1900-01 98 (96), Домашевъ 22 (23), Голубинъ 1-й 15 (22), Ѳедоровъ 2-й «Всего— разъ» (no number;
     stored like 1910-11 MSK Никитина 1-я, with no «Всего» credit row).
Field edits only; no entry added, removed or moved.
usage: uv run python docs/eval/raw_fix_sweep_digit_reads_2026-10-31.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
def T(label, n): return {'credit_type': 'category_totals', 'label': label, 'count': n}
def R(work, role, n): return {'credit_type': 'named_work', 'label': work, 'role_name': role, 'count': n}
def roles(e): return [c for c in e['credits'] if c['credit_type'] == 'named_work']

FIX = [  # page, entry, family_name, old text, new text, new credits (None = keep)
 ('1890-91_MSK_p001', 10, 'Бессонэ', 'Все—10 разъ.', 'Всего—10 разъ.', None),
 ('1894-95_SP_p007', 16, 'Романовъ', 'Въ 13 балетахъ—35', 'Въ 16 балетахъ—35', None),
 ('1899-00_MSK_p003', 23, 'Парикова',
  'Въ 11 балетахъ—67; въ 5 операхъ—18; въ 1 дивертиссементѣ—1. Всего—86 раза.',
  'Въ 11 балетахъ—67; въ 5 операхъ—15; въ 1 дивертиссементѣ—1. Всего—83 раза.',
  [T('балетахъ', 67), T('операхъ', 15), T('дивертиссементѣ', 1), T('Всего', 83)]),
 ('1900-01_MSK_p003', 22, 'Панова 1-я',
  'Въ 13 балетахъ—46; въ 7 операхъ—46; въ 1 дивертиссементѣ—1. Всего—93 разъ.',
  'Въ 13 балетахъ—52; въ 7 операхъ—46; въ 1 дивертиссементѣ—1. Всего—99 разъ.',
  [T('балетахъ', 52), T('операхъ', 46), T('дивертиссементѣ', 1), T('Всего', 99)]),
 ('1900-01_SP_p003', 16, 'Петерсъ', 'Въ 9 балетахъ—80; въ 2 операхъ—15. Всего—95 разъ.',
  'Въ 9 балетахъ—30; въ 2 операхъ—15. Всего—45 разъ.', [T('балетахъ', 30), T('операхъ', 15), T('Всего', 45)]),
 ('1900-01_SP_p005', 21, 'Яковлева 2-я', 'Въ 20 балетахъ—66; въ 5 операхъ—30. Всего—96 разъ.',
  'Въ 20 балетахъ—68; въ 5 операхъ—30. Всего—98 разъ.', [T('балетахъ', 68), T('операхъ', 30), T('Всего', 98)]),
 ('1900-01_SP_p008', 15, 'Плесскій', 'Въ 16 балетахъ—60; въ 5 операхъ—28; въ 1 драмѣ—8. Всего—96 раза.',
  'Въ 16 балетахъ—60; въ 5 операхъ—28; въ 1 драмѣ—5. Всего—93 раза.',
  [T('балетахъ', 60), T('операхъ', 28), T('драмѣ', 5), T('Всего', 93)]),
 ('1901-02_MSK_p004', 13, 'Чумакова 2-я', 'Въ 10 балетахъ—45; въ 3 операхъ—11; въ дивертисементахъ—8. Всего—64 разъ.',
  'Въ 10 балетахъ—45; въ 3 операхъ—11; въ дивертиссементахъ—3. Всего—59 разъ.',
  [T('балетахъ', 45), T('операхъ', 11), T('дивертиссементахъ', 3), T('Всего', 59)]),
 ('1901-02_SP_p004', 24, 'Фонарева', 'Въ 16 балетахъ—43; въ 5 операхъ—23; въ 1 драмѣ—1. Всего—67 разъ.',
  'Въ 16 балетахъ—45; въ 5 операхъ—23; въ 1 дивертиссементѣ—1. Всего—69 разъ. Въ томъ числѣ: Коппелія (подруга Сванильды—4).',
  [T('балетахъ', 45), T('операхъ', 23), T('дивертиссементѣ', 1), T('Всего', 69), R('Коппелія', 'подруга Сванильды', 4)]),
 ('1903-04_SP_p007', 21, 'Масловъ', 'Въ 23 балетахъ—51; въ 8 операхъ—29; въ 2 драмахъ—1. Всего—81 разъ.',
  'Въ 23 балетахъ—51; въ 8 операхъ—29; въ 2 драмахъ—2. Всего—82 раза. Въ томъ числѣ: Спящая красавица (Каталабютъ—1).',
  [T('балетахъ', 51), T('операхъ', 29), T('драмахъ', 2), T('Всего', 82), R('Спящая красавица', 'Каталабютъ', 1)]),
 ('1904-05_MSK_p001', 12, 'Васильчикова', 'Въ 1 балетѣ—6. Всего—6 разъ.', 'Въ 1 балетѣ—5. Всего—5 разъ.',
  [T('балетѣ', 5), T('Всего', 5)]),
 ('1905-06_SP_p004', 8, 'Соболева', 'Въ 1½ балетахъ — 30', 'Въ 14 балетахъ — 30', [T('балетахъ', 30), T('оперѣ', 5), T('Всего', 35)]),
 # B
 ('1892-93_MSK_p005', 26, 'Рябовъ 1-й', 'Всего—14 разъ.', 'Всего—14 разъ. Въ томъ числѣ: Кипрская статуя (морякъ—3).', 'R'),
 ('1897-98_MSK_p005', 26, 'Ивановъ 2-й', 'Всего—75 разъ.', 'Всего—75 разъ. Въ томъ числѣ: Конекъ-горбунокъ (деревенская баба—1).', 'R'),
 ('1903-04_MSK_p005', 21, 'Дьякъ', 'Всего—63 разъ.', 'Всего—63 раза. Въ томъ числѣ: Конекъ-Горбунокъ (одинъ изъ свиты хана—1).', 'R'),
 ('1903-04_SP_p005', 25, 'Барышистовъ', 'Всего—28 разъ.',
  'Всего—28 разъ. Въ томъ числѣ: Дочь Фараона (придворный царя нубійскаго — 2); Фея куколъ (артельщикъ—1).', 'R'),
 # C
 ('1898-99_MSK_p002', 20, 'Куршинская', 'Всего—86 разъ.', 'Всего—80 разъ.', 'TOT'),
 ('1900-01_SP_p007', 20, 'Масловъ', 'Всего—96 разъ.', 'Всего—98 разъ.', 'TOT'),
 ('1905-06_MSK_p005', 17, 'Домашевъ', 'Всего — 23 раза.', 'Всего — 22 раза.', 'TOT'),
 ('1907-08_MSK_p005', 21, 'Голубинъ 1-й', 'Всего—22 раза.', 'Всего—15 разъ.', 'TOT'),
 ('1901-02_SP_p009', 13, 'Ѳедоровъ 2-й', 'Всего—71 разъ.', 'Всего— разъ.', 'NOTOT'),
]
NEWROLES = {'Рябовъ 1-й': [R('Кипрская статуя', 'морякъ', 3)], 'Ивановъ 2-й': [R('Конекъ-горбунокъ', 'деревенская баба', 1)],
            'Дьякъ': [R('Конекъ-Горбунокъ', 'одинъ изъ свиты хана', 1)],
            'Барышистовъ': [R('Дочь Фараона', 'придворный царя нубійскаго', 2), R('Фея куколъ', 'артельщикъ', 1)]}
TOTALS = {'Куршинская': 80, 'Масловъ': 98, 'Домашевъ': 22, 'Голубинъ 1-й': 15}
assert len(FIX) == 21
pages = {}
for page, i, fam, old, new, cr in FIX:
    pid = f'balletartists_{page}'
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    e = pages[pid]['entries'][i - 1]
    assert e['family_name'] == fam, (page, i, e['family_name'])
    t = e['credit_summary_text']; assert t.count(old) == 1, (fam, old, t)
    e['credit_summary_text'] = t.replace(old, new)
    if isinstance(cr, list): assert not roles(e) or fam in ('Фонарева', 'Масловъ'); e['credits'] = cr
    elif cr == 'R': assert not roles(e), fam; e['credits'] = e['credits'] + NEWROLES[fam]
    elif cr == 'TOT':
        tot = [c for c in e['credits'] if c['label'] == 'Всего']; assert len(tot) == 1; tot[0]['count'] = TOTALS[fam]
    elif cr == 'NOTOT':
        assert sum(c['label'] == 'Всего' for c in e['credits']) == 1; e['credits'] = [c for c in e['credits'] if c['label'] != 'Всего']
if '--write' in sys.argv:
    for pid, d in pages.items(): (RAW / f'{pid}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(FIX), 'entries,', len(pages), 'pages', 'WRITTEN' if '--write' in sys.argv else 'dry run')
