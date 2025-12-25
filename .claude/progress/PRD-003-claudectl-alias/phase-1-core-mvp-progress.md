---
type: progress
prd: "PRD-003-claudectl-alias"
phase: 1
phase_title: "Core MVP"
status: completed
progress: 100
total_tasks: 11
completed_tasks: 11
estimated_effort: "2 weeks"
story_points: 20

tasks:
  - id: "P1-T1"
    title: "Smart Defaults Module"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    story_points: 5

  - id: "P1-T2"
    title: "CLI Flag Implementation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T1"]
    story_points: 3

  - id: "P1-T3"
    title: "Add Command Integration"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T2"]
    story_points: 4

  - id: "P1-T4"
    title: "Deploy Command Integration"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T2"]
    story_points: 4

  - id: "P1-T5"
    title: "Remove & Undeploy Commands"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T2"]
    story_points: 3

  - id: "P1-T6"
    title: "Wrapper Script Creation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    story_points: 2

  - id: "P1-T7"
    title: "Bash Completion"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T3", "P1-T4"]
    story_points: 4

  - id: "P1-T8"
    title: "Installation Command"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T6", "P1-T7"]
    story_points: 4

  - id: "P1-T9"
    title: "Unit Tests (Defaults)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T1"]
    story_points: 3

  - id: "P1-T10"
    title: "Integration Tests (Workflows)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T3", "P1-T4", "P1-T5"]
    story_points: 4

  - id: "P1-T11"
    title: "Exit Code Validation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-T3", "P1-T4", "P1-T5"]
    story_points: 2

parallelization:
  batch_1: ["P1-T1", "P1-T6"]
  batch_2: ["P1-T2", "P1-T9"]
  batch_3: ["P1-T3", "P1-T4", "P1-T5"]
  batch_4: ["P1-T7", "P1-T10", "P1-T11"]
  batch_5: ["P1-T8"]
---

# Phase 1: Core MVP

## Orchestration Quick Reference

**Batch 1** (Parallel startup):
- P1-T1 (5pts) → `python-backend-engineer` - SmartDefaults module
- P1-T6 (2pts) → `python-backend-engineer` - Wrapper script

**Batch 2** (After SmartDefaults):
- P1-T2 (3pts) → `python-backend-engineer` - CLI flag
- P1-T9 (3pts) → `python-backend-engineer` - Unit tests

**Batch 3** (Parallel commands):
- P1-T3 (4pts) → `python-backend-engineer` - Add command
- P1-T4 (4pts) → `python-backend-engineer` - Deploy command
- P1-T5 (3pts) → `python-backend-engineer` - Remove/Undeploy

**Batch 4** (Parallel validation):
- P1-T7 (4pts) → `python-backend-engineer` - Bash completion
- P1-T10 (4pts) → `python-backend-engineer` - Integration tests
- P1-T11 (2pts) → `python-backend-engineer` - Exit codes

**Batch 5** (Final):
- P1-T8 (4pts) → `python-backend-engineer` - Install command

### Task Delegation Commands

Task("python-backend-engineer", "P1-T1: Create SmartDefaults module.
File: skillmeat/defaults.py (~200 LOC)
Methods: detect_output_format (TTY/pipe), detect_artifact_type,
get_default_project, get_default_collection, apply_defaults
Acceptance: >85% test coverage")

Task("python-backend-engineer", "P1-T6: Create wrapper script.
File: ~/.local/bin/claudectl (template)
Content: exec skillmeat --smart-defaults \"$@\"
Acceptance: Executable, forwards all args")

Task("python-backend-engineer", "P1-T2: Add --smart-defaults CLI flag.
File: skillmeat/cli/main.py
Flag sets ctx.obj['smart_defaults'] = True
Acceptance: Flag in help, doesn't break existing CLI")

Task("python-backend-engineer", "P1-T9: Unit tests for SmartDefaults.
File: tests/test_defaults.py
Test: TTY detection, type inference, format detection, apply_defaults")

Task("python-backend-engineer", "P1-T3: Wire SmartDefaults into add command.
Command works with minimal args: claudectl add pdf
Acceptance: Auto-selects type, valid JSON/table output")

Task("python-backend-engineer", "P1-T4: Wire SmartDefaults into deploy.
Command: claudectl deploy pdf
Acceptance: Auto-detects project, creates .claude structure")

Task("python-backend-engineer", "P1-T5: Wire SmartDefaults into remove/undeploy.
Commands require --force for scripts, confirm for TTY.
Acceptance: Correct exit codes (0, 1, 3, 4)")

Task("python-backend-engineer", "P1-T7: Create bash completion.
File: bash/claudectl-completion.bash
Complete: commands, artifact names via claudectl list --json")

Task("python-backend-engineer", "P1-T10: Integration tests.
Test: add->deploy workflow, search->add->deploy workflow
Verify: add works, deploy works, status shows deployed")

Task("python-backend-engineer", "P1-T11: Exit code validation.
Codes: 0=success, 1=error, 2=invalid usage, 3=not found, 4=conflict
Acceptance: All commands exit correctly, documented")

Task("python-backend-engineer", "P1-T8: Installation command.
File: skillmeat/cli/commands/alias.py
Commands: skillmeat alias install, skillmeat alias uninstall
Acceptance: Creates wrapper + completion files")

## Quality Gates

- [ ] All 11 tasks completed and reviewed
- [ ] Smart defaults don't break existing CLI
- [ ] JSON output validates with jq
- [ ] Exit codes consistent
- [ ] Bash completion functional
- [ ] Unit test coverage >85%
- [ ] Integration tests passing

## Notes

[Session notes will be added here]
