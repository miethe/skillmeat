"""Core services package for SkillMeat.

This package contains business logic services that are used by API routers
and other application layers.
"""

from skillmeat.core.services.template_service import (
    DeploymentResult,
    deploy_template,
    render_content,
    validate_variables,
    ALLOWED_VARIABLES,
)
from skillmeat.core.services.content_hash import (
    compute_content_hash,
    detect_changes,
    read_file_with_hash,
    update_artifact_hash,
    verify_content_integrity,
)
from skillmeat.core.services.context_sync import (
    ContextSyncService,
    SyncConflict,
    SyncResult,
)
from skillmeat.core.services.tag_service import TagService
from skillmeat.core.services.tag_write_service import TagWriteService
from skillmeat.core.services.context_module_service import ContextModuleService
from skillmeat.core.services.context_packer_service import ContextPackerService
from skillmeat.core.services.memory_service import MemoryService
from skillmeat.core.services.custom_color_service import (
    CustomColorService,
    NotFoundError as CustomColorNotFoundError,
)

__all__ = [
    # Template service
    "DeploymentResult",
    "deploy_template",
    "render_content",
    "validate_variables",
    "ALLOWED_VARIABLES",
    # Content hash service
    "compute_content_hash",
    "detect_changes",
    "read_file_with_hash",
    "update_artifact_hash",
    "verify_content_integrity",
    # Context sync service
    "ContextSyncService",
    "SyncConflict",
    "SyncResult",
    # Tag service
    "TagService",
    # Tag write service (filesystem persistence)
    "TagWriteService",
    # Context module service (memory system)
    "ContextModuleService",
    # Context packer service (memory system)
    "ContextPackerService",
    # Memory service (memory system)
    "MemoryService",
    # Custom color service
    "CustomColorService",
    "CustomColorNotFoundError",
]
