"""Two stray Moscow rows -> Воронцовъ, Владиміръ Васильевичъ (4b9294) -- RG, 2026-10-12.
d8902c = 1901-02 Артисты no. 14, printed «Воронцовъ,» with nothing more (scan, full zoom): his first season back
after «Оставилъ службу 1 ноября 1898 г.»; 865c93 = 1910-11 Артисты no. 8, no patronymic, «съ 1 сентября 1891 г.».
Neither is a queued pair with him, so both are logged here as confirmed_manual.
The parked pair 865c93 / Боронцовъ (SP graduate 1911) is left pending; it lapses when 865c93 is absorbed.
usage: uv run python docs/eval/person_merge_vorontsov_2026-10-12.py [--write]   (dry run copies the db to argv[1])"""
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


s, ds = full('4b9294')
for pref, why in (('d8902c', '1901-02 Moscow Артисты no. 14 is printed with the surname only; he is the only Воронцовъ in the Moscow ballet lists, back from 1 сентября 1901, with the parts he has in the following seasons'),
                  ('865c93', '1910-11 Moscow Артисты no. 8, no patronymic, carries his start date 1 сентября 1891; he is also listed that season as acting assistant regisseur')):
    l, dl = full(pref)
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
                [str(uuid.uuid4()), s, l, ds, dl, 1.0, 'manual_review', 'confirmed_manual', 'manual', 'RG 2026-10-12: ' + why])
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link pl where pl.person_id=p.person_id) from entities.person p where person_id=?", [s]).fetchone())
print('live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0])
con.close()
