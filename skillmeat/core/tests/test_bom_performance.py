"""Performance benchmark for BomGenerator.

Verifies that generating a BOM over 50 mock artifacts completes within a
reasonable wall-clock budget (< 2 seconds).  Mark with ``pytest.mark.slow``
so it can be excluded from fast test runs.

Run:
    pytest -m slow skillmeat/core/tests/test_bom_performance.py -v
"""

from __future__ import annotations

import time
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from skillmeat.core.bom.generator import BomGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ARTIFACT_TYPES = [
    "skill",
    "command",
    "agent",
    "mcp_server",
    "hook",
    "workflow",
    "project_config",
    "spec_file",
    "rule_file",
    "context_file",
]


def _make_artifact(idx: int) -> Any:
    """Return a lightweight MagicMock shaped like an ORM Artifact row."""
    art_type = _ARTIFACT_TYPES[idx % len(_ARTIFACT_TYPES)]
    art = MagicMock()
    art.id = f"{art_type}:perf-artifact-{idx:03d}"
    art.name = f"perf-artifact-{idx:03d}"
    art.type = art_type
    art.source = f"user/repo/artifact-{idx}"
    art.deployed_version = f"v{idx}.0.0"
    art.upstream_version = None
    art.content = f"Content for artifact number {idx}"
    art.content_hash = None  # force hash computation from content
    art.project_id = "proj-perf"
    art.created_at = None
    art.updated_at = None
    art.artifact_metadata = None
    art.uuid = f"uuid-perf-{idx:03d}"
    return art


def _make_session(artifacts: List[Any]) -> MagicMock:
    """Return a MagicMock session whose query().all() returns *artifacts*."""
    session = MagicMock()
    query_mock = MagicMock()
    query_mock.all.return_value = artifacts
    query_mock.filter.return_value = query_mock
    session.query.return_value = query_mock
    return session


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestBomGeneratorPerformance:
    """Performance benchmarks for BomGenerator."""

    _NUM_ARTIFACTS = 50
    _MAX_SECONDS = 2.0

    @pytest.fixture(scope="class")
    def artifacts(self) -> List[Any]:
        """50 mock artifacts of mixed types."""
        return [_make_artifact(i) for i in range(self._NUM_ARTIFACTS)]

    @pytest.fixture(scope="class")
    def session(self, artifacts: List[Any]) -> MagicMock:
        """Mock session returning all 50 artifacts."""
        return _make_session(artifacts)

    def test_generate_50_artifacts_under_2_seconds(
        self, artifacts: List[Any], session: MagicMock
    ) -> None:
        """BomGenerator.generate() over 50 artifacts completes in < 2 s."""
        gen = BomGenerator(session=session)

        start = time.monotonic()
        result = gen.generate()
        elapsed = time.monotonic() - start

        assert result["artifact_count"] == self._NUM_ARTIFACTS, (
            f"Expected {self._NUM_ARTIFACTS} artifacts, got {result['artifact_count']}"
        )
        assert elapsed < self._MAX_SECONDS, (
            f"BOM generation took {elapsed:.3f}s, exceeded {self._MAX_SECONDS}s budget."
        )

    def test_generate_is_repeatable_performance(
        self, artifacts: List[Any], session: MagicMock
    ) -> None:
        """Three consecutive generate() calls all complete under the budget."""
        gen = BomGenerator(session=session)

        for run in range(3):
            start = time.monotonic()
            result = gen.generate()
            elapsed = time.monotonic() - start

            assert result["artifact_count"] == self._NUM_ARTIFACTS
            assert elapsed < self._MAX_SECONDS, (
                f"Run {run + 1}: generation took {elapsed:.3f}s, "
                f"exceeded {self._MAX_SECONDS}s budget."
            )

    def test_elapsed_ms_recorded_in_output(
        self, artifacts: List[Any], session: MagicMock
    ) -> None:
        """The BOM output metadata.elapsed_ms field is a positive number."""
        gen = BomGenerator(session=session)
        result = gen.generate()

        elapsed_ms = result["metadata"].get("elapsed_ms")
        assert elapsed_ms is not None, "elapsed_ms missing from BOM metadata"
        assert isinstance(elapsed_ms, (int, float)), (
            f"elapsed_ms should be numeric, got {type(elapsed_ms)}"
        )
        assert elapsed_ms >= 0, f"elapsed_ms should be non-negative, got {elapsed_ms}"
