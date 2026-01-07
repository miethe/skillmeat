"""Token management for SkillMeat web authentication.

This module provides JWT-based token generation, validation, and lifecycle
management for secure CLI-to-web authentication.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jwt
from pydantic import BaseModel, ConfigDict, Field

from .storage import TokenStorage, get_storage_backend

logger = logging.getLogger(__name__)


class Token(BaseModel):
    """JWT token data model."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    token_id: str = Field(..., description="Unique token identifier")
    name: str = Field(..., description="Human-readable token name")
    token: str = Field(..., description="JWT token string")
    created_at: datetime = Field(..., description="Token creation timestamp")
    expires_at: Optional[datetime] = Field(
        None, description="Token expiration timestamp"
    )
    last_used: Optional[datetime] = Field(None, description="Last time token was used")


class TokenInfo(BaseModel):
    """Token metadata for listing and display."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    token_id: str = Field(..., description="Unique token identifier")
    name: str = Field(..., description="Human-readable token name")
    created_at: datetime = Field(..., description="Token creation timestamp")
    expires_at: Optional[datetime] = Field(
        None, description="Token expiration timestamp"
    )
    last_used: Optional[datetime] = Field(None, description="Last time token was used")
    is_expired: bool = Field(..., description="Whether token has expired")


@dataclass
class TokenManager:
    """Manages authentication tokens for SkillMeat web interface.

    Handles token generation, validation, storage, and lifecycle management
    using JWT tokens with configurable expiration.

    Attributes:
        storage: Token storage backend
        secret_key: Secret key for JWT signing
        algorithm: JWT algorithm (default: HS256)
        default_expiration_days: Default token expiration in days (0 = no expiration)
    """

    storage: Optional[TokenStorage] = None
    secret_key: Optional[str] = None
    algorithm: str = "HS256"
    default_expiration_days: int = 90

    def __post_init__(self):
        """Initialize token manager with storage and secret key."""
        if self.storage is None:
            self.storage = get_storage_backend()

        if self.secret_key is None:
            # Generate or load secret key
            self.secret_key = self._get_or_create_secret_key()

    def _get_or_create_secret_key(self) -> str:
        """Get or create a persistent secret key for JWT signing.

        Returns:
            Secret key string
        """
        # Try to load existing secret key
        secret_data = self.storage.retrieve("_secret_key")

        if secret_data:
            import json

            data = json.loads(secret_data)
            logger.debug("Loaded existing secret key")
            return data["key"]

        # Generate new secret key
        secret_key = secrets.token_urlsafe(32)

        # Store it
        import json

        secret_data = json.dumps({"key": secret_key})
        self.storage.store("_secret_key", secret_data)

        logger.info("Generated new secret key for JWT signing")
        return secret_key

    def generate_token(
        self,
        name: str,
        expiration_days: Optional[int] = None,
        custom_claims: Optional[Dict] = None,
    ) -> Token:
        """Generate a new authentication token.

        Args:
            name: Human-readable name for the token
            expiration_days: Days until expiration (None = use default, 0 = no expiration)
            custom_claims: Additional claims to include in JWT

        Returns:
            Token object with JWT and metadata

        Raises:
            ValueError: If name is empty or invalid
        """
        if not name or not name.strip():
            raise ValueError("Token name cannot be empty")

        # Generate unique token ID
        token_id = str(uuid.uuid4())

        # Determine expiration
        if expiration_days is None:
            expiration_days = self.default_expiration_days

        now = datetime.utcnow()
        expires_at = None
        exp_claim = None

        if expiration_days > 0:
            expires_at = now + timedelta(days=expiration_days)
            exp_claim = int(expires_at.timestamp())

        # Build JWT claims
        claims = {
            "sub": "skillmeat-web",
            "jti": token_id,
            "name": name,
            "iat": int(now.timestamp()),
        }

        if exp_claim:
            claims["exp"] = exp_claim

        if custom_claims:
            claims.update(custom_claims)

        # Generate JWT
        token_string = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

        # Create token object
        token = Token(
            token_id=token_id,
            name=name,
            token=token_string,
            created_at=now,
            expires_at=expires_at,
            last_used=None,
        )

        # Store token metadata
        self._store_token(token)

        logger.info(
            f"Generated token '{name}' (ID: {token_id[:8]}..., "
            f"expires: {expires_at or 'never'})"
        )

        return token

    def _store_token(self, token: Token) -> None:
        """Store token metadata to storage.

        Args:
            token: Token to store
        """
        import json

        # Don't store the full JWT token, just metadata
        token_data = {
            "token_id": token.token_id,
            "name": token.name,
            "created_at": token.created_at.isoformat(),
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
            "last_used": token.last_used.isoformat() if token.last_used else None,
        }

        self.storage.store(token.token_id, json.dumps(token_data))

    def _load_token_metadata(self, token_id: str) -> Optional[Dict]:
        """Load token metadata from storage.

        Args:
            token_id: Token identifier

        Returns:
            Token metadata dict or None if not found
        """
        import json

        token_data = self.storage.retrieve(token_id)
        if not token_data:
            return None

        try:
            data = json.loads(token_data)

            # Parse ISO format timestamps
            if data.get("created_at"):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            if data.get("expires_at"):
                data["expires_at"] = datetime.fromisoformat(data["expires_at"])
            if data.get("last_used"):
                data["last_used"] = datetime.fromisoformat(data["last_used"])

            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse token metadata for {token_id}: {e}")
            return None

    def validate_token(self, token_string: str, update_last_used: bool = True) -> bool:
        """Validate a JWT token.

        Args:
            token_string: JWT token string to validate
            update_last_used: Whether to update last_used timestamp

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Decode and verify JWT
            claims = jwt.decode(
                token_string, self.secret_key, algorithms=[self.algorithm]
            )

            # Extract token ID
            token_id = claims.get("jti")
            if not token_id:
                logger.warning("Token missing jti claim")
                return False

            # Check if token exists in storage
            token_metadata = self._load_token_metadata(token_id)
            if not token_metadata:
                logger.warning(f"Token {token_id[:8]}... not found in storage")
                return False

            # Check if token has been revoked
            if token_metadata.get("revoked"):
                logger.warning(f"Token {token_id[:8]}... has been revoked")
                return False

            # Update last_used timestamp
            if update_last_used:
                self._update_last_used(token_id)

            logger.debug(f"Token {token_id[:8]}... validated successfully")
            return True

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return False
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return False
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False

    def _update_last_used(self, token_id: str) -> None:
        """Update the last_used timestamp for a token.

        Args:
            token_id: Token identifier
        """
        import json

        token_metadata = self._load_token_metadata(token_id)
        if not token_metadata:
            return

        token_metadata["last_used"] = datetime.utcnow()
        self._store_token_from_metadata(token_id, token_metadata)

    def _store_token_from_metadata(self, token_id: str, metadata: Dict) -> None:
        """Store token metadata.

        Args:
            token_id: Token identifier
            metadata: Token metadata dict
        """
        import json

        # Convert datetime objects to ISO format
        data = metadata.copy()
        for key in ["created_at", "expires_at", "last_used"]:
            if data.get(key) and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()

        self.storage.store(token_id, json.dumps(data))

    def get_token_claims(self, token_string: str) -> Optional[Dict]:
        """Extract claims from a JWT token without validating signature.

        Args:
            token_string: JWT token string

        Returns:
            Token claims dict or None if invalid

        Note:
            This does not validate the signature. Use validate_token() for validation.
        """
        try:
            # Decode without verification (just for inspection)
            claims = jwt.decode(
                token_string,
                options={"verify_signature": False},
                algorithms=[self.algorithm],
            )
            return claims
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return None

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a token by ID.

        Args:
            token_id: Token identifier

        Returns:
            True if token was revoked, False if not found
        """
        return self.storage.delete(token_id)

    def revoke_token_by_name(self, name: str) -> int:
        """Revoke all tokens with a given name.

        Args:
            name: Token name

        Returns:
            Number of tokens revoked
        """
        count = 0
        for token_info in self.list_tokens():
            if token_info.name == name:
                if self.revoke_token(token_info.token_id):
                    count += 1

        logger.info(f"Revoked {count} tokens with name '{name}'")
        return count

    def list_tokens(self, include_expired: bool = True) -> List[TokenInfo]:
        """List all stored tokens.

        Args:
            include_expired: Whether to include expired tokens

        Returns:
            List of TokenInfo objects
        """
        token_infos = []
        now = datetime.utcnow()

        for token_id in self.storage.list_tokens():
            # Skip internal keys
            if token_id.startswith("_"):
                continue

            metadata = self._load_token_metadata(token_id)
            if not metadata:
                continue

            # Check if expired
            expires_at = metadata.get("expires_at")
            is_expired = False
            if expires_at and expires_at < now:
                is_expired = True

            if is_expired and not include_expired:
                continue

            token_info = TokenInfo(
                token_id=metadata["token_id"],
                name=metadata["name"],
                created_at=metadata["created_at"],
                expires_at=expires_at,
                last_used=metadata.get("last_used"),
                is_expired=is_expired,
            )
            token_infos.append(token_info)

        # Sort by creation date (newest first)
        token_infos.sort(key=lambda t: t.created_at, reverse=True)

        return token_infos

    def get_token_info(self, token_id: str) -> Optional[TokenInfo]:
        """Get information about a specific token.

        Args:
            token_id: Token identifier

        Returns:
            TokenInfo object or None if not found
        """
        metadata = self._load_token_metadata(token_id)
        if not metadata:
            return None

        now = datetime.utcnow()
        expires_at = metadata.get("expires_at")
        is_expired = False
        if expires_at and expires_at < now:
            is_expired = True

        return TokenInfo(
            token_id=metadata["token_id"],
            name=metadata["name"],
            created_at=metadata["created_at"],
            expires_at=expires_at,
            last_used=metadata.get("last_used"),
            is_expired=is_expired,
        )

    def cleanup_expired_tokens(self) -> int:
        """Remove all expired tokens.

        Returns:
            Number of tokens removed
        """
        count = 0
        now = datetime.utcnow()

        for token_info in self.list_tokens():
            if token_info.expires_at and token_info.expires_at < now:
                if self.revoke_token(token_info.token_id):
                    count += 1

        logger.info(f"Cleaned up {count} expired tokens")
        return count

    def revoke_all_tokens(self) -> int:
        """Revoke all tokens.

        Returns:
            Number of tokens revoked
        """
        # Don't delete the secret key
        count = 0
        for token_id in self.storage.list_tokens():
            if token_id.startswith("_"):
                continue
            if self.storage.delete(token_id):
                count += 1

        logger.info(f"Revoked all {count} tokens")
        return count

    def rotate_secret_key(self) -> str:
        """Generate a new secret key and invalidate all existing tokens.

        Returns:
            New secret key

        Warning:
            This will invalidate ALL existing tokens!
        """
        # Delete old secret key
        self.storage.delete("_secret_key")

        # Generate new key
        new_key = self._get_or_create_secret_key()
        self.secret_key = new_key

        logger.warning("Secret key rotated - all existing tokens are now invalid")
        return new_key
