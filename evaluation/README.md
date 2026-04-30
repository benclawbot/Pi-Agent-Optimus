# Pi Agent Optimus Evaluation Framework

An automated evaluation system for Pi agent with feedback loops. Tests the entire system — LLM, skills, instructions, and tools — not just isolated components.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                   EVALUATION PIPELINE                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Task Pool]  →  [Pi Agent Executes]  →  [Results]    │
│       │                │                   │            │
│       ▼                ▼                   ▼            │
│  Synthetic +      Captures trace      LLM Judge scores  │
│  Historical       + output +          Proactivity check │
│  tasks            files               Speed metrics      │
│       │                │                   │            │
│       │                ▼                   ▼            │
│       │         [Metrics Extraction]  [Skill Evolution] │
│       │                │                   │            │
│       │                ▼                   ▼            │
│       └─────────→ [Reports: MD + HTML + Terminal]      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Three Evaluation Pillars

| Pillar | Measures | How |
|--------|----------|-----|
| **Code Quality** | Correctness, style, security, readability | LLM judge (MiniMax M2.5) + automated checks |
| **Speed** | Execution time, token efficiency | Wall clock + trace analysis |
| **Proactivity** | Initiative, next steps, following through | Behavioral pattern detection |

## Quick Start

```bash
# Run full evaluation (40 tasks)
python3 run_eval.py run --full

# Run quick evaluation (10 tasks)
python3 run_eval.py run --quick

# Compare with previous run
python3 run_eval.py compare

# Show trends
python3 run_eval.py trends
```

## Architecture

```
evaluation/
├── config.json              # Configuration (API keys, weights, thresholds)
├── orchestrator.py          # Main entry point
├── task_runner.py           # Executes tasks against Pi agent
├── judge.py                 # LLM-based judge (MiniMax M2.5)
├── metrics.py              # Extracts speed/efficiency metrics
├── proactivity.py          # Detects proactive behaviors
├── reporter.py             # Generates MD/HTML/terminal reports
├── historical_extractor.py # Extracts tasks from session logs
├── synthetic_generator.py  # Generates tasks from failure patterns
├── scheduler.py            # Manages nightly cron schedule
├── tasks/
│   ├── synthetic/          # Generated test tasks by category
│   │   ├── code-quality/
│   │   ├── debug/
│   │   ├── architecture/
│   │   └── refactor/
│   └── historical/        # Extracted from real session logs
├── judges/                 # Rubrics for LLM judges
│   ├── rubric-code.md
│   └── rubric-proactive.md
├── results/                # Raw results (JSON per run)
└── reports/               # Generated reports
```

## Configuration

Edit `config.json` to customize:

```json
{
  "evaluation": {
    "apiKey": "your-key",
    "judgeModel": "MiniMax-M2.5",
    "agentModel": "MiniMax-M2.7",
    "syntheticCount": 20,
    "historicalCount": 20,
    "timeoutSeconds": 300
  },
  "metrics": {
    "codeQuality": { "weight": 0.4 },
    "speed": { "weight": 0.3 },
    "proactivity": { "weight": 0.3 }
  },
  "skills": {
    "evolutionThreshold": 3,
    "autoUpdate": true
  }
}
```

## Nightly Schedule

Set up automated nightly evaluation:

```bash
# Schedule (runs at 3 AM)
python3 scripts/scheduler.py setup

# Check status
python3 scripts/scheduler.py status

# Remove schedule
python3 scripts/scheduler.py remove
```

## Task Sources

### Synthetic Tasks
Generated from failure patterns to test specific gaps:

```bash
# Generate tasks for a category
python3 scripts/synthetic_generator.py --category code-quality --count 5

# Generate from failure file
python3 scripts/synthetic_generator.py --from-failure failure.json --count 3
```

### Historical Tasks
Extracted from real Pi agent session logs:

```bash
# Extract recent prompts as tasks
python3 scripts/historical_extractor.py --max 20 --dry-run

# Save to tasks/historical/
python3 scripts/historical_extractor.py --max 20
```

## Skill Evolution Loop

When issues are detected repeatedly:

1. **Threshold reached**: 3+ tasks fail with similar pattern
2. **Trigger**: System writes `skill-evolution-needed.json`
3. **Action**: Review and generalize relevant skill
4. **Test**: Re-run evaluation to verify fix

```
Issue detected → Pattern identified → Skill generalized → Tested in next run
```

## LLM Judge Strategy

Using MiniMax M2.5 (weaker) to judge MiniMax M2.7 (stronger):
- Tests if the stronger model can be explained to a weaker one
- Simulates real-world explainability requirements
- Lower cost than self-judging

## Reports

All three formats generated on each run:

- **Markdown**: `reports/YYYY-MM-DD_HH-MM-SS_evaluation.md`
- **HTML**: `reports/YYYY-MM-DD_HH-MM-SS_evaluation.html` (dark themed)
- **Terminal**: Printed immediately with score breakdown

## Proactivity Detection

Detects proactive behaviors via pattern matching:

| Behavior | Pattern Examples |
|----------|------------------|
| Proposed next steps | "suggested:", "i can also", "next steps:" |
| Unprompted action | "i'll go ahead and", "automatically" |
| Volunteered info | "note that", "FYI:", "worth noting" |
| Offered alternatives | "alternatively:", "another option" |

## Extending

### Adding a New Rubric
1. Create `judges/rubric-new.md` with scoring guidelines
2. Update `judge.py` to load and use the rubric
3. Add to the evaluation prompt

### Adding Task Categories
1. Create `tasks/synthetic/new-category/`
2. Add templates to `synthetic_generator.py`
3. Update category_keywords in `historical_extractor.py`

## Notes

- Tasks run in isolated temp directories
- Pi agent runs with `--no-session` for clean evaluation
- Results stored in JSON for trend analysis
- Baseline established from first 10 runs, then compared against