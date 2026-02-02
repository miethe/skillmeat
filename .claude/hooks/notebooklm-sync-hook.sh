#!/bin/bash
# NotebookLM Sync Hook for Claude Code
# Triggers on Write|Edit of markdown files in docs/ or root directory
# Syncs changed files to NotebookLM notebook

set -euo pipefail

LOG_FILE="$HOME/.notebooklm/sync.log"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

log() {
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Read stdin (Claude Code passes JSON via stdin to hooks)
STDIN_JSON=$(cat)

# Parse file_path from tool_input
FILE_PATH=$(echo "$STDIN_JSON" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

if [[ -z "$FILE_PATH" ]]; then
    exit 0  # No file path, nothing to do
fi

# Convert absolute path to relative (if it's within the project)
if [[ "$FILE_PATH" == "$PROJECT_DIR"/* ]]; then
    REL_PATH="${FILE_PATH#$PROJECT_DIR/}"
else
    REL_PATH="$FILE_PATH"
fi

# Check if it's a markdown file
if [[ ! "$REL_PATH" =~ \.md$ ]]; then
    exit 0  # Not a markdown file
fi

# Check if it's in scope (root level or docs/ directory, but not .claude/)
IN_SCOPE=false

# Root level markdown (no directory separators except for the file itself)
if [[ "$REL_PATH" =~ ^[^/]+\.md$ ]]; then
    IN_SCOPE=true
fi

# docs/ directory (any depth)
if [[ "$REL_PATH" =~ ^docs/ ]]; then
    IN_SCOPE=true
fi

# Exclude .claude/ directory
if [[ "$REL_PATH" =~ ^\.claude/ ]]; then
    IN_SCOPE=false
fi

if [[ "$IN_SCOPE" != "true" ]]; then
    exit 0  # Not in sync scope
fi

log "Syncing: $REL_PATH"

# Run the sync script
cd "$PROJECT_DIR"
python scripts/notebooklm_sync/update.py "$REL_PATH" 2>> "$LOG_FILE" || {
    log "ERROR: Sync failed for $REL_PATH"
    exit 0  # Don't fail the hook
}

log "Sync complete: $REL_PATH"
exit 0
