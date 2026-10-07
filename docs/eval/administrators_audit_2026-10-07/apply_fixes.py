"""Apply the Administrators audit corrections (2026-10-07) to outputs/full_run/raw/administration_*.raw.json. Dry run unless --write.
Sources: (A) proposals.json = two independent reads agree against the stored text (token-level patches); (B) MANUAL rulings; (C) noble titles moved out of the name fields into
rank_or_title (convention of the ProductionTeam/TheaterSchoolStaff audits: 'князь' / 'графъ, колл. асс.'); (D) removal of the printed note 'Находятся въ вѣдѣніи придворной медицинской части'
(not a person); (E) two rows missing from the stored data, appended at the END of their page array (no later person_link shifts).
Every field edit asserts the old value. Writes apply_log.json and plan.json (removals/adds for relink_administrators.py)."""
import json, re, os, sys, collections
D = 'docs/eval/administrators_audit_2026-10-07/'; RAW = 'outputs/full_run/raw/'
WRITE = '--write' in sys.argv
A = json.load(open(D + 'adjudication.json')); PR = json.load(open(D + 'proposals.json'))
FIELDS = ['family_name', 'first_name', 'patronymic', 'rank_or_title', 'tenure_note_text']
LAT = str.maketrans({'i': 'і', 'θ': 'ѳ', 'Θ': 'Ѳ'})
TITLES = {'князь': 'князь', 'княгиня': 'княгиня', 'графъ': 'графъ', 'графиня': 'графиня', 'баронъ': 'баронъ', 'баронесса': 'баронесса', 'свѣтлѣйшій': 'свѣтлѣйшій'}
pages, log, fails = {}, [], []
def page(pg):
    if pg not in pages: pages[pg] = json.load(open(RAW + pg + '.raw.json'))
    return pages[pg]
import sys; sys.path.insert(0, D); import adm_common
def kept(pg): return adm_common.kept(page(pg)['entries'])
def entry(eid):
    pg, n = eid.rsplit('__e', 1); n = int(n)
    m = dict(kept(pg))
    if n not in m: raise KeyError((pg, n))
    return pg, n, page(pg)['entries'][m[n]]
def setf(eid, f, old, new, why):
    pg, n, e = entry(eid)
    if (e.get(f) or None) != (old or None): fails.append((eid, f, 'stored', e.get(f), 'expected', old)); return
    e[f] = new if new not in ('', None) else None
    log.append(dict(entry=eid, field=f, old=old, new=new, why=why))
def eid_of(iid): return A[iid]['item']['entry_id']
# ---------- (A) auto proposals ----------
SKIP = {'V5.11', 'V5.12', 'V5.23', 'V5.22', 'V5.45', 'V7.23', 'V4.9', 'V7.9', 'V2.2', 'V3.40', 'V6.21', 'V7.33', 'V5.39', 'V3.14', 'V3.15', 'V5.29', 'V7.11', 'V1.39', 'V3.27', 'V3.39', 'V5.35', 'V6.30',
        'V2.18', 'V2.20', 'V2.23', 'V2.24', 'V3.33', 'V4.8', 'V4.39', 'V4.44', 'V6.1', 'V7.12', 'V7.32'}
def apply_prop(p):
    eid = p['entry_id']; pg, n, e = entry(eid)
    for f, es in p['edits'].items():
        cur = e.get(f) or ''
        old_cur = cur
        for kind, old, new in es:
            if kind == 'sub':
                new = re.sub(r'[A-Za-z]', lambda m: m.group(0).translate(LAT), new)
                if re.search(r'(?<!\S)' + re.escape(old) + r'(?!\S)', cur) is None: fails.append((eid, f, 'token not found', old, cur)); continue
                cur = re.sub(r'(?<!\S)' + re.escape(old) + r'(?!\S)', new.replace('\\', '\\\\'), cur, count=1)
            elif kind == 'del':
                if re.search(r'(?<!\S)' + re.escape(old) + r'(?!\S)', cur) is None: fails.append((eid, f, 'token not found (del)', old, cur)); continue
                cur = re.sub(r'(?<!\S)' + re.escape(old) + r'(?!\S)\s*', '', cur, count=1)
            elif kind == 'append':
                cur = (cur.rstrip() + ' ' + new).strip()
        cur = re.sub(r'\s+', ' ', cur).strip(' ,')
        if cur != old_cur.strip(' ,') and cur != old_cur: setf(eid, f, old_cur or None, cur or None, 'A:' + p['item'])
