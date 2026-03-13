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
- post_commit_hook: extracts SHA and links BOM
- link_bom_to_commit: writes JSON fallback
- restore_from_commit: extracts footer from commit message
- restore_from_commit: reports unresolved entries
- restore_from_commit: dry-run mode does not modify filesystem
- _main CLI: install command
- _main CLI: prepare-commit-msg command
- _main CLI: post-commit command
- _main CLI: restore command
- _main CLI: unknown command returns 1
"""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.bom.git_integration import (
    _BOM_FOOTER_PREFIX,
    _MANAGED_MARKER,
    _append_bom_footer,
    _extract_bom_hash,
    _find_context_lock,
    _main,
    _read_commit_links,
    _write_commit_link_json,
    compute_bom_hash,
    install_hooks,
    link_bom_to_commit,
    post_commit_hook,
    prepare_commit_msg_hook,
    restore_from_commit,
    RestoreResult,
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


# ---------------------------------------------------------------------------
# _extract_bom_hash
# ---------------------------------------------------------------------------


class TestExtractBomHash:
    def test_extracts_hash_from_footer(self) -> None:
        msg = "feat: thing\n\nSkillBOM-Hash: sha256:abc123def456\n"
        result = _extract_bom_hash(msg)
        assert result == "abc123def456"

    def test_returns_none_when_absent(self) -> None:
        assert _extract_bom_hash("no footer here") is None

    def test_returns_none_for_empty_message(self) -> None:
        assert _extract_bom_hash("") is None

    def test_handles_real_64_char_hash(self) -> None:
        hex64 = "a" * 64
        msg = f"fix: thing\n\n{_BOM_FOOTER_PREFIX}{hex64}\n"
        assert _extract_bom_hash(msg) == hex64

    def test_strips_whitespace_around_footer_line(self) -> None:
        hex64 = "b" * 64
        msg = f"msg\n\n  {_BOM_FOOTER_PREFIX}{hex64}  \n"
        result = _extract_bom_hash(msg)
        assert result == hex64


# ---------------------------------------------------------------------------
# link_bom_to_commit — JSON fallback
# ---------------------------------------------------------------------------


class TestLinkBomToCommit:
    def test_writes_json_fallback(self, tmp_path: Path) -> None:
        content_hash = "a" * 64
        commit_sha = "b" * 40
        link_bom_to_commit(content_hash, commit_sha, repo_path=tmp_path)

        links = _read_commit_links(tmp_path)
        assert links.get(content_hash) == commit_sha

    def test_overwrites_existing_entry(self, tmp_path: Path) -> None:
        content_hash = "c" * 64
        old_sha = "0" * 40
        new_sha = "1" * 40
        link_bom_to_commit(content_hash, old_sha, repo_path=tmp_path)
        link_bom_to_commit(content_hash, new_sha, repo_path=tmp_path)

        links = _read_commit_links(tmp_path)
        assert links[content_hash] == new_sha

    def test_preserves_other_entries(self, tmp_path: Path) -> None:
        hash1, sha1 = "a" * 64, "a" * 40
        hash2, sha2 = "b" * 64, "b" * 40
        link_bom_to_commit(hash1, sha1, repo_path=tmp_path)
        link_bom_to_commit(hash2, sha2, repo_path=tmp_path)

        links = _read_commit_links(tmp_path)
        assert links[hash1] == sha1
        assert links[hash2] == sha2

    def test_returns_true_even_when_db_unavailable(self, tmp_path: Path) -> None:
        result = link_bom_to_commit("x" * 64, "y" * 40, repo_path=tmp_path)
        assert result is True


# ---------------------------------------------------------------------------
# _write_commit_link_json / _read_commit_links helpers
# ---------------------------------------------------------------------------


class TestCommitLinkJson:
    def test_round_trip(self, tmp_path: Path) -> None:
        _write_commit_link_json(tmp_path, "hash1", "sha1")
        _write_commit_link_json(tmp_path, "hash2", "sha2")
        data = _read_commit_links(tmp_path)
        assert data == {"hash1": "sha1", "hash2": "sha2"}

    def test_read_missing_file_returns_empty(self, tmp_path: Path) -> None:
        data = _read_commit_links(tmp_path)
        assert data == {}

    def test_read_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        links_file = tmp_path / ".skillmeat" / "bom-commit-links.json"
        links_file.parent.mkdir(parents=True, exist_ok=True)
        links_file.write_text("not valid json", encoding="utf-8")
        assert _read_commit_links(tmp_path) == {}

    def test_creates_skillmeat_subdir(self, tmp_path: Path) -> None:
        _write_commit_link_json(tmp_path, "k", "v")
        assert (tmp_path / ".skillmeat").is_dir()


# ---------------------------------------------------------------------------
# post_commit_hook — with git subprocess mocked
# ---------------------------------------------------------------------------


class TestPostCommitHookWithGit:
    def _make_commit_msg(self, bom_hash: str) -> str:
        return f"feat: thing\n\n{_BOM_FOOTER_PREFIX}{bom_hash}\n"

    def test_extracts_sha_and_writes_json_link(self, tmp_path: Path) -> None:
        commit_sha = "c" * 40
        bom_hash = hashlib.sha256(b"test-bom").hexdigest()
        commit_msg = self._make_commit_msg(bom_hash)

        with (
            patch(
                "skillmeat.core.bom.git_integration._git_rev_parse_head",
                return_value=commit_sha,
            ),
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value=commit_msg,
            ),
        ):
            post_commit_hook(tmp_path)

        links = _read_commit_links(tmp_path)
        assert links.get(bom_hash) == commit_sha

    def test_noop_when_no_bom_footer(self, tmp_path: Path) -> None:
        with (
            patch(
                "skillmeat.core.bom.git_integration._git_rev_parse_head",
                return_value="d" * 40,
            ),
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value="feat: no bom footer\n",
            ),
        ):
            post_commit_hook(tmp_path)

        # No links file written (or empty if it was already there).
        assert _read_commit_links(tmp_path) == {}

    def test_noop_when_head_sha_unavailable(self, tmp_path: Path) -> None:
        with patch(
            "skillmeat.core.bom.git_integration._git_rev_parse_head",
            return_value=None,
        ):
            # Must not raise.
            post_commit_hook(tmp_path)

    def test_fail_open_on_exception(self, tmp_path: Path) -> None:
        with patch(
            "skillmeat.core.bom.git_integration._git_rev_parse_head",
            side_effect=RuntimeError("boom"),
        ):
            post_commit_hook(tmp_path)  # must not raise


# ---------------------------------------------------------------------------
# restore_from_commit
# ---------------------------------------------------------------------------


_FAKE_BOM = {
    "schema_version": "1.0.0",
    "generated_at": "2026-01-01T00:00:00+00:00",
    "project_path": None,
    "artifact_count": 2,
    "artifacts": [
        {
            "type": "skill",
            "name": "canvas",
            "content": "# canvas skill",
            "path": ".claude/skills/canvas/SKILL.md",
        },
        {
            "type": "command",
            "name": "deploy",
            "content": "# deploy cmd",
            "path": ".claude/commands/deploy.md",
        },
    ],
    "metadata": {"generator": "skillmeat-bom", "elapsed_ms": 1.0},
}

_FAKE_BOM_JSON = json.dumps(_FAKE_BOM, sort_keys=True, separators=(",", ":"))
_FAKE_BOM_HASH = hashlib.sha256(_FAKE_BOM_JSON.encode("utf-8")).hexdigest()
_FAKE_COMMIT_MSG = f"feat: something\n\n{_BOM_FOOTER_PREFIX}{_FAKE_BOM_HASH}\n"


class TestRestoreFromCommit:
    def test_raises_when_no_bom_footer(self, tmp_path: Path) -> None:
        with patch(
            "skillmeat.core.bom.git_integration._git_log_message",
            return_value="feat: no bom here\n",
        ):
            with pytest.raises(ValueError, match="SkillBOM-Hash"):
                restore_from_commit("abc123", tmp_path, repo_path=tmp_path)

    def test_raises_when_commit_not_found(self, tmp_path: Path) -> None:
        with patch(
            "skillmeat.core.bom.git_integration._git_log_message",
            return_value=None,
        ):
            with pytest.raises(ValueError, match="commit message"):
                restore_from_commit("abc123", tmp_path, repo_path=tmp_path)

    def test_returns_empty_result_when_snapshot_not_found(
        self, tmp_path: Path
    ) -> None:
        with (
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value=_FAKE_COMMIT_MSG,
            ),
            patch(
                "skillmeat.core.bom.git_integration._locate_bom_snapshot",
                return_value=None,
            ),
            patch(
                "skillmeat.core.bom.git_integration._fetch_bom_from_upstream",
                return_value=None,
            ),
        ):
            result = restore_from_commit("abc123", tmp_path, repo_path=tmp_path)

        assert isinstance(result, RestoreResult)
        assert result.total_entries == 0
        assert result.resolved_entries == 0

    def test_restores_entries_with_content(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()

        with (
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value=_FAKE_COMMIT_MSG,
            ),
            patch(
                "skillmeat.core.bom.git_integration._locate_bom_snapshot",
                return_value=_FAKE_BOM,
            ),
        ):
            result = restore_from_commit("abc123", target, repo_path=tmp_path)

        assert result.resolved_entries == 2
        assert result.unresolved_entries == []
        # Check that files were written.
        assert (target / ".claude" / "skills" / "canvas" / "SKILL.md").is_file()
        assert (target / ".claude" / "commands" / "deploy.md").is_file()

    def test_reports_unresolved_entries(self, tmp_path: Path) -> None:
        bom_with_no_content = {
            **_FAKE_BOM,
            "artifacts": [
                {"type": "skill", "name": "orphan"},  # no content, no path
            ],
            "artifact_count": 1,
        }

        with (
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value=_FAKE_COMMIT_MSG,
            ),
            patch(
                "skillmeat.core.bom.git_integration._locate_bom_snapshot",
                return_value=bom_with_no_content,
            ),
        ):
            result = restore_from_commit("abc123", tmp_path, repo_path=tmp_path)

        assert result.total_entries == 1
        assert result.resolved_entries == 0
        assert "orphan" in result.unresolved_entries

    def test_dry_run_does_not_write_files(self, tmp_path: Path) -> None:
        target = tmp_path / "dry-target"
        target.mkdir()

        with (
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value=_FAKE_COMMIT_MSG,
            ),
            patch(
                "skillmeat.core.bom.git_integration._locate_bom_snapshot",
                return_value=_FAKE_BOM,
            ),
        ):
            result = restore_from_commit(
                "abc123", target, dry_run=True, repo_path=tmp_path
            )

        assert result.dry_run is True
        assert result.resolved_entries == 2
        # No actual files written.
        assert not (target / ".claude").exists()

    def test_bom_hash_in_result(self, tmp_path: Path) -> None:
        with (
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value=_FAKE_COMMIT_MSG,
            ),
            patch(
                "skillmeat.core.bom.git_integration._locate_bom_snapshot",
                return_value=None,
            ),
            patch(
                "skillmeat.core.bom.git_integration._fetch_bom_from_upstream",
                return_value=None,
            ),
        ):
            result = restore_from_commit("abc123", tmp_path, repo_path=tmp_path)

        assert result.bom_hash == _FAKE_BOM_HASH

    def test_upstream_confirm_callback_decline(self, tmp_path: Path) -> None:
        """Declined upstream fetch returns empty result without network."""
        declined = False

        def _decline(hash_: str) -> bool:
            nonlocal declined
            declined = True
            return False

        with (
            patch(
                "skillmeat.core.bom.git_integration._git_log_message",
                return_value=_FAKE_COMMIT_MSG,
            ),
            patch(
                "skillmeat.core.bom.git_integration._locate_bom_snapshot",
                return_value=None,
            ),
        ):
            result = restore_from_commit(
                "abc123",
                tmp_path,
                repo_path=tmp_path,
                upstream_confirm_callback=_decline,
            )

        assert declined is True
        assert result.total_entries == 0


# ---------------------------------------------------------------------------
# _main CLI — restore command
# ---------------------------------------------------------------------------


class TestMainCliRestore:
    def test_restore_requires_two_args(self) -> None:
        rc = _main(["restore", "abc123"])
        assert rc == 1

    def test_restore_raises_value_error_returns_1(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            side_effect=ValueError("no footer"),
        ):
            rc = _main(["restore", "abc123", str(tmp_path)])
        assert rc == 1

    def test_restore_success_returns_0(self, tmp_path: Path) -> None:
        fake_result = RestoreResult(
            commit_sha="abc123" + "0" * 34,
            bom_hash=_FAKE_BOM_HASH,
            total_entries=2,
            resolved_entries=2,
            dry_run=False,
            signature_valid=None,
        )
        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            return_value=fake_result,
        ):
            rc = _main(["restore", "abc123", str(tmp_path)])
        assert rc == 0

    def test_restore_dry_run_flag(self, tmp_path: Path) -> None:
        captured: dict = {}

        def _fake_restore(commit_hash, target_dir, dry_run=False, **kw):
            captured["dry_run"] = dry_run
            return RestoreResult(
                commit_sha=commit_hash,
                bom_hash="x" * 64,
                total_entries=0,
                resolved_entries=0,
                dry_run=dry_run,
                signature_valid=None,
            )

        with patch(
            "skillmeat.core.bom.git_integration.restore_from_commit",
            side_effect=_fake_restore,
        ):
            _main(["restore", "abc123", str(tmp_path), "--dry-run"])

        assert captured.get("dry_run") is True
