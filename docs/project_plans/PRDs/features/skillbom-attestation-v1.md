---
title: 'PRD: SkillBOM & Attestation System'
description: Cryptographic tracking and provenance for AI agent context, enabling reproducible commits and AI supply chain security.
audience:
  - ai-agents
  - developers
  - security-engineers
tags:
  - prd
  - planning
  - enhancement
  - skillbom
  - security
  - provenance
  - versioning
created: 2026-02-23
updated: 2026-02-23
category: product-planning
status: draft
related:
  - /docs/project_plans/PRDs/features/versioning-merge-system-v1.5-state-tracking.md
  - /docs/dev/architecture/decisions/004-artifact-version-tracking.md
  - /docs/security/SIGNING_POLICY.md
  - /skillmeat/core/deployment.py
schema_version: 2
doc_type: prd
feature_slug: skillbom-attestation
---

# PRD: SkillBOM & Attestation System

**Feature Name:** SkillBOM (Software Bill of Materials for Skills) & Attestation System
**Filepath Name:** skillbom-attestation-v1
**Date:** 2026-02-23
**Version:** 1.0
**Status:** Draft
**Priority:** HIGH (Strategic Enterprise Differentiator)

## 1. Executive Summary

The SkillBOM & Attestation System transforms SkillMeat from an artifact management utility into a comprehensive AI supply chain security platform. It introduces a cryptographic "Bill of Materials" (BOM) for AI context, capturing the exact state, content hashes, and configuration of all agents, skills, and tools active in a project at a specific moment in time. By linking these attestations to Git commits, organizations achieve perfect reproducibility, provable AI provenance, and protection against configuration drift or prompt injection attacks.

## 2. Context & Background

### Problem Space
Agentic development introduces non-determinism into the software development lifecycle. When an AI agent authors a commit, the output is a product of the code *and* the specific configuration of the agent at that exact moment (prompts, loaded tools, specific versions of skills).
1. **The "Time Travel" Problem:** A bug appears in AI-authored code months later. Debugging or extending it fails because the agent's underlying `sql-helper` skill was silently updated, changing its behavior.
2. **The "Shadow IT" Problem:** Compliance teams cannot verify which tools or guardrails were active when a piece of sensitive logic was generated.
3. **Prompt Injection/Tampering:** Malicious actors can silently alter an agent's system prompt in the `.claude/` directory to introduce vulnerabilities, with no audit trail indicating the agent's environment was compromised.

### Current Capabilities
SkillMeat already utilizes SHA-256 content hashing for drift detection (`004-artifact-version-tracking.md`) and maintains deployment metadata in `.skillmeat-deployed.toml`. The `SIGNING_POLICY.md` establishes a robust Ed25519 signature infrastructure. The missing link is binding these existing systems to specific developmental milestones (commits) and creating a restorable artifact from that data.

## 3. Goals & Outcomes

* **Reproducibility:** Enable developers to "rehydrate" an agent's exact context state to any historical commit.
* **Provable Provenance:** Cryptographically prove which AI artifacts were (and were not) used to author a specific change.
* **CI/CD Gatekeeping:** Allow CI pipelines to reject PRs authored by agents lacking required security guardrail skills.
* **Auditability:** Provide security teams with structured, parsable JSON tracking the evolution of AI workflows over time.

## 4. Functional Specifications

### 4.1 The SkillBOM Artifact (`context.lock`)
A structured JSON document generated at the project root (`.skillmeat/context.lock`) that acts similarly to `package-lock.json` but for AI context.

**Required Fields:**
* BOM Schema Version
* Timestamp of generation
* Associated Git Commit SHA
* Environment details (Model versions, MCP server versions)
* Array of `artifacts`:
  * `type` (skill, command, agent, mcp, hook)
  * `name`
  * `version_tag` (if applicable)
  * `content_hash` (SHA-256, mapped directly from cache database)
  * `provenance` (Upstream GitHub URL or Local source)

### 4.2 Generation & Git Integration
* **Agent Tool Integration:** An exposed `generate_attestation` tool allows autonomous agents to snapshot their environment just before issuing a git commit.
* **Pre-commit Hook:** An optional standard git pre-commit hook that automatically generates/updates the SkillBOM when changes in `.claude/` or code occur.
* **Commit Linking:** Appending a metadata footer to commit messages: `SkillBOM-Hash: sha256:abc123...`

### 4.3 Cryptographic Attestation
Utilizing the existing `SIGNING_POLICY.md` infrastructure:
* SkillBOMs are optionally signed using the developer's local Ed25519 private key.
* The signature proves that a specific human authorized the specific agent configuration that authored the code.

### 4.4 Time-Travel Restoration
* `skillmeat restore --commit <git-hash>`
* Reads the SkillBOM from the target commit.
* Queries `~/.skillmeat/collections/` (or upstream sources) to resolve the exact `content_hash` versions.
* Temporarily overwrites the `.claude/` directory, placing the agent into a historically accurate state.

## 5. Proposed Data Structure

```json
{
  "bom_version": "1.0",
  "timestamp": "2026-02-23T14:30:00Z",
  "commit_sha": "7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a",
  "signature": "ed25519:...",
  "environment": {
    "claude_model": "claude-3-7-sonnet-20250219",
    "mcp_server_versions": {
      "filesystem": "1.2.0"
    }
  },
  "artifacts": [
    {
      "type": "skill",
      "name": "python-expert",
      "content_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "provenance": "[github.com/anthropics/skills](https://github.com/anthropics/skills)",
      "local_modifications": false
    },
    {
      "type": "agent",
      "name": "security-reviewer",
      "content_hash": "sha256:88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589",
      "local_modifications": true
    }
  ]
}

```

## 6. Implementation Phases

### Phase 1: BOM Schema & Core Generation (Week 1)

* Define the Pydantic schema for `SkillBOM` in `skillmeat/api/schemas/bom.py`.
* Implement `BomGenerator` service in `skillmeat/core/bom/generator.py` utilizing the existing `DeploymentTracker` and `content_hash` utilities.
* Add CLI command: `skillmeat bom generate`.

### Phase 2: Git Workflow & Automation (Week 2)

* Implement `.git/hooks/pre-commit` installation logic (`skillmeat bom install-hook`).
* Create the Claude Code tool definition (`generate_attestation`) so agents can self-report their state.
* Implement logic to write the `SkillBOM-Hash` footer to commit messages.

### Phase 3: Time-Travel & Rehydration (Week 3)

* Implement `skillmeat bom restore --commit <hash>`.
* Tie into the `VersionManager` and `SyncManager` to pull specific historical versions of artifacts from the local cache.
* Handle fallback states (e.g., prompting to fetch from upstream if a specific historical hash is missing from the local collection).

### Phase 4: Security & CI/CD Verification (Week 4)

* Integrate `skillmeat/security/crypto.py` to sign the `context.lock` file.
* Add CLI command: `skillmeat bom verify` to validate signatures and ensure file integrity against the BOM hashes.
* Publish documentation for CI/CD pipeline integration (e.g., GitHub Actions snippet).

## 7. Open Questions & Future Explorations

* **Storage Overhead:** How large will `context.lock` files grow in highly active repositories? *Mitigation:* Ensure the file only tracks *active* deployed artifacts, not the entire user collection.
* **Missing Hashes:** If a user runs `restore` on a teammate's commit, and their local collection lacks the required historical artifact, should the system attempt to automatically reconstruct it from the upstream GitHub commit history?
* **UI Integration:** How should the web UI surface SkillBOMs? *Idea:* Add a "Provenance" tab to the project dashboard showing the chronological evolution of the project's agentic configuration.
