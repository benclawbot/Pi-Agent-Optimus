#!/usr/bin/env python3
"""
Chunked Evaluation Runner
========================
Runs evaluation tasks in configurable chunks with context reset between chunks.
Designed for environments with time limits (e.g., 5-minute task limits).

Usage:
    # Run all 10 quick tasks in chunks of 3
    python3 run_chunked.py --mode quick --chunk-size 3

    # Run specific chunk
    python3 run_chunked.py --mode quick --chunk-size 3 --chunk-index 0

    # Run category with custom chunk size
    python3 run_chunked.py --category refactor --chunk-size 2 --chunk-index 1

    # Collect and aggregate all chunks
    python3 run_chunked.py --aggregate --results-dir results/pi
"""

import argparse
import json
import sys
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "scripts"))

from task_runner import TaskRunner
from judge import Judge
from metrics import MetricsCollector
from proactivity import ProactivityDetector
from reporter import Reporter


class ChunkedEvaluator:
    """Runs evaluation in chunks with checkpointing for resilience."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = SCRIPT_DIR / "config.json"

        with open(config_path) as f:
            self.config = json.load(f)

        self.eval_config = self.config["evaluation"]
        self.agent_id = self.eval_config.get("targetAgent", "pi")
        self.results_dir = SCRIPT_DIR / "results" / self.agent_id
        self.results_dir.mkdir(exist_ok=True)
        self.chunks_dir = SCRIPT_DIR / "results" / f"{self.agent_id}_chunks"
        self.chunks_dir.mkdir(exist_ok=True)

    def run_chunk(
        self,
        mode: str = "quick",
        category: str = None,
        chunk_size: int = 3,
        chunk_index: int = 0,
    ) -> Dict[str, Any]:
        """Run a single chunk of tasks."""
        tasks = self._load_tasks(mode, category)
        total_tasks = len(tasks)

        start_idx = chunk_index * chunk_size
        end_idx = min(start_idx + chunk_size, total_tasks)

        if start_idx >= total_tasks:
            print(f"No tasks in chunk {chunk_index} (start_idx={start_idx} >= {total_tasks})")
            return {"error": "no_tasks", "chunk_index": chunk_index}

        chunk_tasks = tasks[start_idx:end_idx]
        print(f"\n{'='*60}")
        print(f"  CHUNK {chunk_index}")
        print(f"  Tasks {start_idx}-{end_idx-1} of {total_tasks}")
        print(f"  Size: {len(chunk_tasks)} tasks")
        print(f"{'='*60}\n")

        task_runner = TaskRunner(self.config)
        judge = Judge(self.config)
        metrics = MetricsCollector(self.config)
        proactivity_detector = ProactivityDetector(self.config)

        results = []
        for i, task in enumerate(chunk_tasks, start_idx + 1):
            task_start = datetime.now()
            print(f"[{i}/{total_tasks}] {task['name']}...", end=" ", flush=True)

            result = self._execute_task(
                task, task_runner, judge, metrics, proactivity_detector
            )
            results.append(result)

            score = result.get("overall_score", 0)
            status = "✓" if score >= 0.6 else "✗"
            elapsed = (datetime.now() - task_start).total_seconds()
            print(f"→ {score:.2f} {status} ({elapsed:.0f}s)")

            # Checkpoint after each task
            self._save_chunk_results(chunk_index, results)

        summary = self._aggregate_results(results)
        self._save_chunk_results(chunk_index, results, summary)

        print(f"\nChunk {chunk_index} complete: {summary['overall_score']:.2%} overall")
        return {"results": results, "summary": summary, "chunk_index": chunk_index}

    def _load_tasks(self, mode: str, category: str) -> List[Dict]:
        """Load tasks from synthetic and historical pools."""
        limit = self.eval_config.get("syntheticCount", 20) // 2 if mode == "quick" else self.eval_config.get("syntheticCount", 20)
        hist_limit = self.eval_config.get("historicalCount", 10) // 2 if mode == "quick" else self.eval_config.get("historicalCount", 10)

        tasks = []
        synthetic_dir = SCRIPT_DIR / "tasks" / "synthetic"
        if category:
            synthetic_dir = synthetic_dir / category

        if synthetic_dir.exists():
            task_files = list(synthetic_dir.glob("*.json")) if category else list(synthetic_dir.rglob("*.json"))
            for task_file in task_files:
                if len(tasks) >= limit:
                    break
                with open(task_file) as f:
                    task = json.load(f)
                    task["source"] = "synthetic"
                    tasks.append(task)

        hist_dir = SCRIPT_DIR / "tasks" / "historical"
        if hist_dir.exists():
            for task_file in hist_dir.glob("*.json"):
                if len(tasks) >= limit + hist_limit:
                    break
                with open(task_file) as f:
                    task = json.load(f)
                    if category and task.get("category") != category:
                        continue
                    task["source"] = "historical"
                    tasks.append(task)

        return tasks

    def _execute_task(self, task, task_runner, judge, metrics, proactivity_detector) -> Dict:
        """Execute a single task."""
        start_time = datetime.now()
        execution = task_runner.run(task)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        metrics_data = metrics.extract(execution)
        proactivity_data = proactivity_detector.analyze(execution["trace"], execution["output"])

        judge_scores = judge.evaluate(
            task, execution["output"], execution["files_created"],
            execution.get("file_contents", {}), execution.get("validation", {})
        )

        token_data = execution.get("token_data", {})
        memory_data = execution.get("memory_data", {})
        validation = execution.get("validation", {})
        token_efficiency = self._compute_token_efficiency(token_data, task)
        memory_retrieval = self._compute_memory_retrieval(memory_data, execution["output"], task)

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

    def _compute_overall_score(self, metrics_data, proactivity_data, judge_scores,
                               token_efficiency, memory_retrieval, task, validation) -> float:
        """Compute weighted overall score."""
        if metrics_data.get("timed_out") or metrics_data.get("execution_failed"):
            return 0.0

        dim_weights = {
            "speed": 0.08, "output_quality": 0.08, "code_quality": 0.08,
            "reasoning": 0.08, "adaptability": 0.08, "proactivity": 0.08,
            "reliability": 0.08, "tool_use": 0.08, "user_experience": 0.08,
            "safety": 0.08, "token_efficiency": 0.08, "memory_retrieval": 0.08,
        }

        cq = judge_scores.get("code_quality", 3) / 5.0
        corr = judge_scores.get("correctness", 3) / 5.0
        safety = judge_scores.get("safety", 4) / 5.0
        speed = min(metrics_data.get("speed_score", 1.0), 1.0)
        validation_score = validation.get("score", 0.5)
        code_quality = (cq * 0.5) + (validation_score * 0.5)
        output_quality = (corr * 0.35) + (validation_score * 0.65)
        proactivity = proactivity_data.get("score", 0) / 5.0
        reliability = min(1.0, metrics_data.get("reliability_score", 0.8))
        tool_use = min(1.0, metrics_data.get("tool_efficiency", 0.7))
        token_eff = token_efficiency.get("score", 0.5)
        memory = memory_retrieval.get("score", 0.5)

        scores = {
            "speed": speed, "output_quality": output_quality, "code_quality": code_quality,
            "reasoning": (corr + output_quality) / 2, "adaptability": output_quality,
            "proactivity": proactivity, "reliability": reliability, "tool_use": tool_use,
            "user_experience": 0.7, "safety": safety, "token_efficiency": token_eff,
            "memory_retrieval": memory,
        }

        total_weight = sum(dim_weights.values())
        overall = sum(scores[k] * dim_weights[k] for k in dim_weights) / total_weight

        grade = validation.get("grade")
        if grade == "fail":
            overall = min(overall, 0.45)
        elif grade == "partial":
            overall = min(overall, 0.7)
        elif grade == "low_evidence":
            overall = min(overall, 0.75)

        return round(overall, 3)

    def _compute_token_efficiency(self, token_data: Dict, task: Dict) -> Dict:
        total = token_data.get("total_tokens", 0)
        desc_len = len((task.get("description") or "") + (task.get("context") or ""))
        baseline = max(500, desc_len * 3)
        ratio = total / baseline if baseline > 0 and total > 0 else 1.0
        return {
            "score": min(1.0, max(0.3, 1.0 - abs(ratio - 1.0) * 0.2)),
            "total_tokens": total,
            "ratio": ratio,
            "waste": "ideal" if 0.5 <= ratio <= 1.5 else "verbose" if ratio > 2 else "brief",
        }

    def _compute_memory_retrieval(self, memory_data: Dict, output: str, task: Dict) -> Dict:
        score = 0.5
        if memory_data.get("cache_hit"):
            score += 0.15
        if memory_data.get("cross_session_recall"):
            score += 0.2
        return {"score": min(1.0, score), "cache_hit": memory_data.get("cache_hit", False)}

    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        if not results:
            return {"overall_score": 0}
        return {
            "tasks_run": len(results),
            "overall_score": sum(r["overall_score"] for r in results) / len(results),
            "code_quality_avg": sum(r["judge_scores"].get("code_quality", 0) for r in results) / len(results),
            "proactivity_avg": sum(r["proactivity"].get("score", 0) for r in results) / len(results),
            "validation_avg": sum(r.get("validation", {}).get("score", 0.5) for r in results) / len(results),
            "objective_pass_rate": sum(1 for r in results if r.get("validation", {}).get("grade") == "pass") / len(results),
            "avg_duration_seconds": sum(r["duration_seconds"] for r in results) / len(results),
        }

    def _save_chunk_results(self, chunk_index: int, results: List[Dict], summary: Dict = None):
        """Save chunk results to checkpoint file."""
        chunk_file = self.chunks_dir / f"chunk_{chunk_index:03d}.json"
        data = {
            "chunk_index": chunk_index,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": summary or self._aggregate_results(results),
        }
        with open(chunk_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def aggregate_all_chunks(self) -> Dict[str, Any]:
        """Aggregate all completed chunks into final results."""
        chunk_files = sorted(self.chunks_dir.glob("chunk_*.json"))
        if not chunk_files:
            return {"error": "no_chunks_found"}

        all_results = []
        for chunk_file in chunk_files:
            with open(chunk_file) as f:
                chunk_data = json.load(f)
                all_results.extend(chunk_data.get("results", []))

        summary = self._aggregate_results(all_results)
        summary["chunks_aggregated"] = len(chunk_files)
        summary["total_tasks"] = len(all_results)

        # Save final aggregated results
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        final_file = self.results_dir / f"{timestamp}_results.json"
        with open(final_file, "w") as f:
            json.dump({"timestamp": timestamp, "summary": summary, "results": all_results}, f, indent=2, default=str)

        # Generate report
        self._generate_report(all_results, summary, timestamp)

        print(f"\n{'='*60}")
        print(f"  AGGREGATED RESULTS")
        print(f"  Chunks: {len(chunk_files)}")
        print(f"  Tasks: {len(all_results)}")
        print(f"  Overall: {summary['overall_score']:.2%}")
        print(f"  Pass rate: {summary['objective_pass_rate']:.1%}")
        print(f"{'='*60}\n")

        return {"summary": summary, "total_tasks": len(all_results), "final_file": str(final_file)}

    def _generate_report(self, results: List[Dict], summary: Dict, timestamp: str):
        """Generate markdown and HTML reports."""
        try:
            reporter = Reporter(self.config)
            md_report = reporter.markdown(results, summary)
            md_path = SCRIPT_DIR / "reports" / self.agent_id / f"{timestamp}_evaluation.md"
            md_path.parent.mkdir(exist_ok=True)
            with open(md_path, "w") as f:
                f.write(md_report)
            print(f"   → Markdown: {md_path}")
        except Exception as e:
            print(f"   → Report generation skipped: {e}")

    def run_all_chunks(
        self,
        mode: str = "quick",
        category: str = None,
        chunk_size: int = 3,
        max_chunks: int = 10,
    ) -> Dict[str, Any]:
        """Run all chunks sequentially, collecting results."""
        tasks = self._load_tasks(mode, category)
        total_tasks = len(tasks)
        total_chunks = (total_tasks + chunk_size - 1) // chunk_size
        total_chunks = min(total_chunks, max_chunks)

        print(f"\nRunning {total_tasks} tasks in {total_chunks} chunks of {chunk_size}")

        all_results = []
        for i in range(total_chunks):
            print(f"\n--- Chunk {i+1}/{total_chunks} ---")
            chunk_result = self.run_chunk(
                mode=mode, category=category,
                chunk_size=chunk_size, chunk_index=i
            )
            if "error" in chunk_result:
                break
            all_results.extend(chunk_result["results"])

        summary = self._aggregate_results(all_results)
        return self.aggregate_all_chunks()


def main():
    parser = argparse.ArgumentParser(description="Chunked Evaluation Runner")
    parser.add_argument("--mode", choices=["full", "quick"], default="quick")
    parser.add_argument("--category", choices=["code-quality", "debug", "architecture", "refactor"])
    parser.add_argument("--chunk-size", type=int, default=3, help="Tasks per chunk (default: 3 ≈ 5 min)")
    parser.add_argument("--chunk-index", type=int, help="Run specific chunk only")
    parser.add_argument("--aggregate", action="store_true", help="Aggregate all chunks into final results")
    parser.add_argument("--agent", choices=["pi", "hermes"], default="pi")
    parser.add_argument("--run-all", action="store_true", help="Run all chunks sequentially")
    parser.add_argument("--max-chunks", type=int, default=10, help="Max chunks to run in --run-all mode")

    args = parser.parse_args()

    evaluator = ChunkedEvaluator()
    evaluator.eval_config["targetAgent"] = args.agent

    if args.aggregate:
        result = evaluator.aggregate_all_chunks()
        print(json.dumps(result, indent=2, default=str))
    elif args.chunk_index is not None:
        result = evaluator.run_chunk(args.mode, args.category, args.chunk_size, args.chunk_index)
        print(json.dumps(result, indent=2, default=str))
    elif args.run_all:
        result = evaluator.run_all_chunks(args.mode, args.category, args.chunk_size, args.max_chunks)
        print(json.dumps(result, indent=2, default=str))
    else:
        # Default: run single chunk
        result = evaluator.run_chunk(args.mode, args.category, args.chunk_size, 0)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
