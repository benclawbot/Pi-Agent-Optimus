#!/usr/bin/env python3
"""
Cross-Conversation Task Linking — manages task-links.md, detects task references.
Usage:
  python link-tasks.py --show
  python link-tasks.py --add "task-id" "conversation note"
  python link-tasks.py --history "task-id"
  python link-tasks.py --find "query"
  python link-tasks.py --detect "text"
"""
import os
import sys
from datetime import datetime

LINKS_FILE = os.path.expanduser("~/.pi/agent/task-links.md")
TASK_MEMORY = os.path.expanduser("~/.pi/agent/current-task.md")

DEFAULT_TEMPLATE = """# Task Links

<!-- Task conversation chains. Auto-built as tasks move across sessions. -->

"""

def read_links():
    if not os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "w") as f:
            f.write(DEFAULT_TEMPLATE)
        return DEFAULT_TEMPLATE
    with open(LINKS_FILE) as f:
        return f.read()

def write_links(content):
    with open(LINKS_FILE, "w") as f:
        f.write(content)

def parse_links(content):
    """Parse task-links.md into task chains."""
    tasks = []
    current = None
    
    for line in content.split("\n"):
        if line.startswith("## "):
            if current:
                tasks.append(current)
            task_id = line.replace("## ", "").strip()
            current = {"id": task_id, "conversations": [], "project": "", "status": ""}
        elif current:
            if line.startswith("Conversations:"):
                pass  # marker
            elif line.startswith("- 20"):
                current["conversations"].append(line[1:].strip())
            elif line.startswith("Project:"):
                current["project"] = line.replace("Project:", "").strip()
            elif line.startswith("Status:"):
                current["status"] = line.replace("Status:", "").strip()
    
    if current:
        tasks.append(current)
    return tasks

def show_links():
    tasks = parse_links(read_links())
    if not tasks:
        print("\n  No task links yet. Links are created automatically when tasks cross conversations.\n")
        return
    
    print(f"\n  TASK LINKS ({len(tasks)})")
    print(f"  {'='*55}")
    
    for t in tasks:
        conv_count = len(t["conversations"])
        status = t.get("status", "")
        status_icon = {"active": "▶", "blocked": "⏸", "pending-review": "👀"}.get(status, "○")
        
        print(f"\n  {status_icon} {t['id']}")
        print(f"     Project: {t['project']}")
        print(f"     {conv_count} conversation(s):")
        for conv in t["conversations"][-3:]:
            print(f"       • {conv[:60]}")
        if conv_count > 3:
            print(f"       +{conv_count - 3} more")
    
    print()

def add_link(task_id, conversation_note, project="", status="active"):
    content = read_links()
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Check if task already exists
    existing = f"## {task_id}" in content
    
    if existing:
        # Append to conversations
        lines = content.split("\n")
        new_lines = []
        in_task = False
        
        for line in lines:
            if line.startswith(f"## {task_id}"):
                in_task = True
            elif in_task and line.startswith("## "):
                in_task = False
            
            if in_task and "Conversations:" in line:
                # Add after the marker
                new_lines.append(line)
                new_lines.append(f"- {today}: {conversation_note}")
            else:
                new_lines.append(line)
        
        write_links("\n".join(new_lines))
    else:
        # Create new entry
        new_task = f"""

## {task_id}
Conversations:
- {today}: {conversation_note}
Project: {project}
Status: {status}
"""
        write_links(content + new_task)
    
    print(f"  ✓ Linked: {task_id}")

def show_history(task_id):
    tasks = parse_links(read_links())
    task = next((t for t in tasks if t["id"] == task_id), None)
    
    if not task:
        print(f"  Task not found: {task_id}")
        return
    
    print(f"\n  {task_id}")
    print(f"  Project: {task['project']}")
    print(f"  Status: {task.get('status', 'unknown')}")
    print(f"\n  Conversation history:")
    for conv in task["conversations"]:
        print(f"  • {conv}")
    print()

def find_task(query):
    """Find tasks matching a query."""
    tasks = parse_links(read_links())
    query_lower = query.lower()
    
    matches = []
    for t in tasks:
        if query_lower in t["id"].lower() or query_lower in t["project"].lower():
            matches.append(t)
    
    if not matches:
        print(f"  No tasks matching '{query}'")
        return
    
    print(f"\n  Matches for '{query}':")
    for t in matches:
        print(f"  • {t['id']} ({t['project']})")
    print()

def detect_task(text, task_memory_content=""):
    """Detect if text references a known task."""
    tasks = parse_links(read_links())
    
    # Simple keyword matching
    for t in tasks:
        keywords = t["id"].split("-") + t["project"].split("-")
        matched = [kw for kw in keywords if kw.lower() in text.lower()]
        if matched:
            return t
    
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_links()
    elif sys.argv[1] == "--show":
        show_links()
    elif sys.argv[1] == "--add" and len(sys.argv) > 3:
        task_id = sys.argv[2]
        note = " ".join(sys.argv[3:])
        project = ""
        status = "active"
        # Check for --project flag
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            project = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        add_link(task_id, note, project, status)
    elif sys.argv[1] == "--history" and len(sys.argv) > 2:
        show_history(sys.argv[2])
    elif sys.argv[1] == "--find" and len(sys.argv) > 2:
        find_task(sys.argv[2])
    elif sys.argv[1] == "--detect" and len(sys.argv) > 2:
        result = detect_task(" ".join(sys.argv[2:]))
        if result:
            print(f"  Detected: {result['id']} ({result['project']})")
            print(f"  Last: {result['conversations'][-1] if result['conversations'] else 'none'}")
        else:
            print("  No matching task found.")
    elif sys.argv[1] == "--help":
        print("Usage: link-tasks.py [--show|--add id note|--history id|--find query|--detect text]")