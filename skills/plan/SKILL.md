---
name: plan
description: Requirements gathering and planning skill. Use when asked to "plan", "create a plan", "clarify requirements", or "spec out". Asks one question at a time until requirements are fully understood, then proposes an implementation plan for user review. Once approved, executes in YOLO mode until complete - no further user action required.
---

# Requirements Gathering & Planning Skill

## Summary

Gathers project requirements through structured questioning, one question at a time. Once requirements are complete, generates a detailed implementation plan for user approval. **Approval triggers immediate YOLO execution - no Enter press, no further commands needed.**

## Workflow

### Phase 1: Requirements Gathering

The skill operates as a **conversation loop** — ask ONE question, wait for answer, then decide next question based on answer.

#### Question Categories

**A. Project Overview (ask first)**
- What is the project called?
- What does it do?
- Who are the users?

**B. Current State**
- What exists today?
- What is the current architecture?
- What's working and what's broken?

**C. Target State**
- What should happen when complete?
- What does success look like?
- What are the non-goals (what it explicitly should NOT do)?

**D. Technical Requirements**
- What technologies are required?
- Are there existing codebases to integrate with?
- What are the deployment constraints?

**E. User Experience**
- Who interacts with this and how?
- What are the key user flows?
- What does mobile vs desktop look like?

**F. Constraints & Risks**
- What's the timeline?
- What could go wrong?
- What's been tried before that didn't work?

#### When to Ask What

1. **Start with Project Overview** (A) if you don't understand the basic what/why
2. **Ask about Current State** (B) to understand existing assets
3. **Ask about Target State** (C) to clarify goals
4. **Deep-dive Technical** (D) when you need to build something
5. **Clarify UX** (E) when behavior matters
6. **Check Constraints** (F) before proposing a plan

#### Decision Tree for Next Question

After each answer:
1. Does the answer complete the current category? → Move to next category
2. Is more detail needed on this topic? → Ask follow-up
3. Do you now understand enough to move on? → Ask about next priority area
4. Is something mentioned that needs context? → Ask for clarification

#### When Requirements Are "Done"

Stop asking questions when you can answer:
- ✅ What is being built?
- ✅ What is the starting point?
- ✅ What is the ending point?
- ✅ What technologies/methods are involved?
- ✅ Who will use it and how?
- ✅ What are the constraints?

### Phase 2: Create Implementation Plan

After requirements are gathered, create a structured plan:

```
# [Project Name] Implementation Plan

## Overview
[2-3 sentence summary of what will be built]

## Current State
[What's there today]

## Target State  
[What will exist after implementation]

## Work Items

### Phase 1: [Name]
| Task | Description | Estimated |
|------|-------------|-----------|
| T1.1 | [Task name] | [Description] | [Size estimate] |

### Phase 2: [Name]
| Task | Description | Estimated |
|------|-------------|-----------|
| T2.1 | [Task name] | [Description] | [Size estimate] |

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | [Impact] | [Mitigation] |

## Dependencies
[External dependencies, prerequisites]

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
```

### Phase 3: User Review

Present the plan and ask:
> "Does this plan cover everything? What needs to change?"

**If changes requested:** Update plan and re-present.
**If approved:** → **Execute immediately, no further prompts**

### Phase 4: YOLO Execution (Automatic)

**When user approves the plan, execution starts IMMEDIATELY without any further user action.**

Execution steps:
1. Create todos for each work item using the `todo` tool
2. Execute tasks using `execute_command` with `/subagent worker` for complex tasks
3. Report progress inline as tasks complete
4. Mark items done using `todo` tool
5. Continue until ALL todos complete
6. Report final status when done

#### Sub-Agent Delegation Pattern

For complex tasks, delegate with full context:
```
execute_command: /subagent worker [task description] --context [relevant files and context]
```

Provide each sub-agent:
- Clear task description
- Relevant file paths
- Key constraints
- Expected output

**Execute sub-agents via `execute_command` tool, not as a command to type.**

## Exit Conditions

**This skill completes when:**
1. ✅ ALL work items are complete
2. ✅ User confirms success (or explicit sign-off)

**Or when user says:**
- "Stop" / "Cancel" / "Abort"
- "That's enough for now"
- "Let's do this later"

## Tips

### Good Questioning Practice
- One question at a time (no compound questions)
- Be specific, not vague
- "What should happen when X?" not "Tell me about X"
- Ask for concrete examples when abstract

### Bad Questioning Practice
- ❌ "Tell me everything about your project" (too broad)
- ❌ "What are the requirements? And also what's your budget?" (compound)
- ❌ "Do you want the chat at the bottom or side?" (jumping ahead)

### Knowing When to Stop
If you find yourself asking questions you could reasonably guess the answer to, make a reasonable assumption and note it in the plan. You can always clarify during review.

### YOLO Mode Reminders
- Execute tasks immediately without waiting for confirmation
- Use sub-agents for parallel work where possible
- Report progress as you go
- If blocked, make reasonable assumptions and continue
- Trust the plan - execute it as written unless user explicitly asks for changes
