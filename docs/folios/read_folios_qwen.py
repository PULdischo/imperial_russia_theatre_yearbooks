"""Ask Qwen (DashScope) for the printed page number of staff-list pages. usage: folio_qwen.py <pages.txt> <out.csv> [--conc N]
Image: the page's head 16% and foot 22% stacked, width 1000, JPEG. Answer: digits or NONE. Records token usage."""
import sys, io, csv, base64, asyncio, os, re
from pathlib import Path
import pymupdf
from PIL import Image
from dotenv import load_dotenv
from openai import AsyncOpenAI
REPO = Path('/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main')
load_dotenv(REPO / '.env')
sys.path.insert(0, str(REPO / 'pipeline'))
from run_pilot import BASE_URL
DIRS = {'BalletArtists': 'Spiski_BalletArtists', 'Musicians': 'Spiski_Musicians', 'ProductionTeam': 'Spiski_ProductionTeam',
        'Administrators': 'Spiski_Administration', 'TheaterSchoolStaff': 'Spiski_TheaterSchoolStaff', 'Graduates': 'Spiski_Graduates'}
PM = {r['page_id']: r for r in csv.DictReader(open(REPO / 'docs/eval/person_field_audit_2026-11-01/page_map.csv', encoding='utf-8'))}
PROMPT = ("The image shows two strips cut from ONE page of a printed Russian yearbook (1890-1911): the TOP of the page above "
          "the black bar, the BOTTOM of the page below it. What is this page's printed page number (folio)? It is usually "
          "centred at the foot («— 110 —») or in a corner at the head or foot; old-style figures (I for 1). Ignore list "
          "numbers like «12.» and dates. Answer with the number in Arabic digits only, or NONE if no page number is visible.")
def image(pid):
    r = PM[pid]; path = REPO / 'pdf' / DIRS[r['entity_type']] / r['source_file']
    doc = pymupdf.open(path); pg = doc[int(r['source_page_index'])]; imgs = pg.get_images()
    im = (Image.open(io.BytesIO(doc.extract_image(imgs[0][0])['image'])) if len(imgs) == 1
          else Image.open(io.BytesIO(pg.get_pixmap(dpi=200).tobytes('png')))).convert('L')
    w, h = im.size; top = im.crop((0, 0, w, int(h * .16))); bot = im.crop((0, int(h * .78), w, h))
    comp = Image.new('L', (w, top.size[1] + bot.size[1] + 30), 0); comp.paste(top, (0, 0)); comp.paste(bot, (0, top.size[1] + 30))
    comp = comp.resize((1000, int(comp.size[1] * 1000 / w)))
    b = io.BytesIO(); comp.save(b, 'JPEG', quality=80)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
async def one(client, sem, pid, w, tot):
    async with sem:
        for attempt in range(4):
            try:
                r = await client.chat.completions.create(model='qwen3-vl-plus', max_tokens=20, temperature=0,
                    messages=[{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': image(pid)}},
                                                          {'type': 'text', 'text': PROMPT}]}])
                ans = (r.choices[0].message.content or '').strip()
                u = r.usage; tot[0] += u.prompt_tokens; tot[1] += u.completion_tokens
                m = re.search(r'\d{1,4}', ans)
                w.writerow([pid, m.group(0) if m else '', ans[:40], u.prompt_tokens, u.completion_tokens]); return
            except Exception as e:
                await asyncio.sleep(2 * (attempt + 1)); err = str(e)[:80]
        w.writerow([pid, '', 'ERROR ' + err, 0, 0])
async def main():
    pages = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    conc = int(sys.argv[sys.argv.index('--conc') + 1]) if '--conc' in sys.argv else 8
    client = AsyncOpenAI(api_key=os.environ['DASHSCOPE_API_KEY'], base_url=BASE_URL, timeout=120)
    f = open(sys.argv[2], 'w', newline='', encoding='utf-8'); w = csv.writer(f); w.writerow(['page_id', 'folio', 'answer', 'in_tok', 'out_tok'])
    tot = [0, 0]; sem = asyncio.Semaphore(conc)
    await asyncio.gather(*(one(client, sem, p, w, tot) for p in pages)); f.close()
    print(f'{len(pages)} pages; tokens in {tot[0]:,}, out {tot[1]:,}')
asyncio.run(main())
