"""Obsidian reading notes for the ballet-relevant jubilees and obituaries: one note per entry,
Russian and English, with the catalogue's metadata as YAML properties.

FOR READING ONLY. The Russian is a single machine reading of each page (qwen3-vl-plus, one pass,
not checked against the scans); the English is a machine translation of it. Quote from the scan.
Generated files: never hand-edit, rebuild instead.

Inputs
  jubilees_obituaries_all_entries.csv           the catalogue (metadata, tiers, page ranges)
  outputs/jubilees_obituaries/raw/*.raw.json    page readings (pipeline/run_reviews.py, single view)
  outputs/jubilees_obituaries/translations.csv  English, keyed by block_id (pipeline/translate_reviews.py)

Steps
  1.  uv run python docs/jubilees_obituaries/build/build_obsidian_notes.py --segment
          cut each page reading into entries, keep the ballet-relevant ones, and write
          outputs/jubilees_obituaries/parsed/review_block.csv for the translator
  2.  uv run python pipeline/translate_reviews.py --parsed-dir outputs/jubilees_obituaries/parsed \
          --out outputs/jubilees_obituaries/translations.csv
  3.  uv run python docs/jubilees_obituaries/build/build_obsidian_notes.py --build
          write the vault to outputs/jubilees_obituaries/obsidian_vault/
"""
from __future__ import annotations
import argparse, collections, csv, datetime, difflib, hashlib, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # docs/jubilees_obituaries
REPO = ROOT.parent.parent
OUT = REPO / 'outputs' / 'jubilees_obituaries'
CAT = ROOT / 'jubilees_obituaries_all_entries.csv'
TEXT_KINDS = ('obituary', 'jubilee', 'memorial_feature', 'biographical_feature')


def reflow(t: str) -> str:
    t = re.sub(r'([^\s-])-\n\s*', r'\1', t)
    return re.sub(r'\s*\n\s*', ' ', t).strip()


def load_page(path: Path) -> dict | None:
    j = json.load(open(path, encoding='utf-8'))
    if 'blocks' not in j:
        raw = j.get('raw_text') or j.get('content') or ''
        try: j = json.loads(re.sub(r'^```(?:json)?|```$', '', raw.strip(), flags=re.M))
        except Exception: return None
    return j


def block_text(b: dict) -> str:
    if b.get('spans'): t = ''.join(s.get('text', '') for s in b['spans'])
    elif b.get('lines'): t = '\n'.join(b['lines'])
    else: t = b.get('text') or ''
    return reflow(t)


def page_stem(source_file: str) -> str:
    sf = source_file[:-4]
    m = re.match(r'(\d{4}) Vol ([IVX-]+)/(.+)', sf)
    return (f'{m.group(1)}_Vol_{m.group(2)}__{m.group(3)}' if m else sf).replace(' ', '_')


def pages_of(d: dict) -> list[int]:
    out = []
    for a, b in re.findall(r'(\d+)(?:\s*-\s*(\d+))?', d['pdf_page']):
        out += list(range(int(a), int(b or a) + 1))
    return out


def norm(s: str) -> str:
    return re.sub(r'[^\w]+', '', s.lower().replace('ё', 'е'), flags=re.U)


def name_keys(d: dict) -> list[str]:
    """strings an entry's opening is expected to start with or contain, most specific first"""
    n = re.sub(r'\[\?\]', '', d['name_verbatim'])
    n = re.sub(r'\([^)]*\)', ' ', n)
    words = [w for w in re.findall(r'[А-Яа-яѣіѳѵІѲѢA-Za-z-]+', n) if len(w) > 2]
    if ',' in n:                                   # "Surname, Given Patronymic"
        sur = re.findall(r'[А-Яа-яѣіѳѵІѲѢ-]+', n.split(',')[0])
        keys = [norm(' '.join(sur[:1] + words[len(sur):len(sur) + 1])), norm(sur[0]) if sur else '']
    else:                                          # "Given Patronymic Surname" or "И. О. Surname"
        keys = [norm(' '.join(words)), norm(words[-1]) if words else '']
    return [k for k in keys if len(k) >= 4]


def read_catalogue() -> list[dict]:
    return list(csv.DictReader(open(CAT, encoding='utf-8')))


