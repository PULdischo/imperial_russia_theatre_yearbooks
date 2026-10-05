import duckdb, re, json, difflib, collections, sys
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
rows = con.execute("""
select cast(l.person_id as varchar) pid, l.entry_id, e.entity_type, sp.season, sp.city,
       a.family_name_clean fam, a.first_name_clean fn, a.patronymic_clean pat, e.rank_or_title, e.heading_path, e.tenure_note_text,
       p.display_name, l.match_method
from entities.person_link l
join entities.person p on p.person_id = l.person_id and p.superseded_by_person_id is null
join raw.person_entry e on e.entry_id = l.entry_id
join analysis.person_entry a on a.entry_id = l.entry_id
join raw.source_pages sp on sp.page_id = e.page_id
""").fetchall()
svc = collections.defaultdict(list)
for eid, so, sd, eu, et in con.execute("select entry_id, period_order, start_date_undate, end_date_undate, end_type from raw.person_entry_service order by 1,2").fetchall():
    svc[eid].append((sd, eu, et))

def norm(s):
    s = (s or '').lower()
    for a, b in (('ѳ', 'ф'), ('і', 'и'), ('ѣ', 'е'), ('э', 'е'), ('ё', 'е'), ('ъ', ''), ('ь', ''), ('й', 'и'), ('ы', 'и'), ('я', 'а'), ('ю', 'у')):
        s = s.replace(a, b)
    s = re.sub(r'[^а-яa-z]', '', s)
    s = re.sub(r'(.)\1', r'\1', s)       # doubled letters
    return s
def stem(s):
    s = norm(s)
    s = re.sub(r'(ич|вич|евич|овна|евна|ична|инична|ович|овн|евн|ичн)$', '', s)
    return s
def sim(a, b): return difflib.SequenceMatcher(None, a, b).ratio()
def seas_year(s): return int(s[:4])

by = collections.defaultdict(list)
for r in rows: by[r[0]].append(r)
out = []
for pid, es in by.items():
    sig = {}
    # S1 patronymic conflict
    pats = collections.Counter(stem(e[7]) for e in es if e[7] and stem(e[7]))
    keys = list(pats)
    worst = 1.0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            worst = min(worst, sim(keys[i], keys[j]))
    if len(keys) >= 2 and worst < 0.80:
        sig['PATRONYMIC'] = (round(worst, 2), dict(collections.Counter(e[7] for e in es if e[7])))
    # S5 first-name conflict
    fns = collections.Counter(stem(e[6]) for e in es if e[6] and stem(e[6]))
    keys = list(fns); worst = 1.0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)): worst = min(worst, sim(keys[i], keys[j]))
    if len(keys) >= 2 and worst < 0.75:
        sig['FIRSTNAME'] = (round(worst, 2), dict(collections.Counter(e[6] for e in es if e[6])))
    # S2 start-date conflict (distinct first-period start dates, years differing >= 2)
    starts = collections.defaultdict(list)
    for e in es:
        for sd, eu, et in svc.get(e[1], [])[:1]:
            if sd: starts[sd].append(e[3])
    ys = sorted({int(d[:4]) for d in starts})
    if len(ys) >= 2 and ys[-1] - ys[0] >= 2:
        sig['STARTDATE'] = ({d: sorted(set(s))[:2] for d, s in starts.items()},)
    # S3 entry after recorded end (died / left) by > 1 season
    ends = []
    for e in es:
        for sd, eu, et in svc.get(e[1], []):
            if eu and et in ('died', 'left service'): ends.append((eu, et, e[3]))
    if ends:
        first_end = min(ends)
        later = sorted({e[3] for e in es if seas_year(e[3]) > int(first_end[0][:4]) + 1})
        if later and first_end[1] in ('died', 'left service'):
            sig['AFTER_END'] = (first_end[0], first_end[1], later[:4])
    # S4 same season, same entity type, different city
    sc = collections.defaultdict(set)
    for e in es:
        if e[4]: sc[(e[3], e[2])].add(e[4])
    sim_city = [k for k, v in sc.items() if len(v) >= 2]
    if sim_city: sig['TWO_CITIES_SAME_SEASON'] = (sim_city[:3],)
    if sig:
        out.append((pid, es[0][11], len(es), sorted({e[2] for e in es}), sig))
json.dump(out, open('/tmp/homonym/scan.json', 'w'), ensure_ascii=False, default=str, indent=1)
print(len(by), 'live persons with entries;', len(out), 'flagged')
cnt = collections.Counter(k for o in out for k in o[4]); print(cnt)
multi = [o for o in out if len(o[4]) >= 2]; print(len(multi), 'with >=2 signals')
