---
title: Feature Flags
description: Configuration options for toggling SkillMeat features
---

# Feature Flags

SkillMeat supports feature flags to enable or disable functionality at runtime. Feature flags are configured via environment variables with the `SKILLMEAT_` prefix.

## Memory & Context Intelligence System

Memory and extraction APIs are deployed directly and are not runtime-gated by
feature flags.

## Deployment Sets

### `DEPLOYMENT_SETS_ENABLED`

**Environment Variable**: `SKILLMEAT_DEPLOYMENT_SETS_ENABLED`
**Default**: `true`
**Type**: boolean

Enable deployment sets feature for grouping and batch-deploying artifact bundles. When disabled, the Deployment Sets navigation link and all `/api/v1/deployment-sets/` endpoints are hidden.

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

def test_discovery_flags():
    with patch.dict(os.environ, {"SKILLMEAT_ENABLE_AUTO_DISCOVERY": "false"}):
        # Your test code here
        ...
```

See `skillmeat/api/tests/test_feature_flags.py` for examples.
