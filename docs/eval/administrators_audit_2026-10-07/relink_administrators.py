"""person_link step for the Administrators apply (plan.json): delete the links of removed rows, renumber the later entry_ids on each page (issue #131 rule),
seed links for the rows appended at the end of their page by exact canonical name (Всеволожской / Покровскій). Dry run unless --write."""
import sys, json, duckdb
write = '--write' in sys.argv
D = 'docs/eval/administrators_audit_2026-10-07/'
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
for a in plan['add']:
    fam = a['family_name']; first = a['first_name']; pat = a['patronymic']
    rows = c.execute("""select cast(person_id as varchar) from entities.person where superseded_by_person_id is null and canonical_family_name like ?
        and coalesce(canonical_first_name,'')=? and coalesce(canonical_patronymic,'')=?""", [fam[:6] + '%', first or '', pat or '']).fetchall()
    ids = {r[0] for r in rows}
    print('ADD', a['entry_id'], fam, first, pat, '-> candidate persons:', [i[:6] for i in ids])
    if write and len(ids) == 1:
        c.execute("insert into entities.person_link(entry_id,person_id,match_method,match_confidence) values (?,?,?,1.0)", [a['entry_id'], next(iter(ids)), 'manual_seed_adm_name'])
        print('   seeded')
if write:
    left = [p for p in phantom if c.execute("select count(*) from entities.person_link where person_id=?", [p]).fetchone()[0] == 0]
    print('WRITTEN; persons left with zero links:', len(left))
