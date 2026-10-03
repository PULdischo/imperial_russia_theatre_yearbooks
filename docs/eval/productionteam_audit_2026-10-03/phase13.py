import sys,glob
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
n_by=__import__('collections').Counter()
for f in sorted(glob.glob(E.R+'productionteam_*.raw.json')):
    pg=f.split('/')[-1][:-9]
    for i,x in enumerate(E.load(pg)['entries']):
        hp=x.get('heading_path') or ''; parts=hp.split(' / ')
        if len(parts)>1 and parts[1] in ('Главный гардеробъ','Мѣстные гардеробы'):
            new=' / '.join([parts[0],'Отдѣлъ гардеробный']+parts[1:])
            log.append((pg,'e%03d'%(i+1),'heading_path',hp,new)); x['heading_path']=new; n_by[parts[1]]+=1
print(len(log),'changes;',dict(n_by),len(fails),'fails')
