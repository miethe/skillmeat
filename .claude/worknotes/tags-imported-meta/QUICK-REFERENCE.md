# Quick Reference: Origin Fields Implementation

## TL;DR

**Both `origin` and `origin_source` fields are fully implemented and correctly flow through the entire pipeline from marketplace import to API response.**

---

## Where Are They Set?

| Location | File | Line | Code |
|----------|------|------|------|
| **Import** | `import_coordinator.py` | 404, 413 | `origin="marketplace"`, `origin_source="github"` |
| **TOML** | `artifact.py` | 177, 202 | `to_dict()` includes both fields |
| **Validation** | `artifact.py` | 144-161 | `__post_init__()` enforces valid combinations |
| **API Response** | `routers/artifacts.py` | 542-543 | `artifact_to_response()` passes both fields |
| **Schema** | `schemas/artifacts.py` | 187-195 | `ArtifactResponse` defines both fields |

---

## Valid Value Combinations

```
Scenario 1: Marketplace Import
  origin = "marketplace"
  origin_source = "github"
  ✅ VALID

Scenario 2: Direct GitHub Add
  origin = "github"
  origin_source = None
  ✅ VALID

Scenario 3: Local Artifact
  origin = "local"
  origin_source = None
  ✅ VALID

Scenario 4: INVALID (mixing)
  origin = "github"
  origin_source = "github"
  ❌ INVALID - origin_source only allowed with marketplace
```

---

## How to Verify Implementation

### 1. Check Artifact Model
```bash
# File: skillmeat/core/artifact.py
grep -n "origin" skillmeat/core/artifact.py | head -20
```

Expected output includes:
- Line 101: `origin: str  # "local", "github", or "marketplace"`
- Line 111: `origin_source: Optional[str] = None`

### 2. Check Serialization
```bash
# File: skillmeat/core/artifact.py
sed -n '171,204p' skillmeat/core/artifact.py | grep -E "origin|origin_source"
```

Expected output:
- `"origin": self.origin` (line 177)
- `if self.origin_source is not None:` (line 201)

### 3. Check Import Flow
```bash
# File: skillmeat/core/marketplace/import_coordinator.py
sed -n '400,414p' skillmeat/core/marketplace/import_coordinator.py | grep -E "origin|origin_source"
```

Expected output:
- `origin="marketplace",` (line 404)
- `origin_source="github",` (line 413)

### 4. Check API Response
```bash
# File: skillmeat/api/routers/artifacts.py
sed -n '537,551p' skillmeat/api/routers/artifacts.py | grep -E "origin|origin_source"
```

Expected output:
- `origin=artifact.origin,` (line 542)
- `origin_source=artifact.origin_source,` (line 543)

### 5. Check API Schema
```bash
# File: skillmeat/api/schemas/artifacts.py
sed -n '187,195p' skillmeat/api/schemas/artifacts.py
```

Expected output includes both fields in ArtifactResponse definition

---

## Data Flow Checklist

- [x] Step 1: ImportCoordinator creates Artifact with origin="marketplace", origin_source="github"
- [x] Step 2: Artifact.to_dict() serializes both fields to dict
- [x] Step 3: Manifest writes dict to TOML file
- [x] Step 4: Artifact.from_dict() deserializes from TOML
- [x] Step 5: __post_init__() validates the fields
- [x] Step 6: Collection loads artifact with both fields intact
- [x] Step 7: artifact_to_response() passes both to ArtifactResponse
- [x] Step 8: ArtifactResponse schema defines both fields
- [x] Step 9: Pydantic serializes to JSON with both fields
- [x] Step 10: API returns JSON with origin and origin_source

---

## Common Issues & Solutions

### Issue: origin_source is `null` in response

**Cause**: Artifact was imported before origin_source field was added

**Solution**:
```bash
# Option 1: Re-import the artifact
skillmeat import <marketplace-source>

# Option 2: Edit manifest.toml manually
# Add: origin_source = "github"
```

### Issue: origin shows wrong value

**Cause**: Artifact created with incorrect origin value

**Solution**:
```bash
# Check manifest.toml directly
cat ~/.skillmeat/collection/manifest.toml

# Verify the origin value for your artifact
# If wrong, either:
# 1. Delete and re-import
# 2. Edit manifest.toml and save
```

### Issue: Validation error on artifact creation

**Cause**: Invalid combination of origin and origin_source

