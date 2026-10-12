"""Apply the ordinal-shift review decided with RG on 2026-10-12 (docs/eval/person_merge_candidates_batch.md).
Mechanism = the 2026-10-05 batch's: tombstone the loser (superseded_by_person_id), log it (confirmed_manual), then
BE._repoint_all_superseded + BE._refresh_canonical_fields.  Two records that each hold two people are split first by
moving one entry to the person it belongs to (move_entry.py's mechanism).
Queued candidate pairs get status 'confirmed_manual' (or 'rejected' for the two cross pairs of the split records) --
NOT 'confirmed': reconcile_person_merges would then pick its own survivor (the smallest id) on the next rebuild.
Dry run (default) works on a throwaway COPY given as argv[1]; --write works on outputs/full_run.
usage: uv run python docs/eval/person_merge_ordinal_shift_apply_2026-10-12.py <copy_path> | --write"""
import sys, shutil, uuid, duckdb
sys.path.insert(0, 'pipeline')
import build_entities as BE

REAL = 'outputs/full_run/imperial_theaters.duckdb'
if '--write' in sys.argv:
    DB = REAL
else:
    DB = sys.argv[1]
    shutil.copy2(REAL, DB)
con = duckdb.connect(DB)
TAG = 'ordinal-shift review 2026-10-12 (RG): '

# The 30 plain graduate-to-company pairs: survivor = the company record (more entries), loser = the graduate.
PLAIN = [('6273a1', 'd8d544'), ('e9f2f0', '2165d0'), ('0f5d90', '3335a6'), ('029869', '513299'), ('25ecbc', 'ec084b'),
         ('b62d1f', 'fc0068'), ('599e50', '35546d'), ('7c55da', 'bdbbbd'), ('1ab20c', '202592'), ('06fbd5', '3841f5'),
         ('4ef695', '5f271c'), ('1ced70', '6ca724'), ('36763e', '369f12'), ('067275', 'bd6b67'), ('2b3824', 'affaa4'),
         ('11f34b', '31f865'), ('e66fc9', '6ded9c'), ('86235b', '09d031'), ('5fd9cb', 'beb615'), ('6b6d87', 'f61ec1'),
         ('e63497', 'bb1ddc'), ('076cab', 'c5244f'), ('5cf33f', '5f9001'), ('309250', 'e52de0'), ('26b1ee', '89e758'),
         ('17bb41', 'e4dd63')]
PLAIN_REASON = 'graduate (no patronymic, no ordinal) = the company record with the same name and printed start date'

