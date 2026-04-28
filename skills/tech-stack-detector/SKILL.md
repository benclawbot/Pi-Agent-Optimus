---
name: tech-stack-detector
description: Reads package.json, Cargo.toml, pyproject.toml, requirements.txt at project open and auto-triggers relevant skills. Thomas doesn't manually invoke skills — the detected tech stack activates them. Use when opening a project, or with `[[stack]]` to see what's detected.
allowed-tools: Read,Bash
---

# Tech Stack Auto-Detection

When you open a project, reads the tech stack and activates the right skills automatically.

## Detection Files

| File | Detects |
|------|---------|
| `package.json` | Node.js, npm, React, Next.js, TypeScript |
| `Cargo.toml` | Rust |
| `pyproject.toml` | Python, Poetry |
| `requirements.txt` | Python, pip |
| `go.mod` | Go |
| `Gemfile` | Ruby |
| `pom.xml` | Java/Maven |
| `build.gradle` | Java/Gradle |
| `docker-compose.yml` | Docker |
| `Makefile` | Shell, build tooling |
| `.env.example` | Environment config |

## Tech-to-Skill Mapping

| Detected | Activates |
|----------|-----------|
| Python | `auto-test` (pytest), `context-memory`, `project-health` |
| Node.js/React | `auto-test`, `context-memory`, `project-health` |
| Rust | `auto-test` (cargo test), `context-memory`, `project-health` |
| Go | `auto-test`, `context-memory`, `project-health` |
| Docker | `system-awareness`, `project-health` |
| TypeScript | `auto-test`, `context-memory` |
| Next.js | `auto-test`, `system-awareness` (dev server) |
| FastAPI | `auto-test`, `project-health` |
| Django | `auto-test`, `project-health` |

## What Happens

When you open or work on a project:

1. Scan for detection files in the project root
2. Parse detected files to identify stack
3. Show brief indicator: "Detected: Python + FastAPI + Docker → activating relevant skills"
4. Activate skill chain based on detected tech

## Output Format

```
Tech Stack:
  • Python 3.11
  • FastAPI
  • Docker
  • React 18 (frontend)
  • PostgreSQL

Relevant skills activated:
  • auto-test (pytest)
  • project-health
  • context-memory
  • system-awareness (Docker)
```

## Commands

| Command | Action |
|---------|--------|
| `[[stack]]` | Detect and show current project tech stack |
| `[[stack: /path/to/project]]` | Detect tech stack for specific project |
| `[[skills for: python]]` | Show what skills activate for a given tech |

## Scripts

- `scripts/detect_stack.py` — scans project directory, returns detected stack + skills