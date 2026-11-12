"""1911-12 opera / drama production lists vs Repertoire (finding aid; RG 2026-11-12 "go ahead and do it").

Each list entry is matched to research.work by folded title within the list's company (opera -> opera, Русская драма ->
Russian drama of the city's own troupe, Французская драма -> French drama). Its printed dates are compared with the dates
the Repertoire prints a performance of that work or of an excerpt of it (same city, 1911-12). Writes:
  entries.csv   one row per list entry: matched work(s), list dates, Repertoire dates, list-only, Repertoire-only
  rep_only.csv  Repertoire performances (opera / Russian drama / French drama, the cities' own companies) whose
                work has no list entry at all
Run: uv run python docs/eval/scan_audit/compare_opera_drama_lists_1911-12.py (writes entries.csv / rep_only.csv to outputs/c7_1911-12/)
"""
import csv, re, unicodedata, duckdb, os
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = 'outputs/c7_1911-12'; os.makedirs(OUT, exist_ok=True)
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)

def key(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(ch for ch in t if not (unicodedata.combining(ch) and ch != '̆'))
    for a, b in (('ъ', ''), ('ь', ''), ('ѣ', 'е'), ('і', 'и'), ('ѳ', 'ф'), ('ё', 'е'), ('й', 'и')):
        t = t.replace(a, b)
    t = re.sub(r'\(.*?\)', '', t)
    return re.sub(r'[\W_]+', '', t)

COMPANY = {('SP', 'Русская опера'): ('opera', 'St. Petersburg opera'),
           ('Moscow', 'Русская опера'): ('opera', 'Moscow opera'),
           ('SP', 'Русская драма'): ('Russian drama', 'St. Petersburg Russian drama'),
           ('Moscow', 'Русская драма'): ('Russian drama', 'Moscow Russian drama'),
           ('SP', 'Французская драма'): ('French drama', 'St. Petersburg French drama')}

perf = con.execute("""
    select p.performance_id, e.city, cast(e.date as varchar), e.time_of_day, t.canonical_name, p.verbatim_title,
           p.discipline, p.company, w.work_id, w.canonical_title, w.excerpt_of_work_id, pw.canonical_title
    from research.performance p join research.event e using(event_id) join research.theater t using(theater_id)
    join research.work w using(work_id) left join research.work pw on pw.work_id = w.excerpt_of_work_id
    where e.season = '1911-12'""").fetchall()
by_company = defaultdict(list)
for r in perf:
    by_company[(r[6], r[7])].append(r)

def lev(a, b):
    if abs(len(a) - len(b)) > 2: return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1): cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

rows = list(csv.DictReader(open(os.path.join(HERE, '1911-12_opera_drama_lists.csv'), encoding='utf-8')))
out, covered = [], set()
for e in rows:
    disc, comp = COMPANY[(e['city'], e['list'])]
    k = key(e['title_verbatim'])
    cand = [r for r in by_company[(disc, comp)] if key(r[11] or r[9]) == k or key(r[9]) == k]
    if not cand:  # looser: the list title starts the work title or vice versa (subtitles, «или ...»)
        cand = [r for r in by_company[(disc, comp)]
                if (key(r[11] or r[9]).startswith(k) or k.startswith(key(r[11] or r[9]))) and len(k) > 4]
    if not cand:  # looser still: one or two letters differ (spelling variants between the two sources)
        cand = [r for r in by_company[(disc, comp)] if len(k) > 5 and lev(key(r[11] or r[9]), k) <= 2]
    works = sorted({(r[11] or r[9]) for r in cand})
    rep = defaultdict(list)
    for r in cand:
        rep[r[2]].append(f"{r[4]} {r[3]}: {r[5]}")
        covered.add(r[0])
    ld = [d for d in e['dates_iso'].split(';') if d]
    list_only = [d for d in ld if d not in rep]
    rep_only = [f"{d} ({'; '.join(v)})" for d, v in sorted(rep.items()) if d not in ld]
    out.append([e['city'], e['list'], e['printed_page'], e['entry_number'], e['title_verbatim'], ' | '.join(works) or 'NO WORK MATCHED',
                len(ld), len(rep), ';'.join(list_only), ' || '.join(rep_only)])

w = csv.writer(open(os.path.join(OUT, 'entries.csv'), 'w', encoding='utf-8', newline=''))
w.writerow(['city', 'list', 'page', 'no', 'list_title', 'matched_work', 'n_list_dates', 'n_rep_dates', 'list_only_dates', 'rep_only'])
w.writerows(out)
own = [c for c in COMPANY.values()]
ro = [r for r in perf if (r[6], r[7]) in own and r[0] not in covered]
w = csv.writer(open(os.path.join(OUT, 'rep_only.csv'), 'w', encoding='utf-8', newline=''))
w.writerow(['city', 'date', 'session', 'theater', 'verbatim_title', 'discipline', 'work', 'parent'])
for r in sorted(ro, key=lambda r: (r[1], r[2])):
    w.writerow([r[1], r[2], r[3], r[4], r[5], r[6], r[9], r[11]])
n_ok = sum(1 for o in out if not o[8] and not o[9] and o[5] != 'NO WORK MATCHED')
print(f"list entries {len(out)}: exact {n_ok}; no work matched {sum(o[5]=='NO WORK MATCHED' for o in out)}; "
      f"with list-only dates {sum(bool(o[8]) for o in out)}; with Repertoire-only dates {sum(bool(o[9]) for o in out)}; "
      f"Repertoire performances of the listed companies with no list entry: {len(ro)}")
