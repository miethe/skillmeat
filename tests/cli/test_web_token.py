"""Tests for web token CLI commands."""

import json
import re
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main
from skillmeat.core.auth import TokenManager
from skillmeat.core.auth.storage import EncryptedFileStorage


def strip_ansi(text):
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_token_manager():
    """Create mock token manager."""
    with patch("skillmeat.core.auth.TokenManager") as mock_class:
        manager = MagicMock()
        mock_class.return_value = manager
        yield manager


def test_token_generate_basic(cli_runner, mock_token_manager):
    """Test basic token generation command."""
    # Setup mock
    mock_token = MagicMock()
    mock_token.token_id = "test-token-id-12345"
    mock_token.name = "default"
    mock_token.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    mock_token.created_at = datetime.utcnow()
    mock_token.expires_at = datetime.utcnow() + timedelta(days=90)

    mock_token_manager.generate_token.return_value = mock_token

    # Run command
    result = cli_runner.invoke(main, ["web", "token", "generate"])

    # Verify
    assert result.exit_code == 0
    assert "generated successfully" in result.output
    assert "default" in result.output
    mock_token_manager.generate_token.assert_called_once()


def test_token_generate_custom_name(cli_runner, mock_token_manager):
    """Test token generation with custom name."""
    mock_token = MagicMock()
    mock_token.token_id = "test-id"
    mock_token.name = "production"
    mock_token.created_at = datetime.utcnow()
    mock_token.expires_at = None

    mock_token_manager.generate_token.return_value = mock_token

    result = cli_runner.invoke(main, ["web", "token", "generate", "--name", "production"])

    assert result.exit_code == 0
    assert "production" in result.output
    mock_token_manager.generate_token.assert_called_with(name="production", expiration_days=None)


def test_token_generate_with_expiration(cli_runner, mock_token_manager):
    """Test token generation with custom expiration."""
    mock_token = MagicMock()
    mock_token.token_id = "test-id"
    mock_token.name = "default"
    mock_token.created_at = datetime.utcnow()
    mock_token.expires_at = datetime.utcnow() + timedelta(days=365)

    mock_token_manager.generate_token.return_value = mock_token

    result = cli_runner.invoke(main, ["web", "token", "generate", "--days", "365"])

    assert result.exit_code == 0
    mock_token_manager.generate_token.assert_called_with(name="default", expiration_days=365)


def test_token_generate_show_token(cli_runner, mock_token_manager):
    """Test token generation with --show-token flag."""
    mock_token = MagicMock()
    mock_token.token_id = "test-id"
    mock_token.name = "default"
    mock_token.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
    mock_token.created_at = datetime.utcnow()
    mock_token.expires_at = None

    mock_token_manager.generate_token.return_value = mock_token

    result = cli_runner.invoke(main, ["web", "token", "generate", "--show-token"])

    assert result.exit_code == 0
    assert mock_token.token in result.output
    assert "WARNING" in result.output


def test_token_generate_json_output(cli_runner, mock_token_manager):
    """Test token generation with JSON output."""
    created_at = datetime(2025, 1, 1, 12, 0, 0)
    expires_at = datetime(2025, 4, 1, 12, 0, 0)

    mock_token = MagicMock()
    mock_token.token_id = "test-id"
    mock_token.name = "default"
    mock_token.token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
    mock_token.created_at = created_at
    mock_token.expires_at = expires_at

    mock_token_manager.generate_token.return_value = mock_token

    result = cli_runner.invoke(main, ["web", "token", "generate", "--json"])

    assert result.exit_code == 0

    # Parse JSON output (strip ANSI codes first)
    clean_output = strip_ansi(result.output)
    output_data = json.loads(clean_output)
    assert output_data["token_id"] == "test-id"
    assert output_data["name"] == "default"
    assert output_data["created_at"] == created_at.isoformat()
    assert output_data["expires_at"] == expires_at.isoformat()


def test_token_list_empty(cli_runner, mock_token_manager):
    """Test listing tokens when none exist."""
    mock_token_manager.list_tokens.return_value = []

    result = cli_runner.invoke(main, ["web", "token", "list"])

    assert result.exit_code == 0
    assert "No tokens found" in result.output


