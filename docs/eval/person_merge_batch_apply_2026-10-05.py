"""Apply the person-merge batch decided with RG on 2026-10-05 (docs/eval/person_merge_candidates_batch.md).
Mechanism = the issue #125/#131 precedent: tombstone the loser (superseded_by_person_id), add a person_merge_log row
(confirmed_manual), then BE._repoint_all_superseded + BE._refresh_canonical_fields.  Survivors were chosen so that
downstream references (Wikidata link, production_credit_link) stay valid.
Dry run (default) works on a throwaway COPY of the database; --write works on outputs/full_run.
usage: uv run python docs/eval/person_merge_batch_apply_2026-10-05.py [--write]"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else '/tmp/merge_dry.duckdb'
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)

# (survivor prefix, [loser prefixes], family, reason)
MERGES = [
    ('831b71', ['a9d821'], 'Зандинъ Михаилъ', 'one decorator: same start 1 мая 1907 in 3 of 4 volumes, promotion path, no overlap; patronymic Ивановичъ (1906-08) vs Павловичъ (1908-10) -- RG: investigate later'),
    ('ea76e8', ['1134bf'], 'Лебедевъ Иванъ (ProductionTeam)', 'one prop-maker: same Мариинскій Бутафоръ post, same start 3 іюня 1889, no overlap; patronymic Васильевичъ (1907-08) vs Афанасьевичъ (1908-10) -- RG: investigate later'),
    ('e04344', ['0f4adf', '6310e8'], 'Петипа Маріусъ Ивановичъ', 'one man: first ballet-master 1890-1910 (BalletArtists) and school teacher since 1 сентября 1855; identical name, patronymic and start date; 6310e8 = the 1892-93 school row seeded in issue #134'),
    ('09350c', ['bfe3f9'], 'Чекетти Энрико/Генрихъ Цезаревичъ', 'one man in two lists (company second ballet-master "Генрихъ", school teacher "Энрико"); same patronymic; display name Энрико set in the research layer (RG)'),
    ('6b54e5', ['0c0f54'], 'Ширяевъ Александръ Викторовичъ', 'the 1890-91 school row prints Васильевичъ (genuine print variant, verified on the scan) -- same first name, subject Танцы, start 15 сентября 1891'),
    ('7fd62c', ['dd0ff7'], 'Голяховскій Петръ', 'one teacher: same post and start 7 сентября 1888 throughout; Васильевичъ printed in 1901-06 (verified in the 1903-04 blind sample), Власьевичъ elsewhere'),
]


def full(prefix):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return str(r[0][0])


before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
for surv, losers, name, reason in MERGES:
    s = full(surv)
    for lp in losers:
        l = full(lp)
        d1 = con.execute("select display_name from entities.person where person_id=?", [s]).fetchone()[0]
        d2 = con.execute("select display_name from entities.person where person_id=?", [l]).fetchone()[0]
        con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
        con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
                    [str(uuid.uuid4()), s, l, d1, d2, 1.0, 'manual_review', 'confirmed_manual', 'manual', 'merge batch review 2026-10-05 (RG): ' + reason])
        print(f'{name}: {lp} -> {surv}')
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live persons', before, '->', after)
for surv, losers, name, reason in MERGES:
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where person_id=?", [full(surv) if False else con.execute("select person_id from entities.person where cast(person_id as varchar) like ?", [surv + '%']).fetchone()[0]]).fetchall())
con.close()
print('WRITTEN to', DB)
