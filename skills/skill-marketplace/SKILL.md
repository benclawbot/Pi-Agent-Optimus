---
name: skill-marketplace
description: Index of all available skills with their triggers and domains. Shows what's available for current context. Use when "what skills", "skills available", "marketplace", or with `[[skills]]` to list all skills with what they do.
allowed-tools: Read
---

# Skill Marketplace

Lists all available skills with their triggers and what they do. Shows what's relevant to the current context.

## All Skills

| Skill | What it does | Triggers |
|-------|---------------|----------|
| **proactive-context** | Loads vault context at session start | Auto at startup |
| **quick-context** | Wikilink-style `[[context]]` resolution | `[[context]]`, `[[mem]]` |
| **skill-chain** | Skills activate together based on context | Context signals |
| **task-continuity** | Tracks tasks across sessions | `[[tasks]]`, `[[current]]` |
| **task-memory** | Current task + relevant files | `[[task]]`, `[[files]]` |
| **task-linker** | Links tasks across conversations | Auto-detection |
| **decision-tracker** | Persists decisions to decisions.md | `[[decisions]]` |
| **daily-standup** | Generates standup from conversations | `[[standup]]` |
| **memory-summarizer** | Captures discoveries, decisions, open items | `[[summarize]]` |
| **tech-stack-detector** | Auto-detects project tech, triggers skills | `[[stack]]` |
| **intent-classifier** | Auto-detects coding/debugging/research/etc | Auto |
| **improvement-tracker** | Tracks 30 improvements progress | `[[improvements]]` |
| **project-health** | CI status, deps, test freshness | `[[health]]` |
| **system-awareness** | Tracks running processes, servers, ports | `[[processes]]` |
| **auto-recover** | Diagnoses errors, suggests fixes | `[[fix]]` |
| **auto-test** | Runs tests for changed files | `[[test]]` |
| **architecture-diagram** | Generates SVG architecture diagrams | `[[diagram]]` |
| **ci-watcher** | Monitors CI pipelines, alerts on failures | `[[ci]]` |
| **file-watcher** | Watches files for changes, triggers actions | `[[watch]]` |
| **scheduler** | Sets reminders and alerts | `[[remind]]` |
| **db-introspect** | Queries database schemas directly | `[[schema]]` |
| **context-memory** | Stores project conventions and patterns | `[[remember]]` |
| **skill-evolution** | Evaluates and evolves skills | `[[evolve]]` |

## Commands

| Command | Action |
|---------|--------|
| `[[skills]]` | List all skills with descriptions |
| `[[skills: coding]]` | List skills relevant to coding |
| `[[skill: name]]` | Load a specific skill's context |
| `[[marketplace]]` | Show full skill marketplace |

## How It Works

1. Reads all skill directories from `~/.pi/agent/skills/`
2. Parses SKILL.md frontmatter for `name` and `description`
3. Shows skills with their triggers and domains
4. Filters by context when relevant (e.g., when coding, show testing/pattern skills)

## Format

```
 Skill Marketplace (22 skills)

 [Startup / Memory]
   proactive-context — loads vault context at session start
   quick-context — wikilink-style [[context]] resolution
   context-memory — stores project conventions
   improvement-tracker — tracks improvement progress

 [Tasks / Continuity]
   task-continuity — tracks tasks across sessions
   task-memory — current task + relevant files
   task-linker — links tasks across conversations
   decision-tracker — persists decisions

 [Code]
   auto-test — runs tests for changed files
   auto-recover — diagnoses errors, suggests fixes
   context-memory — coding conventions
   tech-stack-detector — auto-detects tech, triggers skills

 [Context]
   intent-classifier — auto-detects coding/debugging/etc
   skill-chain — skills activate together based on context
   memory-summarizer — captures discoveries from conversation

 [System]
   project-health — CI status, deps, test freshness
   system-awareness — tracks processes, servers, ports
   ci-watcher — monitors CI pipelines
```

## Scripts

- `scripts/list-skills.py` — lists all skills with metadata