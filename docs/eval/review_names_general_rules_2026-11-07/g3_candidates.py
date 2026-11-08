"""Rule G3 (review names; RG 2026-11-07 Petipa ruling made general): the role the review names for the mention appears in exactly one
candidate's staff-list entry that season (named_work role_name) -> that person. Also cross-checks G1/G2 picks against the role evidence."""
import duckdb, csv, re, collections, sys
sys.path.insert(0, 'docs/eval/review_names_general_rules_2026-11-07'); import oldcast_check as oc
G = 'docs/eval/review_names_general_rules_2026-11-07'
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
hb = {r['block_id'] for r in csv.DictReader(open('docs/eval/review_historical_passages.csv'))}
roles = collections.defaultdict(list)   # (person, season, city) -> [(work, role)]
for pid, s, city, w, r in c.sql("""select a.person_id::varchar, a.season, a.city, cr.label, cr.role_name from raw.person_entry_credit cr
        join research.person_appearance a on a.appearance_id = cr.entry_id where cr.credit_type = 'named_work' and cr.role_name is not null""").fetchall():
    roles[(pid, s, city)].append((w or '', r))
onlist = {(p, s, ci) for p, s, ci in c.sql("select distinct person_id::varchar, season, city from research.person_appearance").fetchall()}
forms = collections.defaultdict(list)
for p, s, ci, fam in c.sql("select person_id::varchar, season, city, printed_family_name from research.person_appearance").fetchall():
    forms[(p, s, ci)].append(fam or '')
fem = lambda f: bool(re.search(r"(а|ая|я)(\s*\d.*)?$", f.strip()))
def contradicts(p, s, ci, surf, pre, tail):
    fs = forms[(p, s, ci)]
    pm = re.search(r"(\d)\s*-?\s*(я|й|ая|ый|ой)?", surf) or re.match(r"\s*(\d)\s*-?\s*(я|й|ая|ый|ой)?", tail)
    if pm and not any(re.search(r"\b" + pm.group(1) + r"\b", f) for f in fs): return 'printed number differs'
    f_ = any(fem(f) for f in fs)
    if (re.search(r"(г-ж|Г-ж|в-ц)\w*\.?\s*([А-ЯЁ]\.\s*){0,2}$", pre) or (pm and pm.group(2) in ('я', 'ая'))) and not f_: return 'gender'
    if (re.search(r"(\bг\.|\bгг\.|г-нъ|в-къ)\s*([А-ЯЁ]\.\s*){0,2}$", pre) or (pm and pm.group(2) in ('й', 'ый', 'ой'))) and f_: return 'gender'
    return ''

names = dict(c.sql("select person_id::varchar, display_name from research.person").fetchall())
STOP = {'граф', 'графин', 'королев', 'корол', 'принцесс', 'принц', 'фе', 'жен', 'дочер', 'подруг', 'мать', 'сестр', 'слуг', 'сын'}
def words(s):
    s = s.lower().replace('ѣ', 'е').replace('і', 'и').replace('ѳ', 'ф')
    return [re.sub(r"(ией|ою|ею|ами|ями|ой|ей|ыя|ия|ая|ии|ию|ы|и|а|я|у|ю|ъ|ь|е|о)$", "", w) for w in re.findall(r"[a-zа-яё]{3,}", s)]
def key(r): return {w for w in words(r) if w not in STOP and len(w) >= 3}
def review_role(pre, post_tail):
    ra = re.match(r"\s*\d?\s*(-я|-й)?\s*\(([^)]{2,40})\)", post_tail)
    rb = re.search(r"([А-ЯЁA-Za-zа-яёѣі][^—;:()\d]{1,40}?)\s*[—–]\s*(г-ж\w*\s*|Г-ж\w*\s*|г\.\s*|г-нъ\s*|восп\.\s*|в-\w+\s*)?([А-ЯЁ]\.\s*)*$", pre)
    return (ra.group(2) if ra else (rb.group(1) if rb else '')).strip(' ,.')
done = {r['mention_id']: ('G1', r['person_id']) for r in csv.DictReader(open(f'{G}/g1.csv')) if not r['flag']}
done.update({r['mention_id']: ('G2', r['person_id']) for r in csv.DictReader(open(f'{G}/g2.csv'))})
old = {r['mention_id'] for r in csv.DictReader(open(f'{G}/oldcast_mentions.csv'))}
rows = c.sql("""select m.mention_id, m.season, m.city, m.surface, m.block_id, m.candidate_ids, m.char_start, coalesce(b.text, b.caption_text, '')
        from research.review_mention m join raw.review_block b on b.block_id = m.block_id
        where m.mention_type = 'person' and m.person_id is null and m.candidates_n > 1""").fetchall()
g3, conflicts = [], []
for mid, s, city, surf, bid, cids, a, t in rows:
    mid = str(mid)
    if bid in hb or mid in old: continue
    k = t.find(surf.split()[0], max(0, a - 40)); k = a if k < 0 else k
    pre, tail = t[max(0, k - 70):k].replace('\n', ' '), t[k + len(surf):k + len(surf) + 50].replace('\n', ' ')
    role = review_role(pre, tail)
    if not role or not key(role): continue
    listed = [p for p in cids.split('|') if (p, s, city) in onlist]
    hits = {p: [f"{w} — {r}" for w, r in roles[(p, s, city)] if key(r) & key(role)] for p in listed}
    hits = {p: h for p, h in hits.items() if h}
    if mid in done:
        if hits and done[mid][1] not in hits:
            conflicts.append(dict(mention_id=mid, rule=done[mid][0], season=s, city=city, surface=surf, role=role,
                                  rule_pick=names.get(done[mid][1]), role_points_to='; '.join(f"{names.get(p)} ({h[0]})" for p, h in hits.items())))
        continue
    if oc.is_oldcast(bid, a, t)[0]: continue
    if len(hits) == 1:
        p, h = next(iter(hits.items()))
        if contradicts(p, s, city, surf, pre, tail): continue
        g3.append(dict(mention_id=mid, season=s, city=city, surface=surf, role=role, chosen=names.get(p), person_id=p, staff_list_role=h[0],
                       others='; '.join(names.get(q) for q in listed if q != p), context=(pre + '[' + surf + ']' + tail)[-150:]))
for fn, rows_ in (('g3.csv', g3), ('role_conflicts.csv', conflicts)):
    if rows_:
        w = csv.DictWriter(open(f'{G}/{fn}', 'w', encoding='utf-8'), fieldnames=list(rows_[0])); w.writeheader(); w.writerows(rows_)
print('G3 mentions:', len(g3), '| G1/G2 picks contradicted by the role evidence:', len(conflicts))
for x in conflicts[:10]: print('  CONFLICT', x)
