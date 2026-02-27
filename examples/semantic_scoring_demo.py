"""Demo of semantic scoring with embeddings.

This example demonstrates how to use the SemanticScorer with SentenceTransformerEmbedder
to compute semantic similarity between queries and artifacts.

Note: This requires the sentence-transformers package to be installed.
      Without it, the scorer will gracefully degrade and return None,
      allowing fallback to keyword-based matching.

Usage:
    python examples/semantic_scoring_demo.py
"""

import asyncio
import os

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring import SentenceTransformerEmbedder, SemanticScorer


async def main():
    """Demonstrate semantic scoring."""
    print("=" * 60)
    print("Semantic Scoring Demo")
    print("=" * 60)

    # Check if API key is available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nNote: ANTHROPIC_API_KEY not set.")
        print("Semantic scoring will be unavailable and return None.")
        print("This allows graceful fallback to keyword matching.\n")

    # Initialize embedder and scorer
    embedder = SentenceTransformerEmbedder()
    scorer = SemanticScorer(embedder)

    print(f"Embedder available: {embedder.is_available()}")
    print(f"Scorer available: {scorer.is_available()}")
    print()

    # Create sample artifacts
    artifacts = [
        ArtifactMetadata(
            title="PDF Processor",
            description="Extract and process text from PDF documents",
            tags=["pdf", "document", "processing", "text-extraction"],
        ),
        ArtifactMetadata(
            title="Database Manager",
            description="Query and manage SQL databases",
            tags=["database", "sql", "query", "management"],
        ),
        ArtifactMetadata(
            title="Document Converter",
            description="Convert documents between formats (PDF, DOCX, HTML)",
            tags=["conversion", "documents", "pdf", "docx"],
        ),
        ArtifactMetadata(
            title="Web Scraper",
            description="Scrape and extract data from websites",
            tags=["web", "scraping", "extraction", "html"],
        ),
    ]

    # Test query
    query = "process PDF files"
    print(f"Query: '{query}'\n")

    # Score all artifacts
    print("Scoring artifacts...")
    results = await scorer.score_all(query, artifacts)

    # Display results
    print("\nResults:")
    print("-" * 60)
    for artifact, score in results:
        if score is not None:
            print(f"{artifact.title:25s} | Score: {score:5.1f}%")
        else:
            print(f"{artifact.title:25s} | Score: N/A (embeddings unavailable)")

    # Find best match
    scored_results = [(art, score) for art, score in results if score is not None]
    if scored_results:
        best_match, best_score = max(scored_results, key=lambda x: x[1])
        print("\n" + "=" * 60)
        print(f"Best match: {best_match.title} ({best_score:.1f}%)")
        print(f"Description: {best_match.description}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("No semantic scores available.")
        print("Fallback to keyword-based matching would be used.")
        print("=" * 60)

    # Demonstrate graceful degradation
    print("\nGraceful Degradation Test:")
    print("-" * 60)
    # AnthropicEmbedder always returns is_available=False (no Anthropic embedding API)
    from skillmeat.core.scoring import AnthropicEmbedder
    unavailable_embedder = AnthropicEmbedder()  # Always unavailable
    unavailable_scorer = SemanticScorer(unavailable_embedder)

    score = await unavailable_scorer.score_artifact(query, artifacts[0])
    print(f"Score with unavailable embedder: {score}")
    print("Expected: None (allows fallback to keyword matching)")


if __name__ == "__main__":
    asyncio.run(main())
