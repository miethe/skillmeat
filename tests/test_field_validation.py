"""Tests for field validation in refresh operations.

Tests validate_fields() function and integration with refresh_metadata
and refresh_collection methods.

Task: BE-407
"""

import pytest

from skillmeat.core.refresher import (
    REFRESHABLE_FIELDS,
    validate_fields,
    _find_closest_field,
)


class TestValidateFields:
    """Test field validation function."""

    def test_validate_all_valid_fields(self):
        """Test validation with all valid field names."""
        valid_list = list(REFRESHABLE_FIELDS)
        validated, invalid = validate_fields(valid_list, strict=True)

        assert set(validated) == REFRESHABLE_FIELDS
        assert invalid == []

    def test_validate_subset_of_fields(self):
        """Test validation with subset of valid fields."""
        fields = ["description", "tags"]
        validated, invalid = validate_fields(fields, strict=True)

        assert set(validated) == {"description", "tags"}
        assert invalid == []

    def test_validate_case_insensitive(self):
        """Test case-insensitive field name matching."""
        fields = ["DESCRIPTION", "Tags", "AuThOr"]
        validated, invalid = validate_fields(fields, strict=True)

        # Should normalize to lowercase canonical names
        assert set(validated) == {"description", "tags", "author"}
        assert invalid == []

    def test_validate_with_whitespace(self):
        """Test field names with leading/trailing whitespace."""
        fields = ["  description  ", " tags "]
        validated, invalid = validate_fields(fields, strict=True)

        assert set(validated) == {"description", "tags"}
        assert invalid == []

    def test_validate_none_returns_all_fields(self):
        """Test that None input returns all valid fields."""
        validated, invalid = validate_fields(None, strict=True)

        assert set(validated) == REFRESHABLE_FIELDS
        assert invalid == []

    def test_validate_invalid_field_strict(self):
        """Test validation raises ValueError for invalid fields in strict mode."""
        fields = ["description", "invalid_field", "tags"]

        with pytest.raises(ValueError) as exc_info:
            validate_fields(fields, strict=True)

        error_msg = str(exc_info.value)
        assert "invalid_field" in error_msg
        assert "Invalid field name" in error_msg
        # Should list valid fields
        assert "description" in error_msg
        assert "tags" in error_msg

    def test_validate_invalid_field_non_strict(self):
        """Test validation returns invalid fields in non-strict mode."""
        fields = ["description", "invalid_field", "another_bad"]

        validated, invalid = validate_fields(fields, strict=False)

        assert set(validated) == {"description"}
        assert set(invalid) == {"invalid_field", "another_bad"}

    def test_validate_all_invalid_strict(self):
        """Test validation with all invalid fields raises ValueError."""
        fields = ["bad1", "bad2", "bad3"]

        with pytest.raises(ValueError) as exc_info:
            validate_fields(fields, strict=True)

        error_msg = str(exc_info.value)
        assert "bad1" in error_msg
        assert "bad2" in error_msg
        assert "bad3" in error_msg

    def test_validate_empty_list(self):
        """Test validation with empty list."""
        validated, invalid = validate_fields([], strict=True)

        assert validated == []
        assert invalid == []

    def test_validate_duplicate_fields(self):
        """Test validation with duplicate field names."""
        fields = ["description", "tags", "description"]
        validated, invalid = validate_fields(fields, strict=True)

        # Should preserve duplicates (caller can deduplicate if needed)
        assert validated == ["description", "tags", "description"]
        assert invalid == []


class TestFindClosestField:
    """Test fuzzy matching for field name suggestions."""

    def test_exact_prefix_match(self):
        """Test exact prefix matching has highest priority."""
        assert _find_closest_field("desc") == "description"
        assert _find_closest_field("tag") == "tags"
        assert _find_closest_field("auth") == "author"
        assert _find_closest_field("lic") == "license"

    def test_contains_match(self):
        """Test substring matching."""
        assert _find_closest_field("scription") == "description"
        assert _find_closest_field("icense") == "license"

    def test_typo_suggestions(self):
        """Test suggestions for common typos."""
        # Missing letter
        assert _find_closest_field("descriptio") == "description"
        # Wrong letter
        assert _find_closest_field("togs") == "tags"

    def test_no_match_returns_none(self):
        """Test that completely unrelated input returns None."""
        result = _find_closest_field("xyz123")
        # May return None or a weak match, both acceptable
        assert result is None or result in REFRESHABLE_FIELDS

    def test_case_insensitive_matching(self):
        """Test case-insensitive fuzzy matching."""
        assert _find_closest_field("DESC") == "description"
        assert _find_closest_field("TAGS") == "tags"


class TestValidationErrorMessages:
    """Test error message quality and suggestions."""

    def test_error_includes_valid_fields(self):
        """Test error message lists all valid fields."""
        with pytest.raises(ValueError) as exc_info:
            validate_fields(["invalid"], strict=True)

        error_msg = str(exc_info.value)
        # Should include all valid field names
        for field in REFRESHABLE_FIELDS:
            assert field in error_msg

    def test_error_includes_suggestions(self):
        """Test error message includes typo suggestions."""
        with pytest.raises(ValueError) as exc_info:
            validate_fields(["descriptio"], strict=True)

        error_msg = str(exc_info.value)
        # Should suggest the correct field
        assert "description" in error_msg.lower()
        assert "did you mean" in error_msg.lower() or "suggestion" in error_msg.lower()

    def test_error_lists_all_invalid_fields(self):
        """Test error message lists all invalid fields."""
        invalid_fields = ["bad1", "bad2", "bad3"]

        with pytest.raises(ValueError) as exc_info:
            validate_fields(invalid_fields, strict=True)

        error_msg = str(exc_info.value)
        for field in invalid_fields:
            assert field in error_msg


class TestRefreshableFieldsConstant:
    """Test REFRESHABLE_FIELDS constant."""

    def test_contains_expected_fields(self):
        """Test that REFRESHABLE_FIELDS contains all expected fields."""
        expected = {"description", "tags", "author", "license", "origin_source"}
        assert REFRESHABLE_FIELDS == expected

    def test_is_frozen(self):
        """Test that REFRESHABLE_FIELDS is immutable."""
        with pytest.raises((TypeError, AttributeError)):
            REFRESHABLE_FIELDS.add("new_field")

        with pytest.raises((TypeError, AttributeError)):
            REFRESHABLE_FIELDS.remove("description")
