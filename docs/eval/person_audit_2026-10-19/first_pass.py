"""Automatic first pass over the M8 / M9 person-audit worklists (RG, 2026-10-19). Read-only.
Sorts each row into a bucket so that only the doubtful ones go on to scan checks. A bucket is a WORKLIST, never a rule.

M8 (a person's first printed start date varies within one list), per person x list, by season:
  odd_single_date    one season (one entry) disagrees with a date every other season agrees on: likely a print or
                     extraction slip in that season. Flagged `near` when the odd date differs from the usual one
                     only in the day, or in one digit of the year.
  clean_split        the run splits into two unbroken blocks, each with one consistent date (each block 2+ seasons):
                     a change of post / re-engagement, or two people.
  clean_split_near   the same, but the two dates differ only in the day/month or one year digit: the print
                     corrected (or mis-set) its date from that season on.
  clean_split_1908_format  a clean split whose second date starts in 1908-09 or 1909-10, the volumes of the new
                     format (yearbook-issue-structure change): the printed start date was re-based, not a new person.
  same_season_two    two different dates printed in one season (two posts or two orchestras in one volume) and
                     otherwise consistent.
  scattered          anything else.

M9 (listed after a printed leaving or death), per note:
  note_reprinted     every later listing in that list carries the same leaving/death date: the note is being
                     reprinted, not a person listed after leaving.
  reengaged          a later listing prints a start date AFTER the leaving date: returned to service.
  note_printed_late  every later listing without the note comes BEFORE the first season that prints it: the person
                     was still printed after the event and the note caught up a volume late.
  left_one_of_two_posts  in a season that prints the note, the person has another row in the same list without it:
                     the note closes one post, the person keeps the other.
  return_after_gap   first later listing comes after at least one season with no listing.
  continuous_after   listed in the very next season(s) with no new start date and without the note: the note may be
                     misdated, belong to someone else, or the person never actually left.
  ... each with `died` marked, since a death followed by further listings is the strongest signal.

usage: uv run python docs/eval/person_audit_2026-10-19/first_pass.py   (writes M8_first_pass.csv, M9_first_pass.csv here)"""
import collections, csv, re
from pathlib import Path
import duckdb

OUT = Path(__file__).parent
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
SEASONS = [r[0] for r in con.execute("select distinct season from raw.source_pages where season is not null order by 1").fetchall()]
SI = {s: i for i, s in enumerate(SEASONS)}
NONP = set(re.findall(r'"([0-9a-f-]{36})"', Path('pipeline/build_research_model.py').read_text(encoding='utf-8').split('NON_PERSON_IDS = [')[1].split(']')[0]))

ents = con.execute("""
    select cast(pl.person_id as varchar), p.display_name, pe.entry_id, pe.page_id, sp.season, coalesce(sp.city, ''), sp.entity_type,
           pe.tenure_note_text, pe.credit_summary_text
    from entities.person_link pl join entities.person p using(person_id)
    join raw.person_entry pe using(entry_id) join raw.source_pages sp on sp.page_id = pe.page_id
    where p.superseded_by_person_id is null""").fetchall()
svc = collections.defaultdict(list)
for eid, sd, ed, et in con.execute("select entry_id, start_date_undate, end_date_undate, end_type from raw.person_entry_service").fetchall():
    svc[eid].append((str(sd) if sd else None, str(ed) if ed else None, et))

P = collections.defaultdict(list)
for pid, disp, eid, page, season, city, et, note, cred in ents:
    if pid in NONP: continue
    P[pid].append(dict(disp=disp, eid=eid, page=page, season=season, city=city, et=et, note=(note or '') + ' ' + (cred or ''),
                       starts=sorted(s for s, _, _ in svc[eid] if s), ends=[(e, t) for _, e, t in svc[eid] if e]))


def near(a, b):
    if a[:7] == b[:7] or a[:4] == b[:4]:
        return True                                    # only the day (or month) differs
    ya, yb = a[:4], b[:4]
    return sum(x != y for x, y in zip(ya, yb)) == 1 and a[5:] == b[5:]


