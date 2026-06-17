# Self-Improve Ledger

Append-only log of auto-applied guardrail fixes. Each entry is git-committed; rollback with `git revert <sha>`.

---

## 2026-06-17 — session 019ed630-b0bd-7db7-9de7-9281eb584415

**Tier**: B (user-approved)
**Cluster**: Slash command loaded skill content, agent treated as informational not as invocation
**Confidence**: 0.85
**File**: `~/.pi/agent/skills/self-improve/SKILL.md`
**Diff**:
```diff
@@ Hard limits @@
 - **No fixes outside the harness**: ...
+- **Invocation contract**: when this skill content appears in your context
+  via slash command (`/self-improve` or any short form the user typed that
+  resolved to this skill), the user has EXPLICITLY invoked it. Execute all
+  phases immediately. Do not ask "do you want me to run this?" — the slash
+  command IS the request. `disable-model-invocation: true` means "don't
+  auto-load on context match", not "ignore slash command invocations".
```

**Verify**: type `/self-improve` → agent should run Phase A immediately, not ask "do you want me to run this?"
**Reason**: User typed `/self-improve`, skill loaded, agent responded "say the word if you want me to run it" — wrong, the slash command is the word.