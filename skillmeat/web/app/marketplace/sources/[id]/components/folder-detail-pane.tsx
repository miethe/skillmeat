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
 *
 * PERFORMANCE OPTIMIZATIONS:
 * - useMemo for expensive filtering and grouping operations
 * - useCallback for event handlers passed to child components
 * - Child components (ArtifactTypeSection, SubfoldersSection) are memoized
 */

import { useMemo, useCallback } from 'react';
import { Folder } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  applyFiltersToEntries,
  hasActiveFilters,
  groupByType,
  getDisplayArtifactsForFolder,
} from '@/lib/folder-filter-utils';
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
  /** Selected folder node (null if none selected, shows root view) */
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
  /** Top-level folders to show as subfolders when at root (folder === null) */
  rootFolders?: FolderNode[];
  /** Callback when artifact card is clicked (opens modal) */
  onArtifactClick?: (entry: CatalogEntry) => void;
  /** Source ID for exclude operations */
  sourceId: string;
  /** Whether import is in progress */
  isImporting?: boolean;
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
  rootFolders,
  onArtifactClick,
  sourceId,
  isImporting = false,
}: FolderDetailPaneProps) {
  // Note: onImportAll is intentionally unused in this implementation.
  // It will be wired up when batch import functionality is integrated.
  void _onImportAll;

  // When folder is null, we're at the source root
  const isAtRoot = !folder;
  const folderPath = folder?.fullPath ?? '';

  // PERFORMANCE: All hooks must be called unconditionally (Rules of Hooks)
  // Memoize folder artifacts - includes artifacts from filtered-out leaf containers
  // This handles "promotion" of artifacts from skills/, commands/, etc. to parent folders
  // For root (folderPath === ''), returns root-level artifacts
  const folderArtifacts = useMemo(() => {
    return getDisplayArtifactsForFolder(catalog, folderPath);
  }, [catalog, folderPath]);

  // PERFORMANCE: Memoize filtered artifacts calculation
  // Applies type, confidence, search, and status filters
  const filteredArtifacts = useMemo(() => {
    return applyFiltersToEntries(folderArtifacts, filters);
  }, [folderArtifacts, filters]);

  // PERFORMANCE: Memoize artifact grouping by type
  // Groups filtered artifacts into type buckets for section display
  const artifactsByType = useMemo(() => {
    return groupByType(filteredArtifacts);
  }, [filteredArtifacts]);

  // PERFORMANCE: Memoize subfolders array
  // At root: use rootFolders prop; in folder: use folder.children
  const subfolders = useMemo(() => {
    if (folder) {
      return Object.values(folder.children);
    }
    return rootFolders ?? [];
  }, [folder, rootFolders]);

  // Determine if we're showing filtered results
  const isFiltered = hasActiveFilters(filters);
  const unfilteredCount = folderArtifacts.length;

  // Check if folder/root has any artifacts to display (direct + promoted from leaf containers)
  const hasDisplayableArtifacts = folderArtifacts.length > 0;
  const hasSubfolders = isAtRoot
    ? (rootFolders?.length ?? 0) > 0
    : (folder?.hasSubfolders ?? false);

  // PERFORMANCE: Memoize handlers passed to child components
  const handleImport = useCallback(
    (entry: CatalogEntry) => {
      onImport(entry);
    },
    [onImport]
  );

  const handleExclude = useCallback(
    (entry: CatalogEntry) => {
      onExclude(entry);
    },
    [onExclude]
  );

  const handleSelectSubfolder = useCallback(
    (path: string) => {
      onSelectSubfolder(path);
    },
    [onSelectSubfolder]
  );

  // Display name and description for header
  const displayName = isAtRoot ? 'Source Root' : folder.name;
  const displayPath = isAtRoot ? '' : folder.fullPath;
  const displayDescription = isAtRoot ? 'Root-level artifacts and top-level folders' : displayPath;

  // Empty state: no artifacts match filters (but folder/root has artifacts to show without filters)
  if (filteredArtifacts.length === 0 && hasDisplayableArtifacts) {
    return (
      <section
        role="region"
        aria-label={`${displayName} folder details`}
        aria-live="polite"
        className={cn('h-full overflow-y-auto p-6')}
      >
        <div className="space-y-6">
          {/* Folder/Root header */}
          <header className="space-y-2">
            <h2 id="folder-detail-heading" className="text-2xl font-semibold">
              {displayName}
            </h2>
            <p className="text-sm text-muted-foreground">{displayDescription}</p>
          </header>

          {/* No matches empty state */}
          <div className="flex min-h-[300px] items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-center">
              <Folder className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
              <div>
                <p className="text-sm font-medium">No artifacts match current filters</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {unfilteredCount} artifact{unfilteredCount !== 1 ? 's' : ''} in this{' '}
                  {isAtRoot ? 'source' : 'folder'} ({isFiltered ? 'filtered out' : 'hidden'})
                </p>
              </div>
            </div>
          </div>

          {/* Show subfolders even when artifacts are filtered */}
          {hasSubfolders && (
            <SubfoldersSection subfolders={subfolders} onSelectFolder={handleSelectSubfolder} />
          )}
        </div>
      </section>
    );
  }

  return (
    <section
      role="region"
      aria-label={`${displayName} folder details`}
      aria-live="polite"
      className={cn('h-full overflow-y-auto p-6')}
    >
      <div className="space-y-6">
        {/* Folder/Root header with metadata */}
        <header className="space-y-2">
          <h2 id="folder-detail-heading" className="text-2xl font-semibold">
            {displayName}
          </h2>
          <p className="text-sm text-muted-foreground">{displayDescription}</p>
          <div className="flex items-center gap-4 text-sm">
            <span>
              <span className="font-medium">
                {isFiltered ? filteredArtifacts.length : folderArtifacts.length}
              </span>{' '}
              {isFiltered ? 'matching' : 'root'} artifact
              {(isFiltered ? filteredArtifacts.length : folderArtifacts.length) !== 1 ? 's' : ''}
            </span>
            {isFiltered && unfilteredCount !== filteredArtifacts.length && (
              <>
                <span className="text-muted-foreground">.</span>
                <span className="text-muted-foreground">
                  {unfilteredCount} total in {isAtRoot ? 'source' : 'folder'}
                </span>
              </>
            )}
            {!isFiltered && !isAtRoot && folder && (
              <>
                <span className="text-muted-foreground">.</span>
                <span>
                  <span className="font-medium">{folder.totalArtifactCount}</span> total artifact
                  {folder.totalArtifactCount !== 1 ? 's' : ''}
                </span>
              </>
            )}
          </div>
        </header>

        {/* Artifact type sections (includes promoted artifacts from leaf containers) */}
        {hasDisplayableArtifacts && filteredArtifacts.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Artifacts</h3>
            <div className="space-y-4">
              {(Object.keys(artifactsByType) as ArtifactType[]).sort().map((type) => {
                const entries = artifactsByType[type] || [];
                return (
                  <ArtifactTypeSection
                    key={type}
                    type={type}
                    artifacts={entries}
                    defaultExpanded={true}
                    onImport={handleImport}
                    onExclude={handleExclude}
                    onArtifactClick={onArtifactClick}
                    sourceId={sourceId}
                    isImporting={isImporting}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* SubfoldersSection - integrated with navigation (NOT affected by filters) */}
        {hasSubfolders && (
          <SubfoldersSection subfolders={subfolders} onSelectFolder={handleSelectSubfolder} />
        )}

        {/* Empty state for folder/root with no artifacts (direct or promoted) and no subfolders */}
        {!hasDisplayableArtifacts && !hasSubfolders && (
          <div className="flex min-h-[200px] items-center justify-center">
            <p className="text-sm text-muted-foreground">
              {isAtRoot ? 'This source is empty' : 'This folder is empty'}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