def segment() -> None:
    cat = [d for d in read_catalogue() if d['source_type'] == 'section' and d['kind'] in TEXT_KINDS]
    by_file = collections.defaultdict(list)
    for d in cat: by_file[d['source_file']].append(d)
    rows, report = [], []
    for sf, entries in sorted(by_file.items()):
        if not any(e['relevance'] in ('core', 'mentions') for e in entries): continue
        stem = page_stem(sf)
        blocks = []                                # (page, idx, type, text, folio)
        pages_have = set()
        for p in sorted({p for e in entries for p in pages_of(e)}):
            f = OUT / 'raw' / f'jo_{stem}_p{p:02d}.raw.json'
            if not f.exists(): continue
            pg = load_page(f)
            if pg is None: report.append((sf, p, 'UNPARSEABLE PAGE')); continue
            pages_have.add(p)
            for i, b in enumerate(pg.get('blocks', [])):
                t = block_text(b)
                bt = b.get('block_type') or b.get('type') or 'paragraph'
                if bt == 'figure':
                    cap = b.get('caption_text') or b.get('caption') or b.get('caption_spans') or t
                    if isinstance(cap, list): cap = ' '.join((c.get('text', '') if isinstance(c, dict) else str(c)) for c in cap)
                    t = reflow(cap)
                if t: blocks.append([p, i, bt, t, pg.get('printed_folio') or ''])
        # where does each entry start?  first block on its first page whose opening matches its name
        starts = {}
        for ei, e in enumerate(sorted(entries, key=lambda e: (pages_of(e)[:1] or [0])[0])):
            pp = pages_of(e)
            if not pp: continue
            cands = [bi for bi, b in enumerate(blocks) if b[0] in (pp[0], pp[0] + 1) and b[2] != 'figure' and bi not in starts.values()]
            hit = None
            for key in name_keys(e):
                for bi in cands:
                    head = norm(blocks[bi][3])[:len(key) + 12]
                    if head.startswith(key) or (blocks[bi][2] == 'heading' and key in norm(blocks[bi][3])):
                        hit = bi; break
                if hit is not None: break
            if hit is None:                       # fuzzy: best opening match on the first page
                best = (0, None)
                for bi in cands:
                    k = name_keys(e)[-1] if name_keys(e) else ''
                    r = difflib.SequenceMatcher(None, k, norm(blocks[bi][3])[:len(k)]).ratio() if k else 0
                    if r > best[0]: best = (r, bi)
                if best[0] >= 0.8: hit = best[1]
            if hit is not None: starts[id(e)] = hit
        order = sorted((bi, e) for e in entries for bi in [starts.get(id(e))] if bi is not None)
        single = len(entries) == 1                 # a stand-alone article: the whole file is the entry
        for e in entries:
            if e['relevance'] not in ('core', 'mentions'): continue
            if single: lo, hi = 0, len(blocks)
            elif id(e) in starts:
                lo = starts[id(e)]
                later = [bi for bi, _ in order if bi > lo]
                hi = later[0] if later else len(blocks)
                # a caption or portrait sitting just above the heading belongs to this entry
                while lo > 0 and blocks[lo - 1][2] == 'figure' and blocks[lo - 1][0] == blocks[lo][0] and (lo - 1) not in starts.values(): lo -= 1
            else:
                report.append((sf, e['name_verbatim'], 'START NOT FOUND' if pages_have & set(pages_of(e)) else 'pages not read')); continue
            eid = hashlib.sha1(f"{e['season']}|{sf}|{e['name_verbatim']}".encode()).hexdigest()[:10]
            for bi in range(lo, hi):
                p, i, bt, t, folio = blocks[bi]
                rows.append({'block_id': f'{eid}_{bi - lo:03d}', 'entry_id': eid, 'season': e['season'], 'source_file': sf,
                             'name_verbatim': e['name_verbatim'], 'pdf_page': p, 'printed_folio': folio,
                             'block_type': 'figure' if bt == 'figure' else bt, 'text': '' if bt == 'figure' else t,
                             'caption_text': t if bt == 'figure' else ''})
    (OUT / 'parsed').mkdir(parents=True, exist_ok=True)
    with open(OUT / 'parsed' / 'review_block.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    ents = collections.Counter(r['entry_id'] for r in rows)
    print(f'{len(ents)} entries, {len(rows)} blocks, {sum(len(r["text"] or r["caption_text"]) for r in rows):,} characters')
    for r in report: print('  !', *r)
    short = [(r['name_verbatim'], n) for eid, n in ents.items() for r in [next(x for x in rows if x['entry_id'] == eid)] if n == 1]
    print('single-block entries:', len(short))


# ----------------------------------------------------------------------------------------------
# Note design agreed with RG, 2026-10-12:
#   title        "<Kind> - <Surname, Given Patronymic>" in Latin letters (season added only to tell two apart)
#   properties   person, kind, season and volume, printed pages, date of death / jubilee; role and troupe;
#                ballet relevance; author and portrait; scan file and the catalogue's check columns
#   body         details, then the text as a two-column table (Русскій | English), then "My notes"
#   My notes     everything under that heading is RG's and is carried over untouched on every rebuild
# ----------------------------------------------------------------------------------------------
NOTES_MARK = '## My notes'
NOTES_HINT = '<!-- Everything below this line is yours. Rebuilding the vault never changes it. -->'

TR = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p',
      'р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
      'ѣ':'e','і':'i','ѳ':'f','ѵ':'i'}
