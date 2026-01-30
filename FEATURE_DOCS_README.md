# SkillMeat Feature Documentation

Complete feature catalog and UI reference for screenshot planning and development.

**Generated**: 2026-01-29 | **Status**: Complete | **Scope**: Full Web UI

---

## Quick Start

### For Screenshot Planning

Use **FEATURE_CATALOG_SUMMARY.md** for quick lookups:
- Pages at a glance table
- Modal quick reference
- Common workflows
- Filter matrix
- API endpoint summary

### For Detailed Reference

Use **FEATURE_CATALOG.md** for complete details:
- All 22 pages documented
- Every modal described
- Component inventory
- API endpoints with descriptions
- Dashboard widgets
- Filter/sort specifications

### For Organization Overview

Use **FEATURE_INDEX.md** for structure and relationships:
- Navigation hierarchy
- Complete page inventory with features
- Component organization
- Data models
- Statistics and metrics
- Performance characteristics

---

## Document Map

### FEATURE_CATALOG_SUMMARY.md (505 lines)

**Quick Reference** - Perfect for finding what you need fast

Sections:
- Pages at a glance (table)
- Filter & sort quick reference
- Modal catalog (by category)
- Key components by category
- API endpoint quick reference
- Data structures
- Common UI states
- Common workflows
- Performance characteristics

**Best for**: When you know what you're looking for and need quick details

---

### FEATURE_CATALOG.md (1,456 lines)

**Complete Reference** - Comprehensive documentation of every feature

Sections:
1. **Main Navigation** - All sidebar/menu options
2. **Pages & Views** (13 pages documented):
   - Dashboard
   - Collection (with all UI elements)
   - Manage
   - Projects + sub-pages
   - Deployments
   - Marketplace (+ Sources, Listings, Publish)
   - Groups
   - Context Entities
   - Templates
   - MCP Servers
   - Settings
   - Sharing

3. **Reusable Components** (100+)
   - Organized by domain
   - Path and purpose for each

4. **Forms & Modals** (40+)
   - By domain
   - Trigger and purpose

5. **Dashboard Widgets** - All analytics components

6. **Filtering & Sorting** - Complete filter specifications

7. **API Endpoints** - 150+ endpoints across 15 routers

8. **Key UI Patterns** - Design patterns used throughout

9. **Summary Statistics**

**Best for**: When you need comprehensive details about a specific page or feature

---

### FEATURE_INDEX.md (763 lines)

**Organization Overview** - Structure and relationships

Sections:
1. **Executive Summary** - Total inventory
2. **Feature Matrix** - Navigation structure visualization
3. **Complete Page Inventory** - All pages grouped by category
4. **Complete Modal Inventory** - 40+ modals organized by domain
5. **Component Hierarchy** - Component organization by layer
6. **API Endpoint Organization** - By router and operation type
7. **Filter & Sort Matrix** - Summary of all filtering
8. **Data Model Summary** - Entity definitions
9. **Statistics & Metrics** - Counts and measurements
10. **Technology Stack**
11. **Navigation Patterns**
12. **Common User Workflows**
13. **Accessibility & Performance**
14. **Responsive Design**

**Best for**: When you need to understand the overall structure and relationships

---

## Feature Inventory Summary

### Pages (22 total)

**Core Collection**: 4 pages
- Dashboard, Collection, Manage, Groups

**Projects**: 3 pages
- Projects, Projects Detail, Projects Manage

**Deployments**: 1 page
- Deployments dashboard

**Marketplace**: 4 pages
- Marketplace, Sources, Source Detail, Listing Detail, Publish

**Configuration**: 5 pages
- Context Entities, Templates, MCP Servers, Settings, Sharing

### Key Features

**Artifact Types**: 5
- Skill, Command, Agent, MCP, Hook

**Sync States**: 6
- Synced, Modified, Outdated, Conflict, Error, Unknown

**View Modes**: 3+
- Grid (3-column responsive), List (table), Grouped

**Filters**: 8+ dimensions
- Type (6 options)
- Status (6 options)
- Scope (2-3 options)
- Tags (multi-select)
- Search (full-text)
- Trust level
- Artifact type
- Date range

**Sorting**: 4 primary options
- Confidence, Name, Updated Date, Usage Count

### Components & Modals

**Components**: 100+
- Organized into: Collection, Entity, Marketplace, Dashboard, MCP, Context, Template, Shared, UI Primitives

**Modals**: 40+
- Organized by domain: Collection (7), Entity (10), Marketplace (10), Project (5), Other (8)

### API Coverage

**Endpoints**: 150+
- 15 routers with complete CRUD
- By operation: 70+ GET, 35+ POST, 20+ PUT, 15+ DELETE

**Key Routers**:
1. Artifacts (50+)
2. User Collections (20+)
3. Groups (15+)
4. Projects (15+)
5. Deployments (20+)
6. Marketplace (25+)
7. Marketplace Catalog (10+)
8. Marketplace Sources (20+)
9. MCP (10+)
10. Context Entities (12+)
11. Templates (8+)
12. Tags (5+)
13. Bundles (8+)
14. Analytics (10+)
15. Health (3+)

