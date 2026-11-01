"""Render one scan page (roster, ballet production list, or Season Review) to PNG for reading.
usage: uv run python docs/eval/person_field_audit_2026-11-01/render.py <page_id> <out.png> [--band TOP BOTTOM] [--width W]
  TOP/BOTTOM are fractions of page height (0..1) to crop a horizontal band; default whole page.
Uses the full-resolution image embedded in the PDF when the page holds exactly one, else renders at 300 dpi."""
import sys, io, re
import duckdb, pymupdf
from PIL import Image

pid, out = sys.argv[1], sys.argv[2]
band = (float(sys.argv[sys.argv.index('--band') + 1]), float(sys.argv[sys.argv.index('--band') + 2])) if '--band' in sys.argv else (0, 1)
width = int(sys.argv[sys.argv.index('--width') + 1]) if '--width' in sys.argv else 2400
DIRS = {'BalletArtists': 'Spiski_BalletArtists', 'Musicians': 'Spiski_Musicians', 'ProductionTeam': 'Spiski_ProductionTeam',
        'Administrators': 'Spiski_Administration', 'TheaterSchoolStaff': 'Spiski_TheaterSchoolStaff', 'Graduates': 'Spiski_Graduates'}
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
if pid.startswith('review_'):
    m = re.match(r'review_(\d{4}-\d\d)_(SP|MSK)_(\w+?)_p(\d+)$', pid)
    season, city, genre, idx = m.groups()
    path = f"pdf/Reviews_Season/{season}_SeasonReview_{genre.capitalize()}{'SP' if city == 'SP' else 'Moscow'}.pdf"
    idx = int(idx)
elif pid.startswith('balletproductions_'):
    sf, idx = con.execute("select any_value(source_file), any_value(source_page_index) from raw.production_entry where page_id=?", [pid.split('__')[0]]).fetchone()
    path = f'pdf/Spiski_BalletProductions/{sf}'
else:
    et, sf, idx = con.execute("select entity_type, source_file, source_page_index from raw.source_pages where page_id=?", [pid.split('__')[0]]).fetchone()
    path = f'pdf/{DIRS[et]}/{sf}'
doc = pymupdf.open(path)
pg = doc[int(idx)]
imgs = pg.get_images()
if len(imgs) == 1:
    im = Image.open(io.BytesIO(doc.extract_image(imgs[0][0])['image']))
else:
    im = Image.open(io.BytesIO(pg.get_pixmap(dpi=300).tobytes('png')))
im = im.convert('L')
W, H = im.size
im = im.crop((0, int(band[0] * H), W, int(band[1] * H)))
if im.width > width:
    im = im.resize((width, int(im.height * width / im.width)))
im.save(out)
print(path, 'page', idx, 'size', (W, H), '->', im.size)
