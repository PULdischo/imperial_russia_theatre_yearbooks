"""Compose final (institution, heading_path) per ProductionTeam row.
Priority: manual spec > agent correction (assign.json) > proposal (+ container heading lifted from inst).
Writes /tmp/audit9/final.json  {page: {eNNN: [institution, heading_path]}} and prints diagnostics."""
import json, re, sys, collections
sys.path.insert(0, '/tmp/audit8')
import stage2_rules as R

prop = json.load(open('/tmp/audit8/proposal.json'))
assign = json.load(open('/tmp/audit9/assign.json'))
PT = 'productionteam_'

CITY = re.compile(r'^(МОСКВА|С\.-?ПЕТЕРБУРГЪ|С\.-Петербургъ)$', re.I)
THEATRE = re.compile(r'театръ$')
MOSCOW_TH = ('Большой театръ', 'Малый театръ', 'Новый театръ')
SPB_TH = ('Маріинскій театръ', 'Александринскій театръ', 'Михайловскій театръ')
CONTAINERS = {'Мѣстные гардеробы', 'Отдѣлъ гардеробный', 'Машинисты и ихъ помощники', 'Машинисты-механики и ихъ помощники',
              'Отдѣлъ освѣтительный', 'Главный гардеробъ', 'Парикмахеры', 'Отдѣлъ бутафорскій', 'Гардеробмейстерши'}

def strip_end(s): return re.sub(r'[\s.:]+$', '', s.strip())

# ---------------- manual specs ----------------
M = {}
def setm(season_page, es, chain):
    for e in es: M[(PT + season_page, e)] = chain
def th_roles(season_page, es, dept):
    """dept / <proposal hp> (proposal already 'theatre / role')"""
    for e in es:
        r = [x for x in prop[PT + season_page] if x['e'] == 'e%03d' % e][0]
        hp = r['hp']; ins = strip_end(r['inst'] or '')
        if THEATRE.search(ins) and 'театръ' not in hp: hp = ins + ' / ' + hp
        M[(PT + season_page, e)] = dept + ' / ' + hp

