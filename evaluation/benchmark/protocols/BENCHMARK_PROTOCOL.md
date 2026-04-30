# Benchmark Suite Protocol

## Overview

This benchmark suite evaluates Pi Agent across 10 dimensions, measuring:
- Speed & Efficiency
- Output Quality
- Code Quality
- Reasoning & Problem-Solving
- Adaptability & Learning
- Proactivity & Autonomy
- Robustness & Reliability
- Tool Use & Integration
- User Experience
- Safety & Alignment

## Running the Benchmark

### Full Benchmark (50 tasks)
```bash
python3 scripts/benchmark_runner.py --version v1.0
```

### Quick Benchmark (subset)
```bash
python3 scripts/benchmark_runner.py --version v1.0 --quick
```

### Generate New Benchmark Suite
```bash
python3 scripts/benchmark_generator.py --count 10
```

## Benchmark Suite Structure

```
benchmark/
├── tasks/
│   └── benchmark-suite.json    # Generated task suite
├── protocols/
│   └── BENCHMARK_PROTOCOL.md   # This file
└── data/
    ├── latest.json             # Most recent results
    └── *_results.json          # Historical results
```

## Categories

| Category | Tasks | Purpose |
|----------|-------|---------|
| coding | 8 | Code generation, debugging, refactoring |
| reasoning | 8 | Logical problem solving |
| tool_usage | 8 | Multi-step tool orchestration |
| open_ended | 8 | Autonomous planning and improvement |
| safety | 8 | Policy compliance |
| adversarial | 3 | Edge cases and failure modes |

## Dimensions & Weights

| Dimension | Weight | Metrics |
|-----------|--------|---------|
| Speed | 15% | Latency (P50/P95/P99), throughput, cost |
| Output Quality | 20% | Success rate, correctness, coherence |
| Code Quality | 15% | Test pass %, lint, maintainability |
| Reasoning | 15% | Multi-step accuracy, error recovery |
| Adaptability | 10% | Adaptation score, few-shot learning |
| Proactivity | 10% | Initiative rate, goal completion |
| Reliability | 10% | Failure rate, consistency |
| Safety | 5% | Policy violations, refusal correctness |

## Scoring

### Rubric (0-3 scale for task success)
- 0 = Wrong - completely incorrect
- 1 = Partially correct - major gaps
- 2 = Correct but messy / suboptimal
- 3 = Correct and clean

### Proactivity (0-5 scale)
- 0 = No initiative - waits for everything
- 3 = Sometimes proactive
- 5 = Exceptional - autonomous execution

## Interpreting Results

### Overall Score (0-1)
- 0.8+ : Excellent - production ready
- 0.6-0.8 : Good - minor improvements possible
- 0.4-0.6 : Needs work - significant gaps
- <0.4 : Critical - major issues

### Dimension Scores (0-1)
Each dimension is normalized to 0-1 where 1 is best.

### Latency
- P50 < 2s : Excellent
- P50 2-5s : Good
- P50 > 5s : Needs improvement

## Comparison

Compare versions:
```bash
python3 scripts/benchmark_comparison.py --baseline
python3 scripts/benchmark_comparison.py --version v0.9
python3 scripts/benchmark_comparison.py --evolution
```

## Dashboards

Access dashboards at:
- Simple: `dashboard.html` - Quick overview
- Comprehensive: `dashboard-comprehensive.html` - Full analysis

Start server:
```bash
python3 -m http.server 8080
# Open http://localhost:8080/dashboard.html
```

## Continuous Monitoring

Schedule nightly benchmarks:
```bash
python3 scripts/scheduler.py setup
```

Results are stored in `benchmark/data/` and trends are tracked over time.

## Key Insights

A strong harness should show:
1. **Consistent gains** across versions
2. **No regression** in reliability
3. **Better performance** per cost unit
4. **High proactivity** without sacrificing quality
5. **Low latency** at P95/P99

Track these trends in the dashboard to identify degradation early.