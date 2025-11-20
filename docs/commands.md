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
  - [Security](#security)

---

## Core Commands

### init

Initialize a new collection.

**Syntax:**

```bash
skillmeat init [--name NAME]
```

**Options:**

- `-n, --name TEXT` - Collection name (default: 'default')

**Examples:**

```bash
# Create default collection
skillmeat init

# Create named collection
skillmeat init --name work
```

**Output:**

```
Collection 'default' initialized
  Location: /home/user/.skillmeat/collections/default
  Artifacts: 0
```

**Notes:**

- Creates collection directory structure
- Initializes empty collection.toml manifest
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

Deploy artifacts to a project's .claude/ directory.

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

- Creates `.claude/` directory if it doesn't exist
- Creates deployment tracking file `.skillmeat-deployed.toml`
- Preserves artifact structure (skills as directories, commands as files)

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

**Examples:**

```bash
# Check collection update status
skillmeat status

# Check specific collection
skillmeat status --collection work

# Check deployment status for project
skillmeat status --project /path/to/project
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
