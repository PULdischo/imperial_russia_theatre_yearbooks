import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
for pg,e,old,new in [('1901-02_p000','e001','Аллегрі','Аллегри'),('1890-91_p001','e020','Педдерь','Педдеръ'),('1894-95_p002','e010','Вивьень де-Шатобріанъ','Вивьенъ де-Шатобріанъ'),('1896-97_p001','e003','Зыбінь','Зыбинъ'),
 ('1890-91_p001','e014','Пипарь','Пипаръ'),('1891-92_p001','e015','Пипарь','Пипаръ'),('1899-00_p002','e002','Пипарь','Пипаръ'),('1901-02_p001','e023','Пипарь','Пипаръ'),('1905-06_p001','e009','Семирадскій','Семирадзкій')]:
    try: E.set_field(PT+pg,e,'family',old,new,log)
    except Exception as ex: fails.append((pg,e,str(ex)[:150]))
print(len(log),'changes;',len(fails),'fails'); [print(f) for f in fails]
