---
name: skill-memory-sharing
description: Skills learn from past experiences — auto-recover recalls past fixes, project-health learns from past health checks. Skills share memory so they don't repeat mistakes. Use when skill should remember from previous sessions.
allowed-tools: Read,Bash
---

# Skill Memory Sharing

Skills remember their past and learn from it. auto-recover learns from past fixes. project-health learns from past checks. Skill-evolution learns from skill improvements.

## Memory Files

| Skill | Memory File | What it learns |
|-------|-------------|----------------|
| **auto-recover** | `~/.pi/agent/skill-memory/auto-recover.json` | Past error patterns + fixes that worked |
| **project-health** | `~/.pi/agent/skill-memory/project-health.json` | Past health check results + patterns |
| **skill-evolution** | `~/.pi/agent/skill-memory/skill-evolution.json` | Past skill improvements + what worked |
| **context-memory** | `~/.pi/agent/skill-memory/context-memory.json` | Project conventions learned |

## How It Works

When a skill performs an action, it logs to its memory file:
- What it did
- What the result was
- What context it operated in

When the skill runs again, it reads its memory file first and applies learned patterns.

## Example: auto-recover Memory

```json
{
  "error_patterns": [
    {
      "pattern": "connection refused",
      "fix_applied": "restart service, check port",
      "success_count": 3,
      "last_success": "2026-04-28"
    }
  ]
}
```

When "connection refused" error is detected:
1. Check memory for past fixes
2. Suggest most successful fix first
3. Log new attempt
4. Update success rate

## Memory Sharing Across Skills

When one skill learns something relevant to another:
- auto-recover discovers a dependency issue → tells project-health
- project-health sees outdated deps → tells auto-recover
- skill-evolution evolves a skill → tells skill-chain to update routing

## Commands

| Command | Action |
|---------|--------|
| `[[skill-memory]]` | Show what skills have learned |
| `[[clear: skill-memory]]` | Clear a skill's memory |
| `[[memory: skill-name]]` | Show specific skill's memory |
| `[[forget: pattern]]` | Remove a learned pattern |

## Scripts

- `scripts/skill-memory.py` — manages skill memory files, reads/writes learned patterns