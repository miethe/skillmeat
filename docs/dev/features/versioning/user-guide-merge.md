---
title: Merge Workflow User Guide
description: Complete guide to understanding and using SkillMeat's merge system for resolving collection changes and conflicts
audience: users
tags: [merge, conflict-resolution, sync, versioning, collections]
created: 2025-12-17
updated: 2025-12-17
category: features/versioning
status: published
related_documents:
  - syncing-changes.md
  - updating-safely.md
  - versioning-overview.md
---

# Merge Workflow User Guide

A comprehensive guide to understanding merges, resolving conflicts, and keeping your collection in sync when both local and remote changes occur.

## What is a Merge?

A **merge** combines changes from two different versions of your collection into a single unified version. Merges happen when:

- You want to sync your local collection with remote changes
- Both you and an upstream source have modified the same artifacts
- You need to integrate new features while keeping your customizations

### Why Merges Happen

Think of your collection as a living document. Over time, different things can change:

**Example Scenario:**

```
Original Collection (Base)
├── canvas skill (v1.0)
├── pdf-extractor skill (v1.0)
└── code-reviewer command (v1.0)

Your Local Changes              Remote Changes
├── canvas (v1.0 + yours)      ├── canvas (v2.0 official)
├── pdf-extractor (v1.0)       ├── pdf-extractor (v2.0 official)
├── code-reviewer (v1.0)        ├── code-reviewer (v1.5 official)
└── your-skill (new, custom)    └── new-official-tool (new official)

Goal: Merge → Combine best of both
```

## Types of Merges

### Fast-Forward Merge (Simple)

**When it happens:** You only made changes on your side, remote hasn't changed.

**What it means:** Remote is "ahead" of your version, so SkillMeat just applies the remote changes without any conflict.

**Example:**
```
Local: canvas v1.0 (unchanged)
Remote: canvas v2.0 (updated)
Result: canvas v2.0 → Applied automatically
```

**No action needed** - these merge automatically.

### Automatic Three-Way Merge (Smart)

**When it happens:** Both you and remote changed different parts of the file.

**What it means:** SkillMeat intelligently combines changes that don't conflict.

**Example:**
```
Base (original): canvas.md (10 lines)
├── You added: 5 new lines at the end
└── Remote added: 2 new lines at the beginning

Result: Combined → All 5 + all 2 = automatic merge ✓
```

**Minimal action needed** - SkillMeat handles most of it.

### Manual Conflict Resolution (Interactive)

**When it happens:** You and remote changed the exact same lines in the same file.

**What it means:** SkillMeat can't automatically decide whose version is correct - you need to choose.

**Example:**
```
Base (original):
  def process():
      return base_version()

You changed to:
  def process():
      return your_custom_version()

Remote changed to:
  def process():
      return official_new_version()

Result: Conflict → Need your decision
```

**Action required** - You resolve by choosing which version to keep.

## The Merge Workflow

SkillMeat guides you through a structured 5-step process to safely merge changes:

```
START
  ↓
[1. Analyze] → Safety checks & conflict detection
  ↓
[2. Preview] → See files that will be affected
  ↓
[3. Resolve] → Handle conflicts (if any)
  ↓
[4. Confirm] → Final review before applying
  ↓
[5. Execute] → Apply the merge
  ↓
END (automatic snapshot created)
```

### Step 1: Analyze

**What happens:**
- SkillMeat compares your collection with the remote version
- Identifies which files can auto-merge
- Counts conflicts that need manual resolution
- Checks for potential issues (deletions, overwrites, etc.)

**What you see:**
- Total files to merge
- Auto-mergeable files (safe, automatic)
- Files with conflicts (needs your attention)
- Warnings about deletions or major changes

**Your action:** Review the analysis, then proceed to Preview.

**Example Analysis:**
```
Merge Analysis Results:
├── Total files to merge: 12
├── Auto-mergeable: 10 ✓
├── Conflicts: 2 ✗
│   ├── canvas-skill.py (content conflict)
│   └── config.toml (both modified)
└── Warnings:
    └── 1 artifact will be removed from your collection
```

### Step 2: Preview

