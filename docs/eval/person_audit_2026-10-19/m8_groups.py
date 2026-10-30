"""Second-level grouping of the 115 M8 rows left for checking (clean_split 21 + scattered 94), RG 2026-10-30.
Read-only. Each row (person x list) gets ONE group, first match wins:
  G1 printed_break     the person's entries print a broken service («съ ... по ... и съ ...»): the second start date is
                       a re-engagement the print itself records -- explained by the print.
  G2 post_change       the different start dates go with different headings (posts) in the list: each post has its own
                       start date -- explained by the print.
  G3 near_variants     every date differs from the usual one only in the day/month or in one digit of the year: print
                       variation of one date, no identity question.
  G4 isolated_slips    the usual date covers all but at most two seasons, and the odd seasons are not consecutive: one-off
                       slips (print or extraction) inside a consistent run.
  G5 open              anything else: a real second date with no printed explanation -- these go to the scans.
Writes M8_groups.csv here. A group is a WORKLIST, never a rule.
usage: uv run python docs/eval/person_audit_2026-10-19/m8_groups.py"""
import collections, csv, re
from pathlib import Path
import duckdb

HERE = Path(__file__).parent
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
SEASONS = [r[0] for r in con.execute("select distinct season from raw.source_pages where season is not null order by 1").fetchall()]
SI = {s: i for i, s in enumerate(SEASONS)}
rows = [r for r in csv.DictReader(open(HERE / 'M8_first_pass.csv', encoding='utf-8-sig'))
        if r['bucket'] in ('clean_split', 'scattered')]
BREAK = re.compile(r'по\s+\d')


def near(a, b):
    if a[:4] == b[:4]:
        return True
    return sum(x != y for x, y in zip(a[:4], b[:4])) == 1 and a[5:] == b[5:]


out = []
for r in rows:
    pid = con.execute("select cast(person_id as varchar) from entities.person where cast(person_id as varchar) like ? "
                      "and superseded_by_person_id is null", [r['id'] + '%']).fetchone()[0]
    ents = con.execute("""
        select sp.season, coalesce(pe.heading_path, ''), coalesce(pe.tenure_note_text, ''),
               (select min(cast(s.start_date_undate as varchar)) from raw.person_entry_service s where s.entry_id = pe.entry_id),
               coalesce(a.title_clean, '') || '|' || coalesce(a.rank_clean, '')
        from entities.person_link pl join raw.person_entry pe using(entry_id) join raw.source_pages sp on sp.page_id = pe.page_id
        join analysis.person_entry a on a.entry_id = pe.entry_id
        where pl.person_id = ? and sp.entity_type = ?""", [pid, r['list']]).fetchall()
    norm = lambda x: re.sub(r'[\s:.,]+', ' ', x).strip()      # punctuation and spacing are not a different post
    ents = [(s, norm(h) + ' || ' + norm(tr), t, d) for s, h, t, d, tr in ents if d]
    dates = collections.Counter(e[3] for e in ents)
    usual = dates.most_common(1)[0][0]
    # the post = the whole heading path (orchestra + section), plus the rank/title printed with the name
    leaf = lambda h: h
    heads = collections.defaultdict(set)
    for s, h, t, d in ents:
        heads[d].add(leaf(h))
    if any(BREAK.search(t) for s, h, t, d in ents):
        g, why = 'G1 printed_break', next(t for s, h, t, d in ents if BREAK.search(t))[:90]
    elif len(dates) > 1 and all(not (heads[d] & heads[usual]) for d in dates if d != usual):
        g, why = 'G2 post_change', '; '.join(f"{d}: {sorted(heads[d])[:2]}" for d in dates)[:160]
    elif all(near(d, usual) for d in dates):
        g, why = 'G3 near_variants', ', '.join(dates)
    else:
        odd = sorted({s for s, h, t, d in ents if d != usual}, key=SI.get)
        consecutive = any(SI[b] - SI[a] == 1 for a, b in zip(odd, odd[1:]))
        if len(odd) <= 2 and not consecutive:
            g, why = 'G4 isolated_slips', ', '.join(f"{s}: {d}" for s, h, t, d in sorted(ents, key=lambda e: SI[e[0]]) if d != usual)
        else:
            g, why = 'G5 open', r['detail'][:160]
    out.append((g, r['bucket'], r['id'], r['person'], r['list'], r['seasons'], r['start_dates'], why))

out.sort(key=lambda x: (x[0], x[3]))
with open(HERE / 'M8_groups.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['group', 'first_pass_bucket', 'id', 'person', 'list', 'seasons', 'start_dates', 'why'])
    w.writerows(out)
print(len(out), collections.Counter(x[0] for x in out))
