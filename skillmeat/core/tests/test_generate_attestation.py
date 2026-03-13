"""Tests for skillmeat.core.tools.generate_attestation.

Covers:
- generate_attestation: returns a valid dict with 'bom', 'signature', 'hash'
- generate_attestation: handles missing/unavailable BomGenerator gracefully
- generate_attestation: artifact_filters limit the returned artifacts
- generate_attestation: include_memory_items=False removes memory_item adapter
- generate_attestation: signature_key_id triggers signing path
- generate_attestation: hash is SHA-256 of canonical BOM JSON
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.tools.generate_attestation import generate_attestation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_BOM: Dict[str, Any] = {
    "schema_version": "1.0.0",
    "generated_at": "2026-01-01T00:00:00+00:00",
    "project_path": None,
    "artifact_count": 3,
    "artifacts": [
        {"type": "skill", "name": "canvas", "content": "# canvas"},
        {"type": "command", "name": "deploy", "content": "# deploy"},
        {"type": "memory_item", "name": "mem-01", "content": "data"},
    ],
    "metadata": {"generator": "skillmeat-bom", "elapsed_ms": 1.0},
}


def _canonical_hash(bom: Dict[str, Any]) -> str:
    canonical = json.dumps(bom, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Basic return structure
# ---------------------------------------------------------------------------


class TestGenerateAttestationReturnStructure:
    def test_returns_required_keys(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation()

        assert "bom" in result
        assert "signature" in result
        assert "hash" in result
        assert "error" in result

    def test_bom_key_is_dict(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation()

        assert isinstance(result["bom"], dict)

    def test_hash_is_sha256_hex(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation()

        bom_hash = result["hash"]
        assert len(bom_hash) == 64
        assert all(c in "0123456789abcdef" for c in bom_hash)

    def test_hash_matches_canonical_json(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation()

        expected = _canonical_hash(_FAKE_BOM)
        assert result["hash"] == expected

    def test_no_signature_by_default(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            with patch(
                "skillmeat.core.tools.generate_attestation._signing_available",
                return_value=False,
            ):
                result = generate_attestation()

        assert result["signature"] is None

    def test_error_is_none_on_success(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            with patch(
                "skillmeat.core.tools.generate_attestation._signing_available",
                return_value=False,
            ):
                result = generate_attestation()

        assert result["error"] is None


# ---------------------------------------------------------------------------
# Graceful degradation when BomGenerator is unavailable
# ---------------------------------------------------------------------------


class TestGenerateAttestationDegradation:
    def test_generator_import_error_returns_empty_bom(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            side_effect=RuntimeError("DB unavailable"),
        ):
            result = generate_attestation()

        assert result["bom"]["artifact_count"] == 0
        assert result["bom"]["artifacts"] == []
        assert result["error"] is not None
        assert "DB unavailable" in result["error"]

    def test_error_key_populated_on_failure(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            side_effect=RuntimeError("cache offline"),
        ):
            result = generate_attestation()

        assert result["error"] is not None

    def test_hash_still_computed_on_bom_fallback(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            side_effect=RuntimeError("fail"),
        ):
            result = generate_attestation()

        # Hash should be a non-empty hex string even for the empty BOM.
        assert len(result["hash"]) == 64


# ---------------------------------------------------------------------------
# artifact_filters
# ---------------------------------------------------------------------------


class TestGenerateAttestationFilters:
    def test_filter_by_name(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation(artifact_filters=["canvas"])

        kept = result["bom"]["artifacts"]
        assert len(kept) == 1
        assert kept[0]["name"] == "canvas"

    def test_filter_by_type_colon_name(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation(artifact_filters=["command:deploy"])

        kept = result["bom"]["artifacts"]
        assert len(kept) == 1
        assert kept[0]["name"] == "deploy"

    def test_empty_filter_returns_all(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation(artifact_filters=[])

        # Empty filter list → no filtering applied.
        assert len(result["bom"]["artifacts"]) == 3

    def test_none_filter_returns_all(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation(artifact_filters=None)

        assert len(result["bom"]["artifacts"]) == 3

    def test_no_matching_filter_returns_empty(self) -> None:
        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            return_value=_FAKE_BOM,
        ):
            result = generate_attestation(artifact_filters=["nonexistent"])

        assert result["bom"]["artifacts"] == []
        assert result["bom"]["artifact_count"] == 0


# ---------------------------------------------------------------------------
# include_memory_items
# ---------------------------------------------------------------------------


class TestIncludeMemoryItems:
    def test_memory_items_excluded_by_default(self) -> None:
        """_generate_bom is called with include_memory_items=False by default."""
        captured: dict = {}

        def _fake_generate(filters, include_memory):
            captured["include_memory"] = include_memory
            return _FAKE_BOM

        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            side_effect=_fake_generate,
        ):
            generate_attestation()

        assert captured.get("include_memory") is False

    def test_memory_items_included_when_requested(self) -> None:
        captured: dict = {}

        def _fake_generate(filters, include_memory):
            captured["include_memory"] = include_memory
            return _FAKE_BOM

        with patch(
            "skillmeat.core.tools.generate_attestation._generate_bom",
            side_effect=_fake_generate,
        ):
            generate_attestation(include_memory_items=True)

        assert captured.get("include_memory") is True


# ---------------------------------------------------------------------------
# signing path (signature_key_id)
# ---------------------------------------------------------------------------


class TestGenerateAttestationSigning:
    def test_signing_called_when_key_id_provided(self) -> None:
        fake_sig = "deadbeef" * 8  # 64 hex chars

        with (
            patch(
                "skillmeat.core.tools.generate_attestation._generate_bom",
                return_value=_FAKE_BOM,
            ),
            patch(
                "skillmeat.core.tools.generate_attestation._sign_bom",
                return_value=fake_sig,
            ),
        ):
            result = generate_attestation(signature_key_id="my-key")

        assert result["signature"] == fake_sig

    def test_signing_error_reported_in_error_field(self) -> None:
        with (
            patch(
                "skillmeat.core.tools.generate_attestation._generate_bom",
                return_value=_FAKE_BOM,
            ),
            patch(
                "skillmeat.core.tools.generate_attestation._sign_bom",
                side_effect=RuntimeError("key not found"),
            ),
        ):
            result = generate_attestation(signature_key_id="bad-key")

        assert result["signature"] is None
        assert result["error"] is not None
        assert "key not found" in result["error"]

    def test_no_signing_when_key_id_none_and_signing_unavailable(self) -> None:
        with (
            patch(
                "skillmeat.core.tools.generate_attestation._generate_bom",
                return_value=_FAKE_BOM,
            ),
            patch(
                "skillmeat.core.tools.generate_attestation._signing_available",
                return_value=False,
            ),
        ):
            result = generate_attestation(signature_key_id=None)

        assert result["signature"] is None
