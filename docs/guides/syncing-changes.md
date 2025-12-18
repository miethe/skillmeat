# Syncing Project Changes Guide

Learn how to synchronize artifacts between projects and collections, detect drift, and keep everything in sync.

## Overview

SkillMeat provides bidirectional synchronization to keep artifacts consistent across collections and projects:

- **Drift Detection**: Identify when project artifacts differ from collection
- **Preview Changes**: See what would be synced before applying
- **Multiple Strategies**: Merge, overwrite, or fork diverged versions
- **Deployment Tracking**: Track which version is deployed via `.skillmeat-deployed.toml`
- **Conflict Resolution**: Handle conflicts with Git-style merge markers

## Concepts

### What is Drift?

**Drift** occurs when the deployed version of an artifact in a project differs from the version in the collection. This can happen when:

1. **Collection Changed**: Upstream updated the artifact in your collection
2. **Project Changed**: You modified artifact files directly in the project
3. **Deployment Lag**: Project has an older version than collection
4. **Removed**: Artifact was removed from collection but still deployed

### Understanding Change Attribution

SkillMeat tracks the **origin of changes** in three categories:

- **Upstream Changes** (Blue Badge): Changes pulled from your collection or upstream source
  - Safe to apply - represents upstream improvements
  - Shown with blue change badges in the UI

- **Local Modifications** (Amber Badge): Changes made locally in your project
  - Your customizations - preserve if important
  - Shown with amber change badges in the UI

- **Conflicting Changes** (Red Badge): Both sides changed the same lines
  - Requires manual resolution
  - Shown with red change badges in the UI
  - Indicates potential conflict or decision point

### Change Attribution in Merges

When merging versions, the system performs a **three-way merge** using:

1. **Base** (common ancestor): Starting point before changes
2. **Local** (your version): Your current changes
3. **Remote** (upstream version): Incoming changes

Each change is tagged with its origin so you know what's upstream vs local vs conflicting. This enables accurate conflict detection and helps you understand what's changing.

### Deployment Tracking

SkillMeat automatically creates `.skillmeat-deployed.toml` in each project:

```toml
# .skillmeat/deployed/.skillmeat-deployed.toml
[metadata]
collection = "default"
last_synced = "2024-01-15T10:30:00Z"

[[artifacts]]
name = "canvas"
type = "skill"
deployed_version = "v2.1.0"
deployed_sha = "abc123def456..."
deployed_at = "2024-01-15T10:30:00Z"

[[artifacts]]
name = "pdf-extractor"
type = "skill"
deployed_version = "v1.5.0"
deployed_sha = "xyz789abc123..."
deployed_at = "2024-01-14T09:15:00Z"
```

This metadata allows SkillMeat to detect changes accurately.

## Sync Workflow

The recommended sync workflow follows these steps:

```
1. Check for Drift     (skillmeat sync check)
    ↓
2. Preview Changes     (skillmeat sync preview)
    ↓
3. Review Differences  (examine output carefully)
    ↓
4. Choose Strategy     (overwrite, merge, or fork)
    ↓
5. Apply Sync          (skillmeat sync pull)
    ↓
6. Verify Results      (test the synced artifacts)
```

## Step 1: Check for Drift

Start by detecting what's out of sync:

### Basic Drift Check

```bash
# Check drift in current directory project
skillmeat sync check .

# Output shows:
# No drift detected. Project is in sync.
```

### Detect Drift with Details

```bash
# Check for drift with details
skillmeat sync check /path/to/project

# Output shows:
# Drift Detection Results: 3 artifacts
#
# Artifact       Type     Drift Type              Recommendation
# ────────────────────────────────────────────────────────────────
# canvas         skill    UPSTREAM_CHANGED        SYNC_UPSTREAM
# pdf-extractor  skill    MODIFIED_LOCALLY        REVIEW_CHANGES
# code-reviewer  command  REMOVED_FROM_COLLECTION VERIFY_AND_REMOVE
```

### Check Against Specific Collection

