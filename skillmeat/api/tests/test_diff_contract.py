"""Contract tests for artifact diff query flags.

Validates payload shape and backward compatibility for all three diff endpoints:
- GET /api/v1/artifacts/{artifact_id}/diff            (collection vs project)
- GET /api/v1/artifacts/{artifact_id}/upstream-diff   (collection vs upstream)
- GET /api/v1/artifacts/{artifact_id}/source-project-diff (source vs project)

Each endpoint supports three query flags:
  summary_only          (bool, default False)  — omit unified_diff from all files
  include_unified_diff  (bool, default True)   — alias / orthogonal to above
  file_paths            (str, csv)             — restrict diff content to named files

Tests are organised per-endpoint and cover:
  A. Legacy / default mode
  B. summary_only=true
  C. include_unified_diff=false
  D. file_paths filter (selective diff)
  E. Backward-compatibility contract (all FileDiff fields present, correct types)
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.api.utils.upstream_cache import UpstreamFetchCache
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType


# ---------------------------------------------------------------------------
# Shared constants used across all tests
# ---------------------------------------------------------------------------

ARTIFACT_ID = "skill:test-skill"
ARTIFACT_NAME = "test-skill"

# Two text files with different content so they produce a real diff
_COLLECTION_SKILL_MD = "# Test Skill\nversion: 1\n"
_PROJECT_SKILL_MD = "# Test Skill\nversion: 2\n"
_COLLECTION_README = "README from collection\n"
_PROJECT_README = "README from collection\n"  # identical → unchanged


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


_SKILL_MD_COLL_HASH = _sha256(_COLLECTION_SKILL_MD)
_SKILL_MD_PROJ_HASH = _sha256(_PROJECT_SKILL_MD)
_README_HASH = _sha256(_COLLECTION_README)


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_settings():
    """API settings with auth and rate limiting disabled."""
    return APISettings(
        env="testing",
        api_key_enabled=False,
        cors_enabled=True,
    )


@pytest.fixture
def client(api_settings):
    """TestClient with fully initialised app state."""
    from skillmeat.api.dependencies import app_state

    app = create_app(api_settings)
    app_state.initialize(api_settings)

    with TestClient(app) as c:
        yield c

    app_state.shutdown()


@pytest.fixture
def sample_artifact():
    """Minimal artifact for diff endpoint mocking."""
    metadata = ArtifactMetadata(
        title="Test Skill",
        description="Contract-test skill",
        author="tester",
        license="MIT",
        version="1.0.0",
        tags=[],
    )
    return Artifact(
        name=ARTIFACT_NAME,
        type=ArtifactType.SKILL,
        path=f"skills/{ARTIFACT_NAME}",
        origin="github",
        upstream="anthropics/skills/test-skill",
        version_spec="latest",
        resolved_sha="abc123",
        resolved_version="v1.0.0",
        added=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        metadata=metadata,
        tags=[],
    )


def _make_collection_manager(tmp_path: Path, artifact: Artifact):
    """Build a mock CollectionManager backed by real files in tmp_path."""
    coll_path = tmp_path / "collection"
    artifact_dir = coll_path / "skills" / ARTIFACT_NAME
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "SKILL.md").write_text(_COLLECTION_SKILL_MD)
    (artifact_dir / "README.md").write_text(_COLLECTION_README)

    mock_config = MagicMock()
    mock_config.get_collection_path.return_value = coll_path

    mock_coll_mgr = MagicMock()
    mock_coll_mgr.config = mock_config
    mock_coll_mgr.get_artifact.return_value = artifact
    mock_coll_mgr.list_collections.return_value = ["default"]
    return mock_coll_mgr


def _make_project(tmp_path: Path) -> Path:
    """Create a fake project directory with a deployed artifact."""
    proj_path = tmp_path / "project"
    artifact_dir = proj_path / ".claude" / "skills" / ARTIFACT_NAME
    artifact_dir.mkdir(parents=True)
    # SKILL.md is *modified* relative to collection; README is *unchanged*
    (artifact_dir / "SKILL.md").write_text(_PROJECT_SKILL_MD)
    (artifact_dir / "README.md").write_text(_PROJECT_README)
    return proj_path


# ---------------------------------------------------------------------------
# Helper: patch all boundary collaborators for /diff endpoint
# ---------------------------------------------------------------------------

def _patch_diff_boundaries(tmp_path: Path, sample_artifact: Artifact):
    """
    Return a context-manager stack that patches:
      - app_state.collection_manager
      - app_state.artifact_manager
      - DeploymentTracker.get_deployment  (returns a fake deployment record)
      - _find_artifact_in_collections     (returns the sample artifact + 'default')
    """
    coll_mgr = _make_collection_manager(tmp_path, sample_artifact)
    proj_path = _make_project(tmp_path)

    fake_deployment = MagicMock()
    fake_deployment.from_collection = "default"
    fake_deployment.artifact_path = f"skills/{ARTIFACT_NAME}"

    stack = [
        patch(
            "skillmeat.api.dependencies.app_state.collection_manager",
            coll_mgr,
        ),
        patch(
            "skillmeat.api.dependencies.app_state.artifact_manager",
        ),
        patch(
            "skillmeat.api.routers.artifacts.DeploymentTracker.get_deployment",
            return_value=fake_deployment,
        ),
        patch(
            "skillmeat.api.routers.artifacts._find_artifact_in_collections",
            return_value=(sample_artifact, "default"),
        ),
    ]
    return stack, proj_path


def _enter_stack(stack):
    entered = [ctx.__enter__() for ctx in stack]
    return entered


def _exit_stack(stack, exc=None):
    for ctx in reversed(stack):
        ctx.__exit__(exc, None, None)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/artifacts/{artifact_id}/diff
# ---------------------------------------------------------------------------


class TestCollectionVsProjectDiff:
    """Contract tests for the collection-vs-project diff endpoint."""

    ENDPOINT = f"/api/v1/artifacts/{ARTIFACT_ID}/diff"

    def _call(self, client, tmp_path, sample_artifact, **query_params):
        """Helpers: set up real files, patch boundaries, call endpoint."""
        stack, proj_path = _patch_diff_boundaries(tmp_path, sample_artifact)
        try:
            _enter_stack(stack)
            params = {"project_path": str(proj_path), **query_params}
            return client.get(self.ENDPOINT, params=params)
        finally:
            _exit_stack(stack)

    # ------------------------------------------------------------------
    # A. Legacy / default mode
    # ------------------------------------------------------------------

    def test_legacy_mode_returns_200(self, client, tmp_path, sample_artifact):
        """Default call (no special params) returns 200."""
        resp = self._call(client, tmp_path, sample_artifact)
        assert resp.status_code == 200

    def test_legacy_mode_has_changes(self, client, tmp_path, sample_artifact):
        """Modified files → has_changes is True."""
        data = self._call(client, tmp_path, sample_artifact).json()
        assert data["has_changes"] is True

    def test_legacy_mode_summary_counts(self, client, tmp_path, sample_artifact):
        """Summary reports 1 modified and 1 unchanged file."""
        summary = self._call(client, tmp_path, sample_artifact).json()["summary"]
        assert summary["modified"] == 1
        assert summary["unchanged"] == 1
        assert summary["added"] == 0
        assert summary["deleted"] == 0

    def test_legacy_mode_unified_diff_populated(self, client, tmp_path, sample_artifact):
        """Modified file has unified_diff populated in legacy mode."""
        files = self._call(client, tmp_path, sample_artifact).json()["files"]
        modified = [f for f in files if f["status"] == "modified"]
        assert len(modified) == 1
        assert modified[0]["unified_diff"] is not None
        assert "SKILL.md" in modified[0]["file_path"]

    def test_legacy_mode_unchanged_no_diff(self, client, tmp_path, sample_artifact):
        """Unchanged files never have unified_diff."""
        files = self._call(client, tmp_path, sample_artifact).json()["files"]
        unchanged = [f for f in files if f["status"] == "unchanged"]
        for f in unchanged:
            assert f["unified_diff"] is None

    # ------------------------------------------------------------------
    # B. summary_only=true
    # ------------------------------------------------------------------

    def test_summary_only_unified_diff_is_none(self, client, tmp_path, sample_artifact):
        """summary_only=true → unified_diff is None for all files."""
        files = self._call(
            client, tmp_path, sample_artifact, summary_only="true"
        ).json()["files"]
        for f in files:
            assert f["unified_diff"] is None, (
                f"Expected unified_diff=None for {f['file_path']} in summary_only mode"
            )

    def test_summary_only_summary_counts_match_legacy(
        self, client, tmp_path, sample_artifact
    ):
        """summary_only mode still returns correct counts."""
        data = self._call(
            client, tmp_path, sample_artifact, summary_only="true"
        ).json()
        assert data["summary"]["modified"] == 1
        assert data["summary"]["unchanged"] == 1
        assert data["has_changes"] is True

    def test_summary_only_files_have_status_and_hashes(
        self, client, tmp_path, sample_artifact
    ):
        """status and hash fields are still present in summary_only mode."""
        files = self._call(
            client, tmp_path, sample_artifact, summary_only="true"
        ).json()["files"]
        for f in files:
            assert "status" in f
            assert "file_path" in f
            # hash fields exist (may be None for added/deleted)
            assert "collection_hash" in f
            assert "project_hash" in f

    # ------------------------------------------------------------------
    # C. include_unified_diff=false
    # ------------------------------------------------------------------

    def test_include_unified_diff_false_omits_diff(
        self, client, tmp_path, sample_artifact
    ):
        """include_unified_diff=false → unified_diff is None for all files."""
        files = self._call(
            client, tmp_path, sample_artifact, include_unified_diff="false"
        ).json()["files"]
        for f in files:
            assert f["unified_diff"] is None

    def test_include_unified_diff_false_summary_correct(
        self, client, tmp_path, sample_artifact
    ):
        """Counts are still correct when unified diff is suppressed."""
        data = self._call(
            client, tmp_path, sample_artifact, include_unified_diff="false"
        ).json()
        assert data["summary"]["modified"] == 1
        assert data["summary"]["unchanged"] == 1

    # ------------------------------------------------------------------
    # D. file_paths filter
    # ------------------------------------------------------------------

    def test_file_paths_filter_targeted_file_gets_diff(
        self, client, tmp_path, sample_artifact
    ):
        """Filtered file (SKILL.md) receives unified_diff content."""
        files = self._call(
            client, tmp_path, sample_artifact, file_paths="SKILL.md"
        ).json()["files"]
        skill_files = [f for f in files if "SKILL.md" in f["file_path"]]
        assert len(skill_files) == 1
        assert skill_files[0]["unified_diff"] is not None

    def test_file_paths_filter_other_modified_files_no_diff(
        self, client, tmp_path, sample_artifact
    ):
        """Files NOT in file_paths filter have unified_diff=None even if modified."""
        # Add a second modified file to the fixture so we have one in and one out
        coll_mgr_mock = _make_collection_manager(tmp_path, sample_artifact)
        proj_path = _make_project(tmp_path)

        # Write an extra modified file: EXTRA.md
        coll_art = (
            coll_mgr_mock.config.get_collection_path("default")
            / "skills"
            / ARTIFACT_NAME
        )
        (coll_art / "EXTRA.md").write_text("extra-coll\n")
        proj_art = proj_path / ".claude" / "skills" / ARTIFACT_NAME
        (proj_art / "EXTRA.md").write_text("extra-proj-modified\n")

        fake_deployment = MagicMock()
        fake_deployment.from_collection = "default"
        fake_deployment.artifact_path = f"skills/{ARTIFACT_NAME}"

        with (
            patch(
                "skillmeat.api.dependencies.app_state.collection_manager",
                coll_mgr_mock,
            ),
            patch("skillmeat.api.dependencies.app_state.artifact_manager"),
            patch(
                "skillmeat.api.routers.artifacts.DeploymentTracker.get_deployment",
                return_value=fake_deployment,
            ),
            patch(
                "skillmeat.api.routers.artifacts._find_artifact_in_collections",
                return_value=(sample_artifact, "default"),
            ),
        ):
            resp = client.get(
                self.ENDPOINT,
                params={
                    "project_path": str(proj_path),
                    "file_paths": "SKILL.md",
                },
            )

        assert resp.status_code == 200
        files = resp.json()["files"]
        for f in files:
            if "SKILL.md" in f["file_path"]:
                assert f["unified_diff"] is not None
            else:
                # EXTRA.md and README.md should not have diff content
                if f["status"] == "modified":
                    assert f["unified_diff"] is None

    def test_file_paths_filter_summary_counts_all_files(
        self, client, tmp_path, sample_artifact
    ):
        """Summary counts include ALL files, not just the filtered ones."""
        data = self._call(
            client, tmp_path, sample_artifact, file_paths="SKILL.md"
        ).json()
        # Both SKILL.md (modified) and README.md (unchanged) must appear in counts
        total = sum(data["summary"].values())
        assert total == 2

    # ------------------------------------------------------------------
    # E. Backward compatibility — contract shape
    # ------------------------------------------------------------------

    def test_backward_compat_top_level_fields(self, client, tmp_path, sample_artifact):
        """Response includes all top-level fields from original contract."""
        data = self._call(client, tmp_path, sample_artifact).json()
        required_keys = {
            "artifact_id",
            "artifact_name",
            "artifact_type",
            "collection_name",
            "project_path",
            "has_changes",
            "files",
            "summary",
        }
        assert required_keys <= set(data.keys())

    def test_backward_compat_file_diff_shape(self, client, tmp_path, sample_artifact):
        """Every FileDiff entry has all required fields."""
        files = self._call(client, tmp_path, sample_artifact).json()["files"]
        assert files  # non-empty
        for f in files:
            assert "file_path" in f
            assert "status" in f
            assert "collection_hash" in f
            assert "project_hash" in f
            assert "unified_diff" in f

    def test_backward_compat_artifact_id_passthrough(
        self, client, tmp_path, sample_artifact
    ):
        """artifact_id in response matches the request path segment."""
        data = self._call(client, tmp_path, sample_artifact).json()
        assert data["artifact_id"] == ARTIFACT_ID

    def test_backward_compat_summary_has_four_keys(
        self, client, tmp_path, sample_artifact
    ):
        """Summary dict has exactly: added, modified, deleted, unchanged."""
        summary = self._call(client, tmp_path, sample_artifact).json()["summary"]
        assert set(summary.keys()) == {"added", "modified", "deleted", "unchanged"}

    def test_backward_compat_has_changes_type(self, client, tmp_path, sample_artifact):
        """has_changes is a boolean."""
        data = self._call(client, tmp_path, sample_artifact).json()
        assert isinstance(data["has_changes"], bool)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/artifacts/{artifact_id}/upstream-diff
# ---------------------------------------------------------------------------


class TestUpstreamDiff:
    """Contract tests for the collection-vs-upstream diff endpoint."""

    ENDPOINT = f"/api/v1/artifacts/{ARTIFACT_ID}/upstream-diff"

    def _make_upstream_dir(self, tmp_path: Path):
        """Write 'upstream' files to a temp dir and return the path."""
        upstream_dir = tmp_path / "upstream_tmp"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Test Skill\nversion: upstream\n")
        (upstream_dir / "README.md").write_text(_COLLECTION_README)
        return upstream_dir

    def _patch_upstream(self, tmp_path: Path, sample_artifact: Artifact):
        """Patch all collaborators for the upstream-diff endpoint."""
        coll_mgr = _make_collection_manager(tmp_path, sample_artifact)
        upstream_dir = self._make_upstream_dir(tmp_path)

        # Build a fetch_result that mimics the real FetchUpdateResult structure:
        #   fetch_result.error           → None (no error)
        #   fetch_result.has_update      → True (upstream differs)
        #   fetch_result.temp_workspace  → truthy sentinel
        #   fetch_result.fetch_result.artifact_path → Path to upstream files
        inner_fetch = MagicMock()
        inner_fetch.artifact_path = upstream_dir

        mock_fetch_result = MagicMock()
        mock_fetch_result.error = None
        mock_fetch_result.has_update = True
        mock_fetch_result.temp_workspace = upstream_dir  # truthy Path
        mock_fetch_result.fetch_result = inner_fetch
        # update_info must be falsy so the router takes the "unknown" branch
        # rather than trying to access update_info.latest_sha (a MagicMock).
        mock_fetch_result.update_info = None

        mock_art_mgr = MagicMock()
        mock_art_mgr.fetch_update.return_value = mock_fetch_result

        return coll_mgr, mock_art_mgr, upstream_dir

    def _call(self, client, tmp_path, sample_artifact, **query_params):
        coll_mgr, mock_art_mgr, _ = self._patch_upstream(tmp_path, sample_artifact)
        with (
            patch(
                "skillmeat.api.dependencies.app_state.collection_manager",
                coll_mgr,
            ),
            patch(
                "skillmeat.api.dependencies.app_state.artifact_manager",
                mock_art_mgr,
            ),
            patch(
                "skillmeat.api.routers.artifacts._find_artifact_in_collections",
                return_value=(sample_artifact, "default"),
            ),
            patch(
                "skillmeat.api.routers.artifacts.get_upstream_cache",
                return_value=UpstreamFetchCache(),
            ),
        ):
            return client.get(self.ENDPOINT, params=query_params)

    # ------------------------------------------------------------------
    # A. Legacy / default mode
    # ------------------------------------------------------------------

    def test_legacy_mode_returns_200(self, client, tmp_path, sample_artifact):
        resp = self._call(client, tmp_path, sample_artifact)
        assert resp.status_code == 200

    def test_legacy_mode_unified_diff_populated_for_modified(
        self, client, tmp_path, sample_artifact
    ):
        """Modified file gets unified_diff in default mode."""
        files = self._call(client, tmp_path, sample_artifact).json()["files"]
        modified = [f for f in files if f["status"] == "modified"]
        assert modified
        assert all(f["unified_diff"] is not None for f in modified)

    def test_legacy_mode_summary_counts(self, client, tmp_path, sample_artifact):
        data = self._call(client, tmp_path, sample_artifact).json()
        # SKILL.md is modified; README.md is identical → unchanged
        assert data["summary"]["modified"] == 1
        assert data["summary"]["unchanged"] == 1

    # ------------------------------------------------------------------
    # B. summary_only=true
    # ------------------------------------------------------------------

    def test_summary_only_no_unified_diff(self, client, tmp_path, sample_artifact):
        files = self._call(
            client, tmp_path, sample_artifact, summary_only="true"
        ).json()["files"]
        for f in files:
            assert f["unified_diff"] is None

    def test_summary_only_counts_match_legacy(self, client, tmp_path, sample_artifact):
        data = self._call(
            client, tmp_path, sample_artifact, summary_only="true"
        ).json()
        assert data["summary"]["modified"] == 1
        assert data["summary"]["unchanged"] == 1
        assert data["has_changes"] is True

    # ------------------------------------------------------------------
    # C. include_unified_diff=false
    # ------------------------------------------------------------------

    def test_include_unified_diff_false(self, client, tmp_path, sample_artifact):
        files = self._call(
            client, tmp_path, sample_artifact, include_unified_diff="false"
        ).json()["files"]
        for f in files:
            assert f["unified_diff"] is None

    # ------------------------------------------------------------------
    # D. file_paths filter
    # ------------------------------------------------------------------

    def test_file_paths_targeted_file_has_diff(self, client, tmp_path, sample_artifact):
        files = self._call(
            client, tmp_path, sample_artifact, file_paths="SKILL.md"
        ).json()["files"]
        skill = [f for f in files if "SKILL.md" in f["file_path"]]
        assert skill
        assert skill[0]["unified_diff"] is not None

    def test_file_paths_summary_includes_all(self, client, tmp_path, sample_artifact):
        data = self._call(
            client, tmp_path, sample_artifact, file_paths="SKILL.md"
        ).json()
        assert sum(data["summary"].values()) == 2

    # ------------------------------------------------------------------
    # E. Backward compatibility
    # ------------------------------------------------------------------

    def test_backward_compat_top_level_fields(self, client, tmp_path, sample_artifact):
        data = self._call(client, tmp_path, sample_artifact).json()
        required_keys = {
            "artifact_id",
            "artifact_name",
            "artifact_type",
            "collection_name",
            "upstream_source",
            "upstream_version",
            "has_changes",
            "files",
            "summary",
        }
        assert required_keys <= set(data.keys())

    def test_backward_compat_file_diff_shape(self, client, tmp_path, sample_artifact):
        files = self._call(client, tmp_path, sample_artifact).json()["files"]
        assert files
        for f in files:
            assert "file_path" in f
            assert "status" in f
            assert "collection_hash" in f
            assert "project_hash" in f
            assert "unified_diff" in f

    def test_backward_compat_no_extra_params_response_stable(
        self, client, tmp_path, sample_artifact
    ):
        """Calling with no new query params at all produces the same result as legacy."""
        # Use separate subdirs so two calls don't collide on the same mkdir paths.
        data_no_params = self._call(
            client, tmp_path / "a", sample_artifact
        ).json()
        data_explicit = self._call(
            client,
            tmp_path / "b",
            sample_artifact,
            summary_only="false",
            include_unified_diff="true",
        ).json()
        # Files length must be the same
        assert len(data_no_params["files"]) == len(data_explicit["files"])
        # has_changes must be the same
        assert data_no_params["has_changes"] == data_explicit["has_changes"]
        # summary counts must match
        assert data_no_params["summary"] == data_explicit["summary"]


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/artifacts/{artifact_id}/source-project-diff
# ---------------------------------------------------------------------------


class TestSourceProjectDiff:
    """Contract tests for the source-to-project diff endpoint."""

    ENDPOINT = f"/api/v1/artifacts/{ARTIFACT_ID}/source-project-diff"

    def _make_upstream_dir(self, tmp_path: Path) -> Path:
        upstream_dir = tmp_path / "source_upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Test Skill\nversion: upstream\n")
        (upstream_dir / "README.md").write_text(_COLLECTION_README)
        return upstream_dir

    def _make_fetch_result(self, upstream_dir: Path) -> MagicMock:
        """Build a mock FetchUpdateResult pointing at upstream_dir."""
        inner_fetch = MagicMock()
        inner_fetch.artifact_path = upstream_dir

        mock_fetch_result = MagicMock()
        mock_fetch_result.error = None
        mock_fetch_result.has_update = True
        mock_fetch_result.temp_workspace = upstream_dir  # truthy Path
        mock_fetch_result.fetch_result = inner_fetch
        # update_info must be falsy to avoid accessing MagicMock attributes
        # that would fail Pydantic string validation.
        mock_fetch_result.update_info = None
        return mock_fetch_result

    def _call(self, client, tmp_path, sample_artifact, **query_params):
        coll_mgr = _make_collection_manager(tmp_path, sample_artifact)
        proj_path = _make_project(tmp_path)
        upstream_dir = self._make_upstream_dir(tmp_path)

        mock_art_mgr = MagicMock()
        mock_art_mgr.fetch_update.return_value = self._make_fetch_result(upstream_dir)

        with (
            patch(
                "skillmeat.api.dependencies.app_state.collection_manager",
                coll_mgr,
            ),
            patch(
                "skillmeat.api.dependencies.app_state.artifact_manager",
                mock_art_mgr,
            ),
            patch(
                "skillmeat.api.routers.artifacts._find_artifact_in_collections",
                return_value=(sample_artifact, "default"),
            ),
            patch(
                "skillmeat.api.routers.artifacts.DeploymentTracker.get_deployment",
                return_value=MagicMock(
                    from_collection="default",
                    artifact_path=f"skills/{ARTIFACT_NAME}",
                ),
            ),
            patch(
                "skillmeat.api.routers.artifacts.get_upstream_cache",
                return_value=UpstreamFetchCache(),
            ),
        ):
            params = {"project_path": str(proj_path), **query_params}
            return client.get(self.ENDPOINT, params=params)

    # ------------------------------------------------------------------
    # A. Legacy / default mode
    # ------------------------------------------------------------------

    def test_legacy_mode_returns_200(self, client, tmp_path, sample_artifact):
        resp = self._call(client, tmp_path, sample_artifact)
        assert resp.status_code == 200

    def test_legacy_mode_has_changes(self, client, tmp_path, sample_artifact):
        data = self._call(client, tmp_path, sample_artifact).json()
        assert data["has_changes"] is True

    def test_legacy_mode_unified_diff_for_modified(
        self, client, tmp_path, sample_artifact
    ):
        files = self._call(client, tmp_path, sample_artifact).json()["files"]
        modified = [f for f in files if f["status"] == "modified"]
        assert modified
        assert all(f["unified_diff"] is not None for f in modified)

    def test_legacy_mode_summary_counts(self, client, tmp_path, sample_artifact):
        data = self._call(client, tmp_path, sample_artifact).json()
        # Upstream SKILL.md differs from project SKILL.md → modified
        # README.md is the same in both → unchanged
        assert data["summary"]["modified"] == 1
        assert data["summary"]["unchanged"] == 1

    # ------------------------------------------------------------------
    # B. summary_only=true
    # ------------------------------------------------------------------

    def test_summary_only_no_unified_diff(self, client, tmp_path, sample_artifact):
        files = self._call(
            client, tmp_path, sample_artifact, summary_only="true"
        ).json()["files"]
        for f in files:
            assert f["unified_diff"] is None

    def test_summary_only_counts_correct(self, client, tmp_path, sample_artifact):
        data = self._call(
            client, tmp_path, sample_artifact, summary_only="true"
        ).json()
        assert data["summary"]["modified"] == 1
        assert data["has_changes"] is True

    # ------------------------------------------------------------------
    # C. include_unified_diff=false
    # ------------------------------------------------------------------

    def test_include_unified_diff_false_no_diff(
        self, client, tmp_path, sample_artifact
    ):
        files = self._call(
            client, tmp_path, sample_artifact, include_unified_diff="false"
        ).json()["files"]
        for f in files:
            assert f["unified_diff"] is None

    def test_include_unified_diff_false_counts_correct(
        self, client, tmp_path, sample_artifact
    ):
        data = self._call(
            client, tmp_path, sample_artifact, include_unified_diff="false"
        ).json()
        assert data["summary"]["modified"] == 1

    # ------------------------------------------------------------------
    # D. file_paths filter
    # ------------------------------------------------------------------

    def test_file_paths_targeted_file_has_diff(self, client, tmp_path, sample_artifact):
        files = self._call(
            client, tmp_path, sample_artifact, file_paths="SKILL.md"
        ).json()["files"]
        skill = [f for f in files if "SKILL.md" in f["file_path"]]
        assert skill
        assert skill[0]["unified_diff"] is not None

    def test_file_paths_non_targeted_modified_has_no_diff(
        self, client, tmp_path, sample_artifact
    ):
        """Files outside file_paths get no unified_diff."""
        # README is unchanged so its unified_diff would be None regardless.
        # Add a second modified file to verify filtering.
        coll_mgr = _make_collection_manager(tmp_path, sample_artifact)
        proj_path = _make_project(tmp_path)
        upstream_dir = self._make_upstream_dir(tmp_path)

        # extra file: modified in source vs project
        (upstream_dir / "EXTRA.md").write_text("upstream extra\n")
        (proj_path / ".claude" / "skills" / ARTIFACT_NAME / "EXTRA.md").write_text(
            "project extra different\n"
        )

        mock_art_mgr = MagicMock()
        mock_art_mgr.fetch_update.return_value = self._make_fetch_result(upstream_dir)

        with (
            patch(
                "skillmeat.api.dependencies.app_state.collection_manager",
                coll_mgr,
            ),
            patch(
                "skillmeat.api.dependencies.app_state.artifact_manager",
                mock_art_mgr,
            ),
            patch(
                "skillmeat.api.routers.artifacts._find_artifact_in_collections",
                return_value=(sample_artifact, "default"),
            ),
            patch(
                "skillmeat.api.routers.artifacts.DeploymentTracker.get_deployment",
                return_value=MagicMock(
                    from_collection="default",
                    artifact_path=f"skills/{ARTIFACT_NAME}",
                ),
            ),
            patch(
                "skillmeat.api.routers.artifacts.get_upstream_cache",
                return_value=UpstreamFetchCache(),
            ),
        ):
            resp = client.get(
                self.ENDPOINT,
                params={
                    "project_path": str(proj_path),
                    "file_paths": "SKILL.md",
                },
            )

        assert resp.status_code == 200
        files = resp.json()["files"]
        for f in files:
            if "SKILL.md" in f["file_path"]:
                assert f["unified_diff"] is not None
            elif f["status"] == "modified":
                assert f["unified_diff"] is None

    def test_file_paths_summary_counts_all(self, client, tmp_path, sample_artifact):
        data = self._call(
            client, tmp_path, sample_artifact, file_paths="SKILL.md"
        ).json()
        assert sum(data["summary"].values()) == 2

    # ------------------------------------------------------------------
    # E. Backward compatibility
    # ------------------------------------------------------------------

    def test_backward_compat_response_shape(self, client, tmp_path, sample_artifact):
        """Response uses ArtifactDiffResponse (same as /diff endpoint)."""
        data = self._call(client, tmp_path, sample_artifact).json()
        required_keys = {
            "artifact_id",
            "artifact_name",
            "artifact_type",
            "collection_name",
            "project_path",
            "has_changes",
            "files",
            "summary",
        }
        assert required_keys <= set(data.keys())
        # source-project-diff should NOT return upstream_source / upstream_version
        assert "upstream_source" not in data
        assert "upstream_version" not in data

    def test_backward_compat_file_diff_shape(self, client, tmp_path, sample_artifact):
        files = self._call(client, tmp_path, sample_artifact).json()["files"]
        assert files
        for f in files:
            for key in ("file_path", "status", "collection_hash", "project_hash", "unified_diff"):
                assert key in f, f"Missing field '{key}' in FileDiff for {f.get('file_path')}"

    def test_backward_compat_no_new_params_matches_explicit_defaults(
        self, client, tmp_path, sample_artifact
    ):
        """Calling with no new params is identical to explicit defaults."""
        # Use separate subdirs so two calls don't collide on the same mkdir paths.
        data_bare = self._call(client, tmp_path / "a", sample_artifact).json()
        data_explicit = self._call(
            client,
            tmp_path / "b",
            sample_artifact,
            summary_only="false",
            include_unified_diff="true",
        ).json()
        assert data_bare["has_changes"] == data_explicit["has_changes"]
        assert data_bare["summary"] == data_explicit["summary"]
        assert len(data_bare["files"]) == len(data_explicit["files"])
