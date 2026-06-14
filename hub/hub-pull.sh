#!/usr/bin/env bash
# hub-pull.sh — run on the Linux/MacBook Air hub (MacBook Air runs this)
#
# Schedule: cron (every 30 min)
#   crontab -e
#   */30 * * * * ~/memory-hub/hub-pull.sh >> ~/memory-hub/hub.log 2>&1
#
set -euo pipefail

HUB_DIR="$HOME/memory-hub"
EXPORT_DIR="$HOME/.memory/exports"
GIT_REPO="${GIT_REPO:-git@github.com:you/memory-exports.git}"
LOG="$HUB_DIR/hub.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== Hub pull started ==="

# 1. Pull exports from GitHub
log "[1/4] Pulling exports from GitHub..."
cd "$EXPORT_DIR"
if [[ -d ".git" ]]; then
  git pull --ff-only 2>>"$LOG" || log "[git] Pull failed — continuing with local data"
else
  log "[git] Cloning export repo..."
  git clone "$GIT_REPO" "$EXPORT_DIR" 2>>"$LOG" || {
    log "[git] Clone failed — export repo may not exist yet"
  }
fi

# 2. Ingest new events
log "[2/4] Ingesting events..."
node "$HUB_DIR/ingest/merge-events.mjs" 2>>"$LOG" || log "[ingest] failed"

# 3. Run synthesis
log "[3/4] Running synthesis..."
node "$HUB_DIR/synthesis/analyze.mjs" 2>>"$LOG" || log "[synthesis] failed"

# 4. Send Telegram proposals
log "[4/4] Telegram dispatch..."
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  # Check if bot is already running
  if ! pgrep -f "telegram/bot.mjs" > /dev/null 2>&1; then
    nohup node "$HUB_DIR/telegram/bot.mjs" >> "$HUB_DIR/telegram.log" 2>&1 &
    log "[telegram] Bot started PID=$!"
  else
    log "[telegram] Bot already running"
  fi
else
  log "[telegram] TELEGRAM_BOT_TOKEN not set — skipping"
fi

log "=== Hub pull done ==="
