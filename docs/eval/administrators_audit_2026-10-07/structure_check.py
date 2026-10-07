"""Which OFFICE (Directorate / St Petersburg Office / Moscow Office) is each row under -- stored vs the readers' headings carried forward across pages.
Office = the last H1 heading seen (carried across pages within a season); rows before the first H1 of a season (the first lines of the list) = Directorate-level (both cities)."""
import json, re, collections
D = 'docs/eval/administrators_audit_2026-10-07/'
P = json.load(open(D + 'parsed_reports.json')); C = json.load(open(D + 'compare_result.json')); S = {r['entry_id']: r for r in json.load(open(D + 'stored_rows.json'))}
def office_of(h):
    if re.search(r'Московск|Москв', h): return 'MSK'
    if re.search(r'Петербург', h): return 'SPB'
    return 'OTHER'
def stored_office(r):
    t = (r['institution'] or '') + ' | ' + (r['heading_path'] or '')
    m = bool(re.search(r'Московск|Москв', t)); p = bool(re.search(r'Петербург', t))
    return 'MSK' if m and not p else 'SPB' if p and not m else 'BOTH?' if m and p else 'NONE'
seasons = collections.defaultdict(list)
for pg in P: seasons[pg.split('_')[1]].append(pg)
exp = {}   # entry_id -> expected office
for se, pgs in seasons.items():
    cur = 'DIR'
    for pg in sorted(pgs):
        pairs = {j: eid for eid, j in C[pg]['pairs']}
        # headings in reading order are interleaved with rows via each row's 'stack'
        for j, row in enumerate(P[pg]['rows']):
            h1 = row['stack'].get('1') or row['stack'].get(1)
            if h1: cur = office_of(h1)
            if j in pairs: exp[pairs[j]] = (cur, pg)
bad = collections.Counter(); ex = collections.defaultdict(list)
for eid, (e, pg) in exp.items():
    s = stored_office(S[eid])
    key = (e, s)
    bad[key] += 1
    if (e, s) not in (('DIR', 'NONE'), ('SPB', 'SPB'), ('MSK', 'MSK')): ex[key].append((pg[15:], eid[-4:], (S[eid]['institution'] or '')[:35], (S[eid]['heading_path'] or '')[:45]))
print('expected office (rows) x stored office:'); 
for k, v in sorted(bad.items(), key=lambda x: -x[1]): print('  ', k, v)
json.dump({k[0] + '>' + k[1]: v for k, v in ex.items()}, open(D + 'structure_mismatch_examples.json', 'w'), ensure_ascii=False, indent=1)
