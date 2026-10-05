"""Revert the 2026-10-05 split of Николаевъ Иванъ Николаевичъ (RG, 2026-10-05): the evidence that the Moscow ballet entry (1909-10, no. 29,
start 1 августа 1900) and the Moscow ProductionTeam assistant machinist (start 16 августа 1899) are two men was too thin (start dates one year apart,
dual listings are common, a single ballet entry). The ballet entry goes back onto the machinist's person; open note: possibly two men.
Same mechanism as the merge batch (tombstone + person_merge_log confirmed_manual + repoint + refresh canonical). Dry run unless --write."""
import sys, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
write = '--write' in sys.argv
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not write)
def full(p):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
    assert len(r) == 1, (p, r); return str(r[0][0])
keep, gone = full('3f4bfd'), full('a47853')
print('entries on', gone[:6], ':', con.execute("select entry_id from entities.person_link where person_id=?", [gone]).fetchall())
if write:
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [keep, gone])
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), keep, gone, 'Николаевъ, Иванъ Николаевичъ', 'Николаевъ, Иванъ Николаевичъ', 1.0, 'manual_review', 'confirmed_manual', 'manual',
        'REVERT of the 2026-10-05 homonym-sweep split (RG): evidence for two men too thin -- Moscow ballet no.29 (съ 1 августа 1900, 1909-10) vs ProductionTeam assistant machinist (съ 16 августа 1899, 1908-10); possibly two men, undecided'])
    BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con); print('WRITTEN')
