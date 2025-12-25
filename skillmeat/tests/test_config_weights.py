"""Tests for score weight configuration.

This module tests the weight customization feature that allows users to
configure scoring weights via CLI commands and config files.
"""

import pytest
from pathlib import Path

from skillmeat.config import ConfigManager
from skillmeat.cli import parse_score_weights
from skillmeat.core.scoring.score_calculator import ScoreCalculator, DEFAULT_WEIGHTS
from skillmeat.core.scoring.match_analyzer import MatchAnalyzer


class TestParseScoreWeights:
    """Tests for parse_score_weights helper function."""

    def test_parse_valid_weights(self):
        """Parse valid weight string."""
        result = parse_score_weights("trust=0.3,quality=0.3,match=0.4")
        assert result == {"trust": 0.3, "quality": 0.3, "match": 0.4}

    def test_parse_weights_with_spaces(self):
        """Parse weights with extra spaces."""
        result = parse_score_weights(" trust = 0.25 , quality = 0.25 , match = 0.50 ")
        assert result == {"trust": 0.25, "quality": 0.25, "match": 0.50}

    def test_parse_default_weights(self):
        """Parse default weight values."""
        result = parse_score_weights("trust=0.25,quality=0.25,match=0.50")
        assert result == DEFAULT_WEIGHTS

    def test_parse_invalid_format_missing_equals(self):
        """Reject invalid format without equals sign."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_score_weights("trust:0.3,quality:0.3,match:0.4")

    def test_parse_invalid_format_missing_comma(self):
        """Reject invalid format with missing commas."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_score_weights("trust=0.3 quality=0.3 match=0.4")

    def test_parse_non_numeric(self):
        """Reject non-numeric values."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_score_weights("trust=abc,quality=0.3,match=0.4")

    def test_parse_empty_string(self):
        """Reject empty string."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_score_weights("")

    def test_parse_incomplete_pairs(self):
        """Reject incomplete key-value pairs."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_score_weights("trust=0.3,quality,match=0.4")


class TestConfigManagerScoreWeights:
    """Tests for ConfigManager weight methods."""

    def test_set_valid_weights(self, tmp_path):
        """Set valid score weights in config."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {"trust": 0.3, "quality": 0.3, "match": 0.4}
        config_mgr.set_score_weights(weights)

        # Verify saved
        loaded = config_mgr.get_score_weights()
        assert loaded == weights

    def test_set_weights_with_floats(self, tmp_path):
        """Set weights with various float values."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {"trust": 0.123, "quality": 0.456, "match": 0.421}
        config_mgr.set_score_weights(weights)

        loaded = config_mgr.get_score_weights()
        assert loaded == weights

    def test_set_weights_invalid_sum_too_high(self, tmp_path):
        """Reject weights summing above 1.0."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {"trust": 0.5, "quality": 0.5, "match": 0.5}  # Sum = 1.5

        with pytest.raises(ValueError, match="must sum to 1.0"):
            config_mgr.set_score_weights(weights)

    def test_set_weights_invalid_sum_too_low(self, tmp_path):
        """Reject weights summing below 1.0."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {"trust": 0.2, "quality": 0.2, "match": 0.2}  # Sum = 0.6

        with pytest.raises(ValueError, match="must sum to 1.0"):
            config_mgr.set_score_weights(weights)

    def test_set_weights_missing_key(self, tmp_path):
        """Reject weights missing required keys."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {"trust": 0.5, "quality": 0.5}  # Missing 'match'

        with pytest.raises(ValueError, match="Expected keys"):
            config_mgr.set_score_weights(weights)

    def test_set_weights_extra_key(self, tmp_path):
        """Reject weights with extra keys."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {
            "trust": 0.25,
            "quality": 0.25,
            "match": 0.25,
            "extra": 0.25,
        }

        with pytest.raises(ValueError, match="Expected keys"):
            config_mgr.set_score_weights(weights)

    def test_set_weights_negative_value(self, tmp_path):
        """Reject weights with negative values."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {"trust": -0.1, "quality": 0.6, "match": 0.5}

        with pytest.raises(ValueError, match="must be 0-1"):
            config_mgr.set_score_weights(weights)

    def test_set_weights_value_above_one(self, tmp_path):
        """Reject weights with values above 1.0."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = {"trust": 1.5, "quality": -0.3, "match": -0.2}

        with pytest.raises(ValueError, match="must be 0-1"):
            config_mgr.set_score_weights(weights)

    def test_get_weights_default(self, tmp_path):
        """Return default weights when not configured."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        weights = config_mgr.get_score_weights()

        # Should return DEFAULT_WEIGHTS
        assert weights == DEFAULT_WEIGHTS
        assert sum(weights.values()) == 1.0

    def test_get_weights_after_set(self, tmp_path):
        """Get weights after setting custom values."""
        config_mgr = ConfigManager(config_dir=tmp_path)
        custom_weights = {"trust": 0.4, "quality": 0.3, "match": 0.3}

        config_mgr.set_score_weights(custom_weights)
        retrieved = config_mgr.get_score_weights()

        assert retrieved == custom_weights

    def test_weights_persist_across_instances(self, tmp_path):
        """Weights persist when creating new ConfigManager instance."""
        # Set weights with first instance
        config_mgr1 = ConfigManager(config_dir=tmp_path)
        custom_weights = {"trust": 0.5, "quality": 0.2, "match": 0.3}
        config_mgr1.set_score_weights(custom_weights)

        # Load with new instance
        config_mgr2 = ConfigManager(config_dir=tmp_path)
        retrieved = config_mgr2.get_score_weights()

        assert retrieved == custom_weights


