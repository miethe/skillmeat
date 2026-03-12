"""Concrete repository implementations for SkillMeat's hexagonal architecture.

Each module in this package provides one or more implementations of the
abstract interfaces defined in ``skillmeat.core.interfaces.repositories``.
Infrastructure concerns (filesystem I/O, SQLAlchemy sessions, HTTP calls)
are isolated here so the core domain layer stays clean.

Available implementations
-------------------------
LocalCollectionRepository
    Filesystem-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.ICollectionRepository`.
    Delegates to :class:`~skillmeat.core.collection.CollectionManager`.

LocalArtifactRepository
    Filesystem-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.IArtifactRepository`.
    Delegates to :class:`~skillmeat.core.artifact.ArtifactManager` and
    optionally syncs the DB cache via ``refresh_single_artifact_cache()``
    after mutations.

LocalProjectRepository
    Filesystem + DB-cache implementation of
    :class:`~skillmeat.core.interfaces.repositories.IProjectRepository`.
    Uses ``CacheRepository`` / ``CacheManager`` for persistence and falls
    back to filesystem discovery when no DB is available.

LocalDeploymentRepository
    TOML-file-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.IDeploymentRepository`.
    Delegates to :class:`~skillmeat.core.deployment.DeploymentManager`.

LocalTagRepository
    SQLite-DB-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.ITagRepository`.
    Delegates to :class:`~skillmeat.cache.repositories.TagRepository`.

LocalSettingsRepository
    TOML-file-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.ISettingsRepository`.
    Delegates to :class:`~skillmeat.config.ConfigManager`.

LocalProjectTemplateRepository
    SQLAlchemy-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.IProjectTemplateRepository`.
    Delegates to SQLite DB via ``ProjectTemplate`` / ``TemplateEntity`` ORM
    models and the ``deploy_template_async`` service for deployments.

LocalContextEntityRepository
    DB-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.IContextEntityRepository`.
    Stores context entities as ``Artifact`` rows in the SQLite cache via
    ``get_session()``.

LocalGroupRepository
    DB-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.IGroupRepository`.
    Delegates to SQLite DB via ``Group`` / ``GroupArtifact`` ORM models,
    preserves position ordering, and syncs groups to the collection manifest
    after every mutation.

LocalMarketplaceSourceRepository
    SQLite-DB-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.IMarketplaceSourceRepository`.
    Wraps :class:`~skillmeat.cache.repositories.MarketplaceSourceRepository`
    and :class:`~skillmeat.cache.repositories.MarketplaceCatalogRepository`,
    converting ORM rows to DTOs at the boundary.

EnterpriseMembershipRepository
    PostgreSQL-backed implementation of
    :class:`~skillmeat.core.interfaces.repositories.IMembershipRepository`.
    Queries ``EnterpriseTeamMember`` rows with automatic tenant scoping via
    ``TenantContext`` (matching the ``EnterpriseRepositoryBase`` convention).

Usage::

    from skillmeat.core.repositories import (
        LocalArtifactRepository,
        LocalCollectionRepository,
        LocalDeploymentRepository,
        LocalProjectRepository,
        LocalSettingsRepository,
        LocalTagRepository,
    )
    from skillmeat.core.artifact import ArtifactManager
    from skillmeat.core.collection import CollectionManager
    from skillmeat.core.deployment import DeploymentManager
    from skillmeat.core.path_resolver import ProjectPathResolver

    resolver = ProjectPathResolver()

    artifact_repo = LocalArtifactRepository(
        artifact_manager=ArtifactManager(),
        path_resolver=resolver,
    )

    collection_repo = LocalCollectionRepository(
        collection_manager=CollectionManager(),
        path_resolver=resolver,
    )

    project_repo = LocalProjectRepository(path_resolver=resolver)
    projects = project_repo.list()

    deployment_repo = LocalDeploymentRepository(
        deployment_manager=DeploymentManager(),
        path_resolver=resolver,
    )
    deployments = deployment_repo.list()

    tag_repo = LocalTagRepository()
    tags = tag_repo.list()

    settings_repo = LocalSettingsRepository(path_resolver=resolver)
    settings = settings_repo.get()
"""

from skillmeat.core.repositories.enterprise_membership import (
    EnterpriseMembershipRepository,
)
from skillmeat.core.repositories.local_artifact import LocalArtifactRepository
from skillmeat.core.repositories.local_collection import LocalCollectionRepository
from skillmeat.core.repositories.local_context_entity import LocalContextEntityRepository
from skillmeat.core.repositories.local_deployment import LocalDeploymentRepository
from skillmeat.core.repositories.local_group import LocalGroupRepository
from skillmeat.core.repositories.local_marketplace_source import (
    LocalMarketplaceSourceRepository,
)
from skillmeat.core.repositories.local_project import LocalProjectRepository
from skillmeat.core.repositories.local_project_template import (
    LocalProjectTemplateRepository,
)
from skillmeat.core.repositories.local_settings_repo import LocalSettingsRepository
from skillmeat.core.repositories.local_tag import LocalTagRepository

__all__ = [
    "EnterpriseMembershipRepository",
    "LocalArtifactRepository",
    "LocalCollectionRepository",
    "LocalContextEntityRepository",
    "LocalDeploymentRepository",
    "LocalGroupRepository",
    "LocalMarketplaceSourceRepository",
    "LocalProjectRepository",
    "LocalProjectTemplateRepository",
    "LocalSettingsRepository",
    "LocalTagRepository",
]
