---
title: Collection Management Patterns & Examples
description: Code patterns, common operations, and examples for working with SkillMeat collections
references:
  - skillmeat/core/collection.py
  - skillmeat/api/routers/user_collections.py
last_verified: 2026-01-11
---

# Collection Management Patterns

## Pattern 1: Initialize & Manage Collections

### Initialize a New Collection

```python
from skillmeat.core.collection import CollectionManager

manager = CollectionManager()
collection = manager.init(name="default")
# Creates: ~/.skillmeat/collection/
#          ├── collection.toml
#          ├── collection.lock
#          ├── skills/
#          ├── commands/
#          └── agents/
```

### Load & Save Collection

```python
manager = CollectionManager()

# Load active collection
collection = manager.load_collection()

# Load specific collection
collection = manager.load_collection("my-collection")

# Make changes
from skillmeat.core.artifact import Artifact, ArtifactMetadata
artifact = Artifact(
    name="my-skill",
    type=ArtifactType.SKILL,
    path="skills/my-skill/",
    origin="local",
    metadata=ArtifactMetadata(title="My Skill"),
    added=datetime.utcnow()
)
collection.add_artifact(artifact)

# Save back to disk (atomic write)
manager.save_collection(collection)
```

### List & Switch Collections

```python
manager = CollectionManager()

# List all collections
names = manager.list_collections()
# → ["default", "work", "experiments"]

# Get active
active = manager.get_active_collection_name()
# → "default"

# Switch
manager.switch_collection("work")
```

---

## Pattern 2: Working with Artifacts

### Find Artifact by Name

```python
collection = manager.load_collection()

# Find by name
artifact = collection.find_artifact("canvas-design")
# → Artifact(...) or None

# Find by name and type (more precise)
artifact = collection.find_artifact("canvas-design", ArtifactType.SKILL)
# → Artifact(...) or None

# Ambiguity detection
try:
    artifact = collection.find_artifact("my-item")  # exists as skill AND command
except ValueError as e:
    print(e)  # "Ambiguous artifact name... Please specify type explicitly"
```

### Add Artifact with Duplicate Check

```python
collection = manager.load_collection()

artifact = Artifact(
    name="canvas-design",
    type=ArtifactType.SKILL,
    path="skills/canvas-design/",
    origin="github",
    metadata=ArtifactMetadata(title="Canvas Design"),
    added=datetime.utcnow(),
    upstream="anthropics/skills/canvas-design"
)

try:
    collection.add_artifact(artifact)
except ValueError as e:
    print(e)  # "Artifact 'canvas-design' of type 'skill' already exists"
```

### Remove Artifact

```python
collection = manager.load_collection()

removed = collection.remove_artifact("canvas-design", ArtifactType.SKILL)
if removed:
    manager.save_collection(collection)
    print("Removed successfully")
else:
    print("Artifact not found")
```

---

## Pattern 3: Membership Checking (API Use)

### Check Single Artifact

```python
manager = CollectionManager()

# Single check with priority matching
in_coll, matched_id, match_type = manager.artifact_in_collection(
    name="canvas-design",
    artifact_type="skill",
    source_link="anthropics/skills/canvas-design",
    collection_name="default"
)

match match_type:
    case "exact":
        print(f"Exact source match: {matched_id}")
    case "hash":
        print(f"Content hash match: {matched_id}")
    case "name_type":
        print(f"Name+type match: {matched_id}")
    case "none":
        print("Not in collection")
```

### Batch Membership Check (Optimized)

```python
manager = CollectionManager()

# Build index once (O(m) where m = collection size)
index = manager.get_collection_membership_index()

artifacts = [
    {"name": "skill-1", "artifact_type": "skill", "source_link": "user/repo/skill-1"},
    {"name": "skill-2", "artifact_type": "skill", "source_link": "user/repo/skill-2"},
    # ... 100+ more
]

# Check all (O(n) where n = artifacts)
results = manager.check_membership_batch(artifacts)
# → [(True, "skill:skill-1", "exact"), (False, None, "none"), ...]
```

### Access Index Directly (Advanced)

```python
index = manager.get_collection_membership_index()

# Fast O(1) lookups
by_source = index["by_source"]  # Dict: source_normalized → artifact_id
by_hash = index["by_hash"]      # Dict: content_hash → artifact_id
by_name_type = index["by_name_type"]  # Dict: (name_lower, type_lower) → artifact_id

# Example: Check by source
source = "anthropics/skills/canvas-design".lower()
if source in by_source:
    artifact_id = by_source[source]
    print(f"Found: {artifact_id}")
```

