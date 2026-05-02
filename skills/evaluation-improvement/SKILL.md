---
name: evaluation-improvement
description: Run and interpret the shared agent evaluation harness for Pi Agent Optimus or Hermes, then turn repeated failures into concrete fixes or skill-evolution work.
allowed-tools: Read,Bash,write,edit,execute_command
---

# Evaluation Improvement

Use this skill when asked to evaluate Pi Agent Optimus, evaluate Hermes, compare the agents, investigate benchmark failures, or improve skills based on evaluation results.

## Canonical Harness

The only active harness is:

```bash
/home/thomas/Dropbox/Projects/Pi-Agent-Optimus/evaluation
```

Do not create separate per-agent evaluation harnesses. Hermes and Pi are selected through the same CLI.

## Commands

Run quick evaluations:

```bash
cd /home/thomas/Dropbox/Projects/Pi-Agent-Optimus/evaluation
python3 run_eval.py run --agent pi --quick
python3 run_eval.py run --agent hermes --quick
```

Run a category:

```bash
python3 run_eval.py run --agent pi --category debug --quick
python3 run_eval.py run --agent hermes --category refactor --quick
```

Review outputs:

```bash
ls -t reports/pi reports/hermes results/pi results/hermes
```

## Evaluation Protocol

1. Run the smallest useful eval first, usually `--quick` or a single category.
2. Read the JSON result and markdown report. Do not trust the aggregate score alone.
3. Inspect objective validation first:
   - `pass`: deterministic checks succeeded
   - `partial`: some checks failed; inspect failed checks
   - `fail`: critical validator or generated tests failed
   - `low_evidence`: task lacks deterministic validators and should not support strong benchmark claims
4. Separate failures into:
   - task defects: bad prompt, missing expected criteria, secret-like historical data
   - harness defects: broken parser, bad scoring, agent command failure
   - agent defects: wrong code, weak tests, poor tool use, poor final report
   - skill defects: repeated missing behavior that should be encoded into a skill
5. Fix harness defects before judging agent quality.
6. For repeated agent defects, update or create skills through `skill-evolution`.
7. Re-run the same task/category to verify the fix.

## Guardrails

- Score raw agent output. Do not add rewarded phrases after the run.
- Keep Pi and Hermes on the same task corpus.
- Store results per agent under `results/pi`, `results/hermes`, `reports/pi`, and `reports/hermes`.
- Historical tasks must have objective `requirements` or `expected` criteria.
- Prefer tasks with `validators.expected_files`, `validators.test_command`, and required/forbidden output patterns.
- Generated Python tests are executed with `python3 -m pytest -q` unless a task overrides `validators.test_command`.
- Failed critical objective checks cap the aggregate score, regardless of LLM judge output.
- Tasks with no deterministic checks are `low_evidence`.
- Skip tasks containing raw tokens, API keys, or credential-shaped strings.
- Timeout or process failure is a failed evaluation, not a fast success.

## Improvement Output

When reporting an evaluation improvement, include:

- Agent evaluated: `pi` or `hermes`
- Task/category scope
- Main failures with concrete evidence
- Whether the issue is task, harness, agent, or skill related
- Files changed
- Verification command and result
