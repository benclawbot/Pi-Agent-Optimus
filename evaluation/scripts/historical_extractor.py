#!/usr/bin/env python3
"""
Historical Prompt Extractor - Extracts tasks from Pi agent session logs.
Extracts relevant prompts that can be used as evaluation tasks.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class HistoricalExtractor:
    """Extracts evaluation tasks from session logs."""
    
    def __init__(self, sessions_dir: str = None):
        if sessions_dir is None:
            sessions_dir = Path.home() / ".pi/agent/sessions"
        self.sessions_dir = Path(sessions_dir)
        
        # Categories for classification
        self.category_keywords = {
            "code-quality": ["create", "write", "implement", "function", "class", "python", "javascript", "refactor", "code"],
            "debug": ["fix", "debug", "error", "bug", "issue", "problem", "crash", "exception"],
            "architecture": ["design", "architecture", "system", "service", "api", "microservice", "structure"],
            "refactor": ["refactor", "improve", "clean", "restructure", "rewrite", "simplify"]
        }
    
    def extract(self, max_tasks: int = 20) -> List[Dict[str, Any]]:
        """
        Extract tasks from session logs.
        
        Returns:
            List of task dictionaries
        """
        session_files = self._find_session_files()
        
        tasks = []
        seen_prompts = set()
        
        for session_file in session_files:
            if len(tasks) >= max_tasks:
                break
            
            session_tasks = self._extract_from_session(session_file, seen_prompts)
            tasks.extend(session_tasks)
            seen_prompts.update(t['prompt'] for t in session_tasks)
        
        return tasks[:max_tasks]
    
    def _find_session_files(self) -> List[Path]:
        """Find all session log files."""
        
        if not self.sessions_dir.exists():
            return []
        
        jsonl_files = list(self.sessions_dir.glob("**/*.jsonl"))
        
        # Sort by modification time (most recent first)
        jsonl_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        return jsonl_files[:50]  # Limit to last 50 session files
    
    def _extract_from_session(
        self,
        session_file: Path,
        seen_prompts: set
    ) -> List[Dict[str, Any]]:
        """Extract tasks from a single session file."""
        
        tasks = []
        
        try:
            with open(session_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # Look for user messages
                    if entry.get("type") == "message":
                        msg = entry.get("message", {})
                        if msg.get("role") == "user":
                            content = self._extract_content(msg.get("content", []))
                            
                            if content and len(content) > 20:  # Minimum length
                                prompt_hash = hash(content)
                                if prompt_hash not in seen_prompts:
                                    category = self._classify(content)
                                    
                                    if category:
                                        task = {
                                            "name": self._generate_task_name(content),
                                            "category": category,
                                            "description": content,
                                            "prompt": content,
                                            "source_session": session_file.name,
                                            "timestamp": entry.get("timestamp"),
                                            "source": "historical"
                                        }
                                        tasks.append(task)
                                    
                    if len(tasks) >= 5:  # Max 5 tasks per session
                        break
                        
        except Exception as e:
            pass  # Skip problematic files
        
        return tasks
    
    def _extract_content(self, content: List[Dict]) -> str:
        """Extract text content from message."""
        
        if isinstance(content, str):
            return content
        
        text_parts = []
        
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif item.get("type") == "input_image":
                        pass  # Skip images for now
        
        return "\n".join(text_parts)
    
    def _classify(self, text: str) -> Optional[str]:
        """Classify the prompt into a category."""
        
        text_lower = text.lower()
        
        scores = defaultdict(int)
        
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[category] += 1
        
        if scores:
            return max(scores, key=scores.get)
        
        return None
    
    def _generate_task_name(self, content: str) -> str:
        """Generate a task name from content."""
        
        # Take first meaningful phrase
        lines = content.strip().split("\n")
        first_line = lines[0].strip()
        
        # Remove common prefixes
        for prefix in ["Can you", "Please", "I need you to", "I want", "Help me", ""]:
            if first_line.startswith(prefix):
                first_line = first_line[len(prefix):].strip()
        
        # Truncate if too long
        if len(first_line) > 60:
            first_line = first_line[:57] + "..."
        
        # Clean up
        first_line = re.sub(r'[^\w\s\-]', '', first_line)
        
        return first_line if first_line else "Untitled Task"
    
    def save_tasks(self, tasks: List[Dict], output_dir: Path):
        """Save extracted tasks to files."""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, task in enumerate(tasks, 1):
            filename = f"{i:02d}_{task['category']}_{task['name'][:30].replace(' ', '-')}.json"
            filename = re.sub(r'[^\w\-.]', '', filename)
            
            filepath = output_dir / filename
            
            with open(filepath, "w") as f:
                json.dump(task, f, indent=2)
            
            print(f"  → {filepath.name}")


def main():
    """Command-line interface."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract tasks from historical sessions")
    parser.add_argument("--max", type=int, default=20, help="Maximum tasks to extract")
    parser.add_argument("--output", help="Output directory (default: ../tasks/historical)")
    parser.add_argument("--dry-run", action="store_true", help="Show tasks without saving")
    
    args = parser.parse_args()
    
    extractor = HistoricalExtractor()
    
    print(f"🔍 Scanning session logs...")
    tasks = extractor.extract(max_tasks=args.max)
    
    print(f"\n📋 Found {len(tasks)} tasks:")
    for t in tasks:
        print(f"  [{t['category']}] {t['name'][:50]}")
    
    if args.dry_run:
        return
    
    if args.output:
        output_dir = Path(args.output)
    else:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / "tasks" / "historical"
    
    print(f"\n💾 Saving to {output_dir}...")
    extractor.save_tasks(tasks, output_dir)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()