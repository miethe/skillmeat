"""Filesystem error handler middleware for enterprise edition.

In enterprise mode, filesystem access should not be required for most operations.
This middleware catches filesystem errors and returns helpful error messages
directing users to the actual issue.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from skillmeat.api.config import get_settings

logger = logging.getLogger(__name__)


class FilesystemErrorMiddleware(BaseHTTPMiddleware):
    """Middleware to handle filesystem errors gracefully in enterprise mode."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        try:
            return await call_next(request)
        except PermissionError as e:
            settings = get_settings()
            if settings.edition == "enterprise":
                logger.error(
                    f"Filesystem permission error in enterprise mode: {e}. "
                    "This indicates a code path that hasn't been migrated to use "
                    "DB-backed repositories."
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "EnterpriseFilesystemError",
                        "message": (
                            "Service temporarily unavailable: filesystem access failed in enterprise mode. "
                            "This is a configuration issue - enterprise mode should not require filesystem access. "
                            "Please check container volume mounts and permissions, or contact support."
                        ),
                        "details": {
                            "edition": "enterprise",
                            "path": str(e),
                            "suggestion": (
                                "Ensure /home/app/.skillmeat is writable, or if this "
                                "persists, report this as a bug - some code paths may "
                                "need migration to database-backed repositories."
                            ),
                        },
                    },
                )
            raise
        except OSError as e:
            settings = get_settings()
            if settings.edition == "enterprise" and "Permission denied" in str(e):
                logger.error(f"OSError with permission issue in enterprise mode: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "EnterpriseFilesystemError",
                        "message": "Service configuration issue: filesystem access failed",
                        "details": {"error": str(e)},
                    },
                )
            raise
