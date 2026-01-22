---
title: Collection Refresh and Rollback Guide
description: How to refresh artifact metadata from GitHub sources and safely rollback changes using snapshots
audience: users
tags:
  - collection-refresh
  - snapshots
  - metadata
  - rollback
  - github
  - artifact-management
created: "2026-01-22"
updated: "2026-01-22"
category: user-guides
status: current
related_documents:
  - docs/user/guides/updating-safely.md
  - docs/user/guides/syncing-changes.md
  - docs/user/cli/commands.md
---

# Collection Refresh and Rollback Guide

Learn how to refresh artifact metadata from GitHub sources and safely restore previous versions using automatic snapshots.

## What is Collection Refresh?

Collection Refresh updates artifact metadata (like descriptions, tags, authors, and licenses) from upstream GitHub sources. Unlike full updates, refresh operations:

- **Only update metadata**, not artifact version or content
- **Work in dry-run mode** to preview changes before applying
- **Create automatic snapshots** for easy rollback if needed
- **Support filtering** by type, name, or specific fields

This is ideal for keeping collection artifacts current without triggering full version updates.

## When to Use Refresh

Use collection refresh when:

- Your imported artifacts have outdated descriptions or tags
- GitHub repository metadata changed (new license, added topics)
- Multiple artifacts need metadata updates at once
- You want to preview changes before applying them

Do NOT use refresh for:

- Updating artifact version or code content (use `skillmeat update` instead)
- Handling merge conflicts
- Managing local modifications to artifacts

See [Updating Artifacts Safely](updating-safely.md) for full version updates.

## How Snapshots Work

SkillMeat automatically creates snapshots at key moments:

### Automatic Snapshots During Refresh

When you run a refresh operation without `--dry-run`, the system:

1. **Detects changes** before applying them
2. **Creates a snapshot** with timestamp if changes exist
3. **Applies the refresh** to your collection
4. **Logs the snapshot ID** so you can reference it later

This means every refresh operation that makes changes is automatically protected by a snapshot.

### Manual Snapshots

You can also create manual snapshots anytime:

```bash
# Create a snapshot with custom message
skillmeat snapshot "Before major refresh"

# Create with default message
skillmeat snapshot
```

### How Snapshots Store Data

Snapshots are complete point-in-time copies of your collection:

- All artifacts and their metadata
- All versions and content
- Exact state at snapshot creation time
- Immutable (cannot be modified)

They're stored in your SkillMeat data directory and don't affect your current collection size.

## Basic Workflow: Refresh → Verify → Rollback if Needed

### Step 1: Preview Changes

Always preview refresh changes before applying:

```bash
# Dry-run to see what will change
skillmeat collection refresh --dry-run

# Output shows:
# Refresh Summary
# Metric          Count
# ────────────────────
# Refreshed       3
# Unchanged       5
# Skipped         2
# Errors          0
#
# Changed Artifacts:
#   ✓ python-skill
#     description: [old]... → [new]...
#     tags: skill, python → skill, python, automation
#
#   ✓ canvas-design
#     license: MIT → Apache-2.0
```

This shows exactly what will change without modifying your collection.

### Step 2: Apply Refresh

Once satisfied with changes:

```bash
# Apply the refresh (creates snapshot automatically)
skillmeat collection refresh

# Output confirms changes applied:
# Refresh Summary
# Metric          Count
# ────────────────────
# Refreshed       3
# Unchanged       5
# Skipped         2
# Errors          0
# Duration: 234.56ms
```

### Step 3: Verify Results

Test the refreshed artifacts:

```bash
# List artifacts to verify metadata updated
skillmeat list

# Export artifact to check details
skillmeat show artifact-name

# View in web interface for visual confirmation
skillmeat web dev
```

### Step 4: Rollback if Issues Occur

If refreshed metadata causes problems, restore the previous snapshot:

```bash
# List available snapshots
skillmeat history

# Output shows:
# Snapshots for 'default' (5)
# ID        Created                Message
# ──────────────────────────────────────────
# xyz789a   2026-01-22 14:30:00  (auto)
# abc123d   2026-01-21 09:15:00  Before major refresh
# def456e   2026-01-20 16:45:00  Backup

# Rollback to previous snapshot
skillmeat rollback xyz789a

# Confirm when prompted:
# Warning: This will replace collection 'default' with snapshot 'xyz789a'
# Continue with rollback? [y/N]: y

# Output confirms restoration:
# Rolling back to snapshot xyz789a...
# ✓ Restored collection from snapshot
```

## Filtering Refresh Operations

Refresh specific artifacts to avoid updating everything at once:

