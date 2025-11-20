"""Broker registry for managing marketplace brokers.

Loads brokers from configuration and provides access to registered brokers.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.signing import KeyManager

from .broker import MarketplaceBroker, RateLimitConfig

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

TOML_DUMPS = tomli_w.dumps

logger = logging.getLogger(__name__)


class BrokerRegistryError(Exception):
    """Raised when broker registry operations fail."""

    pass


class BrokerRegistry:
    """Registry for marketplace brokers.

    Manages broker instances and loads configuration from marketplace.toml.
    Provides access to registered brokers by name.

    Configuration file location: ~/.skillmeat/marketplace.toml

    Example configuration:
        [brokers.skillmeat]
        enabled = true
        endpoint = "https://marketplace.skillmeat.dev/api"

        [brokers.claudehub]
        enabled = true
        endpoint = "https://claude.ai/marketplace/api"

        [brokers.custom]
        enabled = false
        endpoint = "https://custom.example.com/api"
        schema_url = "https://custom.example.com/schema.json"
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".skillmeat"
    CONFIG_FILE = "marketplace.toml"

    # Default broker configurations
    DEFAULT_BROKERS = {
        "mock-local": {
            "enabled": True,
            "endpoint": "local://mock",
            "description": "Local mock broker for development (no network required)",
            "priority": 1,
        },
        "skillmeat": {
            "enabled": False,
            "endpoint": "https://marketplace.skillmeat.dev/api",
            "description": "Official SkillMeat marketplace",
            "priority": 2,
        },
        "claudehub": {
            "enabled": False,
            "endpoint": "https://claude.ai/marketplace/api",
            "description": "Claude Hub public catalogs (read-only)",
            "priority": 3,
        },
    }

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        key_manager: Optional[KeyManager] = None,
    ):
        """Initialize broker registry.

        Args:
            config_dir: Override default config directory (for testing)
            key_manager: Key manager for signature verification
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_path = self.config_dir / self.CONFIG_FILE
        self.key_manager = key_manager or KeyManager()

        # Registry of broker instances
        self._brokers: Dict[str, MarketplaceBroker] = {}

        # Load configuration
        self._ensure_config_exists()
        self._load_brokers()

    def _ensure_config_exists(self) -> None:
        """Create config directory and default config if not exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            # Write default configuration
            default_config = {"brokers": self.DEFAULT_BROKERS.copy()}
            self._write_config(default_config)
            logger.info(f"Created default marketplace config: {self.config_path}")

    def _read_config(self) -> Dict:
        """Read marketplace configuration.

        Returns:
            Dictionary containing marketplace configuration

        Raises:
            BrokerRegistryError: If config file is corrupted
        """
        if not self.config_path.exists():
            return {"brokers": {}}

        try:
            with open(self.config_path, "rb") as f:
                return TOML_LOADS(f.read().decode("utf-8"))
        except Exception as e:
            raise BrokerRegistryError(
                f"Failed to parse marketplace config: {e}"
            ) from e

    def _write_config(self, config: Dict) -> None:
        """Write marketplace configuration.

        Args:
            config: Configuration dictionary to write

        Raises:
            BrokerRegistryError: If write operation fails
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "wb") as f:
                f.write(TOML_DUMPS(config).encode("utf-8"))
        except Exception as e:
            raise BrokerRegistryError(
                f"Failed to write marketplace config: {e}"
            ) from e

    def _load_brokers(self) -> None:
        """Load brokers from configuration.

        Instantiates enabled broker classes and registers them.
        """
        config = self._read_config()
        brokers_config = config.get("brokers", {})

        # Import broker classes
        from .brokers import (
            ClaudeHubBroker,
            CustomWebBroker,
            MockLocalBroker,
            SkillMeatMarketplaceBroker,
        )

        # Map broker names to classes
        broker_classes = {
            "mock-local": MockLocalBroker,
            "skillmeat": SkillMeatMarketplaceBroker,
            "claudehub": ClaudeHubBroker,
            "custom": CustomWebBroker,
        }

        # Load each configured broker
        for broker_name, broker_config in brokers_config.items():
            if not broker_config.get("enabled", False):
                logger.debug(f"Broker {broker_name} is disabled, skipping")
                continue

            endpoint = broker_config.get("endpoint")
            if not endpoint:
                logger.warning(f"Broker {broker_name} has no endpoint, skipping")
                continue

            # Validate endpoint before instantiation
            if not self._validate_endpoint(endpoint):
                logger.warning(
                    f"Broker {broker_name} endpoint validation failed: {endpoint}"
                )
                continue

            # Get broker class
            broker_class = broker_classes.get(broker_name)
            if not broker_class:
                logger.warning(f"Unknown broker type: {broker_name}, skipping")
                continue

            try:
                # Parse rate limit config if present
                rate_limit = None
                if "rate_limit" in broker_config:
                    rl_config = broker_config["rate_limit"]
                    rate_limit = RateLimitConfig(
                        max_requests=rl_config.get("max_requests", 100),
                        time_window=rl_config.get("time_window", 60),
                        retry_after=rl_config.get("retry_after", 60),
                    )

                # Get cache TTL
                cache_ttl = broker_config.get("cache_ttl", 300)

                # Instantiate broker
                if broker_name == "custom":
                    # Custom broker needs schema_url
                    schema_url = broker_config.get("schema_url")
                    broker = broker_class(
                        name=broker_name,
                        endpoint=endpoint,
                        schema_url=schema_url,
                        rate_limit=rate_limit,
                        cache_ttl=cache_ttl,
                        key_manager=self.key_manager,
                    )
                else:
                    broker = broker_class(
                        name=broker_name,
                        endpoint=endpoint,
                        rate_limit=rate_limit,
                        cache_ttl=cache_ttl,
                        key_manager=self.key_manager,
                    )

                self._brokers[broker_name] = broker
                logger.info(f"Registered broker: {broker_name} ({endpoint})")

            except Exception as e:
                logger.error(f"Failed to load broker {broker_name}: {e}")
                continue

    def _validate_endpoint(self, endpoint: str) -> bool:
        """Validate broker endpoint URL.

        Args:
            endpoint: Endpoint URL to validate

        Returns:
            True if endpoint is valid
        """
        # Basic URL validation
        if not endpoint:
            return False

        # Allow local:// for mock broker
        if endpoint.startswith("local://"):
            return True

        if not endpoint.startswith(("http://", "https://")):
            logger.warning(f"Endpoint must use http or https: {endpoint}")
            return False

        # Could add more validation (DNS resolution, connectivity check)
        # but keeping it simple for now

        return True

    def get_broker(self, name: str) -> Optional[MarketplaceBroker]:
        """Get broker by name.

        Args:
            name: Broker name (e.g., "skillmeat", "claudehub")

        Returns:
            MarketplaceBroker instance or None if not found
        """
        return self._brokers.get(name)

    def list_brokers(self) -> List[str]:
        """List all registered broker names.

        Returns:
            List of broker names
        """
        return list(self._brokers.keys())

    def get_enabled_brokers(self) -> List[MarketplaceBroker]:
        """Get all enabled broker instances.

        Returns:
            List of enabled MarketplaceBroker instances
        """
        return list(self._brokers.values())

    def register_broker(self, name: str, broker: MarketplaceBroker) -> None:
        """Register a broker instance.

        Args:
            name: Broker name
            broker: MarketplaceBroker instance

        Raises:
            BrokerRegistryError: If broker name already registered
        """
        if name in self._brokers:
            raise BrokerRegistryError(f"Broker '{name}' is already registered")

        self._brokers[name] = broker
        logger.info(f"Registered broker: {name}")

    def unregister_broker(self, name: str) -> bool:
        """Unregister a broker.

        Args:
            name: Broker name to unregister

        Returns:
            True if broker was unregistered, False if not found
        """
        if name in self._brokers:
            broker = self._brokers[name]
            broker.close()
            del self._brokers[name]
            logger.info(f"Unregistered broker: {name}")
            return True
        return False

    def enable_broker(self, name: str) -> None:
        """Enable a broker in configuration.

        Args:
            name: Broker name to enable

        Raises:
            BrokerRegistryError: If broker not found in config
        """
        config = self._read_config()
        brokers_config = config.get("brokers", {})

        if name not in brokers_config:
            raise BrokerRegistryError(f"Broker '{name}' not found in configuration")

        brokers_config[name]["enabled"] = True
        config["brokers"] = brokers_config
        self._write_config(config)

        # Reload brokers
        self._brokers.clear()
        self._load_brokers()

        logger.info(f"Enabled broker: {name}")

    def disable_broker(self, name: str) -> None:
        """Disable a broker in configuration.

        Args:
            name: Broker name to disable

        Raises:
            BrokerRegistryError: If broker not found in config
        """
        config = self._read_config()
        brokers_config = config.get("brokers", {})

        if name not in brokers_config:
            raise BrokerRegistryError(f"Broker '{name}' not found in configuration")

        brokers_config[name]["enabled"] = False
        config["brokers"] = brokers_config
        self._write_config(config)

        # Unregister broker if loaded
        self.unregister_broker(name)

        logger.info(f"Disabled broker: {name}")

    def close_all(self) -> None:
        """Close all broker sessions and cleanup resources."""
        for broker in self._brokers.values():
            broker.close()
        self._brokers.clear()
        logger.debug("Closed all broker sessions")


# Global registry instance
_global_registry: Optional[BrokerRegistry] = None


def get_broker_registry(
    config_dir: Optional[Path] = None,
    key_manager: Optional[KeyManager] = None,
) -> BrokerRegistry:
    """Get global broker registry instance.

    Args:
        config_dir: Override default config directory (for testing)
        key_manager: Key manager for signature verification

    Returns:
        BrokerRegistry instance
    """
    global _global_registry

    if _global_registry is None or config_dir is not None:
        _global_registry = BrokerRegistry(
            config_dir=config_dir, key_manager=key_manager
        )

    return _global_registry
