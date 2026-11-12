"""1911-12 merge batch, Group B spelling variants (RG 2026-11-12: "Yes, merge them"; docs/eval/person_merge_candidates_batch.md,
"Group B, spelling variants"). The class of 1911 whose surname prints differently in the 1910-11 graduate list and the 1911-12
company list (both zoomed by Claude 2026-11-12). The graduate record survives. Dry run on a copy unless --write.
usage: uv run python docs/eval/person_merge_group_b2_1911-12_2026-11-12.py [--write]"""
import sys, shutil, uuid, datetime, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
REASON = ("1911-12 merge batch Group B spelling variants (RG 2026-11-12): 1910-11 graduate joins the company in 1911-12, same city, "
          "surname printed differently, both lists zoomed")
# survivor prefix -> loser prefixes (display name for the log)
GROUPS = [
    ("8f4bbc7c", ["d9304a99"]),   # Вольшакова, Лидія -> Большакова 2-я, Лидія Іосифовна (SP)
    ("c4d7ab13", ["782afaae"]),   # Боронцовъ, Владиміръ -> Воронцовъ, Владиміръ Петровичъ (SP)
    ("7bf20009", ["92808b96"]),   # Гавриловъ, Александръ (graduate) -> Гавриловъ, Александръ (SP ballet)
    # Ивановъ, Николай (graduate) NOT merged: the 1911-12 SP list has both «Ивановскій, Николай Павловичъ (съ 1 іюня 1911)»
    # and «Ивановъ 5-й, Николай Павловичъ» (undated); which is the graduate is ambiguous -> RG (rechecked on the scans 2026-11-12)
    ("40bf44fb", ["b042e317"]),   # Литовкинъ, Сергѣй -> Литавкинъ, Сергѣй Сергѣевичъ (SP)
    ("dadf00bb", ["1f5195c0"]),   # Гилевичъ, Евгенія -> Гитлевичъ, Евгенія Львовна (Moscow)
    ("83f7e4e5", ["e13cb221"]),   # Подлевская, Янина -> Годлевская, Янина Михайловна (Moscow)
    ("c3b834fc", ["d5539533"]),   # Чичелева, Елена -> Чичилева 2-я, Елена Васильевна (Moscow)
]

if '--write' in sys.argv:
    DB = REAL
    shutil.copy2(REAL, f"outputs/full_run/imperial_theaters.pre_merge_group_b2_1911-12_{datetime.date.today()}.duckdb")
else:
    DB = '/private/tmp/claude-502/merge_group_b2_dry.duckdb'
    shutil.copy2(REAL, DB)
con = duckdb.connect(DB)


def full(prefix):
    r = con.execute("select cast(person_id as varchar), display_name from entities.person "
                    "where cast(person_id as varchar) like ? and superseded_by_person_id is null", [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return r[0]


apart = BE._keep_apart_pairs(con)
before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
for surv, losers in GROUPS:
    s = full(surv); ls = [full(l) for l in losers]
    ids = [s[0]] + [l[0] for l in ls]
    assert not any(frozenset((a, b)) in apart for a in ids for b in ids if a < b), ("kept apart by RG", s)
    queued = set()
    for cid, a, b in con.execute("select candidate_id, cast(person_id_1 as varchar), cast(person_id_2 as varchar) "
                                 "from entities.person_candidate where status='pending'").fetchall():
        if a in ids and b in ids:
            con.execute("update entities.person_candidate set status='confirmed_manual' where candidate_id=?", [cid])
            queued.add(frozenset((a, b)))
    for l in ls:
        if frozenset((s[0], l[0])) not in queued:
            con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
                        [str(uuid.uuid4()), s[0], l[0], s[1], l[1], 1.0, 'manual_review', 'confirmed_manual', 'manual', REASON])
        con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s[0], l[0]])
BE._log_decided_candidates(con)
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)
for surv, _ in GROUPS:
    print(con.execute("select display_name, first_attested_season, last_attested_season, "
                      "(select count(*) from entities.person_link l where l.person_id=p.person_id) "
                      "from entities.person p where cast(person_id as varchar) like ?", [surv + '%']).fetchone())
after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
print('live persons', before, '->', after, '| written' if DB == REAL else '| dry run')
