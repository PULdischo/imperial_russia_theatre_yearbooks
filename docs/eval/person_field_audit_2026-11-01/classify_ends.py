"""Classify every stored service end by RG's rulings (2026-11-02) and propose end_type changes. Read-only; writes
B8_end_types.csv (entry_id, period_order, end_date_text, end_date_undate, end_type_now, end_type_new, basis, sentence).
A1: a break inside a tenure bracket («съ X по Y и съ Z») is typed only where some printed line for the same person gives
    the reason with the same date; otherwise blank.
A2: moving OUT («Назначенъ …», «Переведенъ/а въ …», «Освобожденъ …» from a post) = other; ARRIVING («Переведенъ изъ …»,
    «въ С.-Петербургѣ съ», promoted into the listed post) is never an end; secondments («командирован», «откомандирован»,
    «прикомандирован») are never ends (they go to the assignments table).
«†», «Умеръ/ла», «скончал» = died; «Оставилъ/а службу», «Уволенъ», «вышелъ» = left service.
A8: Graduates' «съ 1-го сентября 1897 года, въ Московскую балетную труппу» is an arrival (no end)."""
import re, csv, collections
from pathlib import Path
import duckdb

D = Path(__file__).parent
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
rows = con.execute("""
    select s.entry_id, s.period_order, s.end_date_text, cast(s.end_date_undate as varchar), s.end_type,
           pe.tenure_note_text, pe.credit_summary_text, pe.entity_type, cast(pl.person_id as varchar),
           (select max(period_order) from raw.person_entry_service s2 where s2.entry_id = s.entry_id)
    from raw.person_entry_service s join raw.person_entry pe using(entry_id) left join entities.person_link pl using(entry_id)
    where s.end_date_text is not null or s.end_type is not null or s.end_date_undate is not null""").fetchall()

MONTHS = 'январ феврал март апрѣл ма іюн іюл август сентябр октябр ноябр декабр'.split()
def date_key(t):
    t = (t or '').lower()
    m = re.search(r'(\d{1,2})[^\d]{0,4}?([а-яѣі]+)\s+(\d{4})', t)
    if m:
        for i, k in enumerate(MONTHS):
            if m.group(2).startswith(k): return f'{m.group(3)}-{i + 1:02d}-{int(m.group(1)):02d}'
    m = re.search(r'(\d{4})', t)
    return m.group(1) if m else None

def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.;)])\s+(?=[А-ЯЁѢІѲ(†])', text or '') if s.strip()]

def classify(sentence, entity_type):
    s = sentence.lower()
    if re.search(r'(откомандир|командирован|прикомандир)', s): return 'not_end:secondment'
    if re.search(r'переведен\w*\s+изъ|въ с\.-петербургѣ съ|въ московскую балетную труппу', s) and entity_type == 'Graduates': return 'not_end:arrival'
    if re.search(r'переведен\w*\s+изъ', s): return 'not_end:arrival'
    if re.search(r'(†|умер|скончал)', s): return 'died'
    if re.search(r'(оставил\w*\s+(службу|преподав|должност|чтен)|уволен|вышел\w* въ отставку|оставила? сл)', s):
        return 'other' if re.search(r'оставил\w*\s+должност', s) else 'left service'
    if re.search(r'(назначен|переведен|освобожден|утвержден|произведен)', s): return 'other'
    return None

# explicit reasons per person, keyed by date
explicit = collections.defaultdict(dict)
for eid, po, edt, eud, et, note, cred, etype, pid, maxpo in rows:
    for s in sentences((note or '') + ' ' + (cred or '')):
        c = classify(s, etype)
        k = date_key(s)
        if c and k and pid and not c.startswith('not_end'):
            explicit[pid].setdefault(k, (c, s))

out = []
for eid, po, edt, eud, et, note, cred, etype, pid, maxpo in rows:
    key = eud or date_key(edt)
    text = (note or '') + ' ' + (cred or '')
    sent = None
    if edt:
        core = re.sub(r'^(съ|по)\s+', '', edt.strip())
        for s in sentences(text):
            if core and core[:-3] in s and not s.startswith('('): sent = s; break
    in_bracket = po < maxpo or (sent is None and re.search(r'по\s+' + re.escape(re.sub(r'^(съ|по)\s+', '', (edt or '').strip())[:8]), text or ''))
    if etype == 'Graduates' and re.search(r'въ Московскую балетную труппу', text or ''):
        new, basis = 'REMOVE', 'A8 graduates: arrival in the troupe'
    elif sent and classify(sent, etype):
        c = classify(sent, etype)
        new, basis = ('REMOVE', 'A2 ' + c) if c.startswith('not_end') else (c, 'own sentence')
    elif in_bracket and re.search(r'по найму', text or ''):
        new, basis = 'other', 'A2 contract hire ended, staff service began (по найму … на службѣ съ)'
    elif in_bracket:
        hit = explicit.get(pid, {}).get(key)
        new, basis = (hit[0], 'A1 break; printed elsewhere: ' + hit[1][:80]) if hit else (None, 'A1 break, no printed reason')
    else:
        new, basis = et, 'unchanged (no sentence found)'
    if (new or None) != (et or None):
        out.append((eid, po, edt or '', eud or '', et or '', new or '', basis, (sent or '')[:120]))

with open(D / 'B8_end_types.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['entry_id', 'period_order', 'end_date_text', 'end_date_undate', 'end_type_now', 'end_type_new', 'basis', 'sentence']); w.writerows(out)
print(len(rows), 'stored ends;', len(out), 'proposed changes')
print(collections.Counter((r[4] or '(blank)', r[5] or '(blank)') for r in out).most_common())
print(collections.Counter(r[6].split(':')[0][:40] for r in out).most_common())
