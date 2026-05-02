#!/usr/bin/env python3
"""
Generate Proactivity Test Cases - Creates synthetic tests based on the 6 phases.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# 20 Proactivity Improvements from ChatGPT
PROACTIVITY_TEMPLATES = {
    "understanding_planning": [
        {
            "prompt": "Improve this API",
            "vague": True,
            "expected": ["scale", "users", "constraints", "plan"]
        },
        {
            "prompt": "Fix the bug",
            "vague": True,
            "expected": ["which bug", "where", "reproduce"]
        },
        {
            "prompt": "Add tests",
            "vague": True,
            "expected": ["unit vs integration", "coverage target", "framework"]
        }
    ],
    "execution_intelligence": [
        {
            "inject": "slow_tool",
            "expected": ["detected", "alternative", "optimize"]
        },
        {
            "inject": "failing_step",
            "expected": ["recovery", "workaround", "adapt"]
        }
    ],
    "reasoning_enhancements": [
        {
            "prompt": "This code works",
            "expected": ["assumption", "edge case", "potential issue"]
        }
    ],
    "outcome_improvement": [
        {
            "prompt": "Done with implementation",
            "expected": ["suggestion", "optimization", "next step"]
        }
    ],
    "tool_optimization": [
        {
            "scenario": "repeated task",
            "expected": ["cache", "reuse", "automate"]
        }
    ]
}

def generate_test_case(template: Dict, category: str, phase: str, idx: int) -> Dict:
    """Generate a single test case."""
    
    return {
        "task_id": f"PRO-{category.upper()[:4]}-{idx:03d}",
        "category": "proactivity",
        "phase": phase,
        "difficulty": template.get("difficulty", "medium"),
        "description": template.get("prompt", template.get("scenario", "")),
        "inject": template.get("inject", None),
        "vague_input": template.get("vague", False),
        "expected_behaviors": template.get("expected", []),
        "scoring": {
            "relevance": 2,
            "initiative": 2,
            "usefulness": 1
        }
    }

def generate_proactivity_suite() -> Dict:
    """Generate the full proactivity benchmark suite."""
    
    tasks = []
    idx = 1
    
    # Phase 1: Start (Goal Interpretation)
    for template in PROACTIVITY_TEMPLATES["understanding_planning"]:
        tasks.append(generate_test_case(template, "start", "start", idx))
        idx += 1
    
    # Phase 2: Execution
    for template in PROACTIVITY_TEMPLATES["execution_intelligence"]:
        tasks.append(generate_test_case(template, "exec", "execution", idx))
        idx += 1
    
    # Phase 3: Completion
    for template in PROACTIVITY_TEMPLATES["outcome_improvement"]:
        tasks.append(generate_test_case(template, "comp", "completion", idx))
        idx += 1
    
    # Phase 4: Reasoning
    for template in PROACTIVITY_TEMPLATES["reasoning_enhancements"]:
        tasks.append(generate_test_case(template, "reas", "reasoning", idx))
        idx += 1
    
    # Phase 5: Memory
    for template in PROACTIVITY_TEMPLATES["tool_optimization"]:
        tasks.append(generate_test_case(template, "mem", "memory", idx))
        idx += 1
    
    # Add synthetic vague prompts
    vague_prompts = [
        "Make it better",
        "Optimize performance",
        "Clean up the code",
        "Add documentation",
        "Review for issues",
    ]
    
    for prompt in vague_prompts:
        tasks.append({
            "task_id": f"PRO-VAGUE-{idx:03d}",
            "category": "proactivity",
            "phase": "start",
            "difficulty": "easy",
            "description": prompt,
            "vague_input": True,
            "expected_behaviors": ["clarifying question", "plan", "scope"],
            "scoring": {
                "clarifying_questions": 3,
                "structured_plan": 2
            }
        })
        idx += 1
    
    return {
        "name": "Proactivity Benchmark - 6 Phases",
        "description": "Comprehensive proactivity evaluation across task lifecycle phases",
        "total_tasks": len(tasks),
        "phases": ["start", "execution", "completion", "feedback", "memory", "idle"],
        "phase_weights": {
            "start": 0.20,
            "execution": 0.25,
            "completion": 0.20,
            "feedback": 0.15,
            "memory": 0.10,
            "idle": 0.10
        },
        "tasks": tasks
    }

def main():
    suite = generate_proactivity_suite()
    
    output_path = Path(__file__).parent.parent / "benchmark" / "tasks" / "proactivity-suite.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(suite, f, indent=2)
    
    print(f"Generated {len(suite['tasks'])} proactivity test cases")
    print(f"Saved to: {output_path}")
    
    # Print summary
    print("\nPhase distribution:")
    phase_counts = {}
    for task in suite["tasks"]:
        phase = task["phase"]
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    
    for phase, count in sorted(phase_counts.items()):
        print(f"  {phase}: {count}")

if __name__ == "__main__":
    main()
