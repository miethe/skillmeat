# Content Viewer Extraction Analysis

Complete inventory and extraction strategy for content viewing/file browsing components in SkillMeat web app.

## Documents in This Analysis

### 1. `content-viewing-extraction-inventory.md` (28 KB)
**Comprehensive technical analysis**

- Detailed breakdown of all 12 files involved in content viewing
- Organized by category (Utilities, Hooks, Components, Types, API)
- For each file:
  - Exports and signatures
  - External and internal dependencies
  - Domain coupling assessment
  - Use cases and extraction readiness
  - Performance notes where relevant
- Extraction readiness matrix (✅ High / 🟡 Medium / 🔴 Low)
- Recommended 3-tier extraction strategy
- Full dependency and compatibility matrix
- Integration patterns and testing considerations
- Known limitations and gotchas

**Read this for**: Deep technical understanding, dependency analysis, full context

### 2. `content-viewer-quick-ref.md` (9.8 KB)
**Quick reference and action guide**

- What to extract (components, utilities, hooks, types)
- What to keep in SkillMeat (domain-specific code)
- Package structure proposal
- Dependencies (runtime, peer, dev)
- Import examples before/after extraction
- Migration checklist
- Feature checklist
- Testing coverage needed
- Performance notes
- Versioning strategy

**Read this for**: Quick lookup, planning, package structure, checklists

---

## Key Findings

### Ready for Extraction (Tier 1) ✅

**100% Generic, Zero Domain Coupling**:

1. **Components** (2)
   - `FileTree` - Recursive file browser with keyboard nav and ARIA
   - `FrontmatterDisplay` - Collapsible YAML metadata viewer

2. **Utilities** (5)
   - `parseFrontmatter()` - YAML parsing
   - `stripFrontmatter()` - Remove frontmatter
   - `detectFrontmatter()` - Check presence
   - `extractFirstParagraph()` - Markdown summary
   - `extractFolderReadme()` - Find and extract README

3. **Hooks** (2)
   - `useCatalogFileTree()` - Fetch file tree via TanStack Query
   - `useCatalogFileContent()` - Fetch file content via TanStack Query

4. **Types** (Generic variants)
   - `FileNode` - Generic tree node structure
   - `FileTreeResponse` - API response type
   - `FileContentResponse` - API response type

5. **API Clients**
   - `fetchCatalogFileTree()` - HTTP file tree fetching
   - `fetchCatalogFileContent()` - HTTP file content fetching

### Keep in SkillMeat (Domain-Specific)

**Medium Coupling**:
- `buildFolderTree()` - Tree builder (could adapt but uses CatalogEntry)
- `files.ts` types - Mix of generic + SkillMeat wrappers
- Detection patterns configuration

**High Coupling**:
- `filterSemanticTree()` - Artifact container filtering
- `applyFiltersToEntries()` - Catalog filtering with SkillMeat enums
- `CatalogEntry` and marketplace types
- `useDetectionPatterns()` hook

---

## Extraction Impact

### Size Reduction
- **Extracted**: ~2,500 lines of code
- **Remaining**: ~1,000+ lines in SkillMeat (domain-specific)
- **Result**: Cleaner separation of concerns

### Dependency Footprint
```
@skillmeat/content-viewer would depend on:
- react ^18.0
- @tanstack/react-query ^5.0
- lucide-react
- tailwindcss
- radix-ui primitives (via shadcn)
- tailwind-merge (for cn() utility)

NOT dependent on:
- SkillMeat types (CatalogEntry, ArtifactType)
- Marketplace logic
- Collection management
- Deployment workflows
```

### Token Efficiency
- **Frontmatter parser**: No external dependencies - embed or make optional `js-yaml`
- **Tree builder**: Generic algorithm, small footprint
- **Components**: Tailwind-based, no runtime CSS-in-JS
- **Hooks**: Standard TanStack Query pattern

---

## Use Cases Beyond SkillMeat

1. **Generic content viewers** - Any markdown/code documentation browser
2. **Code editor file panels** - VS Code-like file tree widget
3. **Documentation sites** - File browsing for public docs
4. **Artifact libraries** - File trees for any artifact system
5. **CMS interfaces** - Content management with file browsing

---

## Implementation Timeline

### Phase 1: Package Setup (1-2 hours)
- Create repo structure
- Set up tsconfig, package.json
- Configure build system (tsup/vite)
- Add GitHub workflows

### Phase 2: Component Extraction (4-6 hours)
- Copy FileTree component
- Copy FrontmatterDisplay component
- Adjust imports for standalone
- Add comprehensive prop documentation

