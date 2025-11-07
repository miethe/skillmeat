#!/bin/bash

# Backup utilities for Claude commands
# Common backup and restore operations used across artifact commands

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/file-utils.sh" 2>/dev/null || true
source "$SCRIPT_DIR/git-utils.sh" 2>/dev/null || true

# Default backup directory
DEFAULT_BACKUP_DIR=".claude/backups"

# Create backup directory if it doesn't exist
ensure_backup_dir() {
    local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"

    if [[ ! -d "$backup_dir" ]]; then
        mkdir -p "$backup_dir"
        echo -e "${BLUE}Created backup directory: $backup_dir${NC}"
    fi

    echo "$backup_dir"
}

# Generate timestamp for backup naming
get_backup_timestamp() {
    date +"%Y%m%d-%H%M%S"
}

# Create a full backup of files before operation
create_backup_set() {
    local operation_name="$1"
    shift
    local files=("$@")
    local timestamp
    timestamp=$(get_backup_timestamp)
    local backup_dir
    backup_dir=$(ensure_backup_dir)
    local backup_set_dir="$backup_dir/${operation_name}-${timestamp}"

    if [[ ${#files[@]} -eq 0 ]]; then
        echo -e "${YELLOW}No files specified for backup${NC}"
        return 0
    fi

    mkdir -p "$backup_set_dir"

    echo -e "${BLUE}Creating backup set: $backup_set_dir${NC}"

    local backup_count=0
    local failed_count=0

    for file in "${files[@]}"; do
        if [[ -e "$file" ]]; then
            # Preserve directory structure
            local file_dir
            file_dir=$(dirname "$file")
            local backup_file_dir="$backup_set_dir/$file_dir"

            mkdir -p "$backup_file_dir"

            if cp -p "$file" "$backup_file_dir/" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Backed up: $file"
                ((backup_count++))
            else
                echo -e "${RED}✗${NC} Failed to backup: $file"
                ((failed_count++))
            fi
        else
            echo -e "${YELLOW}⚠${NC} File not found (skipping): $file"
        fi
    done

    # Create backup manifest
    create_backup_manifest "$backup_set_dir" "$operation_name" "${files[@]}"

    echo ""
    echo -e "${BLUE}Backup Summary:${NC}"
    echo -e "  Location: $backup_set_dir"
    echo -e "  Files backed up: $backup_count"
    echo -e "  Failed backups: $failed_count"

    if [[ $failed_count -gt 0 ]]; then
        return 1
    fi

    echo "$backup_set_dir"
    return 0
}

# Create backup manifest file
create_backup_manifest() {
    local backup_dir="$1"
    local operation="$2"
    shift 2
    local files=("$@")

    local manifest_file="$backup_dir/MANIFEST.txt"

    cat > "$manifest_file" <<EOF
Backup Manifest
===============
Operation: $operation
Created: $(date)
Backup Directory: $backup_dir

Files Backed Up:
EOF

    for file in "${files[@]}"; do
        if [[ -e "$backup_dir/$file" ]]; then
            local file_size
            file_size=$(get_file_info "$backup_dir/$file" text 2>/dev/null | grep "Size:" | awk '{print $2}' || echo "unknown")
            echo "  ✓ $file ($file_size)" >> "$manifest_file"
        else
            echo "  ✗ $file (missing)" >> "$manifest_file"
        fi
    done

    echo "" >> "$manifest_file"
    echo "Total files in backup: $(find "$backup_dir" -type f ! -name "MANIFEST.txt" | wc -l | xargs)" >> "$manifest_file"
    echo "Backup size: $(get_directory_size "$backup_dir" text 2>/dev/null | grep "Size:" | awk '{print $2}' || echo "unknown")" >> "$manifest_file"
}

# Backup entire project state
create_project_backup() {
    local project_dir="${1:-.}"
    local operation_name="${2:-project-backup}"
    local exclude_patterns="${3:-node_modules,.git,dist,build,.next,__pycache__,*.pyc,*.log}"

    local timestamp
    timestamp=$(get_backup_timestamp)
    local backup_dir
    backup_dir=$(ensure_backup_dir)
    local project_backup_dir="$backup_dir/${operation_name}-${timestamp}"

    echo -e "${BLUE}Creating full project backup: $project_backup_dir${NC}"

    # Create exclusion file
    local exclude_file
    exclude_file=$(mktemp)
    IFS=',' read -ra EXCLUDES <<< "$exclude_patterns"
    for exclude in "${EXCLUDES[@]}"; do
        echo "$exclude" >> "$exclude_file"
    done

    # Create backup using rsync if available, otherwise use cp
    if command -v rsync > /dev/null 2>&1; then
        if rsync -av --exclude-from="$exclude_file" "$project_dir/" "$project_backup_dir/"; then
            echo -e "${GREEN}✓ Project backup completed using rsync${NC}"
        else
            echo -e "${RED}✗ Project backup failed${NC}" >&2
            rm -f "$exclude_file"
            return 1
        fi
    else
        # Fallback to cp with find
        mkdir -p "$project_backup_dir"
        find "$project_dir" -type f | while read -r file; do
            # Check if file should be excluded
            local should_exclude=false
            for exclude in "${EXCLUDES[@]}"; do
                if [[ "$file" == *"$exclude"* ]]; then
                    should_exclude=true
                    break
                fi
            done

            if [[ "$should_exclude" == "false" ]]; then
                local relative_path
                relative_path=$(realpath --relative-to="$project_dir" "$file" 2>/dev/null || echo "$file")
                local backup_file="$project_backup_dir/$relative_path"
                local backup_file_dir
                backup_file_dir=$(dirname "$backup_file")

                mkdir -p "$backup_file_dir"
                cp -p "$file" "$backup_file"
            fi
        done
        echo -e "${GREEN}✓ Project backup completed using cp${NC}"
    fi

    rm -f "$exclude_file"

    # Create project manifest
    create_project_manifest "$project_backup_dir" "$operation_name" "$project_dir"

    echo -e "${BLUE}Project backup location: $project_backup_dir${NC}"
    echo "$project_backup_dir"
    return 0
}

# Create project backup manifest
create_project_manifest() {
    local backup_dir="$1"
    local operation="$2"
    local project_dir="$3"

    local manifest_file="$backup_dir/PROJECT_MANIFEST.txt"

    cat > "$manifest_file" <<EOF
Project Backup Manifest
======================
Operation: $operation
Created: $(date)
Original Project: $project_dir
Backup Directory: $backup_dir

Project Structure:
EOF

    # Add directory tree
    if command -v tree > /dev/null 2>&1; then
        tree -L 3 "$backup_dir" >> "$manifest_file" 2>/dev/null || echo "Directory tree not available" >> "$manifest_file"
    else
        find "$backup_dir" -type d | head -20 | sed 's/^/  /' >> "$manifest_file"
        echo "  ..." >> "$manifest_file"
    fi

    echo "" >> "$manifest_file"
    echo "Statistics:" >> "$manifest_file"
    echo "  Total files: $(find "$backup_dir" -type f | wc -l | xargs)" >> "$manifest_file"
    echo "  Total directories: $(find "$backup_dir" -type d | wc -l | xargs)" >> "$manifest_file"
    echo "  Backup size: $(get_directory_size "$backup_dir" text 2>/dev/null | grep "Size:" | awk '{print $2}' || echo "unknown")" >> "$manifest_file"

    # Add Git information if available
    if [[ -d "$project_dir/.git" ]]; then
        echo "" >> "$manifest_file"
        echo "Git Information:" >> "$manifest_file"
        echo "  Current branch: $(git -C "$project_dir" branch --show-current 2>/dev/null || echo "unknown")" >> "$manifest_file"
        echo "  Latest commit: $(git -C "$project_dir" rev-parse --short HEAD 2>/dev/null || echo "unknown")" >> "$manifest_file"
        echo "  Working directory clean: $(git -C "$project_dir" diff-index --quiet HEAD -- 2>/dev/null && echo "yes" || echo "no")" >> "$manifest_file"
    fi
}

# Restore from backup set
restore_backup_set() {
    local backup_set_dir="$1"
    local target_dir="${2:-.}"
    local confirm="${3:-true}"
    local dry_run="${4:-false}"

    if [[ ! -d "$backup_set_dir" ]]; then
        echo -e "${RED}✗ Backup set not found: $backup_set_dir${NC}" >&2
        return 1
    fi

    local manifest_file="$backup_set_dir/MANIFEST.txt"
    if [[ -f "$manifest_file" ]]; then
        echo -e "${BLUE}Backup Manifest:${NC}"
        head -20 "$manifest_file"
        echo ""
    fi

    if [[ "$confirm" == "true" ]]; then
        echo -e "${YELLOW}This will restore files from backup to: $target_dir${NC}"
        echo -e "This may overwrite existing files. Continue? (y/N): ${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Restore cancelled${NC}"
            return 1
        fi
    fi

    local restore_count=0
    local failed_count=0

    # Find all files in backup (excluding manifest)
    find "$backup_set_dir" -type f ! -name "MANIFEST.txt" ! -name "PROJECT_MANIFEST.txt" | while read -r backup_file; do
        # Calculate relative path
        local relative_path
        relative_path=$(realpath --relative-to="$backup_set_dir" "$backup_file" 2>/dev/null || echo "${backup_file#$backup_set_dir/}")
        local target_file="$target_dir/$relative_path"
        local target_file_dir
        target_file_dir=$(dirname "$target_file")

        if [[ "$dry_run" == "true" ]]; then
            echo -e "${BLUE}[DRY RUN]${NC} Would restore: $relative_path"
        else
            mkdir -p "$target_file_dir"

            if cp -p "$backup_file" "$target_file" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Restored: $relative_path"
                ((restore_count++))
            else
                echo -e "${RED}✗${NC} Failed to restore: $relative_path"
                ((failed_count++))
            fi
        fi
    done

    if [[ "$dry_run" != "true" ]]; then
        echo ""
        echo -e "${BLUE}Restore Summary:${NC}"
        echo -e "  Files restored: $restore_count"
        echo -e "  Failed restores: $failed_count"

        if [[ $failed_count -gt 0 ]]; then
            return 1
        fi
    fi

    return 0
}

# List available backups
list_backups() {
    local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"
    local operation_filter="${2:-}"

    if [[ ! -d "$backup_dir" ]]; then
        echo -e "${YELLOW}No backup directory found: $backup_dir${NC}"
        return 0
    fi

    echo -e "${BLUE}Available Backups in $backup_dir:${NC}"
    echo ""

    local backup_count=0

    find "$backup_dir" -maxdepth 1 -type d -name "*-[0-9]*" | sort -r | while read -r backup; do
        local backup_name
        backup_name=$(basename "$backup")

        # Apply operation filter if specified
        if [[ -n "$operation_filter" && "$backup_name" != *"$operation_filter"* ]]; then
            continue
        fi

        local manifest_file="$backup/MANIFEST.txt"
        local project_manifest_file="$backup/PROJECT_MANIFEST.txt"

        echo -e "${GREEN}$backup_name${NC}"

        if [[ -f "$manifest_file" ]]; then
            echo "  Type: File Set Backup"
            echo "  Files: $(grep -c "✓" "$manifest_file" 2>/dev/null || echo "unknown")"
        elif [[ -f "$project_manifest_file" ]]; then
            echo "  Type: Project Backup"
            echo "  Files: $(grep "Total files:" "$project_manifest_file" 2>/dev/null | awk '{print $3}' || echo "unknown")"
        else
            echo "  Type: Unknown"
        fi

        echo "  Size: $(get_directory_size "$backup" text 2>/dev/null | grep "Size:" | awk '{print $2}' || echo "unknown")"
        echo "  Location: $backup"
        echo ""

        ((backup_count++))
    done

    if [[ $backup_count -eq 0 ]]; then
        echo -e "${YELLOW}No backups found${NC}"
        if [[ -n "$operation_filter" ]]; then
            echo -e "  (with filter: $operation_filter)"
        fi
    else
        echo -e "${BLUE}Total backups: $backup_count${NC}"
    fi
}

# Clean up old backups
cleanup_old_backups() {
    local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"
    local keep_days="${2:-7}"
    local operation_filter="${3:-}"
    local dry_run="${4:-false}"

    if [[ ! -d "$backup_dir" ]]; then
        echo -e "${YELLOW}No backup directory found: $backup_dir${NC}"
        return 0
    fi

    echo -e "${BLUE}Cleaning up backups older than $keep_days days in: $backup_dir${NC}"

    local cleanup_count=0

    find "$backup_dir" -maxdepth 1 -type d -name "*-[0-9]*" -mtime "+$keep_days" | while read -r backup; do
        local backup_name
        backup_name=$(basename "$backup")

        # Apply operation filter if specified
        if [[ -n "$operation_filter" && "$backup_name" != *"$operation_filter"* ]]; then
            continue
        fi

        local backup_age_days
        backup_age_days=$(find "$backup" -maxdepth 0 -mtime "+$keep_days" -printf '%A@\n' 2>/dev/null | head -1)
        backup_age_days=${backup_age_days:-"unknown"}

        if [[ "$dry_run" == "true" ]]; then
            echo -e "${YELLOW}[DRY RUN]${NC} Would delete: $backup_name (age: ${backup_age_days} days)"
        else
            if rm -rf "$backup" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Deleted: $backup_name"
                ((cleanup_count++))
            else
                echo -e "${RED}✗${NC} Failed to delete: $backup_name"
            fi
        fi
    done

    if [[ "$dry_run" != "true" ]]; then
        echo -e "${BLUE}Cleanup completed. Removed $cleanup_count backup(s).${NC}"
    fi
}

# Create incremental backup (Git-based)
create_incremental_backup() {
    local operation_name="$1"
    local base_commit="${2:-HEAD~1}"
    local target_commit="${3:-HEAD}"

    if ! check_git_repo; then
        echo -e "${RED}✗ Not in a Git repository${NC}" >&2
        return 1
    fi

    local timestamp
    timestamp=$(get_backup_timestamp)
    local backup_dir
    backup_dir=$(ensure_backup_dir)
    local incremental_backup_dir="$backup_dir/incremental-${operation_name}-${timestamp}"

    echo -e "${BLUE}Creating incremental backup: $incremental_backup_dir${NC}"

    # Get list of changed files
    local changed_files
    changed_files=$(git diff --name-only "$base_commit" "$target_commit" || true)

    if [[ -z "$changed_files" ]]; then
        echo -e "${YELLOW}No changes found between $base_commit and $target_commit${NC}"
        return 0
    fi

    mkdir -p "$incremental_backup_dir"

    # Backup changed files
    local backup_count=0

    while IFS= read -r file; do
        if [[ -f "$file" ]]; then
            local file_dir
            file_dir=$(dirname "$file")
            local backup_file_dir="$incremental_backup_dir/$file_dir"

            mkdir -p "$backup_file_dir"

            if cp -p "$file" "$backup_file_dir/" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} Backed up: $file"
                ((backup_count++))
            else
                echo -e "${RED}✗${NC} Failed to backup: $file"
            fi
        fi
    done <<< "$changed_files"

    # Create incremental manifest
    create_incremental_manifest "$incremental_backup_dir" "$operation_name" "$base_commit" "$target_commit"

    echo -e "${BLUE}Incremental backup completed: $backup_count files${NC}"
    echo "$incremental_backup_dir"
    return 0
}

# Create incremental backup manifest
create_incremental_manifest() {
    local backup_dir="$1"
    local operation="$2"
    local base_commit="$3"
    local target_commit="$4"

    local manifest_file="$backup_dir/INCREMENTAL_MANIFEST.txt"

    cat > "$manifest_file" <<EOF
Incremental Backup Manifest
===========================
Operation: $operation
Created: $(date)
Base Commit: $base_commit
Target Commit: $target_commit
Backup Directory: $backup_dir

Git Information:
  Base: $(git rev-parse --short "$base_commit" 2>/dev/null || echo "unknown") - $(git log --format="%s" -n 1 "$base_commit" 2>/dev/null || echo "unknown")
  Target: $(git rev-parse --short "$target_commit" 2>/dev/null || echo "unknown") - $(git log --format="%s" -n 1 "$target_commit" 2>/dev/null || echo "unknown")

Changed Files:
EOF

    git diff --name-status "$base_commit" "$target_commit" 2>/dev/null | while read -r status file; do
        case "$status" in
            "A") echo "  + $file (added)" ;;
            "D") echo "  - $file (deleted)" ;;
            "M") echo "  ~ $file (modified)" ;;
            "R"*) echo "  → $file (renamed)" ;;
            *) echo "  ? $file ($status)" ;;
        esac
    done >> "$manifest_file"

    echo "" >> "$manifest_file"
    echo "Backup Statistics:" >> "$manifest_file"
    echo "  Total files backed up: $(find "$backup_dir" -type f ! -name "*_MANIFEST.txt" | wc -l | xargs)" >> "$manifest_file"
    echo "  Backup size: $(get_directory_size "$backup_dir" text 2>/dev/null | grep "Size:" | awk '{print $2}' || echo "unknown")" >> "$manifest_file"
}

# Export functions for sourcing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly, not sourced
    echo "Backup utilities loaded. Available functions:"
    echo "  ensure_backup_dir, get_backup_timestamp, create_backup_set"
    echo "  create_project_backup, restore_backup_set, list_backups"
    echo "  cleanup_old_backups, create_incremental_backup"
fi
