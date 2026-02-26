"""Local sentence-transformers embedding provider.

This module implements the EmbeddingProvider interface using the
``sentence-transformers`` library with the ``all-MiniLM-L6-v2`` model.
The model runs entirely locally (no API key required) and produces
384-dimensional vectors.

The model is loaded lazily on the first call to ``get_embedding()`` so that
importing this module never blocks the event loop or incurs the ~80 MB
download/load cost at startup.

Usage:
    >>> import asyncio
    >>> from skillmeat.core.scoring.embedder import SentenceTransformerEmbedder
    >>>
    >>> embedder = SentenceTransformerEmbedder()
    >>> if embedder.is_available():
    ...     embedding = asyncio.run(embedder.get_embedding("process PDF files"))
    ...     print(f"Generated {len(embedding)}-dimensional embedding")
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from skillmeat.core.scoring.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)

# Module-level flag so we only attempt the import once per process.
_sentence_transformers_available: Optional[bool] = None


def _check_sentence_transformers() -> bool:
    """Return True if sentence_transformers can be imported."""
    global _sentence_transformers_available
    if _sentence_transformers_available is None:
        try:
            import sentence_transformers  # noqa: F401

            _sentence_transformers_available = True
        except ImportError:
            _sentence_transformers_available = False
    return _sentence_transformers_available


class SentenceTransformerEmbedder(EmbeddingProvider):
    """Embedding provider backed by a local sentence-transformers model.

    Uses ``all-MiniLM-L6-v2`` (approx. 80 MB, 384 dimensions).  The model is
    loaded lazily on the first :meth:`get_embedding` call to avoid blocking the
    event loop or paying the load cost when the embedder is never used.

    CPU inference is offloaded to a ``ThreadPoolExecutor`` so that async
    callers are never blocked.

    Attributes:
        MODEL_NAME:          HuggingFace model identifier.
        EMBEDDING_DIMENSION: Dimensionality of output vectors (384).

    Example:
        >>> embedder = SentenceTransformerEmbedder()
        >>> if embedder.is_available():
        ...     embedding = await embedder.get_embedding("classify images")
        ... else:
        ...     print("sentence-transformers not installed")
    """

    MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    def __init__(self) -> None:
        """Initialize the embedder.

        The underlying sentence-transformers model is NOT loaded here.  It will
        be loaded on the first :meth:`get_embedding` call.
        """
        self._model = None  # loaded lazily
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="st-embed")

    # ------------------------------------------------------------------
    # EmbeddingProvider interface
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True only when ``sentence_transformers`` is importable.

        Returns:
            True if the package is installed and importable, False otherwise.

        Example:
            >>> embedder = SentenceTransformerEmbedder()
            >>> if not embedder.is_available():
            ...     print("Install sentence-transformers to enable semantic search")
        """
        return _check_sentence_transformers()

    def get_embedding_dimension(self) -> int:
        """Return the dimensionality of embeddings produced by this provider.

        Returns:
            384 (``all-MiniLM-L6-v2`` output size).

        Example:
            >>> embedder = SentenceTransformerEmbedder()
            >>> print(embedder.get_embedding_dimension())
            384
        """
        return self.EMBEDDING_DIMENSION

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate a 384-dimensional embedding for *text*.

        The model is loaded on first call (lazy).  Inference is run in a
        thread executor so the calling coroutine is not blocked.

        Args:
            text: Input text to embed.  Empty or whitespace-only strings
                  return ``None``.

        Returns:
            A list of 384 ``float`` values, or ``None`` when the text is
            empty or the provider is unavailable.

        Example:
            >>> embedder = SentenceTransformerEmbedder()
            >>> vec = await embedder.get_embedding("search PDFs")
            >>> if vec:
            ...     print(f"Dimension: {len(vec)}")
        """
        if not text or not text.strip():
            logger.warning("SentenceTransformerEmbedder: empty text, returning None")
            return None

        if not self.is_available():
            logger.warning(
                "SentenceTransformerEmbedder: sentence_transformers not installed; "
                "install with: pip install sentence-transformers"
            )
            return None

        text = text.strip()

        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self._executor, self._encode_sync, text
            )
            return embedding
        except Exception as exc:
            logger.error("SentenceTransformerEmbedder: encoding failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Load the sentence-transformers model (called once, thread-safe via executor)."""
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        logger.info(
            "SentenceTransformerEmbedder: loading model '%s' (first use)…",
            self.MODEL_NAME,
        )
        self._model = SentenceTransformer(self.MODEL_NAME)
        logger.info(
            "SentenceTransformerEmbedder: model '%s' loaded successfully.",
            self.MODEL_NAME,
        )

    def _encode_sync(self, text: str) -> List[float]:
        """Synchronous encode call — runs inside the thread executor.

        Args:
            text: Pre-validated, stripped input text.

        Returns:
            List of float values representing the embedding vector.
        """
        self._load_model()
        # encode() returns a numpy array; convert to plain Python list of float.
        vector = self._model.encode(text, convert_to_numpy=True)
        return [float(v) for v in vector]
