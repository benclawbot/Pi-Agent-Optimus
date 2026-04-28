#!/usr/bin/env python3
"""
Daily Standup Generator — compiles recent work into standup format.
Usage:
  python standup.py
  python standup.py --project project-name
  python standup.py --yesterday
  python standup.py --done
  python standup.py --next
  python standup.py --blocked
"""
import os
import sys
from datetime import datetime, timedelta

TASK_MEMORY = os.path.expanduser("~/.pi/agent/task-memory.md")
DECISIONS = os.path.expanduser("~/.pi/agent/decisions.md")
VAULT = os.path.expanduser("~/Dropbox/memory/Obsidian")
TRACKER_SCRIPT = os.path.expanduser("~/.pi/agent/skills/improvement-tracker/scripts/update-tracker.py")

def read_file(path, max_lines=200):
    try:
        with open(path) as f:
            lines = f.readlines()[:max_lines]
            return "".join(lines).strip()
    except:
        return ""

def get_recent_conversations(days=3):
    """Get conversation summaries from last N days."""
    conv_dir = os.path.join(VAULT, "Conversations")
    if not os.path.exists(conv_dir):
        return []
    
    today = datetime.now()
    conversations = []
    
    for i in range(days):
        date = today - timedelta(days=i)
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day_str = date.strftime("%Y-%m-%d")
        
        # Try various paths
        paths = [
            os.path.join(conv_dir, year, month, f"{day_str}.md"),
            os.path.join(conv_dir, year, month, f"{day_str}-full.md"),
        ]
        
        for path in paths:
            if os.path.exists(path):
                content = read_file(path, 100)
                if content:
                    # Extract meaningful first lines
                    lines = content.split("\n")[:20]
                    conversations.append({
                        "date": day_str,
                        "path": path,
                        "content": "\n".join(lines)
                    })
                    break
    
    return conversations

def parse_tasks():
    """Parse task-memory.md for active tasks."""
    content = read_file(TASK_MEMORY, 500)
    if not content or "<!--" in content and content.count("##") <= 1:
        return {"in_progress": [], "blocked": [], "done": [], "pending_review": []}
    
    tasks = {"in_progress": [], "blocked": [], "done": [], "pending_review": []}
    current = None
    
    for line in content.split("\n"):
        if line.startswith("## task-id:"):
            task_id = line.split("task-id:")[1].strip()
            current = {"id": task_id, "project": "", "status": "", "last_work": "", "pending": [], "blocked": ""}
        elif current:
            if line.startswith("Project:"):
                current["project"] = line.split("Project:")[1].strip()
            elif line.startswith("Status:"):
                current["status"] = line.split("Status:")[1].strip()
            elif line.startswith("Last work:"):
                current["last_work"] = line.split("Last work:")[1].strip()
            elif line.startswith("Pending:"):
                pass
            elif line.startswith("-") and current["status"]:
                current["pending"].append(line[1:].strip())
            elif line.startswith("Blocked:"):
                current["blocked"] = line.split("Blocked:")[1].strip()
            elif line.startswith("##") and line != f"## task-id: {current['id']}":
                # End of task
                if current["status"] in tasks:
                    tasks[current["status"]].append(current)
                current = None
    
    if current and current["status"] in tasks:
        tasks[current["status"]].append(current)
    
    return tasks

def parse_decisions(max_count=5):
    """Parse recent decisions."""
    content = read_file(DECISIONS, 200)
    if not content or content.count("##") <= 1:
        return []
    
    decisions = []
    current = None
    
    for line in content.split("\n"):
        if line.startswith("## 20"):
            if current:
                decisions.append(current)
            parts = line.replace("## ", "").split(" — ")
            date = parts[0].strip() if parts else ""
            project = parts[1].strip() if len(parts) > 1 else ""
            current = {"date": date, "project": project, "text": ""}
        elif current and line.startswith("Decision:"):
            current["text"] = line.replace("Decision:", "").strip()
    
    if current:
        decisions.append(current)
    
    return decisions[-max_count:]

def generate_standup(filter_project=""):
    """Generate the full standup."""
    today = datetime.now().strftime("%Y-%m-%d")
    tasks = parse_tasks()
    decisions = parse_decisions()
    
    lines = []
    lines.append(f"## Standup — {today}\n")
    
    # DONE section
    lines.append("### Done\n")
    done_items = tasks.get("done", []) + tasks.get("pending-review", [])
    if done_items:
        for t in done_items:
            if not filter_project or filter_project.lower() in t["project"].lower():
                lines.append(f"- {t['project']}: {t['last_work'][:80]}")
    else:
        # Try to extract from conversations
        convs = get_recent_conversations(1)
        if convs:
            lines.append(f"- (see recent conversations for detail)")
    lines.append("")
    
    # IN PROGRESS
    lines.append("### In Progress\n")
    in_prog = tasks.get("in-progress", [])
    if in_prog:
        for t in in_prog:
            if not filter_project or filter_project.lower() in t["project"].lower():
                pending = t["pending"][0] if t["pending"] else "ongoing work"
                lines.append(f"- {t['project']}: {pending[:80]}")
    else:
        lines.append("- (no active in-progress tasks)")
    lines.append("")
    
    # BLOCKED
    lines.append("### Blocked\n")
    blocked = tasks.get("blocked", [])
    if blocked:
        for t in blocked:
            if not filter_project or filter_project.lower() in t["project"].lower():
                lines.append(f"- {t['project']}: {t['blocked'][:80]}")
    else:
        lines.append("- (nothing blocked)")
    lines.append("")
    
    # DECISIONS
    if decisions:
        lines.append("### Decisions\n")
        for d in decisions:
            lines.append(f"- {d['date']} | {d['project']}: {d['text'][:70]}")
        lines.append("")
    
    return "\n".join(lines)

def show_section(section):
    tasks = parse_tasks()
    if section == "done":
        items = tasks.get("done", []) + tasks.get("pending-review", [])
        if not items:
            print("  No completed tasks.")
            return
        print("  Done:")
        for t in items:
            print(f"  - {t['project']}: {t['last_work'][:70]}")
    elif section == "next":
        items = tasks.get("in-progress", [])
        if not items:
            print("  No in-progress tasks.")
            return
        print("  In Progress:")
        for t in items:
            pending = t["pending"][0] if t["pending"] else "ongoing"
            print(f"  - {t['project']}: {pending[:70]}")
    elif section == "blocked":
        items = tasks.get("blocked", [])
        if not items:
            print("  Nothing blocked.")
            return
        print("  Blocked:")
        for t in items:
            print(f"  - {t['project']}: {t['blocked'][:70]}")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(generate_standup())
    elif sys.argv[1] == "--project" and len(sys.argv) > 2:
        print(generate_standup(sys.argv[2]))
    elif sys.argv[1] == "--yesterday":
        print(f"(Yesterday's standup not stored — showing today)")
        print(generate_standup())
    elif sys.argv[1] == "--done":
        show_section("done")
    elif sys.argv[1] == "--next":
        show_section("next")
    elif sys.argv[1] == "--blocked":
        show_section("blocked")
    elif sys.argv[1] == "--help":
        print("Usage: standup.py [--project name|--done|--next|--blocked]")