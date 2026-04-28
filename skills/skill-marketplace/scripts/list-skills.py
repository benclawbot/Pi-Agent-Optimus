#!/usr/bin/env python3
"""
Skill Marketplace — lists all available skills with descriptions and triggers.
Usage:
  python list-skills.py
  python list-skills.py --category coding
  python list-skills.py --skill skill-name
"""
import os
import re
import sys
from pathlib import Path

SKILLS_DIR = Path(os.path.expanduser("~/.pi/agent/skills"))

CATEGORIES = {
    "startup": ["proactive-context", "startup"],
    "memory": ["context-memory", "memory-summarizer", "task-memory", "decision-tracker"],
    "tasks": ["task-continuity", "task-memory", "task-linker"],
    "context": ["quick-context", "intent-classifier", "skill-chain", "skill-marketplace"],
    "skills": ["skill-evolution", "skill-marketplace"],
    "code": ["auto-test", "auto-recover", "tech-stack-detector"],
    "system": ["project-health", "system-awareness", "ci-watcher", "file-watcher"],
    "output": ["architecture-diagram", "memory-summarizer", "daily-standup"],
    "data": ["db-introspect", "scheduler"],
}

def parse_skill_frontmatter(skill_path):
    """Parse skill's SKILL.md for name and description."""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        return None
    
    content = skill_file.read_text()
    
    name = skill_path.name
    description = ""
    triggers = []
    
    # Parse frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]
            
            # Get name and description from frontmatter
            for line in frontmatter.split("\n"):
                if line.startswith("name:"):
                    name = line.replace("name:", "").strip()
                elif line.startswith("description:"):
                    description = line.replace("description:", "").strip()
            
            # Extract triggers from body (lines with backticks [[ ]])
            trigger_pattern = r'\[\[([^\]]+)\]\]'
            triggers = re.findall(trigger_pattern, body)
    
    return {
        "name": name,
        "description": description or "No description",
        "triggers": triggers[:5],  # limit to 5
        "path": str(skill_path),
    }

def list_all_skills():
    """List all skills in the skills directory."""
    skills = []
    
    for item in SKILLS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            skill = parse_skill_frontmatter(item)
            if skill:
                skills.append(skill)
    
    return sorted(skills, key=lambda x: x["name"])

def show_marketplace(filter_category=""):
    skills = list_all_skills()
    
    if filter_category:
        filter_skills = CATEGORIES.get(filter_category.lower(), [])
        skills = [s for s in skills if s["name"] in filter_skills or filter_category.lower() in s["name"].lower()]
    
    print(f"\n  Skill Marketplace ({len(skills)} skills)")
    print(f"  {'='*55}\n")
    
    # Group by first letter/category
    grouped = {}
    for s in skills:
        first = s["name"][0].upper()
        grouped.setdefault(first, []).append(s)
    
    for letter in sorted(grouped.keys()):
        print(f"  {letter}")
        for s in grouped[letter]:
            desc = s["description"][:45] + "..." if len(s["description"]) > 45 else s["description"]
            print(f"    {s['name']:<30} {desc}")
            if s["triggers"]:
                triggers_str = ", ".join(s["triggers"][:3])
                print(f"      triggers: {triggers_str}")
        print()

def show_skill_detail(name):
    skills = list_all_skills()
    skill = next((s for s in skills if s["name"] == name), None)
    
    if not skill:
        # Try partial match
        matches = [s for s in skills if name.lower() in s["name"].lower()]
        if len(matches) == 1:
            skill = matches[0]
        elif len(matches) > 1:
            print(f"  Multiple matches for '{name}':")
            for m in matches:
                print(f"    - {m['name']}")
            return
        else:
            print(f"  Skill not found: {name}")
            return
    
    print(f"\n  Skill: {skill['name']}")
    print(f"  Description: {skill['description']}")
    print(f"  Location: {skill['path']}")
    if skill["triggers"]:
        print(f"  Triggers: {', '.join(skill['triggers'])}")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_marketplace()
    elif sys.argv[1] == "--category" and len(sys.argv) > 2:
        show_marketplace(sys.argv[2])
    elif sys.argv[1] == "--skill" and len(sys.argv) > 2:
        show_skill_detail(sys.argv[2])
    elif sys.argv[1] == "--all":
        show_marketplace()
    elif sys.argv[1] == "--help":
        print("Usage: list-skills.py [--category name|--skill name]")
    else:
        # Assume it's a skill name to show
        show_skill_detail(sys.argv[1])