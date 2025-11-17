"""Tests for local vault connector."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.core.sharing.bundle import BundleMetadata
from skillmeat.core.sharing.vault.local_vault import LocalVaultConnector
from skillmeat.core.sharing.vault.base import (
    VaultError,
    VaultNotFoundError,
    VaultPermissionError,
)


@pytest.fixture
def temp_vault_dir(tmp_path):
    """Create temporary vault directory."""
    vault_dir = tmp_path / "test-vault"
    vault_dir.mkdir()
    return vault_dir


@pytest.fixture
def vault_config(temp_vault_dir):
    """Create vault configuration."""
    return {
        "path": str(temp_vault_dir),
    }


@pytest.fixture
def local_vault(vault_config):
    """Create local vault connector."""
    vault = LocalVaultConnector(
        vault_id="test-vault",
        config=vault_config,
        read_only=False,
    )
    return vault


@pytest.fixture
def sample_bundle_metadata():
    """Create sample bundle metadata."""
    return BundleMetadata(
        name="test-bundle",
        description="Test bundle for vault tests",
        author="Test Author",
        created_at=datetime.utcnow().isoformat(),
        version="1.0.0",
        license="MIT",
        tags=["test", "vault"],
    )


@pytest.fixture
def sample_bundle_file(tmp_path, sample_bundle_metadata):
    """Create a sample bundle file."""
    bundle_path = tmp_path / "test-bundle.skillmeat-pack"

    # Create a simple test bundle (just a text file for testing)
    bundle_path.write_text("Test bundle content")

    return bundle_path


class TestLocalVaultConnector:
    """Tests for LocalVaultConnector."""

    def test_init(self, vault_config):
        """Test vault initialization."""
        vault = LocalVaultConnector(
            vault_id="test-vault",
            config=vault_config,
            read_only=False,
        )

        assert vault.vault_id == "test-vault"
        assert vault.vault_path == Path(vault_config["path"]).expanduser().resolve()
        assert not vault.read_only

    def test_init_missing_path(self):
        """Test initialization fails without path."""
        with pytest.raises(ValueError, match="must contain 'path'"):
            LocalVaultConnector(
                vault_id="test-vault",
                config={},
                read_only=False,
            )

    def test_authenticate(self, local_vault):
        """Test authentication creates directory structure."""
        assert local_vault.authenticate()

        # Check directory structure was created
        assert local_vault.vault_path.exists()
        assert local_vault.bundles_dir.exists()
        assert local_vault.metadata_dir.exists()
        assert local_vault.index_path.exists()

    def test_authenticate_read_only_missing_dir(self, temp_vault_dir):
        """Test read-only authentication fails if directory doesn't exist."""
        # Remove the directory
        temp_vault_dir.rmdir()

        vault = LocalVaultConnector(
            vault_id="test-vault",
            config={"path": str(temp_vault_dir)},
            read_only=True,
        )

        with pytest.raises(VaultError, match="does not exist"):
            vault.authenticate()

    def test_push_bundle(self, local_vault, sample_bundle_file, sample_bundle_metadata):
        """Test pushing bundle to vault."""
        local_vault.authenticate()

        bundle_hash = "sha256:" + "a" * 64

        bundle_id = local_vault.push(
            sample_bundle_file,
            sample_bundle_metadata,
            bundle_hash,
        )

        # Check bundle was created
        assert bundle_id == "test-bundle-v1.0.0"

        bundle_path = local_vault.bundles_dir / f"{bundle_id}.skillmeat-pack"
        assert bundle_path.exists()

        # Check metadata was created
        metadata_path = local_vault.metadata_dir / f"{bundle_id}.json"
        assert metadata_path.exists()

        # Check index was updated
        index = local_vault._read_index()
        assert bundle_id in index

    def test_push_bundle_without_auth(self, local_vault, sample_bundle_file, sample_bundle_metadata):
        """Test pushing fails without authentication."""
        bundle_hash = "sha256:" + "a" * 64

        with pytest.raises(VaultError, match="Not authenticated"):
            local_vault.push(
                sample_bundle_file,
                sample_bundle_metadata,
                bundle_hash,
            )

    def test_push_bundle_read_only(self, vault_config, sample_bundle_file, sample_bundle_metadata):
        """Test pushing fails in read-only mode."""
        vault = LocalVaultConnector(
            vault_id="test-vault",
            config=vault_config,
            read_only=True,
        )
        vault.authenticate()

        bundle_hash = "sha256:" + "a" * 64

        with pytest.raises(VaultPermissionError, match="read-only"):
            vault.push(
                sample_bundle_file,
                sample_bundle_metadata,
                bundle_hash,
            )

    def test_pull_bundle(self, local_vault, sample_bundle_file, sample_bundle_metadata, tmp_path):
        """Test pulling bundle from vault."""
        local_vault.authenticate()

        # First push a bundle
        bundle_hash = "sha256:" + "a" * 64
        bundle_id = local_vault.push(
            sample_bundle_file,
            sample_bundle_metadata,
            bundle_hash,
        )

        # Now pull it
        destination = tmp_path / "downloads"
        pulled_path = local_vault.pull(bundle_id, destination)

        assert pulled_path.exists()
        assert pulled_path.name == f"{bundle_id}.skillmeat-pack"
        assert pulled_path.read_text() == sample_bundle_file.read_text()

    def test_pull_nonexistent_bundle(self, local_vault, tmp_path):
        """Test pulling nonexistent bundle fails."""
        local_vault.authenticate()

        destination = tmp_path / "downloads"

        with pytest.raises(VaultNotFoundError, match="not found"):
            local_vault.pull("nonexistent-bundle", destination)

    def test_list_bundles(self, local_vault, sample_bundle_file, tmp_path):
        """Test listing bundles in vault."""
        local_vault.authenticate()

        # Push multiple bundles
        for i in range(3):
            metadata = BundleMetadata(
                name=f"bundle-{i}",
                description=f"Test bundle {i}",
                author="Test Author",
                created_at=datetime.utcnow().isoformat(),
                version="1.0.0",
                tags=["test", f"tag-{i}"],
            )

            bundle_hash = "sha256:" + "a" * 64
            local_vault.push(sample_bundle_file, metadata, bundle_hash)

        # List all bundles
        bundles = local_vault.list()
        assert len(bundles) == 3

    def test_list_bundles_with_filter(self, local_vault, sample_bundle_file):
        """Test listing bundles with name filter."""
        local_vault.authenticate()

        # Push bundles with different names
        for name in ["frontend-app", "backend-api", "frontend-lib"]:
            metadata = BundleMetadata(
                name=name,
                description=f"Test {name}",
                author="Test Author",
                created_at=datetime.utcnow().isoformat(),
                version="1.0.0",
            )

            bundle_hash = "sha256:" + "a" * 64
            local_vault.push(sample_bundle_file, metadata, bundle_hash)

        # Filter by name
        bundles = local_vault.list(name_filter="frontend")
        assert len(bundles) == 2
        assert all("frontend" in b.name for b in bundles)

    def test_list_bundles_with_tag_filter(self, local_vault, sample_bundle_file):
        """Test listing bundles with tag filter."""
        local_vault.authenticate()

        # Push bundles with different tags
        for i, tags in enumerate([["python", "backend"], ["javascript", "frontend"], ["python", "cli"]]):
            metadata = BundleMetadata(
                name=f"bundle-{i}",
                description=f"Test bundle {i}",
                author="Test Author",
                created_at=datetime.utcnow().isoformat(),
                version="1.0.0",
                tags=tags,
            )

            bundle_hash = "sha256:" + "a" * 64
            local_vault.push(sample_bundle_file, metadata, bundle_hash)

        # Filter by tag
        bundles = local_vault.list(tag_filter=["python"])
        assert len(bundles) == 2

    def test_delete_bundle(self, local_vault, sample_bundle_file, sample_bundle_metadata):
        """Test deleting bundle from vault."""
        local_vault.authenticate()

        # Push a bundle
        bundle_hash = "sha256:" + "a" * 64
        bundle_id = local_vault.push(
            sample_bundle_file,
            sample_bundle_metadata,
            bundle_hash,
        )

        # Delete it
        assert local_vault.delete(bundle_id)

        # Verify it's gone
        assert not local_vault.exists(bundle_id)

        # Check files were removed
        bundle_path = local_vault.bundles_dir / f"{bundle_id}.skillmeat-pack"
        assert not bundle_path.exists()

    def test_delete_nonexistent_bundle(self, local_vault):
        """Test deleting nonexistent bundle returns False."""
        local_vault.authenticate()

        assert not local_vault.delete("nonexistent-bundle")

    def test_exists(self, local_vault, sample_bundle_file, sample_bundle_metadata):
        """Test checking bundle existence."""
        local_vault.authenticate()

        bundle_hash = "sha256:" + "a" * 64
        bundle_id = local_vault.push(
            sample_bundle_file,
            sample_bundle_metadata,
            bundle_hash,
        )

        assert local_vault.exists(bundle_id)
        assert not local_vault.exists("nonexistent-bundle")

    def test_get_metadata(self, local_vault, sample_bundle_file, sample_bundle_metadata):
        """Test getting bundle metadata."""
        local_vault.authenticate()

        bundle_hash = "sha256:" + "a" * 64
        bundle_id = local_vault.push(
            sample_bundle_file,
            sample_bundle_metadata,
            bundle_hash,
        )

        metadata = local_vault.get_metadata(bundle_id)

        assert metadata.bundle_id == bundle_id
        assert metadata.name == sample_bundle_metadata.name
        assert metadata.version == sample_bundle_metadata.version
        assert metadata.description == sample_bundle_metadata.description
        assert metadata.author == sample_bundle_metadata.author

    def test_get_metadata_nonexistent(self, local_vault):
        """Test getting metadata for nonexistent bundle fails."""
        local_vault.authenticate()

        with pytest.raises(VaultNotFoundError):
            local_vault.get_metadata("nonexistent-bundle")

    def test_progress_callback(self, local_vault, sample_bundle_file, sample_bundle_metadata, tmp_path):
        """Test progress callback during push/pull."""
        local_vault.authenticate()

        progress_calls = []

        def progress_callback(info):
            progress_calls.append(info)

        # Push with progress
        bundle_hash = "sha256:" + "a" * 64
        bundle_id = local_vault.push(
            sample_bundle_file,
            sample_bundle_metadata,
            bundle_hash,
            progress_callback=progress_callback,
        )

        # Should have received progress updates
        assert len(progress_calls) >= 2  # At least start and end

        # Pull with progress
        progress_calls.clear()
        destination = tmp_path / "downloads"
        local_vault.pull(bundle_id, destination, progress_callback=progress_callback)

        assert len(progress_calls) >= 2

    def test_bundle_id_generation(self, local_vault):
        """Test bundle ID generation."""
        bundle_id = local_vault._generate_bundle_id("My Test Bundle", "1.2.3")
        assert bundle_id == "my-test-bundle-v1.2.3"

        # Test special characters
        bundle_id = local_vault._generate_bundle_id("Test@Bundle!", "2.0.0")
        assert bundle_id == "test@bundle!-v2.0.0"
