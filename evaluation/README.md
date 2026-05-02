# Agent Evaluation Framework

Single evaluation harness for running the same benchmark tasks against Pi Agent Optimus or Hermes.

## Quick Start

```bash
cd evaluation

# Evaluate Pi Agent Optimus
python3 run_eval.py run --agent pi --quick

# Evaluate Hermes
python3 run_eval.py run --agent hermes --quick

# Run one category
python3 run_eval.py run --agent hermes --category debug --quick
```

Reports and result JSON are written per agent:

```text
evaluation/reports/pi/
evaluation/reports/hermes/
evaluation/results/pi/
evaluation/results/hermes/
```

## What It Measures

The harness executes task files from `tasks/synthetic/` and curated historical tasks from `tasks/historical/`.

Core signals:

- Objective validation: expected files, required/forbidden output patterns, and generated test execution.
- Python test execution: if a task requires tests or generated `test_*.py` files, the harness runs `python3 -m pytest -q` inside the task workspace before it is deleted.
- LLM judge scores for correctness, code quality, readability, efficiency, and safety.
- Process-level reliability: timeout and process failures score as failed runs.
- Speed relative to a per-agent baseline.
- Proactivity from raw agent output only. The harness does not inject rewarded phrases into the output.
- Tool-use and UX proxies from available traces.

Objective validation is treated as primary evidence. Failed critical checks cap the overall score, even when the LLM judge is generous. Tasks without objective validators are marked `low_evidence` and cannot receive a top benchmark score.

## Agent Selection

Agents are configured in `config.json` under `evaluation.agents`.

```json
{
  "evaluation": {
    "targetAgent": "pi",
    "agents": {
      "pi": {"name": "Pi Agent Optimus", "command": "pi"},
      "hermes": {"name": "Hermes Agent", "command": "hermes"}
    }
  }
}
```

Use `--agent pi` or `--agent hermes` at runtime. The task corpus and scoring code stay the same, which makes comparisons meaningful.

## Task Requirements

A task should include objective criteria:

```json
{
  "name": "fix-sql-injection",
  "category": "debug",
  "description": "Fix the SQL injection vulnerability.",
  "requirements": ["Use parameterized queries", "Keep same interface", "Add tests"],
  "context": "...code...",
  "expected": "Fixed with tests proving injection is blocked"
}
```

Optional validators make a task stronger:

```json
{
  "validators": {
    "expected_files": ["cache.py", "test_cache.py"],
    "test_command": "python3 -m pytest -q",
    "required_output_patterns": ["Test Results"],
    "forbidden_output_patterns": ["Traceback"]
  }
}
```

If `validators.expected_files` is omitted, the harness extracts filenames from `expected`. If `test_command` is omitted but the task requires tests or creates `test_*.py`, it runs `python3 -m pytest -q`.

Validation grades:

- `pass`: objective checks passed.
- `partial`: some checks failed; score is capped.
- `fail`: critical checks failed; score is capped at failure range.
- `low_evidence`: no objective validators existed; useful for smoke tests, not strong benchmark claims.

Historical tasks are only loaded when they have `requirements` or `expected` criteria and do not contain credential-like secrets.

## Commands

```bash
# Quick run
python3 run_eval.py run --agent pi --quick

# Full run
python3 run_eval.py run --agent hermes --full

# Compare latest runs for the selected/default agent
python3 run_eval.py compare

# Show trends
python3 run_eval.py trends
```

## Skill Improvement Loop

When repeated failures cross the configured threshold, the harness writes `skill-evolution-needed.json`. Use the shared `evaluation-improvement` skill plus `skill-evolution` to convert repeated failures into concrete skill updates for either agent.
