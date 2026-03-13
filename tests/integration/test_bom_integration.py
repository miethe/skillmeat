"""Integration tests for SkillBOM: multi-artifact types, RBAC visibility, and
API/CLI data consistency.

Three test scenarios are covered:

1. ``TestMultiArtifactBomGeneration`` — exercises ``BomGenerator`` with all
   supported artifact types (skill, command, agent, mcp_server, hook,
   composite), verifying entries, hashes, metadata, schema version, and count.

2. ``TestRbacVisibilityEnforcement`` — creates ``AttestationRecord`` instances
   with different owner scopes (user, team, enterprise) and asserts that
   ``AttestationScopeResolver.filter_visible`` enforces the expected visibility
   boundaries.  These tests run entirely in-memory (no DB) following the same
   pattern established in ``skillmeat/api/tests/test_bom_attestation_rbac.py``.

3. ``TestApiCliDataConsistency`` — builds a shared in-memory data set, queries
   it via the ``BomGenerator`` (service layer), serialises the output through
   ``BomSchema`` (API layer), and asserts that field names, timestamps, and
   counts are consistent across both surfaces.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.auth_types import OwnerType, Visibility
from skillmeat.cache.models import (
    Artifact,
    AttestationRecord,
    Base,
    Project,
)
from skillmeat.core.bom.generator import BomGenerator
from skillmeat.core.bom.policy import AttestationPolicyEnforcer, PolicyValidationResult
from skillmeat.core.bom.scope import AttestationScopeResolver, OwnershipResolver


# =============================================================================
# Shared DB Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def db_session(tmp_path: Path) -> Session:
    """Provide a clean, isolated SQLite session for each test function.

    Creates all ORM tables via ``Base.metadata.create_all`` so that tests are
    independent of Alembic and run quickly in memory.

    Yields:
        An open SQLAlchemy ``Session`` backed by a per-test SQLite file.
    """
    db_file = tmp_path / "test_bom.db"
    engine = create_engine(f"sqlite:///{db_file}", echo=False)
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)
    session: Session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def sample_project(db_session: Session) -> Project:
    """Insert and return a minimal ``Project`` row for use in BOM tests."""
    project = Project(
        id="proj-bom-test",
        name="BOM Integration Test Project",
        path="/tmp/bom-test-project",
    )
    db_session.add(project)
    db_session.flush()
    return project


# =============================================================================
# Helpers
# =============================================================================


def _make_artifact(
    project_id: str,
    name: str,
    artifact_type: str,
    *,
    source: str = "user/repo/artifact@v1.0.0",
    deployed_version: str = "1.0.0",
    content: Optional[str] = None,
) -> Artifact:
    """Build an ``Artifact`` ORM instance suitable for BOM testing.

    The ``id`` follows the ``type:name`` convention used throughout the codebase.
    A stable UUID hex is computed deterministically from the id so that
    assertions on ``artifact.uuid`` are reproducible.

    Args:
        project_id: Parent project identifier.
        name: Artifact name.
        artifact_type: Type string (e.g. ``"skill"``).
        source: Optional source specifier.
        deployed_version: Deployed version string.
        content: Optional text content — used as the fallback hash source.

    Returns:
        Unsaved ``Artifact`` instance.
    """
    art_id = f"{artifact_type}:{name}"
    stable_uuid = hashlib.md5(art_id.encode()).hexdigest()
    return Artifact(
        id=art_id,
        uuid=stable_uuid,
        project_id=project_id,
        name=name,
        type=artifact_type,
        source=source,
        deployed_version=deployed_version,
        upstream_version=deployed_version,
        content=content or f"# {artifact_type} content for {name}",
        content_hash=hashlib.sha256(
            (content or f"# {artifact_type} content for {name}").encode()
        ).hexdigest(),
    )


def _make_mock_attestation_record(
    artifact_id: str = "skill:test-skill",
    owner_type: str = OwnerType.user.value,
    owner_id: str = "user-1",
    visibility: str = Visibility.private.value,
    roles: Optional[List[str]] = None,
    scopes: Optional[List[str]] = None,
) -> AttestationRecord:
    """Return a mock ``AttestationRecord`` for in-memory RBAC tests.

    The resolver reads only ``owner_type``, ``owner_id``, and ``visibility``.
    Using a ``MagicMock`` keeps tests decoupled from DB setup.
    """
    record = MagicMock(
        spec=["owner_type", "owner_id", "visibility", "artifact_id", "roles", "scopes"]
    )
    record.artifact_id = artifact_id
    record.owner_type = owner_type
    record.owner_id = owner_id
    record.visibility = visibility
    record.roles = roles or []
    record.scopes = scopes or []
    return record  # type: ignore[return-value]


# =============================================================================
# Scenario 1: Multi-artifact BOM generation
# =============================================================================


class TestMultiArtifactBomGeneration:
    """BomGenerator processes all supported artifact types and produces a valid BOM."""

    ARTIFACT_TYPES = [
        "skill",
        "command",
        "agent",
        "mcp_server",
        "hook",
        "composite",
    ]

    @pytest.fixture(autouse=True)
    def _populate_artifacts(self, db_session: Session, sample_project: Project) -> None:
        """Insert one artifact of each tested type into the session."""
        for artifact_type in self.ARTIFACT_TYPES:
            artifact = _make_artifact(
                project_id=sample_project.id,
                name=f"test-{artifact_type}",
                artifact_type=artifact_type,
                content=f"deterministic content for {artifact_type}",
            )
            db_session.add(artifact)
        db_session.commit()

    def test_bom_contains_all_artifact_types(self, db_session: Session) -> None:
        """BOM has one entry for every inserted artifact type."""
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        assert bom["artifact_count"] == len(self.ARTIFACT_TYPES)
        found_types = {entry["type"] for entry in bom["artifacts"]}
        assert found_types == set(self.ARTIFACT_TYPES)

    def test_each_entry_has_non_empty_content_hash(self, db_session: Session) -> None:
        """Every BOM entry carries a non-empty SHA-256 hex content hash.

        Adapters must fall back to the DB ``content_hash`` column when no
        filesystem path is available.
        """
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        for entry in bom["artifacts"]:
            assert entry["content_hash"], (
                f"Empty content_hash for artifact type={entry['type']!r}, "
                f"name={entry['name']!r}"
            )
            # SHA-256 hex strings are exactly 64 characters.
            assert len(entry["content_hash"]) == 64, (
                f"content_hash is not 64 chars for {entry['type']!r}:{entry['name']!r}"
            )

    def test_each_entry_has_required_fields(self, db_session: Session) -> None:
        """Every BOM entry exposes the required top-level fields."""
        required_keys = {"name", "type", "source", "version", "content_hash", "metadata"}
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        for entry in bom["artifacts"]:
            missing = required_keys - entry.keys()
            assert not missing, (
                f"Entry for {entry.get('type')!r}:{entry.get('name')!r} "
                f"is missing keys: {missing}"
            )

    def test_metadata_extracted_from_content_field(self, db_session: Session) -> None:
        """Metadata dict is non-None for every entry (may be empty but not missing)."""
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        for entry in bom["artifacts"]:
            assert isinstance(entry["metadata"], dict), (
                f"metadata is not a dict for {entry['type']!r}:{entry['name']!r}"
            )

    def test_bom_schema_version_is_present(self, db_session: Session) -> None:
        """Top-level BOM dict carries a non-empty ``schema_version`` string."""
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        assert "schema_version" in bom
        assert bom["schema_version"], "schema_version must not be empty"

    def test_bom_entries_sorted_by_type_then_name(self, db_session: Session) -> None:
        """BOM artifact list is deterministically sorted by (type, name)."""
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        entries = bom["artifacts"]
        sort_keys = [(e["type"], e["name"]) for e in entries]
        assert sort_keys == sorted(sort_keys), "BOM entries are not sorted by (type, name)"

    def test_bom_generated_at_is_valid_iso8601(self, db_session: Session) -> None:
        """``generated_at`` field parses as a valid ISO-8601 UTC timestamp."""
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        generated_at = bom["generated_at"]
        # datetime.fromisoformat raises ValueError on invalid input.
        ts = datetime.fromisoformat(generated_at)
        assert ts is not None

    def test_bom_metadata_block_contains_generator_key(self, db_session: Session) -> None:
        """The BOM ``metadata`` block includes the ``generator`` identifier."""
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        assert "metadata" in bom
        assert bom["metadata"].get("generator") == "skillmeat-bom"

    def test_composite_entry_has_members_key(self, db_session: Session) -> None:
        """Composite artifact entries include a ``members`` key (list, may be empty)."""
        generator = BomGenerator(session=db_session)
        bom = generator.generate()

        composite_entries = [e for e in bom["artifacts"] if e["type"] == "composite"]
        assert len(composite_entries) == 1, "Expected exactly one composite entry"

        composite = composite_entries[0]
        assert "members" in composite, "Composite entry missing 'members' key"
        assert isinstance(composite["members"], list)

    def test_project_id_filter_restricts_results(
        self, db_session: Session, sample_project: Project
    ) -> None:
        """Passing ``project_id`` to ``generate()`` limits results to that project."""
        # Insert a second project with its own artifact.
        other_project = Project(
            id="proj-other",
            name="Other Project",
            path="/tmp/other-project",
        )
        db_session.add(other_project)
        db_session.flush()
        db_session.add(
            _make_artifact(
                project_id="proj-other",
                name="other-skill",
                artifact_type="skill",
            )
        )
        db_session.commit()

        generator = BomGenerator(session=db_session)
        bom = generator.generate(project_id=sample_project.id)

        found_project_ids = {
            entry["name"]
            for entry in bom["artifacts"]
        }
        # "other-skill" must not appear when filtering on sample_project.
        assert "other-skill" not in found_project_ids

    def test_bom_is_idempotent(self, db_session: Session) -> None:
        """Calling ``generate()`` twice with identical state returns identical output."""
        generator = BomGenerator(session=db_session)
        bom_1 = generator.generate()
        bom_2 = generator.generate()

        # Timestamps will differ so compare structural content only.
        assert bom_1["artifact_count"] == bom_2["artifact_count"]
        assert bom_1["schema_version"] == bom_2["schema_version"]
        for e1, e2 in zip(bom_1["artifacts"], bom_2["artifacts"]):
            assert e1["name"] == e2["name"]
            assert e1["type"] == e2["type"]
            assert e1["content_hash"] == e2["content_hash"]


# =============================================================================
# Scenario 2: RBAC visibility enforcement
# =============================================================================


class TestRbacVisibilityEnforcement:
    """AttestationScopeResolver enforces correct owner-scoped visibility.

    These tests are entirely in-memory (no DB session required).  They extend
    the unit tests in ``skillmeat/api/tests/test_bom_attestation_rbac.py``
    with multi-scope integration narratives that mirror realistic request paths.
    """

    @pytest.fixture(autouse=True)
    def _setup_resolvers(self) -> None:
        """Initialise the resolver pair used across all tests in this class."""
        self.ownership_resolver = OwnershipResolver()
        self.scope_resolver = AttestationScopeResolver(self.ownership_resolver)

    # ------------------------------------------------------------------
    # User scope
    # ------------------------------------------------------------------

    def test_user_a_cannot_see_user_b_private_attestations(self) -> None:
        """User A's private attestation is not visible to User B."""
        user_a_record = _make_mock_attestation_record(
            artifact_id="skill:canvas",
            owner_type=OwnerType.user.value,
            owner_id="user-alice",
            visibility=Visibility.private.value,
        )
        user_b_record = _make_mock_attestation_record(
            artifact_id="skill:canvas",
            owner_type=OwnerType.user.value,
            owner_id="user-bob",
            visibility=Visibility.private.value,
        )

        visible_to_bob = self.scope_resolver.filter_visible(
            [user_a_record, user_b_record],
            viewer_owner_type=OwnerType.user.value,
            viewer_owner_id="user-bob",
            viewer_roles=[],
        )

        assert user_a_record not in visible_to_bob, (
            "User B must not see User A's private attestation"
        )
        assert user_b_record in visible_to_bob, (
            "User B must see their own private attestation"
        )

    def test_user_sees_all_public_attestations_regardless_of_owner(self) -> None:
        """Any user can see attestation records with ``public`` visibility."""
        records = [
            _make_mock_attestation_record(
                artifact_id=f"skill:art-{i}",
                owner_type=OwnerType.user.value,
                owner_id=f"user-other-{i}",
                visibility=Visibility.public.value,
            )
            for i in range(3)
        ]

        visible = self.scope_resolver.filter_visible(
            records,
            viewer_owner_type=OwnerType.user.value,
            viewer_owner_id="user-viewer",
            viewer_roles=[],
        )

        assert len(visible) == 3, "All public records must be visible"

    def test_mixed_visibility_user_sees_correct_subset(self) -> None:
        """User sees own-private + public, but not others-private."""
        own_private = _make_mock_attestation_record(
            owner_id="user-alice",
            owner_type=OwnerType.user.value,
            visibility=Visibility.private.value,
        )
        other_private = _make_mock_attestation_record(
            owner_id="user-bob",
            owner_type=OwnerType.user.value,
            visibility=Visibility.private.value,
        )
        public_record = _make_mock_attestation_record(
            owner_id="user-charlie",
            owner_type=OwnerType.user.value,
            visibility=Visibility.public.value,
        )

        visible = self.scope_resolver.filter_visible(
            [own_private, other_private, public_record],
            viewer_owner_type=OwnerType.user.value,
            viewer_owner_id="user-alice",
            viewer_roles=[],
        )

        assert own_private in visible
        assert other_private not in visible
        assert public_record in visible

    # ------------------------------------------------------------------
    # Team scope
    # ------------------------------------------------------------------

    def test_team_member_sees_team_visibility_not_private(self) -> None:
        """``team_member`` sees team-visibility records but not private ones."""
        team_vis = _make_mock_attestation_record(
            owner_type=OwnerType.team.value,
            owner_id="team-alpha",
            visibility=Visibility.team.value,
        )
        team_priv = _make_mock_attestation_record(
            owner_type=OwnerType.team.value,
            owner_id="team-alpha",
            visibility=Visibility.private.value,
        )

        visible = self.scope_resolver.filter_visible(
            [team_vis, team_priv],
            viewer_owner_type=OwnerType.team.value,
            viewer_owner_id="team-alpha",
            viewer_roles=["team_member"],
        )

        assert team_vis in visible
        assert team_priv not in visible

    def test_team_admin_sees_private_team_records(self) -> None:
        """``team_admin`` sees all records owned by their team, including private."""
        team_private = _make_mock_attestation_record(
            owner_type=OwnerType.team.value,
            owner_id="team-alpha",
            visibility=Visibility.private.value,
        )

        visible = self.scope_resolver.filter_visible(
            [team_private],
            viewer_owner_type=OwnerType.team.value,
            viewer_owner_id="team-alpha",
            viewer_roles=["team_admin"],
        )

        assert team_private in visible

    def test_team_member_cannot_see_other_team_records(self) -> None:
        """Team A member has no access to Team B records at any visibility level."""
        team_b_team_vis = _make_mock_attestation_record(
            owner_type=OwnerType.team.value,
            owner_id="team-beta",
            visibility=Visibility.team.value,
        )
        team_b_public = _make_mock_attestation_record(
            owner_type=OwnerType.team.value,
            owner_id="team-beta",
            visibility=Visibility.public.value,
        )

        visible = self.scope_resolver.filter_visible(
            [team_b_team_vis, team_b_public],
            viewer_owner_type=OwnerType.team.value,
            viewer_owner_id="team-alpha",
            viewer_roles=["team_member"],
        )

        # Public records are always visible (rule 6).
        assert team_b_public in visible
        # Team-visibility records from another team are hidden.
        assert team_b_team_vis not in visible

    # ------------------------------------------------------------------
    # Enterprise scope
    # ------------------------------------------------------------------

    def test_enterprise_admin_sees_all_enterprise_scoped_records(self) -> None:
        """``enterprise_admin`` can see all records where ``owner_type == 'enterprise'``."""
        records = [
            _make_mock_attestation_record(
                owner_type=OwnerType.enterprise.value,
                owner_id="tenant-acme",
                visibility=v,
            )
            for v in [
                Visibility.private.value,
                Visibility.team.value,
                Visibility.public.value,
            ]
        ]

        visible = self.scope_resolver.filter_visible(
            records,
            viewer_owner_type=OwnerType.enterprise.value,
            viewer_owner_id="tenant-acme",
            viewer_roles=["enterprise_admin"],
        )

        assert len(visible) == 3, "enterprise_admin must see all enterprise records"

    def test_enterprise_admin_cannot_see_user_private_records(self) -> None:
        """``enterprise_admin`` role does not grant access to user-private records."""
        user_private = _make_mock_attestation_record(
            owner_type=OwnerType.user.value,
            owner_id="user-alice",
            visibility=Visibility.private.value,
        )

        visible = self.scope_resolver.filter_visible(
            [user_private],
            viewer_owner_type=OwnerType.enterprise.value,
            viewer_owner_id="tenant-acme",
            viewer_roles=["enterprise_admin"],
        )

        assert user_private not in visible

    def test_regular_user_cannot_see_enterprise_private_records(self) -> None:
        """A regular user (no elevated roles) cannot see enterprise-private records."""
        ent_private = _make_mock_attestation_record(
            owner_type=OwnerType.enterprise.value,
            owner_id="tenant-acme",
            visibility=Visibility.private.value,
        )

        visible = self.scope_resolver.filter_visible(
            [ent_private],
            viewer_owner_type=OwnerType.user.value,
            viewer_owner_id="user-alice",
            viewer_roles=[],
        )

        assert ent_private not in visible

    # ------------------------------------------------------------------
    # System admin
    # ------------------------------------------------------------------

    def test_system_admin_sees_all_records_across_all_scopes(self) -> None:
        """``system_admin`` bypasses every ownership and visibility restriction."""
        records = [
            _make_mock_attestation_record(
                owner_type=OwnerType.user.value,
                owner_id="user-alice",
                visibility=Visibility.private.value,
            ),
            _make_mock_attestation_record(
                owner_type=OwnerType.team.value,
                owner_id="team-alpha",
                visibility=Visibility.private.value,
            ),
            _make_mock_attestation_record(
                owner_type=OwnerType.enterprise.value,
                owner_id="tenant-acme",
                visibility=Visibility.private.value,
            ),
        ]

        visible = self.scope_resolver.filter_visible(
            records,
            viewer_owner_type=OwnerType.user.value,
            viewer_owner_id="global-admin",
            viewer_roles=["system_admin"],
        )

        assert visible == records

    # ------------------------------------------------------------------
    # build_query_filters consistency with filter_visible
    # ------------------------------------------------------------------

    def test_build_query_filters_user_scope_matches_filter_visible(self) -> None:
        """``build_query_filters`` for a regular user returns ``owner_id``-scoped criteria."""
        filters = self.scope_resolver.build_query_filters(
            owner_type=OwnerType.user.value,
            owner_id="user-alice",
            roles=[],
        )
        assert filters == {"owner_type": "user", "owner_id": "user-alice"}

        # in-memory check: another user's record must be excluded.
        bob_record = _make_mock_attestation_record(
            owner_type=OwnerType.user.value,
            owner_id="user-bob",
            visibility=Visibility.private.value,
        )
        visible = self.scope_resolver.filter_visible(
            [bob_record],
            viewer_owner_type=OwnerType.user.value,
            viewer_owner_id="user-alice",
            viewer_roles=[],
        )
        assert bob_record not in visible

    def test_build_query_filters_system_admin_returns_empty_dict(self) -> None:
        """``build_query_filters`` for ``system_admin`` returns an empty dict (no restriction)."""
        filters = self.scope_resolver.build_query_filters(
            owner_type=OwnerType.user.value,
            owner_id="admin-user",
            roles=["system_admin"],
        )
        assert filters == {}, "system_admin must receive no DB-level restriction"

    # ------------------------------------------------------------------
    # OwnershipResolver integration
    # ------------------------------------------------------------------

    def test_ownership_resolver_enterprise_context_feeds_scope_resolver(self) -> None:
        """Auth context with ``tenant_id`` resolves to enterprise ownership and filters correctly."""
        auth_context = SimpleNamespace(
            user_id="user-alice",
            team_id="team-alpha",
            tenant_id="tenant-acme",
        )
        owner_type, owner_id = self.ownership_resolver.resolve_from_auth_context(
            auth_context
        )
        assert owner_type == OwnerType.enterprise.value
        assert owner_id == "tenant-acme"

        ent_record = _make_mock_attestation_record(
            owner_type=OwnerType.enterprise.value,
            owner_id="tenant-acme",
            visibility=Visibility.private.value,
        )
        user_record = _make_mock_attestation_record(
            owner_type=OwnerType.user.value,
            owner_id="user-alice",
            visibility=Visibility.private.value,
        )

        # enterprise owner without elevated role: can only see own enterprise records
        # (rule 5 — enterprise owner_id match) or public records.
        visible = self.scope_resolver.filter_visible(
            [ent_record, user_record],
            viewer_owner_type=owner_type,
            viewer_owner_id=owner_id,
            viewer_roles=[],
        )

        # Enterprise record with matching owner_id is visible (rule 5).
        assert ent_record in visible
        # User-private record is hidden.
        assert user_record not in visible


