"""issue #131 phase 2: theaterschoolstaff_1896-97_p000 e014..e024 were each linked to the NEXT entry's person (a row, e014 Speranskij, had been inserted
mid-array after the links existed). Re-point by name; tombstone the stray single-entry Speranskij person."""
import sys, duckdb
write = '--write' in sys.argv
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not write)
P = 'theaterschoolstaff_1896-97_p000__e%03d'
cur = {n: str(c.execute("select person_id from entities.person_link where entry_id=?", [P % n]).fetchone()[0]) for n in range(14, 25)}
dob = str(c.execute("select person_id from entities.person where person_id::varchar like '0ef17fa2%'").fetchone()[0])
new = {14: cur[15]}
for n in range(15, 24): new[n] = cur[n + 1]
new[24] = dob
stray = cur[14]
print('stray person (to tombstone into', cur[15][:8] + '):', stray[:8])
for n in range(14, 25):
    e = c.execute("select family_name, first_name from raw.person_entry where entry_id=?", [P % n]).fetchone()
    p = c.execute("select display_name from entities.person where person_id=?", [new[n]]).fetchone()[0]
    print(P % n, e, '->', p, '' if p.split(',')[0][:4] == e[0][:4] else '  <-- NAME MISMATCH')
if write:
    for n in range(14, 25): c.execute("update entities.person_link set person_id=?, match_method='manual_relink_131', match_confidence=1.0 where entry_id=?", [new[n], P % n])
    c.execute("update entities.person set superseded_by_person_id=? where person_id=?", [new[14], stray])
    print('WRITTEN')