def translit(s: str) -> str:
    """popular English style: Kshesinskaya, Vsevolozhsky, Lev Ivanovich"""
    s = re.sub(r'(?i)(ск|цк)ій\b', lambda m: m.group(1) + 'Й', s)            # -скій -> -sky
    s = re.sub(r'(?i)[іи]й\b', 'ий', s)
    out = []
    for ch in s:
        lo = ch.lower()
        if ch == 'Й' and out and out[-1] in 'kK': out.append('y'); continue
        t = TR.get(lo, ch)
        out.append(t.capitalize() if ch.isupper() and t else t)
    r = ''.join(out)
    r = re.sub(r'\b(\d+)-(?:y|ya|i|oy)\b', lambda m: m.group(1) + {'1': 'st', '2': 'nd', '3': 'rd'}.get(m.group(1)[-1], 'th'), r)   # 2-й -> 2nd
    r = re.sub(r'iy\b', 'y', r)                                                 # Dmitriy -> Dmitry, Vasiliy -> Vasily
    r = re.sub(r'\bE(?=[a-z])', 'E', r)
    return r

GEN = [(r'скаго$', 'скій'), (r'ского$', 'ской'), (r'ской$', 'ская'), (r'овой$', 'ова'), (r'евой$', 'ева'), (r'иной$', 'ина'), (r'ыной$', 'ына'),
       (r'ова$', 'овъ'), (r'ева$', 'евъ'), (r'ина$', 'инъ'), (r'ына$', 'ынъ'), (r'а$', 'ъ'), (r'ымъ$', 'ъ')]
def person_name(d: dict) -> str:
    """the name in the nominative, 'Surname, Given Patronymic' where the source allows it"""
    n = d['name_verbatim']
    m = re.search(r'normalised name: ([^;]+)', d['notes'])
    if m: n = m.group(1).strip()
    for k, v in FAMILIAR.items():
        if k in n: return v
    n = re.sub(r'\[\?\]', '', n)
    n = re.sub(r'\s*\[[^\]]*\]', '', n)                                       # editorial brackets
    n = re.sub(r'^(г-жи|г-жа|г-жу|Г-жу|г\.|балерины|князя)\s+', '', n).strip()
    n = re.sub(r'\b(князь|баронъ|графъ)\s+', '', n)
    if d['kind'] not in ('work_milestone', 'other'): n = re.sub(r'\s*\([^)]*\)', '', n)     # aliases stay in name_as_printed
    if ',' in n or d['kind'] in ('work_milestone', 'other'): return n
    w = n.split()
    sur_i = next((i for i in range(len(w) - 1, -1, -1) if not re.fullmatch(r'[А-ЯІѲ][а-яѣіѳ]{0,3}\.|\d-[йя]', w[i])), len(w) - 1)
    sur = ' '.join(w[sur_i:]); rest = ' '.join(w[:sur_i])
    return f'{sur}, {rest}' if rest else sur

