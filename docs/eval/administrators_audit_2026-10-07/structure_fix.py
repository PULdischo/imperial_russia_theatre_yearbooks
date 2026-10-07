"""Structure stage (RG, 2026-10-07; Directorate label = option 1). For every Administrators row (1890-91..1909-10):
  institution  := the season's printed list title (the H0 heading of the season's first page, carried over to its other pages);
  heading_path := '<office> / <department / position chain>' with office = 'Дирекція Императорскихъ театровъ' (first lines of each list: officials over BOTH cities) until the first
                  printed office heading, then 'С.-Петербургская Контора Императорскихъ театровъ' / 'Московская Контора Императорскихъ театровъ' as the printed headings change
                  (carried forward across pages: a continuation page has no office heading of its own).
The department/position chain comes from the BLIND READERS' headings (levels 1 non-office / 2 / 3), carried across page breaks (continuation pages do not repeat the department heading), NOT from the stored
chain (which had typos 'Контроры/Контролю', truncated 'X кл', and stuck headings). Unpaired rows inherit the previous row's chain. Dry run unless --write.
Needs compare_result_after.json (reader row <-> stored row pairs) and parsed_reports.json."""
import json, re, os, sys, collections, glob
D = 'docs/eval/administrators_audit_2026-10-07/'; RAW = 'outputs/full_run/raw/'
sys.path.insert(0, D); import adm_common
WRITE = '--write' in sys.argv
P = json.load(open(D + 'parsed_reports.json')); C = json.load(open(D + 'compare_result_after.json'))
DIR = 'Дирекція Императорскихъ театровъ'
SPB = 'С.-Петербургская Контора Императорскихъ театровъ'; MSK = 'Московская Контора Императорскихъ театровъ'
OFFICE_H = re.compile(r'Контор|Контро[лр]|Контрор', re.I)
def office_kind(h):
    if not OFFICE_H.search(h) and not re.search(r'Императорск\w* театр', h): return None
    if re.search(r'Московск|Москв', h): return 'MSK'
    if re.search(r'Петербург', h): return 'SPB'
    return None
def clean(s): return re.sub(r'\s+', ' ', re.sub(r'^[IVX]+\.\s*', '', (s or '').strip())).strip(' .:;')
DEPT_LIKE = re.compile(r'отдѣленіе|отдѣлъ|часть|Бухгалтер|библіотек|Врач|Контора|Хозяйствен|Счетн|Монтиров|Распорядит', re.I)
TITLE_LIKE = re.compile(r'^(Списокъ|СПИСОКЪ|личн)', re.I)
def is_office_segment(seg): return bool(office_kind(seg)) and bool(OFFICE_H.search(seg))
seasons = collections.defaultdict(list)
for pg in P: seasons[pg.split('_')[1]].append(pg)
title = {}; chain = {}; stats = collections.Counter()
CHANC = 'Канцелярскіе чиновники Конторы'
GRADE = re.compile(r'^(Чиновники?|Чиновникъ) (X|XII|XI)\b|^(X|XI|XII) ?(кл|класса)|^Причисленн', re.I)
def seg(t): return re.sub(r'(?<![А-Яа-яЁё])Х(?![А-Яа-яЁё])', 'X', clean(t))   # Roman numeral X typed as Cyrillic Х by a reader
def label(o): return {'DIR': DIR, 'SPB': SPB, 'MSK': MSK}[o]
for se, pgs in seasons.items():
    pgs = sorted(pgs)
    t = [h[1] for h in P[pgs[0]]['heads'] if h[0] == 0]; title[se] = re.sub(r'\s+', ' ', ' '.join(t).replace(' / ', ' ')).strip()
    office = 'DIR'; l1 = None; l2 = None; chancery = {}; last = None
    for pg in pgs:
        pairs = {j: eid for eid, j in C[pg]['pairs']}
        for j, r in enumerate(P[pg]['rows']):
            st = {int(k): v for k, v in r['stack'].items()}
            if 1 in st:
                k = office_kind(st[1])
                if k: office = k; l1 = None
                else: l1 = seg(st[1])
                l2 = seg(st[2]) if 2 in st else None
            elif 2 in st: l2 = seg(st[2])
            h3 = seg(st[3]) if 3 in st else None; d = l2
            # The readers' stacks keep the last department after a new office-level list begins: 'Врачебная часть' (or the mis-levelled
            # 'Старшій врачъ VI кл') stuck above the chancery-grade lists that follow the medical part. A medical department only
            # applies to medical positions; a bare grade list continuing the chancery block is nested under it again.
            u1 = l1
            inner = h3 or d or u1          # innermost printed heading of the row (readers' level numbers vary by page)
            med = bool(inner and re.search(r'врач', inner, re.I) and not re.search(r'часть', inner, re.I))
            if inner and not med:
                if d and re.search(r'врач', d, re.I): d = None
                if u1 and re.search(r'врач', u1, re.I): u1 = None
            if u1 is None and d is None and h3 and GRADE.match(h3) and chancery.get(office): d = CHANC
            if (d and re.match(CHANC, d)) or (h3 and re.match(CHANC, h3)): chancery[office] = True
            elif d or (h3 and not GRADE.match(h3)): chancery[office] = False
            if not any(k in st for k in (1, 2, 3)) and last is not None and last[0] == office:
                u1, d, h3 = None, None, None   # page-start continuation with no heading at all: inherits the previous row's whole chain
                cur = (office, list(last[1]))
            else: cur = (office, [x for x in (u1, d, h3) if x])
            last = cur
            if j in pairs: chain[pairs[j]] = cur
            else: stats['reader row without stored pair'] += 1
log = []; xt = collections.Counter(); pages = {}
for f in sorted(glob.glob(RAW + 'administration_*.raw.json')):
    b = os.path.basename(f)
    if ' ' in b or '1910-11' in b: continue
    pg = b[:-9]; se = pg.split('_')[1]; d = json.load(open(f)); pages[pg] = d
    prev = ('DIR', [])
    for n, ri in adm_common.kept(d['entries']):
        e = d['entries'][ri]; eid = f'{pg}__e{n:03d}'
        if eid in chain: prev = chain[eid]
        else: stats['stored row inherited chain'] += 1
        off, segs = prev
        new_hp = ' / '.join([label(off)] + segs); new_inst = title[se]
        xt[(off, office_kind((e.get('institution') or '') + ' ' + (e.get('heading_path') or '')) or '-')] += 1
        if (e.get('heading_path') or None) != new_hp or (e.get('institution') or None) != new_inst:
            log.append(dict(entry=eid, old_inst=e.get('institution'), old_hp=e.get('heading_path'), new_inst=new_inst, new_hp=new_hp))
            e['heading_path'] = new_hp; e['institution'] = new_inst
print(len(log), 'rows changed;', dict(stats))
print('expected office x office named in the stored text:', dict(xt))
json.dump(log, open(D + 'structure_log.json', 'w'), ensure_ascii=False, indent=1)
if WRITE:
    for pg, d in pages.items():
        tmp = RAW + pg + '.raw.json.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, RAW + pg + '.raw.json')
    print('WRITTEN', len(pages), 'pages')
