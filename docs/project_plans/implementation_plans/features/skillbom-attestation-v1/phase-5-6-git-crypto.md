---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 5-6: Git & Crypto"
description: >
  Git hook integration (Phase 5) + cryptographic signing (Phase 6).
  Links BOM snapshots to commits using the correct Git lifecycle, enables signature verification,
  and preserves the foundation for future exact point-in-time recovery.
audience:
  - ai-agents
  - developers
  - backend-engineers
  - security-engineers
tags:
  - implementation-plan
  - phases
  - skillbom
  - git
  - cryptography
created: 2026-03-10
updated: 2026-03-11
phase: 5-6
phase_title: "Git & Crypto: Commit Integration & Signing"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - Phase 1-4 complete with models, generators, activity history, and RBAC in place
  - BomGenerator service stable and tested
  - SIGNING_POLICY.md Ed25519 infrastructure available
exit_criteria:
  - Git hook installer functional (`skillmeat bom install-hook`)
  - BOM snapshot linked to final commit with `SkillBOM-Hash` footer
  - Ed25519 signing/verification working
  - Time-travel restoration (`skillmeat bom restore --commit`) functional
  - `generate_attestation` Claude Code tool available
feature_slug: skillbom-attestation
effort_estimate: "16-18 story points"
timeline: "2 weeks"
parallelization: "Phase 5 and Phase 6 can run mostly in parallel"
---

# SkillBOM & Attestation System - Phases 5-6: Git & Crypto

## Overview

Phases 5-6 integrate BOM snapshots with Git commits and add cryptographic signing. Phase 5 uses the correct Git hook lifecycle for commit-message metadata and final commit linkage. Phase 6 adds Ed25519 signing for non-repudiation and integrity verification.

---

## Phase 5: Git Commit Integration

**Duration**: 1 week | **Effort**: 8-10 story points | **Assigned**: python-backend-engineer

### Overview

Implement Git hook installation and BOM snapshot generation on commit. The hook set should:
1. Generate or refresh `.skillmeat/context.lock`
2. Append `SkillBOM-Hash: sha256:<64-char-hex>` to the commit message using `prepare-commit-msg` or `commit-msg`
3. Link the final commit SHA to the stored BOM snapshot using `post-commit`
4. Support time-travel restoration via `skillmeat bom restore --commit <hash>`

Also define `generate_attestation` for Claude Code agents.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 5.1 | Git hook installer (`skillmeat bom install-hook`) | CLI command that creates the required Git hook set in the current repo. Recommended hooks: `prepare-commit-msg` or `commit-msg` plus `post-commit`, backed by a shared helper script. | Command executes without errors; hook files created with executable permissions; works on Linux, macOS, and Windows Git Bash | 2 | Pending |
| 5.2 | Commit-message footer hook implementation | Hook script: generate or refresh `context.lock`, compute SHA-256, append `SkillBOM-Hash: sha256:<64-char-hex>` footer to the commit message file, avoid duplicate footer insertion. | Footer appended correctly; no duplicate footer lines; hash is valid SHA-256; failure handling graceful | 2 | Pending |
| 5.3 | Post-commit BOM linkage | After the commit is created, update the `BomSnapshot` record (or mapping table) with the final commit SHA. | Snapshot linked to final commit SHA; linkage robust even when commit message was edited interactively; mapping retrievable for restore | 2 | Pending |
| 5.4 | Commit-linked BOM retrieval (`skillmeat bom restore --commit <hash>`) | CLI command: read commit metadata, extract `SkillBOM-Hash`, resolve stored BOM snapshot, verify signature if present, and rehydrate `.claude/` to that state where exact entry resolution is available. The workflow must surface unresolved entries explicitly rather than silently substituting current content. | Command accepts commit hash; extracts footer; retrieves corresponding BOM snapshot; restores artifact files where exact resolution is available; supports `--dry-run`; reports unresolved entries clearly | 2 | Pending |
| 5.5 | Upstream fallback for missing BOMs | If local state lacks the requested commit's BOM snapshot, `skillmeat bom restore --commit` can attempt an upstream GitHub fetch with user confirmation. | Restore checks local state first; prompts before network access; user can decline fetch cleanly | 2 | Pending |
| 5.6 | `generate_attestation` Claude Code tool definition | Tool callable from Claude Code. Parameters: optional artifact filters, `include_memory_items`, optional `signature_key_id`. Returns generated BOM JSON and signature if available. | Tool callable from agents; generates BOM synchronously; returns valid JSON; handles missing parameters gracefully | 2 | Pending |
| 5.7 | Integration test: Hook set runs on commit | End-to-end test: initialize repo, install hooks, create artifact deployment, make commit, verify `context.lock`, footer insertion, and post-commit linkage. | Test repo created; hook set installed and executes; `context.lock` generated; footer present; snapshot linked to final commit | 2 | Pending |

