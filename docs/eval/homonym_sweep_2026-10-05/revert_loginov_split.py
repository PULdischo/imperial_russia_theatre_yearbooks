"""Revert the 2026-10-05 split of Логиновъ Сергѣй Андреевичъ (RG decision, 2026-10-05): after the evidence review (no Petersburg trumpet entry before 1904-05; Petersburg run 1904-06 ends as the Moscow run 1905-10 begins; Moscow start "1 сентября 1904" = his first Petersburg season; the Petersburg entries print "1894", read digit by digit on the scan, a probable print typo) RG chose one man. The Moscow person (408708fb) is folded back into the Petersburg person (4240d1). Open note: possibly two men.
Same mechanism as the merge batch (tombstone + person_merge_log confirmed_manual + repoint + refresh canonical). Dry run unless --write."""
import sys, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
write = '--write' in sys.argv
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not write)
def full(p):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
    assert len(r) == 1, (p, r); return str(r[0][0])
keep, gone = full('4240d1'), full('408708')
print('entries on', gone[:6], ':', con.execute("select entry_id from entities.person_link where person_id=?", [gone]).fetchall())
if write:
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [keep, gone])
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), keep, gone, 'Николаевъ, Иванъ Николаевичъ', 'Николаевъ, Иванъ Николаевичъ', 1.0, 'manual_review', 'confirmed_manual', 'manual',
        'REVERT of the 2026-10-05 homonym-sweep split (RG decision): one trumpeter hired 1 сентября 1904 who moved SPb->Moscow in 1905-06; printed SPb start 1894 is a probable print typo; possibly two men'])
    BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con); print('WRITTEN')
