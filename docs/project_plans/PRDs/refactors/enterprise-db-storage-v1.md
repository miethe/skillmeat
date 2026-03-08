---
status: inferred_complete
---
# PRD 3: Enterprise Database Storage Implementation

**Author**: Gemini
**Date**: 2026-03-01

## 1. Executive Summary

This PRD outlines the creation of the "Enterprise Edition" storage backend. It fulfills the repository interfaces established in PRD 1 by connecting directly to a centralized, cloud-hosted database (e.g., PostgreSQL with JSONB or DocumentDB). This eliminates the need for a local `~/.skillmeat/collections/` filesystem vault for SaaS users, storing all artifacts natively as database records while preserving the ability to deploy them as files to local project directories.

**Priority:** HIGH

**Complexity:** LARGE

## 2. Goals & Outcomes

* **Stateless Backend:** Ensure the FastAPI application requires no persistent local disk storage (other than temporary processing directories), allowing horizontal scaling.
* **Database-First Repositories:** Implement `EnterpriseDBRepository` classes that read/write directly to a central database.
* **Seamless Deployment:** Update the deployment engine to stream artifact contents from the API directly into local project `.claude/` directories.
* **Migration Pathway:** Provide utilities for users to push their local filesystem vaults up to the enterprise cloud database.

## 3. Architectural Design

### 3.1 The Enterprise Repository Suite

Implement the interfaces defined in PRD 1 specifically for a relational/document database.

* `EnterpriseArtifactRepository`: Reads artifact metadata and Markdown content directly from database tables.
* Every query automatically applies a `WHERE tenant_id = current_tenant` filter using the `AuthContext` from PRD 2.

### 3.2 Database Schema Design

* **artifacts:** `id`, `tenant_id`, `name`, `type`, `description`, `tags` (JSONB).
* **artifact_versions:** `id`, `artifact_id`, `content_hash`, `markdown_payload` (Text), `created_at`.
* **collections:** `id`, `tenant_id`, `name`, `is_default`.

### 3.3 The Deployment Engine Pivot

Currently, the CLI copies files from `~/.skillmeat/` to `./.claude/`.
In Enterprise mode, the CLI will call `GET /api/v1/artifacts/{id}/download`. The API returns a JSON payload containing the file tree and contents. The CLI parses this response and materializes the files into the local `./.claude/` directory.

## 4. Implementation Phases

* **Phase 1: Enterprise Schema Deployment:** Provision the cloud database and run SQLAlchemy/Alembic migrations for the new Enterprise schema.
* **Phase 2: Repository Implementation:** Write the `EnterpriseArtifactRepository` and `EnterpriseCollectionRepository` classes.
* **Phase 3: Deployment & Sync Refactor:** Update the CLI `deploy` and `sync` commands to interact with the API content delivery endpoints rather than local paths when running in Enterprise mode.
* **Phase 4: Cloud Migration Tooling:** Build a CLI command (`skillmeat enterprise migrate`) that reads the `LocalFileSystemRepository`, authenticates via PAT, and pushes all local artifacts to the `EnterpriseDBRepository` endpoints.
