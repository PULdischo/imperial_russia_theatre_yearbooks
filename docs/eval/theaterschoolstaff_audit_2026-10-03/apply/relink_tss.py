"""person_link step for the TheaterSchoolStaff apply: remove links of deleted rows + renumber the rest (like issue #131's rule), seed links for appended rows by exact canonical name.
usage: relink_tss.py [--write]"""
import sys, json, duckdb
write = '--write' in sys.argv
plan = json.load(open('/tmp/tss/plan.json'))
c = duckdb.connect('/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/outputs/full_run/imperial_theaters.duckdb', read_only=not write)
n_del = n_ren = 0
for page, rem in plan['remove'].items():
    nums = sorted(int(r[0].rsplit('__e', 1)[1]) for r in c.execute("select entry_id from entities.person_link where entry_id like ?", [page + '__e%']).fetchall())
    for r in rem:
        if write: c.execute("delete from entities.person_link where entry_id=?", [f'{page}__e{r:03d}'])
        n_del += 1
    for n in nums:
        if n in rem: continue
        new = n - sum(1 for r in rem if r < n)
        if new != n:
            if write: c.execute("update entities.person_link set entry_id=? where entry_id=?", [f'{page}__e{new:03d}', f'{page}__e{n:03d}'])
            n_ren += 1
print('links to delete', n_del, 'to rename', n_ren)
import glob, os, re
R = '/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/outputs/full_run/raw/'
added_ids = {a['entry_id'] for a in plan['add']}
def key(e): return ((e.get('family_name') or '').strip(), (e.get('first_name') or '').strip(), (e.get('patronymic') or '').strip())
by_season = {}
for f in glob.glob(R + 'theaterschoolstaff_*.raw.json'):
    pg = os.path.basename(f)[:-9]; season = pg.split('_')[1]
    for i, e in enumerate(json.load(open(f))['entries'], 1):
        by_season.setdefault(season, []).append((f'{pg}__e{i:03d}', key(e)))
seeded = ambiguous = nomatch = 0; todo = []
for a in plan['add']:
    season = a['entry_id'].split('_')[1]; k = (a['family_name'].strip(), (a['first_name'] or '').strip(), (a['patronymic'] or '').strip())
    sib = [eid for eid, kk in by_season.get(season, []) if kk == k and eid not in added_ids]
    pids = set()
    for eid in sib:
        r = c.execute("select person_id from entities.person_link where entry_id=?", [eid]).fetchone()
        if r: pids.add(str(r[0]))
    method = 'sibling'
    if len(pids) != 1:
        fam, first, pat = k[0], k[1] or None, k[2] or None; ordinal = None
        m = re.match(r'^(.*?)\s+(\d+-[йя])$', fam)
        if m: fam, ordinal = m.group(1), m.group(2)
        rows = c.execute("""select person_id from entities.person where superseded_by_person_id is null and canonical_family_name=?
            and coalesce(canonical_first_name,'')=? and coalesce(canonical_patronymic,'')=? and coalesce(ordinal_suffix,'')=?""", [fam, first or '', pat or '', ordinal or '']).fetchall()
        pids = {str(r[0]) for r in rows}; method = 'name'
    if len(pids) == 1: seeded += 1; todo.append((a['entry_id'], next(iter(pids)), method))
    elif len(pids) > 1: ambiguous += 1; print('AMBIGUOUS', a['entry_id'], k, len(pids))
    else: nomatch += 1; print('NO MATCH (new person)', a['entry_id'], k)
print('seed', seeded, '(sibling %d)' % sum(1 for t in todo if t[2] == 'sibling'), 'ambiguous', ambiguous, 'new-person', nomatch)
if write:
    for e, p, m in todo: c.execute("insert into entities.person_link(entry_id,person_id,match_method,match_confidence) values (?,?,?,1.0)", [e, p, 'manual_seed_tss_' + m])
    print('WRITTEN')
