"""Three content fixes found during the BalletArtists section audit (RG, 2026-10-11: "yes").
All readings are from a blind letter-level read at 5-6x (content_blind_reading.json); I viewed the crops for
Ѳедорова, Сергѣевна, Огневъ and Замбелли myself.

A. The letter Є / є (not a letter of this print) in 28 fields on 17 roster pages. It stood in for different
   letters, so each word was read: Ѳедорова x3, Ѳеоктистова (fita); Сергѣевна (a speck in the bowl of С);
   Огневъ x5, Вильеръ-де-Лиль-Адамъ x2, Граціенко (plain е); and six role / title words in credit summaries
   (Бріенъ, де-Бріенъ, Жанъ-де-Бріенъ, Люсьенъ, Граціелла, Генріэтта, Лье). Fixed in the text and in the parsed
   credit rows. "Лье нарда" keeps its space: the print breaks Льенарда over a line end with no hyphen.
B. balletartists_1901-02_SP_p001, the unnumbered guest between 33 and 34: printed "Замбелли, Карлотта (съ 1 октября
   по 1 декабря 1901 г.)." Stored with list_number "Замбели" and family_name "Карлотта". Now list_number null,
   family_name "Замбелли", first_name "Карлотта".
C. balletartists_1899-00_SP_p000: the note "Прикомандированъ къ Монтировочной части для исполненія обязанностей
   помощника машиниста Маріинскаго театра 1 февраля 1899 г." is printed under "3. Петровъ, Николай Ивановичъ" (assistant
   régisseur). It was stored as a separate person. The note is appended to Петровъ's tenure_note_text and the stray
   row (index 7, entry e008) is removed. Removing a mid-array row shifts e009-e016, so entities.person_link is
   renumbered in the same run (issue #131 rule) and the phantom person's link is deleted.

Dry run by default; --write edits outputs/full_run/raw (copies under backup_content/) and entities.person_link.
usage: uv run python docs/eval/balletartists_section_audit_2026-10-10/fix_content.py [--write]"""
import json, re, shutil, sys, time
from pathlib import Path
import duckdb

HERE = Path(__file__).parent
RAW = Path('outputs/full_run/raw')
WRITE = '--write' in sys.argv
WORDS = {  # stored -> printed
    'Вильєръ-де-Лиль-Адамъ': 'Вильеръ-де-Лиль-Адамъ', 'Грацієнко': 'Граціенко', 'Огнєвъ': 'Огневъ',
    'Єедорова': 'Ѳедорова', 'Єеоктистова': 'Ѳеоктистова', 'Єргѣевна': 'Сергѣевна',
    'Жанъ-де-Брієнь': 'Жанъ-де-Бріенъ', 'де-Врієнь': 'де-Бріенъ', 'Брієнь': 'Бріенъ', 'Графієлла': 'Граціелла',
    'Люсьєнь': 'Люсьенъ', 'Генрієтта': 'Генріэтта', 'Льє': 'Лье',
}
PAGES = ['administration_1892-93_p000', 'administration_1896-97_p000', 'balletartists_1896-97_MSK_p001',
         'balletartists_1897-98_SP_p007', 'balletartists_1900-01_SP_p008', 'balletartists_1901-02_SP_p005',
         'balletartists_1901-02_SP_p007', 'balletartists_1901-02_SP_p008', 'balletartists_1902-03_MSK_p001',
         'balletartists_1902-03_MSK_p005', 'balletartists_1902-03_SP_p008', 'balletartists_1904-05_SP_p008',
         'balletartists_1906-07_SP_p009', 'balletartists_1908-09_SP_p003', 'balletartists_1908-09_SP_p007',
         'balletartists_1909-10_SP_p001', 'balletartists_1909-10_SP_p008']
n_fields = 0


def fix(o):
    global n_fields
    if isinstance(o, str):
        if not re.search('[Єє]', o): return o
        new = o
        for a in sorted(WORDS, key=len, reverse=True): new = new.replace(a, WORDS[a])
        assert not re.search('[Єє]', new), o
        n_fields += 1
        return new
    if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list): return [fix(v) for v in o]
    return o


def save(page, d):
    if WRITE:
        (HERE / 'backup_content').mkdir(exist_ok=True)
        shutil.copy2(RAW / f'{page}.raw.json', HERE / 'backup_content' / f'{page}.raw.json')
        json.dump(d, open(RAW / f'{page}.raw.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


for page in PAGES:                                   # A
    d = json.load(open(RAW / f'{page}.raw.json'))
    before = n_fields
    d = fix(d)
    assert n_fields > before, page
    save(page, d)
print('A:', n_fields, 'fields on', len(PAGES), 'pages')

page = 'balletartists_1901-02_SP_p001'               # B
d = json.load(open(RAW / f'{page}.raw.json')); e = d['entries'][17]
assert e['list_number'] == 'Замбели' and e['family_name'] == 'Карлотта' and e.get('first_name') is None, e
e['list_number'], e['family_name'], e['first_name'] = None, 'Замбелли', 'Карлотта'
save(page, d); print('B: Замбелли, Карлотта')

page = 'balletartists_1899-00_SP_p000'               # C
d = json.load(open(RAW / f'{page}.raw.json')); es = d['entries']
assert len(es) == 16 and es[6]['family_name'] == 'Петровъ' and es[7]['family_name'].startswith('Прикомандированъ къ'), [x['family_name'] for x in es[5:9]]
assert es[6]['tenure_note_text'] == '(съ 16 сентября 1881 г.)', es[6]['tenure_note_text']
es[6]['tenure_note_text'] = ('(съ 16 сентября 1881 г.). Прикомандированъ къ Монтировочной части для исполненія обязанностей '
                             'помощника машиниста Маріинскаго театра 1 февраля 1899 г.')
del es[7]
save(page, d); print('C: note moved to Петровъ; stray row removed; page now', len(es), 'entries')

for i in range(30):
    try: con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not WRITE); break
    except Exception: time.sleep(10)
links = dict(con.execute("select entry_id, person_id::varchar from entities.person_link where entry_id like ?", [page + '__e%']).fetchall())
assert len(links) == 16, len(links)
phantom = links[f'{page}__e008']
assert con.execute("select count(*) from entities.person_link where person_id=?", [phantom]).fetchone()[0] == 1
print('   person_link: delete e008 (phantom person', phantom[:8] + '), rename e009..e016 -> e008..e015')
if WRITE:
    con.execute("delete from entities.person_link where entry_id=?", [f'{page}__e008'])
    for n in range(9, 17):
        con.execute("update entities.person_link set entry_id=? where entry_id=?", [f'{page}__e{n-1:03d}', f'{page}__e{n:03d}'])
    print('   WRITTEN')
con.close()
print('done', 'WRITTEN' if WRITE else '(dry run)')
