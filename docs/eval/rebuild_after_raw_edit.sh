#!/bin/bash
# Rebuild raw/analysis/entities/research from the raw JSON on disk after a raw edit (used by the TheaterSchoolStaff, Graduates and Administrators audits).
# parse_and_validate needs BOTH --page-headers and --printed-page-numbers (CLAUDE.md: omitting them silently blanks dates / page numbers).
# Run from anywhere; take a backup of outputs/full_run/imperial_theaters.duckdb (+ the raw pages you edit) first.
set -e
cd "$(dirname "$0")/../.."
uv run python pipeline/parse_and_validate.py --manifest outputs/full_run/manifest.csv --raw-dir outputs/full_run/raw --out-dir outputs/full_run/parsed --page-headers outputs/repertoire_singlepage_pagenumbers/all_page_headers.csv --printed-page-numbers outputs/full_run/printed_page_numbers_all.csv 2>&1 | grep -E "person_entry:"
uv run python pipeline/quality_checks.py --parsed-dir outputs/full_run/parsed --out outputs/full_run/quality_flags.csv 2>&1 | head -1
uv run python pipeline/build_duckdb.py --parsed-dir outputs/full_run/parsed --manifest outputs/full_run/manifest.csv --db outputs/full_run/imperial_theaters.duckdb 2>&1 | grep -E "raw.person_entry:"
uv run python pipeline/build_entities.py --db outputs/full_run/imperial_theaters.duckdb 2>&1 | grep -E "entities.person \(Tier 1\)"
uv run python pipeline/validate_performance_dates.py --db outputs/full_run/imperial_theaters.duckdb 2>&1 | grep verified
uv run python pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb 2>&1 | grep -E "research.(person|event):"