### Key Design Notes

- **Correct Git Lifecycle**: Do not use `pre-commit` for commit-message mutation. Use `prepare-commit-msg` or `commit-msg` for footer edits and `post-commit` for final SHA linkage.
- **Footer Format**: `SkillBOM-Hash: sha256:<64-char-hex>`
- **Determinism**: The hashed BOM payload must be deterministic. Ephemeral generation metadata should not change the hash unexpectedly.
- **Error Handling**: If BOM generation fails, hooks should surface a clear warning. Whether commit should proceed must be configurable; default recommended behavior is fail-open during rollout.
- **Restore Strategy**: Local first, upstream as fallback; always prompt user before network access.
- **Foundation vs. Full Guarantee**: This phase establishes commit-to-BOM linkage and restore orchestration. Universal exact point-in-time recovery still depends on a future restore-source architecture for every BOM entry type.
- **No Silent Approximation**: Restore must not silently replace unresolved historical entries with current versions. Exact mode should fail closed unless the operator explicitly allows partial recovery.
- **Agent Tool**: Synchronous execution; returns immediately with JSON.

### Deliverables

1. **Code**:
   - `skillmeat/core/bom/git_integration.py` — Hook installer, commit message writer, restore logic
   - `skillmeat/cli/__init__.py` and/or `skillmeat/cli/commands/` — `bom install-hook`, `bom restore`, `bom generate`
   - `skillmeat/core/tools/generate_attestation.py` — Claude Code agent tool definition

2. **Tests**:
   - `skillmeat/core/tests/test_git_integration.py` — Hook installation and execution tests
   - `skillmeat/core/tests/test_bom_restore.py` — Time-travel restoration tests

### Exit Criteria

- [ ] `skillmeat bom install-hook` creates the expected Git hook set
- [ ] Hook set executes on commit and appends `SkillBOM-Hash` footer
- [ ] `context.lock` generated with valid SHA-256 hash
- [ ] Final commit SHA linked to stored BOM snapshot
- [ ] `skillmeat bom restore --commit <hash>` restores exact artifact state where resolvable and reports unresolved entries explicitly
- [ ] Upstream fallback works with user confirmation
- [ ] `generate_attestation` tool callable from Claude Code
- [ ] Integration test passes (hook set runs on actual commit)

---

## Phase 6: Cryptographic Signing

**Duration**: 1 week | **Effort**: 6-8 story points | **Assigned**: python-backend-engineer

### Overview

Add Ed25519 signing to BOM snapshots. Implements `skillmeat bom sign` and `skillmeat bom verify` commands using existing `SIGNING_POLICY.md` infrastructure.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 6.1 | Ed25519 signing integration with existing `skillmeat/security/crypto.py` | Integrate with existing signing infrastructure. Methods: `sign_bom(...)` and `verify_signature(...)`. Use existing key management. | Signing produces valid Ed25519 signature; verification works; key_id optional; integration clean | 2 | Pending |
| 6.2 | `skillmeat bom sign` CLI command | Sign a `context.lock` file. Default output: `context.lock.sig`. | Command executes and produces valid signature file; signature contains key metadata; file created with correct permissions | 2 | Pending |
| 6.3 | `skillmeat bom verify` CLI command | Verify BOM signature. Returns `VALID` / `INVALID` / `ERROR` with details. | Command executes and returns correct verification result; metadata displayed; works for signed and unsigned BOMs | 1 | Pending |
| 6.4 | Signature chain validation | Validate signature lineage across BOM history. | Chain validation traces back to known-good anchor; reports unbroken chain or verification break | 1 | Pending |
| 6.5 | `BomSnapshot` signature storage | Store signature and `signature_algorithm` alongside snapshots. | `BomSnapshot.signature` populated on creation (if signing enabled); algorithm stored | 1 | Pending |
| 6.6 | Automatic signing on BOM generation (feature flag) | Feature flag `skillbom_auto_sign = false` by default. | Feature flag controls auto-signing behavior; when enabled, BOMs generated with attached signature | 1 | Pending |
| 6.7 | Signature verification in restore workflow | When restoring from commit, verify signature before rehydrating filesystem. User can override on failure with warning. | Restore workflow verifies signature; failure does not silently pass; warning message clear | 1 | Pending |
| 6.8 | Unit tests for signing and verification | Tests for sign, verify, and chain validation with valid/tampered/missing signatures. | All tests pass; tampered data fails verification; missing signature handled gracefully | 2 | Pending |

