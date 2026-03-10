---
schema_version: 2
doc_type: phase_plan
title: "SkillBOM & Attestation - Phases 5-6: Git & Crypto"
description: >
  Git pre-commit hook integration (Phase 5) + cryptographic signing (Phase 6).
  Links BOM snapshots to git commits and enables signature verification.
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
updated: 2026-03-10
phase: 5-6
phase_title: "Git & Crypto: Commit Integration & Signing"
prd_ref: /docs/project_plans/PRDs/features/skillbom-attestation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
entry_criteria:
  - Phase 1-4 complete with models, generators, history, and RBAC in place
  - BomGenerator service stable and tested
  - SIGNING_POLICY.md Ed25519 infrastructure available
exit_criteria:
  - Pre-commit hook installer functional ("skillmeat bom install-hook")
  - BOM snapshot created on commit with SkillBOM-Hash footer
  - Ed25519 signing/verification working
  - Time-travel restoration (skillmeat restore --commit) functional
  - generate_attestation Claude Code tool available
feature_slug: skillbom-attestation
effort_estimate: "16-18 story points"
timeline: "2 weeks"
parallelization: "Phase 5 and Phase 6 can run mostly in parallel"
---

# SkillBOM & Attestation System - Phases 5-6: Git & Crypto

## Overview

Phases 5-6 integrate BOM snapshots with Git commits and add cryptographic signing. Phase 5 implements the pre-commit hook that generates BOM snapshots and appends commit footers. Phase 6 adds Ed25519 signing for non-repudiation and integrity verification.

---

## Phase 5: Git Commit Integration

**Duration**: 1 week | **Effort**: 8-10 story points | **Assigned**: python-backend-engineer

### Overview

Implement Git pre-commit hook installation and BOM snapshot generation on commit. The hook:
1. Calls `skillmeat bom generate` to create `.skillmeat/context.lock`
2. Appends `SkillBOM-Hash: sha256:<hash>` footer to commit message
3. Implements time-travel restoration via `skillmeat restore --commit <hash>`

Also define `generate_attestation` tool for Claude Code agents.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 5.1 | Pre-commit hook installer (`skillmeat bom install-hook`) | CLI command that creates `.git/hooks/pre-commit` script in the current project. Hook calls `skillmeat bom generate` and appends SkillBOM-Hash footer to commit message. | Command executes without errors; hook file created with executable permissions; hook runs on next commit; works on Linux, macOS, and Windows Git Bash | 2 | Pending |
| 5.2 | Pre-commit hook script implementation | The hook script (BASH/Python): (1) Call `skillmeat bom generate` to create context.lock, (2) Compute SHA256 hash of context.lock file, (3) Append `SkillBOM-Hash: sha256:<hash>` footer to COMMIT_EDITMSG file, (4) Exit 0 on success, 1 on failure. | Hook runs silently on commit; footer appended correctly to commit message; hash is valid SHA256; failure handling graceful | 2 | Pending |
| 5.3 | BOM snapshot on commit | When hook runs, BomGenerator captures current artifact state and writes context.lock with timestamp. Snapshot includes commit_sha (if available) for traceability. | context.lock file created with timestamp; snapshot linked to commit SHA; idempotent (running hook twice produces same snapshot) | 2 | Pending |
| 5.4 | Commit-linked BOM retrieval (`skillmeat restore --commit <hash>`) | CLI command to retrieve BOM snapshot from a specific commit SHA. Command: (1) Reads commit message, (2) Extracts SkillBOM-Hash footer, (3) Queries BomSnapshot table by commit_sha or hash, (4) Rehydrates `.claude/` directory to that state. | Command accepts commit hash; extracts SkillBOM-Hash from commit message; retrieves corresponding BOM snapshot; restores artifact files | 2 | Pending |
| 5.5 | Upstream fallback for missing BOMs | If local collection lacks the requested commit's BOM snapshot, `skillmeat restore --commit` attempts to fetch from upstream GitHub repository (with user confirmation). Prompts before network access. | Restore checks local DB first; if missing, prompts user for upstream fetch; fetches from GitHub release artifacts or archive; user can decline fetch | 2 | Pending |
| 5.6 | `generate_attestation` Claude Code tool definition | Define agent tool callable from Claude Code. Parameters: (1) artifact_names (optional list of artifact names to include), (2) include_memory_items (bool), (3) signature_key_id (optional). Returns: generated context.lock JSON + signature if key available. | Tool instantiates and callable from agents; generates BOM synchronously; returns valid JSON; handles missing parameters gracefully | 2 | Pending |
| 5.7 | Integration test: Hook runs on commit | End-to-end test: initialize repo, install hook, create artifact deployment, make commit, verify context.lock created and footer appended. | Test repo created; hook installed and executes; context.lock generated; commit message footer present; hash valid | 2 | Pending |