### Phase 3: Utilities & Hooks (3-4 hours)
- Extract utility functions
- Extract hooks with TanStack Query
- Extract API client functions
- Create type definitions

### Phase 4: Documentation (2-3 hours)
- README with examples
- API documentation
- Migration guide
- Contributing guidelines

### Phase 5: Testing (4-6 hours)
- Unit tests for all utilities
- Component integration tests
- Hook tests with mock API
- E2E tests for examples

### Phase 6: Release (1-2 hours)
- Version bump (1.0.0)
- CHANGELOG
- Publish to npm
- Announce

**Total**: 15-23 hours (2-3 days)

---

## File-by-File Breakdown

### Tier 1 (Extract) ✅

| File | Type | Lines | Status |
|------|------|-------|--------|
| `lib/frontmatter.ts` | Utility | 398 | ✅ Ready |
| `lib/folder-readme-utils.ts` | Utility | 188 | ✅ Ready |
| `lib/api/catalog.ts` | API Client | 142 | ✅ Ready |
| `hooks/use-catalog-files.ts` | Hook | 133 | ✅ Ready |
| `components/entity/file-tree.tsx` | Component | 562 | ✅ Ready |
| `components/entity/frontmatter-display.tsx` | Component | 160 | ✅ Ready |

**Total for Extraction**: ~1,583 lines

### Tier 2 (Adapt/Keep) 🟡

| File | Type | Lines | Notes |
|------|------|-------|-------|
| `lib/tree-builder.ts` | Utility | 189 | Could extract with generics |
| `types/files.ts` | Types | 37 | Split generic + wrappers |

### Tier 3 (Keep) 🔴

| File | Type | Lines | Reason |
|------|------|-------|--------|
| `lib/tree-filter-utils.ts` | Utility | 261 | Detection patterns + leaf containers |
| `lib/folder-filter-utils.ts` | Utility | 333 | CatalogEntry + enums |
| `types/marketplace.ts` | Types | 100+ | Marketplace-specific |
| `hooks/use-detection-patterns.ts` | Hook | 200+ | SkillMeat configuration |

---

## Dependency Changes Post-Extraction

### SkillMeat package.json After

```json
{
  "dependencies": {
    "@skillmeat/content-viewer": "^1.0.0"  // NEW
    // ... other deps
  }
}
```

### SkillMeat imports After

```tsx
// Components now from package
import { FileTree, FrontmatterDisplay } from '@skillmeat/content-viewer';
import { parseFrontmatter } from '@skillmeat/content-viewer';

// Domain-specific utilities stay local
import { filterSemanticTree } from '@/lib/tree-filter-utils';
import { applyFiltersToEntries } from '@/lib/folder-filter-utils';

// Types from both
import type { FileNode } from '@skillmeat/content-viewer';
import type { CatalogEntry } from '@/types/marketplace';
```

---

## Risk Assessment

### Low Risk ✅
- Extracting generic components (FileTree, FrontmatterDisplay)
- Extracting utility functions (YAML, markdown extraction)
- Standard TanStack Query hook pattern

### Medium Risk 🟡
- Maintaining shadcn component compatibility across packages
- Tailwind CSS configuration alignment
- Peer dependency management (React version)

### Mitigation Strategies
- Comprehensive tests before publication
- SemVer discipline with CHANGELOG
- Clear migration guide
- Sample project in repo

---

## Next Steps

1. **Review** these documents with team
2. **Decide** on package name and scope
3. **Create** npm package (public or private)
4. **Extract** Tier 1 components following checklist
5. **Test** thoroughly before publishing
6. **Update** SkillMeat imports
7. **Document** migration path
8. **Release** v1.0.0

---

## Supporting Documents

- **`content-viewing-extraction-inventory.md`** - Full technical analysis (read first for deep dive)
- **`content-viewer-quick-ref.md`** - Checklists and quick lookup (read for implementation)

## Questions to Answer

1. **Package name**: `@skillmeat/content-viewer` or alternative?
2. **npm registry**: Public or private?
3. **License**: Same as SkillMeat main project?
4. **Maintenance**: Who owns the package?
5. **Timeline**: When to publish?
6. **Versioning**: Follow semver?

---

## Related Context

The content viewing components currently support:
- Marketplace artifact browsing
- File tree navigation in catalog entries
- Metadata display for artifacts
- File content previewing

Post-extraction, they can support any use case requiring:
- File tree browsing
- Markdown content viewing
- Frontmatter parsing and display

---

**Analysis Date**: 2026-02-13
**Status**: Complete - Ready for decision
**Confidence**: High (95%+)

All files are well-documented, fully typed, and follow React/TypeScript best practices. Extraction is straightforward and low-risk.
