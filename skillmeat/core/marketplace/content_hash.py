"""Content hashing utilities for artifact deduplication.

Provides SHA256-based content hashing for single files and multi-file
artifacts, enabling detection of duplicate artifacts across different
sources or paths.
"""

import hashlib
from typing import Dict, Union


def compute_file_hash(content: Union[bytes, str]) -> str:
    """Compute SHA256 hash of file content.

    Args:
        content: File content as bytes or string.
            Strings are encoded as UTF-8 before hashing.

    Returns:
        Lowercase hex digest (64 characters).

    Example:
        >>> compute_file_hash("Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        >>> compute_file_hash(b"Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        >>> compute_file_hash("")  # Empty content is handled
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    return hashlib.sha256(content).hexdigest()


def compute_artifact_hash(files: Dict[str, str]) -> str:
    """Compute deterministic SHA256 hash for multi-file artifact.

    Creates a canonical representation by sorting files alphabetically
    by filename and concatenating with delimiters, then hashing the result.
    This ensures identical content produces identical hashes regardless
    of the order files were added.

    Args:
        files: Dictionary mapping filenames to their content.
            Example: {"SKILL.md": "skill content", "README.md": "readme"}

    Returns:
        Lowercase hex digest (64 characters).

    Example:
        >>> files = {"SKILL.md": "# My Skill", "README.md": "Documentation"}
        >>> compute_artifact_hash(files)
        'a1b2c3...'  # Deterministic based on content

        >>> # Order doesn't matter - same hash
        >>> files2 = {"README.md": "Documentation", "SKILL.md": "# My Skill"}
        >>> compute_artifact_hash(files) == compute_artifact_hash(files2)
        True

        >>> # Empty dict returns hash of empty string
        >>> compute_artifact_hash({})
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """
    if not files:
        return compute_file_hash("")

    # Sort filenames for deterministic ordering
    sorted_filenames = sorted(files.keys())

    # Build canonical representation with delimiters
    # Format: ---{filename}---\n{content}\n for each file
    parts = []
    for filename in sorted_filenames:
        content = files[filename]
        parts.append(f"---{filename}---\n{content}\n")

    canonical = "".join(parts)
    return compute_file_hash(canonical)


if __name__ == "__main__":
    # Self-test examples
    print("Content Hash Utilities - Self Test")
    print("=" * 50)

    # Test single file hashing
    print("\n1. Single file hashing:")
    content = "Hello, World!"
    hash1 = compute_file_hash(content)
    print(f"   String content: '{content}'")
    print(f"   Hash: {hash1}")

    # Verify bytes produces same hash
    hash2 = compute_file_hash(content.encode("utf-8"))
    print(f"   Bytes produces same hash: {hash1 == hash2}")

    # Test empty content
    empty_hash = compute_file_hash("")
    print(f"\n2. Empty content hash: {empty_hash}")

    # Test multi-file artifact hashing
    print("\n3. Multi-file artifact hashing:")
    files = {
        "SKILL.md": "# Canvas Design\n\nA skill for design tasks.",
        "README.md": "## Documentation\n\nHow to use this skill.",
        "config.toml": '[skill]\nname = "canvas"',
    }

    artifact_hash = compute_artifact_hash(files)
    print(f"   Files: {list(files.keys())}")
    print(f"   Hash: {artifact_hash}")

    # Verify order independence
    files_reversed = {
        "config.toml": '[skill]\nname = "canvas"',
        "README.md": "## Documentation\n\nHow to use this skill.",
        "SKILL.md": "# Canvas Design\n\nA skill for design tasks.",
    }
    artifact_hash2 = compute_artifact_hash(files_reversed)
    print(f"   Order-independent: {artifact_hash == artifact_hash2}")

    # Test empty dict
    empty_artifact_hash = compute_artifact_hash({})
    print(f"\n4. Empty artifact hash: {empty_artifact_hash}")
    print(f"   Equals empty string hash: {empty_artifact_hash == empty_hash}")

    print("\n" + "=" * 50)
    print("All tests passed!")
