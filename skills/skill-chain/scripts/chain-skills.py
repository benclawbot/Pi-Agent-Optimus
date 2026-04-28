#!/usr/bin/env python3
"""
Skill Chain Executor — activates a set of skills together.
Usage:
  python chain-skills.py --chain auto-recover,system-awareness
  python chain-skills.py --list
  python chain-skills.py --status
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path(os.path.expanduser("~/.pi/agent/skills"))
CHAIN_STATE = os.path.expanduser("~/.pi/agent/.chain-state.json")

# ── skill definitions ─────────────────────────────────────────────────────────

SKILL_REGISTRY = {
    "auto-test": {
        "triggers": ["test", "testing", "run tests", "test this", ".py", ".js", ".ts"],
        "chains_with": ["project-health", "auto-recover"],
        "domains": ["code", "backend", "frontend"],
        "entry": "auto-test/SKILL.md",
    },
    "auto-recover": {
        "triggers": ["error", "bug", "crash", "failed", "broken", "Exception"],
        "chains_with": ["context-memory", "system-awareness"],
        "domains": ["code", "runtime", "ci"],
        "entry": "auto-recover/SKILL.md",
    },
    "system-awareness": {
        "triggers": ["server", "running", "process", "port", "localhost", "deploy"],
        "chains_with": ["auto-test", "auto-recover"],
        "domains": ["runtime", "dev"],
        "entry": "system-awareness/SKILL.md",
    },
    "project-health": {
        "triggers": ["health", "deps", "outdated", "ci status", "status"],
        "chains_with": ["auto-recover", "ci-watcher"],
        "domains": ["project", "ci", "deps"],
        "entry": "project-health/SKILL.md",
    },
    "context-memory": {
        "triggers": ["remember", "convention", "pattern", "context"],
        "chains_with": ["proactive-context"],
        "domains": ["project", "memory"],
        "entry": "context-memory/SKILL.md",
    },
    "proactive-context": {
        "triggers": ["context", "memory", "session", "startup"],
        "chains_with": ["quick-context", "skill-chain"],
        "domains": ["memory", "session"],
        "entry": "proactive-context/SKILL.md",
    },
    "quick-context": {
        "triggers": ["[[", "wikilink", "context"],
        "chains_with": ["proactive-context"],
        "domains": ["memory", "retrieval"],
        "entry": "quick-context/SKILL.md",
    },
    "skill-chain": {
        "triggers": ["skills", "chain", "activate"],
        "chains_with": ["intent-classifier", "skill-marketplace"],
        "domains": ["meta", "skills"],
        "entry": "skill-chain/SKILL.md",
    },
    "intent-classifier": {
        "triggers": ["intent", "classify", "what am i doing"],
        "chains_with": ["skill-chain"],
        "domains": ["meta", "routing"],
        "entry": "intent-classifier/SKILL.md",
    },
    "architecture-diagram": {
        "triggers": ["architecture", "diagram", "system design", "component"],
        "chains_with": ["context-memory"],
        "domains": ["design", "architecture"],
        "entry": "architecture-diagram/SKILL.md",
    },
    "ci-watcher": {
        "triggers": ["ci", "pipeline", "github actions", "build"],
        "chains_with": ["project-health", "auto-recover"],
        "domains": ["ci", "ops"],
        "entry": "ci-watcher/SKILL.md",
    },
    "tech-stack-detector": {
        "triggers": ["stack", "tech", "dependencies", "package.json"],
        "chains_with": ["auto-test", "project-health"],
        "domains": ["project", "meta"],
        "entry": "tech-stack-detector/SKILL.md",
    },
    "decision-tracker": {
        "triggers": ["decided", "decision", "agreed", "conclusion"],
        "chains_with": ["proactive-context"],
        "domains": ["memory", "decisions"],
        "entry": "decision-tracker/SKILL.md",
    },
    "daily-standup": {
        "triggers": ["standup", "daily", "status"],
        "chains_with": ["task-memory", "decision-tracker"],
        "domains": ["workflow", "planning"],
        "entry": "daily-standup/SKILL.md",
    },
    "task-memory": {
        "triggers": ["task", "working on", "current"],
        "chains_with": ["task-continuity", "context-memory"],
        "domains": ["workflow", "tasks"],
        "entry": "task-memory/SKILL.md",
    },
    "task-continuity": {
        "triggers": ["continue", "picking up", "task"],
        "chains_with": ["task-memory"],
        "domains": ["workflow", "tasks"],
        "entry": "task-continuity/SKILL.md",
    },
    "memory-summarizer": {
        "triggers": ["summarize", "discoveries", "open items"],
        "chains_with": ["decision-tracker", "context-memory"],
        "domains": ["memory", "session"],
        "entry": "memory-summarizer/SKILL.md",
    },
    "skill-marketplace": {
        "triggers": ["skills", "marketplace", "what skills"],
        "chains_with": ["skill-chain"],
        "domains": ["meta", "skills"],
        "entry": "skill-marketplace/SKILL.md",
    },
}

# ── chain state ───────────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(CHAIN_STATE):
        try:
            with open(CHAIN_STATE) as f:
                return json.load(f)
        except:
            pass
    return {"active": [], "disabled": False}

def save_state(state):
    with open(CHAIN_STATE, "w") as f:
        json.dump(state, f, indent=2)

# ── skill activation ─────────────────────────────────────────────────────────

def activate_skill(skill_name):
    """Mark a skill as active (loaded)."""
    state = load_state()
    if skill_name not in state["active"]:
        state["active"].append(skill_name)
    save_state(state)
    return skill_name

def deactivate_skill(skill_name):
    """Remove a skill from active set."""
    state = load_state()
    if skill_name in state["active"]:
        state["active"].remove(skill_name)
    save_state(state)

def chain_skills(skill_names):
    """Activate a set of skills together."""
    state = load_state()
    activated = []
    for skill in skill_names:
        if skill not in state["active"]:
            state["active"].append(skill)
            activated.append(skill)
        else:
            activated.append(skill)  # already active
    save_state(state)
    return activated

def expand_chain(skill_names, max_depth=2):
    """Expand chain to include related skills (chains_with)."""
    expanded = set(skill_names)
    frontier = list(skill_names)
    depth = 0

    while frontier and depth < max_depth:
        depth += 1
        next_frontier = []
        for skill in frontier:
            chains = SKILL_REGISTRY.get(skill, {}).get("chains_with", [])
            for related in chains:
                if related not in expanded:
                    expanded.add(related)
                    next_frontier.append(related)
        frontier = next_frontier

    return sorted(expanded)

# ── output ────────────────────────────────────────────────────────────────────

def list_skills():
    print(f"\n  Skill Registry ({len(SKILL_REGISTRY)} skills)")
    print(f"  {'='*55}")

    state = load_state()
    active = set(state.get("active", []))

    for name, info in sorted(SKILL_REGISTRY.items()):
        status = "▶" if name in active else "○"
        domains = ", ".join(info.get("domains", []))
        chains = ", ".join(info.get("chains_with", []))[:40]
        print(f"\n  {status} {name}")
        print(f"     Domains: {domains}")
        print(f"     Chains: {chains if chains else '(none)'}")
    print()

def show_status():
    state = load_state()
    active = state.get("active", [])
    disabled = state.get("disabled", False)

    if disabled:
        print(f"\n  Skill chaining is DISABLED.")
        return

    if active:
        print(f"\n  Active skills ({len(active)}):")
        for s in active:
            info = SKILL_REGISTRY.get(s, {})
            desc = info.get("domains", [])
            print(f"    ▶ {s} ({', '.join(desc)})")
    else:
        print(f"\n  No skills currently active.")
        print(f"  (Skills activate based on context signals)")

    print()

def activate_chain(skill_names_str):
    """Parse comma-separated skills and activate them."""
    names = [s.strip() for s in skill_names_str.split(",")]
    expanded = expand_chain(names)
    activated = chain_skills(expanded)

    print(f"\n  Activated chain: {', '.join(names)}")
    if len(expanded) > len(names):
        print(f"  Expanded via chains_with: {', '.join(set(expanded) - set(names))}")
    print(f"  Total active: {len(activated)}")
    for s in activated:
        print(f"    ▶ {s}")
    print()

def disable_chaining():
    state = load_state()
    state["disabled"] = True
    save_state(state)
    print(f"\n  Skill chaining disabled.")

def enable_chaining():
    state = load_state()
    state["disabled"] = False
    save_state(state)
    print(f"\n  Skill chaining enabled.")

# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_status()
    elif sys.argv[1] == "--chain" and len(sys.argv) > 2:
        activate_chain(sys.argv[2])
    elif sys.argv[1] == "--list":
        list_skills()
    elif sys.argv[1] == "--status":
        show_status()
    elif sys.argv[1] == "--off":
        disable_chaining()
    elif sys.argv[1] == "--on":
        enable_chaining()
    elif sys.argv[1] == "--help":
        print("Usage: chain-skills.py [--chain skill1,skill2|--list|--status|--on|--off]")
    else:
        print("Usage: chain-skills.py [--chain skill1,skill2|--list|--status|--on|--off]")