# ---------------------------------------------------------------- M8
m8 = []
for pid, es in P.items():
    by_list = collections.defaultdict(list)
    for e in es:
        if e['starts']:
            by_list[e['et']].append(e)
    for et, xs in by_list.items():
        dates = collections.Counter(x['starts'][0] for x in xs)
        if len(dates) < 2:
            continue
        per_season = collections.defaultdict(set)
        for x in xs:
            per_season[x['season']].add(x['starts'][0])
        seq = sorted(per_season.items(), key=lambda kv: SI[kv[0]])
        usual, n_usual = dates.most_common(1)[0]
        odd = [(s, d) for s, ds in seq for d in ds if d != usual]
        detail = ''
        if any(len(ds) > 1 for _, ds in seq) and all(usual in ds for _, ds in seq if len(ds) > 1) and \
                len({d for _, ds in seq for d in ds if d != usual}) == 1 and all(ds == {usual} or len(ds) > 1 for _, ds in seq):
            bucket = 'same_season_two'
        elif len(odd) == 1 and len(seq) >= 3:
            bucket = 'odd_single_date'
            detail = f"{odd[0][0]}: {odd[0][1]} (usual {usual})" + (' near' if near(odd[0][1], usual) else '')
        else:
            single = [next(iter(ds)) for _, ds in seq]
            blocks = [k for i, k in enumerate(single) if i == 0 or k != single[i - 1]]
            if all(len(ds) == 1 for _, ds in seq) and len(blocks) == 2 and len(set(blocks)) == 2 and \
                    min(single.count(blocks[0]), single.count(blocks[1])) >= 2:
                bucket = 'clean_split'
                cut = single.index(blocks[1])
                detail = f"{blocks[0]} {seq[0][0]}..{seq[cut - 1][0]} -> {blocks[1]} {seq[cut][0]}..{seq[-1][0]}"
                if near(blocks[0], blocks[1]):
                    detail += ' near'
                    bucket = 'clean_split_near'
                elif seq[cut][0] in ('1908-09', '1909-10'):
                    bucket = 'clean_split_1908_format'
            else:
                bucket = 'scattered'
                detail = ' '.join(f"{s}:{'/'.join(sorted(ds))}" for s, ds in seq)
        years = {d[:4] for d in dates}
        m8.append((bucket, pid[:6], xs[0]['disp'], et, f"{seq[0][0]}..{seq[-1][0]} ({len(seq)})",
                   'different years' if len(years) > 1 else 'same year',
                   '; '.join(f'{d} x{n}' for d, n in dates.most_common()), detail))

order = {'clean_split': 0, 'scattered': 1, 'clean_split_1908_format': 2, 'clean_split_near': 2.5, 'odd_single_date': 3, 'same_season_two': 4}
m8.sort(key=lambda r: (order[r[0]], r[5] != 'different years', r[2]))
with open(OUT / 'M8_first_pass.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['bucket', 'id', 'person', 'list', 'seasons', 'kind', 'start_dates', 'detail'])
    w.writerows(m8)

# ---------------------------------------------------------------- M9
m9 = []
for pid, es in P.items():
    seen = set()
    for e in es:
        for ed, typ in e['ends']:
            if typ not in ('left service', 'died') or len(ed) < 4 or (ed, typ, e['et'], e['city']) in seen:
                continue
            y, m = int(ed[:4]), int(ed[5:7]) if len(ed) >= 7 else 6
            last_ok = f"{y if m >= 7 else y - 1}-{str((y + 1 if m >= 7 else y) % 100).zfill(2)}"
            if last_ok not in SI:
                continue
            same = [x for x in es if x['et'] == e['et'] and x['city'] == e['city']]
            later = sorted({x['season'] for x in same if SI[x['season']] > SI[last_ok]}, key=SI.get)
            if not later:
                continue
            seen.add((ed, typ, e['et'], e['city']))
            later_es = [x for x in same if x['season'] in later]
            carries = [any(e2 == ed for e2, _ in x['ends']) for x in later_es]
            new_start = sorted({s for x in later_es for s in x['starts'] if s > ed})
            gap = SI[later[0]] - SI[last_ok] > 1
            note_seasons_all = {x['season'] for x in same if any(e2 == ed for e2, _ in x['ends'])}
            if all(carries):
                bucket = 'note_reprinted'
            elif new_start:
                bucket = 'reengaged'
            elif gap:
                bucket = 'return_after_gap'
            elif note_seasons_all and all(SI[x['season']] < SI[min(note_seasons_all, key=SI.get)] for x, c in zip(later_es, carries) if not c):
                bucket = 'note_printed_late'
            elif any(x['season'] in note_seasons_all and not any(e2 == ed for e2, _ in x['ends']) for x in same):
                bucket = 'left_one_of_two_posts'
            else:
                bucket = 'continuous_after'
            note_seasons = sorted({x['season'] for x in same if any(e2 == ed for e2, _ in x['ends'])}, key=SI.get)
            m9.append((bucket, 'died' if typ == 'died' else '', pid[:6], e['disp'], e['et'], e['city'], ed, ';'.join(note_seasons),
                       ';'.join(later), ';'.join(new_start), sum(not c for c in carries)))

order9 = {'continuous_after': 0, 'return_after_gap': 1, 'note_printed_late': 1.5, 'left_one_of_two_posts': 2, 'reengaged': 3, 'note_reprinted': 4}
m9.sort(key=lambda r: (order9[r[0]], r[1] != 'died', r[3]))
with open(OUT / 'M9_first_pass.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['bucket', 'died', 'id', 'person', 'list', 'city', 'end_date', 'note_printed_in', 'listed_after', 'new_start_after', 'later_rows_without_note'])
    w.writerows(m9)

c8 = collections.Counter((r[0], r[5]) for r in m8)
print('M8', len(m8), dict(sorted(c8.items())))
print('   odd_single_date near:', sum(1 for r in m8 if r[0] == 'odd_single_date' and r[7].endswith('near')))
c9 = collections.Counter((r[0], r[1]) for r in m9)
print('M9', len(m9), dict(sorted(c9.items())))
