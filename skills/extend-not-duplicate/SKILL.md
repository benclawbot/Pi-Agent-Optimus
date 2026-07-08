---
name: extend-not-duplicate
description: Before building a plugin, extension, slash command, or hook for any platform with a registry, scan the registry for existing implementations of the same surface. Extend or complement — never silently duplicate. Catches the "I shipped a parallel X that shadowed the user's real X" failure mode. Trigger on "build an extension", "add a slash command", "add a plugin", "implement X for Y", "write a hook for Z", or any time you are about to add code to a system whose loader discovers files/registrations by name. Especially load this before writing an extension for a system the user already runs (VSCode, pi, Vim, Obsidian, Home Assistant, GitHub Actions, etc.) — their existing install may already have what you're about to build.
---

# Extend, Don't Duplicate

The failure mode: an agent is asked to add capability X to platform Y. The agent reads the docs, builds a clean implementation of X, tests it, and ships it. The user's real session then loads BOTH the new X and the existing X — silently shadowed commands, conflicting tool names, double-fired hooks, double-persisted state. The agent never noticed because it didn't scan Y's actual registry.

## Step 1: Inventory the Target Registry

Before writing any code, enumerate what already exists at the destination:

| Platform | Discovery command |
|----------|-------------------|
| pi (`~/.pi/agent/extensions/`) | `ls ~/.pi/agent/extensions/`, `ls ~/.pi/agent/skills/`, `ls ~/.pi/agent/prompts*/` |
| pi (runtime registry) | spawn `pi --mode rpc --no-session`, send `get_commands`, inspect names + paths |
| VSCode | `~/.vscode/extensions/`, workspace `.vscode/extensions.json` |
| Vim/Neovim | `:scriptnames`, `:Lazy`, `:PlugStatus` |
| Obsidian | `ls <vault>/.obsidian/plugins/` |
| GitHub Actions | grep `.github/workflows/` |
| Home Assistant | `~/.homeassistant/custom_components/` |
| Generic | look for the platform's "extensions", "plugins", "tools", "components", "skills", "hooks", "macros", or "commands" directory |

Do this BEFORE writing. The 30 seconds saves a refactor.

## Step 2: Read the Existing Implementation

For each match that overlaps with what you were asked to build, read it fully. Look for:

- **Surface conflicts** — same command name, same tool name, same slash trigger
- **Hook overlap** — same event hooked twice
- **State overlap** — two writers to the same file/db/key
- **Complementary functionality** — half of what you wanted to build already exists, the other half is missing

## Step 3: Pick One of Three Outcomes

| Scenario | Move |
|----------|------|
| No overlap | Build as planned |
| Existing is the full ask | Tell the user it already exists. Don't build a parallel one. |
| Existing is partial / differs from your spec | **Extend or complement.** Wire into the same state file, hook the same lifecycle event, call the same tools. Don't write a parallel state file. |
| Surface conflict unavoidable | Use a distinctly named command/hook the user can disambiguate, OR ask the user which to keep. |

## Step 4: Verify After Build

Add a check to your e2e that the registry doesn't show double-registration:

```js
// pi example
const cmds = await getCommands();
const goalCount = cmds.filter(c => c.name === "goal").length;
assert(goalCount === 1, `exactly one /goal (got ${goalCount})`);
```

For pi specifically, `get_commands` returns `sourceInfo.path` — filter by your extension's path to confirm no duplicate, then count same-named commands to confirm no shadow.

## Real-World Example: Hermes `/goal` Parity for pi

User asked for `/goal` parity. I built `hermes-goal/` with `/goal` + `/subgoal` + state file. E2E against real pi showed `goal:1` (mine) and `goal:2` (existing `~/.pi/agent/extensions/goal/index.ts`) — name collision, would have shadowed the user's existing tool, blocked the existing `create_goal` LLM tool from being called because the slash command intercepted `/goal <text>` before the LLM could see it as a `create_goal` invocation.

Correct move: read `~/.pi/agent/extensions/goal/index.ts` first, see that it owns the goal lifecycle + LLM-callable tools + `/goal` slash + `goal.json` persistence, and build `goal-loop/` as a complementary extension that hooks `turn_end`, reads the same `goal.json`, and sends the continuation prompt. No duplicate commands, no duplicate state, no shadowing. Three layers of e2e pass on the second attempt.

## Heuristic

If your planned extension's slash command name, tool name, hook target, or persistence path would collide with an existing extension's, you have two choices: rebuild as complementary, or stop and ask. Silently shipping the collision is the failure mode this skill prevents.

## When NOT to Apply

- Truly greenfield targets with no extension system
- Libraries / SDKs where "extensions" don't exist as runtime-discovered artifacts (use package conventions instead)
- User explicitly says "build it as a standalone, don't reuse X"
