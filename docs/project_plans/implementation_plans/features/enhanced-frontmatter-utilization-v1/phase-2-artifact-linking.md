---
title: 'Phase 2: Artifact Linking'
description: LinkedArtifactReference model, auto-linking logic, manual linking API
  endpoints
created: 2026-01-21
updated: 2026-01-21
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: enhanced-frontmatter-utilization
prd_ref: null
plan_ref: null
---
# Phase 2: Artifact Linking

**Duration**: 1.5 weeks
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: backend-architect (Opus), python-backend-engineer (Opus)

## Phase Overview

Implement the artifact linking system, including the LinkedArtifactReference data model, auto-linking logic that parses frontmatter references, manual linking API endpoints, and storage of unmatched references for user action.

---

## Task Breakdown

### LINK-001: LinkedArtifactReference Model

**Duration**: 1 day
**Effort**: 2 story points
**Assigned**: backend-architect
**Dependencies**: Phase 1 complete

#### Description

Define `LinkedArtifactReference` dataclass and corresponding API schema. This represents a link from one artifact to another, with metadata about the relationship type.

#### Acceptance Criteria

- [ ] Dataclass `LinkedArtifactReference` created in `skillmeat/core/artifact.py`
- [ ] Fields:
  - `artifact_id: Optional[str]` - ID of target artifact (None if unresolved/external)
  - `artifact_name: str` - Display name of target artifact
  - `artifact_type: ArtifactType` - Type of target artifact (skill, agent, etc.)
  - `source_name: Optional[str]` - Source name where target was found
  - `link_type: str` - Type of relationship (requires, enables, related)
  - `created_at: Optional[datetime]` - When link was created
- [ ] Schema `LinkedArtifactReferenceSchema` created in API schemas
- [ ] Pydantic validation ensures link_type is valid
- [ ] Serialization works (to_dict, from_dict)
- [ ] Docstrings explain each field and link types

#### Implementation Notes

```python
# skillmeat/core/artifact.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class LinkedArtifactReference:
    """Reference to a linked artifact."""
    artifact_name: str
    artifact_type: 'ArtifactType'  # Use string for forward reference
    artifact_id: Optional[str] = None  # None if external or unresolved
    source_name: Optional[str] = None
    link_type: str = "requires"  # requires, enables, related
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'artifact_id': self.artifact_id,
            'artifact_name': self.artifact_name,
            'artifact_type': self.artifact_type.value if hasattr(self.artifact_type, 'value') else str(self.artifact_type),
            'source_name': self.source_name,
            'link_type': self.link_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LinkedArtifactReference':
        return cls(
            artifact_id=data.get('artifact_id'),
            artifact_name=data['artifact_name'],
            artifact_type=data['artifact_type'],
            source_name=data.get('source_name'),
            link_type=data.get('link_type', 'requires'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
        )
```

