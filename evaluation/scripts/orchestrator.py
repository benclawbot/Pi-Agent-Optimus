#!/usr/bin/env python3
"""
Pi Agent Optimus Evaluation Framework - Orchestrator
=====================================================
Main entry point for the evaluation system.
Can be run manually (on-demand) or triggered by cron (nightly schedule).

Usage:
    python3 orchestrator.py run [--full|--quick] [--category <category>]
    python3 orchestrator.py compare
    python3 orchestrator.py trends
    python3 orchestrator.py --schedule (cron entry point)
"""

import json
import sys
import os
import argparse
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
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = SCRIPT_DIR.parent / "config.json"
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.eval_config = self.config["evaluation"]
        self.metrics_config = self.config["metrics"]
        self.reporting_config = self.config["reporting"]
        
        self.results_dir = SCRIPT_DIR.parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.tasks_dir = SCRIPT_DIR.parent / "tasks"
        
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
        print(f"  PI AGENT OPTIMUS EVALUATION")
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
        
        # Run task against Pi agent
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
            execution["files_created"]
        )
        
        # Combine all data into result
        return {
            "task_name": task["name"],
            "task_category": task["category"],
            "duration_seconds": duration,
            "metrics": metrics_data,
            "proactivity": proactivity_data,
            "judge_scores": judge_scores,
            "overall_score": self._compute_overall_score(
                metrics_data, proactivity_data, judge_scores
            )
        }
    
    def _compute_overall_score(
        self,
        metrics_data: Dict,
        proactivity_data: Dict,
        judge_scores: Dict
    ) -> float:
        """Compute weighted overall score from all components."""
        weights = self.metrics_config
        
        # Code quality score (from judge)
        code_quality = judge_scores.get("code_quality", 0) / 5.0
        
        # Speed score (normalized, 1.0 = at baseline)
        speed_score = metrics_data.get("speed_score", 1.0)
        
        # Proactivity score (normalized 0-1)
        proactivity_score = proactivity_data.get("score", 0) / 5.0
        
        # Weighted combination
        overall = (
            code_quality * weights["codeQuality"]["weight"] +
            speed_score * weights["speed"]["weight"] +
            proactivity_score * weights["proactivity"]["weight"]
        )
        
        return overall
    
    def _load_tasks(self, mode: str, category: str) -> List[Dict]:
        """Load tasks from synthetic and historical pools."""
        
        limit = self.eval_config["syntheticCount"] // 2 if mode == "quick" else self.eval_config["syntheticCount"]
        hist_limit = self.eval_config["historicalCount"] // 2 if mode == "quick" else self.eval_config["historicalCount"]
        
        tasks = []
        
        # Load synthetic tasks
        synthetic_dir = self.tasks_dir / "synthetic"
        if category:
            synthetic_dir = synthetic_dir / category
        
        if synthetic_dir.exists():
            for task_file in synthetic_dir.glob("*.json"):
                if len(tasks) >= limit:
                    break
                with open(task_file) as f:
                    task = json.load(f)
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
                    task["source"] = "historical"
                    tasks.append(task)
        
        # If no tasks found, return placeholder for testing
        if not tasks:
            tasks = self._generate_placeholder_tasks(mode)
        
        return tasks
    
    def _generate_placeholder_tasks(self, mode: str) -> List[Dict]:
        """Generate placeholder tasks for initial testing."""
        count = 10 if mode == "quick" else 20
        return [
            {
                "name": f"Placeholder Task {i}",
                "category": "code-quality",
                "description": f"Test task {i} - to be replaced with real tasks",
                "expected": "placeholder",
                "source": "generated"
            }
            for i in range(1, count + 1)
        ]
    
    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Aggregate results into summary statistics."""
        
        if not results:
            return {"overall_score": 0, "speed_improvement_pct": 0}
        
        code_quality_avg = sum(r["judge_scores"].get("code_quality", 0) for r in results) / len(results)
        proactivity_avg = sum(r["proactivity"].get("score", 0) for r in results) / len(results)
        
        avg_duration = sum(r["duration_seconds"] for r in results) / len(results)
        
        # Compute speed improvement vs baseline
        speed_improvement_pct = self._compute_speed_improvement(results)
        
        return {
            "tasks_run": len(results),
            "overall_score": sum(r["overall_score"] for r in results) / len(results),
            "code_quality_avg": code_quality_avg,
            "proactivity_avg": proactivity_avg,
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
    
    def _generate_reports(self, results: List[Dict], summary: Dict[str, Any]):
        """Generate reports in all configured formats."""
        
        reports_dir = SCRIPT_DIR.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Markdown report
        reporter = Reporter(self.config)
        
        md_report = reporter.markdown(results, summary)
        md_path = reports_dir / f"{timestamp}_evaluation.md"
        with open(md_path, "w") as f:
            f.write(md_report)
        print(f"📄 Markdown report: {md_path}")
        
        # Terminal output
        reporter.terminal(summary)
        
        # HTML report
        html_report = reporter.html(results, summary)
        html_path = reports_dir / f"{timestamp}_evaluation.html"
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
        description="Pi Agent Optimus Evaluation Framework"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run evaluation")
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
    
    orchestrator = EvaluationOrchestrator()
    
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