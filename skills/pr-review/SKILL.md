---
name: pr-review
description: Structured PR review with files changed, risks, questions, and approval. Use when "review PR", "review pull request", "check PR", or "approve PR".
---

# PR Review

Provide a structured review of a pull request.

## Review Format

### Summary
Brief description of what the PR does.

### Files Changed
List files modified with a one-line description of each change.

### Risks
Identify potential issues:
- Breaking changes
- Security concerns
- Performance impacts
- Migration complexity

### Questions
Open questions or items needing clarification.

### Recommendations
Suggestions for improvement (optional).

### Approval

```
Status: [APPROVED / CHANGES REQUESTED / COMMENT]
```

## Steps

### 1. Get PR Info

```bash
# View files changed
gh pr view <number> --json files,title,body,state

# Or using gh pr diff
gh pr diff <number>
```

### 2. Analyze Changes

- Read the code diff
- Check for test coverage
- Verify no secrets committed
- Look for breaking changes
- Check documentation updates

### 3. Identify Risks

Common risk areas:
| Risk Type | What to Look For |
|-----------|------------------|
| Security | Auth bypass, injection, exposed secrets |
| Breaking | API changes, removed fields, renamed configs |
| Performance | N+1 queries, missing indexes, unbounded loops |
| Complexity | Deep nesting, unclear logic, missing abstractions |

### 4. Write Review

Use the format above. Be specific with line references.

## Example

```
## PR #42: Add user authentication

### Summary
Implements JWT-based authentication with refresh tokens.

### Files Changed
- `src/auth/login.ts` — Login endpoint with JWT generation
- `src/auth/middleware.ts` — Auth guard for protected routes
- `src/auth/refresh.ts` — Token refresh handler
- `tests/auth.test.ts` — Unit tests for auth flow

### Risks
- **Medium**: Token expiration hardcoded to 1h — should be configurable
- **Low**: No rate limiting on login endpoint

### Questions
- Should refresh tokens be stored in DB or just validated?

### Approval
Status: CHANGES REQUESTED

Add configurable token expiration.
```