"""Apply the TheaterSchoolStaff strict tables (issue #133): field fixes, NONPERSON removal, missing rows, institution/heading_path.
Dry run by default; --write writes raw JSON (atomic per page) and the person_link plan. Run with: python3 apply_tss.py [seasons...] [--write]"""
import sys, json, glob, os, re, collections

ROOT = '/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/'
R = ROOT + 'outputs/full_run/raw/'
FIELD_KEY = {'family_name': 'family_name', 'first_name': 'first_name', 'patronymic': 'patronymic', 'list_number': 'list_number',
             'rank_or_title': 'rank_or_title', 'subject_taught': 'subject_taught', 'tenure_note_text': 'tenure_note_text'}
TITLE_DEFAULT = 'Списокъ личнаго состава преподавателей и служащихъ въ Императорскихъ Театральныхъ Училищахъ.'
TITLES = {s: TITLE_DEFAULT for s in ['1891-92', '1892-93', '1893-94', '1894-95', '1895-96', '1896-97', '1897-98', '1898-99', '1899-00', '1900-01',
                                      '1901-02', '1902-03', '1903-04', '1904-05', '1905-06', '1906-07', '1907-08', '1908-09']}
TITLES['1890-91'] = 'Списокъ личнаго состава преподавателей и служащихъ.'
TITLES['1909-10'] = 'Списокъ служащихъ при Императорскихъ Театральныхъ Училищахъ лицъ.'
MOSCOW = 'Императорское Московское Театральное Училище'
SPB = {s: 'Императорское С.-Петербургское Театральное Училище' for s in TITLES}
for s in ('1891-92', '1892-93', '1893-94', '1894-95'): SPB[s] = 'С.-Петербургское Театральное Училище'
DATE_RE = re.compile(r'(?:съ|по|и съ)?\s*(\d{1,2}\s+[а-яѣ]+\s+\d{4})')

EXPLICIT_PERIODS = {
    ('1891-92_p002', 'e019'): [('1 сентября 1888 г.', '1 сентября 1892 г.', 'left service')],
    ('1891-92_p002', 'e026'): [('1 сентября 1888 г.', '15 ноября 1891 г.', 'left service')],
    ('1895-96_p001', 'e032'): [('съ 1 сентября 1893 г.', '16 января 1896 г.', 'died')],
    ('1896-97_p000', 'e013'): [('съ 1 октября 1892 г.', '1 февраля 1897 г.', 'left service')],
    ('1899-00_p001', 'e016'): [('11 сентября 1880 г.', None, None)],
    ('1899-00_p004', 'e007'): [('1 сентября 1889 г.', None, None)],
    ('1900-01_p004', 'e029'): [('1 сентября 1889 г.', None, None)],
    ('1901-02_p004', 'e013'): [('съ 1 сентября 1889 г.', None, None)],
    ('1902-03_p001', 'e020'): [('1 сентября 1881 г.', '1 марта 1903 г.', 'died')],
    ('1904-05_p002', 'e024'): [('съ 1 сентября 1891 г.', '1 сентября 1904 г.', 'left service')],
    ('1905-06_p001', 'e013'): [('съ 11 сентября 1880 г.', '1 сентября 1904 г.', None), ('1 ноября 1905 г.', None, None)],
    ('1905-06_p004', 'e031'): [('съ 1 ноября 1888 г.', '1 января 1906 г.', 'left service')],
}


def nz(v):
    v = (v or '').strip()
    return '' if v in ('-', 'None') else v


def rd(path):
    if not os.path.exists(path): return []
    return [l.rstrip('\n').split('\t') for l in open(path, encoding='utf-8') if l.strip()]


def dates(t):
    return sorted(set(re.findall(r'\d{1,2}\s+[а-яѣ]+\s+\d{4}', t or '')))


