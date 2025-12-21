---
title: Password Reset / Token Management
description: Support script for helping users reset authentication tokens and re-authenticate
audience: support-team
tags:
  - support-scripts
  - authentication
  - troubleshooting
created: 2025-11-17
updated: 2025-11-17
category: Support Scripts
status: Published
---

# Support Script: Password/Token Reset

**Issue**: User lost/compromised authentication token, or authentication is failing
**Time to resolve**: 5-10 minutes
**Difficulty**: Easy
**Escalation**: None needed (self-service)

## Quick Diagnosis

Ask the user: "Are you seeing authentication errors, or did you forget/lose your token?"

### Signs of Authentication Issue
- "Permission denied" errors
- "Invalid token" messages
- "Authentication failed"
- Cannot deploy or access web UI

### Signs of Lost Token
- "I don't know my token"
- "I lost my config files"
- Starting fresh on new machine

## Resolution Steps

### Step 1: Locate Config Files

Guide the user to find their SkillMeat configuration:

```bash
# Check if config exists
ls ~/.skillmeat/
```

Expected files:
```
config.toml          # General config
collection.toml      # Collection manifest
.skillmeat.auth      # Auth token file
```

### Step 2: Check Current Authentication

Try to verify current authentication:

```bash
# Check if authenticated
skillmeat config get github-token

# Or check web UI
skillmeat web dev
# Try to login in web interface
```

### Step 3: Reset Token (If Needed)

**Option A: Generate New Local Token**

```bash
# Remove old token
rm ~/.skillmeat/.skillmeat.auth

# Initialize new authentication
skillmeat init
# Follow prompts to set up new token
```

**Option B: Reset via Config**

```bash
# Edit config directly
nano ~/.skillmeat/config.toml

# Find and update auth section:
[auth]
token = "your-new-token-here"
provider = "local"
```

**Option C: Complete Reset**

If complete reset needed:

```bash
# Backup existing config
mkdir ~/.skillmeat.backup
cp -r ~/.skillmeat/* ~/.skillmeat.backup/

# Reset configuration
rm -rf ~/.skillmeat

# Re-initialize
skillmeat init
skillmeat config set github-token <your-github-token>
```

### Step 4: Verify Authentication Works

Test the reset:

```bash
# List collection
skillmeat list

# Check status
skillmeat status

# Try web UI
skillmeat web dev
```

## Common Issues & Fixes

### Issue: "Permission denied" in ~/.skillmeat/

**Cause**: File permissions are too restrictive

**Fix**:
```bash
# Fix permissions on config directory
chmod 700 ~/.skillmeat
chmod 600 ~/.skillmeat/config.toml
chmod 600 ~/.skillmeat/.skillmeat.auth
```

### Issue: Token file corrupted or invalid

**Cause**: Token file got corrupted or contains wrong format

**Fix**:
```bash
# Check token file format
cat ~/.skillmeat/.skillmeat.auth

# Should contain valid JSON or plaintext token
# If corrupt, remove and regenerate
rm ~/.skillmeat/.skillmeat.auth
skillmeat init
```

### Issue: "GitHub token invalid"

**Cause**: GitHub token was revoked or expired

**Fix**:
1. Generate new GitHub token at https://github.com/settings/tokens
2. Update in SkillMeat:
   ```bash
   skillmeat config set github-token <new-token>
   ```
3. Verify with:
   ```bash
   skillmeat status
   ```

### Issue: Web UI authentication failing

**Cause**: Web session expired or token mismatch

**Fix**:
```bash
# Clear web cache
rm -rf ~/.skillmeat/.web-cache

# Restart web server
skillmeat web dev

# Clear browser cache (Ctrl+Shift+Delete)
# Then reload page
```

## What to Tell the User

### If they lost their token:
> "No problem! We can generate a new one. Your token is stored locally on your computer, so you can safely reset it. We'll create a new authentication token and you'll be back up and running in a couple of minutes."

### If they're getting auth errors:
> "Let's check a few things. First, can you run `skillmeat status`? That will tell us if your token is still valid. If not, we can reset it with just a couple of commands."

### If they need to migrate machines:
> "Your token is machine-specific for security. On your new machine, you'll need to generate a fresh token. It's a one-time setup that takes about 2 minutes."

## Escalation Conditions

Escalate to engineering if:
- Token reset doesn't work after trying all steps
- Persistent "authentication failed" after reset
- File permission errors that can't be fixed
- Token file corrupted and can't be regenerated

**Escalation path**: Create GitHub issue with:
- OS and Python version
- Exact error message
- Steps already tried
- Output of `skillmeat --version`

## Prevention Tips

Share these with users to prevent future issues:

1. **Backup configuration**:
   ```bash
   cp -r ~/.skillmeat ~/.skillmeat.backup
   ```

2. **Never share tokens**: Keep tokens private and secure

3. **Secure GitHub token**:
   - Set expiration to 90 days
   - Use minimal required scopes
   - Revoke if compromised

4. **Use secure storage**:
   - SkillMeat stores tokens in system keychain when possible
   - Check keychain settings on your OS

## Related Resources

- [Configuration Guide](../../guides/configuration.md)
- [Security Best Practices](../../security/SECURITY_REVIEW.md)
- [Troubleshooting Guide](../../guides/troubleshooting.md)

## Script Metadata

- **Audience**: Users with auth issues
- **Complexity**: Easy
- **Resolution Time**: 5-10 minutes
- **Success Rate**: 95%+ (if user can reset token)
