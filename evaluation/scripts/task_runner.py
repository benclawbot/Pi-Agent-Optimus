#!/usr/bin/env python3
"""
Task Runner - Executes tasks against Pi agent and captures results.
"""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class TaskRunner:
    """Runs evaluation tasks against the Pi agent."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.eval_config = config["evaluation"]
        self.timeout = self.eval_config.get("timeoutSeconds", 300)
        
    def run(self, task: Dict) -> Dict[str, Any]:
        """
        Execute a task against the Pi agent.
        
        Returns:
            Dict containing execution trace, output, and metadata
        """
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            
            # Build the prompt for Pi
            prompt = self._build_prompt(task, workspace_path)
            
            # Execute Pi agent
            start_time = time.time()
            trace, output, files_created = self._execute_pi(prompt, workspace_path)
            end_time = time.time()
            
            return {
                "task": task,
                "workspace": str(workspace_path),
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "trace": trace,
                "output": output,
                "files_created": files_created,
                "tool_calls": self._extract_tool_calls(trace)
            }
    
    def _build_prompt(self, task: Dict, workspace: Path) -> str:
        """Build the prompt to send to Pi agent."""
        
        prompt_parts = [
            f"# Task: {task['name']}",
            f"## Category: {task['category']}",
            f"\n{task.get('description', '')}",
            f"\n## Requirements:",
        ]
        
        if "requirements" in task:
            for req in task["requirements"]:
                prompt_parts.append(f"- {req}")
        
        if "context" in task:
            prompt_parts.append(f"\n## Context:\n{task['context']}")
        
        prompt_parts.append(f"\nWork in: {workspace}")
        prompt_parts.append("\nExecute this task and report what you did.")
        
        return "\n".join(prompt_parts)
    
    def _execute_pi(self, prompt: str, workspace: Path) -> tuple:
        """
        Execute Pi agent with the given prompt.
        
        Returns:
            (trace, output, files_created)
        """
        # Build the pi command
        cmd = [
            "pi",
            "--provider", self.eval_config.get("apiProvider", "minimax"),
            "--model", self.eval_config.get("agentModel", "MiniMax-M2.7"),
            "--no-session",  # Don't persist for evaluation
            "--mode", "json",  # JSON output for easier parsing
            "--print",  # Non-interactive
            "--no-context-files",  # Don't load AGENTS.md/CLAUDE.md
            f"--session-dir={workspace / 'sessions'}",
            "--",  # End of pi options, start of prompt
            prompt
        ]
        
        # Actually, let's construct it properly
        pi_cmd = [
            "pi",
            "--provider", "minimax",
            "--model", "MiniMax-M2.7",
            "--print",
            "--no-session",
            f"--session-dir={workspace}"
        ]
        
        trace = []
        output = ""
        files_created = []
        
        try:
            # Run Pi agent
            result = subprocess.run(
                pi_cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(workspace)
            )
            
            output = result.stdout
            trace_output = result.stderr
            
            # Parse trace if available
            if trace_output:
                trace = self._parse_trace(trace_output)
            
            # Find created files
            files_created = self._find_created_files(workspace)
            
        except subprocess.TimeoutExpired:
            output = json.dumps({"error": "timeout", "task": task.get("name")})
            trace = [{"type": "timeout", "timestamp": datetime.now().isoformat()}]
        except Exception as e:
            output = json.dumps({"error": str(e)})
            trace = [{"type": "error", "error": str(e), "timestamp": datetime.now().isoformat()}]
        
        return trace, output, files_created
    
    def _parse_trace(self, stderr_output: str) -> List[Dict]:
        """Parse the trace output from Pi."""
        # Trace output might be mixed with other output
        # For now, just capture raw lines
        trace = []
        for line in stderr_output.split("\n"):
            if line.strip():
                try:
                    # Try to parse as JSON
                    entry = json.loads(line)
                    trace.append(entry)
                except:
                    # Not JSON, just store as text
                    trace.append({"type": "text", "content": line})
        return trace
    
    def _extract_tool_calls(self, trace: List[Dict]) -> List[Dict]:
        """Extract tool calls from the trace."""
        tool_calls = []
        for entry in trace:
            if entry.get("type") in ["tool_call", "tool_use", "function_call"]:
                tool_calls.append({
                    "tool": entry.get("name", "unknown"),
                    "args": entry.get("args", {}),
                    "timestamp": entry.get("timestamp")
                })
        return tool_calls
    
    def _find_created_files(self, workspace: Path) -> List[str]:
        """Find files created during task execution."""
        files = []
        for f in workspace.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                # Get relative path from workspace
                rel_path = f.relative_to(workspace)
                files.append(str(rel_path))
        return files


def run_evaluation_task(task: Dict, config: Dict) -> Dict[str, Any]:
    """Convenience function to run a single evaluation task."""
    runner = TaskRunner(config)
    return runner.run(task)


if __name__ == "__main__":
    # Test with a simple task
    test_task = {
        "name": "Test Task",
        "category": "code-quality",
        "description": "Create a simple Python function that returns 'Hello, World!'"
    }
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    config = {"evaluation": {"timeoutSeconds": 60}}
    runner = TaskRunner(config)
    result = runner.run(test_task)
    print(json.dumps(result, indent=2, default=str))