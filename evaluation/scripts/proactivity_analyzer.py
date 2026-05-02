#!/usr/bin/env python3
"""
Proactivity Analyzer - Scores proactivity across 6 phases.
"""

import json
import re
from typing import Dict, List, Any
from dataclasses import dataclass

# Phase patterns for detection
PHASE_PATTERNS = {
    "start": {
        "clarifying_questions": [
            r"\?$",
            r"(?i)(what|how|when|where|why|which)",
            r"(?i)could you clarify",
            r"(?i)quick question",
            r"(?i)need to know",
            r"(?i)scale|users|constraints",
        ],
        "structured_plan": [
            r"(?i)here'?s (my )?plan",
            r"(?i)step \d+[:\.]",
            r"(?i)(first|second|third|finally)",
            r"(?i)(approach|strategy)",
            r"(?i)1\)[ \t].*2\)[ \t].*3\)",
        ],
        "ambiguity_detection": [
            r"(?i)(unclear|ambiguous|vague)",
            r"(?i)assuming",
            r"(?i)i'?ll interpret",
        ]
    },
    "execution": {
        "inefficiency_detection": [
            r"(?i)(slow|inefficient|bottleneck)",
            r"(?i)could optimize",
            r"(?i)better approach",
            r"(?i)this is taking",
        ],
        "adaptation": [
            r"(?i)switching to",
            r"(?i)let'?s try a different",
            r"(?i)instead of",
            r"(?i)pivot",
            r"(?i)changing my approach",
        ],
        "strategy_switch": [
            r"(?i)alternative",
            r"(?i)rather than",
            r"(?i)will use",
        ]
    },
    "completion": {
        "improvement_suggestions": [
            r"(?i)(could|should) be (enhanced|improved|better)",
            r"(?i)future enhancement",
            r"(?i)optimization",
            r"(?i)next (steps?|thing)",
        ],
        "next_steps": [
            r"(?i)next steps? (you might consider|:)",
            r"(?i)follow[-\s]?up",
            r"(?i)after this",
            r"(?i)you might also",
            r"(?i)i can also",
        ],
        "risk_identification": [
            r"(?i)be careful",
            r"(?i)watch out",
            r"(?i)(potential )?risk",
            r"(?i)caution",
            r"(?i)before (implementing|deploying)",
            r"(?i)note that",
        ]
    },
    "feedback": {
        "generalization": [
            r"(?i)applying this to",
            r"(?i)generalizing",
            r"(?i)across all",
        ],
        "future_application": [
            r"(?i)in the future",
            r"(?i)will use this",
            r"(?i)remember to",
        ],
        "system_improvement": [
            r"(?i)should update.*system",
            r"(?i)add this to.*guidelines",
            r"(?i)proactively check",
        ]
    },
    "memory": {
        "prior_reference": [
            r"(?i)as we discussed",
            r"(?i)from.*earlier",
            r"(?i)remember",
            r"(?i)in our previous",
        ],
        "pattern_reuse": [
            r"(?i)same pattern as",
            r"(?i)similar to",
            r"(?i)following the same",
        ],
        "optimization_proposal": [
            r"(?i)now that.*we can",
            r"(?i)with.*done, we should",
        ]
    },
    "idle": {
        "opportunity_detection": [
            r"(?i)noticed.*could improve",
            r"(?i)i see an opportunity",
            r"(?i)while we'?re here",
        ],
        "anomaly_identification": [
            r"(?i)unusual",
            r"(?i)inconsistent",
            r"(?i)doesn'?t match",
            r"(?i)out of place",
        ],
        "automation_proposal": [
            r"(?i)could automate",
            r"(?i)let me create a script",
            r"(?i)add this to.*ci",
        ]
    }
}

# Anti-patterns (reduce score)
ANTI_PATTERNS = [
    r"(?i)not sure if this is right",  # Hedging
    r"(?i)probably should",  # Low confidence
    r"(?i)i'?ll just",  # Passivity
    r"(?i)whatever you prefer",  # No initiative
]


@dataclass
class ProactivityEvent:
    phase: str
    category: str
    text: str
    accepted: bool = False


