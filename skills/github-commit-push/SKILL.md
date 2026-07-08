---
name: github-commit-push
description: "Commit and push a project's changes to GitHub, including adding a README screenshot for visual interfaces. Use when the user asks to commit and push, save work to GitHub, publish to a new/existing repo, or sync local changes upstream. Handles repo init, .gitignore, README screenshot (web UI, TUI, native, charts), conventional commit message, branch setup, and first push. Assumes `gh auth status` is logged in."
---

# GitHub Commit + Push

End-to-end: stage changes, commit with a clean message, push to GitHub. Handles the gotchas (parent-dir git confusion, oversized `.bun`/`.cache`/`.pi-progress*` getting staged, missing `.gitignore`, no remote yet).

## Pre-flight

```bash
# 1. Confirm gh is logged in
gh auth status

# 2. Confirm we're inside the project root (NOT the parent)
cd <project-dir>
pwd
git rev-parse --show-toplevel   # MUST equal $(pwd)
```

If `git rev-parse --show-toplevel` is the **parent** of `pwd`:
- A previous `git init` ran in the wrong directory. Fix:
  ```bash
  rm -rf .git
  git init
  git rev-parse --show-toplevel   # confirm now correct
  ```

## .gitignore (defensive defaults)

Before the first `git add`, ensure `.gitignore` excludes the agent/tool caches that pollute staging on Windows:

```gitignore
# Agent / tool caches
.bun/
.cache/
.codex/
.hermes/
.pi-progress*
.pi-progress/
.cagent/
.impeccable/

# OS / IDE
.DS_Store
Thumbs.db
.idea/
.vscode/

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/

# Project data (most projects want this)
data/
runs/
*.db
*.npz
.env
```

If `.gitignore` already exists, append any missing patterns.

## Screenshot (if visual interface)

If the project has a visual interface (webpage, desktop app, dashboard, mobile UI, terminal UI, chart-heavy output), add a screenshot to the README before committing. A repo without a preview forces readers to clone + run before they know what they're looking at; one image flips that.

**Detect automatically** (pick whichever applies):

```bash
# Web app (any of: src with .tsx/.jsx/.vue/.svelte, or known web frameworks)
ls src/ 2>/dev/null | grep -E '\.(tsx|jsx|vue|svelte)$' && echo "WEB_UI"

# Terminal UI (TUI / curses-style / Rich / Textual / bubbletea)
grep -rE 'Textual|curses|blessed|bubbletea' --include='*.py' --include='*.ts' --include='*.go' src/ 2>/dev/null && echo "TUI"

# Desktop / native GUI
ls src/ 2>/dev/null | grep -E '\.(swift|kt|kotlin)$' && echo "NATIVE_UI"

# Charts / plots in output (matplotlib, plotly, d3)
grep -rE 'matplotlib|plotly|chart\.js|d3\.' --include='*.py' --include='*.ts' --include='*.tsx' src/ 2>/dev/null && echo "CHARTS"
```

**Capture the screenshot:**

- **Web UI**: run the dev server, open in headless browser, save PNG. With Chrome DevTools MCP:
  ```bash
  # navigate to localhost, then save full-page screenshot to docs/screenshot.png
  ```
  Or scripted (Playwright/Puppeteer):
  ```bash
  npx playwright screenshot --full-page http://localhost:3000 docs/screenshot.png
  ```
