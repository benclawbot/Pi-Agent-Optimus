#!/usr/bin/env python3
"""
Direct Evolution Loop - Improves skills based on benchmark analysis.
Each iteration: benchmark → analyze → directly improve weakest skill → re-benchmark.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

EVALUATION_DIR = Path.home() / "Pi-Agent-Optimus" / "evaluation"
SKILL_DIR = Path.home() / ".pi" / "agent" / "skills"
RESULTS_DIR = EVALUATION_DIR / "benchmark" / "data"

# Dimension to skill mapping
DIMENSION_TO_SKILL = {
    "proactivity": "proactive-context",
    "reasoning": "chain-of-thought",
    "code_quality": "context-memory",
    "speed": "system-awareness",
    "adaptability": "skill-evolution",
    "tool_use": "system-awareness",
    "user_experience": "context-memory",
    "reliability": "auto-recover",
    "safety": "auto-recover",
    "output_quality": "context-memory",
    "output": "context-memory",
}

# Skill improvement hints based on dimension
IMPROVEMENT_HINTS = {
    "proactivity": """
## Proactive Behaviors

When responding, INCLUDE at least one of:
1. "Suggested next steps:" - list 2-3 follow-up actions
2. "I can also:" - offer related capabilities
3. "Meanwhile:" - suggest parallel work
4. "Before you go:" - flag important considerations

Do NOT just answer the immediate question. Anticipate what's next.
""",
    "reasoning": """
## Reasoning Steps

For complex problems, show your reasoning:
1. "The issue appears to be..." - identify root cause
2. "This means..." - explain implications  
3. "Options are..." - list alternatives
4. "My recommendation is..." - pick one with justification

Do NOT jump to solutions. Show the thought process.
""",
    "code_quality": """
## Code Quality Standards

When writing code, ensure:
- Clear variable/function names
- Comments for non-obvious logic
- Error handling for edge cases
- Tests mentioned or suggested
- Security considerations noted

Do NOT just make it work. Make it maintainable.
""",
    "reliability": """
## Reliability Patterns

Handle failures gracefully:
1. Validate inputs before processing
2. Provide meaningful error messages
3. Suggest recovery actions
4. Log what went wrong for debugging

Do NOT fail silently. Make errors informative.
""",
    "tool_use": """
## Tool Selection

Choose tools wisely:
- Read before Write (understand existing)
- Use grep/find before read (locate files)
- Verify operations succeeded
- Chain related operations efficiently

