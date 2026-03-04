#!/usr/bin/env python3
"""Seed script for the fin-serv-compliance demo composite artifact.

Creates a ``composite:fin-serv-compliance`` of type ``stack`` in the
SkillMeat collection, consisting of:

  1. CLAUDE.md (project config) — financial services compliance template
  2. agent:db-architect — database architecture specialist agent
  3. mcp:internal-db-explorer — PostgreSQL MCP server for schema introspection

The script operates in two phases:

1. **Filesystem phase** — writes the artifact files under
   ``~/.skillmeat/collection/artifacts/fin-serv-compliance/`` following the
   layout expected by the heuristic detector.

2. **Database phase** — seeds the ``Artifact``, ``CompositeArtifact``, and
   ``CompositeMembership`` rows that ``render_in_memory`` needs (specifically
   ``path_pattern`` and ``core_content`` on each child Artifact).

Both phases are idempotent — re-running the script is safe.

Usage::

    python scripts/seed_demo_composite.py
    python scripts/seed_demo_composite.py --dry-run
    python scripts/seed_demo_composite.py --collection-dir /custom/path
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import click

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_demo_composite")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPOSITE_NAME = "fin-serv-compliance"
COMPOSITE_ID = f"composite:{COMPOSITE_NAME}"
COLLECTION_ID = "default"

# Sentinel project used for collection-scoped artifacts (must match models.py
# and artifact_cache_service.py constant).
_SENTINEL_PROJECT_ID = "collection_artifacts_global"

# ---------------------------------------------------------------------------
# Artifact content definitions
# ---------------------------------------------------------------------------

CLAUDE_MD_CONTENT = """\
# {{PROJECT_NAME}}

> Author: {{AUTHOR}}
> Generated: {{DATE}}

## Financial Services Compliance Configuration

This project is subject to financial-services regulatory requirements.
All contributors **must** read and adhere to the rules in this file before
writing code, designing schemas, or deploying services.

Compliance frameworks in scope:

- **SOC 2 Type II** — data security, availability, processing integrity
- **PCI-DSS v4.0** — cardholder data protection (if payments are processed)
- **GDPR / CCPA** — personal data handling and right-to-erasure

---

## Database Patterns

### Connection Pooling

Always use connection pooling with explicit limits:

```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_pre_ping=True,   # detect stale connections
)
```

### Query Logging

Enable query logging in non-production environments:

```python
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
```

Production query logging must route to the centralised audit log — never
to stdout.

### Migration Requirements

- All schema changes MUST be managed via Alembic migrations.
- Migrations must be reviewed by the database architect before merging.
- Destructive migrations (DROP TABLE, DROP COLUMN) require a rollback plan.
- Column renames must use a two-step add-then-drop migration.

---

## Security Patterns

### No Raw SQL

Raw SQL is **prohibited**.  Use parameterised queries or the ORM exclusively:

```python
# WRONG — never do this
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# CORRECT — parameterised
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# PREFERRED — ORM
session.query(User).filter(User.id == user_id).first()
```

### Secrets Management

- Database credentials must be loaded from environment variables or a
  secrets manager (HashiCorp Vault, AWS Secrets Manager).
- Secrets must never appear in source code, logs, or git history.
- Rotate credentials on a 90-day cycle or immediately after suspected
  exposure.

### Input Validation

All external inputs (API requests, file uploads, webhook payloads) must be
validated against a strict Pydantic schema before processing.

---

## Code Review Requirements

- Every PR must have at least two approvals before merging.
- At least one reviewer must have the "compliance-reviewer" role.
- Security-sensitive changes (auth, payments, PII) require a security review.
- Database migrations require a DBA review sign-off comment.
- PRs must not contain secrets, credentials, or PII in diffs or commit
  messages.

---

## Architecture Description

{{ARCHITECTURE_DESCRIPTION}}
"""

AGENT_DB_ARCHITECT_CONTENT = """\
---
name: db-architect
description: >
  Database architecture specialist with deep PostgreSQL expertise and
  financial-data compliance awareness. Engages on schema design, migration
  planning, query optimisation, and regulatory data-handling requirements.
  Always recommends parameterised queries, connection pooling, and audit
  logging for financial workloads.

