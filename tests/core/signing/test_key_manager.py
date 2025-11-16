"""Tests for key manager."""

import pytest
from datetime import datetime
from pathlib import Path

from skillmeat.core.signing import KeyManager
from skillmeat.core.signing.storage import EncryptedFileKeyStorage


@pytest.fixture
def key_storage(tmp_path):
    """Create temporary key storage for testing."""
    storage_dir = tmp_path / "signing-keys"
    return EncryptedFileKeyStorage(storage_dir)


@pytest.fixture
def key_manager(key_storage):
    """Create key manager with test storage."""
    return KeyManager(storage=key_storage)


def test_generate_key_pair(key_manager):
    """Test Ed25519 key pair generation."""
    name = "Test User"
    email = "test@example.com"

    key_pair = key_manager.generate_key_pair(name, email)

    assert key_pair.name == name
    assert key_pair.email == email
    assert key_pair.key_id is not None
    assert key_pair.fingerprint is not None
    assert len(key_pair.fingerprint) == 64  # SHA256 hex digest
    assert key_pair.private_key is not None
    assert key_pair.public_key is not None


def test_store_and_load_key_pair(key_manager):
    """Test key pair storage and retrieval."""
    # Generate and store key pair
    key_pair = key_manager.generate_key_pair("Test User", "test@example.com")
    signing_key = key_manager.store_key_pair(key_pair)

    assert signing_key.key_id == key_pair.key_id
    assert signing_key.fingerprint == key_pair.fingerprint

    # Load key pair
    loaded_key_pair = key_manager.load_private_key(key_pair.key_id)

    assert loaded_key_pair is not None
    assert loaded_key_pair.key_id == key_pair.key_id
    assert loaded_key_pair.fingerprint == key_pair.fingerprint
    assert loaded_key_pair.name == key_pair.name
    assert loaded_key_pair.email == key_pair.email


def test_delete_private_key(key_manager):
    """Test private key deletion."""
    # Generate and store key pair
    key_pair = key_manager.generate_key_pair("Test User", "test@example.com")
    key_manager.store_key_pair(key_pair)

    # Delete key
    deleted = key_manager.delete_private_key(key_pair.key_id)

    assert deleted is True

    # Verify key is gone
    loaded_key_pair = key_manager.load_private_key(key_pair.key_id)
    assert loaded_key_pair is None


def test_list_signing_keys(key_manager):
    """Test listing signing keys."""
    # Initially empty
    keys = key_manager.list_signing_keys()
    assert len(keys) == 0

    # Generate and store keys
    key_pair1 = key_manager.generate_key_pair("User 1", "user1@example.com")
    key_manager.store_key_pair(key_pair1)

    key_pair2 = key_manager.generate_key_pair("User 2", "user2@example.com")
    key_manager.store_key_pair(key_pair2)

    # List keys
    keys = key_manager.list_signing_keys()

    assert len(keys) == 2
    assert any(k.key_id == key_pair1.key_id for k in keys)
    assert any(k.key_id == key_pair2.key_id for k in keys)


def test_import_public_key(key_manager):
    """Test public key import."""
    # Generate key pair and export public key
    key_pair = key_manager.generate_key_pair("Test User", "test@example.com")
    signing_key = key_manager.store_key_pair(key_pair)
    public_key_pem = signing_key.public_key_pem

    # Import public key as trusted
    public_key = key_manager.import_public_key(
        public_key_pem,
        "Test User",
        "test@example.com",
        trusted=True
    )

    assert public_key.key_id == key_pair.key_id
    assert public_key.fingerprint == key_pair.fingerprint
    assert public_key.trusted is True


def test_load_public_key_by_fingerprint(key_manager):
    """Test loading public key by full fingerprint."""
    # Generate and import public key
    key_pair = key_manager.generate_key_pair("Test User", "test@example.com")
    signing_key = key_manager.store_key_pair(key_pair)

    public_key = key_manager.import_public_key(
        signing_key.public_key_pem,
        "Test User",
        "test@example.com"
    )

    # Load by full fingerprint
    loaded_public_key = key_manager.load_public_key_by_fingerprint(key_pair.fingerprint)

    assert loaded_public_key is not None
    assert loaded_public_key.fingerprint == key_pair.fingerprint


def test_export_public_key(key_manager):
    """Test public key export."""
    # Generate and store key pair
    key_pair = key_manager.generate_key_pair("Test User", "test@example.com")
    key_manager.store_key_pair(key_pair)

    # Export public key
    public_key_pem = key_manager.export_public_key(key_pair.key_id)

    assert public_key_pem is not None
    assert "-----BEGIN PUBLIC KEY-----" in public_key_pem
    assert "-----END PUBLIC KEY-----" in public_key_pem


def test_invalid_key_generation(key_manager):
    """Test key generation with invalid inputs."""
    with pytest.raises(ValueError, match="name cannot be empty"):
        key_manager.generate_key_pair("", "test@example.com")

    with pytest.raises(ValueError, match="email cannot be empty"):
        key_manager.generate_key_pair("Test User", "")

    with pytest.raises(ValueError, match="Invalid email"):
        key_manager.generate_key_pair("Test User", "invalid-email")