class TestScoreCalculatorWeightLoading:
    """Tests for ScoreCalculator weight loading from config."""

    def test_calculator_uses_default_weights(self, tmp_path, monkeypatch):
        """ScoreCalculator uses default weights when config not set."""
        # Use clean config dir to avoid picking up real config
        def mock_config_manager(*args, **kwargs):
            return ConfigManager(config_dir=tmp_path)

        monkeypatch.setattr(
            "skillmeat.config.ConfigManager",
            mock_config_manager,
        )

        calc = ScoreCalculator(
            match_analyzer=MatchAnalyzer(),
        )

        assert calc.weights == DEFAULT_WEIGHTS

    def test_calculator_explicit_weights_override(self):
        """Explicit weights override config defaults."""
        explicit_weights = {"trust": 0.5, "quality": 0.2, "match": 0.3}
        calc = ScoreCalculator(
            match_analyzer=MatchAnalyzer(),
            weights=explicit_weights,
        )

        assert calc.weights == explicit_weights

    def test_calculator_loads_from_config(self, tmp_path, monkeypatch):
        """ScoreCalculator loads weights from config when not explicit."""
        # Set custom weights in config
        config_mgr = ConfigManager(config_dir=tmp_path)
        custom_weights = {"trust": 0.4, "quality": 0.3, "match": 0.3}
        config_mgr.set_score_weights(custom_weights)

        # Patch ConfigManager constructor in the config module
        def mock_config_manager(*args, **kwargs):
            return ConfigManager(config_dir=tmp_path)

        monkeypatch.setattr(
            "skillmeat.config.ConfigManager",
            mock_config_manager,
        )

        # Create calculator without explicit weights
        calc = ScoreCalculator(match_analyzer=MatchAnalyzer())

        assert calc.weights == custom_weights

    def test_calculator_validates_explicit_weights(self):
        """ScoreCalculator validates explicit weights."""
        invalid_weights = {"trust": 0.5, "quality": 0.5, "match": 0.5}  # Sum = 1.5

        with pytest.raises(ValueError, match="must sum to 1.0"):
            ScoreCalculator(
                match_analyzer=MatchAnalyzer(),
                weights=invalid_weights,
            )

    def test_calculator_fallback_on_config_error(self, monkeypatch):
        """ScoreCalculator falls back to defaults on config error."""

        # Mock ConfigManager to raise exception
        def mock_config_manager(*args, **kwargs):
            raise RuntimeError("Config error")

        monkeypatch.setattr(
            "skillmeat.config.ConfigManager",
            mock_config_manager,
        )

        # Should fall back to defaults without crashing
        calc = ScoreCalculator(match_analyzer=MatchAnalyzer())
        assert calc.weights == DEFAULT_WEIGHTS


class TestIntegration:
    """Integration tests for weight customization flow."""

    def test_end_to_end_weight_customization(self, tmp_path, monkeypatch):
        """Test full flow: parse -> set -> load -> calculate."""
        # 1. Parse weight string
        weight_string = "trust=0.3,quality=0.3,match=0.4"
        parsed_weights = parse_score_weights(weight_string)

        # 2. Set in config
        config_mgr = ConfigManager(config_dir=tmp_path)
        config_mgr.set_score_weights(parsed_weights)

        # 3. Patch ConfigManager for ScoreCalculator
        def mock_config_manager(*args, **kwargs):
            return ConfigManager(config_dir=tmp_path)

        monkeypatch.setattr(
            "skillmeat.config.ConfigManager",
            mock_config_manager,
        )

        # 4. Load in ScoreCalculator
        calc = ScoreCalculator(match_analyzer=MatchAnalyzer())

        # 5. Verify weights are used
        assert calc.weights == parsed_weights
        assert calc.weights == {"trust": 0.3, "quality": 0.3, "match": 0.4}

    def test_roundtrip_with_defaults(self, tmp_path):
        """Test setting and retrieving default weights."""
        config_mgr = ConfigManager(config_dir=tmp_path)

        # Set defaults explicitly
        config_mgr.set_score_weights(DEFAULT_WEIGHTS)

        # Retrieve
        retrieved = config_mgr.get_score_weights()

        assert retrieved == DEFAULT_WEIGHTS
        assert sum(retrieved.values()) == 1.0