for iid, p in PR.items():
    if iid in SKIP or not p['auto'] or not p['entry_id']: continue
    apply_prop(p)
# ---------- (B) manual rulings ----------
M = [
 ('V1.39', 'family_name', 'Млюдзѣевскій', 'Млодзѣевскій'), ('V1.39', 'rank_or_title', 'ст. сов.', None),
 ('V3.27', 'family_name', 'Млодзѣвскій', 'Млодзѣевскій'), ('V3.27', 'rank_or_title', 'налв. сов.', 'надв. сов.'),
 ('V3.39', 'family_name', 'Фонъ-Бооль', 'Фонъ-Боолъ'),
 ('V5.35', 'patronymic', 'Казимировичъ', 'Казиміровичъ'),
 ('V6.30', 'tenure_note_text', None, None),   # filled below (needs the stored value)
 ('V2.20', 'rank_or_title', 'колл. секр.', 'колл. секр., въ званіи камеръ-юнкера'),
 ('V2.24', 'rank_or_title', 'л. ст. сов.', 'д. ст. сов.'),
 ('V4.8', 'rank_or_title', 'ст. сов.', 'д. ст. сов.'),
 ('V6.1', 'rank_or_title', 'пот. поч. гражд.', 'по найму, пот. поч. гражд.'),
 ('V7.12', 'rank_or_title', 'совѣтникъ', 'ст. совѣтникъ'),
 ('V5.22', 'patronymic', 'Фёдоровичъ', 'Федоровичъ'), ('V5.45', 'patronymic', 'Фёдоровичъ', 'Федоровичъ'),
 ('V2.18', 'family_name', 'Бриліантовъ', 'Бриллiантовъ'.replace('i', 'і')),
]
for iid, f, old, new in M:
    eid = eid_of(iid)
    if iid == 'V6.30': continue
    if eid is None: fails.append((iid, 'no entry')); continue
    setf(eid, f, old, new, 'B:' + iid)
def note_set(iid, new, why):
    eid = eid_of(iid); pg, n, e = entry(eid); old = e.get('tenure_note_text'); setf(eid, 'tenure_note_text', old, new, why)
note_set('V6.30', '(съ 1 іюня 1888 г.). Завѣдывающій центральною библіотекою.', 'B:V6.30')
note_set('V2.18', 'съ 1 августа 1887 г.). Съ 1 сентября 1895 г. назначенъ чиновникомъ особыхъ порученій при Конторѣ.', 'B:V2.18')
note_set('V2.23', '(съ 4 декабря 1892 г.). Оставилъ службу 1 мая 1896 г.', 'B:V2.23')
note_set('V3.33', '(съ 19 сентября 1882 г.). 6 марта 1900 г. назначенъ чиновникомъ особыхъ порученій при Дирекціи.', 'B:V3.33')
note_set('V5.39', '(съ 13 марта 1903 г.). Назначенъ помощникомъ завѣдывающаго постановками 2 апрѣля 1905 г.', 'B:V5.39 (year 1903 from the volumes before and after; the 1904-05 digit is damaged)')
# ---------- (F) recovered rows: names sat in heading_path (parse recovers the name but loses the rank) -> proper raw fields ----------
for f in sorted(os.listdir(RAW)):
    if not f.startswith('administration_') or '1910-11' in f or not f.endswith('.raw.json') or ' ' in f: continue
    pg = f[:-9]
    for i, e in enumerate(page(pg)['entries']):
        if (e.get('family_name') or '').strip(): continue
        m = adm_common.NAME_IN_HEADING_RE.match((e.get('heading_path') or '').strip())
        if not m: continue
        old = dict(family_name=e.get('family_name'), first_name=e.get('first_name'), patronymic=e.get('patronymic'), heading_path=e.get('heading_path'))
        e['family_name'], e['first_name'], e['patronymic'] = m.group(1), m.group(2), m.group(3)
        rest = (m.group(4) or '').strip()
        if rest and not e.get('rank_or_title'): e['rank_or_title'] = rest
        e['heading_path'] = None
        log.append(dict(entry=f'{pg}__ri{i+1}', field='RECOVERED ROW', old=old, new=dict(family_name=m.group(1), first_name=m.group(2), patronymic=m.group(3), rank_or_title=e.get('rank_or_title')), why='F:name was in heading_path'))
