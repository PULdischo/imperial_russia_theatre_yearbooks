"""Merge named person records on RG's decision. Pending candidate pairs inside the group become confirmed_manual;
other pairs get a manual log row. Dry run on a copy unless --write (which backs production up first).
usage: uv run python docs/eval/person_merge_manual.py <survivor_prefix> <loser_prefix,...> "<reason>" [--write]"""
import sys, shutil, uuid, datetime, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
surv, losers, reason = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
if '--write' in sys.argv:
    DB = REAL
    shutil.copy2(REAL, f"outputs/full_run/imperial_theaters.pre_merge_{surv}_{datetime.date.today()}.duckdb")
else:
    DB = '/private/tmp/claude-502/merge_manual_dry.duckdb'
    shutil.copy2(REAL, DB)
con = duckdb.connect(DB)


def full(prefix):
    r = con.execute("select cast(person_id as varchar), display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return r[0]


s = full(surv); ls = [full(l) for l in losers]
ids = [s[0]] + [l[0] for l in ls]
queued = set()
for cid, a, b in con.execute("select candidate_id, cast(person_id_1 as varchar), cast(person_id_2 as varchar) from entities.person_candidate where status='pending'").fetchall():
    if a in ids and b in ids:
        con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid]); queued.add(frozenset((a, b)))
BE._log_decided_candidates(con)
for l in ls:
    if frozenset((s[0], l[0])) not in queued:
        con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), s[0], l[0], s[1], l[1], 1.0, 'manual_review', 'confirmed_manual', 'manual', reason])
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s[0], l[0]])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where person_id=?", [s[0]]).fetchone(),
      '| live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0], '| written' if DB == REAL else '| dry run')
