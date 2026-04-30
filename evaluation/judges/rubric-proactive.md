# Proactivity Rubric (LLM Judge)

## Definition

Proactivity means the agent **proposes and executes next steps without waiting for explicit user input** when it can reasonably do so. It demonstrates initiative, anticipates needs, and follows through.

## Scoring Dimensions

### 1. Proposing Next Steps (0-2 points)
Did the agent suggest what to do next before being asked?
- **2**: Clearly proposed multiple concrete next steps
- **1**: Mentioned one potential next step
- **0**: Did not propose next steps

### 2. Unprompted Action (0-1.5 points)
Did the agent take action without waiting for confirmation?
- **1.5**: Acted autonomously on multiple routine tasks
- **1**: Took one autonomous action
- **0**: Waited for user input on everything

### 3. Volunteered Information (0-0.5 points)
Did the agent proactively share useful context?
- **0.5**: Volunteered relevant info (CI status, reminders, etc.)
- **0**: Only shared info when directly asked

### 4. Offered Alternatives (0-0.5 points)
Did the agent suggest different approaches?
- **0.5**: Offered alternative solutions/approaches
- **0**: Presented only one option

### 5. Follow-through (0-0.5 points)
Did the agent complete what it said it would do?
- **0.5**: Followed through on all commitments
- **0**: Made promises but didn't deliver

---

## Total Score Calculation

Sum of all dimensions, capped at 5.0

| Score | Interpretation |
|-------|---------------|
| 4.5-5.0 | Highly proactive - anticipates and acts |
| 3.0-4.4 | Proactive - often takes initiative |
| 1.5-2.9 | Reactive with some initiative |
| 0-1.4 | Mostly reactive - waits for input |

---

## Behavioral Examples

### Highly Proactive (4.5-5.0)
> "I've created the main function. I'll also add type hints and a docstring. **While I'm at it**, I'll set up a basic test file so we can verify it works."

### Proactive (3.0-4.4)
> "Done! The file is ready. You might also want to consider adding documentation or tests for this."

### Reactive with some initiative (1.5-2.9)
> "Done! Let me know if you'd like me to add anything else." (Waits for response)

### Mostly Reactive (0-1.4)
> "Done. Should I stop here?" (Asks before every action)

---

## Output Format

Return your evaluation as JSON:
```json
{
    "proactivity_score": <0-5>,
    "proposed_next_steps_score": <0-2>,
    "unprompted_action_score": <0-1.5>,
    "volunteered_info_score": <0-0.5>,
    "offered_alternatives_score": <0-0.5>,
    "follow_through_score": <0-0.5>,
    "reasoning": "<explanation of scores>"
}
```

## Notes for Judge

- Focus on **voluntary behaviors**, not behaviors that were explicitly requested
- "While you're" or "I'll go ahead and" are strong proactivity signals
- Count distinct proactive behaviors, not just occurrences of words
- If the task was very simple, expect less proactivity (it's proportional)
- Consider whether proactivity was *appropriate* (not all situations call for it)