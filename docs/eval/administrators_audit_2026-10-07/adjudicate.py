"""Three-way adjudication of the disputed lines: stored text S, first read R1, verifier V (verify/report_NN.txt).
STORED_OK: V==S (first read was wrong). STORED_WRONG: V==R1 (two independent reads agree against the stored text; S->V is the correction).
MISSING_LINE: V == S + an extra printed line. DISAGREE: V differs from both. -> adjudication.json"""
import json, re, glob, collections
D = 'docs/eval/administrators_audit_2026-10-07/'
TITLES = r'(?:свѣтлѣйшій князь|свѣтлѣйшій|князь|княгиня|графъ|графиня|баронъ|баронесса|принцъ)'
LAT = str.maketrans({'i': 'і', 'I': 'І', 'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у', 'θ': 'ѳ', 'Θ': 'Ѳ', 'є': 'е'})
def norm(s):
    s = re.sub(r'^\s*\d+[.)]\s*', '', s or '').translate(LAT).lower()
    s = re.sub(r'\b' + TITLES + r'\b', ' ', s)
    s = re.sub(r'[^\wѣіѳѵ]+', '', s)
    return s.replace('оставилъслужбу', '')
items = {}
for f in sorted(glob.glob(D + 'verify/bundle_*.json')):
    for i in json.load(open(f)): items[i['id']] = i
V = {}; V_diff = {}; V_conf = {}
for f in sorted(glob.glob(D + 'verify/report_*.txt')):
    for line in open(f, encoding='utf-8'):
        m = re.match(r'^(V\d+\.\d+) \| PRINTED ENTRY: (.*?) \| DIFFERENCES: (.*?) \| CONFIDENCE (\w[\w-]*)', line.strip())
        if m:
            t = re.sub(r'\[[^\]]*\]', '', m.group(2))                                   # location notes
            t = re.sub(r'\s*\((?:under |heading |no list number|printed )[^)]*\)\s*$', '', t.strip())   # trailing annotations
            V[m.group(1)] = t.strip(); V_diff[m.group(1)] = m.group(3); V_conf[m.group(1)] = m.group(4)
res = {}; cnt = collections.Counter()
for iid, it in items.items():
    s, r1, v = it['stored_text'], it['first_read_text'], V.get(iid)
    if v is None: verdict = 'NO_REPORT'
    elif 'NOT FOUND' in v.upper()[:40]: verdict = 'NOT_FOUND'
    else:
        ns, nr, nv = norm(s) if s else None, norm(r1) if r1 else None, norm(v)
        if ns is not None and nv == ns: verdict = 'STORED_OK'
        elif nr is not None and nv == nr: verdict = 'STORED_WRONG'
        elif ns and nv.startswith(ns) and len(nv) > len(ns): verdict = 'MISSING_LINE'
        elif ns is None: verdict = 'UNPAIRED'
        else: verdict = 'DISAGREE'
    res[iid] = dict(item=it, verifier=v, diffs=V_diff.get(iid), conf=V_conf.get(iid), verdict=verdict)
    cnt[verdict] += 1
json.dump(res, open(D + 'adjudication.json', 'w'), ensure_ascii=False, indent=1)
print(dict(cnt), len(V), 'reports parsed for', len(items), 'items')