class ProactivityAnalyzer:
    """Analyzes proactivity across task lifecycle phases."""
    
    def __init__(self):
        self.events: List[ProactivityEvent] = []
        self.phase_weights = {
            "start": 0.20,
            "execution": 0.25,
            "completion": 0.20,
            "feedback": 0.15,
            "memory": 0.10,
            "idle": 0.10
        }
    
    def analyze_output(self, output: str, phase: str = None) -> Dict[str, Any]:
        """Analyze output for proactivity signals."""
        
        scores = {}
        events = []
        
        # If specific phase, only check that phase
        phases_to_check = [phase] if phase else PHASE_PATTERNS.keys()
        
        for p in phases_to_check:
            if p not in PHASE_PATTERNS:
                continue
            
            phase_score = 0
            phase_max = 0
            
            for category, patterns in PHASE_PATTERNS[p].items():
                max_score = 2 if category != "ambiguity_detection" else 1
                phase_max += max_score
                
                # Count pattern matches
                matches = sum(1 for pat in patterns if re.search(pat, output))
                category_score = min(matches, max_score)
                phase_score += category_score
                
                if matches > 0:
                    events.append(ProactivityEvent(
                        phase=p,
                        category=category,
                        text=output[:200]
                    ))
            
            # Normalize to 0-1
            scores[p] = phase_score / phase_max if phase_max > 0 else 0
        
        # Calculate anti-pattern penalty
        anti_count = sum(1 for pat in ANTI_PATTERNS if re.search(pat, output))
        anti_penalty = min(anti_count * 0.05, 0.3)
        
        # Calculate weighted score
        weighted_score = sum(
            scores.get(p, 0) * self.phase_weights[p]
            for p in self.phase_weights
        )
        
        # Apply penalty
        final_score = max(0, weighted_score - anti_penalty)
        
        return {
            "phase_scores": scores,
            "weighted_score": final_score,
            "anti_pattern_penalty": anti_penalty,
            "events": [
                {"phase": e.phase, "category": e.category}
                for e in events
            ],
            "initiative_count": len(events),
            "precision": self._calculate_precision(events)
        }
    
    def _calculate_precision(self, events: List[ProactivityEvent]) -> float:
        """
        Precision = useful suggestions / total suggestions.
        In the absence of user feedback, estimate based on quality heuristics.
        """
        if not events:
            return 0.5  # Neutral
        
        # Penalize if too many events (noise)
        if len(events) > 10:
            return 0.3
        
        # Reward balanced events across phases
        phases = set(e.phase for e in events)
        if len(phases) >= 3:
            return 0.8
        
        return 0.6
    
    def analyze_benchmark_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze full benchmark results."""
        
        phase_totals = {p: 0 for p in self.phase_weights}
        phase_counts = {p: 0 for p in self.phase_weights}
        
        for r in results:
            output = r.get("output", "")
            phase = r.get("phase", "completion")
            
            analysis = self.analyze_output(output, phase)
            
            if phase in phase_totals:
                phase_totals[phase] += analysis["phase_scores"].get(phase, 0)
                phase_counts[phase] += 1
        
        # Average per phase
        phase_averages = {
            p: phase_totals[p] / phase_counts[p] if phase_counts[p] > 0 else 0
            for p in self.phase_weights
        }
        
        # Overall score
        overall = sum(
            phase_averages[p] * self.phase_weights[p]
            for p in self.phase_weights
        )
        
        return {
            "overall_score": overall,
            "phase_scores": phase_averages,
            "initiative_rate": sum(phase_counts.values()) / len(results) if results else 0,
            "total_events": sum(phase_counts.values()),
            "precision_estimate": overall * 0.7  # Conservative estimate
        }


def main():
    """CLI for testing."""
    import sys
    
    analyzer = ProactivityAnalyzer()
    
    test_outputs = [
        ("completion", "I've created the file. Next steps: test it, then deploy. You might also want to add error handling. Be careful about race conditions."),
        ("start", "I need some clarification: what's the expected scale? Who's the target user? Here's my plan: first analyze, then implement, finally test."),
        ("execution", "This approach is slow. Let me switch to a different strategy instead."),
    ]
    
    print("=" * 60)
    print("PROACTIVITY ANALYSIS")
    print("=" * 60)
    
    for phase, output in test_outputs:
        print(f"\n[{phase.upper()}]")
        print(f"Output: {output[:80]}...")
        result = analyzer.analyze_output(output, phase)
        print(f"Score: {result['weighted_score']:.2f}")
        print(f"Events: {result['initiative_count']}")
        print(f"Phases detected: {list(result['phase_scores'].keys())}")


if __name__ == "__main__":
    main()
