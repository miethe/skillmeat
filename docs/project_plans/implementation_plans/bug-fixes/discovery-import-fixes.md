---
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: discovery-import-fixes
prd_ref: null
---
# Discovery & Import Bug Fixes Implementation Plan

**Created**: 2026-01-12
**Status**: Completed
**Priority**: High
**Affected Areas**: Project Discovery, Bulk Import, Collection Status

---

## Executive Summary

The artifact discovery and import functionality for Projects has multiple bugs preventing proper import of commands and agents. These bugs cause:

1. All commands/agents to fail with "not a directory" errors
2. Status mismatch where artifacts show as "New" but fail import as "already exists"
3. Invalid character errors for namespaced command names

**Root Cause**: The codebase was designed primarily for directory-based artifacts (skills) but commands and agents are **single-file** artifacts per `ARTIFACT_SIGNATURES`.

---

## Bug Analysis

### Bug 1: Importer Directory Validation

**Severity**: Critical
**Impact**: ALL commands and agents fail to import

#### Location
- **File**: `skillmeat/core/importer.py`
- **Line**: 630
- **Function**: `_validate_artifact_structure()`

#### Current Code
```python
# Check it's a directory
if not artifact_path.is_dir():
    artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
    return ImportResultData(
        artifact_id=artifact_id,
        success=False,
        message="Validation failed",
        error=f"Artifact path is not a directory: {artifact.path}",
        status=ImportStatus.FAILED,
        reason_code="invalid_structure",
        path=artifact.path,
    )
```

#### Root Cause
The validation unconditionally requires all artifacts to be directories. However, per `ARTIFACT_SIGNATURES` in `artifact_detection.py`:

| Artifact Type | `is_directory` | Expected Structure |
|--------------|----------------|-------------------|
| skill | `True` | Directory with `SKILL.md` |
| command | `False` | Single `.md` file |
| agent | `False` | Single `.md` file |
| hook | `False` | File-based |
| mcp | `False` | File-based |

#### Symptoms
- Error: `Artifact path is not a directory: /path/to/.claude/agents/pm/lead-pm.md`
- All commands and agents fail validation
- Only skills import successfully

---

### Bug 2: Discovery Existence Check

**Severity**: Critical
**Impact**: Deployed artifacts show as "New" but fail import as duplicates

#### Location
- **File**: `skillmeat/core/discovery.py`
- **Lines**: 1212, 1253
- **Function**: `check_artifact_exists()`

#### Current Code
```python
# Check Collection (line 1212)
if collection_artifact_dir.exists() and collection_artifact_dir.is_dir():
    exists_in_collection = True

# Check Project (line 1253)
if project_artifact_dir.exists() and project_artifact_dir.is_dir():
    exists_in_project = True
```

#### Root Cause
Both checks only look for **directories**. For file-based artifacts:
- Path constructed: `.claude/commands/{name}/` (directory)
- Actual path: `.claude/commands/{subdirs}/filename.md` (file)
- Result: Always returns `False` even when artifact exists

#### Symptoms
- Artifact deployed to project shows correctly as "deployed" in artifact view
- Same artifact shows as "New" in discovery view (file not found as directory)
- Import fails with "already exists in collection" (manifest check succeeds)
- Creates confusing UX with contradictory status

---

### Bug 3: Artifact Name with Colon

**Severity**: Medium
**Impact**: Namespaced commands fail name validation

#### Location
- **File**: `skillmeat/core/validation.py`
- **Lines**: 197-201
- **Function**: `validate_artifact_name()`

#### Current Code
```python
# Check for invalid characters
invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
for char in invalid_chars:
    if char in name:
        return False, f"Artifact name cannot contain invalid character: {char}"
```

#### Observed Error
```
Artifact name cannot contain invalid character: :
command:symbols:query
```

#### Root Cause Analysis
The error message shows `command:symbols:query` as the artifact name. This is the **artifact_id format** (`type:name`), not the actual name. Possible sources:

1. **Frontend mapping issue**: Import request constructed with `artifact_id` instead of `name`
2. **Nested path extraction**: Commands like `.claude/commands/analyze/symbols/symbols-query.md` may have name extracted incorrectly
3. **Logging artifact**: Error message includes artifact_id for context

#### Investigation Needed
- Trace frontend `BulkImportRequest` construction
- Check if `source` field parsing extracts name correctly
- Verify discovery service name extraction for nested artifacts

---

## Remediation Plan

### Phase 1: Fix Importer Directory Validation (Bug 1)

**Estimated Effort**: Low
**Risk**: Low (isolated change)

#### Changes Required

**File**: `skillmeat/core/importer.py`

Replace the unconditional directory check with type-aware validation:

