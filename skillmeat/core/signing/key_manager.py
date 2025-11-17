"""Key management for bundle signing.

This module provides Ed25519 key pair generation, storage, and management
for bundle signing operations.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, ConfigDict, Field

from .storage import KeyStorage, get_key_storage_backend

logger = logging.getLogger(__name__)


class SigningKey(BaseModel):
    """Private signing key model."""

    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={datetime: lambda v: v.isoformat()})

    key_id: str = Field(..., description="Unique key identifier (fingerprint)")
    name: str = Field(..., description="Key owner name")
    email: str = Field(..., description="Key owner email")
    fingerprint: str = Field(..., description="Key fingerprint")
    created_at: datetime = Field(..., description="Key creation timestamp")
    public_key_pem: str = Field(..., description="PEM-encoded public key")


class PublicKey(BaseModel):
    """Trusted public key model."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    key_id: str = Field(..., description="Unique key identifier (fingerprint)")
    name: str = Field(..., description="Key owner name")
    email: str = Field(..., description="Key owner email")
    fingerprint: str = Field(..., description="Key fingerprint")
    imported_at: datetime = Field(..., description="Key import timestamp")
    trusted: bool = Field(True, description="Whether key is trusted")
    public_key_pem: str = Field(..., description="PEM-encoded public key")


@dataclass
class KeyPair:
    """Ed25519 key pair container."""

    private_key: ed25519.Ed25519PrivateKey
    public_key: ed25519.Ed25519PublicKey
    key_id: str
    name: str
    email: str
    fingerprint: str