# Names with an established Latin spelling, or printed in the Yearbook with their own Latin form.
FAMILIAR = {'Перро': 'Perrot, Jules-Joseph', 'Чайковск': 'Tchaikovsky, P. I.', 'Чекетти': 'Cecchetti, Enrico', 'Дель-Эра': "Dell'Era, Antonietta",
            'Замбелли': 'Zambelli, Carlotta', 'Леньяни': 'Legnani, Pierina', 'Кюи': 'Cui, César Antonovich', 'Глинк': 'Glinka, M. I.',
            'Ауэр': 'Auer, Leopold Semenovich', 'Мендес': 'Mendes, José', 'Гримальди': 'Grimaldi, Enrichetta'}
KIND_LABEL = {'obituary': 'Obituary', 'jubilee': 'Jubilee', 'memorial_feature': 'Memorial', 'biographical_feature': 'Article', 'farewell': 'Farewell',
              'death_notice': 'Death notice', 'death_mark': 'Death mark', 'departure': 'Departure', 'work_milestone': 'Work milestone', 'other': 'Occasion'}
SOURCE_LABEL = {'section': 'Yearbook section or article', 'review': 'Season review', 'roster': 'Roster (death mark)', 'repertoire': 'Repertoire table (annotation)'}
RU_MON = {'январ': 1, 'феврал': 2, 'март': 3, 'апрѣл': 4, 'ма[яйѣ]': 5, 'іюн': 6, 'іюл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12}
EN_MON = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}

def find_dates(s: str) -> list[tuple[int, str]]:
    """(position, ISO date) for every full date in the catalogue's free-text dates field; old style, as printed"""
    out = []
    for m in re.finditer(r'(\d{1,2})(?:-го|-е)?\s+([A-Za-zА-Яа-яѣі]+)\.?,?\s+\[?(\d{4})\]?', s):
        mon = m.group(2).lower()
        mo = next((v for k, v in EN_MON.items() if mon.startswith(k)), None) or next((v for k, v in RU_MON.items() if re.match(k, mon)), None)
        if mo and 1 <= int(m.group(1)) <= 31: out.append((m.start(), f'{int(m.group(3)):04d}-{mo:02d}-{int(m.group(1)):02d}'))
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m: out.append((0, m.group(0)))
    return out

def occasion_date(d: dict) -> str:
    s, ds = d['dates'], find_dates(d['dates'])
    if not ds: return ''
    if d['kind'] in ('obituary', 'death_notice', 'death_mark'):
        m = re.search(r'(†|\bd\.|died|сконч|умер)', s)
        if m:
            after = [iso for pos, iso in ds if pos >= m.start()]
            if after: return after[0]
        return '' if len(ds) > 1 and not m else ds[0][1]
    return ds[0][1] if len(ds) == 1 or d['source_type'] in ('review', 'repertoire') else ''

def volume_of(d: dict) -> str:
    m = re.match(r'(\d{4}) Vol ([IVX-]+)/', d['source_file'])
    if m: return f'{m.group(1)}, issue {m.group(2)}'
    m = re.search(r'Supplement(\d)', d['source_file'])
    return f'{d["season"]}, supplement {m.group(1)}' if m else (f'{d["season"]} volume' if d['source_type'] == 'section' else '')

