---
title: 'Phase 1: Backend Extraction & Caching'
description: Database schema, frontmatter extraction, tools field, metadata auto-population
created: 2026-01-21
updated: 2026-01-21
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: enhanced-frontmatter-utilization
prd_ref: null
plan_ref: null
---
# Phase 1: Backend Extraction & Caching

**Duration**: 1.5 weeks
**Dependencies**: Phase 0 complete
**Assigned Subagent(s)**: data-layer-expert (Opus), python-backend-engineer (Opus), backend-architect (Opus)

## Phase Overview

Implement the backend infrastructure for extracting, caching, and leveraging frontmatter metadata. This includes database schema updates, frontmatter extraction logic, tools field population, and integration with the artifact import workflow.

---

## Task Breakdown

### DB-001: Database Schema Updates

**Duration**: 1 day
**Effort**: 3 story points
**Assigned**: data-layer-expert
**Dependencies**: Phase 0 complete

#### Description

Create Alembic migration to add `tools` and `linked_artifacts` fields to the artifact model in the database. Both fields are JSON columns for flexible storage.

#### Acceptance Criteria

- [ ] Alembic migration file created in `skillmeat/api/migrations/versions/`
- [ ] Migration adds `tools` JSON column to artifacts table (nullable, empty list default)
- [ ] Migration adds `linked_artifacts` JSON column (nullable, empty list default)
- [ ] Foreign key constraint for linked artifact references (deferred to Phase 2 if needed)
- [ ] Proper indexes created for query performance
- [ ] Migration includes upgrade and downgrade functions
- [ ] Migration tested on fresh database
- [ ] Migration tested on database with existing artifact records
- [ ] Migration rollback verified

#### Implementation Notes

**Migration Structure**:
```python
# skillmeat/api/migrations/versions/xxxx_add_tools_and_linked_artifacts.py
def upgrade():
    # Add tools column
    op.add_column('artifacts',
        sa.Column('tools', sa.JSON, nullable=True,
                  server_default=sa.text('[]'),
                  comment='List of Tool enum values used by this artifact'))

    # Add linked_artifacts column
    op.add_column('artifacts',
        sa.Column('linked_artifacts', sa.JSON, nullable=True,
                  server_default=sa.text('[]'),
                  comment='List of LinkedArtifactReference objects'))

    # Add index for tools queries
    op.create_index('ix_artifacts_tools', 'artifacts', ['tools'])

def downgrade():
    op.drop_index('ix_artifacts_tools', 'artifacts')
    op.drop_column('artifacts', 'tools')
    op.drop_column('artifacts', 'linked_artifacts')
```

**Database Model Update** (SQLAlchemy):
```python
# In artifact model definition
tools: Mapped[List[str]] = mapped_column(
    JSON, default=list,
    comment="Tools used by this artifact"
)
linked_artifacts: Mapped[List[Dict[str, Any]]] = mapped_column(
    JSON, default=list,
    comment="Linked artifact references"
)
```

#### Definition of Done

- [ ] Migration file created and named correctly
- [ ] Upgrade and downgrade functions complete
- [ ] Both columns added to artifacts table
- [ ] Columns have appropriate defaults (empty arrays)
- [ ] Indexes created for performance
- [ ] Migration runs cleanly on fresh database
- [ ] Migration applies to existing databases without data loss
- [ ] SQLAlchemy model updated to reflect new columns

---

### DB-002: Migration Testing

**Duration**: 0.5 days
**Effort**: 2 story points
**Assigned**: data-layer-expert
**Dependencies**: DB-001

#### Description

Thoroughly test the migration on both fresh and populated databases, verify rollback, and confirm model synchronization.

#### Acceptance Criteria

- [ ] Migration runs on fresh database schema
- [ ] Migration runs on database with 100+ existing artifacts
- [ ] Existing artifact records unaffected (no data loss)
- [ ] New columns have correct default values
- [ ] Rollback (downgrade) works correctly
- [ ] Data integrity checks pass (no orphaned references)
- [ ] SQLAlchemy model queries work without errors
- [ ] Performance testing shows indexes are used

