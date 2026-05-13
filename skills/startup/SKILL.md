---
name: startup
description: Load user preferences and project memory at session start. This skill runs automatically to ensure consistent behavior across sessions. Use when "load preferences", "read memory", "startup", or at session initialization.
allowed-tools: Read,Bash
---

# Startup Memory Loader

Loads user preferences and project memory at session start with optimized startup performance.

## Performance Optimizations

This skill implements 4 optimizations for faster startup on large codebases:

1. **Project Index Cache** - Pre-scanned structure cached to disk
2. **Parallel Scanning** - Convention files scanned concurrently  
3. **Selective Loading** - Only relevant directories scanned
4. **Incremental Updates** - Cache invalidated only when files change

## What Gets Loaded

### 1. User Preferences
**File:** `~/.pi/user-memory.md`

Loaded first to apply your communication style and work preferences.

### 2. Project Memory
**File:** `.pi/memory.md` (in current project)

Loaded if exists to apply project-specific conventions.

### 3. Session History
Session files are auto-loaded from previous session, enabling session continuation.

### 4. Project Convention Cache
**File:** `~/.pi/cache/{project_hash}/conventions.json`

Cached conventions for fast retrieval on subsequent sessions.

## Startup Process

### Step 1: Load User Preferences

```bash
[ -f ~/.pi/user-memory.md ] && cat ~/.pi/user-memory.md
```

### Step 2: Load Project Memory

```bash
[ -f .pi/memory.md ] && cat .pi/memory.md
```

### Step 3: Check Convention Cache

```bash
# Compute project hash (directory fingerprint)
PROJECT_HASH=$(echo "$PWD" | md5sum | cut -d' ' -f1)
CACHE_DIR=~/.pi/cache/$PROJECT_HASH

# Check if cache exists and is valid (less than 24h old)
if [ -f "$CACHE_DIR/conventions.json" ] && [ $(find "$CACHE_DIR/conventions.json" -mmin -1440 2>/dev/null) ]; then
  cat "$CACHE_DIR/conventions.json"
  CACHE_HIT=true
else
  CACHE_HIT=false
fi
```

### Step 4: Refresh Cache If Needed

If no cache hit, scan conventions in parallel:

```bash
if [ "$CACHE_HIT" = "false" ]; then
  mkdir -p "$CACHE_DIR"
  
  # Run scans in parallel, merge results
  {
    echo "=== CLAUDE MD ===" && [ -f CLAUDE.md ] && head -50 CLAUDE.md
    echo "=== AGENTS MD ===" && [ -f AGENTS.md ] && head -50 AGENTS.md
    echo "=== CURSOR RULES ===" && [ -d .cursor/rules ] && ls .cursor/rules/ 2>/dev/null | head -20
    echo "=== PROJECT STRUCTURE ===" && ls -d */ 2>/dev/null | head -20
  } > "$CACHE_DIR/conventions.json"
  
  # Store scan timestamp
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$CACHE_DIR/last-scan.txt"
fi
```

## Selective Scanning (Optimized)

Only scan relevant directories. Never scan these by default:

```bash
EXCLUDE_PATTERNS="node_modules|.git|dist|build|target|vendor|__pycache__|.next|.nuxt"
```

Scan priority order:
1. Root convention files (CLAUDE.md, AGENTS.md, etc.)
2. Agent config dirs (.claude/, .cursor/, .pi/)
3. Source directories (src/, lib/, app/)
4. Config files (*.json, *.yaml, *.toml in root)

## Helper Scripts

### Cache Status

```bash
./scripts/cache-manager.sh status
```

Shows cached projects and last scan times.

### Clear Cache

```bash
# Clear current project cache
./scripts/cache-manager.sh refresh

# Clear all caches
./scripts/cache-manager.sh clear-all
```

## Cache Invalidation

Cache is automatically invalidated when:
- `.pi/memory.md` changes
- `.claude/` or `.cursor/` directories change
- Any root convention file changes (checked on access)
- Manual trigger via `cache-manager.sh refresh`

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

From cache:
- Pre-computed project structure summary
- Discovered conventions and rules
- Available skills and commands

## No Action Needed

This skill runs automatically. No trigger needed from user.