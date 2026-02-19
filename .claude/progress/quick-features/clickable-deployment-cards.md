---
feature: clickable-deployment-cards
status: completed
scope: frontend
files_affected:
- skillmeat/web/app/collection/page.tsx
estimated_complexity: simple
schema_version: 2
doc_type: quick_feature
feature_slug: clickable-deployment-cards
---

# Clickable Deployment Cards in Artifact Modals

## Problem

The Collection page uses `ArtifactDetailsModal` which lacks a Deployments tab entirely.
The `CollectionArtifactModal` wrapper (which wraps `UnifiedEntityModal` with deployments
tab and clickable cards) already exists but isn't used on the Collection page.

Project pages already work correctly - `ProjectArtifactModal` wraps `UnifiedEntityModal`
with `onNavigateToDeployment` wired up.

## Solution

Replace `ArtifactDetailsModal` with `CollectionArtifactModal` on the Collection page.

The `CollectionArtifactModal` already:
- Wraps `UnifiedEntityModal` which has the Deployments tab
- Implements `handleNavigateToDeployment` (base64-encodes project path, navigates to manage page)
- Implements `handleNavigateToSource` (navigates to marketplace source page)
- Supports `initialTab` and `onTabChange` props for URL state sync

## Tasks

- [x] TASK-1: Replace ArtifactDetailsModal import with CollectionArtifactModal on collection page
- [ ] TASK-2: Adapt tab type from ArtifactDetailsTab to ArtifactModalTab
- [ ] TASK-3: Handle any prop differences (onDelete, returnTo)
- [ ] TASK-4: Run quality gates (typecheck, lint, build)
