# Pi Config

My personal [pi](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) configuration — agents, skills, extensions, and prompts.

## Setup

```bash
git clone git@github.com:benclawbot/Pi-Agent-Optimus.git ~/.pi/agent
cd ~/.pi/agent && npm install
```

---

## What's Included

### Extensions
| Extension | Purpose |
|-----------|---------|
| **telegram** | Telegram bot bridge — chat with pi from anywhere |
| **btw** | Side-band steering without interrupting flow |
| **status** | Project health overlay |
| **cmux** | Sidebar status integration |
| **auto-commit** | Prompts for commit after work sessions |
| **commit-review** | Diff summary before commits |
| **compact-tools** | One-liner tool rendering |
| **todos** | Full TUI todo manager |
| **reload** | Hot-reload extensions |

### Agents
| Agent | Model | Purpose |
|-------|-------|---------|
| **spec** | M2.7 | Interactive WHAT clarifier |
| **planner** | M2.7 | Interactive HOW planner |
| **scout** | M2.5 | Fast codebase recon |
| **worker** | M2.7 | Implements + commits todos |
| **reviewer** | M2.7 | Code quality/security review |
| **researcher** | M2.7 | Deep research + web discovery |
| **fullstack** | M2.5 | Web development specialist |

### Skills (lazy-loaded)
| Skill | Trigger |
|-------|---------|
| startup, context-memory, skill-evolution, quick-ref, write-todos | On startup / command |

---

## Telegram Bot

The Telegram extension lets you chat with pi via @Ben2clawbot.

```
/telegram set <token>   — configure bot token
/telegram clear        — remove configuration  
/telegram status       — show connection status
```

Only whitelisted users can access (configured in `telegram-config.json`).

---

## Token Optimization

- **Model split**: M2.5 for workers/scouts (fast), M2.7 for reviewers/planners (reasoning)
- **Lazy skills**: Only 5 skills at startup (~8KB), rest load on-demand
- **Compaction**: 8K reserve, 15K keep (was 16K/20K)
- **Retry**: 2 max (was 3)
