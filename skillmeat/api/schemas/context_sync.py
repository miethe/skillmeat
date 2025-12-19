"""Context sync API request/response schemas.

Pydantic models for context entity synchronization endpoints.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SyncPullRequest(BaseModel):
    """Request schema for pulling changes from project to collection.

    Attributes:
        project_path: Absolute path to project directory
        entity_ids: Optional list of entity IDs to pull (pulls all if None)
    """

    project_path: str = Field(
        ...,
        description="Absolute path to project directory",
        examples=["/path/to/project"],
    )
    entity_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of entity IDs to pull (pulls all if None)",
        examples=[["spec_file:api-patterns", "rule_file:debugging"]],
    )


class SyncPushRequest(BaseModel):
    """Request schema for pushing collection changes to project.

    Attributes:
        project_path: Absolute path to project directory
        entity_ids: Optional list of entity IDs to push (pushes all if None)
        overwrite: If True, push even if file modified locally (force)
    """

    project_path: str = Field(
        ...,
        description="Absolute path to project directory",
        examples=["/path/to/project"],
    )
    entity_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of entity IDs to push (pushes all if None)",
        examples=[["spec_file:api-patterns"]],
    )
    overwrite: bool = Field(
        False,
        description="If True, push even if file modified locally (force)",
    )


class SyncConflictResponse(BaseModel):
    """Response schema for sync conflict information.

    Attributes:
        entity_id: Entity identifier
        entity_name: Entity name
        entity_type: Entity type (spec_file, rule_file, etc.)
        collection_hash: Hash in collection
        deployed_hash: Hash of deployed file
        collection_content: Current content in collection
        deployed_content: Current content in deployed file
        collection_path: Path to entity in collection
        deployed_path: Path to deployed file in project
        change_origin: Origin of the change (optional)
        baseline_hash: Hash at deployment time (baseline for three-way merge)
    """

    entity_id: str = Field(..., description="Entity identifier")
    entity_name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    collection_hash: str = Field(..., description="Content hash in collection")
    deployed_hash: str = Field(..., description="Content hash of deployed file")
    collection_content: str = Field(..., description="Current content in collection")
    deployed_content: str = Field(..., description="Current content in deployed file")
    collection_path: str = Field(..., description="Path to entity in collection")
    deployed_path: str = Field(..., description="Path to deployed file in project")
    change_origin: Optional[str] = Field(
        default=None,
        description="Origin of the change (deployment/sync/local_modification)",
    )
    baseline_hash: Optional[str] = Field(
        default=None,
        description="Hash at deployment time (baseline for three-way merge)",
    )


class SyncResultResponse(BaseModel):
    """Response schema for sync operation result.

    Attributes:
        entity_id: Entity identifier
        entity_name: Entity name
        action: Action performed (pulled, pushed, skipped, conflict, resolved)
        message: Human-readable status message
    """

    entity_id: str = Field(..., description="Entity identifier")
    entity_name: str = Field(..., description="Entity name")
    action: str = Field(
        ...,
        description="Action performed",
        examples=["pulled", "pushed", "skipped", "conflict", "resolved"],
    )
    message: str = Field(..., description="Human-readable status message")


class SyncStatusResponse(BaseModel):
    """Response schema for sync status information.

    Attributes:
        modified_in_project: Entity IDs modified in project
        modified_in_collection: Entity IDs modified in collection
        conflicts: List of sync conflicts
    """

    modified_in_project: List[str] = Field(
        ...,
        description="Entity IDs modified in project",
        examples=[["spec_file:api-patterns"]],
    )
    modified_in_collection: List[str] = Field(
        ...,
        description="Entity IDs modified in collection",
        examples=[["rule_file:debugging"]],
    )
    conflicts: List[SyncConflictResponse] = Field(
        ..., description="List of sync conflicts"
    )


class SyncResolveRequest(BaseModel):
    """Request schema for resolving sync conflicts.

    Attributes:
        project_path: Absolute path to project directory
        entity_id: Entity identifier to resolve
        resolution: Resolution strategy (keep_local, keep_remote, merge)
        merged_content: Required if resolution is "merge"
    """

    project_path: str = Field(
        ...,
        description="Absolute path to project directory",
        examples=["/path/to/project"],
    )
    entity_id: str = Field(
        ...,
        description="Entity identifier to resolve",
        examples=["spec_file:api-patterns"],
    )
    resolution: Literal["keep_local", "keep_remote", "merge"] = Field(
        ...,
        description="Resolution strategy",
    )
    merged_content: Optional[str] = Field(
        None,
        description="Required if resolution is 'merge'",
    )
