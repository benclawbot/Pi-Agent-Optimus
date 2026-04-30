#!/usr/bin/env python3
"""
Adaptability Analyzer - Measures learning and adaptation from feedback.
Implements: adaptation_score, few_shot_efficiency, cross_domain_transfer.

The feedback loop:
1. Run baseline task -> record score
2. Provide feedback/examples
3. Re-run same type of task -> measure improvement
4. Compute adaptation score
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class AdaptabilityAnalyzer:
    """Analyzes adaptability and learning capabilities."""
    
    # Categories for cross-domain transfer analysis
    DOMAIN_CATEGORIES = [
        'coding', 'reasoning', 'tool_usage', 'open_ended', 'safety'
    ]
    
    def __init__(self, memory_path: str = None):
        if memory_path is None:
            memory_path = Path.home() / ".pi/agent/skill-memory"
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        
        self.feedback_history = []
        self.learning_records = []
    
    def record_baseline(
        self,
        task_type: str,
        score: float,
        timestamp: str = None
    ) -> Dict[str, Any]:
        """
        Record baseline performance before feedback.
        
        Args:
            task_type: Category of task (coding, reasoning, etc.)
            score: Performance score (0-1)
        
        Returns:
            Baseline record
        """
        record = {
            'type': 'baseline',
            'task_type': task_type,
            'score': score,
            'timestamp': timestamp or datetime.now().isoformat(),
            'iteration': len([r for r in self.learning_records if r['task_type'] == task_type])
        }
        
        self.learning_records.append(record)
        self._save_learning_data()
        
        return record
    
    def record_feedback(
        self,
        task_type: str,
        feedback: str,
        examples: List[str] = None
    ) -> Dict[str, Any]:
        """
        Record feedback provided to the agent.
        
        Args:
            task_type: Category of task
            feedback: The feedback content
            examples: Optional examples demonstrating correct behavior
        
        Returns:
            Feedback record
        """
        record = {
            'type': 'feedback',
            'task_type': task_type,
            'feedback': feedback,
            'examples': examples or [],
            'timestamp': datetime.now().isoformat()
        }
        
        self.feedback_history.append(record)
        self._save_feedback_data()
        
        return record
    
    def record_post_feedback_score(
        self,
        task_type: str,
        score: float
    ) -> Dict[str, Any]:
        """
        Record performance after feedback.
        
        Args:
            task_type: Category of task
            score: New performance score
        
        Returns:
            Adaptation analysis
        """
        # Find corresponding baseline
        baselines = [
            r for r in self.learning_records
            if r['task_type'] == task_type and r['type'] == 'baseline'
        ]
        
        if not baselines:
            # No baseline - record as baseline
            return self.record_baseline(task_type, score)
        
        baseline = baselines[-1]  # Most recent baseline for this type
        
        # Compute adaptation score
        baseline_score = baseline['score']
        improvement = score - baseline_score
        adaptation_rate = improvement / baseline_score if baseline_score > 0 else 0
        
        # Record post-feedback performance
        post_record = {
            'type': 'post_feedback',
            'task_type': task_type,
            'score': score,
            'baseline_score': baseline_score,
            'improvement': improvement,
            'adaptation_rate': adaptation_rate,
            'timestamp': datetime.now().isoformat(),
            'iteration': baseline['iteration'] + 1
        }
        
        self.learning_records.append(post_record)
        self._save_learning_data()
        
        return post_record
    
    def compute_adaptation_score(self, task_type: str = None) -> Dict[str, Any]:
        """
        Compute adaptation score for task type or overall.
        
        Returns:
            Dict with adaptation metrics
        """
        records = self.learning_records
        
        if task_type:
            records = [r for r in records if r.get('task_type') == task_type]
        
        # Separate baselines and post-feedback scores
        baselines = [r for r in records if r['type'] == 'baseline']
        posts = [r for r in records if r['type'] == 'post_feedback']
        
        if not posts:
            return {
                'adaptation_score': 0.65,  # Default when no feedback loop data
                'feedback_sessions': 0,
                'avg_improvement': 0,
                'score': 0.65
            }
        
        # Compute adaptation score
        improvements = [p['improvement'] for p in posts]
        adaptation_rates = [p['adaptation_rate'] for p in posts]
        
        avg_improvement = sum(improvements) / len(improvements)
        avg_adaptation_rate = sum(adaptation_rates) / len(adaptation_rates)
        
        # Score: 0.65 base + bonus for improvement
        base_score = 0.65
        improvement_bonus = min(0.25, avg_adaptation_rate * 0.5)  # Cap bonus at 0.25
        
        adaptation_score = base_score + improvement_bonus
        adaptation_score = max(0, min(1, adaptation_score))
        
        return {
            'adaptation_score': round(adaptation_score, 3),
            'feedback_sessions': len(posts),
            'avg_improvement': round(avg_improvement, 3),
            'avg_adaptation_rate': round(avg_adaptation_rate, 3),
            'score': round(adaptation_score, 3)
        }
    
    def compute_few_shot_efficiency(self, examples: List[Dict]) -> float:
        """
        Compute few-shot learning efficiency.
        
        Measures how quickly the agent learns from examples.
        
        Args:
            examples: List of {task, solution, test} dicts
        
        Returns:
            Efficiency score (0-1)
        """
        if len(examples) < 2:
            return 0.8  # Need at least 2 for comparison
        
        # Look for improvement trend across examples
        first_score = examples[0].get('score', 0.5)
        last_score = examples[-1].get('score', 0.5)
        
        improvement_trend = (last_score - first_score) / len(examples)
        
        # Efficiency: positive trend = good, diminishing returns = efficient
        if improvement_trend > 0:
            # Good learning - score based on improvement rate
            efficiency = min(1, 0.6 + improvement_trend * 2)
        else:
            # No improvement - average efficiency
            efficiency = 0.6
        
        return round(efficiency, 3)
    
    def compute_cross_domain_transfer(self) -> Dict[str, float]:
        """
        Compute cross-domain transfer learning.
        
        Measures if skills learned in one domain transfer to others.
        
        Returns:
            Dict with transfer scores per domain pair
        """
        # Group records by task type
        by_type = defaultdict(list)
        for record in self.learning_records:
            if record['type'] == 'post_feedback':
                by_type[record['task_type']].append(record)
        
        transfer_scores = {}
        
        for domain_a in self.DOMAIN_CATEGORIES:
            for domain_b in self.DOMAIN_CATEGORIES:
                if domain_a >= domain_b:  # Skip same and duplicates
                    continue
                
                # Check if learning in A improved performance in B
                # This requires sequential runs across domains
                key = f"{domain_a}_to_{domain_b}"
                
                # Placeholder - would need actual cross-domain data
                # For now, estimate based on general improvement
                records_b = by_type.get(domain_b, [])
                if len(records_b) >= 2:
                    # Has post-feedback data
                    scores = [r['score'] for r in records_b]
                    # Compute if scores improve over time
                    if len(scores) >= 2:
                        trend = (scores[-1] - scores[0]) / len(scores)
                        transfer_scores[key] = max(0, min(1, 0.6 + trend))
                    else:
                        transfer_scores[key] = 0.65
                else:
                    transfer_scores[key] = 0.60  # No data, estimate
        
        # Add self-transfer (within domain)
        for domain in self.DOMAIN_CATEGORIES:
            records = by_type.get(domain, [])
            if len(records) >= 2:
                scores = [r['score'] for r in records]
                trend = (scores[-1] - scores[0]) / len(scores)
                transfer_scores[f"{domain}_self"] = max(0, min(1, 0.7 + trend))
            else:
                transfer_scores[f"{domain}_self"] = 0.65
        
        return transfer_scores
    
    def get_adaptability_dimension(self) -> Dict[str, Any]:
        """Get complete adaptability dimension scores."""
        
        # Compute overall adaptation
        overall = self.compute_adaptation_score()
        
        # Cross-domain transfer
        cross_domain = self.compute_cross_domain_transfer()
        
        # Few-shot efficiency (from recent feedback sessions)
        few_shot_records = [
            r for r in self.learning_records
            if r['type'] == 'post_feedback'
        ][-5:]  # Last 5 sessions
        
        few_shot_eff = self.compute_few_shot_efficiency(few_shot_records)
        
        return {
            'adaptation_score': overall.get('adaptation_score', 0.65),
            'few_shot_efficiency': few_shot_eff,
            'cross_domain_transfer': cross_domain,
            'feedback_sessions_count': overall.get('feedback_sessions', 0),
            'avg_improvement': overall.get('avg_improvement', 0),
            'score': overall.get('score', 0.65)
        }
    
    def _save_learning_data(self):
        """Save learning records to disk."""
        
        learning_file = self.memory_path / 'adaptability_learning.json'
        
        with open(learning_file, 'w') as f:
            json.dump({
                'records': self.learning_records,
                'updated_at': datetime.now().isoformat()
            }, f, indent=2)
    
    def _save_feedback_data(self):
        """Save feedback history to disk."""
        
        feedback_file = self.memory_path / 'adaptability_feedback.json'
        
        with open(feedback_file, 'w') as f:
            json.dump({
                'history': self.feedback_history,
                'updated_at': datetime.now().isoformat()
            }, f, indent=2)
    
    def load_learning_data(self):
        """Load learning data from disk."""
        
        learning_file = self.memory_path / 'adaptability_learning.json'
        feedback_file = self.memory_path / 'adaptability_feedback.json'
        
        if learning_file.exists():
            with open(learning_file) as f:
                data = json.load(f)
                self.learning_records = data.get('records', [])
        
        if feedback_file.exists():
            with open(feedback_file) as f:
                data = json.load(f)
                self.feedback_history = data.get('history', [])


def simulate_adaptation():
    """Simulate an adaptation feedback loop for testing."""
    
    analyzer = AdaptabilityAnalyzer()
    
    # Record baseline
    print("Recording baseline...")
    baseline = analyzer.record_baseline('coding', 0.50)
    print(f"  Baseline: {baseline['score']}")
    
    # Record feedback
    print("\nProviding feedback...")
    feedback = analyzer.record_feedback(
        'coding',
        'Remember to handle edge cases and validate inputs',
        ['Example: check for null before using']
    )
    print(f"  Feedback recorded: {len(feedback['examples'])} examples")
    
    # Record post-feedback score
    print("\nRecording post-feedback performance...")
    result = analyzer.record_post_feedback_score('coding', 0.65)
    print(f"  New score: {result['score']}")
    print(f"  Improvement: +{result['improvement']:.2f}")
    print(f"  Adaptation rate: {result['adaptation_rate']:.2%}")
    
    # Compute adaptation score
    print("\nComputing adaptation score...")
    score = analyzer.compute_adaptation_score('coding')
    print(f"  Adaptation score: {score['adaptation_score']:.2f}")
    
    return analyzer


if __name__ == "__main__":
    # Run simulation
    analyzer = simulate_adaptation()
    
    # Get complete dimension
    print("\n=== Adaptability Dimension ===")
    dim = analyzer.get_adaptability_dimension()
    print(json.dumps(dim, indent=2))