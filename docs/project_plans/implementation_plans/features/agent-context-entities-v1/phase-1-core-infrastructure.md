---
status: inferred_complete
---
# Phase 1: Core Infrastructure

**Parent Plan**: [agent-context-entities-v1.md](../agent-context-entities-v1.md)
**Duration**: 2 weeks
**Story Points**: 21
**Dependencies**: None

---

## Overview

Establish the foundational infrastructure for context entities: database schema, validation logic, content parsing, and basic CRUD API endpoints. This phase creates the data layer and backend services that all subsequent phases depend on.

### Key Deliverables

1. Extended `ArtifactType` enum with 5 context entity types
2. Database schema migration (4 new columns to `artifacts` table)
3. Validation modules for all context entity types
4. Markdown parser with frontmatter support
5. API router for context entities with 7 endpoints
6. Comprehensive unit tests (90%+ coverage)

---

## Task Breakdown

### TASK-1.1: Extend ArtifactType Enum

**Story Points**: 1
**Assigned To**: `data-layer-expert`
**Dependencies**: None

**Description**:
Add 5 new context entity types to the `ArtifactType` enum in `skillmeat/core/artifact.py`.

**Files to Modify**:
- `skillmeat/core/artifact.py` (lines 33-40)

**Changes Required**:
```python
class ArtifactType(str, Enum):
    # Existing
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP_SERVER = "mcp_server"
    HOOK = "hook"

    # NEW: Context Entities
    PROJECT_CONFIG = "project_config"      # CLAUDE.md, AGENTS.md
    SPEC_FILE = "spec_file"                # .claude/specs/*.md
    RULE_FILE = "rule_file"                # .claude/rules/**/*.md
    CONTEXT_FILE = "context_file"          # .claude/context/*.md
    PROGRESS_TEMPLATE = "progress_template" # .claude/progress/ templates
```

**Acceptance Criteria**:
- [ ] All 5 new types added to enum
- [ ] Docstrings updated to describe each type
- [ ] Type hints remain valid
- [ ] No breaking changes to existing artifact code

---

### TASK-1.2: Database Schema Migration

**Story Points**: 3
**Assigned To**: `data-layer-expert`
**Dependencies**: TASK-1.1

**Description**:
Create Alembic migration to extend `artifacts` table with 4 new columns: `path_pattern`, `auto_load`, `category`, `content_hash`. Update `ArtifactType` database constraint.

**Files to Create**:
- `skillmeat/migrations/versions/{revision}_add_context_entity_columns.py`

**Migration Logic**:
```sql
-- Up migration
ALTER TABLE artifacts ADD COLUMN path_pattern TEXT;
ALTER TABLE artifacts ADD COLUMN auto_load BOOLEAN DEFAULT FALSE;
ALTER TABLE artifacts ADD COLUMN category TEXT;
ALTER TABLE artifacts ADD COLUMN content_hash TEXT;

-- Update constraint
ALTER TABLE artifacts DROP CONSTRAINT IF EXISTS check_artifact_type;
ALTER TABLE artifacts ADD CONSTRAINT check_artifact_type
  CHECK (type IN (
    'skill', 'command', 'agent', 'mcp_server', 'hook',
    'project_config', 'spec_file', 'rule_file',
    'context_file', 'progress_template'
  ));

-- Create index for common queries
CREATE INDEX idx_artifacts_type_category ON artifacts(type, category);
CREATE INDEX idx_artifacts_auto_load ON artifacts(auto_load) WHERE auto_load = TRUE;

-- Down migration (reverse all changes)
```

**Testing Requirements**:
- [ ] Migration runs successfully on dev database
- [ ] Rollback (downgrade) works correctly
- [ ] Existing artifact data is preserved
- [ ] Constraints are enforced (invalid type rejected)
- [ ] Indexes are created

**Acceptance Criteria**:
- [ ] Migration file created with proper revision ID
- [ ] Up and down migrations both work
- [ ] No data loss or corruption
- [ ] New columns have correct types and defaults

