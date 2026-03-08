"""OpenAPI specification generation and export.

This module provides utilities for generating and exporting the OpenAPI specification
from the FastAPI application. The generated spec is used for TypeScript SDK generation
and API documentation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from fastapi.openapi.utils import get_openapi

from skillmeat import __version__ as skillmeat_version

logger = logging.getLogger(__name__)


_BEARER_AUTH_DESCRIPTION = """
JWT Bearer token authentication. Send the token in the `Authorization: Bearer <token>` header.

**Supported providers**: `local` (SkillMeat-issued PATs) and `clerk` (Clerk.dev JWTs).

### Available Scopes

| Scope | Description |
|-------|-------------|
| `artifact:read` | Read artifact data |
| `artifact:write` | Create, update, and delete artifacts |
| `collection:read` | Read collection data |
| `collection:write` | Create, update, and delete collections |
| `deployment:read` | Read deployment data |
| `deployment:write` | Create, update, and delete deployments |
| `admin:*` | Full administrative access (wildcard — grants all scopes) |

### Roles

| Role | Description |
|------|-------------|
| `system_admin` | Full system access (service accounts only) |
| `team_admin` | Team administration |
| `team_member` | Standard team member |
| `viewer` | Read-only access |

### Auth Bypass

When `auth_enabled=false` (development default), the server accepts all requests
without credentials. Set `SKILLMEAT_AUTH_ENABLED=true` to enforce authentication.
"""

#: Routers that are intentionally public (no Bearer token required).
_PUBLIC_PATH_PREFIXES = (
    "/health",
    "/api/v1/settings",
    "/api/v1/cache",
    "/metrics",
    "/",
    "/docs",
    "/redoc",
)


def _is_public_path(path: str) -> bool:
    """Return True when *path* is explicitly excluded from auth requirements."""
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in _PUBLIC_PATH_PREFIXES
    )


def generate_openapi_spec(app, api_version: str = "v1") -> Dict:
    """Generate OpenAPI specification from FastAPI app.

    Args:
        app: FastAPI application instance
        api_version: API version string

    Returns:
        OpenAPI specification as dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags or [],
    )

    # Add custom extensions
    openapi_schema["info"]["x-api-version"] = api_version
    openapi_schema["info"]["x-package-version"] = skillmeat_version

    # Add server URLs
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8080",
            "description": "Local development server",
        },
        {
            "url": "http://localhost:8080/api/v1",
            "description": "Local development API",
        },
    ]

    # Ensure components section exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    # Merge security schemes: preserve any FastAPI-generated schemes (APIKeyHeader,
    # HTTPBearer) and add/overwrite BearerAuth with full scope+role documentation.
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": _BEARER_AUTH_DESCRIPTION,
    }

    # Also document the legacy API key scheme for routers that still use it.
    if "APIKeyAuth" not in openapi_schema["components"]["securitySchemes"]:
        openapi_schema["components"]["securitySchemes"]["APIKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": (
                "Legacy API key authentication. "
                "Prefer Bearer tokens for new integrations."
            ),
        }

    # Apply BearerAuth security requirement to all protected paths.
    # Public paths (health, settings, cache, metrics, docs) are left unchanged.
    bearer_security = [{"BearerAuth": []}]
    for path, path_item in openapi_schema.get("paths", {}).items():
        if _is_public_path(path):
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if isinstance(operation, dict):
                # Set security if not already declared at the operation level
                if "security" not in operation:
                    operation["security"] = bearer_security
                # Ensure 401 and 403 responses are documented
                responses = operation.setdefault("responses", {})
                if "401" not in responses:
                    responses["401"] = {
                        "description": "Missing or invalid authentication credentials."
                    }
                if "403" not in responses:
                    responses["403"] = {
                        "description": "Authenticated but lacking required scope."
                    }

    # Add common error responses
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    # Add error response schemas
    openapi_schema["components"]["schemas"]["HTTPValidationError"] = {
        "title": "HTTPValidationError",
        "type": "object",
        "properties": {
            "detail": {
                "title": "Detail",
                "type": "array",
                "items": {"$ref": "#/components/schemas/ValidationError"},
            }
        },
    }

    openapi_schema["components"]["schemas"]["ValidationError"] = {
        "title": "ValidationError",
        "required": ["loc", "msg", "type"],
        "type": "object",
        "properties": {
            "loc": {
                "title": "Location",
                "type": "array",
                "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
            },
            "msg": {"title": "Message", "type": "string"},
            "type": {"title": "Error Type", "type": "string"},
        },
    }

    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "title": "ErrorResponse",
        "type": "object",
        "properties": {
            "detail": {"title": "Detail", "type": "string"},
            "status_code": {"title": "Status Code", "type": "integer"},
        },
        "required": ["detail"],
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def export_openapi_spec(
    app,
    output_path: Optional[Path] = None,
    api_version: str = "v1",
    pretty: bool = True,
) -> Path:
    """Export OpenAPI specification to JSON file.

    Args:
        app: FastAPI application instance
        output_path: Path to write the OpenAPI spec (default: skillmeat/api/openapi.json)
        api_version: API version string
        pretty: Whether to pretty-print the JSON

    Returns:
        Path to the exported OpenAPI spec file

    Raises:
        IOError: If file cannot be written
    """
    # Generate the spec
    openapi_schema = generate_openapi_spec(app, api_version)

    # Determine output path
    if output_path is None:
        # Default to skillmeat/api/openapi.json
        api_dir = Path(__file__).parent
        output_path = api_dir / "openapi.json"

    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the spec
    with open(output_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        else:
            json.dump(openapi_schema, f, ensure_ascii=False)

    logger.info(f"OpenAPI specification exported to: {output_path}")
    return output_path


def validate_openapi_spec(spec: Dict) -> tuple[bool, list[str]]:
    """Validate OpenAPI specification for completeness.

    Checks:
    - Required fields are present
    - All endpoints have descriptions
    - All request/response models have schemas
    - Security schemes are defined

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    errors = []

    # Check required top-level fields
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in spec:
            errors.append(f"Missing required field: {field}")

    # Check info object
    if "info" in spec:
        required_info_fields = ["title", "version"]
        for field in required_info_fields:
            if field not in spec["info"]:
                errors.append(f"Missing required info field: {field}")

    # Check paths
    if "paths" in spec:
        for path, path_item in spec["paths"].items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Check for operation description
                    if "description" not in operation and "summary" not in operation:
                        errors.append(
                            f"Endpoint {method.upper()} {path} missing description/summary"
                        )

                    # Check for response definitions
                    if "responses" not in operation:
                        errors.append(
                            f"Endpoint {method.upper()} {path} missing responses"
                        )

    # Check for security schemes if security is used
    has_security = False
    if "paths" in spec:
        for path, path_item in spec["paths"].items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    if "security" in operation:
                        has_security = True
                        break

    if has_security:
        if "components" not in spec or "securitySchemes" not in spec["components"]:
            errors.append("Security is used but no security schemes defined")

    is_valid = len(errors) == 0
    return is_valid, errors


def get_api_version_from_spec(spec: Dict) -> str:
    """Extract API version from OpenAPI spec.

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        API version string, or "unknown" if not found
    """
    # Try custom extension first
    if "info" in spec and "x-api-version" in spec["info"]:
        return spec["info"]["x-api-version"]

    # Fall back to package version
    if "info" in spec and "version" in spec["info"]:
        return spec["info"]["version"]

    return "unknown"
