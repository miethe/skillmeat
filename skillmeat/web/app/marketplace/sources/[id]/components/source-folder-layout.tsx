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
import type { FolderNode, FolderTree } from '@/lib/tree-builder';
import { FolderDetailPane } from './folder-detail-pane';

// ============================================================================
// Types
// ============================================================================

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
  /**
   * Navigate to a folder by path (optional, for subfolder navigation).
   * If provided, enables smooth subfolder card navigation with automatic tree expansion.
   * If not provided, falls back to separate onSelectFolder + expandPath calls.
   */
  onNavigateToFolder?: (path: string) => void;
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
 *   onNavigateToFolder={handleNavigateToFolder}
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
  filters,
  onImport,
  onExclude: _onExclude,
  onNavigateToFolder,
}: SourceFolderLayoutProps) {
  // Note: Prefixed props are intentionally unused in this placeholder.
  // They will be wired up when SemanticTree is integrated.
  void _onSelectFolder;
  void _onToggleExpand;
  void _onExclude;

  // Convert FolderTree (Record<string, FolderNode>) to array of root nodes
  const rootNodes = Object.values(tree);

  // Get the selected folder node from the tree
  const selectedFolderNode = selectedFolder
    ? findFolderByPath(rootNodes, selectedFolder)
    : null;

  /**
   * Handle subfolder selection - navigate to folder with tree expansion.
   * Uses onNavigateToFolder if provided, otherwise falls back to onSelectFolder.
   */
  const handleSubfolderSelect = (path: string) => {
    if (onNavigateToFolder) {
      onNavigateToFolder(path);
    } else {
      _onSelectFolder(path);
    }
  };

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
        aria-label="Folder navigation"
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
          <h3
            id="folder-nav-heading"
            className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
          >
            Folders
          </h3>
          {/* SemanticTree placeholder - will be replaced with actual component */}
          <div className="space-y-1 text-sm">
            {rootNodes.length === 0 ? (
              <p className="py-4 text-center text-muted-foreground">No folders found</p>
            ) : (
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  Tree: {rootNodes.length} folder{rootNodes.length !== 1 ? 's' : ''}
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
        aria-label="Folder contents"
        className={cn(
          'flex-1 overflow-y-auto'
          // No padding here - FolderDetailPane has its own padding
        )}
      >
        <FolderDetailPane
          folder={selectedFolderNode}
          catalog={catalog}
          filters={filters}
          onImport={onImport}
          onExclude={() => {
            // Exclude is handled within the detail pane via ExcludeArtifactDialog
          }}
          onImportAll={(entries) => {
            // Import all entries from folder
            entries.forEach((entry) => onImport(entry));
          }}
          onSelectSubfolder={handleSubfolderSelect}
        />
      </main>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Find a folder node by its full path in the tree.
 *
 * @param roots - Root folder nodes to search
 * @param path - Full path to search for
 * @returns Folder node if found, null otherwise
 */
function findFolderByPath(roots: FolderNode[], path: string): FolderNode | null {
  for (const root of roots) {
    if (root.fullPath === path) {
      return root;
    }

    // Recursively search children
    const childrenArray = Object.values(root.children);
    const found = findFolderByPath(childrenArray, path);
    if (found) {
      return found;
    }
  }

  return null;
}
