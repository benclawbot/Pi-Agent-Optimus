#!/usr/bin/env python3
"""
Quick Project Switch — load project context instantly.
Usage:
  python goto.py
  python goto.py liquidity-pulse
  python goto.py --search query
"""
import os
import sys

VAULT = os.path.expanduser("~/Dropbox/memory/Obsidian/Projects")
TASK_MEMORY = os.path.expanduser("~/.pi/agent/task-memory.md")
DECISIONS = os.path.expanduser("~/.pi/agent/decisions.md")

def read_file(path, max_lines=50):
    try:
        with open(path) as f:
            return "".join(f.readlines()[:max_lines]).strip()
    except:
        return ""

def find_projects():
    """Find all project folders."""
    if not os.path.exists(VAULT):
        return []
    return [d for d in os.listdir(VAULT) if os.path.isdir(os.path.join(VAULT, d)) and not d.startswith(".")]

def load_project_context(name):
    """Load all context for a project."""
    # Normalize name
    name_lower = name.lower().replace(" ", "-")
    
    # Find project folder
    project_path = None
    for p in find_projects():
        if p.lower().replace(" ", "-") == name_lower or p.lower() == name_lower:
            project_path = os.path.join(VAULT, p)
            break
    
    if not project_path:
        return None, find_closest(name, find_projects())
    
    # Load overview
    overview = read_file(os.path.join(project_path, "overview.md"), 30)
    status = read_file(os.path.join(project_path, "status.md"), 20)
    plan = read_file(os.path.join(project_path, "plan.md"), 20)
    
    # Load task memory
    task = None
    task_content = read_file(TASK_MEMORY, 200)
    for line in task_content.split("\n"):
        if f"Project: {name}" in line or f"Project: {p}" in line:
            # Found task
            pass
    
    # Load decisions for this project
    project_decisions = []
    decisions_content = read_file(DECISIONS, 300)
    for line in decisions_content.split("\n"):
        if f" — {p}" in line or f" — {name}" in line:
            project_decisions.append(line)
    
    return {
        "name": p,
        "path": project_path,
        "overview": overview,
        "status": status,
        "plan": plan,
        "decisions": project_decisions
    }, None

def find_closest(query, items):
    """Find closest matching project name."""
    query_lower = query.lower()
    matches = []
    for item in items:
        item_lower = item.lower()
        if query_lower in item_lower:
            matches.append(item)
        elif any(word in item_lower for word in query_lower.split()):
            matches.append(item)
    return matches[:3]

def list_projects():
    projects = find_projects()
    print(f"\n  Projects ({len(projects)}):\n")
    for p in sorted(projects):
        overview_path = os.path.join(VAULT, p, "overview.md")
        if os.path.exists(overview_path):
            first_line = read_file(overview_path, 3).split("\n")[0][:50]
            print(f"  {p}: {first_line}")
        else:
            print(f"  {p}")
    print()

def show_project(name):
    context, alternatives = load_project_context(name)
    
    if alternatives:
        print(f"\n  '{name}' not found. Did you mean:")
        for alt in alternatives:
            print(f"  - {alt}")
        print()
        return
    
    print(f"\n  Switched to: {context['name']}\n")
    
    if context['status']:
        print(f"  Status: {context['status'].split(chr(10))[0]}")
    
    if context['overview']:
        lines = context['overview'].split("\n")
        if len(lines) > 1:
            print(f"  Overview: {lines[1][:70]}")
    
    if context['decisions']:
        print(f"\n  Decisions:")
        for d in context['decisions'][:2]:
            print(f"    {d[:70]}")
    
    print("\n  Quick links:")
    print(f"    [[standup: {context['name']}]]")
    print(f"    [[decisions: {context['name']}]]")
    print(f"    [[task: {context['name']}]]")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_projects()
    elif sys.argv[1] == "--search" and len(sys.argv) > 2:
        query = sys.argv[2]
        projects = find_projects()
        matches = find_closest(query, projects)
        if matches:
            print(f"  Matches for '{query}':")
            for m in matches:
                print(f"  - {m}")
        else:
            print(f"  No matches for '{query}'")
    else:
        show_project(sys.argv[1])