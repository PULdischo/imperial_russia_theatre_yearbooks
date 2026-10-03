import sys,json
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
def run(fn,*a,**k):
    try: fn(*a,**k)
    except Exception as ex: fails.append((a[:2],str(ex)[:220]))
run(E.set_field,PT+'1902-03_p003','e014','tenure','(съ 10 іюля 1903 г.)','(онъ-же Хлоповъ) (съ 10 іюля 1903 г.)',log)
run(E.set_field,PT+'1903-04_p003','e014','family','Холоповъ (онъ-же Хлоповъ)','Холоповъ',log)
run(E.set_field,PT+'1903-04_p003','e014','tenure','(съ 10 іюля 1903 г.). Оставилъ службу 1 марта 1904 г.','(онъ-же Хлоповъ) (съ 10 іюля 1903 г.). Оставилъ службу 1 марта 1904 г.',log)
run(E.replace_in,PT+'1904-05_p003','e019','tenure_note_text','онъ же','онъ-же',log)
print(len(log),'changes;',len(fails),'fails'); [print(f) for f in fails]
