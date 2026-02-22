---
schema_version: '1.1'
doc_type: implementation_plan
title: Fix Marketplace Embedded Artifacts Detection and File Loading
status: completed
created: '2026-02-21'
updated: '2026-02-21'
feature_slug: marketplace-embedded-artifacts
priority: high
risk_level: medium
prd_ref: null
plan_ref: null
scope: Marketplace artifact detection and file serving
effort_estimate: 2 phases, ~8-12 story points
related_documents:
- docs/project_plans/PRDs/features/marketplace-source-detection-improvements-v1.md
- docs/project_plans/bugs/marketplace-sources-non_skills-v1.md
---
# Implementation Plan: Fix Marketplace Embedded Artifacts Detection and File Loading

**Plan ID**: `BUGFIX-2026-02-21-EMBEDDED-ARTIFACTS`
**Date**: 2026-02-21
**Author**: Sonnet (Implementation Planner)
**Priority**: High

**Related Documents**:
- `docs/project_plans/bugs/marketplace-sources-non_skills-v1.md`
- `skillmeat/core/marketplace/heuristic_detector.py`
- `skillmeat/api/routers/marketplace_sources.py`
- `skillmeat/web/sdk/services/MarketplaceSourcesService.ts`

**Complexity**: Medium
**Total Estimated Effort**: 8-12 story points
**Target Timeline**: 2 phases, ~1 week

---

## Executive Summary

When loading a Source from the Marketplace, the Contents tab fails to display file details for artifacts embedded within Skills (e.g., Commands nested inside a Skill directory). The heuristic detector incorrectly treats these embedded artifacts as independent top-level artifacts, and subsequent file path resolution fails with 404 errors.

**Error trace**:
```
WARNING: File not found: skills/agentient-frontend-tools/skills/agentient-frontend-ui/commands/add-animation.md
GET .../artifacts/skills/{id}/skills/{id}/commands/add-animation.md/files/add-animation.md - 404
```

**Fix strategy**: Two-phase approach. Phase 1 fixes the root cause in the heuristic detector so embedded artifacts are never promoted to top-level detection. Phase 2 adds defensive fixes in the API endpoint and frontend, plus comprehensive tests.

**Success criteria**:
- Skills with embedded Commands, Agents, or nested Skills load without 404 errors in the Contents tab
- Embedded artifacts appear under their parent Skill's metadata, not as top-level items
- File content loading works for all embedded artifact types
- No regression in existing single-file artifact detection or top-level detection

---

## Root Cause Analysis

The bug spans three layers, each compounding the previous.

### Layer 1: Heuristic Detector (Primary Root Cause)

**File**: `skillmeat/core/marketplace/heuristic_detector.py`
**Lines**: 770-1008 (`_detect_single_file_artifacts()`), 1128-1228 (plugin/skill detection)

`_detect_single_file_artifacts()` scans `.md` files inside skill directories and registers each as a standalone top-level artifact. For a skill at `skills/agentient-frontend-tools/skills/agentient-frontend-ui/` containing `commands/add-animation.md`, the file is promoted to a top-level Command with `artifact_path = "skills/.../commands/add-animation.md"`.

The detector performs skill detection (directory-based, requires `SKILL.md`) and single-file detection as independent passes without cross-referencing. There is no guard that checks whether a candidate file already falls within a previously detected Skill's directory tree.

### Layer 2: File Serving Endpoint (Secondary)

**File**: `skillmeat/api/routers/marketplace_sources.py`
**Lines**: 5429-5600

The endpoint `GET /api/v1/marketplace/sources/{source_id}/artifacts/{artifact_path}/files/{file_path}` assumes `artifact_path` is a directory. When `artifact_path` is the file itself (e.g., `skills/.../commands/add-animation.md`) and `file_path` is `add-animation.md`, the resolver appends `file_path` to `artifact_path`, constructing a non-existent double path.

