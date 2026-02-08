"""Tests for LLM classifier module (MEX-3.5).

Tests all components of the multi-provider LLM classification system:
- ClassificationResult data structure
- Response parsing (JSON, markdown, truncated)
- Retry logic with exponential backoff
- Usage statistics tracking
- All 4 provider implementations (Anthropic, OpenAI, Ollama, OpenAI-compatible)
- Factory function

All tests use mocking to avoid real API calls.
"""

import json
import pytest
from unittest.mock import MagicMock, Mock, patch

from skillmeat.core.services.llm_classifier import (
    ClassificationResult,
    LLMUsageStats,
    AnthropicClassifier,
    OpenAIClassifier,
    OllamaClassifier,
    OpenAICompatibleClassifier,
    get_classifier,
    _parse_classification_response,
    _retry_with_backoff,
    _is_rate_limit_error,
    _is_server_error,
    SMALL_CONTEXT_BATCH_SIZE,
    DEFAULT_BATCH_SIZE,
)


# =============================================================================
# ClassificationResult Tests
# =============================================================================


class TestClassificationResult:
    def test_valid_type(self):
        """Valid types are accepted."""
        result = ClassificationResult(
            type="learning",
            confidence=0.85,
            reasoning="This is a learning insight"
        )
        assert result.type == "learning"
        assert result.confidence == 0.85
        assert result.reasoning == "This is a learning insight"

    def test_invalid_type_falls_back_to_learning(self):
        """Invalid types fallback to 'learning'."""
        result = ClassificationResult(
            type="invalid_type",
            confidence=0.75,
            reasoning="Test"
        )
        assert result.type == "learning"

    def test_confidence_clamping(self):
        """Confidence is clamped to [0.0, 1.0]."""
        # Test upper bound
        result1 = ClassificationResult(type="gotcha", confidence=1.5, reasoning="")
        assert result1.confidence == 1.0

        # Test lower bound
        result2 = ClassificationResult(type="gotcha", confidence=-0.5, reasoning="")
        assert result2.confidence == 0.0

        # Test valid range
        result3 = ClassificationResult(type="gotcha", confidence=0.85, reasoning="")
        assert result3.confidence == 0.85

    def test_to_dict(self):
        """to_dict returns correct structure."""
        result = ClassificationResult(
            type="constraint",
            confidence=0.92,
            reasoning="Clear constraint identified"
        )
        data = result.to_dict()
        assert data == {
            "type": "constraint",
            "confidence": 0.92,
            "reasoning": "Clear constraint identified",
        }

    def test_repr(self):
        """__repr__ returns useful debug string."""
        result = ClassificationResult(
            type="decision",
            confidence=0.88,
            reasoning="Design choice"
        )
        repr_str = repr(result)
        assert "ClassificationResult" in repr_str
        assert "decision" in repr_str
        assert "0.88" in repr_str


# =============================================================================
# Response Parsing Tests
# =============================================================================


class TestParseClassificationResponse:
    def test_valid_json_array(self):
        """Clean JSON array parses correctly."""
        response = json.dumps([
            {"type": "learning", "confidence": 0.85, "reasoning": "test1"},
            {"type": "gotcha", "confidence": 0.92, "reasoning": "test2"},
        ])
        results = _parse_classification_response(response, expected_count=2)
        assert len(results) == 2
        assert results[0].type == "learning"
        assert results[0].confidence == 0.85
        assert results[1].type == "gotcha"
        assert results[1].confidence == 0.92

    def test_markdown_code_fences(self):
        """JSON with markdown code fences is handled."""
        response = """```json
[
  {"type": "constraint", "confidence": 0.78, "reasoning": "test"}
]
```"""
        results = _parse_classification_response(response, expected_count=1)
        assert len(results) == 1
        assert results[0].type == "constraint"
        assert results[0].confidence == 0.78

    def test_truncated_json_repaired(self):
        """Truncated JSON is salvaged where possible."""
        # Missing closing bracket
        response = '[{"type": "learning", "confidence": 0.7, "reasoning": "test"'
        results = _parse_classification_response(response, expected_count=1)
        assert len(results) == 1
        assert results[0].type == "learning"

        # Missing closing brace and bracket
        response2 = '[{"type": "gotcha", "confidence": 0.8, "reasoning": "test"'
        results2 = _parse_classification_response(response2, expected_count=1)
        assert len(results2) == 1
        assert results2[0].type == "gotcha"

    def test_partial_results(self):
        """If fewer results than expected, remaining are None."""
        response = json.dumps([
            {"type": "decision", "confidence": 0.9, "reasoning": "test"}
        ])
        results = _parse_classification_response(response, expected_count=3)
        assert len(results) == 3
        assert results[0].type == "decision"
        assert results[1] is None
        assert results[2] is None

    def test_completely_invalid_json(self):
        """Completely invalid JSON returns all None."""
        response = "This is not JSON at all!"
        results = _parse_classification_response(response, expected_count=2)
        assert len(results) == 2
        assert all(r is None for r in results)

    def test_non_array_json(self):
        """JSON object (not array) returns all None."""
        response = json.dumps({"type": "learning", "confidence": 0.8})
        results = _parse_classification_response(response, expected_count=1)
        assert len(results) == 1
        assert results[0] is None

    def test_invalid_item_structure(self):
        """Items missing required fields are returned as None."""
        response = json.dumps([
            {"type": "learning"},  # Missing confidence
            {"confidence": 0.8},   # Missing type
            {"type": "gotcha", "confidence": "invalid"},  # Invalid confidence type
        ])
        results = _parse_classification_response(response, expected_count=3)
        # All items have issues but may salvage some defaults
        assert len(results) == 3


