# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
CI Monitor

Monitor CI pipelines and alert on failures.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("~/.pi/ci-alerts.json").expanduser()


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"alerts": [], "lastCheck": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_ci_status(limit: int = 5) -> dict:
    """Get CI status from GitHub CLI."""
    try:
        result = subprocess.run(
            ["gh", "run", "list", "--limit", str(limit), "--json", 
             "id,status,conclusion,name,headBranch,startedAt,updatedAt"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {"error": "gh CLI not available", "runs": []}
        
        runs = json.loads(result.stdout)
        return {"runs": runs, "error": None}
    except Exception as e:
        return {"error": str(e), "runs": []}


def check_for_failures(runs: list[dict]) -> list[dict]:
    """Find failed runs."""
    failures = []
    for run in runs:
        if run.get("conclusion") == "failure":
            failures.append({
                "id": run.get("id"),
                "name": run.get("name"),
                "branch": run.get("headBranch"),
                "time": run.get("startedAt"),
                "status": "failure"
            })
    return failures


def get_failures(limit: int = 10) -> dict:
    """Get recent failures."""
    status = get_ci_status(limit)
    if status.get("error"):
        return {"failures": [], "error": status["error"]}
    
    failures = check_for_failures(status["runs"])
    return {"failures": failures, "count": len(failures)}


def watch_for_failures(branch: str = None, interval: int = 60) -> None:
    """Watch CI and alert on failures."""
    state = load_state()
    known_failures = {a["id"] for a in state.get("alerts", []) if not a.get("acknowledged")}

    print(f"Watching CI (interval: {interval}s)" + (f" branch: {branch}" if branch else ""))

    while True:
        status = get_ci_status(limit=10)
        if status.get("error"):
            print(f"Error: {status['error']}")
            time.sleep(interval)
            continue

        new_failures = []
        for run in status["runs"]:
            if run.get("conclusion") == "failure":
                run_id = run.get("id")
                run_branch = run.get("headBranch")

                # Filter by branch if specified
                if branch and run_branch != branch:
                    continue

                if run_id not in known_failures:
                    # New failure
                    alert = {
                        "id": run_id,
                        "time": run.get("startedAt"),
                        "branch": run_branch,
                        "name": run.get("name"),
                        "acknowledged": False
                    }
                    new_failures.append(alert)
                    known_failures.add(run_id)
                    state.setdefault("alerts", []).append(alert)

        if new_failures:
            save_state(state)
            print("\n🔴 NEW CI FAILURE DETECTED:")
            for f in new_failures:
                print(f"  - {f['name']} on {f['branch']} at {f['time']}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CI OK", end="\r")

        time.sleep(interval)


def main():
    if len(sys.argv) < 2:
        print("Usage: ci-monitor.py <command> [args]")
        print("Commands:")
        print("  status                    Show recent CI status")
        print("  failures --limit <n>      Show recent failures")
        print("  watch --interval <s>      Watch for failures")
        print("  watch --branch <name>     Watch specific branch")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        status = get_ci_status()
        if status.get("error"):
            print(f"Error: {status['error']}")
        else:
            for run in status["runs"][:5]:
                icon = "✅" if run.get("conclusion") == "success" else "❌" if run.get("conclusion") == "failure" else "🔄"
                print(f"{icon} {run.get('name')} ({run.get('headBranch')}) - {run.get('conclusion', run.get('status'))}")

    elif cmd == "failures":
        limit = 10
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            limit = int(sys.argv[idx + 1])

        result = get_failures(limit)
        if result.get("error"):
            print(f"Error: {result['error']}")
        else:
            print(f"Found {result['count']} recent failures:")
            for f in result["failures"][:limit]:
                print(f"  - {f['name']} on {f['branch']}")

    elif cmd == "watch":
        interval = 60
        branch = None

        if "--interval" in sys.argv:
            idx = sys.argv.index("--interval")
            interval = int(sys.argv[idx + 1])

        if "--branch" in sys.argv:
            idx = sys.argv.index("--branch")
            branch = sys.argv[idx + 1]

        try:
            watch_for_failures(branch=branch, interval=interval)
        except KeyboardInterrupt:
            print("\nStopped watching.")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
