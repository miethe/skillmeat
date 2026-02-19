"""Tests for import_plugin_transactional (CAI-P3-03 + CAI-P3-04).

Covers:
- Happy path: discovered graph with 3 children -> all created + memberships written
- Dedup path: re-import of the same content -> children_reused=3, children_imported=0
- Rollback path: failure mid-import -> no orphaned rows, success=False
- Pin verification: pinned_version_hash matches child content hash on each membership

Patching strategy
-----------------
``import_plugin_transactional`` defers its heavy imports (cache models,
deduplication, hashing) *inside* the function body to avoid the circular
import chain:

    cache.models -> cache -> cache.marketplace -> api -> api.routers ->
    core.importer -> cache.models

Because of this, ``patch("skillmeat.core.importer.<name>")`` does **not**
work — the names are not bound at module level.  Instead we patch at the
canonical source module paths:

    skillmeat.core.hashing.compute_artifact_hash
    skillmeat.core.deduplication.resolve_artifact_for_import
    skillmeat.cache.models.Artifact
    skillmeat.cache.models.ArtifactVersion
    skillmeat.cache.models.CompositeArtifact
    skillmeat.cache.models.CompositeMembership
"""

from __future__ import annotations

from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.importer import ImportResult, import_plugin_transactional


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

PROJECT_ID = "proj-test-001"
COLLECTION_ID = "col-test-001"
SOURCE_URL = "github:owner/test-plugin"

CHILD_HASHES = [
    "a" * 64,
    "b" * 64,
    "c" * 64,
]


def _make_discovered_artifact(name: str, artifact_type: str, path: str) -> MagicMock:
    """Return a minimal DiscoveredArtifact-like mock."""
    artifact = MagicMock()
    artifact.name = name
    artifact.type = artifact_type
    artifact.path = path
    artifact.description = f"Description for {name}"
    return artifact


def _make_discovered_graph(plugin_name: str = "my-plugin") -> MagicMock:
    """Return a minimal DiscoveredGraph mock with 3 children."""
    graph = MagicMock()
    graph.parent.name = plugin_name
    graph.parent.description = "A test plugin"
    graph.children = [
        _make_discovered_artifact("skill-alpha", "skill", "/tmp/skill-alpha"),
        _make_discovered_artifact("cmd-beta", "command", "/tmp/cmd-beta.md"),
        _make_discovered_artifact("agent-gamma", "agent", "/tmp/agent-gamma.md"),
    ]
    return graph


def _make_artifact_row(artifact_id: str, artifact_uuid: str) -> MagicMock:
    """Return a minimal Artifact ORM mock."""
    row = MagicMock()
    row.id = artifact_id
    row.uuid = artifact_uuid
    return row


def _noop_filter_chain(return_value: Any = None) -> MagicMock:
    """Return a query mock whose .filter().first() returns `return_value`."""
    q = MagicMock()
    q.filter.return_value.first.return_value = return_value
    return q


# ---------------------------------------------------------------------------
# Happy path: 3 children, all CREATE_NEW_ARTIFACT
# ---------------------------------------------------------------------------


def test_happy_path_all_children_created():
    """Import a graph with 3 children that don't exist yet.

    Verifies:
    - ImportResult.success is True
    - children_imported == 3
    - children_reused == 0
    - plugin_id has correct format
    - session.commit() called exactly once
    - session.rollback() never called
    """
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("my-plugin")
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    child_uuids = ["uuid-alpha-0001", "uuid-beta-0002", "uuid-gamma-0003"]

    with (
        patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=CHILD_HASHES,
        ),
        patch(
            "skillmeat.core.deduplication.resolve_artifact_for_import",
            return_value=DeduplicationResult(
                decision=DeduplicationDecision.CREATE_NEW_ARTIFACT,
                artifact_id=None,
                artifact_version_id=None,
                reason="no match",
            ),
        ),
        patch("skillmeat.cache.models.Artifact") as MockArtifact,
        patch("skillmeat.cache.models.ArtifactVersion") as MockArtifactVersion,
        patch("skillmeat.cache.models.CompositeArtifact") as MockCompositeArtifact,
        patch("skillmeat.cache.models.CompositeMembership") as MockCompositeMembership,
    ):
        # Build artifact instances with pre-set uuids
        artifact_instances = []
        for i, child in enumerate(graph.children):
            inst = MagicMock()
            inst.id = f"{child.type}:{child.name}"
            inst.uuid = child_uuids[i]
            artifact_instances.append(inst)
        MockArtifact.side_effect = artifact_instances

        # ArtifactVersion instances
        version_instances = [MagicMock(), MagicMock(), MagicMock()]
        MockArtifactVersion.side_effect = version_instances

        composite_instance = MagicMock()
        MockCompositeArtifact.return_value = composite_instance

        membership_instances = [MagicMock(), MagicMock(), MagicMock()]
        MockCompositeMembership.side_effect = membership_instances

        composite_query = _noop_filter_chain(return_value=None)
        membership_query = _noop_filter_chain(return_value=None)
        artifact_query = _noop_filter_chain(return_value=None)

        def query_router(model):
            model_name = getattr(model, "__name__", str(model))
            if "CompositeArtifact" in model_name:
                return composite_query
            if "CompositeMembership" in model_name:
                return membership_query
            return artifact_query

        session.query.side_effect = query_router

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True
    assert result.plugin_id == "composite:my-plugin"
    assert result.children_imported == 3
    assert result.children_reused == 0
    assert result.errors == []
    assert result.transaction_id
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


