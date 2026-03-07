"""Shared auth utilities for SkillMeat CLI.

This module contains helpers that are used across multiple CLI modules to avoid
circular imports.  It is intentionally kept small — only place functions here
when they are needed by more than one module in ``skillmeat.cli``.
"""

from __future__ import annotations

import os


def is_local_mode() -> bool:
    """Return ``True`` when SkillMeat is running in zero-auth (local) mode.

    Checks the ``SKILLMEAT_AUTH_MODE`` environment variable first (explicit
    override), then falls back to reading ``APISettings`` if available.

    Returns:
        ``True`` when no authentication provider is configured.
    """
    auth_mode = os.environ.get("SKILLMEAT_AUTH_MODE", "").strip().lower()
    if auth_mode == "local":
        return True
    if auth_mode and auth_mode != "clerk":
        # Unknown explicit mode — treat as local to be safe.
        return True

    # No explicit override — consult API settings if reachable.
    try:
        from skillmeat.api.config import get_settings

        settings = get_settings()
        return not settings.auth_enabled or settings.auth_provider == "local"
    except Exception:
        # API settings unavailable (e.g. running without API installed).
        # Fall back to env-var based detection.
        issuer = os.environ.get("SKILLMEAT_AUTH_ISSUER_URL", "").strip()
        client_id = os.environ.get("SKILLMEAT_AUTH_CLIENT_ID", "").strip()
        return not (issuer and client_id)
