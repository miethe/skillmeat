# Origin and Origin_Source Fields: Implementation Summary

## Overview

The `origin` and `origin_source` fields are fully implemented throughout the SkillMeat data pipeline. They track artifact provenance and marketplace source platform.

---

## Field Definitions

### `origin` Field
- **Type**: Required string
- **Location**: Artifact core field
- **Valid Values**:
  - `"local"` - Created locally
  - `"github"` - Added directly from GitHub
  - `"marketplace"` - Imported from marketplace catalog
- **Purpose**: Track where the artifact came from
- **Example**: `"marketplace"`

### `origin_source` Field
- **Type**: Optional string (None if not set)
- **Location**: Artifact core field
- **Valid Values** (when origin="marketplace"):
  - `"github"` - GitHub-based marketplace source
  - `"gitlab"` - GitLab-based source
  - `"bitbucket"` - Bitbucket-based source
- **Constraints**:
  - ONLY valid when `origin="marketplace"`
  - Must be one of the valid values above
- **Purpose**: Specify which platform hosts the marketplace source
- **Example**: `"github"`

---

## Implementation Checklist

### ✅ Core Model (artifact.py)

**Dataclass Definition** (lines 94-111):
```python
@dataclass
class Artifact:
    origin: str  # "local", "github", or "marketplace"
    origin_source: Optional[str] = None  # Platform when origin="marketplace"
```

**Serialization** (lines 171-204):
```python
def to_dict(self) -> Dict[str, Any]:
    result = {
        "origin": self.origin,  # Line 177
        ...
    }
    if self.origin_source is not None:
        result["origin_source"] = self.origin_source  # Line 202
    return result
```

**Deserialization** (lines 206-237):
```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
    return cls(
        origin=data["origin"],  # Line 226
        origin_source=data.get("origin_source"),  # Line 236
        ...
    )
```

**Validation** (lines 113-162):
```python
def __post_init__(self):
    # Validate origin value (line 144)
    if self.origin not in ("local", "github", "marketplace"):
        raise ValueError(f"Invalid origin: {self.origin}")

    # Validate origin_source (lines 149-161)
    if self.origin_source is not None:
        if self.origin != "marketplace":
            raise ValueError("origin_source only allowed with marketplace")
        if self.origin_source not in ("github", "gitlab", "bitbucket"):
            raise ValueError(f"Invalid origin_source: {self.origin_source}")
```

**Status**: ✅ **COMPLETE**

---

### ✅ Marketplace Import (import_coordinator.py)

**Creation** (lines 400-414):
```python
artifact = Artifact(
    origin="marketplace",      # Line 404
    origin_source="github",    # Line 413
    ...
)
```

**Manifest Write** (lines 416-427):
```python
collection.add_artifact(artifact)
manifest_mgr.write(collection_path, collection)
```

**Status**: ✅ **COMPLETE**

---

### ✅ Manifest Storage (TOML)

**Written by**: `Artifact.to_dict()` (lines 177, 202)
**Read by**: `Artifact.from_dict()` (lines 226, 236)

**Example in manifest.toml**:
```toml
[[artifacts]]
name = "pdf-processor"
origin = "marketplace"
origin_source = "github"
...
```

**Status**: ✅ **COMPLETE**

---

### ✅ Collection Loading

**Mechanism**: When collection is loaded, artifacts are deserialized via `Artifact.from_dict()`, which preserves both origin fields.

**Status**: ✅ **COMPLETE**

---

### ✅ API Response (routers/artifacts.py)

**Conversion Function** (lines 473-552):
```python
def artifact_to_response(artifact, ...):
    return ArtifactResponse(
        origin=artifact.origin,          # Line 542
        origin_source=artifact.origin_source,  # Line 543
        ...
    )
```

**Status**: ✅ **COMPLETE**

---

### ✅ API Schema (schemas/artifacts.py)

**ArtifactResponse Definition** (lines 164-264):
```python
class ArtifactResponse(BaseModel):
    origin: str = Field(
        description="Origin category: 'local', 'github', or 'marketplace'",
        examples=["github"],
    )  # Lines 187-190

    origin_source: Optional[str] = Field(
        default=None,
        description="Platform source when origin is 'marketplace'",
        examples=["github"],
    )  # Lines 191-195
```

**Status**: ✅ **COMPLETE**

---

## Data Flow Verification

```
Import Entry → Artifact Created → to_dict() → manifest.toml
                    ↓
                  valid
                    ↓
            from_dict() → Collection → API request
                            ↓
                    artifact_to_response()
                            ↓
                    ArtifactResponse → JSON
```

### Checkpoint 1: Creation ✅
- `origin="marketplace"` set at line 404
- `origin_source="github"` set at line 413
- Validation passes at lines 144-161

### Checkpoint 2: Serialization ✅
- `to_dict()` includes "origin" at line 177
- `to_dict()` includes "origin_source" at line 202 (if not None)

### Checkpoint 3: Storage ✅
- TOML manifest contains both fields

### Checkpoint 4: Deserialization ✅
- `from_dict()` reads "origin" at line 226
- `from_dict()` reads "origin_source" at line 236

### Checkpoint 5: Collection Load ✅
- Artifacts in collection have both fields

### Checkpoint 6: API Response ✅
- `artifact_to_response()` passes origin at line 542
- `artifact_to_response()` passes origin_source at line 543

### Checkpoint 7: Schema ✅
- ArtifactResponse defines both fields
- Both fields will be in JSON response

---

## Validation Logic

### Origin Validation (artifact.py:144-146)
```
IF origin NOT IN ("local", "github", "marketplace"):
    RAISE ValueError
END IF
```

**Result for marketplace**: ✅ PASS

