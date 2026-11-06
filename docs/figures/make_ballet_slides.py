"""Draw the two "one ballet work" slides (Спящая красавица, Донъ-Кихотъ) as SVG from the production database.

Counts (performances per season, printed titles, excerpts, list entries, review rows) are read live from
outputs/full_run/imperial_theaters.duckdb (read-only). The quoted productions-list wording is fixed in QUOTES below and
was scan-checked (docs/query_log.md, 2026-11-04).

usage: uv run python docs/figures/make_ballet_slides.py
"""
import html
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
import sys
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs/full_run/imperial_theaters.duckdb'
OUT = Path(__file__).resolve().parent
SEASONS = [f'{y}-{str(y + 1)[2:]}' for y in range(1890, 1911)]   # 1890-91 .. 1910-11
NO_LISTS = {'1905-06', '1906-07'}                                 # no productions list in the database, either city

INK, MUTED, FAINT, LINE = '#1f2328', '#5b6470', '#8a929c', '#e2ddd1'
SP_C, SP_F = '#2f6db5', '#e9f0f9'
MO_C, MO_F = '#b5562f', '#fbeee8'
PAPER, PAPER_LINE = '#f4f1ea', '#b9ae96'

X0, COLW = 676, 40      # first season column, column width


def esc(s):
    return html.escape(s, quote=False)


def season_label(s):
    return s.replace('-', '/')


def col_x(season):
    return X0 + COLW * SEASONS.index(season)


def data(con, title):
    q = lambda s, *a: con.execute(s, a).fetchall()
    wid = q("SELECT work_id FROM research.work WHERE canonical_title = ? AND art_form = 'ballet' AND excerpt_of_work_id IS NULL",
            title)[0][0]
    perf = {(s, c): n for s, c, n in q(
        "SELECT e.season, e.city, count(*) FROM research.performance p JOIN research.event e USING (event_id) "
        "WHERE p.work_id = ? GROUP BY ALL", wid)}
    titles = q("SELECT p.verbatim_title, count(*) n FROM research.performance p WHERE p.work_id = ? GROUP BY 1 ORDER BY n DESC, 1",
               wid)
    # excerpt lines shown on the slide are hand-picked (exc_show) from cells scan-checked 2026-11-04; counts come from here.
    exc = q("SELECT w.canonical_title, count(p.performance_id) n, bool_and(p.verbatim_genre IS NULL) whole FROM research.work w "
            "LEFT JOIN research.performance p ON p.work_id = w.work_id WHERE w.excerpt_of_work_id = ? GROUP BY 1 ORDER BY n DESC, 1",
            wid)
    lists = {(s, c) for s, c in q("SELECT season, city FROM research.production WHERE work_id = ?", wid)}
    n_lists = q("SELECT count(*) FROM research.production WHERE work_id = ?", wid)[0][0]
    n_cred = q("SELECT count(*) FROM research.review_credit WHERE work_id = ?", wid)[0][0]
    n_cast = q("SELECT count(*) FROM research.review_assertion WHERE work_id = ?", wid)[0][0]
    return dict(perf=perf, titles=titles, exc=exc, lists=lists, n_lists=n_lists, n_cred=n_cred, n_cast=n_cast)


def card(x, y, w, h, label, lines, fill=PAPER, stroke=PAPER_LINE):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
           f'<text x="{x + 20}" y="{y + 30}" font-size="14" font-weight="700" letter-spacing="1.5" fill="{FAINT}">{esc(label)}</text>']
    yy = y + 42 + (lines[0][1] if lines else 16)
    for txt, size, color, weight in lines:
        out.append(f'<text x="{x + 20}" y="{yy}" font-size="{size}" font-weight="{weight}" fill="{color}">{txt}</text>')
        yy += size + 8
    return out