# =============================================================================
# Scenario 3: API/CLI data consistency
# =============================================================================


class TestApiCliDataConsistency:
    """BomGenerator (service layer) and BomSchema (API layer) agree on all fields.

    Both surfaces read from the same underlying data.  This suite verifies
    that ``BomSchema.model_validate(bom_dict)`` succeeds without validation
    errors and that key field values are preserved identically — no silent
    renaming, type coercion, or count mismatch between the two layers.
    """

    # Import lazily so that pydantic validation errors surface as failures
    # rather than import errors.
    from skillmeat.api.schemas.bom import BomSchema, ArtifactEntrySchema

    ARTIFACT_SPECS = [
        ("my-skill", "skill"),
        ("my-command", "command"),
        ("my-agent", "agent"),
        ("my-mcp", "mcp_server"),
        ("my-hook", "hook"),
    ]

    @pytest.fixture(autouse=True)
    def _populate_db(self, db_session: Session, sample_project: Project) -> None:
        """Insert a fixed artifact set for consistency assertions."""
        for name, artifact_type in self.ARTIFACT_SPECS:
            db_session.add(
                _make_artifact(
                    project_id=sample_project.id,
                    name=name,
                    artifact_type=artifact_type,
                    source=f"user/repo/{name}@v1.0.0",
                    deployed_version="1.0.0",
                    content=f"content-{name}",
                )
            )
        db_session.commit()
        self._db_session = db_session

    def _generate_bom(self) -> dict:
        """Run BomGenerator and return the raw BOM dict (service layer)."""
        generator = BomGenerator(session=self._db_session)
        return generator.generate()

    def test_bom_schema_validates_without_error(self) -> None:
        """``BomSchema.model_validate`` succeeds on the raw BOM dict."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)
        assert schema is not None

    def test_artifact_count_matches_between_service_and_schema(self) -> None:
        """``artifact_count`` field agrees between the raw dict and the schema object."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        assert bom_dict["artifact_count"] == schema.artifact_count
        assert schema.artifact_count == len(self.ARTIFACT_SPECS)

    def test_artifact_entries_count_matches_artifact_count(self) -> None:
        """The length of ``artifacts`` list equals ``artifact_count``."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        assert len(schema.artifacts) == schema.artifact_count

    def test_artifact_names_preserved_through_schema(self) -> None:
        """Artifact names are identical between raw BOM dict and schema entries."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        raw_names = sorted(e["name"] for e in bom_dict["artifacts"])
        schema_names = sorted(e.name for e in schema.artifacts)
        assert raw_names == schema_names

    def test_artifact_types_preserved_through_schema(self) -> None:
        """Artifact type strings are identical between raw BOM dict and schema entries."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        raw_types = sorted(e["type"] for e in bom_dict["artifacts"])
        schema_types = sorted(e.type for e in schema.artifacts)
        assert raw_types == schema_types

    def test_content_hash_preserved_through_schema(self) -> None:
        """``content_hash`` values are identical between raw dict and schema entries."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        raw_hashes = {e["name"]: e["content_hash"] for e in bom_dict["artifacts"]}
        schema_hashes = {e.name: e.content_hash for e in schema.artifacts}
        assert raw_hashes == schema_hashes

    def test_schema_version_is_consistent(self) -> None:
        """``schema_version`` is identical between raw dict and schema object."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        assert bom_dict["schema_version"] == schema.schema_version

    def test_generated_at_is_consistent(self) -> None:
        """``generated_at`` timestamp string is preserved through the schema."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        assert bom_dict["generated_at"] == schema.generated_at

    def test_artifact_sources_preserved_through_schema(self) -> None:
        """``source`` field is preserved without modification through the schema."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        raw_sources = {e["name"]: e["source"] for e in bom_dict["artifacts"]}
        schema_sources = {e.name: e.source for e in schema.artifacts}
        assert raw_sources == schema_sources

    def test_artifact_versions_preserved_through_schema(self) -> None:
        """``version`` field is preserved without modification through the schema."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        raw_versions = {e["name"]: e["version"] for e in bom_dict["artifacts"]}
        schema_versions = {e.name: e.version for e in schema.artifacts}
        assert raw_versions == schema_versions

    def test_metadata_dict_preserved_through_schema(self) -> None:
        """The ``metadata`` block on each artifact entry survives schema validation."""
        from skillmeat.api.schemas.bom import BomSchema

        bom_dict = self._generate_bom()
        schema = BomSchema.model_validate(bom_dict)

        raw_metadata = {e["name"]: e["metadata"] for e in bom_dict["artifacts"]}
        schema_metadata = {e.name: e.metadata for e in schema.artifacts}

        for name, raw_meta in raw_metadata.items():
            assert name in schema_metadata, f"Entry {name!r} missing from schema artifacts"
            assert raw_meta == schema_metadata[name], (
                f"metadata mismatch for {name!r}: "
                f"raw={raw_meta!r}, schema={schema_metadata[name]!r}"
            )


