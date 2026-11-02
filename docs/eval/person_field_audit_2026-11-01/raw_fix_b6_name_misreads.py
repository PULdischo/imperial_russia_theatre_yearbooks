"""B6 + B7 (person field audit, RG 2026-11-02: "High confidence only (95)"): letter-level misreads in name fields and stray
non-Russian characters, read on the scans by Claude. Input B6_name_misreads.csv; only confidence == 'high' rows are applied
(the 7 medium rows are held for RG). Each edit asserts the current raw value equals 'now'. Field edits only.
usage: uv run python docs/eval/person_field_audit_2026-11-01/raw_fix_b6_name_misreads.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import csv, json, sys, collections
from pathlib import Path

RAW = Path('outputs/full_run/raw'); D = Path(__file__).parent
rows = [r for r in csv.DictReader(open(D / 'B6_name_misreads.csv', encoding='utf-8')) if r['confidence'] == 'high']
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
        e[r['field']] = r['new']
        n += 1
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(n, 'edits on', len(by_page), 'pages', '| WRITTEN' if '--write' in sys.argv else '| dry run')
