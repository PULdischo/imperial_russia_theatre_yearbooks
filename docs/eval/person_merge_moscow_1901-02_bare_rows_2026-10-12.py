"""Three more bare-surname rows of the Moscow 1901-02 ballet list (RG, 2026-10-12: "as long as there's only one
possible future candidate" -- checked: each surname has exactly one Moscow ballet person listed after 1901-02).
usage: uv run python docs/eval/person_merge_moscow_1901-02_bare_rows_2026-10-12.py <copy_path> | --write"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
MERGES = [('fe0e68', '34abdf', '«27. Гримальди» = Гримальди, Генріетта, listed 1902-03..1905-06 «съ 1 сентября 1901 г.»; the only Гримальди in the Moscow lists'),
          ('0f1e45', '2e44c8', '«51. Пановъ» = Пановъ, Александръ Викторовичъ, absent 1899-1901 and back «съ 1 сентября 1901 г.»; Николай Викторовичъ is last listed 1897-98'),
          ('0339b3', '042dd3', '«83. Щегловъ» = Щегловъ, Василій Семеновичъ, absent 1899-1901 and back «съ 16 ноября 1901 г.»; the only Щегловъ in the corpus')]
for sp, lp, why in MERGES:
    r = {}
    for k, p in (('s', sp), ('l', lp)):
        x = con.execute("select person_id, display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
        assert len(x) == 1, (p, x); r[k] = x[0]
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), r['s'][0], r['l'][0], r['s'][1], r['l'][1], 1.0, 'manual_review', 'confirmed_manual', 'manual', 'RG 2026-10-12: Moscow 1901-02 bare-surname row (scan): ' + why])
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [r['s'][0], r['l'][0]])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
for sp, _, _ in MERGES:
    print(con.execute("select display_name, (select list(distinct sp.season order by sp.season) from entities.person_link l join raw.person_entry r using(entry_id) join raw.source_pages sp on sp.page_id=r.page_id where l.person_id=p.person_id and sp.entity_type='BalletArtists') from entities.person p where cast(person_id as varchar) like ?", [sp + '%']).fetchone())
print('live', con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0])