---

### TASK-1.3: Context Entity Validation Module

**Story Points**: 5
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-1.1

**Description**:
Create validation module with specific validators for each context entity type. Implement path traversal prevention and structure validation.

**Files to Create**:
- `skillmeat/core/validators/context_entity.py`

**Validation Rules by Type**:

**1. ProjectConfig (CLAUDE.md)**:
- Must have top-level `#` heading (e.g., `# ProjectName`)
- Must NOT have YAML frontmatter
- Content must be valid Markdown
- Recommended sections: Prime Directives, Documentation Policy, Architecture

**2. SpecFile**:
- YAML frontmatter REQUIRED with fields: `title`, `purpose`, `version`
- Optional fields: `token_target`, `format`
- Content after frontmatter must be Markdown
- Frontmatter must be valid YAML

**3. RuleFile**:
- YAML frontmatter REQUIRED with fields: `title`, `scope`
- Optional field: `auto_load`
- Must have `<!-- Path Scope: {scope} -->` comment
- Comment scope must match frontmatter scope
- Content must be Markdown

**4. ContextFile**:
- YAML frontmatter REQUIRED with fields: `title`, `references`
- Optional fields: `last_verified`, `tags`
- `references` must be list of file paths
- Content must be Markdown

**5. ProgressTemplate**:
- YAML frontmatter REQUIRED with `tasks`, `parallelization` sections
- Each task must have `id`, `status`, `assigned_to`, `dependencies`
- Content must be Markdown

**Path Traversal Prevention**:
```python
def validate_path_pattern(pattern: str) -> bool:
    """Ensure path pattern is safe."""
    # Must start with .claude/
    if not pattern.startswith(".claude/"):
        raise ValueError("path_pattern must start with .claude/")

    # No parent directory references
    if ".." in pattern:
        raise ValueError("path_pattern cannot contain ..")

    # No absolute paths
    if pattern.startswith("/"):
        raise ValueError("path_pattern cannot be absolute")

    # No path traversal sequences
    forbidden = ["../", "/..", "//"]
    if any(seq in pattern for seq in forbidden):
        raise ValueError("path_pattern contains forbidden sequence")

    return True
```

**Acceptance Criteria**:
- [ ] All 5 entity types have validators
- [ ] Path traversal attempts are rejected
- [ ] Valid entities pass validation
- [ ] Invalid entities raise descriptive errors
- [ ] Validation errors include field name and reason

---

### TASK-1.4: Markdown Parser with Frontmatter

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: None

**Description**:
Create markdown parser that extracts YAML frontmatter and validates structure. Support optional frontmatter for ProjectConfig type.

**Files to Create**:
- `skillmeat/core/parsers/markdown_parser.py`

**Parser Interface**:
```python
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ParsedMarkdown:
    """Result of parsing markdown with frontmatter."""
    frontmatter: Optional[Dict[str, Any]]
    content: str
    raw: str

def parse_markdown(content: str, require_frontmatter: bool = False) -> ParsedMarkdown:
    """Parse markdown content with optional YAML frontmatter.

    Args:
        content: Raw markdown content
        require_frontmatter: If True, raise error if no frontmatter found

    Returns:
        ParsedMarkdown with separated frontmatter and content

    Raises:
        ValueError: If frontmatter required but not found
        yaml.YAMLError: If frontmatter is invalid YAML
    """
    pass

def extract_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Extract YAML frontmatter from markdown.

    Frontmatter format:
    ---
    key: value
    list:
      - item1
      - item2
    ---

    Content here...
    """
    pass

def validate_frontmatter_schema(
    frontmatter: Dict[str, Any],
    required_fields: list[str],
    optional_fields: list[str] = None
) -> bool:
    """Validate frontmatter has required fields."""
    pass
```

