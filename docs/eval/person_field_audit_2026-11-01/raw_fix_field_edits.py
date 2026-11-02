"""Generic field edits from an audit CSV (entry_id, field, now, new, confidence). Asserts each current raw value equals
'now' before writing 'new'. Field edits only (no entries added/removed/reordered; person_link stays aligned).
usage: uv run python docs/eval/person_field_audit_2026-11-01/raw_fix_field_edits.py <csv> [--min high|medium] [--write]
then docs/eval/rebuild_after_raw_edit.sh"""
import csv, json, sys, collections
from pathlib import Path
RAW = Path('outputs/full_run/raw')
src = sys.argv[1]
mins = sys.argv[sys.argv.index('--min') + 1] if '--min' in sys.argv else 'high'
ok = {'high'} if mins == 'high' else {'high', 'medium'}
rows = [r for r in csv.DictReader(open(src, encoding='utf-8')) if r['confidence'] in ok]
by_page = collections.defaultdict(list)
for r in rows:
    page, idx = r['entry_id'].rsplit('__e', 1)
    by_page[page].append((int(idx), r))
n = 0
for page, items in sorted(by_page.items()):
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    for idx, r in items:
        e = d['entries'][idx - 1]
        assert (e.get(r['field']) or '') == r['now'], (r['entry_id'], r['field'], e.get(r['field']), r['now'])
        e[r['field']] = r['new'] or None
        n += 1
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(n, 'field edits on', len(by_page), 'pages (min', mins + ')', '| WRITTEN' if '--write' in sys.argv else '| dry run')
