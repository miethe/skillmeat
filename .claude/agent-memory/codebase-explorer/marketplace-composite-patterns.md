# Marketplace Composite/Plugin Artifact Detection Patterns

## Overview

This document summarizes the discovery of how SkillMeat detects, manages, and displays composite/plugin artifacts in the marketplace context, along with how file contents are determined for artifacts.

## Key Files

### Core Detection & Composite Management

1. **skillmeat/core/artifact_detection.py** (PRIMARY)
   - Canonical artifact type detection with ArtifactType enum
   - Lines 67-186: ArtifactType enum with deployable_types(), composite_types(), context_types() classification methods
   - Lines 483-490: ARTIFACT_SIGNATURES registry with composite detection rules (container names, manifest files, nesting)
   - Key composite detection:
     - Container names: {"composites", "composite", "plugins", "plugin", "claude-composites"}
     - Manifest files: {"COMPOSITE.md", "composite.md", "PLUGIN.md", "plugin.md"}
     - is_directory: True (composites are directory-based)
     - requires_manifest: True
   - Function detect_artifact() (716-845): Main detection function returning DetectionResult

2. **skillmeat/core/services/composite_service.py** (SERVICE LAYER)
   - Lines 115-129: CompositeService class handles composite membership operations
   - Key methods:
     - add_composite_member() (171-234): Add child artifact to composite by type:name
     - create_composite() (318-378): Create new composite with initial members
     - create_skill_composite() (380-514): Create skill-type composite wrapping skills with embedded artifacts
     - _create_skill_composite_in_session() (591-758): Dedup + membership creation logic
   - UUID resolution: type:name → UUID lookup for API boundary
   - Dedup strategy (lines 676-720): content_hash first, then id-based lookup

3. **skillmeat/core/marketplace/heuristic_detector.py** (MARKETPLACE SIGNALS)
   - Lines 162-213: DetectionConfig dataclass with scoring weights
   - Lines 215-320: HeuristicDetector class
   - Key signals for composite detection (lines 0-88):
     - Signal 0 (highest priority): `.claude-plugin/plugin.json` detection (confidence 98)
     - Plugin directory structure: `category/plugin-name/.claude-plugin/plugin.json`
     - Parent of `.claude-plugin/` directory recorded as plugin root
     - Lines 550-625: detect_composites_in_tree() method

### Frontend Components

4. **skillmeat/web/components/artifact/artifact-contains-tab.tsx**
   - Lines 1-100+: Display child artifacts in composite
   - getContainerDisplayName() (31-44): Maps composite_type to display names (plugin, stack, suite, skill)
   - ArtifactTypeIcon() (50-66): Icon mapping for artifact types
   - AssociationItemDTO type: Child artifact representation
   - Shows name, type, description, and link to each child's detail page

### API Schemas

5. **skillmeat/api/schemas/marketplace.py**
   - Lines 17: ALLOWED_ARTIFACT_TYPES includes "composite"
   - ListingResponse, DetectedArtifact, HeuristicMatch schemas

6. **skillmeat/api/schemas/artifacts.py**
   - ArtifactResponse: Primary artifact response model
   - LinkedArtifactReferenceSchema (89-134): Represents artifact relationships

## Composite/Plugin Architecture Pattern

### 1. Artifact Detection (Local & Marketplace)

**Baseline Detection** (skillmeat/core/artifact_detection.py):
- Container name matching (skills/, commands/, composites/, plugins/)
- Manifest file detection (SKILL.md, COMMAND.md, COMPOSITE.md, PLUGIN.md)
- Path structure inference using canonical container names
- Returns DetectionResult with confidence 0-100

**Marketplace-Specific Signals** (skillmeat/core/marketplace/heuristic_detector.py):
- Signal weights: dir_name(10) + manifest(20) + skill_manifest_bonus(40) + extensions(5) + parent_hint(15) + frontmatter(15) + container_hint(25) + frontmatter_type(30)
- MAX_RAW_SCORE = 160, normalized to 0-100 scale
- `.claude-plugin/plugin.json` detection gets confidence 98 (highest priority)

### 2. Composite Type Variants (CompositeType enum)

From artifact_detection.py lines 162-186:
```
- PLUGIN: Curated bundle of skills, commands, agents, and/or hooks
- STACK: (Reserved) Multi-tool stack declaration
- SUITE: (Reserved) Curated workflow suite
```

### 3. Single-File Artifact Membership in Composites

**Skills with Embedded Artifacts**:
- create_skill_composite() wraps skill artifact with embedded child artifacts
- Embedded list: artifacts discovered inside skill directory (commands, agents, etc.)
- Dedup mechanism: content_hash first, id-based fallback, creates Artifact row if missing
- Links via CompositeMembership table

**Detection Flow**:
1. Marketplace scanner detects artifact (skill, command, agent)
2. If skill type: scan for embedded children (commands in subdirs, etc.)
3. Create composite with initial_members list
4. Dedup and link members in single transaction

### 4. File Contents Determination

**For Single Artifacts**:
- GET /api/v1/artifacts/{artifact_id} returns ArtifactResponse
- file_paths query parameter (optional): Request specific files (comma-separated paths)
- get_artifact_file_content() endpoint handles path traversal protection
- Files resolved from artifact directory filesystem

**For Composites**:
- Contents tab shows child artifacts (AssociationItemDTO)
- Child artifacts queried via get_associations() from CompositeService
- Returns MembershipRecord list with type, name, uuid
- Frontend renders as list of linked artifacts with icons

