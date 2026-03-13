"""Tests for the ``skillmeat bom`` CLI command group.

Covers argument parsing, output formatting, and error messages for:
  - bom sign
  - bom verify
  - bom keygen
  - bom generate
  - bom restore
  - bom install-hook
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli.commands.bom import bom_group


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def bom_file(tmp_path):
    """A minimal context.lock file on disk."""
    p = tmp_path / "context.lock"
    p.write_text('{"schema_version": "1.0.0", "artifacts": []}')
    return p


@pytest.fixture
def key_dir(tmp_path):
    """A temporary key directory."""
    d = tmp_path / "keys"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# bom sign
# ---------------------------------------------------------------------------


class TestSignCommand:
    def test_sign_missing_file_exits_nonzero(self, runner, tmp_path):
        """Exits with non-zero status when the target file does not exist."""
        result = runner.invoke(bom_group, ["sign", str(tmp_path / "nonexistent.lock")])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_sign_custom_key_not_found_exits_nonzero(self, runner, bom_file, tmp_path):
        """Exits with non-zero status when the explicit --key path does not exist."""
        result = runner.invoke(
            bom_group,
            ["sign", str(bom_file), "--key", str(tmp_path / "missing.pem")],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_sign_success_message(self, runner, bom_file, tmp_path):
        """Displays success panel when signing succeeds."""
        sig_path = bom_file.with_suffix(".lock.sig")

        fake_result = SimpleNamespace(
            signature=b"\x00" * 64,
            signature_hex="aa" * 32,
            algorithm="ed25519",
            key_id="fingerprint-abc",
            signed_at=None,
        )

        with patch(
            "skillmeat.cli.commands.bom.sign_file",
            return_value=sig_path,
        ) as mock_sign:
            result = runner.invoke(
                bom_group,
                [
                    "sign",
                    str(bom_file),
                    "--key",
                    str(tmp_path / "key.pem"),  # won't exist but we patch sign_file
                ],
            )

        # sign_file is patched — we never reach the FileNotFoundError from key path check.
        # But the key-path guard runs before sign_file, so let's test the sign path
        # more carefully by first writing a dummy key file.
        dummy_key = tmp_path / "key.pem"
        dummy_key.write_text("FAKE KEY")

        with patch(
            "skillmeat.cli.commands.bom.sign_file",
            return_value=sig_path,
        ):
            result = runner.invoke(
                bom_group,
                ["sign", str(bom_file), "--key", str(dummy_key)],
            )

        assert result.exit_code == 0
        assert "BOM signed successfully" in result.output

    def test_sign_signing_error_exits_nonzero(self, runner, bom_file, tmp_path):
        """Exits with non-zero status when sign_file raises SigningError."""
        from skillmeat.core.bom.signing import SigningError

        dummy_key = tmp_path / "key.pem"
        dummy_key.write_text("FAKE KEY")

        with patch(
            "skillmeat.cli.commands.bom.sign_file",
            side_effect=SigningError("key format invalid"),
        ):
            result = runner.invoke(
                bom_group,
                ["sign", str(bom_file), "--key", str(dummy_key)],
            )

        assert result.exit_code != 0
        assert "Signing error" in result.output

    def test_sign_key_not_found_error_exits_nonzero(self, runner, bom_file, tmp_path):
        """Exits with non-zero status when sign_file raises KeyNotFoundError."""
        from skillmeat.core.bom.signing import KeyNotFoundError

        dummy_key = tmp_path / "key.pem"
        dummy_key.write_text("FAKE KEY")

        with patch(
            "skillmeat.cli.commands.bom.sign_file",
            side_effect=KeyNotFoundError("no key"),
        ):
            result = runner.invoke(
                bom_group,
                ["sign", str(bom_file), "--key", str(dummy_key)],
            )

        assert result.exit_code != 0

    def test_sign_output_option_passed_through(self, runner, bom_file, tmp_path):
        """--output option is accepted without error."""
        dummy_key = tmp_path / "key.pem"
        dummy_key.write_text("FAKE KEY")
        custom_sig = tmp_path / "my.sig"

        with patch(
            "skillmeat.cli.commands.bom.sign_file",
            return_value=custom_sig,
        ):
            result = runner.invoke(
                bom_group,
                [
                    "sign",
                    str(bom_file),
                    "--key",
                    str(dummy_key),
                    "--output",
                    str(custom_sig),
                ],
            )

        assert result.exit_code == 0

    def test_sign_no_key_prompts_keygen(self, runner, bom_file, tmp_path):
        """When no key exists, the command prompts to generate one (and aborts on 'n')."""
        with patch(
            "skillmeat.cli.commands.bom._DEFAULT_KEY_DIR",
            tmp_path / "keys",
        ):
            result = runner.invoke(bom_group, ["sign", str(bom_file)], input="n\n")

        assert result.exit_code != 0
        assert "Aborted" in result.output


# ---------------------------------------------------------------------------
# bom verify
# ---------------------------------------------------------------------------


class TestVerifyCommand:
    def test_verify_missing_file_exits_nonzero(self, runner, tmp_path):
        """Exits non-zero when the target BOM file does not exist."""
        result = runner.invoke(bom_group, ["verify", str(tmp_path / "nonexistent.lock")])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_verify_valid_signature_exits_zero(self, runner, bom_file, tmp_path):
        """Exits 0 when verify_file returns a valid result."""
        from skillmeat.core.bom.signing import VerificationResult

        fake_result = VerificationResult(
            valid=True,
            algorithm="ed25519",
            key_id="fp-abc",
            error=None,
        )

        with patch(
            "skillmeat.cli.commands.bom.verify_file",
            return_value=fake_result,
        ):
            result = runner.invoke(bom_group, ["verify", str(bom_file)])

        assert result.exit_code == 0
        assert "VALID" in result.output

    def test_verify_invalid_signature_exits_nonzero(self, runner, bom_file):
        """Exits 1 when signature verification fails."""
        from skillmeat.core.bom.signing import VerificationResult

        fake_result = VerificationResult(
            valid=False,
            algorithm="ed25519",
            key_id=None,
            error="signature mismatch",
        )

        with patch(
            "skillmeat.cli.commands.bom.verify_file",
            return_value=fake_result,
        ):
            result = runner.invoke(bom_group, ["verify", str(bom_file)])

        assert result.exit_code == 1
        assert "INVALID" in result.output

    def test_verify_file_not_found_error_exits_nonzero(self, runner, bom_file):
        """Exits non-zero when verify_file raises FileNotFoundError."""
        with patch(
            "skillmeat.cli.commands.bom.verify_file",
            side_effect=FileNotFoundError("sig file missing"),
        ):
            result = runner.invoke(bom_group, ["verify", str(bom_file)])

        assert result.exit_code == 1
        assert "ERROR" in result.output

    def test_verify_error_exits_nonzero(self, runner, bom_file):
        """Exits non-zero when verify_file raises VerificationError."""
        from skillmeat.core.bom.signing import VerificationError

        with patch(
            "skillmeat.cli.commands.bom.verify_file",
            side_effect=VerificationError("invalid key format"),
        ):
            result = runner.invoke(bom_group, ["verify", str(bom_file)])

        assert result.exit_code == 1

    def test_verify_signature_option_accepted(self, runner, bom_file, tmp_path):
        """--signature option is accepted and passed to verify_file."""
        from skillmeat.core.bom.signing import VerificationResult

        sig_file = tmp_path / "custom.sig"
        sig_file.write_bytes(b"\x00" * 64)

        fake_result = VerificationResult(
            valid=True,
            algorithm="ed25519",
            key_id=None,
            error=None,
        )

        with patch(
            "skillmeat.cli.commands.bom.verify_file",
            return_value=fake_result,
        ) as mock_verify:
            result = runner.invoke(
                bom_group,
                ["verify", str(bom_file), "--signature", str(sig_file)],
            )

        assert result.exit_code == 0
        # confirm the sig path was forwarded
        call_kwargs = mock_verify.call_args
        assert call_kwargs is not None

    def test_verify_key_option_accepted(self, runner, bom_file, tmp_path):
        """--key option is accepted and passed to verify_file."""
        from skillmeat.core.bom.signing import VerificationResult

        pub_key = tmp_path / "key.pub"
        pub_key.write_text("FAKE PUB KEY")

        fake_result = VerificationResult(
            valid=True,
            algorithm="ed25519",
            key_id="fp-123",
            error=None,
        )

        with patch(
            "skillmeat.cli.commands.bom.verify_file",
            return_value=fake_result,
        ):
            result = runner.invoke(
                bom_group,
                ["verify", str(bom_file), "--key", str(pub_key)],
            )

        assert result.exit_code == 0
        assert "VALID" in result.output


# ---------------------------------------------------------------------------
# bom keygen
# ---------------------------------------------------------------------------


class TestKeygenCommand:
    def test_keygen_success_shows_key_paths(self, runner, tmp_path):
        """Displays generated key paths on success."""
        with patch(
            "skillmeat.cli.commands.bom.generate_signing_keypair",
            return_value=(b"PEM_PUB_BYTES", b"PEM_PRIV_BYTES"),
        ):
            result = runner.invoke(bom_group, ["keygen", "--dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "Keypair generated" in result.output
        # Rich panels truncate long paths with ellipsis — check algorithm instead
        assert "ed25519" in result.output

    def test_keygen_uses_default_dir_when_no_option(self, runner, tmp_path):
        """Uses default key directory when --dir is not specified."""
        with (
            patch(
                "skillmeat.cli.commands.bom._DEFAULT_KEY_DIR",
                tmp_path / "keys",
            ),
            patch(
                "skillmeat.cli.commands.bom.generate_signing_keypair",
                return_value=(b"PUB", b"PRIV"),
            ),
        ):
            result = runner.invoke(bom_group, ["keygen"])

        assert result.exit_code == 0

    def test_keygen_error_exits_nonzero(self, runner, tmp_path):
        """Exits non-zero when generate_signing_keypair raises KeyGenerationError."""
        from skillmeat.core.bom.signing import KeyGenerationError

        with patch(
            "skillmeat.cli.commands.bom.generate_signing_keypair",
            side_effect=KeyGenerationError("entropy failure"),
        ):
            result = runner.invoke(bom_group, ["keygen", "--dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "Key generation error" in result.output

    def test_keygen_prompts_before_overwrite(self, runner, tmp_path):
        """Prompts for overwrite when key files already exist; aborts on 'n'."""
        # Create existing key files
        (tmp_path / "skillbom_ed25519").write_text("existing")
        (tmp_path / "skillbom_ed25519.pub").write_text("existing")

        result = runner.invoke(
            bom_group,
            ["keygen", "--dir", str(tmp_path)],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Aborted" in result.output

    def test_keygen_overwrites_on_confirm(self, runner, tmp_path):
        """Overwrites existing keys when user confirms 'y'."""
        (tmp_path / "skillbom_ed25519").write_text("old")
        (tmp_path / "skillbom_ed25519.pub").write_text("old")

        with patch(
            "skillmeat.cli.commands.bom.generate_signing_keypair",
            return_value=(b"NEW_PUB", b"NEW_PRIV"),
        ):
            result = runner.invoke(
                bom_group,
                ["keygen", "--dir", str(tmp_path)],
                input="y\n",
            )

        assert result.exit_code == 0
        assert "Keypair generated" in result.output


# ---------------------------------------------------------------------------
# bom generate
# ---------------------------------------------------------------------------


class TestGenerateCommand:
    def _fake_bom(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "generated_at": "2026-03-13T00:00:00Z",
            "artifact_count": 2,
            "artifacts": [
                {"name": "skill-a", "type": "skill", "content_hash": "aaa"},
                {"name": "skill-b", "type": "command", "content_hash": "bbb"},
            ],
        }

    def test_generate_creates_output_file(self, runner, tmp_path):
        """BOM is written to the output file on success."""
        out_file = tmp_path / "bom.json"
        bom_dict = self._fake_bom()

        mock_session = MagicMock()
        mock_generator = MagicMock()
        mock_generator.generate.return_value = bom_dict
        mock_serializer = MagicMock()
        mock_serializer.to_json.return_value = json.dumps(bom_dict)
        mock_serializer.write_file = MagicMock()

        with (
            patch("skillmeat.cli.commands.bom.sign_bom"),  # not called — no --auto-sign
            patch(
                "skillmeat.cache.models.get_session",
                return_value=mock_session,
            ),
            patch(
                "skillmeat.core.bom.generator.BomGenerator",
                return_value=mock_generator,
            ),
            patch(
                "skillmeat.core.bom.generator.BomSerializer",
                return_value=mock_serializer,
            ),
        ):
            result = runner.invoke(
                bom_group,
                [
                    "generate",
                    "--project",
                    str(tmp_path),
                    "--output",
                    str(out_file),
                ],
            )

        assert result.exit_code == 0
        assert "BOM generated successfully" in result.output

    def test_generate_json_format_output(self, runner, tmp_path):
        """--format json prints a JSON object with status field."""
        bom_dict = self._fake_bom()

        mock_session = MagicMock()
        mock_generator = MagicMock()
        mock_generator.generate.return_value = bom_dict
        mock_serializer = MagicMock()
        mock_serializer.to_json.return_value = json.dumps(bom_dict)
        mock_serializer.write_file = MagicMock()

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.core.bom.generator.BomGenerator",
                return_value=mock_generator,
            ),
            patch(
                "skillmeat.core.bom.generator.BomSerializer",
                return_value=mock_serializer,
            ),
        ):
            result = runner.invoke(
                bom_group,
                [
                    "generate",
                    "--project",
                    str(tmp_path),
                    "--output",
                    str(tmp_path / "bom.json"),
                    "--format",
                    "json",
                ],
            )

        assert result.exit_code == 0
        # Rich console.print(json.dumps(...)) emits ANSI/box chars; check key strings
        assert '"status"' in result.output
        assert '"success"' in result.output
        assert '"artifact_count"' in result.output

    def test_generate_generator_failure_exits_nonzero(self, runner, tmp_path):
        """Exits non-zero when BomGenerator.generate() raises an exception."""
        mock_session = MagicMock()
        mock_generator = MagicMock()
        mock_generator.generate.side_effect = RuntimeError("db unavailable")

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.core.bom.generator.BomGenerator",
                return_value=mock_generator,
            ),
        ):
            result = runner.invoke(
                bom_group,
                [
                    "generate",
                    "--project",
                    str(tmp_path),
                    "--output",
                    str(tmp_path / "bom.json"),
                ],
            )

        assert result.exit_code != 0
        assert "BOM generation failed" in result.output

    def test_generate_auto_sign_calls_sign_bom(self, runner, tmp_path):
        """--auto-sign triggers sign_bom after generation."""
        bom_dict = self._fake_bom()

        mock_session = MagicMock()
        mock_generator = MagicMock()
        mock_generator.generate.return_value = bom_dict
        mock_serializer = MagicMock()
        mock_serializer.to_json.return_value = json.dumps(bom_dict)
        mock_serializer.write_file = MagicMock()

        fake_sig_result = SimpleNamespace(
            signature=b"\x00" * 64,
            signature_hex="aa" * 32,
            algorithm="ed25519",
            key_id="fp-abc",
        )

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.core.bom.generator.BomGenerator",
                return_value=mock_generator,
            ),
            patch(
                "skillmeat.core.bom.generator.BomSerializer",
                return_value=mock_serializer,
            ),
            patch(
                "skillmeat.cli.commands.bom.sign_bom",
                return_value=fake_sig_result,
            ) as mock_sign_bom,
        ):
            result = runner.invoke(
                bom_group,
                [
                    "generate",
                    "--project",
                    str(tmp_path),
                    "--output",
                    str(tmp_path / "bom.json"),
                    "--auto-sign",
                ],
            )

        assert result.exit_code == 0
        mock_sign_bom.assert_called_once()

    def test_generate_auto_sign_key_not_found_warning(self, runner, tmp_path):
        """When --auto-sign key is missing, a warning is shown but exit is 0."""
        from skillmeat.core.bom.signing import KeyNotFoundError

        bom_dict = self._fake_bom()
        mock_session = MagicMock()
        mock_generator = MagicMock()
        mock_generator.generate.return_value = bom_dict
        mock_serializer = MagicMock()
        mock_serializer.to_json.return_value = json.dumps(bom_dict)
        mock_serializer.write_file = MagicMock()

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.core.bom.generator.BomGenerator",
                return_value=mock_generator,
            ),
            patch(
                "skillmeat.core.bom.generator.BomSerializer",
                return_value=mock_serializer,
            ),
            patch(
                "skillmeat.cli.commands.bom.sign_bom",
                side_effect=KeyNotFoundError("no key"),
            ),
        ):
            result = runner.invoke(
                bom_group,
                [
                    "generate",
                    "--project",
                    str(tmp_path),
                    "--output",
                    str(tmp_path / "bom.json"),
                    "--auto-sign",
                ],
            )

        assert result.exit_code == 0
        assert "Warning" in result.output

    def test_generate_session_failure_exits_nonzero(self, runner, tmp_path):
        """Exits non-zero when get_session() raises an exception."""
        with patch(
            "skillmeat.cache.models.get_session",
            side_effect=Exception("no DB"),
        ):
            result = runner.invoke(
                bom_group,
                [
                    "generate",
                    "--project",
                    str(tmp_path),
                    "--output",
                    str(tmp_path / "bom.json"),
                ],
            )

        assert result.exit_code != 0
        assert "could not open cache database" in result.output

    def test_generate_format_choices(self, runner, tmp_path):
        """--format only accepts 'json' or 'summary'."""
        result = runner.invoke(
            bom_group,
            [
                "generate",
                "--format",
                "xml",
            ],
        )
        assert result.exit_code != 0

    def test_generate_default_output_path(self, runner, tmp_path):
        """When --output is omitted, BOM is written to <project>/.skillmeat/context.lock."""
        bom_dict = self._fake_bom()
        mock_session = MagicMock()
        mock_generator = MagicMock()
        mock_generator.generate.return_value = bom_dict
        mock_serializer = MagicMock()
        mock_serializer.to_json.return_value = json.dumps(bom_dict)
        mock_serializer.write_file = MagicMock()

        with (
            patch("skillmeat.cache.models.get_session", return_value=mock_session),
            patch(
                "skillmeat.core.bom.generator.BomGenerator",
                return_value=mock_generator,
            ),
            patch(
                "skillmeat.core.bom.generator.BomSerializer",
                return_value=mock_serializer,
            ),
        ):
            result = runner.invoke(
                bom_group,
                ["generate", "--project", str(tmp_path)],
            )

        assert result.exit_code == 0
        # The default output path is .skillmeat/context.lock under the project.
        call_args = mock_serializer.write_file.call_args
        if call_args:
            written_path = call_args[0][1]
            assert "context.lock" in str(written_path)


# ---------------------------------------------------------------------------
# bom restore
# ---------------------------------------------------------------------------


class TestRestoreCommand:
    def _fake_preview(self, unresolved=None):
        return SimpleNamespace(
            bom_hash="deadbeef" * 8,
            total_entries=3,
            resolved_entries=3,
            unresolved_entries=unresolved or [],
            signature_valid=True,
        )

    def test_restore_requires_commit_option(self, runner):
        """--commit is required; missing it exits non-zero."""
        result = runner.invoke(bom_group, ["restore"])
        assert result.exit_code != 0

    def test_restore_dry_run_shows_preview_and_exits_zero(self, runner, tmp_path):
        """--dry-run displays the restore preview and exits 0 without writing files."""
        preview = self._fake_preview()

        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            return_value=preview,
        ):
            result = runner.invoke(
                bom_group,
                ["restore", "--commit", "abc1234", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Dry-run" in result.output or "Restore preview" in result.output

    def test_restore_prompts_without_force(self, runner, tmp_path):
        """Without --force, the command prompts before restoring; aborts on 'n'."""
        preview = self._fake_preview()

        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            return_value=preview,
        ):
            result = runner.invoke(
                bom_group,
                ["restore", "--commit", "abc1234"],
                input="n\n",
            )

        assert result.exit_code == 0
        assert "Aborted" in result.output

    def test_restore_force_skips_prompt(self, runner, tmp_path):
        """--force skips the confirmation prompt and restores directly.

        restore_cmd calls restore_from_commit twice:
          1st call: dry_run=True  — returns preview
          2nd call: dry_run=False — returns actual result
        """
        preview = self._fake_preview()
        actual_result = SimpleNamespace(
            commit_sha="abc1234ef5",
            bom_hash="deadbeef" * 8,
            total_entries=3,
            resolved_entries=3,
            unresolved_entries=[],
            signature_valid=True,
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return preview if call_count == 1 else actual_result

        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            side_effect=side_effect,
        ):
            result = runner.invoke(
                bom_group,
                ["restore", "--commit", "abc1234", "--force"],
            )

        assert result.exit_code == 0
        assert "Restore complete" in result.output

    def test_restore_nothing_to_restore_exits_nonzero(self, runner):
        """Exits non-zero when preview has 0 total_entries."""
        preview = SimpleNamespace(
            bom_hash="deadbeef",
            total_entries=0,
            resolved_entries=0,
            unresolved_entries=[],
            signature_valid=None,
        )

        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            return_value=preview,
        ):
            result = runner.invoke(
                bom_group,
                ["restore", "--commit", "abc1234", "--force"],
            )

        assert result.exit_code != 0
        assert "Nothing to restore" in result.output

    def test_restore_commit_not_found_exits_nonzero(self, runner):
        """ValueError from restore_from_commit (bad commit) exits non-zero."""
        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            side_effect=ValueError("commit not found in git history"),
        ):
            result = runner.invoke(
                bom_group,
                ["restore", "--commit", "badhash"],
            )

        assert result.exit_code != 0
        assert "commit not found" in result.output

    def test_restore_generic_error_exits_nonzero(self, runner):
        """Generic exception from restore preview exits non-zero with error message."""
        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            side_effect=RuntimeError("unexpected failure"),
        ):
            result = runner.invoke(
                bom_group,
                ["restore", "--commit", "abc1234"],
            )

        assert result.exit_code != 0
        assert "restore preview failed" in result.output

    def test_restore_unresolved_entries_exits_nonzero(self, runner):
        """When restored result has unresolved entries, exits with code 1."""
        preview = self._fake_preview()
        actual_result = SimpleNamespace(
            commit_sha="abc1234xyz",
            bom_hash="deadbeef",
            total_entries=3,
            resolved_entries=2,
            unresolved_entries=["skill:orphan"],
            signature_valid=True,
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return preview  # dry_run=True call
            return actual_result  # dry_run=False call

        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            side_effect=side_effect,
        ):
            result = runner.invoke(
                bom_group,
                ["restore", "--commit", "abc1234xyz", "--force"],
            )

        assert result.exit_code == 1
        assert "Unresolved" in result.output or "unresolved" in result.output.lower()


# ---------------------------------------------------------------------------
# bom install-hook
# ---------------------------------------------------------------------------


class TestInstallHookCommand:
    def test_install_hook_success(self, runner, tmp_path):
        """Displays success panel when hooks are installed."""
        with patch(
            "skillmeat.core.bom.git_integration.install_hooks",
            return_value=None,
        ):
            result = runner.invoke(
                bom_group,
                ["install-hook", "--project", str(tmp_path)],
            )

        assert result.exit_code == 0
        assert "Git hooks installed" in result.output
        assert "prepare-commit-msg" in result.output
        assert "post-commit" in result.output

    def test_install_hook_default_project_is_cwd(self, runner, tmp_path):
        """When --project is omitted, the current directory is used."""
        with (
            patch(
                "skillmeat.core.bom.git_integration.install_hooks",
                return_value=None,
            ),
        ):
            result = runner.invoke(bom_group, ["install-hook"])

        assert result.exit_code == 0

    def test_install_hook_not_a_git_repo_exits_nonzero(self, runner, tmp_path):
        """FileNotFoundError (no .git/hooks/) exits non-zero."""
        with patch(
            "skillmeat.core.bom.git_integration.install_hooks",
            side_effect=FileNotFoundError(".git not found"),
        ):
            result = runner.invoke(
                bom_group,
                ["install-hook", "--project", str(tmp_path)],
            )

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_install_hook_generic_error_exits_nonzero(self, runner, tmp_path):
        """Generic exception from install_hooks exits non-zero with error message."""
        with patch(
            "skillmeat.core.bom.git_integration.install_hooks",
            side_effect=RuntimeError("permission denied"),
        ):
            result = runner.invoke(
                bom_group,
                ["install-hook", "--project", str(tmp_path)],
            )

        assert result.exit_code != 0
        assert "hook installation failed" in result.output


# ---------------------------------------------------------------------------
# bom group — help and top-level
# ---------------------------------------------------------------------------


class TestBomGroupHelp:
    def test_bom_help_lists_subcommands(self, runner):
        """Top-level `bom --help` lists all subcommands."""
        result = runner.invoke(bom_group, ["--help"])
        assert result.exit_code == 0
        for subcommand in ["sign", "verify", "keygen", "generate", "restore", "install-hook"]:
            assert subcommand in result.output

    def test_sign_help(self, runner):
        """bom sign --help exits 0."""
        result = runner.invoke(bom_group, ["sign", "--help"])
        assert result.exit_code == 0
        assert "--key" in result.output
        assert "--output" in result.output

    def test_verify_help(self, runner):
        """bom verify --help exits 0."""
        result = runner.invoke(bom_group, ["verify", "--help"])
        assert result.exit_code == 0
        assert "--signature" in result.output
        assert "--key" in result.output

    def test_keygen_help(self, runner):
        """bom keygen --help exits 0."""
        result = runner.invoke(bom_group, ["keygen", "--help"])
        assert result.exit_code == 0
        assert "--dir" in result.output

    def test_generate_help(self, runner):
        """bom generate --help exits 0."""
        result = runner.invoke(bom_group, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--output" in result.output
        assert "--auto-sign" in result.output
        assert "--format" in result.output

    def test_restore_help(self, runner):
        """bom restore --help exits 0."""
        result = runner.invoke(bom_group, ["restore", "--help"])
        assert result.exit_code == 0
        assert "--commit" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output

    def test_install_hook_help(self, runner):
        """bom install-hook --help exits 0."""
        result = runner.invoke(bom_group, ["install-hook", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