**Solution**:
```python
# Valid combinations only:
# origin="marketplace" + origin_source="github"    ✅
# origin="github" + origin_source=None             ✅
# origin="local" + origin_source=None              ✅

# Invalid combinations:
# origin="github" + origin_source="github"         ❌
# origin="local" + origin_source="github"          ❌
```

---

## Testing Commands

### List all imported artifacts
```bash
skillmeat list --origin marketplace
```

### Check manifest directly
```bash
cat ~/.skillmeat/collection/manifest.toml | grep -A 3 "origin = "
```

### Test API response
```bash
curl http://localhost:8000/api/v1/artifacts/skill:pdf | jq '.origin, .origin_source'
```

Expected output:
```json
"marketplace"
"github"
```

---

## Code Locations (Absolute Paths)

```
Core Model:
  /Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py
  Lines 94-111:   Model definition
  Lines 171-204:  Serialization (to_dict)
  Lines 206-237:  Deserialization (from_dict)
  Lines 113-162:  Validation (__post_init__)

Marketplace Import:
  /Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/import_coordinator.py
  Lines 400-414:  Artifact creation with origin fields

API Layer:
  /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py
  Lines 473-552:  artifact_to_response() function
  Lines 542-543:  origin and origin_source assignment

API Schema:
  /Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/artifacts.py
  Lines 187-195:  ArtifactResponse field definitions
```

---

## Field Specifications

### origin
- **Required**: Yes
- **Type**: String
- **Valid Values**:
  - `"local"` - Created locally
  - `"github"` - Added directly from GitHub
  - `"marketplace"` - Imported from marketplace
- **Stored In**: manifest.toml
- **In API Response**: Yes, as `origin`

### origin_source
- **Required**: Only when origin="marketplace"
- **Type**: String or null
- **Valid Values** (if not null):
  - `"github"` - GitHub-based marketplace
  - `"gitlab"` - GitLab-based marketplace
  - `"bitbucket"` - Bitbucket-based marketplace
- **Stored In**: manifest.toml (omitted if null)
- **In API Response**: Yes, as `origin_source` (null if not set)

---

## Integration Points

### When Creating Artifact Programmatically
```python
from skillmeat.core.artifact import Artifact, ArtifactType
from datetime import datetime

artifact = Artifact(
    name="my-skill",
    type=ArtifactType.SKILL,
    path="skills/my-skill",
    origin="marketplace",          # Required
    origin_source="github",        # Set if origin="marketplace"
    metadata=ArtifactMetadata(...),
    added=datetime.utcnow(),
    upstream="https://github.com/...",
    version_spec="latest",
)
# Validation happens in __post_init__()
```

### When Querying Artifacts
```python
artifacts = collection.artifacts

# Filter by origin
marketplace_artifacts = [a for a in artifacts if a.origin == "marketplace"]

# Get source details
for artifact in marketplace_artifacts:
    print(f"{artifact.name}: from {artifact.origin_source}")
```

### When Building API Responses
```python
# artifact_to_response() automatically includes both fields
response = artifact_to_response(artifact)
# response.origin = "marketplace"
# response.origin_source = "github"
```

---

## Manifest Example

```toml
[[artifacts]]
name = "pdf-processor"
type = "skill"
path = "skills/pdf-processor"
origin = "marketplace"
origin_source = "github"
upstream = "https://github.com/anthropics/skills/tree/main/pdf-processor"
version_spec = "latest"
added = "2025-01-21T10:00:00+00:00"
tags = ["pdf", "document-processing"]

[artifacts.metadata]
title = "PDF Processor"
description = "Process and analyze PDF documents"
```

---

## Summary

| Aspect | Status | Evidence |
|--------|--------|----------|
| Fields defined in model | ✅ | artifact.py lines 101, 111 |
| Serialized to TOML | ✅ | artifact.py lines 177, 202 |
| Deserialized from TOML | ✅ | artifact.py lines 226, 236 |
| Validated on creation | ✅ | artifact.py lines 144-161 |
| Set during import | ✅ | import_coordinator.py lines 404, 413 |
| Included in API response | ✅ | routers/artifacts.py lines 542-543 |
| Defined in API schema | ✅ | schemas/artifacts.py lines 187-195 |
| Present in JSON response | ✅ | Pydantic serialization |

**Conclusion**: Fields are fully implemented end-to-end. ✅

