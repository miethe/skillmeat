"""Unit tests for EnterpriseDeployer.

Covers:
- Correct endpoint is called for download
- Files from response are written to the right subdirectory under target_dir
- .skillmeat-deployed.toml is created/updated with artifact metadata
- Non-2xx API response returns DeployResult(success=False) without raising
- Atomic writes: temp file is used then renamed (os.replace / Path.replace)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from skillmeat.core.enterprise_deploy import DeployResult, EnterpriseDeployer

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response with json() returning *payload*."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = payload
    if status_code >= 400:
        http_error = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def _read_deployed_toml(target_dir: Path) -> list[dict]:
    deployed_file = target_dir / ".skillmeat-deployed.toml"
    with open(deployed_file, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("deployed", [])


# ---------------------------------------------------------------------------
# Tests: correct API endpoint
# ---------------------------------------------------------------------------


class TestDeployEndpointCall:
    """enterprise_request is called with the right method and path."""

    def test_calls_download_endpoint(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "my-skill", "type": "skill", "version": "1.0.0"},
            "content_hash": "abc123",
            "files": [],
        }
        mock_resp = _mock_response(payload)

        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=mock_resp,
        ) as mock_req:
            EnterpriseDeployer().deploy("my-skill", target_dir=tmp_path)

        mock_req.assert_called_once_with(
            "GET",
            "/api/v1/artifacts/my-skill/download",
            timeout=30,
        )

    def test_artifact_name_url_encoded_correctly(self, tmp_path: Path, monkeypatch):
        """Artifact names with colons (type:name format) appear verbatim in path."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "my-cmd", "type": "command", "version": "2.0"},
            "content_hash": "def456",
            "files": [],
        }
        mock_resp = _mock_response(payload)

        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=mock_resp,
        ) as mock_req:
            EnterpriseDeployer().deploy("command:my-cmd", target_dir=tmp_path)

        mock_req.assert_called_once_with(
            "GET",
            "/api/v1/artifacts/command:my-cmd/download",
            timeout=30,
        )


# ---------------------------------------------------------------------------
# Tests: file materialisation
# ---------------------------------------------------------------------------


class TestFileMaterialisation:
    """Files from the API response land in the correct subdirectory."""

    def test_files_written_to_correct_path(self, tmp_path: Path, monkeypatch):
        """skill files land under <target_dir>/skills/<name>/."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "canvas", "type": "skill", "version": "1.0"},
            "content_hash": "aaa",
            "files": [
                {"path": "SKILL.md", "content": "# Canvas skill"},
                {"path": "src/main.py", "content": "print('hello')"},
            ],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseDeployer().deploy("canvas", target_dir=tmp_path)

        assert result.success is True
        assert (tmp_path / "skills" / "canvas" / "SKILL.md").read_text() == "# Canvas skill"
        assert (tmp_path / "skills" / "canvas" / "src" / "main.py").read_text() == "print('hello')"

    def test_command_files_in_commands_subdir(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "my-cmd", "type": "command", "version": "0.1"},
            "content_hash": "bbb",
            "files": [{"path": "cmd.md", "content": "do stuff"}],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseDeployer().deploy("my-cmd", target_dir=tmp_path)

        assert result.success is True
        assert (tmp_path / "commands" / "my-cmd" / "cmd.md").exists()

    def test_unknown_type_falls_back_to_skills(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "thing", "type": "exotic_type", "version": "1.0"},
            "content_hash": "ccc",
            "files": [{"path": "README.md", "content": "readme"}],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseDeployer().deploy("thing", target_dir=tmp_path)

        # Falls back to "skills" subdir
        assert result.success is True
        assert (tmp_path / "skills" / "thing" / "README.md").exists()

    def test_empty_path_entry_is_skipped(self, tmp_path: Path, monkeypatch):
        """File entries with empty path are ignored gracefully."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "art", "type": "skill", "version": "1.0"},
            "content_hash": "ddd",
            "files": [
                {"path": "", "content": "ignored"},
                {"path": "real.md", "content": "kept"},
            ],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseDeployer().deploy("art", target_dir=tmp_path)

        assert result.success is True
        assert len(result.files_written) == 1
        assert "real.md" in result.files_written[0]

    def test_result_contains_written_paths(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "demo", "type": "skill", "version": "2.0"},
            "content_hash": "eee",
            "files": [
                {"path": "a.md", "content": "A"},
                {"path": "b.md", "content": "B"},
            ],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            result = EnterpriseDeployer().deploy("demo", target_dir=tmp_path)

        assert len(result.files_written) == 2
        # Paths are relative to target_dir
        for p in result.files_written:
            assert not Path(p).is_absolute()
        assert result.target_path == tmp_path / "skills" / "demo"


# ---------------------------------------------------------------------------
# Tests: .skillmeat-deployed.toml tracking
# ---------------------------------------------------------------------------


