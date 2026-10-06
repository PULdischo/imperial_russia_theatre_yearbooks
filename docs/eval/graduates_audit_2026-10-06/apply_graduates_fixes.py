"""Apply the Graduates audit corrections (2026-10-06) to outputs/full_run/raw/graduates_*.raw.json. Dry run unless --write.
Every field edit asserts the old value. Rows removed = non-person rows (enrolment counts / prose / headings, plus the Бекъ phantom
from a posting-sentence exception clause). Writes plan.json (removals) for relink_graduates.py.
Name edits: confirmed by two independent blind reads (reader_reports/ + the targeted second read, see README.md)."""
import json, os, re, sys, collections
D = 'docs/eval/graduates_audit_2026-10-06/'
RAW = 'outputs/full_run/raw/'
WRITE = '--write' in sys.argv
G = 'graduates_'
# (page, entry number, field, old, new)
FIELD = [
 (G+'1893-94_p002', 1, 'family_name', 'Галать, Надежда.', 'Галатъ, Надежда.'),
 (G+'1896-97_p003', 11, 'family_name', 'Шипановъ', 'Щипановъ'),
 (G+'1899-00_p001', 20, 'first_name', 'Сергій', 'Сергѣй'),
 (G+'1901-02_p000', 1, 'family_name', 'Карсаѣина, Тамара.', 'Карсавина, Тамара.'),
 (G+'1901-02_p000', 2, 'family_name', 'Кляштъ, Лидія.', 'Кякштъ, Лидія.'),
 (G+'1902-03_p000', 12, 'family_name', 'Леонтъевъ', 'Леонтьевъ'),
 (G+'1904-05_p000', 13, 'first_name', 'Іліодоръ', 'Иліодоръ'),
 (G+'1905-06_p000', 3, 'first_name', 'Лилія', 'Лидія'),
 (G+'1909-10_p000', 10, 'first_name', 'Алексѣй', 'Алексѣ'),            # genuine print truncation (both readers: "Алексѣ.")
 (G+'1890-91_p006', 3, 'family_name', 'Щернваль (по театру Таирова)', 'Шернваль (по театру Таирова)'),
 (G+'1891-92_p002', 10, 'family_name', 'Кульгинъ, Георгій.', 'Кулыгинъ, Георгій.'),
 (G+'1890-91_p002', 7, 'family_name', 'Матвѣева', 'Матвѣева 3-я'),
 (G+'1890-91_p002', 9, 'family_name', 'Эрлеръ', 'Эрлеръ 1-я'),
 (G+'1890-91_p002', 11, 'family_name', 'Легатъ', 'Легатъ 2-й'),
 (G+'1890-91_p002', 14, 'family_name', 'Солянниковъ', 'Солянниковъ 2-й'),
 (G+'1890-91_p002', 8, 'first_name', 'АннаПетровна', 'Анна'),
 (G+'1890-91_p002', 18, 'first_name', 'ЕкатеринаВладиміровна', 'Екатерина'),
]
PATRONYMIC = [(G+'1890-91_p002', 8, 'Петровна'), (G+'1890-91_p002', 18, 'Владиміровна')]   # set patronymic where it was glued into first_name
# Тихомировъ 1892-93 p001 e014: the printed exception clause gives him Moscow, 1 Sept 1893 (the cohort default 1 June 1893 St Petersburg applies to the others)
TIHOMIROV = (G+'1892-93_p001', 14)
# Жуковъ Леонидъ 1908-09 p001 e004: the printed note "(при услов. сдачи одного экзам.)" was stored in rank_or_title; it is a note, not a rank
ZHUKOV = (G+'1908-09_p001', 4)
# non-person rows to remove: (page, entry number); built from compare_result.json + the Бекъ phantom
STAGE_NAME_ROWS = {'e007', 'e009', 'e003'}   # 1890-91 p005 e007/e009 and p006 e003 are real people (stage name in parentheses) -- never removed
def removals():
    res = json.load(open(D + 'compare_result.json'))
    rem = collections.defaultdict(list)
    for pg, d in res.items():
        for eid, fam, note in d['stored_nonperson']:
            if '(по театру' in fam or 'Щернваль' in fam or 'Шернваль' in fam: continue
            rem[pg].append(int(eid[1:]))
    rem[G+'1891-92_p001'].append(1)      # the Бекъ phantom row (posting-sentence exception clause)
    return {k: sorted(v) for k, v in rem.items()}
