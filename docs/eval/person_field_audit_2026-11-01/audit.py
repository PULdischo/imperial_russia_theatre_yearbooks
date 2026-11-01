"""Field-level audit of every person (RG, 2026-11-01): anything parsed wrongly, in the wrong field, missing or wrong.
Covers roster rows (all six lists), research.person, ballet-production-list creators, review credits,
jubilee/obituary person links and Wikidata links. Read-only. One CSV per check in this directory.
A flag is a WORKLIST, never a verdict: pre-reform spelling is unstable and the print has its own slips.
The 2026-10-12 / 10-19 audits covered identity (duplicates, mis-merges, start dates, leaving notes); this one
looks at the fields.
usage: uv run python docs/eval/person_field_audit_2026-11-01/audit.py [--db path] [--no-wikidata]"""
import sys, re, csv, json, collections, urllib.request, urllib.parse
from pathlib import Path
import duckdb

DB = sys.argv[sys.argv.index('--db') + 1] if '--db' in sys.argv else 'outputs/full_run/imperial_theaters.duckdb'
OUT = Path(__file__).parent
con = duckdb.connect(DB, read_only=True)
Q = lambda sql: con.execute(sql).fetchall()
COUNTS = {}

CYR = r'А-Яа-яЁёѢѣІіѲѳѴѵ'
FEM_PAT = re.compile(r'(вна|ична|инична|шна)\.?$')
MAL_PAT = re.compile(r'(вичъ|ичъ|вич|ичь|ьичъ)\.?$')
ORD = re.compile(r'\s*\d+\s*-\s*[йяеао]\w*\.?\s*$')


def fold(s):
    s = (s or '').lower().strip(' .,;:()"«»')
    for a, b in (('ѳ', 'ф'), ('і', 'и'), ('ѣ', 'е'), ('ё', 'е'), ('ѵ', 'и'), ('й', 'и')):
        s = s.replace(a, b)
    s = re.sub(r'[ъь]', '', s)
    s = re.sub(r'(.)\1', r'\1', s)
    return re.sub(r'[^а-яa-z-]', '', s)


def stem(s):
    """Fold, then drop Russian case endings so «Ивановымъ» meets «Ивановъ», «Горскаго» meets «Горскій»."""
    f = fold(s)
    for end in ('ыми', 'ыму', 'ымъ', 'ым', 'ого', 'аго', 'ему', 'ому', 'ою', 'ой', 'ая', 'ую', 'ии', 'ии', 'ии', 'ии',
                'ого', 'ых', 'ой', 'им', 'ым', 'ую', 'ы', 'а', 'у', 'е', 'и', 'о', 'я', 'ю'):
        if len(f) - len(end) >= 3 and f.endswith(end):
            return f[:-len(end)]
    return f


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


def same_surname(a, b):
    sa, sb = stem(ORD.sub('', a or '')), stem(ORD.sub('', b or ''))
    if not sa or not sb: return True
    if sa == sb or sa.startswith(sb) or sb.startswith(sa): return True
    return lev(sa, sb) <= 1


