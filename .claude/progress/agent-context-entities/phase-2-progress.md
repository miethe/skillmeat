---
type: progress
prd: "agent-context-entities"
phase: 2
phase_title: "CLI Management"
status: pending
progress: 0
total_tasks: 8
completed_tasks: 0
created: "2025-12-14"
updated: "2025-12-14"

tasks:
  - id: "TASK-2.1"
    name: "Create Context Command Group"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: 2

  - id: "TASK-2.2"
    name: "Implement Context Add Command"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimate: 3

  - id: "TASK-2.3"
    name: "Implement Context List Command"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimate: 2

  - id: "TASK-2.4"
    name: "Implement Context Show Command"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimate: 2

  - id: "TASK-2.5"
    name: "Implement Context Deploy Command"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimate: 3

  - id: "TASK-2.6"
    name: "Implement Context Remove Command"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
    estimate: 1

  - id: "TASK-2.7"
    name: "CLI Help Documentation"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-2.2", "TASK-2.3", "TASK-2.4", "TASK-2.5", "TASK-2.6"]
    estimate: 1

  - id: "TASK-2.8"
    name: "Integration Testing for CLI"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.2", "TASK-2.3", "TASK-2.4", "TASK-2.5", "TASK-2.6"]
    estimate: 2

parallelization:
  batch_1: ["TASK-2.1"]
  batch_2: ["TASK-2.2", "TASK-2.3", "TASK-2.4", "TASK-2.6"]
  batch_3: ["TASK-2.5"]
  batch_4: ["TASK-2.7", "TASK-2.8"]
---

# Phase 2: CLI Management

## Orchestration Quick Reference

**Batch 1** (Sequential):
- TASK-2.1 → `python-backend-engineer` (2h)

**Batch 2** (Parallel):
- TASK-2.2 → `python-backend-engineer` (3h)
- TASK-2.3 → `python-backend-engineer` (2h)
- TASK-2.4 → `python-backend-engineer` (2h)
- TASK-2.6 → `python-backend-engineer` (1h)

**Batch 3** (Sequential - Security Review):
- TASK-2.5 → `python-backend-engineer` (3h)

**Batch 4** (Parallel):
- TASK-2.7 → `documentation-writer` (1h)
- TASK-2.8 → `python-backend-engineer` (2h)

### Task Delegation Commands

**Batch 1**:
```python
Task("python-backend-engineer", "TASK-2.1: Create context command group structure. File: skillmeat/cli.py. Add 'skillmeat context' group with subcommands for add, list, show, remove, deploy. Include help text describing context entity types.")
```

**Batch 2**:
```python
Task("python-backend-engineer", "TASK-2.2: Implement 'skillmeat context add' command. Support local files and GitHub URLs. Auto-detect entity type from path. Validate content and call API to create entity.")

Task("python-backend-engineer", "TASK-2.3: Implement 'skillmeat context list' command with filters (type, category, auto-load). Use Rich table format. Support JSON/YAML output.")

Task("python-backend-engineer", "TASK-2.4: Implement 'skillmeat context show' command. Display metadata and content preview (first 20 lines). Support --full flag for complete content. Use Rich panels.")

Task("python-backend-engineer", "TASK-2.6: Implement 'skillmeat context remove' command with confirmation prompt. Warn user about deployed files. Support --force flag.")
```

**Batch 3**:
```python
Task("python-backend-engineer", "TASK-2.5: Implement 'skillmeat context deploy' command with SECURITY REVIEW. Validate deployment path prevents traversal (no .., must be in .claude/). Support --dry-run. Create directories if needed. Test path traversal prevention thoroughly.")
```

**Batch 4**:
```python
Task("documentation-writer", "TASK-2.7: Write complete help text for all context CLI commands. Include examples (2-3 per command), common errors, usage patterns. Follow Click conventions.")

Task("python-backend-engineer", "TASK-2.8: Create integration tests for CLI commands. File: tests/integration/test_context_cli.py. Test add, list, show, deploy, remove. Include path traversal security test. Use Click testing utilities.")
```

## Quality Gates

- [ ] All commands execute without errors
- [ ] Help text is clear and complete
- [ ] Can add entity from local file
- [ ] Can add entity from GitHub URL
- [ ] Can deploy entity to project
- [ ] Path traversal security tests pass
- [ ] Integration tests cover all commands
- [ ] Error messages are user-friendly
- [ ] CLI follows SkillMeat conventions

## Notes

_Session notes go here_
