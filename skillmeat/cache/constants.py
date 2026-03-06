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

# ---------------------------------------------------------------------------
# Local single-user identity  (AAA/RBAC — PRD-2, DB-001)
# ---------------------------------------------------------------------------

# Deterministic UUID for the implicit admin user created automatically in
# local (single-tenant, single-user) mode.  Using a fixed value means that
# existing local data always belongs to the same "user" across restarts and
# migrations, without requiring an explicit user-creation step.
#
# The UUID uses version 4 format (random-bit layout) with a hand-crafted
# value so it is instantly recognisable in logs and test fixtures:
#   00000000-0000-4000-a000-000000000002
#
# It intentionally differs from DEFAULT_TENANT_ID (…000000000001) by only the
# last digit so the two can be distinguished at a glance.
LOCAL_ADMIN_USER_ID: uuid.UUID = uuid.UUID("00000000-0000-4000-a000-000000000002")
