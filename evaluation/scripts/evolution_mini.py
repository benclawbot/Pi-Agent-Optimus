#!/usr/bin/env python3
"""
Mini-Benchmark for Fast Evolution - 5 quick tasks.
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

EVAL_DIR = Path.home() / "Pi-Agent-Optimus" / "evaluation"
SKILL_DIR = Path.home() / ".pi" / "agent" / "skills"
RESULTS_DIR = EVAL_DIR / "benchmark" / "data"

def get_scores():
    latest = RESULTS_DIR / "latest.json"
    if latest.exists():
        with open(latest) as f:
            d = json.load(f)
            score = d.get("scorecard", {}).get("overall_score", 0)
            dims = d.get("scorecard", {}).get("dimensions", {})
            normalized = {}
            for k, v in dims.items():
                normalized[k] = v.get("raw_score", 0) if isinstance(v, dict) else v
            return score, normalized
    return 0, {}

def run_mini_benchmark():
    """Run mini benchmark with only 5 tasks."""
    # Create mini suite
    suite = {
        "name": "Mini Evolution Suite",
        "tasks": [
            {
                "id": "test-1",
                "task": "Create a simple hello world function in Python",
                "category": "code",
                "expected_tools": ["write"]
            },
            {
                "id": "test-2", 
                "task": "Read the contents of any markdown file in this directory",
                "category": "read",
                "expected_tools": ["bash"]
            },
            {
                "id": "test-3",
                "task": "List all files in the current directory",
                "category": "file",
                "expected_tools": ["bash"]
            },
            {
                "id": "test-4",
                "task": "Explain what the following code does and suggest improvements: x = [i for i in range(10) if i % 2 == 0]",
                "category": "reasoning",
                "expected_tools": []
            },
            {
                "id": "test-5",
                "task": "What files might be related to this project?",
                "category": "proactive",
                "expected_tools": ["bash"]
            }
        ]
    }
    
    # Save mini suite
    mini_path = EVAL_DIR / "benchmark" / "tasks" / "mini-suite.json"
    with open(mini_path, "w") as f:
        json.dump(suite, f, indent=2)
    
    # Run with mini suite
    result = subprocess.run(
        f"cd {EVAL_DIR} && python3 scripts/benchmark_runner.py --suite benchmark/tasks/mini-suite.json --version mini",
        shell=True,
        capture_output=True,
        text=True,
        timeout=120
    )
    
    return result.returncode == 0

def improve_skill(skill_name, section):
    """Add section to skill."""
    path = SKILL_DIR / skill_name / "SKILL.md"
    if not path.exists():
        return False
    
    with open(path) as f:
        content = f.read()
    
    if section[:30] in content:
        return False
    
    with open(path, "w") as f:
        f.write(content.rstrip() + "\n\n" + section)
    return True

def remove_evolution_markers():
    """Remove all evolution markers from skills."""
    removed = []
    for skill in SKILL_DIR.iterdir():
        if not skill.is_dir() or skill.name.startswith("."):
            continue
        path = skill / "SKILL.md"
        if not path.exists():
            continue
        
        with open(path) as f:
            content = f.read()
        
        if "## EVOLUTION-GUIDANCE" in content:
            # Remove it
            parts = content.split("## EVOLUTION-GUIDANCE")
            content = parts[0].rstrip() + "\n"
            with open(path, "w") as f:
                f.write(content)
            removed.append(skill.name)
    
    return removed

# Main loop
if __name__ == "__main__":
    import sys
    
    if "--reset" in sys.argv:
        print("Removing evolution markers...")
        removed = remove_evolution_markers()
        print(f"Removed from: {removed}")
        exit(0)
    
    print("=" * 60)
    print("EVOLUTION LOOP - Mini Benchmark")
    print("=" * 60)
    
    # Reset first
    print("\n[Resetting skills...]")
    remove_evolution_markers()
    
    # Baseline
    print("\n[BASELINE - Running benchmark...]")
    run_mini_benchmark()
    score, dims = get_scores()
    print(f"Score: {score:.3f}")
    for k in sorted(dims.keys(), key=lambda x: dims[x]):
        print(f"  {k}: {dims[k]:.3f}")
    
    scores = [score]
    
    # Skills to improve
    SKILLS = [
        ("proactive-context", "## Proactive Prompts\n\nAlways suggest next steps."),
        ("context-memory", "## Memory Hints\n\nRemember previous context."),
        ("system-awareness", "## System Awareness\n\nKnow what processes are running."),
    ]
    
    for i in range(1, 11):
        print(f"\n{'='*40}")
        print(f"Iteration {i}/10")
        
        skill_name, section = SKILLS[(i-1) % len(SKILLS)]
        improved = improve_skill(skill_name, section)
        print(f"Improved {skill_name}: {improved}")
        
        # Run benchmark
        run_mini_benchmark()
        
        score, dims = get_scores()
        scores.append(score)
        
        change = (score - scores[-2]) / scores[-2] * 100 if scores[-2] > 0 else 0
        print(f"Score: {score:.3f} ({change:+.1f}%)")
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Start: {scores[0]:.3f}")
    print(f"End:   {scores[-1]:.3f}")
    print(f"Change: {(scores[-1]-scores[0])/scores[0]*100:+.2f}%")
    print("\nTrend:")
    for i, s in enumerate(scores):
        bar = "█" * int(s * 20)
        print(f"  {i}: {s:.3f} {bar}")