```bash
# Check drift against non-default collection
skillmeat sync check /path/to/project --collection work

# Useful when project uses different collection
```

### JSON Output for Automation

```bash
# Get drift data as JSON for scripting
skillmeat sync check /path/to/project --json

# Parse results programmatically
skillmeat sync check /path/to/project --json | jq '.artifacts[] | select(.drift_type == "UPSTREAM_CHANGED")'
```

### Understanding Drift Types

**UPSTREAM_CHANGED**: Collection has newer version
- Recommendation: Sync upstream (SYNC_UPSTREAM)
- Action: Pull changes from collection
- Change origin: upstream (blue badge)

**MODIFIED_LOCALLY**: Project version differs from deployed
- Recommendation: Review changes (REVIEW_CHANGES)
- Action: Decide whether to keep local changes or sync
- Change origin: local_modification (amber badge)

**REMOVED_FROM_COLLECTION**: Artifact no longer in collection
- Recommendation: Verify and remove (VERIFY_AND_REMOVE)
- Action: Remove from project if no longer needed
- Change origin: upstream (blue badge)

**VERSION_MISMATCH**: Version numbers differ
- Recommendation: Sync (SYNC)
- Action: Apply sync strategy
- Change origin: varies by situation

## Step 2: Preview Changes

Before syncing, preview what will happen:

### Preview All Syncs

```bash
# Preview all drift changes
skillmeat sync preview /path/to/project

# Output shows:
# Sync Preview: /path/to/project
#
# canvas (skill)
#   Status: WOULD_SYNC
#   Changes: 12 additions, 5 deletions
#   Files: +2, -1, M 3
#
# pdf-extractor (skill)
#   Status: WOULD_CONFLICT
#   Details: Local and upstream both modified
#   Action: Requires manual merge
#
# Total artifacts to sync: 2
# Potential conflicts: 1
```

### Preview Specific Artifacts

```bash
# Preview sync for specific artifact
skillmeat sync preview /path/to/project canvas

# Preview multiple specific artifacts
skillmeat sync preview /path/to/project canvas pdf-extractor
```

### JSON Preview for Automation

```bash
# Get preview as JSON
skillmeat sync preview /path/to/project --json

# Check for conflicts programmatically
skillmeat sync preview /path/to/project --json | jq '.artifacts[] | select(.status == "WOULD_CONFLICT")'
```

## Step 2b: Understanding Version Timeline and Change Badges

SkillMeat provides a visual timeline showing all versions of an artifact with change badges indicating the origin of each change.

### Version Timeline Display

The version timeline shows:
- **All versions** in chronological order
- **Change badges** on each file showing its origin
- **Deployment markers** showing which versions are deployed
- **Summary counts** of changes by origin

### Change Badge Colors

Understanding the visual indicators:

**Blue Badge** - Upstream Changes
- Changes from your collection or upstream source
- Safe to apply and integrate
- Example: "Latest features from maintainer"

**Amber Badge** - Local Modifications
- Changes made locally in your project
- Your customizations and local fixes
- Example: "Custom configuration for our use case"

**Red Badge** - Conflicting Changes
- Both sides changed (potential conflict)
- Requires manual review to merge
- Example: "Upstream improved error handling, but we also modified it"

### Interpreting Version Timeline

When viewing a version timeline for an artifact:

1. **Identify change origins**: Look at badge colors to understand each change
2. **Find conflicts**: Red badges indicate decisions to make
3. **Review drift**: Compare current deployment against upstream
4. **Plan updates**: Decide if upstream changes are compatible with your customizations

### Example Timeline

```
Version v2.2.0 (Upstream - 2025-12-18)
  ├─ canvas-ui.py: Blue badge (upstream)
  ├─ core.py: Red badge (conflicting)
  └─ config.yml: Amber badge (local)

Version v2.1.0 (Deployed - 2025-12-15)
  ├─ canvas-ui.py: Blue badge (upstream)
  └─ core.py: Amber badge (local)

Version v2.0.0 (Base - 2025-12-01)
  └─ canvas-ui.py: Blue badge (upstream)
```

