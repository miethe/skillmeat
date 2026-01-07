"""Key storage backends for signing keys.

This module provides storage backends for Ed25519 signing keys, integrating
with the existing token storage infrastructure from skillmeat.core.auth.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class KeyStorageError(Exception):
    """Raised when key storage operations fail."""

    pass


class KeyStorage(ABC):
    """Abstract base class for key storage backends."""

    @abstractmethod
    def store_private_key(
        self, key_id: str, private_key_pem: bytes, metadata: Dict
    ) -> None:
        """Store a private signing key.

        Args:
            key_id: Unique key identifier
            private_key_pem: PEM-encoded private key
            metadata: Key metadata (name, email, created_at, etc.)

        Raises:
            KeyStorageError: If storage operation fails
        """
        pass

    @abstractmethod
    def retrieve_private_key(self, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve a private signing key.

        Args:
            key_id: Key identifier

        Returns:
            Tuple of (private_key_pem, metadata) or None if not found

        Raises:
            KeyStorageError: If retrieval operation fails
        """
        pass

    @abstractmethod
    def delete_private_key(self, key_id: str) -> bool:
        """Delete a private signing key.

        Args:
            key_id: Key identifier

        Returns:
            True if key was deleted, False if not found

        Raises:
            KeyStorageError: If deletion operation fails
        """
        pass

    @abstractmethod
    def store_public_key(
        self, key_id: str, public_key_pem: bytes, metadata: Dict
    ) -> None:
        """Store a trusted public key.

        Args:
            key_id: Unique key identifier (typically fingerprint)
            public_key_pem: PEM-encoded public key
            metadata: Key metadata (name, email, imported_at, etc.)

        Raises:
            KeyStorageError: If storage operation fails
        """
        pass

    @abstractmethod
    def retrieve_public_key(self, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve a trusted public key.

        Args:
            key_id: Key identifier

        Returns:
            Tuple of (public_key_pem, metadata) or None if not found

        Raises:
            KeyStorageError: If retrieval operation fails
        """
        pass

    @abstractmethod
    def delete_public_key(self, key_id: str) -> bool:
        """Delete a trusted public key.

        Args:
            key_id: Key identifier

        Returns:
            True if key was deleted, False if not found

        Raises:
            KeyStorageError: If deletion operation fails
        """
        pass

    @abstractmethod
    def list_private_keys(self) -> List[str]:
        """List all private key IDs.

        Returns:
            List of key IDs

        Raises:
            KeyStorageError: If listing operation fails
        """
        pass

    @abstractmethod
    def list_public_keys(self) -> List[str]:
        """List all trusted public key IDs.

        Returns:
            List of key IDs

        Raises:
            KeyStorageError: If listing operation fails
        """
        pass


class KeychainKeyStorage(KeyStorage):
    """Key storage using OS keychain/credential manager.

    Uses the same underlying keychain infrastructure as TokenStorage
    but with a separate service name for signing keys.
    """

    SERVICE_NAME = "skillmeat-signing-keys"

    def __init__(self):
        """Initialize keychain key storage.

        Raises:
            KeyStorageError: If keychain is not available
        """
        try:
            import keyring
            from keyring.errors import KeyringError

            self.keyring = keyring
            self.KeyringError = KeyringError
            self._test_keychain()
            self.available = True
            logger.info(
                f"Keychain key storage initialized (backend: {keyring.get_keyring()})"
            )
        except ImportError as e:
            logger.warning("Keyring library not available")
            self.available = False
            raise KeyStorageError(f"Keyring library not available: {e}")
        except Exception as e:
            logger.warning(f"Keychain not available: {e}")
            self.available = False
            raise KeyStorageError(f"Keychain not available: {e}")

    def _test_keychain(self) -> None:
        """Test if keychain is accessible."""
        test_key = f"{self.SERVICE_NAME}:test"
        try:
            self.keyring.set_password(self.SERVICE_NAME, test_key, "test")
            value = self.keyring.get_password(self.SERVICE_NAME, test_key)
            if value != "test":
                raise ValueError("Keychain test failed: value mismatch")
            self.keyring.delete_password(self.SERVICE_NAME, test_key)
        except Exception as e:
            raise Exception(f"Keychain not accessible: {e}")

    def _get_key_name(self, prefix: str, key_id: str) -> str:
        """Generate keychain key name.

        Args:
            prefix: Key prefix (private or public)
            key_id: Key identifier

        Returns:
            Keychain key name
        """
        return f"{prefix}:{key_id}"

    def _store_key(
        self, prefix: str, key_id: str, key_pem: bytes, metadata: Dict
    ) -> None:
        """Store a key in keychain.

        Args:
            prefix: Key prefix (private or public)
            key_id: Key identifier
            key_pem: PEM-encoded key
            metadata: Key metadata
        """
        if not self.available:
            raise KeyStorageError("Keychain storage not available")

        try:
            # Combine key and metadata
            key_data = {
                "pem": key_pem.decode("utf-8"),
                "metadata": metadata,
            }
            key_json = json.dumps(key_data)

            # Store in keychain
            key_name = self._get_key_name(prefix, key_id)
            self.keyring.set_password(self.SERVICE_NAME, key_name, key_json)

            # Update index
            self._update_index(prefix, key_id, add=True)

            logger.debug(f"Stored {prefix} key in keychain: {key_id[:8]}...")
        except self.KeyringError as e:
            raise KeyStorageError(f"Failed to store key in keychain: {e}")

    def _retrieve_key(self, prefix: str, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve a key from keychain.

        Args:
            prefix: Key prefix (private or public)
            key_id: Key identifier

        Returns:
            Tuple of (key_pem, metadata) or None if not found
        """
        if not self.available:
            raise KeyStorageError("Keychain storage not available")

        try:
            key_name = self._get_key_name(prefix, key_id)
            key_json = self.keyring.get_password(self.SERVICE_NAME, key_name)

            if not key_json:
                return None

            key_data = json.loads(key_json)
            key_pem = key_data["pem"].encode("utf-8")
            metadata = key_data["metadata"]

            logger.debug(f"Retrieved {prefix} key from keychain: {key_id[:8]}...")
            return key_pem, metadata
        except self.KeyringError as e:
            raise KeyStorageError(f"Failed to retrieve key from keychain: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Corrupted key data for {key_id}: {e}")
            return None

    def _delete_key(self, prefix: str, key_id: str) -> bool:
        """Delete a key from keychain.

        Args:
            prefix: Key prefix (private or public)
            key_id: Key identifier

        Returns:
            True if key was deleted, False if not found
        """
        if not self.available:
            raise KeyStorageError("Keychain storage not available")

        try:
            key_name = self._get_key_name(prefix, key_id)

            # Check if exists
            if self.keyring.get_password(self.SERVICE_NAME, key_name) is None:
                return False

            # Delete from keychain
            self.keyring.delete_password(self.SERVICE_NAME, key_name)

            # Update index
            self._update_index(prefix, key_id, add=False)

            logger.debug(f"Deleted {prefix} key from keychain: {key_id[:8]}...")
            return True
        except self.KeyringError as e:
            raise KeyStorageError(f"Failed to delete key from keychain: {e}")

    def _list_keys(self, prefix: str) -> List[str]:
        """List all keys of a specific type.

        Args:
            prefix: Key prefix (private or public)

        Returns:
            List of key IDs
        """
        if not self.available:
            raise KeyStorageError("Keychain storage not available")

        try:
            index_name = f"{prefix}:index"
            index_json = self.keyring.get_password(self.SERVICE_NAME, index_name)

            if not index_json:
                return []

            key_ids = json.loads(index_json)
            logger.debug(f"Listed {len(key_ids)} {prefix} keys from keychain")
            return key_ids
        except self.KeyringError as e:
            raise KeyStorageError(f"Failed to list keys from keychain: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted key index: {e}")
            return []

    def _update_index(self, prefix: str, key_id: str, add: bool) -> None:
        """Update the key index in keychain.

        Args:
            prefix: Key prefix (private or public)
            key_id: Key identifier
            add: True to add, False to remove
        """
        try:
            key_ids = self._list_keys(prefix)

            if add:
                if key_id not in key_ids:
                    key_ids.append(key_id)
            else:
                if key_id in key_ids:
                    key_ids.remove(key_id)

            index_name = f"{prefix}:index"
            index_json = json.dumps(key_ids)
            self.keyring.set_password(self.SERVICE_NAME, index_name, index_json)
        except self.KeyringError as e:
            logger.error(f"Failed to update key index: {e}")

    # Public API methods

    def store_private_key(
        self, key_id: str, private_key_pem: bytes, metadata: Dict
    ) -> None:
        """Store a private signing key."""
        self._store_key("private", key_id, private_key_pem, metadata)

    def retrieve_private_key(self, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve a private signing key."""
        return self._retrieve_key("private", key_id)

    def delete_private_key(self, key_id: str) -> bool:
        """Delete a private signing key."""
        return self._delete_key("private", key_id)

    def store_public_key(
        self, key_id: str, public_key_pem: bytes, metadata: Dict
    ) -> None:
        """Store a trusted public key."""
        self._store_key("public", key_id, public_key_pem, metadata)

    def retrieve_public_key(self, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve a trusted public key."""
        return self._retrieve_key("public", key_id)

    def delete_public_key(self, key_id: str) -> bool:
        """Delete a trusted public key."""
        return self._delete_key("public", key_id)

    def list_private_keys(self) -> List[str]:
        """List all private key IDs."""
        return self._list_keys("private")

    def list_public_keys(self) -> List[str]:
        """List all trusted public key IDs."""
        return self._list_keys("public")


class EncryptedFileKeyStorage(KeyStorage):
    """Encrypted file-based key storage.

    Uses Fernet encryption with a machine-specific key as fallback
    when OS keychain is not available.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize encrypted file key storage.

        Args:
            storage_dir: Directory to store encrypted keys
                        (defaults to ~/.skillmeat/signing-keys)
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".skillmeat" / "signing-keys"

        self.storage_dir = storage_dir
        self.private_keys_dir = storage_dir / "private"
        self.public_keys_dir = storage_dir / "public"

        self.private_keys_dir.mkdir(parents=True, exist_ok=True)
        self.public_keys_dir.mkdir(parents=True, exist_ok=True)

        # Generate encryption key
        self.encryption_key = self._get_encryption_key()
        self.cipher = Fernet(self.encryption_key)

        logger.info(f"Encrypted file key storage initialized at {self.storage_dir}")

    def _get_encryption_key(self) -> bytes:
        """Generate encryption key from machine-specific data.

        Returns:
            Fernet-compatible encryption key
        """
        import platform

        # Use machine-specific data as seed
        seed = f"{platform.node()}-{Path.home()}-skillmeat-signing-keys"

        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"skillmeat-signing-key-storage",
            iterations=100000,
        )
        key = kdf.derive(seed.encode())

        # Encode for Fernet
        import base64

        return base64.urlsafe_b64encode(key)

    def _get_key_path(self, key_type: str, key_id: str) -> Path:
        """Get file path for a key.

        Args:
            key_type: "private" or "public"
            key_id: Key identifier

        Returns:
            Path to key file
        """
        base_dir = (
            self.private_keys_dir if key_type == "private" else self.public_keys_dir
        )

        # Use first 2 chars for directory sharding
        shard = key_id[:2] if len(key_id) >= 2 else "00"
        shard_dir = base_dir / shard
        shard_dir.mkdir(exist_ok=True)

        return shard_dir / f"{key_id}.enc"

    def _store_key(
        self, key_type: str, key_id: str, key_pem: bytes, metadata: Dict
    ) -> None:
        """Store an encrypted key to file.

        Args:
            key_type: "private" or "public"
            key_id: Key identifier
            key_pem: PEM-encoded key
            metadata: Key metadata
        """
        try:
            # Combine key and metadata
            key_data = {
                "pem": key_pem.decode("utf-8"),
                "metadata": metadata,
            }
            key_json = json.dumps(key_data)

            # Encrypt the data
            encrypted_data = self.cipher.encrypt(key_json.encode())

            # Write to file
            key_path = self._get_key_path(key_type, key_id)
            key_path.write_bytes(encrypted_data)

            logger.debug(f"Stored {key_type} key to file: {key_id[:8]}...")
        except Exception as e:
            raise KeyStorageError(f"Failed to store key to file: {e}")

    def _retrieve_key(self, key_type: str, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve and decrypt a key from file.

        Args:
            key_type: "private" or "public"
            key_id: Key identifier

        Returns:
            Tuple of (key_pem, metadata) or None if not found
        """
        try:
            key_path = self._get_key_path(key_type, key_id)

            if not key_path.exists():
                return None

            # Read and decrypt
            encrypted_data = key_path.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)

            # Parse JSON
            key_data = json.loads(decrypted_data.decode())
            key_pem = key_data["pem"].encode("utf-8")
            metadata = key_data["metadata"]

            logger.debug(f"Retrieved {key_type} key from file: {key_id[:8]}...")
            return key_pem, metadata
        except Exception as e:
            raise KeyStorageError(f"Failed to retrieve key from file: {e}")

    def _delete_key(self, key_type: str, key_id: str) -> bool:
        """Delete a key file.

        Args:
            key_type: "private" or "public"
            key_id: Key identifier

        Returns:
            True if key was deleted, False if not found
        """
        try:
            key_path = self._get_key_path(key_type, key_id)

            if not key_path.exists():
                return False

            key_path.unlink()
            logger.debug(f"Deleted {key_type} key from file: {key_id[:8]}...")
            return True
        except Exception as e:
            raise KeyStorageError(f"Failed to delete key file: {e}")

    def _list_keys(self, key_type: str) -> List[str]:
        """List all keys of a specific type.

        Args:
            key_type: "private" or "public"

        Returns:
            List of key IDs
        """
        try:
            base_dir = (
                self.private_keys_dir if key_type == "private" else self.public_keys_dir
            )
            key_ids = []

            # Scan all shard directories
            for shard_dir in base_dir.iterdir():
                if not shard_dir.is_dir():
                    continue

                for key_file in shard_dir.glob("*.enc"):
                    key_id = key_file.stem
                    key_ids.append(key_id)

            logger.debug(f"Listed {len(key_ids)} {key_type} keys from file storage")
            return key_ids
        except Exception as e:
            raise KeyStorageError(f"Failed to list keys from files: {e}")

    # Public API methods

    def store_private_key(
        self, key_id: str, private_key_pem: bytes, metadata: Dict
    ) -> None:
        """Store a private signing key."""
        self._store_key("private", key_id, private_key_pem, metadata)

    def retrieve_private_key(self, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve a private signing key."""
        return self._retrieve_key("private", key_id)

    def delete_private_key(self, key_id: str) -> bool:
        """Delete a private signing key."""
        return self._delete_key("private", key_id)

    def store_public_key(
        self, key_id: str, public_key_pem: bytes, metadata: Dict
    ) -> None:
        """Store a trusted public key."""
        self._store_key("public", key_id, public_key_pem, metadata)

    def retrieve_public_key(self, key_id: str) -> Optional[tuple[bytes, Dict]]:
        """Retrieve a trusted public key."""
        return self._retrieve_key("public", key_id)

    def delete_public_key(self, key_id: str) -> bool:
        """Delete a trusted public key."""
        return self._delete_key("public", key_id)

    def list_private_keys(self) -> List[str]:
        """List all private key IDs."""
        return self._list_keys("private")

    def list_public_keys(self) -> List[str]:
        """List all trusted public key IDs."""
        return self._list_keys("public")


def get_key_storage_backend(prefer_keychain: bool = True) -> KeyStorage:
    """Get the appropriate key storage backend.

    Tries to use KeychainKeyStorage if available, falls back to EncryptedFileKeyStorage.

    Args:
        prefer_keychain: Whether to prefer keychain storage if available

    Returns:
        KeyStorage instance
    """
    if prefer_keychain:
        try:
            return KeychainKeyStorage()
        except KeyStorageError as e:
            logger.warning(
                f"Keychain key storage not available, using file storage: {e}"
            )

    return EncryptedFileKeyStorage()
