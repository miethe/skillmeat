"""Tests for Project API schema validation.

This module tests the validation rules for project creation and update endpoints,
including name format validation, path validation, and error message clarity.
"""

import os
import platform
import pytest
from pydantic import ValidationError

from skillmeat.api.schemas.projects import ProjectCreateRequest, ProjectUpdateRequest


class TestProjectCreateRequestNameValidation:
    """Test name validation in ProjectCreateRequest."""

    def test_valid_name_simple(self):
        """Test simple valid project name."""
        request = ProjectCreateRequest(
            name="myproject",
            path="/home/user/projects/myproject"
        )
        assert request.name == "myproject"

    def test_valid_name_with_hyphens(self):
        """Test valid name with hyphens."""
        request = ProjectCreateRequest(
            name="my-awesome-project",
            path="/home/user/projects/my-awesome-project"
        )
        assert request.name == "my-awesome-project"

    def test_valid_name_with_underscores(self):
        """Test valid name with underscores."""
        request = ProjectCreateRequest(
            name="my_awesome_project",
            path="/home/user/projects/my_awesome_project"
        )
        assert request.name == "my_awesome_project"

    def test_valid_name_mixed_separators(self):
        """Test valid name with mixed hyphens and underscores."""
        request = ProjectCreateRequest(
            name="my-awesome_project",
            path="/home/user/projects/my-awesome_project"
        )
        assert request.name == "my-awesome_project"

    def test_valid_name_with_numbers(self):
        """Test valid name with numbers."""
        request = ProjectCreateRequest(
            name="project123",
            path="/home/user/projects/project123"
        )
        assert request.name == "project123"

    def test_valid_single_character_name(self):
        """Test valid single character name."""
        request = ProjectCreateRequest(
            name="a",
            path="/home/user/projects/a"
        )
        assert request.name == "a"

    def test_valid_name_max_length(self):
        """Test valid name at max length (100 characters)."""
        long_name = "a" * 100
        request = ProjectCreateRequest(
            name=long_name,
            path="/home/user/projects/test"
        )
        assert request.name == long_name

    def test_invalid_name_starts_with_hyphen(self):
        """Test name starting with hyphen is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="-myproject",
                path="/home/user/projects/myproject"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)

    def test_invalid_name_starts_with_underscore(self):
        """Test name starting with underscore is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="_myproject",
                path="/home/user/projects/myproject"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)

    def test_invalid_name_ends_with_hyphen(self):
        """Test name ending with hyphen is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="myproject-",
                path="/home/user/projects/myproject"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)

    def test_invalid_name_ends_with_underscore(self):
        """Test name ending with underscore is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="myproject_",
                path="/home/user/projects/myproject"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)

    def test_invalid_name_with_spaces(self):
        """Test name with spaces is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="my project",
                path="/home/user/projects/myproject"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)

    def test_invalid_name_with_special_chars(self):
        """Test name with special characters is rejected."""
        invalid_names = [
            "project@name",
            "project#name",
            "project$name",
            "project%name",
            "project&name",
            "project*name",
            "project.name",
            "project/name",
        ]
        for invalid_name in invalid_names:
            with pytest.raises(ValidationError):
                ProjectCreateRequest(
                    name=invalid_name,
                    path="/home/user/projects/test"
                )

    def test_invalid_name_empty(self):
        """Test empty name is rejected."""
        with pytest.raises(ValidationError):
            ProjectCreateRequest(
                name="",
                path="/home/user/projects/test"
            )

    def test_invalid_name_exceeds_max_length(self):
        """Test name exceeding max length (100 chars) is rejected."""
        long_name = "a" * 101
        with pytest.raises(ValidationError):
            ProjectCreateRequest(
                name=long_name,
                path="/home/user/projects/test"
            )


class TestProjectCreateRequestPathValidation:
    """Test path validation in ProjectCreateRequest."""

    def test_valid_path_unix_absolute(self):
        """Test valid Unix absolute path."""
        request = ProjectCreateRequest(
            name="myproject",
            path="/home/user/projects/myproject"
        )
        assert request.path == "/home/user/projects/myproject"

    def test_valid_path_unix_root(self):
        """Test valid path at Unix root."""
        request = ProjectCreateRequest(
            name="test",
            path="/tmp/test"
        )
        assert request.path == "/tmp/test"

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows path test"
    )
    def test_valid_path_windows_absolute(self):
        """Test valid Windows absolute path (C: drive)."""
        request = ProjectCreateRequest(
            name="myproject",
            path="C:\\Users\\john\\projects\\myproject"
        )
        assert request.path == "C:\\Users\\john\\projects\\myproject"

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows path test"
    )
    def test_valid_path_windows_different_drive(self):
        """Test valid Windows absolute path (D: drive)."""
        request = ProjectCreateRequest(
            name="myproject",
            path="D:\\projects\\myproject"
        )
        assert request.path == "D:\\projects\\myproject"

    def test_invalid_path_relative(self):
        """Test relative path is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="myproject",
                path="projects/myproject"
            )
        error_str = str(exc_info.value)
        assert "absolute path" in error_str

    def test_invalid_path_tilde_expansion(self):
        """Test tilde path (unexpanded) is rejected as relative."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="myproject",
                path="~/projects/myproject"
            )
        error_str = str(exc_info.value)
        assert "absolute path" in error_str

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix-specific test"
    )
    def test_invalid_path_windows_on_unix(self):
        """Test Windows path on Unix is treated as relative."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="myproject",
                path="C:\\Users\\john\\projects"
            )
        error_str = str(exc_info.value)
        assert "absolute path" in error_str

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix-specific test"
    )
    def test_invalid_path_contains_null_char(self):
        """Test path with null character is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="myproject",
                path="/home/user\x00/projects"
            )
        error_str = str(exc_info.value)
        assert "null character" in error_str or "Invalid path" in error_str

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows-specific test"
    )
    def test_invalid_path_windows_reserved_chars(self):
        """Test Windows reserved characters in path are rejected."""
        invalid_paths = [
            'C:\\Users\\john\\project<test>',
            'C:\\Users\\john\\project|test',
            'C:\\Users\\john\\project"test',
            'C:\\Users\\john\\project?test',
            'C:\\Users\\john\\project*test',
        ]
        for path in invalid_paths:
            with pytest.raises(ValidationError):
                ProjectCreateRequest(
                    name="test",
                    path=path
                )

    def test_path_with_spaces(self):
        """Test path with spaces is valid."""
        request = ProjectCreateRequest(
            name="myproject",
            path="/home/user/my projects/myproject"
        )
        assert request.path == "/home/user/my projects/myproject"

    def test_path_with_special_valid_chars(self):
        """Test path with valid special characters."""
        request = ProjectCreateRequest(
            name="myproject",
            path="/home/user-john/my_projects/my.project"
        )
        assert request.path == "/home/user-john/my_projects/my.project"


class TestProjectUpdateRequestNameValidation:
    """Test name validation in ProjectUpdateRequest."""

    def test_update_valid_name(self):
        """Test updating to valid name."""
        request = ProjectUpdateRequest(
            name="new-project-name",
            description="New description"
        )
        assert request.name == "new-project-name"

    def test_update_no_name_provided(self):
        """Test update with no name (None) is valid."""
        request = ProjectUpdateRequest(
            description="Only updating description"
        )
        assert request.name is None
        assert request.description == "Only updating description"

    def test_update_only_name(self):
        """Test updating only the name."""
        request = ProjectUpdateRequest(
            name="only-name-update"
        )
        assert request.name == "only-name-update"
        assert request.description is None

    def test_update_invalid_name_with_hyphen_start(self):
        """Test invalid name in update request."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectUpdateRequest(
                name="-invalid",
                description="Some description"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)

    def test_update_invalid_name_with_hyphen_end(self):
        """Test invalid name ending with hyphen."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectUpdateRequest(
                name="invalid-",
                description="Some description"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)

    def test_update_invalid_name_with_spaces(self):
        """Test invalid name with spaces."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectUpdateRequest(
                name="invalid name"
            )
        assert "must start and end with alphanumeric" in str(exc_info.value)


