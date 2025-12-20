---
type: progress
prd: "artifact-deletion-v1"
phase: 3
title: "Polish & Documentation"
status: pending
progress: 0
total_tasks: 5
completed_tasks: 0
blocked_tasks: 0
created: "2025-12-20"
updated: "2025-12-20"

tasks:
  - id: "FE-014"
    title: "Performance optimization for deployment fetching"
    status: "pending"
    priority: "medium"
    estimate: "0.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    file_targets:
      - "skillmeat/web/components/entity/artifact-deletion-dialog.tsx"
    notes: "Optimize queries, add loading states, handle large deployment lists"

  - id: "FE-015"
    title: "Mobile responsiveness for deletion dialog"
    status: "pending"
    priority: "medium"
    estimate: "0.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    file_targets:
      - "skillmeat/web/components/entity/artifact-deletion-dialog.tsx"
    notes: "Test and fix responsive layout, touch targets for mobile"

  - id: "FE-016"
    title: "Final accessibility pass"
    status: "pending"
    priority: "medium"
    estimate: "0.5pt"
    assigned_to: ["a11y-sheriff"]
    dependencies: ["FE-014", "FE-015"]
    file_targets: []
    notes: "Final audit after all changes, verify with real screen readers"

  - id: "FE-017"
    title: "Update component documentation"
    status: "pending"
    priority: "low"
    estimate: "0.5pt"
    assigned_to: ["documentation-writer"]
    dependencies: []
    file_targets:
      - "skillmeat/web/components/entity/README.md"
    notes: "Add ArtifactDeletionDialog to component docs with usage examples"

  - id: "FE-018"
    title: "Code review and cleanup"
    status: "pending"
    priority: "high"
    estimate: "0.5pt"
    assigned_to: ["code-reviewer"]
    dependencies: ["FE-014", "FE-015", "FE-016"]
    file_targets: []
    notes: "Final code review for quality, patterns, and cleanup"

parallelization:
  batch_1: ["FE-014", "FE-015", "FE-017"]
  batch_2: ["FE-016"]
  batch_3: ["FE-018"]

blockers: []

phase_dependencies:
  - phase: 2
    required_tasks: ["FE-009", "FE-010", "FE-011"]

references:
  prd: "docs/project_plans/PRDs/features/artifact-deletion-v1.md"
  implementation_plan: "docs/project_plans/implementation_plans/features/artifact-deletion-v1.md"
---

# Phase 3: Polish & Documentation

## Summary

Phase 3 focuses on performance optimization, mobile responsiveness, final accessibility verification, documentation, and code review for production readiness.

**Estimated Effort**: 2.5 story points (1-2 days)
**Dependencies**: Phase 2 completion
**Assigned Agents**: ui-engineer-enhanced, a11y-sheriff, documentation-writer, code-reviewer

## Orchestration Quick Reference

### Batch 1 (Parallel - FE-014, FE-015, FE-017)

**FE-014** → `ui-engineer-enhanced` (0.5pt)

```
Task("ui-engineer-enhanced", "FE-014: Performance optimization for deployment fetching.

File: skillmeat/web/components/entity/artifact-deletion-dialog.tsx

Optimizations:
1. Only fetch deployments when toggle is enabled (lazy loading)
2. Add staleTime to deployment query to prevent refetching
3. Handle large deployment lists (>20) with virtualization or pagination hint
4. Add loading skeleton for expandable sections
5. Memoize filtered/grouped deployment lists with useMemo
6. Debounce checkbox changes if needed

Test with:
- Artifact deployed to 50+ projects
- Slow network conditions")
```

**FE-015** → `ui-engineer-enhanced` (0.5pt)

```
Task("ui-engineer-enhanced", "FE-015: Mobile responsiveness for deletion dialog.

File: skillmeat/web/components/entity/artifact-deletion-dialog.tsx

Mobile fixes:
1. Dialog should be full-width on small screens (max-w-lg → sm:max-w-lg)
2. Toggle labels should wrap correctly
3. Checkbox items should have adequate touch targets (min 44px)
4. Expandable sections should scroll independently if too tall
5. Buttons should stack on very small screens
6. Test at 320px, 375px, 414px, 768px breakpoints

Use Tailwind responsive classes (sm:, md:, lg:).
Test on iOS Safari and Android Chrome.")
```

**FE-017** → `documentation-writer` (0.5pt)

```
Task("documentation-writer", "FE-017: Update component documentation.

File: skillmeat/web/components/entity/README.md

Add section for ArtifactDeletionDialog:

## ArtifactDeletionDialog

Multi-step confirmation dialog for artifact deletion with cascade options.

### Usage

\`\`\`tsx
<ArtifactDeletionDialog
  entity={selectedEntity}
  open={showDialog}
  onOpenChange={setShowDialog}
  context='collection'
  onSuccess={() => handleDeletionComplete()}
/>
\`\`\`

### Props

| Prop | Type | Description |
|------|------|-------------|
| entity | Entity | The entity to delete |
| open | boolean | Dialog open state |
| onOpenChange | (open: boolean) => void | Open state handler |
| context | 'collection' | 'project' | Deletion context |
| projectPath? | string | Project path (for project context) |
| onSuccess? | () => void | Called after successful deletion |

### Features

- Context-aware messaging
- Cascade deletion toggles
- Project selection for bulk operations
- Deployment warning with RED styling
- Partial failure handling")
```

### Batch 2 (Sequential - Depends on FE-014, FE-015)

**FE-016** → `a11y-sheriff` (0.5pt)

```
Task("a11y-sheriff", "FE-016: Final accessibility pass.

Components:
- skillmeat/web/components/entity/artifact-deletion-dialog.tsx

Final verification:
1. Screen reader testing (VoiceOver, NVDA)
2. Keyboard-only navigation
3. Color contrast in all states (hover, focus, disabled)
4. Mobile VoiceOver testing
5. High contrast mode
6. Reduced motion preferences respected

Create accessibility report if any issues found.
Mark task complete only when all issues resolved.")
```

### Batch 3 (Sequential - Depends on FE-016)

**FE-018** → `code-reviewer` (0.5pt)

```
Task("code-reviewer", "FE-018: Final code review and cleanup.

Files to review:
- skillmeat/web/lib/api/artifacts.ts (new functions)
- skillmeat/web/hooks/use-artifact-deletion.ts
- skillmeat/web/components/entity/artifact-deletion-dialog.tsx
- skillmeat/web/components/entity/entity-actions.tsx (changes)
- skillmeat/web/components/entity/unified-entity-modal.tsx (changes)

Review criteria:
1. Code quality and readability
2. TypeScript types correct and complete
3. Error handling comprehensive
4. No console.logs or commented code
5. Consistent naming conventions
6. Performance considerations
7. Security (no XSS vectors, proper encoding)
8. Test coverage adequate

Provide feedback or approve for merge.")
```

## Key Files

| File | Purpose | Changes |
|------|---------|---------|
| `components/entity/artifact-deletion-dialog.tsx` | Dialog component | Performance + Mobile |
| `components/entity/README.md` | Component docs | +50 LOC |

## Acceptance Criteria

- [ ] Deployment fetching is lazy and optimized
- [ ] Dialog works well on mobile devices (320px+)
- [ ] Final accessibility audit passes
- [ ] Component documentation complete
- [ ] Code review approved
- [ ] No performance regressions

## Notes

- Phase 3 is polish - core functionality complete in Phases 1-2
- Can be done in parallel with other work if needed
- Code review is final gate before merge to main
