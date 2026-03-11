# SQLAlchemy Model Patterns for SkillMeat BOM/Attestation Feature

**Date**: 2026-03-11
**Purpose**: Reference patterns discovered for implementing Bill of Materials (BOM) and attestation models in SkillMeat
**References**: models.py, models_enterprise.py, auth_types.py, enterprise_repositories.py, migrations/

## Summary

SkillMeat maintains a **dual-tier database architecture** with intentional divergence between local (SQLite, `models.py`) and enterprise (PostgreSQL, `models_enterprise.py`) repositories. This document codifies the patterns needed to add BOM and attestation models consistently.

---

## Key Findings

### 1. Base Classes and Imports

**Local Mode (SQLite)**:
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass
```

**Enterprise Mode (PostgreSQL)**:
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class EnterpriseBase(DeclarativeBase):
    """Shared DeclarativeBase for all enterprise (PostgreSQL) ORM models."""
    pass
```

**Key invariant**: Never mix bases — use `Base` for local models, `EnterpriseBase` for enterprise models. They have separate metadata registries.

### 2. Primary Key Patterns

**Local Edition (SQLite)**:
- PKs are typically `String` (composite like `type:name`) or `Integer` with autoincrement
- Example from `Artifact`:
  ```python
  id: Mapped[str] = mapped_column(String, primary_key=True)
  ```

**Enterprise Edition (PostgreSQL)**:
- PKs are always `UUID(as_uuid=True)` from `sqlalchemy.dialects.postgresql`
- Server-generated via `gen_random_uuid()`
- Example from `EnterpriseArtifact`:
  ```python
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True),
      primary_key=True,
      default=uuid.uuid4,
      server_default=text("gen_random_uuid()"),
      comment="Globally unique artifact identifier",
  )
  ```

**For BOM/Attestation models**:
- Local: Use `id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)` OR a String composite key
- Enterprise: Always `id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))`

### 3. Tenant Filtering (Enterprise Only)

**Invariant**: Every enterprise model MUST have a `tenant_id` column of type `UUID`.

```python
tenant_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    nullable=False,
    comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
)
```

**Repository layer** (`EnterpriseRepositoryBase._apply_tenant_filter`):
```python
def _apply_tenant_filter(self, stmt: Select) -> Select:
    tenant_id = self._get_tenant_id()  # Falls back to DEFAULT_TENANT_ID if TenantContext not set
    return stmt.where(self.model_class.tenant_id == tenant_id)
```

**Enforcement**: Every `select()` statement in enterprise repos MUST call `_apply_tenant_filter()` before execution. Omitting this is a security defect.

### 4. JSON Column Patterns

**Local Mode (SQLite)**:
- Use `JSON` type from sqlalchemy core
- Mapped as `Mapped[Optional[List[str]]]` or `Mapped[Optional[Dict[str, Any]]]`
- Example from Artifact:
  ```python
  target_platforms: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
  ```

**Enterprise Mode (PostgreSQL)**:
- Use `JSONB` type from `sqlalchemy.dialects.postgresql`
- Mapped as `Mapped[List[str]]` or `Mapped[Dict[str, Any]]`
- Supports GIN indexing for `@>` containment queries
- Example from `EnterpriseArtifact`:
  ```python
  from sqlalchemy.dialects.postgresql import JSONB

  tags: Mapped[List[str]] = mapped_column(
      JSONB,
      nullable=False,
      default=list,
      server_default=text("'[]'::jsonb"),
      comment="Array of tag strings; GIN-indexed for @> containment",
  )
  custom_fields: Mapped[Dict[str, Any]] = mapped_column(
      JSONB,
      nullable=False,
      default=dict,
      server_default=text("'{}'::jsonb"),
      comment="Arbitrary key-value pairs for extensibility",
  )
  ```

**For BOM/Attestation**:
- Local: `mapped_column(JSON, nullable=...)`
- Enterprise: `mapped_column(JSONB, nullable=..., default=..., server_default=...)`

### 5. Enum Patterns

