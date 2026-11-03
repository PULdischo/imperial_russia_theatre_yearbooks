"""1908-09 BalletArtists (person field audit, 2026-11-03): SP p000 and MSK p007 came back from extraction with NO credit rows, though
eight entries print a tally. The tally text itself was read on the scans for every 1908-09 line on 2026-10-30
(known_issues.md, "1908-09 BalletArtists italic «Всего» sentence"). This builds credit rows from that text in the shape the other
1908-09 pages use: one named_work row per «Title (role—N)», one category_totals row labelled «балетѣ»/«балетахъ» whose count is
the printed «— N разъ». Writes only `credits` on entries that have none; checks the roles sum to the printed total.
usage: uv run python docs/eval/person_field_audit_2026-11-01/raw_fix_1908-09_missing_credits.py [--write]"""
import json, re, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
PAGES = ['balletartists_1908-09_SP_p000', 'balletartists_1908-09_MSK_p007']
WORK = re.compile(r'([^;()]+?)\s*\(([^()]+?)\)')
ROLE = re.compile(r'(.+?)\s*—\s*(\d+)$')
TOTAL = re.compile(r'Всего\s*—\s*въ\s+(\d+)\s+(балет\w+)\s*—\s*(\d+)\s+раз')
out = []
for pg in PAGES:
    f = RAW / f'{pg}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
    for i, e in enumerate(d['entries'], 1):
        t = e.get('credit_summary_text') or ''
        if e.get('credits') or 'Всего' not in t:
            continue
        head, _, _ = t.partition('Всего')
        rows = []
        for title, inner in WORK.findall(head):
            for part in inner.split(','):
                m = ROLE.match(part.strip())
                assert m, (pg, i, part)
                rows.append({'credit_type': 'named_work', 'label': title.strip(' .'), 'role_name': m.group(1).strip(), 'count': int(m.group(2))})
        m = TOTAL.search(t); assert m, (pg, i, t)
        n_ballets, label, total = int(m.group(1)), m.group(2), int(m.group(3))
        assert sum(r['count'] for r in rows) == total, (pg, i, 'roles sum', sum(r['count'] for r in rows), 'printed', total)
        assert len({r['label'] for r in rows}) == n_ballets, (pg, i, 'ballets', n_ballets)
        rows.append({'credit_type': 'category_totals', 'label': label, 'count': total})
        e['credits'] = rows
        out.append((f'{pg}__e{i:03d}', e['family_name'], rows))
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
for eid, fam, rows in out:
    print(eid, fam)
    for r in rows: print('   ', r)
print(len(out), 'entries,', sum(len(r) for _, _, r in out), 'credit rows', '| WRITTEN' if '--write' in sys.argv else '| dry run')
