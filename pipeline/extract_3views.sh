set -e
cd "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main"
echo "=== view 1: full page, remaining 824 (existing 200 are skipped) ==="
uv run python pipeline/run_reviews.py --manifest outputs/reviews/manifest.csv \
  --images-dir outputs/reviews/images --out-dir outputs/reviews/pilot_1 \
  --prompt review_system_lines.txt --temperature 0 --max-concurrent 8
echo "=== view 2: 2-band, all 1024 pages (2048 calls) ==="
uv run python pipeline/run_reviews.py --manifest outputs/reviews/bands2/manifest.csv \
  --images-dir outputs/reviews/bands2/images --out-dir outputs/reviews/bands2/raw \
  --prompt review_system_lines.txt --temperature 0 --max-concurrent 8
echo "=== view 3: 4-band, all 1024 pages (4096 calls) ==="
uv run python pipeline/run_reviews.py --manifest outputs/reviews/bands4/manifest.csv \
  --images-dir outputs/reviews/bands4/images --out-dir outputs/reviews/bands4/raw \
  --prompt review_system_lines.txt --temperature 0 --max-concurrent 8
echo "=== ALL EXTRACTION DONE ==="
