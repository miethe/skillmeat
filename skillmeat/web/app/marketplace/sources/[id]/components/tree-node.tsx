'use client';

import { Folder, FolderOpen, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface TreeNodeProps {
  name: string;
  fullPath: string;
  depth: number;
  directCount: number;
  totalCount: number;
  hasDirectArtifacts: boolean;
  hasSubfolders: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
}

export function TreeNode({
  name,
  fullPath,
  depth,
  directCount,
  totalCount,
  hasDirectArtifacts,
  hasSubfolders,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpand,
}: TreeNodeProps) {
  const FolderIcon = isExpanded ? FolderOpen : Folder;
  const isMixedContent = hasDirectArtifacts && hasSubfolders;

  // Generate accessible label
  const ariaLabel = `${name} folder, ${directCount} direct artifact${directCount === 1 ? '' : 's'}, ${totalCount} total`;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect();
    }
  };

  const handleChevronClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleExpand();
  };

  return (
    <div
      role="treeitem"
      aria-selected={isSelected}
      aria-expanded={hasSubfolders ? isExpanded : undefined}
      aria-label={ariaLabel}
      tabIndex={0}
      className={cn(
        'flex items-center gap-2 py-2 pr-2 rounded-md cursor-pointer transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        isSelected
          ? 'bg-accent text-accent-foreground'
          : 'bg-transparent hover:bg-accent/50'
      )}
      style={{ paddingLeft: `${depth * 24 + 8}px` }}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
    >
      {/* Expand/collapse chevron */}
      {hasSubfolders && (
        <button
          type="button"
          onClick={handleChevronClick}
          className={cn(
            'flex-shrink-0 p-0.5 rounded transition-transform duration-200',
            'hover:bg-accent focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
            isExpanded && 'rotate-90'
          )}
          aria-label={isExpanded ? 'Collapse folder' : 'Expand folder'}
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      )}

      {/* Spacer when no chevron to maintain alignment */}
      {!hasSubfolders && <div className="w-5" />}

      {/* Folder icon */}
      <FolderIcon className="h-4 w-4 flex-shrink-0 text-muted-foreground" />

      {/* Folder name */}
      <TooltipProvider delayDuration={500}>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="truncate text-sm font-medium flex-1 min-w-0">
              {name}
            </span>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p className="text-xs">{totalCount} total artifact{totalCount === 1 ? '' : 's'}</p>
            <p className="text-xs text-muted-foreground">{fullPath}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Direct count badge */}
      {directCount > 0 && (
        <Badge variant="secondary" className="text-xs px-1.5 py-0">
          {directCount}
        </Badge>
      )}

      {/* Mixed-content indicator */}
      {isMixedContent && (
        <TooltipProvider delayDuration={300}>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
            </TooltipTrigger>
            <TooltipContent side="right">
              <p className="text-xs">Mixed content: artifacts and subfolders</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}
