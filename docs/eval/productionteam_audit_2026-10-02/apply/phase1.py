import json,re,sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
items=json.load(open('/tmp/audit7/items.json')); simple=json.load(open('/tmp/audit7/simple_items.json'))
log=[];fails=[]
def run(fn,*a,**k):
    try: fn(*a,**k)
    except Exception as ex: fails.append((a[:2],str(ex)[:200]))
# 1. corroborated name fixes (same stored->printed seen in >=2 places)
for s in simple['corro']:
    if s['page']=='productionteam_1905-06_p004' and s['entry']=='e012': continue
    run(E.set_field,s['page'],s['entry'],s['field'],s['stored'],s['printed'],log)
run(E.set_field,'productionteam_1905-06_p004','e012','family','Фонтъ-Фитинггофъ-Шель','Фонъ-Фитингофъ-Шель',log)
# 2. specialty text restoration (append after the date sentence)
SPEC=re.compile(r'(Мужскіе|Женскіе|парики|костюмы)')
done=set()
for i in items:
    if i['field'] not in('tenure','title/specialty') or len(i['entries'])!=1: continue
    P=i['printed'].strip().strip('"'); P=re.split(r'"\s*\|',P)[0].strip().strip('"')
    if not SPEC.search(P): continue
    if re.search(r'Оставилъ|Оставила|†|Назначенъ|Переведена|Переведенъ',P): continue
    if 'труппы' in i['stored'] or 'труппъ.' in i['stored']: continue
    suf=P.split('). ',1)[1] if '). ' in P else P
    suf=suf.strip().strip('"')
    if not suf.endswith('.'): suf+='.'
    key=(i['page'],i['entries'][0])
    if key in done or key==('productionteam_1892-93_p004','e006'): continue
    done.add(key)
    run(E.append_note,i['page'],i['entries'][0],suf,log)
# 3. труппы -> труппъ (final ъ misread as ы)
for pg,es in (('productionteam_1896-97_p001',['e014','e015','e016','e017']),('productionteam_1903-04_p001',['e019','e020','e021','e022']),('productionteam_1906-07_p001',['e020'])):
    for e in es: run(E.replace_in,pg,e,'tenure_note_text','труппы','труппъ',log)
# 4. юня -> іюня (tenure + service periods)
for pg,e in (('productionteam_1896-97_p001','e018'),('productionteam_1902-03_p000','e003'),('productionteam_1903-04_p000','e003'),('productionteam_1907-08_p001','e019'),('productionteam_1907-08_p001','e021')):
    run(E.replace_in,pg,e,'tenure_note_text','юня','іюня',log,periods=True)
# 5. other small text fixes
run(E.replace_in,'productionteam_1909-10_p003','e002','tenure_note_text','назначень','назначенъ',log)
run(E.replace_in,'productionteam_1894-95_p002','e012','tenure_note_text','Большого','Большаго',log)
print(len(log),'changes;',len(fails),'fails')
for f in fails: print(f)
if '--write' in sys.argv and not fails:
    E.write_all(); json.dump(log,open('/tmp/audit8/phase1_log.json','w'),ensure_ascii=False,indent=1); print('WRITTEN')
