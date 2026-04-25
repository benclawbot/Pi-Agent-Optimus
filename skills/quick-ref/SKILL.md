---
name: quick-ref
description: One-page reference for most-used commands. Use when "quick reference", "show commands", "help with git", "npm scripts", "common patterns", or "cheat sheet".
---

# Quick Reference

Your most-used commands in one place.

## Git

```bash
# Status & History
git status                    # What changed
git log --oneline -10         # Recent commits
git diff                      # Unstaged changes
git diff --staged             # Staged changes

# Branching
git branch                    # List branches
git checkout -b <name>        # Create & switch
git switch <name>             # Switch branch
git merge <branch>            # Merge into current

# Commit
git add -p                    # Stage hunks interactively
git commit -v                 # Commit with diff review
git commit --amend            # Fix last commit

# Remote
git pull                      # Fetch & merge
git push                      # Push to remote
git fetch --all               # Fetch all remotes

# Cleanup
git clean -fd                 # Remove untracked files
git restore .                 # Restore unstaged
```

## NPM / Node

```bash
# Scripts (package.json scripts)
npm run <script>              # Run script
npm test                      # Run tests
npm run build                 # Build project
npm run dev                   # Dev server

# Packages
npm install <pkg>             # Install package
npm install -D <pkg>          # Dev dependency
npm update                    # Update all
npm audit                     # Security audit
```

## Docker

```bash
# Containers
docker ps                     # Running containers
docker ps -a                  # All containers
docker stop <id>              # Stop container
docker rm <id>                # Remove container

# Images
docker images                 # Local images
docker rmi <id>               # Remove image
docker build -t <name> .      # Build image

# Compose
docker-compose up -d          # Start services
docker-compose down           # Stop services
docker-compose logs -f        # Follow logs
```

## File Operations

```bash
# Navigate
cd ~                          # Home
cd -                          # Previous dir
pushd <dir>                   # Push & cd
popd                          # Pop directory

# Find
find . -name "*.ts"           # Find files
grep -r "pattern" .            # Search content
ls -la                        # Long format

# Edit
cat file.txt                  # View file
touch file.txt                # Create empty
mkdir -p path/to/dir          # Create directories
rm -rf dir                    # Remove recursively
```

## Process Management

```bash
# List & Kill
ps aux | grep <name>          # Find process
kill -9 <pid>                # Force kill
pkill -f <name>               # Kill by name

# Background
ctrl+z                        # Suspend job
bg                            # Resume background
fg                            # Bring to foreground
nohup cmd &                   # Run detached
```

## System

```bash
# Info
uname -a                      # System info
df -h                         # Disk usage
free -h                       # Memory usage

# Network
curl -I <url>                 # Check URL
ping -c 4 <host>              # Test connectivity
netstat -tlnp                 # Listening ports
```

## Common Patterns

```bash
# Watch file changes (nodemon, etc.)
npx nodemon src/index.ts

# Run in container
docker run -it --rm <image> bash

# Pipe grep to useful output
git log --oneline | grep "fix"

# Xargs for batch
find . -name "*.log" | xargs rm

# Tee for log + output
command | tee output.log
```