setm('1890-91_p003', [21], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ мужскихъ костюмовъ')
setm('1890-91_p003', [22], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ женскихъ костюмовъ')
setm('1890-91_p003', [23], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ головныхъ уборовъ, обуви и бѣлья')
setm('1892-93_p004', [14], 'Мѣстные гардеробы / Гардеробмейстеры / Большой театръ')
setm('1892-93_p004', [15, 16], 'Мѣстные гардеробы / Гардеробмейстеры / Малый театръ')
setm('1893-94_p000', [18], 'Отдѣлъ декораціонный / Машинисты и ихъ помощники / Маріинскій театръ / Машинистъ')
setm('1893-94_p000', [19], 'Отдѣлъ декораціонный / Машинисты и ихъ помощники / Маріинскій театръ / Старшій помощникъ машиниста')
setm('1894-95_p003', [13], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ мужскихъ костюмовъ')
setm('1894-95_p003', [14], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ женскихъ костюмовъ')
setm('1895-96_p001', [9], 'Отдѣлъ освѣтительный / Завѣдывающіе освѣщеніемъ / Александринскій театръ')
setm('1895-96_p001', [10], 'Отдѣлъ освѣтительный / Завѣдывающіе освѣщеніемъ / Михайловскій театръ')
setm('1895-96_p001', [12], 'Отдѣлъ бутафорскій / Бутафоры / Александринскій театръ')
setm('1895-96_p001', [13], 'Отдѣлъ бутафорскій / Бутафоры / Михайловскій театръ')
for e, t in ((1, 'Маріинскій'), (2, 'Александринскій'), (3, 'Михайловскій')):
    setm('1895-96_p002', [e], 'Мѣстные гардеробы / Гардеробмейстеры / %s театръ' % t)
for e, t in ((4, 'Маріинскій'), (5, 'Александринскій'), (6, 'Михайловскій')):
    setm('1895-96_p002', [e], 'Мѣстные гардеробы / Гардеробмейстерши / %s театръ' % t)
setm('1895-96_p003', [8], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ мужскихъ костюмовъ')
setm('1895-96_p003', [9], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ женскихъ костюмовъ')
for e, t in ((19, 'Маріинскій'), (20, 'Александринскій'), (21, 'Михайловскій')):
    setm('1899-00_p002', [e], 'Мѣстные гардеробы / Гардеробмейстерши / %s театръ' % t)
setm('1902-03_p003', [5], 'Отдѣлъ освѣтительный / Большой театръ / Завѣдывающій освѣщеніемъ')
setm('1902-03_p003', [6], 'Отдѣлъ освѣтительный / Большой театръ / Завѣдывающій освѣщеніемъ Малаго театра')
setm('1902-03_p003', [7], 'Отдѣлъ освѣтительный / Новый театръ / Завѣдывающій освѣщеніемъ')
setm('1902-03_p003', [8], 'Отдѣлъ освѣтительный / Новый театръ / Помощникъ завѣдывающаго освѣщеніемъ')
th_roles('1899-00_p001', [21,22,23,24,25], 'Отдѣлъ освѣтительный')
th_roles('1903-04_p001', [6, 7, 8, 9], 'Машинисты-механики и ихъ помощники')
th_roles('1903-04_p002', [1, 2, 3, 4], 'Отдѣлъ гардеробный / Парикмахеры')
for e, t in ((1, 'Большой'), (2, 'Малый'), (3, 'Новый')):
    setm('1903-04_p004', [e], 'Мѣстные гардеробы / Гардеробмейстеры / %s театръ' % t)
for e, t in ((4, 'Большой'), (5, 'Малый'), (6, 'Новый')):
    setm('1903-04_p004', [e], 'Мѣстные гардеробы / Гардеробмейстерши / %s театръ' % t)
for e, t in ((11, 'Большой'), (12, 'Малый'), (13, 'Новый')):
    setm('1904-05_p004', [e], 'Мѣстные гардеробы / Гардеробмейстерши / %s театръ' % t)
for e, t in ((13, 'Маріинскій'), (14, 'Александринскій'), (15, 'Михайловскій')):
    setm('1905-06_p002', [e], 'Мѣстные гардеробы / Гардеробмейстеры / %s театръ' % t)
for e, t in ((16, 'Маріинскій'), (17, 'Александринскій'), (18, 'Александринскій'), (19, 'Михайловскій')):
    setm('1905-06_p002', [e], 'Мѣстные гардеробы / Гардеробмейстерши / %s театръ' % t)
th_roles('1906-07_p003', [5, 6, 7, 8, 9], 'Отдѣлъ декораціонный')
setm('1906-07_p003', [12], 'Отдѣлъ освѣтительный / Завѣдывающій освѣщеніемъ Малаго театра')
setm('1906-07_p004', [3], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ мужскихъ костюмовъ')
setm('1906-07_p004', [4], 'Главный гардеробъ / Смотрительницы отдѣловъ / Отдѣлъ женскихъ костюмовъ')
setm('1906-07_p004', [6], 'Мѣстные гардеробы / Гардеробмейстеры / Большой театръ')
setm('1906-07_p004', [7], 'Мѣстные гардеробы / Гардеробмейстеры / Малый театръ')
setm('1906-07_p004', [10], 'Мѣстные гардеробы / Гардеробмейстерши / Большой театръ')
setm('1906-07_p004', [11], 'Мѣстные гардеробы / Гардеробмейстерши / Малый театръ')
setm('1906-07_p004', [12], 'Мѣстные гардеробы / Гардеробмейстерши / Новый театръ')
th_roles('1907-08_p001', [1, 2, 3, 4, 5, 6, 7], 'Машинисты-механики и ихъ помощники')
# lighting continuation rows: Отдѣлъ освѣтительный / theatre / role (role from proposal, last segment)
for e in range(12, 19):
    r = [x for x in prop[PT + '1907-08_p001'] if x['e'] == 'e%03d' % e][0]
    th, role = r['hp'].split(' / ')[-2:]
    setm('1907-08_p001', [e], 'Отдѣлъ освѣтительный / %s / %s' % (th, role))
th_roles('1907-08_p001', [21, 22], 'Отдѣлъ бутафорскій')
for e, t in ((4, 'Михайловскій'), (5, 'Михайловскій'), (6, 'Маріинскій'), (7, 'Маріинскій'), (8, 'Александринскій'), (9, 'Александринскій')):
    r = [x for x in prop[PT + '1909-10_p000'] if x['e'] == 'e%03d' % e][0]
    role = r['hp'].split(' / ')[-1]
    setm('1909-10_p000', [e], 'Отдѣлъ декораціонный / Машинисты-механики и ихъ помощники / %s театръ / %s' % (t, role))


for e, t, w in ((24, 'Большой', 'Гардеробмейстеры'), (25, 'Малый', 'Гардеробмейстеры'), (26, 'Большой', 'Гардеробмейстерши'), (27, 'Малый', 'Гардеробмейстерши')):
    setm('1890-91_p003', [e], 'Мѣстные гардеробы / %s / %s театръ' % (w, t))
for e, t, w in ((11, 'Маріинскій', 'Гардеробмейстеры'), (12, 'Александринскій', 'Гардеробмейстеры'), (13, 'Михайловскій', 'Гардеробмейстеры'),
                (14, 'Маріинскій', 'Гардеробмейстерши'), (15, 'Александринскій', 'Гардеробмейстерши'), (16, 'Михайловскій', 'Гардеробмейстерши')):
    setm('1903-04_p002', [e], 'Мѣстные гардеробы / %s / %s театръ' % (w, t))

# spelling-only fixes from the section agents (applied to every chain on the page)
PAGE_SPELL = {PT + '1907-08_p001': [('электрическою станціей', 'электрическою станціею'), ('бутафорскою мастерской', 'бутафорской мастерской')]}
GLOBAL_SPELL = [('бутафорскою мастерскою', 'бутафорской мастерской'), ('красильною мастерскою', 'красильной мастерской')]

# ---------------- compose ----------------
def norm_chain(ch):
    segs = [strip_end(s) for s in ch.split(' / ')]
    segs = [s for s in segs if s and not CITY.match(s) and not s.startswith(('Списокъ', 'личный составъ', 'Императорск'))]
    segs = [re.sub(r'(?<!\S)(?:\S ){3,}\S(?!\S)', lambda m: m.group(0).replace(' ', ''), s) for s in segs]
    segs = [R.fix_text(s) for s in segs]
    out = []
    for i, s in enumerate(segs):
        if s == 'Отдѣлъ гардеробный' and i + 1 < len(segs) and segs[i + 1] in ('Главный гардеробъ', 'Мѣстные гардеробы'):
            continue
        out.append(s)
    if out and out[0].startswith(('Парикмахеры','Парикмахеръ')): out.insert(0, 'Отдѣлъ гардеробный')
    elif out and out[0].startswith('Французская'): out[0:0] = ['Отдѣлъ гардеробный', 'Парикмахеры']
    elif out and out[0].startswith('Смотрительницы отдѣловъ'): out.insert(0, 'Главный гардеробъ')
    elif len(out) > 1 and out[0] in MOSCOW_TH and re.match(r'(Машинист|Помощник\w* машин|Старшій помощн|Ст\. помощн|Младшій помощн|И\. д\. машин)', out[1]): out.insert(0, 'Отдѣлъ декораціонный')
    if out and out[0].startswith('Машинисты'):
        out.insert(0, 'Отдѣлъ декораціонный')
    out=[x for seg in out for x in re.split(r'(?:(?<=декораціонный)|(?<=помощники)|(?<=отдѣловъ)|(?<=театръ))[.:]\s+(?=[А-ЯЁ])',seg)]
    # de-duplicate adjacent repeats
    ded = [s for j, s in enumerate(out) if j == 0 or s != out[j - 1]]
    return ' / '.join(ded)

final = {}; src = collections.Counter(); flags = []
for pg, rows in prop.items():
    final[pg] = {}
    for r in rows:
        e = int(r['e'][1:]); key = (pg, e)
        ak = '%s|%d' % (pg, e)
        if key in M: ch = M[key]; src['manual'] += 1
        elif ak in assign:
            ch = assign[ak][0]; src['agent'] += 1
            m = re.match(r'^(.*?)"\s*\(institution (.+?)\)', ch)
            if m:
                ch, th = m.group(1), m.group(2)
                segs = ch.split(' / ')
                if THEATRE.search(th) and th not in segs: segs.insert(len(segs) - 1, th)
                ch = ' / '.join(segs)
            elif '"' in ch: ch = ch.split('"')[0]
        else:
            ch = r['hp'] or ''
            i = strip_end(r['inst'] or '')
            TOP = ('Отдѣлъ', 'Главный гардеробъ', 'Мѣстные', 'Машинисты', 'Парикмахер', 'Смотрительницы', 'Мастерская', 'Французская')
            if i in CONTAINERS and i not in ch.split(' / ') and not ch.startswith(TOP):
                ch = i + (' / ' + ch if ch else '')
            elif THEATRE.search(i) and not re.search(r'театръ', ch) and re.match(r'(Машинист|Помощник|Старшій|Ст\.|Бутафор|Завѣд|Младшій|Мл\.)', ch):
                if ch.startswith('Машинисты'):
                    a = ch.split(' / '); a.insert(1, i); ch = ' / '.join(a)
                else:
                    ch = i + ' / ' + ch
            src['proposal'] += 1
        ins = strip_end(r['inst'] or '')
        if THEATRE.search(ins) and 'театръ' not in ch.split(' / ')[-2:-1] + [''] and not any(THEATRE.search(x) for x in ch.split(' / ')):
            sg = ch.split(' / ')
            if re.match(r'(Машинист|Помощник\w*[- ]машин|Старшій помощн|Ст\. помощн|Младшій помощн|Бутафор|Помощники бутафор|Завѣдывающій (освѣщ|электр)|Помощникъ завѣд)', sg[-1]) and sg[0] in ('Отдѣлъ декораціонный','Отдѣлъ освѣтительный','Отдѣлъ бутафорскій','Машинисты-механики и ихъ помощники','Машинисты и ихъ помощники') or (sg[-1] in ('Гардеробмейстеры','Гардеробмейстерши') and sg[0]=='Мѣстные гардеробы'):
                sg.insert(len(sg) if sg[-1] in ('Гардеробмейстеры','Гардеробмейстерши') else len(sg) - 1, ins); ch = ' / '.join(sg); src['theatre-from-inst'] += 1; flags.append((pg, r['e'], ch))
        ch = norm_chain(ch)
        for a, b in PAGE_SPELL.get(pg, []) + GLOBAL_SPELL: ch = ch.replace(a, b)
        final[pg][r['e']] = [r['inst'], ch, src and None]
json.dump(final, open('/tmp/audit9/final_chain.json', 'w'), ensure_ascii=False, indent=1)
print(dict(src))

json.dump(flags, open('/tmp/audit9/theatre_from_inst.json','w'), ensure_ascii=False, indent=0)
print(len(flags),'theatre-from-inst insertions')

# ---------------- city (institution := city) ----------------
def city_of(inst, ch):
    t = inst or ''
    if re.search(r'МОСКВА', t, re.I): return 'МОСКВА'
    if re.search(r'С\.-?ПЕТЕРБУРГЪ', t, re.I): return 'С.-ПЕТЕРБУРГЪ'
    return None
def th_city(ch):
    for x in ch.split(' / '):
        if x in MOSCOW_TH: return 'МОСКВА'
        if x in SPB_TH: return 'С.-ПЕТЕРБУРГЪ'
    return None
out = {}; conflicts = []; src_city = collections.Counter()
for pg in sorted(prop):
    season = pg.split('_')[1]
    state = 'С.-ПЕТЕРБУРГЪ' if pg.endswith('_p000') else state  # noqa: F821 (first page of a season is St Petersburg)
    out[pg] = {}
    for r in prop[pg]:
        ch = final[pg][r['e']][1]
        mk = city_of(r['inst'], ch); tc = th_city(ch)
        if mk: state = mk; src_city['marker'] += 1
        city = state
        if tc and tc != city:
            conflicts.append((pg[14:], r['e'], city, tc, ch)); city = tc; state = tc; src_city['theatre-override'] += 1
        out[pg][r['e']] = [city, ch]
json.dump(out, open('/tmp/audit9/final.json', 'w'), ensure_ascii=False, indent=1)
print(dict(src_city), len(conflicts), 'city conflicts')
for c in conflicts[:40]: print(c)
cc = collections.Counter(v[0] for p in out.values() for v in p.values()); print(cc)
