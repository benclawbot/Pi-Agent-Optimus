# CI Status Reference

## GitHub CLI Commands

### List Recent Runs
```bash
gh run list --limit 5
gh run list --limit 5 --json status,conclusion,name,startedAt
```

### View Run Details
```bash
gh run view <run-id>
gh run view <run-id> --log
```

### Trigger a Run
```bash
gh workflow run <workflow-name>
gh workflow run <workflow-name> --ref <branch>
```

### Download Artifacts
```bash
gh run download <run-id>
```

## Status Values

| Status | Meaning |
|--------|---------|
| `queued` | Waiting to start |
| `in_progress` | Running |
| `completed` | Finished |

## Conclusion Values

| Conclusion | Meaning |
|------------|---------|
| `success` | Passed |
| `failure` | Failed |
| `cancelled` | Manually cancelled |
| `skipped` | Skipped |
| `action_required` | Needs attention |

## JSON Output

For scripting, always use `--json`:
```bash
gh run list --json status,conclusion,name,headBranch,startedAt,updatedAt
```

## Workflow Names

List available workflows:
```bash
gh workflow list
```

## Filtering

By branch:
```bash
gh run list --branch main
```

By workflow:
```bash
gh run list --workflow "CI"
```

By status:
```bash
gh run list --status failure
```
