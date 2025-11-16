"""Bundle signing functionality.

This module provides cryptographic signing for bundles using Ed25519
digital signatures.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, ConfigDict, Field

from .key_manager import KeyManager, KeyPair

logger = logging.getLogger(__name__)


class SignatureData(BaseModel):
    """Bundle signature metadata."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    signature: str = Field(..., description="Base64-encoded signature")
    signer_name: str = Field(..., description="Signer name")
    signer_email: str = Field(..., description="Signer email")
    key_fingerprint: str = Field(..., description="Signing key fingerprint")
    signed_at: datetime = Field(..., description="Signing timestamp")
    algorithm: str = Field("Ed25519", description="Signature algorithm")

    def to_dict(self) -> Dict:
        """Convert to dictionary for manifest inclusion.

        Returns:
            Dictionary representation
        """
        return {
            "signature": self.signature,
            "signer_name": self.signer_name,
            "signer_email": self.signer_email,
            "key_fingerprint": self.key_fingerprint,
            "signed_at": self.signed_at.isoformat(),
            "algorithm": self.algorithm,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SignatureData":
        """Create from dictionary.

        Args:
            data: Dictionary with signature data

        Returns:
            SignatureData instance
        """
        return cls(
            signature=data["signature"],
            signer_name=data["signer_name"],
            signer_email=data["signer_email"],
            key_fingerprint=data["key_fingerprint"],
            signed_at=datetime.fromisoformat(data["signed_at"]),
            algorithm=data.get("algorithm", "Ed25519"),
        )


@dataclass
class BundleSigner:
    """Signs bundles with Ed25519 digital signatures.

    Provides functionality for:
    - Signing bundle manifests
    - Computing canonical representations for signing
    - Managing signature metadata
    """

    key_manager: KeyManager

    def sign_bundle(
        self,
        bundle_hash: str,
        manifest_data: Dict,
        key_id: Optional[str] = None,
    ) -> SignatureData:
        """Sign a bundle.

        Args:
            bundle_hash: Bundle hash to sign
            manifest_data: Bundle manifest data
            key_id: Signing key ID (uses default if None)

        Returns:
            SignatureData with signature and metadata

        Raises:
            ValueError: If no signing key is available
            RuntimeError: If signing fails
        """
        # Load signing key
        if key_id:
            key_pair = self.key_manager.load_private_key(key_id)
            if not key_pair:
                raise ValueError(f"Signing key {key_id} not found")
        else:
            # Use default signing key
            signing_key = self.key_manager.get_default_signing_key()
            if not signing_key:
                raise ValueError(
                    "No signing key available. Generate a key with 'skillmeat sign generate-key'"
                )
            key_pair = self.key_manager.load_private_key(signing_key.key_id)
            if not key_pair:
                raise ValueError(f"Failed to load signing key {signing_key.key_id}")

        # Prepare data to sign
        sign_data = self._prepare_sign_data(bundle_hash, manifest_data)

        # Sign the data
        try:
            signature_bytes = key_pair.private_key.sign(sign_data)

            # Encode signature as base64
            import base64

            signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")

            # Create signature metadata
            signature_data = SignatureData(
                signature=signature_b64,
                signer_name=key_pair.name,
                signer_email=key_pair.email,
                key_fingerprint=key_pair.fingerprint,
                signed_at=datetime.utcnow(),
                algorithm="Ed25519",
            )

            logger.info(
                f"Signed bundle with key {key_pair.key_id} "
                f"({key_pair.name} <{key_pair.email}>)"
            )

            return signature_data

        except Exception as e:
            raise RuntimeError(f"Failed to sign bundle: {e}")

    def _prepare_sign_data(self, bundle_hash: str, manifest_data: Dict) -> bytes:
        """Prepare canonical data for signing.

        Creates a deterministic representation of the bundle for signing.

        Args:
            bundle_hash: Bundle hash
            manifest_data: Bundle manifest data

        Returns:
            Bytes to sign
        """
        # Create canonical representation
        # We sign: bundle_hash + canonical manifest (without signature field)
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

        Removes signature field and normalizes data for deterministic signing.

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

        # Remove any other non-canonical fields
        # (e.g., fields that might change without affecting content)
        non_canonical_fields = ["created_at", "bundle_path"]
        for field in non_canonical_fields:
            if field in canonical:
                del canonical[field]

        return canonical

    def add_signature_to_manifest(
        self, manifest_data: Dict, signature_data: SignatureData
    ) -> Dict:
        """Add signature to bundle manifest.

        Args:
            manifest_data: Bundle manifest data
            signature_data: Signature data to add

        Returns:
            Updated manifest with signature
        """
        manifest_data["signature"] = signature_data.to_dict()
        return manifest_data

    def sign_bundle_file(
        self,
        bundle_path,
        key_id: Optional[str] = None,
        output_path: Optional = None,
    ):
        """Sign an existing bundle file.

        Reads the bundle, adds signature, and optionally writes to new file.

        Args:
            bundle_path: Path to bundle file
            key_id: Signing key ID (uses default if None)
            output_path: Output path (overwrites original if None)

        Returns:
            Updated Bundle object with signature

        Raises:
            ValueError: If bundle is invalid or signing fails
        """
        import zipfile
        from pathlib import Path

        from skillmeat.core.sharing.builder import inspect_bundle
        from skillmeat.core.sharing.manifest import BundleManifest

        bundle_path = Path(bundle_path)

        # Inspect bundle
        bundle = inspect_bundle(bundle_path)

        # Check if already signed
        if hasattr(bundle, "signature") and bundle.signature:
            logger.warning(f"Bundle {bundle_path} is already signed")
            # Could optionally allow re-signing

        # Sign the bundle
        manifest_dict = bundle.to_dict()
        signature_data = self.sign_bundle(bundle.bundle_hash, manifest_dict, key_id)

        # Add signature to manifest
        manifest_dict = self.add_signature_to_manifest(manifest_dict, signature_data)

        # Update bundle object
        bundle.signature = signature_data

        # Write updated manifest
        if output_path is None:
            output_path = bundle_path

        output_path = Path(output_path)

        # Need to update the ZIP file with new manifest
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract bundle
            with zipfile.ZipFile(bundle_path, "r") as zf:
                zf.extractall(temp_path)

            # Write updated manifest
            manifest_path = temp_path / "manifest.json"
            BundleManifest.write_manifest(manifest_dict, manifest_path)

            # Create new ZIP
            temp_output = temp_path / "signed_bundle.zip"
            with zipfile.ZipFile(temp_output, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in sorted(temp_path.rglob("*")):
                    if file_path.is_file() and file_path != temp_output:
                        arcname = file_path.relative_to(temp_path)
                        zipf.write(file_path, arcname)

            # Move to output path
            shutil.move(str(temp_output), str(output_path))

        logger.info(f"Signed bundle written to {output_path}")

        return bundle
