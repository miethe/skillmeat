---
title: claudectl Complete User Guide
description: Comprehensive reference guide for the claudectl CLI - all commands, options, examples, error handling, and troubleshooting
audience: users
tags: [cli, reference, guide, claudectl, skillmeat]
created: 2025-12-24
updated: 2025-12-24
category: guide
status: published
related_documents:
  - claudectl-quickstart.md
  - /docs/user/cli/commands.md
  - PRD-003-claudectl-alias.md
---

# claudectl Complete User Guide

Complete reference for the claudectl command-line interface. claudectl is a streamlined wrapper around skillmeat that provides sensible defaults, auto-detection, and minimal typing for common artifact management operations.

## Table of Contents

1. [Installation](#installation)
2. [Quick Reference](#quick-reference)
3. [Core Commands](#core-commands)
4. [Advanced Commands](#advanced-commands)
5. [Output Formats](#output-formats)
6. [Exit Codes](#exit-codes)
7. [Error Handling](#error-handling)
8. [Scripting & Automation](#scripting--automation)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

---

## Installation

### Quick Install

```bash
# Install claudectl wrapper and shell completion
skillmeat alias install

# Verify installation
claudectl --help
```

For detailed installation, see [claudectl Quick Start Guide](claudectl-quickstart.md#installation).

### Supported Shells

- bash
- zsh
- fish

### Uninstall

```bash
skillmeat alias uninstall
```

---

## Quick Reference

### Most-Used Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `search` | Find artifacts | `claudectl search pdf` |
| `add` | Add to collection | `claudectl add pdf-tools` |
| `list` | Show collection | `claudectl list` |
| `deploy` | Deploy to project | `claudectl deploy pdf-tools` |
| `status` | Show deployments | `claudectl status` |
| `remove` | Remove from collection | `claudectl remove pdf-tools` |
| `undeploy` | Remove from project | `claudectl undeploy pdf-tools` |
| `sync` | Update artifacts | `claudectl sync` |
| `config` | View/set settings | `claudectl config list` |
| `collection` | Manage collections | `claudectl collection list` |
| `show` | Show artifact details | `claudectl show pdf-tools` |
| `bundle` | Create/import bundles | `claudectl bundle create backup.tar.gz` |
| `verify` | Verify artifact | `claudectl verify ./my-skill skill` |
| `diff` | Compare artifacts | `claudectl diff artifact1 artifact2` |

### Smart Defaults

claudectl applies automatic defaults:

- **Type Detection**: `pdf` → skill, `cli` → command, `agent` → agent
- **Collection**: Uses active collection (configurable)
- **Project**: Current directory (configurable)
- **Format**: Auto-table (TTY), auto-JSON (pipes/scripts)

---

## Core Commands

### search

Search for artifacts by name, description, or type.

**Syntax:**

```bash
claudectl search <QUERY> [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--type` | `-t` | Filter by type: `skill`, `command`, `agent` |
| `--limit` | `-l` | Limit results (default: 10) |
| `--rating` | `-r` | Filter by minimum rating (1-5) |
| `--collection` | `-c` | Search in specific collection |
| `--format` | | `table` (default) or `json` |

**Examples:**

```bash
# Basic search
claudectl search pdf

# Filter by type
claudectl search auth --type skill

# Show top 5 results
claudectl search database --limit 5

# Only highly-rated results
claudectl search testing --rating 4.0

# JSON output for scripting
claudectl search react --format json
```

**Output Example:**

```
Name              Type     Origin                  Rating  Downloads
pdf-tools         skill    anthropics/skills       4.8     1,200
pdf-expert        command  community/data-tools    4.2     540
advanced-pdf-ml   skill    research/ml-tools       5.0     203
```

**Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `No results found` | Query doesn't match any artifacts | Try broader search terms, use `--limit 100` |
| `Collection not found` | Specified collection doesn't exist | Use `claudectl collection list` to see available |
| `Invalid rating value` | Rating not 1-5 | Use number between 1 and 5 |

---

### add

Add artifacts to your collection from GitHub or local path.

**Syntax:**

```bash
claudectl add <SPEC> [OPTIONS]
```

**Arguments:**

- `SPEC`: GitHub path (`user/repo/path[@version]`) or local path (`./my-skill`)

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--type` | `-t` | Artifact type: `skill`, `command`, `agent` (auto-detected if omitted) |
| `--name` | `-n` | Override artifact name |
| `--collection` | `-c` | Target collection (default: active) |
| `--force` | `-f` | Overwrite if already exists |
| `--format` | | `table` or `json` |

**Examples:**

```bash
# Add from GitHub (type auto-detected)
claudectl add anthropics/skills/pdf-tools

# Add command (detected from -cli suffix)
claudectl add user/repo/my-cli

# Add with explicit type
claudectl add my-artifact --type skill

# Add from local path
claudectl add ./my-local-skill

# Override name
claudectl add pdf-tools --name pdf

# Add to specific collection
claudectl add pdf-tools --collection work

# Overwrite existing
claudectl add pdf-tools --force

# JSON output
claudectl add pdf-tools --format json
```

**Output Example:**

```json
{
  "status": "success",
  "artifact": "anthropics/skills/pdf-tools",
  "name": "pdf-tools",
  "type": "skill",
  "collection": "default",
  "version": "1.2.0",
  "location": "/home/user/.skillmeat/collections/default/skills/pdf-tools"
}
```

**Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Artifact already exists` | Name conflict | Use `--name` to rename or `--force` to overwrite |
| `GitHub rate limit exceeded` | Too many requests | Set `GITHUB_TOKEN` or wait 1 hour |
| `Invalid artifact structure` | Missing required files | Verify artifact has `SKILL.md`, `COMMAND.md`, or `AGENT.md` |
| `Permission denied` | Can't write to collection | Check collection directory permissions |

---

### list

List artifacts in your collection.

**Syntax:**

```bash
claudectl list [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--type` | `-t` | Filter by type: `skill`, `command`, `agent` |
| `--collection` | `-c` | Show specific collection (default: active) |
| `--tags` | | Show tags for each artifact |
| `--deployed` | `-d` | Show only deployed artifacts |
| `--no-cache` | | Force fresh read from filesystem |
| `--format` | | `table` (default) or `json` |

**Examples:**

```bash
# List all artifacts
claudectl list

# List only skills
claudectl list --type skill

# List deployed artifacts
claudectl list --deployed

# Show tags
claudectl list --tags

# List from specific collection
claudectl list --collection work

# JSON output
claudectl list --format json

# Count artifacts
claudectl list --format json | jq '.artifacts | length'
```

**Output Example:**

```
Name              Type     Version  Collection  Deployed  Updated
pdf-tools         skill    1.2.0    default     Yes       2025-12-20
canvas-design     skill    2.0.1    default     No        2025-12-18
react-tester      command  0.5.0    default     Yes       2025-12-15
```

**Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Collection not found` | Collection doesn't exist | Use `claudectl collection list` |
| `No artifacts found` | Collection is empty | Use `claudectl add` to add artifacts |
| `Cache is stale` | Filesystem changed externally | Use `--no-cache` flag |

---

### deploy

Deploy artifacts to your project's `.claude/` directory.

**Syntax:**

```bash
claudectl deploy <NAME>... [OPTIONS]
```

**Arguments:**

- `NAME`: One or more artifact names (space-separated)

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--project` | `-p` | Target project (default: current directory) |
| `--collection` | `-c` | Source collection (default: active) |
| `--force` | `-f` | Redeploy even if already deployed |
| `--format` | | `table` or `json` |

**Examples:**

```bash
# Deploy single artifact to current project
claudectl deploy pdf-tools

# Deploy multiple artifacts
claudectl deploy pdf-tools canvas react-cli

# Deploy to specific project
claudectl deploy pdf-tools --project /path/to/my-project

# Force redeploy (update files)
claudectl deploy pdf-tools --force

# Deploy all artifacts at once
claudectl list --format json | jq -r '.artifacts[].name' | xargs claudectl deploy

# JSON output
claudectl deploy pdf-tools --format json
```

**Output Example:**

```json
{
  "status": "success",
  "deployed": [
    {
      "artifact": "pdf-tools",
      "type": "skill",
      "location": "/home/user/project/.claude/skills/pdf-tools",
      "files": 12,
      "size_kb": 45
    }
  ],
  "project": "/home/user/project"
}
```

**Pre-Deployment Plan:**

Before deploying, claudectl shows what will happen:

```
Will deploy to: /home/user/project/.claude/
  pdf-tools (skill) -> .claude/skills/pdf-tools/ [12 files, 45KB]
  canvas (skill) -> .claude/skills/canvas/ [8 files, 23KB]

Continue? (y/n)
```

**Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Artifact not found` | Name doesn't exist in collection | Use `claudectl list` to find correct name |
| `Project not found` | Directory doesn't exist | Create directory or use `--project` |
| `Already deployed` | Artifact already in this project | Use `--force` to redeploy |
| `Permission denied` | Can't write to project | Check `.claude/` directory permissions |

---

### status

Show what artifacts are deployed in your project.

**Syntax:**

```bash
claudectl status [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--project` | `-p` | Target project (default: current directory) |
| `--detail` | `-d` | Show file counts and modification times |
| `--format` | | `table` (default) or `json` |

**Examples:**

```bash
# Show deployment status for current directory
claudectl status

# Show with detailed info
claudectl status --detail

# Check status of specific project
claudectl status --project /path/to/project

# JSON output
claudectl status --format json

# Check if specific artifact is deployed
claudectl status --format json | jq '.deployed | map(.name) | contains(["pdf-tools"])'
```

**Output Example:**

```
Deployment Status: /home/user/project/.claude/

Artifact         Type     Version  Location              Files   Modified
pdf-tools        skill    1.2.0    .claude/skills/pdf    12      2025-12-20
canvas           skill    2.0.1    .claude/skills/canvas 8       2025-12-15
react-cli        command  0.5.0    .claude/commands      3       2025-12-10

Total: 3 artifacts (23 files)
```

**Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `.claude/ not found` | No artifacts deployed | Use `claudectl deploy` to deploy |
| `Project not found` | Directory doesn't exist | Check `--project` path |

---

### remove

Remove artifacts from your collection.

**Syntax:**

```bash
claudectl remove <NAME>... [OPTIONS]
```

**Arguments:**

- `NAME`: One or more artifact names (space-separated)

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--collection` | `-c` | Target collection (default: active) |
| `--force` | `-f` | Skip confirmation prompt |
| `--format` | | `table` or `json` |

**Examples:**

```bash
# Remove artifact (asks for confirmation)
claudectl remove old-skill

# Remove multiple artifacts
claudectl remove old-skill outdated-command

# Remove without confirmation
claudectl remove old-skill --force

# Remove from specific collection
claudectl remove old-skill --collection work

# JSON output
claudectl remove old-skill --format json
```

**Output Example:**

```
Removed artifact(s):
  old-skill (skill)
  outdated-command (command)

Collection 'default' now has 8 artifacts
```

**Error Handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Artifact not found` | Name doesn't exist | Use `claudectl list` to find |
| `Still deployed` | Artifact deployed to projects | Use `claudectl undeploy` first or use `--force` |
| `Permission denied` | Can't delete from collection | Check collection directory permissions |

---

### undeploy

Remove deployed artifacts from your project.

**Syntax:**

```bash
claudectl undeploy <NAME>... [OPTIONS]
```

**Arguments:**

- `NAME`: One or more artifact names (space-separated)

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--project` | `-p` | Target project (default: current directory) |
| `--force` | `-f` | Skip confirmation prompt |
| `--format` | | `table` or `json` |

**Examples:**

```bash
# Undeploy from current project
claudectl undeploy pdf-tools

# Undeploy multiple
claudectl undeploy pdf-tools canvas

# Undeploy from specific project
claudectl undeploy pdf-tools --project /path/to/project

# Skip confirmation
claudectl undeploy pdf-tools --force

# JSON output
claudectl undeploy pdf-tools --format json
```

**Output Example:**

```
Undeployed from /home/user/project/.claude/:
  pdf-tools (skill)
  canvas (skill)

Remaining: 1 artifact (3 files)
```

**Note:** `undeploy` only removes from `.claude/` directory. Use `remove` to delete from collection entirely.

---

### sync

Update artifacts in your collection from upstream sources.

**Syntax:**

```bash
claudectl sync [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--check-only` | | Check for updates without applying |
| `--artifact` | `-a` | Update specific artifact only |
| `--collection` | `-c` | Target collection (default: active) |
| `--strategy` | `-s` | Update strategy: `latest`, `minor`, `patch` |
| `--force` | `-f` | Skip confirmation |
| `--format` | | `table` or `json` |

**Examples:**

```bash
# Check for updates
claudectl sync --check-only

# Check for updates to specific artifact
claudectl sync --check-only --artifact pdf-tools

# Apply all updates
claudectl sync

# Update specific artifact
claudectl sync --artifact pdf-tools

# Update to latest major version
claudectl sync --strategy latest

# Update only patch versions
claudectl sync --strategy patch

# Skip confirmation
claudectl sync --force

# JSON output
claudectl sync --format json
```

**Output Example:**

```
Updates available:
  pdf-tools    1.2.0 -> 1.3.0 (minor)
  canvas       2.0.1 -> 2.1.0 (minor)
  react-cli    0.5.0 -> 0.5.1 (patch)

Apply updates? (y/n)
```

---

## Advanced Commands

### show

Display detailed information about an artifact.

**Syntax:**

```bash
claudectl show <NAME> [OPTIONS]
```

**Arguments:**

- `NAME`: Artifact name

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--collection` | `-c` | Source collection (default: active) |
| `--scores` | `-s` | Show confidence scores |
| `--format` | | `table` or `json` |

**Examples:**

```bash
# Show artifact details
claudectl show pdf-tools

# Include confidence scores
claudectl show pdf-tools --scores

# JSON output
claudectl show pdf-tools --format json
```

**Output Example:**

```
Name: pdf-tools
Type: skill
Origin: anthropics/skills/pdf-tools
Version: 1.2.0
Updated: 2025-12-20

Description:
  Extract text, metadata, and pages from PDF files with support for...

Size: 45 KB
Files: 12
Rating: 4.8/5.0 (1,200 downloads)

Deployed to: 2 projects
  /home/user/project1/.claude/skills/pdf-tools
  /home/user/project2/.claude/skills/pdf-tools
```

---

### collection

Manage multiple collections.

**Syntax:**

```bash
claudectl collection <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### collection list

```bash
claudectl collection list

# Output:
# Collections:
#   * default  (8 artifacts, active)
#     work     (5 artifacts)
#     personal (12 artifacts)
```

#### collection use

```bash
claudectl collection use <NAME>

# Sets the active collection for all subsequent commands
claudectl collection use work
claudectl add pdf-tools  # Added to 'work' collection
```

#### collection create

```bash
claudectl collection create <NAME>

# Creates a new collection
claudectl collection create experimental
```

**Examples:**

```bash
# View all collections
claudectl collection list

# Switch to work collection
claudectl collection use work

# Verify switch
claudectl list  # Shows artifacts from 'work'

# Create new collection
claudectl collection create temporary

# Switch to it
claudectl collection use temporary
```

---

### config

View and configure settings.

**Syntax:**

```bash
claudectl config [SUBCOMMAND] [OPTIONS]
```

**Subcommands:**

#### config list

```bash
claudectl config list

# Shows all current settings
```

#### config get

```bash
claudectl config get <KEY>

# Get specific setting
claudectl config get default-collection
# Output: default
```

#### config set

```bash
claudectl config set <KEY> <VALUE>

# Common settings:
claudectl config set default-collection work
claudectl config set github-token ghp_your_token
claudectl config set default-project /path/to/project
```

**Examples:**

```bash
# View all config
claudectl config list

# Set GitHub token for private repos
claudectl config set github-token ghp_1234567890abcdef

# Set default collection
claudectl config set default-collection work

# Set default project path
claudectl config set default-project ~/my-project

# Verify settings
claudectl config list
```

---

### bundle

Create and import artifact bundles for sharing.

**Syntax:**

```bash
claudectl bundle <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### bundle create

```bash
claudectl bundle create <FILE.tar.gz> [OPTIONS]

# Create bundle from all deployed artifacts in current project
claudectl bundle create my-setup.tar.gz

# Create bundle from specific artifacts
claudectl bundle create my-setup.tar.gz --artifacts pdf-tools canvas

# Include collection metadata
claudectl bundle create my-setup.tar.gz --include-metadata
```

#### bundle inspect

```bash
claudectl bundle inspect <FILE.tar.gz>

# Show what's in a bundle
claudectl bundle inspect my-setup.tar.gz

# Output:
# Bundle Contents:
#   pdf-tools (skill) - 45 KB
#   canvas (skill) - 23 KB
#   react-cli (command) - 12 KB
```

#### bundle import

```bash
claudectl bundle import <FILE.tar.gz> [OPTIONS]

# Import bundle to current collection
claudectl bundle import my-setup.tar.gz

# Import to specific collection
claudectl bundle import my-setup.tar.gz --collection work

# Import and deploy to project
claudectl bundle import my-setup.tar.gz --deploy
```

**Examples:**

```bash
# Create bundle from current deployments
claudectl bundle create backup-$(date +%Y%m%d).tar.gz

# List bundle contents
claudectl bundle inspect backup-20251224.tar.gz

# Import on another machine
claudectl bundle import backup-20251224.tar.gz --collection restored

# Share bundle
# (tar.gz file can be committed to repo or shared)
```

---

### verify

Verify artifact structure and validity.

**Syntax:**

```bash
claudectl verify <PATH> [--type TYPE]
```

**Arguments:**

- `PATH`: Path to artifact directory or file

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--type` | `-t` | Expected type: `skill`, `command`, `agent` |
| `--format` | | `table` or `json` |

**Examples:**

```bash
# Verify local skill
claudectl verify ./my-skill --type skill

# Verify command
claudectl verify ./my-command --type command

# Verify any type (auto-detect)
claudectl verify ./my-artifact

# JSON output
claudectl verify ./my-artifact --format json
```

**Output Example:**

```
Verification Report: ./my-skill

Status: VALID
Type: skill
Issues: 0

Checks:
  [✓] Required files present (SKILL.md)
  [✓] Valid markdown format
  [✓] Metadata section valid
  [✓] No broken links
  [✓] File permissions correct
```

---

### diff

Compare two artifacts and detect differences.

**Syntax:**

```bash
claudectl diff <ARTIFACT1> <ARTIFACT2> [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--stat` | | Show only file statistics |
| `--format` | | `table`, `json`, or `unified` |

**Examples:**

```bash
# Compare two versions of same artifact
claudectl diff pdf-tools pdf-tools-backup

# Show only changed file count
claudectl diff artifact1 artifact2 --stat

# Get detailed diff
claudectl diff artifact1 artifact2 --format unified
```

---

## Output Formats

### Auto-Detection

claudectl automatically selects output format:

- **TTY (Terminal)**: Table format with colors
- **Pipes/Redirection**: JSON format (parseable)
- **Override**: Use `--format` flag

```bash
# Auto table (terminal)
claudectl list

# Auto JSON (piped)
claudectl list | jq '.'

# Force JSON in terminal
claudectl list --format json

# Force table in pipe (unusual but possible)
claudectl list --format table | less
```

### Table Format

Human-readable colored output:

```
Name              Type     Version  Collection  Deployed
pdf-tools         skill    1.2.0    default     Yes
canvas            skill    2.0.1    default     No
react-cli         command  0.5.0    default     Yes
```

### JSON Format

Machine-parseable JSON:

```json
{
  "status": "success",
  "artifacts": [
    {
      "name": "pdf-tools",
      "type": "skill",
      "version": "1.2.0",
      "collection": "default",
      "deployed": true
    }
  ],
  "total": 3
}
```

---

## Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | Command completed without errors |
| 1 | General error | Unexpected error during operation |
| 2 | Usage error | Invalid arguments or options |
| 3 | Not found | Artifact, collection, or project not found |
| 4 | Conflict | Resource already exists |
| 5 | Permission denied | Insufficient permissions |
| 65 | Input error | Invalid input format |
| 70 | Internal error | Software internal error |

**Scripting with exit codes:**

```bash
#!/bin/bash
if claudectl deploy my-skill; then
    echo "Deployment succeeded"
else
    echo "Deployment failed with exit code $?"
    exit 1
fi
```

---

## Error Handling

### Common Errors and Solutions

#### GitHub-Related Errors

**Error:** `GitHub API rate limit exceeded (60 req/hour)`

**Solution:**
```bash
# Set GitHub token to increase limit (5000 req/hour)
claudectl config set github-token ghp_your_token

# Or use environment variable
export GITHUB_TOKEN=ghp_your_token
claudectl add anthropics/skills/pdf
```

**Error:** `Repository not found (404)`

**Solution:**
```bash
# Verify GitHub path format
claudectl search pdf  # Find exact name

# Use correct format
claudectl add anthropics/skills/pdf-tools
```

#### Collection Errors

**Error:** `Collection 'default' not found`

**Solution:**
```bash
# List available collections
claudectl collection list

# Create collection if needed
claudectl collection create default

# Initialize if new to SkillMeat
skillmeat init
```

**Error:** `Artifact 'pdf' is ambiguous (multiple matches)`

**Solution:**
```bash
# Search to find exact name
claudectl search pdf

# Use exact name
claudectl add pdf-tools  # Instead of just 'pdf'

# Or specify type
claudectl add pdf --type skill
```

#### Permission Errors

**Error:** `Permission denied: /home/user/.skillmeat/collections`

**Solution:**
```bash
# Check directory permissions
ls -la ~/.skillmeat/

# Fix permissions if needed
chmod u+rwx ~/.skillmeat/collections

# Or reinstall
skillmeat alias uninstall
skillmeat alias install
```

**Error:** `Permission denied: .claude/`

**Solution:**
```bash
# Check project directory permissions
ls -la .claude/

# Create if missing
mkdir -p .claude

# Fix permissions
chmod u+rwx .claude

# Retry deployment
claudectl deploy my-skill
```

#### Type Detection Errors

**Error:** `Cannot auto-detect type for 'my-artifact'`

**Solution:**
```bash
# Specify type explicitly
claudectl add my-artifact --type skill

# Or rename with -cli, -agent, etc. suffix
claudectl add my-skill  # Auto-detected as skill
```

### Error Messages Format

claudectl provides structured error messages:

```
ERROR: Failed to add artifact
  Artifact: anthropics/skills/pdf
  Reason: Repository not found (404)
  GitHub Path: https://github.com/anthropics/skills/tree/main/pdf
  Suggestion: Use 'claudectl search pdf' to find available artifacts
```

---

## Scripting & Automation

### JSON Output for Scripts

All commands support `--format json` for automation:

```bash
# Get list of all skills as JSON
claudectl list --type skill --format json > artifacts.json

# Parse with jq
jq '.artifacts[] | select(.rating > 4.0) | .name' artifacts.json
```

### Deployment Automation

**Deploy all artifacts in a collection:**

```bash
#!/bin/bash
claudectl list --format json | \
  jq -r '.artifacts[].name' | \
  xargs claudectl deploy
```

**Deploy to multiple projects:**

```bash
#!/bin/bash
for project in ~/projects/*; do
  claudectl deploy pdf-tools canvas --project "$project"
done
```

**Conditional deployment:**

```bash
#!/bin/bash
# Deploy only if not already deployed
if ! claudectl status --format json | jq -e '.deployed | map(.name) | contains(["pdf"])' > /dev/null; then
  claudectl deploy pdf-tools
fi
```

### Backup and Restore

**Automated backup:**

```bash
#!/bin/bash
BACKUP_DIR=~/skillmeat-backups
mkdir -p "$BACKUP_DIR"

for collection in $(claudectl collection list --format json | jq -r '.collections[].name'); do
  claudectl bundle create "$BACKUP_DIR/$collection-$(date +%Y%m%d-%H%M%S).tar.gz" \
    --collection "$collection"
done

echo "Backups created in $BACKUP_DIR"
```

**Restore from backup:**

```bash
#!/bin/bash
# Restore to new collection
claudectl collection create restored
claudectl bundle import backup-20251224.tar.gz --collection restored
claudectl collection use restored
```

### CI/CD Integration

**GitHub Actions example:**

```yaml
name: Deploy Artifacts

on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install SkillMeat
        run: pip install skillmeat

      - name: Setup claudectl
        run: skillmeat alias install --shells bash

      - name: Deploy artifacts
        run: |
          claudectl add anthropics/skills/pdf-tools
          claudectl deploy pdf-tools --project .
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Configuration

### Configuration Files

```
~/.skillmeat/config.toml    # Global configuration
~/.skillmeat/collections/   # All collections
```

### Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `default-collection` | string | `default` | Active collection |
| `default-project` | path | `.` | Default deployment target |
| `github-token` | string | (empty) | GitHub API token |
| `auto-update` | bool | `true` | Check for updates on startup |
| `cache-dir` | path | `~/.skillmeat/cache` | Cache location |
| `output-format` | string | `auto` | Default output format |

### Setting Configuration

```bash
# View all settings
claudectl config list

# View specific setting
claudectl config get default-collection

# Change default collection
claudectl config set default-collection work

# Set GitHub token
claudectl config set github-token ghp_1234567890

# Unset setting (return to default)
claudectl config unset default-project
```

### Environment Variables

Override configuration with environment variables:

```bash
# Force JSON output
export CLAUDECTL_JSON=1

# Set active collection
export CLAUDECTL_COLLECTION=work

# Set GitHub token
export GITHUB_TOKEN=ghp_your_token

# Run command
claudectl list  # Uses 'work' collection, outputs JSON
```

---

## Troubleshooting

### General Issues

#### "claudectl: command not found"

**Cause:** claudectl is not in PATH

**Solution:**
```bash
# Check if installed
ls ~/.local/bin/claudectl

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Or use full path
~/.local/bin/claudectl list

# Make permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Tab completion not working

**Cause:** Shell completion not sourced

**Solution:**
```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc

# For fish
source ~/.config/fish/conf.d/claudectl.fish

# Or reinstall
skillmeat alias uninstall
skillmeat alias install
```

#### Permission denied errors

**Cause:** Insufficient permissions on collection or project

**Solution:**
```bash
# Check permissions
ls -la ~/.skillmeat/
ls -la .claude/

# Fix collection permissions
chmod -R u+rwx ~/.skillmeat/

# Create .claude if missing
mkdir -p .claude
chmod u+rwx .claude

# Or reinstall as your user
skillmeat alias uninstall
skillmeat alias install
```

### Artifact Issues

#### "Artifact not found"

**Cause:** Artifact name doesn't exist

**Solution:**
```bash
# Search for similar names
claudectl search pdf

# Use exact name from search
claudectl add pdf-tools

# Check what's installed
claudectl list
```

#### "Already exists" when adding

**Cause:** Artifact already in collection

**Solution:**
```bash
# Use --force to overwrite
claudectl add pdf-tools --force

# Or rename
claudectl add pdf-tools --name pdf-v2

# Or use different collection
claudectl add pdf-tools --collection work
```

#### Artifact won't deploy

**Cause:** Artifact not found or permission issues

**Solution:**
```bash
# Verify artifact exists in collection
claudectl list | grep pdf-tools

# Check project exists
ls -la .claude/ 2>/dev/null || mkdir -p .claude

# Deploy with details
claudectl deploy pdf-tools

# If still fails, use full path
claudectl deploy pdf-tools --project /absolute/path/to/project
```

### Deployment Issues

#### Deployed files seem old

**Cause:** Cached version being used

**Solution:**
```bash
# Force redeploy
claudectl undeploy pdf-tools
claudectl deploy pdf-tools

# Or use --force
claudectl deploy pdf-tools --force

# Check what's there
claudectl status --detail
```

#### .claude directory corrupted

**Cause:** External modification or partial deployment

**Solution:**
```bash
# Clean and redeploy
rm -rf .claude/

# Redeploy all artifacts
claudectl list --format json | \
  jq -r '.artifacts[].name' | \
  xargs claudectl deploy
```

### Performance Issues

#### Slow search or list

**Cause:** Stale cache or network delay

**Solution:**
```bash
# Clear cache
rm -rf ~/.skillmeat/cache/

# Bypass cache
claudectl list --no-cache

# Set GitHub token to avoid rate limiting
claudectl config set github-token ghp_your_token
```

#### Slow deployment

**Cause:** Large artifacts or slow disk

**Solution:**
```bash
# Deploy to faster disk
claudectl deploy pdf-tools --project /mnt/ssd/project

# Deploy one at a time instead of multiple
claudectl deploy pdf-tools
claudectl deploy canvas
```

### Getting Help

```bash
# View all commands
claudectl --help

# View command-specific help
claudectl deploy --help

# Search documentation
# Check docs/claudectl-guide.md (this file)

# Verbose output for debugging
CLAUDECTL_DEBUG=1 claudectl list
```

---

## Quick Command Reference

### Most Common Tasks

**Find and deploy quickly:**
```bash
claudectl search pdf
claudectl add pdf-tools
claudectl deploy pdf-tools
claudectl status
```

**Manage collections:**
```bash
claudectl collection list
claudectl collection use work
claudectl list
```

**Keep artifacts updated:**
```bash
claudectl sync --check-only
claudectl sync
```

**Create backup:**
```bash
claudectl bundle create backup-$(date +%Y%m%d).tar.gz
```

**Share setup:**
```bash
# Create bundle
claudectl bundle create my-setup.tar.gz

# On another machine
claudectl bundle import my-setup.tar.gz
claudectl deploy pdf-tools canvas
```

---

## Advanced Tips

### Alias Shortcuts

Create bash aliases for faster typing:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias cs='claudectl search'
alias ca='claudectl add'
alias cl='claudectl list'
alias cd='claudectl deploy'
alias cstat='claudectl status'
alias csync='claudectl sync'

# Reload shell
source ~/.bashrc
```

### One-Liner Patterns

**Deploy many artifacts at once:**
```bash
claudectl add pdf-tools canvas react-cli && claudectl deploy pdf-tools canvas react-cli
```

**Backup to cloud:**
```bash
claudectl bundle create backup.tar.gz && gsutil cp backup.tar.gz gs://my-bucket/
```

**Find and deploy highest-rated:**
```bash
claudectl search skill --format json | jq -r '.artifacts | sort_by(.rating) | reverse | .[0].name' | xargs claudectl deploy
```

---

## See Also

- [claudectl Quick Start](claudectl-quickstart.md) - Installation and first steps
- [SkillMeat Commands Reference](../user/cli/commands.md) - Full skillmeat CLI reference
- [PRD-003: claudectl Alias](../../.claude/docs/prd/PRD-003-claudectl-alias.md) - Feature specification

---

## Support

- **Issue Tracker:** GitHub Issues in SkillMeat repository
- **Documentation:** See `/docs/` directory
- **Examples:** See `/docs/user/examples.md`
