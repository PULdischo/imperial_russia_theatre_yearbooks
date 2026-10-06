"""person_link step for the Graduates apply: delete the links of removed rows and renumber the later entry_ids on each page (issue #131 rule).
usage: relink_graduates.py [--write]   (reads docs/eval/graduates_audit_2026-10-06/plan.json)"""
import sys, json, duckdb
write = '--write' in sys.argv
D = 'docs/eval/graduates_audit_2026-10-06/'
plan = json.load(open(D + 'plan.json'))
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not write)
n_del = n_ren = 0; phantom = set()
for page, rem in plan['remove'].items():
    nums = sorted(int(r[0].rsplit('__e', 1)[1]) for r in c.execute("select entry_id from entities.person_link where entry_id like ?", [page + '__e%']).fetchall())
    for r in rem:
        row = c.execute("select person_id from entities.person_link where entry_id=?", [f'{page}__e{r:03d}']).fetchone()
        if row: phantom.add(str(row[0]))
        if write: c.execute("delete from entities.person_link where entry_id=?", [f'{page}__e{r:03d}'])
        n_del += 1
    for n in nums:
        if n in rem: continue
        new = n - sum(1 for r in rem if r < n)
        if new != n:
            if write: c.execute("update entities.person_link set entry_id=? where entry_id=?", [f'{page}__e{new:03d}', f'{page}__e{n:03d}'])
            n_ren += 1
print('links to delete', n_del, 'to rename', n_ren, '; persons that lose a link:', len(phantom))
if write:
    left = [p for p in phantom if c.execute("select count(*) from entities.person_link where person_id=?", [p]).fetchone()[0] == 0]
    json.dump(left, open(D + 'phantom_persons_after_relink.json', 'w'))
    print('WRITTEN; persons left with zero links:', len(left))
