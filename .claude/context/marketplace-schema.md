---
title: Marketplace Source Detection Schema
references:
  - skillmeat/cache/models.py (MarketplaceSource, MarketplaceCatalogEntry)
  - skillmeat/core/artifact.py (ArtifactType enum)
last_verified: 2026-01-05
---

# Marketplace Source Detection Schema

Schema definitions and validation rules for marketplace source detection improvements (Phase 1-3).

## Overview

The marketplace source detection system uses two main database tables:
- **`marketplace_sources`**: GitHub repositories configured as artifact sources
- **`marketplace_catalog_entries`**: Artifacts detected during repository scanning

Both tables support JSON-based configuration and metadata storage for flexible artifact detection.

---

## MarketplaceSource Schema

### Database Column: `manual_map`

**Type**: `Text` (JSON-serialized string)
**Nullable**: Yes (NULL = no manual overrides)
**Column Name**: `manual_map`
**ORM Field**: `MarketplaceSource.manual_map`

### JSON Schema for `manual_map`

```json
{
  "type": "object",
  "title": "Manual Artifact Type Mapping",
  "description": "Maps directory paths to artifact types, overriding automatic detection",
  "additionalProperties": {
    "type": "string",
    "enum": ["skill", "command", "agent", "mcp_server", "hook"],
    "description": "Artifact type assigned to this path"
  },
  "examples": [
    {
      "skills/python": "skill",
      "scripts": "command",
      "agents/research": "agent",
      "servers/database": "mcp_server",
      "hooks/pre-commit": "hook"
    }
  ]
}
```

### Valid Artifact Types

The following artifact types are supported in `manual_map` and other detections:

| Type | Description | Example Path |
|------|-------------|--------------|
| `skill` | Claude Code skill artifact | `skills/python-skill/` |
| `command` | CLI command definition | `commands/deploy.md` |
| `agent` | Agent artifact | `agents/research/` |
| `mcp_server` | MCP server implementation | `servers/database/` |
| `hook` | Git or lifecycle hook | `hooks/pre-commit.py` |

**Note**: The following types are stored but not typically used in manual mappings:
- `project_config` - CLAUDE.md files
- `spec_file` - Specification documents
- `rule_file` - Rule files
- `context_file` - Context documents
- `progress_template` - Progress tracking templates

### Data Access Patterns

#### Reading Manual Map

```python
from skillmeat.cache.models import get_session, MarketplaceSource

session = get_session()
try:
    source = session.query(MarketplaceSource).filter_by(id="source-123").first()

    # Method 1: Get as parsed dictionary
    manual_map_dict = source.get_manual_map_dict()
    if manual_map_dict:
        artifact_type = manual_map_dict.get("skills/python")
        # artifact_type = "skill"

    # Method 2: Get raw JSON string
    json_str = source.manual_map
    # json_str = '{"skills/python": "skill", ...}'
finally:
    session.close()
```

#### Writing Manual Map

```python
source = session.query(MarketplaceSource).filter_by(id="source-123").first()

# Method 1: Set from dictionary (recommended)
mapping = {
    "skills/python": "skill",
    "scripts": "command",
    "agents/research": "agent",
}
source.set_manual_map_dict(mapping)
session.commit()

# Method 2: Set raw JSON string
import json
mapping_dict = {"skills/python": "skill"}
source.manual_map = json.dumps(mapping_dict)
session.commit()
```

### Hierarchical Path Inheritance

Paths support hierarchical matching with inheritance rules:

```
/root
├── skills/         → "skill" (applies to all children)
│   ├── python/     → inherits "skill"
│   └── javascript/ → inherits "skill"
├── commands/       → "command" (applies to all children)
└── agents/
    ├── research/   → "agent" (matches exact path)
    └── planning/   → "agent" (inherits from parent)
```

**Inheritance Rules**:
1. **Exact Match**: If path has exact entry, use that type
2. **Parent Inheritance**: If no exact match, check parent directories (shortest path first)
3. **Default**: If no match, use automatic detection
4. **Override**: Child entries override parent entries

**Example Configuration**:
```json
{
  "skills": "skill",
  "skills/deprecated": "project_config",
  "commands": "command",
  "agents/research": "agent"
}
```

Resolution:
- `skills/python/` → matches `skills` → type = `skill`
- `skills/deprecated/old-skill/` → matches `skills/deprecated` → type = `project_config`
- `commands/cli/` → matches `commands` → type = `command`
- `agents/research/v2/` → matches `agents/research` → type = `agent`

---

## MarketplaceCatalogEntry Schema

### Database Column: `metadata_json`

**Type**: `Text` (JSON-serialized string)
**Nullable**: Yes (NULL = no additional metadata)
**Column Name**: `metadata_json`
**ORM Field**: `MarketplaceCatalogEntry.metadata_json`

### JSON Schema for `metadata_json`

