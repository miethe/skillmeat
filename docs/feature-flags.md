---
title: Feature Flags
description: Configuration options for toggling SkillMeat features
---

# Feature Flags

SkillMeat supports feature flags to enable or disable functionality at runtime. Feature flags are configured via environment variables with the `SKILLMEAT_` prefix.

## Memory & Context Intelligence System

### `MEMORY_CONTEXT_ENABLED`

**Environment Variable**: `SKILLMEAT_MEMORY_CONTEXT_ENABLED`
**Default**: `true`
**Type**: boolean

Controls whether the entire Memory & Context Intelligence System is available. When disabled, all memory-related endpoints return 503 (Service Unavailable).

**Affected Endpoints**:
- `GET/POST /api/v1/memory-items` - Memory item CRUD operations
- `POST /api/v1/memory-items/merge` - Memory item merging
- `GET/POST /api/v1/context-modules` - Context module management
- `POST /api/v1/context-packs/preview` - Context pack preview
- `POST /api/v1/context-packs/generate` - Context pack generation

**Usage**:

```bash
# Disable the feature
export SKILLMEAT_MEMORY_CONTEXT_ENABLED=false

# Enable the feature (default)
export SKILLMEAT_MEMORY_CONTEXT_ENABLED=true
```

### `MEMORY_AUTO_EXTRACT`

**Environment Variable**: `SKILLMEAT_MEMORY_AUTO_EXTRACT`
**Default**: `false`
**Type**: boolean

Controls whether automatic memory extraction from conversations is enabled. This is a Phase 5 feature that is not yet implemented.

**Usage**:

```bash
# Enable auto-extraction (when implemented)
export SKILLMEAT_MEMORY_AUTO_EXTRACT=true

# Disable auto-extraction (default)
export SKILLMEAT_MEMORY_AUTO_EXTRACT=false
```

## Discovery Features

### `ENABLE_AUTO_DISCOVERY`

**Environment Variable**: `SKILLMEAT_ENABLE_AUTO_DISCOVERY`
**Default**: `true`
**Type**: boolean

Enable artifact auto-discovery feature for finding Claude artifacts in repositories.

### `ENABLE_AUTO_POPULATION`

**Environment Variable**: `SKILLMEAT_ENABLE_AUTO_POPULATION`
**Default**: `true`
**Type**: boolean

Enable automatic GitHub metadata population for artifacts.

### `DISCOVERY_CACHE_TTL`

**Environment Variable**: `SKILLMEAT_DISCOVERY_CACHE_TTL`
**Default**: `3600` (1 hour)
**Type**: integer (seconds)

Cache TTL for discovery metadata.

## Configuration File

All feature flags are defined in `skillmeat/api/config.py` as part of the `APISettings` Pydantic model. The configuration system:

- Loads from environment variables with `SKILLMEAT_` prefix
- Supports `.env` file in project root
- Provides sensible defaults
- Validates configuration on startup

## Testing Feature Flags

Feature flags can be tested using environment variable overrides:

```python
import os
from unittest.mock import patch

def test_memory_disabled():
    with patch.dict(os.environ, {"SKILLMEAT_MEMORY_CONTEXT_ENABLED": "false"}):
        # Your test code here
        response = client.get("/api/v1/memory-items?project_id=test")
        assert response.status_code == 503
```

See `skillmeat/api/tests/test_feature_flags.py` for examples.
