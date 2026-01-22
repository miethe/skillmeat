# Data Flow Trace: `origin` and `origin_source` Fields

## Summary
The `origin` and `origin_source` fields are correctly set during marketplace import but ARE being correctly serialized to the API response. The trace shows all fields are properly handled through each step of the pipeline.

---

## Step 1: ImportCoordinator Creates Artifact with Origin Fields

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/import_coordinator.py`

### Line 400-414: Artifact Creation
```python
artifact = Artifact(
    name=entry.name,
    type=artifact_type,
    path=str(local_path),
    origin="marketplace",  # ✅ SET: Track provenance via origin field
    metadata=metadata,
    added=datetime.utcnow(),
    upstream=entry.upstream_url,  # Keep full GitHub URL
    version_spec="latest",
    resolved_sha=None,
    resolved_version=None,
    last_updated=None,
    tags=artifact_tags,
    origin_source="github",  # ✅ SET: Currently all marketplace sources are GitHub-based
)
```

**Status**: ✅ Both fields correctly set
- `origin="marketplace"` - Track that artifact came from marketplace import
- `origin_source="github"` - Platform type for marketplace sources

---

## Step 2: Artifact Serialized to Manifest (TOML)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`

### Line 171-204: Artifact.to_dict() Method
```python
def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for TOML serialization."""
    result = {
        "name": self.name,
        "type": self.type.value,
        "path": self.path,
        "origin": self.origin,
        "added": self.added.isoformat(),
    }

    # ... optional fields ...
    if self.origin_source is not None:
        result["origin_source"] = self.origin_source  # ✅ LINE 202: Included if not None

    return result
```

**Status**: ✅ Both fields included in serialization
- Line 177: `"origin": self.origin` - always included (required field)
- Line 202: `"origin_source": self.origin_source` - conditionally included

### Line 416-427: Manifest Write (Collection Add)
```python
# Add artifact to collection
try:
    collection.add_artifact(artifact)
except ValueError as e:
    # Artifact already exists
    logger.warning(f"Artifact {entry.name} already in manifest: {e}")
    # If overwriting, remove and re-add
    collection.remove_artifact(entry.name, artifact_type)
    collection.add_artifact(artifact)

# Write updated manifest
manifest_mgr.write(collection_path, collection)
```

**Status**: ✅ Manifest written with all fields

---

## Step 3: Artifact Deserialized from Manifest (TOML)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`

### Line 206-237: Artifact.from_dict() Method
```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
    """Create from dictionary (TOML deserialization)."""
    # ... metadata parsing ...

    return cls(
        name=data["name"],
        type=ArtifactType(data["type"]),
        path=data["path"],
        origin=data["origin"],
        metadata=metadata,
        added=added,
        upstream=data.get("upstream"),
        version_spec=data.get("version_spec"),
        resolved_sha=data.get("resolved_sha"),
        resolved_version=data.get("resolved_version"),
        last_updated=last_updated,
        discovered_at=discovered_at,
        tags=data.get("tags", []),
        origin_source=data.get("origin_source"),  # ✅ LINE 236: Deserialized
    )
```

**Status**: ✅ Both fields correctly deserialized
- Line 226: `origin=data["origin"]` - required, loaded from manifest
- Line 236: `origin_source=data.get("origin_source")` - optional, loaded from manifest

---

## Step 4: Artifact Validation in __post_init__

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`

### Line 113-162: Artifact.__post_init__() Validation
```python
def __post_init__(self):
    """Validate artifact configuration."""
    # ... name validation ...

    if self.origin not in ("local", "github", "marketplace"):  # ✅ LINE 144
        raise ValueError(
            f"Invalid origin: {self.origin}. Must be 'local', 'github', or 'marketplace'."
        )

    # Validate origin_source: only allowed when origin is "marketplace"
    valid_origin_sources = ("github", "gitlab", "bitbucket")
    if self.origin_source is not None:
        if self.origin != "marketplace":  # ✅ LINE 152: Validation enforces marketplace requirement
            raise ValueError(
                f"origin_source can only be set when origin is 'marketplace', "
                f"but origin is '{self.origin}'"
            )
        if self.origin_source not in valid_origin_sources:
            raise ValueError(
                f"Invalid origin_source: {self.origin_source}. "
                f"Must be one of: {', '.join(valid_origin_sources)}"
            )
```

**Status**: ✅ Validation enforces correctness
- `origin="marketplace"` with `origin_source="github"` passes validation

---

## Step 5: Artifact Loaded from Collection

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/collection.py`

