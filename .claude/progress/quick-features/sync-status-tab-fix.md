---
feature: sync-status-tab-fix
status: completed
created: 2025-01-07
source: docs/project_plans/implementation_plans/bug-fixes/sync-status-tab-remediation-v1.md
tracking:
- REQ-20260107-skillmeat-01
- REQ-20260107-skillmeat-02
tasks:
- id: FIX-001
  name: Remove local-only early return
  status: pending
  assigned_to: ui-engineer-enhanced
- id: FIX-002
  name: Improve hasSource detection
  status: pending
  assigned_to: ui-engineer-enhanced
- id: FIX-003
  name: Set smart default scope
  status: pending
  assigned_to: ui-engineer-enhanced
- id: FIX-004
  name: Guard upstream query
  status: pending
  assigned_to: ui-engineer-enhanced
- id: FIX-005
  name: Handle empty diff state
  status: pending
  assigned_to: ui-engineer-enhanced
schema_version: 2
doc_type: quick_feature
feature_slug: sync-status-tab-fix
---

# Quick Feature: Sync Status Tab Fix

## Summary
Fix two bugs preventing Sync Status tab from working on /collection page:
1. 404 errors from upstream-diff API
2. "local-only" message blocking all artifacts

## Key File
`skillmeat/web/components/sync-status/sync-status-tab.tsx`

## Implementation Details
See: `docs/project_plans/implementation_plans/bug-fixes/sync-status-tab-remediation-v1.md`