### Key Design Notes

- **Ed25519 Keys**: Use existing key management from `skillmeat/security/crypto.py`; no new key infrastructure.
- **Signature Format**: Standard Ed25519 signature stored as base64 or hex with key metadata.
- **Signature Algorithm**: Store algorithm identifier in `BomSnapshot.signature_algorithm` for future upgrades.
- **Verification**: Verify signature and report status clearly; do not fail silently.
- **Chain of Trust**: Signature metadata can include hash of previous BOM for lineage tracking.

### Deliverables

1. **Code**:
   - `skillmeat/core/bom/signing.py` — Ed25519 signing and verification
   - `skillmeat/cli/__init__.py` and/or `skillmeat/cli/commands/` — `bom sign` and `bom verify`
   - Modified `skillmeat/cache/models.py` — Signature fields on `BomSnapshot`

2. **Tests**:
   - `skillmeat/core/tests/test_bom_signing.py` — Sign/verify tests
   - `skillmeat/core/tests/test_signature_chain.py` — Chain-validation tests

### Exit Criteria

- [ ] Ed25519 signing/verification functional using existing crypto module
- [ ] `skillmeat bom sign` produces valid signatures
- [ ] `skillmeat bom verify` correctly validates signatures
- [ ] Signature chain validation traces trust lineage
- [ ] `BomSnapshot` stores signatures with metadata
- [ ] Auto-signing feature flag functional (default: disabled)
- [ ] Restore workflow verifies signatures before rehydration
- [ ] All signing tests pass

---

## Integration Points

### From Phase 5 → Phase 6
- Hook set can optionally sign BOMs if feature flag enabled
- Commit footer references the BOM hash; signature remains sidecar/DB metadata, not commit-message payload

### To Phase 7 (API)
- API endpoints expose signature status and verification results
- Provenance views can filter or annotate by signature integrity

### To Phase 8 (CLI)
- CLI commands (`history`, `attest`, `bom`) integrate signature verification where relevant
- Help text explains signature verification workflow

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Hook semantics wrong for commit-message mutation | Use correct hook lifecycle and integration tests against real Git repos |
| Key management issues (lost keys, rotation) | Use existing signing policy infrastructure; document key management best practices |
| Signature verification performance | Cache public keys; verify lazily when appropriate |
| Git repo state out of sync with BOM | Store explicit commit-to-BOM linkage and validate before restore |

---

## Success Metrics

- **Signing Latency**: Sign `context.lock` in < 500ms
- **Verification Latency**: Verify signature in < 100ms
- **Hook Success Rate**: >= 99% of commits trigger hook set without unexpected failure
- **Signature Chain**: Unbroken chain of trust from current commit back to root

---

## Next Steps (Gate to Phase 7)

1. ✅ Phase 5-6 exit criteria verified
2. ✅ Git integration tested with real commits
3. ✅ Signature verification validated with known-good keys
4. ✅ Phase 7 (API) can begin with git/crypto foundation in place

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/skillbom-attestation-v1.md` § FR-05, FR-07, FR-08, FR-09, FR-10
- **Main Plan**: `/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md`
- **SIGNING_POLICY**: `/docs/ops/security/SIGNING_POLICY.md`
- **ADR-004**: `/docs/dev/architecture/decisions/004-artifact-version-tracking.md`