- **TUI**: run the app with a fixed seed/input, capture the terminal frame. With `script` (Unix) or `vhs` (https://github.com/charmbracelet/vhs — preferred, produces reproducible `.tape` files):
  ```bash
  vhs docs/demo.tape    # produces docs/demo.gif
  ```
- **Charts/output**: render once with sample data, save the output as `docs/screenshot.png`. Most plotting libs have `savefig()` / `write_image()`.
- **Native GUI**: capture with OS tool (`screencapture` on macOS, `gnome-screenshot` on Linux, Snipping Tool on Windows). Save as `docs/screenshot.png`.

**Add to README** near the top, right after the one-line description:

```markdown
![Screenshot](docs/screenshot.png)
```

If the README is structured differently (badges, table of contents), place the image in the first ~20 lines so it's visible before the fold on GitHub.

**Naming**: prefer `docs/screenshot.png` (or `docs/demo.gif` for animated). Avoid names that include the project name — repo URLs already provide that context, redundancy wastes alt-text.

**Commit the image**: `docs/screenshot.png` is a normal tracked file. If the image is large (>1 MB), prefer WebP or optimize with `pngquant` / `oxipng` first. Don't commit `.mov`/raw screen recordings — convert to GIF or short MP4 first.

**Skip this step** when:
- The project is a CLI / library / API with no visual surface (a CLI's `--help` text doesn't count as a UI).
- The output is plain text logs (those don't render meaningfully as a screenshot).
- The user has explicitly said "no screenshot" or "internal tool, no public docs".

## Commit

Write a Conventional Commits message:
- `<type>(<scope>): <summary>` (≤72 chars, no trailing period)
- Body explains **what** changed and **why**
- `Co-Authored-By: Claude <noreply@anthropic.com>` footer (when AI-assisted)

```bash
git add -A
git status --short   # scan for parent-dir leakage or unexpected files
git commit -m "<type>(<scope>): <summary>" \
            -m "<body explaining what + why>" \
            -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Scan `git status --short` before committing.** Watch for:
- `?? ../` entries → repo root is wrong, abort and re-init
- `.bun/`, `.cache/`, `.pi-progress*` → missing from .gitignore, add and re-add
- Secrets (`.env`, `id_rsa`, `*.pem`) → STOP, ask user

## Push

### Existing repo (already has a remote)

```bash
git remote -v   # confirm remote exists
git push -u origin <current-branch>
```

If branch name is `master` and remote default is `main` (or vice-versa), rename the local branch first:
```bash
git branch -m master main    # or vice-versa
```

### New repo (no remote yet)

```bash
# Create on GitHub and push in one shot
gh repo create <repo-name> \
  --public \
  --description "<one-line description>" \
  --source=. \
  --remote=origin \
  --push

# If --push fails (e.g., empty repo, branch mismatch), fall back to:
git remote add origin https://github.com/<owner>/<repo-name>.git
git push -u origin <current-branch>
```

**If `gh repo create ... --push` errors with `"--push enabled but no commits found in <path>"`:**
- It walks up looking for a git repo. Make sure you're inside it (`cd` first), then:
  ```bash
  git remote add origin https://github.com/<owner>/<repo>.git
  git push -u origin <current-branch>
  ```

## Verify

```bash
git log --oneline -5
git remote -v
gh repo view --web   # optional: open in browser
```

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `git add` triggers `Filename too long` | `.bun/`, `.cache/` cache dirs | Add to `.gitignore`, `git rm -r --cached <dir>` |
| `git status` shows `?? ../.cache/` etc. | git init ran in parent dir | `rm -rf .git && git init` inside project |
| `LF will be replaced by CRLF` warnings | Windows + Unix line endings | Harmless. Commit will use CRLF. Disable with `git config core.autocrlf false` if it bothers you |
| `Permission denied (publickey)` | ssh key not configured | Use `https://` remote, not `git@github.com:` |
| Push rejected: `non-fast-forward` | Remote has commits you don't have | `git pull --rebase origin <branch>` then push |
| Push rejected: `protected branch` | Branch protection rules | Push to a feature branch + open PR |

## When NOT to use this skill

- User only wants to commit (no push) → use the `commit` skill
- User only wants to inspect GitHub (PRs, issues, CI) → use the `github` skill
- Pre-commit hook failures need fixing → fix hooks first, then re-run
- Need to capture the screenshot (use the `screenshot-handler` skill), then return here