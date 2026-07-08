---
name: verify-done
description: 'Pre-commit verification ritual. Use before claiming any code change is done, before closing any todo, and before any "fixed" / "shipped" / "ready" claim. The 5-step gate that catches the most common agent failure mode: declaring victory without running the test.'
---

# verify-done

The 5-step verification gate. Run ALL of them in order. If any step fails, the change is **not done** — go back, fix, re-run the gate.

## When to invoke

MANDATORY before:
- Closing a todo as done
- Saying "fixed", "shipped", "ready", "works"
- Marking a file edit complete
- Ending a multi-step implementation turn

## The 5-step gate

Before step 1, re-read the request and make a requirements ledger: requested outcomes, constraints, expected artifacts, and the evidence that will prove each one.

### 1. Did I run the change?

If the change is a script, command, or test — **run it**. Show the exit code and last 20 lines of output. If you can't run it, say so explicitly.

```bash
# example
node dist/index.js --version
# exit: 0, output: "v1.2.3"  ← good
# exit: 1, output: "Error: ..."  ← NOT done
```

### 2. Did I run the project's test suite (if it has one)?

```bash
npm test 2>&1 | tail -40
# or: pytest, cargo test, go test, etc.
```

If the project has no tests, write one. A new function without a test is not done.

### 3. Did the diff match my intent?

```bash
git diff --stat
```

Read every file in the diff. Confirm the change does what you said it would. If you changed files you didn't mention, say so.

### 4. Are there artifacts to clean up?

Per the AGENTS.md cleanup section:
- Console.log / print statements added for debugging
- Commented-out test code
- Hardcoded test values
- Disabled tests still disabled

If yes, remove them before claiming done.

### 5. Self-audit

In ONE short paragraph, state:
- What I changed
- What test/command I ran to verify
- The exit code / outcome
- Any caveat the user should know

Before passing the gate:
- Re-check every item in the requirements ledger
- Verify requested artifacts exist at the expected paths and open, parse, or run as appropriate
- Prefer runtime or test evidence over source inspection, documentation, or memory
- Remember that absence of evidence is not evidence of absence

If you cannot fill in all four fields, you have not verified.

## Anti-patterns

❌ "I made the change, it should work now" — should? Did you run it?
❌ "Tests passed" without showing the output
❌ "Fixed in a previous turn" without re-running
❌ "The change is small so it doesn't need verification"
❌ Closing todos before running the gate

## When something fails

The change is **not done**. Three options:

1. **Fix it** — debug, re-run, re-verify
2. **Roll it back** — `git checkout -- <file>` if the change made things worse
3. **Tell the user** — be honest about what didn't work, what you tried, and what's left

Treat the failure as evidence. Change the hypothesis or method before retrying; do not repeat the same failed action unchanged.

Never close a todo as done while the verification gate is red.

## Output format

When you invoke this skill, end your turn with a one-line verdict:

```
verify-done: PASS (5/5) — npm test 0 failures, git diff clean, 0 artifacts
```

or

```
verify-done: FAIL at step 3 — diff includes unintended file changes, reverting
```

The user should never have to ask "did you actually test this?"
