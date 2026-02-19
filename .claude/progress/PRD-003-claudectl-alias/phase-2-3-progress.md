---
type: progress
prd: PRD-003-claudectl-alias
phase: 2-3
phase_title: Management Commands & Polish
status: completed
progress: 100
total_tasks: 14
completed_tasks: 14
estimated_effort: 2 weeks
story_points: 28
dependencies:
- phase: 1
  status: must_complete
tasks:
- id: P2-T1
  title: Search Command Enhancement
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  story_points: 3
  phase: 2
- id: P2-T2
  title: Sync & Update Commands
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  story_points: 3
  phase: 2
- id: P2-T3
  title: Diff Command
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  story_points: 2
  phase: 2
- id: P2-T4
  title: Bundle Commands
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  story_points: 3
  phase: 2
- id: P2-T5
  title: Config Management
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  story_points: 2
  phase: 2
- id: P2-T6
  title: Zsh Completion
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T1
  - P2-T2
  - P2-T3
  story_points: 3
  phase: 2
- id: P2-T7
  title: Fish Completion
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T1
  - P2-T2
  - P2-T3
  story_points: 2
  phase: 2
- id: P2-T8
  title: Quick Start Guide
  status: pending
  assigned_to:
  - documentation-writer
  dependencies: []
  story_points: 2
  phase: 2
- id: P3-T1
  title: Full User Guide
  status: pending
  assigned_to:
  - documentation-writer
  dependencies: []
  story_points: 3
  phase: 3
- id: P3-T2
  title: Scripting Examples
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - P2-T4
  story_points: 2
  phase: 3
- id: P3-T3
  title: Man Page
  status: pending
  assigned_to:
  - documentation-writer
  dependencies: []
  story_points: 2
  phase: 3
- id: P3-T4
  title: Confidence Score Integration
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T1
  story_points: 2
  phase: 3
  note: Depends on PRD-001 completion
- id: P3-T5
  title: Shell Compatibility Tests
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-T6
  - P2-T7
  story_points: 2
  phase: 3
- id: P3-T6
  title: Final Integration Tests
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  story_points: 1
  phase: 3
parallelization:
  batch_1:
  - P2-T1
  - P2-T2
  - P2-T3
  - P2-T4
  - P2-T5
  batch_2:
  - P2-T6
  - P2-T7
  - P2-T8
  batch_3:
  - P3-T1
  - P3-T3
  batch_4:
  - P3-T2
  - P3-T4
  - P3-T5
  batch_5:
  - P3-T6
schema_version: 2
doc_type: progress
feature_slug: prd-003-claudectl-alias
---

# Phases 2-3: Management Commands & Polish

## Phase 2: Management Commands (16 pts)

### Orchestration Quick Reference

**Batch 1** (All parallel):
- P2-T1 (3pts) → `python-backend-engineer` - Search enhancement
- P2-T2 (3pts) → `python-backend-engineer` - Sync/Update
- P2-T3 (2pts) → `python-backend-engineer` - Diff
- P2-T4 (3pts) → `python-backend-engineer` - Bundles
- P2-T5 (2pts) → `python-backend-engineer` - Config

**Batch 2** (After commands):
- P2-T6 (3pts) → `python-backend-engineer` - Zsh completion
- P2-T7 (2pts) → `python-backend-engineer` - Fish completion
- P2-T8 (2pts) → `documentation-writer` - Quick start

### Task Delegation Commands

Task("python-backend-engineer", "P2-T1: Search command enhancement.
Add PRD-001 confidence scoring if available, fuzzy matching, ranking.
Acceptance: Ranked results, confidence optional")

Task("python-backend-engineer", "P2-T2: Sync & Update commands.
sync: upstream sync, update: version update.
Acceptance: --check-only preview mode works")

Task("python-backend-engineer", "P2-T3: Diff command.
Show upstream changes with --stat and --full modes.
Acceptance: Shows file changes, stat summary")

Task("python-backend-engineer", "P2-T4: Bundle commands.
bundle: create tarball, import: extract + validate.
Acceptance: Valid tar.gz, signature verification optional")

Task("python-backend-engineer", "P2-T5: Config management.
config: get/set preferences, collection: switch active.
Acceptance: Changes persisted")

Task("python-backend-engineer", "P2-T6: Zsh completion.
File: zsh/_claudectl
Acceptance: Completes all commands and artifacts")

Task("python-backend-engineer", "P2-T7: Fish completion.
File: fish/claudectl.fish
Acceptance: Completes commands and artifacts")

Task("documentation-writer", "P2-T8: Quick start guide.
File: .claude/docs/claudectl-quickstart.md
Cover: install, add, deploy, list, status, search")

## Phase 3: Polish & Integration (12 pts)

### Orchestration Quick Reference

**Batch 3** (Documentation):
- P3-T1 (3pts) → `documentation-writer` - Full guide
- P3-T3 (2pts) → `documentation-writer` - Man page

**Batch 4** (Integration):
- P3-T2 (2pts) → `documentation-writer` - Scripting examples
- P3-T4 (2pts) → `python-backend-engineer` - Confidence scoring
- P3-T5 (2pts) → `python-backend-engineer` - Shell tests

**Batch 5** (Final):
- P3-T6 (1pt) → `python-backend-engineer` - Final tests

### Task Delegation Commands

Task("documentation-writer", "P3-T1: Full user guide.
File: docs/claudectl-guide.md
Cover all 14 commands, examples, error handling, troubleshooting")

Task("documentation-writer", "P3-T3: Man page.
File: man/claudectl.1
Acceptance: Renders correctly with man claudectl")

Task("documentation-writer", "P3-T2: Scripting examples.
File: docs/claudectl-examples.sh
5+ CI/CD examples: deploy bundle, check status, jq parsing")

Task("python-backend-engineer", "P3-T4: Confidence score integration.
Wire PRD-001 scoring into search and show if available.
Add optional --scores flag")

Task("python-backend-engineer", "P3-T5: Shell compatibility tests.
Test on bash, zsh, fish.
Document version requirements and known issues")

Task("python-backend-engineer", "P3-T6: Final integration tests.
All 14 commands, output formats, error cases, exit codes.
Acceptance: Full test suite passing")

## Quality Gates

### Phase 2
- [ ] All 8 tasks completed
- [ ] Search respects confidence scoring
- [ ] Zsh and fish completion functional
- [ ] Quick start guide clear

### Phase 3
- [ ] All 14 commands documented
- [ ] Man page available
- [ ] Shell compatibility verified
- [ ] Ready for release

## Notes

[Session notes will be added here]
