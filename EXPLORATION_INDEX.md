# SkillMeat Codebase Exploration - Navigation Index

**Date**: December 12, 2025
**Explorer**: Codebase Exploration Agent (Haiku 4.5)
**Project**: SkillMeat - Personal Collection Manager for Claude Code Artifacts

---

## What Is This?

This is a comprehensive exploration of the SkillMeat web application architecture, created to provide a foundation for implementing Collections Navigation enhancements. Three detailed documents have been created to help you understand the codebase and plan new features.

---

## The Three Exploration Documents

### 1. **EXPLORATION_SUMMARY.md** ⭐ START HERE
**Best for**: Quick overview, architectural recommendations, implementation planning

**Contents**:
- What was explored (7 areas)
- Key findings and strengths
- Current limitations for collections
- Recommended architecture for collections navigation
- 4-phase implementation roadmap
- Code patterns to follow
- Estimated files to create/modify
- Next steps

**Read this if**: You need a high-level overview and want to start planning the collections feature

**Length**: ~360 lines, 15 minutes read

---

### 2. **CODEBASE_EXPLORATION_REPORT.md** 📚 DETAILED REFERENCE
**Best for**: Deep understanding, implementation details, integration points

**Contents**:
1. Executive Summary
2. Navigation & Sidebar (implementation, features, structure)
3. Collection Page (`/collection`) - components, state management, hierarchy
4. Manage Page (`/manage`) - layout, tabs, filters, actions
5. Artifact Cards & Modal - tabs, props, action menu
6. API Endpoints & Backend - routers, request/response types, endpoints
7. Database Models (SQLAlchemy) - marketplace models, cache layer
8. Caching Mechanism - frontend (TanStack Query) & backend (Python)
9. Existing Patterns - filtering, grouping, views, status states
10. Modal Tabs & Card Menu - tab structure, available actions
11. Key Files Reference - complete file structure
12. Technology Stack - frameworks, libraries, tools
13. Architectural Decisions - key design choices
14. Data Flow - collection/manage/modal interaction flows
15. Missing/Planned Features - future enhancements
16. Integration Points - where to add new features

**Read this if**: You're implementing features and need detailed reference material

**Length**: ~800 lines, 45 minutes thorough read

---

### 3. **QUICK_REFERENCE_COMPONENTS.md** 🔍 API LOOKUP
**Best for**: Quick component lookups, prop interfaces, hook signatures

**Contents**:
- Navigation components (Navigation, Header, Layout)
- Collection page components (Page, Grid, List, Filters)
- Manage page components (Page, Tabs, Filters, List)
- Unified modal components (Modal, DiffViewer, FileTree, etc.)
- Marketplace components (AddSourceModal, EditSourceModal, etc.)
- Hooks (useArtifacts, useEntityLifecycle, useMarketplaceSources, etc.)
- Entity types & configurations
- API request utilities
- Type definitions
- Environment variables
- Common patterns
- API response types

**Read this if**: You need quick reference for component props, hooks, or type definitions

**Length**: ~570 lines, reference-style (look up as needed)

---

## Reading Paths Based on Your Goal

### Goal: Understand Current Architecture
```
1. Read: EXPLORATION_SUMMARY.md (sections: "What Was Explored", "Key Findings")
2. Read: CODEBASE_EXPLORATION_REPORT.md (sections 1-4: Navigation, Collection, Manage)
3. Reference: QUICK_REFERENCE_COMPONENTS.md (Navigation & Collection components)
```

### Goal: Plan Collections Navigation Feature
```
1. Read: EXPLORATION_SUMMARY.md (entire document)
   - Especially: "Recommended Architecture", "Implementation Roadmap"
2. Reference: CODEBASE_EXPLORATION_REPORT.md
   - Section 15: "Integration Points for New Features"
   - Section 13: "Architectural Decisions"
3. Reference: QUICK_REFERENCE_COMPONENTS.md
   - For component patterns and hook signatures
```

### Goal: Implement Collections Feature
```
1. Read: EXPLORATION_SUMMARY.md
   - "Recommended Architecture for Collections Navigation"
   - "Code Patterns to Follow"
2. Deep dive: CODEBASE_EXPLORATION_REPORT.md
   - Section 9: "Existing Patterns" (filtering, grouping)
   - Section 10: "Modal Tabs & Card Menu"
   - Section 16: "Integration Points"
3. Reference as needed: QUICK_REFERENCE_COMPONENTS.md
   - For exact component props, hook signatures
```