class TestDeployedToml:
    """Deployment record is written correctly to .skillmeat-deployed.toml."""

    def test_toml_created_on_first_deploy(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "first", "type": "skill", "version": "1.0"},
            "content_hash": "hash1",
            "files": [{"path": "SKILL.md", "content": "x"}],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseDeployer().deploy("first", target_dir=tmp_path)

        records = _read_deployed_toml(tmp_path)
        assert len(records) == 1
        assert records[0]["artifact_name"] == "first"
        assert records[0]["artifact_type"] == "skill"
        assert records[0]["from_collection"] == "enterprise"
        assert records[0]["enterprise_version"] == "1.0"

    def test_toml_updated_on_second_deploy(self, tmp_path: Path, monkeypatch):
        """Re-deploying the same artifact replaces the existing record."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload_v1 = {
            "metadata": {"name": "art", "type": "skill", "version": "1.0"},
            "content_hash": "hash1",
            "files": [{"path": "f.md", "content": "v1"}],
        }
        payload_v2 = {
            "metadata": {"name": "art", "type": "skill", "version": "2.0"},
            "content_hash": "hash2",
            "files": [{"path": "f.md", "content": "v2"}],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload_v1),
        ):
            EnterpriseDeployer().deploy("art", target_dir=tmp_path)

        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload_v2),
        ):
            EnterpriseDeployer().deploy("art", target_dir=tmp_path)

        records = _read_deployed_toml(tmp_path)
        # Only one record for the same artifact
        enterprise_records = [r for r in records if r["artifact_name"] == "art"]
        assert len(enterprise_records) == 1
        assert enterprise_records[0]["enterprise_version"] == "2.0"

    def test_toml_accumulates_multiple_artifacts(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        for name, version in [("art-a", "1.0"), ("art-b", "1.0")]:
            payload = {
                "metadata": {"name": name, "type": "skill", "version": version},
                "content_hash": f"hash-{name}",
                "files": [],
            }
            with patch(
                "skillmeat.core.enterprise_deploy.enterprise_request",
                return_value=_mock_response(payload),
            ):
                EnterpriseDeployer().deploy(name, target_dir=tmp_path)

        records = _read_deployed_toml(tmp_path)
        names = {r["artifact_name"] for r in records}
        assert names == {"art-a", "art-b"}

    def test_toml_artifact_path_field(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "skill-x", "type": "skill", "version": "3.0"},
            "content_hash": "hash3",
            "files": [],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseDeployer().deploy("skill-x", target_dir=tmp_path)

        records = _read_deployed_toml(tmp_path)
        assert records[0]["artifact_path"] == "skills/skill-x"

    def test_toml_enterprise_files_list(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "multi", "type": "skill", "version": "1.0"},
            "content_hash": "h",
            "files": [
                {"path": "SKILL.md", "content": "s"},
                {"path": "src/a.py", "content": "a"},
            ],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseDeployer().deploy("multi", target_dir=tmp_path)

        records = _read_deployed_toml(tmp_path)
        files = records[0]["enterprise_files"]
        assert len(files) == 2


# ---------------------------------------------------------------------------
# Tests: non-2xx response handling
# ---------------------------------------------------------------------------


class TestNon2xxHandling:
    """Non-2xx responses return DeployResult(success=False) without raising."""

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500, 503])
    def test_http_error_returns_failure_result(
        self, status_code: int, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        mock_resp = _mock_response({}, status_code=status_code)

        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=mock_resp,
        ):
            result = EnterpriseDeployer().deploy("missing", target_dir=tmp_path)

        assert result.success is False
        assert result.error is not None
        assert str(status_code) in result.error
        assert result.artifact_name == "missing"

    def test_no_exception_raised_on_http_error(self, tmp_path: Path, monkeypatch):
        """deploy() never raises — errors surface in result.error."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        mock_resp = _mock_response({}, status_code=404)

        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=mock_resp,
        ):
            # Should not raise
            result = EnterpriseDeployer().deploy("not-found", target_dir=tmp_path)

        assert result.success is False

    def test_deployed_toml_not_written_on_failure(self, tmp_path: Path, monkeypatch):
        """No .skillmeat-deployed.toml is created when the API call fails."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        mock_resp = _mock_response({}, status_code=500)

        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=mock_resp,
        ):
            EnterpriseDeployer().deploy("broken", target_dir=tmp_path)

        assert not (tmp_path / ".skillmeat-deployed.toml").exists()


# ---------------------------------------------------------------------------
# Tests: atomic writes
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    """Files are written via temp file + rename (Path.replace), not directly."""

    def test_path_replace_called_for_each_file(self, tmp_path: Path, monkeypatch):
        """Path.replace is invoked for each file entry (atomic rename)."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "atm", "type": "skill", "version": "1.0"},
            "content_hash": "h",
            "files": [
                {"path": "a.md", "content": "aaa"},
                {"path": "b.md", "content": "bbb"},
            ],
        }

        replace_calls: list[Path] = []
        original_replace = Path.replace

        def tracking_replace(self_path, target):  # noqa: ANN001
            replace_calls.append(target)
            return original_replace(self_path, target)

        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ), patch.object(Path, "replace", tracking_replace):
            EnterpriseDeployer().deploy("atm", target_dir=tmp_path)

        # At least 2 replaces for the 2 content files (plus 1 for the TOML)
        assert len(replace_calls) >= 2

    def test_files_actually_written_with_correct_content(
        self, tmp_path: Path, monkeypatch
    ):
        """The final file content matches what the API returned."""
        monkeypatch.setenv("SKILLMEAT_EDITION", "enterprise")
        monkeypatch.setenv("SKILLMEAT_API_URL", "http://test")

        payload = {
            "metadata": {"name": "verify", "type": "skill", "version": "1.0"},
            "content_hash": "x",
            "files": [{"path": "hello.txt", "content": "hello world\n"}],
        }
        with patch(
            "skillmeat.core.enterprise_deploy.enterprise_request",
            return_value=_mock_response(payload),
        ):
            EnterpriseDeployer().deploy("verify", target_dir=tmp_path)

        dest = tmp_path / "skills" / "verify" / "hello.txt"
        assert dest.read_text() == "hello world\n"
