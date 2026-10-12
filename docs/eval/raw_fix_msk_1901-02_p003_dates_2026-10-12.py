"""balletartists_1901-02_MSK_p003: 21 rows (nos. 76-99) were stored with no start date though the print gives one
for each. Read at full zoom, 2026-10-12 (RG). Also «82. Поржицкая» (stored Поржипкая), and the dropped «2-я» on
the 1902-03 row printed «26. Трекова 2-я» (surname left verbatim: a print error for Грекова).
Field edits only. usage: ... [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
DATES = {  # list number -> printed tenure note
    '76.': '(съ 1 сентября 1887 г.).', '77.': '(съ 1 сентября 1888 г.).', '79.': '(съ 1 сентября 1898 г.).',
    '80.': '(съ 17 сентября 1881 г.).', '81.': '(съ 1 сентября 1886 г.).', '82.': '(съ 1 сентября 1900 г.).',
    '83.': '(съ 1 сентября 1888 г.).', '84.': '(съ 2 ноября 1881 г.).', '85.': '(съ 1 сентября 1886 г.).',
    '86.': '(съ 1 сентября 1893 г.).', '88.': '(съ 1 сентября 1892 г.).', '90.': '(съ 23 августа 1884 г.).',
    '91.': '(съ 1 августа 1885 г.).', '92.': '(съ 1 августа 1885 г.).', '93.': '(съ 1 сентября 1900 г.).',
    '94.': '(съ 1 сентября 1887 г.).', '95.': '(съ 1 сентября 1894 г.).', '96.': '(съ 1 августа 1885 г.).',
    '97.': '(съ 1 сентября 1894 г.).', '99.': '(съ 23 августа 1884 г.).',
}
f = RAW / 'balletartists_1901-02_MSK_p003.raw.json'
d = json.loads(f.read_text(encoding='utf-8'))
n = 0
for e in d['entries']:
    num = e.get('list_number')
    if num in DATES:
        assert e['service_periods'] == [] and e['tenure_note_text'] == e['credit_summary_text'], num
        note = DATES[num]
        e['tenure_note_text'] = note + ' ' + e['credit_summary_text']
        e['service_periods'] = [{'start_date_text': note.strip('().'), 'end_date_text': None, 'end_type': None}]
        n += 1
    if num == '87.':   # two periods: «съ 1 сентября по 1 декабря 1887 г. и съ 1 марта 1889 г.»
        assert e['service_periods'] == [] and e['family_name'] == 'Романова'
        e['tenure_note_text'] = '(съ 1 сентября по 1 декабря 1887 г. и съ 1 марта 1889 г.). ' + e['credit_summary_text']
        e['service_periods'] = [{'start_date_text': 'съ 1 сентября 1887 г.', 'end_date_text': '1 декабря 1887 г.', 'end_type': None},
                                {'start_date_text': 'съ 1 марта 1889 г.', 'end_date_text': None, 'end_type': None}]
        n += 1
    if num == '82.':
        assert e['family_name'] == 'Поржипкая'; e['family_name'] = 'Поржицкая'
assert n == 21, n
g = RAW / 'balletartists_1902-03_MSK_p001.raw.json'
d2 = json.loads(g.read_text(encoding='utf-8'))
t = [e for e in d2['entries'] if e.get('family_name') == 'Трекова' and e.get('list_number') == '26.']
assert len(t) == 1; t[0]['family_name'] = 'Трекова 2-я'
print(n, 'start dates restored; Поржицкая; Трекова 2-я')
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    g.write_text(json.dumps(d2, ensure_ascii=False, indent=2), encoding='utf-8'); print('WRITTEN')
