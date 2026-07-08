#!/usr/bin/env bash
# agent-pull.sh — pull approved skills on agent startup.
# Skills come from the Omni-Memory/skills folder in your git repo.
#
# Usage:
#   AGENT_DIR=~/.pi/agent bash ~/Omni-Memory/skills/agent-pull.sh
#   Or run from your pi/agent dir: bash ../Omni-Memory/skills/agent-pull.sh
#
set -euo pipefail

AGENT_DIR="${AGENT_DIR:-$HOME/.pi/agent}"
SKILLS_REPO_DIR="${SKILLS_REPO_DIR:-$HOME/Omni-Memory}"
SKILLS_SOURCE="$SKILLS_REPO_DIR/skills"
SKILLS_TARGET="$AGENT_DIR/skills"

# GitHub SSH known hosts (first run only)
mkdir -p ~/.ssh && chmod 700 ~/.ssh

echo "[agent-pull] Pulling skills from $SKILLS_SOURCE"

if [[ ! -d "$SKILLS_SOURCE" ]]; then
  echo "[agent-pull] Omni-Memory repo not cloned yet — cloning..."
  GIT_REPO="https://github.com/benclawbot/Omni-Memory.git"
  git clone --depth=1 "$GIT_REPO" "$SKILLS_REPO_DIR" 2>/dev/null || {
    echo "[agent-pull] Clone failed — check SSH key and network"
    exit 0
  }
fi

# Pull latest skills
cd "$SKILLS_REPO_DIR"
git pull --ff-only 2>/dev/null || echo "[agent-pull] Pull failed — using cached skills"

# Read registry
REGISTRY="$SKILLS_SOURCE/registry.json"
if [[ ! -f "$REGISTRY" ]]; then
  echo "[agent-pull] No registry.json — no skills to install"
  exit 0
fi

SKILL_IDS=$(python3 -c "import json,sys; r=json.load(open('$REGISTRY')); print('\n'.join(s['id'] for s in r.get('skills',[]) if s.get('status')=='active'))" 2>/dev/null || echo "")

if [[ -z "$SKILL_IDS" ]]; then
  echo "[agent-pull] No active skills"
  exit 0
fi

COPIED=0
for SKILL_ID in $SKILL_IDS; do
  SRC="$SKILLS_SOURCE/$SKILL_ID/SKILL.md"
  DST="$SKILLS_TARGET/$SKILL_ID/SKILL.md"
  if [[ -f "$SRC" ]]; then
    mkdir -p "$(dirname "$DST")"
    cp "$SRC" "$DST"
    echo "[agent-pull] Installed: $SKILL_ID"
    COPIED=$((COPIED+1))
  fi
done

echo "[agent-pull] Done — $COPIED skills installed to $SKILLS_TARGET"