def slide(title, subtitle, d, work_meta, quotes, footer, fname, n_title_lines=4, exc_show=(), annotations=()):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900" '
         f'font-family="\'Helvetica Neue\', Helvetica, Arial, sans-serif">',
         '<rect width="1600" height="900" fill="#ffffff"/>',
         f'<text x="80" y="84" font-size="40" font-weight="700" fill="{INK}">{title}</text>',
         f'<text x="80" y="120" font-size="20" fill="{MUTED}">{esc(subtitle)}</text>']

    # ---- left column: the work and what hangs on it
    total = sum(d['perf'].values())
    o += card(80, 150, 440, 160, 'ONE WORK', [
        (f'«{esc(work_meta["name"])}»', 34, '#1f4f8a', 700),
        (esc(work_meta['line']), 17, MUTED, 400),
        (f'{total} Repertoire performances, 1890/91–1910/11', 17, INK, 400)], fill=SP_F, stroke=SP_C)

    t_lines = [(f'«{esc(t)}» <tspan fill="{FAINT}">×{n}</tspan>', 16, INK, 400) for t, n in d['titles'][:n_title_lines]]
    if len(d['titles']) > n_title_lines:
        t_lines.append((f'+ {len(d["titles"]) - n_title_lines} more forms', 15, MUTED, 400))
    o += card(80, 326, 440, 66 + 24 * len(t_lines), f'PRINTED TITLES → THIS WORK ({len(d["titles"])} FORM{"S" if len(d["titles"]) != 1 else ""})', t_lines)

    y_exc = 326 + 66 + 24 * len(t_lines) + 16
    n_exc_perf = sum(n for _, n, _w in d['exc'])
    cnt = {t: n for t, n, _w in d['exc']}
    e_lines = [(f'{esc(t)} <tspan fill="{FAINT}">×{cnt[t]}</tspan>', 15, INK, 400) for t in exc_show]
    e_lines.append((f'{len(d["exc"])} excerpt forms, {n_exc_perf} performances, each tied to the ballet', 15, MUTED, 400))
    o += card(80, y_exc, 440, 66 + 23 * len(e_lines), 'EXCERPTS → LINKED TO THIS WORK', e_lines)

    y_ev = y_exc + 66 + 23 * len(e_lines) + 16
    o += card(80, y_ev, 440, 92, 'EVIDENCE ATTACHED', [
        (f'{d["n_lists"]} list entries · {d["n_cred"]} review credits · {d["n_cast"]} cast statements', 16, INK, 400)])

    # ---- right: timeline
    o.append(f'<text x="560" y="166" font-size="14" font-weight="700" letter-spacing="1.5" fill="{FAINT}">PERFORMANCES PER SEASON</text>')
    for s in ['1890-91', '1895-96', '1900-01', '1905-06', '1910-11']:
        cx = col_x(s) + COLW / 2
        o.append(f'<text x="{cx}" y="190" font-size="13" fill="{FAINT}" text-anchor="middle">{season_label(s)}</text>')
    for s in NO_LISTS:
        o.append(f'<rect x="{col_x(s)}" y="200" width="{COLW}" height="330" fill="#f6f7f9"/>')
    for s in SEASONS:
        o.append(f'<line x1="{col_x(s)}" y1="200" x2="{col_x(s)}" y2="530" stroke="{LINE}" stroke-width="1"/>')
    o.append(f'<line x1="{col_x("1910-11") + COLW}" y1="200" x2="{col_x("1910-11") + COLW}" y2="530" stroke="{LINE}" stroke-width="1"/>')
    mx = max(d['perf'].values())
    for city, base, lab, c, f in [('SP', 310, 'St Petersburg', SP_C, SP_F), ('Moscow', 420, 'Moscow', MO_C, MO_F)]:
        o.append(f'<text x="560" y="{base - 8}" font-size="16" font-weight="700" fill="{c}">{lab}</text>')
        o.append(f'<line x1="{X0}" y1="{base}" x2="{col_x("1910-11") + COLW}" y2="{base}" stroke="{FAINT}" stroke-width="1"/>')
        for s in SEASONS:
            n = d['perf'].get((s, city), 0)
            if n:
                h = 92 * n / mx
                o.append(f'<rect x="{col_x(s) + 6}" y="{base - h:.1f}" width="{COLW - 12}" height="{h:.1f}" fill="{c}" opacity="0.85"/>')
                o.append(f'<text x="{col_x(s) + COLW / 2}" y="{base - h - 4:.1f}" font-size="11" fill="{MUTED}" text-anchor="middle">{n}</text>')
    for (s0, s1, yb, txt) in annotations:
        xm = (col_x(s0) + col_x(s1) + COLW) / 2
        o.append(f'<text x="{xm}" y="{yb}" font-size="14" font-style="italic" fill="{MUTED}" text-anchor="middle">{esc(txt)}</text>')
    o.append(f'<text x="560" y="458" font-size="14" font-weight="700" letter-spacing="1.5" fill="{FAINT}">PRODUCTIONS LIST ENTRY</text>')
    for city, y, c, f in [('SP', 470, SP_C, SP_F), ('Moscow', 500, MO_C, MO_F)]:
        o.append(f'<text x="560" y="{y + 18}" font-size="14" fill="{c}">{"St Petersburg" if city == "SP" else "Moscow"}</text>')
        for s in SEASONS:
            if (s, city) in d['lists']:
                o.append(f'<rect x="{col_x(s) + 8}" y="{y + 4}" width="{COLW - 16}" height="20" rx="4" fill="{f}" stroke="{c}" stroke-width="1.5"/>')
    o.append(f'<text x="{col_x("1905-06") + COLW}" y="546" font-size="12" font-style="italic" fill="{FAINT}" text-anchor="middle">no lists</text>')

    # ---- quote cards from the productions lists
    o.append(f'<text x="560" y="580" font-size="14" font-weight="700" letter-spacing="1.5" fill="{FAINT}">WHAT THE PRODUCTIONS LISTS PRINT</text>')
    n = len(quotes)
    gap = 14
    w = (1520 - 560 - gap * (n - 1)) / n
    for i, qd in enumerate(quotes):
        x = 560 + i * (w + gap)
        c, f = (SP_C, SP_F) if qd['city'] == 'SP' else (MO_C, MO_F) if qd['city'] == 'Moscow' else ('#6b5d9a', '#f1ebf7')
        hq = 40 + 21 * len(qd['lines']) + (6 + 19 * len(qd['note']) if qd.get('note') else 0) + 12
        hmax = max(40 + 21 * len(q2['lines']) + (6 + 19 * len(q2['note']) if q2.get('note') else 0) + 12 for q2 in quotes)
        o.append(f'<rect x="{x:.1f}" y="594" width="{w:.1f}" height="{hmax}" rx="10" fill="{f}" stroke="{c}" stroke-width="1.5"/>')
        o.append(f'<text x="{x + 14:.1f}" y="618" font-size="14" font-weight="700" fill="{c}">{esc(qd["head"])}</text>')
        yy = 644
        for ln in qd['lines']:
            o.append(f'<text x="{x + 14:.1f}" y="{yy}" font-size="15" fill="{INK}">{ln}</text>')
            yy += 21
        if qd.get('note'):
            yy += 6
            for ln in qd['note']:
                ln_svg = esc(ln).replace('Yearbook', '<tspan font-style="normal">Yearbook</tspan>')   # title set upright inside italics
                o.append(f'<text x="{x + 14:.1f}" y="{yy}" font-size="14" font-style="italic" fill="{MUTED}">{ln_svg}</text>')
                yy += 19
        # leader tick to the season column
        for s in qd['seasons']:
            cx = col_x(s) + COLW / 2
            o.append(f'<line x1="{cx}" y1="530" x2="{cx}" y2="560" stroke="{c}" stroke-width="2"/>')
            o.append(f'<circle cx="{cx}" cy="530" r="4" fill="{c}"/>')

    o.append(f'<text x="80" y="872" font-size="17" fill="{MUTED}">{esc(footer)}</text>')
    o.append(f'<g font-size="13" fill="{FAINT}" text-anchor="end">'
             '<text x="1520" y="30">Graphic made with Claude Code (AI): drafting, layout, database queries, scan checks of the quoted list entries.</text>'
             '<text x="1520" y="47">Choice of ballets, data model, final wording and editorial decisions by the author.</text></g>')
    o.append('</svg>')
    (OUT / fname).write_text('\n'.join(o), encoding='utf-8')
    return OUT / fname


