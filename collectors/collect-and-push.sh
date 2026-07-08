#!/usr/bin/env bash
# collect-and-push.sh — run on each machine via Task Scheduler.
# Collects new AI session events and pushes to Omni-Memory GitHub repo.
#
# Usage: bash collect-and-push.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORT_DIR="${EXPORT_DIR:-$HOME/Omni-Memory/exports}"
GIT_REPO="https://github.com/benclawbot/Omni-Memory.git"
GIT_DIR="$EXPORT_DIR/.git"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" ; }

log "=== Omni-Memory collector (platform=$(uname -s)) ==="

# 1. Run collectors
log "[1/3] Running collectors..."
node "$SCRIPT_DIR/collect-all.mjs" 2>&1 | tee -a "$SCRIPT_DIR/collect.log" || log "[collector] exited with code $?"

# 2. Set up git repo in exports dir (lazy init)
if [[ ! -d "$GIT_DIR" ]]; then
  log "[git] Cloning $GIT_REPO into $EXPORT_DIR"
  mkdir -p "$EXPORT_DIR"
  git clone --depth=1 "$GIT_REPO" "$EXPORT_DIR" 2>/dev/null || {
    log "[git] Clone failed — check your SSH key and repo permissions"
    exit 1
  }
fi

cd "$EXPORT_DIR"
git config --local user.email "collector@omni-memory" 2>/dev/null || true
git config --local user.name "Omni-Memory Collector" 2>/dev/null || true

# 3. Commit and push
if git status --porcelain | grep -q '.'; then
  git add -A
  git commit -m "exports $(date '+%Y-%m-%d %H:%M')" --quiet 2>/dev/null || true
  git pull --ff-only 2>/dev/null || log "[git] pull failed, continuing"
  git push 2>&1 | tee -a "$SCRIPT_DIR/collect.log" || {
    log "[git] push failed — check network and SSH key"
    exit 1
  }
  log "[3/3] Pushed successfully"
else
  log "[2/3] No changes to push"
fi

log "=== Done ==="
