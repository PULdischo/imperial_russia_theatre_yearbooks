"""Stage 5: load parsed CSVs (from parse_and_validate.py) into a DuckDB file
with two schemas -- `raw` (verbatim, exactly as parsed, the reproducibility
guarantee) and `analysis` (normalized/derived, built from `raw` via SQL,
never hand-edited). See docs/research_questions.md for the two-layer
rationale and docs/pipeline.md for the full stage sketch.

Usage:
    python pipeline/build_duckdb.py --parsed-dir outputs/pilot/parsed \
        --manifest docs/eval/gold/source_pages.csv \
        --db outputs/pilot/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

# tables that may legitimately be empty/absent for a given run (e.g. a pilot
# with no BalletArtists page would have zero person_entry_credit rows)
RAW_TABLES = [
    "source_pages", "person_entry", "person_entry_service", "person_entry_credit",
    "event_entry", "event_entry_performance",
]


def load_raw_schema(con: duckdb.DuckDBPyConnection, parsed_dir: Path, manifest: Path) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    # source_pages comes from the manifest, not outputs/parsed (parse_and_validate.py
    # doesn't touch it -- it's Stage 1/2 output, already schema-conformant)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.source_pages AS
        SELECT * FROM read_csv_auto('{manifest.as_posix()}', header=true)
    """)
    for table in RAW_TABLES:
        if table == "source_pages":
            continue
        csv_path = parsed_dir / f"{table}.csv"
        if not csv_path.exists():
            print(f"skip (no data yet): {table}")
            continue
        con.execute(f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_csv_auto('{csv_path.as_posix()}', header=true, all_varchar=true)
        """)
        n = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        print(f"raw.{table}: {n} rows")


def build_analysis_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Derived layer. Kept intentionally small for now -- add normalization/
    entity-resolution rules here as they're developed (see
    docs/research_questions.md), always as new columns/tables on top of
    `raw`, never overwriting it."""
    con.execute("CREATE SCHEMA IF NOT EXISTS analysis")

    tables = [t[0] for t in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
    ).fetchall()]

    if "person_entry" in tables:
        # Two known, recurring VLM output quirks (docs/eval/known_issues.md
        # #2 and #3) turned out NOT to respond to prompt fixes on re-test --
        # both are mechanical/regex-shaped, so they're normalized here in the
        # analysis layer instead of chased further in the prompt. raw.person_entry
        # keeps the model's literal heading_path untouched.
        con.execute(r"""
            CREATE OR REPLACE TABLE analysis.person_entry AS
            WITH step1 AS (
                SELECT *,
                    regexp_extract(heading_path, '[,:]?\s*([IVXLC]+\.?\s*кл\.?):?\s*$', 1)
                        AS _extracted_class,
                    regexp_replace(heading_path, '[,:]?\s*([IVXLC]+\.?\s*кл\.?):?\s*$', '')
                        AS _heading_no_class
                FROM raw.person_entry
            ),
            step2 AS (
                SELECT * EXCLUDE (_extracted_class, _heading_no_class),
                    CASE WHEN trim(service_class) <> '' THEN service_class
                         WHEN _extracted_class <> '' THEN _extracted_class
                         ELSE service_class END AS service_class_clean,
                    CASE WHEN _extracted_class <> '' THEN _heading_no_class
                         ELSE heading_path END AS _heading_step2
                FROM step1
            ),
            step3 AS (
                SELECT * EXCLUDE (_heading_step2),
                    CASE WHEN institution <> '' AND starts_with(_heading_step2, institution || ' / ')
                         THEN substr(_heading_step2, length(institution) + 4)
                         ELSE _heading_step2
                    END AS heading_path_clean
                FROM step2
            ),
            step4 AS (
            SELECT *,
                -- best-effort single "role" value, derived from the cleaned
                -- breadcrumb rather than asking the model to split it (see
                -- docs/schema.md's heading_path note on why that split was
                -- collapsed after the roster extraction smoke test)
                trim(list_extract(str_split(heading_path_clean, ' / '),
                     len(str_split(heading_path_clean, ' / ')))) AS role_normalized,
                -- docs/eval/known_issues.md #32: raw.person_entry.instrument
                -- sometimes holds non-instrument text instead of (or as well
                -- as) a real instrument -- a "(см. ...)" cross-reference note
                -- (21 rows, same cross-reference convention as issue #29,
                -- captured into the wrong field on this specific appearance)
                -- or a resignation/transfer continuation sentence that
                -- belongs with tenure_note_text (2 rows). NULL those out here
                -- rather than let a query treat a cross-reference pointer or
                -- a resignation note as if it were the instrument someone
                -- played; the continuation-note text is preserved (moved into
                -- tenure_note_text_clean below), not discarded.
                -- NOTE: uses regexp_matches(), not the `~` operator -- `~`
                -- silently fails to match plain Cyrillic text (even a bare
                -- prefix, even with no anchor) in this DuckDB build
                -- (v1.5.5), confirmed by direct comparison; regexp_matches()
                -- with the identical pattern works correctly.
                CASE
                    WHEN instrument LIKE 'см.%'
                      OR regexp_matches(instrument, '^(Оставилъ службу|Переведенъ)')
                    THEN NULL
                    ELSE instrument
                END AS instrument_clean,
                -- docs/eval/known_issues.md #27/#34: 79 Graduates rows print
                -- "Surname, Firstname." as one string in family_name instead
                -- of splitting into family_name/first_name the way every
                -- other entity_type does -- confirmed uniform across all 79
                -- (no patronymic ever printed in this roll-call-style list,
                -- no ordinals, single comma). Split here rather than in
                -- Tier 1 directly so a non-Graduates family_name with an
                -- incidental comma is never touched.
                -- BalletArtists/Musicians ordinal-suffix misplacement bug
                -- (found while identity-linking Graduates against BalletArtists,
                -- 2026-08-20): a bare ordinal ("1-й"/"2-я"/...) that should be
                -- appended to family_name (the normal convention throughout
                -- this corpus, e.g. "Крылова 2-я") instead landed as the
                -- *entire* first_name value on some pages, shoving the real
                -- first_name into patronymic (sometimes as one word, "Дмитрій";
                -- sometimes as "FirstName Patronymic" together, "Дмитрій
                -- Спиридоновичъ" -- both shapes confirmed corpus-wide). 115
                -- rows total (77 BalletArtists, 38 Musicians; zero elsewhere).
                -- Confirmed via a single real case (two brothers, "Литавкинъ
                -- 1-й"/"2-й") that this isn't cosmetic: the same two real
                -- people fragment into 9 distinct raw (family,first,patronymic)
                -- triples across different seasons because of it -- directly
                -- inflating any distinct-person count taken from raw fields.
                -- BalletArtists name-field audit (2026-08-20, RG's explicit
                -- request after the identity-linking work above surfaced the
                -- first instance): three more shapes of essentially the same
                -- ordinal-misplacement bug, plus a dropped-surname case and a
                -- Latin-homoglyph corruption pattern, all confirmed directly
                -- (corpus cross-check and/or the scanned page) before fixing.
                -- Scoped to entity_type='BalletArtists' only for the new
                -- branches below -- Musicians/TheaterSchoolStaff/Administrators
                -- show some of these same shapes (confirmed by query) but
                -- weren't individually verified this pass; left for later
                -- (see docs/eval/known_issues.md #36).
                CASE
                    WHEN entity_type = 'Graduates'
                     AND (first_name IS NULL OR trim(first_name) = '')
                     AND regexp_matches(family_name, '^[^,]+,\s*[^,]+\.?\s*$')
                    THEN trim(regexp_extract(family_name, '^([^,]+),', 1))
                    WHEN regexp_matches(first_name, '^[0-9IVXІ]+-(й|я|е)$')
                     AND NOT regexp_matches(family_name, '\s[0-9IVXІ]+-(й|я|е)$')
                    THEN family_name || ' ' || first_name
                    -- docs/eval/known_issues.md #36: a real surname dropped
                    -- entirely, first_name promoted into family_name --
                    -- confirmed against the scanned page
                    -- (ForUpload_1901-02_Spisok_BalletArtistsSP.pdf p.73, an
                    -- unnumbered guest-artist entry between #33 and #34):
                    -- "Замбелли, Карлотта (съ 1 октября по 1 декабря 1901 г.)"
                    -- -- Carlotta Zambelli, a real guest ballerina, briefly
                    -- engaged Oct-Dec 1901. Single hand-verified instance, not
                    -- a general rule.
                    WHEN entity_type = 'BalletArtists' AND entry_id = 'balletartists_1901-02_SP_p001__e018'
                    THEN 'Замбелли'
                    -- Pattern B: ordinal + comma + real first_name run
                    -- together in first_name ("1-я, Анна"), patronymic intact.
                    -- 20 rows, confirmed BalletArtists-only.
                    WHEN entity_type = 'BalletArtists'
                     AND regexp_matches(first_name, '^[0-9IVXІ]+-(й|я|е),\s*\S')
                    THEN family_name || ' ' || regexp_extract(first_name, '^([0-9IVXІ]+-(?:й|я|е))', 1)
                    -- Pattern D: the ordinal landed in patronymic instead,
                    -- family_name has none. 9 rows in BalletArtists (e.g.
                    -- "Мендесъ" sisters "Анжелика"/"Джульетта", each
                    -- patronymic="1-я"/"2-я"); extended 2026-08-21 to
                    -- Musicians/Administrators/TheaterSchoolStaff after a
                    -- follow-up audit found the same shape corpus-wide (1
                    -- more row: Musicians' "Эйхенвальдъ" sisters Ида/Надежда,
                    -- same pattern -- confirmed via the raw corpus, not the
                    -- scanned page, since it exactly matches an
                    -- already-page-verified BalletArtists shape and the
                    -- sisters' own other rows already spell it out
                    -- unambiguously). Pattern B/E and the Latin-homoglyph
                    -- corruption below were checked the same pass and
                    -- confirmed genuinely absent outside BalletArtists (zero
                    -- rows, not just unverified) -- left BalletArtists-only.
                    WHEN entity_type IN ('BalletArtists', 'Musicians', 'Administrators', 'TheaterSchoolStaff')
                     AND regexp_matches(trim(patronymic), '^[0-9IVXІ]+-(й|я|е)$')
                     AND NOT regexp_matches(family_name, '\s[0-9IVXІ]+-(й|я|е)$')
                    THEN family_name || ' ' || trim(patronymic)
                    -- Pattern E: the ordinal landed in rank_or_title instead
                    -- -- family_name/first_name/patronymic are all otherwise
                    -- correct and complete here, just missing the ordinal
                    -- suffix itself. 24 rows, found in a follow-up sweep of
                    -- BalletArtists fields beyond just the three name columns
                    -- (docs/eval/known_issues.md #37).
                    WHEN entity_type = 'BalletArtists'
                     AND regexp_matches(trim(rank_or_title), '^[0-9IVXІ]+-(й|я|е)$')
                     AND NOT regexp_matches(family_name, '\s[0-9IVXІ]+-(й|я|е)$')
                    THEN family_name || ' ' || trim(rank_or_title)
                    -- Latin-homoglyph corruption: a handful of BalletArtists
                    -- family_name values have one or more Latin lookalike
                    -- characters substituted into an otherwise-Cyrillic word
                    -- (17 rows total). Most are a single swapped letter,
                    -- handled by the translate() wrapping this whole CASE
                    -- (below); these three have a multi-character garble
                    -- translate() can't fix character-by-character, each
                    -- confirmed instead by finding the same real person's
                    -- correctly-spelled name elsewhere in the same
                    -- entity_type (matching first_name+patronymic, in
                    -- Грекова's case matching ordinal+first_name+patronymic
                    -- across 8 other seasons).
                    WHEN entity_type = 'BalletArtists' AND family_name = 'Гавликowsкій' THEN 'Гавликовскій'
                    WHEN entity_type = 'BalletArtists' AND family_name = 'Спрышиńskaя' THEN 'Спрышинская'
                    WHEN entity_type = 'BalletArtists' AND family_name = 'Гrekова 1-я' THEN 'Грекова 1-я'
                    WHEN entity_type = 'BalletArtists' AND family_name = 'Гrekова 2-я' THEN 'Грекова 2-я'
                    -- "Мендесь" (ь) vs "Мендесъ" (ъ): initially left as
                    -- possible genuine period spelling variance, but RG
                    -- asked directly whether it was OCR or real -- checked
                    -- both instances against the scanned page
                    -- (ForUpload_1906-07_Spisok_BalletArtistsMoscow.pdf p.52
                    -- #52: "Мендесъ, Джульетта Іосифовна" -- unambiguously
                    -- ъ) and it's a misread, not variance: every instance
                    -- checked (this one and the two "Джулъетта" cases below)
                    -- turned out to be the ordinary, standard spelling once
                    -- the actual page was read -- a hard-sign/soft-sign
                    -- (ъ/ь) OCR confusion, a well-known visually-similar
                    -- Cyrillic character pair. 2 rows.
                    WHEN entity_type = 'BalletArtists' AND family_name = 'Мендесь' THEN 'Мендесъ'
                    -- The one Latin-corruption case translate() genuinely
                    -- couldn't fix ("Тиistroва") turned out to have a
                    -- perfectly ordinary correct spelling once the actual
                    -- page was checked -- confirmed against the scanned page
                    -- (ForUpload_1893-94_Spisok_BalletArtistsSP.pdf, p.62,
                    -- entry #135): "Тистрова, Марія Ѳедоровна (съ 10 декабря
                    -- 1873 г.)" -- plain Cyrillic, no complexity at all; the
                    -- extraction just inserted spurious Latin letters into a
                    -- simple name.
                    WHEN entity_type = 'BalletArtists' AND entry_id = 'balletartists_1893-94_SP_p005__e002'
                    THEN 'Тистрова'
                    ELSE family_name
                END AS family_name_pre,
                CASE
                    WHEN entity_type = 'Graduates'
                     AND (first_name IS NULL OR trim(first_name) = '')
                     AND regexp_matches(family_name, '^[^,]+,\s*[^,]+\.?\s*$')
                    THEN rtrim(trim(regexp_extract(family_name, ',\s*([^,]+?)\.?\s*$', 1)), '.')
                    -- docs/eval/known_issues.md #34: a rarer, distinct bug --
                    -- first_name and patronymic run together with no space at
                    -- all ("АннаПетровна"), confirmed against the source page
                    -- (ForUpload_1890-91_TheaterSchoolReport.pdf, printed as
                    -- two words: "Анна Петровна"). Only 3 rows corpus-wide
                    -- have this exact no-hyphen, no-space, capital-letter-
                    -- boundary shape (checked directly, not inferred) -- the
                    -- hyphenated-compound-first-name case ("Іоганъ-Фридрихъ")
                    -- is a real, different, and far more common pattern this
                    -- deliberately does NOT touch.
                    WHEN entity_type = 'Graduates'
                     AND (patronymic IS NULL OR trim(patronymic) = '')
                     AND first_name NOT LIKE '%-%'
                     AND regexp_matches(first_name, '^[А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+[А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+$')
                    THEN regexp_extract(first_name, '^([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+?)[А-ЯЁІѢѲѴ]', 1)
                    -- ordinal-misplacement fix (see family_name_clean above):
                    -- the real first_name is patronymic's first word, whether
                    -- patronymic holds just that word alone or "FirstName
                    -- Patronymic" run together.
                    WHEN regexp_matches(first_name, '^[0-9IVXІ]+-(й|я|е)$')
                    THEN regexp_extract(trim(patronymic), '^(\S+)', 1)
                    WHEN entity_type = 'BalletArtists' AND entry_id = 'balletartists_1901-02_SP_p001__e018'
                    THEN 'Карлотта'
                    -- "Джулъетта" (ъ) vs "Джульетта" (ь): same ъ/ь OCR
                    -- confusion as "Мендесь" above -- confirmed a misread by
                    -- checking two of the three instances directly against
                    -- the scanned page (ForUpload_1897-98_Spisok_BalletArtistsMoscow.pdf
                    -- p.94 #60 and ForUpload_1903-04_Spisok_BalletArtistsMoscow.pdf
                    -- p.106 #53, both unambiguously print "Джульетта" with ь).
                    -- 3 rows.
                    WHEN entity_type = 'BalletArtists' AND first_name = 'Джулъетта'
                    THEN 'Джульетта'
                    -- "Пуни, ЛеонтинаКонстанція" (issue #34): flagged then as
                    -- an unresolved no-separator concatenation, since
                    -- "Констанція" doesn't have a typical Russian patronymic
                    -- suffix. RG's context (this is Cesare Pugni's family --
                    -- her brother is listed two entries away as "Пуни,
                    -- Николай Цезаревичъ", literally "son of Cesare")
                    -- pointed at the right answer: confirmed against the
                    -- scanned page (ForUpload_1905-06_Spisok_BalletArtistsSP.pdf
                    -- p.18 #80) it's printed "Пуни, Леонтина - Констанція" --
                    -- a genuine hyphenated compound first name (same pattern
                    -- as "Іоганъ-Фридрихъ" elsewhere), not first_name+
                    -- patronymic. No patronymic at all, consistent with
                    -- every other foreign-origin artist already confirmed in
                    -- this corpus. The hyphen itself was mangled three
                    -- different ways across 5 rows (dropped entirely, run
                    -- together with no separator; or captured with a stray
                    -- leading "-" on whatever landed in patronymic instead)
                    -- -- reassembled here regardless of which shape it took.
                    WHEN entity_type = 'BalletArtists' AND family_name = 'Пуни'
                     AND (first_name = 'ЛеонтинаКонстанція'
                          OR (first_name = 'Леонтина' AND patronymic IN ('Констанція', '-Констанція')))
                    THEN 'Леонтина-Констанція'
                    -- Pattern B (see family_name_clean): the real first_name
                    -- is whatever follows the ordinal+comma.
                    WHEN entity_type = 'BalletArtists'
                     AND regexp_matches(first_name, '^[0-9IVXІ]+-(й|я|е),\s*\S')
                    THEN trim(regexp_extract(first_name, ',\s*(.+)$', 1))
                    -- Pattern C: first_name holds "FirstName Patronymic" run
                    -- together as two words, patronymic blank -- 54 rows in
                    -- BalletArtists (known_issues.md #36). Extended
                    -- 2026-08-21 to Musicians/Administrators/
                    -- TheaterSchoolStaff after a follow-up corpus-wide audit
                    -- quantified the same shape there: 149/11/84 rows
                    -- respectively (244 total, more than 4x the original
                    -- BalletArtists count) -- confirmed by direct sample
                    -- inspection to be the identical shape, not a
                    -- lookalike (known_issues.md #43). Graduates and
                    -- ProductionTeam checked the same pass and confirmed
                    -- genuinely zero rows of this shape (Graduates has its
                    -- own different concatenation bug, already fixed
                    -- separately above -- #34).
                    WHEN entity_type IN ('BalletArtists', 'Musicians', 'Administrators', 'TheaterSchoolStaff')
                     AND (patronymic IS NULL OR trim(patronymic) = '')
                     AND regexp_matches(trim(first_name), '^\S+\s+\S+(на|вна|ична|вичъ|евичъ|ичъ)$')
                    THEN regexp_extract(trim(first_name), '^(\S+)', 1)
                    ELSE first_name
                END AS first_name_pre,
                CASE
                    WHEN entity_type = 'Graduates'
                     AND (patronymic IS NULL OR trim(patronymic) = '')
                     AND first_name NOT LIKE '%-%'
                     AND regexp_matches(first_name, '^[А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+[А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+$')
                    THEN regexp_extract(first_name, '([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+)$', 1)
                    -- ordinal-misplacement fix: the real patronymic, if any
                    -- survived, is whatever follows that first word -- NULL
                    -- when patronymic held only the bare first_name (nothing
                    -- to recover for that row, not invented).
                    WHEN regexp_matches(first_name, '^[0-9IVXІ]+-(й|я|е)$')
                    THEN NULLIF(trim(regexp_replace(trim(patronymic), '^\S+\s*', '')), '')
                    -- Pattern B: patronymic was already correct/untouched.
                    -- Pattern D: the ordinal that WAS patronymic has moved to
                    -- family_name_clean -- nothing real is left to recover.
                    -- Extended 2026-08-21 alongside family_name_clean's
                    -- Pattern D branch above -- same corpus-wide audit.
                    WHEN entity_type IN ('BalletArtists', 'Musicians', 'Administrators', 'TheaterSchoolStaff')
                     AND regexp_matches(trim(patronymic), '^[0-9IVXІ]+-(й|я|е)$')
                    THEN NULL
                    -- Pattern C (see first_name_clean): the real patronymic is
                    -- first_name's second word. Extended 2026-08-21 alongside
                    -- first_name_clean's Pattern C branch above.
                    WHEN entity_type IN ('BalletArtists', 'Musicians', 'Administrators', 'TheaterSchoolStaff')
                     AND (patronymic IS NULL OR trim(patronymic) = '')
                     AND regexp_matches(trim(first_name), '^\S+\s+\S+(на|вна|ична|вичъ|евичъ|ичъ)$')
                    THEN regexp_extract(trim(first_name), '\s+(\S+)$', 1)
                    -- "Пуни, Леонтина-Констанція" (see first_name_clean): no
                    -- real patronymic, whatever landed here was really the
                    -- second half of her hyphenated first name.
                    WHEN entity_type = 'BalletArtists' AND family_name = 'Пуни'
                     AND (first_name = 'ЛеонтинаКонстанція'
                          OR (first_name = 'Леонтина' AND patronymic IN ('Констанція', '-Констанція')))
                    THEN NULL
                    ELSE patronymic
                END AS patronymic_pre,
                CASE
                    WHEN regexp_matches(instrument, '^(Оставилъ службу|Переведенъ)')
                    THEN trim(coalesce(rtrim(tenure_note_text, '.') || '. ', '') || instrument)
                    -- The one-off Флоринскій case that used to live here
                    -- (docs/eval/known_issues.md #28/#33, entry_id
                    -- theaterschoolstaff_1896-97_p000__e013: a resignation note
                    -- split off into its own fake person entry, family_name
                    -- literally "Оставилъ службу") is now handled generally, at
                    -- the raw layer, not as a one-off SQL patch here --
                    -- _repair_fragment_person_entries() in parse_and_validate.py
                    -- (known_issues.md #64, 2026-08-28) merges the fragment into
                    -- the preceding entry's tenure_note_text before raw.person_entry
                    -- is even built, and covers all 5 corpus-wide instances of
                    -- this shape (3 entity types), not just this one. Keeping
                    -- this branch here too would double-append the same note --
                    -- confirmed by the duplicate text this actually produced in
                    -- research.person_appearance before it was removed.
                    ELSE tenure_note_text
                END AS _tenure_note_text_step
            FROM step3
            ),
            -- Final pass: single-character Latin-lookalike homoglyph swaps
            -- (docs/eval/known_issues.md #36) -- a stray Latin letter
            -- substituted into an otherwise-Cyrillic name, e.g. "Милютинa"
            -- (Latin 'a') for "Милютина", "Iосифъ" (Latin 'I') for "Іосифъ".
            -- translate() only swaps exact single characters, so it can't
            -- touch the multi-character garbles already hand-fixed above
            -- (those are correct as of family_name_pre/first_name_pre) --
            -- applying it again here is a safe no-op for text that's already
            -- clean Cyrillic. Scoped to entity_type='BalletArtists', the only
            -- entity_type individually verified for this pattern this pass.
            --
            -- Also here: the tenure-date punctuation normalization RG asked
            -- for (2026-08-28) -- "let's make sure the clean version follows
            -- the (съ ... г.) convention." Confirmed by direct scan check
            -- (two full pages, zero exceptions -- musicians_1893-94_MSK_p001
            -- p.100, musicians_1892-93_SP_p003 p.99) that the printed page
            -- ALWAYS wraps the tenure date in a matched pair of parens; the
            -- model just drops the opening paren inconsistently (918 rows),
            -- sometimes both (1921 rows). Not a real printed variant, so this
            -- rewrites the *leading* "съ ... г." clause (with or without its
            -- own parens) into a single canonical "(съ ... г.)", leaving
            -- everything else in the string untouched -- including compound
            -- multi-period service dates ("съ ... г. по ... г. и съ ... г.",
            -- 35 confirmed corpus-wide, still captured whole) and text that
            -- doesn't start with a date at all (crossref/dual-role-
            -- parenthetical prefixes, 187 rows, deliberately left alone --
            -- out of scope for this specific convention). The inner
            -- non-greedy "г\." stop is what keeps a malformed no-closing-
            -- paren row (e.g. "съ ... г. Альтъ. † ... г.") from swallowing
            -- unrelated later sentences into the "date" -- verified against
            -- the full corpus, longest genuine match 68 chars, no runaway
            -- over-matches.
            step5 AS (
            SELECT * EXCLUDE (family_name_pre, first_name_pre, patronymic_pre, _tenure_note_text_step),
                -- RG's question while reviewing the rank_or_title split
                -- (2026-08-28): "aren't these ordinals stored in another
                -- field already?" -- checked, and no: all 24 BalletArtists
                -- rows where rank_or_title is a bare "1-я"/"2-я"/... name-
                -- disambiguation ordinal (see _rank_or_title_class below)
                -- have a family_name with NO ordinal suffix at all
                -- (confirmed by query, not assumed). This is the same class
                -- of bug as the ordinal-misplacement fixes already applied
                -- to first_name/patronymic just above (a bare ordinal
                -- landing in the wrong field) -- here it landed in
                -- rank_or_title instead. Relocate it onto family_name_clean,
                -- matching the corpus-wide convention documented in
                -- docs/schema.md's family_name row (`Алексѣева 1-я`),
                -- rather than classifying-and-discarding it.
                CASE WHEN entity_type = 'BalletArtists'
                      AND regexp_matches(rank_or_title, '^\d+-(я|й|е)\.?$')
                      AND NOT (trim(coalesce(family_name_pre,'')) ILIKE '%' || trim(rank_or_title) || '%')
                     THEN translate(family_name_pre, 'aceopxyivfACEOPXYIVF', 'асеорхуивфАСЕОРХУІВФ') || ' ' || trim(rank_or_title)
                     WHEN entity_type = 'BalletArtists'
                     THEN translate(family_name_pre, 'aceopxyivfACEOPXYIVF', 'асеорхуивфАСЕОРХУІВФ')
                     ELSE family_name_pre END AS family_name_clean,
                CASE WHEN entity_type = 'BalletArtists'
                     THEN translate(first_name_pre, 'aceopxyivfACEOPXYIVF', 'асеорхуивфАСЕОРХУІВФ')
                     ELSE first_name_pre END AS first_name_clean,
                CASE WHEN entity_type = 'BalletArtists'
                     THEN translate(patronymic_pre, 'aceopxyivfACEOPXYIVF', 'асеорхуивфАСЕОРХУІВФ')
                     ELSE patronymic_pre END AS patronymic_clean,
                -- RG's follow-up (2026-08-28) on rank_or_title_excluded_reason:
                -- "these exceptions really belong in other fields" -- rather
                -- than tag-and-drop dual-role/cross-reference notes ("(онъ же
                -- и режиссеръ)", "(см. СПБ. балетъ)"), relocate them onto
                -- tenure_note_text_clean, same convention already used for
                -- the instrument-field crossref fix (known_issues.md #66).
                -- Scan-verified first (RG: "Can we check these against the
                -- scans?") across all 9 distinct people covering the 24
                -- rows (Вальцъ, Чекетти, Гельцеръ x2 phrasing variants,
                -- Ивановъ 1-й, Аистовъ, Ширяевъ, Легатъ, Фарскій) -- 9/9
                -- confirmed the printed order is NOTE then DATE (e.g.
                -- "Вальцъ, Карлъ Ѳедоровичъ (онъ же и декораторъ) (съ 3
                -- октября 1861 г.)"), the reverse of a naive append -- this
                -- reconstructs that order rather than tacking the note onto
                -- the end. Also checked first: none of the 24 rows already
                -- carry this text in tenure_note_text (0/24 duplicates), so
                -- the relocation can't double up existing content.
                CASE
                    WHEN regexp_matches(rank_or_title, '^\(.*(онъ же|она же|см\.).*\)$', 'i')
                    THEN trim(trim(rank_or_title) || ' ' || coalesce(
                        regexp_replace(_tenure_note_text_step,
                            '^\(?(съ (?:.+?г\. (?:по|и) )*.+?г\.)\)?', '(\1)'), ''))
                    ELSE regexp_replace(
                        _tenure_note_text_step,
                        '^\(?(съ (?:.+?г\. (?:по|и) )*.+?г\.)\)?',
                        '(\1)'
                    )
                END AS tenure_note_text_clean,
                -- docs/schema.md's rank_or_title note (2026-08-28, RG-driven
                -- corpus exploration): the raw field conflates RANK
                -- (institutionally conferred status -- civil/court Table-of-
                -- Ranks grades, military ranks, court/Academy-of-Arts
                -- honorifics) with TITLE (how the Yearbook labels the entry
                -- -- occupational role, subject taught, workshop specialty),
                -- plus two shapes that are neither: a BalletArtists name-
                -- disambiguation ordinal ("1-я"/"2-я"/...), confirmed by
                -- query (not assumed) to pair a distinct patronymic with
                -- each ordinal within a shared surname -- the same device
                -- already baked into family_name elsewhere in the corpus
                -- (`Алексѣева 1-я`), not a seniority marker; and dual-role/
                -- cross-reference notes ("(онъ же и режиссеръ)", "(см. СПБ.
                -- балетъ)"), administrative notes conceptually closer to
                -- tenure_note_text (the crossref shape mirrors the
                -- instrument_clean fix above). Classification below was
                -- validated two ways before landing here: cross-checked
                -- byte-for-byte (0 mismatches over all 2208 non-blank
                -- corpus-wide values) against a Python reference
                -- implementation, and RG confirmed each ambiguous call
                -- individually (академикъ/профессоръ -> RANK, a conferred
                -- Academy of Arts distinction, not an occupation -- every
                -- checked example has the actual job already sitting in
                -- heading_path; "пот. поч. гражд." -> RANK, a conferred
                -- civil-estate status). The one remaining residual, RG asked
                -- checked against the scan directly ("Can we check these
                -- against the scans?") rather than guessed at: raw
                -- "по найму, Московскій пеховой" (2 rows, one person, both
                -- seasons) turned out to be an OCR misread of "по найму,
                -- Московскій цеховой" (confirmed against
                -- ForUpload_1902-03_Spisok_Administration.pdf p.128) --
                -- fixed at the raw layer (_OCR_MISREAD_CORRECTIONS in
                -- parse_and_validate.py), and "цеховой" (a craft-guild/
                -- artisan estate designation) is the same civil-estate-
                -- status category as "пот. поч. гражд." -> RANK.
                -- NOTE: uses regexp_matches(), not the `~` operator, and an
                -- explicit Cyrillic letter class instead of `\b`/`\w` --
                -- confirmed by direct testing that DuckDB's RE2 engine
                -- (v1.5.5) does not treat Cyrillic letters as word
                -- characters, so `\b`/`\w` silently fail on this corpus
                -- (see the instrument_clean `~`-operator note above for the
                -- same class of gotcha).
                CASE
                    WHEN trim(coalesce(rank_or_title,'')) = '' THEN NULL
                    WHEN regexp_matches(rank_or_title, '^по найму, Московскій цеховой', 'i') THEN 'RANK'
                    WHEN regexp_matches(rank_or_title, '^\d+-(я|й|е)\.?$') THEN 'EXCLUDED_ordinal'
                    WHEN regexp_matches(rank_or_title, '^\(.*(онъ же|она же|см\.).*\)$', 'i') THEN 'EXCLUDED_note'
                    WHEN regexp_matches(rank_or_title, '^(академикъ|профессоръ)\.?$', 'i') THEN 'RANK'
                    WHEN regexp_matches(rank_or_title, '^пот\. поч\. гражд\.', 'i') THEN 'RANK'
                    WHEN regexp_matches(rank_or_title,
                        '(^|[^а-яёіѣѳѵА-ЯЁІѢѲѴ])(сов|асс|секр|рег)[а-яёіѣѳѵА-ЯЁІѢѲѴ]*\.?|чина$|чина\.', 'i')
                        THEN 'RANK'
                    WHEN regexp_matches(rank_or_title,
                        '^(Солист[а-яёіѣѳѵА-ЯЁІѢѲѴ]*\s+(Двора|Его|Ея)|Заслуженн[а-яёіѣѳѵА-ЯЁІѢѲѴ]+\s+артист)|гофмейстер|шталмейстер|егермейстер|церемоніймейстер|статсъ-дам|фрейлин', 'i')
                        THEN 'RANK'
                    WHEN regexp_matches(rank_or_title,
                        '(генералъ|полковн|подполковн|поручикъ|подпоручикъ|штабсъ-капитанъ|штабсъ-ротмистръ|кап\.|капитанъ|ротмистръ|корнетъ|прапорщикъ|маіоръ|камеръ-юнкера|камергеръ)', 'i')
                        THEN 'RANK'
                    ELSE 'TITLE'
                END AS _rank_or_title_class
            FROM step4
            )
            SELECT * EXCLUDE (_rank_or_title_class),
                CASE WHEN _rank_or_title_class = 'RANK' THEN rank_or_title ELSE NULL END AS rank_clean,
                CASE WHEN _rank_or_title_class = 'TITLE' THEN rank_or_title ELSE NULL END AS title_clean,
                CASE _rank_or_title_class
                    WHEN 'EXCLUDED_ordinal' THEN 'name_disambiguation_ordinal'
                    WHEN 'EXCLUDED_note' THEN 'dual_role_or_crossref_note'
                    WHEN 'EXCLUDED_needs_review' THEN 'needs_review'
                    ELSE NULL
                END AS rank_or_title_excluded_reason
            FROM step5
        """)
        print("analysis.person_entry built (+ heading_path_clean, service_class_clean, "
              "role_normalized, instrument_clean, tenure_note_text_clean, "
              "rank_clean, title_clean, rank_or_title_excluded_reason, "
              "family_name_clean, first_name_clean, patronymic_clean)")

    if "person_entry_credit" in tables and "person_entry" in tables:
        # Known VLM output quirk (docs/eval/known_issues.md #23): credit_summary_text
        # sentences of the shape "Въ N категорияхъ—X" (e.g. "Въ 7 балетахъ—21")
        # carry two different numbers -- N (count of distinct productions) and
        # X (count of total performances) -- and the model's own structured
        # `count` field, which becomes raw.person_entry_credit.category_credit_count,
        # sometimes captures N where X belongs (confirmed directly against
        # raw JSON on multiple entries). X is recoverable deterministically:
        # it's the same verbatim credit_summary_text already used to backfill
        # category_production_count (schemas/roster.py's _PRODUCTION_COUNT_RE),
        # just the second number instead of the first. Same playbook as issue
        # #3 (service_class_clean above) -- raw.person_entry_credit keeps the
        # model's literal count untouched; this only overrides the *clean*
        # column, and only when the row's own label matches a "N label—X"
        # pair in its own entry's credit_summary_text AND the stored count
        # equals N rather than X (so a coincidental N==X, or a row whose
        # label doesn't appear in this exact phrasing, is left alone).
        con.execute(r"""
            CREATE OR REPLACE TABLE analysis.person_entry_credit AS
            WITH joined AS (
                SELECT c.*,
                    regexp_extract(e.credit_summary_text,
                        '[Вв]ъ\s+(\d+)\s+' || c.label || '\s*[—-]\s*([\d.]+)', 1) AS _n_extracted,
                    regexp_extract(e.credit_summary_text,
                        '[Вв]ъ\s+(\d+)\s+' || c.label || '\s*[—-]\s*([\d.]+)', 2) AS _x_extracted
                FROM raw.person_entry_credit c
                JOIN raw.person_entry e ON c.entry_id = e.entry_id
            )
            SELECT * EXCLUDE (_n_extracted, _x_extracted),
                CASE WHEN credit_type = 'category_totals'
                          AND _n_extracted <> '' AND _x_extracted <> ''
                          AND TRY_CAST(category_credit_count AS DOUBLE) = TRY_CAST(_n_extracted AS DOUBLE)
                          AND TRY_CAST(_n_extracted AS DOUBLE) <> TRY_CAST(_x_extracted AS DOUBLE)
                     THEN _x_extracted
                     ELSE category_credit_count
                END AS category_credit_count_clean
            FROM joined
        """)
        n_corrected = con.execute("""
            SELECT count(*) FROM analysis.person_entry_credit
            WHERE category_credit_count_clean <> category_credit_count
        """).fetchone()[0]
        print(f"analysis.person_entry_credit built (+ category_credit_count_clean, "
              f"{n_corrected} rows corrected)")

    if "event_entry" in tables and "source_pages" in tables:
        # Completeness reconciliation (docs/schema.md's event_status note).
        # A model recall failure produces no row at all for a (date, theater)
        # cell, which is indistinguishable from "nothing happened here" if
        # you only look at raw.event_entry -- this makes that gap
        # queryable instead of invisible, by comparing what was captured
        # against an expected date x theater grid and inserting an
        # event_status='not_captured' placeholder for anything missing.
        # Two real data-quality bugs were found and fixed getting here (both
        # upstream of this query, not worked around inside it): parse_russian_date
        # was assigning the wrong calendar year for season-spanning printed
        # ranges like "1896-1897 гг." (schemas/dates.py), and theater names
        # need prefix/alias normalization -- post-1898-99 pages consistently
        # append "театръ"/"театр", and "Маріинскій" is sometimes spelled without
        # its pre-reform "і" ("Мариинскій") -- both handled by theater_canonical
        # below rather than by touching the verbatim raw.theater column.
        con.execute(r"""
            CREATE OR REPLACE TABLE analysis.event_entry AS
            WITH base AS (
                SELECT *,
                       TRY_CAST(receipts_rubles AS INTEGER) * 100
                           + TRY_CAST(receipts_kopecks AS INTEGER) AS receipts_total_kopecks,
                       TRY_CAST(date_undate AS DATE) AS date_parsed,
                       -- RG's 2026-08-24 venue-accuracy audit: on a day when
                       -- one specific theater (not its whole city) was dark,
                       -- `theater` is sometimes written as a compound
                       -- "[city group]. [theater name]" string (e.g.
                       -- "Московскіе театры. Большой") instead of the theater
                       -- name alone -- confirmed against the scan
                       -- (ForUpload_1896-97_Repertoire.pdf p.2-3: Большой is
                       -- dark that week while Малый has shows, i.e. a real
                       -- specific-theater closure, not a whole-city one) --
                       -- so this checks contains(), not just starts_with(),
                       -- to still resolve those. Genuine whole-city/whole-
                       -- table dark days ("С.-Петербургскіе театры",
                       -- "Московскіе театры", or the column-header text
                       -- "Мѣсяцъ, день и число" leaking in when literally
                       -- every theater was dark) correctly stay NULL -- there
                       -- is no single theater to name for those.
                       CASE
                           WHEN contains(theater, 'Маріинскій') OR contains(theater, 'Мариинскій')
                               THEN 'Маріинскій'
                           WHEN contains(theater, 'Александринскій') THEN 'Александринскій'
                           WHEN contains(theater, 'Михайловскій') THEN 'Михайловскій'
                           WHEN contains(theater, 'Большой') THEN 'Большой'
                           WHEN contains(theater, 'Малый') THEN 'Малый'
                           WHEN contains(theater, 'Новый') THEN 'Новый'
                           ELSE NULL
                       END AS theater_canonical
                FROM raw.event_entry
            ),
            -- Which of the 6 known theaters existed for a given season --
            -- SP's 3 theaters run the whole 1890/91-1907/08 span; Moscow's
            -- third venue (Новый театръ) only from 1898-99 on, per
            -- docs/structural_survey.md.
            season_years AS (
                SELECT DISTINCT season, TRY_CAST(left(season, 4) AS INTEGER) AS start_year
                FROM raw.source_pages WHERE entity_type = 'Repertoire'
            ),
            theater_roster AS (
                SELECT season, theater, city FROM season_years, (VALUES
                    ('Маріинскій', 'SP'), ('Александринскій', 'SP'), ('Михайловскій', 'SP'),
                    ('Большой', 'Moscow'), ('Малый', 'Moscow')
                ) AS t(theater, city)
                UNION ALL
                SELECT season, 'Новый', 'Moscow' FROM season_years WHERE start_year >= 1898
            ),
            -- Expected city set per page: pre-1898-99 pages combine both
            -- cities' theaters (hardcoded -- true regardless of what
            -- survived extraction); 1898-99-on pages are single-city blocks,
            -- so the expected city is whichever city's sessions actually
            -- appear for that page. Known limit: if a post-split page lost
            -- 100% of its sessions, there's no surviving evidence of which
            -- city it was, so no gaps can be synthesized for it.
            page_cities AS (
                SELECT sp.page_id, sp.season,
                    CASE WHEN sy.start_year < 1898 THEN ['SP', 'Moscow']
                         ELSE (SELECT list(DISTINCT b.city) FROM base b WHERE b.page_id = sp.page_id)
                    END AS expected_cities
                FROM raw.source_pages sp
                JOIN season_years sy USING (season)
                WHERE sp.entity_type = 'Repertoire'
            ),
            -- Expected date range per page: min/max of its own captured
            -- dates, assuming (per docs/schema.md) the source prints one
            -- row per calendar day with no skipped days in between.
            page_dates AS (
                SELECT page_id, min(date_parsed) AS min_date, max(date_parsed) AS max_date
                FROM base WHERE date_parsed IS NOT NULL
                GROUP BY page_id
            ),
            expected_grid AS (
                SELECT pc.page_id, pc.season, CAST(gs.d AS DATE) AS date_parsed,
                       tr.theater, tr.city
                FROM page_cities pc
                JOIN page_dates pd USING (page_id)
                JOIN theater_roster tr
                    ON tr.season = pc.season AND list_contains(pc.expected_cities, tr.city)
                , LATERAL (SELECT unnest(generate_series(pd.min_date, pd.max_date, INTERVAL 1 DAY)) AS d) AS gs
            ),
            covered AS (
                SELECT DISTINCT page_id, date_parsed, theater_canonical AS theater
                FROM base
                WHERE date_parsed IS NOT NULL AND theater_canonical IS NOT NULL
            ),
            gap_rows AS (
                SELECT
                    eg.page_id || '__gap_' || strftime(eg.date_parsed, '%Y%m%d') || '_' || eg.theater
                        AS event_id,
                    eg.page_id, eg.season, eg.city,
                    '' AS date_text, '' AS month_text, '' AS year_text,
                    strftime(eg.date_parsed, '%Y-%m-%d') AS date_undate,
                    'unspecified' AS time_of_day, eg.theater,
                    'not_captured' AS event_status,
                    '' AS receipts_text, NULL::INTEGER AS receipts_rubles,
                    NULL::INTEGER AS receipts_kopecks, '' AS annotation,
                    NULL::INTEGER AS receipts_total_kopecks, eg.date_parsed,
                    eg.theater AS theater_canonical
                FROM expected_grid eg
                LEFT JOIN covered c
                    ON c.page_id = eg.page_id AND c.date_parsed = eg.date_parsed AND c.theater = eg.theater
                WHERE c.page_id IS NULL
            )
            SELECT * EXCLUDE (date_parsed) FROM base
            UNION ALL BY NAME
            SELECT * EXCLUDE (date_parsed) FROM gap_rows
        """)
        n_gaps = con.execute(
            "SELECT count(*) FROM analysis.event_entry WHERE event_status = 'not_captured'"
        ).fetchone()[0]
        print(f"analysis.event_entry built (+ receipts_total_kopecks, theater_canonical, "
              f"{n_gaps} not_captured completeness gaps)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(args.db))

    load_raw_schema(con, args.parsed_dir, args.manifest)
    build_analysis_schema(con)

    con.close()
    print(f"\nBuilt {args.db} -- copy this off scratch/temp storage, it's the deliverable.")


if __name__ == "__main__":
    main()
