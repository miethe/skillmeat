# SkillMeat Command Reference

Complete reference for all SkillMeat CLI commands.

## Table of Contents

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
- [Updates & Status](#updates--status)
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
- [Utilities](#utilities)
  - [verify](#verify)

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
