"""End-to-end audit of entities.person (RG, 2026-10-12): unconnected records, mis-merges, suspicious names.
Read-only. Writes one CSV per signal into this directory and prints the counts.
A signal is a WORKLIST, never a rule (pre-reform spelling is unstable; ordinals are per-season; lists double up).
usage: uv run python docs/eval/person_audit_2026-10-12/audit.py [--db path]"""
import sys, re, csv, collections, itertools
from pathlib import Path
import duckdb

DB = sys.argv[sys.argv.index('--db') + 1] if '--db' in sys.argv else 'outputs/full_run/imperial_theaters.duckdb'
OUT = Path(__file__).parent
con = duckdb.connect(DB, read_only=True)
SEASONS = [r[0] for r in con.execute("select distinct season from raw.source_pages where season is not null order by 1").fetchall()]
SI = {s: i for i, s in enumerate(SEASONS)}


def fold(s):
    s = (s or '').lower().strip(' .,;:()"«»')
    for a, b in (('ѳ', 'ф'), ('і', 'и'), ('ѣ', 'е'), ('ё', 'е'), ('ѵ', 'и'), ('й', 'и')):
        s = s.replace(a, b)
    s = re.sub(r'[ъь]', '', s)
    s = re.sub(r'(.)\1', r'\1', s)           # doubled letters
    return re.sub(r'[^а-яa-z]', '', s)


def lev(a, b):
    if a == b: return 0
    if abs(len(a) - len(b)) > 3: return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


ORD = re.compile(r'\s*\d+\s*-\s*[йяеao]\w*\.?')
rows = con.execute("""
    select cast(pl.person_id as varchar), p.display_name, pe.entry_id, pe.page_id, sp.season, coalesce(sp.city,''), sp.entity_type,
           pe.heading_path, pe.list_number, pe.family_name, pe.first_name, pe.patronymic, pe.instrument, pe.tenure_note_text
    from entities.person_link pl join entities.person p using(person_id)
    join raw.person_entry pe using(entry_id) join raw.source_pages sp on sp.page_id = pe.page_id
    where p.superseded_by_person_id is null""").fetchall()
starts = collections.defaultdict(set); ends = collections.defaultdict(list)
for eid, sd, ed, et in con.execute("select entry_id, start_date_undate, end_date_undate, end_type from raw.person_entry_service").fetchall():
    if sd: starts[eid].add(sd)
    if ed: ends[eid].append((ed, et))
NONP = set(re.findall(r'"([0-9a-f-]{36})"', Path('pipeline/build_research_model.py').read_text(encoding='utf-8').split('NON_PERSON_IDS = [')[1].split(']')[0]))

P = {}
for pid, disp, eid, page, season, city, et, hp, num, fam, first, pat, instr, note in rows:
    if pid in NONP: continue
    e = P.setdefault(pid, dict(disp=disp, ents=[], fams=collections.Counter(), firsts=collections.Counter(), pats=collections.Counter(),
                               starts=set(), lists=collections.defaultdict(set), seasons=set(), etypes=set(), cities=set()))
    leaf = (hp or '').split(' / ')[-1].strip(' :.')
    e['ents'].append(dict(eid=eid, page=page, season=season, city=city, et=et, leaf=leaf, num=num, fam=fam, first=first, pat=pat, instr=instr, note=note))
    base = ORD.sub('', fam or '')
    e['fams'][fold(base)] += 1
    f1 = first or ''
    if ORD.fullmatch(f1.strip()) or re.fullmatch(r'\d+\s*-\s*\w+', f1.strip()): f1 = ''
    if fold(f1): e['firsts'][fold(f1.split()[0] if f1.split() else f1)] += 1
    if fold(pat): e['pats'][fold(pat)] += 1
    e['starts'] |= starts.get(eid, set())
    e['lists'][(city, et)].add(season); e['seasons'].add(season); e['etypes'].add(et)
    if city: e['cities'].add(city)
