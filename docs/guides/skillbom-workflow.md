---
title: "SkillBOM Workflow Guide"
description: "Comprehensive guide to using SkillBOM for Bill of Materials generation, signing, verification, and artifact state restoration."
audience: "developers, operators"
tags: ["bom", "signature", "verification", "deployment", "snapshot"]
created: "2026-03-13"
updated: "2026-03-13"
category: "Guides"
status: "published"
related_documents: ["attestation-compliance.md", "bom-api.md"]
---

# SkillBOM Workflow Guide

SkillBOM is SkillMeat's Bill of Materials system that captures, signs, and verifies artifact snapshots. This guide explains what SkillBOM does, why you need it, and how to use it in your workflow.

## What is a SkillBOM?

A SkillBOM is a point-in-time snapshot of all artifacts deployed in your SkillMeat project or collection. It records:

- **Artifact metadata**: Name, type, version, source, and content hash
- **Timestamp**: When the snapshot was generated
- **Schema version**: Format compatibility information
- **Signature**: Optional Ed25519 cryptographic signature for authenticity verification

Think of it as a manifest that freezes your artifact state at a specific moment, allowing you to answer questions like:

- "What artifacts were deployed when this commit was made?"
- "Has this artifact set been tampered with?"
- "Can I restore my project to this exact configuration?"

## Why Use SkillBOM?

### Reproducibility

Deploy the same artifact set across environments with certainty. SkillBOM captures the exact versions and content hashes of all artifacts, enabling consistent reproducible builds.

### Audit Trail

Link every Git commit to its corresponding SkillBOM snapshot via the `SkillBOM-Hash` footer in commit messages. This creates an immutable audit trail showing what was deployed when.

### Compliance

Some organizations require proof that deployed artifacts haven't been modified. SkillBOM's Ed25519 signatures provide cryptographic evidence of authenticity.

### Disaster Recovery

Restore your project to any previous artifact configuration using a commit SHA. The system automatically retrieves the linked BOM snapshot and rehydrates your `.claude/` directory.

## CLI Commands

### Generate a SkillBOM

Generate a snapshot of all currently deployed artifacts:

```bash
skillmeat bom generate
```

**Output**: Creates `.skillmeat/context.lock` with all artifact metadata.

**Options**:

```bash
# Generate for a specific project directory
skillmeat bom generate --project /path/to/project

# Output to a custom location
skillmeat bom generate --output /tmp/my-snapshot.json

# Generate and automatically sign (see keygen below)
skillmeat bom generate --auto-sign

# Output machine-readable JSON instead of summary
skillmeat bom generate --format json
```

### Generate Signing Keys

Before signing BOMs, generate an Ed25519 keypair:

```bash
skillmeat bom keygen
```

**Output**:
- `~/.skillmeat/keys/skillbom_ed25519` (private key, mode 0600)
- `~/.skillmeat/keys/skillbom_ed25519.pub` (public key, mode 0644)

**Options**:

```bash
# Generate keys in a custom directory
skillmeat bom keygen --dir /path/to/keys
```

### Sign a SkillBOM

Sign an existing BOM snapshot with your Ed25519 private key:

```bash
skillmeat bom sign
```

This reads `.skillmeat/context.lock` and creates `.skillmeat/context.lock.sig`.

**Options**:

```bash
# Sign a specific file
skillmeat bom sign /path/to/snapshot.json

# Use a custom signing key
skillmeat bom sign --key /path/to/my_ed25519

# Output signature to a custom location
skillmeat bom sign --output /tmp/custom.sig
```

### Verify a SkillBOM Signature

Verify that a BOM hasn't been tampered with:

```bash
skillmeat bom verify
```

This checks the signature stored in `.skillmeat/context.lock.sig` against the `.skillmeat/context.lock` content.

**Output**: Displays signature status (VALID, INVALID, or ERROR) with key details.

**Exit codes**:
- `0` — Signature is valid
- `1` — Signature is invalid or verification failed

**Options**:

```bash
# Verify a specific file
skillmeat bom verify /path/to/snapshot.json

# Use a custom signature file
skillmeat bom verify --signature /path/to/custom.sig

# Use a custom public key
skillmeat bom verify --key /path/to/public_key.pub
```

### Restore from a Previous BOM

Restore your artifact state to match a previous Git commit's BOM snapshot:

```bash
skillmeat bom restore --commit abc1234
```

This fetches the BOM snapshot linked to commit `abc1234` and rehydrates the `.claude/` directory.

**Preview (dry-run)**:

```bash
skillmeat bom restore --commit abc1234 --dry-run
```

Shows what would change without making modifications. This is helpful for understanding what artifacts would be restored.

**Force without confirmation**:

```bash
skillmeat bom restore --commit abc1234 --force
```

Skips the confirmation prompt before restoring.

### Install Git Hooks

Automate BOM tracking by installing Git hooks. These hooks automatically:

1. Append a `SkillBOM-Hash` footer to commit messages
2. Link the commit to its BOM snapshot in the database

```bash
skillmeat bom install-hook
```

**Options**:

```bash
# Install hooks in a specific repository
skillmeat bom install-hook --project /path/to/repo
```

**Behavior**: Existing non-SkillBOM hooks are backed up with a `.bak` suffix before being replaced.

