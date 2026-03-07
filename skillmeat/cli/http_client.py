"""Authenticated HTTP client for SkillMeat CLI.

Wraps :class:`httpx.Client` to automatically inject an ``Authorization:
Bearer`` header when valid OAuth credentials are available, and to attempt a
transparent token refresh before each request when the stored access token has
expired.

In local (zero-auth) mode — detected via
:func:`~skillmeat.cli.auth_utils.is_local_mode` — the client makes requests
without any ``Authorization`` header so that unauthenticated local API servers
work without needing credentials.

Usage::

    from skillmeat.cli.http_client import get_authenticated_client

    client = get_authenticated_client()
    resp = client.get("/api/v1/artifacts")
    resp.raise_for_status()
    print(resp.json())

Dependency injection for tests::

    from skillmeat.cli.http_client import AuthenticatedClient
    from skillmeat.cli.credential_store import CredentialStore, StoredCredentials
    import time

    fake_store = CredentialStore(backend=MockBackend())
    client = AuthenticatedClient(credential_store=fake_store)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

from skillmeat.cli.auth_utils import is_local_mode
from skillmeat.cli.credential_store import CredentialStore, StoredCredentials

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8080"


class AuthenticatedClient:
    """HTTP client that injects ``Authorization: Bearer`` headers automatically.

    On each request the client:

    1. Checks whether we are in local (zero-auth) mode — if so, proceeds
       without any auth header.
    2. Loads credentials from :class:`~skillmeat.cli.credential_store.CredentialStore`.
    3. If credentials are expired *and* a refresh token is present, calls
       :meth:`~skillmeat.cli.credential_store.CredentialStore.refresh_if_needed`
       to obtain a fresh access token transparently.
    4. Adds ``Authorization: Bearer <token>`` to the request headers when
       valid credentials exist.

    The underlying :class:`httpx.Client` is created once and reused for all
    requests.  Call :meth:`close` (or use the client as a context manager) to
    release the underlying connection pool.

    Args:
        base_url:         Base URL prepended to all request paths.  Defaults
                          to the ``SKILLMEAT_API_URL`` environment variable, or
                          ``http://localhost:8080`` when the variable is not set.
        credential_store: Optional :class:`~skillmeat.cli.credential_store.CredentialStore`
                          instance.  Pass a custom store in tests to avoid
                          touching real keyring / filesystem state.
        http_client:      Optional pre-built :class:`httpx.Client`.  When
                          ``None`` a default client with a 30-second timeout is
                          created automatically.  Useful for injecting mocks in
                          tests.
        timeout:          Request timeout in seconds (default: 30).  Ignored
                          when *http_client* is provided.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        credential_store: Optional[CredentialStore] = None,
        http_client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = (
            (base_url or os.environ.get("SKILLMEAT_API_URL") or _DEFAULT_BASE_URL).rstrip("/")
        )
        self._store = credential_store or CredentialStore()
        self._client = http_client or httpx.Client(timeout=timeout)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "AuthenticatedClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying :class:`httpx.Client` and release connections."""
        self._client.close()

    # ------------------------------------------------------------------
    # HTTP methods
    # ------------------------------------------------------------------

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send a GET request to *path*.

        Args:
            path:    URL path (relative to ``base_url``) or full URL.
            **kwargs: Forwarded to :meth:`httpx.Client.get`.

        Returns:
            :class:`httpx.Response` from the server.
        """
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send a POST request to *path*.

        Args:
            path:    URL path (relative to ``base_url``) or full URL.
            **kwargs: Forwarded to :meth:`httpx.Client.post`.

        Returns:
            :class:`httpx.Response` from the server.
        """
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send a PUT request to *path*.

        Args:
            path:    URL path (relative to ``base_url``) or full URL.
            **kwargs: Forwarded to :meth:`httpx.Client.put`.

        Returns:
            :class:`httpx.Response` from the server.
        """
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send a PATCH request to *path*.

        Args:
            path:    URL path (relative to ``base_url``) or full URL.
            **kwargs: Forwarded to :meth:`httpx.Client.patch`.

        Returns:
            :class:`httpx.Response` from the server.
        """
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send a DELETE request to *path*.

        Args:
            path:    URL path (relative to ``base_url``) or full URL.
            **kwargs: Forwarded to :meth:`httpx.Client.delete`.

        Returns:
            :class:`httpx.Response` from the server.
        """
        return self._request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """Return an absolute URL for *path*.

        If *path* is already absolute (starts with ``http://`` or
        ``https://``), it is returned unchanged.  Otherwise it is joined with
        :attr:`_base_url`.
        """
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base_url}/{path.lstrip('/')}"

    def _resolve_credentials(self) -> Optional[StoredCredentials]:
        """Return valid credentials, refreshing if necessary.

        Returns ``None`` in local mode or when credentials cannot be obtained.
        """
        if is_local_mode():
            return None

        creds = self._store.load()
        if creds is None:
            return None

        if creds.is_expired:
            # Attempt silent refresh.
            creds = self._store.refresh_if_needed()
            if creds is None:
                logger.debug(
                    "Token refresh failed or not possible; proceeding without auth header."
                )
                return None

        return creds

    def _auth_headers(self) -> dict[str, str]:
        """Build ``Authorization`` header dict, or empty dict in local mode."""
        creds = self._resolve_credentials()
        if creds is None:
            return {}
        return {"Authorization": f"{creds.token_type} {creds.access_token}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Execute *method* request against *path* with auth headers injected.

        Merges the resolved auth headers with any ``headers`` kwarg the caller
        provided.  Caller-supplied headers always take precedence over the
        auth header so that tests can override behaviour.

        Args:
            method:   HTTP verb (``"GET"``, ``"POST"``, etc.).
            path:     URL path or full URL.
            **kwargs: Forwarded to :meth:`httpx.Client.request`.

        Returns:
            :class:`httpx.Response`.
        """
        url = self._build_url(path)
        auth_hdrs = self._auth_headers()

        # Merge caller headers with auth headers; caller wins on conflict.
        if auth_hdrs:
            caller_headers: dict[str, str] = dict(kwargs.pop("headers", {}) or {})
            merged = {**auth_hdrs, **caller_headers}
            kwargs["headers"] = merged

        return self._client.request(method, url, **kwargs)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_authenticated_client(
    base_url: Optional[str] = None,
    credential_store: Optional[CredentialStore] = None,
    timeout: float = 30.0,
) -> AuthenticatedClient:
    """Create and return an :class:`AuthenticatedClient` with default settings.

    This is the preferred entry point for CLI commands that need to call the
    SkillMeat API.

    Args:
        base_url:         Override the API base URL.  Defaults to the
                          ``SKILLMEAT_API_URL`` env var or
                          ``http://localhost:8080``.
        credential_store: Optional custom :class:`CredentialStore`.
        timeout:          Request timeout in seconds (default: 30).

    Returns:
        A ready-to-use :class:`AuthenticatedClient`.

    Example::

        client = get_authenticated_client()
        resp = client.get("/api/v1/health")
        resp.raise_for_status()
    """
    return AuthenticatedClient(
        base_url=base_url,
        credential_store=credential_store,
        timeout=timeout,
    )
