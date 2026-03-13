---
type: progress
schema_version: 2
doc_type: progress
prd: "artifact-modal-content-viewer-extraction-v1"
feature_slug: "artifact-modal-content-viewer-extraction"
phase: 2
phase_name: "Extract Generic Utilities, Types, and Tree Components"
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
  - id: EXT-201
    description: "Utility extraction — move generic utility functions (formatting, parsing, tree helpers) into the package with no SkillMeat-specific imports"
    status: "pending"
    story_points: 2
    assigned_to: "frontend-developer"
    dependencies: ["PKG-103"]

  - id: EXT-202
    description: "FileTree extraction — extract the FileTree component and all sub-components into the package; ensure it compiles and is tested independently"
    status: "pending"
    story_points: 3
    assigned_to: "ui-engineer-enhanced"
    dependencies: ["EXT-201"]

  - id: EXT-203
    description: "FrontmatterDisplay extraction — extract the FrontmatterDisplay component into the package with no SkillMeat-specific imports"
    status: "pending"
    story_points: 1
    assigned_to: "ui-engineer-enhanced"
    dependencies: ["EXT-201"]

  - id: EXT-204
    description: "Shared type exports — consolidate and export all shared TypeScript types/interfaces used across the extracted components through the public API"
    status: "pending"
    story_points: 1
    assigned_to: "frontend-developer"
    dependencies: ["EXT-201"]

parallelization:
  batch_1:
    - EXT-201
  batch_2:
    - EXT-202
    - EXT-203
    - EXT-204

success_criteria:
  - "All extracted utilities and components compile and pass tests from the package"
  - "No SkillMeat-specific imports remain in the extracted modules"

total_story_points: 7
completed_story_points: 0
---

## Phase Objective

Extract the generic utilities, shared types, FileTree, and FrontmatterDisplay into the new package with clean boundaries and no app-specific dependencies.

## Implementation Notes

<!-- Agent notes go here during execution. -->

## Completion Notes

<!-- Filled in when phase is marked complete. -->
