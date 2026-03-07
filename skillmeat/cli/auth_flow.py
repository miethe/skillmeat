"""OAuth 2.0 Device Authorization Grant (RFC 8628) flow for SkillMeat CLI.

Implements the device code flow used by ``skillmeat auth login`` to obtain
access tokens from an OAuth 2.0 / OpenID Connect provider (Clerk or any
standards-compliant issuer) without requiring a browser on the CLI host.

Standard flow summary
---------------------
1. CLI POSTs to ``/oauth/device/authorize`` → receives ``device_code``,
   ``user_code``, ``verification_uri``, ``expires_in``, ``interval``.
2. CLI displays ``user_code`` and ``verification_uri`` to the user.
3. CLI polls ``/oauth/token`` with ``grant_type=urn:ietf:params:oauth:grant-type:device_code``
   at the given interval until ``authorization_pending`` clears.
4. On success the token endpoint returns ``access_token``, optionally
   ``refresh_token`` and ``expires_in``.

Error codes handled
-------------------
- ``authorization_pending`` — user has not yet authorised; keep polling.
- ``slow_down`` — server requests a longer interval; increment by 5 seconds.
- ``expired_token`` — device code has expired; abort with clear message.
- ``access_denied`` — user explicitly declined; abort with clear message.

Configuration
-------------
All settings are read from environment variables so the flow works without
touching any config file:

    SKILLMEAT_AUTH_ISSUER_URL   — Base URL of the OIDC issuer (required when
                                  auth_provider is "clerk").
    SKILLMEAT_AUTH_CLIENT_ID    — OAuth client ID (required).
    SKILLMEAT_AUTH_AUDIENCE     — Optional audience claim value for the token.

References:
    RFC 8628 — OAuth 2.0 Device Authorization Grant
    https://datatracker.ietf.org/doc/html/rfc8628
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
from rich.console import Console

console = Console(force_terminal=True, legacy_windows=False)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceCodeResult:
    """Successful device-code flow result containing OAuth tokens.

    Attributes:
        access_token:  Bearer token to include in API requests.
        refresh_token: Long-lived token that can be exchanged for a new
                       access token (may be ``None`` if the server did not
                       issue one).
        expires_in:    Lifetime of ``access_token`` in seconds (may be
                       ``None`` when the server omits the field).
        token_type:    Token type string (almost always ``"Bearer"``).
        id_token:      Raw OIDC ID token, present when the ``openid`` scope
                       was requested (may be ``None``).
    """

    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: str = "Bearer"
    id_token: Optional[str] = None


@dataclass(frozen=True)
class DeviceAuthResponse:
    """Parsed response from the device-authorization endpoint.

    Attributes:
        device_code:      Opaque code sent to the token endpoint during polling.
        user_code:        Short, human-typeable code shown to the user.
        verification_uri: URL the user must visit to authorise the device.
        verification_uri_complete: Full URL with ``user_code`` embedded
                                   (suitable for QR codes); may be ``None``.
        expires_in:       Seconds until ``device_code`` expires.
        interval:         Minimum polling interval in seconds.
    """

    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int = 5
    verification_uri_complete: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth configuration
# ---------------------------------------------------------------------------


@dataclass
class AuthConfig:
    """Configuration for the device-code flow.

    Reads defaults from environment variables; callers may override any field
    directly.

    Attributes:
        issuer_url:  Base URL of the OIDC/OAuth 2.0 issuer.  The device-
                     authorization and token endpoints are derived from this.
        client_id:   OAuth 2.0 client ID registered with the issuer.
        audience:    Optional ``audience`` parameter appended to the device-
                     authorization request when set.
        scope:       Space-separated list of OAuth scopes to request.
    """

    issuer_url: str = field(
        default_factory=lambda: os.environ.get("SKILLMEAT_AUTH_ISSUER_URL", "")
    )
    client_id: str = field(
        default_factory=lambda: os.environ.get("SKILLMEAT_AUTH_CLIENT_ID", "")
    )
    audience: Optional[str] = field(
        default_factory=lambda: os.environ.get("SKILLMEAT_AUTH_AUDIENCE")
    )
    scope: str = "openid profile email"

    # ---------------------------------------------------------------------------
    # Derived endpoint helpers
    # ---------------------------------------------------------------------------

    @property
    def device_authorization_endpoint(self) -> str:
        """URL for the device-authorization request.

        Clerk exposes this at ``<issuer>/oauth/device/authorize``.
        """
        return f"{self.issuer_url.rstrip('/')}/oauth/device/authorize"

    @property
    def token_endpoint(self) -> str:
        """URL for the token-polling request.

        Clerk exposes this at ``<issuer>/oauth/token``.
        """
        return f"{self.issuer_url.rstrip('/')}/oauth/token"

    def is_configured(self) -> bool:
        """Return True when both ``issuer_url`` and ``client_id`` are set."""
        return bool(self.issuer_url and self.client_id)


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class DeviceCodeFlowError(Exception):
    """Base class for device-code flow errors."""


class DeviceCodeExpiredError(DeviceCodeFlowError):
    """The device code expired before the user authorised."""


class DeviceCodeAccessDeniedError(DeviceCodeFlowError):
    """The user explicitly denied the authorization request."""


class DeviceCodeTimeoutError(DeviceCodeFlowError):
    """The overall timeout elapsed before authorization completed."""


class DeviceCodeConfigError(DeviceCodeFlowError):
    """Auth configuration is incomplete or invalid."""


# ---------------------------------------------------------------------------
# Main flow class
# ---------------------------------------------------------------------------

_DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


class DeviceCodeFlow:
    """Implements RFC 8628 Device Authorization Grant.

    The class is intentionally thin — it delegates HTTP calls to an injected
    client so unit tests can mock the network without patching global state.

    Args:
        config:      Auth configuration (issuer URL, client ID, audience).
        http_client: Optional ``httpx.Client``-compatible object.  When
                     ``None`` a default ``httpx.Client`` with a 30-second
                     timeout is created automatically.

    Example::

        flow = DeviceCodeFlow(config)
        device_auth = flow.start()
        # ... display device_auth.user_code and device_auth.verification_uri ...
        result = flow.poll(device_auth, timeout=300)
        print(result.access_token)
    """

    def __init__(
        self,
        config: AuthConfig,
        http_client: Any = None,
    ) -> None:
        self._config = config
        self._http = http_client or httpx.Client(timeout=30.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> DeviceAuthResponse:
        """Initiate a device-code flow.

        POSTs to the device-authorization endpoint and returns a parsed
        :class:`DeviceAuthResponse`.

        Returns:
            Parsed device-authorization response from the server.

        Raises:
            DeviceCodeConfigError: When ``issuer_url`` or ``client_id`` are
                not configured.
            DeviceCodeFlowError: When the server returns an unexpected error.
            httpx.HTTPError: On network-level failures.
        """
        if not self._config.is_configured():
            raise DeviceCodeConfigError(
                "Auth not configured. Set SKILLMEAT_AUTH_ISSUER_URL and "
                "SKILLMEAT_AUTH_CLIENT_ID environment variables."
            )

        payload: dict = {
            "client_id": self._config.client_id,
            "scope": self._config.scope,
        }
        if self._config.audience:
            payload["audience"] = self._config.audience

        response = self._http.post(
            self._config.device_authorization_endpoint, data=payload
        )
        response.raise_for_status()

        data = response.json()
        return DeviceAuthResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data["verification_uri"],
            expires_in=int(data.get("expires_in", 300)),
            interval=int(data.get("interval", 5)),
            verification_uri_complete=data.get("verification_uri_complete"),
        )

    def poll(
        self,
        device_auth: DeviceAuthResponse,
        timeout: float = 300.0,
    ) -> DeviceCodeResult:
        """Poll the token endpoint until the user authorises or an error occurs.

        Respects the ``interval`` from the server; backs off by 5 seconds when
        ``slow_down`` is received.

        Args:
            device_auth: The response object returned by :meth:`start`.
            timeout:     Maximum total wait time in seconds before raising
                         :class:`DeviceCodeTimeoutError`.

        Returns:
            :class:`DeviceCodeResult` containing the access token and optional
            refresh / ID tokens.

        Raises:
            DeviceCodeExpiredError:     Device code expired server-side.
            DeviceCodeAccessDeniedError: User denied the request.
            DeviceCodeTimeoutError:     ``timeout`` elapsed without success.
            DeviceCodeFlowError:        Unrecognised error from the server.
            httpx.HTTPError:            Network-level failures.
        """
        interval = float(device_auth.interval)
        deadline = time.monotonic() + timeout

        while True:
            if time.monotonic() >= deadline:
                raise DeviceCodeTimeoutError(
                    f"Authorization timed out after {timeout:.0f} seconds."
                )

            time.sleep(interval)

            if time.monotonic() >= deadline:
                raise DeviceCodeTimeoutError(
                    f"Authorization timed out after {timeout:.0f} seconds."
                )

            result = self._poll_once(device_auth.device_code)

            if isinstance(result, DeviceCodeResult):
                return result

            # result is an error string from the token endpoint
            error = result
            if error == "authorization_pending":
                continue
            elif error == "slow_down":
                interval += 5.0
                continue
            elif error == "expired_token":
                raise DeviceCodeExpiredError(
                    "The device code has expired. Please run 'skillmeat auth login' again."
                )
            elif error == "access_denied":
                raise DeviceCodeAccessDeniedError(
                    "Authorization was denied. The user declined the request."
                )
            else:
                raise DeviceCodeFlowError(f"Unexpected error from token endpoint: {error}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _poll_once(self, device_code: str) -> "DeviceCodeResult | str":
        """Issue a single token-endpoint poll.

        Returns:
            A :class:`DeviceCodeResult` on success, or the OAuth ``error``
            string on a pending / recoverable error.

        Raises:
            DeviceCodeFlowError: On HTTP-level errors or unexpected responses.
        """
        response = self._http.post(
            self._config.token_endpoint,
            data={
                "grant_type": _DEVICE_GRANT_TYPE,
                "device_code": device_code,
                "client_id": self._config.client_id,
            },
        )

        data = response.json()

        if response.is_success:
            return DeviceCodeResult(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_in=data.get("expires_in"),
                token_type=data.get("token_type", "Bearer"),
                id_token=data.get("id_token"),
            )

        # RFC 8628 §3.5 — error responses use HTTP 400 with JSON body
        error = data.get("error", "")
        if error in ("authorization_pending", "slow_down", "expired_token", "access_denied"):
            return error

        # Unexpected HTTP or OAuth error
        description = data.get("error_description", "")
        raise DeviceCodeFlowError(
            f"Token endpoint returned {response.status_code}: {error} — {description}"
        )
