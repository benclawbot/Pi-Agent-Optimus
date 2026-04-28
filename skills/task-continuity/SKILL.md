---
name: task-continuity
description: Tracks tasks across sessions. Detects when a task spans multiple conversations, links them, carries state forward. Shows ongoing work at session start. Use when "continue", "what was I doing", "task status", "pick up", or session start.
allowed-tools: Read,Bash
---

# Task Continuity

Tasks persist across sessions. Thomas never has to say "we were working on X" — the agent already knows.

## Task Memory File

**Location:** `~/.pi/agent/task-memory.md`

```markdown
# Active Tasks

## task-id: liquidity-pulse-backend
Started: 2026-04-27
Project: liquidity-pulse
Status: in-progress
Last session: 2026-04-28
Last work: "Refactoring /api/orders endpoint, moved validation to service layer"
Session history:
  - 2026-04-27: Set up FastAPI project, defined /api/orders schema
  - 2026-04-28: Refactored validation, next is adding rate limiting
Pending:
  - Add rate limiting to /api/orders
  - Write tests for new service layer
Blocked: none

## task-id: llm-knowledge-base-schema
Started: 2026-04-25
Project: llm-knowledge-base
Status: blocked
Last session: 2026-04-28
Last work: "Defining vector schema, blocked on embedding dimension decision"
Session history:
  - 2026-04-25: Initial schema draft
  - 2026-04-28: Revised schema based on feedback, need embedding decision
Pending:
  - Decide embedding dimensions (1536 vs 768)
  - Update schema
Blocked: embedding dimension decision from architecture review

## task-id: dropsync-pwa-review
Started: 2026-04-28
Project: dropsync-pwa
Status: pending-review
Last session: 2026-04-28
Last work: "Completed PWA implementation, preparing PR"
Session history:
  - 2026-04-28: Completed implementation, wrote README
Pending:
  - Submit PR
  - Address review feedback
Blocked: none
```

## At Session Start

1. Read `task-memory.md`
2. List active tasks with one-line summaries
3. Show: "Continuing: liquidity-pulse (rate limiting next), dropsync-pwa (PR pending)"
4. If Thomas mentions a project that has an active task → offer to continue from where it left off
5. Ask: "Pick up where we left off on [task]?"

## At Session End

When the conversation is wrapping up (or Thomas switches projects):

1. Ask: "Want me to save this session as a task?"
2. If yes → parse the conversation for what was done and what's next
3. Write to `task-memory.md`:
   - Update session history
   - Update "last work" summary
   - Update pending items
   - Update status (in-progress → done → pending-review → done)

## Task Detection

During conversation, detect task-related signals:
- "next" / "then" / "after this" → mark as next pending
- "done" / "finished" / "completed" → mark step as complete
- "blocked" / "waiting on" → mark as blocked, record reason
- Project name mention → check if there's an active task

## Cross-Session Linking

When Thomas starts a new session and mentions a project:
1. Check `task-memory.md` for that project
2. If found → show last session summary + pending items
3. Offer: "Continue with [task]?"
4. If different project → show task switch confirmation

## Commands

| Command | Action |
|---------|--------|
| `[[tasks]]` | Show all active tasks with status |
| `[[task]]` or `[[current]]` | Show current/most recent task |
| `[[task: name]]` | Switch to specific task by project name |
| `[[done: task-id]]` | Mark task as done, archive it |
| `[[save]]` | Save current session to task memory |
| `[[block: reason]]` | Mark current task as blocked |
| `[[next: description]]` | Set next step for current task |
| `[[clear tasks]]` | Archive all done tasks, show only active |

## Script

- `scripts/task-memory.py` — reads/writes task-memory.md, detects context