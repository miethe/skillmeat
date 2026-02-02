---
# === TOOLS API SUPPORT - PHASE 2 PROGRESS ===
# Cache Population & API Wiring

type: progress
prd: "tools-api-support"
phase: 2
title: "Cache Population & API Wiring"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer", "backend-architect"]
contributors: []

tasks:
  - id: "TOOLS-2.1"
    description: "Extract tools from frontmatter in markdown parser"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"

  - id: "TOOLS-2.2"
    description: "Populate tools_json in cache sync/refresh logic"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: ["TOOLS-2.1"]
    estimated_effort: "1.5h"
    priority: "high"

  - id: "TOOLS-2.3"
    description: "Wire tools to /user-collections/{id}/artifacts endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TOOLS-2.2"]
    estimated_effort: "0.5h"
    priority: "high"

  - id: "TOOLS-2.4"
    description: "Wire tools to /artifacts endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TOOLS-2.2"]
    estimated_effort: "0.5h"
    priority: "high"

  - id: "TOOLS-2.5"
    description: "Add unit tests for tools extraction, caching, and API responses"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TOOLS-2.3", "TOOLS-2.4"]
    estimated_effort: "1h"
    priority: "medium"

parallelization:
  batch_1: ["TOOLS-2.1"]
  batch_2: ["TOOLS-2.2"]
  batch_3: ["TOOLS-2.3", "TOOLS-2.4"]
  batch_4: ["TOOLS-2.5"]
  critical_path: ["TOOLS-2.1", "TOOLS-2.2", "TOOLS-2.3", "TOOLS-2.5"]
  estimated_total_time: "3.5h"

blockers:
  - id: "BLOCKER-P2-001"
    title: "Phase 1 must complete first"
    severity: "high"
    blocking: ["TOOLS-2.2", "TOOLS-2.3", "TOOLS-2.4"]
    resolution: "Complete Phase 1 (schema & model updates)"
    created: "2026-02-02"

success_criteria:
  - { id: "SC-1", description: "Tools extracted from SKILL.md frontmatter", status: "pending" }
  - { id: "SC-2", description: "Cache populated with tools_json on artifact sync", status: "pending" }
  - { id: "SC-3", description: "tools field appears in user-collections endpoint", status: "pending" }
  - { id: "SC-4", description: "tools field appears in artifacts endpoint", status: "pending" }
  - { id: "SC-5", description: "Unit tests achieve >80% coverage", status: "pending" }

files_modified:
  - "skillmeat/core/parsers/markdown_parser.py"
  - "skillmeat/cache/ (sync logic TBD)"
  - "skillmeat/api/routers/ (endpoint wiring TBD)"
  - "tests/"
---

# tools-api-support - Phase 2: Cache Population & API Wiring

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/tools-api-support/phase-2-progress.md -t TOOLS-2.1 -s completed
```

---

## Objective

Populate `tools_json` during cache sync from artifact frontmatter and wire the `tools` field into API responses for both `/user-collections/{id}/artifacts` and `/artifacts` endpoints.

---

## Quick Reference

### Orchestration Commands

```python
# TOOLS-2.1: Frontmatter extraction
Task("python-backend-engineer", """
TOOLS-2.1: Extract tools from frontmatter in markdown parser
File: skillmeat/core/parsers/markdown_parser.py

Update extract_metadata() function to include tools:
- Look for 'tools' key in frontmatter
- Return as List[str] (empty list if not present)
- Validate against Tool enum values (optional normalization)

Pattern to follow (existing in same file):
def extract_metadata(content: str) -> dict[str, Any]:
    result = parse_markdown_with_frontmatter(content)
    frontmatter = result.frontmatter or {}
    return {
        "tools": frontmatter.get("tools", []),  # Add this line
        # ... existing fields
    }
""")

# TOOLS-2.2: Cache population (needs exploration first)
Task("codebase-explorer", """
Find the cache population/sync logic for CollectionArtifact:
1. Where is CollectionArtifact created/updated?
2. Where does it get metadata from frontmatter?
3. What function populates fields like tags_json?

Search terms: "CollectionArtifact", "populate", "sync", "refresh", "tags_json"
Files to check: skillmeat/cache/, skillmeat/sources/, skillmeat/core/
""", model="haiku")

# After exploration, implement:
Task("backend-architect", """
TOOLS-2.2: Populate tools_json in cache sync
Based on exploration findings, update cache population to:
1. Extract tools from artifact metadata
2. JSON serialize to tools_json column
3. Handle both new artifacts and refresh/update paths

Pattern: Follow how tags_json is populated
""")

# TOOLS-2.3 & 2.4: API wiring (parallel after 2.2)
Task("python-backend-engineer", """
TOOLS-2.3: Wire tools to /user-collections/{id}/artifacts endpoint
File: Find the router/service that builds ArtifactSummary response

Add tools field:
- From cache: artifact.tools (uses property from Phase 1)
- From fallback: metadata.get("tools", [])
""", model="sonnet")

Task("python-backend-engineer", """
TOOLS-2.4: Wire tools to /artifacts endpoint
Same pattern as TOOLS-2.3, ensure consistency
""", model="sonnet")

# TOOLS-2.5: Tests
Task("python-backend-engineer", """
TOOLS-2.5: Add unit tests for tools functionality
Create/update test files:
1. tests/test_parsers.py - test tools extraction from frontmatter
2. tests/test_cache.py - test tools_json population
3. tests/test_api_*.py - test tools in API responses

Test cases:
- Artifact with tools in frontmatter
- Artifact without tools (should return empty list)
- Invalid/malformed tools (graceful handling)
- API response includes tools field
""", model="sonnet")
```

---

## Implementation Notes

### Discovery Required

Before implementing TOOLS-2.2, need to explore:
1. **Cache population location**: Where does CollectionArtifact get populated?
2. **Metadata source**: How does frontmatter metadata flow to cache?
3. **Refresh pattern**: How are existing artifacts updated?

### Patterns and Best Practices

**Frontmatter extraction** (existing pattern in markdown_parser.py):
```python
"version": frontmatter.get("version"),
"tags": frontmatter.get("tags", []),
# Add similar for tools
"tools": frontmatter.get("tools", []),
```

**JSON serialization** (for cache population):
```python
import json
artifact.tools_json = json.dumps(tools) if tools else None
```

### Known Gotchas

- Frontmatter `tools` may be missing, empty, or a string (should be list)
- Cache refresh must update tools_json, not just initial population
- API response mapping may differ between cache-hit and fallback paths
- Test fixtures need sample SKILL.md with tools frontmatter

### Sample Frontmatter

```yaml
---
name: "example-skill"
description: "Example skill"
tools:
  - Bash
  - Read
  - Write
  - Edit
---
```

---

## Completion Notes

(Fill in when phase is complete)
