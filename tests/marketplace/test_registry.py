"""Tests for marketplace broker registry."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from skillmeat.marketplace.broker import MarketplaceBroker
from skillmeat.marketplace.registry import BrokerRegistry, BrokerRegistryError


class TestBrokerRegistry:
    """Tests for BrokerRegistry."""

    def test_initialization(self, tmp_path):
        """Test registry initialization."""
        registry = BrokerRegistry(config_dir=tmp_path)

        assert registry.config_dir == tmp_path
        assert registry.config_path.exists()

    def test_default_config_creation(self, tmp_path):
        """Test that default config is created on initialization."""
        config_dir = tmp_path / "test_registry"
        registry = BrokerRegistry(config_dir=config_dir)

        assert registry.config_path.exists()

        # Check default config content
        config = registry._read_config()
        assert "brokers" in config
        assert "skillmeat" in config["brokers"]
        assert "claudehub" in config["brokers"]

    def test_get_broker_exists(self, tmp_path):
        """Test getting existing broker."""
        registry = BrokerRegistry(config_dir=tmp_path)

        # Should have default brokers loaded
        broker = registry.get_broker("skillmeat")
        assert broker is not None
        assert broker.name == "skillmeat"

    def test_get_broker_not_found(self, tmp_path):
        """Test getting non-existent broker."""
        registry = BrokerRegistry(config_dir=tmp_path)

        broker = registry.get_broker("nonexistent")
        assert broker is None

    def test_list_brokers(self, tmp_path):
        """Test listing all brokers."""
        registry = BrokerRegistry(config_dir=tmp_path)

        brokers = registry.list_brokers()
        assert isinstance(brokers, list)
        # Should have at least the default brokers
        assert "skillmeat" in brokers
        assert "claudehub" in brokers

    def test_get_enabled_brokers(self, tmp_path):
        """Test getting all enabled brokers."""
        registry = BrokerRegistry(config_dir=tmp_path)

        brokers = registry.get_enabled_brokers()
        assert isinstance(brokers, list)
        assert len(brokers) >= 2  # At least skillmeat and claudehub

    def test_register_broker(self, tmp_path):
        """Test registering a new broker."""
        registry = BrokerRegistry(config_dir=tmp_path)

        # Create mock broker
        mock_broker = Mock(spec=MarketplaceBroker)
        mock_broker.name = "test"
        mock_broker.close = Mock()

        registry.register_broker("test", mock_broker)

        # Should be able to retrieve it
        broker = registry.get_broker("test")
        assert broker is mock_broker

    def test_register_broker_duplicate_name(self, tmp_path):
        """Test that registering duplicate broker raises error."""
        registry = BrokerRegistry(config_dir=tmp_path)

        mock_broker1 = Mock(spec=MarketplaceBroker)
        mock_broker1.name = "test"
        mock_broker1.close = Mock()

        mock_broker2 = Mock(spec=MarketplaceBroker)
        mock_broker2.name = "test"
        mock_broker2.close = Mock()

        registry.register_broker("test", mock_broker1)

        with pytest.raises(BrokerRegistryError, match="already registered"):
            registry.register_broker("test", mock_broker2)

    def test_unregister_broker(self, tmp_path):
        """Test unregistering a broker."""
        registry = BrokerRegistry(config_dir=tmp_path)

        # Register test broker
        mock_broker = Mock(spec=MarketplaceBroker)
        mock_broker.name = "test"
        mock_broker.close = Mock()

        registry.register_broker("test", mock_broker)

        # Unregister it
        result = registry.unregister_broker("test")
        assert result is True

        # Should no longer be available
        broker = registry.get_broker("test")
        assert broker is None

        # Close should have been called
        mock_broker.close.assert_called_once()

    def test_unregister_broker_not_found(self, tmp_path):
        """Test unregistering non-existent broker."""
        registry = BrokerRegistry(config_dir=tmp_path)

        result = registry.unregister_broker("nonexistent")
        assert result is False

    def test_enable_broker(self, tmp_path):
        """Test enabling a broker in configuration."""
        registry = BrokerRegistry(config_dir=tmp_path)

        # Disable a broker first
        config = registry._read_config()
        config["brokers"]["skillmeat"]["enabled"] = False
        registry._write_config(config)

        # Reload registry to pick up change
        registry._brokers.clear()
        registry._load_brokers()

        # Should not be available
        broker = registry.get_broker("skillmeat")
        assert broker is None

        # Enable it
        registry.enable_broker("skillmeat")

        # Should now be available
        broker = registry.get_broker("skillmeat")
        assert broker is not None

    def test_enable_broker_not_found(self, tmp_path):
        """Test enabling non-existent broker raises error."""
        registry = BrokerRegistry(config_dir=tmp_path)

        with pytest.raises(BrokerRegistryError, match="not found in configuration"):
            registry.enable_broker("nonexistent")

    def test_disable_broker(self, tmp_path):
        """Test disabling a broker in configuration."""
        registry = BrokerRegistry(config_dir=tmp_path)

        # Should initially be available
        broker = registry.get_broker("skillmeat")
        assert broker is not None

        # Disable it
        registry.disable_broker("skillmeat")

        # Should no longer be available
        broker = registry.get_broker("skillmeat")
        assert broker is None

        # Check config
        config = registry._read_config()
        assert config["brokers"]["skillmeat"]["enabled"] is False

    def test_disable_broker_not_found(self, tmp_path):
        """Test disabling non-existent broker raises error."""
        registry = BrokerRegistry(config_dir=tmp_path)

        with pytest.raises(BrokerRegistryError, match="not found in configuration"):
            registry.disable_broker("nonexistent")

    def test_validate_endpoint_valid_https(self, tmp_path):
        """Test endpoint validation with valid HTTPS URL."""
        registry = BrokerRegistry(config_dir=tmp_path)

        assert registry._validate_endpoint("https://example.com/api")

    def test_validate_endpoint_valid_http(self, tmp_path):
        """Test endpoint validation with valid HTTP URL."""
        registry = BrokerRegistry(config_dir=tmp_path)

        assert registry._validate_endpoint("http://localhost:8000/api")

    def test_validate_endpoint_empty(self, tmp_path):
        """Test endpoint validation with empty URL."""
        registry = BrokerRegistry(config_dir=tmp_path)

        assert not registry._validate_endpoint("")

    def test_validate_endpoint_no_protocol(self, tmp_path):
        """Test endpoint validation without protocol."""
        registry = BrokerRegistry(config_dir=tmp_path)

        assert not registry._validate_endpoint("example.com/api")

    def test_close_all(self, tmp_path):
        """Test closing all broker sessions."""
        registry = BrokerRegistry(config_dir=tmp_path)

        # Register mock brokers
        mock_broker1 = Mock(spec=MarketplaceBroker)
        mock_broker1.name = "test1"
        mock_broker1.close = Mock()

        mock_broker2 = Mock(spec=MarketplaceBroker)
        mock_broker2.name = "test2"
        mock_broker2.close = Mock()

        registry.register_broker("test1", mock_broker1)
        registry.register_broker("test2", mock_broker2)

        # Close all
        registry.close_all()

        # All brokers should be closed
        mock_broker1.close.assert_called_once()
        mock_broker2.close.assert_called_once()

        # Registry should be empty
        assert len(registry._brokers) == 0

    def test_load_brokers_with_rate_limit(self, tmp_path):
        """Test loading brokers with rate limit configuration."""
        config_dir = tmp_path / "test_registry"
        config_dir.mkdir()

        # Create config with rate limit
        config = {
            "brokers": {
                "skillmeat": {
                    "enabled": True,
                    "endpoint": "https://marketplace.skillmeat.dev/api",
                    "rate_limit": {
                        "max_requests": 50,
                        "time_window": 30,
                        "retry_after": 30,
                    },
                }
            }
        }

        import tomli_w

        config_path = config_dir / "marketplace.toml"
        with open(config_path, "wb") as f:
            f.write(tomli_w.dumps(config).encode("utf-8"))

        # Load registry
        registry = BrokerRegistry(config_dir=config_dir)

        broker = registry.get_broker("skillmeat")
        assert broker is not None
        assert broker.rate_limit.max_requests == 50
        assert broker.rate_limit.time_window == 30

    def test_load_brokers_invalid_endpoint(self, tmp_path):
        """Test that brokers with invalid endpoints are skipped."""
        config_dir = tmp_path / "test_registry"
        config_dir.mkdir()

        # Create config with invalid endpoint
        config = {
            "brokers": {
                "invalid": {
                    "enabled": True,
                    "endpoint": "invalid-url",  # No http/https
                }
            }
        }

        import tomli_w

        config_path = config_dir / "marketplace.toml"
        with open(config_path, "wb") as f:
            f.write(tomli_w.dumps(config).encode("utf-8"))

        # Load registry
        registry = BrokerRegistry(config_dir=config_dir)

        # Invalid broker should not be loaded
        broker = registry.get_broker("invalid")
        assert broker is None

    def test_read_config_error(self, tmp_path):
        """Test that corrupted config raises error."""
        config_dir = tmp_path / "test_registry"
        config_dir.mkdir()

        # Create invalid config
        config_path = config_dir / "marketplace.toml"
        config_path.write_text("invalid toml {{}")

        with pytest.raises(BrokerRegistryError, match="Failed to parse"):
            registry = BrokerRegistry(config_dir=config_dir)
            registry._read_config()


def test_get_broker_registry_singleton(tmp_path):
    """Test that get_broker_registry returns singleton."""
    from skillmeat.marketplace.registry import get_broker_registry

    # First call
    registry1 = get_broker_registry(config_dir=tmp_path)

    # Second call with same config_dir should return new instance
    registry2 = get_broker_registry(config_dir=tmp_path)

    # Should be different instances (config_dir override)
    assert registry1 is not registry2

    # Call without config_dir should return cached
    registry3 = get_broker_registry()
    registry4 = get_broker_registry()

    # These should be the same instance
    assert registry3 is registry4
