import duckdb,json
plan=json.load(open('/tmp/audit8/relink_plan.json'))
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb')
n_del=n_ren=0
for page,rem in plan['remove'].items():
    rows=c.execute("select entry_id from entities.person_link where entry_id like ? order by entry_id",[page+'__e%']).fetchall()
    nums=sorted(int(r[0].rsplit('__e',1)[1]) for r in rows)
    for r in rem:
        c.execute("delete from entities.person_link where entry_id=?",[f'{page}__e{r:03d}']); n_del+=1
    for n in nums:
        if n in rem: continue
        new=n-sum(1 for r in rem if r<n)
        if new!=n:
            c.execute("update entities.person_link set entry_id=? where entry_id=?",[f'{page}__e{new:03d}',f'{page}__e{n:03d}']); n_ren+=1
for a in plan['add']:
    c.execute("insert into entities.person_link(entry_id,person_id,match_method,match_confidence) values (?,?,'manual_seed',1.0)",[a['entry_id'],a['person_id']])
print('deleted',n_del,'renamed',n_ren,'added',len(plan['add']))
print(c.execute("select count(*) from entities.person_link").fetchone())
