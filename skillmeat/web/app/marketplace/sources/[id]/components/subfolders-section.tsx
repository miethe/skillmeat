'use client';

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
 * @example
 * ```tsx
 * <SubfoldersSection
 *   subfolders={Object.values(folderNode.children)}
 *   onSelectFolder={(path) => console.log('Navigate to:', path)}
 * />
 * ```
 */
export function SubfoldersSection({ subfolders, onSelectFolder }: SubfoldersSectionProps) {
  // Return null if no subfolders (conditional rendering)
  if (subfolders.length === 0) {
    return null;
  }

  return (
    <section className="mt-8 border-t border-border pt-6">
      {/* Section Header */}
      <div className="mb-4 flex items-center gap-2">
        <FolderTree className="h-5 w-5" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Subfolders</h3>
        <span className="text-sm font-normal text-muted-foreground">({subfolders.length})</span>
      </div>

      {/* Responsive Cards Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {subfolders.map((subfolder) => (
          <SubfolderCard
            key={subfolder.fullPath}
            folder={subfolder}
            onSelect={onSelectFolder}
          />
        ))}
      </div>
    </section>
  );
}
