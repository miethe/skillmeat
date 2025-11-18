"""Bundle import/export API endpoints.

Provides REST API for importing and validating artifact bundles.
"""

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from skillmeat.api.dependencies import ConfigManagerDep
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.bundles import (
    ArtifactPopularity,
    BundleAnalyticsResponse,
    BundleArtifactSummary,
    BundleDeleteResponse,
    BundleDetailResponse,
    BundleExportRequest,
    BundleExportResponse,
    BundleImportRequest,
    BundleImportResponse,
    BundleListItem,
    BundleListResponse,
    BundleMetadataResponse,
    BundlePreviewCategorization,
    BundlePreviewResponse,
    BundleValidationResponse,
    ImportedArtifactResponse,
    PreviewArtifact,
    ShareLinkDeleteResponse,
    ShareLinkResponse,
    ShareLinkUpdateRequest,
    ValidationIssueResponse,
)
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.sharing.builder import BundleBuilder
from skillmeat.core.sharing.importer import BundleImporter
from skillmeat.core.sharing.validator import BundleValidator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/bundles",
    tags=["bundles"],
)


@router.post(
    "/import",
    response_model=BundleImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import artifact bundle",
    description="Import a bundle ZIP file into collection with conflict resolution",
    responses={
        200: {"description": "Bundle imported successfully"},
        400: {"model": ErrorResponse, "description": "Invalid bundle or parameters"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Import failed"},
    },
)
async def import_bundle(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    bundle_file: UploadFile = File(..., description="Bundle ZIP file to import"),
    strategy: str = Form(
        default="interactive",
        description="Conflict resolution strategy (merge, fork, skip, interactive)",
    ),
    collection_name: Optional[str] = Form(
        default=None,
        description="Target collection (uses active if None)",
    ),
    dry_run: bool = Form(
        default=False,
        description="Preview import without making changes",
    ),
    force: bool = Form(
        default=False,
        description="Force import even with validation warnings",
    ),
    expected_hash: Optional[str] = Form(
        default=None,
        description="Expected SHA-256 hash for verification",
    ),
) -> BundleImportResponse:
    """Import artifact bundle into collection.

    Upload a bundle ZIP file and import its contents with comprehensive
    conflict resolution and validation.

    Args:
        bundle_file: Uploaded bundle ZIP file
        strategy: Conflict resolution strategy
        collection_name: Target collection name
        dry_run: Preview mode flag
        force: Force import flag
        expected_hash: Expected bundle hash
        config_mgr: Configuration manager dependency
        token: Authentication token

    Returns:
        BundleImportResponse with import details

    Raises:
        HTTPException: On validation or import failure
    """
    temp_bundle_path = None

    try:
        # Validate strategy
        allowed_strategies = {"merge", "fork", "skip", "interactive"}
        if strategy not in allowed_strategies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy. Must be one of: {', '.join(allowed_strategies)}",
            )

        # Interactive strategy not supported in API (no user prompts)
        if strategy == "interactive" and not dry_run:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interactive strategy not supported via API. Use merge, fork, or skip.",
            )

        # Validate file type
        if not bundle_file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bundle must be a ZIP file",
            )

        logger.info(
            f"Importing bundle: {bundle_file.filename} "
            f"(strategy={strategy}, dry_run={dry_run})"
        )

        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".zip", prefix="skillmeat_bundle_"
        ) as temp_file:
            temp_bundle_path = Path(temp_file.name)
            content = await bundle_file.read()
            temp_file.write(content)

        # Initialize importer
        collection_mgr = CollectionManager(config=config_mgr)
        importer = BundleImporter(collection_mgr=collection_mgr)

        # Perform import (console=None for non-interactive)
        result = importer.import_bundle(
            bundle_path=temp_bundle_path,
            collection_name=collection_name,
            strategy=strategy,
            dry_run=dry_run,
            force=force,
            expected_hash=expected_hash,
            console=None,  # Non-interactive mode
        )

        # Convert to response model
        artifacts_response = [
            ImportedArtifactResponse(
                name=artifact.name,
                type=artifact.type,
                resolution=artifact.resolution,
                new_name=artifact.new_name,
                reason=artifact.reason,
            )
            for artifact in result.artifacts
        ]

        response = BundleImportResponse(
            success=result.success,
            imported_count=result.imported_count,
            skipped_count=result.skipped_count,
            forked_count=result.forked_count,
            merged_count=result.merged_count,
            artifacts=artifacts_response,
            errors=result.errors,
            warnings=result.warnings,
            bundle_hash=result.bundle_hash,
            import_time=result.import_time,
            summary=result.summary(),
        )

        if not result.success:
            # Import failed - return 400 with error details
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Bundle import failed",
                    "errors": result.errors,
                    "warnings": result.warnings,
                },
            )

        logger.info(f"Bundle import successful: {result.summary()}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Bundle import failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bundle import failed: {str(e)}",
        )

    finally:
        # Clean up temp file
        if temp_bundle_path and temp_bundle_path.exists():
            try:
                temp_bundle_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temp bundle file: {e}")


