"""Git hook installer and BOM-hash integration for SkillMeat.

This module wires SkillMeat's BOM (Bill of Materials) snapshot mechanism into
the standard Git commit workflow via two hooks:

1. ``prepare-commit-msg`` — appends a ``SkillBOM-Hash: sha256:<hex>`` footer to
   every commit message so the BOM state at commit time is permanently recorded
   in history.

2. ``post-commit`` — placeholder for future work that links the final commit SHA
   back to the BOM snapshot stored in the DB.

Design decisions
----------------
* **Fail-open** — both hooks call into this module with ``2>/dev/null || true``
  so a Python import error or unexpected exception never blocks a commit.
* **Idempotent footer** — ``prepare_commit_msg_hook`` detects an existing
  ``SkillBOM-Hash:`` line and skips re-appending, making the hook safe to
  invoke multiple times (e.g. ``--amend`` flows).
* **Backup before overwrite** — existing hook files are renamed to ``.bak``
  and a warning is emitted so user scripts are not silently destroyed.
* **Pure stdlib** — no third-party imports; ``hashlib``, ``pathlib``,
  ``stat``, ``shutil``, and ``logging`` only.

CLI entry-point
---------------
The installed shell scripts delegate to::

    python -m skillmeat.core.bom.git_integration <command> [args...]

Supported commands:

* ``prepare-commit-msg <COMMIT_MSG_FILE>``
* ``post-commit``

Run ``python -m skillmeat.core.bom.git_integration --help`` for usage.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import stat
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BOM_FOOTER_PREFIX = "SkillBOM-Hash: sha256:"
_CONTEXT_LOCK_FILENAME = "context.lock"

# Shell script templates (thin wrappers that delegate to Python).
# $@ forwards all hook arguments (e.g. COMMIT_MSG_FILE for prepare-commit-msg).
_PREPARE_COMMIT_MSG_SCRIPT = """\
#!/bin/sh
# SkillBOM prepare-commit-msg hook — managed by SkillMeat.
# Do NOT remove the marker comment above; it is used to detect managed hooks.
python -m skillmeat.core.bom.git_integration prepare-commit-msg "$@" 2>/dev/null || true
"""

_POST_COMMIT_SCRIPT = """\
#!/bin/sh
# SkillBOM post-commit hook — managed by SkillMeat.
# Do NOT remove the marker comment above; it is used to detect managed hooks.
python -m skillmeat.core.bom.git_integration post-commit "$@" 2>/dev/null || true
"""

# Map hook name → script content
_HOOK_SCRIPTS: dict[str, str] = {
    "prepare-commit-msg": _PREPARE_COMMIT_MSG_SCRIPT,
    "post-commit": _POST_COMMIT_SCRIPT,
}

# Marker string present in every managed hook script.
_MANAGED_MARKER = "managed by SkillMeat"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def install_hooks(repo_path: "str | Path") -> None:
    """Install SkillBOM Git hooks into *repo_path*/.git/hooks/.

    Parameters
    ----------
    repo_path:
        Root of the Git repository (the directory that contains ``.git/``).

    Raises
    ------
    FileNotFoundError
        If ``repo_path/.git/`` does not exist (not a Git repository).
    """
    repo_path = Path(repo_path)
    git_dir = repo_path / ".git"

    if not git_dir.is_dir():
        raise FileNotFoundError(
            f"No .git directory found at {git_dir}. "
            "Is this a Git repository?"
        )

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    for hook_name, script_content in _HOOK_SCRIPTS.items():
        hook_path = hooks_dir / hook_name
        _install_single_hook(hook_path, script_content, hook_name)

    logger.info("SkillBOM Git hooks installed at %s", hooks_dir)


def compute_bom_hash(context_lock_path: "str | Path") -> str:
    """Return the SHA-256 hex digest of *context_lock_path* file content.

    Parameters
    ----------
    context_lock_path:
        Path to the ``context.lock`` file (or any BOM snapshot file).

    Returns
    -------
    str
        64-character lowercase hex string.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    """
    context_lock_path = Path(context_lock_path)
    data = context_lock_path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def prepare_commit_msg_hook(
    commit_msg_file: str,
    repo_path: "str | Path" = ".",
) -> None:
    """Append a ``SkillBOM-Hash`` footer to the commit message file.

    This function is invoked by the installed ``prepare-commit-msg`` shell
    hook.  It is designed to be **fail-open**: any exception is logged as a
    warning and the function returns without raising so the commit is never
    blocked.

    Parameters
    ----------
    commit_msg_file:
        Path to the temporary file Git passes to ``prepare-commit-msg``.
    repo_path:
        Root of the Git repository.  Used to locate ``context.lock``.
    """
    try:
        _append_bom_footer(commit_msg_file, Path(repo_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "SkillBOM: failed to append BOM hash to commit message (%s). "
            "Commit will proceed without BOM footer.",
            exc,
        )


def post_commit_hook(repo_path: "str | Path" = ".") -> None:
    """Link the latest commit SHA back to the BOM snapshot (placeholder).

    Currently this is a no-op stub.  Future work will:
    - Read ``git rev-parse HEAD`` to obtain the commit SHA.
    - Look up the BOM snapshot whose hash matches the footer in the commit
      message.
    - Record the commit SHA in the DB against the ``BomSnapshot`` row.

    Fail-open: exceptions are logged as warnings only.
    """
    try:
        logger.debug(
            "SkillBOM post-commit hook invoked (repo=%s) — no-op in this version.",
            repo_path,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("SkillBOM post-commit hook error: %s", exc)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _install_single_hook(
    hook_path: Path,
    script_content: str,
    hook_name: str,
) -> None:
    """Write *script_content* to *hook_path*, backing up any existing file."""
    if hook_path.exists():
        existing_text = _read_text_safe(hook_path)
        if _MANAGED_MARKER in (existing_text or ""):
            # Already our hook — overwrite silently (update).
            logger.debug("Updating existing SkillBOM hook: %s", hook_path)
        else:
            # Unknown / user-defined hook — back it up.
            backup = hook_path.with_suffix(".bak")
            shutil.copy2(str(hook_path), str(backup))
            logger.warning(
                "Existing %s hook backed up to %s. "
                "Installing SkillBOM hook in its place.",
                hook_name,
                backup,
            )

    hook_path.write_text(script_content, encoding="utf-8")
    _make_executable(hook_path)
    logger.debug("Installed hook: %s", hook_path)


def _make_executable(path: Path) -> None:
    """Set owner-executable + group/other read-execute bits (chmod 755)."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
               | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def _find_context_lock(repo_path: Path) -> Optional[Path]:
    """Return the first ``context.lock`` file found under *repo_path*.

    Search order:
    1. ``<repo_path>/context.lock``
    2. ``<repo_path>/.claude/context.lock``
    3. ``<repo_path>/.skillmeat/context.lock``
    """
    candidates = [
        repo_path / _CONTEXT_LOCK_FILENAME,
        repo_path / ".claude" / _CONTEXT_LOCK_FILENAME,
        repo_path / ".skillmeat" / _CONTEXT_LOCK_FILENAME,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _append_bom_footer(commit_msg_file: str, repo_path: Path) -> None:
    """Core logic: read commit message, append BOM footer if not present."""
    msg_path = Path(commit_msg_file)
    if not msg_path.is_file():
        logger.warning(
            "SkillBOM: commit message file not found: %s", commit_msg_file
        )
        return

    existing_msg = msg_path.read_text(encoding="utf-8", errors="replace")

    # Idempotency guard — skip if footer already present.
    if _BOM_FOOTER_PREFIX in existing_msg:
        logger.debug("SkillBOM: BOM footer already present, skipping.")
        return

    # Locate context.lock and compute its hash.
    lock_path = _find_context_lock(repo_path)
    if lock_path is None:
        logger.debug(
            "SkillBOM: no context.lock found under %s; skipping BOM footer.",
            repo_path,
        )
        return

    bom_hash = compute_bom_hash(lock_path)
    footer = f"{_BOM_FOOTER_PREFIX}{bom_hash}"

    # Append footer, ensuring exactly one blank line separator.
    stripped = existing_msg.rstrip("\n")
    new_msg = f"{stripped}\n\n{footer}\n"

    msg_path.write_text(new_msg, encoding="utf-8")
    logger.debug("SkillBOM: appended footer %s", footer)


def _read_text_safe(path: Path) -> Optional[str]:
    """Read *path* as text, returning ``None`` on any error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _usage() -> None:
    print(
        "Usage:\n"
        "  python -m skillmeat.core.bom.git_integration install <REPO_PATH>\n"
        "  python -m skillmeat.core.bom.git_integration prepare-commit-msg"
        " <COMMIT_MSG_FILE> [REPO_PATH]\n"
        "  python -m skillmeat.core.bom.git_integration post-commit"
        " [REPO_PATH]\n"
    )


def _main(argv: list[str]) -> int:
    """Entry-point for shell hook delegation.

    Returns an exit code (0 = success, non-zero = error).
    Hooks invoke this with ``|| true`` so the exit code is informational only.
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s [skillbom] %(message)s",
    )

    if not argv:
        _usage()
        return 1

    command, *rest = argv

    if command in ("--help", "-h"):
        _usage()
        return 0

    if command == "install":
        repo = rest[0] if rest else "."
        try:
            install_hooks(repo)
            print(f"SkillBOM hooks installed in {Path(repo).resolve() / '.git' / 'hooks'}")
            return 0
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if command == "prepare-commit-msg":
        if not rest:
            print(
                "Error: COMMIT_MSG_FILE argument required", file=sys.stderr
            )
            return 1
        commit_msg_file = rest[0]
        repo = rest[1] if len(rest) > 1 else "."
        prepare_commit_msg_hook(commit_msg_file, repo)
        return 0

    if command == "post-commit":
        repo = rest[0] if rest else "."
        post_commit_hook(repo)
        return 0

    print(f"Unknown command: {command!r}", file=sys.stderr)
    _usage()
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
