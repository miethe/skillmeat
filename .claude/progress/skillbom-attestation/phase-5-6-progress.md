---
schema_version: 2
doc_type: progress
type: progress
prd: "skillbom-attestation"
feature_slug: "skillbom-attestation"
phase: 5-6
status: pending
created: 2026-03-10
updated: 2026-03-10
prd_ref: "docs/project_plans/PRDs/features/skillbom-attestation-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-5-6-git-crypto.md"
commit_refs: []
pr_refs: []
owners:
  - "python-backend-engineer"
contributors: []
tasks:
  - id: "TASK-5.1"
    name: "Implement pre-commit hook installer (skillmeat bom install-hook) creating executable .git/hooks/pre-commit"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "2 pts"
  - id: "TASK-5.2"
    name: "Implement pre-commit hook script: call BomGenerator, compute SHA256 of context.lock, append SkillBOM-Hash footer to COMMIT_EDITMSG"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-5.1"]
    estimate: "2 pts"
  - id: "TASK-5.3"
    name: "Implement BOM snapshot capture on commit with commit_sha linkage and idempotency guarantee"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-5.2"]
    estimate: "2 pts"
  - id: "TASK-5.4"
    name: "Implement skillmeat restore --commit <hash>: extract SkillBOM-Hash from commit message and rehydrate .claude/ to that state"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-5.3"]
    estimate: "2 pts"
  - id: "TASK-5.5"
    name: "Implement upstream fallback for missing commit BOMs with user confirmation prompt before network fetch, plus generate_attestation Claude Code agent tool"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-5.4"]
    estimate: "4 pts"
  - id: "TASK-6.1"
    name: "Integrate Ed25519 signing with existing skillmeat/security/crypto.py: sign_bom() and verify_signature() methods"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "2 pts"
  - id: "TASK-6.2"
    name: "Implement skillmeat bom sign CLI command producing context.lock.sig signature file"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-6.1"]
    estimate: "2 pts"
  - id: "TASK-6.3"
    name: "Implement skillmeat bom verify CLI command returning VALID/INVALID/ERROR with signature details"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-6.1"]
    estimate: "1 pt"
  - id: "TASK-6.4"
    name: "Implement signature chain validation, BomSnapshot signature storage, auto-sign feature flag, restore signature verification, and signing unit tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-6.1", "TASK-6.2", "TASK-6.3"]
    estimate: "6 pts"
parallelization:
  batch_1: ["TASK-5.1", "TASK-5.2"]
  batch_2: ["TASK-5.3", "TASK-5.4", "TASK-5.5"]
  batch_3: ["TASK-6.1", "TASK-6.2", "TASK-6.3"]
  batch_4: ["TASK-6.4"]
---

# Phase 5-6 Progress: Git & Crypto — Commit Integration & Signing

**Objective**: Link BOM snapshots to git commits via a pre-commit hook and add Ed25519 cryptographic signing for non-repudiation.

## Entry Criteria

- Phases 1-4 complete: models, BomGenerator, history capture, and RBAC all stable and tested
- `SIGNING_POLICY.md` Ed25519 key infrastructure available in `skillmeat/security/crypto.py`
- `BomSnapshot` model with `signature` and `signature_algorithm` nullable fields ready

## Exit Criteria

- `skillmeat bom install-hook` creates executable `.git/hooks/pre-commit` script on Linux, macOS, and Windows Git Bash
- Pre-commit hook generates `context.lock`, computes SHA256 hash, appends `SkillBOM-Hash: sha256:<hash>` footer to commit message
- BOM snapshot stored in DB with `commit_sha` on each commit (idempotent: same state → same snapshot)
- `skillmeat restore --commit <hash>` reads SkillBOM-Hash footer, retrieves snapshot, rehydrates `.claude/` directory
- Upstream fallback prompts user before network access; fetches from GitHub if confirmed
- `generate_attestation` Claude Code tool callable from agents, returns valid BOM JSON synchronously
- Ed25519 signing/verification using existing `skillmeat/security/crypto.py` (no new crypto primitives)
- `skillmeat bom sign` produces valid signature file with key metadata
- `skillmeat bom verify` correctly validates/invalidates signatures
- Signature chain traces lineage from current BOM back to signed anchor
- `BomSnapshot.signature` and `BomSnapshot.signature_algorithm` populated when signing enabled
- `skillbom_auto_sign: false` feature flag controls auto-signing behavior
- Restore workflow verifies signature before rehydration; user can override warning
- Integration test: hook runs on real commit, footer appended, snapshot stored

## Phase Plan Reference

`docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-5-6-git-crypto.md`
