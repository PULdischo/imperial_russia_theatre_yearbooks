"""Грибенъ, two Petersburg percussionists (RG, 2026-10-15). Августъ Ѳедоровичъ (съ 1 мая 1862, † 17 марта 1896) and
Ѳедоръ Ѳедоровичъ (съ 15 августа 1873; again съ 1 августа 1897). Record 3d3d25 mixed them: the bare ballet-orchestra
cross-reference «Грибенъ (см. оперный оркестръ). Ударные инструменты.» of 1890-91..1892-93 -- in those years the only
Грибенъ in the opera orchestra is Ѳедоръ (scans 1890-91 pp. 75/78/80, 1892-93 p. 71) -- and «Грибенъ 1-й, Августъ
Ѳедоровичъ (съ 1 мая 1862 г.)» of the opera orchestra 1893-94, 1894-95.
This script moves the three cross-references to Ѳедоръ (11088e) and records a split_manual pair Августъ (1ed184) /
Ѳедоръ (11088e) so nothing automatic joins them. Then: person_merge_manual.py 1ed184 3d3d25 (the two Августъ rows).
usage: uv run python docs/eval/person_resplit_griben_2026-10-15.py <copy_path> | --write"""
import sys, shutil, uuid, datetime, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
if '--write' in sys.argv:
    DB = REAL; shutil.copy2(REAL, f"outputs/full_run/imperial_theaters.pre_resplit_griben_{datetime.date.today()}.duckdb")
else:
    DB = sys.argv[1]; shutil.copy2(REAL, DB)
con = duckdb.connect(DB)


def full(prefix):
    r = con.execute("select cast(person_id as varchar), display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return r[0]


mixed, fedor, avgust = full('3d3d25'), full('11088e'), full('1ed184')
bare = con.execute("""select l.entry_id, p.season from entities.person_link l join raw.person_entry r using(entry_id)
                      join raw.source_pages p on p.page_id = r.page_id
                      where l.person_id = ? and r.first_name is null and r.tenure_note_text like '%см. оперный оркестръ%'
                      order by 2""", [mixed[0]]).fetchall()
assert [s for _, s in bare] == ['1890-91', '1891-92', '1892-93'], bare
for e, _ in bare:
    con.execute("update entities.person_link set person_id = ?, match_method = 'manual_split', match_confidence = 1.0 where entry_id = ?", [fedor[0], e])
con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
            [str(uuid.uuid4()), avgust[0], fedor[0], avgust[1], fedor[1], 0.0, 'homonym_split', 'split_manual', 'conflicting_dates',
             'RG 2026-10-15: two Petersburg percussionists Грибенъ -- Августъ Ѳедоровичъ (съ 1 мая 1862, † 17 марта 1896) and Ѳедоръ Ѳедоровичъ (съ 15 августа 1873, again съ 1 августа 1897); both in the opera orchestra 1893-94, 1894-95'])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
for pid in (avgust[0], fedor[0], mixed[0]):
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id = p.person_id) from entities.person p where person_id = ?", [pid]).fetchone())
print('kept apart:', len(BE._keep_apart_pairs(con)), '| written' if DB == REAL else '| dry run')
con.close()
