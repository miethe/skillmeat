"""Bundle signing and verification system for SkillMeat.

This module provides cryptographic signing for bundles using Ed25519 signatures
with support for key management, signature generation, and verification.

Key Features:
- Ed25519 digital signatures for bundle integrity
- OS keychain integration for key storage
- Public key trust management
- Signature verification on bundle import
- Key generation, rotation, and revocation
"""

from .key_manager import KeyManager, SigningKey, PublicKey, KeyPair
from .signer import BundleSigner, SignatureData
from .verifier import BundleVerifier, VerificationResult, VerificationStatus
from .storage import KeyStorage, get_key_storage_backend

__all__ = [
    "KeyManager",
    "SigningKey",
    "PublicKey",
    "KeyPair",
    "BundleSigner",
    "SignatureData",
    "BundleVerifier",
    "VerificationResult",
    "VerificationStatus",
    "KeyStorage",
    "get_key_storage_backend",
]
