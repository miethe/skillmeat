---
title: Collection Recovery
description: Support script for recovering corrupted or lost collections
audience: support-team
tags:
  - support-scripts
  - recovery
  - troubleshooting
created: 2025-11-17
updated: 2025-11-17
category: Support Scripts
status: Published
---

# Support Script: Collection Recovery

**Issue**: User lost collection data, corrupted manifest, or wants to restore from backup
**Time to resolve**: 10-15 minutes
**Difficulty**: Medium
**Escalation**: None needed (if backup available)

## Quick Diagnosis

Ask the user:
1. "Did you accidentally delete the collection?"
2. "Are you seeing errors when listing or deploying?"
3. "Do you have a backup of your collection?"

### Signs of Collection Corruption
- `skillmeat list` returns errors
- `skillmeat show <name>` fails
- Manifest file is empty or malformed
- Collection appears to be missing files

### Signs of Data Loss
- Collections directory missing or empty
- Can't find collection.toml file
- Artifacts aren't loading

## Recovery Steps

### Step 1: Check Collection Status

```bash
# Check if collection exists
ls ~/.skillmeat/collection.toml

# Check collection directory
ls -la ~/.skillmeat/

# Try to list artifacts
skillmeat list --verbose
```

**Expected output**: List of artifacts or error message

### Step 2: Backup Current State (If Possible)

**Before doing anything, make a backup**:

```bash
# Backup current state
mkdir ~/collection-recovery-backup
cp -r ~/.skillmeat ~/collection-recovery-backup/

# Note timestamp
date > ~/collection-recovery-backup/RECOVERY-DATE.txt
```

This preserves current state in case recovery fails.

### Step 3: Validate Collection Manifest

Check if manifest file is corrupted:

```bash
# Check manifest syntax
python3 -m py_compile ~/.skillmeat/collection.toml 2>&1

# Or check with TOML parser
python3 -c "
import tomllib
with open(expanduser('~/.skillmeat/collection.toml'), 'rb') as f:
    tomllib.load(f)
print('Manifest is valid')
"
```

**If valid**: Manifest is OK, issue is elsewhere
**If invalid**: Manifest is corrupted, needs repair

### Step 4: Repair Corrupted Manifest

If manifest is corrupted:

```bash
# Check current content
cat ~/.skillmeat/collection.toml

# If completely corrupted or empty
rm ~/.skillmeat/collection.toml
skillmeat init
```

### Step 5: Restore from Backup (If Available)

If user has a backup:

```bash
# Check backup location
ls ~/collection-recovery-backup/
# or
ls ~/Downloads/skillmeat-backup/
# or similar

# Restore from backup
cp ~/collection-recovery-backup/collection.toml ~/.skillmeat/collection.toml
cp -r ~/collection-recovery-backup/artifacts ~/.skillmeat/

# Verify restoration
skillmeat list
```

### Step 6: Verify Collection Integrity

Test that collection is working:

```bash
# List artifacts
skillmeat list

# Check specific artifact
skillmeat show <artifact-name>

# Try a deployment (non-destructive)
skillmeat deploy <artifact> --dry-run
```

## Recovery Options by Scenario

### Scenario: Completely Lost Collection

**User has no backup**

Options:
1. **Recreate from scratch**:
   ```bash
   skillmeat init
   skillmeat add anthropics/skills/code-review
   # Add other artifacts...
   ```

2. **Check if artifacts are in deployments**:
   ```bash
   # Find deployed artifacts
   find ~/repos -name ".claude/skills" -type d

   # You can re-add them from deployments
   ```

3. **Search marketplace** for artifacts they might have used:
   ```bash
   skillmeat marketplace-search <topic>
   ```

**Tell user**: "We can rebuild your collection. Do you remember what artifacts you had? We can look them up in the marketplace."

### Scenario: Corrupted Manifest

**Manifest file is malformed**

Steps:
1. Backup current state
2. Remove corrupted manifest:
   ```bash
   rm ~/.skillmeat/collection.toml
   ```
3. Re-initialize:
   ```bash
   skillmeat init
   ```
4. Re-add artifacts from memory or marketplace

