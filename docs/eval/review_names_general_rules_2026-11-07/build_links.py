"""Turn the ruled general rules (G1, G2, G3; RG 2026-11-07) into rows for docs/eval/review_mention_links.csv.
occurrence = position among same-surface person mentions of the block in the matcher's own row order
(outputs/reviews/mentions/review_mention.csv), not text order."""
import csv, collections, duckdb, json
G = 'docs/eval/review_names_general_rules_2026-11-07'
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
old = {r['mention_id'] for r in csv.DictReader(open(f'{G}/oldcast_mentions.csv'))}
picks = {}
for r in csv.DictReader(open(f'{G}/g1.csv')):
    if not r['flag'] and r['mention_id'] not in old: picks[r['mention_id']] = (r['person_id'], 'G1 only one candidate on that season\'s list', r)
for r in csv.DictReader(open(f'{G}/g2.csv')):
    if r['mention_id'] not in old: picks.setdefault(r['mention_id'], (r['person_id'], f"G2 {r['decided_by']} leaves one candidate", r))
for r in csv.DictReader(open(f'{G}/g3.csv')):
    picks.setdefault(r['mention_id'], (r['person_id'], f"G3 role in only one candidate's staff-list entry ({r['staff_list_role']})", r))
meta = {str(m): (b, a, s) for m, b, a, s in c.sql(f"select mention_id, block_id, char_start, surface from entities.review_mention where mention_id in ({','.join(picks)})").fetchall()}
blocks = {v[0] for v in meta.values()}
seen = collections.Counter(); occ = {}
for r in csv.DictReader(open('outputs/reviews/mentions/review_mention.csv', encoding='utf-8')):
    if r['mention_type'] != 'person' or r['block_id'] not in blocks: continue
    k = (r['block_id'], r['surface']); occ[(r['block_id'], r['surface'], int(r['char_start']))] = seen[k]; seen[k] += 1
links = {(r['block_id'], r['surface'], r['occurrence']): r['person_id'] for r in csv.DictReader(open('docs/eval/review_mention_links.csv', encoding='utf-8'))}
new, clash, same = [], [], 0
for mid, (pid, rule, r) in picks.items():
    bid, a, surf = meta[mid]; key = (bid, surf, str(occ[(bid, surf, a)]))
    if key in links:
        if links[key] == pid: same += 1
        else: clash.append((mid, key, links[key], pid))
        continue
    new.append({'block_id': bid, 'surface': surf, 'occurrence': key[2], 'person_id': pid,
                'decided_by': f'RG 2026-11-07, general rule {rule}', 'evidence': f"{r['season']} {r['city']} (mention {mid}; {G})"})
json.dump(new, open(f'{G}/new_links.json', 'w'), ensure_ascii=False)
print('picks', len(picks), '| new rows', len(new), '| already same', same, '| clashes', len(clash))
print(collections.Counter(p[1][:2] for p in picks.values()))
for x in clash[:10]: print('  CLASH', x)
