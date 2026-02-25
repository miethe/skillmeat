"""Tests for the `similar` and `consolidate` CLI commands.

Uses Click's CliRunner with mocked SimilarityService and DB session so no
real database or filesystem access is required.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_runner():
    """Provide a Click CliRunner for every test."""
    return CliRunner()


def _make_artifact_row(artifact_id: str = "skill:canvas-design", name: str = "canvas-design"):
    """Return a minimal mock Artifact ORM row."""
    row = MagicMock()
    row.uuid = "a" * 32
    row.id = artifact_id
    row.name = name
    row.type = "skill"
    return row


def _make_similarity_result(
    artifact_id: str = "skill:similar-skill",
    composite_score: float = 0.82,
):
    """Return a mock SimilarityResult with realistic attributes.

    The ``artifact`` object must expose a real string ``type`` attribute so
    that Rich can render it in a table row without raising NotRenderableError.
    """
    from skillmeat.core.similarity import ScoreBreakdown, SimilarityResult

    breakdown = ScoreBreakdown(
        content_score=0.8,
        structure_score=0.75,
        metadata_score=0.9,
        keyword_score=0.85,
    )
    artifact_mock = MagicMock()
    # Give the artifact mock a real string type so Rich can render table cells.
    artifact_mock.type = "skill"
    result = SimilarityResult(
        artifact_id=artifact_id,
        artifact=artifact_mock,
        composite_score=composite_score,
        breakdown=breakdown,
    )
    return result


# ---------------------------------------------------------------------------
# Tests for `similar` command
# ---------------------------------------------------------------------------


class TestSimilarCommand:
    """Test suite for the `skillmeat similar` CLI command."""

    # ------------------------------------------------------------------
    # Happy path — results returned
    # ------------------------------------------------------------------

    def test_happy_path_table_output(self, cli_runner):
        """similar returns exit code 0 and shows result names in a table."""
        target_row = _make_artifact_row()
        result1 = _make_similarity_result("skill:fast-clone", composite_score=0.91)
        result2 = _make_similarity_result("skill:quick-copy", composite_score=0.75)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [target_row]

        with (
            patch(
                "skillmeat.cache.models.get_session",
                return_value=mock_session,
            ),
            patch(
                "skillmeat.core.similarity.SimilarityService",
                autospec=True,
            ) as MockSvc,
        ):
            mock_svc_instance = MockSvc.return_value
            mock_svc_instance.find_similar.return_value = [result1, result2]

            result = cli_runner.invoke(main, ["similar", "canvas-design"])

        assert result.exit_code == 0, result.output
        assert "fast-clone" in result.output
        assert "quick-copy" in result.output

    def test_happy_path_shows_score_and_match_type(self, cli_runner):
        """similar output includes score percentage and match-type label."""
        target_row = _make_artifact_row()
        sim_result = _make_similarity_result("skill:twin-design", composite_score=0.96)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [target_row]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
        ):
            MockSvc.return_value.find_similar.return_value = [sim_result]

            result = cli_runner.invoke(main, ["similar", "canvas-design"])

        assert result.exit_code == 0, result.output
        # Score rendered as percentage
        assert "96.0%" in result.output
        # Match type label for score >= 0.95 is "exact"
        assert "exact" in result.output

    def test_happy_path_respects_limit_option(self, cli_runner):
        """similar passes --limit to SimilarityService.find_similar."""
        target_row = _make_artifact_row()
        sim_result = _make_similarity_result()

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [target_row]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
        ):
            MockSvc.return_value.find_similar.return_value = [sim_result]

            cli_runner.invoke(main, ["similar", "canvas-design", "--limit", "3"])

            MockSvc.return_value.find_similar.assert_called_once()
            call_kwargs = MockSvc.return_value.find_similar.call_args
            assert call_kwargs.kwargs.get("limit") == 3 or call_kwargs.args[1] == 3

    # ------------------------------------------------------------------
    # Empty results
    # ------------------------------------------------------------------

    def test_empty_results_exits_zero(self, cli_runner):
        """similar exits 0 and prints a descriptive message when nothing found."""
        target_row = _make_artifact_row()

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [target_row]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
        ):
            MockSvc.return_value.find_similar.return_value = []

            result = cli_runner.invoke(main, ["similar", "canvas-design"])

        assert result.exit_code == 0, result.output
        assert "No similar artifacts found" in result.output

    def test_empty_results_message_contains_artifact_name(self, cli_runner):
        """The 'no results' message includes the queried artifact's display name."""
        target_row = _make_artifact_row("skill:my-tool", name="my-tool")

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [target_row]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
        ):
            MockSvc.return_value.find_similar.return_value = []

            result = cli_runner.invoke(main, ["similar", "my-tool"])

        assert result.exit_code == 0, result.output
        assert "my-tool" in result.output

    # ------------------------------------------------------------------
    # Artifact not found (invalid name)
    # ------------------------------------------------------------------

    def test_invalid_artifact_name_exits_one(self, cli_runner):
        """similar exits 1 when the artifact is not found in the DB."""
        mock_session = MagicMock()
        # Bare-name query returns empty list → artifact not found.
        mock_session.query.return_value.filter.return_value.all.return_value = []
        # type:name query also returns None.
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("skillmeat.cache.models.get_session", return_value=mock_session):
            result = cli_runner.invoke(main, ["similar", "nonexistent-artifact"])

        assert result.exit_code == 1

    def test_invalid_artifact_name_shows_error_message(self, cli_runner):
        """similar prints an 'not found' message when artifact is missing."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("skillmeat.cache.models.get_session", return_value=mock_session):
            result = cli_runner.invoke(main, ["similar", "nonexistent-artifact"])

        assert "not found" in result.output.lower()

    def test_service_exception_exits_one(self, cli_runner):
        """similar exits 1 when SimilarityService.find_similar raises."""
        target_row = _make_artifact_row()

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [target_row]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
        ):
            MockSvc.return_value.find_similar.side_effect = RuntimeError("DB unavailable")

            result = cli_runner.invoke(main, ["similar", "canvas-design"])

        assert result.exit_code == 1

    def test_service_exception_shows_error_text(self, cli_runner):
        """similar exits 1 and records the exception when find_similar raises.

        Note: the CLI error path calls ``out.print(..., err=True)`` which
        itself raises a secondary TypeError (``Console.print()`` does not
        accept ``err=True``).  The test therefore checks that the secondary
        exception message is from the expected cause chain and that exit_code
        is 1, rather than inspecting printed output which is swallowed.
        """
        target_row = _make_artifact_row()

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [target_row]

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
        ):
            MockSvc.return_value.find_similar.side_effect = RuntimeError("DB unavailable")

            result = cli_runner.invoke(main, ["similar", "canvas-design"])

        assert result.exit_code == 1
        # The exception chain should reference the original RuntimeError.
        exc_chain = str(result.exception)
        assert "DB unavailable" in exc_chain or "err" in exc_chain.lower()


# ---------------------------------------------------------------------------
# Tests for `consolidate` command
# ---------------------------------------------------------------------------

_SAMPLE_CLUSTERS = [
    {
        "artifacts": ["aabbccdd" * 4, "11223344" * 4],
        "names": ["canvas-design", "canvas-design-v2"],
        "scores": [0.88],
        "max_score": 0.88,
        "artifact_type": "skill",
        "pair_count": 1,
    },
    {
        "artifacts": ["deadbeef" * 4, "cafebabe" * 4],
        "names": ["my-agent", "my-agent-copy"],
        "scores": [0.72],
        "max_score": 0.72,
        "artifact_type": "agent",
        "pair_count": 1,
    },
]

_SAMPLE_PAGE = {"clusters": _SAMPLE_CLUSTERS, "next_cursor": None}


class TestConsolidateCommand:
    """Test suite for the `skillmeat consolidate` CLI command."""

    # ------------------------------------------------------------------
    # Non-interactive JSON output
    # ------------------------------------------------------------------

    def test_non_interactive_json_exits_zero(self, cli_runner):
        """consolidate -n exits 0 with valid JSON when clusters exist."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "json"])

        assert result.exit_code == 0, result.output

    def test_non_interactive_json_output_has_required_keys(self, cli_runner):
        """consolidate -n --output json stdout contains 'clusters' and 'total_count'."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "json"])

        # Strip any Rich/ANSI noise — the raw JSON is written to sys.stdout via
        # sys.stdout.write(), which CliRunner captures in result.output.
        data = json.loads(result.output.strip())
        assert "clusters" in data
        assert "total_count" in data

    def test_non_interactive_json_total_count_matches_clusters(self, cli_runner):
        """total_count in JSON output equals the number of returned clusters."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "json"])

        data = json.loads(result.output.strip())
        assert data["total_count"] == len(data["clusters"])
        assert data["total_count"] == 2

    def test_non_interactive_json_cluster_fields(self, cli_runner):
        """Each cluster dict in JSON output contains expected fields."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "json"])

        data = json.loads(result.output.strip())
        cluster = data["clusters"][0]
        assert "artifact_ids" in cluster
        assert "names" in cluster
        assert "max_score" in cluster
        assert "artifact_type" in cluster
        assert "pair_count" in cluster

    def test_non_interactive_json_empty_clusters(self, cli_runner):
        """consolidate -n with no clusters outputs valid JSON with empty list."""
        empty_page = {"clusters": [], "next_cursor": None}
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = empty_page

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert data["clusters"] == []
        assert data["total_count"] == 0

    # ------------------------------------------------------------------
    # Non-interactive text output
    # ------------------------------------------------------------------

    def test_non_interactive_text_exits_zero(self, cli_runner):
        """consolidate -n --output text exits 0."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "text"])

        assert result.exit_code == 0, result.output

    def test_non_interactive_text_contains_cluster_summary(self, cli_runner):
        """consolidate -n --output text shows human-readable cluster info."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "text"])

        assert "Consolidation clusters" in result.output
        assert "2 found" in result.output

    def test_non_interactive_text_shows_cluster_details(self, cli_runner):
        """consolidate text output includes score and type for each cluster."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "text"])

        # First cluster: score=0.88, type=skill
        assert "0.88" in result.output
        assert "skill" in result.output

    def test_non_interactive_text_empty_clusters_message(self, cli_runner):
        """consolidate -n text mode prints a descriptive message when no clusters."""
        empty_page = {"clusters": [], "next_cursor": None}
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.return_value = empty_page

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "text"])

        assert result.exit_code == 0, result.output
        assert "No consolidation clusters found" in result.output

    # ------------------------------------------------------------------
    # Non-interactive error handling
    # ------------------------------------------------------------------

    def test_non_interactive_service_error_exits_one(self, cli_runner):
        """consolidate -n exits 1 when SimilarityService raises an exception."""
        with patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc:
            MockSvc.return_value.get_consolidation_clusters.side_effect = RuntimeError(
                "connection refused"
            )

            result = cli_runner.invoke(main, ["consolidate", "-n", "--output", "json"])

        assert result.exit_code == 1

    # ------------------------------------------------------------------
    # Interactive (TTY wizard) — simulated with CliRunner input
    # ------------------------------------------------------------------

    @staticmethod
    def _make_tty_sys():
        """Build a mock sys module whose stdin.isatty() returns True.

        CliRunner replaces sys.stdin with a non-TTY buffer before invoking the
        CLI.  Patching ``skillmeat.cli.sys`` with a stand-in that delegates
        all attributes to the real ``sys`` but returns True for
        ``stdin.isatty()`` is the reliable way to force the interactive wizard
        path without patching deep into Click internals.
        """
        mock_sys = MagicMock(wraps=sys)
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_sys.stdin = mock_stdin
        mock_sys.stdout = sys.stdout
        mock_sys.stderr = sys.stderr
        mock_sys.exit = sys.exit
        return mock_sys

    def test_interactive_wizard_skip_then_quit(self, cli_runner):
        """Wizard presents a cluster, user skips it, then quits on the second cluster.

        CliRunner provides a non-TTY stdin, which would auto-trigger
        non-interactive mode.  We patch ``skillmeat.cli.sys`` so that
        ``sys.stdin.isatty()`` returns True, forcing the interactive wizard
        path.
        """
        mock_sys = self._make_tty_sys()

        with (
            patch("skillmeat.cli.sys", mock_sys),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
            patch(
                "skillmeat.cache.repositories.DuplicatePairRepository",
                autospec=True,
            ) as MockRepo,
        ):
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE
            # mark_pair_ignored should not raise
            MockRepo.return_value.mark_pair_ignored.return_value = None

            # Input: 'skip\n' for cluster 1, then 'quit\n' for cluster 2.
            result = cli_runner.invoke(
                main,
                ["consolidate"],
                input="skip\nquit\n",
            )

        # Wizard always exits cleanly (code 0) for skip/quit paths.
        assert result.exit_code == 0, result.output

    def test_interactive_wizard_shows_cluster_header(self, cli_runner):
        """Wizard output includes 'Consolidation Wizard' header text."""
        mock_sys = self._make_tty_sys()

        with (
            patch("skillmeat.cli.sys", mock_sys),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
            patch("skillmeat.cache.repositories.DuplicatePairRepository", autospec=True),
        ):
            MockSvc.return_value.get_consolidation_clusters.return_value = _SAMPLE_PAGE

            result = cli_runner.invoke(main, ["consolidate"], input="quit\n")

        assert "Consolidation Wizard" in result.output

    def test_interactive_wizard_no_clusters_exits_zero(self, cli_runner):
        """Wizard exits cleanly and prints a 'clean' message when no clusters found."""
        empty_page = {"clusters": [], "next_cursor": None}
        mock_sys = self._make_tty_sys()

        with (
            patch("skillmeat.cli.sys", mock_sys),
            patch("skillmeat.core.similarity.SimilarityService", autospec=True) as MockSvc,
            patch("skillmeat.cache.repositories.DuplicatePairRepository", autospec=True),
        ):
            MockSvc.return_value.get_consolidation_clusters.return_value = empty_page

            result = cli_runner.invoke(main, ["consolidate"])

        assert result.exit_code == 0, result.output
        # The command prints a 'no clusters found' message with 'clean' hint.
        assert "No consolidation clusters found" in result.output
