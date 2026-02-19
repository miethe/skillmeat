"""Tests for OpenTelemetry observability instrumentation on composite import operations.

Covers:
- OTel span creation in import_plugin_transactional (mock tracer)
- OTel metric counters increment on success and failure paths
- Structured log fields (plugin_name, child_count, transaction_id, duration_ms)
- Deduplication hit/miss counters update correctly
- Graceful fallback when OTel is not installed (no-op path)

Patching strategy
-----------------
``import_plugin_transactional`` defers its heavy imports inside the function
body.  Because of this the canonical source paths must be patched, not the
names in ``skillmeat.core.importer``.  Same strategy as
``test_import_orchestration.py``.
"""

from __future__ import annotations

import logging
from typing import Any, List
from unittest.mock import MagicMock, call, patch

import pytest

from skillmeat.core.importer import ImportResult, import_plugin_transactional


# ---------------------------------------------------------------------------
# Helpers (mirrors test_import_orchestration.py fixture style)
# ---------------------------------------------------------------------------

PROJECT_ID = "proj-obs-001"
COLLECTION_ID = "col-obs-001"
SOURCE_URL = "github:owner/obs-plugin"

CHILD_HASHES = [
    "d" * 64,
    "e" * 64,
]


def _make_discovered_artifact(name: str, artifact_type: str, path: str) -> MagicMock:
    """Return a minimal DiscoveredArtifact-like mock."""
    artifact = MagicMock()
    artifact.name = name
    artifact.type = artifact_type
    artifact.path = path
    artifact.description = f"Description for {name}"
    return artifact


def _make_discovered_graph(plugin_name: str = "obs-plugin") -> MagicMock:
    """Return a minimal DiscoveredGraph mock with 2 children."""
    graph = MagicMock()
    graph.parent.name = plugin_name
    graph.parent.description = "An observability test plugin"
    graph.children = [
        _make_discovered_artifact("obs-skill", "skill", "/tmp/obs-skill"),
        _make_discovered_artifact("obs-cmd", "command", "/tmp/obs-cmd.md"),
    ]
    return graph


def _noop_filter_chain(return_value: Any = None) -> MagicMock:
    """Return a query mock whose .filter().first() returns `return_value`."""
    q = MagicMock()
    q.filter.return_value.first.return_value = return_value
    return q


def _build_session_for_new_artifacts(graph: MagicMock) -> MagicMock:
    """Return a Session mock that creates fresh artifacts for every child."""
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    def _side_effect_query(model):
        # Always return None (no existing rows)
        return _noop_filter_chain(return_value=None)

    session.query.side_effect = _side_effect_query
    return session


# ---------------------------------------------------------------------------
# OTel span creation tests (mock tracer)
# ---------------------------------------------------------------------------


class _FakeSpan:
    """Minimal span stub that records set_attribute calls."""

    def __init__(self, name: str):
        self.name = name
        self.attributes: dict = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _FakeTracer:
    """Tracer stub that records started spans."""

    def __init__(self):
        self.spans: List[_FakeSpan] = []

    def start_as_current_span(self, name: str):
        span = _FakeSpan(name)
        self.spans.append(span)
        return span


def test_import_plugin_transactional_emits_parent_span():
    """import_plugin_transactional creates a plugin.import_transactional span."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")
    session = _build_session_for_new_artifacts(graph)
    fake_tracer = _FakeTracer()

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
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact"),
        patch("skillmeat.cache.models.CompositeMembership"),
        # Inject our fake tracer into the importer module
        patch("skillmeat.core.importer._OTEL_AVAILABLE", True),
        patch("skillmeat.core.importer._tracer", fake_tracer),
    ):
        # Give each Artifact instance a uuid
        artifact_instances = []
        for i, child in enumerate(graph.children):
            inst = MagicMock()
            inst.id = f"{child.type}:{child.name}"
            inst.uuid = f"uuid-{i:04d}"
            artifact_instances.append(inst)
        MockArtifact.side_effect = artifact_instances

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True
    span_names = [s.name for s in fake_tracer.spans]
    assert "plugin.import_transactional" in span_names

    parent_span = next(
        s for s in fake_tracer.spans if s.name == "plugin.import_transactional"
    )
    assert parent_span.attributes["plugin_name"] == "obs-plugin"
    assert parent_span.attributes["child_count"] == 2
    assert "transaction_id" in parent_span.attributes


def test_import_plugin_transactional_emits_association_write_span():
    """A successful import emits an association.write span after child processing."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")
    session = _build_session_for_new_artifacts(graph)
    fake_tracer = _FakeTracer()

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
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact"),
        patch("skillmeat.cache.models.CompositeMembership"),
        patch("skillmeat.core.importer._OTEL_AVAILABLE", True),
        patch("skillmeat.core.importer._tracer", fake_tracer),
    ):
        artifact_instances = []
        for i, child in enumerate(graph.children):
            inst = MagicMock()
            inst.id = f"{child.type}:{child.name}"
            inst.uuid = f"uuid-assoc-{i:04d}"
            artifact_instances.append(inst)
        MockArtifact.side_effect = artifact_instances

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True
    span_names = [s.name for s in fake_tracer.spans]
    assert "association.write" in span_names

    assoc_span = next(s for s in fake_tracer.spans if s.name == "association.write")
    assert assoc_span.attributes["composite_id"] == "composite:obs-plugin"
    assert assoc_span.attributes["child_count"] == 2


