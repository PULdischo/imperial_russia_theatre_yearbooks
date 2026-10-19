"""productionteam_1902-03_p001 (printed p. 120), RG 2026-10-19: «Оставилъ службу 1 августа 1903 г.» is printed under no. 2
Пипаръ, Христіанъ Петровичъ only (zoomed); the extraction also copied it onto no. 1 Каффи, Иванъ Іосифовичъ. Пипаръ's row keeps
it; the sentence is removed from Каффи's tenure note and his service period's end date / end type are cleared. Same kind as
Иванова 1902-03 and Неменскій 1904-05 (raw_fix_m9_misattributed_and_spellings_2026-10-19.py). Field edit only.
usage: uv run python docs/eval/raw_fix_kaffi_misattributed_2026-10-19.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

f = Path('outputs/full_run/raw/productionteam_1902-03_p001.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
sentence = 'Оставилъ службу 1 августа 1903 г.'
e, nb = d['entries'][20 - 1], d['entries'][21 - 1]          # entry_id numbers are 1-based
assert e['family_name'] == 'Каффи' and nb['family_name'] == 'Пипаръ', (e['family_name'], nb['family_name'])
assert sentence in nb['tenure_note_text'], 'Пипаръ must keep the note'
assert e['tenure_note_text'].count(sentence) == 1, e['tenure_note_text']
e['tenure_note_text'] = e['tenure_note_text'].replace(' ' + sentence, '').replace(sentence, '').rstrip()
sp = e['service_periods']
assert len(sp) == 1 and sp[0]['end_type'] == 'left service' and sp[0]['end_date_text'] == '1 августа 1903 г.', sp
sp[0]['end_date_text'] = None; sp[0]['end_type'] = None
print('Каффи 1902-03: removed «%s» (printed under Пипаръ) ->' % sentence, e['tenure_note_text'])
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8'); print('WRITTEN')
