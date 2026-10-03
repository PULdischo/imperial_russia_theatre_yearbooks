import json,sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
ver=set(json.load(open('/tmp/audit7/v/verified_ids.json')))
simple=json.load(open('/tmp/audit7/simple_items.json'))
for s in simple['single']:
    iid=f"{s['page']}|{s['entry']}|{s['field']}"
    if iid not in ver: continue
    new=s['printed'].replace('-/','')
    try: E.set_field(s['page'],s['entry'],s['field'],s['stored'],new,log)
    except Exception as ex: fails.append((iid,str(ex)[:200]))
print(len(log),'changes;',len(fails),'fails'); [print(f) for f in fails]
