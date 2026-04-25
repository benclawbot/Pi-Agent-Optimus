---
name: context-memory
description: Maintain project memory and conventions. Use when "remember this", "add to context", "project memory", "store convention", "remember the pattern", or onboarding to a new project.
---

# Context Memory

Store and retrieve project conventions, patterns, and state to avoid re-explaining things across sessions.

## Memory File Location

Project memory lives at `.pi/memory.md` in the project root. If it doesn't exist, create it.

## Memory Structure

```markdown
# Project Memory

## Conventions
<!-- Coding standards, patterns to follow -->

## Architecture
<!-- Key architectural decisions and why -->

## Current State
<!-- Active work, known issues, recent changes -->

## Patterns
<!-- Reusable code patterns, templates, examples -->

## Gotchas
<!-- Common pitfalls, known workarounds -->
```

## Commands

### Store Information

When the user tells you something important about the project, add it to `.pi/memory.md`:

1. Read the current `.pi/memory.md` (create if missing)
2. Determine which section applies
3. Add the information with context
4. Write the file

**Example:** User says "we always use Effect for services"
```
# Read existing memory
read .pi/memory.md

# Add to conventions section:
## Conventions
- Use Effect for all service layer code (never plain classes)
```

### Retrieve Information

Start each project session by checking memory:

```
read .pi/memory.md
```

If it exists, briefly summarize relevant conventions at the start of work.

### Update for New Discoveries

When you discover something that should be remembered:
- Pattern that works well → add to Patterns
- Architectural decision → add to Architecture  
- Common mistake → add to Gotchas

## What to Remember

| Category | Examples |
|----------|----------|
| Conventions | "Use TypeScript strict mode", "No default exports" |
| Architecture | "We use Event Sourcing for orders", "Auth via middleware" |
| Current State | "Migrating from REST to GraphQL", "Deprecating v1 API" |
| Patterns | "Service creation pattern", "Test setup boilerplate" |
| Gotchas | "Don't use Date, use dayjs", "CSS import order matters" |

## Rules

- Keep entries concise — one paragraph max per item
- Include "why" for architectural decisions
- Update rather than duplicate — if a pattern changes, update the old entry
- Never invent memory — only store what the user or codebase tells you
- If `.pi/memory.md` doesn't exist and you have no information, skip this step