import sys, duckdb
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
for pref in sys.argv[1:]:
    p = con.execute("select cast(person_id as varchar), display_name from entities.person where cast(person_id as varchar) like ? and superseded_by_person_id is null", [pref + '%']).fetchall()
    assert len(p) == 1, (pref, p)
    print('=====', p[0][1], p[0][0][:8])
    for r in con.execute("""select sp.season, sp.city, e.entity_type, regexp_replace(l.entry_id,'^[a-z]+_[0-9-]+_(?:(?:SP|MSK)_)?','') pg, e.first_name, e.patronymic, coalesce(e.instrument,''), substr(coalesce(e.rank_or_title,''),1,22), substr(coalesce(e.heading_path,''),-28), substr(coalesce(e.tenure_note_text,''),1,75)
        from entities.person_link l join raw.person_entry e using(entry_id) join raw.source_pages sp on sp.page_id=e.page_id
        where cast(l.person_id as varchar)=? order by sp.season, sp.city, l.entry_id""", [p[0][0]]).fetchall(): print(' ', r)
