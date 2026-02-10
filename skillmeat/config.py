"""Configuration management for SkillMeat."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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
                },
                "analytics": {
                    "enabled": True,
                    "retention-days": 90,
                },
                "artifact_search": {
                    "indexing_mode": "opt_in",
                },
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
        # Validate artifact_search.indexing_mode
        if key == "artifact_search.indexing_mode":
            value = self._validate_indexing_mode(value)

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

    def is_analytics_enabled(self) -> bool:
        """Check if analytics tracking is enabled.

        Returns:
            True if analytics is enabled, False otherwise
        """
        return self.get("analytics.enabled", True)

    def get_analytics_retention_days(self) -> int:
        """Get analytics retention period in days.

        Returns:
            Number of days to retain analytics events (0 = keep forever)
        """
        return self.get("analytics.retention-days", 90)

    def get_analytics_db_path(self) -> Path:
        """Get analytics database path.

        Returns:
            Path to analytics database file
        """
        custom_path = self.get("analytics.db-path")
        if custom_path:
            return Path(custom_path)
        return self.config_dir / "analytics.db"

    def get_score_weights(self) -> Dict[str, float]:
        """Get configured score weights or defaults.

        Returns:
            Dict with keys: trust, quality, match (floats summing to 1.0)

        Example:
            >>> config = ConfigManager()
            >>> weights = config.get_score_weights()
            >>> assert sum(weights.values()) == 1.0
        """
        weights = self.get("scoring.weights")
        if weights is None:
            # Return defaults from score_calculator
            from skillmeat.core.scoring.score_calculator import DEFAULT_WEIGHTS

            return DEFAULT_WEIGHTS.copy()
        return weights

    def set_score_weights(self, weights: Dict[str, float]) -> None:
        """Set score weights in config.

        Args:
            weights: Dict with keys trust, quality, match (must sum to 1.0)

        Raises:
            ValueError: If weights invalid or don't sum to 1.0

        Example:
            >>> config = ConfigManager()
            >>> config.set_score_weights({"trust": 0.3, "quality": 0.3, "match": 0.4})
        """
        # Validate required keys
        required_keys = {"trust", "quality", "match"}
        if set(weights.keys()) != required_keys:
            raise ValueError(
                f"Expected keys: {required_keys}, got: {set(weights.keys())}"
            )

        # Validate value ranges
        for key, val in weights.items():
            if not (0 <= val <= 1):
                raise ValueError(f"Weight '{key}' must be 0-1, got {val}")

        # Validate sum
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.set("scoring.weights", weights)

    def get_api_base_url(self) -> str:
        """Get API server base URL from config or default.

        Returns:
            API base URL string
        """
        return self.get("api.base_url", "http://localhost:8080")

    def _validate_indexing_mode(self, value: str) -> str:
        """Validate the indexing mode value.

        Args:
            value: The indexing mode to validate. Valid values are:
                - "off": Disable indexing for all sources
                - "on": Enable indexing by default (sources can opt-out)
                - "opt_in": Disable indexing by default (sources must opt-in)

        Returns:
            The validated mode, or "opt_in" if the value was invalid.

        Note:
            Invalid values log a warning and return "opt_in" as the default.
        """
        valid_modes = {"off", "on", "opt_in"}
        if value not in valid_modes:
            logger.warning(
                f"Invalid indexing_mode '{value}'. "
                f"Valid values: {valid_modes}. Defaulting to 'opt_in'."
            )
            return "opt_in"
        return value

    def get_indexing_mode(self) -> str:
        """Get the current artifact search indexing mode.

        Returns:
            The indexing mode ("off", "on", or "opt_in"). Defaults to "opt_in"
            if not configured.

        Example:
            >>> config = ConfigManager()
            >>> mode = config.get_indexing_mode()
            >>> print(mode)
            'opt_in'
        """
        return self.get("artifact_search.indexing_mode", "opt_in")

    def set_indexing_mode(self, value: str) -> str:
        """Set the artifact search indexing mode.

        Args:
            value: The indexing mode. Valid values:
                - "off": Disable indexing for all sources
                - "on": Enable indexing by default (sources can opt-out)
                - "opt_in": Disable indexing by default (sources must opt-in)

        Returns:
            The actual value that was set (after validation).

        Example:
            >>> config = ConfigManager()
            >>> config.set_indexing_mode("on")
            'on'
        """
        logger.info(f"Setting artifact_search.indexing_mode to '{value}'")
        self.set("artifact_search.indexing_mode", value)
        return self.get_indexing_mode()

    def get_project_search_paths(self) -> List[str]:
        """Get configured project search paths.

        Returns:
            List of project search paths. If not configured, returns default paths.
        """
        paths = self.get("settings.project-search-paths")
        if paths is not None:
            return paths

        # Default paths
        home = Path.home()
        return [
            str(home / "projects"),
            str(home / "dev"),
            str(home / "workspace"),
            str(home / "src"),
            str(Path.cwd()),
        ]

    def set_project_search_paths(self, paths: List[str]) -> None:
        """Set project search paths.

        Args:
            paths: List of search paths
        """
        self.set("settings.project-search-paths", paths)

    def add_project_search_path(self, path: str) -> None:
        """Add a project search path.

        Args:
            path: Path to add
        """
        paths = self.get_project_search_paths()
        if path not in paths:
            paths.append(path)
            self.set_project_search_paths(paths)

    def remove_project_search_path(self, path: str) -> None:
        """Remove a project search path.

        Args:
            path: Path to remove
        """
        paths = self.get_project_search_paths()
        if path in paths:
            paths.remove(path)
            self.set_project_search_paths(paths)