specialisations:
  - PostgreSQL schema design (normalisation, partitioning, JSONB patterns)
  - Alembic migration planning and rollback strategies
  - Query optimisation (EXPLAIN ANALYSE, index strategy, N+1 elimination)
  - Data compliance (PCI-DSS, SOC 2, GDPR field-level encryption)
  - Connection pool sizing and failover configuration

tools:
  - read   # schema files, migration scripts, ERDs
  - bash   # EXPLAIN ANALYSE, pg_stat_statements, psql diagnostics

guidelines:
  - Never suggest raw string interpolation in SQL — always parameterised.
  - Flag any column storing PII without encryption or masking.
  - Migrations must include a `downgrade()` path unless the change is truly
    irreversible and that decision is explicitly documented.
  - Recommend `pool_pre_ping=True` for all SQLAlchemy engines in financial
    services context.
  - When reviewing a schema, check for missing indexes on FK columns.
  - All timestamp columns must store UTC; application layer converts to local.
---

## db-architect Agent

I am a database architecture specialist optimised for financial-services
engineering teams. My primary focus areas are:

1. **Schema Design** — normalised relational models, partition strategies for
   time-series financial data, JSONB vs relational trade-offs.

2. **Migration Safety** — Alembic-based workflows with zero-downtime strategies
   (shadow tables, blue-green, online DDL where supported).

3. **Query Performance** — index selection, query plan analysis, connection
   pool tuning, and read-replica routing.

4. **Compliance Awareness** — column-level encryption for PII/PCI data, audit
   trail tables, field masking, right-to-erasure implementation patterns.

When you ask me to review a schema or query, I will:

- Identify missing constraints (FK, CHECK, NOT NULL)
- Flag potential N+1 query risks
- Recommend appropriate indexes
- Note any PII fields that should be encrypted or masked
- Propose a migration plan with rollback if schema changes are involved
"""

MCP_INTERNAL_DB_EXPLORER_CONTENT = json.dumps(
    {
        "mcpServers": {
            "internal-db-explorer": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    "--read-only",
                ],
                "env": {
                    "POSTGRES_CONNECTION_STRING": "${INTERNAL_DB_CONNECTION_STRING}"
                },
                "description": (
                    "Read-only MCP server for exploring the internal PostgreSQL "
                    "database. Provides schema introspection, table listing, and "
                    "safe SELECT queries. Write operations (INSERT, UPDATE, DELETE, "
                    "DDL) are blocked at the server level."
                ),
                "capabilities": [
                    "list_tables",
                    "describe_table",
                    "list_schemas",
                    "execute_query",
                ],
                "restrictions": {
                    "read_only": True,
                    "max_rows_per_query": 1000,
                    "query_timeout_seconds": 30,
                },
            }
        }
    },
    indent=2,
)

MANIFEST_TOML_CONTENT = f"""\
# SkillMeat composite manifest — fin-serv-compliance
# type = stack (a curated set of tools for a specific engineering context)

[composite]
name = "{COMPOSITE_NAME}"
composite_type = "stack"
display_name = "Financial Services Compliance Stack"
description = \"\"\"
A curated compliance stack for financial-services projects.

Includes:
- CLAUDE.md project config with SOC 2 / PCI-DSS rules and DB patterns
- db-architect agent for schema design and migration guidance
- internal-db-explorer MCP server for read-only PostgreSQL introspection
\"\"\"
collection_id = "{COLLECTION_ID}"

[[members]]
artifact_id = "config:CLAUDE.md"
type = "project_config"
path = "CLAUDE.md"
position = 0
relationship = "contains"

[[members]]
artifact_id = "agent:db-architect"
type = "agent"
path = "agents/db-architect.md"
position = 1
relationship = "contains"

