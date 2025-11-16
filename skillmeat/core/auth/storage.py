"""Token storage backends for SkillMeat authentication.

This module provides multiple storage backends for authentication tokens:
- KeychainStorage: Uses OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- EncryptedFileStorage: Encrypted file-based storage as fallback

All storage backends implement the TokenStorage interface.
"""

import json
import logging
import platform
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class TokenStorage(ABC):
    """Abstract base class for token storage backends."""

    @abstractmethod
    def store(self, token_id: str, token_data: str) -> None:
        """Store a token.

        Args:
            token_id: Unique identifier for the token
            token_data: Serialized token data (JSON string)

        Raises:
            StorageError: If storage operation fails
        """
        pass

    @abstractmethod
    def retrieve(self, token_id: str) -> Optional[str]:
        """Retrieve a token by ID.

        Args:
            token_id: Unique identifier for the token

        Returns:
            Serialized token data if found, None otherwise

        Raises:
            StorageError: If retrieval operation fails
        """
        pass

    @abstractmethod
    def delete(self, token_id: str) -> bool:
        """Delete a token by ID.

        Args:
            token_id: Unique identifier for the token

        Returns:
            True if token was deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        pass

    @abstractmethod
    def list_tokens(self) -> List[str]:
        """List all stored token IDs.

        Returns:
            List of token IDs

        Raises:
            StorageError: If listing operation fails
        """
        pass

    @abstractmethod
    def clear_all(self) -> int:
        """Delete all stored tokens.

        Returns:
            Number of tokens deleted

        Raises:
            StorageError: If clear operation fails
        """
        pass


class KeychainStorage(TokenStorage):
    """Token storage using OS keychain/credential manager.

    Uses:
    - macOS: Keychain
    - Windows: Credential Manager
    - Linux: Secret Service (GNOME Keyring, KWallet, etc.)

    Falls back to EncryptedFileStorage if keychain is unavailable.
    """

    SERVICE_NAME = "skillmeat-web-auth"

    def __init__(self):
        """Initialize keychain storage.

        Raises:
            ImportError: If keyring library is not available
        """
        try:
            import keyring
            from keyring.errors import KeyringError

            self.keyring = keyring
            self.KeyringError = KeyringError
            self._test_keychain()
            self.available = True
            logger.info(
                f"Keychain storage initialized (backend: {keyring.get_keyring()})"
            )
        except ImportError:
            logger.warning("Keyring library not available, storage will fail")
            self.available = False
            raise
        except Exception as e:
            logger.warning(f"Keychain not available: {e}")
            self.available = False
            raise

    def _test_keychain(self) -> None:
        """Test if keychain is accessible.

        Raises:
            Exception: If keychain is not accessible
        """
        test_key = f"{self.SERVICE_NAME}:test"
        try:
            # Try to set and get a test value
            self.keyring.set_password(self.SERVICE_NAME, test_key, "test")
            value = self.keyring.get_password(self.SERVICE_NAME, test_key)
            if value != "test":
                raise ValueError("Keychain test failed: value mismatch")
            self.keyring.delete_password(self.SERVICE_NAME, test_key)
        except Exception as e:
            raise Exception(f"Keychain not accessible: {e}")

    def _get_key_name(self, token_id: str) -> str:
        """Generate keychain key name for a token ID.

        Args:
            token_id: Token identifier

        Returns:
            Keychain key name
        """
        return f"token:{token_id}"

    def store(self, token_id: str, token_data: str) -> None:
        """Store a token in the keychain.

        Args:
            token_id: Unique identifier for the token
            token_data: Serialized token data (JSON string)

        Raises:
            StorageError: If storage operation fails
        """
        if not self.available:
            raise RuntimeError("Keychain storage not available")

        try:
            key_name = self._get_key_name(token_id)
            self.keyring.set_password(self.SERVICE_NAME, key_name, token_data)
            logger.debug(f"Token stored in keychain: {token_id[:8]}...")
        except self.KeyringError as e:
            raise RuntimeError(f"Failed to store token in keychain: {e}")

    def retrieve(self, token_id: str) -> Optional[str]:
        """Retrieve a token from the keychain.

        Args:
            token_id: Unique identifier for the token

        Returns:
            Serialized token data if found, None otherwise

        Raises:
            StorageError: If retrieval operation fails
        """
        if not self.available:
            raise RuntimeError("Keychain storage not available")

        try:
            key_name = self._get_key_name(token_id)
            token_data = self.keyring.get_password(self.SERVICE_NAME, key_name)
            if token_data:
                logger.debug(f"Token retrieved from keychain: {token_id[:8]}...")
            return token_data
        except self.KeyringError as e:
            raise RuntimeError(f"Failed to retrieve token from keychain: {e}")

    def delete(self, token_id: str) -> bool:
        """Delete a token from the keychain.

        Args:
            token_id: Unique identifier for the token

        Returns:
            True if token was deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        if not self.available:
            raise RuntimeError("Keychain storage not available")

        try:
            key_name = self._get_key_name(token_id)
            # Check if token exists first
            if self.keyring.get_password(self.SERVICE_NAME, key_name) is None:
                return False

            self.keyring.delete_password(self.SERVICE_NAME, key_name)
            logger.debug(f"Token deleted from keychain: {token_id[:8]}...")
            return True
        except self.KeyringError as e:
            raise RuntimeError(f"Failed to delete token from keychain: {e}")

    def list_tokens(self) -> List[str]:
        """List all stored token IDs.

        Note: Keychain doesn't provide a native way to list all keys,
        so we maintain an index in the keychain.

        Returns:
            List of token IDs

        Raises:
            StorageError: If listing operation fails
        """
        if not self.available:
            raise RuntimeError("Keychain storage not available")

        try:
            # Retrieve the token index
            index_data = self.keyring.get_password(self.SERVICE_NAME, "token:index")
            if not index_data:
                return []

            token_ids = json.loads(index_data)
            logger.debug(f"Listed {len(token_ids)} tokens from keychain")
            return token_ids
        except self.KeyringError as e:
            raise RuntimeError(f"Failed to list tokens from keychain: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted token index: {e}")
            return []

    def _update_index(self, token_ids: List[str]) -> None:
        """Update the token index in keychain.

        Args:
            token_ids: List of token IDs to store in index
        """
        try:
            index_data = json.dumps(token_ids)
            self.keyring.set_password(self.SERVICE_NAME, "token:index", index_data)
        except self.KeyringError as e:
            logger.error(f"Failed to update token index: {e}")

    def clear_all(self) -> int:
        """Delete all stored tokens.

        Returns:
            Number of tokens deleted

        Raises:
            StorageError: If clear operation fails
        """
        if not self.available:
            raise RuntimeError("Keychain storage not available")

        try:
            token_ids = self.list_tokens()
            count = 0

            for token_id in token_ids:
                try:
                    if self.delete(token_id):
                        count += 1
                except Exception as e:
                    logger.error(f"Failed to delete token {token_id}: {e}")

            # Clear the index
            try:
                self.keyring.delete_password(self.SERVICE_NAME, "token:index")
            except self.KeyringError:
                pass

            logger.info(f"Cleared {count} tokens from keychain")
            return count
        except Exception as e:
            raise RuntimeError(f"Failed to clear tokens from keychain: {e}")

    def store(self, token_id: str, token_data: str) -> None:
        """Store a token in the keychain and update index.

        Args:
            token_id: Unique identifier for the token
            token_data: Serialized token data (JSON string)
        """
        if not self.available:
            raise RuntimeError("Keychain storage not available")

        try:
            # Store the token
            key_name = self._get_key_name(token_id)
            self.keyring.set_password(self.SERVICE_NAME, key_name, token_data)

            # Update the index
            token_ids = self.list_tokens()
            if token_id not in token_ids:
                token_ids.append(token_id)
                self._update_index(token_ids)

            logger.debug(f"Token stored in keychain: {token_id[:8]}...")
        except self.KeyringError as e:
            raise RuntimeError(f"Failed to store token in keychain: {e}")

    def delete(self, token_id: str) -> bool:
        """Delete a token from the keychain and update index.

        Args:
            token_id: Unique identifier for the token

        Returns:
            True if token was deleted, False if not found
        """
        if not self.available:
            raise RuntimeError("Keychain storage not available")

        try:
            key_name = self._get_key_name(token_id)

            # Check if token exists
            if self.keyring.get_password(self.SERVICE_NAME, key_name) is None:
                return False

            # Delete the token
            self.keyring.delete_password(self.SERVICE_NAME, key_name)

            # Update the index
            token_ids = self.list_tokens()
            if token_id in token_ids:
                token_ids.remove(token_id)
                self._update_index(token_ids)

            logger.debug(f"Token deleted from keychain: {token_id[:8]}...")
            return True
        except self.KeyringError as e:
            raise RuntimeError(f"Failed to delete token from keychain: {e}")


