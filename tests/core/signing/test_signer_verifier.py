"""Tests for bundle signer and verifier."""

import pytest
from datetime import datetime

from skillmeat.core.signing import (
    KeyManager,
    BundleSigner,
    BundleVerifier,
    VerificationStatus,
)
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


@pytest.fixture
def signing_key_pair(key_manager):
    """Generate and store a test signing key pair."""
    key_pair = key_manager.generate_key_pair("Test Signer", "signer@example.com")
    key_manager.store_key_pair(key_pair)
    return key_pair


@pytest.fixture
def signer(key_manager):
    """Create bundle signer."""
    return BundleSigner(key_manager)


@pytest.fixture
def verifier(key_manager):
    """Create bundle verifier."""
    return BundleVerifier(key_manager)


def test_sign_bundle(signer, signing_key_pair):
    """Test bundle signing."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
    }

    signature_data = signer.sign_bundle(
        bundle_hash, manifest_data, signing_key_pair.key_id
    )

    assert signature_data.signature is not None
    assert signature_data.signer_name == "Test Signer"
    assert signature_data.signer_email == "signer@example.com"
    assert signature_data.key_fingerprint == signing_key_pair.fingerprint
    assert signature_data.algorithm == "Ed25519"
    assert isinstance(signature_data.signed_at, datetime)


def test_sign_bundle_with_default_key(signer, signing_key_pair):
    """Test bundle signing with default key."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
    }

    # Sign without specifying key_id (uses default)
    signature_data = signer.sign_bundle(bundle_hash, manifest_data)

    assert signature_data.signature is not None
    assert signature_data.key_fingerprint == signing_key_pair.fingerprint


def test_verify_valid_signature(signer, verifier, key_manager, signing_key_pair):
    """Test verification of valid signature."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
    }

    # Sign bundle
    signature_data = signer.sign_bundle(
        bundle_hash, manifest_data, signing_key_pair.key_id
    )

    # Add signature to manifest
    manifest_data["signature"] = signature_data.to_dict()

    # Import signer's public key as trusted
    signing_key = key_manager.list_signing_keys()[0]
    key_manager.import_public_key(
        signing_key.public_key_pem,
        "Test Signer",
        "signer@example.com",
        trusted=True,
    )

    # Verify signature
    result = verifier.verify_bundle(bundle_hash, manifest_data)

    assert result.valid is True
    assert result.status == VerificationStatus.VALID
    assert result.signer_trusted is True
    assert result.signature_data is not None


def test_verify_invalid_signature(signer, verifier, key_manager, signing_key_pair):
    """Test verification of invalid signature (tampered bundle)."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
    }

    # Sign bundle
    signature_data = signer.sign_bundle(
        bundle_hash, manifest_data, signing_key_pair.key_id
    )

    # Add signature to manifest
    manifest_data["signature"] = signature_data.to_dict()

    # Import signer's public key as trusted
    signing_key = key_manager.list_signing_keys()[0]
    key_manager.import_public_key(
        signing_key.public_key_pem,
        "Test Signer",
        "signer@example.com",
        trusted=True,
    )

    # Tamper with bundle (change hash)
    tampered_hash = "tampered123"

    # Verify signature (should fail)
    result = verifier.verify_bundle(tampered_hash, manifest_data)

    assert result.valid is False
    assert result.status == VerificationStatus.INVALID


def test_verify_unsigned_bundle(verifier):
    """Test verification of unsigned bundle."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
    }

    # Verify unsigned bundle (optional)
    result = verifier.verify_bundle(bundle_hash, manifest_data, require_signature=False)

    assert result.valid is True  # Valid when signature not required
    assert result.status == VerificationStatus.UNSIGNED
    assert result.signer_trusted is False

    # Verify unsigned bundle (required)
    result = verifier.verify_bundle(bundle_hash, manifest_data, require_signature=True)

    assert result.valid is False  # Invalid when signature required
    assert result.status == VerificationStatus.UNSIGNED


def test_verify_untrusted_key(signer, verifier, key_manager, signing_key_pair):
    """Test verification with untrusted key."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
    }

    # Sign bundle
    signature_data = signer.sign_bundle(
        bundle_hash, manifest_data, signing_key_pair.key_id
    )

    # Add signature to manifest
    manifest_data["signature"] = signature_data.to_dict()

    # Import signer's public key as UNTRUSTED
    signing_key = key_manager.list_signing_keys()[0]
    key_manager.import_public_key(
        signing_key.public_key_pem,
        "Test Signer",
        "signer@example.com",
        trusted=False,  # Not trusted
    )

    # Verify signature (should fail due to untrusted key)
    result = verifier.verify_bundle(bundle_hash, manifest_data)

    assert result.valid is False
    assert result.status == VerificationStatus.KEY_UNTRUSTED
    assert result.signer_trusted is False


def test_verify_key_not_found(signer, verifier, signing_key_pair):
    """Test verification when signer's key is not in trust store."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
    }

    # Sign bundle
    signature_data = signer.sign_bundle(
        bundle_hash, manifest_data, signing_key_pair.key_id
    )

    # Add signature to manifest
    manifest_data["signature"] = signature_data.to_dict()

    # Don't import signer's public key

    # Verify signature (should fail due to key not found)
    result = verifier.verify_bundle(bundle_hash, manifest_data)

    assert result.valid is False
    assert result.status == VerificationStatus.KEY_NOT_FOUND
    assert result.signer_trusted is False


def test_canonical_representation(signer):
    """Test canonical representation for deterministic signing."""
    bundle_hash = "abc123def456"
    manifest_data = {
        "bundle": {"name": "test-bundle", "version": "1.0.0"},
        "artifacts": [],
        "created_at": "2025-11-16T10:30:00Z",  # Should be removed
        "signature": {"signature": "old_sig"},  # Should be removed
    }

    # Prepare sign data
    sign_data = signer._prepare_sign_data(bundle_hash, manifest_data)

    # Verify non-canonical fields are removed
    import json
    sign_dict = json.loads(sign_data.decode())

    assert "created_at" not in str(sign_dict)
    assert "old_sig" not in str(sign_dict)
    assert "bundle_hash" in str(sign_dict)
