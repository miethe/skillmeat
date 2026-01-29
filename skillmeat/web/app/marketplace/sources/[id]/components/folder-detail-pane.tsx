'use client';

/**
 * FolderDetailPane Component
 *
 * Right pane (75% width) container that displays selected folder metadata and artifacts.
 * Integrates with the semantic tree for folder selection and displays:
 * 1. Folder header with metadata
 * 2. Artifact type sections (grouped by type, filtered)
 * 3. Subfolders section (NOT filtered)
 *
 * Applies all filters (type, confidence, search, status) to displayed artifacts.
 * Subfolders section is NOT affected by filters and always shows all subfolders.
 */

import { Folder } from 'lucide-react';
import { cn } from '@/lib/utils';
import { applyFiltersToEntries, hasActiveFilters, groupByType } from '@/lib/folder-filter-utils';
import { ArtifactTypeSection } from './artifact-type-section';
import { SubfoldersSection } from './subfolders-section';
import type { FolderNode } from '@/lib/tree-builder';
import type { CatalogEntry, CatalogFilters, ArtifactType } from '@/types/marketplace';

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
 * Filters are applied to artifacts displayed in type sections. Subfolders
 * are not affected by filters and always show all children.
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
  filters,
  onImport,
  onExclude,
  onImportAll: _onImportAll,
  onSelectSubfolder,
}: FolderDetailPaneProps) {
  // Note: onImportAll is intentionally unused in this implementation.
  // It will be wired up when batch import functionality is integrated.
  void _onImportAll;

  // Empty state: no folder selected
  if (!folder) {
    return (
      <section
        role="region"
        aria-label="Folder details"
        className="flex h-full min-h-[400px] items-center justify-center"
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <Folder className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Select a folder to view its contents</p>
        </div>
      </section>
    );
  }

  // Get artifacts for the selected folder (direct artifacts only)
  const folderArtifacts = catalog.filter((entry) => {
    // Match entries where path matches the folder's fullPath
    const entryDir = entry.path.substring(0, entry.path.lastIndexOf('/'));
    return entryDir === folder.fullPath;
  });

  // Apply filters to artifacts
  const filteredArtifacts = applyFiltersToEntries(folderArtifacts, filters);

  // Group filtered artifacts by type
  const artifactsByType = groupByType(filteredArtifacts);

  // Get subfolders from the folder node (NOT affected by filters)
  const subfolders = Object.values(folder.children);

  // Determine if we're showing filtered results
  const isFiltered = hasActiveFilters(filters);
  const unfilteredCount = folderArtifacts.length;

  // Empty state: no artifacts match filters
  if (filteredArtifacts.length === 0 && folder.hasDirectArtifacts) {
    return (
      <section
        role="region"
        aria-label={`${folder.name} folder details`}
        aria-live="polite"
        className={cn('h-full overflow-y-auto p-6')}
      >
        <div className="space-y-6">
          {/* Folder header */}
          <header className="space-y-2">
            <h2 id="folder-detail-heading" className="text-2xl font-semibold">
              {folder.name}
            </h2>
            <p className="text-sm text-muted-foreground">{folder.fullPath}</p>
          </header>

          {/* No matches empty state */}
          <div className="flex min-h-[300px] items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-center">
              <Folder className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
              <div>
                <p className="text-sm font-medium">No artifacts match current filters</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {unfilteredCount} artifact{unfilteredCount !== 1 ? 's' : ''} in this folder (
                  {isFiltered ? 'filtered out' : 'hidden'})
                </p>
              </div>
            </div>
          </div>

          {/* Show subfolders even when artifacts are filtered */}
          {folder.hasSubfolders && (
            <SubfoldersSection subfolders={subfolders} onSelectFolder={onSelectSubfolder} />
          )}
        </div>
      </section>
    );
  }

  return (
    <section
      role="region"
      aria-label={`${folder.name} folder details`}
      aria-live="polite"
      className={cn('h-full overflow-y-auto p-6')}
    >
      <div className="space-y-6">
        {/* Folder header with metadata */}
        <header className="space-y-2">
          <h2 id="folder-detail-heading" className="text-2xl font-semibold">
            {folder.name}
          </h2>
          <p className="text-sm text-muted-foreground">{folder.fullPath}</p>
          <div className="flex items-center gap-4 text-sm">
            <span>
              <span className="font-medium">
                {isFiltered ? filteredArtifacts.length : folder.directCount}
              </span>{' '}
              {isFiltered ? 'matching' : 'direct'} artifact
              {(isFiltered ? filteredArtifacts.length : folder.directCount) !== 1 ? 's' : ''}
            </span>
            {isFiltered && unfilteredCount !== filteredArtifacts.length && (
              <>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground">
                  {unfilteredCount} total in folder
                </span>
              </>
            )}
            {!isFiltered && (
              <>
                <span className="text-muted-foreground">•</span>
                <span>
                  <span className="font-medium">{folder.totalArtifactCount}</span> total artifact
                  {folder.totalArtifactCount !== 1 ? 's' : ''}
                </span>
              </>
            )}
          </div>
        </header>

        {/* Artifact type sections */}
        {folder.hasDirectArtifacts && filteredArtifacts.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Artifacts</h3>
            <div className="space-y-4">
              {(Object.keys(artifactsByType) as ArtifactType[])
                .sort()
                .map((type) => {
                  const entries = artifactsByType[type] || [];
                  return (
                    <ArtifactTypeSection
                      key={type}
                      type={type}
                      artifacts={entries}
                      defaultExpanded={true}
                      onImport={onImport}
                      onExclude={onExclude}
                    />
                  );
                })}
            </div>
          </div>
        )}

        {/* SubfoldersSection - integrated with navigation (NOT affected by filters) */}
        {folder.hasSubfolders && (
          <SubfoldersSection subfolders={subfolders} onSelectFolder={onSelectSubfolder} />
        )}

        {/* Empty state for folder with no artifacts or subfolders */}
        {!folder.hasDirectArtifacts && !folder.hasSubfolders && (
          <div className="flex min-h-[200px] items-center justify-center">
            <p className="text-sm text-muted-foreground">This folder is empty</p>
          </div>
        )}
      </div>
    </section>
  );
}