```python
def _validate_artifact_structure(
    self, artifact: BulkImportArtifactData
) -> Optional[ImportResultData]:
    """Validate artifact structure before import."""
    from skillmeat.core.artifact_detection import (
        ArtifactType,
        ARTIFACT_SIGNATURES,
    )

    # ... existing path existence check ...

    artifact_path = Path(artifact.path)

    # Get expected structure from artifact signatures
    try:
        artifact_type_enum = ArtifactType(artifact.artifact_type)
        signature = ARTIFACT_SIGNATURES.get(artifact_type_enum)
    except (ValueError, KeyError):
        signature = None

    # Validate structure based on artifact type
    if signature and signature.is_directory:
        # Skills require directory structure
        if not artifact_path.is_dir():
            return ImportResultData(
                artifact_id=f"{artifact.artifact_type}:{artifact.name or artifact_path.name}",
                success=False,
                message="Validation failed",
                error=f"Artifact path is not a directory: {artifact.path}",
                status=ImportStatus.FAILED,
                reason_code="invalid_structure",
                path=artifact.path,
            )
    else:
        # Commands, agents, etc. can be single files
        if not artifact_path.is_file() and not artifact_path.is_dir():
            return ImportResultData(
                artifact_id=f"{artifact.artifact_type}:{artifact.name or artifact_path.name}",
                success=False,
                message="Validation failed",
                error=f"Artifact path does not exist: {artifact.path}",
                status=ImportStatus.FAILED,
                reason_code="invalid_structure",
                path=artifact.path,
            )

    # Continue with metadata file validation...
```

#### Also Update Metadata File Check (lines 642-665)

The metadata file check also assumes directories. Update to handle single-file artifacts:

```python
# For single-file artifacts, the file IS the metadata
if signature and not signature.is_directory:
    if artifact_path.is_file() and artifact_path.suffix.lower() == ".md":
        # Single-file artifact - validate YAML frontmatter directly
        # ... validate frontmatter in artifact_path itself ...
        return None  # Valid
```

---

### Phase 2: Fix Discovery Existence Check (Bug 2)

**Estimated Effort**: Medium
**Risk**: Low (read-only operation)

#### Changes Required

**File**: `skillmeat/core/discovery.py`

Update `check_artifact_exists()` to handle file-based artifacts:

```python
def check_artifact_exists(
    self,
    artifact_key: str,
    manifest: Optional["Collection"] = None,
) -> Dict[str, Any]:
    """Check if artifact exists in Collection and/or Project."""
    from skillmeat.core.artifact_detection import (
        ArtifactType,
        ARTIFACT_SIGNATURES,
    )

    # Parse artifact_key
    try:
        artifact_type, artifact_name = artifact_key.split(":", 1)
    except ValueError:
        # ... existing error handling ...

    # Get artifact signature to determine structure
    try:
        artifact_type_enum = ArtifactType(artifact_type)
        signature = ARTIFACT_SIGNATURES.get(artifact_type_enum)
        is_directory_based = signature.is_directory if signature else True
    except (ValueError, KeyError):
        is_directory_based = True  # Default to directory for unknown types

    # Check Collection
    try:
        collection_base = config.get_collection_path(collection_name)
        container_name = f"{artifact_type}s"  # e.g., "skills", "commands"

        if is_directory_based:
            # Skills: look for directory
            collection_artifact_path = (
                collection_base / "artifacts" / container_name / artifact_name
            )
            if collection_artifact_path.exists() and collection_artifact_path.is_dir():
                exists_in_collection = True
                collection_path = str(collection_artifact_path)
        else:
            # Commands/agents: look for .md file (may be nested)
            # Search for {name}.md in container directory
            container_dir = collection_base / "artifacts" / container_name
            if container_dir.exists():
                # Direct file: container/{name}.md
                direct_file = container_dir / f"{artifact_name}.md"
                if direct_file.exists() and direct_file.is_file():
                    exists_in_collection = True
                    collection_path = str(direct_file)
                else:
                    # Search nested: container/**/{name}.md
                    for md_file in container_dir.rglob(f"{artifact_name}.md"):
                        if md_file.is_file():
                            exists_in_collection = True
                            collection_path = str(md_file)
                            break

        # Fallback to manifest check (existing code)
        if not exists_in_collection and manifest:
            # ... existing manifest check ...

    except Exception as e:
        logger.warning(f"Error checking collection: {e}")

    # Check Project (similar pattern)
    try:
        container_name = f"{artifact_type}s"

        if is_directory_based:
            project_artifact_path = (
                self.base_path / ".claude" / container_name / artifact_name
            )
            if project_artifact_path.exists() and project_artifact_path.is_dir():
                exists_in_project = True
                project_path = str(project_artifact_path)
        else:
            container_dir = self.base_path / ".claude" / container_name
            if container_dir.exists():
                # Search for file
                for md_file in container_dir.rglob(f"{artifact_name}.md"):
                    if md_file.is_file():
                        exists_in_project = True
                        project_path = str(md_file)
                        break

    except Exception as e:
        logger.warning(f"Error checking project: {e}")

    # ... rest of function ...
```

---

### Phase 3: Investigate Artifact Name Issue (Bug 3)

**Estimated Effort**: Low-Medium
**Risk**: Low (investigation only)

#### Investigation Steps