### Key Design Notes

- **Hook Language**: Use BASH for portability (works on Linux, macOS, Windows Git Bash); fallback to Python if BASH unavailable.
- **Idempotency**: Running hook multiple times produces identical snapshot (deterministic artifact ordering, timestamps).
- **Error Handling**: If BOM generation fails, hook should log error but allow commit to proceed (history is more important than perfect snapshots).
- **Commit Footer Format**: Follow conventional footer style: `SkillBOM-Hash: sha256:<40-char-hex>`
- **Restore Strategy**: Local first, upstream as fallback; always prompt user before network access.
- **Agent Tool**: Synchronous execution; returns immediately with JSON (no long-running operations).

### Deliverables

1. **Code**:
   - `skillmeat/core/bom/git_integration.py` — Hook installer, commit message writer, restore logic
   - `skillmeat/cli.py` — New CLI commands: `bom install-hook`, `bom restore`, `bom generate`
   - `skillmeat/core/tools/generate_attestation.py` — Claude Code agent tool definition

2. **Tests**:
   - `skillmeat/core/tests/test_git_integration.py` — Hook installation and execution tests
   - `skillmeat/core/tests/test_bom_restore.py` — Time-travel restoration tests

### Exit Criteria

- [ ] `skillmeat bom install-hook` creates executable pre-commit script
- [ ] Hook executes on commit and appends SkillBOM-Hash footer
- [ ] context.lock generated with valid SHA256 hash
- [ ] `skillmeat restore --commit <hash>` restores artifact state
- [ ] Upstream fallback works with user confirmation
- [ ] `generate_attestation` tool callable from Claude Code
- [ ] Integration test passes (hook runs on actual commit)

---

## Phase 6: Cryptographic Signing

**Duration**: 1 week | **Effort**: 6-8 story points | **Assigned**: python-backend-engineer

### Overview

Add Ed25519 signing to BOM snapshots. Implements `skillmeat bom sign` and `skillmeat bom verify` commands using existing `SIGNING_POLICY.md` infrastructure.

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Status |
|----|------|-------------|-------------------|----------|--------|
| 6.1 | Ed25519 signing integration with existing `skillmeat/security/crypto.py` | Integrate with existing signing infrastructure from SIGNING_POLICY.md. Methods: (1) sign_bom(bom_json, key_id=None) → signature_bytes, (2) verify_signature(bom_json, signature) → bool. Use existing key management (keyring library). | Signing produces valid Ed25519 signature; verification works; key_id optional (uses default key if not specified); integration with existing crypto module clean | 2 | Pending |
| 6.2 | `skillmeat bom sign` CLI command | Command to sign a context.lock file. Parameters: (1) --file <path> (default: .skillmeat/context.lock), (2) --key-id <id> (optional, uses default if not specified), (3) --output <path> (default: context.lock.sig). Produces signature file. | Command executes and produces valid signature file; signature contains key metadata; file created with correct permissions; idempotent | 2 | Pending |
| 6.3 | `skillmeat bom verify` CLI command | Command to verify BOM signature. Parameters: (1) --file <path>, (2) --signature <path> (default: context.lock.sig). Returns: VALID / INVALID / ERROR with details. | Command executes and returns correct verification result; signature metadata displayed; error messages clear; works for both signed and unsigned BOMs | 1 | Pending |
| 6.4 | Signature chain validation | Utility to validate signature lineage: (1) Verify signature on current BOM, (2) Extract previous BOM hash from signature, (3) Verify previous BOM's signature, etc. Builds chain of trust. | Chain validation traces back to known-good anchor (trusted key); reports unbroken chain or breaks in verification | 1 | Pending |
| 6.5 | BomSnapshot signature storage | Extend BomSnapshot model to store signature and signature_algorithm. When BOM generated with signing enabled, signature stored alongside snapshot. | BomSnapshot.signature column populated on creation (if signing enabled); signature_algorithm stored (e.g., "ed25519"); query by signature integrity possible | 1 | Pending |
| 6.6 | Automatic signing on BOM generation (feature flag) | Feature flag `skillbom_auto_sign: false` (default). When enabled, `skillmeat bom generate` automatically signs resulting BOM with default key. | Feature flag controls auto-signing behavior; when enabled, BOMs generated with attached signature; when disabled, unsigned BOMs | 1 | Pending |
| 6.7 | Signature verification in restore workflow | When `skillmeat restore --commit <hash>` retrieves BOM snapshot, verify signature before rehydrating filesystem. If verification fails, prompt user to proceed anyway (with warning). | Restore workflow verifies signature; verification failure doesn't block restore (user can override); warning message clear | 1 | Pending |
| 6.8 | Unit tests for signing and verification | Tests for sign(), verify(), chain_validation(). Test with valid, tampered, and missing signature scenarios. | All tests pass; signature round-trip works (sign then verify returns true); tampered data fails verification; missing signature handled gracefully | 2 | Pending |

