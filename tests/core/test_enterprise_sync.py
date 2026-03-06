"""Unit tests for EnterpriseSyncer.

Covers:
- check() returns up_to_date=True when hash matches stored state
- check() returns up_to_date=False when hash differs (or no prior state)
- sync() skips file writes when up_to_date=True
- sync() materialises files when hash differs
- Sync state file is updated with new hash after successful sync
- Base64-encoded files are decoded correctly
- API errors are surfaced in result.error without raising
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from skillmeat.core.enterprise_sync import EnterpriseSyncer, EnterpriseSyncResult

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SYNC_STATE_FILE = ".skillmeat-enterprise-sync.toml"


def _mock_payload(
    artifact_name: str,
    content_hash: str,
    files: list[dict] | None = None,
) -> dict:
    return {
        "metadata": {"name": artifact_name, "type": "skill", "version": "1.0"},
        "content_hash": content_hash,
        "files": files or [],
    }


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = payload
    if status_code >= 400:
        http_error = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def _read_sync_state(target_dir: Path) -> dict:
    state_file = target_dir / _SYNC_STATE_FILE
    if not state_file.exists():
        return {}
    with open(state_file, "rb") as fh:
        return tomllib.load(fh)


def _write_initial_hash(target_dir: Path, artifact_name: str, content_hash: str) -> None:
    """Pre-seed the sync state file so tests can simulate prior syncs."""
    import tomli_w

    state = {
        "artifacts": {
            artifact_name: {
                "content_hash": content_hash,
                "synced_at": "2026-01-01T00:00:00+00:00",
            }
        }
    }
    state_file = target_dir / _SYNC_STATE_FILE
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(state_file, "wb") as fh:
        tomli_w.dump(state, fh)


# ---------------------------------------------------------------------------
# Tests: check() — up_to_date logic
# ---------------------------------------------------------------------------


class TestCheckUpToDate:
    """check() compares stored hash with API hash; never writes files."""

    def test_check_up_to_date_when_hashes_match(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "my-skill", "abc123")

        payload = _mock_payload("my-skill", "abc123")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().check("my-skill", target_dir=tmp_path)

        assert result.up_to_date is True
        assert result.updated is False
        assert result.new_hash == "abc123"
        assert result.old_hash == "abc123"

    def test_check_not_up_to_date_when_hash_differs(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "my-skill", "old_hash")

        payload = _mock_payload("my-skill", "new_hash")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().check("my-skill", target_dir=tmp_path)

        assert result.up_to_date is False
        assert result.updated is False
        assert result.old_hash == "old_hash"
        assert result.new_hash == "new_hash"

    def test_check_not_up_to_date_when_no_prior_state(self, tmp_path: Path, monkeypatch):
        """No sync state file → first check always reports not up-to-date."""
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        # No prior state seeded

        payload = _mock_payload("fresh-art", "xyz789")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().check("fresh-art", target_dir=tmp_path)

        assert result.up_to_date is False
        assert result.old_hash == ""
        assert result.new_hash == "xyz789"

    def test_check_does_not_write_files(self, tmp_path: Path, monkeypatch):
        """check() never writes artifact files even when hash differs."""
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "old")

        payload = _mock_payload(
            "art",
            "new_hash",
            files=[{"path": "SKILL.md", "content": "content", "encoding": "utf-8"}],
        )
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().check("art", target_dir=tmp_path)

        assert result.updated is False
        assert result.files_updated == 0
        # No artifact file should have been written
        assert not (tmp_path / "SKILL.md").exists()

    def test_check_does_not_update_sync_state(self, tmp_path: Path, monkeypatch):
        """check() never modifies .skillmeat-enterprise-sync.toml."""
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "old_hash")

        payload = _mock_payload("art", "new_hash")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseSyncer().check("art", target_dir=tmp_path)

        # Stored hash must still be "old_hash"
        state = _read_sync_state(tmp_path)
        assert state["artifacts"]["art"]["content_hash"] == "old_hash"


# ---------------------------------------------------------------------------
# Tests: sync() — skip when up-to-date
# ---------------------------------------------------------------------------


class TestSyncSkipsWhenUpToDate:
    """sync() returns early without file I/O when hashes match."""

    def test_sync_returns_up_to_date_result(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "cached-art", "same_hash")

        payload = _mock_payload("cached-art", "same_hash", files=[
            {"path": "SKILL.md", "content": "should not be written", "encoding": "utf-8"},
        ])
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().sync("cached-art", target_dir=tmp_path)

        assert result.up_to_date is True
        assert result.updated is False
        assert result.files_updated == 0

    def test_sync_does_not_write_files_when_up_to_date(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "match")

        payload = _mock_payload("art", "match", files=[
            {"path": "should_not_exist.md", "content": "x"},
        ])
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseSyncer().sync("art", target_dir=tmp_path)

        assert not (tmp_path / "should_not_exist.md").exists()

    def test_sync_does_not_update_hash_when_up_to_date(self, tmp_path: Path, monkeypatch):
        """synced_at timestamp should not change when already up-to-date."""
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "same")

        # Record the original synced_at
        state_before = _read_sync_state(tmp_path)
        synced_at_before = state_before["artifacts"]["art"]["synced_at"]

        payload = _mock_payload("art", "same")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseSyncer().sync("art", target_dir=tmp_path)

        state_after = _read_sync_state(tmp_path)
        assert state_after["artifacts"]["art"]["synced_at"] == synced_at_before


# ---------------------------------------------------------------------------
# Tests: sync() — materialise files when hash differs
# ---------------------------------------------------------------------------


class TestSyncMaterialisesFiles:
    """sync() writes files when remote hash differs from stored hash."""

    def test_sync_writes_files_when_hash_differs(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "old_hash")

        payload = _mock_payload(
            "art",
            "new_hash",
            files=[
                {"path": "SKILL.md", "content": "# Updated skill\n", "encoding": "utf-8"},
                {"path": "src/helper.py", "content": "# helper\n", "encoding": "utf-8"},
            ],
        )
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().sync("art", target_dir=tmp_path)

        assert result.updated is True
        assert result.files_updated == 2
        assert (tmp_path / "SKILL.md").read_text() == "# Updated skill\n"
        assert (tmp_path / "src" / "helper.py").read_text() == "# helper\n"

    def test_sync_writes_files_on_first_sync(self, tmp_path: Path, monkeypatch):
        """No prior state → sync materialises files."""
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = _mock_payload(
            "new-art",
            "first_hash",
            files=[{"path": "SKILL.md", "content": "first content\n", "encoding": "utf-8"}],
        )
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().sync("new-art", target_dir=tmp_path)

        assert result.updated is True
        assert result.files_updated == 1
        assert (tmp_path / "SKILL.md").read_text() == "first content\n"

    def test_sync_handles_base64_encoded_files(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        raw_bytes = b"\x89PNG\r\n\x1a\n"  # PNG header
        encoded = base64.b64encode(raw_bytes).decode("ascii")

        payload = _mock_payload(
            "binary-art",
            "bin_hash",
            files=[{"path": "icon.png", "content": encoded, "encoding": "base64"}],
        )
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().sync("binary-art", target_dir=tmp_path)

        assert result.updated is True
        assert (tmp_path / "icon.png").read_bytes() == raw_bytes

    def test_sync_result_hashes(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "hash_v1")

        payload = _mock_payload("art", "hash_v2")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseSyncer().sync("art", target_dir=tmp_path)

        assert result.old_hash == "hash_v1"
        assert result.new_hash == "hash_v2"
        assert result.up_to_date is False


# ---------------------------------------------------------------------------
# Tests: sync state persistence
# ---------------------------------------------------------------------------


class TestSyncStatePersistence:
    """New hash is written to .skillmeat-enterprise-sync.toml after sync."""

    def test_new_hash_persisted_after_sync(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "old_hash")

        payload = _mock_payload("art", "new_hash")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseSyncer().sync("art", target_dir=tmp_path)

        state = _read_sync_state(tmp_path)
        assert state["artifacts"]["art"]["content_hash"] == "new_hash"

    def test_sync_state_file_created_on_first_sync(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = _mock_payload("brand-new", "first_hash")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseSyncer().sync("brand-new", target_dir=tmp_path)

        assert (tmp_path / _SYNC_STATE_FILE).exists()
        state = _read_sync_state(tmp_path)
        assert state["artifacts"]["brand-new"]["content_hash"] == "first_hash"

    def test_sync_state_preserves_other_artifacts(self, tmp_path: Path, monkeypatch):
        """Syncing one artifact does not remove other artifacts from state."""
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        import tomli_w

        # Seed two artifacts
        state = {
            "artifacts": {
                "art-a": {"content_hash": "hash_a", "synced_at": "2026-01-01T00:00:00+00:00"},
                "art-b": {"content_hash": "old_b", "synced_at": "2026-01-01T00:00:00+00:00"},
            }
        }
        with open(tmp_path / _SYNC_STATE_FILE, "wb") as fh:
            tomli_w.dump(state, fh)

        # Sync only art-b
        payload = _mock_payload("art-b", "new_b")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseSyncer().sync("art-b", target_dir=tmp_path)

        final_state = _read_sync_state(tmp_path)
        assert final_state["artifacts"]["art-a"]["content_hash"] == "hash_a"
        assert final_state["artifacts"]["art-b"]["content_hash"] == "new_b"

    def test_synced_at_updated_after_sync(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")
        _write_initial_hash(tmp_path, "art", "old_hash")

        old_state = _read_sync_state(tmp_path)
        old_ts = old_state["artifacts"]["art"]["synced_at"]

        payload = _mock_payload("art", "new_hash")
        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseSyncer().sync("art", target_dir=tmp_path)

        new_state = _read_sync_state(tmp_path)
        new_ts = new_state["artifacts"]["art"]["synced_at"]
        # Timestamp must have advanced
        assert new_ts >= old_ts


# ---------------------------------------------------------------------------
# Tests: atomic writes in sync
# ---------------------------------------------------------------------------


class TestSyncAtomicWrites:
    """Files are written via temp file + Path.replace."""

    def test_replace_called_for_each_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = _mock_payload(
            "art",
            "h",
            files=[
                {"path": "a.md", "content": "a", "encoding": "utf-8"},
                {"path": "b.md", "content": "b", "encoding": "utf-8"},
            ],
        )

        replace_calls: list = []
        original_replace = Path.replace

        def tracking_replace(self_path, target):
            replace_calls.append(target)
            return original_replace(self_path, target)

        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=_mock_response(payload),
        ), patch.object(Path, "replace", tracking_replace):
            EnterpriseSyncer().sync("art", target_dir=tmp_path)

        # At least 2 calls for the 2 content files (plus 1 for sync state TOML)
        assert len(replace_calls) >= 2


# ---------------------------------------------------------------------------
# Tests: API error handling
# ---------------------------------------------------------------------------


class TestSyncAPIErrors:
    """API errors are surfaced in result.error without raising."""

    def test_http_error_sets_result_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        mock_resp = _mock_response({}, status_code=404)

        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=mock_resp,
        ):
            result = EnterpriseSyncer().sync("missing", target_dir=tmp_path)

        assert result.error is not None
        assert result.updated is False

    def test_check_http_error_sets_result_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        mock_resp = _mock_response({}, status_code=500)

        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=mock_resp,
        ):
            result = EnterpriseSyncer().check("bad-art", target_dir=tmp_path)

        assert result.error is not None
        assert result.up_to_date is False
        assert result.updated is False

    def test_network_exception_set_as_error(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            side_effect=requests.ConnectionError("network down"),
        ):
            result = EnterpriseSyncer().sync("art", target_dir=tmp_path)

        assert result.error is not None
        assert "network down" in result.error
        assert result.updated is False

    def test_sync_no_exception_raised_on_http_error(self, tmp_path: Path, monkeypatch):
        """sync() never raises — errors surface in result.error."""
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        mock_resp = _mock_response({}, status_code=403)

        with patch(
            "skillmeat.core.enterprise_sync.enterprise_request",
            return_value=mock_resp,
        ):
            # Must not raise
            result = EnterpriseSyncer().sync("forbidden-art", target_dir=tmp_path)

        assert result.error is not None
