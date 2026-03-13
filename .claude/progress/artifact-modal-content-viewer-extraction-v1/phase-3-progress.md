---
type: progress
schema_version: 2
doc_type: progress
prd: "artifact-modal-content-viewer-extraction-v1"
feature_slug: "artifact-modal-content-viewer-extraction"
phase: 3
phase_name: "Extract Content Pane Surfaces and Adapterize Data Paths"
prd_ref: "/docs/project_plans/PRDs/refactors/artifact-modal-content-viewer-extraction-v1.md"
plan_ref: "/docs/project_plans/implementation_plans/refactors/artifact-modal-content-viewer-extraction-v1.md"

status: "planning"
overall_progress: 0
completion_estimate: "on-track"
created: "2026-03-13"
updated: "2026-03-13"
started: "2026-03-13"
completed: null

tasks:
  - id: EXT-301
    description: "ContentPane extraction — extract the top-level ContentPane component and its direct children into the package; verify exported types and props surface"
    status: "pending"
    story_points: 3
    assigned_to: "ui-engineer-enhanced"
    dependencies: ["EXT-204"]

  - id: EXT-302
    description: "SplitPreview and MarkdownEditor extraction — extract SplitPreview and MarkdownEditor surfaces into the package on top of the extracted ContentPane"
    status: "pending"
    story_points: 2
    assigned_to: "ui-engineer-enhanced"
    dependencies: ["EXT-301"]

  - id: EXT-303
    description: "Hook adapter abstraction — introduce adapter interfaces so consumers can inject their own data-fetching hooks without coupling to SkillMeat's API layer"
    status: "pending"
    story_points: 2
    assigned_to: "frontend-developer"
    dependencies: ["EXT-301"]

  - id: EXT-304
    description: "Performance guardrails — add bundle-size and render-count assertions to CI; verify the extracted package does not regress on Core Web Vitals indicators"
    status: "pending"
    story_points: 1
    assigned_to: "react-performance-optimizer"
    dependencies: ["EXT-302"]

parallelization:
  batch_1:
    - EXT-301
  batch_2:
    - EXT-302
    - EXT-303
  batch_3:
    - EXT-304

success_criteria:
  - "Content pane component stack is exported and fully typed from the package"
  - "Adapter abstraction verified — no direct SkillMeat hook imports in extracted code"
  - "Performance guardrails pass in CI"

total_story_points: 8
completed_story_points: 0
---

## Phase Objective

Extract the full content pane surface (ContentPane, SplitPreview, MarkdownEditor) and introduce the adapter pattern that decouples data-fetching from the extracted components.

## Implementation Notes

<!-- Agent notes go here during execution. -->

## Completion Notes

<!-- Filled in when phase is marked complete. -->