### Layer 3: Frontend URL Construction (Tertiary)

**File**: `skillmeat/web/sdk/services/MarketplaceSourcesService.ts`
**Lines**: 1005-1026

The SDK uses `artifact.path` directly as `artifactPath`, without checking whether the path is already a file path. This produces the malformed URL pattern `.../artifacts/.../commands/add-animation.md/files/add-animation.md`.

---

## Phase 1: Detection Fix (Backend)

**Goal**: Prevent embedded artifacts from being promoted as top-level items. Surface them as metadata on their parent Skill instead.

**Entry criteria**: Bug is reproducible; `heuristic_detector.py` is understood.
**Exit criteria**: Embedded artifacts no longer appear as top-level; parent Skill metadata lists them under `embedded_artifacts` or `children`.

### Task Table

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|----|------|-------------|---------------------|----------|----------------|
| P1-T1 | Build skill directory exclusion set | After Skill detection completes, collect all detected Skill directory paths into a `skill_dirs` set. Pass this set into `_detect_single_file_artifacts()`. | All skill root paths are present in the set; no performance regression for large repos. | 1 pt | `python-backend-engineer` |
| P1-T2 | Guard single-file detection against skill subtrees | Inside `_detect_single_file_artifacts()`, before creating a new artifact for a file, check whether any ancestor path of that file is in `skill_dirs`. If yes, skip top-level promotion. | Files under `skills/foo/commands/*.md` are skipped when `skills/foo` is a detected Skill. Unit test covers this guard. | 2 pt | `python-backend-engineer` |
| P1-T3 | Add embedded_artifacts field to DetectedArtifact model | Extend the `DetectedArtifact` dataclass/model with an `embedded_artifacts: list[DetectedArtifact]` field (default empty list). Mirror how composites expose children. | Field is present; serialization to dict/JSON includes it; existing artifacts unaffected (field defaults to `[]`). | 1 pt | `python-backend-engineer` |
| P1-T4 | Populate embedded_artifacts on Skill artifacts | When `_detect_single_file_artifacts()` encounters a file inside a Skill's directory tree, append a child `DetectedArtifact` (with correct relative path, type, and name) to the parent Skill's `embedded_artifacts` list. | `parent.embedded_artifacts` contains one entry per embedded file. The child's `path` is the correct repo-relative path (not duplicated). | 2 pt | `python-backend-engineer` |
| P1-T5 | Verify scanner orchestration propagates embedded artifacts | Confirm `github_scanner.py` (or wherever `DetectedArtifact` is persisted to DB) passes `embedded_artifacts` through to storage. No data is silently dropped. | `embedded_artifacts` values reach the DB or are at minimum accessible from the parent artifact record in API responses. | 1 pt | `python-backend-engineer` |

**Phase 1 Quality Gate**:
- [ ] `_detect_single_file_artifacts()` skips files inside detected Skill directories
- [ ] Parent Skill artifact's `embedded_artifacts` list is populated with correct child entries
- [ ] Child entries carry correct `path` (no duplication)
- [ ] No regression: existing top-level Command/Agent detection still works
- [ ] Manual smoke test: load `agentient-frontend-tools` source; Contents tab shows embedded artifacts under parent Skill, not as top-level items

---

## Phase 2: Defensive Fixes and Testing (Full Stack)

**Goal**: Add fallback path resolution in the API and defensive URL construction on the frontend. Cover all embedded artifact scenarios with tests.

**Entry criteria**: Phase 1 complete; embedded artifacts no longer appear top-level.
**Exit criteria**: File content loading works for all artifact types; test suite covers embedded scenarios.

