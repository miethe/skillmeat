---
title: "PRD: Enhanced Frontmatter Utilization for Marketplace Artifacts"
description: "Extract, cache, and leverage Claude Code frontmatter metadata for artifact discovery, enrichment, and intelligent linking within the marketplace"
audience: [ai-agents, developers, product]
tags: [prd, planning, marketplace, frontmatter, metadata, artifacts, linking]
created: 2026-01-21
updated: 2026-01-21
category: "product-planning"
status: draft
related: []
---

# PRD: Enhanced Frontmatter Utilization for Marketplace Artifacts

**Feature Name:** Enhanced Frontmatter Utilization for Marketplace Artifacts

**Filepath:** `enhanced-frontmatter-utilization-v1.md`

**Date:** 2026-01-21

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Complexity:** Large | **Estimated Effort:** 48 story points | **Timeline:** 4 weeks | **Priority:** High

---

## 1. Executive Summary

SkillMeat currently parses and displays Claude Code frontmatter metadata on the frontend, but this metadata is not utilized for enriching artifact data, caching, discovery, or intelligent linking. This feature enables systematic extraction, storage, and intelligent leveraging of frontmatter fields to enrich artifacts with agent configurations, tool dependencies, and automatic artifact linking within marketplace sources.

**Primary Outcomes:**

1. **Frontmatter Caching** — Extract and persist frontmatter metadata during artifact import, enabling instant display without re-parsing
2. **Metadata Auto-population** — Extract description, tools, and other relevant frontmatter fields to populate artifact.metadata and new artifact.tools field
3. **Tool Tracking** — Track tools and allowed-tools from frontmatter as a new artifact.tools field with Platform/Tool enums
4. **Artifact Linking** — Parse skill/tool references from frontmatter and auto-link to other artifacts in the same source
5. **UI Linking Workflows** — Provide UI for viewing, creating, and managing linked artifact relationships
6. **Raw Frontmatter Exclusion** — When frontmatter display is enabled, exclude the raw `---` block from content pane

**Impact:**

- Artifacts become self-documenting with extracted metadata visible in UX
- Tools and dependencies become discoverable without opening artifact content
- Linked artifacts enable artifact dependency visualization and smart deployment
- Reduces manual metadata entry during collection import
- Enables marketplace source features like "artifact compatibility" queries

---

## 2. Context & Background

### Current State

**Frontend Frontmatter Parsing (Implemented):**
- `skillmeat/web/lib/frontmatter.ts` — YAML parser with detectFrontmatter(), parseFrontmatter(), stripFrontmatter()
- `skillmeat/web/components/entity/frontmatter-display.tsx` — Collapsible YAML metadata display
- `skillmeat/web/components/entity/content-pane.tsx` — File viewer integrating frontmatter display
- Frontmatter displayed alongside content; raw `---` block still visible

**Frontend Artifact Types:**
- `skillmeat/web/types/artifact.ts` — ArtifactMetadata with title, description, license, author, version, tags
- Current gaps: No tools field, no linked_artifacts field

**Backend Artifact Types (Python):**
- `skillmeat/core/artifact.py` — ArtifactMetadata dataclass with: title, description, author, license, version, tags, dependencies, extra
- Current gaps: No tools field, no linked_artifacts field, no frontmatter caching

**Backend Artifact Detection:**
- `skillmeat/core/artifact_detection.py` — ArtifactType enum, detection via manifest files
- Currently extracts basic metadata but not frontmatter fields

**Claude Code Frontmatter Reference:**

Agent frontmatter fields:
- `name` — Unique identifier
- `description` — When Claude should delegate
- `tools` — Tools the agent can use (comma-separated or array)
- `disallowedTools` — Tools to deny
- `model` — sonnet, opus, haiku, or inherit
- `permissionMode` — default, acceptEdits, dontAsk, bypassPermissions, plan
- `skills` — Skills to preload
- `hooks` — Lifecycle hooks (PreToolUse, PostToolUse, Stop)

Skill/Command/Hook frontmatter fields:
- `name` — Display name
- `description` — What the skill does
- `argument-hint` — Autocomplete hint
- `disable-model-invocation` — Prevent automatic loading
- `user-invocable` — Hide from / menu
- `allowed-tools` — Tools without permission when active
- `model` — Model to use
- `context` — fork for isolated execution
- `agent` — Subagent type when context:fork
- `hooks` — Scoped lifecycle hooks

Available Claude Code tools:
- AskUserQuestion, Bash, TaskOutput, Edit, ExitPlanMode, Glob, Grep, KillShell, MCPSearch, NotebookEdit, Read, Skill, Task, TodoWrite, WebFetch, WebSearch, Write

### Problem Space

**Pain Points:**

