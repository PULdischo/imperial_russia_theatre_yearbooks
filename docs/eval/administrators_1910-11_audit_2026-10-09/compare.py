"""Compare blind-reader rows (parsed_reports.json) with the stored rows (stored_rows.json[_after]) page by page, ORDER-INDEPENDENT (best-pair matching on surname+name).
Classes: SURNAME / NAME / RANKNOTE (rank+note tokens differ) / DATE / NUMBER / TITLE_IN_NAME / HOMOGLYPH (Latin letter in a Cyrillic word) / STORED_ONLY / READ_ONLY.
usage: uv run python compare.py [after]"""
import json, re, difflib, collections, sys
D = 'docs/eval/administrators_1910-11_audit_2026-10-09/'
suffix = '_after' if 'after' in sys.argv else ''
P = json.load(open(D + 'parsed_reports.json')); S = json.load(open(D + f'stored_rows{suffix}.json'))
st = collections.defaultdict(list)
for r in S: st[r['page_id']].append(r)
TITLES = r'(?:свѣтлѣйшій князь|свѣтлѣйшій|князь|княгиня|графъ|графиня|баронъ|баронесса|принцъ)'
def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[^\wѣіѳѵ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()
def strip_title(s): return re.sub(r'\b' + TITLES + r'\b', ' ', s or '', flags=re.I)
def ntoks(*xs): return norm(strip_title(' '.join(x or '' for x in xs))).split()
def has_title(*xs): return any(re.search(r'\b' + TITLES + r'\b', x or '', re.I) for x in xs)
MON = {'января':1,'февраля':2,'марта':3,'апрѣля':4,'мая':5,'іюня':6,'іюля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12,'июня':6,'июля':7}
def dates(t):
    out = []
    for m in re.finditer(r'(\d{1,2})\s+([а-яѣі]+)\s+(\d{4})', t or ''):
        mo = MON.get(m.group(2))
        if mo: out.append((int(m.group(3)), mo, int(m.group(1))))
    return sorted(set(out))
def num(s): return re.sub(r'[^0-9]', '', s or '')
LAT = re.compile(r'[A-Za-z]')
def homoglyph(s): return bool(s) and bool(LAT.search(s)) and bool(re.search(r'[А-Яа-яЁёѢѣІіѲѳ]', s))
def key(fam, first, pat): return norm(strip_title(re.sub(r'\s+\d+-[йя]$', '', fam or ''))) + ' | ' + ' '.join(ntoks(first, pat))
res = {}; tot = collections.Counter()
for pg, d in P.items():
    rr = d['rows']; ss = st.get(pg, [])
    ks = [key(s['family_name'], s['first_name'], s['patronymic']) for s in ss]
    kr = [key(r['fam'], r['first'], r['pat']) for r in rr]
    sims = sorted(((difflib.SequenceMatcher(None, ks[i], kr[j]).ratio(), i, j) for i in range(len(ss)) for j in range(len(rr))), reverse=True)
    mi, mj, pairs = set(), set(), []
    for sim, i, j in sims:
        if sim < 0.72: break
        if i in mi or j in mj: continue
        mi.add(i); mj.add(j); pairs.append((i, j))
    diffs = []
    for i in range(len(ss)):
        if i not in mi: diffs.append(('STORED_ONLY', ss[i]['entry_id'][-4:], ' | '.join(str(ss[i][f]) for f in ('family_name', 'first_name', 'patronymic')), (ss[i]['note'] or '')[:70]))
    for j in range(len(rr)):
        if j not in mj: diffs.append(('READ_ONLY', '-', rr[j]['verbatim'][:110], ''))
    for i, j in pairs:
        s, r = ss[i], rr[j]; eid = s['entry_id'][-4:]
        sf = norm(strip_title(re.sub(r'\s+\d+-[йя]$', '', s['family_name'] or ''))); rf = norm(strip_title(r['fam']))
        if sf != rf: diffs.append(('SURNAME', eid, s['family_name'], r['fam']))
        if has_title(s['family_name'], s['first_name'], s['patronymic']): diffs.append(('TITLE_IN_NAME', eid, [s['family_name'], s['first_name'], s['patronymic'], s['rank']], [r['title'], r['first'], r['pat'], r['rank']]))
        ts, tr = ntoks(s['first_name'], s['patronymic']), ntoks(r['first'], r['pat'])
        if ts != tr: diffs.append(('NAME', eid, ' '.join(ts), ' '.join(tr)))
        # character-level diff of the whole entry (stored name+rank+note vs printed verbatim), titles stripped, spaces/punctuation ignored
        sj = re.sub(r'\s+', '', norm(strip_title(' '.join(str(s[f] or '') for f in ('family_name', 'first_name', 'patronymic', 'rank', 'note')))))
        vv = re.sub(r'^\s*\d+[.)]\s*', '', r['verbatim'])
        vj = re.sub(r'\s+', '', norm(strip_title(vv)))
        sj2 = sj.replace('оставилъслужбу', '')
        vj2 = vj.replace('оставилъслужбу', '')
        if sj2 != vj2:
            sm = difflib.SequenceMatcher(None, sj2, vj2, autojunk=False)
            ch = [(sj2[i1:i2], vj2[j1:j2]) for tg, i1, i2, j1, j2 in sm.get_opcodes() if tg != 'equal']
            diffs.append(('CHARS', eid, ch[:6], len(ch)))
        ds, dr = dates(s['note']), dates(r['verbatim'])
        if dr and ds != dr:
            diffs.append(('DATE_MISSING' if set(ds) < set(dr) else 'DATE_DIFF', eid, ds, dr))
        if (s['list_number'] or '') and r['n'] not in ('-', '') and num(s['list_number']) != num(r['n']): diffs.append(('NUMBER', eid, s['list_number'], r['n']))
        for f in ('family_name', 'first_name', 'patronymic', 'rank', 'note'):
            if homoglyph(s[f]): diffs.append(('HOMOGLYPH', eid, f, s[f][:60]))
    res[pg] = dict(stored=len(ss), read=len(rr), diffs=diffs, pairs=[(ss[i]['entry_id'], j) for i, j in pairs])
    tot['pages'] += 1; tot['stored'] += len(ss); tot['read'] += len(rr)
    for x in diffs: tot[x[0]] += 1
json.dump(res, open(D + f'compare_result{suffix}.json', 'w'), ensure_ascii=False, indent=1)
print(dict(tot))