**API Schema**:
```python
# skillmeat/api/schemas/artifact.py
from pydantic import BaseModel, Field

class LinkedArtifactReferenceSchema(BaseModel):
    artifact_id: Optional[str] = None
    artifact_name: str
    artifact_type: str  # ArtifactType value
    source_name: Optional[str] = None
    link_type: str = Field(default="requires", regex="^(requires|enables|related)$")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

#### Definition of Done

- [ ] Dataclass defined and tested
- [ ] Serialization/deserialization works
- [ ] API schema matches dataclass
- [ ] Validation of link_type works
- [ ] Can import and use in models

---

### LINK-002: Artifact Linking Logic

**Duration**: 2 days
**Effort**: 4 story points
**Assigned**: backend-architect
**Dependencies**: LINK-001, Phase 1 complete

#### Description

Implement the core linking logic that identifies artifact references in frontmatter and matches them to artifacts in the collection. This includes parsing skill references, resolving to existing artifacts, and handling unmatched references.

#### Acceptance Criteria

- [ ] Function `extract_artifact_references(frontmatter: Dict, artifact_type: ArtifactType) -> List[str]`
  - Extracts skill references from agent frontmatter.skills field
  - Extracts tool references from any artifact's tools/allowed-tools field
  - Handles both string and array formats
- [ ] Function `match_artifact_reference(reference: str, source_artifacts: List[Artifact], artifact_type: ArtifactType) -> Optional[Artifact]`
  - Case-insensitive name matching
  - Handles plural forms (skill→skills)
  - Optional fuzzy matching if confidence >80%
  - Returns matched Artifact or None
- [ ] Function `create_linked_artifact_reference(target_artifact: Artifact, link_type: str) -> LinkedArtifactReference`
  - Creates reference from target artifact data
  - Sets artifact_id, name, type
- [ ] Linking matches 70%+ of references without user intervention
- [ ] Unmatched references stored for manual linking
- [ ] No errors on edge cases (missing fields, malformed data)

#### Implementation Notes

**Reference Extraction**:
```python
def extract_artifact_references(
    frontmatter: Dict[str, Any],
    artifact_type: ArtifactType
) -> Dict[str, List[str]]:
    """Extract artifact references from frontmatter.

    Returns:
        Dict with keys 'requires', 'enables', 'related'
    """
    references = {'requires': [], 'enables': [], 'related': []}

    # Agent-specific: skills field indicates "requires"
    if artifact_type == ArtifactType.AGENT:
        skills = frontmatter.get('skills', [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',')]
        references['requires'].extend(skills)

    # Tools field (any artifact): indicates "requires"
    tools = frontmatter.get('tools', [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(',')]
    references['requires'].extend(tools)

    # Skill-specific: agent field indicates "enables"
    if artifact_type == ArtifactType.SKILL:
        agent = frontmatter.get('agent')
        if agent:
            references['enables'].append(agent)

    return references
```

**Reference Matching**:
```python
def match_artifact_reference(
    reference: str,
    source_artifacts: List[Artifact],
    artifact_type: Optional[ArtifactType] = None
) -> Optional[Artifact]:
    """Match artifact reference to collection artifact.

    Tries:
    1. Exact name match (case-insensitive)
    2. Plural/singular form match (skill → skills, tool → tools)
    3. Fuzzy match if confidence >80% (future enhancement)
    """
    reference_lower = reference.lower().strip()

    # Exact name match
    for artifact in source_artifacts:
        if artifact.name.lower() == reference_lower:
            return artifact

    # Plural/singular form match
    singular = reference_lower.rstrip('s')
    plural = reference_lower + 's'
    for artifact in source_artifacts:
        artifact_name_lower = artifact.name.lower()
        if artifact_name_lower in (singular, plural):
            return artifact

    # Type-filtered match if artifact_type specified
    if artifact_type:
        for artifact in source_artifacts:
            if artifact.type == artifact_type and artifact.name.lower() == reference_lower:
                return artifact

    return None
```

#### Definition of Done

- [ ] Linking logic implemented and tested
- [ ] Extract function handles all reference types
- [ ] Match function achieves 70%+ success rate
- [ ] Edge cases handled (missing fields, malformed data)
- [ ] Comprehensive unit tests
- [ ] Performance acceptable (<100ms per artifact)

---

### LINK-003: Auto-Linking During Import

**Duration**: 1.5 days
**Effort**: 3 story points
**Assigned**: python-backend-engineer
**Dependencies**: LINK-002, EXT-003

#### Description

Integrate artifact linking into the import workflow. When importing an artifact with frontmatter, automatically resolve references to other artifacts in the same source and create links.

#### Acceptance Criteria

- [ ] `ArtifactManager.add_from_github()` calls linking logic after extraction
- [ ] `ArtifactManager.add_from_local()` calls linking logic for local artifacts
- [ ] Auto-linking matches 70%+ of references in same source
- [ ] Unmatched references stored in `artifact.unlinked_references`
- [ ] Linked artifacts stored in `artifact.linked_artifacts`
- [ ] Link type set appropriately (requires, enables, related)
- [ ] Non-blocking (linking failures don't block import)
- [ ] Linking tested with real artifact samples
- [ ] No performance regression in import workflow

#### Implementation Notes

```python
# In ArtifactManager.add_from_github()
async def add_from_github(self, source: str, artifact_type: ArtifactType, ...):
    # ... existing code through frontmatter extraction ...

    # Get other artifacts in same source for linking
    source_artifacts = self.repository.get_artifacts_by_source(source_id)

    # Extract and resolve references
    try:
        references = extract_artifact_references(frontmatter, artifact_type)
        linked = []
        unlinked = []

        for ref_name in references['requires']:
            matched = match_artifact_reference(ref_name, source_artifacts)
            if matched:
                linked.append(create_linked_artifact_reference(matched, 'requires'))
            else:
                unlinked.append(ref_name)

        # Store in artifact
        self.artifact.linked_artifacts = linked
        self.artifact.unlinked_references = unlinked
    except Exception as e:
        logger.warning(f"Auto-linking failed for {source}: {e}")
        # Continue without linking

    # ... rest of import workflow ...
```

#### Definition of Done

- [ ] Auto-linking integrated into import workflow
- [ ] 70%+ reference match rate achieved
- [ ] Unlinked references stored and queryable
- [ ] Linked artifacts persist to database
- [ ] No import regressions
- [ ] Integration tests verify linking during import

---

### API-002: Artifact Linking Endpoints

**Duration**: 2 days
**Effort**: 4 story points
**Assigned**: python-backend-engineer
**Dependencies**: LINK-001, LINK-003, API-001

#### Description

Create REST API endpoints for managing artifact links: create, delete, and list links for an artifact.

#### Acceptance Criteria

- [ ] `POST /artifacts/{artifact_id}/linked-artifacts` - Create link
  - Request: `{ target_artifact_id: str, link_type: str }`
  - Response: Created LinkedArtifactReference
  - Validation: Both artifacts exist, not self-linking
- [ ] `DELETE /artifacts/{artifact_id}/linked-artifacts/{target_artifact_id}` - Delete link
  - Response: 204 No Content
  - Validation: Link exists, authenticated user owns artifact
- [ ] `GET /artifacts/{artifact_id}/linked-artifacts` - List links
  - Response: Array of LinkedArtifactReference
  - Optional filters: link_type
- [ ] `GET /artifacts` supports optional `tools` query parameter for filtering by tools
  - Example: `GET /artifacts?tools=Bash,Read`
  - Returns artifacts with any of specified tools
- [ ] All endpoints require authentication (user owns artifact)
- [ ] Proper error responses (404, 400, 409, etc.)
- [ ] OpenAPI documentation generated correctly

#### Router Implementation

```python
# skillmeat/api/routers/artifacts.py

@router.post("/{artifact_id}/linked-artifacts")
async def create_linked_artifact(
    artifact_id: str,
    request: CreateLinkedArtifactRequest,
    db: DbSessionDep,
    user: UserDep,
):
    """Create a link from artifact to another artifact."""
    # Verify both artifacts exist and belong to user
    source = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.user_id == user.id
    ).first()
    if not source:
        raise HTTPException(404, "Artifact not found")

    target = db.query(Artifact).filter(
        Artifact.id == request.target_artifact_id
    ).first()
    if not target:
        raise HTTPException(404, "Target artifact not found")

    if artifact_id == request.target_artifact_id:
        raise HTTPException(400, "Cannot link to self")

    # Create link
    link = LinkedArtifactReference(
        artifact_id=target.id,
        artifact_name=target.name,
        artifact_type=target.type,
        link_type=request.link_type
    )
    source.linked_artifacts.append(link)
    db.commit()

    return LinkedArtifactReferenceSchema.from_orm(link)

