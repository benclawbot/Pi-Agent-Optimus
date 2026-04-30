#!/usr/bin/env python3
"""
Historical Runs Storage
Stores benchmark results over time and provides data for dashboard trends.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class HistoricalRuns:
    """Manages historical benchmark runs for trend analysis."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "benchmark" / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_file = self.data_dir / "history.json"
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """Load historical runs."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                data = json.load(f)
                return data.get("runs", [])
        return []
    
    def _save_history(self):
        """Save history to disk."""
        with open(self.history_file, "w") as f:
            json.dump({
                "runs": self.history,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)
    
    def add_run(self, result: Dict[str, Any]) -> int:
        """
        Add a benchmark run to history.
        
        Args:
            result: Benchmark result dict with scorecard and dimension_scores
        
        Returns:
            Run index
        """
        # Extract summary data for trends
        run_summary = {
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            "version": result.get("version", "unknown"),
            "overall_score": result.get("scorecard", {}).get("overall_score", 0),
            "tasks_run": result.get("completed_tasks", 0),
            "dimension_scores": {},
            "latency_p50": result.get("latency_stats", {}).get("p50", 0),
            "latency_p95": result.get("latency_stats", {}).get("p95", 0),
            "avg_duration": result.get("latency_stats", {}).get("mean", 0),
            "avg_tokens": result.get("token_stats", {}).get("avg_tokens", 0)
        }
        
        # Add each dimension score
        dimensions = result.get("scorecard", {}).get("dimensions", {})
        for dim_name, dim_data in dimensions.items():
            run_summary["dimension_scores"][dim_name] = dim_data.get("raw_score", 0)
        
        # Add to history
        self.history.append(run_summary)
        self._save_history()
        
        return len(self.history) - 1
    
    def get_runs(self, last_n: int = None) -> List[Dict]:
        """Get historical runs, optionally limited to last N."""
        if last_n is None:
            return self.history
        return self.history[-last_n:]
    
    def get_trend_data(self, dimension: str = None, last_n: int = 10) -> Dict[str, List]:
        """
        Get trend data for a dimension or all.
        
        Returns:
            Dict with timestamps and scores
        """
        runs = self.get_runs(last_n)
        
        if not runs:
            return {"timestamps": [], "scores": [], "labels": []}
        
        timestamps = [r["timestamp"][:10] for r in runs]  # Just date part
        labels = [r.get("version", f"v{i+1}") for i, r in enumerate(runs)]
        
        if dimension:
            scores = [r["dimension_scores"].get(dimension, 0) for r in runs]
        else:
            scores = [r["overall_score"] for r in runs]
        
        return {
            "timestamps": timestamps,
            "scores": scores,
            "labels": labels
        }
    
    def compute_improvement(self) -> Dict[str, float]:
        """Compute improvement from first to latest run."""
        
        if len(self.history) < 2:
            return {"overall": 0, "dimensions": {}}
        
        first = self.history[0]
        latest = self.history[-1]
        
        # Overall improvement
        first_score = first.get("overall_score", 0)
        latest_score = latest.get("overall_score", 0)
        overall_improvement = ((latest_score - first_score) / first_score * 100) if first_score > 0 else 0
        
        # Per-dimension improvement
        dimensions = {}
        for dim in first.get("dimension_scores", {}).keys():
            first_dim = first["dimension_scores"].get(dim, 0)
            latest_dim = latest["dimension_scores"].get(dim, 0)
            if first_dim > 0:
                improvement = ((latest_dim - first_dim) / first_dim * 100)
            else:
                improvement = latest_dim * 100  # From 0
            dimensions[dim] = round(improvement, 1)
        
        return {
            "overall": round(overall_improvement, 1),
            "dimensions": dimensions
        }
    
    def export_for_dashboard(self) -> Dict[str, Any]:
        """Export data in format dashboard expects."""
        
        runs = self.get_runs(20)  # Last 20 runs
        
        return {
            "updated_at": datetime.now().isoformat(),
            "total_runs": len(self.history),
            "runs": runs,
            "trend": {
                "overall": self.get_trend_data(),
                "improvement": self.compute_improvement()
            }
        }


def add_current_run_to_history():
    """Add the current/latest benchmark run to history."""
    
    historical = HistoricalRuns()
    
    # Load latest results
    latest_path = Path(__file__).parent.parent / "benchmark" / "data" / "latest.json"
    
    if latest_path.exists():
        with open(latest_path) as f:
            result = json.load(f)
        
        historical.add_run(result)
        
        # Export for dashboard
        dashboard_data = historical.export_for_dashboard()
        
        # Write dashboard trend file
        trend_file = Path(__file__).parent.parent / "benchmark" / "data" / "trend_data.json"
        with open(trend_file, "w") as f:
            json.dump(dashboard_data, f, indent=2)
        
        print(f"✅ Added run to history ({len(historical.history)} total)")
        print(f"   Overall trend: {dashboard_data['trend']['improvement']['overall']:+.1f}%")
    else:
        print("⚠️ No latest.json found - run benchmark first")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage historical runs")
    parser.add_argument("--add", action="store_true", help="Add current run to history")
    parser.add_argument("--export", action="store_true", help="Export for dashboard")
    parser.add_argument("--trend", action="store_true", help="Show trend")
    parser.add_argument("--last", type=int, default=10, help="Number of runs to show")
    
    args = parser.parse_args()
    
    historical = HistoricalRuns()
    
    if args.add:
        add_current_run_to_history()
    elif args.export:
        data = historical.export_for_dashboard()
        print(json.dumps(data, indent=2))
    elif args.trend:
        trend = historical.get_trend_data(last_n=args.last)
        print(f"Last {len(trend['scores'])} runs:")
        for label, score in zip(trend['labels'], trend['scores']):
            print(f"  {label}: {score:.3f}")
        
        improvement = historical.compute_improvement()
        print(f"\nImprovement: {improvement['overall']:+.1f}%")
    else:
        print(f"Total runs in history: {len(historical.history)}")