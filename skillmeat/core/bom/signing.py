"""Ed25519 signing and verification for SkillBOM snapshots.

Provides key management, BOM signing, and signature verification using
the Ed25519 algorithm via the cryptography library.

Default key location: ~/.skillmeat/keys/skillbom_ed25519 (private)
                       ~/.skillmeat/keys/skillbom_ed25519.pub (public)
"""
from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SigningError(Exception):
    """Raised when signing a BOM or file fails."""


class VerificationError(Exception):
    """Raised when signature verification encounters an unexpected error."""


class KeyNotFoundError(Exception):
    """Raised when a required key file does not exist."""


class KeyGenerationError(Exception):
    """Raised when key generation or serialization fails."""


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SignatureResult:
    """Result of a signing operation."""

    signature: bytes
    signature_hex: str
    algorithm: str  # always "ed25519"
    key_id: str  # SHA-256 fingerprint of the public key (hex)
    signed_at: datetime


@dataclass
class VerificationResult:
    """Result of a signature verification operation."""

    valid: bool
    algorithm: str  # always "ed25519"
    key_id: Optional[str]  # None when public key unavailable
    error: Optional[str]  # None if valid, error message if invalid


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DEFAULT_KEY_DIR = Path.home() / ".skillmeat" / "keys"
_DEFAULT_PRIVATE_KEY_NAME = "skillbom_ed25519"
_DEFAULT_PUBLIC_KEY_NAME = "skillbom_ed25519.pub"


def _default_private_key_path() -> Path:
    return _DEFAULT_KEY_DIR / _DEFAULT_PRIVATE_KEY_NAME


def _default_public_key_path() -> Path:
    return _DEFAULT_KEY_DIR / _DEFAULT_PUBLIC_KEY_NAME


def _compute_key_id(public_key_bytes: bytes) -> str:
    """Return the SHA-256 fingerprint (hex) of the raw public key bytes."""
    return hashlib.sha256(public_key_bytes).hexdigest()


def _raw_public_bytes(public_key: Ed25519PublicKey) -> bytes:
    """Extract the 32-byte raw public key material."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _set_private_permissions(path: Path) -> None:
    """Set restrictive permissions on a private key file (0o600)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Non-fatal on platforms that don't support POSIX permissions (e.g. Windows)
        pass


