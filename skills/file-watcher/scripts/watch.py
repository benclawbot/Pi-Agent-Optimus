# /// script
# requires-python = ">=3.10"
# dependencies = ["watchdog"]
# ///

"""
File Watcher

Watch files for changes and trigger automated actions.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

STATE_FILE = Path("~/.pi/watch-state.json").expanduser()


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"watched": [], "pid": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def find_tests_for_file(file_path: str) -> list[str]:
    """Find tests related to a file."""
    source = Path(file_path)
    stem = source.stem
    parent = source.parent

    patterns = [
        parent / f"{stem}.test{source.suffix}",
        parent / f"{stem}.spec{source.suffix}",
        parent / "__tests__" / source.name,
        Path("tests") / source.name,
        Path("tests") / f"{stem}.test{source.suffix}",
    ]

    return [str(p) for p in patterns if p.exists()]


def run_tests_for_file(file_path: str) -> dict:
    """Run tests for a file."""
    tests = find_tests_for_file(file_path)

    if not tests:
        return {"file": file_path, "tests": [], "ran": False}

    # Use vitest or jest as available
    for test in tests:
        try:
            result = subprocess.run(
                ["npx", "vitest", "run", test],
                capture_output=True,
                text=True,
                timeout=120,
                shell=True
            )
            return {
                "file": file_path,
                "tests": tests,
                "ran": True,
                "passed": result.returncode == 0,
                "output": result.stdout[:500]
            }
        except Exception:
            pass

    return {"file": file_path, "tests": tests, "ran": False}


def watch_directory(dir_path: str, debounce: float = 0.5) -> None:
    """Watch a directory for file changes."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("Error: watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    class ChangeHandler(FileSystemEventHandler):
        def __init__(self):
            self.last_run = {}

        def on_modified(self, event):
            if event.is_directory:
                return

            path = event.src_path
            if path.endswith(('.ts', '.js', '.tsx', '.jsx', '.py')):
                # Debounce
                now = time.time()
                if path in self.last_run and now - self.last_run[path] < debounce:
                    return
                self.last_run[path] = now

                print(f"\n--- File changed: {path} ---")
                result = run_tests_for_file(path)
                print(json.dumps(result, indent=2))

    handler = ChangeHandler()
    observer = Observer()
    observer.schedule(handler, dir_path, recursive=True)
    observer.start()

    print(f"Watching {dir_path} for changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching.")


def main():
    if len(sys.argv) < 2:
        print("Usage: watch.py <command> [args]")
        print("Commands:")
        print("  run --file <path>     Watch a single file")
        print("  run --dir <path>      Watch a directory")
        print("  check --file <path>   Run tests once, no watch")
        print("  stop                  Stop watching")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "run":
        if "--file" in sys.argv:
            idx = sys.argv.index("--file")
            file_path = sys.argv[idx + 1]
            # Single file - just run tests once
            result = run_tests_for_file(file_path)
            print(json.dumps(result, indent=2))
        elif "--dir" in sys.argv:
            idx = sys.argv.index("--dir")
            dir_path = sys.argv[idx + 1]
            watch_directory(dir_path)
        else:
            print("Error: specify --file or --dir")
            sys.exit(1)

    elif cmd == "check":
        if "--file" in sys.argv:
            idx = sys.argv.index("--file")
            file_path = sys.argv[idx + 1]
            result = run_tests_for_file(file_path)
            print(json.dumps(result, indent=2))
        else:
            print("Error: specify --file")
            sys.exit(1)

    elif cmd == "stop":
        state = load_state()
        if state.get("pid"):
            try:
                import os
                os.kill(state["pid"], 9)
                state["pid"] = None
                save_state(state)
                print("Stopped watcher.")
            except Exception as e:
                print(f"Error stopping: {e}")
        else:
            print("No active watcher.")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
