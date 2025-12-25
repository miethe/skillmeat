"""Tests for SemanticScorer class."""

import math

import pytest

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.embedding_provider import EmbeddingProvider
from skillmeat.core.scoring.semantic_scorer import SemanticScorer


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, available: bool = True, return_none: bool = False):
        self.available = available
        self.return_none = return_none
        self.call_count = 0
        self.last_text = None

    async def get_embedding(self, text: str):
        self.call_count += 1
        self.last_text = text

        if self.return_none:
            return None

        # Return a deterministic embedding based on text
        # This allows us to test similarity calculations
        if "pdf" in text.lower():
            return [1.0, 0.0, 0.0]
        elif "database" in text.lower():
            return [0.0, 1.0, 0.0]
        elif "process" in text.lower():
            return [0.7, 0.7, 0.0]  # Similar to both pdf and processing
        else:
            return [0.0, 0.0, 1.0]

    def is_available(self) -> bool:
        return self.available

    def get_embedding_dimension(self) -> int:
        return 3


@pytest.fixture
def mock_provider():
    """Create mock embedding provider."""
    return MockEmbeddingProvider()


@pytest.fixture
def semantic_scorer(mock_provider):
    """Create semantic scorer with mock provider."""
    return SemanticScorer(mock_provider)


def test_scorer_initialization(mock_provider):
    """Test SemanticScorer initialization."""
    scorer = SemanticScorer(mock_provider, min_score=10.0, max_score=95.0)

    assert scorer.provider == mock_provider
    assert scorer.min_score == 10.0
    assert scorer.max_score == 95.0


def test_scorer_availability(mock_provider):
    """Test availability checking."""
    # Available provider
    scorer = SemanticScorer(mock_provider)
    assert scorer.is_available() is True

    # Unavailable provider
    unavailable_provider = MockEmbeddingProvider(available=False)
    scorer = SemanticScorer(unavailable_provider)
    assert scorer.is_available() is False


@pytest.mark.asyncio
async def test_score_artifact_basic(semantic_scorer):
    """Test basic artifact scoring."""
    artifact = ArtifactMetadata(
        title="PDF Processor", description="Process PDF documents"
    )

    score = await semantic_scorer.score_artifact("pdf processing", artifact)

    assert score is not None
    assert 0 <= score <= 100


@pytest.mark.asyncio
async def test_score_artifact_high_similarity(semantic_scorer):
    """Test scoring with high semantic similarity."""
    artifact = ArtifactMetadata(
        title="PDF Tool", description="Extract text from PDF files"
    )

    score = await semantic_scorer.score_artifact("pdf extraction", artifact)

    # Both query and artifact contain "pdf", should have high similarity
    assert score is not None
    assert score > 90


@pytest.mark.asyncio
async def test_score_artifact_low_similarity(semantic_scorer):
    """Test scoring with low semantic similarity."""
    artifact = ArtifactMetadata(
        title="Database Tool", description="Query and manage databases"
    )

    score = await semantic_scorer.score_artifact("pdf processing", artifact)

    # Query has "pdf", artifact has "database" - orthogonal vectors
    assert score is not None
    assert score < 10


@pytest.mark.asyncio
async def test_score_artifact_empty_query(semantic_scorer):
    """Test scoring with empty query."""
    artifact = ArtifactMetadata(title="Test", description="Test artifact")

    # Empty string
    score = await semantic_scorer.score_artifact("", artifact)
    assert score is None

    # Whitespace only
    score = await semantic_scorer.score_artifact("   ", artifact)
    assert score is None


@pytest.mark.asyncio
async def test_score_artifact_no_description(semantic_scorer):
    """Test scoring artifact without description."""
    artifact = ArtifactMetadata(title=None, description=None)

    score = await semantic_scorer.score_artifact("test query", artifact)

    # Should return min_score when no artifact text
    assert score == semantic_scorer.min_score


@pytest.mark.asyncio
async def test_score_artifact_unavailable_provider():
    """Test scoring when provider is unavailable."""
    provider = MockEmbeddingProvider(available=False)
    scorer = SemanticScorer(provider)

    artifact = ArtifactMetadata(title="Test", description="Test artifact")
    score = await scorer.score_artifact("test", artifact)

    assert score is None


@pytest.mark.asyncio
async def test_score_artifact_embedding_failure():
    """Test scoring when embedding generation fails."""
    provider = MockEmbeddingProvider(return_none=True)
    scorer = SemanticScorer(provider)

    artifact = ArtifactMetadata(title="Test", description="Test artifact")
    score = await scorer.score_artifact("test", artifact)

    assert score is None


