"""All person mentions in the Season Reviews that stand in a list of school pupils (RG 2026-11-07: "we should definitely collect a
list of school pupil mentions"). A mention counts when the last list heading before it (within 200 chars, same block) is a pupils'
marker (воспитанницы/-ки, восп., в-цы/в-ки, уч-цы/уч-ки, ученицы/-ки) rather than г-жа/г-жи/г./гг. Writes pupil_mentions.csv."""
import duckdb, csv, re, collections
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
hb = {r['block_id'] for r in csv.DictReader(open('docs/eval/review_historical_passages.csv'))}
grad = collections.defaultdict(list)   # surname stem -> [(season, printed name)]
for fam, first, pid in c.sql("select family_name, first_name, page_id from raw.person_entry where page_id like 'graduates_%'").fetchall():
    s = re.search(r"_(\d{4}-\d{2})_", pid).group(1)
    grad[re.sub(r"\s*\d.*$", "", fam or '').strip()[:-1]].append((s, f"{fam}, {first or ''}".strip(', ')))
names = dict(c.sql("select person_id::varchar, display_name from research.person").fetchall())
rows = c.sql("""select m.mention_id, m.season, m.city, m.page_id, sp.printed_page, m.block_id, m.surface, m.char_start,
        m.person_id::varchar, coalesce(b.text, b.caption_text, '')
        from research.review_mention m join raw.review_block b on b.block_id = m.block_id
        left join research.source_page sp on sp.page_id = m.page_id where m.mention_type = 'person'""").fetchall()
PUP = r"(воспитанни\w*|восп\.|восп-\w*|в-ц\w*|в-к\w*|уч-ц\w*|уч-к\w*|учени\w*)"
out = []
for mid, s, city, pid, pp, bid, surf, a, person, t in rows:
    k = t.find(surf.split()[0], max(0, a - 40)); k = a if k < 0 else k
    window = t[max(0, k - 200):k]
    heads = list(re.finditer(PUP + r"|(г-ж\w*|Г-ж\w*|гг\.|г-нъ|\bг\.)", window))
    if not heads or not heads[-1].group(1): continue
    stem = re.sub(r"(ой|ою|ей|ою|ымъ|омъ|ую|ы|у|а|я|ъ)$", "", re.sub(r"\s*\d.*$", "", surf).strip())
    g = sorted({f"{gs} {gn}" for st, lst in grad.items() if st.startswith(stem[:max(4, len(stem) - 1)]) for gs, gn in lst if gs >= s})
    out.append(dict(mention_id=mid, season=s, city=city, page_id=pid, printed_page=pp, surface=surf,
                    pupil_marker=heads[-1].group(1), linked_now=names.get(person, '') if person else '',
                    historical_block='yes' if bid in hb else '', graduates_same_surname_later='; '.join(g[:4]),
                    context=t[max(0, k - 90):k + len(surf) + 30].replace('\n', ' ')))
w = csv.DictWriter(open('docs/eval/review_pupil_mentions.csv', 'w', encoding='utf-8', newline=''), fieldnames=list(out[0]), lineterminator='\n')
w.writeheader(); w.writerows(out)
print('pupil mentions:', len(out), '| seasons:', len({o['season'] for o in out}), '| by city:', collections.Counter(o['city'] for o in out))
print('linked now:', sum(1 for o in out if o['linked_now']), '| with a same-surname graduate that season or later:', sum(1 for o in out if o['graduates_same_surname_later']))
print('markers:', collections.Counter(o['pupil_marker'] for o in out).most_common(8))
