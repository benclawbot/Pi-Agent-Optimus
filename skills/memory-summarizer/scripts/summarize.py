#!/usr/bin/env python3
"""
Conversational Memory Summarizer — generates session summaries from vault context.
Usage:
  python summarize.py
  python summarize.py --discoveries
  python summarize.py --open
  python summarize.py --map
  python summarize.py --save
"""
import os
import sys
from datetime import datetime

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
VAULT = os.path.expanduser("~/Dropbox/memory/Obsidian")

TASK_MEMORY = os.path.expanduser("~/.pi/agent/current-task.md")
DECISIONS = os.path.expanduser("~/.pi/agent/decisions.md")
SUMMARIES_DIR = os.path.expanduser("~/.pi/agent/session-summaries")

def read_file(path, max_lines=200):
    try:
        with open(path) as f:
            return "".join(f.readlines()[:max_lines]).strip()
    except:
        return ""

def get_today_conversation():
    """Get today's conversation file."""
    today = datetime.now().strftime("%Y-%m-%d")
    paths = [
        os.path.join(VAULT, "Conversations", today[:7], f"{today}.md"),
        os.path.join(VAULT, "Conversations", today[:7], f"{today}-full.md"),
    ]
    for path in paths:
        if os.path.exists(path):
            return read_file(path, 300)
    return ""

def get_session_log():
    """Get session log from task-memory."""
    content = read_file(TASK_MEMORY)
    if not content:
        return ""
    
    lines = content.split("\n")
    in_log = False
    log_lines = []
    
    for line in lines:
        if line.startswith("## Session Log"):
            in_log = True
        elif in_log and line.startswith("##"):
            break
        elif in_log:
            log_lines.append(line)
    
    return "\n".join(log_lines).strip()

def get_recent_decisions(max_count=5):
    """Get recent decisions."""
    content = read_file(DECISIONS)
    if not content:
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

def generate_summary():
    """Generate full session summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    log = get_session_log()
    decisions = get_recent_decisions()
    conversation = get_today_conversation()
    
    lines = []
    lines.append(f"# Session Summary — {today}\n")
    
    # Session Log (from task-memory)
    if log:
        lines.append("## Session Log")
        for entry in log.split("\n"):
            if entry.strip():
                lines.append(entry)
        lines.append("")
    
    # Recent Decisions
    if decisions:
        lines.append("## Decisions")
        for d in decisions:
            lines.append(f"- {d['date']} | {d['project']}: {d['text']}")
        lines.append("")
    
    # Open Items (from task-memory)
    task_content = read_file(TASK_MEMORY)
    if task_content:
        next_action = ""
        for line in task_content.split("\n"):
            if line.startswith("Next:"):
                next_action = line.replace("Next:", "").strip()
        
        if next_action:
            lines.append("## Open Items")
            lines.append(f"- Next: {next_action}")
            lines.append("")
    
    # Conversation excerpt
    if conversation:
        # Get first meaningful chunk
        lines.append("## Conversation")
        excerpt = conversation[:500]
        lines.append(f"```\n{excerpt}...\n```")
    
    return "\n".join(lines)

def show_discoveries():
    """Show discoveries from session."""
    log = get_session_log()
    if log:
        print("\n  Discoveries (from session log):\n")
        for entry in log.split("\n"):
            if entry.strip():
                print(f"  {entry}")
    else:
        print("\n  No discoveries logged yet.\n")

def show_open():
    """Show open items."""
    task_content = read_file(TASK_MEMORY)
    if not task_content:
        print("\n  No active task.\n")
        return
    
    next_action = ""
    task_name = ""
    
    for line in task_content.split("\n"):
        if line.startswith("Task:"):
            task_name = line.replace("Task:", "").strip()
        elif line.startswith("Next:"):
            next_action = line.replace("Next:", "").strip()
    
    print(f"\n  Current task: {task_name}")
    if next_action:
        print(f"  Next: {next_action}")
    else:
        print("  No open items.")
    print()

def show_map():
    """Show conversation map."""
    log = get_session_log()
    task_content = read_file(TASK_MEMORY)
    
    task_name = ""
    project = ""
    for line in task_content.split("\n"):
        if line.startswith("Task:"):
            task_name = line.replace("Task:", "").strip()
        elif line.startswith("Project:"):
            project = line.replace("Project:", "").strip()
    
    print(f"\n  Conversation Map")
    print(f"  {'='*55}")
    
    if project or task_name:
        print(f"\n  └── {project or 'project'}")
        if task_name:
            print(f"      └── {task_name}")
    
    if log:
        print(f"      └── Session log:")
        for entry in log.split("\n"):
            if entry.strip():
                print(f"          • {entry.strip()}")
    
    print()

def save_summary():
    """Save summary to session-summaries dir."""
    os.makedirs(SUMMARIES_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(SUMMARIES_DIR, f"{today}.md")
    
    summary = generate_summary()
    with open(path, "w") as f:
        f.write(summary)
    
    print(f"  ✓ Summary saved to {path}")

def save_thread(text):
    """Save a mid-conversation thread to memory."""
    today = datetime.now().strftime("%Y-%m-%d")
    thread_file = os.path.join(SUMMARIES_DIR, f"threads-{today}.md")
    
    os.makedirs(SUMMARIES_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%H:%M")
    entry = f"""
## {timestamp}

{text}

---
"""
    
    with open(thread_file, "a") as f:
        f.write(entry)
    
    print(f"  ✓ Thread saved ({len(text)} chars) to {thread_file}")
    return thread_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(generate_summary())
    elif sys.argv[1] == "--discoveries":
        show_discoveries()
    elif sys.argv[1] == "--open":
        show_open()
    elif sys.argv[1] == "--map":
        show_map()
    elif sys.argv[1] == "--save":
        save_summary()
    elif sys.argv[1] == "--save-thread":
        # Save arbitrary text as a thread
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "(no text provided)"
        save_thread(text)
    elif sys.argv[1] == "--help":
        print("Usage: summarize.py [--discoveries|--open|--map|--save|--save-thread text]")