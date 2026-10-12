"""Three raw rows from the 2026-10-12 person audit, each read on the scan. Field edits only (issue #131 safe).
usage: uv run python docs/eval/raw_fix_audit_rows_2026-10-12.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
FIXES = [
    # specks on the page were read as quotation marks: «93. Эрлеръ, Александръ Александровичъ»
    ('balletartists_1904-05_SP_p010', {'list_number': '93.', 'first_name': '"Александръ"'}, {'first_name': 'Александръ'}),
    # print: «80. Петипа 2-я, Надежда Васильевна» (full zoom) -- the ordinal was dropped; Васильевна IS printed
    ('balletartists_1904-05_SP_p003', {'list_number': '80.', 'family_name': 'Петипа', 'patronymic': 'Васильевна'}, {'family_name': 'Петипа 2-я'}),
    # guest section «Танцовала на Петербургской сценѣ...: Гельцеръ. Донъ-Кихотъ (Китри—1)»: the role is not a patronymic
    ('balletartists_1909-10_SP_p005', {'family_name': 'Гельцеръ', 'patronymic': '(Китри)'}, {'patronymic': None}),
]
for page, cur, new in FIXES:
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    hits = [e for e in d['entries'] if all(e.get(k) == v for k, v in cur.items())]
    assert len(hits) == 1, (page, cur, len(hits))
    hits[0].update(new); print(page, cur, '->', new)
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
