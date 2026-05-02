#!/usr/bin/env python3
"""
Agent Evaluation Framework
CLI entry point for evaluating Pi Agent Optimus or Hermes.
"""

import sys
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(script_dir))

from orchestrator import main as orchestrator_main

if __name__ == "__main__":
    orchestrator_main()
