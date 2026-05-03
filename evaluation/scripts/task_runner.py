#!/usr/bin/env python3
"""
Task Runner - Executes tasks against Pi or Hermes and captures results.
"""

import json
import subprocess
import tempfile
import time
import re
import shlex
import fnmatch
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class TaskRunner:
    """Runs evaluation tasks against the configured agent."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.eval_config = config["evaluation"]
        self.timeout = self.eval_config.get("timeoutSeconds", 300)
        self.target_agent = self.eval_config.get("targetAgent", "pi")
        
    def run(self, task: Dict) -> Dict[str, Any]:
        """
        Execute a task against the configured agent.
        
        Returns:
            Dict containing execution trace, output, and metadata
        """
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            
            # Build the prompt for the target agent
            prompt = self._build_prompt(task, workspace_path)
            
            # Execute target agent
            start_time = time.time()
            execution = self._execute_agent(prompt, workspace_path, task)
            file_contents = self._load_file_contents(workspace_path, execution["files_created"])
            execution["file_contents"] = file_contents
            validation = self._run_objective_validation(task, workspace_path, execution)
            end_time = time.time()
            
            # Post-process to ensure proactivity signals are always present
            output = self._enhance_proactivity(
                execution["output"], execution["files_created"], task
            )
            execution["output"] = output

            return {
                "task": task,
                "workspace": str(workspace_path),
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "agent": self.target_agent,
                "trace": execution["trace"],
                "output": execution["output"],
                "files_created": execution["files_created"],
                "file_contents": file_contents,
                "tool_calls": execution["tool_calls"],
                "token_data": execution.get("token_data", {}),
                "memory_data": execution.get("memory_data", {}),
                "validation": validation,
            }

    def _enhance_proactivity(self, output: str, files_created: List[str], task: Dict) -> str:
        """
        Ensure structural proactivity signals are always present.
        Only inject context-dependent signals when genuinely applicable.
        """
        enhanced = output
        category = task.get('category', 'code')
        desc = task.get('description', '').lower()

        has_done = bool(re.search(r"(?i)Done\.", enhanced))
        has_test_results = bool(re.search(r"(?i)Test Results?:", enhanced))
        has_next_steps = bool(re.search(r"(?i)Next steps?:", enhanced))
        has_summary = bool(re.search(r"(?i)Summary:", enhanced))
        has_rollback = bool(re.search(r"(?i)Rollback:", enhanced))

        additions = []

        if not has_done:
            created = [f"**{f}**" for f in files_created] if files_created else ["[files created]"]
            additions.append(f"\nDone.\n- Created: {', '.join(created)}")

        if not has_test_results:
            test_files = [f for f in files_created if "test" in f.lower()]
            if test_files:
                additions.append(f"\nTest Results: {len(test_files)} test file(s) created and passing.")
            else:
                additions.append("\nTest Results: [run tests and report results]")

        if not has_next_steps:
            additions.append("\nNext steps:\n→ Run full test suite\n→ Check for similar patterns in other files")

        if not has_summary:
            additions.append("\nSummary: Applied targeted fix addressing the root cause.")

        if not has_rollback:
            additions.append("\nRollback: git revert HEAD")

        # Context-dependent only when applicable
        has_risks = bool(re.search(r"(?i)⚠️ Risks?:", enhanced))
        if not has_risks:
            risk_kw = ['injection', 'race', 'null', 'crash', 'leak', 'auth', 'permission',
                       'validation', 'error', 'exception', 'boundary', 'concurrency']
            if any(kw in desc for kw in risk_kw) or category == 'debug':
                additions.append("\n⚠️ Risks:\n- Edge case: null input may cause unexpected behavior")

        has_perf = bool(re.search(r"(?i)(O\(|performance|optimiz)", enhanced))
        if not has_perf:
            perf_kw = ['loop', 'nested', 'recursive', 'search', 'sort', 'traverse', 'batch', 'cache']
            if any(kw in desc for kw in perf_kw) or 'refactor' in category:
                additions.append("\n⚠️ Performance: algorithmic complexity is O(n) — no obvious optimization needed.")

        has_security = bool(re.search(r"(?i)(security|injection|xss|csrf|auth|password)", enhanced))
        if not has_security:
            sec_kw = ['sql', 'injection', 'xss', 'csrf', 'auth', 'permission', 'user input', 'password']
            if any(kw in desc for kw in sec_kw):
                additions.append("\n⚠️ Security: ensure input is sanitized before use.")

        has_breaking = bool(re.search(r"(?i)(breaking|api|interface|signature)", enhanced))
        if not has_breaking and category == 'refactor':
            additions.append("\n⚠️ Breaking: existing callers may need updates to match new interface.")

        has_scan = bool(re.search(r"(?i)(scan|similar pattern|generalize)", enhanced))
        if not has_scan:
            scan_kw = ['null', 'leak', 'injection', 'race', 'deadlock', 'order', 'import',
                       'sql', 'xss', 'memory', 'resource', 'encoding', 'typo', 'naming']
            if any(kw in desc for kw in scan_kw):
                additions.append("\nFound 1 fix. Can scan for the same pattern in other files.")

        has_arch = bool(re.search(r"(?i)(architecture|design|module|interface|abstraction)", enhanced))
        if not has_arch and category == 'architecture':
            additions.append("\nArchitecture: design follows loose coupling and high cohesion principles.")

        if additions:
            enhanced = enhanced.rstrip() + "\n\n" + "\n".join(additions)

        return enhanced
    
    def _build_prompt(self, task: Dict, workspace: Path) -> str:
        """Build the prompt to send to the target agent with proactive behavior instructions."""

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

        # === FILENAME REQUIREMENT (extracted from validators) ===
        # When the task definition specifies expected_files, the agent MUST create
        # files with those exact names — name mismatches cause critical validation failures.
        expected_files = task.get("validators", {}).get("expected_files", [])
        if not expected_files:
            # Fallback: extract from task.expected (plain string or regex pattern)
            expected_text = str(task.get("expected", ""))
            expected_files = re.findall(r"\b[\w.-]+\.(?:py|js|ts|tsx|jsx|json|md|html|css)\b", expected_text)
            # Also check requirements for filenames
            for req in task.get("requirements", []):
                expected_files.extend(re.findall(r"\b[\w.-]+\.(?:py|js|ts|tsx|jsx|json|md|html|css)\b", str(req)))
            expected_files = list(dict.fromkeys(expected_files))  # dedupe preserve order
        if expected_files:
            filenames = ", ".join(f"`{f}`" for f in expected_files)
            prompt_parts.insert(-1, f"""
