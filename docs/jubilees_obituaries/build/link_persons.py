"""Link every person entry in the jubilee/obituary catalogue to a research.person record (proposals only).

Reads the catalogue and the production DuckDB (read-only). Writes build/person_link_proposals.csv (what the
matcher found), then applies build/person_link_decisions.csv (every uncertain case read by hand, with its basis)
and writes jubilees_obituaries_person_links.csv. Nothing in the database or the catalogue is changed.
Proposal methods:
  roster_row      the catalogue row IS a roster death mark: its own roster entry -> person_link
  review_mention  a review notice: the review-mention layer already links a person in that block whose
                  surname matches the notice
  name_unique     exactly one research.person agrees on surname and every initial/name the entry gives,
                  and its attested seasons fit
  ambiguous       more than one record fits (candidates listed) -- needs a reading
  possible        same surname but the given names disagree (or surname equal only with doubled letters
                  collapsed); candidates listed -- needs a reading
  no_record       no record with that surname (most drama/opera people: the rosters do not list them)
Spelling is compared after folding pre-reform letters (ѣ/і/ѳ/ъ etc.) for MATCHING only; nothing is
"corrected", and every proposal keeps the printed name next to the record's name.

Entry ids are the Obsidian builder's (sha1 of season|source_file|name, plus pdf_page|kind off the sections).

Run:  uv run python docs/jubilees_obituaries/build/link_persons.py
"""
import csv, hashlib, os, re, collections
import duckdb

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
DB = os.path.join(REPO, 'outputs/full_run/imperial_theaters.duckdb')
NON_PERSON = {'section_heading_only', 'other', 'work_milestone'}


def entry_id(d):
    if d['source_type'] == 'section':
        s = f"{d['season']}|{d['source_file']}|{d['name_verbatim']}"
    else:
        s = f"{d['season']}|{d['source_file']}|{d['pdf_page']}|{d['kind']}|{d['name_verbatim']}"
    return hashlib.sha1(s.encode()).hexdigest()[:10]


FOLD = str.maketrans({'ѣ': 'е', 'і': 'и', 'ї': 'и', 'ѳ': 'ф', 'ѵ': 'и', 'ё': 'е', 'й': 'и', 'ъ': '', 'ь': ''})
def fold(s): return (s or '').lower().translate(FOLD).replace('-', '').replace(' ', '')

ORD = re.compile(r'\s*\d+-?[йяеаго]+\b\.?')
def season_start(s): return int(s[:4])


def parse_name(raw):
    """-> (family, [given tokens]) from 'Фам., Имя Отч.', 'И. О. Фам.', 'Фам., И. О.', 'г-жа Фам.' etc."""
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', raw)
    s = re.sub(r'(?i)(?<![\w-])(г-ж[аиѣу]|г-н[уаъ]|г\.|М-elle|M-lle|M-r|Mr\.?|M-me|Mme|бар\.|баронъ|баронесса|кн\.|князь|княгиня)\s*', ' ', s)
    s = ORD.sub(' ', s).strip(' ,.;')
    if ',' in s:
        fam, given = s.split(',', 1)
        return fam.strip(), given.split()
    toks = s.split()
    if not toks: return '', []
    inits = [t for t in toks if re.fullmatch(r'[А-ЯЁѲІѢA-Z][а-яёѳіѣa-z]?\.', t)]
    rest = [t for t in toks if t not in inits]
    return (rest[-1] if rest else toks[-1]), inits + rest[:-1]


def squash(s):
    """fold + collapse doubled letters (Кшессинская/Кшесинская) -- for proposing near matches only"""
    return re.sub(r'(.)\1+', r'\1', fold(s))


def given_agrees(given, first, patr):
    """Every given token must agree with the record: an initial with the record's initial, an abbreviation
    («Евг.») with the record's opening letters, a full name with the full name (after folding only)."""
    names = [first or '', patr or '']
    toks = [t for t in given if t.strip('.')]
    for i, t in enumerate(toks[:2]):
        rec = names[i]
        if not rec: continue
        t0, r0 = fold(t.rstrip('.')), fold(rec.rstrip('.'))
        if t.endswith('.') or len(t0) <= 1 or rec.endswith('.') or len(r0) <= 1:
            n = min(len(t0), len(r0))
            if t0[:n] != r0[:n]: return False
        elif t0 != r0:
            return False
    return True


