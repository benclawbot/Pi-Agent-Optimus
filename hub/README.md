# Memory Hub — Cross-Device Behavioral Knowledge Graph

Aggregates AI agent sessions from all machines, detects workflow patterns,
and proposes automations via Telegram.

---

## Architecture

```
[Windows PC 1]  → collectors/collect-and-push.sh  →  GitHub private repo
[Windows PC 2]  → collectors/collect-and-push.sh  →  (same repo)
[MacBook Air]  →  hub/hub-pull.sh  →  SQLite (local)
                           ↓
                    Synthesis engine
                    Pattern detection
                           ↓
                    Telegram approval bot
                           ↓
                    Shared skills repo (git)
                           ↓
              [all agents] → agent-pull.sh on restart
```

---

## Quick Start

### 1. Create GitHub private repos

Create two private repos on GitHub:

- **`memory-exports`** — holds encrypted JSONL event exports
- **`memory-skills`** — holds approved skill definitions

### 2. Set up each Windows machine

```bash
# Clone this repo
git clone git@github.com:you/memory-hub.git ~/memory-hub

# Install Node.js deps for collectors
cd ~/memory-hub/collectors
npm install

# Test collectors (dry run)
node collect-all.mjs --dry-run

# Real run
node collect-all.mjs
```

**Schedule with Task Scheduler:**
```
Action: Start a program
Program: bash
Arguments: -c "cd %USERPROFILE%\memory-hub\collectors && bash collect-and-push.sh"
Trigger: Daily at 9am and 6pm
```

**First push:**
```bash
cd ~/.memory/exports
git init
git remote add origin git@github.com:you/memory-exports.git
git push -u origin main
```

### 3. Set up MacBook Air (Linux hub)

```bash
# Clone hub
git clone git@github.com:you/memory-hub.git ~/memory-hub
cd ~/memory-hub/hub

# Install deps
npm install better-sqlite3 node-telegram-bot-api dotenv

# Clone the exports repo
git clone git@github.com:you/memory-exports.git ~/.memory/exports
git clone git@github.com:you/memory-skills.git ~/memory-hub/skills-registry/memory-skills

# Create ~/.memory/.env
cat > ~/.memory/.env << 'EOF'
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_USER_ID=your_chat_id
EOF

# Run full pipeline manually
~/memory-hub/hub-pull.sh

# Schedule as cron job (every 30 min)
# crontab -e
# */30 * * * * ~/memory-hub/hub-pull.sh >> ~/memory-hub/hub.log 2>&1
```

### 4. Set up Telegram bot

1. Message `@BotFather` on Telegram: `/newbot`
2. Copy the token to `~/.memory/.env` as `TELEGRAM_BOT_TOKEN`
3. Get your chat ID: `@userinfobot`
4. Add `TELEGRAM_USER_ID=your_id` to `~/.memory/.env`

Test manually:
```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_USER_ID=... node ~/memory-hub/hub/telegram/bot.mjs
```

---

## Collectors

Each collector reads session data from its source and exports to JSONL.

| Source | Storage | Events per session | Sessions on this machine |
|--------|---------|--------------------|-------------------------|
| Pi | `~/.pi/agent/sessions/{project}/*.jsonl` | 20–60 | 164 |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | 5–20 | 138 |
| Claude CLI | `~/.claude/context-mode/sessions/*.db` (SQLite) | 40–200 | 189 sessions/38 DBs |
| Hermes | `~/.hermes/sessions/*.jsonl` + `desktop/sessions.json` | 10–212 | 5 |

**Note:** Codex stores session metadata in `~/.codex/state_5.sqlite` (163 threads).
Claude CLI stores rich behavioral events (user_prompt, file_read, git, etc.) in SQLite.
Hermes sessions are mostly on macOS; the Windows machine has a subset.

To add a new collector:
1. Create `collectors/ai/{name}.mjs` extending `BaseCollector`
2. Add to `collectors/collect-all.mjs` registry
3. Implement `probe()` and `extractEvents()`

---

## Event Schema

Unified schema for all sources:

```
id            TEXT PRIMARY KEY
timestamp     INTEGER (ms since epoch)
content_type  TEXT (transcript|structured|...)
content       TEXT (raw content)
source        TEXT (pi|hermes|claude-cli|...)
source_type   TEXT (ai_session|...)
device_id     TEXT (platform-hostname)
session_id    TEXT (source's session ID)
event_hash    TEXT (sha256 of source+session+timestamp+content)
metadata      TEXT (json, source-specific data)
imported_at   INTEGER
```

Rule: **Fixed columns never change.** New source-specific data goes in `metadata`.

---

## Synthesis Engine

Detects patterns without relying on tool_call blocks (which most sessions don't have).
Uses **content n-gram analysis** across sessions to find recurring topics and workflows.

Current patterns detected:
- Frequent phrase sequences across sessions
- Session openers/closers
- Role transition patterns (user → assistant → ...)

Matched to workflow templates:
- Explanation Request
- Bug Investigation
- Code Creation
- Code Improvement
- Test Writing
- Code Search
- Debugging Session

---

## Telegram Approval Flow

1. Hub runs synthesis → generates workflow proposals
2. Telegram bot sends proposal with [Approve] [Modify] [Dismiss] buttons
3. User taps Approve → skill saved to `memory-skills` repo
4. All agents pull skills on next restart via `agent-pull.sh`

---

## Files

```
collectors/
  base/
    platform.mjs     — OS detection, path resolution
    schema.mjs       — UnifiedEvent schema, SQL
    collector.mjs    — BaseCollector class
  ai/
    pi.mjs           — Pi session collector
    hermes.mjs       — Hermes session collector
    claude-cli.mjs   — Claude CLI collector
    codex.mjs        — OpenAI Codex collector
  collect-all.mjs    — Runner for all collectors
  collect-and-push.sh — Git push for Windows Task Scheduler

hub/
  ingest/
    merge-events.mjs — JSONL → SQLite
  synthesis/
    analyze.mjs      — Pattern detection + proposal generation
  telegram/
    bot.mjs          — Approval bot
  skills-registry/
    agent-pull.sh    — Agent startup skill pull
  run-hub.sh        — Full hub pipeline
  hub-pull.sh       — Git pull + ingest + synthesize + telegram
```

---

## Privacy

- Raw session data: encrypted at rest (GitHub private repo)
- Only derived patterns (workflow templates, phrase frequencies) shared
- `event_hash` dedup means identical events are never stored twice
- metadata JSON never contains raw conversation content — only structured fields
