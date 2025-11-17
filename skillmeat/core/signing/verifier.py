"""Bundle signature verification.

This module provides cryptographic verification of bundle signatures using
Ed25519 digital signatures.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, Field

from .key_manager import KeyManager
from .signer import SignatureData

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Bundle signature verification status."""

    VALID = "valid"  # Signature is valid and key is trusted
    INVALID = "invalid"  # Signature is cryptographically invalid
    UNSIGNED = "unsigned"  # Bundle has no signature
    KEY_NOT_FOUND = "key_not_found"  # Signing key not in trust store
    KEY_UNTRUSTED = "key_untrusted"  # Key found but not trusted
    TAMPERED = "tampered"  # Bundle contents don't match signature
    ERROR = "error"  # Verification error


class VerificationResult(BaseModel):
    """Bundle verification result."""

    status: VerificationStatus = Field(..., description="Verification status")
    valid: bool = Field(..., description="Whether signature is valid and trusted")
    message: str = Field(..., description="Human-readable verification message")
    signature_data: Optional[SignatureData] = Field(
        None, description="Signature metadata if present"
    )
    signer_trusted: bool = Field(False, description="Whether signer key is trusted")

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Verification summary
        """
        if self.status == VerificationStatus.VALID:
            return f"✓ Valid signature by {self.signature_data.signer_name} <{self.signature_data.signer_email}>"
        elif self.status == VerificationStatus.UNSIGNED:
            return "⚠ Bundle is not signed"
        elif self.status == VerificationStatus.INVALID:
            return "✗ Invalid signature - bundle may be tampered"
        elif self.status == VerificationStatus.KEY_NOT_FOUND:
            return "⚠ Signer key not in trust store"
        elif self.status == VerificationStatus.KEY_UNTRUSTED:
            return "⚠ Signer key is not trusted"
        elif self.status == VerificationStatus.TAMPERED:
            return "✗ Bundle has been tampered with"
        else:
            return f"✗ Verification error: {self.message}"


@dataclass
class BundleVerifier:
    """Verifies bundle signatures.

    Provides functionality for:
    - Verifying Ed25519 signatures
    - Checking signer key trust
    - Validating bundle integrity
    """

    key_manager: KeyManager

    def verify_bundle(
        self, bundle_hash: str, manifest_data: Dict, require_signature: bool = False
    ) -> VerificationResult:
        """Verify bundle signature.

        Args:
            bundle_hash: Bundle hash to verify
            manifest_data: Bundle manifest data
            require_signature: If True, fail if bundle is unsigned

        Returns:
            VerificationResult with verification status
        """
        # Check if bundle has signature
        if "signature" not in manifest_data:
            if require_signature:
                return VerificationResult(
                    status=VerificationStatus.UNSIGNED,
                    valid=False,
                    message="Bundle is not signed (signature required)",
                    signer_trusted=False,
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.UNSIGNED,
                    valid=True,  # Not required, so still "valid"
                    message="Bundle is not signed (optional)",
                    signer_trusted=False,
                )

        # Parse signature data
        try:
            signature_data = SignatureData.from_dict(manifest_data["signature"])
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                valid=False,
                message=f"Failed to parse signature data: {e}",
                signer_trusted=False,
            )

        # Load signer's public key
        public_key_obj = self.key_manager.load_public_key_by_fingerprint(
            signature_data.key_fingerprint
        )

        if not public_key_obj:
            return VerificationResult(
                status=VerificationStatus.KEY_NOT_FOUND,
                valid=False,
                message=f"Signer key {signature_data.key_fingerprint[:8]}... not found in trust store",
                signature_data=signature_data,
                signer_trusted=False,
            )

        # Check if key is trusted
        if not public_key_obj.trusted:
            return VerificationResult(
                status=VerificationStatus.KEY_UNTRUSTED,
                valid=False,
                message=f"Signer key {signature_data.key_fingerprint[:8]}... is not trusted",
                signature_data=signature_data,
                signer_trusted=False,
            )

        # Load public key for verification
        try:
            public_key = serialization.load_pem_public_key(
                public_key_obj.public_key_pem.encode()
            )

            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                return VerificationResult(
                    status=VerificationStatus.ERROR,
                    valid=False,
                    message="Signer key is not an Ed25519 public key",
                    signature_data=signature_data,
                    signer_trusted=True,
                )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                valid=False,
                message=f"Failed to load signer public key: {e}",
                signature_data=signature_data,
                signer_trusted=True,
            )

        # Prepare data that was signed
        sign_data = self._prepare_sign_data(bundle_hash, manifest_data)

        # Decode signature
        try:
            import base64

            signature_bytes = base64.b64decode(signature_data.signature)
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                valid=False,
                message=f"Failed to decode signature: {e}",
                signature_data=signature_data,
                signer_trusted=True,
            )

        # Verify signature
        try:
            public_key.verify(signature_bytes, sign_data)

            logger.info(
                f"Signature verified successfully for bundle signed by "
                f"{signature_data.signer_name} <{signature_data.signer_email}>"
            )

            return VerificationResult(
                status=VerificationStatus.VALID,
                valid=True,
                message=f"Valid signature by {signature_data.signer_name} <{signature_data.signer_email}>",
                signature_data=signature_data,
                signer_trusted=True,
            )

        except InvalidSignature:
            logger.warning(
                f"Invalid signature for bundle - possible tampering "
                f"(signer: {signature_data.signer_name})"
            )

            return VerificationResult(
                status=VerificationStatus.INVALID,
                valid=False,
                message="Invalid signature - bundle may have been tampered with",
                signature_data=signature_data,
                signer_trusted=True,
            )

        except Exception as e:
            logger.error(f"Signature verification error: {e}")

            return VerificationResult(
                status=VerificationStatus.ERROR,
                valid=False,
                message=f"Verification error: {e}",
                signature_data=signature_data,
                signer_trusted=True,
            )

    def _prepare_sign_data(self, bundle_hash: str, manifest_data: Dict) -> bytes:
        """Prepare canonical data for verification.

        Must match the data preparation in BundleSigner.

        Args:
            bundle_hash: Bundle hash
            manifest_data: Bundle manifest data

        Returns:
            Bytes that were signed
        """
        # Create canonical representation (same as signer)
        canonical_manifest = self._canonicalize_manifest(manifest_data)

        # Combine bundle hash and manifest
        sign_data = {
            "bundle_hash": bundle_hash,
            "manifest": canonical_manifest,
        }

        # Serialize to JSON with sorted keys for determinism
        sign_json = json.dumps(sign_data, sort_keys=True, separators=(",", ":"))

        return sign_json.encode("utf-8")

    def _canonicalize_manifest(self, manifest_data: Dict) -> Dict:
        """Create canonical representation of manifest.

        Must match the canonicalization in BundleSigner.

        Args:
            manifest_data: Original manifest data

        Returns:
            Canonicalized manifest
        """
        # Deep copy to avoid modifying original
        import copy

        canonical = copy.deepcopy(manifest_data)

        # Remove signature field if present
        if "signature" in canonical:
            del canonical["signature"]

        # Remove non-canonical fields
        non_canonical_fields = ["created_at", "bundle_path"]
        for field in non_canonical_fields:
            if field in canonical:
                del canonical[field]

        return canonical

    def verify_bundle_file(self, bundle_path, require_signature: bool = False):
        """Verify signature of a bundle file.

        Args:
            bundle_path: Path to bundle file
            require_signature: If True, fail if bundle is unsigned

        Returns:
            VerificationResult with verification status

        Raises:
            ValueError: If bundle is invalid
        """
        from pathlib import Path

        from skillmeat.core.sharing.builder import inspect_bundle

        bundle_path = Path(bundle_path)

        # Inspect bundle
        bundle = inspect_bundle(bundle_path)

        # Verify signature
        manifest_dict = bundle.to_dict()
        result = self.verify_bundle(bundle.bundle_hash, manifest_dict, require_signature)

        return result
