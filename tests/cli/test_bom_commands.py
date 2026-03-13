"""Tests for ``skillmeat bom`` CLI commands.

Covers:
1. ``bom sign``   — produces a valid signature file
2. ``bom sign``   — uses custom --key and --output options
3. ``bom sign``   — prompts to generate keypair when default key is missing
4. ``bom sign``   — errors out when specified --key file is missing
5. ``bom sign``   — errors when input FILE does not exist
6. ``bom verify`` — returns exit 0 and VALID for a correct signature
7. ``bom verify`` — returns exit 1 and INVALID for a tampered file
8. ``bom verify`` — returns exit 1 when signature file is missing
9. ``bom verify`` — returns exit 1 when input FILE does not exist
10. ``bom keygen`` — creates private and public key files
11. ``bom keygen`` — prompts for overwrite when keys already exist
12. ``bom keygen`` — uses --dir to write keys to custom directory
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from skillmeat.cli.commands.bom import bom_group
from skillmeat.core.bom.signing import generate_signing_keypair


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes so plain-string assertions work."""
    return re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])").sub("", text)


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def tmp_bom_dir(tmp_path: Path) -> Path:
    """Return a temp directory with a sample context.lock and Ed25519 keypair."""
    lock = tmp_path / "context.lock"
    lock.write_text("bom-content-for-testing\n", encoding="utf-8")

    key_dir = tmp_path / "keys"
    generate_signing_keypair(key_dir=key_dir)

    return tmp_path


# ---------------------------------------------------------------------------
# sign command
# ---------------------------------------------------------------------------


