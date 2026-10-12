#!/bin/bash
# After a person merge or split on outputs/full_run: rebuild entities, research and the review tables, then check alignment.
set -e
cd "$(dirname "$0")/../.."
DB=outputs/full_run/imperial_theaters.duckdb
uv run python pipeline/build_entities.py --db $DB --export-review-queue outputs/full_run/person_candidate_review.csv 2>&1 | grep -E "Tier 1|auto-confirmed|merged into|pending candidates"
uv run python pipeline/build_research_model.py --db $DB 2>&1 | grep -E "research.person:|conflict|point at" || true
uv run python pipeline/match_review_mentions.py --reviews-dir outputs/reviews/merged_full --db $DB --out-dir outputs/reviews/mentions 2>&1 | grep -E "resolved to"
uv run python pipeline/build_reviews_duckdb.py --reviews-dir outputs/reviews/merged_full --mentions-dir outputs/reviews/mentions --db $DB 2>&1 | grep -E "joining research.person"
uv run python pipeline/build_review_assertions.py --reviews-dir outputs/reviews/merged_full --db $DB --out outputs/reviews/mentions/review_assertion.csv 2>&1 | grep -E "performer entity"
uv run python pipeline/check_person_link_alignment.py --db $DB 2>&1 | tail -1
uv run python -c "
import duckdb
c=duckdb.connect('$DB',read_only=True)
print('receipts',c.execute('select sum(receipts_total_kopecks) from research.event').fetchone()[0],'wikidata',c.execute('select count(*) from research.person where wikidata_qid is not null').fetchone()[0],'orphans',c.execute('select count(*) from entities.person_link pl join entities.person p using(person_id) where p.superseded_by_person_id is not null').fetchone()[0],'pending',c.execute(\"select count(*) from entities.person_candidate where status='pending'\").fetchone()[0])"
