"""Merge the three Фонъ-Бооль, Николай Константиновичъ records -- RG, 2026-10-12 ("it's the same person").
Two queued family_name_variant pairs (hyphen in the administration list, space in the Moscow school list).
Survivor = 420cb6, the long Administrators record. Raw is untouched: both printed leaving dates stay verbatim.
usage: uv run python docs/eval/person_merge_fon_bool_2026-10-12.py [--write]   (dry run copies the db to argv[1])"""
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


s, losers = full('420cb6'), [full('054608'), full('aa74c2')]
for t in ('person_wikidata_link', 'wikidata_decision', 'production_credit_link', 'review_person'):
    print(t, con.execute(f"select * from entities.{t} where cast(person_id as varchar) in (?,?,?)", [s] + losers).fetchall())
n = 0
for l in losers:
    cid = con.execute("""select candidate_id from entities.person_candidate where status='pending'
        and ((cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?) or (cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?))""", [s, l, l, s]).fetchall()
    assert len(cid) == 1, cid
    con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid[0][0]])
    n += 1
BE._log_decided_candidates(con)
for l in losers:
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link pl where pl.person_id=p.person_id) from entities.person p where person_id=?", [s]).fetchone())
print('live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0],
      'pending', con.execute("select count(*) from entities.person_candidate where status='pending'").fetchone()[0])
con.close()