Reading this timeline:
- v2.2.0 has upstream improvements but one conflicting change in core.py
- v2.1.0 is currently deployed with one local customization
- Upgrading to v2.2.0 requires resolving the core.py conflict

## Step 3: Review Differences

When examining previews, look for:

### Safe to Sync

Artifacts that can be safely synced:

```
canvas (skill)
  Status: WOULD_SYNC
  Changes: 12 additions, 5 deletions
  Conflict: None
```

These are safe - changes don't conflict.

### Requires Attention

Artifacts that need careful review:

```
pdf-extractor (skill)
  Status: WOULD_CONFLICT
  Details: Local and upstream both modified
  Conflict: Line 15-25 in pdf_processor.py
```

These have conflicts - manual merge may be needed.

### Potential Issues

Watch for:
- Removing artifacts you still need
- Overwriting critical customizations
- Large changes that might break functionality

## Step 4: Choose Sync Strategy

Decide how to handle conflicts:

### Strategy 1: `overwrite` (Collection Wins)

**Best for**: Collection is authoritative

```bash
skillmeat sync pull /path/to/project --strategy overwrite
```

**Behavior**:
- Collection version replaces project version
- Local project changes are discarded
- No conflict markers
- Fast and clean

**Use when**:
- Collection is source of truth
- Project changes are temporary
- You want clean synchronization

**Example**:
```bash
# Sync all with overwrite strategy
skillmeat sync pull /path/to/project --strategy overwrite --force

# Project version → Discarded
# Collection version → Applied to project
```

### Strategy 2: `merge` (Auto-Merge)

**Best for**: Preserving changes from both sides

```bash
skillmeat sync pull /path/to/project --strategy merge
```

**Behavior**:
- Attempts to merge changes from both sides
- Preserves non-conflicting changes
- Creates conflict markers if conflict exists
- Requires manual resolution if conflicts occur

**Use when**:
- Both sides have valid changes
- Want to preserve project modifications
- Don't want to lose work

**Example**:
```bash
# Merge strategy attempts to combine changes
# Collection: Added logging
# Project: Changed error handling
# Result: Both changes preserved

def process():
    log("Processing...")           # From collection
    try:
        return new_handler()       # From project
    except CustomError:
        return None               # From project
```

### Strategy 3: `fork` (Create Variant)

**Best for**: Keeping diverged versions separate

```bash
skillmeat sync pull /path/to/project --strategy fork
```

**Behavior**:
- Creates new artifact with `-fork` suffix
- Preserves both versions
- No overwriting or conflicts
- Safest option for diverged versions

**Use when**:
- Project version is different enough to be separate
- Want to keep both versions
- Planning to refactor later

**Example**:
```bash
# Before: canvas (project version)
# After:  canvas (collection version)
#         canvas-fork (project version preserved)

# Both versions now exist separately
skillmeat list
# canvas
# canvas-fork
```

## Step 5: Apply Sync

Once you've reviewed and chosen a strategy, apply the sync:

### Sync All Drifted Artifacts

```bash
# Sync all with interactive prompts
skillmeat sync pull /path/to/project

# For each drifted artifact, asks which strategy to use
```

### Sync Specific Artifacts

```bash
# Sync only canvas
skillmeat sync pull /path/to/project canvas

# Sync multiple specific artifacts
skillmeat sync pull /path/to/project canvas pdf-extractor
```

### Force Sync Without Prompts

```bash
# Use strategy without confirmation
skillmeat sync pull /path/to/project --strategy overwrite --force

# Useful for automation/CI/CD
```

### Sync to Different Collection

```bash
# Sync against non-default collection
skillmeat sync pull /path/to/project --collection work
```

## Handling Sync Conflicts

When merge conflicts occur, resolve them manually. Use change attribution to understand what changed and why.

### Understanding Conflict Context

Before resolving, check the **change origin** to understand the conflict:

- **Blue (upstream) vs Amber (local)**: Upstream improved something you customized
  - Decide: Keep your customization, use upstream, or merge both
  - Strategy: Often merge intelligently to get both benefits