# =============================================================================
# Retry Logic Tests
# =============================================================================


class TestRetryWithBackoff:
    def test_success_no_retry(self):
        """Successful call doesn't retry."""
        mock_fn = Mock(return_value="success")
        result = _retry_with_backoff(mock_fn, max_retries=3)
        assert result == "success"
        assert mock_fn.call_count == 1

    def test_rate_limit_retries(self):
        """Rate limit (429) triggers retry."""
        # Mock a rate limit error with status_code
        error = Exception("Rate limit exceeded")
        error.status_code = 429

        mock_fn = Mock(side_effect=[error, error, "success"])

        with patch('time.sleep'):  # Mock sleep to avoid delay
            result = _retry_with_backoff(mock_fn, max_retries=3)

        assert result == "success"
        assert mock_fn.call_count == 3

    def test_server_error_retries(self):
        """Server error (5xx) triggers retry."""
        error = Exception("Internal server error")
        error.status_code = 500

        mock_fn = Mock(side_effect=[error, "success"])

        with patch('time.sleep'):
            result = _retry_with_backoff(mock_fn, max_retries=3)

        assert result == "success"
        assert mock_fn.call_count == 2

    def test_auth_error_no_retry(self):
        """Auth error (401) does NOT retry."""
        error = Exception("Unauthorized")
        error.status_code = 401

        mock_fn = Mock(side_effect=error)

        with pytest.raises(Exception, match="Unauthorized"):
            _retry_with_backoff(mock_fn, max_retries=3)

        assert mock_fn.call_count == 1

    def test_max_retries_exceeded(self):
        """After max retries, raises the exception."""
        error = Exception("Server error")
        error.status_code = 503

        mock_fn = Mock(side_effect=error)

        with patch('time.sleep'):
            with pytest.raises(Exception, match="Server error"):
                _retry_with_backoff(mock_fn, max_retries=2)

        assert mock_fn.call_count == 3  # Initial + 2 retries

    def test_exponential_delay(self):
        """Delay increases exponentially (use mock time.sleep)."""
        error = Exception("Server error")
        error.status_code = 500

        mock_fn = Mock(side_effect=[error, error, error, "success"])

        with patch('time.sleep') as mock_sleep:
            result = _retry_with_backoff(
                mock_fn,
                max_retries=3,
                base_delay=2.0,
                max_delay=30.0
            )

        assert result == "success"
        # Verify exponential backoff: 2, 4, 8
        assert mock_sleep.call_count == 3
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays[0] == 2.0   # 2 * 2^0
        assert delays[1] == 4.0   # 2 * 2^1
        assert delays[2] == 8.0   # 2 * 2^2


class TestErrorDetection:
    def test_is_rate_limit_error(self):
        """Rate limit detection works for various formats."""
        # Status code 429
        error1 = Exception("Too many requests")
        error1.status_code = 429
        assert _is_rate_limit_error(error1)

        # Exception name contains RateLimit
        class RateLimitError(Exception):
            pass
        error2 = RateLimitError("Rate limited")
        assert _is_rate_limit_error(error2)

        # Not a rate limit error
        error3 = Exception("Other error")
        assert not _is_rate_limit_error(error3)

    def test_is_server_error(self):
        """Server error detection works for various formats."""
        # Status code 5xx
        for status in [500, 502, 503, 504]:
            error = Exception("Server error")
            error.status_code = status
            assert _is_server_error(error)

        # Exception name contains InternalServer
        class InternalServerError(Exception):
            pass
        error2 = InternalServerError("Server failed")
        assert _is_server_error(error2)

        # Not a server error
        error3 = Exception("Client error")
        error3.status_code = 400
        assert not _is_server_error(error3)


