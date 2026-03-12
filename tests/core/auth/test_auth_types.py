"""Tests for OwnerType enum and schema validators using it.

Covers:
  - OwnerType enum completeness and string values
  - Backward compatibility (user, team) and new enterprise value
  - Invalid value rejection
  - Schema validators in ArtifactCreateRequest, ArtifactUpdateRequest,
    CollectionCreateRequest, and CollectionUpdateRequest
"""

from typing import Any

import pytest
from pydantic import ValidationError

from skillmeat.cache.auth_types import OwnerType
from skillmeat.api.schemas.artifacts import ArtifactCreateRequest, ArtifactSourceType
from skillmeat.api.schemas.collections import (
    CollectionCreateRequest,
    CollectionUpdateRequest,
)


# =============================================================================
# OwnerType enum
# =============================================================================


class TestOwnerTypeEnum:
    """Tests for the OwnerType enum definition."""

    def test_has_exactly_three_members(self):
        """OwnerType must have exactly user, team, and enterprise."""
        assert len(OwnerType) == 3

    def test_member_names(self):
        """All three expected names are present."""
        names = {m.name for m in OwnerType}
        assert names == {"user", "team", "enterprise"}

    def test_string_values(self):
        """Each member's value is the expected lowercase string."""
        assert OwnerType.user.value == "user"
        assert OwnerType.team.value == "team"
        assert OwnerType.enterprise.value == "enterprise"

    def test_is_str_subclass(self):
        """OwnerType members compare equal to their string values."""
        assert OwnerType.user == "user"
        assert OwnerType.team == "team"
        assert OwnerType.enterprise == "enterprise"

    # ------------------------------------------------------------------
    # Construction from raw string
    # ------------------------------------------------------------------

    def test_construct_user(self):
        """OwnerType('user') returns the user member."""
        assert OwnerType("user") is OwnerType.user

    def test_construct_team(self):
        """OwnerType('team') returns the team member (backward compat)."""
        assert OwnerType("team") is OwnerType.team

    def test_construct_enterprise(self):
        """OwnerType('enterprise') returns the enterprise member."""
        assert OwnerType("enterprise") is OwnerType.enterprise

    def test_invalid_value_raises(self):
        """OwnerType with an unrecognised string raises ValueError."""
        with pytest.raises(ValueError):
            OwnerType("invalid")

    def test_empty_string_raises(self):
        """OwnerType with an empty string raises ValueError."""
        with pytest.raises(ValueError):
            OwnerType("")

    def test_case_sensitive(self):
        """OwnerType values are lowercase; uppercase variants are rejected."""
        with pytest.raises(ValueError):
            OwnerType("User")
        with pytest.raises(ValueError):
            OwnerType("ENTERPRISE")


# =============================================================================
# ArtifactCreateRequest schema — owner_type validator
# =============================================================================


def _minimal_artifact_payload(**overrides: Any) -> dict[str, Any]:
    """Return the minimum required fields for ArtifactCreateRequest."""
    base: dict[str, Any] = {
        "source_type": ArtifactSourceType.GITHUB,
        "source": "owner/repo",
        "artifact_type": "skill",
    }
    base.update(overrides)
    return base


class TestArtifactCreateRequestOwnerType:
    """Schema validation tests for owner_type on ArtifactCreateRequest."""

    def test_owner_type_omitted_is_valid(self):
        """owner_type is optional; omitting it produces a valid model."""
        req = ArtifactCreateRequest(**_minimal_artifact_payload())
        assert req.owner_type is None

    def test_owner_type_none_is_valid(self):
        """Explicitly passing owner_type=None is valid."""
        req = ArtifactCreateRequest(**_minimal_artifact_payload(owner_type=None))
        assert req.owner_type is None

    def test_owner_type_user(self):
        """'user' is accepted (backward compat)."""
        req = ArtifactCreateRequest(**_minimal_artifact_payload(owner_type="user"))
        assert req.owner_type == "user"

    def test_owner_type_team(self):
        """'team' is accepted (backward compat)."""
        req = ArtifactCreateRequest(**_minimal_artifact_payload(owner_type="team"))
        assert req.owner_type == "team"

    def test_owner_type_enterprise(self):
        """'enterprise' is accepted (new value)."""
        req = ArtifactCreateRequest(
            **_minimal_artifact_payload(owner_type="enterprise")
        )
        assert req.owner_type == "enterprise"

    def test_owner_type_invalid_raises(self):
        """An unrecognised owner_type raises ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactCreateRequest(**_minimal_artifact_payload(owner_type="org"))

    def test_owner_type_empty_string_raises(self):
        """An empty string owner_type raises ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactCreateRequest(**_minimal_artifact_payload(owner_type=""))

    def test_owner_type_uppercase_raises(self):
        """Uppercase values are rejected."""
        with pytest.raises(ValidationError):
            ArtifactCreateRequest(**_minimal_artifact_payload(owner_type="User"))


# =============================================================================
# CollectionCreateRequest schema — owner_type validator
# =============================================================================


class TestCollectionCreateRequestOwnerType:
    """Schema validation tests for owner_type on CollectionCreateRequest."""

    def test_owner_type_omitted_is_valid(self):
        """owner_type is optional for collection creation."""
        req = CollectionCreateRequest(name="my-col")
        assert req.owner_type is None

    def test_owner_type_user(self):
        """'user' is accepted."""
        req = CollectionCreateRequest(name="my-col", owner_type="user")
        assert req.owner_type == "user"

    def test_owner_type_team(self):
        """'team' is accepted."""
        req = CollectionCreateRequest(name="my-col", owner_type="team")
        assert req.owner_type == "team"

    def test_owner_type_enterprise(self):
        """'enterprise' is accepted."""
        req = CollectionCreateRequest(name="my-col", owner_type="enterprise")
        assert req.owner_type == "enterprise"

    def test_owner_type_invalid_raises(self):
        """An unrecognised value raises ValidationError."""
        with pytest.raises(ValidationError):
            CollectionCreateRequest(name="my-col", owner_type="department")

    def test_owner_type_empty_string_raises(self):
        """An empty string raises ValidationError."""
        with pytest.raises(ValidationError):
            CollectionCreateRequest(name="my-col", owner_type="")


# =============================================================================
# CollectionUpdateRequest schema — owner_type validator
# =============================================================================


class TestCollectionUpdateRequestOwnerType:
    """Schema validation tests for owner_type on CollectionUpdateRequest."""

    def test_owner_type_omitted_is_valid(self):
        """All fields are optional on an update request."""
        req = CollectionUpdateRequest()
        assert req.owner_type is None

    def test_owner_type_user(self):
        """'user' is accepted in an update."""
        req = CollectionUpdateRequest(owner_type="user")
        assert req.owner_type == "user"

    def test_owner_type_team(self):
        """'team' is accepted in an update."""
        req = CollectionUpdateRequest(owner_type="team")
        assert req.owner_type == "team"

    def test_owner_type_enterprise(self):
        """'enterprise' is accepted in an update."""
        req = CollectionUpdateRequest(owner_type="enterprise")
        assert req.owner_type == "enterprise"

    def test_owner_type_invalid_raises(self):
        """An unrecognised value raises ValidationError."""
        with pytest.raises(ValidationError):
            CollectionUpdateRequest(owner_type="root")
