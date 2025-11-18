# Marketplace Troubleshooting Guide

Comprehensive troubleshooting guide for SkillMeat marketplace users and operators addressing common issues, their causes, and solutions.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Search Issues](#search-issues)
- [Publishing Issues](#publishing-issues)
- [Performance Issues](#performance-issues)
- [Security and Verification](#security-and-verification)
- [Conflict Resolution](#conflict-resolution)
- [System Issues](#system-issues)
- [Getting Help](#getting-help)

## Installation Issues

### Installation Fails with "Network Error"

**Symptom:**
```
Error: Network error connecting to marketplace
Error code: NETWORK_UNREACHABLE
```

**Possible Causes:**
1. No internet connectivity
2. Marketplace server unreachable
3. Firewall/proxy blocking connection
4. DNS resolution failure

**Diagnostic Steps:**

```bash
# Check internet connectivity
ping 8.8.8.8

# Check marketplace server reachability
curl -v https://marketplace.skillmeat.dev/health

# Check DNS resolution
nslookup marketplace.skillmeat.dev
# or
dig marketplace.skillmeat.dev

# Check firewall/proxy
curl -v --proxy [proxy-url] https://marketplace.skillmeat.dev/health

# Test with different DNS
curl -v --resolve marketplace.skillmeat.dev:443:1.2.3.4 https://marketplace.skillmeat.dev/health
```

**Solutions:**

```bash
# Option 1: Retry with exponential backoff
skillmeat marketplace-install bundle --retry 5 --retry-delay 2

# Option 2: Use offline mode (if bundle downloaded previously)
skillmeat marketplace-install bundle --offline

# Option 3: Manual download and local install
# Download bundle manually:
# https://s3.amazonaws.com/skillmeat-marketplace/bundles/bundle-id.skillmeat-pack
# Then install locally:
skillmeat import downloaded-bundle.skillmeat-pack

# Option 4: Configure proxy
skillmeat config set http-proxy "http://proxy.company.com:8080"
skillmeat marketplace-install bundle

# Option 5: Wait for connectivity restoration
# Marketplace status: https://status.skillmeat.com
```

**Prevention:**
- Check marketplace status before bulk operations
- Use offline mode for critical environments
- Configure local caching proxy

### Installation Fails with "Authentication Error"

**Symptom:**
```
Error: Authentication failed
Error: Invalid or expired API token
```

**Possible Causes:**
1. Missing or invalid API token
2. Expired credentials
3. Token permissions insufficient
4. Account suspended

**Diagnostic Steps:**

```bash
# Check current authentication status
skillmeat auth status

# Verify token is set
skillmeat config get marketplace-token

# Check token validity (if accessible)
skillmeat auth validate

# Check account status
skillmeat marketplace-info --account
```

**Solutions:**

```bash
# Option 1: Re-authenticate
skillmeat auth login

# Option 2: Generate new token
# 1. Go to https://marketplace.skillmeat.dev/settings/tokens
# 2. Click "Generate New Token"
# 3. Set appropriate scopes (read, write, etc.)
# 4. Configure in SkillMeat:
skillmeat config set marketplace-token "new-token-here"

# Option 3: Use different authentication method
skillmeat auth login --method github     # Use GitHub auth
skillmeat auth login --method oauth      # Use OAuth

# Option 4: Check account status
# If suspended, contact support:
# Email: support@skillmeat.com
```

**Prevention:**
- Store tokens securely (not in git or scripts)
- Rotate tokens regularly (quarterly)
- Use appropriate permission scopes
- Enable 2FA on account

### Installation Hangs or Times Out

**Symptom:**
```
Installation in progress... [no changes for 5+ minutes]
Error: Installation timeout after 30 minutes
```

**Possible Causes:**
1. Large bundle size
2. Slow network connection
3. Server processing delay
4. Zombie process

**Diagnostic Steps:**

```bash
# Check network speed
speedtest-cli
# or
curl -w "Download speed: %{speed_download} bytes/sec\n" -o /dev/null -s http://speedtest.example.com/1gb.bin

# Monitor installation progress
# In another terminal:
tail -f ~/.skillmeat/logs/install.log

# Check for stuck processes
ps aux | grep skillmeat
ps aux | grep python

# Check system resources
top -b -n 1 | head -20
df -h
```

**Solutions:**

```bash
# Option 1: Increase timeout
skillmeat marketplace-install bundle --timeout 3600  # 1 hour

# Option 2: Cancel and retry
Ctrl+C
skillmeat marketplace-install bundle --retry 3

# Option 3: Install with compression
skillmeat marketplace-install bundle --compress

# Option 4: Kill stuck process
# Find process ID:
ps aux | grep skillmeat
# Kill it:
kill -9 <PID>

# Option 5: Check available space
df -h
# If disk full, free up space:
skillmeat cache clear
rm -rf ~/.skillmeat/tmp/*

# Option 6: Install in parts
skillmeat marketplace-install bundle --type skill
skillmeat marketplace-install bundle --type command
```

**Prevention:**
- Pre-download large bundles during off-peak
- Use wired connection for large installs
- Ensure adequate disk space
- Monitor system resources

### Installation Succeeds but Artifacts Don't Appear

**Symptom:**
```
Installation completed successfully
But artifacts not visible: skillmeat list shows no new artifacts
```

**Possible Causes:**
1. Installation cached but not written to disk
2. Wrong scope (user vs. local)
3. Artifacts in wrong location
4. Cache not refreshed

**Diagnostic Steps:**

```bash
# Check if artifacts exist in filesystem
ls -la ~/.claude/skills/user/      # User scope
ls -la ./.claude/skills/            # Local scope

# Check if database has artifacts
skillmeat list --all --include-hidden

# Check installation logs
tail -20 ~/.skillmeat/logs/install.log

# Verify artifact validity
skillmeat verify bundle-name

# Check cache status
skillmeat cache info
```

**Solutions:**

```bash
# Option 1: Refresh artifact cache
skillmeat cache clear collections
skillmeat list --refresh

# Option 2: Check installation scope
# Where were artifacts installed?
skillmeat show bundle-name --scope

# Install to correct scope:
skillmeat marketplace-install bundle --scope user    # Global
skillmeat marketplace-install bundle --scope local   # Project

# Option 3: Force rescan
skillmeat scan --force

# Option 4: Verify installation
skillmeat verify bundle-name --detailed

# Option 5: Check file permissions
ls -la ~/.claude/skills/user/artifact-name/
# If permission denied:
chmod -R u+rwx ~/.claude/

# Option 6: Reinstall
skillmeat marketplace-uninstall bundle
skillmeat marketplace-install bundle --force
```

**Prevention:**
- Always verify after install: `skillmeat list`
- Check scope before installing
- Enable installation logging

### Conflicts During Installation

**Symptom:**
```
Conflict detected: artifact already exists
Installation stopped, choose conflict strategy
```

**Understanding Conflict Strategies:**

```
Merge (default):
  Existing: skill:python-automation v1.0
  Installing: skill:python-automation v2.0
  Result: Updated to v2.0 (old version replaced)

Fork:
  Existing: skill:python-automation
  Installing: skill:python-automation
  Result: Both versions kept (new one renamed to python-automation-v2.0)

Skip:
  Existing: skill:python-automation
  Installing: skill:python-automation
  Result: Keep existing, don't install new version

Ask:
  For each conflict: Prompt user to choose merge/fork/skip
```

**Resolving Conflicts:**

```bash
# Option 1: Use merge (recommended for updates)
skillmeat marketplace-install bundle --strategy merge

# Option 2: Use fork (keep both versions)
skillmeat marketplace-install bundle --strategy fork
# Then manually delete old if not needed:
skillmeat remove skill:python-automation-v1.0

# Option 3: Use skip (keep existing)
skillmeat marketplace-install bundle --strategy skip

# Option 4: Use ask (decide per conflict)
skillmeat marketplace-install bundle --strategy ask

# Option 5: Manual conflict resolution
# First, remove conflicting artifacts:
skillmeat remove skill:existing-conflict
# Then install:
skillmeat marketplace-install bundle --strategy merge

# Option 6: Dry-run first
skillmeat marketplace-install bundle --strategy merge --dry-run
# Review what will happen
# Then proceed:
skillmeat marketplace-install bundle --strategy merge
```

**Best Practices:**
- Use `--dry-run` before conflicting installations
- Understand the difference between versions
- Backup before updating (use fork strategy first)
- Document reason for keeping duplicates

## Search Issues

### No Results Found

**Symptom:**
```
Search returns 0 results
"No matching bundles found"
```

**Possible Causes:**
1. Search term too specific
2. Marketplace empty or not synced
3. Search index outdated
4. Typos in search term

**Diagnostic Steps:**

```bash
# Check marketplace connectivity
skillmeat marketplace-health

# Test simple search
skillmeat marketplace-search "python"

# Check search index status
skillmeat admin marketplace search-stats

# Check if any bundles exist
curl https://marketplace.skillmeat.dev/api/bundles/count

# Try web UI search
# Access http://localhost:3000/marketplace
# Try same search in web interface
```

**Solutions:**

```bash
# Option 1: Try broader search
skillmeat marketplace-search python     # Instead of "python-automation-pro"

# Option 2: Search by tag
skillmeat marketplace-search --tags productivity

# Option 3: Browse instead of search
skillmeat marketplace-search --trending
skillmeat marketplace-search --new

# Option 4: Refresh search index
skillmeat admin marketplace cache clear --type search
skillmeat marketplace-search query

# Option 5: Use exact match
skillmeat marketplace-search --exact "exact-bundle-name"

# Option 6: Check if marketplace syncing
skillmeat admin marketplace jobs --type broker-sync
# If syncing stalled, try:
skillmeat admin marketplace brokers sync-all --force

# Option 7: Access via web UI
# May work even if CLI search fails
# https://marketplace.skillmeat.dev
```

**Prevention:**
- Marketplace syncs every 6 hours
- Full sync takes 15-30 minutes
- Check status page for sync issues

### Search Extremely Slow

**Symptom:**
```
Search query takes > 10 seconds
"Search timeout exceeded"
```

**Possible Causes:**
1. Large dataset, complex query
2. Search index not optimized
3. Server resource constraints
4. Network latency

**Diagnostic Steps:**

```bash
# Test search latency
time skillmeat marketplace-search "python"

# Check search engine health
curl -s http://elasticsearch:9200/_cluster/health | jq '.status'

# Monitor search performance
skillmeat admin marketplace metrics --period 1h --metrics search_latency

# Check network latency
ping marketplace.skillmeat.dev
```

**Solutions:**

```bash
# Option 1: Clear cache
skillmeat cache clear marketplace

# Option 2: Use more specific search
skillmeat marketplace-search "python automation"  # Instead of just "python"

# Option 3: Filter instead of search
skillmeat marketplace-search --tags productivity
skillmeat marketplace-search --type skill

# Option 4: Try at different time
# Peak hours (9 AM - 5 PM UTC) may be slower
# Try: 2 AM - 6 AM UTC (lowest traffic)

# Option 5: Report performance issue
curl -s https://marketplace.skillmeat.dev/api/debug/search-perf
# Share output with support team
```

**Prevention:**
- Use specific search terms
- Use filters/tags when possible
- Schedule searches for off-peak hours

### Search Returns Wrong Results

**Symptom:**
```
Search for "security" returns unrelated bundles
Results not matching query terms
```

**Possible Causes:**
1. Fuzzy matching too loose
2. Index contains outdated data
3. Typos in metadata
4. Relevance algorithm issue

**Diagnostic Steps:**

```bash
# Check search parameters
skillmeat marketplace-search "security" --verbose

# View search ranking scores
curl -s "https://marketplace.skillmeat.dev/api/search?q=security&debug=true" | jq '.results[] | {name, score}'

# Verify bundle metadata
skillmeat marketplace-info bundle-id --full
```

**Solutions:**

```bash
# Option 1: Use exact match
skillmeat marketplace-search --exact "Bundle Name"

# Option 2: Use advanced search syntax
skillmeat marketplace-search "security AND encryption"
skillmeat marketplace-search "security NOT monitoring"

# Option 3: Filter by type
skillmeat marketplace-search "security" --type command

# Option 4: Report incorrect listing
# Contact publisher:
skillmeat marketplace-info bundle-id --contact
# Or report to marketplace team:
# support@skillmeat.com

# Option 5: Use web UI with faceted search
# Better control over filtering
# https://marketplace.skillmeat.dev
```

## Publishing Issues

### "License Incompatibility Detected"

**Symptom:**
```
Error: License incompatibility detected
GPL artifacts with non-GPL bundle license
```

**Understanding License Compatibility:**

```
COMPATIBLE:
- MIT bundle + MIT artifacts ✓
- Apache bundle + Apache artifacts ✓
- MIT bundle + Apache artifacts ✓
- Apache bundle + MIT artifacts ✓

PROBLEMATIC:
- GPL bundle + MIT artifacts ⚠️ (warning)
- Non-GPL bundle + GPL artifacts ✗ (error)
- MIT bundle + GPL artifacts ✗ (error)
```

**Solutions:**

```bash
# Option 1: Check artifact licenses
skillmeat verify bundle.skillmeat-pack --show-licenses

# Option 2: Match bundle license to artifacts
# If all MIT/Apache:
--license "MIT"

# If any GPL:
--license "GPL-3.0-or-later"

# Option 3: Remove incompatible artifacts
skillmeat bundle-remove artifact-name
skillmeat bundle-build new-name --output bundle.skillmeat-pack

# Option 4: Use compatible license
# Check all artifacts licenses
# Use most permissive compatible license
skillmeat marketplace-publish bundle.skillmeat-pack \
  --license "MIT"

# Option 5: Review SPDX license compatibility
# https://spdx.org/licenses/
# Understand license implications before publishing
```

**Best Practices:**
- Document license strategy
- Choose compatible licenses when possible
- Consider MIT/Apache for maximum compatibility
- Review GPL implications before including

### "Security Scan Failed: Secrets Detected"

**Symptom:**
```
Error: Security scan failed
Potential AWS key found: AKIA*****
Potential API token found
```

**Diagnostic Steps:**

```bash
# Run security scan manually
skillmeat compliance-scan bundle.skillmeat-pack --verbose

# Find specific secrets
grep -r "AKIA\|sk_\|api_key\|password" artifacts/

# Check common secret files
find artifacts -name ".env" -o -name "*.key" -o -name "*.pem"
```

**Solutions:**

```bash
# Option 1: Remove secrets from code
# Search and replace hardcoded secrets with environment variables:
# Bad:
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"

# Good:
import os
AWS_KEY = os.environ.get("AWS_KEY")

# Option 2: Remove secret files
rm -f artifacts/**/.env
rm -f artifacts/**/*.key
rm -f artifacts/**/*.pem

# Option 3: Use .gitignore equivalent
# Ensure secrets not included in bundle:
rm -rf artifacts/config/secrets/
rm artifacts/**/credentials.json

# Option 4: Scan and remove
# Run scan to find all issues:
skillmeat compliance-scan bundle.skillmeat-pack --report-file scan.json

# Review report:
cat scan.json | jq '.findings'

# Fix each finding, then re-export

# Option 5: Override scan (NOT RECOMMENDED)
# Only in development:
skillmeat marketplace-publish bundle.skillmeat-pack \
  --skip-security

# WARNING: Do not use on production publishes
```

**Prevention:**
- Never hardcode secrets
- Use environment variables
- Use `.env` files (excluded from bundles)
- Use `git-secrets` to prevent accidental commits
- Scan before publishing

### "Bundle Too Large"

**Symptom:**
```
Error: Bundle exceeds maximum size
Maximum: 100 MB, Your bundle: 250 MB
```

**Solutions:**

```bash
# Option 1: Check bundle size
ls -lh bundle.skillmeat-pack

# Option 2: Identify large files
unzip -l bundle.skillmeat-pack | sort -k4 -n | tail -20

# Option 3: Remove unnecessary files
# From artifact directories before bundling:
rm -rf artifacts/*/.git
rm -rf artifacts/*/node_modules
rm -rf artifacts/*/venv
rm -rf artifacts/**/__pycache__
rm -rf artifacts/**/.pytest_cache

# Option 4: Exclude file types
skillmeat bundle-build my-bundle \
  --exclude "*.pyc" \
  --exclude "__pycache__" \
  --exclude "node_modules" \
  --exclude ".git"

# Option 5: Split into multiple bundles
# Group related artifacts:
skillmeat bundle-build python-tools \
  --artifacts skill:python-automation,skill:ml-analysis

skillmeat bundle-build cli-tools \
  --artifacts command:git-helper,command:docker-assist

# Option 6: Compress before publishing
skillmeat marketplace-publish bundle.skillmeat-pack --compress
```

**Best Practices:**
- Minimize dependencies
- Exclude unnecessary files
- Split large bundles
- Keep bundles focused and cohesive

### "Invalid Metadata"

**Symptom:**
```
Error: Invalid metadata
- Title: Too short (5 chars minimum)
- Description: Too long (5000 chars maximum)
- Tags: Invalid tag "mytag"
```

**Solutions:**

```bash
# Option 1: Review metadata requirements
# Title: 5-100 characters
skillmeat marketplace-publish bundle.skillmeat-pack \
  --title "Professional Development Tools"  # ✓ 30 chars

# Description: 100-5000 characters
# Write detailed, helpful descriptions

# Tags: Valid tags from allowed list
skillmeat marketplace-search --help | grep -A 20 "valid tags"

# Option 2: Validate metadata before publishing
skillmeat marketplace-publish bundle.skillmeat-pack \
  --title "..." \
  --description "..." \
  --tags "productivity,automation" \
  --dry-run

# Option 3: Fix specific issues
# Too short description - expand with more details
# Invalid tags - use only valid tags
# URLs not valid - fix HTTP/HTTPS URLs

# Option 4: Check license
# Must be valid SPDX identifier
# https://spdx.org/licenses/

# Option 5: Review other metadata
# Publisher name, email (required)
# Repository URL (if provided, must be valid)
# Homepage URL (if provided, must be valid)
```

## Performance Issues

### Deployments Take Too Long

**Symptom:**
```
Deployment started 30 minutes ago, still running
Expected: 2-5 minutes
```

**Diagnostic Steps:**

```bash
# Check deployment status
skillmeat deployment status <deployment-id> --verbose

# Monitor logs
tail -f ~/.skillmeat/logs/deploy.log

# Check network speed
speedtest-cli

# Check target project disk space
du -sh ~/target-project
df -h ~/target-project
```

**Solutions:**

```bash
# Option 1: Check network speed
# If slow (< 1 Mbps):
# - Use wired connection
# - Check ISP throttling
# - Try again during off-peak

# Option 2: Cancel and retry
Ctrl+C
skillmeat deploy skill:artifact --to ~/project

# Option 3: Deploy smaller bundles
# Instead of deploying entire bundle:
skillmeat deploy skill:python-automation --to ~/project
# Then:
skillmeat deploy command:git-helper --to ~/project

# Option 4: Check disk space
df -h
# If > 90% full:
rm -rf ~/.skillmeat/cache/*
skillmeat cache clear

# Option 5: Increase timeout
skillmeat deploy artifact --to ~/project --timeout 1800  # 30 min

# Option 6: Deploy in background
nohup skillmeat deploy artifact --to ~/project > deploy.log 2>&1 &

# Option 7: Use faster network
# Mobile hotspot or different ISP if current is slow
```

## Security and Verification

### "Signature Verification Failed"

**Symptom:**
```
Error: Signature verification failed
Bundle may have been modified
```

**Possible Causes:**
1. Bundle corrupted/modified
2. Signing key not in keychain
3. Untrusted signer

**Solutions:**

```bash
# Option 1: Verify signature manually
skillmeat verify-signature bundle.skillmeat-pack --verbose

# Option 2: Check trusted keys
skillmeat keys list
skillmeat keys trust <key-id>

# Option 3: Re-download bundle
# Original bundle may have been corrupted
rm bundle.skillmeat-pack
skillmeat marketplace-install bundle-id

# Option 4: Verify signer identity
skillmeat verify-signature bundle.skillmeat-pack --show-signer

# Check if signer is trusted:
# If trusted publisher (Anthropic, verified user): proceed
# If unknown publisher: contact support

# Option 5: Manual inspection
unzip -t bundle.skillmeat-pack
# If "test OK": file is valid, issue is with signature

# Option 6: Contact bundle publisher
skillmeat marketplace-info bundle-id --contact
# Ask for new signed bundle
```

**Prevention:**
- Verify from official sources only
- Keep signing keys up-to-date
- Trust established publishers

### "Hash Mismatch"

**Symptom:**
```
Error: Hash verification failed
Expected: abc123...
Actual: def456...
```

**Possible Causes:**
1. Incomplete download
2. File corruption
3. Network error during transfer

**Solutions:**

```bash
# Option 1: Clear cache and retry
skillmeat cache clear imports
skillmeat marketplace-install bundle --force-redownload

# Option 2: Manual download and verification
# Download bundle
curl -o bundle.skillmeat-pack "https://marketplace.skillmeat.dev/api/bundles/bundle-id/download"

# Verify hash
sha256sum bundle.skillmeat-pack

# Compare with expected hash from:
skillmeat marketplace-info bundle-id | grep sha256

# Option 3: Check network
# If frequent hash errors:
ping marketplace.skillmeat.dev
speedtest-cli

# Option 4: Use different network
# If current network unreliable, try:
# - Mobile hotspot
# - Different WiFi
# - Wired connection

# Option 5: Contact support
# If hash mismatch persists:
# Email: support@skillmeat.com
# Include: bundle-id, error message, network info
```

## Conflict Resolution

### Multiple Versions of Same Artifact

**Symptom:**
```
skillmeat list shows:
- artifact-name
- artifact-name-v2.0
- artifact-name-20240115
```

**Solutions:**

```bash
# Option 1: Keep one version
skillmeat remove artifact-name-v2.0
skillmeat remove artifact-name-20240115

# Option 2: Rename to clarify versions
# No built-in rename, so delete and reimport:
skillmeat remove artifact-name-old
skillmeat marketplace-install --version "old-version" --output-name "artifact-name-old"

# Option 3: Use aliases
skillmeat alias add artifact-name-old "artifact-name@1.0"
skillmeat alias add artifact-name "artifact-name@2.0"

# Option 4: Check which version to keep
skillmeat show artifact-name --verbose
skillmeat show artifact-name-v2.0 --verbose
# Compare dates, features, compatibility
# Keep the one you need

# Option 5: Document custom versions
# Create README:
echo "artifact-name: production version 2.0" > .claude/VERSIONS.md
echo "artifact-name-old: legacy version 1.0" >> .claude/VERSIONS.md
```

## System Issues

### Marketplace Server Appears Down

**Symptom:**
```
Error: Cannot reach marketplace.skillmeat.dev
Connection refused / timeout
```

**Verification Steps:**

```bash
# Check status page
curl https://status.skillmeat.com

# Check marketplace health
curl -I https://marketplace.skillmeat.dev/health

# Check network route
traceroute marketplace.skillmeat.dev

# Check DNS
nslookup marketplace.skillmeat.dev

# Check system DNS
cat /etc/resolv.conf
```

**Wait for Resolution:**
```bash
# Server may be temporarily down for maintenance
# Monitor status page: https://status.skillmeat.com

# Typical downtime: < 1 hour
# Scheduled maintenance: Announced 7 days in advance
```

**Workarounds:**
```bash
# Option 1: Install previously downloaded bundles
skillmeat import local-bundle.skillmeat-pack

# Option 2: Use offline features
skillmeat list --offline

# Option 3: Use previously cached data
skillmeat marketplace-search --cache-only

# Option 4: Wait and retry
# After 30 minutes, try again:
skillmeat marketplace-install bundle
```

## Getting Help

### When to Contact Support

**Contact support if:**
- Error persists after trying troubleshooting steps
- Errors appear to be on server side (not local)
- Security concerns with bundles
- Account or authentication issues

**DO NOT contact support for:**
- How-to questions (use documentation or GitHub discussions)
- Feature requests (use GitHub issues)
- General SkillMeat usage (use docs or forums)

### How to Get Help

**Preferred Order:**

1. **Check Documentation:**
   - [SkillMeat Docs](https://docs.skillmeat.com)
   - [Marketplace Guide](./marketplace-usage-guide.md)
   - [FAQ](../faq.md)

2. **Search Existing Issues:**
   - GitHub Issues: https://github.com/skillmeat/skillmeat/issues
   - GitHub Discussions: https://github.com/skillmeat/skillmeat/discussions
   - Community Forum: https://forum.skillmeat.com

3. **Collect Diagnostics:**
   ```bash
   skillmeat diagnose --output diagnostics.json
   ```

4. **Contact Support:**
   - **Email:** support@skillmeat.com
   - **Slack:** #skillmeat-support (community workspace)
   - **GitHub:** Create issue with `[SUPPORT]` tag

5. **Report Security Issues:**
   - **Email ONLY:** security@skillmeat.com
   - Do NOT post security issues publicly
   - Allow 48 hours for response

### Providing Helpful Information

When reporting issues, include:

```bash
# System information
skillmeat version
uname -a
python --version

# Error messages (full output, not truncated)
# Reproducible steps (exact commands to reproduce)

# Relevant logs
cat ~/.skillmeat/logs/install.log     # For install issues
cat ~/.skillmeat/logs/api.log         # For API errors
cat ~/.skillmeat/logs/marketplace.log # For marketplace issues

# Diagnostics
skillmeat diagnose --output diag.json
```

## See Also

- [Marketplace Usage Guide](./marketplace-usage-guide.md)
- [Publishing to Marketplace Guide](../guides/publishing-to-marketplace.md)
- [MCP Troubleshooting](./mcp-troubleshooting-charts.md)
- [SkillMeat Documentation](https://docs.skillmeat.com)
