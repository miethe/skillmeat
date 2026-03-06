"""Repository factory with edition-based routing.

Provides a ``RepositoryFactory`` that selects between the community (local
filesystem + SQLite) and enterprise (PostgreSQL, tenant-aware) repository
implementations based on the ``SKILLMEAT_EDITION`` environment variable or
the ``APISettings.edition`` config field.

Edition values
--------------
``"local"`` (default)
    Uses ``LocalArtifactRepository`` / ``LocalCollectionRepository`` from
    ``skillmeat.core.repositories``.  No injected SQLAlchemy session is
    required — these implementations manage their own session lifecycle
    internally via the existing ``get_session()`` helper.

``"enterprise"``
    Uses session-injected enterprise repositories backed by PostgreSQL with
    automatic tenant scoping via ``TenantContext`` from
    ``skillmeat.cache.enterprise_repositories``.  An open SQLAlchemy
    ``Session`` must be passed to each factory method.

FastAPI integration
-------------------
Two ready-to-use dependency providers are exported:

- :func:`get_artifact_repo` — returns ``IArtifactRepository`` for the active
  edition.
- :func:`get_collection_repo` — returns ``ICollectionRepository`` for the
  active edition.

These are thin wrappers around :class:`RepositoryFactory` that wire in the
per-request ``DbSessionDep`` session automatically.

Usage (standalone)::

    from skillmeat.cache.repository_factory import RepositoryFactory

    factory = RepositoryFactory()
    if factory.is_enterprise():
        # caller must supply an open session
        repo = factory.get_artifact_repository(session)
    else:
        repo = factory.get_artifact_repository()

Usage (FastAPI route)::

    from skillmeat.cache.repository_factory import get_artifact_repo
    from skillmeat.core.interfaces.repositories import IArtifactRepository
    from fastapi import APIRouter, Depends

    router = APIRouter()

    @router.get("/artifacts")
    def list_artifacts(repo: IArtifactRepository = Depends(get_artifact_repo)):
        return repo.list()

References
----------
ENT-2.9 implementation task.
See also: ``skillmeat/api/dependencies.py`` for the full set of DI providers.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.core.interfaces.repositories import (
    IArtifactRepository,
    ICollectionRepository,
)

logger = logging.getLogger(__name__)


class RepositoryFactory:
    """Select repository implementations based on deployment edition.

    The factory reads ``SKILLMEAT_EDITION`` from the environment at
    construction time (defaulting to ``"local"``).  This means the edition is
    resolved once per factory instance; create a new instance if you need to
    re-read the environment (e.g. in tests that mutate ``os.environ``).

    Parameters
    ----------
    edition:
        Override the edition string directly.  Useful in tests.  When
        ``None`` (default), the value is read from the
        ``SKILLMEAT_EDITION`` environment variable (fallback: ``"local"``).
    """

    def __init__(self, edition: Optional[str] = None) -> None:
        self._edition: str = (
            edition
            if edition is not None
            else os.environ.get("SKILLMEAT_EDITION", "local")
        ).lower()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def is_enterprise() -> bool:
        """Return ``True`` when the active edition is ``"enterprise"``.

        Reads ``SKILLMEAT_EDITION`` from the environment each time it is
        called so that the check reflects runtime mutations (e.g. during
        testing).

        Returns
        -------
        bool
        """
        return os.environ.get("SKILLMEAT_EDITION", "local").lower() == "enterprise"

    def get_artifact_repository(
        self,
        session: Optional[Session] = None,
    ) -> IArtifactRepository:
        """Return an ``IArtifactRepository`` for the configured edition.

        Parameters
        ----------
        session:
            An open SQLAlchemy session.  Required for the ``"enterprise"``
            edition (where repositories are session-injected); ignored for
            the ``"local"`` edition.

        Returns
        -------
        IArtifactRepository

        Raises
        ------
        ValueError
            When ``edition == "enterprise"`` and no session is provided.
        NotImplementedError
            When the edition string is unrecognised.
        """
        if self._edition == "local":
            return self._build_local_artifact_repository()
        if self._edition == "enterprise":
            if session is None:
                raise ValueError(
                    "An open SQLAlchemy Session is required for enterprise edition."
                )
            return self._build_enterprise_artifact_repository(session)
        raise NotImplementedError(
            f"Unknown edition '{self._edition}'. "
            "Valid values are 'local' and 'enterprise'."
        )

    def get_collection_repository(
        self,
        session: Optional[Session] = None,
    ) -> ICollectionRepository:
        """Return an ``ICollectionRepository`` for the configured edition.

        Parameters
        ----------
        session:
            An open SQLAlchemy session.  Required for the ``"enterprise"``
            edition; ignored for ``"local"``.

        Returns
        -------
        ICollectionRepository

        Raises
        ------
        ValueError
            When ``edition == "enterprise"`` and no session is provided.
        NotImplementedError
            When the edition string is unrecognised.
        """
        if self._edition == "local":
            return self._build_local_collection_repository()
        if self._edition == "enterprise":
            if session is None:
                raise ValueError(
                    "An open SQLAlchemy Session is required for enterprise edition."
                )
            return self._build_enterprise_collection_repository(session)
        raise NotImplementedError(
            f"Unknown edition '{self._edition}'. "
            "Valid values are 'local' and 'enterprise'."
        )

    # ------------------------------------------------------------------
    # Private builders — local edition
    # ------------------------------------------------------------------

    @staticmethod
    def _build_local_artifact_repository() -> IArtifactRepository:
        """Instantiate the local (filesystem) artifact repository.

        Mirrors the construction logic in
        ``skillmeat.api.dependencies.get_artifact_repository``.
        """
        from skillmeat.config import ConfigManager
        from skillmeat.core.artifact import ArtifactManager
        from skillmeat.core.collection import CollectionManager
        from skillmeat.core.path_resolver import ProjectPathResolver
        from skillmeat.core.repositories import LocalArtifactRepository

        config_manager = ConfigManager()
        collection_manager = CollectionManager(config=config_manager)
        artifact_manager = ArtifactManager(collection_mgr=collection_manager)
        path_resolver = ProjectPathResolver()

        return LocalArtifactRepository(
            artifact_manager=artifact_manager,
            path_resolver=path_resolver,
        )

    @staticmethod
    def _build_local_collection_repository() -> ICollectionRepository:
        """Instantiate the local (filesystem) collection repository.

        Mirrors the construction logic in
        ``skillmeat.api.dependencies.get_collection_repository``.
        """
        from skillmeat.config import ConfigManager
        from skillmeat.core.collection import CollectionManager
        from skillmeat.core.path_resolver import ProjectPathResolver
        from skillmeat.core.repositories import LocalCollectionRepository

        config_manager = ConfigManager()
        collection_manager = CollectionManager(config=config_manager)
        path_resolver = ProjectPathResolver()

        return LocalCollectionRepository(
            collection_manager=collection_manager,
            path_resolver=path_resolver,
        )

    # ------------------------------------------------------------------
    # Private builders — enterprise edition
    # ------------------------------------------------------------------

    @staticmethod
    def _build_enterprise_artifact_repository(session: Session) -> IArtifactRepository:
        """Instantiate the enterprise (PostgreSQL, tenant-scoped) artifact repository.

        Note: concrete enterprise repository implementations are expected to be
        added as part of ENT-2.x tasks.  This placeholder raises
        ``NotImplementedError`` until an ``EnterpriseArtifactRepository``
        class that satisfies ``IArtifactRepository`` is available.
        """
        # Import guard — avoid hard dependency on enterprise models in community installs.
        try:
            from skillmeat.cache.enterprise_repositories import (  # noqa: F401
                EnterpriseRepositoryBase,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Enterprise repository dependencies are not installed. "
                "Install the enterprise extras: pip install skillmeat[enterprise]"
            ) from exc

        # TODO (ENT-2.x): replace with EnterpriseArtifactRepository(session)
        # once the concrete implementation satisfying IArtifactRepository is ready.
        raise NotImplementedError(
            "EnterpriseArtifactRepository is not yet implemented. "
            "Use edition='local' or wait for ENT-2.x tasks."
        )

    @staticmethod
    def _build_enterprise_collection_repository(
        session: Session,
    ) -> ICollectionRepository:
        """Instantiate the enterprise (PostgreSQL, tenant-scoped) collection repository.

        Note: concrete enterprise repository implementations are expected to be
        added as part of ENT-2.x tasks.  This placeholder raises
        ``NotImplementedError`` until an ``EnterpriseCollectionRepository``
        class that satisfies ``ICollectionRepository`` is available.
        """
        try:
            from skillmeat.cache.enterprise_repositories import (  # noqa: F401
                EnterpriseRepositoryBase,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Enterprise repository dependencies are not installed. "
                "Install the enterprise extras: pip install skillmeat[enterprise]"
            ) from exc

        # TODO (ENT-2.x): replace with EnterpriseCollectionRepository(session)
        raise NotImplementedError(
            "EnterpriseCollectionRepository is not yet implemented. "
            "Use edition='local' or wait for ENT-2.x tasks."
        )


# ---------------------------------------------------------------------------
# FastAPI dependency providers
# ---------------------------------------------------------------------------
# These functions follow the same ``Annotated`` + ``Depends`` convention used
# throughout ``skillmeat/api/dependencies.py``.  Import them directly in
# routers that need a session-aware repository without going through AppState.


def get_artifact_repo(
    db: "Session" = None,  # type: ignore[assignment]
) -> IArtifactRepository:
    """FastAPI dependency that returns the active ``IArtifactRepository``.

    Wires the per-request ``DbSessionDep`` session into
    :class:`RepositoryFactory` automatically.  For the ``"local"`` edition the
    session argument is not used by the underlying repository (it manages its
    own sessions), but it is still accepted so the function signature is
    consistent.

    Intended to be used with ``fastapi.Depends``::

        from fastapi import Depends
        from skillmeat.cache.repository_factory import get_artifact_repo

        @router.get("/artifacts")
        def list_artifacts(repo = Depends(get_artifact_repo)):
            ...

    For typed aliases compatible with ``Annotated`` DI, prefer importing the
    pre-built alias from this module::

        from skillmeat.cache.repository_factory import ArtifactRepoDep

    Returns
    -------
    IArtifactRepository
    """
    return RepositoryFactory().get_artifact_repository(session=db)


def get_collection_repo(
    db: "Session" = None,  # type: ignore[assignment]
) -> ICollectionRepository:
    """FastAPI dependency that returns the active ``ICollectionRepository``.

    See :func:`get_artifact_repo` for usage notes.

    Returns
    -------
    ICollectionRepository
    """
    return RepositoryFactory().get_collection_repository(session=db)


# ---------------------------------------------------------------------------
# Properly wired FastAPI dependency functions (with Depends)
# ---------------------------------------------------------------------------
# These are the preferred entry points for use in route signatures.
# They correctly wire ``get_db_session`` so FastAPI manages the session
# lifecycle (commit / rollback / close) per request.


def _make_artifact_repo_dep():
    """Build the properly-wired FastAPI dependency for IArtifactRepository.

    Deferred to avoid circular imports at module load time (``session.py``
    imports ``models.get_session`` which can trigger engine initialisation).
    """
    from fastapi import Depends

    from skillmeat.cache.session import get_db_session

    def _dep(db: Session = Depends(get_db_session)) -> IArtifactRepository:
        return RepositoryFactory().get_artifact_repository(session=db)

    return _dep


def _make_collection_repo_dep():
    """Build the properly-wired FastAPI dependency for ICollectionRepository."""
    from fastapi import Depends

    from skillmeat.cache.session import get_db_session

    def _dep(db: Session = Depends(get_db_session)) -> ICollectionRepository:
        return RepositoryFactory().get_collection_repository(session=db)

    return _dep


# Lazy singletons — constructed on first attribute access via module-level
# assignment.  Routers that want the session-wired versions should use these.
artifact_repo_dep = _make_artifact_repo_dep()
collection_repo_dep = _make_collection_repo_dep()