**Implementation Notes**:
- Use `python-markdown` or `mistune` for markdown validation
- Use `PyYAML` for frontmatter parsing
- Handle edge cases: empty frontmatter, malformed YAML, missing delimiters
- Preserve original content for hash comparison

**Acceptance Criteria**:
- [ ] Can parse markdown with frontmatter
- [ ] Can parse markdown without frontmatter
- [ ] Invalid YAML raises descriptive error
- [ ] Frontmatter and content are correctly separated
- [ ] Parser preserves original content exactly

---

### TASK-1.5: API Schemas for Context Entities

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-1.1

**Description**:
Create Pydantic schemas for context entity requests and responses. Include validation logic in schema validators.

**Files to Create**:
- `skillmeat/api/schemas/context_entity.py`

**Schemas to Implement**:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

class ContextEntityCreateRequest(BaseModel):
    """Request to create a new context entity."""

    name: str = Field(..., min_length=1, max_length=255)
    type: Literal[
        "project_config",
        "spec_file",
        "rule_file",
        "context_file",
        "progress_template"
    ]
    category: Optional[str] = Field(None, max_length=100)
    path_pattern: str = Field(..., min_length=1, max_length=500)
    auto_load: bool = False
    content: str = Field(..., min_length=1)
    source: Optional[str] = Field(None, max_length=1000)
    version: Optional[str] = Field(None, max_length=50)

    @validator("path_pattern")
    def validate_path(cls, v):
        """Ensure path pattern is safe (no traversal)."""
        if not v.startswith(".claude/"):
            raise ValueError("path_pattern must start with .claude/")
        if ".." in v:
            raise ValueError("path_pattern cannot contain ..")
        if v.startswith("/"):
            raise ValueError("path_pattern cannot be absolute")
        return v

    @validator("content")
    def validate_content(cls, v, values):
        """Validate content structure based on type."""
        entity_type = values.get("type")
        if not entity_type:
            return v

        # Import validator based on type
        # from skillmeat.core.validators.context_entity import (
        #     validate_project_config, validate_spec_file, ...
        # )
        # Run appropriate validator

        return v

