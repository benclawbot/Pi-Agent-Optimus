---
name: skill-evolution
description: Advanced skill evolution with LLM-based evaluation, session mining, and continuous improvement. Use when "learn from this", "improve this skill", "evolve skill", "evaluate skill", "measure skill quality", "mine sessions", or when building evaluation datasets.
allowed-tools: Read,Bash,write,edit,execute_command
---

# Skill Evolution

Advanced skill improvement through structured feedback, evaluation, and evolutionary optimization.

## Core Concept

Skills evolve through a **4-phase improvement loop**:
```
Phase 1: LLM-as-Judge Evaluation
Phase 2: Session Mining for Examples  
Phase 3: Size & Semantic Guards
Phase 4: Evolutionary Improvement
```

## Memory Structure

All evolution data goes to `.pi/skill-memory.json`:

```json
{
  "lessons": [...],
  "gaps": [...],
  "patterns": [...],
  "evaluations": [...],
  "sessions": [...],
  "evolutions": [...]
}
```

## Phase 1: LLM-as-Judge Evaluation

### Fitness Rubric

When evaluating a skill, score on:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Follows procedure | 30% | Does the agent follow the skill's steps? |
| Output quality | 30% | Is the result correct and useful? |
| Conciseness | 20% | Within token budget? Not verbose? |
| Completeness | 20% | All required elements present? |

### Score Range

| Score | Label | Action |
|-------|-------|--------|
| 90-100 | Excellent | Skill is performing well |
| 70-89 | Good | Minor improvements possible |
| 50-69 | Needs Work | Significant gaps identified |
| <50 | Poor | Major rewrite recommended |

### Evaluation Command

```bash
python scripts/evaluate-skill.py --skill skill-evolution --eval-source session-db
python scripts/evaluate-skill.py --skill skill-evolution --eval-source synthetic --count 10
```

## Phase 2: Session Mining

Extract real examples from session history:

### Mining Sources

| Source | Description | Quality |
|--------|-------------|---------|
| `session.jsonl` | Current session conversations | High |
| `~/.pi/agent/sessions/` | Historical sessions | High |
| `synthetic` | LLM-generated test cases | Medium |

### What to Mine

1. **Success cases** — Tasks where skill worked well
2. **Failure cases** — Where skill guidance was ignored or failed
3. **Edge cases** — Unusual scenarios handled well
4. **Patterns** — Repeated behaviors worth codifying

### Mining Command

```bash
python scripts/mine-sessions.py --skill skill-evolution --limit 20
python scripts/mine-sessions.py --all-skills --limit 10
```

## Phase 3: Guardrails

### Size Limits

| Target | Max Size | Reason |
|--------|----------|--------|
| SKILL.md | 15KB | Injected as message, wastes context |
| Tool descriptions | 500 chars | Sent every turn |
| References | 50KB per file | Loaded conditionally |

### Semantic Preservation

Before any update:
1. Compare evolved text to original
2. Ensure core intent preserved
3. Check for drift in trigger phrases
4. Verify examples still relevant

### Validation Commands

```bash
python scripts/validate-skill.py --skill skill-evolution --check-size --check-semantic
```

## Phase 4: Evolutionary Improvement

### The Evolution Loop

```
1. SELECT TARGET
   - Pick skill with lowest evaluation scores
   - Load current version as baseline

2. BUILD CANDIDATES
   - Generate 3-5 variants with targeted changes
   - Use LLM to propose improvements based on gaps

3. EVALUATE CANDIDATES
   - Run each candidate on eval dataset
   - Score using LLM-as-judge rubric

4. SELECT BEST
   - Pick highest-scoring variant
   - If improvement > 10%, apply it
   - Otherwise, keep original

5. VALIDATE
   - Check size limits
   - Verify semantic preservation
   - Run functional tests
```

### Evolution Command

```bash
python scripts/evolve-skill.py --skill skill-evolution --iterations 5
```

## Commands Reference

| Command | Purpose |
|---------|---------|
| `evaluate-skill.py` | Score skill quality with LLM judge |
| `mine-sessions.py` | Extract examples from history |
| `validate-skill.py` | Check size and semantic limits |
| `evolve-skill.py` | Run evolution loop on skill |
| `report-skill.py` | Generate improvement report |

## File Structure

```
skill-evolution/
├── SKILL.md
├── scripts/
│   ├── skill-memory.py         # Basic memory ops
│   ├── evaluate-skill.py       # Phase 1: LLM evaluation
│   ├── mine-sessions.py       # Phase 2: Session mining
│   ├── validate-skill.py      # Phase 3: Guardrails
│   ├── evolve-skill.py        # Phase 4: Evolution
│   └── report-skill.py        # Generate reports
├── references/
│   └── evolution-patterns.md   # Evolution patterns
└── datasets/                   # Eval datasets (gitignored)
```

## Example Workflow

```
User: evolve skill-evolution
→ Phase 1: Evaluate current skill (score: 72/100)
→ Phase 2: Mine sessions for examples (found 15)
→ Phase 3: Check limits (passed)
→ Phase 4: Generate 3 candidates
   - Candidate A: +15% (improved examples)
   - Candidate B: +8% (better trigger phrases)
   - Candidate C: +3% (refined instructions)
→ Apply Candidate A (+15% improvement)
→ Validation passed
```

## Self-Evolution

This skill evolves itself:
- Track its own evaluation scores
- Identify its gaps
- Apply improvements
- Measure impact

The feedback loop applies to this skill too.
