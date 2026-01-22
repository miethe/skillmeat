# Origin Fields Data Flow Diagram

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MARKETPLACE IMPORT FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

STEP 1: IMPORT COORDINATOR (import_coordinator.py:400-414)
═════════════════════════════════════════════════════════════════════════════

Entry Data                 │  Create Artifact Object
from Catalog:              │
  - name                   │  artifact = Artifact(
  - artifact_type    ──┐   │    name="pdf",
  - upstream_url     ──┼─→ │    type=skill,
  - description      ──┤   │    path="skills/pdf",
  - tags             ──┘   │    origin="marketplace",      ✅ SET LINE 404
                           │    origin_source="github",    ✅ SET LINE 413
                           │    metadata=metadata,
                           │    upstream=upstream_url,
                           │    version_spec="latest",
                           │    ...
                           │  )


STEP 2: ADD TO COLLECTION (import_coordinator.py:416-427)
═════════════════════════════════════════════════════════════════════════════

Artifact Instance          │  Collection Manifest Write
with origin fields ───────→ │
                           │  collection.add_artifact(artifact)
                           │         ↓
                           │  manifest_mgr.write(collection_path, collection)


STEP 3: SERIALIZE TO TOML (artifact.py:171-204)
═════════════════════════════════════════════════════════════════════════════

Artifact.to_dict() called:

Field              │ Line │ Status           │ TOML Output
───────────────────┼──────┼──────────────────┼─────────────────────────
name               │ 174  │ Always included  │ name = "pdf"
type               │ 175  │ Always included  │ type = "skill"
path               │ 176  │ Always included  │ path = "skills/pdf"
origin             │ 177  │ Always included  │ origin = "marketplace"  ✅
origin_source      │ 202  │ If not None      │ origin_source = "github" ✅
upstream           │ 188  │ If not None      │ upstream = "https://..."
version_spec       │ 189  │ If not None      │ version_spec = "latest"
resolved_sha       │ 191  │ If not None      │ resolved_sha = null
tags               │ 199  │ If not empty     │ tags = [...]
metadata           │ 183  │ If present       │ [metadata] table

Result in manifest.toml:
┌────────────────────────────────────────┐
│ [[artifacts]]                          │
│ name = "pdf"                           │
│ type = "skill"                         │
│ path = "skills/pdf"                    │
│ origin = "marketplace"        ✅       │
│ origin_source = "github"      ✅       │
│ upstream = "https://..."               │
│ version_spec = "latest"                │
│                                        │
│ [artifacts.metadata]                   │
│ title = "PDF Processor"                │
│ ...                                    │
└────────────────────────────────────────┘


STEP 4: DESERIALIZE FROM TOML (artifact.py:206-237)
═════════════════════════════════════════════════════════════════════════════

When loading artifact from manifest:

Artifact.from_dict(data) called:

Field              │ Line │ Source              │ Status
───────────────────┼──────┼─────────────────────┼──────────────
name               │ 223  │ data["name"]        │ ✅ Required
type               │ 224  │ data["type"]        │ ✅ Required
path               │ 225  │ data["path"]        │ ✅ Required
origin             │ 226  │ data["origin"]      │ ✅ Required
origin_source      │ 236  │ data.get("origin_source") │ ✅ Optional
upstream           │ 229  │ data.get("upstream")       │ Optional
version_spec       │ 230  │ data.get("version_spec")   │ Optional
resolved_sha       │ 231  │ data.get("resolved_sha")   │ Optional
tags               │ 235  │ data.get("tags", []) │ Optional
metadata           │ 211  │ ArtifactMetadata.from_dict() │ Optional

Deserialized Artifact Instance:
  Artifact(
    name="pdf",
    type=ArtifactType.skill,
    origin="marketplace",          ✅ RESTORED
    origin_source="github",        ✅ RESTORED
    ...
  )


STEP 5: VALIDATE (artifact.py:113-162)
═════════════════════════════════════════════════════════════════════════════

On Artifact instantiation (__post_init__):

Check                               │ Line │ Status
────────────────────────────────────┼──────┼──────────────────────
origin in ("local", "github", "marketplace") │ 144 │ ✅ PASS
                                   │      │ "marketplace" is valid
                                   │      │
