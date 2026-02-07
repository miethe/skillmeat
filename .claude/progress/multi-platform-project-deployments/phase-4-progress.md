---
type: progress
prd: "multi-platform-project-deployments-v1"
phase: 4
title: "Discovery, Cache, and UI/UX"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 19
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer", "ui-engineer-enhanced", "frontend-developer"]
contributors: ["ui-designer"]

tasks:
  - id: "P4-T1"
    description: "Extend FileWatcher to all profile roots - Update skillmeat/cache/watcher.py to monitor all configured profile roots (.codex/, .gemini/, custom); emit events with profile info"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-T5"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "P4-T2"
    description: "Update cache invalidation for profile-aware changes - Modify cache invalidation to handle all profiles; refresh_single_artifact_cache accepts profile param; project stats aggregate across profiles"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-T1"]
    estimated_effort: "1.5 pts"
    priority: "high"

  - id: "P4-T3"
    description: "Implement platform detection on artifact import - Scan source structure for .codex/.gemini dirs; auto-tag artifacts with target_platforms from source; users can override"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T2", "P2-T5"]
    estimated_effort: "1.5 pts"
    priority: "medium"

  - id: "P4-T4"
    description: "Create DeploymentProfile selector component - Build React dropdown component showing available profiles (Claude, Codex, Gemini, custom); default to primary; clear descriptions per platform"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P1-T6"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "P4-T5"
    description: "Update deploy-dialog component for profile support - Modify deploy-dialog.tsx to include profile selector; add --all-profiles checkbox for one-click deploy to all"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P4-T4"]
    estimated_effort: "1.5 pts"
    priority: "high"

  - id: "P4-T6"
    description: "Update template-deploy-wizard for profile awareness - Modify template-deploy-wizard.tsx to accept profile during template deployment; context entities in template respect profile"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P4-T4"]
    estimated_effort: "1.5 pts"
    priority: "medium"

  - id: "P4-T7"
    description: "Add profile parameter to API client deployment calls - Update skillmeat/web/lib/api/deployments.ts to send deployment_profile_id in deploy requests"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P2-T10"]
    estimated_effort: "1 pt"
    priority: "high"

  - id: "P4-T8"
    description: "Generate CLI commands with profile support - Update skillmeat/web/lib/cli-commands.ts to generate deploy commands with --profile and --all-profiles flags"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P2-T6"]
    estimated_effort: "1 pt"
    priority: "medium"

  - id: "P4-T9"
    description: "Create deployment status component showing profiles - Build component displaying status segmented by profile; artifact name, version, deployed profiles (checkmarks), last deployed time per profile"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P2-T11"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "P4-T10"
    description: "Create cross-platform sync comparison view - Build UI showing sync state across profiles (e.g., Claude: v1.2, Codex: v1.1, Gemini: none); highlight mismatches; suggest sync actions"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P2-T11", "P3-T13"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "P4-T11"
    description: "Add artifact filter by target_platforms - Extend artifact list/search UI to filter by target_platforms (show Codex-only, universal, etc.); platform tags in list"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P1-T4"]
    estimated_effort: "1.5 pts"
    priority: "medium"

  - id: "P4-T12"
    description: "Create deployment profile management UI - Build page at /projects/[id]/profiles for viewing/editing profiles; add profiles, update artifact path maps, configure context prefixes"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P1-T11"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "P4-T13"
    description: "Create hooks for profile-aware deployment state - Build useDeploymentProfiles(projectId), useDeploymentStatus(artifactId, projectId), useProfileSelector() hooks; add to hooks/index.ts"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P2-T10", "P2-T11"]
    estimated_effort: "1.5 pts"
    priority: "high"

  - id: "P4-T14"
    description: "Update frontend types for profile info - Extend types/deployments.ts with DeploymentProfile, DeploymentStatus; update types/artifacts.ts with target_platforms; match backend schemas"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P1-T7", "P4-T7"]
    estimated_effort: "1 pt"
    priority: "high"

  - id: "P4-T15"
    description: "Add profile selection to context entity deploy UI - Extend context entity deployment UI with profile selector; match artifact deploy UX"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P3-T7"]
    estimated_effort: "1 pt"
    priority: "medium"

  - id: "P4-T16"
    description: "Design platform badge/icon component - Create reusable component showing platform badges (Claude Code, Codex, Gemini icons); used in selectors, status, filters"
    status: "pending"
    assigned_to: ["ui-designer"]
    dependencies: []
    estimated_effort: "0.5 pts"
    priority: "medium"

  - id: "P4-T17"
    description: "Update API endpoints to return profile info - Ensure GET /projects/{id} returns deployment_profiles, GET /artifacts/{id} returns target_platforms, status returns per-profile breakdown"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-T10", "P2-T11"]
    estimated_effort: "1 pt"
    priority: "high"

  - id: "P4-T18"
    description: "Frontend integration tests: profile selection and deploy - Test deploying with profile selector; test all-profiles; test sync status view; test artifact platform filter"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P4-T5", "P4-T9", "P4-T10"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "P4-T19"
    description: "End-to-end test: multi-platform deployment workflow - Full E2E: create project, set up profiles, deploy via UI, verify status, verify CLI commands match UI state"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P4-T5", "P4-T9", "P4-T18"]
    estimated_effort: "1.5 pts"
    priority: "high"

