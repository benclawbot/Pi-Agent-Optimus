#!/usr/bin/env python3
"""
Proactivity Detector - Analyzes traces and outputs for proactive behaviors.
Proactivity = proposing next steps without waiting for user input.
"""

import json
import re
from typing import Dict, Any, List, Tuple
from pathlib import Path


class ProactivityDetector:
    """Detects proactive behaviors in agent execution."""
    
    # Patterns that indicate proactive behavior
    PROACTIVE_PATTERNS = {
        # Proposed next steps without being asked
        "proposed_next_steps": [
            r"(?i)suggest(?:ed|ing)?:",
            r"(?i)i can (?:also|additionally)?",
            r"(?i)would you like me to",
            r"(?i)i could also",
            r"(?i)next steps?(?: might be| could be)?:",
            r"(?i)you might also want to",
            r"(?i)recommend(?:ed)?:",
            r"(?i)consider (?:also|adding)",
        ],
        
        # Took action without waiting
        "unprompted_action": [
            r"(?i)i'?ll (?:go ahead and|just|now)",
            r"(?i)automatically",
            r"(?i)without waiting",
            r"(?i)going ahead with",
            r"(?i)i'?ve (?:already |just )?(?:created|written|updated|added|fixed)",
            r"(?i)proceeding with",
        ],
        
        # Volunteered information
        "volunteered_info": [
            r"(?i)note that",
            r"(?i)FYI:",
            r"(?i)worth noting",
            r"(?i)just so you know",
            r"(?i)i'?ve noticed that",
            r"(?i)you should be aware that",
        ],
        
        # Parallel/background actions
        "parallel_action": [
            r"(?i)while you'?re",
            r"(?i)in parallel",
            r"(?i)at the same time",
            r"(?i)simultaneously",
        ],
        
        # Offered alternatives
        "offered_alternatives": [
            r"(?i)alternatively:",
            r"(?i)another option",
            r"(?i)you could also",
            r"(?i)if you prefer",
        ]
    }
    
    # Patterns that indicate waiting for user (reactive behavior)
    REACTIVE_PATTERNS = [
        r"(?i)should i",
        r"(?i)do you want me to",
        r"(?i)let me know if",
        r"(?i)wait(?:ing)? for",
        r"(?i)please confirm",
        r"(?i)is this okay",
        r"(?i)let me know when",
    ]
    
    def __init__(self, config: Dict):
        self.config = config
        self.proactivity_config = config["metrics"]["proactivity"]
        self.patterns = self.proactivity_config.get("patterns", [])
    
    def analyze(
        self,
        trace: List[Dict],
        output: str
    ) -> Dict[str, Any]:
        """
        Analyze execution for proactivity indicators.
        
        Returns:
            Dict with proactivity score and breakdown
        """
        # Combine trace and output for analysis
        full_text = output + "\n".join([
            str(entry) for entry in trace
            if isinstance(entry, dict)
        ])
        
        # Detect patterns
        detected = self._detect_patterns(full_text)
        
        # Count unprompted skill activations
        skill_activations = self._count_skill_activations(trace)
        
        # Compute overall proactivity score
        score = self._compute_proactivity_score(detected, skill_activations)
        
        return {
            "score": score,
            "detected_patterns": detected,
            "skill_activations_unprompted": skill_activations,
            "proactive_ratio": self._compute_proactive_ratio(detected),
            "waited_for_user": self._detected_waiting(full_text),
            "breakdown": {
                "proposed_next_steps": len(detected.get("proposed_next_steps", [])),
                "unprompted_action": len(detected.get("unprompted_action", [])),
                "volunteered_info": len(detected.get("volunteered_info", [])),
                "parallel_action": len(detected.get("parallel_action", [])),
                "offered_alternatives": len(detected.get("offered_alternatives", [])),
            }
        }
    
    def _detect_patterns(self, text: str) -> Dict[str, List[str]]:
        """Detect all proactive patterns in text."""
        
        detected = {}
        
        for category, patterns in self.PROACTIVE_PATTERNS.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text)
                matches.extend(found)
            
            if matches:
                detected[category] = matches
        
        return detected
    
    def _count_skill_activations(self, trace: List[Dict]) -> int:
        """
        Count skill activations that weren't explicitly requested.
        This would need access to actual skill activation data from the trace.
        """
        
        # Look for skill-related entries in trace
        skill_patterns = [
            r"skill:\s*(\w+)",
            r"activating skill",
            r"skill activated",
            r"using skill",
        ]
        
        count = 0
        for entry in trace:
            if isinstance(entry, dict):
                entry_str = json.dumps(entry)
                for pattern in skill_patterns:
                    if re.search(pattern, entry_str, re.IGNORECASE):
                        count += 1
                        break
        
        return count
    
    def _compute_proactivity_score(
        self,
        detected: Dict[str, List],
        skill_activations: int
    ) -> float:
        """
        Compute proactivity score (0-5).
        
        Score breakdown:
        - Proposing next steps: up to 2 points
        - Unprompted actions: up to 1.5 points
        - Volunteered info: up to 0.5 points
        - Offered alternatives: up to 0.5 points
        - Skill activations: up to 0.5 points
        """
        
        score = 0.0
        
        # Proposing next steps (max 2 points)
        proposed = sum(len(matches) for matches in detected.get("proposed_next_steps", []))
        score += min(proposed * 0.4, 2.0)
        
        # Unprompted actions (max 1.5 points)
        unprompted = sum(len(matches) for matches in detected.get("unprompted_action", []))
        score += min(unprompted * 0.5, 1.5)
        
        # Volunteered info (max 0.5 points)
        volunteered = sum(len(matches) for matches in detected.get("volunteered_info", []))
        score += min(volunteered * 0.25, 0.5)
        
        # Offered alternatives (max 0.5 points)
        alternatives = sum(len(matches) for matches in detected.get("offered_alternatives", []))
        score += min(alternatives * 0.25, 0.5)
        
        # Skill activations (max 0.5 points)
        score += min(skill_activations * 0.25, 0.5)
        
        # Cap at 5.0
        return min(score, 5.0)
    
    def _compute_proactive_ratio(self, detected: Dict[str, List]) -> float:
        """Compute ratio of proactive to total actions detected."""
        
        proactive_count = sum(len(matches) for matches in detected.values())
        
        if proactive_count == 0:
            return 0.0
        
        # Normalize to 0-1
        return min(proactive_count / 5.0, 1.0)
    
    def _detected_waiting(self, text: str) -> bool:
        """Check if agent was waiting for user input."""
        
        for pattern in self.REACTIVE_PATTERNS:
            if re.search(pattern, text):
                return True
        
        return False
    
    def suggest_improvements(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements based on proactivity analysis.
        
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        score = analysis.get("score", 0)
        
        if score < 1.5:
            suggestions.append("Low proactivity: Try to propose next steps before being asked")
        
        if analysis.get("waited_for_user", False):
            suggestions.append("Agent waited for user confirmation - consider acting autonomously")
        
        breakdown = analysis.get("breakdown", {})
        
        if breakdown.get("proposed_next_steps", 0) == 0:
            suggestions.append("Consider adding 'next steps' section to output")
        
        if breakdown.get("unprompted_action", 0) == 0:
            suggestions.append("Try to take initiative on routine tasks")
        
        if breakdown.get("offered_alternatives", 0) == 0:
            suggestions.append("When appropriate, offer alternative approaches")
        
        return suggestions


def detect_proactivity(output: str, trace: List[Dict] = None) -> Dict[str, Any]:
    """Convenience function for proactivity detection."""
    
    config = {
        "metrics": {
            "proactivity": {
                "patterns": [
                    "suggested:",
                    "i'll go ahead and",
                    "would you like me to",
                    "automatically",
                    "while you're"
                ]
            }
        }
    }
    
    detector = ProactivityDetector(config)
    return detector.analyze(output, trace or [])


if __name__ == "__main__":
    # Test with sample output
    test_output = """
    I've created the main.py file with the requested function.
    
    Suggested: You might also want to add:
    - Unit tests for the function
    - Documentation comments
    - Type hints
    
    I'll go ahead and add the type hints now.
    
    Alternatively, we could use a decorator-based approach.
    """
    
    test_trace = [
        {"type": "skill_activation", "skill": "auto-test"}
    ]
    
    detector = ProactivityDetector({
        "metrics": {
            "proactivity": {
                "patterns": ["suggested:", "i'll go ahead and", "would you like me to"]
            }
        }
    })
    
    result = detector.analyze(test_trace, test_output)
    print(json.dumps(result, indent=2))
    
    # Show suggestions
    suggestions = detector.suggest_improvements(result)
    if suggestions:
        print("\n📋 Suggestions:")
        for s in suggestions:
            print(f"  - {s}")