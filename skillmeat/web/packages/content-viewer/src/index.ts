// @skillmeat/content-viewer
// Public API Contract v0.0.1
//
// This barrel export defines the planned public surface area.
// Exports are added as components are extracted from the main app.
//
// Phase legend:
//   Phase 2 — Component + utility extraction (no external runtime dependencies)
//   Phase 3 — Hook + API client extraction (requires adapter abstraction for
//              TanStack Query and the SkillMeat backend URL)

// ============================================================
// Components (Phase 2)
// ============================================================
// export { FileTree } from './components/FileTree';
// export type { FileTreeProps } from './components/FileTree';
// export { FrontmatterDisplay } from './components/FrontmatterDisplay';
// export type { FrontmatterDisplayProps } from './components/FrontmatterDisplay';

// ============================================================
// Utilities (Phase 2)
// ============================================================
export {
  parseFrontmatter,
  stripFrontmatter,
  detectFrontmatter,
} from './lib/frontmatter';
export {
  extractFirstParagraph,
  extractFolderReadme,
} from './lib/readme-utils';
export type { ReadmeSearchEntry } from './lib/readme-utils';

// ============================================================
// Types (Phase 2)
// ============================================================
// export type { FileNode } from './types';
// export type { FileTreeResponse, FileContentResponse } from './types';

// ============================================================
// Hooks (Phase 3 — requires adapter abstraction)
// ============================================================
// export { useCatalogFileTree, useCatalogFileContent } from './hooks/useFileContent';

// ============================================================
// API Client (Phase 3 — requires adapter abstraction)
// ============================================================
// export { fetchCatalogFileTree, fetchCatalogFileContent } from './lib/api';

