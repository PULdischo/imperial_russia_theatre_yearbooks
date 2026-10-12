"""Graduates pages: two places where the printed posting sentence was not applied correctly (RG, 2026-10-12).
1. graduates_1898-99_p002 (Moscow class of 1899, 12 rows): the sentence «Окончили курсъ весной 1899 года. Всѣ ...
   опредѣлены на службу съ 1 сентября 1899 года въ Московскую балетную труппу» was parsed as a period running FROM
   «весной 1899 года» TO 1 September. Start = съ 1 сентября 1899 года (docs/ballet_graduates_tenure.csv agrees).
2. graduates_1910-11_p000, Безкоровайная, Елизавета: the class is posted «съ 1 іюня 1911 г. ... за исключеніемъ больной
   г-жи Безкоровайной» -- she is the exception, so she has no start date. The note stays verbatim.
Field edits only. usage: ... [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
f1 = RAW / 'graduates_1898-99_p002.raw.json'; d1 = json.loads(f1.read_text(encoding='utf-8'))
n = 0
for e in d1['entries']:
    sp = e.get('service_periods') or []
    if len(sp) == 1 and sp[0]['start_date_text'] == 'весной 1899 года' and sp[0]['end_date_text'] == '1 сентября 1899 года':
        e['service_periods'] = [{'start_date_text': 'съ 1 сентября 1899 года', 'end_date_text': None, 'end_type': None}]; n += 1
assert n == 12, n
f2 = RAW / 'graduates_1910-11_p000.raw.json'; d2 = json.loads(f2.read_text(encoding='utf-8'))
b = [e for e in d2['entries'] if e.get('family_name') == 'Безкоровайная']
assert len(b) == 1 and len(b[0]['service_periods']) == 1
b[0]['service_periods'] = []
print('12 start dates corrected; Безкоровайная undated')
if '--write' in sys.argv:
    f1.write_text(json.dumps(d1, ensure_ascii=False, indent=2), encoding='utf-8')
    f2.write_text(json.dumps(d2, ensure_ascii=False, indent=2), encoding='utf-8'); print('WRITTEN')
