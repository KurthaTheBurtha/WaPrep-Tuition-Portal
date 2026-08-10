#!/usr/bin/env bash
# Regenerate docs/database-schema.pdf from docs/database-schema.html
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HTML="file://${ROOT}/docs/database-schema.html"
OUT="${ROOT}/docs/database-schema.pdf"
google-chrome --headless --disable-gpu --no-pdf-header-footer \
  --user-data-dir=/tmp/chrome-pdf-profile \
  --print-to-pdf="$OUT" "$HTML"
echo "Wrote $OUT"
