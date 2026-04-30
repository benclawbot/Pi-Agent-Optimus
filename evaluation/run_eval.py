#!/usr/bin/env python3
"""
Pi Agent Optimus Evaluation Framework
CLI entry point - can be called as `python3 run_eval.py` or aliased as `pi-eval`
"""

import sys
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(script_dir))

from orchestrator import main as orchestrator_main

if __name__ == "__main__":
    orchestrator_main()