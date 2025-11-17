"""Tests for vault configuration management."""

import json
from pathlib import Path

import pytest

from skillmeat.core.sharing.vault.config import VaultConfig, VaultConfigManager


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".skillmeat"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def vault_config_mgr(temp_config_dir):
    """Create vault config manager with temp directory."""
    return VaultConfigManager(config_dir=temp_config_dir)


class TestVaultConfig:
    """Tests for VaultConfig."""

    def test_init(self):
        """Test vault config initialization."""
        config = VaultConfig(
            name="test-vault",
            type="git",
            config={"url": "git@github.com:test/vault.git"},
            read_only=False,
            is_default=True,
        )

        assert config.name == "test-vault"
        assert config.type == "git"
        assert config.config["url"] == "git@github.com:test/vault.git"
        assert not config.read_only
        assert config.is_default

    def test_to_dict(self):
        """Test converting vault config to dictionary."""
        config = VaultConfig(
            name="test-vault",
            type="git",
            config={"url": "git@github.com:test/vault.git", "branch": "main"},
            read_only=True,
        )

        data = config.to_dict()

        assert data["type"] == "git"
        assert data["url"] == "git@github.com:test/vault.git"
        assert data["branch"] == "main"
        assert data["read_only"] is True

    def test_from_dict(self):
        """Test creating vault config from dictionary."""
        data = {
            "type": "s3",
            "bucket": "test-bucket",
            "region": "us-west-2",
            "read_only": True,
        }

        config = VaultConfig.from_dict("test-s3", data)

        assert config.name == "test-s3"
        assert config.type == "s3"
        assert config.config["bucket"] == "test-bucket"
        assert config.config["region"] == "us-west-2"
        assert config.read_only

    def test_from_dict_missing_type(self):
        """Test creating config from dict without type fails."""
        data = {"bucket": "test-bucket"}

        with pytest.raises(ValueError, match="missing required 'type'"):
            VaultConfig.from_dict("test", data)