# (survivor, [losers], label, reason)
MERGES = [(s, [l], 'plain graduate pair', PLAIN_REASON) for s, l in PLAIN] + [
    ('021b0d', ['97676f', '0c2699'], 'Бакинъ Александръ Всеволодовичъ', 'graduate + «3-й» + the 1908-09 row, printed «Бакинъ 2-й, Александръ Всеволодовичъ (съ 1895 г.)» (scan)'),
    ('2c7d73', ['b75eaf', 'ba3854'], 'Гончаровъ Леонидъ Ивановичъ', 'graduate + «2-й»; the 1910-11 row prints «съ 1 іюня 1900 г.» for 1907 (scan; print error)'),
    ('8fb4d1', ['088e87', '2a7cdf'], 'Панова Елизавета Евгеньевна', 'graduate + «4-я» 1896-97 + 1897-99; the print has «4-я, Елизавета Евгеньевна» in 1896-97 and 1897-98 (scan)'),
    ('1d7a9b', ['f3629e', '71546a'], 'Ѳедорова Екатерина Никифоровна', 'graduate + «1-я»; the 1904-05 row is printed «Федорова 1-я, Екатерина Никифоровна» (scan), extracted as Никитовна'),
    ('3a0568', ['380540'], 'Ильина Елена Ивановна', '1894 graduate = «Ильина 3-я, Елена Ивановна (съ 1 іюня 1894 г.)» (scan, reduced size)'),
    ('222cec', ['94b516', 'e452c2'], 'Мартьяновъ Александръ Александровичъ', 'graduate + artist/assistant regisseur 1893-1911; the print has «Мартьяновъ» throughout (scan), Мартыновъ etc. are extraction misreads'),
    ('6d97a1', ['75d4f2', '58c4eb', '690831', '974a69'], 'Тихомировъ Василій', 'one man: start 1 сентября 1893 throughout, the same leading roles across 1899-00/1900-01; artists\' list prints Ивановичъ 1893-1900, Дмитріевичъ after -- uncertain_person_identities.md #26'),
    ('154c0f', ['5a9a14', '53235d'], 'Сергѣевъ Николай Григорьевичъ', 'graduate + regisseur + «1-й, Николай Георгіевичъ» 1909-11 (same start 1 іюня 1894; no second candidate in the corpus) -- uncertain_person_identities.md #27'),
    ('7dd0bc', ['7a10e6', '3aa7d7'], 'Ивановъ Иванъ Николаевичъ', 'graduate + the 1908-09 row printed «1-й, Иванъ Григорьевичъ (съ 1 іюня 1899 г.)» (his date and post); the 1906-07 row stays with Григорьевичъ -- uncertain_person_identities.md #28'),
    ('18b3fd', ['43c8c6'], 'Павлова Анна Матвѣевна', 'the Moscow 1907-08 row is printed «Павлова 2-я, Анна Матвѣевна (съ 1 іюня 1899 г.)», 1 appearance (scan)'),
    ('974ba5', ['4e6cf9'], 'Чіарлоне Виргинія Михайловна', 'harpist; the 1895-96 Moscow row prints «Съ 1 іюня 1896 года переведена въ С.-Петербургскій оркестръ оперы и балета» (scan)'),
    ('b7652f', ['671bc6'], 'Чіарлоне Джанина', 'one harpist; the print alternates Джанина / Джаннина (scan, 1894-95..1899-00)'),
    # after the two splits below
    ('3a64bd', ['8bb688', '924313'], 'Иванова Надежда Михайловна', '8bb688 keeps only its 1901-02 row, printed «Иванова 4-я, Надежда Михайловна (съ 1 сентября 1900 г.)» (scan); 924313 = the 1900 Moscow graduate'),
    ('05efa7', ['38a3db'], 'Ивановъ Александръ Николаевичъ', '38a3db keeps only its 1895-96 graduate row (съ 1 мая 1896 г.)'),
]
# (from, to, page_id of the entry to move, reason)
MOVES = [
    ('8bb688', '495eba', 'balletartists_1907-08_MSK_p002', '«Иванова 4-я, Надежда» held two women: the 1907-08 row (Сергѣевна, съ 1 августа 1907) is Надежда Сергѣевна'),
    ('38a3db', '95b2cd', 'graduates_1905-06_p000', 'graduate «Ивановъ, Александръ» held two graduates: the 1906 one (съ 1 іюня 1906) is Александръ Гавриловичъ; RG: Николаевичъ and Гавриловичъ are two men'),
]
# queued candidate pairs that must NOT merge as pairs (the other half of each split record)
REJECT = [('495eba', '8bb688'), ('38a3db', '95b2cd')]


def full(prefix, live=True):
    q = "select person_id from entities.person where cast(person_id as varchar) like ?" + (" and superseded_by_person_id is null" if live else "")
    r = con.execute(q, [prefix + '%']).fetchall()
    assert len(r) == 1, (prefix, r)
    return str(r[0][0])


def disp(pid):
    return con.execute("select display_name from entities.person where person_id=?", [pid]).fetchone()[0]


before = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
pend_before = con.execute("select count(*) from entities.person_candidate where status='pending' and match_reason='ordinal_shift'").fetchone()[0]

# downstream references held by a loser (the survivor must carry them)
involved = {full(l): full(s) for s, ls, _, _ in MERGES for l in ls}
for tbl in ('person_wikidata_link', 'production_credit_link', 'review_person', 'creator_person', 'wikidata_decision'):
    n = con.execute(f"select count(*) from entities.{tbl} where cast(person_id as varchar) in ({','.join(['?'] * len(involved))})", list(involved)).fetchone()[0]
    print(f'loser references in entities.{tbl}: {n}')

