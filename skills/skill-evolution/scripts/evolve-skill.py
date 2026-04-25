# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Phase 4: Evolutionary Improvement

Runs the evolution loop to improve skills through candidate generation and selection.
"""

import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
SKILLS_DIR = Path.home() / ".pi" / "agent" / "skills"
MEMORY_FILE = Path.home() / ".pi" / "skill-memory.json"

# Evolution settings
MAX_CANDIDATES = 5
MIN_IMPROVEMENT = 10  # Minimum % improvement to apply


def load_skill(skill_name: str) -> Optional[dict]:
    """Load skill content."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return None
    
    with open(skill_path) as f:
        content = f.read()
    
    return {
        "name": skill_name,
        "path": skill_path,
        "content": content,
        "size_kb": len(content) / 1024
    }


def load_memory() -> dict:
    """Load skill memory."""
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {"evaluations": [], "lessons": [], "gaps": [], "patterns": [], "evolutions": []}


def save_memory(memory: dict) -> None:
    """Save skill memory."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def get_latest_evaluation(skill_name: str) -> Optional[dict]:
    """Get the most recent evaluation for a skill."""
    memory = load_memory()
    evals = [e for e in memory.get("evaluations", []) if e["skill"] == skill_name]
    
    if not evals:
        return None
    
    return sorted(evals, key=lambda x: x["timestamp"], reverse=True)[0]


def get_skill_gaps(skill_name: str) -> list[dict]:
    """Get identified gaps for a skill."""
    memory = load_memory()
    gaps = memory.get("gaps", [])
    return [g for g in gaps if g.get("skill") == skill_name]


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from content."""
    lines = content.split("\n")
    frontmatter = {}
    body_lines = []
    in_frontmatter = False
    
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
        elif not in_frontmatter:
            body_lines.append(line)
    
    return frontmatter, "\n".join(body_lines)


def generate_candidates(skill: dict, gaps: list[dict]) -> list[dict]:
    """
    Generate improvement candidates.
    
    In production, this would use LLM to generate variants.
    Here we use heuristic improvements.
    """
    candidates = []
    name = skill["name"]
    content = skill["content"]
    frontmatter, body = parse_frontmatter(content)
    
    # Candidate 1: Improve trigger phrases
    candidate_1 = content
    if "Use when" in body:
        # Expand trigger phrases
        candidate_1 = body.replace(
            "Use when", 
            "Use when asked to, requested to, or prompted to"
        )
    candidate_1 = f"---\nname: {name}\ndescription: {frontmatter.get('description', '')}\n---\n{candidate_1}"
    
    candidates.append({
        "id": "candidate-1",
        "type": "improved_triggers",
        "description": "Expanded trigger phrases for better activation",
        "content": candidate_1
    })
    
    # Candidate 2: Add more examples
    candidate_2 = body
    if "Example" not in candidate_2:
        # Add example section
        example_section = """

## Example

```
You: Ask a question matching this skill
Skill: Activates and provides guidance
```
"""
        candidate_2 += example_section
    candidate_2 = f"---\nname: {name}\ndescription: {frontmatter.get('description', '')}\n---\n{candidate_2}"
    
    candidates.append({
        "id": "candidate-2",
        "type": "added_examples",
        "description": "Added example section for better understanding",
        "content": candidate_2
    })
    
    # Candidate 3: Improve structure (validation section)
    candidate_3 = body
    if "Validation" not in candidate_3:
        validation_section = """

## Validation

- [ ] Core functionality works as described
- [ ] Trigger phrases activate the skill
- [ ] Output matches expected format
"""
        candidate_3 += validation_section
    candidate_3 = f"---\nname: {name}\ndescription: {frontmatter.get('description', '')}\n---\n{candidate_3}"
    
    candidates.append({
        "id": "candidate-3",
        "type": "added_validation",
        "description": "Added validation criteria section",
        "content": candidate_3
    })
    
    # Candidate 4: Condense if oversized
    if skill["size_kb"] > 10:
        candidate_4 = body
        # Remove excessive whitespace
        candidate_4 = re.sub(r'\n\n\n+', '\n\n', candidate_4)
        candidate_4 = f"---\nname: {name}\ndescription: {frontmatter.get('description', '')}\n---\n{candidate_4}"
        
        candidates.append({
            "id": "candidate-4",
            "type": "condensed",
            "description": "Reduced excessive whitespace",
            "content": candidate_4
        })
    
    return candidates[:MAX_CANDIDATES]


def score_candidate(candidate: dict, baseline_score: float) -> dict:
    """
    Score a candidate relative to baseline.
    
    In production, this would run LLM evaluation.
    Here we use heuristics.
    """
    content = candidate["content"]
    size_kb = len(content) / 1024
    
    # Base score starts at baseline
    base_score = baseline_score
    
    # Bonus for size within limits
    if size_kb <= 15:
        base_score += 2
    
    # Bonus for examples
    if "Example" in content:
        base_score += 5
    
    # Bonus for validation section
    if "Validation" in content:
        base_score += 3
    
    # Bonus for improved triggers
    if candidate["type"] == "improved_triggers":
        base_score += 5
    
    # Penalty for oversized
    if size_kb > 15:
        base_score -= 10
    
    return {
        "candidate_id": candidate["id"],
        "type": candidate["type"],
        "description": candidate["description"],
        "score": round(min(100, max(0, base_score)), 1),
        "improvement": round(base_score - baseline_score, 1)
    }


