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
    ('527973', ['0aeaf9'], 'Петровъ Иванъ Степановичъ',
     'RG decision 2026-10-05 (merge, labelled UNCERTAIN): tutor (Воспитатели, since 1 сентября 1891, 1890-91..1907-08) and teacher of preparatory classes (since 15 ноября 1907, 1908-10); the tutor line ends where the teacher line begins, but start dates differ and no transfer is printed'),
    ('c58d24', ['232905'], 'Боборыкинъ Петръ Дмитріевичъ',
     'RG-approved 2026-10-05: honorary member of the school conference (Moscow list to 1898-99, both lists 1899-00..1901-02 with the transfer note, Petersburg from 1902-03); the 1908-10 lines were on a separate record'),
    ('0b9603', ['d0ad53'], 'Казанскій Левъ Ивановичъ',
     'RG-approved 2026-10-05: Moscow staff/senior physician of the Directorate (since 20 April 1885) and doctor of the Moscow school; the 1908-10 school-doctor lines were on a separate record'),
    ('4af6a7', ['d54352'], 'Пчельниковъ Павелъ Михайловичъ',
     'RG-approved 2026-10-05: manager of the Moscow Office of the Imperial Theaters since 16 June 1882 (Administrators list) and manager of the Moscow school, honorary member of the school conference; the 1908-10 lines were on a separate record'),
    ('a550ac', ['750b99'], 'Габріель',
     'RG-approved 2026-10-05: French teacher in the Petersburg ballet department, since 1 сентября 1890; 1890-91 and 1891-92 lines (surname only), appears in no other volume'),
    ('7029d5', ['6f5c3c'], 'Гавронскій',
     'RG-approved 2026-10-05: teacher of Законъ Божій (Roman Catholic pupils), Petersburg ballet department, since 1 февраля 1895, 1894-95..1902-03 (left 1 сентября 1902); surname only'),
    ('3e22b9', ['3732cd'], 'Жукова Вѣра Васильевна',
     'RG-approved 2026-10-05: dance teacher in the Petersburg ballet department since 1 сентября 1901, 1901-02..1909-10; the ballet artist Жукова 1-я (c03d21) stays separate, labelled uncertain (list entry 10)'),
    ('76d1b9', ['de05ca'], 'Преображенская Ольга Іосифовна',
     'RG-approved 2026-10-05: the 1908-09 ballet-artist line (the only season missing from 76d1b9) prints the start date 1899 where 19 other volumes print 1889; scan-verified (p. 91, no. 74) as a genuine print typo'),
    ('088ec9', ['224c50'], 'Піотровичъ',
     'RG-approved 2026-10-05: teacher of Законъ Божій (Roman Catholic pupils), Petersburg ballet department, since 1 ноября 1888, 1890-91..1893-94 (left 1 сентября 1894); surname only'),
    ('87c046', ['023b1e', '1150d3'], 'Рыхлякова 1-я Варвара Трофимовна',
     'RG-approved 2026-10-05: ballet artist Рыхлякова 1-я, 1890-91..1909-10; the 1904-05 line (fields misparsed, scan-verified start "1 сентября 1890") and the 1908-10 lines (start "1 сентября 1890") were on their own records; start date printed 1 іюня 1890 in the other volumes'),
    ('33e281', ['760668', 'af49d5', '7bc39e'], 'Рыхлякова 2-я Наталья Трофимовна',
     'RG-approved 2026-10-05: ballet artist Рыхлякова 2-я, joined the company 1 іюня 1892 (matches the 1891-92 Graduates line), one line per season 1892-93..1909-10 split over three records by the Наталья/Наталія spelling and a misparsed 1904-05 line'),
    ('87c046', ['5d6d24'], 'Рыхлякова 1-я Варвара Трофимовна',
     'RG decision 2026-10-05 (merge, labelled UNCERTAIN): the 1909-10 Petersburg school teacher line (съ 1 ноября 1907, no subject stored) joined to the ballet artist of the same name; dual dancer/teacher listing assumed'),
    ('6d97a1', ['ed66b3'], 'Тихоміровъ Василій Дмитріевичъ',
     'RG-approved 2026-10-05: Moscow ballet artist (since 1 сентября 1893, assistant ballet master from 22 Dec 1909) and Moscow school dance teacher (since 1 октября 1896); the same two lines every season 1897-98..1909-10, split at 1908-09'),
]
def full(p):
    r = con.execute("select person_id from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchall()
    assert len(r) == 1, (p, r); return str(r[0][0])
before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
def is_live(p):   # a merge is pending while its losers are still live persons (skipping by SURVIVOR once silently dropped a second merge into the same survivor)
    return con.execute("select count(*) from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [p + '%']).fetchone()[0] > 0
MERGES = [m for m in MERGES if all(is_live(lp) for lp in m[1])]
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