# ---------------------------------------------------------------------------
# Metric counter tests
# ---------------------------------------------------------------------------


def test_plugin_import_total_incremented_on_success():
    """plugin_import_total counter is incremented with status=success on success."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")
    session = _build_session_for_new_artifacts(graph)

    mock_counter = MagicMock()
    mock_histogram = MagicMock()

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
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact"),
        patch("skillmeat.cache.models.CompositeMembership"),
        patch("skillmeat.core.importer._OTEL_AVAILABLE", True),
        patch("skillmeat.core.importer._tracer", None),
        patch("skillmeat.core.importer._plugin_import_total", mock_counter),
        patch("skillmeat.core.importer._plugin_import_duration", mock_histogram),
        patch("skillmeat.core.importer._dedup_hit_total", MagicMock()),
        patch("skillmeat.core.importer._dedup_miss_total", MagicMock()),
        patch("skillmeat.core.importer._artifact_hash_compute_duration", MagicMock()),
    ):
        artifact_instances = []
        for i, child in enumerate(graph.children):
            inst = MagicMock()
            inst.id = f"{child.type}:{child.name}"
            inst.uuid = f"uuid-ctr-{i:04d}"
            artifact_instances.append(inst)
        MockArtifact.side_effect = artifact_instances

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True
    # Verify counter was called with status=success
    mock_counter.add.assert_called_once()
    call_kwargs = mock_counter.add.call_args
    assert call_kwargs[0][0] == 1  # increment value
    assert call_kwargs[0][1]["status"] == "success"
    assert call_kwargs[0][1]["plugin_name"] == "obs-plugin"


def test_plugin_import_total_incremented_on_failure():
    """plugin_import_total counter is incremented with status=failure on error."""
    graph = _make_discovered_graph("obs-plugin")
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    mock_counter = MagicMock()
    mock_histogram = MagicMock()

    with (
        patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=RuntimeError("hash exploded"),
        ),
        patch("skillmeat.cache.models.Artifact"),
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact"),
        patch("skillmeat.cache.models.CompositeMembership"),
        patch("skillmeat.core.importer._OTEL_AVAILABLE", True),
        patch("skillmeat.core.importer._tracer", None),
        patch("skillmeat.core.importer._plugin_import_total", mock_counter),
        patch("skillmeat.core.importer._plugin_import_duration", mock_histogram),
        patch("skillmeat.core.importer._dedup_hit_total", MagicMock()),
        patch("skillmeat.core.importer._dedup_miss_total", MagicMock()),
        patch("skillmeat.core.importer._artifact_hash_compute_duration", MagicMock()),
    ):
        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is False
    mock_counter.add.assert_called_once()
    call_kwargs = mock_counter.add.call_args
    assert call_kwargs[0][0] == 1
    assert call_kwargs[0][1]["status"] == "failure"


def test_dedup_hit_counter_incremented_on_link_existing():
    """dedup_hit_total is incremented when LINK_EXISTING decision is returned."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")

    # Build a session that returns existing artifact rows for LINK_EXISTING
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None

    artifact_row_alpha = MagicMock()
    artifact_row_alpha.uuid = "uuid-existing-alpha"
    artifact_row_beta = MagicMock()
    artifact_row_beta.uuid = "uuid-existing-beta"

    # Both children already exist — every query returns a row
    artifact_rows = [artifact_row_alpha, artifact_row_beta]
    call_count = {"n": 0}

    def _query_side_effect(model):
        q = MagicMock()

        def _filter_side_effect(*args, **kwargs):
            fq = MagicMock()
            idx = call_count["n"]
            call_count["n"] += 1
            fq.first.return_value = artifact_rows[idx % len(artifact_rows)]
            return fq

        q.filter.side_effect = _filter_side_effect
        return q

    session.query.side_effect = _query_side_effect

    dedup_hit_mock = MagicMock()
    dedup_miss_mock = MagicMock()

    link_existing_result = DeduplicationResult(
        decision=DeduplicationDecision.LINK_EXISTING,
        artifact_id="art-existing-id",
        artifact_version_id="ver-existing-id",
        reason="exact hash match",
    )

    with (
        patch(
            "skillmeat.core.hashing.compute_artifact_hash",
            side_effect=CHILD_HASHES,
        ),
        patch(
            "skillmeat.core.deduplication.resolve_artifact_for_import",
            return_value=link_existing_result,
        ),
        patch("skillmeat.cache.models.Artifact"),
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact"),
        patch("skillmeat.cache.models.CompositeMembership"),
        patch("skillmeat.core.importer._OTEL_AVAILABLE", True),
        patch("skillmeat.core.importer._tracer", None),
        patch("skillmeat.core.importer._plugin_import_total", MagicMock()),
        patch("skillmeat.core.importer._plugin_import_duration", MagicMock()),
        patch("skillmeat.core.importer._dedup_hit_total", dedup_hit_mock),
        patch("skillmeat.core.importer._dedup_miss_total", dedup_miss_mock),
        patch("skillmeat.core.importer._artifact_hash_compute_duration", MagicMock()),
    ):
        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True
    assert result.children_reused == 2
    # Both children triggered a dedup_hit
    assert dedup_hit_mock.add.call_count == 2
    # No misses
    dedup_miss_mock.add.assert_not_called()


