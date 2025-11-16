"""Bundle import/export API endpoints.

Provides REST API for importing and validating artifact bundles.
"""

import logging
import tempfile
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
    BundleImportRequest,
    BundleImportResponse,
    BundleValidationResponse,
    ImportedArtifactResponse,
    ValidationIssueResponse,
)
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.core.collection import CollectionManager
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