# ---------- (C) titles ----------
def title_pass():
    n = 0
    for f in sorted(os.listdir(RAW)):
        if not f.startswith('administration_') or '1910-11' in f or not f.endswith('.raw.json') or ' ' in f: continue
        pg = f[:-9]
        for i, ri in kept(pg):
            e = page(pg)['entries'][ri]
            eid = f'{pg}__e{i:03d}'
            fam, first, pat, rank = (e.get(k) or '' for k in ('family_name', 'first_name', 'patronymic', 'rank_or_title'))
            toks = lambda s: [t for t in s.split()]
            hit = [t for t in toks(fam) + toks(first) + toks(pat) if t.lower() in TITLES and not (fam == 'Принцъ')]
            if not hit: continue
            title = ' '.join(dict.fromkeys(t.lower() for t in hit))
            if title == 'свѣтлѣйшій' : title = 'свѣтлѣйшій князь'
            def strip(s): return ' '.join(t for t in s.split() if t.lower() not in TITLES)
            nf, n1, n2 = strip(fam), strip(first), strip(pat)
            nrank = rank
            # shifted fields: title alone in first_name, first name in patronymic, patronymic in rank (Соллогубъ 1890-91; Канкринъ and Кусовъ 1908-09)
            if not n1 and n2 and rank and re.search(r'(овичъ|евичъ|ичъ)$', rank):
                n1, n2, nrank = n2, rank, ''
            if first.lower() in TITLES and pat and ' ' not in pat.strip() and rank and re.search(r'(овичъ|евичъ|ичъ)$', rank):
                n1, n2, nrank = pat, rank, ''
            # first name and patronymic merged in one field (title removed): move up if needed, then split on the last space
            if n2 and not n1: n1, n2 = n2, ''
            if n1 and not n2 and ' ' in n1: n1, n2 = n1.rsplit(' ', 1)
            if ' ' in n2 and n1 and ' ' not in n1 and n2.count(' ') == 1:      # 'Владиміръ Алексѣевичъ' sat in the patronymic: first name + patronymic
                n1, n2 = n2.split(' ')
            # a patronymic that was pushed into the rank field ('Алексѣевичъ, надв. сов.')
            mm = re.match(r'^(\S+(?:овичъ|евичъ|ичъ))(?:,\s*(.*))?$', nrank or '')
            if mm and not n2: n2, nrank = mm.group(1), (mm.group(2) or '')
            note = e.get('tenure_note_text') or ''; new_note = note
            mn = re.match(r'^((?:д\. )?(?:ст|колл|надв|тит|губ|над)\.\s*(?:сов|асс|рег|секр)\.)\s*(\(.*)$', note)
            if mn and not nrank: nrank, new_note = mn.group(1), mn.group(2)      # rank had slipped into the date note (shifted fields)
            if new_note != note: setf(eid, 'tenure_note_text', note or None, new_note or None, 'C:title (rank slipped into the note)')
            nr = ', '.join(x for x in [title, re.sub(r'^(графъ|баронъ|князь|свѣтлѣйшій князь),?\s*', '', nrank, flags=re.I) if nrank else ''] if x)
            for f, old, new in (('family_name', fam, nf), ('first_name', first, n1), ('patronymic', pat, n2), ('rank_or_title', rank, nr)):
                if (old or '') != (new or ''): setf(eid, f, old or None, new or None, 'C:title')
            n += 1
    return n
n_title = title_pass()
# ---------- (P) service_periods follow the corrected note ----------
MONTHS = 'января|февраля|марта|апрѣля|мая|іюня|іюля|августа|сентября|октября|ноября|декабря'
def reconcile_periods(eid):
    pg, n, e = entry(eid); note = e.get('tenure_note_text') or ''; per = e.get('service_periods') or []
    if len(per) > 1: log.append(dict(entry=eid, field='service_periods', old=per, new='REVIEW (multi-period)', why='P:skipped')); return
    ms = re.search(r'(?:съ|Съ)\s+(\d{1,2}\s+(?:' + MONTHS + r')\s+\d{4})', note)
    me = re.search(r'Оставилъ службу\s+(\d{1,2}\s+(?:' + MONTHS + r')\s+\d{4})', note)
    md = re.search(r'†\s*(\d{1,2}\s+(?:' + MONTHS + r')\s+\d{4})', note)
    # a note whose first date is not introduced by 'съ' (e.g. 'по найму съ ...') still has one start date
    if not ms:
        new = []
    else:
        new = [dict(start_date_text='съ ' + ms.group(1) + ' г.', end_date_text=None, end_type=None)]
        if me: new[0].update(end_date_text=me.group(1) + ' г.', end_type='left service')
        elif md: new[0].update(end_date_text=md.group(1) + ' г.', end_type='died')
    if per:   # keep the original start text style if the date is the same
        old_start = (per[0].get('start_date_text') or '')
        if new and ms and ms.group(1) in old_start: new[0]['start_date_text'] = old_start
        if new and not (me or md) and per[0].get('end_date_text'): new[0].update(end_date_text=per[0]['end_date_text'], end_type=per[0].get('end_type'))
    if new != per:
        e['service_periods'] = new; log.append(dict(entry=eid, field='service_periods', old=per, new=new, why='P:reconcile'))
