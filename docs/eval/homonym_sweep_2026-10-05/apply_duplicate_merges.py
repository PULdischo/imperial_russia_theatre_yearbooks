"""Apply RG-approved merges from the 94-pair duplicate review (docs/eval/homonym_sweep_2026-10-05/duplicate_person_pairs.md). Mechanism = issue #125/#131 precedent:
tombstone the loser (superseded_by_person_id) + person_merge_log 'confirmed_manual' + BE._repoint_all_superseded + BE._refresh_canonical_fields.
Aborts if a loser is referenced by person_wikidata_link / production_credit_link / creator_person (survivor choice would orphan it). Dry run on a COPY unless --write."""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE
REAL = 'outputs/full_run/imperial_theaters.duckdb'
DB = REAL if '--write' in sys.argv else '/tmp/dupmerge_dry.duckdb'
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
APPLIED = {'68fa76', '0c1633', 'c11d62', 'b53a76', '24f7fc'}   # survivors of merges already applied to production (skipped on re-run)
MERGES = [  # (survivor prefix, [loser prefixes], label, reason)
    ('68fa76', ['110f6d', '396ea1', '9327f4', '773570'], 'Волконскій Григорій Дмитріевичъ (князь)',
     'RG-approved 2026-10-05, labelled UNCERTAIN: lighting chief (ProductionTeam, since 1887-09-01, left 1898-09-01) and geography teacher in the ballet department of the Petersburg school (TheaterSchoolStaff, since 1888-09-01, left 1901-09-01); same name, rank, 20 entries, one line per list per year; the pairing of the two posts is unusual -- see uncertain_person_identities.md'),
    ('0c1633', ['335352', '8fc18b'], 'Черемухинъ Михаилъ Никифоровичъ',
     'RG-approved 2026-10-05: inspector of the Moscow school (съ 6 сентября 1887) who also teaches mathematics and geography in the ballet department; the teacher line prints "(инспекторъ Училища)" every year; 40 entries over 20 seasons'),
    ('c11d62', ['e1cac8', '50a743'], 'Петровъ Василій Ивановичъ',
     'RG-approved 2026-10-05: teacher of Выразительное чтеніе (ballet dept, 1894-1905) and Практика драматическаго искусства (drama courses, start 1 сентября 1902, 1902-1910); one line per season, identical start dates, no overlap'),
    ('b53a76', ['8872b8', '0fd64e'], 'Потѣхинъ Алексѣй Антиповичъ',
     'RG-approved 2026-10-05: honorary member of the school conference, one line every season 1890-91..1907-08, no overlap'),
    ('24f7fc', ['2f3464'], 'Рюминъ Иванъ Ивановичъ',
     'RG-approved 2026-10-05: manager of the Petersburg school from 27 May 1887, died 2 Sept 1899; the 1899-00 manager line carrying the death note was on a separate record'),
    ('0ef17f', ['d42d9e'], 'Добрынина Елена Андреевна',
     'RG-approved 2026-10-05: class lady (Классныя дамы) since 1 April 1884, one line per season 1890-91..1899-00, died 27 Oct 1899; the 1896-97 line printed the start date without the day ("съ апрѣля 1884"), so it had its own record'),
]
def full(p):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
    assert len(r) == 1, (p, r); return str(r[0][0])
before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
MERGES = [m for m in MERGES if m[0] not in APPLIED]
for surv, losers, label, reason in MERGES:
    s = full(surv)
    for lp in losers:
        l = full(lp)
        for t, c in (('person_wikidata_link', 'person_id'), ('production_credit_link', 'person_id'), ('creator_person', 'proposed_roster_person_id')):
            n = con.execute(f"select count(*) from entities.{t} where cast({c} as varchar)=?", [l]).fetchone()[0]
            assert n == 0, f'loser {lp} is referenced by entities.{t} ({n} rows) -- choose another survivor'
        d1 = con.execute("select display_name from entities.person where person_id=?", [s]).fetchone()[0]
        d2 = con.execute("select display_name from entities.person where person_id=?", [l]).fetchone()[0]
        con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
        con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)", [str(uuid.uuid4()), s, l, d1, d2, 1.0, 'manual_review', 'confirmed_manual', 'manual', reason])
        print(f'{label}: {lp} -> {surv}')
BE._repoint_all_superseded(con); BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live persons', before, '->', after)
for surv, *_ in MERGES:
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where cast(person_id as varchar) like ?", [surv + '%']).fetchall())
con.close(); print('DONE on', DB)
