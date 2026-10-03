import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
for pg,e,old,new in [('1900-01_p001','e010','Бергёръ','Бергеръ'),('1895-96_p003','e006','Бьєнвеню','Бьенвеню'),('1899-00_p003','e025','Бьєнвеню','Бьенвеню'),('1900-01_p002','e011','Жулєевъ','Жуляевъ'),('1893-94_p002','e022','Мєтловъ','Метловъ'),('1894-95_p002','e026','Мєтловъ','Метловъ'),('1900-01_p002','e006','Офicerова','Офицерова'),('1901-02_p000','e018','Шарбє','Шарбе')]:
    try: E.set_field(PT+pg,e,'family',old,new,log)
    except Exception as ex: fails.append((pg,e,str(ex)[:150]))
print(len(log),'changes;',len(fails),'fails'); [print(f) for f in fails]
