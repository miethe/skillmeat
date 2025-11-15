#!/usr/bin/env python3
"""Demo script for three-way diff functionality.

This script demonstrates the three-way diff capabilities with concrete examples.
"""

from pathlib import Path
import tempfile
import shutil

from skillmeat.core.diff_engine import DiffEngine


def demo_basic_scenarios():
    """Demonstrate basic three-way diff scenarios."""
    print("=" * 70)
    print("THREE-WAY DIFF DEMONSTRATION")
    print("=" * 70)

    engine = DiffEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Scenario 1: Auto-merge - only remote changed
        print("\n[Scenario 1] Auto-merge: Only remote changed")
        print("-" * 70)

        base = tmppath / "scenario1_base"
        local = tmppath / "scenario1_local"
        remote = tmppath / "scenario1_remote"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "config.txt").write_text("version=1.0\nfeature=disabled\n")
        (local / "config.txt").write_text("version=1.0\nfeature=disabled\n")
        (remote / "config.txt").write_text("version=1.0\nfeature=enabled\n")

        result = engine.three_way_diff(base, local, remote)

        print(f"Auto-mergeable files: {len(result.auto_mergeable)}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Summary: {result.summary()}")
        print(f"Can auto-merge: {result.can_auto_merge}")
        print("\nResult: Remote changes can be automatically merged")

        # Scenario 2: Auto-merge - only local changed
        print("\n[Scenario 2] Auto-merge: Only local changed")
        print("-" * 70)

        base = tmppath / "scenario2_base"
        local = tmppath / "scenario2_local"
        remote = tmppath / "scenario2_remote"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "settings.txt").write_text("debug=false\n")
        (local / "settings.txt").write_text("debug=true\n")
        (remote / "settings.txt").write_text("debug=false\n")

        result = engine.three_way_diff(base, local, remote)

        print(f"Auto-mergeable files: {len(result.auto_mergeable)}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Summary: {result.summary()}")
        print("\nResult: Local changes preserved (remote unchanged)")

        # Scenario 3: Conflict - both changed differently
        print("\n[Scenario 3] Conflict: Both changed differently")
        print("-" * 70)

        base = tmppath / "scenario3_base"
        local = tmppath / "scenario3_local"
        remote = tmppath / "scenario3_remote"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "readme.txt").write_text("# Original Project\n\nDescription here.\n")
        (local / "readme.txt").write_text(
            "# My Fork\n\nLocal modifications.\n"
        )
        (remote / "readme.txt").write_text(
            "# Original Project v2\n\nUpdated description.\n"
        )

        result = engine.three_way_diff(base, local, remote)

        print(f"Auto-mergeable files: {len(result.auto_mergeable)}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Summary: {result.summary()}")
        print(f"Can auto-merge: {result.can_auto_merge}")

        if result.conflicts:
            conflict = result.conflicts[0]
            print(f"\nConflict details:")
            print(f"  File: {conflict.file_path}")
            print(f"  Type: {conflict.conflict_type}")
            print(f"  Strategy: {conflict.merge_strategy}")
            print("\nResult: Manual resolution required")

        # Scenario 4: Both changed identically (auto-merge)
        print("\n[Scenario 4] Auto-merge: Both changed to same content")
        print("-" * 70)

        base = tmppath / "scenario4_base"
        local = tmppath / "scenario4_local"
        remote = tmppath / "scenario4_remote"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "version.txt").write_text("1.0.0\n")
        (local / "version.txt").write_text("1.1.0\n")
        (remote / "version.txt").write_text("1.1.0\n")

        result = engine.three_way_diff(base, local, remote)

        print(f"Auto-mergeable files: {len(result.auto_mergeable)}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Summary: {result.summary()}")
        print("\nResult: Both changed identically - safe to merge")

        # Scenario 5: Deletion conflict
        print("\n[Scenario 5] Conflict: File deleted locally, modified remotely")
        print("-" * 70)

        base = tmppath / "scenario5_base"
        local = tmppath / "scenario5_local"
        remote = tmppath / "scenario5_remote"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "deprecated.txt").write_text("Old feature\n")
        # Local deleted (file doesn't exist)
        (remote / "deprecated.txt").write_text("Updated old feature\n")

        result = engine.three_way_diff(base, local, remote)

        print(f"Auto-mergeable files: {len(result.auto_mergeable)}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Summary: {result.summary()}")

        if result.conflicts:
            conflict = result.conflicts[0]
            print(f"\nConflict details:")
            print(f"  Type: {conflict.conflict_type}")
            print(f"  Local deleted: {conflict.local_content is None}")
            print(f"  Remote modified: {conflict.remote_content is not None}")
            print("\nResult: User must decide whether to keep remote changes or deletion")

        # Scenario 6: Multiple files - mixed outcomes
        print("\n[Scenario 6] Complex: Multiple files with various changes")
        print("-" * 70)

        base = tmppath / "scenario6_base"
        local = tmppath / "scenario6_local"
        remote = tmppath / "scenario6_remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Unchanged file
        for path in [base, local, remote]:
            (path / "unchanged.txt").write_text("Same content\n")

        # Auto-merge: remote changed
        (base / "auto_remote.txt").write_text("base\n")
        (local / "auto_remote.txt").write_text("base\n")
        (remote / "auto_remote.txt").write_text("remote\n")

        # Auto-merge: local changed
        (base / "auto_local.txt").write_text("base\n")
        (local / "auto_local.txt").write_text("local\n")
        (remote / "auto_local.txt").write_text("base\n")

        # Conflict: both changed
        (base / "conflict.txt").write_text("base\n")
        (local / "conflict.txt").write_text("local\n")
        (remote / "conflict.txt").write_text("remote\n")

        result = engine.three_way_diff(base, local, remote)

        print(f"Statistics:")
        print(f"  Files compared: {result.stats.files_compared}")
        print(f"  Unchanged: {result.stats.files_unchanged}")
        print(f"  Auto-mergeable: {result.stats.auto_mergeable}")
        print(f"  Conflicts: {result.stats.files_conflicted}")
        print(f"\nSummary: {result.summary()}")
        print(f"Stats summary: {result.stats.summary()}")


