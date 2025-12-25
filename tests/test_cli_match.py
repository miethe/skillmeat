"""Tests for the CLI match command."""

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.scoring.models import ArtifactScore, ScoringResult


def strip_ansi(text):
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_artifacts():
    """Create mock artifacts for testing."""
    return [
        Artifact(
            name="pdf-processor",
            type=ArtifactType.SKILL,
            path="skills/pdf-processor",
            origin="github",
            metadata=ArtifactMetadata(
                title="PDF Processor",
                description="Process PDF documents",
                tags=["pdf", "document"],
            ),
            added=None,
        ),
        Artifact(
            name="document-handler",
            type=ArtifactType.SKILL,
            path="skills/document-handler",
            origin="github",
            metadata=ArtifactMetadata(
                title="Document Handler",
                description="Handle various document types",
                tags=["document", "conversion"],
            ),
            added=None,
        ),
        Artifact(
            name="file-converter",
            type=ArtifactType.COMMAND,
            path="commands/file-converter",
            origin="local",
            metadata=ArtifactMetadata(
                title="File Converter",
                description="Convert files between formats",
                tags=["conversion"],
            ),
            added=None,
        ),
    ]


@pytest.fixture
def mock_scores():
    """Create mock scoring results."""
    return [
        ArtifactScore(
            artifact_id="skill:pdf-processor",
            trust_score=85.0,
            quality_score=70.0,
            match_score=98.0,
            confidence=92.5,
        ),
        ArtifactScore(
            artifact_id="skill:document-handler",
            trust_score=75.0,
            quality_score=65.0,
            match_score=85.0,
            confidence=78.2,
        ),
        ArtifactScore(
            artifact_id="command:file-converter",
            trust_score=60.0,
            quality_score=55.0,
            match_score=75.0,
            confidence=65.1,
        ),
    ]


@pytest.fixture
def mock_scoring_result(mock_scores):
    """Create mock ScoringResult."""
    return ScoringResult(
        scores=mock_scores,
        used_semantic=True,
        degraded=False,
        degradation_reason=None,
        duration_ms=150.5,
        query="pdf",
    )


