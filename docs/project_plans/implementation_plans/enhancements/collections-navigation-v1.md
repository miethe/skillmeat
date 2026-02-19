---
title: Collections & Site Navigation Enhancement
version: 1.0
status: inferred_complete
priority: high
date_created: 2025-12-12
estimated_effort: 65 story points
timeline: 6 weeks
complexity: large
contributors:
- architecture-team
- frontend-team
- backend-team
tags:
- navigation
- collections
- ui-redesign
- caching
---
# Implementation Plan: Collections & Site Navigation Enhancement

**Complexity**: L (Large) | **Track**: Full | **Model**: Haiku Orchestration
**Estimated Effort**: 65 story points | **Timeline**: 6 weeks | **Priority**: High

---

## Executive Summary

This comprehensive enhancement restructures the SkillMeat navigation and artifact management system to support a unified Collections-centric experience. Currently, the `/collection` and `/manage` pages serve overlapping functions, creating confusion. This plan transforms the architecture into a clear, hierarchical structure:

- **Navigation**: Collections (parent) → Manage | Projects | MCP Servers (nested)
- **Collection Page**: Primary interface for browsing, organizing artifacts across collections
- **Groups**: User-defined custom groupings within collections for flexible organization
- **Deployment Dashboard**: Repurposed /manage page showing cross-project deployment status
- **Caching**: Intelligent local artifact caching with background refresh

The implementation follows the MeatyPrompts layered architecture pattern: Database → Repository → Service → API → Frontend, with strict separation of concerns and comprehensive type safety.

---

## Key Features Overview

### 1. Navigation Restructuring
- Parent "Collections" tab in sidebar leading to /collection page
- Nested tabs: Manage, Projects, MCP Servers
- Collapsible sidebar section with dynamic state management

### 2. Collection Page Enhancement
- Dropdown selector to switch between collections (with "Add Collection" and "All Collections" options)
- Support for three view modes: Grid, List, Grouped
- Advanced filtering, search, and sorting capabilities
- Integrated artifact card actions (ellipsis menu)

### 3. Custom Groups System
- Create, rename, delete groups within each collection
- Drag-and-drop artifact reordering between groups
- Group membership management via modal dialog
- Grouped view to visualize artifact organization

### 4. Deployment Dashboard
- Repurposed /manage page showing deployment status across projects
- Quick actions for "Deploy to New Project" and "View Deployments"
- New "Deployments" tab in unified modal with detailed information
- Deployment status indicators (active, inactive, version mismatch)

### 5. Multiple Collections Management
- Create, rename, delete collections
- Move/copy artifacts between collections with confirmation dialog
- Bulk operations support
- Collection switcher with easy navigation

### 6. Unified Artifact Modal Enhancement
- New "Collections/Groups" tab
- Hierarchical display: Collections → Groups
- Management buttons for group and collection operations
- Seamless integration with existing tabs

### 7. Advanced Caching
- Startup: Pull all artifacts from manifests and API
- Local SQLite cache with artifact metadata
- Background refresh every 5-10 minutes
- Manual refresh button on UI
- Persistent cache across app restarts
- Fallback to cached data if API unreachable

---

## Phase Overview

