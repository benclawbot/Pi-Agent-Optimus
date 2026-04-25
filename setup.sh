#!/bin/bash
# ============================================
# Pi Agent Optimus - Complete Setup Script
# ============================================
# One-command installer for memory-augmented Pi
# Run: curl -s https://raw.githubusercontent.com/benclawbot/Pi-Agent-Optimus/main/setup.sh | bash
# Or: ./setup.sh (if cloned locally)
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || (-f /proc/version && "$(grep -i microsoft /proc/version)" ) ]]; then
        echo "windows"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Paths
PI_DIR="$HOME/.pi/agent"
SKILLS_DIR="$PI_DIR/skills"
SETTINGS_FILE="$PI_DIR/settings.json"
USER_MEMORY="$HOME/.pi/user-memory.md"
USER_CONFIG="$HOME/.pi/github-config"

# ============================================
# STEP 1: Welcome & Prerequisites Check
# ============================================
echo ""
echo -e "${CYAN}=========================================="
echo -e "  Pi Agent Optimus - Setup Wizard"
echo -e "==========================================${NC}"
echo ""

PLATFORM=$(detect_os)
echo -e "${BLUE}Detected platform: ${PLATFORM}${NC}"
echo ""

# Check if running interactively
if [ ! -t 0 ]; then
    INTERACTIVE=false
else
    INTERACTIVE=true
fi

# ============================================
# STEP 2: Node.js Installation
# ============================================
check_nodejs() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node -v 2>/dev/null | tr -d 'v')
        echo -e "${GREEN}✓${NC} Node.js found: v$NODE_VERSION"
        return 0
    else
        echo -e "${RED}✗${NC} Node.js not found"
        return 1
    fi
}

install_nodejs() {
    echo ""
    echo -e "${YELLOW}Installing Node.js...${NC}"
    
    if [ "$PLATFORM" == "windows" ]; then
        echo "Downloading Node.js LTS..."
        curl -fsSL https://get.npmjs.org/install.sh | sh 2>/dev/null || {
            echo "Please install Node.js manually:"
            echo "  1. Go to https://nodejs.org"
            echo "  2. Download and run the Windows installer"
            echo "  3. Restart your terminal"
            echo "  4. Run this setup again"
            exit 1
        }
    elif [ "$PLATFORM" == "macos" ]; then
        if command -v brew &> /dev/null; then
            brew install node
        else
            echo "Please install Node.js via https://nodejs.org or 'brew install node'"
            exit 1
        fi
    elif [ "$PLATFORM" == "linux" ]; then
        if command -v apt-get &> /dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs
        elif command -v yum &> /dev/null; then
            curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash - && sudo yum install -y nodejs
        else
            echo "Please install Node.js from https://nodejs.org"
            exit 1
        fi
    fi
}

# Check Node.js
if ! check_nodejs; then
    install_nodejs
fi

# Verify Node.js after installation attempt
if ! check_nodejs; then
    echo ""
    echo -e "${RED}Node.js installation failed. Please install manually from https://nodejs.org${NC}"
    exit 1
fi

# ============================================
# STEP 3: Install Pi Coding Agent
# ============================================
echo ""
echo -e "${BLUE}Step 1/4: Installing Pi coding agent...${NC}"

if command -v pi &> /dev/null; then
    echo -e "${GREEN}✓${NC} Pi already installed"
elif command -v npx &> /dev/null; then
    echo "Installing Pi via npx..."
    npm install -g @mariozechner/pi-coding-agent 2>/dev/null || {
        echo -e "${YELLOW}Note: Pi will be installed on first run via npx${NC}"
    }
else
    echo -e "${YELLOW}Note: Will use npx to run Pi${NC}"
fi

# ============================================
# STEP 4: Install Skills & Configuration
# ============================================
echo ""
echo -e "${BLUE}Step 2/4: Installing enhanced skills...${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create directories
mkdir -p "$PI_DIR"
mkdir -p "$SKILLS_DIR"

# Copy skills
if [ -d "$SCRIPT_DIR/skills" ]; then
    SKILLS_SOURCE="$SCRIPT_DIR/skills"
elif [ -d "$SCRIPT_DIR" ]; then
    SKILLS_SOURCE="$SCRIPT_DIR/skills"
else
    echo "Error: Could not find skills directory"
    exit 1
fi