### Key Design Notes

- **Ed25519 Keys**: Use existing key management from `skillmeat/security/crypto.py` — no new key infrastructure.
- **Key ID**: Optional parameter; default key used if not specified. Key metadata stored in signature.
- **Signature Format**: Use standard Ed25519 format (64 bytes); encode as base64 or hex for file storage.
- **Signature Algorithm**: Store algorithm identifier in BomSnapshot.signature_algorithm for future algorithm upgrades.
- **Verification**: Verify signature and report status clearly; do not fail silently.
- **Chain of Trust**: Signature can optionally include hash of previous BOM for lineage tracking.

### Deliverables

1. **Code**:
   - `skillmeat/core/bom/signing.py` — Ed25519 signing and verification
   - `skillmeat/cli.py` — `bom sign` and `bom verify` CLI commands
   - Modified `skillmeat/cache/models.py` — Add signature fields to BomSnapshot

2. **Tests**:
   - `skillmeat/core/tests/test_bom_signing.py` — Sign/verify tests
   - `skillmeat/core/tests/test_signature_chain.py` — Chain validation tests

### Exit Criteria

- [ ] Ed25519 signing/verification functional using existing crypto module
- [ ] `skillmeat bom sign` produces valid signatures
- [ ] `skillmeat bom verify` correctly validates signatures
- [ ] Signature chain validation traces trust lineage
- [ ] BomSnapshot stores signatures with metadata
- [ ] Auto-signing feature flag functional (default: disabled)
- [ ] Restore workflow verifies signatures before rehydration
- [ ] All signing tests pass

---

## Integration Points

### From Phase 5 → Phase 6
- Pre-commit hook can optionally sign BOMs if feature flag enabled
- Signature appended to commit message (optional, extended footer)

### To Phase 7 (API)
- API endpoints expose signature status and verification results
- History queries can filter by signature integrity status

### To Phase 8 (CLI)
- CLI commands (history, attest, bom) integrate signature verification
- Help text explains signature verification workflow

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Key management issues (lost keys, rotation) | Use existing SIGNING_POLICY.md infrastructure; document key management best practices |
| Signature verification performance | Caching of public keys; lazy verification (only when explicitly requested) |
| Hook failures block commits | Hook designed to fail gracefully; BOM generation errors logged but don't prevent commit |
| Git repo state out of sync with BOM | Fallback to local state if Git retrieval fails; always validate state before restore |

---

## Success Metrics

- **Signing Latency**: Sign context.lock in < 500ms (Ed25519 is fast)
- **Verification Latency**: Verify signature in < 100ms
- **Key Management**: No lost keys (backup strategy verified)
- **Hook Success Rate**: >= 99% of commits trigger hook without error
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
