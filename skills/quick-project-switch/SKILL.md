---
name: quick-project-switch
description: Instant project context switch with `[[goto project-name]]`. Loads project overview, skills, memory, recent work. Use when Thomas wants to switch projects mid-session or load a project's context.
allowed-tools: Read,Bash
---

# Quick Project Switch

`[[goto project-name]]` — instantly loads that project's context.

## How It Works

Thomas types `[[goto liquidity-pulse]]`:

1. Check `~/.pi/agent/task-memory.md` — any active task for this project?
2. Check `~/Dropbox/memory/Obsidian/Projects/{project}/overview.md` — project overview
3. Check `~/.pi/agent/decisions.md` — any decisions for this project?
4. Check `~/Dropbox/memory/Obsidian/Projects/{project}/status.md` — current status
5. Compile into a brief, present it

## Output Format

```
 Switched to: liquidity-pulse

 Status: MVP in progress
 Last session: 2026-04-28 — refactored /api/orders validation
 Next: Add rate limiting

 Active task: #liquidity-pulse-backend (in-progress)
 Decisions: Use Effect for service layer

 Quick:
   [[standup]] — project standup
   [[decisions: liquidity-pulse]] — all decisions
   [[task: liquidity-pulse]] — current task details
```

## Project Lookup

Projects are stored at:
- `~/Dropbox/memory/Obsidian/Projects/{name}/`
- Or any folder Thomas has set up

If project not found:
- Search vault for folder matching the name
- Show closest matches: "Did you mean: liquidity-pulse, llm-knowledge-base?"

## Commands

| Command | Action |
|---------|--------|
| `[[goto]]` | Show all available projects |
| `[[goto: name]]` | Switch to named project |
| `[[goto? query]]` | Search for project by keyword |
| `[[project]]` | Current project context |
| `[[projects]]` | List all projects |

## Auto-Switch

When Thomas switches projects mid-conversation:
- Ask: "Want me to update the task memory with what we finished in [old project]?"
- Save current state to task-memory
- Load new project context
- Thomas continues naturally

## Scripts

- `scripts/goto.py` — resolves project name, loads context