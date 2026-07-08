#!/usr/bin/env bash
# hub-pull.sh — run on the Linux/MacBook Air hub (every 30 min via cron).
# Pulls exports from GitHub, ingests into SQLite, runs synthesis, dispatches Telegram.
#
# Setup:
#   chmod +x hub-pull.sh
#   crontab -e → */30 * * * * /full/path/to/hub-pull.sh >> /full/path/to/hub.log 2>&1
#
set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$HOME/Omni-Memory}"
GIT_REPO="https://github.com/benclawbot/Omni-Memory.git"
EXPORT_DIR="$REPO_DIR/exports"
SKILLS_DIR="$REPO_DIR/skills"
LOG="$HUB_DIR/hub.log"
DB_DIR="${DB_DIR:-$HOME/.memory/hub}"
ENV_FILE="$HOME/.memory/.env"

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
  fi
}

log "=== Omni-Memory hub started ==="

# 1. Clone / pull the repo
load_env

if [[ ! -d "$REPO_DIR/.git" ]]; then
  log "[1/5] Cloning $GIT_REPO"
  git clone "$GIT_REPO" "$REPO_DIR" 2>>"$LOG" || {
    log "[git] Clone failed"
    exit 1
  }
else
  log "[1/5] Pulling from GitHub..."
  cd "$REPO_DIR"
  git pull --ff-only 2>>"$LOG" || log "[git] Pull failed — continuing with local data"
fi

# 2. Ingest new events from all exports
log "[2/5] Ingesting events..."
node "$HUB_DIR/ingest/merge-events.mjs" --export-dir "$EXPORT_DIR" 2>>"$LOG" || log "[ingest] failed"

# 3. Run synthesis
log "[3/5] Running synthesis..."
node "$HUB_DIR/synthesis/analyze.mjs" 2>>"$LOG" || log "[synthesis] failed"

# 4. Check for new approved skills and push them
log "[4/5] Syncing skills..."
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  load_env
  # Start Telegram bot in background (it handles its own polling)
  if ! pgrep -f "telegram/bot.mjs" > /dev/null 2>&1; then
    nohup node "$HUB_DIR/telegram/bot.mjs" \
      --skills-dir "$SKILLS_DIR" \
      >> "$HUB_DIR/telegram.log" 2>&1 &
    log "[telegram] Bot started PID=$!"
  else
    log "[telegram] Bot already running"
  fi

  # Push any new approved skills
  cd "$REPO_DIR"
  if [[ -d "$SKILLS_DIR" ]] && git status --porcelain "$SKILLS_DIR" | grep -q '.'; then
    git add "$SKILLS_DIR"
    git commit -m "skills $(date '+%Y-%m-%d %H:%M')" --quiet 2>/dev/null || true
    git push 2>>"$LOG" || log "[git] skills push failed"
    log "[4/5] Skills pushed"
  else
    log "[4/5] No new skills to push"
  fi
else
  log "[4/5] TELEGRAM_BOT_TOKEN not set — skipping Telegram"
fi

log "[5/5] Done — next run in 30 min"
log "=== Hub cycle complete ==="
