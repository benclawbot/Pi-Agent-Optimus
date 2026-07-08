# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Phase 2: Session Mining

Extracts examples from session history for evaluation datasets.
"""

import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
SESSIONS_DIR = Path.home() / ".pi" / "agent" / "sessions"
MEMORY_FILE = Path.home() / ".pi" / "skill-memory.json"
SKILLS_DIR = Path.home() / ".pi" / "agent" / "skills"


def load_sessions(limit: Optional[int] = None) -> list[dict]:
    """Load recent session files."""
    if not SESSIONS_DIR.exists():
        return []
    
    sessions = []
    for session_file in sorted(SESSIONS_DIR.rglob("*.jsonl"), reverse=True)[:limit or 100]:
        try:
            entries = []
            with open(session_file) as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            if entries:
                sessions.append({
                    "file": str(session_file),
                    "entries": entries,
                    "timestamp": entries[0].get("timestamp", "")
                })
        except Exception:
            continue
    
    return sessions


def extract_skill_triggers(entries: list[dict]) -> list[dict]:
    """Find where skills were triggered."""
    triggers = []
    
    for entry in entries:
        # Check for skill mentions
        content = entry.get("message", {}).get("content", "")
        if isinstance(content, list):
            content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
        
        # Look for skill patterns
        if "/skill:" in content or "skill:" in content.lower():
            triggers.append({
                "type": "skill_invocation",
                "content": content[:200],
                "timestamp": entry.get("timestamp", "")
            })
        
        # Look for skill learning patterns
        if any(phrase in content.lower() for phrase in ["learn from this", "remember this", "improve"]):
            triggers.append({
                "type": "learning_capture",
                "content": content[:200],
                "timestamp": entry.get("timestamp", "")
            })
    
    return triggers


def extract_success_cases(entries: list[dict]) -> list[dict]:
    """Identify likely success cases."""
    successes = []
    
    for i, entry in enumerate(entries):
        content = entry.get("message", {}).get("content", "")
        if isinstance(content, list):
            content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
        
        # Look for positive indicators
        positive_patterns = [
            "done", "completed", "success", "working", "fixed",
            "implemented", "created", "added", "updated"
        ]
        
        if any(pattern in content.lower() for pattern in positive_patterns):
            # Check if followed by assistant response
            if i + 1 < len(entries):
                next_entry = entries[i + 1]
                if next_entry.get("message", {}).get("role") == "assistant":
                    successes.append({
                        "type": "success",
                        "user_request": content[:300],
                        "assistant_response": str(next_entry.get("message", {}).get("content", ""))[:500],
                        "timestamp": entry.get("timestamp", "")
                    })
    
    return successes[:5]  # Limit to 5 per session


def extract_failure_cases(entries: list[dict]) -> list[dict]:
    """Identify likely failure cases."""
    failures = []
    
    for i, entry in enumerate(entries):
        content = entry.get("message", {}).get("content", "")
        if isinstance(content, list):
            content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
        
        # Look for failure indicators
        failure_patterns = [
            "didn't work", "failed", "error", "exception",
            "not working", "broken", "issue", "problem"
        ]
        
        if any(pattern in content.lower() for pattern in failure_patterns):
            failures.append({
                "type": "failure",
                "content": content[:300],
                "timestamp": entry.get("timestamp", "")
            })
    
    return failures[:3]  # Limit to 3 per session


def mine_sessions(skill_name: Optional[str] = None, limit: int = 20) -> dict:
    """Mine sessions for examples."""
    sessions = load_sessions(limit)
    
    if not sessions:
        return {"error": "No sessions found"}
    
    all_triggers = []
    all_successes = []
    all_failures = []
    
    for session in sessions:
        triggers = extract_skill_triggers(session["entries"])
        successes = extract_success_cases(session["entries"])
        failures = extract_failure_cases(session["entries"])
        
        all_triggers.extend(triggers)
        all_successes.extend(successes)
        all_failures.extend(failures)
    
    # Filter by skill if specified
    if skill_name:
        all_triggers = [t for t in all_triggers if skill_name in t.get("content", "")]
        all_successes = [s for s in all_successes if skill_name in str(s)]
        all_failures = [f for f in all_failures if skill_name in f.get("content", "")]
    
    result = {
        "timestamp": datetime.now().isoformat()[:19] + "Z",
        "sessions_analyzed": len(sessions),
        "skill_filter": skill_name,
        "triggers": all_triggers[:10],
        "success_cases": all_successes[:10],
        "failure_cases": all_failures[:5],
        "summary": {
            "total_triggers": len(all_triggers),
            "total_successes": len(all_successes),
            "total_failures": len(all_failures)
        }
    }
    
    # Save to memory
    save_to_memory(result, skill_name)
    
    return result


def save_to_memory(mining_result: dict, skill_name: Optional[str]) -> None:
    """Save mining results to memory."""
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE) as f:
            memory = json.load(f)
    else:
        memory = {"sessions": [], "lessons": [], "gaps": [], "patterns": [], "evaluations": []}
    
    if "sessions" not in memory:
        memory["sessions"] = []
    
    # Add session summary
    session_entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": mining_result["timestamp"],
        "skill": skill_name,
        "sessions_analyzed": mining_result["sessions_analyzed"],
        "triggers_found": mining_result["summary"]["total_triggers"],
        "success_cases": mining_result["summary"]["total_successes"],
        "failure_cases": mining_result["summary"]["total_failures"]
    }
    
    memory["sessions"].append(session_entry)
    
    # Keep last 100 entries
    memory["sessions"] = memory["sessions"][-100:]
    
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def build_eval_dataset(skill_name: str, min_examples: int = 10) -> dict:
    """Build evaluation dataset from mined sessions."""
    mining = mine_sessions(skill_name, limit=50)
    
    if mining.get("error"):
        return mining
    
    # Build dataset entries
    dataset = []
    
    # Add success cases
    for case in mining.get("success_cases", []):
        dataset.append({
            "id": str(uuid.uuid4())[:8],
            "type": "success",
            "task": case.get("user_request", "")[:200],
            "expected_behavior": "Skill should complete successfully",
            "source": "session_mining",
            "timestamp": case.get("timestamp", "")
        })
    
    # Add failure cases as negative examples
    for case in mining.get("failure_cases", []):
        dataset.append({
            "id": str(uuid.uuid4())[:8],
            "type": "failure",
            "task": case.get("content", "")[:200],
            "expected_behavior": "Skill should handle gracefully or fail with clear error",
            "source": "session_mining",
            "timestamp": case.get("timestamp", "")
        })
    
    result = {
        "skill": skill_name,
        "dataset_size": len(dataset),
        "examples": dataset,
        "timestamp": datetime.now().isoformat()[:19] + "Z"
    }
    
    # Save dataset
    dataset_file = SKILLS_DIR / skill_name / "datasets" / "eval-dataset.json"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    with open(dataset_file, "w") as f:
        json.dump(result, f, indent=2)
    
    return result


def get_mining_history(skill_name: Optional[str] = None) -> dict:
    """Get historical mining results."""
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE) as f:
            memory = json.load(f)
    else:
        return {"error": "No memory file found"}
    
    sessions = memory.get("sessions", [])
    
    if skill_name:
        sessions = [s for s in sessions if s.get("skill") == skill_name]
    
    return {
        "skill": skill_name,
        "total_minings": len(sessions),
        "history": sorted(sessions, key=lambda x: x["timestamp"], reverse=True)[:20]
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: mine-sessions.py <command> [args]")
        print("Commands:")
        print("  mine [--skill <name>] [--limit N]")
        print("  build-dataset <skill>")
        print("  history [--skill <name>]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "mine":
        skill_name = None
        limit = 20
        
        if "--skill" in sys.argv:
            idx = sys.argv.index("--skill")
            skill_name = sys.argv[idx + 1]
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            limit = int(sys.argv[idx + 1])
        
        result = mine_sessions(skill_name, limit)
        print(json.dumps(result, indent=2))
    
    elif cmd == "build-dataset":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        result = build_eval_dataset(skill)
        print(json.dumps(result, indent=2))
    
    elif cmd == "history":
        skill_name = None
        if "--skill" in sys.argv:
            idx = sys.argv.index("--skill")
            skill_name = sys.argv[idx + 1]
        
        result = get_mining_history(skill_name)
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
