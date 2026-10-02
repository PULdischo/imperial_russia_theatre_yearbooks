import json,glob,re,shutil,os,sys
WRITE='--write' in sys.argv
B='outputs/full_run_pre_promote_backup_2026-10-02_headings/'
log=[];touched=set()
for f in sorted(glob.glob('outputs/full_run/raw/musicians_*.raw.json')):
    d=json.load(open(f)); ch=False; pg=os.path.basename(f)[:-9]
    for i,e in enumerate(d['entries']):
        h=e.get('heading_path')
        if not h: continue
        n=re.sub(r'(Оркестр|оркестр)(?!ъ|ы|ов|а|у|о)',r'\1ъ',h) if ('Оркестр оперы' in h or 'Оперный оркестр' in h) else h
        if pg=='musicians_1898-99_SP_p006' and 'Бібліотеки' in n: n=n.replace('Бібліотеки','Бблiотеки')
        if n!=h: e['heading_path']=n; ch=True; log.append((pg,i+1,h,n))
    if ch:
        touched.add(pg)
        if WRITE:
            os.makedirs(B+'raw',exist_ok=True); shutil.copy(f,B+'raw/'); json.dump(d,open(f,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
print(len(log),'rows on',len(touched),'pages')
import collections; print(collections.Counter((a,b) for _,_,a,b in log).most_common(30))
if WRITE:
    shutil.copy('outputs/full_run/imperial_theaters.duckdb',B); shutil.copytree('outputs/full_run/parsed',B+'parsed',dirs_exist_ok=True)
    json.dump(log,open('/tmp/audit6/headings_log.json','w'),ensure_ascii=False,indent=1); print('WRITTEN')
