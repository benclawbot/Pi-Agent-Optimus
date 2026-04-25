---
name: file-watcher
description: Watch files for changes and trigger actions. Use when "watch files", "auto-test on save", "run on change", "file watcher", or "monitor changes".
allowed-tools: Read,Bash,execute_command
---

# File Watcher

Watch files for changes and trigger automated actions.

## Core Concept

When you save a file, automatically run the related tests — no manual trigger needed.

## Usage

### Watch a File

```bash
python scripts/watch.py run --file src/utils.ts
```

### Watch a Directory

```bash
python scripts/watch.py run --dir src
```

### One-shot Check (No Watch)

```bash
python scripts/watch.py check --file src/utils.ts
```

### Stop Watching

```bash
python scripts/watch.py stop
```

## How It Works

1. File changes detected
2. Find related tests (via auto-test skill)
3. Run tests
4. Report results
5. Log to skill-memory.json if tests failed

## Configuration

Watch config stored in `~/.pi/watch-config.json`:

```json
{
  "watched": [
    {
      "path": "src/**/*.ts",
      "testPattern": "*.test.ts",
      "exclude": ["*.d.ts", "node_modules/**"]
    }
  ],
  "debounceMs": 500,
  "autoTest": true
}
```

## Debouncing

Changes are debounced (default: 500ms) to avoid triggering on rapid saves.

## State

Process runs in background, tracked via CMux or stored PID.

## File Structure

```
file-watcher/
├── SKILL.md
└── scripts/
    └── watch.py
```
