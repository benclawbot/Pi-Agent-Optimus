# Project Memory

## Critical Conventions

### Always Extract Filenames from Task Specs
When a task specifies `expected_file:<filename>` in validators, you MUST create that exact filename.
- Task says "expected_file:config.py" → create `config.py`, NOT `settings.py` or `configuration.py`
- Even if the name seems wrong or "more descriptive", USE THE SPECIFIED NAME
- This is a deterministic validator — wrong filename = instant fail even if tests pass

### File Naming Pattern
- Look for `expected_file:` in task description
- Create the EXACT filename specified
- Verify before responding with "done"

## Benchmark Failures to Avoid
- Wrong filename: causes objective_score ~0.49 (fail grade)
- Correct code + wrong filename = 0 points on validation
