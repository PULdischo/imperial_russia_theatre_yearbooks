"""1911-12 merge batch, Group A (RG 2026-11-12: "Yes, merge Group A"; docs/eval/person_merge_candidates_batch.md,
"1911-12 batch"). Same family, first name and patronymic (or patronymic blank on one side), same list, consecutive
seasons: the 1911-12 entry -- and, where 1910-11 also left one, the 1910-11 one-season record -- joins the established
record, which survives (its id is the one curated files point at). Same mechanism as person_merge_manual.py, one backup
for the whole batch. Dry run on a copy unless --write.
usage: uv run python docs/eval/person_merge_group_a_1911-12_2026-11-12.py [--write]"""
import sys, shutil, uuid, datetime, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
REASON = ("1911-12 merge batch Group A (RG 2026-11-12): same name and list in consecutive seasons; the automatic merge "
          "skipped it (no start date printed, or the printed start date varies)")
# survivor prefix -> loser prefixes (display name for the log)
GROUPS = [
    ("2700eadd", ["8a7f1096"]),                # Байковъ, Андрей Андреевичъ
    ("c58d2480", ["3ef85960", "76f257bc"]),    # Боборыкинъ, Петръ Дмитріевичъ (+1910-11)
    ("a0e9491a", ["ccbf54d0", "02e03a6d"]),    # Бруннеръ, Леонтій Федоровичъ (+1910-11)
    ("55d0b0a4", ["0f5a1d78"]),                # Брындинъ, Корнелій Корнеліевичъ
    ("3f35335b", ["cd2764dd"]),                # Воздвиженскій, Виталій Петровичъ
    ("13a8cdbf", ["cdefacf4"]),                # Герасимова, Варвара Ивановна
    ("0b96035d", ["14bc65bc", "913b9dfd"]),    # Казанскій, Левъ Ивановичъ (+1910-11)
    ("34a0e13e", ["4214f7f9"]),                # Карпова, Лидія Владиміровна
    ("3281b91b", ["e632d3b0"]),                # Касаткинъ, Юрій Владиміровичъ
    ("31caa25a", ["6cddd202", "e30cb2f7"]),    # Клемецкая, Евгенія Вацлавовна (+1910-11)
    ("12e20c15", ["80e0409f"]),                # Крюгеръ, Эмануилъ Эдуардовичъ
    ("803d8943", ["2714c66d"]),                # Легатъ, Антонина Савельевна
    ("15715408", ["218f1f2e"]),                # Литке, Константинъ Константиновичъ
    ("723f64f2", ["8a6a6670"]),                # Мендесъ, Джульетта (Іосифовна)
    ("fafdf7e9", ["be447344", "9dd66289"]),    # Наумовъ, Павелъ (Наумовичъ) (+1910-11)
    ("2634b8f5", ["8bb323ef"]),                # Печатниковъ, Николай Алексѣевичъ
    ("730b588d", ["2025ff82", "d4ad1e76"]),    # Пигулевскій, Василій Фавстовичъ (+1910-11)
    ("3151915b", ["af5b075c"]),                # Плаксинъ, Александръ Леонтьевичъ / Леонтьёвичъ
    ("7608d958", ["a87baef5", "2053dfdc"]),    # Погожевъ, Владиміръ Петровичъ (+1910-11)
    ("28890d06", ["2f4b86e1"]),                # Сенкусъ
    ("22a90baa", ["afb72b37"]),                # Соколовъ, Николай Георгіевичъ
    ("0fde7730", ["143a5051"]),                # Тецъ, Владиміръ Карловичъ
]

if '--write' in sys.argv:
    DB = REAL
    shutil.copy2(REAL, f"outputs/full_run/imperial_theaters.pre_merge_group_a_1911-12_{datetime.date.today()}.duckdb")
else:
    DB = '/private/tmp/claude-502/merge_group_a_dry.duckdb'
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
