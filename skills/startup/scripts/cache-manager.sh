#!/usr/bin/env bash
# cache-manager.sh - Manage project convention cache
# Usage: ./cache-manager.sh [status|clear|clear-all|refresh]

CACHE_DIR="${HOME}/.pi/cache"

case "${1:-status}" in
    status)
        echo "=== Pi Convention Cache Status ==="
        if [ -d "$CACHE_DIR" ]; then
            echo "Cache directory: $CACHE_DIR"
            echo ""
            for project_cache in "$CACHE_DIR"/*; do
                if [ -d "$project_cache" ]; then
                    name=$(basename "$project_cache")
                    last_scan=""
                    conv_count=""
                    if [ -f "$project_cache/last-scan.txt" ]; then
                        last_scan=$(cat "$project_cache/last-scan.txt")
                    fi
                    if [ -f "$project_cache/conventions.json" ]; then
                        conv_count=$(wc -l < "$project_cache/conventions.json")
                    fi
                    echo "Project: ${name:0:8}..."
                    echo "  Last scan: $last_scan"
                    echo "  Conventions: $conv_count lines"
                    echo ""
                fi
            done
        else
            echo "No cache directory found"
        fi
        ;;
    clear)
        if [ -z "$2" ]; then
            echo "Usage: $0 clear <project-hash-or-*>"
            echo "Use '$0 status' to see project hashes"
            exit 1
        fi
        if [ "$2" = "*" ]; then
            rm -rf "$CACHE_DIR"/*
            echo "Cleared all caches"
        else
            rm -rf "$CACHE_DIR/$2"
            echo "Cleared cache for project $2"
        fi
        ;;
    clear-all)
        rm -rf "$CACHE_DIR"
        mkdir -p "$CACHE_DIR"
        echo "Cleared all caches"
        ;;
    refresh)
        # Force refresh by touching the cache file
        PROJECT_HASH=$(echo "$PWD" | md5sum | cut -d' ' -f1)
        if [ -f "$CACHE_DIR/$PROJECT_HASH/conventions.json" ]; then
            rm -f "$CACHE_DIR/$PROJECT_HASH/conventions.json"
            echo "Cache invalidated for current project"
        else
            echo "No cache found for current project"
        fi
        ;;
    *)
        echo "Usage: $0 [status|clear|clear-all|refresh]"
        ;;
esac