def test_dedup_miss_counter_incremented_on_create_new_artifact():
    """dedup_miss_total is incremented when CREATE_NEW_ARTIFACT decision is returned."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")
    session = _build_session_for_new_artifacts(graph)

    dedup_hit_mock = MagicMock()
    dedup_miss_mock = MagicMock()

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
        patch("skillmeat.cache.models.ArtifactVersion"),
        patch("skillmeat.cache.models.CompositeArtifact"),
        patch("skillmeat.cache.models.CompositeMembership"),
        patch("skillmeat.core.importer._OTEL_AVAILABLE", True),
        patch("skillmeat.core.importer._tracer", None),
        patch("skillmeat.core.importer._plugin_import_total", MagicMock()),
        patch("skillmeat.core.importer._plugin_import_duration", MagicMock()),
        patch("skillmeat.core.importer._dedup_hit_total", dedup_hit_mock),
        patch("skillmeat.core.importer._dedup_miss_total", dedup_miss_mock),
        patch("skillmeat.core.importer._artifact_hash_compute_duration", MagicMock()),
    ):
        artifact_instances = []
        for i, child in enumerate(graph.children):
            inst = MagicMock()
            inst.id = f"{child.type}:{child.name}"
            inst.uuid = f"uuid-miss-{i:04d}"
            artifact_instances.append(inst)
        MockArtifact.side_effect = artifact_instances

        result = import_plugin_transactional(
            discovered_graph=graph,
            source_url=SOURCE_URL,
            session=session,
            project_id=PROJECT_ID,
            collection_id=COLLECTION_ID,
        )

    assert result.success is True
    assert result.children_imported == 2
    # Both children triggered a dedup_miss
    assert dedup_miss_mock.add.call_count == 2
    dedup_hit_mock.add.assert_not_called()


# ---------------------------------------------------------------------------
# Structured logging tests
# ---------------------------------------------------------------------------


def test_import_start_log_contains_structured_fields(caplog):
    """import_plugin_transactional logs import start at INFO with structured fields."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")
    session = _build_session_for_new_artifacts(graph)

    with caplog.at_level(logging.INFO, logger="skillmeat.core.importer"):
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
            patch("skillmeat.cache.models.ArtifactVersion"),
            patch("skillmeat.cache.models.CompositeArtifact"),
            patch("skillmeat.cache.models.CompositeMembership"),
            patch("skillmeat.core.importer._OTEL_AVAILABLE", False),
            patch("skillmeat.core.importer._tracer", None),
        ):
            artifact_instances = []
            for i, child in enumerate(graph.children):
                inst = MagicMock()
                inst.id = f"{child.type}:{child.name}"
                inst.uuid = f"uuid-log-{i:04d}"
                artifact_instances.append(inst)
            MockArtifact.side_effect = artifact_instances

            result = import_plugin_transactional(
                discovered_graph=graph,
                source_url=SOURCE_URL,
                session=session,
                project_id=PROJECT_ID,
                collection_id=COLLECTION_ID,
            )

    assert result.success is True

    # Find the "started" log record
    started_records = [r for r in caplog.records if "started" in r.message]
    assert started_records, "Expected an import_plugin_transactional started log record"

    started = started_records[0]
    assert started.levelno == logging.INFO
    # Check structured extra fields are present
    assert hasattr(started, "plugin_name")
    assert started.plugin_name == "obs-plugin"
    assert hasattr(started, "child_count")
    assert started.child_count == 2
    assert hasattr(started, "transaction_id")