### Goal: Add New API Endpoint
```
1. Reference: CODEBASE_EXPLORATION_REPORT.md
   - Section 5: "API Endpoints & Backend"
   - Section 6: "Database Models"
2. Reference: QUICK_REFERENCE_COMPONENTS.md
   - "API Request Utilities"
   - "API Response Types"
3. Check actual files:
   - /skillmeat/api/routers/artifacts.py (pattern reference)
   - /skillmeat/api/schemas/artifacts.py (schema pattern reference)
```

### Goal: Create New Frontend Component
```
1. Reference: CODEBASE_EXPLORATION_REPORT.md
   - Section 4: "Artifact Cards & Unified Modal"
   - Section 9: "Existing Patterns"
2. Reference: QUICK_REFERENCE_COMPONENTS.md
   - "Collection Page Components"
   - "Common Component Patterns"
3. Look at actual component:
   - /skillmeat/web/components/entity/unified-entity-modal.tsx
```

---

## Directory Structure of Explored Code

```
skillmeat/
├── web/                              # Next.js 15 frontend
│   ├── app/
│   │   ├── collection/              # Collection browser page
│   │   ├── manage/                  # Entity management page
│   │   ├── marketplace/             # Marketplace pages
│   │   └── layout.tsx               # Root layout
│   ├── components/
│   │   ├── navigation.tsx           # Sidebar nav
│   │   ├── header.tsx               # Top header
│   │   ├── entity/                  # Entity management components
│   │   ├── collection/              # Collection-specific components
│   │   ├── marketplace/             # Marketplace components
│   │   └── ui/                      # shadcn primitives
│   ├── hooks/
│   │   ├── useArtifacts.ts         # Collection data hook
│   │   ├── useEntityLifecycle.tsx  # Entity management hook
│   │   └── useMarketplaceSources.ts # Marketplace hook
│   ├── types/
│   │   ├── entity.ts               # Entity type definitions
│   │   ├── artifact.ts             # Artifact type definitions
│   │   └── marketplace.ts          # Marketplace types
│   └── lib/
│       └── api.ts                  # API client wrapper
│
└── api/                             # FastAPI backend
    ├── routers/
    │   ├── artifacts.py            # Artifact CRUD + deployment
    │   ├── collections.py          # Collection management
    │   ├── marketplace_sources.py   # GitHub source ingestion
    │   └── (other routers)
    ├── schemas/
    │   ├── artifacts.py            # Artifact request/response models
    │   ├── collections.py          # Collection schemas
    │   ├── marketplace.py          # Marketplace schemas
    │   └── (other schemas)
    └── server.py                   # FastAPI app setup
```

---

## Key Concepts Referenced

### Entity Types (5 Supported)
- **Skill**: Reusable Claude skills with markdown documentation
- **Command**: CLI-style commands for automation
- **Agent**: Multi-turn AI agents with specialized behaviors
- **MCP**: Model Context Protocol servers for tool integration
- **Hook**: Git hooks and automation triggers

### Scopes
- **User Scope**: Global artifacts in ~/.skillmeat/collection
- **Local Scope**: Project-specific artifacts in ./.claude/artifacts

### Status States
- **synced**: Entity matches collection version
- **modified**: Entity has local modifications
- **outdated**: Collection has newer version
- **conflict**: Unable to automatically merge

### Views
- **Grid View**: Card-based visual layout (default)
- **List View**: Table-style rows for quick scanning

---

## Important Files Referenced

### Frontend Core
| File | Purpose |
|------|---------|
| `/skillmeat/web/app/layout.tsx` | Root layout with Header + Navigation |
| `/skillmeat/web/app/collection/page.tsx` | Collection browser |
| `/skillmeat/web/app/manage/page.tsx` | Entity management dashboard |
| `/skillmeat/web/components/navigation.tsx` | Sidebar navigation |
| `/skillmeat/web/components/header.tsx` | Top header with notifications |
| `/skillmeat/web/components/entity/unified-entity-modal.tsx` | Main detail modal |

### Hooks
| File | Purpose |
|------|---------|
| `/skillmeat/web/hooks/useArtifacts.ts` | Collection data fetching |
| `/skillmeat/web/hooks/useEntityLifecycle.tsx` | Entity management state |
| `/skillmeat/web/hooks/useMarketplaceSources.ts` | Marketplace sources |