parallelization:
  batch_1: ["P4-T1", "P4-T3", "P4-T4", "P4-T7", "P4-T8", "P4-T11", "P4-T12", "P4-T13", "P4-T16", "P4-T17"]
  batch_2: ["P4-T2", "P4-T5", "P4-T6", "P4-T9", "P4-T10", "P4-T14", "P4-T15"]
  batch_3: ["P4-T18"]
  batch_4: ["P4-T19"]
  critical_path: ["P4-T4", "P4-T5", "P4-T18", "P4-T19"]
  estimated_total_time: "20 pts (4 batches)"

blockers: []

success_criteria:
  - { id: "SC-1", description: "FileWatcher monitors all profile roots; cache invalidation working for all platforms", status: "pending" }
  - { id: "SC-2", description: "Platform detection on import working; artifacts tagged with source platform", status: "pending" }
  - { id: "SC-3", description: "Deploy dialog renders profile selector; form includes profile ID", status: "pending" }
  - { id: "SC-4", description: "--all-profiles checkbox/flag works; artifacts deploy to all profiles", status: "pending" }
  - { id: "SC-5", description: "Deployment status component shows per-profile breakdown correctly", status: "pending" }
  - { id: "SC-6", description: "Cross-platform sync comparison UI renders and highlights mismatches", status: "pending" }
  - { id: "SC-7", description: "Artifact filtering by target_platforms working in search/list", status: "pending" }
  - { id: "SC-8", description: "Profile management UI allows creating/editing profiles", status: "pending" }
  - { id: "SC-9", description: "Hooks exported in hooks/index.ts and documented", status: "pending" }
  - { id: "SC-10", description: "Frontend types match backend API contracts", status: "pending" }
  - { id: "SC-11", description: "All integration and E2E tests passing", status: "pending" }
  - { id: "SC-12", description: "Accessibility audit passed for new UI components", status: "pending" }

files_modified:
  - "skillmeat/cache/watcher.py"
  - "skillmeat/api/routers/deployments.py"
  - "skillmeat/api/routers/projects.py"
  - "skillmeat/web/components/profile-selector.tsx"
  - "skillmeat/web/components/platform-badge.tsx"
  - "skillmeat/web/components/deployment-status-profile-view.tsx"
  - "skillmeat/web/components/sync-comparison-view.tsx"
  - "skillmeat/web/components/collection/deploy-dialog.tsx"
  - "skillmeat/web/components/templates/template-deploy-wizard.tsx"
  - "skillmeat/web/components/artifact-list.tsx"
  - "skillmeat/web/app/projects/[id]/profiles/"
  - "skillmeat/web/lib/api/deployments.ts"
  - "skillmeat/web/lib/cli-commands.ts"
  - "skillmeat/web/hooks/index.ts"
  - "skillmeat/web/types/deployments.ts"
  - "skillmeat/web/types/artifacts.ts"
