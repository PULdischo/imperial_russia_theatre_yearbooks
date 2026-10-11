"""Cross-check the Repertoire's printed annotations (raw.event_entry.annotation) against the catalogue.

  --export   (needs the database) snapshot every annotated Repertoire event to build/repertoire_annotations.csv
  default    write repertoire_annotations_matched.csv  (annotations with jubilee / farewell / memorial wording, and
             whether the catalogue has the occasion) and repertoire_date_check.csv (each dated review notice in the
             catalogue against the Repertoire's entry for that day)
"""
import csv, os, re, sys, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SNAP = HERE + '/repertoire_annotations.csv'
if '--export' in sys.argv:
    import duckdb
    c = duckdb.connect(os.path.join(ROOT, '..', '..', 'outputs/full_run/imperial_theaters.duckdb'), read_only=True)
    cur = c.sql("""select e.event_id, e.page_id, e.printed_page_number, e.season, e.city, e.theater, e.date_undate, e.time_of_day, e.annotation,
        string_agg(p.performance_title || coalesce(' (' || p.genre || ')', ''), '; ' order by p.performance_order) works
        from raw.event_entry e left join raw.event_entry_performance p using (event_id)
        where e.annotation is not null and trim(e.annotation) <> '' group by all order by e.season, e.date_undate, e.event_id""")
    with open(SNAP, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(cur.fetchall())
    sys.exit()

A = list(csv.DictReader(open(SNAP, encoding='utf-8')))
for a in A:
    a['ann'] = re.sub(r'\s+', ' ', a['annotation']).strip(); a['annl'] = re.sub(r'(.)\1', r'\1', a['ann'].lower())
C = list(csv.DictReader(open(ROOT + '/jubilees_obituaries_all_entries.csv', encoding='utf-8')))

def classify(t):
    l = t.lower()
    if re.search(r"прощальн|adieu", l): return 'farewell'
    if re.search(r'veuve', l): return 'for widow or family'
    if re.search(r'ans de service|années de service', l): return 'jubilee'
    if re.search(r'въ пользу вдов[ыъ]|вдовы и|сиротъ', l): return 'for widow or family'
    if re.search(r'бенефисъ.*(за|въ награду за) *\d+.{0,6}лѣт|лѣті[ея] (службы|.{0,40}дѣятельности)|юбилейный спектакль за|\d+.{0,5}лѣтн\w+ .{0,30}дѣятельности', l): return 'jubilee'
    if re.search(r'въ память|памяти |кончины|со дня рожденія|на памятникъ|памятника', l): return 'memorial'
    if re.search(r'юбил|лѣті[ея]|годовщин|лѣтняго', l): return 'anniversary (institution, work or event)'
    return ''
ENG = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
def cat_dates(s):
    out = []
    for d, m, y in re.findall(r'(\d{1,2}) ([A-Za-z]{3})[a-z]* \[?(\d{4})\]?', s):
        if m.lower() in ENG: out.append(datetime.date(int(y), ENG[m.lower()], int(d)))
    # "17 and 22 Feb 1894"
    for d1, d2, m, y in re.findall(r'(\d{1,2}) and (\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})', s):
        out.append(datetime.date(int(y), ENG[m.lower()], int(d1)))
    return sorted(set(out))
def stem(d):
    n = d['name_verbatim']; m = re.search(r'normalised name: ([^;]+)', d['notes'])
    if m: n = m.group(1)
    n = re.sub(r'\([^)]*\)', ' ', n)
    if ',' in n: s = n.split(',')[0]
    else:
        w = [x for x in re.findall(r'[А-Яа-яѣіѳѵІѲѢ-]+', re.sub(r'\b[А-ЯІѲ][а-яѣіѳ]{0,3}\.', ' ', n)) if len(x) > 3]
        s = w[-1] if w else n
    s = re.sub(r'\s*\d-[йя].*$', '', s.strip()).split()[0] if s.strip() else ''
    return re.sub(r'(.)\1', r'\1', re.sub(r'(ъ|ь|а|ая|ой|ій|аго|ымъ|у|и)$', '', s.lower()))
byday = collections.defaultdict(list)
for a in A:
    if a['date_undate']: byday[(a['city'], a['date_undate'][:10])].append(a)
CITY = lambda d: 'Moscow' if ('_MSK_' in d['source_file'] or 'Moscow' in d['troupe_city']) else 'SP'
def city_ok(a, d): return (a['city'][:3].lower() == 'mos') == (CITY(d) == 'Moscow')

# ---- 1. every dated review/section notice: what does the Repertoire print that day? ----
chk = []
occ = [d for d in C if d['kind'] in ('jubilee', 'farewell', 'memorial_feature', 'work_milestone', 'biographical_feature') and d['source_type'] in ('review', 'section')]
matched_events = collections.defaultdict(list)
for d in occ:
    ds = cat_dates(d['dates']); st = stem(d)
    if not ds or (d['source_type'] == 'section' and d['kind'] != 'jubilee'): continue
    best = None
    for dt in ds:
        if not (1890 <= dt.year <= 1911): continue
        same = [a for a in A if a['date_undate'][:10] == dt.isoformat() and city_ok(a, d)]
        named = [a for a in same if st and len(st) > 3 and st in a['annl']]
        near = [a for a in A if st and len(st) > 3 and st in a['annl'] and city_ok(a, d) and a['date_undate']
                and abs((datetime.date.fromisoformat(a['date_undate'][:10]) - dt).days) <= 400 and a not in named]
        if named: best = ('annotation names the person on that date', named[0], dt); break
        if same and not best: best = ('event annotated that date, person not named', same[0], dt)
        if near and (not best or best[0].startswith('event annotated')):
            cl = [a for a in near if classify(a['ann'])]
            if cl: best = ('person named on a DIFFERENT date', cl[0], dt)
    if best:
        st_, a, dt = best
        if st_.startswith('annotation names'): matched_events[a['event_id']].append(d)
        if st_.startswith('person named on a DIFF'): matched_events[a['event_id']].append(d)
        chk.append([d['season'], d['source_type'], d['kind'], d['name_verbatim'], d['dates'], d['relevance'], st_, a['date_undate'][:10], a['theater'], a['ann'], a['works'], a['page_id']])
    else:
        chk.append([d['season'], d['source_type'], d['kind'], d['name_verbatim'], d['dates'], d['relevance'], 'no annotated Repertoire event for that date', '', '', '', '', ''])
with open(ROOT + '/repertoire_date_check.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['season', 'catalogue_source', 'kind', 'name_in_catalogue', 'dates_in_catalogue', 'relevance', 'status', 'repertoire_date', 'theater', 'annotation', 'works', 'repertoire_page_id']); w.writerows(chk)
print('date check:', collections.Counter(r[6] for r in chk))
for r in chk:
    if 'DIFFERENT' in r[6]: print('  DIFF', r[0], r[3], '|', r[4], '|| rep', r[7], r[9][:70])

# ---- 2. annotations with jubilee / farewell / memorial wording: is the occasion in the catalogue? ----
out = []
for a in A:
    k = classify(a['ann'])
    if not k: continue
    hits = matched_events.get(a['event_id'], [])
    if not hits:   # same person anywhere in the catalogue, same season +-1, any jubilee/farewell/memorial kind
        hits = [d for d in occ if len(stem(d)) > 3 and stem(d) in a['annl'] and abs(int(d['season'][:4]) - int(a['season'][:4])) <= 1
                and d['kind'] in ('jubilee', 'farewell', 'memorial_feature', 'biographical_feature')]
    out.append([a['season'], a['city'], a['theater'], a['date_undate'][:10], k, a['ann'], a['works'], a['page_id'], a['printed_page_number'], a['event_id'],
                'in catalogue' if hits else 'NOT in catalogue', '; '.join(dict.fromkeys(f"{d['source_type']} {d['season']} {d['kind']}: {d['name_verbatim']}" for d in hits))])
with open(ROOT + '/repertoire_annotations_matched.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['season', 'city', 'theater', 'date', 'kind', 'annotation', 'works', 'repertoire_page_id', 'printed_page', 'event_id', 'status', 'catalogue_rows']); w.writerows(out)
print('annotations:', len(out), collections.Counter((r[4], r[10]) for r in out))