def _set_public_permissions(path: Path) -> None:
    """Set standard permissions on a public key file (0o644)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Key Management
# ---------------------------------------------------------------------------


def generate_signing_keypair(
    key_dir: Optional[Path] = None,
) -> tuple[bytes, bytes]:
    """Generate an Ed25519 keypair and persist it to disk.

    Args:
        key_dir: Directory in which to write the key files.  Defaults to
            ``~/.skillmeat/keys/``.

    Returns:
        A ``(public_key_bytes, private_key_bytes)`` tuple where both values
        are PEM-encoded bytes suitable for later deserialization.

    Raises:
        KeyGenerationError: If key generation or file I/O fails.
    """
    target_dir = key_dir if key_dir is not None else _DEFAULT_KEY_DIR
    private_path = target_dir / _DEFAULT_PRIVATE_KEY_NAME
    public_path = target_dir / _DEFAULT_PUBLIC_KEY_NAME

    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        private_path.write_bytes(private_pem)
        _set_private_permissions(private_path)

        public_path.write_bytes(public_pem)
        _set_public_permissions(public_path)

        return public_pem, private_pem

    except OSError as exc:
        raise KeyGenerationError(
            f"Failed to generate or persist keypair in {target_dir}: {exc}"
        ) from exc
    except Exception as exc:
        raise KeyGenerationError(f"Key generation failed: {exc}") from exc


def load_signing_key(key_path: Optional[Path] = None) -> bytes:
    """Load a PEM-encoded Ed25519 private key from disk.

    Args:
        key_path: Path to the private key PEM file.  Defaults to
            ``~/.skillmeat/keys/skillbom_ed25519``.

    Returns:
        PEM-encoded private key bytes.

    Raises:
        KeyNotFoundError: If the key file does not exist.
        SigningError: If the file cannot be read or is not a valid private key.
    """
    path = key_path if key_path is not None else _default_private_key_path()
    if not path.exists():
        raise KeyNotFoundError(
            f"Private key not found at {path}. "
            "Generate one with generate_signing_keypair()."
        )
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SigningError(f"Cannot read private key from {path}: {exc}") from exc


def load_verify_key(key_path: Optional[Path] = None) -> bytes:
    """Load a PEM-encoded Ed25519 public key from disk.

    Args:
        key_path: Path to the public key PEM file.  Defaults to
            ``~/.skillmeat/keys/skillbom_ed25519.pub``.

    Returns:
        PEM-encoded public key bytes.

    Raises:
        KeyNotFoundError: If the key file does not exist.
        VerificationError: If the file cannot be read.
    """
    path = key_path if key_path is not None else _default_public_key_path()
    if not path.exists():
        raise KeyNotFoundError(
            f"Public key not found at {path}. "
            "Generate one with generate_signing_keypair()."
        )
    try:
        return path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"Cannot read public key from {path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Signing & Verification
# ---------------------------------------------------------------------------


def sign_bom(
    bom_content: bytes,
    private_key: Optional[bytes] = None,
    key_path: Optional[Path] = None,
) -> SignatureResult:
    """Sign BOM content with an Ed25519 private key.

    Exactly one of *private_key* or *key_path* must resolve to a valid key.
    If neither is provided the default key location is used.

    Args:
        bom_content: Raw BOM bytes to sign.
        private_key: PEM-encoded Ed25519 private key bytes.  Takes precedence
            over *key_path* when supplied.
        key_path: Path to a PEM-encoded Ed25519 private key file.

    Returns:
        :class:`SignatureResult` containing the signature and metadata.

    Raises:
        KeyNotFoundError: If no key can be located.
        SigningError: If signing fails for any reason.
    """
    if private_key is None:
        private_key = load_signing_key(key_path)

    try:
        loaded_key = serialization.load_pem_private_key(
            private_key, password=None
        )
        if not isinstance(loaded_key, Ed25519PrivateKey):
            raise SigningError("Key is not an Ed25519 private key")
        key_obj = loaded_key
    except SigningError:
        raise
    except (ValueError, TypeError, Exception) as exc:
        raise SigningError(f"Failed to deserialize private key: {exc}") from exc

    try:
        signature = key_obj.sign(bom_content)
    except Exception as exc:
        raise SigningError(f"Signing operation failed: {exc}") from exc

    public_key = key_obj.public_key()
    raw_pub = _raw_public_bytes(public_key)
    key_id = _compute_key_id(raw_pub)

    return SignatureResult(
        signature=signature,
        signature_hex=signature.hex(),
        algorithm="ed25519",
        key_id=key_id,
        signed_at=datetime.now(tz=timezone.utc),
    )


def verify_signature(
    bom_content: bytes,
    signature: bytes,
    public_key: Optional[bytes] = None,
    key_path: Optional[Path] = None,
) -> VerificationResult:
    """Verify an Ed25519 signature over BOM content.

    Args:
        bom_content: The original BOM bytes that were signed.
        signature: The raw signature bytes to verify.
        public_key: PEM-encoded Ed25519 public key bytes.  Takes precedence
            over *key_path* when supplied.
        key_path: Path to a PEM-encoded Ed25519 public key file.

    Returns:
        :class:`VerificationResult`.  ``valid=True`` indicates a good
        signature; ``valid=False`` indicates a bad or unverifiable one.
    """
    if public_key is None:
        try:
            public_key = load_verify_key(key_path)
        except KeyNotFoundError as exc:
            return VerificationResult(
                valid=False,
                algorithm="ed25519",
                key_id=None,
                error=str(exc),
            )

    try:
        loaded_pub = serialization.load_pem_public_key(public_key)
        if not isinstance(loaded_pub, Ed25519PublicKey):
            return VerificationResult(
                valid=False,
                algorithm="ed25519",
                key_id=None,
                error="Key is not an Ed25519 public key",
            )
        key_obj = loaded_pub
    except (ValueError, TypeError, Exception) as exc:
        return VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=None,
            error=f"Failed to deserialize public key: {exc}",
        )

    raw_pub = _raw_public_bytes(key_obj)
    key_id = _compute_key_id(raw_pub)

    try:
        key_obj.verify(signature, bom_content)
        return VerificationResult(
            valid=True,
            algorithm="ed25519",
            key_id=key_id,
            error=None,
        )
    except InvalidSignature:
        return VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=key_id,
            error="Signature verification failed: signature does not match content.",
        )
    except Exception as exc:
        return VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=key_id,
            error=f"Unexpected error during verification: {exc}",
        )


# ---------------------------------------------------------------------------
# File Operations
# ---------------------------------------------------------------------------


def sign_file(
    file_path: Path,
    output_path: Optional[Path] = None,
    key_path: Optional[Path] = None,
) -> Path:
    """Sign a file and write the signature to a companion ``.sig`` file.

    Args:
        file_path: Path to the file to sign.
        output_path: Destination for the signature file.  Defaults to
            ``<file_path>.sig``.
        key_path: Path to the PEM-encoded Ed25519 private key.  Defaults to
            the standard key location.

    Returns:
        Path to the written signature file.

    Raises:
        FileNotFoundError: If *file_path* does not exist.
        KeyNotFoundError: If the signing key cannot be found.
        SigningError: If reading the file or signing fails.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File to sign not found: {file_path}")

    try:
        content = file_path.read_bytes()
    except OSError as exc:
        raise SigningError(f"Cannot read file {file_path}: {exc}") from exc

    result = sign_bom(content, key_path=key_path)

    sig_path = output_path if output_path is not None else file_path.with_suffix(
        file_path.suffix + ".sig"
    )
    try:
        sig_path.write_bytes(result.signature)
    except OSError as exc:
        raise SigningError(f"Cannot write signature to {sig_path}: {exc}") from exc

    return sig_path


def verify_file(
    file_path: Path,
    signature_path: Optional[Path] = None,
    key_path: Optional[Path] = None,
) -> VerificationResult:
    """Verify the Ed25519 signature of a file.

    Args:
        file_path: Path to the signed file.
        signature_path: Path to the ``.sig`` file.  Defaults to
            ``<file_path>.sig``.
        key_path: Path to the PEM-encoded Ed25519 public key.  Defaults to
            the standard key location.

    Returns:
        :class:`VerificationResult`.

    Raises:
        FileNotFoundError: If *file_path* or *signature_path* does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File to verify not found: {file_path}")

    sig_path = signature_path if signature_path is not None else file_path.with_suffix(
        file_path.suffix + ".sig"
    )
    if not sig_path.exists():
        raise FileNotFoundError(f"Signature file not found: {sig_path}")

    try:
        content = file_path.read_bytes()
    except OSError as exc:
        return VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=None,
            error=f"Cannot read file {file_path}: {exc}",
        )

    try:
        signature = sig_path.read_bytes()
    except OSError as exc:
        return VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=None,
            error=f"Cannot read signature file {sig_path}: {exc}",
        )

    return verify_signature(content, signature, key_path=key_path)