# =============================================================================
# Usage Stats Tests
# =============================================================================


class TestLLMUsageStats:
    def test_initial_state(self):
        """Fresh stats are all zeros."""
        stats = LLMUsageStats()
        assert stats.total_calls == 0
        assert stats.total_input_tokens == 0
        assert stats.total_output_tokens == 0
        assert stats.total_candidates == 0
        assert stats.failed_calls == 0

    def test_record_call(self):
        """Call recording accumulates correctly."""
        stats = LLMUsageStats()
        stats.record_call(input_tokens=100, output_tokens=50, candidates=5)
        stats.record_call(input_tokens=200, output_tokens=75, candidates=10)

        assert stats.total_calls == 2
        assert stats.total_input_tokens == 300
        assert stats.total_output_tokens == 125
        assert stats.total_candidates == 15

    def test_record_failure(self):
        """Failure recording works."""
        stats = LLMUsageStats()
        stats.record_failure()
        stats.record_failure()
        assert stats.failed_calls == 2

    def test_estimated_cost_anthropic(self):
        """Anthropic Haiku cost calculation is correct."""
        stats = LLMUsageStats()
        stats.record_call(input_tokens=1_000_000, output_tokens=1_000_000, candidates=100)

        # Claude Haiku: $0.80 input, $4.00 output per 1M tokens
        cost = stats.estimated_cost("anthropic", "claude-haiku-4-5-20251001")
        assert cost == pytest.approx(4.80, rel=0.01)

    def test_estimated_cost_openai(self):
        """OpenAI GPT-4o-mini cost calculation is correct."""
        stats = LLMUsageStats()
        stats.record_call(input_tokens=1_000_000, output_tokens=1_000_000, candidates=100)

        # GPT-4o-mini: $0.15 input, $0.60 output per 1M tokens
        cost = stats.estimated_cost("openai", "gpt-4o-mini")
        assert cost == pytest.approx(0.75, rel=0.01)

    def test_estimated_cost_ollama_free(self):
        """Ollama returns $0.00."""
        stats = LLMUsageStats()
        stats.record_call(input_tokens=1_000_000, output_tokens=1_000_000, candidates=100)

        cost = stats.estimated_cost("ollama", "llama3.2")
        assert cost == 0.0

    def test_to_dict(self):
        """Dict format includes all fields."""
        stats = LLMUsageStats()
        stats.record_call(input_tokens=100, output_tokens=50, candidates=5)
        stats.record_failure()

        data = stats.to_dict()
        assert data == {
            "total_calls": 1,
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_candidates": 5,
            "failed_calls": 1,
        }

    def test_summary_with_cost(self):
        """Summary includes est_cost for paid providers."""
        stats = LLMUsageStats()
        stats.record_call(input_tokens=100_000, output_tokens=50_000, candidates=5)

        summary = stats.summary(provider="anthropic", model="claude-haiku-4-5-20251001")
        assert "est_cost=" in summary
        assert "1 calls" in summary
        assert "5 candidates" in summary

    def test_summary_without_cost(self):
        """Summary omits cost for free providers."""
        stats = LLMUsageStats()
        stats.record_call(input_tokens=100_000, output_tokens=50_000, candidates=5)

        summary = stats.summary(provider="ollama", model="llama3.2")
        assert "est_cost=" not in summary
        assert "1 calls" in summary


# =============================================================================
# Anthropic Classifier Tests
# =============================================================================


