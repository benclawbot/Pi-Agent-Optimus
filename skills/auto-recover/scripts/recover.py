# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Auto Recover

Analyze errors and suggest/apply fixes for common issues.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

STATE_FILE = Path("~/.pi/recovery-log.json").expanduser()

# Common error patterns and their fixes
ERROR_PATTERNS = [
    {
        "pattern": r"Cannot find module ['\"]([^'\"]+)['\"]",
        "type": "missing-import",
        "description": "Missing import statement",
        "fix_template": "Add import for {0}"
    },
    {
        "pattern": r"Unexpected token",
        "type": "syntax-error",
        "description": "Syntax error in code",
        "fix_template": "Fix syntax error at indicated location"
    },
    {
        "pattern": r"Type ['\"]([^'\"]+)['\"] is not assignable to type ['\"]([^'\"]+)['\"]",
        "type": "type-error",
        "description": "TypeScript type mismatch",
        "fix_template": "Add type annotation or fix type"
    },
    {
        "pattern": r"Cannot find package ['\"]([^'\"]+)['\"]",
        "type": "missing-dependency",
        "description": "Missing npm package",
        "fix_template": "Run: npm install {0}"
    },
    {
        "pattern": r"ER_NO_SUCH_TABLE: Table ['\"]([^'\"]+)['\"] doesn't exist",
        "type": "missing-table",
        "description": "Database table not found",
        "fix_template": "Run migration for table {0}"
    },
    {
        "pattern": r"ENOENT: no such file or directory",
        "type": "missing-file",
        "description": "File not found",
        "fix_template": "Create missing file or check path"
    },
    {
        "pattern": r"Port (\d+) is already in use",
        "type": "port-conflict",
        "description": "Port already in use",
        "fix_template": "Kill process on port {0} or use different port"
    },
    {
        "pattern": r"Permission denied",
        "type": "permission-error",
        "description": "Permission denied",
        "fix_template": "Check file permissions or run with elevated privileges"
    }
]


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"attempts": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def match_error(error_msg: str) -> Optional[dict]:
    """Match error against known patterns."""
    for pattern in ERROR_PATTERNS:
        match = re.search(pattern["pattern"], error_msg, re.IGNORECASE)
        if match:
            result = {
                "type": pattern["type"],
                "description": pattern["description"],
                "fix": pattern["fix_template"],
                "match": match.group(0),
                "groups": match.groups()
            }
            # Fill in template variables
            groups = match.groups()
            for i, group in enumerate(groups):
                placeholder = "{" + str(i) + "}"
                if group:
                    result["fix"] = result["fix"].replace(placeholder, group)
            return result
    return None


def diagnose_error(error_msg: str) -> dict:
    """Diagnose an error message."""
    match = match_error(error_msg)

    if match:
        return {
            "diagnosed": True,
            "type": match["type"],
            "description": match["description"],
            "suggested_fix": match["fix"],
            "confidence": "high"
        }
    else:
        return {
            "diagnosed": False,
            "description": "Unknown error type",
            "suggested_fix": "Investigate manually",
            "confidence": "low",
            "original_error": error_msg[:200]
        }


def suggest_fix(issue_type: str, context: dict) -> Optional[str]:
    """Suggest a fix for a specific issue type."""
    fixes = {
        "missing-import": "Check the import path and ensure the module exists",
        "syntax-error": "Check for matching brackets, quotes, and semicolons",
        "type-error": "Add explicit type annotation or cast",
        "missing-dependency": "Run 'npm install <package>' or check package.json",
        "missing-table": "Run database migration or create table",
        "missing-file": "Create the file or check the path",
        "port-conflict": "Kill the process using the port: 'netstat -ano | findstr :PORT' then 'taskkill /F /PID PID'",
        "permission-error": "Run as administrator or chmod the file"
    }
    return fixes.get(issue_type)