1. **Lost Metadata During Import** — When importing artifacts, frontmatter description and configuration are visible on web UI but not stored in artifact.metadata; if artifact is later viewed without frontend, metadata is lost
2. **No Tool Discovery** — Tools required by agents/skills are only visible by reading frontmatter in content pane; cannot filter or discover by tool dependency
3. **No Artifact Linking** — When an agent lists required skills in frontmatter `skills:` field, there is no way to link to those other artifacts for dependency visualization or smart deployment
4. **Duplicate Content Display** — FrontmatterDisplay section exists but raw `---` block remains in ContentPane; creates redundant display of same information
5. **Inefficient Metadata Extraction** — Frontmatter must be re-parsed on every page load; not cached in database or API responses
6. **Manual Dependency Management** — Users cannot discover artifact dependencies without reading frontmatter content
7. **Platform Lock-in** — No standard way to track which tools/platforms an artifact targets (Claude Code vs future platforms)

### Architectural Context

**Artifact Import Flow (Current):**
```
GitHub Fetch → Copy to Collection → Create Artifact object → Save manifest
                                                      ↓
                                           (metadata extracted from some file,
                                            but frontmatter not captured)
```

**Desired Artifact Import Flow:**
```
GitHub Fetch → Parse Frontmatter → Copy to Collection → Create Artifact object
                                                        (with tools & links)
                                                        ↓
                                                    Save manifest + cache metadata
```

**Database Schema Context:**
- Artifact model (both backend and frontend) needs new fields:
  - `tools`: List of Tool enums
  - `linked_artifacts`: List of references to other artifacts (name, type, source)
  - `unlinked_references`: Unmatched artifact names parsed from frontmatter

**Frontend Components Involved:**
- ContentPane (will exclude raw frontmatter when FrontmatterDisplay is shown)
- ArtifactDetail/Edit pages (new LinkedArtifactsSection)
- Artifact search/filter (new Tools filter)

**Backend Services Involved:**
- ArtifactDetection (add frontmatter parsing)
- MetadataExtraction (enhanced for frontmatter fields)
- ArtifactManager (populate tools during import)

---

## 3. Problem Statement

**Core Gap:** Frontmatter metadata extracted during import is visible in the web UI but not persisted or leveraged for enrichment, caching, discovery, or linking, resulting in metadata loss, duplicate display, and inability to discover artifact dependencies.

**User Story Format:**

> "As a marketplace user importing a skill, when I view the artifact on the web, I see the frontmatter description, but when I export or view via API, that description is missing. I need frontmatter metadata to be extracted and persisted so artifacts are fully documented regardless of how they're accessed."

> "As a developer, when an agent in the marketplace lists required skills in its frontmatter `skills:` field, I cannot discover or navigate to those dependency artifacts. I need automatic artifact linking so I can understand the full dependency tree."

> "As a user browsing artifacts, when I'm looking for agents that use specific tools (like Bash or WebSearch), I have no way to filter by tool dependency. I need tool tracking so I can discover compatible artifacts."

> "As a content creator, when I look at an artifact detail page, I see both the FrontmatterDisplay component and the raw `---` metadata block in the content area, making the display cluttered and confusing. I need raw frontmatter excluded from content when formatted display is used."

**Technical Root Causes:**
- Frontmatter parsing only on frontend; no backend integration
- No persistence of extracted frontmatter fields beyond basic metadata
- No Platform or Tool enum types
- No linked_artifacts relationship model
- ContentPane displays raw frontmatter even when FrontmatterDisplay is active
- No import-time frontmatter extraction

**Files Involved:**
- Backend: `skillmeat/core/artifact.py`, `skillmeat/core/artifact_detection.py`, `skillmeat/api/schemas/artifact.py`
- Frontend: `skillmeat/web/types/artifact.ts`, `skillmeat/web/components/entity/content-pane.tsx`, `skillmeat/web/lib/frontmatter.ts`
- Database: Artifact model migration needed for tools/linked_artifacts fields

---

## 4. Goals & Success Metrics

### Primary Goals

**Goal 1: Extract and Cache Frontmatter Metadata**
- During artifact import from marketplace sources, parse frontmatter and extract relevant fields
- Cache extracted metadata in artifact.metadata for persistence
- Enable description auto-population from frontmatter.description
- Success: Description automatically populated for 95%+ of imported artifacts with frontmatter

**Goal 2: Track Tools and Platform Dependencies**
- Create Platform enum (CLAUDE_CODE, CURSOR, etc.)
- Create Tool enum with all Claude Code tools
- Parse tools/allowed-tools from frontmatter
- Populate artifact.tools during import
- Success: Tools field populated for 80%+ of agents/skills/commands with frontmatter tools field

**Goal 3: Implement Artifact Linking**
- Parse skill/tool references from frontmatter (skills:, tools:, context: fields)
- Auto-link to other artifacts in same Source that match references
- Store unmatched references for manual linking
- Success: Auto-link 70%+ of referenced artifacts without user intervention

**Goal 4: Provide Linking UI and Workflows**
- New LinkedArtifactsSection in artifact detail/edit views
- Dialog to search and link Collection artifacts to unlinked references
- Show linked artifacts with click-to-navigate
- Success: Users can add 5+ linked artifacts in <30 seconds

