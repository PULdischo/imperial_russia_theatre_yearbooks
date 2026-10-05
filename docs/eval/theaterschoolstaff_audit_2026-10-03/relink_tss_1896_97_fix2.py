"""issue #134 / #131 follow-up (2026-10-05): repair the person_link shift that TSS stage 1 left on theaterschoolstaff_1896-97_p000.
Stage 1 removed old e011 (Священникъ) and old e014 (Оставилъ службу); old e015 was a blank-name row (heading carried "Сперанскій"),
so it never had a link. relink_tss.py assumed one link per row, so after the removals e013..e022 each carry the NEXT row's person.
Fix: e013 (Сперанскій) -> the live Сперанскій person 1f77bdfc; e014..e022 -> the person currently on the row above (= the person
of their own name). Every assignment is name-verified before anything is written. Dry run unless --write."""
import sys, duckdb
write = '--write' in sys.argv
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not write)
P = 'theaterschoolstaff_1896-97_p000__e%03d'
cur = {n: str(c.execute("select person_id from entities.person_link where entry_id=?", [P % n]).fetchone()[0]) for n in range(13, 24)}
sper = str(c.execute("select person_id from entities.person where person_id::varchar like '1f77bdfc%' and superseded_by_person_id is null").fetchone()[0])
new = {13: sper}
for n in range(14, 23): new[n] = cur[n - 1]
bad = 0
for n in range(13, 24):
    tgt = new.get(n, cur[n])
    e = c.execute("select family_name, first_name, patronymic from raw.person_entry where entry_id=?", [P % n]).fetchone()
    p = c.execute("select display_name from entities.person where person_id=?", [tgt]).fetchone()[0]
    ok = p.split(',')[0][:5].lower() == e[0][:5].lower()
    bad += not ok
    print(P % n, e, '->', p, '' if ok else '  <-- NAME MISMATCH', '(unchanged)' if tgt == cur[n] else '')
assert not bad, 'name mismatch -- nothing written'
if write:
    for n in new:
        if new[n] != cur[n]:
            c.execute("update entities.person_link set person_id=?, match_method='manual_relink_134', match_confidence=1.0 where entry_id=?", [new[n], P % n])
    print('WRITTEN', sum(new[n] != cur[n] for n in new), 'links')