### By Artifact Type

```bash
# Refresh only skills
skillmeat collection refresh --type skill

# Refresh only commands
skillmeat collection refresh --type command

# Refresh only MCP servers
skillmeat collection refresh --type mcp-server
```

Valid types: `skill`, `command`, `agent`, `mcp-server`, `hook`

### By Name Pattern

```bash
# Refresh artifacts matching pattern
skillmeat collection refresh --name "canvas-*"

# Refresh artifacts containing "python"
skillmeat collection refresh --name "*python*"

# Pattern uses glob syntax (*, ?, [abc])
```

### By Specific Fields

```bash
# Refresh only descriptions (skip tags, license, etc.)
skillmeat collection refresh --fields description

# Refresh multiple specific fields
skillmeat collection refresh --fields description,tags,author

# Valid fields: description, tags, author, license, origin_source
```

### Combine Filters

```bash
# Refresh only skill tags
skillmeat collection refresh --type skill --fields tags

# Refresh canvas artifacts, all fields
skillmeat collection refresh --name "canvas-*"

# Refresh all agent author fields
skillmeat collection refresh --type agent --fields author
```

## Advanced Operations

### Check for Available Updates Only

Find what would refresh without making changes:

```bash
# See what could refresh
skillmeat collection refresh --check

# Output shows summary of changes available
```

### Check Version Updates (Without Metadata)

For faster version-only checks:

```bash
# Compare versions against upstream
skillmeat collection refresh --check-only

# Output:
# Update Check Summary
# Artifact          Current SHA    Upstream SHA   Update Available
# ─────────────────────────────────────────────────────────────
# python            abc123...      def456...      Yes
# canvas            xyz789...      xyz789...      No
```

Exit code indicates availability:
- `0` = No updates available
- `2` = Updates available
- `1` = Error occurred

Useful for automation and scripting.

### Refresh Specific Collection

By default, refresh uses your active collection:

```bash
# Specify different collection
skillmeat collection refresh --collection work

# Refresh default explicitly
skillmeat collection refresh --collection default
```

## Understanding Snapshot Messages

Snapshots can have different messages:

| Message | Meaning |
|---------|---------|
| `(auto)` | Created automatically by a refresh operation |
| `Before major refresh` | Custom message you provided |
| `Manual snapshot` | Created with `skillmeat snapshot` (no message) |

Use custom messages for important milestones:

```bash
# Create snapshot with meaningful message
skillmeat snapshot "Before field standardization"

# Now when rolling back, you'll recognize it
skillmeat history
# Before field standardization   2026-01-22 10:00:00
```

## Troubleshooting

### "No snapshots found"

**Problem**: Can't rollback because no snapshots exist

**Solution**:
```bash
# Create snapshot first
skillmeat snapshot "Safe point"

# Then you can rollback later
skillmeat rollback <snapshot_id>
```

### Refresh Skips Artifacts (No GitHub Source)

**Problem**: Some artifacts show "Skipped" status

**Output**: `Skipped: No GitHub source`

**Meaning**: Artifacts were added locally, not from GitHub

**Solution**:
```bash
# Check artifact source
skillmeat show artifact-name

# If local source, either:
# Option 1: Re-add from GitHub
skillmeat remove artifact-name
skillmeat add skill github-user/repo/path/artifact

# Option 2: Manually update metadata
# Edit artifact directly in .skillmeat collection directory
```

### Refresh Errors for Specific Artifacts

**Problem**: Some artifacts have errors, others succeed

**Solution**:
```bash
# Refresh is fault-tolerant - it continues on errors
# Check which ones failed (shown in red in output)

# Try refreshing just the failed artifacts
skillmeat collection refresh --name failed-artifact-name

# If still fails:
# 1. Check repository still exists on GitHub
# 2. Verify GitHub authentication configured
# 3. Check rate limit hasn't been exceeded
```

### Rate Limit Hit During Refresh

**Problem**: Refresh stops with "Rate limit exceeded"

**Solution**:
```bash
# Option 1: Add GitHub authentication
skillmeat config set github-token ghp_xxxxxxxxxxxx

# Option 2: Wait for rate limit reset (usually 1 hour)
# Check rate limit status:
skillmeat config get github-rate-limit

# Option 3: Refresh smaller batches
skillmeat collection refresh --type skill
# Wait...
skillmeat collection refresh --type command
```

See [GitHub Authentication Guide](github-authentication.md) for setup details.

### Rollback Doesn't Restore All Data

**Problem**: After rollback, some data seems different