class TestAnthropicClassifier:
    def test_lazy_init(self):
        """Client is None until first use."""
        classifier = AnthropicClassifier(api_key="test-key")
        assert classifier._client is None

    def test_no_api_key_unavailable(self):
        """No API key → is_available() returns False."""
        with patch.dict('os.environ', {}, clear=True):
            classifier = AnthropicClassifier(api_key=None)
            assert not classifier.is_available()

    def test_classify_batch_with_mock(self):
        """Mock Anthropic API response and verify classification."""
        classifier = AnthropicClassifier(api_key="test-key")

        # Mock the Anthropic response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps([
            {"type": "learning", "confidence": 0.85, "reasoning": "test learning"}
        ])
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_response

            results = classifier.classify_batch(["Test candidate text"])

        assert len(results) == 1
        assert results[0].type == "learning"
        assert results[0].confidence == 0.85

    def test_classify_batch_empty(self):
        """Empty input returns empty list."""
        classifier = AnthropicClassifier(api_key="test-key")
        results = classifier.classify_batch([])
        assert results == []

    def test_classify_batch_api_failure(self):
        """API failure returns None for all items."""
        classifier = AnthropicClassifier(api_key="test-key")

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = Exception("API error")

            results = classifier.classify_batch(["Test candidate"])

        assert len(results) == 1
        assert results[0] is None

    def test_usage_stats_recorded(self):
        """Token usage is tracked after API call."""
        classifier = AnthropicClassifier(api_key="test-key")

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps([
            {"type": "gotcha", "confidence": 0.9, "reasoning": "test"}
        ])
        mock_response.usage = MagicMock(input_tokens=200, output_tokens=75)

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_response

            classifier.classify_batch(["Test"])

        assert classifier.usage_stats.total_calls == 1
        assert classifier.usage_stats.total_input_tokens == 200
        assert classifier.usage_stats.total_output_tokens == 75

    def test_batch_splitting(self):
        """Large batches are split correctly."""
        classifier = AnthropicClassifier(api_key="test-key")

        # Create 20 candidates (exceeds default batch size of 15)
        candidates = [f"Test {i}" for i in range(20)]

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        # Return appropriate JSON for each batch
        mock_response.content[0].text = json.dumps([
            {"type": "learning", "confidence": 0.8, "reasoning": "test"}
            for _ in range(15)
        ])
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Second batch has 5 items
                mock_response.content[0].text = json.dumps([
                    {"type": "learning", "confidence": 0.8, "reasoning": "test"}
                    for _ in range(5)
                ])
            return mock_response

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = side_effect

            results = classifier.classify_batch(candidates, batch_size=15)

        assert len(results) == 20
        assert call_count == 2  # Two batches


# =============================================================================
# OpenAI Classifier Tests
# =============================================================================


