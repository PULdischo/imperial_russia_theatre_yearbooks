"""Two excerpt titles printed across two lines and stored as two works each (PDF pages read 2026-10-13):
- 9 Dec 1898, Новый (1898-99 printed p. 19): «1-я карт. 2-го д. оп. Волшебный / стрѣлокъ.» after «Паяцы, оп.»;
- 22 Oct 1906 evening, Маріинскій (1906-07 printed p. 92): «2-я карт. 2-го акта и 1-я карт. / 3 акта бал. Конекъ-Горбунокъ.».
Each becomes one work. Run the rebuild steps by hand with full output (known_issues, 2026-10-13, "Trap hit on the way").
usage: uv run python docs/eval/raw_fix_split_excerpt_lines_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
NOTE = 'scan-checked 2026-10-13: one item printed across two lines was stored as two works'
JOBS = [('repertoire_1898-99_p017', '9', 'unspecified', 'Нов', ['1-я карт.', '2-го д. оп. Волшебный стрѣлокъ'],
         '1-я карт. 2-го д. оп. Волшебный стрѣлокъ'),
        ('repertoire_1906-07_p008', '22', 'evening', 'Маріинск', ['2-я карт. 2-го акта и 1-я карт.', '3 акта бал. Конекъ-Горбунокъ'],
         '2-я карт. 2-го акта и 1-я карт. 3 акта бал. Конекъ-Горбунокъ')]
for page, day, session, theater, parts, joined in JOBS:
    f = RAW / f'{page}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
    hits = [s for s in d['sessions'] if s['date_text'].split()[0] == day and s['session'] == session
            and (s.get('theater') or '').startswith(theater)]
    assert len(hits) == 1, (page, len(hits))
    w = hits[0]['works']; titles = [x['work_title'] for x in w]
    i = titles.index(parts[0]); assert titles[i:i + 2] == parts and not w[i]['genre'] and not w[i + 1]['genre'], titles
    hits[0]['works'] = w[:i] + [{'work_title': joined, 'genre': None}] + w[i + 2:]
    hits[0]['_fix_note'] = NOTE
    print(page, hits[0]['date_text'], titles, '\n ->', [x['work_title'] for x in hits[0]['works']])
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
