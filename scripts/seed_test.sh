#!/bin/bash
# Run a test prompt through the pipeline
set -e

PROMPT="${1:-Write a deep dive on how transformer attention mechanisms actually work, aimed at CS undergraduates}"
AUDIENCE="${2:-CS undergraduates}"

echo "Testing pipeline with prompt:"
echo "  \"$PROMPT\""
echo "  Audience: $AUDIENCE"
echo ""

curl -s -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"$PROMPT\", \"audience\": \"$AUDIENCE\", \"tone\": \"informative\"}" | python -m json.tool

echo ""
echo "Done!"
