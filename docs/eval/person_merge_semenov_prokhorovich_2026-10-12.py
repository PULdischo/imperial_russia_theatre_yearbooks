"""«Семеновъ, Николай Прохоровичъ» (Moscow ballet 1908-09, no. 47, съ 1 сентября 1899) -> Семеновъ, Николай Прокопьевичъ,
whose run it completes (no. 54 in 1907-08, no. 47 in 1909-10, same start). RG, 2026-10-12. Patronymic printed three
ways in the data (Прокопьевичъ / Прокофьевичъ / Прохоровичъ); the 1908-09 row was not read on the scan.
NOT merged: «Ѳокинъ, Михаилъ Федоровичъ» is an assistant hairdresser at the Bolshoi (ProductionTeam, съ 16 августа
1901), a different man from the dancer Фокинъ, Михаилъ Михайловичъ.
usage: uv run python docs/eval/person_merge_semenov_prokhorovich_2026-10-12.py <copy_path> | --write"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
r = {}
for k, p in (('s', '3923fd'), ('l', '79f3ba')):
    x = con.execute("select person_id, display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
    assert len(x) == 1, (p, x); r[k] = x[0]
con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), r['s'][0], r['l'][0], r['s'][1], r['l'][1], 1.0, 'manual_review', 'confirmed_manual', 'manual',
            'RG 2026-10-12: the 1908-09 Moscow row fills the one gap in his run; same slot and start date 1 сентября 1899; patronymic variant'])
con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [r['s'][0], r['l'][0]])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
print(con.execute("select display_name, (select list(distinct sp.season order by sp.season) from entities.person_link l join raw.person_entry e using(entry_id) join raw.source_pages sp on sp.page_id=e.page_id where l.person_id=p.person_id) from entities.person p where person_id=?", [r['s'][0]]).fetchone())
