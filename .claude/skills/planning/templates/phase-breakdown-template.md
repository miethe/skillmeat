---
title: "Phase [N]: [Phase Name]" # Human-readable phase plan title
schema_version: 2 # CCDash frontmatter schema version
doc_type: phase_plan # Must remain `phase_plan`
status: draft # draft|planning|in-progress|review|completed|blocked
created: YYYY-MM-DD # Initial creation date (YYYY-MM-DD)
updated: YYYY-MM-DD # Last edit date (YYYY-MM-DD)
feature_slug: "feature-name" # Kebab-case feature identifier
feature_version: "v1" # Version label for this feature document set
phase: [N] # Numeric phase identifier (integer)
phase_title: "[Phase Name]" # Short phase name for dashboards
prd_ref: /docs/project_plans/PRDs/category/feature-name-v1.md # Parent PRD path
plan_ref: /docs/project_plans/implementation_plans/category/feature-name-v1.md # Parent implementation plan path
entry_criteria: [] # Preconditions required to start this phase
exit_criteria: [] # Conditions that define phase completion
related_documents: [] # Related docs (phase siblings, ADRs, specs)
owner: null # Single accountable owner (name or agent)
contributors: [] # Supporting contributors
priority: medium # low|medium|high|critical
risk_level: medium # low|medium|high|critical
category: "product-planning" # Planning taxonomy label
tags: [phase-plan, implementation] # Search/filter tags
milestone: null # Optional release/milestone marker
commit_refs: [] # Commit SHAs added during implementation
pr_refs: [] # Pull request refs (e.g., #123)
files_affected: [] # Key files expected to change
---

# Phase [N]: [Phase Name]

**Parent Plan**: [Link to parent implementation plan]
**Duration**: [X] days
**Effort**: [X] story points
**Dependencies**: [Phase N-1 complete | None]
**Team Members**: [Developer roles needed]

---

## Phase Overview

[Brief description of what this phase accomplishes and why it's needed]

### Goals

- [Goal 1]
- [Goal 2]
- [Goal 3]

### Architecture Focus

This phase implements the [layer name] following MeatyPrompts architecture:
- **Layer**: [Database | Repository | Service | API | UI | Testing | Documentation | Deployment]
- **Patterns**: [Specific patterns used]
- **Standards**: [Relevant standards]

---

## Task Breakdown

### Epic: [Epic Name]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|--------------|
| [ID-001] | [Task Name] | [Description] | [Criteria] | [X] pts | [subagent-1, subagent-2] | [None or ID] |
| [ID-002] | [Task Name] | [Description] | [Criteria] | [X] pts | [subagent-1] | [ID-001] |
| [ID-003] | [Task Name] | [Description] | [Criteria] | [X] pts | [subagent-1] | [ID-001] |

---

## Detailed Task Specifications

### Task [ID-001]: [Task Name]

**Estimate**: [X] points
**Assigned Subagent(s)**: [subagent-1, subagent-2]
**Dependencies**: [None or other task IDs]

**Description**:
[Detailed description of what needs to be done]

**Acceptance Criteria**:
- [ ] [Criterion 1 with specific, measurable outcome]
- [ ] [Criterion 2 with specific, measurable outcome]
- [ ] [Criterion 3 with specific, measurable outcome]

**Implementation Notes**:
- [Note 1: Technical approach or pattern to use]
- [Note 2: Files to modify or create]
- [Note 3: Integration points to consider]

**Files Involved**:
- `path/to/file1.py` - [What changes are needed]
- `path/to/file2.tsx` - [What changes are needed]

---

### Task [ID-002]: [Task Name]

**Estimate**: [X] points
**Assigned Subagent(s)**: [subagent-1]
**Dependencies**: [ID-001]

**Description**:
[Detailed description]

**Acceptance Criteria**:
- [ ] [Criterion 1]
- [ ] [Criterion 2]

**Implementation Notes**:
- [Note 1]

**Files Involved**:
- `path/to/file.py` - [Changes needed]

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: [All features working as specified]
- [ ] **Testing**: [Required test coverage achieved]
- [ ] **Performance**: [Performance benchmarks met]
- [ ] **Security**: [Security requirements met]
- [ ] **Documentation**: [Documentation complete]
- [ ] **Code Quality**: [Linting and quality checks pass]
- [ ] **Architecture**: [Follows MeatyPrompts patterns]

---

## Integration Points

### External Systems

- **System 1**: [How this phase integrates]
- **System 2**: [How this phase integrates]

### Internal Systems

- **Component 1**: [Integration details]
- **Component 2**: [Integration details]

---

## Key Files Modified

| File Path | Lines | Purpose | Subagent |
|-----------|-------|---------|----------|
| `path/to/file1.py` | 100-150 | [Purpose] | [subagent-1] |
| `path/to/file2.tsx` | 50-80 | [Purpose] | [subagent-2] |
| `path/to/file3.sql` | - | [Purpose] | [subagent-1] |

---

## Testing Strategy

### Unit Tests

- [What unit tests are needed]
- [Coverage targets]

### Integration Tests

- [What integration tests are needed]
- [What scenarios to cover]

### E2E Tests (if applicable)

- [What E2E tests are needed]
- [What user journeys to cover]

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| [Risk 1] | [High/Med/Low] | [How to mitigate] |
| [Risk 2] | [High/Med/Low] | [How to mitigate] |

---

## Success Metrics

- **Completion**: All tasks checked off
- **Quality**: All quality gates passed
- **Performance**: [Specific performance targets]
- **Testing**: [Coverage and passing tests]

---

## Notes

### Implementation Approach

[Notes about the overall approach for this phase]

### Gotchas

- [Gotcha 1]: [What to watch out for]
- [Gotcha 2]: [What to watch out for]

### Learnings

[Capture learnings as phase progresses]

---

**Phase Version**: 1.0
**Last Updated**: YYYY-MM-DD

[Return to Parent Plan](../[feature-name]-v1.md)