Do NOT use tools unnecessarily. Be efficient.
""",
}

def run_command(cmd, cwd=None, timeout=120):
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

def run_benchmark():
    """Run benchmark and get results."""
    print("  Running benchmark...")
    
    cmd = f"cd {EVALUATION_DIR} && python3 scripts/benchmark_runner.py --quick"
    code, out, err = run_command(cmd, timeout=300)
    
    # Load results
    latest = RESULTS_DIR / "latest.json"
    if latest.exists():
        with open(latest) as f:
            return json.load(f)
    return None

def get_scores(data):
    """Extract scores from benchmark results."""
    if not data:
        return 0, {}
    
    score = data.get("scorecard", {}).get("overall_score", 0)
    dims = data.get("scorecard", {}).get("dimensions", {})
    
    # Normalize dimension names
    normalized_dims = {}
    for name, d in dims.items():
        if isinstance(d, dict):
            normalized_dims[name] = d.get("raw_score", 0)
        else:
            normalized_dims[name] = d
    
    return score, normalized_dims

def find_weakest(dims):
    """Find the weakest dimension."""
    if not dims:
        return None, 0
    
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    return sorted_dims[0]

def improve_skill(skill_name, dimension):
    """Directly improve a skill based on its weak dimension."""
    skill_path = SKILL_DIR / skill_name / "SKILL.md"
    
    if not skill_path.exists():
        print(f"    Skill not found: {skill_path}")
        return False
    
    # Read current content
    with open(skill_path) as f:
        content = f.read()
    
    original_content = content
    
    # Check if improvement hint is already present
    hint = IMPROVEMENT_HINTS.get(dimension, "")
    if hint and hint[:50] in content:
        print(f"    Already has {dimension} guidance")
        return False
    
    # Add improvement section
    if hint:
        # Find a good insertion point (before examples or at end of main content)
        sections = content.split("## ")
        
        # Insert after first substantial section or before Examples
        improved = False
        new_sections = []
        
        for i, section in enumerate(sections):
            if i == 0:  # Frontmatter
                new_sections.append(section)
                continue
            
            # Look for Examples or similar
            if section.lower().startswith("example"):
                # Insert before this
                new_sections.append(hint.strip())
                improved = True
            
            new_sections.append(section)
        
        if not improved:
            # Append at end
            content = content.rstrip() + "\n\n" + hint
        
        # Only write if changed
        if content != original_content:
            with open(skill_path, "w") as f:
                f.write(content)
            print(f"    Improved {skill_name} with {dimension} guidance")
            return True
    
    return False

def validate_skill(skill_name):
    """Validate skill meets requirements."""
    skill_path = SKILL_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return False
    
    size = skill_path.stat().st_size
    if size > 15 * 1024:  # 15KB
        print(f"    WARNING: {skill_name} is {size} bytes (limit 15KB)")
        return False
    
    return True

def validate_all_skills():
    """Validate all skills."""
    all_valid = True
    for skill in SKILL_DIR.iterdir():
        if not skill.is_dir() or skill.name.startswith("."):
            continue
        skill_md = skill / "SKILL.md"
        if skill_md.exists():
            size = skill_md.stat().st_size
            if size > 15 * 1024:
                print(f"    OVERSIZED: {skill.name} ({size} bytes)")
                all_valid = False
    return all_valid

def main():
    print("=" * 60)
    print("EVOLUTION LOOP - 10 Iterations")
    print("=" * 60)
    print()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = EVALUATION_DIR / f"evolution_log_{timestamp}.txt"
    scores = []
    changes_made = []
    
    for iteration in range(1, 11):
        print(f"\n{'='*50}")
        print(f"ITERATION {iteration}/10")
        print(f"{'='*50}")
        
        iter_start = time.time()
        
        # 1. Run benchmark
        print("\n[1/4] Running benchmark...")
        data = run_benchmark()
        
        if not data:
            print("  ERROR: No benchmark data")
            continue
        
        score, dims = get_scores(data)
        scores.append(score)
        
        print(f"  Overall: {score:.3f}")
        print("  Dimensions:")
        for name, val in sorted(dims.items(), key=lambda x: x[1]):
            indicator = "↓" if val < 0.5 else (" " if val < 0.8 else "↑")
            print(f"    {indicator} {name}: {val:.3f}")
        
        # 2. Analyze weakest
        print("\n[2/4] Analyzing...")
        weakest_dim, weakest_score = find_weakest(dims)
        print(f"  Weakest: {weakest_dim} ({weakest_score:.3f})")
        
        # 3. Improve
        print("\n[3/4] Improving skills...")
        target_skill = DIMENSION_TO_SKILL.get(weakest_dim, "context-memory")
        print(f"  Target skill: {target_skill} (for {weakest_dim})")
        
        improved = improve_skill(target_skill, weakest_dim)
        if improved:
            changes_made.append((iteration, weakest_dim, target_skill))
            print(f"  Applied improvement")
        else:
            # Try another dimension
            for dim in sorted(dims.items(), key=lambda x: x[1]):
                if dim[0] != weakest_dim:
                    alt_skill = DIMENSION_TO_SKILL.get(dim[0], "context-memory")
                    if improve_skill(alt_skill, dim[0]):
                        changes_made.append((iteration, dim[0], alt_skill))
                        print(f"  Applied improvement to {alt_skill}")
                        break
        
        # 4. Validate
        print("\n[4/4] Validating...")
        valid = validate_all_skills()
        print(f"  Skills valid: {valid}")
        print(f"  Skills valid: {valid}")
        
        elapsed = time.time() - iter_start
        
        # Log iteration
        log_entry = {
            "iteration": iteration,
            "score": score,
            "dimensions": dims,
            "weakest": weakest_dim,
            "weakest_score": weakest_score,
            "target_skill": target_skill,
            "improved": improved,
            "elapsed": elapsed
        }
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        # Calculate improvement
        if iteration > 1:
            pct = (score - scores[iteration-2]) / scores[iteration-2] * 100
            print(f"\n  Score change: {pct:+.2f}%")
        
        print(f"  Time: {elapsed:.1f}s")
        
        # Brief pause
        time.sleep(1)
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Starting: {scores[0]:.3f}")
    print(f"Ending:   {scores[-1]:.3f}")
    print(f"Change:   {(scores[-1] - scores[0]) / scores[0] * 100:+.2f}%")
    
    print(f"\nSkills improved: {len(changes_made)}")
    for iter_num, dim, skill in changes_made:
        print(f"  Iter {iter_num}: {dim} → {skill}")
    
    print(f"\nScore progression:")
    for i, s in enumerate(scores, 1):
        bar = "█" * int(s * 20)
        print(f"  {i:2}: {s:.3f} {bar}")
    
    print(f"\nLog: {log_file}")

if __name__ == "__main__":
    main()