for e in P.values():
    e['fam'] = e['fams'].most_common(1)[0][0]
    e['first'] = e['firsts'].most_common(1)[0][0] if e['firsts'] else ''
    e['pat'] = e['pats'].most_common(1)[0][0] if e['pats'] else ''
    e['company'] = {s for (c, et), ss in e['lists'].items() if et != 'Graduates' for s in ss}

decided = set()
for a, b, st in con.execute("select cast(person_id_1 as varchar), cast(person_id_2 as varchar), status from entities.person_merge_log where status='rejected'").fetchall():
    decided.add(frozenset((a, b)))


def span(e):
    ss = sorted(e['seasons']); return f"{ss[0]}..{ss[-1]} ({len(e['ents'])})"


def lists(e):
    return '; '.join(f"{c or '-'}/{et} {min(ss)}..{max(ss)}" for (c, et), ss in sorted(e['lists'].items()))


def same_list_overlap(a, b):
    out = []
    for k in set(a['lists']) & set(b['lists']):
        if k[1] == 'Graduates': continue
        out += sorted(a['lists'][k] & b['lists'][k])
    return out


def write(name, header, data):
    with open(OUT / f'{name}.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(data)
    print(f'{name:32} {len(data):5}')


# ---------------------------------------------------------------- UNCONNECTED
ids = list(P)
by_fam3 = collections.defaultdict(list)          # crude blocking: first 3 folded letters, plus letters 2-4
for pid in ids:
    f = P[pid]['fam']
    for key in {f[:3], f[1:4]}:
        if key: by_fam3[key].append(pid)
pairs = set()
for grp in by_fam3.values():
    for a, b in itertools.combinations(grp, 2):
        pairs.add((a, b) if a < b else (b, a))
by_first_start = collections.defaultdict(list)   # second blocking: same first name + a shared start date
for pid in ids:
    for sd in P[pid]['starts']:
        if P[pid]['first']: by_first_start[(P[pid]['first'], sd)].append(pid)
for grp in by_first_start.values():
    if len(grp) <= 30:
        for a, b in itertools.combinations(grp, 2):
            pairs.add((a, b) if a < b else (b, a))

U = []
for a, b in pairs:
    if frozenset((a, b)) in decided: continue
    A, B = P[a], P[b]
    d = lev(A['fam'], B['fam'])
    if d > 2: continue
    if d and min(len(A['fam']), len(B['fam'])) < 5: continue
    fa, fb, pa, pb = A['first'], B['first'], A['pat'], B['pat']
    first_ok = (fa == fb and fa) or not fa or not fb or lev(fa, fb) <= 1
    pat_ok = pa == pb or not pa or not pb or lev(pa, pb) <= 2
    if not first_ok or not pat_ok: continue
    shared = A['starts'] & B['starts']
    ov = same_list_overlap(A, B)
    same_list = bool({k for k in A['lists'] if k[1] != 'Graduates'} & {k for k in B['lists'] if k[1] != 'Graduates'})
    grad = (A['etypes'] == {'Graduates'}) != (B['etypes'] == {'Graduates'})
    # gap filler: every company season of the smaller record is a season the larger one lacks, inside its span
    small, big = (A, B) if len(A['ents']) <= len(B['ents']) else (B, A)
    gap = False
    if same_list and not ov and big['company'] and small['company']:
        lo, hi = min(SI[s] for s in big['company']), max(SI[s] for s in big['company'])
        gap = all(lo - 1 <= SI[s] <= hi + 1 for s in small['company'])
    score = (3 if shared else 0) + (2 if d == 0 else 0) + (2 if fa == fb and fa else 0) + (2 if pa == pb and pa else 0) + (2 if gap else 0) + (1 if grad else 0) - (3 if ov else 0)
    if not (shared or gap or (d == 0 and fa == fb and fa and pa == pb and pa) or (d == 0 and (not fa or not fb) and same_list)):
        continue
    kind = ('same name + same start date' if shared and d == 0 else 'surname variant + same start date' if shared else
            'fills a gap in the same list' if gap else 'identical name' if d == 0 and fa and fb else 'surname-only record in the same list')
    U.append((score, kind, a[:6], A['disp'], span(A), lists(A), b[:6], B['disp'], span(B), lists(B), ';'.join(sorted(shared)), ';'.join(ov)))
U.sort(key=lambda r: (-r[0], r[3]))
write('U_unconnected_pairs', ['score', 'kind', 'id_1', 'person_1', 'span_1', 'lists_1', 'id_2', 'person_2', 'span_2', 'lists_2', 'shared_start', 'same_list_overlap'], U)
print('   by kind:', dict(collections.Counter(r[1] for r in U)))

# graduates with no company record at all
G = []
for pid, e in P.items():
    if e['etypes'] == {'Graduates'}:
        en = e['ents'][0]
        G.append((pid[:6], e['disp'], en['season'], en['page'], en['leaf'], ';'.join(sorted(e['starts']))))
G.sort(key=lambda r: (r[2], r[1]))
write('G_graduate_only_records', ['id', 'person', 'season', 'page', 'heading', 'start'], G)

# ---------------------------------------------------------------- MIS-MERGES
M1, M2, M3, M4, M5, M6, M7 = [], [], [], [], [], [], []
for pid, e in P.items():
    k = collections.defaultdict(list)
    for en in e['ents']:
        k[(en['season'], en['city'], en['et'], en['leaf'])].append(en)
    for key, lst in k.items():
        if len(lst) > 1:
            M1.append((pid[:6], e['disp'], *key, len(lst), ' | '.join(f"{x['page']} {x['num'] or ''} {x['fam']} {x['first'] or ''} {x['pat'] or ''}" for x in lst)))
    pats = [p for p, n in e['pats'].items()]
    far = [(x, y) for x, y in itertools.combinations(pats, 2) if lev(x, y) > 2]
    if far:
        M2.append((pid[:6], e['disp'], span(e), lists(e), '; '.join(f'{p} x{n}' for p, n in e['pats'].most_common())))
    fs = list(e['firsts'])
    farf = [(x, y) for x, y in itertools.combinations(fs, 2) if lev(x, y) > 2 and not (x.startswith(y) or y.startswith(x))]
    if farf:
        M3.append((pid[:6], e['disp'], span(e), lists(e), '; '.join(f'{p} x{n}' for p, n in e['firsts'].most_common())))
    fam_far = [(x, y) for x, y in itertools.combinations(list(e['fams']), 2) if lev(x, y) > 2]
    if fam_far:
        M4.append((pid[:6], e['disp'], span(e), lists(e), '; '.join(f'{p} x{n}' for p, n in e['fams'].most_common())))
    bys = collections.defaultdict(set)
    for en in e['ents']:
        if en['city']: bys[(en['season'], en['et'])].add(en['city'])
    both = sorted(s for (s, et), cs in bys.items() if len(cs) > 1)
    if both:
        M5.append((pid[:6], e['disp'], span(e), lists(e), ';'.join(both)))
    g = set()
    for f in e['fams']:
        if re.search(r'(ова|ева|ина|ына|ская|цкая|ая)$', f): g.add('f')
        elif re.search(r'(ов|ев|ин|ын|скии|цкии|ии|ои)$', f): g.add('m')
    if len(g) > 1:
        M6.append((pid[:6], e['disp'], span(e), lists(e), '; '.join(f'{p} x{n}' for p, n in e['fams'].most_common())))
    if e['company']:
        idx = sorted(SI[s] for s in e['company'])
        gaps = [(SEASONS[x], SEASONS[y]) for x, y in zip(idx, idx[1:]) if y - x >= 4]
        if gaps:
            M7.append((pid[:6], e['disp'], span(e), lists(e), '; '.join(f'{a} -> {b}' for a, b in gaps)))
write('M1_two_rows_same_list_season', ['id', 'person', 'season', 'city', 'list', 'heading', 'n', 'rows'], sorted(M1, key=lambda r: (r[1], r[2])))
write('M2_conflicting_patronymics', ['id', 'person', 'span', 'lists', 'patronymics'], sorted(M2, key=lambda r: r[1]))
write('M3_conflicting_first_names', ['id', 'person', 'span', 'lists', 'first_names'], sorted(M3, key=lambda r: r[1]))
write('M4_conflicting_surnames', ['id', 'person', 'span', 'lists', 'surnames'], sorted(M4, key=lambda r: r[1]))
write('M5_both_cities_one_season', ['id', 'person', 'span', 'lists', 'seasons'], sorted(M5, key=lambda r: r[1]))
write('M6_gender_conflict', ['id', 'person', 'span', 'lists', 'surnames'], sorted(M6, key=lambda r: r[1]))
write('M7_gap_of_4plus_seasons', ['id', 'person', 'span', 'lists', 'gaps'], sorted(M7, key=lambda r: r[1]))

# start-date conflicts inside one list type
M8 = []
for pid, e in P.items():
    per = collections.defaultdict(collections.Counter)
    for en in e['ents']:
        s = sorted(starts.get(en['eid'], ()))
        if s: per[en['et']][s[0]] += 1
    for et, c in per.items():
        if len(c) > 1:
            years = {d[:4] for d in c}
            M8.append((pid[:6], e['disp'], et, span(e), '; '.join(f'{d} x{n}' for d, n in c.most_common()), 'different years' if len(years) > 1 else 'same year'))
write('M8_first_start_date_varies', ['id', 'person', 'list', 'span', 'first_period_start_dates', 'kind'], sorted(M8, key=lambda r: (r[5], r[1])))

# listed after a printed leaving / death date
M9 = []
for pid, e in P.items():
    for en in e['ents']:
        for ed, et in ends.get(en['eid'], ()):
            if et in ('left service', 'died') and len(ed) >= 4:
                y = int(ed[:4]); m = int(ed[5:7]) if len(ed) >= 7 else 6
                last_ok = f"{y if m >= 7 else y - 1}-{str((y + 1 if m >= 7 else y) % 100).zfill(2)}"
                if last_ok in SI:
                    later = sorted(s for s in e['company'] if SI[s] > SI[last_ok] + 0 and (en['city'], en['et']) in e['lists'] and s in e['lists'][(en['city'], en['et'])])
                    if later:
                        M9.append((pid[:6], e['disp'], en['et'], en['city'], en['season'], et, ed, ';'.join(later)))
M9 = sorted(set(M9), key=lambda r: r[1])
write('M9_listed_after_leaving_or_death', ['id', 'person', 'list', 'city', 'note_in_season', 'end_type', 'end_date', 'same_list_seasons_after'], M9)

# ---------------------------------------------------------------- SUSPICIOUS NAMES
S = []
LAT = re.compile(r'[A-Za-z]')
for pid, e in P.items():
    for en in e['ents']:
        fam, first, pat = en['fam'] or '', en['first'] or '', en['pat'] or ''
        why = []
        if any(LAT.search(x) and re.search(r'[А-Яа-яѢѣІіѲѳ]', x) for x in (fam, first, pat)): why.append('Latin letter inside a Cyrillic name')
        if re.search(r'\d', first) or re.search(r'\d', pat): why.append('ordinal or digit in first name / patronymic')
        if re.search(r'[()"«»\[\]]', fam + first + pat): why.append('bracket or quote in a name field')
        if re.search(r'[а-яѣіѳ][А-ЯѢІѲ]', fam + ' ' + first + ' ' + pat): why.append('two words glued together')
        if pat and not re.search(r'(ичъ|ична|вна|шна|ичь|ич|инична|овъ|евъ)\.?$', pat.strip()) and not re.search(r'[A-Za-z]', pat) and en['et'] != 'Graduates': why.append('patronymic field does not look like a patronymic')
        if first and len(first.split()) > 1 and not re.search(r'-', first): why.append('first-name field holds two words')
        if fam and re.search(r'[.,;:]$', fam.strip()): why.append('punctuation left on the surname')
        if fam and fam[0].islower(): why.append('surname starts lower-case')
        if not first.strip() and en['et'] not in ('Graduates',): why.append('no first name')
        if re.search(r'(службу|умеръ|умерла|переведен|назначен|см\.)', fam + ' ' + first + ' ' + pat, re.I): why.append('note text in a name field')
        for w in why:
            S.append((w, pid[:6], e['disp'], en['season'], en['page'], en['num'] or '', fam, first, pat))
S.sort(key=lambda r: (r[0], r[2], r[3]))
write('S_suspicious_name_fields', ['signal', 'id', 'person', 'season', 'page', 'no', 'family_name', 'first_name', 'patronymic'], S)
print('   by signal:', dict(collections.Counter(r[0] for r in S)))
single = [(pid[:6], e['disp'], e['ents'][0]['season'], e['ents'][0]['page'], e['ents'][0]['et'], e['ents'][0]['city']) for pid, e in P.items() if len(e['ents']) == 1 and e['etypes'] != {'Graduates'}]
write('X_single_entry_company_records', ['id', 'person', 'season', 'page', 'list', 'city'], sorted(single, key=lambda r: (r[4], r[5], r[2], r[1])))
print('live persons audited:', len(P))

# ---------------------------------------------------------------- sharper mis-merge signals (added after the first pass)
# M10: inside ONE list type, two start dates of different years that are both printed in the same season --
# two simultaneous careers on one record (how Никитинъ, Алексѣй Никитичъ's 2026-10-05 split came undone).
M10 = []
for pid, e in P.items():
    per = collections.defaultdict(lambda: collections.defaultdict(set))     # et -> start -> seasons
    where = collections.defaultdict(set)
    for en in e['ents']:
        s = sorted(starts.get(en['eid'], ()))
        if s:
            per[en['et']][s[0]].add(en['season']); where[(en['et'], s[0])].add(f"{en['city'] or '-'}:{en['leaf'][:18]}:{(en['instr'] or '')[:14]}")
    for et, d in per.items():
        for (a, sa), (b, sb) in itertools.combinations(d.items(), 2):
            if a[:4] != b[:4] and sa & sb:
                M10.append((pid[:6], e['disp'], et, a, len(sa), ' / '.join(sorted(where[(et, a)]))[:70], b, len(sb), ' / '.join(sorted(where[(et, b)]))[:70], ';'.join(sorted(sa & sb))))
write('M10_two_start_dates_same_season', ['id', 'person', 'list', 'start_a', 'n_a', 'where_a', 'start_b', 'n_b', 'where_b', 'seasons_with_both'], sorted(M10, key=lambda r: r[1]))
# M11: a musician with two unrelated instruments
FAM = [('string', r'скрипк|альт|віолонч|контрабас|арф'), ('wood', r'флейт|гобо|кларнет|фагот|рожок'), ('brass', r'валторн|труб|тромбон|туб|корнет'), ('perc', r'литавр|удар|барабан|тарелк|треугол'), ('keys', r'орган|фортеп|челест|піан')]
M11 = []
for pid, e in P.items():
    c = collections.Counter()
    for en in e['ents']:
        if en['et'] == 'Musicians' and en['instr']:
            for name, rx in FAM:
                if re.search(rx, en['instr'].lower()): c[name] += 1
    if len(c) > 1:
        M11.append((pid[:6], e['disp'], span(e), lists(e), '; '.join(f'{k} x{v}' for k, v in c.most_common()),
                    '; '.join(sorted({(en['instr'] or '') for en in e['ents'] if en['instr']}))[:120]))
write('M11_two_instrument_families', ['id', 'person', 'span', 'lists', 'families', 'instruments'], sorted(M11, key=lambda r: r[1]))
