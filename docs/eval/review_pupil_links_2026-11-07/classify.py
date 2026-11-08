"""Pupil mentions in the reviews that are already linked: could the linked person have been that pupil?
A pupil should (a) agree in gender with the printed surname/marker, and (b) not be a dancer already on the company lists years before.
For doubtful links, look for a better candidate: same surname stem and gender, on a graduates' list in that season or up to 6 later."""
import duckdb, csv, re, collections
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
D = 'docs/eval/review_pupil_links_2026-11-07'
P = {r[0]: r[1:] for r in c.sql("select display_name, person_id::varchar, first_attested_season, canonical_family_name from research.person").fetchall()}
grads = collections.defaultdict(set)      # person_id -> graduation seasons
for pid, s in c.sql("select person_id::varchar, season from research.person_appearance where entity_type = 'Graduates'").fetchall(): grads[pid].add(s)
byname = collections.defaultdict(list)    # surname stem -> persons
for name, (pid, first, fam) in P.items():
    byname[re.sub(r"\s*\d.*$", "", fam or '').strip()[:-1]].append((pid, name, first))
fem_name = lambda n: bool(re.search(r"(а|ая|я)(\s+\d-я)?,", n + ','))  # display_name "Фамилия N-я, Имя"
rows = list(csv.DictReader(open('docs/eval/review_pupil_mentions.csv', encoding='utf-8')))
out = []
for r in rows:
    if not r['linked_now'] or r['historical_block']: continue
    pid, first, fam = P.get(r['linked_now'], (None, None, None))
    base = re.sub(r"\s*\d.*$", "", r['surface']).strip()
    marker_f = bool(re.match(r"(воспитанниц|в-ц|восп-ц|уч-ц|учениц)", r['pupil_marker']))
    marker_m = bool(re.match(r"(воспитанник|в-к|восп-к|уч-к|ученик)", r['pupil_marker']))
    surf_f = bool(re.search(r"(ова|ева|ина|ына|ская|цкая|ой|ою|ей|ая)$", base)); surf_m = bool(re.search(r"(овъ|евъ|инъ|ынъ|скій|цкій)$", base))
    want_f = marker_f or (surf_f and not marker_m); want_m = marker_m or (surf_m and not marker_f)
    is_f = fem_name(r['linked_now'])
    gender_bad = (want_f and not is_f) or (want_m and is_f)
    years_before = int(r['season'][:4]) - int(first[:4]) if first else 0
    grad_ok = any(g >= r['season'] for g in grads.get(pid, ())) or (first and first >= r['season'])
    if not gender_bad and (grad_ok or years_before <= 2): verdict = 'fits'
    else:
        stem = base[:-1] if base[-1:] in 'аъ' else base
        alts = [(p2, n2) for p2, n2, f2 in byname.get(stem[:-1] if len(stem) > 4 else stem, []) + byname.get(stem, [])
                if p2 != pid and fem_name(n2) == (want_f or (not want_m and is_f))
                and any(r['season'] <= g <= f"{int(r['season'][:4]) + 6}-{(int(r['season'][:4]) + 7) % 100:02d}" for g in grads.get(p2, ()))]
        alts = list(dict(alts).items())
        verdict = 'relink' if len(alts) == 1 else ('unlink (no graduate found)' if not alts else 'unlink (several graduates)')
    out.append(dict(mention_id=r['mention_id'], season=r['season'], city=r['city'], page=r['printed_page'], surface=r['surface'],
                    marker=r['pupil_marker'], linked_now=r['linked_now'], first_listed=first or '', gender_clash='yes' if gender_bad else '',
                    verdict=verdict, proposed=(alts[0][1] if verdict == 'relink' else ''), proposed_id=(alts[0][0] if verdict == 'relink' else ''),
                    context=r['context']))
w = csv.DictWriter(open(f'{D}/pupil_links.csv', 'w', encoding='utf-8', newline=''), fieldnames=list(out[0]), lineterminator='\n')
w.writeheader(); w.writerows(out)
print('linked pupil mentions (non-historical):', len(out)); print(collections.Counter(o['verdict'] for o in out).most_common())
print('gender clashes among doubtful:', sum(1 for o in out if o['verdict'] != 'fits' and o['gender_clash']))
