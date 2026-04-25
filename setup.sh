#!/bin/bash
# Pi Agent Optimus - Setup Script
# Run this from the Pi-Agent-Optimus directory

set -e

echo "=========================================="
echo "  Pi Agent Optimus - Setup"
echo "=========================================="

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
    SKILLS_DIR="$HOME/.pi/agent/skills"
    SETTINGS_FILE="$HOME/.pi/agent/settings.json"
    USER_MEMORY="$HOME/.pi/user-memory.md"
else
    PLATFORM="unix"
    SKILLS_DIR="$HOME/.pi/agent/skills"
    SETTINGS_FILE="$HOME/.pi/agent/settings.json"
    USER_MEMORY="$HOME/.pi/user-memory.md"
fi

echo ""
echo "Platform: $PLATFORM"
echo "Skills directory: $SKILLS_DIR"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p "$SKILLS_DIR"
mkdir -p "$(dirname $SETTINGS_FILE)"

# Copy skills
echo "Installing skills..."
for skill in skills/*; do
    if [ -d "$skill" ]; then
        skill_name=$(basename "$skill")
        echo "  - $skill_name"
        rm -rf "$SKILLS_DIR/$skill_name"
        cp -r "$skill" "$SKILLS_DIR/"
    fi
done

# Backup existing settings
if [ -f "$SETTINGS_FILE" ]; then
    echo ""
    echo "Backing up existing settings..."
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
fi

# Copy settings
echo ""
echo "Installing settings..."
cp settings.json "$SETTINGS_FILE"

# Copy user memory template (if not exists)
if [ ! -f "$USER_MEMORY" ]; then
    echo ""
    echo "Creating user memory template..."
    cp user-memory.md "$USER_MEMORY"
    echo ""
    echo "NOTE: Please edit ~/.pi/user-memory.md to set your preferences"
else
    echo ""
    echo "NOTE: user-memory.md already exists, skipping"
fi

# Install optional Python dependencies
echo ""
echo "Installing optional Python dependencies..."
pip install watchdog psycopg2-binary pymysql 2>/dev/null || echo "  (some packages may have failed - that's ok)"

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit ~/.pi/user-memory.md with your preferences"
echo "2. Start pi: npx pi"
echo "3. Say 'load user preferences' to test"
echo ""
echo "Available commands:"
echo "  /skill:project-health    - Check CI status, deps, tests"
echo "  /skill:system-awareness  - List running processes"
echo "  /skill:auto-test        - Run tests for a file"
echo "  /skill:architecture-diagram - Generate diagrams"
echo "  /skill:scheduler        - Set reminders"
echo "  /skill:auto-recover      - Diagnose errors"
echo ""
