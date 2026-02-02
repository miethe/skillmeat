---
# === TOOLS API SUPPORT - PHASE 1 PROGRESS ===
# Schema & Data Model implementation

type: progress
prd: "tools-api-support"
phase: 1
title: "Schema & Data Model"
status: "planning"
started: "2026-02-02"
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer", "data-layer-expert"]
contributors: []

tasks:
  - id: "TOOLS-1.1"
    description: "Add tools field to ArtifactSummary in user_collections.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "0.5h"
    priority: "high"

  - id: "TOOLS-1.2"
    description: "Add tools field to ArtifactSummary in collections.py"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "0.5h"
    priority: "high"

  - id: "TOOLS-1.3"
    description: "Add tools_json column to CollectionArtifact model"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"

  - id: "TOOLS-1.4"
    description: "Create Alembic migration for collection_artifacts.tools_json"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TOOLS-1.3"]
    estimated_effort: "1h"
    priority: "high"

  - id: "TOOLS-1.5"
    description: "Add tools property to CollectionArtifact for JSON parsing"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TOOLS-1.3"]
    estimated_effort: "0.5h"
    priority: "medium"

parallelization:
  batch_1: ["TOOLS-1.1", "TOOLS-1.2", "TOOLS-1.3"]
  batch_2: ["TOOLS-1.4", "TOOLS-1.5"]
  critical_path: ["TOOLS-1.3", "TOOLS-1.4"]
  estimated_total_time: "2.5h"

blockers: []

success_criteria:
  - { id: "SC-1", description: "ArtifactSummary schemas include tools field", status: "pending" }
  - { id: "SC-2", description: "CollectionArtifact model has tools_json column", status: "pending" }
  - { id: "SC-3", description: "Migration runs cleanly on dev database", status: "pending" }
  - { id: "SC-4", description: "No breaking changes to existing API responses", status: "pending" }

files_modified:
  - "skillmeat/api/schemas/user_collections.py"
  - "skillmeat/api/schemas/collections.py"
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/migrations/versions/"
---

# tools-api-support - Phase 1: Schema & Data Model

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/tools-api-support/phase-1-progress.md -t TOOLS-1.1 -s completed
```

---

## Objective

Add `tools` field to API schemas and `tools_json` column to the database cache model, enabling tools data to be stored and returned in collection API responses.

---

## Quick Reference

### Orchestration Commands

```python
# Execute batch_1 (parallel)
Task("python-backend-engineer", """
TOOLS-1.1: Add tools field to ArtifactSummary in user_collections.py
File: skillmeat/api/schemas/user_collections.py
Add: tools: Optional[List[str]] = Field(default=None, description="Claude Code tools used")
After: tags field in ArtifactSummary class
""", model="sonnet")

Task("python-backend-engineer", """
TOOLS-1.2: Add tools field to ArtifactSummary in collections.py
File: skillmeat/api/schemas/collections.py
Add: tools: Optional[List[str]] = Field(default=None, description="Claude Code tools used")
""", model="sonnet")

Task("data-layer-expert", """
TOOLS-1.3: Add tools_json column to CollectionArtifact model
File: skillmeat/cache/models.py
Find: class CollectionArtifact
Add after tags_json: tools_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
Pattern: Same as tags_json column
""", model="sonnet")

# After batch_1 completes, execute batch_2
Task("data-layer-expert", """
TOOLS-1.4: Create Alembic migration for collection_artifacts.tools_json
Create: skillmeat/cache/migrations/versions/[timestamp]_add_tools_to_collection_artifacts.py
Pattern: Copy from 20260122_1100_add_tools_and_linked_artifacts.py
Add: tools_json TEXT column to collection_artifacts table
Add: Index on tools_json for filtering
""", model="sonnet")

Task("python-backend-engineer", """
TOOLS-1.5: Add tools property to CollectionArtifact for JSON parsing
File: skillmeat/cache/models.py
Add property after tools_json column:
@property
def tools(self) -> list[str]:
    if self.tools_json:
        return json.loads(self.tools_json)
    return []
""", model="sonnet")
```

---

## Implementation Notes

### Architectural Decisions

- **JSON column over relational**: Tools stored as JSON array in `tools_json` column (consistent with `tags_json` pattern)
- **Nullable column**: No default value required, existing rows will have NULL
- **Property accessor**: `tools` property parses JSON for convenient access

### Patterns and Best Practices

**Existing pattern** (from CollectionArtifact line 933):
```python
tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

**Migration pattern** (from 20260122_1100):
```python
op.add_column('collection_artifacts', sa.Column('tools_json', sa.Text(), nullable=True))
op.create_index('ix_collection_artifacts_tools', 'collection_artifacts', ['tools_json'])
```

### Known Gotchas

- Tool values must be PascalCase to match `Tool` enum (e.g., "Bash", "Read", not "bash", "read")
- Don't forget to import `List` from typing in schema files
- JSON parsing should handle malformed JSON gracefully

---

## Completion Notes

(Fill in when phase is complete)