---

# Phase 4: Discovery, Cache, and UI/UX

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/multi-platform-project-deployments/phase-4-progress.md -t P4-T1 -s completed
```

---

## Objective

Bring project discovery and cache infrastructure into the multi-platform world and create frontend UX for managing deployments across platforms. Expand FileWatcher to monitor all profile roots, update project stats aggregation, add platform detection on artifact import, and build UI components for profile selection and cross-platform sync visualization.

---

## Orchestration Quick Reference

**Batch 1** (Parallel - independent tasks with resolved Phase 1-3 deps):
- P4-T1 -> `python-backend-engineer` (2 pts) - FileWatcher
- P4-T3 -> `python-backend-engineer` (1.5 pts) - Platform detection
- P4-T4 -> `ui-engineer-enhanced` (2 pts) - Profile selector
- P4-T7 -> `frontend-developer` (1 pt) - API client
- P4-T8 -> `frontend-developer` (1 pt) - CLI commands
- P4-T11 -> `frontend-developer` (1.5 pts) - Artifact filter
- P4-T12 -> `ui-engineer-enhanced` (2 pts) - Profile management UI
- P4-T13 -> `frontend-developer` (1.5 pts) - Hooks
- P4-T16 -> `ui-designer` (0.5 pts) - Platform badges
- P4-T17 -> `python-backend-engineer` (1 pt) - API profile info

**Batch 2** (Parallel - depend on Batch 1 components):
- P4-T2 -> `python-backend-engineer` (1.5 pts) - Cache invalidation
- P4-T5 -> `frontend-developer` (1.5 pts) - Deploy dialog
- P4-T6 -> `frontend-developer` (1.5 pts) - Template wizard
- P4-T9 -> `ui-engineer-enhanced` (2 pts) - Status component
- P4-T10 -> `ui-engineer-enhanced` (2 pts) - Sync comparison
- P4-T14 -> `frontend-developer` (1 pt) - Types
- P4-T15 -> `frontend-developer` (1 pt) - Context entity UI

**Batch 3** (Sequential - integration tests):
- P4-T18 -> `frontend-developer` (2 pts)

**Batch 4** (Sequential - E2E tests):
- P4-T19 -> `frontend-developer` (1.5 pts)

### Task Delegation Commands

**Batch 1**:
```python
Task("python-backend-engineer", "P4-T1: Extend FileWatcher to all profile roots. File: skillmeat/cache/watcher.py (lines 204-205, 317). Monitor all configured profile roots (.codex/, .gemini/, custom) not just .claude/. Emit events with profile info. Changes in any profile trigger cache invalidation.")

Task("python-backend-engineer", "P4-T3: Implement platform detection on artifact import. When importing from repos with .codex/ or .gemini/ dirs, scan source structure and auto-tag artifacts with target_platforms based on source. Users can override during import.")

Task("ui-engineer-enhanced", "P4-T4: Create DeploymentProfile selector component. File: skillmeat/web/components/profile-selector.tsx. Dropdown showing available profiles (Claude, Codex, Gemini, custom). Default to primary profile. Show platform name and description. Integrate with deployment dialog.")

Task("frontend-developer", "P4-T7: Add profile parameter to API client deployment calls. File: skillmeat/web/lib/api/deployments.ts. Send deployment_profile_id in deploy requests. Update all artifact and context entity deploy functions to accept profile parameter.")

Task("frontend-developer", "P4-T8: Generate CLI commands with profile support. File: skillmeat/web/lib/cli-commands.ts. Generate 'skillmeat deploy <artifact> --profile <id>' and 'skillmeat deploy <artifact> --all-profiles' commands based on user selections.")

Task("frontend-developer", "P4-T11: Add artifact filter by target_platforms. File: skillmeat/web/components/artifact-list.tsx. Filter dropdown for target_platforms (show Codex-only, universal, etc.). Show platform tags in artifact list. Works in search results.")

