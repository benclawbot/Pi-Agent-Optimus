#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.pi/agent"

node "$SCRIPT_DIR/scripts/install-harness.mjs" "$TARGET_DIR"
node "$TARGET_DIR/scripts/install-packages.mjs" "$TARGET_DIR/settings.json"
npm --prefix "$TARGET_DIR" test

echo "Setup complete. Restart Pi to load the current harness."
