"""Ballet Seasons by City, drawn for the CURVE wall (19,200 x 4,320 px, 40:9, 40.6 px/in, 39'4" x 8'8").

Reads the same seasons.json the Ballet Seasons by City artifact reads (export_season_data.py), so the figures match it.
Layout is in wall pixels; the PDF page is 19,200 x 4,320 px at 96 px/in = 200 x 45 in (14,400 x 3,240 pt), which is
Acrobat's largest page size, so the PDF maps 1:1 onto the wall's pixels when shown full screen.

Page 1 (the default output): every season at a glance (a bar per city per season, all on one scale, one named segment per
ballet sized by its events, so a bar's height is its performances; the 12 coloured ballets first in a fixed order; the 12 most-performed ballets each have their own colour, the rest a dark neutral per city; no both-cities marking,
RG 2026-11-25). With --seasons, one page per season: St Petersburg on the left, Moscow on the right, titles facing each
other across the middle, gold curves joining a ballet given in both cities. Order within a city: most events first.

usage: uv run python docs/figures/explorer/curve_season_pdf.py [out.pdf] [--seasons] [--png]
  (--seasons adds the per-season pages after page 1; --png also writes one PNG per page)"""
import json, sys
from pathlib import Path
import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = Path(args[0]) if args else ROOT / 'docs/figures/curve/ballet_seasons_by_city_CURVE.pdf'
PNG = '--png' in sys.argv
SEASONS = '--seasons' in sys.argv
DATA = json.loads((HERE / 'seasons.json').read_text())

W, H = 19200, 4320
S = 0.75                         # px -> pt
M = 320                          # outer margin, px

def rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def mix(a, b, t): return tuple(x * (1 - t) + y * t for x, y in zip(a, b))
C = {k: rgb(v) for k, v in dict(
    bg='#2C3932', panel='#36463D', panel2='#3F4F45', rule='#6F7D73', text='#DFD2C4', muted='#BDB2A5', faint='#9C9488',
    sp='#8296AA', sp_fill='#2F3F4C', sp_text='#AFC0D1', mo='#D2BD9A', mo_fill='#4A4537', mo_text='#DCCAA8',
    hl='#E3B66B', flag='#E39A7F', pie_sp='#7F9AB8', pie_mo='#A3835A').items()}
C['both_row'] = mix(C['panel'], C['hl'], .16)

FONTDIR = ROOT / 'docs/figures/curve/fonts/static'   # the artifact's typefaces; provenance in docs/figures/curve/fonts/README.md
FONTS = {'disp': FONTDIR / 'PlayfairDisplay-Regular.ttf', 'dispi': FONTDIR / 'PlayfairDisplay-Italic.ttf',
         'fig': FONTDIR / 'PlayfairDisplay-Regular-LiningFigures.ttf',
         'body': FONTDIR / 'Raleway-Regular.ttf', 'bodyi': FONTDIR / 'Raleway-Italic.ttf',
         'semi': FONTDIR / 'Raleway-SemiBold.ttf', 'bold': FONTDIR / 'Raleway-Bold.ttf'}
FOBJ = {k: pymupdf.Font(fontfile=str(v)) for k, v in FONTS.items()}
CITY = {'SP': 'St Petersburg', 'Moscow': 'Moscow'}
ROLE = {'music': 'music', 'author': 'author', 'libretto': 'libretto', 'source': 'source', 'staging': 'staging', 'instrumentation': 'orchestration'}
lab = lambda s: s.replace('-', '/')
plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"


class Page:
    def __init__(self, doc):
        self.p = doc.new_page(width=W * S, height=H * S)
        self.loaded = set()                 # fonts are embedded on first use, so unused ones add nothing to the file
        self.rect(0, 0, W, H, C['bg'])

    def rect(self, x, y, w, h, fill, stroke=None, width=0, radius=None):
        r = pymupdf.Rect(x * S, y * S, (x + w) * S, (y + h) * S)
        self.p.draw_rect(r, color=stroke, fill=fill, width=width * S, radius=radius)

    def line(self, x0, y0, x1, y1, color, width):
        self.p.draw_line((x0 * S, y0 * S), (x1 * S, y1 * S), color=color, width=width * S)

    def text(self, x, y, s, size, font='body', color=C['text'], align='l'):
        """y is the baseline. align l/r/c relative to x. Returns the text width in px."""
        w = FOBJ[font].text_length(s, fontsize=size)
        x0 = x - w if align == 'r' else x - w / 2 if align == 'c' else x
        if font not in self.loaded:
            self.p.insert_font(fontname=font, fontfile=str(FONTS[font])); self.loaded.add(font)
        self.p.insert_text((x0 * S, y * S), s, fontsize=size * S, fontname=font, color=color)
        return w

    def runs(self, x, y, runs, align='l'):
        """runs: [(text, size, font, color)] set on one baseline."""
        total = sum(FOBJ[f].text_length(t, fontsize=sz) for t, sz, f, _ in runs)
        cx = x - total if align == 'r' else x
        for t, sz, f, col in runs:
            cx += self.text(cx, y, t, sz, f, col)
        return total


