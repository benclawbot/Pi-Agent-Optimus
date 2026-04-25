# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Phase 1: LLM-as-Judge Evaluation

Evaluates skill quality using an LLM judge with a structured rubric.
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
SKILLS_DIR = Path.home() / ".pi" / "agent" / "skills"
MEMORY_FILE = Path.home() / ".pi" / "skill-memory.json"

# Evaluation rubric
RUBRIC = {
    "follows_procedure": {
        "weight": 0.30,
        "description": "Does the agent follow the skill's defined steps?",
        "prompts": [
            "Does this skill provide clear, actionable steps?",
            "Is the workflow well-defined and sequential?"
        ]
    },
    "output_quality": {
        "weight": 0.30,
        "description": "Is the output correct, useful, and well-structured?",
        "prompts": [
            "Is the expected output clearly specified?",
            "Are examples provided and relevant?"
        ]
    },
    "conciseness": {
        "weight": 0.20,
        "description": "Is the skill concise without sacrificing clarity?",
        "prompts": [
            "Is the skill appropriately sized?",
            "Are there unnecessary words or redundancy?"
        ]
    },
    "completeness": {
        "weight": 0.20,
        "description": "Are all required elements present?",
        "prompts": [
            "Are all edge cases covered?",
            "Is the error handling documented?"
        ]
    }
}

SCORE_LABELS = {
    (90, 100): "Excellent",
    (70, 89): "Good",
    (50, 69): "Needs Work",
    (0, 49): "Poor"
}


def load_skill(skill_name: str) -> Optional[dict]:
    """Load a skill's SKILL.md."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        return None
    
    with open(skill_path) as f:
        content = f.read()
    
    # Extract frontmatter
    lines = content.split("\n")
    frontmatter = {}
    in_frontmatter = False
    body_lines = []
    
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
        elif not in_frontmatter:
            body_lines.append(line)
    
    return {
        "name": skill_name,
        "description": frontmatter.get("description", ""),
        "content": "\n".join(body_lines).strip(),
        "size_kb": len(content) / 1024
    }


def load_memory() -> dict:
    """Load skill memory."""
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {"evaluations": [], "lessons": [], "gaps": [], "patterns": []}


def save_memory(memory: dict) -> None:
    """Save skill memory."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def llm_judge_score(skill: dict, test_cases: list[dict]) -> dict:
    """
    Simulate LLM-as-judge scoring.
    
    In production, this would call an LLM API with the rubric.
    For now, we calculate based on heuristics.
    """
    scores = {}
    
    content = skill["content"]
    size_kb = skill["size_kb"]
    
    # Follows procedure (30%)
    # Score based on having clear steps, numbered lists, imperative voice
    has_steps = any(char in content for char in ["1.", "2.", "3.", "## Step"])
    has_triggers = "Use when" in content or "trigger" in content.lower()
    procedure_score = 50 + (20 if has_steps else 0) + (20 if has_triggers else 0) + (10 if "```" in content else 0)
    scores["follows_procedure"] = min(100, procedure_score)
    
    # Output quality (30%)
    # Score based on having examples, tables, clear output format
    has_examples = "Example" in content or "```" in content
    has_tables = "|" in content and "-" in content
    has_output_section = "output" in content.lower() or "expected" in content.lower()
    quality_score = 50 + (20 if has_examples else 0) + (15 if has_tables else 0) + (15 if has_output_section else 0)
    scores["output_quality"] = min(100, quality_score)
    
    # Conciseness (20%)
    # Penalize oversized skills, reward brevity
    if size_kb < 5:
        conciseness_score = 90
    elif size_kb < 10:
        conciseness_score = 75
    elif size_kb < 15:
        conciseness_score = 60
    else:
        conciseness_score = 40
    scores["conciseness"] = conciseness_score
    
    # Completeness (20%)
    # Score based on having frontmatter, references, validation criteria
    has_frontmatter = skill["description"]
    has_references = "references/" in content or "Read" in content
    has_validation = "Validation" in content or "Acceptance" in content
    completeness_score = 50 + (20 if has_frontmatter else 0) + (15 if has_references else 0) + (15 if has_validation else 0)
    scores["completeness"] = min(100, completeness_score)
    
    return scores


def calculate_weighted_score(scores: dict) -> float:
    """Calculate weighted total score."""
    total = 0
    for criterion, score in scores.items():
        weight = RUBRIC[criterion]["weight"]
        total += score * weight
    return round(total, 1)


def get_label(score: float) -> str:
    """Get score label."""
    for (low, high), label in SCORE_LABELS.items():
        if low <= score <= high:
            return label
    return "Poor"


