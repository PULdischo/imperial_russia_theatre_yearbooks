"""Егорова, Petersburg ballet (RG, 2026-11-02, "1903-04 to 1909-10"). Марія Николаевна (съ 7 іюня 1882) prints
«Оставила службу 7 іюня 1902 г.» in 1901-02. After that the list has one Егорова a season, printed «Любовь» (1902-03,
1904-05, 1910-11) or «Марія Николаевна» (1903-04, 1905-08 with Марія's start 1882; 1908-09, 1909-10 with Любовь's start
1898); the roles run on unbroken (Мирта, Клемансъ, нереиды, Голубая георгина, Цикалія, Гамзатти), so these are Любовь.
This script moves the four 1903-08 «Марія Николаевна» entries from Марія's record (a3dee646) to Любовь (0eea687d) and
records a split_manual pair so nothing automatic joins them. Then: person_merge_manual.py 0eea687d d45195ed (the 1908-10
record). 1899-00/1900-01 left open (RG). Raw is untouched.
usage: uv run python docs/eval/person_resplit_egorova_2026-11-02.py <copy_path> | --write"""
import sys, shutil, uuid, datetime, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
if '--write' in sys.argv:
    DB = REAL; shutil.copy2(REAL, f"outputs/full_run/imperial_theaters.pre_resplit_egorova_{datetime.date.today()}.duckdb")
else:
    DB = sys.argv[1]; shutil.copy2(REAL, DB)
con = duckdb.connect(DB)


def full(prefix):
    r = con.execute("select cast(person_id as varchar), display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return r[0]


maria, lyubov = full('a3dee646'), full('0eea687d')
MOVE = ['balletartists_1903-04_SP_p001__e019', 'balletartists_1905-06_SP_p001__e012',
        'balletartists_1906-07_SP_p002__e001', 'balletartists_1907-08_SP_p001__e020']
for e in MOVE:
    r = con.execute("select cast(l.person_id as varchar), r.family_name, r.first_name, r.patronymic from entities.person_link l join raw.person_entry r using(entry_id) where entry_id = ?", [e]).fetchone()
    assert r[0] == maria[0] and r[1].startswith('Егорова') and r[2] == 'Марія' and r[3] == 'Николаевна', (e, r)
    con.execute("update entities.person_link set person_id = ?, match_method = 'manual_split', match_confidence = 1.0 where entry_id = ?", [lyubov[0], e])
con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
            [str(uuid.uuid4()), maria[0], lyubov[0], maria[1], lyubov[1], 0.0, 'homonym_split', 'split_manual', 'conflicting_dates',
             'RG 2026-11-02: Petersburg ballet -- Марія Николаевна (съ 7 іюня 1882, left 7 іюня 1902) and Любовь Александровна (съ 1 іюня 1898); '
             'the 1903-04 and 1905-08 lists print Любовь under Марія\'s name and start (roles continuous); 1899-00/1900-01 left open'])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
for pid in (maria[0], lyubov[0]):
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id = p.person_id) from entities.person p where person_id = ?", [pid]).fetchone())
print('kept apart:', len(BE._keep_apart_pairs(con)), '| written' if DB == REAL else '| dry run')
con.close()
