"""Tests for skillmeat.core.bom.signing — Ed25519 BOM signing module."""
from __future__ import annotations

import os
import platform
import stat
from pathlib import Path
from typing import Optional

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from skillmeat.core.bom.signing import (
    ChainValidationResult,
    KeyGenerationError,
    KeyNotFoundError,
    SignatureResult,
    SigningError,
    VerificationError,
    VerificationResult,
    auto_sign_bom,
    generate_signing_keypair,
    is_auto_sign_enabled,
    load_signing_key,
    load_verify_key,
    sign_bom,
    sign_file,
    validate_signature_chain,
    verify_bom,
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


# ---------------------------------------------------------------------------
# Helpers shared by new test classes
# ---------------------------------------------------------------------------


def _make_snapshot(
    bom_json: str,
    parent_hash: Optional[str] = None,
    sign_with: Optional[bytes] = None,
) -> dict:
    """Build a snapshot dict, optionally signing it with a PEM private key."""
    import hashlib as _hashlib

    content_hash = _hashlib.sha256(bom_json.encode()).hexdigest()
    signature_hex: Optional[str] = None
    if sign_with is not None:
        result = sign_bom(bom_json.encode(), private_key=sign_with)
        signature_hex = result.signature_hex
    return {
        "bom_json": bom_json,
        "content_hash": content_hash,
        "parent_hash": parent_hash,
        "signature": signature_hex,
    }


# ---------------------------------------------------------------------------
# validate_signature_chain
# ---------------------------------------------------------------------------


class TestValidateSignatureChain:
    def test_empty_chain_is_valid(self) -> None:
        result = validate_signature_chain([])
        assert result.valid is True
        assert result.chain_length == 0
        assert result.verified_count == 0
        assert result.unsigned_count == 0
        assert result.first_break_at is None
        assert result.errors == []

    def test_single_unsigned_snapshot(self) -> None:
        snap = _make_snapshot('{"artifacts": []}')
        result = validate_signature_chain([snap])
        assert result.valid is True
        assert result.chain_length == 1
        assert result.verified_count == 0
        assert result.unsigned_count == 1
        assert result.first_break_at is None

    def test_valid_chain_all_signed(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        snap0 = _make_snapshot('{"v": 1}', sign_with=priv_pem)
        snap1 = _make_snapshot('{"v": 2}', parent_hash=snap0["content_hash"], sign_with=priv_pem)
        snap2 = _make_snapshot('{"v": 3}', parent_hash=snap1["content_hash"], sign_with=priv_pem)

        result = validate_signature_chain([snap0, snap1, snap2], public_key=pub_pem)
        assert result.valid is True
        assert result.chain_length == 3
        assert result.verified_count == 3
        assert result.unsigned_count == 0
        assert result.first_break_at is None
        assert result.errors == []

    def test_broken_chain_parent_hash_mismatch(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        snap0 = _make_snapshot('{"v": 1}', sign_with=priv_pem)
        # Deliberately wrong parent_hash (not the hash of snap0)
        snap1 = _make_snapshot('{"v": 2}', parent_hash="deadbeef" * 8, sign_with=priv_pem)

        result = validate_signature_chain([snap0, snap1], public_key=pub_pem)
        assert result.valid is False
        assert result.first_break_at == 1
        assert any("parent_hash mismatch" in e for e in result.errors)

    def test_chain_with_unsigned_snapshots(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        snap0 = _make_snapshot('{"v": 1}', sign_with=priv_pem)
        snap1 = _make_snapshot('{"v": 2}', parent_hash=snap0["content_hash"])  # unsigned
        snap2 = _make_snapshot('{"v": 3}', parent_hash=snap1["content_hash"], sign_with=priv_pem)

        result = validate_signature_chain([snap0, snap1, snap2], public_key=pub_pem)
        # Parent hash links are correct, so chain is intact
        assert result.valid is True
        assert result.verified_count == 2
        assert result.unsigned_count == 1
        assert result.first_break_at is None

    def test_tampered_signature_breaks_chain(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        snap0 = _make_snapshot('{"v": 1}', sign_with=priv_pem)
        snap1 = _make_snapshot('{"v": 2}', parent_hash=snap0["content_hash"], sign_with=priv_pem)

        # Tamper with snap1's signature (flip all bytes via XOR)
        raw_sig = bytes.fromhex(snap1["signature"])
        tampered_hex = bytes(b ^ 0xFF for b in raw_sig).hex()
        snap1_tampered = {**snap1, "signature": tampered_hex}

        result = validate_signature_chain([snap0, snap1_tampered], public_key=pub_pem)
        assert result.valid is False
        assert result.first_break_at == 1
        assert any("signature invalid" in e for e in result.errors)

    def test_content_hash_mismatch_detected(self) -> None:
        bom_json = '{"v": 1}'
        snap = {
            "bom_json": bom_json,
            "content_hash": "a" * 64,  # wrong hash
            "parent_hash": None,
            "signature": None,
        }
        result = validate_signature_chain([snap])
        assert result.valid is False
        assert any("content_hash mismatch" in e for e in result.errors)

    def test_invalid_signature_hex_detected(self) -> None:
        snap = _make_snapshot('{"v": 1}')
        snap["signature"] = "not-valid-hex!!!"
        result = validate_signature_chain([snap])
        assert result.valid is False
        assert any("not valid hex" in e for e in result.errors)

    def test_chain_verified_count_excludes_unsigned(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        snaps = [_make_snapshot(f'{{"v": {i}}}') for i in range(5)]
        # link parent hashes
        for i in range(1, 5):
            snaps[i]["parent_hash"] = snaps[i - 1]["content_hash"]

        result = validate_signature_chain(snaps, public_key=pub_pem)
        assert result.valid is True
        assert result.unsigned_count == 5
        assert result.verified_count == 0


# ---------------------------------------------------------------------------
# verify_bom
# ---------------------------------------------------------------------------


class TestVerifyBom:
    def test_valid_signed_bom_dict(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        bom_json = '{"artifacts": [{"name": "foo"}]}'
        sign_result = sign_bom(bom_json.encode(), private_key=priv_pem)

        bom_data = {
            "bom_json": bom_json,
            "signature": sign_result.signature_hex,
        }

        # Load the public key so default path isn't needed
        import unittest.mock as mock
        with mock.patch(
            "skillmeat.core.bom.signing.load_verify_key",
            return_value=pub_pem,
        ):
            result = verify_bom(bom_data)

        assert result.valid is True
        assert result.error is None

    def test_missing_signature_field_returns_invalid(self) -> None:
        bom_data = {"bom_json": '{"v": 1}'}
        result = verify_bom(bom_data)
        assert result.valid is False
        assert "No signature" in (result.error or "")

    def test_tampered_bom_json_fails_verification(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        original = '{"artifacts": []}'
        sign_result = sign_bom(original.encode(), private_key=priv_pem)

        bom_data = {
            "bom_json": '{"artifacts": [{"name": "injected"}]}',  # tampered
            "signature": sign_result.signature_hex,
        }

        import unittest.mock as mock
        with mock.patch(
            "skillmeat.core.bom.signing.load_verify_key",
            return_value=pub_pem,
        ):
            result = verify_bom(bom_data)

        assert result.valid is False

    def test_invalid_hex_signature_returns_invalid(self) -> None:
        bom_data = {
            "bom_json": '{"v": 1}',
            "signature": "zzznotvalidhex",
        }
        result = verify_bom(bom_data)
        assert result.valid is False
        assert "not valid hex" in (result.error or "").lower()

    def test_empty_signature_field_returns_invalid(self) -> None:
        bom_data = {"bom_json": '{"v": 1}', "signature": ""}
        result = verify_bom(bom_data)
        assert result.valid is False

    def test_fallback_payload_serialisation(self, tmp_path: Path) -> None:
        """verify_bom falls back to serialising non-bom_json fields when no bom_json key."""
        import json as _json

        key_dir = tmp_path / "keys"
        pub_pem, priv_pem = generate_signing_keypair(key_dir=key_dir)

        # Build canonical payload (the dict without 'signature', sorted keys)
        payload = {"artifacts": [], "version": "1.0.0"}
        canonical = _json.dumps(payload, sort_keys=True, separators=(",", ":"))
        sign_result = sign_bom(canonical.encode(), private_key=priv_pem)

        bom_data = {**payload, "signature": sign_result.signature_hex}

        import unittest.mock as mock
        with mock.patch(
            "skillmeat.core.bom.signing.load_verify_key",
            return_value=pub_pem,
        ):
            result = verify_bom(bom_data)

        assert result.valid is True


# ---------------------------------------------------------------------------
# Auto-sign feature flag
# ---------------------------------------------------------------------------


class TestIsAutoSignEnabled:
    def test_disabled_by_default(self, monkeypatch) -> None:
        monkeypatch.delenv("SKILLBOM_AUTO_SIGN", raising=False)
        assert is_auto_sign_enabled() is False

    def test_enabled_with_1(self, monkeypatch) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "1")
        assert is_auto_sign_enabled() is True

    def test_enabled_with_true(self, monkeypatch) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "true")
        assert is_auto_sign_enabled() is True

    def test_enabled_with_yes(self, monkeypatch) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "yes")
        assert is_auto_sign_enabled() is True

    def test_enabled_case_insensitive(self, monkeypatch) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "TRUE")
        assert is_auto_sign_enabled() is True

    def test_disabled_with_false(self, monkeypatch) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "false")
        assert is_auto_sign_enabled() is False

    def test_disabled_with_empty_string(self, monkeypatch) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "")
        assert is_auto_sign_enabled() is False

    def test_disabled_with_zero(self, monkeypatch) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "0")
        assert is_auto_sign_enabled() is False


class TestAutoSignBom:
    def test_returns_none_when_disabled(self, monkeypatch, bom_content: bytes) -> None:
        monkeypatch.delenv("SKILLBOM_AUTO_SIGN", raising=False)
        result = auto_sign_bom(bom_content)
        assert result is None

    def test_returns_signature_result_when_enabled(
        self, tmp_path: Path, monkeypatch, bom_content: bytes
    ) -> None:
        key_dir = tmp_path / "keys"
        generate_signing_keypair(key_dir=key_dir)
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "1")
        result = auto_sign_bom(bom_content, key_path=key_dir / "skillbom_ed25519")
        assert isinstance(result, SignatureResult)
        assert result.algorithm == "ed25519"

    def test_returns_none_when_enabled_but_key_missing(
        self, tmp_path: Path, monkeypatch, bom_content: bytes
    ) -> None:
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "1")
        missing_key = tmp_path / "no_key_here"
        result = auto_sign_bom(bom_content, key_path=missing_key)
        assert result is None  # swallowed KeyNotFoundError

    def test_signature_is_verifiable(
        self, tmp_path: Path, monkeypatch, bom_content: bytes
    ) -> None:
        key_dir = tmp_path / "keys"
        pub_pem, _ = generate_signing_keypair(key_dir=key_dir)
        monkeypatch.setenv("SKILLBOM_AUTO_SIGN", "1")

        sign_result = auto_sign_bom(bom_content, key_path=key_dir / "skillbom_ed25519")
        assert sign_result is not None

        verify_result = verify_signature(
            bom_content,
            sign_result.signature,
            public_key=pub_pem,
        )
        assert verify_result.valid is True
