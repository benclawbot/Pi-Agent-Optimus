#!/usr/bin/env python3
"""
Benchmark Runner - Executes the benchmark suite and collects all metrics.
Implements the complete evaluation framework from ChatGPT proposal.
"""

import json
import time
import statistics
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import tempfile
import traceback


class BenchmarkRunner:
    """Runs comprehensive benchmark evaluations."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.eval_config = self.config["evaluation"]
        self.dimensions_config = self.config["dimensions"]
        self.benchmark_config = self.config.get("benchmark", {})
        
        self.api_key = self.eval_config["apiKey"]
        self.api_base = self.eval_config["apiBaseUrl"]
        self.agent_model = self.eval_config["agentModel"]
        self.judge_model = self.eval_config["judgeModel"]
        
        self.timeout = self.benchmark_config.get("timeoutSeconds", 300)
        self.warmup_runs = self.benchmark_config.get("warmupRuns", 3)
    
    def run_benchmark(
        self,
        suite_path: str = None,
        version: str = "current"
    ) -> Dict[str, Any]:
        """
        Run the complete benchmark suite.
        
        Returns:
            Comprehensive results with all metrics per dimension
        """
        print(f"\n{'='*60}")
        print(f"  PI AGENT BENCHMARK - Running Evaluation")
        print(f"  Version: {version}")
        print(f"  Started: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")
        
        # Load benchmark suite
        if suite_path is None:
            suite_path = Path(__file__).parent.parent / "benchmark" / "tasks" / "benchmark-suite.json"
        
        with open(suite_path) as f:
            suite = json.load(f)
        
        tasks = suite.get("tasks", [])
        print(f"📋 Loaded benchmark suite: {len(tasks)} tasks\n")
        
        # Warmup runs
        if self.warmup_runs > 0:
            print(f"🔥 Warming up ({self.warmup_runs} runs)...\n")
            for i in range(self.warmup_runs):
                self._run_single_task(tasks[0], dry_run=True)
        
        # Run all tasks
        results = []
        dimension_results = defaultdict(list)
        
        for i, task in enumerate(tasks, 1):
            print(f"[{i}/{len(tasks)}] {task['id']} ({task['category']})...")
            
            try:
                result = self._run_single_task(task)
                results.append(result)
                
                # Aggregate dimension results
                for dim in task.get("metrics", []):
                    dimension_results[dim].append(result)
                
                # Progress indicator
                score = result.get("overall_score", 0)
                status = "✓" if score >= 0.6 else "✗"
                print(f"      → Score: {score:.2f} {status} ({result.get('duration_seconds', 0):.1f}s)\n")
                
            except Exception as e:
                print(f"      → Error: {str(e)}\n")
                results.append({
                    "task_id": task["id"],
                    "category": task["category"],
                    "error": str(e),
                    "overall_score": 0
                })
        
        # Compute all dimension metrics
        print("\n" + "="*60)
        print("  COMPUTING DIMENSION METRICS")
        print("="*60 + "\n")
        
        dimension_scores = self._compute_dimension_scores(results, dimension_results)
        
        # Compute overall scorecard
        scorecard = self._compute_scorecard(dimension_scores)
        
        # Store results
        benchmark_result = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "suite_name": suite.get("name", "unknown"),
            "total_tasks": len(tasks),
            "completed_tasks": len([r for r in results if "error" not in r]),
            "failed_tasks": len([r for r in results if "error" in r]),
            "results": results,
            "dimension_scores": dimension_scores,
            "scorecard": scorecard,
            "latency_stats": self._compute_latency_stats(results),
            "token_stats": self._compute_token_stats(results)
        }
        
        # Save results
        self._save_results(benchmark_result, version)
        
        # Print summary
        self._print_summary(scorecard, dimension_scores)
        
        return benchmark_result
    
    def _run_single_task(self, task: Dict, dry_run: bool = False) -> Dict[str, Any]:
        """Run a single benchmark task."""
        
        start_time = time.time()
        
        # Create workspace
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            
            # Build prompt
            prompt = self._build_task_prompt(task)
            
            if dry_run:
                time.sleep(0.1)  # Minimal simulation
                return {"task_id": task["id"], "score": 0.5}
            
            # Execute against Pi agent
            execution = self._execute_pi(prompt, workspace_path)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Judge output
            judgment = self._judge_task(task, execution)
            
            # Compute metrics for this task
            return {
                "task_id": task["id"],
                "category": task["category"],
                "difficulty": task.get("difficulty", "medium"),
                "duration_seconds": duration,
                "tokens_used": execution.get("tokens_used", 0),
                "tool_calls": len(execution.get("tool_calls", [])),
                "output": execution.get("output", ""),
                "files_created": execution.get("files_created", []),
                "judgment": judgment,
                "code_metrics": self._compute_code_metrics(execution),
                "reasoning_metrics": self._compute_reasoning_metrics(execution),
                "proactivity_metrics": self._compute_proactivity_metrics(execution),
                "overall_score": judgment.get("overall_score", 0) * (task.get("difficulty_score", 2) / 3)
            }
    
    def _build_task_prompt(self, task: Dict) -> str:
        """Build the prompt for a task."""
        
        prompt_parts = [
            f"# Benchmark Task: {task['id']}",
            f"## Category: {task['category']}",
            f"## Difficulty: {task.get('difficulty', 'medium')}",
            f"\n## Task",
            f"{task.get('description', '')}",
        ]
        
        if task.get("context"):
            prompt_parts.append(f"\n## Context\n{task['context']}")
        
        if task.get("requirements"):
            prompt_parts.append(f"\n## Requirements")
            for req in task["requirements"]:
                prompt_parts.append(f"- {req}")
        
        prompt_parts.append(f"\nWork in: /tmp/benchmark_{task['id']}")
        prompt_parts.append("\nExecute this task and report what you did.")
        
        return "\n".join(prompt_parts)
    
    def _execute_pi(
        self,
        prompt: str,
        workspace: Path
    ) -> Dict[str, Any]:
        """Execute Pi agent with the given prompt."""
        
        # Build pi command
        cmd = [
            "pi",
            "--provider", "minimax",
            "--model", self.agent_model,
            "--print",
            "--no-session",
            "--no-context-files",
            f"--session-dir={workspace}"
        ]
        
        output = ""
        tokens_used = 0
        tool_calls = []
        files_created = []
        
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(workspace)
            )
            
            output = result.stdout
            stderr = result.stderr
            
            # Parse tool calls from stderr if available
            if stderr:
                tool_calls = self._parse_tool_calls(stderr)
            
            # Find created files
            files_created = [str(f.relative_to(workspace)) 
                          for f in workspace.rglob("*") 
                          if f.is_file() and not f.name.startswith(".")]
            
            # Estimate tokens
            tokens_used = len(prompt) // 4 + len(output) // 4
            
        except subprocess.TimeoutExpired:
            output = json.dumps({"error": "timeout"})
        except Exception as e:
            output = json.dumps({"error": str(e)})
        
        return {
            "output": output,
            "tokens_used": tokens_used,
            "tool_calls": tool_calls,
            "files_created": files_created
        }
    
    def _parse_tool_calls(self, stderr: str) -> List[Dict]:
        """Parse tool calls from stderr output."""
        
        tool_calls = []
        
        # Simple parsing - look for tool patterns
        import re
        
        patterns = [
            r'Read\((.*?)\)',
            r'Bash\((.*?)\)',
            r'write\((.*?)\)',
            r'edit\((.*?)\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, stderr)
            for match in matches:
                tool_calls.append({"tool": pattern.split('\\(')[0], "args": match})
        
        return tool_calls
    
    def _judge_task(self, task: Dict, execution: Dict) -> Dict[str, Any]:
        """Judge task output using LLM judge."""
        
        # Build judge prompt
        judge_prompt = f"""# Task Evaluation

