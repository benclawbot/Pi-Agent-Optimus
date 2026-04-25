# Testing Patterns

## Test Discovery

### File Location Patterns

| Pattern | Example |
|---------|---------|
| Same file, `.test` suffix | `src/utils.ts` → `src/utils.test.ts` |
| Same file, `.spec` suffix | `src/utils.ts` → `src/utils.spec.ts` |
| `__tests__/` sibling | `src/utils.ts` → `src/__tests__/utils.ts` |
| `tests/` root | `src/utils.ts` → `tests/utils.ts` |
| `spec/` sibling | `src/utils.ts` → `src/spec/utils.ts` |

### Confidence Levels

| Level | When | Action |
|-------|------|--------|
| High | Same file tests | Run these first |
| Medium | Same module tests | Run if high-level tests pass |
| Low | Generic suite | Run for final verification |

## Test Runners

### Vitest
```bash
npx vitest run src/file.test.ts
npx vitest related src/file.ts  # Run related tests
```

### Jest
```bash
npx jest src/file.test.ts
npx jest --watch src/file.ts   # Watch mode
```

### Mocha
```bash
npx mocha "src/**/*.test.ts"
```

### Playwright
```bash
npx playwright test
npx playwright test src/file.spec.ts
```

## Rust Testing

```bash
cargo test
cargo test <test-name>
cargo test --lib           # Library tests only
cargo test --doc           # Doc tests only
```

## Integration with Skill Evolution

### What to Log

After a test run, note:

1. **What was tested** — file, test count
2. **What passed/failed** — results
3. **What the failure revealed** — gap in coverage?

### Example Log Entry
```json
{
  "skill": "auto-test",
  "pattern": "High-confidence test discovery via .test.ts suffix",
  "context": "Found 3 tests for utils.ts in same directory",
  "success": true
}
```

### Captured Anti-Patterns
```json
{
  "skill": "auto-test",
  "gap": "Test files not named consistently (.spec vs .test)",
  "suggestion": "Standardize to .test.ts pattern",
  "priority": "medium"
}
```

## When to Run What

| Change | Test Scope |
|--------|------------|
| Single file | Same-file tests only |
| Shared module | Module + dependent tests |
| Config change | Full suite |
| Dependency bump | Full suite |
| Hotfix | Same-file + integration |

## Test State Tracking

Store test state in `~/.pi/test-state.json`:

```json
{
  "lastRun": "2026-04-25T10:00:00Z",
  "duration": 45,
  "passed": 142,
  "failed": 0,
  "files": ["src/**/*.test.ts"]
}
```

Update after each test run to track freshness.
