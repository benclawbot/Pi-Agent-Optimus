---
name: task-linker
description: Links tasks across conversations. When a task is mentioned in a new session, links to the previous conversation where it was active. Use when "continue", "we were working on", "link to previous", or when detecting a task reference in a new session.
allowed-tools: Read,Bash
---

# Cross-Conversation Task Linking

When Thomas mentions a task in a new session, the system finds the previous conversation where it was active and links them. Task history is discoverable instead of siloed.

## How It Works

1. **Task Detection** — When Thomas mentions something that sounds like a known task (project name, feature, bug), check `task-memory.md` and conversation history.
2. **Link Discovery** — Find the most recent conversation where this task was active.
3. **Context Linking** — Show: "This was active in the [date] conversation. Continue from where we left off?"
4. **History Building** — As tasks move across conversations, build a chain: `conversation A → conversation B → conversation C`.

## Task Link File

**Location:** `~/.pi/agent/task-links.md`

```markdown
# Task Links

## liquidity-pulse-rate-limiting
Created: 2026-04-28
Conversations:
  - 2026-04-28 (14:30): "Adding rate limiting to /api/orders"
  - 2026-04-28 (16:45): "Continuing with rate limiting — found bug in config"
Project: liquidity-pulse
Status: active

## llm-knowledge-base-schema
Created: 2026-04-25
Conversations:
  - 2026-04-25: Initial schema draft
  - 2026-04-28: "Need to finalize embedding dimensions"
Project: llm-knowledge-base
Status: blocked
Blocked by: embedding dimension decision

## dropsync-pwa
Created: 2026-04-28
Conversations:
  - 2026-04-28: "PWA implementation complete, preparing PR"
Project: dropsync-pwa
Status: pending-review
```

## Detection Patterns

Tasks are detected when Thomas mentions:
- A project name → check if that project has an active task
- "continue", "picking up", "we were" → look for matching tasks in recent conversations
- "earlier", "last time", "yesterday" → search conversation history for task context
- A feature name that appears in `task-memory.md` → link to the original task

## Linking Behavior

When a task is detected in a new conversation:

1. Look up the task in `task-links.md`
2. Find the most recent conversation file for this task
3. Show a one-line summary: "Resuming: [task] from [date] conversation"
4. Offer to load the full previous context
5. Add the new conversation to the task's chain

## Commands

| Command | Action |
|---------|--------|
| `[[links]]` or `[[task-links]]` | Show all task link chains |
| `[[link: task-name]]` | Show conversation chain for a task |
| `[[history: task-name]]` | Full history of a task across conversations |
| `[[unlink: task-name]]` | Archive a task link (keep history) |

## Auto-Linking

When you detect Thomas is continuing work on something:
- Check `task-links.md` for existing link chain
- If found: "I see you're back on [task]. Last worked on it [date]. Continuing from: [last action]"
- Add the new conversation reference to the chain

## Scripts

- `scripts/link-tasks.py` — manages task-links.md, detects task references, builds chains