# =============================================================================
# Scenario 3 extension: Policy enforcer in local mode
# =============================================================================


class TestAttestationPolicyEnforcerLocalMode:
    """AttestationPolicyEnforcer in local (non-enterprise) mode is always permissive.

    This supplements the API/CLI consistency tests by verifying that the
    policy layer does not unexpectedly gate local-mode workflows.
    """

    @pytest.fixture(autouse=True)
    def _setup_enforcer(self) -> None:
        self.enforcer = AttestationPolicyEnforcer(is_enterprise=False)

    def _make_mock_policy(
        self,
        name: str = "test-policy",
        required_artifacts: Optional[List[str]] = None,
        required_scopes: Optional[List[str]] = None,
    ):
        """Return a minimal mock AttestationPolicy object."""
        policy = MagicMock()
        policy.name = name
        policy.required_artifacts = required_artifacts or []
        policy.required_scopes = required_scopes or []
        policy.tenant_id = None
        return policy

    def test_local_mode_artifact_validation_always_passes(self) -> None:
        """Local mode: ``validate_required_artifacts`` returns ``is_valid=True``."""
        policy = self._make_mock_policy(required_artifacts=["skill:canvas"])
        result: PolicyValidationResult = self.enforcer.validate_required_artifacts(
            policy, attested_artifact_ids=[]  # empty — would fail in enterprise mode
        )
        assert result.is_valid is True
        assert result.missing == []

    def test_local_mode_scope_validation_always_passes(self) -> None:
        """Local mode: ``validate_required_scopes`` returns ``is_valid=True``."""
        policy = self._make_mock_policy(required_scopes=["deploy:prod"])
        records: List[AttestationRecord] = []  # no scopes — would fail in enterprise
        result: PolicyValidationResult = self.enforcer.validate_required_scopes(
            policy, attestation_records=records
        )
        assert result.is_valid is True
        assert result.missing == []

    def test_local_mode_full_compliance_report_is_compliant(self) -> None:
        """Local mode: ``evaluate_full_compliance`` always returns ``is_compliant=True``."""
        policy = self._make_mock_policy(
            required_artifacts=["skill:art-1"],
            required_scopes=["write"],
        )
        report = self.enforcer.evaluate_full_compliance(
            policy, attested_artifact_ids=[], attestation_records=[]
        )
        assert report.is_compliant is True
        assert report.policy_name == "test-policy"
        assert report.tenant_id is None

    def test_local_mode_compliance_metadata_has_full_coverage(self) -> None:
        """Local mode compliance metadata reports 1.0 coverage for all dimensions."""
        policy = self._make_mock_policy()
        metadata = self.enforcer.extract_compliance_metadata(
            policy, attestation_records=[]
        )
        assert metadata["artifact_coverage"] == 1.0
        assert metadata["scope_coverage"] == 1.0
        assert metadata["compliant"] is True
        assert "timestamp" in metadata