class ContextEntityUpdateRequest(BaseModel):
    """Request to update a context entity."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    path_pattern: Optional[str] = Field(None, min_length=1, max_length=500)
    auto_load: Optional[bool] = None
    content: Optional[str] = Field(None, min_length=1)
    version: Optional[str] = Field(None, max_length=50)

    @validator("path_pattern")
    def validate_path(cls, v):
        """Validate path pattern if provided."""
        if v is None:
            return v
        # Same validation as CreateRequest
        return v

class ContextEntityResponse(BaseModel):
    """Response with context entity data."""

    id: str
    name: str
    type: str
    category: Optional[str]
    path_pattern: str
    auto_load: bool
    content_hash: str
    source: Optional[str]
    version: Optional[str]
    created_at: datetime
    updated_at: datetime
    collections: List[str] = []  # Collection IDs

    class Config:
        from_attributes = True  # Pydantic v2 (use orm_mode for v1)

class ContextEntityListResponse(BaseModel):
    """Response with list of context entities."""

    items: List[ContextEntityResponse]
    total: int
    page_info: Optional[dict] = None  # Pagination info

class ContextEntityContentResponse(BaseModel):
    """Response with raw markdown content."""

    content: str
    content_hash: str
```

**Acceptance Criteria**:
- [ ] All schemas match PRD specifications
- [ ] Validators reject invalid data
- [ ] Validators provide descriptive error messages
- [ ] Schemas are compatible with SQLAlchemy models
- [ ] OpenAPI spec generates correctly

---

### TASK-1.6: Context Entities Router

**Story Points**: 5
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-1.2, TASK-1.3, TASK-1.4, TASK-1.5

**Description**:
Create FastAPI router with 7 endpoints for context entity CRUD operations. Follow patterns from `.claude/rules/api/routers.md`.

**Files to Create**:
- `skillmeat/api/routers/context_entities.py`

**Endpoints to Implement**:

| Method | Endpoint | Purpose | Status Code |
|--------|----------|---------|-------------|
| GET | `/context-entities` | List all context entities | 200 |
| GET | `/context-entities/{id}` | Get entity details | 200, 404 |
| POST | `/context-entities` | Create entity | 201, 422 |
| PUT | `/context-entities/{id}` | Update entity | 200, 404, 422 |
| DELETE | `/context-entities/{id}` | Delete entity | 204, 404 |
| GET | `/context-entities/{id}/content` | Get raw markdown | 200, 404 |
| PUT | `/context-entities/{id}/content` | Update content only | 200, 404, 422 |

**Router Implementation Pattern**:

```python
from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from skillmeat.api.dependencies import DbSessionDep
from skillmeat.api.schemas.context_entity import (
    ContextEntityCreateRequest,
    ContextEntityUpdateRequest,
    ContextEntityResponse,
    ContextEntityListResponse,
    ContextEntityContentResponse,
)
from skillmeat.cache.models import Artifact
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.validators.context_entity import validate_context_entity
from skillmeat.core.parsers.markdown_parser import parse_markdown
import hashlib

router = APIRouter(
    prefix="/context-entities",
    tags=["context-entities"],
)

@router.get("", response_model=ContextEntityListResponse)
async def list_context_entities(
    session: DbSessionDep,
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    auto_load: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
) -> ContextEntityListResponse:
    """List context entities with optional filtering."""
    query = session.query(Artifact).filter(
        Artifact.type.in_([
            ArtifactType.PROJECT_CONFIG,
            ArtifactType.SPEC_FILE,
            ArtifactType.RULE_FILE,
            ArtifactType.CONTEXT_FILE,
            ArtifactType.PROGRESS_TEMPLATE,
        ])
    )

    if type:
        query = query.filter(Artifact.type == type)
    if category:
        query = query.filter(Artifact.category == category)
    if auto_load is not None:
        query = query.filter(Artifact.auto_load == auto_load)

    total = query.count()
    items = query.limit(limit).all()

    return ContextEntityListResponse(
        items=[ContextEntityResponse.model_validate(item) for item in items],
        total=total,
    )

@router.post("", response_model=ContextEntityResponse, status_code=status.HTTP_201_CREATED)
async def create_context_entity(
    request: ContextEntityCreateRequest,
    session: DbSessionDep,
) -> ContextEntityResponse:
    """Create a new context entity."""
    try:
        # Validate content structure
        validate_context_entity(request.type, request.content)

        # Compute content hash
        content_hash = hashlib.sha256(request.content.encode()).hexdigest()

        # Create artifact
        artifact = Artifact(
            name=request.name,
            type=request.type,
            category=request.category,
            path_pattern=request.path_pattern,
            auto_load=request.auto_load,
            content=request.content,
            content_hash=content_hash,
            source=request.source,
            version=request.version,
        )

        session.add(artifact)
        session.commit()
        session.refresh(artifact)

        return ContextEntityResponse.model_validate(artifact)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation failed: {str(e)}"
        )

# Implement remaining endpoints: GET /{id}, PUT /{id}, DELETE /{id}, etc.
```

**Error Handling**:
- 404 if entity not found
- 422 for validation errors (include field name)
- 500 for unexpected errors (log stack trace)

**Acceptance Criteria**:
- [ ] All 7 endpoints implemented
- [ ] Query filtering works (type, category, auto_load)
- [ ] Content hash is computed on create/update
- [ ] Validation errors return 422 with details
- [ ] Router registered in `server.py`

---

### TASK-1.7: Unit Tests for Validation

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-1.3, TASK-1.4

**Description**:
Create comprehensive unit tests for context entity validation and markdown parsing. Aim for 90%+ coverage.

**Files to Create**:
- `tests/unit/test_context_entity_validators.py`
- `tests/unit/test_markdown_parser.py`

**Test Coverage**:

**Validation Tests**:
- [ ] Valid ProjectConfig passes
- [ ] ProjectConfig with frontmatter fails
- [ ] Valid SpecFile passes
- [ ] SpecFile missing frontmatter fails
- [ ] Valid RuleFile passes
- [ ] RuleFile with mismatched scope fails
- [ ] Valid ContextFile passes
- [ ] ContextFile with invalid references fails
- [ ] Valid ProgressTemplate passes
- [ ] ProgressTemplate missing tasks fails

**Path Traversal Tests**:
- [ ] Path with `..` is rejected
- [ ] Path without `.claude/` prefix is rejected
- [ ] Absolute path is rejected
- [ ] Valid path patterns pass

**Markdown Parser Tests**:
- [ ] Parse markdown with frontmatter
- [ ] Parse markdown without frontmatter
- [ ] Invalid YAML raises error
- [ ] Empty frontmatter handled
- [ ] Frontmatter/content separation is correct

**Test Example**:
```python
import pytest
from skillmeat.core.validators.context_entity import (
    validate_project_config,
    validate_spec_file,
    validate_path_pattern,
)

def test_valid_project_config():
    content = """# My Project

