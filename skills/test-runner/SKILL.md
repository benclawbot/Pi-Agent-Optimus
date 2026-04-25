---
name: test-runner
description: Run tests on relevant file changes. Use when "run tests", "test this", "test file", "execute tests", or watching files for changes. ALSO invoke MANDATORILY after completing any code change — before claiming done or finishing a task, run the relevant tests and confirm they pass.
---

# Test Runner

Run relevant tests when files change. Map changed files to their test files and execute.

## Test File Patterns

Common test file patterns to search for:

| Framework | Pattern |
|-----------|---------|
| Jest | `*.test.ts`, `*.spec.ts`, `**/__tests__/**/*.ts` |
| Vitest | `*.test.ts`, `*.spec.ts` |
| Python pytest | `test_*.py`, `*_test.py` |
| Go | `*_test.go` |
| Rust | `*_test.rs` |

## How to Find Test Files

### 1. Same Directory Match

Tests often live next to the code they test:
```
src/utils/format.ts → src/utils/format.test.ts
```

### 2. Test Directory

Tests may be in a separate test directory:
```
src/utils/format.ts → tests/utils/format.test.ts
src/utils/format.ts → test/utils/format.test.ts
src/utils/format.ts → __tests__/utils/format.test.ts
```

### 3. Find by Pattern

Search for test files matching the source filename:
```bash
# Find test files with same name
find . -name "*.test.ts" -o -name "*.spec.ts" | grep -i "format"
```

## Running Tests

### Single File

Run tests for a specific file:
```bash
# npm test with file
npm test -- src/utils/format.test.ts

# vitest
npx vitest run src/utils/format.test.ts

# pytest
pytest tests/test_format.py

# go
go test ./... -run TestFormat
```

### Directory

Run all tests in a directory:
```bash
npm test -- src/utils/
npx vitest run src/utils/
pytest tests/unit/
go test ./internal/...
```

### All Tests

Run full test suite when needed:
```bash
npm test
npx vitest run
pytest
go test ./...
```

## Watch Mode

For continuous testing during development:
```bash
npx vitest src/utils/format.ts --watch
npm test -- --watch
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Tests failed |
| 2 | Test runner error (syntax, misconfiguration) |

Show the user the output and any failures.

## Example

```
# User says "run tests for src/api/user.ts"

1. Find test files:
   - src/api/user.test.ts (same directory)
   - tests/api/user.test.ts (test directory)

2. Run the tests:
   npx vitest run src/api/user.test.ts

3. Report results:
   - 15 tests passed
   - 2 failed (details in output)
```