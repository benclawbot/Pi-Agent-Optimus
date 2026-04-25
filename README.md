# Pi Config

My personal [pi](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) configuration — agents, skills, extensions, and prompts that shape how pi works for me.

## Setup

Clone this repo directly to `~/.pi/agent/` — pi auto-discovers everything from there (extensions, skills, agents, AGENTS.md, mcp.json). No symlinks, no manual wiring.

### Fresh machine

```bash
# 1. Install pi (https://github.com/badlogic/pi)

# 2. Clone this repo as your agent config
mkdir -p ~/.pi
git clone git@github.com:HazAT/pi-config ~/.pi/agent

# 3. Run setup (installs packages + extension deps)
cd ~/.pi/agent && ./setup.sh

# 4. Add your API keys to ~/.pi/agent/auth.json

# 5. Restart pi
```

### Updating

```bash
cd ~/.pi/agent && git pull
```

---

## Architecture

This config uses **subagents** — visible pi sessions spawned in cmux terminals. Each subagent is a full pi session with its own identity, tools, and skills. The user can watch agents work in real-time and interact when needed.

### Key Concepts

- **Subagents** — visible cmux terminals running pi. Autonomous agents self-terminate via `subagent_done`. Interactive agents wait for the user.
- **Agent definitions** (`agents/*.md`) — one source of truth for model, tools, skills, and identity per role.
- **Plan workflow** — `/plan` spawns an interactive planner subagent, then orchestrates workers and reviewers.
- **Iterate pattern** — `/iterate` forks the session into a subagent for quick fixes without polluting the main context.

---

## Agents

Specialized roles with baked-in identity, workflow, and review rubrics. Most agents now ship with the [pi-interactive-subagents](https://github.com/HazAT/pi-interactive-subagents) package; local overrides live in `agents/`.

| Agent | Source | Purpose |
|-------|--------|---------|
| **spec** | package | Interactive spec agent — clarifies WHAT to build (intent, requirements, ISC) |
| **planner** | package | Interactive planning — takes a spec and figures out HOW to build it |
| **scout** | package | Fast codebase reconnaissance — gathers context without making changes |
| **worker** | package | Implements tasks from todos, commits with polished messages |
| **reviewer** | package | Reviews code for quality, security, correctness |
| **visual-tester** | package | Visual QA — navigates web UIs via Chrome CDP, spots issues, produces reports |
| **claude-code** | package | Delegates autonomous tasks to Claude Code |
| **researcher** | local | Deep research using parallel.ai tools + Claude Code for code analysis |
| **autoresearch** | local | Autonomous experiment loop — runs, measures, and optimizes iteratively |

## Skills

Loaded on-demand when the context matches.

| Skill | When to Load |
|-------|-------------|
| **startup** | Session start — loads user preferences and project memory |
| **context-memory** | Maintaining project memory and conventions |
| **skill-evolution** | Capturing usage feedback and improving skills |
| **project-health** | Monitoring CI, test freshness, dependency updates |
| **system-awareness** | Tracking running processes, dev servers, open ports |
| **auto-test** | Running tests based on file changes |
| **file-watcher** | Watching files for changes and triggering actions |
| **ci-watcher** | Monitoring CI runs and alerting on failures |
| **architecture-diagram** | Creating architecture/system diagrams as HTML |
| **scheduler** | Scheduling reminders and alerts |
| **db-introspect** | Introspecting database schemas |
| **auto-recover** | Analyzing errors and suggesting/applying fixes |
| **todo-update** | Updating and closing todos with automatic summary |
| **write-todos** | Writing clear, actionable todos from a plan |
| **learn-codebase** | Onboarding to a new project, checking conventions |
| **pr-review** | Structured PR review with files, risks, approval |
| **test-runner** | Running tests by file or pattern |
| **quick-ref** | One-page reference for most-used commands |
| **commit** | Making git commits (mandatory for every commit) |
| **code-simplifier** | Simplifying or cleaning up code |
| **frontend-design** | Building web components, pages, or apps |
| **github** | Working with GitHub via `gh` CLI |
| **iterate-pr** | Iterating on a PR until CI passes |
| **session-reader** | Reading and analyzing pi session JSONL files |
| **skill-creator** | Scaffolding new agent skills |
| **cmux** | Managing terminal sessions via cmux |
| **presentation-creator** | Creating data-driven presentation slides |
| **add-mcp-server** | Adding MCP server configurations |

## Extensions

| Extension | What it provides |
|-----------|------------------|
| **answer/** | `/answer` command + `Ctrl+.` — extracts questions into interactive Q&A UI |
| **auto-commit/** | Automatic commit on command |
| **branch-cleanup/** | Find and delete merged/stale branches |
| **btw/** | `/btw` command — side-band input for clarifications without interrupting |
| **commit-review/** | Structured commit review before push |
| **compact-tools/** | Context compaction tools |
| **context-hotloader/** | Hot-load context files |
| **cmux/** | cmux integration — notifications, sidebar, workspace tools |
| **cost/** | `/cost` command — API cost summary |
| **execute-command/** | `execute_command` tool — lets the agent self-invoke slash commands |
| **session-notes/** | Session note-taking |
| **status/** | Project health status dashboard |
| **todos/** | `/todos` command + `todo` tool — file-based todo management |

## Commands

| Command | Description |
|---------|-------------|
| `/plan <description>` | Start a planning session — spawns planner subagent, then orchestrates execution |
| `/subagent <agent> <task>` | Spawn a subagent (e.g., `/subagent scout analyze the auth module`) |
| `/iterate [task]` | Fork session into interactive subagent for quick fixes |
| `/answer` | Extract questions into interactive Q&A |
| `/btw <note>` | Add a side-band clarification or steering note |
| `/todos` | Visual todo manager |
| `/cost` | API cost summary |

## Packages

Installed via `pi install`, managed in `settings.json`.

| Package | Description |
|---------|-------------|
| [pi-interactive-subagents](https://github.com/HazAT/pi-interactive-subagents) | Subagent tools + agent definitions + `/plan`, `/subagent`, `/iterate` commands |
| [pi-parallel](https://github.com/HazAT/pi-parallel) | Parallel web search, extract, research, and enrich tools |
| [pi-smart-sessions](https://github.com/HazAT/pi-smart-sessions) | AI-generated session names |
| [pi-diff-review](https://github.com/badlogic/pi-diff-review) | Interactive diff review UI |
| [chrome-cdp-skill](https://github.com/pasky/chrome-cdp-skill) | Chrome DevTools Protocol CLI for visual testing |

---

## Credits

Extensions from [mitsuhiko/agent-stuff](https://github.com/mitsuhiko/agent-stuff): `answer`, `todos`

Skills from [mitsuhiko/agent-stuff](https://github.com/mitsuhiko/agent-stuff): `commit`, `github`

Skills from [getsentry/skills](https://github.com/getsentry/skills): `code-simplifier`
