"""Configuration management for SkillMeat."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

TOML_DUMPS = tomli_w.dumps


class ConfigManager:
    """Manages user configuration in ~/.skillmeat/config.toml"""

    DEFAULT_CONFIG_DIR = Path.home() / ".skillmeat"
    CONFIG_FILE = "config.toml"

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize config manager.

        Args:
            config_dir: Override default config directory (for testing)
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_path = self.config_dir / self.CONFIG_FILE
        self._ensure_config_exists()

    def _ensure_config_exists(self) -> None:
        """Create config directory and default config if not exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            default_config = {
                "settings": {
                    "default-collection": "default",
                    "update-strategy": "prompt",
                }
            }
            self.write(default_config)

    def read(self) -> Dict[str, Any]:
        """Read entire config.

        Returns:
            Dictionary containing all config values

        Raises:
            ValueError: If config file is corrupted
        """
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "rb") as f:
                return TOML_LOADS(f.read().decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse config file: {e}")

    def write(self, config: Dict[str, Any]) -> None:
        """Write entire config.

        Args:
            config: Configuration dictionary to write

        Raises:
            IOError: If write operation fails
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "wb") as f:
            f.write(TOML_DUMPS(config).encode("utf-8"))

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get config value by key (supports nested keys with dot notation).

        Args:
            key: Configuration key (e.g., "settings.github-token")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get("settings.github-token")
            >>> config.get("settings.default-collection", "default")
        """
        config = self.read()
        parts = key.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set config value by key (supports nested keys with dot notation).

        Args:
            key: Configuration key (e.g., "settings.github-token")
            value: Value to set

        Raises:
            IOError: If write operation fails

        Example:
            >>> config.set("settings.github-token", "ghp_...")
            >>> config.set("settings.default-collection", "my-collection")
        """
        config = self.read()
        parts = key.split(".")

        # Navigate to nested dict, creating as needed
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        current[parts[-1]] = value
        self.write(config)

    def delete(self, key: str) -> bool:
        """Delete configuration value by key.

        Args:
            key: Configuration key to delete

        Returns:
            True if key existed and was deleted, False otherwise
        """
        config = self.read()
        parts = key.split(".")

        # Navigate to parent dict
        current = config
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]

        # Delete the key
        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
            self.write(config)
            return True

        return False

    def get_active_collection(self) -> str:
        """Get active collection name.

        Returns:
            Active collection name (defaults to "default")
        """
        return self.get("settings.default-collection", "default")

    def set_active_collection(self, name: str) -> None:
        """Set active collection name.

        Args:
            name: Collection name to set as active
        """
        self.set("settings.default-collection", name)

    def get_collections_dir(self) -> Path:
        """Get collections directory path.

        Returns:
            Path to collections directory
        """
        return self.config_dir / "collections"

    def get_snapshots_dir(self) -> Path:
        """Get snapshots directory path.

        Returns:
            Path to snapshots directory
        """
        return self.config_dir / "snapshots"

    def get_collection_path(self, name: str) -> Path:
        """Get path to specific collection.

        Args:
            name: Collection name

        Returns:
            Path to collection directory
        """
        return self.get_collections_dir() / name
