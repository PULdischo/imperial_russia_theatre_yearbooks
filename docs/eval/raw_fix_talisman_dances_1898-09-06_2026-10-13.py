"""6 Sep 1898, Маріинскій (1898-99 printed p. 2; PDF page read 2026-10-13): the third item of the bill is printed across two
lines, «Танцы и группы изъ 2 акта бал.» / «Талисманъ.». It was stored as two works, the second a whole «Талисманъ». One work
now, «Танцы и группы изъ 2 акта бал. Талисманъ» (the 1898-99 SP ballet list gives Талисманъ on that date). Then run the rebuild
steps by hand with full output.
usage: uv run python docs/eval/raw_fix_talisman_dances_1898-09-06_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/repertoire_1898-99_p000.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
hits = [s for s in d['sessions'] if s['date_text'].split()[0] == '6' and (s.get('theater') or '').startswith('Маріинск')]
OLD = [{'work_title': 'Привалъ кавалеріи', 'genre': 'бал.'}, {'work_title': '1-е д. бал. Дочь Микадо', 'genre': None},
       {'work_title': 'Танцы и группы изъ 2 акта бал.', 'genre': None}, {'work_title': 'Талисманъ', 'genre': None}]
assert len(hits) == 1 and hits[0]['works'] == OLD, [h['works'] for h in hits]
hits[0]['works'] = OLD[:2] + [{'work_title': 'Танцы и группы изъ 2 акта бал. Талисманъ', 'genre': None}]
hits[0]['_fix_note'] = 'scan-checked 2026-10-13: one item printed across two lines was stored as two works'
print(OLD, '\n ->', hits[0]['works'])
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
