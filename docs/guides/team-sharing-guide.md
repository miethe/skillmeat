# Team Sharing Guide

This guide covers sharing SkillMeat artifact collections with teammates securely using signed bundles, team vaults, and permission management.

## Table of Contents

- [Overview](#overview)
- [Exporting Collections](#exporting-collections)
- [Signing and Security](#signing-and-security)
- [Sharing Methods](#sharing-methods)
- [Importing Bundles](#importing-bundles)
- [Team Vault Configuration](#team-vault-configuration)
- [Permissions and Access Control](#permissions-and-access-control)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Team sharing in SkillMeat allows you to:

- **Export** curated artifact bundles for teammates
- **Sign** bundles with Ed25519 signatures for security
- **Verify** bundle integrity and authenticity
- **Share** via file transfer, Git, cloud storage, or recommendation links
- **Import** bundles with conflict resolution
- **Manage** team vaults with access controls

### Supported Sharing Methods

1. **Direct File Sharing** - Copy bundle files to shared location
2. **Git Repository** - Store bundles in Git for version control
3. **Cloud Storage** - Upload to S3, Azure, or similar services
4. **Recommendation Links** - Generate shareable preview URLs
5. **Team Vault** - Centralized team artifact repository

## Exporting Collections

### Creating a Bundle

**Export Entire Collection:**
```bash
skillmeat export my-collection \
  --output my-collection.skillmeat-pack
```

**Export Specific Artifacts:**
```bash
skillmeat export dev-tools \
  --artifacts skill:python-automation,command:git-helper,agent:code-review \
  --output dev-tools.skillmeat-pack
```

**Export by Tags:**
```bash
skillmeat export productivity-pack \
  --tags productivity,automation,development \
  --output productivity-pack.skillmeat-pack
```

**Export by Type:**
```bash
# Only skills
skillmeat export skills-only \
  --type skill \
  --output skills-bundle.skillmeat-pack

# Only commands and agents
skillmeat export commands-agents \
  --type command,agent \
  --output tools.skillmeat-pack
```

### Bundle Structure

A `.skillmeat-pack` bundle contains:

```
my-collection.skillmeat-pack (ZIP archive)
├── manifest.json          # Artifact metadata and inventory
├── artifacts/             # Artifact files and directories
│   ├── skill-python/
│   ├── command-git/
│   └── agent-review/
├── signature.json         # Ed25519 digital signature
├── hashes.json           # SHA-256 hashes for integrity verification
├── metadata.json         # Bundle metadata (version, author, etc.)
└── LICENSE               # Bundle license information
```

### Bundle Metadata

Control what's included in your bundle:

```bash
skillmeat export my-pack \
  --title "My Team's Productivity Tools" \
  --description "Curated collection for our team" \
  --version "1.0.0" \
  --author "John Doe" \
  --license "MIT" \
  --homepage "https://team.example.com" \
  --output my-pack.skillmeat-pack
```

## Signing and Security

### Automatic Signing

Bundles are automatically signed during export using Ed25519 keys:

```bash
# Export creates a signed bundle automatically
skillmeat export my-pack --output my-pack.skillmeat-pack
# File includes: signature.json with Ed25519 signature
```

### Managing Signing Keys

**View Available Keys:**
```bash
skillmeat keys list
```

**Create New Signing Key:**
```bash
# Creates key and stores in system keychain
skillmeat keys create signing-key-2024
```

**Use Specific Key for Signing:**
```bash
skillmeat export my-pack \
  --sign-with "signing-key-2024" \
  --output my-pack.skillmeat-pack
```

### Verifying Signatures

**Verify Bundle Signature:**
```bash
skillmeat verify-signature my-pack.skillmeat-pack
```

Output shows:
- Signature validity (valid/invalid)
- Signing key ID
- Signature timestamp
- Signer identity

**Verify Hashes:**
```bash
# Automatically done during import
# Or manually verify:
skillmeat verify-hashes my-pack.skillmeat-pack
```

### Security Scanning

Bundles are scanned for security issues during export:

```bash
# Automatic scan results during export
# Or manually scan:
skillmeat compliance-scan my-pack.skillmeat-pack
```

Scans check for:
- Hardcoded secrets (API keys, tokens, passwords)
- Suspicious patterns (eval, exec, shell injection)
- Malicious code indicators
- Dependency vulnerabilities
- License compatibility

## Sharing Methods

### Method 1: Direct File Sharing

**Share via File System:**
```bash
# Copy bundle to shared folder
cp my-pack.skillmeat-pack /shared/team-artifacts/

# Or shared network drive
cp my-pack.skillmeat-pack /mnt/team-share/skillmeat/
```

**Share via Email:**
```bash
# Bundle is a single file, suitable for email
# For large files (>20MB), consider cloud storage instead
```

### Method 2: Git Repository

**Create Team Vault Repository:**
```bash
# On team GitHub/GitLab:
git clone git@github.com:team/skillmeat-packs.git
cd skillmeat-packs
mkdir -p v1.0
cp ~/my-pack.skillmeat-pack v1.0/
git add v1.0/my-pack.skillmeat-pack
git commit -m "Add team dev tools bundle v1.0"
git push
```

**Access in SkillMeat:**
```bash
# Configure Git vault in config
skillmeat config vault-git-url "git@github.com:team/skillmeat-packs.git"

# Import from Git vault
skillmeat import-from-vault --name "my-pack" --version "v1.0"
```

### Method 3: Cloud Storage (S3)

**Upload Bundle to S3:**
```bash
# Using AWS CLI
aws s3 cp my-pack.skillmeat-pack s3://team-skillmeat/packs/v1.0/

# Or using SkillMeat
skillmeat share upload s3://team-skillmeat/ \
  --file my-pack.skillmeat-pack \
  --public-url "https://team-artifacts.s3.amazonaws.com/my-pack.skillmeat-pack"
```

**Access in SkillMeat:**
```bash
# Import from S3 URL
skillmeat import https://team-artifacts.s3.amazonaws.com/my-pack.skillmeat-pack

# Or configure S3 vault
skillmeat config vault-s3-bucket "team-skillmeat"
skillmeat import-from-vault --name "my-pack"
```

### Method 4: Recommendation Links

**Generate Shareable Link:**
```bash
# Creates recommendation link (read-only preview)
skillmeat share recommend my-pack.skillmeat-pack
# Output: skillmeat://recommend/abc123def456
```

**Share Link with Teammates:**
```
Hey team! Check out this artifact bundle:
skillmeat://recommend/abc123def456

Or install with:
skillmeat import skillmeat://recommend/abc123def456
```

**Preview Without Installing:**
```bash
# Teammates can preview before installing
skillmeat preview skillmeat://recommend/abc123def456

# Shows:
# - Artifact list and metadata
# - Bundle signature and verification
# - Security scan results
# - Installation instructions
```

### Method 5: Team Vault (Centralized)

**Create Team Vault:**
```bash
# Admin sets up central vault
skillmeat vault create team-vault \
  --description "Centralized team artifacts" \
  --members team@example.com,john@example.com \
  --permissions read,write
```

**Add Bundles to Vault:**
```bash
skillmeat vault add team-vault my-pack.skillmeat-pack \
  --version "1.0" \
  --category "dev-tools"
```

**Browse Team Vault:**
```bash
# List available bundles
skillmeat vault browse team-vault

# Import from vault
skillmeat vault import team-vault/my-pack --version "1.0"
```

## Importing Bundles

### Basic Import

**Import from File:**
```bash
skillmeat import my-pack.skillmeat-pack
```

**Import from URL:**
```bash
skillmeat import https://team-artifacts.s3.amazonaws.com/my-pack.skillmeat-pack
```

**Import from Recommendation Link:**
```bash
skillmeat import skillmeat://recommend/abc123def456
```

### Specifying Import Options

**Conflict Resolution Strategies:**
```bash
# Merge (overwrite with new version) - default
skillmeat import my-pack.skillmeat-pack --strategy merge

# Fork (keep both, rename new)
skillmeat import my-pack.skillmeat-pack --strategy fork

# Skip (keep existing, don't import)
skillmeat import my-pack.skillmeat-pack --strategy skip

# Ask (prompt for each conflict)
skillmeat import my-pack.skillmeat-pack --strategy ask
```

**Custom Destination:**
```bash
# Import to specific scope
skillmeat import my-pack.skillmeat-pack --scope user   # Global scope
skillmeat import my-pack.skillmeat-pack --scope local  # Project scope
```

**Selective Import:**
```bash
# Import only specific artifacts
skillmeat import my-pack.skillmeat-pack \
  --artifacts skill:python-automation,command:git-helper

# Import only specific types
skillmeat import my-pack.skillmeat-pack --type skill,command
```

### Import Verification

SkillMeat automatically verifies during import:

1. **Signature Verification**
   - Ed25519 signature validity
   - Signer identity verification
   - Signature timestamp validation

2. **Hash Verification**
   - SHA-256 hash integrity
   - File corruption detection
   - Download integrity check

3. **Security Scanning**
   - Hardcoded secrets detection
   - Malicious pattern identification
   - Dependency vulnerability scan

4. **License Compatibility**
   - Bundle license validation
   - Artifact license compatibility
   - Existing license conflicts

5. **Integrity Checks**
   - Archive validity
   - File completeness
   - Manifest consistency

**View Verification Results:**
```bash
# Show detailed verification results
skillmeat import my-pack.skillmeat-pack --show-verification

# Expected output:
# ✓ Signature valid (key: abc123...)
# ✓ Hash verification passed
# ✓ License compatible
# ✓ No security issues detected
# ? 1 artifact conflict (python-automation)
```

### Conflict Resolution

When artifacts already exist:

**Merge Strategy (Default):**
```bash
# Overwrites existing with imported version
skillmeat import my-pack.skillmeat-pack --strategy merge

# Result: python-automation updated to new version
```

**Fork Strategy:**
```bash
# Keeps both versions with different names
skillmeat import my-pack.skillmeat-pack --strategy fork

# Result:
# - python-automation (existing, kept)
# - python-automation-imported-20240117 (new version)
```

**Skip Strategy:**
```bash
# Keeps existing, doesn't import conflicting artifacts
skillmeat import my-pack.skillmeat-pack --strategy skip

# Result: Skips python-automation, imports others
```

**Ask Strategy:**
```bash
# Prompts for each conflict
skillmeat import my-pack.skillmeat-pack --strategy ask

# Prompts for each:
# ? python-automation: merge/fork/skip/cancel
```

## Team Vault Configuration

### Setting Up Git Vault

**Configure in Config File:**
```toml
# ~/.skillmeat/sharing.toml
[vault.git]
name = "team-vault"
url = "git@github.com:team/skillmeat-packs.git"
branch = "main"
auth_token = "env:GITHUB_TOKEN"
permissions = "read,write"
members = ["john@example.com", "jane@example.com"]
```

**Or via CLI:**
```bash
skillmeat vault configure git \
  --url "git@github.com:team/skillmeat-packs.git" \
  --branch "main" \
  --auth-token-env "GITHUB_TOKEN"
```

### Setting Up S3 Vault

**Configure in Config File:**
```toml
[vault.s3]
name = "team-vault-s3"
bucket = "my-team-skillmeat"
region = "us-west-2"
prefix = "artifact-packs/"
access_key = "env:AWS_ACCESS_KEY_ID"
secret_key = "env:AWS_SECRET_ACCESS_KEY"
public_url = "https://team-artifacts.s3.amazonaws.com"
permissions = "read,write"
```

**Or via CLI:**
```bash
skillmeat vault configure s3 \
  --bucket "my-team-skillmeat" \
  --region "us-west-2" \
  --access-key-env "AWS_ACCESS_KEY_ID" \
  --secret-key-env "AWS_SECRET_ACCESS_KEY"
```

### Managing Vault Access

**Add Team Members:**
```bash
skillmeat vault members add team-vault john@example.com --role write
skillmeat vault members add team-vault jane@example.com --role read
```

**Remove Team Members:**
```bash
skillmeat vault members remove team-vault bob@example.com
```

**View Vault Members:**
```bash
skillmeat vault members list team-vault
```

## Permissions and Access Control

### Role-Based Access Control

**Available Roles:**
- **admin** - Full control (add, remove, configure)
- **write** - Add and update bundles
- **read** - View and import bundles
- **none** - No access

**Set Member Permissions:**
```bash
# Grant write access
skillmeat vault members update team-vault john@example.com --role write

# Grant read-only access
skillmeat vault members update team-vault contractor@example.com --role read
```

### Bundle-Level Permissions

**Restrict Bundle Access:**
```bash
# Make bundle private (only accessible to owner)
skillmeat vault update my-pack.skillmeat-pack --visibility private

# Share with specific members
skillmeat vault update my-pack.skillmeat-pack --visibility team

# Make publicly accessible
skillmeat vault update my-pack.skillmeat-pack --visibility public
```

### Audit and Compliance

**View Access Log:**
```bash
skillmeat vault audit team-vault

# Shows:
# - Who accessed what bundle
# - When access occurred
# - Import success/failure
# - IP address and device
```

**Export Audit Report:**
```bash
skillmeat vault audit team-vault --export report.json --days 30
```

## Best Practices

### 1. Bundle Organization

**Use Descriptive Names:**
```bash
# Good
skillmeat export dev-tools-q1-2024.skillmeat-pack
skillmeat export team-onboarding-skills.skillmeat-pack

# Avoid
skillmeat export bundle.skillmeat-pack
skillmeat export stuff.skillmeat-pack
```

**Include Version Numbers:**
```bash
# Semantic versioning
skillmeat export team-tools-v1.2.3.skillmeat-pack
```

### 2. Documentation and Metadata

**Complete Bundle Metadata:**
```bash
skillmeat export team-pack \
  --title "Team Development Tools" \
  --description "Essential development artifacts for all team members" \
  --version "1.2.0" \
  --author "Tech Lead" \
  --homepage "https://team.example.com/tools" \
  --output team-tools-v1.2.0.skillmeat-pack
```

**Include Changelogs:**
```bash
# Update description to include changes
--description "Version 1.2.0
- Added Python static analysis command
- Updated linting rules
- Fixed git workflow agent bugs
- Improved documentation"
```

### 3. Security and Signing

**Always Sign Bundles:**
```bash
# Signing is automatic, but verify:
skillmeat verify-signature team-pack.skillmeat-pack
```

**Rotate Signing Keys Regularly:**
```bash
# Create new key quarterly
skillmeat keys create signing-key-q1-2024

# Use new key for exports
skillmeat export team-pack --sign-with "signing-key-q1-2024"
```

**Review Security Scans:**
```bash
# Check compliance before sharing
skillmeat compliance-scan team-pack.skillmeat-pack

# Address any warnings
```

### 4. Version Control

**Track Bundle Changes in Git:**
```bash
git add team-tools-v1.2.0.skillmeat-pack
git commit -m "chore: add team tools bundle v1.2.0

- Added Python linting command
- Updated ML analysis skill
- Bumped tool versions"
```

### 5. Testing Before Sharing

**Dry-Run Import:**
```bash
# Test import without making changes
skillmeat import team-pack.skillmeat-pack --dry-run

# Review what will be imported
# Check for conflicts
# Verify signatures and hashes
```

**Verify in Clean Environment:**
```bash
# Test in temporary directory
mkdir test-import
cd test-import
skillmeat init
skillmeat import ../team-pack.skillmeat-pack
# Verify artifacts work correctly
```

### 6. Communication

**Share Import Instructions:**
```markdown
## Installing Team Tools Bundle

1. Update SkillMeat:
   ```bash
   pip install --upgrade skillmeat
   ```

2. Download bundle:
   ```bash
   # From S3
   aws s3 cp s3://team-artifacts/team-tools-v1.2.0.skillmeat-pack .
   ```

3. Import:
   ```bash
   skillmeat import team-tools-v1.2.0.skillmeat-pack --strategy merge
   ```

4. Verify:
   ```bash
   skillmeat verify team-tools
   skillmeat list --filter "team-tools"
   ```

5. Deploy (optional):
   ```bash
   skillmeat deploy team-tools --to-project ~/project
   ```
```

## Troubleshooting

### Import Issues

**Signature Verification Failed**

**Problem:** "Signature verification failed" error

**Causes:**
- Bundle corrupted or modified
- Signing key not in keychain
- Bundle from untrusted source

**Resolution:**
```bash
# Verify signature manually
skillmeat verify-signature bundle.skillmeat-pack

# Check key availability
skillmeat keys list

# Reimport from original source
rm bundle.skillmeat-pack
# Download again or request new bundle
```

**Hash Mismatch**

**Problem:** "Hash verification failed" error

**Causes:**
- Incomplete download
- Network interruption
- File corruption

**Resolution:**
```bash
# Clear download cache
skillmeat cache clear imports

# Retry import
skillmeat import bundle.skillmeat-pack --force-redownload
```

### Export Issues

**License Incompatibility**

**Problem:** "License incompatibility detected"

**Causes:**
- GPL-2.0 mixed with Apache-2.0
- Proprietary license included
- License conflict warning

**Resolution:**
```bash
# Check licenses
skillmeat verify bundle.skillmeat-pack --show-licenses

# Export subset without conflicts
skillmeat export selected-pack \
  --artifacts skill1,skill2 \
  --output compatible-pack.skillmeat-pack

# Or choose compatible license
--license "GPL-3.0-or-later"
```

**Security Scan Failures**

**Problem:** "Security scan failed: secrets detected"

**Causes:**
- Hardcoded API keys
- Credentials in config files
- Passwords in documentation

**Resolution:**
```bash
# Review scan results
skillmeat compliance-scan bundle.skillmeat-pack --verbose

# Locate secrets
grep -r "AKIA\|sk_\|password=" artifacts/

# Remove secrets
# - Remove .env files
# - Remove credentials from code
# - Use environment variables instead

# Verify scan passes
skillmeat compliance-scan bundle.skillmeat-pack
```

### Vault Issues

**Can't Access Team Vault**

**Problem:** "Permission denied" or "Vault not found"

**Solutions:**
```bash
# Check vault configuration
skillmeat vault info team-vault

# Verify permissions
skillmeat vault members list team-vault

# Check authentication
skillmeat config show vault-credentials

# Request access from admin
# Admin runs: skillmeat vault members add team-vault you@example.com
```

**Slow Vault Operations**

**Problem:** Import/export takes too long

**Solutions:**
```bash
# Check vault connection
skillmeat vault test-connection team-vault

# Import smaller bundles
skillmeat import bundle.skillmeat-pack --type skill,command

# Use local cache
skillmeat cache enable vault-cache

# Contact admin for performance investigation
```

### Getting Help

If issues persist:

1. **Check Documentation:**
   - [SkillMeat Docs](https://docs.skillmeat.com)
   - [Team Sharing FAQ](./team-sharing-guide.md#faq)

2. **Enable Debug Output:**
   ```bash
   skillmeat import --debug bundle.skillmeat-pack
   ```

3. **Collect Diagnostics:**
   ```bash
   skillmeat diagnose --output diagnostics.json
   ```

4. **Contact Support:**
   - Email: support@skillmeat.com
   - GitHub Issues: https://github.com/skillmeat/skillmeat/issues
   - Team Slack: #skillmeat-support

## See Also

- [Publishing to Marketplace](./publishing-to-marketplace.md)
- [Web UI Guide](./web-ui-guide.md)
- [Collections Management](./collections-guide.md)
