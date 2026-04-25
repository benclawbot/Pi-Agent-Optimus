---
name: startup
description: Load user preferences and project memory at session start. This skill runs automatically to ensure consistent behavior across sessions. Use when "load preferences", "read memory", "startup", or at session initialization.
allowed-tools: Read
---

# Startup Memory Loader

Automatically loads user preferences and project memory at session start.

## What Gets Loaded

### 1. User Preferences
**File:** `~/.pi/user-memory.md`

Loaded first to apply your communication style and work preferences.

### 2. Project Memory
**File:** `.pi/memory.md` (in current project)

Loaded if exists to apply project-specific conventions.

### 3. Session History
Session files are auto-loaded from previous session, enabling session continuation.

## Startup Process

1. Check for `~/.pi/user-memory.md` → apply preferences
2. Check for `.pi/memory.md` in current directory → apply project conventions
3. Check for recent session in same directory → offer to resume
4. Apply loaded preferences to interaction style

## What Gets Applied

From user-memory:
- Communication verbosity (concise vs detailed)
- Format preferences (bullets, tables, etc.)
- Work style (ask first vs act autonomously)
- Tool preferences
- Git workflow preferences

From project memory:
- Conventions to follow
- Architecture decisions
- Current state of work
- Gotchas to watch for

## No Action Needed

This skill runs automatically. No trigger needed from user.

## Integration

This skill is referenced in `~/.pi/agent/settings.json` under `skills` to ensure auto-loading at startup.
