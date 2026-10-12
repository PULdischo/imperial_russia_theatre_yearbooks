"""«Раманова, Марія» (SP graduate 1903) -> Романова, Марія Федоровна; and REJECT the queued pair
Раманова, Марія / Бажанова, Марія (two women) -- RG, 2026-10-12.
Not a queued pair itself (the surnames differ too much for Tier 2), so it is logged here as confirmed_manual.
Survivor = 2b7b59, which carries the Wikidata link.
usage: uv run python docs/eval/person_merge_romanova_2026-10-12.py [--write]   (dry run copies the db to argv[1])"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)


def full(prefix):
    r = con.execute("select person_id, display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return str(r[0][0]), r[0][1]


(s, ds), (l, dl), (b, _) = full('2b7b59'), full('0f0d0d'), full('94f663')
cid = con.execute("""select candidate_id from entities.person_candidate where status='pending'
    and ((cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?) or (cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?))""", [l, b, b, l]).fetchall()
assert len(cid) == 1, cid
con.execute("update entities.person_candidate set status='rejected' where candidate_id=?", [cid[0][0]])
BE._log_decided_candidates(con)
con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
            [str(uuid.uuid4()), s, l, ds, dl, 1.0, 'manual_review', 'confirmed_manual', 'manual',
             'RG 2026-10-12: the 1903 SP graduate printed «Раманова, Марія» is Романова, Марія Федоровна -- the 14 graduates of 1903 match the 14 entries «съ 1 іюня 1903 г.» in the 1903-04 SP list one for one, and no other Р-манова Марія exists in the corpus'])
con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link pl where pl.person_id=p.person_id) from entities.person p where person_id=?", [s]).fetchone())
print('live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0],
      'pending', con.execute("select display_1, display_2 from entities.person_candidate where status='pending'").fetchall())
con.close()
