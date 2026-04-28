#!/usr/bin/env python3
"""
Skill Chain — detects context signals and emits skill activation events.
Usage:
  python detect-context.py "message text"
  python detect-context.py --signals
  python detect-context.py --active
"""
import os
import re
import sys
from pathlib import Path

SKILLS_DIR = Path(os.path.expanduser("~/.pi/agent/skills"))
SCRIPT_BASE = os.path.expanduser("~/.pi/agent/skills")

# ── context signal map ────────────────────────────────────────────────────────

CONTEXT_SIGNALS = {
    # File patterns
    (r"\.(py)\b",):                              ["auto-test", "context-memory", "project-health"],
    (r"\.(ts|tsx|js|jsx)\b",):                   ["auto-test", "context-memory", "project-health"],
    (r"\.(rs)\b",):                              ["auto-test", "context-memory", "project-health"],
    (r"\.(go)\b",):                              ["auto-test", "context-memory", "project-health"],

    # Error/debug signals
    (r"\berror\b", r"\bbug\b", r"\bcrash\b",
     r"failed", r"Exception", r"traceback",
     r"doesn't work", r"broken", r"fix this"):   ["auto-recover", "system-awareness", "context-memory"],

    # Architecture signals
    (r"architecture", r"diagram", r"system design",
     r"component", r"structure"):                 ["architecture-diagram", "context-memory"],

    # Health/status signals
    (r"health", r"status", r"deps", r"outdated",
     r"ci status", r"are we green"):             ["project-health", "ci-watcher"],

    # Testing signals
    (r"test", r"pytest", r"coverage", r"run tests"): ["auto-test", "project-health"],

    # Server/runtime signals
    (r"server", r"running", r"port", r"process",
     r"deploy", r"docker"):                       ["system-awareness", "project-health"],

    # Memory/context signals
    (r"remember", r"convention", r"pattern",
     r"context"):                                 ["context-memory", "proactive-context"],

    # Planning signals
    (r"plan", r"next steps", r"roadmap",
     r"should we", r"how to"):                    ["context-memory", "architecture-diagram"],

    # Stack detection
    (r"stack", r"tech", r"dependencies",
     r"package.json", r"pyproject.toml"):         ["tech-stack-detector"],

    # Skill discovery
    (r"what skills", r"skills available",
     r"marketplace", r"skill:"):                 ["skill-marketplace"],

    # Wikilinks (quick context)
    (r"\[\[",):                                  ["quick-context"],

    # Project switching
    (r"\[\[goto ", r"switch to project",
     r"load project"):                            ["quick-project-switch"],
}

# ── tech-to-skills map ────────────────────────────────────────────────────────

TECH_SIGNALS = {
    "package.json":      ["auto-test", "project-health"],
    "pyproject.toml":    ["auto-test", "project-health"],
    "requirements.txt":  ["auto-test"],
    "Cargo.toml":        ["auto-test", "project-health"],
    "go.mod":            ["auto-test"],
    "docker-compose.yml": ["system-awareness"],
    ".env.example":      ["context-memory"],
}

# ── detection ─────────────────────────────────────────────────────────────────

def detect_from_text(text):
    """Detect context signals from a message."""
    text_lower = text.lower()
    matched_signals = []

    for signals, skills in CONTEXT_SIGNALS.items():
        # Check all patterns in the tuple
        if all(re.search(p, text_lower, re.IGNORECASE) for p in signals):
            matched_signals.append({"signals": signals, "skills": skills})

    return matched_signals

def detect_from_project(cwd=None):
    """Detect skills from project files."""
    cwd = Path(cwd or os.getcwd())
    active_skills = set()
    project_files = []

    for indicator, skills in TECH_SIGNALS.items():
        if (cwd / indicator).exists():
            active_skills.update(skills)
            project_files.append(indicator)

    return sorted(active_skills), project_files

def merge_skills(context_signals, tech_skills):
    """Merge skills from context signals and tech detection."""
    all_skills = set()

    for signal_group in context_signals:
        all_skills.update(signal_group["skills"])

    all_skills.update(tech_skills)

    # Filter to skills that actually exist
    existing = []
    for skill in all_skills:
        skill_path = SKILLS_DIR / skill
        if skill_path.exists() and skill_path.is_dir():
            existing.append(skill)

    return sorted(existing)

# ── output ───────────────────────────────────────────────────────────────────

def show_detected(text):
    """Show what was detected from text."""
    signals = detect_from_text(text)
    cwd_skills, project_files = detect_from_project()
    merged = merge_skills(signals, cwd_skills)

    print(f"\n  Context signals detected:")
    if signals:
        for sg in signals:
            signal_names = ", ".join(sg["signals"])
            skills = ", ".join(sg["skills"])
            print(f"    Pattern match: {signal_names[:40]}")
            print(f"      → Skills: {skills}")
    else:
        print(f"    (none specific)")

    if project_files:
        print(f"\n  Project files found: {', '.join(project_files)}")

    if merged:
        print(f"\n  Skills to activate ({len(merged)}):")
        for skill in merged[:5]:
            print(f"    → {skill}")
        if len(merged) > 5:
            print(f"    +{len(merged) - 5} more")
    else:
        print(f"\n  No specific skills detected.")

    print()
    return merged

def show_signals():
    print(f"\n  Context Signals → Skill Chains")
    print(f"  {'='*55}")
    for signals, skills in CONTEXT_SIGNALS.items():
        sig_names = ", ".join(s[:15] for s in signals)[:40]
        print(f"\n  Signals: {sig_names}")
        print(f"    → {', '.join(skills)}")
    print()

def show_active():
    cwd_skills, project_files = detect_from_project()
    if cwd_skills:
        print(f"\n  Active skills for current project:")
        for s in cwd_skills:
            print(f"    → {s}")
        print(f"\n  Project files: {', '.join(project_files)}")
    else:
        print(f"\n  No project detected in {os.getcwd()}")
        print(f"  (Run from a project directory for auto-detection)")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_active()
    elif sys.argv[1] == "--signals":
        show_signals()
    elif sys.argv[1] == "--active":
        show_active()
    else:
        text = " ".join(sys.argv[1:])
        show_detected(text)
