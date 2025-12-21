---
title: Version History User Guide
description: Complete guide to managing collection version history, snapshots, comparisons, and rollbacks
audience: users
tags: ["versioning", "snapshots", "rollback", "history", "comparison"]
created: 2025-12-17
updated: 2025-12-17
category: Feature Guide
status: published
related_documents:
  - docs/user/guides/syncing-changes.md
  - docs/user/guides/updating-safely.md
---

# Version History User Guide

SkillMeat's version history feature lets you capture, compare, and restore previous states of your collections. This guide explains how to use these powerful tools to manage your artifacts safely.

## Table of Contents

- [Introduction](#introduction)
- [Viewing Version History](#viewing-version-history)
- [Comparing Versions](#comparing-versions)
- [Rolling Back to Previous Versions](#rolling-back-to-previous-versions)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

### What is Version History?

Version history (also called "snapshots") is a record of your collection at different points in time. Think of it like a photo album of your collection - each snapshot captures:
- All artifacts in your collection
- When the snapshot was taken
- Why it was taken (with an optional message)
- How many artifacts were included

### Why Version History Matters

Version history gives you peace of mind:
- **Safety**: Accidentally modified or deleted something? Restore it with one click
- **Tracking**: See exactly what changed between versions
- **Experimentation**: Try new artifacts or changes, then revert if needed
- **Auditing**: Keep a record of collection changes over time

### How Snapshots are Created

SkillMeat automatically creates snapshots at key moments:
- When you **sync** your collection (checking for updates)
- When you **deploy** artifacts to projects
- Whenever you perform major collection operations
- When you manually create one before making changes

You can also manually create snapshots anytime with a custom message.

## Viewing Version History

### Accessing the History Tab

To view your collection's version history:

1. Navigate to your collection in the web interface
2. Click the **History** tab (clock icon) at the top of the collection view
3. You'll see a timeline of all snapshots for this collection

### Understanding the Timeline

The timeline displays snapshots in chronological order, newest first. For each snapshot you can see:

| Information | Meaning |
|------------|---------|
| **Timestamp** | When this snapshot was created (date and time) |
| **Message** | Optional description you provided when creating the snapshot |
| **Artifact Count** | How many artifacts were in your collection at this time |
| **ID** | Unique identifier for this snapshot (shown as abbreviated hash) |

### Example Timeline Entry

```
2025-12-17 14:32 UTC - "After adding canvas design skill"
[artifact count: 47 artifacts]
Snapshot ID: abc1d2e3...
```

This shows a snapshot was taken at 2:32 PM UTC on Dec 17, 2025, with a description about adding a canvas design skill. The collection contained 47 artifacts at that time.

### Creating a Manual Snapshot

Before making significant changes or trying something new:

1. Click **Create Snapshot** button (top right of History tab)
2. Add an optional message describing what you're about to do:
   - "Before major reorganization"
   - "After adding ML skills"
   - "Testing new artifact sources"
3. Click **Create Snapshot**

The snapshot appears at the top of your timeline immediately.

**Tip**: Descriptive messages make it much easier to find the snapshot you want to restore to later.

## Comparing Versions

### Why Compare Versions?

Comparing two snapshots shows you exactly what changed:
- Which files were added, removed, or modified
- How many lines changed in each file
- A complete list of modifications

This is helpful when:
- You want to see what a deployment changed
- You're investigating unexpected modifications
- You need to understand the impact of an operation
- You're reviewing changes before rolling back

### How to Compare Two Versions

1. In the timeline, click **Compare** on one of the snapshots
2. Select the second snapshot you want to compare it to
3. The comparison view opens, showing all differences

The older snapshot is displayed on the left, and the newer one on the right.

### Understanding the Comparison View

The comparison shows statistics at the top:

```
Total Changes: 12 files modified
Lines Added: +347 insertions
Lines Removed: -89 deletions
```

Below the statistics, three sections show:

#### Files Added (Green)
New files that appeared between the two snapshots.
- Indicates new artifacts or content was added
- Shows count and list of files

Example:
```
Added Files (3)
  canvas-design/skill.json
  ml-integration/utils.py
  web-tools/api-client.ts
```

#### Files Modified (Yellow)
Files that existed in both snapshots but changed.
- Most common type of change
- Could be artifact updates or configuration changes
- Shows count of files changed

Example:
```
Modified Files (8)
  collection/manifest.toml
  artifacts/config.yaml
  deployments/settings.json
```

#### Files Removed (Red)
Files that existed in the older snapshot but are gone in the newer one.
- Indicates artifacts or content was deleted
- Shows what was removed
- Can be useful for understanding what changed

Example:
```
Removed Files (1)
  deprecated-artifact/old-skill.json
```

### Using Comparison Results

The comparison view helps you:
- **Before rollback**: Review what you're about to change
- **Understand changes**: See the scope and impact of operations
- **Verify safety**: Check if files you care about are affected

## Rolling Back to Previous Versions

### What is Rollback?

Rollback restores your collection to a previous snapshot, undoing all changes that happened after that point. It's like pressing "undo" for your entire collection.

### When to Use Rollback

Use rollback when:
- You accidentally deleted important artifacts
- An update changed things you didn't want changed
- You want to undo recent changes but keep some new work
- You need to recover from a mistake

**Important**: Rollback should be used thoughtfully. Review the comparison before proceeding.

### Before You Rollback

SkillMeat performs a **safety analysis** to warn you about potential issues:

1. **Files with Conflicts**: Some files may have local changes that would be overwritten
   - These are shown in **yellow** warning boxes
   - Lists specific files that will be affected
   - You can choose to preserve these changes or discard them

2. **Files Safe to Restore**: Files that can be safely restored without issues
   - These are shown in **green** safe boxes
   - These will be restored without any problems
   - No action needed on your part

3. **Warnings**: Additional notices about the rollback
   - May mention files that require manual review
   - Explains any special considerations
   - Guides you on next steps

### How to Execute a Rollback

1. In the timeline, click **Rollback** on the snapshot you want to restore to
2. Review the safety analysis dialog carefully
3. The dialog shows:
   - **Snapshot information**: Message and timestamp you're restoring to
   - **Safety status**: Whether it's safe to proceed
   - **Files with conflicts**: What local changes might be affected
   - **Files safe to restore**: What will be cleanly restored

4. Check the confirmation checkbox: "I understand this will restore files"
5. Choose merge strategy (see next section)
6. Click **Rollback to This Version**

The rollback is complete when you see the success message with stats:
- Files merged
- Files restored
- Any manual resolutions needed

### Merge Strategies

When rolling back, you choose how to handle local changes:

#### Preserve Local Changes (Default, Recommended)
- Attempts 3-way merge to keep your uncommitted changes
- Restores snapshot files without overwriting your work
- Conflicts show files needing manual review
- Best for: When you want to keep recent work while restoring older structure

#### Discard All Local Changes
- Completely replaces everything with the snapshot
- Ignores any uncommitted changes
- Fastest option, but loses recent work
- Best for: When you want a clean restore to a known state

**Tip**: Always use "Preserve Local Changes" unless you specifically want to discard recent work.

### What Happens After Rollback

After a successful rollback:

1. **Your collection is restored**: Files match the snapshot you chose
2. **Safety snapshot created**: A backup of your current state (before rollback) is automatically created
   - Labeled with snapshot ID
   - Lets you undo the rollback if needed
3. **Results shown**: You see statistics about what was changed
4. **Any conflicts listed**: Files that need manual review are listed

### Understanding Rollback Results

The success dialog shows:

```
Files Merged: 23
Files Restored: 18
Manual Resolution Required: 2 files
  - config/settings.json
  - local-artifacts/custom-skill.yaml
```

This means:
- 23 files were successfully merged with your local changes
- 18 files were cleanly restored
- 2 files have conflicts requiring manual review
  - You need to decide which version to keep
  - Check these files after rollback completes

### Manual Conflict Resolution

If rollback shows conflicts:

1. Open the conflicted files in your editor
2. Look for conflict markers (typically `<<<<< ===== >>>>>`)
3. Decide which version to keep
4. Edit the file to remove markers and keep your choice
5. Save the file

Alternatively, you can use the backup snapshot to try again with different merge settings.

## Best Practices

### Planning Snapshots

1. **Create snapshots before major changes**
   - Before reorganizing artifacts
   - Before testing new sources
   - Before updating many artifacts at once

2. **Use descriptive messages**
   - "Before Q4 content update" (tells you what happened)
   - "Backup before testing" (explains why it exists)
   - Avoid: "snapshot1", "temp", "test" (not helpful)

3. **Keep regular snapshots**
   - Let automatic snapshots from sync and deploy happen
   - Manually snapshot before intentional changes
   - You don't need to manually snapshot everything

### Before Rolling Back

1. **Always review the comparison first**
   - Compare the current state with the snapshot you want
   - Understand what will change
   - Identify files you care about

2. **Check the safety analysis**
   - Read all warnings carefully
   - Note files with conflicts
   - Understand what will be overwritten

3. **Back up important work**
   - If you have local changes you care about, save them separately
   - Screenshot any important metadata before rollback
   - The safety snapshot will preserve your current state, but make a copy just in case

4. **Choose the right merge strategy**
   - Use "Preserve Local Changes" to keep recent work
   - Use "Discard All Local Changes" only when you want complete reset

### After Rolling Back

1. **Verify the rollback succeeded**
   - Check that expected files were restored
   - Review any manually resolved conflicts
   - Confirm your collection is in expected state

2. **Address conflicts if any**
   - Don't ignore files listed as requiring manual resolution
   - Edit them to complete the merge
   - Test that everything still works correctly

3. **Create a new snapshot** (optional but recommended)
   - After successful rollback
   - Document what was restored and why
   - Makes it easier to track your decision

### Viewing Rollback History

Each automatic backup snapshot created during rollback is labeled, so you can:
- Undo a rollback if needed (rollback to the backup)
- Understand what changes were made
- See the timeline of your collection's evolution

## Troubleshooting

### Problem: "Snapshot not found"

**Cause**: The snapshot may have been deleted or IDs changed

**Solution**:
1. Refresh your browser (F5)
2. Check the timeline to confirm snapshot still exists
3. Try comparing with a nearby snapshot instead
4. Contact support if snapshot is missing unexpectedly

### Problem: Rollback shows many conflicts

**Cause**: Multiple files changed between snapshots, or snapshot is very old

**Solution**:
1. Review the conflicted files carefully
2. Consider using selective rollback (rollback only specific files instead of all)
3. Make changes manually instead of using rollback
4. Create a new snapshot of your current state first

### Problem: Rollback completed but I still see old files

**Cause**: Browser cache may be showing old data

**Solution**:
1. Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Restart the web interface
3. Re-sync your collection to refresh metadata
4. Check the actual files in your collection folder

### Problem: Can't undo a rollback

**Cause**: You want to revert to the state before the rollback

**Solution**:
1. Look for the automatic "Safety Snapshot" created during rollback
2. Rollback to that safety snapshot to restore your previous state
3. This effectively undoes the previous rollback
4. Create a manual snapshot now so you can easily restore this state

### Problem: Comparison view won't load

**Cause**: May be a network issue or files are too large

**Solution**:
1. Wait a moment and try again
2. Refresh your browser
3. Try comparing different snapshots that are closer together
4. Check your network connection

### Problem: Rollback button is disabled

**Cause**: Safety analysis found serious issues, or you need to check boxes

**Solution**:
1. Check if you've marked the confirmation checkbox
2. Review any error messages shown
3. Try a different snapshot that's closer in time
4. Resolve the error condition (e.g., fix file permissions)

## Additional Resources

- **Quick Start**: [Getting Started with SkillMeat](../../../quickstart.md)
- **Web Interface Guide**: [SkillMeat Web UI Guide](../../guides/web-ui-guide.md)
- **Updating Safely**: [Updating Artifacts Safely](../../guides/updating-safely.md)
- **Syncing Changes**: [Syncing with Upstream](../../guides/syncing-changes.md)

## Getting Help

If you encounter issues with version history:

1. Check this guide's troubleshooting section
2. Review the web UI guide for general navigation help
3. Check error messages shown in the browser
4. Contact support with:
   - Snapshot ID (shown in timeline)
   - Error message (if any)
   - Steps to reproduce
   - Your SkillMeat version

---

**Last Updated**: December 17, 2025

For information about the technical architecture of the versioning system, see the [Versioning & Merge System Implementation](../../project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md).