```json
{
  "type": "object",
  "title": "Catalog Entry Metadata",
  "description": "Additional detection and validation metadata",
  "properties": {
    "content_hash": {
      "type": "string",
      "description": "SHA-256 hash of detected artifact content",
      "minLength": 64,
      "maxLength": 64,
      "pattern": "^[a-f0-9]{64}$"
    },
    "detection_method": {
      "type": "string",
      "enum": ["path_pattern", "frontmatter", "manual_map", "heuristic"],
      "description": "How this artifact was detected"
    },
    "frontmatter_title": {
      "type": "string",
      "description": "Title extracted from markdown frontmatter (if available)"
    },
    "frontmatter_description": {
      "type": "string",
      "description": "Description extracted from markdown frontmatter (if available)"
    },
    "file_extension": {
      "type": "string",
      "description": "File extension (e.g., '.md', '.py', '.js')",
      "examples": [".md", ".py", ".js", ".ts"]
    },
    "validation_errors": {
      "type": "array",
      "description": "List of validation errors found during detection",
      "items": {
        "type": "object",
        "properties": {
          "field": {
            "type": "string",
            "description": "Field that failed validation"
          },
          "error": {
            "type": "string",
            "description": "Error message"
          }
        }
      }
    },
    "detection_confidence_breakdown": {
      "type": "object",
      "description": "Component scores contributing to confidence_score",
      "properties": {
        "path_match": { "type": "number", "minimum": 0, "maximum": 100 },
        "frontmatter_match": { "type": "number", "minimum": 0, "maximum": 100 },
        "content_match": { "type": "number", "minimum": 0, "maximum": 100 },
        "manual_override": { "type": "number", "minimum": 0, "maximum": 100 }
      }
    }
  }
}
```

### Data Access Patterns

#### Reading Metadata

```python
from skillmeat.cache.models import get_session, MarketplaceCatalogEntry
import json

session = get_session()
try:
    entry = session.query(MarketplaceCatalogEntry).filter_by(id="entry-123").first()

    # Method 1: Get as parsed dictionary (recommended)
    metadata = entry.get_metadata_dict()
    if metadata:
        content_hash = metadata.get("content_hash")
        detection_method = metadata.get("detection_method")

    # Method 2: Get raw JSON string
    json_str = entry.metadata_json
    # json_str = '{"content_hash": "abc123...", "detection_method": "path_pattern"}'
finally:
    session.close()
```

#### Writing Metadata with New Fields

```python
entry = session.query(MarketplaceCatalogEntry).filter_by(id="entry-123").first()

# Get current metadata or start fresh
metadata = entry.get_metadata_dict() or {}

# Add new fields (e.g., content_hash)
metadata["content_hash"] = "abc123def456..."
metadata["detection_method"] = "path_pattern"
metadata["detection_confidence_breakdown"] = {
    "path_match": 95,
    "frontmatter_match": 0,
    "content_match": 75,
    "manual_override": 0
}

# Save back
entry.set_metadata_dict(metadata)
session.commit()
```

### Adding New Metadata Fields

The `metadata_json` column supports dynamic extension without schema migrations:

```python
# Phase 3 addition example: Adding path_segments tracking
metadata = entry.get_metadata_dict() or {}

# Add new nested structure for path tag extraction
metadata["path_segments"] = [
    {
        "segment": "skills",
        "type": "directory",
        "approved": True
    },
    {
        "segment": "python",
        "type": "directory",
        "approved": True
    },
    {
        "segment": "skill.md",
        "type": "file",
        "approved": True
    }
]

metadata["path_tag_extraction"] = {
    "status": "completed",
    "timestamp": "2026-01-05T10:30:00Z",
    "tags_extracted": ["skill", "python", "directory"]
}

entry.set_metadata_dict(metadata)
session.commit()
```

---

## Score Breakdown Reference

### Confidence Score Calculation

The `confidence_score` (0-100) is computed from multiple detection signals:

```
confidence_score = (
    path_match_score * 0.40 +        # 40% weight: filename/path patterns
    frontmatter_match_score * 0.30 + # 30% weight: frontmatter analysis
    content_match_score * 0.20 +     # 20% weight: content analysis
    manual_override_score * 0.10     # 10% weight: manual mapping
)
```

### Score Breakdown Fields

| Field | Range | Meaning | When Set |
|-------|-------|---------|----------|
| `path_match` | 0-100 | How well filename/path matches artifact patterns | Always |
| `frontmatter_match` | 0-100 | How well frontmatter metadata matches | If markdown file with frontmatter |
| `content_match` | 0-100 | How well content analysis matches | If deep content scan enabled |
| `manual_override` | 0-100 | Score from manual mapping | If manual_map applies to this path |

### Example Breakdown

```json
{
  "path_match": 90,
  "frontmatter_match": 85,
  "content_match": 70,
  "manual_override": 0,
  "final_confidence": 82
}
```

Interpretation:
- Path patterns strongly suggest this is the right artifact type (90/100)
- Frontmatter confirms it (85/100)
- Content analysis is less certain (70/100)
- No manual override applied (0/100)
- Weighted average: 0.4×90 + 0.3×85 + 0.2×70 + 0.1×0 = 82/100

---

## Validation Rules

### Manual Map Validation

