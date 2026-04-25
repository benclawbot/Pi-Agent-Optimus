---
name: ci-watcher
description: Monitor CI runs and alert on failures. Use when "check CI", "CI status", "watch CI", "build status", "pipeline monitor", or "notify on CI failure".
allowed-tools: Read,Bash,execute_command
---

# CI Watcher

Monitor CI pipelines and alert on failures.

## Core Concept

Don't wait for someone to notice CI is red — get notified automatically.

## Usage

### Check CI Status

```bash
python scripts/ci-monitor.py status
```

### Watch Mode (Poll)

```bash
python scripts/ci-monitor.py watch --interval 60
```

### Get Recent Failures

```bash
python scripts/ci-monitor.py failures --limit 10
```

### Watch for Specific Branch

```bash
python scripts/ci-monitor.py watch --branch main
```

## Output Format

```json
{
  "run": {
    "id": "1234567890",
    "status": "completed",
    "conclusion": "failure",
    "branch": "main",
    "commit": "abc1234",
    "message": "2 tests failed"
  },
  "alert": true
}
```

## Alert Integration

When failure detected:
1. Log to `~/.pi/ci-alerts.json`
2. Show notification (if supported)
3. Store failure for skill-evolution

## State

Failure history stored in `~/.pi/ci-alerts.json`:

```json
{
  "alerts": [
    {
      "id": "run-123",
      "time": "2026-04-25T10:00:00Z",
      "branch": "main",
      "commit": "abc123",
      "failure": "2 tests failed",
      "acknowledged": false
    }
  ]
}
```

## Polling Interval

| Interval | Use Case |
|----------|----------|
| 30s | Critical projects |
| 60s | Normal monitoring |
| 300s | Infrequent checks |

## File Structure

```
ci-watcher/
├── SKILL.md
└── scripts/
    └── ci-monitor.py
```

## Reference

Use `gh run list` and `gh run view` commands. See `project-health` skill for GitHub CLI patterns.
