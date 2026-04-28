#!/usr/bin/env python3
"""
Skill Memory Sharing — manages learned patterns across skills.
Usage:
  python skill-memory.py --show
  python skill-memory.py --skill auto-recover
  python skill-memory.py --add auto-recover "pattern" "fix"
  python skill-memory.py --clear auto-recover
  python skill-memory.py --forget "pattern"
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SKILL_MEMORY_DIR = Path(os.path.expanduser("~/.pi/agent/skill-memory"))
SKILL_MEMORY_DIR.mkdir(exist_ok=True)

MEMORY_FILES = {
    "auto-recover": SKILL_MEMORY_DIR / "auto-recover.json",
    "project-health": SKILL_MEMORY_DIR / "project-health.json",
    "skill-evolution": SKILL_MEMORY_DIR / "skill-evolution.json",
    "context-memory": SKILL_MEMORY_DIR / "context-memory.json",
}

DEFAULT_MEMORY = {
    "last_updated": "",
    "patterns": [],
    "learned_fixes": [],
    "stats": {},
}

def read_memory(skill_name):
    path = MEMORY_FILES.get(skill_name)
    if not path:
        return None
    
    if not path.exists():
        return DEFAULT_MEMORY.copy()
    
    with open(path) as f:
        return json.load(f)

def write_memory(skill_name, data):
    path = MEMORY_FILES.get(skill_name)
    if not path:
        return False
    
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return True

def show_all():
    print(f"\n  Skill Memory ({len(MEMORY_FILES)} skills)")
    print(f"  {'='*55}")
    
    for skill, path in MEMORY_FILES.items():
        memory = read_memory(skill)
        pattern_count = len(memory.get("patterns", []))
        fixes_count = len(memory.get("learned_fixes", []))
        last = memory.get("last_updated", "never")
        
        print(f"\n  {skill}:")
        print(f"    Patterns: {pattern_count}")
        print(f"    Fixes: {fixes_count}")
        print(f"    Last updated: {last}")
    
    print()

def show_skill(skill_name):
    memory = read_memory(skill_name)
    
    if memory is None:
        print(f"  Unknown skill: {skill_name}")
        return
    
    print(f"\n  {skill_name} memory")
    print(f"  Last updated: {memory.get('last_updated', 'never')}")
    
    patterns = memory.get("patterns", [])
    if patterns:
        print(f"\n  Patterns ({len(patterns)}):")
        for p in patterns[-5:]:  # show last 5
            print(f"    • {p.get('pattern', 'unknown')[:50]}")
            print(f"      Fix: {p.get('fix_applied', 'none')[:50]}")
            print(f"      Success: {p.get('success_count', 0)}")
    
    fixes = memory.get("learned_fixes", [])
    if fixes:
        print(f"\n  Learned fixes ({len(fixes)}):")
        for f in fixes[-3:]:
            print(f"    • {f[:60]}")
    
    print()

def add_pattern(skill_name, pattern, fix):
    memory = read_memory(skill_name)
    
    if memory is None:
        print(f"  Unknown skill: {skill_name}")
        return
    
    patterns = memory.get("patterns", [])
    
    # Check if pattern exists
    existing = next((p for p in patterns if p.get("pattern") == pattern), None)
    if existing:
        existing["fix_applied"] = fix
        existing["success_count"] = existing.get("success_count", 0) + 1
        existing["last_success"] = datetime.now().strftime("%Y-%m-%d")
    else:
        patterns.append({
            "pattern": pattern,
            "fix_applied": fix,
            "success_count": 1,
            "last_success": datetime.now().strftime("%Y-%m-%d"),
            "first_seen": datetime.now().strftime("%Y-%m-%d"),
        })
    
    memory["patterns"] = patterns
    write_memory(skill_name, memory)
    print(f"  ✓ Added pattern to {skill_name}")

def clear_skill(skill_name):
    if skill_name not in MEMORY_FILES:
        print(f"  Unknown skill: {skill_name}")
        return
    
    path = MEMORY_FILES[skill_name]
    if path.exists():
        path.unlink()
    
    write_memory(skill_name, DEFAULT_MEMORY.copy())
    print(f"  ✓ Cleared memory for {skill_name}")

def forget_pattern(pattern):
    """Remove a pattern from any skill's memory."""
    removed = False
    for skill_name, path in MEMORY_FILES.items():
        memory = read_memory(skill_name)
        if not memory:
            continue
        
        patterns = memory.get("patterns", [])
        new_patterns = [p for p in patterns if pattern.lower() not in p.get("pattern", "").lower()]
        
        if len(new_patterns) < len(patterns):
            memory["patterns"] = new_patterns
            write_memory(skill_name, memory)
            removed = True
    
    if removed:
        print(f"  ✓ Forgot pattern: {pattern[:50]}")
    else:
        print(f"  Pattern not found: {pattern[:50]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_all()
    elif sys.argv[1] == "--show":
        show_all()
    elif sys.argv[1] == "--skill" and len(sys.argv) > 2:
        show_skill(sys.argv[2])
    elif sys.argv[1] == "--add" and len(sys.argv) > 4:
        skill_name = sys.argv[2]
        pattern = sys.argv[3]
        fix = " ".join(sys.argv[4:])
        add_pattern(skill_name, pattern, fix)
    elif sys.argv[1] == "--clear" and len(sys.argv) > 2:
        clear_skill(sys.argv[2])
    elif sys.argv[1] == "--forget" and len(sys.argv) > 2:
        forget_pattern(" ".join(sys.argv[2:]))
    elif sys.argv[1] == "--help":
        print("Usage: skill-memory.py [--show|--skill name|--add skill pattern fix|--clear skill|--forget pattern]")
    else:
        print("Usage: skill-memory.py [--show|--skill name|--add skill pattern fix|--clear skill|--forget pattern]")