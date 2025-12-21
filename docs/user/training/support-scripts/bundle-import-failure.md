---
title: Bundle Import Failures
description: Support script for resolving bundle import, extraction, and merge errors
audience: support-team
tags:
  - support-scripts
  - bundle
  - import
  - sharing
  - troubleshooting
created: 2025-11-17
updated: 2025-11-17
category: Support Scripts
status: Published
---

# Support Script: Bundle Import Failures

**Issue**: Bundle import fails, extraction errors, or merge conflicts can't be resolved
**Time to resolve**: 10-20 minutes
**Difficulty**: Medium
**Escalation**: None for most merge conflicts

## Quick Diagnosis

Ask the user:
1. "Are you getting an extraction error, signature error, or merge conflict?"
2. "Where did you get the bundle from?"
3. "What's the exact error message?"
4. "Have you received bundles from this person before?"

### Common Bundle Import Issues
- Signature verification failed
- File extraction error
- Hash mismatch
- Merge conflict can't be resolved
- Bundle format incompatible
- Insufficient disk space

## Issue: Signature Verification Failed

### Symptoms
- "Signature verification failed"
- "Invalid signature on bundle"
- "Bundle not signed by trusted key"

### Diagnosis Steps

```bash
# Check bundle signature
skillmeat verify-bundle my-collection.skillmeat-pack --verbose

# Check if signing keys are installed
ls ~/.skillmeat/keys/

# View bundle metadata
unzip -l my-collection.skillmeat-pack

# Check bundle integrity
unzip -t my-collection.skillmeat-pack
```

### Fix Steps

**Step 1: Verify bundle integrity first**

```bash
# Test if ZIP is valid
unzip -t my-collection.skillmeat-pack

# If corrupted, get fresh copy from sender
```

**Step 2: Update signing keys**

```bash
# Fetch latest signing keys
skillmeat fetch-signing-keys --force

# This downloads trusted keys from repository
```

**Step 3: Try import again**

```bash
# Verify bundle again
skillmeat verify-bundle my-collection.skillmeat-pack --verbose

# If still fails, try import with verbose
skillmeat import my-collection.skillmeat-pack --verbose
```

**Step 4: Import without verification (temporary)**

```bash
# ONLY if you absolutely trust the source
skillmeat import my-collection.skillmeat-pack --skip-verification

# Note: This bypasses security checks - use with caution
```

### Common Causes & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Signature verification failed | Old signing key | Update keys: `skillmeat fetch-signing-keys` |
| Bundle not signed | Unsigned bundle | Sender must sign: `skillmeat package --sign` |
| Untrusted key | Key not in trust store | Add sender's key: `skillmeat add-trusted-key <key>` |
| Expired signature | Bundle signature expired | Re-sign bundle: `skillmeat package --sign --force` |

### What to Tell the User

> "The bundle signature couldn't be verified. This is a security measure to prevent tampering. Let me update our signing keys and try again. If the bundle is unsigned, you'll need to ask the sender to sign it before sharing."

## Issue: File Extraction Failed

### Symptoms
- "Failed to extract bundle"
- "Permission denied" during extraction
- "Invalid ZIP file"
- "Insufficient disk space"

### Diagnosis Steps

```bash
# Check disk space
df -h

# Verify ZIP file
unzip -l my-collection.skillmeat-pack | head

# Check file permissions in directory
ls -la ~/

# Check if directory is writable
touch ~/.skillmeat/test-write && rm ~/.skillmeat/test-write
```

### Fix Steps

**Step 1: Verify bundle file**

```bash
# Check file size and type
ls -lh my-collection.skillmeat-pack
file my-collection.skillmeat-pack

# Should be ZIP format
```

**Step 2: Ensure sufficient disk space**

```bash
# Check available disk space
df -h /home

# Should have at least 2x bundle size available
# If low on space, clean up:
rm -rf ~/.skillmeat/.web-cache
rm -rf ~/.skillmeat/.marketplace-cache
```

**Step 3: Fix permissions**

```bash
# Fix directory permissions
chmod 700 ~/.skillmeat

# Fix file permissions
chmod 600 ~/.skillmeat/collection.toml

# Try again
skillmeat import my-collection.skillmeat-pack
```

**Step 4: Try extraction manually (debug)**

```bash
# Manual extraction to temp directory
mkdir /tmp/bundle-debug
cd /tmp/bundle-debug
unzip ~/my-collection.skillmeat-pack

# Check what's in there
ls -la

# This can show extraction errors
```

### Common Causes & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| Permission denied | Can't write to directory | Fix permissions: `chmod 700 ~/.skillmeat` |
| Insufficient space | Disk full | Clean cache, free up space: `df -h` |
| Invalid ZIP | Bundle corrupted | Get fresh copy from sender |
| Path too long | File path exceeds limit | Check bundle contents, shorten paths if needed |

## Issue: Merge Conflict

### Symptoms
- "Merge conflict detected"
- "Cannot auto-merge due to conflicts"
- Conflicting versions of same artifact
- User choice needed for conflict resolution

### Diagnosis Steps

```bash
# Try import to see conflicts
skillmeat import my-collection.skillmeat-pack --verbose

# View conflict details
skillmeat import my-collection.skillmeat-pack --show-conflicts

# Check current collection state
skillmeat list
```

### Fix Steps

**Step 1: Understand the conflict**

```bash
# View detailed conflict information
skillmeat import my-collection.skillmeat-pack --show-conflicts --detailed

# Shows:
# - Conflicting artifacts
# - Your version vs incoming version
# - Recommendations for resolution
```

