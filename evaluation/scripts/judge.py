#!/usr/bin/env python3
"""
Judge - LLM-based evaluation of task outputs.
Uses MiniMax M2.5 to judge MiniMax-M2.7 outputs.
"""

import json
import subprocess
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
        files_created: List[str],
        file_contents: Dict[str, str] = None,
        validation: Dict[str, Any] = None
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
        file_contents = file_contents or {}
        validation = validation or {}
        prompt = self._build_evaluation_prompt(task, output, files_created, file_contents, validation, code_rubric)
        
        # Call LLM judge
        scores = self._call_judge(prompt)
        judge_error = scores.get("error")
        
        # Also do quick automated checks
        automated = self._automated_checks(output, files_created)
        
        if judge_error:
            return {
                "code_quality": 0,
                "readability": 0,
                "correctness": 0,
                "efficiency": 0,
                "safety": 0,
                "judge_error": judge_error,
                "automated_checks": automated
            }

        return {
            "code_quality": self._score_or_zero(scores, "code_quality"),
            "readability": self._score_or_zero(scores, "readability"),
            "correctness": self._score_or_zero(scores, "correctness"),
            "efficiency": self._score_or_zero(scores, "efficiency"),
            "safety": self._score_or_zero(scores, "safety"),
            "reasoning": scores.get("reasoning", ""),
            "automated_checks": automated
        }
    
    def _score_or_zero(self, scores: Dict[str, Any], key: str) -> float:
        """Return a bounded numeric score; missing/invalid judge fields fail closed."""
        try:
            value = float(scores.get(key, 0))
        except (TypeError, ValueError):
            return 0
        return min(max(value, 0), 5)
    
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
        file_contents: Dict[str, str],
        validation: Dict[str, Any],
        rubric: str
    ) -> str:
        """Build the prompt for the judge."""
        files_section = ""
        for path, content in list(file_contents.items())[:8]:
            files_section += f"\n### {path}\n```\n{content}\n```\n"

        validation_section = json.dumps(validation, indent=2)[:4000] if validation else "{}"
        
        prompt = f"""# Task Evaluation

## Task Name: {task.get('name', 'Unknown')}
## Category: {task.get('category', 'Unknown')}

## Task Description:
{task.get('description', 'No description provided.')}

## Files Created:
{chr(10).join(f"- {f}" for f in files_created) if files_created else "No files created."}

## File Contents:
{files_section if files_section else "No readable file contents captured."}

## Objective Validation Evidence:
```json
{validation_section}
```

## Agent Output:
{output[:2000] if len(output) > 2000 else output}

---

{rubric}

---

## Your Task:
Evaluate the agent's performance on this task.
Use the objective validation evidence as the primary source of truth. If tests failed
or required files are missing, correctness and code_quality should be low even if the
written explanation sounds plausible.

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
        """Call the LLM judge. By default reuse the working pi CLI auth path."""
        
        # Keep the normal evaluation path simple and aligned with the agent run:
        # Pi already knows the configured provider/model credentials. Direct API
        # calls are opt-in only to avoid duplicate/broken credential paths.
        if not self.eval_config.get("useDirectJudgeApi", False):
            return self._call_judge_via_pi(prompt)

        if not self.api_key or self.api_key == "***":
            return self._call_judge_via_pi(prompt)

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
                fallback = self._call_judge_via_pi(prompt)
                if "error" not in fallback:
                    return fallback
                return {"error": f"API error: {response.status_code}; pi fallback: {fallback['error']}"}
                
        except Exception as e:
            fallback = self._call_judge_via_pi(prompt)
            if "error" not in fallback:
                return fallback
            return {"error": f"{str(e)}; pi fallback: {fallback['error']}"}
    
    def _call_judge_via_pi(self, prompt: str) -> Dict[str, Any]:
        """Use the configured pi CLI as judge, reusing its existing provider auth."""
        cmd = [
            "pi",
            "--provider", self.eval_config.get("apiProvider", "minimax"),
            "--model", self.judge_model,
            "--print",
            "--no-session",
            "--no-tools",
            "--no-context-files",
        ]

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.eval_config.get("judgeTimeoutSeconds", 120),
            )
        except Exception as e:
            return {"error": f"pi judge failed: {e}"}

        if result.returncode != 0:
            return {"error": f"pi judge exited {result.returncode}: {result.stderr.strip()}"}

        content = result.stdout.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return self._parse_json_fallback(content)
    
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
        
        return {"error": "Failed to parse judge response"}
    
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