# ---------------------------------------------------------------------------
# Dedup path: all 3 children already exist (LINK_EXISTING)
# ---------------------------------------------------------------------------


def test_dedup_all_children_reused():
    """Re-import the same graph -> children_reused=3, children_imported=0.

    Verifies:
    - All three children get LINK_EXISTING from deduplication
    - No new Artifact or ArtifactVersion rows are created
    - Memberships are still created
    - children_reused == 3
    """
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("my-plugin")
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    existing_artifact_uuids = ["uuid-existing-1", "uuid-existing-2", "uuid-existing-3"]
    existing_artifact_ids = [f"{child.type}:{child.name}" for child in graph.children]

    existing_artifacts = [
        _make_artifact_row(existing_artifact_ids[i], existing_artifact_uuids[i])
        for i in range(3)
    ]

    with (
        patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=CHILD_HASHES,
        ),
        patch(
            "skillmeat.core.deduplication.resolve_artifact_for_import",
            side_effect=[
                DeduplicationResult(
                    decision=DeduplicationDecision.LINK_EXISTING,
                    artifact_id=existing_artifact_ids[i],
                    artifact_version_id=f"ver-existing-{i}",
                    reason="exact hash match",
                )
                for i in range(3)
            ],
        ),
        patch("skillmeat.cache.models.Artifact") as MockArtifact,
        patch("skillmeat.cache.models.ArtifactVersion") as MockArtifactVersion,
        patch("skillmeat.cache.models.CompositeArtifact") as MockCompositeArtifact,
        patch("skillmeat.cache.models.CompositeMembership") as MockCompositeMembership,
    ):
        # Artifact query cycles through existing artifacts for UUID resolution
        artifact_query_index = [0]

        def artifact_query_factory(model):
            q = MagicMock()
            idx = artifact_query_index[0]
            if idx < len(existing_artifacts):
                q.filter.return_value.first.return_value = existing_artifacts[idx]
                artifact_query_index[0] += 1
            else:
                q.filter.return_value.first.return_value = None
            return q

        composite_query = _noop_filter_chain(return_value=None)
        membership_query = _noop_filter_chain(return_value=None)

        def query_router(model):
            model_name = getattr(model, "__name__", str(model))
            if "CompositeArtifact" in model_name:
                return composite_query
            if "CompositeMembership" in model_name:
                return membership_query
            return artifact_query_factory(model)

        session.query.side_effect = query_router

        MockCompositeArtifact.return_value = MagicMock()

        membership_instances = [MagicMock(), MagicMock(), MagicMock()]
        MockCompositeMembership.side_effect = membership_instances

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True
    assert result.children_reused == 3
    assert result.children_imported == 0
    assert result.errors == []
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    # No new Artifact or ArtifactVersion rows created
    MockArtifact.assert_not_called()
    MockArtifactVersion.assert_not_called()


# ---------------------------------------------------------------------------
# Rollback path: failure mid-import -> no orphaned rows
# ---------------------------------------------------------------------------


def test_rollback_on_mid_import_failure():
    """A failure mid-import triggers rollback and returns success=False.

    Simulates compute_artifact_hash raising FileNotFoundError on the second child.
    Verifies:
    - session.rollback() called exactly once
    - session.commit() never called
    - result.success is False
    - result.errors is non-empty
    - children_imported and children_reused both reset to 0
    """

    def hash_that_fails(path: str) -> str:
        if "cmd-beta" in path:
            raise FileNotFoundError(f"Artifact path does not exist: {path}")
        return "a" * 64

    graph = _make_discovered_graph("broken-plugin")
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    with (
        patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=hash_that_fails,
        ),
        patch("skillmeat.core.deduplication.resolve_artifact_for_import") as mock_dedup,
        patch("skillmeat.cache.models.Artifact"),
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact"),
        patch("skillmeat.cache.models.CompositeMembership"),
    ):
        from skillmeat.core.deduplication import (
            DeduplicationDecision,
            DeduplicationResult,
        )

        mock_dedup.return_value = DeduplicationResult(
            decision=DeduplicationDecision.CREATE_NEW_ARTIFACT,
            artifact_id=None,
            artifact_version_id=None,
            reason="no match",
        )

        composite_query = _noop_filter_chain(return_value=None)
        artifact_query = _noop_filter_chain(return_value=None)

        def query_router(model):
            model_name = getattr(model, "__name__", str(model))
            if "CompositeArtifact" in model_name:
                return composite_query
            return artifact_query

        session.query.side_effect = query_router

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is False
    assert result.children_imported == 0
    assert result.children_reused == 0
    assert len(result.errors) >= 1
    assert "cmd-beta" in result.errors[0] or "path does not exist" in result.errors[0]
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Pin verification: pinned_version_hash matches child content hash
# ---------------------------------------------------------------------------