[[members]]
artifact_id = "mcp:internal-db-explorer"
type = "mcp"
path = "mcp-servers/internal-db-explorer.json"
position = 2
relationship = "contains"
"""

# ---------------------------------------------------------------------------
# Member definitions (drives both filesystem and DB seeding)
# ---------------------------------------------------------------------------

# Each tuple: (artifact_id, artifact_type, relative_path, content, path_pattern)
# path_pattern is the target path in a scaffolded project (used by render_in_memory)
MEMBERS: List[Tuple[str, str, str, str, str]] = [
    (
        "config:CLAUDE.md",
        "project_config",
        "CLAUDE.md",
        CLAUDE_MD_CONTENT,
        "CLAUDE.md",
    ),
    (
        "agent:db-architect",
        "agent",
        "agents/db-architect.md",
        AGENT_DB_ARCHITECT_CONTENT,
        ".claude/agents/db-architect.md",
    ),
    (
        "mcp:internal-db-explorer",
        "mcp",
        "mcp-servers/internal-db-explorer.json",
        MCP_INTERNAL_DB_EXPLORER_CONTENT,
        ".mcp.json",
    ),
]


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def _sha256(content: str) -> str:
    """Return hex SHA-256 digest of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def write_filesystem(base_dir: Path, dry_run: bool) -> None:
    """Write composite artifact files under *base_dir*.

    Args:
        base_dir: Root of the composite directory, e.g.
            ``~/.skillmeat/collection/artifacts/fin-serv-compliance/``.
        dry_run: When ``True`` log what would be written but make no changes.
    """
    files_to_write = [
        (base_dir / "manifest.toml", MANIFEST_TOML_CONTENT),
        (base_dir / "CLAUDE.md", CLAUDE_MD_CONTENT),
        (base_dir / "agents" / "db-architect.md", AGENT_DB_ARCHITECT_CONTENT),
        (base_dir / "mcp-servers" / "internal-db-explorer.json", MCP_INTERNAL_DB_EXPLORER_CONTENT),
    ]

    for file_path, content in files_to_write:
        if dry_run:
            action = "EXISTS" if file_path.exists() else "CREATE"
            click.echo(f"  [dry-run] {action} {file_path}")
            continue

        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")
            if existing == content:
                logger.debug("unchanged: %s", file_path)
                continue
            logger.info("overwriting: %s", file_path)
        else:
            logger.info("creating: %s", file_path)

        file_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Database seeding helpers
# ---------------------------------------------------------------------------


def _ensure_sentinel_project(session) -> None:
    """Create the sentinel Project row if it does not exist."""
    from skillmeat.cache.models import Project  # noqa: PLC0415

    exists = (
        session.query(Project.id)
        .filter(Project.id == _SENTINEL_PROJECT_ID)
        .first()
    )
    if exists is None:
        sentinel = Project(
            id=_SENTINEL_PROJECT_ID,
            name="Collection Artifacts",
            path="~/.skillmeat/collections",
            description="Sentinel project for collection artifacts",
            status="active",
        )
        session.add(sentinel)
        session.flush()
        logger.debug("created sentinel Project row '%s'", _SENTINEL_PROJECT_ID)


