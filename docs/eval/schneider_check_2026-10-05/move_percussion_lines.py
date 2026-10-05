"""Move the three 1907-10 percussion lines (printed 'Шредеръ, Карлъ Ѳедоровичъ, съ 1 сентября 1902, Ударные инструменты') from the trombonist's person 019ed1 (Шнейдеръ) to the
percussionist cd67fa (Шредеръ Карлъ Августовичъ). RG decision 2026-10-05: chair and list position are continuous; the patronymic/start-date change is a probable yearbook slip.
Dry run on a copy unless --write."""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else '/tmp/schn_dry.duckdb'
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
MOVES = ['musicians_1907-08_SP_p003__e019', 'musicians_1908-09_SP_p004__e011', 'musicians_1909-10_SP_p004__e016']
def full(p):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
    assert len(r) == 1, (p, r); return str(r[0][0])
src, dst = full('019ed1'), full('cd67fa')
for e in MOVES:
    r = con.execute("select e.family_name, e.instrument, e.tenure_note_text from raw.person_entry e where entry_id=?", [e]).fetchone()
    assert r[0] == 'Шредеръ' and r[1] == 'Ударные инструменты', (e, r)
    assert str(con.execute("select person_id from entities.person_link where entry_id=?", [e]).fetchone()[0]) == src, e
d1 = con.execute("select display_name from entities.person where person_id=?", [src]).fetchone()[0]
d2 = con.execute("select display_name from entities.person where person_id=?", [dst]).fetchone()[0]
for e in MOVES: con.execute("update entities.person_link set person_id=?, match_method='manual_move', match_confidence=1.0 where entry_id=?", [dst, e])
con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), src, dst, d1, d2, 0.0, 'homonym_split', 'split_manual', 'manual',
  'RG 2026-10-05, labelled UNCERTAIN: the 1907-10 percussion lines (Шредеръ Карлъ Ѳедоровичъ, съ 1 сентября 1902, Ударные инструменты) were attached to the trombonist Шнейдеръ Карлъ Ѳедоровичъ (019ed1) by name/patronymic/start-date similarity; in 1908-10 a trombone and a percussion line print in the same list, so two men. Moved to the percussionist Шредеръ Карлъ Августовичъ (cd67fa): same chair and alphabetical position as 1906-07'])
BE._refresh_canonical_fields(con)
for p in (src, dst):
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where person_id=?", [p]).fetchall())
con.close(); print('DONE on', DB)
