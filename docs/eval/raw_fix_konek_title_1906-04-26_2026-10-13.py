"""26 Apr 1906, Маріинскій (1905-06 printed p. 128; PDF page read 2026-10-13): the cell prints «Конекъ-Горбунокъ, бал.»,
2592 р. 45 к. It was stored «Конекъ-Горбуночкъ», a misreading that kept the night apart from the ballet's other performances.
usage: uv run python docs/eval/raw_fix_konek_title_1906-04-26_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/repertoire_1905-06_p044.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
hits = [s for s in d['sessions'] if s['date_text'].split()[0] == '26' and (s.get('theater') or '').startswith('Маріинск')]
assert len(hits) == 1 and hits[0]['works'] == [{'work_title': 'Конекъ-Горбуночкъ', 'genre': 'бал.'}], [h['works'] for h in hits]
hits[0]['works'][0]['work_title'] = 'Конекъ-Горбунокъ'
hits[0]['_fix_note'] = 'scan-checked 2026-10-13: title was misread as «Конекъ-Горбуночкъ»'
print(hits[0]['works'])
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
