"""Merge Давильеръ (1908-09) into Девильеръ (1909-11), Екатерина Львовна -- RG, 2026-10-12.
One queued family_name_variant pair; same mechanism as person_merge_ordinal_shift_apply_2026-10-12.py.
Survivor = the Девильеръ record, so the display name stays the form two volumes and the 1910-11 review print.
usage: uv run python docs/eval/person_merge_devilier_2026-10-12.py [--write]   (dry run copies the db to argv[1])"""
import sys, shutil, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)


def full(prefix):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return str(r[0][0])


s, l = full('1272e3'), full('c82bb1')
cid = con.execute("""select candidate_id from entities.person_candidate where status='pending'
    and ((cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?) or (cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?))""", [s, l, l, s]).fetchall()
assert len(cid) == 1, cid
con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid[0][0]])
BE._log_decided_candidates(con)
con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link pl where pl.person_id=p.person_id) from entities.person p where person_id=?", [s]).fetchone())
print('live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0],
      'pending', con.execute("select count(*) from entities.person_candidate where status='pending'").fetchone()[0])
con.close()