**Goal 5: Improve ContentPane UX**
- Exclude raw frontmatter block from ContentPane body when FrontmatterDisplay is active
- Use stripFrontmatter() to remove metadata before display
- Success: No duplicate frontmatter display; clean content pane

### Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Description auto-population rate | 95% | Frontmatter should cover most artifacts |
| Tools field population rate | 80% | Not all artifact types have tools field |
| Auto-linked artifacts rate | 70% | Some references may be renamed or external |
| User satisfaction with linking UI | 8/10 | Quick, intuitive workflow |
| Frontmatter cache hit rate | 99% | Cache should eliminate re-parsing |
| Reduced ContentPane render time | 20% | Eliminating frontmatter parsing from render |
| Time to link 5 artifacts | <30s | Workflow should be fast and discoverable |

---

## 5. Detailed Requirements

### Functional Requirements

#### FR-1: Platform and Tool Enums

**Requirement:** Create Platform and Tool enums to standardize artifact capability tracking.

| Aspect | Specification |
|--------|---------------|
| **Backend Implementation** | Create `skillmeat/core/enums.py` with: Platform enum (CLAUDE_CODE, CURSOR, OTHER), Tool enum with all Claude Code tools |
| **Frontend Implementation** | Create `skillmeat/web/types/enums.ts` mirroring backend enums |
| **API Schema** | Update `skillmeat/api/schemas/artifact.py` to include tools field as List[Tool] |
| **Validation** | Tool enum values must exactly match Claude Code tool names |

**Implementation Detail:**
```
Platform: CLAUDE_CODE, CURSOR, OTHER
Tool: AskUserQuestion, Bash, TaskOutput, Edit, ExitPlanMode, Glob, Grep,
      KillShell, MCPSearch, NotebookEdit, Read, Skill, Task, TodoWrite,
      WebFetch, WebSearch, Write
```

#### FR-2: Frontmatter Extraction During Import

**Requirement:** Extract and persist frontmatter metadata when importing artifacts from marketplace sources.

| Aspect | Specification |
|--------|---------------|
| **Trigger** | During `ArtifactManager.add_from_github()` and `add_from_local()` |
| **Parser** | Extend `skillmeat/utils/metadata.py` with `extract_frontmatter()` function |
| **Fields Extracted** | name, description, tools, allowed-tools, model, skills, hooks |
| **Mapping** | description → artifact.metadata.description, tools → artifact.tools, tools → artifact.metadata.extra['frontmatter_tools'] |
| **Fallback** | If frontmatter description exists, prefer it over other metadata sources |
| **Error Handling** | If frontmatter parse fails, continue with existing metadata (non-blocking) |

**Acceptance Criteria:**
- Frontmatter is extracted during import without blocking other operations
- description field from frontmatter is persisted in artifact.metadata.description
- tools field from frontmatter is persisted in artifact.tools
- Artifact manifest reflects persisted metadata

#### FR-3: Artifact.tools Field

**Requirement:** Add tools field to Artifact model and API schema.

| Aspect | Specification |
|--------|---------------|
| **Backend Model** | Add `tools: List[Tool] = field(default_factory=list)` to `ArtifactMetadata` dataclass |
| **Frontend Model** | Add `tools?: Tool[]` to ArtifactMetadata interface |
| **API Schema** | Add `tools: list[str]` to ArtifactSchema (serialized as string names) |
| **Database Migration** | Add tools JSON field to artifacts table (nullable, defaults to empty list) |
| **API Endpoints** | Expose tools in GET /artifacts, GET /artifacts/{id} responses |
| **Filtering** | Support optional `tools` query parameter in artifact list endpoints |

**Acceptance Criteria:**
- tools field visible in artifact detail view
- tools field populated during import from frontmatter
- tools field can be manually edited in artifact editor
- tools filter available in search/filter UI

#### FR-4: Artifact Linking System

**Requirement:** Parse frontmatter references and auto-link to other artifacts; support manual linking.

| Aspect | Specification |
|--------|---------------|
| **Fields Parsed** | skills (agent frontmatter), tools (any frontmatter), context + agent (skill frontmatter) |
| **Reference Format** | artifact_name or artifact_name/artifact_type or fully qualified source reference |
| **Matching Algorithm** | Case-insensitive name match within same Source; handle plurals (skill→skills) |
| **Auto-linking** | During import, match references to artifacts in same Source |
| **Unmatched References** | Store as artifact.unlinked_references with original text for manual linking |
| **Linked Artifacts Model** | Add `linked_artifacts: List[LinkedArtifactReference]` to Artifact |
| **LinkedArtifactReference** | { artifact_id, artifact_name, artifact_type, source_name, link_type: 'requires'|'enables'|'related' } |
| **Directionality** | Linking is directional (A requires B); queries support forward and reverse lookup |

**Acceptance Criteria:**
- Parse skills field from agent frontmatter
- Parse tools field from any frontmatter
- Auto-link 70%+ of references to matching artifacts in same source
- Store unmatched references with original text
- Linked artifacts persist in database and visible in API

