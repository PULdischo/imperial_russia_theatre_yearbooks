"""Merge the two live records of Эдуардова, Евгенія (Платоновна), RG 2026-10-10 ("fix all these").
The 1900-01 Graduates list prints "Эдуардова, Евгенія" (no patronymic) leaving the Petersburg school's ballet section
"съ 1-го іюня 1901 г., въ С.-Петербургскую балетную группу"; the SP BalletArtists lists 1901-02..1910-11 print
Эдуардова, Евгенія Платоновна "(съ 1 іюня 1901 г.)". Same name, same date, same troupe; no other Эдуардова.
Same mechanism as person_merge_batch_apply_2026-10-05.py. Dry run on a copy by default; --write for full_run.
usage: uv run python docs/eval/person_merge_eduardova_2026-10-10.py [--write]"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else '/tmp/merge_eduardova_dry.duckdb'
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
SURV, LOSERS = '7e0939fb', ['f2b9f4e5']
REASON = ('one woman: the 1900-01 graduate line (no patronymic) joins the SP ballet on 1 іюня 1901, the start date '
          'the SP BalletArtists lists print for Эдуардова, Евгенія Платоновна from 1901-02 on')


def full(prefix):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return str(r[0][0])


before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
s = full(SURV)
for lp in LOSERS:
    l = full(lp)
    d1, d2 = (con.execute("select display_name from entities.person where person_id=?", [x]).fetchone()[0] for x in (s, l))
    con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
                [str(uuid.uuid4()), s, l, d1, d2, 1.0, 'manual_review', 'confirmed_manual', 'manual', 'RG 2026-10-10: ' + REASON])
    print(f'{d2} ({lp}) -> {d1} ({SURV})')
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live persons', before, '->', after)
print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where person_id=?", [s]).fetchall())
con.close()
print('WRITTEN to', DB)
