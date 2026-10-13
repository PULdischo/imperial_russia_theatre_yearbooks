"""Three ballet cells read on the scan 2026-10-13 (RG: "address this"). Then rebuild (docs/eval/rebuild_after_raw_edit.sh).
- 12 Sep 1904, Маріинскій (1904-05 printed p. 92): the cell prints three lines, «Жемчужина, бал.» / «1, 3 д. и 2-я карт. 4 д.
  балета.» / «Волшебное зеркало, бал.». The act list belongs to «Волшебное зеркало» (the 1904-05 SP ballet list enters it as
  «(1-е, 3-е д. и 2-я карт. 4-го д.)» with this one date); it was stored as part of the «Жемчужина» title.
- 8 Feb 1904 evening, Большой (1903-04 printed p. 29; PDF page at high zoom): «2-е д. бал. Лебединое озеро.» and «6 и 7 карт.
  бал. Конекъ-Горбунокъ.»; stored «2-е х.» and «6 и 7 март.».
- 28 Dec 1905 morning, Большой (1905-06 printed p. 107): «1-е д. бал. Лебединое озеро.»; stored «Лебединное».
usage: uv run python docs/eval/raw_fix_ballet_excerpt_cells_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
NOTE = 'scan-checked 2026-10-13 (raw_fix_ballet_excerpt_cells_2026-10-13.py)'
W = lambda t, g: {'work_title': t, 'genre': g}
# page, day, session, theater prefix, works expected now, works the print has
JOBS = [('repertoire_1904-05_p002', '12', 'unspecified', 'Маріинск',
         [W('Жемчужина, 1, 3 д. и 2-я карт. 4 д. балета.', 'бал.'), W('Волшебное зеркало', 'бал.')],
         [W('Жемчужина', 'бал.'), W('1, 3 д. и 2-я карт. 4 д. балета. Волшебное зеркало', 'бал.')]),
        ('repertoire_1903-04_p027', '8', 'evening', 'Больш',
         [W('2-е х. бал. Лебединое озеро', None), W('6 и 7 март. бал. Конекъ-Горбунокъ', None), W('5-я карт. бал. Эсмеральда', None)],
         [W('2-е д. бал. Лебединое озеро', None), W('6 и 7 карт. бал. Конекъ-Горбунокъ', None), W('5-я карт. бал. Эсмеральда', None)]),
        ('repertoire_1905-06_p023', '28', 'morning', 'Больш',
         [W('1-е д. Лебединное озеро', 'бал.'), W('2, 3, 4, 6 и 7 карт. „Волшебное зеркало“', 'бал.')],
         [W('1-е д. Лебединое озеро', 'бал.'), W('2, 3, 4, 6 и 7 карт. „Волшебное зеркало“', 'бал.')])]
for page, day, session, theater, old, new in JOBS:
    f = RAW / f'{page}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
    hits = [s for s in d['sessions'] if s['date_text'].split()[0] == day and s['session'] == session
            and (s.get('theater') or '').startswith(theater)]
    assert len(hits) == 1 and hits[0]['works'] == old, (page, [h['works'] for h in hits])
    hits[0]['works'], hits[0]['_fix_note'] = new, NOTE
    print(page, hits[0]['date_text'], '\n   ', old, '\n ->', new)
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
