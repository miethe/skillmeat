# Updating Artifacts Safely Guide

Learn how to update artifacts from upstream sources safely with preview, diff, and merge conflict handling.

## Overview

SkillMeat provides safe update workflows to help you keep artifacts current while handling local modifications:

- **Preview Changes**: See what will change before applying updates
- **Understand Diffs**: View detailed differences between versions
- **Multiple Strategies**: Choose how to handle conflicts (prompt, overwrite, or keep local)
- **Automatic Snapshots**: Rollback to previous versions if needed
- **Merge Conflict Detection**: Identify conflicts before they break things

## Prerequisites

- SkillMeat installed and configured
- At least one artifact in a collection
- Artifacts with upstream sources (GitHub) can be updated

## Update Workflow Overview

The recommended update workflow follows these steps:

```
1. Check Update Status  (skillmeat status)
    ↓
2. Preview Changes      (skillmeat diff artifact --upstream)
    ↓
3. Review Differences   (examine output carefully)
    ↓
4. Apply Update         (skillmeat update artifact)
    ↓
5. Verify Results       (test the updated artifact)
```

## Step 1: Check Update Status

Start by seeing which artifacts have available updates:

```bash
# Check for available updates
skillmeat status

# Output shows:
# Updates available (2):
#   python (skill): v2.0.0 -> v2.1.0
#   review (command): abc123 -> def456
#
# Up to date (3):
#   canvas (skill)
#   ...
```

This tells you:
- Which artifacts have newer versions upstream
- Current vs. available versions
- Artifacts that are already up to date

## Step 2: Preview Changes

Before updating, preview what will change:

### View Artifact Diff

```bash
# Compare artifact against upstream version
skillmeat diff artifact canvas --upstream

# Output shows:
# Directory Comparison
#   Files added:     1
#   Files removed:   0
#   Files modified:  2
#
# Modified Files:
#   M canvas.py (15 additions, 8 deletions)
#   M README.md (3 additions, 1 deletion)
#   + styles.css (new file)
```

### View Detailed File Diffs

```bash
# Get detailed context around changes
skillmeat diff artifact canvas --upstream --context 5

# Shows unified diff format with more context
```

### Compare Against Previous Version

```bash
# See what changed since last version
skillmeat diff artifact python --previous

# Useful for understanding evolution of artifact
```

### Export Statistics Only

```bash
# Just see the numbers, not full diff
skillmeat diff artifact pdf-extractor --upstream --stats-only

# Output:
# Files added:     2
# Files removed:   1
# Files modified:  4
# Lines added:     142
# Lines removed:   45
```

## Step 3: Review Differences

When examining diffs, look for:

### Breaking Changes

Signs that an update might break things:

```diff
- def authenticate(user_id):
+ def authenticate(user_id, options=None):
    # New required parameter structure

- legacy_config = load_config()
+ config = load_config(format="json")
    # API changes

+ from new_module import dependency
  # New dependencies added
```

### Behavioral Changes

Watch for logic changes:

```diff
- if error:
-     raise Exception(error)
+ if error:
+     return None
    # Changed error handling
```

### Version Compatibility

Check for version requirements:

```diff
  # SKILL.md
+ Requires: SkillMeat >= 1.2.0
+ Python >= 3.10
```

### Migration Guide

Look for migration notes:

```diff
+ ## Migration from v1 to v2
+ 1. Update configuration format
+ 2. Re-run initialization
+ 3. Verify deployments
```

## Step 4: Apply Update

Once you've reviewed the changes, apply the update:

### Interactive Update (Default)

```bash
# Update with prompt
skillmeat update canvas

# Shows:
# Version 1.0.0 -> 1.2.3
#
# Changes:
#   + feature-detection.py
#   M canvas.md (15 additions, 3 deletions)
#   M utils.py (7 additions, 12 deletions)
#
# Apply changes? [y/N]:
```

This is the safest option - you review before accepting.

### Force Upstream Version