def test_pinned_version_hash_stored_correctly():
    """Each CompositeMembership is created with the correct pinned_version_hash.

    Verifies (CAI-P3-04): pinned_version_hash equals the content hash of each
    child at import time.
    """
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("pinned-plugin")
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    child_uuids = ["uuid-pin-1", "uuid-pin-2", "uuid-pin-3"]

    with (
        patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=list(CHILD_HASHES),
        ),
        patch(
            "skillmeat.core.deduplication.resolve_artifact_for_import",
            return_value=DeduplicationResult(
                decision=DeduplicationDecision.CREATE_NEW_ARTIFACT,
                artifact_id=None,
                artifact_version_id=None,
                reason="no match",
            ),
        ),
        patch("skillmeat.cache.models.Artifact") as MockArtifact,
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact") as MockCompositeArtifact,
        patch("skillmeat.cache.models.CompositeMembership") as MockCompositeMembership,
    ):
        # Build artifact instances with pre-set uuids
        artifact_instances = []
        for i, child in enumerate(graph.children):
            inst = MagicMock()
            inst.id = f"{child.type}:{child.name}"
            inst.uuid = child_uuids[i]
            artifact_instances.append(inst)
        MockArtifact.side_effect = artifact_instances

        MockCompositeArtifact.return_value = MagicMock()

        composite_query = _noop_filter_chain(return_value=None)
        membership_query = _noop_filter_chain(return_value=None)
        artifact_query = _noop_filter_chain(return_value=None)

        def query_router(model):
            model_name = getattr(model, "__name__", str(model))
            if "CompositeArtifact" in model_name:
                return composite_query
            if "CompositeMembership" in model_name:
                return membership_query
            return artifact_query

        session.query.side_effect = query_router

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True

    # Verify CompositeMembership was instantiated 3 times with correct kwargs
    assert MockCompositeMembership.call_count == 3

    # Inspect each call for pinned_version_hash (CAI-P3-04)
    for i, membership_call in enumerate(MockCompositeMembership.call_args_list):
        kwargs = membership_call.kwargs
        assert kwargs.get("pinned_version_hash") == CHILD_HASHES[i], (
            f"Child {i}: expected pinned_version_hash={CHILD_HASHES[i]!r}, "
            f"got {kwargs.get('pinned_version_hash')!r}"
        )
        assert kwargs.get("child_artifact_uuid") == child_uuids[i]
        assert kwargs.get("composite_id") == "composite:pinned-plugin"
        assert kwargs.get("collection_id") == COLLECTION_ID
        assert kwargs.get("relationship_type") == "contains"


# ---------------------------------------------------------------------------
# Additional: transaction_id is unique per call
# ---------------------------------------------------------------------------


def test_transaction_id_is_unique():
    """Each call to import_plugin_transactional generates a distinct transaction_id."""
    graph = _make_discovered_graph()
    graph.children = []  # no children to simplify mock setup

    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    with (
        patch("skillmeat.cache.models.CompositeArtifact") as MockCompositeArtifact,
        patch("skillmeat.cache.models.CompositeMembership"),
    ):
        MockCompositeArtifact.return_value = MagicMock()
        composite_query = _noop_filter_chain(return_value=None)
        session.query.return_value = composite_query

        result1 = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )
        session.reset_mock()
        composite_query2 = _noop_filter_chain(return_value=None)
        session.query.return_value = composite_query2

        result2 = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result1.transaction_id != result2.transaction_id


# ---------------------------------------------------------------------------
# Additional: ImportResult dataclass fields
# ---------------------------------------------------------------------------


def test_import_result_defaults():
    """ImportResult auto-generates a non-empty transaction_id."""
    result = ImportResult(
        success=True,
        plugin_id="composite:test",
        children_imported=1,
        children_reused=2,
        errors=[],
    )
    assert result.success is True
    assert result.plugin_id == "composite:test"
    assert result.children_imported == 1
    assert result.children_reused == 2
    assert result.errors == []
    assert len(result.transaction_id) > 0