def apply_fix(issue_type: str, context: dict) -> dict:
    """Attempt to apply an automatic fix."""
    result = {"applied": False, "action": None, "success": False}

    if issue_type == "port-conflict":
        # Extract port number
        match = re.search(r"Port (\d+)", context.get("error", ""))
        if match:
            port = match.group(1)
            try:
                # Find process on port
                find_result = subprocess.run(
                    "netstat -ano | findstr :" + port,
                    shell=True, capture_output=True, text=True
                )
                if find_result.stdout:
                    lines = find_result.stdout.strip().split("\n")
                    for line in lines:
                        if "LISTENING" in line:
                            parts = line.split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                # Kill it
                                subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
                                result = {
                                    "applied": True,
                                    "action": "Killed process " + pid + " on port " + port,
                                    "success": True
                                }
                                break
            except Exception as e:
                result["error"] = str(e)

    return result


def log_attempt(error: str, fix: str, status: str) -> None:
    """Log recovery attempt."""
    state = load_state()
    state["attempts"].append({
        "id": "rec-" + str(len(state["attempts"]) + 1).zfill(3),
        "error": error[:100],
        "fix": fix,
        "status": status
    })
    # Keep last 100 attempts
    state["attempts"] = state["attempts"][-100:]
    save_state(state)


def main():
    if len(sys.argv) < 2:
        print("Usage: recover.py <command> [args]")
        print("Commands:")
        print("  diagnose <error>              Analyze an error message")
        print("  analyze --file <path>         Analyze error from file")
        print("  fix --issue <type>            Attempt to auto-fix")
        print("  suggest <type>                Get fix suggestion")
        print("  log                           Show recovery history")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "diagnose":
        if len(sys.argv) < 3:
            print("Error: provide error message")
            sys.exit(1)
        error_msg = " ".join(sys.argv[2:])
        result = diagnose_error(error_msg)
        print(json.dumps(result, indent=2))

    elif cmd == "analyze":
        if "--file" in sys.argv:
            idx = sys.argv.index("--file")
            file_path = sys.argv[idx + 1]
            if not Path(file_path).exists():
                print("Error: file not found: " + file_path)
                sys.exit(1)
            with open(file_path) as f:
                content = f.read()
            # Look for common errors in the file
            result = {"file": file_path, "issues": []}
            for pattern in ERROR_PATTERNS:
                matches = re.finditer(pattern["pattern"], content, re.MULTILINE)
                for match in matches:
                    result["issues"].append({
                        "type": pattern["type"],
                        "description": pattern["description"],
                        "at": match.group(0)[:50]
                    })
            print(json.dumps(result, indent=2))
        else:
            print("Error: specify --file <path>")
            sys.exit(1)

    elif cmd == "fix":
        if "--issue" in sys.argv:
            idx = sys.argv.index("--issue")
            issue_type = sys.argv[idx + 1]
            context = {"error": " ".join(sys.argv[idx + 2:]) if len(sys.argv) > idx + 2 else ""}
            result = apply_fix(issue_type, context)
            print(json.dumps(result, indent=2))
        else:
            print("Error: specify --issue <type>")
            sys.exit(1)

    elif cmd == "suggest":
        if len(sys.argv) < 3:
            print("Error: specify issue type")
            sys.exit(1)
        issue_type = sys.argv[2]
        suggestion = suggest_fix(issue_type, {})
        print(suggestion if suggestion else "No suggestion available for this type")

    elif cmd == "log":
        state = load_state()
        if state["attempts"]:
            print("Recent recovery attempts:")
            for a in state["attempts"][-10:]:
                status_icon = "OK" if a["status"] == "success" else "FAIL"
                print("  [" + status_icon + "] " + a["error"][:50] + " - " + a["fix"][:40])
        else:
            print("No recovery attempts logged.")

    else:
        print("Unknown command: " + cmd)
        sys.exit(1)


if __name__ == "__main__":
    main()
