# SkillBOM Point-in-Time Environment Recovery Design Spec

**Date**: 2026-03-11
**Author**: Codex
**Status**: Draft design-spec for future planning

## Summary

SkillBOM already has a clear product goal: link AI context to commits so users can inspect the SkillBOM for a commit and recover the exact environment that existed at that point in time. The current SkillBOM architecture is close on manifest generation and commit linkage, but it does not yet fully define the restore-source architecture needed for universal, deterministic environment recovery.

This spec documents:
- the current state and reusable building blocks,
- the gaps that prevent guaranteed exact recovery today,
- the foundation requirements the current SkillBOM plan should preserve,
- the larger future design work needed before exact point-in-time recovery can be considered complete.

## Goal

Define the future architecture for `skillmeat bom restore --commit <sha>` so that it can rehydrate the exact SkillMeat/Claude environment represented by the SkillBOM linked to that commit.

## Non-Goals

- Finalize the full restore implementation in this document.
- Replace the current SkillBOM implementation plan with a recovery-specific plan.
- Decide the final storage backend for immutable historical content.

## Current State

### Existing building blocks

1. **Deployment tracking exists**
   - `DeploymentTracker` records deployed artifacts, deployment paths, and deployment-time content hashes in `.skillmeat-deployed.toml`.
   - Current modification detection compares current filesystem content to the deployment baseline hash.

2. **Lockfile concepts already exist**
   - `skillmeat/storage/lockfile.py` stores `name`, `type`, `upstream`, `resolved_sha`, `resolved_version`, and `content_hash`.
   - This helps with reproducibility, but it is collection-oriented and not sufficient by itself for universal project-environment restoration.

3. **Snapshot infrastructure already exists**
   - `skillmeat/storage/snapshot.py` supports immutable tarball snapshots for collections.
   - This is useful precedent, but it is not currently a project-environment snapshot system.

4. **Version tracking exists conceptually**
   - `004-artifact-version-tracking.md` establishes content-hash-based version lineage and deployment-state tracking.
   - This is valuable for identity and drift detection, but it does not guarantee that historical content remains recoverable.

5. **SkillBOM plan already covers manifest linkage**
   - `BomSnapshot` is planned with `commit_sha`, `bom_json`, and signature metadata.
   - Git hook flow already plans for `SkillBOM-Hash` footer insertion and post-commit commit-to-BOM linkage.

### What the current architecture can do

- Generate a deterministic manifest of active artifacts at a point in time.
- Link that manifest to a Git commit.
- Verify integrity/signature of the manifest.
- Potentially restore entries whose exact content is still locally available or retrievable from a stable upstream source.

### What it cannot yet guarantee

- Universal exact restoration of all artifact/context types for an old commit.
- Deterministic recovery of DB-backed or ephemeral context purely from current storage.
- Guaranteed retrieval of historical bytes when the source artifact has changed or disappeared.

## Core Gap

The current architecture has a **manifest**, but not yet a universal **historical restore source**.

A SkillBOM can say:
- what artifacts existed,
- what their hashes were,
- how they were composed,
- which commit they were linked to.

But exact recovery also requires:
- a place to fetch the exact historical bytes from,
- stable per-entry identity and source-location metadata,
- restore rules for non-file artifacts,
- defined failure semantics when exact bytes cannot be recovered.

Without that, the system can provide commit-linked provenance and partial or best-effort restore, but not guaranteed point-in-time environment recovery.

## Gap Analysis

### 1. Manifest vs. content-source gap

The SkillBOM plan focuses on generating and storing manifests. It does not yet define the authoritative source of historical content for each BOM entry.

Why this matters:
- `content_hash` proves identity, but does not supply bytes.
- Upstream artifacts may have been modified, deleted, or force-pushed.
- Local collections may no longer contain the historical version.

### 2. Non-file and DB-backed artifacts are underspecified

Some environment state is not just a file in `.claude/`.

Examples:
- memory items,
- deployment-set composition,
- workflow definitions with overrides,
- attestation state or related metadata,
- project-level configuration stored in DB-backed records.

These require a restore format beyond “copy file by hash.”

### 3. Entry identity is not yet rich enough for universal recovery

For future exact restore, each BOM entry should be resolvable through more than `name + type + content_hash`.