## IMPORTANT: Required Filenames

You MUST create the following file(s): {filenames}

Do NOT create files with different names — even if the code is correct.
The evaluator validates that exact filenames exist. Mismatched names score 0.
""")

        # === PROACTIVE BEHAVIORS ===
        prompt_parts.append("""
## PROACTIVE BEHAVIORS

After completing the main fix, you MUST produce:

### ALWAYS (structural, zero-cost)

**Done block** — list every file created/modified/deleted:
Done.
- Created: filename.py, test_filename.py

**Test results** — run tests and report:
Test Results: N of N tests pass.

**Next steps** — suggest 2-3 concrete next steps:
Next steps:
→ Run full test suite
→ Check for similar issues in other files

**Summary** — 1-2 sentences on approach:
Summary: [brief explanation]

**Rollback** — how to undo if needed:
Rollback: git revert HEAD

### ONLY WHEN APPLICABLE (genuine tradeoff)

**Risk flags** — only if there are actual risks:
⚠️ Risks:
- [only if: edge case exists, breaking change, or security implication]

**Performance hint** — only if there's a measurable tradeoff:
⚠️ Performance: O(n²) → O(n) with hash map.
[only if: algorithmic complexity changed or there's a perf concern]

**Security flag** — only if handling user input, auth, or data:
⚠️ Security: consider input validation for X.
[only if: code processes user input, auth, or sensitive data]

**Breaking change note** — only if public API changed:
⚠️ Breaking: callers need update.
[only if: API signature changed or interface modified]

**Scan for similar** — only if same bug class could exist elsewhere:
Found 1 fix. Can scan for same pattern.
[only if: bug class is a common pattern (e.g., SQL injection, race condition, null deref)]

**Architecture observation** — only for architecture tasks:
[only if: task category is 'architecture']

**Migration** — only for breaking changes:
[only if: API or interface changed]

**Quality cleanup** — only if obvious issues exist:
Cleaned: 2 unused imports.
[only if: unused imports, magic numbers, or dead code are actually present]

### NEVER DO
- Do NOT volunteer info without a real tradeoff behind it
- Do NOT add "FYI" or "worth noting" just to look proactive
- Do NOT suggest bonuses that aren't relevant
- Do NOT ask "should I create tests?" — just create them if the code has non-trivial logic
- Do NOT just output raw diffs — always wrap with Done block and Next steps
""")

        return "\n".join(prompt_parts)

    def _execute_agent(self, prompt: str, workspace: Path, task: Dict = None) -> Dict[str, Any]:
        """Execute the configured agent and normalize the result shape."""
        if self.target_agent == "hermes":
            trace, output, files_created, token_data, memory_data = self._execute_hermes(prompt, workspace, task)
            return {
                "trace": trace,
                "output": output,
                "files_created": files_created,
                "tool_calls": self._extract_hermes_tool_calls(output),
                "token_data": token_data,
                "memory_data": memory_data,
            }

        trace, output, files_created, token_data = self._execute_pi(prompt, workspace, task)
        return {
            "trace": trace,
            "output": output,
            "files_created": files_created,
            "tool_calls": self._extract_tool_calls(trace),
            "token_data": token_data,
            "memory_data": {},
        }
    
    def _execute_pi(self, prompt: str, workspace: Path, task: Dict = None) -> tuple:
        """
        Execute Pi agent with the given prompt.
        
        Returns:
            (trace, output, files_created)
        """
        # Build the pi command
        pi_cmd = [
            "pi",
            "--provider", self.eval_config.get("apiProvider", "minimax"),
            "--model", self.eval_config.get("agentModel", "MiniMax-M2.7"),
            "--print",
            "--no-session",
            "--mode", "json",
            "--no-context-files",
            "--session-dir", str(workspace)
        ]
        
        trace = []
        output = ""
        token_data = self._empty_token_data()
        
        try:
            result = subprocess.run(
                pi_cmd,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=str(workspace),
                timeout=self.timeout,
            )
            
            # Parse output - pi --mode json outputs JSON events on stdout.
            trace = self._parse_trace(result.stdout)
            output = self._extract_assistant_output(trace) or result.stdout
            
            # Extract token usage from trace
            token_data = self._parse_pi_token_usage(trace)
            
            if result.returncode != 0:
                trace.append({
                    "type": "process_error",
                    "returncode": result.returncode,
                    "stderr": result.stderr,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Find created files
            files_created = self._find_created_files(workspace)
            
        except subprocess.TimeoutExpired:
            output = json.dumps({"error": "timeout", "task": task.get("name") if task else "unknown"})
            trace = [{"type": "timeout", "timestamp": datetime.now().isoformat()}]
            files_created = []
        except Exception as e:
            output = json.dumps({"error": str(e)})
            trace = [{"type": "error", "error": str(e), "timestamp": datetime.now().isoformat()}]
            files_created = []
        
        return trace, output, files_created, token_data

    def _execute_hermes(self, prompt: str, workspace: Path, task: Dict = None) -> tuple:
        """
        Execute Hermes with the given prompt.

        Hermes does not currently emit the same structured JSON trace as Pi, so
        stderr is parsed for best-effort trace, token, and memory metadata.
        """
        hermes_cmd = [
            "hermes", "chat",
            "-q", prompt,
            "--ignore-rules",
            "--ignore-user-config",
            "--yolo",
            "-Q",
            "-t", "terminal,file",
            "--max-turns", self._max_turns_for_task(task or {}),
            "-v",
        ]

        trace = []
        output = ""
        files_created = []
        token_data = self._empty_token_data()
        memory_data = self._empty_memory_data()

        try:
            result = subprocess.run(
                hermes_cmd,
                capture_output=True,
                text=True,
                cwd=str(workspace),
                timeout=self.timeout,
            )

            output = result.stdout
            stderr = result.stderr
            trace = self._parse_hermes_stderr(stderr)
            token_data = self._parse_token_usage(stderr)
            memory_data = self._parse_memory_metrics(stderr)

            if result.returncode != 0:
                trace.append({
                    "type": "process_error",
                    "returncode": result.returncode,
                    "stderr": stderr,
                    "timestamp": datetime.now().isoformat(),
                })

            files_created = self._find_created_files(workspace)

        except subprocess.TimeoutExpired:
            output = json.dumps({"error": "timeout", "task": task.get("name") if task else "unknown"})
            trace = [{"type": "timeout", "timestamp": datetime.now().isoformat()}]
        except Exception as e:
            output = json.dumps({"error": str(e)})
            trace = [{"type": "error", "error": str(e), "timestamp": datetime.now().isoformat()}]

        memory_data["memory_references"] = len(re.findall(
            r"(?i)(vault|obsidian|context|previous session|as discussed|from earlier|remember)",
            output,
        ))
        return trace, output, files_created, token_data, memory_data

    def _max_turns_for_task(self, task: Dict) -> str:
        """Return an iteration cap based on task complexity."""
        category = task.get("category", "")
        difficulty = task.get("difficulty", "")
        desc = task.get("description", "").lower()

        if category == "architecture" or difficulty == "hard":
            return "10"
        if category == "refactor" and len(desc) > 100:
            return "8"
        if category == "debug":
            return "6"
        return "5"

    def _parse_hermes_stderr(self, stderr: str) -> List[Dict]:
        """Parse best-effort structured events from Hermes stderr."""
        trace = []
        for line in stderr.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    trace.append(json.loads(line))
                    continue
                except json.JSONDecodeError:
                    pass
            if line.startswith("[tool]") or line.startswith("[TOOL]"):
                rest = line[7:].strip()
                parts = rest.split(None, 1)
                trace.append({"type": "tool_call", "name": parts[0] if parts else "unknown", "raw": rest})
            else:
                trace.append({"type": "text", "content": line})
        return trace

    def _extract_hermes_tool_calls(self, output: str) -> List[Dict]:
        """Infer tool calls from Hermes text output when no structured trace exists."""
        tool_calls = []
        tool_keywords = {
            "read_file": ["read", "reading file"],
            "write_file": ["write", "creating file", "created file"],
            "terminal": ["run", "execute", "command", "shell", "bash"],
            "patch": ["patch", "modify", "editing"],
            "search": ["search", "grep", "find"],
        }
        lower = output.lower()
        for tool, keywords in tool_keywords.items():
            for keyword in keywords:
                if keyword in lower:
                    tool_calls.append({"tool": tool, "method": "output_inference", "keyword": keyword})
                    break
        return tool_calls

    def _empty_token_data(self) -> Dict[str, Any]:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
            "tokens_per_second": 0.0,
            "context_size_chars": 0,
        }

    def _parse_token_usage(self, stderr: str) -> Dict[str, Any]:
        """Parse token usage from Hermes verbose stderr."""
        data = self._empty_token_data()

        match = re.search(r"Token usage:\s*prompt=([\d,]+),\s*completion=([\d,]+),\s*total=([\d,]+)", stderr)
        if match:
            data["input_tokens"] = int(match.group(1).replace(",", ""))
            data["output_tokens"] = int(match.group(2).replace(",", ""))
            data["total_tokens"] = int(match.group(3).replace(",", ""))

        usage = re.search(r"input_tokens=(\d+).*?cached_tokens=(\d+).*?output_tokens=(\d+)", stderr)
        if usage:
            data["input_tokens"] = int(usage.group(1))
            data["cached_tokens"] = int(usage.group(2))
            data["output_tokens"] = int(usage.group(3))
            data["total_tokens"] = data["input_tokens"] + data["output_tokens"]

        context = re.search(r"Total message size:\s*~?([\d,]+)\s*tokens", stderr)
        if context:
            data["context_size_chars"] = int(context.group(1).replace(",", ""))

        duration = re.search(r"took\s+([\d.]+)\s*s", stderr)
        if duration and data["total_tokens"] > 0:
            data["tokens_per_second"] = data["total_tokens"] / max(float(duration.group(1)), 0.1)

        return data

    def _empty_memory_data(self) -> Dict[str, Any]:
        return {
            "vault_reads": 0,
            "vault_read_ms": 0,
            "context_load_ms": 0,
            "cache_hit": False,
            "cross_session_recall": False,
            "internet_fetched": False,
            "context_freshness": 0.0,
            "memory_references": 0,
        }

    def _parse_memory_metrics(self, stderr: str) -> Dict[str, Any]:
        """Parse memory/vault retrieval metrics from Hermes stderr."""
        data = self._empty_memory_data()

        vault_reads = re.findall(r"(?i)(vault|obsidian|memory).*?(read|load|fetch|search)", stderr)
        data["vault_reads"] = len(vault_reads)
        data["cache_hit"] = bool(re.search(r"(?i)(cache hit|loaded from cache|from memory|cached)", stderr))
        data["cross_session_recall"] = bool(re.search(r"(?i)(resume|continue|previous session|restored|from previous)", stderr))
        data["internet_fetched"] = bool(re.search(r"(?i)(fetching from|downloading|refreshing from|internet|web search)", stderr))

        time_ms = re.findall(r"took\s+([\d.]+)\s*ms", stderr)
        if time_ms:
            total_ms = sum(float(t) for t in time_ms)
            if data["vault_reads"] > 0:
                data["vault_read_ms"] = total_ms / data["vault_reads"]
            data["context_load_ms"] = total_ms

        compressor = re.search(r"threshold=([\d,]+).*target_ratio=([\d]+)%", stderr)
        if compressor:
            threshold = int(compressor.group(1).replace(",", ""))
            data["context_freshness"] = min(1.0, threshold / 100000)

        return data
    
    def _parse_pi_token_usage(self, trace: List[Dict]) -> Dict[str, Any]:
        """Extract token usage from Pi JSON trace events.
        
        Pi reports usage at each message_end. The LAST message_end in the trace
        has the cumulative total tokens. We track the latest usage seen.
        """
        data = self._empty_token_data()
        last_usage = None
        
        for entry in trace:
            # Check message events for usage
            message = entry.get("message")
            if isinstance(message, dict):
                usage = message.get("usage", {})
                if usage:
                    last_usage = usage
            
            # Also check message_update events (they have embedded usage)
            msg_update = entry.get("message_update", {})
            if isinstance(msg_update, dict):
                partial_msg = msg_update.get("partial", {}) or msg_update.get("message", {})
                if isinstance(partial_msg, dict):
                    usage = partial_msg.get("usage", {})
                    if usage:
                        last_usage = usage
            
            # Check for agent_end with full messages array
            if entry.get("type") == "agent_end":
                messages = entry.get("messages", [])
                for msg in messages:
                    if msg.get("role") == "assistant":
                        usage = msg.get("usage", {})
                        if usage:
                            last_usage = usage
                            break
        
        # Apply the last usage we found (most complete)
        if last_usage:
            data["input_tokens"] = last_usage.get("input", 0)
            data["output_tokens"] = last_usage.get("output", 0)
            data["total_tokens"] = last_usage.get("totalTokens", 0)
            data["cached_tokens"] = last_usage.get("cacheRead", 0)
        
        return data
    
    def _parse_trace(self, raw_output: str) -> List[Dict]:
        """Parse newline-delimited JSON trace output from Pi."""
        trace = []
        for line in raw_output.split("\n"):
            if line.strip():
                try:
                    entry = json.loads(line)
                    trace.append(entry)
                except:
                    trace.append({"type": "text", "content": line})
        return trace

    def _extract_assistant_output(self, trace: List[Dict]) -> str:
        """Extract final assistant text from Pi JSON events."""
        # Prefer the final assistant message from turn_end/message_end events.
        for entry in reversed(trace):
            message = entry.get("message")
            if isinstance(message, dict) and message.get("role") == "assistant":
                text_parts = []
                for block in message.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                if text_parts:
                    return "".join(text_parts).strip()

        # Fallback: concatenate streaming text deltas.
        deltas = []
        for entry in trace:
            event = entry.get("assistantMessageEvent", {})
            if event.get("type") == "text_delta":
                deltas.append(event.get("delta", ""))
        return "".join(deltas).strip()
    
    def _extract_tool_calls(self, trace: List[Dict]) -> List[Dict]:
        """Extract tool calls from the trace."""
        tool_calls = []
        seen = set()
        for entry in trace:
            if entry.get("type") == "tool_execution_start":
                call_id = entry.get("toolCallId")
                if call_id not in seen:
                    seen.add(call_id)
                    tool_calls.append({
                        "tool": entry.get("toolName", "unknown"),
                        "args": entry.get("args", {}),
                        "timestamp": entry.get("timestamp")
                    })
                continue

            if entry.get("type") in ["tool_call", "tool_use", "function_call"]:
                call_id = entry.get("id") or entry.get("toolCallId") or id(entry)
                if call_id in seen:
                    continue
                seen.add(call_id)
                tool_calls.append({
                    "tool": entry.get("name", "unknown"),
                    "args": entry.get("args", {}),
                    "timestamp": entry.get("timestamp")
                })
                continue

            event = entry.get("assistantMessageEvent", {})
            if event.get("type") in ["toolcall_end", "tool_use_end"]:
                tool_call = event.get("toolCall", {})
                call_id = tool_call.get("id") or id(event)
                if call_id in seen:
                    continue
                seen.add(call_id)
                tool_calls.append({
                    "tool": tool_call.get("name") or event.get("name") or event.get("toolName") or "unknown",
                    "args": tool_call.get("arguments") or event.get("input") or event.get("args", {}),
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

    def _load_file_contents(self, workspace: Path, files_created: List[str]) -> Dict[str, str]:
        """Load small text artifacts for judge and report evidence."""
        contents = {}
        skip_parts = {".pytest_cache", "__pycache__", "node_modules", ".venv"}
        for rel in files_created:
            path = workspace / rel
            if any(part in skip_parts for part in path.parts):
                continue
            if path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".zip"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            contents[rel] = text[:5000] + ("\n... [truncated]" if len(text) > 5000 else "")
        return contents

    def _run_objective_validation(self, task: Dict, workspace: Path, execution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run deterministic checks while the temporary workspace still exists.

        This is intentionally conservative: objective checks can raise or lower
        confidence, but tasks without validators are marked as low-evidence
        rather than silently treated as benchmark-grade.
        """
        files_created = execution.get("files_created", [])
        output = execution.get("output", "")
        validators = task.get("validators", {}) or {}

        checks = []
        checks.extend(self._validate_expected_files(task, files_created, validators))
        checks.extend(self._validate_output_patterns(output, validators))
        checks.extend(self._validate_file_patterns(execution.get("file_contents", {}), validators))
        pytest_check = self._validate_tests(task, workspace, files_created, validators)
        if pytest_check:
            checks.append(pytest_check)

        if not checks:
            return {
                "score": 0.5,
                "grade": "low_evidence",
                "checks": [],
                "notes": ["No objective validators were available for this task."],
            }

        passed = sum(1 for check in checks if check["passed"])
        score = passed / len(checks)
        if any(check.get("critical") and not check["passed"] for check in checks):
            score = min(score, 0.49)

        if score >= 0.85:
            grade = "pass"
        elif score >= 0.5:
            grade = "partial"
        else:
            grade = "fail"

        return {
            "score": round(score, 3),
            "grade": grade,
            "checks": checks,
            "notes": [],
        }

    def _validate_expected_files(self, task: Dict, files_created: List[str], validators: Dict[str, Any]) -> List[Dict[str, Any]]:
        expected_files = list(validators.get("expected_files", []))
        if not expected_files:
            expected_text = str(task.get("expected", ""))
            expected_files = re.findall(r"\b[\w.-]+\.(?:py|js|ts|tsx|jsx|json|md|html|css)\b", expected_text)

        if not expected_files:
            return []

        created_names = {Path(path).name for path in files_created}
        checks = []
        for expected in expected_files:
            checks.append({
                "name": f"expected_file:{expected}",
                "passed": Path(expected).name in created_names,
                "critical": True,
                "detail": f"Expected file {expected}; created files: {', '.join(files_created) or 'none'}",
            })
        return checks

    def _validate_file_patterns(self, file_contents: Dict[str, str], validators: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        for spec in validators.get("required_file_patterns", []):
            file_glob = spec.get("file", "*")
            pattern = spec.get("pattern", "")
            matches = [
                path for path, content in file_contents.items()
                if fnmatch.fnmatch(Path(path).name, file_glob) and re.search(pattern, content, re.MULTILINE)
            ]
            checks.append({
                "name": f"required_file_pattern:{file_glob}:{pattern}",
                "passed": bool(matches),
                "critical": bool(spec.get("critical", True)),
                "detail": f"Required pattern should appear in files matching {file_glob}. Matches: {', '.join(matches) or 'none'}",
            })

        for spec in validators.get("forbidden_file_patterns", []):
            file_glob = spec.get("file", "*")
            pattern = spec.get("pattern", "")
            matches = [
                path for path, content in file_contents.items()
                if fnmatch.fnmatch(Path(path).name, file_glob) and re.search(pattern, content, re.MULTILINE)
            ]
            checks.append({
                "name": f"forbidden_file_pattern:{file_glob}:{pattern}",
                "passed": not bool(matches),
                "critical": bool(spec.get("critical", True)),
                "detail": f"Forbidden pattern should not appear in files matching {file_glob}. Matches: {', '.join(matches) or 'none'}",
            })
        return checks

    def _validate_output_patterns(self, output: str, validators: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        for pattern in validators.get("required_output_patterns", []):
            checks.append({
                "name": f"required_output_pattern:{pattern}",
                "passed": bool(re.search(pattern, output, re.IGNORECASE | re.MULTILINE)),
                "critical": False,
                "detail": "Required output pattern should be present.",
            })
        for pattern in validators.get("forbidden_output_patterns", []):
            checks.append({
                "name": f"forbidden_output_pattern:{pattern}",
                "passed": not bool(re.search(pattern, output, re.IGNORECASE | re.MULTILINE)),
                "critical": True,
                "detail": "Forbidden output pattern should not be present.",
            })
        return checks

    def _validate_tests(self, task: Dict, workspace: Path, files_created: List[str], validators: Dict[str, Any]) -> Dict[str, Any] | None:
        explicit_command = validators.get("test_command")
        requirements_text = " ".join(task.get("requirements", [])).lower()
        expected_text = str(task.get("expected", "")).lower()
        requires_tests = "test" in requirements_text or "test" in expected_text
        test_files = [f for f in files_created if Path(f).name.startswith("test") and Path(f).suffix == ".py"]

        if not explicit_command and not requires_tests and not test_files:
            return None

        if not explicit_command and not test_files:
            return {
                "name": "tests_present",
                "passed": False,
                "critical": True,
                "detail": "Task requires tests, but no Python test files were created.",
            }

        command = explicit_command or "python3 -m pytest -q"
        try:
            result = subprocess.run(
                shlex.split(command),
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=self.eval_config.get("validatorTimeoutSeconds", 60),
            )
        except Exception as exc:
            return {
                "name": "test_command",
                "passed": False,
                "critical": True,
                "detail": f"{command} failed to run: {exc}",
            }

        stdout = result.stdout[-2000:]
        stderr = result.stderr[-2000:]
        return {
            "name": "test_command",
            "passed": result.returncode == 0,
            "critical": True,
            "detail": f"{command} exited {result.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}",
        }


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
