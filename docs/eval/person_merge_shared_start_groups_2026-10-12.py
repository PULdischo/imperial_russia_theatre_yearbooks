"""The shared-start queue (RG, 2026-10-12): 63 groups merged, Шефферъ/Шпейеръ rejected, Чумакова, Ольга split.
Groups are read from docs/eval/person_audit_2026-10-12/Q_shared_start_groups.csv. Held back for RG (nine groups):
Адамовъ, Аѳанасьева, Чичелева, Иманъ, Межакова/Лежакова, Дюжикова, Розай, Грибенъ, Голласъ.
Survivor of a group = the member with the most entries.
usage: uv run python docs/eval/person_merge_shared_start_groups_2026-10-12.py <copy_path> | --write"""
import sys, shutil, csv, uuid, re, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
HOLD = ('Адамовъ, Михаилъ', 'Аѳанасьева, Вѣра', 'Чичелева, Елизавета', 'Иманъ,', 'Межакова,', 'Дюжикова,', 'Розай,', 'Грибенъ', 'Голласъ')
REJECT = ('Шефферъ, Фридрихъ',)
SPLIT = ('Чумакова, Ольга',)
TAG = 'RG 2026-10-12, shared-start queue: '


def full(prefix):
    r = con.execute("select cast(person_id as varchar), display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return r[0]


def n_entries(pid):
    return con.execute("select count(*) from entities.person_link where person_id=?", [pid]).fetchone()[0]


pending = {frozenset((str(a), str(b))): str(c) for c, a, b in con.execute(
    "select candidate_id, person_id_1, person_id_2 from entities.person_candidate where status='pending'").fetchall()}
groups = []
for r in csv.DictReader(open('docs/eval/person_audit_2026-10-12/Q_shared_start_groups.csv', encoding='utf-8-sig')):
    mem = [m.split(' ', 1) for m in r['members'].split(' || ')]
    names = ' | '.join(m[1] for m in mem)
    kind = 'hold' if any(h in names for h in HOLD) else 'reject' if any(h in names for h in REJECT) else 'split' if any(h in names for h in SPLIT) else 'merge'
    groups.append((kind, [m[0] for m in mem], names))
cnt = {k: sum(1 for g in groups if g[0] == k) for k in ('merge', 'hold', 'reject', 'split')}
print(cnt); assert cnt == {'merge': 63, 'hold': 9, 'reject': 1, 'split': 1}, cnt

before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
status, merges = {}, []
for kind, ids, names in groups:
    if kind == 'hold': continue
    fulls = [full(i) for i in ids]
    if kind == 'reject':
        for i in range(len(fulls)):
            for j in range(i + 1, len(fulls)):
                k = frozenset((fulls[i][0], fulls[j][0]))
                if k in pending: status[pending[k]] = 'rejected'
        continue
    if kind == 'split':
        g, d, s = full('902c25')[0], full('0fa36b'), full('54acfe')
        e = con.execute("select l.entry_id from entities.person_link l join raw.person_entry r using(entry_id) where l.person_id=? and r.page_id='graduates_1893-94_p001'", [g]).fetchall()
        assert len(e) == 1 and n_entries(g) == 2
        con.execute("update entities.person_link set person_id=?, match_method='manual_split', match_confidence=1.0 where entry_id=?", [s[0], e[0][0]])
        con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), g, s[0], 'Чумакова, Ольга', s[1], 0.0, 'homonym_split', 'split_manual', 'conflicting_dates',
                    TAG + 'graduate «Чумакова, Ольга» held two graduates: the Petersburg one of 1894 (съ 1 іюня 1894) is Ольга Савельевна; the Moscow one of 1893 is Ольга Дмитріевна'])
        k1, k2 = frozenset((g, d[0])), frozenset((g, s[0]))
        if k1 in pending: status[pending[k1]] = 'confirmed_manual'
        if k2 in pending: status[pending[k2]] = 'rejected'
        merges.append((d, [(g, 'Чумакова, Ольга')], k1 in pending))
        continue
    surv = max(fulls, key=lambda f: (n_entries(f[0]), f[0]))
    losers = [f for f in fulls if f[0] != surv[0]]
    for i in range(len(fulls)):
        for j in range(i + 1, len(fulls)):
            k = frozenset((fulls[i][0], fulls[j][0]))
            if k in pending: status[pending[k]] = 'confirmed_manual'
    merges.append((surv, losers, None))
for cid, st in status.items():
    con.execute("update entities.person_candidate set status=? where candidate_id=?", [st, cid])
BE._log_decided_candidates(con)
n = 0
for surv, losers, _ in merges:
    for l in losers:
        if frozenset((surv[0], l[0])) not in pending:
            con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), surv[0], l[0], surv[1], l[1], 1.0, 'manual_review', 'confirmed_manual', 'manual',
                        TAG + 'member of a shared-start group merged as one person (Q_shared_start_groups.csv)'])
        con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [surv[0], l[0]]); n += 1
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live', before, '->', after, f'({n} absorbed)')
print('pending left:', con.execute("select count(*) from entities.person_candidate where status='pending'").fetchone()[0])
ids = ','.join("'%s'" % m[0][0] for m in merges)
print('same season + city + list + heading twice on a survivor:')
for r in con.execute(f"""select p.display_name, sp.season, coalesce(sp.city,'-'), sp.entity_type, count(*) from entities.person p join entities.person_link pl using(person_id)
    join raw.person_entry r using(entry_id) join raw.source_pages sp on sp.page_id=r.page_id where cast(p.person_id as varchar) in ({ids})
    group by p.display_name, sp.season, sp.city, sp.entity_type, r.heading_path having count(*)>1 order by 1,2""").fetchall(): print('   ', r)
con.close()
