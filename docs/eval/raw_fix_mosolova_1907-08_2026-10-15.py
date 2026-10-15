"""balletartists_1907-08_MSK_p003, no. 57 (RG, 2026-10-15): the scan prints «57. Мосолова 1-я, Вѣра Владими-|ровна (съ 1
сентября 1893 г.).» The extraction shifted the ordinal into first_name ('1-я'), the first name into patronymic ('Вѣра') and the
patronymic into tenure_note_text ('Владиміровна (съ ...'). Restored to the printed fields, ordinal kept on the surname as in
1906-07 and 1908-09 («Мосолова 1-я»). Field edit only, no entries added or removed (person_link entry_ids unchanged).
usage: uv run python docs/eval/raw_fix_mosolova_1907-08_2026-10-15.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/balletartists_1907-08_MSK_p003.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
hit = [e for e in d['entries'] if e.get('family_name') == 'Мосолова' and e.get('list_number') == '57.']
assert len(hit) == 1 and hit[0]['first_name'] == '1-я' and hit[0]['patronymic'] == 'Вѣра', hit
e = hit[0]
assert e['tenure_note_text'] == 'Владиміровна (съ 1 сентября 1893 г.).', e['tenure_note_text']
e['family_name'], e['first_name'], e['patronymic'] = 'Мосолова 1-я', 'Вѣра', 'Владиміровна'
e['tenure_note_text'] = '(съ 1 сентября 1893 г.).'
print('Мосолова no. 57: -> Мосолова 1-я / Вѣра / Владиміровна; tenure_note_text -> (съ 1 сентября 1893 г.).')
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8'); print('WRITTEN')
