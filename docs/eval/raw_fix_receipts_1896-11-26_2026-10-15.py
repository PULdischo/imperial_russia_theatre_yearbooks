"""repertoire_1896-97_pair010, 26 Вторникъ (26 Nov 1896), Большой («О время!, ком. / Ѳедулъ съ дѣтьми, оп.»): receipts
stored «894 р. 46 к.»; the print has «8?4 р. 46 к.» with the middle digit damaged (only its upper loop inked; viewed at 900 dpi,
2026-10-15). The printed 1896-97 Moscow statistics line «Смѣшанныхъ (опера и драма) 2 — 3,527 р. 98 к.» is these two
evenings: 24 Nov 2,643.52 + 884.46 = 3,527.98 exactly; with 894 it is 10 р. over. Damaged digit stored as the intended 8
(the worn-type convention). Field edit only. Then rebuild.
usage: uv run python docs/eval/raw_fix_receipts_1896-11-26_2026-10-15.py [--write]"""
import json, sys
from pathlib import Path
f = Path('outputs/full_run/raw/repertoire_1896-97_pair010.raw.json')
d = json.loads(f.read_text(encoding='utf-8'))
h = [s for s in d['sessions'] if s['date_text'] == '26 Вторникъ.' and 'Большой' in (s.get('theater') or '')]
assert len(h) == 1 and h[0]['receipts_text'] == '894 р. 46 к.', h
h[0]['receipts_text'] = '884 р. 46 к.'
h[0]['_fix_note'] = ('2026-10-15: receipts 894 -> 884; middle digit damaged in print (upper loop only), 884 makes the '
                     'printed «опера и драма» line 3,527.98 exact')
print('26 Nov 1896 Большой: 894 р. 46 к. -> 884 р. 46 к.')
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
