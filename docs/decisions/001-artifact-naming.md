# Decision: Artifact Naming Strategy

**Status**: Approved
**Date**: 2025-11-07
**Decider**: Implementation Team

## Context

The PRD leaves open whether artifact names must be unique across the entire collection or can be duplicated if they have different types (e.g., a "review" command and a "review" skill).

## Decision

**ALLOW duplicate names across different artifact types.**

Artifacts are uniquely identified by the composite key `(name, type)` rather than name alone.

## Rationale

1. **Natural Mental Model**: "review" is a concept that can manifest in different forms (command, skill, agent)
2. **Deployment Separation**: Files naturally separate by directory:
   - `.claude/commands/review.md`
   - `.claude/skills/review/`
   - `.claude/agents/review.md`
3. **User Flexibility**: Users can use semantic naming without artificial uniqueness constraints
4. **Type-Based Grouping**: CLI already groups by type in `list` command, making this clear

## Implementation Impact

- **Data Model**: `Artifact` uses composite key `(name, type)` for uniqueness
- **CLI Syntax**: Support both:
  - `skillmeat show review` (if unique)
  - `skillmeat show command/review` (if ambiguous or explicit)
  - `--type` flag: `skillmeat show review --type command`
- **Storage**: Collection manifest stores artifacts with type field for disambiguation
- **Validation**: Check for duplicate `(name, type)` combinations, not just names

## Examples

```python
# ALLOWED:
collection.artifacts = [
    Artifact(name="review", type="command"),
    Artifact(name="review", type="skill"),
    Artifact(name="review", type="agent")
]

# NOT ALLOWED (duplicate composite key):
collection.artifacts = [
    Artifact(name="review", type="command"),
    Artifact(name="review", type="command")  # ERROR
]
```

## Alternatives Considered

**Option 1: Unique names across all types** (PRD leaning)
- Rejected: Too restrictive, forces artificial naming like "review-command", "review-skill"

**Option 2: Namespace prefixing** (e.g., "command:review")
- Rejected: Redundant with type field, ugly in deployment paths
