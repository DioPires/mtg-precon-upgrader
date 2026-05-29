#!/usr/bin/env bash
# Smoke test: starts a local server, opens each deck in headless Chromium,
# and checks for JS errors or visible error banners.
#
# Requirements: gstack browse binary at ~/.claude/skills/gstack/browse/dist/browse
# Usage: ./scripts/smoke_test.sh

set -uo pipefail

B="${BROWSE_BIN:-$HOME/.claude/skills/gstack/browse/dist/browse}"
PORT=8799
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
TOTAL=0

echo "=== Deck JSON Validation ==="
python3 "$ROOT/scripts/validate_deck_json.py" || exit 1
echo ""

echo "=== Strategy-Ceiling Check (DEC-309) ==="
python3 "$ROOT/scripts/validate_strategy_ceiling.py" || true
echo ""

# Start server
python3 -m http.server "$PORT" --directory "$ROOT" &>/dev/null &
SERVER_PID=$!
cleanup() { local rc=$?; kill $SERVER_PID 2>/dev/null; $B stop 2>/dev/null; exit $rc; }
trap cleanup EXIT
sleep 1

# Extract deck IDs from index.json
DECK_IDS=$(python3 -c "
import json, sys
with open('$ROOT/data/index.json') as f:
    data = json.load(f)
for c in data['commanders']:
    print(c['id'])
")

echo "=== The Grimoire Smoke Test ==="
echo ""

check_errors() {
  local label="$1"
  local ok=true

  # Check for visible #error banner with content
  local err_visible
  err_visible=$($B js "(() => { const el = document.getElementById('error'); return el && el.style.display !== 'none' && el.textContent.trim().length > 0 })()" 2>/dev/null || echo "false")
  if [ "$err_visible" = "true" ]; then
    local err_text
    err_text=$($B js "document.getElementById('error').textContent" 2>/dev/null)
    echo "FAIL (error banner: $err_text)"
    ok=false
  fi

  # Check console for real JS errors (not the "(no console errors)" placeholder)
  local console_out
  console_out=$($B console --errors 2>/dev/null)
  if [ "$console_out" != "(no console errors)" ] && [ -n "$console_out" ]; then
    if $ok; then
      echo "FAIL (console errors)"
    fi
    echo "  $console_out"
    ok=false
  fi

  if $ok; then
    echo "OK"
    return 0
  fi
  return 1
}

# Test 1: Homepage loads
TOTAL=$((TOTAL + 1))
echo -n "Homepage... "
$B goto "http://localhost:$PORT" 2>/dev/null >/dev/null
$B wait --networkidle 2>/dev/null >/dev/null
if ! check_errors "Homepage"; then
  FAILED=$((FAILED + 1))
fi
$B console --clear 2>/dev/null >/dev/null

# Test 2: Each deck loads without errors
for DECK_ID in $DECK_IDS; do
  TOTAL=$((TOTAL + 1))
  echo -n "Deck: $DECK_ID... "

  $B goto "http://localhost:$PORT/#deck=$DECK_ID" 2>/dev/null >/dev/null
  $B wait --networkidle 2>/dev/null >/dev/null
  sleep 2

  if ! check_errors "$DECK_ID"; then
    FAILED=$((FAILED + 1))
  fi
  $B console --clear 2>/dev/null >/dev/null
done

echo ""
echo "=== Results: $((TOTAL - FAILED))/$TOTAL passed ==="

if [ "$FAILED" -gt 0 ]; then
  echo "FAILED: $FAILED test(s)"
  exit 1
else
  echo "All tests passed."
  exit 0
fi