def clean_file(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|#^\[\]«»„“”]', '', s)
    return re.sub(r'\s+', ' ', s).strip().rstrip('.')[:110]

def yq(v: str) -> str:
    return '"' + re.sub(r'\s+', ' ', v).strip().replace('\\', '\\\\').replace('"', '\\"') + '"'

def cell(t: str) -> str:
    return re.sub(r'\s+', ' ', t).replace('|', '\\|').strip()


def findings(d: dict) -> list[str]:
    """only the catalogue remarks RG asked to see: print conflicts and corrections"""
    out = re.findall(r'\[((?:SOURCE CONFLICT|PRINT CONFLICT|DATE CORRECTED|Name corrected)[^\]]*)\]', d['notes'])
    for key, col in (('differs', 'date_check'), ('one day apart', 'date_check')):
        if key in d[col].lower(): out.append(d[col])
    return [re.sub(r'\s+', ' ', x).strip() for x in out]


def build(vault: Path) -> None:
    cat = read_catalogue()
    blocks = collections.defaultdict(list)
    bp = OUT / 'parsed' / 'review_block.csv'
    if bp.exists():
        for r in csv.DictReader(open(bp, encoding='utf-8')): blocks[r['entry_id']].append(r)
    en = {}
    tp = OUT / 'translations.csv'
    if tp.exists(): en = {r['block_id']: r['english'] for r in csv.DictReader(open(tp, encoding='utf-8'))}
    FOLDER = {'obituary': 'Obituaries', 'jubilee': 'Jubilees', 'memorial_feature': 'Articles and memorials', 'biographical_feature': 'Articles and memorials'}
    SHORT = 'Short notices'
    # carry over RG's notes: keyed by the stable entry id stored in each note's properties
    kept = {}
    if vault.exists():
        for f in vault.rglob('*.md'):
            txt = f.read_text(encoding='utf-8')
            m = re.search(r'^entry_id: "?([0-9a-f]{10})"?', txt, flags=re.M)
            if m and NOTES_MARK in txt:
                mine = txt.split(NOTES_MARK, 1)[1]
                mine = mine.replace(NOTES_HINT, '', 1).strip('\n')
                if mine.strip(): kept[m.group(1)] = mine
    entries = []
    for d in cat:
        if d['relevance'] not in ('core', 'mentions'): continue
        eid = hashlib.sha1(f"{d['season']}|{d['source_file']}|{d['name_verbatim']}".encode()).hexdigest()[:10]
        if d['source_type'] != 'section': eid = hashlib.sha1(f"{d['season']}|{d['source_file']}|{d['pdf_page']}|{d['kind']}|{d['name_verbatim']}".encode()).hexdigest()[:10]
        bl = blocks.get(eid, []) if d['source_type'] == 'section' else []
        nm = person_name(d)
        latin = nm if re.match(r'[A-Za-z]', nm) else translit(nm)
        entries.append((d, eid, bl, nm, latin))
    entries = [x for x in entries if x[2]]                # RG 2026-10-12: notes only for entries with a full text
    base_count = collections.Counter(clean_file(f"{KIND_LABEL[d['kind']]} - {latin}") for d, _, _, _, latin in entries)
    for sub in set(FOLDER.values()):
        (vault / sub).mkdir(parents=True, exist_ok=True)
        for f in (vault / sub).glob('*.md'):              # remove only files this builder made
            if re.search(r'^entry_id: "?[0-9a-f]{10}"?', f.read_text(encoding='utf-8'), flags=re.M): f.unlink()
    used, index, made, lost = set(), collections.defaultdict(list), collections.Counter(), dict(kept)
    today = datetime.date.today().isoformat()
    for d, eid, bl, nm, latin in entries:
        title = clean_file(f"{KIND_LABEL[d['kind']]} - {latin}")
        if base_count[title] > 1: title = clean_file(f'{title} ({d["season"]})')
        n, base = 2, title
        while title in used: title = f'{base} {n}'; n += 1
        used.add(title)
        folder = FOLDER.get(d['kind'], SHORT) if bl else SHORT
        od = occasion_date(d)
        date_key = 'death_date' if d['kind'] in ('obituary', 'death_notice', 'death_mark') else 'occasion_date'
        props = [('entry_id', eid), ('person', latin), ('name_as_printed', d['name_verbatim']), ('kind', KIND_LABEL[d['kind']]),
                 ('season', d['season']), ('volume', volume_of(d)), ('printed_pages', d['printed_page']),
                 (date_key, od), ('dates_as_recorded', d['dates']),
                 ('role', d['role']), ('troupe_or_city', d['troupe_city']),
                 ('ballet_relevance', d['relevance']), ('relevance_basis', d['tier_basis']),
                 ('author', d['author']), ('portrait', d['portrait'] if d['source_type'] == 'section' else ''),
                 ('source', SOURCE_LABEL[d['source_type']]), ('scan_file', d['source_file']),
                 ('scan_pages', d['pdf_page'] if d['source_type'] == 'section' else ''),
                 ('date_check', d['date_check']), ('tier_check', d['tier_check'])]
        out = ['---']
        for k, v in props:
            if not v.strip(): continue
            out.append(f'{k}: {v}' if k in ('death_date', 'occasion_date') else f'{k}: {yq(v)}')
        out.append(f'tags: [yearbook/{d["kind"].replace("_", "-")}, ballet/{d["relevance"]}]')
        out += ['---', '', f'# {KIND_LABEL[d["kind"]]} — {latin}', '', f'**{d["name_verbatim"]}**' + (f' · {d["role"]}' if d['role'] else ''), '']
        det = [('Yearbook', volume_of(d) or d['season']), ('Printed pages', d['printed_page']),
               ('Date of death' if date_key == 'death_date' else 'Date', (od + ' (old style)') if od else ''), ('As recorded', d['dates']),
               ('Signed', d['author']), ('Source', SOURCE_LABEL[d['source_type']])]
        out += [f'- **{k}:** {re.sub(chr(10), " ", v)}' for k, v in det if v.strip()] + ['']
        if d['evidence_verbatim'].strip() and not bl:
            out += ['## Notice', '', '| Русскій | English |', '| --- | --- |', f'| {cell(d["evidence_verbatim"])} | {cell(d["evidence_english"])} |', '']
        elif d['evidence_verbatim'].strip():
            out += [f'> [!quote] Ballet connection', f'> {d["evidence_verbatim"].strip()}'] + ([f'> — {d["evidence_english"].strip()}'] if d['evidence_english'].strip() else []) + ['']
        if bl:
            out += ['## Text', '']
            page = None
            for b in bl:
                if b['pdf_page'] != page:
                    page = b['pdf_page']
                    out += ['', f'###### printed p. {b["printed_folio"] or "?"} · scan page {page}', '', '| Русскій | English |', '| --- | --- |']
                ru = b['text'] or b['caption_text']; e = en.get(b['block_id'], '')
                if b['block_type'] == 'figure': ru, e = f'*[illustration: {ru}]*', (f'*[{e}]*' if e else '')
                elif b['block_type'] == 'heading': ru, e = f'**{ru}**', (f'**{e}**' if e else '')
                out.append(f'| {cell(ru)} | {cell(e)} |')
            out.append('')
        fnd = findings(d)
        if fnd: out += ['## Catalogue findings', ''] + [f'- {x}' for x in fnd] + ['']
        if d['see_also'].strip(): out += ['## Other notices of this person in the Yearbooks', ''] + [f'- {x.strip()}' for x in d['see_also'].split(';') if x.strip()] + ['']
        out += ['> [!info] Reading copy — quote from the scan',
                '> ' + ('The Russian is one machine reading of the page and the English a machine translation; neither has been checked. ' if bl else '')
                + f'Generated {today} from the jubilee and obituary catalogue. Edit only under "My notes".', '',
                '---', NOTES_MARK, NOTES_HINT, '']
        if eid in kept: out.append(kept[eid]); lost.pop(eid, None)
        (vault / folder / f'{title}.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
        made[folder] += 1
        index[folder].append((d['season'], title, d['relevance']))
    home = ['# Jubilees and obituaries — ballet set', '',
            f'Generated {today}: one note per ballet-relevant entry of the catalogue. Reading copies; quote from the scans.', '']
    for folder in ['Obituaries', 'Jubilees', 'Articles and memorials']:
        home += [f'## {folder}', '']
        season = None
        for se, t, rel in sorted(index.get(folder, [])):
            if se != season: season = se; home += ['', f'**{se}**', '']
            home.append(f'- [[{t}]]' + (' · mentions' if rel == 'mentions' else ''))
        home.append('')
    (vault / 'Jubilees and obituaries - index.md').write_text('\n'.join(home), encoding='utf-8')
    if lost:      # notes whose entry no longer exists: never drop RG's writing
        (vault / '_orphaned notes.md').write_text('\n\n'.join(f'## entry {k}\n\n{v}' for k, v in lost.items()), encoding='utf-8')
    print(dict(made), '| blocks translated:', sum(1 for bs in blocks.values() for b in bs if b['block_id'] in en), 'of', sum(len(v) for v in blocks.values()),
          '| notes carried over:', len(kept) - len(lost), '| orphaned:', len(lost))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--segment', action='store_true'); ap.add_argument('--build', action='store_true')
    ap.add_argument('--vault', help='folder to write the notes into (default: outputs/jubilees_obituaries/obsidian_vault)')
    a = ap.parse_args()
    if a.segment: segment()
    if a.build: build(Path(a.vault).expanduser() if a.vault else OUT / 'obsidian_vault')
    if not (a.segment or a.build): ap.print_help()