class TestOpenAIClassifier:
    def test_lazy_init(self):
        """Client is None until first use."""
        classifier = OpenAIClassifier(api_key="test-key")
        assert classifier._client is None

    def test_classify_batch_with_mock(self):
        """Mock OpenAI API response and verify classification."""
        classifier = OpenAIClassifier(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps([
            {"type": "gotcha", "confidence": 0.9, "reasoning": "test gotcha"}
        ])
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            results = classifier.classify_batch(["Test candidate"])

        assert len(results) == 1
        assert results[0].type == "gotcha"
        assert results[0].confidence == 0.9

    def test_custom_base_url(self):
        """Custom base URL is passed to client."""
        classifier = OpenAIClassifier(
            api_key="test-key",
            base_url="https://custom.api.com/v1"
        )

        # Patch at the import location inside the method
        with patch('builtins.__import__', side_effect=ImportError):
            # This will make the client unavailable
            client = classifier._get_client()
            assert client is None

        # Test that base_url is stored correctly
        assert classifier.base_url == "https://custom.api.com/v1"
        assert classifier.api_key == "test-key"

    def test_usage_stats_recorded(self):
        """Token usage is tracked correctly."""
        classifier = OpenAIClassifier(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps([
            {"type": "constraint", "confidence": 0.88, "reasoning": "test"}
        ])
        mock_response.usage = MagicMock(prompt_tokens=150, completion_tokens=60)

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            classifier.classify_batch(["Test"])

        assert classifier.usage_stats.total_input_tokens == 150
        assert classifier.usage_stats.total_output_tokens == 60


# =============================================================================
# Ollama Classifier Tests
# =============================================================================


class TestOllamaClassifier:
    def test_base_url_adds_v1(self):
        """Base URL gets /v1 appended for OpenAI compat."""
        classifier = OllamaClassifier(base_url="http://localhost:11434")
        assert classifier.base_url == "http://localhost:11434/v1"

        # Already has /v1
        classifier2 = OllamaClassifier(base_url="http://localhost:11434/v1")
        assert classifier2.base_url == "http://localhost:11434/v1"

    def test_no_api_key_needed(self):
        """Ollama doesn't require API key to be available."""
        classifier = OllamaClassifier()

        # Mock the _get_client to return a mock client
        with patch.object(classifier, '_get_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()
            assert classifier.is_available()

    def test_small_batch_size(self):
        """Default batch size is SMALL_CONTEXT_BATCH_SIZE (5)."""
        classifier = OllamaClassifier()

        # Create 10 candidates
        candidates = [f"Test {i}" for i in range(10)]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps([
            {"type": "learning", "confidence": 0.8, "reasoning": "test"}
            for _ in range(5)
        ])
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            # Don't override batch_size, should use default SMALL_CONTEXT_BATCH_SIZE
            results = classifier.classify_batch(candidates)

        # Should make 2 calls (10 / 5)
        assert len(results) == 10
        assert mock_client.return_value.chat.completions.create.call_count == 2


# =============================================================================
# OpenAI-Compatible Classifier Tests
# =============================================================================


class TestOpenAICompatibleClassifier:
    def test_custom_api_key(self):
        """Custom API key is used."""
        classifier = OpenAICompatibleClassifier(
            base_url="http://localhost:8080",
            model="custom-model",
            api_key="custom-key"
        )
        assert classifier.api_key == "custom-key"

    def test_default_api_key(self):
        """Default API key is 'not-needed'."""
        classifier = OpenAICompatibleClassifier(
            base_url="http://localhost:8080",
            model="custom-model"
        )
        assert classifier.api_key == "not-needed"

    def test_base_url_required(self):
        """OpenAI-compatible requires base_url."""
        classifier = OpenAICompatibleClassifier(
            base_url="http://custom.server:8000/v1",
            model="local-model"
        )
        assert classifier.base_url == "http://custom.server:8000/v1"

    def test_small_batch_size(self):
        """Uses small batch size by default."""
        classifier = OpenAICompatibleClassifier(
            base_url="http://localhost:8080",
            model="custom"
        )

        # Create 10 candidates
        candidates = [f"Test {i}" for i in range(10)]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps([
            {"type": "learning", "confidence": 0.8, "reasoning": "test"}
            for _ in range(SMALL_CONTEXT_BATCH_SIZE)
        ])
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        with patch.object(classifier, '_get_client') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response

            results = classifier.classify_batch(candidates)

        # Should split into batches of SMALL_CONTEXT_BATCH_SIZE
        assert len(results) == 10


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestGetClassifier:
    def test_anthropic_default(self):
        """Default provider is anthropic."""
        classifier = get_classifier()
        assert isinstance(classifier, AnthropicClassifier)

    def test_openai(self):
        """OpenAI provider returns OpenAIClassifier."""
        classifier = get_classifier(provider="openai")
        assert isinstance(classifier, OpenAIClassifier)

    def test_ollama(self):
        """Ollama provider returns OllamaClassifier."""
        classifier = get_classifier(provider="ollama")
        assert isinstance(classifier, OllamaClassifier)

    def test_openai_compatible_requires_base_url(self):
        """OpenAI-compatible raises ValueError without base_url."""
        with pytest.raises(ValueError, match="base_url is required"):
            get_classifier(provider="openai-compatible", model="custom")

    def test_openai_compatible_requires_model(self):
        """OpenAI-compatible raises ValueError without model."""
        with pytest.raises(ValueError, match="model is required"):
            get_classifier(
                provider="openai-compatible",
                base_url="http://localhost:8080"
            )

    def test_unknown_provider_raises(self):
        """Unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            get_classifier(provider="unknown-provider")

    def test_case_insensitive_provider(self):
        """Provider names are case-insensitive."""
        classifier1 = get_classifier(provider="ANTHROPIC")
        assert isinstance(classifier1, AnthropicClassifier)

        classifier2 = get_classifier(provider="OpenAI")
        assert isinstance(classifier2, OpenAIClassifier)

    def test_custom_model(self):
        """Custom model is passed to classifier."""
        classifier = get_classifier(provider="anthropic", model="claude-sonnet-4-5-20250929")
        assert classifier.model == "claude-sonnet-4-5-20250929"

    def test_custom_api_key(self):
        """Custom API key is passed to classifier."""
        classifier = get_classifier(provider="anthropic", api_key="custom-key")
        assert classifier.api_key == "custom-key"

    def test_openai_compatible_full_config(self):
        """OpenAI-compatible with full config works."""
        classifier = get_classifier(
            provider="openai-compatible",
            model="local-model",
            base_url="http://localhost:8080/v1",
            api_key="custom-key"
        )
        assert isinstance(classifier, OpenAICompatibleClassifier)
        assert classifier.model == "local-model"
        assert classifier.base_url == "http://localhost:8080/v1"
        assert classifier.api_key == "custom-key"
