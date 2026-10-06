"""Compare blind-reader rows (parsed_reports.json) with the stored rows (stored_rows.json), page by page.
Stored non-person rows (enrolment counts, prose, headings) are identified by NOT having a person-like name; reported separately."""
import json, re, difflib, collections, sys
D = 'docs/eval/graduates_audit_2026-10-06/'
P = json.load(open(D + 'parsed_reports.json')); S = json.load(open(D + 'stored_rows.json'))
st = collections.defaultdict(list)
for r in S: st[r['page_id']].append(r)
def split_name(r):
    fam, first = (r['family_name'] or '').strip(), (r['first_name'] or '').strip()
    if not first and ',' in fam:
        fam, first = [x.strip() for x in fam.split(',', 1)]
    return fam.rstrip('.').strip(), first.rstrip('.').strip()
def personlike(r):
    fam, first = split_name(r)
    note = r['note'] or ''
    if not fam or fam[:1].islower(): return False
    if len(fam.split()) > 2: return False
    if re.fullmatch(r'\s*\d+\s*', note) or len(note) > 200: return False
    if re.match(r'(?i)(ученицы|ученики|балетное|императорск|московск|петербургск)', fam): return False
    return True
out = {}; tot = collections.Counter()
for pg, d in P.items():
    stored = st.get(pg, [])
    sp = [r for r in stored if personlike(r)]; nonp = [r for r in stored if not personlike(r)]
    rd = d['rows']
    a = [split_name(r) for r in sp]; b = [(r['fam'], r['first']) for r in rd]
    sm = difflib.SequenceMatcher(None, [x[0] for x in a], [x[0] for x in b], autojunk=False)
    diffs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                if a[i1 + k][1] != b[j1 + k][1]: diffs.append(('FIRST', sp[i1 + k]['entry_id'][-4:], a[i1 + k], b[j1 + k]))
        elif tag == 'replace':
            for k in range(max(i2 - i1, j2 - j1)):
                diffs.append(('SURNAME' if i1 + k < i2 and j1 + k < j2 else ('STORED_ONLY' if j1 + k >= j2 else 'READ_ONLY'),
                              sp[i1 + k]['entry_id'][-4:] if i1 + k < i2 else '-', a[i1 + k] if i1 + k < i2 else None, b[j1 + k] if j1 + k < j2 else None))
        elif tag == 'delete':
            for k in range(i1, i2): diffs.append(('STORED_ONLY', sp[k]['entry_id'][-4:], a[k], None))
        elif tag == 'insert':
            for k in range(j1, j2): diffs.append(('READ_ONLY', '-', None, b[k]))
    out[pg] = dict(stored_persons=len(sp), stored_nonperson=[(r['entry_id'][-4:], (r['family_name'] or '')[:30], (r['note'] or '')[:50]) for r in nonp], read_rows=len(rd), diffs=diffs)
    tot['pages'] += 1; tot['stored_persons'] += len(sp); tot['read_rows'] += len(rd); tot['nonperson'] += len(nonp); tot['diffs'] += len(diffs)
json.dump(out, open(D + 'compare_result.json', 'w'), ensure_ascii=False, indent=1)
print(dict(tot))
for pg, o in out.items():
    flag = '' if (o['stored_persons'] == o['read_rows'] and not o['diffs'] and not o['stored_nonperson']) else '  <-- differs'
    print(f"{pg[10:]:14} stored_persons={o['stored_persons']:3} read={o['read_rows']:3} nonperson_stored={len(o['stored_nonperson'])} diffs={len(o['diffs'])}{flag}")
