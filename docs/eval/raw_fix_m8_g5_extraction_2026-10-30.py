"""M8 group 5 scan checks (RG, 2026-10-30: "Fix them"). Read on the full-resolution PDF images, zoomed (agent + re-read by Claude):
- theaterschoolstaff_1895-96_p001 no. 18 Петровъ, Василій Ивановичъ (printed p. 466): «(съ 1 сентября 1894 г.). Выразительное чтеніе.»
  -- the extraction read 1893. -> 1894 (note text and service-period start).
- theaterschoolstaff_1904-05_p003 no. 5 Сизовъ, Владиміръ Ильичъ (Moscow school, «Почетные члены конференціи», printed p. 79): the entry
  prints no start date, only «† 19 октября 1904 г.»; the extraction copied the death date into the start. -> start cleared, death kept.
(Легатъ 1906-07 «17 іюня 1888», also flagged, is already stored correctly.) Field edits only.
usage: uv run python docs/eval/raw_fix_m8_g5_extraction_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
out = []
f = RAW / 'theaterschoolstaff_1895-96_p001.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
e = d['entries'][23 - 1]; assert e['family_name'] == 'Петровъ' and e['list_number'] == '18.'
assert e['tenure_note_text'] == 'съ 1 сентября 1893 г.' and e['service_periods'][0]['start_date_text'] == 'съ 1 сентября 1893 г.'
e['tenure_note_text'] = 'съ 1 сентября 1894 г.'; e['service_periods'][0]['start_date_text'] = 'съ 1 сентября 1894 г.'
print('Петровъ 1895-96: 1893 -> 1894'); out.append((f, d))
f = RAW / 'theaterschoolstaff_1904-05_p003.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
e = d['entries'][6 - 1]; assert e['family_name'] == 'Сизовъ' and e['list_number'] == '5.'
sp = e['service_periods']; assert len(sp) == 1 and sp[0]['start_date_text'] == '19 октября 1904 г.' and sp[0]['end_type'] == 'died'
sp[0]['start_date_text'] = None
print('Сизовъ 1904-05: start cleared (death date kept)'); out.append((f, d))
if '--write' in sys.argv:
    for f, d in out: f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WRITTEN')