@router.delete("/{artifact_id}/linked-artifacts/{target_artifact_id}")
async def delete_linked_artifact(
    artifact_id: str,
    target_artifact_id: str,
    db: DbSessionDep,
    user: UserDep,
):
    """Delete a link from artifact."""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.user_id == user.id
    ).first()
    if not artifact:
        raise HTTPException(404, "Artifact not found")

    artifact.linked_artifacts = [
        l for l in artifact.linked_artifacts
        if l.artifact_id != target_artifact_id
    ]
    db.commit()
    return Response(status_code=204)

@router.get("/{artifact_id}/linked-artifacts")
async def list_linked_artifacts(
    artifact_id: str,
    link_type: Optional[str] = None,
    db: DbSessionDep = None,
):
    """List artifacts linked from this artifact."""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id
    ).first()
    if not artifact:
        raise HTTPException(404, "Artifact not found")

    links = artifact.linked_artifacts
    if link_type:
        links = [l for l in links if l.link_type == link_type]

    return [LinkedArtifactReferenceSchema.from_orm(l) for l in links]
```

#### Definition of Done

- [ ] All three endpoints implemented
- [ ] Request/response schemas defined
- [ ] Authentication and validation working
- [ ] OpenAPI docs generated
- [ ] Error handling correct (404, 400, 409, 204)
- [ ] Tests verify all endpoints
- [ ] No regressions to existing artifact endpoints

---

### LINK-004: Unlinked References Management

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: python-backend-engineer
**Dependencies**: LINK-003

#### Description

Implement storage and querying of unlinked artifact references. These are references found in frontmatter that didn't match any collection artifacts, stored for user manual linking later.

#### Acceptance Criteria

- [ ] `artifact.unlinked_references: List[str]` field persists to database
- [ ] Unlinked references populated during auto-linking
- [ ] API endpoint `GET /artifacts/{id}/unlinked-references` returns list
- [ ] Unlinked references include original reference text (for user action)
- [ ] Can query artifacts with unlinked references: `GET /artifacts?has_unlinked=true`
- [ ] Unlinked references cleared when manual link created
- [ ] Queryable for migration/cleanup purposes

#### API Endpoints

```python
@router.get("/{artifact_id}/unlinked-references")
async def get_unlinked_references(artifact_id: str, db: DbSessionDep):
    """Get list of unlinked artifact references."""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id
    ).first()
    if not artifact:
        raise HTTPException(404, "Artifact not found")

    return {
        'unlinked_references': artifact.unlinked_references or []
    }
