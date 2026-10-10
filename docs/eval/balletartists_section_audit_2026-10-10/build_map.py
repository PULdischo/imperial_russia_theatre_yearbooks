"""Build the BalletArtists section map (heading_path + institution per entry) from the blind heading readings.

readings.json: one object per page (8 blind readers, 392 pages, 2026-10-10): every printed heading, its kind
(title / section / post / other_list) and the entry it stands before.  This script walks each list's raw entries
in page order, attaches each heading to the entry it stands before (list number + surname), and carries the
current title and heading forward.  It writes nothing to outputs/: it produces section_map.csv and a report.

usage: uv run python docs/eval/balletartists_section_audit_2026-10-10/build_map.py"""
import collections, csv, difflib, glob, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).parent
RAW = Path('outputs/full_run/raw')
R = json.load(open(HERE / 'readings.json'))
FEM = re.compile(r'(а|ая|я)(\s+\d-я)?(\s*\(.*\))?$')


def num(s):
    m = re.match(r'\s*\*?\s*(\d+)', s or '')
    return int(m.group(1)) if m else None


def sur(s):
    s = re.sub(r'^\s*\*?\s*\d+\s*[.)]?\s*', '', s or '')
    s = re.sub(r'\s+', '', s.split(',')[0])            # letter-spaced surnames
    s = re.sub(r'\d-[йя]$', '', s)
    return s.lower().replace('ё', 'е').replace('ѳ', 'ф')


def same(heading_before, entry):
    hn, hs = num(heading_before), sur(heading_before)
    en, es = num(entry.get('list_number')), sur(entry.get('family_name'))
    if not hs or not es:
        return False
    ratio = difflib.SequenceMatcher(None, hs, es).ratio()
    if hn is not None and en is not None:
        return hn == en and ratio >= 0.7
    if hn is None and en is None:
        return ratio >= 0.75
    # one side has a number and the other has none (a list number the extraction dropped, or an unnumbered
    # staff name): only an exact surname counts, so "1. Аистова" never attaches to the régisseur Аистовъ
    return hs == es


lists = collections.OrderedDict()
for f in sorted(glob.glob(str(RAW / 'balletartists_*.raw.json'))):
    p = os.path.basename(f)[:-9]
    lists.setdefault('_'.join(p.split('_')[1:3]), []).append(p)

rows, problems, notes = [], [], []
for key, pages in lists.items():
    title, head, kind = None, None, None
    prev_sec, prev_last = None, None        # the section that was open before the current one, and its last number
    cur_last = None                         # last list number seen in the current section
    for p in pages:
        es = json.load(open(RAW / f'{p}.raw.json'))['entries']
        hs = list(R[p]['headings'])
        used = [False] * len(hs)
        foreign = False
        for i, e in enumerate(es):
            # attach every not-yet-used heading (in reading order) that stands before this entry; a heading whose
            # entry is not in the raw array is skipped and reported, it must not block the ones after it
            local = None                    # a heading matched out of reading order applies to this entry only
            taken = None
            for j, h in enumerate(hs):
                if used[j] or not same(h['before_entry'], e):
                    continue
                # a second heading attaches to the same entry only if it is the very next heading in reading
                # order and names the same entry (title + first post; "Оркестры." + "Музыканты:"). Two posts
                # held by one man (Легатъ, 1905-08) are separate entries and must not both land on the first.
                if taken is not None and not (j == taken + 1 and h['before_entry'] == hs[taken]['before_entry']):
                    continue
                taken = j
                used[j] = True
                in_order = not any(used[k] for k in range(j + 1, len(hs)))   # no later heading has attached yet
                if h['kind'] == 'title':
                    title, head, kind, foreign = h['text'], None, 'title', False
                elif h['kind'] == 'other_list':
                    foreign, head, kind = True, h['text'], 'other_list'
                elif not in_order:
                    local = (h['text'], h['kind'])
                    notes.append((p, i, e.get('list_number'), e.get('family_name'), 'out of print order in the raw array; takes ' + h['text'] + ' for itself only'))
                else:
                    if h['kind'] == 'section' and kind == 'section':
                        prev_sec, prev_last = head, cur_last
                    head, kind, foreign = h['text'], h['kind'], False
                    cur_last = None
            n = num(e.get('list_number'))
            use_head, use_kind = local if local else (head, kind)
            # the raw array is not always in print order: an entry that continues the PREVIOUS section's numbering
            # (and not the current one's) after the next heading has attached still belongs to the previous section
            if not local and kind == 'section' and prev_sec and n is not None and prev_last is not None and n == prev_last + 1 and n != (cur_last or 0) + 1:
                use_head = prev_sec; prev_last = n
                notes.append((p, i, e.get('list_number'), e.get('family_name'), 'continues ' + prev_sec + ' after the next heading in the raw array'))
            elif not local and kind == 'section' and n is not None:
                cur_last = n
            before_title = (title is None)
            rows.append(dict(list=key, page_id=p, idx=i, list_number=e.get('list_number') or '', family_name=e.get('family_name') or '',
                             old_institution=e.get('institution') or '', old_heading=e.get('heading_path') or '',
                             new_institution='' if (foreign or before_title) else title,
                             new_heading='' if (foreign or before_title) else (use_head or ''),
                             kind='foreign' if (foreign or before_title) else (use_kind or ''),
                             fem=int(bool(FEM.search((e.get('family_name') or '').strip())))))
        for j, h in enumerate(hs):
            if not used[j]:
                problems.append((p, 'UNMATCHED heading', h['kind'], h['text'], h['before_entry']))

cols = list(rows[0].keys())
w = csv.DictWriter(open(HERE / 'section_map.csv', 'w', newline='', encoding='utf-8'), cols); w.writeheader(); w.writerows(rows)

print(len(rows), 'entries;', len(problems), 'heading problems (other_list ones are expected: those lists are not in the ballet data)')
for x in problems:
    if x[2] != 'other_list': print('  ', x)
print(len(notes), 'entries re-attached to the previous section by numbering:')
for x in notes: print('  ', x)
# numbering inside each section should rise; anything else is listed for a look at the scan
for key in lists:
    last = {}
    for r in rows:
        if r['list'] != key or r['kind'] != 'section': continue
        n = num(r['list_number'])
        if n is None: print('   no number:', r['page_id'], r['idx'], r['family_name'], '|', r['new_heading'])
        elif r['new_heading'] in last and n <= last[r['new_heading']]: print('   not rising:', r['page_id'], r['idx'], r['list_number'], r['family_name'], '| after', last[r['new_heading']], '|', r['new_heading'])
        if n is not None: last[r['new_heading']] = max(n, last.get(r['new_heading'], 0)) if False else n
# per list: sections and their gender make-up / first number
for key in lists:
    rs = [r for r in rows if r['list'] == key]
    seq = []
    for r in rs:
        k = (r['kind'], r['new_heading'])
        if not seq or seq[-1][0] != k: seq.append([k, 0, 0, r['list_number'], r['page_id'][-4:]])
        seq[-1][1] += 1; seq[-1][2] += r['fem']
    secs = [(k[1][:22], n, f'{f/n:.2f}', first, pg) for k, n, f, first, pg in seq if k[0] in ('section', 'foreign', 'title', '')]
    print(key, secs)
