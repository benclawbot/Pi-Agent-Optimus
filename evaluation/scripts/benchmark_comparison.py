#!/usr/bin/env python3
"""
Benchmark Comparison - Compare results across versions.
Tracks evolution over time and identifies regressions.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics


class BenchmarkComparison:
    """Compares benchmark results across versions."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "benchmark" / "data"
        self.data_dir = Path(data_dir)
    
    def compare_versions(
        self,
        version1: str,
        version2: str = None
    ) -> Dict[str, Any]:
        """
        Compare two versions of benchmark results.
        
        If version2 is None, compares to previous version.
        """
        
        results_files = sorted(self.data_dir.glob("*_results.json"))
        
        if len(results_files) < 1:
            return {"error": "Not enough results to compare"}
        
        # Load latest results
        latest = self._load_result(results_files[-1])
        
        if version2 is None:
            # Compare to previous
            if len(results_files) < 2:
                return {"error": "No previous version to compare"}
            previous = self._load_result(results_files[-2])
            comparison_label = f"{previous['version']} vs {latest['version']}"
        else:
            # Find specific version
            prev_file = self._find_version(version2)
            if prev_file is None:
                return {"error": f"Version {version2} not found"}
            previous = self._load_result(prev_file)
            comparison_label = f"{previous['version']} vs {latest['version']}"
        
        return self._build_comparison(previous, latest, comparison_label)
    
    def compare_to_baseline(self, version: str = "current") -> Dict[str, Any]:
        """Compare current results to baseline (first run)."""
        
        results_files = sorted(self.data_dir.glob("*_results.json"))
        
        if len(results_files) < 2:
            return {"error": "Not enough data for baseline comparison"}
        
        baseline = self._load_result(results_files[0])
        current = self._load_result(results_files[-1])
        
        return self._build_comparison(baseline, current, f"baseline vs current")
    
    def track_evolution(self, last_n: int = 10) -> Dict[str, Any]:
        """Track performance evolution over last N versions."""
        
        results_files = sorted(self.data_dir.glob("*_results.json"))[-last_n:]
        
        if len(results_files) < 2:
            return {"error": "Not enough data for evolution tracking"}
        
        versions = []
        overall_scores = []
        dimension_trends = {}
        
        for f in results_files:
            result = self._load_result(f)
            versions.append(result["version"])
            overall_scores.append(result["scorecard"]["overall_score"])
            
            # Track each dimension
            for dim, data in result.get("scorecard", {}).get("dimensions", {}).items():
                if dim not in dimension_trends:
                    dimension_trends[dim] = []
                dimension_trends[dim].append(data.get("raw_score", 0))
        
        return {
            "versions": versions,
            "overall_trend": overall_scores,
            "dimension_trends": dimension_trends,
            "improvement_pct": self._calculate_improvement(overall_scores),
            "regressions": self._detect_regressions(dimension_trends)
        }
    
    def _load_result(self, filepath: Path) -> Dict[str, Any]:
        """Load a result file."""
        
        with open(filepath) as f:
            return json.load(f)
    
    def _find_version(self, version: str) -> Optional[Path]:
        """Find results file for a specific version."""
        
        for f in self.data_dir.glob("*_results.json"):
            if version in f.name:
                return f
        return None
    
    def _build_comparison(
        self,
        previous: Dict,
        current: Dict,
        label: str
    ) -> Dict[str, Any]:
        """Build comparison report between two versions."""
        
        comparison = {
            "label": label,
            "previous_version": previous.get("version", "unknown"),
            "current_version": current.get("version", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "overall": self._compare_overall(previous, current),
            "dimensions": {},
            "latency_changes": {},
            "token_changes": {},
            "regressions": [],
            "improvements": []
        }
        
        # Compare dimensions
        prev_dims = previous.get("scorecard", {}).get("dimensions", {})
        curr_dims = current.get("scorecard", {}).get("dimensions", {})
        
        for dim in set(list(prev_dims.keys()) + list(curr_dims.keys())):
            prev_score = prev_dims.get(dim, {}).get("raw_score", 0)
            curr_score = curr_dims.get(dim, {}).get("raw_score", 0)
            delta = curr_score - prev_score
            
            comparison["dimensions"][dim] = {
                "previous": prev_score,
                "current": curr_score,
                "delta": delta,
                "change_pct": (delta / prev_score * 100) if prev_score > 0 else 0
            }
            
            if delta < -0.05:
                comparison["regressions"].append(dim)
            elif delta > 0.05:
                comparison["improvements"].append(dim)
        
        # Compare latency
        prev_lat = previous.get("latency_stats", {})
        curr_lat = current.get("latency_stats", {})
        
        for key in ["p50", "p95", "p99", "mean"]:
            prev_val = prev_lat.get(key, 0)
            curr_val = curr_lat.get(key, 0)
            
            if prev_val > 0:
                change = (curr_val - prev_val) / prev_val * 100
            else:
                change = 0
            
            comparison["latency_changes"][key] = {
                "previous": prev_val,
                "current": curr_val,
                "change_pct": change
            }
        
        # Compare tokens
        prev_tokens = previous.get("token_stats", {})
        curr_tokens = current.get("token_stats", {})
        
        comparison["token_changes"] = {
            "avg_tokens": {
                "previous": prev_tokens.get("avg_tokens", 0),
                "current": curr_tokens.get("avg_tokens", 0),
                "change_pct": self._pct_change(
                    prev_tokens.get("avg_tokens", 0),
                    curr_tokens.get("avg_tokens", 0)
                )
            }
        }
        
        return comparison
    
    def _compare_overall(self, previous: Dict, current: Dict) -> Dict[str, Any]:
        """Compare overall scores."""
        
        prev_score = previous.get("scorecard", {}).get("overall_score", 0)
        curr_score = current.get("scorecard", {}).get("overall_score", 0)
        delta = curr_score - prev_score
        
        return {
            "previous": prev_score,
            "current": curr_score,
            "delta": delta,
            "change_pct": self._pct_change(prev_score, curr_score),
            "verdict": "improved" if delta > 0.01 else ("regressed" if delta < -0.01 else "stable")
        }
    
    def _calculate_improvement(self, scores: List[float]) -> float:
        """Calculate overall improvement percentage."""
        
        if len(scores) < 2:
            return 0
        
        first = scores[0]
        last = scores[-1]
        
        if first == 0:
            return 0
        
        return (last - first) / first * 100
    
    def _detect_regressions(self, dimension_trends: Dict[str, List[float]]) -> List[Dict]:
        """Detect regressions in dimension trends."""
        
        regressions = []
        
        for dim, scores in dimension_trends.items():
            if len(scores) >= 3:
                # Check if recent scores are declining
                recent = scores[-3:]
                if all(recent[i] >= recent[i+1] for i in range(len(recent)-1)):
                    regressions.append({
                        "dimension": dim,
                        "trend": "declining",
                        "last_values": recent
                    })
        
        return regressions
    
    def _pct_change(self, old: float, new: float) -> float:
        """Calculate percentage change."""
        
        if old == 0:
            return 0 if new == 0 else 100
        return (new - old) / old * 100
    
    def generate_report(self, comparison: Dict) -> str:
        """Generate a human-readable comparison report."""
        
        lines = []
        
        lines.append("=" * 60)
        lines.append("  BENCHMARK COMPARISON REPORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"  Comparing: {comparison['label']}")
        lines.append(f"  Generated: {comparison['timestamp']}")
        lines.append("")
        
        # Overall
        overall = comparison.get("overall", {})
        lines.append("  OVERALL PERFORMANCE")
        lines.append("-" * 40)
        lines.append(f"  Previous: {overall.get('previous', 0):.3f}")
        lines.append(f"  Current:  {overall.get('current', 0):.3f}")
        lines.append(f"  Delta:    {overall.get('delta', 0):+.3f}")
        lines.append(f"  Verdict:  {overall.get('verdict', 'unknown')}")
        lines.append("")
        
        # Dimensions
        lines.append("  DIMENSION BREAKDOWN")
        lines.append("-" * 40)
        lines.append(f"  {'Dimension':<15} {'Prev':>8} {'Curr':>8} {'Delta':>8}")
        lines.append(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8}")
        
        for dim, data in sorted(comparison.get("dimensions", {}).items(), key=lambda x: -abs(x[1].get("delta", 0))):
            delta = data.get("delta", 0)
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
            lines.append(f"  {dim:<15} {data.get('previous', 0):>8.3f} {data.get('current', 0):>8.3f} {delta:>+7.3f} {arrow}")
        
        lines.append("")
        
        # Latency
        if comparison.get("latency_changes"):
            lines.append("  LATENCY CHANGES")
            lines.append("-" * 40)
            for key, data in comparison["latency_changes"].items():
                change = data.get("change_pct", 0)
                arrow = "↓" if change < 0 else ("↑" if change > 0 else "→")
                lines.append(f"  {key.upper()}: {data.get('previous', 0):.2f}s → {data.get('current', 0):.2f}s ({change:+.1f}% {arrow})")
            lines.append("")
        
        # Regressions/Improvements
        if comparison.get("regressions"):
            lines.append("  ⚠️  REGRESSIONS DETECTED:")
            for reg in comparison["regressions"]:
                lines.append(f"    - {reg}")
            lines.append("")
        
        if comparison.get("improvements"):
            lines.append("  ✅ IMPROVEMENTS:")
            for imp in comparison["improvements"]:
                lines.append(f"    - {imp}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


def main():
    """Command-line interface."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare benchmark versions")
    parser.add_argument("--baseline", action="store_true", help="Compare to baseline")
    parser.add_argument("--evolution", "-e", action="store_true", help="Track evolution")
    parser.add_argument("--version", "-v", help="Specific version to compare")
    parser.add_argument("--report", "-r", action="store_true", help="Generate report")
    
    args = parser.parse_args()
    
    comparison = BenchmarkComparison()
    
    if args.evolution:
        result = comparison.track_evolution()
        print(json.dumps(result, indent=2, default=str))
    elif args.baseline:
        result = comparison.compare_to_baseline()
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            report = comparison.generate_report(result)
            print(report)
    elif args.version:
        result = comparison.compare_versions(args.version)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            report = comparison.generate_report(result)
            print(report)
    else:
        result = comparison.compare_versions("current")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            report = comparison.generate_report(result)
            print(report)


if __name__ == "__main__":
    main()