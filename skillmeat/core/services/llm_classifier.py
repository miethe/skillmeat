"""Multi-provider LLM classifier for memory extraction.

Supports Anthropic, OpenAI, Ollama, and any OpenAI-compatible endpoint
for semantic classification of memory candidates. All providers share
a single classification prompt and return structured ClassificationResult
objects.

Providers degrade gracefully: missing SDKs, bad API keys, unreachable
endpoints, and malformed responses all return None per item so the caller
can fall back to heuristic scoring.

Usage:
    >>> from skillmeat.core.services.llm_classifier import get_classifier
    >>> classifier = get_classifier(provider="anthropic")
    >>> if classifier.is_available():
    ...     results = classifier.classify_batch(["Learned that X causes Y"])
    ...     print(results[0].to_dict())
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared classification prompt
# ---------------------------------------------------------------------------

CLASSIFICATION_SYSTEM_PROMPT = """\
You are a memory classifier for a software development knowledge base.
Classify each candidate memory into exactly one type and provide a confidence score.

Types:
- learning: General development insight or lesson learned
- constraint: Hard requirement, limitation, or boundary condition
- gotcha: Subtle pitfall, common mistake, or non-obvious behavior
- decision: Architectural or design decision with rationale
- process: Workflow step, procedure, or operational knowledge
- tool: Tool-specific knowledge, configuration, or usage pattern

Respond with a JSON array. Each element must have:
- "type": one of the types above
- "confidence": float 0.0-1.0 (how confident you are this is a useful memory)
- "reasoning": brief explanation (1 sentence)

Example for 2 candidates:
[
  {"type": "gotcha", "confidence": 0.85, "reasoning": "Identifies a specific pitfall with clear context"},
  {"type": "learning", "confidence": 0.72, "reasoning": "General insight about testing patterns"}
]"""

_VALID_TYPES = frozenset({
    "learning", "constraint", "gotcha", "decision", "process", "tool",
})

# Default batch sizes
DEFAULT_BATCH_SIZE = 15
SMALL_CONTEXT_BATCH_SIZE = 5


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

class ClassificationResult:
    """Result from LLM classification of a memory candidate."""

    def __init__(self, type: str, confidence: float, reasoning: str = ""):
        self.type = type if type in _VALID_TYPES else "learning"
        self.confidence = max(0.0, min(float(confidence), 1.0))
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }

    def __repr__(self) -> str:
        return (
            f"ClassificationResult(type={self.type!r}, "
            f"confidence={self.confidence:.2f}, reasoning={self.reasoning!r})"
        )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_user_prompt(contents: List[str]) -> str:
    """Build the numbered user prompt from a list of candidate texts."""
    lines = [f"{i}. {text}" for i, text in enumerate(contents, start=1)]
    return "Classify these memory candidates:\n\n" + "\n".join(lines)


def _parse_classification_response(
    raw_text: str,
    expected_count: int,
) -> List[Optional[ClassificationResult]]:
    """Parse LLM response text into ClassificationResult objects.

    Handles:
    - Clean JSON arrays
    - Markdown code fences (```json ... ```)
    - Partial / truncated JSON (best-effort salvage)

    Returns a list of length ``expected_count``. Items that could not be
    parsed are ``None``.
    """
    text = raw_text.strip()

    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    parsed: Optional[list] = None

    # Attempt 1: direct JSON parse
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: find first [ ... ] span and parse that
    if parsed is None:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    # Attempt 3: try fixing truncated JSON by closing brackets
    if parsed is None and text.startswith("["):
        for suffix in ("]", "}]"):
            try:
                parsed = json.loads(text + suffix)
                break
            except json.JSONDecodeError:
                continue

    if not isinstance(parsed, list):
        logger.warning("Failed to parse LLM classification response as JSON array")
        return [None] * expected_count

    results: List[Optional[ClassificationResult]] = []
    for i in range(expected_count):
        if i < len(parsed) and isinstance(parsed[i], dict):
            item = parsed[i]
            try:
                results.append(ClassificationResult(
                    type=str(item.get("type", "learning")),
                    confidence=float(item.get("confidence", 0.5)),
                    reasoning=str(item.get("reasoning", "")),
                ))
            except (ValueError, TypeError):
                results.append(None)
        else:
            results.append(None)

    return results


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMClassifier(ABC):
    """Abstract base for LLM-based memory classification."""

    @abstractmethod
    def classify_batch(
        self, contents: List[str], batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> List[Optional[ClassificationResult]]:
        """Classify a batch of candidate texts.

        Implementations must handle splitting into sub-batches if
        ``len(contents) > batch_size``.

        Returns a list the same length as *contents*. Items that fail
        classification are ``None`` so the caller can fall back to
        heuristic scoring.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""