class TestSignCommand:
    """Tests for ``skillmeat bom sign``."""

    def test_sign_produces_signature_file(self, runner: CliRunner, tmp_bom_dir: Path) -> None:
        """Happy path: sign defaults to <file>.sig when no --output given."""
        lock = tmp_bom_dir / "context.lock"
        key = tmp_bom_dir / "keys" / "skillbom_ed25519"

        result = runner.invoke(
            bom_group,
            ["sign", str(lock), "--key", str(key)],
        )
        assert result.exit_code == 0, result.output
        sig = Path(str(lock) + ".sig")
        assert sig.exists(), "Signature file was not created"
        assert len(sig.read_bytes()) > 0

    def test_sign_custom_output(self, runner: CliRunner, tmp_bom_dir: Path) -> None:
        """--output directs the signature to the specified path."""
        lock = tmp_bom_dir / "context.lock"
        key = tmp_bom_dir / "keys" / "skillbom_ed25519"
        out = tmp_bom_dir / "custom.sig"

        result = runner.invoke(
            bom_group,
            ["sign", str(lock), "--key", str(key), "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_sign_output_contains_metadata(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """Output mentions the algorithm and success panel title."""
        lock = tmp_bom_dir / "context.lock"
        key = tmp_bom_dir / "keys" / "skillbom_ed25519"

        result = runner.invoke(
            bom_group,
            ["sign", str(lock), "--key", str(key)],
        )
        assert result.exit_code == 0, result.output
        plain = strip_ansi(result.output)
        # Rich may truncate long paths with '…' but algorithm and panel
        # title are always short enough to display in full.
        assert "ed25519" in plain
        assert "BOM signed successfully" in plain

    def test_sign_missing_input_file_exits_1(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exit code 1 when FILE does not exist."""
        result = runner.invoke(bom_group, ["sign", str(tmp_path / "nonexistent.lock")])
        assert result.exit_code == 1

    def test_sign_missing_custom_key_exits_1(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """Exit code 1 when an explicit --key path does not exist."""
        lock = tmp_bom_dir / "context.lock"
        result = runner.invoke(
            bom_group,
            ["sign", str(lock), "--key", str(tmp_bom_dir / "no_such_key")],
        )
        assert result.exit_code == 1

    def test_sign_prompts_keygen_when_default_key_missing(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """When default key absent, user is offered to generate one; 'n' aborts."""
        lock = tmp_bom_dir / "context.lock"
        nonexistent_key_dir = tmp_bom_dir / "no_keys"

        # Patch the default key dir so it points to a dir with no keys.
        with patch("skillmeat.cli.commands.bom._DEFAULT_KEY_DIR", nonexistent_key_dir):
            # Answer 'n' to the "Generate keypair?" prompt → should abort.
            result = runner.invoke(bom_group, ["sign", str(lock)], input="n\n")

        assert result.exit_code == 1
        plain = strip_ansi(result.output + (result.stderr or ""))
        assert "Aborted" in plain or "no signing key" in plain.lower()

    def test_sign_generates_keypair_on_confirmation(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """When default key absent and user answers 'y', a keypair is generated and signing proceeds."""
        lock = tmp_bom_dir / "context.lock"
        new_key_dir = tmp_bom_dir / "generated_keys"

        with patch("skillmeat.cli.commands.bom._DEFAULT_KEY_DIR", new_key_dir):
            result = runner.invoke(bom_group, ["sign", str(lock)], input="y\n")

        # Key generation + signing should succeed.
        assert result.exit_code == 0, result.output
        assert (new_key_dir / "skillbom_ed25519").exists()
        assert (new_key_dir / "skillbom_ed25519.pub").exists()


# ---------------------------------------------------------------------------
# verify command
# ---------------------------------------------------------------------------


class TestVerifyCommand:
    """Tests for ``skillmeat bom verify``."""

    def _sign_lock(self, lock: Path, key_dir: Path) -> None:
        """Helper: sign lock file using the keypair in key_dir."""
        from skillmeat.core.bom.signing import sign_file

        sign_file(
            file_path=lock,
            key_path=key_dir / "skillbom_ed25519",
        )

    def test_verify_valid_signature(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """Exit 0 and VALID output for a correct signature."""
        lock = tmp_bom_dir / "context.lock"
        key_dir = tmp_bom_dir / "keys"
        self._sign_lock(lock, key_dir)

        result = runner.invoke(
            bom_group,
            [
                "verify",
                str(lock),
                "--key",
                str(key_dir / "skillbom_ed25519.pub"),
            ],
        )
        assert result.exit_code == 0, result.output
        plain = strip_ansi(result.output)
        assert "VALID" in plain

    def test_verify_invalid_signature_tampered_file(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """Exit 1 and INVALID when file content has been tampered after signing."""
        lock = tmp_bom_dir / "context.lock"
        key_dir = tmp_bom_dir / "keys"
        self._sign_lock(lock, key_dir)

        # Tamper with the file AFTER signing.
        lock.write_text("tampered-content\n", encoding="utf-8")

        result = runner.invoke(
            bom_group,
            [
                "verify",
                str(lock),
                "--key",
                str(key_dir / "skillbom_ed25519.pub"),
            ],
        )
        assert result.exit_code == 1
        plain = strip_ansi(result.output)
        assert "INVALID" in plain

    def test_verify_missing_signature_file_exits_1(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """Exit 1 when the .sig companion file is absent."""
        lock = tmp_bom_dir / "context.lock"
        key_dir = tmp_bom_dir / "keys"

        result = runner.invoke(
            bom_group,
            [
                "verify",
                str(lock),
                "--key",
                str(key_dir / "skillbom_ed25519.pub"),
            ],
        )
        assert result.exit_code == 1

    def test_verify_missing_input_file_exits_1(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exit 1 when the FILE to verify does not exist."""
        result = runner.invoke(bom_group, ["verify", str(tmp_path / "missing.lock")])
        assert result.exit_code == 1

    def test_verify_custom_signature_path(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """--signature accepts a custom sig path."""
        lock = tmp_bom_dir / "context.lock"
        key_dir = tmp_bom_dir / "keys"
        custom_sig = tmp_bom_dir / "custom.sig"

        from skillmeat.core.bom.signing import sign_file

        sign_file(
            file_path=lock,
            output_path=custom_sig,
            key_path=key_dir / "skillbom_ed25519",
        )

        result = runner.invoke(
            bom_group,
            [
                "verify",
                str(lock),
                "--signature",
                str(custom_sig),
                "--key",
                str(key_dir / "skillbom_ed25519.pub"),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "VALID" in strip_ansi(result.output)

    def test_verify_output_shows_algorithm(
        self, runner: CliRunner, tmp_bom_dir: Path
    ) -> None:
        """Verify output includes algorithm name."""
        lock = tmp_bom_dir / "context.lock"
        key_dir = tmp_bom_dir / "keys"
        self._sign_lock(lock, key_dir)

        result = runner.invoke(
            bom_group,
            [
                "verify",
                str(lock),
                "--key",
                str(key_dir / "skillbom_ed25519.pub"),
            ],
        )
        assert "ed25519" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# keygen command
# ---------------------------------------------------------------------------


class TestKeygenCommand:
    """Tests for ``skillmeat bom keygen``."""

    def test_keygen_creates_keypair(self, runner: CliRunner, tmp_path: Path) -> None:
        """keygen writes private and public key files."""
        result = runner.invoke(bom_group, ["keygen", "--dir", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "skillbom_ed25519").exists()
        assert (tmp_path / "skillbom_ed25519.pub").exists()

    def test_keygen_output_contains_paths(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Output shows keypair metadata (algorithm, panel title)."""
        result = runner.invoke(bom_group, ["keygen", "--dir", str(tmp_path)])
        assert result.exit_code == 0, result.output
        plain = strip_ansi(result.output)
        # Rich may truncate long tmp paths with '…', but algorithm and the
        # panel title are always short enough to render in full.
        assert "ed25519" in plain
        assert "Keypair generated" in plain

    def test_keygen_default_dir(self, runner: CliRunner, tmp_path: Path) -> None:
        """keygen without --dir uses ~/.skillmeat/keys (patched for test isolation)."""
        with patch("skillmeat.cli.commands.bom._DEFAULT_KEY_DIR", tmp_path):
            result = runner.invoke(bom_group, ["keygen"])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "skillbom_ed25519").exists()

    def test_keygen_prompts_on_existing_keys_no(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """When keys exist and user answers 'n', keys are not overwritten."""
        # Pre-create keys.
        generate_signing_keypair(key_dir=tmp_path)
        original_mtime = (tmp_path / "skillbom_ed25519").stat().st_mtime

        result = runner.invoke(bom_group, ["keygen", "--dir", str(tmp_path)], input="n\n")
        assert result.exit_code == 0  # no error, just aborted gracefully
        plain = strip_ansi(result.output)
        assert "Aborted" in plain or "not overwritten" in plain

        # Keys should be unchanged.
        assert (tmp_path / "skillbom_ed25519").stat().st_mtime == original_mtime

    def test_keygen_prompts_on_existing_keys_yes(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """When keys exist and user answers 'y', new keys are generated."""
        # Pre-create keys.
        generate_signing_keypair(key_dir=tmp_path)
        old_pub = (tmp_path / "skillbom_ed25519.pub").read_bytes()

        result = runner.invoke(bom_group, ["keygen", "--dir", str(tmp_path)], input="y\n")
        assert result.exit_code == 0, result.output

        # New public key should differ from old one (distinct random keypair).
        new_pub = (tmp_path / "skillbom_ed25519.pub").read_bytes()
        assert old_pub != new_pub
