"""Tests for vault connector factory."""

import pytest

from skillmeat.core.sharing.vault.factory import VaultFactory, register_vault_connector
from skillmeat.core.sharing.vault.base import VaultConnector, VaultError
from skillmeat.core.sharing.vault.local_vault import LocalVaultConnector
from skillmeat.core.sharing.vault.git_vault import GitVaultConnector
from skillmeat.core.sharing.vault.s3_vault import S3VaultConnector


class TestVaultFactory:
    """Tests for VaultFactory."""

    def test_builtin_connectors_registered(self):
        """Test that builtin connectors are registered."""
        assert VaultFactory.is_registered("local")
        assert VaultFactory.is_registered("git")
        assert VaultFactory.is_registered("s3")

    def test_get_registered_types(self):
        """Test getting list of registered types."""
        types = VaultFactory.get_registered_types()

        assert "local" in types
        assert "git" in types
        assert "s3" in types

    def test_create_local_vault(self, tmp_path):
        """Test creating local vault connector."""
        config = {"path": str(tmp_path / "vault")}

        vault = VaultFactory.create(
            vault_id="test-local",
            vault_type="local",
            config=config,
        )

        assert isinstance(vault, LocalVaultConnector)
        assert vault.vault_id == "test-local"
        assert not vault.read_only

    def test_create_git_vault(self):
        """Test creating git vault connector."""
        config = {
            "url": "git@github.com:test/vault.git",
            "branch": "main",
        }

        vault = VaultFactory.create(
            vault_id="test-git",
            vault_type="git",
            config=config,
        )

        assert isinstance(vault, GitVaultConnector)
        assert vault.vault_id == "test-git"

    def test_create_s3_vault(self):
        """Test creating S3 vault connector (requires boto3)."""
        pytest.importorskip("boto3")

        config = {
            "bucket": "test-bucket",
            "region": "us-east-1",
        }

        vault = VaultFactory.create(
            vault_id="test-s3",
            vault_type="s3",
            config=config,
        )

        assert isinstance(vault, S3VaultConnector)
        assert vault.vault_id == "test-s3"

    def test_create_read_only_vault(self, tmp_path):
        """Test creating read-only vault."""
        config = {"path": str(tmp_path / "vault")}

        vault = VaultFactory.create(
            vault_id="test-local",
            vault_type="local",
            config=config,
            read_only=True,
        )

        assert vault.read_only

    def test_create_unknown_type(self):
        """Test creating vault with unknown type fails."""
        with pytest.raises(VaultError, match="Unknown vault type"):
            VaultFactory.create(
                vault_id="test",
                vault_type="unknown",
                config={},
            )

    def test_create_invalid_config(self):
        """Test creating vault with invalid config fails."""
        with pytest.raises(VaultError):
            VaultFactory.create(
                vault_id="test-local",
                vault_type="local",
                config={},  # Missing 'path'
            )

    def test_register_custom_connector(self):
        """Test registering custom vault connector."""

        class CustomVaultConnector(VaultConnector):
            """Custom vault connector for testing."""

            def authenticate(self):
                return True

            def push(self, bundle_path, bundle_metadata, bundle_hash, progress_callback=None):
                return "custom-bundle-id"

            def pull(self, bundle_id, destination, progress_callback=None):
                return destination / f"{bundle_id}.skillmeat-pack"

            def list(self, name_filter=None, tag_filter=None):
                return []

            def delete(self, bundle_id):
                return True

            def exists(self, bundle_id):
                return False

            def get_metadata(self, bundle_id):
                raise NotImplementedError()

        # Register custom connector
        VaultFactory.register("custom", CustomVaultConnector)

        # Verify it's registered
        assert VaultFactory.is_registered("custom")

        # Create instance
        vault = VaultFactory.create(
            vault_id="test-custom",
            vault_type="custom",
            config={},
        )

        assert isinstance(vault, CustomVaultConnector)

        # Cleanup
        VaultFactory.unregister("custom")

    def test_register_duplicate_type(self):
        """Test registering duplicate type fails."""
        with pytest.raises(ValueError, match="already registered"):
            VaultFactory.register("local", LocalVaultConnector)

    def test_register_invalid_class(self):
        """Test registering non-VaultConnector class fails."""

        class NotAVaultConnector:
            pass

        with pytest.raises(TypeError, match="must be a subclass"):
            VaultFactory.register("invalid", NotAVaultConnector)

    def test_unregister(self):
        """Test unregistering vault type."""

        # Register a temporary type
        class TempVaultConnector(VaultConnector):
            def authenticate(self):
                return True

            def push(self, *args, **kwargs):
                pass

            def pull(self, *args, **kwargs):
                pass

            def list(self, *args, **kwargs):
                return []

            def delete(self, *args, **kwargs):
                return True

            def exists(self, *args, **kwargs):
                return False

            def get_metadata(self, *args, **kwargs):
                pass

        VaultFactory.register("temp", TempVaultConnector)
        assert VaultFactory.is_registered("temp")

        # Unregister it
        VaultFactory.unregister("temp")
        assert not VaultFactory.is_registered("temp")

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent type fails."""
        with pytest.raises(KeyError, match="not registered"):
            VaultFactory.unregister("nonexistent")

    def test_register_vault_connector_convenience_function(self):
        """Test convenience function for registering connectors."""

        class AnotherCustomVaultConnector(VaultConnector):
            def authenticate(self):
                return True

            def push(self, *args, **kwargs):
                pass

            def pull(self, *args, **kwargs):
                pass

            def list(self, *args, **kwargs):
                return []

            def delete(self, *args, **kwargs):
                return True

            def exists(self, *args, **kwargs):
                return False

            def get_metadata(self, *args, **kwargs):
                pass

        # Use convenience function
        register_vault_connector("another-custom", AnotherCustomVaultConnector)

        assert VaultFactory.is_registered("another-custom")

        # Cleanup
        VaultFactory.unregister("another-custom")
