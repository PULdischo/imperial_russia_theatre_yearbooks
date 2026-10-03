import sys,json
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
allfails=[];alllog=[]
for ph in sys.argv[1].split(','):
    ns={'__name__':'phase','E':E}
    sys.argv_backup=sys.argv; sys.argv=[ph]   # no --write inside phases
    exec(open(f'/tmp/audit8/{ph}.py').read(),ns)
    sys.argv=sys.argv_backup
    allfails+=ns['fails']; alllog+=ns['log']
print('TOTAL',len(alllog),'changes;',len(allfails),'fails')
if '--write' in sys.argv and not allfails:
    E.write_all(); json.dump(alllog,open('/tmp/audit8/all_log.json','w'),ensure_ascii=False,indent=1); print('WRITTEN',len(E._c),'pages')
