#!/usr/bin/env bash
# agent-pull.sh — pull approved skills on agent startup
# Run from ~/.pi/agent/ or wherever the agent's home is.
#
# Usage: ./agent-pull.sh
#   SKILLS_REPO=https://github.com/you/memory-skills  (default from env or hardcoded)
#   AGENT_DIR=~/.pi/agent                            (where to install skills)
#
set -euo pipefail

AGENT_DIR="${AGENT_DIR:-$HOME/.pi/agent}"
SKILLS_REPO="${SKILLS_REPO:-git@github.com:you/memory-skills.git}"
SKILLS_TMP="/tmp/memory-skills-pull-$$"
SKILLS_TARGET="$AGENT_DIR/skills"

# GitHub SSH known hosts
mkdir -p ~/.ssh && chmod 700 ~/.ssh

echo "[agent-pull] Pulling skills from $SKILLS_REPO"

# Clone to tmp
git clone --depth=1 "$SKILLS_REPO" "$SKILLS_TMP" 2>/dev/null || {
  echo "[agent-pull] No skills repo or no network — skipping"
  exit 0
}

# Read registry
REGISTRY="$SKILLS_TMP/registry.json"
if [[ ! -f "$REGISTRY" ]]; then
  echo "[agent-pull] No registry.json in skills repo — skipping"
  rm -rf "$SKILLS_TMP"
  exit 0
fi

# Load skill IDs from registry
SKILL_IDS=$(python3 -c "import json,sys; r=json.load(open('$REGISTRY')); print('\n'.join(s['id'] for s in r.get('skills',[]) if s.get('status')=='active'))" 2>/dev/null || echo "")

if [[ -z "$SKILL_IDS" ]]; then
  echo "[agent-pull] No active skills — skipping"
  rm -rf "$SKILLS_TMP"
  exit 0
fi

# Copy each skill's SKILL.md to the agent's skills dir
COPIED=0
for SKILL_ID in $SKILL_IDS; do
  SRC_SKILL="$SKILLS_TMP/$SKILL_ID/SKILL.md"
  DST_SKILL="$SKILLS_TARGET/$SKILL_ID/SKILL.md"
  if [[ -f "$SRC_SKILL" ]]; then
    mkdir -p "$(dirname "$DST_SKILL")"
    cp "$SRC_SKILL" "$DST_SKILL"
    echo "[agent-pull] Installed skill: $SKILL_ID"
    COPIED=$((COPIED+1))
  fi
done

rm -rf "$SKILLS_TMP"
echo "[agent-pull] Done — $COPIED skills installed to $SKILLS_TARGET"
