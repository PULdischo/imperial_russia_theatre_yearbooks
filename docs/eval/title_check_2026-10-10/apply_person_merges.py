"""Merge the two live person pairs that differ only by a final ь/ъ in the family name (issue #151, RG: "Do the 18
title groups and 2 person pairs ... each needs the scan").
Mechanism = the 2026-10-05 batch (docs/eval/person_merge_batch_apply_2026-10-05.py): tombstone the loser
(superseded_by_person_id), add a person_merge_log row (confirmed_manual), BE._repoint_all_superseded + _refresh_canonical_fields.
Evidence (scan, blind reader of 2026-10-10, reader_reports/persons.csv):
  * Оголейтъ Марія Германовна: 1897-98 SP p003 no. 77 prints «Оголейтъ 1-я, Марія Германовна (съ 8 іюля 1876 г.)» and
    1899-00 SP p003 no. 78 «Оголейтъ 3-я, Марія Германовна (съ 8 іюля 1876 г.)» -- both end in ъ; the other record
    (383eea63, «Оголейть 2-я», 1890-91..1896-97) carries the same name and the same date 8 іюля 1876. The ordinal changes
    between volumes as sisters leave; the person does not.
  * Галатъ Надежда: the 1893-94 school graduates list prints «Галатъ, Надежда.» (hard sign, no patronymic or date) with
    «съ 1-го сентября 1894 года въ Московскую балетную труппу»; the BalletArtists records (35f5810e, «Галать Надежда
    Петровна», Moscow) all start «съ 1 сентября 1894 г.».
usage: uv run python docs/eval/title_check_2026-10-10/apply_person_merges.py [--write]"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
DRY = '/private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/41c12e63-8fd3-4d7c-9b0c-93c1ff66bdab/scratchpad/merge_dry.duckdb'
DB = REAL if '--write' in sys.argv else DRY
if DB != REAL: shutil.copy2(REAL, DB)
con = duckdb.connect(DB)

# (survivor prefix, [loser prefixes], label, reason)
MERGES = [
    ('383eea63', ['9455596b'], 'Оголейтъ/Оголейть Марія Германовна',
     'same name, patronymic and service start 8 іюля 1876; 1897-98 and 1899-00 print ъ and a different ordinal (scan-read 2026-10-10)'),
    ('35f5810e', ['4f799a33'], 'Галатъ/Галать Надежда',
     'school graduate 1893-94 (printed Галатъ, to the Moscow ballet from 1 сентября 1894) = BalletArtists Moscow from 1 сентября 1894 (scan-read 2026-10-10)'),
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
                    [str(uuid.uuid4()), s, l, d1, d2, 1.0, 'manual_review', 'confirmed_manual', 'manual', 'ь/ъ pair, issue #151 (RG): ' + reason])
        print(f'{name}: {lp} -> {surv}')
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live persons', before, '->', after)
for surv, losers, name, reason in MERGES:
    print(con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where cast(person_id as varchar) like ?", [surv + '%']).fetchall())
con.close()
print('WRITTEN to', DB)