def test_token_list_with_tokens(cli_runner, mock_token_manager):
    """Test listing tokens."""
    # Create mock token info
    mock_token1 = MagicMock()
    mock_token1.token_id = "token-id-1"
    mock_token1.name = "default"
    mock_token1.created_at = datetime(2025, 1, 1)
    mock_token1.expires_at = datetime(2025, 4, 1)
    mock_token1.last_used = None
    mock_token1.is_expired = False

    mock_token2 = MagicMock()
    mock_token2.token_id = "token-id-2"
    mock_token2.name = "production"
    mock_token2.created_at = datetime(2025, 1, 15)
    mock_token2.expires_at = None
    mock_token2.last_used = datetime(2025, 1, 20)
    mock_token2.is_expired = False

    mock_token_manager.list_tokens.return_value = [mock_token1, mock_token2]

    result = cli_runner.invoke(main, ["web", "token", "list"])

    assert result.exit_code == 0
    assert "default" in result.output
    assert "production" in result.output
    assert "Active" in result.output


def test_token_list_json(cli_runner, mock_token_manager):
    """Test listing tokens with JSON output."""
    created_at = datetime(2025, 1, 1, 12, 0, 0)
    expires_at = datetime(2025, 4, 1, 12, 0, 0)

    mock_token = MagicMock()
    mock_token.token_id = "token-id"
    mock_token.name = "default"
    mock_token.created_at = created_at
    mock_token.expires_at = expires_at
    mock_token.last_used = None
    mock_token.is_expired = False

    mock_token_manager.list_tokens.return_value = [mock_token]

    result = cli_runner.invoke(main, ["web", "token", "list", "--json"])

    assert result.exit_code == 0

    # Parse JSON output (strip ANSI codes first)
    clean_output = strip_ansi(result.output)
    output_data = json.loads(clean_output)
    assert len(output_data) == 1
    assert output_data[0]["token_id"] == "token-id"
    assert output_data[0]["name"] == "default"
    assert output_data[0]["created_at"] == created_at.isoformat()
    assert output_data[0]["expires_at"] == expires_at.isoformat()
    assert output_data[0]["last_used"] is None
    assert output_data[0]["is_expired"] is False


def test_token_revoke_by_id(cli_runner, mock_token_manager):
    """Test revoking token by ID."""
    mock_token_info = MagicMock()
    mock_token_info.name = "default"

    mock_token_manager.get_token_info.return_value = mock_token_info
    mock_token_manager.revoke_token.return_value = True

    result = cli_runner.invoke(
        main, ["web", "token", "revoke", "token-id", "--confirm"], catch_exceptions=False
    )

    assert result.exit_code == 0
    assert "revoked" in result.output.lower()
    mock_token_manager.revoke_token.assert_called_once_with("token-id")


def test_token_revoke_by_name(cli_runner, mock_token_manager):
    """Test revoking token by name."""
    mock_token_manager.get_token_info.return_value = None
    mock_token_manager.revoke_token_by_name.return_value = 1

    result = cli_runner.invoke(
        main, ["web", "token", "revoke", "default", "--confirm"], catch_exceptions=False
    )

    assert result.exit_code == 0
    assert "revoked" in result.output.lower()


def test_token_revoke_not_found(cli_runner, mock_token_manager):
    """Test revoking non-existent token."""
    mock_token_manager.get_token_info.return_value = None
    mock_token_manager.revoke_token_by_name.return_value = 0

    result = cli_runner.invoke(
        main, ["web", "token", "revoke", "nonexistent", "--confirm"], catch_exceptions=False
    )

    assert result.exit_code == 1
    clean_output = strip_ansi(result.output)
    assert "no token found" in clean_output.lower()


def test_token_revoke_all(cli_runner, mock_token_manager):
    """Test revoking all tokens."""
    mock_token_manager.revoke_all_tokens.return_value = 5

    result = cli_runner.invoke(
        main, ["web", "token", "revoke", "--all", "--confirm", "dummy"], catch_exceptions=False
    )

    assert result.exit_code == 0
    assert "5" in result.output
    mock_token_manager.revoke_all_tokens.assert_called_once()


def test_token_cleanup_no_expired(cli_runner, mock_token_manager):
    """Test cleanup when no expired tokens."""
    mock_token_manager.list_tokens.return_value = []

    result = cli_runner.invoke(main, ["web", "token", "cleanup"])

    assert result.exit_code == 0
    assert "No expired tokens" in result.output


