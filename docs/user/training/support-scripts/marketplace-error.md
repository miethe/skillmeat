---
title: Marketplace Errors and Fixes
description: Support script for resolving marketplace search, install, and publishing issues
audience: support-team
tags:
  - support-scripts
  - marketplace
  - troubleshooting
created: 2025-11-17
updated: 2025-11-17
category: Support Scripts
status: Published
---

# Support Script: Marketplace Errors and Fixes

**Issue**: Marketplace search fails, install errors, or publishing issues
**Time to resolve**: 5-15 minutes depending on issue
**Difficulty**: Medium
**Escalation**: None for most issues

## Quick Diagnosis

Ask the user:
1. "Are you trying to search, install, or publish?"
2. "What's the exact error message you see?"
3. "When did this start happening?"

### Common Marketplace Issues
- Search returns no results or times out
- Install fails with signature or hash error
- Publishing validation fails
- Marketplace UI slow or unresponsive
- License compatibility errors

## Issue: Marketplace Search Not Working

### Symptoms
- `skillmeat marketplace-search` returns nothing
- "Marketplace unavailable" error
- Search times out
- Web UI marketplace tab is empty

### Diagnosis Steps

```bash
# Check connectivity
ping marketplace.skillmeat.dev

# Test search directly
skillmeat marketplace-search test --verbose

# Check if brokers are configured
skillmeat config get marketplace

# View marketplace logs
tail ~/.skillmeat/logs/marketplace.log
```

### Fix Steps

**Step 1: Check broker configuration**

```bash
# View current brokers
cat ~/.skillmeat/marketplace.toml

# Should have at least one enabled broker
# Default should include:
# [brokers.skillmeat]
# enabled = true
```

**Step 2: Verify network connectivity**

```bash
# Test connection to marketplace
curl -I https://marketplace.skillmeat.dev

# Should return 200 OK
```

**Step 3: Reset marketplace cache**

```bash
# Clear marketplace cache
rm -rf ~/.skillmeat/.marketplace-cache

# Retry search
skillmeat marketplace-search <query>
```

**Step 4: Restart services**

```bash
# Kill any running web services
pkill -f "skillmeat web"

# Restart
skillmeat web dev
```

### Common Causes & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| No brokers enabled | Config issue | Enable brokers in `marketplace.toml` |
| Network blocked | Firewall/proxy | Check network settings, use VPN if needed |
| Marketplace down | Service issue | Check status page, try again later |
| Cache corrupted | Old data | Clear cache: `rm -rf ~/.skillmeat/.marketplace-cache` |
| Rate limited | Too many requests | Wait 5 minutes before retrying |

## Issue: Marketplace Install Fails

### Symptoms
- "Signature verification failed"
- "Hash mismatch"
- "Invalid bundle format"
- "Installation interrupted"

### Diagnosis Steps

```bash
# Check bundle integrity
unzip -t downloaded-bundle.skillmeat-pack

# Verify bundle signature
skillmeat verify-bundle downloaded-bundle.skillmeat-pack --verbose

# Check installation logs
tail ~/.skillmeat/logs/install.log
```

### Fix Steps

**Step 1: Verify bundle file**

```bash
# Check file size and type
ls -lh downloaded-bundle.skillmeat-pack
file downloaded-bundle.skillmeat-pack

# Should be ZIP format with reasonable size
```

**Step 2: Re-download bundle**

```bash
# Delete corrupted bundle
rm downloaded-bundle.skillmeat-pack

# Re-download from marketplace
skillmeat marketplace-install <artifact-id>
```

**Step 3: Check signing keys**

```bash
# Verify signing keys are installed
ls ~/.skillmeat/keys/

# If missing, update:
skillmeat fetch-signing-keys
```

**Step 4: Try with --skip-verification (temporary)**

```bash
# CAREFUL: Only use if you trust the source
skillmeat marketplace-install <artifact-id> --skip-verification

# Note: This is not recommended for production
```

### Common Causes & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| Signature verification failed | Invalid or missing signing key | Update keys: `skillmeat fetch-signing-keys` |
| Hash mismatch | Bundle corrupted during download | Re-download bundle |
| Invalid bundle format | Older bundle format incompatible | Update SkillMeat: `pip install --upgrade skillmeat` |
| Installation interrupted | Disk full or permission issue | Check disk space: `df -h`, fix permissions |

## Issue: Publishing Fails

### Symptoms
- "Validation failed"
- "License not compatible"
- "Metadata incomplete"
- "Security scan failed"

