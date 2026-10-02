import json,sys,copy
sys.path.insert(0,'/tmp/audit6')
import engine, spec_struct
WRITE = '--write' in sys.argv
log=[]; fails=[]
# 1. structural
for pg,e,ops in spec_struct.S:
    try: engine.apply_ops(pg,e,ops,log)
    except Exception as ex: fails.append(('struct',pg,e,str(ex)))
# 1b. extra struct from batch17
try:
    import spec_struct17
    for pg,e,ops in spec_struct17.S:
        try: engine.apply_ops(pg,e,ops,log)
        except Exception as ex: fails.append(('struct17',pg,e,str(ex)))
except ImportError: pass
# 2. dates
for pg,e,old,new in spec_struct.DATES:
    try:
        x=engine.resolve('musicians_'+pg,e)
        t=x.get('tenure_note_text') or ''
        assert old in t,('tenure lacks',old,t)
        x['tenure_note_text']=t.replace(old,new)
        n=0
        for sp in x['service_periods']:
            v=sp.get('start_date_text')
            if v and old in v: sp['start_date_text']=v.replace(old,new); n+=1
        assert n==1,('service_periods',n)
        log.append(('musicians_'+pg,e,'start_date',old,new))
    except Exception as ex: fails.append(('date',pg,e,str(ex)))
# 3. generic
edits=json.load(open('/tmp/audit6/edits_generic.json'))
edits+= [dict(page='musicians_1903-04_SP_p000',entry='e025',field='patronymic',old='Тригорьевичъ',new='Григорьевичъ')]
fixmap={'patronymic/first':'first'}
SKIP={('musicians_1904-05_MSK_p002','e020'),('musicians_1909-10_SP_p000','e007'),('musicians_1895-96_SP_p003','e039'),('musicians_1899-00_MSK_p002','e026'),('musicians_1899-00_MSK_p002','e032'),('musicians_1906-07_MSK_p002','e030')}
for ed in edits:
    if (ed['page'],ed['entry']) in SKIP: continue
    f=fixmap.get(ed['field'],ed['field']); new=ed['new']; old=ed['old']
    if ed['old']=='Людвиго-вичъ': new='Людвиговичъ'
    if ed['old']=='Александро-вичъ': new='Александровичъ'
    if new=='Владимiровичъ': new='Владиміровичъ'
    try: engine.apply_field(ed['page'],ed['entry'],f,old,new,log)
    except Exception as ex: fails.append(('generic',ed['page'],ed['entry'],f'{ed["field"]} {old!r}->{new!r}: {ex}'))
print(len(log),'changes;',sum(1 for l in log if len(l)==6),'already-correct;',len(fails),'FAILURES')
for f in fails: print(f)
json.dump(log,open('/tmp/audit6/change_log.json','w'),ensure_ascii=False,indent=1)
if WRITE and not fails:
    engine.write_all(); print('WRITTEN',len(engine._cache),'pages')
elif WRITE: print('NOT written: failures present')