@router.post(
    "/validate",
    response_model=BundleValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate bundle without importing",
    description="Check bundle integrity and validity without importing",
    responses={
        200: {"description": "Validation completed (check is_valid field)"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Validation failed"},
    },
)
async def validate_bundle(
    token: TokenDep,
    bundle_file: UploadFile = File(..., description="Bundle ZIP file to validate"),
    expected_hash: Optional[str] = Form(
        default=None,
        description="Expected SHA-256 hash for verification",
    ),
) -> BundleValidationResponse:
    """Validate bundle without importing.

    Performs comprehensive validation including:
    - Hash verification (if expected_hash provided)
    - Path traversal prevention
    - Zip bomb detection
    - Schema validation
    - File size checks

    Args:
        bundle_file: Uploaded bundle ZIP file
        expected_hash: Expected SHA-256 hash
        token: Authentication token

    Returns:
        BundleValidationResponse with validation details

    Raises:
        HTTPException: On validation error
    """
    temp_bundle_path = None

    try:
        # Validate file type
        if not bundle_file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bundle must be a ZIP file",
            )

        logger.info(f"Validating bundle: {bundle_file.filename}")

        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".zip", prefix="skillmeat_validate_"
        ) as temp_file:
            temp_bundle_path = Path(temp_file.name)
            content = await bundle_file.read()
            temp_file.write(content)

        # Validate
        validator = BundleValidator()
        validation = validator.validate(temp_bundle_path, expected_hash)

        # Convert to response
        issues_response = [
            ValidationIssueResponse(
                severity=issue.severity,
                category=issue.category,
                message=issue.message,
                file_path=issue.file_path,
            )
            for issue in validation.issues
        ]

        response = BundleValidationResponse(
            is_valid=validation.is_valid,
            issues=issues_response,
            bundle_hash=validation.bundle_hash,
            artifact_count=validation.artifact_count,
            total_size_bytes=validation.total_size_bytes,
            summary=validation.summary(),
        )

        logger.info(f"Bundle validation completed: {validation.summary()}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Bundle validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bundle validation failed: {str(e)}",
        )

    finally:
        # Clean up temp file
        if temp_bundle_path and temp_bundle_path.exists():
            try:
                temp_bundle_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temp bundle file: {e}")


