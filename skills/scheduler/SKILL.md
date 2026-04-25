---
name: scheduler
description: Schedule reminders and alerts. Use when "remind me", "set a timer", "schedule", "alert me later", or "notify".
allowed-tools: Read,Bash,write
---

# Scheduler

Schedule reminders and system notifications.

## Core Concept

Don't rely on memory — schedule reminders for follow-ups, deadlines, and check-ins.

## Usage

### Set a Reminder

```bash
python scripts/schedule.py remind "Check PR status" --in 30m
python scripts/schedule.py remind "Review the code" --at "14:00"
python scripts/schedule.py remind "Deploy at 5pm" --at "2026-04-25T17:00:00"
```

### List Active Reminders

```bash
python scripts/schedule.py list
```

### Cancel Reminder

```bash
python scripts/schedule.py cancel <id>
```

### Snooze

```bash
python scripts/schedule.py snooze <id> --by 15m
```

## Output

When a reminder fires:
1. Show system notification
2. Log to `~/.pi/reminders.json`
3. Speak notification (if TTS available)

## State

Reminders stored in `~/.pi/reminders.json`:

```json
{
  "active": [
    {
      "id": "rem-001",
      "message": "Check CI status",
      "scheduled": "2026-04-25T10:30:00Z",
      "repeat": null
    }
  ],
  "completed": []
}
```

## Integration

- With `skill-evolution` to learn reminder patterns
- With `ci-watcher` to schedule follow-up checks
- System-level notifications via Windows `toast` or CLI

## Limitation

Requires background process to fire reminders. Best used:
- Before ending a session
- As a todo with explicit check-in

## File Structure

```
scheduler/
├── SKILL.md
└── scripts/
    └── schedule.py
```
