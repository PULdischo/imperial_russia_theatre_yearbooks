"""Restore a print slip the extraction silently corrected: Маріинскій 7 Feb 1893 morning (repertoire_1892-93_pair018, printed p.18)
prints «Сцепа изъ бал. Корсаръ» (п set for н, as «Паяда» for «Наяда»); raw stored «Сцена». Scan read by Claude 2026-11-04 against the
н of «Маріинскій», «Кандавлъ», «Русланъ», «Демонъ» and the п of «оп.», «Коппелія» on the same page. RG: "take care of these".
Matching is kept by the alias «Сцепа изъ бал. Корсаръ» -> «Сцена изъ бал. Корсаръ» (pipeline/entity_curation/work_title_aliases.csv).
Asserts the old value; one field changed, nothing added or removed.

usage: uv run python docs/eval/title_fixes_2026-11-04/raw_fix_scepa_1892-93.py [--write]"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/repertoire_1892-93_pair018.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
hits = []
def walk(o):
    if isinstance(o, dict):
        if o.get('work_title') == 'Сцена изъ бал. Корсаръ':
            hits.append(o)
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(d)
assert len(hits) == 1, len(hits)
hits[0]['work_title'] = 'Сцепа изъ бал. Корсаръ'
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
print('1 field edit', '| WRITTEN' if '--write' in sys.argv else '| dry run')