touched = sorted({l['entry'] for l in log if l['field'] == 'tenure_note_text'})
for eid in touched: reconcile_periods(eid)
# ---------- (D) removals: the printed doctors' note, not a person ----------
rem = collections.defaultdict(list)
for f in sorted(os.listdir(RAW)):
    if not f.startswith('administration_') or '1910-11' in f or not f.endswith('.raw.json') or ' ' in f: continue
    pg = f[:-9]
    for i, ri in kept(pg):
        if 'вѣдѣніи придворной медицинской части' in (page(pg)['entries'][ri].get('family_name') or ''): rem[pg].append((i, ri))
# ---------- (E) missing rows ----------
adds = []
def add_row(pg, ref_eid, data):
    d = page(pg); ref = entry(ref_eid)[2]
    e = {k: None for k in ('institution', 'heading_path', 'list_number', 'family_name', 'first_name', 'patronymic', 'rank_or_title', 'service_class', 'instrument', 'subject_taught', 'tenure_note_text', 'credit_summary_text')}
    e.update(institution=ref.get('institution'), heading_path=ref.get('heading_path')); e.update(data); e['service_periods'] = data.get('_periods', []); e.pop('_periods', None); e['credits'] = []
    d['entries'].append(e); adds.append(dict(entry_id=f"{pg}__e{len(kept(pg)):03d}", family_name=e['family_name'], first_name=e['first_name'], patronymic=e['patronymic']))
    log.append(dict(entry=adds[-1]['entry_id'], field='ADD ROW', old=None, new=f"{e['family_name']}, {e['first_name']} {e['patronymic']}", why='E:missing row'))
add_row('administration_1896-97_p000', 'administration_1896-97_p000__e001', dict(family_name='Всеволожской', first_name='Иванъ', patronymic='Александровичъ', rank_or_title='оберъ-гофмейстеръ', tenure_note_text='(съ 3 сентября 1881 г.).', _periods=[dict(start_date_text='съ 3 сентября 1881 г.', end_date_text=None, end_type=None)]))
add_row('administration_1909-10_p002', 'administration_1909-10_p002__e008', dict(family_name='Покровскій', first_name='Сергѣй', patronymic='Алексѣевичъ', rank_or_title='тит. сов.', tenure_note_text='(съ 9 декабря 1902 г.).', _periods=[dict(start_date_text='съ 9 декабря 1902 г.', end_date_text=None, end_type=None)]))
# removals applied last (descending)
plan = dict(remove={}, add=adds)
for pg, idx in rem.items():
    d = page(pg)
    for n, ri in sorted(idx, reverse=True):
        e = d['entries'][ri]; log.append(dict(entry=f'{pg}__e{n:03d}', field='REMOVE ROW', old=(e.get('family_name') or '')[:60], new=None, why='D:note, not a person')); del d['entries'][ri]
    plan['remove'][pg] = sorted(n for n, _ in idx)
for a in adds:                                           # final database numbers (after the removals above); each new row is the last kept row of its page
    pg = a['entry_id'].split('__')[0]; a['entry_id'] = f"{pg}__e{len(kept(pg)):03d}"
c = collections.Counter(l['why'].split(':')[0] + ':' + l['field'] for l in log)
print(len(log), 'edits;', len(fails), 'fails;', 'title rows', n_title, ';', dict(c))
for f in fails[:40]: print('FAIL', f)
json.dump(log, open(D + 'apply_log.json', 'w'), ensure_ascii=False, indent=1); json.dump(plan, open(D + 'plan.json', 'w'), ensure_ascii=False, indent=1)
if WRITE and not fails:
    for pg, d in pages.items():
        tmp = RAW + pg + '.raw.json.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, RAW + pg + '.raw.json')
    print('WRITTEN', len(pages), 'pages')
