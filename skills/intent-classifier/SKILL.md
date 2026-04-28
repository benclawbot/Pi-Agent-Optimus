---
name: intent-classifier
description: Auto-detects what Thomas is trying to do — coding, debugging, architecture, research, health check — and routes to relevant skills. Activates the right combination without Thomas having to name skills explicitly. Use when skills should activate automatically based on what you're doing, or when you want to know what the current intent is.
allowed-tools: Read,Bash
---

# Intent Classifier

Auto-detects what Thomas is working on and activates the relevant skills. Thomas doesn't invoke skills — the context signals what he needs.

## How It Works

1. **Signal Detection** — Analyzes the current message and context for intent signals.
2. **Skill Routing** — Routes to the relevant combination of skills.
3. **Chain Activation** — Triggers skill-chain to activate related skills together.

## Intent Categories

| Intent | Signals | Activates |
|--------|---------|-----------|
| **coding** | file paths, function names, `def`, `class`, `import`, `const` | auto-test, context-memory, project-health |
| **debugging** | `error`, `bug`, `crash`, `stack`, `failed`, `Exception` | auto-recover, system-awareness, context-memory |
| **architecture** | `design`, `structure`, `diagram`, `component`, `architecture` | architecture-diagram, context-memory |
| **research** | `search`, `find`, `look up`, `what is`, `explain` | context-memory, quick-context |
| **health-check** | `health`, `status`, `deps`, `outdated`, `ci` | project-health, ci-watcher |
| **testing** | `test`, `pytest`, `run tests`, `coverage` | auto-test, project-health |
| **planning** | `plan`, `next steps`, `how to`, `should we` | context-memory, architecture-diagram |
| **review** | `review`, `PR`, `pull request`, `check this` | ci-watcher, auto-test |
| **ops** | `deploy`, `server`, `running`, `port`, `process` | system-awareness, project-health |

## Detection Patterns

```python
INTENT_PATTERNS = {
    "debugging": [
        r"error\b", r"bug\b", r"crash\b", r"failed\b", r"Exception\b",
        r"traceback", r"stack.*trace", r"doesn't work", r"broken",
        r"fix this", r"what went wrong"
    ],
    "coding": [
        r"\.(py|js|ts|jsx|tsx|go|rs|java|cpp)\b",  # file extensions
        r"def\s+\w+\(", r"class\s+\w+", r"import\s+\w+",
        r"function\s+\w+", r"const\s+\w+\s*=", r"let\s+\w+\s*=",
        r"=>", r"->", r"fn\s+\w+", r"func\s+\w+"
    ],
    "architecture": [
        r"architecture", r"system design", r"component map",
        r"diagram", r"structure", r"design pattern",
        r"how do i structure", r"what's the best way to"
    ],
    "research": [
        r"what is", r"how does", r"explain", r"search for",
        r"find information", r"look up", r"research",
        r"tell me about", r"what's a"
    ],
    "health-check": [
        r"health", r"status", r"deps", r"outdated",
        r"ci status", r"test coverage", r"are we green"
    ],
    "testing": [
        r"test", r"pytest", r"coverage", r"run tests",
        r"unit test", r"integration test", r"spec"
    ],
    "planning": [
        r"plan", r"next steps", r"how to", r"should we",
        r"roadmap", r"milestones", r"getting started"
    ],
    "ops": [
        r"deploy", r"server", r"running", r"port",
        r"process", r"docker", r"kubernetes", r"ci/cd"
    ]
}
```

## Intent Resolution

When you receive a message:

1. Run intent detection on the message text + context
2. Determine primary intent and any secondary intents
3. Activate the primary intent's skill combination
4. Show brief indicator: "Detected: [intent] → [skills activated]"

## Output Format

```
Intent: debugging
Confidence: high
Signals: error message, stack trace detected
Activating: auto-recover, system-awareness, context-memory
Chain: running
```

## Commands

| Command | Action |
|---------|--------|
| `[[intent]]` | Show current detected intent |
| `[[intent: type]]` | Override intent (e.g., `[[intent: coding]]`) |
| `[[skills]]` | List what skills are active based on intent |
| `[[intents]]` | Show all intent categories and their signals |

## Scripts

- `scripts/classify.py` — detects intent from text, returns intent + confidence + skills to activate