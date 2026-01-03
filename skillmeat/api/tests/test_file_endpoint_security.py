"""Security tests for marketplace file endpoints.

Tests path traversal prevention, input validation, and content sanitization
for the file tree and file content endpoints.
"""

import pytest
from fastapi import HTTPException

from skillmeat.api.routers.marketplace_sources import (
    validate_file_path,
    validate_source_id,
)


class TestValidateFilePath:
    """Tests for validate_file_path security function."""

    def test_valid_simple_path(self) -> None:
        """Test that simple valid paths pass validation."""
        result = validate_file_path("SKILL.md")
        assert result == "SKILL.md"

    def test_valid_nested_path(self) -> None:
        """Test that nested paths are allowed."""
        result = validate_file_path("src/components/Button.tsx")
        assert result == "src/components/Button.tsx"

    def test_valid_deep_path(self) -> None:
        """Test deeply nested paths pass validation."""
        result = validate_file_path("a/b/c/d/e/f/g/file.txt")
        assert result == "a/b/c/d/e/f/g/file.txt"

    def test_normalizes_windows_separators(self) -> None:
        """Test that Windows path separators are normalized to Unix."""
        result = validate_file_path("src\\components\\Button.tsx")
        assert result == "src/components/Button.tsx"

    # Path traversal attack tests

    def test_rejects_parent_directory_reference(self) -> None:
        """Test that .. path traversal is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "path traversal not allowed" in exc_info.value.detail

    def test_rejects_dotdot_in_middle(self) -> None:
        """Test that .. in the middle of path is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("src/../../../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "path traversal not allowed" in exc_info.value.detail

    def test_rejects_dotdot_at_end(self) -> None:
        """Test that .. at end of path is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("valid/path/..")
        assert exc_info.value.status_code == 400
        assert "path traversal not allowed" in exc_info.value.detail

    def test_rejects_windows_path_traversal(self) -> None:
        """Test that Windows-style path traversal is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("..\\..\\etc\\passwd")
        assert exc_info.value.status_code == 400
        assert "path traversal not allowed" in exc_info.value.detail

    def test_rejects_mixed_separator_traversal(self) -> None:
        """Test that mixed separator traversal is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("src\\..\\../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "path traversal not allowed" in exc_info.value.detail

    # Absolute path tests

    def test_rejects_absolute_path_unix(self) -> None:
        """Test that absolute Unix paths are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("/etc/passwd")
        assert exc_info.value.status_code == 400
        assert "absolute paths not allowed" in exc_info.value.detail

    def test_rejects_absolute_path_after_normalization(self) -> None:
        """Test absolute path detection after backslash normalization."""
        # After normalizing \\ to /, this becomes an absolute path
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("\\etc\\passwd")
        assert exc_info.value.status_code == 400
        assert "absolute paths not allowed" in exc_info.value.detail

    # Null byte injection tests

    def test_rejects_null_byte(self) -> None:
        """Test that null bytes are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("test\x00.md")
        assert exc_info.value.status_code == 400
        assert "null bytes not allowed" in exc_info.value.detail

    def test_rejects_null_byte_in_middle(self) -> None:
        """Test null byte in middle of path."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("src/test\x00/../../../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "null bytes not allowed" in exc_info.value.detail

    # URL-encoded traversal tests

    def test_rejects_url_encoded_dotdot(self) -> None:
        """Test that URL-encoded .. (%2e%2e) is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("src/%2e%2e/etc/passwd")
        assert exc_info.value.status_code == 400
        assert "encoded traversal not allowed" in exc_info.value.detail

    def test_rejects_double_url_encoded_dotdot(self) -> None:
        """Test that double URL-encoded .. (%252e%252e) is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("src/%252e%252e/etc/passwd")
        assert exc_info.value.status_code == 400
        assert "encoded traversal not allowed" in exc_info.value.detail

    def test_rejects_mixed_case_url_encoded(self) -> None:
        """Test case-insensitive URL encoding detection."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path("src/%2E%2e/etc")
        assert exc_info.value.status_code == 400
        assert "encoded traversal not allowed" in exc_info.value.detail

    # Edge cases

    def test_allows_dots_in_filename(self) -> None:
        """Test that dots in filenames are allowed (not traversal)."""
        result = validate_file_path("file.name.with.dots.txt")
        assert result == "file.name.with.dots.txt"

    def test_allows_single_dot_directory(self) -> None:
        """Test that single dot directories are allowed."""
        result = validate_file_path("./src/file.txt")
        assert result == "./src/file.txt"

    def test_allows_dotfiles(self) -> None:
        """Test that dotfiles like .gitignore are allowed."""
        result = validate_file_path(".gitignore")
        assert result == ".gitignore"

    def test_allows_dotdirectories(self) -> None:
        """Test that dot directories like .github are allowed."""
        result = validate_file_path(".github/workflows/ci.yml")
        assert result == ".github/workflows/ci.yml"


class TestValidateSourceId:
    """Tests for validate_source_id security function."""

    def test_valid_uuid_format(self) -> None:
        """Test that UUID-format source IDs pass."""
        result = validate_source_id("abc123-def456-789")
        assert result == "abc123-def456-789"

    def test_valid_alphanumeric(self) -> None:
        """Test that alphanumeric source IDs pass."""
        result = validate_source_id("source123")
        assert result == "source123"

    def test_valid_with_dashes(self) -> None:
        """Test that source IDs with dashes pass."""
        result = validate_source_id("my-source-id")
        assert result == "my-source-id"

    def test_rejects_path_traversal_in_source_id(self) -> None:
        """Test that path traversal in source_id is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_source_id("../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "Invalid source ID format" in exc_info.value.detail

    def test_rejects_special_characters(self) -> None:
        """Test that special characters are rejected."""
        invalid_ids = [
            "source/id",
            "source\\id",
            "source;id",
            "source|id",
            "source`id",
            "source$id",
            "source id",  # space
        ]
        for invalid_id in invalid_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_source_id(invalid_id)
            assert exc_info.value.status_code == 400
            assert "Invalid source ID format" in exc_info.value.detail

    def test_rejects_null_byte_in_source_id(self) -> None:
        """Test that null bytes in source_id are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_source_id("source\x00id")
        assert exc_info.value.status_code == 400
        assert "Invalid source ID format" in exc_info.value.detail


class TestPathTraversalVectors:
    """Test comprehensive path traversal attack vectors."""

    @pytest.mark.parametrize(
        "malicious_path",
        [
            # Basic traversal
            "../",
            "../../",
            "../../../etc/passwd",
            # Windows-style
            "..\\",
            "..\\..\\",
            "..\\..\\..\\windows\\system32",
            # Mixed separators
            "../..\\../",
            "..\\../..\\",
            # With valid prefix
            "valid/../../../",
            "src/file/../../..",
            # Trailing traversal
            "src/file/..",
            # Multiple levels
            "a/b/c/../../../..",
            # With filename
            "../../../etc/passwd",
            "..\\..\\boot.ini",
        ],
    )
    def test_rejects_traversal_vector(self, malicious_path: str) -> None:
        """Test that various traversal vectors are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path(malicious_path)
        assert exc_info.value.status_code == 400
        # Should be rejected for either traversal or absolute path
        assert "not allowed" in exc_info.value.detail

    @pytest.mark.parametrize(
        "malicious_path",
        [
            # Null byte attacks
            "file.txt\x00.jpg",
            "../../etc/passwd\x00.txt",
            "\x00../etc/passwd",
        ],
    )
    def test_rejects_null_byte_vector(self, malicious_path: str) -> None:
        """Test that null byte injection vectors are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path(malicious_path)
        assert exc_info.value.status_code == 400
        assert "null bytes not allowed" in exc_info.value.detail

    @pytest.mark.parametrize(
        "malicious_path",
        [
            "/etc/passwd",
            "/var/log/secure",
            "//network/share",
        ],
    )
    def test_rejects_absolute_path_vector(self, malicious_path: str) -> None:
        """Test that absolute path vectors are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_path(malicious_path)
        assert exc_info.value.status_code == 400
        assert "absolute paths not allowed" in exc_info.value.detail


class TestValidPathPatterns:
    """Test that valid paths are correctly allowed."""

    @pytest.mark.parametrize(
        "valid_path",
        [
            # Simple files
            "README.md",
            "SKILL.md",
            "package.json",
            # Nested paths
            "src/index.ts",
            "src/components/Button.tsx",
            "lib/utils/helpers.py",
            # Deep nesting
            "a/b/c/d/e/f/g/h/file.txt",
            # Dotfiles and directories
            ".gitignore",
            ".github/workflows/ci.yml",
            ".claude/CLAUDE.md",
            # Files with dots in name
            "module.test.ts",
            "file.config.local.json",
            # Underscores and hyphens
            "my_module/some-file.txt",
            "__init__.py",
            "test-data.json",
        ],
    )
    def test_allows_valid_path(self, valid_path: str) -> None:
        """Test that valid paths are allowed through."""
        result = validate_file_path(valid_path)
        # Should return normalized path (Windows separators converted)
        assert result == valid_path.replace("\\", "/")
