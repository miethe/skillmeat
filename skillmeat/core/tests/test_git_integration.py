"""Tests for skillmeat.core.bom.git_integration.

Covers:
- install_hooks: creates expected files, sets executable bits
- install_hooks: backs up pre-existing non-managed hooks
- install_hooks: overwrites managed hooks silently (update path)
- install_hooks: raises FileNotFoundError when .git/ is absent
- compute_bom_hash: returns 64-char hex SHA-256
- prepare_commit_msg_hook: appends SkillBOM-Hash footer
- prepare_commit_msg_hook: idempotent (no double-append)
- prepare_commit_msg_hook: no-op when context.lock is absent
- prepare_commit_msg_hook: no-op when commit message file is absent
- prepare_commit_msg_hook: fail-open on unexpected error
- _main CLI: install command
- _main CLI: prepare-commit-msg command
- _main CLI: post-commit command
- _main CLI: unknown command returns 1
"""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from skillmeat.core.bom.git_integration import (
    _BOM_FOOTER_PREFIX,
    _MANAGED_MARKER,
    _append_bom_footer,
    _find_context_lock,
    _main,
    compute_bom_hash,
    install_hooks,
    post_commit_hook,
    prepare_commit_msg_hook,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Return a temp directory that looks like a Git repository root."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def context_lock(git_repo: Path) -> Path:
    """Write a minimal context.lock file and return its path."""
    lock = git_repo / "context.lock"
    lock.write_text('{"version": "1.0", "artifacts": []}', encoding="utf-8")
    return lock


@pytest.fixture()
def commit_msg_file(tmp_path: Path) -> Path:
    """Return a temp file pre-populated with a simple commit message."""
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text("feat: my awesome feature\n", encoding="utf-8")
    return msg


# ---------------------------------------------------------------------------
# install_hooks
# ---------------------------------------------------------------------------


class TestInstallHooks:
    def test_creates_prepare_commit_msg_hook(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        hook = git_repo / ".git" / "hooks" / "prepare-commit-msg"
        assert hook.is_file()

    def test_creates_post_commit_hook(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        hook = git_repo / ".git" / "hooks" / "post-commit"
        assert hook.is_file()

    def test_hooks_contain_managed_marker(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        for name in ("prepare-commit-msg", "post-commit"):
            text = (git_repo / ".git" / "hooks" / name).read_text()
            assert _MANAGED_MARKER in text

    def test_hooks_are_executable(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        for name in ("prepare-commit-msg", "post-commit"):
            hook = git_repo / ".git" / "hooks" / name
            mode = hook.stat().st_mode
            assert mode & stat.S_IXUSR, f"{name} is not user-executable"

    def test_backs_up_existing_non_managed_hook(
        self, git_repo: Path
    ) -> None:
        hook_path = git_repo / ".git" / "hooks" / "prepare-commit-msg"
        hook_path.write_text("#!/bin/sh\necho original\n")

        install_hooks(git_repo)

        backup = hook_path.with_suffix(".bak")
        assert backup.is_file(), "Backup file was not created"
        assert "original" in backup.read_text()

    def test_overwrites_managed_hook_without_backup(
        self, git_repo: Path
    ) -> None:
        """Re-installing should silently overwrite an existing managed hook."""
        install_hooks(git_repo)
        install_hooks(git_repo)  # second call

        backup = (
            git_repo / ".git" / "hooks" / "prepare-commit-msg"
        ).with_suffix(".bak")
        assert not backup.exists(), (
            "A .bak should NOT be created when overwriting our own hook"
        )

    def test_raises_when_no_git_dir(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match=".git"):
            install_hooks(tmp_path)

    def test_accepts_string_path(self, git_repo: Path) -> None:
        """install_hooks must accept plain strings, not just Path objects."""
        install_hooks(str(git_repo))
        assert (git_repo / ".git" / "hooks" / "post-commit").is_file()

    def test_creates_hooks_dir_if_missing(self, tmp_path: Path) -> None:
        """hooks/ dir may not exist in a brand-new repo."""
        (tmp_path / ".git").mkdir()
        install_hooks(tmp_path)
        assert (tmp_path / ".git" / "hooks").is_dir()


# ---------------------------------------------------------------------------
# compute_bom_hash
# ---------------------------------------------------------------------------


class TestComputeBomHash:
    def test_returns_64_char_hex(self, tmp_path: Path) -> None:
        lock = tmp_path / "context.lock"
        lock.write_bytes(b'{"version": "1"}')
        result = compute_bom_hash(lock)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_matches_expected_sha256(self, tmp_path: Path) -> None:
        content = b"hello world"
        lock = tmp_path / "context.lock"
        lock.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_bom_hash(lock) == expected

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            compute_bom_hash(tmp_path / "nonexistent.lock")

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        lock = tmp_path / "context.lock"
        lock.write_bytes(b"data")
        result = compute_bom_hash(str(lock))
        assert len(result) == 64


# ---------------------------------------------------------------------------
# prepare_commit_msg_hook / _append_bom_footer
# ---------------------------------------------------------------------------


class TestPrepareCommitMsgHook:
    def test_appends_footer_to_commit_message(
        self,
        git_repo: Path,
        context_lock: Path,
        commit_msg_file: Path,
    ) -> None:
        prepare_commit_msg_hook(str(commit_msg_file), git_repo)

        result = commit_msg_file.read_text()
        assert _BOM_FOOTER_PREFIX in result

    def test_footer_contains_64_char_hex(
        self,
        git_repo: Path,
        context_lock: Path,
        commit_msg_file: Path,
    ) -> None:
        prepare_commit_msg_hook(str(commit_msg_file), git_repo)

        text = commit_msg_file.read_text()
        # Extract the hash part after the prefix
        idx = text.index(_BOM_FOOTER_PREFIX)
        hash_part = text[idx + len(_BOM_FOOTER_PREFIX) : idx + len(_BOM_FOOTER_PREFIX) + 64]
        assert len(hash_part) == 64
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_idempotent_no_double_append(
        self,
        git_repo: Path,
        context_lock: Path,
        commit_msg_file: Path,
    ) -> None:
        prepare_commit_msg_hook(str(commit_msg_file), git_repo)
        prepare_commit_msg_hook(str(commit_msg_file), git_repo)

        text = commit_msg_file.read_text()
        assert text.count(_BOM_FOOTER_PREFIX) == 1

    def test_noop_when_no_context_lock(
        self,
        git_repo: Path,
        commit_msg_file: Path,
    ) -> None:
        """No context.lock → footer is NOT appended, message unchanged."""
        original = commit_msg_file.read_text()
        prepare_commit_msg_hook(str(commit_msg_file), git_repo)

        assert commit_msg_file.read_text() == original

    def test_noop_when_commit_msg_file_missing(
        self, git_repo: Path, context_lock: Path
    ) -> None:
        """Missing commit msg file → warn but do not raise."""
        prepare_commit_msg_hook("/nonexistent/COMMIT_EDITMSG", git_repo)
        # No exception raised — fail-open

    def test_fail_open_on_unexpected_error(
        self,
        git_repo: Path,
        context_lock: Path,
        commit_msg_file: Path,
    ) -> None:
        """An unexpected exception inside the hook must NOT propagate."""
        with patch(
            "skillmeat.core.bom.git_integration._append_bom_footer",
            side_effect=RuntimeError("boom"),
        ):
            # Should not raise
            prepare_commit_msg_hook(str(commit_msg_file), git_repo)

    def test_separator_blank_line_before_footer(
        self,
        git_repo: Path,
        context_lock: Path,
        commit_msg_file: Path,
    ) -> None:
        """Footer should be separated from the message by a blank line."""
        prepare_commit_msg_hook(str(commit_msg_file), git_repo)

        text = commit_msg_file.read_text()
        # The line before the footer line should be blank
        lines = text.splitlines()
        footer_idx = next(
            i for i, line in enumerate(lines) if _BOM_FOOTER_PREFIX in line
        )
        assert footer_idx >= 1
        assert lines[footer_idx - 1] == "", (
            "Expected a blank line before the SkillBOM footer"
        )

    def test_context_lock_discovery_claude_subdir(
        self,
        tmp_path: Path,
        commit_msg_file: Path,
    ) -> None:
        """context.lock inside .claude/ is discovered automatically."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        (tmp_path / ".claude").mkdir()
        lock = tmp_path / ".claude" / "context.lock"
        lock.write_text('{"v": 2}', encoding="utf-8")

        prepare_commit_msg_hook(str(commit_msg_file), tmp_path)

        assert _BOM_FOOTER_PREFIX in commit_msg_file.read_text()

    def test_context_lock_discovery_skillmeat_subdir(
        self,
        tmp_path: Path,
        commit_msg_file: Path,
    ) -> None:
        """context.lock inside .skillmeat/ is discovered automatically."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        (tmp_path / ".skillmeat").mkdir()
        lock = tmp_path / ".skillmeat" / "context.lock"
        lock.write_text('{"v": 3}', encoding="utf-8")

        prepare_commit_msg_hook(str(commit_msg_file), tmp_path)

        assert _BOM_FOOTER_PREFIX in commit_msg_file.read_text()


# ---------------------------------------------------------------------------
# _find_context_lock
# ---------------------------------------------------------------------------


class TestFindContextLock:
    def test_finds_root_level_lock(self, tmp_path: Path) -> None:
        lock = tmp_path / "context.lock"
        lock.write_text("{}")
        assert _find_context_lock(tmp_path) == lock

    def test_finds_claude_subdir_lock(self, tmp_path: Path) -> None:
        (tmp_path / ".claude").mkdir()
        lock = tmp_path / ".claude" / "context.lock"
        lock.write_text("{}")
        assert _find_context_lock(tmp_path) == lock

    def test_returns_none_when_absent(self, tmp_path: Path) -> None:
        assert _find_context_lock(tmp_path) is None

    def test_root_takes_priority_over_subdir(self, tmp_path: Path) -> None:
        root_lock = tmp_path / "context.lock"
        root_lock.write_text("{}")
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "context.lock").write_text("{}")
        assert _find_context_lock(tmp_path) == root_lock


# ---------------------------------------------------------------------------
# post_commit_hook (smoke test — currently a no-op)
# ---------------------------------------------------------------------------


class TestPostCommitHook:
    def test_does_not_raise(self, git_repo: Path) -> None:
        post_commit_hook(git_repo)  # must not raise

    def test_fail_open(self) -> None:
        """Even with a bad path it must not raise."""
        post_commit_hook("/totally/nonexistent/path")


# ---------------------------------------------------------------------------
# _main CLI entry-point
# ---------------------------------------------------------------------------


class TestMainCli:
    def test_install_command(self, git_repo: Path) -> None:
        rc = _main(["install", str(git_repo)])
        assert rc == 0
        assert (git_repo / ".git" / "hooks" / "post-commit").is_file()

    def test_install_command_missing_git(self, tmp_path: Path) -> None:
        rc = _main(["install", str(tmp_path)])
        assert rc == 1

    def test_prepare_commit_msg_command(
        self,
        git_repo: Path,
        context_lock: Path,
        commit_msg_file: Path,
    ) -> None:
        rc = _main(["prepare-commit-msg", str(commit_msg_file), str(git_repo)])
        assert rc == 0
        assert _BOM_FOOTER_PREFIX in commit_msg_file.read_text()

    def test_prepare_commit_msg_requires_file_arg(self) -> None:
        rc = _main(["prepare-commit-msg"])
        assert rc == 1

    def test_post_commit_command(self, git_repo: Path) -> None:
        rc = _main(["post-commit", str(git_repo)])
        assert rc == 0

    def test_unknown_command_returns_1(self) -> None:
        rc = _main(["bogus-command"])
        assert rc == 1

    def test_help_flag_returns_0(self) -> None:
        rc = _main(["--help"])
        assert rc == 0

    def test_no_args_returns_1(self) -> None:
        rc = _main([])
        assert rc == 1