def width(runs): return sum(FOBJ[f].text_length(t, fontsize=sz) for t, sz, f, _ in runs)
def fit(s, size, font, maxw, floor=.6):
    """Largest size <= size (down to floor*size) at which s fits maxw; truncate with … only past the floor."""
    w = FOBJ[font].text_length(s, fontsize=size)
    if w <= maxw: return s, size
    sz = max(size * floor, size * maxw / w)
    while FOBJ[font].text_length(s, fontsize=sz) > maxw and len(s) > 2: s = s[:-2] + '…'
    return s, sz


# ---------------------------------------------------------------- page 1: every season at a glance
def seg_label(pg, x, y, w, h, title, col, pad=14, font='semi', big=64, floor=26):
    """Ballet title inside its bar segment, in col: the largest of one line or two lines
    (split at the space or hyphen nearest the middle) that fits; truncated with … only if neither reaches the floor size."""
    iw = w - 2 * pad
    L = lambda t, sz: FOBJ[font].text_length(t, fontsize=sz)
    one = min(big, h * .62, big * iw / max(L(title, big), 1))
    two, lines = 0, None
    sp = [i for i, ch in enumerate(title) if ch in ' -']   # break at a space, or after a hyphen (Конекъ-горбунокъ)
    if sp:
        k = min(sp, key=lambda i: abs(i - len(title) / 2))
        a, b = (title[:k], title[k + 1:]) if title[k] == ' ' else (title[:k + 1], title[k + 1:])
        two = min(big, h * .40, big * iw / max(L(a, big), L(b, big), 1))
        lines = (a, b)
    if two > one and two >= floor:
        lh = two * 1.08
        base = y + h / 2 - lh / 2 + two * .36
        for t in lines:
            pg.text(x + w / 2, base, t, two, font, col, 'c'); base += lh
    else:
        sz = max(min(one, h * .62), min(floor, h * .62))
        t = title
        while L(t, sz) > iw and len(t) > 2: t = t[:-2] + '…'
        pg.text(x + w / 2, y + h / 2 + sz * .36, t, sz, font, col, 'c')


# The 12 ballets with the most events across both cities and all seasons each get their own colour (validated: every pair,
# including the two neutrals, at least CIEDE2000 14.9 apart; dark label text at contrast >= 4:1 on each). The rest get a dark
# neutral per city with light label text. Ranked from the data, so the set follows the export.
PALETTE = ['#F2D04B', '#6E9EF7', '#ECE7DC', '#EE6A6A', '#62D6E8', '#F28C4E', '#B48CF0', '#B8DD62', '#E36FC0', '#A89C6C', '#F4A9C8', '#5FC98A']
OTHER_SP, OTHER_MO = rgb('#46576A'), rgb('#5C5242')
_ev, TITLE_OF = {}, {}
for _se in DATA['seasons']:
    for _cd in DATA['data'][_se]['cities'].values():
        for _b in _cd['ballets']:
            _ev[_b['id']] = _ev.get(_b['id'], 0) + _b['events']; TITLE_OF[_b['id']] = _b['title']
# Ties are broken alphabetically, except that RG chose «Щелкунчикъ» for the 12th colour (2026-11-25) out of a three-way tie at
# 64 events with «Пахита» and «Привалъ кавалеріи».
TIE_PREFER = {'Щелкунчикъ'}
TOP12 = sorted(_ev, key=lambda i: (-_ev[i], TITLE_OF[i] not in TIE_PREFER, TITLE_OF[i]))[:12]
BALLET_COL = {wid: rgb(h) for wid, h in zip(TOP12, PALETTE)}


