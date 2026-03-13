"""Tests for skillmeat.core.bom.signing — Ed25519 BOM signing module."""
from __future__ import annotations

import os
import platform
import stat
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from skillmeat.core.bom.signing import (
    KeyGenerationError,
    KeyNotFoundError,
    SignatureResult,
    SigningError,
    VerificationError,
    VerificationResult,
    generate_signing_keypair,
    load_signing_key,
    load_verify_key,
    sign_bom,
    sign_file,
    verify_file,
    verify_signature,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def key_dir(tmp_path: Path) -> Path:
    """Return a fresh temporary directory for key storage."""
    return tmp_path / "keys"


@pytest.fixture()
def generated_keys(key_dir: Path) -> tuple[bytes, bytes]:
    """Generate a keypair and return (public_pem, private_pem)."""
    return generate_signing_keypair(key_dir=key_dir)


@pytest.fixture()
def bom_content() -> bytes:
    """Sample BOM content for signing tests."""
    return b'{"artifacts": [{"name": "test-skill", "version": "1.0.0"}]}'


# ---------------------------------------------------------------------------
# Key Generation
# ---------------------------------------------------------------------------


class TestGenerateSigningKeypair:
    def test_creates_key_directory(self, key_dir: Path) -> None:
        assert not key_dir.exists()
        generate_signing_keypair(key_dir=key_dir)
        assert key_dir.is_dir()

    def test_returns_tuple_of_bytes(self, key_dir: Path) -> None:
        result = generate_signing_keypair(key_dir=key_dir)
        assert isinstance(result, tuple)
        assert len(result) == 2
        pub, priv = result
        assert isinstance(pub, bytes)
        assert isinstance(priv, bytes)

    def test_public_key_is_valid_pem(self, key_dir: Path) -> None:
        pub, _ = generate_signing_keypair(key_dir=key_dir)
        # Should deserialize without error
        key = serialization.load_pem_public_key(pub)
        assert key is not None

    def test_private_key_is_valid_pem(self, key_dir: Path) -> None:
        _, priv = generate_signing_keypair(key_dir=key_dir)
        key = serialization.load_pem_private_key(priv, password=None)
        assert isinstance(key, Ed25519PrivateKey)

    def test_keys_are_mathematically_paired(self, key_dir: Path) -> None:
        pub, priv = generate_signing_keypair(key_dir=key_dir)
        priv_obj = serialization.load_pem_private_key(priv, password=None)
        pub_obj = serialization.load_pem_public_key(pub)
        # Sign something with private, verify with public
        msg = b"pairing check"
        sig = priv_obj.sign(msg)
        pub_obj.verify(sig, msg)  # raises if mismatch

    def test_private_key_file_written(self, key_dir: Path) -> None:
        generate_signing_keypair(key_dir=key_dir)
        private_path = key_dir / "skillbom_ed25519"
        assert private_path.exists()

    def test_public_key_file_written(self, key_dir: Path) -> None:
        generate_signing_keypair(key_dir=key_dir)
        public_path = key_dir / "skillbom_ed25519.pub"
        assert public_path.exists()

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="POSIX file permissions not applicable on Windows",
    )
    def test_private_key_has_restrictive_permissions(self, key_dir: Path) -> None:
        generate_signing_keypair(key_dir=key_dir)
        private_path = key_dir / "skillbom_ed25519"
        file_stat = os.stat(private_path)
        mode = stat.S_IMODE(file_stat.st_mode)
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="POSIX file permissions not applicable on Windows",
    )
    def test_public_key_has_standard_permissions(self, key_dir: Path) -> None:
        generate_signing_keypair(key_dir=key_dir)
        public_path = key_dir / "skillbom_ed25519.pub"
        file_stat = os.stat(public_path)
        mode = stat.S_IMODE(file_stat.st_mode)
        assert mode == 0o644, f"Expected 0o644, got {oct(mode)}"

    def test_each_call_produces_unique_keypair(self, tmp_path: Path) -> None:
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        pub_a, _ = generate_signing_keypair(key_dir=dir_a)
        pub_b, _ = generate_signing_keypair(key_dir=dir_b)
        assert pub_a != pub_b


# ---------------------------------------------------------------------------
# Load Keys
# ---------------------------------------------------------------------------


class TestLoadSigningKey:
    def test_loads_valid_private_key(self, key_dir: Path, generated_keys: tuple) -> None:
        priv_bytes = load_signing_key(key_dir / "skillbom_ed25519")
        assert b"PRIVATE KEY" in priv_bytes

    def test_raises_key_not_found_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(KeyNotFoundError):
            load_signing_key(tmp_path / "nonexistent_key")

    def test_loaded_key_matches_generated(
        self, key_dir: Path, generated_keys: tuple
    ) -> None:
        _, expected_priv = generated_keys
        loaded = load_signing_key(key_dir / "skillbom_ed25519")
        assert loaded == expected_priv


