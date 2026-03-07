"""Clerk JWT authentication provider for SkillMeat AAA/RBAC system.

Validates JSON Web Tokens issued by Clerk (https://clerk.com) and maps the
contained claims to an ``AuthContext`` for downstream request handling.

Configuration
-------------
Set the following environment variables before starting the API server:

    CLERK_JWKS_URL
        The Clerk JWKS endpoint, typically::

            https://<your-clerk-frontend-api>/.well-known/jwks.json

        Required when ``SKILLMEAT_AUTH_ENABLED=true`` and ``SKILLMEAT_AUTH_PROVIDER=clerk``.

JWKS key caching
----------------
``ClerkAuthProvider`` uses ``jwt.PyJWKClient`` which fetches and caches the
public keys from the JWKS endpoint.  Keys are refreshed automatically when an
unknown ``kid`` is encountered (PyJWT default behaviour).  No external call is
made on every request once the key set has been populated — the in-process
cache is consulted first.

Clerk claim → AuthContext mapping
----------------------------------
+--------------------+---------------------------+------------------------------+
| Clerk JWT claim    | AuthContext field          | Notes                        |
+====================+===========================+==============================+
| ``sub``            | ``user_id``               | UUID5 from sub string        |
+--------------------+---------------------------+------------------------------+
| ``org_id``         | ``tenant_id``             | UUID5 from org_id string;    |
|                    |                           | ``None`` when absent         |
+--------------------+---------------------------+------------------------------+
| ``org_role``       | ``roles``                 | ``org:admin`` → team_admin;  |
|                    |                           | ``org:member`` → team_member;|
|                    |                           | missing org → viewer         |
+--------------------+---------------------------+------------------------------+
| custom metadata    | ``scopes``                | ``permissions`` key if set   |
+--------------------+---------------------------+------------------------------+

Error conventions
-----------------
401 Unauthorized
    Token is absent, malformed, expired, or the signature cannot be verified.
403 Forbidden
    Token is valid but the caller lacks a required permission (not raised here
    directly — the router layer enforces scope/role checks on the returned
    ``AuthContext``).

References:
    .claude/progress/aaa-rbac-foundation/  AUTH-003
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import jwt
from fastapi import HTTPException, Request

from skillmeat.api.auth.provider import AuthProvider
from skillmeat.api.schemas.auth import AuthContext, Role, Scope

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Namespace UUID used when deriving deterministic UUIDs from Clerk string IDs.
#: A fixed, well-known namespace keeps the mapping stable across restarts.
_CLERK_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace

#: Algorithms that Clerk uses for token signing.  RS256 is the standard; RS384
#: and RS512 are included defensively.
_SUPPORTED_ALGORITHMS = ["RS256", "RS384", "RS512"]

#: Clerk org-role string → our Role enum value.
_ORG_ROLE_MAP: dict[str, str] = {
    "org:admin": Role.team_admin.value,
    "org:member": Role.team_member.value,
}

#: Default role granted when no org context is present in the token.
_DEFAULT_ROLE = Role.viewer.value

#: Default scopes granted for authenticated users with no explicit permissions.
_DEFAULT_SCOPES: list[str] = [
    Scope.artifact_read.value,
    Scope.collection_read.value,
    Scope.deployment_read.value,
]

#: Scopes granted to org:member level.
_MEMBER_SCOPES: list[str] = _DEFAULT_SCOPES + [
    Scope.artifact_write.value,
    Scope.collection_write.value,
    Scope.deployment_write.value,
]

#: Scopes granted to org:admin level.
_ADMIN_SCOPES: list[str] = _MEMBER_SCOPES + [
    Scope.admin_wildcard.value,
]

#: Role → default scope set (used when the token carries no explicit permissions).
_ROLE_DEFAULT_SCOPES: dict[str, list[str]] = {
    Role.viewer.value: _DEFAULT_SCOPES,
    Role.team_member.value: _MEMBER_SCOPES,
    Role.team_admin.value: _ADMIN_SCOPES,
    Role.system_admin.value: _ADMIN_SCOPES,
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _str_to_uuid(value: str) -> uuid.UUID:
    """Convert an arbitrary string to a deterministic UUID5.

    Clerk user/org identifiers are opaque strings (e.g. ``user_2abc…``).
    We derive a stable UUID from each string so that ``AuthContext.user_id``
    and ``AuthContext.tenant_id`` always satisfy the ``uuid.UUID`` type
    annotation without forcing callers to handle ``str`` variants.

    Args:
        value: The source string (Clerk ``sub`` or ``org_id``).

    Returns:
        A deterministic UUID5 derived from ``value``.
    """
    return uuid.uuid5(_CLERK_NAMESPACE, value)


def _resolve_jwks_url() -> str:
    """Return the configured Clerk JWKS URL.

    Reads the ``CLERK_JWKS_URL`` environment variable.

    Returns:
        The JWKS URL string.

    Raises:
        RuntimeError: When the environment variable is not set.
    """
    url = os.environ.get("CLERK_JWKS_URL", "").strip()
    if not url:
        raise RuntimeError(
            "CLERK_JWKS_URL environment variable is required when using "
            "ClerkAuthProvider.  Set it to your Clerk JWKS endpoint, e.g. "
            "https://<frontend-api>/.well-known/jwks.json"
        )
    return url


# ---------------------------------------------------------------------------
# ClerkAuthProvider
# ---------------------------------------------------------------------------


class ClerkAuthProvider(AuthProvider):
    """Validates Clerk JWTs and maps claims to ``AuthContext``.

    A single ``ClerkAuthProvider`` instance is created at startup and reused
    for every request.  The internal ``PyJWKClient`` maintains an in-process
    JWKS key cache, so no remote call is made on each request after the initial
    key fetch.

    Thread safety:
        ``PyJWKClient`` is documented as thread-safe for read operations; key
        cache refresh is serialised internally by PyJWT.  ``ClerkAuthProvider``
        itself introduces no additional shared mutable state.

    Args:
        jwks_url: Optional JWKS endpoint URL.  When omitted the value is read
            from the ``CLERK_JWKS_URL`` environment variable at the time the
            first ``validate()`` call is made (lazy initialisation).
        lifespan_in_seconds: JWKS cache TTL passed to ``PyJWKClient``.
            Defaults to 300 s (5 minutes).

    Raises:
        RuntimeError: At construction time when ``jwks_url`` is ``None`` *and*
            ``CLERK_JWKS_URL`` is not set in the environment.
    """

    def __init__(
        self,
        jwks_url: str | None = None,
        lifespan_in_seconds: int = 300,
    ) -> None:
        if jwks_url is None:
            jwks_url = _resolve_jwks_url()

        self._jwks_url = jwks_url
        self._lifespan_in_seconds = lifespan_in_seconds

        # Initialise the JWKS client immediately so misconfiguration is caught
        # at startup rather than at the first authenticated request.
        self._jwks_client = jwt.PyJWKClient(
            self._jwks_url,
            lifespan_in_seconds=self._lifespan_in_seconds,
        )

        logger.info(
            "ClerkAuthProvider initialised",
            extra={"jwks_url": self._jwks_url},
        )

    # ------------------------------------------------------------------
    # AuthProvider interface
    # ------------------------------------------------------------------

    async def validate(self, request: Request) -> AuthContext:
        """Validate the Clerk JWT carried in the ``Authorization`` header.

        Extracts the bearer token, verifies its signature against the Clerk
        JWKS endpoint, and maps the decoded claims to an ``AuthContext``.

        Args:
            request: The incoming FastAPI / Starlette ``Request``.

        Returns:
            A populated, immutable ``AuthContext`` for the authenticated caller.

        Raises:
            HTTPException(401): Token is absent, expired, or signature invalid.
            HTTPException(503): JWKS endpoint is unreachable.
        """
        raw_token = self._extract_bearer_token(request)
        claims = self._decode_jwt(raw_token)
        return self._map_claims_to_context(claims)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_bearer_token(self, request: Request) -> str:
        """Pull the raw JWT from the ``Authorization: Bearer <token>`` header.

        Args:
            request: Incoming HTTP request.

        Returns:
            The JWT string (without the ``Bearer`` prefix).

        Raises:
            HTTPException(401): Header is absent or does not start with
                ``Bearer ``.
        """
        authorization: str = request.headers.get("Authorization", "")
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header",
            )

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(
                status_code=401,
                detail="Authorization header must use Bearer scheme",
            )

        return token.strip()

    def _decode_jwt(self, raw_token: str) -> dict[str, Any]:
        """Fetch the matching signing key from the JWKS cache and decode the JWT.

        Args:
            raw_token: The raw JWT string.

        Returns:
            Decoded JWT payload as a plain dictionary.

        Raises:
            HTTPException(401): Signature invalid, token expired, or claims
                validation failed.
            HTTPException(503): JWKS endpoint is unreachable.
        """
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(raw_token)
        except jwt.PyJWKClientConnectionError as exc:
            logger.error(
                "Failed to reach Clerk JWKS endpoint",
                extra={"jwks_url": self._jwks_url, "error": str(exc)},
            )
            raise HTTPException(
                status_code=503,
                detail="Authentication service temporarily unavailable",
            ) from exc
        except jwt.PyJWKClientError as exc:
            logger.warning(
                "JWKS client error resolving signing key",
                extra={"error": str(exc)},
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid token: unable to resolve signing key",
            ) from exc

        try:
            payload: dict[str, Any] = jwt.decode(
                raw_token,
                signing_key.key,
                algorithms=_SUPPORTED_ALGORITHMS,
                options={"require": ["sub", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError as exc:
            logger.debug("Rejected expired JWT")
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
            ) from exc
        except jwt.InvalidTokenError as exc:
            logger.warning(
                "JWT validation failed",
                extra={"error": str(exc)},
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            ) from exc

        return payload

    def _map_claims_to_context(self, claims: dict[str, Any]) -> AuthContext:
        """Map decoded Clerk JWT claims to an ``AuthContext``.

        Claim mapping rules
        -------------------
        - ``sub``       → ``user_id``  (deterministic UUID5)
        - ``org_id``    → ``tenant_id`` (deterministic UUID5, or ``None``)
        - ``org_role``  → role in ``roles`` (via ``_ORG_ROLE_MAP``)
        - no ``org_id`` → ``viewer`` role
        - ``permissions`` (custom metadata) → ``scopes`` when present;
          otherwise role-default scopes are applied

        Args:
            claims: Decoded JWT payload dictionary.

        Returns:
            Immutable ``AuthContext`` for the authenticated caller.
        """
        # --- user_id ----------------------------------------------------
        sub: str = claims["sub"]
        user_id: uuid.UUID = _str_to_uuid(sub)

        # --- tenant_id --------------------------------------------------
        org_id: str | None = claims.get("org_id")
        tenant_id: uuid.UUID | None = _str_to_uuid(org_id) if org_id else None

        # --- roles ------------------------------------------------------
        if org_id:
            org_role: str = claims.get("org_role", "")
            role_value = _ORG_ROLE_MAP.get(org_role, Role.team_member.value)
        else:
            role_value = _DEFAULT_ROLE

        roles: list[str] = [role_value]

        # --- scopes -----------------------------------------------------
        # Honour an explicit ``permissions`` list if Clerk includes it (e.g.
        # via a custom session claim or Clerk's built-in permissions feature).
        # Fall back to the role-appropriate default set.
        raw_permissions: list[str] | None = claims.get("permissions")
        if raw_permissions and isinstance(raw_permissions, list):
            scopes: list[str] = [
                p for p in raw_permissions if isinstance(p, str)
            ]
        else:
            scopes = _ROLE_DEFAULT_SCOPES.get(role_value, _DEFAULT_SCOPES)

        logger.debug(
            "Clerk JWT mapped to AuthContext",
            extra={
                "user_id": str(user_id),
                "tenant_id": str(tenant_id) if tenant_id else None,
                "roles": roles,
                "scope_count": len(scopes),
            },
        )

        return AuthContext(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            scopes=scopes,
        )