**What happens:**
- SkillMeat shows you every file that will be affected
- Categorizes files into: Added, Removed, or Changed
- Shows summary statistics

**Files categories:**

| Category | Meaning | Icon | Example |
|----------|---------|------|---------|
| Added | New files from remote | Plus | `new-skill/skill.py` |
| Removed | Files that will be deleted | Minus | `old-skill/skill.py` |
| Changed | Files that will be modified | Changed | `canvas/skill.py` |

**What you see:**
```
Merge Preview Summary:
├── Total Changes: 12
├── Added: 3 new files ✨
├── Removed: 1 file 🗑️
└── Changed: 8 files 📝

Files Being Added:
├── new-feature-skill/skill.py
├── new-feature-skill/config.toml
└── documentation.md

Files Being Removed:
└── deprecated-tool/skill.py

Files Being Changed:
├── canvas/skill.py
├── pdf-extractor/skill.py
├── config.toml
└── manifest.toml
```

**Your action:**
- Review what will change
- If anything concerns you, note it for the Resolve step
- Proceed to Resolve (if conflicts exist) or Confirm

### Step 3: Resolve (If Needed)

**When you see it:** Only if there are conflicts from Step 1.

**What happens:**
- SkillMeat shows each conflicted file
- Displays side-by-side comparison using three-way diff
- Lets you choose how to resolve

**The Three-Way Diff Viewer:**

The diff shows three versions:

```
LEFT SIDE (Your Version)     MIDDLE (Original Base)     RIGHT SIDE (Remote Version)
─────────────────────────────────────────────────────────────────────────────
def process():              def process():              def process():
    print("local")              print("base")               print("remote v2.0")
    return local_result()       return base_result()        return official_result()

Color coding:
🟢 Green = Added in this version
🔴 Red = Removed from this version
🟡 Yellow = Changed in this version
```

**Resolution Options:**

| Option | Meaning | When to Use |
|--------|---------|-------------|
| **Use Local** | Keep your version | Your changes are better/more important |
| **Use Remote** | Take remote version | Remote has official updates you want |
| **Use Base** | Revert to original | Start fresh from the base version |
| **Custom** | Write your own version | Combine the best parts manually |

**Decision Guide:**

```
For each conflict, ask yourself:

Q1: Is my local version more important?
    YES → Use Local
    NO  → Continue to Q2

Q2: Should I fully adopt the remote version?
    YES → Use Remote
    NO  → Continue to Q3

Q3: Do I want to start from scratch?
    YES → Use Base
    NO  → Continue to Q4

Q4: Can I manually combine both?
    YES → Custom (edit manually)
    NO  → Use Remote (safest)
```

**Practical Examples:**

**Example 1: Canvas Skill Conflict**
```
Local (you):   Uses custom authentication
Remote:        Uses official new authentication

Decision: Use Remote + manually add custom logic after
Resolution: Custom → Keep official auth, add custom layer on top
```

**Example 2: Config File Conflict**
```
Local (you):   Added custom settings
Remote:        Added official new settings

Decision: Use Custom → Merge both
Resolution: Custom → Keep both custom AND new official settings
```

**Example 3: Deprecated Code Conflict**
```
Local (you):   Kept old code
Remote:        Removed deprecated code

Decision: Use Remote
Resolution: Use Remote → Remove the deprecated code
```

**Your action:**
- For each conflict, choose a resolution option
- If choosing Custom, edit the content directly
- Resolve all conflicts before proceeding

### Step 4: Confirm

**What happens:**
- SkillMeat shows a final summary of all changes
- Lists all resolutions you made
- Confirms no conflicts remain

**What you see:**
```
Final Merge Summary:
├── Auto-merged files: 10
├── Manually resolved: 2
│   ├── canvas-skill.py → Used Local
│   └── config.toml → Used Custom
├── Safety snapshot: Will be created automatically
└── Ready to execute!
```

**Your action:**
- Review the summary one final time
- Check that all resolutions are correct
- Click "Execute Merge" to apply

### Step 5: Execute

**What happens:**
- SkillMeat applies all changes
- Creates an automatic safety snapshot (backup)
- Updates your collection
- Logs the merge operation