## Typical Workflow

### Setup (One-time)

1. **Generate signing keys** (if not already done):
   ```bash
   skillmeat bom keygen
   ```

2. **Install Git hooks** in your project:
   ```bash
   skillmeat bom install-hook --project .
   ```

### Per-Deployment Cycle

1. **Deploy artifacts** using your normal process:
   ```bash
   skillmeat deploy my-skill --project .
   ```

2. **Generate a BOM snapshot**:
   ```bash
   skillmeat bom generate --auto-sign
   ```

3. **Commit changes** (hooks automatically add BOM footer):
   ```bash
   git add -A
   git commit -m "Deploy updated skills"
   # Git hook appends: SkillBOM-Hash: abc123...
   ```

4. **Verify the snapshot** (optional, for confidence):
   ```bash
   skillmeat bom verify
   ```

### During Disaster Recovery

1. **Identify the commit** you want to restore:
   ```bash
   git log --oneline | head -20
   ```

2. **Preview what will be restored**:
   ```bash
   skillmeat bom restore --commit abc1234 --dry-run
   ```

3. **Perform the restore**:
   ```bash
   skillmeat bom restore --commit abc1234
   ```

## Workflow Diagram

```
Deploy artifacts
    ↓
Generate BOM
    ↓
Sign BOM (optional)
    ↓
Commit changes
    ↓
Git hooks append SkillBOM-Hash footer
    ↓
BOM snapshot linked to commit in DB
    ↓
Later: Restore from commit
    ↓
Fetch BOM snapshot
    ↓
Verify signature (optional)
    ↓
Rehydrate .claude/ directory
```

## Troubleshooting

### No signing key found when signing

**Problem**: `Error: key file not found: ~/.skillmeat/keys/skillbom_ed25519`

**Solution**: Generate a keypair first:
```bash
skillmeat bom keygen
```

The `sign` command will prompt you to generate a key if the default doesn't exist.

### Signature verification fails

**Problem**: `Status: INVALID — Signature verification failed.`

**Cause**: Either:
1. The BOM file was modified after signing
2. The wrong public key is being used
3. The signature file is corrupted

**Solution**:
- Verify you're using the correct public key with `--key`
- Check that the BOM file hasn't been edited
- Regenerate the signature if needed: `skillmeat bom sign --output <path>`

### Restore shows "unresolved entries"

**Problem**: When restoring, some artifacts show as unresolvable.

**Cause**: The artifacts referenced in the historical BOM may no longer exist in the current collection.

**Solution**:
- Review which artifacts are unresolved in the dry-run output
- Import those artifacts back into your collection if needed
- Retry the restore

### BOM generation fails with database error

**Problem**: `Error: could not open cache database`

**Cause**: The local SQLite cache database may be corrupted or missing.

**Solution**:
- Rebuild the cache: `skillmeat cache refresh`
- If that fails, check file permissions on `~/.skillmeat/cache/`

## File Locations

| File | Purpose |
|------|---------|
| `~/.skillmeat/keys/skillbom_ed25519` | Private signing key (mode 0600) |
| `~/.skillmeat/keys/skillbom_ed25519.pub` | Public verification key (mode 0644) |
| `.skillmeat/context.lock` | Generated BOM snapshot (JSON) |
| `.skillmeat/context.lock.sig` | Binary Ed25519 signature |
| `.git/hooks/prepare-commit-msg` | Hook for appending BOM footer |
| `.git/hooks/post-commit` | Hook for DB linkage |

## Key Concepts

### Content Hash

Each artifact entry includes a SHA-256 hash of its content. This enables:
- Detection of accidental modifications
- Comparison across BOMs
- Content-based deduplication

### Owner Scope

BOMs respect ownership hierarchies:
- **User**: Personal artifact collections
- **Team**: Shared team artifacts
- **Enterprise**: Organization-wide artifacts (enterprise edition only)

The generated BOM reflects only artifacts visible to the authenticated user.

### Signature Algorithm

SkillBOM uses **Ed25519**, a modern public-key signature scheme that is:
- Fast and secure
- Hard to misuse
- Smaller keys than RSA
- Deterministic (no random number generator needed)

## Best Practices

1. **Generate signatures for all production BOMs**: Use `--auto-sign` in CI/CD pipelines.
2. **Store public keys securely**: Share public keys through your organization's key distribution system.
3. **Review dry-runs before restoring**: Always use `--dry-run` to preview changes before committing.
4. **Keep hooks installed**: Once installed via `install-hook`, maintain them across team checkouts.
5. **Audit BOM history**: Regularly review the `SkillBOM-Hash` footers in your Git history.

## API Integration

For programmatic access to BOM operations, use the REST API endpoints documented in `/docs/api/bom-api.md`. The API provides the same functionality as the CLI but returns structured JSON responses.

Example:

```bash
# Generate BOM via API
curl -X POST http://localhost:8080/api/v1/bom/generate \
  -H "Content-Type: application/json" \
  -d '{"auto_sign": true}'

# Verify signature via API
curl -X POST http://localhost:8080/api/v1/bom/verify \
  -H "Content-Type: application/json" \
  -d '{"snapshot_id": 42}'
```

See `/docs/api/bom-api.md` for complete endpoint specifications and examples.