def evaluate_skill(skill_name: str, eval_source: str = "synthetic", count: int = 5) -> dict:
    """Evaluate a skill."""
    skill = load_skill(skill_name)
    if not skill:
        return {"error": f"Skill '{skill_name}' not found"}
    
    # Generate or load test cases
    if eval_source == "synthetic":
        test_cases = generate_synthetic_cases(skill, count)
    else:
        test_cases = load_session_cases(skill_name, count)
    
    # Score using LLM judge
    scores = llm_judge_score(skill, test_cases)
    total_score = calculate_weighted_score(scores)
    label = get_label(total_score)
    
    # Build evaluation result
    evaluation = {
        "id": str(uuid.uuid4())[:8],
        "skill": skill_name,
        "timestamp": datetime.now().isoformat()[:19] + "Z",
        "total_score": total_score,
        "label": label,
        "criteria": scores,
        "criteria_details": {
            criterion: {
                "score": score,
                "weight": RUBRIC[criterion]["weight"],
                "weighted": round(score * RUBRIC[criterion]["weight"], 1),
                "description": RUBRIC[criterion]["description"]
            }
            for criterion, score in scores.items()
        },
        "test_cases_generated": len(test_cases),
        "skill_size_kb": round(skill["size_kb"], 2)
    }
    
    # Save to memory
    memory = load_memory()
    if "evaluations" not in memory:
        memory["evaluations"] = []
    memory["evaluations"].append(evaluation)
    save_memory(memory)
    
    return evaluation


def generate_synthetic_cases(skill: dict, count: int) -> list[dict]:
    """Generate synthetic test cases."""
    cases = []
    skill_name = skill["name"]
    
    # Generic test case generators
    generic_cases = [
        {"task": f"Test {skill_name} with a simple request", "expected": "Skill should be triggered and followed"},
        {"task": f"Test {skill_name} edge case", "expected": "Skill handles gracefully"},
        {"task": f"Verify {skill_name} output format", "expected": "Output matches expected structure"},
    ]
    
    for i in range(min(count, len(generic_cases))):
        cases.append({
            "id": f"synth-{i}",
            "type": "synthetic",
            "task": generic_cases[i]["task"],
            "expected": generic_cases[i]["expected"],
            "source": "llm-generated"
        })
    
    return cases


def load_session_cases(skill_name: str, limit: int) -> list[dict]:
    """Load real cases from session history."""
    # Placeholder - would read from session files
    return []


def compare_evaluations(skill_name: str) -> dict:
    """Compare historical evaluations."""
    memory = load_memory()
    evals = [e for e in memory.get("evaluations", []) if e["skill"] == skill_name]
    
    if len(evals) < 2:
        return {"error": "Not enough evaluations to compare"}
    
    # Sort by timestamp
    evals.sort(key=lambda x: x["timestamp"])
    
    latest = evals[-1]
    previous = evals[-2]
    
    change = round(latest["total_score"] - previous["total_score"], 1)
    trend = "improving" if change > 0 else "declining" if change < 0 else "stable"
    
    return {
        "skill": skill_name,
        "evaluations": len(evals),
        "latest_score": latest["total_score"],
        "previous_score": previous["total_score"],
        "change": change,
        "trend": trend,
        "history": [
            {"timestamp": e["timestamp"], "score": e["total_score"]}
            for e in evals
        ]
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: evaluate-skill.py <command> [args]")
        print("Commands:")
        print("  evaluate <skill> [--eval-source synthetic|session] [--count N]")
        print("  compare <skill>")
        print("  history <skill>")
        print("  scores")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "evaluate":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        eval_source = "synthetic"
        count = 5
        
        if "--eval-source" in sys.argv:
            idx = sys.argv.index("--eval-source")
            eval_source = sys.argv[idx + 1]
        if "--count" in sys.argv:
            idx = sys.argv.index("--count")
            count = int(sys.argv[idx + 1])
        
        result = evaluate_skill(skill, eval_source, count)
        print(json.dumps(result, indent=2))
    
    elif cmd == "compare":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        result = compare_evaluations(skill)
        print(json.dumps(result, indent=2))
    
    elif cmd == "history":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        memory = load_memory()
        evals = [e for e in memory.get("evaluations", []) if e["skill"] == skill]
        print(f"Found {len(evals)} evaluations for '{skill}'")
        for e in evals:
            print(f"  {e['timestamp']}: {e['total_score']}/100 ({e['label']})")
    
    elif cmd == "scores":
        memory = load_memory()
        evals = memory.get("evaluations", [])
        
        # Get latest evaluation per skill
        latest_by_skill = {}
        for e in evals:
            skill = e["skill"]
            if skill not in latest_by_skill or e["timestamp"] > latest_by_skill[skill]["timestamp"]:
                latest_by_skill[skill] = e
        
        print("Latest skill scores:")
        for skill, e in sorted(latest_by_skill.items(), key=lambda x: x[1]["total_score"], reverse=True):
            print(f"  {skill}: {e['total_score']}/100 ({e['label']})")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