def _upsert_artifact(
    session,
    artifact_id: str,
    artifact_type: str,
    name: str,
    content: str,
    path_pattern: str,
) -> str:
    """Insert or update an Artifact row; returns its stable UUID.

    Args:
        session: Active SQLAlchemy session.
        artifact_id: ``type:name`` primary key, e.g. ``"agent:db-architect"``.
        artifact_type: Type string matching ORM ``type`` column.
        name: Human-readable name.
        content: Full file content (stored as ``core_content``).
        path_pattern: Destination path in scaffolded project.

    Returns:
        The 32-char hex UUID of the artifact row.
    """
    from skillmeat.cache.models import Artifact  # noqa: PLC0415

    now = datetime.now(timezone.utc)
    content_hash = _sha256(content)

    existing: Optional[Artifact] = (
        session.query(Artifact).filter(Artifact.id == artifact_id).first()
    )

    if existing is not None:
        # Update mutable fields so re-runs pick up content changes.
        existing.core_content = content
        existing.content_hash = content_hash
        existing.path_pattern = path_pattern
        existing.updated_at = now
        session.flush()
        logger.debug("updated Artifact row '%s' uuid=%s", artifact_id, existing.uuid)
        return existing.uuid

    artifact_uuid = uuid.uuid4().hex
    row = Artifact(
        id=artifact_id,
        uuid=artifact_uuid,
        project_id=_SENTINEL_PROJECT_ID,
        name=name,
        type=artifact_type,
        source=f"local:demo/{COMPOSITE_NAME}",
        path_pattern=path_pattern,
        core_content=content,
        content_hash=content_hash,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    logger.debug("created Artifact row '%s' uuid=%s", artifact_id, artifact_uuid)
    return artifact_uuid


def _upsert_composite(session, collection_id: str) -> None:
    """Insert or update the CompositeArtifact row."""
    from skillmeat.cache.models import CompositeArtifact  # noqa: PLC0415

    now = datetime.now(timezone.utc)
    existing = (
        session.query(CompositeArtifact)
        .filter(CompositeArtifact.id == COMPOSITE_ID)
        .first()
    )

    if existing is not None:
        existing.composite_type = "stack"
        existing.display_name = "Financial Services Compliance Stack"
        existing.description = (
            "A curated compliance stack for financial-services projects. "
            "Includes SOC2/PCI-DSS CLAUDE.md config, db-architect agent, "
            "and internal-db-explorer MCP server."
        )
        existing.updated_at = now
        session.flush()
        logger.debug("updated CompositeArtifact '%s'", COMPOSITE_ID)
        return

    composite = CompositeArtifact(
        id=COMPOSITE_ID,
        collection_id=collection_id,
        composite_type="stack",
        display_name="Financial Services Compliance Stack",
        description=(
            "A curated compliance stack for financial-services projects. "
            "Includes SOC2/PCI-DSS CLAUDE.md config, db-architect agent, "
            "and internal-db-explorer MCP server."
        ),
        created_at=now,
        updated_at=now,
    )
    session.add(composite)
    session.flush()
    logger.debug("created CompositeArtifact '%s'", COMPOSITE_ID)


def _upsert_membership(
    session,
    collection_id: str,
    child_uuid: str,
    position: int,
) -> None:
    """Insert a CompositeMembership row if it does not already exist."""
    from skillmeat.cache.models import CompositeMembership  # noqa: PLC0415

    exists = (
        session.query(CompositeMembership)
        .filter(
            CompositeMembership.collection_id == collection_id,
            CompositeMembership.composite_id == COMPOSITE_ID,
            CompositeMembership.child_artifact_uuid == child_uuid,
        )
        .first()
    )
    if exists is not None:
        logger.debug(
            "membership already exists: composite=%s child_uuid=%s",
            COMPOSITE_ID,
            child_uuid,
        )
        return

    membership = CompositeMembership(
        collection_id=collection_id,
        composite_id=COMPOSITE_ID,
        child_artifact_uuid=child_uuid,
        relationship_type="contains",
        position=position,
    )
    session.add(membership)
    session.flush()
    logger.debug(
        "created membership: composite=%s child_uuid=%s position=%d",
        COMPOSITE_ID,
        child_uuid,
        position,
    )


def seed_database(collection_id: str, dry_run: bool) -> None:
    """Seed Artifact, CompositeArtifact, and CompositeMembership rows.

    Args:
        collection_id: Owning collection identifier (typically ``"default"``).
        dry_run: When ``True`` log the plan but do not commit anything.
    """
    if dry_run:
        click.echo("\n[dry-run] Database phase — would upsert:")
        click.echo(f"  CompositeArtifact id={COMPOSITE_ID!r}")
        for artifact_id, artifact_type, _, _, path_pattern in MEMBERS:
            click.echo(
                f"  Artifact id={artifact_id!r} type={artifact_type!r} "
                f"path_pattern={path_pattern!r}"
            )
        click.echo(f"  {len(MEMBERS)} CompositeMembership rows")
        return

    try:
        from skillmeat.cache.models import get_session  # noqa: PLC0415
    except ImportError as exc:
        logger.error(
            "Cannot import skillmeat — is the package installed? (%s)", exc
        )
        sys.exit(1)

    session = get_session()
    try:
        _ensure_sentinel_project(session)
        _upsert_composite(session, collection_id)

        for position, (artifact_id, artifact_type, _rel_path, content, path_pattern) in enumerate(MEMBERS):
            # Derive the artifact name from the artifact_id (strip type prefix)
            name = artifact_id.split(":", 1)[-1]
            child_uuid = _upsert_artifact(
                session=session,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                name=name,
                content=content,
                path_pattern=path_pattern,
            )
            _upsert_membership(
                session=session,
                collection_id=collection_id,
                child_uuid=child_uuid,
                position=position,
            )

        session.commit()
        logger.info(
            "Database seeding complete: composite='%s' members=%d",
            COMPOSITE_ID,
            len(MEMBERS),
        )

    except Exception:
        session.rollback()
        logger.exception("Database seeding failed — rolled back")
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command(name="seed_demo_composite")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print what would be created without writing any files or DB rows.",
)
@click.option(
    "--collection-dir",
    default=None,
    type=click.Path(path_type=Path),
    help=(
        "Override the collection artifacts root directory. "
        "Defaults to ~/.skillmeat/collection/artifacts/."
    ),
)
@click.option(
    "--collection-id",
    default=COLLECTION_ID,
    show_default=True,
    help="Collection identifier stored in the DB (default: 'default').",
)
@click.option(
    "--skip-db",
    is_flag=True,
    default=False,
    help="Only write filesystem files; skip DB seeding.",
)
@click.option(
    "--skip-fs",
    is_flag=True,
    default=False,
    help="Only seed the database; skip filesystem file writes.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable DEBUG-level logging.",
)
def main(
    dry_run: bool,
    collection_dir: Optional[Path],
    collection_id: str,
    skip_db: bool,
    skip_fs: bool,
    verbose: bool,
) -> None:
    """Seed the fin-serv-compliance demo composite artifact.

    Creates filesystem files and DB rows for the financial-services compliance
    stack used in the Backstage/IDP integration demo.

    The composite contains three member artifacts:

    \b
      1. CLAUDE.md (project_config) — compliance template with {{PROJECT_NAME}}
         and {{AUTHOR}} variables
      2. agent:db-architect — DB architecture specialist agent
      3. mcp:internal-db-explorer — read-only PostgreSQL MCP server

    Run with --dry-run to preview all changes without writing anything.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve collection artifacts directory
    if collection_dir is None:
        collection_dir = Path.home() / ".skillmeat" / "collection" / "artifacts"

    composite_dir = collection_dir / COMPOSITE_NAME

    click.echo(f"Seeding composite: {COMPOSITE_ID}")
    click.echo(f"  Composite directory : {composite_dir}")
    click.echo(f"  Collection ID       : {collection_id}")
    click.echo(f"  Dry run             : {dry_run}")
    click.echo(f"  Skip filesystem     : {skip_fs}")
    click.echo(f"  Skip database       : {skip_db}")
    click.echo("")

    # Phase 1 — Filesystem
    if not skip_fs:
        click.echo("Phase 1: Writing filesystem files...")
        write_filesystem(composite_dir, dry_run=dry_run)
        if not dry_run:
            click.echo(f"  Written to {composite_dir}")

    # Phase 2 — Database
    if not skip_db:
        click.echo("Phase 2: Seeding database rows...")
        seed_database(collection_id=collection_id, dry_run=dry_run)

    if dry_run:
        click.echo("\nDry-run complete — no changes made.")
    else:
        click.echo(
            f"\nDone. Composite '{COMPOSITE_ID}' is ready.\n"
            "You can verify with:\n"
            "  skillmeat list\n"
            "or query the DB directly:\n"
            "  sqlite3 ~/.skillmeat/cache/cache.db "
            f"\"SELECT id, composite_type FROM composite_artifacts WHERE id='{COMPOSITE_ID}'\""
        )


if __name__ == "__main__":
    main()
