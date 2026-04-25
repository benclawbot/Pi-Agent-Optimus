# Contributing to Pi Agent Optimus

Thank you for your interest in contributing!

## How to Contribute

### 1. Reporting Issues

- Check existing issues before creating new ones
- Include your OS, Python version, and Pi version
- Provide reproduction steps

### 2. Suggesting New Skills

Create a new skill by following the Agent Skills standard:

```
skill-name/
├── SKILL.md              # Required
├── scripts/              # Optional
├── references/           # Optional
└── assets/              # Optional
```

See [Agent Skills specification](https://agentskills.io) for details.

### 3. Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## Skill Guidelines

### SKILL.md Requirements

- Frontmatter with `name` and `description`
- Third-person description with trigger phrases
- Imperative voice in body
- Examples of expected output
- Max 500 lines

### Script Requirements

- Use PEP 723 inline metadata
- Output structured JSON
- Handle errors explicitly
- Document interface in SKILL.md

### Validation

Run before submitting:
```bash
python scripts/validate-skills.py
```

## Code of Conduct

- Be respectful
- Focus on the problem
- Help others learn

## Questions?

Open an issue or start a discussion.
