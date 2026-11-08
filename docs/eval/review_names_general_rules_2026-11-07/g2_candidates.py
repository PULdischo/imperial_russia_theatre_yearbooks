"""Rule G2 (review names): several candidates are on that season's staff lists in that city, and the printed ordinal, the honorific,
the gender of the printed surname or the printed initial leave exactly one. Writes g2.csv with the deciding feature."""
import duckdb, csv, re, collections
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
hb = {r['block_id'] for r in csv.DictReader(open('docs/eval/review_historical_passages.csv'))}
app = collections.defaultdict(list)
for pid, s, city, et, fam, first in c.sql("""select person_id::varchar, season, city, entity_type, printed_family_name, printed_first_name
        from research.person_appearance""").fetchall():
    app[(pid, s, city)].append((et, fam or '', first or ''))
names = dict(c.sql("select person_id::varchar, display_name from research.person").fetchall())
rows = c.sql("""select m.mention_id, m.season, m.city, m.surface, m.block_id, m.candidate_ids, m.char_start, coalesce(b.text, b.caption_text, '')
        from research.review_mention m join raw.review_block b on b.block_id = m.block_id
        where m.mention_type = 'person' and m.person_id is null and m.candidates_n > 1""").fetchall()
fem = lambda f: bool(re.search(r"(а|ая|я)(\s*\d.*)?$", f.strip()))
def ordn(x):
    m = re.search(r"\b(\d)\s*-?\s*(я|й|ая|ый|ой)?\s*$", x.strip()); return m.group(1) if m else None
out = []
for mid, s, city, surf, bid, cids, a, t in rows:
    if bid in hb: continue
    listed = [p for p in cids.split('|') if (p, s, city) in app]
    if len(listed) < 2: continue
    k = t.find(surf.split()[0], max(0, a - 40)); k = a if k < 0 else k
    pre, post = t[max(0, k - 70):k].replace('\n', ' '), t[k:k + 60].replace('\n', ' ')
    if re.search(r"\b18[0-8]\d\b", t[max(0, k - 160):k + 80]): continue                      # possibly historical: not here
    heads = list(re.finditer(r"(воспитанни\w*|восп\.|в-ц\w*|в-к\w*|уч-ц\w*|уч-к\w*|учени\w*|г-ж\w*|Г-ж\w*|гг\.|г-нъ|г\.)", t[max(0, k - 200):k]))
    pupil_ctx = bool(heads) and bool(re.match(r"(воспитанни|восп|в-ц|в-к|уч-ц|уч-к|учени)", heads[-1].group(1)))
    hon_f = bool(re.search(r"(г-ж|Г-ж|в-ц|восп-ц|балерин)\w*\.?\s*([А-ЯЁ]\.\s*){0,2}$", pre))
    hon_m = bool(re.search(r"(\bг\.|\bгг\.|г-нъ|в-къ|восп-къ)\s*([А-ЯЁ]\.\s*){0,2}$", pre))
    base = re.sub(r"\s*\d.*$", "", surf).strip()
    surf_f = bool(re.search(r"(ова|ева|ина|ына|ская|цкая|ой|ою|ей|ею|ая)$", base))
    surf_m = bool(re.search(r"(овъ|евъ|инъ|ынъ|скій|цкій)$", base))
    tail = post[len(surf):] if post.startswith(surf.split()[0]) else post
    pm = re.search(r"(\d)\s*-?\s*(я|й|ая|ый|ой)?", surf) or re.match(r"\s*(\d)\s*-?\s*(я|й|ая|ый|ой)?", tail)
    po = pm.group(1) if pm else None
    if pm and pm.group(2) in ('я', 'ая'): surf_f = True
    if pm and pm.group(2) in ('й', 'ый', 'ой'): surf_m = True
    ini = re.search(r"([А-ЯЁ])\.\s*$", pre); ini = ini.group(1) if ini else None
    if surf_f and (surf_m or hon_m) or surf_m and hon_f: continue
    keep, why = [], set()
    for p in listed:
        forms = app[(p, s, city)]; f_ = any(fem(f) for _, f, _ in forms)
        if (hon_f or surf_f) and not f_: why.add('gender'); continue
        if (hon_m or surf_m) and f_ and not any(not fem(f) for _, f, _ in forms): why.add('gender'); continue
        if po and not any(ordn(f) == po for _, f, _ in forms): why.add('ordinal'); continue
        if ini and not any(fn.startswith(ini) for _, _, fn in forms): why.add('initial'); continue
        if pupil_ctx and not any(et == 'Graduates' for et, _, _ in forms): why.add('pupil'); continue
        keep.append(p)
    if len(keep) == 1:
        p = keep[0]
        out.append(dict(mention_id=mid, season=s, city=city, surface=surf, chosen=names.get(p, p), person_id=p, decided_by='+'.join(sorted(why)),
                        others='; '.join(names.get(q, q) for q in listed if q != p), before=pre, after=post))
w = csv.DictWriter(open('docs/eval/review_names_general_rules_2026-11-07/g2.csv', 'w', encoding='utf-8'), fieldnames=list(out[0]))
w.writeheader(); w.writerows(out)
print('G2 mentions:', len(out)); print(collections.Counter(o['decided_by'] for o in out).most_common())
