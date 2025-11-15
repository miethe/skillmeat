#!/usr/bin/env python3
"""Demo script showcasing DiffEngine capabilities."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from skillmeat.core.diff_engine import DiffEngine
from skillmeat.models import FileDiff, DiffResult


def main():
    """Demonstrate DiffEngine functionality."""
    print("DiffEngine Feature Demonstration")
    print("=" * 70)

    engine = DiffEngine()

    # Demo 1: File comparison
    print("\n1. FILE COMPARISON")
    print("-" * 70)

    source = Path(__file__).parent / "fixtures/phase2/diff/file_v1.txt"
    target = Path(__file__).parent / "fixtures/phase2/diff/file_v2.txt"

    result = engine.diff_files(source, target)

    print(f"Comparing: {source.name} -> {target.name}")
    print(f"  Status: {result.status}")
    print(f"  Changes: +{result.lines_added} -{result.lines_removed} lines")

    if result.unified_diff:
        print("\n  Diff preview:")
        for line in result.unified_diff.split('\n')[:15]:
            print(f"    {line}")

    # Demo 2: Directory comparison
    print("\n\n2. DIRECTORY COMPARISON")
    print("-" * 70)

    source_dir = Path(__file__).parent / "fixtures/phase2/diff/dir_v1"
    target_dir = Path(__file__).parent / "fixtures/phase2/diff/dir_v2"

    result = engine.diff_directories(source_dir, target_dir)

    print(f"Comparing directories:")
    print(f"  Source: {source_dir}")
    print(f"  Target: {target_dir}")
    print(f"\n  Summary: {result.summary()}")
    print(f"  Changes detected: {result.has_changes}")
    print(f"  Total files affected: {result.total_files_changed}")

    if result.files_added:
        print(f"\n  Added files:")
        for f in result.files_added:
            print(f"    + {f}")

    if result.files_removed:
        print(f"\n  Removed files:")
        for f in result.files_removed:
            print(f"    - {f}")

    if result.files_modified:
        print(f"\n  Modified files:")
        for f in result.files_modified:
            print(f"    ~ {f.path} (+{f.lines_added} -{f.lines_removed})")

    # Demo 3: Custom ignore patterns
    print("\n\n3. CUSTOM IGNORE PATTERNS")
    print("-" * 70)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create test directories
        source = tmppath / "source"
        target = tmppath / "target"
        source.mkdir()
        target.mkdir()

        # Add files
        (source / "include.txt").write_text("keep this")
        (target / "include.txt").write_text("keep this modified")
        (source / "test.log").write_text("log file")
        (target / "test.log").write_text("different log")

        # Compare without custom patterns
        result1 = engine.diff_directories(source, target)
        print(f"  Without custom patterns: {result1.total_files_changed} files changed")

        # Compare with custom pattern to ignore .log files
        result2 = engine.diff_directories(source, target, ignore_patterns=["*.log"])
        print(f"  With '*.log' ignored: {result2.total_files_changed} files changed")

    # Demo 4: Performance metrics
    print("\n\n4. PERFORMANCE CHARACTERISTICS")
    print("-" * 70)

    print("  Text vs Binary Detection: Reads first 8KB of file")
    print("  File Comparison: SHA-256 hash for identity check (fast path)")
    print("  Unified Diff: Uses Python difflib (efficient for text files)")
    print("  Directory Traversal: Recursive with pattern matching")
    print("  Default Ignore Patterns:")
    from skillmeat.core.diff_engine import DEFAULT_IGNORE_PATTERNS
    for pattern in DEFAULT_IGNORE_PATTERNS[:6]:
        print(f"    - {pattern}")
    print(f"    ... and {len(DEFAULT_IGNORE_PATTERNS) - 6} more")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print()


if __name__ == "__main__":
    main()
