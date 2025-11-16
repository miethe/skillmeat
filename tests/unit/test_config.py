"""Tests for ConfigManager."""

import pytest
from pathlib import Path
from skillmeat.config import ConfigManager


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    return tmp_path / "config"


@pytest.fixture
def config_manager(temp_config_dir):
    """Create ConfigManager with temp directory."""
    return ConfigManager(config_dir=temp_config_dir)


def test_config_manager_initialization(config_manager, temp_config_dir):
    """Test ConfigManager initialization creates config directory and default config."""
    assert temp_config_dir.exists()
    assert (temp_config_dir / "config.toml").exists()

    # Check default config values
    config = config_manager.read()
    assert "settings" in config
    assert config["settings"]["default-collection"] == "default"
    assert config["settings"]["update-strategy"] == "prompt"

    # Check analytics defaults
    assert "analytics" in config
    assert config["analytics"]["enabled"] is True
    assert config["analytics"]["retention-days"] == 90


def test_get_existing_key(config_manager):
    """Test getting existing config value."""
    value = config_manager.get("settings.default-collection")
    assert value == "default"


def test_get_nonexistent_key_returns_default(config_manager):
    """Test getting nonexistent key returns default value."""
    value = config_manager.get("nonexistent.key", "default_value")
    assert value == "default_value"


def test_get_without_default_returns_none(config_manager):
    """Test getting nonexistent key without default returns None."""
    value = config_manager.get("nonexistent.key")
    assert value is None


def test_set_new_key(config_manager):
    """Test setting new config value."""
    config_manager.set("settings.github-token", "ghp_test123")
    value = config_manager.get("settings.github-token")
    assert value == "ghp_test123"


def test_set_nested_key_creates_structure(config_manager):
    """Test setting nested key creates intermediate dictionaries."""
    config_manager.set("new.nested.key", "value")
    value = config_manager.get("new.nested.key")
    assert value == "value"

    config = config_manager.read()
    assert "new" in config
    assert "nested" in config["new"]
    assert config["new"]["nested"]["key"] == "value"


def test_set_overwrites_existing_key(config_manager):
    """Test setting existing key overwrites value."""
    config_manager.set("settings.default-collection", "new-collection")
    value = config_manager.get("settings.default-collection")
    assert value == "new-collection"


def test_delete_existing_key(config_manager):
    """Test deleting existing key."""
    config_manager.set("settings.test-key", "test-value")
    assert config_manager.get("settings.test-key") == "test-value"

    result = config_manager.delete("settings.test-key")
    assert result is True
    assert config_manager.get("settings.test-key") is None


def test_delete_nonexistent_key(config_manager):
    """Test deleting nonexistent key returns False."""
    result = config_manager.delete("nonexistent.key")
    assert result is False


def test_get_active_collection(config_manager):
    """Test getting active collection name."""
    collection_name = config_manager.get_active_collection()
    assert collection_name == "default"


def test_set_active_collection(config_manager):
    """Test setting active collection name."""
    config_manager.set_active_collection("my-collection")
    assert config_manager.get_active_collection() == "my-collection"


def test_get_collections_dir(config_manager, temp_config_dir):
    """Test getting collections directory path."""
    collections_dir = config_manager.get_collections_dir()
    assert collections_dir == temp_config_dir / "collections"


def test_get_snapshots_dir(config_manager, temp_config_dir):
    """Test getting snapshots directory path."""
    snapshots_dir = config_manager.get_snapshots_dir()
    assert snapshots_dir == temp_config_dir / "snapshots"


def test_get_collection_path(config_manager, temp_config_dir):
    """Test getting specific collection path."""
    collection_path = config_manager.get_collection_path("test-collection")
    assert collection_path == temp_config_dir / "collections" / "test-collection"


def test_read_write_roundtrip(config_manager):
    """Test reading and writing config maintains data integrity."""
    test_config = {
        "settings": {
            "default-collection": "test",
            "github-token": "ghp_test",
            "nested": {"key": "value"},
        },
        "custom": {"data": [1, 2, 3]},
    }

    config_manager.write(test_config)
    read_config = config_manager.read()

    assert read_config == test_config


def test_corrupted_config_raises_error(temp_config_dir):
    """Test reading corrupted config raises ValueError."""
    config_file = temp_config_dir / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("invalid toml {{{")

    config_manager = ConfigManager(config_dir=temp_config_dir)

    with pytest.raises(ValueError, match="Failed to parse config file"):
        config_manager.read()


def test_nested_key_partial_path_returns_default(config_manager):
    """Test getting partial path in nested key returns default."""
    config_manager.set("a.b.c", "value")
    # Try to get "a.b.c.d" which doesn't exist
    value = config_manager.get("a.b.c.d", "default")
    assert value == "default"


def test_multiple_managers_same_directory(temp_config_dir):
    """Test multiple ConfigManager instances share same config file."""
    manager1 = ConfigManager(config_dir=temp_config_dir)
    manager2 = ConfigManager(config_dir=temp_config_dir)

    manager1.set("test.key", "value1")
    value = manager2.get("test.key")

    assert value == "value1"


def test_is_analytics_enabled_default(config_manager):
    """Test analytics enabled by default."""
    assert config_manager.is_analytics_enabled() is True


def test_is_analytics_enabled_disabled(config_manager):
    """Test disabling analytics."""
    config_manager.set("analytics.enabled", False)
    assert config_manager.is_analytics_enabled() is False


def test_get_analytics_retention_days_default(config_manager):
    """Test default analytics retention period."""
    assert config_manager.get_analytics_retention_days() == 90


def test_get_analytics_retention_days_custom(config_manager):
    """Test custom analytics retention period."""
    config_manager.set("analytics.retention-days", 30)
    assert config_manager.get_analytics_retention_days() == 30


def test_get_analytics_db_path_default(config_manager, temp_config_dir):
    """Test default analytics database path."""
    path = config_manager.get_analytics_db_path()
    assert path == temp_config_dir / "analytics.db"


def test_get_analytics_db_path_custom(config_manager, tmp_path):
    """Test custom analytics database path."""
    custom_path = tmp_path / "custom" / "analytics.db"
    config_manager.set("analytics.db-path", str(custom_path))
    path = config_manager.get_analytics_db_path()
    assert path == custom_path
