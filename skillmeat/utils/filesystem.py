"""Filesystem utility functions for SkillMeat."""

import hashlib
import tempfile
from pathlib import Path
from typing import Union


def compute_content_hash(path: Path) -> str:
    """Compute SHA256 hash of file or directory contents.

    Args:
        path: Path to file or directory

    Returns:
        Hexadecimal SHA256 hash string

    Raises:
        FileNotFoundError: If path doesn't exist
        PermissionError: If path is not readable
    """
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    hasher = hashlib.sha256()

    if path.is_file():
        # Hash file contents
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
    elif path.is_dir():
        # Hash all files recursively (sorted for consistency)
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                # Include relative path in hash for structure
                rel_path = file_path.relative_to(path)
                hasher.update(str(rel_path).encode("utf-8"))

                # Include file contents
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        hasher.update(chunk)
    else:
        raise ValueError(f"Path is neither file nor directory: {path}")

    return hasher.hexdigest()


def atomic_write(content: str, dest: Path) -> None:
    """Write file atomically using temp file + rename.

    Args:
        content: String content to write
        dest: Destination file path

    Raises:
        IOError: If write operation fails
        PermissionError: If destination is not writable
    """
    # Ensure parent directory exists
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file in same directory
    # (ensures same filesystem for atomic rename)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp"
    )

    try:
        # Write content to temp file
        with open(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)

        # Atomic rename
        temp_path_obj = Path(temp_path)
        temp_path_obj.replace(dest)
    except Exception:
        # Clean up temp file on error
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass  # Best effort cleanup
        raise
