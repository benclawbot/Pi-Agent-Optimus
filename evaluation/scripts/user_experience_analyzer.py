#!/usr/bin/env python3
"""
User Experience Analyzer - Tracks UX metrics from agent interactions.
Measures: time to usable result, iterations, turns, corrections needed.
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class UserExperienceAnalyzer:
    """Analyzes user experience from execution data."""
    
    # Patterns indicating iterations/corrections
    CORRECTION_PATTERNS = [
        r'(?i)sorry,?\s*(i|we)',
        r'(?i)let me (retry|try again|redo|reconsider)',
        r'(?i)actually,?\s*(wait|no)',
        r'(?i)i made a mistake',
        r'(?i)revis(?:e|ing)',
        r'(?i)instead,?\s*(let me|i should)',
        r'(?i)correction:',
        r'(?i)updated:',
        r'(?i)fixed:'
    ]
    
    # Patterns indicating clarification needed
    CLARIFICATION_PATTERNS = [
        r'(?i)could you (clarify|specify|explain)',
        r'(?i)what do you mean',
        r'(?i)i need more (info|details|context)',
        r'(?i)can you (elaborate|expand)',
        r'(?i)i\'m not sure i understand'
    ]
    
    # Good UX patterns (proactive, clear)
    GOOD_UX_PATTERNS = [
        r'(?i)here\'s (what i did|the plan|the summary)',
        r'(?i)to summarize:',
        r'(?i)the result is ready',
        r'(?i)done,?\s*(here\'s|this)',
        r'(?i)complete'
    ]
    
    def __init__(self):
        self.session_metrics = []
    
    def analyze_interaction(
        self,
        output: str,
        duration_seconds: float,
        task_complexity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Analyze user experience from a single interaction.
        
        Returns:
            Dict with UX metrics
        """
        output_lower = output.lower()
        
        # Count corrections
        correction_count = self._count_patterns(output, self.CORRECTION_PATTERNS)
        
        # Count clarifications needed
        clarification_count = self._count_patterns(output, self.CLARIFICATION_PATTERNS)
        
        # Count good UX signals
        good_ux_count = self._count_patterns(output, self.GOOD_UX_PATTERNS)
        
        # Estimate iterations from corrections
        estimated_iterations = max(1, correction_count + 1)
        
        # Time to usable result (duration adjusted by corrections)
        time_to_result = duration_seconds * (1 + correction_count * 0.3)
        
        # Compute UX score (0-1)
        ux_score = self._compute_ux_score(
            correction_count=correction_count,
            clarification_count=clarification_count,
            good_ux_count=good_ux_count,
            complexity=task_complexity
        )
        
        return {
            'corrections_needed': correction_count,
            'clarifications_requested': clarification_count,
            'iterations_required': estimated_iterations,
            'turns_estimated': estimated_iterations * 2,  # Estimate
            'time_to_usable_result': round(time_to_result, 2),
            'good_ux_signals': good_ux_count,
            'ux_score': ux_score
        }
    
    def analyze_session(
        self,
        interactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a complete session with multiple interactions.
        
        Args:
            interactions: List of {output, duration, category} dicts
        
        Returns:
            Session-level UX metrics
        """
        if not interactions:
            return self._empty_ux_metrics()
        
        results = []
        for interaction in interactions:
            result = self.analyze_interaction(
                output=interaction.get('output', ''),
                duration_seconds=interaction.get('duration', 1),
                task_complexity=interaction.get('complexity', 'medium')
            )
            results.append(result)
        
        return self._aggregate_session_metrics(results)
    
    def _count_patterns(self, text: str, patterns: List[str]) -> int:
        """Count occurrences of patterns in text."""
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        
        return count
    
    def _compute_ux_score(
        self,
        correction_count: int,
        clarification_count: int,
        good_ux_count: int,
        complexity: str
    ) -> float:
        """
        Compute overall UX score (0-1).
        
        Higher = better experience
        """
        
        # Complexity affects expectations
        complexity_multipliers = {
            'easy': 1.2,
            'medium': 1.0,
            'hard': 0.8
        }
        mult = complexity_multipliers.get(complexity, 1.0)
        
        # Base score
        score = 1.0
        
        # Penalties
        score -= correction_count * 0.15
        score -= clarification_count * 0.10
        
        # Bonuses
        score += good_ux_count * 0.05
        
        # Normalize
        score = score * mult
        score = max(0, min(1, score))
        
        return round(score, 3)
    
    def _aggregate_session_metrics(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate metrics across a session."""
        
        n = len(results)
        
        return {
            'total_interactions': n,
            'avg_time_to_result': sum(r['time_to_usable_result'] for r in results) / n,
            'avg_iterations': sum(r['iterations_required'] for r in results) / n,
            'avg_turns': sum(r['turns_estimated'] for r in results) / n,
            'avg_corrections': sum(r['corrections_needed'] for r in results) / n,
            'avg_clarifications': sum(r['clarifications_requested'] for r in results) / n,
            'avg_ux_score': sum(r['ux_score'] for r in results) / n,
            'good_ux_signals_total': sum(r['good_ux_signals'] for r in results),
            'interactions': results
        }
    
    def _empty_ux_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            'total_interactions': 0,
            'avg_time_to_result': 0,
            'avg_iterations': 1,
            'avg_turns': 1,
            'avg_corrections': 0,
            'avg_clarifications': 0,
            'avg_ux_score': 0.7,
            'good_ux_signals_total': 0,
            'interactions': []
        }
    
    def score_ux_dimension(self, session_metrics: Dict) -> Dict[str, Any]:
        """Compute UX dimension score from session metrics."""
        
        if session_metrics.get('total_interactions', 0) == 0:
            return {
                'time_to_usable_result': 60,  # seconds
                'iterations_required': 1.2,
                'turns_count': 4,
                'corrections_needed': 0.5,
                'score': 0.7
            }
        
        return {
            'time_to_usable_result': round(session_metrics.get('avg_time_to_result', 60), 1),
            'iterations_required': round(session_metrics.get('avg_iterations', 1), 2),
            'turns_count': round(session_metrics.get('avg_turns', 4), 1),
            'corrections_needed': round(session_metrics.get('avg_corrections', 0.5), 2),
            'score': round(session_metrics.get('avg_ux_score', 0.7), 3)
        }


def analyze_ux(output: str, duration: float, complexity: str = "medium") -> Dict[str, Any]:
    """Convenience function."""
    analyzer = UserExperienceAnalyzer()
    return analyzer.analyze_interaction(output, duration, complexity)


if __name__ == "__main__":
    # Test
    test_output = """
    I've created the file. Here's what I did:
    
    1. Read the existing config
    2. Added the new section
    3. Verified the syntax
    
    To summarize: The task is complete. You can find the output at output.json.
    """
    
    analyzer = UserExperienceAnalyzer()
    result = analyzer.analyze_interaction(test_output, 5.2, "medium")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    # Test correction detection
    test_bad = """
    Actually, wait - I made a mistake. Let me retry.
    Actually, I should reconsider the approach. Let me fix this.
    """
    
    analyzer = UserExperienceAnalyzer()
    bad_result = analyzer.analyze_interaction(test_bad, 10.0, "medium")
    print("Bad UX:", bad_result['ux_score'])
    
    good_result = analyzer.analyze_interaction(test_output, 5.0, "medium")
    print("Good UX:", good_result['ux_score'])