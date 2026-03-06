"""Local TOML-backed implementation of the ISettingsRepository interface.

Settings are stored in ``~/.skillmeat/config.toml`` and managed by
:class:`~skillmeat.config.ConfigManager`.  This repository provides the
hexagonal-architecture-compatible interface over that existing mechanism,
converting between the flat TOML config structure and the
:class:`~skillmeat.core.interfaces.dtos.SettingsDTO` contract.

The ``validate_github_token`` method performs a lightweight call to the
GitHub API (via the :class:`~skillmeat.core.github_client.GitHubClient`
wrapper) to verify that the supplied token is valid.  On import failure or
network error it degrades gracefully and returns ``False``.

Design notes:
- Constructor takes a ``ProjectPathResolver`` for forward-compatibility (e.g.
  future collection-path resolution); at present only ``ConfigManager`` is
  used.
- No I/O at construction time: the config file is read lazily on first
  method call.
- Python 3.9+ compatible (no ``X | Y`` union syntax in runtime code).
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from skillmeat.config import ConfigManager
from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import CategoryDTO, EntityTypeConfigDTO, SettingsDTO
from skillmeat.core.interfaces.repositories import ISettingsRepository
from skillmeat.core.path_resolver import ProjectPathResolver

logger = logging.getLogger(__name__)

__all__ = ["LocalSettingsRepository"]


def _slugify(text: str) -> str:
    """Convert *text* to a URL-safe kebab-case slug.

    Lowercases, replaces spaces and underscores with hyphens, and strips any
    character that is not alphanumeric or a hyphen.

    Args:
        text: Human-readable string to slugify.

    Returns:
        URL-safe slug string.
    """
    import re

    slug = text.lower().strip()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "category"


# TOML config key that stores the GitHub Personal Access Token.
_GITHUB_TOKEN_KEY = "settings.github-token"

# TOML key for the user's chosen default scope.
_DEFAULT_SCOPE_KEY = "settings.default-scope"

# TOML key for the active collection path (when overridden from default).
_COLLECTION_PATH_KEY = "settings.collection-path"

# TOML key for the edition identifier (community / pro / etc.).
_EDITION_KEY = "settings.edition"

# TOML key for the artifact search indexing mode.
_INDEXING_MODE_KEY = "artifact_search.indexing_mode"


def _read_settings_dto(config: ConfigManager, resolver: ProjectPathResolver) -> SettingsDTO:
    """Build a :class:`SettingsDTO` from the current TOML configuration.

    All TOML entries that do not map to known DTO fields are collected into
    ``extra`` so no information is silently discarded.

    Args:
        config: Initialised :class:`~skillmeat.config.ConfigManager`.
        resolver: :class:`~skillmeat.core.path_resolver.ProjectPathResolver`
            used to determine the default collection path.

    Returns:
        Fully populated :class:`SettingsDTO`.
    """
    github_token: Optional[str] = config.get(_GITHUB_TOKEN_KEY)

    # Mask the token in the DTO — only expose whether it is set.
    # Callers that need the raw token must read it from ConfigManager directly.
    masked_token: Optional[str] = None
    if github_token:
        visible = github_token[:4] if len(github_token) > 4 else github_token
        masked_token = visible + "*" * (len(github_token) - len(visible))

    raw_collection_path: Optional[str] = config.get(_COLLECTION_PATH_KEY)
    if not raw_collection_path:
        raw_collection_path = str(resolver.collection_root())

    default_scope: str = config.get(_DEFAULT_SCOPE_KEY, "user") or "user"
    edition: str = config.get(_EDITION_KEY, "community") or "community"
    indexing_mode: str = config.get_indexing_mode()

    # Collect the full TOML tree, flatten top-level, gather unknowns.
    full_config: Dict[str, Any] = {}
    try:
        full_config = config.read()
    except Exception:
        pass

    known_sections = {"settings", "artifact_search", "analytics", "scoring", "similarity", "platform"}
    extra: Dict[str, Any] = {
        section: values
        for section, values in full_config.items()
        if section not in known_sections
    }

    return SettingsDTO(
        github_token=masked_token,
        collection_path=raw_collection_path,
        default_scope=default_scope,
        edition=edition,
        indexing_mode=indexing_mode,
        extra=extra,
    )


class LocalSettingsRepository(ISettingsRepository):
    """``ISettingsRepository`` backed by ``~/.skillmeat/config.toml``.

    Wraps :class:`~skillmeat.config.ConfigManager` to expose settings through
    the hexagonal-architecture interface contract.

    Args:
        path_resolver: :class:`~skillmeat.core.path_resolver.ProjectPathResolver`
            used for default collection-path resolution.
        config_manager: Optional pre-configured
            :class:`~skillmeat.config.ConfigManager`.  When ``None``, a
            default instance pointing at ``~/.skillmeat/`` is created.
    """

    def __init__(
        self,
        path_resolver: ProjectPathResolver,
        config_manager: Optional[ConfigManager] = None,
    ) -> None:
        self._resolver = path_resolver
        self._config = config_manager or ConfigManager()

    # ------------------------------------------------------------------
    # ISettingsRepository
    # ------------------------------------------------------------------

    def get(
        self,
        ctx: Optional[RequestContext] = None,
    ) -> SettingsDTO:
        """Return the current application settings snapshot.

        Reads ``~/.skillmeat/config.toml`` on every call to ensure freshness.
        The GitHub token is masked before being included in the DTO.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.SettingsDTO` populated
            with the current configuration values.
        """
        return _read_settings_dto(self._config, self._resolver)

    def update(
        self,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> SettingsDTO:
        """Apply a partial update to the application settings.

        Recognised keys and their TOML mappings:

        =====================  ============================
        DTO key                TOML path
        =====================  ============================
        ``github_token``       ``settings.github-token``
        ``collection_path``    ``settings.collection-path``
        ``default_scope``      ``settings.default-scope``
        ``edition``            ``settings.edition``
        ``indexing_mode``      ``artifact_search.indexing_mode``
        =====================  ============================

        Unknown keys from *updates* are stored under ``settings.<key>`` for
        forward-compatibility.

        Args:
            updates: Map of setting keys to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.SettingsDTO`.
        """
        _known_key_map: Dict[str, str] = {
            "github_token": _GITHUB_TOKEN_KEY,
            "collection_path": _COLLECTION_PATH_KEY,
            "default_scope": _DEFAULT_SCOPE_KEY,
            "edition": _EDITION_KEY,
        }

        for dto_key, value in updates.items():
            if dto_key == "indexing_mode":
                self._config.set_indexing_mode(str(value))
            elif dto_key in _known_key_map:
                self._config.set(_known_key_map[dto_key], value)
            else:
                # Store unknown keys under the settings section.
                self._config.set(f"settings.{dto_key}", value)

        return _read_settings_dto(self._config, self._resolver)

    def validate_github_token(
        self,
        token: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Validate a GitHub Personal Access Token against the GitHub API.

        Performs a lightweight ``GET /rate_limit`` call (or equivalent)
        through the :class:`~skillmeat.core.github_client.GitHubClient`
        wrapper.  Returns ``False`` on any error (network failure, import
        error, invalid token) so the caller can degrade gracefully.

        Args:
            token: Raw GitHub PAT string.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` if the token is valid and authenticated, ``False``
            otherwise.
        """
        if not token or not token.strip():
            return False

        try:
            from skillmeat.core.github_client import GitHubClient, GitHubAuthError

            client = GitHubClient(token=token)
            rate_limit = client.get_rate_limit()
            # A successful rate-limit call confirms the token is valid.
            # Authenticated tokens have a higher rate limit than unauthenticated.
            limit = (
                rate_limit.get("rate", {}).get("limit")
                if isinstance(rate_limit, dict)
                else None
            )
            if limit is not None and int(limit) > 60:
                return True
            # Even if we cannot read the limit, a non-exception response means
            # the token was accepted.
            return rate_limit is not None
        except Exception as exc:
            exc_str = str(exc).lower()
            if "auth" in exc_str or "401" in exc_str or "403" in exc_str:
                logger.debug("validate_github_token: token rejected by GitHub: %s", exc)
            else:
                logger.debug("validate_github_token: unexpected error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # ISettingsRepository — EntityTypeConfig CRUD
    # ------------------------------------------------------------------

    def list_entity_type_configs(
        self,
        ctx: Optional[RequestContext] = None,
    ) -> List[EntityTypeConfigDTO]:
        """Return all registered entity type configurations from the DB cache.

        Delegates to the ``entity_type_configs`` ORM table (``EntityTypeConfig``
        model) ordered by ``sort_order``.

        Args:
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`
            objects, including both system-defined and user-created entries.
        """
        try:
            from skillmeat.cache.models import EntityTypeConfig, get_session

            with get_session() as session:
                rows = (
                    session.query(EntityTypeConfig)
                    .order_by(EntityTypeConfig.sort_order)
                    .all()
                )
                return [self._entity_type_config_to_dto(r) for r in rows]
        except Exception as exc:
            logger.debug("list_entity_type_configs: DB unavailable: %s", exc)
            return []

    def create_entity_type_config(
        self,
        entity_type: str,
        display_name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
    ) -> EntityTypeConfigDTO:
        """Create a new user-defined entity type configuration.

        Args:
            entity_type: Machine-readable entity type key (used as ``slug``).
                Must be unique.
            display_name: Human-readable display name.
            description: Optional description of this entity type.
            icon: Optional icon identifier or URL.
            color: Optional hex color code (e.g. ``"#FF5733"``).
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`.

        Raises:
            ValueError: If an entity type config with the same *entity_type*
                already exists.
        """
        from skillmeat.cache.models import EntityTypeConfig, get_session

        with get_session() as session:
            existing = (
                session.query(EntityTypeConfig)
                .filter(EntityTypeConfig.slug == entity_type)
                .first()
            )
            if existing is not None:
                raise ValueError(
                    f"EntityTypeConfig with entity_type='{entity_type}' already exists"
                )

            # Compute next sort_order.
            max_order_row = (
                session.query(EntityTypeConfig.sort_order)
                .order_by(EntityTypeConfig.sort_order.desc())
                .first()
            )
            next_order = ((max_order_row[0] or 0) + 10) if max_order_row else 0

            config = EntityTypeConfig(
                slug=entity_type,
                display_name=display_name,
                description=description,
                icon=icon,
                color=color,
                is_builtin=False,
                sort_order=next_order,
            )
            session.add(config)
            session.flush()
            return self._entity_type_config_to_dto(config)

    def update_entity_type_config(
        self,
        config_id: str,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> EntityTypeConfigDTO:
        """Apply a partial update to an existing entity type configuration.

        Immutable fields (``entity_type`` / ``slug``, ``is_system`` /
        ``is_builtin``) are rejected when present in *updates*.

        Args:
            config_id: Unique identifier of the entity type config — either
                the integer PK (as a string) or the ``slug``.
            updates: Map of field names to new values.  Recognised keys:
                ``display_name``, ``description``, ``icon``, ``color``.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`.

        Raises:
            KeyError: If no config with *config_id* exists.
            ValueError: If the update attempts to mutate an immutable field.
        """
        from skillmeat.cache.models import EntityTypeConfig, get_session

        # Reject immutable-field mutations.
        immutable = {"entity_type", "slug", "is_system", "is_builtin"}
        bad_keys = immutable.intersection(updates)
        if bad_keys:
            raise ValueError(
                f"Cannot update immutable field(s): {', '.join(sorted(bad_keys))}"
            )

        with get_session() as session:
            config = self._get_entity_type_config_row(session, config_id)
            if config is None:
                raise KeyError(f"EntityTypeConfig '{config_id}' not found")

            mutable_map = {
                "display_name": "display_name",
                "description": "description",
                "icon": "icon",
                "color": "color",
            }
            for dto_key, orm_attr in mutable_map.items():
                if dto_key in updates:
                    setattr(config, orm_attr, updates[dto_key])

            session.flush()
            return self._entity_type_config_to_dto(config)

    def delete_entity_type_config(
        self,
        config_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> None:
        """Delete a user-defined entity type configuration.

        System-defined / built-in configs cannot be deleted.

        Args:
            config_id: Unique identifier of the entity type config — either
                the integer PK (as a string) or the ``slug``.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no config with *config_id* exists.
            ValueError: If the config is system-defined (``is_builtin=True``).
        """
        from skillmeat.cache.models import EntityTypeConfig, get_session

        with get_session() as session:
            config = self._get_entity_type_config_row(session, config_id)
            if config is None:
                raise KeyError(f"EntityTypeConfig '{config_id}' not found")

            if config.is_builtin:
                raise ValueError(
                    f"EntityTypeConfig '{config_id}' is a built-in type and cannot be deleted"
                )

            session.delete(config)
            session.commit()

    # ------------------------------------------------------------------
    # ISettingsRepository — Category CRUD
    # ------------------------------------------------------------------

    def list_categories(
        self,
        entity_type: Optional[str] = None,
        platform: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
    ) -> List[CategoryDTO]:
        """Return all categories from the DB cache, optionally filtered by entity type
        and platform.

        Args:
            entity_type: When provided, return only categories whose
                ``entity_type_slug`` matches.  When omitted, all categories
                are returned.
            platform: When provided, return only categories scoped to this
                platform.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CategoryDTO` objects.
        """
        try:
            from skillmeat.cache.models import ContextEntityCategory, get_session

            with get_session() as session:
                query = session.query(ContextEntityCategory)
                if entity_type is not None:
                    query = query.filter(
                        ContextEntityCategory.entity_type_slug == entity_type
                    )
                if platform is not None:
                    query = query.filter(ContextEntityCategory.platform == platform)
                rows = query.order_by(ContextEntityCategory.sort_order).all()
                return [self._category_to_dto(r) for r in rows]
        except Exception as exc:
            logger.debug("list_categories: DB unavailable: %s", exc)
            return []

    def create_category(
        self,
        name: str,
        slug: Optional[str] = None,
        entity_type: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        platform: Optional[str] = None,
        sort_order: Optional[int] = None,
        ctx: Optional[RequestContext] = None,
    ) -> CategoryDTO:
        """Create a new category in the DB cache.

        Args:
            name: Human-readable category name.
            slug: Optional URL-safe slug; auto-generated from *name* when
                omitted.
            entity_type: Optional entity type this category applies to.
                Pass ``None`` for a cross-type (universal) category.
            description: Optional description text.
            color: Optional hex color code for UI display (e.g. ``"#00FF00"``).
            platform: Optional platform scope filter.
            sort_order: Optional explicit display order; auto-computed when
                omitted.
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.CategoryDTO`.

        Raises:
            ValueError: If a category with the same resolved slug already
                exists.
        """
        from skillmeat.cache.models import ContextEntityCategory, get_session

        # Generate a URL-safe slug from the name when not provided.
        resolved_slug = slug if slug else _slugify(name)

        with get_session() as session:
            existing = (
                session.query(ContextEntityCategory)
                .filter(ContextEntityCategory.slug == resolved_slug)
                .first()
            )
            if existing is not None:
                raise ValueError(
                    f"Category with slug='{resolved_slug}' already exists"
                )

            # Compute next sort_order when not explicitly provided.
            if sort_order is None:
                max_order_row = (
                    session.query(ContextEntityCategory.sort_order)
                    .order_by(ContextEntityCategory.sort_order.desc())
                    .first()
                )
                sort_order = ((max_order_row[0] or 0) + 10) if max_order_row else 0

            category = ContextEntityCategory(
                name=name,
                slug=resolved_slug,
                description=description,
                color=color,
                entity_type_slug=entity_type,
                platform=platform,
                sort_order=sort_order,
                is_builtin=False,
            )
            session.add(category)
            session.flush()
            return self._category_to_dto(category)

    def update_category(
        self,
        category_id: int,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> CategoryDTO:
        """Apply a partial update to an existing category.

        Args:
            category_id: Integer primary key of the category to update.
            updates: Map of field names to new values.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.CategoryDTO`.

        Raises:
            KeyError: If no category with *category_id* exists.
            ValueError: If the requested new slug is already taken.
        """
        from skillmeat.cache.models import ContextEntityCategory, get_session

        with get_session() as session:
            category = (
                session.query(ContextEntityCategory)
                .filter(ContextEntityCategory.id == category_id)
                .first()
            )
            if category is None:
                raise KeyError(f"Category with id='{category_id}' not found")

            # Check slug uniqueness when slug is being changed.
            new_slug = updates.get("slug")
            if new_slug is not None and new_slug != category.slug:
                collision = (
                    session.query(ContextEntityCategory)
                    .filter(ContextEntityCategory.slug == new_slug)
                    .first()
                )
                if collision is not None:
                    raise ValueError(
                        f"Category with slug='{new_slug}' already exists"
                    )

            for field, value in updates.items():
                setattr(category, field, value)

            session.flush()
            return self._category_to_dto(category)

    def delete_category(
        self,
        category_id: int,
        ctx: Optional[RequestContext] = None,
    ) -> None:
        """Delete a category by integer primary key.

        Args:
            category_id: Integer primary key of the category to delete.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no category with *category_id* exists.
            ValueError: If the category has one or more artifact associations.
        """
        from skillmeat.cache.models import ArtifactCategoryAssociation, ContextEntityCategory, get_session

        with get_session() as session:
            category = (
                session.query(ContextEntityCategory)
                .filter(ContextEntityCategory.id == category_id)
                .first()
            )
            if category is None:
                raise KeyError(f"Category with id='{category_id}' not found")

            association_count = (
                session.query(ArtifactCategoryAssociation)
                .filter(ArtifactCategoryAssociation.category_id == category_id)
                .count()
            )
            if association_count > 0:
                raise ValueError(
                    f"Category '{category.slug}' has {association_count} artifact "
                    "association(s) and cannot be deleted. Remove all artifact "
                    "associations first."
                )

            session.delete(category)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_entity_type_config_row(
        session: Any,
        config_id: str,
    ) -> Optional[Any]:
        """Resolve an EntityTypeConfig row by integer PK string or slug.

        Args:
            session: Active SQLAlchemy session.
            config_id: Integer PK (as string) or slug string.

        Returns:
            The matching ORM row, or ``None`` if not found.
        """
        from skillmeat.cache.models import EntityTypeConfig

        # Try integer PK first.
        if config_id.isdigit():
            row = session.query(EntityTypeConfig).get(int(config_id))
            if row is not None:
                return row

        # Fall back to slug lookup.
        return (
            session.query(EntityTypeConfig)
            .filter(EntityTypeConfig.slug == config_id)
            .first()
        )

    @staticmethod
    def _entity_type_config_to_dto(config: Any) -> EntityTypeConfigDTO:
        """Convert an ``EntityTypeConfig`` ORM row to a DTO.

        Args:
            config: ``EntityTypeConfig`` ORM instance.

        Returns:
            A frozen :class:`~skillmeat.core.interfaces.dtos.EntityTypeConfigDTO`.
        """
        return EntityTypeConfigDTO(
            id=str(config.id),
            entity_type=config.slug,
            display_name=config.display_name,
            description=config.description,
            icon=config.icon,
            color=config.color,
            is_system=bool(config.is_builtin),
            sort_order=int(config.sort_order) if config.sort_order is not None else 0,
            path_prefix=getattr(config, "path_prefix", None),
            required_frontmatter_keys=getattr(config, "required_frontmatter_keys", None),
            optional_frontmatter_keys=getattr(config, "optional_frontmatter_keys", None),
            validation_rules=getattr(config, "validation_rules", None),
            example_path=getattr(config, "example_path", None),
            content_template=getattr(config, "content_template", None),
            applicable_platforms=getattr(config, "applicable_platforms", None),
            frontmatter_schema=getattr(config, "frontmatter_schema", None),
            created_at=config.created_at.isoformat() if config.created_at else None,
            updated_at=config.updated_at.isoformat() if config.updated_at else None,
        )

    @staticmethod
    def _category_to_dto(category: Any) -> CategoryDTO:
        """Convert a ``ContextEntityCategory`` ORM row to a DTO.

        Args:
            category: ``ContextEntityCategory`` ORM instance.

        Returns:
            A frozen :class:`~skillmeat.core.interfaces.dtos.CategoryDTO`.
        """
        artifact_count = 0
        try:
            artifact_count = len(category.artifacts) if category.artifacts else 0
        except Exception:
            pass

        return CategoryDTO(
            id=str(category.id),
            name=category.name,
            slug=category.slug or "",
            entity_type=category.entity_type_slug,
            description=category.description,
            color=category.color,
            platform=getattr(category, "platform", None),
            sort_order=int(category.sort_order) if category.sort_order is not None else 0,
            is_builtin=bool(getattr(category, "is_builtin", False)),
            artifact_count=artifact_count,
            created_at=category.created_at.isoformat() if category.created_at else None,
            updated_at=category.updated_at.isoformat() if category.updated_at else None,
        )
