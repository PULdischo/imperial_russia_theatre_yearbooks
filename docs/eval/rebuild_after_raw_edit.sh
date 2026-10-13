#!/bin/bash
# Rebuild raw/analysis/entities/research from the raw JSON on disk after a raw edit (used by the TheaterSchoolStaff, Graduates and Administrators audits).
# parse_and_validate needs BOTH --page-headers and --printed-page-numbers (CLAUDE.md: omitting them silently blanks dates / page numbers).
# Run from anywhere; take a backup of outputs/full_run/imperial_theaters.duckdb (+ the raw pages you edit) first.
#
# Every step's full output goes to a log; a step that exits non-zero prints the end of its log and STOPS the script with exit 1.
# (Until 2026-10-13 each step was piped through grep with `set -e` and no pipefail: a Python traceback was filtered out, the script
# stopped without a word, and a second run then rebuilt the works with no id continuity. known_issues.md, 2026-10-13.)
set -euo pipefail
cd "$(dirname "$0")/../.."
F=outputs/full_run
LOGDIR=$(mktemp -d)
step() {  # step <name> <summary-pattern> <command...>
    local name=$1 pat=$2; shift 2
    local log="$LOGDIR/$name.log"
    if ! "$@" > "$log" 2>&1; then
        echo "STEP FAILED: $name   (full log: $log)"; tail -30 "$log"; exit 1
    fi
    grep -E "$pat" "$log" | head -3 || echo "$name: done"
}
step parse_and_validate "person_entry:" uv run python pipeline/parse_and_validate.py --manifest $F/manifest.csv --raw-dir $F/raw --out-dir $F/parsed --page-headers outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv --printed-page-numbers $F/printed_page_numbers_all.csv
step quality_checks "flags ->" uv run python pipeline/quality_checks.py --parsed-dir $F/parsed --out $F/quality_flags.csv
step build_duckdb "raw.person_entry:" uv run python pipeline/build_duckdb.py --parsed-dir $F/parsed --manifest $F/manifest.csv --db $F/imperial_theaters.duckdb
step build_entities "entities.person \(Tier 1\)|entities.work:" uv run python pipeline/build_entities.py --db $F/imperial_theaters.duckdb
step validate_performance_dates "verified" uv run python pipeline/validate_performance_dates.py --db $F/imperial_theaters.duckdb
step build_research_model "research.(person|event|work|performance):" uv run python pipeline/build_research_model.py --db $F/imperial_theaters.duckdb
echo "rebuild complete; logs in $LOGDIR. Now diff against the backup (work ids included) and rebuild the sqlite export."
