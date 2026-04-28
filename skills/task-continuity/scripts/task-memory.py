#!/usr/bin/env python3
"""
Task Continuity — reads/writes task-memory.md, detects context.
Usage:
  python task-memory.py --list
  python task-memory.py --current
  python task-memory.py --add "project-name" "description"
  python task-memory.py --done task-id
  python task-memory.py --next "task-id" "next step"
  python task-memory.py --block "task-id" "reason"
"""
import os
import sys
import json
from datetime import datetime

MEMORY_FILE = os.path.expanduser("~/.pi/agent/task-memory.md")
TRACKER_MARK = os.path.expanduser("~/.pi/agent/skills/improvement-tracker/scripts/update-tracker.py")

DEFAULT_TEMPLATE = """# Active Tasks

<!-- Tasks persist across sessions. Update after each session. -->

"""

def read_memory():
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w") as f:
            f.write(DEFAULT_TEMPLATE)
        return DEFAULT_TEMPLATE
    with open(MEMORY_FILE) as f:
        return f.read()

def write_memory(content):
    with open(MEMORY_FILE, "w") as f:
        f.write(content)

def get_active_tasks():
    """Parse task-memory.md and return active tasks."""
    content = read_memory()
    tasks = []
    
    current_task = None
    for line in content.split("\n"):
        if line.startswith("## task-id:"):
            task_id = line.split("task-id:")[1].strip()
            current_task = {"id": task_id, "lines": []}
        elif current_task and line.startswith("##"):
            tasks.append(current_task)
            current_task = None
        elif current_task:
            current_task["lines"].append(line)
    
    if current_task:
        tasks.append(current_task)
    
    # Parse task fields
    parsed = []
    for t in tasks:
        task = {"id": t["id"], "project": "", "status": "", "last_session": "", "last_work": "", "pending": [], "blocked": ""}
        in_pending = False
        for line in t["lines"]:
            line = line.strip()
            if line.startswith("Project:"):
                task["project"] = line.split("Project:")[1].strip()
            elif line.startswith("Status:"):
                task["status"] = line.split("Status:")[1].strip()
            elif line.startswith("Last session:"):
                task["last_session"] = line.split("Last session:")[1].strip()
            elif line.startswith("Last work:"):
                task["last_work"] = line.split("Last work:")[1].strip()
            elif line.startswith("Pending:"):
                in_pending = True
            elif line.startswith("Blocked:") and in_pending:
                in_pending = False
                task["blocked"] = line.split("Blocked:")[1].strip()
            elif in_pending and line.startswith("-"):
                task["pending"].append(line[1:].strip())
        parsed.append(task)
    
    return parsed

def list_tasks():
    tasks = get_active_tasks()
    if not tasks:
        print("No active tasks.")
        return
    
    print(f"\n{'='*60}")
    print(f"  ACTIVE TASKS ({len(tasks)})")
    print(f"{'='*60}\n")
    
    for t in tasks:
        status_icon = {
            "in-progress": "▶",
            "blocked": "⏸",
            "pending-review": "👀",
            "done": "✓"
        }.get(t["status"], "○")
        
        blocked_str = f" [BLOCKED: {t['blocked'][:40]}]" if t["blocked"] else ""
        pending_str = f" → {t['pending'][0][:50]}" if t["pending"] else ""
        
        print(f"  {status_icon} {t['project']} ({t['last_session']})")
        if t["last_work"]:
            print(f"     {t['last_work'][:60]}{blocked_str}{pending_str}")
        print()
    
    return tasks

def show_current():
    tasks = get_active_tasks()
    if not tasks:
        print("No active tasks.")
        return
    
    # Most recent
    t = tasks[-1]
    print(f"\n  Current: {t['project']}")
    print(f"  Status: {t['status']}")
    print(f"  Last: {t['last_work']}")
    if t["pending"]:
        print(f"  Next: {t['pending'][0]}")
    if t["blocked"]:
        print(f"  Blocked: {t['blocked']}")
    print()

