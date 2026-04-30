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
        self.metrics_config = config["metrics"]
        self.results_dir = Path(__file__).parent.parent / "results"
        self.baseline_file = self.results_dir / "baseline.json"
    
    def extract(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from execution data.
        
        Returns:
            Dict with computed metrics
        """
        metrics = {}
        
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
        
        # Speed score (compared to baseline)
        metrics["speed_score"] = self._compute_speed_score(execution.get("duration", 0))
        
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
        # This would need calibration based on actual token counts
        # For now, return a normalized score
        total = tokens.get("total_estimate", 0)
        if total == 0:
            return 0.5
        
        # Efficiency: work done per token
        # This is a placeholder - would need real API data
        return 0.8  # Default reasonable score
    
    def _summarize_tool_calls(self, tool_calls: List[Dict]) -> Dict[str, int]:
        """Summarize tool call patterns."""
        summary = {}
        for call in tool_calls:
            tool_name = call.get("tool", "unknown")
            summary[tool_name] = summary.get(tool_name, 0) + 1
        
        return summary
    
    def _compute_speed_score(self, duration: float) -> float:
        """
        Compute speed score (1.0 = at baseline, >1.0 = faster/better).
        """
        baseline = self._get_baseline_duration()
        
        if baseline == 0:
            return 1.0
        
        # Score = how much faster than baseline
        score = baseline / duration if duration > 0 else 1.0
        
        # Cap at 2.0 (2x baseline is "good enough")
        return min(score, 2.0)
    
    def _get_baseline_duration(self) -> float:
        """Get baseline duration from historical data."""
        
        if self.baseline_file.exists():
            with open(self.baseline_file) as f:
                baseline = json.load(f)
                return baseline.get("median_duration", 60)
        
        # Try to compute from historical results
        results_files = sorted(self.results_dir.glob("*_results.json"))
        
        if len(results_files) >= 5:
            # Use median of last 5 runs
            durations = []
            for f in results_files[-5:]:
                data = json.load(open(f))
                if "summary" in data and "avg_duration_seconds" in data["summary"]:
                    durations.append(data["summary"]["avg_duration_seconds"])
            
            if durations:
                durations.sort()
                return durations[len(durations) // 2]
        
        return 60  # Default 60 second baseline
    
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
    """
    Compute trend for a metric over last N runs.
    
    Returns:
        List of {timestamp, value} dicts
    """
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


if __name__ == "__main__":
    # Test with sample execution
    test_execution = {
        "duration": 45.5,
        "trace": [
            {"type": "tool_call", "tool": "read", "args": {"path": "test.py"}},
            {"type": "tool_call", "tool": "write", "args": {"path": "output.py", "content": "..."}}
        ],
        "output": "I created a Python file with a function that...",
        "tool_calls": [
            {"tool": "read", "args": {"path": "test.py"}, "timestamp": None},
            {"tool": "write", "args": {"path": "output.py"}, "timestamp": None}
        ]
    }
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    config = {
        "metrics": {
            "speed": {"baselineMetric": "median_time_first_N_runs"}
        }
    }
    
    collector = MetricsCollector(config)
    metrics = collector.extract(test_execution)
    
    print(json.dumps(metrics, indent=2))