#### FR-5: Frontmatter Caching in Artifact Metadata

**Requirement:** Cache full parsed frontmatter in artifact.metadata.extra['frontmatter'] for fast retrieval.

| Aspect | Specification |
|--------|---------------|
| **Cache Location** | artifact.metadata.extra['frontmatter'] = parsed frontmatter dict |
| **Trigger** | Populated during import or when viewing artifact without parsed frontmatter |
| **Lazy Loading** | If cache miss, parse frontmatter on-demand and update artifact |
| **TTL** | No explicit TTL; cache valid as long as artifact file unchanged |
| **Invalidation** | Frontmatter cache invalidated when artifact is updated |
| **Performance** | Frontmatter cached in API response (reducing frontend parsing overhead) |

**Acceptance Criteria:**
- Frontmatter cache populated during import
- API responses include cached frontmatter in artifact.metadata.extra
- Frontend uses cached frontmatter when available (optional optimization)
- No performance regression from caching mechanism

#### FR-6: ContentPane Raw Frontmatter Exclusion

**Requirement:** When FrontmatterDisplay is active, exclude raw frontmatter block from ContentPane body.

| Aspect | Specification |
|--------|---------------|
| **Component** | `skillmeat/web/components/entity/content-pane.tsx` |
| **Logic** | When frontmatter is detected AND FrontmatterDisplay is rendered, apply stripFrontmatter() before displaying content |
| **Implementation** | Check if frontmatter exists; if yes, pass stripped content to markdown renderer |
| **Behavior** | Raw `---\n...\n---\n` block removed from content; formatted FrontmatterDisplay used instead |
| **User Experience** | Single source of truth for frontmatter metadata; cleaner content display |

**Acceptance Criteria:**
- Raw frontmatter block no longer visible in content pane when FrontmatterDisplay is shown
- FrontmatterDisplay properly displays all frontmatter fields
- Content pane shows only artifact body, no metadata
- Works with all artifact types (skill, command, agent, hook, mcp)

#### FR-7: LinkedArtifactsSection Component

**Requirement:** New UI section for viewing and managing linked artifacts in artifact detail/edit views.

| Aspect | Specification |
|--------|---------------|
| **Component** | New `skillmeat/web/components/entity/linked-artifacts-section.tsx` |
| **Display** | Shows linked artifacts as a grid or list with artifact type, name, link type |
| **Interactions** | Click to navigate to linked artifact; delete link; add new link via dialog |
| **Link Types** | Visual indicators for requires/enables/related relationships |
| **Unlinked References** | Section for unmatched references with "Link" button to open dialog |
| **Responsive** | Grid layout; collapses on mobile |
| **Empty State** | "No linked artifacts" message with link to add new ones |

**Acceptance Criteria:**
- Display linked artifacts from artifact.linked_artifacts field
- Show unlinked references with actionable "Link" button
- Dialog allows search and selection of Collection artifacts
- Links persist after creation
- UX is clear and discoverable

#### FR-8: Artifact Linking Dialog

**Requirement:** Dialog UI for manually linking unlinked artifact references to existing Collection artifacts.

| Aspect | Specification |
|--------|---------------|
| **Component** | New `skillmeat/web/components/entity/artifact-linking-dialog.tsx` |
| **Trigger** | From LinkedArtifactsSection "Link" button or "Add Link" button |
| **Search** | Searchable dropdown of Collection artifacts with type filters |
| **Filtering** | By artifact type, by collection, by tag |
| **Display** | Show artifact name, type, version, source for clarity |
| **Selection** | Single select; confirm to create link |
| **Link Type** | Dropdown to select link type (requires/enables/related) |
| **Create** | POST /artifacts/{id}/linked-artifacts with target artifact |
| **Error Handling** | Show user-friendly error if link creation fails |
| **Accessibility** | Keyboard navigable, screen reader friendly |

**Acceptance Criteria:**
- Dialog opens and closes correctly
- Search/filter works for finding artifacts
- Can select artifact and create link
- Link appears immediately in LinkedArtifactsSection
- Error handling for invalid selections

### Non-Functional Requirements

| Requirement | Specification |
|-----------|---------------|
| **Performance** | Frontmatter caching eliminates re-parsing on every load; <10ms overhead for cache lookup |
| **Scalability** | Artifact linking supports 1000+ links per artifact without degradation |
| **Backward Compatibility** | Artifacts without frontmatter continue to work; optional fields |
| **Data Integrity** | Linked artifacts validated against actual artifacts; orphaned links cleaned up |
| **Error Handling** | Frontmatter parse failures are logged but non-blocking |
| **Testing** | 80%+ code coverage for frontmatter extraction and linking |
| **Documentation** | API docs updated; frontend component stories created |
| **Accessibility** | ARIA labels on new UI components; keyboard navigation supported |

---

## 6. Scope

### In-Scope