# ---------------------------------------------------------------------------
# Anthropic (Claude Haiku / Sonnet)
# ---------------------------------------------------------------------------

class AnthropicClassifier(LLMClassifier):
    """Anthropic Claude classifier (Haiku/Sonnet).

    Uses the Anthropic Messages API. Requires the ``anthropic`` package
    and a valid ``ANTHROPIC_API_KEY``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None  # Lazy init

    def _get_client(self):
        """Get or create Anthropic client (lazy initialization)."""
        if self._client is None and self.api_key:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning(
                    "anthropic package not installed. Install with: pip install anthropic"
                )
                return None
            except Exception as e:
                logger.warning(f"Failed to init Anthropic client: {e}")
                return None
        return self._client

    def is_available(self) -> bool:
        return self.api_key is not None and self._get_client() is not None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def classify_batch(
        self, contents: List[str], batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> List[Optional[ClassificationResult]]:
        if not contents:
            return []

        client = self._get_client()
        if client is None:
            return [None] * len(contents)

        all_results: List[Optional[ClassificationResult]] = []
        for start in range(0, len(contents), batch_size):
            chunk = contents[start : start + batch_size]
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=CLASSIFICATION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": _build_user_prompt(chunk)}],
                )
                raw_text = response.content[0].text if response.content else ""
                all_results.extend(
                    _parse_classification_response(raw_text, len(chunk))
                )
            except Exception as e:
                logger.warning(f"Anthropic classify_batch failed for chunk: {e}")
                all_results.extend([None] * len(chunk))

        return all_results


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIClassifier(LLMClassifier):
    """OpenAI classifier (GPT-4o-mini, etc.).

    Uses the OpenAI Chat Completions API. Also works with any server
    exposing an OpenAI-compatible ``/v1/chat/completions`` endpoint when
    a custom ``base_url`` is supplied.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI

                kwargs: Dict[str, Any] = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                logger.warning(
                    "openai package not installed. Install with: pip install openai"
                )
                return None
            except Exception as e:
                logger.warning(f"Failed to init OpenAI client: {e}")
                return None
        return self._client

    def is_available(self) -> bool:
        return self.api_key is not None and self._get_client() is not None

    @property
    def provider_name(self) -> str:
        return "openai"

    def _call_chat(self, chunk: List[str]) -> str:
        """Make a single Chat Completions call and return raw text."""
        client = self._get_client()
        if client is None:
            return ""
        response = client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(chunk)},
            ],
        )
        return response.choices[0].message.content or "" if response.choices else ""

    def classify_batch(
        self, contents: List[str], batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> List[Optional[ClassificationResult]]:
        if not contents:
            return []

        client = self._get_client()
        if client is None:
            return [None] * len(contents)

        all_results: List[Optional[ClassificationResult]] = []
        for start in range(0, len(contents), batch_size):
            chunk = contents[start : start + batch_size]
            try:
                raw_text = self._call_chat(chunk)
                all_results.extend(
                    _parse_classification_response(raw_text, len(chunk))
                )
            except Exception as e:
                logger.warning(f"OpenAI classify_batch failed for chunk: {e}")
                all_results.extend([None] * len(chunk))

        return all_results


# ---------------------------------------------------------------------------
# Ollama (local LLMs via OpenAI-compatible /v1 endpoint)
# ---------------------------------------------------------------------------

class OllamaClassifier(LLMClassifier):
    """Ollama local LLM classifier.

    Ollama exposes an OpenAI-compatible endpoint at
    ``http://localhost:11434/v1``.  This classifier uses the ``openai``
    SDK pointed at that endpoint so no extra dependencies are needed.

    Because local models often have smaller context windows, the default
    batch size is reduced to ``SMALL_CONTEXT_BATCH_SIZE``.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        # Ensure the base_url ends with /v1 for OpenAI compat
        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url += "/v1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key="ollama",  # Ollama ignores API key
                    base_url=self.base_url,
                )
            except ImportError:
                logger.warning(
                    "openai package not installed. Install with: pip install openai"
                )
                return None
            except Exception as e:
                logger.warning(f"Failed to init Ollama client: {e}")
                return None
        return self._client

    def is_available(self) -> bool:
        """Check availability by attempting to create the client.

        Does NOT make a network call -- Ollama reachability is verified
        lazily on first ``classify_batch`` call.
        """
        return self._get_client() is not None

    @property
    def provider_name(self) -> str:
        return "ollama"

    def classify_batch(
        self, contents: List[str], batch_size: int = SMALL_CONTEXT_BATCH_SIZE,
    ) -> List[Optional[ClassificationResult]]:
        if not contents:
            return []

        client = self._get_client()
        if client is None:
            return [None] * len(contents)

        all_results: List[Optional[ClassificationResult]] = []
        for start in range(0, len(contents), batch_size):
            chunk = contents[start : start + batch_size]
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    max_tokens=1024,
                    messages=[
                        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": _build_user_prompt(chunk)},
                    ],
                )
                raw_text = (
                    response.choices[0].message.content or ""
                    if response.choices
                    else ""
                )
                all_results.extend(
                    _parse_classification_response(raw_text, len(chunk))
                )
            except Exception as e:
                logger.warning(f"Ollama classify_batch failed for chunk: {e}")
                all_results.extend([None] * len(chunk))

        return all_results


# ---------------------------------------------------------------------------
# Generic OpenAI-compatible endpoint
# ---------------------------------------------------------------------------

class OpenAICompatibleClassifier(LLMClassifier):
    """Generic OpenAI-compatible endpoint classifier.

    Works with LM Studio, text-generation-webui, vLLM, and any other
    server that implements the ``/v1/chat/completions`` contract.

    Many local servers do not require a real API key -- pass any non-empty
    string (the default ``"not-needed"``).
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "not-needed",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                logger.warning(
                    "openai package not installed. Install with: pip install openai"
                )
                return None
            except Exception as e:
                logger.warning(f"Failed to init OpenAI-compatible client: {e}")
                return None
        return self._client

    def is_available(self) -> bool:
        return self._get_client() is not None

    @property
    def provider_name(self) -> str:
        return "openai-compatible"

    def classify_batch(
        self, contents: List[str], batch_size: int = SMALL_CONTEXT_BATCH_SIZE,
    ) -> List[Optional[ClassificationResult]]:
        if not contents:
            return []

        client = self._get_client()
        if client is None:
            return [None] * len(contents)

        all_results: List[Optional[ClassificationResult]] = []
        for start in range(0, len(contents), batch_size):
            chunk = contents[start : start + batch_size]
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    max_tokens=1024,
                    messages=[
                        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": _build_user_prompt(chunk)},
                    ],
                )
                raw_text = (
                    response.choices[0].message.content or ""
                    if response.choices
                    else ""
                )
                all_results.extend(
                    _parse_classification_response(raw_text, len(chunk))
                )
            except Exception as e:
                logger.warning(
                    f"OpenAI-compatible classify_batch failed for chunk: {e}"
                )
                all_results.extend([None] * len(chunk))

        return all_results


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_PROVIDER_MAP = {
    "anthropic": "AnthropicClassifier",
    "openai": "OpenAIClassifier",
    "ollama": "OllamaClassifier",
    "openai-compatible": "OpenAICompatibleClassifier",
}


