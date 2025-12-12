# Collections Navigation Enhancement - Context

**PRD**: collections-navigation-v1
**Status**: Planning Complete, Implementation Pending
**Start Date**: TBD
**Target Completion**: TBD

---

## High-Level Summary

This enhancement introduces Collections and Groups functionality to SkillMeat, enabling users to organize artifacts into custom collections and further organize them into groups within collections. Additionally, it converts the `/manage` page into a deployment-focused dashboard for better visibility of artifact deployments across projects.

### Core Features
1. **Collections**: User-defined collections of artifacts (e.g., "Work Skills", "Personal Projects")
2. **Groups**: Custom groupings within collections (e.g., "Python Skills", "JavaScript Skills" within "Work Skills")
3. **Deployment Dashboard**: Aggregated view of all deployments with filtering and status tracking
4. **Enhanced Navigation**: Collapsible Collections section in sidebar with drill-down navigation

---

## Architecture Overview

### Database Layer (Phase 1)
- **Collections Table**: Stores user collections (id, name, description, metadata)
- **Groups Table**: Stores groups within collections (id, collection_id, name, description, position)
- **CollectionArtifacts Association**: Many-to-many relationship between Collections and Artifacts
- **GroupArtifacts Association**: Many-to-many relationship between Groups and Artifacts (with position for ordering)

### Backend API (Phase 2)
- **Collections Router**: CRUD endpoints for collections (`/api/v1/collections`)
- **Groups Router**: CRUD endpoints for groups (`/api/v1/groups`)
- **Deployment Router**: Aggregated deployment endpoints (`/api/v1/deployments`)
- **Association Endpoints**: Add/remove/move/copy artifacts between collections and groups

### Frontend (Phases 3-5)
- **React Hooks**: useCollections, useGroups, useDeployments (TanStack Query)
- **Context**: CollectionContext for shared state across components
- **Pages**: Collection detail page, All Collections view, Deployment Dashboard
- **Components**: CollectionSwitcher, ManageGroupsDialog, DeploymentCard, GroupedView
- **Drag-and-Drop**: @dnd-kit for reordering artifacts within/between groups

### Caching & Performance (Phase 6)
- **SQLite Cache**: Local cache for frequently accessed artifact data (5-minute TTL)
- **Background Refresh**: Periodic cache updates every 5 minutes
- **Cache Persistence**: Cache survives server restarts

---

## Key Design Decisions

### 1. Collections vs Groups Hierarchy
- **Collections**: Top-level organizational unit (e.g., "Work", "Personal")
- **Groups**: Sub-organizational unit within collections (e.g., "Python Skills" within "Work")
- **Rationale**: Two-level hierarchy provides flexibility without excessive nesting

### 2. Many-to-Many Relationships
- Artifacts can belong to multiple collections
- Artifacts can belong to multiple groups across different collections
- **Rationale**: Flexibility in organization (e.g., "React Skill" in both "Work" and "Learning")

### 3. Position-Based Ordering
- Groups have `position` field for ordering within collection
- Artifacts have `position` field within groups (via association table)
- **Rationale**: Enables drag-and-drop reordering with stable sort order

### 4. Deployment Dashboard Redesign
- Convert `/manage` from CRUD-focused to deployment-focused
- Aggregated stats: total deployments, by status, by artifact, by project
- **Rationale**: Better visibility for multi-project artifact usage

### 5. Caching Strategy
- Cache artifact data at API layer (SQLite)
- Short TTL (5 minutes) to balance freshness vs performance
- Background refresh to keep cache warm
- **Rationale**: Reduce latency for frequently accessed data without staleness

### 6. Navigation Structure
- Collapsible "Collections" parent section in sidebar
- Dynamic child links for each collection
- "All Collections" and "Manage Groups" as fixed links
- **Rationale**: Scalable navigation that doesn't clutter sidebar with many collections

---

## Critical Implementation Notes

### Database Migrations
- Alembic migration must create 4 tables: collections, groups, collection_artifacts, group_artifacts
- Foreign keys with CASCADE delete for data consistency
- Indexes on commonly queried fields for performance
- **Gotcha**: Ensure proper cascade rules to prevent orphaned records

### API Performance
- Optimize queries to avoid N+1 problem (use selectin loading)
- Deployment summary endpoint must be <100ms even with 10K+ deployments
- Pagination required for large collections
- **Gotcha**: Deployment aggregation can be slow without proper indexes

### Frontend State Management
- CollectionContext provides current collection state
- TanStack Query handles caching and invalidation
- Optimistic updates for better UX
- **Gotcha**: Cache invalidation must happen after mutations to prevent stale data

### Drag-and-Drop
- @dnd-kit/core for all drag-drop functionality
- Persist position changes to backend immediately
- Rollback on error (optimistic update)
- **Gotcha**: Handle edge cases like dragging to empty groups

---

## Integration Points

### Existing Systems
1. **Artifact Management**: Collections and groups reference existing artifact IDs
2. **Project Cache**: Deployment data from project cache (existing)
3. **Web UI**: Integrate with existing layout, navigation, and artifact cards
4. **API Server**: Register new routers in server.py

