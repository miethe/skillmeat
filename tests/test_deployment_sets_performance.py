"""Performance benchmark test for deployment set resolution (DS-T02).

Validates that resolving a deeply-nested deployment set (5 levels, ~100
artifact members) completes within the 500ms SLA.

Two complementary approaches are used:
1. In-memory DFS benchmark — exercises ``_resolve_dfs`` directly with
   pre-built member/group maps.  Hermetic, zero DB overhead.  Isolates the
   algorithm cost.
2. Full DB-backed benchmark — inserts real ``DeploymentSet`` and
   ``DeploymentSetMember`` rows into an isolated in-process SQLite database
   and calls ``DeploymentSetService.resolve()``.  Exercises the complete
   SQL query path that the production endpoint runs.

Hierarchy layout
----------------
Level 0: 1 root set
    └── 5 child sets  (Level 1)
         └── each child → 4 grandchild sets  (Level 2, 20 total)
              └── each grandchild → 1 artifact member (leaf) + nests into
                  Level 3 sets that themselves have artifact members (Levels 3-4).

Target unique artifact count: ≥ 100 across all levels.

Performance target: resolve() completes in < 500 ms.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, List

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Base, DeploymentSet, DeploymentSetMember
from skillmeat.core.deployment_sets import DeploymentSetService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SLA — whole resolution must finish within this budget (seconds)
_SLA_SECONDS: float = 0.500

# Structural parameters — keep in sync with module docstring
_NUM_L1_CHILDREN: int = 5   # children of root
_NUM_L2_PER_L1: int = 4     # sub-sets per L1 child
_NUM_L3_PER_L2: int = 3     # sub-sets per L2 node
_NUM_L4_PER_L3: int = 2     # leaf sets per L3 node (carry artifact members)
_ARTS_PER_LEAF: int = 2     # artifact members in each L4 leaf set
# Artifacts also attached at L2 and L3 to exceed the 100-member target.
_ARTS_PER_L2: int = 1
_ARTS_PER_L3: int = 1

# Total unique artifact UUIDs wired in by _build_member_map:
# L4 leaves: 5*4*3*2 = 120 leaves × 2 arts = 240
# L3 nodes:  5*4*3   = 60 × 1 art = 60
# L2 nodes:  5*4     = 20 × 1 art = 20
# Grand total: 320 unique UUIDs (well above 100)

_OWNER_ID: str = "perf-test-owner"


# ---------------------------------------------------------------------------
# Helpers — in-memory map builder
# ---------------------------------------------------------------------------


def _build_member_map() -> tuple[str, Dict[str, List[Dict]], Dict[str, List[str]]]:
    """Construct member_map and group_map for a 5-level hierarchy.

    Returns:
        (root_set_id, member_map, group_map) where:
        - root_set_id: ID string for the root deployment set.
        - member_map: {set_id -> [member_dict, ...]}  (artifact_uuid or member_set_id)
        - group_map: {} (no group members in this benchmark)
    """
    member_map: Dict[str, List[Dict]] = {}
    group_map: Dict[str, List[str]] = {}

    def new_id() -> str:
        return uuid.uuid4().hex

    def art_member(artifact_uuid: str) -> Dict:
        return {"artifact_uuid": artifact_uuid, "group_id": None, "member_set_id": None}

    def set_member(child_set_id: str) -> Dict:
        return {"artifact_uuid": None, "group_id": None, "member_set_id": child_set_id}

    root_id = new_id()
    member_map[root_id] = []

    for _ in range(_NUM_L1_CHILDREN):
        l1_id = new_id()
        member_map[root_id].append(set_member(l1_id))
        member_map[l1_id] = []

        for _ in range(_NUM_L2_PER_L1):
            l2_id = new_id()
            member_map[l1_id].append(set_member(l2_id))
            members_l2: List[Dict] = []
            # Attach unique artifact members at L2
            for _ in range(_ARTS_PER_L2):
                members_l2.append(art_member(new_id()))

            for _ in range(_NUM_L3_PER_L2):
                l3_id = new_id()
                members_l2.append(set_member(l3_id))
                members_l3: List[Dict] = []
                # Attach unique artifact members at L3
                for _ in range(_ARTS_PER_L3):
                    members_l3.append(art_member(new_id()))

                for _ in range(_NUM_L4_PER_L3):
                    l4_id = new_id()
                    members_l3.append(set_member(l4_id))
                    members_l4: List[Dict] = []
                    # Leaf artifacts
                    for _ in range(_ARTS_PER_LEAF):
                        members_l4.append(art_member(new_id()))
                    member_map[l4_id] = members_l4

                member_map[l3_id] = members_l3

            member_map[l2_id] = members_l2

    return root_id, member_map, group_map


# ---------------------------------------------------------------------------
# In-memory DFS benchmark (no DB)
# ---------------------------------------------------------------------------


class TestInMemoryResolutionPerformance:
    """Benchmark _resolve_dfs with pre-built in-memory maps.

    No SQLAlchemy session involved — purely measures algorithm cost.
    """

    def test_resolve_dfs_completes_within_sla(self) -> None:
        """DFS over 5-level, 100+ artifact hierarchy must complete in < 500ms."""
        root_id, member_map, group_map = _build_member_map()

        svc = DeploymentSetService(session=None)

        start = time.perf_counter()
        result = svc._resolve_dfs(
            root_set_id=root_id,
            member_map=member_map,
            group_map=group_map,
        )
        elapsed = time.perf_counter() - start

        print(
            f"\n[perf] in-memory _resolve_dfs: {elapsed * 1000:.2f}ms "
            f"({len(result)} unique artifacts)"
        )

        assert len(result) >= 100, (
            f"Expected at least 100 unique artifacts, got {len(result)}"
        )
        assert elapsed < _SLA_SECONDS, (
            f"_resolve_dfs exceeded {_SLA_SECONDS * 1000:.0f}ms SLA: "
            f"{elapsed * 1000:.2f}ms"
        )

    def test_resolve_dfs_deduplication(self) -> None:
        """Verify that duplicate artifact UUIDs appear only once in the result."""
        # Build a small map where a single artifact UUID is referenced twice
        shared_uuid = uuid.uuid4().hex
        set_a = uuid.uuid4().hex
        set_b = uuid.uuid4().hex
        root = uuid.uuid4().hex

        member_map: Dict[str, List[Dict]] = {
            root: [
                {"artifact_uuid": None, "group_id": None, "member_set_id": set_a},
                {"artifact_uuid": None, "group_id": None, "member_set_id": set_b},
            ],
            set_a: [
                {"artifact_uuid": shared_uuid, "group_id": None, "member_set_id": None}
            ],
            set_b: [
                {"artifact_uuid": shared_uuid, "group_id": None, "member_set_id": None}
            ],
        }

        svc = DeploymentSetService(session=None)
        result = svc._resolve_dfs(root_set_id=root, member_map=member_map, group_map={})

        assert result.count(shared_uuid) == 1, (
            f"Duplicate UUID should appear exactly once; result={result}"
        )


# ---------------------------------------------------------------------------
# DB-backed benchmark — exercises real SQL query path
# ---------------------------------------------------------------------------


@pytest.fixture()
def perf_db_session(tmp_path):
    """Isolated in-process SQLite session with deployment-set tables created."""
    db_file = tmp_path / "perf_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(conn, _):
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _insert_hierarchy(session) -> str:
    """Insert 5-level deployment set hierarchy into the DB session.

    Returns the root deployment set id.
    """

    def new_id() -> str:
        return uuid.uuid4().hex

    def make_set(name: str) -> str:
        sid = new_id()
        ds = DeploymentSet(id=sid, name=name, owner_id=_OWNER_ID)
        session.add(ds)
        return sid

    def add_artifact_member(set_id: str, pos: int) -> str:
        art_uuid = new_id()
        m = DeploymentSetMember(
            id=new_id(),
            set_id=set_id,
            artifact_uuid=art_uuid,
            position=pos,
        )
        session.add(m)
        return art_uuid

    def add_set_member(set_id: str, child_set_id: str, pos: int) -> None:
        m = DeploymentSetMember(
            id=new_id(),
            set_id=set_id,
            member_set_id=child_set_id,
            position=pos,
        )
        session.add(m)

    root_id = make_set("root-perf-set")

    l1_pos = 0
    for l1_idx in range(_NUM_L1_CHILDREN):
        l1_id = make_set(f"l1-{l1_idx}")
        add_set_member(root_id, l1_id, l1_pos)
        l1_pos += 1

        l2_pos = 0
        for l2_idx in range(_NUM_L2_PER_L1):
            l2_id = make_set(f"l2-{l1_idx}-{l2_idx}")
            add_set_member(l1_id, l2_id, l2_pos)
            l2_pos += 1

            # Artifact members at L2
            for art_i in range(_ARTS_PER_L2):
                add_artifact_member(l2_id, l2_pos + art_i)

            l3_pos = _ARTS_PER_L2
            for l3_idx in range(_NUM_L3_PER_L2):
                l3_id = make_set(f"l3-{l1_idx}-{l2_idx}-{l3_idx}")
                add_set_member(l2_id, l3_id, l3_pos)
                l3_pos += 1

                # Artifact members at L3
                for art_i in range(_ARTS_PER_L3):
                    add_artifact_member(l3_id, art_i)

                l4_pos = _ARTS_PER_L3
                for l4_idx in range(_NUM_L4_PER_L3):
                    l4_id = make_set(f"l4-{l1_idx}-{l2_idx}-{l3_idx}-{l4_idx}")
                    add_set_member(l3_id, l4_id, l4_pos)
                    l4_pos += 1

                    # Leaf artifact members at L4
                    for art_i in range(_ARTS_PER_LEAF):
                        add_artifact_member(l4_id, art_i)

    session.commit()
    return root_id


class TestDBBackedResolutionPerformance:
    """Benchmark DeploymentSetService.resolve() against a real SQLite DB.

    This exercises the full SQL query path (member_map and group_map built
    via actual queries) and validates the end-to-end 500ms SLA.
    """

    def test_resolve_db_backed_completes_within_sla(self, perf_db_session) -> None:
        """Full DB-backed resolve over 5-level hierarchy must complete in <500ms."""
        root_id = _insert_hierarchy(perf_db_session)

        svc = DeploymentSetService(session=perf_db_session)

        # Warm the session cache with one quick query before timing (avoids
        # counting SQLAlchemy connection overhead against the SLA)
        _ = perf_db_session.query(DeploymentSet).count()

        start = time.perf_counter()
        result = svc.resolve(root_id)
        elapsed = time.perf_counter() - start

        print(
            f"\n[perf] DB-backed resolve: {elapsed * 1000:.2f}ms "
            f"({len(result)} unique artifacts)"
        )

        assert len(result) >= 100, (
            f"Expected at least 100 unique artifacts from DB resolve, got {len(result)}"
        )
        assert elapsed < _SLA_SECONDS, (
            f"DB-backed resolve exceeded {_SLA_SECONDS * 1000:.0f}ms SLA: "
            f"{elapsed * 1000:.2f}ms"
        )

    def test_resolve_db_backed_result_is_deterministic(self, perf_db_session) -> None:
        """Repeated resolve() calls on the same DB must return identical results."""
        root_id = _insert_hierarchy(perf_db_session)
        svc = DeploymentSetService(session=perf_db_session)

        first = svc.resolve(root_id)
        second = svc.resolve(root_id)

        assert first == second, "resolve() must be deterministic across repeated calls"

    def test_resolve_empty_set_is_fast(self, perf_db_session) -> None:
        """An empty root set should resolve instantly and return an empty list."""
        root_id = uuid.uuid4().hex
        ds = DeploymentSet(id=root_id, name="empty-perf-set", owner_id=_OWNER_ID)
        perf_db_session.add(ds)
        perf_db_session.commit()

        svc = DeploymentSetService(session=perf_db_session)

        start = time.perf_counter()
        result = svc.resolve(root_id)
        elapsed = time.perf_counter() - start

        print(f"\n[perf] empty set resolve: {elapsed * 1000:.2f}ms")

        assert result == [], f"Expected empty list, got {result}"
        # Empty resolve should complete in well under 50ms
        assert elapsed < 0.050, (
            f"Empty set resolve took unexpectedly long: {elapsed * 1000:.2f}ms"
        )
