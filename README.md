# Pi Agent Optimus

Personal configuration for [pi-coding-agent](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (`@earendil-works/pi-coding-agent`, currently 0.80.x). Ships agents, skills, extensions, hooks, MCP servers, behavioral tests, and a `setup.ps1` installer that merges into `~/.pi/agent/` without overwriting user secrets.

## Setup

```bash
git clone https://github.com/benclawbot/Pi-Agent-Optimus.git
cd Pi-Agent-Optimus
./setup.sh              # macOS / Linux
```

On Windows:

```powershell
.\setup.ps1
```

The installer:

1. Copies `agents/`, `extensions/`, `skills/`, `templates/`, `scripts/`, `project-template/`, and `tests/` into `~/.pi/agent/` (additive — local-only entries are not deleted).
2. Merges `settings.json` using array-union semantics: arrays dedupe and combine, scalars take the local value, secrets are never overwritten.
3. Runs `npm test` from `~/.pi/agent/` to confirm every configured extension resolves on disk and every skill has valid frontmatter.
4. Calls `pi install <source>` for each entry in `settings.json.packages[]`.

Restart pi (or run `/reload`) to pick up the new harness.

## API keys

`models.json` and `auth.json` are environment-variable driven. Set these in your shell profile **or** via Windows User environment (`[Environment]::SetEnvironmentVariable`):

```powershell
[Environment]::SetEnvironmentVariable("MINIMAX_API_KEY", "<key>", "User")
[Environment]::SetEnvironmentVariable("NVIDIA_API_KEY",  "<key>", "User")
```

Pi reads `MINIMAX_API_KEY` and `NVIDIA_API_KEY` from the process env at startup. `~/.pi/agent/models.json` holds non-secret metadata (baseUrl, model ids, contextWindow, cost) — never the keys themselves.

`auth.json` is git-ignored; if you need a fallback key for an alternate provider, store it there locally and it will be picked up before the env var.

## What's Included

### Agents (8)

Markdown-defined subagents, each pinned to a model and toolset via frontmatter. Spawned with `/subagent <name> <task>` or the `subagent` tool.

| Agent         | Model       | Tools                           | Purpose                              |
|---------------|-------------|----------------------------------|--------------------------------------|
| `spec`        | MiniMax M2.7 | read, bash, grep                 | Interactive WHAT clarifier           |
| `planner`     | MiniMax M2.7 | read, bash, grep                 | Interactive HOW planner              |
| `scout`       | MiniMax M2.5 | read, bash, glob, grep           | Fast codebase reconnaissance         |
| `worker`      | MiniMax M2.7 | read, bash, write, edit, grep, todo | Implements todos, makes commits      |
| `reviewer`    | MiniMax M2.7 | read, bash, grep                 | Code quality + security review       |
| `researcher`  | MiniMax M2.7 | read, bash, search, fetch        | Deep research + web discovery        |
| `fullstack`   | MiniMax M2.5 | read, bash, write, edit          | Web / fullstack specialist           |
| `autoresearch`| MiniMax M2.7 | read, bash, grep, write          | Multi-hour research loop             |

Frontmatter shape:

```yaml
---
name: <id>
description: <one-liner>
tools: [read, bash, grep]
model: MiniMax/M2.7
thinking: off | low | medium | high
spawning: true | false
auto-exit: true | false
---
```

### Extensions (30 active + 3 archived)

The loader activates every entry in `settings.json.extensions[]`. Extensions not listed are dormant on disk.

| Extension            | Status   | Purpose                                                            |
|----------------------|----------|--------------------------------------------------------------------|
| `btw`                | active   | Side-band steering without interrupting flow                      |
| `reload`             | active   | Hot-reload extensions, skills, prompts, themes                     |
| `todos`              | active   | Full TUI todo manager (`/todos`)                                   |
| `todo-panel`         | active   | Persistent above-editor todo progress widget                       |
| `telegram`           | active   | Telegram bot bridge — chat with pi from anywhere                   |
| `load-skill`         | active   | Load skill instructions on demand                                  |
| `subagent`           | active   | Restricted delegated pi process                                   |
| `fusion`             | active   | Parallel MiniMax M2.7 + M3 deliberation with M3 judge               |
| `repo-map`           | active   | Bounded repository map (tree-sitter + PageRank)                    |
| `long-task`          | active   | Persistent long-task checkpoints (Ralph-loop style)               |
| `cost`               | active   | Per-session token cost tracking                                   |
| `status`             | active   | `/status` dashboard — todos, dirty git, pending PRs, CI           |
| `execute-command`    | active   | `execute_command` tool — model self-invokes slash commands         |
| `commit-review`      | active   | Pre-commit review hook                                            |
| `auto-skill-suggest` | active   | Suggests skills to load on context match                           |
| `goal-loop`          | active   | Goal lifecycle tracking                                           |
| `session-notes`      | active   | Persists session notes                                            |
| `skill-auto-evolve`  | active   | Auto-evolves skill bodies from observed failures                   |
| `branch-cleanup`     | active   | Git branch cleanup                                                |
| `local-ollama`       | active   | Registers local Ollama provider (lazy, ECONNREFUSED-safe)          |
| `answer`             | active   | Structured multi-question answer capture                          |
| `branch-cleanup`     | active   | Git branch cleanup                                                |
| `caveman-default`    | active   | Default caveman-mode persona on session start                      |
| `goal`               | active   | Goal tracking (companion to `goal-loop`)                           |
| `cmux`               | active   | CMUX socket integration (only useful inside cmux)                  |
| `compact-tools`      | active   | One-liner summary renderers for built-in tools                     |
| `context-hotloader`  | active   | Hot-loads project context on session start                         |
| `pre-compact-snapshot` | active | Snapshot the session before compaction for forensics               |
| `_shared/`           | shared   | Reusable extension helpers (e.g. `pi-resolve.ts`)                  |
| `cmux.disabled/`     | archived | Legacy CMUX variant (preserved, not loaded — `.disabled/` suffix is a convention, not a loader signal) |
| `compact-tools.disabled/`     | archived | Legacy variant (not loaded) |
| `context-hotloader.disabled/` | archived | Legacy variant (not loaded) |

**Important:** the `.disabled/` suffix is a community convention for archiving old versions. The pi loader does **not** recognize it as a skip signal — it walks every directory. If you re-add a `.disabled` directory containing `index.ts` while a non-disabled variant also exists, you'll get tool-name conflicts on startup. Move `.disabled` dirs out of `~/.pi/agent/extensions/` (or delete them) before activating the live variant.

### Skills (38 lazy-loaded)

Each skill is a `SKILL.md` with YAML frontmatter. Loaded on demand by trigger phrase or slash command — the default model prompt doesn't list them.

**Productivity:** `startup`, `quick-ref`, `commit`, `verify-done`, `caveman`, `caveman-commit`, `caveman-help`, `caveman-review`, `todo-update`, `write-todos`, `compress`, `plan`, `pr-review`, `iterate-pr`

**Code intelligence:** `code-simplifier`, `learn-codebase`, `cmux`, `5-why`, `presentation-creator`, `frontend-design`

**Self-evolution:** `self-improve` (Phase A: errors-driven auto-apply, Phase B: general reflection), `skill-evolution`, `skill-creator`, `context-memory`, `auto-recover`, `system-awareness`, `project-health`

**Test & build:** `auto-test`, `ci-watcher`, `file-watcher`, `test-runner`, `db-introspect`, `scheduler`

**Git & repo:** `github`, `add-mcp-server`

**Research:** `deep-research`

The full list is in `settings.json.skills[]`. Additional skills from `~/.agents/skills/` are loaded automatically when that directory exists.

### Self-improve (Phase A / Phase B)

`skills/self-improve/SKILL.md` runs two phases, unified into one approval queue:

- **Phase A** (errors-driven, automated) — analyzes session errors and warnings, clusters them, judges preventability, and auto-applies up to 3 low-risk guardrail fixes (skill edits, AGENTS.md tweaks, hooks, memory writes). Hard cap: 3 auto-applied per invocation, 5 queued for review.
- **Phase B** (general reflection, ask-first) — broader retrospective on the session, asks for approval before queuing anything.

Both phases share the same approval queue. Cooldown: refuses to run twice in the same session unless the user explicitly invokes `/self-improve` again.

Auto-applied fixes are committed by the skill itself with an `improve-log.md` ledger entry per session. Roll back with `git revert <sha>`.

### Hooks

`PreToolUse` for `Bash` runs `rtk hook claude` to wrap every shell call. Add more hooks to `settings.json.hooks` for `PostToolUse` (e.g. `prettier --write $FILE` after `write|edit`), `SessionStart`, or `SessionEnd`.

### MCP servers

`~/.pi/agent/mcp.json` (git-ignored locally, example in `project-template/`) configures stdio and npm transports. Sample:

```json
{
  "mcpServers": {
    "filesystem":    { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "."] },
    "context-mode":  { "command": "context-mode" }
  }
}
```

Add your own servers there. The loader spawns them lazily on first tool call.

### Packages

`settings.json.packages[]` lists `npm:` and `git:` sources that the installer fetches via `pi install`. Examples in `settings.json`:

```json
"packages": [
  "npm:context-mode",
  "git:github.com/DietrichGebert/ponytail"
]
```

`ponytail` adds a status-bar badge showing the current ponytail rung (FULL / LITE / OFF) — visible as `🐴 ⚡ FULL` in the pi header.

---

## Behavioral Tests

`tests/harness.test.mjs` runs as part of `npm test` from `~/.pi/agent/`. Asserts:

- Every configured extension in `settings.json.extensions[]` resolves on disk
- Every skill has valid YAML frontmatter (`name`, `description`) with quoted colons
- The installer round-trips without overwriting user settings
- Sensitive files (`auth.json`, `trust.json`, `npm/`, `sessions/`) are in `.gitignore`
- `fusion` extension actually invokes parallel MiniMax panelists with an M3 judge

`tests/behavioral/` covers end-to-end flows for `fusion` and `subagent`. Add new behavioural specs there.

`tests/harness/utils.ts` provides helpers for mocking `ExtensionContext`.

---

## File Layout (after setup)

```
~/.pi/agent/
├── AGENTS.md                # compact base identity + Core Principles
├── settings.json            # merged defaults + local overrides
├── models.json              # non-secret provider metadata
├── auth.json                # (optional) fallback keys, git-ignored
├── mcp.json                 # MCP server configs, git-ignored
├── goal.json                # active goal state (auto-managed)
├── improve-log.md           # self-improve ledger (git-committed)
├── .pre-upgrade-backup-*    # upgrade-time snapshots (git-ignored)
├── agents/                  # 8 markdown subagents
├── skills/                  # 38 SKILL.md directories
├── extensions/              # 30 active + 3 archived (.disabled/)
│   └── _shared/             # shared helpers
├── scripts/                 # install-harness / install-packages / merge-settings / curate-skills
├── templates/               # prompt templates
├── project-template/        # canonical settings.json + package.json for new projects
└── tests/                   # harness.test.mjs + behavioural/*
```

---

## Token Optimization

- **Model split:** M2.5 for workers / scouts (fast), M2.7 for reviewers / planners (reasoning), M3 default for lead.
- **Lazy skills:** specialist skills remain available as commands but are hidden from the default model prompt.
- **Compaction:** 8 K reserve, 15 K keep (was 16 K / 20 K).
- **Retry:** 2 max (was 3).
- **Branch summary:** `doubleEscapeAction: "fork"` enables session forking at any message boundary — copies the transcript into a new session id and continues from there in both directions.

---

## Maintenance

- **`~/.pi/feedback.log`** is rotated by `~/.pi/feedback-loop.py` at 10 MiB, keeping 3 backups. If you ever see a 100+ MiB log, you've likely disabled the daemon — restart it.
- **`improvements`** — the `self-improve` skill commits to `improve-log.md` automatically. Roll back with `git revert <sha>`.
- **Sync** — re-running `setup.ps1` after pulling is safe: array-union semantics preserve local config; tests gate the result. Expect noisy auto-commits if `self-optimization-loop` is enabled on the remote.
- **Update pi** — `npm i -g @earendil-works/pi-coding-agent@latest`. The Optimus pin in `package.json` is `^0.79.3` for the dev harness; the runtime tracks whatever the global npm has.

## License

MIT.