1. Backend frontmatter extraction and caching during artifact import
2. Platform and Tool enum definitions and validation
3. artifact.tools field implementation (backend and frontend)
4. artifact.linked_artifacts field and LinkedArtifactReference model
5. Artifact linking logic (auto-link + manual linking)
6. LinkedArtifactsSection and ArtifactLinkingDialog components
7. ContentPane exclusion of raw frontmatter
8. API endpoints for artifact linking (GET linked artifacts, POST new link, DELETE link)
9. Database migration for new fields
10. Unit tests for frontmatter extraction and linking logic
11. Integration tests for import workflow
12. Component tests for UI linking workflows

### Out-of-Scope

1. **Bulk linking UI** — Managing links for 100+ artifacts at once (Phase 2)
2. **Link visualization** — Graphical dependency tree (Future phase)
3. **Bi-directional sync** — Syncing linked artifacts from upstream (Future)
4. **Version pinning** — Pinning to specific versions of linked artifacts (Future)
5. **Tool permission enforcement** — Runtime enforcement of tool restrictions (Future)
6. **Transitive dependencies** — Following chains of dependencies (Future)
7. **Marketplace package bundles** — Creating multi-artifact packages (Future)

---

## 7. Dependencies & Assumptions

### Internal Dependencies

| Component | Dependency | Impact |
|-----------|-----------|--------|
| ArtifactManager | Frontmatter parsing library | Must exist or be added |
| API schemas | Tool/Platform enums | Enums must be defined before schemas |
| Frontend types | API schema definitions | Types auto-generated from OpenAPI spec |
| Database | Migration system | Alembic migrations required |
| API routes | Database models | Models must support new fields |

### External Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python YAML parser | stdlib tomli (TOML) or PyYAML (YAML) | Parse frontmatter |
| TypeScript | 5.x | Frontend type safety |
| Next.js | 15.x | Frontend framework |
| TanStack Query | Latest | Frontend data fetching |

### Assumptions

| Assumption | Rationale | Risk |
|-----------|-----------|------|
| Frontmatter structure is consistent across artifact types | Based on Claude Code reference | Different upstream sources may use different formats; mitigation: lenient parsing |
| Auto-linking will match 70%+ of references | Most artifact authors use canonical names | Some projects rename skills; mitigation: unlinked_references + manual linking UI |
| Users will engage with linked artifacts feature | Assuming discovery is valuable | Low engagement possible; mitigation: prominent UX placement |
| Artifact descriptions in frontmatter are user-friendly | Standard practice for skill authors | Some descriptions may be technical jargon; no mitigation needed (informational) |
| Tools enum covers all current and near-future Claude Code tools | As of Jan 2026 | New tools may be added; mitigation: update enum and API schema |

---

## 8. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Frontmatter parse failures cause import errors | Import workflow broken for some artifacts | Medium | Non-blocking error handling; log and continue with basic metadata |
| Large number of linked artifacts slows API response | Slow artifact detail load | Low | Pagination for linked artifacts; lazy load in frontend |
| Users create invalid links (e.g., circular dependencies) | Confusing UX, incorrect recommendations | Medium | Validation in dialog; prevent self-links; documentation of link semantics |
| Frontmatter inconsistency across sources | Auto-linking fails; manual linking required | High | Case-insensitive matching; fuzzy matching with threshold; unlinked_references fallback |
| Database migration fails on large datasets | Deployment blocked | Low | Test migration on replica; rollback plan; monitoring during rollout |
| Tool enum becomes outdated | New tools not tracked | Medium | Version enum; add migration path for custom tools in extra['unknown_tools'] |
| Users don't use linking feature | Low ROI | Medium | Prominent placement in artifact detail; educate via docs/help; measure engagement |

---

## 9. Acceptance Criteria

### Phase 0: Backend Foundations (Weeks 1-2)

| Criterion | Definition | Success |
|-----------|-----------|---------|
| Platform & Tool enums defined | `skillmeat/core/enums.py` created with complete Platform and Tool enums | 14 tools defined; 2 platforms; matches Claude Code reference |
| Frontmatter extraction implemented | `skillmeat/utils/metadata.py` enhanced with `extract_frontmatter()` function | Extracts description, tools, allowed-tools from YAML frontmatter |
| artifact.tools field added (Python) | ArtifactMetadata.tools field added and persists to manifest | Tests passing; field visible in artifact.to_dict() output |
| Artifact import updated | ArtifactManager.add_from_github() and add_from_local() call extract_frontmatter() | Frontmatter fields extracted during import; metadata persisted |
| Database migration created | Alembic migration for artifacts table (add tools JSON field) | Migration runs without error; rollback works |
| API schema updated | artifact.py schema includes tools field | OpenAPI spec reflects tools field; tests passing |

### Phase 1: Frontend & Artifact Linking (Weeks 2-3)

