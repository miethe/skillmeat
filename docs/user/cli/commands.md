# SkillMeat Command Reference

Complete reference for all SkillMeat CLI commands.

## Table of Contents

- [SkillMeat Command Reference](#skillmeat-command-reference)
  - [Table of Contents](#table-of-contents)
  - [Core Commands](#core-commands)
    - [init](#init)
    - [list](#list)
    - [show](#show)
    - [remove](#remove)
  - [Adding Artifacts](#adding-artifacts)
    - [add skill](#add-skill)
    - [add command](#add-command)
    - [add agent](#add-agent)
  - [Deployment](#deployment)
    - [deploy](#deploy)
    - [undeploy](#undeploy)
  - [Updates \& Status](#updates--status)
    - [status](#status)
    - [update](#update)
  - [Versioning](#versioning)
    - [snapshot](#snapshot)
    - [history](#history)
    - [rollback](#rollback)
  - [Collection Management](#collection-management)
    - [collection create](#collection-create)
    - [collection list](#collection-list)
    - [collection use](#collection-use)
  - [Configuration](#configuration)
    - [config list](#config-list)
    - [config get](#config-get)
    - [config set](#config-set)
  - [Cache Management](#cache-management)
    - [cache status](#cache-status)
    - [cache refresh](#cache-refresh)
    - [cache clear](#cache-clear)
    - [cache config](#cache-config)
  - [Scoring and Matching](#scoring-and-matching)
    - [match](#match)
    - [rate](#rate)
    - [scores import](#scores-import)
    - [scores refresh](#scores-refresh)
    - [scores show](#scores-show)
    - [scores stats](#scores-stats)
    - [scores confirm](#scores-confirm)
  - [Phase 2: Diff Commands](#phase-2-diff-commands)
    - [diff files](#diff-files)
    - [diff dirs](#diff-dirs)
    - [diff three-way](#diff-three-way)
    - [diff artifact](#diff-artifact)
  - [Phase 2: Search Commands](#phase-2-search-commands)
    - [search](#search)
    - [find-duplicates](#find-duplicates)
  - [Phase 2: Sync Commands](#phase-2-sync-commands)
    - [sync check](#sync-check)
    - [sync pull](#sync-pull)
    - [sync preview](#sync-preview)
  - [Phase 2: Analytics Commands](#phase-2-analytics-commands)
    - [analytics usage](#analytics-usage)
    - [analytics top](#analytics-top)
    - [analytics cleanup](#analytics-cleanup)
    - [analytics trends](#analytics-trends)
    - [analytics export](#analytics-export)
    - [analytics stats](#analytics-stats)
    - [analytics clear](#analytics-clear)
  - [Utilities](#utilities)
    - [verify](#verify)
  - [Exit Codes](#exit-codes)
  - [Global Options](#global-options)
  - [Environment Variables](#environment-variables)
  - [File Locations](#file-locations)
  - [Version Specifications](#version-specifications)
  - [Web Interface](#web-interface)
    - [web dev](#web-dev)
    - [web build](#web-build)
    - [web start](#web-start)
    - [web doctor](#web-doctor)
    - [web generate-sdk](#web-generate-sdk)
    - [web token](#web-token)
  - [MCP (Model Context Protocol) Servers](#mcp-model-context-protocol-servers)
    - [mcp add](#mcp-add)
    - [mcp list](#mcp-list)
    - [mcp deploy](#mcp-deploy)
    - [mcp undeploy](#mcp-undeploy)
    - [mcp health](#mcp-health)
  - [Context Management](#context-management)
    - [context add](#context-add)
    - [context list](#context-list)
    - [context show](#context-show)
    - [context deploy](#context-deploy)
    - [context remove](#context-remove)
  - [Bundle Management](#bundle-management)
    - [bundle create](#bundle-create)
    - [bundle inspect](#bundle-inspect)
    - [bundle import](#bundle-import)
  - [Vault Management](#vault-management)
    - [vault add](#vault-add)
    - [vault list](#vault-list)
    - [vault push](#vault-push)
    - [vault pull](#vault-pull)
    - [vault ls](#vault-ls)
    - [vault remove](#vault-remove)
    - [vault set-default](#vault-set-default)
    - [vault auth](#vault-auth)
  - [Bundle Signing](#bundle-signing)
    - [sign generate-key](#sign-generate-key)
    - [sign list-keys](#sign-list-keys)
    - [sign export-key](#sign-export-key)
    - [sign import-key](#sign-import-key)
    - [sign verify](#sign-verify)
    - [sign revoke](#sign-revoke)
  - [Marketplace](#marketplace)
    - [marketplace-search](#marketplace-search)
    - [marketplace-install](#marketplace-install)
    - [marketplace-publish](#marketplace-publish)
  - [Compliance](#compliance)
    - [compliance-scan](#compliance-scan)
    - [compliance-checklist](#compliance-checklist)
    - [compliance-consent](#compliance-consent)
    - [compliance-history](#compliance-history)
  - [Project Operations](#project-operations)
    - [project sync-context](#project-sync-context)
  - [Migration](#migration)
    - [migrate](#migrate)
  - [Special Commands](#special-commands)
    - [active-collection](#active-collection)
    - [quick-add](#quick-add)
    - [alias](#alias)
  - [Security](#security)

---

## Core Commands

### init

Initialize a collection or scaffold project deployment roots.

**Syntax:**

```bash
skillmeat init [--name NAME] [--project-path PATH] [--profile PROFILE | --all-profiles]
```

**Options:**

- `-n, --name TEXT` - Collection name (default: 'default')
- `--project-path PATH` - Optional project path to scaffold deployment roots
- `--profile [claude_code|codex|gemini|cursor]` - Initialize a single profile root
- `--all-profiles` - Initialize all built-in profile roots

**Examples:**

```bash
# Create default collection
skillmeat init

# Create named collection
skillmeat init --name work

# Initialize Codex profile for a project
skillmeat init --project-path /path/to/project --profile codex

# Initialize all profile roots
skillmeat init --project-path /path/to/project --all-profiles
```

**Output:**

```
Collection 'default' initialized
  Location: /home/user/.skillmeat/collections/default
  Artifacts: 0
```

**Notes:**

- Creates collection directory structure (collection mode)
- Initializes empty collection.toml manifest
- In project mode, scaffolds profile roots like `.claude/`, `.codex/`, `.gemini/`, `.cursor/`
- Safe to run multiple times (won't overwrite existing)

---

### list

List artifacts in collection.

**Syntax:**

```bash
skillmeat list [OPTIONS]
```

**Options:**

- `-t, --type [skill|command|agent]` - Filter by artifact type
- `-c, --collection TEXT` - Collection name (default: active collection)
- `--tags` - Show tags for each artifact

**Examples:**

```bash
# List all artifacts
skillmeat list

# List only skills
skillmeat list --type skill

# List with tags
skillmeat list --tags

# List from specific collection
skillmeat list --collection work
```

**Output:**

```
Artifacts (3)
┌─────────────┬─────────┬────────┐
│ Name        │ Type    │ Origin │
├─────────────┼─────────┼────────┤
│ canvas      │ skill   │ github │
│ review      │ command │ github │
│ my-custom   │ skill   │ local  │
└─────────────┴─────────┴────────┘
```

---

### show

Show detailed information about an artifact.

**Syntax:**

```bash
skillmeat show NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Artifact name

**Options:**

- `-t, --type [skill|command|agent]` - Artifact type (required if name is ambiguous)
- `-c, --collection TEXT` - Collection name (default: active collection)

**Examples:**

```bash
# Show artifact details
skillmeat show canvas

# Show when name is ambiguous
skillmeat show review --type command
```

**Output:**

```
canvas
─────────────────────────────────────────
Type:         skill
Name:         canvas
Description:  Canvas design and prototyping skill
Origin:       github
Upstream:     https://github.com/anthropics/skills/tree/main/canvas
Version:      latest -> abc123d
Added:        2025-11-01 10:30:00
Location:     ~/.skillmeat/collections/default/skills/canvas/

Deployed to:
  • ~/projects/web-app (.claude/skills/canvas/)
  • ~/projects/design-tool (.claude/skills/canvas/)

Tags: design, ui, prototyping
```

---

### remove

Remove artifact from collection.

**Syntax:**

```bash
skillmeat remove NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Artifact name

**Options:**

- `-t, --type [skill|command|agent]` - Artifact type (required if name is ambiguous)
- `-c, --collection TEXT` - Collection name (default: active collection)
- `--keep-files` - Remove from collection but keep files on disk

**Examples:**

```bash
# Remove artifact completely
skillmeat remove canvas

# Remove from collection but keep files
skillmeat remove canvas --keep-files

# Remove when name is ambiguous
skillmeat remove review --type command
```

**Output:**

```
Removed skill: canvas
  From collection: default
  Files deleted: yes
```

---

## Adding Artifacts

### add skill

Add a skill from GitHub or local path.

**Syntax:**

```bash
skillmeat add skill SPEC [OPTIONS]
```

**Arguments:**

- `SPEC` - GitHub path or local file path
  - GitHub: `user/repo/path/to/skill[@version]`
  - Local: `/path/to/skill` or `./relative/path`

**Options:**

- `-c, --collection TEXT` - Collection name (default: active collection)
- `-n, --name TEXT` - Override artifact name
- `--no-verify` - Skip validation
- `-f, --force` - Overwrite existing artifact
- `--dangerously-skip-permissions` - Skip security warning (not recommended)

**Examples:**

```bash
# Add from GitHub (latest version)
skillmeat add skill anthropics/skills/canvas

# Add specific version
skillmeat add skill user/repo/skill@v1.0.0

# Add from local path
skillmeat add skill ./my-local-skill

# Add with custom name
skillmeat add skill ./skill --name custom-name

# Force overwrite existing
skillmeat add skill anthropics/skills/canvas --force
```

**Output:**

```
Security warning: Artifacts can execute code and access system resources.
...
Do you want to continue installing this artifact? [y/N]: y

Fetching from GitHub: anthropics/skills/canvas...
Added skill: canvas
```

---

### add command

Add a command from GitHub or local path.

**Syntax:**

```bash
skillmeat add command SPEC [OPTIONS]
```

**Arguments:**

- `SPEC` - GitHub path or local file path
  - GitHub: `user/repo/path/to/command.md[@version]`
  - Local: `/path/to/command.md` or `./command.md`

**Options:**

- Same as `add skill`

**Examples:**

```bash
# Add command from GitHub
skillmeat add command user/repo/commands/review.md

# Add from local path
skillmeat add command ./review.md --name my-review

# Skip security warning (not recommended)
skillmeat add command user/repo/cmd.md --dangerously-skip-permissions
```

---

### add agent

Add an agent from GitHub or local path.

**Syntax:**

```bash
skillmeat add agent SPEC [OPTIONS]
```

**Arguments:**

- `SPEC` - GitHub path or local file path
  - GitHub: `user/repo/path/to/agent.md[@version]`
  - Local: `/path/to/agent.md` or `./agent.md`

**Options:**

- Same as `add skill`

**Examples:**

```bash
# Add agent from GitHub
skillmeat add agent user/repo/agents/reviewer.md

# Add from local
skillmeat add agent ./my-agent.md
```

---

## Deployment

### deploy

Deploy artifacts to a project profile root (defaults to Claude profile for legacy workflows).

**Syntax:**

```bash
skillmeat deploy NAMES... [OPTIONS]
```

**Arguments:**

- `NAMES...` - One or more artifact names

**Options:**

- `-c, --collection TEXT` - Collection name (default: active collection)
- `-p, --project PATH` - Project path (default: current directory)
- `-t, --type [skill|command|agent]` - Artifact type (required if names are ambiguous)
- `--profile TEXT` - Deploy to one profile (for example `claude_code`, `codex`)
- `--all-profiles` - Deploy to all configured project profiles

**Examples:**

```bash
# Deploy single artifact to current directory
skillmeat deploy canvas

# Deploy multiple artifacts
skillmeat deploy canvas python review

# Deploy to specific project
skillmeat deploy canvas --project /path/to/project

# Deploy with type filter
skillmeat deploy review --type command

# Deploy to Codex profile
skillmeat deploy canvas --project /path/to/project --profile codex

# Deploy to all profiles
skillmeat deploy canvas --project /path/to/project --all-profiles
```

**Output:**

```
Deploying 3 artifact(s)...
Deployed 3 artifact(s)
  canvas -> .claude/skills/canvas/
  python -> .claude/skills/python/
  review -> .claude/commands/review.md
```

**Notes:**

- Creates profile root directory if it doesn't exist
- Creates deployment tracking file `.skillmeat-deployed.toml`
- Preserves artifact structure (skills as directories, commands as files)
- Without `--profile`, legacy behavior targets the default Claude profile

---

### undeploy

Remove deployed artifact from project.

**Syntax:**

```bash
skillmeat undeploy NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Artifact name

**Options:**

- `-p, --project PATH` - Project path (default: current directory)
- `-t, --type [skill|command|agent]` - Artifact type (required if name is ambiguous)

**Examples:**

```bash
# Undeploy from current project
skillmeat undeploy canvas

# Undeploy from specific project
skillmeat undeploy canvas --project /path/to/project
```

**Output:**

```
Undeployed skill: canvas
  From project: /path/to/project
  Removed: .claude/skills/canvas/
```

---

## Updates & Status

### status

Check update status for artifacts and deployments.

**Syntax:**

```bash
skillmeat status [OPTIONS]
```

**Options:**

- `-c, --collection TEXT` - Collection name (default: active collection)
- `-p, --project PATH` - Project path for deployment status (default: current directory)
- `--profile TEXT` - Filter deployment status to a single profile

**Examples:**

```bash
# Check collection update status
skillmeat status

# Check specific collection
skillmeat status --collection work

# Check deployment status for project
skillmeat status --project /path/to/project

# Check status for Codex profile only
skillmeat status --project /path/to/project --profile codex
```

**Output:**

```
Checking for updates...

Updates available (2):
  python (skill): v2.0.0 -> v2.1.0
  review (command): abc123 -> def456

Up to date (3):
  canvas (skill)
  custom (skill)
  test-runner (command)

Checking deployment status...

Locally modified (1):
  review (command)

Synced (2):
  canvas (skill)
  python (skill)
```

---

### update

Update artifact(s) from upstream sources.

**Syntax:**

```bash
skillmeat update [NAME] [OPTIONS]
```

**Arguments:**

- `NAME` - Artifact name (optional if using --all)

**Options:**

- `-c, --collection TEXT` - Collection name (default: active collection)
- `-t, --type [skill|command|agent]` - Artifact type (required if name is ambiguous)
- `--strategy [prompt|upstream|local]` - Update strategy (default: prompt)

**Update Strategies:**

- `prompt` - Ask user what to do if conflicts exist
- `upstream` - Always take upstream version
- `local` - Keep local modifications

**Examples:**

```bash
# Update single artifact (with prompt on conflicts)
skillmeat update python

# Force upstream version
skillmeat update python --strategy upstream

# Keep local modifications
skillmeat update review --strategy local
```

**Output:**

```
Updating python...
Fetching latest version from upstream...
Updated python: v2.0.0 -> v2.1.0
```

---

## Versioning

### snapshot

Create a snapshot of the collection.

**Syntax:**

```bash
skillmeat snapshot [MESSAGE] [OPTIONS]
```

**Arguments:**

- `MESSAGE` - Snapshot message (default: "Manual snapshot")

**Options:**

- `-c, --collection TEXT` - Collection name (default: active collection)

**Examples:**

```bash
# Create snapshot with default message
skillmeat snapshot

# Create with custom message
skillmeat snapshot "Before major refactor"

# Snapshot specific collection
skillmeat snapshot "Backup" --collection work
```

**Output:**

```
Created snapshot: abc123d
  Collection: default
  Message: Before major refactor
  Artifacts: 12
  Location: ~/.skillmeat/snapshots/default/2025-11-08-143000.tar.gz
```

**Notes:**

- Snapshots are automatically created before destructive operations
- Stored as compressed tarballs in `~/.skillmeat/snapshots/`
- Include entire collection state (manifest + lock + all artifacts)

---

### history

List collection snapshots.

**Syntax:**

```bash
skillmeat history [OPTIONS]
```

**Options:**

- `-c, --collection TEXT` - Collection name (default: active collection)
- `-n, --limit INTEGER` - Number of snapshots to show (default: 10)

**Examples:**

```bash
# Show recent snapshots
skillmeat history

# Show more snapshots
skillmeat history --limit 20

# Show from specific collection
skillmeat history --collection work
```

**Output:**

```
Snapshots for 'default' (5)
┌──────────┬─────────────────────┬────────────────────────┬───────────┐
│ ID       │ Created             │ Message                │ Artifacts │
├──────────┼─────────────────────┼────────────────────────┼───────────┤
│ abc123d  │ 2025-11-08 14:30:00 │ Before major refactor  │ 12        │
│ def456e  │ 2025-11-07 09:15:00 │ Added security tools   │ 10        │
│ 789fghi  │ 2025-11-06 16:45:00 │ Initial setup          │ 5         │
└──────────┴─────────────────────┴────────────────────────┴───────────┘
```

---

### rollback

Restore collection from a snapshot.

**Syntax:**

```bash
skillmeat rollback SNAPSHOT_ID [OPTIONS]
```

**Arguments:**

- `SNAPSHOT_ID` - Snapshot identifier from history

**Options:**

- `-c, --collection TEXT` - Collection name (default: active collection)
- `-y, --yes` - Skip confirmation prompt

**Examples:**

```bash
# Rollback with confirmation
skillmeat rollback abc123d

# Rollback without confirmation
skillmeat rollback abc123d --yes

# Rollback specific collection
skillmeat rollback abc123d --collection work
```

**Output:**

```
Warning: This will replace collection 'default' with snapshot 'abc123d'
Continue with rollback? [y/N]: y

Rolling back to snapshot abc123d...
Created safety snapshot: xyz789a
Restored collection from snapshot
  Artifacts restored: 12
  Collection state: 2025-11-08 14:30:00
```

**Notes:**

- Creates a safety snapshot of current state before rollback
- Replaces entire collection (manifest + lock + artifacts)
- Cannot be undone (except by rolling back to the safety snapshot)

---

## Collection Management

### collection create

Create a new collection.

**Syntax:**

```bash
skillmeat collection create NAME
```

**Arguments:**

- `NAME` - Collection name

**Examples:**

```bash
# Create work collection
skillmeat collection create work

# Create experimental collection
skillmeat collection create experimental
```

**Output:**

```
Creating collection 'work'...
Collection 'work' created
  Location: /home/user/.skillmeat/collections/work
```

---

### collection list

List all collections.

**Syntax:**

```bash
skillmeat collection list
```

**Examples:**

```bash
skillmeat collection list
```

**Output:**

```
Collections
┌──────────────┬────────┬───────────┐
│ Name         │ Active │ Artifacts │
├──────────────┼────────┼───────────┤
│ default      │ ✓      │ 12        │
│ work         │        │ 8         │
│ experimental │        │ 3         │
└──────────────┴────────┴───────────┘
```

**Notes:**

- Active collection is marked with ✓
- Shows artifact count for each collection

---

### collection use

Switch to a different collection.

**Syntax:**

```bash
skillmeat collection use NAME
```

**Arguments:**

- `NAME` - Collection name

**Examples:**

```bash
# Switch to work collection
skillmeat collection use work

# Switch back to default
skillmeat collection use default
```

**Output:**

```
Switched to collection 'work'
```

**Notes:**

- Makes the collection active for all subsequent commands
- Setting persists across terminal sessions

---

## Configuration

### config list

List all configuration values.

**Syntax:**

```bash
skillmeat config list
```

**Examples:**

```bash
skillmeat config list
```

**Output:**

```
Configuration
┌──────────────────────┬─────────────────┐
│ Key                  │ Value           │
├──────────────────────┼─────────────────┤
│ default-collection   │ default         │
│ github-token         │ ghp_xxxxx...    │
│ update-strategy      │ prompt          │
└──────────────────────┴─────────────────┘
```

**Notes:**

- GitHub tokens are masked in output
- Configuration stored in `~/.skillmeat/config.toml`

---

### config get

Get a configuration value.

**Syntax:**

```bash
skillmeat config get KEY
```

**Arguments:**

- `KEY` - Configuration key

**Examples:**

```bash
# Get GitHub token
skillmeat config get github-token

# Get default collection
skillmeat config get default-collection
```

**Output:**

```
github-token = ghp_xxxxx...
```

---

### config set

Set a configuration value.

**Syntax:**

```bash
skillmeat config set KEY VALUE
```

**Arguments:**

- `KEY` - Configuration key
- `VALUE` - Configuration value

**Common Keys:**

- `github-token` - GitHub personal access token (for private repos and higher rate limits)
- `default-collection` - Default collection name
- `update-strategy` - Default update strategy (prompt/upstream/local)

**Examples:**

```bash
# Set GitHub token
skillmeat config set github-token ghp_xxxxxxxxxxxxx

# Set default collection
skillmeat config set default-collection work

# Set update strategy
skillmeat config set update-strategy upstream
```

**Output:**

```
Set github-token
```

**Notes:**

- GitHub token format: `ghp_` followed by alphanumeric characters
- [Create GitHub token](https://github.com/settings/tokens)

---

## Cache Management

### cache status

Show cache statistics and health information.

**Syntax:**

```bash
skillmeat cache status
```

**Examples:**

```bash
skillmeat cache status
```

**Output:**

```
Cache Statistics

Total Projects Cached:    5
Cached Size:             2.4 MB
Last Updated:            2024-01-15 10:30:00
Cache TTL:               300 seconds

Project Cache:
  ~/projects/app1        ✓ Fresh   (updated 5m ago)
  ~/projects/app2        ✓ Fresh   (updated 15m ago)
  ~/projects/app3        ⚠ Stale   (updated 2h ago)

Cache Health: 3/5 fresh, 2/5 stale
```

---

### cache refresh

Refresh cache data for projects or entire cache.

**Syntax:**

```bash
skillmeat cache refresh [PROJECT_ID] [OPTIONS]
```

**Arguments:**

- `PROJECT_ID` - Optional project ID to refresh (refreshes all if omitted)

**Options:**

- `--force` - Force refresh even if fresh

**Examples:**

```bash
# Refresh all cached data
skillmeat cache refresh

# Refresh specific project
skillmeat cache refresh proj-abc123

# Force refresh
skillmeat cache refresh --force
```

**Output:**

```
Refreshing cache...
Updated 3 projects:
  ~/projects/app1        ✓ 5ms
  ~/projects/app2        ✓ 8ms
  ~/projects/app3        ✓ 12ms
```

---

### cache clear

Clear all cached data.

**Syntax:**

```bash
skillmeat cache clear [OPTIONS]
```

**Options:**

- `--confirm` - Skip confirmation prompt
- `--older-than-days INTEGER` - Only clear data older than N days

**Examples:**

```bash
# Clear all cache with confirmation
skillmeat cache clear

# Clear without confirmation
skillmeat cache clear --confirm

# Clear data older than 30 days
skillmeat cache clear --older-than-days 30
```

**Output:**

```
Cache cleared
  Projects cleared: 5
  Space freed: 2.4 MB
```

---

### cache config

Get or set cache configuration.

**Syntax:**

```bash
skillmeat cache config [get|set] [KEY] [VALUE]
```

**Commands:**

- `get KEY` - Get configuration value
- `set KEY VALUE` - Set configuration value

**Common Keys:**

- `cache-ttl` - Cache time-to-live in seconds (default: 300)
- `auto-refresh` - Auto-refresh on stale data (default: true)

**Examples:**

```bash
# Get cache TTL
skillmeat cache config get cache-ttl

# Set cache TTL to 10 minutes
skillmeat cache config set cache-ttl 600

# Get auto-refresh setting
skillmeat cache config get auto-refresh
```

**Output:**

```
cache-ttl = 300
```

---

## Scoring and Matching

### match

Match artifacts against a query using confidence scoring.

**Syntax:**

```bash
skillmeat match QUERY [OPTIONS]
```

**Arguments:**

- `QUERY` - Search query or artifact description

**Options:**

- `-l, --limit INTEGER` - Maximum results to show (default: 5)
- `-m, --min-confidence FLOAT` - Minimum confidence threshold (0-100, default: 0)
- `-c, --collection TEXT` - Collection to search (default: active)
- `-v, --verbose` - Show score breakdown
- `--json` - Output results as JSON

**Examples:**

```bash
# Basic semantic match
skillmeat match "pdf processor"

# Limit results
skillmeat match "authentication" --limit 3

# Filter by confidence
skillmeat match "testing" --min-confidence 50

# Show detailed breakdown
skillmeat match "database" --verbose

# Get JSON output
skillmeat match "api" --json
```

**Output:**

```
Matching artifacts for 'pdf processor'

Rank  Name              Type     Confidence   Score Details
──────────────────────────────────────────────────────────
1     pdf-extractor     skill    95           Semantic: 98, Keyword: 92
2     document-parser   skill    87           Semantic: 85, Keyword: 89
3     file-processor    skill    72           Semantic: 68, Keyword: 76
```

---

### rate

Rate an artifact from 1-5.

**Syntax:**

```bash
skillmeat rate ARTIFACT RATING [OPTIONS]
```

**Arguments:**

- `ARTIFACT` - Artifact name
- `RATING` - Rating from 1-5

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `-t, --type [skill|command|agent]` - Artifact type (if ambiguous)
- `--note TEXT` - Optional feedback note

**Examples:**

```bash
# Rate artifact
skillmeat rate canvas 5

# Rate with feedback
skillmeat rate pdf-extractor 4 --note "Very useful but needs documentation"

# Rate specific type
skillmeat rate review 3 --type command
```

**Output:**

```
Rating recorded: canvas = 5/5
```

---

### scores import

Import community scores from external sources.

**Syntax:**

```bash
skillmeat scores import [OPTIONS]
```

**Options:**

- `--source [github|registry|all]` - Import source (default: all)
- `--force` - Force re-import even if recent

**Examples:**

```bash
# Import from all sources
skillmeat scores import

# Import GitHub stars only
skillmeat scores import --source github

# Force re-import
skillmeat scores import --force
```

**Output:**

```
Importing scores...
  From GitHub: 12 artifacts updated
  From registry: 5 artifacts updated
Total: 17 artifacts updated
```

---

### scores refresh

Refresh stale community scores.

**Syntax:**

```bash
skillmeat scores refresh [OPTIONS]
```

**Options:**

- `--stale-threshold-days INTEGER` - Age threshold in days (default: 30)

**Examples:**

```bash
# Refresh all stale scores
skillmeat scores refresh

# Refresh scores older than 60 days
skillmeat scores refresh --stale-threshold-days 60
```

**Output:**

```
Refreshing scores...
Updated 8 artifacts with fresh data
```

---

### scores show

Show detailed scores for an artifact.

**Syntax:**

```bash
skillmeat scores show ARTIFACT [OPTIONS]
```

**Arguments:**

- `ARTIFACT` - Artifact name

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `-t, --type [skill|command|agent]` - Artifact type (if ambiguous)

**Examples:**

```bash
skillmeat scores show canvas
skillmeat scores show pdf-extractor --type skill
```

**Output:**

```
Scores for 'canvas'

Community Score:       4.8/5.0
  GitHub Stars:        1,250
  Downloads:           2,400
  Community Ratings:   24 (4.8/5)
  Usage Score:         0.92

Breakdown:
  Quality:             92
  Popularity:          88
  Maintenance:         85
  Documentation:       90
```

---

### scores stats

Show match success statistics.

**Syntax:**

```bash
skillmeat scores stats
```

**Examples:**

```bash
skillmeat scores stats
```

**Output:**

```
Match Statistics

Successful Matches:    156
Failed Matches:        12
Success Rate:          92.9%

Top Matching Artifacts:
  canvas               (45 matches)
  pdf-extractor        (32 matches)
  code-reviewer        (28 matches)
```

---

### scores confirm

Confirm or reject a previous match.

**Syntax:**

```bash
skillmeat scores confirm ARTIFACT [confirm|reject]
```

**Arguments:**

- `ARTIFACT` - Artifact name
- Action - `confirm` or `reject`

**Examples:**

```bash
# Confirm match was correct
skillmeat scores confirm canvas confirm

# Reject match as incorrect
skillmeat scores confirm incorrect-match reject
```

**Output:**

```
Match feedback recorded
```

---

## Phase 2: Diff Commands

Diff commands compare files and directories to detect changes, with support for three-way merges and conflict detection.

### diff files

Compare two individual files and show unified differences.

**Syntax:**

```bash
skillmeat diff files FILE1 FILE2 [OPTIONS]
```

**Arguments:**

- `FILE1` - Path to first file
- `FILE2` - Path to second file

**Options:**

- `-c, --context INTEGER` - Context lines around changes (default: 3)
- `--color/--no-color` - Enable/disable colored output (default: enabled)

**Examples:**

```bash
# Compare two files with default context
skillmeat diff files ./old-skill.md ./new-skill.md

# Show 5 lines of context
skillmeat diff files ./script1.py ./script2.py --context 5

# Disable colored output
skillmeat diff files ./file1.txt ./file2.txt --no-color
```

**Output:**

```diff
--- ./old-skill.md
+++ ./new-skill.md
@@ -1,5 +1,6 @@
 # Skill Name
 Description here
+New line added

 ## Usage
 Example usage
```

---

### diff dirs

Compare two directories recursively and show structure differences.

**Syntax:**

```bash
skillmeat diff dirs DIR1 DIR2 [OPTIONS]
```

**Arguments:**

- `DIR1` - Path to first directory
- `DIR2` - Path to second directory

**Options:**

- `--ignore TEXT` - Patterns to ignore (can use multiple times)
- `--limit INTEGER` - Max file diffs to show (default: 50)
- `--stats-only` - Show only statistics

**Examples:**

```bash
# Compare artifact directories
skillmeat diff dirs ./canvas-v1 ./canvas-v2

# Ignore build artifacts
skillmeat diff dirs ./src1 ./src2 --ignore "*.pyc" --ignore "dist/"

# Show only statistics
skillmeat diff dirs ./project1 ./project2 --stats-only
```

**Output:**

```
Directory Comparison
  Files added:     5
  Files removed:   2
  Files modified:  8

Modified Files:
  M main.py (42 additions, 18 deletions)
  M README.md (5 additions, 3 deletions)
```

---

### diff three-way

Perform three-way diff for detecting merge conflicts.

**Syntax:**

```bash
skillmeat diff three-way BASE LOCAL REMOTE [OPTIONS]
```

**Arguments:**

- `BASE` - Base/original version
- `LOCAL` - Local version
- `REMOTE` - Remote version

**Options:**

- `-o, --output PATH` - Write merged result to file
- `--algorithm TEXT` - Merge algorithm (default: auto)

**Examples:**

```bash
# Detect merge conflicts
skillmeat diff three-way ./base-skill ./local-skill ./upstream-skill

# Write merged result
skillmeat diff three-way ./base.md ./local.md ./upstream.md --output ./merged.md
```

**Output (with conflicts):**

```diff
<<<<<<< LOCAL
Local changes here
=======
Remote changes here
>>>>>>> REMOTE
```

---

### diff artifact

Compare artifact between versions or against upstream.

**Syntax:**

```bash
skillmeat diff artifact ARTIFACT [OPTIONS]
```

**Arguments:**

- `ARTIFACT` - Artifact name

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `-t, --type [skill|command|agent]` - Artifact type (if ambiguous)
- `--upstream` - Compare against upstream
- `--previous` - Compare against previous version
- `--snapshot TEXT` - Compare against snapshot ID
- `--context INTEGER` - Context lines (default: 3)
- `--stats-only` - Show only statistics

**Examples:**

```bash
# Check what changed in artifact
skillmeat diff artifact canvas

# Compare against upstream
skillmeat diff artifact pdf-extractor --upstream

# Compare against previous version
skillmeat diff artifact code-reviewer --previous

# Show only stats
skillmeat diff artifact my-skill --stats-only
```

---

## Phase 2: Search Commands

Search commands help find and discover artifacts across collections and projects.

### search

Search artifacts by metadata or content.

**Syntax:**

```bash
skillmeat search QUERY [OPTIONS]
```

**Arguments:**

- `QUERY` - Search query

**Options:**

- `-c, --collection TEXT` - Collection to search (default: active)
- `-t, --type [skill|command|agent]` - Filter by type
- `--search-type [metadata|content|both]` - Search scope (default: both)
- `--tags TEXT` - Filter by tags (comma-separated)
- `-l, --limit INTEGER` - Max results (default: 50)
- `-p, --projects PATH` - Project paths to search (multiple allowed)
- `--discover` - Auto-discover projects
- `--no-cache` - Disable cache
- `--json` - Output as JSON

**Examples:**

```bash
# Search in collection
skillmeat search "authentication"

# Search content only
skillmeat search "error handling" --search-type content

# Filter by tags
skillmeat search "productivity" --tags documentation,utilities

# Cross-project search
skillmeat search "testing" --projects ~/projects/app1 ~/projects/app2

# Auto-discover projects
skillmeat search "api" --discover

# Get JSON output
skillmeat search "database" --json

# Combine filters
skillmeat search "auth" --type command --tags security --limit 20
```

**Output:**

```
Artifacts matching 'authentication'

Name              Type     Collection   Tags                  Score
────────────────────────────────────────────────────────────────────
auth-handler      skill    default      security,core         0.95
login-validator   command  default      validation,auth       0.88
oauth-integrator  skill    default      integration,security  0.82
```

---

### find-duplicates

Detect duplicate or similar artifacts.

**Syntax:**

```bash
skillmeat find-duplicates [OPTIONS]
```

**Options:**

- `-c, --collection TEXT` - Collection to check (default: active)
- `-p, --projects PATH` - Project paths (multiple allowed)
- `-t, --threshold FLOAT` - Similarity threshold 0.0-1.0 (default: 0.85)
- `--no-cache` - Disable cache
- `--json` - Output as JSON

**Examples:**

```bash
# Find duplicates in collection
skillmeat find-duplicates

# Find across projects
skillmeat find-duplicates --projects ~/projects/app1 ~/projects/app2

# Use stricter threshold (95%)
skillmeat find-duplicates --threshold 0.95

# Use looser threshold (70%)
skillmeat find-duplicates --threshold 0.70

# Get JSON output
skillmeat find-duplicates --json
```

**Output:**

```
Duplicate Detection Results

Group 1: 2 similar artifacts (95% match)
  canvas-v1        (skill, collection: default)
  canvas-redesign  (skill, collection: default)
  Recommendation: Review and consolidate

Group 2: 3 similar artifacts (87% match)
  pdf-reader       (skill, collection: default)
  pdf-extractor    (skill, collection: work)
  doc-parser       (command, collection: work)
  Recommendation: Check for code reuse
```

---

## Phase 2: Sync Commands

Sync commands handle bidirectional synchronization between projects and collections.

### sync check

Check for drift between project and collection.

**Syntax:**

```bash
skillmeat sync check PROJECT_PATH [OPTIONS]
```

**Arguments:**

- `PROJECT_PATH` - Path to project root

**Options:**

- `-c, --collection TEXT` - Collection (default: from deployment metadata)
- `--json` - Output as JSON

**Examples:**

```bash
# Check project in current directory
skillmeat sync check /path/to/project

# Check against specific collection
skillmeat sync check /path/to/project --collection work

# Get JSON output
skillmeat sync check /path/to/project --json
```

**Output (No Drift):**

```
No drift detected. Project is in sync.

Project: /path/to/project
```

**Output (With Drift):**

```
Drift Detection Results: 3 artifacts

Artifact       Type     Drift Type              Recommendation
────────────────────────────────────────────────────────────────
canvas         skill    UPSTREAM_CHANGED        SYNC_UPSTREAM
pdf-extractor  skill    MODIFIED_LOCALLY        REVIEW_CHANGES
code-reviewer  command  REMOVED_FROM_COLLECTION VERIFY_AND_REMOVE
```

**Exit Codes:**

- `0` - No drift detected
- `1` - Drift detected
- `2` - Error

---

### sync pull

Sync changes from project to collection.

**Syntax:**

```bash
skillmeat sync pull PROJECT_PATH [ARTIFACTS...] [OPTIONS]
```

**Arguments:**

- `PROJECT_PATH` - Path to project root
- `ARTIFACTS...` - Specific artifact names (optional)

**Options:**

- `-c, --collection TEXT` - Collection (default: from metadata)
- `--strategy [overwrite|merge|fork]` - Sync strategy
- `--force` - Skip confirmation

**Sync Strategies:**

- `overwrite` - Collection version takes precedence
- `merge` - Auto-merge if possible
- `fork` - Create new artifact for diverged version

**Examples:**

```bash
# Sync all drifted artifacts
skillmeat sync pull /path/to/project

# Sync specific artifacts
skillmeat sync pull /path/to/project canvas pdf-extractor

# Force overwrite from collection
skillmeat sync pull /path/to/project --strategy overwrite --force

# Merge changes
skillmeat sync pull /path/to/project --strategy merge
```

**Output:**

```
Syncing artifacts from project...

canvas (skill)
  Status: SYNCED (merged)
  Changes: 15 additions, 3 deletions

pdf-extractor (skill)
  Status: CONFLICT
  Action: Manual merge required
```

---

### sync preview

Preview sync changes before applying.

**Syntax:**

```bash
skillmeat sync preview PROJECT_PATH [ARTIFACTS...] [OPTIONS]
```

**Arguments:**

- `PROJECT_PATH` - Path to project root
- `ARTIFACTS...` - Specific artifact names (optional)

**Options:**

- `-c, --collection TEXT` - Collection (default: from metadata)
- `--json` - Output as JSON

**Examples:**

```bash
# Preview all changes
skillmeat sync preview /path/to/project

# Preview specific artifacts
skillmeat sync preview /path/to/project canvas pdf-extractor

# Get JSON output
skillmeat sync preview /path/to/project --json
```

**Output:**

```
Sync Preview: /path/to/project

canvas (skill)
  Status: WOULD_SYNC
  Changes: 12 additions, 5 deletions
  Files: +2, -1, M 3

Total artifacts to sync: 2
Potential conflicts: 1

Run 'skillmeat sync pull' to apply changes
```

---

## Phase 2: Analytics Commands

Analytics commands track usage patterns and provide insights about artifact operations.

### analytics usage

View artifact usage statistics.

**Syntax:**

```bash
skillmeat analytics usage [ARTIFACT] [OPTIONS]
```

**Arguments:**

- `ARTIFACT` - Artifact name (optional, shows all if omitted)

**Options:**

- `--days INTEGER` - Time window in days (default: 30)
- `-t, --type [skill|command|agent]` - Filter by type
- `-c, --collection TEXT` - Filter by collection
- `--format [table|json]` - Output format (default: table)
- `--sort-by [total_events|deploy_count|update_count|last_used|artifact_name]` - Sort field

**Examples:**

```bash
# Show usage for all artifacts (30-day window)
skillmeat analytics usage

# Show usage for specific artifact
skillmeat analytics usage canvas

# Show all skills
skillmeat analytics usage --type skill

# From last 90 days
skillmeat analytics usage --days 90

# Sort by recency
skillmeat analytics usage --sort-by last_used

# Get JSON output
skillmeat analytics usage --format json
```

**Output:**

```
Artifact Usage

Name              Type     Total Events   Deploy   Update   Last Used
──────────────────────────────────────────────────────────────────────
canvas            skill    47             12       8        2024-01-15
pdf-extractor     skill    23             5        3        2024-01-10
code-reviewer     command  15             2        1        2024-01-05
```

---

### analytics top

List top artifacts by metric.

**Syntax:**

```bash
skillmeat analytics top [OPTIONS]
```

**Options:**

- `--limit INTEGER` - Number to show (default: 10)
- `--metric [total_events|deploy_count|update_count|sync_count|search_count]` - Ranking metric (default: total_events)
- `-t, --type [skill|command|agent]` - Filter by type
- `--format [table|json]` - Output format (default: table)

**Examples:**

```bash
# Top 10 artifacts
skillmeat analytics top

# Top 20 by deploys
skillmeat analytics top --limit 20 --metric deploy_count

# Top skills by updates
skillmeat analytics top --metric update_count --type skill

# Get JSON
skillmeat analytics top --format json
```

**Output:**

```
Top 10 Artifacts by Total Events

Rank   Name              Type     Total Events   Deploy   Update
──────────────────────────────────────────────────────────────────
1      canvas            skill    47             12       8
2      pdf-extractor     skill    23             5        3
3      code-reviewer     command  15             2        1
```

---

### analytics cleanup

Show cleanup suggestions for unused artifacts.

**Syntax:**

```bash
skillmeat analytics cleanup [OPTIONS]
```

**Options:**

- `--inactivity-days INTEGER` - Inactivity threshold in days (default: 90)
- `-c, --collection TEXT` - Filter by collection
- `--format [table|json]` - Output format (default: table)
- `--show-size` - Show disk space estimates

**Examples:**

```bash
# Get cleanup suggestions
skillmeat analytics cleanup

# Use stricter threshold (60 days)
skillmeat analytics cleanup --inactivity-days 60

# Show disk space
skillmeat analytics cleanup --show-size

# Get JSON output
skillmeat analytics cleanup --format json
```

**Output:**

```
Cleanup Suggestions

Unused (90+ days): 5 artifacts
  auth-legacy      skill      Last used: 2023-09-20    Size: 245 KB
  deprecated-api   command    Last used: 2023-08-15    Size: 128 KB

Never Deployed: 3 artifacts
  experimental     skill      Created: 2024-01-01      Size: 156 KB

Estimated space savings: 1.2 MB
```

---

### analytics trends

Display usage trends over time.

**Syntax:**

```bash
skillmeat analytics trends [ARTIFACT] [OPTIONS]
```

**Arguments:**

- `ARTIFACT` - Artifact name (optional)

**Options:**

- `--period [7d|30d|90d|all]` - Time period (default: 30d)
- `--format [table|json]` - Output format (default: table)

**Examples:**

```bash
# Overall trends (30 days)
skillmeat analytics trends

# Specific artifact
skillmeat analytics trends canvas

# Last 7 days
skillmeat analytics trends --period 7d

# All-time trends
skillmeat analytics trends canvas --period all
```

**Output:**

```
Usage Trends: canvas (30-day period)

Week 1 (Jan 1-7):   ████░░░░░░ 4 events
Week 2 (Jan 8-14):  ██████░░░░ 6 events
Week 3 (Jan 15-21): ████████░░ 8 events
Week 4 (Jan 22-28): ██████░░░░ 6 events

Event Breakdown:
  Deployments: 12  ████░░
  Updates:      8  ███░░░
```

---

### analytics export

Export comprehensive analytics report to file.

**Syntax:**

```bash
skillmeat analytics export OUTPUT_PATH [OPTIONS]
```

**Arguments:**

- `OUTPUT_PATH` - Path where report will be saved

**Options:**

- `--format [json|csv]` - Export format (default: json)
- `-c, --collection TEXT` - Filter by collection

**Examples:**

```bash
# Export to JSON
skillmeat analytics export report.json

# Export to CSV
skillmeat analytics export report.csv --format csv

# Export for specific collection
skillmeat analytics export work-report.json --collection work
```

**Output:**

```
Exporting analytics report...
Report exported successfully!
  File: /path/to/report.json
  Size: 256.4 KB
  Format: JSON
```

---

### analytics stats

Show analytics database statistics.

**Syntax:**

```bash
skillmeat analytics stats
```

**Examples:**

```bash
skillmeat analytics stats
```

**Output:**

```
Analytics Database Statistics

Total Events:      247
Total Artifacts:   12
Date Range:        2023-10-01 to 2024-01-15 (107 days)

Event Type Breakdown:
  Deployments: 45   (18.2%)
  Updates:     32   (13.0%)
  Syncs:       28   (11.3%)
  Searches:   142   (57.5%)

Database Size:     1.2 MB
```

---

### analytics clear

Clear old analytics data.

**Syntax:**

```bash
skillmeat analytics clear [OPTIONS]
```

**Options:**

- `--older-than-days INTEGER` - Delete events older than N days
- `--confirm` - Skip confirmation

**Examples:**

```bash
# Clear events older than 180 days
skillmeat analytics clear --older-than-days 180 --confirm

# Clear with confirmation
skillmeat analytics clear --older-than-days 90
```

**Output:**

```
This will delete analytics events older than 180 days.
Continue? [y/N]: y

Deleted 1,247 events
Space freed: 245 MB
Remaining events: 2,156
```

---

## Utilities

### verify

Verify an artifact has valid structure.

**Syntax:**

```bash
skillmeat verify SPEC --type TYPE
```

**Arguments:**

- `SPEC` - GitHub path or local file path
- `--type [skill|command|agent]` - Artifact type (required)

**Examples:**

```bash
# Verify GitHub skill
skillmeat verify anthropics/skills/canvas --type skill

# Verify local skill
skillmeat verify ./my-skill --type skill

# Verify command
skillmeat verify user/repo/cmd.md --type command
```

**Output:**

```
Verifying GitHub artifact: anthropics/skills/canvas...
Valid artifact
  Spec: anthropics/skills/canvas
  Type: skill
  Title: Canvas Design Skill
  Description: Design and prototype UI components
  Author: Anthropic
  Version: 2.1.0
  Tags: design, ui, prototyping
```

**Notes:**

- Checks artifact structure without adding to collection
- Useful for testing before installation
- Downloads GitHub artifacts to temporary directory (automatically cleaned up)

---

## Exit Codes

- `0` - Success
- `1` - User error (invalid arguments, artifact not found, etc.)
- `2` - System error (network failure, file system error, etc.)

## Global Options

All commands support:

- `--help` - Show command help
- `--version` - Show SkillMeat version (root command only)

## Environment Variables

- `SKILLMEAT_CONFIG_DIR` - Override config directory (default: `~/.skillmeat`)
- `GITHUB_TOKEN` - GitHub token (overrides config file)

## File Locations

- **Config:** `~/.skillmeat/config.toml`
- **Collections:** `~/.skillmeat/collections/{name}/`
- **Snapshots:** `~/.skillmeat/snapshots/{name}/`
- **Project deployments:** `./.claude/`
- **Deployment tracking:** `./.claude/.skillmeat-deployed.toml`

## Version Specifications

When adding artifacts from GitHub, you can specify versions:

- `@latest` - Latest commit (default)
- `@v1.0.0` - Specific tag
- `@abc123d` - Specific commit SHA
- `@main` - Specific branch
- Omit version - Same as `@latest`

Examples:

```bash
skillmeat add skill user/repo/skill@latest
skillmeat add skill user/repo/skill@v1.0.0
skillmeat add skill user/repo/skill@abc123d
skillmeat add skill user/repo/skill@main
skillmeat add skill user/repo/skill
```

## Web Interface

### web dev

Start development servers with auto-reload.

**Syntax:**

```bash
skillmeat web dev [OPTIONS]
```

**Options:**

- `--api-only` - Start only FastAPI backend server
- `--web-only` - Start only Next.js frontend
- `--port INTEGER` - API port (default: 8080)
- `--web-port INTEGER` - Web port (default: 3000)
- `--no-open` - Don't open browser automatically

**Examples:**

```bash
# Start both servers
skillmeat web dev

# Start API only
skillmeat web dev --api-only

# Start Next.js only
skillmeat web dev --web-only

# Custom ports
skillmeat web dev --port 8888 --web-port 3001
```

**Output:**

```
Starting development servers...

FastAPI server: http://localhost:8080
  API docs: http://localhost:8080/api/v1/docs

Next.js server: http://localhost:3000
  App ready: http://localhost:3000

Press Ctrl+C to stop
```

---

### web build

Build Next.js application for production.

**Syntax:**

```bash
skillmeat web build [OPTIONS]
```

**Options:**

- `--analyze` - Analyze bundle size
- `--debug` - Keep debug symbols

**Examples:**

```bash
# Build for production
skillmeat web build

# Build and analyze
skillmeat web build --analyze
```

**Output:**

```
Building Next.js application...

Compiled successfully!
  Routes:    42
  Pages:     18
  Bundle:    1.2 MB (gzipped: 385 KB)

Ready to deploy: dist/
```

---

### web start

Start production servers.

**Syntax:**

```bash
skillmeat web start [OPTIONS]
```

**Options:**

- `--port INTEGER` - API port (default: 8080)
- `--web-port INTEGER` - Web port (default: 3000)

**Examples:**

```bash
# Start production
skillmeat web start

# Custom ports
skillmeat web start --port 5000 --web-port 5001
```

**Output:**

```
Starting production servers...

FastAPI: http://localhost:8080
Next.js: http://localhost:3000

Ready for requests
```

---

### web doctor

Diagnose web development environment.

**Syntax:**

```bash
skillmeat web doctor
```

**Examples:**

```bash
skillmeat web doctor
```

**Output:**

```
Web Development Environment Check

Python:            ✓ 3.11.0
Node.js:           ✓ 18.14.2
npm/pnpm:          ✓ pnpm 7.31.0
FastAPI:           ✓ 0.104.1
Next.js:           ✓ 14.0.0
SQLite:            ✓ 3.44.0

Database:          ✓ Connected
Config:            ✓ Valid
Dependencies:      ✓ All installed

Status: Ready for development
```

---

### web generate-sdk

Generate TypeScript SDK from OpenAPI specification.

**Syntax:**

```bash
skillmeat web generate-sdk [OUTPUT_PATH] [OPTIONS]
```

**Arguments:**

- `OUTPUT_PATH` - Where to save generated SDK (default: ./sdk)

**Options:**

- `--api-url TEXT` - API URL for spec (default: http://localhost:8080)
- `--watch` - Regenerate on spec changes

**Examples:**

```bash
# Generate SDK
skillmeat web generate-sdk

# Custom output
skillmeat web generate-sdk ./src/generated

# Watch mode
skillmeat web generate-sdk --watch
```

**Output:**

```
Generating TypeScript SDK...

Fetching OpenAPI spec: http://localhost:8080/api/v1/openapi.json
Generating SDK types and client...
Generated: ./sdk
  - types/
  - client/
  - models/

Ready to import in your app!
```

---

### web token

Manage web authentication tokens.

**Syntax:**

```bash
skillmeat web token [OPTIONS] COMMAND [ARGS]...
```

**Commands:**

- `generate` - Generate new authentication token
- `list` - List active tokens
- `revoke TOKEN` - Revoke a token

**Examples:**

```bash
# Generate token
skillmeat web token generate

# List tokens
skillmeat web token list

# Revoke token
skillmeat web token revoke abc123
```

---

## MCP (Model Context Protocol) Servers

### mcp add

Add MCP server to collection.

**Syntax:**

```bash
skillmeat mcp add SPEC [OPTIONS]
```

**Arguments:**

- `SPEC` - GitHub path or local path to MCP server

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `-n, --name TEXT` - Override server name
- `--no-verify` - Skip validation

**Examples:**

```bash
# Add from GitHub
skillmeat mcp add anthropics/mcp/postgres-server

# Add from local
skillmeat mcp add ./my-mcp-server

# Custom name
skillmeat mcp add ./server --name my-server
```

---

### mcp list

List MCP servers in collection.

**Syntax:**

```bash
skillmeat mcp list [OPTIONS]
```

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `--deployed` - Show only deployed servers

**Examples:**

```bash
# List all MCP servers
skillmeat mcp list

# Show deployed only
skillmeat mcp list --deployed
```

**Output:**

```
MCP Servers

Name             Type      Status     Location
──────────────────────────────────────────────
postgres-server  database  ✓ Active   ~/.claude/mcp/postgres/
slack-server     messaging ✓ Active   ~/.claude/mcp/slack/
test-server      utility   ✗ Inactive ./my-server/
```

---

### mcp deploy

Deploy MCP server to Claude Desktop.

**Syntax:**

```bash
skillmeat mcp deploy NAME [OPTIONS]
```

**Arguments:**

- `NAME` - MCP server name

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `--backup` - Create backup before deploying

**Examples:**

```bash
# Deploy server
skillmeat mcp deploy postgres-server

# Deploy with backup
skillmeat mcp deploy postgres-server --backup
```

**Output:**

```
Deploying postgres-server...
  Added to Claude Desktop config
  Ready to use in Claude
```

---

### mcp undeploy

Remove MCP server from Claude Desktop.

**Syntax:**

```bash
skillmeat mcp undeploy NAME [OPTIONS]
```

**Arguments:**

- `NAME` - MCP server name

**Options:**

- `--backup` - Create backup before undeploying

**Examples:**

```bash
# Undeploy server
skillmeat mcp undeploy postgres-server

# With backup
skillmeat mcp undeploy postgres-server --backup
```

**Output:**

```
Undeployed postgres-server
  Removed from Claude Desktop config
```

---

### mcp health

Check health of deployed MCP servers.

**Syntax:**

```bash
skillmeat mcp health [NAME] [OPTIONS]
```

**Arguments:**

- `NAME` - Optional server name (checks all if omitted)

**Options:**

- `-t, --timeout INTEGER` - Health check timeout (default: 5)

**Examples:**

```bash
# Check all servers
skillmeat mcp health

# Check specific server
skillmeat mcp health postgres-server

# Custom timeout
skillmeat mcp health --timeout 10
```

**Output:**

```
MCP Server Health

postgres-server   ✓ Healthy   (response: 45ms)
slack-server      ✓ Healthy   (response: 120ms)
test-server       ✗ Offline

Status: 2/3 healthy
```

---

## Context Management

### context add

Add a context entity from a local file or GitHub URL.

**Syntax:**

```bash
skillmeat context add PATH [OPTIONS]
```

**Arguments:**

- `PATH` - Local file path or GitHub URL

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `-t, --type [spec|rule|config|context|template]` - Entity type
- `-cat, --category TEXT` - Category for organization
- `--auto-load` - Auto-load when deploying to projects

**Examples:**

```bash
# Add local spec
skillmeat context add ./.claude/specs/doc-policy.md --type spec

# Add rule
skillmeat context add ./.claude/rules/backend/api.md --type rule --category backend-rules

# Add from GitHub
skillmeat context add https://github.com/user/repo/rules/api.md

# Auto-load configuration
skillmeat context add ./CLAUDE.md --type config --auto-load
```

---

### context list

List all context entities with optional filtering.

**Syntax:**

```bash
skillmeat context list [OPTIONS]
```

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `-t, --type [spec|rule|config|context|template]` - Filter by type
- `-cat, --category TEXT` - Filter by category
- `--auto-load-only` - Show only auto-load entities

**Examples:**

```bash
# List all entities
skillmeat context list

# List specs only
skillmeat context list --type spec

# List backend rules
skillmeat context list --type rule --category backend-rules

# Show auto-load entities
skillmeat context list --auto-load-only
```

**Output:**

```
Context Entities (12)

Name                  Type     Category         Auto-Load  Size
──────────────────────────────────────────────────────────────
doc-policy-spec      spec     documentation    ✓          8.2 KB
api-rules             rule     backend-rules    ✓          15 KB
python-guide         rule     backend-rules             12 KB
CLAUDE.md            config   project                   6.5 KB
```

---

### context show

Show context entity details, metadata, and content.

**Syntax:**

```bash
skillmeat context show NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Entity name or ID

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `--head INTEGER` - Show first N lines (default: 50)

**Examples:**

```bash
# Show entity details
skillmeat context show doc-policy-spec

# Show full content
skillmeat context show api-rules --head 999

# Preview first 20 lines
skillmeat context show CLAUDE.md --head 20
```

**Output:**

```
doc-policy-spec

Type:          spec
Category:      documentation
Auto-load:     Yes
Size:          8.2 KB
Created:       2024-01-10
Modified:      2024-01-15

Content Preview:
─────────────────────────
# Documentation Policy

Only create documentation when explicitly tasked...
```

---

### context deploy

Deploy context entity to a project directory.

**Syntax:**

```bash
skillmeat context deploy NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Entity name

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `--to-project PATH` - Target project path (default: current directory)
- `--profile TEXT` - Deploy entity to a specific profile root
- `--all-profiles` - Deploy to all configured profile roots
- `--force` - Overwrite existing files

**Examples:**

```bash
# Deploy to current project
skillmeat context deploy doc-policy-spec

# Deploy to specific project
skillmeat context deploy api-rules --to-project ~/projects/backend

# Deploy to Gemini profile
skillmeat context deploy api-rules --to-project ~/projects/backend --profile gemini

# Deploy to all profiles
skillmeat context deploy doc-policy-spec --to-project ~/projects/backend --all-profiles

# Force overwrite
skillmeat context deploy CLAUDE.md --to-project ~/myapp --force
```

**Output:**

```
Deploying doc-policy-spec...
  Deployed to ~/projects/web-app/.claude/specs/doc-policy-spec.md
```

---

### context remove

Remove context entity from collection.

**Syntax:**

```bash
skillmeat context remove NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Entity name

**Options:**

- `-c, --collection TEXT` - Collection name (default: active)
- `--force` - Skip confirmation

**Examples:**

```bash
# Remove entity
skillmeat context remove old-spec

# Force remove
skillmeat context remove experimental-rule --force
```

**Output:**

```
Removed: old-spec
```

---

## Bundle Management

### bundle create

Create a new artifact bundle.

**Syntax:**

```bash
skillmeat bundle create NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Bundle name

**Options:**

- `-c, --collection TEXT` - Collection to bundle (default: active)
- `-f, --filter TEXT` - Filter artifacts (pattern)
- `--include-deps` - Include dependencies
- `--sign` - Sign the bundle
- `-o, --output PATH` - Output file path

**Examples:**

```bash
# Create bundle from collection
skillmeat bundle create my-bundle

# Bundle specific artifacts
skillmeat bundle create backend-bundle --filter "skill"

# Create with signature
skillmeat bundle create my-bundle --sign

# Custom output
skillmeat bundle create my-bundle --output ./builds/
```

**Output:**

```
Creating bundle...

Bundle: my-bundle.skillmeat-pack
  Artifacts: 12
  Size: 2.4 MB
  Signature: Signed with john@example.com

Ready to share!
```

---

### bundle inspect

Inspect a bundle file.

**Syntax:**

```bash
skillmeat bundle inspect BUNDLE_PATH [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file

**Options:**

- `--json` - Output as JSON

**Examples:**

```bash
# Inspect bundle
skillmeat bundle inspect my-bundle.skillmeat-pack

# Get JSON output
skillmeat bundle inspect my-bundle.skillmeat-pack --json
```

**Output:**

```
Bundle: my-bundle.skillmeat-pack

Metadata:
  Created: 2024-01-15
  Author: john@example.com
  Version: 1.0.0

Signature: ✓ Valid
  Key ID: abc123

Contents:
  Skills:    8
  Commands:  3
  Agents:    1
  Total:     12 artifacts

Total Size: 2.4 MB
```

---

### bundle import

Import artifact bundle into collection.

**Syntax:**

```bash
skillmeat bundle import BUNDLE_PATH [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file

**Options:**

- `-c, --collection TEXT` - Target collection (default: active)
- `--strategy [merge|overwrite|skip]` - Conflict strategy (default: merge)
- `--verify-signature` - Verify bundle signature

**Examples:**

```bash
# Import bundle
skillmeat bundle import my-bundle.skillmeat-pack

# Import with conflict resolution
skillmeat bundle import my-bundle.skillmeat-pack --strategy overwrite

# Verify signature
skillmeat bundle import my-bundle.skillmeat-pack --verify-signature
```

**Output:**

```
Importing bundle...

Imported 12 artifacts:
  Skills:    8 ✓
  Commands:  3 ✓
  Agents:    1 ✓

Conflicts resolved: 2
  canvas: Merged changes
  pdf-reader: Kept local version
```

---

## Vault Management

### vault add

Add a new vault configuration.

**Syntax:**

```bash
skillmeat vault add NAME TYPE LOCATION [OPTIONS]
```

**Arguments:**

- `NAME` - Vault identifier
- `TYPE` - Vault type (git, s3, fs)
- `LOCATION` - Vault location (URL or path)

**Options:**

- `--set-default` - Make default vault

**Examples:**

```bash
# Add Git vault
skillmeat vault add team-vault git git@github.com:team/vault.git

# Add S3 vault
skillmeat vault add prod-vault s3 s3://my-bucket/artifacts

# Add local filesystem
skillmeat vault add local-vault fs /data/vault
```

**Output:**

```
Vault 'team-vault' added
  Type: git
  Location: git@github.com:team/vault.git
```

---

### vault list

List all configured vaults.

**Syntax:**

```bash
skillmeat vault list
```

**Examples:**

```bash
skillmeat vault list
```

**Output:**

```
Vaults

Name          Type   Location                        Default
───────────────────────────────────────────────────────────────
team-vault    git    git@github.com:team/vault.git   ✓
prod-vault    s3     s3://my-bucket/artifacts
local-vault   fs     /data/vault
```

---

### vault push

Upload bundle to team vault.

**Syntax:**

```bash
skillmeat vault push BUNDLE_PATH [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file

**Options:**

- `--vault NAME` - Target vault (default: default)
- `--tag TEXT` - Tag bundle version

**Examples:**

```bash
# Push to default vault
skillmeat vault push my-bundle.skillmeat-pack

# Push to specific vault
skillmeat vault push my-bundle.skillmeat-pack --vault prod-vault

# With version tag
skillmeat vault push my-bundle.skillmeat-pack --tag v1.0.0
```

**Output:**

```
Uploading to team-vault...
my-bundle.skillmeat-pack [100%]
Pushed successfully!
```

---

### vault pull

Download bundle from team vault.

**Syntax:**

```bash
skillmeat vault pull BUNDLE_NAME [OPTIONS]
```

**Arguments:**

- `BUNDLE_NAME` - Bundle name or ID

**Options:**

- `--vault NAME` - Source vault (default: default)
- `-o, --output PATH` - Output path (default: current dir)

**Examples:**

```bash
# Pull from default vault
skillmeat vault pull my-bundle

# Pull from specific vault
skillmeat vault pull my-bundle --vault team-vault

# Save to location
skillmeat vault pull my-bundle --output ./bundles/
```

**Output:**

```
Downloading from team-vault...
my-bundle [100%]
Downloaded to: ./my-bundle.skillmeat-pack
```

---

### vault ls

List bundles in team vault.

**Syntax:**

```bash
skillmeat vault ls [OPTIONS]
```

**Options:**

- `--vault NAME` - Vault to list (default: default)

**Examples:**

```bash
skillmeat vault ls
skillmeat vault ls --vault prod-vault
```

**Output:**

```
Bundles in team-vault

Name                  Version  Date       Size
─────────────────────────────────────────────
my-bundle             1.0.0    2024-01-15  2.4 MB
backend-tools         2.1.0    2024-01-10  5.2 MB
shared-skills         1.5.0    2024-01-05  1.8 MB
```

---

### vault remove

Remove a vault configuration.

**Syntax:**

```bash
skillmeat vault remove NAME [OPTIONS]
```

**Arguments:**

- `NAME` - Vault name

**Options:**

- `--force` - Skip confirmation

**Examples:**

```bash
skillmeat vault remove old-vault
skillmeat vault remove test-vault --force
```

---

### vault set-default

Set default vault for push/pull operations.

**Syntax:**

```bash
skillmeat vault set-default NAME
```

**Arguments:**

- `NAME` - Vault name

**Examples:**

```bash
skillmeat vault set-default team-vault
```

**Output:**

```
Default vault set to: team-vault
```

---

### vault auth

Configure authentication for a vault.

**Syntax:**

```bash
skillmeat vault auth VAULT_NAME [OPTIONS]
```

**Arguments:**

- `VAULT_NAME` - Vault name

**Options:**

- `--type [ssh|https|token|s3-creds]` - Auth type
- `--key PATH` - SSH key path
- `--token TEXT` - Auth token

**Examples:**

```bash
# Configure SSH auth
skillmeat vault auth team-vault --type ssh --key ~/.ssh/id_rsa

# Configure token auth
skillmeat vault auth team-vault --type token --token ghp_xxxxx
```

**Output:**

```
Authentication configured for team-vault
```

---

## Bundle Signing

### sign generate-key

Generate a new Ed25519 signing key pair.

**Syntax:**

```bash
skillmeat sign generate-key [OPTIONS]
```

**Options:**

- `-n, --name TEXT` - Key owner name (required)
- `-e, --email TEXT` - Key owner email (required)
- `--force` - Overwrite existing key

**Examples:**

```bash
skillmeat sign generate-key --name "John Doe" --email "john@example.com"
```

**Output:**

```
Generated signing key pair
  Name: John Doe
  Email: john@example.com
  Key ID: abc123def456
  Location: ~/.skillmeat/keys/abc123def456
```

---

### sign list-keys

List all signing and trusted keys.

**Syntax:**

```bash
skillmeat sign list-keys [OPTIONS]
```

**Options:**

- `--trusted` - Show only trusted keys
- `--own` - Show only your own keys

**Examples:**

```bash
skillmeat sign list-keys
skillmeat sign list-keys --trusted
skillmeat sign list-keys --own
```

**Output:**

```
Signing Keys

Key ID           Name             Email
──────────────────────────────────────────
abc123def456     John Doe         john@example.com

Trusted Keys

Key ID           Name             Email
──────────────────────────────────────────
xyz789abc123     Jane Smith       jane@example.com
```

---

### sign export-key

Export public key for sharing.

**Syntax:**

```bash
skillmeat sign export-key KEY_ID [OPTIONS]
```

**Arguments:**

- `KEY_ID` - Key identifier

**Options:**

- `-o, --output PATH` - Output file path (default: stdout)

**Examples:**

```bash
skillmeat sign export-key abc123def456
skillmeat sign export-key abc123def456 --output my-key.pub
```

---

### sign import-key

Import a trusted public key.

**Syntax:**

```bash
skillmeat sign import-key KEY_PATH [OPTIONS]
```

**Arguments:**

- `KEY_PATH` - Path to public key file

**Examples:**

```bash
skillmeat sign import-key ./jane-key.pub
```

**Output:**

```
Imported trusted key
  Name: Jane Smith
  Email: jane@example.com
  Key ID: xyz789abc123
```

---

### sign verify

Verify bundle signature.

**Syntax:**

```bash
skillmeat sign verify BUNDLE_PATH
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file

**Examples:**

```bash
skillmeat sign verify my-bundle.skillmeat-pack
```

**Output:**

```
Bundle signature: ✓ Valid

Signed by: John Doe (john@example.com)
Key ID: abc123def456
Signed: 2024-01-15 10:30:00
```

---

### sign revoke

Revoke a signing or trusted key.

**Syntax:**

```bash
skillmeat sign revoke KEY_ID [OPTIONS]
```

**Arguments:**

- `KEY_ID` - Key identifier

**Options:**

- `--force` - Skip confirmation

**Examples:**

```bash
skillmeat sign revoke abc123def456
skillmeat sign revoke xyz789abc123 --force
```

---

## Marketplace

### marketplace-search

Search marketplace for artifact bundles.

**Syntax:**

```bash
skillmeat marketplace-search [QUERY] [OPTIONS]
```

**Arguments:**

- `QUERY` - Search query (optional)

**Options:**

- `-b, --broker TEXT` - Specific broker to search (default: all)
- `-t, --tags TEXT` - Filter by tags (comma-separated)
- `-l, --license TEXT` - Filter by license
- `-p, --page INTEGER` - Page number (default: 1)
- `-s, --page-size INTEGER` - Results per page (default: 20)

**Examples:**

```bash
# Search all brokers
skillmeat marketplace-search python

# Search specific broker
skillmeat marketplace-search --broker skillmeat "code review"

# Filter by tags and license
skillmeat marketplace-search --tags productivity --license MIT

# Pagination
skillmeat marketplace-search python --page 2 --page-size 50
```

**Output:**

```
Marketplace Results (156 bundles)

Name                  Author       Stars  Tags                Version
──────────────────────────────────────────────────────────────────
python-tools          anthropic    345    python,tools       v1.5.0
py-analyzer           john-dev     128    analysis,coding    v2.0.0
py-formatter          alex-tools   92     formatting         v1.2.0

[Page 1 of 8]
```

---

### marketplace-install

Install bundle from marketplace.

**Syntax:**

```bash
skillmeat marketplace-install BUNDLE_ID [OPTIONS]
```

**Arguments:**

- `BUNDLE_ID` - Bundle identifier

**Options:**

- `-c, --collection TEXT` - Target collection (default: active)

**Examples:**

```bash
skillmeat marketplace-install python-tools
skillmeat marketplace-install python-tools --collection work
```

**Output:**

```
Installing from marketplace...

python-tools (v1.5.0)
  Importing 12 artifacts...
  Configuring dependencies...

Installed successfully!
```

---

### marketplace-publish

Publish bundle to marketplace.

**Syntax:**

```bash
skillmeat marketplace-publish BUNDLE_PATH [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file

**Options:**

- `--title TEXT` - Bundle title
- `--description TEXT` - Bundle description
- `--tags TEXT` - Tags (comma-separated)
- `--license TEXT` - License type
- `--public` - Make publicly available

**Examples:**

```bash
skillmeat marketplace-publish my-bundle.skillmeat-pack --title "My Tools" --public
```

**Output:**

```
Publishing to marketplace...

Bundle published!
  ID: my-bundle-abc123
  URL: https://marketplace.skillmeat.io/bundles/my-bundle-abc123
```

---

## Compliance

### compliance-scan

Scan bundle for license compliance.

**Syntax:**

```bash
skillmeat compliance-scan BUNDLE_PATH [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file

**Options:**

- `--strict` - Fail on warnings (not just errors)
- `--json` - Output as JSON

**Examples:**

```bash
skillmeat compliance-scan my-bundle.skillmeat-pack
skillmeat compliance-scan my-bundle.skillmeat-pack --strict
```

**Output:**

```
License Compliance Scan

Bundle: my-bundle.skillmeat-pack
Artifacts: 12

Licenses Found:
  MIT              8 artifacts ✓
  Apache-2.0       3 artifacts ✓
  Unknown          1 artifact  ⚠

Conflicts: None detected ✓

Status: PASS
```

---

### compliance-checklist

Generate compliance checklist for bundle.

**Syntax:**

```bash
skillmeat compliance-checklist BUNDLE_PATH [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file

**Options:**

- `-o, --output PATH` - Output file path

**Examples:**

```bash
skillmeat compliance-checklist my-bundle.skillmeat-pack
skillmeat compliance-checklist my-bundle.skillmeat-pack --output checklist.md
```

**Output:**

```
Compliance Checklist

Bundle: my-bundle.skillmeat-pack

- [x] License headers present
- [x] Copyright notices documented
- [x] No conflicting licenses
- [x] Dependencies validated
- [x] Code review approved

Status: Ready for release
```

---

### compliance-consent

Record compliance consent for checklist.

**Syntax:**

```bash
skillmeat compliance-consent BUNDLE_PATH [CONSENT_LEVEL]
```

**Arguments:**

- `BUNDLE_PATH` - Path to bundle file
- `CONSENT_LEVEL` - Consent level (approved/conditional/rejected)

**Options:**

- `--notes TEXT` - Consent notes

**Examples:**

```bash
skillmeat compliance-consent my-bundle.skillmeat-pack approved
skillmeat compliance-consent my-bundle.skillmeat-pack conditional --notes "Requires legal review"
```

**Output:**

```
Consent recorded
  Bundle: my-bundle.skillmeat-pack
  Level: approved
  Date: 2024-01-15
```

---

### compliance-history

View compliance consent history.

**Syntax:**

```bash
skillmeat compliance-history [BUNDLE_PATH] [OPTIONS]
```

**Arguments:**

- `BUNDLE_PATH` - Optional bundle path (shows all if omitted)

**Examples:**

```bash
skillmeat compliance-history
skillmeat compliance-history my-bundle.skillmeat-pack
```

**Output:**

```
Compliance History

Bundle                Date        Reviewer    Level      Notes
──────────────────────────────────────────────────────────────
my-bundle             2024-01-15  John Doe    approved
backend-tools         2024-01-10  Jane Smith  approved   Legal cleared
shared-skills         2024-01-05  Admin       approved
```

---

## Project Operations

### project sync-context

Synchronize context entities between project and collection.

**Syntax:**

```bash
skillmeat project sync-context [PROJECT_PATH] [OPTIONS]
```

**Arguments:**

- `PROJECT_PATH` - Project directory (default: current)

**Options:**

- `-c, --collection TEXT` - Source collection (default: active)
- `--direction [pull|push|both]` - Sync direction (default: both)

**Examples:**

```bash
# Sync context in current directory
skillmeat project sync-context

# Sync specific project
skillmeat project sync-context ~/myproject

# Pull only from collection
skillmeat project sync-context --direction pull

# Push only to collection
skillmeat project sync-context --direction push
```

**Output:**

```
Syncing context...

Pulled from collection:
  doc-policy-spec        ✓
  backend-rules          ✓

Project context in sync!
```

---

## Migration

### migrate

Migrate from skillman to skillmeat.

**Syntax:**

```bash
skillmeat migrate [OPTIONS]
```

**Options:**

- `--from PATH` - skillman collection path
- `--to PATH` - Target skillmeat path (default: ~/.skillmeat)

**Examples:**

```bash
skillmeat migrate
skillmeat migrate --from ~/.skillman --to ~/.skillmeat
```

**Output:**

```
Migrating from skillman...

Artifacts migrated: 23
Collections: 3
Success!
```

---

## Special Commands

### active-collection

View or switch active collection.

**Syntax:**

```bash
skillmeat active-collection [NAME]
```

**Arguments:**

- `NAME` - Collection name to switch to (optional)

**Examples:**

```bash
# Show active collection
skillmeat active-collection

# Switch collection
skillmeat active-collection work
```

**Output:**

```
Active collection: work
```

---

### quick-add

Add artifact with smart defaults (claudectl mode).

**Syntax:**

```bash
skillmeat quick-add SPEC [OPTIONS]
```

**Arguments:**

- `SPEC` - Artifact spec (GitHub or local)

**Options:**

- `-c, --collection TEXT` - Collection (default: active)
- `--infer-type` - Auto-detect artifact type

**Examples:**

```bash
skillmeat quick-add anthropics/skills/canvas
skillmeat quick-add ./my-skill --infer-type
```

---

### alias

Manage claudectl alias and shell integration.

**Syntax:**

```bash
skillmeat alias [OPTIONS] COMMAND [ARGS]...
```

**Commands:**

- `install` - Install shell alias and completion
- `uninstall` - Remove alias and completion

**Examples:**

```bash
skillmeat alias install
skillmeat alias uninstall
```

---

## Security

SkillMeat displays security warnings before installing artifacts from any source. Artifacts can:

- Execute code
- Access system resources
- Read, create, and modify files
- Execute system commands

**Best Practices:**

- Only install from trusted sources
- Review artifacts before installation
- Use `verify` command to inspect artifacts
- Never use `--dangerously-skip-permissions` for untrusted sources

For more information: [Using Skills in Claude - Security](https://support.claude.com/en/articles/12512180-using-skills-in-claude#h_2746475e70)
