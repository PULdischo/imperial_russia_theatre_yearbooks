"""Move entries to an EXISTING person (other person_id keeps/gets them); recompute canonical rows for both.
usage: move_entry.py <from_prefix> <to_prefix> <entry_id,...> <reason> [--write]"""
import sys, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
fp, tp, moves, reason = sys.argv[1], sys.argv[2], sys.argv[3].split(','), sys.argv[4]
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only='--write' not in sys.argv)
def pid(pref):
    r = con.execute("select person_id from entities.person where person_id::varchar like ? and superseded_by_person_id is null", [pref + '%']).fetchall(); assert len(r) == 1, r; return str(r[0][0])
f, t = pid(fp), pid(tp)
def members(p):
    rows = con.execute("""select l.entry_id, ae.family_name_clean, ae.first_name_clean, ae.patronymic_clean, sp.season from entities.person_link l join raw.person_entry r using(entry_id)
      join analysis.person_entry ae using(entry_id) join raw.source_pages sp on sp.page_id=r.page_id where l.person_id=?""", [p]).fetchall()
    return {r[0]: (r[0],) + BE._split_ordinal(r[1]) + (r[2], r[3], r[4]) for r in rows}
mf, mt = members(f), members(t)
assert all(m in mf for m in moves), moves
newf = [mf[e] for e in mf if e not in moves]; newt = list(mt.values()) + [mf[e] for e in moves]
assert newf
rf, rt = BE._canonicalize_person(f, newf), BE._canonicalize_person(t, newt)
print('from stays:', rf[1], rf[6], rf[7], len(newf), '| to gets:', rt[1], rt[6], rt[7], len(newt))
if '--write' in sys.argv:
    for r in (rf, rt):
        con.execute("update entities.person set display_name=?, canonical_family_name=?, canonical_first_name=?, canonical_patronymic=?, ordinal_suffix=?, first_attested_season=?, last_attested_season=?, tier1_key=? where person_id=?", list(r[1:9]) + [r[0]])
    for e in moves: con.execute("update entities.person_link set person_id=?, match_method='manual_split', match_confidence=1.0 where entry_id=?", [t, e])
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), f, t, rf[1], rt[1], 0.0, 'homonym_split', 'split_manual', 'conflicting_dates', reason]); print('WRITTEN')