```

#### Definition of Done

- [ ] Unlinked references stored and retrieved correctly
- [ ] API endpoint returns comprehensive list
- [ ] Can query artifacts with unlinked references
- [ ] Unlinked references cleared on manual link creation
- [ ] Tests verify storage and retrieval

---

### TEST-001: Integration Tests for Linking

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: python-backend-engineer
**Dependencies**: All Phase 2 tasks complete

#### Description

Comprehensive integration tests for the entire linking workflow, including auto-linking during import, manual linking via API, and unlinked reference management.

#### Acceptance Criteria

- [ ] Test: Import artifact with frontmatter → auto-linked artifacts stored
- [ ] Test: Import artifact with unmatchable references → unlinked_references populated
- [ ] Test: Create manual link via API → link persisted and queryable
- [ ] Test: Delete link via API → link removed
- [ ] Test: List linked artifacts → correct data returned
- [ ] Test: Self-linking prevented → 400 error returned
- [ ] Test: Nonexistent target → 404 error returned
- [ ] Test: Link type variations (requires, enables, related) → all work
- [ ] Coverage: >85% for linking code
- [ ] Performance: Linking <100ms per artifact

#### Test Scenarios

```python
def test_auto_linking_during_import():
    """Artifacts referenced in frontmatter are auto-linked."""
    # Create two artifacts in collection
    skill1 = create_artifact(name="python-utils", type=SKILL)
    skill2 = create_artifact(name="bash-helpers", type=SKILL)

    # Create agent with skill references
    agent = create_artifact(
        name="code-analyzer",
        type=AGENT,
        frontmatter={'skills': ['python-utils', 'bash-helpers']}
    )

    # Auto-linking should have created links
    assert len(agent.linked_artifacts) == 2
    assert agent.linked_artifacts[0].artifact_name == "python-utils"
    assert agent.linked_artifacts[1].artifact_name == "bash-helpers"

def test_manual_linking_via_api():
    """User can manually create links via API."""
    artifact1 = create_artifact()
    artifact2 = create_artifact()

    # Create link
    response = client.post(
        f"/artifacts/{artifact1.id}/linked-artifacts",
        json={
            "target_artifact_id": artifact2.id,
            "link_type": "requires"
        }
    )
    assert response.status_code == 201

    # Verify link persisted
    links = artifact1.linked_artifacts
    assert len(links) == 1
    assert links[0].artifact_id == artifact2.id

def test_unlinked_references():
    """References that don't match are stored as unlinked."""
    # Create artifact with unmatchable reference
    artifact = create_artifact(
        type=AGENT,
        frontmatter={'skills': ['unknown-skill']}
    )

    assert 'unknown-skill' in artifact.unlinked_references
```

#### Definition of Done

- [ ] All test scenarios passing
- [ ] >85% coverage for linking code
- [ ] Performance targets met
- [ ] Edge cases covered
- [ ] Ready for Phase 3 (UI implementation)

---

## Phase 2 Quality Gates

Before proceeding to Phase 3, verify:

### Linking Logic
- [ ] Auto-linking matches 70%+ of references
- [ ] Unmatched references stored for manual action
- [ ] No circular linking allowed
- [ ] Link types (requires, enables, related) working correctly

### API Endpoints
- [ ] All CRUD operations functional
- [ ] Authentication and authorization enforced
- [ ] Proper error responses (400, 404, 409, 204)
- [ ] OpenAPI documentation accurate
- [ ] Tools filter working

### Data Integrity
- [ ] No orphaned references
- [ ] Links persist correctly
- [ ] Unlinked references queryable
- [ ] No data loss on link deletion

### Testing
- [ ] >85% code coverage for linking
- [ ] All integration tests passing
- [ ] Performance targets met (<100ms per artifact)
- [ ] Edge cases handled

### Documentation
- [ ] API endpoints documented
- [ ] Linking algorithm documented
- [ ] Link type semantics explained

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Auto-linking accuracy <70% | Medium | High | Implement fuzzy matching fallback, manual linking UI |
| Circular linking | Low | Medium | Prevent self-links, detect cycles in validation |
| Large number of links slows API | Low | Medium | Pagination, lazy-load in frontend |
| Database constraints break | Low | High | Thorough migration testing, constraint validation |

### Schedule Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Matching algorithm complexity | Medium | Medium | Implement early, iterate with samples |
| API design changes late | Low | Medium | Finalize schema early, mock in frontend |
| Integration test coverage gaps | Medium | Low | Comprehensive test scenarios planned |

---

## Success Criteria Summary

**Auto-Linking**: 70%+ of references matched and linked
**API**: All CRUD operations functional with proper validation
**Unlinked References**: Stored and queryable for manual linking
**Data Integrity**: No orphaned references, correct persistence
**Testing**: >85% coverage, all integration tests passing

---

## Next Steps

Once Phase 2 is complete:
1. Begin Phase 3: UI Components & Integration
2. Phase 2 enables: Frontend can consume linking APIs
3. Ready for: LinkedArtifactsSection and ArtifactLinkingDialog components