| Criterion | Definition | Success |
|-----------|-----------|---------|
| Frontend enums created | `skillmeat/web/types/enums.ts` mirrors backend | Tool and Platform types exported from enums.ts |
| artifact.tools field (Frontend) | ArtifactMetadata interface includes tools field | Types update; artifact detail shows tools |
| LinkedArtifactReference model | Backend and frontend models for linked artifacts | Models include artifact_id, name, type, link_type |
| artifact.linked_artifacts field | Backend and frontend models support linked_artifacts array | Field persists; API endpoint returns linked artifacts |
| Artifact linking logic | Backend logic to auto-link referenced artifacts | 70% of references auto-linked; unlinked_references stored |
| Artifact linking API | POST /artifacts/{id}/linked-artifacts, DELETE, GET | CRUD operations working; validated against actual artifacts |
| ContentPane raw frontmatter exclusion | stripFrontmatter() applied when FrontmatterDisplay is active | No raw frontmatter visible; FrontmatterDisplay shows formatted data |

### Phase 2: UI Workflows (Weeks 3-4)

| Criterion | Definition | Success |
|-----------|-----------|---------|
| LinkedArtifactsSection component | Displays linked artifacts and unlinked references | Shows 5+ linked artifacts without performance regression |
| ArtifactLinkingDialog component | Dialog to search and link artifacts | Can select and link artifact; closes on success |
| Manual artifact linking workflow | User can click "Link" button and create link | Link created and visible immediately |
| Tools filter in artifact search | Ability to filter by tool dependency | Can select multiple tools; results filtered correctly |
| Integration tests for linking | Test auto-linking during import; test manual linking workflows | All workflows tested; 80% code coverage |
| User documentation | Updated docs explaining linked artifacts feature | Docs include how to view, create, and navigate links |

### Phase 3: Polish & Validation (Week 4)

| Criterion | Definition | Success |
|-----------|-----------|---------|
| Performance testing | Verify no regression from caching/linking changes | Load times within baseline; cache hit rate 99%+ |
| Error handling validation | Test error cases (invalid links, parse failures, etc.) | Users see helpful error messages; no silent failures |
| Accessibility audit | Verify keyboard navigation and screen reader support | All new components WCAG 2.1 AA compliant |
| Data integrity checks | Verify orphaned links cleaned up; invalid artifacts handled | No broken links; cleanup runs on import/delete |
| Regression testing | Verify existing artifact import/view workflows unchanged | All existing tests passing |
| Final integration test | End-to-end test: import artifact with frontmatter → view linked artifacts → manual link | Full workflow successful without errors |

---

## 10. Phased Implementation

### Phase 0: Backend Foundations
**Duration:** 2 weeks | **Effort:** 18 story points

**Deliverables:**
- Platform & Tool enums with complete Claude Code tool list
- Frontmatter extraction function in metadata utility
- artifact.tools field (Python model + API schema)
- Database migration for tools field
- ArtifactManager updated to extract frontmatter during import
- Backend unit tests for frontmatter extraction (80%+ coverage)
- Basic linking data model (artifact.linked_artifacts field definition only)

**Execution Stories:**
1. Define Platform & Tool enums in `skillmeat/core/enums.py` (3 points)
2. Implement frontmatter extraction in `skillmeat/utils/metadata.py` (5 points)
3. Add artifact.tools field to ArtifactMetadata; update manifest serialization (3 points)
4. Create Alembic migration for tools field; test migration (3 points)
5. Update API schema; regenerate OpenAPI client (2 points)
6. Update ArtifactManager to extract frontmatter during import (2 points)

### Phase 1: Frontend & Artifact Linking
**Duration:** 2 weeks | **Effort:** 18 story points

**Deliverables:**
- Frontend enums mirroring backend
- artifact.tools field on frontend; artifact detail displays tools
- LinkedArtifactReference model (backend + frontend)
- artifact.linked_artifacts field persists and API returns it
- Artifact linking logic (auto-link + unlinked_references)
- Artifact linking API endpoints (CRUD)
- ContentPane exclusion of raw frontmatter
- Integration tests for linking workflows
- Frontend component stubs for linked artifacts UI

**Execution Stories:**
1. Create frontend enums; update API types (3 points)
2. Add artifact.tools to frontend ArtifactMetadata; update artifact detail (2 points)
3. Define LinkedArtifactReference model; update Artifact models (2 points)
4. Implement artifact linking logic in ArtifactManager (5 points)
5. Create API endpoints for artifact linking (POST/DELETE/GET) (3 points)
6. Update ContentPane to exclude raw frontmatter (2 points)
7. Integration tests for import + linking workflows (2 points)
8. Frontend component stubs for linked artifacts (Placeholder only) (1 point)

### Phase 2: UI Workflows
**Duration:** 1.5 weeks | **Effort:** 12 story points

**Deliverables:**
- LinkedArtifactsSection component (displays links + unlinked refs)
- ArtifactLinkingDialog component (search & link UI)
- Manual artifact linking workflow fully functional
- Tools filter integrated into search UI
- Component tests for new UI components (80%+ coverage)
- User-facing documentation
- Accessibility audit complete

