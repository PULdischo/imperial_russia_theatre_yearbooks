import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
pg='productionteam_1898-99_p002'
for n in range(17,25):
    x=E.ent(pg,'e%03d'%n); old=x['heading_path']
    try:
        assert old.startswith('С.-ПЕТЕРБУРГЪ / Отдѣлъ декораціонный / '),old
        x['heading_path']='МОСКВА / '+old[len('С.-ПЕТЕРБУРГЪ / '):]; log.append((pg,'e%03d'%n,'heading_path',old,x['heading_path']))
    except AssertionError as ex: fails.append((pg,n,str(ex)))
print(len(log),'changes;',len(fails),'fails')