echo "Installing skills..."
for skill in "$SKILLS_SOURCE"/*; do
    if [ -d "$skill" ]; then
        skill_name=$(basename "$skill")
        echo -e "  ${GREEN}✓${NC} $skill_name"
        rm -rf "$SKILLS_DIR/$skill_name" 2>/dev/null || true
        cp -r "$skill" "$SKILLS_DIR/"
    fi
done

# Backup and install settings
if [ -f "$SETTINGS_FILE" ]; then
    echo ""
    echo "Backing up existing settings..."
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
fi

if [ -f "$SCRIPT_DIR/settings.json" ]; then
    cp "$SCRIPT_DIR/settings.json" "$SETTINGS_FILE"
fi

echo -e "${GREEN}✓${NC} Settings installed"

# ============================================
# STEP 5: User Memory Setup
# ============================================
echo ""
echo -e "${BLUE}Step 3/4: Setting up user preferences...${NC}"

if [ ! -f "$USER_MEMORY" ]; then
    if [ -f "$SCRIPT_DIR/user-memory.md" ]; then
        cp "$SCRIPT_DIR/user-memory.md" "$USER_MEMORY"
    else
        cat > "$USER_MEMORY" << 'EOF'
# User Memory

Personal preferences that apply across all projects.

## Communication Preferences
- **Response verbosity:** Concise
- **Format:** Context-dependent (bullets/tables/steps)
- **Tone:** Direct

## Work Style
- **Clarification first:** Ask before implementing
- **Implementation after:** Execute without questions
- **Session mode:** Stay in main session

## Tools
- **Shell:** CMD / PowerShell
- **Git workflow:** Merge
EOF
    fi
    echo -e "${YELLOW}Created user-memory.md - you can customize it later${NC}"
else
    echo -e "${GREEN}✓${NC} User preferences already exist"
fi

# ============================================
# STEP 6: Python Dependencies
# ============================================
echo ""
echo -e "${BLUE}Step 4/4: Installing Python dependencies...${NC}"

install_python_dep() {
    local pkg=$1
    if python -c "import $pkg" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $pkg already installed"
    else
        echo -e "  Installing $pkg..."
        pip install "$pkg" 2>/dev/null || echo -e "  ${YELLOW}Note: $pkg optional${NC}"
    fi
}

if command -v python &> /dev/null; then
    install_python_dep "watchdog"
    install_python_dep "psycopg2_binary"
    install_python_dep "pymysql"
else
    echo -e "${YELLOW}Python not found - some skills may have reduced functionality${NC}"
fi

# ============================================
# STEP 7: Provider Setup Guide
# ============================================
echo ""
echo -e "${CYAN}=========================================="
echo -e "  Setup Complete!"
echo -e "==========================================${NC}"
echo ""

# Interactive provider setup prompt
if [ "$INTERACTIVE" = true ]; then
    echo -e "${YELLOW}Would you like to configure your AI provider now? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Available providers:"
        echo "  1. Anthropic (Claude) - Recommended"
        echo "  2. OpenAI (GPT-4)"
        echo "  3. Google (Gemini)"
        echo ""
        echo "Enter your choice (1-3) or press Enter to skip:"
        read -r choice
        
        case $choice in
            1) echo "Get your Anthropic API key at: https://console.anthropic.com/" ;;
            2) echo "Get your OpenAI API key at: https://platform.openai.com/" ;;
            3) echo "Get your Google API key at: https://makersuite.google.com/" ;;
            *) echo "Skipping provider setup" ;;
        esac
    fi
fi

# ============================================
# FINAL: Instructions
# ============================================
echo ""
echo -e "${GREEN}✓${NC} Pi Agent Optimus is ready!"
echo ""
echo "=========================================="
echo "  Quick Start"
echo "=========================================="
echo ""
echo "1. Get an API key:"
echo "   - Anthropic: https://console.anthropic.com/"
echo "   - OpenAI: https://platform.openai.com/"
echo ""
echo "2. Start Pi:"
if command -v pi &> /dev/null; then
    echo "   pi"
else
    echo "   npx pi"
fi
echo ""
echo "3. On first run, enter your API key when prompted"
echo ""
echo "=========================================="
echo "  Available Skills"
echo "=========================================="
echo ""
echo "  /skill:project-health       Check CI, deps, tests"
echo "  /skill:system-awareness    Track running servers"
echo "  /skill:auto-test          Run tests for files"
echo "  /skill:ci-watcher         Monitor CI pipelines"
echo "  /skill:architecture-diagram Generate diagrams"
echo "  /skill:scheduler          Set reminders"
echo "  /skill:auto-recover       Diagnose errors"
echo "  /skill:db-introspect      Query schemas"
echo ""
echo "=========================================="
echo "  Documentation"
echo "=========================================="
echo ""
echo "  README: https://github.com/benclawbot/Pi-Agent-Optimus"
echo "  Architecture: https://github.com/benclawbot/Pi-Agent-Optimus/blob/main/ARCHITECTURE.html"
echo ""
