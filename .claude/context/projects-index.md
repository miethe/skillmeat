---
title: Projects & Deployments - Complete Index
description: Navigation guide for project-level artifact management documentation
---

# Projects & Deployments - Complete Index

## Quick Start

**New to projects?** Start here:

1. **[Project Architecture](./project-artifact-management.md#overview)** - Understand what a project is
2. **[Deployment Workflow](./project-artifact-management.md#deployment-workflow)** - How artifacts are deployed
3. **[API Quick Reference](./project-management-quick-ref.md#api-endpoints)** - Available endpoints
4. **[Common Workflows](./project-artifact-management.md#common-workflows)** - Real-world examples

## Documentation Map

### Core Concepts

| Topic | Document | Section |
|-------|----------|---------|
| What is a Project? | project-artifact-management.md | [Project Definition](./project-artifact-management.md#project-definition) |
| Project Structure | project-artifact-management.md | [Overview](./project-artifact-management.md#overview) |
| Deployment Metadata | project-artifact-management.md | [Deployment Metadata](./project-artifact-management.md#deployment-metadata-skillmeat-deployedtoml) |
| Project Metadata | project-artifact-management.md | [Project Metadata](./project-artifact-management.md#project-metadata-skillmeat-projecttoml) |
| Artifact Scopes | project-artifact-management.md | [Artifact Scopes](./project-artifact-management.md#artifact-scopes-user-vs-local) |

### Implementation Guide

| Topic | Document | Section |
|-------|----------|---------|
| Core Classes | project-management-quick-ref.md | [Key Classes](./project-management-quick-ref.md#key-classes) |
| Deployment Manager | project-artifact-management.md | [Deploy Artifacts](./project-artifact-management.md#deploy-artifacts-core-logic) |
| Deployment Tracker | project-management-quick-ref.md | [DeploymentTracker](./project-management-quick-ref.md#deploymenttracker) |
| Project Registry | project-artifact-management.md | [Project Registry](./project-artifact-management.md#project-registry--discovery) |
| Project Discovery | project-artifact-management.md | [Project Discovery](./project-artifact-management.md#project-discovery) |

### API Reference

| Endpoint | Document | Deployment | Projects |
|----------|----------|------------|----------|
| Deploy | Quick Ref | [Endpoint](./project-management-quick-ref.md#deployment-endpoints) | - |
| Undeploy | Quick Ref | [Endpoint](./project-management-quick-ref.md#deployment-endpoints) | - |
| List Deployments | Quick Ref | [Endpoint](./project-management-quick-ref.md#deployment-endpoints) | - |
| List Projects | architecture.md | - | [GET /projects](./project-artifact-management.md#get-apiv1projects) |
| Create Project | architecture.md | - | [POST /projects](./project-artifact-management.md#post-apiv1projects) |
| Get Project | architecture.md | - | [GET /projects/{id}](./project-artifact-management.md#get-apiv1projectsproject_id) |
| Update Project | architecture.md | - | [PUT /projects/{id}](./project-artifact-management.md#put-apiv1projectsproject_id) |
| Delete Project | architecture.md | - | [DELETE /projects/{id}](./project-artifact-management.md#delete-apiv1projectsproject_id) |
| Remove Deployment | architecture.md | - | [DELETE /projects/{id}/deployments/{artifact}](./project-artifact-management.md#delete-apiv1projectsproject_iddeploymentsartifact_name) |
| Check Modifications | architecture.md | - | [POST /projects/{id}/check-modifications](./project-artifact-management.md#post-apiv1projectsproject_idcheck-modifications) |
| Drift Summary | architecture.md | - | [GET /projects/{id}/drift/summary](./project-artifact-management.md#get-apiv1projectsproject_iddriftsummary) |

### Technical Details

| Topic | Document | Section |
|-------|----------|---------|
| TOML Format | architecture.md | [Example TOML](./project-artifact-management.md#example-toml) |
| Artifact Paths | architecture.md | [Artifact Path Resolution](./project-artifact-management.md#artifact-path-resolution) |
| Directory vs File Artifacts | architecture.md | [Directory vs File-Based](./project-artifact-management.md#directory-vs-file-based-artifacts) |
| Content Hash | architecture.md | [Content Hash](./project-artifact-management.md#content-hash-sha-256) |
| Version Lineage | architecture.md | [Version Lineage](./project-artifact-management.md#version-lineage) |
| Merge Base Snapshot | architecture.md | [Merge Base Snapshot](./project-artifact-management.md#merge-base-snapshot) |
| Drift Detection | architecture.md | [Drift Detection](./project-artifact-management.md#drift-detection) |
| Path Validation | architecture.md | [Path Validation](./project-artifact-management.md#path-validation) |

### Code Examples

| Use Case | Document | Section |
|----------|----------|---------|
| Deploy Single Artifact | quick-ref.md | [Deploy Single](./project-management-quick-ref.md#deploy-single-artifact) |
| Detect Modifications | quick-ref.md | [Detect Modifications](./project-management-quick-ref.md#detect-modifications) |
| List All Projects | quick-ref.md | [List Projects](./project-management-quick-ref.md#list-all-projects) |
| Deploy via API | quick-ref.md | [API Deploy](./project-management-quick-ref.md#api-deploy-via-curl) |
| Full Workflows | architecture.md | [Workflows](./project-artifact-management.md#common-workflows) |

## File Organization

```
skillmeat/
├── core/
│   └── deployment.py                    # Deployment, DeploymentManager
├── storage/
│   ├── deployment.py                    # DeploymentTracker (TOML I/O)
│   └── project.py                       # ProjectMetadata, ProjectMetadataStorage
├── api/
│   ├── routers/
│   │   ├── deployments.py              # Deployment API endpoints
│   │   └── projects.py                 # Project management API endpoints
│   ├── project_registry.py             # ProjectRegistry (cached discovery)
│   └── schemas/
│       └── projects.py                 # API response schemas
└── .claude/
    └── context/
        ├── project-artifact-management.md       # This guide
        ├── project-management-quick-ref.md      # Quick reference
        └── projects-index.md                    # This index
```

## Key Classes Reference

### Core Logic

| Class | File | Purpose |
|-------|------|---------|
| `Deployment` | core/deployment.py | Represents a deployed artifact |
| `DeploymentManager` | core/deployment.py | High-level deployment operations |
| `DeploymentTracker` | storage/deployment.py | TOML file I/O |
| `ProjectMetadata` | storage/project.py | Project metadata model |
| `ProjectMetadataStorage` | storage/project.py | Project metadata I/O |
| `ProjectRegistry` | api/project_registry.py | Cached project discovery |

### Data Models

| Model | File | Purpose |
|-------|------|---------|
| `ProjectCacheEntry` | api/project_registry.py | Cached project info |
| `ProjectSummary` | api/schemas/projects.py | API list response |
| `ProjectDetail` | api/schemas/projects.py | API detail response |
| `DeploymentInfo` | api/schemas/deployments.py | API deployment info |

## Common Tasks

### As a Developer Implementing Features

1. **Adding deployment functionality**
   - Read: [Deployment Workflow](./project-artifact-management.md#deployment-workflow)
   - Reference: [DeploymentManager code](./project-management-quick-ref.md#deploymentmanager)
   - Files: `skillmeat/core/deployment.py`, `skillmeat/api/routers/deployments.py`

2. **Working with project metadata**
   - Read: [Project Metadata](./project-artifact-management.md#project-metadata-skillmeat-projecttoml)
   - Reference: [ProjectMetadataStorage](./project-management-quick-ref.md#projectmetadata)
   - Files: `skillmeat/storage/project.py`, `skillmeat/api/routers/projects.py`

3. **Adding new API endpoints**
   - Read: [Deployment API](./project-artifact-management.md#deployment-api-endpoints)
   - Reference: [API Endpoints](./project-management-quick-ref.md#api-endpoints)
   - Files: `skillmeat/api/routers/projects.py`, `skillmeat/api/schemas/projects.py`

### As a User Deploying Artifacts

1. **Deploy to a project**
   - Read: [Deploy Artifacts](./project-artifact-management.md#deployment-workflow)
   - Example: [Common Workflows](./project-artifact-management.md#common-workflows)

2. **Check deployment status**
   - API: [GET /api/v1/deploy](./project-management-quick-ref.md#deployment-endpoints)
   - CLI: `skillmeat list-deployments {project_path}`

3. **Detect modifications**
   - API: [POST /api/v1/projects/{id}/check-modifications](./project-artifact-management.md#post-apiv1projectsproject_idcheck-modifications)
   - CLI: `skillmeat check-drift {project_path}`

### As a Database Maintainer

1. **Understanding version tracking**
   - Read: [Version Tracking](./project-artifact-management.md#version-tracking)
   - Fields: `content_hash`, `version_lineage`, `merge_base_snapshot`

2. **Drift detection**
   - Read: [Drift Detection](./project-artifact-management.md#drift-detection)
   - API: [GET /api/v1/projects/{id}/drift/summary](./project-artifact-management.md#get-apiv1projectsproject_iddriftsummary)

## Related Documentation

- **[Artifact Management](../artifact-management.md)** - Collection-level artifacts
- **[Deployment Tracking](../deployment-tracking.md)** - Version and history (if exists)
- **[API Documentation](../../api/CLAUDE.md)** - FastAPI patterns
- **[Collection Architecture](./collection-architecture.md)** - Collection structure

## Quick Lookups

### Find a File
```bash
# Deployment TOML
{project_path}/.claude/.skillmeat-deployed.toml

# Project metadata TOML
{project_path}/.claude/.skillmeat-project.toml

# Python classes
grep -r "class Deployment" skillmeat/core/deployment.py
grep -r "class DeploymentTracker" skillmeat/storage/deployment.py
```

### API Endpoint Status

All deployment and project endpoints:
- ✅ Implemented: Deploy, Undeploy, List, Projects CRUD, Drift detection
- 🚧 In progress: None currently
- ❌ Not planned: None

### Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Deploy single artifact | ~100ms | + file copy time |
| List projects (cached) | <50ms | Uses ProjectRegistry |
| List projects (uncached) | 5-30s | Full filesystem scan |
| Check modifications | ~50-200ms | Hash computation |
| Drift detection | 100-500ms | Comparing with collection |

## Related Discussions

- **ADR-004**: Version tracking and merge bases
- **SVCV-003**: Auto-snapshots after deployment
- **TASK-2.3**: Cache database for version records
- **TASK-4.3**: Drift summary count calculations

## Questions? See:

- **"How do I deploy?"** → [Deployment Workflow](./project-artifact-management.md#deployment-workflow)
- **"What's the TOML format?"** → [Deployment Metadata](./project-artifact-management.md#deployment-metadata-skillmeat-deployedtoml)
- **"What APIs are available?"** → [API Endpoints](./project-management-quick-ref.md#api-endpoints)
- **"How do I check modifications?"** → [Modification Detection](./project-artifact-management.md#modification-detection)
- **"What are artifact scopes?"** → [Artifact Scopes](./project-artifact-management.md#artifact-scopes-user-vs-local)

