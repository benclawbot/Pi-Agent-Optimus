---
name: project-health
description: Monitor project health status including CI runs, test freshness, dependency updates, and dev server status. Use when "project health", "check CI", "is everything green", "outdated deps", "health check", or "test freshness".
allowed-tools: Read,Bash,execute_command
---

# Project Health Monitor

Tracks the health of a project across multiple dimensions.

## Checks

| Check | Command | Health Indicator |
|-------|---------|------------------|
| CI Status | `gh run list --limit 5` | Green/yellow/red |
| Test Freshness | Check last test run | Stale if > 24h |
| Outdated Dependencies | `npm outdated` / `cargo outdated` | Count of outdated |
| Running Dev Servers | Process list | Active if running |

## Usage

### Quick Health Check

```bash
python ~/.pi/agent/skills/project-health/scripts/check-health.py
```

Output format:
```json
{
  "ci": {
    "status": "passing",
    "lastRun": "2026-04-25T10:00:00Z",
    "runs": [...]
  },
  "tests": {
    "stale": false,
    "lastRun": "2026-04-25T09:30:00Z"
  },
  "deps": {
    "outdated": 3,
    "major": 1
  },
  "servers": {
    "running": ["5173", "3000"]
  }
}
```

### CI Status Only

```bash
gh run list --limit 5 --json status,conclusion,name,startedAt
```

### Dependency Check

```bash
# npm
npm outdated

# yarn
yarn outdated

# pnpm
pnpm outdated

# Rust
cargo outdated
```

## Health Indicators

| Status | Meaning | Action |
|--------|---------|--------|
| 🟢 Green | All checks passing | Good to ship |
| 🟡 Yellow | Warnings or stale data | Investigate |
| 🔴 Red | Failures or blocking issues | Fix before proceeding |

## Integration

This skill integrates with:
- `system-awareness` for server status
- `skill-evolution` to capture health patterns
- `github` skill for CI interaction

## File Structure

```
project-health/
├── SKILL.md
├── scripts/
│   └── check-health.py
└── references/
    └── ci-status.md
```

## Reference Files

Read `references/ci-status.md` for GitHub CLI patterns.
