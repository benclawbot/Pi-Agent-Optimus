# Slash command = explicit invocation

**Triggered by**: User typing a slash command that resolves to a skill (`/self-improve`, etc.)
**Prevents**: Agent acknowledging "skill loaded, want me to run it?" when the user already invoked it explicitly.

## Background

Pi's skill frontmatter has two relevant flags:

- `disable-model-invocation: true` — means "don't auto-load this skill when context matches"
- Slash command invocation — means "the user explicitly loaded this skill"

These are orthogonal. A skill with `disable-model-invocation: true` is still loadable by the user via its slash command. When loaded that way, the agent MUST treat it as an explicit request to execute the skill's procedure.

## Verify

Run: type `/self-improve` in pi
Expect: agent immediately begins Phase A (gathering errors), without asking "do you want me to run this?"

Failure mode: agent says something like "Skill loaded. `disable-model-invocation: true` — only runs on explicit `/self-improve`, not auto. Say the word if you want me to run it."

## Why this guardrail

Without it, the user has to type the slash command AND then issue a follow-up instruction. Doubles the friction. Worse, the response sounds like the slash command wasn't recognized — the user thinks the command failed, when it actually succeeded.

## Source rule

Lives in `~/.pi/agent/skills/self-improve/SKILL.md` under "Hard limits" as the "Invocation contract" bullet.