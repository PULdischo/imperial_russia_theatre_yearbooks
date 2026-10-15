"""balletartists_1899-00_MSK_p005, no. 111 (RG, 2026-10-15): the scan prints «111. Чичелева, Елизавета (съ 1 сентября
1899 г.)» with NO patronymic; the extraction supplied «Сергѣевна» (the Ячменева sisters, «Сергѣевна», are on the same
page). Patronymic -> null. Field edit only, no entries added or removed.
usage: uv run python docs/eval/raw_fix_chicheleva_patronymic_2026-10-15.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/balletartists_1899-00_MSK_p005.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
hit = [e for e in d['entries'] if e.get('family_name') == 'Чичелева' and e.get('list_number') == '111.']
assert len(hit) == 1 and hit[0]['patronymic'] == 'Сергѣевна', hit
hit[0]['patronymic'] = None
print('Чичелева, Елизавета: patronymic Сергѣевна -> null')
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8'); print('WRITTEN')