def run(seasons, write=False):
    rep = collections.defaultdict(list)           # problems / manual items
    stats = collections.Counter()
    plan = {'remove': {}, 'add': []}              # for the person_link step
    for season in seasons:
        pages = {}
        for f in sorted(glob.glob(R + f'theaterschoolstaff_{season}_p*.raw.json')):
            pg = os.path.basename(f)[:-9]; pages[pg] = json.load(open(f))
        struct = {(r[0], r[1]): r for r in rd(f'/tmp/tss/strict/{season}_struct.tsv')}
        fixes = rd(f'/tmp/tss/strict/{season}_fix.tsv'); missing = rd(f'/tmp/tss/strict/{season}_missing.tsv')
        # ---- field fixes (original index space) ----
        seen = {}
        for r in fixes:
            pg, e, fld, old, new, conf = r[:6]
            if conf == 'PRINT_TYPO': stats['print_typo_skipped'] += 1; rep['print_typos'].append(r); continue
            if conf == 'UNCERTAIN': rep['uncertain_fix'].append(r)
            k = (pg, e, fld)
            if k in seen and seen[k] != new: rep['conflict'].append((k, seen[k], new)); continue
            seen[k] = new
            ent = pages[pg]['entries'][int(e[1:]) - 1]
            cur = nz(str(ent.get(FIELD_KEY[fld]) or ''))
            if cur != nz(old): rep['stored_mismatch'].append((pg, e, fld, cur, old)); continue
            old_ten = ent.get('tenure_note_text')
            val = new if new != '' else None
            if fld == 'list_number': val = new if new else None
            ent[FIELD_KEY[fld]] = val
            stats['field_fix'] += 1
            if fld == 'tenure_note_text':
                if dates(old_ten) != dates(new):
                    key = (pg.split('theaterschoolstaff_')[1][:12], e)
                    if not dates(new): ent.pop('service_periods', None); stats['periods_cleared'] += 1
                    elif key in EXPLICIT_PERIODS:
                        ent['service_periods'] = [{'start_date_text': a, 'end_date_text': b, 'end_type': c} for a, b, c in EXPLICIT_PERIODS[key]]; stats['periods_set'] += 1
                    else: rep['dates_changed_unhandled'].append((pg, e, old_ten, new, ent.get('service_periods')))
        # ---- structure ----
        remove = collections.defaultdict(list)
        for (pg, e), r in struct.items():
            ent = pages[pg]['entries'][int(e[1:]) - 1]
            if r[6] == 'NONPERSON': remove[pg].append(int(e[1:])); continue
            school = SPB[season] if r[2] == 'SPB' else MOSCOW
            hp = ' / '.join([school] + [x for x in r[3:6] if x])
            if ent.get('institution') != TITLES[season]: stats['inst_set'] += 1
            if ent.get('heading_path') != hp: stats['hp_set'] += 1
            ent['institution'] = TITLES[season]; ent['heading_path'] = hp
        for pg, idx in remove.items():
            plan['remove'][pg] = sorted(idx)
            for i in sorted(idx, reverse=True):
                rep['removed'].append((pg, 'e%03d' % i, pages[pg]['entries'][i - 1].get('family_name'), pages[pg]['entries'][i - 1].get('tenure_note_text')))
                del pages[pg]['entries'][i - 1]
            stats['removed'] += len(idx)
        # ---- missing rows (appended at the END of the page array, print order) ----
        byp = collections.defaultdict(list)
        for r in missing: byp[r[0]].append(r)
        for pg, rows in byp.items():
            for r in sorted(rows, key=lambda x: int(x[1])):
                (_, seq, school, l2, l3, l4, num, fam, first, pat, rank, subj, ten, start, end, etype, conf) = (r + [''] * 17)[:17]
                hp = ' / '.join([SPB[season] if school == 'SPB' else MOSCOW] + [x for x in (l2, l3, l4) if x])
                ent = {'institution': TITLES[season], 'heading_path': hp}
                if num: ent['list_number'] = num
                ent['family_name'] = fam; ent['first_name'] = first or None; ent['patronymic'] = pat or None
                if rank: ent['rank_or_title'] = rank
                if subj: ent['subject_taught'] = subj
                if ten: ent['tenure_note_text'] = ten
                if start or end: ent['service_periods'] = [{'start_date_text': start or None, 'end_date_text': end or None, 'end_type': etype or None}]
                pages[pg]['entries'].append(ent)
                n = len(pages[pg]['entries'])
                plan['add'].append(dict(entry_id=f'{pg}__e{n:03d}', family_name=fam, first_name=first, patronymic=pat, conf=conf))
                stats['added'] += 1
        if write:
            for pg, d in pages.items():
                tmp = R + pg + '.raw.json.tmp'
                json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, R + pg + '.raw.json')
    return stats, rep, plan


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    seasons = args or sorted({os.path.basename(f).split('_')[0] for f in glob.glob('/tmp/tss/strict/*_struct.tsv')})
    stats, rep, plan = run(seasons, '--write' in sys.argv)
    print(dict(stats))
    for k, v in rep.items():
        print(f'[{k}] {len(v)}')
        for x in v[:6]: print('   ', str(x)[:260])
    json.dump(plan, open('/tmp/tss/plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
