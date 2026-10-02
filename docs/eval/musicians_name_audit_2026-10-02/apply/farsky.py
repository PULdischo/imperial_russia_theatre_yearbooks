import sys,json,shutil,os
sys.path.insert(0,'/tmp/audit6'); import engine
AL='(онъ же и библіотекарь Музыкальной библіотеки)'
rows=[('1893-94_MSK_p003','e032'),('1894-95_MSK_p003','e028'),('1901-02_MSK_p004','e034'),('1902-03_MSK_p004','e021')]
log=[]
for pg,e in rows:
    x=engine.resolve('musicians_'+pg,e); assert x['family_name']=='Фарскій' and x.get('rank_or_title')==AL,(pg,e,x.get('rank_or_title'))
    t=x.get('tenure_note_text') or ''; assert 'онъ же' not in t
    x['rank_or_title']=None; x['tenure_note_text']=AL+' '+t if t else AL
    log.append(('musicians_'+pg,e,AL,t,x['tenure_note_text']))
for l in log: print(l[0][10:],l[1],'|',l[3],'=>',l[4])
if '--write' in sys.argv:
    B='outputs/full_run_pre_promote_backup_2026-10-02_farsky/raw/'; os.makedirs(B,exist_ok=True)
    for p in engine._cache: shutil.copy(engine.R+p+'.raw.json',B)
    shutil.copy('outputs/full_run/imperial_theaters.duckdb',B+'../'); shutil.copytree('outputs/full_run/parsed',B+'../parsed',dirs_exist_ok=True)
    engine.write_all(); json.dump(log,open('/tmp/audit6/farsky_log.json','w'),ensure_ascii=False,indent=1); print('WRITTEN')
