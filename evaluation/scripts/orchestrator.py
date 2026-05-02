#!/usr/bin/env python3
"""
Agent Evaluation Framework - Orchestrator
=========================================
Main entry point for evaluating Pi Agent Optimus or Hermes.
Can be run manually (on-demand) or triggered by cron (nightly schedule).

Usage:
    python3 orchestrator.py run [--agent pi|hermes] [--full|--quick] [--category <category>]
    python3 orchestrator.py compare
    python3 orchestrator.py trends
    python3 orchestrator.py --schedule (cron entry point)
"""

import json
import sys
import os
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from task_runner import TaskRunner
from judge import Judge
from metrics import MetricsCollector
from proactivity import ProactivityDetector
from reporter import Reporter

class EvaluationOrchestrator:
    """Coordinates the entire evaluation pipeline."""
    
    def __init__(self, config_path: str = None, agent: str = None):
        if config_path is None:
            config_path = SCRIPT_DIR.parent / "config.json"
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.eval_config = self.config["evaluation"]
        self.metrics_config = self.config["metrics"]
        self.reporting_config = self.config["reporting"]

        self.set_agent(agent or self.eval_config.get("targetAgent", "pi"))

    def set_agent(self, agent: str):
        """Select the agent under test and configure result/report output paths."""
        agents = self.eval_config.get("agents", {})
        if agent not in agents:
            raise ValueError(f"Unknown agent {agent!r}. Expected one of: {', '.join(sorted(agents))}")

        agent_config = agents[agent]
        self.agent_id = agent
        self.agent_name = agent_config.get("name", agent)
        self.eval_config["targetAgent"] = agent
        self.eval_config["agentModel"] = agent_config.get("model", self.eval_config.get("agentModel"))
        self.config["activeAgent"] = agent_config

        self.results_dir = SCRIPT_DIR.parent / "results" / agent
        self.results_dir.mkdir(exist_ok=True)
        self.reports_dir = SCRIPT_DIR.parent / "reports" / agent
        self.reports_dir.mkdir(exist_ok=True)

        self.tasks_dir = SCRIPT_DIR.parent / "tasks"
        self.secret_patterns = [
            re.compile(r"\bsl\.u\.[A-Za-z0-9_\-.]{40,}\b"),
            re.compile(r"\b(?:sk|ghp|gho|github_pat|xox[baprs])-?[A-Za-z0-9_\-]{20,}\b"),
            re.compile(r"\b[A-Za-z0-9_\-]{80,}\b"),
        ]
        
    def run(self, mode: str = "full", category: str = None) -> Dict[str, Any]:
        """
        Execute the evaluation pipeline.
        
        Args:
            mode: "full" (40 tasks) or "quick" (10 tasks)
            category: Optional filter (code-quality, debug, architecture, refactor)
        
        Returns:
            Dict containing all results and scores
        """
        print(f"\n{'='*60}")
        print(f"  {self.agent_name.upper()} EVALUATION")
        print(f"  Mode: {mode} | Category: {category or 'all'}")
        print(f"  Started: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")
        
        # Load tasks
        tasks = self._load_tasks(mode, category)
        print(f"📋 Loaded {len(tasks)} tasks\n")
        
        # Initialize components
        task_runner = TaskRunner(self.config)
        judge = Judge(self.config)
        metrics = MetricsCollector(self.config)
        proactivity_detector = ProactivityDetector(self.config)
        
        # Run tasks
        results = []
        for i, task in enumerate(tasks, 1):
            print(f"[{i}/{len(tasks)}] Running: {task['name']}...")
            
            result = self._execute_task(
                task, task_runner, judge, metrics, proactivity_detector
            )
            results.append(result)
            
            # Progress indicator
            score = result.get("overall_score", 0)
            status = "✓" if score >= 0.6 else "✗"
            print(f"      → Score: {score:.2f} {status}\n")
        
        # Aggregate results
        summary = self._aggregate_results(results)
        
        # Save results to disk
        self._save_results(results, summary)
        
        # Generate reports
        self._generate_reports(results, summary)
        
        # Check for skill evolution triggers
        self._check_skill_evolution(results)
        
        print(f"\n{'='*60}")
        print(f"  EVALUATION COMPLETE")
        print(f"  Overall Score: {summary['overall_score']:.2f}")
        print(f"  Speed Improvement: {summary['speed_improvement_pct']:.1f}%")
        print(f"  Proactivity Avg: {summary['proactivity_avg']:.2f}")
        print(f"{'='*60}\n")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "category": category,
            "tasks": len(tasks),
            "results": results,
            "summary": summary
        }
    
    def _execute_task(
        self,
        task: Dict,
        task_runner: TaskRunner,
        judge: Judge,
        metrics: MetricsCollector,
        proactivity_detector: ProactivityDetector
    ) -> Dict[str, Any]:
        """Execute a single task and collect all metrics."""
        
        start_time = datetime.now()
        
        # Run task against the configured agent
        execution = task_runner.run(task)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Extract metrics
        metrics_data = metrics.extract(execution)
        
        # Detect proactivity
        proactivity_data = proactivity_detector.analyze(
            execution["trace"],
            execution["output"]
        )
        
        # Judge with LLM
        judge_scores = judge.evaluate(
            task,
            execution["output"],
            execution["files_created"],
            execution.get("file_contents", {}),
            execution.get("validation", {})
        )
        
        # Token efficiency & memory retrieval
        token_data = execution.get("token_data", {})
        memory_data = execution.get("memory_data", {})
        validation = execution.get("validation", {})
        token_efficiency = self._compute_token_efficiency(token_data, task)
        memory_retrieval = self._compute_memory_retrieval(memory_data, execution["output"], task)

        # Combine all data into result
        return {
            "task_name": task["name"],
            "task_category": task["category"],
            "agent": self.agent_id,
            "duration_seconds": duration,
            "files_created": execution.get("files_created", []),
            "metrics": metrics_data,
            "proactivity": proactivity_data,
            "judge_scores": judge_scores,
            "token_data": token_data,
            "memory_data": memory_data,
            "validation": validation,
            "token_efficiency": token_efficiency,
            "memory_retrieval": memory_retrieval,
            "overall_score": self._compute_overall_score(
                metrics_data, proactivity_data, judge_scores,
                token_efficiency, memory_retrieval, task, validation
            )
        }
    
    def _compute_overall_score(
        self,
        metrics_data: Dict,
        proactivity_data: Dict,
        judge_scores: Dict,
        token_efficiency: Dict = None,
        memory_retrieval: Dict = None,
        task: Dict = None,
        validation: Dict = None
    ) -> float:
        """Compute weighted overall score across all 12 dimensions."""
        if (
            metrics_data.get("timed_out")
            or metrics_data.get("execution_failed")
            or judge_scores.get("judge_error")
            or judge_scores.get("error")
        ):
            return 0.0

        # Fallback for old 3-arg calls
        token_efficiency = token_efficiency or {"score": 0.5}
        memory_retrieval = memory_retrieval or {"score": 0.5}
        task = task or {"category": "", "description": "", "name": ""}
        validation = validation or {"score": 0.5, "grade": "low_evidence"}

        dim_weights = {
            "speed": 0.08,
            "output_quality": 0.08,
            "code_quality": 0.08,
            "reasoning": 0.08,
            "adaptability": 0.08,
            "proactivity": 0.08,
            "reliability": 0.08,
            "tool_use": 0.08,
            "user_experience": 0.08,
            "safety": 0.08,
            "token_efficiency": 0.08,
            "memory_retrieval": 0.08,
        }

        cq = judge_scores.get("code_quality", 3)
        corr = judge_scores.get("correctness", 3)
        coh = judge_scores.get("coherence", 3)
        safety = judge_scores.get("safety", 4)

        speed = min(metrics_data.get("speed_score", 1.0), 1.0)
        validation_score = validation.get("score", 0.5)
        judge_code_quality = cq / 5.0
        judge_output_quality = (corr/5.0 + coh/5.0) / 2
        code_quality = (judge_code_quality * 0.5) + (validation_score * 0.5)
        output_quality = (judge_output_quality * 0.35) + (validation_score * 0.65)
        reasoning = (corr/5.0 + output_quality) / 2
        adaptability = output_quality
        proactivity = proactivity_data.get("score", 0) / 5.0
        reliability = min(1.0, metrics_data.get("reliability_score", 0.8))
        tool_use = min(1.0, metrics_data.get("tool_efficiency", 0.7))

        # User experience: feedback-based
        feedback = metrics_data.get("feedback_instances", 0)
        tool_loops = metrics_data.get("tool_loops", 0)
        judge_corrections = judge_scores.get("corrections_needed", 0)
        task_score = cq / 5.0

        ue = 1.0
        ue -= min(feedback * 0.15, 0.6)
        ue -= min(tool_loops * 0.10, 0.3)
        ue -= min(judge_corrections * 0.20, 0.4)
        if task_score >= 0.6 and feedback == 0 and tool_loops == 0:
            ue = min(1.0, ue + 0.1)
        user_experience = max(0.05, ue)

        safety_score = safety / 5.0
        token_eff = token_efficiency.get("score", 0.5)
        memory = memory_retrieval.get("score", 0.5)

        scores = {
            "speed": speed,
            "output_quality": output_quality,
            "code_quality": code_quality,
            "reasoning": reasoning,
            "adaptability": adaptability,
            "proactivity": proactivity,
            "reliability": reliability,
            "tool_use": tool_use,
            "user_experience": user_experience,
            "safety": safety_score,
            "token_efficiency": token_eff,
            "memory_retrieval": memory,
        }

        total_weight = sum(dim_weights.values())
        overall = sum(scores[k] * dim_weights[k] for k in dim_weights) / total_weight
        if validation.get("grade") == "fail":
            overall = min(overall, 0.45)
        elif validation.get("grade") == "partial":
            overall = min(overall, 0.7)
        elif validation.get("grade") == "low_evidence":
            overall = min(overall, 0.75)
        return round(overall, 3)
    
    def _load_tasks(self, mode: str, category: str) -> List[Dict]:
        """Load tasks from synthetic and historical pools."""
        
        limit = self.eval_config.get("syntheticCount", 20) // 2 if mode == "quick" else self.eval_config.get("syntheticCount", 20)
        hist_limit = self.eval_config.get("historicalCount", 10) // 2 if mode == "quick" else self.eval_config.get("historicalCount", 10)
        
        tasks = []
        
        # Load synthetic tasks
        synthetic_dir = self.tasks_dir / "synthetic"
        if category:
            synthetic_dir = synthetic_dir / category
        
        if synthetic_dir.exists():
            task_files = synthetic_dir.glob("*.json") if category else synthetic_dir.rglob("*.json")
            for task_file in task_files:
                if len(tasks) >= limit:
                    break
                with open(task_file) as f:
                    task = json.load(f)
                    if self._is_unsafe_task(task):
                        continue
                    task["source"] = "synthetic"
                    tasks.append(task)
        
        # Load historical tasks
        hist_dir = self.tasks_dir / "historical"
        if hist_dir.exists():
            for task_file in hist_dir.glob("*.json"):
                if len(tasks) >= limit + hist_limit:
                    break
                with open(task_file) as f:
                    task = json.load(f)
                    if category and task.get("category") != category:
                        continue
                    if self._is_unsafe_task(task):
                        continue
                    if not self._is_evaluable_task(task):
                        continue
                    task["source"] = "historical"
                    tasks.append(task)
        
        # A real evaluation must fail loudly if no real tasks are available.
        # Silent placeholders make the reports look valid while measuring nothing.
        if not tasks:
            raise RuntimeError(
                f"No evaluable tasks found for mode={mode!r}, category={category!r}. "
                "Add synthetic tasks under evaluation/tasks/synthetic/ or curated historical tasks with requirements/expected criteria."
            )
        
        return tasks

    def _is_unsafe_task(self, task: Dict) -> bool:
        """Skip tasks containing credentials or raw token dumps."""
        text = "\n".join(str(task.get(k, "")) for k in ["name", "description", "prompt", "context"])
        lowered = text.lower().strip()
        if lowered.startswith(("the token is", "token is", "api key", "apikey", "secret is")):
            return True
        return any(pattern.search(text) for pattern in self.secret_patterns)

    def _is_evaluable_task(self, task: Dict) -> bool:
        """Require objective criteria for historical/chat-derived tasks."""
        if task.get("source") != "historical":
            return True
        return bool(task.get("expected") or task.get("requirements"))
    
    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Aggregate results into summary statistics."""
        
        if not results:
            return {"overall_score": 0, "speed_improvement_pct": 0}
        
        code_quality_avg = sum(r["judge_scores"].get("code_quality", 0) for r in results) / len(results)
        proactivity_avg = sum(r["proactivity"].get("score", 0) for r in results) / len(results)
        validation_avg = sum(r.get("validation", {}).get("score", 0.5) for r in results) / len(results)
        objective_pass_rate = (
            sum(1 for r in results if r.get("validation", {}).get("grade") == "pass") / len(results)
        )
        
        avg_duration = sum(r["duration_seconds"] for r in results) / len(results)
        
        # Compute speed improvement vs baseline
        speed_improvement_pct = self._compute_speed_improvement(results)
        
        return {
            "tasks_run": len(results),
            "overall_score": sum(r["overall_score"] for r in results) / len(results),
            "code_quality_avg": code_quality_avg,
            "proactivity_avg": proactivity_avg,
            "validation_avg": validation_avg,
            "objective_pass_rate": objective_pass_rate,
            "avg_duration_seconds": avg_duration,
            "speed_improvement_pct": speed_improvement_pct
        }
    
    def _compute_speed_improvement(self, results: List[Dict]) -> float:
        """Compute speed improvement percentage vs baseline."""
        
        # Get baseline from historical data or default
        baseline_file = self.results_dir / "baseline.json"
        
        if baseline_file.exists():
            with open(baseline_file) as f:
                baseline = json.load(f)
                baseline_time = baseline.get("median_duration", 60)
        else:
            baseline_time = 60  # Default 60 second baseline
        
        avg_time = sum(r["duration_seconds"] for r in results) / len(results)
        
        improvement = (baseline_time - avg_time) / baseline_time * 100
        return improvement
    
    def _compute_token_efficiency(self, token_data: Dict, task: Dict) -> Dict[str, Any]:
        """
        Compute token efficiency score (0-1).

        Constraints:
          - Penalize OVERUSE: >5x description length = wasteful verbose prompts
          - Penalize UNDERUSE: <1x description length = rushed/thoughtless
          - Reward HIGH DENSITY: more output per token (quality over quantity)
          - Reward CACHE: cached tokens = context reuse = efficient
        """
        total = token_data.get("total_tokens", 0)
        input_t = token_data.get("input_tokens", 0)
        output_t = token_data.get("output_tokens", 0)
        cached = token_data.get("cached_tokens", 0)

        desc_len = len((task.get("description") or "") + (task.get("context") or ""))
        input_baseline = max(500, desc_len * 3)
        output_baseline = input_baseline * 2
        total_baseline = input_baseline + output_baseline

        if total == 0:
            return {
                "score": 0.3,
                "total_tokens": 0,
                "input_baseline": round(input_baseline),
                "output_baseline": round(output_baseline),
                "ratio": 0,
                "density": 0,
                "cache_rate": 0,
                "waste": "no data"
            }

        ratio = total / total_baseline if total_baseline > 0 else 1.0

        if 0.5 <= ratio <= 1.5:
            efficiency = 1.0
        elif 0.3 <= ratio < 0.5:
            efficiency = 0.5 + (ratio - 0.3) / 0.2 * 0.5
        elif 1.5 < ratio <= 2.5:
            efficiency = 1.0 - (ratio - 1.5) / 1.0 * 0.3
        else:
            efficiency = max(0.2, 0.7 - (ratio - 2.5) * 0.15) if ratio > 2.5 else max(0.2, ratio)

        density = output_t / input_t if input_t > 0 else 0.5
        density_score = min(1.0, density / 0.3)
        cache_rate = cached / input_t if input_t > 0 else 0
        cache_bonus = min(0.1, cache_rate * 0.15)

        final = efficiency * 0.7 + density_score * 0.2 + cache_bonus * 0.1
        final = min(1.0, final)

        if ratio < 0.5:
            waste = "rushed" if ratio < 0.3 else "brief"
        elif ratio > 2.0:
            waste = "verbose" if ratio < 3.0 else "wasteful"
        else:
            waste = "ideal"

        return {
            "score": round(final, 3),
            "total_tokens": total,
            "input_baseline": round(input_baseline),
            "output_baseline": round(output_baseline),
            "ratio": round(ratio, 2),
            "density": round(density, 2),
            "cache_rate": round(cache_rate, 2),
            "waste": waste,
        }

    def _compute_memory_retrieval(self, memory_data: Dict, output: str, task: Dict) -> Dict[str, Any]:
        """
        Compute memory retrieval score (0-1).
        Measures: vault speed, cross-session recall, context freshness, internet avoidance.
        """
        score = 0.5

        load_ms = memory_data.get("context_load_ms", 0)
        if load_ms > 0:
            if load_ms < 500:
                score += 0.1
            elif load_ms > 2000:
                score -= 0.1

        if memory_data.get("cache_hit", False):
            score += 0.15

        if memory_data.get("cross_session_recall", False):
            score += 0.2

        vault_reads = memory_data.get("vault_reads", 0)
        if vault_reads > 0:
            score += min(vault_reads * 0.05, 0.15)

        if not memory_data.get("internet_fetched", False):
            score += 0.1

        mem_refs = memory_data.get("memory_references", 0)
        if mem_refs > 0:
            score += min(mem_refs * 0.05, 0.15)

        freshness = memory_data.get("context_freshness", 0.5)
        score += (freshness - 0.5) * 0.2

        return {
            "score": round(min(max(score, 0), 1.0), 3),
            "vault_reads": vault_reads,
            "cache_hit": memory_data.get("cache_hit", False),
            "cross_session_recall": memory_data.get("cross_session_recall", False),
            "internet_fetched": memory_data.get("internet_fetched", False),
            "context_load_ms": load_ms,
            "memory_references": mem_refs,
            "context_freshness": memory_data.get("context_freshness", 0.0),
        }

        """Generate reports in all configured formats."""
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Markdown report
        reporter = Reporter(self.config)
        
        md_report = reporter.markdown(results, summary)
        md_path = self.reports_dir / f"{timestamp}_evaluation.md"
        with open(md_path, "w") as f:
            f.write(md_report)
        print(f"📄 Markdown report: {md_path}")
        
        # Terminal output
        reporter.terminal(summary)
        
        # HTML report
        html_report = reporter.html(results, summary)
        html_path = self.reports_dir / f"{timestamp}_evaluation.html"
        with open(html_path, "w") as f:
            f.write(html_report)
        print(f"🌐 HTML report: {html_path}")
        
        # Save results JSON
        results_path = self.results_dir / f"{timestamp}_results.json"
        with open(results_path, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "summary": summary,
                "results": results
            }, f, indent=2, default=str)
        print(f"💾 Results saved: {results_path}")

        # Update trends.json for dashboard
        try:
            from trends_api import TrendsAPI
            trends_api = TrendsAPI()
            trends_api.update_trends()
        except Exception as e:
            print(f"⚠️  Could not update trends: {e}")
    
    def _save_results(self, results: List[Dict], summary: Dict):
        """Save results JSON to disk."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        results_file = self.results_dir / f"{timestamp}_results.json"
        data = {"timestamp": timestamp, "summary": summary, "results": results}
        with open(results_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"   → Results saved: {results_file}")

    def _generate_reports(self, results: List[Dict], summary: Dict):
        """Generate markdown and HTML reports."""
        from reporter import generate_report
        output = generate_report(results, summary, self.config)
        for fmt, path in output.items():
            print(f"   → {fmt} report: {path}")

    def _check_skill_evolution(self, results: List[Dict]):
        """Check if any skill gaps require evolution."""
        
        threshold = self.config["skills"]["evolutionThreshold"]
        issues = []
        
        for result in results:
            if result["judge_scores"].get("code_quality", 5) < 3:
                issues.append({
                    "task": result["task_name"],
                    "category": result["task_category"],
                    "score": result["judge_scores"]["code_quality"]
                })
        
        if len(issues) >= threshold:
            print(f"\n⚠️  Skill evolution triggered: {len(issues)} issues detected")
            self._trigger_skill_evolution(issues)
    
    def _trigger_skill_evolution(self, issues: List[Dict]):
        """Notify that skill evolution should occur."""
        
        evolution_file = SCRIPT_DIR.parent / "skill-evolution-needed.json"
        with open(evolution_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "issues": issues,
                "suggested_action": "Review and generalize skills to handle these patterns"
            }, f, indent=2)
        print(f"   → Evolution file written: {evolution_file}")
    
    def compare(self) -> Dict[str, Any]:
        """Compare current results to previous runs."""
        
        results_files = sorted(self.results_dir.glob("*_results.json"))
        
        if len(results_files) < 2:
            print("Not enough historical data for comparison")
            return {}
        
        current = json.load(open(results_files[-1]))
        previous = json.load(open(results_files[-2]))
        
        comparison = {
            "current": current["summary"],
            "previous": previous["summary"],
            "delta": {
                "overall_score": current["summary"]["overall_score"] - previous["summary"]["overall_score"],
                "speed_improvement_pct": current["summary"]["speed_improvement_pct"] - previous["summary"]["speed_improvement_pct"],
                "proactivity_avg": current["summary"]["proactivity_avg"] - previous["summary"]["proactivity_avg"]
            }
        }
        
        print(f"\n{'='*60}")
        print(f"  COMPARISON: Current vs Previous")
        print(f"{'='*60}")
        print(f"  Overall Score:   {comparison['delta']['overall_score']:+.2f}")
        print(f"  Speed:            {comparison['delta']['speed_improvement_pct']:+.1f}%")
        print(f"  Proactivity:      {comparison['delta']['proactivity_avg']:+.2f}")
        print(f"{'='*60}\n")
        
        return comparison
    
    def trends(self) -> Dict[str, Any]:
        """Show trend analysis over historical runs."""
        
        results_files = sorted(self.results_dir.glob("*_results.json"))
        
        if len(results_files) < 3:
            print("Not enough historical data for trends (need at least 3 runs)")
            return {}
        
        trends = []
        for f in results_files[-10:]:  # Last 10 runs
            data = json.load(open(f))
            trends.append({
                "timestamp": data["timestamp"],
                "overall_score": data["summary"]["overall_score"],
                "speed_improvement_pct": data["summary"]["speed_improvement_pct"]
            })
        
        print(f"\n{'='*60}")
        print(f"  TREND ANALYSIS (Last {len(trends)} runs)")
        print(f"{'='*60}")
        for t in trends:
            print(f"  {t['timestamp'][:19]}: Score={t['overall_score']:.2f}, Speed={t['speed_improvement_pct']:+.1f}%")
        print(f"{'='*60}\n")
        
        return {"trends": trends}


