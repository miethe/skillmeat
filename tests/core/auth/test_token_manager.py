"""Tests for token manager functionality."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest

from skillmeat.core.auth import TokenManager
from skillmeat.core.auth.storage import EncryptedFileStorage, TokenStorage


class MockStorage(TokenStorage):
    """In-memory token storage for testing."""

    def __init__(self):
        self.tokens = {}

    def store(self, token_id: str, token_data: str) -> None:
        self.tokens[token_id] = token_data

    def retrieve(self, token_id: str) -> str:
        return self.tokens.get(token_id)

    def delete(self, token_id: str) -> bool:
        if token_id in self.tokens:
            del self.tokens[token_id]
            return True
        return False

    def list_tokens(self) -> list:
        return list(self.tokens.keys())

    def clear_all(self) -> int:
        count = len(self.tokens)
        self.tokens.clear()
        return count


@pytest.fixture
def mock_storage():
    """Create mock storage for testing."""
    return MockStorage()


@pytest.fixture
def token_manager(mock_storage):
    """Create token manager with mock storage."""
    return TokenManager(storage=mock_storage, secret_key="test-secret-key")


def test_generate_token_basic(token_manager):
    """Test basic token generation."""
    token = token_manager.generate_token(name="test-token")

    assert token.name == "test-token"
    assert token.token_id is not None
    assert token.token is not None
    assert token.created_at is not None
    assert isinstance(token.created_at, datetime)


def test_generate_token_with_expiration(token_manager):
    """Test token generation with expiration."""
    token = token_manager.generate_token(name="test-token", expiration_days=30)

    assert token.expires_at is not None
    # Should expire in approximately 30 days
    delta = token.expires_at - token.created_at
    assert 29 <= delta.days <= 30


def test_generate_token_no_expiration(token_manager):
    """Test token generation without expiration."""
    token = token_manager.generate_token(name="test-token", expiration_days=0)

    assert token.expires_at is None


def test_generate_token_empty_name_fails(token_manager):
    """Test that empty name raises error."""
    with pytest.raises(ValueError, match="Token name cannot be empty"):
        token_manager.generate_token(name="")


def test_validate_token_success(token_manager):
    """Test successful token validation."""
    token = token_manager.generate_token(name="test-token")

    assert token_manager.validate_token(token.token) is True


def test_validate_token_invalid_signature(token_manager):
    """Test validation fails with invalid signature."""
    token = token_manager.generate_token(name="test-token")

    # Tamper with the token
    tampered_token = token.token[:-10] + "tampered00"

    assert token_manager.validate_token(tampered_token) is False


def test_validate_token_expired(token_manager, mock_storage):
    """Test validation fails for expired token."""
    # Generate token with immediate expiration
    token = token_manager.generate_token(name="test-token", expiration_days=0)

    # Manually create an expired token
    past_time = datetime.utcnow() - timedelta(days=1)
    claims = {
        "sub": "skillmeat-web",
        "jti": token.token_id,
        "name": "test-token",
        "iat": int(past_time.timestamp()),
        "exp": int(past_time.timestamp()) + 1,  # Expired 1 second after creation
    }

    expired_token = jwt.encode(claims, token_manager.secret_key, algorithm="HS256")

    assert token_manager.validate_token(expired_token) is False


def test_validate_token_not_in_storage(token_manager):
    """Test validation fails if token not in storage."""
    # Create token with different manager
    other_manager = TokenManager(storage=MockStorage(), secret_key="test-secret-key")
    token = other_manager.generate_token(name="other-token")

    # Try to validate with first manager (token not in its storage)
    assert token_manager.validate_token(token.token) is False


def test_revoke_token(token_manager):
    """Test token revocation."""
    token = token_manager.generate_token(name="test-token")

    # Verify token works
    assert token_manager.validate_token(token.token) is True

    # Revoke token
    assert token_manager.revoke_token(token.token_id) is True

    # Verify token no longer works
    assert token_manager.validate_token(token.token) is False


def test_revoke_token_by_name(token_manager):
    """Test revoking tokens by name."""
    token1 = token_manager.generate_token(name="test-token")
    token2 = token_manager.generate_token(name="test-token")
    token3 = token_manager.generate_token(name="other-token")

    # Revoke all tokens with name "test-token"
    count = token_manager.revoke_token_by_name("test-token")

    assert count == 2
    assert token_manager.validate_token(token1.token) is False
    assert token_manager.validate_token(token2.token) is False
    assert token_manager.validate_token(token3.token) is True


def test_list_tokens(token_manager):
    """Test listing tokens."""
    token1 = token_manager.generate_token(name="token1")
    token2 = token_manager.generate_token(name="token2")

    tokens = token_manager.list_tokens()

    assert len(tokens) == 2
    token_names = {t.name for t in tokens}
    assert token_names == {"token1", "token2"}


def test_list_tokens_exclude_expired(token_manager, mock_storage):
    """Test listing tokens excludes expired by default."""
    # Create active token
    token1 = token_manager.generate_token(name="active", expiration_days=30)

    # Create expired token metadata manually
    expired_id = "expired-token-id"
    past_time = datetime.utcnow() - timedelta(days=1)
    expired_metadata = {
        "token_id": expired_id,
        "name": "expired",
        "created_at": past_time.isoformat(),
        "expires_at": past_time.isoformat(),
        "last_used": None,
    }
    mock_storage.store(expired_id, json.dumps(expired_metadata))

    # List without expired
    tokens = token_manager.list_tokens(include_expired=False)
    assert len(tokens) == 1
    assert tokens[0].name == "active"

    # List with expired
    tokens = token_manager.list_tokens(include_expired=True)
    assert len(tokens) == 2


def test_get_token_info(token_manager):
    """Test getting token information."""
    token = token_manager.generate_token(name="test-token", expiration_days=30)

    info = token_manager.get_token_info(token.token_id)

    assert info is not None
    assert info.name == "test-token"
    assert info.token_id == token.token_id
    assert info.created_at == token.created_at
    assert info.expires_at is not None
    assert info.is_expired is False


def test_cleanup_expired_tokens(token_manager, mock_storage):
    """Test cleaning up expired tokens."""
    # Create active token
    token1 = token_manager.generate_token(name="active", expiration_days=30)

    # Create expired token metadata manually
    expired_id = "expired-token-id"
    past_time = datetime.utcnow() - timedelta(days=1)
    expired_metadata = {
        "token_id": expired_id,
        "name": "expired",
        "created_at": past_time.isoformat(),
        "expires_at": past_time.isoformat(),
        "last_used": None,
    }
    mock_storage.store(expired_id, json.dumps(expired_metadata))

    # Cleanup
    count = token_manager.cleanup_expired_tokens()

    assert count == 1

    # Verify only active token remains
    tokens = token_manager.list_tokens()
    assert len(tokens) == 1
    assert tokens[0].name == "active"


def test_revoke_all_tokens(token_manager):
    """Test revoking all tokens."""
    token_manager.generate_token(name="token1")
    token_manager.generate_token(name="token2")
    token_manager.generate_token(name="token3")

    count = token_manager.revoke_all_tokens()

    assert count == 3
    assert len(token_manager.list_tokens()) == 0


def test_get_token_claims(token_manager):
    """Test extracting token claims."""
    token = token_manager.generate_token(
        name="test-token", custom_claims={"custom": "value"}
    )

    claims = token_manager.get_token_claims(token.token)

    assert claims is not None
    assert claims["name"] == "test-token"
    assert claims["custom"] == "value"
    assert claims["sub"] == "skillmeat-web"


def test_token_update_last_used(token_manager):
    """Test that token validation updates last_used."""
    token = token_manager.generate_token(name="test-token")

    # Initially last_used is None
    info = token_manager.get_token_info(token.token_id)
    assert info.last_used is None

    # Validate token (should update last_used)
    time.sleep(0.1)  # Small delay to ensure different timestamp
    token_manager.validate_token(token.token, update_last_used=True)

    # Check last_used is now set
    info = token_manager.get_token_info(token.token_id)
    assert info.last_used is not None


def test_encrypted_file_storage(tmp_path):
    """Test encrypted file storage backend."""
    storage_dir = tmp_path / "tokens"
    storage = EncryptedFileStorage(storage_dir=storage_dir)

    # Store token
    token_data = json.dumps({"test": "data"})
    storage.store("test-token-id", token_data)

    # Verify file was created and is encrypted
    token_files = list(storage_dir.rglob("*.enc"))
    assert len(token_files) == 1

    # Verify we can't read it without decryption
    raw_content = token_files[0].read_bytes()
    assert b"test" not in raw_content  # Should be encrypted

    # Retrieve token
    retrieved = storage.retrieve("test-token-id")
    assert retrieved == token_data

    # List tokens
    tokens = storage.list_tokens()
    assert "test-token-id" in tokens

    # Delete token
    assert storage.delete("test-token-id") is True
    assert storage.retrieve("test-token-id") is None


def test_secret_key_persistence(tmp_path):
    """Test that secret key is persisted and reused."""
    storage_dir = tmp_path / "tokens"
    storage1 = EncryptedFileStorage(storage_dir=storage_dir)

    manager1 = TokenManager(storage=storage1)
    secret1 = manager1.secret_key

    # Create new manager with same storage
    manager2 = TokenManager(storage=storage1)
    secret2 = manager2.secret_key

    # Should be the same secret key
    assert secret1 == secret2


def test_rotate_secret_key(token_manager):
    """Test secret key rotation."""
    # Generate token with old key
    token = token_manager.generate_token(name="test-token")

    # Verify it works
    assert token_manager.validate_token(token.token) is True

    # Rotate secret key
    old_key = token_manager.secret_key
    new_key = token_manager.rotate_secret_key()

    assert new_key != old_key
    assert token_manager.secret_key == new_key

    # Old token should no longer validate
    assert token_manager.validate_token(token.token) is False


@pytest.mark.skipif(
    not hasattr(pytest, "mark") or not pytest.importorskip("keyring", minversion=None),
    reason="keyring library not available",
)
def test_keychain_storage_fallback():
    """Test that keychain storage falls back to file storage if unavailable."""
    from skillmeat.core.auth.storage import get_storage_backend

    # This should succeed even if keychain is unavailable
    storage = get_storage_backend(prefer_keychain=True)
    assert storage is not None


def test_token_json_output():
    """Test token serialization to JSON."""
    manager = TokenManager(storage=MockStorage(), secret_key="test-secret")
    token = manager.generate_token(name="test", expiration_days=30)

    # Test TokenInfo JSON serialization
    info = manager.get_token_info(token.token_id)
    info_dict = info.model_dump()

    assert "token_id" in info_dict
    assert "name" in info_dict
    assert "created_at" in info_dict
    assert "expires_at" in info_dict
    assert "is_expired" in info_dict
