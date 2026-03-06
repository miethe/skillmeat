---
type: progress
schema_version: 2
doc_type: progress
prd: "aaa-rbac-foundation"
feature_slug: "aaa-rbac-foundation"
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
phase: 5
title: "Frontend Identity Integration - Clerk SDK & UI"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: ["frontend-developer"]

tasks:
  - id: "FE-001"
    description: "Install @clerk/nextjs; add ClerkProvider to app root; configure paths"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1 pt"
    priority: "critical"

  - id: "FE-002"
    description: "Create Login/Signup pages using Clerk components"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-001"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "FE-003"
    description: "Build Workspace Switcher component (Personal vs Team contexts)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-001"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "FE-004"
    description: "Update API client to inject Clerk auth token in Authorization header"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-001"]
    estimated_effort: "1 pt"
    priority: "critical"

  - id: "FE-005"
    description: "Implement Clerk middleware for route protection"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-001"]
    estimated_effort: "1 pt"
    priority: "high"

  - id: "FE-006"
    description: "Create user profile/settings page"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-002"]
    estimated_effort: "1 pt"
    priority: "medium"

  - id: "FE-007"
    description: "Add NEXT_PUBLIC_AUTH_ENABLED env var; conditionally skip Clerk in local mode"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-001"]
    estimated_effort: "1 pt"
    priority: "critical"

  - id: "FE-008"
    description: "Create Playwright E2E tests for auth flows"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["FE-004", "FE-006"]
    estimated_effort: "2 pts"
    priority: "medium"

parallelization:
  batch_1: ["FE-001"]
  batch_2: ["FE-002", "FE-003", "FE-004", "FE-005", "FE-007"]
  batch_3: ["FE-006", "FE-008"]
  critical_path: ["FE-001", "FE-004", "FE-008"]
  estimated_total_time: "6 days"

blockers: []

success_criteria:
  - { id: "SC-1", description: "Clerk SDK integrated and ClerkProvider wraps app", status: "pending" }
  - { id: "SC-2", description: "Login and signup pages functional", status: "pending" }
  - { id: "SC-3", description: "Workspace switcher changes org context", status: "pending" }
  - { id: "SC-4", description: "Auth token injected into all API calls", status: "pending" }
  - { id: "SC-5", description: "Protected routes redirect unauthenticated users", status: "pending" }
  - { id: "SC-6", description: "Zero-auth local mode works without Clerk", status: "pending" }

files_modified:
  - "skillmeat/web/app/layout.tsx"
  - "skillmeat/web/app/auth/login/page.tsx"
  - "skillmeat/web/app/auth/signup/page.tsx"
  - "skillmeat/web/components/workspace-switcher.tsx"
  - "skillmeat/web/lib/api-client.ts"
  - "skillmeat/web/middleware.ts"
  - "skillmeat/web/app/settings/page.tsx"
---

# aaa-rbac-foundation - Phase 5: Frontend Identity Integration - Clerk SDK & UI

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/aaa-rbac-foundation/phase-5-progress.md -t FE-001 -s completed
```

---

## Objective

Integrate Clerk SDK into the Next.js frontend. Build login/signup pages, workspace switcher, route protection, and auth token injection. Maintain zero-auth local mode via NEXT_PUBLIC_AUTH_ENABLED feature flag.