**Verify**:
```bash
# List artifacts to verify count
skillmeat list

# Show specific artifact
skillmeat show artifact-name

# If still wrong, check which snapshot you rolled back to
skillmeat history
```

**Root causes**:
- Rolled back to wrong snapshot ID
- Changes made after snapshot was created
- Rollback completed successfully but display hasn't refreshed

**Solution**:
```bash
# Always list history first to pick correct snapshot
skillmeat history --limit 20

# ID and timestamp help identify correct snapshot
# Rollback to different snapshot if needed
skillmeat rollback different-snapshot-id
```

## Best Practices

### 1. Always Dry-Run First

```bash
# Good: Preview before applying
skillmeat collection refresh --dry-run
# Review output...
skillmeat collection refresh

# Bad: Apply without checking
skillmeat collection refresh  # Too risky!
```

### 2. Use Meaningful Snapshot Messages

```bash
# Meaningful
skillmeat snapshot "Before standardizing Python descriptions"

# Less useful
skillmeat snapshot
```

### 3. Create Snapshots Before Bulk Changes

```bash
# Before major refresh operations
skillmeat snapshot "Pre-bulk-refresh"
skillmeat collection refresh

# Before testing experimental updates
skillmeat snapshot "Before experiment"
skillmeat collection refresh --type skill
```

### 4. Keep Your Snapshots Organized

```bash
# View recent snapshots
skillmeat history --limit 10

# Use consistent naming conventions
skillmeat snapshot "Milestone: Q1 cleanup"
skillmeat snapshot "Backup: Before integration"
```

### 5. Verify After Refresh

```bash
# Always spot-check after refresh
skillmeat show important-artifact

# Verify metadata looks correct
# Test deployments if applicable

# Only then delete old snapshots if confident
```

### 6. Use Filters for Large Collections

```bash
# Refresh in batches rather than all at once
skillmeat collection refresh --type skill
skillmeat collection refresh --type command
skillmeat collection refresh --type agent

# Easier to identify issues and rollback one type
```

## Common Refresh Scenarios

### Scenario 1: Update All Metadata

Refresh everything:

```bash
skillmeat collection refresh --dry-run
# Review changes...
skillmeat collection refresh
```

### Scenario 2: Update Tags Only

Keep other metadata, update only tags:

```bash
skillmeat collection refresh --fields tags --dry-run
skillmeat collection refresh --fields tags
```

### Scenario 3: Fix Broken License Info

Some artifacts have outdated license metadata:

```bash
# Refresh licenses only
skillmeat collection refresh --fields license --dry-run

# If good...
skillmeat collection refresh --fields license

# If something breaks...
skillmeat rollback <snapshot_id>
```

### Scenario 4: Batch Update by Type

Update skills while keeping other types unchanged:

```bash
# Create safety snapshot first
skillmeat snapshot "Before skill refresh"

# Refresh only skills
skillmeat collection refresh --type skill --dry-run
skillmeat collection refresh --type skill

# Can rollback just this batch if needed
skillmeat rollback <snapshot_id>
```

### Scenario 5: Emergency Rollback

Production collection broke, need immediate restore:

```bash
# List snapshots to find last known good state
skillmeat history --limit 5

# Get the ID of last good snapshot
# Rollback immediately with --yes to skip prompt
skillmeat rollback abc123d --yes

# Verify
skillmeat list
skillmeat show critical-artifact
```

## How Refresh Differs from Update

| Aspect | Refresh | Update |
|--------|---------|--------|
| **Scope** | Metadata only | Full version + content |
| **Fields Changed** | Description, tags, author, license | Code, structure, everything |
| **Use Case** | Keep metadata current | Install new versions |
| **Merge Strategy** | Not applicable | Has conflict handling |
| **Breaking Changes** | Very rare | Possible |
| **Typical Change** | Few fields | Entire artifact |
| **Safe for Batch** | Yes | Case-by-case |

Use `skillmeat collection refresh` for metadata, `skillmeat update` for new versions.

See [Updating Artifacts Safely](updating-safely.md) for version update details.

## See Also

- [Updating Artifacts Safely](updating-safely.md) - Full version updates with merge strategies
- [GitHub Authentication Guide](github-authentication.md) - Configure GitHub access
- [Searching for Artifacts](searching.md) - Find artifacts to refresh
- [Using Analytics & Insights](using-analytics.md) - Track changes over time
- [CLI Commands Reference](../cli/commands.md) - Full command details

## Related Guides

- [Syncing Changes](syncing-changes.md) - Sync artifacts across projects
- [Managing Collections](../guides/managing-collections.md) - Collection operations
- [Tags Developer Guide](tags-developer-guide.md) - Understanding metadata fields
