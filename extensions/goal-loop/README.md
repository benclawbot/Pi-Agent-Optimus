# goal-loop

The Ralph-loop driver for the existing pi `goal` capability.

## What it adds

The `~/.pi/agent/extensions/goal/index.ts` extension gives the LLM the
`create_goal` / `get_goal` / `update_goal` tools and a `/goal` slash
command. It tracks goal state in `~/.pi/agent/goal.json` and counts
turns via an `agent_end` hook. **It does not drive the loop.**

This extension fills the gap: after every turn, an auxiliary "judge"
model is asked whether the active goal is satisfied. If not, and the
turn budget isn't exhausted, the continuation prompt is fed back to
the agent as the next user message. The loop ends when:

- judge says done → goal marked complete
- judge says done because blocked → goal marked blocked
- turn budget exhausted → goal marked blocked with reason
- 3 consecutive judge parse failures → goal marked blocked with hint
- real user message preempts (queued input wins)

## Mirror

Line-by-line port of Hermes Agent's `/goal` Ralph loop. Source:
`hermes_cli/goals.py` (GoalManager, judge_goal) +
`hermes_cli/cli.py:_maybe_continue_goal_after_turn`. Differences are
purely plumbing: pi's hook surface (`turn_end`), notification surface
(`ctx.ui.notify`), and message-send API (`pi.sendUserMessage`).

## Configuration

The judge is a separate LLM call. Configure via env vars (the loop
no-ops with a one-time warning if any are missing):

| Env var | Default | Notes |
|---------|---------|-------|
| `GOAL_LOOP_JUDGE_URL` | — | base URL. Anthropic format auto-detected when URL contains `/anthropic` |
| `GOAL_LOOP_JUDGE_MODEL` | — | model id, e.g. `MiniMax/M2.7`, `gpt-4o-mini` |
| `GOAL_LOOP_JUDGE_KEY` | `OPENAI_API_KEY` | API key (also `ANTHROPIC_API_KEY` works for Anthropic) |
| `GOAL_LOOP_JUDGE_FORMAT` | auto | `openai` \| `anthropic`. Auto = detect from URL (`/anthropic` → Anthropic). |
| `GOAL_LOOP_JUDGE_TIMEOUT_MS` | `30000` | judge call timeout |
| `GOAL_LOOP_JUDGE_MAX_TOKENS` | `4096` | judge response cap |
| `GOAL_LOOP_MAX_TURNS` | `20` | per-goal turn budget |

The judge prompt is fixed: strict JSON `{"done": bool, "reason": str}`,
fail-OPEN on transport errors, parse-failure auto-pause after 3.

## Provider Examples

**MiniMax (Anthropic-compatible)** — direct, no third-party:
```
GOAL_LOOP_JUDGE_URL=https://api.minimax.io/anthropic
GOAL_LOOP_JUDGE_MODEL=MiniMax/M2.7
GOAL_LOOP_JUDGE_KEY=<your-key>
```

**OpenAI**:
```
GOAL_LOOP_JUDGE_URL=https://api.openai.com/v1
GOAL_LOOP_JUDGE_MODEL=gpt-4o-mini
GOAL_LOOP_JUDGE_KEY=<your-key>
```

**OpenRouter** (OpenAI-compat):
```
GOAL_LOOP_JUDGE_URL=https://openrouter.ai/api/v1
GOAL_LOOP_JUDGE_MODEL=google/gemini-3-flash-preview
GOAL_LOOP_JUDGE_KEY=<your-key>
```

**NVIDIA** (OpenAI-compat, e.g. third-party MiniMax mirror):
```
GOAL_LOOP_JUDGE_URL=https://integrate.api.nvidia.com/v1
GOAL_LOOP_JUDGE_MODEL=minimaxai/minimax-m2.7
GOAL_LOOP_JUDGE_KEY=<your-nvapi-key>
```

When using `setx` on Windows, restart your shell (or pi) for the env vars to be visible to the judge at extension-load time.

## Testing

```bash
bun test.mjs        # 16 judge-parser assertions
bun e2e-test.mjs    # 7 RPC assertions (real pi --mode rpc)
```

## Files

- `index.ts` — extension entry; `turn_end` hook
- `judge.ts` — auxiliary LLM call (OpenAI + Anthropic formats) + strict-JSON parser
- `test.mjs` — mocked unit tests for judge
- `e2e-test.mjs` — real `pi --mode rpc` invocation