SkillMeat: Description

## Prime Directives
...
"""
    # Should not raise
    validate_project_config(content)

def test_project_config_with_frontmatter_fails():
    content = """---
title: "My Project"
---

# My Project
"""
    with pytest.raises(ValueError, match="must not have frontmatter"):
        validate_project_config(content)

def test_path_traversal_prevention():
    with pytest.raises(ValueError, match="cannot contain .."):
        validate_path_pattern(".claude/../../../etc/passwd")

    with pytest.raises(ValueError, match="must start with .claude/"):
        validate_path_pattern("specs/doc-policy.md")
```

**Acceptance Criteria**:
- [ ] 90%+ code coverage for validators
- [ ] 90%+ code coverage for parser
- [ ] All edge cases tested
- [ ] Tests run in CI/CD pipeline
- [ ] Test names are descriptive

---

### TASK-1.8: Integration Tests for API

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-1.6

**Description**:
Create integration tests for context entities router endpoints. Use TestClient to test full request/response cycle.

**Files to Create**:
- `tests/integration/test_context_entities_api.py`

**Test Scenarios**:
- [ ] Create ProjectConfig via POST
- [ ] Create SpecFile via POST
- [ ] List entities with filters
- [ ] Get entity by ID
- [ ] Update entity
- [ ] Delete entity
- [ ] Get raw content
- [ ] Update content only
- [ ] Invalid requests return 422
- [ ] Non-existent entity returns 404

**Test Example**:
```python
from fastapi.testclient import TestClient
from skillmeat.api.server import app

client = TestClient(app)

def test_create_spec_file():
    payload = {
        "name": "doc-policy-spec",
        "type": "spec_file",
        "category": "specs",
        "path_pattern": ".claude/specs/doc-policy-spec.md",
        "auto_load": True,
        "content": """---
title: "Documentation Policy"
purpose: "Documentation rules"
version: "1.0"
---

