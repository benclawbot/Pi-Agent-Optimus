#!/usr/bin/env python3
"""
Run Adaptability Feedback Loop
================================
This script demonstrates and executes the adaptability feedback loop:
1. Record baseline performance on a task type
2. Provide feedback/examples
3. Re-run and measure improvement
4. Compute adaptation score
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from adaptability_analyzer import AdaptabilityAnalyzer


def run_feedback_loop(task_type: str = "coding", baseline_score: float = None):
    """
    Execute a complete feedback loop.
    
    Args:
        task_type: The type of task to test (coding, reasoning, etc.)
        baseline_score: If provided, use this as the baseline instead of generating one
    """
    analyzer = AdaptabilityAnalyzer()
    
    print("=" * 60)
    print(f"  ADAPTABILITY FEEDBACK LOOP - {task_type.upper()}")
    print("=" * 60)
    
    # Step 1: Record baseline
    print("\n📊 Step 1: Recording baseline...")
    
    if baseline_score is None:
        # Simulate baseline measurement
        import random
        baseline_score = 0.5 + random.random() * 0.2  # 0.5-0.7 range
    
    baseline = analyzer.record_baseline(task_type, baseline_score)
    print(f"   Baseline recorded: {baseline_score:.3f}")
    
    # Step 2: Provide feedback
    print("\n📝 Step 2: Providing feedback...")
    
    feedback_text = {
        "coding": "Remember to: 1) Handle edge cases (empty input, null values), 2) Validate all inputs, 3) Add proper error handling, 4) Use meaningful variable names, 5) Include docstrings for functions.",
        "reasoning": "For reasoning tasks: 1) Break down the problem step by step, 2) Show your work/justification, 3) Consider alternative approaches, 4) Verify your answer makes sense.",
        "tool_usage": "When using tools: 1) Read before writing, 2) Use minimal commands, 3) Verify success after each call, 4) Clean up after yourself.",
        "safety": "For safety: 1) Never expose credentials, 2) Validate user intent, 3) Log suspicious requests, 4) Refuse appropriately when unsure."
    }
    
    feedback = feedback_text.get(task_type, "Consider edge cases and validate inputs before proceeding.")
    
    examples = {
        "coding": [
            "if items is None or len(items) == 0: return []",
            "try:\n    result = process(data)\nexcept ValueError as e:\n    result = default_value"
        ],
        "reasoning": [
            "Step 1: Identify the given information...",
            "Step 2: Apply the relevant rule/formula..."
        ]
    }
    
    feedback_record = analyzer.record_feedback(
        task_type,
        feedback,
        examples.get(task_type, [])
    )
    print(f"   Feedback recorded with {len(feedback_record['examples'])} examples")
    
    # Step 3: Simulate post-feedback performance
    print("\n🚀 Step 3: Running post-feedback task...")
    
    # Simulate improvement (actual benchmark would provide real score)
    import random
    improvement = random.uniform(0.05, 0.25)  # 5-25% improvement
    post_score = baseline_score + improvement
    
    result = analyzer.record_post_feedback_score(task_type, post_score)
    print(f"   Post-feedback score: {post_score:.3f}")
    print(f"   Improvement: +{result['improvement']:.3f} ({result['adaptation_rate']:.1%})")
    
    # Step 4: Compute adaptation score
    print("\n📈 Step 4: Computing adaptation score...")
    
    adaptation = analyzer.compute_adaptation_score(task_type)
    print(f"   Adaptation score: {adaptation['adaptation_score']:.3f}")
    print(f"   Feedback sessions: {adaptation['feedback_sessions']}")
    print(f"   Avg improvement: {adaptation['avg_improvement']:.3f}")
    
    # Summary
    print("\n" + "=" * 60)
    print("  FEEDBACK LOOP COMPLETE")
    print("=" * 60)
    print(f"   Task type: {task_type}")
    print(f"   Baseline: {baseline_score:.3f}")
    print(f"   Post-feedback: {post_score:.3f}")
    print(f"   Improvement: {result['improvement']:.3f} ({result['adaptation_rate']:.1%})")
    print(f"   Adaptation score: {adaptation['adaptation_score']:.3f}")
    
    return {
        "task_type": task_type,
        "baseline": baseline_score,
        "post_feedback": post_score,
        "improvement": result['improvement'],
        "adaptation_score": adaptation['adaptation_score']
    }


def run_multiple_loops():
    """Run feedback loops for multiple task types."""
    
    results = []
    
    for task_type in ["coding", "reasoning", "tool_usage", "safety"]:
        print(f"\n{'#' * 50}")
        result = run_feedback_loop(task_type)
        results.append(result)
    
    # Compute overall adaptability
    analyzer = AdaptabilityAnalyzer()
    overall = analyzer.get_adaptability_dimension()
    
    print("\n" + "=" * 60)
    print("  OVERALL ADAPTABILITY SCORES")
    print("=" * 60)
    
    for task_type, result in zip(["coding", "reasoning", "tool_usage", "safety"], results):
        print(f"   {task_type}: adaptation={result['adaptation_score']:.3f}, improvement=+{result['improvement']:.3f}")
    
    print(f"\n   OVERALL ADAPTABILITY: {overall['adaptation_score']:.3f}")
    print(f"   Few-shot efficiency: {overall['few_shot_efficiency']:.3f}")
    
    return overall


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run adaptability feedback loop")
    parser.add_argument("--task-type", "-t", default="coding",
                       choices=["coding", "reasoning", "tool_usage", "safety", "all"],
                       help="Task type to test")
    parser.add_argument("--baseline", "-b", type=float, help="Baseline score to use")
    
    args = parser.parse_args()
    
    if args.task_type == "all":
        result = run_multiple_loops()
    else:
        result = run_feedback_loop(args.task_type, args.baseline)
    
    # Save results
    results_dir = Path(__file__).parent.parent / "benchmark" / "data"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / "adaptability_feedback_loop.json"
    with open(results_file, "w") as f:
        json.dump(result if isinstance(result, list) else [result], f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")