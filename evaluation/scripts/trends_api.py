#!/usr/bin/env python3
"""
Trends Data API - Serves evaluation data for the dashboard.
Maintains a consolidated trends.json file for easy dashboard access.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import os


class TrendsAPI:
    """Manages trends data for the dashboard."""
    
    def __init__(self, results_dir: str = None, trends_file: str = None):
        if results_dir is None:
            results_dir = Path(__file__).parent.parent / "results"
        if trends_file is None:
            trends_file = Path(__file__).parent.parent / "trends.json"
        
        self.results_dir = Path(results_dir)
        self.trends_file = Path(trends_file)
    
    def update_trends(self) -> Dict[str, Any]:
        """
        Update the trends.json file from all result files.
        
        Returns:
            The updated trends data
        """
        result_files = sorted(self.results_dir.glob("*_results.json"))
        
        all_runs = []
        category_data = {cat: [] for cat in ["code-quality", "debug", "architecture", "refactor"]}
        proactivity_totals = {
            "proposed_next_steps": 0,
            "unprompted_action": 0,
            "volunteered_info": 0,
            "offered_alternatives": 0,
            "follow_through": 0
        }
        
        for result_file in result_files:
            try:
                with open(result_file) as f:
                    data = json.load(f)
                
                run = {
                    "timestamp": data.get("timestamp", result_file.stem.split("_")[0]),
                    "tasks_run": data.get("summary", {}).get("tasks_run", 0),
                    "overall_score": data.get("summary", {}).get("overall_score", 0),
                    "code_quality_avg": data.get("summary", {}).get("code_quality_avg", 0),
                    "proactivity_avg": data.get("summary", {}).get("proactivity_avg", 0),
                    "speed_improvement_pct": data.get("summary", {}).get("speed_improvement_pct", 0),
                    "avg_duration_seconds": data.get("summary", {}).get("avg_duration_seconds", 0)
                }
                all_runs.append(run)
                
                # Aggregate category data
                if "results" in data:
                    for result in data["results"]:
                        cat = result.get("task_category", "unknown")
                        if cat in category_data:
                            category_data[cat].append({
                                "timestamp": run["timestamp"],
                                "score": result.get("judge_scores", {}).get("code_quality", 0),
                                "proactivity": result.get("proactivity", {}).get("score", 0)
                            })
                        
                        # Aggregate proactivity breakdown
                        breakdown = result.get("proactivity", {}).get("breakdown", {})
                        for key in proactivity_totals:
                            proactivity_totals[key] += breakdown.get(key, 0)
                
            except Exception as e:
                print(f"Warning: Could not read {result_file}: {e}")
        
        # Compute trends
        trends = {
            "updated_at": datetime.now().isoformat(),
            "total_runs": len(all_runs),
            "runs": all_runs,
            "categories": category_data,
            "proactivity_totals": proactivity_totals,
            "latest": all_runs[-1] if all_runs else None,
            "summary": self._compute_summary(all_runs)
        }
        
        # Write trends file
        with open(self.trends_file, "w") as f:
            json.dump(trends, f, indent=2)
        
        print(f"✅ Updated trends with {len(all_runs)} runs")
        return trends
    
    def _compute_summary(self, runs: List[Dict]) -> Dict[str, Any]:
        """Compute summary statistics."""
        
        if not runs:
            return {}
        
        # Overall score trend
        scores = [r["overall_score"] for r in runs]
        
        # Speed improvement trend
        speeds = [r["speed_improvement_pct"] for r in runs]
        
        # Proactivity trend
        proactivity = [r["proactivity_avg"] for r in runs]
        
        return {
            "overall_score_avg": sum(scores) / len(scores),
            "overall_score_latest": runs[-1]["overall_score"],
            "overall_score_change": runs[-1]["overall_score"] - runs[0]["overall_score"] if len(runs) > 1 else 0,
            "speed_improvement_avg": sum(speeds) / len(speeds),
            "speed_improvement_latest": runs[-1]["speed_improvement_pct"],
            "proactivity_avg": sum(proactivity) / len(proactivity),
            "proactivity_latest": runs[-1]["proactivity_avg"],
            "runs_count": len(runs)
        }
    
    def get_data(self) -> Dict[str, Any]:
        """
        Get current trends data.
        Updates if trends file doesn't exist or is stale (>1 hour).
        """
        
        if not self.trends_file.exists():
            return self.update_trends()
        
        with open(self.trends_file) as f:
            data = json.load(f)
        
        # Check if stale
        updated_at = datetime.fromisoformat(data["updated_at"])
        if (datetime.now() - updated_at).total_seconds() > 3600:
            return self.update_trends()
        
        return data
    
    def get_runs(self, days: int = 30) -> List[Dict]:
        """Get runs from the last N days."""
        
        data = self.get_data()
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        return [
            r for r in data["runs"]
            if datetime.fromisoformat(r["timestamp"]).timestamp() > cutoff
        ]
    
    def export_for_dashboard(self) -> str:
        """
        Export data in the format the dashboard expects.
        This is a simple static file approach.
        """
        
        data = self.get_data()
        
        # Create dashboard-compatible format
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "runs": data["runs"][-30:]  # Last 30 runs
        }
        
        output_path = self.trends_file.parent / "dashboard_data.json"
        
        with open(output_path, "w") as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        return str(output_path)


def main():
    """Command-line interface."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage evaluation trends")
    parser.add_argument("--update", action="store_true", help="Update trends from results")
    parser.add_argument("--export", action="store_true", help="Export for dashboard")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    
    args = parser.parse_args()
    
    api = TrendsAPI()
    
    if args.update:
        data = api.update_trends()
        print(f"Updated trends with {data['total_runs']} runs")
    
    if args.export:
        path = api.export_for_dashboard()
        print(f"Exported to: {path}")
    
    if args.json or not (args.update or args.export):
        data = api.get_data()
        print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()