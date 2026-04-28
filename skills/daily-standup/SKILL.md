---
name: daily-standup
description: Generates a daily standup from recent conversations — done, in-progress, blocked, decisions. Use when "standup", "daily", "status", "what's done", "what's next", or at session start.
allowed-tools: Read,Bash
---

# Daily Standup Generator

Summarizes recent work into a standup format. Thomas opens a new day and sees what matters.

## What It Generates

```markdown
## Standup — 2026-04-28

### Done
- Liquidity Pulse: Refactored /api/orders validation to service layer
- Dropsync PWA: Completed PWA implementation, wrote README

### In Progress
- Liquidity Pulse: Adding rate limiting to /api/orders
- LLM Knowledge Base: Vector schema definition (blocked on embedding dims)

### Blocked
- LLM Knowledge Base: Awaiting embedding dimension decision from architecture review

### Decisions
- Use Effect for service layer (2026-04-28)
- Use pgvector over Pinecone (2026-04-27)

### Pressure
- Ship liquidity-pulse MVP by end of week
```

## How It Works

1. Read `~/.pi/agent/task-memory.md` → active tasks + status
2. Read `~/.pi/agent/decisions.md` → recent decisions
3. Read `~/Dropbox/memory/Obsidian/Conversations/YYYY/MM/YYYY-MM-DD.md` → today's conversation
4. Read recent conversations (last 3) → extract what's done
5. Compile into standup format

## Commands

| Command | Output |
|---------|--------|
| `[[standup]]` | Full standup for today |
| `[[standup: yesterday]]` | Yesterday's standup |
| `[[standup: project-name]]` | Standup filtered to project |
| `[[done]]` | Just the "Done" section |
| `[[next]]` | Just the "In Progress" section |
| `[[blocked]]` | Just the blocked items |

## Startup Behavior

At session start, after showing improvement tracker:
- "Standup ready: [1 line]. Type [[standup]] for full view."

## Scripts

- `scripts/standup.py` — generates standup from task-memory + decisions + conversations