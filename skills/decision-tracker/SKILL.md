---
name: decision-tracker
description: Persists decisions from conversations to ~/.pi/agent/decisions.md. One-word trigger to recall decisions. Use when "decided", "decision", "what did we decide", "agreed on", or at session start when a decision is made.
allowed-tools: Read,Bash
---

# Decision Tracker

Decisions made in conversation get stored. Thomas never loses track of what was agreed.

## Decision Log

**Location:** `~/.pi/agent/decisions.md`

```markdown
# Decisions Log

## 2026-04-28 — liquidity-pulse
Decision: Use Effect for service layer (never plain classes)
Context: "we were discussing architecture for /api/orders"
Source: Conversation 2026-04-28

## 2026-04-27 — llm-knowledge-base
Decision: Use pgvector for embeddings (not pinecone)
Context: "evaluating vector DB options"
Source: Architecture review

## 2026-04-25 — dropsync-pwa
Decision: PWA first, native app later
Context: "mobile strategy discussion"
Source: Meeting 2026-04-25
```

## How It Works

1. During conversation, detect decision signals:
   - "decided", "agreed", "conclusion", "going with", "using X over Y"
   - "we will", "we're going to", "choice is"
2. Parse: what was decided, project/context, date
3. Store to `decisions.md`
4. Thomas can recall with `[[decisions]]` or `[[decisions: topic]]`

## At Decision Point

When Thomas says something that sounds like a decision:

1. Confirm: "Save this as a decision: [summary]?"
2. If yes → write to `decisions.md`
3. Acknowledge: "✓ Decision saved. Next?"

## Retrieval

`[[decisions]]` → shows all decisions, newest first  
`[[decisions: auth]]` → filters to auth-related decisions  
`[[decisions: liquidity-pulse]]` → decisions for that project

Format:
```
 Decisions (8)

 2026-04-28 | liquidity-pulse
 Use Effect for service layer (not plain classes)

 2026-04-27 | llm-knowledge-base  
 Use pgvector over pinecone (cost + control)

 2026-04-25 | dropsync-pwa
 PWA first, native later
```

## Commands

| Command | Action |
|---------|--------|
| `[[decisions]]` | All decisions, newest first |
| `[[decisions: topic]]` | Filter by topic/project |
| `[[decide: summary]]` | Save current as decision |
| `[[decisions clear]]` | Archive old decisions |

## Auto-Capture

When conversation ends and a decision was made:
- "Want me to save the decision we just made?"
- If yes → append to `decisions.md`

## Scripts

- `scripts/decisions.py` — read/write decisions, filter by topic/project