**What you see:**
- Progress indicator showing steps
- Completion confirmation
- Success notification

**Automatic snapshot:**
```
Snapshot created automatically:
├── Timestamp: 2025-12-17 14:23:45 UTC
├── Type: Pre-merge backup
├── Collection: default
├── Can restore if needed: Yes
└── Status: Ready
```

**Your action:** Done! Your collection is now merged and in sync.

## Handling Common Scenarios

### Scenario A: Simple Sync with No Conflicts

**Your situation:**
- You haven't made local changes
- Remote has updates
- Everything is safe

**What happens:**
```
Analyze   → No conflicts detected ✓
Preview   → All files ready to merge
Resolve   → (skipped, no conflicts)
Confirm   → Summary shows automatic merge
Execute   → Changes applied automatically
```

**Time to complete:** 1-2 minutes

**Steps:**
1. Open Sync dialog
2. Click "Start Merge"
3. Click "Execute" at confirmation
4. Done!

### Scenario B: Conflicts in One File

**Your situation:**
- You customized one file locally
- Remote updated the same file
- Other files are fine

**What happens:**
```
Analyze   → 1 conflict found
Preview   → 11 files auto-mergeable, 1 with conflict
Resolve   → Shows conflict in your file
            You choose: Local, Remote, or Custom
Confirm   → Shows your resolution
Execute   → Applies all changes
```

**Time to complete:** 3-5 minutes

**Steps:**
1. Open Sync dialog
2. Click "Start Merge"
3. At Resolve step, select your conflicted file
4. Choose resolution (usually "Use Local" or "Use Remote")
5. Click "Confirm Resolution"
6. Click "Execute"
7. Done!

### Scenario C: Multiple Conflicts Across Files

**Your situation:**
- You customized multiple files
- Remote also updated multiple files
- Several conflicts need resolution

**What happens:**
```
Analyze   → 5 conflicts found
Preview   → Shows all 5 conflicted files
Resolve   → Walk through each conflict
            Resolve #1 → Resolve #2 → ... → Resolve #5
Confirm   → Final review of all 5 resolutions
Execute   → Apply all changes
```

**Time to complete:** 10-15 minutes

**Steps:**
1. Open Sync dialog
2. Click "Start Merge"
3. At Resolve step, select first conflict
4. Choose and apply resolution
5. Move to next conflict (automatic)
6. Repeat until all resolved
7. Click "Confirm"
8. Click "Execute"
9. Done!

### Scenario D: Binary File Conflicts (Images, etc.)

**Your situation:**
- A binary file (image, PDF, etc.) differs between local and remote
- Can't merge binary files automatically

**What happens:**
```
Analyze   → Binary conflict found
Preview   → Shows binary file
Resolve   → Only options: Use Local or Use Remote
            (Can't edit binary files manually)
Confirm   → Your choice recorded
Execute   → Your chosen version applied
```

**Time to complete:** 2-3 minutes

**Binary Resolution Options:**

| Option | Use When |
|--------|----------|
| Use Local | Your version is correct |
| Use Remote | Remote version is correct |

**Note:** You can't manually edit binary files. If neither version is acceptable, you must:
1. Keep one version for now
2. Manually replace it after the merge
3. Deploy the corrected version

## Best Practices

### Before You Merge

**1. Backup first**
```
Even though SkillMeat creates automatic snapshots,
it's good practice to be prepared.
```

**2. Review the preview carefully**
- Check what files will be added/removed/changed
- Make sure nothing surprises you
- Ask "Does this look right?" before proceeding

**3. Understand your customizations**
- Know which files you've customized locally
- Be prepared to explain why you customized them
- Have a strategy for resolving conflicts

**4. Close applications using the files**
- If editing a skill file, close your editor
- If running a deployed artifact, stop it first
- Prevents lock-file conflicts

### During Merge Resolution

**1. Understand each conflict**
- Read both versions carefully
- Check the original base version
- Understand what changed and why

**2. Make informed decisions**
- Don't just pick the first option
- Consider: Will this break anything?
- Think long-term, not just short-term