---

## How to Use These Docs

### Use Case 1: Planning Screenshots

1. Open **FEATURE_CATALOG_SUMMARY.md**
2. Go to "Pages at a Glance" table
3. Find the page you want
4. Note the key UI elements
5. For more detail, check **FEATURE_CATALOG.md** page section

### Use Case 2: Finding a Specific Modal

1. Open **FEATURE_CATALOG_SUMMARY.md**
2. Go to "Modal Catalog"
3. Find modal by name or trigger
4. For full details, check **FEATURE_CATALOG.md** "Forms & Modals" section

### Use Case 3: Understanding a Component

1. Open **FEATURE_INDEX.md**
2. Go to "Component Hierarchy"
3. Find component by category
4. Note the path (e.g., `collection/collection-header.tsx`)
5. For usage, check **FEATURE_CATALOG.md** "Reusable Components" section

### Use Case 4: Implementing a Feature

1. Open **FEATURE_CATALOG_SUMMARY.md**
2. Check "Common Workflows" for your scenario
3. Note the pages, modals, and API calls involved
4. For detailed specs, check **FEATURE_CATALOG.md** for each page/modal
5. For API details, check API section

### Use Case 5: Understanding Page Structure

1. Open **FEATURE_INDEX.md**
2. Go to "Complete Page Inventory"
3. Find your page and read the detailed description
4. For UI element details, go to **FEATURE_CATALOG.md**
5. For component usage, cross-reference "Reusable Components"

---

## Key Statistics

| Category | Count |
|----------|-------|
| Pages | 22 |
| Modals | 40+ |
| Components | 100+ |
| API Endpoints | 150+ |
| Routers | 15 |
| Artifact Types | 5 |
| Sync States | 6 |
| Filter Dimensions | 8+ |
| Lines of Documentation | 2,724 |

---

## Navigation Hierarchy

```
Root (/)
├── Dashboard
├── Collection          (browse & manage)
├── Manage              (by type)
├── Projects            (deployments)
│   ├── [id]/
│   ├── [id]/settings/
│   └── [id]/manage/
├── Deployments         (dashboard)
├── Marketplace         (bundles)
│   ├── sources/        (GitHub)
│   │   └── [id]/       (detail)
│   ├── [listing_id]/   (listing)
│   └── publish/        (wizard)
├── Groups              (by group)
├── Context Entities    (config)
├── Templates           (quick setup)
├── MCP Servers         (protocols)
├── Settings            (config)
└── Sharing             (bundles)
```

---

## Quick Reference Tables

### Pages by Category

**Core Collection (4)**
- Dashboard, Collection, Manage, Groups

**Project Management (3)**
- Projects, Projects Detail, Projects Manage

**Deployment (1)**
- Deployments

**Marketplace (4)**
- Marketplace, Sources, Listing Detail, Publish

**Configuration (5)**
- Context Entities, Templates, MCP Servers, Settings, Sharing

### Filter Options Summary

```
Collection Page Filters:
  Type:   [All, Skill, Command, Agent, MCP, Hook]
  Status: [All, Synced, Modified, Outdated, Conflict, Error]
  Scope:  [All, User, Local]
  Tags:   [Multi-select, dynamic]
  Search: [Full-text]

Deployments Filters:
  Status: [All, Synced, Modified, Outdated, Conflict, Error]
  Type:   [Multi-select from 5 types]
  Search: [Artifact name]

Marketplace Filters:
  Broker:    [Multi-select]
  Category:  [Type filter]
  Rating:    [Range]
  Date:      [Range]
  Search:    [Full-text]

Sources Filters:
  Type:       [Artifact type]
  Trust:      [High/Medium/Low]
  Tags:       [Multi-select]
  Search:     [FTS5 query]
```

### Sort Options Summary

```
Collection Page Sort:
  • Confidence (descending)
  • Name (alphabetical, toggle)
  • Updated Date (newest first)
  • Usage Count (most used first)

Deployments Sort:
  • By project (implicit)
  • By date (implicit)
```

---

## For Different Roles

### Screenshot Planner

**Start with**: FEATURE_CATALOG_SUMMARY.md
- Pages at a glance
- Modal catalog
- Filter matrix
- Common workflows

### Feature Developer

**Start with**: FEATURE_CATALOG.md
- Detailed page specs
- Component inventory
- API endpoint details
- Modal specifications

### Architect

**Start with**: FEATURE_INDEX.md
- Navigation hierarchy
- Component organization
- API organization
- Data models
- Technology stack

### QA/Tester

**Start with**: FEATURE_CATALOG_SUMMARY.md → FEATURE_CATALOG.md
- Common workflows (for test scenarios)
- Filter combinations (for edge cases)
- Empty/error states (for negative tests)
- Modals and dialogs (for interaction tests)

### Product Manager

**Start with**: FEATURE_INDEX.md → FEATURE_CATALOG_SUMMARY.md
- Feature inventory (FEATURE_INDEX.md)
- Workflow descriptions (FEATURE_CATALOG_SUMMARY.md)
- Page purposes (FEATURE_CATALOG.md)

