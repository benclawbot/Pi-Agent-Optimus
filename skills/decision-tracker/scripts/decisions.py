#!/usr/bin/env python3
"""
Decision Tracker — read/write decisions, filter by topic.
Usage:
  python decisions.py --list
  python decisions.py --add "project" "decision text" [--context "context"]
  python decisions.py --search "query"
  python decisions.py --project "project-name"
"""
import os
import sys
from datetime import datetime

DECISIONS_FILE = os.path.expanduser("~/.pi/agent/decisions.md")
TRACKER_SCRIPT = os.path.expanduser("~/.pi/agent/skills/improvement-tracker/scripts/update-tracker.py")

DEFAULT_TEMPLATE = """# Decisions Log

<!-- Decisions made in conversation. Organized by date, filterable by project/topic. -->

"""

def read_decisions():
    if not os.path.exists(DECISIONS_FILE):
        with open(DECISIONS_FILE, "w") as f:
            f.write(DEFAULT_TEMPLATE)
        return DEFAULT_TEMPLATE
    with open(DECISIONS_FILE) as f:
        return f.read()

def write_decisions(content):
    with open(DECISIONS_FILE, "w") as f:
        f.write(content)

def list_decisions(filter_text=""):
    content = read_decisions()
    
    decisions = []
    current = None
    
    for line in content.split("\n"):
        if line.startswith("## 20"):
            if current:
                decisions.append(current)
            parts = line.split(" — ")
            if len(parts) >= 2:
                date = parts[0].replace("## ", "").strip()
                project = parts[1].strip()
                current = {"date": date, "project": project, "text": "", "context": ""}
            else:
                current = {"date": line.replace("## ", "").strip(), "project": "", "text": "", "context": ""}
        elif current:
            if line.startswith("Decision:"):
                current["text"] = line.replace("Decision:", "").strip()
            elif line.startswith("Context:"):
                current["context"] = line.replace("Context:", "").strip()
    
    if current:
        decisions.append(current)
    
    if filter_text:
        filter_lower = filter_text.lower()
        decisions = [d for d in decisions if filter_lower in d["project"].lower() or filter_lower in d["text"].lower() or filter_lower in d["context"].lower()]
    
    if not decisions:
        print(f"No decisions found" + (f" matching '{filter_text}'" if filter_text else ""))
        return []
    
    print(f"\n  Decisions ({len(decisions)})")
    print(f"  {'='*55}")
    
    for d in reversed(decisions):
        print(f"\n  {d['date']} | {d['project']}")
        print(f"  {d['text']}")
        if d["context"]:
            print(f"  ({d['context'][:60]})")
    
    print()
    return decisions

def add_decision(project, text, context=""):
    today = datetime.now().strftime("%Y-%m-%d")
    
    entry = f"""

## {today} — {project}
Decision: {text}
Context: {context}
Source: Conversation {today}
"""
    
    content = read_decisions()
    write_decisions(content + entry)
    print(f"✓ Decision saved: {text[:60]}")

def search_decisions(query):
    list_decisions(query)

def get_project_decisions(project):
    list_decisions(project)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_decisions()
    elif sys.argv[1] == "--list":
        filter_text = sys.argv[2] if len(sys.argv) > 2 else ""
        list_decisions(filter_text)
    elif sys.argv[1] == "--add":
        project = sys.argv[2] if len(sys.argv) > 2 else "general"
        text = sys.argv[3] if len(sys.argv) > 3 else "decision made"
        ctx_idx = next((i for i, a in enumerate(sys.argv) if a == "--context"), None)
        context = sys.argv[ctx_idx + 1] if ctx_idx and ctx_idx + 1 < len(sys.argv) else ""
        add_decision(project, text, context)
    elif sys.argv[1] == "--search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        search_decisions(query)
    elif sys.argv[1] == "--project":
        project = sys.argv[2] if len(sys.argv) > 2 else ""
        get_project_decisions(project)
    elif sys.argv[1] == "--help":
        print("Usage: decisions.py [--list [filter]|--add project text [--context c]|--search query|--project name]")