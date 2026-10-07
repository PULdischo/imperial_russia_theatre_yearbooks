"""Collect the rows where the first blind read and the stored value disagree (after removing reader artifacts) -> disputes.json.
Reader artifacts ignored: Greek theta for Ѳ, Latin i for і, e-diaeresis, a reader's own bracketed remarks."""
import json, re, collections
D = 'docs/eval/administrators_audit_2026-10-07/'
C = json.load(open(D + 'compare_result.json')); P = json.load(open(D + 'parsed_reports.json')); S = {r['entry_id']: r for r in json.load(open(D + 'stored_rows.json'))}
ART = {('ѳ', 'θ'), ('θ', 'ѳ'), ('і', 'i'), ('i', 'і'), ('ф', 'θ')}
def real_chars(ch):
    ch = [c for c in ch if tuple(c) not in ART]
    dels = {c[0] for c in ch if c[0] and not c[1]}; ins = {c[1] for c in ch if c[1] and not c[0]}
    out = []
    for c in ch:
        a, b = c
        if a and not b and any(a in i or i in a for i in ins if len(i) >= 4): continue    # reorder: the same text printed elsewhere in the entry
        if b and not a and any(b in d or d in b for d in dels if len(d) >= 4): continue
        out.append(c)
    return out
disp = collections.OrderedDict()
def add(pg, eid, kind, a, b):
    d = disp.setdefault((pg, eid), dict(page=pg, entry_id=eid, kinds=[], detail=[]))
    d['kinds'].append(kind); d['detail'].append((a, b))
for pg, d in C.items():
    for x in d['diffs']:
        k, eid = x[0], x[1]
        eid = (pg + '__' + eid) if eid not in ('-', 'READ') else 'READ'
        if k == 'CHARS':
            rc = real_chars(x[2])
            if rc: add(pg, eid, k, rc, x[3])
        elif k in ('SURNAME', 'NAME', 'DATE_MISSING', 'DATE_DIFF', 'HOMOGLYPH', 'TITLE_IN_NAME'): add(pg, eid, k, x[2], x[3] if len(x) > 3 else None)
        elif k in ('STORED_ONLY', 'READ_ONLY'): add(pg, eid if k == 'STORED_ONLY' else 'READ', k, x[2], x[3])
out = []
for (pg, eid), d in disp.items():
    s = S.get(eid)
    d['stored'] = ' | '.join(str(s[f] or '') for f in ('list_number', 'family_name', 'first_name', 'patronymic', 'rank', 'note')) if s else None
    out.append(d)
json.dump(out, open(D + 'disputes.json', 'w'), ensure_ascii=False, indent=1)
kinds = collections.Counter(k for d in out for k in set(d['kinds']))
print(len(out), 'disputed rows on', len(set(d['page'] for d in out)), 'pages;', dict(kinds))