ORD_NUM = re.compile(r'(\d+)-?[йяеаго]+')
def ordinal(s):
    m = ORD_NUM.search(s or ''); return m.group(1) if m else ''


DEATH_KINDS = ('obituary', 'death_mark', 'death_notice')


def main():
    con = duckdb.connect(DB, read_only=True)
    persons = {r[0]: r for r in con.execute("""select person_id::varchar, display_name, canonical_family_name, canonical_first_name,
        canonical_patronymic, ordinal_suffix, first_attested_season, last_attested_season, person_source from research.person""").fetchall()}
    for pid, r in list(persons.items()):          # production-list records keep their initials only in display_name
        if not r[3] and ',' in (r[1] or ''):
            g = r[1].split(',', 1)[1].split()
            persons[pid] = r[:3] + ((g[0] if g else None), (g[1] if len(g) > 1 else None)) + r[5:]
    sup = dict(con.execute("select person_id::varchar, superseded_by_person_id::varchar from entities.person where superseded_by_person_id is not null").fetchall())
    def live(pid):
        seen = set()
        while pid in sup and pid not in seen: seen.add(pid); pid = sup[pid]
        return pid
    # every printed spelling of each person's surname (rosters), for matching variants
    fam_index = collections.defaultdict(set)
    for pid, fam, first, patr in con.execute("""select pl.person_id::varchar, pe.family_name_clean, pe.first_name_clean, pe.patronymic_clean
            from entities.person_link pl join analysis.person_entry pe using(entry_id)""").fetchall():
        fam_index[fold(ORD.sub('', fam or ''))].add(live(pid))
    for pid, r in persons.items():
        fam_index[fold(r[2])].add(pid)
    for pid, pf in con.execute("select person_id::varchar, printed_form from entities.review_person").fetchall():
        fam_index[fold(ORD.sub('', pf))].add(live(pid))
    cities = collections.defaultdict(set); kinds = collections.defaultdict(set)
    for pid, city, et in con.execute("select person_id::varchar, city, entity_type from research.person_appearance").fetchall():
        if city: cities[pid].add(city)
        kinds[pid].add(et)
    roster_rows = collections.defaultdict(list)
    for eid, page, fam, first, patr, pid in con.execute("""select pe.entry_id, pe.page_id, pe.family_name, pe.first_name, pe.patronymic, pl.person_id::varchar
            from raw.person_entry pe left join entities.person_link pl using(entry_id)""").fetchall():
        roster_rows[page].append((eid, fam or '', first or '', patr or '', pid))
    mentions = collections.defaultdict(list)
    for blk, surface, ent in con.execute("""select block_id, surface, entity_id from entities.review_mention
            where mention_type='person' and entity_id is not null""").fetchall():
        mentions[blk].append((surface, ent))

    cat = list(csv.DictReader(open(os.path.join(ROOT, 'jubilees_obituaries_all_entries.csv'), encoding='utf-8')))
    out = []
    for d in cat:
        if d['kind'] in NON_PERSON: continue
        eid = entry_id(d)
        fam, given = parse_name(d['name_verbatim'])
        row = dict(entry_id=eid, source_type=d['source_type'], season=d['season'], kind=d['kind'], relevance=d['relevance'],
                   name_verbatim=d['name_verbatim'], name_latin=d['name_latin'], role=d['role'], troupe_city=d['troupe_city'],
                   dates=d['dates'], source_file=d['source_file'], pdf_page=d['pdf_page'],
                   person_id='', record_name='', record_seasons='', link_method='', status='', candidates='', note='')

        y = season_start(d['season'])

        def put(pid, method, note=''):
            pid = live(pid); r = persons.get(pid)
            row.update(person_id=pid, link_method=method, note=note,
                       record_name=(r[1] + (' ' + r[5] if r and r[5] else '')) if r else '(not in research.person)',
                       record_seasons=f'{r[6]}–{r[7]}' if r else '')
            probs = []
            if r:
                if given and not given_agrees(given, r[3], r[4]): probs.append('given names differ from the record')
                o1, o2 = ordinal(d['name_verbatim']), ordinal(r[5] or r[1])
                if o1 and o2 and o1 != o2: probs.append(f'ordinal {o1} vs record {o2}')
                if d['kind'] in DEATH_KINDS and r[8] == 'roster' and r[7] and season_start(r[7]) > y + 1:
                    probs.append(f'record still on the rosters in {r[7]}, after this death')
            row['status'] = 'needs_reading' if probs else 'proposed'
            if probs: row['note'] = (row['note'] + '; ' if row['note'] else '') + '; '.join(probs)

        # 1. roster death marks: the row's own roster entry
        if d['source_type'] == 'roster':
            want_f = fold(ORD.sub('', fam)); hits = []
            for (re_id, rf, rfi, rp, pid) in roster_rows.get(d['source_file'], []):
                if fold(ORD.sub('', rf)) == want_f and given_agrees(given, rfi, rp): hits.append((re_id, pid))
            if len(hits) == 1 and hits[0][1]:
                put(hits[0][1], 'roster_row', f'roster entry {hits[0][0]}'); out.append(row); continue
            row['note'] = f'roster row not found uniquely on {d["source_file"]} ({len(hits)} hits); fell back to name'

        # 2. review notices: a person the review-mention layer already linked in this block
        if d['source_type'] == 'review':
            m = re.match(r'block (\d+)', d['pdf_page'])
            if m:
                blk = f"{d['source_file']}__b{int(m.group(1)):03d}"
                st = fold(ORD.sub('', fam))[:5]
                ents = {live(e) for s, e in mentions.get(blk, []) if st and fold(s).find(st) >= 0 and live(e) in persons}
                if len(ents) == 1:
                    put(ents.pop(), 'review_mention', f'review-mention link in {blk}'); out.append(row); continue
                if len(ents) > 1:
                    row['note'] = f'{len(ents)} different linked mentions of this surname in {blk}'

        # 3. name match (sections, repertoire annotations, and anything unresolved above)
        if d['source_type'] == 'repertoire':
            ms = re.findall(r'((?:[А-ЯЁѲІѢ]\.\s*){1,2})([А-ЯЁѲІѢ][а-яёѳіѣъь-]+)', d['name_verbatim'])
            if ms: fam, given = ms[-1][1], ms[-1][0].split()
            else:
                g = re.search(r'(?:г-жи|г-жа|г\.|г-на|M-elle|M-lle|M-r|Mme|M-me)\s+([А-ЯЁѲІѢA-Z][\w-]+)', d['name_verbatim'])
                fam, given = (g.group(1), []) if g else ('', [])
        if not fam:
            row.update(link_method='no_name', status='no_record', note=(row['note'] + '; ' if row['note'] else '') + 'no personal name in the entry')
            out.append(row); continue
        # genitive/dative forms in reviews/annotations: also try the stem
        keys = {fold(ORD.sub('', fam))}
        f0 = fold(ORD.sub('', fam))
        for suf, rep in () if d['source_type'] in ('section', 'roster') else (('ои', 'ая'), ('ои', 'ои'), ('ого', 'ии'), ('аго', 'ии'), ('ого', 'ои'), ('аго', 'ои'), ('а', ''), ('ои', 'а'), ('ую', 'ая'), ('у', '')):
            if f0.endswith(suf): keys.add(f0[: -len(suf)] + rep)
        cands = set()
        for k in keys: cands |= fam_index.get(k, set())
        cands = {c for c in cands if c in persons}
        fits = []
        for c in cands:
            r = persons[c]
            if not given_agrees(given, r[3], r[4]): continue
            if given and not r[3] and not r[4]: continue
            o1, o2 = ordinal(d['name_verbatim']), ordinal(r[5] or r[1])
            if o1 and o2 and o1 != o2: continue
            # a dead person cannot first appear >1 season later; a jubilee/obituary person should be attested within ~25 years before
            if r[6] and season_start(r[6]) > y + 1 and d['kind'] in ('obituary', 'death_mark', 'death_notice', 'memorial_feature'): continue
            fits.append(c)
        if len(fits) == 1:
            put(fits[0], 'name_unique', (row['note'] + '; ' if row['note'] else '') + f'surname{" and given names" if given else " only"}')
        elif fits:
            row['link_method'] = 'ambiguous'; row['status'] = 'needs_reading'
            row['candidates'] = ' | '.join(f'{persons[c][1]}{" " + persons[c][5] if persons[c][5] else ""} [{persons[c][6]}–{persons[c][7]}; {"/".join(sorted(cities[c]))}; {"/".join(sorted(k for k in kinds[c] if k))}] {c}' for c in sorted(fits, key=lambda c: persons[c][1]))
        else:
            near = {c for c in cands if not (persons[c][6] and season_start(persons[c][6]) > y + 1 and d['kind'] in ('obituary', 'death_mark', 'death_notice', 'memorial_feature'))}
            if not cands:
                sq = squash(ORD.sub('', fam))
                near = {c for c in persons if squash(persons[c][2]) == sq}
            if near:
                row['link_method'] = 'possible'; row['status'] = 'needs_reading'
                row['candidates'] = ' | '.join(f'{persons[c][1]}{" " + persons[c][5] if persons[c][5] else ""} [{persons[c][6]}–{persons[c][7]}; {"/".join(sorted(cities[c]))}; {"/".join(sorted(k for k in kinds[c] if k))}] {c}' for c in sorted(near, key=lambda c: persons[c][1]))
                row['note'] = (row['note'] + '; ' if row['note'] else '') + ('given names differ from every same-surname record' if cands else 'surname matches only with doubled letters collapsed')
                out.append(row); continue
            row['link_method'] = 'no_record'; row['status'] = 'no_record'
            if cands: row['note'] = (row['note'] + '; ' if row['note'] else '') + f'{len(cands)} same-surname record(s) rejected on given names or dates: ' + '; '.join(sorted(persons[c][1] for c in cands))
        out.append(row)

    path = os.path.join(HERE, 'person_link_proposals.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    print(len(out), 'proposals ->', path)

    # --- apply the read decisions (build/person_link_decisions.csv) -> the catalogue's link file ---------------
    dec = {r['entry_id']: r for r in csv.DictReader(open(os.path.join(HERE, 'person_link_decisions.csv'), encoding='utf-8'))}
    by_name = collections.defaultdict(list)
    for pid, r in persons.items(): by_name[r[1]].append(pid)
    def resolve(spec, row):
        name, _, last = spec.partition('|')
        pool = [c.rsplit(' ', 1)[1] for c in row['candidates'].split(' | ')] if row['candidates'] else []
        hits = [p for p in pool if persons[p][1].startswith(name) or (persons[p][1] + ' ' + (persons[p][5] or '')).startswith(name)]
        if not hits: hits = [p for p in persons if persons[p][1].startswith(name)]
        if last: hits = [p for p in hits if persons[p][7] == last]
        assert len(hits) == 1, (row['entry_id'], spec, [persons[h][1] for h in hits])
        return hits[0]
    final, unused = [], set(dec)
    for row in out:
        d = dec.get(row['entry_id']); unused.discard(row['entry_id'])
        pid, basis = row['person_id'], ''
        if d:
            if d['decision'] == 'link':
                pid = resolve(d['record'], row) if d['record'] else row['person_id']
                assert pid, row['entry_id']
                status = 'linked'
            else:
                pid, status = '', d['decision']
            basis = 'decided 2026-10-22: ' + d['basis']
        elif row['status'] == 'proposed':
            status = 'linked'
            basis = {'roster_row': 'automatic: the death mark\'s own roster entry',
                     'review_mention': 'automatic: the review-mention link in the same block, surname agrees',
                     'name_unique': 'automatic: the only record agreeing on surname and every printed name or initial'}[row['link_method']]
            if row['note']: basis += f" ({row['note']})"
        elif row['status'] == 'no_record':
            status, basis = 'no_record', 'automatic: ' + (row['note'] or 'no record with this surname')
        else:
            status, basis = 'unresolved', row['note']
        r = persons.get(pid)
        final.append(dict(entry_id=row['entry_id'], season=row['season'], source_type=row['source_type'], kind=row['kind'],
                          relevance=row['relevance'], name_verbatim=row['name_verbatim'], link_status=status, person_id=pid,
                          record_name=(r[1] + (' ' + r[5] if r[5] and r[5] not in r[1] else '')) if r else '',
                          record_seasons=f'{r[6]}–{r[7]}' if r else '', record_source=r[8] if r else '', basis=basis))
    assert not unused, unused
    fpath = os.path.join(ROOT, 'jubilees_obituaries_person_links.csv')
    with open(fpath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(final[0].keys())); w.writeheader(); w.writerows(final)
    c = collections.Counter((r['relevance'], r['link_status']) for r in final)
    for k in sorted(c): print(k, c[k])
    print(len(final), 'person entries ->', fpath)


if __name__ == '__main__':
    main()