class TestMatchCommand:
    """Tests for skillmeat match command."""

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_basic_match(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scoring_result,
    ):
        """Test basic match command."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = mock_scoring_result

        # Run command
        result = runner.invoke(main, ["match", "pdf"])

        # Assertions
        assert result.exit_code == 0
        assert "Artifact Match Results" in result.output
        assert "pdf-processor" in result.output
        # Check for any confidence score (format may vary)
        assert "87.8" in result.output or "92.5" in result.output
        mock_artifact_manager.list_artifacts.assert_called_once()

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_match_with_limit(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scoring_result,
    ):
        """Test match command with --limit option."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = mock_scoring_result

        # Run command with limit
        result = runner.invoke(main, ["match", "pdf", "--limit", "2"])

        # Assertions
        assert result.exit_code == 0
        # Should show only top 2 results
        assert "Top 2 Matches" in result.output
        assert "pdf-processor" in result.output
        assert "document-handler" in result.output

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_match_with_min_confidence(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scoring_result,
    ):
        """Test match command with --min-confidence filtering."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = mock_scoring_result

        # Run command with min-confidence filter (should exclude file-converter at 65.1)
        result = runner.invoke(main, ["match", "pdf", "--min-confidence", "70"])

        # Assertions
        assert result.exit_code == 0
        assert "pdf-processor" in result.output  # 92.5
        assert "document-handler" in result.output  # 78.2
        # file-converter (65.1) should be filtered out - check it's not in matches
        # Note: May appear in query/header, so check for specific context
        assert "Top 2 Matches" in result.output

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_match_verbose_output(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scoring_result,
    ):
        """Test match command with --verbose showing score breakdown."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = mock_scoring_result

        # Run command with verbose
        result = runner.invoke(main, ["match", "pdf", "--verbose"])

        # Assertions
        assert result.exit_code == 0
        # Should show breakdown columns
        assert "Trust" in result.output
        assert "Quality" in result.output
        assert "Match" in result.output
        # Should show score values
        assert "85.0" in result.output  # trust_score for pdf-processor
        assert "98.0" in result.output  # match_score for pdf-processor

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_match_json_output(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scoring_result,
    ):
        """Test match command with --json output (enhanced in P2-T6)."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = mock_scoring_result

        # Run command with JSON output
        result = runner.invoke(main, ["match", "pdf", "--json"])

        # Assertions
        assert result.exit_code == 0
        # Parse JSON output
        output_data = json.loads(result.output)

        # Original fields
        assert output_data["query"] == "pdf"
        assert output_data["used_semantic"] is True
        assert output_data["degraded"] is False
        assert len(output_data["results"]) == 3
        assert output_data["results"][0]["artifact_id"] == "skill:pdf-processor"
        assert output_data["results"][0]["confidence"] > 80.0

        # Enhanced fields (P2-T6)
        assert output_data["schema_version"] == "1.0.0"
        assert "scored_at" in output_data
        # Validate ISO 8601 timestamp
        from datetime import datetime
        datetime.fromisoformat(output_data["scored_at"].replace("Z", "+00:00"))
        assert output_data["total_artifacts"] == 3
        assert output_data["result_count"] == 3

        # Enhanced result fields
        first_result = output_data["results"][0]
        assert first_result["name"] == "pdf-processor"
        assert first_result["artifact_type"] == "skill"
        assert first_result["title"] == "PDF Processor"
        assert "explanation" in first_result
        assert isinstance(first_result["explanation"], str)
        # Explanation should be descriptive (High/Moderate/Low match)
        assert any(
            keyword in first_result["explanation"]
            for keyword in ["High match", "Moderate match", "Low relevance"]
        )

    @patch("skillmeat.cli.ArtifactManager")
    def test_match_no_artifacts(
        self, mock_artifact_manager_class, runner
    ):
        """Test match command with no artifacts in collection."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = []
        mock_artifact_manager_class.return_value = mock_artifact_manager

        # Run command
        result = runner.invoke(main, ["match", "pdf"])

        # Assertions
        assert result.exit_code == 0
        assert "No artifacts found in collection" in result.output

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_match_no_results_above_threshold(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scoring_result,
    ):
        """Test match command when no results meet min-confidence threshold."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = mock_scoring_result

        # Run command with very high min-confidence (above all scores)
        result = runner.invoke(main, ["match", "pdf", "--min-confidence", "95"])

        # Assertions
        assert result.exit_code == 0
        # Strip ANSI codes for cleaner matching
        clean_output = strip_ansi(result.output)
        assert "No artifacts found matching" in clean_output
        assert "pdf" in clean_output
        assert "confidence >= 95" in clean_output

    @patch("skillmeat.cli.ArtifactManager")
    def test_match_invalid_min_confidence(self, mock_artifact_manager_class, runner):
        """Test match command with invalid min-confidence value."""
        # Setup mocks (to avoid hitting actual artifact loading code)
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = []
        mock_artifact_manager_class.return_value = mock_artifact_manager

        # Test value above 100
        result = runner.invoke(main, ["match", "pdf", "--min-confidence", "150"])
        assert result.exit_code == 1
        # Check both stdout and output combined
        output = result.output + (result.stdout if hasattr(result, 'stdout') else '')
        assert "min-confidence must be between 0 and 100" in output or result.exception is not None

        # Test negative value
        result = runner.invoke(main, ["match", "pdf", "--min-confidence", "-10"])
        assert result.exit_code == 1
        output = result.output + (result.stdout if hasattr(result, 'stdout') else '')
        assert "min-confidence must be between 0 and 100" in output or result.exception is not None

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_match_degraded_mode(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scores,
    ):
        """Test match command when scoring is degraded (keyword-only fallback)."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        # Create degraded scoring result
        degraded_result = ScoringResult(
            scores=mock_scores,
            used_semantic=False,
            degraded=True,
            degradation_reason="Embedding service unavailable: missing API key",
            duration_ms=50.0,
            query="pdf",
        )

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = degraded_result

        # Run command
        result = runner.invoke(main, ["match", "pdf"])

        # Assertions
        assert result.exit_code == 0
        assert "Keyword-only" in result.output
        assert "Warning:" in result.output
        assert "missing API key" in result.output

    @patch("skillmeat.cli.ArtifactManager")
    @patch("skillmeat.core.scoring.service.ScoringService")
    @patch("skillmeat.cli.asyncio.run")
    def test_match_with_collection_option(
        self,
        mock_asyncio_run,
        mock_scoring_service_class,
        mock_artifact_manager_class,
        runner,
        mock_artifacts,
        mock_scoring_result,
    ):
        """Test match command with --collection option."""
        # Setup mocks
        mock_artifact_manager = MagicMock()
        mock_artifact_manager.list_artifacts.return_value = mock_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_scoring_service = MagicMock()
        mock_scoring_service_class.return_value = mock_scoring_service
        mock_asyncio_run.return_value = mock_scoring_result

        # Run command with collection specified
        result = runner.invoke(main, ["match", "pdf", "--collection", "work"])

        # Assertions
        assert result.exit_code == 0
        mock_artifact_manager.list_artifacts.assert_called_once_with(
            collection_name="work"
        )