```bash
# Replace with upstream version (discard local changes)
skillmeat update canvas --strategy upstream

# Use when:
# - Upstream is authoritative
# - Local changes are unimportant
# - You want clean version
```

### Keep Local Version

```bash
# Skip update, keep local version
skillmeat update canvas --strategy local

# Use when:
# - You have critical local changes
# - Upstream might break your setup
# - You want to manually merge later
```

## Understanding Merge Strategies

### Strategy 1: `prompt` (Default)

**Best for**: Most situations

```bash
skillmeat update artifact --strategy prompt
```

**Behavior**:
- Shows changes before applying
- Asks for confirmation
- You can review and decide
- Safest option

**Use when**:
- You're unsure about changes
- Artifact has local modifications
- Want human review of changes

### Strategy 2: `upstream`

**Best for**: Authoritative upstream sources

```bash
skillmeat update artifact --strategy upstream
```

**Behavior**:
- Automatically accepts upstream version
- Overwrites local modifications
- No prompts or confirmation
- Fast and clean

**Use when**:
- Upstream is the source of truth
- Local changes are temporary/disposable
- You trust the source completely

### Strategy 3: `local`

**Best for**: Custom modifications

```bash
skillmeat update artifact --strategy local
```

**Behavior**:
- Skips update entirely
- Keeps local version unchanged
- Useful for marking as "do not update"
- Allows manual merge later

**Use when**:
- You have critical customizations
- Upstream changes might conflict
- You want to manually merge later

## Handling Merge Conflicts

When local and upstream both have conflicting changes, SkillMeat uses Git-style conflict markers:

### Conflict Example

```python
<<<<<<< LOCAL
def process_data(data):
    """Process with old algorithm"""
    return old_algorithm(data)
=======
def process_data(data):
    """Process with new algorithm"""
    return new_algorithm(data)
>>>>>>> UPSTREAM
```

**Markers mean**:
- `<<<<<<< LOCAL`: Your local version starts here
- `=======`: Separator between versions
- `>>>>>>> UPSTREAM`: Remote version ends here

### Resolving Conflicts

1. **Understand both versions**:
   - Read LOCAL version (your code)
   - Read UPSTREAM version (new code)

2. **Choose or merge**:
   - Keep LOCAL (delete UPSTREAM section)
   - Use UPSTREAM (delete LOCAL section)
   - Merge both intelligently

3. **Example resolution**:

   **Original conflict**:
   ```python
   <<<<<<< LOCAL
   def authenticate(user_id):
       return db.get_user(user_id)
   =======
   def authenticate(user_id, cache=True):
       if cache:
           return cache.get_user(user_id)
       return db.get_user(user_id)
   >>>>>>> UPSTREAM
   ```

   **Resolved**:
   ```python
   def authenticate(user_id, cache=True):
       # Keep both: new parameter from upstream
       # with local database integration
       if cache:
           return cache.get_user(user_id)
       return db.get_user(user_id)
   ```

4. **Remove conflict markers** once resolved

5. **Test thoroughly** after merging

### Preventing Conflicts

Reduce merge conflicts by:

1. **Keep local changes minimal**: Only customize what you need
2. **Document customizations**: Comments about local changes
3. **Regular updates**: Small, frequent updates are easier to merge
4. **Separate concerns**: Keep custom code in separate files

## Automatic Snapshots

SkillMeat automatically creates snapshots before destructive operations:

### Snapshot Creation

```bash
# Snapshots created automatically during updates
skillmeat update canvas

# Also manually create snapshots
skillmeat snapshot "Before major update"
```

### View Snapshots

```bash
# List available snapshots
skillmeat history

# Output:
# Snapshots for 'default' (5)
# ID        Created                Message
# ────────────────────────────────────────────
# abc123d   2024-01-15 14:30:00  Before update
# def456e   2024-01-14 09:15:00  Backup
# 789fghi   2024-01-10 16:45:00  Initial setup
```

### Rollback on Failure

If an update goes wrong, restore from snapshot:

```bash
# Rollback to previous state
skillmeat rollback abc123d

# Output:
# Warning: This will replace collection with snapshot 'abc123d'
# Continue? [y/N]: y
#
# Rolling back...
# Created safety snapshot: xyz789a
# Restored collection from snapshot abc123d
```

## Versioning and Compatibility

### Understanding Versions

Artifacts can have different version formats:

```bash
# Semantic versioning (Recommended)
skillmeat update artifact@v2.1.0

# Git tags
skillmeat update artifact@latest

# Commit SHAs
skillmeat update artifact@abc123d

# Branches
skillmeat update artifact@main
```

### Version Constraints

Check version compatibility:

```bash
# View artifact version info
skillmeat show artifact

# Output includes:
# Version: latest -> v2.1.0
# Requires: SkillMeat >= 1.2.0
# Python: >= 3.9
```

### Checking Breaking Changes

Before updating between major versions:

```bash
# Preview major version jump
skillmeat diff artifact canvas --upstream --context 10

# Look for:
# - API changes
# - Configuration format changes
# - New dependencies
# - Deprecated features removed
```

## Best Practices

### 1. Always Preview First

```bash
# Good: Preview before updating
skillmeat diff artifact canvas --upstream
skillmeat update canvas

# Bad: Update without reviewing
skillmeat update canvas --strategy upstream  # Too fast!
```

### 2. Create Snapshots Before Major Updates

```bash
# Snapshot before risky update
skillmeat snapshot "Before canvas update"
skillmeat update canvas
```

### 3. Test in Safe Environment

```bash
# Test in development collection first
skillmeat list --collection dev
skillmeat update test-artifact --collection dev
# Verify it works...
# Then update production collection
skillmeat update test-artifact --collection default
```

### 4. Document Local Changes

```bash
# If you have local modifications, document them
# In artifact's README or comments:
# "LOCAL: Added custom authentication"
# "LOCAL: Modified error handling"
```

### 5. Update Regularly

```bash
# Small, frequent updates are easier to manage
skillmeat status  # Check weekly
skillmeat update artifact  # Update one at a time
# vs
skillmeat status  # Check after 3 months
skillmeat update artifact1 artifact2 artifact3  # Multiple conflicts!
```

### 6. Version Pin When Needed

```bash
# Pin to stable version if updates are problematic
skillmeat add skill user/repo/artifact@v1.5.0

# Later, selectively update when ready
skillmeat update artifact --strategy prompt
```

## Troubleshooting

### "No upstream information" Error

Artifact was added locally, not from GitHub:

```bash
# Shows if artifact was local source
skillmeat show artifact

# To enable updates, re-add from GitHub
skillmeat remove old-artifact
skillmeat add skill github-user/repo/artifact
```

### Merge Conflicts Won't Resolve

If automatic merge fails:

```bash
# Try different strategy
skillmeat update artifact --strategy upstream  # Force upstream
# or
skillmeat update artifact --strategy local  # Keep local
# Then manually merge later
```

### Rolled Back Update Won't Redo

If rollback happened but you want the update back:

```bash
# Rollback undid the update
skillmeat history

# ID        Created                Message
# abc123d   2024-01-15 14:30:00  Safety snapshot

# Find the snapshot before the failed update
skillmeat rollback def456e
```

### Update Doesn't Reflect Changes

If updated artifact seems unchanged:

```bash
# Artifact might be cached in deployment
skillmeat undeploy artifact
skillmeat deploy artifact

# Or check deployed version
skillmeat diff artifact --previous
```

## Related Guides

- [Searching for Artifacts](searching.md) - Find artifacts to update
- [Syncing Changes](syncing-changes.md) - Sync across projects
- [Using Analytics & Insights](using-analytics.md) - Track update history

## See Also

- [Command Reference: update](../commands.md#update)
- [Command Reference: diff artifact](../commands.md#diff-artifact)
- [Command Reference: snapshot](../commands.md#snapshot)
- [Command Reference: rollback](../commands.md#rollback)