B = lambda s: f'<tspan font-weight="700">{esc(s)}</tspan>'   # bold a quoted phrase

QUOTES = {
    'Спящая красавица': [
        dict(city='SP', seasons=['1890-91'], head='St Petersburg · 1890/91 · p. 32',
             lines=['«Балетъ-феерія въ 3 д. съ', 'прологомъ, содержаніе', 'заимствовано изъ сказки', 'Перро, музыка П. И.', 'Чайковскаго.»'],
             note=['already running when the', 'Yearbook begins: 21 dates listed']),
        dict(city='Moscow', seasons=['1898-99'], head='Moscow · 1898/99 · p. 58',
             lines=['«Балетъ-феерія въ 3 д., съ', 'прологомъ, содержаніе', 'заимствовано изъ сказокъ', 'Перро, музыка П. И.', 'Чайковскаго.»'],
             note=['Moscow\'s own production,', 'first date 17 Jan 1899;', 'entry marked * in the list']),
        dict(city='SP', seasons=['1901-02'], head='St Petersburg · 1901/02 · p. 47',
             lines=['«3 актъ балета-феерія,', 'музыка П. И. Чайковскаго,', 'постановка М. И. Петипа.»'],
             note=['one act only that season:', 'still filed under the work']),
    ],
    'Донъ-Кихотъ': [
        dict(city='Moscow', seasons=['1890-91'], head='Moscow · 1890/91 · p. 38',
             lines=['«Донъ-Кихотъ»', '«Балетъ въ 4 д. и 8 карт.,', B('соч. М. И. Петипа') + ', музыка', 'Л. Минкуса.»']),
        dict(city='Moscow', seasons=['1900-01'], head='Moscow · 1900/01 · p. 54',
             lines=[B('«Донъ-Кихотъ Ламанчскій»'), '«Большой балетъ въ 4 д.', 'и ' + B('7 карт., съ прологомъ') + ',', B('либретто') + ' М. И. Петипа,', 'музыка Л. Минкуса.»'],
             note=['new title, new shape']),
        dict(city='both', seasons=['1901-02'], head='Both cities · 1901/02',
             lines=['Moscow p. 54 and', 'St Petersburg p. 46:', '«… ' + B('поставленъ'), B('А. А. Горскимъ') + '.»'],
             note=['both lists now credit Горскій;', 'the 1900/01 entry names', 'no stager']),
        dict(city='SP', seasons=['1908-09'], head='St Petersburg · 1908/09 · p. 63',
             lines=['«… Музыка соч. Минкуса', B('и другихъ авторовъ') + '.»'],
             note=['music now credited', 'to more than one hand']),
    ],
    'Волшебное зеркало': [
        # «Г***»: the print sets an italic Г and three asterisks in a point-down triangle (scan check 2026-11-06)
        dict(city='SP', seasons=['1902-03'], head='St Petersburg · 1902/03 · p. 44',
             lines=['«Фантастическій балетъ', 'въ 4 д. и ' + B('7 карт.') + ' …', 'либретто составлено', 'М. И. Петипа и Г***', 'музыка А. Н. Корещенко.»'],
             note=['entry marked * in the list;', 'one date, 9 Feb 1903']),
        dict(city='SP', seasons=['1903-04'], head='St Petersburg · 1903/04 · p. 45',
             lines=['«Большой фантастическій', 'балетъ въ 4 д. и ' + B('8 карт.') + ',', '… либретто М. И. Петипа', 'и Г***, …»'],
             note=['one more scene than', 'the year before']),
        dict(city='SP', seasons=['1904-05'], head='St Petersburg · 1904/05 · p. 138',
             lines=[B('«(1-е, 3-е д. и 2-я карт.'), B('4-го д.).') + ' Большой', 'фантастическій балетъ …»'],
             note=['selected acts only, one date;', 'still filed under the work']),
        dict(city='Moscow', seasons=['1904-05'], head='Moscow · 1904/05 · p. 145',
             lines=['«Балетъ въ 4 д.,', B('соч. М. Петипа') + ', музыка', 'А. Корещенко.»'],
             note=['Petipa alone credited;', 'first date 13 Feb 1905']),
    ],
}