- **Both Red**: Upstream and local both modified
  - Decide: Which approach is better? Can they be combined?
  - Strategy: Review both carefully, may need manual merge

### Conflict Markers

Conflicts appear as Git-style markers:

```python
<<<<<<< LOCAL
def authenticate(user_id):
    """Project version - our customization"""
    return authenticate_v2(user_id)
=======
def authenticate(user_id):
    """Collection version - upstream improvement"""
    return authenticate_v1(user_id)
>>>>>>> UPSTREAM
```

### Resolution Process

1. **Understand the conflict**:
   - LOCAL = Your project version (amber badge - local modification)
   - UPSTREAM = Collection version (blue badge - upstream improvement)
   - Check the change origin to understand context

2. **Analyze both approaches**:
   - What does LOCAL do? (your customization)
   - What does UPSTREAM do? (upstream improvement)
   - Can they be combined?

3. **Decide on approach**:
   - Keep LOCAL only (preserve your customization)
   - Use UPSTREAM only (accept upstream improvement)
   - Merge intelligently (combine benefits of both)

4. **Edit and resolve** - Example of intelligent merge:

   ```python
   # Resolved: Combine both approaches
   def authenticate(user_id):
       """Improved authentication with both local and upstream logic"""
       # Use newer version detection from collection (upstream)
       if isinstance(user_id, str):
           # But use our custom handler (local)
           return authenticate_v2(user_id)
       else:
           # Fallback to upstream approach
           return authenticate_v1(user_id)
   ```

5. **Remove markers**:
   - Delete all `<<<<<<`, `=======`, `>>>>>>` lines
   - Keep the resolved code

6. **Test thoroughly**:
   ```bash
   # Test the resolved artifact
   skillmeat deploy canvas --project /path/to/project
   # Run tests to verify functionality
   ```

7. **Update metadata**:
   ```bash
   # Update deployment tracking
   skillmeat sync pull /path/to/project canvas
   ```

### Conflict Resolution Decision Guide

| Situation | Recommendation | Action |
|-----------|---|--------|
| Upstream improved error handling, you added logging | Merge intelligently | Keep both: upstream error handling + your logging |
| Upstream refactored function signature, you customized behavior | Use upstream | Accept refactor, reapply your customization if needed |
| Upstream deprecated function, you still use it | Keep local | Keep your version until you can update code |
| Both added different features | Merge intelligently | Import/call both features if possible |
| Upstream simplified, you complexified | Review both | Understand why each approach exists before deciding |

## Preventing Drift

Keep projects and collections in sync:

### 1. Regular Sync Checks

```bash
# Check weekly or daily in CI/CD
skillmeat sync check /path/to/project

# Fail CI if drift detected
if [ $? -ne 0 ]; then
  echo "Drift detected - please sync"
  exit 1
fi
```

### 2. Minimize Local Changes

```bash
# Keep project changes minimal
# Only customize what you need
# Document all customizations

# Instead of modifying canvas.py, create:
# canvas_custom.py - your customizations
# Then import in your code
```

### 3. Regular Updates

```bash
# Update collection regularly
skillmeat status
skillmeat update artifact

# Then sync projects
skillmeat sync pull /path/to/project
```

### 4. CI/CD Integration

```bash
# Example CI/CD workflow
#!/bin/bash

# Check for drift
skillmeat sync check . --json | jq '.drift_detected' | grep -q "true"
if [ $? -eq 0 ]; then
    # Preview changes
    skillmeat sync preview .
    # Fail build
    exit 1
fi
```

## Resolving Specific Situations

### Situation: Collection Has Newer Version

**Signs**:
- Drift type: UPSTREAM_CHANGED
- Collection SHA differs from project SHA

**Resolution**:
```bash
# Option 1: Preview and sync
skillmeat sync preview /path/to/project
skillmeat sync pull /path/to/project --strategy merge

# Option 2: Force collection version
skillmeat sync pull /path/to/project --strategy overwrite --force

# Option 3: Keep and manually merge
skillmeat sync pull /path/to/project --strategy local
# Then manually review and update
```

