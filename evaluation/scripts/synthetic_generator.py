#!/usr/bin/env python3
"""
Synthetic Task Generator - Creates test tasks based on failure patterns.
When issues are detected, this generates synthetic probes to test for those patterns.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class SyntheticTaskGenerator:
    """Generates synthetic evaluation tasks based on failure patterns."""
    
    # Task templates by category
    TEMPLATES = {
        "code-quality": [
            {
                "name_pattern": "{topic} Implementation",
                "description": "Implement a {topic} component following best practices. The code should be clean, efficient, and well-documented.",
                "requirements": [
                    "Clean, readable code structure",
                    "Proper error handling",
                    "Appropriate data structures",
                    "Type hints if applicable"
                ],
                "difficulty": "medium"
            },
            {
                "name_pattern": "{topic} with Validation",
                "description": "Create a {topic} implementation with comprehensive input validation and error handling.",
                "requirements": [
                    "Validate all inputs",
                    "Handle edge cases gracefully",
                    "Clear error messages",
                    "No hardcoded values"
                ],
                "difficulty": "medium"
            }
        ],
        "debug": [
            {
                "name_pattern": "Fix {topic} Issue",
                "description": "Debug and fix the {topic} problem. Identify the root cause and implement a proper fix.",
                "requirements": [
                    "Identify root cause",
                    "Fix without breaking existing functionality",
                    "Add test case for the bug",
                    "Explain the fix"
                ],
                "difficulty": "medium"
            },
            {
                "name_pattern": "Handle {topic} Error",
                "description": "The system is failing when encountering {topic}. Find and fix the issue.",
                "requirements": [
                    "Reproduce the error scenario",
                    "Identify the failure point",
                    "Implement fix",
                    "Verify the fix works"
                ],
                "difficulty": "medium"
            }
        ],
        "architecture": [
            {
                "name_pattern": "Design {topic} System",
                "description": "Design an architecture for {topic}. Define components, interactions, and data flow.",
                "requirements": [
                    "Clear component boundaries",
                    "Scalable design",
                    "Consistent patterns",
                    "Consider failure modes"
                ],
                "difficulty": "hard"
            },
            {
                "name_pattern": "Refactor {topic} Architecture",
                "description": "Current {topic} architecture has issues. Propose and implement a refactored design.",
                "requirements": [
                    "Identify current problems",
                    "Propose improved architecture",
                    "Plan migration path",
                    "Maintain backward compatibility"
                ],
                "difficulty": "hard"
            }
        ],
        "refactor": [
            {
                "name_pattern": "Clean {topic} Code",
                "description": "Refactor the {topic} code to improve readability and maintainability.",
                "requirements": [
                    "Reduce complexity",
                    "Improve naming",
                    "Add documentation",
                    "Maintain behavior"
                ],
                "difficulty": "medium"
            },
            {
                "name_pattern": "Extract {topic} Component",
                "description": "Extract the {topic} functionality into a reusable component.",
                "requirements": [
                    "Clear interface",
                    "Minimal dependencies",
                    "Comprehensive tests",
                    "Documentation"
                ],
                "difficulty": "medium"
            }
        ]
    }
    
    # Topic generators by failure type
    FAILURE_TOPICS = {
        "error_handling": ["null reference", "file not found", "connection timeout", "invalid input", "resource exhausted"],
        "concurrency": ["race condition", "deadlock", "thread safety", "async callback", "shared state"],
        "memory": ["memory leak", "object retention", "cache overflow", "large allocation", "circular reference"],
        "api_design": ["inconsistent naming", "missing validation", "poor error responses", "version mismatch", "auth flow"],
        "data_handling": ["sql injection", "data race", "transaction rollback", "constraint violation", "serialization"],
        "testing": ["edge case", "failure recovery", "timeout handling", "retry logic", "fallback behavior"]
    }
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "tasks" / "synthetic"
    
    def generate_from_failure(
        self,
        failure: Dict[str, Any],
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic tasks based on a failure pattern.
        
        Args:
            failure: Dict with 'type' and 'description' keys
            count: Number of tasks to generate
        
        Returns:
            List of task dictionaries
        """
        
        failure_type = failure.get("type", "generic")
        description = failure.get("description", "")
        
        # Find relevant topics
        topics = self.FAILURE_TOPICS.get(failure_type, ["general issue"])
        
        tasks = []
        
        for i, topic in enumerate(topics[:count]):
            category = self._infer_category(failure_type, description)
            
            templates = self.TEMPLATES.get(category, self.TEMPLATES["code-quality"])
            template = templates[i % len(templates)]
            
            task = self._build_task(template, topic, category, failure)
            tasks.append(task)
        
        return tasks
    
    def generate_category_tasks(
        self,
        category: str,
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate tasks for a specific category."""
        
        templates = self.TEMPLATES.get(category, [])
        
        if not templates:
            return []
        
        tasks = []
        
        # Get topics for this category
        category_topics = {
            "code-quality": ["function", "class", "module", "utility", "handler"],
            "debug": ["crash", "exception", "timeout", "corruption", "mismatch"],
            "architecture": ["service", "pipeline", "cache", "queue", "gateway"],
            "refactor": ["legacy code", "duplication", "complexity", "coupling", "abstraction"]
        }
        
        topics = category_topics.get(category, ["component"])
        
        for i in range(count):
            topic = topics[i % len(topics)]
            template = templates[i % len(templates)]
            
            task = self._build_task(template, topic, category, {})
            tasks.append(task)
        
        return tasks
    
    def _build_task(
        self,
        template: Dict,
        topic: str,
        category: str,
        failure: Dict
    ) -> Dict[str, Any]:
        """Build a task from a template."""
        
        name = template["name_pattern"].format(topic=topic)
        
        task = {
            "name": name,
            "category": category,
            "description": template["description"].format(topic=topic),
            "requirements": template["requirements"],
            "difficulty": template["difficulty"],
            "source": "synthetic",
            "generated_at": datetime.now().isoformat(),
            "triggered_by_failure": failure.get("type") if failure else None
        }
        
        # Add context from failure if available
        if failure and "context" in failure:
            task["context"] = failure["context"]
        
        # Add expected behavior
        task["expected"] = self._generate_expected(category, topic)
        
        # Estimate time based on difficulty
        time_estimates = {"easy": 60, "medium": 120, "hard": 180}
        task["estimated_time_seconds"] = time_estimates.get(template["difficulty"], 120)
        
        return task
    
    def _infer_category(self, failure_type: str, description: str) -> str:
        """Infer category from failure type."""
        
        category_map = {
            "error_handling": "code-quality",
            "concurrency": "debug",
            "memory": "debug",
            "api_design": "architecture",
            "data_handling": "code-quality",
            "testing": "refactor"
        }
        
        return category_map.get(failure_type, "code-quality")
    
    def _generate_expected(self, category: str, topic: str) -> str:
        """Generate expected behavior description."""
        
        expectations = {
            "code-quality": f"Clean, well-documented {topic} implementation",
            "debug": f"Fixed {topic} with explanation of root cause",
            "architecture": f"Designed {topic} with clear component boundaries",
            "refactor": f"Refactored {topic} with improved maintainability"
        }
        
        return expectations.get(category, f"Complete {topic} task")
    
    def save_tasks(self, tasks: List[Dict], category: str):
        """Save generated tasks to files."""
        
        category_dir = self.output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Find existing files to determine next number
        existing = list(category_dir.glob("*.json"))
        start_num = len(existing) + 1
        
        for i, task in enumerate(tasks, start_num):
            filename = f"{i:02d}_{task['name'][:30].replace(' ', '-')}.json"
            filename = "".join(c if c.isalnum() or c in '.-' else '_' for c in filename)
            
            filepath = category_dir / filename
            
            with open(filepath, "w") as f:
                json.dump(task, f, indent=2)
            
            print(f"  → {category}/{filepath.name}")


def main():
    """Command-line interface."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic evaluation tasks")
    parser.add_argument("--category", "-c", choices=["code-quality", "debug", "architecture", "refactor"],
                       help="Category to generate for")
    parser.add_argument("--count", type=int, default=5, help="Number of tasks to generate")
    parser.add_argument("--from-failure", "-f", help="JSON file with failure pattern")
    parser.add_argument("--dry-run", action="store_true", help="Show tasks without saving")
    
    args = parser.parse_args()
    
    generator = SyntheticTaskGenerator()
    
    if args.from_failure:
        # Generate from failure file
        with open(args.from_failure) as f:
            failure = json.load(f)
        
        tasks = generator.generate_from_failure(failure, count=args.count)
        
        print(f"🔧 Generated {len(tasks)} tasks from failure pattern: {failure.get('type', 'unknown')}")
    
    elif args.category:
        # Generate for category
        tasks = generator.generate_category_tasks(args.category, count=args.count)
        print(f"🔧 Generated {len(tasks)} tasks for category: {args.category}")
    
    else:
        # Generate for all categories
        tasks = []
        for category in ["code-quality", "debug", "architecture", "refactor"]:
            cat_tasks = generator.generate_category_tasks(category, count=3)
            tasks.extend(cat_tasks)
        print(f"🔧 Generated {len(tasks)} tasks across all categories")
    
    for t in tasks:
        print(f"  [{t['category']}] {t['name']}")
    
    if args.dry_run:
        return
    
    # Save tasks
    if args.category:
        generator.save_tasks(tasks, args.category)
    else:
        for category in ["code-quality", "debug", "architecture", "refactor"]:
            cat_tasks = [t for t in tasks if t["category"] == category]
            if cat_tasks:
                generator.save_tasks(cat_tasks, category)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()