"""Two Repertoire cells corrected from the scan during the divertissement cell check (2026-10-12; every cell of the 51
ballet-assigned divertissements viewed on a 300-dpi render of the PDF page).
- repertoire_1904-05_p040, 20 Среда, Маріинскій: the cell prints «Парижскій рынокъ, бал. / Ацисъ и Галатея, бал. /
  Дивертиссементъ. 1927 р. 10 к.». The stored fourth work «Фаустъ, оп.» is not there: it is the NEXT day's cell (21 Четв.,
  «Фаустъ, оп.» 2618 р. 72 к., stored correctly as well). Removed (last work of the session, so no id shifts).
- repertoire_1905-06_p042, 8 Суббота, Маріинскій: the cell prints «2-я карт. 1-го д. бал. Виноградная лоза.» and
  «2-е д. бал. Коппелія.»; the stored titles were the bare ballets. Excerpt wording restored (genre inside the title, genre
  field empty, the corpus convention for «N-е д. бал. X»).
- repertoire_1909-10_p021, 13 Воскр., Маріинскій, вечеръ: the cell prints two lines, «Щелкунчикъ, бал.-феерія.» and
  «Дивертиссементъ.»; they were stored fused as ONE work «Щелкунчикъ, бал.-феерія. Дивертиссементъ.». Split into two works
  (the second appended inside the same session; no session added, no event id moves).
Then rebuild. usage: uv run python docs/eval/raw_fix_divertissement_cells_2026-10-12.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')

def session(d, date_text, theater):
    hits = [s for s in d['sessions'] if s['date_text'] == date_text and (s.get('theater') or '').startswith(theater)]
    assert len(hits) == 1, (date_text, len(hits))
    return hits[0]

f1 = RAW / 'repertoire_1904-05_p040.raw.json'
d1 = json.loads(f1.read_text(encoding='utf-8'))
s = session(d1, '20 Среда.', 'Маріин')
if len(s['works']) == 3:
    s['works'].append({'work_title': 'Фаустъ', 'genre': 'оп.'})  # already applied: keep the script re-runnable
assert [w['work_title'] for w in s['works']] == ['Парижскій рынокъ', 'Ацисъ и Галатея', 'Дивертиссементъ', 'Фаустъ'], s['works']
s['works'] = s['works'][:3]
s['_fix_note'] = '2026-10-12: «Фаустъ, оп.» removed, it is the next day\'s cell (21 Четв.); cell viewed on the scan'
print('repertoire_1904-05_p040 20 Среда. Маріинскій: «Фаустъ» removed')

f2 = RAW / 'repertoire_1905-06_p042.raw.json'
d2 = json.loads(f2.read_text(encoding='utf-8'))
s = session(d2, '8 Суббота.', 'Маріин')
new = {'Виноградная лоза': '2-я карт. 1-го д. бал. Виноградная лоза', 'Коппелія': '2-е д. бал. Коппелія'}
n = 0
for w in s['works']:
    if w['work_title'] in new and w.get('genre') == 'бал.':
        print('repertoire_1905-06_p042 8 Суббота. Маріинскій:', w['work_title'], '->', new[w['work_title']])
        w['work_title'], w['genre'] = new[w['work_title']], None; n += 1
assert n == 2, n
s['_fix_note'] = '2026-10-12: excerpt wording restored for Виноградная лоза and Коппелія; cell viewed on the scan'
f3 = RAW / 'repertoire_1909-10_p021.raw.json'
d3 = json.loads(f3.read_text(encoding='utf-8'))
hits = [s for s in d3['sessions'] if s['date_text'] == '13 Воскр.' and s['theater'].startswith('Маріин') and s['session'] == 'evening']
assert len(hits) == 1 and [w['work_title'] for w in hits[0]['works']] == ['Щелкунчикъ, бал.-феерія. Дивертиссементъ.'], hits
hits[0]['works'] = [{'work_title': 'Щелкунчикъ', 'genre': 'бал.-феерія'}, {'work_title': 'Дивертиссементъ', 'genre': None}]
hits[0]['_fix_note'] = '2026-10-12: fused title split into «Щелкунчикъ, бал.-феерія.» and «Дивертиссементъ.» (two printed lines); cell viewed on the scan'
print('repertoire_1909-10_p021 13 Воскр. Маріинскій evening: fused title split into two works')
if '--write' in sys.argv:
    f3.write_text(json.dumps(d3, ensure_ascii=False, indent=2), encoding='utf-8')
    f1.write_text(json.dumps(d1, ensure_ascii=False, indent=2), encoding='utf-8')
    f2.write_text(json.dumps(d2, ensure_ascii=False, indent=2), encoding='utf-8')