**3. Test your resolutions**
- If using Custom, verify the syntax
- Check that your merge makes sense
- Consider running tests after

**4. Document your choices**
- If you made Custom resolutions, add a comment
- Note why you chose this resolution
- Help future-you understand the decision

### After Merge

**1. Verify the result**
```bash
# Test your merged artifacts
skillmeat deploy <artifact> --project /path/to/project

# Run any automated tests
npm test
pytest
```

**2. Check everything works**
- Deploy merged artifacts
- Run your workflows
- Test integrations
- Make sure nothing broke

**3. Monitor for issues**
- Watch for unexpected behavior
- Keep an eye on logs
- Be ready to rollback if needed

## Troubleshooting

### "Merge Failed" Error

**Possible causes:**

1. **Files locked or in use**
   - Solution: Close editors, stop running artifacts
   - Retry the merge

2. **Insufficient permissions**
   - Solution: Check you have write access to collection
   - Retry with proper permissions

3. **Corrupted data**
   - Solution: Try restoring from a previous snapshot
   - Contact support if persists

### Merge Completed But Something Looks Wrong

**Investigation steps:**

1. **Check the summary**
   - Review what was merged
   - Check resolutions you made
   - Look for unexpected changes

2. **Use version history**
   ```
   View all snapshots to see before/after state
   Compare your merged version with what you expected
   ```

3. **Rollback if needed**
   ```
   If something is definitely wrong,
   restore the pre-merge snapshot
   Start over with different resolutions
   ```

### Conflict Won't Resolve

**If a conflict keeps failing:**

1. **Try different resolution**
   - Use Local instead of Remote
   - Use Remote instead of Local
   - Try Base version
   - Different choices might work

2. **Use Custom and resolve manually**
   - Take full control
   - Manually combine both versions
   - Fix any syntax issues
   - Verify it makes sense

3. **Ask for help**
   - Share the conflict details
   - Explain what you're trying to do
   - Get guidance on best resolution

### I Accidentally Used Wrong Resolution

**Can I undo?**

Yes! The merge creates an automatic snapshot before applying changes.

**Steps to undo:**

1. Go to Snapshots
2. Find the "Pre-merge backup" snapshot
3. Click "Restore from snapshot"
4. Start the merge again with correct resolution

## When to Get Help

### Contact support if:

- **Merge is failing repeatedly**
  - Same error keeps happening
  - You can't identify the cause
  - Technical issue blocking the merge

- **Conflicts are complex**
  - Multiple files with interdependencies
  - Not sure how to resolve together
  - Risk of breaking functionality

- **Collection is in unexpected state**
  - Merge completed but something seems wrong
  - Files missing or corrupted
  - Deployment failed after merge

- **You need merge strategy advice**
  - Not sure which resolution to choose
  - Conflicting changes seem incompatible
  - Want expert guidance on approach

## Related Topics

- **[Syncing Changes Guide](syncing-changes.md)** - Full sync workflow including drift detection
- **[Updating Safely Guide](updating-safely.md)** - Best practices for artifact updates
- **[Versioning Overview](versioning-overview.md)** - How versioning and snapshots work
- **[Command Reference: sync](../commands.md#sync-pull)** - CLI sync commands
- **[Deployment Tracking](../commands.md#deployment)** - How deployment metadata works

## Frequently Asked Questions

**Q: Does merging delete my local changes?**
A: No, unless you explicitly choose "Use Remote" for a conflicted file. By default, local changes are preserved.

**Q: Can I cancel a merge?**
A: Yes, at any step before "Execute". Once executed, you can restore from the automatic snapshot.

**Q: What happens to files I added locally?**
A: They're preserved. Merge only affects files that exist in both versions.

**Q: Is it safe to auto-merge when there are conflicts?**
A: No. You must resolve conflicts manually. The merge dialog won't let you execute until all conflicts are handled.

**Q: How do I prevent conflicts in the future?**
A: Keep local customizations minimal, sync regularly, and coordinate with others on who modifies what.

**Q: Can I merge with multiple people's versions?**
A: Merge currently handles two versions (local and remote). For three-way merges with multiple collaborators, merge in stages: local+remote1 first, then result+remote2, etc.
