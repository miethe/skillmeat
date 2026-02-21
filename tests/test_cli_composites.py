"""CLI integration tests for composite artifact commands.

Tests cover:
- skillmeat list — composite artifacts appear with 'plugin' label
- skillmeat list --type composite/plugin — filters to composites only
- skillmeat composite create — happy path, error cases
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


@pytest.fixture
def cli_runner():
    """Provide Click CLI test runner."""
    return CliRunner()


# ===========================================================================
# skillmeat list — composite visibility
# ===========================================================================


class TestListIncludesComposites:
    """Test that 'skillmeat list' displays composite artifacts with 'plugin' label."""

    def test_list_shows_composite_with_plugin_label(self, cli_runner):
        """Composite artifacts appear in list output with type label 'plugin'."""
        composite_rows = [
            {
                "id": "composite:my-plugin",
                "display_name": "My Plugin",
                "description": "A test plugin",
            }
        ]

        with (
            patch(
                "skillmeat.cli.ArtifactManager.list_artifacts",
                return_value=[],
            ),
            patch(
                "skillmeat.cache.composite_repository.CompositeMembershipRepository.list_composites",
                return_value=composite_rows,
            ),
            patch(
                "skillmeat.cli.CollectionManager.get_active_collection_name",
                return_value="default",
            ),
        ):
            result = cli_runner.invoke(main, ["list"])

        assert result.exit_code == 0
        assert "My Plugin" in result.output
        assert "plugin" in result.output

    def test_list_shows_composite_id_name_when_no_display_name(self, cli_runner):
        """Falls back to the name part of the composite ID when display_name is absent."""
        composite_rows = [
            {
                "id": "composite:bare-plugin",
                "display_name": None,
                "description": "",
            }
        ]

        with (
            patch(
                "skillmeat.cli.ArtifactManager.list_artifacts",
                return_value=[],
            ),
            patch(
                "skillmeat.cache.composite_repository.CompositeMembershipRepository.list_composites",
                return_value=composite_rows,
            ),
            patch(
                "skillmeat.cli.CollectionManager.get_active_collection_name",
                return_value="default",
            ),
        ):
            result = cli_runner.invoke(main, ["list"])

        assert result.exit_code == 0
        assert "bare-plugin" in result.output

    def test_list_no_cache_skips_composites(self, cli_runner):
        """With --no-cache, composite fetch is skipped; no error is raised."""
        with patch(
            "skillmeat.cli.ArtifactManager.list_artifacts",
            return_value=[],
        ):
            result = cli_runner.invoke(main, ["list", "--no-cache"])

        # Command should succeed even with no artifacts
        assert result.exit_code == 0

    def test_list_composite_fetch_failure_is_graceful(self, cli_runner):
        """If the composite repository raises, list still succeeds (logs debug)."""
        with (
            patch(
                "skillmeat.cli.ArtifactManager.list_artifacts",
                return_value=[],
            ),
            patch(
                "skillmeat.cache.composite_repository.CompositeMembershipRepository.list_composites",
                side_effect=Exception("DB unavailable"),
            ),
            patch(
                "skillmeat.cli.CollectionManager.get_active_collection_name",
                return_value="default",
            ),
        ):
            result = cli_runner.invoke(main, ["list"])

        # Should not crash — composites are silently skipped on error
        assert result.exit_code == 0


# ===========================================================================
# skillmeat list --type composite/plugin — filtering
# ===========================================================================


class TestListTypeCompositeFilter:
    """Test that --type composite and --type plugin filter to composites only."""

    def _make_composite_row(self, name: str, description: str = "") -> dict:
        return {
            "id": f"composite:{name}",
            "display_name": name.replace("-", " ").title(),
            "description": description,
        }

    @pytest.mark.parametrize("type_flag", ["composite", "plugin"])
    def test_list_type_filter_shows_only_composites(self, cli_runner, type_flag):
        """--type composite and --type plugin both filter to composite artifacts only."""
        composite_rows = [
            self._make_composite_row("canvas-suite"),
            self._make_composite_row("dev-stack"),
        ]

        with (
            patch(
                "skillmeat.cache.composite_repository.CompositeMembershipRepository.list_composites",
                return_value=composite_rows,
            ),
            patch(
                "skillmeat.cli.CollectionManager.get_active_collection_name",
                return_value="default",
            ),
        ):
            result = cli_runner.invoke(main, ["list", "--type", type_flag])

        assert result.exit_code == 0
        assert "Canvas Suite" in result.output
        assert "Dev Stack" in result.output
        # Type label for composite rows is always 'plugin'
        assert "plugin" in result.output

    @pytest.mark.parametrize("type_flag", ["composite", "plugin"])
    def test_list_type_filter_exits_zero_when_no_composites(
        self, cli_runner, type_flag
    ):
        """No composites found with type filter — exits 0 with empty message."""
        with (
            patch(
                "skillmeat.cache.composite_repository.CompositeMembershipRepository.list_composites",
                return_value=[],
            ),
            patch(
                "skillmeat.cli.CollectionManager.get_active_collection_name",
                return_value="default",
            ),
        ):
            result = cli_runner.invoke(main, ["list", "--type", type_flag])

        assert result.exit_code == 0
        assert "No artifacts found" in result.output

    def test_list_type_skill_excludes_composites(self, cli_runner):
        """--type skill must not query or display composite rows."""
        mock_artifact = MagicMock()
        mock_artifact.name = "my-skill"
        mock_artifact.type = MagicMock()
        mock_artifact.type.value = "skill"
        mock_artifact.origin = "user/repo"
        mock_artifact.tags = []

        with (
            patch(
                "skillmeat.cli.ArtifactManager.list_artifacts",
                return_value=[mock_artifact],
            ),
            patch(
                "skillmeat.cache.composite_repository.CompositeMembershipRepository.list_composites"
            ) as mock_comp,
        ):
            result = cli_runner.invoke(main, ["list", "--type", "skill"])

        assert result.exit_code == 0
        # Composite repo must NOT be called when filtering for non-composite types
        mock_comp.assert_not_called()


# ===========================================================================
# skillmeat composite create — happy path
# ===========================================================================


class TestCompositeCreate:
    """Test 'skillmeat composite create' success scenarios."""

    def _make_service_record(self, name: str, composite_type: str = "plugin") -> dict:
        return {
            "id": f"composite:{name}",
            "composite_type": composite_type,
            "display_name": name,
            "description": None,
            "collection_id": "default",
            "members": [],
        }

    def test_create_composite_no_members_exits_zero(self, cli_runner):
        """Creating a composite with no members succeeds with exit code 0."""
        record = self._make_service_record("my-plugin")

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            return_value=record,
        ):
            result = cli_runner.invoke(main, ["composite", "create", "my-plugin"])

        assert result.exit_code == 0
        assert "composite:my-plugin" in result.output

    def test_create_composite_with_valid_members_exits_zero(self, cli_runner):
        """Creating a composite with valid type:name members succeeds."""
        record = self._make_service_record("my-plugin")

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            return_value=record,
        ):
            result = cli_runner.invoke(
                main,
                [
                    "composite",
                    "create",
                    "my-plugin",
                    "skill:canvas",
                    "command:git-commit",
                ],
            )

        assert result.exit_code == 0
        assert "Composite created successfully" in result.output
        assert "skill:canvas" in result.output
        assert "command:git-commit" in result.output

    def test_create_composite_with_type_stack(self, cli_runner):
        """--type stack is passed through to the service correctly."""
        record = self._make_service_record("my-stack", composite_type="stack")

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            return_value=record,
        ) as mock_create:
            result = cli_runner.invoke(
                main,
                ["composite", "create", "my-stack", "--type", "stack"],
            )

        assert result.exit_code == 0
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("composite_type") == "stack"

    def test_create_composite_with_display_name_and_description(self, cli_runner):
        """--display-name and --description options are forwarded to the service."""
        record = self._make_service_record("my-plugin")

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            return_value=record,
        ) as mock_create:
            result = cli_runner.invoke(
                main,
                [
                    "composite",
                    "create",
                    "my-plugin",
                    "--display-name",
                    "My Awesome Plugin",
                    "--description",
                    "Does great things",
                ],
            )

        assert result.exit_code == 0
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("display_name") == "My Awesome Plugin"
        assert call_kwargs.get("description") == "Does great things"

    def test_create_composite_with_collection_option(self, cli_runner):
        """--collection option is forwarded to the service."""
        record = self._make_service_record("my-plugin")
        record["collection_id"] = "work"

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            return_value=record,
        ) as mock_create:
            result = cli_runner.invoke(
                main,
                ["composite", "create", "my-plugin", "--collection", "work"],
            )

        assert result.exit_code == 0
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("collection_id") == "work"

    def test_create_composite_no_members_service_receives_none(self, cli_runner):
        """When no members are supplied, initial_members is None in the service call."""
        record = self._make_service_record("empty-plugin")

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            return_value=record,
        ) as mock_create:
            result = cli_runner.invoke(
                main, ["composite", "create", "empty-plugin"]
            )

        assert result.exit_code == 0
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("initial_members") is None


# ===========================================================================
# skillmeat composite create — error cases
# ===========================================================================


class TestCompositeCreateErrors:
    """Test 'skillmeat composite create' error / validation scenarios."""

    def test_invalid_member_format_exits_one(self, cli_runner):
        """Members without 'type:name' format cause exit code 1."""
        result = cli_runner.invoke(
            main,
            ["composite", "create", "my-plugin", "invalid-member"],
        )

        assert result.exit_code == 1
        assert "Invalid member format" in result.output or "invalid" in result.output.lower()

    def test_multiple_invalid_members_all_reported(self, cli_runner):
        """All invalid members are reported in the error output."""
        result = cli_runner.invoke(
            main,
            [
                "composite",
                "create",
                "my-plugin",
                "no-colon",
                "also-bad",
                "skill:valid",  # This one is fine
            ],
        )

        assert result.exit_code == 1
        # Both bad members should appear in output
        assert "no-colon" in result.output
        assert "also-bad" in result.output

    def test_artifact_not_found_exits_one(self, cli_runner):
        """ArtifactNotFoundError from the service produces exit code 1."""
        from skillmeat.core.services.composite_service import ArtifactNotFoundError

        error = ArtifactNotFoundError("skill:nonexistent")

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            side_effect=error,
        ):
            result = cli_runner.invoke(
                main,
                ["composite", "create", "my-plugin", "skill:nonexistent"],
            )

        assert result.exit_code == 1
        assert "skill:nonexistent" in result.output

    def test_artifact_not_found_shows_hint(self, cli_runner):
        """ArtifactNotFoundError output includes an actionable hint to import first."""
        from skillmeat.core.services.composite_service import ArtifactNotFoundError

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            side_effect=ArtifactNotFoundError("skill:missing"),
        ):
            result = cli_runner.invoke(
                main,
                ["composite", "create", "my-plugin", "skill:missing"],
            )

        assert result.exit_code == 1
        # The hint about importing first must be present
        assert "import" in result.output.lower() or "collection" in result.output.lower()

    def test_duplicate_name_exits_one(self, cli_runner):
        """ConstraintError (duplicate name) produces exit code 1 with error message."""
        from skillmeat.cache.repositories import ConstraintError

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            side_effect=ConstraintError("UNIQUE constraint failed"),
        ):
            result = cli_runner.invoke(
                main, ["composite", "create", "existing-plugin"]
            )

        assert result.exit_code == 1
        assert "existing-plugin" in result.output

    def test_duplicate_name_error_message_is_descriptive(self, cli_runner):
        """Duplicate name error output clearly identifies the conflicting name."""
        from skillmeat.cache.repositories import ConstraintError

        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            side_effect=ConstraintError("UNIQUE constraint failed"),
        ):
            result = cli_runner.invoke(
                main, ["composite", "create", "duplicate-plugin", "--collection", "work"]
            )

        assert result.exit_code == 1
        # Both the name and the collection must be mentioned
        assert "duplicate-plugin" in result.output
        assert "work" in result.output

    def test_value_error_exits_one(self, cli_runner):
        """ValueError from the service produces exit code 1."""
        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            side_effect=ValueError("name cannot be empty"),
        ):
            result = cli_runner.invoke(
                main, ["composite", "create", "bad-name"]
            )

        assert result.exit_code == 1

    def test_unexpected_exception_exits_one(self, cli_runner):
        """Unexpected exceptions from the service produce exit code 1."""
        with patch(
            "skillmeat.core.services.composite_service.CompositeService.create_composite",
            side_effect=RuntimeError("unexpected DB failure"),
        ):
            result = cli_runner.invoke(
                main, ["composite", "create", "my-plugin"]
            )

        assert result.exit_code == 1