def main():
    parser = argparse.ArgumentParser(
        description="Agent Evaluation Framework"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run evaluation")
    run_parser.add_argument("--agent", choices=["pi", "hermes"], default=None,
                          help="Agent to evaluate")
    run_parser.add_argument("--full", action="store_true", help="Full evaluation (40 tasks)")
    run_parser.add_argument("--quick", action="store_true", help="Quick evaluation (10 tasks)")
    run_parser.add_argument("--category", choices=["code-quality", "debug", "architecture", "refactor"],
                          help="Filter by category")
    run_parser.set_defaults(mode="full")
    
    # Compare command
    subparsers.add_parser("compare", help="Compare with previous run")
    
    # Trends command
    subparsers.add_parser("trends", help="Show trend analysis")
    
    # Schedule mode (called by cron)
    parser.add_argument("--schedule", action="store_true", help="Run in scheduled mode")
    
    args = parser.parse_args()
    
    orchestrator = EvaluationOrchestrator(agent=getattr(args, "agent", None))
    
    if args.schedule:
        print("🔄 Running in scheduled (nightly) mode...")
        orchestrator.run(mode="full")
    elif args.command == "run":
        mode = "quick" if args.quick else "full"
        orchestrator.run(mode=mode, category=args.category)
    elif args.command == "compare":
        orchestrator.compare()
    elif args.command == "trends":
        orchestrator.trends()
    else:
        # Default: run full evaluation
        orchestrator.run(mode="full")


if __name__ == "__main__":
    main()
