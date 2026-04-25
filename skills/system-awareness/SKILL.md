---
name: system-awareness
description: Track running processes, dev servers, and open ports. Use when "what's running", "kill server", "check ports", "running processes", "dev servers", "stop dev", or "restart server".
allowed-tools: Read,Bash,execute_command
---

# System Awareness

Maintains awareness of running processes, dev servers, and port usage.

## Core Concept

Keep track of what the system is doing — don't start blind.

## Commands

### List Running Servers

```bash
python ~/.pi/agent/skills/system-awareness/scripts/process-tracker.py list
```

Output:
```json
{
  "processes": [
    {
      "pid": 12345,
      "name": "vite",
      "port": 5173,
      "dir": "C:/Users/thoma/project",
      "started": "2026-04-25T09:00:00Z"
    }
  ],
  "ports": [3000, 5173]
}
```

### Kill a Server

```bash
python ~/.pi/agent/skills/system-awareness/scripts/process-tracker.py kill <port>
# or
python ~/.pi/agent/skills/system-awareness/scripts/process-tracker.py kill --pid <pid>
```

### Detect Port Conflict

```bash
python ~/.pi/agent/skills/system-awareness/scripts/process-tracker.py check-port <port>
```

Returns whether port is in use and by what.

### Register Running Server

When you start a dev server manually:

```bash
python ~/.pi/agent/skills/system-awareness/scripts/process-tracker.py register <port> <name> <dir>
```

## Common Ports

| Port | Common Use |
|------|------------|
| 3000 | Next.js, CRA |
| 5173 | Vite (default) |
| 5174 | Vite (alt) |
| 5175+ | Vite (additional) |
| 8000 | Django, Flask |
| 8080 | Java, Go servers |
| 9229 | Node debugger |

## Common Dev Server Patterns

| Stack | Command | Port |
|-------|---------|------|
| Node/Vite | `npm run dev` | 5173 |
| Next.js | `npm run dev` | 3000 |
| React (CRA) | `npm start` | 3000 |
| Rust | `cargo run` | 8080 |
| Python/Flask | `flask run` | 5000 |
| Python/Django | `python manage.py runserver` | 8000 |
| Go | `go run .` | 8080 |
| Bun | `bun run dev` | 5173 |

## State File

Processes are tracked in `~/.pi/processes.json`:

```json
{
  "registered": [
    {
      "pid": 12345,
      "name": "vite",
      "port": 5173,
      "dir": "C:/Users/thoma/project",
      "started": "2026-04-25T09:00:00Z"
    }
  ]
}
```

## Integration

- Works with `cmux` skill for terminal process management
- `project-health` uses this for server status
- Can auto-register servers started via CMux

## File Structure

```
system-awareness/
├── SKILL.md
├── scripts/
│   └── process-tracker.py
└── references/
    └── common-patterns.md
```
