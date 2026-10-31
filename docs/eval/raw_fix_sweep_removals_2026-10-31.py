"""BalletArtists: 14 tallies stored on people who print none, found by the unread-pages sweep (RG, 2026-10-31: "yes").

The sweep (docs/eval/copied_tallies_2026-10-30/sweep/, commit 4995af9) read every BalletArtists page not read in full before (344
pages, 7,550 entries) and compared it with the store. Each case below was then read by Claude on the scan (embedded page image):
nothing at all is printed under the person.
  13 bare fragments: only «Всего—N разъ» stored, N being the previous entry's total (Мокшева's «Всего—1» matches nobody's).
   1 near-copy: 1907-08 MSK no. 60 Мыльникова held no. 61 Невельская's full line with «13 балетахъ» for «12»; she prints only
     «Оставила службу 24 февраля 1907 г.», already in her tenure note.
-> credit_summary_text null, credits []. Tenure notes untouched. Field edits only; no entry added, removed or moved.
usage: uv run python docs/eval/raw_fix_sweep_removals_2026-10-31.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
REMOVE = [('1891-92_SP_p006', 24, 'Степановъ', 'Всего—28 разъ.'), ('1893-94_MSK_p004', 5, 'Френева', 'Всего—49 разъ.'),
          ('1894-95_MSK_p004', 21, 'Френева', 'Всего—11 разъ.'), ('1894-95_MSK_p004', 30, 'Чумичева', 'Всего—37 разъ.'),
          ('1894-95_SP_p003', 3, 'Мокшева', 'Всего—1 разъ.'), ('1894-95_SP_p007', 23, 'Степановъ', 'Всего—60 разъ.'),
          ('1895-96_MSK_p002', 16, 'Кузнецова', 'Всего—69 разъ.'), ('1895-96_MSK_p002', 17, 'Лузина 1-я', 'Всего—69 разъ.'),
          ('1895-96_MSK_p002', 20, 'Марковская', 'Всего—69 разъ.'), ('1898-99_MSK_p005', 3, 'Центерова', 'Всего—79 разъ.'),
          ('1898-99_MSK_p005', 4, 'Черепова 1-я', 'Всего—79 разъ.'), ('1898-99_MSK_p005', 13, 'Ѳедорова 1-я', 'Всего—79 разъ.'),
          ('1899-00_MSK_p003', 24, 'Петрова 1-я', 'Всего—88 разъ.'),
          ('1907-08_MSK_p003', 10, 'Мыльникова', 'Въ 13 балетахъ—45; въ 5 дивертиссментахъ—5; въ 10 операхъ—61. Всего—111 разъ.')]
assert len(REMOVE) == 14
pages = {}
for page, i, fam, old in REMOVE:
    pid = f'balletartists_{page}'
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    e = pages[pid]['entries'][i - 1]
    assert e['family_name'] == fam and e['credit_summary_text'] == old, (page, i, e['family_name'], e['credit_summary_text'])
    e['credit_summary_text'] = None; e['credits'] = []
if '--write' in sys.argv:
    for pid, d in pages.items(): (RAW / f'{pid}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(REMOVE), 'entries,', len(pages), 'pages', 'WRITTEN' if '--write' in sys.argv else 'dry run')