def main():
    con = duckdb.connect(str(DB), read_only=True)
    sb = data(con, 'Спящая красавица')
    dq = data(con, 'Донъ-Кихотъ')
    wm = data(con, 'Волшебное зеркало')
    con.close()
    slide('One work, two cities: «Спящая красавица»',
          'A straightforward case: one ballet, a St Petersburg staging and a later Moscow production, all linked to one work',
          sb, dict(name='Спящая красавица', line='ballet · music by Tchaikovsky'),
          QUOTES['Спящая красавица'],
          'Each season\'s list entry and Repertoire title is kept as printed; all of them point to the one work, none is merged away.',
          'ballet_sleeping_beauty.svg', n_title_lines=2,
          exc_show=['1-е д. бал. Спящая красавица', 'Прологъ балета Спящая красавица', '3-й актъ бал. Спящая красавица'])
    slide('One work, many iterations: «Донъ-Кихотъ»',
          'A complex case: a gap, a new title, a new staging taken up by St Petersburg, and changing credits, all under one work',
          dq, dict(name='Донъ-Кихотъ', line='ballet · music by Minkus'),
          QUOTES['Донъ-Кихотъ'],
          'The stagings are connected, not equated: each list entry keeps its own printed credits, while the work ties them together.',
          'ballet_don_quixote.svg', n_title_lines=4,
          exc_show=['1-е д. бал. Донъ-Кихотъ Ламанчскій', '1-я карт. 1-го д. бал. «Донъ-Кихотъ».'],
          annotations=[('1893-94', '1899-00', 392, 'not performed 1893/94–1899/00')])
    slide('One work, two cities in turn: «Волшебное зеркало»',
          'A St Petersburg premiere that survives there only in excerpts, while Moscow keeps the whole ballet',
          wm, dict(name='Волшебное зеркало', line='ballet · music by Koreshchenko'),
          QUOTES['Волшебное зеркало'],
          'Each list entry keeps its own printed scene count and credits; the work ties the two cities\' records together.',
          'ballet_magic_mirror.svg', n_title_lines=1,
          exc_show=['4-е д. бал. Волшебное зеркало', '1-е д., 3-е д. и 2-я карт. 4-го д. бал. Волшебное зеркало'])


if __name__ == '__main__':
    main()
