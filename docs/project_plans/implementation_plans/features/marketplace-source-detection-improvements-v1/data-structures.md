---
parent: ../marketplace-source-detection-improvements-v1.md
section: Data Structures
status: inferred_complete
---
# Appendix: Data Structures

## Manual Map JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "mappings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "directory": {
            "type": "string",
            "description": "Path relative to root (e.g., 'commands', 'agents/llm')"
          },
          "type": {
            "type": "string",
            "enum": ["skill", "command", "agent", "mcp_server", "hook"],
            "description": "Artifact type for this directory"
          }
        },
        "required": ["directory", "type"],
        "additionalProperties": false
      },
      "minItems": 0,
      "maxItems": 100
    },
    "last_updated": {
      "type": "string",
      "format": "date-time",
      "description": "When mappings were last updated"
    }
  },
  "required": ["mappings"],
  "additionalProperties": false
}
```

## DeduplicationResult Data Structure

```python
@dataclass
class DeduplicationResult:
    total_detected: int
    duplicates_within_source: int
    duplicates_across_sources: int
    surviving_entries: list[ArtifactMetadata]
    excluded_entries: list[tuple[ArtifactMetadata, str]]  # (entry, reason)
    dedup_time_ms: int
```

## Content Hash Storage (in metadata_json)

```json
{
  "content_hash": "sha256:abcd1234...",
  "hash_algorithm": "sha256",
  "hash_computed_at": "2026-01-05T10:00:00Z",
  "hash_files_count": 3,
  "hash_total_size_bytes": 5240,
  "duplicate_reason": "Duplicate within source (highest confidence survives)",
  "duplicate_group_id": "dedup_grp_123"
}
```
