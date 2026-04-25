---
name: auto-test
description: Run tests automatically based on file changes, show test results for changed code. Use when "run tests", "test this file", "test changes", "which tests cover this", "test pattern", or running test suite.
allowed-tools: Read,Bash,execute_command
---

# Auto Test

Runs relevant tests based on changed files, integrates with skill evolution.

## Core Concept

When code changes, run the tests that cover those changes — not the full suite.

## Usage

### Test a Single File

```bash
python ~/.pi/agent/skills/auto-test/scripts/test-loop.py run <file>
```

Finds related tests and runs them.

### Test Changes (Git Diff)

```bash
python ~/.pi/agent/skills/auto-test/scripts/test-loop.py changed
```

Gets the current git diff, finds affected files, runs relevant tests.

### Watch Mode

```bash
python ~/.pi/agent/skills/auto-test/scripts/test-loop.py watch <file>
```

Runs tests when the file changes (requires test-runner skill).

## Test Discovery Patterns

The script finds tests using these patterns:

| Pattern | Example |
|---------|--------|
| Same directory, `*.test.ts` | `src/utils.ts` → `src/utils.test.ts` |
| `__tests__/` directory | `src/utils.ts` → `src/__tests__/utils.ts` |
| `tests/` directory | `src/utils.ts` → `tests/utils.ts` |
| `spec/` directory | `src/utils.ts` → `src/spec/utils.ts` |

## Output Format

```json
{
  "file": "src/utils.ts",
  "tests": ["src/utils.test.ts"],
  "results": [
    {
      "testFile": "src/utils.test.ts",
      "passed": true,
      "duration": 120
    }
  ],
  "summary": {
    "total": 1,
    "passed": 1,
    "failed": 0
  }
}
```

## Integration Points

### With test-runner Skill
- Uses `test-runner` to execute tests
- Follows test configuration from project

### With skill-evolution Skill
- Logs test patterns discovered
- Captures which tests catch which bugs
- Records flaky test patterns

### With project-health Skill
- Reports test freshness
- Links to CI test results

## File Structure

```
auto-test/
├── SKILL.md
├── scripts/
│   └── test-loop.py
└── references/
    └── testing-patterns.md
```

## Test Confidence

| Confidence | Meaning |
|-----------|---------|
| High | Same file tests (e.g., `utils.ts` → `utils.test.ts`) |
| Medium | Same module tests (e.g., `utils.ts` → `math.test.ts` if both in `utils/`) |
| Low | Generic test suite |

## Integration

To capture learning:
1. After test run, note which tests caught the bug
2. Say "learn from this - test X catches Y type of bug"
3. This gets stored in skill-memory.json

## Reference

Read `references/testing-patterns.md` for more on test discovery and patterns.