def demo_performance():
    """Demonstrate performance with many files."""
    print("\n" + "=" * 70)
    print("PERFORMANCE DEMONSTRATION")
    print("=" * 70)

    import time

    engine = DiffEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        base = tmppath / "base"
        local = tmppath / "local"
        remote = tmppath / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Create 500 files (PRD performance target)
        print("\nCreating 500 test files...")
        num_files = 500
        for i in range(num_files):
            content = f"File {i}\nContent line 2\n"
            (base / f"file_{i:04d}.txt").write_text(content)
            (local / f"file_{i:04d}.txt").write_text(content)

            # Modify 10% in remote
            if i % 10 == 0:
                (remote / f"file_{i:04d}.txt").write_text(f"Modified {i}\n")
            else:
                (remote / f"file_{i:04d}.txt").write_text(content)

        print("Running three-way diff...")
        start = time.time()
        result = engine.three_way_diff(base, local, remote)
        elapsed = time.time() - start

        print(f"\nPerformance Results:")
        print(f"  Files processed: {num_files}")
        print(f"  Time elapsed: {elapsed:.3f} seconds")
        print(f"  Performance: {num_files/elapsed:.0f} files/second")
        print(f"  PRD target: <2.0 seconds for 500 files")
        print(f"  Status: {'PASS' if elapsed < 2.0 else 'FAIL'}")

        print(f"\nDiff Results:")
        print(f"  Auto-mergeable: {len(result.auto_mergeable)}")
        print(f"  Conflicts: {len(result.conflicts)}")


def main():
    """Run all demonstrations."""
    demo_basic_scenarios()
    demo_performance()

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
