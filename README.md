# Pi Config

My personal [pi](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) configuration — agents, skills, extensions, and prompts.

## Setup

```bash
git clone https://github.com/benclawbot/Pi-Agent-Optimus.git
cd Pi-Agent-Optimus
./setup.sh
```

On Windows, run `.\setup.ps1`. The installer merges settings and preserves local secrets and user-selected defaults.

---

## What's Included

### Extensions
| Extension | Purpose |
|-----------|---------|
| **telegram** | Telegram bot bridge — chat with pi from anywhere |
| **btw** | Side-band steering without interrupting flow |
| **todos** | Full TUI todo manager |
| **todo-panel** | Persistent above-editor todo progress panel |
| **subagent** | Restricted delegated Pi process |
| **fusion** | Parallel MiniMax M2.7/M3 coding deliberation with an M3 judge |
| **repo-map** | Bounded repository map |
| **long-task** | Persistent long-task checkpoints |
| **load-skill** | Load skill instructions on demand |
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
/telegram              — start the exclusive poller and show status
```

The token and allowed users live in `~/.pi/telegram-config.json`, outside the repository. Only whitelisted users can access the bridge, and a process lock prevents duplicate pollers.

## Todo Panel

The persistent todo widget appears above the interactive editor, including when a project has no todos.

```
/todos       — open the full todo manager
/todo-panel  — force-refresh the persistent panel
```

The panel is a TUI widget and therefore does not render in `--mode text` or `--mode rpc`.

## MiniMax Fusion

The `fusion` tool runs independent MiniMax coding analyses in parallel, asks M3 to identify consensus, contradictions, unique insights, and blind spots, then returns the judged synthesis to the lead agent.

- `profile="lite"` is the default: M2.7 analyst + M3 critic + M3 judge.
- `profile="full"` adds a second independent M2.7 path.
- Use it for architecture, difficult debugging, risky migrations, security review, and expensive decisions.
- Avoid it for straightforward edits; lite Fusion plus the lead answer uses roughly four model completions, while full Fusion uses roughly five.

---

## Token Optimization

- **Model split**: M2.5 for workers/scouts (fast), M2.7 for reviewers/planners (reasoning)
- **Lazy skills**: specialist skills remain available as commands but are hidden from the default model prompt
- **Compaction**: 8K reserve, 15K keep (was 16K/20K)
- **Retry**: 2 max (was 3)