### Scenario: Missing Artifacts Directory

**Artifacts directory deleted or moved**

Steps:
1. Check if backup exists:
   ```bash
   ls ~/.skillmeat.backup/artifacts/
   find ~ -name "artifacts" -type d 2>/dev/null
   ```

2. If backup exists, restore:
   ```bash
   cp -r ~/.skillmeat.backup/artifacts ~/.skillmeat/
   ```

3. If no backup, reinitialize and re-add artifacts

### Scenario: Lock File Corrupted

**Artifacts have wrong versions or dependencies broken**

Steps:
1. Remove lock file:
   ```bash
   rm ~/.skillmeat/collection.lock
   ```

2. Update all artifacts to re-lock:
   ```bash
   skillmeat update --all
   ```

3. Verify status:
   ```bash
   skillmeat status
   ```

## Common Issues & Fixes

### Issue: "collection.toml not found"

**Cause**: Collection was deleted or initialization failed

**Fix**:
```bash
# Re-initialize
skillmeat init

# Or restore from backup
cp ~/backup/collection.toml ~/.skillmeat/
```

### Issue: "Invalid TOML syntax"

**Cause**: Manifest file is corrupted

**Fix**:
```bash
# View corruption
cat ~/.skillmeat/collection.toml

# Compare with backup if available
diff ~/.skillmeat/collection.toml ~/backup/collection.toml

# Restore from backup or reinitialize
```

### Issue: "Artifacts not loading"

**Cause**: Artifacts directory missing or file permissions wrong

**Fix**:
```bash
# Check directory exists
ls ~/.skillmeat/artifacts/

# Fix permissions
chmod -R 755 ~/.skillmeat/

# If missing, restore from backup
cp -r ~/backup/artifacts ~/.skillmeat/
```

### Issue: "Circular dependency detected"

**Cause**: Lock file has conflicting versions

**Fix**:
```bash
# Remove lock file to force regeneration
rm ~/.skillmeat/collection.lock

# Update everything
skillmeat update --all --verbose

# Check for real conflicts
skillmeat verify
```

## What to Tell the User

### If data is lost:
> "I understand - losing data is frustrating. Here's the good news: if your artifacts are also deployed to your projects, we can recover them. Let me check your projects and we can re-add them to your collection."

### If manifest is corrupted:
> "Your manifest file got corrupted, probably from an interrupted operation. No worries - this is recoverable. We can either restore from a backup if you have one, or reinitialize and re-add your artifacts."

### If they don't have a backup:
> "This is a good opportunity to implement backups going forward. For now, let's focus on recovering what we can. Do you remember what artifacts you had, or can we find them in the marketplace?"

## Prevention Tips

Share these with users to prevent collection loss:

1. **Regular backups**:
   ```bash
   # Weekly backup script
   cp -r ~/.skillmeat ~/.skillmeat.backup.$(date +%Y%m%d)
   ```

2. **Monitor collection health**:
   ```bash
   skillmeat verify
   skillmeat status
   ```

3. **Use snapshots** for major changes:
   ```bash
   skillmeat snapshot "Before major update"
   ```

4. **Keep Git repository**:
   ```bash
   cd ~/.skillmeat
   git init
   git add .
   git commit -m "Initial collection"
   ```

## Escalation Conditions

Escalate to engineering if:
- Manifest is corrupted and won't re-initialize
- Artifacts directory can't be restored
- Permission errors prevent recovery
- User has custom modifications that can't be recovered

**Escalation path**: Create GitHub issue with:
- Error messages from recovery attempts
- Contents of collection.toml (sanitized)
- Available backups or recovery options
- OS and Python version

## Related Resources

- [Collections Guide](../../guides/collections-guide.md)
- [Backup Best Practices](../../guides/backup-strategy.md)
- [Snapshots and Rollback](../../guides/snapshots.md)
- [Troubleshooting Guide](../../guides/troubleshooting.md)

## Script Metadata

- **Audience**: Users with lost/corrupted collections
- **Complexity**: Medium
- **Resolution Time**: 10-15 minutes
- **Success Rate**: 80%+ (higher if backup available)
