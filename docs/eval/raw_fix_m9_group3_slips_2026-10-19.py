"""M9 group 3 side slips (RG, 2026-10-19: "and fix these"). Read on the full-resolution PDF images, zoomed.
- balletartists_1903-04_MSK_p008 no. 80 Ширяевъ, Сергѣй: the print has «Лебединое озеро (церемоніймейстеръ — 3)»; the extraction
  read «перемоніймейстеръ» (in the note text, the credit line and the credit's role name). -> «церемоніймейстеръ».
  (The same misread is stored on 10 other entries; NOT changed here -- each needs its own scan check.)
- balletartists_1898-99_MSK_p004 no. 93 Свѣтинская, Марія: the credit line «Въ 1 балетѣ—1. Всего—1 разъ.» is printed once but
  stored twice (credit_summary_text and again inside tenure_note_text). -> removed from tenure_note_text.
  (913 other rows carry the same duplication; NOT changed here.)
«44. Решке» (1910-11 Moscow musicians, for 74) is already stored as printed; nothing to change.
Field edits only. usage: uv run python docs/eval/raw_fix_m9_group3_slips_2026-10-19.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')


def fix_strings(obj, old, new):
    n = 0
    if isinstance(obj, dict):
        items = obj.items()
    else:
        items = enumerate(obj)
    for k, v in list(items):
        if isinstance(v, str) and old in v:
            n += v.count(old); obj[k] = v.replace(old, new)
        elif isinstance(v, (dict, list)):
            n += fix_strings(v, old, new)
    return n


out = []
f = RAW / 'balletartists_1903-04_MSK_p008.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
e = d['entries'][13 - 1]; assert e['family_name'] == 'Ширяевъ' and e['list_number'] == '80.'
n = fix_strings(e, 'перемоніймейстеръ', 'церемоніймейстеръ'); assert n == 3, n
print(f'Ширяевъ 1903-04: перемоніймейстеръ -> церемоніймейстеръ x{n}'); out.append((f, d))

f = RAW / 'balletartists_1898-99_MSK_p004.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
e = d['entries'][10 - 1]; assert e['family_name'] == 'Свѣтинская' and e['list_number'] == '93.'
cred = e['credit_summary_text']; t = e['tenure_note_text']
assert cred and t.endswith(' ' + cred), (t, cred)
e['tenure_note_text'] = t[: -len(cred)].rstrip()
print('Свѣтинская 1898-99: tenure note ->', e['tenure_note_text']); out.append((f, d))

if '--write' in sys.argv:
    for f, d in out:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WRITTEN')
