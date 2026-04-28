---
name: skill-chain
description: Automatically chains related skills based on context. Detects what Thomas is working on and activates the right combination of skills without manual invocation. Use when skills should work together, when context suggests related skills, or when one skill triggers another.
allowed-tools: Read,Bash
---

# Skill Chaining

Skills activate together based on context — not just standalone commands.

## Core Concept

Thomas doesn't invoke skills manually. The context signals what skills are relevant, and skills chain together:

```
system-awareness detects dev server → auto-test activates
project-health finds stale deps → auto-recover suggests fixes
proactive-context loads project → relevant skills activate

coding in TypeScript → ts-patterns, error-handling, testing
working on llm-knowledge-base → context-memory, architecture-diagram
reading error logs → auto-recover
```

## Trigger Detection

Skills activate based on **context signals**:

| Signal | Triggers |
|--------|----------|
| File pattern `*.py` | python-patterns, testing |
| File pattern `*.ts`, `*.tsx` | ts-patterns, testing |
| `package.json` detected | project-health, auto-test |
| `Cargo.toml` / `*.rs` | rust-patterns, testing |
| Error message / stack trace | auto-recover, debugging |
| Dev server running | system-awareness, auto-test |
| Git diff / PR | code-review, ci-watcher |
| New file creation | context-memory, architecture-diagram |
| `[[context]]` at startup | proactive-context |
| Health check requested | project-health |
| Error recovery requested | auto-recover |
| Testing requested | auto-test |
| Architecture discussed | architecture-diagram |
| Time/reminder mentioned | scheduler |

## Skill Combinations

### Coding Session
```
proactive-context → skill-chain → [auto-test + project-health + context-memory]
```

### Debugging Session
```
auto-recover → skill-chain → [context-memory + system-awareness]
```

### Architecture Discussion
```
proactive-context → skill-chain → [architecture-diagram + context-memory]
```

### Project Kickoff
```
proactive-context → skill-chain → [context-memory + architecture-diagram + project-health]
```

### CI/CD Monitoring
```
ci-watcher → skill-chain → [project-health + auto-recover]
```

## Chain Activation

When a skill detects its trigger:

```
1. Emit a "chain signal" (internal note of what was activated)
2. skill-chain checks for related skills
3. Related skills activate if their triggers are present
4. Thomas sees the combination without invoking anything

Example:
- Thomas: "check the liquidity-pulse backend"
- skill-chain detects: project reference + backend + server
- Chains: proactive-context (loads project) + system-awareness (check server) + auto-recover (if errors)
```

## Skill Registry

Tracks which skills exist and their dependencies:

```json
{
  "auto-test": {
    "triggers": ["test", "testing", "run tests", "test this"],
    "chains_with": ["project-health", "auto-recover"],
    "domains": ["code", "backend", "frontend"]
  },
  "auto-recover": {
    "triggers": ["error", "bug", "crash", "failed", "broken"],
    "chains_with": ["context-memory", "system-awareness"],
    "domains": ["code", "runtime", "ci"]
  },
  "system-awareness": {
    "triggers": ["server", "running", "process", "port", "localhost"],
    "chains_with": ["auto-test", "auto-recover"],
    "domains": ["runtime", "dev"]
  },
  "project-health": {
    "triggers": ["health", "deps", "outdated", "ci status"],
    "chains_with": ["auto-recover"],
    "domains": ["project", "ci", "deps"]
  },
  "architecture-diagram": {
    "triggers": ["architecture", "diagram", "system design", "component"],
    "chains_with": ["context-memory"],
    "domains": ["design", "architecture"]
  },
  "context-memory": {
    "triggers": ["remember", "convention", "pattern", "context"],
    "chains_with": ["proactive-context"],
    "domains": ["project", "memory"]
  }
}
```

## Activation Rules

1. **Explicit wins** — if Thomas names a skill, activate it directly
2. **Context adds** — detected signals activate related skills
3. **No over-activation** — max 3 skills chained per context signal
4. **Thomas controls** — `[[skills off]]` disables chaining
5. **Token-aware** — chain only the top 3 most relevant skills

## Commands

| Command | Effect |
|---------|--------|
| `[[skills on]]` | Enable chaining (default) |
| `[[skills off]]` | Disable chaining |
| `[[chain]]` | Show what skills are currently active |
| `[[chain: skill-name]]` | Add a skill to current chain |
| `[[unchain: skill-name]]` | Remove from current chain |
| `[[skills]]` | List all available skills with their triggers |

## Scripts

- `scripts/detect-context.py` — detects context signals from text + project files, emits skill activation suggestions
- `scripts/chain-skills.py` — activates skills, manages active chain state, expands via chains_with

## Chain State

Active chain state is persisted to `~/.pi/agent/.chain-state.json`.

## Usage

Thomas doesn't invoke skills manually. When he types a message:
1. `detect-context.py` analyzes the text for context signals
2. `chain-skills.py` activates the matched skills (up to 3)
3. Thomas sees the skills activate without any explicit command

```bash
python3 scripts/detect-context.py "fix this error in main.py"
# → Detects: error signal + .py file
# → Activates: auto-recover, system-awareness, context-memory

python3 scripts/chain-skills.py --chain auto-recover,system-awareness
# → Activates both + any chains_with skills

python3 scripts/chain-skills.py --status
# → Shows currently active skills

python3 scripts/chain-skills.py --off
# → Disables chaining (Thomas can re-enable with --on)
```
