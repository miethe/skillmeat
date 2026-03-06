"""Thin HTTP client helper for enterprise API requests.

All requests are authenticated via a Personal Access Token (PAT) resolved
through :func:`~skillmeat.core.enterprise_config.get_pat`.

Usage::

    from skillmeat.core.enterprise_http import enterprise_request

    resp = enterprise_request("GET", "/api/v1/artifacts")
    resp.raise_for_status()
    data = resp.json()
"""

from __future__ import annotations

import os
from typing import Any

import requests

from skillmeat.core.enterprise_config import EnterpriseConfigError, get_pat

__all__ = [
    "get_auth_headers",
    "enterprise_request",
]


def get_auth_headers() -> dict[str, str]:
    """Return HTTP auth headers for the active PAT.

    Returns:
        A dict containing ``{"Authorization": "Bearer <pat>"}`` when a PAT is
        available, or an empty dict when no PAT is configured.
    """
    pat = get_pat()
    if pat:
        return {"Authorization": f"Bearer {pat}"}
    return {}


def enterprise_request(
    method: str,
    path: str,
    **kwargs: Any,
) -> requests.Response:
    """Make an authenticated HTTP request to the enterprise API server.

    The base URL is read from the ``SKILLMEAT_API_URL`` environment variable.
    Auth headers are injected automatically via :func:`get_auth_headers`.

    Args:
        method: HTTP method string (e.g. ``"GET"``, ``"POST"``).
        path: URL path relative to the API base URL (e.g. ``"/api/v1/artifacts"``).
        **kwargs: Additional keyword arguments forwarded to
            :func:`requests.request` (e.g. ``json``, ``params``, ``timeout``).

    Returns:
        :class:`requests.Response` — callers are responsible for calling
        ``raise_for_status()`` or inspecting the status code.

    Raises:
        EnterpriseConfigError: If no PAT is available from any source, or if
            ``SKILLMEAT_API_URL`` is not set.
        requests.RequestException: For network-level failures.
    """
    api_url = os.environ.get("SKILLMEAT_API_URL", "").rstrip("/")
    if not api_url:
        raise EnterpriseConfigError(
            "SKILLMEAT_API_URL is not set. "
            "Configure it via the environment variable or enterprise config."
        )

    pat = get_pat()
    if not pat:
        raise EnterpriseConfigError(
            "No Personal Access Token (PAT) found. "
            "Provide one via --token, the SKILLMEAT_PAT environment variable, "
            "or 'skillmeat --token <pat>' to store it."
        )

    # Merge caller-supplied headers with auth headers (auth wins on conflict).
    headers: dict[str, str] = dict(kwargs.pop("headers", {}) or {})
    headers.update(get_auth_headers())

    url = api_url + path
    return requests.request(method, url, headers=headers, **kwargs)
