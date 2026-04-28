---
name: quick-context
description: Wikilink-style context retrieval using [[double-bracket]] syntax matching Thomas's Obsidian vault习惯. Use [[project-name]], [[decision]], [[context]], or [[skill name]] anywhere in a message for instant context. Triggers on any [[...]] pattern.
allowed-tools: Read
---

# Quick Context via Wikilinks

Thomas uses `[[double brackets]]` — the same as his Obsidian vault. Any `[[...]]` pattern in a message is a context request. Resolve it instantly.

## Resolution Order

When Thomas types `[[something]]`:

```
1. Check ~/.pi/agent/context-today.md       ← current session memory
2. Check ~/Dropbox/memory/Obsidian/          ← vault project files
3. Check ~/.pi/agent/skills/                ← skill references
4. Check recent conversations               ← decisions, context
5. Check Active Context                     ← current priorities
6. Not found → ask Thomas what they meant
```

## Built-in Context Links

| Link | Resolves to |
|------|-------------|
| `[[context]]` or `[[mem]]` | proactive-context summary |
| `[[decisions]]` | Recent decisions from conversations |
| `[[active]]` | Active Context, full |
| `[[continue]]` | Last session summary |
| `[[projects]]` | Active project briefs |
| `[[health]]` | project-health status |
| `[[memory]]` | context-memory summary |
| `[[skills]]` | Available skills with triggers |

## Project Wikilinks

Thomas types `[[liquidity-pulse]]` or `[[llm-knowledge-base]]`:

1. Read `~/Dropbox/memory/Obsidian/Projects/{name}/overview.md`
2. Extract: current state, decisions, blockers, key files
3. Present: one-paragraph brief + current pressure
4. Offer: "Want me to check health / read decisions / look at recent work?"

## Decision Wikilinks

`[[decisions]]` or `[[decision: topic]]`:

1. Search recent conversations for `decision:`, `decided:`, `agreed:`, `conclusion:`
2. List: [date] [decision] [source conversation]
3. If `[[decision: auth]]` → search for auth-related decisions

## Skill Wikilinks

`[[skill-name]]` or `[[skill: name]]`:

1. Find skill in `~/.pi/agent/skills/`
2. Load SKILL.md summary
3. Present: triggers, what it does, current state
4. Activate if Thomas confirms

## Format

```markdown
[[liquidity-pulse]]

Liquidity Pulse — Active
Status: Working full-stack MVP (FastAPI + frontend)
Last session: [1 line]
Key files: backend/main.py, frontend/js/app.js
Pressure: [from Active Context]

Quick links:
- [[decisions]] for this project
- [[health]] to check CI/deps
- [[continue]] to see session history
```

## Disambiguation

If `[[buffer]]` matches multiple things:
- `[[buffer: crypto]]` → buffer + crypto context
- `[[buffer: typescript]]` → buffer in ts context
- `[[buffer]]` → list matches

## Commands

| Pattern | Action |
|---------|--------|
| `[[name]]` | Context for named project, skill, or topic |
| `[[name: detail]]` | Context with disambiguation |
| `[[context]]` | Session context summary |
| `[[decisions]]` | All recent decisions |
| `[[decisions: topic]]` | Decisions about specific topic |
| `[[skills]]` | List all available skills |
| `[[health]]` | Quick project health check |
| `[[memory]]` | What's stored in context-memory |

## Token Efficiency

- Resolve wikilinks first, then respond to Thomas's actual question
- Only load full files when relevant
- Summaries over full files at start
- Thomas can type `[[context]]` alone to refresh, then continue naturally