def test_token_cleanup_with_expired(cli_runner, mock_token_manager):
    """Test cleanup with expired tokens."""
    expired_token = MagicMock()
    expired_token.name = "old-token"
    expired_token.expires_at = datetime.utcnow() - timedelta(days=1)
    expired_token.is_expired = True

    mock_token_manager.list_tokens.return_value = [expired_token]
    mock_token_manager.cleanup_expired_tokens.return_value = 1

    result = cli_runner.invoke(main, ["web", "token", "cleanup", "--confirm"])

    assert result.exit_code == 0
    assert "Removed" in result.output
    assert "1" in result.output


def test_token_info(cli_runner, mock_token_manager):
    """Test getting token info."""
    mock_token_info = MagicMock()
    mock_token_info.name = "default"
    mock_token_info.token_id = "token-id-12345"
    mock_token_info.created_at = datetime(2025, 1, 1, 12, 0, 0)
    mock_token_info.expires_at = datetime(2025, 4, 1, 12, 0, 0)
    mock_token_info.last_used = datetime(2025, 1, 15, 10, 30, 0)
    mock_token_info.is_expired = False

    mock_token_manager.get_token_info.return_value = mock_token_info

    result = cli_runner.invoke(main, ["web", "token", "info", "token-id-12345"])

    assert result.exit_code == 0
    clean_output = strip_ansi(result.output)
    assert "default" in clean_output
    assert "token-id-12345" in clean_output
    assert "Active" in clean_output


def test_token_info_not_found(cli_runner, mock_token_manager):
    """Test getting info for non-existent token."""
    mock_token_manager.get_token_info.return_value = None
    mock_token_manager.list_tokens.return_value = []

    result = cli_runner.invoke(main, ["web", "token", "info", "nonexistent"])

    assert result.exit_code == 1
    clean_output = strip_ansi(result.output)
    assert "no token found" in clean_output.lower()


@pytest.mark.integration
def test_token_generate_integration(cli_runner, tmp_path):
    """Integration test for token generation."""
    # Use real storage
    from skillmeat.core.auth.storage import EncryptedFileStorage

    storage_dir = tmp_path / "tokens"
    storage = EncryptedFileStorage(storage_dir=storage_dir)

    with patch("skillmeat.core.auth.token_manager.get_storage_backend", return_value=storage):
        result = cli_runner.invoke(main, ["web", "token", "generate", "--name", "test"])

        assert result.exit_code == 0
        assert "generated successfully" in result.output

        # Verify token was actually stored
        tokens = storage.list_tokens()
        assert len(tokens) > 0


@pytest.mark.integration
def test_token_list_integration(cli_runner, tmp_path):
    """Integration test for token listing."""
    from skillmeat.core.auth import TokenManager
    from skillmeat.core.auth.storage import EncryptedFileStorage

    storage_dir = tmp_path / "tokens"
    storage = EncryptedFileStorage(storage_dir=storage_dir)

    # Create some tokens
    manager = TokenManager(storage=storage)
    manager.generate_token(name="token1", expiration_days=30)
    manager.generate_token(name="token2", expiration_days=60)

    with patch("skillmeat.core.auth.token_manager.get_storage_backend", return_value=storage):
        result = cli_runner.invoke(main, ["web", "token", "list"])

        assert result.exit_code == 0
        assert "token1" in result.output
        assert "token2" in result.output


@pytest.mark.integration
def test_token_revoke_integration(cli_runner, tmp_path):
    """Integration test for token revocation."""
    from skillmeat.core.auth import TokenManager
    from skillmeat.core.auth.storage import EncryptedFileStorage

    storage_dir = tmp_path / "tokens"
    storage = EncryptedFileStorage(storage_dir=storage_dir)

    # Create token
    manager = TokenManager(storage=storage)
    token = manager.generate_token(name="test-token")

    with patch("skillmeat.core.auth.token_manager.get_storage_backend", return_value=storage):
        # Revoke token
        result = cli_runner.invoke(
            main, ["web", "token", "revoke", token.token_id, "--confirm"]
        )

        assert result.exit_code == 0
        assert "revoked" in result.output.lower()

        # Verify token is gone
        info = manager.get_token_info(token.token_id)
        assert info is None