### Origin_Source Validation (artifact.py:149-161)
```
IF origin_source IS NOT NULL:
    IF origin ≠ "marketplace":
        RAISE ValueError("can only be set when origin is 'marketplace'")
    END IF

    IF origin_source NOT IN ("github", "gitlab", "bitbucket"):
        RAISE ValueError("must be one of: github, gitlab, bitbucket")
    END IF
END IF
```

**Result for origin="marketplace", origin_source="github"**: ✅ PASS

---

## Use Cases

### Case 1: Marketplace Import
```python
# Input
artifact = Artifact(
    origin="marketplace",
    origin_source="github",
    upstream="https://github.com/user/repo/skill",
    ...
)

# Manifest storage
origin = "marketplace"
origin_source = "github"

# API response
"origin": "marketplace",
"origin_source": "github"

# Query example
artifacts = list_artifacts()
for a in artifacts:
    if a.origin == "marketplace":
        print(f"Marketplace artifact from {a.origin_source}")
```

### Case 2: Direct GitHub Addition
```python
# Input
artifact = Artifact(
    origin="github",
    origin_source=None,  # Not set
    upstream="https://github.com/user/repo",
    ...
)

# Manifest storage
origin = "github"
# origin_source omitted (None)

# API response
"origin": "github",
"origin_source": null

# Query example
if artifact.origin == "github":
    print("Added directly from GitHub")
```

### Case 3: Local Artifact
```python
# Input
artifact = Artifact(
    origin="local",
    origin_source=None,  # Not set
    upstream=None,
    ...
)

# Manifest storage
origin = "local"
# origin_source omitted (None)

# API response
"origin": "local",
"origin_source": null

# Query example
if artifact.origin == "local":
    print("Created locally")
```

---

## Related Fields & Context

### `upstream` Field
- **Purpose**: Full GitHub URL for artifacts with origin="github" or origin="marketplace"
- **Stored**: manifest.toml
- **API**: Yes, as `source` field in response

### `version_spec` Field
- **Purpose**: Version specification ("latest", "v1.0.0", branch name)
- **Stored**: manifest.toml
- **API**: Yes, as `version` field in response

### `resolved_sha` Field
- **Purpose**: Current resolved commit SHA
- **Stored**: manifest.toml
- **API**: Yes, in upstream tracking info

### `tags` Field
- **Purpose**: User-defined tags for organization
- **Stored**: manifest.toml
- **API**: Yes, as `tags` field in response
- **Note**: Do NOT use tags for provenance - use `origin` and `origin_source` fields

---

## Manifest Backward Compatibility

### When origin_source Is Missing
If a manifest has an artifact without the `origin_source` field:

```python
# from_dict() will handle gracefully
origin_source = data.get("origin_source")  # Line 236
# Returns None if key is missing
```

**Result**: Artifact loads with `origin_source=None`

**For API Response**: Field will be `"origin_source": null`

### Migration Path
```bash
# To add origin_source to existing artifacts:
1. Reload artifact (triggers from_dict)
2. If origin="marketplace" and origin_source is None:
   - Set origin_source based on upstream URL (if GitHub)
   - Save collection
```

---

## Testing Verification

### Create Test
```python
# Test marketplace import with both fields
artifact = Artifact(
    name="test",
    type=ArtifactType.SKILL,
    path="skills/test",
    origin="marketplace",
    origin_source="github",
    metadata=ArtifactMetadata(),
    added=datetime.utcnow(),
)

assert artifact.origin == "marketplace"
assert artifact.origin_source == "github"
```

### Serialization Test
```python
data = artifact.to_dict()
assert data["origin"] == "marketplace"
assert data["origin_source"] == "github"
```

### Deserialization Test
```python
restored = Artifact.from_dict(data)
assert restored.origin == "marketplace"
assert restored.origin_source == "github"
```

### API Response Test
```python
response = artifact_to_response(artifact)
assert response.origin == "marketplace"
assert response.origin_source == "github"
```

---

## Summary Table

| Aspect | Status | File | Lines | Notes |
|--------|--------|------|-------|-------|
| **Model Definition** | ✅ | artifact.py | 94-111 | Dataclass fields defined |
| **Serialization** | ✅ | artifact.py | 171-204 | to_dict() includes both |
| **Deserialization** | ✅ | artifact.py | 206-237 | from_dict() restores both |
| **Validation** | ✅ | artifact.py | 113-162 | __post_init__() enforces rules |
| **Manifest Storage** | ✅ | (TOML) | N/A | Written via to_dict() |
| **Manifest Loading** | ✅ | (TOML) | N/A | Read via from_dict() |
| **Import Creation** | ✅ | import_coordinator.py | 400-414 | Set during marketplace import |
| **API Conversion** | ✅ | routers/artifacts.py | 473-552 | artifact_to_response() |
| **API Schema** | ✅ | schemas/artifacts.py | 164-264 | ArtifactResponse fields |
| **API Response** | ✅ | routers/artifacts.py | 542-543 | Included in JSON response |

---

## Conclusion

**Status: FULLY IMPLEMENTED ✅**

Both `origin` and `origin_source` fields are:
- ✅ Properly defined in the Artifact dataclass
- ✅ Serialized to TOML manifest with to_dict()
- ✅ Deserialized from TOML with from_dict()
- ✅ Validated in __post_init__()
- ✅ Set during marketplace import
- ✅ Included in API responses via artifact_to_response()
- ✅ Defined in ArtifactResponse schema
- ✅ Will appear in JSON responses

**If you're not seeing these fields in API responses, the issue is likely:**
1. Artifact created before fields were added (reload/re-import needed)
2. Manifest file doesn't have the fields (manual update or re-import needed)
3. API caching (clear cache)
4. Old artifact instance in memory (restart API)

