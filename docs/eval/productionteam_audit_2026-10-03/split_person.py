"""Split one wrongly merged person: entries in --move go to a NEW person; the rest stay.
usage: split_person.py <person_id_prefix> <entry_id,entry_id,...> <reason> [--write]"""
import sys, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
pref, moves, reason = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only='--write' not in sys.argv)
old = con.execute("select person_id from entities.person where person_id::varchar like ? and superseded_by_person_id is null", [pref + '%']).fetchall()
assert len(old) == 1, old
old_id = str(old[0][0])
rows = con.execute("""select l.entry_id, ae.family_name_clean, ae.first_name_clean, ae.patronymic_clean, p.season
   from entities.person_link l join raw.person_entry r using(entry_id) join analysis.person_entry ae using(entry_id) join raw.source_pages p on p.page_id=r.page_id
   where l.person_id = ?""", [old_id]).fetchall()
mem = {r[0]: (r[0],) + BE._split_ordinal(r[1]) + (r[2], r[3], r[4]) for r in rows}
assert all(m in mem for m in moves), [m for m in moves if m not in mem]
stay = [mem[e] for e in mem if e not in moves]; go = [mem[e] for e in moves]
assert stay and go
new_id = str(uuid.uuid4())
r_old = BE._canonicalize_person(old_id, stay); r_new = BE._canonicalize_person(new_id, go)
print('stays :', r_old[1], r_old[6], r_old[7], len(stay)); print('new   :', r_new[1], r_new[6], r_new[7], len(go), new_id[:8])
if '--write' in sys.argv:
    con.execute("update entities.person set display_name=?, canonical_family_name=?, canonical_first_name=?, canonical_patronymic=?, ordinal_suffix=?, first_attested_season=?, last_attested_season=?, tier1_key=? where person_id=?", list(r_old[1:9]) + [old_id])
    con.execute("insert into entities.person values (?,?,?,?,?,?,?,?,?,?)", list(r_new))
    for e in moves: con.execute("update entities.person_link set person_id=?, match_method='manual_split', match_confidence=1.0 where entry_id=?", [new_id, e])
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), old_id, new_id, r_old[1], r_new[1], 0.0, 'homonym_split', 'split_manual', 'conflicting_dates', reason])
    print('WRITTEN')
