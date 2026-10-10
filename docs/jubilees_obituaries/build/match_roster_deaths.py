"""Cross-check the rosters' printed death marks («† 4 іюня 1891 г.» in raw.person_entry.tenure_note_text)
against the obituaries and death notices in catalogue.csv.

Step 1 (needs the database):  uv run python docs/jubilees_obituaries/build/match_roster_deaths.py --export
        writes build/roster_death_marks.csv, a snapshot of the roster rows.
Step 2:                        uv run python docs/jubilees_obituaries/build/match_roster_deaths.py
        writes roster_deaths_matched.csv.
"""
import csv, os, re, sys, difflib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SNAP = HERE + '/roster_death_marks.csv'
SQL = """select regexp_extract(page_id,'\\d{4}-\\d{2}') season, entity_type, family_name, first_name, patronymic,
       rank_or_title, instrument, subject_taught, institution, heading_path, tenure_note_text, page_id, entry_id
from raw.person_entry where tenure_note_text like '%†%' order by 1, 2, 3"""
if '--export' in sys.argv:
    import duckdb
    c = duckdb.connect(os.path.join(ROOT, '..', '..', 'outputs/full_run/imperial_theaters.duckdb'), read_only=True)
    cur = c.sql(SQL)
    with open(SNAP, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(cur.fetchall())
    sys.exit()

MON = {'январ': 1, 'феврал': 2, 'март': 3, 'апрѣл': 4, 'ма[яйѣ]': 5, 'іюн': 6, 'іюл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12}
ENG = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
def dmy_ru(t):
    m = re.search(r'†\s*(\d+)\s*(?:-го)?\s*([а-яѣі]+)\s*(\d{4})', t)
    if not m: return None
    mo = next((v for k, v in MON.items() if re.match(k, m.group(2))), None)
    return (int(m.group(1)), mo, int(m.group(3)))
def dates_in(s):
    """every (day, month, year) the catalogue's dates field mentions, Russian or English month names"""
    out = set(); s = s.lower()
    for d, mon, y in re.findall(r'(\d{1,2})(?:-го|-е)?\s+([a-zа-яѣі]+)\.?,?\s+(\d{4})', s):
        mo = next((v for k, v in MON.items() if re.match(k, mon)), None) or next((v for k, v in ENG.items() if mon.startswith(k)), None)
        if mo: out.add((int(d), mo, int(y)))
    return out
def stem(s): return re.sub(r'(ъ|а|ая|ій|ой|аго)$', '', re.sub(r'\s*\d-[йя].*', '', s).lower()).replace('сс', 'с')
def cat_key(d):
    n = d['name_verbatim']; m = re.search(r'normalised name: ([^;]+)', d['notes'])
    if m: n = m.group(1)
    n = re.sub(r'\([^)]*\)', ' ', n)
    if ',' in n: s, rest = n.split(',', 1)
    else:
        w = [x for x in re.findall(r'[А-Яа-яѣіѳѵІѲѢ-]+', re.sub(r'\b[А-ЯІѲ][а-яѣіѳ]{0,3}\.', ' ', n)) if len(x) > 3]
        s, rest = (w[-1] if w else n), n
    ini = re.search(r'[А-ЯІѲ]', rest.replace(s, ' ', 1))
    return stem(s.split()[0] if s.split() else s), (ini.group(0) if ini else '')

C = [d for d in csv.DictReader(open(ROOT + '/catalogue.csv', encoding='utf-8'))
     if d['kind'] in ('obituary', 'death_notice', 'memorial_feature') and d['source_type'] != 'roster']
CK = [cat_key(d) for d in C]
rows = list(csv.DictReader(open(SNAP, encoding='utf-8')))
out = []
for r in rows:
    k = stem(r['family_name']); ini = (r['first_name'] or ' ')[0]; rd = dmy_ru(r['tenure_note_text'])
    cand = []
    for d, (ck, ci) in zip(C, CK):
        if difflib.SequenceMatcher(None, k, ck).ratio() < 0.86: continue
        if ci and ini.strip() and ci != ini and not (rd and rd in dates_in(d['dates'])): continue   # same surname + same death date overrides a differing given name (Фридрихъ / Ѳедоръ)
        if abs(int(d['season'][:4]) - int(r['season'][:4])) > 1: continue
        fem = lambda n: re.sub(r'\s*\d-[йя].*', '', re.sub(r'\([^)]*\)', '', n).split(',')[0].strip()).endswith(('а', 'ая'))
        if ',' in d['name_verbatim'] and fem(d['name_verbatim']) != fem(r['family_name']): continue
        cand.append(d)
    same_date = [d for d in cand if rd and rd in dates_in(d['dates'])]
    pick = (same_date or cand or [None])[0]
    if pick is None: status = 'not in catalogue'
    elif same_date: status = 'matched, same date'
    else:
        cd = dates_in(pick['dates'])
        status = 'matched, date differs' if cd and rd else 'matched, date not comparable'
    mark = re.search(r'†[^.;)]*(?:г\.)?', r['tenure_note_text']).group(0).strip()
    out.append([r['season'], r['entity_type'], r['family_name'], r['first_name'], r['patronymic'], r['rank_or_title'],
                r['instrument'] or r['subject_taught'], r['heading_path'], mark, r['page_id'], status,
                pick['name_verbatim'] if pick else '', pick['kind'] if pick else '', pick['printed_page'] if pick else '',
                pick['dates'] if pick else '', pick['relevance'] if pick else ''])
with open(ROOT + '/roster_deaths_matched.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['season', 'roster', 'family_name', 'first_name', 'patronymic', 'rank_or_title', 'instrument_or_subject', 'heading_path',
                'death_mark', 'roster_page_id', 'status', 'catalogue_name', 'catalogue_kind', 'catalogue_printed_page', 'catalogue_dates', 'catalogue_relevance'])
    w.writerows(out)
print(len(out), collections.Counter(o[10] for o in out))
print(collections.Counter((o[1], o[10]) for o in out))
for o in out:
    if o[10] in ('matched, date differs',): print('DIFF', o[0], o[1][:6], o[2], o[3], '|', o[8], '||', o[11][:35], '|', o[14][:70])