@router.post(
    "/preview",
    response_model=BundlePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview bundle before importing",
    description="Analyze bundle contents and detect conflicts without importing",
    responses={
        200: {"description": "Preview completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid bundle"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Preview failed"},
    },
)
async def preview_bundle(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    bundle_file: UploadFile = File(..., description="Bundle ZIP file to preview"),
    collection_name: Optional[str] = Form(
        default=None,
        description="Target collection (uses active if None)",
    ),
    expected_hash: Optional[str] = Form(
        default=None,
        description="Expected SHA-256 hash for verification",
    ),
) -> BundlePreviewResponse:
    """Preview bundle before importing.

    Validates bundle and analyzes what would happen during import:
    - Lists all artifacts in bundle
    - Identifies conflicts with existing artifacts
    - Categorizes artifacts (new vs existing)
    - Shows validation issues

    This is a read-only operation - no artifacts are imported.

    Args:
        bundle_file: Uploaded bundle ZIP file
        collection_name: Target collection name
        expected_hash: Expected SHA-256 hash
        config_mgr: Configuration manager dependency
        token: Authentication token

    Returns:
        BundlePreviewResponse with analysis results

    Raises:
        HTTPException: On validation or analysis failure
    """
    temp_bundle_path = None
    temp_extract_dir = None

    try:
        # Validate file type
        if not bundle_file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bundle must be a ZIP file",
            )

        logger.info(f"Previewing bundle: {bundle_file.filename}")

        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".zip", prefix="skillmeat_preview_"
        ) as temp_file:
            temp_bundle_path = Path(temp_file.name)
            content = await bundle_file.read()
            temp_file.write(content)

        # Step 1: Validate bundle
        validator = BundleValidator()
        validation = validator.validate(temp_bundle_path, expected_hash)

        # Convert validation issues to response format
        validation_issues = [
            ValidationIssueResponse(
                severity=issue.severity,
                category=issue.category,
                message=issue.message,
                file_path=issue.file_path,
            )
            for issue in validation.issues
        ]

        # If bundle is invalid, return early with validation results
        if not validation.is_valid:
            logger.warning(f"Bundle validation failed: {validation.summary()}")
            return BundlePreviewResponse(
                is_valid=False,
                bundle_hash=validation.bundle_hash,
                metadata=None,
                artifacts=[],
                categorization=BundlePreviewCategorization(),
                validation_issues=validation_issues,
                total_size_bytes=validation.total_size_bytes,
                collection_name=collection_name or "default",
                summary="Bundle validation failed - cannot preview",
            )

        # Step 2: Load target collection
        try:
            collection_mgr = CollectionManager(config=config_mgr)
            collection = collection_mgr.load_collection(collection_name)
            collection_name = collection.name
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to load collection: {e}",
            )

        # Step 3: Extract bundle and load manifest
        temp_extract_dir = Path(tempfile.mkdtemp(prefix="skillmeat_preview_"))

        with zipfile.ZipFile(temp_bundle_path, "r") as zf:
            zf.extractall(temp_extract_dir)

        manifest_path = temp_extract_dir / "bundle.toml"
        if not manifest_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bundle missing required bundle.toml manifest",
            )

        # Load manifest
        from skillmeat.utils.toml_compat import loads as toml_loads

        with open(manifest_path, "rb") as f:
            manifest_data = toml_loads(f.read().decode("utf-8"))

        # Extract bundle metadata
        bundle_section = manifest_data.get("bundle", {})
        metadata = BundleMetadataResponse(
            name=bundle_section.get("name", "unknown"),
            description=bundle_section.get("description", ""),
            author=bundle_section.get("creator", "unknown"),
            created_at=bundle_section.get("created_at", ""),
            version=bundle_section.get("version", "1.0.0"),
            license=bundle_section.get("license", "MIT"),
            tags=bundle_section.get("tags", []),
            homepage=bundle_section.get("homepage"),
            repository=bundle_section.get("repository"),
        )

        # Step 4: Analyze artifacts and detect conflicts
        from skillmeat.core.artifact import ArtifactType

        artifacts_data = manifest_data.get("artifacts", [])
        preview_artifacts = []
        new_count = 0
        existing_count = 0

        for artifact_data in artifacts_data:
            artifact_name = artifact_data["name"]
            artifact_type = ArtifactType(artifact_data["type"])
            artifact_version = artifact_data.get("version")
            artifact_path = artifact_data["path"]

            # Check if exists in collection
            existing = collection.find_artifact(artifact_name, artifact_type)

            has_conflict = existing is not None
            existing_version = None

            if has_conflict:
                existing_count += 1
                # Try to get version from existing artifact
                if existing.metadata and hasattr(existing.metadata, "version"):
                    existing_version = existing.metadata.version
                elif existing.resolved_version:
                    existing_version = existing.resolved_version
            else:
                new_count += 1

            preview_artifacts.append(
                PreviewArtifact(
                    name=artifact_name,
                    type=artifact_type.value,
                    version=artifact_version,
                    path=artifact_path,
                    has_conflict=has_conflict,
                    existing_version=existing_version,
                )
            )

        # Step 5: Create categorization
        categorization = BundlePreviewCategorization(
            new_artifacts=new_count,
            existing_artifacts=existing_count,
            will_import=new_count,
            will_require_resolution=existing_count,
        )

        # Step 6: Build summary
        summary_parts = []
        summary_parts.append(f"Bundle contains {len(preview_artifacts)} artifact(s)")
        if new_count > 0:
            summary_parts.append(f"{new_count} new")
        if existing_count > 0:
            summary_parts.append(f"{existing_count} conflict(s)")

        summary = (
            " - ".join(summary_parts) if len(summary_parts) > 1 else summary_parts[0]
        )

        # Build response
        response = BundlePreviewResponse(
            is_valid=True,
            bundle_hash=validation.bundle_hash,
            metadata=metadata,
            artifacts=preview_artifacts,
            categorization=categorization,
            validation_issues=validation_issues,
            total_size_bytes=validation.total_size_bytes,
            collection_name=collection_name,
            summary=summary,
        )

        logger.info(
            f"Bundle preview completed: {summary} (collection: {collection_name})"
        )
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Bundle preview failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bundle preview failed: {str(e)}",
        )

    finally:
        # Clean up temp files
        if temp_bundle_path and temp_bundle_path.exists():
            try:
                temp_bundle_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temp bundle file: {e}")

        if temp_extract_dir and temp_extract_dir.exists():
            try:
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up temp extract directory: {e}")