---

## Pattern 4: Duplicate Linking

### Link Discovered Artifact to Collection

```python
manager = CollectionManager()

# User has artifact deployed locally, want to link to collection copy
success = manager.link_duplicate(
    discovered_path="/Users/me/.claude/skills/my-canvas",
    collection_artifact_id="skill:canvas-design",  # format: type:name
    collection_name="default"
)

if success:
    print("Linked successfully")
```

### Get Duplicate Links

```python
manager = CollectionManager()

links = manager.get_duplicate_links(
    collection_artifact_id="skill:canvas-design"
)
# → ["/Users/me/.claude/skills/my-canvas", "/Users/me/work/.claude/skills/canvas"]
```

### Remove Duplicate Link

```python
manager = CollectionManager()

removed = manager.remove_duplicate_link(
    discovered_path="/Users/me/.claude/skills/my-canvas",
    collection_artifact_id="skill:canvas-design"
)

if removed:
    print("Link removed")
```

---

## Pattern 5: Database Collections (API)

### Create Collection

```python
from skillmeat.cache.models import Collection, get_session
from datetime import datetime

session = get_session()

collection = Collection(
    name="My Context",
    description="Collection for project context files",
    created_by="user123",
    collection_type="context",
    context_category="rules",
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)

session.add(collection)
session.commit()
```

### Create Group (organization within collection)

```python
from skillmeat.cache.models import Group

group = Group(
    collection_id="abc123def456",  # from collection.id
    name="Project Setup",
    description="Initial setup artifacts",
    position=0,
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)

session.add(group)
session.commit()
```

### Add Artifacts to Collection

```python
from skillmeat.cache.models import CollectionArtifact

# Add to collection
collection_artifact = CollectionArtifact(
    collection_id="abc123def456",
    artifact_id="skill:canvas-design",
    added_at=datetime.utcnow()
)

session.add(collection_artifact)
session.commit()
```

### Add Artifacts to Group with Order

```python
from skillmeat.cache.models import GroupArtifact

# Add to group with position
group_artifact = GroupArtifact(
    group_id="group123",
    artifact_id="skill:canvas-design",
    position=0,  # First in group
    added_at=datetime.utcnow()
)

session.add(group_artifact)
session.commit()
```

### Query Collections

```python
# Get all collections
collections = session.query(Collection).all()

# Get with filters
context_collections = session.query(Collection).filter(
    Collection.collection_type == "context"
).all()

# Get single
collection = session.query(Collection).filter_by(id="abc123").first()

# Get with relationships loaded
collection = session.query(Collection).filter_by(id="abc123").first()
for group in collection.groups:
    print(f"Group: {group.name}")
    for artifact in group.group_artifacts:
        print(f"  - {artifact.artifact_id}")
```

### Query Artifacts in Collection

```python
from sqlalchemy import func

# Count artifacts in collection
count = session.query(CollectionArtifact).filter_by(
    collection_id="abc123"
).count()

# List artifacts
artifacts = session.query(CollectionArtifact).filter_by(
    collection_id="abc123"
).all()
```

---

## Pattern 6: API Response Conversion

### Convert ORM to Response DTO

```python
from skillmeat.api.routers.user_collections import (
    collection_to_response,
    collection_to_response_with_groups
)

# Basic response
response = collection_to_response(collection, session)
# Returns: UserCollectionResponse(
#   id, name, description, created_by,
#   group_count, artifact_count, created_at, updated_at
# )

# With nested groups
response = collection_to_response_with_groups(collection, session)
# Returns: UserCollectionWithGroupsResponse(
#   ... + groups: List[GroupSummary]
# )
```

---

## Pattern 7: Pagination

### Cursor-Based Pagination

```python
import base64

def encode_cursor(value: str) -> str:
    return base64.b64encode(value.encode()).decode()

def decode_cursor(cursor: str) -> str:
    return base64.b64decode(cursor.encode()).decode()

# In list endpoint
limit = 20
after = "abc123"  # cursor from user

all_collections = session.query(Collection).order_by(Collection.id).all()

# Decode cursor to get start index
if after:
    try:
        start_id = decode_cursor(after)
        all_collections = [c for c in all_collections if c.id >= start_id]
    except:
        raise HTTPException(400, "Invalid cursor format")

# Get page
page = all_collections[:limit]
next_cursor = None
if len(all_collections) > limit:
    next_cursor = encode_cursor(page[-1].id)

# Response
return UserCollectionListResponse(
    items=[collection_to_response(c, session) for c in page],
    page_info=PageInfo(after=after, next_cursor=next_cursor)
)
```