def mark_done(task_id):
    content = read_memory()
    content = content.replace(f"Status: {task_id}", "Status: done")
    write_memory(content)
    print(f"✓ Task marked done: {task_id}")

def add_task(project, description, session_date=None):
    if session_date is None:
        session_date = datetime.now().strftime("%Y-%m-%d")
    
    task_id = project.lower().replace(" ", "-")
    today = datetime.now().strftime("%Y-%m-%d")
    
    new_task = f"""

## task-id: {task_id}
Started: {today}
Project: {project}
Status: in-progress
Last session: {session_date}
Last work: {description}
Session history:
  - {session_date}: {description}
Pending:
  - 
Blocked: none
"""
    
    content = read_memory()
    write_memory(content + new_task)
    print(f"✓ Task added: {project}")

def set_next(task_id, next_step):
    content = read_memory()
    # Find task, update pending
    lines = content.split("\n")
    in_task = False
    in_pending = False
    new_lines = []
    
    for line in lines:
        if f"task-id: {task_id}" in line:
            in_task = True
        elif in_task and line.startswith("## task-id:"):
            in_task = False
        
        if in_task:
            if line.strip() == "Pending:":
                in_pending = True
            elif in_pending and line.startswith("-"):
                new_lines.append(f"  - {next_step}")
                in_pending = False
                continue
            elif in_pending and line.startswith("Blocked:"):
                new_lines.append(f"  - {next_step}")
                in_pending = False
        
        new_lines.append(line)
    
    write_memory("\n".join(new_lines))
    print(f"✓ Next step set: {next_step}")

def mark_blocked(task_id, reason):
    content = read_memory()
    lines = content.split("\n")
    in_task = False
    new_lines = []
    
    for line in lines:
        if f"task-id: {task_id}" in line:
            in_task = True
        elif in_task and line.startswith("## task-id:"):
            in_task = False
        
        if in_task and line.startswith("Blocked:"):
            line = f"Blocked: {reason}"
        
        new_lines.append(line)
    
    write_memory("\n".join(new_lines))
    print(f"✓ Marked blocked: {reason}")

def append_session(task_id, date, summary):
    content = read_memory()
    lines = content.split("\n")
    in_task = False
    new_lines = []
    in_history = False
    
    for line in lines:
        if f"task-id: {task_id}" in line:
            in_task = True
        elif in_task and line.startswith("## task-id:"):
            in_task = False
            in_history = False
        
        if in_task and "Session history:" in line:
            in_history = True
        
        if in_history and line.startswith("Pending:"):
            in_history = False
            new_lines.append(f"  - {date}: {summary}")
        
        new_lines.append(line)
    
    # Update last work and session
    content = "\n".join(new_lines)
    if f"Last session:" in content:
        content = content.replace("Last session: (date)", f"Last session: {date}")
    if f"Last work:" in content:
        content = content.replace("Last work: (description)", f"Last work: {summary}")
    
    write_memory(content)
    print(f"✓ Session appended to {task_id}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_tasks()
    elif sys.argv[1] == "--list":
        list_tasks()
    elif sys.argv[1] == "--current":
        show_current()
    elif sys.argv[1] == "--add":
        project = sys.argv[2] if len(sys.argv) > 2 else "new-project"
        desc = sys.argv[3] if len(sys.argv) > 3 else "task started"
        add_task(project, desc)
    elif sys.argv[1] == "--done":
        mark_done(sys.argv[2] if len(sys.argv) > 2 else "")
    elif sys.argv[1] == "--next":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        step = sys.argv[3] if len(sys.argv) > 3 else ""
        set_next(task_id, step)
    elif sys.argv[1] == "--block":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        reason = " ".join(sys.argv[3:])
        mark_blocked(task_id, reason)
    elif sys.argv[1] == "--append":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        date = sys.argv[3] if len(sys.argv) > 3 else datetime.now().strftime("%Y-%m-%d")
        summary = " ".join(sys.argv[4:])
        append_session(task_id, date, summary)
    elif sys.argv[1] == "--help":
        print("Usage: task-memory.py [--list|--current|--add project desc|--done id|--next id step|--block id reason]")