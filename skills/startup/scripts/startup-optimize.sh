#!/usr/bin/env bash
# startup-optimize.sh - Fast startup with caching for large codebases
# Usage: source this from startup skill

set -e

CACHE_DIR="${HOME}/.pi/cache"
PROJECT_HASH=$(echo "$PWD" | md5sum | cut -d' ' -f1)
PROJECT_CACHE="$CACHE_DIR/$PROJECT_HASH"

# Create cache dir
mkdir -p "$PROJECT_CACHE"

# Check cache validity (24h)
is_cache_valid() {
    if [ -f "$PROJECT_CACHE/conventions.json" ] && [ -f "$PROJECT_CACHE/last-scan.txt" ]; then
        LAST_SCAN=$(cat "$PROJECT_CACHE/last-scan.txt")
        CURRENT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        # Simple check: if same day, cache is valid
        LAST_DAY=$(echo "$LAST_SCAN" | cut -d'T' -f1)
        CURRENT_DAY=$(echo "$CURRENT" | cut -d'T' -f1)
        [ "$LAST_DAY" = "$CURRENT_DAY" ]
    else
        return 1
    fi
}

# Scan conventions in parallel
scan_conventions() {
    local output_file="$1"
    
    # Run scans in parallel, collect PIDs
    local temp_files=()
    
    # Scan root files
    for f in CLAUDE.md AGENTS.md COPILOT.md .cursorrules .clinerules .github/copilot-instructions.md; do
        if [ -f "$f" ]; then
            echo "=== $f ===" >> "$output_file"
            head -30 "$f" >> "$output_file" 2>/dev/null || true
            echo "" >> "$output_file"
        fi
    done
    
    # Scan directories in parallel
    for d in .claude .cursor .pi .github; do
        if [ -d "$d" ]; then
            echo "=== $d ===" >> "$output_file"
            ls -la "$d" >> "$output_file" 2>/dev/null || true
            echo "" >> "$output_file"
        fi
    done
    
    # Scan source structure
    echo "=== PROJECT STRUCTURE ===" >> "$output_file"
    ls -d */ 2>/dev/null | grep -v -E "^(node_modules|\.git|dist|build|target|vendor|__pycache__|\.next|\.nuxt)" | head -20 >> "$output_file" 2>/dev/null || true
    echo "" >> "$output_file"
    
    # Quick package.json check
    if [ -f package.json ]; then
        echo "=== PACKAGE INFO ===" >> "$output_file"
        cat package.json | grep -E '"(name|version|scripts|dependencies|devDependencies)"' | head -20 >> "$output_file" 2>/dev/null || true
    fi
    
    # Save timestamp
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$PROJECT_CACHE/last-scan.txt"
}

# Main logic
if is_cache_valid; then
    echo "Using cached conventions from $PROJECT_CACHE"
    cat "$PROJECT_CACHE/conventions.json"
else
    echo "Building convention cache for this project..."
    TEMP_OUTPUT=$(mktemp)
    scan_conventions "$TEMP_OUTPUT"
    mv "$TEMP_OUTPUT" "$PROJECT_CACHE/conventions.json"
    cat "$PROJECT_CACHE/conventions.json"
fi