### Types
| File | Purpose |
|------|---------|
| `/skillmeat/web/types/entity.ts` | Entity interface + configurations |
| `/skillmeat/web/types/artifact.ts` | Artifact interface |
| `/skillmeat/web/types/marketplace.ts` | Marketplace types |

### Backend
| File | Purpose |
|------|---------|
| `/skillmeat/api/server.py` | FastAPI app setup |
| `/skillmeat/api/routers/artifacts.py` | Artifact endpoints |
| `/skillmeat/api/routers/marketplace_sources.py` | Marketplace endpoints |
| `/skillmeat/api/schemas/artifacts.py` | Pydantic models |

---

## Quick Facts

### Frontend Stack
- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **UI**: shadcn/ui + Radix UI primitives
- **Styling**: Tailwind CSS
- **State**: TanStack Query + React Context
- **Icons**: Lucide React

### Backend Stack
- **Framework**: FastAPI
- **Language**: Python 3.9+
- **Validation**: Pydantic
- **Storage**: File-based + SQLite (in progress)
- **ORM**: SQLAlchemy (in progress)

### Key Patterns
- **Hierarchical Query Keys**: `['artifacts', 'list', filters, sort]`
- **Mock Fallback**: All hooks fall back to mock data if API fails
- **Unified Modal**: Single modal for all entity types with context tabs
- **Provider Pattern**: `EntityLifecycleProvider` for entity state management

---

## How to Use These Documents

### For Code Review
```
1. Read EXPLORATION_SUMMARY.md (Key Findings section)
2. Reference CODEBASE_EXPLORATION_REPORT.md for specific details
3. Use QUICK_REFERENCE_COMPONENTS.md for prop verification
```

### For Feature Planning
```
1. Start with EXPLORATION_SUMMARY.md
2. Use "Recommended Architecture" section
3. Reference "Integration Points" in CODEBASE_EXPLORATION_REPORT.md
4. Create implementation plan based on 4-phase roadmap
```

### For Developer Onboarding
```
1. Reading Path: "Understand Current Architecture" above
2. Study the navigation and collection page flow
3. Examine unified modal implementation
4. Explore one hook (useArtifacts.ts recommended)
```

---

## What's NOT in This Exploration

These documents cover **web application architecture** specifically. The following are out of scope:

- CLI implementation (skillmeat command)
- Collection storage and manifest format
- Artifact source fetching (GitHub integration)
- Deployment execution
- Marketplace publishing
- MCP server setup
- Sync/merge algorithms (touch on, don't deep dive)

For these topics, refer to:
- `/skillmeat/cli.py` for CLI implementation
- `/skillmeat/core/` for business logic
- `/skillmeat/api/CLAUDE.md` for API details
- `/skillmeat/web/CLAUDE.md` for web-specific documentation

---

## Next Steps

### Immediate
1. [ ] Read EXPLORATION_SUMMARY.md (15 minutes)
2. [ ] Skim CODEBASE_EXPLORATION_REPORT.md sections 1-4
3. [ ] Look at 2-3 component files from the references

### Short Term
1. [ ] Create design mockups for collections navigation
2. [ ] Define API schema for collection endpoints
3. [ ] Plan database migrations
4. [ ] Create implementation plan based on recommended architecture

### Medium Term
1. [ ] Implement Phase 1 (backend models + endpoints)
2. [ ] Implement Phase 2 (frontend components)
3. [ ] Integrate and test
4. [ ] Gather user feedback

---

## Document Maintenance

**These exploration documents should be:**
- ✓ Checked into version control
- ✓ Referenced in pull requests
- ✓ Updated when major architectural changes occur
- ✓ Shared with new team members
- ✗ Not treated as the absolute source of truth (code is)
- ✗ Not updated for every minor code change

**To update these documents:**
1. Make significant architectural changes
2. Re-run exploration with updated codebase
3. Commit updated documents with feature work
4. Note changes in commit message

---

## Questions? Issues?

If you find:
- **Inaccuracies**: The codebase may have changed; check actual files
- **Missing patterns**: Check `/skillmeat/web/CLAUDE.md` and `/skillmeat/api/CLAUDE.md`
- **Unclear explanations**: Read the actual code referenced
- **New features**: Add notes for next exploration run

---

**Last Explored**: December 12, 2025
**Explored By**: Claude Code (Haiku 4.5)
**Status**: Ready for implementation planning

Start with **EXPLORATION_SUMMARY.md** for a high-level overview, then dive into the detailed reference as needed.