**Location**: `skillmeat/cache/auth_types.py` — NOT in models files.

**Existing enums**:
```python
class OwnerType(str, enum.Enum):
    user = "user"
    team = "team"

class Visibility(str, enum.Enum):
    private = "private"
    team = "team"
    public = "public"

class UserRole(str, enum.Enum):
    system_admin = "system_admin"
    team_admin = "team_admin"
    team_member = "team_member"
    viewer = "viewer"
```

**Storage**: SQLAlchemy stores enum values as their string `.value`, so they round-trip cleanly through SQLite TEXT and PostgreSQL ENUM.

**Usage in models**:
```python
from skillmeat.cache.auth_types import OwnerType, Visibility

visibility: Mapped[Optional[str]] = mapped_column(
    String, nullable=True, default=Visibility.private.value
)
```

**For BOM/Attestation**:
- Define enums in `auth_types.py` or a new dedicated `bom_types.py`
- Import in both `models.py` and `models_enterprise.py`
- Store as `String` columns with `.value` defaults

### 6. Timestamp Patterns

**Local Mode (SQLite)**:
```python
from datetime import datetime

created_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, default=datetime.utcnow
)
updated_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
)
```

**Enterprise Mode (PostgreSQL)**:
```python
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=datetime.utcnow,
    server_default=text("now()"),
    comment="Creation timestamp (server-managed)",
)
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=datetime.utcnow,
    server_default=text("now()"),
    comment="Last-modified timestamp (app-managed)",
)
```

### 7. Foreign Keys and Relationships

**Pattern**: FK targets use the `id` column, relationship uses `Mapped[...]` with optional `cascade` and `lazy` settings.

**Example from Artifact**:
```python
project_id: Mapped[str] = mapped_column(
    String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
)
project: Mapped["Project"] = relationship("Project", back_populates="artifacts")
```

**For BOM/Attestation FK to Artifact**:
- Local: `artifact_id: Mapped[str]` with FK to `artifacts.id`
- Enterprise: `artifact_id: Mapped[uuid.UUID]` with FK to `enterprise_artifacts.id`

### 8. Ownership and Visibility Fields (Already in Models)

**Artifact model includes**:
```python
owner_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
owner_type: Mapped[Optional[str]] = mapped_column(
    String, nullable=True, default=OwnerType.user.value
)
visibility: Mapped[Optional[str]] = mapped_column(
    String, nullable=True, default=Visibility.private.value
)
```

**These are already present on Artifact** — BOM/Attestation may reuse or have their own.

### 9. Indexes and Constraints

**Common patterns**:
```python
__tablename__ = "table_name"

# Composite indexes for performance
Index("idx_table_col1_col2", "col1", "col2")

# Unique constraints
UniqueConstraint("tenant_id", "name", name="uq_table_tenant_name")

# Check constraints
CheckConstraint("length(name) > 0", name="ck_table_name_length")
```

**Enterprise-specific**:
- Always include tenant_id in composite indexes
- Example: `Index("idx_bom_entries_tenant_artifact", "tenant_id", "artifact_id")`
- Use `server_default=text("...")` for PostgreSQL defaults

### 10. Constants

**Location**: `skillmeat/cache/constants.py`

```python
DEFAULT_TENANT_ID: uuid.UUID = uuid.UUID(
    os.environ.get("SKILLMEAT_DEFAULT_TENANT_ID", "00000000-0000-4000-a000-000000000001")
)
LOCAL_ADMIN_USER_ID: uuid.UUID = uuid.UUID("00000000-0000-4000-a000-000000000002")
```

**For BOM**: No special constants needed unless modeling distinct entity types.

---

## Migration Naming Convention

**Pattern**: `{prefix}_{number}_{description}.py`

**Prefixes**:
- `ent_` — Enterprise schema changes (PostgreSQL)
- `pg_` — PostgreSQL-specific features (full-text search, etc.)
- No prefix — SQLite-compatible changes (older pattern)

