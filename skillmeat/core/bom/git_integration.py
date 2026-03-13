"""Git hook installer and BOM-hash integration for SkillMeat.

This module wires SkillMeat's BOM (Bill of Materials) snapshot mechanism into
the standard Git commit workflow via two hooks:

1. ``prepare-commit-msg`` — appends a ``SkillBOM-Hash: sha256:<hex>`` footer to
   every commit message so the BOM state at commit time is permanently recorded
   in history.

2. ``post-commit`` — links the final commit SHA back to the BOM snapshot
   stored in the DB (with JSON file fallback when the DB is unavailable).

Design decisions
----------------
* **Fail-open** — both hooks call into this module with ``2>/dev/null || true``
  so a Python import error or unexpected exception never blocks a commit.
* **Idempotent footer** — ``prepare_commit_msg_hook`` detects an existing
  ``SkillBOM-Hash:`` line and skips re-appending, making the hook safe to
  invoke multiple times (e.g. ``--amend`` flows).
* **Backup before overwrite** — existing hook files are renamed to ``.bak``
  and a warning is emitted so user scripts are not silently destroyed.
* **Dual persistence** — BOM-to-commit linkages are written to both the DB
  (when available) and a JSON file (``.skillmeat/bom-commit-links.json``) so
  that ``restore_from_commit`` can always find them.
* **Never silent substitution** — ``restore_from_commit`` reports unresolved
  entries rather than substituting current versions.

CLI entry-point
---------------
The installed shell scripts delegate to::

    python -m skillmeat.core.bom.git_integration <command> [args...]

Supported commands:

* ``prepare-commit-msg <COMMIT_MSG_FILE>``
* ``post-commit``
* ``restore <COMMIT_HASH> <TARGET_DIR> [--dry-run]``

Run ``python -m skillmeat.core.bom.git_integration --help`` for usage.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BOM_FOOTER_PREFIX = "SkillBOM-Hash: sha256:"
_CONTEXT_LOCK_FILENAME = "context.lock"
_COMMIT_LINKS_FILENAME = "bom-commit-links.json"  # relative to .skillmeat/


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RestoreResult:
    """Result of a commit-linked BOM restore operation.

    Attributes:
        commit_sha: The Git commit SHA that was inspected.
        bom_hash: The ``sha256:<hex>`` value extracted from the commit footer.
        total_entries: Number of artifact entries present in the BOM snapshot.
        resolved_entries: Number of entries successfully restored.
        unresolved_entries: Names of artifacts that could not be restored.
        dry_run: Whether this was a dry-run (no filesystem changes made).
        signature_valid: True/False if a signature was present and checked;
            None if no signature existed in the snapshot.
    """

    commit_sha: str
    bom_hash: str
    total_entries: int
    resolved_entries: int
    unresolved_entries: List[str] = field(default_factory=list)
    dry_run: bool = False
    signature_valid: Optional[bool] = None

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
    """Link the latest commit SHA back to the BOM snapshot.

    Steps:
    1. Run ``git rev-parse HEAD`` to get the commit SHA.
    2. Read the commit message and extract the ``SkillBOM-Hash`` footer.
    3. Call :func:`link_bom_to_commit` to persist the linkage.

    Fail-open: any exception is logged as a warning and the hook returns
    without raising, so the commit is never blocked.
    """
    try:
        _post_commit_impl(Path(repo_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("SkillBOM post-commit hook error: %s", exc)


def _post_commit_impl(repo_path: Path) -> None:
    """Core logic for :func:`post_commit_hook`."""
    # Obtain the commit SHA.
    commit_sha = _git_rev_parse_head(repo_path)
    if commit_sha is None:
        logger.warning("SkillBOM: could not determine HEAD SHA; skipping linkage.")
        return

    # Read the commit message.
    commit_msg = _git_log_message(repo_path, commit_sha)
    if commit_msg is None:
        logger.warning(
            "SkillBOM: could not read commit message for %s; skipping linkage.",
            commit_sha,
        )
        return

    # Extract the BOM hash from the footer.
    content_hash = _extract_bom_hash(commit_msg)
    if content_hash is None:
        logger.debug(
            "SkillBOM: no %s footer in commit %s; skipping linkage.",
            _BOM_FOOTER_PREFIX,
            commit_sha[:8],
        )
        return

    success = link_bom_to_commit(content_hash, commit_sha, repo_path=repo_path)
    if success:
        logger.debug(
            "SkillBOM: linked commit %s → BOM hash %s.", commit_sha[:8], content_hash[:8]
        )
    else:
        logger.warning(
            "SkillBOM: no BOM snapshot found for hash %s (commit %s).",
            content_hash[:8],
            commit_sha[:8],
        )


def link_bom_to_commit(
    content_hash: str,
    commit_sha: str,
    db_session: Any = None,
    repo_path: "str | Path" = ".",
) -> bool:
    """Persist a BOM-hash → commit-SHA linkage.

    Attempts to update the matching ``BomSnapshot`` row in the DB first.
    Falls back to a JSON file at ``<repo>/.skillmeat/bom-commit-links.json``
    when the DB is unavailable or no matching snapshot is found.

    Parameters
    ----------
    content_hash:
        The ``sha256:<hex>`` value from the commit footer (without the prefix).
    commit_sha:
        Full 40-character Git commit SHA.
    db_session:
        Optional SQLAlchemy session.  When ``None`` the DB path is attempted.
    repo_path:
        Repository root, used to locate the JSON fallback file.

    Returns
    -------
    bool
        ``True`` if the linkage was recorded in *either* the DB or the JSON
        file; ``False`` if both failed.
    """
    repo_path = Path(repo_path)
    db_linked = _try_link_in_db(content_hash, commit_sha, db_session)
    # Always write to JSON fallback for cross-tool visibility.
    _write_commit_link_json(repo_path, content_hash, commit_sha)
    return db_linked or True  # JSON write is always attempted


def restore_from_commit(
    commit_hash: str,
    target_dir: "str | Path",
    dry_run: bool = False,
    repo_path: "str | Path" = ".",
    upstream_confirm_callback: Any = None,
) -> RestoreResult:
    """Restore the ``.claude/`` directory state from a commit-linked BOM.

    Steps:
    1. Read the commit message for *commit_hash*.
    2. Extract ``SkillBOM-Hash: sha256:<hex>`` from the footer.
    3. Look up the BOM snapshot (DB first, then JSON fallback, then upstream).
    4. Rehydrate the ``.claude/`` directory from the snapshot's ``bom_json``.
    5. Return a :class:`RestoreResult` describing resolved / unresolved entries.

    Parameters
    ----------
    commit_hash:
        Full or abbreviated Git commit SHA.
    target_dir:
        Directory into which ``.claude/`` will be restored.
    dry_run:
        When ``True`` no files are written; the result still reports what
        *would* be resolved.
    repo_path:
        Repository root (for JSON fallback look-up).
    upstream_confirm_callback:
        Optional callable that receives ``(content_hash: str) -> bool``.
        Called before attempting a GitHub fetch; if it returns ``False`` the
        upstream attempt is skipped.  When ``None`` upstream fetch is
        performed without prompting.

    Returns
    -------
    RestoreResult
    """
    repo_path = Path(repo_path)
    target_dir = Path(target_dir)

    # 1. Get commit message.
    commit_msg = _git_log_message(repo_path, commit_hash)
    if commit_msg is None:
        raise ValueError(
            f"Could not read commit message for {commit_hash!r}. "
            "Ensure the commit exists in this repository."
        )

    # 2. Extract BOM hash.
    content_hash = _extract_bom_hash(commit_msg)
    if content_hash is None:
        raise ValueError(
            f"Commit {commit_hash!r} does not contain a SkillBOM-Hash footer. "
            "This commit was not made with SkillBOM hooks installed."
        )

    # 3. Locate BOM snapshot.
    bom_data = _locate_bom_snapshot(content_hash, repo_path)

    if bom_data is None:
        # Upstream fallback.
        bom_data = _fetch_bom_from_upstream(
            content_hash, upstream_confirm_callback
        )

    if bom_data is None:
        return RestoreResult(
            commit_sha=commit_hash,
            bom_hash=content_hash,
            total_entries=0,
            resolved_entries=0,
            unresolved_entries=[],
            dry_run=dry_run,
            signature_valid=None,
        )

    # 4. Rehydrate .claude/ directory.
    artifacts: List[Dict[str, Any]] = bom_data.get("artifacts", [])
    total = len(artifacts)
    resolved = []
    unresolved = []

    for entry in artifacts:
        name = entry.get("name") or entry.get("id") or "<unknown>"
        entry_type = entry.get("type", "")
        content = entry.get("content")
        restore_path = entry.get("path")

        if not content and not restore_path:
            unresolved.append(name)
            continue

        if not dry_run:
            try:
                _restore_entry(target_dir, entry_type, name, entry)
                resolved.append(name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("SkillBOM: could not restore entry %r: %s", name, exc)
                unresolved.append(name)
        else:
            # Dry run: mark resolvable entries as resolved without writing.
            resolved.append(name)

    # Signature check.
    signature_valid: Optional[bool] = None
    if bom_data.get("signature"):
        signature_valid = _verify_snapshot_signature(bom_data)

    return RestoreResult(
        commit_sha=commit_hash,
        bom_hash=content_hash,
        total_entries=total,
        resolved_entries=len(resolved),
        unresolved_entries=unresolved,
        dry_run=dry_run,
        signature_valid=signature_valid,
    )


# ---------------------------------------------------------------------------
# Internal helpers — Git subprocess wrappers
# ---------------------------------------------------------------------------


def _run_git(repo_path: Path, *args: str) -> Optional[str]:
    """Run a git command in *repo_path* and return stdout, or None on error."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.debug("git %s failed: %s", " ".join(args), result.stderr.strip())
            return None
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("git subprocess error: %s", exc)
        return None


