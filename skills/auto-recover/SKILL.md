---
name: auto-recover
description: Analyze errors and suggest/apply fixes. Use when "fix this error", "what went wrong", "error recovery", or "diagnose failure".
allowed-tools: Read,Bash,write,edit
---

# Auto Recover

Analyze errors and automate recovery for common issues.

## Core Concept

When something breaks, diagnose and fix — don't leave it for manual debugging.

## Usage

### Diagnose Error

```bash
python scripts/recover.py diagnose "error message here"
```

### Analyze Recent Failure

```bash
python scripts/recover.py analyze --file src/utils.ts
```

### Apply Suggested Fix

```bash
python scripts/recover.py fix --issue missing-import
```

### Common Error Patterns

| Error | Pattern | Fix |
|-------|---------|-----|
| Missing import | `Cannot find module` | Add import statement |
| Syntax error | `Unexpected token` | Fix syntax |
| Type error | `Type 'X' is not assignable` | Add type annotation |
| Missing dependency | `Cannot find package` | Add to package.json |
| Circular import | `Circular dependency` | Restructure imports |

## How It Works

1. Parse error message
2. Match against known patterns
3. Extract relevant code context
4. Generate fix suggestion
5. Apply if confident

## Confidence Levels

| Level | Action |
|-------|--------|
| High (90%+) | Auto-apply fix |
| Medium (60-90%) | Suggest, ask confirmation |
| Low (<60%) | Describe issue, suggest investigation |

## State

Recovery attempts logged to `~/.pi/recovery-log.json`:

```json
{
  "attempts": [
    {
      "id": "rec-001",
      "time": "2026-04-25T10:00:00Z",
      "error": "Cannot find module './utils'",
      "fix": "Added import to src/index.ts",
      "status": "success"
    }
  ]
}
```

## Integration

- With `skill-evolution` to learn fix patterns
- With `test-runner` to verify fix
- With `file-watcher` to detect regressions

## File Structure

```
auto-recover/
├── SKILL.md
└── scripts/
    └── recover.py
```

## Limitations

- Can't fix logic errors
- Complex refactoring needs manual review
- Security issues always need human review
