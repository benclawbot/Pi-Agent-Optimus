---
name: memory-summarizer
description: Captures discoveries, decisions, and open items from conversation as rich maps — not just skeletons. Use at end of session, with `[[summarize]]`, or when saying "what did we discover", "what's open", "summarize this".
allowed-tools: Read,Bash
---

# Conversational Memory Summarizer

Captures what was discovered, decided, and what's still open — as rich maps, not bare summaries.

## What Gets Captured

### Discoveries
Things Thomas learned or the system discovered during the session:
- Facts, insights, patterns found in code
- Architecture decisions explained
- New approaches identified

### Decisions
Formal decisions (also goes to `decisions.md`):
- Technology choices
- Architecture approaches
- Prioritization calls

### Open Items
Things that need follow-up:
- Bugs found but not fixed
- Questions raised but not answered
- Tasks identified but not started

### Conversation Map
The full conversation topology — not just a summary, but what connected to what:

```
├── Project setup
│   └── Decision: Use FastAPI (not Flask)
├── Feature: rate limiting
│   ├── Discovery: middleware is bottleneck
│   └── Open: test with k6
└── Next: finish rate limiting before EOD
```

## Output Format

```markdown
# Session Summary — 2026-04-28

## Discoveries
- Rate limiting middleware adds ~50ms latency
- LLM knowledge base embedding dimension must be 1536
- Pi agent context loading takes ~2s at startup

## Decisions
- Use Effect for service layer (not plain classes)
- PWA first, native app later (from earlier)

## Open Items
- Fix rate limit config bug (in progress)
- Decide embedding dimensions for llm-knowledge-base
- Review dropsync-pwa PR

## Conversation Map
[see above]
```

## When It Runs

1. **`[[summarize]]`** — Generate full session summary
2. **`[[discoveries]]`** — Show only discoveries from this session
3. **`[[open]]`** — Show only open items
4. **`[[map]]`** — Show conversation map
5. **`[[save]]`** — Save the current thread/point mid-conversation to memory
6. **At end of session** — "Save summary?" prompt before session closes

## [[save]] Command

Thomas types `[[save: important insight about X]]` or `[[save this]]`:
- Saves to `~/.pi/agent/session-summaries/threads-YYYY-MM-DD.md`
- Timestamped with session time
- Appended to daily thread log
- Available via `[[discoveries]]` and `[[summarize]]`

```bash
python summarize.py --save-thread "Use Effect for service layer not plain classes"
# → ✓ Thread saved (58 chars)
```

## Format Rules

- **Discovery lines start with `-`** and are specific (not vague)
- **Decision lines include context** — why this choice was made
- **Open items are tagged** — `@project`, `@priority`, `@blocked`
- **Conversation map uses tree structure** — `├──` and `└──` for topology

## Scripts

- `scripts/summarize.py` — generates session summary, manages thread storage