"""Rule G1 (review names): of a tied mention's candidates, only one appears on that season's staff lists in that city.
Writes g1.csv: mention, the one listed candidate, the list(s) she/he is on, honorific vs gender, context."""
import duckdb, csv, re, collections
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
hb = {r['block_id'] for r in csv.DictReader(open('docs/eval/review_historical_passages.csv'))}
app = collections.defaultdict(list)
for pid, s, city, et, fam, first in c.sql("""select person_id::varchar, season, city, entity_type, printed_family_name, printed_first_name
        from research.person_appearance""").fetchall():
    app[(pid, s, city)].append((et, fam or '', first or ''))
names = dict(c.sql("select person_id::varchar, display_name from research.person").fetchall())
rows = c.sql("""select m.mention_id, m.season, m.city, m.surface, m.block_id, m.candidate_ids, m.char_start,
        coalesce(b.text, b.caption_text, ''), b.block_type
        from research.review_mention m join raw.review_block b on b.block_id = m.block_id
        where m.mention_type = 'person' and m.person_id is null and m.candidates_n > 1""").fetchall()
fem = lambda f: bool(re.search(r"(а|ая|я)(\s*\d.*)?$", f.strip()))
out = []
for mid, s, city, surf, bid, cids, a, t, bt in rows:
    if bid in hb: continue
    listed = [p for p in cids.split('|') if (p, s, city) in app]
    if len(listed) != 1: continue
    p = listed[0]; forms = app[(p, s, city)]
    # context around the surface (offsets can drift ~12 chars)
    k = t.find(surf.split()[0], max(0, a - 40)); k = a if k < 0 else k
    pre, post = t[max(0, k - 70):k].replace('\n', ' '), t[k:k + 60].replace('\n', ' ')
    hon_f = bool(re.search(r"(г-ж|Г-ж|в-ц|восп-ц|балерин)\w*\.?\s*([А-ЯЁ]\.\s*){0,2}$", pre))
    hon_m = bool(re.search(r"(\bг\.|\bгг\.|г-нъ|в-къ|восп-къ)\s*([А-ЯЁ]\.\s*){0,2}$", pre))
    cand_f = any(fem(f) for _, f, _ in forms)
    flag = ''
    if hon_f and not cand_f: flag = 'woman\'s honorific, man listed'
    if hon_m and cand_f: flag = 'man\'s honorific, woman listed'
    # gender of the printed surname itself (feminine endings incl. oblique cases; ordinal stripped)
    base = re.sub(r"\s*\d.*$", "", surf).strip()
    surf_f = bool(re.search(r"(ова|ева|ёва|ина|ына|ская|цкая|ой|ою|ей|ею|ую|ая)$", base))
    surf_m = bool(re.search(r"(овъ|евъ|инъ|ынъ|скій|цкій|ымъ|омъ|ова|ева|ина|скаго|цкаго|ому|ему)$", base)) and not surf_f
    if not flag and surf_f and not cand_f: flag = 'feminine surname, man listed'
    if not flag and re.search(r"(овъ|евъ|инъ|ынъ|скій|цкій)$", base) and cand_f: flag = 'masculine surname, woman listed'
    # printed ordinal must match an ordinal the candidate carries that season
    tail = post[len(surf):] if post.startswith(surf.split()[0]) else post
    pm = re.search(r"(\d)\s*-?\s*(я|й|ая|ый|ой)?", surf) or re.match(r"\s*(\d)\s*-?\s*(я|й|ая|ый|ой)?", tail)
    po = pm
    ord_f = bool(pm and pm.group(2) in ('я', 'ая')); ord_m = bool(pm and pm.group(2) in ('й', 'ый', 'ой'))
    if not flag and ord_f and not cand_f: flag = 'feminine ordinal, man listed'
    if not flag and ord_m and cand_f: flag = 'masculine ordinal, woman listed'
    if not flag and po and not any(re.search(r"\b" + po.group(1) + r"\b", f) for _, f, _ in forms): flag = 'ordinal does not match'
    # a pre-1890 year within the sentence before the name: possibly historical
    if not flag and re.search(r"\b18[0-8]\d\b", t[max(0, k - 160):k + 80]): flag = 'pre-1890 year nearby (historical?)'
    # inside a pupils' list (the last list heading before the name is a pupils' one), unless the candidate is a pupil/graduate that season
    heads = list(re.finditer(r"(воспитанни\w*|восп\.|в-ц\w*|в-к\w*|уч-ц\w*|уч-к\w*|учени\w*|г-ж\w*|Г-ж\w*|гг\.|г-нъ|г\.)", t[max(0, k - 200):k]))
    if not flag and heads and re.match(r"(воспитанни|восп|в-ц|в-к|уч-ц|уч-к|учени)", heads[-1].group(1)) \
            and not any(et in ('Graduates',) for et, _, _ in forms):
        flag = 'in a pupils\' list, candidate is not a pupil'
    out.append(dict(mention_id=mid, season=s, city=city, surface=surf, listed=names.get(p, p), person_id=p,
                    lists='/'.join(sorted({et for et, _, _ in forms})), flag=flag, before=pre, after=post, block_type=bt))
w = csv.DictWriter(open('docs/eval/review_names_general_rules_2026-11-07/g1.csv', 'w', encoding='utf-8'), fieldnames=list(out[0]))
w.writeheader(); w.writerows(out)
print('G1 mentions:', len(out))
print('lists of the one listed candidate:', collections.Counter(o['lists'] for o in out).most_common(8))
print('honorific/gender flags:', collections.Counter(o['flag'] for o in out))
