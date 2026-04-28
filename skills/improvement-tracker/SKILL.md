---
name: improvement-tracker
description: Tracks the top 30 Pi agent improvements, auto-updates as fixes are applied, and returns to the list at session start. When Thomas asks "improvements", "todo", "pending fixes", "progress", or at session start. Auto-deletes the todo when complete and stores a summary of changes applied.
allowed-tools: Read,Bash
---

# Improvement Tracker

Tracks the top 30 Pi agent improvements. Auto-updates as fixes are applied. When the list is complete, deletes itself and stores the summary of all changes applied.

## The 30 Improvements

### Memory & Continuity

| # | Improvement | Status | Impact |
|---|-------------|--------|--------|
| 1 | Proactive context at session start — surface relevant memories, active projects, pending work, recent decisions | **DONE** | 🔴 Critical |
| 2 | Task continuity across sessions — detect when a task spans multiple conversations | **TODO** | 🔴 Critical |
| 3 | Quick context command — `[[context]]` or `[[mem]]` inline for instant context | **DONE** | 🟠 High |
| 4 | Decision tracker — persist decisions to context-memory/ with one-word triggers | **TODO** | 🟠 High |
| 5 | Daily standup generator — summarize recent conversations into done/in-progress/blocked/decisions | **TODO** | 🟠 High |
| 6 | Task memory layer — track what's being worked on, link to files, show at startup | **TODO** | 🟡 Medium |
| 7 | Cross-conversation task linking — link tasks mentioned across conversations | **TODO** | 🟡 Medium |

### Context & Retrieval

| # | Improvement | Status | Impact |
|---|-------------|--------|--------|
| 8 | Vault context compiler — read project overview + active context + recent decisions at startup | **TODO** | 🔴 Critical |
| 9 | Wikilink-style context — `[[project-name]]` for instant project status | **DONE** | 🟠 High |
| 10 | Intent classifier — auto-detect coding/debugging/architecture/health, route to skills | **TODO** | 🟡 Medium |
| 11 | Conversational memory summarizer — capture discoveries, decisions, open items | **TODO** | 🟡 Medium |

### Skills & Interoperability

| # | Improvement | Status | Impact |
|---|-------------|--------|--------|
| 12 | Skill chaining — system-awareness detects dev server → auto-test activates | **DONE** | 🔴 Critical |
| 13 | Tech stack auto-detection — read package.json, Cargo.toml → trigger relevant skills | **TODO** | 🟠 High |
| 14 | Skill marketplace — index available skills, show what's relevant to current context | **TODO** | 🟡 Medium |
| 15 | Skill memory sharing — auto-recover learns from past fixes, project-health learns | **TODO** | 🟡 Medium |
| 16 | Quick skill command — `[[skill name]]` to load skill context | **TODO** | 🟡 Medium |

### Reasoning & Delivery Quality

| # | Improvement | Status | Impact |
|---|-------------|--------|--------|
| 17 | Chain-of-thought reveal on critical paths — show reasoning before acting | **TODO** | 🔴 Critical |
| 18 | Change log from conversations — generate .changes/ log per project per week | **TODO** | 🟠 High |
| 19 | Architecture diagram as default output — offer SVG proactively when Thomas describes a system | **TODO** | 🟠 High |
| 20 | Implementation plan generator — auto-generate structured plans from conversation | **TODO** | 🟡 Medium |
| 21 | Code pattern library — extract patterns from actual code changes | **TODO** | 🟡 Medium |

### Speed & Token Efficiency

| # | Improvement | Status | Impact |
|---|-------------|--------|--------|
| 22 | Startup context optimizer — load only the 3 most relevant vault notes | **TODO** | 🔴 Critical |
| 23 | Smart file selection — retrieve by semantic relevance, not just name | **TODO** | 🟠 High |
| 24 | Incremental context loading — minimal at start, grow as conversation develops | **TODO** | 🟠 High |
| 25 | Project memory snapshot — after each session, snapshot project state | **TODO** | 🟡 Medium |

### Productivity & Workflow

| # | Improvement | Status | Impact |
|---|-------------|--------|--------|
| 26 | Quick project switch — `[[goto project]]` instantly loads context | **TODO** | 🟠 High |
| 27 | Pending work dashboard — surface tasks started but not finished, blockers | **TODO** | 🟠 High |
| 28 | Auto-fix from past errors — learn error patterns, auto-suggest fixes | **TODO** | 🟡 Medium |
| 29 | Effort vs. progress tracker — per project: hours talked vs. shipped | **TODO** | 🟡 Medium |
| 30 | Conversation-to-memory command — `[[save this]]` mid-conversation to persist thread | **TODO** | 🟡 Medium |

## Tracking File

**Location:** `~/.pi/agent/improvement-tracker.md`

When an improvement is applied:
1. Mark it **DONE** in the tracking file
2. Add: date applied, what was built, where it lives
3. If **all 30 are DONE**: delete the tracker, create `improvement-summary.md` with the full list of changes applied

## Commands

| Command | Action |
|---------|--------|
| `[[improvements]]` | Show full list with current status |
| `[[progress]]` | Show only what's DONE vs TODO |
| `[[done: 1]]` | Mark improvement #1 as done, record what was built |
| `[[todo]]` | Same as `[[improvements]]` |
| `[[improve: skill-name]]` | Suggest a new improvement to add |

## Auto-Behavior

At session start:
1. Check `~/.pi/agent/improvement-tracker.md`
2. If exists and has progress: show `[[progress]]` summary
3. If exists and all DONE: run completion protocol
4. Offer: "Continue with improvement #[N]?"

## Completion Protocol

When all 30 are DONE:
1. Create `~/.pi/agent/improvement-summary.md` with:
   - Full list of changes applied
   - Date completed
   - What improved
2. Delete `~/.pi/agent/improvement-tracker.md`
3. Say: "All 30 improvements applied. Summary saved to improvement-summary.md. Starting fresh."
