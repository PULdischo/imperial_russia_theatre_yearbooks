"""«Фонъ-Боолъ» -> «Фонъ-Бооль» on two administration rows (RG, 2026-10-12). Both read at full zoom: the print has ь.
Field edit only, no entry moved. Then run docs/eval/rebuild_after_raw_edit.sh.
usage: uv run python docs/eval/raw_fix_fon_bool_2026-10-12.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
for page in ('administration_1898-99_p003', 'administration_1899-00_p003'):
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    hits = [e for e in d['entries'] if e.get('family_name') == 'Фонъ-Боолъ' and e.get('list_number') == '1.']
    assert len(hits) == 1, (page, len(hits))
    hits[0]['family_name'] = 'Фонъ-Бооль'
    print(page, 'Фонъ-Боолъ -> Фонъ-Бооль')
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
