---
name: improvement-tracker
description: Identifies 30 new improvement areas in Hermes/Pi agents and fixes them one by one by criticality. Use when Thomas asks "improvements", "improve the agent", "pending fixes", "fix status", or "what are we fixing". Auto-fixes in priority order — no approval questions.
allowed-tools: Read,Bash
---

# Improvement Tracker

Identifies new improvement areas in Hermes/Pi agents, proposes solutions, approves them, then tracks fixes to completion via a todo list. If interrupted mid-fix, you can resume exactly where you left off.

## Tracker File

**Location:** `~/.pi/agent/improvement-tracker.md`

```markdown
# Improvement Tracker
Generated: 2026-05-02
Total: 30 improvements across 6 categories

## candidate
[ ] approved
[ ] rejected

## approved
[ ] id: 1
    area: Memory & Continuity
    issue: <what's wrong or missing>
    solution: <concrete fix or feature>
    effort: low|med|high
    status: pending|in_progress|deferred|done
    applied_date: -
    notes: -

## backlog
[ ] id: 2
    area: ...
```

## Commands

| Command | Action |
|---------|--------|
| `[[improvements]]` | Show full tracker — all 30 candidates with status |
| `[[improvements: generate]]` | Generate 30 new improvement candidates, auto-approved by priority |
| `[[fix: N]]` | Start working on improvement #N (or pick next pending if N omitted) |
| `[[fix: N: notes]]` | Add notes to improvement #N (e.g. blocker, partial progress) |
| `[[fix: N: defer]]` | Defer improvement #N to backlog |
| `[[fix: abort]]` | Save current fix state to notes, stop work |
| `[[fix status]]` | Show all approved fixes with their current status |

## Generation

When `[[improvements: generate]]` is called:

1. Scan the codebase and config:
   - `~/.pi/agent/` — all skills, settings.json, user-memory.md
   - `~/.hermes/` — skills, config, memory systems
   - Active sessions in `~/.hermes/sessions/` — recent pain points
   - The Pi Agent base at `~/.pi/agent/` — what extensions actually override

2. Identify 30 improvement areas across 6 categories:

### Category 1: Memory & Continuity
Issues where the agent forgets, loses context, or can't resume work.

### Category 2: Context & Retrieval
Issues where relevant context is available but not surfaced at the right time.

### Category 3: Skill System
Issues with how skills are loaded, chained, or how they share knowledge.

### Category 4: Reasoning & Output Quality
Issues with how the agent thinks, explains, or delivers results.

### Category 5: Speed & Token Efficiency
Issues with latency, startup time, or token waste.

### Category 6: Workflow & Automation
Issues with recurring tasks, proactive behavior, or task management.

3. For each improvement, write:
   - **area**: which category
   - **issue**: what's wrong or missing in one sentence
   - **solution**: concrete fix or feature in one sentence
   - **effort**: `low` (minutes), `med` (hours), `high` (days)

4. Store all 30 in the tracker under `## candidate` with `[ ] approved`.

## Approval

Auto-approve everything. No questions. Generation implies all 30 are approved and queued by priority (high/critical first, then by effort within each tier).

After generation, immediately start with the highest-priority pending fix. No approval step needed.

## Todo-Driven Fix Tracking

Approved improvements live in `## approved`. Only one is `in_progress` at a time.

When called with `[[fix: N]]`:
1. Check improvement #N exists and is `pending` or `deferred`
2. Set status to `in_progress`
3. Show: area, issue, solution, effort, and current notes
4. Implement the solution — do not ask permission, just do it
5. After each atomic change: say what changed, move toward completion
6. If blocked: note the blocker in `notes`, set status to `pending`, move to next
7. When done: set status to `done`, record `applied_date`, auto-pick up the next pending fix

When `[[fix: abort]]` is called during active work:
1. Set status to `pending`
2. Add to notes: current state, what's done, what's left
3. Say: "Progress saved. Say `[[fix: N]]` to resume when ready."

When all approved fixes are `done`:
1. Write `~/.pi/agent/improvement-summary.md` with all applied fixes
2. Say: "All 30 fixes complete. Summary saved to improvement-summary.md."

## Format Rules

- Each improvement is one block with id, area, issue, solution, effort, status, applied_date, notes
- Status values: `pending` | `in_progress` | `deferred` | `done`
- Never overwrite notes — append with timestamps
- The tracker file never auto-deletes until all approved items are done
