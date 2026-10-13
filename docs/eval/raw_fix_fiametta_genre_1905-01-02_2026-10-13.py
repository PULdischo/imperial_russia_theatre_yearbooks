"""2 Jan 1905 evening, Маріинскій (1904-05 printed p. 112; PDF page read 2026-10-13): the cell prints «Тщетная предосторожность,
бал.» / «2-е д. бал. Фіаметта.» with nothing after the title. The stored genre «бал.» on the second item is not in the print
(RG: "fix this"); every other printing of this excerpt has an empty genre field. Genre field only.
usage: uv run python docs/eval/raw_fix_fiametta_genre_1905-01-02_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/repertoire_1904-05_p022.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
hits = [s for s in d['sessions'] if s['date_text'].split()[0] == '2' and s['session'] == 'evening'
        and (s.get('theater') or '').startswith('Маріинск')]
assert len(hits) == 1 and hits[0]['works'][1] == {'work_title': '2-е д. бал. Фіаметта', 'genre': 'бал.'}, [h['works'] for h in hits]
hits[0]['works'][1]['genre'] = None
hits[0]['_fix_note'] = 'scan-checked 2026-10-13: genre «бал.» on the Фіаметта excerpt is not in the print; removed'
print(hits[0]['works'])
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
