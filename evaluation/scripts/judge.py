#!/usr/bin/env python3
"""
Judge - LLM-based evaluation of task outputs.
Uses MiniMax M2.5 to judge MiniMax-M2.7 outputs.
"""

import json
import requests
from typing import Dict, Any, List
from pathlib import Path


class Judge:
    """LLM-based judge for evaluating task outputs."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.eval_config = config["evaluation"]
        self.judge_config = config["metrics"]
        
        self.api_key = self.eval_config.get("apiKey")
        self.api_base = self.eval_config.get("apiBaseUrl", "https://api.minimax.chat/v1")
        self.judge_model = self.eval_config.get("judgeModel", "MiniMax-M2.5")
        
        self.rubrics_dir = Path(__file__).parent.parent / "judges"
    
    def evaluate(
        self,
        task: Dict,
        output: str,
        files_created: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate task output using LLM judge.
        
        Returns:
            Dict with scores for different dimensions
        """
        # Load rubrics
        code_rubric = self._load_rubric("rubric-code.md")
        proactivity_rubric = self._load_rubric("rubric-proactive.md")
        
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(task, output, files_created, code_rubric)
        
        # Call LLM judge
        scores = self._call_judge(prompt)
        
        # Also do quick automated checks
        automated = self._automated_checks(output, files_created)
        
        return {
            "code_quality": scores.get("code_quality", 3),
            "readability": scores.get("readability", 3),
            "correctness": scores.get("correctness", 3),
            "efficiency": scores.get("efficiency", 3),
            "safety": scores.get("safety", 3),
            "automated_checks": automated
        }
    
    def _load_rubric(self, name: str) -> str:
        """Load a rubric file."""
        rubric_path = self.rubrics_dir / name
        if rubric_path.exists():
            return rubric_path.read_text()
        return ""
    
    def _build_evaluation_prompt(
        self,
        task: Dict,
        output: str,
        files_created: List[str],
        rubric: str
    ) -> str:
        """Build the prompt for the judge."""
        
        prompt = f"""# Task Evaluation

## Task Name: {task.get('name', 'Unknown')}
## Category: {task.get('category', 'Unknown')}

## Task Description:
{task.get('description', 'No description provided.')}

## Files Created:
{chr(10).join(f"- {f}" for f in files_created) if files_created else "No files created."}

## Agent Output:
{output[:2000] if len(output) > 2000 else output}

---

{rubric}

---

## Your Task:
Evaluate the agent's performance on this task.
Provide scores for each dimension (1-5) and explain your reasoning.
Output as JSON with this structure:
{{
    "code_quality": <1-5>,
    "readability": <1-5>,
    "correctness": <1-5>,
    "efficiency": <1-5>,
    "safety": <1-5>,
    "reasoning": "<brief explanation>"
}}
"""
        return prompt
    
    def _call_judge(self, prompt: str) -> Dict[str, Any]:
        """Call the LLM judge via API."""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.judge_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON from response
                try:
                    scores = json.loads(content)
                    return scores
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code block
                    return self._parse_json_fallback(content)
            else:
                return {"error": f"API error: {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_json_fallback(self, content: str) -> Dict[str, Any]:
        """Parse JSON from content, handling markdown code blocks."""
        import re
        
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try to find JSON directly
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        return {"code_quality": 3, "error": "Failed to parse judge response"}
    
    def _automated_checks(
        self,
        output: str,
        files_created: List[str]
    ) -> Dict[str, Any]:
        """Run automated checks on the output."""
        
        checks = {
            "has_code": len(output) > 100,
            "mentioned_actions": any(
                keyword in output.lower()
                for keyword in ["created", "wrote", "modified", "implemented"]
            ),
            "files_created_match": len(files_created) > 0,
            "error_mentioned": "error" in output.lower() or "failed" in output.lower()
        }
        
        return checks


def judge_task_output(
    task: Dict,
    output: str,
    files_created: List[str],
    config: Dict
) -> Dict[str, Any]:
    """Convenience function for judging task output."""
    judge = Judge(config)
    return judge.evaluate(task, output, files_created)


if __name__ == "__main__":
    # Test with sample data
    test_task = {
        "name": "Test Task",
        "category": "code-quality",
        "description": "Create a simple Python function"
    }
    
    test_output = "I created a file called hello.py with a function that returns 'Hello, World!'"
    test_files = ["hello.py"]
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    judge = Judge(config)
    result = judge.evaluate(test_task, test_output, test_files)
    print(json.dumps(result, indent=2))