# school repair
SPB = 'Императорское С.-Петербургское Театральное Училище'; MSK = 'Московское Театральное Училище'
GOOD = re.compile(r'^(Императорское )?(С\.-Петербургское|Московское) Театральное Училище\.?$')
def main():
    pages = {}
    def page(pg):
        if pg not in pages: pages[pg] = json.load(open(RAW + pg + '.raw.json'))
        return pages[pg]
    log, fails = [], []
    def setf(pg, n, k, old, new):
        e = page(pg)['entries'][n - 1]
        if (e.get(k) or None) != (old or None): fails.append((pg, n, k, 'stored', e.get(k), 'expected', old)); return
        e[k] = new; log.append((pg, 'e%03d' % n, k, old, new))
    for pg, n, k, old, new in FIELD: setf(pg, n, k, old, new)
    for pg, n, pat in PATRONYMIC: setf(pg, n, 'patronymic', None, pat)
    # Тихомировъ
    pg, n = TIHOMIROV; e = page(pg)['entries'][n - 1]
    assert e['family_name'] == 'Тихомировъ' and 'кромѣ ученика Тихомирова' in (e.get('tenure_note_text') or ''), 'unexpected Тихомировъ row'
    old = (e['tenure_note_text'], e.get('service_periods'))
    e['tenure_note_text'] = 'съ 1-го сентября 1893 года въ Московскую балетную труппу.'
    e['service_periods'] = [{'start_date_text': 'съ 1-го сентября 1893 года', 'end_date_text': None, 'end_type': None}]
    log.append((pg, 'e%03d' % n, 'tenure_note_text+service_periods', str(old)[:80], e['tenure_note_text']))
    # Жуковъ
    pg, n = ZHUKOV; e = page(pg)['entries'][n - 1]
    assert e['family_name'] == 'Жуковъ' and e.get('rank_or_title') == '(при услов. сдачи одного экзам.)', ('unexpected Жуковъ', e)
    e['tenure_note_text'] = '(при услов. сдачи одного экзам.).'; e['rank_or_title'] = None
    log.append((pg, 'e%03d' % n, 'rank_or_title->tenure_note_text', '(при услов. сдачи одного экзам.)', e['tenure_note_text']))
    # school / institution repair on the remaining person rows
    exp = json.load(open(D + 'expected_school.json'))     # page -> 'SPB'|'MSK' (from the blind readers' PAGE headers)
    sch = lambda s: 'MSK' if re.search(r'Московск|Москв', s or '') and not re.search(r'Петербург', s or '') else 'SPB' if re.search(r'Петербург', s or '') and not re.search(r'Московск|Москв', s or '') else None
    rem = removals()
    nfix = 0
    import glob
    for f in sorted(glob.glob(RAW + 'graduates_*.raw.json')):
        pg = os.path.basename(f)[:-9]
        if '1910-11' in pg: continue
        d = page(pg)
        for i, e in enumerate(d['entries'], 1):
            if i in rem.get(pg, []): continue
            hint = sch((e.get('heading_path') or '') + ' ' + (e.get('institution') or '')) if not GOOD.match((e.get('institution') or '').strip()) else sch(e['institution'])
            want = None
            # explicit per-row school: heading_path of the 1890-91 drama lists names the city ("Въ Москвѣ", "Въ С.-Петербургѣ")
            hp = e.get('heading_path') or ''
            if re.search(r'Москв', hp): want = 'MSK'
            elif re.search(r'Петербург', hp): want = 'SPB'
            else: want = exp.get(pg) if exp.get(pg) in ('SPB', 'MSK') else hint
            if want is None: continue
            label = SPB if want == 'SPB' else MSK
            inst = (e.get('institution') or '').strip()
            if GOOD.match(inst) and sch(inst) == want: continue      # already a clean label of the right school
            e['institution'] = label; nfix += 1
            log.append((pg, 'e%03d' % i, 'institution', inst[:60], label))
    # removals last (descending so indexes stay valid)
    plan = {'remove': {}}
    for pg, idx in rem.items():
        d = page(pg)
        for n in sorted(idx, reverse=True):
            e = d['entries'][n - 1]
            log.append((pg, 'e%03d' % n, 'REMOVE', (e.get('family_name') or '')[:30], (e.get('tenure_note_text') or '')[:50]))
            del d['entries'][n - 1]
        plan['remove'][pg] = sorted(idx)
    print(len(log), 'edits;', len(fails), 'fails;', 'institution fixes', nfix, '; rows removed', sum(len(v) for v in plan['remove'].values()), 'on', len(plan['remove']), 'pages')
    for l in log[:0]: print(l)
    for f in fails: print('FAIL', f)
    json.dump(log, open(D + 'apply_log.json', 'w'), ensure_ascii=False, indent=1)
    json.dump(plan, open(D + 'plan.json', 'w'), ensure_ascii=False, indent=1)
    if WRITE and not fails:
        for pg, d in pages.items():
            tmp = RAW + pg + '.raw.json.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, RAW + pg + '.raw.json')
        print('WRITTEN', len(pages), 'pages')
main()