def select_best_candidate(candidates: list[dict]) -> Optional[dict]:
    """Select the best candidate if it meets improvement threshold."""
    if not candidates:
        return None
    
    # Sort by score
    sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    best = sorted_candidates[0]
    
    if best["improvement"] >= MIN_IMPROVEMENT:
        return best
    
    return None


def evolve_skill(skill_name: str, iterations: int = 5) -> dict:
    """Run the evolution loop for a skill."""
    # Load skill
    skill = load_skill(skill_name)
    if not skill:
        return {"error": f"Skill '{skill_name}' not found"}
    
    # Get baseline evaluation
    baseline = get_latest_evaluation(skill_name)
    baseline_score = baseline["total_score"] if baseline else 60.0
    
    # Get gaps for targeted improvements
    gaps = get_skill_gaps(skill_name)
    
    # Generate candidates
    candidates_raw = generate_candidates(skill, gaps)
    
    # Score candidates
    candidates_scored = []
    for candidate in candidates_raw:
        score_result = score_candidate(candidate, baseline_score)
        candidates_scored.append({
            **candidate,
            **score_result
        })
    
    # Select best
    best = select_best_candidate(candidates_scored)
    
    result = {
        "skill": skill_name,
        "timestamp": datetime.now().isoformat()[:19] + "Z",
        "iterations": iterations,
        "baseline_score": baseline_score,
        "candidates_evaluated": len(candidates_scored),
        "candidates": candidates_scored,
        "best_candidate": None,
        "applied": False,
        "improvement": 0
    }
    
    if best:
        result["best_candidate"] = {
            "id": best["id"],
            "type": best["type"],
            "description": best["description"],
            "score": best["score"],
            "improvement": best["improvement"]
        }
        result["improvement"] = best["improvement"]
        
        # Apply the best candidate
        with open(skill["path"], "w") as f:
            f.write(best["content"])
        
        result["applied"] = True
        result["message"] = f"Applied {best['type']} improvement"
    else:
        result["message"] = f"No candidate met {MIN_IMPROVEMENT}% improvement threshold"
    
    # Save evolution record
    memory = load_memory()
    if "evolutions" not in memory:
        memory["evolutions"] = []
    memory["evolutions"].append(result)
    save_memory(memory)
    
    return result


def rollback_skill(skill_name: str, evolution_id: str) -> dict:
    """Rollback to a previous version."""
    memory = load_memory()
    evolutions = memory.get("evolutions", [])
    
    # Find the evolution to rollback
    target = None
    for e in evolutions:
        if e.get("id") == evolution_id or (e["skill"] == skill_name and evolutions.index(e) == evolution_id):
            target = e
            break
    
    if not target:
        return {"error": "Evolution not found"}
    
    # Note: This is simplified - real rollback would need versioned content
    return {
        "skill": skill_name,
        "rolled_back": False,
        "message": "Rollback requires git-based versioning"
    }


def get_evolution_history(skill_name: Optional[str] = None) -> dict:
    """Get evolution history for a skill."""
    memory = load_memory()
    evolutions = memory.get("evolutions", [])
    
    if skill_name:
        evolutions = [e for e in evolutions if e.get("skill") == skill_name]
    
    return {
        "skill": skill_name,
        "total_evolutions": len(evolutions),
        "successful": len([e for e in evolutions if e.get("applied")]),
        "failed": len([e for e in evolutions if not e.get("applied")]),
        "history": sorted(evolutions, key=lambda x: x["timestamp"], reverse=True)[:10]
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: evolve-skill.py <command> [args]")
        print("Commands:")
        print("  evolve <skill> [--iterations N]")
        print("  candidates <skill>")
        print("  history [--skill <name>]")
        print("  rollback <skill> <evolution-id>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "evolve":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        iterations = 5
        
        if "--iterations" in sys.argv:
            idx = sys.argv.index("--iterations")
            iterations = int(sys.argv[idx + 1])
        
        result = evolve_skill(skill, iterations)
        print(json.dumps(result, indent=2))
    
    elif cmd == "candidates":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        skill_data = load_skill(skill)
        
        if not skill_data:
            print(f"Skill '{skill}' not found")
            sys.exit(1)
        
        baseline = get_latest_evaluation(skill)
        baseline_score = baseline["total_score"] if baseline else 60.0
        
        gaps = get_skill_gaps(skill)
        candidates_raw = generate_candidates(skill_data, gaps)
        candidates_scored = []
        
        for c in candidates_raw:
            score = score_candidate(c, baseline_score)
            candidates_scored.append({**c, **score})
        
        print(f"Candidates for '{skill}' (baseline: {baseline_score}):")
        for c in sorted(candidates_scored, key=lambda x: x["score"], reverse=True):
            print(f"  {c['id']}: {c['type']} - {c['score']}/100 ({c['improvement']:+.1f})")
    
    elif cmd == "history":
        skill_name = None
        if "--skill" in sys.argv:
            idx = sys.argv.index("--skill")
            skill_name = sys.argv[idx + 1]
        
        result = get_evolution_history(skill_name)
        print(json.dumps(result, indent=2))
    
    elif cmd == "rollback":
        skill = sys.argv[2]
        evolution_id = sys.argv[3] if len(sys.argv) > 3 else "latest"
        result = rollback_skill(skill, evolution_id)
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
