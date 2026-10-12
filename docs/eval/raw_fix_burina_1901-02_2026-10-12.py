"""balletartists_1901-02_MSK_p000, rows 9 and 10 (scan, full zoom, 2026-10-12).
Print: «9. Бурина 1-я, Клавдія Александровна (съ 1 сентября 1899 г.)» and «10. Бурина 2-я.» -- a bare surname,
«Въ 13 балетахъ—52; въ 6 операхъ — 11; въ дивертиссементахъ—7. Всего—70 разъ.»
The extraction had filled row 10 with the name, date and credits of row 11 (Бюхнеръ, Евгенія Фердинандовна),
inventing a «Бурина, Евгенія Фердинандовна». Field edits only; no entry moved.
usage: uv run python docs/eval/raw_fix_burina_1901-02_2026-10-12.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/balletartists_1901-02_MSK_p000.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
r9 = [e for e in d['entries'] if e.get('list_number') == '9.' and e.get('family_name') == 'Бурина' and e.get('first_name') == 'Клавдія']
r10 = [e for e in d['entries'] if e.get('list_number') == '10.' and e.get('family_name') == 'Бурина' and e.get('patronymic') == 'Фердинандовна']
assert len(r9) == 1 and len(r10) == 1
r9[0]['family_name'] = 'Бурина 1-я'
r10[0].update({
    'family_name': 'Бурина 2-я', 'first_name': None, 'patronymic': None, 'tenure_note_text': None, 'service_periods': [],
    'credit_summary_text': 'Въ 13 балетахъ—52; въ 6 операхъ — 11; въ дивертиссементахъ—7. Всего—70 разъ.',
    'credits': [{'credit_type': 'category_totals', 'label': 'балетахъ', 'count': 52},
                {'credit_type': 'category_totals', 'label': 'операхъ', 'count': 11},
                {'credit_type': 'category_totals', 'label': 'дивертиссементахъ', 'count': 7},
                {'credit_type': 'category_totals', 'label': 'Всего', 'count': 70}]})
print('rows 9 and 10 corrected')
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8'); print('WRITTEN')