@router.post(
    "/export",
    response_model=BundleExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export artifacts as a bundle",
    description="Create a bundle archive from selected artifacts with optional sharing",
    responses={
        200: {"description": "Bundle exported successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or artifact not found",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Export failed"},
    },
)
async def export_bundle(
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    request: BundleExportRequest,
) -> BundleExportResponse:
    """Export artifacts as a bundle.

    Creates a .skillmeat-pack bundle containing selected artifacts with:
    - Comprehensive metadata
    - Cryptographic integrity verification
    - Optional digital signature
    - Optional shareable link generation

    Args:
        config_mgr: Configuration manager dependency
        token: Authentication token
        request: Export request with artifact IDs, metadata, and options

    Returns:
        BundleExportResponse with bundle details and download URL

    Raises:
        HTTPException: On validation or export failure
    """
    try:
        logger.info(
            f"Exporting bundle: {request.metadata.name} "
            f"({len(request.artifact_ids)} artifacts)"
        )

        # Initialize collection manager
        collection_mgr = CollectionManager(config=config_mgr)
        collection = collection_mgr.load_collection(request.collection_name)

        # Validate artifact IDs format and parse them
        artifacts_to_add = []
        warnings = []

        for artifact_id in request.artifact_ids:
            # Parse artifact_id format: "type::name"
            if "::" not in artifact_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact ID format: {artifact_id}. "
                    "Expected format: 'type::name' (e.g., 'skill::python-debugger')",
                )

            artifact_type_str, artifact_name = artifact_id.split("::", 1)

            # Validate artifact type
            try:
                artifact_type = ArtifactType(artifact_type_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact type: {artifact_type_str}. "
                    f"Must be one of: {', '.join([t.value for t in ArtifactType])}",
                )

            # Verify artifact exists in collection
            artifact = collection.find_artifact(artifact_name, artifact_type)
            if not artifact:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Artifact '{artifact_name}' of type '{artifact_type_str}' "
                    f"not found in collection '{collection.name}'",
                )

            artifacts_to_add.append((artifact_name, artifact_type))

        # Create bundle builder with metadata
        builder = BundleBuilder(
            name=request.metadata.name,
            description=request.metadata.description,
            author=request.metadata.author,
            version=request.metadata.version,
            license=request.metadata.license,
            tags=request.metadata.tags,
            homepage=request.metadata.homepage,
            repository=request.metadata.repository,
            collection_name=collection.name,
        )

        # Add artifacts to builder
        for artifact_name, artifact_type in artifacts_to_add:
            try:
                builder.add_artifact(artifact_name, artifact_type)
            except Exception as e:
                logger.warning(
                    f"Failed to add artifact {artifact_name} ({artifact_type.value}): {e}"
                )
                warnings.append(f"Failed to add artifact {artifact_name}: {str(e)}")

        # Determine output directory (use bundles directory)
        bundles_dir = config_mgr.get_collection_path(collection.name).parent / "bundles"
        bundles_dir.mkdir(parents=True, exist_ok=True)

        # Build bundle (use .skillmeat-pack extension)
        output_filename = f"{request.metadata.name}.skillmeat-pack"
        output_path = bundles_dir / output_filename

        # Build bundle with options
        bundle = builder.build(
            output_path=output_path,
            validate=True,
            sign=request.options.sign_bundle,
            signing_key_id=request.options.signing_key_id,
        )

        # Calculate bundle size
        bundle_size = output_path.stat().st_size

        # Generate download URL (relative to API base)
        # Format: sha256:first64chars (shortened for readability)
        bundle_id_short = bundle.bundle_hash[:71] if bundle.bundle_hash else "unknown"
        download_url = f"/api/bundles/{bundle_id_short}/download"

        # Generate share link if requested
        share_link = None
        if request.options.generate_share_link:
            # TODO: Implement actual share link generation with vault storage
            # For now, return a placeholder
            share_link = f"https://skillmeat.app/share/{bundle.bundle_hash[7:15]}"
            warnings.append(
                "Share link generation not yet implemented. Placeholder returned."
            )

        # Create response metadata
        from datetime import datetime

        export_time = datetime.utcnow()

        response_metadata = BundleMetadataResponse(
            name=bundle.metadata.name,
            description=bundle.metadata.description,
            author=bundle.metadata.author,
            created_at=bundle.metadata.created_at,
            version=bundle.metadata.version,
            license=bundle.metadata.license,
            tags=bundle.metadata.tags,
            homepage=bundle.metadata.homepage,
            repository=bundle.metadata.repository,
        )

        response = BundleExportResponse(
            success=True,
            bundle_id=bundle.bundle_hash or "unknown",
            bundle_path=str(output_path),
            download_url=download_url,
            share_link=share_link,
            stream_url=None,  # SSE streaming not yet implemented
            metadata=response_metadata,
            artifact_count=len(bundle.artifacts),
            total_size_bytes=bundle_size,
            warnings=warnings,
            export_time=export_time,
        )

        logger.info(
            f"Bundle export successful: {bundle.metadata.name} "
            f"({bundle.artifact_count} artifacts, {bundle_size} bytes)"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Bundle export failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bundle export failed: {str(e)}",
        )


