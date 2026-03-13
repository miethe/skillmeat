"""Claude Code agent tool for generating BOM attestations.

This module exposes :func:`generate_attestation` as a synchronous callable
suitable for use as a Claude Code agent tool.  It wraps the
:class:`~skillmeat.core.bom.generator.BomGenerator` and optionally the
signing module to produce a complete BOM attestation in one call.

Usage (agent tool invocation)::

    from skillmeat.core.tools.generate_attestation import generate_attestation

    result = generate_attestation(
        artifact_filters=["my-skill"],
        include_memory_items=False,
        signature_key_id=None,
    )
    # result = {"bom": {...}, "signature": None, "hash": "sha256:<hex>"}

Design decisions
----------------
* **Synchronous** — agent tool calls are synchronous by convention in SkillMeat.
* **Graceful degradation** — if the DB cache is unavailable, an empty BOM is
  returned rather than raising; the caller is notified via the ``error`` key.
* **No side effects** — this function does *not* persist a ``BomSnapshot``; it
  only generates and optionally signs the BOM dict.
* **Filter semantics** — ``artifact_filters`` is a list of artifact names or
  type:name pairs.  An empty list or ``None`` includes all artifacts.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_attestation(
    artifact_filters: Optional[List[str]] = None,
    include_memory_items: bool = False,
    signature_key_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a BOM attestation synchronously.

    Parameters
    ----------
    artifact_filters:
        Optional list of artifact names (or ``type:name`` strings) to include.
        When ``None`` or empty, all artifacts are included.
    include_memory_items:
        Whether to include memory-item type artifacts in the BOM.  Defaults to
        ``False`` because memory items are typically large and not relevant for
        deployment attestation.
    signature_key_id:
        Optional key identifier for signing the BOM with the default Ed25519
        key at ``~/.skillmeat/keys/skillbom_ed25519``.  When ``None`` the BOM
        is not signed.

    Returns
    -------
    dict
        A dict with the following keys:

        ``bom`` (dict):
            The full BOM dict as returned by :meth:`BomGenerator.generate`.
        ``signature`` (str | None):
            Hex-encoded Ed25519 signature over the canonical JSON, or ``None``
            if signing was not requested or failed.
        ``hash`` (str):
            SHA-256 hex digest of the canonical BOM JSON (without signature).
        ``error`` (str | None):
            Human-readable error message if generation partially or fully
            failed; ``None`` on full success.
    """
    bom: Dict[str, Any] = {}
    signature: Optional[str] = None
    bom_hash: str = ""
    error: Optional[str] = None

    try:
        bom = _generate_bom(artifact_filters, include_memory_items)
        # Apply filters in the outer function so they work even in tests.
        if artifact_filters:
            bom = _apply_filters(bom, artifact_filters)
    except Exception as exc:  # noqa: BLE001
        logger.warning("generate_attestation: BOM generation failed: %s", exc)
        bom = _empty_bom()
        error = f"BOM generation failed: {exc}"

    # Compute hash over canonical JSON (sorted keys, no signature).
    try:
        canonical_json = json.dumps(bom, sort_keys=True, separators=(",", ":"))
        bom_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    except Exception as exc:  # noqa: BLE001
        logger.warning("generate_attestation: hash computation failed: %s", exc)
        bom_hash = ""
        if error is None:
            error = f"Hash computation failed: {exc}"

    # Optional signing.
    if signature_key_id is not None or (signature_key_id is None and _signing_available()):
        if signature_key_id is not None:
            try:
                signature = _sign_bom(canonical_json, signature_key_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("generate_attestation: signing failed: %s", exc)
                if error is None:
                    error = f"Signing failed: {exc}"

    return {
        "bom": bom,
        "signature": signature,
        "hash": bom_hash,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_bom(
    artifact_filters: Optional[List[str]],
    include_memory_items: bool,
) -> Dict[str, Any]:
    """Run BomGenerator and apply filters.  Raises on hard failure."""
    from skillmeat.core.bom.generator import BomGenerator  # noqa: PLC0415
    from skillmeat.cache.manager import CacheManager  # noqa: PLC0415

    cache_mgr = CacheManager()
    session = cache_mgr.get_session()
    if session is None:
        raise RuntimeError("DB cache session unavailable.")

    generator = BomGenerator(session=session)

    # Optionally remove the memory-item adapter.
    if not include_memory_items:
        generator._adapters.pop("memory_item", None)

    return generator.generate()


def _apply_filters(
    bom: Dict[str, Any],
    filters: List[str],
) -> Dict[str, Any]:
    """Return a copy of *bom* with only the artifacts matching *filters*.

    A filter string matches an entry if it equals the entry's ``name`` field
    or its ``type:name`` compound string.
    """
    filter_set = set(filters)
    original_artifacts = bom.get("artifacts", [])
    kept = []
    for entry in original_artifacts:
        name = entry.get("name", "")
        artifact_type = entry.get("type", "")
        compound = f"{artifact_type}:{name}"
        if name in filter_set or compound in filter_set:
            kept.append(entry)

    return {
        **bom,
        "artifacts": kept,
        "artifact_count": len(kept),
    }


def _empty_bom() -> Dict[str, Any]:
    """Return a minimal empty BOM dict."""
    import time  # noqa: PLC0415
    from datetime import datetime, timezone  # noqa: PLC0415

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_path": None,
        "artifact_count": 0,
        "artifacts": [],
        "metadata": {
            "generator": "skillmeat-bom",
            "elapsed_ms": 0.0,
        },
    }


def _signing_available() -> bool:
    """Return True if the signing module can be imported."""
    try:
        import skillmeat.core.bom.signing  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False


def _sign_bom(canonical_json: str, key_id: str) -> Optional[str]:
    """Sign *canonical_json* with the Ed25519 key identified by *key_id*.

    Returns the hex-encoded signature string, or None on failure.
    """
    from skillmeat.core.bom.signing import sign_bom  # noqa: PLC0415

    result = sign_bom(canonical_json.encode("utf-8"))
    return result.signature_hex