At minimum, future-compatible entries should preserve:
- stable artifact identity (`artifact_uuid` or equivalent when available),
- content hash,
- artifact type,
- deployment target path or target locator,
- source class (`collection`, `project`, `memory`, `generated`, `external`, etc.),
- source locator metadata (collection name/path, upstream URL, resolved commit/tag, DB row identity, or other resolver inputs).

### 4. Environment boundary is not yet fully defined

The current PRD says “rehydrate `.claude/` to the exact artifact state,” but the practical environment boundary needs to be explicit.

Open boundary questions:
- Is the environment only `.claude/`?
- Does it include project-scoped memory items?
- Does it include deployment metadata files?
- Does it include workflow execution defaults or only persisted workflow definitions?

### 5. Restore failure semantics are not yet defined

Future restore behavior should not silently approximate old state with current content.

Needed semantics:
- `dry-run` preview,
- exact vs partial restore mode,
- unresolved-entry reporting,
- fail-closed default for exact restore,
- explicit override for operator-approved partial recovery.

## Foundations Required in the Current SkillBOM Plan

The current implementation plan can proceed if it preserves the following foundations now:

1. **Immutable commit-to-BOM linkage**
   - A commit must resolve to a specific immutable `BomSnapshot`.

2. **Deterministic BOM payloads**
   - The same environment state must always produce the same hashable payload.

3. **Rich per-entry restore metadata**
   - BOM entries should preserve stable identity and source-locator metadata sufficient for future restore resolution.

4. **No silent substitution during restore**
   - If exact historical content cannot be resolved, the restore flow must report that explicitly.

5. **Dry-run and verification-first restore flow**
   - Restore should support inspection before mutation and verify signatures when present.

6. **Separation between provenance manifest and restore source**
   - `BomSnapshot` should remain the manifest record.
   - The future content store or resolver system should be modeled separately.

## Recommended Future Architecture Directions

### Option A: Immutable content store per artifact version

Store recoverable historical bytes or canonical serialized payloads keyed by content hash.

Best for:
- exact deterministic restore,
- offline recovery,
- strong provenance guarantees.

Tradeoffs:
- storage cost,
- retention policy complexity,
- migration work for all artifact types.

### Option B: Hybrid resolver architecture

Store manifests plus resolver metadata. Recover bytes from:
- local immutable cache,
- collection snapshot store,
- DB-backed serialized payloads,
- upstream Git source when explicitly allowed.

Best for:
- phased rollout,
- lower storage cost up front.

Tradeoffs:
- more resolver complexity,
- weaker guarantee unless every artifact type has a reliable fallback chain.

### Option C: Full project-environment snapshots

Create environment tarballs or equivalent snapshot bundles at attestation time.

Best for:
- strongest restore guarantee,
- simplest restore execution path.

Tradeoffs:
- potentially large storage footprint,
- duplication across similar snapshots,
- more operational weight than the current SkillBOM direction.

## Recommended Direction

For SkillMeat, the most pragmatic future direction is a **hybrid resolver architecture** with a path to immutable content storage for unresolved artifact classes.

Suggested model:
- `BomSnapshot` stays the authoritative manifest.
- Each BOM entry carries sufficient resolver metadata.
- Restore attempts local immutable sources first, then stable DB or collection snapshots, then optional upstream fetches with confirmation.
- Exact restore mode fails if any entry cannot be resolved exactly.

This aligns with the current SkillBOM plan without forcing large storage commitments immediately.

## Future Planning Questions

1. What is the exact environment boundary for commit restore?
2. Which artifact types require serialized historical payload storage rather than hash-only resolution?
3. Should memory items be restored into DB state, filesystem state, or both?
4. What retention policy should apply to historical restorable content?
5. Should local and enterprise editions share the same restore guarantees?
6. How should partial restore be presented to users and audit logs?

## Immediate Recommendation for the Current SkillBOM Plan

Proceed with the current SkillBOM plan only as a **foundation for future exact restore**, not as proof that universal exact commit recovery is already designed end to end.

The current plan is appropriate if Phases 1, 2, and 5 preserve:
- commit-linked immutable `BomSnapshot` records,
- deterministic per-entry content hashes,
- stable artifact identity where available,
- source and deployment locator metadata,
- restore workflows that surface unresolved entries explicitly.

## Source References

- `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-1-2-foundation.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/implementation_plans/features/skillbom-attestation-v1/phase-5-6-git-crypto.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/PRDs/features/skillbom-attestation-v1.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/dev/architecture/decisions/004-artifact-version-tracking.md`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/lockfile.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/snapshot.py`
