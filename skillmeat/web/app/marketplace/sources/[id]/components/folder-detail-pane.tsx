'use client';

/**
 * FolderDetailPane Component
 *
 * Right pane (75% width) container that displays selected folder metadata and artifacts.
 * Integrates with the semantic tree for folder selection and displays:
 * 1. Folder header with metadata
 * 2. Artifact type sections (grouped by type)
 * 3. Subfolders section
 */

import { Folder } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FolderNode } from '@/lib/tree-builder';
import type { CatalogEntry, CatalogFilters } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

/**
 * Props for FolderDetailPane component.
 */
export interface FolderDetailPaneProps {
  /** Selected folder node (null if none selected) */
  folder: FolderNode | null;
  /** All catalog entries for the source */
  catalog: CatalogEntry[];
  /** Current filter state */
  filters: CatalogFilters;
  /** Callback when import is requested */
  onImport: (entry: CatalogEntry) => void;
  /** Callback when exclude is requested */
  onExclude: (entry: CatalogEntry) => void;
  /** Callback when "Import All" is clicked */
  onImportAll: (entries: CatalogEntry[]) => void;
  /** Callback when a subfolder is selected */
  onSelectSubfolder: (path: string) => void;
}

// ============================================================================
// Component
// ============================================================================

/**
 * FolderDetailPane - Right pane container for displaying folder details
 *
 * Shows folder metadata, artifacts grouped by type, and subfolders when
 * a folder is selected from the semantic tree. Displays an empty state
 * when no folder is selected.
 *
 * @example
 * ```tsx
 * <FolderDetailPane
 *   folder={selectedFolderNode}
 *   catalog={catalogEntries}
 *   filters={currentFilters}
 *   onImport={handleImport}
 *   onExclude={handleExclude}
 *   onImportAll={handleImportAll}
 *   onSelectSubfolder={handleSelectSubfolder}
 * />
 * ```
 */
export function FolderDetailPane({
  folder,
  catalog,
  filters: _filters,
  onImport: _onImport,
  onExclude: _onExclude,
  onImportAll: _onImportAll,
  onSelectSubfolder: _onSelectSubfolder,
}: FolderDetailPaneProps) {
  // Note: Prefixed props are intentionally unused in this placeholder.
  // They will be wired up when child components (FolderDetailHeader, etc.) are integrated.
  void _filters;
  void _onImport;
  void _onExclude;
  void _onImportAll;
  void _onSelectSubfolder;

  // Empty state: no folder selected
  if (!folder) {
    return (
      <div className="flex h-full min-h-[400px] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <Folder className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Select a folder to view its contents</p>
        </div>
      </div>
    );
  }

  // Get artifacts for the selected folder (direct artifacts only)
  const folderArtifacts = catalog.filter((entry) => {
    // Match entries where path matches the folder's fullPath
    const entryDir = entry.path.substring(0, entry.path.lastIndexOf('/'));
    return entryDir === folder.fullPath;
  });

  // Group artifacts by type for placeholder display
  const artifactsByType = folderArtifacts.reduce(
    (acc, entry) => {
      if (!acc[entry.artifact_type]) {
        acc[entry.artifact_type] = [];
      }
      acc[entry.artifact_type]!.push(entry);
      return acc;
    },
    {} as Record<string, CatalogEntry[]>
  );

  // Get subfolders from the folder node
  const subfolders = Object.values(folder.children);

  return (
    <div className={cn('h-full overflow-y-auto p-6')}>
      <div className="space-y-6">
        {/* FolderDetailHeader slot - placeholder */}
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold">{folder.name}</h2>
          <p className="text-sm text-muted-foreground">{folder.fullPath}</p>
          <div className="flex items-center gap-4 text-sm">
            <span>
              <span className="font-medium">{folder.directCount}</span> direct artifact
              {folder.directCount !== 1 ? 's' : ''}
            </span>
            <span className="text-muted-foreground">•</span>
            <span>
              <span className="font-medium">{folder.totalArtifactCount}</span> total artifact
              {folder.totalArtifactCount !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        {/* ArtifactTypeSections slot - placeholder */}
        {folder.hasDirectArtifacts && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Artifacts</h3>
            {Object.entries(artifactsByType).map(([type, entries]) => (
              <div key={type} className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">
                  {type} ({entries.length})
                </h4>
                <div className="space-y-2">
                  {entries.map((entry) => (
                    <div
                      key={entry.id}
                      className="flex items-center justify-between rounded-md border p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{entry.name}</p>
                        <p className="truncate text-xs text-muted-foreground">{entry.path}</p>
                      </div>
                      <div className="ml-4">
                        <span className="text-xs text-muted-foreground">
                          {entry.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* SubfoldersSection slot - placeholder */}
        {folder.hasSubfolders && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Subfolders ({subfolders.length})</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {subfolders.map((subfolder) => (
                <div
                  key={subfolder.fullPath}
                  className="flex items-center gap-3 rounded-md border p-3"
                >
                  <Folder className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{subfolder.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {subfolder.totalArtifactCount} artifact
                      {subfolder.totalArtifactCount !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state for folder with no artifacts or subfolders */}
        {!folder.hasDirectArtifacts && !folder.hasSubfolders && (
          <div className="flex min-h-[200px] items-center justify-center">
            <p className="text-sm text-muted-foreground">
              This folder is empty
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
