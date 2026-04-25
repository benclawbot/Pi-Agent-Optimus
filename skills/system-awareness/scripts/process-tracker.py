# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Process Tracker

Tracks running dev servers and processes across the system.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("~/.pi/processes.json").expanduser()

COMMON_PORTS = {
    3000: "Next.js/CRA",
    5173: "Vite",
    5174: "Vite (alt)",
    5175: "Vite (extra)",
    8000: "Django/Flask",
    8080: "Java/Go",
    5000: "Flask dev",
    9229: "Node debugger",
    4000: "SvelteKit",
    4200: "Angular",
}


def load_state() -> dict:
    """Load process state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"registered": []}


def save_state(state: dict) -> None:
    """Save process state."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def list_processes() -> dict:
    """List known processes."""
    state = load_state()
    processes = state.get("registered", [])

    return {
        "processes": processes,
        "ports": [p.get("port") for p in processes if p.get("port")],
        "count": len(processes)
    }


def detect_port_on_windows(port: int) -> dict:
    """Check if a port is in use on Windows."""
    cmd = f'netstat -ano | findstr ":{port}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        for line in lines:
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = int(parts[-1])
                    return {"in_use": True, "pid": pid, "port": port}

        return {"in_use": False, "port": port}
    except Exception as e:
        return {"in_use": None, "error": str(e)}


def kill_by_port(port: int) -> dict:
    """Kill process using a specific port."""
    port_info = detect_port_on_windows(port)

    if not port_info.get("in_use"):
        return {"killed": False, "reason": "Port not in use"}

    pid = port_info["pid"]

    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)

        # Remove from state
        state = load_state()
        state["registered"] = [p for p in state["registered"] if p.get("port") != port]
        save_state(state)

        return {"killed": True, "pid": pid, "port": port}
    except subprocess.CalledProcessError:
        return {"killed": False, "error": f"Failed to kill process {pid}"}


def kill_by_pid(pid: int) -> dict:
    """Kill process by PID."""
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)

        # Remove from state
        state = load_state()
        state["registered"] = [p for p in state["registered"] if p.get("pid") != pid]
        save_state(state)

        return {"killed": True, "pid": pid}
    except subprocess.CalledProcessError:
        return {"killed": False, "error": f"Failed to kill process {pid}"}


def register_process(name: str, port: int, directory: str) -> dict:
    """Register a running process."""
    state = load_state()

    # Check if already registered
    for p in state["registered"]:
        if p.get("port") == port:
            p["pid"] = None  # Unknown
            p["started"] = datetime.now().isoformat()[:19] + "Z"
            p["name"] = name
            p["dir"] = directory
            save_state(state)
            return {"registered": True, "updated": True}

    # Add new
    state["registered"].append({
        "name": name,
        "port": port,
        "dir": directory,
        "started": datetime.now().isoformat()[:19] + "Z"
    })

    save_state(state)
    return {"registered": True, "updated": False}


def main():
    if len(sys.argv) < 2:
        print("Usage: process-tracker.py <command> [args]")
        print("Commands:")
        print("  list")
        print("  check-port <port>")
        print("  kill <port>")
        print("  kill --pid <pid>")
        print("  register <port> <name> <directory>")
        sys.exit(1)

    cmd = sys.argv[1]
    result = {}

    if cmd == "list":
        result = list_processes()

    elif cmd == "check-port":
        port = int(sys.argv[2])
        result = detect_port_on_windows(port)

    elif cmd == "kill":
        if "--pid" in sys.argv:
            pid = int(sys.argv[sys.argv.index("--pid") + 1])
            result = kill_by_pid(pid)
        else:
            port = int(sys.argv[2])
            result = kill_by_port(port)

    elif cmd == "register":
        port = int(sys.argv[2])
        name = sys.argv[3]
        directory = sys.argv[4]
        result = register_process(name, port, directory)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
