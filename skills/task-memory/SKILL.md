---
name: task-memory
description: Tracks the current task across sessions — what you're working on, which files are relevant, what was just done. Shows current task at startup and keeps it updated as you work. Use when "what am I working on", "current task", "files for this task", or session start.
allowed-tools: Read,Bash
---

# Task Memory Layer

Keeps track of the active task — what's being worked on right now, which files matter, what's next. Shows at startup and stays current throughout the session.

## Current Task File

**Location:** `~/.pi/agent/current-task.md`

```markdown
# Current Task

## Active
Project: liquidity-pulse
Task: Adding rate limiting to /api/orders
Started: 2026-04-28
Context: Refactored validation to service layer earlier today
Relevant files:
  - /home/thomas/Dropbox/Projects/liquidity-pulse/backend/main.py
  - /home/thomas/Dropbox/Projects/liquidity-pulse/backend/services/orders.py
  - /home/thomas/Dropbox/Projects/liquidity-pulse/backend/tests/test_orders.py
Last action: Added rate limit decorator to create_order endpoint
Next: Write tests for rate limiting, then test with load

## Session Log
- [14:30] Refactored /api/orders validation to service layer
- [14:45] Added rate limit decorator to create_order endpoint
- [14:50] Found bug in rate limit config — needs fix
```

## At Startup

1. Read `current-task.md`
2. Show: "Working on: [task] in [project]. Next: [next action]. Files: [count] relevant."
3. Ask: "Continue with [task]?"

## During Session

When you switch tasks or make progress:

**`[[task: description]]`** — Set a new current task
**`[[files: path1, path2]]`** — Add relevant files to the task
**`[[done: description]]`** — Log a completed action, update "Next"
**`[[next: description]]`** — Set what comes next
**`[[switch: project]]`** — Switch to a different project's task

## Commands

| Command | Action |
|---------|--------|
| `[[task]]` or `[[current]]` | Show current task + relevant files |
| `[[task: description]]` | Set/update current task |
| `[[files]]` | List relevant files for current task |
| `[[files: path]]` | Add a file to current task |
| `[[done: action]]` | Log completed action, update next |
| `[[next: action]]` | Set what's next |
| `[[switch: project]]` | Switch to a different task |
| `[[clear task]]` | Archive current task |
| `[[link: file]]` | Add file link to current task |

## Auto-Updates

When you use tools to read/write files related to the current project, the system should:
- Detect which project the file belongs to
- Offer to add it to `Relevant files` if not already listed
- Suggest adding it when you access a file that hasn't been linked

## Format

```
CURRENT TASK: [task name]
Project: [project]
Started: [date]

RELEVANT FILES (3):
  • main.py — API entry point
  • orders.py — service layer
  • test_orders.py — tests

NEXT: [what comes next]
LAST: [what was just done]

Session log:
  • [14:30] Did X
  • [14:45] Did Y
```

## Scripts

- `scripts/task-memory.py` — read/write current-task.md, manage file links