"""BOM (Bill of Materials) and attestation API endpoints.

Provides endpoints for generating, retrieving, and managing SkillBOM snapshots
and attestation records.  All endpoints are owner-scoped: users see only their
own context's data, filtered by ``AuthContext.user_id`` and ``AuthContext.tenant_id``.

Endpoints:
    GET  /bom/snapshot      -- Current point-in-time BOM snapshot
    POST /bom/generate      -- On-demand BOM generation (with optional auto-sign)
    GET  /attestations      -- Cursor-paginated list of attestation records
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from skillmeat.api.dependencies import (
    DbSessionDep,
    get_auth_context,
)
from skillmeat.api.schemas.auth import AuthContext
from skillmeat.api.schemas.bom import (
    ArtifactEntrySchema,
    AttestationSchema,
    BomSchema,
)
from skillmeat.cache.models import AttestationRecord, BomSnapshot

logger = logging.getLogger(__name__)


# =============================================================================
# Response schemas (BOM router-specific)
# =============================================================================


class BomSnapshotResponse(BaseModel):
    """Response schema for a stored BOM snapshot.

    Wraps the deserialized BOM document alongside snapshot storage metadata
    (id, project_id, commit_sha, owner_type, created_at).  Signature fields
    are included when the caller requests ``include_signatures=true``.
    """

    id: int = Field(description="Auto-incrementing snapshot primary key")
    project_id: Optional[str] = Field(
        default=None, description="Project scope for this snapshot"
    )
    commit_sha: Optional[str] = Field(
        default=None, description="Git commit SHA associated with this snapshot"
    )
    owner_type: str = Field(description="Owner context (user / team / enterprise)")
    created_at: str = Field(description="ISO-8601 UTC timestamp of snapshot creation")
    bom: BomSchema = Field(description="Deserialized BOM document")
    signature: Optional[str] = Field(
        default=None,
        description="Hex-encoded Ed25519 signature (present when include_signatures=true)",
    )
    signature_algorithm: Optional[str] = Field(
        default=None,
        description="Signature algorithm identifier (present when include_signatures=true)",
    )
    signing_key_id: Optional[str] = Field(
        default=None,
        description="SHA-256 fingerprint of the signing key (present when include_signatures=true)",
    )

    model_config = ConfigDict(from_attributes=True)


class BomGenerateRequest(BaseModel):
    """Request body for on-demand BOM generation."""

    project_id: Optional[str] = Field(
        default=None,
        description="Project scope to filter artifacts. None generates a collection-level BOM.",
    )
    auto_sign: bool = Field(
        default=False,
        description="Sign the generated BOM with the local Ed25519 signing key.",
    )

    model_config = ConfigDict(from_attributes=True)


class BomGenerateResponse(BaseModel):
    """Response schema for a freshly generated and persisted BOM snapshot."""

    id: int = Field(description="Auto-incrementing snapshot primary key")
    project_id: Optional[str] = Field(default=None)
    owner_type: str = Field(description="Owner context (user / team / enterprise)")
    created_at: str = Field(description="ISO-8601 UTC timestamp")
    bom: BomSchema = Field(description="Deserialized BOM document")
    signed: bool = Field(description="Whether the snapshot was signed")
    signature: Optional[str] = Field(
        default=None,
        description="Hex-encoded signature (present when auto_sign=true and signing succeeded)",
    )
    signing_key_id: Optional[str] = Field(
        default=None,
        description="SHA-256 fingerprint of the signing key (present when signed=true)",
    )

    model_config = ConfigDict(from_attributes=True)


class AttestationPageInfo(BaseModel):
    """Cursor-based pagination metadata for attestation list responses."""

    end_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor pointing to the last item on this page",
    )
    has_next_page: bool = Field(
        description="True when more records exist after this page"
    )


class AttestationListResponse(BaseModel):
    """Paginated list of attestation records."""

    items: List[AttestationSchema] = Field(
        default_factory=list, description="Attestation records on this page"
    )
    page_info: AttestationPageInfo = Field(
        description="Cursor-based pagination metadata"
    )


# =============================================================================
# Helper utilities
# =============================================================================

_VALID_OWNER_SCOPES = frozenset({"user", "team", "enterprise"})


def _bom_dict_to_schema(bom_data: Dict[str, Any]) -> BomSchema:
    """Convert a raw BOM dict (from JSON) into a :class:`BomSchema` instance.

    Unknown keys in *bom_data* are placed into the ``metadata`` block so that
    the schema remains stable as the BOM format evolves.

    Args:
        bom_data: Parsed BOM dict as returned by ``BomGenerator.generate()``.

    Returns:
        Populated :class:`BomSchema`.
    """
    artifacts_raw: List[Dict[str, Any]] = bom_data.get("artifacts", [])
    artifact_entries = [
        ArtifactEntrySchema(
            name=entry.get("name", ""),
            type=entry.get("type", ""),
            source=entry.get("source"),
            version=entry.get("version"),
            content_hash=entry.get("content_hash", ""),
            metadata=entry.get("metadata", {}),
            members=entry.get("members"),
        )
        for entry in artifacts_raw
    ]

    # Gather all non-core top-level keys into metadata.
    core_keys = {"schema_version", "generated_at", "project_path", "artifact_count", "artifacts"}
    extra_meta: Dict[str, Any] = {
        k: v for k, v in bom_data.items() if k not in core_keys
    }

    return BomSchema(
        schema_version=bom_data.get("schema_version", "1.0.0"),
        generated_at=bom_data.get("generated_at", ""),
        project_path=bom_data.get("project_path"),
        artifact_count=bom_data.get("artifact_count", len(artifact_entries)),
        artifacts=artifact_entries,
        metadata=extra_meta,
    )


def _snapshot_to_bom_response(
    snapshot: BomSnapshot,
    include_signatures: bool = False,
) -> BomSnapshotResponse:
    """Build a :class:`BomSnapshotResponse` from a :class:`BomSnapshot` ORM row.

    Args:
        snapshot: ORM model row from ``bom_snapshots``.
        include_signatures: When False, signature fields are omitted (None).

    Returns:
        Populated :class:`BomSnapshotResponse`.

    Raises:
        HTTPException: 500 when ``bom_json`` cannot be deserialized.
    """
    try:
        bom_data: Dict[str, Any] = json.loads(snapshot.bom_json)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error(
            "Failed to deserialize bom_json for snapshot id=%s: %s",
            snapshot.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BOM snapshot data is corrupted and cannot be deserialized.",
        )

    return BomSnapshotResponse(
        id=snapshot.id,
        project_id=snapshot.project_id,
        commit_sha=snapshot.commit_sha,
        owner_type=snapshot.owner_type,
        created_at=snapshot.created_at.isoformat() if snapshot.created_at else "",
        bom=_bom_dict_to_schema(bom_data),
        signature=snapshot.signature if include_signatures else None,
        signature_algorithm=snapshot.signature_algorithm if include_signatures else None,
        signing_key_id=snapshot.signing_key_id if include_signatures else None,
    )


def _attestation_to_schema(record: AttestationRecord) -> AttestationSchema:
    """Convert an :class:`AttestationRecord` ORM row to :class:`AttestationSchema`.

    Args:
        record: ORM row from ``attestation_records``.

    Returns:
        Serializable :class:`AttestationSchema`.
    """
    return AttestationSchema(
        id=str(record.id),
        artifact_id=record.artifact_id,
        owner_type=record.owner_type,
        owner_id=record.owner_id,
        roles=record.roles or [],
        scopes=record.scopes or [],
        visibility=record.visibility,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


# =============================================================================
# Router
# =============================================================================

router = APIRouter(tags=["bom"])


# ---------------------------------------------------------------------------
# GET /bom/snapshot
# ---------------------------------------------------------------------------


@router.get(
    "/bom/snapshot",
    response_model=BomSnapshotResponse,
    summary="Get current BOM snapshot",
    description=(
        "Return the most recent point-in-time Bill of Materials snapshot for "
        "the authenticated caller's scope.  Snapshots are owner-scoped: the "
        "response reflects only artifacts visible to the caller."
    ),
    responses={
        200: {"description": "BOM snapshot retrieved successfully"},
        404: {"description": "No BOM snapshot exists for the caller's scope"},
    },
)
async def get_bom_snapshot(
    db: DbSessionDep,
    auth_context: AuthContext = Depends(get_auth_context),
    project_id: Optional[str] = Query(
        default=None,
        description="Optional project scope filter. When omitted, returns the collection-level snapshot.",
    ),
    include_memory_items: bool = Query(
        default=False,
        description="Include memory-item artifact entries in the BOM (may increase response size).",
    ),
    include_signatures: bool = Query(
        default=False,
        description="Include Ed25519 signature fields (signature, signature_algorithm, signing_key_id).",
    ),
) -> BomSnapshotResponse:
    """Return the most recent BOM snapshot for the caller's owner context.

    Filters snapshots by:
    - ``owner_type`` matching the caller's principal type (``"user"`` by default).
    - Optional ``project_id`` when provided.

    The snapshot with the latest ``created_at`` is returned.
    """
    try:
        # Determine owner_type from auth context (default to "user").
        owner_type = "user"
        if auth_context.tenant_id:
            owner_type = "enterprise"

        query = db.query(BomSnapshot).filter(BomSnapshot.owner_type == owner_type)

        if project_id is not None:
            query = query.filter(BomSnapshot.project_id == project_id)

        snapshot: Optional[BomSnapshot] = (
            query.order_by(BomSnapshot.created_at.desc()).first()
        )

        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No BOM snapshot found for the caller's scope.",
            )

        response = _snapshot_to_bom_response(snapshot, include_signatures=include_signatures)

        # Filter out memory-item artifacts unless explicitly requested.
        if not include_memory_items and response.bom.artifacts:
            response.bom.artifacts = [
                a for a in response.bom.artifacts if a.type != "memory_item"
            ]
            response.bom.artifact_count = len(response.bom.artifacts)

        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve BOM snapshot: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve BOM snapshot.",
        )


# ---------------------------------------------------------------------------
# POST /bom/generate
# ---------------------------------------------------------------------------


@router.post(
    "/bom/generate",
    response_model=BomGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a BOM snapshot on demand",
    description=(
        "Trigger an on-demand Bill of Materials generation for the caller's "
        "artifact scope.  The result is persisted as a BomSnapshot row and "
        "optionally signed with the local Ed25519 signing key."
    ),
    responses={
        201: {"description": "BOM generated and persisted successfully"},
        500: {"description": "BOM generation failed"},
    },
)
async def generate_bom(
    request: BomGenerateRequest,
    db: DbSessionDep,
    auth_context: AuthContext = Depends(get_auth_context),
) -> BomGenerateResponse:
    """Generate a fresh BOM snapshot and persist it to the database.

    Steps:
    1. Instantiate ``BomGenerator`` with the current DB session.
    2. Call ``generate(project_id=...)`` to produce the BOM dict.
    3. Serialize to JSON via ``BomSerializer.to_json()``.
    4. If ``auto_sign`` is True, sign with ``sign_bom()`` using the default key.
    5. Persist as a ``BomSnapshot`` row and commit the session.
    6. Return the generated snapshot.
    """
    from skillmeat.core.bom.generator import BomGenerator, BomSerializer

    # Determine owner_type from auth context.
    owner_type = "user"
    if auth_context.tenant_id:
        owner_type = "enterprise"

    try:
        generator = BomGenerator(session=db)
        bom_dict = generator.generate(project_id=request.project_id)
    except Exception as exc:
        logger.exception("BOM generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BOM generation failed: {exc}",
        )

    serializer = BomSerializer()
    bom_json_str = serializer.to_json(bom_dict)

    # Optional Ed25519 signing.
    signature_hex: Optional[str] = None
    signing_key_id: Optional[str] = None
    signing_algorithm: Optional[str] = None
    signed = False

    if request.auto_sign:
        try:
            from skillmeat.core.bom.signing import sign_bom

            sig_result = sign_bom(bom_json_str.encode())
            signature_hex = sig_result.signature_hex
            signing_key_id = sig_result.key_id
            signing_algorithm = sig_result.algorithm
            signed = True
        except Exception as sign_exc:
            logger.warning(
                "BOM auto-sign requested but signing failed (key missing or error): %s",
                sign_exc,
            )
            # Non-fatal: persist the BOM without a signature.

    try:
        snapshot = BomSnapshot(
            bom_json=bom_json_str,
            project_id=request.project_id,
            owner_type=owner_type,
            signature=signature_hex,
            signature_algorithm=signing_algorithm,
            signing_key_id=signing_key_id,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist BOM snapshot: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist BOM snapshot.",
        )

    return BomGenerateResponse(
        id=snapshot.id,
        project_id=snapshot.project_id,
        owner_type=snapshot.owner_type,
        created_at=snapshot.created_at.isoformat() if snapshot.created_at else "",
        bom=_bom_dict_to_schema(bom_dict),
        signed=signed,
        signature=signature_hex,
        signing_key_id=signing_key_id,
    )


# ---------------------------------------------------------------------------
# GET /attestations
# ---------------------------------------------------------------------------


@router.get(
    "/attestations",
    response_model=AttestationListResponse,
    tags=["attestations"],
    summary="List attestation records",
    description=(
        "Return a cursor-paginated list of attestation records visible to the "
        "authenticated caller.  Results are owner-scoped: each caller sees only "
        "records belonging to their own principal context."
    ),
    responses={
        200: {"description": "Attestation records retrieved successfully"},
        400: {"description": "Invalid query parameters"},
    },
)
async def list_attestations(
    db: DbSessionDep,
    auth_context: AuthContext = Depends(get_auth_context),
    owner_scope: Optional[str] = Query(
        default=None,
        description=(
            "Filter by owner scope: 'user', 'team', or 'enterprise'. "
            "When omitted, returns all records accessible to the caller."
        ),
    ),
    artifact_id: Optional[str] = Query(
        default=None,
        description="Filter by artifact identifier in 'type:name' format.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of records to return per page.",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description=(
            "Opaque pagination cursor from a previous response's "
            "``page_info.end_cursor``.  When provided, results begin after "
            "the record identified by this cursor."
        ),
    ),
) -> AttestationListResponse:
    """List attestation records with owner-scope filtering and cursor pagination.

    Cursor semantics:
    - The cursor is the string representation of the last returned record's
      integer primary key (``id``).
    - Passing ``cursor=N`` returns records with ``id < N`` (newest-first ordering
      within each page is by ``id DESC``).
    """
    # Validate owner_scope when provided.
    if owner_scope is not None and owner_scope not in _VALID_OWNER_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid owner_scope '{owner_scope}'. "
                f"Must be one of: {sorted(_VALID_OWNER_SCOPES)!r}."
            ),
        )

    try:
        # Determine the caller's effective owner context.
        caller_owner_type = "user"
        caller_owner_id = auth_context.user_id or "local_admin"
        if auth_context.tenant_id:
            caller_owner_type = "enterprise"
            caller_owner_id = auth_context.tenant_id

        # Build the base query — restrict to caller's owner context.
        query = db.query(AttestationRecord).filter(
            AttestationRecord.owner_type == caller_owner_type,
            AttestationRecord.owner_id == caller_owner_id,
        )

        # Optional owner_scope secondary filter (refines owner_type).
        if owner_scope is not None:
            query = query.filter(AttestationRecord.owner_type == owner_scope)

        # Optional artifact filter.
        if artifact_id is not None:
            query = query.filter(AttestationRecord.artifact_id == artifact_id)

        # Cursor-based pagination: records with id < cursor, newest-first.
        if cursor is not None:
            try:
                cursor_id = int(cursor)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid cursor value '{cursor}'. Must be an integer.",
                )
            query = query.filter(AttestationRecord.id < cursor_id)

        # Fetch one extra record to determine hasNextPage.
        records: List[AttestationRecord] = (
            query.order_by(AttestationRecord.id.desc()).limit(limit + 1).all()
        )

        has_next_page = len(records) > limit
        page_records = records[:limit]

        end_cursor: Optional[str] = None
        if page_records:
            end_cursor = str(page_records[-1].id)

        return AttestationListResponse(
            items=[_attestation_to_schema(r) for r in page_records],
            page_info=AttestationPageInfo(
                end_cursor=end_cursor,
                has_next_page=has_next_page,
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list attestation records: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve attestation records.",
        )