# Documentation Policy
...""",
        "version": "1.0",
    }

    response = client.post("/api/v1/context-entities", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "doc-policy-spec"
    assert data["type"] == "spec_file"
    assert data["content_hash"] is not None

def test_path_traversal_rejected():
    payload = {
        "name": "malicious",
        "type": "spec_file",
        "path_pattern": ".claude/../../../etc/passwd",
        "content": "# Malicious"
    }

    response = client.post("/api/v1/context-entities", json=payload)
    assert response.status_code == 422
    assert "cannot contain .." in response.json()["detail"]
```

**Acceptance Criteria**:
- [ ] All endpoints have integration tests
- [ ] Happy path and error cases covered
- [ ] Database state is cleaned up after tests
- [ ] Tests are isolated (no dependencies between tests)

---

### TASK-1.9: Register Router in Server

**Story Points**: 1
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-1.6

**Description**:
Register the context entities router in the main FastAPI application.

**Files to Modify**:
- `skillmeat/api/server.py`

**Changes Required**:
```python
from skillmeat.api.routers import (
    artifacts,
    collections,
    user_collections,
    context_entities,  # NEW
    # ... other routers
)

# Register routers
app.include_router(
    context_entities.router,
    prefix=settings.api_prefix,  # "/api/v1"
    tags=["context-entities"]
)
```

**Acceptance Criteria**:
- [ ] Router is registered with correct prefix
- [ ] OpenAPI docs show context entities endpoints
- [ ] Endpoints are accessible at `/api/v1/context-entities`

---

## Parallelization Plan

### Batch 1 (Parallel)
Run these tasks simultaneously - no dependencies between them:
- TASK-1.1: Extend ArtifactType enum
- TASK-1.3: Context entity validation module (depends only on 1.1, can start immediately after)
- TASK-1.4: Markdown parser (independent)

**Delegation**:
```python
Task("data-layer-expert", "TASK-1.1: Extend ArtifactType enum...")
Task("python-backend-engineer", "TASK-1.3: Context entity validation...")
Task("python-backend-engineer", "TASK-1.4: Markdown parser...")
```

### Batch 2 (Sequential)
Wait for Batch 1 to complete, then run:
- TASK-1.2: Database migration (needs TASK-1.1)

**Delegation**:
```python
Task("data-layer-expert", "TASK-1.2: Database migration...")
```

### Batch 3 (Parallel)
After Batch 2, run these in parallel:
- TASK-1.5: API schemas (needs TASK-1.1)
- TASK-1.7: Unit tests (needs TASK-1.3, TASK-1.4)

**Delegation**:
```python
Task("python-backend-engineer", "TASK-1.5: API schemas...")
Task("python-backend-engineer", "TASK-1.7: Unit tests...")
```

### Batch 4 (Sequential)
After Batch 3:
- TASK-1.6: Context entities router (needs TASK-1.2, 1.3, 1.4, 1.5)

**Delegation**:
```python
Task("python-backend-engineer", "TASK-1.6: Context entities router...")
```

### Batch 5 (Parallel)
After TASK-1.6:
- TASK-1.8: Integration tests
- TASK-1.9: Register router

**Delegation**:
```python
Task("python-backend-engineer", "TASK-1.8: Integration tests...")
Task("python-backend-engineer", "TASK-1.9: Register router...")
```

---

## Quality Gates

Before completing Phase 1:

- [ ] All tasks marked complete
- [ ] Database migration runs successfully (up and down)
- [ ] All 5 context entity types have validators
- [ ] API endpoints return correct status codes
- [ ] 90%+ test coverage for new code
- [ ] OpenAPI spec generates without errors
- [ ] No critical security issues (path traversal tests pass)
- [ ] Code review completed
- [ ] Documentation strings complete

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Test coverage (validation) | 90%+ | ___ |
| Test coverage (parser) | 90%+ | ___ |
| Test coverage (router) | 80%+ | ___ |
| API endpoint count | 7 | ___ |
| Context entity types supported | 5 | ___ |
| Migration time (dev DB) | < 5s | ___ |

---

## Risks & Mitigation

**Risk 1**: Migration conflicts with production data
- **Mitigation**: Test migration on staging database first, create rollback plan
- **Owner**: `data-layer-expert`

**Risk 2**: Path traversal validation bypass
- **Mitigation**: Comprehensive edge case testing, security review
- **Owner**: `python-backend-engineer`

**Risk 3**: Markdown parser performance with large files
- **Mitigation**: Profile parser, add file size limits (e.g., 1MB max)
- **Owner**: `python-backend-engineer`

---

## Next Phase

Once Phase 1 is complete and all quality gates pass, proceed to:
**[Phase 2: CLI Management](phase-2-cli-management.md)**
