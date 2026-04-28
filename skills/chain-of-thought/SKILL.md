---
name: chain-of-thought
description: On architecture, fix, or major refactor decisions, shows reasoning before acting. Thomas can course-correct before the agent goes down a wrong path. Use when planning, deciding, debugging complex issues, or when "why", "how", "reasoning" is needed.
allowed-tools: Read
---

# Chain-of-Thought Reveal

Shows the reasoning before acting on critical paths. Thomas sees what the agent is thinking and can correct before things go wrong.

## When It Activates

On these decision types, the agent explains its reasoning before proceeding:

| Situation | What to show |
|-----------|--------------|
| **Architecture decision** | Current understanding, options considered, tradeoffs, recommendation |
| **Fix approach** | Root cause analysis, alternative fixes, why the chosen approach |
| **Refactor plan** | Current state, target state, migration path, risks |
| **Tool selection** | Why this tool over alternatives, expected outcome |
| **Design choice** | Constraints, options, reasoning for the chosen direction |

## Format

```markdown
REASONING:

Current understanding:
- [what I think is going on]

Options considered:
A. [option A] — pros/cons
B. [option B] — pros/cons
C. [option C] — pros/cons

Recommendation: [B] because [reason]
Confidence: [high/medium/low]

Shall I proceed with [B]?
```

## Trigger Signals

The agent shows reasoning when:
- Thomas asks "why", "how", "what's the plan"
- The change affects architecture or core structure
- Multiple approaches exist and the choice matters
- The agent is uncertain about the right path
- The action could have significant side effects

## Commands

| Command | Action |
|---------|--------|
| `[[think]]` | Show current reasoning on what's being worked on |
| `[[why]]` | Explain why a particular decision or approach |
| `[[how]]` | Show how a solution was reached |
| `[[alternatives]]` | Show alternative approaches considered |
| `[[confidence]]` | Show how confident the agent is |

## When NOT to Show Reasoning

- Simple, well-defined tasks with clear correct answers
- When Thomas asks for speed over explanation
- Routine operations with no meaningful alternatives
- Very short responses where explanation would double the length

## Rules

1. **Show reasoning on critical paths** — architecture, fixes, refactors, design
2. **Keep reasoning brief** — not verbose, just the key decision factors
3. **Ask before acting on major paths** — give Thomas a chance to redirect
4. **Be explicit about uncertainty** — "I'm not sure about X, leaning toward Y because Z"