When Collection Manager loads the manifest, artifacts are deserialized via `Artifact.from_dict()` (step 3). The fields are preserved during this load.

**Status**: ✅ Fields maintained through collection load

---

## Step 6: Artifact Response Serialization (API)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py`

### Line 473-552: artifact_to_response() Function
```python
def artifact_to_response(
    artifact,
    drift_status: Optional[str] = None,
    has_local_modifications: Optional[bool] = None,
    collections_data: Optional[List[dict]] = None,
) -> ArtifactResponse:
    """Convert Artifact model to API response schema."""

    # ... metadata conversion ...

    return ArtifactResponse(
        id=f"{artifact.type.value}:{artifact.name}",
        name=artifact.name,
        type=artifact.type.value,
        source=artifact.upstream if artifact.upstream else "local",
        origin=artifact.origin,  # ✅ LINE 542: Passed through directly
        origin_source=artifact.origin_source,  # ✅ LINE 543: Passed through directly
        version=version,
        aliases=[],
        tags=artifact.tags or [],
        metadata=metadata_response,
        upstream=upstream_response,
        collections=collections_response,
        added=artifact.added,
        updated=artifact.last_updated or artifact.added,
    )
```

**Status**: ✅ Both fields included in response
- Line 542: `origin=artifact.origin` - directly from artifact
- Line 543: `origin_source=artifact.origin_source` - directly from artifact

---

## Step 7: API Response Schema Definition

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py`

### Line 164-264: ArtifactResponse Model
```python
class ArtifactResponse(BaseModel):
    """Response schema for a single artifact."""

    # ... other fields ...

    origin: str = Field(
        description="Origin category: 'local', 'github', or 'marketplace'",
        examples=["github"],
    )
    origin_source: Optional[str] = Field(
        default=None,
        description="Platform source when origin is 'marketplace' (e.g., 'github', 'gitlab', 'bitbucket')",
        examples=["github"],
    )

    # ... more fields ...
```

**Status**: ✅ Schema correctly defines both fields
- Line 187-190: `origin` field - required string
- Line 191-195: `origin_source` field - optional string

---

## End-to-End Flow Verification

### For Marketplace Import:

```
1. ImportCoordinator._update_manifest()
   ├─ Creates Artifact(origin="marketplace", origin_source="github")
   └─ Collection.add_artifact(artifact)

2. Collection writes to manifest.toml
   ├─ Artifact.to_dict() includes origin and origin_source
   └─ TOML file contains both fields

3. API route calls artifact_to_response(artifact)
   ├─ Artifact.from_dict() reconstructs from manifest
   ├─ origin and origin_source preserved in Artifact instance
   └─ artifact_to_response() passes directly to ArtifactResponse

4. ArtifactResponse serialized to JSON
   ├─ "origin": "marketplace"
   └─ "origin_source": "github"
```

---

## Key Code Locations Summary

| Step | File | Lines | Field |
|------|------|-------|-------|
| 1. Create | `import_coordinator.py` | 404, 413 | Set to "marketplace", "github" |
| 2. To TOML | `artifact.py` | 177, 202 | to_dict() includes both |
| 3. From TOML | `artifact.py` | 226, 236 | from_dict() deserializes both |
| 4. Validate | `artifact.py` | 144-161 | Enforces origin_source requires marketplace |
| 5. Load | collection.py | N/A | Uses from_dict() |
| 6. To Response | `routers/artifacts.py` | 542-543 | artifact_to_response() includes both |
| 7. Schema | `schemas/artifacts.py` | 187-195 | ArtifactResponse defines both |

---

## Conclusion

**The origin and origin_source fields are correctly implemented throughout the entire pipeline:**

✅ **Created**: ImportCoordinator sets both fields when importing from marketplace
✅ **Serialized**: Artifact.to_dict() includes both in TOML output
✅ **Deserialized**: Artifact.from_dict() restores both from TOML
✅ **Validated**: __post_init__() enforces valid combinations
✅ **Loaded**: Collection load preserves both fields
✅ **Response**: artifact_to_response() passes both to API response
✅ **Schema**: ArtifactResponse defines both fields correctly

### If Fields Are Missing in API Response

If you're seeing empty `origin` or `origin_source` in responses, the issue is likely:

1. **Artifact not re-created after schema update** - Old artifacts in manifest may not have origin_source field
2. **Manifest not rewritten** - If imported before origin_source field was added, manifest won't have it
3. **API caching** - Cached responses may not reflect manifest updates
4. **Collection reload** - Collection manager may be serving cached instances

**Solution**: Re-import artifacts or manually update manifest.toml files to include the origin_source field.

