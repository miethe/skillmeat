'use client';

import { memo, useCallback } from 'react';
import { FolderTree } from 'lucide-react';
import type { FolderNode } from '@/lib/tree-builder';
import { SubfolderCard } from './subfolder-card';

/**
 * Props for SubfoldersSection component.
 */
interface SubfoldersSectionProps {
  /** Array of subfolder nodes */
  subfolders: FolderNode[];
  /** Callback when a subfolder is selected */
  onSelectFolder: (path: string) => void;
}

/**
 * SubfoldersSection component displays subfolders in a responsive grid layout.
 *
 * Renders a section with header (icon, title, count) and a grid of SubfolderCard
 * components. Only displays when subfolders exist - returns null if empty array.
 *
 * Layout adapts responsively:
 * - Mobile: 1 column
 * - Tablet (md): 2 columns
 * - Desktop (lg): 3 columns
 *
 * PERFORMANCE: Wrapped with React.memo to prevent re-renders when
 * sibling components update without affecting subfolders list.
 *
 * @example
 * ```tsx
 * <SubfoldersSection
 *   subfolders={Object.values(folderNode.children)}
 *   onSelectFolder={(path) => console.log('Navigate to:', path)}
 * />
 * ```
 */
function SubfoldersSectionComponent({ subfolders, onSelectFolder }: SubfoldersSectionProps) {
  // Memoize the select handler to provide stable reference to SubfolderCard
  // Must be called unconditionally (Rules of Hooks)
  const handleSelect = useCallback(
    (path: string) => {
      onSelectFolder(path);
    },
    [onSelectFolder]
  );

  // Return null if no subfolders (after hooks)
  if (subfolders.length === 0) {
    return null;
  }

  return (
    <section
      role="region"
      aria-label={`Subfolders, ${subfolders.length} ${subfolders.length === 1 ? 'folder' : 'folders'}`}
      className="mt-8 border-t border-border pt-6"
    >
      {/* Section Header */}
      <div className="mb-4 flex items-center gap-2">
        <FolderTree className="h-5 w-5" aria-hidden="true" />
        <h3 id="subfolders-heading" className="text-lg font-semibold">
          Subfolders
        </h3>
        <span className="text-sm font-normal text-muted-foreground" aria-hidden="true">
          ({subfolders.length})
        </span>
      </div>

      {/* Responsive Cards Grid */}
      <div
        role="list"
        aria-labelledby="subfolders-heading"
        className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      >
        {subfolders.map((subfolder) => (
          <div key={subfolder.fullPath} role="listitem">
            <SubfolderCard folder={subfolder} onSelect={handleSelect} />
          </div>
        ))}
      </div>
    </section>
  );
}

export const SubfoldersSection = memo(SubfoldersSectionComponent);
