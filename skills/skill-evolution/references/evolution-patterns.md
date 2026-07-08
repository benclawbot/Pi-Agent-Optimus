# Evolution Patterns

## Candidate Generation Patterns

### 1. Trigger Expansion
Expand trigger phrases to catch more variations:

```markdown
# Before
Use when "fix bug", "debug", or "error"

# After  
Use when "fix bug", "fix error", "debug", "investigate error", or "diagnose issue"
```

### 2. Example Addition
Add concrete examples to clarify expected behavior:

```markdown
## Example

### Simple Case
```
User: fix the login bug
Skill: Identifies login-related code, runs tests, suggests fix
```

### Complex Case
```
User: intermittent timeout in production
Skill: Checks logs, identifies root cause, proposes solution
```
```

### 3. Structure Improvement
Add validation or acceptance criteria:

```markdown
## Validation

Before claiming a skill is complete:
- [ ] All steps execute without error
- [ ] Output format matches specification
- [ ] Edge cases handled gracefully
```

### 4. Condensation
Remove redundant content while preserving meaning:

```markdown
# Before (verbose)
In order to properly handle this situation, the first thing
you should do is check the configuration file to ensure that
all the necessary settings are in place.

# After (concise)
Check configuration file for required settings.
```

## Evaluation Patterns

### LLM-as-Judge Prompt

```
You are evaluating a skill for an AI coding agent.

Skill Name: {skill_name}
Skill Description: {description}

Evaluate on a scale of 0-100:
1. Follows Procedure (30%): Does it provide clear, actionable steps?
2. Output Quality (30%): Is the expected output well-specified?
3. Conciseness (20%): Is it appropriately sized?
4. Completeness (20%): Are all elements present?

Provide a score and brief justification for each criterion.
```

### Semantic Similarity Check

Use these questions to verify preservation:
1. Does the core purpose remain the same?
2. Are trigger phrases still present?
3. Do examples still illustrate the skill's purpose?
4. Is the structure (steps, references, etc.) intact?

## Gap Analysis Patterns

### Low Scores by Category

| Score < 70 | Likely Gap |
|-----------|-----------|
| Procedure | Missing steps or unclear workflow |
| Quality | No examples or vague output specs |
| Conciseness | Over 10KB or redundant content |
| Completeness | Missing references or validation |

### Improvement Actions

| Gap Type | Candidate Type |
|---------|---------------|
| Missing triggers | Expand trigger phrases |
| No examples | Add example section |
| Vague output | Add output format spec |
| No validation | Add validation criteria |
| Too verbose | Condense and remove redundancy |

## Evolution Loop

```
1. Evaluate baseline (60-80%)
   ↓
2. Identify lowest-scoring criteria
   ↓
3. Generate targeted candidates
   ↓
4. Score candidates (relative to baseline)
   ↓
5. Select best if > 10% improvement
   ↓
6. Validate (size, semantic)
   ↓
7. Apply or keep original
```

## Guardrail Thresholds

| Guardrail | Limit | Action if Exceeded |
|-----------|-------|-------------------|
| SKILL.md size | 15KB | Reject or warn |
| Description | 1024 chars | Warn |
| Reference files | 50KB each | Warn |
| Semantic drift | >20% change | Review required |

## Session Mining Queries

Useful patterns to mine from sessions:

```python
# Success patterns
success_patterns = [
    "done", "completed", "success", "working",
    "fixed", "implemented", "created"
]

# Failure patterns
failure_patterns = [
    "didn't work", "failed", "error", "exception",
    "not working", "broken", "issue", "problem"
]

# Learning captures
learning_patterns = [
    "learn from this", "remember this", "improve",
    "capture this", "pattern noticed"
]
```
