#!/usr/bin/env python3
"""
Tech Stack Detector — scans project, identifies stack, shows relevant skills.
Usage:
  python detect_stack.py
  python detect_stack.py /path/to/project
  python detect_stack.py --skills python
"""
import json
import os
import sys
from pathlib import Path

STACK_SKILLS = {
    "python": ["auto-test", "context-memory", "project-health"],
    "rust": ["auto-test", "context-memory", "project-health"],
    "node.js": ["auto-test", "context-memory", "project-health"],
    "typescript": ["auto-test", "context-memory"],
    "react": ["auto-test", "context-memory"],
    "next.js": ["auto-test", "system-awareness"],
    "fastapi": ["auto-test", "project-health"],
    "django": ["auto-test", "project-health"],
    "docker": ["system-awareness", "project-health"],
    "postgresql": ["db-introspect"],
    "mysql": ["db-introspect"],
    "sqlite": ["db-introspect"],
    "go": ["auto-test", "context-memory", "project-health"],
    "java": ["auto-test", "project-health"],
    "ruby": ["auto-test"],
    "shell": ["system-awareness"],
}

DETECTION_FILES = {
    "package.json": "node.js",
    "Cargo.toml": "rust",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "go.mod": "go",
    "Gemfile": "ruby",
    "pom.xml": "java",
    "build.gradle": "java",
    "docker-compose.yml": "docker",
    "Makefile": "shell",
    ".env.example": "env",
}

def detect_stack(project_path="."):
    """Detect tech stack from project files."""
    path = Path(project_path).resolve()
    
    if not path.exists():
        print(f"  Path not found: {path}")
        return
    
    detected = []
    frameworks = []
    
    # Check for detection files
    for filename, tech in DETECTION_FILES.items():
        filepath = path / filename
        if filepath.exists():
            if tech == "python" and "pyproject.toml" in str(filepath):
                detected.append(("Python (Poetry)", filepath.name))
            elif tech == "python" and "requirements.txt" in str(filepath):
                detected.append(("Python (pip)", filepath.name))
            elif tech == "node.js":
                # Parse package.json for more detail
                frameworks.append(("Node.js", filepath.name))
                try:
                    with open(filepath) as f:
                        pkg = json.load(f)
                        deps = pkg.get("dependencies", {})
                        dev_deps = pkg.get("devDependencies", {})
                        if "react" in deps or "react" in dev_deps:
                            frameworks.append(("React", "package.json"))
                        if "next" in deps or "next" in dev_deps:
                            frameworks.append(("Next.js", "package.json"))
                        if "@nestjs" in deps:
                            frameworks.append(("NestJS", "package.json"))
                        engines = pkg.get("engines", {})
                        if engines:
                            node = engines.get("node", "")
                            if node:
                                frameworks.append((f"Node {node}", "package.json"))
                except:
                    pass
            elif tech == "docker":
                frameworks.append(("Docker", filepath.name))
            elif tech != "env":
                detected.append((tech.capitalize(), filepath.name))
    
    # Parse specific framework files
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        if "fastapi" in content.lower():
            frameworks.append(("FastAPI", "pyproject.toml"))
        if "django" in content.lower():
            frameworks.append(("Django", "pyproject.toml"))
        if "flask" in content.lower():
            frameworks.append(("Flask", "pyproject.toml"))
    
    cargo = path / "Cargo.toml"
    if cargo.exists():
        content = cargo.read_text()
        if "axum" in content.lower():
            frameworks.append(("Axum", "Cargo.toml"))
        if "tokio" in content.lower():
            frameworks.append(("Tokio (async)", "Cargo.toml"))
    
    # Combine and deduplicate
    all_items = list(set(detected + frameworks))
    all_items.sort(key=lambda x: x[0])
    
    return all_items

def get_skills_for_stack(stack):
    """Get skills that activate for a given stack."""
    skills = set()
    stack_lower = [s[0].lower() for s in stack]
    
    for tech, tech_skills in STACK_SKILLS.items():
        if any(tech in s for s in stack_lower):
            skills.update(tech_skills)
    
    return sorted(list(skills))

def show_stack(project_path="."):
    stack = detect_stack(project_path)
    
    if not stack:
        print(f"\n  No tech stack detected in {project_path}")
        return
    
    print(f"\n  Tech Stack ({len(stack)} detected):")
    print(f"  {'='*50}")
    
    for tech, source in stack:
        print(f"  • {tech}")
    
    skills = get_skills_for_stack(stack)
    if skills:
        print(f"\n  Relevant skills:")
        for skill in skills:
            print(f"    → {skill}")
    
    print()

def list_skills_for_tech(tech):
    """List skills for a specific tech."""
    tech_lower = tech.lower()
    matching = []
    
    for t, skills in STACK_SKILLS.items():
        if tech_lower in t:
            matching.append((t, skills))
    
    if not matching:
        print(f"  No skills configured for: {tech}")
        return
    
    print(f"\n  Skills for {tech}:")
    for t, skills in matching:
        print(f"  {t}: {', '.join(skills)}")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_stack(".")
    elif sys.argv[1] == "--skills" and len(sys.argv) > 2:
        list_skills_for_tech(sys.argv[2])
    elif sys.argv[1] == "--help":
        print("Usage: detect_stack.py [--skills tech|project_path]")
    else:
        show_stack(sys.argv[1])