@router.get(
    "",
    response_model=BundleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all bundles",
    description="Get list of all bundles with optional filtering by source (created, imported)",
    responses={
        200: {"description": "List of bundles retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Failed to retrieve bundles"},
    },
)
async def list_bundles(
    token: TokenDep,
    source_filter: Optional[str] = None,
) -> BundleListResponse:
    """List all bundles with optional filtering.

    Returns a list of all bundles in the collection, with optional filtering
    by source (created, imported, marketplace).

    Args:
        source_filter: Optional filter by bundle source (created, imported, marketplace)
        token: Authentication token

    Returns:
        BundleListResponse with list of bundles

    Raises:
        HTTPException: On retrieval failure
    """
    try:
        # Validate source filter
        if source_filter and source_filter not in [
            "created",
            "imported",
            "marketplace",
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source filter. Must be one of: created, imported, marketplace",
            )

        logger.info(f"Listing bundles (filter={source_filter or 'none'})")

        # TODO: Replace with actual bundle storage retrieval
        # For now, return mock data to enable frontend integration
        mock_bundles = _get_mock_bundles()

        # Apply filter if specified
        if source_filter:
            filtered_bundles = [b for b in mock_bundles if b["source"] == source_filter]
        else:
            filtered_bundles = mock_bundles

        # Convert to response models
        bundle_items = [BundleListItem(**bundle) for bundle in filtered_bundles]

        response = BundleListResponse(
            bundles=bundle_items,
            total=len(bundle_items),
            filtered_by=source_filter,
        )

        logger.info(
            f"Retrieved {len(bundle_items)} bundles (total: {len(mock_bundles)})"
        )
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Failed to list bundles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bundles: {str(e)}",
        )


@router.get(
    "/{bundle_id}",
    response_model=BundleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bundle details",
    description="Retrieve detailed information about a specific bundle",
    responses={
        200: {"description": "Bundle details retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Bundle not found"},
        500: {"model": ErrorResponse, "description": "Failed to retrieve bundle"},
    },
)
async def get_bundle(
    bundle_id: str,
    token: TokenDep,
) -> BundleDetailResponse:
    """Get detailed information about a specific bundle.

    Retrieves complete bundle metadata, artifact list, and other details.

    Args:
        bundle_id: Bundle unique identifier (SHA-256 hash)
        token: Authentication token

    Returns:
        BundleDetailResponse with bundle details

    Raises:
        HTTPException: On retrieval failure or if bundle not found
    """
    try:
        logger.info(f"Retrieving bundle details: {bundle_id}")

        # TODO: Replace with actual bundle storage lookup
        # For now, return mock data
        bundle_data = _get_mock_bundle_detail(bundle_id)

        if bundle_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bundle not found: {bundle_id}",
            )

        # Convert to response model
        response = BundleDetailResponse(**bundle_data)

        logger.info(f"Retrieved bundle: {response.metadata.name}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve bundle {bundle_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bundle: {str(e)}",
        )


@router.delete(
    "/{bundle_id}",
    response_model=BundleDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a bundle",
    description="Delete a bundle from the collection",
    responses={
        200: {"description": "Bundle deleted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Bundle not found"},
        500: {"model": ErrorResponse, "description": "Failed to delete bundle"},
    },
)
async def delete_bundle(
    bundle_id: str,
    token: TokenDep,
) -> BundleDeleteResponse:
    """Delete a bundle from the collection.

    Removes the bundle file and its metadata. Does not affect artifacts
    that were previously imported from this bundle.

    Args:
        bundle_id: Bundle unique identifier (SHA-256 hash)
        token: Authentication token

    Returns:
        BundleDeleteResponse with deletion status

    Raises:
        HTTPException: On deletion failure or if bundle not found
    """
    try:
        logger.info(f"Deleting bundle: {bundle_id}")

        # TODO: Replace with actual bundle storage deletion
        # For now, simulate successful deletion
        # In real implementation:
        # 1. Verify bundle exists
        # 2. Delete bundle file from storage
        # 3. Remove bundle metadata from database
        # 4. Log deletion event

        # Mock validation
        if not bundle_id.startswith("sha256:"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid bundle_id format. Must start with 'sha256:'",
            )

        # Simulate bundle lookup
        bundle_data = _get_mock_bundle_detail(bundle_id)
        if bundle_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bundle not found: {bundle_id}",
            )

        response = BundleDeleteResponse(
            success=True,
            bundle_id=bundle_id,
            message=f"Bundle deleted successfully (mock implementation)",
        )

        logger.info(f"Bundle deleted: {bundle_id}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Failed to delete bundle {bundle_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bundle: {str(e)}",
        )


