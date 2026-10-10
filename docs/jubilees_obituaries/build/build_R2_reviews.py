"""Review notices the first keyword sweep could not match (found by the wider searches of the 2026-10-10 audit).
Each was read in context; evidence is cut from the database text so it stays verbatim.
Writes first_read/R2_reviews_wider_search.csv (same columns as R_reviews.csv) and appends folios to review_page_folios.csv.
Needs the database:  uv run python docs/jubilees_obituaries/build/build_R2_reviews.py
"""
import csv, os, re, duckdb
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
c = duckdb.connect(os.path.join(ROOT, '..', '..', 'outputs/full_run/imperial_theaters.duckdb'), read_only=True)
# (season, page, block, kind, name as printed, latin, role, dates, relevance, evidence start, evidence end, english, notes)
ITEMS = [
 ('1891-92', 'SP_ballet_p017', 2, 'obituary', 'Яковлевъ 2-й', 'Yakovlev 2-i', 'ballet artist, newly graduated (SP)', '† 9 Aug 1892',
  'core', 'Приняты на службы', '1892 г.),', 'Among the graduates of the ballet department taken into service from 1 June 1892: Yakovlev 2-i († 9 August 1892).',
  'death mark inside the list of new entrants; found by the wider search'),
 ('1892-93', 'SP_ballet_p016', 1, 'farewell', 'г-жа Дель-Эра', "Dell'Era", 'guest ballerina, St Petersburg', '3 Jan 1893',
  'core', '2) 1-е дѣйствіе', 'парадныхъ спектакляхъ', "Act 1 of Sleeping Beauty, in which Dell'Era appeared (as Aurora) for the last time before the Petersburg public, being called to Berlin.",
  'normalised name: Дель-Эра; last appearance of a guest artist, at Л. И. Ивановъ\'s benefit (date from the preceding block, p015 #10); not a retirement'),
 ('1893-94', 'SP_ballet_p023', 3, 'memorial', 'П. И. Чайковскаго', 'P. I. Chaikovskii', 'composer', '17 Feb 1894',
  'mentions', '17-го февраля', 'П. И. Чайковскимъ.', 'Performance "in memory of P. I. Tchaikovsky" at the Mariinsky, including Act 2 of the ballet Swan Lake.',
  'normalised name: П. И. Чайковскій; the performance the 1894-95 review refers back to'),
 ('1899-00', 'MSK_all_p022', 3, 'memorial', '75-лѣтія Большого театра', 'Bolshoi Theatre, 75th anniversary', 'theatre (institution)', '6 Jan 1900',
  'mentions', '6-го января', 'поне- волѣ“', 'For the 75th anniversary of the Bolshoi Theatre the old ballet "Tantsovshchiki ponevole" was revived.',
  'anniversary of a theatre, not a person; the drama troupe\'s part is in MSK_all_p008 #3'),
 ('1900-01', 'MSK_opera_p007', 3, 'farewell', 'г. Кламрота', 'Klamrot', 'concertmaster, Moscow theatres (Bolshoi orchestra)', '11 Oct 1900',
  'core', '11-го октября', 'концертмейстера.', 'Honoured on stage with the curtain up during La Traviata, on leaving the service of the Moscow theatres, where he had been concertmaster for 44 years.',
  'normalised name: Кламротъ; the database text reads «¼ года» but the page prints «44 года» (zoomed on the review scan 2026-10-10; the same typeface 4 as in «4-хъ дѣйствіяхъ» below) — evidence corrected here, the review transcription itself is not; core as a player in the opera-and-ballet orchestra (RG ruling 2026-10-10)'),
 ('1900-01', 'MSK_opera_p013', 2, 'jubilee', 'Н. А. Римскаго-Корсакова', 'N. A. Rimskii-Korsakov', 'composer', '19 Dec 1900',
  'none', '19-го декабря', 'царя Берендѣя.', 'On the 30th anniversary of his work as a composer, his opera Snegurochka was given at the Bolshoi.',
  'normalised name: Н. А. Римскій-Корсаковъ'),
 ('1901-02', 'SP_ballet_p009', 3, 'farewell', 'г-жа Карлота Замбелли', 'Carlotta Zambelli', 'guest ballerina, St Petersburg', '25 Nov 1901',
  'core', '25-го ноября', 'главной роли.', 'Carlotta Zambelli appeared for the last time, in the title role of Paquita, at the Mariinsky.',
  'normalised name: Карлота Замбелли; last appearance of a guest artist, not a retirement'),
 ('1902-03', 'MSK_opera_p013', 4, 'jubilee', 'г-жи Салиной', 'Salina', 'opera singer (soprano), Moscow', '15 Jan 1903',
  'none', '15-го января', '1888 года).', 'Honoured at the Bolshoi during Evgenii Onegin for 15 years in the Moscow opera.',
  'normalised name: Н. В. Салина'),
 ('1907-08', 'SP_ballet_p014', 6, 'jubilee', 'г-жи Сѣдо- вой', 'Sedova', 'ballet artist, St Petersburg', '20 Apr 1908',
  'core', 'Спектакль этотъ совпалъ', 'подарковъ.', "The performance coincided with Sedova's 10 years of service (in the ballet troupe from 1 June 1898); ovation, flowers and gifts.",
  'normalised name: Сѣдова'),
]
out = []; fol = []
for (season, page, b, kind, name, latin, role, dates, rel, a, z, eng, notes) in ITEMS:
    pid = 'review_' + season + '_' + page
    t = c.sql(f"select text from raw.review_block where page_id='{pid}' and block_index={b}").fetchone()[0]
    t = re.sub(r'\s+', ' ', t)
    assert a in t and z in t, (pid, a, z)
    i = t.index(a); j = t.index(z, i) + len(z)
    ev = re.sub(r'-\s+(?=[а-яѣіѳ])', '', t[i:j])        # join words split across a line
    ev = re.sub(r'\s+', ' ', ev)
    if 'Кламрота' in ev: assert '¼ года' in ev; ev = ev.replace('¼ года', '44 года')   # misread in raw.review_block, see notes
    name = re.sub(r'-\s+', '', name)
    out.append([season, pid, b, kind, name, latin, role, dates, rel, ev, eng, notes])
    fol.append((pid, c.sql(f"select printed_folio from raw.review_page where page_id='{pid}'").fetchone()[0]))
with open(ROOT + '/first_read/R2_reviews_wider_search.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['season', 'page_id', 'block_index', 'kind', 'name_verbatim', 'name_latin', 'role', 'dates', 'relevance', 'evidence_verbatim', 'evidence_english', 'notes']); w.writerows(out)
have = {r['page_id'] for r in csv.DictReader(open(HERE + '/review_page_folios.csv', encoding='utf-8'))}
with open(HERE + '/review_page_folios.csv', 'a', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    for pid, fo in fol:
        if pid not in have: w.writerow([pid, fo]); have.add(pid)
for o in out: print(o[0], o[3], o[8], '|', o[4], '|', o[9][:150])
