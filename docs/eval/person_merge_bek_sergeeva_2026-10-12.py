"""Two Petersburg graduates who appear in the Moscow company (RG, 2026-10-12).
Бекъ, Константинъ (class of 1892): the Graduates page says so -- «кромѣ ученика Бека, который зачисленъ въ Московскую
балетную труппу» (scan). Сергѣева, Наталія (class of 1909): NO transfer note; the class is assigned to the Petersburg
troupe съ 1 іюня 1909 and she is listed only in Moscow, съ 1 августа 1909. Merged as a likely transfer, uncertainty
noted (uncertain_person_identities.md #31).
usage: uv run python docs/eval/person_merge_bek_sergeeva_2026-10-12.py <copy_path> | --write"""
import sys, shutil, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
todo = []
for sp, lp in (('38e7d3', '63cc6f'), ('b6b70d', 'eb5f25')):
    ids = []
    for p in (sp, lp):
        r = con.execute("select cast(person_id as varchar) from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
        assert len(r) == 1, (p, r); ids.append(r[0][0])
    cid = con.execute("""select candidate_id from entities.person_candidate where status='pending'
        and ((cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?) or (cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?))""", ids + ids[::-1]).fetchall()
    assert len(cid) == 1, cid
    con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid[0][0]])
    todo.append(ids)
BE._log_decided_candidates(con)
for s, l in todo:
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
for s, _ in todo:
    print(con.execute("select display_name, first_attested_season, last_attested_season from entities.person where person_id=?", [s]).fetchone())
print('live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0])
