#!/usr/bin/env python3
"""Basic manual test for DiffEngine functionality.

This script verifies that the DiffEngine implementation works correctly
for both file and directory comparisons.
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from skillmeat.core.diff_engine import DiffEngine


def test_diff_files():
    """Test file comparison."""
    print("=" * 60)
    print("TEST: File Comparison")
    print("=" * 60)

    engine = DiffEngine()

    # Test text file diff
    source = Path(__file__).parent / "fixtures/phase2/diff/file_v1.txt"
    target = Path(__file__).parent / "fixtures/phase2/diff/file_v2.txt"

    if not source.exists() or not target.exists():
        print(f"ERROR: Test files not found")
        print(f"  Source: {source}")
        print(f"  Target: {target}")
        return False

    result = engine.diff_files(source, target)

    print(f"\nFile: {result.path}")
    print(f"Status: {result.status}")
    print(f"Lines added: {result.lines_added}")
    print(f"Lines removed: {result.lines_removed}")

    if result.unified_diff:
        print(f"\nUnified diff (first 500 chars):")
        print(result.unified_diff[:500])

    # Verify expectations
    success = True
    if result.status != "modified":
        print(f"\nERROR: Expected status 'modified', got '{result.status}'")
        success = False

    if result.lines_added != 2:
        print(f"\nERROR: Expected 2 lines added, got {result.lines_added}")
        success = False

    if result.lines_removed != 1:
        print(f"\nERROR: Expected 1 line removed, got {result.lines_removed}")
        success = False

    if success:
        print("\n[PASS] File comparison test passed")
    else:
        print("\n[FAIL] File comparison test failed")

    return success


def test_diff_directories():
    """Test directory comparison."""
    print("\n" + "=" * 60)
    print("TEST: Directory Comparison")
    print("=" * 60)

    engine = DiffEngine()

    # Test directory diff
    source_dir = Path(__file__).parent / "fixtures/phase2/diff/dir_v1"
    target_dir = Path(__file__).parent / "fixtures/phase2/diff/dir_v2"

    if not source_dir.exists() or not target_dir.exists():
        print(f"ERROR: Test directories not found")
        print(f"  Source: {source_dir}")
        print(f"  Target: {target_dir}")
        return False

    result = engine.diff_directories(source_dir, target_dir)

    print(f"\nSource: {result.source_path}")
    print(f"Target: {result.target_path}")
    print(f"\nSummary: {result.summary()}")
    print(f"Total files changed: {result.total_files_changed}")
    print(f"Has changes: {result.has_changes}")

    print(f"\nFiles added ({len(result.files_added)}):")
    for f in result.files_added:
        print(f"  + {f}")

    print(f"\nFiles removed ({len(result.files_removed)}):")
    for f in result.files_removed:
        print(f"  - {f}")

    print(f"\nFiles modified ({len(result.files_modified)}):")
    for f in result.files_modified:
        print(f"  ~ {f.path} (+{f.lines_added} -{f.lines_removed})")

    print(f"\nFiles unchanged ({len(result.files_unchanged)}):")
    for f in result.files_unchanged:
        print(f"  = {f}")

    print(f"\nTotal: +{result.total_lines_added} -{result.total_lines_removed} lines")

    # Verify expectations
    success = True

    if len(result.files_added) != 1 or 'added.txt' not in result.files_added:
        print(f"\nERROR: Expected 1 added file (added.txt)")
        success = False

    if len(result.files_removed) != 1 or 'removed.txt' not in result.files_removed:
        print(f"\nERROR: Expected 1 removed file (removed.txt)")
        success = False

    if len(result.files_modified) != 1:
        print(f"\nERROR: Expected 1 modified file")
        success = False

    if len(result.files_unchanged) != 1 or 'common.txt' not in result.files_unchanged:
        print(f"\nERROR: Expected 1 unchanged file (common.txt)")
        success = False

    if not result.has_changes:
        print(f"\nERROR: Expected has_changes to be True")
        success = False

    if success:
        print("\n[PASS] Directory comparison test passed")
    else:
        print("\n[FAIL] Directory comparison test failed")

    return success


def test_ignore_patterns():
    """Test ignore patterns."""
    print("\n" + "=" * 60)
    print("TEST: Ignore Patterns")
    print("=" * 60)

    engine = DiffEngine()

    # Create temp directories with files that should be ignored
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create source directory
        source = tmppath / "source"
        source.mkdir()
        (source / "keep.txt").write_text("keep this")
        (source / "ignore.pyc").write_text("ignore this")
        pycache = source / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.pyc").write_text("cached")

        # Create target directory
        target = tmppath / "target"
        target.mkdir()
        (target / "keep.txt").write_text("keep this")
        (target / "ignore.pyc").write_text("ignore this")
        pycache = target / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.pyc").write_text("cached")

        result = engine.diff_directories(source, target)

        print(f"\nTotal files found: {len(result.files_unchanged)}")
        print(f"Files: {result.files_unchanged}")

        # Should only find keep.txt, ignoring .pyc and __pycache__
        success = True
        if len(result.files_unchanged) != 1 or 'keep.txt' not in result.files_unchanged:
            print(f"\nERROR: Expected only keep.txt, got {result.files_unchanged}")
            success = False

        if success:
            print("\n[PASS] Ignore patterns test passed")
        else:
            print("\n[FAIL] Ignore patterns test failed")

        return success


def test_performance():
    """Test performance with multiple files."""
    print("\n" + "=" * 60)
    print("TEST: Performance (100 files)")
    print("=" * 60)

    import tempfile
    import time

    engine = DiffEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create source directory with 100 files
        source = tmppath / "source"
        source.mkdir()
        for i in range(100):
            (source / f"file_{i:03d}.txt").write_text(f"Content {i}\nLine 2\nLine 3\n")

        # Create target directory with modifications
        target = tmppath / "target"
        target.mkdir()
        for i in range(100):
            if i % 10 == 0:
                # Modify every 10th file
                (target / f"file_{i:03d}.txt").write_text(f"Modified {i}\nLine 2\nLine 3\nNew line\n")
            else:
                # Keep unchanged
                (target / f"file_{i:03d}.txt").write_text(f"Content {i}\nLine 2\nLine 3\n")

        # Measure time
        start = time.time()
        result = engine.diff_directories(source, target)
        elapsed = time.time() - start

        print(f"\nFiles compared: 100")
        print(f"Time elapsed: {elapsed:.3f} seconds")
        print(f"Files modified: {len(result.files_modified)}")
        print(f"Files unchanged: {len(result.files_unchanged)}")
        print(f"Performance: {100/elapsed:.0f} files/second")

        success = True
        if elapsed > 2.0:
            print(f"\nWARNING: Performance slower than 2s target (PRD requirement for 500 files)")
            print(f"  Extrapolated time for 500 files: {elapsed * 5:.3f} seconds")
        else:
            print(f"\nPerformance acceptable. Extrapolated time for 500 files: {elapsed * 5:.3f} seconds")

        if len(result.files_modified) != 10:
            print(f"\nERROR: Expected 10 modified files, got {len(result.files_modified)}")
            success = False

        if success:
            print("\n[PASS] Performance test passed")
        else:
            print("\n[FAIL] Performance test failed")

        return success


def main():
    """Run all tests."""
    print("\nDiffEngine Basic Verification Tests")
    print("=" * 60)

    results = []

    results.append(("File Comparison", test_diff_files()))
    results.append(("Directory Comparison", test_diff_directories()))
    results.append(("Ignore Patterns", test_ignore_patterns()))
    results.append(("Performance", test_performance()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