origin_source validates only if    │ 151  │ ✅ PASS
origin == "marketplace"            │      │ Sets together as required
                                   │      │
origin_source in valid values      │ 157  │ ✅ PASS
("github", "gitlab", "bitbucket")  │      │ "github" is valid


STEP 6: LOAD FROM COLLECTION (collection.py)
═════════════════════════════════════════════════════════════════════════════

CollectionManager.load_collection(name):
  │
  ├─ manifest_mgr.read(collection_path)
  │    └─ Reads manifest.toml
  │         └─ For each [[artifacts]] section:
  │              └─ Artifact.from_dict(artifact_dict)
  │                   └─ Returns Artifact with origin="marketplace", origin_source="github"
  │
  └─ Collection instance created with all artifacts
       └─ Artifact instances have origin and origin_source fields intact ✅


STEP 7: API REQUEST (routers/artifacts.py)
═════════════════════════════════════════════════════════════════════════════

GET /api/v1/artifacts/{artifact_id}

Route Handler:
  artifact = artifact_mgr.show(artifact_name, artifact_type)
              │
              └─ Returns Artifact instance with:
                 - origin = "marketplace"
                 - origin_source = "github"

  response = artifact_to_response(artifact)


STEP 8: CONVERT TO RESPONSE (routers/artifacts.py:473-552)
═════════════════════════════════════════════════════════════════════════════

artifact_to_response() function:

Input: Artifact(origin="marketplace", origin_source="github")

Processing:
  Line │ Code                              │ Value Assigned
  ─────┼──────────────────────────────────┼──────────────────────────────
  538  │ id=f"{artifact.type}:{artifact.name}" │ "skill:pdf"
  539  │ name=artifact.name                │ "pdf"
  540  │ type=artifact.type.value          │ "skill"
  541  │ source=artifact.upstream or ...   │ "https://github.com/..."
  542  │ origin=artifact.origin            │ "marketplace"         ✅
  543  │ origin_source=artifact.origin_source │ "github"           ✅
  544  │ version=artifact.version_spec     │ "latest"
  545  │ aliases=[]                        │ []
  546  │ tags=artifact.tags                │ ["..."]
  547  │ metadata=metadata_response        │ ArtifactMetadataResponse(...)
  548  │ upstream=upstream_response        │ ArtifactUpstreamInfo(...)
  549  │ collections=collections_response  │ [ArtifactCollectionInfo(...)]
  550  │ added=artifact.added              │ datetime(...)
  551  │ updated=artifact.last_updated     │ datetime(...)

Result: ArtifactResponse instance created with all fields ✅


STEP 9: SERIALIZE TO JSON (schemas/artifacts.py:164-264)
═════════════════════════════════════════════════════════════════════════════

ArtifactResponse Pydantic Model Definition:

Field           │ Line │ Type            │ Default │ Required? │ In Response?
────────────────┼──────┼─────────────────┼─────────┼───────────┼─────────────
id              │ 171  │ str             │ -       │ Yes       │ ✅
name            │ 175  │ str             │ -       │ Yes       │ ✅
type            │ 179  │ str             │ -       │ Yes       │ ✅
source          │ 183  │ str             │ -       │ Yes       │ ✅
origin          │ 187  │ str             │ -       │ Yes       │ ✅ LINE 187
origin_source   │ 191  │ Optional[str]   │ None    │ No        │ ✅ LINE 191
version         │ 196  │ str             │ -       │ Yes       │ ✅
tags            │ 205  │ List[str]       │ []      │ Yes       │ ✅
metadata        │ 210  │ Optional[...]   │ None    │ No        │ ✅
upstream        │ 214  │ Optional[...]   │ None    │ No        │ ✅
collections     │ 222  │ List[...]       │ []      │ Yes       │ ✅
added           │ 226  │ datetime        │ -       │ Yes       │ ✅
updated         │ 229  │ datetime        │ -       │ Yes       │ ✅

Pydantic serialization to JSON:

{
  "id": "skill:pdf",
  "name": "pdf",
  "type": "skill",
  "source": "https://github.com/...",
  "origin": "marketplace",          ✅ INCLUDED
  "origin_source": "github",        ✅ INCLUDED
  "version": "latest",
  "aliases": [],
  "tags": ["..."],
  "metadata": { ... },
  "upstream": { ... },
  "collections": [ ... ],
  "added": "2025-01-21T10:00:00Z",
  "updated": "2025-01-21T10:00:00Z"
}


STEP 10: HTTP RESPONSE
═════════════════════════════════════════════════════════════════════════════

HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "skill:pdf",
  "name": "pdf",
  "type": "skill",
  "source": "https://github.com/user/repo/tree/main/skills/pdf",
  "origin": "marketplace",          ✅ PRESENT
  "origin_source": "github",        ✅ PRESENT
  ...
}
```

---

## Field Validation Rules

```
┌─────────────────────────────────────┐
│ ORIGIN FIELD VALIDATION             │
└─────────────────────────────────────┘

Valid Values:
  • "local"       - Artifact created locally
  • "github"      - Added directly from GitHub
  • "marketplace" - Imported from marketplace catalog


┌─────────────────────────────────────┐
│ ORIGIN_SOURCE FIELD VALIDATION      │
└─────────────────────────────────────┘

Valid Values (when origin="marketplace"):
  • "github"      - GitHub-based marketplace source
  • "gitlab"      - GitLab-based marketplace source
  • "bitbucket"   - Bitbucket-based marketplace source

Constraints:
  • Can ONLY be set when origin="marketplace"
  • Must match one of: github, gitlab, bitbucket
  • Optional (can be None if not specified)

Examples:
  ✅ origin="marketplace", origin_source="github"
  ✅ origin="github", origin_source=None
  ✅ origin="local", origin_source=None
  ❌ origin="github", origin_source="github" (violates constraint)
  ❌ origin="local", origin_source="github" (violates constraint)
```

---

## Manifest File Example

When an artifact is imported from marketplace and saved to `manifest.toml`:

```toml
# Collection metadata
version = "1.0.0"
name = "default"

# Array of artifacts
[[artifacts]]
name = "pdf-processor"
type = "skill"
path = "skills/pdf-processor"
origin = "marketplace"                    ← Indicates marketplace import
origin_source = "github"                  ← Platform source
upstream = "https://github.com/user/repo/tree/main/skills/pdf-processor"
version_spec = "latest"
added = "2025-01-21T10:00:00+00:00"
last_updated = "2025-01-21T10:00:00+00:00"
tags = ["data-processing", "pdf"]

[artifacts.metadata]
title = "PDF Processing Skill"
description = "Extract and analyze PDF documents"
author = "Anthropic"
license = "MIT"
version = "1.2.3"
```

---

## Troubleshooting Guide

### Problem: origin_source is null in API response

**Possible Causes:**
1. Artifact was imported before origin_source field was added
2. Artifact.to_dict() is not being called (using old serialization)
3. Manifest file is corrupted or was edited without origin_source

**Verification:**
```bash
# Check manifest.toml file directly
cat ~/.skillmeat/collection/manifest.toml | grep -A 5 "name = \"pdf-processor\""

# Should show:
# origin_source = "github"
```

**Fix:**
1. Re-import artifact from marketplace
2. Or manually edit manifest.toml to add: `origin_source = "github"`

### Problem: origin shows as wrong value

**Possible Causes:**
1. Artifact created with wrong origin value
2. Manifest corruption or manual editing

**Verification:**
```bash
# Load artifact in Python REPL
from skillmeat.core.artifact import Artifact
artifact = Artifact.from_dict({"origin": "marketplace", ...})
print(artifact.origin)  # Should print: marketplace
```

**Fix:**
1. Check collection manifest.toml for correct origin value
2. Validate using Artifact.__post_init__() rules

---

## Code References Quick Lookup

| Question | File | Lines |
|----------|------|-------|
| Where is origin set during import? | import_coordinator.py | 404, 413 |
| How is it serialized to TOML? | artifact.py | 177, 202 |
| How is it deserialized from TOML? | artifact.py | 226, 236 |
| How is it validated? | artifact.py | 144-161 |
| How is it sent in API response? | routers/artifacts.py | 542-543 |
| What does the API schema say about it? | schemas/artifacts.py | 187-195 |
| What are the valid values? | artifact.py | 144-161 |