```python
def validate_manual_map(manual_map_dict: Dict[str, str]) -> List[str]:
    """Validate manual_map structure and values.

    Returns:
        List of validation errors (empty if valid)
    """
    valid_types = {"skill", "command", "agent", "mcp_server", "hook"}
    errors = []

    if not isinstance(manual_map_dict, dict):
        errors.append("manual_map must be a dictionary")
        return errors

    for path, artifact_type in manual_map_dict.items():
        # Validate path
        if not isinstance(path, str) or not path.strip():
            errors.append(f"Invalid path: must be non-empty string, got {path!r}")

        if path.startswith("/"):
            errors.append(f"Path '{path}' should not start with /")

        if "//" in path:
            errors.append(f"Path '{path}' contains double slashes")

        # Validate artifact type
        if artifact_type not in valid_types:
            errors.append(
                f"Invalid artifact type for path '{path}': '{artifact_type}'. "
                f"Must be one of {valid_types}"
            )

    return errors
```

### Metadata Validation

```python
def validate_metadata(metadata_dict: Dict[str, Any]) -> List[str]:
    """Validate metadata_json structure.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate content_hash if present
    if "content_hash" in metadata_dict:
        content_hash = metadata_dict["content_hash"]
        if not isinstance(content_hash, str) or len(content_hash) != 64:
            errors.append(
                f"Invalid content_hash: must be 64-character hex string, "
                f"got {len(content_hash)} chars"
            )
        if not all(c in "0123456789abcdef" for c in content_hash.lower()):
            errors.append(f"Invalid content_hash: must be hex string")

    # Validate detection_method if present
    valid_methods = {"path_pattern", "frontmatter", "manual_map", "heuristic"}
    if "detection_method" in metadata_dict:
        method = metadata_dict["detection_method"]
        if method not in valid_methods:
            errors.append(
                f"Invalid detection_method: '{method}'. "
                f"Must be one of {valid_methods}"
            )

    # Validate confidence_breakdown if present
    if "detection_confidence_breakdown" in metadata_dict:
        breakdown = metadata_dict["detection_confidence_breakdown"]
        for key, value in breakdown.items():
            if not isinstance(value, (int, float)) or not (0 <= value <= 100):
                errors.append(
                    f"Invalid confidence score '{key}': {value}. "
                    f"Must be between 0 and 100"
                )

    return errors
```

---

## Migration Path (If Needed)

Currently, both columns use `Text` type which is compatible with SQLite. If future requirements demand native JSON column support:

```sql
-- PostgreSQL migration example (not needed for SQLite)
ALTER TABLE marketplace_sources
  ALTER COLUMN manual_map TYPE jsonb USING manual_map::jsonb;

ALTER TABLE marketplace_catalog_entries
  ALTER COLUMN metadata_json TYPE jsonb USING metadata_json::jsonb;
```

For SQLite (current database):
- No migration needed - `Text` columns handle JSON perfectly
- Indexes can be added with generated columns if needed (SQLite 3.31+)
- Consider adding indexes for common queries if performance requires

---

## Code Examples

### Phase 1: Setting Manual Map

```python
from skillmeat.cache.models import get_session, MarketplaceSource
from datetime import datetime

session = get_session()
try:
    source = MarketplaceSource(
        id="github-anthropic-skills",
        repo_url="https://github.com/anthropic/skills",
        owner="anthropic",
        repo_name="skills",
        ref="main"
    )

    # Set manual mapping
    source.set_manual_map_dict({
        "skills/python": "skill",
        "skills/javascript": "skill",
        "templates": "project_config",
        "commands": "command",
    })

    session.add(source)
    session.commit()
finally:
    session.close()
```

### Phase 2: Adding Confidence Breakdown

```python
from skillmeat.cache.models import MarketplaceCatalogEntry

entry = session.query(MarketplaceCatalogEntry).filter_by(id="entry-1").first()

# Get or initialize metadata
metadata = entry.get_metadata_dict() or {}

# Add confidence breakdown
metadata["detection_confidence_breakdown"] = {
    "path_match": 95,
    "frontmatter_match": 85,
    "content_match": 70,
    "manual_override": 0
}

metadata["raw_score"] = 82  # Weighted average
entry.set_metadata_dict(metadata)
session.commit()
```

### Phase 3: Adding Content Hash

```python
from skillmeat.cache.models import MarketplaceCatalogEntry
import hashlib

entry = session.query(MarketplaceCatalogEntry).filter_by(id="entry-1").first()

# Compute and store content hash
content_bytes = fetch_artifact_content(entry.upstream_url)
content_hash = hashlib.sha256(content_bytes).hexdigest()

metadata = entry.get_metadata_dict() or {}
metadata["content_hash"] = content_hash
entry.set_metadata_dict(metadata)
session.commit()
```

---

## References

- **Database Models**: `skillmeat/cache/models.py` (MarketplaceSource line 1173, MarketplaceCatalogEntry line 1368)
- **Artifact Types**: `skillmeat/core/artifact.py` (ArtifactType enum line 33)
- **ORM Documentation**: SQLAlchemy docs on JSON/Text column handling
- **Phase Documentation**: See `.claude/progress/` for phase-specific implementation details
