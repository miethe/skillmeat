"""Tests for OpenAPI specification generation and validation."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI

from skillmeat.api.openapi import (
    export_openapi_spec,
    generate_openapi_spec,
    get_api_version_from_spec,
    validate_openapi_spec,
)
from skillmeat.api.server import create_app


class TestOpenAPIGeneration:
    """Test OpenAPI specification generation."""

    def test_generate_openapi_spec_basic(self):
        """Test basic OpenAPI spec generation."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        # Check required fields
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec

        # Check info object
        assert "title" in spec["info"]
        assert "version" in spec["info"]
        assert spec["info"]["x-api-version"] == "v1"

    def test_generate_openapi_spec_with_version(self):
        """Test OpenAPI spec generation with custom API version."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v2")

        assert spec["info"]["x-api-version"] == "v2"

    def test_generate_openapi_spec_includes_security_schemes(self):
        """Test that security schemes are included in spec."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        assert "components" in spec
        assert "securitySchemes" in spec["components"]
        assert "BearerAuth" in spec["components"]["securitySchemes"]

        # Check Bearer auth configuration
        bearer_auth = spec["components"]["securitySchemes"]["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"

    def test_generate_openapi_spec_includes_error_schemas(self):
        """Test that error response schemas are included."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        assert "components" in spec
        assert "schemas" in spec["components"]

        # Check error schemas
        schemas = spec["components"]["schemas"]
        assert "HTTPValidationError" in schemas
        assert "ValidationError" in schemas
        assert "ErrorResponse" in schemas

    def test_generate_openapi_spec_includes_servers(self):
        """Test that server URLs are included."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        assert "servers" in spec
        assert len(spec["servers"]) >= 2

        # Check for local development server
        server_urls = [s["url"] for s in spec["servers"]]
        assert any("localhost:8000" in url for url in server_urls)

    def test_generate_openapi_spec_caches_schema(self):
        """Test that OpenAPI schema is cached on the app."""
        app = create_app()

        # First generation
        spec1 = generate_openapi_spec(app, api_version="v1")

        # Second generation should return cached version
        spec2 = generate_openapi_spec(app, api_version="v1")

        # Should be the same object
        assert spec1 is spec2

    def test_generate_openapi_spec_includes_health_endpoints(self):
        """Test that health check endpoints are in the spec."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        # Check for health endpoints
        assert "/health" in spec["paths"]

        # Check health endpoint details
        health_endpoint = spec["paths"]["/health"]
        assert "get" in health_endpoint


class TestOpenAPIExport:
    """Test OpenAPI specification export to file."""

    def test_export_openapi_spec_creates_file(self):
        """Test that export creates a JSON file."""
        app = create_app()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "openapi.json"
            result_path = export_openapi_spec(app, output_path, api_version="v1")

            # Check file was created
            assert output_path.exists()
            assert result_path == output_path

            # Check file content
            with open(output_path) as f:
                content = f.read()
                spec = json.loads(content)

            assert "openapi" in spec
            assert "info" in spec

    def test_export_openapi_spec_creates_parent_directories(self):
        """Test that export creates parent directories if needed."""
        app = create_app()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "openapi.json"
            result_path = export_openapi_spec(app, output_path, api_version="v1")

            # Check directories were created
            assert output_path.parent.exists()
            assert output_path.exists()
            assert result_path == output_path

    def test_export_openapi_spec_pretty_print(self):
        """Test that export can pretty-print JSON."""
        app = create_app()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "openapi.json"

            # Export with pretty printing
            export_openapi_spec(app, output_path, api_version="v1", pretty=True)

            with open(output_path) as f:
                content = f.read()

            # Pretty-printed JSON should have newlines and indentation
            assert "\n" in content
            assert "  " in content

    def test_export_openapi_spec_compact(self):
        """Test that export can create compact JSON."""
        app = create_app()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "openapi.json"

            # Export without pretty printing
            export_openapi_spec(app, output_path, api_version="v1", pretty=False)

            with open(output_path) as f:
                content = f.read()

            # Compact JSON should not have unnecessary whitespace
            lines = content.split("\n")
            assert len(lines) == 1  # Should be a single line

    def test_export_openapi_spec_default_path(self):
        """Test export with default output path."""
        app = create_app()

        # Export to default path
        result_path = export_openapi_spec(app, api_version="v1")

        # Should be in skillmeat/api/openapi.json
        assert result_path.name == "openapi.json"
        assert result_path.parent.name == "api"


class TestOpenAPIValidation:
    """Test OpenAPI specification validation."""

    def test_validate_valid_spec(self):
        """Test validation of a valid OpenAPI spec."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        is_valid, errors = validate_openapi_spec(spec)

        assert is_valid
        assert len(errors) == 0

    def test_validate_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        spec = {"info": {"title": "Test"}}  # Missing 'openapi' and 'paths'

        is_valid, errors = validate_openapi_spec(spec)

        assert not is_valid
        assert len(errors) > 0
        assert any("openapi" in err.lower() for err in errors)
        assert any("paths" in err.lower() for err in errors)

    def test_validate_missing_info_fields(self):
        """Test validation fails for missing info fields."""
        spec = {
            "openapi": "3.0.0",
            "info": {},  # Missing title and version
            "paths": {},
        }

        is_valid, errors = validate_openapi_spec(spec)

        assert not is_valid
        assert any("title" in err.lower() for err in errors)
        assert any("version" in err.lower() for err in errors)

    def test_validate_endpoint_missing_description(self):
        """Test validation warns about missing endpoint descriptions."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        # Missing description and summary
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            },
        }

        is_valid, errors = validate_openapi_spec(spec)

        assert not is_valid
        assert any("description" in err.lower() for err in errors)

    def test_validate_endpoint_missing_responses(self):
        """Test validation fails for endpoints without responses."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "description": "Test endpoint"
                        # Missing responses
                    }
                }
            },
        }

        is_valid, errors = validate_openapi_spec(spec)

        assert not is_valid
        assert any("responses" in err.lower() for err in errors)

    def test_validate_security_without_schemes(self):
        """Test validation fails when security is used without schemes."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/secure": {
                    "get": {
                        "description": "Secure endpoint",
                        "security": [{"BearerAuth": []}],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
            # Missing components.securitySchemes
        }

        is_valid, errors = validate_openapi_spec(spec)

        assert not is_valid
        assert any("security" in err.lower() for err in errors)


class TestAPIVersionExtraction:
    """Test API version extraction from spec."""

    def test_get_api_version_from_custom_extension(self):
        """Test extracting API version from custom extension."""
        spec = {
            "info": {
                "x-api-version": "v2",
                "version": "1.0.0",
            }
        }

        version = get_api_version_from_spec(spec)
        assert version == "v2"

    def test_get_api_version_from_package_version(self):
        """Test fallback to package version."""
        spec = {
            "info": {
                "version": "1.0.0",
            }
        }

        version = get_api_version_from_spec(spec)
        assert version == "1.0.0"

    def test_get_api_version_missing(self):
        """Test handling when version is missing."""
        spec = {"info": {}}

        version = get_api_version_from_spec(spec)
        assert version == "unknown"


class TestOpenAPIIntegration:
    """Integration tests for OpenAPI generation and export."""

    def test_full_workflow(self):
        """Test complete workflow: create app, generate spec, export, validate."""
        # Create app
        app = create_app()

        # Generate spec
        spec = generate_openapi_spec(app, api_version="v1")

        # Validate
        is_valid, errors = validate_openapi_spec(spec)
        assert is_valid, f"Validation errors: {errors}"

        # Export
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "openapi.json"
            export_openapi_spec(app, output_path, api_version="v1", pretty=True)

            # Read back and validate
            with open(output_path) as f:
                exported_spec = json.load(f)

            is_valid, errors = validate_openapi_spec(exported_spec)
            assert is_valid

            # Extract version
            version = get_api_version_from_spec(exported_spec)
            assert version == "v1"

    def test_spec_has_all_expected_endpoints(self):
        """Test that generated spec includes all expected endpoints."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        # Expected endpoints
        expected_paths = [
            "/",  # Root endpoint
            "/health",  # Health check
            "/api/v1/version",  # Version endpoint
        ]

        for path in expected_paths:
            assert path in spec["paths"], f"Missing expected path: {path}"

    def test_spec_has_proper_types(self):
        """Test that spec has properly typed responses."""
        app = create_app()
        spec = generate_openapi_spec(app, api_version="v1")

        # Check health endpoint has response schema
        health_endpoint = spec["paths"]["/health"]["get"]
        assert "responses" in health_endpoint
        assert "200" in health_endpoint["responses"]

        # Should have a response schema or content type
        response_200 = health_endpoint["responses"]["200"]
        assert "description" in response_200 or "content" in response_200
