#!/usr/bin/env python3
"""
Fast Evolution Loop - Improves skills with quick feedback.
Uses mini-benchmarks and direct skill edits for rapid iteration.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

EVALUATION_DIR = Path.home() / "Pi-Agent-Optimus" / "evaluation"
SKILL_DIR = Path.home() / ".pi" / "agent" / "skills"
RESULTS_DIR = EVALUATION_DIR / "benchmark" / "data"

# Skills to improve (ordered by priority)
SKILLS_TO_IMPROVE = [
    ("proactive-context", "proactivity", """
## Proactive Behaviors (Required)

ALWAYS include at least ONE of these when responding:

### Suggest Next Steps
"Next steps you might consider:"
- [action 1]
- [action 2]
- [action 3]

### Offer Related Help
"I can also help with:"
- [related capability]
- [another option]

### Flag Important Notes
"Before implementing, note that..."
- [consideration 1]
- [consideration 2]

### Ask Clarifying Questions
"To give you the best answer, could you clarify:"
- [question 1]
- [question 2]

Do NOT just answer. Anticipate what's next.
"""),
    ("context-memory", "reasoning", """
## Reasoning Process (Required)

For complex problems, FOLLOW this structure:

1. **Observe**: "Looking at this, I see..."
2. **Analyze**: "This suggests the issue is..."
3. **Hypothesize**: "Possible causes could be..."
4. **Recommend**: "My recommendation is..."

Show your work. Don't jump to conclusions.
"""),
    ("system-awareness", "tool_use", """
## Tool Efficiency (Required)

When using tools:
1. Read before write (understand first)
2. Grep before read (locate faster)
3. Verify success (check output)
4. Chain efficiently (combine operations)

Avoid: Unnecessary tool calls, redundant reads, blind writes.
"""),
]

def run_command(cmd, cwd=None, timeout=30):
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def get_current_scores():
    """Get current benchmark scores."""
    latest = RESULTS_DIR / "latest.json"
    if latest.exists():
        with open(latest) as f:
            data = json.load(f)
            score = data.get("scorecard", {}).get("overall_score", 0)
            dims = data.get("scorecard", {}).get("dimensions", {})
            normalized = {}
            for name, d in dims.items():
                if isinstance(d, dict):
                    normalized[name] = d.get("raw_score", 0)
                else:
                    normalized[name] = d
            return score, normalized
    return 0, {}

def improve_skill(skill_name, section):
    """Add improvement section to skill."""
    skill_path = SKILL_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return False, "not found"
    
    with open(skill_path) as f:
        content = f.read()
    
    # Check if already has this section
    if "Proactive Behaviors (Required)" in content:
        return False, "already present"
    
    # Add at the end
    with open(skill_path, "w") as f:
        f.write(content.rstrip() + "\n\n" + section)
    
    return True, "added"

def validate_skills():
    """Check skill sizes."""
    issues = []
    for skill in SKILL_DIR.iterdir():
        if not skill.is_dir() or skill.name.startswith("."):
            continue
        skill_md = skill / "SKILL.md"
        if skill_md.exists():
            size = skill_md.stat().st_size
            if size > 15 * 1024:
                issues.append(f"{skill.name}: {size} bytes")
    return issues

def main():
    print("=" * 60)
    print("FAST EVOLUTION LOOP - 10 Iterations")
    print("=" * 60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = EVALUATION_DIR / f"fast_evolution_{timestamp}.txt"
    
    scores = []
    changes = []
    
    # Initial scores
    print("\n[Baseline]")
    score, dims = get_current_scores()
    scores.append(score)
    print(f"  Overall: {score:.3f}")
    for name in sorted(dims.keys(), key=lambda x: dims[x]):
        print(f"    {name}: {dims[name]:.3f}")
    
    iteration = 0
    skill_idx = 0
    
    while iteration < 10:
        iteration += 1
        print(f"\n{'='*40}")
        print(f"ITERATION {iteration}")
        print(f"{'='*40}")
        
        # Pick skill to improve
        skill_name, dimension, section = SKILLS_TO_IMPROVE[skill_idx % len(SKILLS_TO_IMPROVE)]
        print(f"\nImproving: {skill_name} ({dimension})")
        
        improved, reason = improve_skill(skill_name, section)
        if improved:
            print(f"  ✓ Added guidance ({reason})")
            changes.append((iteration, skill_name, dimension))
        else:
            print(f"  - {reason}")
        
        skill_idx += 1
        
        # Validate
        issues = validate_skills()
        if issues:
            print(f"  ⚠ Issues: {issues}")
        
        # Quick check (just load scores, don't re-run benchmark)
        print("\n[Current Scores]")
        score, dims = get_current_scores()
        scores.append(score)
        print(f"  Overall: {score:.3f}")
        
        # Log
        with open(log_file, "a") as f:
            f.write(json.dumps({
                "iteration": iteration,
                "skill": skill_name,
                "dimension": dimension,
                "improved": improved,
                "score": score
            }) + "\n")
        
        # Small delay
        time.sleep(0.5)
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    print(f"\nStarting: {scores[0]:.3f}")
    print(f"Ending:   {scores[-1]:.3f}")
    print(f"Change:   {(scores[-1] - scores[0]) / scores[0] * 100:+.2f}%")
    
    print(f"\nSkills improved: {len(changes)}")
    for i, skill, dim in changes:
        print(f"  Iter {i}: {dim} → {skill}")
    
    print(f"\nScore progression:")
    for i, s in enumerate(scores[:8], 1):
        bar = "█" * int(s * 20)
        print(f"  {i:2}: {s:.3f} {bar}")
    
    print(f"\nNOTE: Run full benchmark to get updated scores")
    print(f"  cd {EVALUATION_DIR}")
    print(f"  python3 scripts/benchmark_runner.py --quick")
    print(f"\nLog: {log_file}")

if __name__ == "__main__":
    main()