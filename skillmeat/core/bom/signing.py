"""Ed25519 signing and verification for SkillBOM snapshots.

Provides key management, BOM signing, and signature verification using
the Ed25519 algorithm via the cryptography library.

Default key location: ~/.skillmeat/keys/skillbom_ed25519 (private)
                       ~/.skillmeat/keys/skillbom_ed25519.pub (public)
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

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


@dataclass
class ChainValidationResult:
    """Result of validating a chain of signed BOM snapshots."""

    valid: bool
    chain_length: int
    verified_count: int  # snapshots with valid signatures
    unsigned_count: int  # snapshots without signatures
    first_break_at: Optional[int]  # index where chain breaks, or None if unbroken
    errors: List[str] = field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Chain Validation
# ---------------------------------------------------------------------------


def validate_signature_chain(
    snapshots: List[dict],
    public_key: Optional[bytes] = None,
    key_path: Optional[Path] = None,
) -> ChainValidationResult:
    """Validate a chain of signed BOM snapshots.

    Each snapshot dict should have:
    - ``bom_json``: str — the BOM payload that was signed.
    - ``signature``: str | None — hex-encoded Ed25519 signature over ``bom_json``.
    - ``parent_hash``: str | None — SHA-256 hex of the previous BOM (for lineage).
    - ``content_hash``: str — SHA-256 hex of this BOM's ``bom_json``.

    Validates:
    1. Each signature is valid (if present).
    2. ``parent_hash`` of each snapshot matches ``content_hash`` of the previous one.
    3. Chain is unbroken from first to last.

    Args:
        snapshots: Ordered list of snapshot dicts (oldest → newest).
        public_key: PEM-encoded Ed25519 public key bytes for verification.
        key_path: Path to a PEM-encoded Ed25519 public key file (used when
            *public_key* is not supplied).

    Returns:
        :class:`ChainValidationResult` describing the chain's integrity.
    """
    if not snapshots:
        return ChainValidationResult(
            valid=True,
            chain_length=0,
            verified_count=0,
            unsigned_count=0,
            first_break_at=None,
            errors=[],
        )

    errors: List[str] = []
    first_break_at: Optional[int] = None
    verified_count = 0
    unsigned_count = 0

    for idx, snapshot in enumerate(snapshots):
        bom_json: Optional[str] = snapshot.get("bom_json")
        signature_hex: Optional[str] = snapshot.get("signature")
        parent_hash: Optional[str] = snapshot.get("parent_hash")
        content_hash: Optional[str] = snapshot.get("content_hash")

        # --- Signature verification ---
        if signature_hex:
            if bom_json is None:
                err = f"[{idx}] has signature but missing bom_json"
                errors.append(err)
                if first_break_at is None:
                    first_break_at = idx
            else:
                bom_bytes = bom_json.encode() if isinstance(bom_json, str) else bom_json
                try:
                    sig_bytes = bytes.fromhex(signature_hex)
                except ValueError:
                    err = f"[{idx}] signature is not valid hex"
                    errors.append(err)
                    if first_break_at is None:
                        first_break_at = idx
                else:
                    result = verify_signature(
                        bom_bytes, sig_bytes, public_key=public_key, key_path=key_path
                    )
                    if result.valid:
                        verified_count += 1
                    else:
                        err = f"[{idx}] signature invalid: {result.error}"
                        errors.append(err)
                        if first_break_at is None:
                            first_break_at = idx
        else:
            unsigned_count += 1

        # --- Parent hash linkage ---
        if idx > 0:
            prev_snapshot = snapshots[idx - 1]
            prev_content_hash: Optional[str] = prev_snapshot.get("content_hash")
            if parent_hash is not None and prev_content_hash is not None:
                if parent_hash != prev_content_hash:
                    err = (
                        f"[{idx}] parent_hash mismatch: expected {prev_content_hash!r}, "
                        f"got {parent_hash!r}"
                    )
                    errors.append(err)
                    if first_break_at is None:
                        first_break_at = idx
            elif parent_hash is not None and prev_content_hash is None:
                # Previous snapshot has no content_hash to compare against;
                # record a warning but do not break the chain.
                errors.append(
                    f"[{idx}] parent_hash present but previous snapshot has no content_hash"
                )

        # --- content_hash self-consistency ---
        if content_hash is not None and bom_json is not None:
            bom_bytes = bom_json.encode() if isinstance(bom_json, str) else bom_json
            computed = hashlib.sha256(bom_bytes).hexdigest()
            if computed != content_hash:
                err = (
                    f"[{idx}] content_hash mismatch: declared {content_hash!r}, "
                    f"computed {computed!r}"
                )
                errors.append(err)
                if first_break_at is None:
                    first_break_at = idx

    valid = len(errors) == 0
    return ChainValidationResult(
        valid=valid,
        chain_length=len(snapshots),
        verified_count=verified_count,
        unsigned_count=unsigned_count,
        first_break_at=first_break_at,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# verify_bom — verify embedded signature in a BOM data dict
# ---------------------------------------------------------------------------


def verify_bom(bom_data: dict) -> VerificationResult:
    """Verify the embedded signature in a BOM data dict.

    The dict is expected to have a ``"signature"`` key (hex-encoded) and either
    a ``"bom_json"`` key (str) containing the canonical BOM payload, or the
    remaining keys will be serialised to JSON for verification.

    Args:
        bom_data: BOM data dict containing an embedded ``"signature"`` field.

    Returns:
        :class:`VerificationResult`.  ``valid=True`` if the signature checks
        out; ``valid=False`` otherwise (including when no signature is present).
    """
    signature_hex: Optional[str] = bom_data.get("signature")
    if not signature_hex:
        return VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=None,
            error="No signature field found in BOM data.",
        )

    # Prefer an explicit bom_json payload; fall back to re-serialising the dict
    # with the signature field excluded (canonical form).
    bom_json: Optional[str] = bom_data.get("bom_json")
    if bom_json is not None:
        bom_bytes = bom_json.encode() if isinstance(bom_json, str) else bom_json
    else:
        # Reconstruct canonical payload by removing the signature field.
        payload = {k: v for k, v in bom_data.items() if k != "signature"}
        bom_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    try:
        sig_bytes = bytes.fromhex(signature_hex)
    except ValueError:
        return VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=None,
            error="Signature field is not valid hex.",
        )

    return verify_signature(bom_bytes, sig_bytes)


# ---------------------------------------------------------------------------
# Auto-sign feature flag
# ---------------------------------------------------------------------------

#: Module-level default for auto-sign (always disabled; use env var to enable).
SKILLBOM_AUTO_SIGN: bool = False


def is_auto_sign_enabled() -> bool:
    """Return True if auto-signing is enabled via the ``SKILLBOM_AUTO_SIGN`` env var.

    Accepted truthy values (case-insensitive): ``"1"``, ``"true"``, ``"yes"``.
    """
    return os.environ.get("SKILLBOM_AUTO_SIGN", "").lower() in ("1", "true", "yes")


def auto_sign_bom(
    bom_content: bytes,
    key_path: Optional[Path] = None,
) -> Optional[SignatureResult]:
    """Sign BOM content if auto-signing is enabled.

    Returns ``None`` silently when auto-signing is disabled or when the
    signing key cannot be found / signing fails.  This is a best-effort
    helper — callers must not rely on a non-``None`` return value.

    Args:
        bom_content: Raw BOM bytes to sign.
        key_path: Path to a PEM-encoded Ed25519 private key file.  When
            ``None``, the default key location is used.

    Returns:
        :class:`SignatureResult` on success, or ``None``.
    """
    if not is_auto_sign_enabled():
        return None
    try:
        return sign_bom(bom_content, key_path=key_path)
    except (KeyNotFoundError, SigningError):
        return None