---

## Pattern 8: Error Handling

### File-Based Collection Errors

```python
from skillmeat.core.collection import CollectionManager

manager = CollectionManager()

try:
    # Non-existent collection
    collection = manager.load_collection("missing")
except ValueError as e:
    print(f"Not found: {e}")

try:
    # Invalid artifact
    artifact = Artifact(name="", type=ArtifactType.SKILL, ...)
except ValueError as e:
    print(f"Invalid: {e}")

try:
    # Duplicate artifact
    collection.add_artifact(same_artifact_twice)
except ValueError as e:
    print(f"Duplicate: {e}")

try:
    # Ambiguous name
    artifact = collection.find_artifact("ambiguous-name")
except ValueError as e:
    print(f"Ambiguous: {e}")
```

### Database Errors

```python
from sqlalchemy.exc import IntegrityError

session = get_session()

try:
    group = Group(
        collection_id="abc",
        name="My Group",
        position=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(group)
    session.commit()
except IntegrityError as e:
    session.rollback()
    if "uq_group_collection_name" in str(e):
        raise HTTPException(422, "Group name already exists in collection")
```

---

## Pattern 9: Security Validation

### Artifact Name Validation

```python
def validate_artifact_name(name: str):
    if not name:
        raise ValueError("Name cannot be empty")
    if "/" in name or "\\" in name:
        raise ValueError("Name cannot contain path separators")
    if ".." in name:
        raise ValueError("Name cannot contain parent directory references")
    if name.startswith("."):
        raise ValueError("Name cannot start with '.'")
    return name

# Usage
name = validate_artifact_name(user_input)
artifact = Artifact(name=name, ...)
```

### Collection Access Control (Future)

```python
# When multi-user support added:
def verify_collection_access(collection_id: str, user_id: str, session: Session):
    collection = session.query(Collection).filter_by(id=collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")
    if collection.created_by != user_id:
        raise HTTPException(403, "Not authorized")
    return collection
```

---

## Pattern 10: Testing

### Unit Test: Add Artifact

```python
from pathlib import Path
import tempfile
from skillmeat.core.collection import Collection, Artifact, ArtifactType, ArtifactMetadata
from datetime import datetime

def test_add_artifact():
    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=[],
        created=datetime.utcnow(),
        updated=datetime.utcnow()
    )

    artifact = Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill/",
        origin="local",
        metadata=ArtifactMetadata(title="Test"),
        added=datetime.utcnow()
    )

    collection.add_artifact(artifact)
    assert len(collection.artifacts) == 1
    assert collection.artifacts[0].name == "test-skill"

    # Test duplicate check
    with pytest.raises(ValueError):
        collection.add_artifact(artifact)
```

### Integration Test: Manifest Round-trip

```python
def test_manifest_roundtrip(tmp_path: Path):
    manifest_mgr = ManifestManager()

    # Create
    collection = manifest_mgr.create_empty(tmp_path, "test")
    assert (tmp_path / "collection.toml").exists()

    # Modify
    artifact = Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill/",
        origin="local",
        metadata=ArtifactMetadata(title="Test"),
        added=datetime.utcnow()
    )
    collection.add_artifact(artifact)

    # Save
    manifest_mgr.write(tmp_path, collection)

    # Load back
    loaded = manifest_mgr.read(tmp_path)
    assert len(loaded.artifacts) == 1
    assert loaded.artifacts[0].name == "test-skill"
```

---

## Quick Reference: Key Methods

| Class | Method | Returns |
|-------|--------|---------|
| CollectionManager | init(name) | Collection |
| CollectionManager | load_collection(name) | Collection |
| CollectionManager | save_collection(collection) | None |
| CollectionManager | artifact_in_collection(...) | (bool, str, str) |
| CollectionManager | check_membership_batch(...) | List[tuple] |
| Collection | find_artifact(name, type) | Artifact \| None |
| Collection | add_artifact(artifact) | None |
| Collection | remove_artifact(name, type) | bool |
| ManifestManager | read(path) | Collection |
| ManifestManager | write(path, collection) | None |
| LockManager | read(path) | Dict[(str, str), LockEntry] |
| LockManager | write(path, entries) | None |

