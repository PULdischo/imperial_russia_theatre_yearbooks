"""Re-apply the 2026-10-05 split of Никитинъ, Алексѣй Никитичъ (RG, 2026-10-12).
merge_duplicate_persons had rejoined the Petersburg second violinist (съ 1 сентября 1881, left 1 октября 1900)
and the Moscow trombonist (съ 23 сентября 1898); both are listed in 1898-99, 1899-00 and 1900-01.
738f18 (the violinist's original id) is brought back to life and takes the Petersburg entries; 636532 keeps Moscow.
The original split_manual log row (738f18 / b20a5e, and b20a5e -> 636532) now keeps them apart in build_entities.
usage: uv run python docs/eval/person_resplit_nikitin_2026-10-12.py <copy_path> | --write"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else sys.argv[1]
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
live = con.execute("select cast(person_id as varchar) from entities.person where cast(person_id as varchar) like '636532%' and superseded_by_person_id is null").fetchall()
old = con.execute("select cast(person_id as varchar), cast(superseded_by_person_id as varchar) from entities.person where cast(person_id as varchar) like '738f18%'").fetchall()
assert len(live) == 1 and len(old) == 1 and old[0][1] == live[0][0], (live, old)
m, v = live[0][0], old[0][0]
sp = con.execute("""select l.entry_id from entities.person_link l join raw.person_entry r using(entry_id) join raw.source_pages p on p.page_id = r.page_id
                    where l.person_id = ? and p.city = 'SP'""", [m]).fetchall()
assert len(sp) == 11, len(sp)
con.execute("update entities.person set superseded_by_person_id = NULL where person_id = ?", [v])
for (e,) in sp:
    con.execute("update entities.person_link set person_id = ?, match_method = 'manual_split', match_confidence = 1.0 where entry_id = ?", [v, e])
con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
            [str(uuid.uuid4()), v, m, 'Никитинъ, Алексѣй Никитичъ', 'Никитинъ, Алексѣй Никитичъ', 0.0, 'homonym_split', 'split_manual', 'conflicting_dates',
             'RG 2026-10-12: the 2026-10-05 split re-applied after merge_duplicate_persons undid it; SPb second violinist (1881-1900) vs Moscow trombonist (from 23 сентября 1898), both listed 1898-99..1900-01'])
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
for pid in (v, m):
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id = p.person_id) from entities.person p where person_id = ?", [pid]).fetchone())
print('kept apart:', len(BE._keep_apart_pairs(con)))
con.close()