@router.get(
    "/{bundle_id}/analytics",
    response_model=BundleAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bundle analytics",
    description="Retrieve analytics data for a bundle including downloads and popular artifacts",
    responses={
        200: {"description": "Bundle analytics retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Bundle not found"},
        500: {"model": ErrorResponse, "description": "Failed to retrieve analytics"},
    },
)
async def get_bundle_analytics(
    bundle_id: str,
    token: TokenDep,
) -> BundleAnalyticsResponse:
    """Get analytics data for a specific bundle.

    Retrieves usage statistics including:
    - Total downloads/imports
    - Deployment counts
    - Popular artifacts from the bundle
    - Active projects using bundle artifacts

    Args:
        bundle_id: Bundle unique identifier (SHA-256 hash)
        token: Authentication token

    Returns:
        BundleAnalyticsResponse with analytics data

    Raises:
        HTTPException: On retrieval failure or if bundle not found
    """
    try:
        logger.info(f"Retrieving analytics for bundle: {bundle_id}")

        # TODO: Replace with actual analytics from AnalyticsDB
        # For now, return mock data
        # In real implementation:
        # 1. Query analytics database for bundle-related events
        # 2. Aggregate download/import counts
        # 3. Count deployments per artifact
        # 4. Count unique projects using artifacts
        # 5. Find most popular artifacts

        # Verify bundle exists
        bundle_data = _get_mock_bundle_detail(bundle_id)
        if bundle_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bundle not found: {bundle_id}",
            )

        analytics_data = _get_mock_bundle_analytics(bundle_id, bundle_data)

        response = BundleAnalyticsResponse(**analytics_data)

        logger.info(
            f"Retrieved analytics for bundle: {response.bundle_name} "
            f"(downloads: {response.total_downloads}, deploys: {response.total_deploys})"
        )
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(
            f"Failed to retrieve analytics for bundle {bundle_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bundle analytics: {str(e)}",
        )


# ====================
# Mock Data Helpers
# ====================
# TODO: Remove these when real bundle storage is implemented


