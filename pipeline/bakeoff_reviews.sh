#!/usr/bin/env bash
# Season Reviews model bake-off: qwen3-vl-plus vs three Claude models, on the
# 11 gold pages (the rotated full-page plate is excluded from the scoring).
#
# Needs an Anthropic key:   export ANTHROPIC_API_KEY=sk-ant-...
# Cost, measured from the pilot's token counts: ~$2.80 total.
#
#   claude-opus-5    $0.47    claude-sonnet-5  $0.19    claude-fable-5-1  ~$2.10
#
# Fable is the expensive one because its thinking cannot be disabled and
# thinking tokens bill as output at $50/1M -- on a transcription task that is
# spend on deliberation, which is the suspected failure mode, not the fix.
#
# NB: temperature is NOT passed. Current Claude models removed the sampling
# parameters and return a 400 if it is present; run_reviews.py drops it for
# --provider anthropic automatically.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
  echo "No Anthropic credentials found. export ANTHROPIC_API_KEY=... first." >&2
  exit 1
fi

GOLD=$(ls docs/eval/gold_reviews/*.txt | sed 's|.*/[0-9]*_||; s|\.txt$||' | tr '\n' ' ')
echo "gold pages: $GOLD"

for M in claude-opus-5 claude-sonnet-5 claude-fable-5-1; do
  OUT="outputs/reviews/bakeoff_${M}"
  echo "=== $M -> $OUT ==="
  uv run python pipeline/run_reviews.py \
      --manifest outputs/reviews/manifest.csv \
      --images-dir outputs/reviews/images \
      --out-dir "$OUT" \
      --provider anthropic --model "$M" \
      --prompt review_system_lines.txt \
      --max-concurrent 4 \
      --only $GOLD
done

echo
echo "All three done. Score them with:"
echo "  uv run python pipeline/score_bakeoff.py"