### External Dependencies
- **@dnd-kit/core**: Drag-and-drop library for React
- **TanStack Query**: Data fetching and caching
- **Radix UI**: Dialogs, dropdowns, and other primitives
- **SQLAlchemy 2.0+**: ORM for database models
- **Alembic**: Database migrations

---

## Testing Strategy

### Phase-by-Phase Testing
- **Phase 1**: Unit tests for models, migration tests (up/down)
- **Phase 2**: Integration tests for API endpoints, schema validation
- **Phase 3**: Unit tests for hooks and context
- **Phase 4**: Component tests for dialogs, pages
- **Phase 5**: E2E tests for drag-drop, deployment dashboard
- **Phase 6**: Performance tests for caching

### Coverage Targets
- Backend: 85%+ (pytest-cov)
- Frontend: 80%+ (Jest)
- E2E critical paths: 100%

---

## Known Risks and Mitigation

### Risk 1: Performance Degradation
- **Concern**: Large collections (1000+ artifacts) may slow down UI
- **Mitigation**: Pagination, virtualization, caching, lazy loading

### Risk 2: Data Consistency
- **Concern**: Artifacts removed from collection while user viewing
- **Mitigation**: Optimistic updates, error handling, cache invalidation

### Risk 3: Migration Complexity
- **Concern**: Existing deployments may not map cleanly to new schema
- **Mitigation**: Thorough migration testing, rollback plan, data validation

### Risk 4: Drag-Drop UX
- **Concern**: Drag-drop may be confusing or unreliable
- **Mitigation**: Clear visual feedback, keyboard alternatives, undo functionality

---

## Files Modified (High-Level)

### Backend
- `/skillmeat/cache/models.py` - Add Collection, Group, association models
- `/skillmeat/cache/migrations/versions/` - New migration file
- `/skillmeat/api/routers/` - New routers for collections, groups, deployments
- `/skillmeat/api/schemas/` - New Pydantic schemas
- `/skillmeat/api/server.py` - Register routers

### Frontend
- `/skillmeat/web/lib/types/collections.ts` - TypeScript interfaces
- `/skillmeat/web/hooks/` - New hooks for collections, groups, deployments
- `/skillmeat/web/contexts/CollectionContext.tsx` - New context provider
- `/skillmeat/web/components/collections/` - New components for collections UI
- `/skillmeat/web/components/deployments/` - New components for deployments UI
- `/skillmeat/web/app/collections/` - Collection pages
- `/skillmeat/web/app/manage/` - Deployment dashboard

### Documentation
- `/docs/user-guide/collections.md` - User guide
- `/docs/user-guide/deployments.md` - Deployment guide
- `/docs/api/collections-api.md` - API reference
- `/docs/development/collections-architecture.md` - Architecture docs

---

## Success Metrics

### User Experience
- Average time to organize 10 artifacts: <2 minutes
- User satisfaction with collections: >80% positive feedback
- Deployment dashboard usage: >50% of weekly active users

### Performance
- Collections page load time: <1 second
- Deployment summary API: <100ms
- Cache hit rate: >80%
- No regressions in existing page load times

### Code Quality
- Test coverage: >85% backend, >80% frontend
- No critical bugs in production
- Code review approval from all stakeholders

---

## Rollback Plan

If critical issues arise:

1. **Database**: Rollback migration (`alembic downgrade -1`)
2. **API**: Remove router registrations from server.py
3. **Frontend**: Feature flag to hide Collections navigation
4. **Cache**: Clear cache and disable background refresh

**Recovery Time**: <1 hour to rollback to previous stable state

---

## Next Steps (Post-Implementation)

### Future Enhancements
1. **Collection Sharing**: Share collections between users (Phase 2)
2. **Collection Templates**: Pre-defined collections for common use cases
3. **Smart Groups**: Auto-populate groups based on rules (e.g., "All Python Skills")
4. **Collection Analytics**: Track artifact usage within collections
5. **Export/Import**: Export collections as JSON for backup/sharing

### Monitoring
- Track cache hit/miss rates
- Monitor deployment summary query performance
- Collect user feedback on collections UX
- Analyze most common collection/group patterns

---

## Key Takeaways for Future Development

1. **Progressive Disclosure**: Two-level hierarchy (collections → groups) strikes good balance
2. **Caching**: Local cache with background refresh significantly improves performance
3. **Drag-and-Drop**: @dnd-kit provides robust, accessible drag-drop experience
4. **State Management**: TanStack Query + React Context is effective for this use case
5. **Testing**: Comprehensive testing (unit, integration, E2E) prevents regressions

---

## References

- **PRD**: `/docs/project_plans/PRDs/enhancements/collections-navigation-v1.md`
- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/collections-navigation-v1.md`
- **Phase Plans**: `/docs/project_plans/implementation_plans/enhancements/collections-navigation-v1/phase-*.md`
- **Progress Tracking**: `.claude/progress/collections-navigation/phase-*-progress.md`

---

**Last Updated**: 2025-12-12
**Document Owner**: ai-artifacts-engineer