### Task Table

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|----|------|-------------|---------------------|----------|----------------|
| P2-T1 | Defensive path resolution in file serving endpoint | In `marketplace_sources.py` lines 5492-5501: when `artifact_path` ends with a file extension (`.md`, `.py`, etc.), treat `artifact_path` itself as the file path and ignore the appended `file_path`. Add a fallback that resolves the correct filesystem path. | Requests with a file-path `artifact_path` return 200 with correct content. Requests with directory `artifact_path` (existing behavior) unchanged. | 2 pt | `python-backend-engineer` |
| P2-T2 | Defensive URL construction in frontend SDK | In `MarketplaceSourcesService.ts` lines 1005-1026: detect when `artifact.path` ends with a file extension. If yes, strip the filename from `artifactPath` or use the parent directory so the appended `/files/{file_path}` is not duplicated. | No double-file-path URLs generated. Existing directory-based artifact URLs unchanged. | 1 pt | `ui-engineer-enhanced` |
| P2-T3 | Update source detail page rendering | Audit `skillmeat/web/app/marketplace/sources/[id]/page.tsx` and related components. Ensure the artifact tree correctly renders embedded artifacts under their parent Skill (not as top-level list entries). Add visual distinction if needed. | Embedded artifacts shown as children of parent Skill in UI. Top-level artifacts list does not include embedded items. | 2 pt | `ui-engineer-enhanced` |
| P2-T4 | Unit tests: heuristic detector embedded artifact handling | Add test cases to `tests/test_heuristic_detector.py` (or equivalent). Scenarios: Skill with embedded Commands, Skill with embedded Agents, nested Skills (skill within skill), Skill with no embedded artifacts (regression). | All new test cases pass; no existing tests break. | 2 pt | `python-backend-engineer` |
| P2-T5 | API integration tests: file serving endpoint | Add tests for the file serving endpoint covering: directory-based artifact path (existing), file-path artifact path (new defensive case), embedded artifact file content retrieval. | All new tests pass; endpoint returns correct content or 404 with meaningful message. | 1 pt | `python-backend-engineer` |

**Phase 2 Quality Gate**:
- [ ] File serving endpoint returns 200 for embedded artifact file requests (no more 404)
- [ ] Frontend SDK generates correct URLs for both directory-based and file-path artifacts
- [ ] Source detail page renders embedded artifacts as children, not top-level
- [ ] All new unit and integration tests pass
- [ ] No regression in existing marketplace functionality (`pytest tests/` clean)
- [ ] TypeScript type-check passes (`pnpm type-check`)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Skill directory set construction is expensive for large repos | Medium | Low | Build the set once per scan pass; use `str.startswith()` checks (O(n) but fast for typical repo sizes) |
| `embedded_artifacts` field breaks existing API consumers | Low | Medium | Field defaults to `[]`; existing serialization is additive; validate no consumers check for exact key absence |
| Defensive endpoint fix masks future path bugs | Medium | Low | Add explicit logging when fallback path resolution triggers; include source artifact type in log context |
| Frontend rendering change introduces visual regression | Low | Medium | Scope UI change to source detail page only; delegate review to `task-completion-validator` before merging |
| Nested Skills (skill-within-skill) creates unbounded recursion | Low | High | Limit `embedded_artifacts` population to one level of nesting for Phase 1; add recursion guard (max depth = 2) |

---

## Orchestration Quick Reference

### Phase 1 — Batch 1 (all tasks sequential due to data model dependency)

