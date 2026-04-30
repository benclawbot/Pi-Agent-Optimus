# Pi Agent Optimus - Evaluation Framework

Comprehensive evaluation system for testing the entire Pi agent harness — LLM, skills, instructions, and tools working together.

## Architecture

```
evaluation/
├── config.json                  # Configuration (dimensions, weights, API keys)
├── benchmark/                   # Benchmark suite system
│   ├── tasks/                   # Generated task suites
│   ├── protocols/              # Benchmark protocols
│   └── data/                   # Results storage
├── scripts/
│   ├── benchmark_generator.py  # Generate task suites
│   ├── benchmark_runner.py     # Run evaluations
│   ├── benchmark_comparison.py # Compare versions
│   └── ...                     # Other utilities
├── dashboard.html              # Simple dashboard
├── dashboard-comprehensive.html # Full analysis dashboard
└── README.md
```

## Quick Start

```bash
# Generate benchmark suite (first time)
python3 scripts/benchmark_generator.py --count 8

# Run full benchmark
python3 scripts/benchmark_runner.py --version v1.0

# View dashboard
python3 -m http.server 8080
# Open http://localhost:8080/dashboard.html
```

## 10 Evaluation Dimensions

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| **Speed** | 15% | Latency (P50/P95/P99), throughput, cost efficiency |
| **Output Quality** | 20% | Task success rate, correctness, coherence |
| **Code Quality** | 15% | Test pass rate, linting, maintainability |
| **Reasoning** | 15% | Multi-step accuracy, error recovery, step efficiency |
| **Adaptability** | 10% | Adaptation score, few-shot learning |
| **Proactivity** | 10% | Initiative rate, goal completion without intervention |
| **Reliability** | 10% | Failure rate, consistency across runs |
| **Tool Use** | 0% | Correct tool selection, chaining efficiency |
| **UX** | 0% | Time to usable result, iterations required |
| **Safety** | 5% | Policy violations, refusal correctness |

## Benchmark Categories

- **coding** - Code generation, debugging, refactoring
- **reasoning** - Logical problem solving, chain-of-thought
- **tool_usage** - Multi-step tool orchestration
- **open_ended** - Autonomous planning and improvement
- **safety** - Policy compliance and adversarial handling
- **adversarial** - Edge cases, incomplete info, misleading instructions

## Commands Reference

```bash
# Generate tasks
python3 scripts/benchmark_generator.py --count 8

# Run benchmark
python3 scripts/benchmark_runner.py --version v1.0

# Compare versions
python3 scripts/benchmark_comparison.py --baseline      # vs first run
python3 scripts/benchmark_comparison.py --evolution      # track over time

# View dashboards
python3 -m http.server 8080
# dashboard.html - Quick overview
# dashboard-comprehensive.html - Full analysis
```

## Scorecard Example

```
OVERALL SCORE: 0.72

Dimension       Weight   Score   Weighted
speed            15%     0.85    0.128
output_quality   20%     0.75    0.150
code_quality     15%     0.70    0.105
reasoning        15%     0.68    0.102
adaptability     10%     0.65    0.065
proactivity      10%     0.72    0.072
reliability      10%     0.80    0.080
safety            5%     0.90    0.045
```

## Key Metrics

### Latency
- P50 < 2s = Excellent
- P95 < 5s = Good
- P99 < 10s = Acceptable

### Task Success
- 80%+ = Excellent
- 60-80% = Good
- <60% = Needs work

### Proactivity
- Initiative rate > 50% = Good
- Goal completion without intervention = Key indicator

## Dashboards

Start server and open in browser:
```bash
cd evaluation && python3 -m http.server 8080
```

**Simple Dashboard** (`dashboard.html`):
- Summary cards with trends
- Line charts for each metric
- Recent runs table

**Comprehensive Dashboard** (`dashboard-comprehensive.html`):
- Full scorecard with all dimensions
- Latency statistics (P50/P95/P99)
- Version comparison
- Proactivity breakdown

## Nightly Automation

```bash
# Schedule nightly benchmark
python3 scripts/scheduler.py setup

# Check status
python3 scripts/scheduler.py status
```

## Skill Evolution

When issues are detected repeatedly (threshold: 3+ failures):
1. System writes `skill-evolution-needed.json`
2. Review relevant skills
3. Generalize to handle pattern (not project-specific)
4. Re-run benchmark to verify fix

## LLM Judge Strategy

Using MiniMax M2.5 (weaker) to judge MiniMax M2.7 (stronger):
- Tests explainability
- Lower cost than self-judging
- Real-world evaluation scenario

## Key Insights

A strong harness should show:
1. **Consistent gains** across versions
2. **No regression** in reliability
3. **Better performance** per cost unit
4. **High proactivity** without sacrificing quality
5. **Low latency** at P95/P99

Most people evaluate AI systems incorrectly because they:
- rely too much on subjective impressions
- don't separate dimensions
- don't test edge cases and failure modes

Track these trends in the dashboard to identify degradation early.