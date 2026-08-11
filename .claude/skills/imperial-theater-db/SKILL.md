---
name: imperial-theater-db
description: Use whenever answering a question about the Imperial Theater Yearbooks data — who worked where, what was performed, box-office figures, counts, dates, or any other fact derivable from outputs/full_run/imperial_theaters.duckdb. Applies to any factual claim about the dataset's contents, not just explicit "query the database" requests.
---

# Querying the Imperial Theater Yearbooks database

This is a research dataset. A claim about the data that isn't traceable to
an actual query is not usable — it can't be checked, cited, or trusted by
someone else working from the same database. Treat every factual statement
about record counts, specific people/works/performances, dates, or figures
the same way a paper treats a statistic: it needs a citation, and the
citation is the query.

## The rule

**Never answer a question about the data's contents from memory, from a
prior turn's cached numbers, or by pattern-matching against what the schema
"should" contain — always run a fresh SQL query and answer from its actual
output.** This applies even if you're confident, even if you answered a
similar question minutes ago, even if the number seems obvious from the
row counts in `CLAUDE.md`. Those row counts are a snapshot from one point
in time; the live file is the source of truth. If a question can't be
answered with a query (it's about pipeline *design* rather than data
*contents*), this rule doesn't apply — answer from the docs/code as normal.

## The database

`outputs/full_run/imperial_theaters.duckdb` (read-only unless you're
explicitly running a pipeline stage — see `CLAUDE.md`'s architecture
section for the full `raw`/`analysis`/`entities`/`research` layering).
For a research question, query `research.*` first — it's the resolved,
deduplicated layer with real foreign keys (`theater`, `work`, `person`,
`event`, `performance`, `person_appearance`). Drop to `raw.*` only when the
question is specifically about the verbatim printed source rather than the
resolved entity.

Query however is natural — `duckdb outputs/full_run/imperial_theaters.duckdb -c "..."`
from the shell, or `python -c "import duckdb; ..."` — the logging
requirement below is the same either way.

## Logging every query

Every query run to answer a data question gets appended to
`docs/query_log.md` (create it if it doesn't exist yet), in this format:

```
## <YYYY-MM-DD> — <one-line description of the question asked>

```sql
<the exact SQL run>
```

Result: <brief summary of what came back — the key number(s) or row(s),
not a full dump of a large result set>
```

Log the query even if the result is "0 rows" or "no match" — a negative
result is still a finding. Log it even for a quick sanity-check query, not
just the final one that produced the answer given to the user — the point
is a complete, honest trail of what was actually asked of the database,
not a curated highlight reel. Append-only: never edit or delete a past
entry, even if a later query supersedes it (write a new entry instead,
noting what changed).
