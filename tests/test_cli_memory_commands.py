"""CLI tests for memory command parity and share-scope options."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from skillmeat.cli import main


def _mock_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


def test_memory_extract_run_calls_apply_endpoint():
    runner = CliRunner()

    with runner.isolated_filesystem():
        run_log = Path("run.log")
        run_log.write_text("Decision: Use retries for flaky APIs.", encoding="utf-8")

        with patch(
            "skillmeat.cli._memory_request",
            return_value=_mock_response({"created": [], "skipped_duplicates": [], "preview_total": 0}),
        ) as mock_request:
            result = runner.invoke(
                main,
                [
                    "memory",
                    "extract",
                    "run",
                    "--project",
                    "proj-1",
                    "--run-log",
                    str(run_log),
                    "--profile",
                    "aggressive",
                ],
            )

    assert result.exit_code == 0
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args.args[0] == "POST"
    assert call_args.args[1] == "/memory-items/extract/apply"
    assert call_args.kwargs["params"]["project_id"] == "proj-1"
    assert call_args.kwargs["json"]["profile"] == "aggressive"


def test_memory_item_create_includes_share_scope():
    runner = CliRunner()

    with patch(
        "skillmeat.cli._memory_request",
        return_value=_mock_response({"id": "mem-1"}),
    ) as mock_request:
        result = runner.invoke(
            main,
            [
                "memory",
                "item",
                "create",
                "--project",
                "proj-1",
                "--type",
                "decision",
                "--content",
                "Use retries.",
                "--share-scope",
                "global_candidate",
            ],
        )

    assert result.exit_code == 0
    assert mock_request.call_args.kwargs["json"]["share_scope"] == "global_candidate"


def test_memory_item_list_forwards_share_scope_filter():
    runner = CliRunner()

    with patch(
        "skillmeat.cli._memory_request",
        return_value=_mock_response({"items": [], "has_more": False, "next_cursor": None}),
    ) as mock_request:
        result = runner.invoke(
            main,
            [
                "memory",
                "item",
                "list",
                "--project",
                "proj-1",
                "--share-scope",
                "private",
            ],
        )

    assert result.exit_code == 0
    assert mock_request.call_args.kwargs["params"]["share_scope"] == "private"