def test_import_complete_log_contains_duration_ms(caplog):
    """import_plugin_transactional logs completion at INFO with duration_ms field."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")
    session = _build_session_for_new_artifacts(graph)

    with caplog.at_level(logging.INFO, logger="skillmeat.core.importer"):
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
            patch("skillmeat.cache.models.ArtifactVersion"),
            patch("skillmeat.cache.models.CompositeArtifact"),
            patch("skillmeat.cache.models.CompositeMembership"),
            patch("skillmeat.core.importer._OTEL_AVAILABLE", False),
            patch("skillmeat.core.importer._tracer", None),
        ):
            artifact_instances = []
            for i, child in enumerate(graph.children):
                inst = MagicMock()
                inst.id = f"{child.type}:{child.name}"
                inst.uuid = f"uuid-dur-{i:04d}"
                artifact_instances.append(inst)
            MockArtifact.side_effect = artifact_instances

            result = import_plugin_transactional(
                discovered_graph=graph,
                source_url=SOURCE_URL,
                session=session,
                project_id=PROJECT_ID,
                collection_id=COLLECTION_ID,
            )

    assert result.success is True
    # Find the "committed" log record
    committed_records = [r for r in caplog.records if "committed" in r.message]
    assert (
        committed_records
    ), "Expected an import_plugin_transactional committed log record"

    committed = committed_records[0]
    assert committed.levelno == logging.INFO
    assert hasattr(committed, "duration_ms")
    assert isinstance(committed.duration_ms, float)
    assert committed.duration_ms >= 0.0


def test_import_failure_logged_at_error_level(caplog):
    """import_plugin_transactional logs failures at ERROR level with error field."""
    graph = _make_discovered_graph("obs-plugin")
    session = MagicMock()
    session.rollback.return_value = None

    with caplog.at_level(logging.ERROR, logger="skillmeat.core.importer"):
        with (
            patch(
                "skillmeat.core.hashing.compute_artifact_hash",
                side_effect=FileNotFoundError("no such file"),
            ),
            patch("skillmeat.cache.models.Artifact"),
            patch("skillmeat.cache.models.ArtifactVersion"),
            patch("skillmeat.cache.models.CompositeArtifact"),
            patch("skillmeat.cache.models.CompositeMembership"),
            patch("skillmeat.core.importer._OTEL_AVAILABLE", False),
            patch("skillmeat.core.importer._tracer", None),
        ):
            result = import_plugin_transactional(
                discovered_graph=graph,
                source_url=SOURCE_URL,
                session=session,
                project_id=PROJECT_ID,
                collection_id=COLLECTION_ID,
            )

    assert result.success is False
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert error_records, "Expected an ERROR log record on import failure"

    error_rec = error_records[0]
    assert hasattr(error_rec, "transaction_id")
    assert hasattr(error_rec, "plugin_name")
    assert error_rec.plugin_name == "obs-plugin"


# ---------------------------------------------------------------------------
# No-op fallback (OTel not available)
# ---------------------------------------------------------------------------


def test_import_works_without_otel(caplog):
    """import_plugin_transactional runs cleanly when _OTEL_AVAILABLE is False."""
    from skillmeat.core.deduplication import DeduplicationDecision, DeduplicationResult

    graph = _make_discovered_graph("obs-plugin")
    session = _build_session_for_new_artifacts(graph)

    with caplog.at_level(logging.INFO, logger="skillmeat.core.importer"):
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
            patch("skillmeat.cache.models.ArtifactVersion"),
            patch("skillmeat.cache.models.CompositeArtifact"),
            patch("skillmeat.cache.models.CompositeMembership"),
            # Explicitly disable OTel
            patch("skillmeat.core.importer._OTEL_AVAILABLE", False),
            patch("skillmeat.core.importer._tracer", None),
        ):
            artifact_instances = []
            for i, child in enumerate(graph.children):
                inst = MagicMock()
                inst.id = f"{child.type}:{child.name}"
                inst.uuid = f"uuid-nootel-{i:04d}"
                artifact_instances.append(inst)
            MockArtifact.side_effect = artifact_instances

            result = import_plugin_transactional(
                discovered_graph=graph,
                source_url=SOURCE_URL,
                session=session,
                project_id=PROJECT_ID,
                collection_id=COLLECTION_ID,
            )

    assert result.success is True
    assert result.children_imported == 2
    assert result.children_reused == 0
    assert result.plugin_id == "composite:obs-plugin"


# ---------------------------------------------------------------------------
# Hashing module: span around compute_artifact_hash
# ---------------------------------------------------------------------------


def test_compute_artifact_hash_emits_span(tmp_path):
    """compute_artifact_hash emits an artifact.hash_compute OTel span when available."""
    # Create a real file to hash
    test_file = tmp_path / "skill.md"
    test_file.write_text("# Test skill\n")

    fake_tracer = _FakeTracer()

    with (
        patch("skillmeat.core.hashing._OTEL_AVAILABLE", True),
        patch("skillmeat.core.hashing._tracer", fake_tracer),
    ):
        from skillmeat.core.hashing import compute_artifact_hash

        content_hash = compute_artifact_hash(str(test_file))

    assert len(content_hash) == 64  # SHA-256 hex
    span_names = [s.name for s in fake_tracer.spans]
    assert "artifact.hash_compute" in span_names

    hash_span = next(s for s in fake_tracer.spans if s.name == "artifact.hash_compute")
    assert hash_span.attributes["artifact_name"] == "skill.md"
    assert hash_span.attributes["content_hash"] == content_hash


def test_compute_artifact_hash_no_span_without_otel(tmp_path):
    """compute_artifact_hash does not raise when OTel is unavailable."""
    test_file = tmp_path / "skill.md"
    test_file.write_text("# Test skill\n")

    with (
        patch("skillmeat.core.hashing._OTEL_AVAILABLE", False),
        patch("skillmeat.core.hashing._tracer", None),
    ):
        from skillmeat.core.hashing import compute_artifact_hash

        content_hash = compute_artifact_hash(str(test_file))

    assert len(content_hash) == 64


# ---------------------------------------------------------------------------
# Deduplication module: span around resolve_artifact_for_import
# ---------------------------------------------------------------------------


def test_resolve_artifact_for_import_emits_span():
    """resolve_artifact_for_import emits an artifact.dedup_resolve OTel span."""
    from skillmeat.core.deduplication import (
        DeduplicationDecision,
        resolve_artifact_for_import,
    )

    session = MagicMock()
    session.query.return_value = _noop_filter_chain(return_value=None)

    fake_tracer = _FakeTracer()

    with (
        patch("skillmeat.core.deduplication._OTEL_AVAILABLE", True),
        patch("skillmeat.core.deduplication._tracer", fake_tracer),
    ):
        result = resolve_artifact_for_import(
            name="my-skill",
            artifact_type="skill",
            content_hash="f" * 64,
            session=session,
        )

    assert result.decision == DeduplicationDecision.CREATE_NEW_ARTIFACT
    span_names = [s.name for s in fake_tracer.spans]
    assert "artifact.dedup_resolve" in span_names

    dedup_span = next(
        s for s in fake_tracer.spans if s.name == "artifact.dedup_resolve"
    )
    assert dedup_span.attributes["artifact_name"] == "my-skill"
    assert dedup_span.attributes["content_hash"] == "f" * 64
    assert dedup_span.attributes["decision"] == "create_new_artifact"


def test_resolve_artifact_for_import_no_span_without_otel():
    """resolve_artifact_for_import does not raise when OTel is unavailable."""
    from skillmeat.core.deduplication import (
        DeduplicationDecision,
        resolve_artifact_for_import,
    )

    session = MagicMock()
    session.query.return_value = _noop_filter_chain(return_value=None)

    with (
        patch("skillmeat.core.deduplication._OTEL_AVAILABLE", False),
        patch("skillmeat.core.deduplication._tracer", None),
    ):
        result = resolve_artifact_for_import(
            name="my-skill",
            artifact_type="skill",
            content_hash="a" * 64,
            session=session,
        )

    assert result.decision == DeduplicationDecision.CREATE_NEW_ARTIFACT
