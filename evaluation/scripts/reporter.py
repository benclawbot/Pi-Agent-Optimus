#!/usr/bin/env python3
"""
Reporter - Generates evaluation reports in multiple formats.
Markdown, terminal, and HTML output.
"""

import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


class Reporter:
    """Generates evaluation reports in various formats."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.reporting_config = config.get("reporting", {})
        self.agent_name = config.get("activeAgent", {}).get("name", "Agent")
        self.framework_name = "Agent Evaluation Framework"
    
    def markdown(self, results: List[Dict], summary: Dict[str, Any]) -> str:
        """
        Generate markdown report.
        
        Args:
            results: List of individual task results
            summary: Aggregated summary statistics
        
        Returns:
            Markdown-formatted report string
        """
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        report = f"""# {self.agent_name} Evaluation Report

**Generated:** {timestamp}  
**Agent:** {self.agent_name}  
**Tasks Run:** {summary.get('tasks_run', len(results))}  
**Overall Score:** {summary.get('overall_score', 0):.2f}/1.0

---

## Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | {summary.get('overall_score', 0):.2f} |
| **Code Quality (avg)** | {summary.get('code_quality_avg', 0):.2f}/5 |
| **Objective Validation (avg)** | {summary.get('validation_avg', 0):.2f}/1 |
| **Objective Pass Rate** | {summary.get('objective_pass_rate', 0) * 100:.1f}% |
| **Proactivity (avg)** | {summary.get('proactivity_avg', 0):.2f}/5 |
| **Speed Improvement** | {summary.get('speed_improvement_pct', 0):+.1f}% |
| **Avg Duration** | {summary.get('avg_duration_seconds', 0):.1f}s |

---

## Detailed Results

"""
        
        # Group by category
        categories = {}
        for result in results:
            cat = result.get("task_category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        for category, cat_results in sorted(categories.items()):
            report += f"### {category.replace('-', ' ').title()}\n\n"
            report += "| Task | Score | Validation | Code Quality | Proactivity | Duration | Status |\n"
            report += "|------|-------|------------|--------------|-------------|---------|--------|\n"
            
            for r in cat_results:
                score = r.get("overall_score", 0)
                cq = r.get("judge_scores", {}).get("code_quality", 0)
                val = r.get("validation", {})
                validation = f"{val.get('score', 0.5):.2f} {val.get('grade', 'unknown')}"
                pro = r.get("proactivity", {}).get("score", 0)
                dur = r.get("duration_seconds", 0)
                status = "✓" if score >= 0.6 else "✗"
                
                report += f"| {r.get('task_name', 'Unknown')} | {score:.2f} | {validation} | {cq:.1f}/5 | {pro:.1f}/5 | {dur:.1f}s | {status} |\n"
            
            report += "\n"
        
        # Speed analysis
        report += """---

## Speed Analysis

