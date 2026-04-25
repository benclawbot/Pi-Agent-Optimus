# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Test Loop

Runs relevant tests based on file changes.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Test discovery patterns
TEST_PATTERNS = [
    # Same file, .test suffix
    lambda f: Path(str(f).replace(Path(f).suffix, ".test" + Path(f).suffix)),
    # Same file, .spec suffix
    lambda f: Path(str(f).replace(Path(f).suffix, ".spec" + Path(f).suffix)),
    # __tests__ directory
    lambda f: Path(str(f).replace(str(Path(f).parent), str(Path(f).parent / "__tests__"))),
    # tests/ directory (root level)
    lambda f: Path("tests" / Path(f).name),
    # spec/ directory
    lambda f: Path(str(f).replace(str(Path(f).parent), str(Path(f).parent / "spec"))),
]


def find_tests_for_file(file_path: str) -> list[Path]:
    """Find test files that cover a given source file."""
    source = Path(file_path)

    if not source.exists():
        return []

    found = []

    for pattern_fn in TEST_PATTERNS:
        test_path = pattern_fn(source)
        if test_path.exists():
            found.append(test_path)

    return found


def get_git_changed_files() -> list[str]:
    """Get list of changed files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        pass

    return []


def run_tests_for_file(file_path: str, test_path: Path) -> dict:
    """Run tests for a specific test file."""
    result = {
        "testFile": str(test_path),
        "passed": False,
        "duration": None,
        "output": None
    }

    # Detect test runner from project
    project_file = Path("package.json")
    has_cargo = Path("Cargo.toml").exists()

    if has_cargo:
        cmd = ["cargo", "test", "--test", test_path.stem]
    elif project_file.exists():
        # npm/yarn/pnpm
        cmd = ["npx", "vitest", "run", str(test_path)]
    else:
        result["error"] = "No test runner detected"
        return result

    try:
        start = subprocess.time.time()
        proc_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True
        )
        duration = subprocess.time.time() - start

        result["passed"] = proc_result.returncode == 0
        result["duration"] = round(duration, 1)
        result["output"] = proc_result.stdout + proc_result.stderr

    except subprocess.TimeoutExpired:
        result["error"] = "Test timeout (>120s)"
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: test-loop.py <command> [file]")
        print("Commands:")
        print("  run <file>        - Run tests for a file")
        print("  changed           - Run tests for changed files")
        print("  find <file>       - Find tests for a file")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: test-loop.py run <file>")
            sys.exit(1)

        file_path = sys.argv[2]
        tests = find_tests_for_file(file_path)

        if not tests:
            print(json.dumps({"file": file_path, "tests": [], "message": "No tests found"}))
            sys.exit(0)

        results = [run_tests_for_file(file_path, test) for test in tests]

        output = {
            "file": file_path,
            "tests": [str(t) for t in tests],
            "results": results,
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r["passed"]),
                "failed": sum(1 for r in results if not r["passed"])
            }
        }

        print(json.dumps(output, indent=2))

    elif cmd == "changed":
        files = get_git_changed_files()
        if not files:
            print(json.dumps({"changed": [], "message": "No changed files"}))
            sys.exit(0)

        output = {"changed": files, "tests": {}}

        for file in files:
            tests = find_tests_for_file(file)
            if tests:
                output["tests"][file] = [str(t) for t in tests]

        print(json.dumps(output, indent=2))

    elif cmd == "find":
        if len(sys.argv) < 3:
            print("Usage: test-loop.py find <file>")
            sys.exit(1)

        file_path = sys.argv[2]
        tests = find_tests_for_file(file_path)

        print(json.dumps({
            "file": file_path,
            "tests": [str(t) for t in tests],
            "count": len(tests)
        }, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