class TestVaultConfigManager:
    """Tests for VaultConfigManager."""

    def test_init(self, temp_config_dir):
        """Test config manager initialization."""
        mgr = VaultConfigManager(config_dir=temp_config_dir)

        assert mgr.config_dir == temp_config_dir
        assert mgr.config_path == temp_config_dir / "sharing.toml"

    def test_add_vault(self, vault_config_mgr):
        """Test adding vault configuration."""
        config = VaultConfig(
            name="team-git",
            type="git",
            config={"url": "git@github.com:team/vault.git", "branch": "main"},
        )

        vault_config_mgr.add_vault(config)

        # Verify vault was added
        vault = vault_config_mgr.get_vault("team-git")
        assert vault is not None
        assert vault.name == "team-git"
        assert vault.type == "git"
        assert vault.config["url"] == "git@github.com:team/vault.git"

    def test_add_vault_sets_default(self, vault_config_mgr):
        """Test adding first vault sets it as default."""
        config = VaultConfig(
            name="team-git",
            type="git",
            config={"url": "git@github.com:team/vault.git"},
        )

        vault_config_mgr.add_vault(config)

        # Should be set as default
        assert vault_config_mgr.get_default_vault() == "team-git"

    def test_add_multiple_vaults(self, vault_config_mgr):
        """Test adding multiple vaults."""
        configs = [
            VaultConfig(
                name="git-vault",
                type="git",
                config={"url": "git@github.com:test/vault.git"},
            ),
            VaultConfig(
                name="s3-vault",
                type="s3",
                config={"bucket": "test-bucket"},
            ),
            VaultConfig(
                name="local-vault",
                type="local",
                config={"path": "/tmp/vault"},
            ),
        ]

        for config in configs:
            vault_config_mgr.add_vault(config)

        # List vaults
        vaults = vault_config_mgr.list_vaults()
        assert len(vaults) == 3
        assert "git-vault" in vaults
        assert "s3-vault" in vaults
        assert "local-vault" in vaults

    def test_remove_vault(self, vault_config_mgr):
        """Test removing vault configuration."""
        # Add two vaults
        config1 = VaultConfig(
            name="vault1",
            type="local",
            config={"path": "/tmp/vault1"},
        )
        config2 = VaultConfig(
            name="vault2",
            type="local",
            config={"path": "/tmp/vault2"},
            is_default=True,
        )

        vault_config_mgr.add_vault(config1)
        vault_config_mgr.add_vault(config2)

        # Set vault2 as default explicitly
        vault_config_mgr.set_default_vault("vault2")

        # Remove vault1
        assert vault_config_mgr.remove_vault("vault1")

        # Verify it's gone
        assert vault_config_mgr.get_vault("vault1") is None
        assert "vault1" not in vault_config_mgr.list_vaults()

    def test_remove_nonexistent_vault(self, vault_config_mgr):
        """Test removing nonexistent vault returns False."""
        assert not vault_config_mgr.remove_vault("nonexistent")

    def test_remove_default_vault_fails(self, vault_config_mgr):
        """Test removing default vault fails."""
        config = VaultConfig(
            name="default-vault",
            type="local",
            config={"path": "/tmp/vault"},
        )

        vault_config_mgr.add_vault(config)

        # Try to remove default vault
        with pytest.raises(ValueError, match="Cannot remove default vault"):
            vault_config_mgr.remove_vault("default-vault")

    def test_get_vault(self, vault_config_mgr):
        """Test getting vault configuration."""
        config = VaultConfig(
            name="test-vault",
            type="git",
            config={"url": "git@github.com:test/vault.git"},
        )

        vault_config_mgr.add_vault(config)

        vault = vault_config_mgr.get_vault("test-vault")

        assert vault is not None
        assert vault.name == "test-vault"
        assert vault.type == "git"

    def test_get_nonexistent_vault(self, vault_config_mgr):
        """Test getting nonexistent vault returns None."""
        assert vault_config_mgr.get_vault("nonexistent") is None

    def test_list_vaults(self, vault_config_mgr):
        """Test listing vaults."""
        # Initially empty
        assert vault_config_mgr.list_vaults() == []

        # Add vaults
        for i in range(3):
            config = VaultConfig(
                name=f"vault{i}",
                type="local",
                config={"path": f"/tmp/vault{i}"},
            )
            vault_config_mgr.add_vault(config)

        vaults = vault_config_mgr.list_vaults()
        assert len(vaults) == 3

    def test_set_default_vault(self, vault_config_mgr):
        """Test setting default vault."""
        # Add vaults
        config1 = VaultConfig(name="vault1", type="local", config={"path": "/tmp/vault1"})
        config2 = VaultConfig(name="vault2", type="local", config={"path": "/tmp/vault2"})

        vault_config_mgr.add_vault(config1)
        vault_config_mgr.add_vault(config2)

        # Set vault2 as default
        vault_config_mgr.set_default_vault("vault2")

        assert vault_config_mgr.get_default_vault() == "vault2"

        # Verify is_default flag
        vault2 = vault_config_mgr.get_vault("vault2")
        assert vault2.is_default

    def test_set_default_nonexistent_vault(self, vault_config_mgr):
        """Test setting nonexistent vault as default fails."""
        with pytest.raises(ValueError, match="not found"):
            vault_config_mgr.set_default_vault("nonexistent")

    def test_get_default_vault(self, vault_config_mgr):
        """Test getting default vault."""
        # Initially no default
        assert vault_config_mgr.get_default_vault() is None

        # Add a vault
        config = VaultConfig(
            name="default-vault",
            type="local",
            config={"path": "/tmp/vault"},
        )
        vault_config_mgr.add_vault(config)

        # Should be set as default
        assert vault_config_mgr.get_default_vault() == "default-vault"

    def test_store_and_get_credentials(self, vault_config_mgr):
        """Test storing and retrieving credentials."""
        # Store Git credentials
        git_creds = {
            "username": "testuser",
            "password": "testpass",
        }

        vault_config_mgr.store_credentials("test-git", "git", git_creds)

        # Retrieve credentials
        retrieved = vault_config_mgr.get_credentials("test-git", "git")

        assert retrieved is not None
        assert retrieved["username"] == "testuser"
        assert retrieved["password"] == "testpass"

    def test_store_s3_credentials(self, vault_config_mgr):
        """Test storing S3 credentials."""
        s3_creds = {
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        }

        vault_config_mgr.store_credentials("test-s3", "s3", s3_creds)

        retrieved = vault_config_mgr.get_credentials("test-s3", "s3")

        assert retrieved is not None
        assert retrieved["access_key_id"] == s3_creds["access_key_id"]
        assert retrieved["secret_access_key"] == s3_creds["secret_access_key"]

    def test_store_invalid_git_credentials(self, vault_config_mgr):
        """Test storing invalid Git credentials fails."""
        # Username without password
        with pytest.raises(ValueError, match="must include password"):
            vault_config_mgr.store_credentials(
                "test-git",
                "git",
                {"username": "testuser"},
            )

    def test_store_invalid_s3_credentials(self, vault_config_mgr):
        """Test storing invalid S3 credentials fails."""
        # Access key without secret key
        with pytest.raises(ValueError, match="must include secret_access_key"):
            vault_config_mgr.store_credentials(
                "test-s3",
                "s3",
                {"access_key_id": "AKIAIOSFODNN7EXAMPLE"},
            )

    def test_delete_credentials(self, vault_config_mgr):
        """Test deleting credentials."""
        # Store credentials
        creds = {"username": "testuser", "password": "testpass"}
        vault_config_mgr.store_credentials("test-vault", "git", creds)

        # Delete credentials
        assert vault_config_mgr.delete_credentials("test-vault", "git")

        # Verify they're gone
        assert vault_config_mgr.get_credentials("test-vault", "git") is None

    def test_delete_nonexistent_credentials(self, vault_config_mgr):
        """Test deleting nonexistent credentials returns False."""
        assert not vault_config_mgr.delete_credentials("nonexistent", "git")

    def test_get_vault_with_credentials(self, vault_config_mgr):
        """Test getting vault config with credentials merged."""
        # Add vault
        config = VaultConfig(
            name="test-git",
            type="git",
            config={"url": "git@github.com:test/vault.git"},
        )
        vault_config_mgr.add_vault(config)

        # Store credentials
        creds = {"username": "testuser", "password": "testpass"}
        vault_config_mgr.store_credentials("test-git", "git", creds)

        # Get vault with credentials
        vault = vault_config_mgr.get_vault_with_credentials("test-git")

        assert vault is not None
        assert vault.config["url"] == "git@github.com:test/vault.git"
        assert vault.config["username"] == "testuser"
        assert vault.config["password"] == "testpass"

    def test_get_vault_with_credentials_no_stored_creds(self, vault_config_mgr):
        """Test getting vault without stored credentials."""
        config = VaultConfig(
            name="test-vault",
            type="local",
            config={"path": "/tmp/vault"},
        )
        vault_config_mgr.add_vault(config)

        # Get vault (no credentials stored)
        vault = vault_config_mgr.get_vault_with_credentials("test-vault")

        assert vault is not None
        assert "username" not in vault.config

    def test_config_persistence(self, vault_config_mgr, temp_config_dir):
        """Test that configuration persists across instances."""
        # Add vault with first instance
        config = VaultConfig(
            name="persistent-vault",
            type="git",
            config={"url": "git@github.com:test/vault.git"},
        )
        vault_config_mgr.add_vault(config)

        # Create new instance
        new_mgr = VaultConfigManager(config_dir=temp_config_dir)

        # Verify vault exists
        vault = new_mgr.get_vault("persistent-vault")
        assert vault is not None
        assert vault.name == "persistent-vault"