**Step 2: Choose resolution strategy**

For each conflict, you can:

**Option A: Keep your version (overwrite incoming)**
```bash
skillmeat import my-collection.skillmeat-pack --conflict-strategy=skip
# or
skillmeat import my-collection.skillmeat-pack --conflict-strategy=local
```

**Option B: Accept incoming version (overwrite yours)**
```bash
skillmeat import my-collection.skillmeat-pack --conflict-strategy=remote
```

**Option C: Create fork (keep both, rename incoming)**
```bash
skillmeat import my-collection.skillmeat-pack --conflict-strategy=fork
# Creates artifact with "_imported_v2" suffix
```

**Option D: Smart merge (auto-resolve if possible)**
```bash
skillmeat import my-collection.skillmeat-pack --conflict-strategy=merge
# Attempts intelligent merge of non-conflicting changes
```

**Step 3: Handle specific conflicts**

```bash
# Interactive mode to decide per artifact
skillmeat import my-collection.skillmeat-pack --interactive

# For each conflict, choose:
# [k] Keep local version
# [i] Import incoming version
# [f] Fork (keep both)
# [m] Merge (if possible)
# [s] Skip this artifact
```

**Step 4: Verify import**

```bash
# After resolving conflicts, verify
skillmeat list

# Check imported artifacts
skillmeat list --source=imported

# Verify deployment still works
skillmeat deploy <artifact> --dry-run
```

### Common Conflicts & Resolution

| Conflict | Scenario | Recommended Resolution |
|----------|----------|------------------------|
| Different versions | You updated locally, sender also updated | Use merge strategy, manual review if conflicts |
| Artifact removed | You deleted artifact, sender has newer version | Choose skip to keep local state |
| Metadata changed | You modified description, sender updated license | Merge or fork |
| Major version bump | Incoming has breaking changes | Use fork to keep both, test new version |

### What to Tell the User

> "The bundle has some artifacts that conflict with what you already have. This is normal when both you and your teammate have been working on similar things. Let me walk you through your options:
>
> 1. **Keep your version** - You stay with what you have
> 2. **Take their version** - You accept the incoming changes
> 3. **Keep both** - Create a fork with a different name
> 4. **Smart merge** - Combine changes intelligently
>
> What's your preference for each conflicting artifact?"

## Issue: Bundle Format Incompatible

### Symptoms
- "Bundle format incompatible"
- "Unknown bundle version"
- "Cannot read bundle metadata"

### Diagnosis Steps

```bash
# Check bundle contents
unzip -l my-collection.skillmeat-pack

# Look for:
# - manifest.json
# - metadata.json
# - .skillmeat/metadata

# Check SkillMeat version
skillmeat --version

# Check bundle creation date
unzip -l my-collection.skillmeat-pack | grep manifest
```

### Fix Steps

**Step 1: Check bundle format**

```bash
# View bundle metadata
unzip -p my-collection.skillmeat-pack manifest.json | jq .

# Should show:
# - "format_version": 1
# - "created_at": timestamp
# - "skillmeat_version": compatible version
```

**Step 2: Update SkillMeat if needed**

```bash
# Bundle was created with newer SkillMeat version
# Update to latest version
pip install --upgrade skillmeat

# Verify update
skillmeat --version

# Try import again
skillmeat import my-collection.skillmeat-pack
```

**Step 3: Ask sender for compatibility info**

```bash
# If still incompatible:
# Ask sender for bundle details:
# - SkillMeat version used
# - Bundle creation date
# - Any custom modifications

# Or ask for re-export with current version
```

### Common Causes & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Incompatible version | Bundle from newer SkillMeat | Update SkillMeat: `pip install --upgrade skillmeat` |
| Old format | Bundle from old SkillMeat | Ask sender to re-export with new version |
| Corrupted manifest | Bundle metadata invalid | Get fresh bundle from sender |
| Custom format | Non-standard bundle | Verify bundle format with sender |

## Prevention Tips

Share with users:

1. **Request signed bundles**:
   ```bash
   # Always ask for signed bundles
   skillmeat package --sign
   ```

2. **Verify before importing**:
   ```bash
   skillmeat verify-bundle <bundle> --verbose
   ```

3. **Plan merge strategy ahead**:
   ```bash
   # Decide strategy before importing
   skillmeat import <bundle> --show-conflicts
   ```

4. **Keep versions in sync**:
   ```bash
   # Both parties should use same SkillMeat version
   pip install --upgrade skillmeat
   ```

5. **Document bundle source**:
   ```bash
   # Store bundle metadata
   echo "From: colleague, Date: $(date)" > bundle-info.txt
   ```

## Escalation Conditions

Escalate to engineering if:
- Bundle consistently fails signature verification
- ZIP file corrupted and can't be recovered
- Merge conflicts that can't be resolved automatically
- Bundle format truly incompatible with current version
- Disk space issues that affect other operations

**Escalation path**: Create GitHub issue with:
- Bundle creation source and date
- Exact error message and full logs
- SkillMeat version on both sender and receiver side
- Bundle format version if known
- Steps to reproduce

## Related Resources

- [Team Sharing Guide](../../guides/team-sharing-guide.md)
- [Bundle Format Specification](../../architecture/bundle-format.md)
- [Merge Strategies](../../guides/merge-strategies.md)
- [Security Best Practices](../../security/SECURITY_REVIEW.md)

## Script Metadata

- **Audience**: Users importing team bundles
- **Complexity**: Medium
- **Resolution Time**: 10-20 minutes
- **Success Rate**: 90%+ (merge conflicts resolution-dependent)