class TestProjectRequestIntegration:
    """Integration tests for request validation."""

    def test_create_request_all_fields_valid(self):
        """Test creating request with all fields valid."""
        request = ProjectCreateRequest(
            name="my-awesome-project",
            path="/home/john/projects/my-awesome-project",
            description="A project for managing Claude configurations"
        )
        assert request.name == "my-awesome-project"
        assert request.path == "/home/john/projects/my-awesome-project"
        assert request.description == "A project for managing Claude configurations"

    def test_create_request_no_description(self):
        """Test creating request without description."""
        request = ProjectCreateRequest(
            name="my-project",
            path="/home/john/projects/my-project"
        )
        assert request.name == "my-project"
        assert request.path == "/home/john/projects/my-project"
        assert request.description is None

    def test_validation_error_contains_helpful_message(self):
        """Test that validation errors contain helpful messages."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="my-invalid-",
                path="invalid/relative/path"
            )
        # Should have errors for both name and path
        errors = exc_info.value.errors()
        assert len(errors) >= 2  # At least 2 validation errors

    def test_error_message_for_invalid_name(self):
        """Test error message clarity for invalid name."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="-startwithhyphen",
                path="/home/test"
            )
        error_str = str(exc_info.value)
        assert "alphanumeric" in error_str.lower()
        assert "letter" in error_str.lower() or "number" in error_str.lower()

    def test_error_message_for_invalid_path(self):
        """Test error message clarity for invalid path."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="valid-name",
                path="relative/path"
            )
        error_str = str(exc_info.value)
        assert "absolute" in error_str.lower()

    def test_pydantic_validation_returns_422_details(self):
        """Test that Pydantic validation errors are properly formatted."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                name="bad-name-",
                path="not/absolute"
            )
        errors = exc_info.value.errors()
        # Verify error structure for API 422 response
        assert isinstance(errors, list)
        assert all("loc" in err for err in errors)
        assert all("msg" in err for err in errors)
        assert all("type" in err for err in errors)
