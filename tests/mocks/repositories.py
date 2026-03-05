"""In-memory mock repository implementations.

Each class implements the corresponding interface from
``skillmeat.core.interfaces.repositories`` using plain Python dicts for
storage.  No filesystem I/O, no database — suitable for fast unit tests.

Design choices:
- ``reset()`` clears all stored data; call it in a ``pytest`` fixture or
  ``setUp`` method to isolate tests.
- Constructors accept ``initial_*`` keyword arguments for pre-seeding data.
- Mutations are applied to mutable copies of frozen DTOs via
  ``dataclasses.replace()``.
- Methods that specify ``Raises: KeyError`` in the interface do raise
  ``KeyError`` here so tests can verify that callers handle missing records.
- ``search()`` performs a simple case-insensitive substring match on
  ``artifact.name`` and ``artifact.id`` — sufficient for test assertions.
- Tag associations are stored independently of the artifact DTOs so that
  ``get_tags`` / ``set_tags`` can be tested without rebuilding artifacts.
"""

from __future__ import annotations

import dataclasses
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import (
    ArtifactDTO,
    CategoryDTO,
    CollectionDTO,
    CollectionMembershipDTO,
    DeploymentDTO,
    EntityTypeConfigDTO,
    ProjectDTO,
    SettingsDTO,
    TagDTO,
)
from skillmeat.core.interfaces.repositories import (
    IArtifactRepository,
    ICollectionRepository,
    IDeploymentRepository,
    IProjectRepository,
    ISettingsRepository,
    ITagRepository,
)

