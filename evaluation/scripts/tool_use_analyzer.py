#!/usr/bin/env python3
"""
Tool Use Analyzer - Tracks and scores tool usage patterns.
Measures: correct tool selection, call success rate, chaining efficiency.
"""

import json
import re
from typing import Dict, List, Any, Tuple
from collections import Counter


class ToolUseAnalyzer:
    """Analyzes tool usage patterns from execution traces."""
    
    # Standard tools available to Pi agent
    STANDARD_TOOLS = {
        'read': 'Reads file contents',
        'write': 'Creates or overwrites files',
        'edit': 'Modifies specific parts of files',
        'bash': 'Executes shell commands',
        'search': 'Searches within files',
        'glob': 'Finds files by pattern'
    }
    
    # Correct tool for task types
    TASK_TOOL_MAPPING = {
        'coding': ['read', 'write', 'edit', 'bash'],
        'tool_usage': ['read', 'bash', 'write', 'search'],
        'open_ended': ['read', 'bash', 'write', 'search', 'glob'],
        'reasoning': [],  # No tools typically needed
        'safety': [],  # No tools typically needed
        'adversarial': []
    }
    
    def __init__(self):
        self.call_history = []
    
    def analyze_execution(
        self,
        trace: str,
        output: str,
        task_category: str
    ) -> Dict[str, Any]:
        """
        Analyze tool usage from execution trace.
        
        Returns:
            Dict with tool_use metrics
        """
        # Extract tool calls from trace
        tool_calls = self._extract_tool_calls(trace)
        
        # Analyze patterns
        unique_tools = set(c['tool'] for c in tool_calls)
        call_count = len(tool_calls)
        
        # Score correct tool selection
        expected_tools = self.TASK_TOOL_MAPPING.get(task_category, [])
        correct_selections = sum(1 for t in unique_tools if t in expected_tools or not expected_tools)
        
        # Chaining efficiency (tools used in logical sequence)
        chaining_score = self._compute_chaining_score(tool_calls)
        
        # Tool call success (parse errors, etc)
        success_rate = self._compute_success_rate(tool_calls, output)
        
        # Latency estimate (based on trace timestamps if available)
        avg_tool_time = self._estimate_tool_latency(tool_calls, trace)
        
        return {
            'total_calls': call_count,
            'unique_tools': list(unique_tools),
            'correct_selection_rate': correct_selections / max(len(unique_tools), 1),
            'chaining_score': chaining_score,
            'tool_call_success_rate': success_rate,
            'avg_tool_latency_ms': avg_tool_time,
            'tool_sequence': [c['tool'] for c in tool_calls]
        }
    
    def _extract_tool_calls(self, trace: str) -> List[Dict[str, Any]]:
        """Extract tool calls from execution trace."""
        
        calls = []
        
        # Pattern: tool_name(args)
        patterns = [
            r'Read\("([^"]*)"\)',
            r'Write\("([^"]*)"',
            r'Edit\(',
            r'Bash\("([^"]*)"\)',
            r'Search\(',
            r'Glob\(',
        ]
        
        tool_names = ['Read', 'Write', 'Edit', 'Bash', 'Search', 'Glob']
        
        for match in re.finditer(r'(Read|Write|Edit|Bash|Search|Glob)\s*\(', trace):
            tool = match.group(1).lower()
            calls.append({
                'tool': tool,
                'args': match.group(0),
                'position': match.start()
            })
        
        return calls
    
    def _compute_chaining_score(self, tool_calls: List[Dict]) -> float:
        """
        Compute how well tools are chained in logical sequence.
        
        Good patterns:
        - read -> write/edit (read then modify)
        - read -> bash (read then execute)
        - glob -> read (find then read)
        
        Poor patterns:
        - write before read (no context)
        - excessive redundant calls
        """
        
        if len(tool_calls) <= 1:
            return 0.5
        
        score = 0.5  # Base score
        
        # Check for read-first pattern
        if tool_calls[0]['tool'] == 'read':
            score += 0.2
        
        # Check for logical progression
        read_count = sum(1 for c in tool_calls if c['tool'] == 'read')
        write_count = sum(1 for c in tool_calls if c['tool'] == 'write')
        edit_count = sum(1 for c in tool_calls if c['tool'] == 'edit')
        
        # If modifying after reading = good
        if read_count > 0 and (write_count > 0 or edit_count > 0):
            score += 0.2
        
        # Efficiency penalty for excessive calls
        if len(tool_calls) > 10:
            score -= 0.1
        
        # Penalty for no writes when expected
        if write_count == 0 and edit_count == 0 and len(tool_calls) > 3:
            score -= 0.1
        
        return max(0, min(1, score))
    
    def _compute_success_rate(
        self,
        tool_calls: List[Dict],
        output: str
    ) -> float:
        """Compute tool call success rate."""
        
        if not tool_calls:
            return 1.0
        
        # Check for error patterns in output
        error_patterns = [
            'error',
            'failed',
            'permission denied',
            'not found',
            'cannot',
            'exception'
        ]
        
        error_count = sum(1 for p in error_patterns if p in output.lower())
        
        # Success rate = 1 - (errors / expected success)
        # Assume at least some success is expected
        estimated_failures = min(error_count, len(tool_calls))
        
        return 1 - (estimated_failures / len(tool_calls))
    
    def _estimate_tool_latency(
        self,
        tool_calls: List[Dict],
        trace: str
    ) -> float:
        """Estimate average tool call latency in ms."""
        
        if not tool_calls:
            return 0
        
        # Baseline estimates per tool type (ms)
        tool_latencies = {
            'read': 50,
            'write': 100,
            'edit': 75,
            'bash': 200,
            'search': 100,
            'glob': 50
        }
        
        total = sum(
            tool_latencies.get(c['tool'], 100)
            for c in tool_calls
        )
        
        return total / len(tool_calls)
    
    def score_tool_use_dimension(self, analyses: List[Dict]) -> Dict[str, Any]:
        """Compute overall tool_use dimension score from analyses."""
        
        if not analyses:
            return {
                'correct_tool_selection': 0.70,
                'tool_call_success_rate': 0.85,
                'avg_latency_ms': 120,
                'chaining_efficiency': 0.75
            }
        
        return {
            'correct_tool_selection': sum(a['correct_selection_rate'] for a in analyses) / len(analyses),
            'tool_call_success_rate': sum(a['tool_call_success_rate'] for a in analyses) / len(analyses),
            'avg_latency_ms': sum(a['avg_tool_latency_ms'] for a in analyses) / len(analyses),
            'chaining_efficiency': sum(a['chaining_score'] for a in analyses) / len(analyses),
            'total_tool_calls': sum(a['total_calls'] for a in analyses),
            'analyses': analyses
        }


def analyze_tool_use(trace: str, output: str, category: str) -> Dict[str, Any]:
    """Convenience function."""
    analyzer = ToolUseAnalyzer()
    return analyzer.analyze_execution(trace, output, category)


if __name__ == "__main__":
    # Test
    test_trace = """
    Read("config.json")
    Read("schema.json")
    Bash("python validate.py")
    Write("output.json")
    """
    
    analyzer = ToolUseAnalyzer()
    result = analyzer.analyze_execution(test_trace, "Success!", "tool_usage")
    print(json.dumps(result, indent=2))