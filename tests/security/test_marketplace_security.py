"""Security tests for marketplace GitHub ingestion.

Tests path traversal protection and other security validations for the
marketplace source creation endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.server import app

# Path traversal test cases
PATH_TRAVERSAL_PAYLOADS = [
    # Basic path traversal
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32",
    # Double encoding
    "....//....//etc/passwd",
    # URL-encoded
    "%2e%2e%2f%2e%2e%2fetc/passwd",
    ".%2e/.%2e/etc/passwd",
    # Absolute paths
    "/etc/passwd",
    "C:\\Windows\\System32",
    # Mixed valid/invalid
    "skills/../../../etc/passwd",
    # Null byte injection
    "skills/..%00/etc/passwd",
    # Variations
    "..%2f..%2f..%2fetc%2fpasswd",
    ".../.../.../.../etc/passwd",
    "./../.../etc/passwd",
]


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limit state before each test to avoid cross-test interference.

    The RateLimitMiddleware uses an in-process SlidingWindowTracker. Parameterized
    security tests send many requests to the same endpoint which can trigger burst
    detection. Clearing the tracker state before each test ensures security
    validation fires rather than rate limiting.
    """
    try:
        # Access the tracker through app.user_middleware (pre-build middleware list)
        for mw in getattr(app, "user_middleware", []):
            cls = getattr(mw, "cls", None)
            if cls is not None and cls.__name__ == "RateLimitMiddleware":
                # The kwargs dict contains initialization args but not the live instance.
                # The live middleware is wrapped inside the ASGI stack; we can't reach
                # it here. So we use the alternative approach below.
                break

        # Walk the built middleware stack to find the live RateLimitMiddleware instance
        _walk_and_clear_rate_limiter(app.middleware_stack)
    except Exception:
        pass  # Fail gracefully

    yield


def _walk_and_clear_rate_limiter(handler, depth: int = 0) -> bool:
    """Recursively walk the ASGI middleware stack to find RateLimitMiddleware."""
    if depth > 20:
        return False
    cls_name = type(handler).__name__
    if cls_name == "RateLimitMiddleware":
        if hasattr(handler, "tracker"):
            handler.tracker.requests.clear()
            if hasattr(handler.tracker, "blocked_ips"):
                handler.tracker.blocked_ips.clear()
        return True
    # Try common attribute names for the next handler in the chain
    for attr in ("app", "handler", "_app", "next"):
        child = getattr(handler, attr, None)
        if child is not None and child is not handler:
            if _walk_and_clear_rate_limiter(child, depth + 1):
                return True
    return False


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    # Disable raise_server_exceptions so we can inspect all responses
    return TestClient(app, raise_server_exceptions=False)


# Correct endpoint path (router prefix is /marketplace/sources, registered under /api/v1)
_SOURCES_ENDPOINT = "/api/v1/marketplace/sources"


@pytest.mark.security
class TestPathTraversalProtection:
    """Test path traversal protection on root_hint."""

    @pytest.mark.parametrize("malicious_hint", PATH_TRAVERSAL_PAYLOADS)
    def test_root_hint_blocks_path_traversal(
        self, client: TestClient, malicious_hint: str
    ):
        """Verify path traversal attempts are blocked.

        Args:
            client: FastAPI test client
            malicious_hint: Malicious path to test
        """
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
                "root_hint": malicious_hint,
            },
        )
        assert response.status_code in [
            400,
            422,
        ], f"Should block path traversal: {malicious_hint}"

        # Verify error message mentions the issue
        error_detail = response.json().get("detail", "")
        if isinstance(error_detail, list):
            # Pydantic validation errors are lists
            error_messages = " ".join(str(e) for e in error_detail)
        else:
            error_messages = str(error_detail)

        # Check that the error is about path validation
        assert any(
            keyword in error_messages.lower()
            for keyword in [
                "parent directory",
                "references",
                "..",
                "relative",
                "absolute",
                "traversal",
            ]
        ), f"Error should mention path issue. Got: {error_messages}"

    @pytest.mark.parametrize(
        "valid_hint",
        [
            "skills",
            "src/skills",
            ".claude/skills",
            "packages/my-package/skills",
            "deeply/nested/path/to/skills",
            "skill-folder",
            "my_skills",
            ".hidden",
        ],
    )
    def test_valid_root_hint_allowed(self, client: TestClient, valid_hint: str):
        """Verify valid root hints are allowed.

        Args:
            client: FastAPI test client
            valid_hint: Valid path to test
        """
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
                "root_hint": valid_hint,
            },
        )

        # Should not be rejected for path traversal (422 validation error)
        # May fail for other reasons (auth, repo not found, etc) but not path validation
        if response.status_code == 422:
            errors = response.json().get("detail", [])
            for error in errors:
                error_str = str(error).lower()
                # Ensure it's not a path traversal error
                assert "parent directory" not in error_str, (
                    f"Valid path rejected: {valid_hint}"
                )
                assert ".." not in error_str or "references" not in error_str, (
                    f"Valid path rejected: {valid_hint}"
                )
                assert "traversal" not in error_str, f"Valid path rejected: {valid_hint}"

    def test_root_hint_none_allowed(self, client: TestClient):
        """Verify that root_hint can be None or omitted.

        Args:
            client: FastAPI test client
        """
        # Test with None
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
                "root_hint": None,
            },
        )
        # Should not fail validation for None
        if response.status_code == 422:
            errors = response.json().get("detail", [])
            for error in errors:
                error_str = str(error).lower()
                assert "root_hint" not in error_str or "none" not in error_str

        # Test with omitted field
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
            },
        )
        # Should not fail validation when omitted
        if response.status_code == 422:
            errors = response.json().get("detail", [])
            for error in errors:
                error_str = str(error).lower()
                assert "root_hint" not in error_str or "required" not in error_str

    def test_root_hint_strips_whitespace(self, client: TestClient):
        """Verify that root_hint strips leading/trailing whitespace.

        Args:
            client: FastAPI test client
        """
        # This test verifies the behavior, but won't fail the request
        # The actual stripping happens in the validator
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
                "root_hint": "  skills  ",
            },
        )

        # Should not fail validation for whitespace
        # The validator strips it automatically
        if response.status_code == 422:
            errors = response.json().get("detail", [])
            for error in errors:
                error_str = str(error).lower()
                # Make sure it's not complaining about whitespace
                assert "whitespace" not in error_str


