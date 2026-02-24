"""Unit tests for DeploymentSetService.resolve() / _resolve_dfs().

All tests use the in-memory ``_resolve_dfs`` entry-point so no real DB
session is required.  The two arguments accepted by ``_resolve_dfs`` are:

* ``member_map``  — ``{set_id: [{"artifact_uuid": …}, {"group_id": …},
                               {"member_set_id": …}]}``
* ``group_map``   — ``{group_id: [uuid, …]}``

Each member dict must have exactly one non-None key (mirrors the DB CHECK
constraint).  The other two keys may be absent or set to ``None``.
"""

from typing import Dict

import pytest

from skillmeat.core.deployment_sets import DeploymentSetService
from skillmeat.core.exceptions import DeploymentSetResolutionError


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
