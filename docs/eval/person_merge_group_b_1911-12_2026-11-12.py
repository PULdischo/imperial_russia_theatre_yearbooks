"""1911-12 merge batch, Group B (RG 2026-11-12: "Yes, merge them"; docs/eval/person_merge_candidates_batch.md, "1911-12 batch").
The class of 1911 joining the company: each 1910-11 Graduates entry (name only) and the same person's first 1911-12 company
entry (same city, name printed the same; the company entry adds the patronymic and a summer-1911 start). The graduate record
survives (older). Same mechanism as Group A. Dry run on a copy unless --write.
usage: uv run python docs/eval/person_merge_group_b_1911-12_2026-11-12.py [--write]"""
import sys, shutil, uuid, datetime, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
REASON = ("1911-12 merge batch Group B (RG 2026-11-12): 1910-11 graduate joins the company in 1911-12, same city, "
          "name printed the same")
# survivor prefix -> loser prefixes (display name for the log)
GROUPS = [
    ("28d6c38b", ["88794702"]),   # Александрова, Лидія -> Лидія Павловна (Moscow)
    ("94f663d2", ["2c959ed9"]),   # Бажанова, Марія -> Марія Павловна (Moscow)
    ("2f7498c5", ["051758d0"]),   # Владиміровъ, Петръ -> Владимировъ, Петръ Николаевичъ (SP)
    ("8c175dcd", ["f710c7d8"]),   # Клементьева, Марія -> Марія Львовна (Moscow)
    ("78b7bf42", ["647dcd12"]),   # Невельская, Софья -> Невельская 2-я, Софія Карловна (Moscow)
    ("b7022acd", ["71bb2daf"]),   # Павловъ, Евгеній -> Евгеній Павловичъ (Moscow)
    ("374a68cb", ["4a09937e"]),   # Покровская, Анна -> Анна Николаевна (Moscow)
    ("5da71039", ["60ed6a22"]),   # Свобода, Вячеславъ -> Вячеславъ Вячеславовичъ (Moscow)
    ("77543477", ["5278b430"]),   # Фокина, Екатерина -> Фокина 2-я, Екатерина Владиміровна (SP)
    ("12843ab3", ["750087dc"]),   # Цаплева, Елизавета -> Елизавета Павловна (Moscow)
    ("402def7d", ["e049c2fc"]),   # Цаплинъ, Павелъ -> Павелъ Ивановичъ (Moscow)
]

if '--write' in sys.argv:
    DB = REAL
    shutil.copy2(REAL, f"outputs/full_run/imperial_theaters.pre_merge_group_b_1911-12_{datetime.date.today()}.duckdb")
else:
    DB = '/private/tmp/claude-502/merge_group_b_dry.duckdb'
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
