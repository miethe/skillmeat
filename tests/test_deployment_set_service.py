"""Unit tests for DeploymentSetService.resolve() / _resolve_dfs() / _check_cycle().

All resolve tests use the in-memory ``_resolve_dfs`` entry-point so no real DB
session is required.  The two arguments accepted by ``_resolve_dfs`` are:

* ``member_map``  — ``{set_id: [{"artifact_uuid": …}, {"group_id": …},
                               {"member_set_id": …}]}``
* ``group_map``   — ``{group_id: [uuid, …]}``

Each member dict must have exactly one non-None key (mirrors the DB CHECK
constraint).  The other two keys may be absent or set to ``None``.

Cycle-detection tests (``_check_cycle`` and ``add_member_with_cycle_check``)
use a lightweight SQLAlchemy in-memory SQLite database so that the DB queries
inside ``_check_cycle`` work without a real server.
"""

from typing import Dict, List
from unittest.mock import MagicMock, call, patch

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session

from skillmeat.core.deployment_sets import DeploymentSetService
from skillmeat.core.exceptions import (
    DeploymentSetCycleError,
    DeploymentSetResolutionError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _artifact(uuid: str) -> dict:
    return {"artifact_uuid": uuid, "group_id": None, "member_set_id": None}


def _group(group_id: str) -> dict:
    return {"artifact_uuid": None, "group_id": group_id, "member_set_id": None}


def _nested(set_id: str) -> dict:
    return {"artifact_uuid": None, "group_id": None, "member_set_id": set_id}


def make_svc(depth_limit: int = 20) -> DeploymentSetService:
    # session=None is OK for _resolve_dfs; only resolve() needs a real session.
    return DeploymentSetService(session=None, depth_limit=depth_limit)


# ---------------------------------------------------------------------------
# Basic cases
# ---------------------------------------------------------------------------


class TestEmptySet:
    def test_unknown_set_returns_empty(self):
        svc = make_svc()
        result = svc._resolve_dfs("nonexistent", member_map={}, group_map={})
        assert result == []

    def test_known_set_with_no_members_returns_empty(self):
        svc = make_svc()
        result = svc._resolve_dfs(
            "set-A",
            member_map={"set-A": []},
            group_map={},
        )
        assert result == []


# ---------------------------------------------------------------------------
# Artifact members
# ---------------------------------------------------------------------------


class TestArtifactMembers:
    def test_single_artifact_member(self):
        svc = make_svc()
        result = svc._resolve_dfs(
            "set-A",
            member_map={"set-A": [_artifact("uuid-1")]},
            group_map={},
        )
        assert result == ["uuid-1"]

    def test_multiple_artifact_members_preserves_order(self):
        svc = make_svc()
        result = svc._resolve_dfs(
            "set-A",
            member_map={
                "set-A": [_artifact("uuid-1"), _artifact("uuid-2"), _artifact("uuid-3")]
            },
            group_map={},
        )
        assert result == ["uuid-1", "uuid-2", "uuid-3"]


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_duplicate_artifacts_appear_once(self):
        svc = make_svc()
        result = svc._resolve_dfs(
            "set-A",
            member_map={
                "set-A": [
                    _artifact("uuid-1"),
                    _artifact("uuid-2"),
                    _artifact("uuid-1"),  # duplicate
                    _artifact("uuid-3"),
                    _artifact("uuid-2"),  # duplicate
                ]
            },
            group_map={},
        )
        assert result == ["uuid-1", "uuid-2", "uuid-3"]

    def test_first_seen_order_preserved_across_nested_sets(self):
        """uuid-2 appears in set-B before set-C re-references it — first-seen wins."""
        svc = make_svc()
        member_map = {
            "root": [_nested("set-B"), _nested("set-C")],
            "set-B": [_artifact("uuid-1"), _artifact("uuid-2")],
            "set-C": [_artifact("uuid-2"), _artifact("uuid-3")],  # uuid-2 is dup
        }
        result = svc._resolve_dfs("root", member_map=member_map, group_map={})
        assert result == ["uuid-1", "uuid-2", "uuid-3"]

    def test_artifact_via_direct_and_group_deduplicates(self):
        """Same UUID emitted directly and also via a group expansion."""
        svc = make_svc()
        member_map = {
            "set-A": [_artifact("uuid-1"), _group("grp-1")],
        }
        group_map = {"grp-1": ["uuid-1", "uuid-2"]}
        result = svc._resolve_dfs("set-A", member_map=member_map, group_map=group_map)
        assert result == ["uuid-1", "uuid-2"]


# ---------------------------------------------------------------------------
# Group member expansion
# ---------------------------------------------------------------------------


class TestGroupExpansion:
    def test_group_member_expands_to_artifact_uuids(self):
        svc = make_svc()
        member_map = {"set-A": [_group("grp-1")]}
        group_map = {"grp-1": ["uuid-1", "uuid-2", "uuid-3"]}
        result = svc._resolve_dfs("set-A", member_map=member_map, group_map=group_map)
        assert result == ["uuid-1", "uuid-2", "uuid-3"]

    def test_unknown_group_expands_to_empty(self):
        svc = make_svc()
        member_map = {"set-A": [_group("grp-missing")]}
        result = svc._resolve_dfs("set-A", member_map=member_map, group_map={})
        assert result == []

    def test_multiple_groups_concatenate_in_order(self):
        svc = make_svc()
        member_map = {"set-A": [_group("grp-1"), _group("grp-2")]}
        group_map = {
            "grp-1": ["uuid-1", "uuid-2"],
            "grp-2": ["uuid-3", "uuid-4"],
        }
        result = svc._resolve_dfs("set-A", member_map=member_map, group_map=group_map)
        assert result == ["uuid-1", "uuid-2", "uuid-3", "uuid-4"]

    def test_mixed_artifact_and_group(self):
        svc = make_svc()
        member_map = {
            "set-A": [_artifact("uuid-0"), _group("grp-1"), _artifact("uuid-9")]
        }
        group_map = {"grp-1": ["uuid-1", "uuid-2"]}
        result = svc._resolve_dfs("set-A", member_map=member_map, group_map=group_map)
        assert result == ["uuid-0", "uuid-1", "uuid-2", "uuid-9"]


# ---------------------------------------------------------------------------
# 3-level nesting
# ---------------------------------------------------------------------------


class TestThreeLevelNesting:
    def test_three_levels_resolves_all_unique_uuids(self):
        """Root → Level-1 → Level-2, each level adds unique UUIDs."""
        svc = make_svc()
        member_map = {
            "root": [_artifact("uuid-root"), _nested("level-1")],
            "level-1": [_artifact("uuid-l1"), _nested("level-2")],
            "level-2": [_artifact("uuid-l2-a"), _artifact("uuid-l2-b")],
        }
        result = svc._resolve_dfs("root", member_map=member_map, group_map={})
        assert result == ["uuid-root", "uuid-l1", "uuid-l2-a", "uuid-l2-b"]

    def test_three_levels_with_groups_at_each_level(self):
        svc = make_svc()
        member_map = {
            "root": [_group("grp-root"), _nested("level-1")],
            "level-1": [_group("grp-l1"), _nested("level-2")],
            "level-2": [_group("grp-l2")],
        }
        group_map = {
            "grp-root": ["uuid-1"],
            "grp-l1": ["uuid-2"],
            "grp-l2": ["uuid-3"],
        }
        result = svc._resolve_dfs("root", member_map=member_map, group_map=group_map)
        assert result == ["uuid-1", "uuid-2", "uuid-3"]

    def test_three_levels_deduplication_across_all_levels(self):
        """uuid-shared appears at root and deep level — only first-seen kept."""
        svc = make_svc()
        member_map = {
            "root": [_artifact("uuid-shared"), _nested("level-1")],
            "level-1": [_artifact("uuid-l1"), _nested("level-2")],
            "level-2": [_artifact("uuid-shared"), _artifact("uuid-l2")],
        }
        result = svc._resolve_dfs("root", member_map=member_map, group_map={})
        assert result == ["uuid-shared", "uuid-l1", "uuid-l2"]


# ---------------------------------------------------------------------------
# Depth limit guard
# ---------------------------------------------------------------------------


class TestDepthLimit:
    def _make_linear_chain(self, length: int) -> Dict:
        """Build a straight chain: root → set-1 → set-2 → … → set-(length-1)."""
        member_map = {}
        for i in range(length - 1):
            current = f"set-{i}" if i > 0 else "root"
            child = f"set-{i + 1}"
            member_map[current] = [_nested(child)]
        # Leaf has one artifact.
        leaf = f"set-{length - 1}"
        member_map[leaf] = [_artifact("leaf-uuid")]
        return member_map

    def test_chain_at_limit_succeeds(self):
        """A 20-hop chain at exactly the depth limit should not raise."""
        depth_limit = 20
        svc = make_svc(depth_limit=depth_limit)
        # Chain has depth_limit levels so deepest path length == depth_limit.
        member_map = self._make_linear_chain(depth_limit)
        result = svc._resolve_dfs("root", member_map=member_map, group_map={})
        assert "leaf-uuid" in result

    def test_chain_depth_21_raises(self):
        """A 21-hop chain should raise DeploymentSetResolutionError."""
        depth_limit = 20
        svc = make_svc(depth_limit=depth_limit)
        member_map = self._make_linear_chain(depth_limit + 1)
        with pytest.raises(DeploymentSetResolutionError) as exc_info:
            svc._resolve_dfs("root", member_map=member_map, group_map={})
        err = exc_info.value
        assert err.depth_limit == depth_limit
        # Path should be non-empty and contain the offending set.
        assert len(err.path) > 0
        assert "root" in err.path

    def test_error_message_contains_traversal_path(self):
        """The error message should mention the traversal path."""
        svc = make_svc(depth_limit=2)
        member_map = {
            "root": [_nested("set-1")],
            "set-1": [_nested("set-2")],
            "set-2": [_nested("set-3")],
            "set-3": [_artifact("uuid-deep")],
        }
        with pytest.raises(DeploymentSetResolutionError) as exc_info:
            svc._resolve_dfs("root", member_map=member_map, group_map={})
        msg = str(exc_info.value)
        assert "root" in msg
        assert "depth limit" in msg.lower() or "Traversal" in msg

    def test_error_carries_path_attribute(self):
        svc = make_svc(depth_limit=1)
        member_map = {
            "root": [_nested("child-set")],
            "child-set": [_nested("grandchild-set")],
            "grandchild-set": [_artifact("uuid-x")],
        }
        with pytest.raises(DeploymentSetResolutionError) as exc_info:
            svc._resolve_dfs("root", member_map=member_map, group_map={})
        assert isinstance(exc_info.value.path, list)
        assert len(exc_info.value.path) >= 1

    def test_custom_depth_limit_respected(self):
        """Service with depth_limit=5 should fire at depth 6."""
        svc = make_svc(depth_limit=5)
        member_map = self._make_linear_chain(6)
        # depth 5 → succeeds
        member_map_5 = self._make_linear_chain(5)
        result = svc._resolve_dfs("root", member_map=member_map_5, group_map={})
        assert "leaf-uuid" in result

        # depth 6 → raises
        with pytest.raises(DeploymentSetResolutionError):
            svc._resolve_dfs("root", member_map=member_map, group_map={})


# ---------------------------------------------------------------------------
# RuntimeError guard when session is None
# ---------------------------------------------------------------------------


class TestResolveSanityChecks:
    def test_resolve_without_session_raises_runtime_error(self):
        svc = DeploymentSetService(session=None)
        with pytest.raises(RuntimeError, match="requires a session"):
            svc.resolve("any-set-id")


# ---------------------------------------------------------------------------
# Cycle detection helpers
# ---------------------------------------------------------------------------


def _make_engine():
    """Create an in-memory SQLite engine with foreign-key enforcement."""
    engine = sa.create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _set_fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def _build_cycle_db(members: List[tuple]) -> Session:
    """Build a minimal in-memory DB with ``deployment_set_members`` rows.

    ``members`` is a list of ``(set_id, member_set_id)`` tuples representing
    the existing (already committed) set-type membership rows.

    Returns an open SQLAlchemy :class:`Session` backed by the in-memory DB.
    The caller is responsible for closing it.
    """
    engine = _make_engine()

    # Create a minimal table that mirrors the real DeploymentSetMember schema
    # for the columns ``_check_cycle`` actually queries.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE deployment_set_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    set_id TEXT NOT NULL,
                    member_set_id TEXT,
                    artifact_uuid TEXT,
                    group_id TEXT,
                    position INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        for sid, msid in members:
            conn.execute(
                sa.text(
                    "INSERT INTO deployment_set_members "
                    "(set_id, member_set_id) VALUES (:s, :m)"
                ),
                {"s": sid, "m": msid},
            )

    session = Session(bind=engine)
    return session


# ---------------------------------------------------------------------------
# _check_cycle — unit tests with in-memory DB
# ---------------------------------------------------------------------------


class TestCheckCycle:
    """Tests for DeploymentSetService._check_cycle()."""

    def test_self_reference_raises(self):
        """Adding a set as a member of itself must raise DeploymentSetCycleError."""
        session = _build_cycle_db([])
        svc = DeploymentSetService(session=session)
        with pytest.raises(DeploymentSetCycleError) as exc_info:
            svc._check_cycle("set-A", "set-A")
        err = exc_info.value
        assert err.set_id == "set-A"
        assert "set-A" in err.path
        session.close()

    def test_direct_cycle_a_to_b_then_b_to_a(self):
        """Existing edge B→A: adding A→B would create a 2-cycle."""
        # Existing: B already has A as a member (B→A)
        session = _build_cycle_db([("set-B", "set-A")])
        svc = DeploymentSetService(session=session)
        with pytest.raises(DeploymentSetCycleError) as exc_info:
            svc._check_cycle("set-A", "set-B")
        err = exc_info.value
        assert err.set_id == "set-A"
        # Path should contain both set-A and set-B
        assert "set-A" in err.path
        assert "set-B" in err.path
        session.close()

    def test_transitive_cycle_a_b_c_then_c_to_a(self):
        """Existing edges A→B, B→C: adding A as a member of C would create a 3-cycle.

        ``_check_cycle("set-C", "set-A")`` — we are about to make set-A a child
        of set-C.  Traversing descendants of set-A reveals set-B then set-C,
        which equals the container (set-C), so a cycle is detected.
        """
        session = _build_cycle_db([("set-A", "set-B"), ("set-B", "set-C")])
        svc = DeploymentSetService(session=session)
        with pytest.raises(DeploymentSetCycleError) as exc_info:
            svc._check_cycle("set-C", "set-A")
        err = exc_info.value
        assert err.set_id == "set-C"
        assert "set-C" in err.path
        assert "set-A" in err.path
        session.close()

    def test_valid_dag_accepted(self):
        """A→B, A→C, B→D, C→D is a valid DAG — no cycle when adding any safe edge."""
        # Existing: A→B, A→C, B→D, C→D (diamond DAG)
        members = [
            ("set-A", "set-B"),
            ("set-A", "set-C"),
            ("set-B", "set-D"),
            ("set-C", "set-D"),
        ]
        session = _build_cycle_db(members)
        svc = DeploymentSetService(session=session)
        # Adding D→E should be fine (E is a new leaf with no descendants).
        # _check_cycle should not raise.
        svc._check_cycle("set-D", "set-E")  # set-E has no members → no cycle
        session.close()

    def test_error_message_contains_path(self):
        """The error string must describe the cycle path clearly."""
        session = _build_cycle_db([("set-B", "set-A")])
        svc = DeploymentSetService(session=session)
        with pytest.raises(DeploymentSetCycleError) as exc_info:
            svc._check_cycle("set-A", "set-B")
        msg = str(exc_info.value)
        assert "set-A" in msg
        assert "set-B" in msg
        session.close()

    def test_path_attribute_is_list_of_strings(self):
        """DeploymentSetCycleError.path must be a non-empty list of strings."""
        session = _build_cycle_db([("set-B", "set-A")])
        svc = DeploymentSetService(session=session)
        with pytest.raises(DeploymentSetCycleError) as exc_info:
            svc._check_cycle("set-A", "set-B")
        assert isinstance(exc_info.value.path, list)
        assert len(exc_info.value.path) >= 2
        assert all(isinstance(s, str) for s in exc_info.value.path)
        session.close()

    def test_check_cycle_without_session_raises_runtime_error(self):
        svc = DeploymentSetService(session=None)
        with pytest.raises(RuntimeError, match="requires a session"):
            svc._check_cycle("set-A", "set-B")


# ---------------------------------------------------------------------------
# add_member_with_cycle_check — unit tests
# ---------------------------------------------------------------------------


class TestAddMemberWithCycleCheck:
    """Tests for DeploymentSetService.add_member_with_cycle_check()."""

    def test_set_member_triggers_cycle_check_and_raises(self):
        """When member_set_id causes a cycle, DeploymentSetCycleError propagates."""
        # Existing: set-B already contains set-A
        session = _build_cycle_db([("set-B", "set-A")])
        svc = DeploymentSetService(session=session)
        with pytest.raises(DeploymentSetCycleError):
            svc.add_member_with_cycle_check("set-A", "owner-1", member_set_id="set-B")
        session.close()

    def _make_svc_with_mock_repo(self, session, mock_member):
        """Return ``(svc, mock_add_member)`` with a fully mocked repo."""
        svc = DeploymentSetService(session=session)
        mock_repo = MagicMock()
        mock_repo.add_member.return_value = mock_member

        # Patch DeploymentSetRepository constructor so it returns mock_repo
        # instead of trying to open a real SQLite file.
        patcher = patch(
            "skillmeat.cache.repositories.DeploymentSetRepository",
            return_value=mock_repo,
        )
        return svc, mock_repo, patcher

    def test_artifact_member_does_not_trigger_cycle_check(self):
        """Artifact members bypass cycle detection and go straight to the repo."""
        session = _build_cycle_db([])
        mock_member = MagicMock()
        svc, mock_repo, patcher = self._make_svc_with_mock_repo(session, mock_member)

        with patcher:
            result = svc.add_member_with_cycle_check(
                "set-A", "owner-1", artifact_uuid="uuid-xyz"
            )

        mock_repo.add_member.assert_called_once_with(
            "set-A",
            "owner-1",
            artifact_uuid="uuid-xyz",
            group_id=None,
            member_set_id=None,
            position=None,
        )
        assert result is mock_member
        session.close()

    def test_group_member_does_not_trigger_cycle_check(self):
        """Group members bypass cycle detection and go straight to the repo."""
        session = _build_cycle_db([])
        mock_member = MagicMock()
        svc, mock_repo, patcher = self._make_svc_with_mock_repo(session, mock_member)

        with patcher:
            result = svc.add_member_with_cycle_check(
                "set-A", "owner-1", group_id="grp-1"
            )

        mock_repo.add_member.assert_called_once_with(
            "set-A",
            "owner-1",
            artifact_uuid=None,
            group_id="grp-1",
            member_set_id=None,
            position=None,
        )
        assert result is mock_member
        session.close()

    def test_valid_set_member_delegates_to_repo(self):
        """A safe set-member addition passes cycle check and calls repo.add_member."""
        # No existing members — no cycle possible.
        session = _build_cycle_db([])
        mock_member = MagicMock()
        svc, mock_repo, patcher = self._make_svc_with_mock_repo(session, mock_member)

        with patcher:
            result = svc.add_member_with_cycle_check(
                "set-A", "owner-1", member_set_id="set-B"
            )

        mock_repo.add_member.assert_called_once_with(
            "set-A",
            "owner-1",
            artifact_uuid=None,
            group_id=None,
            member_set_id="set-B",
            position=None,
        )
        assert result is mock_member
        session.close()

    def test_add_member_without_session_raises_runtime_error(self):
        svc = DeploymentSetService(session=None)
        with pytest.raises(RuntimeError, match="requires a session"):
            svc.add_member_with_cycle_check("set-A", "owner-1", member_set_id="set-B")


# ---------------------------------------------------------------------------
# batch_deploy — unit tests
# ---------------------------------------------------------------------------


def _make_project_mock(project_id: str = "proj-1", project_path: str = "/tmp/proj"):
    """Return a minimal mock Project row."""
    proj = MagicMock()
    proj.id = project_id
    proj.path = project_path
    return proj


def _make_artifact_row(uuid: str, name: str, artifact_type: str):
    """Return a minimal mock Artifact row with the three columns we access."""
    row = MagicMock()
    row.uuid = uuid
    row.name = name
    row.type = artifact_type
    return row


class TestBatchDeploy:
    """Tests for DeploymentSetService.batch_deploy()."""

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def test_no_session_raises_runtime_error(self):
        dm = MagicMock()
        svc = DeploymentSetService(session=None, deployment_manager=dm)
        with pytest.raises(RuntimeError, match="requires a session"):
            svc.batch_deploy("set-1", "proj-1")

    def test_no_deployment_manager_raises_value_error(self):
        session = MagicMock()
        svc = DeploymentSetService(session=session)
        with pytest.raises(ValueError, match="DeploymentManager"):
            svc.batch_deploy("set-1", "proj-1")

    def test_unknown_project_raises_lookup_error(self):
        """If project_id is not in the DB, raise LookupError before any deploy."""
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        dm = MagicMock()
        svc = DeploymentSetService(session=session, deployment_manager=dm)

        # Patch resolve() so we don't need a real DB for it.
        with patch.object(svc, "resolve", return_value=["uuid-a"]):
            with pytest.raises(LookupError, match="proj-missing"):
                svc.batch_deploy("set-1", "proj-missing")

        # deploy_artifacts must NOT have been called.
        dm.deploy_artifacts.assert_not_called()

    # ------------------------------------------------------------------
    # All-success case
    # ------------------------------------------------------------------

    def test_all_success(self):
        """All artifacts resolve and deploy without error → all results 'success'."""
        session = MagicMock()
        project = _make_project_mock("proj-1", "/projects/proj-1")
        art_a = _make_artifact_row("uuid-a", "canvas", "skill")
        art_b = _make_artifact_row("uuid-b", "review", "command")

        # Project query returns our project mock.
        session.query.return_value.filter.return_value.first.return_value = project

        # Artifact/CollectionArtifact join query returns two rows.
        session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            art_a,
            art_b,
        ]

        dm = MagicMock()
        dm.deploy_artifacts.return_value = [MagicMock()]

        svc = DeploymentSetService(session=session, deployment_manager=dm)

        with patch.object(svc, "resolve", return_value=["uuid-a", "uuid-b"]):
            results = svc.batch_deploy("set-1", "proj-1")

        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
        assert all(r["error"] is None for r in results)
        assert results[0]["artifact_uuid"] == "uuid-a"
        assert results[1]["artifact_uuid"] == "uuid-b"
        assert dm.deploy_artifacts.call_count == 2

    # ------------------------------------------------------------------
    # Mixed-result partial failure
    # ------------------------------------------------------------------

    def test_partial_failure_continues_loop(self):
        """One artifact raises → 'error' result; others still processed."""
        session = MagicMock()
        project = _make_project_mock()
        art_a = _make_artifact_row("uuid-a", "canvas", "skill")
        art_b = _make_artifact_row("uuid-b", "review", "command")
        art_c = _make_artifact_row("uuid-c", "docx", "skill")

        session.query.return_value.filter.return_value.first.return_value = project
        session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            art_a,
            art_b,
            art_c,
        ]

        dm = MagicMock()
        # Second call raises; first and third succeed.
        dm.deploy_artifacts.side_effect = [
            [MagicMock()],
            RuntimeError("deploy boom"),
            [MagicMock()],
        ]

        svc = DeploymentSetService(session=session, deployment_manager=dm)

        with patch.object(svc, "resolve", return_value=["uuid-a", "uuid-b", "uuid-c"]):
            results = svc.batch_deploy("set-1", "proj-1")

        assert len(results) == 3
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        assert "deploy boom" in results[1]["error"]
        assert results[2]["status"] == "success"
        assert dm.deploy_artifacts.call_count == 3

    # ------------------------------------------------------------------
    # Unknown UUID (CollectionArtifact mapping failure)
    # ------------------------------------------------------------------

    def test_unknown_uuid_produces_error_result(self):
        """A UUID not found in collection_artifacts → 'error' result, no exception."""
        session = MagicMock()
        project = _make_project_mock()
        art_a = _make_artifact_row("uuid-a", "canvas", "skill")

        session.query.return_value.filter.return_value.first.return_value = project
        # Only uuid-a is returned; uuid-missing is absent.
        session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            art_a,
        ]

        dm = MagicMock()
        dm.deploy_artifacts.return_value = [MagicMock()]

        svc = DeploymentSetService(session=session, deployment_manager=dm)

        with patch.object(svc, "resolve", return_value=["uuid-a", "uuid-missing"]):
            results = svc.batch_deploy("set-1", "proj-1")

        assert len(results) == 2
        assert results[0]["status"] == "success"
        assert results[1]["artifact_uuid"] == "uuid-missing"
        assert results[1]["status"] == "error"
        assert "uuid-missing" in results[1]["error"]

    # ------------------------------------------------------------------
    # Warning-level log for missing UUID
    # ------------------------------------------------------------------

    def test_missing_uuid_emits_warning_log(self, caplog):
        """A UUID not found in the cache should produce a warning-level log entry."""
        import logging

        session = MagicMock()
        project = _make_project_mock()

        session.query.return_value.filter.return_value.first.return_value = project
        # No artifact rows returned — uuid-x is unknown.
        session.query.return_value.join.return_value.filter.return_value.all.return_value = (
            []
        )

        dm = MagicMock()
        svc = DeploymentSetService(session=session, deployment_manager=dm)

        with caplog.at_level(logging.WARNING, logger="skillmeat.core.deployment_sets"):
            with patch.object(svc, "resolve", return_value=["uuid-x"]):
                results = svc.batch_deploy("set-warn", "proj-1")

        assert results[0]["status"] == "error"
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert any(
            "uuid-x" in msg for msg in warning_messages
        ), f"Expected warning mentioning 'uuid-x', got: {warning_messages}"

    # ------------------------------------------------------------------
    # profile_id is passed through to deploy_artifacts
    # ------------------------------------------------------------------

    def test_profile_id_passed_to_deploy_artifacts(self):
        """profile_id= is forwarded to DeploymentManager.deploy_artifacts."""
        session = MagicMock()
        project = _make_project_mock("proj-1", "/projects/proj-1")
        art_a = _make_artifact_row("uuid-a", "canvas", "skill")

        session.query.return_value.filter.return_value.first.return_value = project
        session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            art_a,
        ]

        dm = MagicMock()
        dm.deploy_artifacts.return_value = [MagicMock()]
        svc = DeploymentSetService(session=session, deployment_manager=dm)

        from pathlib import Path

        with patch.object(svc, "resolve", return_value=["uuid-a"]):
            svc.batch_deploy("set-1", "proj-1", profile_id="my-profile")

        dm.deploy_artifacts.assert_called_once_with(
            artifact_names=["canvas"],
            project_path=Path("/projects/proj-1"),
            profile_id="my-profile",
        )

    # ------------------------------------------------------------------
    # Empty set → empty results
    # ------------------------------------------------------------------

    def test_empty_resolved_set_returns_empty_list(self):
        """When resolve() returns [], batch_deploy returns [] without any DB query."""
        session = MagicMock()
        project = _make_project_mock()
        session.query.return_value.filter.return_value.first.return_value = project

        dm = MagicMock()
        svc = DeploymentSetService(session=session, deployment_manager=dm)

        with patch.object(svc, "resolve", return_value=[]):
            results = svc.batch_deploy("set-empty", "proj-1")

        assert results == []
        dm.deploy_artifacts.assert_not_called()