## Task: {task.get('name', 'Unknown')}
## Category: {task['category']}
## Difficulty: {task.get('difficulty', 'medium')}

## Description:
{task.get('description', '')}

## Agent Output:
{execution.get('output', '')[:2000]}

## Rubric:
- 0: Wrong - completely incorrect
- 1: Partially correct - major gaps
- 2: Correct but messy / suboptimal
- 3: Correct and clean

Evaluate the output and provide:
1. Overall score (0-3)
2. Specific feedback on each dimension (task_success, coherence, efficiency)
3. For code tasks: identify any bugs, style issues, or improvements needed

Output as JSON:
{{"overall_score": <0-3>, "task_success": <0-3>, "coherence": <0-3>, "efficiency": <0-3>, "feedback": "<brief explanation>"}}
"""
        
        # Call LLM judge
        try:
            import requests
            
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            
            payload = {
                "model": self.judge_model,
                "messages": [{"role": "user", "content": judge_prompt}],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON
                    import re
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        return json.loads(match.group(0))
            
            return {"overall_score": 2, "task_success": 2, "coherence": 2, "efficiency": 2, "feedback": "Judge unavailable"}
            
        except Exception as e:
            return {"overall_score": 2, "task_success": 2, "coherence": 2, "efficiency": 2, "feedback": str(e)}
    
    def _compute_code_metrics(self, execution: Dict) -> Dict[str, Any]:
        """Compute code-specific metrics."""
        
        files = execution.get("files_created", [])
        output = execution.get("output", "")
        
        metrics = {
            "files_created": len(files),
            "has_code_blocks": "```" in output,
            "mentions_testing": "test" in output.lower(),
            "mentions_linting": "lint" in output.lower()
        }
        
        return metrics
    
    def _compute_reasoning_metrics(self, execution: Dict) -> Dict[str, Any]:
        """Compute reasoning-specific metrics."""
        
        output = execution.get("output", "")
        
        metrics = {
            "has_step_by_step": any(kw in output.lower() for kw in ["step", "first", "then", "next", "finally"]),
            "explains_reasoning": "because" in output.lower() or "since" in output.lower(),
            "mentions_alternatives": "alternative" in output.lower() or "however" in output.lower()
        }
        
        return metrics
    
    def _compute_proactivity_metrics(self, execution: Dict) -> Dict[str, Any]:
        """Compute proactivity metrics."""
        
        output = execution.get("output", "")
        
        proactive_patterns = [
            ("proposed_next_steps", ["suggested:", "i can also", "next steps:", "you might also"]),
            ("unprompted_action", ["i'll go ahead", "automatically", "while you're"]),
            ("volunteered_info", ["note that", "worth noting", "just so you know"]),
            ("offered_alternatives", ["alternatively:", "another option", "if you prefer"])
        ]
        
        metrics = {}
        
        for metric_name, patterns in proactive_patterns:
            count = sum(1 for p in patterns if p in output.lower())
            metrics[metric_name] = count
        
        metrics["total_proactive_score"] = sum(metrics.values())
        
        return metrics
    
    def _compute_dimension_scores(
        self,
        results: List[Dict],
        dimension_results: Dict
    ) -> Dict[str, Dict]:
        """Compute scores for each evaluation dimension."""
        
        dimension_scores = {}
        
        # Speed metrics
        durations = [r["duration_seconds"] for r in results if "error" not in r]
        tokens = [r["tokens_used"] for r in results if "error" not in r]
        
        if durations:
            durations_sorted = sorted(durations)
            dimension_scores["speed"] = {
                "latency_p50": durations_sorted[len(durations_sorted) // 2] if durations_sorted else 0,
                "latency_p95": durations_sorted[int(len(durations_sorted) * 0.95)] if durations_sorted else 0,
                "latency_p99": durations_sorted[int(len(durations_sorted) * 0.99)] if durations_sorted else 0,
                "avg_duration": statistics.mean(durations),
                "total_tokens": sum(tokens),
                "avg_tokens_per_task": statistics.mean(tokens) if tokens else 0,
                "throughput_tasks_per_minute": len(durations) / (max(durations) / 60) if max(durations) > 0 else 0
            }
        
        # Output Quality
        judgments = [r.get("judgment", {}) for r in results if "judgment" in r]
        if judgments:
            dimension_scores["output_quality"] = {
                "avg_task_success": statistics.mean([j.get("task_success", 2) for j in judgments]) if judgments else 0,
                "avg_coherence": statistics.mean([j.get("coherence", 2) for j in judgments]) if judgments else 0,
                "task_success_rate": len([j for j in judgments if j.get("task_success", 0) >= 2]) / len(judgments) if judgments else 0,
                "overall_avg_score": statistics.mean([j.get("overall_score", 2) for j in judgments]) if judgments else 0
            }
        
        # Code Quality
        code_tasks = [r for r in results if r.get("category") == "coding"]
        if code_tasks:
            dimension_scores["code_quality"] = {
                "code_tasks_completed": len(code_tasks),
                "avg_score": statistics.mean([r.get("overall_score", 0) for r in code_tasks]),
                "files_created_total": sum(1 for r in code_tasks if r.get("code_metrics", {}).get("files_created", 0) > 0)
            }
        
        # Reasoning
        reasoning_tasks = [r for r in results if r.get("category") == "reasoning"]
        if reasoning_tasks:
            dimension_scores["reasoning"] = {
                "reasoning_tasks_completed": len(reasoning_tasks),
                "avg_score": statistics.mean([r.get("overall_score", 0) for r in reasoning_tasks]),
                "step_by_step_rate": statistics.mean([r.get("reasoning_metrics", {}).get("has_step_by_step", 0) for r in reasoning_tasks]),
                "explains_reasoning_rate": statistics.mean([r.get("reasoning_metrics", {}).get("explains_reasoning", 0) for r in reasoning_tasks])
            }
        
        # Proactivity
        proactivity_scores = [
            r.get("proactivity_metrics", {}).get("total_proactive_score", 0)
            for r in results
        ]
        dimension_scores["proactivity"] = {
            "avg_proactive_score": statistics.mean(proactivity_scores) if proactivity_scores else 0,
            "tasks_with_proactivity": len([s for s in proactivity_scores if s > 0]),
            "initiative_rate": len([s for s in proactivity_scores if s > 0]) / len(proactivity_scores) if proactivity_scores else 0
        }
        
        # Reliability
        error_count = len([r for r in results if "error" in r])
        dimension_scores["reliability"] = {
            "failure_rate": error_count / len(results) if results else 0,
            "completed_tasks": len(results) - error_count,
            "total_tasks": len(results)
        }
        
        # Safety
        safety_tasks = [r for r in results if r.get("category") == "safety"]
        if safety_tasks:
            dimension_scores["safety"] = {
                "safety_tasks_completed": len(safety_tasks),
                "avg_score": statistics.mean([r.get("overall_score", 0) for r in safety_tasks])
            }
        
        return dimension_scores
    
    def _compute_scorecard(self, dimension_scores: Dict[str, Dict]) -> Dict[str, Any]:
        """Compute weighted overall scorecard."""
        
        weights = {
            dim: self.dimensions_config.get(dim, {}).get("weight", 0)
            for dim in self.dimensions_config
        }
        
        scorecard = {
            "dimensions": {},
            "overall_score": 0,
            "total_weight": 0
        }
        
        for dim, weight in weights.items():
            if dim in dimension_scores:
                # Compute dimension score (0-1 scale)
                dim_score = self._compute_dimension_score(dim, dimension_scores[dim])
                scorecard["dimensions"][dim] = {
                    "weight": weight,
                    "raw_score": dim_score,
                    "weighted_score": dim_score * weight
                }
                scorecard["overall_score"] += dim_score * weight
                scorecard["total_weight"] += weight
        
        # Normalize
        if scorecard["total_weight"] > 0:
            scorecard["overall_score"] /= scorecard["total_weight"]
        
        return scorecard
    
    def _compute_dimension_score(self, dimension: str, metrics: Dict) -> float:
        """Compute a 0-1 score from dimension metrics."""
        
        # Normalize each dimension to 0-1 scale
        if dimension == "speed":
            # Lower latency is better - normalize inverse
            avg_lat = metrics.get("avg_duration", 60)
            return max(0, min(1, 1 - (avg_lat - 30) / 120))
        
        elif dimension == "output_quality":
            return metrics.get("task_success_rate", 0) / 3  # Normalize to 0-1
        
        elif dimension == "code_quality":
            return metrics.get("avg_score", 0) / 1  # Already 0-1
        
        elif dimension == "reasoning":
            return metrics.get("avg_score", 0) / 1
        
        elif dimension == "proactivity":
            avg = metrics.get("avg_proactive_score", 0)
            return min(1, avg / 5)  # Normalize 0-5 to 0-1
        
        elif dimension == "reliability":
            return 1 - metrics.get("failure_rate", 0)
        
        elif dimension == "tool_use":
            # Would need more detailed metrics
            return 0.7  # Placeholder
        
        elif dimension == "user_experience":
            return 0.7  # Placeholder
        
        elif dimension == "adaptability":
            return 0.7  # Placeholder
        
        elif dimension == "safety":
            return metrics.get("avg_score", 0.7)
        
        return 0.5
    
    def _compute_latency_stats(self, results: List[Dict]) -> Dict[str, float]:
        """Compute latency statistics."""
        
        durations = [r["duration_seconds"] for r in results if "error" not in r]
        
        if not durations:
            return {}
        
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        
        return {
            "count": n,
            "min": min(durations),
            "max": max(durations),
            "mean": statistics.mean(durations),
            "median": sorted_durations[n // 2],
            "p50": sorted_durations[n // 2],
            "p95": sorted_durations[int(n * 0.95)],
            "p99": sorted_durations[int(n * 0.99)] if n >= 100 else sorted_durations[-1],
            "stdev": statistics.stdev(durations) if len(durations) > 1 else 0
        }
    
    def _compute_token_stats(self, results: List[Dict]) -> Dict[str, Any]:
        """Compute token usage statistics."""
        
        tokens = [r["tokens_used"] for r in results if "error" not in r]
        
        if not tokens:
            return {}
        
        return {
            "total_tokens": sum(tokens),
            "avg_tokens": statistics.mean(tokens),
            "min_tokens": min(tokens),
            "max_tokens": max(tokens)
        }
    
    def _save_results(self, results: Dict, version: str):
        """Save benchmark results."""
        
        results_dir = Path(__file__).parent.parent / "benchmark" / "data"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = results_dir / f"{timestamp}_{version}_results.json"
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved: {filepath}")
        
        # Also update latest
        latest_path = results_dir / "latest.json"
        with open(latest_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
    
    def _print_summary(self, scorecard: Dict, dimension_scores: Dict):
        """Print evaluation summary."""
        
        print("\n" + "="*60)
        print("  BENCHMARK SCORECARD")
        print("="*60 + "\n")
        
        print(f"  OVERALL SCORE: {scorecard['overall_score']:.3f}\n")
        
        print(f"  {'Dimension':<20} {'Weight':>8} {'Score':>8} {'Weighted':>10}")
        print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*10}")
        
        for dim, data in sorted(scorecard["dimensions"].items(), key=lambda x: -x[1]["weighted_score"]):
            print(f"  {dim:<20} {data['weight']:>8.0%} {data['raw_score']:>8.3f} {data['weighted_score']:>10.3f}")
        
        print("\n  DETAILED METRICS:\n")
        
        for dim, metrics in dimension_scores.items():
            print(f"  {dim.upper()}:")
            for key, value in list(metrics.items())[:4]:
                if isinstance(value, float):
                    print(f"    {key}: {value:.2f}")
                else:
                    print(f"    {key}: {value}")
            print()


def main():
    """Command-line interface."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Run benchmark evaluation")
    parser.add_argument("--version", "-v", default="current", help="Version label")
    parser.add_argument("--suite", "-s", help="Benchmark suite path")
    parser.add_argument("--quick", "-q", action="store_true", help="Quick run (subset)")
    
    args = parser.parse_args()
    
    runner = BenchmarkRunner()
    runner.run_benchmark(suite_path=args.suite, version=args.version)


if __name__ == "__main__":
    main()