---

## Common Questions Answered

**Q: How many pages are there?**
A: 22 total pages (14 main + 8 sub-pages). See FEATURE_INDEX.md "Complete Page Inventory"

**Q: What artifacts types are supported?**
A: 5 types - Skill, Command, Agent, MCP, Hook. See FEATURE_CATALOG_SUMMARY.md

**Q: How many modals exist?**
A: 40+ modals. Complete list in FEATURE_CATALOG_SUMMARY.md "Modal Catalog"

**Q: What are all the filters available?**
A: Varies by page. See FEATURE_CATALOG_SUMMARY.md "Filter & Sort Quick Reference"

**Q: What's the API endpoint count?**
A: 150+ endpoints across 15 routers. See FEATURE_INDEX.md "API Endpoint Organization"

**Q: How are components organized?**
A: By domain (Collection, Entity, Marketplace, etc.). See FEATURE_INDEX.md "Component Hierarchy"

**Q: What are the sync states?**
A: 6 states - Synced, Modified, Outdated, Conflict, Error, Unknown. See FEATURE_CATALOG.md "Type System"

---

## File Locations in Codebase

### Pages

```
skillmeat/web/app/
├── page.tsx                          # Dashboard (/)
├── collection/page.tsx               # Collection
├── manage/page.tsx                   # Manage
├── groups/page.tsx                   # Groups
├── projects/page.tsx                 # Projects
├── projects/[id]/page.tsx            # Project Detail
├── projects/[id]/settings/page.tsx   # Project Settings
├── projects/[id]/manage/page.tsx     # Project Manage
├── deployments/page.tsx              # Deployments
├── marketplace/page.tsx              # Marketplace
├── marketplace/sources/page.tsx       # Sources
├── marketplace/sources/[id]/page.tsx # Source Detail
├── marketplace/[listing_id]/page.tsx # Listing Detail
├── marketplace/publish/page.tsx      # Publish
├── context-entities/page.tsx         # Context Entities
├── templates/page.tsx                # Templates
├── mcp/page.tsx                      # MCP Servers
├── mcp/[name]/page.tsx              # MCP Detail
├── settings/page.tsx                 # Settings
└── sharing/page.tsx                  # Sharing
```

### Components

```
skillmeat/web/components/
├── collection/          # Collection domain
├── entity/              # Entity/Manage domain
├── marketplace/         # Marketplace domain
├── dashboard/           # Dashboard widgets
├── mcp/                 # MCP components
├── context/             # Context entity components
├── templates/           # Template components
├── shared/              # Cross-domain shared components
└── ui/                  # shadcn/ui primitives
```

### API Routers

```
skillmeat/api/routers/
├── artifacts.py               # Artifact management
├── collections.py             # Collections (deprecated)
├── user_collections.py        # User collections (CRUD)
├── groups.py                  # Group management
├── deployments.py             # Deployment operations
├── projects.py                # Project management
├── marketplace.py             # Marketplace listings
├── marketplace_catalog.py      # Catalog management
├── marketplace_sources.py      # GitHub sources
├── mcp.py                      # MCP servers
├── context_entities.py         # Context entities
├── project_templates.py        # Templates
├── tags.py                     # Tag operations
├── bundles.py                  # Bundle management
├── analytics.py                # Analytics data
├── cache.py                    # Cache management
├── ratings.py                  # Rating/review
├── merge.py                    # Merge operations
├── versions.py                 # Version management
├── context_sync.py             # Context synchronization
├── settings.py                 # App settings
└── health.py                   # Health checks
```

---

## Document Conventions

### Naming

- **Pages**: Full URL path shown with `/`
- **Components**: CamelCase with `.tsx` extension
- **Modals**: Referred to by purpose (e.g., "Create Collection Dialog")
- **Endpoints**: Path format `/api/v1/route`

### Formatting

- **Code snippets**: Monospace for file paths, endpoint names
- **Tables**: Used for quick reference matrices
- **Lists**: Hierarchical when showing structure
- **Callouts**: Special sections highlighted

### Cross-References

- Files reference other docs with relative paths
- Sections use markdown anchors (#)
- Table of contents at top of each document

---

## Notes & Future Enhancements

**Current State**:
- Comprehensive UI documentation
- All pages, modals, and components catalogued
- Complete API endpoint reference
- Filter/sort specifications documented

**Potential Enhancements**:
- Screenshot examples (visual reference)
- Video walkthroughs of workflows
- Interactive component explorer
- Accessibility audit
- Performance baseline metrics
- Load testing results
- User persona workflows
- Keyboard shortcut guide (if implemented)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-29 | 1.0 | Initial complete catalog |

---

## Support

For questions about:
- **Specific pages**: See FEATURE_CATALOG.md
- **Quick lookups**: See FEATURE_CATALOG_SUMMARY.md
- **Organization**: See FEATURE_INDEX.md
- **Architecture**: See skillmeat/web/CLAUDE.md and skillmeat/api/CLAUDE.md

---

**Total Documentation**: 2,724 lines across 3 files

Start with the appropriate document for your use case above.
