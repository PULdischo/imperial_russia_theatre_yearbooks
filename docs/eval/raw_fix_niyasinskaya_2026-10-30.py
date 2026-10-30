"""Restore a print slip the extraction silently corrected (RG, 2026-10-30: "Yes, restore").
balletartists_1908-09_SP_p002 no. 63 (p. 91): the print reads «Ніясинская, Бронислава Фоминична (съ 1 іюня 1908 г.)» (zoomed by a
read-only agent and re-checked by Claude, scratchpad sw/z0809_nizh2.png); raw stored «Нижинская». Raw is verbatim, so the printed
surname goes back. The entry stays linked to Нижинская, Бронислава (person_link is keyed by entry position, not by name).
Field edit only (entry positions unchanged).
usage: uv run python docs/eval/raw_fix_niyasinskaya_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

f = Path('outputs/full_run/raw/balletartists_1908-09_SP_p002.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
e = d['entries'][23 - 1]                              # entry_id numbers are 1-based
assert (e.get('family_name'), e.get('first_name'), e.get('list_number')) == ('Нижинская', 'Бронислава', '63.'), e
e['family_name'] = 'Ніясинская'
print('balletartists_1908-09_SP_p002 no. 63: «Нижинская» -> «Ніясинская»', '| WRITTEN' if '--write' in sys.argv else '| dry run')
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