# 1. splits
for fp, tp, page, reason in MOVES:
    f, t = full(fp), full(tp)
    e = con.execute("select l.entry_id from entities.person_link l join raw.person_entry r using(entry_id) where l.person_id=? and r.page_id=?", [f, page]).fetchall()
    assert len(e) == 1, (fp, page, e)
    left = con.execute("select count(*) from entities.person_link where person_id=?", [f]).fetchone()[0]
    assert left == 2, (fp, left)
    con.execute("update entities.person_link set person_id=?, match_method='manual_split', match_confidence=1.0 where entry_id=?", [t, e[0][0]])
    con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
                [str(uuid.uuid4()), f, t, disp(f), disp(t), 0.0, 'homonym_split', 'split_manual', 'conflicting_dates', TAG + reason])
    print(f'split: entry {e[0][0]} {fp} -> {tp}')

# 2. candidate statuses (before the tombstones, while both ids are live)
cand = {}
for cid, a, b in con.execute("select candidate_id, person_id_1, person_id_2 from entities.person_candidate where status='pending' and match_reason='ordinal_shift'").fetchall():
    cand[frozenset((str(a), str(b)))] = str(cid)
rejected = {frozenset((full(a), full(b))) for a, b in REJECT}
for key, cid in cand.items():
    con.execute("update entities.person_candidate set status=? where candidate_id=?", ['rejected' if key in rejected else 'confirmed_manual', cid])
BE._log_decided_candidates(con)

# 3. merges
logged = set()
for surv, losers, name, reason in MERGES:
    s = full(surv)
    for lp in losers:
        l = full(lp)
        key = frozenset((s, l))
        assert key not in rejected
        if key not in cand:  # not a queued pair: log it here (queued pairs were logged from person_candidate)
            con.execute("insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)",
                        [str(uuid.uuid4()), s, l, disp(s), disp(l), 1.0, 'manual_review', 'confirmed_manual', 'manual', TAG + reason])
        else:
            logged.add(key)
        con.execute("update entities.person set superseded_by_person_id=? where person_id=?", [s, l])
        if name != 'plain graduate pair':
            print(f'{name}: {lp} -> {surv}')
BE._repoint_all_superseded(con)
BE._refresh_canonical_fields(con)

after = con.execute("select count(*) from entities.person where superseded_by_person_id is null").fetchone()[0]
pend_after = con.execute("select count(*) from entities.person_candidate where status='pending' and match_reason='ordinal_shift'").fetchone()[0]
n_losers = sum(len(ls) for _, ls, _, _ in MERGES)
print('live persons', before, '->', after, f'(expected -{n_losers})')
print('pending ordinal_shift candidates', pend_before, '->', pend_after)
print('queued pairs covered by a merge:', len(logged), 'rejected as pairs:', len(rejected), 'of', len(cand))
unmerged = [k for k in cand if k not in logged and k not in rejected]
print('queued pairs neither merged directly nor rejected (members joined through a third record):', len(unmerged))
for k in unmerged:
    a, b = list(k)
    fa = con.execute("select coalesce(superseded_by_person_id, person_id) from entities.person where person_id=?", [a]).fetchone()[0]
    fb = con.execute("select coalesce(superseded_by_person_id, person_id) from entities.person where person_id=?", [b]).fetchone()[0]
    assert str(fa) == str(fb), (a, b)

# 4. checks
orph = con.execute("select count(*) from entities.person_link pl left join entities.person p using(person_id) where p.person_id is null").fetchone()[0]
print('orphan links:', orph)
# a survivor with two rows in one season, city and artists' section would mean two people were joined
clash = con.execute("""
    select p.display_name, sp.season, sp.city, r.heading_path, count(*) n
    from entities.person p join entities.person_link pl using(person_id)
    join raw.person_entry r using(entry_id) join raw.source_pages sp on sp.page_id = r.page_id
    where cast(p.person_id as varchar) in (%s)
    group by all having count(*) > 1 order by 1, 2""" % ','.join("'%s'" % full(s) for s, _, _, _ in MERGES)).fetchall()
print('same season + city + section more than once on a survivor:', len(clash))
for c in clash:
    print('   ', c)
for surv in sorted({s for s, _, _, _ in MERGES if s not in [p[0] for p in PLAIN]}):
    print('  ', con.execute("select display_name, first_attested_season, last_attested_season, (select count(*) from entities.person_link l where l.person_id=p.person_id) from entities.person p where person_id=?", [full(surv)]).fetchone())
con.close()
print('WRITTEN to', DB)
