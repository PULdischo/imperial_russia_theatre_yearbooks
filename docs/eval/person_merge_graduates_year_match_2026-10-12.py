"""80 graduates joined to their company record (RG, 2026-10-12): the clean pairs of the graduate_year_match queue,
listed in docs/eval/person_audit_2026-10-12/Q_graduate_year_match.csv. Held back for RG: Семеновъ, Николай;
Мосолова, Зинаида; Бекъ, Константинъ; Сергѣева, Наталія. Survivor = the company record.
usage: uv run python docs/eval/person_merge_graduates_year_match_2026-10-12.py <copy_path> | --write"""
import sys, shutil, csv, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
HOLD = ('Семеновъ, Николай', 'Мосолова, Зинаида', 'Бекъ, Константинъ', 'Сергѣева, Наталія')
rows = [r for r in csv.DictReader(open('docs/eval/person_audit_2026-10-12/Q_graduate_year_match.csv', encoding='utf-8-sig')) if r['graduate'] not in HOLD]
assert len(rows) == 80, len(rows)


def full(prefix):
    r = con.execute("select cast(person_id as varchar) from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return r[0][0]


before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
todo = []
for r in rows:
    g, k = full(r['graduate_id']), full(r['company_id'])
    cid = con.execute("""select candidate_id from entities.person_candidate where status='pending' and match_reason='graduate_year_match'
        and ((cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?) or (cast(person_id_1 as varchar)=? and cast(person_id_2 as varchar)=?))""", [g, k, k, g]).fetchall()
    assert len(cid) == 1, (r['graduate'], cid)
    con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid[0][0]])
    todo.append((k, g))
BE._log_decided_candidates(con)
for k, g in todo:
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [k, g])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live', before, '->', after)
bad = con.execute("""select p.display_name, count(*) from entities.person p join entities.person_link pl using(person_id) join raw.person_entry r using(entry_id)
    where r.entity_type='Graduates' group by all having count(*)>1""").fetchall()
print('people with two Graduates entries:', bad)
con.close()
