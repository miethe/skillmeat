"""Performance benchmarks for sync operations.

Tests sync manager performance with 500 artifact collections.
Target: <4 seconds for sync preview operations.
"""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import pytest
import tomli_w

from skillmeat.core.sync import SyncManager
from skillmeat.models import DeploymentMetadata, DeploymentRecord


class TestSyncPerformance:
    """Benchmark sync operations on large datasets."""

    def test_drift_detection_500_artifacts(
        self, benchmark, large_collection_500: Path, modified_collection_500: Path
    ):
        """Benchmark drift detection across 500 artifacts.

        Target: <4 seconds
        """
        sync_mgr = SyncManager()

        # Set up deployment metadata for the original collection
        deployment_file = large_collection_500 / ".skillmeat-deployed.toml"
        deployment_data = {
            "deployment": {
                "timestamp": datetime.now().isoformat(),
                "collection_path": str(large_collection_500),
                "artifacts": {},
            }
        }

        # Record all artifacts as deployed
        for artifact_type in ["skill", "command", "agent"]:
            type_dir = large_collection_500 / artifact_type
            if type_dir.exists():
                for artifact_dir in type_dir.iterdir():
                    if artifact_dir.is_dir():
                        # Compute hash
                        artifact_hash = hashlib.sha256(
                            str(artifact_dir).encode()
                        ).hexdigest()[:16]

                        deployment_data["deployment"]["artifacts"][artifact_dir.name] = {
                            "type": artifact_type,
                            "version": "1.0.0",
                            "deployed_hash": artifact_hash,
                        }

        deployment_file.write_bytes(tomli_w.dumps(deployment_data).encode())

        # Run benchmark
        result = benchmark(
            sync_mgr.check_drift,
            collection_path=large_collection_500,
            project_path=modified_collection_500,
        )

        # Verify results
        assert result is not None

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 4.0, f"Drift detection took {mean_time:.2f}s, expected <4s"

    def test_sync_preview_500_artifacts(
        self, benchmark, large_collection_500: Path, modified_collection_500: Path
    ):
        """Benchmark sync preview with 50 modified artifacts.

        Target: <4 seconds
        """
        sync_mgr = SyncManager()

        # Set up deployment metadata
        deployment_file = large_collection_500 / ".skillmeat-deployed.toml"
        deployment_data = {
            "deployment": {
                "timestamp": datetime.now().isoformat(),
                "collection_path": str(large_collection_500),
                "artifacts": {},
            }
        }
        deployment_file.write_bytes(tomli_w.dumps(deployment_data).encode())

        # Run benchmark
        result = benchmark(
            sync_mgr.sync_preview,
            collection_path=large_collection_500,
            project_path=modified_collection_500,
        )

        # Verify results
        assert result is not None

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 4.0, f"Sync preview took {mean_time:.2f}s, expected <4s"

    def test_deployment_metadata_read_500_artifacts(self, benchmark, tmp_path: Path):
        """Benchmark reading deployment metadata for 500 artifacts.

        Target: <500ms
        """
        # Create deployment metadata file
        deployment_file = tmp_path / ".skillmeat-deployed.toml"
        deployment_data = {
            "deployment": {
                "timestamp": datetime.now().isoformat(),
                "collection_path": str(tmp_path),
                "artifacts": {},
            }
        }

        # Add 500 artifact records
        for i in range(500):
            artifact_name = f"artifact-{i:04d}"
            deployment_data["deployment"]["artifacts"][artifact_name] = {
                "type": "skill",
                "version": "1.0.0",
                "deployed_hash": hashlib.sha256(artifact_name.encode()).hexdigest()[:16],
                "deployed_at": datetime.now().isoformat(),
            }

        deployment_file.write_bytes(tomli_w.dumps(deployment_data).encode())

        # Run benchmark
        import sys

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib

        def read_deployment_metadata():
            """Read and parse deployment metadata."""
            with deployment_file.open("rb") as f:
                data = tomllib.load(f)
            return data["deployment"]

        result = benchmark(read_deployment_metadata)

        # Verify results
        assert result is not None
        assert len(result["artifacts"]) == 500

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 0.5, f"Metadata read took {mean_time:.2f}s, expected <0.5s"

    def test_deployment_metadata_write_500_artifacts(self, benchmark, tmp_path: Path):
        """Benchmark writing deployment metadata for 500 artifacts.

        Target: <1 second
        """
        deployment_file = tmp_path / ".skillmeat-deployed.toml"

        # Prepare deployment data
        deployment_data = {
            "deployment": {
                "timestamp": datetime.now().isoformat(),
                "collection_path": str(tmp_path),
                "artifacts": {},
            }
        }

        for i in range(500):
            artifact_name = f"artifact-{i:04d}"
            deployment_data["deployment"]["artifacts"][artifact_name] = {
                "type": "skill",
                "version": "1.0.0",
                "deployed_hash": hashlib.sha256(artifact_name.encode()).hexdigest()[:16],
                "deployed_at": datetime.now().isoformat(),
            }

        # Run benchmark
        def write_deployment_metadata():
            """Write deployment metadata to file."""
            deployment_file.write_bytes(tomli_w.dumps(deployment_data).encode())

        benchmark(write_deployment_metadata)

        # Verify results
        assert deployment_file.exists()

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 1.0, f"Metadata write took {mean_time:.2f}s, expected <1s"

    def test_sync_pull_50_artifacts(
        self, benchmark, large_collection_500: Path, tmp_path: Path
    ):
        """Benchmark sync pull operation for 50 artifacts.

        Target: <3 seconds
        """
        sync_mgr = SyncManager()

        # Create target directory
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Select 50 artifacts to sync
        artifacts_to_sync = []
        for artifact_type in ["skill", "command", "agent"]:
            type_dir = large_collection_500 / artifact_type
            if type_dir.exists():
                for i, artifact_dir in enumerate(type_dir.iterdir()):
                    if i < 17 and artifact_dir.is_dir():  # ~50 total
                        artifacts_to_sync.append(artifact_dir)

        # Run benchmark
        def sync_pull():
            """Pull artifacts from collection to target."""
            for artifact_dir in artifacts_to_sync:
                target_artifact = target_dir / artifact_dir.parent.name / artifact_dir.name
                target_artifact.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(artifact_dir, target_artifact, dirs_exist_ok=True)

        benchmark(sync_pull)

        # Verify results
        synced_count = sum(
            1
            for artifact_type in ["skill", "command", "agent"]
            for _ in (target_dir / artifact_type).iterdir()
            if (target_dir / artifact_type).exists()
        )
        assert synced_count > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 3.0, f"Sync pull took {mean_time:.2f}s, expected <3s"

    def test_hash_computation_500_artifacts(self, benchmark, large_collection_500: Path):
        """Benchmark hash computation for drift detection.

        Target: <2 seconds
        """

        def compute_all_hashes():
            """Compute hashes for all artifacts."""
            hashes = {}
            for artifact_type in ["skill", "command", "agent"]:
                type_dir = large_collection_500 / artifact_type
                if type_dir.exists():
                    for artifact_dir in type_dir.iterdir():
                        if artifact_dir.is_dir():
                            # Simple hash based on directory contents
                            hasher = hashlib.sha256()

                            # Hash all files in artifact
                            for file in sorted(artifact_dir.rglob("*")):
                                if file.is_file():
                                    hasher.update(str(file.relative_to(artifact_dir)).encode())
                                    try:
                                        hasher.update(file.read_bytes())
                                    except Exception:
                                        pass  # Skip unreadable files

                            hashes[artifact_dir.name] = hasher.hexdigest()[:16]

            return hashes

        # Run benchmark
        result = benchmark(compute_all_hashes)

        # Verify results
        assert isinstance(result, dict)
        assert len(result) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Hash computation took {mean_time:.2f}s, expected <2s"

    def test_conflict_detection_50_artifacts(
        self, benchmark, large_collection_500: Path, modified_collection_500: Path, tmp_path: Path
    ):
        """Benchmark conflict detection for 50 modified artifacts.

        Target: <2 seconds
        """
        from skillmeat.core.diff_engine import DiffEngine

        diff_engine = DiffEngine()

        # Get 50 artifacts with potential conflicts
        artifacts = []
        for artifact_type in ["skill", "command", "agent"]:
            type_dir = large_collection_500 / artifact_type
            if type_dir.exists():
                for i, artifact_dir in enumerate(type_dir.iterdir()):
                    if i < 17 and artifact_dir.is_dir():  # ~50 total
                        artifacts.append((artifact_dir, modified_collection_500 / artifact_type / artifact_dir.name))

        # Run benchmark
        def detect_conflicts():
            """Detect conflicts between collection and modified versions."""
            conflicts = []
            for orig, modified in artifacts:
                if modified.exists():
                    diff = diff_engine.diff_directories(orig, modified)
                    if diff and diff.has_changes:
                        # Check if changes are conflicting
                        for file_diff in diff.file_diffs:
                            if file_diff.has_changes and file_diff.status == "modified":
                                conflicts.append((orig.name, file_diff.path))
            return conflicts

        result = benchmark(detect_conflicts)

        # Verify results
        assert isinstance(result, list)

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 2.0, f"Conflict detection took {mean_time:.2f}s, expected <2s"

    def test_deployment_record_creation(self, benchmark, large_collection_500: Path):
        """Benchmark deployment record creation for 500 artifacts.

        Target: <1 second
        """

        def create_deployment_records():
            """Create deployment records for all artifacts."""
            records = []
            for artifact_type in ["skill", "command", "agent"]:
                type_dir = large_collection_500 / artifact_type
                if type_dir.exists():
                    for artifact_dir in type_dir.iterdir():
                        if artifact_dir.is_dir():
                            record = DeploymentRecord(
                                artifact_name=artifact_dir.name,
                                artifact_type=artifact_type,
                                version="1.0.0",
                                deployed_at=datetime.now(),
                                deployed_hash=hashlib.sha256(
                                    artifact_dir.name.encode()
                                ).hexdigest()[:16],
                                source_collection=str(large_collection_500),
                            )
                            records.append(record)
            return records

        # Run benchmark
        result = benchmark(create_deployment_records)

        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0

        # Performance assertion
        stats = benchmark.stats
        mean_time = stats['mean']
        assert mean_time < 1.0, f"Record creation took {mean_time:.2f}s, expected <1s"