@pytest.mark.asyncio
async def test_score_all(semantic_scorer):
    """Test scoring multiple artifacts."""
    artifacts = [
        ArtifactMetadata(title="PDF Tool", description="Process PDF files"),
        ArtifactMetadata(title="DB Tool", description="Manage databases"),
        ArtifactMetadata(title="File Tool", description="Process documents"),
    ]

    results = await semantic_scorer.score_all("pdf processing", artifacts)

    assert len(results) == 3
    assert all(isinstance(result, tuple) for result in results)
    assert all(len(result) == 2 for result in results)

    # First artifact should have highest score (contains "pdf" and "process")
    artifact, score = results[0]
    assert artifact.title == "PDF Tool"
    assert score is not None
    assert score > 90


@pytest.mark.asyncio
async def test_get_artifact_text(semantic_scorer):
    """Test artifact text extraction."""
    # With all fields
    artifact = ArtifactMetadata(
        title="PDF Tool",
        description="Process PDF files",
        tags=["pdf", "processing"],
    )
    text = semantic_scorer._get_artifact_text(artifact)
    assert "PDF Tool" in text
    assert "Process PDF files" in text
    assert "pdf" in text
    assert "processing" in text

    # With only title
    artifact = ArtifactMetadata(title="Test Tool")
    text = semantic_scorer._get_artifact_text(artifact)
    assert text == "Test Tool"

    # With only description
    artifact = ArtifactMetadata(description="Test description")
    text = semantic_scorer._get_artifact_text(artifact)
    assert text == "Test description"

    # Empty artifact
    artifact = ArtifactMetadata()
    text = semantic_scorer._get_artifact_text(artifact)
    assert text == ""


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    similarity = SemanticScorer._cosine_similarity(v1, v2)
    assert abs(similarity - 1.0) < 1e-6

    # Orthogonal vectors
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    similarity = SemanticScorer._cosine_similarity(v1, v2)
    assert abs(similarity - 0.0) < 1e-6

    # Opposite vectors (should be clamped to 0)
    v1 = [1.0, 0.0, 0.0]
    v2 = [-1.0, 0.0, 0.0]
    similarity = SemanticScorer._cosine_similarity(v1, v2)
    assert similarity == 0.0  # Negative similarity treated as 0

    # Similar but not identical
    v1 = [1.0, 1.0, 0.0]
    v2 = [1.0, 0.5, 0.0]
    similarity = SemanticScorer._cosine_similarity(v1, v2)
    assert 0.8 < similarity < 1.0


def test_cosine_similarity_dimension_mismatch():
    """Test that dimension mismatch raises error."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0]

    with pytest.raises(ValueError, match="dimension mismatch"):
        SemanticScorer._cosine_similarity(v1, v2)


def test_cosine_similarity_zero_vectors():
    """Test cosine similarity with zero vectors."""
    v1 = [0.0, 0.0, 0.0]
    v2 = [1.0, 1.0, 1.0]
    similarity = SemanticScorer._cosine_similarity(v1, v2)
    assert similarity == 0.0


def test_cosine_similarity_empty_vectors():
    """Test cosine similarity with empty vectors."""
    v1 = []
    v2 = []
    similarity = SemanticScorer._cosine_similarity(v1, v2)
    assert similarity == 0.0


@pytest.mark.asyncio
async def test_score_clamping(mock_provider):
    """Test that scores are clamped to min/max range."""
    scorer = SemanticScorer(mock_provider, min_score=20.0, max_score=80.0)

    # High similarity artifact (would score >90 without clamping)
    artifact = ArtifactMetadata(title="PDF Tool", description="Process PDF files")
    score = await scorer.score_artifact("pdf processing", artifact)

    assert score is not None
    assert score <= 80.0  # Clamped to max

    # Low similarity artifact (would score <10 without clamping)
    artifact = ArtifactMetadata(title="Database Tool", description="Manage databases")
    score = await scorer.score_artifact("pdf processing", artifact)

    assert score is not None
    assert score >= 20.0  # Clamped to min


@pytest.mark.asyncio
async def test_acceptance_criteria_pdf_skill():
    """Test acceptance criteria: query 'process PDF' matches pdf skill >90%."""
    provider = MockEmbeddingProvider()
    scorer = SemanticScorer(provider)

    artifact = ArtifactMetadata(
        title="PDF Processor",
        description="Process and extract text from PDF documents",
        tags=["pdf", "document", "processing"],
    )

    score = await scorer.score_artifact("process PDF", artifact)

    # Acceptance criteria: >90% match
    assert score is not None
    assert score > 90, f"Expected >90, got {score}"