def _get_mock_bundles() -> list:
    """Get mock bundle list data.

    Returns:
        List of mock bundle dictionaries
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()

    return [
        {
            "bundle_id": "sha256:abc123def456789012345678901234567890123456789012345678901234",
            "name": "python-essentials",
            "description": "Essential Python development skills and commands",
            "author": "john.doe@example.com",
            "created_at": (now - timedelta(days=30)).isoformat() + "Z",
            "artifact_count": 5,
            "total_size_bytes": 1048576,
            "source": "imported",
            "imported_at": (now - timedelta(days=15)).isoformat() + "Z",
            "tags": ["python", "development", "productivity"],
        },
        {
            "bundle_id": "sha256:def456abc789012345678901234567890123456789012345678901234567",
            "name": "web-dev-toolkit",
            "description": "Full-stack web development tools and skills",
            "author": "jane.smith@example.com",
            "created_at": (now - timedelta(days=20)).isoformat() + "Z",
            "artifact_count": 8,
            "total_size_bytes": 2097152,
            "source": "created",
            "imported_at": None,
            "tags": ["web", "javascript", "typescript", "react"],
        },
        {
            "bundle_id": "sha256:789012def456abc123456789012345678901234567890123456789012345",
            "name": "data-science-bundle",
            "description": "Data analysis and machine learning skills",
            "author": "data.scientist@example.com",
            "created_at": (now - timedelta(days=10)).isoformat() + "Z",
            "artifact_count": 12,
            "total_size_bytes": 3145728,
            "source": "marketplace",
            "imported_at": (now - timedelta(days=5)).isoformat() + "Z",
            "tags": ["data-science", "ml", "python", "jupyter"],
        },
    ]


def _get_mock_bundle_detail(bundle_id: str) -> Optional[dict]:
    """Get mock bundle detail data.

    Args:
        bundle_id: Bundle identifier

    Returns:
        Mock bundle detail dictionary or None if not found
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()

    # Mock bundle database
    bundles = {
        "sha256:abc123def456789012345678901234567890123456789012345678901234": {
            "bundle_id": "sha256:abc123def456789012345678901234567890123456789012345678901234",
            "metadata": {
                "name": "python-essentials",
                "description": "Essential Python development skills and commands",
                "author": "john.doe@example.com",
                "created_at": (now - timedelta(days=30)).isoformat() + "Z",
                "version": "1.0.0",
                "license": "MIT",
                "tags": ["python", "development", "productivity"],
                "homepage": "https://github.com/johndoe/python-essentials",
                "repository": "https://github.com/johndoe/python-essentials",
            },
            "artifacts": [
                {
                    "name": "python-debugger",
                    "type": "skill",
                    "version": "1.2.0",
                    "scope": "user",
                },
                {
                    "name": "pytest-helper",
                    "type": "command",
                    "version": "1.0.1",
                    "scope": "user",
                },
                {
                    "name": "code-formatter",
                    "type": "skill",
                    "version": "2.0.0",
                    "scope": "user",
                },
            ],
            "dependencies": [],
            "bundle_hash": "sha256:abc123def456789012345678901234567890123456789012345678901234",
            "total_size_bytes": 1048576,
            "total_files": 25,
            "source": "imported",
            "imported_at": (now - timedelta(days=15)).isoformat() + "Z",
            "bundle_path": "/home/user/.skillmeat/bundles/abc123.zip",
        },
        "sha256:def456abc789012345678901234567890123456789012345678901234567": {
            "bundle_id": "sha256:def456abc789012345678901234567890123456789012345678901234567",
            "metadata": {
                "name": "web-dev-toolkit",
                "description": "Full-stack web development tools and skills",
                "author": "jane.smith@example.com",
                "created_at": (now - timedelta(days=20)).isoformat() + "Z",
                "version": "2.1.0",
                "license": "Apache-2.0",
                "tags": ["web", "javascript", "typescript", "react"],
                "homepage": "https://example.com/web-dev-toolkit",
                "repository": None,
            },
            "artifacts": [
                {
                    "name": "react-component-generator",
                    "type": "skill",
                    "version": "1.5.0",
                    "scope": "user",
                },
                {
                    "name": "typescript-linter",
                    "type": "command",
                    "version": "1.1.0",
                    "scope": "user",
                },
            ],
            "dependencies": [],
            "bundle_hash": "sha256:def456abc789012345678901234567890123456789012345678901234567",
            "total_size_bytes": 2097152,
            "total_files": 42,
            "source": "created",
            "imported_at": None,
            "bundle_path": "/home/user/.skillmeat/bundles/def456.zip",
        },
    }

    return bundles.get(bundle_id)


