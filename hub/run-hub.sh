#!/usr/bin/env bash
# run-hub.sh — run the full memory hub pipeline on the Linux/MacBook Air hub.
#
# Schedule: via launchd (macOS) or cron
#   crontab -e
#   */30 * * * * ~/memory-hub/run-hub.sh >> ~/memory-hub/hub.log 2>&1
#
# Or run manually: ./run-hub.sh
#
set -euo pipefail

HUB_DIR="$HOME/memory-hub"
LOG="$HUB_DIR/hub.log"
mkdir -p "$HUB_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

log "=== Hub pipeline started ==="

# 1. Pull latest exports from GitHub
log "[1/4] Pulling exports from GitHub..."
cd "$HUB_DIR"
if [[ -d ".git" ]]; then
  git pull --ff-only 2>>"$LOG" || log "[git] Pull failed — continuing with local data"
else
  log "[git] Not a git repo — skipping pull"
fi

# 2. Ingest new events into SQLite
log "[2/4] Ingesting events..."
node "$HUB_DIR/ingest/merge-events.mjs" 2>>"$LOG" || log "[ingest] merge-events failed"

# 3. Run synthesis (pattern detection)
log "[3/4] Running synthesis..."
node "$HUB_DIR/synthesis/analyze.mjs" 2>>"$LOG" || log "[synthesis] analyze failed"

# 4. Send Telegram proposals
log "[4/4] Checking Telegram proposals..."
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  node "$HUB_DIR/telegram/bot.mjs" 2>>"$LOG" &
  log "[telegram] Bot started (PID=$!)"
else
  log "[telegram] TELEGRAM_BOT_TOKEN not set — skipping"
fi

log "=== Hub pipeline done ==="
