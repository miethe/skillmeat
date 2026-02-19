---
type: progress
prd: discovery-import-fixes-v1
phase: 2
phase_name: Duplicate Detection & Review Workflow
status: completed
progress: 100
created: 2026-01-09
updated: '2026-01-09'
request_log: REQ-20260109-skillmeat
implementation_plan: docs/project_plans/implementation_plans/harden-polish/discovery-import-fixes-v1.md
phase_detail: docs/project_plans/implementation_plans/harden-polish/discovery-import-fixes-v1/phase-2-duplicate-detection.md
depends_on:
- phase-1
tasks:
- id: P2-T1
  name: Hash-based deduplication integration
  status: completed
  assigned_to:
  - python-backend-engineer
  model: opus
  dependencies: []
  estimate: 6pts
  files:
  - skillmeat/core/discovery.py
  - skillmeat/core/marketplace/deduplication_engine.py
  - skillmeat/core/marketplace/content_hash.py
- id: P2-T2
  name: Duplicate review decision endpoint
  status: completed
  assigned_to:
  - python-backend-engineer
  model: opus
  dependencies: []
  estimate: 5pts
  files:
  - skillmeat/api/routers/artifacts.py
  - skillmeat/api/schemas/discovery.py
  - skillmeat/core/collection.py
- id: P2-T3
  name: Discovery filtering and grouping
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: opus
  dependencies:
  - P2-T1
  estimate: 5pts
  files:
  - skillmeat/web/components/discovery/DiscoveryTab.tsx
  - skillmeat/web/hooks/useProjectDiscovery.ts
  - skillmeat/web/types/discovery.ts
- id: P2-T4
  name: Duplicate review modal UI
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: opus
  dependencies:
  - P2-T1
  - P2-T2
  estimate: 6pts
  files:
  - skillmeat/web/components/discovery/DuplicateReviewModal.tsx (NEW)
  - skillmeat/web/components/discovery/DuplicateReviewTab.tsx (NEW)
  - skillmeat/web/hooks/useProjectDiscovery.ts
parallelization:
  batch_1:
  - P2-T1
  - P2-T2
  batch_2:
  - P2-T3
  - P2-T4
quality_gates:
- "Hash matching accuracy \u226595% across artifact types"
- Exact matches hidden from 'Ready to Import' list
- Review modal usable <2 min average per artifact
- Duplicate link relationships persisted in collection metadata
- Modal responsive on mobile (375px+)
- Keyboard navigation functional (Tab, Enter, Escape)
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
schema_version: 2
doc_type: progress
feature_slug: discovery-import-fixes-v1
---

# Phase 2: Duplicate Detection & Review Workflow

**Duration:** 2 weeks | **Effort:** 18-22 story points | **Priority:** HIGH

**Depends On:** Phase 1 completion (accurate status is foundational)

## Overview

Implement intelligent duplicate detection using hash matching from marketplace deduplication engine, plus a review workflow for users to confirm or reject potential matches.

## Quick Reference

### CLI Status Updates
```bash
# Mark task complete
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/discovery-import-fixes/phase-2-progress.md \
  -t P2-T1 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/discovery-import-fixes/phase-2-progress.md \
  --updates "P2-T1:completed,P2-T2:completed"
```

### Task Delegation
```
# Batch 1 (parallel - backend tasks)
Task("python-backend-engineer", "P2-T1: Integrate hash-based dedup from marketplace engine...", model="opus")
Task("python-backend-engineer", "P2-T2: Create POST /artifacts/confirm-duplicates endpoint...", model="opus")

# Batch 2 (after batch 1)
Task("ui-engineer-enhanced", "P2-T3: Add discovery filtering by match type...", model="opus")
Task("ui-engineer-enhanced", "P2-T4: Create DuplicateReviewModal component...", model="opus")
```

## Task Details

### P2-T1: Hash-Based Deduplication
**Goal:** Integrate marketplace deduplication engine for artifact matching

**Acceptance Criteria:**
- [ ] Compute content hash for each discovered artifact
- [ ] Query collection for matching hashes
- [ ] Return collection_status with match_type (exact/hash/name_type/none)
- [ ] Include matched_artifact_id for exact/hash matches
- [ ] Performance: <500ms for 100+ artifacts
- [ ] Reuse existing ContentHashCache for efficiency

### P2-T2: Duplicate Decision Endpoint
**Goal:** Process user decisions from duplicate review modal

**Acceptance Criteria:**
- [ ] POST /api/v1/artifacts/confirm-duplicates endpoint
- [ ] Accept matches (link discovered → collection), new_artifacts (import), skipped
- [ ] Persist duplicate_links in collection metadata
- [ ] Create audit log of all decisions
- [ ] Return counts (linked_count, imported_count, skipped_count)
- [ ] Atomic operation (all-or-nothing for consistency)

### P2-T3: Discovery Filtering & Grouping
**Goal:** Group discovered artifacts by match type in UI

**Acceptance Criteria:**
- [ ] Group artifacts into: New, Possible Duplicates, Exact Matches
- [ ] Hide exact matches from "Ready to Import" list
- [ ] Show "Possible Duplicates" with link to collection artifact
- [ ] Add "Review Duplicates" button when duplicates exist
- [ ] Update artifact counts per group
- [ ] Clear visual hierarchy with section headers

### P2-T4: Duplicate Review Modal
**Goal:** Create modal for reviewing and confirming duplicate matches

**Acceptance Criteria:**
- [ ] Three-tab layout: New Artifacts, Possible Duplicates, Exact Matches
- [ ] Side-by-side comparison: Discovered (left) vs Collection (right)
- [ ] Dropdown selector for potential matches (default: best match)
- [ ] "Skip" toggle to exclude from import
- [ ] "New Artifact" toggle if no matches are correct
- [ ] Confirm Matches, Import New Only, Cancel buttons
- [ ] Responsive on mobile (90%+ viewport)
- [ ] Keyboard navigation (Tab through items, Enter to confirm)

## Blockers

- Phase 1 must be complete (P2 depends on accurate status from P1)

## Notes

- Reuse existing marketplace deduplication_engine.py
- Reuse existing content_hash.py for hash computation
- Modal design should follow existing SkillMeat modal patterns
- Consider performance with large collections (1000+ artifacts)
