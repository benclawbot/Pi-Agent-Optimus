---
name: proactive-context
description: Loads Thomas's vault context at session start — Active Context, recent conversations, decisions, active projects. Provides zero-effort orientation without Thomas having to re-explain anything. Triggers automatically at startup and via "[[context]]" or "[[mem]]" mid-session.
allowed-tools: Read
---

# Proactive Context Loader

Loads Thomas's Obsidian vault context automatically at session start. Thomas opens a conversation and the agent is already oriented — no re-explanation needed.

## What Gets Loaded

### 1. Active Context
**File:** `~/Dropbox/memory/Obsidian/Active Context/active-context.md`
Quick access: always loaded at startup.

### 2. Recent Conversations (last 3)
**Files:** `~/Dropbox/memory/Obsidian/Conversations/YYYY/MM/YYYY-MM-DD.md`
Loaded automatically at startup. Thomas doesn't have to say "we were working on X."

### 3. Recent Decisions
**Search:** Recent conversation files for lines containing "decision:", "decided:", "agreed:", or "conclusion:".
Stores decisions separately for quick reference.

### 4. Active Projects Briefings
**Files:** `~/Dropbox/memory/Obsidian/Projects/*/overview.md` (projects marked active in Active Context)
One-line summaries of what's live.

### 5. Today's Conversation
**File:** `~/Dropbox/memory/Obsidian/Conversations/YYYY/MM/YYYY-MM-DD.md`
If it exists, load it to continue where Thomas left off.

## Startup Behavior

At session start, in order:

```
1. Read ~/Dropbox/memory/Obsidian/Active Context/active-context.md
2. Summarize: "Active projects: X, Y, Z. Recent decisions: A, B. Current pressure: ..."
3. Read last 3 conversation files (newest first)
4. If any contain decisions → list them briefly
5. If today's conversation exists → say "Continuing from earlier: ..."
6. Present: "Ready. Active: [summary]. Want to pick up where we left off?"
```

## No Token Waste

- Read full files only when relevant to what Thomas says
- At startup: extract 5-10 line summaries from each
- Full files loaded on demand, not preemptively
- Thomas can type `[[context]]` or `[[mem]]` at any time to refresh context

## Context Memory File

All loaded context gets appended to `~/.pi/agent/context-today.md` for this session. This file is the working memory for the current session — don't reload from vault unless Thomas types `[[context]]`.

## Format at Startup

```markdown
SESSION CONTEXT — 2026-04-28

ACTIVE PROJECTS:
- liquidity-pulse: [1 line]
- dropsync-pwa: [1 line]
- llm-knowledge-base: [1 line]

RECENT DECISIONS:
- [decision 1]
- [decision 2]

CURRENT PRESSURE: [from Active Context]

LAST SESSION: [1 line summary of previous conversation]

READY: [question or confirmation]
```

## When Thomas Types `[[context]]` or `[[mem]]`

1. Reload Active Context (full)
2. Read today's conversation if exists
3. List decisions made so far this session
4. Say what's active, what's pending
5. Ask what Thomas wants to continue with

## Commands

| Trigger | Action |
|---------|---------|
| Session start | Auto-load context, summarize, confirm |
| `[[context]]` | Reload and summarize active context |
| `[[mem]]` | Same as `[[context]]` |
| `[[decisions]]` | List decisions from recent conversations |
| `[[projects]]` | Brief status of active projects |
| `[[active]]` | Just Active Context, full |
| `[[continue]]` | Continue from last session summary |

## Memory File Location

Working session memory: `~/.pi/agent/context-today.md`
Persisted decisions: `~/.pi/agent/decisions-log.md`