1. **Check frontend import request construction**
   - File: `skillmeat/web/app/projects/[id]/page.tsx`
   - Line: 205-212
   - Verify `name` field is artifact name, not artifact_id

2. **Check backend name extraction**
   - File: `skillmeat/core/discovery.py`
   - Function: `_extract_artifact_metadata()`
   - Verify nested command paths extract name correctly

3. **Check if issue is logging vs validation**
   - The format `command:symbols:query` may be artifact_id in error message
   - Actual name being validated may be different

#### Potential Fix (if frontend issue)

```typescript
// In app/projects/[id]/page.tsx
artifacts: selected.map((a) => ({
  source: a.source || `local/${a.type}/${a.name}`,
  artifact_type: a.type,
  name: a.name,  // Ensure this is just the name, not type:name
  // ...
})),
```

---

## Implementation Order

| Order | Bug | Phase | Dependencies | Assignee |
|-------|-----|-------|--------------|----------|
| 1 | Bug 1 | Phase 1 | None | python-backend-engineer |
| 2 | Bug 2 | Phase 2 | None (can parallel) | python-backend-engineer |
| 3 | Bug 3 | Phase 3 | Bugs 1 & 2 (to verify) | Investigation first |

---

## Testing Strategy

### Unit Tests

#### Bug 1 Tests
```python
def test_validate_single_file_command():
    """Commands as single .md files should pass validation."""
    artifact = BulkImportArtifactData(
        source="local/command/test-cmd",
        artifact_type="command",
        name="test-cmd",
        path="/path/to/test-cmd.md",
    )
    result = importer._validate_artifact_structure(artifact)
    assert result is None  # None means valid

def test_validate_single_file_agent():
    """Agents as single .md files should pass validation."""
    artifact = BulkImportArtifactData(
        source="local/agent/test-agent",
        artifact_type="agent",
        name="test-agent",
        path="/path/to/test-agent.md",
    )
    result = importer._validate_artifact_structure(artifact)
    assert result is None

def test_validate_skill_requires_directory():
    """Skills must be directories."""
    artifact = BulkImportArtifactData(
        source="local/skill/test-skill",
        artifact_type="skill",
        name="test-skill",
        path="/path/to/test-skill.md",  # File, not directory
    )
    result = importer._validate_artifact_structure(artifact)
    assert result is not None
    assert "not a directory" in result.error
```

#### Bug 2 Tests
```python
def test_check_artifact_exists_file_based():
    """File-based artifacts should be detected correctly."""
    # Create test command file
    cmd_path = tmp_path / ".claude" / "commands" / "test-cmd.md"
    cmd_path.parent.mkdir(parents=True)
    cmd_path.write_text("---\nname: test-cmd\n---\n# Command")

    service = ArtifactDiscoveryService(tmp_path)
    result = service.check_artifact_exists("command:test-cmd")

    assert result["exists_in_project"] is True
    assert result["location"] == "project"

def test_check_artifact_exists_nested_command():
    """Nested commands should be detected."""
    cmd_path = tmp_path / ".claude" / "commands" / "analyze" / "symbols" / "query.md"
    cmd_path.parent.mkdir(parents=True)
    cmd_path.write_text("---\nname: query\n---\n# Command")

    service = ArtifactDiscoveryService(tmp_path)
    result = service.check_artifact_exists("command:query")

    assert result["exists_in_project"] is True
```

### Integration Tests

1. **End-to-end import of command**
   - Discover command in project
   - Import via bulk import
   - Verify success status
   - Verify deployed to project

2. **Status consistency test**
   - Deploy artifact from collection
   - Run discovery
   - Verify NOT shown as "New"
   - Verify correct "in_collection" status

### Manual Testing

1. Run discovery on project with multiple artifact types
2. Verify commands and agents appear correctly
3. Import a command - should succeed
4. Re-run discovery - command should show as already imported

---

## Rollback Plan

If issues arise after deployment:

1. **Bug 1 rollback**: Revert `importer.py` changes - skills will still work
2. **Bug 2 rollback**: Revert `discovery.py` changes - status may be inaccurate but functional
3. Both fixes are isolated and don't affect other functionality

---

## Success Criteria

- [ ] Commands import successfully (no "not a directory" error)
- [ ] Agents import successfully
- [ ] Skills continue to work as before
- [ ] Deployed artifacts show correct status in discovery
- [ ] No "already exists" errors for artifacts shown as "New"
- [ ] Nested commands (e.g., `analyze/symbols/query`) import correctly
- [ ] All existing tests pass
- [ ] New tests added for file-based artifact handling

---

## Related Files

| File | Purpose |
|------|---------|
| `skillmeat/core/importer.py` | Bulk import validation |
| `skillmeat/core/discovery.py` | Artifact discovery service |
| `skillmeat/core/validation.py` | Name validation rules |
| `skillmeat/core/artifact_detection.py` | Artifact signatures (source of truth) |
| `skillmeat/api/routers/artifacts.py` | API endpoints |
| `skillmeat/web/app/projects/[id]/page.tsx` | Frontend import handling |