def write(name, header, rows, note=''):
    rows = list(rows)
    with open(OUT / f'{name}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    COUNTS[name] = (len(rows), note)


def syear(season):
    return int(season[:4])


# =============================================================== ROSTER ROWS
rows = Q("""
    select pe.entry_id, pe.page_id, sp.season, coalesce(sp.city,'') city, pe.entity_type, sp.printed_page_number,
           pe.heading_path, pe.list_number, pe.family_name, pe.first_name, pe.patronymic, pe.rank_or_title,
           pe.service_class, pe.instrument, pe.subject_taught, pe.tenure_note_text, pe.credit_summary_text,
           cast(pl.person_id as varchar), p.display_name, sp.source_page_index
    from raw.person_entry pe join raw.source_pages sp using(page_id)
    left join entities.person_link pl using(entry_id)
    left join entities.person p on p.person_id = pl.person_id""")
R = [dict(zip(['eid', 'page', 'season', 'city', 'et', 'ppn', 'hp', 'num', 'fam', 'first', 'pat', 'rank', 'scls', 'instr',
               'subj', 'note', 'credit', 'pid', 'disp', 'pidx'], r)) for r in rows]
svc = collections.defaultdict(list)
for eid, order, sdt, sd, edt, ed, et in Q("select entry_id, period_order, start_date_text, start_date_undate, end_date_text, end_date_undate, end_type from raw.person_entry_service order by entry_id, period_order"):
    svc[eid].append(dict(sdt=sdt, sd=sd, edt=edt, ed=ed, et=et))
credits_n = collections.Counter(r[0] for r in Q("select entry_id from raw.person_entry_credit"))

base = lambda r: (r['eid'], r['page'], r['season'], r['city'], r['et'], r['ppn'] or '', r['num'] or '', r['fam'] or '', r['first'] or '', r['pat'] or '', r['disp'] or '')
BH = ['entry_id', 'page_id', 'season', 'city', 'list', 'printed_page', 'no', 'family_name', 'first_name', 'patronymic', 'person']

# vocabularies (raw fields, corpus-wide)
first_ct = collections.Counter(fold(r['first']) for r in R if r['first'] and not ORD.fullmatch(r['first']))
pat_ct = collections.Counter(fold(r['pat']) for r in R if r['pat'])
first_gender = collections.defaultdict(collections.Counter)
for r in R:
    if r['first'] and r['pat']:
        g = 'f' if FEM_PAT.search(r['pat']) else 'm' if MAL_PAT.search(r['pat']) else None
        if g: first_gender[fold(r['first'])][g] += 1


def gender_of_first(f):
    c = first_gender.get(fold(f))
    if not c or sum(c.values()) < 4: return None
    g, n = c.most_common(1)[0]
    return g if n / sum(c.values()) >= 0.95 else None


# ---- R1 name-field placement / shape
R1 = []
_pp = collections.defaultdict(lambda: {'pat': 0, 'first': 0})
for r in R:
    if r['pid']:
        if r['pat']: _pp[r['pid']]['pat'] += 1
        if r['first'] and len(r['first'].split()) == 1: _pp[r['pid']]['first'] += 1
for r in R:
    fam, first, pat = (r['fam'] or ''), (r['first'] or ''), (r['pat'] or '')
    why = []
    if any(re.search(r'[A-Za-z]', x) and re.search(f'[{CYR}]', x) for x in (fam, first, pat)): why.append('Latin letter inside a Cyrillic name')
    if re.search(r'\d', first) or re.search(r'\d', pat): why.append('ordinal or digit in first name / patronymic')
    if re.search(r'\d', ORD.sub('', fam)): why.append('digit in surname (not an ordinal)')
    if re.search(r'[()"«»\[\]]', fam + first + pat): why.append('bracket or quote in a name field')
    if re.search(r'[а-яѣіѳ][А-ЯѢІѲ]', fam + ' ' + first + ' ' + pat): why.append('two words glued together')
    if pat and not re.search(r'(ичъ|ична|вна|шна|ичь|ич|инична)\.?$', pat.strip()) and not re.search(r'[A-Za-z]', pat) and not re.fullmatch(rf'[{CYR}]\.', pat.strip()):
        why.append('patronymic field does not look like a patronymic')
    two = first.split()
    if len(two) == 2 and (FEM_PAT.search(two[1]) or MAL_PAT.search(two[1])) and not pat: why.append('first name + patronymic both in first-name field')
    elif first and len(two) > 1 and '-' not in first: why.append('first-name field holds two words')
    if re.search(r',\s*\S', fam): why.append('first name inside surname field («Surname, Name.»)')
    elif fam and len(ORD.sub('', fam).split()) > 1 and '(' not in fam and '-' not in fam and not re.search(r'\b(фонъ|де|ди|дю|ла|ле|ванъ|фанъ|дель|делла)\b', fam, re.I):
        why.append('surname field holds two words')
    if fam and re.search(r'[.,;:]$', fam.strip()): why.append('punctuation left on the surname')
    if first and re.search(r'[,;:]$', first.strip()): why.append('punctuation left on the first name')
    if fam and fam.strip()[:1].islower(): why.append('surname starts lower-case')
    if first and first.strip()[:1].islower(): why.append('first name starts lower-case')
    if not fam.strip(): why.append('no surname')
    if not first.strip() and r['et'] != 'Graduates' and 'см.' not in (r['note'] or ''): why.append('no first name' + (', printed in other seasons' if r['pid'] and _pp[r['pid']]['first'] else ''))
    if not first.strip() and r['et'] == 'Graduates' and not re.search(r',', fam): why.append('graduate with no first name')
    if not pat.strip() and len(two) == 1 and r['et'] not in ('Graduates',) and r['pid'] and _pp[r['pid']]['pat'] >= 1: why.append('patronymic missing here, printed in other seasons')
    if re.search(r'(служб|умеръ|умерла|переведен|назначен|см\.|\bсъ \d+ \w+)', ORD.sub('', fam) + ' ' + first + ' ' + pat, re.I): why.append('note text in a name field')
    if len(two) == 1 and (FEM_PAT.search(first) or MAL_PAT.search(first)): why.append('first-name field looks like a patronymic')
    if pat and fold(pat) in first_ct and first_ct[fold(pat)] >= 5 and not FEM_PAT.search(pat) and not MAL_PAT.search(pat): why.append('patronymic field holds a first name')
    for w in why: R1.append((w,) + base(r))
R1.sort(key=lambda x: (x[0], x[3], x[2]))
write('R1_name_field_shape', ['signal'] + BH, R1, 'name parts in the wrong field, stray punctuation/ordinals/notes, missing parts')

# ---- R2 gender conflict inside one row
R2 = []
for r in R:
    first, pat, fam = r['first'] or '', r['pat'] or '', ORD.sub('', r['fam'] or '').strip()
    pg = 'f' if FEM_PAT.search(pat) else 'm' if MAL_PAT.search(pat) else None
    fg = gender_of_first(first) if first else None
    sg = 'f' if re.search(r'(ова|ева|ина|ына|ская|цкая|ая)$', fam) else 'm' if re.search(r'(овъ|евъ|инъ|ынъ|скій|цкій|ой)$', fam) else None
    gs = {k: v for k, v in (('patronymic', pg), ('first name', fg), ('surname', sg)) if v}
    if len(set(gs.values())) > 1:
        R2.append((' / '.join(f'{k}={v}' for k, v in gs.items()),) + base(r))
write('R2_gender_conflict_in_row', ['genders'] + BH, sorted(R2, key=lambda x: x[2]), 'surname, first name and patronymic disagree on gender')

# ---- R3 rare spelling beside a common near-identical one (possible misread)
R3 = []
fam_ct = collections.Counter(fold(ORD.sub('', r['fam'] or '')) for r in R if r['fam'])
for field, ct in (('first', first_ct), ('pat', pat_ct)):
    common = [w for w, n in ct.items() if n >= 10 and len(w) >= 4]
    for r in R:
        v = r[field]
        if not v or ORD.fullmatch(v): continue
        fv = fold(v)
        if ct[fv] > 2 or len(fv) < 4: continue
        near = sorted((ct[w], w) for w in common if w != fv and lev(fv, w) == 1)
        if near:
            R3.append((field.replace('first', 'first_name').replace('pat', 'patronymic'), v, ct[fv], near[-1][1], near[-1][0]) + base(r))
# surname: one-off spelling inside a person whose other appearances agree
byp = collections.defaultdict(list)
for r in R:
    if r['pid']: byp[r['pid']].append(r)
for pid, rs in byp.items():
    c = collections.Counter(fold(ORD.sub('', x['fam'] or '')) for x in rs)
    if len(c) < 2: continue
    top, n = c.most_common(1)[0]
    if n < 3: continue
    for x in rs:
        fv = fold(ORD.sub('', x['fam'] or ''))
        if fv != top and c[fv] == 1 and lev(fv, top) <= 2:
            R3.append(('family_name (within person)', x['fam'], 1, top, n) + base(x))
    for field in ('first', 'pat'):
        c2 = collections.Counter(fold(x[field]) for x in rs if x[field] and not ORD.fullmatch(x[field]))
        if len(c2) < 2: continue
        top2, n2 = c2.most_common(1)[0]
        if n2 < 3: continue
        for x in rs:
            v = x[field]
            if not v or ORD.fullmatch(v): continue
            fv = fold(v)
            if fv != top2 and c2[fv] == 1:
                R3.append((('first_name' if field == 'first' else 'patronymic') + ' (within person)', v, 1, top2, n2) + base(x))
write('R3_one_off_spelling', ['field', 'value', 'value_count', 'common_neighbour', 'neighbour_count'] + BH,
      sorted(set(R3), key=lambda x: (x[0], x[8], x[7])), 'a spelling seen once/twice next to a common near-identical one: misread or genuine variant')

# ---- R4 content in the wrong column / missing column content
R4 = []
INSTR = re.compile(r'(скрипк|альт|віолончел|виолончел|контрабас|флейт|гобо|кларнет|фагот|валторн|вальдгорн|труб|тромбон|туба|литавр|арф|барабан|тарелк|піанист|пианист|органист|библіотекар|библиотекар|инспектор оркестр)', re.I)
for r in R:
    et = r['et']; why = []
    if r['instr'] and et != 'Musicians': why.append(('instrument filled outside Musicians', r['instr']))
    if r['subj'] and et != 'TheaterSchoolStaff': why.append(('subject_taught filled outside TheaterSchoolStaff', r['subj']))
    if et == 'Musicians' and not r['instr'] and re.search(r'(Музыкант|оркестр)', r['hp'] or '', re.I) and not re.search(r'(Капельмейстер|Дирижер|Дирижёр|Инспектор|Библіотек|Концертмейстер)', (r['hp'] or '') + (r['rank'] or ''), re.I):
        why.append(('Musicians row with no instrument', r['hp'] or ''))
    for f in ('fam', 'first', 'pat'):
        if r[f] and INSTR.search(r[f]): why.append((f'instrument word in {f}', r[f]))
    if r['note'] and INSTR.search(r['note']) and et == 'Musicians' and not r['instr']: why.append(('instrument word only in tenure note', r['note']))
    if r['rank'] and re.search(r'(съ \d|\d{4})', r['rank']): why.append(('date in rank_or_title', r['rank']))
    if r['rank'] and re.search(r'(разъ|балет|опер)', r['rank']) and et == 'BalletArtists': why.append(('credit text in rank_or_title', r['rank']))
    if r['note'] and re.search(r'(Въ \d+ балет|Всего)', r['note']): why.append(('credit summary inside tenure note', r['note']))
    if r['credit'] and re.search(r'съ \d+ \w+ \d{4}', r['credit']) and not re.search(r'(службу|переведен|назначен)', r['credit']): why.append(('start date inside credit summary', r['credit']))
    if r['scls'] and r['scls'] not in ('1', '2', '3', '4', '5', '6', '7', '8') and not re.fullmatch(r'[\dIVX]+\s*\w*\.?\s*\w*\.?', r['scls']): why.append(('unusual service_class', r['scls']))
    for w, v in why: R4.append((w, v) + base(r))
write('R4_wrong_or_missing_column', ['signal', 'value'] + BH, sorted(R4, key=lambda x: (x[0], x[4], x[3])), 'content sitting in the wrong column, or a column that should be filled and is not')

# ---- R5 tenure text vs parsed service periods
R5 = []
for r in R:
    note = r['note'] or ''; ps = svc.get(r['eid'], []); sy = syear(r['season'])
    full = note + ' ' + (r['credit'] or '')
    MONTHS = 'января февраля марта апрѣля мая іюня іюля августа сентября октября ноября декабря'.split()
    for m in re.finditer(r'(?:Оставил[аъ]? службу|†|Умер(?:ъ|ла))\s*(\d{1,2})\s+(\w+)\s+(\d{4})', full):
        d, mon, y = m.groups()
        iso = f"{y}-{MONTHS.index(mon) + 1:02d}-{int(d):02d}" if mon in MONTHS else None
        if not iso: R5.append(('leaving/death month word not recognised', m.group(0)) + base(r))
        elif not any(str(p['ed']) == iso for p in ps): R5.append(('printed leaving/death date not among parsed end dates', f"{m.group(0)} | parsed: {[str(p['ed']) for p in ps]}") + base(r))
    if re.search(r'(Оставил[аъ]? службу.*){2}', full): R5.append(('leaving note printed twice in one entry', full) + base(r))
    for w in re.findall(r'съ\s+\d{1,2}\s+([а-яѣі]+)', full):
        if w not in MONTHS and w not in ('по',): R5.append(('unknown month word after «съ»', w + ' | ' + full[:90]) + base(r))
    years = [int(y) for y in re.findall(r'(1[78]\d\d|19[01]\d)', note)]
    why = []
    if years and not ps: why.append(('note has a year but no service period was parsed', note))
    if re.search(r'съ\s+\d', note) and not any(p['sd'] for p in ps): why.append(('note has «съ <date>» but no start date parsed', note))
    for p in ps:
        if p['sd']:
            y = int(str(p['sd'])[:4])
            if y < 1820: why.append(('start year before 1820', f"{p['sdt']} -> {p['sd']}"))
            if y > sy + 1: why.append(('start date after the season', f"{p['sdt']} -> {p['sd']}"))
            if p['sdt'] and not re.search(str(y), p['sdt'] or '') and re.search(r'\d{4}', p['sdt'] or ''): why.append(('parsed start year not in its own text', f"{p['sdt']} -> {p['sd']}"))
            if str(y) not in note and note and re.search(r'\d{4}', note): why.append(('parsed start year not in the tenure note', f"{p['sd']} | {note}"))
        if p['ed']:
            y2 = int(str(p['ed'])[:4])
            if p['sd'] and str(p['ed']) < str(p['sd']): why.append(('end before start', f"{p['sd']} .. {p['ed']}"))
            if y2 > sy + 2: why.append(('end date long after the season', f"{p['edt']} -> {p['ed']}"))
    if re.search(r'(†|умеръ|умерла|скончал)', full) and not any(p['et'] == 'died' for p in ps): why.append(('death in note but no died period', note))
    if re.search(r'(Оставил|оставил|Уволен|уволен)', full) and not any(p['et'] in ('left service', 'other') for p in ps): why.append(('leaving in note but no end parsed', note))
    nper = len(re.findall(r'съ\s+\d', note))
    if nper > len([p for p in ps if p['sd']]): why.append((f'{nper} «съ» in note, {len([p for p in ps if p["sd"]])} start dates parsed', note))
    for w, v in why: R5.append((w, v) + base(r))
write('R5_tenure_parse', ['signal', 'value'] + BH, sorted(R5, key=lambda x: (x[0], x[4], x[3])), 'tenure note vs the service periods parsed from it')

# ---- R6 numbering gaps / duplicates (missed or doubled people)
R6 = []
bylist = collections.defaultdict(list)
for r in R:
    bylist[(r['season'], r['city'], r['et'], r['hp'] or '')].append(r)
for k, rs in bylist.items():
    rs.sort(key=lambda x: (x['pidx'] or 0, x['eid']))
    nums = []
    for x in rs:
        m = re.match(r'^\s*(\d+)', x['num'] or '')
        nums.append(int(m.group(1)) if m else None)
    seq = [(n, x) for n, x in zip(nums, rs) if n is not None]
    for (a, xa), (b, xb) in zip(seq, seq[1:]):
        if b == a: R6.append(('duplicate number', f'{a} twice', xb['eid'], xa['eid']) + base(xb))
        elif b > a + 1: R6.append(('gap in numbering', f'{a} -> {b} (missing {b - a - 1})', xb['eid'], xa['eid']) + base(xb))
        elif b < a and b != 1: R6.append(('numbering goes backwards', f'{a} -> {b}', xb['eid'], xa['eid']) + base(xb))
    if seq and seq[0][0] not in (1,) and not any(o[0] == k[0] and o[1] == k[1] and o[2] == k[2] and o[3] != k[3] for o in bylist):
        R6.append(('list does not start at 1', f'starts {seq[0][0]}', seq[0][1]['eid'], '') + base(seq[0][1]))
write('R6_numbering', ['signal', 'detail', 'entry_id_at', 'entry_id_before'] + BH, sorted(R6, key=lambda x: (x[0], x[6], x[5])),
      'printed list numbers that skip (a person dropped?) or repeat (a person doubled?), per season/city/list/heading')

# ---- R7 missing credit summary where the rest of the page has one (BalletArtists)
R7 = []
bypage = collections.defaultdict(list)
for r in R:
    if r['et'] == 'BalletArtists': bypage[r['page']].append(r)
for page, rs in bypage.items():
    have = [x for x in rs if x['credit']]
    if len(rs) >= 4 and len(have) / len(rs) >= 0.7:
        for x in rs:
            if not x['credit']: R7.append(('no credit summary on a page where others have one', f'{len(have)}/{len(rs)}') + base(x))
    for x in have:
        if credits_n[x['eid']] == 0: R7.append(('credit summary text but no credit rows parsed', x['credit']) + base(x))
write('R7_credit_summary', ['signal', 'value'] + BH, R7, 'BalletArtists performance tallies missing or unparsed')

# ---- R8 unlinked roster rows
R8 = [base(r) for r in R if not r['pid']]
write('R8_rows_without_person', BH, R8, 'roster rows with no person_link')

# =============================================================== research.person
P = Q("""select cast(person_id as varchar), display_name, canonical_family_name, canonical_first_name, canonical_patronymic,
                ordinal_suffix, first_attested_season, last_attested_season, wikidata_qid, wikidata_label, wikidata_description, person_source
         from research.person""")
app = collections.defaultdict(set)
for pid, s in Q("select cast(person_id as varchar), season from research.person_appearance"): app[pid].add(s)
pc = collections.Counter(r[0] for r in Q("select cast(person_id as varchar) from research.production_credit where person_id is not null"))
rc = collections.Counter(r[0] for r in Q("select cast(person_id as varchar) from research.review_credit where person_id is not null"))
P1 = []
for pid, disp, fam, first, pat, ordn, fa, la, qid, ql, qd, src in P:
    why = []
    if re.search(r'[()"«»\[\]⁂*]', disp or ''): why.append('bracket, quote or symbol in display name')
    if re.search(r'\d', re.sub(r'\d+-[йяе]', '', disp or '')): why.append('digit in display name (not an ordinal)')
    if src == 'roster' and not first: why.append('roster person with no first name')
    if src == 'roster' and first and not pat and not re.search(r'[A-Za-z]', fam or ''): why.append('roster person with no patronymic')
    if fam and re.search(r'[.,;:]$', fam): why.append('punctuation on canonical surname')
    if first and (FEM_PAT.search(first) or MAL_PAT.search(first)): why.append('canonical first name looks like a patronymic')
    if pat and not re.search(r'(ичъ|ична|вна|шна|ичь|ич|инична)\.?$', pat): why.append('canonical patronymic does not look like one')
    if src == 'roster' and not app.get(pid) : why.append('roster person with no appearance')
    if src != 'roster' and not pc.get(pid) and not rc.get(pid) and not app.get(pid): why.append('person with no appearance, credit or review link')
    if app.get(pid):
        s = sorted(app[pid])
        if (fa, la) != (s[0], s[-1]): why.append(f'attested span {fa}..{la} but appearances {s[0]}..{s[-1]}')
    if fam and first and pat:
        pg = 'f' if FEM_PAT.search(pat) else 'm' if MAL_PAT.search(pat) else None
        fg = gender_of_first(first)
        if pg and fg and pg != fg: why.append('canonical first name and patronymic disagree on gender')
    for w in why: P1.append((w, pid[:8], disp, fam or '', first or '', pat or '', ordn or '', fa or '', la or '', src, qid or ''))
write('P1_person_record', ['signal', 'id', 'display_name', 'family', 'first', 'patronymic', 'ordinal', 'first_season', 'last_season', 'source', 'qid'],
      sorted(P1, key=lambda x: (x[0], x[2])), 'research.person record fields')

# P2 two records holding the same Wikidata QID; production-list creators that may duplicate another record
P2 = []
byq = collections.defaultdict(list)
for p in P:
    if p[8]: byq[p[8]].append(p)
for q, ps in byq.items():
    if len(ps) > 1:
        for p in ps: P2.append(('same QID on two records', q, p[0][:8], p[1], p[11], p[6] or '', p[7] or ''))
creators = [p for p in P if p[11] in ('production_list', 'review')]
allp = {p[0]: p for p in P}
for c in creators:
    for p in P:
        if p[0] == c[0]: continue
        if fold(ORD.sub('', p[2] or '')) == fold(ORD.sub('', c[2] or '')) and (p[11] != 'roster' or c[11] == 'review' or p[11] == c[11]):
            P2.append((f'{c[11]} record shares surname with a {p[11]} record', c[8] or p[8] or '', c[0][:8], c[1], c[11], p[0][:8], p[1]))
        elif c[11] == 'production_list' and p[11] == 'roster' and fold(p[2] or '') == fold(c[2] or ''):
            pass
write('P2_possible_duplicate_records', ['signal', 'qid', 'id', 'display_name', 'source', 'other_id/first', 'other_name/last'], P2,
      'two records for one person among creators / review people, or one QID twice')

# P3 production-list creators whose surname matches a roster person (possible same person held twice)
P3 = []
roster_by_fam = collections.defaultdict(list)
for p in P:
    if p[11] == 'roster': roster_by_fam[fold(ORD.sub('', p[2] or ''))].append(p)
for c in creators:
    for p in roster_by_fam.get(fold(c[2] or ''), []):
        ini = re.findall(rf'([{CYR}])\.', c[1] or '')
        firstok = not ini or (p[3] and fold(p[3])[:1] == fold(ini[0])) or (c[3] and p[3] and fold(c[3]) == fold(p[3]))
        P3.append(('initials agree' if firstok else 'initials differ', c[0][:8], c[1], c[11], c[8] or '', p[0][:8], p[1], f'{p[6]}..{p[7]}', p[8] or ''))
write('P3_creator_vs_roster_surname', ['initials', 'creator_id', 'creator', 'source', 'creator_qid', 'roster_id', 'roster_person', 'roster_span', 'roster_qid'],
      sorted(P3, key=lambda x: (x[0], x[2])), 'creator or review-only record with the same surname as a roster person: same person held twice?')

# =============================================================== production-list credits
C = Q("""select pc.credit_id, pc.production_id, cast(pc.person_id as varchar), pc.role_category, pc.role_text, pc.name_printed,
                pc.honorific_printed, pc.qualifier_printed, pc.is_pseudonym, pc.identification_status, p.display_name,
                p.canonical_family_name, p.canonical_first_name, p.canonical_patronymic, p.person_source, pr.season
         from research.production_credit pc left join research.person p using(person_id)
         left join (select production_id, any_value(season) season from research.production group by 1) pr using(production_id)""")
C1 = []
ROLEWORDS = {'music': r'(муз|сюит|сочин|соч\.)', 'libretto': r'(сюжет|програм|либрет|состав|обработ)', 'staging': r'(поста|возобн|танц|посга)', 'author': r'соч',
             'source': r'(заимств|ваимств|взят|по |сюжет|составл)', 'instrumentation': r'(инструм|оркестр)'}
ini_by_person = collections.defaultdict(set)
for cid, prod, pid, cat, rt, nm, hon, qual, pseud, st, disp, fam, first, pat, src, season in C:
    nm2 = (nm or '').strip()
    nm2 = re.sub(r'^Г\.\s+', '', nm2) if (hon or '') == '' and re.match(r'^Г\.\s+[А-ЯѢІѲ][а-яѣіѳ]', nm2) and not re.match(r'^Г\.\s+[А-ЯѢІѲ]\.', nm2) else nm2
    surname = nm2.split()[-1] if nm2.split() else ''
    if re.search(r'[a-zа-яѣіѳ]-$', surname): surname = nm2
    ini = tuple(fold(x) for x in re.findall(rf'([{CYR}A-Za-z][а-яѣіѳa-z]{{0,3}})\.', nm2[:len(nm2) - len(surname)]))
    if pid and ini: ini_by_person[pid].add((ini[:1], cid, nm2))
    why = []
    if not pid: why.append('credit with no person')
    if pid and fam and not pseud and not same_surname(surname, fam): why.append(f'printed surname ≠ person surname ({fam})')
    if cat in ROLEWORDS and rt and not re.search(ROLEWORDS[cat], rt, re.I): why.append(f'role_category {cat} vs role_text «{rt}»')
    if not cat: why.append('no role_category')
    if pid and ini and first and fold(first)[:1] != ini[0][:1]: why.append(f'printed initial {ini[0]} vs person first name {first}')
    if st != 'confirmed': why.append(f'identification_status {st}')
    if re.search(r'\d', nm2): why.append('digit in printed name')
    for w in why: C1.append((w, cid, prod, season or '', cat or '', rt or '', nm2, hon or '', qual or '', disp or ''))
for pid, s in ini_by_person.items():
    firsts = {i[0] for i in s}
    if len(firsts) > 1:
        for i in sorted(s): C1.append((f'one person printed with different first initials: {sorted(firsts)}', i[1], '', '', '', '', i[2], '', '', allp.get(pid, ('', ''))[1]))
write('C1_production_credits', ['signal', 'credit_id', 'production_id', 'season', 'role_category', 'role_text', 'name_printed', 'honorific', 'qualifier', 'person'],
      sorted(C1, key=lambda x: (x[0], x[9])), 'ballet production-list credits: wrong person, wrong role, unlinked')

# =============================================================== review credits
V = Q("""select rc.credit_id, rc.page_id, rc.season, rc.city, rc.printed_phrase, rc.name_surface, rc.initials, rc.role_category,
                cast(rc.person_id as varchar), rc.person_candidates_n, rc.link_method, rc.is_anonymous, p.display_name,
                p.canonical_family_name, p.canonical_first_name, p.canonical_patronymic, p.person_source, p.first_attested_season, p.last_attested_season
         from research.review_credit rc left join research.person p using(person_id)""")
V1 = []
for cid, page, season, city, phrase, surf, ini, cat, pid, ncand, lm, anon, disp, fam, first, pat, src, fa, la in V:
    why = []
    sw = (surf or '').replace('СеньЛеон', 'Сенъ-Леон').split()
    if pid and fam and sw and not same_surname(sw[-1], fam) and not same_surname(surf, fam) and not fold(fam).endswith(stem(sw[-1])[-4:]): why.append(f'review surname ≠ person surname')
    if pid and pat:
        pg = 'f' if FEM_PAT.search(pat) else 'm' if MAL_PAT.search(pat) else None
        sf = fold(surf or '')
        sg = 'f' if re.search(r'(ой|ую|ая|ою|ова|ева|ина|ской|цкой|ну)$', sf) and not re.search(r'(овой|евой)$', '') else None
        if re.search(r'(г-жи|г-жа|г-жѣ|г-жу|г-жею)', phrase or ''): sg = 'f'
        if re.search(r'(ымъ|имъ|ымъ|ова|ева|аго)$', surf or '') and not re.search(r'г-ж', phrase or ''): sg = sg or None
        if sg == 'f' and pg == 'm' and not re.search(r'(ова|ева|ина)$', sf): why.append('feminine form in review, male person')
    if pid and ini and first:
        ini_f = fold(ini[0])
        if fold(first)[:1] != ini_f: why.append(f'review initial {ini} vs first name {first}')
        elif len(ini) > 1 and pat and fold(pat)[:1] != fold(ini[1]): why.append(f'review initials {ini} vs patronymic {pat}')
    if pid and src == 'roster' and fa and la and not (syear(fa) - 2 <= syear(season) <= syear(la) + 2) and cat not in ('ballet_by', 'music', 'libretto', 'source', 'author'):
        why.append(f'person attested {fa}..{la}, review {season}')
    if not pid and lm not in ('anonymous',) and ncand == 1: why.append('unlinked, but exactly one candidate')
    if not pid and lm == 'unresolved': why.append('unresolved')
    for w in why: V1.append((w, cid, page, season, city or '', cat or '', surf or '', ini or '', phrase or '', lm, disp or '', f'{fa}..{la}'))
write('V1_review_credits', ['signal', 'credit_id', 'page_id', 'season', 'city', 'role', 'name_surface', 'initials', 'printed_phrase', 'link_method', 'person', 'person_span'],
      sorted(V1, key=lambda x: (x[0], x[10], x[3])), 'Season Review credits linked to the wrong person, or not linked')

# review_person: 12 review-only people -- roster person of the same surname in that season/city?
V2 = []
rp = Q("""select cast(p.person_id as varchar), p.display_name, p.canonical_family_name, list(distinct rc.season), list(distinct rc.city)
          from research.person p left join research.review_credit rc using(person_id) where p.person_source='review' group by all""")
for pid, disp, fam, seas, cities in rp:
    for q in P:
        if q[11] == 'roster' and same_surname(q[2], fam) and fold(q[2])[:3] == fold(fam)[:3]:
            near = any(s and q[6] and syear(q[6]) - 1 <= syear(s) <= syear(q[7]) + 1 for s in (seas or []))
            if near: V2.append((pid[:8], disp, ';'.join(x for x in (seas or []) if x), ';'.join(x for x in (cities or []) if x), q[0][:8], q[1], f'{q[6]}..{q[7]}'))
write('V2_review_only_people_vs_roster', ['review_person_id', 'review_person', 'review_seasons', 'review_cities', 'roster_id', 'roster_person', 'roster_span'], V2,
      'review-only people who may be a roster person already')

# =============================================================== jubilee / obituary links
J1 = []
jl = list(csv.DictReader(open('docs/jubilees_obituaries/jubilees_obituaries_person_links.csv', encoding='utf-8')))
je = {}
for r in csv.DictReader(open('docs/jubilees_obituaries/jubilees_obituaries_all_entries.csv', encoding='utf-8')):
    je.setdefault((r['season'], r['name_verbatim']), r)
live = {p[0] for p in P}
for r in jl:
    pid = r['person_id']
    if r['link_status'] == 'linked':
        p = allp.get(pid)
        if not p:
            J1.append(('linked person_id not in research.person (merged/deleted?)', r['entry_id'], r['season'], r['kind'], r['name_verbatim'], r['record_name'], '', r['basis'])); continue
        nv = re.sub(r'\(.*?\)', '', r['name_verbatim']).split(',')[0]
        nv = re.sub(rf'^([{CYR}]\.\s*)+', '', nv).strip()
        if not same_surname(nv, p[2]): J1.append(('surname differs', r['entry_id'], r['season'], r['kind'], r['name_verbatim'], p[1], f'{p[6]}..{p[7]}', r['basis']))
        ini = re.findall(rf'([{CYR}])\.', r['name_verbatim'].split(',', 1)[1] if ',' in r['name_verbatim'] else '')
        if ini and p[3] and fold(p[3])[:1] != fold(ini[0]): J1.append((f'initial {ini[0]} vs first name {p[3]}', r['entry_id'], r['season'], r['kind'], r['name_verbatim'], p[1], f'{p[6]}..{p[7]}', r['basis']))
        if r['kind'] in ('obituary', 'death_mark', 'death_notice') and p[7] and r['season'] and syear(p[7]) > syear(r['season']) + 1:
            J1.append(('death notice, person still listed 2+ seasons later', r['entry_id'], r['season'], r['kind'], r['name_verbatim'], p[1], f'{p[6]}..{p[7]}', r['basis']))
        if r['kind'] in ('obituary', 'death_mark', 'death_notice', 'jubilee', 'farewell') and p[6] and r['season'] and syear(p[6]) > syear(r['season']) + 1 and p[11] == 'roster':
            J1.append(('notice before the person is first listed', r['entry_id'], r['season'], r['kind'], r['name_verbatim'], p[1], f'{p[6]}..{p[7]}', r['basis']))
    elif r['link_status'] == 'no_record' and r['relevance'] in ('core', 'mentions'):
        nv = re.sub(r'\(.*?\)', '', r['name_verbatim']).split(',')[0]
        nv = re.sub(rf'^([{CYR}]\.\s*)+', '', nv).strip()
        cands = [p for p in roster_by_fam.get(fold(ORD.sub('', nv)), [])
                 if r['season'] and p[6] and syear(p[6]) - 1 <= syear(r['season']) <= syear(p[7]) + 1]
        if cands: J1.append((f'no_record, but {len(cands)} roster person(s) of that surname listed then', r['entry_id'], r['season'], r['kind'], r['name_verbatim'],
                             ' | '.join(c[1] for c in cands[:4]), '', r['basis']))
write('J1_jubilee_obituary_links', ['signal', 'entry_id', 'season', 'kind', 'name_verbatim', 'linked_or_candidate', 'person_span', 'basis'],
      sorted(J1, key=lambda x: (x[0], x[2])), 'jubilee/obituary person links: wrong person, stale id, or a person missed')

# =============================================================== Wikidata
W1 = []
qids = sorted({p[8] for p in P if p[8]})
wd = {}
cache = OUT / 'wikidata_cache.json'
if cache.exists(): wd = json.loads(cache.read_text())
if '--no-wikidata' not in sys.argv and set(qids) - set(wd):
    for i in range(0, len(qids), 80):
        chunk = [q for q in qids[i:i + 80]]
        sparql = 'SELECT ?q ?b ?d ?g ?ru ?en WHERE { VALUES ?q { %s } OPTIONAL{?q wdt:P569 ?b} OPTIONAL{?q wdt:P570 ?d} OPTIONAL{?q wdt:P21 ?g} ' \
                 'OPTIONAL{?q rdfs:label ?ru FILTER(lang(?ru)="ru")} OPTIONAL{?q rdfs:label ?en FILTER(lang(?en)="en")} }' % ' '.join('wd:' + q for q in chunk)
        url = 'https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(sparql)
        req = urllib.request.Request(url, headers={'User-Agent': 'imperial-theater-yearbooks-audit/1.0 (research)'})
        for b in json.load(urllib.request.urlopen(req, timeout=60))['results']['bindings']:
            q = b['q']['value'].rsplit('/', 1)[1]
            d = wd.setdefault(q, {'birth': [], 'death': [], 'gender': [], 'ru': '', 'en': ''})
            for k, kk in (('b', 'birth'), ('d', 'death'), ('g', 'gender')):
                if k in b and b[k]['value'] not in d[kk]: d[kk].append(b[k]['value'])
            if 'ru' in b: d['ru'] = b['ru']['value']
            if 'en' in b: d['en'] = b['en']['value']
    cache.write_text(json.dumps(wd, ensure_ascii=False, indent=1))
for p in P:
    if not p[8]: continue
    d = wd.get(p[8])
    if not d: W1.append(('QID not returned by Wikidata (deleted/redirected?)', p[8], p[0][:8], p[1], p[9] or '', '', '', '', f'{p[6]}..{p[7]}', p[11])); continue
    by = sorted(int(x[:5].lstrip('+-')[:4]) for x in d['birth'] if re.match(r'[+-]?\d{4}', x.lstrip('+')))
    dy = sorted(int(x.lstrip('+')[:4]) for x in d['death'] if re.match(r'\d{4}', x.lstrip('+')))
    g = 'f' if any(x.endswith('Q6581072') for x in d['gender']) else 'm' if any(x.endswith('Q6581097') for x in d['gender']) else ''
    why = []
    if p[11] == 'roster' and p[6]:
        if by and syear(p[6]) - by[0] < 8: why.append(f'listed {p[6]} but born {by[0]}')
        if dy and syear(p[7]) > dy[-1] + 1: why.append(f'listed to {p[7]} but died {dy[-1]}')
    if p[11] == 'roster' and by and p[6] and syear(p[6]) - by[0] > 75: why.append(f'listed {p[6]} but born {by[0]}')
    pg = 'f' if p[4] and FEM_PAT.search(p[4]) else 'm' if p[4] and MAL_PAT.search(p[4]) else None
    if pg and g and pg != g: why.append(f'gender: record {pg}, Wikidata {g}')
    ru = d['ru'] or ''
    if ru and p[2] and not any(same_surname(w, p[2]) for w in re.split(r'[\s,]+', ru) if w):
        why.append('Russian label shares no surname with the record')
    if ru and p[3] and p[11] == 'roster':
        words = [w for w in re.split(r'[\s,]+', ru) if w]
        if len(words) >= 2 and not any(fold(w)[:2] == fold(p[3])[:2] for w in words): why.append('Russian label first name differs')
    for w in why: W1.append((w, p[8], p[0][:8], p[1], ru, d['en'], ';'.join(map(str, by)), ';'.join(map(str, dy)), f'{p[6]}..{p[7]}', p[11]))
write('W1_wikidata_links', ['signal', 'qid', 'id', 'display_name', 'wd_label_ru', 'wd_label_en', 'birth', 'death', 'attested', 'source'],
      sorted(W1, key=lambda x: (x[0], x[3])), 'Wikidata matches: dates, gender or label that do not fit the record')
W_all = [(p[8], p[1], (wd.get(p[8]) or {}).get('ru', ''), (wd.get(p[8]) or {}).get('en', ''), p[10] or '', f'{p[6]}..{p[7]}', p[11]) for p in P if p[8]]
write('W0_all_wikidata_links', ['qid', 'display_name', 'wd_label_ru', 'wd_label_en', 'wd_description', 'attested', 'source'], sorted(W_all, key=lambda x: x[1]), 'every link, for an eyeball read')

print(f'roster rows {len(R)}, persons {len(P)}, production credits {len(C)}, review credits {len(V)}, jubilee links {len(jl)}, QIDs {len(qids)}')
for k, (n, note) in COUNTS.items():
    print(f'{k:40s} {n:6d}  {note}')
