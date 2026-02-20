---
title: Context Entities Page Fix - Implementation Plan
description: 'Fix broken context entities page: entity type display, form visibility,
  and design consistency'
audience:
- ai-agents
- developers
tags:
- bug-fix
- frontend
- context-entities
- ui
created: 2025-12-20
updated: 2025-12-20
category: bug-fix
status: completed
related:
- /docs/dev/designs/screenshots/context-entities-v1.png
schema_version: 2
doc_type: implementation_plan
feature_slug: context-entities-page-fix
prd_ref: null
---
# Context Entities Page Fix - Implementation Plan

## Executive Summary

The /context-entities page has three critical issues:
1. **Entity type display broken**: All cards show "Unknown entity type:" error
2. **Form shown inline**: Entity creation form visible below catalog instead of in modal
3. **Design inconsistency**: Page doesn't fully follow modal patterns from /collection

**Priority**: High - page is currently unusable for viewing existing entities

## Root Cause Analysis

### Issue 1: Unknown Entity Type

**Location**: `skillmeat/web/components/context/context-entity-card.tsx` lines 214-225

**Problem**: The `typeConfig` record at line 50 expects specific string keys, but the API may be returning different values (case mismatch or enum serialization issue).

**Backend enum** (`skillmeat/api/schemas/context_entity.py`):
```python
class ContextEntityType(str, Enum):
    PROJECT_CONFIG = "project_config"
    SPEC_FILE = "spec_file"
    RULE_FILE = "rule_file"
    CONTEXT_FILE = "context_file"
    PROGRESS_TEMPLATE = "progress_template"
```

**Frontend typeConfig** (`context-entity-card.tsx`):
```typescript
const typeConfig: Record<ContextEntityType, TypeConfig> = {
  project_config: {...},
  spec_file: {...},
  rule_file: {...},
  context_file: {...},
  progress_template: {...},
};
```

**Diagnosis needed**: Check actual API response to see what `entity_type` values are being returned.

### Issue 2: Form Shown Inline

**Location**: `skillmeat/web/app/context-entities/page.tsx` lines 313-319

**Current Implementation**:
```tsx
<ContextEntityEditor
  entity={editingEntity}
  open={isEditorOpen}
  onClose={handleEditorClose}
  onSuccess={handleEditorSuccess}
/>
```

**Problem**: Either:
1. `isEditorOpen` is incorrectly initialized to `true`
2. `ContextEntityEditor` component renders content even when `open={false}`
3. The Dialog wrapper is missing or broken

### Issue 3: Design Inconsistency

**Current**: Uses separate modal components (ContextEntityDetail, ContextEntityEditor, DeployToProjectDialog)
**Target**: Should use unified modal pattern like collections page with UnifiedEntityModal

## Implementation Plan

### Phase 1: Bug Fixes (Critical)

#### Task 1.1: Fix Entity Type Display
**Priority**: P0
**Assigned**: ui-engineer-enhanced
**Effort**: 30 min

1. Add API call logging to see actual `entity_type` values returned
2. Update `ContextEntityCard` to normalize entity_type values:
   ```typescript
   // Normalize entity_type to handle potential case mismatches
   const normalizedType = entity.entity_type?.toLowerCase() as ContextEntityType;
   const config = typeConfig[normalizedType];
   ```
3. Add fallback config for unknown types instead of error state:
   ```typescript
   const defaultConfig: TypeConfig = {
     icon: FileText,
     label: 'Entity',
     borderColor: 'border-l-gray-500',
     bgColor: 'bg-gray-500/[0.02]',
     badgeClassName: 'border-gray-500 text-gray-700 bg-gray-50',
   };
   const config = typeConfig[normalizedType] || defaultConfig;
   ```

#### Task 1.2: Fix Editor Modal Visibility
**Priority**: P0
**Assigned**: ui-engineer-enhanced
**Effort**: 30 min

1. Read `ContextEntityEditor` component to understand structure
2. Ensure Dialog wrapper properly respects `open` prop
3. Add `open={false}` default if missing
4. Verify modal only renders content when open

### Phase 2: Verification & Testing

#### Task 2.1: Test Entity Type Display
**Priority**: P1
**Assigned**: ui-engineer-enhanced
**Effort**: 15 min

1. Load /context-entities page
2. Verify all existing entities display correct type badges
3. Verify color-coded borders appear correctly
4. Test with entities of each type

#### Task 2.2: Test Modal Behavior
**Priority**: P1
**Assigned**: ui-engineer-enhanced
**Effort**: 15 min

1. Verify page loads without form visible
2. Click "Add Entity" button
3. Verify modal opens correctly
4. Close modal, verify it closes
5. Click entity card, verify detail modal opens
6. Test edit and deploy flows

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `skillmeat/web/components/context/context-entity-card.tsx` | Edit | Add type normalization and fallback |
| `skillmeat/web/components/context/context-entity-editor.tsx` | Investigate | Verify Dialog wrapper behavior |
| `skillmeat/web/app/context-entities/page.tsx` | Possibly edit | Fix modal state if needed |

## Success Criteria

1. ✅ All existing context entities display with correct type badges
2. ✅ Entity cards show colored left borders based on type
3. ✅ Page loads without creation form visible
4. ✅ "Add Entity" button opens modal correctly
5. ✅ Clicking entity card opens detail view
6. ✅ Edit and Deploy flows work correctly

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Backend returns unexpected type values | Medium | Add logging, normalize values |
| Editor component has structural issues | Low | May need component refactor |
| Type definitions out of sync | Low | Update TypeScript types |

## Orchestration Quick Reference

**Phase 1** (Sequential - fix bugs first):
- TASK-1.1 → `ui-engineer-enhanced` (30 min)
- TASK-1.2 → `ui-engineer-enhanced` (30 min) - depends on 1.1

**Phase 2** (After fixes):
- TASK-2.1 → `ui-engineer-enhanced` (15 min)
- TASK-2.2 → `ui-engineer-enhanced` (15 min)

### Task Delegation Commands

```
Task("ui-engineer-enhanced", "TASK-1.1: Fix entity type display bug in context-entity-card.tsx.

Problem: All entities show 'Unknown entity type:' error because typeConfig lookup fails.

Files:
- skillmeat/web/components/context/context-entity-card.tsx (primary)
- skillmeat/web/types/context-entity.ts (reference)

Changes needed:
1. Add normalization to handle potential case mismatches in entity_type
2. Add fallback config for unknown types with gray styling instead of error
3. Add console.log temporarily to debug actual values received

Expected behavior: All entity cards display proper type badges (Config, Spec, Rule, Context, Progress)")

Task("ui-engineer-enhanced", "TASK-1.2: Fix editor modal visibility bug.

Problem: Entity creation form shows inline below catalog instead of in modal.

Files:
- skillmeat/web/components/context/context-entity-editor.tsx (investigate)
- skillmeat/web/app/context-entities/page.tsx (verify state management)

Changes needed:
1. Ensure Dialog component respects open={false} and doesn't render content
2. Verify isEditorOpen state initializes to false
3. Fix any Dialog wrapper issues

Expected behavior: Page loads with only filter bar and entity grid - no form visible")
```

## Future Improvements (Out of Scope)

For design consistency with /collection page, consider:
1. Migrate to UnifiedEntityModal for entity viewing/editing
2. Consider toolbar-style filters instead of sidebar
3. Add view mode switching (grid/list)

These are enhancement items, not critical bug fixes.