"""
        
        if summary.get('speed_improvement_pct', 0) > 0:
            report += f"✅ **Speed improved by {summary['speed_improvement_pct']:.1f}%** compared to baseline.\n\n"
        elif summary.get('speed_improvement_pct', 0) < 0:
            report += f"⚠️ **Speed decreased by {abs(summary['speed_improvement_pct']):.1f}%** compared to baseline.\n\n"
        else:
            report += "➡️ **Speed unchanged** compared to baseline.\n\n"
        
        # Issues detected
        issues = [r for r in results if r.get("judge_scores", {}).get("code_quality", 5) < 3]
        if issues:
            report += "## Issues Detected\n\n"
            for issue in issues:
                report += f"- **{issue['task_name']}** (Code Quality: {issue['judge_scores']['code_quality']}/5)\n"
                report += f"  - Category: {issue['task_category']}\n\n"

        validation_failures = [
            r for r in results
            if r.get("validation", {}).get("grade") in {"fail", "partial"}
        ]
        if validation_failures:
            report += "## Objective Validation Failures\n\n"
            for result in validation_failures:
                validation = result.get("validation", {})
                report += f"- **{result['task_name']}** ({validation.get('grade')}, score {validation.get('score', 0):.2f})\n"
                for check in validation.get("checks", [])[:3]:
                    if not check.get("passed"):
                        detail = str(check.get("detail", "")).replace("\n", " ")[:180]
                        report += f"  - {check.get('name')}: {detail}\n"
                report += "\n"
        
        # Proactivity breakdown
        proactive_count = sum(1 for r in results if r.get("proactivity", {}).get("score", 0) > 2)
        report += f"---\n\n## Proactivity Analysis\n\n"
        report += f"**{proactive_count}/{len(results)} tasks** showed proactive behavior.\n\n"
        
        # Breakdown
        breakdown = {"proposed_next_steps": 0, "unprompted_action": 0, "volunteered_info": 0}
        for r in results:
            pro_data = r.get("proactivity", {})
            for key in breakdown:
                breakdown[key] += pro_data.get("breakdown", {}).get(key, 0)
        
        report += "| Behavior | Count |\n|---------|-------|\n"
        for behavior, count in breakdown.items():
            report += f"| {behavior.replace('_', ' ').title()} | {count} |\n"
        
        report += f"\n---\n\n*Report generated by {self.framework_name}*\n"
        
        return report
    
    def terminal(self, summary: Dict[str, Any]):
        """
        Print summary to terminal.
        
        Args:
            summary: Aggregated summary statistics
        """
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                 AGENT EVALUATION SUMMARY                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Agent:                {self.agent_name[:34]:<34} ║
║  📊 Overall Score:        {summary.get('overall_score', 0):.2f}/1.00
║  📈 Code Quality (avg):   {summary.get('code_quality_avg', 0):.2f}/5.00
║  ✅ Objective Pass Rate:  {summary.get('objective_pass_rate', 0) * 100:.1f}%
║  ⚡ Proactivity (avg):     {summary.get('proactivity_avg', 0):.2f}/5.00
║  🏃 Speed Improvement:    {summary.get('speed_improvement_pct', 0):+.1f}%
║  ⏱️  Avg Duration:         {summary.get('avg_duration_seconds', 0):.1f}s
║                                                              ║
╠══════════════════════════════════════════════════════════════╣""")
        
        score = summary.get('overall_score', 0)
        if score >= 0.8:
            grade = "🟢 EXCELLENT"
        elif score >= 0.6:
            grade = "🟡 GOOD"
        elif score >= 0.4:
            grade = "🟠 NEEDS WORK"
        else:
            grade = "🔴 CRITICAL"
        
        print(f"║  Overall Grade:        {grade}")
        print("║                                                              ║")
        print("╚══════════════════════════════════════════════════════════════╝")
    
    def html(self, results: List[Dict], summary: Dict[str, Any]) -> str:
        """
        Generate HTML report.
        
        Args:
            results: List of individual task results
            summary: Aggregated summary statistics
        
        Returns:
            HTML-formatted report string
        """
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Score color
        score = summary.get('overall_score', 0)
        if score >= 0.8:
            score_color = "#22c55e"  # green
        elif score >= 0.6:
            score_color = "#eab308"  # yellow
        elif score >= 0.4:
            score_color = "#f97316"  # orange
        else:
            score_color = "#ef4444"  # red
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.agent_name} - Evaluation Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #f8fafc; margin-bottom: 0.5rem; }}
        .timestamp {{ color: #94a3b8; margin-bottom: 2rem; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .metric-card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }}
        .metric-label {{ font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem; }}
        .metric-value {{ font-size: 2rem; font-weight: 600; color: {score_color}; }}
        .metric-value.speed {{ color: {'#22c55e' if summary.get('speed_improvement_pct', 0) >= 0 else '#ef4444'}; }}
        .section {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #334155; }}
        h2 {{ color: #f8fafc; margin-bottom: 1rem; font-size: 1.25rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #334155; color: #94a3b8; font-weight: 500; }}
        td {{ padding: 0.75rem; border-bottom: 1px solid #334155; }}
        .score {{ font-weight: 600; }}
        .pass {{ color: #22c55e; }}
        .fail {{ color: #ef4444; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; background: #334155; color: #94a3b8; }}
        .footer {{ text-align: center; color: #64748b; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{self.agent_name} Evaluation Report</h1>
        <p class="timestamp">Generated: {timestamp} | Agent: {self.agent_name} | Tasks: {summary.get('tasks_run', len(results))}</p>
        
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-label">Overall Score</div>
                <div class="metric-value">{summary.get('overall_score', 0):.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Code Quality (avg)</div>
                <div class="metric-value">{summary.get('code_quality_avg', 0):.2f}/5</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Objective Pass Rate</div>
                <div class="metric-value">{summary.get('objective_pass_rate', 0) * 100:.0f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Proactivity (avg)</div>
                <div class="metric-value">{summary.get('proactivity_avg', 0):.2f}/5</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Speed Improvement</div>
                <div class="metric-value speed">{summary.get('speed_improvement_pct', 0):+.1f}%</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Task Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Task</th>
                        <th>Category</th>
                        <th>Score</th>
                        <th>Code Quality</th>
                        <th>Proactivity</th>
                        <th>Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for r in results:
            score = r.get('overall_score', 0)
            cq = r.get('judge_scores', {}).get('code_quality', 0)
            pro = r.get('proactivity', {}).get('score', 0)
            dur = r.get('duration_seconds', 0)
            status_class = "pass" if score >= 0.6 else "fail"
            status_icon = "✓" if score >= 0.6 else "✗"
            
            html += f"""
                    <tr>
                        <td>{r.get('task_name', 'Unknown')}</td>
                        <td><span class="badge">{r.get('task_category', 'unknown')}</span></td>
                        <td class="score {status_class}">{score:.2f}</td>
                        <td>{cq:.1f}/5</td>
                        <td>{pro:.1f}/5</td>
                        <td>{dur:.1f}s</td>
                        <td class="{status_class}">{status_icon}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            Generated by {self.framework_name}
        </div>
    </div>
</body>
</html>
"""
        
        return html


def generate_report(results: List[Dict], summary: Dict[str, Any], config: Dict) -> Dict[str, str]:
    """
    Generate reports in all configured formats.
    
    Returns:
        Dict mapping format name to file path
    """
    reporter = Reporter(config)
    
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    output = {}
    
    # Markdown
    md_path = reports_dir / f"{timestamp}_evaluation.md"
    with open(md_path, "w") as f:
        f.write(reporter.markdown(results, summary))
    output["markdown"] = str(md_path)
    
    # HTML
    html_path = reports_dir / f"{timestamp}_evaluation.html"
    with open(html_path, "w") as f:
        f.write(reporter.html(results, summary))
    output["html"] = str(html_path)
    
    return output


if __name__ == "__main__":
    # Test with sample data
    sample_results = [
        {
            "task_name": "Create Python function",
            "task_category": "code-quality",
            "overall_score": 0.85,
            "judge_scores": {"code_quality": 4.5},
            "proactivity": {"score": 3.5},
            "duration_seconds": 42.3
        },
        {
            "task_name": "Debug authentication",
            "task_category": "debug",
            "overall_score": 0.72,
            "judge_scores": {"code_quality": 3.8},
            "proactivity": {"score": 2.1},
            "duration_seconds": 67.8
        }
    ]
    
    sample_summary = {
        "tasks_run": 2,
        "overall_score": 0.79,
        "code_quality_avg": 4.15,
        "proactivity_avg": 2.8,
        "speed_improvement_pct": 5.2,
        "avg_duration_seconds": 55.05
    }
    
    config = {"reporting": {}}
    reporter = Reporter(config)
    
    # Test markdown
    md = reporter.markdown(sample_results, sample_summary)
    print("=== MARKDOWN ===")
    print(md[:500])
    print("...")
    
    # Test terminal
    print("\n=== TERMINAL ===")
    reporter.terminal(sample_summary)
    
    # Test HTML
    html = reporter.html(sample_results, sample_summary)
    print("\n=== HTML (first 300 chars) ===")
    print(html[:300])
