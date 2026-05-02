#!/usr/bin/env python3
"""
Metrics - Extracts and computes metrics from task execution.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


class MetricsCollector:
    """Collects and computes metrics from execution data."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.metrics_config = config.get("metrics", {})
        self.results_dir = Path(__file__).parent.parent / "results"
        self.baseline_file = self.results_dir / "baseline.json"
    
    def extract(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from execution data.
        
        Returns:
            Dict with computed metrics
        """
        metrics = {}
        trace = execution.get("trace", [])
        timed_out = any(entry.get("type") == "timeout" for entry in trace if isinstance(entry, dict))
        process_failed = any(entry.get("type") == "process_error" for entry in trace if isinstance(entry, dict))
        metrics["timed_out"] = timed_out
        metrics["execution_failed"] = timed_out or process_failed
        
        # Duration metrics
        metrics["duration_seconds"] = execution.get("duration", 0)
        metrics["duration_formatted"] = self._format_duration(execution.get("duration", 0))
        
        # Token metrics (from trace if available)
        metrics["tokens_used"] = self._estimate_tokens(execution)
        metrics["token_efficiency"] = self._compute_token_efficiency(metrics["tokens_used"])
        
        # Step/tool call metrics
        tool_calls = execution.get("tool_calls", [])
        metrics["step_count"] = len(tool_calls)
        metrics["tool_calls"] = self._summarize_tool_calls(tool_calls)
        
        # Turns used: count from trace (each assistant message = 1 turn)
        turns = self._count_turns(trace, execution.get("output", ""))
        metrics["turns_used"] = turns
        metrics["first_response_time"] = self._estimate_first_response_time(trace)
        
        # UX: estimate feedback instances from tool patterns
        metrics["feedback_instances"] = self._estimate_feedback_instances(
            trace, tool_calls, execution.get("output", "")
        )
        metrics["tool_loops"] = self._count_tool_loops(trace)
        
        # Speed score (compared to baseline). Failed executions must not earn
        # speed credit just because they stopped quickly or hit the timeout.
        metrics["speed_score"] = 0 if metrics["execution_failed"] else self._compute_speed_score(execution.get("duration", 0))
        
        # Code quality proxies (automated)
        metrics["code_indicators"] = self._analyze_code_indicators(execution)
        
        return metrics
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"
    
    def _estimate_tokens(self, execution: Dict[str, Any]) -> Dict[str, int]:
        """Estimate token usage from execution."""
        trace = execution.get("trace", [])
        output = execution.get("output", "")
        
        # Rough estimation: 1 token ≈ 4 chars
        output_tokens = len(output) // 4
        
        # Estimate from trace
        trace_tokens = sum(len(str(entry)) // 4 for entry in trace)
        
        return {
            "output_estimate": output_tokens,
            "trace_estimate": trace_tokens,
            "total_estimate": output_tokens + trace_tokens
        }
    
    def _compute_token_efficiency(self, tokens: Dict[str, int]) -> float:
        """
        Compute token efficiency score.
        Higher is better - more output per token.
        """
        total = tokens.get("total_estimate", 0)
        if total == 0:
            return 0.5
        return 0.8  # placeholder - real tracking via task_runner token_data
    
    def _summarize_tool_calls(self, tool_calls: List[Dict]) -> Dict[str, int]:
        """Summarize tool call patterns."""
        summary = {}
        for call in tool_calls:
            tool_name = call.get("tool", "unknown")
            summary[tool_name] = summary.get(tool_name, 0) + 1
        return summary
    
    def _count_turns(self, trace: List[Dict], output: str) -> int:
        """
        Count actual turns used from trace.
        Each 'text_response' or 'assistant' event in trace = 1 turn.
        Also counts tool-call loops as turns.
        """
        if not trace:
            # Estimate from output: each major code block ≈ 1 turn
            code_blocks = output.count("```")
            return max(1, code_blocks // 2)

        turns = 0
        for entry in trace:
            if entry.get("type") in ("text_response", "assistant", "response"):
                turns += 1
            elif entry.get("type") == "tool_call":
                prev_idx = trace.index(entry) - 1
                prev = trace[prev_idx] if prev_idx > 0 else {}
                if prev.get("type") not in ("tool_call", "tool_result"):
                    turns += 1

        return max(1, turns)
    
    def _estimate_first_response_time(self, trace: List[Dict]) -> float:
        """
        Estimate time to first usable result (file creation or answer).
        Returns fraction of total duration (0-1). Lower is better.
        """
        if not trace:
            return 0.5

        for i, entry in enumerate(trace):
            if entry.get("type") == "tool_call":
                tool = entry.get("name", "")
                if tool in ("write_file", "write", "patch", "create"):
                    return min(0.9, i / max(len(trace), 1))

        return 0.3
    
    def _estimate_feedback_instances(self, trace: List[Dict], tool_calls: List[Dict], output: str) -> int:
        """
        Estimate how many times the user had to provide feedback/corrections.
        
        Signal: each read→modify loop suggests a correction.
        Signal: repeated reads of same file after write = user corrected.
        Signal: consecutive patch operations = iterative fixes.
        Signal: "error" in output after execution = someone had to fix it.
        """
        if not trace:
            return 0

        instances = 0
        file_reads = {}
        consecutive_writes = 0

        for entry in trace:
            if entry.get("type") == "tool_call":
                name = entry.get("name", "").lower()
                args = entry.get("raw", "")

                if name in ("read_file", "read", "patch"):
                    path = args.split()[1] if len(args.split()) > 1 else ""
                    if path:
                        file_reads[path] = file_reads.get(path, 0) + 1

                elif name in ("write_file", "write", "patch", "terminal"):
                    consecutive_writes += 1
                    if consecutive_writes >= 3:
                        instances += 1
                        consecutive_writes = 0
                else:
                    consecutive_writes = 0

        # Multiple reads of same file = user feedback loops
        for path, count in file_reads.items():
            if count >= 2:
                instances += count - 1

        # "error" in output = someone had to fix it
        if "error" in output.lower() or "failed" in output.lower():
            instances += 1

        return min(instances, 10)
    
    def _count_tool_loops(self, trace: List[Dict]) -> int:
        """
        Count tool call loops (read→write→read→write patterns).
        Each loop = potential user feedback instance.
        """
        if not trace:
            return 0

        loops = 0
        actions = []

        for entry in trace:
            if entry.get("type") == "tool_call":
                name = entry.get("name", "").lower()
                if name in ("read_file", "read"):
                    actions.append("read")
                elif name in ("write_file", "write", "patch"):
                    actions.append("write")
                elif name in ("terminal", "process", "run"):
                    actions.append("run")

        # Count R-W-R-W patterns (loops)
        for i in range(len(actions) - 3):
            if (actions[i] == "read" and actions[i+1] == "write" and
                actions[i+2] == "read" and actions[i+3] == "write"):
                loops += 1

        return loops
    
    def _compute_speed_score(self, duration: float) -> float:
        """
        Compute speed score (1.0 = at baseline, >1.0 = faster/better).
        """
        baseline = self._get_baseline_duration()
        
        if baseline == 0:
            return 1.0
        
        score = baseline / duration if duration > 0 else 1.0
        return min(score, 2.0)
    
    def _get_baseline_duration(self) -> float:
        """Get baseline duration from historical data."""
        
        if self.baseline_file.exists():
            with open(self.baseline_file) as f:
                baseline = json.load(f)
                return baseline.get("median_duration", 60)
        
        results_files = sorted(self.results_dir.glob("*_results.json"))
        
        if len(results_files) >= 5:
            durations = []
            for f in results_files[-5:]:
                data = json.load(open(f))
                if "summary" in data and "avg_duration_seconds" in data["summary"]:
                    durations.append(data["summary"]["avg_duration_seconds"])
            
            if durations:
                durations.sort()
                return durations[len(durations) // 2]
        
        return 60
    
    def _analyze_code_indicators(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code quality indicators from execution."""
        
        output = execution.get("output", "")
        
        indicators = {
            "has_code_block": "```" in output,
            "has_explanation": len(output) > 200,
            "mentions_files": "file" in output.lower() or "created" in output.lower(),
            "has_error": "error" in output.lower() or "failed" in output.lower(),
            "mentions_test": "test" in output.lower(),
            "mentions_refactor": any(k in output.lower() for k in ["refactor", "improve", "clean"])
        }
        
        return indicators
    
    def update_baseline(self, duration: float):
        """Update baseline with new data point."""
        baseline_data = {
            "median_duration": duration,
            "updated_at": datetime.now().isoformat()
        }
        
        with open(self.baseline_file, "w") as f:
            json.dump(baseline_data, f, indent=2)


def compute_trend(results_dir: Path, metric: str, last_n: int = 10) -> List[Dict]:
    """Compute trend for a metric over last N runs."""
    results_files = sorted(results_dir.glob("*_results.json"))[-last_n:]
    
    trend = []
    for f in results_files:
        data = json.load(open(f))
        value = data.get("summary", {}).get(metric)
        if value is not None:
            trend.append({
                "timestamp": data.get("timestamp", f.stem),
                "value": value
            })
    
    return trend