#### Testing Scenarios

1. Fresh database: `alembic upgrade head` → verify artifacts table has new columns
2. Populated database: Create test artifacts, run migration, verify columns exist
3. Rollback: Run downgrade on populated database, verify columns removed
4. Performance: Query against indexed columns, verify index usage in EXPLAIN

#### Definition of Done

- [ ] All test scenarios passing
- [ ] Migration is production-safe
- [ ] No performance regressions
- [ ] Ready for Phase 1 API schema work

---

### EXT-001: Frontmatter Extraction Function

**Duration**: 2 days
**Effort**: 3 story points
**Assigned**: python-backend-engineer
**Dependencies**: Phase 0 complete

#### Description

Create `skillmeat/utils/metadata.py` function `extract_frontmatter(content: str) -> Dict[str, Any]` that parses YAML frontmatter from artifact content and returns structured metadata. Handle various frontmatter formats and edge cases gracefully.

#### Acceptance Criteria

- [ ] Function `extract_frontmatter(content: str) -> Dict[str, Any]` created
- [ ] Parses YAML between `---` delimiters at start of file
- [ ] Returns dict with frontmatter fields (name, description, tools, etc.)
- [ ] Returns empty dict if no frontmatter present
- [ ] Gracefully handles malformed YAML (logs warning, doesn't crash)
- [ ] Handles various tools field formats:
  - Comma-separated string: "Bash,Read,Write"
  - YAML array: ["Bash", "Read", "Write"]
  - Single value: "Bash"
- [ ] Handles case variations and normalizes to enum values
- [ ] Extracts all relevant fields: name, description, tools, allowed-tools, skills, hooks, etc.
- [ ] Returns non-existent fields as None/empty
- [ ] Performance: <100ms per artifact on typical size files

#### Implementation Notes

**Fields to Extract**:
- Agent: name, description, tools, disallowedTools, model, permissionMode, skills, hooks
- Skill/Command: name, description, allowed-tools, argument-hint, user-invocable, disable-model-invocation, model, context, agent, hooks
- All types: Custom fields in extra

**Edge Cases**:
- Malformed YAML → return partial dict, log warning
- No frontmatter → return empty dict
- Tools as string vs array → normalize to list
- Missing fields → use None/empty value
- BOM or encoding issues → handle gracefully

```python
# skillmeat/utils/metadata.py
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def extract_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from artifact content.

    Args:
        content: File content with potential YAML frontmatter

    Returns:
        Dict with parsed frontmatter, or empty dict if no frontmatter
    """
    if not content.startswith('---'):
        return {}

    try:
        # Split on first --- to find end of frontmatter
        lines = content.split('\n', 1)[1]  # Skip first ---
        if '---' not in lines:
            return {}

        frontmatter_str = lines.split('---', 1)[0]
        frontmatter = yaml.safe_load(frontmatter_str) or {}

        # Normalize tools field
        if 'tools' in frontmatter:
            frontmatter['tools'] = _normalize_tools(frontmatter['tools'])

        return frontmatter
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse frontmatter YAML: {e}")
        return {}
    except Exception as e:
        logger.warning(f"Unexpected error extracting frontmatter: {e}")
        return {}

def _normalize_tools(tools_value) -> List[str]:
    """Convert tools field to list of strings."""
    if isinstance(tools_value, list):
        return [str(t).strip() for t in tools_value]
    elif isinstance(tools_value, str):
        return [t.strip() for t in tools_value.split(',')]
    else:
        return []
```

#### Definition of Done

- [ ] Function created and tested
- [ ] Handles all documented edge cases
- [ ] Returns correct structure for all artifact types
- [ ] Performance <100ms per artifact
- [ ] Comprehensive docstring with examples
- [ ] Unit tests for all field types and edge cases

---

### EXT-002: Metadata Auto-Population

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: python-backend-engineer
**Dependencies**: EXT-001

#### Description

Create logic to populate ArtifactMetadata fields from extracted frontmatter, with description taking priority from frontmatter when present.

#### Acceptance Criteria

- [ ] Function `populate_metadata_from_frontmatter(metadata: ArtifactMetadata, frontmatter: Dict) -> ArtifactMetadata`
- [ ] Sets `metadata.description = frontmatter.description` if present
- [ ] Sets `metadata.tools = [Tool(t) for t in frontmatter.tools]` if present (from Phase 0 Tool enum)
- [ ] Caches full frontmatter in `metadata.extra['frontmatter'] = frontmatter`
- [ ] Stores extracted tools in `metadata.extra['frontmatter_tools']` for reference
- [ ] Gracefully handles missing frontmatter fields
- [ ] Validates tool names against Tool enum, skips invalid tools
- [ ] Adds any unrecognized tools to `metadata.extra['unknown_tools']` for tracking
- [ ] Returns updated metadata object

#### Implementation Notes

```python
def populate_metadata_from_frontmatter(
    metadata: ArtifactMetadata,
    frontmatter: Dict[str, Any]
) -> ArtifactMetadata:
    """Populate artifact metadata from parsed frontmatter."""
    if not frontmatter:
        return metadata

    # Auto-populate description if present
    if 'description' in frontmatter:
        metadata.description = frontmatter['description']

    # Extract and validate tools
    tools = []
    unknown_tools = []
    for tool_name in frontmatter.get('tools', []):
        try:
            tools.append(Tool(tool_name))
        except ValueError:
            unknown_tools.append(tool_name)

    metadata.tools = tools

    # Cache full frontmatter
    metadata.extra['frontmatter'] = frontmatter
    metadata.extra['frontmatter_tools'] = [t.value for t in tools]
    if unknown_tools:
        metadata.extra['unknown_tools'] = unknown_tools

    return metadata
```

#### Definition of Done

- [ ] Function creates and tested
- [ ] Description populated when present (95%+ success rate)
- [ ] Tools properly extracted and validated
- [ ] Frontmatter cached for later use
- [ ] Invalid tools handled gracefully
- [ ] No errors on missing fields

---

### EXT-003: ArtifactManager Integration

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: python-backend-engineer
**Dependencies**: EXT-001, EXT-002

#### Description

Integrate frontmatter extraction into the artifact import workflow. Update `ArtifactManager.add_from_github()` and `add_from_local()` to call extraction and population functions during import.

#### Acceptance Criteria

- [ ] `ArtifactManager.add_from_github()` calls `extract_frontmatter()` after fetching content
- [ ] `ArtifactManager.add_from_local()` calls `extract_frontmatter()` on artifact files
- [ ] Metadata populated via `populate_metadata_from_frontmatter()`
- [ ] Tools field populated during import (80%+ success rate for agents/skills)
- [ ] Frontmatter caching works (metadata accessible without re-parsing)
- [ ] Non-blocking error handling (extraction failures don't block import)
- [ ] Extraction errors logged at INFO/WARNING level
- [ ] All existing tests still pass
- [ ] New tests verify extraction during import workflow

#### Implementation Notes

```python
# In ArtifactManager.add_from_github()
async def add_from_github(self, source: str, ...):
    # ... existing code to fetch artifact ...

    # Extract and cache frontmatter
    try:
        frontmatter = extract_frontmatter(content)
        self.metadata = populate_metadata_from_frontmatter(
            self.metadata, frontmatter
        )
    except Exception as e:
        logger.warning(f"Frontmatter extraction failed for {source}: {e}")
        # Continue with basic metadata

    # ... rest of import workflow ...
```

#### Definition of Done

- [ ] Integration complete and working
- [ ] Description auto-populated in 95%+ of cases
- [ ] Tools field populated in 80%+ of cases for agents/skills
- [ ] No import regressions
- [ ] Error handling tested
- [ ] All existing tests pass
- [ ] New integration tests verify frontmatter extraction

---

### API-001: Update Artifact API Schema

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: python-backend-engineer
**Dependencies**: Phase 0 complete, DB-001

#### Description

Update FastAPI artifact schemas to include new `tools` field and ensure API responses include cached frontmatter.

#### Acceptance Criteria

- [ ] `skillmeat/api/schemas/artifact.py`: ArtifactSchema updated with `tools: list[str]`
- [ ] Tools field is optional in response (handles None/empty)
- [ ] Frontmatter visible in response via `metadata.extra['frontmatter']`
- [ ] API response includes tools as list of tool names (strings)
- [ ] OpenAPI schema auto-generated correctly
- [ ] API docs (Swagger) show new fields
- [ ] GET `/artifacts/{id}` includes tools and frontmatter
- [ ] GET `/artifacts` list endpoint includes tools (for filtering in Phase 2)
- [ ] No breaking changes to existing endpoints

#### Schema Updates

```python
# skillmeat/api/schemas/artifact.py
from pydantic import BaseModel

class ArtifactSchema(BaseModel):
    # ... existing fields ...
    tools: Optional[List[str]] = None  # NEW

    # metadata already includes extra['frontmatter']
```

#### Definition of Done

- [ ] Schema updated and validated
- [ ] OpenAPI spec generated
- [ ] API endpoint returns tools field
- [ ] Swagger docs show new fields
- [ ] No test regressions
- [ ] Ready for frontend type generation

---

## Phase 1 Quality Gates

Before proceeding to Phase 2, verify:

### Database
- [ ] Migration runs cleanly on fresh and populated databases
- [ ] New columns have correct defaults and types
- [ ] Rollback verified
- [ ] Indexes created and used
- [ ] No performance regressions

### Extraction & Caching
- [ ] Frontmatter parsed from 95%+ of artifacts with frontmatter blocks
- [ ] Description auto-populated in 95%+ of cases
- [ ] Tools field populated in 80%+ of cases for agents/skills
- [ ] Caching eliminates re-parsing on subsequent loads
- [ ] Edge cases handled gracefully (malformed YAML, missing fields)

### Integration
- [ ] Import workflow unchanged externally
- [ ] Extraction non-blocking (errors don't fail imports)
- [ ] All existing tests pass
- [ ] Tools field visible in API responses

### API
- [ ] OpenAPI schema includes new fields
- [ ] Swagger docs show tools and frontmatter
- [ ] GET endpoints return correct data
- [ ] No breaking changes

### Documentation
- [ ] Docstrings added to extraction functions
- [ ] Comments explain caching strategy
- [ ] Schema changes documented

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Frontmatter parse failures block imports | Medium | High | Non-blocking error handling, comprehensive logging |
| Large frontmatter caches bloat database | Low | Medium | Monitor cache sizes, consider compression if needed |
| Tool enum values don't match upstream | Low | High | Verify against Claude Code reference, unit tests |
| Migration fails on large databases | Low | High | Test on replica, provide rollback plan |
| API response time increases | Low | Medium | Performance test, optimize queries if needed |

### Schedule Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Extraction complexity underestimated | Medium | Medium | Implement early, test with 100+ artifacts |
| Database migration issues | Low | High | Early testing, staging rollout |
| Tools enum integration delayed | Low | Medium | Phase 0 completion unblocks this |

---

## Success Criteria Summary

**Extraction**: 95%+ of artifacts with frontmatter have description auto-populated
**Tools Field**: 80%+ of agents/skills have tools populated from frontmatter
**Caching**: Frontmatter cached in metadata.extra, accessible via API
**Integration**: Import workflow unchanged, tools visible in API responses
**Quality**: All tests passing, no regressions, clean error handling

---

## Next Steps

Once Phase 1 is complete:
1. Begin Phase 2: Artifact Linking (parallel with frontend preparation)
2. Phase 1 unblocks: Frontmatter data now available for linking
3. APIs ready for: Frontend type generation and integration
