#!/usr/bin/env python3
"""
Proactive Context Loader
Reads Thomas's vault context at session start.
"""
import os
import sys
from datetime import datetime

VAULT = os.path.expanduser("~/Dropbox/memory/Obsidian")
SESSION_MEMORY = os.path.expanduser("~/.pi/agent/context-today.md")
PIP_DIR = os.path.expanduser("~/.pi/agent")

def read_file(path, max_lines=50):
    try:
        with open(path) as f:
            lines = f.readlines()[:max_lines]
            return "".join(lines).strip()
    except:
        return None

def get_recent_conversations():
    """Get last 3 conversation files."""
    conv_dir = os.path.join(VAULT, "Conversations")
    if not os.path.exists(conv_dir):
        return []
    
    files = []
    for root, dirs, fnames in os.walk(conv_dir):
        for f in fnames:
            if f.endswith(".md") and f not in ("README.md",):
                path = os.path.join(root, f)
                files.append((os.path.getmtime(path), path, f))
    
    files.sort(reverse=True)
    return [(path, name) for _, path, name in files[:3]]

def extract_decisions(content):
    """Extract decision lines from conversation content."""
    decisions = []
    keywords = ["decision:", "decided:", "agreed:", "conclusion:", "action:"]
    for line in content.split("\n"):
        lower = line.lower()
        if any(kw in lower for kw in keywords):
            decisions.append(line.strip())
    return decisions[:5]

def get_active_projects():
    """Get active projects from Active Context."""
    ac_path = os.path.join(VAULT, "Active Context", "active-context.md")
    content = read_file(ac_path, 100)
    if not content:
        return []
    
    projects = []
    in_active = False
    for line in content.split("\n"):
        if "active projects" in line.lower():
            in_active = True
        elif in_active and line.startswith("## "):
            break
        elif in_active and line.startswith("-"):
            projects.append(line.strip("- ").strip())
    return projects[:5]

def build_context_summary():
    """Build the full context summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"SESSION CONTEXT — {today}\n"]
    
    # Active Context
    ac_path = os.path.join(VAULT, "Active Context", "active-context.md")
    ac_content = read_file(ac_path, 80)
    if ac_content:
        lines.append("\n=== ACTIVE CONTEXT ===")
        lines.append(ac_content[:2000])
    
    # Active projects
    projects = get_active_projects()
    if projects:
        lines.append("\n=== ACTIVE PROJECTS ===")
        for p in projects:
            lines.append(f"- {p}")
    
    # Recent conversations
    recent = get_recent_conversations()
    if recent:
        lines.append("\n=== RECENT CONVERSATIONS ===")
        for path, name in recent:
            content = read_file(path, 100)
            decisions = extract_decisions(content) if content else []
            lines.append(f"\n[{name}]")
            if decisions:
                lines.append(f"  Decisions: {decisions[0][:100]}")
    
    # Check for today's conversation
    today_conv = os.path.join(VAULT, "Conversations", today[:7], f"{today}.md")
    if os.path.exists(today_conv):
        content = read_file(today_conv, 50)
        if content:
            lines.append(f"\n=== TODAY'S SESSION ===")
            lines.append(content[:500])
    
    summary = "\n".join(lines)
    
    # Write session memory
    with open(SESSION_MEMORY, "w") as f:
        f.write(summary)
    
    print(summary)
    return summary

if __name__ == "__main__":
    build_context_summary()
