# Code Quality Rubric (LLM Judge)

## Scoring Guidelines

Evaluate the agent's code output on a scale of 1-5 for each dimension.

### 1. Correctness (1-5)
- **5**: Code is correct, handles all edge cases, passes all tests
- **4**: Code is mostly correct with minor issues
- **3**: Code works for happy path but misses edge cases
- **2**: Code has bugs or logical errors
- **1**: Code is fundamentally broken

### 2. Readability (1-5)
- **5**: Clear variable names, good comments, logical structure, follows style guides
- **4**: Mostly readable with minor unclear sections
- **3**: Readable but could benefit from more comments/structure
- **2**: Difficult to follow without significant refactoring
- **1**: Nearly impossible to understand

### 3. Efficiency (1-5)
- **5**: Optimal algorithm, minimal redundant operations, good resource usage
- **4**: Generally efficient with minor improvements possible
- **3**: Acceptable efficiency, some redundant work
- **2**: Inefficient but functional
- **1**: Severely inefficient (e.g., nested loops on large datasets)

### 4. Idiomaticity (1-5)
- **5**: Follows language conventions perfectly, uses standard library appropriately
- **4**: Mostly idiomatic with minor deviations
- **3**: Mix of idiomatic and non-idiomatic patterns
- **2**: Mostly non-idiomatic code
- **1**: Fighting against the language

### 5. Safety (1-5)
- **5**: No security issues, proper input validation, handles errors gracefully
- **4**: Minor security concerns or missing validations
- **3**: Some safety issues but not critical
- **2**: Notable security or error handling problems
- **1**: Vulnerable code (injection, exposure of secrets, etc.)

---

## Output Format

Return your evaluation as JSON:
```json
{
    "code_quality": <1-5>,
    "readability": <1-5>,
    "correctness": <1-5>,
    "efficiency": <1-5>,
    "safety": <1-5>,
    "reasoning": "<brief explanation of scores>"
}
```

## Notes for Judge

- Focus on the **final code output**, not the agent's reasoning or explanation
- If no code was produced, score all dimensions as 1
- Consider the task category when evaluating (e.g., security tasks should have higher safety bar)
- Be consistent with scoring across similar cases