class KeyManager:
    """Manages Ed25519 signing keys for bundle signing.

    Provides functionality for:
    - Generating Ed25519 key pairs
    - Storing keys securely in OS keychain or encrypted files
    - Managing trusted public keys
    - Key rotation and revocation
    - Key fingerprinting
    """

    def __init__(self, storage: Optional[KeyStorage] = None):
        """Initialize key manager.

        Args:
            storage: Key storage backend (uses default if None)
        """
        self.storage = storage or get_key_storage_backend()

    def generate_key_pair(self, name: str, email: str) -> KeyPair:
        """Generate a new Ed25519 key pair.

        Args:
            name: Key owner name
            email: Key owner email

        Returns:
            KeyPair with generated keys and metadata

        Raises:
            ValueError: If name or email are invalid
        """
        if not name or not name.strip():
            raise ValueError("Key owner name cannot be empty")

        if not email or not email.strip():
            raise ValueError("Key owner email cannot be empty")

        # Basic email validation
        if "@" not in email:
            raise ValueError("Invalid email address")

        # Generate Ed25519 key pair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Get public key bytes for fingerprinting
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        # Generate fingerprint (SHA256 hash of public key)
        fingerprint = hashlib.sha256(public_key_bytes).hexdigest()

        # Use first 16 chars of fingerprint as key_id
        key_id = fingerprint[:16]

        logger.info(
            f"Generated Ed25519 key pair for {name} <{email}> "
            f"(fingerprint: {fingerprint[:16]}...)"
        )

        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            key_id=key_id,
            name=name,
            email=email,
            fingerprint=fingerprint,
        )

    def store_key_pair(self, key_pair: KeyPair) -> SigningKey:
        """Store a key pair securely.

        Args:
            key_pair: KeyPair to store

        Returns:
            SigningKey with metadata

        Raises:
            KeyStorageError: If storage fails
        """
        # Serialize private key to PEM
        private_key_pem = key_pair.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Serialize public key to PEM
        public_key_pem = key_pair.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Prepare metadata
        metadata = {
            "name": key_pair.name,
            "email": key_pair.email,
            "fingerprint": key_pair.fingerprint,
            "created_at": datetime.utcnow().isoformat(),
            "public_key_pem": public_key_pem.decode("utf-8"),
        }

        # Store private key
        self.storage.store_private_key(key_pair.key_id, private_key_pem, metadata)

        logger.info(
            f"Stored signing key {key_pair.key_id} for {key_pair.name} <{key_pair.email}>"
        )

        return SigningKey(
            key_id=key_pair.key_id,
            name=key_pair.name,
            email=key_pair.email,
            fingerprint=key_pair.fingerprint,
            created_at=datetime.fromisoformat(metadata["created_at"]),
            public_key_pem=metadata["public_key_pem"],
        )

    def load_private_key(self, key_id: str) -> Optional[KeyPair]:
        """Load a private signing key.

        Args:
            key_id: Key identifier

        Returns:
            KeyPair if found, None otherwise

        Raises:
            KeyStorageError: If loading fails
        """
        result = self.storage.retrieve_private_key(key_id)
        if not result:
            return None

        private_key_pem, metadata = result

        # Deserialize private key
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None
        )

        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError(f"Key {key_id} is not an Ed25519 private key")

        # Get public key
        public_key = private_key.public_key()

        logger.debug(f"Loaded private key {key_id}")

        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            key_id=key_id,
            name=metadata["name"],
            email=metadata["email"],
            fingerprint=metadata["fingerprint"],
        )

    def delete_private_key(self, key_id: str) -> bool:
        """Delete a private signing key.

        Args:
            key_id: Key identifier

        Returns:
            True if key was deleted, False if not found

        Raises:
            KeyStorageError: If deletion fails
        """
        deleted = self.storage.delete_private_key(key_id)

        if deleted:
            logger.info(f"Deleted private key {key_id}")
        else:
            logger.warning(f"Private key {key_id} not found")

        return deleted

    def list_signing_keys(self) -> List[SigningKey]:
        """List all stored signing keys.

        Returns:
            List of SigningKey objects
        """
        signing_keys = []

        for key_id in self.storage.list_private_keys():
            result = self.storage.retrieve_private_key(key_id)
            if not result:
                continue

            _, metadata = result

            signing_key = SigningKey(
                key_id=key_id,
                name=metadata["name"],
                email=metadata["email"],
                fingerprint=metadata["fingerprint"],
                created_at=datetime.fromisoformat(metadata["created_at"]),
                public_key_pem=metadata["public_key_pem"],
            )
            signing_keys.append(signing_key)

        # Sort by creation date (newest first)
        signing_keys.sort(key=lambda k: k.created_at, reverse=True)

        return signing_keys

    def import_public_key(
        self, public_key_pem: str, name: str, email: str, trusted: bool = True
    ) -> PublicKey:
        """Import a trusted public key.

        Args:
            public_key_pem: PEM-encoded public key
            name: Key owner name
            email: Key owner email
            trusted: Whether to trust this key

        Returns:
            PublicKey with metadata

        Raises:
            ValueError: If public key is invalid
            KeyStorageError: If storage fails
        """
        # Deserialize and validate public key
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode())

            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                raise ValueError("Not an Ed25519 public key")
        except Exception as e:
            raise ValueError(f"Invalid public key: {e}")

        # Get public key bytes for fingerprinting
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        # Generate fingerprint
        fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
        key_id = fingerprint[:16]

        # Check if already imported
        existing = self.storage.retrieve_public_key(key_id)
        if existing:
            logger.warning(
                f"Public key {key_id} already imported, updating metadata"
            )

        # Prepare metadata
        metadata = {
            "name": name,
            "email": email,
            "fingerprint": fingerprint,
            "imported_at": datetime.utcnow().isoformat(),
            "trusted": trusted,
        }

        # Store public key
        self.storage.store_public_key(key_id, public_key_pem.encode(), metadata)

        logger.info(f"Imported public key {key_id} for {name} <{email}>")

        return PublicKey(
            key_id=key_id,
            name=name,
            email=email,
            fingerprint=fingerprint,
            imported_at=datetime.fromisoformat(metadata["imported_at"]),
            trusted=trusted,
            public_key_pem=public_key_pem,
        )

    def load_public_key(self, key_id: str) -> Optional[PublicKey]:
        """Load a trusted public key.

        Args:
            key_id: Key identifier (fingerprint prefix)

        Returns:
            PublicKey if found, None otherwise

        Raises:
            KeyStorageError: If loading fails
        """
        result = self.storage.retrieve_public_key(key_id)
        if not result:
            return None

        public_key_pem, metadata = result

        return PublicKey(
            key_id=key_id,
            name=metadata["name"],
            email=metadata["email"],
            fingerprint=metadata["fingerprint"],
            imported_at=datetime.fromisoformat(metadata["imported_at"]),
            trusted=metadata.get("trusted", True),
            public_key_pem=public_key_pem.decode("utf-8"),
        )

    def load_public_key_by_fingerprint(
        self, fingerprint: str
    ) -> Optional[PublicKey]:
        """Load a public key by full fingerprint.

        Args:
            fingerprint: Full fingerprint (SHA256 hex)

        Returns:
            PublicKey if found, None otherwise
        """
        # Try exact key_id match (first 16 chars)
        key_id = fingerprint[:16]
        public_key = self.load_public_key(key_id)

        if public_key and public_key.fingerprint == fingerprint:
            return public_key

        # Search all public keys for matching fingerprint
        for pk in self.list_public_keys():
            if pk.fingerprint == fingerprint:
                return pk

        return None

    def revoke_public_key(self, key_id: str) -> bool:
        """Revoke trust in a public key.

        Args:
            key_id: Key identifier

        Returns:
            True if key was revoked, False if not found

        Raises:
            KeyStorageError: If revocation fails
        """
        deleted = self.storage.delete_public_key(key_id)

        if deleted:
            logger.info(f"Revoked public key {key_id}")
        else:
            logger.warning(f"Public key {key_id} not found")

        return deleted

    def list_public_keys(self) -> List[PublicKey]:
        """List all trusted public keys.

        Returns:
            List of PublicKey objects
        """
        public_keys = []

        for key_id in self.storage.list_public_keys():
            result = self.storage.retrieve_public_key(key_id)
            if not result:
                continue

            public_key_pem, metadata = result

            public_key = PublicKey(
                key_id=key_id,
                name=metadata["name"],
                email=metadata["email"],
                fingerprint=metadata["fingerprint"],
                imported_at=datetime.fromisoformat(metadata["imported_at"]),
                trusted=metadata.get("trusted", True),
                public_key_pem=public_key_pem.decode("utf-8"),
            )
            public_keys.append(public_key)

        # Sort by import date (newest first)
        public_keys.sort(key=lambda k: k.imported_at, reverse=True)

        return public_keys

    def export_public_key(self, key_id: str) -> Optional[str]:
        """Export a public key in PEM format.

        Args:
            key_id: Key identifier

        Returns:
            PEM-encoded public key or None if not found

        Raises:
            KeyStorageError: If export fails
        """
        # Try to load from private key first
        key_pair = self.load_private_key(key_id)
        if key_pair:
            public_key_pem = key_pair.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            return public_key_pem.decode("utf-8")

        # Try to load from public keys
        public_key = self.load_public_key(key_id)
        if public_key:
            return public_key.public_key_pem

        return None

    def get_default_signing_key(self) -> Optional[SigningKey]:
        """Get the default signing key (most recent).

        Returns:
            SigningKey if available, None otherwise
        """
        signing_keys = self.list_signing_keys()
        if not signing_keys:
            return None

        # Return most recent key
        return signing_keys[0]
