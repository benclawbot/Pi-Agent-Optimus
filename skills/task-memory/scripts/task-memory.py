#!/usr/bin/env python3
"""
Task Memory Layer — tracks current task, relevant files, session log.
Usage:
  python task-memory.py --show
  python task-memory.py --set "task description"
  python task-memory.py --add-file "/path/to/file"
  python task-memory.py --done "action completed"
  python task-memory.py --next "next action"
  python task-memory.py --clear
"""
import os
import sys
from datetime import datetime

MEMORY_FILE = os.path.expanduser("~/.pi/agent/current-task.md")
TRACKER = os.path.expanduser("~/.pi/agent/skills/improvement-tracker/scripts/update-tracker.py")

DEFAULT_TEMPLATE = """# Current Task

## Active
Project: none
Task: 
Started: 
Context: 
Relevant files:
  - 
Last action: 
Next: 

## Session Log

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

def parse_memory(content):
    """Parse current-task.md into sections."""
    sections = {"project": "", "task": "", "started": "", "context": "",
                "files": [], "last_action": "", "next": "", "log": []}
    current_section = None
    
    for line in content.split("\n"):
        if line.startswith("Project:"):
            sections["project"] = line.replace("Project:", "").strip()
        elif line.startswith("Task:"):
            sections["task"] = line.replace("Task:", "").strip()
        elif line.startswith("Started:"):
            sections["started"] = line.replace("Started:", "").strip()
        elif line.startswith("Context:"):
            sections["context"] = line.replace("Context:", "").strip()
        elif line.startswith("Last action:"):
            sections["last_action"] = line.replace("Last action:", "").strip()
        elif line.startswith("Next:"):
            sections["next"] = line.replace("Next:", "").strip()
        elif line.startswith("- ") and "Relevant files" not in line:
            sections["files"].append(line[1:].strip())
        elif line.startswith("- [") and "]" in line:
            sections["log"].append(line.strip())
    
    return sections

def show_task():
    content = read_memory()
    sections = parse_memory(content)
    
    if not sections["task"]:
        print("\n  No active task. Type [[task: description]] to set one.\n")
        return
    
    print(f"\n  CURRENT TASK: {sections['task']}")
    print(f"  Project: {sections['project']}")
    if sections["started"]:
        print(f"  Started: {sections['started']}")
    if sections["context"]:
        print(f"  Context: {sections['context'][:60]}")
    
    files = [f for f in sections["files"] if f and f != "none"]
    if files:
        print(f"\n  RELEVANT FILES ({len(files)}):")
        for f in files[:5]:
            print(f"    • {f[:70]}")
        if len(files) > 5:
            print(f"    +{len(files) - 5} more")
    
    if sections["next"]:
        print(f"\n  NEXT: {sections['next']}")
    if sections["last_action"]:
        print(f"  LAST: {sections['last_action']}")
    
    print()

def set_task(project, description, context=""):
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = read_memory()
    
    lines = content.split("\n")
    new_lines = []
    in_active = False
    
    for line in lines:
        if line.startswith("## Active"):
            in_active = True
        elif in_active and line.startswith("##"):
            in_active = False
        
        if in_active:
            if line.startswith("Project:"):
                line = f"Project: {project}"
            elif line.startswith("Task:"):
                line = f"Task: {description}"
            elif line.startswith("Started:"):
                line = f"Started: {today}"
            elif line.startswith("Context:"):
                line = f"Context: {context}"
            elif line.startswith("Last action:"):
                line = "Last action:"
            elif line.startswith("Next:"):
                line = "Next:"
        
        new_lines.append(line)
    
    write_memory("\n".join(new_lines))
    print(f"  ✓ Task set: {description[:60]}")
    print(f"    Project: {project}")

def add_file(filepath):
    content = read_memory()
    lines = content.split("\n")
    in_files = False
    inserted = False
    new_lines = []
    
    for line in lines:
        if line.startswith("Relevant files:"):
            in_files = True
        elif in_files and line.startswith("##"):
            in_files = False
        
        if in_files and line.startswith("- ") and not inserted:
            new_lines.append(f"- {filepath}")
            inserted = True
        
        new_lines.append(line)
    
    if not inserted:
        new_lines.append(f"- {filepath}")
    
    write_memory("\n".join(new_lines))
    print(f"  ✓ Added: {filepath[:60]}")

def log_done(action):
    today = datetime.now().strftime("%H:%M")
    content = read_memory()
    
    # Update last action
    lines = content.split("\n")
    new_lines = []
    logged = False
    
    for line in lines:
        if line.startswith("Last action:"):
            line = f"Last action: {action}"
        if line.startswith("## Session Log"):
            if not logged:
                new_lines.append(f"- [{today}] {action}")
                logged = True
        new_lines.append(line)
    
    if not logged:
        content = content.rstrip() + f"\n- [{today}] {action}\n"
    else:
        content = "\n".join(new_lines)
    
    write_memory(content)
    print(f"  ✓ Done: {action[:60]}")

def set_next(action):
    content = read_memory()
    lines = content.split("\n")
    new_lines = []
    
    for line in lines:
        if line.startswith("Next:"):
            line = f"Next: {action}"
        new_lines.append(line)
    
    write_memory("\n".join(new_lines))
    print(f"  ✓ Next: {action[:60]}")

def clear_task():
    write_memory(DEFAULT_TEMPLATE)
    print("  Task cleared.")

def show_progress():
    content = read_memory()
    sections = parse_memory(content)
    
    if sections["task"]:
        files = [f for f in sections["files"] if f and f != "none"]
        print(f"\n  ▶ Working on: {sections['task'][:50]}")
        if sections["project"]:
            print(f"    Project: {sections['project']}")
        if sections["next"]:
            print(f"    Next: {sections['next'][:50]}")
        if files:
            print(f"    Files: {len(files)} relevant")
    else:
        print("\n  No active task.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_progress()
    elif sys.argv[1] == "--show":
        show_task()
    elif sys.argv[1] == "--set" and len(sys.argv) > 2:
        project = sys.argv[2] if len(sys.argv) > 2 else "general"
        desc = " ".join(sys.argv[2:])
        set_task(project, desc)
    elif sys.argv[1] == "--add-file" and len(sys.argv) > 2:
        add_file(" ".join(sys.argv[2:]))
    elif sys.argv[1] == "--done" and len(sys.argv) > 2:
        log_done(" ".join(sys.argv[2:]))
    elif sys.argv[1] == "--next" and len(sys.argv) > 2:
        set_next(" ".join(sys.argv[2:]))
    elif sys.argv[1] == "--clear":
        clear_task()
    elif sys.argv[1] == "--progress":
        show_progress()
    elif sys.argv[1] == "--help":
        print("Usage: task-memory.py [--show|--set task|--add-file path|--done action|--next action|--clear]")