def overview(doc):
    pg = Page(doc)
    pg.text(M, 300, 'Ежегодникъ Императорскихъ театровъ · Repertoire and productions lists'.upper(), 64, 'bold', C['faint'])
    pg.text(M, 560, 'Ballet seasons, St Petersburg and Moscow: every season at a glance', 200, 'disp')
    pg.text(M, 720, 'One bar per city per season, all on one scale: a segment per ballet, its height the events that gave it. '
            'The 12 coloured ballets always come first, in the legend\'s order; the rest follow, largest first.', 72, 'body', C['muted'])
    # legend, right-aligned on the title block: the 12 coloured ballets in two rows of six, most events first
    for r, row in enumerate((TOP12[:6], TOP12[6:])):
        lx, ly = W - M, 470 + r * 130
        for wid in reversed(row):
            label = TITLE_OF[wid]
            tw = FOBJ['semi'].text_length(label, fontsize=72)
            pg.text(lx, ly, label, 72, 'semi', C['text'], 'r')
            pg.rect(lx - tw - 110, ly - 62, 80, 80, BALLET_COL[wid], radius=.12)
            lx -= tw + 200
    seasons = DATA['seasons']
    n = len(seasons)
    colw = (W - 2 * M) / n
    top, bot = 1000, 3640
    barw = colw * .45
    gap = 5
    # one scale for every bar: px per performance (a ballet at one event), set by the fullest bar
    k = (bot - top) / max(sum(b['events'] for b in DATA['data'][se]['cities'][c]['ballets'])
                          for se in seasons for c in ('SP', 'Moscow'))
    rank = {wid: r for r, wid in enumerate(TOP12)}
    for i, se in enumerate(seasons):
        d = DATA['data'][se]
        cx = M + colw * i + colw / 2
        pg.text(cx, 870, lab(se), 96, 'fig', C['text'], 'c')
        for j, c in enumerate(('SP', 'Moscow')):
            x = cx - barw - 10 if j == 0 else cx + 10
            # the 12 coloured ballets first in fixed (legend) order, so each colour keeps its place; then the rest, largest first
            items = sorted([b for b in d['cities'][c]['ballets'] if b['events']],
                           key=lambda b: (rank.get(b['id'], 99), -b['events'], b['title']))
            perf = sum(b['events'] for b in items)
            y = top
            for b in items:
                h = b['events'] * k - gap          # the gap comes out of the segment, so bar height stays exactly perf * k
                own = BALLET_COL.get(b['id'])
                fill = own or (OTHER_SP if c == 'SP' else OTHER_MO)
                pg.rect(x, y, barw, h, fill)
                dup = sum(o['title'] == b['title'] for o in items) > 1      # two works, one title: add the tag
                seg_label(pg, x, y, barw, h, b['title'] + (f" ({b['tag']})" if dup and b['tag'] else ''),
                          C['bg'] if own else C['text'])
                y += h + gap
            performed = len(items)
            tc = C['sp_text'] if c == 'SP' else C['mo_text']
            pg.text(x + barw / 2, top - 30, 'St P.' if c == 'SP' else 'Moscow', 44, 'bold', tc, 'c')
            pg.text(x + barw / 2, bot + 115, str(performed), 104, 'fig', tc, 'c')
            pg.text(x + barw / 2, bot + 195, f"{perf} perf.", 56, 'body', C['muted'], 'c')
            pg.text(x + barw / 2, bot + 265, f"{d['cities'][c]['ballet_events']} ev.", 56, 'body', C['faint'], 'c')
        if not d['has_list']:
            pg.text(cx, bot + 345, 'no list', 54, 'bodyi', C['faint'], 'c')
    # row captions at the far left would collide with the first column; put them in the footer instead
    pg.line(M, H - 250, W - M, H - 250, C['rule'], 4)
    pg.text(M, H - 175, 'Under each bar: ballets given (large figure); performances ("perf.": a ballet given at one event, full or excerpt; '
            'the bar\'s height); events with ballet ("ev.": one theatre, date and session; a mixed bill counts once). Left bar St Petersburg, right bar Moscow.', 52, 'body', C['faint'])
    pg.text(M, H - 100, 'The 12 most-performed ballets have their own colour; the rest are dark blue (St Petersburg) or dark brown (Moscow). '
            '"No list": no productions list survives for that season.', 52, 'body', C['faint'])
    pg.text(W - M, H - 100, f"Data exported {DATA['exported']} from the research database · same data as the Ballet Seasons by City artifact",
            60, 'body', C['faint'], 'r')


# ---------------------------------------------------------------- one page per season
def credits_runs(b, size):
    seen, out = set(), []
    for e in b['entries']:
        for c in e['credits']:
            k = (c['role'], c['name'])
            if k in seen: continue
            seen.add(k)
            if out: out.append(('   ', size, 'body', C['faint']))
            out.append((ROLE.get(c['role'], c['role']).upper() + ' ', size * .78, 'bold', C['faint']))
            out.append((c['name'], size, 'body', C['muted']))
    return out