Task("ui-engineer-enhanced", "P4-T12: Create deployment profile management UI. File: skillmeat/web/app/projects/[id]/profiles/. Page for viewing/editing project profiles. Allow adding new profiles, updating artifact path maps, configuring context prefixes. Forms validate JSON artifact path maps.")

Task("frontend-developer", "P4-T13: Create hooks for profile-aware deployment state. File: skillmeat/web/hooks/index.ts. Hooks: useDeploymentProfiles(projectId), useDeploymentStatus(artifactId, projectId) with per-profile status, useProfileSelector() for state management. Follow React Query patterns.")

Task("ui-designer", "P4-T16: Design platform badge/icon component. File: skillmeat/web/components/platform-badge.tsx. Reusable component showing platform badges (Claude Code, Codex, Gemini icons). Used in profile selector, status displays, artifact filters. Consistent styling.")

Task("python-backend-engineer", "P4-T17: Update API endpoints to return profile info. Ensure: GET /projects/{id} returns deployment_profiles list, GET /artifacts/{id} returns target_platforms, GET /projects/{id}/status returns per-profile deployment breakdown. Update OpenAPI docs.")
```

**Batch 2**:
```python
Task("python-backend-engineer", "P4-T2: Update cache invalidation for profile-aware changes. Modify cache invalidation in skillmeat/cache/ to handle all profiles. refresh_single_artifact_cache() accepts profile parameter. Project stats aggregate across all profiles and show per-profile breakdown.")

Task("frontend-developer", "P4-T5: Update deploy-dialog component for profile support. File: skillmeat/web/components/collection/deploy-dialog.tsx. Include profile selector (P4-T4). Add --all-profiles checkbox for one-click deploy to all. Form submits deployment_profile_id to backend.")

Task("frontend-developer", "P4-T6: Update template-deploy-wizard for profile awareness. File: skillmeat/web/components/templates/template-deploy-wizard.tsx. Accept profile during template deployment. Context entities in template deploy to correct profile.")

Task("ui-engineer-enhanced", "P4-T9: Create deployment status component showing profiles. File: skillmeat/web/components/deployment-status-profile-view.tsx. Display status segmented by profile. Show artifact name, version, deployed profiles (checkmarks), last deployed time per profile. Respect platform filtering.")

Task("ui-engineer-enhanced", "P4-T10: Create cross-platform sync comparison view. File: skillmeat/web/components/sync-comparison-view.tsx. Show sync state across profiles (e.g., Claude: v1.2, Codex: v1.1, Gemini: none). Highlight mismatches. Suggest sync actions per profile.")

Task("frontend-developer", "P4-T14: Update frontend types for profile info. Files: skillmeat/web/types/deployments.ts, skillmeat/web/types/artifacts.ts. Add DeploymentProfile type, DeploymentStatus with per-profile breakdown, target_platforms on artifacts. TS types must match backend Pydantic models.")

Task("frontend-developer", "P4-T15: Add profile selection to context entity deploy UI. Extend context entity deployment UI with profile selector. Allow deploying to specific profile or all profiles. Match artifact deploy UX.")
```

**Batch 3**:
```python
Task("frontend-developer", "P4-T18: Frontend integration tests: profile selection and deploy. Test deploying artifact with profile selector. Test all-profiles. Test sync status view rendering. Test artifact filter by platform.")
```

**Batch 4**:
```python
Task("frontend-developer", "P4-T19: End-to-end test: multi-platform deployment workflow. Full E2E: create project, set up multiple profiles, deploy artifacts to different profiles via UI, verify status, verify CLI commands match UI state.")
```

---

## Implementation Notes

### Key Decisions
- UI component design (P4-T16, P4-T4) can start while Phase 3 is finishing
- Profile management (P4-T12) is a new page -- coordinate navigation integration
- Hooks follow React Query patterns used elsewhere in codebase

### Known Gotchas
- FileWatcher monitoring multiple roots may increase I/O -- consider debouncing
- Platform badge icons need coordination with design team
- Ensure profile selector dropdown handles projects with 1 profile gracefully
- Symlink-aware FileWatcher must coordinate with Phase 2 symlink handling

---

## Completion Notes

_Fill in when phase is complete._
