import pandas as pd
class stats:
    @staticmethod
    def chisquare(o,e):
        import numpy as np
        o=np.array(o,float);e=np.array(e,float)
        return round(float(((o-e)**2/e).sum()),1),'df',len(o)-1
sub=pd.read_pickle('/private/tmp/claude-502/x/sub.pkl'); d=pd.read_pickle('/private/tmp/claude-502/x/d2.pkl'); v=pd.read_pickle('/private/tmp/claude-502/x/var.pkl')
def kind(r):
    ch=[f for f in('fam','fn','pat') if r[f] in('sub_letter','sub_whole')]
    if len(ch)>1: return 'multi-field'
    f=ch[0]
    return {'fam':'surname','fn':'first name','pat':'patronymic'}[f]+(' (1-2 letters)' if r[f]=='sub_letter' else ' (different)')
sub['kind']=sub.apply(kind,axis=1)
print(sub.kind.value_counts())
ent=d.groupby(['season','entity_type']).size().unstack(fill_value=0)
sub['n']=1
t=sub.groupby(['s_new','list']).size().unstack(fill_value=0).reindex(ent.index,fill_value=0)
print(t.assign(All=t.sum(1)).to_string())
print((t/ent*1000).round(1).to_string())
tot=ent.sum(); print(t.sum(), (t.sum()/tot*1000).round(1))
# per season total
ss=t.sum(1); es=ent.sum(1)
print((ss/es*1000).round(1).to_string())
print('chi2 season', stats.chisquare(ss, es/es.sum()*ss.sum()))
tl=t.sum(0); el=ent.sum(0).reindex(tl.index)
print('chi2 list', stats.chisquare(tl, el/el.sum()*tl.sum()))
print(sub.groupby('city').size(), d.groupby('city').size())
print(pd.crosstab(sub['list'],sub.kind))
print(sub.same_season.sum())
# persons with >1 substantive
print(sub.groupby('person_id').size().value_counts())
# surname-in-two-lists TheaterSchoolStaff
t.to_csv('/private/tmp/claude-502/x/t.csv'); sub.to_pickle('/private/tmp/claude-502/x/sub2.pkl')
