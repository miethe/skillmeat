# Composite/Plugin Artifact Quick Reference

## File Locations at a Glance

| Component | File | Key Lines |
|-----------|------|-----------|
| **Composite Detection** | skillmeat/core/artifact_detection.py | 483-490 (signatures), 716-845 (detect_artifact) |
| **Service Layer** | skillmeat/core/services/composite_service.py | 115-129 (class), 380-514 (create_skill_composite) |
| **Marketplace Detection** | skillmeat/core/marketplace/heuristic_detector.py | 550+ (detect_composites_in_tree), Signal 0 for .claude-plugin |
| **Frontend Display** | skillmeat/web/components/artifact/artifact-contains-tab.tsx | Full file (show children) |
| **API Schemas** | skillmeat/api/schemas/artifacts.py | 89-134 (LinkedArtifactReferenceSchema) |

## Key Code Snippets

### 1. Detect Artifact Type (Baseline)

```python
from skillmeat.core.artifact_detection import detect_artifact, ArtifactType

result = detect_artifact(path, mode="strict")
if result.artifact_type == ArtifactType.COMPOSITE:
    print(f"Found composite: {result.name} ({result.confidence}%)")
```

### 2. Detect Composites in Marketplace

```python
from skillmeat.core.marketplace.heuristic_detector import HeuristicDetector

detector = HeuristicDetector()
matches = detector.detect_composites_in_tree(
    dir_to_files={
        ".": ["README.md"],
        "plugin-name/.claude-plugin": ["plugin.json"],
    }
)
# Returns highest-priority composites (Signal 0: .claude-plugin/plugin.json = 98% confidence)
```

### 3. Create Composite with Members

```python
from skillmeat.core.services.composite_service import CompositeService

svc = CompositeService()
composite = svc.create_composite(
    collection_id="default",
    composite_id="composite:my-plugin",
    composite_type="plugin",
    initial_members=["skill:canvas", "command:draw"],
)
```

### 4. Create Skill Composite (from skill import)

```python
# When importing a skill with embedded children
composite = svc.create_skill_composite(
    skill_artifact=skill_obj,
    embedded_list=[child_command, child_agent],
    collection_id="default",
)
# Deduplicates by content_hash, creates CompositeMembership edges
```

### 5. Get Child Artifacts

```python
# Frontend pattern
associations = svc.get_associations("composite:my-plugin", "default")
children = associations["children"]  # List[MembershipRecord]

for child in children:
    print(f"  - {child.artifact_type}:{child.artifact_name} (uuid: {child.child_artifact_uuid})")
```

### 6. Frontend Rendering

```tsx
import { artifact-contains-tab } from '@/components/artifact/artifact-contains-tab';

<ArtifactContainsTab
  artifact={artifact}
  children={childArtifacts}
/>
```

## Detection Signals by Priority

| Signal | Source | Confidence | Example |
|--------|--------|-----------|---------|
| **Signal 0** | `.claude-plugin/plugin.json` exists | 98% | category/my-plugin/.claude-plugin/plugin.json |
| **Baseline** | COMPOSITE.md/PLUGIN.md in directory | 100% (strict) | composites/my-composite/COMPOSITE.md |
| **Container** | Parent dir = "composites" | 70-80% | composites/my-composite/ |
| **Heuristic** | Marketplace signals (depth, parent hint) | 30-80% | Variable scoring |

## Type:Name to UUID Pattern

**Why it matters**: Composites store membership as UUID, but frontend passes type:name.

```python
# Frontend sends:
artifact_id = "skill:canvas"  # type:name

# Service translates:
uuid = _resolve_uuid(session, artifact_id)  # ← UUID lookup
child_artifact_uuid = uuid  # Store in CompositeMembership

# API contract:
artifact.uuid  # Always use uuid for API calls
artifact.id    # Display only (e.g., in UI)
```

## Composite vs Composite-Type Variants

### ArtifactType.COMPOSITE (Artifact Type)
- Directory-based artifact
- Requires manifest (COMPOSITE.md, PLUGIN.md)
- Container: {composites, composite, plugins, plugin, claude-composites}

### CompositeType (Variant within COMPOSITE)
- **plugin** (implemented): Curated bundle of artifacts
- **stack** (reserved): Multi-tool stack declaration
- **suite** (reserved): Curated workflow suite
- **skill** (special): Skill type with embedded children

## Dedup Logic in create_skill_composite

```python
for embedded in embedded_list:
    # Step 1: Try content_hash lookup
    if embedded.content_hash:
        existing = query(Artifact).filter(
            Artifact.content_hash == embedded.content_hash
        ).first()

    # Step 2: Fall back to id lookup
    if not existing:
        existing = query(Artifact).filter(
            Artifact.id == f"{embedded.artifact_type}:{embedded.name}"
        ).first()

    # Step 3: Create new if both miss
    if not existing:
        new_artifact = Artifact(...)
        session.add(new_artifact)

    # Step 4: Upsert membership (skip if exists)
    membership = CompositeMembership(
        collection_id=collection_id,
        composite_id=composite_id,
        child_artifact_uuid=child_uuid,
    )
    session.add(membership)
```

## File Path Resolution

**For single artifacts**:
```python
# API: GET /api/v1/artifacts/{artifact_id}/files/{file_path}?file_paths=path1,path2
# Request specific files from artifact directory
# Path traversal protected: ".." rejected, must be within artifact root
```

**For composites**:
```python
# API: GET /api/v1/composites/{composite_id}
# Returns CompositeMembership edges with child artifact UUIDs
# Frontend fetches child artifact details separately via child UUID
```

## Testing Patterns

### Test Composite Detection

```python
from skillmeat.core.artifact_detection import detect_artifact, ArtifactType

result = detect_artifact(Path("composites/my-plugin"), mode="strict")
assert result.artifact_type == ArtifactType.COMPOSITE
assert result.confidence == 100
assert result.manifest_file == "composites/my-plugin/COMPOSITE.md"
```

### Test Composite Service

```python
from skillmeat.core.services.composite_service import CompositeService

svc = CompositeService()
composite = svc.create_composite(
    collection_id="test",
    composite_id="composite:test-plugin",
    initial_members=["skill:s1", "skill:s2"]
)
assert composite["composite_id"] == "composite:test-plugin"

children = svc.get_associations("composite:test-plugin", "test")
assert len(children["children"]) == 2
```

## Common Pitfalls

1. **UUID vs type:name**: Always pass UUID to API for associations, type:name for display
2. **Manifest requirement**: Composites require COMPOSITE.md or PLUGIN.md (unlike skills)
3. **Nesting**: Composites don't nest (allowed_nesting=False)
4. **Dedup scope**: Content hash dedup is global (across all composites)
5. **.claude-plugin ignored**: Never detected as individual artifact, only parent directory

## When to Use This Pattern

| Scenario | Use | File |
|----------|-----|------|
| Detect artifact type from path | detect_artifact() | artifact_detection.py |
| Scan marketplace repo | detect_composites_in_tree() | heuristic_detector.py |
| Create composite programmatically | CompositeService.create_composite() | composite_service.py |
| Import skill with children | CompositeService.create_skill_composite() | composite_service.py |
| Display composite contents | get_associations() | composite_service.py |
| Render in UI | ArtifactContainsTab | artifact-contains-tab.tsx |