class TestLoadVerifyKey:
    def test_loads_valid_public_key(self, key_dir: Path, generated_keys: tuple) -> None:
        pub_bytes = load_verify_key(key_dir / "skillbom_ed25519.pub")
        assert b"PUBLIC KEY" in pub_bytes

    def test_raises_key_not_found_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(KeyNotFoundError):
            load_verify_key(tmp_path / "nonexistent.pub")

    def test_loaded_key_matches_generated(
        self, key_dir: Path, generated_keys: tuple
    ) -> None:
        expected_pub, _ = generated_keys
        loaded = load_verify_key(key_dir / "skillbom_ed25519.pub")
        assert loaded == expected_pub


# ---------------------------------------------------------------------------
# sign_bom
# ---------------------------------------------------------------------------


class TestSignBom:
    def test_returns_signature_result(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        result = sign_bom(bom_content, private_key=priv)
        assert isinstance(result, SignatureResult)

    def test_algorithm_is_ed25519(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        result = sign_bom(bom_content, private_key=priv)
        assert result.algorithm == "ed25519"

    def test_signature_hex_matches_bytes(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        result = sign_bom(bom_content, private_key=priv)
        assert result.signature.hex() == result.signature_hex

    def test_signature_is_64_bytes(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        result = sign_bom(bom_content, private_key=priv)
        assert len(result.signature) == 64

    def test_key_id_is_sha256_hex(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        result = sign_bom(bom_content, private_key=priv)
        # SHA-256 hex is 64 characters
        assert len(result.key_id) == 64
        assert all(c in "0123456789abcdef" for c in result.key_id)

    def test_signed_at_is_aware_datetime(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        from datetime import timezone

        _, priv = generated_keys
        result = sign_bom(bom_content, private_key=priv)
        assert result.signed_at.tzinfo is not None
        assert result.signed_at.tzinfo == timezone.utc

    def test_sign_via_key_path(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        result = sign_bom(bom_content, key_path=key_dir / "skillbom_ed25519")
        assert isinstance(result, SignatureResult)

    def test_raises_key_not_found_when_no_key_available(
        self, tmp_path: Path, bom_content: bytes
    ) -> None:
        missing = tmp_path / "no_such_key"
        with pytest.raises(KeyNotFoundError):
            sign_bom(bom_content, key_path=missing)

    def test_raises_signing_error_for_invalid_key_bytes(
        self, bom_content: bytes
    ) -> None:
        with pytest.raises(SigningError):
            sign_bom(bom_content, private_key=b"not-a-valid-pem-key")


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------


class TestVerifySignature:
    def test_valid_signature_returns_valid_true(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        pub, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        verify_result = verify_signature(bom_content, sign_result.signature, public_key=pub)
        assert verify_result.valid is True
        assert verify_result.error is None

    def test_valid_signature_algorithm_is_ed25519(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        pub, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        verify_result = verify_signature(bom_content, sign_result.signature, public_key=pub)
        assert verify_result.algorithm == "ed25519"

    def test_valid_signature_key_id_matches_signer(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        pub, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        verify_result = verify_signature(bom_content, sign_result.signature, public_key=pub)
        assert verify_result.key_id == sign_result.key_id

    def test_tampered_content_fails_verification(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        pub, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        tampered = bom_content + b" TAMPERED"
        verify_result = verify_signature(tampered, sign_result.signature, public_key=pub)
        assert verify_result.valid is False
        assert verify_result.error is not None

    def test_wrong_key_fails_verification(
        self, tmp_path: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        # Generate a second independent keypair
        other_pub, _ = generate_signing_keypair(key_dir=tmp_path / "other_keys")
        sign_result = sign_bom(bom_content, private_key=priv)
        verify_result = verify_signature(bom_content, sign_result.signature, public_key=other_pub)
        assert verify_result.valid is False

    def test_corrupted_signature_fails_verification(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        pub, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        corrupted_sig = bytes([b ^ 0xFF for b in sign_result.signature])
        verify_result = verify_signature(bom_content, corrupted_sig, public_key=pub)
        assert verify_result.valid is False

    def test_verify_via_key_path(
        self, key_dir: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        verify_result = verify_signature(
            bom_content,
            sign_result.signature,
            key_path=key_dir / "skillbom_ed25519.pub",
        )
        assert verify_result.valid is True

    def test_missing_public_key_returns_invalid(
        self, tmp_path: Path, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        missing_pub = tmp_path / "no_such_key.pub"
        verify_result = verify_signature(
            bom_content, sign_result.signature, key_path=missing_pub
        )
        assert verify_result.valid is False
        assert verify_result.key_id is None
        assert "not found" in (verify_result.error or "").lower()

    def test_invalid_public_key_bytes_returns_invalid(
        self, generated_keys: tuple, bom_content: bytes
    ) -> None:
        _, priv = generated_keys
        sign_result = sign_bom(bom_content, private_key=priv)
        verify_result = verify_signature(
            bom_content, sign_result.signature, public_key=b"garbage"
        )
        assert verify_result.valid is False


# ---------------------------------------------------------------------------
# File Signing
# ---------------------------------------------------------------------------


class TestSignFile:
    def test_creates_sig_file_with_default_path(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        bom_file = tmp_path / "snapshot.json"
        bom_file.write_bytes(b'{"version": "1"}')
        sig_path = sign_file(bom_file, key_path=key_dir / "skillbom_ed25519")
        assert sig_path == bom_file.with_suffix(".json.sig")
        assert sig_path.exists()

    def test_creates_sig_file_at_explicit_output_path(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        bom_file = tmp_path / "snapshot.json"
        bom_file.write_bytes(b'{"version": "2"}')
        out = tmp_path / "custom.sig"
        sig_path = sign_file(bom_file, output_path=out, key_path=key_dir / "skillbom_ed25519")
        assert sig_path == out
        assert out.exists()

    def test_raises_file_not_found_for_missing_input(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        with pytest.raises(FileNotFoundError):
            sign_file(tmp_path / "ghost.json", key_path=key_dir / "skillbom_ed25519")

    def test_signature_file_contains_raw_bytes(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        bom_file = tmp_path / "snapshot.json"
        bom_file.write_bytes(b"content")
        sig_path = sign_file(bom_file, key_path=key_dir / "skillbom_ed25519")
        sig_bytes = sig_path.read_bytes()
        assert len(sig_bytes) == 64  # Ed25519 signature is always 64 bytes


class TestVerifyFile:
    def test_valid_roundtrip(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        pub, _ = generated_keys
        bom_file = tmp_path / "bom.json"
        bom_file.write_bytes(b'{"bom": true}')
        sign_file(bom_file, key_path=key_dir / "skillbom_ed25519")
        result = verify_file(bom_file, key_path=key_dir / "skillbom_ed25519.pub")
        assert result.valid is True
        assert result.error is None

    def test_tampered_file_fails_verification(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        bom_file = tmp_path / "bom.json"
        bom_file.write_bytes(b'{"bom": true}')
        sign_file(bom_file, key_path=key_dir / "skillbom_ed25519")
        # Overwrite content after signing
        bom_file.write_bytes(b'{"bom": false, "tampered": true}')
        result = verify_file(bom_file, key_path=key_dir / "skillbom_ed25519.pub")
        assert result.valid is False

    def test_raises_file_not_found_for_missing_file(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        with pytest.raises(FileNotFoundError):
            verify_file(
                tmp_path / "ghost.json",
                key_path=key_dir / "skillbom_ed25519.pub",
            )

    def test_raises_file_not_found_for_missing_sig_file(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        bom_file = tmp_path / "bom.json"
        bom_file.write_bytes(b"content")
        # No .sig file written
        with pytest.raises(FileNotFoundError):
            verify_file(bom_file, key_path=key_dir / "skillbom_ed25519.pub")

    def test_explicit_signature_path(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        bom_file = tmp_path / "bom.json"
        bom_file.write_bytes(b"explicit sig path test")
        custom_sig = tmp_path / "explicit.sig"
        sign_file(bom_file, output_path=custom_sig, key_path=key_dir / "skillbom_ed25519")
        result = verify_file(
            bom_file,
            signature_path=custom_sig,
            key_path=key_dir / "skillbom_ed25519.pub",
        )
        assert result.valid is True

    def test_wrong_key_fails_verification(
        self, tmp_path: Path, key_dir: Path, generated_keys: tuple
    ) -> None:
        bom_file = tmp_path / "bom.json"
        bom_file.write_bytes(b"content")
        sign_file(bom_file, key_path=key_dir / "skillbom_ed25519")
        # Use a different keypair for verification
        other_dir = tmp_path / "other_keys"
        generate_signing_keypair(key_dir=other_dir)
        result = verify_file(bom_file, key_path=other_dir / "skillbom_ed25519.pub")
        assert result.valid is False
