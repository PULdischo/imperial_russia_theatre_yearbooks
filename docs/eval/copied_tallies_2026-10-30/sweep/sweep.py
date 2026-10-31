"""Sweep helper for the unread-pages copied-tally read (2026-10-30).
  prep N   -> make crops + 6 worklists for batch N (48 pages each, from unread_pages.json)
  clean N  -> delete batch N's crops
  compare  -> compare every sweep_reads_b*_g*.tsv with the stored credit lines
Run from the repo root with: uv run --with pymupdf --with pillow python <this> ..."""
import csv, glob, json, re, shutil, sys
from pathlib import Path

S = Path(__file__).parent
REPO = Path.cwd()
PER_BATCH, PER_AGENT = 48, 8


def batch_pages(n):
    pages = json.load(open(S / 'unread_pages.json'))
    return [p[0] for p in pages[(n - 1) * PER_BATCH: n * PER_BATCH]]


def prep(n):
    import pymupdf
    from PIL import Image
    man = {r['page_id']: r for r in csv.DictReader(open(REPO / 'outputs/full_run/manifest.csv'))}
    out = S / f'sweep_b{n}'; out.mkdir(exist_ok=True)
    pages = batch_pages(n)
    for pid in pages:
        m = man[pid]
        path = glob.glob(str(REPO / f'pdf/**/{m["source_file"]}'), recursive=True)[0]
        d = pymupdf.open(path); x = d[int(m['source_page_index'])].get_images()[0][0]
        pix = pymupdf.Pixmap(d, x)
        if pix.n - pix.alpha > 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        tmp = out / f'{pid}_full.png'; pix.save(str(tmp)); im = Image.open(tmp).convert('RGB'); W, H = im.size
        for col, (x0, x1) in {'L': (0, int(W * .54)), 'R': (int(W * .46), W)}.items():
            for half, (y0, y1) in {'top': (0, int(H * .53)), 'bot': (int(H * .47), H)}.items():
                im.crop((x0, y0, x1, y1)).save(out / f'{pid}_{col}{half}.jpg', quality=88)
        tmp.unlink()
    for g in range(6):
        sub = pages[g * PER_AGENT:(g + 1) * PER_AGENT]
        if not sub: continue
        L = []
        for pid in sub:
            ents = json.load(open(REPO / f'outputs/full_run/raw/{pid}.raw.json'))['entries']
            L.append(f'\n### {pid}  (crops: {out}/{pid}_Ltop.jpg, _Lbot.jpg, _Rtop.jpg, _Rbot.jpg)')
            for i, e in enumerate(ents, 1):
                L.append(f'- {pid}__e{i:03d} | no. {e.get("list_number")} {e.get("family_name")} {e.get("first_name") or ""}')
        (S / f'sweep_b{n}_g{g + 1}.md').write_text('\n'.join(L))
    print(n, len(pages), 'pages prepared')


def clean(n):
    shutil.rmtree(S / f'sweep_b{n}', ignore_errors=True); print('cleaned', n)


def first_num(s):
    m = re.search(r'\d+', s or ''); return m.group(0) if m else ''


def total(s):
    m = re.search(r'Все\S{0,3}\s*[—–-]*\s*(?:(?:въ|вв|всѣ|88|as)\s*\d+\s+\S+\s*[—–-]+\s*)?(\d+)', s or ''); return m.group(1) if m else ''


def compare():
    rows = []
    for f in sorted(S.glob('sweep_reads_b*_g*.tsv')):
        for r in list(csv.reader(open(f), delimiter='\t'))[1:]:
            if len(r) >= 4: rows.append(r)
    flags, n_ok = [], 0
    for eid, has, ptot, pfirst, *note in rows:
        pid, i = eid.rsplit('__e', 1)
        e = json.load(open(REPO / f'outputs/full_run/raw/{pid}.raw.json'))['entries'][int(i) - 1]
        st = (e.get('credit_summary_text') or '').strip()
        stored_has = bool(re.search(r'Всего|Все-|балет|опер|\(', st))
        has = has.strip().lower().startswith('y')
        if has != stored_has:
            flags.append(('REMOVE?' if stored_has else 'MISSING?', eid, e.get('list_number'), e.get('family_name'), ptot, pfirst, st[:80], ' '.join(note)[:80]))
        elif has and (ptot.strip() and total(st) and ptot.strip() != total(st) or pfirst.strip() and first_num(st) and pfirst.strip() != first_num(st)):
            flags.append(('NUMS', eid, e.get('list_number'), e.get('family_name'), ptot, pfirst, st[:80], ' '.join(note)[:80]))
        else:
            n_ok += 1
    print(len(rows), 'read;', n_ok, 'agree;', len(flags), 'flagged')
    for fl in flags: print(fl)
    json.dump(flags, open(S / 'sweep_flags.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    {'prep': lambda: prep(int(sys.argv[2])), 'clean': lambda: clean(int(sys.argv[2])), 'compare': compare}[sys.argv[1]]()