### Diagnosis Steps

```bash
# Validate bundle before publishing
skillmeat package --validate

# Check metadata completeness
skillmeat package --metadata-check

# Run security scan
skillmeat package --security-scan
```

### Fix Steps

**Step 1: Fix metadata**

```bash
# Check what's missing
skillmeat package --validate --verbose

# Edit metadata file
nano ~/.skillmeat/artifacts/<name>/ARTIFACT.yaml

# Required fields:
# - title
# - description
# - version
# - author
# - license (SPDX identifier)
```

**Step 2: Fix license issues**

```bash
# Check license compatibility
skillmeat package --license-check

# Update license to SPDX identifier:
# MIT, Apache-2.0, GPL-3.0, BSD-3-Clause, etc.

# Valid SPDX check: https://spdx.org/licenses/
```

**Step 3: Address security issues**

```bash
# See security scan results
skillmeat package --security-scan --detailed

# Common issues:
# - Remove hardcoded credentials
# - Remove dangerous patterns (eval, exec)
# - Remove test/debug code
# - Update vulnerable dependencies
```

**Step 4: Re-validate and publish**

```bash
# Validate again
skillmeat package --validate

# If all checks pass, publish
skillmeat marketplace-publish
```

## Issue: Marketplace UI Slow or Unresponsive

### Symptoms
- Web marketplace tab takes long to load
- Search hangs in web UI
- Install button doesn't respond
- Marketplace feed is empty

### Diagnosis Steps

```bash
# Check web service status
ps aux | grep "skillmeat web"

# Check web server logs
tail ~/.skillmeat/logs/web.log

# Test API directly
curl -s http://localhost:3000/api/marketplace/search?q=test | jq .
```

### Fix Steps

**Step 1: Clear web cache**

```bash
# Clear all caches
rm -rf ~/.skillmeat/.web-cache
rm -rf ~/.skillmeat/.marketplace-cache

# Clear browser cache:
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete
# Safari: Cmd+Y, clear all
```

**Step 2: Restart web service**

```bash
# Kill web service
pkill -f "skillmeat web"

# Wait 2 seconds
sleep 2

# Restart
skillmeat web dev
```

**Step 3: Check system resources**

```bash
# Check CPU usage
top -bn1 | head -20

# Check available memory
free -h

# Check disk space
df -h ~/.skillmeat
```

**Step 4: Reduce concurrent operations**

```bash
# If marketplace is overloaded, wait and retry
# Or configure to use fewer broker connections:
# Edit ~/.skillmeat/marketplace.toml:
# [settings]
# max_concurrent_brokers = 2
```

## What to Tell the User

### If marketplace is unavailable:
> "The marketplace seems to be temporarily unavailable. This can happen if our servers are being updated or if there's a network issue. Try again in a few minutes, or use the CLI search command instead."

### If signature verification fails:
> "The bundle signature couldn't be verified. This usually means either the bundle was corrupted during download or your signing keys need updating. Let's re-download and try again."

### If publishing fails validation:
> "Your artifact needs some adjustments before publishing. Common issues are missing metadata, license information, or security concerns. I'll help you fix each one."

## Prevention Tips

Share with users:

1. **Keep SkillMeat updated**:
   ```bash
   pip install --upgrade skillmeat
   ```

2. **Regularly update signing keys**:
   ```bash
   skillmeat fetch-signing-keys
   ```

3. **Test before publishing**:
   ```bash
   skillmeat package --validate
   skillmeat package --security-scan
   ```

4. **Monitor marketplace health**:
   ```bash
   skillmeat marketplace-status
   ```

## Escalation Conditions

Escalate to engineering if:
- Marketplace completely unavailable for 30+ minutes
- Systematic signature verification failures
- Corrupted bundles consistently from one broker
- Security scan shows real vulnerabilities

**Escalation path**: Create GitHub issue with:
- Error messages and logs
- Marketplace broker info
- Reproducible steps
- SkillMeat version

## Related Resources

- [Marketplace Guide](../../guides/marketplace-usage-guide.md)
- [Publishing Guide](../../guides/publishing-to-marketplace.md)
- [Security Best Practices](../../security/SECURITY_REVIEW.md)
- [Marketplace Operations](../../runbooks/marketplace-operations.md)

## Script Metadata

- **Audience**: Users with marketplace issues
- **Complexity**: Medium
- **Resolution Time**: 5-15 minutes
- **Success Rate**: 85%+ (higher for simple fixes)