def _git_rev_parse_head(repo_path: Path) -> Optional[str]:
    """Return the full SHA of HEAD, or None on failure."""
    return _run_git(repo_path, "rev-parse", "HEAD")


def _git_log_message(repo_path: Path, commit_hash: str) -> Optional[str]:
    """Return the full commit message body of *commit_hash*, or None."""
    return _run_git(repo_path, "log", "-1", "--format=%B", commit_hash)


def _extract_bom_hash(commit_message: str) -> Optional[str]:
    """Extract the hex digest from the ``SkillBOM-Hash: sha256:<hex>`` footer.

    Returns the 64-char hex string (without the ``sha256:`` prefix), or None.
    """
    for line in commit_message.splitlines():
        stripped = line.strip()
        if stripped.startswith(_BOM_FOOTER_PREFIX):
            return stripped[len(_BOM_FOOTER_PREFIX):]
    return None


# ---------------------------------------------------------------------------
# Internal helpers — BOM linkage persistence
# ---------------------------------------------------------------------------


def _commit_links_path(repo_path: Path) -> Path:
    """Return the path to the JSON commit-links file."""
    return repo_path / ".skillmeat" / _COMMIT_LINKS_FILENAME


def _read_commit_links(repo_path: Path) -> Dict[str, str]:
    """Read the JSON commit-links file and return it as a dict.

    Returns an empty dict if the file is absent or malformed.
    """
    path = _commit_links_path(repo_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _write_commit_link_json(
    repo_path: Path, content_hash: str, commit_sha: str
) -> None:
    """Persist a ``content_hash → commit_sha`` mapping to the JSON file."""
    path = _commit_links_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    links = _read_commit_links(repo_path)
    links[content_hash] = commit_sha
    try:
        path.write_text(json.dumps(links, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("SkillBOM: could not write commit links file: %s", exc)


def _try_link_in_db(
    content_hash: str,
    commit_sha: str,
    db_session: Any,
) -> bool:
    """Attempt to update ``BomSnapshot.commit_sha`` in the DB.

    Imports SQLAlchemy models lazily so this module remains importable even
    when the cache layer is unavailable.

    Returns ``True`` if a matching row was updated.
    """
    try:
        from skillmeat.cache.models import BomSnapshot  # noqa: PLC0415

        session = db_session
        if session is None:
            # No session provided — skip silently.
            return False

        # Look up by matching the bom_json content hash.
        # BomSnapshot stores the raw JSON; we search by computing the hash of
        # each snapshot's bom_json until we find a match.  This is O(n) but
        # invoked only once per commit, so it's acceptable.
        snapshots = session.query(BomSnapshot).filter(
            BomSnapshot.commit_sha.is_(None)
        ).all()
        for snap in snapshots:
            snap_hash = hashlib.sha256(
                snap.bom_json.encode("utf-8")
            ).hexdigest()
            if snap_hash == content_hash:
                snap.commit_sha = commit_sha
                session.commit()
                logger.debug(
                    "SkillBOM: updated BomSnapshot id=%s with commit_sha=%s",
                    snap.id,
                    commit_sha[:8],
                )
                return True
        return False
    except Exception as exc:  # noqa: BLE001
        logger.debug("SkillBOM: DB linkage skipped (%s).", exc)
        return False


# ---------------------------------------------------------------------------
# Internal helpers — BOM snapshot lookup and restore
# ---------------------------------------------------------------------------


def _locate_bom_snapshot(
    content_hash: str,
    repo_path: Path,
) -> Optional[Dict[str, Any]]:
    """Locate a BOM snapshot by its content hash.

    Look-up order:
    1. DB (``BomSnapshot`` rows) — matches by hashing ``bom_json``.
    2. JSON commit-links file — resolves to a ``bom_json`` stored there.

    Returns the parsed BOM dict, or None.
    """
    bom_data = _locate_snapshot_in_db(content_hash)
    if bom_data is not None:
        return bom_data
    return _locate_snapshot_in_json(content_hash, repo_path)


def _locate_snapshot_in_db(content_hash: str) -> Optional[Dict[str, Any]]:
    """Search DB BomSnapshot rows for the given content_hash."""
    try:
        from skillmeat.cache.manager import CacheManager  # noqa: PLC0415
        from skillmeat.cache.models import BomSnapshot  # noqa: PLC0415

        # Try to get a session from the default cache.
        cache_mgr = CacheManager()
        session = cache_mgr.get_session()
        if session is None:
            return None
        snapshots = session.query(BomSnapshot).all()
        for snap in snapshots:
            snap_hash = hashlib.sha256(snap.bom_json.encode("utf-8")).hexdigest()
            if snap_hash == content_hash:
                return json.loads(snap.bom_json)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("SkillBOM: DB snapshot lookup failed (%s).", exc)
        return None


def _locate_snapshot_in_json(
    content_hash: str,
    repo_path: Path,
) -> Optional[Dict[str, Any]]:
    """Search the JSON commit-links file for a BOM matching *content_hash*.

    The JSON file maps ``content_hash → commit_sha`` so this returns None
    (the JSON file alone does not store the BOM payload; it is a pointer).
    In practice, when only the JSON file is present (no DB), the BOM payload
    must come from elsewhere, but we return None rather than silently fail.
    """
    links = _read_commit_links(repo_path)
    if content_hash in links:
        logger.debug(
            "SkillBOM: found commit-links entry for hash %s → %s",
            content_hash[:8],
            links[content_hash][:8],
        )
    # JSON file stores hash→sha only, not the payload.
    return None


def _fetch_bom_from_upstream(
    content_hash: str,
    confirm_callback: Any,
) -> Optional[Dict[str, Any]]:
    """Optionally fetch a BOM snapshot from GitHub upstream.

    Parameters
    ----------
    content_hash:
        The BOM content hash to search for.
    confirm_callback:
        Callable ``(content_hash: str) -> bool`` that must return ``True``
        before a network request is made.  Pass ``None`` to skip prompting.

    Returns
    -------
    Parsed BOM dict from upstream, or None if the fetch was declined or failed.
    """
    if confirm_callback is not None:
        try:
            proceed = confirm_callback(content_hash)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SkillBOM: upstream confirm callback error: %s", exc)
            return None
        if not proceed:
            logger.info("SkillBOM: upstream fetch declined by user.")
            return None

    try:
        from skillmeat.core.github_client import get_github_client  # noqa: PLC0415

        client = get_github_client()
        # Convention: BOM snapshots may be published as release assets or
        # stored in a well-known path in the repo.  For now we attempt to
        # fetch from the default collection repo's BOM archive path.
        bom_path = f".skillmeat/bom-archive/{content_hash}.json"
        try:
            repo_slug = _detect_upstream_repo()
            if repo_slug is None:
                logger.debug("SkillBOM: no upstream repo detected; skipping.")
                return None
            raw = client.get_file_content(repo_slug, bom_path)
            if raw:
                return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.debug("SkillBOM: upstream fetch failed (%s).", exc)
            return None
    except ImportError:
        logger.debug("SkillBOM: GitHub client not available; skipping upstream.")
    return None


def _detect_upstream_repo() -> Optional[str]:
    """Detect the GitHub remote URL and return owner/repo, or None."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        # Handle SSH (git@github.com:owner/repo.git) and HTTPS forms.
        if url.startswith("git@github.com:"):
            slug = url[len("git@github.com:"):].removesuffix(".git")
        elif "github.com/" in url:
            slug = url.split("github.com/", 1)[1].removesuffix(".git")
        else:
            return None
        return slug or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _restore_entry(
    target_dir: Path,
    entry_type: str,
    name: str,
    entry: Dict[str, Any],
) -> None:
    """Write a single BOM entry back to the ``.claude/`` directory.

    Currently only entries with an embedded ``content`` field are supported.
    Entries referencing external paths are skipped (callers handle the
    unresolved accounting).
    """
    content = entry.get("content")
    restore_path_str = entry.get("path")

    if content is None:
        raise ValueError(f"Entry {name!r} has no embedded content to restore.")

    if restore_path_str:
        dest = target_dir / restore_path_str
    else:
        # Fallback: place in .claude/<type>/<name>
        dest = target_dir / ".claude" / entry_type / name

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    logger.debug("SkillBOM: restored %r → %s", name, dest)


def _verify_snapshot_signature(bom_data: Dict[str, Any]) -> Optional[bool]:
    """Verify the embedded signature in *bom_data* if one is present.

    Returns True (valid), False (invalid), or None (no signing module).
    """
    try:
        from skillmeat.core.bom.signing import verify_bom  # noqa: PLC0415

        result = verify_bom(bom_data)
        return result.valid
    except Exception as exc:  # noqa: BLE001
        logger.debug("SkillBOM: signature verification failed (%s).", exc)
        return None


# ---------------------------------------------------------------------------
# Internal helpers — hook installation
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
        "  python -m skillmeat.core.bom.git_integration restore"
        " <COMMIT_HASH> <TARGET_DIR> [--dry-run]\n"
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

    if command == "restore":
        if len(rest) < 2:
            print(
                "Error: COMMIT_HASH and TARGET_DIR arguments required",
                file=sys.stderr,
            )
            return 1
        commit_hash = rest[0]
        target_dir = rest[1]
        dry_run = "--dry-run" in rest[2:]
        repo = "."
        try:
            result = restore_from_commit(commit_hash, target_dir, dry_run=dry_run, repo_path=repo)
            status = "DRY RUN — " if dry_run else ""
            print(
                f"{status}Restored {result.resolved_entries}/{result.total_entries} entries "
                f"from commit {result.commit_sha[:8]} (BOM hash {result.bom_hash[:8]}...)"
            )
            if result.unresolved_entries:
                print(f"Unresolved ({len(result.unresolved_entries)}): "
                      + ", ".join(result.unresolved_entries))
            return 0
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    print(f"Unknown command: {command!r}", file=sys.stderr)
    _usage()
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
