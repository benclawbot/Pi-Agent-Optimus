# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Project Health Checker

Checks CI status, test freshness, outdated dependencies, and running servers.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

STATE_FILE = Path("~/.pi/health-state.json").expanduser()


def run_cmd(cmd: list[str]) -> tuple[str, int]:
    """Run command and return (output, exit_code)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def check_ci_status() -> dict:
    """Check CI status via GitHub CLI."""
    output, code = run_cmd(["gh", "run", "list", "--limit", "5", "--json", "status,conclusion,name,startedAt"])

    if code != 0:
        return {
            "available": False,
            "error": "gh CLI not available or not authenticated"
        }

    try:
        runs = json.loads(output)
        if not runs:
            return {"available": True, "status": "no_runs", "runs": []}

        latest = runs[0]
        status = "passing"
        if latest.get("conclusion") == "failure":
            status = "failing"
        elif latest.get("status") == "in_progress":
            status = "running"

        return {
            "available": True,
            "status": status,
            "lastRun": latest.get("startedAt"),
            "runs": runs[:3]
        }
    except json.JSONDecodeError:
        return {
            "available": True,
            "status": "unknown",
            "error": "Could not parse gh output"
        }


def check_test_freshness() -> dict:
    """Check when tests were last run."""
    state_file = Path("~/.pi/test-state.json").expanduser()

    if not state_file.exists():
        return {"stale": None, "lastRun": None, "message": "No test history"}

    try:
        with open(state_file) as f:
            state = json.load(f)

        last_run = state.get("lastRun")
        if not last_run:
            return {"stale": None, "lastRun": None}

        last_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
        now = datetime.now(last_time.tzinfo)
        age_hours = (now - last_time).total_seconds() / 3600

        return {
            "stale": age_hours > 24,
            "lastRun": last_run,
            "ageHours": round(age_hours, 1)
        }
    except Exception:
        return {"stale": None, "lastRun": None, "error": "Could not read state"}


def check_outdated_deps() -> dict:
    """Check for outdated dependencies."""
    # Detect package manager
    if Path("package.json").exists():
        output, code = run_cmd(["npm", "outdated"])
        if code == 0 and output.strip():
            lines = output.strip().split("\n")
            # npm outdated has headers, count data rows
            return {
                "manager": "npm",
                "outdated": max(0, len(lines) - 1),
                "hasOutput": len(lines) > 1
            }

        return {"manager": "npm", "outdated": 0, "hasOutput": False}

    elif Path("Cargo.toml").exists():
        output, code = run_cmd(["cargo", "outdated"])
        if code == 0:
            # Count lines that look like package entries
            return {"manager": "cargo", "outdated": "unknown", "hasOutput": bool(output.strip())}

        return {"manager": "cargo", "outdated": 0, "hasOutput": False}

    return {"manager": None, "outdated": 0, "message": "No package manager detected"}


def check_running_servers() -> dict:
    """Check for running dev servers."""
    processes_file = Path("~/.pi/processes.json").expanduser()

    if not processes_file.exists():
        return {"running": [], "message": "No process tracking"}

    try:
        with open(processes_file) as f:
            data = json.load(f)

        servers = data.get("registered", [])
        return {
            "running": [s.get("port") for s in servers],
            "count": len(servers)
        }
    except Exception:
        return {"running": [], "error": "Could not read state"}


def calculate_health_status(checks: dict) -> str:
    """Calculate overall health status."""
    if checks.get("ci", {}).get("status") == "failing":
        return "red"
    if checks.get("deps", {}).get("outdated", 0) > 10:
        return "yellow"
    if checks.get("tests", {}).get("stale"):
        return "yellow"
    return "green"


def main():
    output = {
        "timestamp": datetime.now().isoformat()[:19] + "Z",
        "ci": check_ci_status(),
        "tests": check_test_freshness(),
        "deps": check_outdated_deps(),
        "servers": check_running_servers()
    }

    output["health"] = calculate_health_status(output)

    if "--json" in sys.argv:
        print(json.dumps(output, indent=2))
    else:
        print(f"Health: {output['health']}")
        print(f"CI: {output['ci']['status']}")
        print(f"Tests stale: {output['tests'].get('stale', 'unknown')}")
        print(f"Outdated deps: {output['deps']['outdated']}")
        print(f"Running servers: {output['servers'].get('running', [])}")


if __name__ == "__main__":
    main()
