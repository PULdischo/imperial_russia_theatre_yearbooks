"""The Moscow class of 1901: graduate + bare-surname 1901-02 row + named dancer = one person (RG, 2026-10-12).
19 people, tabled in docs/eval/person_audit_2026-10-12/README.md. Survivor = the named record.
Any queued candidate pair inside a group is marked confirmed_manual; the rest are logged here.
usage: uv run python docs/eval/person_merge_moscow_class_1901_2026-10-12.py <copy_path> | --write"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
# (survivor = named record, [graduate, bare 1901-02 row, ...])
GROUPS = [
    ('5bb09b', ['45ab33', '18f952']), ('428ccf', ['34b447', '12bd1e']), ('006a77', ['662be1', '49a2ff', '99a6c5']),
    ('5ff823', ['cbe7ef', 'bcb331']), ('084072', ['66b9fb', 'ba786d']), ('325ea6', ['74e958', '3e54a0']),
    ('726d35', ['d3e9d2']), ('1c9b33', ['dac383', '0f9cd6']), ('312b5e', ['67effd', '873191']),
    ('2185ef', ['347184', 'f4f8dd']), ('5127e0', ['ce1ca9', '9e7b0c']), ('55e4ba', ['1351aa', 'f3d3c2']),
    ('83685c', ['3d61e0', 'e2884a']), ('0358c2', ['49422d', 'ccef34']), ('1b58e5', ['d1e1e9', 'f09c50']),
    ('62f87b', ['d2fac4', 'bcb7c2']), ('43cf59', ['e2e078', '50d744']), ('2f1b64', ['5d54db', 'f38922']),
    ('31398d', ['dc7199', '02b697']),
]
WHY = ('RG 2026-10-12: Moscow class of 1901 -- the graduate (1900-01 list, no start date printed), the 1901-02 row printed as a bare '
       'surname (scan), and the named dancer listed from 1902-03 «съ 1 сентября 1901 г.»')


def full(prefix):
    r = con.execute("select person_id, display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return str(r[0][0]), r[0][1]


before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
todo = []
for surv, losers in GROUPS:
    s, ds = full(surv)
    ids = [s] + [full(l)[0] for l in losers]
    q = con.execute("select candidate_id, cast(person_id_1 as varchar), cast(person_id_2 as varchar) from entities.person_candidate where status='pending'").fetchall()
    queued = set()
    for cid, a, b in q:
        if a in ids and b in ids:
            con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid]); queued.add(frozenset((a, b)))
    for l in ids[1:]:
        todo.append((s, ds, l, frozenset((s, l)) in queued))
BE._log_decided_candidates(con)
for s, ds, l, was_queued in todo:
    dl = con.execute("select display_name from entities.person where person_id=?", [l]).fetchone()[0]
    if not was_queued:
        con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
                    [str(uuid.uuid4()), s, l, ds, dl, 1.0, 'manual_review', 'confirmed_manual', 'manual', WHY])
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live', before, '->', after, f'(expected -{len(todo)})')
for surv, _ in GROUPS:
    print('  ', con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where cast(person_id as varchar) like ?", [surv + '%']).fetchone())
clash = con.execute("""select p.display_name, sp.season, count(*) from entities.person p join entities.person_link pl using(person_id) join raw.person_entry r using(entry_id) join raw.source_pages sp on sp.page_id=r.page_id
    where sp.entity_type='BalletArtists' and (%s) group by all having count(*)>1""" % ' or '.join(f"cast(p.person_id as varchar) like '{s}%'" for s, _ in GROUPS)).fetchall()
print('two ballet rows in one season on a survivor:', clash)
con.close()
