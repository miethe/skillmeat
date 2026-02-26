"""Text similarity utilities for artifact name and description comparison.

This module provides two lightweight, pure-Python text comparison functions
used by the similarity scoring pipeline:

- ``bigram_similarity``: Character bigram Jaccard similarity, optimised for
  short artifact names where surface-form overlap is the dominant signal.
- ``bm25_description_similarity``: Word-level Jaccard similarity with
  stop-word filtering, inspired by BM25 term-frequency weighting, for
  comparing longer description strings where content matters more than length.

Neither function requires external dependencies beyond the Python standard
library.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import FrozenSet

# ---------------------------------------------------------------------------
# Stop-word list (domain-aware)
# ---------------------------------------------------------------------------

_STOP_WORDS: FrozenSet[str] = frozenset(
    {
        # SkillMeat domain terms that appear in almost every artifact description
        "skill",
        "tool",
        "command",
        "agent",
        "hook",
        "mcp",
        "server",
        # Common English function words
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "for",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "just",
        "also",
        "of",
        "in",
        "to",
        "with",
        "on",
        "at",
        "by",
        "from",
        "as",
        "into",
        "about",
        "between",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
    }
)

# ---------------------------------------------------------------------------
# BM25 hyper-parameters
# ---------------------------------------------------------------------------

_BM25_K1: float = 1.2
_BM25_B: float = 0.75


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_name(text: str) -> str:
    """Lowercase and strip hyphens/underscores from *text*."""
    return text.lower().replace("-", "").replace("_", "")


def _char_bigrams(text: str) -> Counter[str]:
    """Return a ``Counter`` of overlapping character bigrams from *text*."""
    if len(text) < 2:
        return Counter()
    return Counter(text[i : i + 2] for i in range(len(text) - 1))


def _tokenize(text: str) -> list[str]:
    """Lowercase-split *text* on whitespace, dropping stop words."""
    return [
        token
        for token in text.lower().split()
        if token and token not in _STOP_WORDS
    ]


def _jaccard(counter_a: Counter[str], counter_b: Counter[str]) -> float:
    """Jaccard coefficient between two multiset counters."""
    if not counter_a and not counter_b:
        return 0.0
    intersection = sum((counter_a & counter_b).values())
    union = sum((counter_a | counter_b).values())
    if union == 0:
        return 0.0
    return intersection / union


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def bigram_similarity(a: str, b: str) -> float:
    """Return character bigram Jaccard similarity between *a* and *b*.

    Both strings are normalised (lowercased, hyphens and underscores removed)
    before bigrams are generated.  This makes the function robust to naming
    convention differences such as ``canvas-design`` vs ``canvas_design``.

    Parameters
    ----------
    a:
        First string (typically an artifact name).
    b:
        Second string (typically an artifact name).

    Returns
    -------
    float
        Jaccard coefficient in ``[0.0, 1.0]``.  Returns ``0.0`` when either
        input is empty or too short to produce bigrams, and ``1.0`` for
        identical (post-normalisation) inputs.

    Examples
    --------
    >>> bigram_similarity("canvas-design", "canvas_design")
    1.0
    >>> bigram_similarity("canvas", "canvas-editor")
    0.625
    >>> bigram_similarity("", "anything")
    0.0
    """
    if not a or not b:
        return 0.0

    norm_a = _normalize_name(a)
    norm_b = _normalize_name(b)

    if norm_a == norm_b:
        return 1.0

    bigrams_a = _char_bigrams(norm_a)
    bigrams_b = _char_bigrams(norm_b)

    return _jaccard(bigrams_a, bigrams_b)


def bm25_description_similarity(desc_a: str, desc_b: str) -> float:
    """Return a BM25-inspired similarity score for two description strings.

    The function uses a two-document BM25 model:

    1. Tokenise both descriptions (lowercase, whitespace split), removing
       domain stop words.
    2. Compute an IDF proxy for each term: terms appearing in *both* documents
       are treated as less discriminative (idf_proxy = log(2 / (df + 1)) where
       df is 0, 1, or 2).
    3. Score *desc_b* against *desc_a* as the query using the standard BM25
       term-frequency saturation formula.
    4. Normalise the raw score by the maximum achievable score (querying a
       document against itself) so the result lies in ``[0.0, 1.0]``.

    Parameters
    ----------
    desc_a:
        First description string (treated as the query document).
    desc_b:
        Second description string (the candidate document to score).

    Returns
    -------
    float
        Similarity in ``[0.0, 1.0]``.  Returns ``0.0`` for empty inputs and
        ``1.0`` for identical (post-tokenisation) inputs.

    Notes
    -----
    The symmetric score is ``max(score(a→b), score(b→a))`` *only* if the
    caller needs symmetry.  The current implementation returns the score of
    *desc_b* given *desc_a* as query, which is intentionally asymmetric and
    matches the standard retrieval use-case (query → candidate).  For a
    symmetric similarity, average both directions.
    """
    if not desc_a or not desc_b:
        return 0.0

    tokens_a = _tokenize(desc_a)
    tokens_b = _tokenize(desc_b)

    if not tokens_a or not tokens_b:
        return 0.0

    # Identical after tokenisation → perfect match
    if tokens_a == tokens_b:
        return 1.0

    tf_a: Counter[str] = Counter(tokens_a)
    tf_b: Counter[str] = Counter(tokens_b)

    len_a = len(tokens_a)
    len_b = len(tokens_b)
    avg_len = (len_a + len_b) / 2.0

    # IDF proxy: df counts across our two-document "corpus"
    # df=2 → term is in both → less discriminative
    # df=1 → term is unique to one document → more discriminative
    vocab: set[str] = set(tf_a.keys()) | set(tf_b.keys())
    idf: dict[str, float] = {}
    for term in vocab:
        df = (1 if term in tf_a else 0) + (1 if term in tf_b else 0)
        # log((N+1)/(df+1)) with N=2; add 1 to avoid log(0)
        idf[term] = math.log((2 + 1) / (df + 1)) + 1.0

    def _bm25_score(query_tf: Counter[str], doc_tf: Counter[str], doc_len: int) -> float:
        """Score *doc_tf* given *query_tf* as a BM25 query."""
        score = 0.0
        k1 = _BM25_K1
        b = _BM25_B
        norm_len = 1 - b + b * (doc_len / avg_len)
        for term, _qf in query_tf.items():
            if term not in doc_tf:
                continue
            tf = doc_tf[term]
            term_score = idf[term] * (tf * (k1 + 1)) / (tf + k1 * norm_len)
            score += term_score
        return score

    raw_score = _bm25_score(tf_a, tf_b, len_b)

    # Normalise: divide by the self-score of desc_a (upper bound for desc_a
    # as a query — a perfect retrieval would score exactly this).
    # Re-compute IDF using only tf_a for fair normalisation.
    idf_self: dict[str, float] = {}
    for term in tf_a:
        # In a single-document corpus df=1 for every term
        idf_self[term] = math.log((2 + 1) / (1 + 1)) + 1.0

    def _bm25_self_score(doc_tf: Counter[str], doc_len: int) -> float:
        score = 0.0
        k1 = _BM25_K1
        b = _BM25_B
        # avg_len of single-document corpus equals doc_len → norm_len = 1.0
        norm_len = 1.0
        for term, tf in doc_tf.items():
            term_score = idf_self.get(term, 0.0) * (tf * (k1 + 1)) / (tf + k1 * norm_len)
            score += term_score
        return score

    max_score = _bm25_self_score(tf_a, len_a)
    if max_score <= 0.0:
        return 0.0

    return min(1.0, raw_score / max_score)