### Situation: Project Has Local Customizations

**Signs**:
- Drift type: MODIFIED_LOCALLY
- Files differ from deployment metadata

**Resolution**:
```bash
# Option 1: Keep customizations
skillmeat sync pull /path/to/project --strategy local
# Document customizations for future reference

# Option 2: Merge with collection
skillmeat sync pull /path/to/project --strategy merge
# Manually resolve conflicts if needed

# Option 3: Create fork for customized version
skillmeat sync pull /path/to/project --strategy fork
# Now have canvas (collection) and canvas-fork (custom)
```

### Situation: Artifact Removed from Collection

**Signs**:
- Drift type: REMOVED_FROM_COLLECTION
- Artifact no longer exists in collection

**Resolution**:
```bash
# Option 1: Remove from project too
skillmeat undeploy artifact --project /path/to/project

# Option 2: Keep locally (one-off)
skillmeat sync pull /path/to/project --strategy local
# Project keeps the artifact

# Option 3: Move to custom collection
skillmeat add skill ./artifact --collection custom
skillmeat deploy artifact --collection custom
```

## Automation and Scripting

### Checking Drift in CI/CD

```bash
#!/bin/bash
# CI/CD script: Check for drift and fail if found

skillmeat sync check /path/to/project --json | jq '.drift_detected' | grep -q "true"
if [ $? -eq 0 ]; then
    echo "ERROR: Drift detected"
    skillmeat sync preview /path/to/project
    exit 1
fi
echo "OK: No drift detected"
```

### Auto-Syncing in Deployment Pipeline

```bash
#!/bin/bash
# Deployment script: Auto-sync before deployment

# Check and sync all drifts
skillmeat sync pull /path/to/project --strategy merge --force || {
    echo "ERROR: Sync failed with conflicts"
    exit 1
}

# Proceed with deployment
echo "Sync complete, proceeding with deployment..."
```

### Finding Projects with Drift

```bash
#!/bin/bash
# Find all projects with drift

for project in ~/projects/*/; do
    echo "Checking $project..."
    skillmeat sync check "$project" --json | jq '.drift_detected' | grep -q "true"
    if [ $? -eq 0 ]; then
        echo "  - Has drift"
    fi
done
```

## Troubleshooting

### "No deployment metadata found" Error

Project hasn't been deployed yet or has old structure:

```bash
# Solution: Deploy artifacts first
skillmeat deploy canvas --project /path/to/project

# Now sync will work
skillmeat sync check /path/to/project
```

### Sync Won't Apply Changes

If sync doesn't seem to work:

```bash
# Check if artifacts actually differ
skillmeat diff artifact canvas --upstream

# Verify deployment metadata
cat /path/to/project/.claude/.skillmeat-deployed.toml

# Redeploy artifact
skillmeat undeploy canvas --project /path/to/project
skillmeat deploy canvas --project /path/to/project
```

### Merge Conflicts Won't Resolve

If automatic merge fails:

```bash
# View exact conflict
skillmeat sync pull /path/to/project --strategy merge
# Manually edit conflicted files
# Resolve conflict markers

# Alternatively, use different strategy
skillmeat sync pull /path/to/project --strategy overwrite
# Or
skillmeat sync pull /path/to/project --strategy fork
```

### Accidentally Overwrote Local Changes

If you accidentally synced with overwrite and lost changes:

```bash
# Check deployment history
skillmeat history --collection default

# Rollback to before the sync
skillmeat rollback snapshot_id --collection default
```

## Related Guides

- [Updating Artifacts Safely](updating-safely.md) - Update artifacts from upstream
- [Searching for Artifacts](searching.md) - Find artifacts across projects
- [Using Analytics & Insights](using-analytics.md) - Track sync operations

## See Also

- [Command Reference: sync check](../commands.md#sync-check)
- [Command Reference: sync pull](../commands.md#sync-pull)
- [Command Reference: sync preview](../commands.md#sync-preview)
- [Deployment Tracking](../commands.md#deployment)
