import duckdb,pandas as pd
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
df=c.execute("""select l.person_id, e.entry_id, e.page_id, s.season, s.entity_type, s.city, e.list_number,
 e.family_name_clean fam, e.first_name_clean fn, e.patronymic_clean pat, e.family_name rfam, e.first_name rfn, e.patronymic rpat, e.heading_path_clean hp, s.printed_page_number ppn
 from analysis.person_entry e join entities.person_link l using(entry_id) join entities.person p on p.person_id=l.person_id and p.superseded_by_person_id is null
 join raw.source_pages s using(page_id)""").df()
df.to_pickle('/private/tmp/claude-502/x/entries.pkl')
print(len(df),df.person_id.nunique())
print(df.entity_type.value_counts()); print(df.season.value_counts().sort_index().to_string()); print(df.city.value_counts())
print(df.sample(8,random_state=1)[['fam','fn','pat','rfam','rfn','rpat']])
