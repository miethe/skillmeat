'use client';

/**
 * SourceFolderLayout Component
 *
 * Two-pane master-detail layout for marketplace folder view.
 * - Left pane (25%): Semantic navigation tree
 * - Right pane (75%): Folder detail with artifacts
 * - Responsive: stacks vertically on mobile (<768px)
 */

import { cn } from '@/lib/utils';
import type { CatalogEntry, CatalogFilters } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

/**
 * Folder tree node structure.
 * Note: This type will be moved to @/lib/tree-builder when that module is created.
 */
export interface FolderNode {
  /** Folder name (last segment of path) */
  name: string;
  /** Full path from repository root */
  path: string;
  /** Child folders */
  children: FolderNode[];
  /** Artifacts directly in this folder (not in subfolders) */
  directArtifacts: CatalogEntry[];
  /** Number of artifacts directly in this folder */
  directCount: number;
  /** Total artifact count including all descendants */
  totalArtifactCount: number;
  /** Whether this folder has child folders */
  hasSubfolders: boolean;
  /** Whether this folder has direct artifacts */
  hasDirectArtifacts: boolean;
}

/**
 * Root folder tree structure.
 */
export interface FolderTree {
  /** Root-level folder nodes */
  roots: FolderNode[];
  /** Total number of folders in tree */
  totalFolders: number;
  /** Maximum depth of tree */
  maxDepth: number;
}

/**
 * Filter state for folder view.
 * Uses CatalogFilters from marketplace types.
 */
export type FilterState = CatalogFilters;

/**
 * Props for SourceFolderLayout component.
 */
export interface SourceFolderLayoutProps {
  /** Folder tree structure */
  tree: FolderTree;
  /** Currently selected folder path, null if none */
  selectedFolder: string | null;
  /** Callback when a folder is selected */
  onSelectFolder: (path: string) => void;
  /** Set of expanded folder paths */
  expanded: Set<string>;
  /** Callback to toggle folder expansion */
  onToggleExpand: (path: string) => void;
  /** All catalog entries (for filtering in detail pane) */
  catalog: CatalogEntry[];
  /** Current filter state */
  filters: FilterState;
  /** Callback when import is requested for an entry */
  onImport: (entry: CatalogEntry) => void;
  /** Callback when exclude is requested for an entry */
  onExclude: (entry: CatalogEntry) => void;
}

// ============================================================================
// Component
// ============================================================================

/**
 * SourceFolderLayout - Two-pane master-detail layout for folder view
 *
 * Displays a semantic navigation tree on the left (25%) and folder detail
 * content on the right (75%). Responsive design stacks panes vertically
 * on screens narrower than 768px.
 *
 * @example
 * ```tsx
 * <SourceFolderLayout
 *   tree={folderTree}
 *   selectedFolder={selectedPath}
 *   onSelectFolder={handleSelectFolder}
 *   expanded={expandedFolders}
 *   onToggleExpand={handleToggleExpand}
 *   catalog={catalogEntries}
 *   filters={currentFilters}
 *   onImport={handleImport}
 *   onExclude={handleExclude}
 * />
 * ```
 */
export function SourceFolderLayout({
  tree,
  selectedFolder,
  onSelectFolder: _onSelectFolder,
  expanded,
  onToggleExpand: _onToggleExpand,
  catalog,
  filters: _filters,
  onImport,
  onExclude: _onExclude,
}: SourceFolderLayoutProps) {
  // Note: Prefixed props are intentionally unused in this placeholder.
  // They will be wired up when SemanticTree and FolderDetailPane are integrated.
  void _onSelectFolder;
  void _onToggleExpand;
  void _filters;
  void _onExclude;
  // Get artifacts for the selected folder
  const selectedFolderArtifacts = selectedFolder
    ? catalog.filter((entry) => {
        // Match entries where path starts with selected folder
        const entryDir = entry.path.substring(0, entry.path.lastIndexOf('/'));
        return entryDir === selectedFolder || entry.path.startsWith(selectedFolder + '/');
      })
    : [];

  return (
    <div
      className={cn(
        'flex h-full min-h-[400px]',
        // Responsive: stack vertically on mobile, side-by-side on md+
        'flex-col md:flex-row'
      )}
    >
      {/* Left Pane - Semantic Tree (25% width on desktop) */}
      <aside
        className={cn(
          'border-b bg-muted/20 md:border-b-0 md:border-r',
          // Width: 100% on mobile, 25% on desktop with min-width
          'w-full md:w-1/4 md:min-w-[200px] md:max-w-[300px]',
          // Scrolling
          'overflow-y-auto',
          // Height: fixed on mobile, full on desktop
          'h-[200px] md:h-full'
        )}
      >
        <div className="p-3">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Folders
          </h3>
          {/* SemanticTree placeholder - will be replaced with actual component */}
          <div className="space-y-1 text-sm">
            {tree.roots.length === 0 ? (
              <p className="py-4 text-center text-muted-foreground">No folders found</p>
            ) : (
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  Tree: {tree.totalFolders} folder{tree.totalFolders !== 1 ? 's' : ''}
                </p>
                {selectedFolder && (
                  <p className="truncate font-medium">Selected: {selectedFolder}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Expanded: {expanded.size} folder{expanded.size !== 1 ? 's' : ''}
                </p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Right Pane - Folder Detail (75% width on desktop) */}
      <main
        className={cn(
          'flex-1 overflow-y-auto',
          // Padding for content
          'p-4'
        )}
      >
        {/* FolderDetailPane placeholder - will be replaced with actual component */}
        {selectedFolder ? (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">{selectedFolder}</h2>
              <p className="text-sm text-muted-foreground">
                {selectedFolderArtifacts.length} artifact
                {selectedFolderArtifacts.length !== 1 ? 's' : ''} in this folder
              </p>
            </div>

            {/* Placeholder artifact list */}
            {selectedFolderArtifacts.length > 0 ? (
              <div className="space-y-2">
                {selectedFolderArtifacts.slice(0, 5).map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between rounded-md border p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{entry.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{entry.path}</p>
                    </div>
                    <div className="ml-4 flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">{entry.artifact_type}</span>
                      {entry.status !== 'imported' && entry.status !== 'excluded' && (
                        <button
                          type="button"
                          onClick={() => onImport(entry)}
                          className="text-xs text-primary hover:underline"
                        >
                          Import
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {selectedFolderArtifacts.length > 5 && (
                  <p className="text-center text-sm text-muted-foreground">
                    ... and {selectedFolderArtifacts.length - 5} more
                  </p>
                )}
              </div>
            ) : (
              <p className="py-8 text-center text-muted-foreground">
                No artifacts in this folder
              </p>
            )}
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-muted-foreground">Select a folder to view its contents</p>
          </div>
        )}
      </main>
    </div>
  );
}
