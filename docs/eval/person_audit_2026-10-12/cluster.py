"""Group the same-start-date pairs of U_unconnected_pairs.csv into clusters and grade them.
A = one consistent name, one patronymic, no season in which two members stand in the same list;
B = something to look at (two patronymics, a same-list overlap, a surname that differs).
usage: uv run python docs/eval/person_audit_2026-10-12/cluster.py"""
import csv, collections, re
from pathlib import Path
D = Path(__file__).parent
U = [r for r in csv.DictReader(open(D / 'U_unconnected_pairs.csv', encoding='utf-8-sig')) if r['kind'].endswith('same start date')]
par = {}
def find(x):
    par.setdefault(x, x)
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x
info = {}
for r in U:
    info[r['id_1']] = (r['person_1'], r['span_1'], r['lists_1']); info[r['id_2']] = (r['person_2'], r['span_2'], r['lists_2'])
    par[find(r['id_1'])] = find(r['id_2'])
cl = collections.defaultdict(set)
for x in list(par): cl[find(x)].add(x)
def pat(name):
    p = name.split(',')[-1].split()
    return p[-1].lower() if len(p) >= 2 else ''
def fold(s):
    for a, b in (('ѳ', 'ф'), ('і', 'и'), ('ѣ', 'е'), ('й', 'и')): s = s.replace(a, b)
    return re.sub(r'(.)\1', r'\1', re.sub('[ъь]', '', s))
out = []
for root, mem in cl.items():
    rows = [r for r in U if r['id_1'] in mem]
    overlap = any(r['same_list_overlap'] for r in rows)
    variant = any(r['kind'].startswith('surname variant') for r in rows)
    pats = {fold(pat(info[m][0])) for m in mem} - {''}
    grad = sum(1 for m in mem if info[m][2].startswith('-/Graduates') and ';' not in info[m][2])
    n_pairs_expected = len(mem) * (len(mem) - 1) // 2
    grade = 'A' if not overlap and not variant and len(pats) <= 1 else 'B'
    why = '; '.join(w for w, c in (('same-list overlap', overlap), ('surname differs', variant), ('patronymics differ: ' + '/'.join(sorted(pats)), len(pats) > 1)) if c)
    members = sorted(mem, key=lambda m: info[m][1])
    out.append((grade, len(mem), grad, why, rows[0]['shared_start'], ' || '.join(f"{m} {info[m][0]} [{info[m][1]}; {info[m][2]}]" for m in members)))
out.sort(key=lambda r: (r[0], r[5].split(' ', 1)[1]))
with open(D / 'U_clusters_same_start_date.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['grade', 'records', 'graduate_only_records', 'look_at', 'shared_start', 'members']); w.writerows(out)
c = collections.Counter(r[0] for r in out)
print('clusters:', dict(c), '| records that would be absorbed:', {g: sum(r[1] - 1 for r in out if r[0] == g) for g in c})
print('A clusters by shape:', collections.Counter(('with graduate' if r[2] else 'company only', r[1]) for r in out if r[0] == 'A'))
for r in out:
    if r[0] == 'B': print('  B', r[3], '|', r[5][:230])
