#!/usr/bin/env bash
# collect-and-push.sh — run on each Windows machine via Task Scheduler.
# Collects new AI session events and pushes to the shared GitHub private repo.
#
# Schedule (Task Scheduler):
#   C:\path\to\collect-and-push.bat
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORT_ROOT="$HOME/.memory/exports"
GIT_REPO="${GIT_REPO:-git@github.com:you/memory-exports.git}"
GIT_DIR="$EXPORT_ROOT/.git"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" ; }

# Detect platform
PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
if [[ "$PLATFORM" == *"mingw"* ]] || [[ "$PLATFORM" == *"msys"* ]] || [[ -n "${USERPROFILE:-}" ]]; then
  PLATFORM="windows"
fi

log "=== Collector push (platform=$PLATFORM) ==="

# 1. Run collectors
log "[1/3] Running collectors..."
node "$SCRIPT_DIR/collect-all.mjs" 2>>"$SCRIPT_DIR/collect.log" || log "[collector] exited with code $?"

# 2. Commit and push to GitHub
log "[2/3] Pushing to GitHub..."

# Lazy-init git repo if not present
if [[ ! -d "$GIT_DIR" ]]; then
  log "[git] Initializing export repo: $GIT_REPO"
  git clone --bare "$GIT_REPO" "$GIT_DIR" 2>/dev/null || {
    log "[git] Clone failed — repo may not exist yet. Create it at $GIT_REPO"
    log "[git] Skipping push"
    exit 0
  }
fi

cd "$EXPORT_ROOT"
git config --local user.email "collector@memory-hub"
git config --local user.name "Memory Collector"

# Check if there are new files to commit
if git status --porcelain | grep -q '.'; then
  git add -A
  git commit -m "exports $(date '+%Y-%m-%d %H:%M')" --quiet 2>/dev/null || true
  git push 2>>"$SCRIPT_DIR/collect.log" || log "[git] push failed"
  log "[3/3] Pushed successfully"
else
  log "[2/3] No changes to push"
fi

log "=== Done ==="
