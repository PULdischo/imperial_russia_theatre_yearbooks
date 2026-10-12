"""Семеновъ, Николай (Moscow graduate 1899) -> Николай Прокопьевичъ (Moscow ballet); the pair with the Petersburg
musician Николай Ивановичъ REJECTED. Мосолова, Зинаида (Moscow graduate 1906) + «Зинаида Алексѣевна» (1905-06 list)
-> Мосолова 2-я, Зинаида Александровна; patronymic variant noted. RG, 2026-10-12.
usage: uv run python docs/eval/person_merge_semenov_mosolova_2026-10-12.py <copy_path> | --write"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)


def full(prefix):
    r = con.execute("select cast(person_id as varchar), display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return r[0]


def pair(a, b):
    r = con.execute("""select candidate_id from entities.person_candidate where status='pending'
        and ((cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?) or (cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?))""", [a, b, b, a]).fetchall()
    return r[0][0] if r else None


MERGES = [('3923fd', '9b9fa9', 'the 1899 Moscow graduate joins the Moscow ballet «съ 1 сентября 1899 г.»'),
          ('2b4912', '30a837', 'the 1906 Moscow graduate; «съ 1 августа 1906 г.»'),
          ('2b4912', '2c590e', 'the 1905-06 list prints «Мосолова, Зинаида Алексѣевна (съ 1 августа 1906 г.)», Александровна from 1906-07; one woman, patronymic variant (1905-06 row not read on the scan)')]
REJECT = [('9b9fa9', '95b5e2')]
for a, b in REJECT:
    cid = pair(full(a)[0], full(b)[0]); assert cid
    con.execute("update entities.person_candidate set status='rejected' where candidate_id=?", [cid])
todo = []
for sp, lp, why in MERGES:
    (s, ds), (l, dl) = full(sp), full(lp)
    cid = pair(s, l)
    if cid:
        con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid])
    todo.append((s, ds, l, dl, bool(cid), why))
BE._log_decided_candidates(con)
for s, ds, l, dl, queued, why in todo:
    if not queued:
        con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), s, l, ds, dl, 1.0, 'manual_review', 'confirmed_manual', 'manual', 'RG 2026-10-12: ' + why])
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
for p in ('3923fd', '2b4912'):
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where cast(person_id as varchar) like ?", [p + '%']).fetchone())
print('live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0])
