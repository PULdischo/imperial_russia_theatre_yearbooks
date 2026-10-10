"""Fix the stuck "Балетмейстеры" heading on 10 BalletArtists pages (221 entries), RG 2026-10-10.

No section heading is printed on these pages (blind scan read of 19 pages, 2026-10-10): each is a
continuation of the season's numbered list of dancers. The stored heading_path "Балетмейстеры" (and,
on four pages, institution "Императорское С.-Петербургское Театральное Училище") was invented by the
extraction. The true heading is the one the run was printed under:
  - a women's run (surnames in -а/-ая, numbering continuing from p000's "Артистки") -> the season's
    printed "Артистки" heading, taken verbatim from that season's p000;
  - a men's run -> the season's printed "Артисты" heading, taken verbatim from the page where the
    men's numbering restarts at 1.
institution -> the list title printed on that season's p000 ("Балетная труппа.").

Only heading_path and institution change; no entry is added, removed or reordered, so person links
(keyed by position) are unaffected. Dry run by default; --write edits outputs/full_run/raw (a copy of
each file is saved next to this script under backup/ first).
usage: uv run python docs/eval/balletartists_heading_fix_2026-10-10/apply.py [--write]"""
import collections, glob, json, re, shutil, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
HERE = Path(__file__).parent
WRITE = '--write' in sys.argv
# page -> 'F' (women's run) or 'M' (men's run), decided from the surnames and the numbering
PAGES = {
    'balletartists_1890-91_SP_p008': 'M', 'balletartists_1891-92_SP_p007': 'M',
    'balletartists_1896-97_SP_p006': 'M', 'balletartists_1896-97_SP_p007': 'M',
    'balletartists_1897-98_MSK_p002': 'F', 'balletartists_1900-01_SP_p007': 'M',
    'balletartists_1901-02_MSK_p006': 'M', 'balletartists_1903-04_SP_p008': 'M',
    'balletartists_1906-07_SP_p009': 'M', 'balletartists_1907-08_SP_p001': 'F',
}
FEM = re.compile(r'(а|ая|я)(\s+\d-я)?(\s*\(.*\))?$')


def season_headings(season_city):
    """(women's heading on p000, men's heading where numbering restarts at 1, p000 list title)."""
    files = sorted(glob.glob(str(RAW / f'balletartists_{season_city}_p*.raw.json')))
    p0 = json.load(open(files[0]))['entries']
    title = p0[0]['institution']
    women = next(e['heading_path'] for e in p0 if re.fullmatch(r'Артистки[:.]?', (e.get('heading_path') or '').strip()))
    men = None
    for f in files[1:]:
        es = json.load(open(f))['entries']
        # the first page after p000 that carries a plain "Артисты" heading is where the men's list
        # starts (the numbering restarts at 1 there); take that page's own printed form
        plain = collections.Counter(e['heading_path'] for e in es if re.fullmatch(r'Артисты[:.]?', (e.get('heading_path') or '').strip()))
        if plain:
            men = plain.most_common(1)[0][0]
            break
    assert men, season_city
    return women, men, title


n = 0
for page, sex in PAGES.items():
    season_city = '_'.join(page.split('_')[1:3])
    women, men, title = season_headings(season_city)
    path = RAW / f'{page}.raw.json'
    d = json.load(open(path))
    es = d['entries']
    assert all(e.get('heading_path') == 'Балетмейстеры' for e in es), page       # expected-old
    fem = sum(bool(FEM.search((e.get('family_name') or '').strip())) for e in es)
    assert (fem / len(es) > 0.6) == (sex == 'F'), (page, fem, len(es))             # the run is what we think
    new_h = women if sex == 'F' else men
    for e in es:
        e['heading_path'] = new_h
        e['institution'] = title
    n += len(es)
    print(f'{page}: {len(es)} entries -> heading_path {new_h!r}, institution {title!r}')
    if WRITE:
        (HERE / 'backup').mkdir(exist_ok=True)
        shutil.copy2(path, HERE / 'backup' / path.name)
        json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(n, 'entries', 'WRITTEN' if WRITE else '(dry run)')
