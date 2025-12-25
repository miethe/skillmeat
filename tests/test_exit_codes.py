"""Tests for exit codes module."""

import pytest
from skillmeat.exit_codes import (
    ExitCodes,
    SUCCESS,
    GENERAL_ERROR,
    INVALID_USAGE,
    NOT_FOUND,
    CONFLICT,
    PERMISSION_DENIED,
)


class TestExitCodeValues:
    """Test exit code values match spec."""

    def test_success_is_zero(self):
        assert ExitCodes.SUCCESS == 0
        assert SUCCESS == 0

    def test_general_error_is_one(self):
        assert ExitCodes.GENERAL_ERROR == 1
        assert GENERAL_ERROR == 1

    def test_invalid_usage_is_two(self):
        assert ExitCodes.INVALID_USAGE == 2
        assert INVALID_USAGE == 2

    def test_not_found_is_three(self):
        assert ExitCodes.NOT_FOUND == 3
        assert NOT_FOUND == 3

    def test_conflict_is_four(self):
        assert ExitCodes.CONFLICT == 4
        assert CONFLICT == 4

    def test_permission_denied_is_five(self):
        assert ExitCodes.PERMISSION_DENIED == 5
        assert PERMISSION_DENIED == 5


class TestDescribe:
    """Test describe() method."""

    def test_describes_success(self):
        assert ExitCodes.describe(0) == "Success"

    def test_describes_not_found(self):
        assert ExitCodes.describe(3) == "Not found"

    def test_describes_unknown(self):
        assert "Unknown" in ExitCodes.describe(99)


class TestForError:
    """Test for_error() method."""

    def test_file_not_found_returns_not_found(self):
        assert ExitCodes.for_error(FileNotFoundError()) == NOT_FOUND

    def test_permission_error_returns_permission_denied(self):
        assert ExitCodes.for_error(PermissionError()) == PERMISSION_DENIED

    def test_value_error_returns_invalid_usage(self):
        assert ExitCodes.for_error(ValueError()) == INVALID_USAGE

    def test_unknown_returns_general_error(self):
        assert ExitCodes.for_error(RuntimeError()) == GENERAL_ERROR