def _get_mock_bundle_analytics(bundle_id: str, bundle_data: dict) -> dict:
    """Get mock bundle analytics data.

    Args:
        bundle_id: Bundle identifier
        bundle_data: Bundle detail data

    Returns:
        Mock analytics dictionary
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()

    # Generate mock analytics based on bundle
    bundle_name = bundle_data["metadata"]["name"]
    artifact_count = len(bundle_data["artifacts"])

    # Mock popular artifacts
    popular_artifacts = []
    for i, artifact in enumerate(bundle_data["artifacts"][:3]):  # Top 3
        popular_artifacts.append(
            {
                "artifact_name": artifact["name"],
                "artifact_type": artifact["type"],
                "deploy_count": max(10, 50 - (i * 10)),  # Decreasing popularity
                "last_deployed": (now - timedelta(days=i + 1)).isoformat() + "Z",
            }
        )

    return {
        "bundle_id": bundle_id,
        "bundle_name": bundle_name,
        "total_downloads": 15 + (artifact_count * 2),
        "total_deploys": 42 + (artifact_count * 5),
        "popular_artifacts": popular_artifacts,
        "first_imported": bundle_data.get("imported_at")
        or bundle_data["metadata"]["created_at"],
        "last_used": (now - timedelta(days=1)).isoformat() + "Z",
        "active_projects": min(5, artifact_count),
    }


# ====================
# Share Link Management
# ====================


@router.put(
    "/{bundle_id}/share",
    response_model=ShareLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update bundle share link",
    description="Generate or update a shareable link for a bundle with permissions and expiration",
    responses={
        200: {"description": "Share link created/updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid bundle_id or request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Bundle not found"},
        500: {"model": ErrorResponse, "description": "Failed to create share link"},
    },
)
async def update_bundle_share_link(
    bundle_id: str,
    request: ShareLinkUpdateRequest,
    token: TokenDep,
) -> ShareLinkResponse:
    """Create or update a shareable link for a bundle.

    Generates a shareable URL with configurable permissions, expiration, and download limits.
    The link allows controlled sharing of bundles with external users.

    Args:
        bundle_id: Bundle unique identifier (SHA-256 hash)
        request: Share link configuration (permissions, expiration, max downloads)
        token: Authentication token

    Returns:
        ShareLinkResponse with shareable URL and link details

    Raises:
        HTTPException: On validation failure or if bundle not found
    """
    try:
        # Validate bundle_id format
        if not bundle_id.startswith("sha256:"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid bundle_id format. Must start with 'sha256:'",
            )

        logger.info(
            f"Creating/updating share link for bundle: {bundle_id} "
            f"(permission={request.permission_level}, expiration={request.expiration_hours}h)"
        )

        # Verify bundle exists
        bundle_data = _get_mock_bundle_detail(bundle_id)
        if bundle_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bundle not found: {bundle_id}",
            )

        # TODO: Replace with actual share link generation and storage
        # In real implementation:
        # 1. Generate unique share token (short code)
        # 2. Store share link in database with metadata
        # 3. Generate QR code image
        # 4. Calculate expiration timestamp
        # 5. Track usage analytics

        from datetime import datetime, timedelta
        import hashlib

        now = datetime.utcnow()

        # Generate short code from bundle_id hash
        short_code = hashlib.sha256(
            f"{bundle_id}{now.isoformat()}".encode()
        ).hexdigest()[:8]

        # Calculate expiration timestamp
        expires_at = None
        if request.expiration_hours:
            expiration_time = now + timedelta(hours=request.expiration_hours)
            expires_at = expiration_time.isoformat() + "Z"

        # Generate URLs
        full_url = f"https://skillmeat.app/share/{short_code}"
        short_url = f"https://sm.app/{short_code}"

        # Mock QR code data URL (in real implementation, generate actual QR code)
        qr_code = f"data:image/png;base64,iVBORw0KGgoAAAANS...{short_code}"

        response = ShareLinkResponse(
            success=True,
            bundle_id=bundle_id,
            url=full_url,
            short_url=short_url,
            qr_code=qr_code,
            permission_level=request.permission_level,
            expires_at=expires_at,
            max_downloads=request.max_downloads,
            download_count=0,  # New link starts at 0
            created_at=now.isoformat() + "Z",
        )

        logger.info(
            f"Share link created for bundle {bundle_id}: {short_url} "
            f"(expires: {expires_at or 'never'})"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(
            f"Failed to create share link for bundle {bundle_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share link: {str(e)}",
        )


@router.delete(
    "/{bundle_id}/share",
    response_model=ShareLinkDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke bundle share link",
    description="Delete and revoke the shareable link for a bundle",
    responses={
        200: {"description": "Share link revoked successfully"},
        400: {"model": ErrorResponse, "description": "Invalid bundle_id"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Bundle or share link not found"},
        500: {"model": ErrorResponse, "description": "Failed to revoke share link"},
    },
)
async def delete_bundle_share_link(
    bundle_id: str,
    token: TokenDep,
) -> ShareLinkDeleteResponse:
    """Revoke and delete the shareable link for a bundle.

    Removes the share link, preventing further access via the link.
    Existing downloads in progress may still complete.

    Args:
        bundle_id: Bundle unique identifier (SHA-256 hash)
        token: Authentication token

    Returns:
        ShareLinkDeleteResponse with deletion status

    Raises:
        HTTPException: On deletion failure or if bundle/link not found
    """
    try:
        # Validate bundle_id format
        if not bundle_id.startswith("sha256:"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid bundle_id format. Must start with 'sha256:'",
            )

        logger.info(f"Revoking share link for bundle: {bundle_id}")

        # Verify bundle exists
        bundle_data = _get_mock_bundle_detail(bundle_id)
        if bundle_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bundle not found: {bundle_id}",
            )

        # TODO: Replace with actual share link deletion
        # In real implementation:
        # 1. Query database for share link by bundle_id
        # 2. Verify share link exists
        # 3. Delete share link record
        # 4. Log revocation event for audit trail
        # 5. Optionally invalidate any cached URLs

        # Mock validation - simulate share link existence check
        # In real implementation, this would query the database
        # For now, we'll assume the link exists if the bundle exists

        response = ShareLinkDeleteResponse(
            success=True,
            bundle_id=bundle_id,
            message="Share link revoked successfully (mock implementation)",
        )

        logger.info(f"Share link revoked for bundle: {bundle_id}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(
            f"Failed to revoke share link for bundle {bundle_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke share link: {str(e)}",
        )
