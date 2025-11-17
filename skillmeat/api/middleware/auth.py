"""Authentication middleware for SkillMeat API.

Provides JWT token validation middleware and dependency injection for
protected endpoints.
"""

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from skillmeat.core.auth import TokenManager

logger = logging.getLogger(__name__)

# Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)

# Global token manager instance (initialized in lifespan)
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get or create token manager instance.

    Returns:
        TokenManager instance
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


def verify_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> str:
    """Verify JWT token from Authorization header.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        Token string if valid

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_string = credentials.credentials
    token_manager = get_token_manager()

    # Validate token
    if not token_manager.validate_token(token_string):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_string


def optional_verify_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> Optional[str]:
    """Optionally verify JWT token from Authorization header.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        Token string if valid, None if missing (does not raise error)

    Raises:
        HTTPException: If token is provided but invalid
    """
    if not credentials:
        return None

    token_string = credentials.credentials
    token_manager = get_token_manager()

    # Validate token
    if not token_manager.validate_token(token_string):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_string


# Type alias for dependency injection
TokenDep = Annotated[str, Depends(verify_token)]
OptionalTokenDep = Annotated[Optional[str], Depends(optional_verify_token)]


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for token-based authentication.

    This middleware validates JWT tokens on protected routes and
    provides request-level authentication state.

    Attributes:
        protected_paths: List of path prefixes that require authentication
        excluded_paths: List of paths to exclude from authentication
    """

    def __init__(
        self,
        app,
        protected_paths: Optional[list] = None,
        excluded_paths: Optional[list] = None,
    ):
        """Initialize auth middleware.

        Args:
            app: FastAPI application
            protected_paths: Path prefixes requiring authentication (default: all under /api/v1)
            excluded_paths: Specific paths to exclude (default: health, docs, openapi)
        """
        super().__init__(app)

        self.protected_paths = protected_paths or ["/api/v1"]
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/api/v1/version",
        ]

        self.token_manager = get_token_manager()

        logger.info(
            f"Auth middleware initialized (protected: {self.protected_paths}, "
            f"excluded: {self.excluded_paths})"
        )

    async def dispatch(self, request: Request, call_next):
        """Process request with authentication checks.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response from next middleware
        """
        # Check if path requires authentication
        path = request.url.path
        requires_auth = self._requires_auth(path)

        # Add auth state to request
        request.state.authenticated = False
        request.state.token = None

        if requires_auth:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return self._unauthorized_response(
                    "Missing or invalid Authorization header"
                )

            token_string = auth_header[7:]  # Remove "Bearer " prefix

            # Validate token
            if not self.token_manager.validate_token(token_string):
                return self._unauthorized_response("Invalid or expired token")

            # Mark as authenticated
            request.state.authenticated = True
            request.state.token = token_string

            logger.debug(f"Authenticated request to {path}")

        # Continue to next middleware
        response = await call_next(request)
        return response

    def _requires_auth(self, path: str) -> bool:
        """Check if a path requires authentication.

        Args:
            path: Request path

        Returns:
            True if authentication is required
        """
        # Check excluded paths first
        for excluded in self.excluded_paths:
            if path == excluded or path.startswith(excluded + "/"):
                return False

        # Check protected paths
        for protected in self.protected_paths:
            if path.startswith(protected):
                return True

        return False

    def _unauthorized_response(self, detail: str):
        """Create unauthorized response.

        Args:
            detail: Error detail message

        Returns:
            JSON response with 401 status
        """
        from fastapi.responses import JSONResponse

        logger.warning(f"Unauthorized request: {detail}")

        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": detail},
            headers={"WWW-Authenticate": "Bearer"},
        )


# Rate limiting state (simple in-memory tracking)
# For production, use Redis or similar
_rate_limit_state = {}


def rate_limit_token_validation(
    max_requests: int = 100, window_seconds: int = 60
) -> None:
    """Rate limit for token validation endpoints.

    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds

    Raises:
        HTTPException: If rate limit exceeded

    Note:
        This is a simple in-memory implementation.
        For production, use Redis with sliding window.
    """
    import time

    # This would be implemented with proper rate limiting
    # For now, just a placeholder
    pass