**Key API Pattern** (from artifacts.py):
- file_paths: Optional[str] = Query(...) parameter for selective file loading
- Path traversal protection: ".." rejected, must be within artifact directory
- File content endpoint: GET /api/v1/artifacts/{artifact_id}/files/{file_path}

### 5. Artifact Identifier System (ADR-007)

**Two identifier fields**:
- `id`: type:name format (e.g., "skill:frontend-design") — display, CLI
- `uuid`: Hex UUID — all API calls for associations/tags/groups

**Critical for Composites**:
- Membership edges use child_artifact_uuid (stable reference)
- Service layer resolves type:name → UUID for API boundary
- CompositeService._resolve_uuid() (145-165) handles this resolution

## Key Detection Patterns

### Pattern 1: `.claude-plugin/` Directory Detection

**Location**: heuristic_detector.py, detect_composites_in_tree() method

**Signal Priority 0** (highest confidence: 98):
```
if .claude-plugin/plugin.json exists:
  parent_directory = plugin root
  record parent as detected composite
  skip .claude-plugin from individual artifact detection
```

**Real-world example**:
```
category/plugin-name/.claude-plugin/plugin.json
  → plugin root = "category/plugin-name"
  → artifact_type = COMPOSITE
  → confidence = 98
```

**Why high confidence**: Explicit `.claude-plugin/` directory is authoritative marker for composites in marketplace repos.

### Pattern 2: Container-based Detection

**From artifact_detection.py, ARTIFACT_SIGNATURES**:

Composites detected by:
- Parent directory matches: {"composites", "composite", "plugins", "plugin", "claude-composites"}
- Manifest file found: {"COMPOSITE.md", "composite.md", "PLUGIN.md", "plugin.md"}
- is_directory = True (must be directory, not single file)
- allowed_nesting = False (composites don't nest inside each other)

### Pattern 3: Type Inference Hierarchy

From infer_artifact_type() (lines 610-668):

1. Check for manifest files in directory
2. Check ancestor directory names (up to depth 10)
3. For depth 0 (direct parent): always allow if type matches
4. For deeper nesting: only allow if signature.allowed_nesting = True

**For composites**: allowed_nesting = False, so only direct children of "composites/" directory are detected.

## Composite Content Assembly

### How Composites Determine Their Contents

**From composite_service.py, create_skill_composite()**:

1. **Input**: skill_artifact + embedded_list (detected children)
2. **Dedup phase** (lines 676-720):
   - For each embedded artifact:
     - Query by content_hash first (reuse if exists)
     - Fall back to id-based lookup
     - Create new Artifact row if both miss
3. **Membership phase** (lines 721-748):
   - Create CompositeMembership edges linking composite → child
   - Skip if edge already exists (idempotent)
   - Track dedup_hits, dedup_misses, memberships_created
4. **Result**: CompositeRecord with member UUIDs in CompositeMembership table

### Frontend Display

**artifact-contains-tab.tsx**:
- Renders tab only when artifact_type === "composite" OR children.length > 0
- Maps composite_type to display name (plugin → "Plugin")
- Shows each child as card with icon, name, type, description
- Clickable link to child's detail page
- Uses AssociationItemDTO type for child representation

## Important Distinctions

### Artifact Types vs Composite Types

- **ArtifactType**: skill, command, agent, hook, mcp, **composite**, project_config, spec_file, etc.
- **CompositeType**: Only for ArtifactType.COMPOSITE artifacts
  - plugin (currently only implemented variant)
  - stack, suite (reserved for future)

### Composites vs Skills with Embedded Artifacts

- **Composite** (type: "composite"): Multi-artifact bundle package (plugin manifest)
- **Skill with embedded** (type: "skill", composite_type: "skill"): Skill containing linked child artifacts
  - Created via create_skill_composite() when skill import detects children
  - Same CompositeMembership table used
  - Composite wrapper is type="composite", composite_type="skill"

## API Boundaries & Data Flow

### Type:Name → UUID Resolution

**Service layer translation** (CompositeService):
- Frontend sends: type:name identifiers (human-readable)
- Service resolves: type:name → UUID via Artifact table lookup
- Database uses: child_artifact_uuid (stable reference)
- Error: ArtifactNotFoundError if type:name cannot resolve

### Get Associations (ADR-007 Identity Pattern)

```python
get_associations(artifact_type_name: str, collection_id: str)
  → Returns:
    {
      "parents": [MembershipRecord, ...],  # composites containing this artifact
      "children": [MembershipRecord, ...]  # children of this composite
    }
```

## Cache & Invalidation

**DB Cache = Web's source of truth** (from CLAUDE.md):
- Frontend reads from DB-backed API endpoints
- Marketplace import syncs detected artifacts to CompositeArtifact table
- Stale time: 5min standard browsing (composites are read-mostly)
- Invalidation: Membership mutations invalidate parent/child queries

## Summary Points

1. **`.claude-plugin/plugin.json`** is the definitive marketplace signal for composites (confidence 98)
2. **Composite artifacts** use ArtifactType.COMPOSITE with CompositeType variants (plugin primary)
3. **File contents** for composites determined by CompositeMembership table, not filesystem traversal
4. **Dedup mechanism** ensures single artifact can be linked from multiple composites
5. **ADR-007 pattern**: type:name (API boundary) ↔ UUID (database identity)
6. **Detection layer**: Baseline (artifact_detection.py) + marketplace (heuristic_detector.py)
7. **Frontend display**: artifact-contains-tab shows children as AssociationItemDTO list with icons & links