```python
# P1-T1 + P1-T3 can run in parallel (independent changes)
Task("python-backend-engineer",
  """Fix embedded artifact detection in heuristic detector.

  Context: Skills with embedded Commands (e.g., add-animation.md inside a Skill directory)
  are incorrectly promoted as top-level artifacts. See bug trace in plan.

  Files:
  - skillmeat/core/marketplace/heuristic_detector.py (primary)
  - skillmeat/core/marketplace/github_scanner.py (verify propagation)

  Tasks (implement in this order):
  1. [P1-T3] Add `embedded_artifacts: list['DetectedArtifact'] = field(default_factory=list)`
     to the DetectedArtifact dataclass. Mirror the composites pattern.
  2. [P1-T1] After skill detection, collect all detected Skill paths into a set `skill_dirs`.
     Pass this set into `_detect_single_file_artifacts()` as a parameter.
  3. [P1-T2] Inside `_detect_single_file_artifacts()`, before creating an artifact for a
     candidate file, check if any ancestor path is in `skill_dirs`. If yes, skip top-level
     promotion.
  4. [P1-T4] When a file is skipped (inside a Skill dir), find the parent Skill artifact
     and append a child DetectedArtifact with the correct relative path to its
     `embedded_artifacts` list.
  5. [P1-T5] Confirm `github_scanner.py` passes embedded_artifacts to storage; add a log
     statement if embedded_artifacts are dropped.

  Follow existing patterns in the file for DetectedArtifact creation.
  Plan reference: docs/project_plans/implementation_plans/bugs/marketplace-embedded-artifacts-v1.md
  """)
```

### Phase 2 — Batch 1 (backend + frontend in parallel)

```python
# Backend defensive fix
Task("python-backend-engineer",
  """Add defensive path resolution and tests for embedded artifact file serving.

  Files:
  - skillmeat/api/routers/marketplace_sources.py (lines ~5492-5501)
  - tests/test_heuristic_detector.py (or equivalent test file)

  Tasks:
  1. [P2-T1] In the file serving endpoint, detect when `artifact_path` ends with a file
     extension. If yes, use `artifact_path` directly as the resolved file path instead of
     appending `file_path`. Preserve existing directory-path behavior unchanged.
     Add a debug log when the fallback triggers.
  2. [P2-T4] Add unit tests for heuristic detector covering:
     - Skill with embedded Commands (should appear in embedded_artifacts, not top-level)
     - Skill with embedded Agents
     - Nested skills (skill within skill, limit to 1 level)
     - Skill with no embedded artifacts (regression: embedded_artifacts == [])
  3. [P2-T5] Add API integration tests for the file serving endpoint:
     - Directory-based artifact path (existing behavior, regression test)
     - File-path artifact path (new defensive fallback)

  Plan reference: docs/project_plans/implementation_plans/bugs/marketplace-embedded-artifacts-v1.md
  """)

# Frontend defensive fix (parallel with backend)
Task("ui-engineer-enhanced",
  """Fix frontend URL construction and rendering for embedded marketplace artifacts.

  Files:
  - skillmeat/web/sdk/services/MarketplaceSourcesService.ts (lines ~1005-1026)
  - skillmeat/web/app/marketplace/sources/[id]/page.tsx (and related components)

  Tasks:
  1. [P2-T2] In MarketplaceSourcesService.ts, before using artifact.path as artifactPath,
     check if it ends with a file extension (e.g., .md). If yes, derive the parent directory
     as artifactPath so the appended /files/{file_path} suffix is not duplicated.
  2. [P2-T3] In the source detail page, ensure the artifact tree renders embedded_artifacts
     as children under their parent Skill. Embedded artifacts should NOT appear in the
     top-level artifact list. Add visual indentation or grouping consistent with existing
     composite/plugin child rendering patterns.

  Follow component patterns in .claude/context/key-context/component-patterns.md.
  Plan reference: docs/project_plans/implementation_plans/bugs/marketplace-embedded-artifacts-v1.md
  """)
```

### Validation (after Phase 2 batch)

```python
Task("task-completion-validator",
  """Validate marketplace-embedded-artifacts fix.

  Verify:
  1. pytest passes for heuristic detector and marketplace API tests
  2. pnpm type-check passes in skillmeat/web/
  3. Source detail page renders embedded artifacts as children of parent Skill
  4. No 404 errors when loading file content for embedded artifacts
  5. Plan docs/project_plans/implementation_plans/bugs/marketplace-embedded-artifacts-v1.md
     reflects current state

  Report any failures with specific file and line references.
  """)
```