| Phase | Title | Focus Area | Story Points | Duration | Status |
|-------|-------|-----------|--------------|----------|--------|
| [Phase 1](#phase-1-database-layer) | Database Layer | SQLAlchemy models & Alembic migrations | 8 | 1 week | Planning |
| [Phase 2](#phase-2-backend-api) | Backend API | Collections/Groups CRUD + associations | 12 | 1.5 weeks | Planning |
| [Phase 3](#phase-3-frontend-foundation) | Frontend Foundation | Navigation, types, hooks, context | 10 | 1.5 weeks | Planning |
| [Phase 4](#phase-4-collection-features) | Collection Features | Collection UI, cards, modals | 15 | 1.5 weeks | Planning |
| [Phase 5](#phase-5-groups-deployment) | Groups & Deployment | Groups UI, Deployment Dashboard | 12 | 1.5 weeks | Planning |
| [Phase 6](#phase-6-caching-polish) | Caching & Polish | Local cache, refresh, testing | 8 | 1 week | Planning |

**Total**: 65 story points across 6 weeks

---

## Phase 1: Database Layer

**Duration**: 1 week | **Story Points**: 8

**Objective**: Establish SQLAlchemy models and Alembic migrations for Collections and Groups functionality.

### Key Deliverables

1. **Collection Model**: SQLAlchemy ORM model for user collections
2. **Group Model**: Custom grouping within collections
3. **CollectionArtifact Association**: Track artifact membership
4. **GroupArtifact Association**: Track group membership
5. **Alembic Migrations**: Database schema versioning
6. **Indexes & Constraints**: Performance optimization

### Assigned Subagents

- **data-layer-expert**: Database design and optimization
- **python-backend-engineer**: Schema implementation and migrations

### Details

See: [Phase 1 - Database Layer](./collections-navigation-v1/phase-1-database.md)

---

## Phase 2: Backend API

**Duration**: 1.5 weeks | **Story Points**: 12

**Objective**: Implement FastAPI routers and schemas for Collections and Groups management.

### Key Deliverables

1. **Collections Router**: CRUD endpoints for collections
2. **Groups Router**: CRUD endpoints for groups
3. **Artifact-Collection Associations**: Link/unlink operations
4. **Artifact-Group Associations**: Group membership management
5. **Deployment Summary Endpoints**: Cross-project deployment data
6. **Schema Updates**: Request/response models

### Assigned Subagents

- **python-backend-engineer**: API implementation
- **backend-architect**: Architecture review and validation

### Details

See: [Phase 2 - Backend API](./collections-navigation-v1/phase-2-backend-api.md)

---

## Phase 3: Frontend Foundation

**Duration**: 1.5 weeks | **Story Points**: 10

**Objective**: Create foundational React components, hooks, and context providers.

### Key Deliverables

1. **Navigation Restructuring**: Collapsible Collections section
2. **TypeScript Types**: Collection, Group, CollectionArtifact types
3. **useCollections Hook**: Fetch and manage collections
4. **useGroups Hook**: Fetch and manage groups
5. **CollectionContext Provider**: Shared state management
6. **API Integration**: TanStack Query setup

### Assigned Subagents

- **ui-engineer-enhanced**: Frontend structure and components
- **frontend-developer**: React patterns and hooks

### Details

See: [Phase 3 - Frontend Foundation](./collections-navigation-v1/phase-3-frontend-foundation.md)

---

## Phase 4: Collection Features

**Duration**: 1.5 weeks | **Story Points**: 15

**Objective**: Build the primary Collection page interface and artifact management UI.

### Key Deliverables

1. **Collection Page Redesign**: View modes, filtering, search
2. **Collection Switcher**: Dropdown with collection selection
3. **All Collections View**: Aggregated artifact listing
4. **Create/Edit Collection Dialogs**: Collection management
5. **Move/Copy to Collections Dialog**: Bulk artifact operations
6. **Artifact Card Enhancements**: Ellipsis menu with actions
7. **Unified Modal Collections/Groups Tab**: Display and manage memberships

### Assigned Subagents

- **ui-engineer-enhanced**: Component design and implementation
- **frontend-developer**: Integration and state management

### Details

See: [Phase 4 - Collection Features](./collections-navigation-v1/phase-4-collection-features.md)

---

## Phase 5: Groups & Deployment Dashboard

**Duration**: 1.5 weeks | **Story Points**: 12

**Objective**: Implement custom groups system and repurpose /manage as Deployment Dashboard.

### Key Deliverables

1. **Grouped View**: Display artifacts organized by groups
2. **Drag-and-Drop**: Reorder artifacts between groups
3. **Manage Groups Dialog**: CRUD for groups
4. **Deployment Dashboard**: Cross-project deployment overview
5. **Deployment Cards**: Quick actions and status indicators
6. **Deployments Tab**: Unified modal enhancement
7. **Deployment Filtering**: Status, project, version filters

### Assigned Subagents

- **ui-engineer-enhanced**: Complex UI components and interactions
- **frontend-developer**: State management and drag-drop implementation

### Details

See: [Phase 5 - Groups & Deployment Dashboard](./collections-navigation-v1/phase-5-groups-deployment.md)

---

## Phase 6: Caching & Polish

**Duration**: 1 week | **Story Points**: 8

**Objective**: Implement intelligent caching, background refresh, and comprehensive testing.

### Key Deliverables

1. **Local Artifact Cache**: SQLite-based cache for collection data
2. **Background Refresh**: Periodic cache updates without blocking UI
3. **Persistent Cache**: Cache survives app restarts
4. **Manual Refresh Button**: UI control for on-demand refresh
5. **Cache Invalidation**: Smart invalidation on mutations
6. **Testing Suite**: Unit, integration, E2E tests
7. **Documentation**: API docs, user guide updates

### Assigned Subagents

- **python-backend-engineer**: Cache implementation and refresh logic
- **ui-engineer-enhanced**: UI controls and feedback
- **testing-specialist**: Comprehensive test coverage

### Details

See: [Phase 6 - Caching & Polish](./collections-navigation-v1/phase-6-caching-polish.md)

---

## Risk Mitigation

### High Risks

| Risk | Impact | Mitigation | Owner |
|------|--------|-----------|-------|
| Complex state management | Bugs, performance issues | Implement unified CollectionContext early (Phase 3) | Frontend Team |
| Database migration complexity | Data loss, inconsistency | Test migrations thoroughly with sample data | Data Layer |
| UI/UX complexity | User confusion | Iterative validation with stakeholders | Design Team |
| Performance with large collections | Slow loading, poor UX | Implement pagination, caching, indexing | Backend Team |

### Medium Risks

| Risk | Impact | Mitigation | Owner |
|------|--------|-----------|-------|
| API contract changes | Breaking changes downstream | Use versioning, deprecation warnings | Backend Team |
| Drag-drop implementation | Accessibility issues | Test with keyboard, screen readers (Phase 5) | Frontend Team |
| Cache staleness | Data inconsistency | Implement background refresh, invalidation logic | Backend Team |

---

## Success Metrics

### Functional Metrics
- All 8 enhancement areas fully implemented and tested
- 95%+ test coverage for new code
- Zero critical bugs in production
- All acceptance criteria met

### Performance Metrics
- Collection page loads < 1 second (cached)
- Drag-drop operations smooth (60 fps)
- Cache reduces API calls by 80%
- Background refresh completes in < 5 seconds

### UX Metrics
- Navigation restructure reduces user confusion (measured via usage)
- 90%+ feature adoption within 2 weeks
- User satisfaction > 4/5 stars
- Deployment Dashboard saves > 30% time on deployment tasks

---

## Architecture Patterns

### MeatyPrompts Layered Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│ Presentation Layer (UI)                                         │
│ - Collection Page, Cards, Modals, Navigation                   │
├─────────────────────────────────────────────────────────────────┤
│ API Router Layer                                                │
│ - /api/v1/collections, /api/v1/groups, /api/v1/deployments   │
├─────────────────────────────────────────────────────────────────┤
│ Service Layer                                                   │
│ - CollectionService, GroupService, DeploymentService          │
├─────────────────────────────────────────────────────────────────┤
│ Repository Layer                                                │
│ - CollectionRepository, GroupRepository (with SQLAlchemy ORM)  │
├─────────────────────────────────────────────────────────────────┤
│ Database Layer                                                  │
│ - SQLAlchemy Models, Migrations, SQLite                        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Separation of Concerns**: Each layer has clear responsibilities
2. **Type Safety**: Full TypeScript on frontend, Pydantic models on backend
3. **Immutability**: React hooks follow immutable patterns
4. **Context Over Props**: Use CollectionContext for shared state (avoid prop drilling)
5. **Async-First**: All API calls properly handle loading/error states
6. **Caching Strategy**: HTTP cache (TanStack Query) + local SQLite cache

---

## Database Schema Overview

### Core Tables

```sql
-- Collections
CREATE TABLE collections (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  created_by TEXT
);

-- Groups
CREATE TABLE groups (
  id TEXT PRIMARY KEY,
  collection_id TEXT NOT NULL REFERENCES collections(id),
  name TEXT NOT NULL,
  description TEXT,
  position INT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  UNIQUE(collection_id, name)
);

-- Association: Collection ← → Artifact (many-to-many)
CREATE TABLE collection_artifacts (
  collection_id TEXT NOT NULL REFERENCES collections(id),
  artifact_id TEXT NOT NULL,
  added_at TIMESTAMP,
  PRIMARY KEY(collection_id, artifact_id)
);

-- Association: Group ← → Artifact (many-to-many)
CREATE TABLE group_artifacts (
  group_id TEXT NOT NULL REFERENCES groups(id),
  artifact_id TEXT NOT NULL,
  position INT,
  added_at TIMESTAMP,
  PRIMARY KEY(group_id, artifact_id)
);

-- Deployments (enhanced)
CREATE TABLE deployments (
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  deployed_version TEXT,
  latest_version TEXT,
  status TEXT,
  deployed_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## API Contract Overview

### Collections Endpoints

```
POST   /api/v1/collections                    # Create collection
GET    /api/v1/collections                    # List collections
GET    /api/v1/collections/{id}               # Get collection
PUT    /api/v1/collections/{id}               # Update collection
DELETE /api/v1/collections/{id}               # Delete collection
POST   /api/v1/collections/{id}/artifacts     # Add artifact to collection
DELETE /api/v1/collections/{id}/artifacts/{artifactId}  # Remove artifact
```

### Groups Endpoints

```
POST   /api/v1/groups                         # Create group
GET    /api/v1/groups?collection_id={id}     # List groups in collection
GET    /api/v1/groups/{id}                    # Get group
PUT    /api/v1/groups/{id}                    # Update group
DELETE /api/v1/groups/{id}                    # Delete group
POST   /api/v1/groups/{id}/artifacts          # Add artifact to group
DELETE /api/v1/groups/{id}/artifacts/{artifactId}  # Remove artifact
```

### Deployments Endpoints

```
GET    /api/v1/deployments                    # List all deployments
GET    /api/v1/deployments?artifact_id={id}  # Deployments for artifact
GET    /api/v1/deployments/summary            # Aggregated deployment summary
POST   /api/v1/deployments                    # Create deployment
PUT    /api/v1/deployments/{id}               # Update deployment
DELETE /api/v1/deployments/{id}               # Remove deployment
```

---

## Frontend Component Hierarchy

```
RootLayout
├── Header
└── Sidebar (Updated Navigation)
    ├── Collections (collapsible parent)
    │   ├── Manage
    │   ├── Projects
    │   └── MCP Servers
    └── CollectionPage
        ├── CollectionHeader
        │   ├── CollectionSwitcher
        │   └── ViewModeToggle
        ├── CollectionFilters
        ├── ArtifactGrid/List/Grouped
        │   └── ArtifactCard (with ellipsis menu)
        │       ├── MoveToCollectionDialog
        │       ├── ManageGroupsDialog
        │       └── ...actions
        ├── DeploymentDashboard (formerly Manage)
        │   ├── DeploymentFilter
        │   └── DeploymentCard (with quick actions)
        └── UnifiedArtifactModal
            ├── Overview tab
            ├── Collections/Groups tab (NEW)
            ├── Deployments tab (NEW)
            └── ...other tabs
```

---

## Quality Gates

### Phase 1 Quality Checklist
- [ ] Database schema reviewed by data-layer-expert
- [ ] Migrations tested with sample data (up/down)
- [ ] Foreign key constraints enforced
- [ ] Indexes created for performance-critical queries
- [ ] Schema documentation complete

### Phase 2 Quality Checklist
- [ ] All routers follow RESTful conventions
- [ ] Pydantic schemas validated with examples
- [ ] Error handling consistent (400, 404, 422, 500)
- [ ] CORS and auth middleware applied
- [ ] API docs auto-generated and accurate

### Phase 3 Quality Checklist
- [ ] Navigation structure validated in design
- [ ] TypeScript types fully strict (no `any`)
- [ ] Hooks follow React best practices
- [ ] Context provider properly memoized
- [ ] TanStack Query configured correctly

### Phase 4 Quality Checklist
- [ ] All view modes (Grid, List, Grouped) functional
- [ ] Filtering/search performant (< 500ms)
- [ ] Modals properly handle loading/error states
- [ ] Accessibility standards met (WCAG 2.1 AA)
- [ ] Component tests > 80% coverage

### Phase 5 Quality Checklist
- [ ] Drag-drop smooth and accessible
- [ ] Deployment Dashboard data accurate
- [ ] Quick actions properly validated
- [ ] Modal tabs properly integrated
- [ ] E2E tests cover critical flows

### Phase 6 Quality Checklist
- [ ] Cache logic thoroughly tested
- [ ] Background refresh doesn't block UI
- [ ] Cache persists across restarts
- [ ] Manual refresh works reliably
- [ ] All tests pass (unit, integration, E2E)

---

## Git Strategy

Each phase will have:
1. Feature branch: `feat/collections-nav-phase-X`
2. Pull request with detailed description
3. Code review from backend-architect (Phase 2) or ui-designer (Phase 4)
4. Merge to `main` after CI passes

### Commit Conventions

```
feat(collections): Add Collection model and migrations (Phase 1)
feat(api): Add collections router endpoints (Phase 2)
feat(web): Restructure navigation sidebar (Phase 3)
feat(collection): Add collection switcher component (Phase 4)
feat(groups): Add Manage Groups dialog (Phase 5)
feat(cache): Add artifact cache and refresh logic (Phase 6)
```

---

## Testing Strategy

### Backend Testing (Phases 1-2)

- **Unit Tests**: Model relationships, queries
- **Integration Tests**: Router endpoints with mock data
- **Database Tests**: Migration up/down, constraints
- **Performance Tests**: Query optimization, N+1 detection

### Frontend Testing (Phases 3-6)

- **Unit Tests**: Components, hooks, utilities (Jest)
- **Integration Tests**: Component interactions (React Testing Library)
- **E2E Tests**: Critical user flows (Playwright)
- **Accessibility Tests**: WCAG 2.1 AA compliance
- **Performance Tests**: Component render times, bundle size

---

## Documentation

### Developer Documentation
- API endpoint reference (OpenAPI/Swagger)
- Database schema documentation
- React component API documentation
- Hook usage patterns and examples

### User Documentation
- Collection management guide
- Group organization best practices
- Deployment Dashboard usage
- Migration guide from old navigation

### Operational Documentation
- Cache management and troubleshooting
- Database backup/restore procedures
- Performance tuning guidelines
- Monitoring and alerting setup

---

## Dependencies & Prerequisites

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy, Alembic, Pydantic
- **Frontend**: Next.js 15, React 19, TypeScript, TanStack Query, Radix UI
- **Database**: SQLite (with WAL mode)

### External Dependencies
- GitHub API (for deployment status)
- Claude API (if needed for AI features)

### Team Skills Required
- Full-stack TypeScript/Python expertise
- Database design experience
- React hook patterns
- API design and REST conventions

---

## Rollback Plan

### If Critical Issues Arise

1. **Database**: Create backup before Phase 1 deployment
2. **API**: Maintain feature flags for new endpoints (Phase 2)
3. **Frontend**: Use feature toggles for new UI (Phases 3-6)
4. **Deployment**: Blue-green deployment strategy

### Rollback Checklist
- [ ] Data backup created and tested
- [ ] Feature flags implemented
- [ ] Previous API contracts maintained
- [ ] Rollback scripts prepared
- [ ] Team communication plan ready

---

## Success Criteria

All phases complete when:
1. All acceptance criteria met for each task
2. Test coverage > 85% (backend) and > 80% (frontend)
3. Performance metrics achieved
4. Code reviewed and approved
5. Documentation complete and accurate
6. No critical bugs in QA environment
7. Stakeholder sign-off obtained

---

## Next Steps

1. **Immediate**: Start Phase 1 (Database Layer) with data-layer-expert
2. **Week 1-2**: Parallelize Phase 2 (Backend API) and Phase 3 (Frontend Foundation)
3. **Week 3-4**: Focus on Phase 4 (Collection Features) with full team
4. **Week 5-6**: Complete Phases 5-6 with integration and testing

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-12 | Orchestrator | Initial implementation plan created |
| TBD | Team | Phase 1 complete |
| TBD | Team | Phase 2 complete |
| TBD | Team | Phase 3 complete |
| TBD | Team | Phase 4 complete |
| TBD | Team | Phase 5 complete |
| TBD | Team | Phase 6 complete |

---

## Contact & Questions

For questions about this implementation plan:
- **Architecture**: Review [Architecture Patterns](#architecture-patterns) section
- **Specific Phase**: See phase files in `collections-navigation-v1/` subdirectory
- **Timeline**: Adjust based on team capacity and priorities