@pytest.mark.security
class TestInvalidCharacterProtection:
    """Test protection against invalid characters in root_hint."""

    @pytest.mark.parametrize(
        "invalid_hint",
        [
            "skills<script>",
            'skills"test',
            "skills|rm -rf",
            "skills?test",
            "skills*test",
            "skills>output.txt",
        ],
    )
    def test_blocks_invalid_characters(
        self, client: TestClient, invalid_hint: str
    ):
        """Verify invalid characters are blocked.

        Args:
            client: FastAPI test client
            invalid_hint: Path with invalid characters
        """
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
                "root_hint": invalid_hint,
            },
        )

        assert response.status_code in [
            400,
            422,
        ], f"Should block invalid characters: {invalid_hint}"

        error_detail = response.json().get("detail", "")
        if isinstance(error_detail, list):
            error_messages = " ".join(str(e) for e in error_detail)
        else:
            error_messages = str(error_detail)

        assert "invalid" in error_messages.lower() or "character" in error_messages.lower(), (
            f"Error should mention invalid characters. Got: {error_messages}"
        )


@pytest.mark.security
class TestAbsolutePathProtection:
    """Test protection against absolute paths in root_hint."""

    @pytest.mark.parametrize(
        "absolute_path",
        [
            "/etc/passwd",
            "/home/user/secrets",
            "/var/log/system",
            "C:\\Windows\\System32",
            "D:\\data\\secrets",
            "E:\\users\\admin",
        ],
    )
    def test_blocks_absolute_paths(self, client: TestClient, absolute_path: str):
        """Verify absolute paths are blocked.

        Args:
            client: FastAPI test client
            absolute_path: Absolute path to test
        """
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
                "root_hint": absolute_path,
            },
        )

        assert response.status_code in [
            400,
            422,
        ], f"Should block absolute path: {absolute_path}"

        error_detail = response.json().get("detail", "")
        if isinstance(error_detail, list):
            error_messages = " ".join(str(e) for e in error_detail)
        else:
            error_messages = str(error_detail)

        assert "relative" in error_messages.lower() or "absolute" in error_messages.lower(), (
            f"Error should mention path type. Got: {error_messages}"
        )


@pytest.mark.security
class TestNullByteProtection:
    """Test protection against null byte injection in root_hint."""

    @pytest.mark.parametrize(
        "null_byte_path",
        [
            "skills\x00.txt",
            "skills/\x00/../../etc/passwd",
            "skills\x00/../../../etc/passwd",
            "\x00skills",
            "skills\x00",
        ],
    )
    def test_blocks_null_bytes(self, client: TestClient, null_byte_path: str):
        """Verify null bytes are blocked.

        Args:
            client: FastAPI test client
            null_byte_path: Path with null bytes
        """
        response = client.post(
            _SOURCES_ENDPOINT,
            json={
                "repo_url": "https://github.com/test/repo",
                "root_hint": null_byte_path,
            },
        )

        assert response.status_code in [
            400,
            422,
        ], f"Should block null bytes: {repr(null_byte_path)}"

        error_detail = response.json().get("detail", "")
        if isinstance(error_detail, list):
            error_messages = " ".join(str(e) for e in error_detail)
        else:
            error_messages = str(error_detail)

        # Validator checks for path traversal (..) before null bytes, so paths that
        # contain both ".." and null bytes may be caught by the traversal check first.
        assert (
            "null" in error_messages.lower()
            or "byte" in error_messages.lower()
            or "parent directory" in error_messages.lower()
            or "traversal" in error_messages.lower()
            or "invalid" in error_messages.lower()
        ), f"Error should mention null bytes or path traversal. Got: {error_messages}"