def list_text(b):
    if not b['entries']: return '—', False
    vals = [(e['total'], e['mismatch']) for e in b['entries']]
    s = ' / '.join('—' if t is None else str(t) for t, _ in vals)
    return s, any(m for _, m in vals)


def season_page(doc, se):
    d = DATA['data'][se]
    pg = Page(doc)
    ballets = {c: sorted(d['cities'][c]['ballets'], key=lambda b: (-b['events'], -b['full'], b['title'])) for c in ('SP', 'Moscow')}
    nmax = max(len(v) for v in ballets.values())
    CW = 2600                                     # centre band
    tw = (W - 2 * M - CW) / 2                     # each city's table width
    ty0, ty1 = 1060, 3990                         # table body
    rh = min(150, (ty1 - ty0) / nmax)
    fs = rh * .58                                 # row font size
    # column widths inside a city table: title | Full | Exc | List | creators (mirrored for SP); title column sized to
    # this season's longest title so the numbers sit next to the titles
    longest = max(FOBJ['bold'].text_length(f"«{b['title']}»" + (f" ({b['tag']})" if b['tag'] else ''), fontsize=fs)
                  for v in ballets.values() for b in v)
    wt, wn = min(tw * .36, longest + fs * 1.2 + 110), 300
    wc = tw - wt - 3 * wn

    # header band
    pg.text(M, 250, 'Ежегодникъ Императорскихъ театровъ · Repertoire and productions lists'.upper(), 60, 'bold', C['faint'])
    pg.text(W / 2, 560, lab(se), 380, 'fig', C['text'], 'c')
    pg.text(W - M, 250, 'Ballet seasons, St Petersburg and Moscow'.upper(), 60, 'bold', C['faint'], 'r')
    for c in ('SP', 'Moscow'):
        cd = d['cities'][c]
        performed = sum(1 for b in cd['ballets'] if b['events'])
        tc = C['sp_text'] if c == 'SP' else C['mo_text']
        x, al = (M, 'l') if c == 'SP' else (W - M, 'r')
        pg.text(x, 560, CITY[c], 230, 'disp', tc, al)
        pg.text(x, 720, f"{plural(performed, 'ballet')} given  ·  {plural(cd['ballet_events'], 'event')} with ballet", 84, 'body', C['muted'], al)
    pg.text(W / 2, 740, f"{plural(d['shared'], 'ballet')} given in both cities", 84, 'bold', C['hl'], 'c')
    if not d['has_list']:
        pg.text(W / 2, 850, 'No productions list survives for this season: creators and list totals are blank', 60, 'bodyi', C['faint'], 'c')

    rows = {}
    for c in ('SP', 'Moscow'):
        x0 = M if c == 'SP' else W - M - tw
        stripe = C['sp'] if c == 'SP' else C['mo']
        # panel
        pg.rect(x0, ty0 - 130, tw, ty1 - ty0 + 150, C['panel'], radius=.012)
        pg.rect(x0, ty0 - 130, tw, 10, stripe)
        # column positions; SP mirrored so titles face the centre
        if c == 'SP':
            cols = {'cred': (x0 + 40, x0 + wc - 30, 'r'), 'list': x0 + wc, 'exc': x0 + wc + wn, 'full': x0 + wc + 2 * wn,
                    'title': (x0 + wc + 3 * wn + 30, x0 + tw - 50, 'r')}
        else:
            cols = {'title': (x0 + 50, x0 + wt - 30, 'l'), 'full': x0 + wt, 'exc': x0 + wt + wn, 'list': x0 + wt + 2 * wn,
                    'cred': (x0 + wt + 3 * wn + 30, x0 + tw - 40, 'l')}
        hy = ty0 - 40
        hs = 50
        t0, t1, al = cols['title']; pg.text(t1 if al == 'r' else t0, hy, 'BALLET', hs, 'bold', C['faint'], al)
        k0, k1, ak = cols['cred']; pg.text(k1 if ak == 'r' else k0, hy, 'CREATORS (LIST ENTRY)', hs, 'bold', C['faint'], ak)
        for k, h in (('full', 'FULL'), ('exc', 'EXC.'), ('list', 'LIST')):
            pg.text(cols[k] + wn / 2, hy, h, hs, 'bold', C['faint'], 'c')
        for i, b in enumerate(ballets[c]):
            y = ty0 + i * rh
            if b['both']:
                pg.rect(x0 + 4, y, tw - 8, rh, C['both_row'])
                bx = x0 + tw - 16 if c == 'SP' else x0 + 4
                pg.rect(bx, y, 12, rh, C['hl'])
            if i:
                pg.line(x0 + 20, y, x0 + tw - 20, y, mix(C['panel'], C['rule'], .5), 2)
            base = y + rh * .5 + fs * .36
            zero = not b['events']
            # title (+ premiere star)
            title = f"«{b['title']}»" + (f" ({b['tag']})" if b['tag'] else '')
            star = any(e['premiere'] for e in b['entries'])
            room = t1 - t0 - (fs * 1.1 if star else 0)
            ttl, tsz = fit(title, fs, 'bodyi' if zero else 'bold', room)
            run = [(ttl, tsz, 'bodyi' if zero else 'bold', C['muted'] if zero else C['text'])]
            if star: run = ([('* ', fs, 'bold', C['hl'])] + run) if al == 'r' else (run + [(' *', fs, 'bold', C['hl'])])
            pg.runs(t1 if al == 'r' else t0, base, run, al)
            # numbers
            pg.text(cols['full'] + wn / 2, base, str(b['full']), fs, 'body', C['text'] if b['full'] else C['faint'], 'c')
            pg.text(cols['exc'] + wn / 2, base, str(b['excerpt']) if b['excerpt'] else '·', fs, 'body', C['text'] if b['excerpt'] else C['faint'], 'c')
            lt, mm = list_text(b)
            if mm: lt += ' ≠'
            lt, lsz = fit(lt, fs, 'bold' if mm else 'body', wn - 20)
            pg.text(cols['list'] + wn / 2, base, lt, lsz, 'bold' if mm else 'body', C['flag'] if mm else (C['faint'] if lt == '—' else C['text']), 'c')
            # creators
            if not b['entries']:
                if d['has_list']:
                    pg.text(k1 if ak == 'r' else k0, base, 'no list entry this season', fs * .8, 'bodyi', C['faint'], ak)
            else:
                cr = credits_runs(b, fs * .86)
                if not cr:
                    pg.text(k1 if ak == 'r' else k0, base, 'no credits printed', fs * .8, 'bodyi', C['faint'], ak)
                else:
                    wcr = width(cr)
                    if wcr > k1 - k0:
                        f = max(.62, (k1 - k0) / wcr)
                        cr = [(t, sz * f, fo, co) for t, sz, fo, co in cr]
                    pg.runs(k1 if ak == 'r' else k0, base, cr, ak)
            rows[(c, b['id'])] = y + rh / 2

    # gold curves joining ballets given in both cities, title edge to title edge across the centre band
    xl, xr = M + tw, W - M - tw
    for (c, bid), ym in rows.items():
        if c != 'SP' or ('Moscow', bid) not in rows: continue
        yr = rows[('Moscow', bid)]
        p0, p3 = pymupdf.Point(xl * S, ym * S), pymupdf.Point(xr * S, yr * S)
        p1, p2 = pymupdf.Point((xl + CW * .45) * S, ym * S), pymupdf.Point((xr - CW * .45) * S, yr * S)
        pg.p.draw_bezier(p0, p1, p2, p3, color=C['hl'], width=10 * S)
        for x, yy in ((xl, ym), (xr, yr)):
            pg.p.draw_circle(pymupdf.Point(x * S, yy * S), 16 * S, color=None, fill=C['hl'])

    # footer key
    fy = H - 150
    pg.text(M, fy, 'FULL events that gave the whole ballet  ·  EXC. events that gave only an excerpt  ·  LIST total printed in the productions list  ·  '
            '≠ list total matches neither Repertoire count  ·  * the list marks the entry as a premiere (also used for some revivals)', 56, 'body', C['faint'])
    pg.text(W - M, fy, f"Events = one theatre, date and session · data exported {DATA['exported']}", 56, 'body', C['faint'], 'r')


doc = pymupdf.open()
overview(doc)
if SEASONS:                      # per-season pages only on request (RG 2026-11-25: page 1 alone for now)
    for se in DATA['seasons']:
        season_page(doc, se)
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.set_metadata({'title': 'Ballet Seasons by City (CURVE)', 'subject': 'St Petersburg and Moscow ballet seasons from the Ежегодникъ Императорскихъ театровъ'})
doc.subset_fonts()
doc.save(OUT, garbage=4, deflate=True)
print(OUT, len(doc), 'pages')
if PNG:
    for i, p in enumerate(doc):
        p.get_pixmap(matrix=pymupdf.Matrix(1 / S, 1 / S)).save(OUT.with_name(f'{OUT.stem}_p{i + 1:02d}.png'))
