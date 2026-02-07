---
type: quick-feature
status: in_progress
created: 2026-02-07
---

# Quick Feature: PRD/Plan Status Manager

**Goal**: Extend artifact-tracking skill with status management for PRD and implementation plan files.

**Scope**: Single script addition + documentation updates

## Requirements

1. Create `manage-plan-status.py` script supporting:
   - Read status from PRD/plan frontmatter
   - Update status field in frontmatter
   - Query plans by status across directories
   - Support statuses: draft, approved, in-progress, completed, superseded

2. Update artifact-tracking SKILL.md:
   - Add brief capability description
   - Link to new detailed doc

3. Create `./plan-status-management.md` in artifact-tracking:
   - Script usage examples
   - Status workflow guidance
   - Directory patterns

4. Update CLAUDE.md:
   - Add plan status management to Orchestration-Driven Development section

5. Update planning/dev-execution skills:
   - Add script to workflow guidance

## Affected Files

- NEW: `.claude/skills/artifact-tracking/scripts/manage-plan-status.py`
- NEW: `.claude/skills/artifact-tracking/plan-status-management.md`
- EDIT: `.claude/skills/artifact-tracking/SKILL.md`
- EDIT: `CLAUDE.md`
- EDIT: `.claude/skills/planning/SKILL.md`
- EDIT: `.claude/skills/dev-execution/SKILL.md`

## Implementation

Delegate to python-backend-engineer for script creation, documentation-writer for docs.

## Validation

```bash
# Test read
python .claude/skills/artifact-tracking/scripts/manage-plan-status.py \
  --read docs/project_plans/PRDs/features/workflow-orchestration-v1.md

# Test update
python .claude/skills/artifact-tracking/scripts/manage-plan-status.py \
  --file docs/project_plans/implementation_plans/features/workflow-orchestration-v1.md \
  --status completed

# Test query
python .claude/skills/artifact-tracking/scripts/manage-plan-status.py \
  --query --status draft --type prd
```

## Completion

All tasks completed:
- ✅ Script created: `manage-plan-status.py` (read, update, query operations)
- ✅ Documentation created: `plan-status-management.md`
- ✅ SKILL.md updated with new capability
- ✅ CLAUDE.md updated in Orchestration section
- ✅ planning skill updated with status tracking
- ✅ dev-execution skill updated with common patterns
- ✅ Validation: All operations tested successfully

Status: Completed