__all__ = [
    "MockArtifactRepository",
    "MockProjectRepository",
    "MockCollectionRepository",
    "MockDeploymentRepository",
    "MockTagRepository",
    "MockSettingsRepository",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def _slugify(name: str) -> str:
    """Convert *name* to a kebab-case slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _apply_dict_filters(items: list[Any], filters: dict[str, Any] | None) -> list[Any]:
    """Return *items* whose attributes match every key/value in *filters*.

    Unknown filter keys are silently ignored so tests can pass rich filter
    dicts without the mock raising AttributeError.
    """
    if not filters:
        return items
    result = []
    for item in items:
        match = True
        for key, expected in filters.items():
            actual = getattr(item, key, None)
            if actual != expected:
                match = False
                break
        if match:
            result.append(item)
    return result


# =============================================================================
# MockArtifactRepository
# =============================================================================


class MockArtifactRepository(IArtifactRepository):
    """In-memory implementation of :class:`IArtifactRepository`.

    Args:
        initial_artifacts: Optional list of :class:`ArtifactDTO` objects to
            pre-seed the store.  Each artifact's ``id`` is used as the
            storage key.
    """

    def __init__(
        self,
        initial_artifacts: list[ArtifactDTO] | None = None,
    ) -> None:
        # Primary store: id -> ArtifactDTO
        self._store: dict[str, ArtifactDTO] = {}
        # UUID index: uuid -> id (for get_by_uuid)
        self._uuid_index: dict[str, str] = {}
        # Tag associations: artifact_id -> set[tag_id]
        self._artifact_tags: dict[str, set[str]] = {}
        # In-memory content store: artifact_id -> str
        self._content: dict[str, str] = {}

        for artifact in (initial_artifacts or []):
            self._store[artifact.id] = artifact
            if artifact.uuid:
                self._uuid_index[artifact.uuid] = artifact.id

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stored data.  Call between tests to ensure isolation."""
        self._store.clear()
        self._uuid_index.clear()
        self._artifact_tags.clear()
        self._content.clear()

    def seed(self, artifact: ArtifactDTO) -> None:
        """Add *artifact* to the store without going through :meth:`create`."""
        self._store[artifact.id] = artifact
        if artifact.uuid:
            self._uuid_index[artifact.uuid] = artifact.id

    # ------------------------------------------------------------------
    # IArtifactRepository implementation
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> ArtifactDTO | None:
        return self._store.get(id)

    def get_by_uuid(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
    ) -> ArtifactDTO | None:
        artifact_id = self._uuid_index.get(uuid)
        if artifact_id is None:
            return None
        return self._store.get(artifact_id)

    def list(
        self,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        items = list(self._store.values())
        items = _apply_dict_filters(items, filters)
        return items[offset : offset + limit]

    def count(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> int:
        items = list(self._store.values())
        items = _apply_dict_filters(items, filters)
        return len(items)

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        query_lower = query.lower()
        matches = [
            a
            for a in self._store.values()
            if query_lower in a.name.lower() or query_lower in a.id.lower()
        ]
        return _apply_dict_filters(matches, filters)

    def create(
        self,
        dto: ArtifactDTO,
        ctx: RequestContext | None = None,
    ) -> ArtifactDTO:
        now = _now_iso()
        artifact_uuid = dto.uuid or uuid.uuid4().hex
        stored = dataclasses.replace(
            dto,
            uuid=artifact_uuid,
            created_at=dto.created_at or now,
            updated_at=dto.updated_at or now,
        )
        self._store[stored.id] = stored
        self._uuid_index[artifact_uuid] = stored.id
        return stored

    def update(
        self,
        id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> ArtifactDTO:
        existing = self._store.get(id)
        if existing is None:
            raise KeyError(f"Artifact '{id}' not found")
        updated = dataclasses.replace(
            existing,
            **{k: v for k, v in updates.items() if k in existing.__dataclass_fields__},
            updated_at=_now_iso(),
        )
        self._store[id] = updated
        if updated.uuid:
            self._uuid_index[updated.uuid] = id
        return updated

    def delete(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        artifact = self._store.pop(id, None)
        if artifact is None:
            return False
        if artifact.uuid:
            self._uuid_index.pop(artifact.uuid, None)
        self._artifact_tags.pop(id, None)
        self._content.pop(id, None)
        return True

    def get_content(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> str:
        if id not in self._store:
            raise KeyError(f"Artifact '{id}' not found")
        return self._content.get(id, "")

    def update_content(
        self,
        id: str,
        content: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        if id not in self._store:
            raise KeyError(f"Artifact '{id}' not found")
        self._content[id] = content
        return True

    def get_tags(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> list[TagDTO]:
        # Returns TagDTO stubs; callers who need full TagDTO must use
        # MockTagRepository and join the data in tests.
        tag_ids = self._artifact_tags.get(id, set())
        return [
            TagDTO(id=tid, name=tid, slug=_slugify(tid))
            for tid in sorted(tag_ids)
        ]

    def set_tags(
        self,
        id: str,
        tag_ids: list[str],
        ctx: RequestContext | None = None,
    ) -> bool:
        self._artifact_tags[id] = set(tag_ids)
        return True

    # ------------------------------------------------------------------
    # UUID resolution (stub implementations)
    # ------------------------------------------------------------------

    def resolve_uuid_by_type_name(
        self,
        artifact_type: str,
        name: str,
        ctx: RequestContext | None = None,
    ) -> str | None:
        return None

    def get_ids_by_uuids(
        self,
        uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> dict[str, str]:
        return {}

    def batch_resolve_uuids(
        self,
        artifacts: list[tuple[str, str]],
        ctx: RequestContext | None = None,
    ) -> dict[tuple[str, str], str]:
        return {}

    # ------------------------------------------------------------------
    # Collection-context queries (stub implementations)
    # ------------------------------------------------------------------

    def get_with_collection_context(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
    ) -> ArtifactDTO | None:
        return None

    def get_collection_memberships(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
    ) -> list[CollectionMembershipDTO]:
        return []

    def get_collection_description(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
    ) -> str | None:
        return None

    # ------------------------------------------------------------------
    # Deduplication cluster queries (stub implementations)
    # ------------------------------------------------------------------

    def get_duplicate_cluster_members(
        self,
        cluster_id: str,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        return []

    # ------------------------------------------------------------------
    # Existence and type queries (stub implementations)
    # ------------------------------------------------------------------

    def validate_exists(
        self,
        uuid: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        return False

    def get_by_type(
        self,
        artifact_type: str,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        return []

    # ------------------------------------------------------------------
    # Collection-level mutations (stub implementations)
    # ------------------------------------------------------------------

    def update_collection_tags(
        self,
        uuid: str,
        tags: list[str],
        ctx: RequestContext | None = None,
    ) -> None:
        return None


# =============================================================================
# MockProjectRepository
# =============================================================================


class MockProjectRepository(IProjectRepository):
    """In-memory implementation of :class:`IProjectRepository`.

    Args:
        initial_projects: Optional list of :class:`ProjectDTO` objects to
            pre-seed the store.
        initial_project_artifacts: Optional mapping of ``project_id ->
            list[ArtifactDTO]`` for pre-seeding :meth:`get_artifacts`.
    """

    def __init__(
        self,
        initial_projects: list[ProjectDTO] | None = None,
        initial_project_artifacts: dict[str, list[ArtifactDTO]] | None = None,
    ) -> None:
        self._store: dict[str, ProjectDTO] = {}
        # project_id -> list of deployed ArtifactDTOs
        self._project_artifacts: dict[str, list[ArtifactDTO]] = {}

        for project in (initial_projects or []):
            self._store[project.id] = project
        if initial_project_artifacts:
            self._project_artifacts.update(initial_project_artifacts)

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stored data."""
        self._store.clear()
        self._project_artifacts.clear()

    def seed(self, project: ProjectDTO) -> None:
        """Add *project* without going through :meth:`create`."""
        self._store[project.id] = project

    def seed_artifacts(self, project_id: str, artifacts: list[ArtifactDTO]) -> None:
        """Pre-populate the artifact list for a project."""
        self._project_artifacts[project_id] = list(artifacts)

    # ------------------------------------------------------------------
    # IProjectRepository implementation
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO | None:
        return self._store.get(id)

    def list(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[ProjectDTO]:
        items = list(self._store.values())
        return _apply_dict_filters(items, filters)

    def create(
        self,
        dto: ProjectDTO,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO:
        now = _now_iso()
        stored = dataclasses.replace(
            dto,
            created_at=dto.created_at or now,
            updated_at=dto.updated_at or now,
        )
        self._store[stored.id] = stored
        return stored

    def update(
        self,
        id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> ProjectDTO:
        existing = self._store.get(id)
        if existing is None:
            raise KeyError(f"Project '{id}' not found")
        updated = dataclasses.replace(
            existing,
            **{k: v for k, v in updates.items() if k in existing.__dataclass_fields__},
            updated_at=_now_iso(),
        )
        self._store[id] = updated
        return updated

    def delete(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        project = self._store.pop(id, None)
        if project is None:
            return False
        self._project_artifacts.pop(id, None)
        return True

    def get_artifacts(
        self,
        project_id: str,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        return list(self._project_artifacts.get(project_id, []))

    def refresh(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> ProjectDTO:
        existing = self._store.get(id)
        if existing is None:
            raise KeyError(f"Project '{id}' not found")
        refreshed = dataclasses.replace(
            existing,
            last_fetched=_now_iso(),
            updated_at=_now_iso(),
        )
        self._store[id] = refreshed
        return refreshed


# =============================================================================
# MockCollectionRepository
# =============================================================================


class MockCollectionRepository(ICollectionRepository):
    """In-memory implementation of :class:`ICollectionRepository`.

    Args:
        initial_collections: Optional list of :class:`CollectionDTO` objects.
            The first entry (if any) becomes the default ``get()`` result.
        initial_collection_artifacts: Optional mapping of
            ``collection_id -> list[ArtifactDTO]``.
    """

    def __init__(
        self,
        initial_collections: list[CollectionDTO] | None = None,
        initial_collection_artifacts: dict[str, list[ArtifactDTO]] | None = None,
    ) -> None:
        self._store: dict[str, CollectionDTO] = {}
        self._collection_artifacts: dict[str, list[ArtifactDTO]] = {}

        for collection in (initial_collections or []):
            self._store[collection.id] = collection
        if initial_collection_artifacts:
            self._collection_artifacts.update(initial_collection_artifacts)

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stored data."""
        self._store.clear()
        self._collection_artifacts.clear()

    def seed(self, collection: CollectionDTO) -> None:
        """Add *collection* to the store."""
        self._store[collection.id] = collection

    def seed_artifacts(
        self, collection_id: str, artifacts: list[ArtifactDTO]
    ) -> None:
        """Pre-populate the artifact list for a collection."""
        self._collection_artifacts[collection_id] = list(artifacts)

    # ------------------------------------------------------------------
    # ICollectionRepository implementation
    # ------------------------------------------------------------------

    def get(
        self,
        ctx: RequestContext | None = None,
    ) -> CollectionDTO | None:
        """Return the first stored collection (simulates the active collection)."""
        if not self._store:
            return None
        return next(iter(self._store.values()))

    def get_by_id(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> CollectionDTO | None:
        return self._store.get(id)

    def list(
        self,
        ctx: RequestContext | None = None,
    ) -> list[CollectionDTO]:
        return list(self._store.values())

    def get_stats(
        self,
        ctx: RequestContext | None = None,
    ) -> dict[str, Any]:
        active = self.get(ctx)
        artifact_count = 0
        if active:
            artifact_count = len(self._collection_artifacts.get(active.id, []))
        return {
            "artifact_count": artifact_count,
            "total_size_bytes": 0,
            "last_synced": None,
        }

    def refresh(
        self,
        ctx: RequestContext | None = None,
    ) -> CollectionDTO:
        active = self.get(ctx)
        if active is None:
            raise ValueError("No active collection to refresh")
        refreshed = dataclasses.replace(
            active,
            updated_at=_now_iso(),
            artifact_count=len(self._collection_artifacts.get(active.id, [])),
        )
        self._store[active.id] = refreshed
        return refreshed

    def get_artifacts(
        self,
        collection_id: str,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
        ctx: RequestContext | None = None,
    ) -> list[ArtifactDTO]:
        items = list(self._collection_artifacts.get(collection_id, []))
        items = _apply_dict_filters(items, filters)
        return items[offset : offset + limit]

    # ------------------------------------------------------------------
    # Mutations (stub implementations)
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        description: str | None = None,
        ctx: RequestContext | None = None,
    ) -> CollectionDTO:
        now = _now_iso()
        collection_id = uuid.uuid4().hex
        dto = CollectionDTO(
            id=collection_id,
            name=name,
            description=description,
            artifact_count=0,
            created_at=now,
            updated_at=now,
        )
        self._store[collection_id] = dto
        return dto

    def update(
        self,
        collection_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> CollectionDTO:
        existing = self._store.get(collection_id)
        if existing is None:
            raise KeyError(f"Collection '{collection_id}' not found")
        updated = dataclasses.replace(
            existing,
            **{k: v for k, v in updates.items() if k in existing.__dataclass_fields__},
            updated_at=_now_iso(),
        )
        self._store[collection_id] = updated
        return updated

    def delete(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        if collection_id not in self._store:
            raise KeyError(f"Collection '{collection_id}' not found")
        self._store.pop(collection_id)
        self._collection_artifacts.pop(collection_id, None)

    def add_artifacts(
        self,
        collection_id: str,
        artifact_uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> None:
        if collection_id not in self._store:
            raise KeyError(f"Collection '{collection_id}' not found")
        # Stub: no-op (test helpers can use seed_artifacts instead)

    def remove_artifact(
        self,
        collection_id: str,
        artifact_uuid: str,
        ctx: RequestContext | None = None,
    ) -> None:
        if collection_id not in self._store:
            raise KeyError(f"Collection '{collection_id}' not found")
        # Stub: no-op

    # ------------------------------------------------------------------
    # Entity management (stub implementations)
    # ------------------------------------------------------------------

    def list_entities(
        self,
        collection_id: str,
        entity_type: str | None = None,
        ctx: RequestContext | None = None,
    ) -> list[Any]:
        return []

    def add_entity(
        self,
        collection_id: str,
        entity_type: str,
        entity_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        return None

    def remove_entity(
        self,
        collection_id: str,
        entity_type: str,
        entity_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        return None

    def migrate_to_default(
        self,
        collection_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        return None


# =============================================================================
# MockDeploymentRepository
# =============================================================================


class MockDeploymentRepository(IDeploymentRepository):
    """In-memory implementation of :class:`IDeploymentRepository`.

    Args:
        initial_deployments: Optional list of :class:`DeploymentDTO` objects
            to pre-seed the store.
    """

    def __init__(
        self,
        initial_deployments: list[DeploymentDTO] | None = None,
    ) -> None:
        self._store: dict[str, DeploymentDTO] = {}

        for deployment in (initial_deployments or []):
            self._store[deployment.id] = deployment

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stored data."""
        self._store.clear()

    def seed(self, deployment: DeploymentDTO) -> None:
        """Add *deployment* to the store without going through :meth:`deploy`."""
        self._store[deployment.id] = deployment

    # ------------------------------------------------------------------
    # IDeploymentRepository implementation
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> DeploymentDTO | None:
        return self._store.get(id)

    def list(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[DeploymentDTO]:
        items = list(self._store.values())
        return _apply_dict_filters(items, filters)

    def deploy(
        self,
        artifact_id: str,
        project_id: str,
        options: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> DeploymentDTO:
        opts = options or {}
        deployment_id = f"{artifact_id}@{project_id}"

        # Check for conflict when overwrite is not permitted
        if deployment_id in self._store and not opts.get("overwrite", False):
            raise ValueError(
                f"Artifact '{artifact_id}' is already deployed to project "
                f"'{project_id}'.  Pass overwrite=True to replace it."
            )

        # Derive artifact name and type from the id ("type:name")
        parts = artifact_id.split(":", 1)
        artifact_type = parts[0] if len(parts) == 2 else "unknown"
        artifact_name = parts[1] if len(parts) == 2 else artifact_id

        dto = DeploymentDTO(
            id=deployment_id,
            artifact_id=artifact_id,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            project_id=project_id,
            scope=opts.get("scope", "local"),
            status="deployed",
            deployed_at=_now_iso(),
            target_path=opts.get("dest_path"),
            deployment_profile_id=opts.get("profile_id"),
        )
        self._store[deployment_id] = dto
        return dto

    def undeploy(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        deployment = self._store.pop(id, None)
        return deployment is not None

    def get_status(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> str:
        deployment = self._store.get(id)
        if deployment is None:
            raise KeyError(f"Deployment '{id}' not found")
        return deployment.status

    def get_by_artifact(
        self,
        artifact_id: str,
        ctx: RequestContext | None = None,
    ) -> list[DeploymentDTO]:
        return [d for d in self._store.values() if d.artifact_id == artifact_id]


# =============================================================================
# MockTagRepository
# =============================================================================


class MockTagRepository(ITagRepository):
    """In-memory implementation of :class:`ITagRepository`.

    Args:
        initial_tags: Optional list of :class:`TagDTO` objects to pre-seed.
    """

    def __init__(
        self,
        initial_tags: list[TagDTO] | None = None,
    ) -> None:
        # id -> TagDTO
        self._store: dict[str, TagDTO] = {}
        # slug -> id (for get_by_slug)
        self._slug_index: dict[str, str] = {}
        # tag_id -> set[artifact_id]
        self._assignments: dict[str, set[str]] = {}

        for tag in (initial_tags or []):
            self._store[tag.id] = tag
            self._slug_index[tag.slug] = tag.id

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stored data."""
        self._store.clear()
        self._slug_index.clear()
        self._assignments.clear()

    def seed(self, tag: TagDTO) -> None:
        """Add *tag* to the store without going through :meth:`create`."""
        self._store[tag.id] = tag
        self._slug_index[tag.slug] = tag.id

    # ------------------------------------------------------------------
    # ITagRepository implementation
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> TagDTO | None:
        return self._store.get(id)

    def get_by_slug(
        self,
        slug: str,
        ctx: RequestContext | None = None,
    ) -> TagDTO | None:
        tag_id = self._slug_index.get(slug)
        if tag_id is None:
            return None
        return self._store.get(tag_id)

    def list(
        self,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[TagDTO]:
        items = list(self._store.values())
        # Support substring match on "name" filter key as a convenience
        if filters and "name" in filters:
            name_filter = filters["name"].lower()
            items = [t for t in items if name_filter in t.name.lower()]
            remaining = {k: v for k, v in filters.items() if k != "name"}
            return _apply_dict_filters(items, remaining or None)
        return _apply_dict_filters(items, filters)

    def create(
        self,
        name: str,
        color: str | None = None,
        ctx: RequestContext | None = None,
    ) -> TagDTO:
        slug = _slugify(name)
        # Check for duplicate slug
        if slug in self._slug_index:
            raise ValueError(f"Tag with slug '{slug}' already exists")
        tag_id = uuid.uuid4().hex
        now = _now_iso()
        tag = TagDTO(
            id=tag_id,
            name=name,
            slug=slug,
            color=color,
            artifact_count=0,
            created_at=now,
            updated_at=now,
        )
        self._store[tag_id] = tag
        self._slug_index[slug] = tag_id
        return tag

    def update(
        self,
        id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> TagDTO:
        existing = self._store.get(id)
        if existing is None:
            raise KeyError(f"Tag '{id}' not found")
        # Handle slug re-indexing if name changes
        new_name = updates.get("name", existing.name)
        new_slug = _slugify(new_name) if "name" in updates else existing.slug
        if new_slug != existing.slug:
            self._slug_index.pop(existing.slug, None)
            self._slug_index[new_slug] = id
        updated = dataclasses.replace(
            existing,
            **{k: v for k, v in updates.items() if k in existing.__dataclass_fields__},
            slug=new_slug,
            updated_at=_now_iso(),
        )
        self._store[id] = updated
        return updated

    def delete(
        self,
        id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        tag = self._store.pop(id, None)
        if tag is None:
            return False
        self._slug_index.pop(tag.slug, None)
        self._assignments.pop(id, None)
        return True

    def assign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        if tag_id not in self._store:
            raise KeyError(f"Tag '{tag_id}' not found")
        self._assignments.setdefault(tag_id, set()).add(artifact_id)
        # Update artifact_count on the stored TagDTO
        count = len(self._assignments[tag_id])
        self._store[tag_id] = dataclasses.replace(
            self._store[tag_id], artifact_count=count
        )
        return True

    def unassign(
        self,
        tag_id: str,
        artifact_id: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        assignments = self._assignments.get(tag_id)
        if assignments is None or artifact_id not in assignments:
            return False
        assignments.discard(artifact_id)
        count = len(assignments)
        self._store[tag_id] = dataclasses.replace(
            self._store[tag_id], artifact_count=count
        )
        return True

    # ------------------------------------------------------------------
    # Additional query helper (not in interface — for test convenience)
    # ------------------------------------------------------------------

    def get_artifact_ids(self, tag_id: str) -> set[str]:
        """Return all artifact IDs associated with *tag_id*."""
        return set(self._assignments.get(tag_id, set()))


# =============================================================================
# MockSettingsRepository
# =============================================================================


class MockSettingsRepository(ISettingsRepository):
    """In-memory implementation of :class:`ISettingsRepository`.

    Args:
        initial_settings: Optional :class:`SettingsDTO` to start with.
            Defaults to a fresh ``SettingsDTO()`` with all defaults.
        valid_github_tokens: Optional set of token strings that
            :meth:`validate_github_token` should consider valid.  When
            ``None`` (default), **all** tokens are accepted.
    """

    def __init__(
        self,
        initial_settings: SettingsDTO | None = None,
        valid_github_tokens: set[str] | None = None,
    ) -> None:
        self._settings: SettingsDTO = initial_settings or SettingsDTO()
        # None means "accept any token" (useful for most tests)
        self._valid_tokens: set[str] | None = valid_github_tokens

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset settings to defaults and clear the valid-token list."""
        self._settings = SettingsDTO()
        self._valid_tokens = None

    def set_valid_tokens(self, tokens: set[str] | None) -> None:
        """Override the set of tokens that :meth:`validate_github_token` accepts.

        Pass ``None`` to accept all tokens (the default behaviour).
        """
        self._valid_tokens = tokens

    # ------------------------------------------------------------------
    # ISettingsRepository implementation
    # ------------------------------------------------------------------

    def get(
        self,
        ctx: RequestContext | None = None,
    ) -> SettingsDTO:
        return self._settings

    def update(
        self,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> SettingsDTO:
        known_fields = {f.name for f in dataclasses.fields(SettingsDTO)}
        known_updates = {k: v for k, v in updates.items() if k in known_fields}
        extra_updates = {k: v for k, v in updates.items() if k not in known_fields}

        merged_extra = dict(self._settings.extra)
        merged_extra.update(extra_updates)

        self._settings = dataclasses.replace(
            self._settings,
            **known_updates,
            extra=merged_extra,
        )
        return self._settings

    def validate_github_token(
        self,
        token: str,
        ctx: RequestContext | None = None,
    ) -> bool:
        if self._valid_tokens is None:
            # Accept any non-empty token by default
            return bool(token)
        return token in self._valid_tokens

    # ------------------------------------------------------------------
    # Entity type configuration (stub implementations)
    # ------------------------------------------------------------------

    def list_entity_type_configs(
        self,
        ctx: RequestContext | None = None,
    ) -> list[EntityTypeConfigDTO]:
        return []

    def create_entity_type_config(
        self,
        entity_type: str,
        display_name: str,
        description: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        ctx: RequestContext | None = None,
    ) -> EntityTypeConfigDTO:
        now = _now_iso()
        return EntityTypeConfigDTO(
            id=uuid.uuid4().hex,
            entity_type=entity_type,
            display_name=display_name,
            description=description,
            icon=icon,
            color=color,
            is_system=False,
            created_at=now,
            updated_at=now,
        )

    def update_entity_type_config(
        self,
        config_id: str,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> EntityTypeConfigDTO:
        raise KeyError(f"EntityTypeConfig '{config_id}' not found")

    def delete_entity_type_config(
        self,
        config_id: str,
        ctx: RequestContext | None = None,
    ) -> None:
        return None

    # ------------------------------------------------------------------
    # Category management (stub implementations)
    # ------------------------------------------------------------------

    def list_categories(
        self,
        entity_type: str | None = None,
        ctx: RequestContext | None = None,
    ) -> list[CategoryDTO]:
        return []

    def create_category(
        self,
        name: str,
        entity_type: str | None = None,
        description: str | None = None,
        color: str | None = None,
        ctx: RequestContext | None = None,
    ) -> CategoryDTO:
        now = _now_iso()
        return CategoryDTO(
            id=uuid.uuid4().hex,
            name=name,
            entity_type=entity_type,
            description=description,
            color=color,
            created_at=now,
            updated_at=now,
        )