**Execution Stories:**
1. Implement LinkedArtifactsSection component (4 points)
2. Implement ArtifactLinkingDialog component (4 points)
3. Integrate tools filter into artifact search UI (2 points)
4. Component tests for linking UI (2 points)
5. Documentation for linked artifacts feature (1 point)
6. Accessibility audit & fixes (1 point)

### Phase 3: Polish & Validation
**Duration:** 1 week | **Effort:** 4 story points

**Deliverables:**
- Performance benchmarks (cache hit rate, load times)
- Error handling validation complete
- Data integrity checks (orphaned link cleanup)
- Regression testing complete
- End-to-end test passing
- Deployment-ready feature flag (if needed)

**Execution Stories:**
1. Performance testing & optimization (2 points)
2. Error handling & edge case validation (1 point)
3. Regression testing & final QA (1 point)

---

## 11. Technical Architecture

### Backend Data Model

**New Enums:**
```python
# skillmeat/core/enums.py
class Platform(str, Enum):
    CLAUDE_CODE = "claude_code"
    CURSOR = "cursor"
    OTHER = "other"

class Tool(str, Enum):
    ASK_USER_QUESTION = "AskUserQuestion"
    BASH = "Bash"
    TASK_OUTPUT = "TaskOutput"
    EDIT = "Edit"
    EXIT_PLAN_MODE = "ExitPlanMode"
    GLOB = "Glob"
    GREP = "Grep"
    KILL_SHELL = "KillShell"
    MCP_SEARCH = "MCPSearch"
    NOTEBOOK_EDIT = "NotebookEdit"
    READ = "Read"
    SKILL = "Skill"
    TASK = "Task"
    TODO_WRITE = "TodoWrite"
    WEB_FETCH = "WebFetch"
    WEB_SEARCH = "WebSearch"
    WRITE = "Write"
```

**Updated ArtifactMetadata:**
```python
@dataclass
class ArtifactMetadata:
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)  # NEW
    extra: Dict[str, Any] = field(default_factory=dict)  # Includes cached frontmatter
```

**New LinkedArtifactReference:**
```python
@dataclass
class LinkedArtifactReference:
    artifact_id: str  # or None if external/unlinked
    artifact_name: str
    artifact_type: ArtifactType
    source_name: Optional[str] = None
    link_type: str = "requires"  # requires, enables, related
    created_at: datetime = field(default_factory=datetime.utcnow)
```

**Updated Artifact:**
```python
@dataclass
class Artifact:
    # ... existing fields ...
    tools: List[Tool] = field(default_factory=list)
    linked_artifacts: List[LinkedArtifactReference] = field(default_factory=list)
    unlinked_references: List[str] = field(default_factory=list)
```

### Frontend Type Changes

**enums.ts:**
```typescript
export enum Platform {
  CLAUDE_CODE = 'claude_code',
  CURSOR = 'cursor',
  OTHER = 'other',
}

export enum Tool {
  ASK_USER_QUESTION = 'AskUserQuestion',
  BASH = 'Bash',
  // ... 16 more tools
}
```

**artifact.ts:**
```typescript
export interface ArtifactMetadata {
  title?: string;
  description?: string;
  license?: string;
  author?: string;
  version?: string;
  tags?: string[];
  tools?: Tool[];  // NEW
}

export interface LinkedArtifactReference {
  artifact_id?: string;
  artifact_name: string;
  artifact_type: ArtifactType;
  source_name?: string;
  link_type: 'requires' | 'enables' | 'related';
  created_at?: string;
}

export interface Artifact {
  // ... existing fields ...
  tools?: Tool[];
  linked_artifacts?: LinkedArtifactReference[];
  unlinked_references?: string[];
}
```

### API Contracts

**GET /artifacts/{id}**
Response includes:
```json
{
  "id": "...",
  "name": "my-agent",
  "type": "agent",
  "metadata": {
    "description": "...",
    "tools": ["Bash", "WebSearch"],
    "extra": {
      "frontmatter": { /* full parsed frontmatter */ }
    }
  },
  "tools": ["Bash", "WebSearch"],
  "linked_artifacts": [
    {
      "artifact_id": "xyz",
      "artifact_name": "python-skill",
      "artifact_type": "skill",
      "link_type": "requires"
    }
  ],
  "unlinked_references": ["unknown-skill"]
}
```

**POST /artifacts/{id}/linked-artifacts**
Request:
```json
{
  "target_artifact_id": "xyz",
  "link_type": "requires"
}
```

**DELETE /artifacts/{id}/linked-artifacts/{target_artifact_id}**
Removes link between artifacts.

**GET /artifacts?tools=Bash,WebSearch**
Optional filter by tools (comma-separated or array format).

---

## 12. Testing Strategy

### Unit Tests

**Frontmatter Extraction:**
- Parse complete frontmatter with all fields
- Parse partial frontmatter (missing optional fields)
- Handle YAML parsing errors gracefully
- Extract nested structures (tools as array, as comma-separated string)
- Map frontmatter fields to ArtifactMetadata correctly