**Latest sequence**:
- `ent_001` through `ent_006` — Phase 1 auth foundation
- `pg_001` — PostgreSQL full-text search

**For BOM feature**:
- Recommend `ent_007_bom_attestation` (covers both local and enterprise)
- Or split: `ent_007_bom_enterprise` + `local_007_bom_local` if changes differ significantly

**Migration template structure**:
```python
"""Feature name and description

Revision ID: ent_007_bom_attestation
Revises: pg_001_fulltext_search
Create Date: 2026-03-11 00:07:00.000000+00:00

Background
----------
[Feature context, PRD reference]

What this migration adds
------------------------
[Local (SQLite) changes]
[Enterprise (PostgreSQL) changes]

Downgrade order
---------------
[Reverse order of operations]
"""
```

---

## File Organization

**Current structure**:
```
skillmeat/cache/
├── models.py                    ← Local (SQLite) ORM models
├── models_enterprise.py         ← Enterprise (PostgreSQL) ORM models
├── auth_types.py               ← Enums for ownership/visibility/roles
├── constants.py                ← Shared constants (DEFAULT_TENANT_ID, etc.)
├── repositories.py             ← Local-mode repository implementations (SQLAlchemy 1.x style)
├── enterprise_repositories.py  ← Enterprise-mode base with tenant filtering
├── migrations/versions/        ← Alembic migration files
└── tests/
    ├── CLAUDE.md              ← Testing patterns for enterprise repos
    ├── test_enterprise_*.py   ← Enterprise-specific tests
    └── test_*.py              ← Local-mode tests
```

**For BOM/Attestation**:
1. Add models to `models.py` (local)
2. Add models to `models_enterprise.py` (enterprise)
3. Create enums in `auth_types.py` (if needed)
4. Add repository base in `enterprise_repositories.py` (subclass `EnterpriseRepositoryBase`)
5. Create migration(s) in `migrations/versions/`

---

## Key Invariants (Security & Consistency)

1. **Never skip `_apply_tenant_filter()`** in enterprise repos — every `select()` statement must call it.
2. **Never mix `Base` and `EnterpriseBase`** — each has separate metadata.
3. **Enterprise PKs are always UUID** — no integers, no composite strings.
4. **Tenant ID is always part of composite indexes** in enterprise schema.
5. **Enums are stored as strings** — use `.value` for defaults.
6. **Timestamps in enterprise always use `DateTime(timezone=True)`** with both `default` and `server_default`.
7. **Local JSON uses `JSON`, enterprise uses `JSONB`** — different dialects.

---

## Example: BOM Entry Model (Skeleton)

**Local (models.py)**:
```python
class BOMEntry(Base):
    """Bill of Materials entry for an artifact."""
    __tablename__ = "bom_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_id: Mapped[str] = mapped_column(
        String, ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    component_name: Mapped[str] = mapped_column(String, nullable=False)
    component_version: Mapped[str] = mapped_column(String, nullable=False)
    license: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_bom_entries_artifact_id", "artifact_id"),
    )
```

**Enterprise (models_enterprise.py)**:
```python
class EnterpriseBOMEntry(EnterpriseBase):
    """Bill of Materials entry for an artifact (enterprise)."""
    __tablename__ = "enterprise_bom_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope",
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprise_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_version: Mapped[str] = mapped_column(String(100), nullable=False)
    license: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("idx_enterprise_bom_entries_tenant_artifact", "tenant_id", "artifact_id"),
    )
```

---

## References

- **Models**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py` (line 254 for Artifact)
- **Enterprise Models**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models_enterprise.py` (line 104 for EnterpriseArtifact)
- **Auth Types**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/auth_types.py`
- **Enterprise Repos**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/enterprise_repositories.py` (line 366 for `_apply_tenant_filter`)
- **Constants**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/constants.py`
- **Latest Migration**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/versions/pg_001_fulltext_search.py`
- **Cache CLAUDE.md**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/CLAUDE.md`
- **Enterprise Testing Patterns**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/tests/CLAUDE.md`
