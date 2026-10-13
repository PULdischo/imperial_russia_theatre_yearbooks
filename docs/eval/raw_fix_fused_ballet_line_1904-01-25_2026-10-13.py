"""25 Jan 1904 evening, Маріинскій (1903-04 printed p. 26): one running line names three items, «1-я карт. 3-го акта бал.
Конекъ-Горбунокъ, бал. Пахита и 2-е д. бал. Фіаметто.» (PDF page read 2026-10-13: the transcription matched the print). RG,
2026-10-13: "split this into 3 performances for this event". The words stay as printed, including «Фіаметто»; «бал. Пахита» is
stored as title «Пахита», genre «бал.», like every other whole-ballet line. The printed line is kept in _printed_line.
Run the rebuild steps by hand with full output afterwards (see known_issues, 2026-10-13, "Trap hit on the way").
usage: uv run python docs/eval/raw_fix_fused_ballet_line_1904-01-25_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/repertoire_1903-04_p024.raw.json')
LINE = '1-я карт. 3-го акта бал. Конекъ-Горбунокъ, бал. Пахита и 2-е д. бал. Фіаметто'
d = json.loads(f.read_text(encoding='utf-8'))
hits = [s for s in d['sessions'] if s['date_text'].split()[0] == '25' and s['session'] == 'evening'
        and (s.get('theater') or '').startswith('Маріинск')]
assert len(hits) == 1 and hits[0]['works'] == [{'work_title': LINE, 'genre': 'бал.'}], [h['works'] for h in hits]
s = hits[0]
s['works'] = [{'work_title': '1-я карт. 3-го акта бал. Конекъ-Горбунокъ', 'genre': None},
              {'work_title': 'Пахита', 'genre': 'бал.'},
              {'work_title': '2-е д. бал. Фіаметто', 'genre': None}]
s['_printed_line'] = LINE + '.'
s['_fix_note'] = 'one printed line split into its three items (RG, 2026-10-13); wording unchanged'
print(LINE, '\n ->', s['works'])
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
