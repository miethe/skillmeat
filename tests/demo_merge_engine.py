#!/usr/bin/env python3
"""Demo script for MergeEngine functionality.

This script demonstrates the MergeEngine's capabilities including:
- Auto-merging simple changes
- Detecting and marking conflicts
- Handling binary files
- Generating statistics

Run with: python tests/demo_merge_engine.py
"""

import tempfile
from pathlib import Path

from skillmeat.core.merge_engine import MergeEngine


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_file_content(path: Path, label: str):
    """Print the content of a file with a label."""
    if path.exists():
        content = path.read_text()
        print(f"\n{label}:")
        print("-" * 40)
        print(content)
        print("-" * 40)
    else:
        print(f"\n{label}: (file does not exist)")


def demo_auto_merge_simple():
    """Demonstrate simple auto-merge scenario."""
    print_section("Demo 1: Simple Auto-Merge (Only Local Changed)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create directory structure
        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Create files
        original_content = "def hello():\n    print('Hello, World!')\n"
        modified_content = "def hello():\n    print('Hello, SkillMeat!')\n"

        (base / "greeter.py").write_text(original_content)
        (local / "greeter.py").write_text(modified_content)  # Modified locally
        (remote / "greeter.py").write_text(original_content)  # Unchanged

        print("\nScenario: Local developer modified greeter.py, remote unchanged")
        print_file_content(base / "greeter.py", "BASE")
        print_file_content(local / "greeter.py", "LOCAL")
        print_file_content(remote / "greeter.py", "REMOTE")

        # Perform merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        print("\n" + "~" * 70)
        print("MERGE RESULT:")
        print("~" * 70)
        print(f"Success: {result.success}")
        print(f"Auto-merged: {result.auto_merged}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Summary: {result.summary()}")
        print(f"Stats: {result.stats.summary()}")

        print_file_content(output / "greeter.py", "MERGED OUTPUT")


def demo_auto_merge_both_sides():
    """Demonstrate auto-merge when both sides changed differently."""
    print_section("Demo 2: Auto-Merge (Both Sides Changed)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Multiple files with different scenarios
        # File 1: Only local changed
        (base / "local_only.txt").write_text("original\n")
        (local / "local_only.txt").write_text("local changes\n")
        (remote / "local_only.txt").write_text("original\n")

        # File 2: Only remote changed
        (base / "remote_only.txt").write_text("original\n")
        (local / "remote_only.txt").write_text("original\n")
        (remote / "remote_only.txt").write_text("remote changes\n")

        # File 3: Both changed identically
        (base / "both_same.txt").write_text("original\n")
        (local / "both_same.txt").write_text("same change\n")
        (remote / "both_same.txt").write_text("same change\n")

        print("\nScenario: Multiple files with different change patterns")
        print("  - local_only.txt: Only modified locally")
        print("  - remote_only.txt: Only modified remotely")
        print("  - both_same.txt: Modified identically in both")

        # Perform merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        print("\n" + "~" * 70)
        print("MERGE RESULT:")
        print("~" * 70)
        print(f"Success: {result.success}")
        print(f"Auto-merged files: {result.auto_merged}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Stats: {result.stats.summary()}")

        for filename in ["local_only.txt", "remote_only.txt", "both_same.txt"]:
            print_file_content(output / filename, f"MERGED {filename}")


def demo_conflict_markers():
    """Demonstrate conflict marker generation."""
    print_section("Demo 3: Conflict Detection and Markers")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Create conflicting changes
        base_content = "# Configuration\nVERSION = '1.0.0'\n"
        local_content = "# Configuration\nVERSION = '1.1.0'  # Local bump\n"
        remote_content = "# Configuration\nVERSION = '1.0.1'  # Patch release\n"

        (base / "config.py").write_text(base_content)
        (local / "config.py").write_text(local_content)
        (remote / "config.py").write_text(remote_content)

        print("\nScenario: Both local and remote modified config.py differently")
        print_file_content(base / "config.py", "BASE")
        print_file_content(local / "config.py", "LOCAL")
        print_file_content(remote / "config.py", "REMOTE")

        # Perform merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        print("\n" + "~" * 70)
        print("MERGE RESULT:")
        print("~" * 70)
        print(f"Success: {result.success}")
        print(f"Auto-merged: {len(result.auto_merged)}")
        print(f"Conflicts: {len(result.conflicts)}")

        if result.conflicts:
            conflict = result.conflicts[0]
            print(f"\nConflict details:")
            print(f"  File: {conflict.file_path}")
            print(f"  Type: {conflict.conflict_type}")
            print(f"  Strategy: {conflict.merge_strategy}")

        print_file_content(output / "config.py", "MERGED OUTPUT (with markers)")


def demo_deletion_conflict():
    """Demonstrate deletion conflict handling."""
    print_section("Demo 4: Deletion Conflict")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # File deleted locally but modified remotely
        (base / "deprecated.txt").write_text("Old feature\n")
        # Local: file deleted (doesn't exist)
        (remote / "deprecated.txt").write_text("Old feature - updated\n")

        print("\nScenario: File deleted locally but modified remotely")
        print_file_content(base / "deprecated.txt", "BASE")
        print("LOCAL: (file deleted)")
        print_file_content(remote / "deprecated.txt", "REMOTE")

        # Perform merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        print("\n" + "~" * 70)
        print("MERGE RESULT:")
        print("~" * 70)
        print(f"Success: {result.success}")
        print(f"Conflicts: {len(result.conflicts)}")

        if result.conflicts:
            conflict = result.conflicts[0]
            print(f"\nConflict details:")
            print(f"  File: {conflict.file_path}")
            print(f"  Type: {conflict.conflict_type}")
            print(f"  Local deleted: {conflict.local_content is None}")
            print(f"  Remote modified: {conflict.remote_content is not None}")

        print_file_content(output / "deprecated.txt", "MERGED OUTPUT (with markers)")


def demo_binary_conflict():
    """Demonstrate binary file conflict handling."""
    print_section("Demo 5: Binary File Conflict")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Binary files changed differently
        (base / "image.dat").write_bytes(b"\x00\x01\x02\x03")
        (local / "image.dat").write_bytes(b"\xff\xfe\xfd\xfc")
        (remote / "image.dat").write_bytes(b"\xaa\xbb\xcc\xdd")

        print("\nScenario: Binary file modified differently in local and remote")
        print("BASE: <binary data>")
        print("LOCAL: <different binary data>")
        print("REMOTE: <different binary data>")

        # Perform merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        print("\n" + "~" * 70)
        print("MERGE RESULT:")
        print("~" * 70)
        print(f"Success: {result.success}")
        print(f"Conflicts: {len(result.conflicts)}")
        print(f"Binary conflicts: {result.stats.binary_conflicts}")

        if result.conflicts:
            conflict = result.conflicts[0]
            print(f"\nConflict details:")
            print(f"  File: {conflict.file_path}")
            print(f"  Is binary: {conflict.is_binary}")
            print(f"  Type: {conflict.conflict_type}")
            print(f"  Note: Binary files cannot be auto-merged")
            print(f"        User must manually choose which version to keep")


def demo_mixed_scenario():
    """Demonstrate mixed auto-merge and conflicts."""
    print_section("Demo 6: Mixed Scenario (Auto-merge + Conflicts)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        base = tmpdir / "base"
        local = tmpdir / "local"
        remote = tmpdir / "remote"
        output = tmpdir / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Auto-mergeable file
        (base / "readme.md").write_text("# Project\nWelcome!\n")
        (local / "readme.md").write_text(
            "# Project\nWelcome!\n\n## Installation\nRun pip install.\n"
        )
        (remote / "readme.md").write_text("# Project\nWelcome!\n")

        # Conflicting file
        (base / "version.txt").write_text("1.0.0\n")
        (local / "version.txt").write_text("1.1.0\n")
        (remote / "version.txt").write_text("1.0.1\n")

        # Another auto-mergeable
        (base / "license.txt").write_text("MIT")
        (local / "license.txt").write_text("MIT")
        (remote / "license.txt").write_text("Apache 2.0")

        print("\nScenario: Mix of auto-mergeable and conflicting files")
        print("  - readme.md: Auto-merge (local changed)")
        print("  - version.txt: CONFLICT (both changed)")
        print("  - license.txt: Auto-merge (remote changed)")

        # Perform merge
        engine = MergeEngine()
        result = engine.merge(base, local, remote, output)

        print("\n" + "~" * 70)
        print("MERGE RESULT:")
        print("~" * 70)
        print(f"Success: {result.success}")
        print(f"Auto-merged: {result.auto_merged}")
        print(f"Conflicts: {[c.file_path for c in result.conflicts]}")
        print(f"Summary: {result.summary()}")
        print(f"Stats: {result.stats.summary()}")

        print_file_content(output / "readme.md", "readme.md (auto-merged)")
        print_file_content(
            output / "version.txt", "version.txt (with conflict markers)"
        )
        print_file_content(output / "license.txt", "license.txt (auto-merged)")


def demo_single_file_merge():
    """Demonstrate merge_files() for single file."""
    print_section("Demo 7: Single File Merge")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        base_file = tmpdir / "base.txt"
        local_file = tmpdir / "local.txt"
        remote_file = tmpdir / "remote.txt"
        output_file = tmpdir / "merged.txt"

        base_file.write_text("Line 1\nLine 2\n")
        local_file.write_text("Line 1\nLine 2 - local edit\n")
        remote_file.write_text("Line 1\nLine 2\n")

        print("\nScenario: Merging single file (local changed)")
        print_file_content(base_file, "BASE")
        print_file_content(local_file, "LOCAL")
        print_file_content(remote_file, "REMOTE")

        # Perform merge
        engine = MergeEngine()
        result = engine.merge_files(base_file, local_file, remote_file, output_file)

        print("\n" + "~" * 70)
        print("MERGE RESULT:")
        print("~" * 70)
        print(f"Success: {result.success}")
        print(f"Merged content available: {result.merged_content is not None}")

        if result.merged_content:
            print("\nMerged content:")
            print("-" * 40)
            print(result.merged_content)
            print("-" * 40)


def main():
    """Run all demos."""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#" + "  MergeEngine Demonstration".center(68) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)

    demos = [
        demo_auto_merge_simple,
        demo_auto_merge_both_sides,
        demo_conflict_markers,
        demo_deletion_conflict,
        demo_binary_conflict,
        demo_mixed_scenario,
        demo_single_file_merge,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\nERROR in demo: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "#" * 70)
    print("#" + "  End of Demonstration".center(68) + "#")
    print("#" * 70)
    print()


if __name__ == "__main__":
    main()