def get_classifier(
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMClassifier:
    """Factory function to create the appropriate classifier.

    Args:
        provider: One of ``"anthropic"``, ``"openai"``, ``"ollama"``,
            ``"openai-compatible"``.
        model: Model name (provider-specific defaults if not set).
        api_key: API key (uses env vars if not set for anthropic/openai).
        base_url: Base URL for API. Required for ``ollama`` and
            ``openai-compatible`` providers.

    Returns:
        Configured LLMClassifier instance.

    Raises:
        ValueError: If *provider* is not one of the supported values.
    """
    provider = provider.lower().strip()

    if provider not in _PROVIDER_MAP:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Must be one of: {sorted(_PROVIDER_MAP.keys())}"
        )

    kwargs: Dict[str, Any] = {}
    if api_key is not None:
        kwargs["api_key"] = api_key
    if model is not None:
        kwargs["model"] = model

    if provider == "anthropic":
        return AnthropicClassifier(**kwargs)

    if provider == "openai":
        if base_url is not None:
            kwargs["base_url"] = base_url
        return OpenAIClassifier(**kwargs)

    if provider == "ollama":
        if base_url is not None:
            kwargs["base_url"] = base_url
        # Ollama doesn't use api_key
        kwargs.pop("api_key", None)
        return OllamaClassifier(**kwargs)

    # openai-compatible
    if base_url is None:
        raise ValueError("base_url is required for openai-compatible provider")
    if model is None:
        raise ValueError("model is required for openai-compatible provider")
    kwargs["base_url"] = base_url
    return OpenAICompatibleClassifier(**kwargs)