class EncryptedFileStorage(TokenStorage):
    """Encrypted file-based token storage.

    Uses Fernet symmetric encryption with a key derived from a machine-specific
    seed. This provides at-rest encryption as a fallback when OS keychain is
    not available.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize encrypted file storage.

        Args:
            storage_dir: Directory to store encrypted tokens
                        (defaults to ~/.skillmeat/tokens)
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".skillmeat" / "tokens"

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate encryption key from machine-specific seed
        self.encryption_key = self._get_encryption_key()
        self.cipher = Fernet(self.encryption_key)

        logger.info(f"Encrypted file storage initialized at {self.storage_dir}")

    def _get_encryption_key(self) -> bytes:
        """Generate encryption key from machine-specific data.

        Returns:
            Fernet-compatible encryption key

        Note:
            This uses machine hostname and user info to generate a stable key.
            For production, consider using a user-provided passphrase.
        """
        # Use machine-specific data as seed
        seed = f"{platform.node()}-{Path.home()}-skillmeat-tokens"

        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"skillmeat-token-storage",  # Static salt for deterministic key
            iterations=100000,
        )
        key = kdf.derive(seed.encode())

        # Encode for Fernet
        import base64

        return base64.urlsafe_b64encode(key)

    def _get_token_path(self, token_id: str) -> Path:
        """Get file path for a token.

        Args:
            token_id: Token identifier

        Returns:
            Path to token file
        """
        # Use first 2 chars for directory sharding (prevents too many files in one dir)
        shard = token_id[:2] if len(token_id) >= 2 else "00"
        shard_dir = self.storage_dir / shard
        shard_dir.mkdir(exist_ok=True)
        return shard_dir / f"{token_id}.enc"

    def store(self, token_id: str, token_data: str) -> None:
        """Store an encrypted token to file.

        Args:
            token_id: Unique identifier for the token
            token_data: Serialized token data (JSON string)

        Raises:
            StorageError: If storage operation fails
        """
        try:
            # Encrypt the token data
            encrypted_data = self.cipher.encrypt(token_data.encode())

            # Write to file
            token_path = self._get_token_path(token_id)
            token_path.write_bytes(encrypted_data)

            logger.debug(f"Token stored to file: {token_id[:8]}...")
        except Exception as e:
            raise RuntimeError(f"Failed to store token to file: {e}")

    def retrieve(self, token_id: str) -> Optional[str]:
        """Retrieve and decrypt a token from file.

        Args:
            token_id: Unique identifier for the token

        Returns:
            Serialized token data if found, None otherwise

        Raises:
            StorageError: If retrieval operation fails
        """
        try:
            token_path = self._get_token_path(token_id)

            if not token_path.exists():
                return None

            # Read and decrypt
            encrypted_data = token_path.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)

            logger.debug(f"Token retrieved from file: {token_id[:8]}...")
            return decrypted_data.decode()
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve token from file: {e}")

    def delete(self, token_id: str) -> bool:
        """Delete a token file.

        Args:
            token_id: Unique identifier for the token

        Returns:
            True if token was deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        try:
            token_path = self._get_token_path(token_id)

            if not token_path.exists():
                return False

            token_path.unlink()
            logger.debug(f"Token deleted from file: {token_id[:8]}...")
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete token file: {e}")

    def list_tokens(self) -> List[str]:
        """List all stored token IDs.

        Returns:
            List of token IDs

        Raises:
            StorageError: If listing operation fails
        """
        try:
            token_ids = []

            # Scan all shard directories
            for shard_dir in self.storage_dir.iterdir():
                if not shard_dir.is_dir():
                    continue

                for token_file in shard_dir.glob("*.enc"):
                    # Extract token ID from filename
                    token_id = token_file.stem
                    token_ids.append(token_id)

            logger.debug(f"Listed {len(token_ids)} tokens from file storage")
            return token_ids
        except Exception as e:
            raise RuntimeError(f"Failed to list tokens from files: {e}")

    def clear_all(self) -> int:
        """Delete all stored tokens.

        Returns:
            Number of tokens deleted

        Raises:
            StorageError: If clear operation fails
        """
        try:
            token_ids = self.list_tokens()
            count = 0

            for token_id in token_ids:
                try:
                    if self.delete(token_id):
                        count += 1
                except Exception as e:
                    logger.error(f"Failed to delete token {token_id}: {e}")

            logger.info(f"Cleared {count} tokens from file storage")
            return count
        except Exception as e:
            raise RuntimeError(f"Failed to clear tokens from files: {e}")


def get_storage_backend(prefer_keychain: bool = True) -> TokenStorage:
    """Get the appropriate token storage backend.

    Tries to use KeychainStorage if available, falls back to EncryptedFileStorage.

    Args:
        prefer_keychain: Whether to prefer keychain storage if available

    Returns:
        TokenStorage instance
    """
    if prefer_keychain:
        try:
            return KeychainStorage()
        except Exception as e:
            logger.warning(f"Keychain storage not available, using file storage: {e}")

    return EncryptedFileStorage()