**Artifact Linking:**
- Auto-link exact name matches
- Auto-link case-insensitive name matches
- Handle artifact type mismatches gracefully
- Store unmatched references
- Support multiple link types (requires, enables, related)

**Tool Enum:**
- All Claude Code tools are present
- Enum serialization/deserialization works
- Invalid tools are rejected
- Case sensitivity handled correctly

### Integration Tests

**Import Workflow:**
- Import artifact with frontmatter → metadata persisted
- Import artifact without frontmatter → falls back gracefully
- Import agent with skill references → auto-linked if match found
- Import skill with tool references → tools populated from frontmatter

**Artifact Linking:**
- Create manual link → reflected in artifact.linked_artifacts
- Delete link → removed from artifact.linked_artifacts
- Invalid artifact ID → error returned
- Query linked artifacts → returns full artifact data

**ContentPane:**
- Raw frontmatter excluded when FrontmatterDisplay active
- Raw frontmatter shown when FrontmatterDisplay not active (for plain text view)
- Stripped content accurate (no missing body content)

### Component Tests

**LinkedArtifactsSection:**
- Renders linked artifacts grid
- Renders unlinked references list
- Delete link button works
- "Link" button opens dialog
- Empty state when no linked artifacts

**ArtifactLinkingDialog:**
- Search works
- Filter by type works
- Select artifact works
- Create link works
- Error handling shows user message
- Closes on success

### E2E Tests

**End-to-End Workflow:**
- User imports artifact with frontmatter
- Artifact detail shows populated tools
- Artifact detail shows linked artifacts
- User clicks "Link" on unlinked reference
- Dialog opens and user selects artifact
- Link created and visible in LinkedArtifactsSection
- User navigates to linked artifact
- Both artifacts show relationship

---

## 13. Success Criteria Summary

| Category | Success Criterion |
|----------|-------------------|
| **Functionality** | All five feature pillars working end-to-end; frontmatter extracted and cached; artifacts linked automatically and manually |
| **Performance** | Frontmatter cache hit rate 99%; no load time regression; ContentPane render time reduced 20% |
| **Quality** | 80%+ code coverage; all acceptance criteria met; zero data integrity issues |
| **UX** | Linking workflow completes in <30 seconds; no duplicate frontmatter display; discoverable and intuitive |
| **Documentation** | API docs updated; user-facing docs complete; component stories created |
| **Accessibility** | All new components WCAG 2.1 AA compliant; keyboard navigation supported |

---

## 14. Open Questions & Future Considerations

### Open Questions

1. **Transitive Dependencies** — Should we follow chains of dependencies (if A requires B and B requires C, should we auto-include C)? Deferred to Phase 2.
2. **Link Visualization** — How should we visualize the dependency graph on the web? Graph visualization library selection needed.
3. **Bulk Linking** — How should users link 100+ artifacts at once? Batch import workflow needs design.
4. **Tool Permissions** — Should SkillMeat enforce tool restrictions at runtime (e.g., prevent execution if disallowedTools present)? Deferred to runtime enforcement phase.

### Future Enhancements

1. **Link Recommendations** — ML-based suggestions for linking artifacts based on similarity or usage patterns
2. **Version-Pinned Linking** — Link to specific versions of artifacts (e.g., "requires python-skill@1.2.0")
3. **Breaking Change Detection** — Warn users when updating linked artifacts with breaking changes
4. **Artifact Bundles** — Create "recipes" of linked artifacts that deploy together
5. **Marketplace Integration** — Surface linked artifacts prominently in marketplace search results
6. **Custom Tool Enum** — Support user-defined tools for non-Claude-Code platforms
7. **Bi-directional Sync** — Sync improvements from projects back to collection/upstream

---

## 15. Appendix: Claude Code Frontmatter Reference

### Agent Frontmatter Fields

| Field | Type | Required | Example |
|-------|------|----------|---------|
| name | string | Yes | "my-agent" |
| description | string | Yes | "Analyzes Python code quality" |
| tools | string \| array | No | "Bash,Grep,Read" or ["Bash", "Grep"] |
| disallowedTools | string \| array | No | "TaskOutput,KillShell" |
| model | string | No | "opus" |
| permissionMode | string | No | "default" |
| skills | array | No | ["python-analyzer", "lint-skill"] |
| hooks | object | No | { PreToolUse: "...", Stop: "..." } |

### Skill/Command Frontmatter Fields

| Field | Type | Required | Example |
|-------|------|----------|---------|
| name | string | No | "my-skill" |
| description | string | No | "Python linting utilities" |
| allowed-tools | string \| array | No | "Bash,Read,Write" |
| argument-hint | string | No | "file path" |
| user-invocable | boolean | No | true |
| disable-model-invocation | boolean | No | false |
| model | string | No | "sonnet" |
| context | string | No | "fork" |
| agent | string | No | "my-agent" |
| hooks | object | No | {} |

---

**Document Revision History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-21 | Claude Code | Initial PRD creation |

