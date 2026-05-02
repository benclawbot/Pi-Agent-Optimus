#!/usr/bin/env python3
"""
Quick Evolution Loop - Improves skills based on benchmark analysis.
"""

import json
from pathlib import Path
from datetime import datetime

EVAL_DIR = Path.home() / "Pi-Agent-Optimus" / "evaluation"
SKILL_DIR = Path.home() / ".pi" / "agent" / "skills"
RESULTS_DIR = EVAL_DIR / "benchmark" / "data"

# Dimension to skill mapping with improvement hints
IMPROVEMENTS = {
    "proactivity": {
        "skill": "proactive-context",
        "hint": "## Proactive Behaviors\n\nWhen responding, ALWAYS include one:\n- Suggested next steps:\n- I can also:\n- Meanwhile:\n"
    },
    "reasoning": {
        "skill": "chain-of-thought",
        "hint": "## Reasoning Steps\n\nFor complex problems:\n1. \"The issue is...\"\n2. \"Options are...\"\n3. \"My recommendation...\"\n"
    },
    "tool_use": {
        "skill": "system-awareness",
        "hint": "## Tool Efficiency\n\nUse tools wisely:\n- Read before write/edit\n- Grep before read\n- Verify after bash\n"
    },
    "code_quality": {
        "skill": "context-memory",
        "hint": "## Code Quality\n\nWhen creating files:\n- Follow project conventions\n- Add comments for complex logic\n- Test before finishing\n"
    },
}

def get_scores():
    """Get current benchmark scores."""
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

def find_weakest_dimensions(dims, threshold=0.7):
    """Find dimensions below threshold."""
    weak = [(k, v) for k, v in dims.items() if v < threshold]
    return sorted(weak, key=lambda x: x[1])

def improve_skill(skill_name, hint):
    """Add hint to skill if not present."""
    path = SKILL_DIR / skill_name / "SKILL.md"
    if not path.exists():
        return False
    
    with open(path) as f:
        content = f.read()
    
    # Check if hint already added
    if hint.strip() in content:
        return False
    
    with open(path, "w") as f:
        f.write(content.rstrip() + "\n\n" + hint)
    return True

def main():
    print("=" * 60)
    print("EVOLUTION LOOP - Skill Improvements")
    print("=" * 60)
    
    # Get current scores
    score, dims = get_scores()
    print(f"\nCurrent score: {score:.3f}")
    print(f"\nDimensions:")
    for k in sorted(dims.keys(), key=lambda x: dims[x]):
        print(f"  {k:20} {dims[k]:.3f}")
    
    # Find weakest dimensions
    weak = find_weakest_dimensions(dims)
    print(f"\nWeakest dimensions (<0.7):")
    for k, v in weak[:3]:
        print(f"  {k}: {v:.3f}")
    
    # Apply improvements to weakest dimensions
    print("\nApplying improvements...")
    improved = []
    for dim_name, dim_score in weak[:3]:
        if dim_name in IMPROVEMENTS:
            imp = IMPROVEMENTS[dim_name]
            success = improve_skill(imp["skill"], imp["hint"])
            if success:
                improved.append(imp["skill"])
                print(f"  ✓ Improved {imp['skill']} for {dim_name}")
            else:
                print(f"  - {imp['skill']} already enhanced")
    
    print(f"\nSkills improved: {len(improved)}")
    
    if improved:
        print("\nNext steps:")
        print("  1. Run benchmark to measure improvement")
        print("  2. Check if scores improved")
        print("  3. If not improved, revert and try different hints")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
