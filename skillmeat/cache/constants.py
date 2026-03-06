"""
Shared constants for the skillmeat cache layer.

Centralizes values that are referenced across models, repositories, and
service code to avoid magic strings/UUIDs scattered throughout the codebase.
"""

import os
import uuid

# ---------------------------------------------------------------------------
# Tenant identity
# ---------------------------------------------------------------------------

# Deterministic UUID used for all data in single-tenant (Phase 1) mode.
# Override via SKILLMEAT_DEFAULT_TENANT_ID for isolated test environments.
# Value is stable across restarts so dev/test data survives process bounces.
_FALLBACK_TENANT_ID = "00000000-0000-4000-a000-000000000001"

DEFAULT_TENANT_ID: uuid.UUID = uuid.UUID(
    os.environ.get("SKILLMEAT_DEFAULT_TENANT_ID", _FALLBACK_TENANT_ID)
)
