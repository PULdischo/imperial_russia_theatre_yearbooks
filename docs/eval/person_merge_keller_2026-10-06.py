"""Merge the three live records of Келеръ (Келлеръ 1-й), Морицъ (Морисъ) Ѳедоровичъ, RG 2026-10-06 ("fix").
One man in every volume 1890-91..1907-08: start 1 сентября 1881, SP first violin (1890-98), Михайловскій
capellmeister from 1 Dec 1898, Александринскій from 1 Sep 1906. The records split on printed variants:
"Келеръ/Келлеръ 1-й" (1893-98) and "Морисъ" (1906-07 p005, 1907-08 p003; both zoomed on the scans 2026-10-06,
genuinely printed с, not misreads). In 1906-07 the print lists him twice (Александринскій, transferred, and
still under the Михайловскій). Survivor 2884550f = the roster person production_creators.csv's keller_m points to.
Same mechanism as person_merge_batch_apply_2026-10-05.py. Dry run on a copy by default; --write for full_run.
usage: uv run python docs/eval/person_merge_keller_2026-10-06.py [--write]"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else '/tmp/merge_keller_dry.duckdb'
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
SURV, LOSERS = '2884550f', ['ab138e8b', 'ad393322']
REASON = ('one man: same name and patronymic, same start 1 сентября 1881, first violin -> Михайловскій capellmeister 1898 '
          '-> Александринскій 1906; records split on printed variants Келлеръ 1-й (1893-98) and Морисъ (1906-08, scan-confirmed)')


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
                [str(uuid.uuid4()), s, l, d1, d2, 1.0, 'manual_review', 'confirmed_manual', 'manual', 'RG 2026-10-06: ' + REASON])
    print(f'{d2} ({lp}) -> {d1} ({SURV})')
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live persons', before, '->', after)
print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where person_id=?", [s]).fetchall())
con.close()
print('WRITTEN to', DB)
